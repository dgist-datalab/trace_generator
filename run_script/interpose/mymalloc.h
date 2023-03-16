#ifndef _MYMALLOC_
#define _MYMALLOC_

#define malloc(size) mymalloc(size)
#define free(ptr) myfree(ptr)

void *mymalloc(size_t size);		// Prototyping
void myfree(void *ptr);	

#endif // ! _MYMALLOC_
