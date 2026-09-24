#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "arch/x86_64/video/display_core.h"
extern ReistX64DisplayState native_display_state;
extern unsigned char native_display_request[16456];
extern uint32_t native_display_boot[8];
extern uint64_t native_display_commits,scheduler_current_slot,fake_task[2];
extern int64_t DISPLAY_ABI display_invoke(void *);
static uintptr_t readable,writable;
uint64_t DISPLAY_ABI display_validate_backend(uintptr_t p,uint64_t bytes,uint64_t flags) {
    return bytes==64 && ((flags==4 && p==readable)||(flags==2 && p==writable));
}
static reist_display_info_v2 request(void) {
    reist_display_info_v2 q={0};q.version=2;q.size=64;q.operation=REIST_DISPLAY_INFO;
    q.owner=UINT64_C(7)<<32|4;q.epoch=1;return q;
}
static void reset(void) {
    reist_display_request_v1 bind={0};bind.version=1;bind.size=64;bind.operation=1;
    bind.owner=UINT64_C(7)<<32|4;
    native_display_core_init64(&native_display_state);
    assert(native_display_core_apply64(&native_display_state,&bind,UINT64_C(3)<<32,100,3)==1);
    scheduler_current_slot=4;fake_task[0]=7;
}
static int64_t invoke(reist_display_info_v2 *q,int write) {
    readable=(uintptr_t)q;writable=write?readable:0;
    ReistX64DisplayState before=native_display_state;
    uint64_t commits=native_display_commits;
    int64_t result=display_invoke(q);
    assert(!memcmp(&before,&native_display_state,sizeof before));
    assert(commits==native_display_commits);
    for(unsigned n=0;n<sizeof native_display_request;n++)assert(native_display_request[n]==0);
    return result;
}
static void denied(reist_display_info_v2 q,int64_t result,int write) {
    reist_display_info_v2 before=q;
    assert(invoke(&q,write)==result);
    assert(!memcmp(&q,&before,sizeof q));
}
int main(void) {
    reset();reist_display_info_v2 q=request();
#if EXPECT_INFO
    assert(invoke(&q,1)==0);
    assert(q.width==1024 && q.height==768 && q.pitch==4096 && q.bits_per_pixel==32);
    assert(q.red_field_position==16 && q.green_field_position==8 && q.blue_field_position==0 && !q.reserved);
    assert(q.owner==(UINT64_C(7)<<32|4) && q.epoch==1 && q.version==2 && q.size==64 && q.operation==5 && !q.flags);
    native_display_boot[2]=3200;native_display_boot[3]=800;native_display_boot[4]=600;
    q=request();assert(invoke(&q,1)==0 && q.width==800 && q.height==600 && q.pitch==3200);
    q=request();q.epoch=0;denied(q,-116,1);
    q=request();q.owner++;denied(q,-116,1);
    q=request();scheduler_current_slot=5;denied(q,-13,1);scheduler_current_slot=4;
    q=request();fake_task[0]=8;denied(q,-13,1);fake_task[0]=7;
    for(unsigned n=0;n<64;n++) {
        if(n>=16 && n<32)continue;
        q=request();((unsigned char *)&q)[n]^=0x80;denied(q,-22,1);
    }
    q=request();denied(q,-14,0);
    readable=writable=0;assert(display_invoke((void *)(uintptr_t)-1)==-14);
    /* An information request cannot replenish an exhausted copy window. */
    reist_display_request_v1 tile={0};tile.version=1;tile.size=64;tile.operation=3;
    tile.owner=q.owner;tile.epoch=1;tile.deadline_ms=200;tile.pixels=1;
    tile.width=tile.height=64;tile.stride=256;
    for(unsigned n=0;n<64;n++)assert(native_display_core_apply64(&native_display_state,&tile,q.owner,100,0)==0);
    assert(native_display_state.commits==64 && native_display_state.bytes==1048576);
    q=request();assert(invoke(&q,1)==0);
    q=request();
    assert(native_display_core_fence64(&native_display_state,q.owner)==0);
    denied(q,-13,1);
#else
    denied(q,-22,1);denied(q,-22,0);
#endif
    reset();reist_display_request_v1 old={0};old.version=1;old.size=64;old.operation=2;
    old.owner=UINT64_C(7)<<32|4;
    readable=(uintptr_t)&old;writable=0;
    assert(display_invoke(&old)==1);
    puts("actual display info syscall/core passed");return 0;
}
