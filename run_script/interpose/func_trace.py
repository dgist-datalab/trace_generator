import matplotlib.pyplot as plt
import numpy as np
import sys

# valgrind에 function begin-end 시 print하는 코드를 추가해 놓았을 때,
# 그 정보를 .vout에서 읽어서 구분하는 스크립트
# input: [.vout] file
# output: stdout 

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

# 특정 Object에 접근하는 Function들에 대해, 
# 특정 Function이 만든 RW가 그 Object에 대한 전체 RW 중 비중이 얼마나 되는지 계산하는 함수
# '전체' RW cnt도 필요하다.
class Access:
    def __init__(self, obj_id, ac_type, ac_addr, ac_timestamp, func_name, func_id):
        self.obj_id = obj_id
        self.ac_type = ac_type
        self.ac_addr = ac_addr
        self.ac_timestamp = ac_timestamp
        self.func_name = func_name
        self.func_id = func_id

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


    print("(obj %d - func %s) R: %d (%.2f), W: %d (%.2f)", ac_list[0], 



input_file_name = sys.argv[1]
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
    
for i in range(7):
    line = raw_trace_file.readline()

func_dict = {}
func_dict.clear()
opened_funcs = []
malloc_list = {}
#opened_mallocs = []
opened_mallocs = {}
malloc_id = 0
func_id = 0
# new trace protocol: starts with ^
while True:
    line = raw_trace_file.readline()
    if not line: break
    #if (i % (linenum//1000)) == 0:
        #print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
    #if line[0] == "f":
    if line[0] == "^":
        """
        sline = line.split(" ")
        func_name = sline[2]
        func_name = func_name.replace("\n", "")
        if sline[1] == "b":
            line_type = 1
        elif sline[1] == "e":
            line_type = 0
        else:
            print("function line error: not b/e")
            exit(1)
        """
        ## !! 함수 이름에 띄어쓰기가 포함되기도 하므로, 이걸로 구분하면 안 된다.
        # f e asdfasdf af e assd...
        # func_name = line[4:].replace("\n", "") # ofs 4~ string을 이름으로

        # (1) ^f b [name]
        # (2) ^f e [name]
        # (3) ^m b [size] [malloc'd addr]
        # (4) ^m e [free'd addr]
        if line[1] == "f": 
            if line[3] == "b": # function call (begin)
                line_type = 0
                func_name = line[5:].replace("\n", "") 
            elif line[3] == "e": # function end
                line_type = 1
                func_name = line[5:].replace("\n", "") 
        elif line[1] == "m":
            if line[3] == "b": # malloc call
                line_type = 2
                splitline = line.replace("\n", "").split(" ")
                maddr = int(splitline[3], 16)
                msize = int(splitline[2], 10)
            elif line[3] == "e": # free call
                line_type = 3
                splitline = line.replace("\n", "").split(" ")
                faddr = int(splitline[2], 16)
        else:
            print("function line protocol error: not f or m")
            print("i:", i)
            print("line:", line)


        """
        if line[1] == "b": # function begin (CLG)
            line_type = 0
            func_name = line[5:].replace("\n", "") 
        elif line[1] == "e": # function end (CLG)
            line_type = 1
            func_name = line[5:].replace("\n", "") 
        elif line[1] == "m": # malloc interpose (compile-time)
            line_type = 2
            splitline = line.replace("\n", "").split(" ")
            maddr = int(splitline[2], 16)
            msize = int(splitline[1], 16)
            malloc_id += 1
        elif line[1] == "f": # free interpose (compile-time)
# function이랑 free marker가 겹치네
            line_type = 3
            splitline = line.replace("\n", "").split(" ")
            faddr = int(splitline[1], 16)
        else:
            print("function line error: not b/e")
            print("line:", line)
            print("line[2]:", line[2])
            print("i:", i)
            exit(1)
        """


        #print("func_name:", func_name)
        # function dictionary를 만들어서, 거기에 있는지 검사, 없으면 추가
        # {func_name = reqline = [..]}
        # func 'begin'을 만나면, "만나는 req line을 추가할 func 목록"에 추가해 놓아야 한다.
        # 그래서 req line을 읽을 때, 현재 열린 func 목록의 dict val에 해당 line들을 append하는 식으로.
        ## 이름이 같은 함수도 고려해야 한다. 같은 함수가 여러 번 다른 시간대에서 호출될 수 있다.
        ## 그렇다면, 이름을 key로 하는 dict보다는 그냥 list에 [name, line]으로 매번 append하는 게..

        # 지금은 func_dict의 key가 func_name이지만, 같은 이름이어도 '동일한 Call'끼리만 묶어야 하므로 이걸론 부족하다.
        # CLG의 begin/end marker를 가지고 call graph를 자체적으로 구성해야 할 것 같다. 

        # 처음 보는 func_name -> new id 부여 가능
        # 동일 func_name으로 b/e를 만나기 전까지는 그 access는 동일 fid로부터 나왔다고 볼 수 있음
        # 새로운 func_name b 만남 -> 그 func에겐 new id, 상관없음
        # 동일 func_name b 만남 -> recursive하게 동일 func를 call한 것. 다른 fid임. 
        # 동일 func_name e 만남 -> 끝난 것
        # 단방향으로 Trace 읽는 상황에서는 정확한 판별 불가
        # CLG의 Call graph는 동일 함수의 다른 호출을 구분하지 않음. Rough하게.
        # 근데 구분할 필요가 얼마나 있을까? 가령 지금 쓰는 microbench에서는 memcpy(4096)이 반복되는데, 각 memcpy를 다른 것으로 분리해봐야 소용없다. 분석할 때는 다시 합쳐야 의미가 있을 것. 하지만, 그렇다고 모든 memcpy()를 같은 것으로 묶어버리면 안된다.
        # 같은 Object 내에서의 같은 Func name은 동일하게 취급? 
        # 


        if line_type == 0: # function call (begin)
            if not func_name in opened_funcs:
                opened_funcs.append(func_name)
            else:
                # recursive는 없지만, 중복되는 함수가 있을 수 있다. e.g., (below main)
                if func_name[0] != "(":
                    print(opened_funcs)
                    print("function line error: duplicated name [%s]" % (func_name))
                    #exit(1)
                # 이름 기준으로 정하니까, 반복되는 memcpy()가 너무 많아 구분이 어렵다. loop instance마다 다른 memcpy()가 호출되니 구분해줘야 좋은데, 이름으로는 구분할 수 없음.
                # 새로 opened_funcs에 들어갈 때 다른 function id를 부여해서 구분하는 식으로 하면 좋을 것 같다.
                # func_name과 call cnt를 조합하면 function identifier로 사용 가능하다.
            if not func_name in func_dict:
                # add new func in dict
                # func_dict: key=func_name, value=[call cnt, [1st call's trace], [2nd call's trace], ...]
                func_dict[func_name] = [] # value list
                val = func_dict[func_name]
                val.append(1) # val[0] == index of latest reqs list (== function call cnt within same function name)
                val.append([])
            else: # 동일 func_name이 2번째 호출됐을 때부터
                # add new empty list for rw requests in dict
                val = func_dict[func_name]
                #print("old: ", val[0])
                val[0] = val[0] + 1
                #print("new: ", val[0])
                val.append([])


            func_id += 1 # function id

        elif line_type == 1: # function end
            if func_name in opened_funcs:
                #print("remove func:", func_name)
                #print("before remove, list:", opened_funcs)
                opened_funcs.remove(func_name)
                #print("after remove, list:", opened_funcs)
            else:
                if func_name[0] != "(": # e.g., (below main)
                    print(opened_funcs)
                    print("function line error: meet end, but no name in list. name:", func_name)


        # malloc/free를 위한 별개의 구조 필요
        elif line_type == 2: # malloc call
            # malloc을 만날 때 list에 넣어두고, 순서에 맞게 id도 적어둬야 함. 
            # e.g., [id=3, size=4096, addr=0x1234
            # address trace를 보고, 특정 object가 pref할만하다고 보여지면, 그 주소에 해당하는 object id를 알 수 있어야 함.
            # 그럼 free'd or not도 필요할 것. malloc list는 id로 찾을 수 있어야 하고.
            # opened malloc은 어떻게 관리? malloc_list 하나로 관리하는 것보다는, opened malloc을 따로 두는 게 더 좋아 보임.
            # addr -> id 의 매핑이 필요한데.. opened_mallocs 중에서 해당 addr를 포함하는 게 있는지 찾는 방법을 사용

            malloc_entry = [malloc_id, msize, maddr, []]
            #opened_mallocs[malloc_id] = malloc_entry
            malloc_list[malloc_id] = malloc_entry
            opened_mallocs[maddr] = malloc_entry
            malloc_id += 1


        elif line_type == 3: # free call
            # free를 만나면, 해당 malloc을 opened_mallocs list에서 제거해두기
            # 어떻게 제거? malloc_id에 해당하는 entry를 찾아야 하는데, 
            # 바로 찾으려면 malloc_id를 'key'로 하는 dict를 써야 할 것 같다.
            # malloc_list는 제거할 필요가 없으니 malloc_id 순서대로 append해서 dict 아니여도 malloc_id가 index와 동일하다.
            # 그래서 malloc_list는 list로 해도 되지만, 그냥 opened_mallocs와 동일하게 dict로 쓰자.

            # 이 때, 아는 정보는 faddr 뿐임. 그래서 faddr로부터 malloc_id를 알아내야 함
            # interposition 코드에서 malloc_id를 직접 적을 수도 있긴 한데, 그쪽에는 연산 관련을 넣지 말자.
            # opened_mallocs를 traverse하면서 addr 범위에 faddr이 포함되는지 찾아야 한다.
            # 이 방법 대신, ^m b일 때의 maddr과 faddr은 동일하니까, opened_mallocs에서 maddr를 index로 사용할 수 있다면 해결된다.

            #print(i)
            #del opened_mallocs[malloc_id]
            #print("faddr:", faddr)
            #print(opened_mallocs[faddr])
            del opened_mallocs[faddr]

        i += 1
        continue
    elif line[0] != "[":
        i += 1
        continue

    # e.g., [R addr timestamp]
    # trace를 읽는 부분이므로, 이 때 각 trace line이 어떤 패턴 그룹에 속하는지 고를 수 있어야 한다.
    # 분류 후에 다시 읽는 방식으로 할 거라면, 그 때 opened만 다시 생성해서 같이 보면 될 것

    sline = line.replace('[', '').replace(']', '').replace('\n', '')
    #sline = sline.split(" ")
    #ts = float(sline[-1])
    for f in opened_funcs:
        val = func_dict[f]
        counter = val[0]
        val[counter].append(sline)


    # 각 trace line 별로 읽으면서 확인
    sline = sline.split(" ")
    a_addr = int(sline[1], 16)
    for maddr, mentry in opened_mallocs.items():
        if (maddr <= a_addr) and (a_addr < maddr + mentry[1]): # If true, this access aims the malloc entry
            #print(mentry[0], sline[0], sline[1], sline[2], opened_funcs[-1])

            # per-object의 trace 따로 자료구조로 관리하기
            # object는 malloc_id로 식별되므로, malloc_list[malloc_id]에 넣으면 된다.
            # malloc_list는 dict이며, key: malloc_id, val: malloc_entry = [mid, msize, addr]
            # val에 trace list를 추가해야 한다. [3]에 []를 init해두면 여기서는 append하면 하면 된다.
            func_name = opened_funcs[-1] # 지금 func_name 추적은 정확하지 않다. 이 R/W 이전 가장 최근에 호출된 Function이 이 R/W을 했다고 가정하는 것이므로, multithread 상황만 가도 틀리게 될 것이다. 

            # 여기서, func_name 뿐만 아니라 이 func의 id를 알아내야 함
            # 가장 최근에 호출된 함수니까, 'f b'마다 fid++를 해놓고 그 fid를 사용하면 될 것
            # 이것도 func_name을 정확하게 알 수 있는 방식으로 교체할 때 같이 교체해야 할 것임
            obj_trace_line = [mentry[0], sline[0], sline[1], sline[2], opened_funcs[-1], func_id]
            _mid = mentry[0]; _mentry = malloc_list[_mid];
            obj_trace = _mentry[3] # per-object trace
            obj_trace.append(obj_trace_line)
            
            malloc_list[_mid][3].append()
    
    i += 1

raw_trace_file.close()


# Trace Read End
# Start to analyze the trace from collected information


cmt=1
if cmt != 1:
    print("func_dict:")
    for key, value in func_dict.items():
        print(key, value[0])
        print(value)
        print("")
    exit()

#print("opened_mallocs:", opened_mallocs)
#print("malloc_list:", malloc_list)

## Analyze Per-object Trace ##
for mid, mentry in malloc_list.items():
    # per-object view
    per_obj_trace = mentry[3]

    # Read per-object trace and analyze
    ac_cnt_per_obj = 0; ac_rcnt_per_obj = 0; ac_wcnt_per_obj = 0
    ac_fid_per_family = 0
    per_obj_per_func_dict = {}

    for obj_trace_line in per_obj_trace:

        #oid = int(obj_trace_line[0], 10)
        oid = obj_trace_line[0]
        ac_type = obj_trace_line[1]
        ac_addr = int(obj_trace_line[2], 16)
        ac_time = float(obj_trace_line[3])
        ac_cnt_per_obj += 1
        if ac_type == "R":
            ac_rcnt_per_obj += 1
        elif ac_type == "W":
            ac_wcnt_per_obj += 1
        else:
            print("ac_type error!"); exit()
        ac_fname = obj_trace_line[4]
        ac_fname = obj_trace_line[4]
        ac_fid = obj_trace_line[5]
        #print(oid, ac_type, ac_addr, ac_time, ac_cnt, ac_fname, ac_fid)

        # per-object 안에서, func_name을 key로 하는 dict를 새로 다시 만들어서 func_name 단위로 statistics 뽑기
        #print(obj_trace_line)
        if not ac_fname in per_obj_per_func_dict:
            per_obj_per_func_dict[ac_fname] = []
        per_obj_per_func_dict[ac_fname].append(obj_trace_line)

    for fname in per_obj_per_func_dict:
        ac_list = per_obj_per_func_dict[fname]
        make_stat_popf(ac_rcnt_per_obj, ac_wcnt_per_obj, ac_list)


    for fname, line in per_obj_per_func_dict.items():

    mentry.append(per_obj_per_func_dict)

    #print(per_obj_per_func_dict)
    #exit()

    obj_stat = [ac_cnt, ac_rcnt, ac_wcnt]
    mentry.append(obj_stat) # malloc_entry[4]

    per_obj_addr = []
    for obj_trace_line in per_obj_trace:
        #print("!!:", obj_trace_line)
        addr = int(obj_trace_line[2], 16)
        #print(hex(addr))
        per_obj_addr.append(addr)

for mid, mentry in malloc_list.items():
    for item in mentry[3]:
        print("mentry[3] ->", item)
    for key, val in mentry[4].items():
        for item in val:
            print("mentry[4].value ->", item)
    #print(mentry[3])
    exit()
exit()

records = []
jump_hist = []
for key, value in func_dict.items():
    for i in range(1, len(value)):
        prev_addr = 0x00
        cnt1 = 0; cnt2 = 0; cnt3 = 0; cnt4 = 0; cnt = 0
        min_addr = 0xffffffffffffffff; max_addr = 0
        trace = value[i] # rw trace per each call (begin-end)
        for line in trace:
            is_first = 0
            if (prev_addr == 0x00):
                is_first = 1
            sline = line.split(" ")
            curr_addr = int(sline[1], 16)
            dist = curr_addr - prev_addr 
            prev_addr = curr_addr
            if min_addr > curr_addr: min_addr = curr_addr
            if curr_addr > max_addr: max_addr = curr_addr
            if (is_first): continue
            if (dist > 0): cnt1 += 1
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
        print("(%.0f%%) " % (stat1), end='')
        print(record)


"""
function/malloc list 작성 후, trace line들을 Prefetch Groups로 묶어야 한다.
1. 모든 trace line을 하나의 Group으로 시작해서, 거기로부터 Prefetch group들로 분류하기
2. Function들로 1차 분류한 뒤, 그 Group들을 Prefetch group으로 분류하기
3. Object들로 1차 분류한 뒤, 그 Group들을 Prefetch group으로 분류하기

2차 분류를 Func으로 해야 하는데, 사실 이때부터 구현 이슈가 있음. 어떤 Function으로 분류할 것인지?
가상의 Call graph가 있다고 치면, 모든 node가 후보가 될 수 있고, 한 node에서도 여러 Prefetch group이 발생할 수 있다.

그럼, 1차 분류하면 Object 별로 trace가 나오고,
거기서 일단 Prefetch하기 좋은 패턴을 식별하기.
그렇게 식별된 패턴을 구성하는 trace line들을, 가장 많이 포함하고 있는? 혹은 그 trace line들이 가장 점유율이 높은? function을 식별하면
그 function들 기준으로 해당 패턴을 prefetch했을 때 효과적일 것.
그 후, 그 group을 prefetch하기 위해 timestamp, call graph, llvm 등이 사용될 것.

패턴 식별 방법?
- 단순하게 연속된 line의 addr 차이로 계산 -> 이건 consecutive accesses만 판별 가능하지, 한 line씩 건너뛰고 sequential한 것도 못 찾는다.
- Addr로 선 Sorting한 후 분석이 도움이 될 수 있음. 특정 Group을 Sorting해서 봤을 때 Seq이 더 잘 보일 수 있으니.
- 

1. inter-arrival time의 분포: 다양할 수록 random일 가능성이 높음
2. dist 분포: 작을수록 spatial locality 높고, 클수록 random
3. reuse distance 분포: 각 access의 reuse distance 계산하여 분포로 만들기. distance들이 적을수록 temporal locality 높음
4. working set 분석: unique memory location의 수를 찾고 분포로 만들기. size가 작고 segment들끼리 동일할 경우 temporal locality 높음
5. 상관분석: segment 내의 access 간의 correlation. 높을수록 sequential

segment: per-object trace

seq, seq with stride, loop, streaming, multiple strides


////각 Object trace를, 그 Object에 접근한 경력이 있는 모든 Function들

"""
