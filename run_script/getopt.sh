#!/bin/bash

# options:
INPUT_FILE=""
OPT_INT=0
OPT_BOOL=False

# get options:
while (( "$#" )); do
    case "$1" in
        -i|--input)
            if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
                INPUT_FILE=$2
                shift 2
            else
                echo "Error: Argument for $1 is missing" >&2
                exit 1
            fi
            ;;
        -p|--pref)
            PREF=True
            shift
            ;;
        --nolog)
            NOLOG=True
            shift
            ;;
        -h|--help)
            echo "Usage:  $0 -i <input> [options]" >&2
            echo "        -i | --input  %  (set input to ...)" >&2
            echo "        -p | --pref	   (use cpu prefetcher in valgrind cache simulator)" >&2
            echo "        --nolog		   (no log redirection)" >&2
            exit 0
            ;;
        -*|--*) # unsupported flags
            echo "Error: Unsupported flag: $1" >&2
            echo "$0 -h for help message" >&2
            exit 1
            ;;
        *)
            echo "Error: Arguments with not proper flag: $1" >&2
            echo "$0 -h for help message" >&2
            exit 1
            ;;
    esac
done
echo "===parsed command line option==="
echo " - input: ${INPUT_FILE}"
echo " - pref: ${PREF}"
echo " - nolog: ${NOLOG}"
