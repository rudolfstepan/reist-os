#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/graphical_session.h>
#include "mbedtls/private/sha256.h"
#include "expected_hash.h"
static unsigned char prepared[REIST_GRAPHICAL_PREPARED_HASH_BYTES];
static uint64_t stamp;static unsigned sleeps,mode;
static uint64_t clock_ms(void *p){(void)p;return mode==3&&sleeps?0:stamp;}
static int sleep_ms(void *p,unsigned ms){(void)p;assert(ms==10);sleeps++;stamp+=mode==2?1000:ms;return mode==1?-5:0;}
static int admit(unsigned fault) {
    reist_graphical_hash_ops ops={0,clock_ms,sleep_ms};mode=fault;stamp=100;sleeps=0;
    return reist_graphical_hash_admit(prepared,sizeof(prepared),expected,&ops);
}
int main(void) {
    unsigned char digest[32];
    static const unsigned char abc[32]={0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
        0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,0x96,0x17,
        0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
    assert(!mbedtls_sha256((const unsigned char*)"abc",3,digest,0));assert(!memcmp(digest,abc,32));
    for(unsigned n=0;n<sizeof(prepared);n++)prepared[n]=(unsigned char)(n*17+n/4096);
    assert(!admit(0));assert(sleeps==64 && stamp==740);
    /* Header, rights, padding and every prepared page, including zero-fill. */
    const unsigned offsets[]={0,8,12,16,24,88,95,96,sizeof(prepared)-1};
    for(unsigned n=0;n<sizeof(offsets)/sizeof(offsets[0]);n++) {
        prepared[offsets[n]]^=1;assert(admit(0)==-13);prepared[offsets[n]]^=1;
    }
    for(unsigned n=0;n<64;n++){prepared[96+4096*n]^=1;assert(admit(0)==-13);prepared[96+4096*n]^=1;}
    assert(admit(1)==-5 && sleeps==1);
    assert(admit(2)==-110 && sleeps==2);
    assert(admit(3)==-22 && sleeps==1);
    reist_graphical_hash_ops ops={0,clock_ms,sleep_ms};mode=0;stamp=UINT64_MAX;
    assert(reist_graphical_hash_admit(prepared,sizeof(prepared),expected,&ops)==-75);
    assert(reist_graphical_hash_admit(prepared,sizeof(prepared)-1,expected,&ops)==-22);
    assert(reist_graphical_hash_admit(0,sizeof(prepared),expected,&ops)==-22);
    puts("GRAPHICAL_HASH_OK");return 0;
}
