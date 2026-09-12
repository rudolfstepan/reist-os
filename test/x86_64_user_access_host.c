#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../arch/x86_64/mm/user_access.h"
#define NX (UINT64_C(1)<<63)
#define BASE UINT64_C(0x400000)
#define BAD (-4096)
static _Alignas(4096) uint64_t pages[4][512];
static uint64_t task[32], frames[4];
static ReistX64UserAccess binding;
static int failed, calls, backend_bad;
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d\n",__LINE__);return 1;}} while(0)
void *__attribute__((sysv_abi)) reist_x64_mapping_pointer64(uint64_t frame) {
    ++calls;
    for(unsigned i=0;i<4;i++)if(frame==frames[i]) {
        if(backend_bad==(int)i+1)return 0;
        if(backend_bad==5 && i==3)return pages[0];
        return pages[i];
    }
    failed=1;return 0;
}
static void reset(void) {
    memset(pages,0,sizeof(pages));memset(task,0,sizeof(task));
    for(unsigned i=0;i<4;i++)frames[i]=0x4000000+4096*i;
    task[0]=2;task[1]=42;task[2]=frames[0];task[3]=0x5008000;
    binding=(ReistX64UserAccess){task,frames,42,frames[0]};
    pages[0][0]=frames[1]|7;pages[1][0]=frames[2]|7;pages[2][2]=frames[3]|7;
    for(unsigned i=0;i<9;i++)pages[3][i]=(0x5000000+4096*i)|7|NX;
    failed=calls=backend_bad=0;
}
static int64_t access(uint64_t addr,uint64_t size,uint64_t rights) {
    uint64_t before[4][512],t[32],f[4];ReistX64UserAccess b=binding;
    memcpy(before,pages,sizeof(pages));memcpy(t,task,sizeof(t));memcpy(f,frames,sizeof(f));
    int64_t result=reist_x64_user_access(&binding,addr,size,rights);
    if(memcmp(before,pages,sizeof(pages))||memcmp(t,task,sizeof(t))||memcmp(f,frames,sizeof(f))||
       memcmp(&b,&binding,sizeof(b))||failed||calls>4)return -9999;
    calls=0;return result;
}
int main(void) {
    reset();
    /* Every offset and page edge, both data directions. Independent oracle. */
    for(unsigned page=0;page<9;page++)for(unsigned off=0;off<4096;off++) {
        uint64_t address=BASE+4096*page+off;
        int expected=address+140<=BASE+9*4096;
        CHECK(access(address,140,4)==expected);CHECK(access(address,140,2)==expected);
    }
    for(unsigned level=0;level<4;level++)for(unsigned bits=0;bits<8;bits++) {
        reset();uint64_t *entry=&pages[level][level==2?2:0];
        *entry=(*entry&~UINT64_C(7))|bits;
        CHECK(access(BASE,64,4)==((bits&5)==5));
        CHECK(access(BASE,64,2)==((bits&7)==7));
    }
    for(unsigned page=0;page<9;page++) {
        reset();pages[3][page]=0;
        CHECK(access(BASE+4096*page,1,4)==0);
        if(page)CHECK(access(BASE+4096*page-64,140,4)==0);
        reset();pages[3][page]&=~UINT64_C(2);
        CHECK(access(BASE+4096*page,1,4)==1);CHECK(access(BASE+4096*page,1,2)==0);
        if(page)CHECK(access(BASE+4096*page-64,140,2)==0);
    }
    reset();uint64_t addresses[]={0,BASE-1,BASE+9*4096,UINT64_MAX-63,UINT64_C(0x800000000000),UINT64_C(0xffff800000000000)};
    for(unsigned i=0;i<sizeof(addresses)/sizeof(*addresses);i++)CHECK(access(addresses[i],140,4)==0);
    CHECK(access(BASE,0,4)==0);CHECK(access(BASE,141,4)==0);CHECK(access(BASE,UINT64_MAX,4)==0);
    CHECK(access(BASE,1,6)==0);CHECK(access(BASE,1,UINT64_C(0x100000004))==0);
    for(unsigned i=0;i<4;i++) {
        reset();frames[i]=0;CHECK(access(BASE,1,4)==BAD);
        reset();frames[i]++;CHECK(access(BASE,1,4)==BAD);
        reset();frames[i]=0x8000000;CHECK(access(BASE,1,4)==BAD);
        reset();backend_bad=i+1;CHECK(access(BASE,1,4)==BAD);
    }
    reset();backend_bad=5;CHECK(access(BASE,1,4)==BAD);
    reset();frames[3]=frames[1];CHECK(access(BASE,1,4)==BAD);
    reset();binding.generation++;CHECK(access(BASE,1,4)==BAD);
    reset();task[0]=1;CHECK(access(BASE,1,4)==BAD);
    reset();binding.active_cr3=frames[1];CHECK(access(BASE,1,4)==BAD);
    reset();task[2]=frames[1];CHECK(access(BASE,1,4)==BAD);
    for(unsigned level=0;level<4;level++) {
        reset();pages[level][level==2?2:0]|=128;CHECK(access(BASE,1,4)==BAD);
        reset();pages[level][level==2?2:0]|=UINT64_C(1)<<52;CHECK(access(BASE,1,4)==BAD);
        reset();pages[level][level==2?2:0]|=32;CHECK(access(BASE,1,4)==1);
    }
    reset();pages[3][0]|=64;CHECK(access(BASE,1,4)==1);
    reset();pages[0][0]^=4096;CHECK(access(BASE,1,4)==BAD);
    reset();pages[3][0]=frames[1]|7|NX;CHECK(access(BASE,1,4)==BAD);
    reset();pages[3][8]^=4096;CHECK(access(BASE+8*4096,1,4)==BAD);
    puts("USER_ACCESS_HOST_OK offsets=36864 directions=2 bound=140 levels=4 nonmutation=1");return 0;
}
