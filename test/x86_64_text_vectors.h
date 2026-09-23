#ifndef REIST_NATIVE_TEXT_VECTORS_H
#define REIST_NATIVE_TEXT_VECTORS_H
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>
static int native_text_copy(char *a,char *b,size_t n,const char *format,...) {
    va_list first,second;va_start(first,format);va_copy(second,first);
    int x=vsnprintf(a,n,format,first),y=vsnprintf(b,n,format,second);
    va_end(second);va_end(first);return x==y?x:-1;
}
static int native_text_vectors(void) {
#define NT(x) do {if(!(x))return __LINE__;}while(0)
    char a[256],b[256];
    const char *expected="1/2/3/4/5/6/7/8/9/10;0.5/1.5/2.5/3.5/4.5/5.5/6.5/7.5/8.5/9.5;18446744073709551616";
    int n=native_text_copy(a,b,sizeof a,
        "%ld/%ld/%ld/%ld/%ld/%ld/%ld/%ld/%ld/%ld;%.1f/%.1f/%.1f/%.1f/%.1f/%.1f/%.1f/%.1f/%.1f/%.1f;%.0Lf",
        1L,2L,3L,4L,5L,6L,7L,8L,9L,10L,
        0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5,0x1p64L);
    NT(n==(int)strlen(expected)&&!strcmp(a,expected)&&!strcmp(b,expected));
    NT(snprintf(a,sizeof a,"%p",(void *)(uintptr_t)UINT64_C(0x123456789abcdef0))==18);
    NT(!strcmp(a,"0x123456789abcdef0"));
    struct { unsigned char before[8];long count;unsigned char after[8]; } guard;
    memset(&guard,0x5a,sizeof guard);
    NT(snprintf(a,4,"abcdef%ln",&guard.count)==6&&guard.count==6&&!strcmp(a,"abc"));
    for(unsigned i=0;i<8;i++)NT(guard.before[i]==0x5a&&guard.after[i]==0x5a);
#if __SIZEOF_LONG__ == 8
    NT(snprintf(a,sizeof a,"%ld/%lu/%zu/%td",LONG_MIN,ULONG_MAX,(size_t)UINT64_C(0x10000000000),(ptrdiff_t)-UINT64_C(0x10000000000))>0);
    NT(!strcmp(a,"-9223372036854775808/18446744073709551615/1099511627776/-1099511627776"));
#endif
    return 0;
#undef NT
}
#endif
