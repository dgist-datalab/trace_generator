#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define WORK_SIZE (1L << 33) //1G Bytes
#define ACCESS_SIZE 64L //64 Bytes
#define STRIDE_SIZE (64L*16) //64 Bytes
#define ACCESS_COUNT (WORK_SIZE/STRIDE_SIZE)


int main(){
	uint64_t count = 0;

	uint8_t *addr = (uint8_t*)malloc((WORK_SIZE)*sizeof(uint8_t));
	memset(addr, 1, WORK_SIZE * sizeof(uint8_t));
	while(count != ACCESS_COUNT){

		for(uint16_t i = 0; i < ACCESS_SIZE; i ++){
			addr[i] = addr[i] + 1;
		}
		
		
		addr += STRIDE_SIZE;

		count++;
	}



	return 0;
}