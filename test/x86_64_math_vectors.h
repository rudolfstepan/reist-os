#ifndef REIST_NATIVE_MATH_VECTORS_H
#define REIST_NATIVE_MATH_VECTORS_H
#include <math.h>
#include <fenv.h>
#include <limits.h>
/* C long follows the compiler's actual ABI: LP64 in the ELF64 guest;
 * the Windows numeric host has LLP64. Never pretend they are identical. */
static int native_lrint_vectors(void) {
#define NATIVE_CHECK(x) do {if(!(x))return __LINE__;}while(0)
    const int modes[]={FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO};
    const long positive[]={2,1,2,1},negative[]={-2,-2,-1,-1};
    for(unsigned n=0;n<4;n++) {
        NATIVE_CHECK(!fesetround(modes[n])&&!feclearexcept(FE_ALL_EXCEPT));
        volatile double p=1.5,m=-1.5;
        NATIVE_CHECK(lrint(p)==positive[n]&&lrint(m)==negative[n]);
        NATIVE_CHECK(fetestexcept(FE_INEXACT)&FE_INEXACT);
    }
    NATIVE_CHECK(!fesetround(FE_TONEAREST)&&!feclearexcept(FE_ALL_EXCEPT));
#if __SIZEOF_LONG__ == 8
    volatile double high=0x1p40,low=-0x1p63,last=0x1.fffffffffffffp62,beyond=0x1p63;
    NATIVE_CHECK(lrint(high)==0x10000000000L&&lrint(-high)==-0x10000000000L);
    NATIVE_CHECK(lrint(low)==LONG_MIN&&lrint(last)==9223372036854774784L);
#else
    volatile double low=-0x1p31,last=2147483647.0,beyond=0x1p31;
    NATIVE_CHECK(lrint(low)==LONG_MIN&&lrint(last)==LONG_MAX);
#endif
    NATIVE_CHECK(!fetestexcept(FE_ALL_EXCEPT));
    volatile double invalids[]={NAN,INFINITY,-INFINITY,beyond};
    for(unsigned n=0;n<4;n++) {
        NATIVE_CHECK(!feclearexcept(FE_ALL_EXCEPT));
        volatile long result=lrint(invalids[n]);(void)result;
        NATIVE_CHECK(fetestexcept(FE_INVALID)&FE_INVALID);
    }
    NATIVE_CHECK(!feclearexcept(FE_ALL_EXCEPT));
    return 0;
#undef NATIVE_CHECK
}
#endif
