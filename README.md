# Trace Generator (Memory Tracing Tool)
A memory tracing tool generating a virtual/physical address trace of the target aplication.
This repository is focused on working together as a part of the [CXL-flash Design Tools](https://github.com/spypaul/MQSim_CXL) used in our research paper, _Overcoming the Memory Wall with CXL-Enabled SSDs_.

## Goal
The goal of this memory tracing tool is generating raw memory trace files (`*.vout` or `*.pout`). 
To use MQSim_CXL in [CXL-flash Design Tools](https://github.com/spypaul/MQSim_CXL), the raw trace files generated from this tool should be translated to `*.trace` files by using [Trace Translator](https://github.com/spypaul/trace_translation).

## Installation
This memory tracing tool is composed of three main components: a modified version of Valgrind, the Linux kernel, and scripts to facilitate its use.
Repositories of the modified version of Valgrind and Linux kernel are submodules of this repository, and they follow their own licenses, GPL v2.

### The modified version of Valgrind
1. Clone [the github repository](https://github.com/dgist-datalab/valgrind_cachetrace/tree/040053890262abac1b504bbd5cd9ace8e2261a4e)
```
$ git clone https://github.com/dgist-datalab/valgrind_cachetrace.git
$ cd valgrind_cachetrace
```
2. Install the modified version of Valgrind
```
$ ./autogen.sh
$ ./configure
$ make
$ sudo make install
```

### Linux Kernel
* If you don't need physical traces, don't need to install this Linux kernel.
* The `defconfig` used in our forked kernel is located at `arch/x86/configs/ubuntu_defconfig`.
1. Clone [the github repository](https://github.com/dgist-datalab/cxl-kernel/tree/220990494efb831170a0dd60b45bd8afeea2d023)
```
$ git clone https://github.com/dgist-datalab/cxl-kernel.git
$ cd cxl-kernel
```
2. Build & install the Linux kernel
```
$ cp arch/x86/configs/ubuntu_defconfig .config
$ make bindeb-pkg -j64
$ cd ../
$ dpkg -i linux-headers-5.17.4-... linux-image-5.17.4-... 
$ reboot
...
```

## Test 
* `test/` directory includes a script generating raw trace files (`*.vout` or `*.pout`) of Synthetic workloads automatically.
* When you run `test_synthetic.sh`, you can select which synthetic workload to run and generate only a virtual memory trace or both virtual/physical traces.
```
$ cd test/
$ sudo ./test_synthetic.sh
```
* After generating the trace file, you can plot a rough figure showing the memory address distribution of the trace file.
```
python3 after_run/graph/cg_histogram.py --input [.vout] --scatter 103
python3 after_run/graph/cg_pa_histogram.py --input [.pout] --scatter 103
```

* If you want to generate trace files of your target applications, run `run_script/run_script.sh` with your target applications following [README](https://github.com/dgist-datalab/trace_generator/tree/main/run_script).

### Test Output
* Raw trace files: `*.vout`, `*.pout`.
* These raw trace files are the input files for [Trace Translator](https://github.com/spypaul/trace_translation).
* [Trace Translator](https://github.com/spypaul/trace_translation) translates these raw trace files to trace files for [MQSim_CXL](https://github.com/spypaul/MQSim_CXL).
