# For Callgrind hint version. first word is begin or end.
# Example: begin processCommand
import matplotlib.pyplot as plt
import numpy as np
import sys

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

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

vpmap_file_name = input_file_name[:-5] + ".vpmap"
print("vpmap fname:", vpmap_file_name)

try:
    vpmap_file = open(vpmap_file_name, 'r')
except:
    sys.stderr.write("No file: %s\n" % vpmap_file_name)
    exit(1)

output_file_name = input_file_name[:-5] + ".mix"
mixed_file = open(output_file_name, 'w')

i = 0
vpmap_end = 0
while True:
    line = raw_trace_file.readline()
    if not line: break
    if (line[0] == "b") or (line[0] == "e"):
        mixed_file.write(line)
        continue

    if (line[0] != "["): 
#print("[%d] %s" % (i, line), end="")
        i += 1
        continue
#if line[0] == "=": break
    if (i % (linenum//1000)) == 0:
        print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
    sline = line.replace(']', '').replace('\n', '')
    sline = sline.split(" ")
    #print("line:", line)
    #print("sline:", sline)
    #print(sline[-1])
    ts = float(sline[-1])
    #exit()

    # find earlier vpmap
    while vpmap_end == 0:
        ofs = vpmap_file.tell()
        mline = vpmap_file.readline()
        if not mline:
            vpmap_end = 1
            break
        msline = mline.replace('}', '').replace('\n', '')
        msline = msline.split(" ")
        map_ts = float(msline[-1])
        if map_ts < ts:
            mixed_file.write(mline)
        else:
            vpmap_file.seek(ofs)
            break
    mixed_file.write(line)
    i += 1

raw_trace_file.close()
vpmap_file.close()
mixed_file.close()

