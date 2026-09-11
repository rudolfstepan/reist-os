#include "../arch/x86_64/exec/image_frames.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL line=%d: %s\n",__LINE__,#x); exit(1); } } while(0)
static unsigned char owner[32768];
static uint64_t contents[32768];
static unsigned free_count, calls, fail_call, counter_calls;
static int skew_before, skew_after;
static struct { uint64_t pre[2]; ReistX64Image image; uint64_t post[2]; } guarded;
static ReistX64Image survivors[2];
static const uint64_t CANARY=UINT64_C(0xdaf74126bc89530e);
unsigned __attribute__((sysv_abi)) physical_free_frame_count64(void) {
    ++counter_calls;
    return free_count+(counter_calls==1?skew_before:skew_after);
}
int __attribute__((sysv_abi)) physical_frame_free64(uint64_t address) {
    ++calls;
    CHECK(address && !(address&4095) && address<0x08000000);
    unsigned page=(unsigned)(address>>12);
    CHECK(owner[page]==1); /* No double-free or unrelated owner may be touched. */
    if (calls==fail_call) return 0;
    owner[page]=0; contents[page]=0; ++free_count;
    return 1;
}
static void claim(ReistX64Image *image,unsigned index,unsigned page,unsigned who) {
    CHECK(!owner[page]); owner[page]=(unsigned char)who; --free_count;
    contents[page]=CANARY^page;
    image->frames[index]=(uint64_t)page<<12; image->flags[index]=(uint8_t)(4+index%3);
}
static void reset(unsigned bitmap) {
    memset(owner,0,sizeof owner); memset(contents,0,sizeof contents);
    memset(&guarded,0,sizeof guarded); memset(survivors,0,sizeof survivors);
    free_count=32760;calls=fail_call=counter_calls=0;skew_before=skew_after=0;
    guarded.pre[0]=guarded.pre[1]=guarded.post[0]=guarded.post[1]=CANARY;
    guarded.image.active=1;guarded.image.segments=2;guarded.image.executable=1;
    guarded.image.entry=0x400000;guarded.image.initial_free=free_count;
    for(unsigned i=0;i<8;++i) if(bitmap&(1u<<i))
        claim(&guarded.image,i,i==7?32767:100+i,1);
    for(unsigned j=0;j<2;++j) {
        survivors[j].active=1;
        for(unsigned i=0;i<8;++i) claim(&survivors[j],i,200+j*8+i,2+j);
    }
    owner[300]=4; contents[300]=CANARY; --free_count;
}
static void others_unchanged(const ReistX64Image *saved) {
    CHECK(!memcmp(survivors,saved,sizeof survivors));
    for(unsigned j=0;j<2;++j) for(unsigned i=0;i<8;++i) {
        unsigned p=200+j*8+i;
        CHECK(owner[p]==j+2 && contents[p]==(CANARY^p));
    }
    CHECK(owner[300]==4 && contents[300]==CANARY);
    CHECK(guarded.pre[0]==CANARY && guarded.pre[1]==CANARY);
    CHECK(guarded.post[0]==CANARY && guarded.post[1]==CANARY);
}
static void sparse_and_partial(void) {
    for(unsigned mask=0;mask<256;++mask) {
        unsigned n=0;for(unsigned i=0;i<8;++i)n+=(mask>>i)&1;
        for(unsigned fail=0;fail<=n;++fail) {
            reset(mask); fail_call=fail;
            ReistX64Image original=guarded.image,saved[2];memcpy(saved,survivors,sizeof saved);
            unsigned before=free_count;
            CHECK(reist_x64_image_release(&guarded.image)==(fail==0));
            CHECK(calls==n && free_count==before+n-(fail!=0));
            unsigned ordinal=0;
            for(unsigned i=0;i<8;++i) {
                if(original.frames[i]) ++ordinal;
                int held=original.frames[i] && fail && ordinal==fail;
                CHECK(guarded.image.frames[i]==(held?original.frames[i]:0));
                CHECK(guarded.image.flags[i]==(held?original.flags[i]:0));
            }
            CHECK(guarded.image.active==(fail!=0));
            CHECK(guarded.image.cleanup_error==(fail!=0));
            CHECK(guarded.image.initial_free==original.initial_free);
            others_unchanged(saved);
            fail_call=0;counter_calls=0;
            CHECK(reist_x64_image_release(&guarded.image)==1);
            CHECK(calls==n+(fail!=0) && free_count==before+n);
            CHECK(guarded.image.active==0 && guarded.image.cleanup_error==0);
            CHECK(!guarded.image.entry && !guarded.image.segments && !guarded.image.executable);
            ReistX64Image released=guarded.image;unsigned old_calls=calls;
            counter_calls=0;CHECK(reist_x64_image_release(&guarded.image)==1);
            CHECK(!memcmp(&released,&guarded.image,sizeof released) && calls==old_calls);
            others_unchanged(saved);
        }
    }
}
static void invalid_metadata(void) {
    for(unsigned variant=0;variant<12;++variant) {
        reset(255);
        switch(variant) {
        case 0:guarded.image.frames[7]=guarded.image.frames[0];break;
        case 1:guarded.image.frames[7]=0x08000000;break;
        case 2:guarded.image.frames[7]=UINT64_MAX;break;
        case 3:guarded.image.frames[7]|=1;break;
        case 4:guarded.image.flags[7]=7;break;
        case 5:guarded.image.flags[7]=8;break;
        case 6:guarded.image.flags[7]=0;break;
        case 7:guarded.image.flags[7]=1;break;
        case 8:guarded.image.active=2;break;
        case 9:guarded.image.active=0;break;
        case 10:guarded.image.cleanup_error=2;break;
        case 11:guarded.image.executable=2;break;
        }
        ReistX64Image bad=guarded.image;unsigned before=free_count;
        CHECK(reist_x64_image_release(&guarded.image)==0);
        CHECK(!memcmp(&bad,&guarded.image,sizeof bad) && !calls && !counter_calls && before==free_count);
    }
    CHECK(!reist_x64_image_release(NULL));
    CHECK(!reist_x64_image_release((ReistX64Image*)((char*)&guarded.image+1)));
    CHECK(!reist_x64_image_release((ReistX64Image*)(UINTPTR_MAX-7)));
    reset(0); /* Valid load rollback: flags marked before any allocation. */
    for(unsigned i=0;i<8;++i)guarded.image.flags[i]=6;
    guarded.image.segments=3; /* Invalid third PHDR rejected before allocation. */
    CHECK(reist_x64_image_release(&guarded.image)==1 && !calls);
}
static void broken_accounting(void) {
    for(int skew=-1;skew<=1;skew+=2) {
        reset(255);skew_after=skew;unsigned before=free_count;
        CHECK(reist_x64_image_release(&guarded.image)==0);
        CHECK(calls==8 && free_count==before+8 && guarded.image.active==1 && guarded.image.cleanup_error==1);
        for(unsigned i=0;i<8;++i) CHECK(!guarded.image.frames[i] && !guarded.image.flags[i]);
    }
    reset(255);skew_before=32769-(int)free_count;
    ReistX64Image before=guarded.image;
    CHECK(!reist_x64_image_release(&guarded.image));
    CHECK(!calls && !memcmp(&before,&guarded.image,sizeof before));
}
int main(void) {
    sparse_and_partial();invalid_metadata();broken_accounting();
    puts("X86_64_IMAGE_CONTEXTS_HOST_OK masks=256 partial-failures=1024");return 0;
}
