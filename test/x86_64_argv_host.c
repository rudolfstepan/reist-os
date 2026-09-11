#include "../arch/x86_64/proc/startup_stack.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("ARGV_FAIL line=%d\n",__LINE__);return 1;}} while(0)
static _Alignas(16) unsigned char source[4096],target[4096];
static struct reist_x64_startup ctx;
static uint64_t word(const unsigned char *p) {uint64_t v;memcpy(&v,p,8);return v;}
static void put(unsigned offset,uint64_t value) {memcpy(source+offset,&value,8);}
static void init(unsigned argc,unsigned len,int alias) {
    memset(source,0x77,sizeof source);memset(target,0xa5,sizeof target);
    ctx=(struct reist_x64_startup){source,target,UINT64_C(0x400000000),
        UINT64_C(0x800001000),argc?UINT64_C(0x400000020):0,argc,UINT64_C(0x1122334455667788)};
    for(unsigned i=0;i<argc;i++) {
        unsigned offset=256+(alias?0:i*128);
        put(32+i*8,ctx.source_base+offset);
        for(unsigned j=0;j<len;j++)source[offset+j]=(unsigned char)(0x81+(j%100));
        source[offset+len-1]=0;
    }
}
static int positive(void) {
    const unsigned lens[]={1,2,15,16,17,127,128};
    unsigned char oldsrc[4096],expected[4096];
    for(unsigned n=0;n<=8;n++)for(unsigned k=0;k<sizeof lens/sizeof *lens;k++)for(unsigned alias=0;alias<2;alias++) {
        unsigned len=lens[k],stride=(len+15)&~15u,head=((n+7)*8+15)&~15u;
        if(head<96)head=96;
        unsigned size=head+n*stride,start=4096-size;
        init(n,len,alias);memcpy(oldsrc,source,4096);memset(expected,0xa5,4096);
        struct reist_x64_startup old=ctx;
        CHECK(reist_x64_startup_stack(&ctx,0)==(int64_t)(ctx.stack_top-size));
        CHECK(!memcmp(target,expected,4096)&&!memcmp(source,oldsrc,4096)&&!memcmp(&ctx,&old,sizeof ctx));
        CHECK(reist_x64_startup_stack(&ctx,1)==(int64_t)(ctx.stack_top-size));
        memset(expected+start,0,size);
        uint64_t value=n;memcpy(expected+start,&value,8);
        for(unsigned i=0;i<n;i++) {
            value=ctx.stack_top-size+head+i*stride;memcpy(expected+start+8+i*8,&value,8);
            memcpy(expected+start+head+i*stride,source+256+(alias?0:i*128),len);
        }
        value=0x52534901;memcpy(expected+start+(n+3)*8,&value,8);
        value=ctx.ipc_handle;memcpy(expected+start+(n+4)*8,&value,8);
        CHECK(!memcmp(target,expected,4096)&&!memcmp(source,oldsrc,4096)&&!memcmp(&ctx,&old,sizeof ctx));
    }
    init(2,16,0);strcpy((char*)source+256,"/shell/child");strcpy((char*)source+384,"token77");
    CHECK(reist_x64_startup_stack(&ctx,1)==(int64_t)(ctx.stack_top-128));
    CHECK(word(target+4096-120)==ctx.stack_top-32 && word(target+4096-112)==ctx.stack_top-16);
    CHECK(!strcmp((char*)target+4096-32,"/shell/child")&&!strcmp((char*)target+4096-16,"token77"));
    init(1,1,0);source[4095]=0;put(32,ctx.source_base+4095);
    CHECK(reist_x64_startup_stack(&ctx,1)==(int64_t)(ctx.stack_top-112));
    return 0;
}
static int negative(void) {
    unsigned char src[4096],dst[4096];
    for(unsigned i=0;i<20;i++) {
        init(2,8,0);int64_t error=-14;unsigned op=1;
        switch(i) {
        case 0:ctx.argc=9;error=-7;break;
        case 1:ctx.argc=UINT64_MAX;error=-7;break;
        case 2:ctx.argv=0;break;
        case 3:ctx.argv++;break;
        case 4:ctx.argv=ctx.source_base+4096-8;break;
        case 5:put(32,0);break;
        case 6:put(32,ctx.source_base-1);break;
        case 7:put(32,UINT64_MAX);break;
        case 8:memset(source+256,1,128);error=-7;break;
        case 9:put(32,ctx.source_base+4095);break;
        case 10:ctx.argc=0;break;
        case 11:ctx.source=NULL;error=-22;break;
        case 12:ctx.destination=NULL;error=-22;break;
        case 13:ctx.destination=source;error=-22;break;
        case 14:ctx.source_base++;error=-22;break;
        case 15:ctx.source_base=UINT64_MAX-4095;error=-22;break;
        case 16:ctx.stack_top=4096;error=-22;break;
        case 17:ctx.stack_top=UINT64_C(0x800000000000);error=-22;break;
        case 18:op=2;error=-22;break;
        case 19:ctx.destination=source+16;error=-22;break;
        }
        memcpy(src,source,4096);memcpy(dst,target,4096);struct reist_x64_startup old=ctx;
        CHECK(reist_x64_startup_stack(&ctx,op)==error);
        CHECK(!memcmp(src,source,4096)&&!memcmp(dst,target,4096)&&!memcmp(&old,&ctx,sizeof ctx));
        if(i<=11 || (i>=14 && i<=17)) {
            CHECK(reist_x64_startup_stack(&ctx,0)==error);
            CHECK(!memcmp(src,source,4096)&&!memcmp(dst,target,4096)&&!memcmp(&old,&ctx,sizeof ctx));
        }
    }
    CHECK(reist_x64_startup_stack(NULL,0)==-22);
    init(2,8,0);ctx.destination=NULL;
    CHECK(reist_x64_startup_stack(&ctx,0)==(int64_t)(ctx.stack_top-128));
    return 0;
}
int main(void) {CHECK(!positive());CHECK(!negative());puts("X86_64_ARGV_HOST_OK counts=9 layouts=126 nonmutation=20");return 0;}
