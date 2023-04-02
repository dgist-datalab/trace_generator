#!/bin/bash

src="main.cpp"
#target="SeqW1M4K_interpose"
target="P90W1M4K_interpose"
target="P90W512M4K_interpose"

g++ -Wall -DCOMPILETIME -c mymalloc.cpp # make mymalloc.o

g++ -Wall -o $target $src mymalloc.o
