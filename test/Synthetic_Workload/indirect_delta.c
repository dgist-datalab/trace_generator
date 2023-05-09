#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#define ROW_SIZE (4UL)
#define COL_SIZE (4UL)

#define WORK_SET (1UL << 22)


int main(){
	
	uint8_t*** ALL = (uint8_t***) malloc(WORK_SET*sizeof(uint8_t**));

	for(uint64_t ops =0; ops < WORK_SET; ops++){
	
	
		uint8_t** M = (uint8_t**)malloc(ROW_SIZE*sizeof(uint8_t*));

    		for(uint64_t i =0; i < ROW_SIZE; i++){
        		M[i] = (uint8_t*)malloc(COL_SIZE*sizeof(uint8_t));
    		}
		ALL[ops] = M;

	}

	for(uint64_t ops = 0 ; ops < WORK_SET - 3; ops += 3){
		uint8_t** M = ALL[ops];
		uint8_t** M2 = ALL[ops+1];
		uint8_t**M3 = ALL[ops+2];

		for(uint64_t i =0; i < ROW_SIZE; i++){
        		for(uint64_t j = 0; j < COL_SIZE; j++){
				for(uint64_t k =0; k < ROW_SIZE; k++){
					M3[i][j] = M[i][k] * M2[k][j];
				}		
			}		
		}
	}


    
    return 0;
}
