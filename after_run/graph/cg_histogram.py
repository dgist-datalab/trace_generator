from tokenize import group
import matplotlib.pyplot as plt
import numpy as np
import sys
import argparse
from itertools import accumulate

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def save_log(fname, min, max, lower_bound, upper_bound, group_num, data=0):
    log_file = open(fname, 'w')
    log_file.write(str(hex(min)) + " " + str(hex(max)) + "\n")
    log_file.write(str(hex(lower_bound) + " " + str(hex(upper_bound))) + "\n")
    log_file.write("group_num " + str(group_num) + "\n")
    if data:
        log_file.write("ydata" + "\n")
        log_file.write(str(data).replace('[', '').replace(']', '').replace(',', ''))
    log_file.close()

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", action='store', type=str, help='input file', default=False)
parser.add_argument("-c", "--cdf", action='store_true', help='plot sorted cdf', default=False)
parser.add_argument("-s", "--scatter", action='store', type=int, help='plot scattered graph', default=False)
args = parser.parse_args()
input_file_name = args.input
scatter=0; cdf=0
if args.scatter:
    scatter = 1
    print("plot scattered order-address graph")
else:
    if args.cdf:
        cdf = 1
        print("plot sorted cdf graph")
    else:
        print("plot basic address histogram")

input_file_name = args.input
if input_file_name[-5:] != ".vout":
    print("input file [%s] is not .vout!" % (input_file_name))
    exit()

linenum = file_len(input_file_name)
print("linenum of %s: %d" % (input_file_name, linenum))

# File open, and find min, max for specifying bound
#input_file_name = "ldst_result"
file = open(input_file_name, 'r')
file.seek(0)

i = 0
min = 0xffffffffffffffff
max = 0
upper_bound = 0x1000000000
lower_bound = 0x100000
print("Find min/max of address..")
while True:
    line = file.readline()
    if not line: break
    if line[0] == "=" or line[0] == "-": continue
    if (i % (linenum//1000)) == 0:
        print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
    #if i>100: exit()
        
    line = line.replace(']', '}').replace('[', '{').replace('}', ' ').replace('\n',' ')
    splitline = line.split("{")
    #del splitline[0]
    item = splitline[-1]
    #for item in splitline[::-1]:
    elem = item.split(" ")
    elem = ' '.join(elem).split()
    if elem[0] == 'R' or elem[0] == 'W':
        a = int(elem[1], 16)
        if a > max:
            if a < upper_bound: # Upper bound of interesting address
                max = a
        if a < min:
            if a > lower_bound: # Lower bound of interesting address
                min = a
    """
    line = line.replace('[R ', '').replace('[W ', '').replace(']', '').replace('\n',' ')
    a = int(line, 16)    
        
    if a > max:
        if a < upper_bound: # Upper bound of interesting address
            max = a
    if a < min:
        if a > lower_bound: # Lower bound of interesting address
            min = a
    """
         
    i += 1
#min= 0x100248; max= 0x158c60000
    
print("min:", hex(min), "max:", hex(max))
file.close()    

# File open, and make histogram (# of access per address group)
file = open(input_file_name, 'r')

va_pool_size = max-min
#group_size = 4096 # Pagesize
#va_group_num = va_pool_size // group_size

group_num = 10000
#group_num = va_group_num
group_size = va_pool_size // group_num
print("group_size:", group_size, "group_num:", group_num)

if scatter:
    # create scatter list
    scope = max-min
    i = 0
    scatter = []
    print("Make scatter list..")
    while True:
        line = file.readline()
        if not line: break
        if line[0] == "=" or line[0] == "-": continue
        if (i % (linenum//1000)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="")         

        line = line.replace(']', '}').replace('[', '{').replace('}', ' ').replace('\n',' ')
        elem = line.split("{")[-1].split(" ")
        elem = ' '.join(elem).split()
        if elem[0] == 'R' or elem[0] == 'W':
            a = int(elem[1], 16)
            if a >= upper_bound or a <= lower_bound:
                i += 1
                continue
            group_idx = round((a-min)/scope*group_num)
            scatter.append(group_idx)
            i += 1
    print("len(scatter):", len(scatter))  
    file.close()

    # scatter plot
    samp_per = args.scatter
    samp = []
    for i in range(len(scatter)):
        if i % samp_per == 0:
            samp.append(scatter[i])
    print("len(samp):", len(samp))

    x = list(np.arange(0, len(samp), 1))

    #plt.rcParams["font.family"] = 'Times New Roman'
    plt.rcParams["font.size"] = 22
    plt.rcParams["figure.figsize"] = (8,5)
    plt.rc('legend', fontsize=18)

    fig, ax1 = plt.subplots(dpi=600)
    #plt.xticks(x, label, fontsize=20)

    x_ = x[:]
    scatter_ = samp[:]
    #x = x[:80]
    #hist = hist[:80]
    ax1.scatter(x, scatter_, c='black', s=1)

    #ax1.bar(x_, scatter_, width=0.2, edgecolor='black', linewidth=1, zorder=1)

    xlabel_name = 'Order of requests (sampled per ' + str(samp_per) + ' requests)'
    ylabel_name="Virtual address group \n(" + str(group_num) + " groups, "+str(group_size)+"B)"
    ax1.set_xlabel(xlabel_name)
    ax1.set_ylabel(ylabel_name)
    ax1.tick_params(axis='y', direction='in')
    ax1.set_ylim(0, group_num)
    id_str = "-scatter"+str(args.scatter)+"-g"+str(group_num)+"-"+str(group_size)
    fig_name = "./plot" + id_str + "_" + input_file_name[:-5] + "_va.png"
    fig.savefig(fig_name, bbox_inches='tight', format='png')
    log_file_name = input_file_name[:-5] + ".slog"
    save_log(log_file_name, min, max, lower_bound, upper_bound, group_num, data=scatter)




else:

    scope = max-min
    i = 0
    hist = [0 for i in range(group_num+1)] # group: [0,100]
    print("Make histogram list..")
    while True:
        line = file.readline()
        if not line: break
        if line[0] == "=" or line[0] == "-": continue
        if (i % (linenum//1000)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="")         

        line = line.replace(']', '}').replace('[', '{').replace('}', ' ').replace('\n',' ')
        elem = line.split("{")[-1].split(" ")
        elem = ' '.join(elem).split()
        if elem[0] == 'R' or elem[0] == 'W':
            a = int(elem[1], 16)
            if a >= upper_bound or a <= lower_bound:
                i += 1
                continue
            percent = round((a-min)/scope*group_num) 
            hist[percent] += 1

        """
        # Integrate read/write as an access
        line = line.replace('[R ', '').replace('[W ', '').replace(']', '').replace('\n',' ')
        a = int(line, 16)
        if a >= upper_bound or a <= lower_bound:
            i += 1
            continue

        percent = round((a-min)/scope*group_num) # 100 groups
        #percent = round((a-min)/scope*1000) # 1000 groups
        hist[percent] += 1
        """
        
        i += 1
        
    file.close()

    if cdf == 1:
        sorted = 1
        hist.sort()
        sum_hist = sum(hist)
        cd = list(accumulate(hist))
        for i in range(len(cd)):
            cd[i] = cd[i]/sum_hist
        hist = cd
    else:
        sorted = 0

    # Make histogram
    x = list(np.arange(0, group_num+1, 1)) 

    #plt.rcParams["font.family"] = 'Times New Roman'
    plt.rcParams["font.size"] = 22
    plt.rcParams["figure.figsize"] = (8,5)
    plt.rc('legend', fontsize=18)

    fig, ax1 = plt.subplots(dpi=600)

    x_ = x[:]
    hist_ = hist[:]
    #x_ = x[20:80] # See 20% ~ 80%
    #hist_ = hist[20:80]
    ax1.bar(x_, hist_, width=0.2, edgecolor='black', linewidth=1, zorder=1)

    if sorted == 1:
        xlabel_name="Virtual address groups (" + str(group_num) + " groups, "+str(group_size)+"B, sorted)"
    else:
        xlabel_name="Virtual address groups (" + str(group_num) + " groups, "+str(group_size)+"B)"
    ax1.set_xlabel(xlabel_name)
    if cdf == 1:
        ax1.set_ylabel('CDF (# of accesses)')
        id_str = "-cdf-g"+str(group_num)+"-"+str(group_size)
    else:
        ax1.set_ylabel('# of accesses')
        id_str = "-g"+str(group_num)+"-"+str(group_size)
    ax1.tick_params(axis='y', direction='in')

    fig_name = "./hist" + id_str + "_" + input_file_name[:-5] + "_va.png"
    fig.savefig(fig_name, bbox_inches='tight', format='png')

    # Save min/max in a log file for calculating the address pool size
    if cdf == 1:
        log_file_name = input_file_name[:-5] + ".clog"
    else:
        log_file_name = input_file_name[:-5] + ".blog"
    save_log(log_file_name, min, max, lower_bound, upper_bound, group_num, data=hist)
