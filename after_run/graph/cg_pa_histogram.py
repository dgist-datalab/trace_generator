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

def read_va_log(input_file_name, args, data_read = 0):
    # From VA histogram log file, calculate each group size
    if args.scatter > 0:
        log_ext = ".slog"
    elif args.cdf:
        log_ext = ".clog"
    else:
        log_ext = ".blog" 
    va_log_file_name = input_file_name[:-5] + log_ext
    va_log_file = open(va_log_file_name, 'r')
    splitline = va_log_file.readline().split(" ")
    va_min = int(splitline[0], 16)
    va_max = int(splitline[1], 16)
    splitline = va_log_file.readline().split(" ")
    va_lower_bound = int(splitline[0], 16)
    va_upper_bound = int(splitline[1], 16)
    splitline = va_log_file.readline().split(" ")
    va_group_num = int(splitline[1], 10)
    va_log_file.readline()
    splitline = va_log_file.readline().split(" ")
    va_hist = []
    if data_read == 1 and args.cdf == 0:
        for y in splitline:
            va_hist.append(int(y))
    va_log_file.close()
    return va_min, va_max, va_lower_bound, va_upper_bound, va_group_num, va_hist

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
#input_file_name = sys.argv[1]
if input_file_name[-5:] != ".pout":
    print("input file [%s] is not .phyout!" % (input_file_name))
    exit()

linenum = file_len(input_file_name)
print("linenum of %s: %d" % (input_file_name, linenum))

# File open, and find min, max for specifying bound
file = open(input_file_name, 'r')

i = 0
min = 0xffffffffffffffff
max = 0
upper_bound = 0x1000000000
#upper_bound = 0x350000000
lower_bound = 0x100000

print("Find min/max of address..")
file.readline()
while True:
    line = file.readline()
    if not line: break
    if line[0] == "=" or line[0] == "-": continue
    if (i % (linenum//1000)) == 0:
        print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="") 
        
    line = line.replace('R ', '').replace('W ', '').replace('\n',' ')
    splitline = line.split(" ")
    a = int(splitline[0], 16)    
        
    if a > max:
        if a < upper_bound: # Upper bound of interesting address
            max = a
    if a < min:
        if a > lower_bound: # Lower bound of interesting address
            min = a
         
    i += 1
    
print("min:", hex(min), "max:", hex(max))
group_num = 100000

# From VA histogram log file, calculate each group size
va_min, va_max, va_lower_bound, va_upper_bound, va_group_num, va_data = read_va_log(input_file_name, args, data_read = 1)
#//print("sum(va_hist): %d" % (sum(va_hist)))

va_pool_size = va_max - va_min
va_group_size = va_pool_size // va_group_num
pa_pool_size = max - min
pa_group_size1 = pa_pool_size // group_num # static group size
pa_group_size2 = va_group_size
group_num2 = pa_pool_size // pa_group_size2
group_weight = group_num2 // va_group_num // 2
precise_plot = 0
print("group_num (va/static_pa/precise_pa): %d/%d/%d, group_weight: %d, va_group_size: %d, pa_group_size (static/precise): %d/%d" % (va_group_num, group_num, group_num2, group_weight, va_group_size, pa_group_size1, pa_group_size2))
if precise_plot == 0:
    print("For precise plotting, use same group size with virtual trace")
    group_num = group_num2
    group_size = pa_group_size2
else:
    group_size = pa_group_size1
# histogram 자체를 group_weight 개수만큼 나눠야 할 것 같긴 하다.


# File open, and make histogram (# of access per address group)
file.seek(0)

man = 0 # manual size of axis
man_range = 10000
if scatter:
    scope = max-min
    i = 0
    scatter = []
    R_cnt = 0
    W_cnt = 0

    print("Make scatter list..")
    file.readline()
    while True:
        line = file.readline()
        if not line: break
        if line[0] == "=" or line[0] == "-": continue
        if (i % (linenum//1000)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="")         

        # Integrate read/write as an access
        if line[0] == 'R':
            R_cnt += 1
        elif line[0] == 'W':
            W_cnt += 1

        line = line.replace('R ', '').replace('W ', '').replace('\n',' ')
        splitline = line.split(" ")
        a = int(splitline[0], 16)
        if a >= upper_bound or a <= lower_bound:
            i += 1
            continue

        group_idx = round((a-min)/scope*group_num)
        scatter.append(group_idx)
        i += 1
    print("len(scatter):", len(scatter))  
    file.close()

    print("R_cnt: %d, W_cnt: %d, Total: %d" % (R_cnt, W_cnt, R_cnt+W_cnt))
    sum_scatter = sum(scatter)
    print("sum(scatter): %d" % (sum_scatter))


    # scatter plot
    samp_per = args.scatter
    samp = []
    for i in range(len(scatter)):
        if i % samp_per == 0:
            samp.append(scatter[i])
    print("len(samp):", len(samp))

    x = list(np.arange(0, len(samp), 1))

    figsize_x = 8; figsize_y = 5
    if precise_plot == 1:
        figsize_x = figsize_x * group_weight
    #plt.rcParams["font.family"] = 'Times New Roman'
    plt.rcParams["font.size"] = 22
    plt.rcParams["figure.figsize"] = (figsize_x, figsize_y)
    plt.rc('legend', fontsize=18)

    fig, ax1 = plt.subplots(dpi=600)

    #x_ = x[10000:15000]
    #hist_ = hist[10000:15000]
    x_ = x[:]
    scatter_ = samp[:]
    #x_ = x[20:80] # See 20% ~ 80%
    #hist_ = hist[20:80]


    print("plot..")
    ax1.scatter(x, scatter_, c='black', s=1)
    xlabel_name = 'Order of requests (sampled per ' + str(samp_per) + ' requests)'
    ylabel_name="Physical address group \n(" + str(group_num) + " groups, "+str(group_size)+"B)"
    ax1.set_xlabel(xlabel_name)
    ax1.set_ylabel(ylabel_name)
    ax1.tick_params(axis='y', direction='in')
    if man == 0:
        ax1.set_ylim(0, group_num)
    else:
        ax1.set_ylim(0, man_range) # add "man" in fig_name

    print("plot end. save..")
    id_str = "-scatter"+str(args.scatter)+"-g"+str(group_num)+"-"+str(group_size)
    if man == 0:
        fig_name = "./plot" + id_str + "_" + input_file_name[:-5] + "_pa.png"
    else:
        fig_name = "./manplot" + id_str + "_" + input_file_name[:-5] + "_pa.png"
    fig.savefig(fig_name, bbox_inches='tight', format='png')

else:
    scope = max-min
    i = 0
    hist = [0 for i in range(group_num+1)] # group: [0,100]
    R_cnt = 0
    W_cnt = 0

    print("Make histogram list..")
    file.readline()
    while True:
        line = file.readline()
        if not line: break
        if line[0] == "=" or line[0] == "-": continue
        if (i % (linenum//1000)) == 0:
            print('\r', "%.0f%% [%d/%d]" % (i/linenum*100, i, linenum), end="")         

        # Integrate read/write as an access
        if line[0] == 'R':
            R_cnt += 1
        elif line[0] == 'W':
            W_cnt += 1

        line = line.replace('R ', '').replace('W ', '').replace('\n',' ')
        a = int(line, 16)
        if a >= upper_bound or a <= lower_bound:
            i += 1
            continue

        percent = round((a-min)/scope*group_num)
        hist[percent] += 1
        
        i += 1
        
    file.close()
    print("R_cnt: %d, W_cnt: %d, Total: %d" % (R_cnt, W_cnt, R_cnt+W_cnt))
    sum_hist = sum(hist)
    print("sum(hist): %d" % (sum_hist))
    va_hotgroup_cnt = 0; va_hotgroup_sum = 0
    hotgroup_cnt = 0; hotgroup_sum = 0
    for y in va_data:
        if y > 5000:
            va_hotgroup_cnt += 1
            va_hotgroup_sum += y
    for y in hist:
        if y > 5000:
            hotgroup_cnt += 1
            hotgroup_sum += y
    print("va_hotgroup_cnt: %d, hotgroup_cnt: %d" % (va_hotgroup_cnt, hotgroup_cnt))
    print("va_hotgroup_sum: %d, hotgroup_sum: %d" % (va_hotgroup_sum, hotgroup_sum))
    # group size가 어쨌든 4K pagesize보다는 크므로, 
    # MMU가 VPN을 page 단위로 퍼뜨린다고 가정하면 더 퍼뜨리는 것처럼 보일 수 있다.
    # 이것까지 제대로 보려면, 애초에 VA hist에서 group size를 group_num=10000이 아니라 
    # group_size=4000으로 해야 한다.

    # Sort and cdf
    from itertools import accumulate

    if cdf == 1:
        sorted = 1
        if man == 1:
            hist = hist[:man_range]
        hist.sort()
        sum_hist = sum(hist)
        cd = list(accumulate(hist))
        for i in range(len(cd)):
            cd[i] = cd[i]/sum_hist
        hist = cd
    else:
        sorted = 0

    # Make histogram
    if cdf == 0:
        x = list(np.arange(0, group_num+1, 1)) 
    else:
        if man == 1:
            x = list(np.arange(0, man_range, 1)) 
        else:
            x = list(np.arange(0, group_num+1, 1)) 

    figsize_x = 8; figsize_y = 5
    if precise_plot == 1:
        figsize_x = figsize_x * group_weight
    #plt.rcParams["font.family"] = 'Times New Roman'
    plt.rcParams["font.size"] = 22
    plt.rcParams["figure.figsize"] = (figsize_x, figsize_y)
    plt.rc('legend', fontsize=18)

    fig, ax1 = plt.subplots(dpi=600)

    #x_ = x[10000:15000]
    #hist_ = hist[10000:15000]
    x_ = x[:]
    hist_ = hist[:]
    #x_ = x[20:80] # See 20% ~ 80%
    #hist_ = hist[20:80]


    print("plot..")
    ax1.bar(x_, hist_, width=0.2, edgecolor='black', linewidth=1, zorder=1)

    if man == 1:
        if cdf == 1:
            ax1.set_xlim(man_range-10000, man_range) # add "man" in fig_name
        else:
            ax1.set_xlim(0, man_range) # add "man" in fig_name

    if sorted == 1:
        xlabel_name="Physical address groups (" + str(group_num) + " groups, "+str(group_size)+"B, sorted)"
    else:
        xlabel_name="Physical address groups (" + str(group_num) + " groups, "+str(group_size)+"B)"
    ax1.set_xlabel(xlabel_name)
    #ax1.set_xlabel('Physical address groups (1,000,000 groups)')
    if cdf == 1:
        ax1.set_ylabel('CDF (# of accesses)')
        id_str = "-cdf-g"+str(group_num)+"-"+str(group_size)
    else:
        ax1.set_ylabel('# of accesses')
        id_str = "-g"+str(group_num)+"-"+str(group_size)
    ax1.tick_params(axis='y', direction='in')

    print("plot end. save..")
    if man == 0:
        fig_name = "./hist" + id_str + "_" + input_file_name[:-5] + "_pa.png"
    else:
        fig_name = "./manhist" + id_str + "_" + input_file_name[:-5] + "_pa.png"
    fig.savefig(fig_name, bbox_inches='tight', format='png')
