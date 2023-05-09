#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define WORK_SIZE (1 << 27) //2G Bytes


void add(uint64_t* h, uint64_t* lp, uint64_t value){
    uint64_t insert_at = *lp +1;
    *lp = insert_at;
    h[insert_at] = value;
    
    uint64_t p = insert_at;

    while(p != 0){
        uint64_t parent = (p -1)/2;

        if(h[parent] > h[p]){
            uint8_t temp = h[p];
            h[p] = h[parent];
            h[parent] = temp;
            p = parent;
        }else{
            return;
        }
    }
}
void delete(uint64_t* h, uint64_t* lp){
    h[0] = h[*lp];
    *lp = *lp -1;

    uint64_t p = 0;

    while(p <= *lp){
        uint64_t lc =2*p +1;
        uint64_t rc =2*p +2;

        if(lc <= *lp){
            if( lc!= *lp ){
                uint64_t ep = 0;

                if(h[lc] > h[rc]) ep = rc;
                else ep = lc;

                if(h[p] > h[ep]){
                    int8_t temp = h[p];
                    h[p] = h[ep];
                    h[ep] = temp;
                    p = ep;

                }else{
                    return;
                }

            }else{
                if(h[p] > h[lc]){
                    uint8_t temp = h[p];
                    h[p] = h[lc];
                    h[lc] = temp;
                    p = lc;
                }
                else{
                    return;
                }
            }

        }else{
            return;
        }


    }


}

int main(){
    uint64_t last_position = 0;
    
    uint64_t* h = (uint64_t*)malloc(sizeof(uint64_t)*WORK_SIZE);

    h[0] = (uint64_t)rand()+1;


    for(uint64_t i = 0;  i < WORK_SIZE -1 ; i++){
        if (i % (1<<15) == 1){
            delete(h, &last_position);
        }
        add(h, &last_position, (uint64_t)rand()+1);
        //printf("%lu ", last_position);
    }

    // for(uint64_t i = 0;  i < WORK_SIZE ; i++){
    //     printf("%lu ", h[i]);
    // }


    return 0; 
}