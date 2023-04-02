# If [.vout] trace file has timestamp, use this script.
import matplotlib.pyplot as plt
import numpy as np
import sys

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def find_close_mapping(x, a):
    target = 0
    close = 50
    small = 0
    big = len(a)-1
    for i in range(len(a)):
        if (a[i]) < x:
            small = i
        if a[i] >= x:
            big = i
            break
    diff_s = x-a[small]
    diff_b = a[big]-x

    if small == 0 and big == 0:
        target = small
    elif small == big and small > 0:
        target = big
    else:
        if diff_s < 0 or diff_b < 0:
            print("Error (diff_s: %d, diff_b: %d)" % (diff_s, diff_b))
        elif diff_s < close and diff_b < close:
            target = small if diff_s <= diff_b else big
        elif diff_s < close:
            target = small
        elif diff_b < close:
            target = big
    return target



input_file_name = sys.argv[1]
linenum = file_len(input_file_name)
print("linenum of %s: %d" % (input_file_name, linenum))

if input_file_name[-4:] != ".mix":
    print("input file [%s] is not .mix!" % (input_file_name))
    exit()

raw_trace_file = open(input_file_name, 'r')
for i in range(7):
    line = raw_trace_file.readline()

i = 0
d = {}
d.clear()
item_idx = {}
item_idx.clear()
item_cnt = 0
map_cnt = 0
vpn_cnt = 0
exist_cnt = 0

# make v2p map (dictionary)
while True:
    line = raw_trace_file.readline()
    if not line: break
    if (i % (linenum//1000)) == 0:
        print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 

    num_cg = line.count('[')
    num_kn = line.count('{')
    num_total = num_cg + num_kn

    line = line.replace(']', '}').replace('[', '{').replace('}', ' ').replace('\n',' ')

    splitline = line.split("{")
    del splitline[0]

    for item in splitline:

        elem = item.split(" ")
        elem = ' '.join(elem).split()
        if elem[0] == 'R' or elem[0] == 'W':
            cg_vaddr = int(elem[1], 16)
        else:
            map_cnt += 1
            kn_vpn = int(elem[2], 16)
            kn_pfn = int(elem[3], 16)
            if kn_vpn in d:
                d[kn_vpn].append([item_cnt, kn_pfn])
                exist_cnt += 1
            else:
                d[kn_vpn] = [[item_cnt, kn_pfn]]
                vpn_cnt += 1
        item_cnt += 1

    i += 1

#raw_trace_file.close()



# Second scan to translate Valgrind's virtual memory trace to the physical memory trace
output_file_name = input_file_name[:-4] + ".pout"
mem_trace = open(output_file_name, 'w')
raw_trace_file.seek(0)

for i in range(7):
    line = raw_trace_file.readline()

i = 0
item_cnt = 0
none_cnt = 0
ok_cnt = 0
find_flag = 0
variable_map_cnt = 0

none_list_file_name = input_file_name[:-4] + ".none"
none_list = open(none_list_file_name, 'w')
while True:
    line = raw_trace_file.readline()
    if not line: break
    if (i % (linenum//1000)) == 0:
        print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 

    line = line.replace(']', '}').replace('[', '{').replace('}', ' ').replace('\n',' ')

    splitline = line.split("{")
    del splitline[0]

    for item in splitline:
        elem = item.split(" ")
        elem = ' '.join(elem).split()
        
        if elem[0] == 'R' or elem[0] == 'W':
            cg_vaddr = int(elem[1], 16)
            cg_vpn = cg_vaddr // 4096
            cg_ofs = cg_vaddr & 0xfff

            if (d.get(cg_vpn) == None):
                none_cnt += 1

                none_list.write(str(hex(cg_vpn)) + " " + str(hex(cg_vaddr)) + "\n")
            else:
                val = d[cg_vpn]
                if len(val) > 1:
                    idx_list = []
                    for j in range(len(val)):
                        idx_list.append(val[j][0])
                    target_j = find_close_mapping(item_cnt, idx_list)
                    kn_pfn = val[target_j][1]
                    variable_map_cnt += 1
                else:
                    kn_pfn = val[0][1];#(d.get(cg_vpn))[1]

                if (kn_pfn == None):
                    none_cnt += 1
                    print(hex(cg_vpn), "what?")
                    exit()
                else:
                    paddr = kn_pfn * 4096 + cg_ofs
                    mem_trace.write(elem[0] + " " + str(hex(paddr)) + " " + elem[2] + "\n")
                    ok_cnt += 1

        item_cnt += 1

    i += 1

print("ok: %d, none: %d, (%.1f%%)" % (ok_cnt, none_cnt, (ok_cnt/(ok_cnt+none_cnt))*100.0))
#mem_trace.seek(0)
#mem_trace.write(str(ok_cnt) + " " + str(none_cnt) + " " + str((ok_cnt/(ok_cnt+none_cnt))*100.0))

raw_trace_file.close()
mem_trace.close()
none_list.close()
