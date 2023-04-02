#!/bin/bash

outname=$1
input=$2

outname="wc-1K_v5_funcset"
outname="wc-1K_v6_linetype"
input="res_ycsb/res_wc-1K/wc-1K.vout"

#python3 -m cProfile -o output.prof refine_dict.py res_ycsb/res_wc-1K/wc-1K.vout
python3 -m cProfile -o $outname.prof sort_refine_dict.py $input
