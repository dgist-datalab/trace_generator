#include<iostream>
#include<unordered_map>
using namespace std;

#define NUM_OPS (1UL << 24)

int main(){
	
	unordered_map<uint64_t, uint64_t> M;

	for(uint64_t i =0; i < NUM_OPS; i++){
		M[i] =i;
	}


	for(auto i =0 ; i < M.bucket_count(); i++){
		for(auto it = M.begin(i); it != M.end(i); it++){
			auto temp {it->first};
			auto temp2{it->second};
			temp += temp2;
		}
	
	}
	return 0; 
}
