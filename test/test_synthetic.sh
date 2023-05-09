#!/bin/bash

tool_dir=$(git rev-parse --show-toplevel)
run_script="${tool_dir}/run_script/run_script.sh"
synth_dir="${tool_dir}/test/Synthetic_Workload"

options=("indirect_delta" "true_random" "heap" "strided_latjob" "hashmap")

echo "Please select a synthetic workload to test: "
PS3="Input workload number: "

select opt in "${options[@]}"; do
    case $opt in
        "indirect_delta")
            echo "You chose $opt"
            break
            ;;
        "true_random")
            echo "You chose $opt"
            break
            ;;
        "heap")
            echo "You chose $opt"
            break
            ;;
        "strided_latjob")
            echo "You chose $opt"
            break
            ;;
        "hashmap")
            echo "You chose $opt"
            break
            ;;
        *) echo "Invalid option $REPLY";;
    esac
done

response=""
while [[ ! "$response" =~ ^([vVpP])$ ]]; do
	read -r -p "Get only virtual address trace or both virtual/physical address trace? [v/p] " response
	if [[ "$response" =~ ^([vV])$ ]]; then
		trace_type="virutal"
	elif [[ "$response" =~ ^([pP])$ ]]; then
		trace_type="physical"
	else
		echo "Invalid option: $response. Please enter 'v' or 'p'."
	fi
done
echo "selected trace type: $trace_type"

read -r -p "Enable Valgrind's cpu cache prefetcher option? [y/N] " response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
	pref_type="--pref"
	echo "prefetcher option: ON"
else
	pref_type=""
	echo "prefetcher option: OFF"
fi

tname="$opt"
tpath="${synth_dir}/$tname"

cmd="${run_script} --type $trace_type $pref_type --outname $tname --input $tpath"

echo "\$$cmd"
#$cmd
