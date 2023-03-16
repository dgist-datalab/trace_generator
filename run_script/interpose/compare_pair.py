# Redis 실험 시에 malloc - free address가 짝이 맞지 않아서 비교하기 위한 스크립트
# 각 addr를 별도의 list에 저장한 뒤, 정렬하여 차례대로 짝이 있는지 비교
# 총 갯수/맞는 개수/안맞는 개수 (+모든 리스트) 출력.

# 끝나고 opened_mallocs에 남은 entry를 모두 출력하면? free 안 된 것들 + free했는데 주소가 달라서 안 지워진 것들
# 짝이 안 맞더라도, Redis에 메모리 누수가 있는 게 아니라면 맞는 것들은 분명 호출되었을 것이다.
# 1) fprintf()가 삽입되지 않는 free가 있다거나, 2) 주소가 살짝 달라서 가까운 거리에 있었다거나.
# 이걸 확인하려면, 결국 다 출력해서 확인해봐야 한다.
# 모든 리스트를 출력할 때, 짝이 맞는지 확인을 위해 상대방의 id도 같이 적게 하자.

import matplotlib.pyplot as plt
import numpy as np
import sys
import cProfile
from collections import namedtuple
import bisect
from bisect import insort, bisect_left
from itertools import islice

class SortedDict:
    def __init__(self, *args, **kwargs):
        self.keys = []
        self.values = []
        # ...

    def __getitem__(self, key):
        index = self.keys.index(key)
        return self.values[index]

    def __setitem__(self, key, value):
        if key in self.keys:
            index = self.keys.index(key)
            self.values[index] = value
        else:
            bisect.insort(self.keys, key)
            index = self.keys.index(key)
            self.values.insert(index, value)

    def __delitem__(self, key):
        index = self.keys.index(key)
        del self.keys[index]
        del self.values[index]

    def get_value(self, key):
        return self[key]

    def __len__(self):
        return len(self.keys)

    def items(self):
        return ((key, self[key]) for key in self.keys)

    def find_closest_key(self, x):
        if not self.keys:
            return None
        index = bisect_left(self.keys, x)
        if index == 0:
            return self.keys[0]
        if index == len(self.keys):
            return self.keys[-1]
        before = self.keys[index - 1]
        after = self.keys[index]
        if after - x < x - before:
            return after
        else:
            return before

    def find_closest_key_less_than(self, x):
        if not self.keys:
            return None
        index = bisect_left(self.keys, x)
        if index == 0:
            return self.keys[0]
        if index == len(self.keys):
            return self.keys[-1]
        before = self.keys[index - 1]
        after = self.keys[index]
        if after <= x:
            return after
        elif before < x:
            return before
        else:
            return None

    def iter_from_key(self, start_key):
        # Find the index of the start_key in the sorted key list
        start_index = bisect_left(self.keys, start_key)
        
        # Use itertools to iterate over the remaining key/value pairs
        return ((key, self[key]) for key in islice(self.keys, start_index, None))

# valgrind에 function begin-end 시 print하는 코드를 추가해 놓았을 때,
# 그 정보를 .vout에서 읽어서 구분하는 스크립트
# func_trace.py 
# input: [.vout] file
# output: stdout 

LINE_FUNC_BEGIN=0
LINE_FUNC_END=1
LINE_MALLOC_CALL=2
LINE_FREE_CALL=3
LINE_IGNORE=4
LINE_RW=5

# Initialize global sequence types & variables
func_dict = {}
opened_funcs = []
malloc_dict = {}
#opened_mallocs = {}
opened_mallocs = SortedDict()
m_list = []
f_list = []

malloc_id = 0
free_id = 0
func_id = 0
popf_dict = {} # nested dict, {key: malloc_id, value: {key: func_name, value: rw_entry}}
total_rcnt = 0 # # of total read
total_wcnt = 0 # # of total write
total_obj_rcnt = 0 # # of total read to objects
total_obj_wcnt = 0 # # of total write to objects
obj_stats = []
output_file = ""

#class StatPopf:
    #def __init__(r_rate, w_rate, 

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

class FuncAccess:
    def __init__(self, fcall_cnt, line_group):
        self.fcall_cnt = fcall_cnt
        self.line_group = line_group

class RWEntry:
    def __init__(self, rw_type, rw_addr, rw_timestamp, func_name=None, obj_id=-1, func_id=-1):
        self.obj_id = obj_id
        self.rw_type = rw_type
        self.rw_addr = rw_addr
        self.rw_timestamp = rw_timestamp
        self.func_name = func_name
        self.func_id = func_id
        
class MemEntry:
    def __init__(self, malloc_id, msize, maddr, line_group, rcnt, wcnt, free_id=-1):
        self.malloc_id = malloc_id
        self.msize = msize
        self.maddr = maddr
        self.line_group = line_group
        self.rcnt = rcnt
        self.wcnt = wcnt
        self.free_id = free_id

class FreeEntry:
    def __init__(self, free_id, faddr, malloc_id=-1):
        self.free_id = free_id
        self.faddr = faddr
        self.malloc_id = malloc_id
    

# 공통된 Access list를 하나 만들어두고
# 여러 dict가 다른 방식으로 그것을 가리키게?
# Access list 하나로 되는지?
# func_dict에는 line을 거의 그대로 넣었는데, 
# 거기에는 obj_id, func_id가 없다. 
# func_id는 없어도 괜찮다고 쳐도, obj_id는 좀 다른데. default=-1로?

# Statistics
# 전체 RW 중 Obj, 모든 Obj 중 Obj, Obj의 함수별 비율 등.. 비율이 너무 많다.

def calculate_rate(cnt, total):
    if total == 0:
        rate = float("nan")
    else:
        rate = cnt/total * 100
    return rate

def make_rwcnt_popf(mentry, rw_list, fname):
    rcnt_popf = 0; wcnt_popf = 0
    for rw_entry in rw_list:
        if rw_entry.rw_type == "R":
            rcnt_popf += 1
        elif rw_entry.rw_type == "W":
            wcnt_popf += 1
        else:
            print("error"); exit()
    return rcnt_popf, wcnt_popf

def make_stat_popf(mentry, rw_list, fname):
    global output_file
    rcnt_popf = 0; wcnt_popf = 0
    for rw_entry in rw_list:
        if rw_entry.rw_type == "R":
            rcnt_popf += 1
        elif rw_entry.rw_type == "W":
            wcnt_popf += 1
        else:
            print("error"); exit()

    r_rate = calculate_rate(rcnt_popf, mentry.rcnt) # read ratio of the function in the object (popf)
    w_rate = calculate_rate(wcnt_popf, mentry.wcnt)
    rw_rate = (rcnt_popf+wcnt_popf) / (mentry.rcnt+mentry.wcnt)
    msg="(obj {0} - func {1}) R: {2}/{3} ({4:.2f}%), W: {5}/{6} ({7:.2f}%)\n".foramt(
            mentry.malloc_id, fname, rcnt_popf, mentry.rcnt, r_rate, 
            wcnt_popf, mentry.wcnt, w_rate)
    output_file.write(msg)
    """
    print("(obj %d - func %s) R: %d/%d (%.2f%%), W: %d/%d (%.2f%%)" 
            % (mentry.malloc_id, fname, rcnt_popf, mentry.rcnt, r_rate, 
            wcnt_popf, mentry.wcnt, w_rate))
    """
    return r_rate, w_rate, rw_rate

"""
def make_stat_popf(rcnt_po, wcnt_po, ac_list): # statistics of 'per-object-per-function'
    rcnt_popf = 0; wcnt_popf = 0;
    for line in ac_list:
        rwtype = line[1]
        if rwtype == "R":
            rcnt_popf += 1
        elif rwtype == "W":
            wcnt_popf += 1
        else:
            print("error"); exit()
    read_ratio = rcnt_popf / rcnt_po # read ratio of the function in the object (popf)
    write_ratio = wcnt_popf / wcnt_po

    #print("(obj %d - func %s) R: %d (%.2f), W: %d (%.2f)", ac_list[0])
"""

def analyze_func(func_dict):
    global output_file
    records = []
    jump_hist = []
    for key, v in func_dict.items():
        value = v.line_group
        for i in range(0, len(value)):
            prev_addr = 0x00
            cnt1 = 0; cnt2 = 0; cnt3 = 0; cnt4 = 0; cnt = 0
            min_addr = 0xffffffffffffffff; max_addr = 0
            trace = value[i] # rw trace per each call (begin-end)
            for rwentry in trace:
                is_first = 0
                if (prev_addr == 0x00):
                    is_first = 1
                #sline = line.split(" ")
                #curr_addr = int(sline[1], 16)
                curr_addr = rwentry.rw_addr
                dist = curr_addr - prev_addr 
                prev_addr = curr_addr
                if min_addr > curr_addr: min_addr = curr_addr
                if curr_addr > max_addr: max_addr = curr_addr
                if (is_first): continue
                if (dist > 0 and dist <= 256): cnt1 += 1
                if (dist == 0): cnt2 += 1
                if (dist >= -64): cnt3 += 1
                if (dist >= -256): cnt4 += 1

                # make dist (jump) distribution
                jump_hist.append(dist)

                cnt += 1
            if (cnt > 0):
                stat1=cnt1/cnt*100.; stat2=cnt2/cnt*100.; stat3=cnt3/cnt*100.; stat4=cnt4/cnt*100.
                #print("%s [%d]: %d/%d (%.0f%%) %d/%d (%.0f%%) %d/%d (%.0f%%) %d/%d (%.0f%%)" % (key, i, cnt1, cnt, stat1, cnt2, cnt, stat2, cnt3, cnt, stat3, cnt4, cnt, stat4))
                cnt_list = [cnt, cnt1, cnt2, cnt3, cnt4]
                minmax_list = [min_addr, max_addr]
                record = [key,i,cnt,cnt_list, minmax_list]
                records.append(record)

    records.sort(key=lambda x: -x[2])
    nRanker = int(len(records) * 0.3)
    for i in range(nRanker):
        record = records[i]
        cnt_list = record[3]
        minmax_list = record[4]
        minmax_list[0] = hex(minmax_list[0])
        minmax_list[1] = hex(minmax_list[1])
        stat1 = cnt_list[1]/cnt_list[0]*100.
        if (stat1 >= 50):
            msg = "({:.0f}%) {}\n".format(stat1, record)
            output_file.write(msg)
            #print("(%.0f%%) " % (stat1), end='')
            #print(record)

    return

def open_input_file(input_file_name):
    if input_file_name[-5:] != ".vout":
        print("input file [%s] is not .vout!" % (input_file_name))
        exit()
    linenum = file_len(input_file_name)
    print("linenum of %s: %d" % (input_file_name, linenum))

    try:
        raw_trace_file = open(input_file_name, 'r')
    except:
        sys.stderr.write("No file: %s\n" % input_file_name)
        exit(1)

    # Skip Callgrind comment
    for i in range(7):
        line = raw_trace_file.readline()

    return linenum, raw_trace_file

def open_output_file(input_file_name):
    global output_file
    if input_file_name[-5:] != ".vout":
        print("input file [%s] is not .vout!" % (input_file_name))
        exit()
    output_file_name = input_file_name[:-5] + ".pair"
    try:
        output_file = open(output_file_name, 'w')
    except:
        sys.stderr.write("File write failed: %s\n" % output_file_name)
        exit(1)

    return output_file

def check_line_type(line):
    if line[0] == "^":
        if line[1] == "f": 
            if line[3] == "b": # function call (begin)
                line_type = LINE_FUNC_BEGIN
            elif line[3] == "e": # function end
                line_type = LINE_FUNC_END
        elif line[1] == "m":
            if line[3] == "b": # malloc call
                line_type = LINE_MALLOC_CALL
            elif line[3] == "e": # free call
                line_type = LINE_FREE_CALL
        else:
            print("function line protocol error: not f or m")
            exit()
    elif line[0] != "[":
        line_type = LINE_IGNORE
    else:
        # Normal CLG R/W trace lines
        line_type = LINE_RW
    return line_type

# 지금 func_dict는 func_id로 구분하지 않고, 개별 instance의 begin-end 사이에 해당하는 것만 구분하고 있다.
def interprete_line(line_type, line):
    global func_dict, opened_funcs, malloc_dict, opened_mallocs, malloc_id, func_id, free_id
    global total_rcnt, total_wcnt, total_obj_rcnt, total_obj_wcnt
    global output_file
    global m_list, f_list

    if line_type == LINE_FUNC_BEGIN:
        func_id += 1

    elif line_type == LINE_FUNC_END:
        func_name = line[5:].replace("\n", "") 

    elif line_type == LINE_MALLOC_CALL:
        splitline = line.replace("\n", "").split(" ")
        maddr = int(splitline[3], 16)
        msize = int(splitline[2], 10)
        malloc_entry = MemEntry(malloc_id, msize, maddr, [], 0, 0)
        m_list.append(malloc_entry)
        malloc_id += 1

    elif line_type == LINE_FREE_CALL:
        splitline = line.replace("\n", "").split(" ")
        faddr = int(splitline[2], 16)
        free_entry = FreeEntry(free_id, faddr)
        f_list.append(free_entry)
        free_id += 1

    elif line_type == LINE_IGNORE:
        ignore_cnt = 0
    elif line_type == LINE_RW:
        ignore_cnt = 0
    else:
        output_file.write("line_type error")
        print("line_type error"); exit()
    return

def compare_mallocfree():
    global m_list, f_list

    sort_mlist = sorted(m_list, key=lambda x: x.maddr)
    sort_flist = sorted(f_list, key=lambda x: x.faddr)

    disjoint_mlist = sort_mlist.copy()
    disjoint_flist = sort_flist.copy()
    common_list = []

    ptr1 = 0
    ptr2 = 0
    delcnt = 0

    while ptr1 < len(sort_mlist) and ptr2 < len(sort_flist):
        if sort_mlist[ptr1].maddr == sort_flist[ptr2].faddr:
            #print(f"{sort_mlist[ptr1]} is in both lists.")
            common_list.append(sort_mlist[ptr1])
            sort_mlist[ptr1].free_id = sort_flist[ptr2].free_id
            sort_flist[ptr2].malloc_id = sort_mlist[ptr1].malloc_id

            del disjoint_mlist[ptr1 - delcnt]
            del disjoint_flist[ptr2 - delcnt]
            delcnt += 1
            ptr1 += 1; ptr2 += 1
        elif sort_mlist[ptr1].maddr < sort_flist[ptr2].faddr:
            ptr1 += 1
        else:
            ptr2 += 1

    print(f"num of mlist: {len(sort_mlist)}, num of flist: {len(sort_flist)}")
    print(f"num of dj_mlist: {len(disjoint_mlist)}, num of dj_flist: {len(disjoint_flist)}")
    print(f"num of common_list: {len(common_list)}")
    for i in range(min(len(sort_mlist), len(sort_flist))):
        m_match = 0; f_match = 0
        if sort_mlist[i].free_id != -1:
            m_match = 1
        if sort_flist[i].malloc_id != -1:
            f_match = 1

        if m_match == 1:
            print('\033[34m' + "%10x %4d [%5d %5d]\t" % (sort_mlist[i].maddr, sort_mlist[i].msize, sort_mlist[i].malloc_id, sort_mlist[i].free_id) + '\033[0m', end="")
        else:
            print("%10x %4d [%5d %5d]\t" % (sort_mlist[i].maddr, sort_mlist[i].msize, sort_mlist[i].malloc_id, sort_mlist[i].free_id), end="")
        if f_match == 1:
            print('\033[31m' + "%10x [%5d %5d]\n" % (sort_flist[i].faddr, sort_flist[i].malloc_id, sort_flist[i].free_id) + '\033[0m', end="")
        else:
            print("%10x [%5d %5d]\n" % (sort_flist[i].faddr, sort_flist[i].malloc_id, sort_flist[i].free_id), end="")

    if len(sort_mlist) > len(sort_flist):
        for j in range(i+1, len(sort_mlist)):
            m_match = 0
            if sort_mlist[j].free_id != -1:
                m_match = 1
            if m_match == 1:
                print('\033[34m' + "%10x %4d [%5d %5d]\n" % (sort_mlist[j].maddr, sort_mlist[j].msize, sort_mlist[j].malloc_id, sort_mlist[j].free_id) + '\033[0m', end="")
            else:
                print("%10x %4d [%5d %5d]\n" % (sort_mlist[j].maddr, sort_mlist[j].msize, sort_mlist[j].malloc_id, sort_mlist[j].free_id), end="")

    else:
        for j in range(i+1, len(sort_flist)):
            f_match = 0
            if sort_flist[j].malloc_id != -1:
                f_match = 1
            if f_match == 1:
                print('\033[31m' + "%10x [%5d %5d]\n" % (sort_flist[j].faddr, sort_flist[j].malloc_id, sort_flist[j].free_id) + '\033[0m', end="")
            else:
                print("%10x [%5d %5d]\n" % (sort_flist[j].faddr, sort_flist[j].malloc_id, sort_flist[j].free_id), end="")
            

    return

def read_trace_file(linenum, raw_trace_file):
    i=0
    while True:
        line = raw_trace_file.readline()
        if not line: break
        if (i % (linenum//100)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 

        # decode line 
        line_type = check_line_type(line)
        interprete_line(line_type, line)

        i += 1

    return

def analyze_object():
    global malloc_dict
    global popf_dict
    global output_file

    PopfStat = namedtuple('PopfStat', ['fname', 'rcnt_popf', 'wcnt_popf'])
    StatEntry = namedtuple('StatEntry', ['obj_id', 'obj_rcnt', 'obj_wcnt', 'obj_rwcnt', 'popf_stat_list'])
    num_objs = len(malloc_dict)
    msg = "num_objs: " + str(num_objs)
    print(msg)
    output_file.write(msg + "\n")
    i = 0
    for mid, mentry in malloc_dict.items():
        if (i % (num_objs//100)) == 0: 
            print('\r', "%.0f%% [%d/%d]" % (i/num_objs*100, i, num_objs), end='')
        popf_dict[mid] = {}
        rcnt_obj=0; wcnt_obj=0;

        for rw_entry in mentry.line_group:
            if rw_entry.rw_type == "R":
                rcnt_obj += 1
            elif rw_entry.rw_type == "W":
                wcnt_obj += 1
            else:
                output_file.write("ac_type error!")
                print("ac_type error!"); exit()
            fname = rw_entry.func_name
            if not fname in popf_dict[mid]:
                popf_dict[mid][fname] = []
            popf_dict[mid][fname].append(rw_entry)

        # rcnt_obj, wcnt_obj가 계산되었으니, MemEntry에 넣는 게 좋을듯
        mentry.rcnt = rcnt_obj
        mentry.wcnt = wcnt_obj
        #print(mentry.rcnt, mentry.wcnt)
        """
        for fname in popf_dict[mid]:
            r_rate, w_rate, rw_rate = make_stat_popf(mentry, popf_dict[mid][fname], fname)
        """

        obj_r_rate = calculate_rate(mentry.rcnt, total_obj_rcnt)
        obj_w_rate = calculate_rate(mentry.wcnt, total_obj_wcnt)
        """
        print("(obj %d/TotalObj) R: %d/%d (%.2f%%), W: %d/%d (%.2f%%)"
                % (mentry.malloc_id, mentry.rcnt, total_obj_rcnt, obj_r_rate,
                mentry.wcnt, total_obj_wcnt, obj_w_rate))
        """

        r_rate = calculate_rate(mentry.rcnt, total_rcnt)
        w_rate = calculate_rate(mentry.wcnt, total_wcnt)
        """
        print("(obj %d/TotalRW) R: %d/%d (%.2f%%), W: %d/%d (%.2f%%)"
                % (mentry.malloc_id, mentry.rcnt, total_rcnt, r_rate,
                mentry.wcnt, total_wcnt, w_rate))
        print("")
        """

        popf_stat_list = []
        for fname in popf_dict[mid]:
            rcnt_popf, wcnt_popf = make_rwcnt_popf(mentry, popf_dict[mid][fname], fname)
            popf_stat = PopfStat(fname=fname, rcnt_popf=rcnt_popf, wcnt_popf=wcnt_popf)
            popf_stat_list.append(popf_stat)
        stat_entry = StatEntry(obj_id=mentry.malloc_id, obj_rcnt=mentry.rcnt, 
                                obj_wcnt=mentry.wcnt, obj_rwcnt=(mentry.rcnt+mentry.wcnt), popf_stat_list=popf_stat_list)
        obj_stats.append(stat_entry)

        i += 1
    msg = "(Total RW to Objects) R: {}, W: {}\n".format(total_obj_rcnt, total_obj_wcnt)
    print(msg, end="")
    output_file.write(msg)

    ## RW to Objects 수로 Rank 정렬
    #  일단 analyze_object()에서 출력되는 값들을 하나로 묶어놓고, 그중 하나의 값을 기준으로 정렬하여 출력하자.
    sorted_obj_stats = sorted(obj_stats, key=lambda p: p.obj_rwcnt, reverse=True)
    for j in range(100):
        ent = sorted_obj_stats[j]
        obj_r_rate = calculate_rate(ent.obj_rcnt, total_obj_rcnt)
        obj_w_rate = calculate_rate(ent.obj_wcnt, total_obj_wcnt)
        r_rate = calculate_rate(ent.obj_rcnt, total_rcnt)
        w_rate = calculate_rate(ent.obj_wcnt, total_wcnt)
        """
        print("(obj %d/TotalObj) R: %d/%d (%.2f%%), W: %d/%d (%.2f%%)"
                % (ent.obj_id, ent.obj_rcnt, total_obj_rcnt, obj_r_rate, ent.obj_wcnt, total_obj_wcnt, obj_w_rate))
        print("(obj %d/TotalRW) R: %d/%d (%.2f%%), W: %d/%d (%.2f%%)"
                % (ent.obj_id, ent.obj_rcnt, total_rcnt, r_rate, ent.obj_wcnt, total_wcnt, w_rate))
        """
        msg="(obj {0}/TotalObj/TotalRW) R: {1}/{2}/{3} ({4:.2f}%/{5:.2f}%), W: {6}/{7}/{8} ({9:.2f}%/{10:.2f}%)\n".format(
                ent.obj_id, ent.obj_rcnt, total_obj_rcnt, total_rcnt, obj_r_rate, r_rate, 
                ent.obj_wcnt, total_obj_wcnt, total_wcnt, obj_w_rate, w_rate)
        output_file.write(msg)
        """
        print("(obj %d/TotalObj/TotalRW) R: %d/%d/%d (%.2f%%/%.2f%%), W: %d/%d/%d (%.2f%%/%.2f%%)"
                % (ent.obj_id, ent.obj_rcnt, total_obj_rcnt, total_rcnt, obj_r_rate, r_rate, 
                                ent.obj_wcnt, total_obj_wcnt, total_wcnt, obj_w_rate, w_rate))
        """
        for popf_stat in ent.popf_stat_list:
            popf_r_rate = calculate_rate(popf_stat.rcnt_popf, ent.obj_rcnt)
            popf_w_rate = calculate_rate(popf_stat.wcnt_popf, ent.obj_wcnt)
            msg="\t(obj {0}-func {1}) R: {2}/{3} ({4:.2f}%), W: {5}/{6} ({7:.2f}%)\n".format(
                    ent.obj_id, popf_stat.fname, popf_stat.rcnt_popf, ent.obj_rcnt, popf_r_rate,
                    popf_stat.wcnt_popf, ent.obj_wcnt, popf_w_rate)
            output_file.write(msg)
            """
            print("\t(obj %d-func %s) R: %d/%d (%.2f%%), W: %d/%d (%.2f%%)"
                    % (ent.obj_id, popf_stat.fname, popf_stat.rcnt_popf, ent.obj_rcnt, popf_r_rate,
                    popf_stat.wcnt_popf, ent.obj_wcnt, popf_w_rate))
            """

    analyze_func(func_dict)

def main():
    global output_file

    # Open input trace file (.vout)
    input_file_name = sys.argv[1]
    input_file_linenum, raw_trace_file = open_input_file(input_file_name)
    open_output_file(input_file_name)

    # Read input trace file
    print("read_trace_file() start")
    read_trace_file(input_file_linenum, raw_trace_file)
    print("read_trace_file() end")
    
    # Close input trace file
    raw_trace_file.close()

    # Analyze per-object trace
    #print("analyze_object() start")
    #analyze_object()
    #print("analyze_object() end")

    # Compare malloc_list vs free_list
    compare_mallocfree()



    # Close input/output file
    raw_trace_file.close()
    output_file.close()
    return

if __name__ == "__main__":
    main()

