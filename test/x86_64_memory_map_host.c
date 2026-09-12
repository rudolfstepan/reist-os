/* Execute the production32-bit Multiboot parser and actual direct-map builder. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if(!(x)){printf("MAP_FAIL line=%d\n",__LINE__);return 1;} }while(0)
extern uint32_t probe_init(uint32_t,void *);
extern uint32_t probe_bitmap[],probe_free;
extern uint64_t probe_pd[],probe_pdpt[],probe_pml4[];
static uint32_t info[29];
static struct __attribute__((packed)) {uint32_t size;uint64_t base,length;uint32_t type;} map[128];
static void entry(unsigned i,uint64_t base,uint64_t length,uint32_t type) {
    map[i].size=20;map[i].base=base;map[i].length=length;map[i].type=type;
}
static int usable(uint64_t byte) {
    unsigned f=(unsigned)(byte/4096);return (probe_bitmap[f/32]>>(f%32))&1;
}
static uint64_t leaf(uint64_t byte) {
    uint64_t pde=probe_pd[byte/(2*1024*1024)];
    if(!(pde&1) || (pde&128))return pde;
    uint64_t *pt=(uint64_t *)(uintptr_t)(pde&UINT64_C(0x3fffff000));
    return pt[(byte/4096)%512];
}
static void setup(unsigned n) {
    memset(info,0,sizeof(info));memset(map,0,sizeof(map));
    info[0]=64;info[11]=n*24;info[12]=(uint32_t)(uintptr_t)map;
}
int main(void) {
    setup(5);
    entry(0,0,UINT64_C(0x400000000),1);
    entry(1,UINT64_C(0x100001001),4096,2);
    entry(2,UINT64_C(0x100000000),UINT64_C(0x400000),1); /* reserve wins */
    entry(3,UINT64_C(0x80000000),UINT64_C(0x80000000),2); /* PCI-like hole */
    entry(4,UINT64_C(0x3fffff123),0,2); /* empty must reserve nothing */
    CHECK(probe_init(0x2badb002,info)==1 && probe_free>2000000);
    CHECK(!usable(0) && !usable(0x9ff000) && usable(0x1000000));
    CHECK(!usable(0x80000000) && !usable(0xfffff000) && usable(UINT64_C(0x100000000)));
    CHECK(!usable(UINT64_C(0x100001000)) && !usable(UINT64_C(0x100002000)));
    CHECK(usable(UINT64_C(0x100003000)) && usable(UINT64_C(0x3fffff000)));
    CHECK(leaf(0)==0 && leaf(0x80000000)==0 && leaf(UINT64_C(0x100001000))==0);
    CHECK(leaf(UINT64_C(0x100003000))==UINT64_C(0x8000000100003003));
    CHECK(leaf(UINT64_C(0x240000000))==UINT64_C(0x8000000240000083));
    CHECK(!(probe_pml4[256]&4) && (probe_pml4[256]>>63)==1);
    for(unsigned i=0;i<16;i++)CHECK((probe_pdpt[i]&7)==3 && (probe_pdpt[i]>>63)==1);
    setup(2);entry(0,0,0x4000000,1);
    entry(1,UINT64_C(0x100000001),8191,1);
    CHECK(probe_init(0x2badb002,info)==1);
    CHECK(!usable(UINT64_C(0x100000000)) && usable(UINT64_C(0x100001000)));
    CHECK(!usable(UINT64_C(0x100002000)));
    entry(1,UINT64_MAX-4095,8192,1);
    CHECK(probe_init(0x2badb002,info)==0 && probe_free==0);
    for(unsigned i=0;i<0x400000/32;i++)CHECK(probe_bitmap[i]==0);
    setup(1);entry(0,0,0x4000000,1);map[0].size=19;
    CHECK(probe_init(0x2badb002,info)==0 && probe_free==0);
    map[0].size=0xffffffff;CHECK(probe_init(0x2badb002,info)==0);
    setup(1);entry(0,UINT64_C(0x400000000),4096,1);
    CHECK(probe_init(0x2badb002,info)==0);
    setup(1);entry(0,0,0x4000000,1);info[11]=4097;
    CHECK(probe_init(0x2badb002,info)==0);
    CHECK(probe_init(0,info)==0);
    puts("NATIVE_MEMORY_MAP_OK fullwidth=1 reserved=1 alignment=1 huge=1 overflow=1");
    return 0;
}
