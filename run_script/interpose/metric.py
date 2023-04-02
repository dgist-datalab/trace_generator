import sys
import numpy as np
import itertools

"""
    방법 1. popf 생성 시 metric도 같이 측정
        편하지만 metric 계산을 조금만 바꾸려고 해도 popf부터 다시 생성해야 해서 시간 비효율적
    방법 2. popf 생성할 때, Per-object trace 및 관련 데이터를 File로 따로 저장.
        File로 다시 저장하고 읽는 과정이 번거롭긴 하지만, Metric 측정과 별개로 이루어지므로 효율적임
        그런데, per-object만 기준? per-function이 남아있다. 
        RWEntry Class에는 function name에 대한 정보도 있으므로 그걸 전부 input으로 넣으면 될 것. (pot)
"""

class RWEntry:
    def __init__(self, rw_type, rw_addr, rw_timestamp, func_name=None, obj_id=-1, func_id=-1):
        self.obj_id = obj_id
        self.rw_type = rw_type
        self.rw_addr = rw_addr
        self.rw_timestamp = rw_timestamp
        self.func_name = func_name
        self.func_id = func_id
        
class MemEntry:
    def __init__(self, malloc_id, msize, maddr, line_group, addr_set, rcnt, wcnt):
        self.malloc_id = malloc_id
        self.msize = msize
        self.maddr = maddr
        self.line_group = line_group # a list of rw_entry
        self.addr_set = addr_set # a list of rw_addr
        self.rcnt = rcnt
        self.wcnt = wcnt

def pearson_correlation_coefficient(x, y):
    """Calculate Pearson's correlation coefficient between two sequences"""
    
    # calculate means of x and y
    mean_x = np.mean(x)
    mean_y = np.mean(y)

    # calculate standard deviations of x and y
    std_x = np.std(x)
    std_y = np.std(y)

    # calculate covariance of x and y
    cov_xy = np.cov(x, y)[0][1]

    # calculate Pearson's correlation coefficient
    r = cov_xy / (std_x * std_y)

    return r

"""
# create two example sequences of memory access addresses
seq1 = [0x100, 0x200, 0x300, 0x400, 0x500]
seq2 = [0x100, 0x150, 0x200, 0x250, 0x300]

# calculate Pearson's correlation coefficient between the two sequences
r = pearson_correlation_coefficient(seq1, seq2)

print("Pearson's correlation coefficient:", r)
"""

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def open_input_file(input_file_name):
    if input_file_name[-4:] != ".pot": # object/function out
        print("input file [%s] is not .pot!" % (input_file_name))
        exit()
    linenum = file_len(input_file_name)
    print("linenum of %s: %d" % (input_file_name, linenum))

    try:
        input_file = open(input_file_name, 'r')
    except:
        sys.stderr.write("No file: %s\n" % input_file_name)
        exit(1)

    # Skip Callgrind comment
    #for i in range(7):
        #line = raw_trace_file.readline()

    return linenum, input_file

def find_max_min(dict):
    max_val = float('-inf')
    min_val = float('inf')
    for value in dict.values():
        if value > max_val:
            max_val = value
        if value < min_val:
            min_val = value
    return (max_val, min_val)

def calculate_reuse_distance(addresses):
    last_access = {}
    max_distance = {}

    for i, address in enumerate(addresses):
        if address in last_access:
            distance = i - last_access[address]
            if address in max_distance:
                max_distance[address] = max(max_distance[address], distance)
            else:
                max_distance[address] = distance
        last_access[address] = i

    if len(max_distance) == 0:
        return None
    #print(max_distance)
    max_reuse, min_reuse = find_max_min(max_distance)
    #max_reuse = max(max_distance.values(), default=0)
    avg_reuse = sum(max_distance.values()) / len(max_distance)
    return (avg_reuse, max_reuse, min_reuse)

def calculate_metrics(mentry1, mentry2):
    # n: numRW, m: numObj -> O(nlogn * m*2)
    reuse_nonecnt = 0

    #pearson_correlation_coefficient(mentry1, mentry2) # mentry 2개를 넣어야 하는데.
    reuse1 = calculate_reuse_distance(mentry1.addr_set)
    reuse2 = calculate_reuse_distance(mentry2.addr_set)
    return reuse1, reuse2

    if (reuse1 != None) and (reuse2 != None):
        print(reuse1, reuse2)
    else:
        reuse_nonecnt += 1

    return reuse_nonecnt, cnt

    #reuse_avg1, reuse_max1, reuse_min1 = calculate_reuse_distance(mentry1.addr_set)
    #reuse_avg2, reuse_max2, reuse_min2 = calculate_reuse_distance(mentry2.addr_set)
    

    return

def read_trace_file(linenum, pot_file):
    i=0
    print("Read trace file to memory!")
    pot = pot_file.read()
    lines = pot.split("\n")
    print("Pot Trace loading ends")

    # Read [.pot] metadata
    pot_meta_line = lines[0]
    num_objs = int(pot_meta_line, 10)

    # Create mentry array
    mentry_list = [None] * num_objs

    # Fill mentry array
    # 만약 trace_metadata_line이 여러 줄이라면, 그게 몇 줄인지도 첫 줄에 적어놓아야 함
    j = 1
    #print("len:", len(lines))
    while j < len(lines)-1:
        objline = lines[j]
        #s_objline = objline[:-1].split(" ") # erase "\n" (objline[-1])
        s_objline = objline.split(" ") 
        #print(s_objline)
        obj_id = int(s_objline[0], 10)
        obj_size = int(s_objline[1], 10)
        obj_addr = int(s_objline[2], 16)
        obj_rcnt = int(s_objline[3], 10)
        obj_wcnt = int(s_objline[4], 10)
        mentry = MemEntry(obj_id, obj_size, obj_addr, [], [], 0, 0)
        j += 1

        metaline = lines[j]
        num_rw = int(metaline, 10)
        j += 1

        for k in range(0, num_rw):
            rwline = lines[j]
            splitline = rwline.replace('\n', '').split(" ")
            rw_type = splitline[0]
            rw_addr = int(splitline[1], 16)
            rw_time = float(splitline[2])
            f_name = splitline[3]
            f_id = int(splitline[4], 10)
            rw_entry = RWEntry(rw_type=rw_type, rw_addr=rw_addr, rw_timestamp=rw_time, func_name=f_name, func_id=f_id)
            mentry.line_group.append(rw_entry)
            mentry.addr_set.append(rw_addr)
            j += 1

        mentry_list[obj_id] = mentry
        #print("j:", j, lines[j])
        #j += 1

    reuse_nonecnt = 0
    for mentry in mentry_list:
        mentry.reuse = calculate_reuse_distance(mentry.addr_set)
        if mentry.reuse != None:
            print(mentry.reuse)
        else:
            reuse_nonecnt += 1

    print("reuse nonecnt: %d/%d" % (reuse_nonecnt, num_objs))

    # Select two mentry for comparison
    # 단순히 C(m, 2)만큼 하면 되긴 하는데, '비슷한 것들을 Grouping'하려면 약간 다르다.
    # 1 1 0 0 1 0 0 0 0 .. > 1이 다른 것과 비교한 결과 1, 2, 5가 한 Group 구성
    #   1 0 0 - 0 0 0 0 .. > 2는 5와 동일 Group이므로 5와는 비교할 필요가 없음
    #                            (나중에 검증용으로 따로 비교)

    """
    comb = itertools.combinations(mentry_list, 2)
    cnt = 0
    reuse_nonecnt = 0
    for pair in comb:
        # 같은 Group인지 먼저 검사


        # 두 mentry의 metric 측정
        reuse1, reuse2 = calculate_metrics(pair[0], pair[1])
        if (reuse1 != None) and (reuse2 != None):
            print(reuse1, reuse2)
        else:
            reuse_nonecnt += 1

        # metric 결과에 따라 같은 Group으로 넣을지 결정
        cnt += 1

    print("reuse none count: %d/%d" % (reuse_nonecnt, cnt))
    for line in lines:
        if not line: break
        if (i % (linenum//100)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 

        


        # decode line 
        line_type = check_line_type(line)
        interprete_line(line_type, line)
    """

def main():
    # Open input trace file (.pot)
    input_file_name = sys.argv[1]
    input_file_linenum, pot_file = open_input_file(input_file_name)

    # Read input trace file
    print("read_trace_file() start")
    read_trace_file(input_file_linenum, pot_file)
    print("read_trace_file() end")

    # Analyze per-object trace
    #print("analyze_object() start")
    #analyze_object()
    #print("analyze_object() end")

    #check_rwaddr_in_maddr_minmax(input_file_linenum, raw_trace_file)
    # Close input/output file
    pot_file.close()
    #output_file.close()
    return

if __name__ == "__main__":
    main()

