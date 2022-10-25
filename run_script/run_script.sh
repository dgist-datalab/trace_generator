#!/bin/bash

# drop page caches
sync
echo 3 > /proc/sys/vm/drop_caches
echo 1 > /proc/sys/vm/compact_memory
echo 3 > /proc/sys/vm/drop_caches
echo 1 > /proc/sys/vm/compact_memory

# command
arguments=$@
. ./getopt.sh $arguments
if [ -z $INPUT_FILE ] || [ -z $TRACE_TYPE ]; then
    echo "No input or trace type!"
    echo "    Args Example: -i/--input [\$INPUT_PROGRAM] -t/--type [virtual/physical]"   
    exit
fi

if [ "$TRACE_TYPE" == "virtual" ]; then
    echo "Trace type: Virtual address"
    echo "You can get trace file of Virtual address only"
elif [ "$TRACE_TYPE" == "physical" ]; then
    echo "Trace type: Physical address"
    echo "You can get both trace files of Virtual address and V2P mapping. It requires modified kernel."
	echo 0 > /proc/vpmap/vpmap
	old_cg=$(pgrep callgrind)
	if [ -n "$old_cg" ]; then
		echo "[CAUTION] In the current version, only one process can be traced in the Physical Trace mode. Stop running.."
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

execname=$INPUT_FILE
proclog="./proclog.log"
logfile="trace_pref${_pref}"
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

target_pid=$(ps | grep callgrind | tail -n1 | awk '{print $1}')
echo "process pid: $target_pid"
if [ "$TRACE_TYPE" == "physical" ]; then
    echo $target_pid > /sys/module/memory/parameters/target_pid
    cat /sys/module/memory/parameters/target_pid
fi

while true; do
    if [ -d "/proc/$target_pid/" ]; then
        cp /proc/$target_pid/maps maps_temp
        maps_numline=$(wc -l maps_temp | awk '{print $1}')
        if [ $maps_numline -ne 0 ]; then
            mv maps_temp maps
        fi
        sleep 0.3
    else
        break
    fi
done

wait $target_pid
end_time=`date +%s`

runtime=$((end_time-start_time))
echo "runtime: $runtime"

cat /proc/vpmap/vpmap > ./$logfile.vpmap
echo 0 > /sys/module/memory/parameters/target_pid

echo "Process end"


if [ "$TRACE_TYPE" == "physical" ]; then
	echo "Make physical trace using virtual trace and V2P mapping.."
	python3 ../after_run/mix_vpmap.py ./$logfile.vout
	python3 ../after_run/make_physical_trace_ts.py ./$logfile.mix
fi

read -r -p "Do you want to plot graph? [y/N] " response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
then
    echo "plot virtual trace graph.."
	python3 ../after_run/graph/cg_histogram.py --input $logfile.vout --scatter 103 
	if [ "$TRACE_TYPE" == "physical" ]; then
		echo "plot physical trace graph.."
		python3 ../after_run/graph/cg_pa_histogram.py --input $logfile.pout --scatter 103 
	fi
fi
