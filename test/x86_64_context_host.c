#include "../arch/x86_64/proc/context_core.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("CONTEXT_FAIL line=%d\n",__LINE__);return 1;}} while(0)
struct sample {
    uint64_t before, task[32], frame[22], after;
    struct reist_x64_context ctx;
};
/* Independent C layout oracle: frame index -> task index. */
static const unsigned target[15]={26,25,24,23,31,22,21,20,19,18,17,16,30,15,29};
static void init(struct sample *s,unsigned kind) {
    memset(s,0,sizeof *s);
    s->before=0x123456789;s->after=0x987654321;
    for(unsigned i=0;i<32;i++)s->task[i]=UINT64_C(0xabcabc0000000000)+i;
    for(unsigned i=0;i<15;i++)s->frame[i]=UINT64_C(0xfedcba9876543210)+i;
    s->task[0]=2;s->task[1]=UINT32_MAX;s->task[2]=UINT64_C(0x123456000);
    s->ctx=(struct reist_x64_context){s->task,UINT32_MAX,s->task[2],
        UINT64_C(0x400000000),UINT64_C(0x400001000),kind};
    s->frame[15]=kind?32:256;s->frame[16]=0;
    s->frame[17]=UINT64_C(0x1234567890);s->frame[18]=0x33;
    s->frame[19]=kind?0x202:2;s->frame[20]=s->ctx.stack_top;s->frame[21]=0x2b;
    if(!kind){s->frame[12]=s->frame[17];s->frame[4]=s->frame[19];}
}
static int denied(struct sample *s,unsigned op) {
    struct sample old=*s;
    return !reist_x64_context_apply(&s->ctx,s->frame,op) && !memcmp(s,&old,sizeof old);
}
static int positive(void) {
    struct sample s;
    for(unsigned kind=0;kind<2;kind++)for(unsigned offset=0;offset<=4096;offset++) {
        init(&s,kind);s.frame[20]=s.ctx.stack_low+offset;
        struct sample old=s;
        CHECK(reist_x64_context_apply(&s.ctx,s.frame,0)==1);
        CHECK(!memcmp(&s,&old,sizeof s));
        CHECK(reist_x64_context_apply(&s.ctx,s.frame,1)==1);
        for(unsigned i=0;i<15;i++) old.task[target[i]]=s.frame[i];
        old.task[12]=s.frame[17];old.task[13]=s.frame[20];old.task[14]=s.frame[19];
        if(!kind)old.task[29]=0;
        CHECK(!memcmp(&s,&old,sizeof s));
    }
    /* Every permitted arithmetic flag and IF are preserved. */
    init(&s,1);s.frame[19]=0x10202;
    CHECK(reist_x64_context_apply(&s.ctx,s.frame,1)==1 && s.task[14]==0x10202);
    for(unsigned kind=0;kind<2;kind++)for(unsigned flags=0;flags<4096;flags++) {
        if((flags&~0xad7u) || !(flags&2) || (kind && !(flags&512)))continue;
        init(&s,kind);s.frame[19]=flags;if(!kind)s.frame[4]=flags;
        CHECK(reist_x64_context_apply(&s.ctx,s.frame,1)==1 && s.task[14]==flags);
    }
    return 0;
}
static int negative(void) {
    struct sample s;
    for(unsigned kind=0;kind<2;kind++) {
        for(unsigned state=0;state<=9;state++)if(state!=2) {
            init(&s,kind);s.task[0]=state;CHECK(denied(&s,1));
        }
        for(unsigned bit=0;bit<64;bit++)if(!((kind?UINT64_C(0x10ad7):UINT64_C(0xad7))&(UINT64_C(1)<<bit))) {
            init(&s,kind);s.frame[19]|=UINT64_C(1)<<bit;
            if(!kind)s.frame[4]=s.frame[19];CHECK(denied(&s,1));
        }
        const uint64_t invalid_addresses[]={0,4095,UINT64_C(0x800000000000),UINT64_C(0xffff800000000000),UINT64_MAX};
        for(unsigned i=0;i<sizeof invalid_addresses/sizeof *invalid_addresses;i++) {
            init(&s,kind);s.frame[17]=invalid_addresses[i];
            if(!kind)s.frame[12]=s.frame[17];CHECK(denied(&s,1));
            init(&s,kind);s.frame[20]=invalid_addresses[i];CHECK(denied(&s,1));
        }
        for(unsigned i=0;i<18;i++) {
            init(&s,kind);
            switch(i) {
            case 0:s.ctx.generation=0;break;
            case 1:s.ctx.generation=UINT64_C(0x1ffffffff);break;
            case 2:s.task[1]--;break;
            case 3:s.ctx.cr3=0;break;
            case 4:s.ctx.cr3++;s.task[2]++;break;
            case 5:s.task[2]+=4096;break;
            case 6:s.ctx.stack_low=s.ctx.stack_top;break;
            case 7:s.ctx.stack_top=UINT64_MAX;break;
            case 8:s.ctx.stack_low=0;break;
            case 9:s.frame[20]=s.ctx.stack_low-1;break;
            case 10:s.frame[20]++;break;
            case 11:s.frame[15]++;break;
            case 12:s.frame[16]=1;break;
            case 13:s.frame[18]=8;break;
            case 14:s.frame[21]=0x10;break;
            case 15:s.frame[19]&=~UINT64_C(2);if(!kind)s.frame[4]=s.frame[19];break;
            case 16:s.ctx.kind=2;break;
            case 17:s.ctx.task=NULL;break;
            }
            CHECK(denied(&s,0));CHECK(denied(&s,1));
        }
        init(&s,kind);CHECK(denied(&s,2));
    }
    init(&s,1);s.frame[19]=2;CHECK(denied(&s,1));
    init(&s,0);s.frame[12]++;CHECK(denied(&s,1));
    init(&s,0);s.frame[4]++;CHECK(denied(&s,1));
    CHECK(!reist_x64_context_apply(NULL,s.frame,1));
    CHECK(!reist_x64_context_apply(&s.ctx,NULL,1));
    return 0;
}
int main(void) {
    CHECK(!positive());CHECK(!negative());
    puts("X86_64_CONTEXT_HOST_OK kinds=2 registers=18 stack_offsets=4097 nonmutation=1");return 0;
}
