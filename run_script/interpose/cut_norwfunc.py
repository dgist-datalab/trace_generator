# Redis obj's zfamily classification per caller name
# Make [.popf] and [.pot] file from the input [.vout]

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
LINE_ZFAMILY_CALL=6

# Initialize global sequence types & variables
func_dict = {}
#opened_funcs = []
#opened_funcs = HashSet()
opened_funcs = {}
malloc_dict = {}
#opened_mallocs = {}
opened_mallocs = SortedDict()
#opened_mallocs = {}
#opened_mallocs_list = []

popf_dict = {} # nested dict, {key: malloc_id, value: {key: func_name, value: rw_entry}}
output_file = ""

def print_numdict():
    global malloc_dict, func_dict, opened_funcs, opened_mallocs, popf_dict
    print("(num) malloc_dict: %d, func_dict: %d, opened_funcs: %d, opened_mallocs: %d, popf_dict: %d" % 
            (len(malloc_dict), len(func_dict), len(opened_funcs), len(opened_mallocs), len(popf_dict)))

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

class OpenedFuncEntry:
    def __init__(self, b_linenum, stackcnt=0, meet_rw=0):
        self.stackcnt = stackcnt
        self.meet_rw = meet_rw
        self.b_linenum = b_linenum

def calculate_rate(cnt, total):
    if total == 0:
        rate = float("nan")
    else:
        rate = cnt/total * 100
    return rate

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

    return linenum, raw_trace_file

def open_output_file(input_file_name):
    global output_file
    if input_file_name[-5:] != ".vout":
        print("input file [%s] is not .vout!" % (input_file_name))
        exit()
    output_file_name = input_file_name[:-5] + "_norwcut.vout"
    try:
        output_file = open(output_file_name, 'w')
    except:
        sys.stderr.write("File write failed: %s\n" % output_file_name)
        exit(1)

    return output_file

# Define lookup table for line types
LINE_TYPES = {
    "^f b": LINE_FUNC_BEGIN,
    "^f e": LINE_FUNC_END,
    "^m b": LINE_MALLOC_CALL,
    "^m e": LINE_FREE_CALL,
    "^z b": LINE_ZFAMILY_CALL,
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

# read trace file and make skip_linenums list
def read_trace_file(linenum, raw_trace_file):
    i=0
    print("Read trace file to memory!")
    raw_trace = raw_trace_file.read()
    lines = raw_trace.split("\n")
    print("Trace loading ends")

    skip_linenums = set()
    #"""
    for j in range(len(lines)):
        line = lines[j]
        if not line: break
        if (i % (linenum//100)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
            print_numdict()

        # 이 방식은 f e가 멀리 있는 경우 O(n*2)이 되므로 unfeasible하다.
        # 스캔 한 번으로 끝나게 만들어야 함
        # RW를 만나면, 이전의 f b들은 모두 skip 대상에서 제외되어 live 대상이 된다.
        # f e를 만났을 때, 그 f가 skip 대상에 있으면 skip 대상 list에서 빼고 f e를 스킵한다.

        # opened_func를 만들어서, f e를 만났을 때 짝인 f b를 찾고, RW를 만난 전적이 있다면 
        # live로 표시하고 RW를 만난 전적이 없다면 skip 대상에 넣는다.
        # 이때 opened_func는 한 함수가 recursive하게 호출되는 경우를 고려할 수 있어야 하는데,
        # opened_func의 원소는 현재 몇 번 중첩되었는지 유지하고 있으면 된다.

        # opened_func는 HashSet으로 구현해놨었는데, 어떻게 응용?
        # HashSet이 아니라 dict로 해야 key: fname, value: stackcnt, meet_rw
        line_type = check_line_type(line)
        if line_type == LINE_FUNC_BEGIN:
            func_name = line[5:].replace("\n", "") 
            if not func_name in opened_funcs:
                opened_funcs[func_name] = OpenedFuncEntry(b_linenum=j) # opened_funcs: the list of funcs that will be skipped
            else:
                opened_funcs[func_name].stackcnt += 1
        elif line_type == LINE_RW:
            # 이러면 opened_funcs가 많을 경우 RW 만날 때마다 시간이 많이 지체된다.
            # RW 만날 때 opened_funcs의 items들을 다 빼 버려도 되나? 어차피 추후 f e를 만나도 skip할 일이 없을 것이고,
            # f e를 만났을 때, opened_funcs에 있는 짝 f의 b와 e에 대한 linenum을 skip_linenums에 추가하고 빼버리면 된다.
            # 
            opened_funcs.clear()
            #for fname, entry in opened_funcs.items():
                #entry.meet_rw = 1
        elif line_type == LINE_FUNC_END:
            func_name = line[5:].replace("\n", "") 
            # opened_funcs에 이 func가 있다면, RW를 안 만났던 f이므로 skip 대상이 된다.
            # func가 없다면, RW를 만나서 지워졌던 것이므로 trace에 잔존해야 하는 f이다.

            # 그런데, recursive한 func에 대해서 추가적인 이슈가 있어 보이는데.
            # RW 만났을 때 그냥 clear해도 되나? end 만났을 때는? stackcnt를 어떻게 사용해야 하지?
            # 몇 번 Recursive하게 쌓였던 간에 한 번이라도 RW를 만나면 잔존 대상이 되므로 e를 만났을 때 액션을 취할 필요가 없으니 지워도 된다.

            ofentry = opened_funcs.get(func_name)
            if ofentry:
                skip_linenums.add(ofentry.b_linenum)
                skip_linenums.add(j) # j: linenum of f e
                del opened_funcs[func_name]
                #print(ofentry.b_linenum+1, j+1) # linenum of fb-fe

        i+=1
    #"""
    """
        # 제외된 f의 f e의 경우, f를 기억해 두고 f e를 만났을 때 live 대상인지 
    for j in range(len(lines)):
        line = lines[j]
        if not line: break
        if (i % (linenum//100)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
            print_numdict()
        line_skip = False
        line_type = check_line_type(line)
        if line_type == LINE_FUNC_BEGIN:
            func_name = line[5:].replace("\n", "") 
            yesrw_func = 0
            for k in range(j+1, len(lines)):
                next_line = lines[k]
                next_line_type = check_line_type(next_line)
                if next_line_type == LINE_RW:
                    yesrw_func = 1
                elif check_line_type(next_line) == LINE_FUNC_END:
                    next_func_name = next_line[5:].replace("\n", "")
                    if func_name == next_func_name:
                        if yesrw_func == 0:
                            line_skip = True
                            skip_linenums.add(j)
                            skip_linenums.add(k)
                            #print(j+1, k+1)
                        break
        i+=1
    #"""
    # skip_linenums is complete. 
    # 방법 1: skip_linenums list를 정렬하고 head만 검사하기
    # 방법 2: skip_linenums set 자체에서 해당하는 게 있는지 검사하기
    # lines는 크고 skip_linenums가 작다면 방법 2가 좋을 수 있다.

    skip_cnt = 0; nonskip_cnt = 0
    for i, line in enumerate(lines):
        if i not in skip_linenums:
            output_file.write(line+"\n")
            nonskip_cnt += 1
        else:
            #output_file.write("(skipped)"+line+"\n")
            skip_cnt += 1

    print("skip_cnt: %d, nonskip_cnt: %d, line remaining rate: 100%% -> %.1f%%" % (skip_cnt, nonskip_cnt, calculate_rate(nonskip_cnt, skip_cnt+nonskip_cnt)))

    return skip_linenums

def main():
    global output_file

    # Open input trace file (.vout)
    input_file_name = sys.argv[1]
    input_file_linenum, raw_trace_file = open_input_file(input_file_name)
    open_output_file(input_file_name)

    # Read input trace file
    print("read_trace_file() start")
    skip_linenums = read_trace_file(input_file_linenum, raw_trace_file)
    print("read_trace_file() end")

    # Close input/output file
    output_file.close()
    raw_trace_file.close()
    return

if __name__ == "__main__":
    main()

