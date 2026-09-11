#include "../arch/x86_64/mm/frame_claim.h"
#include <stdio.h>
#include <string.h>
#define CHECK(c) do {if(!(c)){printf("FAIL line=%d\n",__LINE__);return 1;}}while(0)
static unsigned calls,fail_at,free_fail,live,invalid;
static uint64_t owned[13];
uint64_t X64_CLAIM_ABI physical_frame_alloc64(void) {
    ++calls;
    if(calls==fail_at) return 0;
    if(invalid==1) return 1;
    if(invalid==2) return 0x8000000;
    if(invalid==3 && live) return owned[0];
    uint64_t p=(uint64_t)(calls+1)*4096;
    owned[live++]=p; return p;
}
int X64_CLAIM_ABI physical_frame_free64(uint64_t p) {
    if(free_fail) return 0;
    for(unsigned i=0;i<live;i++) if(owned[i]==p){owned[i]=owned[--live];return 1;}
    return 0;
}
static void reset(void){calls=fail_at=free_fail=live=invalid=0;memset(owned,0,sizeof owned);}
int main(void) {
    struct reist_x64_frame_claim c={0},zero={0},before;
    for(unsigned n=1;n<=13;n++) {
        for(unsigned f=1;f<=n;f++) {
            reset();fail_at=f;
            CHECK(reist_x64_frame_claim_begin(&c,n)==-12);
            CHECK(calls==f && live==0 && !memcmp(&c,&zero,sizeof c));
            CHECK(reist_x64_frame_claim_abort(&c)==1);
            fail_at=0; CHECK(reist_x64_frame_claim_begin(&c,n)==1);
            CHECK(reist_x64_frame_claim_abort(&c)==1 && live==0);
        }
        for(unsigned transferred=0;transferred<=n;transferred++) {
            reset();CHECK(reist_x64_frame_claim_begin(&c,n)==1);
            uint64_t taken[13];
            for(unsigned i=0;i<transferred;i++){long long p=reist_x64_frame_claim_take(&c);CHECK(p>0);taken[i]=(uint64_t)p;}
            CHECK(reist_x64_frame_claim_abort(&c)==1 && live==transferred);
            CHECK(!memcmp(&c,&zero,sizeof c));
            CHECK(reist_x64_frame_claim_abort(&c)==1 && live==transferred);
            for(unsigned i=0;i<transferred;i++) CHECK(physical_frame_free64(taken[i]));
            CHECK(live==0);
        }
    }
    reset();
    CHECK(reist_x64_frame_claim_begin(0,1)==-4096);
    CHECK(reist_x64_frame_claim_begin(&c,0)==-4096);
    CHECK(reist_x64_frame_claim_begin(&c,14)==-4096);
    CHECK(reist_x64_frame_claim_begin(&c,1ULL<<32)==-4096);
    CHECK(reist_x64_frame_claim_take(&c)==-4096 && calls==0);
    for(unsigned i=0;i<15;i++) {
        ((uint64_t*)&c)[i]=1; before=c;
        CHECK(reist_x64_frame_claim_begin(&c,1)==-4096 && calls==0);
        CHECK(!memcmp(&c,&before,sizeof c)); c=zero;
    }
    for(unsigned k=1;k<=3;k++) {
        reset();invalid=k;
        CHECK(reist_x64_frame_claim_begin(&c,2)==-4096);
        invalid=0;CHECK(reist_x64_frame_claim_abort(&c)==1 && live==0);
    }
    reset();CHECK(reist_x64_frame_claim_begin(&c,3)==1);
    before=c;c.frames[2]=c.frames[1];struct reist_x64_frame_claim corrupt=c;
    CHECK(reist_x64_frame_claim_abort(&c)==-4096 && live==3);
    CHECK(!memcmp(&c,&corrupt,sizeof c));c=before;
    free_fail=1;
    CHECK(reist_x64_frame_claim_abort(&c)==-4096 && live==3);
    CHECK(!memcmp(&c,&before,sizeof c));
    free_fail=0;CHECK(reist_x64_frame_claim_abort(&c)==1 && live==0);
    reset();fail_at=3;free_fail=1;
    CHECK(reist_x64_frame_claim_begin(&c,4)==-4096 && live==2);
    free_fail=0;CHECK(reist_x64_frame_claim_abort(&c)==1 && live==0);
    puts("X86_64_SPAWN_OOM_HOST_OK");return 0;
}
