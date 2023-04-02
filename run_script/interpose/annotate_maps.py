import matplotlib.pyplot as plt
import numpy as np
import sys
import cProfile
from collections import namedtuple
import bisect
from bisect import insort, bisect_left
from itertools import islice

# RW trace (=.vout)와 /proc/pid/maps를 input으로 받아서 maps에 각 영역으로 향한 RW cnt를 표기하는 스크립트
# input: [.vout] file, /proc/pid/maps file

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
#opened_mallocs = SortedDict()
maps = []

malloc_id = 0
func_id = 0
popf_dict = {} # nested dict, {key: malloc_id, value: {key: func_name, value: rw_entry}}
total_rcnt = 0 # # of total read
total_wcnt = 0 # # of total write
total_obj_rcnt = 0 # # of total read to objects
total_obj_wcnt = 0 # # of total write to objects
obj_stats = []
output_file = ""
RW_cnt = 0
min_maddr = 0xffffffffffffffff
max_maddr = 0
max_maddr_real = 0

def print_numdict():
    global malloc_dict, func_dict, opened_funcs, opened_mallocs, popf_dict
    print("(num) malloc_dict: %d, func_dict: %d, opened_funcs: %d, opened_mallocs: %d, popf_dict: %d" % 
            (len(malloc_dict), len(func_dict), len(opened_funcs), len(opened_mallocs), len(popf_dict)))

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
    def __init__(self, malloc_id, msize, maddr, line_group, rcnt, wcnt):
        self.malloc_id = malloc_id
        self.msize = msize
        self.maddr = maddr
        self.line_group = line_group
        self.rcnt = rcnt
        self.wcnt = wcnt

class MapEntry:
    def __init__(self, saddr, eaddr, perms, offset, dev, inode, pathname, cnt=0, rcnt=0, wcnt=0, malloc_cnt=0):
        self.saddr = saddr
        self.eaddr = eaddr
        self.perms = perms
        self.offset = offset
        self.dev = dev
        self.inode = inode
        self.pathname = pathname
        self.cnt = cnt
        self.rcnt = rcnt
        self.wcnt = wcnt
        self.malloc_cnt = malloc_cnt


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

    # Open /proc/pid/maps file, which was copied from /proc/pid
    temp = input_file_name.split("/")
    temp[-1] = "maps_" + temp[-1].split(".")[0]
    maps_file_name = "/".join(temp)
    try:
        maps_file = open(maps_file_name, 'r')
    except:
        sys.stderr.write("No file: %s\n" % maps_file_name)
        exit(1)

    return linenum, raw_trace_file, maps_file

def open_output_file(input_file_name):
    global output_file
    if input_file_name[-5:] != ".vout":
        print("input file [%s] is not .vout!" % (input_file_name))
        exit()
    output_file_name = input_file_name[:-5] + ".popf"
    try:
        output_file = open(output_file_name, 'w')
    except:
        sys.stderr.write("File write failed: %s\n" % output_file_name)
        exit(1)

    return output_file

def print_maps():
    global maps
    global RW_cnt

    print("Total RW cnt: %d" % (RW_cnt))
    print("total_rcnt: %d, total_wcnt: %d" % (total_rcnt, total_wcnt))
    print("min_maddr: %x, max_maddr: %x, max_maddr+size: %x" % (min_maddr, max_maddr, max_maddr_real))

    heap_total_rwcnt = 0

    max_pathlen = 0
    for m in maps:
        max_pathlen = max(max_pathlen, len(m.pathname))
        if m.malloc_cnt >= 1:
            heap_total_rwcnt += m.cnt
        """
        splitline = line.replace("\n", "").split(" ")
        maddr = int(splitline[3], 16)
        msize = int(splitline[2], 10)
        #malloc_entry = [malloc_id, msize, maddr, []]
        malloc_entry = MemEntry(malloc_id, msize, maddr, [], 0, 0)
        malloc_dict[malloc_id] = malloc_entry
        opened_mallocs[maddr] = malloc_entry
        min_maddr = min(min_maddr, maddr)
        max_maddr = max(max_maddr, maddr)
        max_maddr_real = max(max_maddr_real, maddr + msize - 1)
        """

    print("Total RW cnt to Heap segments: %d (%.2f%%)" % (heap_total_rwcnt, heap_total_rwcnt/RW_cnt*100))
    for m in maps:
        print("%8x-%8x %4s %8x %6s %8d {:<{}} | %d (%d/%d) (%d)".format(m.pathname, max_pathlen) % (
            m.saddr, m.eaddr, m.perms, m.offset, m.dev, 
            m.inode, m.cnt, m.rcnt, m.wcnt, m.malloc_cnt))

    return

def check_malloc_in_maps(linenum, raw_trace_file):
    raw_trace_file.seek(0)
    maps_malloc_cnt = 0
    while True:
        line = raw_trace_file.readline()
        if not line: break
        line_type = check_line_type(line)
        if line_type == LINE_MALLOC_CALL:
            splitline = line.replace("\n", "").split(" ")
            maddr = int(splitline[3], 16)
            msize = int(splitline[2], 10)
            for m in maps:
                if (m.saddr <= maddr) and (maddr+msize < m.eaddr):
                    m.malloc_cnt += 1
                    maps_malloc_cnt += 1
                    break

    
    print("Total malloc cnt in the maps: %d" % (maps_malloc_cnt))
    return
    
    # 없는거
"""
def check_rwaddr_in_maps(linenum, raw_trace_file):
    global maps

    raw_trace_file.seek(0)
    rwaddr_in_maddr_minmax = 0
    while True:
        line = raw_trace_file.readline()
        if not line: break
        line_type = check_line_type(line)
        if line_type == LINE_RW:
            sline = line.replace('[', '').replace(']', '').replace('\n', '').split(" ")
            rw_type = sline[0]
            rw_addr = int(sline[1], 16)

            # 지도 돌면서 카운트
            for m in maps:

            if (min_maddr <= rw_addr) and (rw_addr <= max_maddr_real):
                rwaddr_in_maddr_minmax += 1

    print("rwaddr_in_maddr_minmax: %d / Total RW cnt: %d\n" % (rwaddr_in_maddr_minmax, total_rcnt + total_wcnt))
    return
"""

def prepare_maps(maps_file):
    global maps

    #MapEntry = namedtuple('MapEntry', ['saddr','eaddr','perms','offset','dev','inode','pathname','cnt','rcnt','wcnt'])
    while True:
        line = maps_file.readline()
        if not line: break
        sline = line.replace("\n", "").split()
        temp = sline[0].split('-')
        sline = temp + sline[1:]
        saddr = int(sline[0], 16)
        eaddr = int(sline[1], 16)
        perms = sline[2]
        offset = int(sline[3], 16)
        dev = sline[4]
        inode = int(sline[5], 10)
        print(sline)
        if len(sline) > 6:
            pathname = sline[6]
        else:
            pathname = ""

        map_entry = MapEntry(saddr=saddr,eaddr=eaddr,perms=perms,offset=offset,dev=dev,inode=inode,pathname=pathname,cnt=0,rcnt=0,wcnt=0)
        maps.append(map_entry)
    return

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
    global func_dict, opened_funcs, malloc_dict, opened_mallocs, malloc_id, func_id
    global total_rcnt, total_wcnt, total_obj_rcnt, total_obj_wcnt
    global output_file
    global RW_cnt
    global min_maddr, max_maddr, max_maddr_real

    if line_type == LINE_FUNC_BEGIN:
        func_id += 1

    elif line_type == LINE_FUNC_END:
        func_name = line[5:].replace("\n", "") 

    elif line_type == LINE_MALLOC_CALL:
        splitline = line.replace("\n", "").split(" ")
        maddr = int(splitline[3], 16)
        msize = int(splitline[2], 10)
        #malloc_entry = [malloc_id, msize, maddr, []]
        #malloc_entry = MemEntry(malloc_id, msize, maddr, [], 0, 0)
        #malloc_dict[malloc_id] = malloc_entry
        #opened_mallocs[maddr] = malloc_entry
        min_maddr = min(min_maddr, maddr)
        max_maddr = max(max_maddr, maddr)
        max_maddr_real = max(max_maddr_real, maddr + msize - 1)
        malloc_id += 1

    elif line_type == LINE_FREE_CALL:
        splitline = line.replace("\n", "").split(" ")

    elif line_type == LINE_IGNORE:
        ignore_cnt = 0

    elif line_type == LINE_RW:
        RW_cnt += 1
        sline = line.replace('[', '').replace(']', '').replace('\n', '').split(" ")
        rw_type = sline[0]
        rw_addr = int(sline[1], 16)
        #rw_time = float(sline[2])
        rw_time = 0
        rw_entry = RWEntry(rw_type=rw_type, rw_addr=rw_addr, rw_timestamp=rw_time) 
        if rw_type == "R":
            total_rcnt += 1
        elif rw_type == "W":
            total_wcnt += 1

        return rw_entry





        # 함수 단위의 구분을 위해 필요한 func_dict 채우기
        # 열린 모든 함수들에게 이 RW를 중복해서 저장해놓기
        # per-object-per-function에서는 필요 없음
        #print("opened_fucs #:", len(opened_funcs))
        for fname in opened_funcs:
            fcall_idx = func_dict[fname].fcall_cnt - 1
            #print(fcall_idx)
            #print(func_dict[fname].line_group)
            #print(func_dict[fname].line_group[0])
            func_dict[fname].line_group[fcall_idx].append(rw_entry)

        #for maddr, mentry in opened_mallocs.items():
        t_maddr = opened_mallocs.find_closest_key_less_than(rw_addr)
        if t_maddr != None:
            maddr = t_maddr; mentry = opened_mallocs[maddr]
            if (maddr <= rw_addr) and (rw_addr < maddr+mentry.msize):
                # True: This RW is RW to Object
                #print("Found!")
                #print("rw_addr: %x, t_maddr: %x, maddr: %x, maddr_mentry.msize: %x" % (rw_addr, t_maddr, maddr, maddr+mentry.msize))
                func_name = opened_funcs[-1]
                rw_entry.obj_id = mentry.malloc_id
                rw_entry.func_name = func_name # 이 RW의 caller로서 가장 가까운 함수를 가정
                malloc_dict[mentry.malloc_id].line_group.append(rw_entry)
                if rw_entry.rw_type == "R":
                    total_obj_rcnt += 1
                elif rw_entry.rw_type == "W":
                    total_obj_wcnt += 1
                #exit()

    else:
        output_file.write("line_type error")
        print("line_type error"); exit()

    return
        

def read_trace_file(linenum, raw_trace_file):
    nomap_cnt = 0; nomap_rcnt = 0; nomap_wcnt = 0
    i=0
    while True:
        line = raw_trace_file.readline()
        if not line: break
        if (i % (linenum//100)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
            #print_numdict()

        # decode line 
        line_type = check_line_type(line)
        #if not ((line_type == LINE_RW) or (line_type == LINE_MALLOC_CALL)):
        if (line_type != LINE_RW) :
            if (line_type == LINE_MALLOC_CALL):
               interprete_line(line_type, line) 
            continue
        rw_entry = interprete_line(line_type, line)

        # rw_entry의 addr이 maps의 어느 entry에 해당하는지 검사
        #print(maps)
        for map_entry in maps:
            find_map_entry = 0
            if (map_entry.saddr <= rw_entry.rw_addr) and (rw_entry.rw_addr < map_entry.eaddr):
                map_entry.cnt += 1
                if rw_entry.rw_type == "R":
                    map_entry.rcnt += 1
                elif rw_entry.rw_type == "W":
                    map_entry.wcnt += 1
                else:
                    print("Error in rw_type!", rw_entry.rw_type)
                    exit()
                find_map_entry = 1
                break

        if (find_map_entry == 0):
            nomap_cnt += 1
            if rw_entry.rw_type == "R":
                nomap_rcnt += 1
            elif rw_entry.rw_type == "W":
                nomap_wcnt += 1
            else:
                print("Error in rw_type!", rw_entry.rw_type)
                exit()

        i += 1

    total_me_cnt = 0; total_me_rcnt = 0; total_me_wcnt = 0
    for map_entry in maps:
        total_me_cnt += map_entry.cnt
        total_me_rcnt += map_entry.rcnt
        total_me_wcnt += map_entry.wcnt

    print("total RWcnt to map_entry: %d, rcnt: %d, wcnt: %d" % (total_me_cnt, total_me_rcnt, total_me_wcnt))
    print("total RWcnt to nomap: %d, rcnt: %d, wcnt: %d" % (nomap_cnt, nomap_rcnt, nomap_wcnt))

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
            print_numdict()
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
    input_file_linenum, raw_trace_file, maps_file = open_input_file(input_file_name)
    #open_output_file(input_file_name)

    # Prepare /proc/pid/maps before classfication
    prepare_maps(maps_file)

    # Read input trace file
    print("read_trace_file() start")
    read_trace_file(input_file_linenum, raw_trace_file)
    print("read_trace_file() end")

    check_malloc_in_maps(input_file_linenum, raw_trace_file)
    
    # Close input trace file
    raw_trace_file.close()

    # Print maps 
    print_maps()

    # Analyze per-object trace
    #print("analyze_object() start")
    #analyze_object()
    #print("analyze_object() end")


    # Close input/output file
    raw_trace_file.close()
    #output_file.close()
    return

if __name__ == "__main__":
    main()

