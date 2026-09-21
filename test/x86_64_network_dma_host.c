#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "arch/x86_64/devices/network_dma.h"
#undef assert
#define assert(x) do {if(!(x)){fprintf(stderr,"check failed at %u: %s\n",__LINE__,#x);abort();}}while(0)
static unsigned reads,writes;static uint32_t config=1,address,regs[64];static int stuck;
static uint32_t input(void *ctx,unsigned port,unsigned width) {
    (void)ctx;(void)width;reads++;
    if(port==0xcfc)return (address&255)==0?0x813910ec:(address&255)==4?config:0xc001;
    if(port==0xc037)return regs[0x37/4];
    if(port>=0xc000 && port<0xc100)return regs[(port-0xc000)/4];
    return 0;
}
static void output(void *ctx,unsigned port,unsigned width,uint32_t value) {
    (void)ctx;(void)width;writes++;
    if(port==0xcf8){address=value;return;}
    if(port==0xcfc){config=stuck?value|4:value;return;}
    if(port==0xc037){regs[0x37/4]=value==16?0:value;return;}
    if(port>=0xc000 && port<0xc100)regs[(port-0xc000)/4]=value;
}
static network_dma_memory dma;static network_dma_state state;
static network_dma_io io={0,input,output,0x200000,0x204000,&dma};
static uint64_t root=1ULL<<32,child=3ULL<<32|2;
static reist_network_request_v1 q;
static unsigned char payload[1536];
static void mirror(network_dma_state *s){for(unsigned n=0;n<24;n++)s->inverse[n]=~s->words[n];}
static int64_t call(unsigned op,uint64_t who,uint64_t now) {
    q.operation=op;return network_dma_apply(&state,&q,who,now,3,payload,&io);
}
int main(void) {
    network_dma_init(&state);q=(reist_network_request_v1){1,64,1,0,child,0,0,0,0,0,0};
    assert(call(1,root,0)==1);assert(!writes);q.epoch=1;
    assert(call(2,child,1)==1);q.deadline_ms=100;
    unsigned before=writes;q.flags=1;assert(call(3,child,2)==-22 && writes==before);q.flags=0;
    assert(call(3,root,2)==-13 && writes==before);
    assert(call(3,child,2)==0 && !(config&4));assert(call(4,child,3)==0 && config&4);
    assert(regs[0x30/4]==0x200000);for(unsigned n=0;n<4;n++)assert(regs[(0x20+n*4)/4]==0x204000+n*2048);
    memset(payload,0xa5,14);q.address=1;q.length=14;
    assert(call(5,child,4)==0);assert(!memcmp((const void*)dma.tx[0],payload,14));
    for(unsigned n=14;n<60;n++)assert(!dma.tx[0][n]);
    assert(call(5,child,5)==-11);q.address=0;q.length=0;
    regs[0x10/4]=1U<<15;assert(call(7,child,6)==0);
    dma.rx[0]=1;dma.rx[1]=0;dma.rx[2]=64;dma.rx[3]=0;
    for(unsigned n=0;n<60;n++)dma.rx[4+n]=(unsigned char)n;
    q.address=1;q.length=1536;assert(call(6,child,7)==60);
    for(unsigned n=0;n<60;n++)assert(payload[n]==n);
    q.address=0;q.length=0;q.deadline_ms=0;assert(call(8,root,8)==0 && !(config&4));
    for(unsigned n=0;n<sizeof(dma);n++)assert(!((volatile unsigned char*)&dma)[n]);
    assert(call(8,root,9)==0);assert(call(2,child,9)==-13);
    q.owner=4ULL<<32|2;q.epoch=0;assert(call(1,root,10)==2);q.epoch=1;
    q.deadline_ms=100;assert(call(3,q.owner,11)==-116);q.epoch=2;
    assert(call(3,q.owner,11)==0);assert(call(4,q.owner,12)==0);
    q.address=1;q.length=1536;dma.rx[0]=0;dma.rx[2]=64;
    assert(call(6,q.owner,13)==-5 && !(config&4));
    network_dma_state copy=state;state.words[2]^=1;before=writes;
    assert(network_dma_valid(&state)==0);state=copy;
    q.address=0;q.length=0;q.deadline_ms=0;stuck=1;
    assert(call(8,root,14)==-84);stuck=0;
    /* Every protected word, including its inverse, detects a single-bit loss. */
    copy=state;for(unsigned n=0;n<48;n++){((uint64_t*)&state)[n]^=1;assert(!network_dma_valid(&state));state=copy;}
    network_dma_init(&state);q=(reist_network_request_v1){1,64,1,0,child,0,0,0,0,0,0};
    before=writes;assert(network_dma_apply(&state,&q,root,0,2,payload,&io)==-13 && writes==before);
    assert(call(1,root,0)==1);q.epoch=1;q.deadline_ms=1000;assert(!call(3,child,1));assert(!call(4,child,2));
    copy=state;
    for(unsigned n=0;n<6;n++) {
        reist_network_request_v1 bad=q;bad.operation=5;bad.address=1;bad.length=64;
        if(n==0)bad.version=2;if(n==1)bad.size=63;if(n==2)bad.reserved=1;
        if(n==3)bad.length=1515;if(n==4)bad.index=4;if(n==5)bad.address=0;
        before=writes;assert(network_dma_apply(&state,&bad,child,3,3,payload,&io)==-22);
        assert(writes==before && !memcmp(&copy,&state,sizeof(copy)));
    }
    /* Boundary-spanning RX, all four TX slots, fixed capacity and deadline. */
    state.words[10]=8188;mirror(&state);dma.rx[8188]=1;dma.rx[8190]=64;dma.rx[8191]=0;
    for(unsigned n=0;n<60;n++)dma.rx[8192+n]=(unsigned char)(255-n);
    q.address=1;q.length=1536;assert(call(6,child,3)==60 && state.words[10]==64);
    for(unsigned n=0;n<60;n++)assert(payload[n]==255-n);
    q.length=64;for(unsigned n=0;n<4;n++){q.index=n;assert(!call(5,child,4));}
    assert(state.words[11]==15);q.address=0;q.length=0;
    for(unsigned n=0;n<4;n++){q.index=n;regs[(0x10+n*4)/4]=1<<15;assert(!call(7,child,5));}
    q.index=0;q.address=1;q.length=64;assert(!call(5,child,6));q.address=0;q.length=0;
    regs[0x10/4]=0;assert(call(7,child,106)==-110 && !(config&4));
    child=5ULL<<32|2;q=(reist_network_request_v1){1,64,1,0,child,0,0,0,0,0,0};
    assert(call(1,root,107)==2);q.epoch=2;q.deadline_ms=1000;
    assert(!call(3,child,107));assert(!call(4,child,108));
    state.words[4]=108;state.words[5]=108;state.words[6]=128;mirror(&state);before=writes;
    assert(call(9,child,109)==-122 && writes==before);
    assert(call(9,child,208)>=0 && state.words[6]==1);
    state.words[16]=UINT64_MAX;mirror(&state);q.address=1;q.length=64;before=writes;
    assert(call(5,child,209)==-75 && writes==before);
    assert(network_dma_retire(&state,root,&io)==0 && !(config&4));
    puts("NETWORK_DMA_HOST_OK");return 0;
}
