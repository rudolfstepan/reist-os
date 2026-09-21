#include <reist/x86_64/graphical_session.h>
#include "mbedtls/private/sha256.h"
#include "mbedtls/platform_util.h"

void mbedtls_platform_zeroize(void *p,size_t bytes) {
    volatile unsigned char *v=p;while(bytes--)*v++=0;
}
#ifdef REIST_GRAPHICAL_FREESTANDING
void *memcpy(void *to,const void *from,size_t bytes) {
    unsigned char *d=to;const unsigned char *s=from;
    for(size_t n=0;n<bytes;n++)d[n]=s[n];return to;
}
void *memset(void *to,int value,size_t bytes) {
    unsigned char *d=to;for(size_t n=0;n<bytes;n++)d[n]=(unsigned char)value;return to;
}
#endif
int reist_graphical_hash_admit(const void *prepared,size_t bytes,
    const unsigned char expected[32],const reist_graphical_hash_ops *ops) {
    if(!prepared || bytes!=REIST_GRAPHICAL_PREPARED_HASH_BYTES || !expected ||
       !ops || !ops->clock_ms || !ops->sleep_ms)return -22;
    if((uintptr_t)prepared>UINTPTR_MAX-bytes || (uintptr_t)expected>UINTPTR_MAX-32)return -22;
    uint64_t last=ops->clock_ms(ops->context);
    if(last>UINT64_MAX-2000)return -75;
    uint64_t end=last+2000;
    mbedtls_sha256_context context;unsigned char digest[32]={0};
    mbedtls_sha256_init(&context);
    int result=mbedtls_sha256_starts(&context,0)?-5:0;
    for(size_t at=0;!result && at<bytes;at+=4096) {
        uint64_t now=ops->clock_ms(ops->context);
        if(now<last || now>=end){result=now<last?-22:-110;break;}
        last=now;size_t count=bytes-at<4096?bytes-at:4096;
        if(mbedtls_sha256_update(&context,(const unsigned char*)prepared+at,count))result=-5;
        if(!result && at+count<bytes && ops->sleep_ms(ops->context,10))result=-5;
    }
    if(!result && mbedtls_sha256_finish(&context,digest))result=-5;
    uint64_t now=ops->clock_ms(ops->context);
    if(!result && (now<last || now>=end))result=now<last?-22:-110;
    unsigned difference=0;
    for(unsigned n=0;n<32;n++)difference|=digest[n]^expected[n];
    if(!result && difference)result=-13;
    mbedtls_sha256_free(&context);mbedtls_platform_zeroize(digest,sizeof(digest));
    return result;
}
