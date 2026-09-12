/* Faultable physical backend, actual native heap core, no virtual identity map. */
#include "arch/x86_64/mm/native_heap.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"heap line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
#define PAGES 2048U
#define PHYSICAL UINT64_C(0x200000000)
static _Alignas(4096) unsigned char storage[PAGES][4096];
static unsigned char occupied[PAGES];
static unsigned live, acquisitions, releases, fail_at, step_acquisitions, step_releases;
static int expected_fault;
uint64_t reist_native_heap_frame(bool user) {
    (void)user;
    if(++acquisitions == fail_at) return 0;
    for(unsigned i=1;i<PAGES;i++) if(!occupied[i]) {
        occupied[i]=1;live++;memset(storage[i],0,4096);
        return PHYSICAL+(uint64_t)i*4096;
    }
    return 0;
}
void *reist_native_heap_pointer(uint64_t frame) {
    CHECK(frame>=PHYSICAL && !(frame&4095));
    uint64_t i=(frame-PHYSICAL)/4096;
    CHECK(i<PAGES && occupied[i]);return storage[i];
}
void reist_native_heap_release(uint64_t frame) {
    (void)reist_native_heap_pointer(frame);
    unsigned i=(unsigned)((frame-PHYSICAL)/4096);
    memset(storage[i],0,4096);occupied[i]=0;live--;releases++;
}
void reist_native_heap_fault(void) {
    if(expected_fault) {
        CHECK(acquisitions==step_acquisitions && releases==step_releases);
        puts("NATIVE_HEAP_HOST_OK fail_closed=1");exit(0);
    }
    fputs("unexpected heap fault\n",stderr);exit(2);
}
static NativeHeapCall owner;
static int64_t invoke(uint64_t op,uint64_t a,uint64_t b) {
    owner.operation=op;owner.first=a;owner.second=b;owner.result=0;
    step_acquisitions=acquisitions;step_releases=releases;
    CHECK(reist_native_heap(&owner)==1);
    CHECK(acquisitions-step_acquisitions+releases-step_releases<=64);
    return (int64_t)owner.result;
}
static int64_t complete(int64_t result) {
    unsigned steps=0;
    while(result==NATIVE_HEAP_PENDING) {
        CHECK(++steps<=8192);result=invoke(NATIVE_HEAP_STEP,0,0);
    }
    return result;
}
static void start(void) {
    CHECK(invoke(NATIVE_HEAP_BOOT,0,0)==0);
    owner.generation=1;
    owner.root=reist_native_heap_frame(false);
    owner.pdpt=reist_native_heap_frame(false);
    ((uint64_t*)reist_native_heap_pointer(owner.root))[0]=owner.pdpt|7;
    CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);
}
static uint64_t *heap_leaf(uint64_t address) {
    uint64_t *pdpt=reist_native_heap_pointer(owner.pdpt);
    uint64_t *pd=reist_native_heap_pointer(pdpt[4]&UINT64_C(0x3fffff000));
    uint64_t *pt=reist_native_heap_pointer(pd[(address>>21)&511]&UINT64_C(0x3fffff000));
    return &pt[(address>>12)&511];
}
static unsigned char *data(uint64_t address) {
    uint64_t entry=*heap_leaf(address);
    CHECK((entry&~UINT64_C(0x3fffff060))==UINT64_C(0x8000000000000007));
    return (unsigned char*)reist_native_heap_pointer(entry&UINT64_C(0x3fffff000))+(address&4095);
}
int main(int argc,char **argv) {
    CHECK(argc==2);start();unsigned baseline=live;
    if(!strcmp(argv[1],"corrupt")) {
        native_heap_state.tasks[0].control.generation^=2;
        expected_fault=1;(void)invoke(NATIVE_HEAP_MALLOC,4096,0);return 3;
    }
    if(!strcmp(argv[1],"leaf") || !strcmp(argv[1],"table")) {
        uint64_t a=(uint64_t)complete(invoke(NATIVE_HEAP_MALLOC,4096,0));
        if(!strcmp(argv[1],"leaf"))*heap_leaf(a)^=UINT64_C(0x1000);
        else native_heap_state.tasks[0].tables[0].pt^=UINT64_C(0x1000);
        expected_fault=1;(void)invoke(NATIVE_HEAP_ACCESS,a,8+2);return 3;
    }
    if(!strcmp(argv[1],"stale")) {
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0);
        CHECK(invoke(NATIVE_HEAP_CANCEL,0,0)==0);
        owner.generation=2;CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);
        owner.generation=1;expected_fault=1;
        (void)invoke(NATIVE_HEAP_CANCEL,0,0);return 3;
    }
    if(!strcmp(argv[1],"owners")) {
        uint64_t a=(uint64_t)complete(invoke(NATIVE_HEAP_MALLOC,4096,0));
        *data(a)=71;uint64_t first_frame=*heap_leaf(a);
        NativeHeapCall first=owner;
        owner.slot=1;owner.root=reist_native_heap_frame(false);
        owner.pdpt=reist_native_heap_frame(false);
        ((uint64_t*)reist_native_heap_pointer(owner.root))[0]=owner.pdpt|7;
        CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);
        CHECK(invoke(NATIVE_HEAP_ACCESS,a,8+2)==0);
        CHECK(complete(invoke(NATIVE_HEAP_MALLOC,4096,0))==(int64_t)a);
        CHECK(*heap_leaf(a)!=first_frame && *data(a)==0);*data(a)=92;
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0);
        reist_native_heap_release(owner.root);reist_native_heap_release(owner.pdpt);
        owner=first;CHECK(*data(a)==71);
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0 && live==baseline);
        puts("NATIVE_HEAP_HOST_OK owners=2");return 0;
    }
    if(!strcmp(argv[1],"quota")) {
        uint64_t addresses[128];
        for(unsigned i=0;i<128;i++) {
            addresses[i]=(uint64_t)complete(invoke(NATIVE_HEAP_MALLOC,1,0));
            CHECK(addresses[i]==NATIVE_HEAP_BASE+i*4096U);
        }
        unsigned before=live;
        CHECK(invoke(NATIVE_HEAP_MALLOC,1,0)==-12 && live==before);
        CHECK(complete(invoke(NATIVE_HEAP_FREE,addresses[63],0))==0);
        CHECK(complete(invoke(NATIVE_HEAP_MALLOC,1,0))==(int64_t)addresses[63]);
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0 && live==baseline);
        CHECK(invoke(NATIVE_HEAP_CANCEL,0,0)==0 && live==baseline);
        owner.generation=2;CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);
        CHECK(invoke(NATIVE_HEAP_MALLOC,NATIVE_HEAP_LIMIT,0)==NATIVE_HEAP_PENDING);
        CHECK(invoke(NATIVE_HEAP_STEP,0,0)==NATIVE_HEAP_PENDING);
        CHECK(live>baseline);
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0 && live==baseline);
        puts("NATIVE_HEAP_HOST_OK quota=128 pending_cancel=1");return 0;
    }
    if(!strcmp(argv[1],"oom")) {
        /* Every acquisition in a 2MiB-crossing transaction, including guards. */
        for(unsigned boundary=1;boundary<=526;boundary++) {
            fail_at=acquisitions+boundary;
            int64_t result=complete(invoke(NATIVE_HEAP_MALLOC,513*4096U,0));
            fail_at=0;
            if(result>=0)CHECK(complete(invoke(NATIVE_HEAP_FREE,(uint64_t)result,0))==0);
            else CHECK(result==-12);
            CHECK(live==baseline);
        }
        puts("NATIVE_HEAP_HOST_OK oom_boundaries=526");return 0;
    }
    CHECK(invoke(NATIVE_HEAP_MALLOC,0,0)==-12);
    CHECK(invoke(NATIVE_HEAP_MALLOC,UINT64_MAX,0)==-12);
    CHECK(invoke(NATIVE_HEAP_FREE,0,0)==0);
    uint64_t a=(uint64_t)complete(invoke(NATIVE_HEAP_MALLOC,65*4096U-3,0));
    CHECK(a==UINT64_C(0x100000000));
    for(unsigned i=0;i<65*4096U-3;i++) {
        CHECK(*data(a+i)==0);*data(a+i)=(unsigned char)(i*17U+3U);
    }
    CHECK(invoke(NATIVE_HEAP_ACCESS,a+4090,(uint64_t)2060*8+2)==1);
    *heap_leaf(a)|=UINT64_C(0x60); /* CPU accessed/dirty bits are not corruption. */
    CHECK(invoke(NATIVE_HEAP_ACCESS,a,8+4)==1);
    CHECK(invoke(NATIVE_HEAP_ACCESS,a,8+1)==0);
    CHECK(invoke(NATIVE_HEAP_FREE,a+1,0)==-22);
    CHECK(complete(invoke(NATIVE_HEAP_REALLOC,a,NATIVE_HEAP_LIMIT+1))==-12);
    fail_at=acquisitions+4;
    CHECK(complete(invoke(NATIVE_HEAP_REALLOC,a,130*4096U))==-12);fail_at=0;
    for(unsigned i=0;i<65*4096U-3;i++)CHECK(*data(a+i)==(unsigned char)(i*17U+3U));
    uint64_t b=(uint64_t)complete(invoke(NATIVE_HEAP_REALLOC,a,130*4096U));
    CHECK(b>a);
    for(unsigned i=0;i<65*4096U-3;i++)CHECK(*data(b+i)==(unsigned char)(i*17U+3U));
    CHECK(invoke(NATIVE_HEAP_ACCESS,a,8+4)==0);
    CHECK(complete(invoke(NATIVE_HEAP_REALLOC,b,17))==(int64_t)b);
    CHECK(complete(invoke(NATIVE_HEAP_FREE,b,0))==0 && live==baseline);
    CHECK(invoke(NATIVE_HEAP_FREE,b,0)==-22);
    CHECK(complete(invoke(NATIVE_HEAP_MALLOC,8192,0))==(int64_t)a);
    CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0 && live==baseline);
    owner.generation=2;CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);
    CHECK(complete(invoke(NATIVE_HEAP_MALLOC,4096,0))==(int64_t)a);
    CHECK(*data(a)==0);
    CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0 && live==baseline);
    puts("NATIVE_HEAP_HOST_OK lifecycle=1 fullwidth=1 realloc=1");return 0;
}
