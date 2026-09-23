#define main retained_math_main
#include "math_host.c"
#undef main
#include "x86_64_math_vectors.h"
int main(void) {
    int result=retained_math_main();if(result)return result;
    result=native_lrint_vectors();
    if(result){fprintf(stderr,"NATIVE_LRINT_FAIL line=%d\n",result);return 1;}
    printf("NATIVE_MATH_HOST_OK pointer_bits=%u long_bits=%u\n",
        (unsigned)(sizeof(void*)*8),(unsigned)(sizeof(long)*8));return 0;
}
