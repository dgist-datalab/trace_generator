#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root or with sudo privileges"
  exit
fi

# drop page caches
sync
echo 3 > /proc/sys/vm/drop_caches
echo 1 > /proc/sys/vm/compact_memory
echo 3 > /proc/sys/vm/drop_caches
echo 1 > /proc/sys/vm/compact_memory

tooldir=$(git rev-parse --show-toplevel)

# command
arguments=$@
. $tooldir/run_script/getopt.sh $arguments
if [ $INPUT_FILE_YES -ne 1 ] || [ -z $TRACE_TYPE ]; then
    echo "No input or trace type!"
    echo "    Args Example: -t/--type [virtual/physical] --pref -i/--input [\$INPUT_PROGRAM]"   
    exit
fi

if [ "$TRACE_TYPE" == "virtual" ]; then
    echo "Trace type: Virtual address"
    echo "You can get trace file of Virtual address only"
elif [ "$TRACE_TYPE" == "physical" ]; then
    echo "Trace type: Physical address"
    echo "You can get both trace files of Virtual address and V2P mapping. It requires modified kernel."
	echo 0 > /proc/vpmap/vpmap
	old_cg=$(pgrep -f callgrind | tail -n1)
	if [ -n "$old_cg" ]; then
		echo "[CAUTION] In the current version, only one process can be traced in the Physical Trace mode."
		echo "You should kill your old PIDs to run this script. The following PID list is assumed to be your old target processes:"
		old_cg_list=$(pgrep -f callgrind)
		echo "========="
		echo "$old_cg_list"
		echo "========="
		echo "Stop running.."
		exit
	fi
fi

if [ "$PREF" = True ]; then
    echo "Valgrind CPU Prefetch: ON"
    pref="yes"
    _pref="ON"
else
    echo "Valgrind CPU Prefetch: OFF. Recommend using prefetch for more accurate trace.."
    pref="no"
    _pref="OFF"
fi

if [ -z "$OUT_NAME" ]; then
    logfile="trace_pref${_pref}"
    proclog="./proclog.log"
else
    logfile="$OUT_NAME"
    proclog="./proclog_${OUT_NAME}.log"
fi

execname=$INPUT_FILE
#proclog="./proclog.log"
#logfile="trace_pref${_pref}"
cglog="./$logfile.vout"

if [ "$NOLOG" = True ]; then
	echo "NOLOG on!"
	proclog=""
	cglog=""
fi

start_time=`date +%s`

# valgrind command
echo "Run $execname with valgrind.."
valgrind --tool=callgrind --simulate-wb=yes --simulate-hwpref=${pref} --log-fd=2 $execname > $proclog 2> $cglog &

#target_pid=$(ps | grep callgrind | tail -n1 | awk '{print $1}')
target_pid=$!
pname=$(tr '\0' ' ' </proc/$target_pid/cmdline)
pidlist=$(ps -AL | grep callgrind | awk '{print $2}' | paste -s -d, -)

echo "process pid: $target_pid (name: $pname)"
if [[ $pname != *"$execname"* ]]; then
	echo "Error: Can't find the pid of target process"
	exit
fi

if [ "$TRACE_TYPE" == "physical" ]; then
    #echo $target_pid > /sys/module/memory/parameters/target_pid
    echo $pidlist > /sys/module/memory/parameters/target_pid
    cat /sys/module/memory/parameters/target_pid
fi

while true; do
    if [ -d "/proc/$target_pid/" ]; then
        if [ "$TRACE_TYPE" == "physical" ]; then
            pidlist=$(ps -AL | grep callgrind | awk '{print $2}' | paste -s -d, -) # consider time lags of TIDs generation
            echo $pidlist > /sys/module/memory/parameters/target_pid
        fi
        sleep 0.3
    else
        break
    fi
done

wait $target_pid
end_time=`date +%s`

runtime=$((end_time-start_time))
echo "runtime: $runtime (sec)"

if [ "$TRACE_TYPE" == "physical" ]; then
	cat /proc/vpmap/vpmap > ./$logfile.vpmap
	echo 0 > /sys/module/memory/parameters/target_pid
fi

echo "Process end"


if [ "$TRACE_TYPE" == "physical" ]; then
	echo "Make physical trace using virtual trace and V2P mapping.."
	python3 $tooldir/after_run/mix_vpmap.py ./$logfile.vout
	python3 $tooldir/after_run/make_physical_trace_ts.py ./$logfile.mix
	nline_vout=$(wc -l ./$logfile.vout | awk '{print $1}')
	nline_pout=$(wc -l ./$logfile.pout | awk '{print $1}')
	echo "# of lines ([.vout] / [.pout]): $nline_vout / $nline_pout"
	rm ./$logfile.mix
fi

read -r -p "Do you want to plot graph? [y/N] " response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
then
    echo "plot virtual trace graph.."
	python3 $tooldir/after_run/graph/cg_histogram.py --input $logfile.vout --scatter 103 
	if [ "$TRACE_TYPE" == "physical" ]; then
		echo "plot physical trace graph.."
		python3 $tooldir/after_run/graph/cg_pa_histogram.py --input $logfile.pout --scatter 103 
	fi
fi
