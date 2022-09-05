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
if [ -z $INPUT_FILE ]; then
	echo "No input!"
	exit
fi
if [ "$PREF" = True ]; then
	echo "Prefetch on!"
	pref="yes"
	_pref="_pref"
else
	echo "Prefetch off!"
	pref="no"
fi

execname=$INPUT_FILE
proclog="./proclog${_pref}.log"
cglog="./cg_result${_pref}.out"

if [ "$NOLOG" = True ]; then
	echo "NOLOG on!"
	proclog=""
	cglog=""
fi

# valgrind command
valgrind --tool=callgrind --simulate-hwpref=${pref} --simulate-wb=yes --log-fd=2 $execname > $proclog 2> $cglog &

# send target_pid to kernel
target_pid=$(pgrep callgrind | sed -n 1p)
echo $target_pid > /sys/module/memory/parameters/target_pid
echo "target_pid: $target_pid"
cat /sys/module/memory/parameters/target_pid
