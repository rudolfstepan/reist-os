#define main retained_text_main
#include "text_host.c"
#undef main
#include "x86_64_text_vectors.h"
int main(void) {
    int result=retained_text_main();if(result)return result;
    result=native_text_vectors();
    if(result){printf("NATIVE_TEXT_FAIL line=%d\n",result);return 1;}
    printf("NATIVE_TEXT_HOST_OK pointer_bits=%u long_bits=%u\n",
        (unsigned)(sizeof(void*)*8),(unsigned)(sizeof(long)*8));return 0;
}
