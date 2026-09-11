#include "../arch/x86_64/mm/address_space.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d: %s\n",__LINE__,#x);exit(1);}}while(0)
#define NX UINT64_C(0x8000000000000000)
static uint64_t pages[23][512] __attribute__((aligned(4096)));
static uint64_t expected[23][512],snapshot[23][512],physical[21];
static struct {uint64_t pre[2];ReistX64AddressPlan plan;uint64_t post[2];} guarded __attribute__((aligned(4096)));
static unsigned calls, fail_call, failure_kind;
static const uint64_t CANARY=UINT64_C(0xdafe881902abc776);
void *__attribute__((sysv_abi)) reist_x64_mapping_pointer64(uint64_t frame) {
    ++calls;
    if(calls==fail_call) {
        switch(failure_kind) {
        case 0:return NULL;
        case 1:return (char*)pages[0]+1;
        case 2:return pages[0];
        case 3:return (void*)(UINTPTR_MAX-4095);
        case 4:return &guarded;
        }
    }
    for(unsigned i=0;i<21;++i)if(physical[i]==frame)return pages[i];
    CHECK(0);return NULL;
}
static void reset(unsigned mask,unsigned style) {
    memset(&guarded,0,sizeof guarded);memset(pages,0,sizeof pages);
    guarded.pre[0]=guarded.pre[1]=guarded.post[0]=guarded.post[1]=CANARY;
    calls=fail_call=failure_kind=0;
    for(unsigned i=0;i<21;++i)physical[i]=i==20?0x07fff000:0x04000000+i*4096;
    for(unsigned i=0;i<4;++i)guarded.plan.tables[i]=physical[i];
    for(unsigned i=0;i<8;++i) {
        for(unsigned j=0;j<512;++j)pages[4+i][j]=CANARY^((uint64_t)i<<32)^j;
        if(mask&(1u<<i)) {
            guarded.plan.flags[i]=(uint8_t)(style==3?4+i%3:4+style);
            guarded.plan.source[i]=physical[4+i];
            if(guarded.plan.flags[i]==6)guarded.plan.private_frames[i]=physical[12+i];
        }
        if(!guarded.plan.private_frames[i])for(unsigned j=0;j<512;++j)pages[12+i][j]=CANARY;
    }
    for(unsigned i=21;i<23;++i)for(unsigned j=0;j<512;++j)pages[i][j]=CANARY;
    guarded.plan.stack=physical[20];guarded.plan.kernel_entries[0]=NX|0x1023;guarded.plan.kernel_entries[1]=0x2003;
}
static void guards(void) {
    CHECK(guarded.pre[0]==CANARY && guarded.pre[1]==CANARY);
    CHECK(guarded.post[0]==CANARY && guarded.post[1]==CANARY);
}
static void check_failure(int metadata) {
    ReistX64AddressPlan saved=guarded.plan;memcpy(snapshot,pages,sizeof pages);
    CHECK(reist_x64_address_space_build(&guarded.plan)==0);
    CHECK(!memcmp(&saved,&guarded.plan,sizeof saved) && !memcmp(snapshot,pages,sizeof pages));
    if(metadata)CHECK(!calls);guards();
}
static void all_mappings(void) {
    for(unsigned mask=0;mask<256;++mask)for(unsigned style=0;style<4;++style) {
        reset(mask,style);ReistX64AddressPlan saved=guarded.plan;memcpy(expected,pages,sizeof pages);
        expected[0][0]=physical[1]|7;expected[0][256]=NX|0x1023;expected[0][511]=0x2003;
        expected[1][0]=physical[2]|7;expected[2][2]=physical[3]|7;expected[3][8]=physical[20]|7|NX;
        unsigned count=5;
        for(unsigned i=0;i<8;++i)if(mask&(1u<<i)) {
            ++count;uint64_t address=physical[4+i],bits=5;
            if(saved.flags[i]==6) {
                ++count;address=physical[12+i];bits|=2;
                memcpy(expected[12+i],pages[4+i],4096);
            }
            if(!(saved.flags[i]&1))bits|=NX;
            expected[3][i]=address|bits;
        }
        CHECK(reist_x64_address_space_build(&guarded.plan)==1 && calls==count);
        CHECK(!memcmp(pages,expected,sizeof pages) && !memcmp(&saved,&guarded.plan,sizeof saved));guards();
        calls=0;check_failure(0); /* Reject reuse of a published/nonzero table. */
    }
}
static void bad_metadata(void) {
    for(unsigned variant=0;variant<21;++variant) {
        reset(255,2);ReistX64AddressPlan *p=&guarded.plan;
        switch(variant) {
        case 0:p->tables[3]=0;break;
        case 1:p->stack=0;break;
        case 2:p->source[7]=0;break;
        case 3:p->private_frames[7]=0;break;
        case 4:p->source[7]|=1;break;
        case 5:p->private_frames[7]=0x08000000;break;
        case 6:p->tables[3]=p->source[0];break;
        case 7:p->private_frames[7]=p->source[7];break;
        case 8:p->stack=p->private_frames[0];break;
        case 9:p->source[7]=p->source[0];break;
        case 10:p->flags[7]=7;break;
        case 11:p->flags[7]=8;break;
        case 12:p->flags[7]=0;break;
        case 13:p->flags[7]=4;break;
        case 14:p->kernel_entries[0]|=4;break;
        case 15:p->kernel_entries[1]|=NX;break;
        case 16:p->kernel_entries[1]&=~UINT64_C(1);break;
        case 17:p->kernel_entries[1]=3;break;
        case 18:p->source[7]=0x1000;break;
        case 19:p->private_frames[7]=UINT64_MAX;break;
        case 20:p->kernel_entries[0]&=~NX;break;
        }
        check_failure(1);
    }
    CHECK(!reist_x64_address_space_build(NULL));
    CHECK(!reist_x64_address_space_build((void*)((char*)&guarded.plan+1)));
    CHECK(!reist_x64_address_space_build((void*)(UINTPTR_MAX-7)));
}
static void bad_backends_and_destinations(void) {
    for(unsigned ordinal=1;ordinal<=21;++ordinal)for(unsigned kind=0;kind<5;++kind) {
        if(kind==2 && ordinal==1)continue; /* first valid pointer is not an alias */
        reset(255,2);fail_call=ordinal;failure_kind=kind;check_failure(0);
        CHECK(calls==ordinal);
    }
    for(unsigned i=0;i<21;++i)if(i<4 || i>=12)for(unsigned last=0;last<2;++last) {
        reset(255,2);pages[i][last?511:0]=CANARY;check_failure(0);
        CHECK(calls==21);
    }
}
int main(void) {
    all_mappings();bad_metadata();bad_backends_and_destinations();
    puts("X86_64_MAPPINGS_HOST_OK layouts=1024 preeffect-failures=151");return 0;
}
