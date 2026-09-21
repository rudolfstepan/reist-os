#include "arch/x86_64/video/display_core.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <stdio.h>
static const uint64_t root=UINT64_C(1)<<32,child=(UINT64_C(2)<<32)|4;
extern int64_t DISPLAY_ABI family_profile_admit64(const void *);
extern int64_t DISPLAY_ABI native_display_user_tile_range64(uint64_t,uint32_t);
static uint64_t next_pointer;
static unsigned calls,reject_at;
int64_t DISPLAY_ABI display_validate_backend(uint64_t pointer,uint64_t bytes,uint64_t rights) {
    assert(pointer==next_pointer && bytes>0 && bytes<=1024 && rights==4);
    next_pointer+=bytes;++calls;return calls==reject_at?0:1;
}
static void tile_range(void) {
    for(unsigned size=1;size<=16384;size+=127) {
        next_pointer=0x420000;calls=reject_at=0;
        assert(native_display_user_tile_range64(next_pointer,size)==1);
        assert(next_pointer==0x420000+size && calls==(size+1023)/1024);
    }
    for(unsigned n=1;n<=16;n++) {
        next_pointer=0x420000;calls=0;reject_at=n;
        assert(native_display_user_tile_range64(next_pointer,16384)==0 && calls==n);
    }
    calls=0;
    assert(!native_display_user_tile_range64(UINT64_MAX-1,64));
    assert(!native_display_user_tile_range64(0x420000,0));
    assert(!native_display_user_tile_range64(0x420000,16385));
    assert(!calls);
}
extern int64_t DISPLAY_ABI native_terminal_plan64(const void *,const void *,const void *,void *);
static void terminal_combination(void) {
    uint64_t state[3]={root,0,0},view[9]={root,0,root,child,root,
        (1ULL<<15)|(1ULL<<20),(1ULL<<63)|(1ULL<<49),0,0},proposal=0xdead;
    uint32_t req[6]={1,24,2,0,2,2};
    int64_t expected=EXPECT_DISPLAY?0:-13;
    assert(native_terminal_plan64(state,view,req,&proposal)==expected);
    assert(proposal==(EXPECT_DISPLAY?child:0xdead));
    state[1]=child;view[0]=child;view[1]=root;view[7]=view[5];view[8]=view[6];
    req[2]=5;req[4]=req[5]=0;
    assert(native_terminal_plan64(state,view,req,&proposal)==expected);
    view[8]|=1ULL<<50;proposal=0xbeef;
    assert(native_terminal_plan64(state,view,req,&proposal)==-13 && proposal==0xbeef);
    view[8]=1ULL<<49;
    assert(native_terminal_plan64(state,view,req,&proposal)==-13);
}
static reist_display_request_v1 request(unsigned operation) {
    reist_display_request_v1 r={1,64,operation,0,child,0,0,0,0,0,0,0,0};
    return r;
}
static void unchanged(ReistX64DisplayState *s,reist_display_request_v1 *r,
                      uint64_t who,uint64_t time,uint64_t flags,int64_t expected) {
    ReistX64DisplayState old=*s;
    assert(native_display_core_apply64(s,r,who,time,flags)==expected);
    assert(memcmp(s,&old,sizeof old)==0);
}
int main(void) {
    terminal_combination();
    tile_range();
    struct {uint32_t version,size;uint64_t mask[3],reserved;} profile={1,40,
        {(1ULL<<9)|(1ULL<<15)|(1ULL<<20),(1ULL<<63)|(1ULL<<49),0},0};
    assert(family_profile_admit64(&profile)==(EXPECT_DISPLAY?1:-13));
    profile.mask[1]=1ULL<<63;assert(family_profile_admit64(&profile)==1);
    profile.mask[2]=1ULL<<4;assert(family_profile_admit64(&profile)==-13);
    profile.mask[2]=0;profile.mask[1]|=1ULL<<50;assert(family_profile_admit64(&profile)==-13);
    ReistX64DisplayState s;native_display_core_init64(&s);
    assert(!native_display_core_admit64(&s));
    reist_display_request_v1 bind=request(REIST_DISPLAY_BIND);
    unchanged(&s,&bind,child,1000,3,-13);
    unchanged(&s,&bind,root,1000,2,-13);
    bind.flags=1;unchanged(&s,&bind,root,1000,3,-22);bind.flags=0;
    assert(native_display_core_apply64(&s,&bind,root,1000,3)==1);
    unchanged(&s,&bind,root,1000,3,-16);
    reist_display_request_v1 r=request(REIST_DISPLAY_QUERY);
    unchanged(&s,&r,child,1000,0,1);
    r.operation=REIST_DISPLAY_COMMIT;r.epoch=1;r.deadline_ms=1100;
    r.pixels=0x10000;r.x=32;r.y=32;r.width=r.height=64;r.stride=256;
    assert(native_display_rectangle64(&r,1024,768)==16384);
    r.x=UINT32_MAX;assert(native_display_rectangle64(&r,1024,768)==0);r.x=32;
    r.y=UINT32_MAX;assert(native_display_rectangle64(&r,1024,768)==0);r.y=32;
    r.width=65;assert(native_display_rectangle64(&r,1024,768)==0);r.width=64;
    r.stride=260;assert(native_display_rectangle64(&r,1024,768)==0);r.stride=256;
    r.epoch=0;unchanged(&s,&r,child,1000,0,-116);r.epoch=1;
    r.deadline_ms=1000;unchanged(&s,&r,child,1000,0,-110);
    r.deadline_ms=2001;unchanged(&s,&r,child,1000,0,-22);r.deadline_ms=1100;
    unchanged(&s,&r,child+(UINT64_C(1)<<32),1000,0,-13);
    unchanged(&s,&r,child,999,0,-84);
    r.width=0;unchanged(&s,&r,child,1000,0,-22);r.width=64;
    for(unsigned i=0;i<64;i++)assert(native_display_core_apply64(&s,&r,child,1000,0)==0);
    assert(s.commits==64 && s.bytes==1048576 && s.fenced==0);
    assert(native_display_core_apply64(&s,&r,child,1000,0)==-122);
    assert(s.fenced==1 && !native_display_core_admit64(&s));
    r.deadline_ms=1300;unchanged(&s,&r,child,1200,0,-13);
    unchanged(&s,&bind,root,1200,2,-13);
    bind.owner+=UINT64_C(1)<<32;
    assert(native_display_core_apply64(&s,&bind,root,1200,3)==2);
    r.owner=bind.owner;r.epoch=1;unchanged(&s,&r,bind.owner,1200,0,-116);r.epoch=2;
    assert(native_display_core_apply64(&s,&r,bind.owner,1200,0)==0);
    ReistX64DisplayState old=s;
    assert(native_display_core_fence64(&s,child)==0);
    assert(memcmp(&s,&old,sizeof s)==0);
    assert(native_display_core_fence64(&s,root)==0 && s.fenced==1);
    old=s;assert(native_display_core_fence64(&s,root)==0);
    assert(memcmp(&s,&old,sizeof s)==0);
    for(unsigned i=0;i<16;i++) {
        s=old;((uint64_t*)&s)[i]^=1;
        ReistX64DisplayState corrupt=s;
        assert(native_display_core_admit64(&s)==-84);
        assert(native_display_core_apply64(&s,&bind,root,1400,3)==-84);
        assert(native_display_core_fence64(&s,root)==-84);
        assert(memcmp(&s,&corrupt,sizeof s)==0);
    }
    native_display_core_init64(&s);bind=request(REIST_DISPLAY_BIND);
    assert(native_display_core_apply64(&s,&bind,root,1000,3)==1);
    r=request(REIST_DISPLAY_COMMIT);r.epoch=1;r.pixels=0x10000;
    r.width=r.height=1;r.stride=4;r.deadline_ms=2000;
    assert(native_display_core_apply64(&s,&r,child,1000,0)==0);
    assert(native_display_core_apply64(&s,&r,child,1099,0)==0 && s.commits==2);
    assert(native_display_core_apply64(&s,&r,child,1100,0)==0 && s.commits==1 && s.bytes==4);
    puts("DISPLAY_CORE_HOST_OK: rejection atomicity, quotas, epochs, fences, corrupt state");
    return 0;
}
