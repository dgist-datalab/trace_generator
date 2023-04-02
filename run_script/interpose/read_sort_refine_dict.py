# refine_dict.py에서 opened_malloc (SortedDict)을 그냥 dict로 변경하고
# 끝까지 채우고 나서 Sorting 한번으로 끝내는 방식
# 기존 방식과 비교해서 성능 차이가 나는지 확인용
# opened_malloc의 탐색은 읽을 때 상시로 이루어지니 끝까지 채우고 Sorting할 순 없다. 
# 또한, opened 이므로 계속 바뀐다. 
# key, value를 pair로 묶어서 쓰는 건? 미세한 성능 이득은 있을 수 있는데 그 정도는 아니다.
# 지금 방식의 문제: Obj 크기가 커질수록 하나하나가 심하게 오래걸림.
# skip list 같은 건?
import matplotlib.pyplot as plt
import numpy as np
import sys
import cProfile
from collections import namedtuple
import bisect
from bisect import insort, bisect_left
from itertools import islice
import math
import profile

class HashSet:
    def __init__(self):
        self.set = set()
        self.last_added = None

    def __len__(self):
        return len(self.set)

    def __contains__(self, elem):
        return elem in self.set

    def __iter__(self):
        return iter(self.set)

    def append(self, elem):
        self.set.add(elem)
        self.last_added = elem

    def remove(self, elem):
        self.set.remove(elem)

    def get_last_added(self):
        return self.last_added


class SortedDict:
    def __init__(self, *args, **kwargs):
        self.keys = []
        self.values = []
        # ...

    def __getitem__(self, key):
        left, right = 0, len(self.keys) - 1

        while left <= right:
            mid = (left + right) // 2
            if self.keys[mid] < key:
                left = mid + 1
            elif self.keys[mid] > key:
                right = mid - 1
            else:
                return self.values[mid]

        raise KeyError(key)

    def __getitem__2(self, key):
        index = self.keys.index(key)
        return self.values[index]

    def __setitem__(self, key, value):
        index = bisect_left(self.keys, key)
        if index < len(self.keys) and self.keys[index] == key:
            self.values[index] = value
        else:
            self.keys.insert(index, key)
            self.values.insert(index, value)
        """
        if key in self.keys:
            index = self.keys.index(key)
            self.values[index] = value
        else:
            bisect.insort(self.keys, key)
            index = self.keys.index(key)
            self.values.insert(index, value) # don't update, add duplicated key
        """
    def __delitem__(self, key):
        left, right = 0, len(self.keys) - 1

        while left <= right:
            mid = (left + right) // 2
            if self.keys[mid] < key:
                left = mid + 1
            elif self.keys[mid] > key:
                right = mid - 1
            else:
                del self.keys[mid]
                del self.values[mid]
                return
        raise KeyError(key)

    def delete(self, key, default=None):
        try:
            del self[key]
            return True
        except KeyError:
            return default

    def __delitem__2(self, key):
        index = self.keys.index(key)
        del self.keys[index]
        del self.values[index]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

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
        index = bisect_left(self.keys, x)
        #print("index:", index)
        if index != len(self.keys) and self.keys[index] == x:
            # x is in the list, return x
            return x
        elif index == 0:
            # x is less than the smallest value in the list, return None
            return None
        else:
            # x is not in the list, return the value at the previous index
            return self.keys[index - 1]

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
#opened_funcs = HashSet()
malloc_dict = {}
#opened_mallocs = {}
opened_mallocs = SortedDict()
#opened_mallocs = {}
#opened_mallocs_list = []

malloc_id = 0
func_id = 0
popf_dict = {} # nested dict, {key: malloc_id, value: {key: func_name, value: rw_entry}}
total_rcnt = 0 # # of total read
total_wcnt = 0 # # of total write
total_obj_rcnt = 0 # # of total read to objects
total_obj_wcnt = 0 # # of total write to objects
obj_stats = []
output_file = ""
min_maddr = 0xffffffffffffffff
max_maddr = 0
max_maddr_real = 0

#class StatPopf:
    #def __init__(r_rate, w_rate, 

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
    output_file_name = input_file_name[:-5] + ".popf"
    try:
        output_file = open(output_file_name, 'w')
    except:
        sys.stderr.write("File write failed: %s\n" % output_file_name)
        exit(1)

    return output_file

def check_line_type_(line):
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

# Define lookup table for line types
LINE_TYPES = {
    "^f b": LINE_FUNC_BEGIN,
    "^f e": LINE_FUNC_END,
    "^m b": LINE_MALLOC_CALL,
    "^m e": LINE_FREE_CALL,
}

# Define function to check line type
def check_line_type(line):
    if line[0] == "[":
        return LINE_RW
    prefix = line[:4]
    if prefix in LINE_TYPES:
        return LINE_TYPES[prefix]
    else:
        return LINE_IGNORE

# 지금 func_dict는 func_id로 구분하지 않고, 개별 instance의 begin-end 사이에 해당하는 것만 구분하고 있다.
def interprete_line(line_type, line):
    global func_dict, opened_funcs, malloc_dict, opened_mallocs, malloc_id, func_id
    global total_rcnt, total_wcnt, total_obj_rcnt, total_obj_wcnt
    global min_maddr, max_maddr, max_maddr_real
    global output_file

    if line_type == LINE_FUNC_BEGIN:
        func_name = line[5:].replace("\n", "") 
        if not func_name in opened_funcs:
            opened_funcs.append(func_name)
        if not func_name in func_dict:
            # func_dict -> dict of {fname:fentry}
            # fentry: [call cnt within same fname (used as index), lines for first call, lines for second call, ...]
            func_dict[func_name] = FuncAccess(1, [[]])
        else: # 동일 func_name이 2번째 호출됐을 때부터
            # add new empty list for rw requests in dict
            func_dict[func_name].fcall_cnt += 1
            func_dict[func_name].line_group.append([])
        func_id += 1

    elif line_type == LINE_FUNC_END:
        func_name = line[5:].replace("\n", "") 
        if func_name in opened_funcs:
            opened_funcs.remove(func_name)
        else:
            if func_name[0] != "(": # e.g., (below main)
                print(opened_funcs)
                print("function line error: meet end, but no name in list. name:", func_name)

    elif line_type == LINE_MALLOC_CALL:
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
        malloc_id += 1

    elif line_type == LINE_FREE_CALL:
        splitline = line.replace("\n", "").split(" ")
        faddr = int(splitline[2], 16)
        #print(opened_mallocs)
        #if faddr in opened_mallocs:
        if opened_mallocs.delete(faddr) == None:
            msg = "free not matched: " + line + "\n"
            output_file.write(msg)

        """
        if faddr in opened_mallocs.keys: # opened_mallocs이 커서 이렇게 찾는 게 별로. 이것도 bs로 바꾸자.
            del opened_mallocs[faddr]
        else:
            # Redis에서 안 맞는 게 많다. 안 맞는 것 때문에 opened_malloc이 너무 많아지고, 이러면 obj trace를 제대로 모을 수 없다.
            msg = "free not matched: " + line
            output_file.write(msg)
            #print("line: %s" % (line))
        """

    elif line_type == LINE_IGNORE:
        ignore_cnt = 0
    elif line_type == LINE_RW:
        # 처음 trace의 RW line을 읽는 곳이니 여기서 Access로 만들어 보관해놓으면 될 것 같다.
        # 오래걸리는 원인
        # nocache trace를 읽을 땐 여기도 통과 못하고 메모리 부족해짐

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

        # 이 RW line이 어떤 obj에 해당하는 건지 검사하여 malloc_dict에 추가
        # obj에 해당하지 않는 RW였으면 그냥 넘어간다.
        # 핵심 오버헤드 구간
        # Redis에서 malloc-free 주소가 달라서 계속 opened_mallocs가 쌓이면서 발생하는 오버헤드
        # malloc-free 주소를 정확히 찾는 방법을 찾아야 함. (Redis에서 찾거나/CLG에서 근본 해결)
        # 하지만, 이 문제를 해결하더라도 프로세스 자체가 갈수록 objects 수가 많아지는 건 자연스러운 현상이므로
        # 이 방식 자체에도 문제가 있음
        #print("opened_mallocs #:", len(opened_mallocs))
        # opened_mallocs를 전체 스캔할 게 아니라, 현재의 rw_addr에 해당하는 mentry를 O(1)으로 찾을 수 있게 변경해야 함

        #for maddr, mentry in opened_mallocs.items():
        t_maddr = opened_mallocs.find_closest_key_less_than(rw_addr)
        if t_maddr != None:
            #print(list(map(hex, opened_mallocs.keys)))
            #print("rw_adrr: %x, t_maddr: %x" % (rw_addr, t_maddr))
            maddr = t_maddr; mentry = opened_mallocs[maddr]
            if (maddr <= rw_addr) and (rw_addr < maddr+mentry.msize):
                # True: This RW is RW to Object
                #print("Found!")
                #print("rw_addr: %x, t_maddr: %x, maddr: %x, maddr_mentry.msize: %x" % (rw_addr, t_maddr, maddr, maddr+mentry.msize))
                func_name = opened_funcs[-1]
                #func_name = opened_funcs.get_last_added()
                rw_entry.obj_id = mentry.malloc_id
                rw_entry.func_name = func_name # 이 RW의 caller로서 가장 가까운 함수를 가정
                malloc_dict[mentry.malloc_id].line_group.append(rw_entry)
                if rw_entry.rw_type == "R":
                    total_obj_rcnt += 1
                elif rw_entry.rw_type == "W":
                    total_obj_wcnt += 1
                #exit()

        """
        i=0
        for maddr, mentry in opened_mallocs.iter_from_key(t_maddr):
            # 현재 살아있는 모든 obj들의 주소 범위와 비교
            # 0개 or 1개일테니 if문에서 break을 거는 게 좋다.
            print("rw_addr: %x, t_maddr: %x, maddr: %x, maddr_mentry.msize: %x" % (rw_addr, t_maddr, maddr, maddr+mentry.msize))
            if i == 1:
                print("end")
                exit()
            if (maddr <= rw_addr) and (rw_addr < maddr+mentry.msize):
                # True: This RW is RW to Object
                print("Found!")
                func_name = opened_funcs[-1]
                rw_entry.obj_id = mentry.malloc_id
                rw_entry.func_name = func_name # 이 RW의 caller로서 가장 가까운 함수를 가정
                malloc_dict[mentry.malloc_id].line_group.append(rw_entry)
                if rw_entry.rw_type == "R":
                    total_obj_rcnt += 1
                elif rw_entry.rw_type == "W":
                    total_obj_wcnt += 1

                break
            i += 1
        """
    else:
        output_file.write("line_type error")
        print("line_type error"); exit()

    return
        

def read_trace_file(linenum, raw_trace_file):
    i=0
    # 심하게 오래걸리는 상태
    # 1) line이 많아서 / 2) 해석해서 malloc_dict/func_dict 생성이 오래걸려서
    # RW를 읽을 때마다, 현재 열린 함수들을 모두 읽어서 그 함수들에게 RW 정보를 추가하고
    # 또한 현재 존재하는 Object들을 모두 뒤져서 이 RW가 어떤 Object에 해당하는 건지 검사한다.
    # -> 2) 작업이 꽤 무거워서 오래걸릴 수 있고, SPECCPU 실험했을 때 메모리 부족으로 터져버렸다.
    # 일단 모든 함수 호출을 다 dict로 만들다보니 너무 무거운데.. 함수를 빼고 보는 옵션을 추가해야 하나?
    # cProfile로 확인하니, 대부분의 시간이 interprete_line에서 소요됨
    print("Read trace file to memory!")
    raw_trace = raw_trace_file.read()
    lines = raw_trace.split("\n")
    print("Trace loading ends")

    for line in lines:
        if not line: break
        if (i % (linenum//100)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
            print_numdict()
        """
        if (i // (linenum//100) >= 5):
            print("read 5%. read stopped.")
            break
        """

        # decode line 
        line_type = check_line_type(line)
        interprete_line(line_type, line)

        #cProfile.run('interprete_line(line_type, line)', globals(), {'line_type': line_type})
        #globals_dict = globals().copy()
        #globals_dict.update(locals())
        #cProfile.run('interprete_line(line_type, line)', globals_dict)

        #if line_type != LINE_IGNORE:
            #profile.run('interprete_line({}, {})'.format(line_type, line))
        #my_locals = {'line_type': line_type}
        #cProfile.run('interprete_line', my_locals, sort='tottime')

        i += 1

    return

def check_rwaddr_in_maddr_minmax(linenum, raw_trace_file):
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
            if (min_maddr <= rw_addr) and (rw_addr <= max_maddr_real):
                rwaddr_in_maddr_minmax += 1

    print("rwaddr_in_maddr_minmax: %d / Total RW cnt: %d\n" % (rwaddr_in_maddr_minmax, total_rcnt + total_wcnt))
    return

def analyze_object():
    global malloc_dict
    global popf_dict
    global output_file
    global max_maddr, max_maddr_real

    PopfStat = namedtuple('PopfStat', ['fname', 'rcnt_popf', 'wcnt_popf'])
    StatEntry = namedtuple('StatEntry', ['obj_id', 'obj_rcnt', 'obj_wcnt', 'obj_rwcnt', 'popf_stat_list', 'start_addr', 'end_addr'])
    num_objs = len(malloc_dict)
    msg = "num_objs: " + str(num_objs)
    print(msg)
    output_file.write(msg + "\n")
    i = 0
    for mid, mentry in malloc_dict.items():
        if (i % (math.ceil(num_objs/100))) == 0: 
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
                                obj_wcnt=mentry.wcnt, obj_rwcnt=(mentry.rcnt+mentry.wcnt), popf_stat_list=popf_stat_list, start_addr=mentry.maddr, end_addr=mentry.maddr+mentry.msize-1)
        obj_stats.append(stat_entry)

        i += 1
    msg = "(Total RW to Objects) R: {}, W: {}  |  min_maddr: {:x}, max_maddr: {:x} (~{:x})\n".format(total_obj_rcnt, total_obj_wcnt, min_maddr, max_maddr, max_maddr_real)
    print(msg, end="")
    output_file.write(msg)

    ## RW to Objects 수로 Rank 정렬
    #  일단 analyze_object()에서 출력되는 값들을 하나로 묶어놓고, 그중 하나의 값을 기준으로 정렬하여 출력하자.
    sorted_obj_stats = sorted(obj_stats, key=lambda p: p.obj_rwcnt, reverse=True)
    for j in range(min(100, len(sorted_obj_stats))):
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
        msg="(obj {0}/TotalObj/TotalRW) R: {1}/{2}/{3} ({4:.2f}%/{5:.2f}%), W: {6}/{7}/{8} ({9:.2f}%/{10:.2f}%) | {11:8x}-{12:8x}\n".format(
                ent.obj_id, ent.obj_rcnt, total_obj_rcnt, total_rcnt, obj_r_rate, r_rate, 
                ent.obj_wcnt, total_obj_wcnt, total_wcnt, obj_w_rate, w_rate, ent.start_addr, ent.end_addr)
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

    # Analyze per-object trace
    print("analyze_object() start")
    analyze_object()
    print("analyze_object() end")

    #check_rwaddr_in_maddr_minmax(input_file_linenum, raw_trace_file)
    # Close input/output file
    raw_trace_file.close()
    output_file.close()
    return

if __name__ == "__main__":
    main()

