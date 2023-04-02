#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>
#include <time.h>
//#include <jemalloc/jemalloc.h>
#include <semaphore.h>
#include <stdexcept>
#include <sys/types.h>
#include <sys/wait.h>
#include <error.h>
#include <iostream>
#include <random>
#include "mymalloc.h"

#define K (1024)
#define M (1048576)
#define G (1073741824)

#define SEQREAD	  0
#define SEQWRITE  1
#define RANDREAD  2
#define RANDWRITE 3
#define HOTREAD   4
#define HOTWRITE  5

#if 0
#include <libc.h>
static void*(*original_malloc)(size_t) = NULL;

void* malloc(size_t size) {
	if (!original_malloc) {
		original_malloc = (void *(*)(size_t)) __libc_dlsym(RTLD_NEXT, "malloc");
	}
	printf("Intercepting malloc(%ld)\n", size);
	void* ptr = original_malloc(size);
	printf("Allocated %p\n", ptr);
	return ptr;
}
#endif
#if 0
void *mymalloc(size_t size) {
	printf("Intercepting malloc(%ld)\n", size);
	void* ptr = malloc(size);
	printf("Allocated %p\n", ptr);
	return ptr;
}
#define malloc(size) mymalloc(size)
#endif


char* buf;

void print_gettime_thr(struct timespec begin, struct timespec end, uint64_t num_op, const char text[]) {
	std::cout << "[TIME] " << text << ": " << (end.tv_sec-begin.tv_sec) + (end.tv_nsec-begin.tv_nsec)/1000000000.0 << std::endl;
	auto elapsed = (end.tv_sec-begin.tv_sec) + (end.tv_nsec-begin.tv_nsec)/1000000000.0;
	std::cout << "[Throughput (op/ms)] " << text << ": " << num_op / (elapsed*1000.0) << "\n";
}
uint64_t int_hash(uint64_t x) {
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    x = x ^ (x >> 31);
    return x;
}
static int random_select(int prob) {
	double r = rand() / (double)RAND_MAX; // (0.0 - 1.0)
	double dr = r * 100.0f; // (0.0 - 100.0)
	if (dr <= prob) {
		return 1;
	} else {
		return 0;
	}
}

void test_seq(char type, char* mem, uint64_t memsize, int rwunit, uint64_t num_op) {
	uint64_t num_blk = memsize/rwunit;

	if (type == SEQREAD) {
		for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
			memcpy(buf, &mem[(op_idx%num_blk)*rwunit], rwunit);
		}
	} else if (type == SEQWRITE) {
		for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
			memcpy(&mem[(op_idx%num_blk)*rwunit], buf, rwunit);
		}
	} else{
		printf("Test type error\n");
		exit(0);
	}
}
void test_rand(char type, char* mem, uint64_t memsize, int rwunit, uint64_t num_op) {
	uint64_t last_idx = memsize/rwunit - 1;
	std::random_device rd1;
	std::mt19937_64 eng1(rd1());
	std::uniform_int_distribution<uint64_t> rand_dist(0UL, last_idx);

	if (type == RANDREAD) {
		for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
			memcpy(buf, &mem[rand_dist(eng1)*rwunit], rwunit);
		}
	} else if (type == RANDWRITE) {
		for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
			memcpy(&mem[rand_dist(eng1)*rwunit], buf, rwunit);
		}
	} else {
		printf("Test type error\n");
		exit(0);
	}
}
void test_hot(char type, char* mem, uint64_t memsize, int rwunit, uint64_t num_op, int p_hot) {
	uint64_t num_blk = memsize / rwunit;
	uint64_t num_hotblk = (uint64_t)(num_blk * ((double)(100-p_hot))/100);
	uint64_t target_bidx;
	std::random_device rd_hot;
	std::mt19937_64 eng_hot(rd_hot());
	std::uniform_int_distribution<uint64_t> hot_range(0UL, num_hotblk - 1UL);
	std::random_device rd_cold;
	std::mt19937_64 eng_cold(rd_cold());
	std::uniform_int_distribution<uint64_t> cold_range(num_hotblk, num_blk - 1UL);

	if (type == HOTREAD) {
		for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
			if (random_select(p_hot)) {
				target_bidx = hot_range(eng_hot);
			} else {
				target_bidx = cold_range(eng_cold);
			}
			//target_bidx = int_hash(target_bidx) % num_op;
			memcpy(buf, &mem[target_bidx*rwunit], rwunit);
		}
	} else if (type == HOTWRITE) {
		for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
			if (random_select(p_hot)) {
				target_bidx = hot_range(eng_hot);
			} else {
				target_bidx = cold_range(eng_cold);
			}
			//target_bidx = int_hash(target_bidx) % num_op;
			memcpy(&mem[target_bidx*rwunit], buf, rwunit);
		}
	} else {
		printf("Test type error\n");
		exit(0);
	}
}

void test(char type, char* mem, uint64_t memsize, int rwunit, uint64_t num_op, int p_hot) {
	switch(type) {
		case SEQREAD:
			printf("Seq Read! memsize: %lu, rwunit: %d, num_op: %lu\n", memsize, rwunit, num_op);
			test_seq(type, mem, memsize, rwunit, num_op);
			break;
		case SEQWRITE:
			printf("Seq Write! memsize: %lu, rwunit: %d, num_op: %lu\n", memsize, rwunit, num_op);
			test_seq(type, mem, memsize, rwunit, num_op);
			break;
		case RANDREAD:
			printf("Rand Read! memsize: %lu, rwunit: %d, num_op: %lu\n", memsize, rwunit, num_op);
			test_rand(type, mem, memsize, rwunit, num_op);
			break;
		case RANDWRITE:
			printf("Rand Write! memsize: %lu, rwunit: %d, num_op: %lu\n", memsize, rwunit, num_op);
			test_rand(type, mem, memsize, rwunit, num_op);
			break;
		case HOTREAD:
			printf("Hot Read! memsize: %lu, rwunit: %d, num_op: %lu, p_hot: %d\n", memsize, rwunit, num_op, p_hot);
			test_hot(type, mem, memsize, rwunit, num_op, p_hot);
			break;
		case HOTWRITE:
			printf("Hot Write! memsize: %lu, rwunit: %d, num_op: %lu, p_hot: %d\n", memsize, rwunit, num_op, p_hot);
			test_hot(type, mem, memsize, rwunit, num_op, p_hot);
			break;
		default:
			break;
	}
}

void _bench(uint64_t memsize, int rwunit) {
	struct timespec test1_s, test1_f;
	uint64_t num_op = memsize/rwunit;
	char* mem = (char*)malloc(memsize);
	buf = (char*)malloc(rwunit);
	memset(buf, 1, rwunit);
	printf("&mem[0]: %p, &mem[%lu]: %p\n", &mem[0], memsize-1, &mem[memsize-1]);

	clock_gettime(CLOCK_MONOTONIC, &test1_s);
	//test(SEQWRITE, mem, memsize, rwunit, num_op, 0);
	test(HOTWRITE, mem, memsize, rwunit, num_op, 90);
	clock_gettime(CLOCK_MONOTONIC, &test1_f);

	//print_gettime_thr(test1_s, test1_f, num_op, "SeqWrite");
	print_gettime_thr(test1_s, test1_f, num_op, "HotWrite");

	free(buf);
	free(mem);

}

void bench(void) {
	//uint64_t memsize = 1UL*M;
	uint64_t memsize = 512UL*M;
	int rwunit = 4096;

	/* Each _bench() calls one malloc() */
	_bench(memsize, rwunit);
}

#if 0
void bench(char* mem) {

	char buf[UNIT];
	memset(buf, 1, UNIT);

	/* seq read */
	uint64_t num_op;
	num_op = memsize / UNIT;
	for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
		memcpy(buf, mem[op_idx*UNIT], UNIT);
	}

	/* seq write */
	uint64_t num_op;
	num_op = memsize / UNIT;
	for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
		memcpy(mem[op_idx*UNIT], buf, UNIT);
	}

	/* rand read */
	uint64_t num_op;
	num_op = memsize / UNIT;
	std::random_device rd1;
	std::mt19937_64 eng1(rd1());
	std::uniform_int_distribution<uint64_t> rand_dist(0UL, (uin64_t)(num_op-1));
	for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
		memcpy(buf, mem[rand_dist(eng1)*UNIT], UNIT);
	}

	/* rand write */
	uint64_t num_op;
	num_op = memsize / UNIT;
	std::random_device rd1;
	std::mt19937_64 eng1(rd1());
	std::uniform_int_distribution<uint64_t> rand_dist(0UL, (uin64_t)(num_op-1));
	for (uint64_t op_idx=0; op_idx<num_op; op_idx++) {
		memcpy(mem[rand_dist(eng1)*UNIT], buf, UNIT);
	}

}
#endif

int main(void) 
{
	//struct timespec main_s, main_f;

	/* test마다 새로 할당? 새로 할당할거면 그냥 프로그램을 새로 하면 되니, 한 할당으로 여러 test를 할 수 있는 게 더 좋아보임 */
	/* 근데 그럴거면 test 인자가 dist/rw 뿐이고 size가 없음. */

	bench();

	return 0;
}
