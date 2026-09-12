#include "native_memory.h"
#ifndef REIST_NATIVE_MEMORY_HOST_TEST
#include "arch/x86/include/interrupt.h"
_Noreturn void reist_native_memory_fault(void) {
    __asm__ volatile("ud2");__builtin_unreachable();
}
void reist_native_memory_zero(uint64_t frame) {
    volatile uint64_t *p=(volatile uint64_t *)(uintptr_t)(UINT64_C(0xffff800000000000)+frame);
    for(unsigned i=0;i<512;i++)p[i]=0;
}
#endif
__attribute__((section(".memory_state"),aligned(4096)))
NativeMemoryState native_memory_state;
#define M native_memory_state
static void need(bool ok) {if(!ok)reist_native_memory_fault();}
static bool chunk_valid(const void *p,size_t n) {return p && n && n<=64;}
static void verify(critical_object_t *guard,const void *data,size_t n) {
    unsigned char copy[64];size_t length=0;
    need(!guard->publication_lock);
    need(critical_object_read(guard,1,copy,n,&length,chunk_valid)>=0 && length==n);
    for(size_t i=0;i<n;i++)need(copy[i]==((const unsigned char*)data)[i]);
}
static void seal(critical_object_t *guard,const void *data,size_t n,bool init) {
    need(!guard->publication_lock);
    need((init?critical_object_init(guard,1,data,n):
               critical_object_update(guard,1,data,n,chunk_valid))==0);
}
static void region_copy(unsigned region,uint64_t words[8]) {
    for(unsigned j=0;j<4;j++) {
        words[j]=M.usable[region*4+j];words[4+j]=M.allocated[region*4+j];
        need(!(words[4+j]&~words[j]));
    }
}
static bool region_available(const uint64_t words[8]) {
    uint64_t bits=0;
    for(unsigned j=0;j<4;j++)bits|=words[j]&~words[j+4];
    return bits!=0;
}
static void check_control(void) {
    verify(&M.control_guard,&M.control,sizeof(M.control));
    need(M.control.initialized==1 && M.control.inverse==~UINT32_C(1));
    need(M.control.managed<=NATIVE_MEMORY_FRAMES && M.control.free<=M.control.managed);
}
static void check_summary(unsigned word) {
    verify(&M.summary_guards[word/8],M.available+(word&~7U),64);
    need(((M.control.roots[word/64]>>(word%64))&1)==(M.available[word]!=0));
}
static void read_region(unsigned region,uint64_t words[8]) {
    region_copy(region,words);
    verify(&M.region_guards[region],words,64);
    need(((M.available[region/64]>>(region%64))&1)==region_available(words));
}
static uint64_t initialize(void) {
    need(!M.control.initialized && !M.control.inverse && !(M.usable[0]&1));
    for(unsigned j=0;j<4;j++)need(!M.control.roots[j]);
    for(unsigned j=0;j<3;j++)need(!M.reserved[j]);
    for(unsigned j=0;j<NATIVE_MEMORY_REGIONS/64;j++)need(!M.available[j]);
    uint32_t count=0;
    for(unsigned region=0;region<NATIVE_MEMORY_REGIONS;region++) {
        uint64_t words[8];region_copy(region,words);
        for(unsigned j=0;j<4;j++) {
            need(!words[4+j]);
            /* Boot-only bounded population count; no POPCNT feature required. */
            uint64_t bits=words[j];
            for(unsigned bit=0;bit<64;bit++) {count+=(uint32_t)(bits&1);bits>>=1;}
        }
        if(region_available(words))M.available[region/64]|=UINT64_C(1)<<(region%64);
        seal(&M.region_guards[region],words,64,true);
    }
    need(count && count==M.control.managed && count==M.control.free);
    for(unsigned word=0;word<NATIVE_MEMORY_REGIONS/64;word++)
        if(M.available[word])M.control.roots[word/64]|=UINT64_C(1)<<(word%64);
    for(unsigned group=0;group<NATIVE_MEMORY_REGIONS/512;group++)
        seal(&M.summary_guards[group],M.available+group*8,64,true);
    M.control.initialized=1;M.control.inverse=~UINT32_C(1);
    seal(&M.control_guard,&M.control,sizeof(M.control),true);
    return 1;
}
static uint64_t publish(unsigned region,unsigned index,uint64_t words[8],bool allocate) {
    unsigned w=index/64;uint64_t bit=UINT64_C(1)<<(index%64);
    need(words[w]&bit);
    need(((words[w+4]&bit)!=0)!=allocate);
    need(allocate?M.control.free>0:M.control.free<M.control.managed);
    uint64_t frame=((uint64_t)region*256+index)*4096;
    /* IF0 pins the admitted free/owned frame until zeroing and publication.
     * Backend failure is trusted corruption, never partial normal success. */
    reist_native_memory_zero(frame);
    if(allocate){words[w+4]|=bit;--M.control.free;}
    else {words[w+4]&=~bit;++M.control.free;}
    M.allocated[region*4+w]=words[w+4];
    unsigned summary=region/64;uint64_t region_bit=UINT64_C(1)<<(region%64);
    if(region_available(words))M.available[summary]|=region_bit;
    else M.available[summary]&=~region_bit;
    uint64_t root_bit=UINT64_C(1)<<(summary%64);
    if(M.available[summary])M.control.roots[summary/64]|=root_bit;
    else M.control.roots[summary/64]&=~root_bit;
    seal(&M.region_guards[region],words,64,false);
    seal(&M.summary_guards[summary/8],M.available+(summary&~7U),64,false);
    seal(&M.control_guard,&M.control,sizeof(M.control),false);
    return allocate?frame:1;
}
static uint64_t allocate(uint64_t minimum) {
    if((minimum&4095) || minimum>=NATIVE_MEMORY_LIMIT)return 0;
    unsigned first=(unsigned)(minimum/4096),first_region=first/256,first_summary=first_region/64;
    /* Four root words. Valid summaries identify actual free regions; only
     * the first partial region may contain free bits exclusively below floor.
     * Every loop also has a fixed capacity independent of installed RAM. */
    for(unsigned root=first_summary/64;root<4;root++) {
        uint64_t roots=M.control.roots[root];
        if(root==first_summary/64)roots&=UINT64_MAX<<(first_summary%64);
        for(unsigned r=0;roots && r<64;r++,roots&=roots-1) {
            unsigned summary=root*64+(unsigned)__builtin_ctzll(roots);
            check_summary(summary);
            uint64_t regions=M.available[summary];
            if(summary==first_summary)regions&=UINT64_MAX<<(first_region%64);
            for(unsigned k=0;regions && k<64;k++,regions&=regions-1) {
                unsigned region=summary*64+(unsigned)__builtin_ctzll(regions);
                uint64_t words[8];read_region(region,words);
                unsigned floor=region==first_region?first%256:0;
                for(unsigned j=floor/64;j<4;j++) {
                    uint64_t bits=words[j]&~words[j+4];
                    if(j==floor/64)bits&=UINT64_MAX<<(floor%64);
                    if(bits)return publish(region,j*64+(unsigned)__builtin_ctzll(bits),words,true);
                }
            }
        }
    }
    if(!minimum)need(!M.control.free);
    return 0;
}
static uint64_t release(uint64_t frame) {
    if(!frame || (frame&4095) || frame>=NATIVE_MEMORY_LIMIT)return 0;
    unsigned region=(unsigned)(frame/(256*4096)),index=(unsigned)(frame/4096)%256;
    uint64_t words[8];check_summary(region/64);read_region(region,words);
    uint64_t bit=UINT64_C(1)<<(index%64);
    if(!(words[index/64]&bit) || !(words[index/64+4]&bit))return 0;
    return publish(region,index,words,false);
}
uint64_t reist_native_memory(uint64_t operation,uint64_t argument) {
#ifndef REIST_NATIVE_MEMORY_HOST_TEST
    need(!irq_enabled());
#endif
    need(!M.entered && operation<=NATIVE_MEMORY_HIGH_FLOOR);M.entered=1;
    uint64_t result=0;
    if(operation==NATIVE_MEMORY_INIT) {need(!argument);result=initialize();}
    else {
        check_control();
        if(operation==NATIVE_MEMORY_ALLOC)result=allocate(argument);
        else if(operation==NATIVE_MEMORY_FREE)result=release(argument);
        else {
            need(!argument);
            if(operation==NATIVE_MEMORY_COUNT)result=M.control.free;
            else result=(M.control.roots[1]|M.control.roots[2]|M.control.roots[3])?
                         UINT64_C(0x100000000):UINT64_C(0x20000000);
        }
    }
    need(M.entered==1);M.entered=0;return result;
}
