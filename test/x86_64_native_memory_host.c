#include "arch/x86_64/mm/native_memory.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"memory check line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
static int expected_fault;
static uint64_t addresses[16];
static unsigned char backing[16][4096];
static unsigned touches;
static NativeMemoryState snapshot;
void reist_native_memory_fault(void) {
    if(expected_fault){CHECK(touches==0);puts("NATIVE_MEMORY_FAULT_CLOSED_OK");exit(0);}
    fputs("unexpected native memory fault\n",stderr);exit(2);
}
void reist_native_memory_zero(uint64_t frame) {
    CHECK(frame && !(frame&4095) && frame<NATIVE_MEMORY_LIMIT);
    unsigned i;
    for(i=0;i<16;i++) if(!addresses[i] || addresses[i]==frame)break;
    CHECK(i<16);addresses[i]=frame;memset(backing[i],0,4096);++touches;
}
static void seed(uint64_t frame) {
    uint64_t index=frame/4096;
    native_memory_state.usable[index/64]|=UINT64_C(1)<<(index%64);
    native_memory_state.control.managed++;
    native_memory_state.control.free++;
}
int main(int argc,char **argv) {
    CHECK(argc==2);
    uint64_t frames[]={0x400000,0x401000,0x7fff000,0x8000000,UINT64_C(0xfffff000),
                       UINT64_C(0x100000000),UINT64_C(0x100001000),
                       UINT64_C(0x240000000),UINT64_C(0x300000000),UINT64_C(0x3fffff000)};
    enum {N=10};
    for(unsigned i=0;i<N;i++)seed(frames[i]);
    CHECK(reist_native_memory(NATIVE_MEMORY_INIT,0)==1);
    CHECK(reist_native_memory(NATIVE_MEMORY_COUNT,0)==N);
    if(strcmp(argv[1],"normal")) {
        expected_fault=1;
        if(!strcmp(argv[1],"root"))native_memory_state.control.free^=1;
        else if(!strcmp(argv[1],"raw"))native_memory_state.allocated[frames[0]/4096/64]^=1;
        else if(!strcmp(argv[1],"summary"))native_memory_state.available[0]^=1;
        else if(!strcmp(argv[1],"dual")) {
            native_memory_state.control_guard.primary.crc32^=3;
            native_memory_state.control_guard.shadow.crc32^=3;
        } else if(!strcmp(argv[1],"busy"))native_memory_state.control_guard.publication_lock=1;
        else if(!strcmp(argv[1],"entered"))native_memory_state.entered=1;
        else if(!strcmp(argv[1],"region")) {
            unsigned region=(unsigned)(frames[0]/(256*4096));
            native_memory_state.region_guards[region].primary.crc32^=3;
            native_memory_state.region_guards[region].shadow.crc32^=3;
        } else if(!strcmp(argv[1],"hierarchy")) {
            native_memory_state.summary_guards[0].primary.crc32^=3;
            native_memory_state.summary_guards[0].shadow.crc32^=3;
        }
        else return 3;
        (void)reist_native_memory(NATIVE_MEMORY_ALLOC,0);return 4;
    }
    native_memory_state.control_guard.primary.words[4]^=1;
    CHECK(reist_native_memory(NATIVE_MEMORY_COUNT,0)==N);
    CHECK(reist_native_memory(NATIVE_MEMORY_HIGH_FLOOR,0)==UINT64_C(0x100000000));
    CHECK(reist_native_memory(NATIVE_MEMORY_ALLOC,UINT64_C(0x100000001))==0);
    CHECK(reist_native_memory(NATIVE_MEMORY_ALLOC,NATIVE_MEMORY_LIMIT)==0);
    memcpy(&snapshot,&native_memory_state,sizeof(snapshot));
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,0)==0);
    CHECK(!memcmp(&snapshot,&native_memory_state,sizeof(snapshot)));
    for(unsigned i=0;i<N;i++) {
        CHECK(reist_native_memory(NATIVE_MEMORY_ALLOC,0)==frames[i]);
        CHECK(reist_native_memory(NATIVE_MEMORY_COUNT,0)==N-1-i);
        memset(backing[i],0xa5,4096);
    }
    memcpy(&snapshot,&native_memory_state,sizeof(snapshot));
    CHECK(reist_native_memory(NATIVE_MEMORY_ALLOC,0)==0);
    CHECK(reist_native_memory(NATIVE_MEMORY_HIGH_FLOOR,0)==UINT64_C(0x20000000));
    CHECK(!memcmp(&snapshot,&native_memory_state,sizeof(snapshot)));
    CHECK(touches==N);
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,0)==0);
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,1)==0);
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,0x402000)==0);
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,NATIVE_MEMORY_LIMIT)==0);
    CHECK(touches==N);
    CHECK(!memcmp(&snapshot,&native_memory_state,sizeof(snapshot)));
    for(unsigned i=0;i<N;i++) {
        CHECK(reist_native_memory(NATIVE_MEMORY_FREE,frames[i])==1);
        memcpy(&snapshot,&native_memory_state,sizeof(snapshot));
        CHECK(reist_native_memory(NATIVE_MEMORY_FREE,frames[i])==0);
        CHECK(!memcmp(&snapshot,&native_memory_state,sizeof(snapshot)));
        for(unsigned j=0;j<4096;j++)CHECK(backing[i][j]==0);
    }
    CHECK(touches==2*N && reist_native_memory(NATIVE_MEMORY_COUNT,0)==N);
    CHECK(reist_native_memory(NATIVE_MEMORY_ALLOC,UINT64_C(0x100001000))==frames[6]);
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,frames[6])==1);
    CHECK(reist_native_memory(NATIVE_MEMORY_ALLOC,0x401000)==frames[1]);
    CHECK(reist_native_memory(NATIVE_MEMORY_FREE,frames[1])==1);
    puts("NATIVE_MEMORY_HOST_OK");return 0;
}
