#ifdef COMPILETIME
#include <stdio.h>
#include <malloc.h>

/* malloc에 대한 Wrapper Function */
void *mymalloc(size_t size) {		
	void *ptr = malloc(size);		

	fprintf(stderr, "^m b %zu %p\n", size, ptr);
	//printf("malloc(%d)=%p\n", (int)size, ptr);		
    
	return ptr;
}

/* free에 대한 Wrapper Function */
void myfree(void *ptr) {
	free(ptr);						
	fprintf(stderr, "^m e %p\n", ptr);
	//printf("free(%p)\n", ptr);		
}
#endif



