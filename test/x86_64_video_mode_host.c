#undef NDEBUG
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "arch/x86_64/video/video_mode.h"
#include "userspace/drivers/video/native_mode.h"
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/display.h>
static uint64_t probe_clock;
static unsigned probe_queries,probe_commits,probe_blocked;
static uint64_t probe_window;
static unsigned probe_window_commits;
static int64_t probe_call0(uint64_t op) {
    if(op==REIST_X64_SYS_GETPID)return 7;
    assert(op==REIST_X64_SYS_MONOTONIC_MS);return (int64_t)probe_clock;
}
static int64_t probe_call1(uint64_t op,uint64_t delay) {
    assert(op==REIST_X64_SYS_SLEEP_MS);
    if(!delay || delay>100)return -22;
    probe_clock+=delay;return 0;
}
static int64_t probe_call2(uint64_t op,uint64_t device,uint64_t pointer) {
    assert(op==REIST_X64_SYS_DEVICE_CONTROL && device==30);
    const reist_display_request_v1 *q=(void *)(uintptr_t)pointer;
    assert(q->version==1 && q->size==64 && !q->flags && q->owner==((UINT64_C(7)<<32)|4));
    if(q->operation==REIST_DISPLAY_QUERY) {
        assert(!q->epoch && !q->deadline_ms && !q->pixels);
        probe_queries++;
        /* Real pre-map/pre-bind outcomes, followed by exact epoch admission. */
        if(probe_blocked || probe_queries==2)return -13;
        if(probe_queries==1)return -19;
        return 3;
    }
    assert(q->operation==REIST_DISPLAY_COMMIT && q->epoch==3);
    if(probe_clock/100!=probe_window) {probe_window=probe_clock/100;probe_window_commits=0;}
    if(probe_window_commits==64)return -122;
    probe_window_commits++;
    assert(q->deadline_ms==probe_clock+100 && q->width==64 && q->height==64 && q->stride==256);
    assert(q->x==(probe_commits%16)*64 && q->y==(probe_commits/16)*64);
    const uint32_t *pixels=(void *)(uintptr_t)q->pixels;
    uint32_t color=q->x<320?0x00336699:q->x<704?0x00339966:0x00996633;
    for(unsigned i=0;i<4096;i++)assert(pixels[i]==color);
    assert(probe_commits++<192);return 0;
}
#define reist_x64_syscall0 probe_call0
#define reist_x64_syscall1 probe_call1
#define reist_x64_syscall2 probe_call2
#define main probe_main
#include "userspace/gui/compositor/native_mode_probe.c"
#undef main
#undef reist_x64_syscall0
#undef reist_x64_syscall1
#undef reist_x64_syscall2
static void probe(void) {
    assert(!probe_main(1,0) && probe_queries==3 && probe_commits==192 && probe_clock==1500);
    probe_queries=probe_commits=0;probe_clock=0;probe_blocked=1;
    assert(probe_main(1,0)==110 && probe_queries==200 && !probe_commits && probe_clock==2000);
    puts("VIDEO_PROBE_OK: real pre-bind wait, complete pixels and absolute timeout");
}
static unsigned calls,fences,expected,fail_step=99,fail_fence;
static int step(void *p,unsigned n) {
    (void)p;assert(n==expected++);calls++;
    return n==fail_step?-5:0;
}
static int fence(void *p) {(void)p;fences++;return fail_fence?-5:0;}
static const reist_video_io io={0,step,fence};
static const uint64_t owner=(UINT64_C(2)<<32)|5,parent=UINT64_C(1)<<32;
static reist_video_request_v1 request(unsigned op) {
    reist_video_request_v1 q={1,64,op,0,owner,op==REIST_VIDEO_BIND||op==REIST_VIDEO_QUERY?0:1,{0}};
    return q;
}
static void fifo(void) {
    struct { uint32_t guard0,area[4096],guard1; } guarded={0};
    uint32_t *area=guarded.area,before[4096];
    guarded.guard0=guarded.guard1=0x5a55a55a;
    area[0]=16;area[1]=16384;area[2]=16380;area[3]=36;
    assert(!reist_video_fifo_update(area,16,10,20,64,64,1));
    assert(area[4095]==1 && area[4]==10 && area[5]==20 && area[6]==64 && area[7]==64 && area[2]==32);
    area[2]=16;area[3]=36;memcpy(before,area,16384);
    assert(reist_video_fifo_update(area,16,0,0,64,64,1)==-11);
    assert(!memcmp(before,area,16384));
    area[3]=40;
    assert(!reist_video_fifo_update(area,16,960,704,64,64,0));
    assert(!memcmp(before+4,area+4,16384-16));
    assert(reist_video_fifo_update(area,16,961,704,64,64,1)==-22);
    area[0]=20;assert(reist_video_fifo_update(area,16,0,0,64,64,1)==-5);
    area[0]=16;area[3]=16384;assert(reist_video_fifo_update(area,16,0,0,64,64,1)==-5);
    area[3]=40;area[1]=4096;assert(reist_video_fifo_update(area,16,0,0,64,64,1)==-5);
    area[1]=16384;assert(reist_video_fifo_update(area,4092,0,0,1,1,1)==-22);
    /* Independent host consumer: require QEMU's >=10KiB usable ring, then
     * decode every command across multiple wraps; no synthetic STOP advance
     * before the complete UPDATE was checked. */
    for(unsigned header=16;header<=4072;header+=4056) {
        memset(area,0,16384);area[0]=header;area[1]=16384;area[2]=area[3]=header;
        assert(area[1]-area[0]>=10240);
        for(unsigned n=0;n<2000;n++) {
            unsigned x=(n%16)*64,y=(n%12)*64;
            assert(!reist_video_fifo_update(area,header,x,y,64,64,1));
            unsigned expected[5]={1,x,y,64,64},stop=area[3];
            for(unsigned k=0;k<5;k++) {
                assert(area[stop/4]==expected[k]);stop+=4;if(stop==area[1])stop=area[0];
            }
            assert(stop==area[2]);area[3]=stop;
        }
    }
    assert(guarded.guard0==0x5a55a55a && guarded.guard1==0x5a55a55a);
    puts("VIDEO_FIFO_OK:16KiB, minimum capacity, repeated consume/wrap, full preflight, guards and corrupt header denial");
}
static uint64_t policy_now;
static unsigned policy_calls,policy_fail=99;
static uint64_t policy_clock(void *p) {(void)p;return policy_now++;}
static int64_t policy_request(void *p,unsigned op,unsigned step) {
    (void)p;assert(op==REIST_VIDEO_STEP && step==policy_calls++);
    return step==policy_fail?-5:0;
}
static void policy(void) {
    reist_video_transport io={0,policy_clock,policy_request};
    policy_now=100;policy_calls=0;
    assert(!reist_video_enter(&io,2100)&&policy_calls==9);
    for(policy_fail=0;policy_fail<9;policy_fail++) {
        policy_now=100;policy_calls=0;
        assert(reist_video_enter(&io,2100)==-5 && policy_calls==policy_fail+1);
    }
    policy_fail=99;policy_now=100;policy_calls=0;
    assert(reist_video_enter(&io,104)==-110 && policy_calls==4);
    policy_now=100;policy_calls=0;
    assert(reist_video_enter(&io,2101)==-110 && !policy_calls);
    policy_now=100;policy_calls=REIST_VIDEO_STOP;
    assert(!reist_video_leave(&io,2100)&&policy_calls==10);
    puts("VIDEO_POLICY_OK: exact Ring3 sequence and original absolute deadline");
}
static void resources(void) {
    reist_video_pci p={REIST_VIDEO_QEMU,0x040515ad,0x03000000,3,0,
                       {0xc011,0xfd000008,0xfe000008},16777216,65536};
    reist_video_memory_range map[2]={{0,0xc0000000,1,0},{UINT64_C(0x100000000),0x40000000,1,0}};
    reist_video_resources out={0},saved;
    assert(!reist_video_resources_admit(&p,map,2,&out));
    assert(out.port==0xc010 && out.framebuffer==0xfd000000 && out.fifo==0xfe000000);
    saved=out;
    p.bar[2]=p.bar[1];assert(reist_video_resources_admit(&p,map,2,&out)==-19);
    assert(!memcmp(&out,&saved,sizeof out));p.bar[2]=0xfe000008;
    map[0].length=UINT64_C(0x100000000);
    assert(reist_video_resources_admit(&p,map,2,&out)==-19);map[0].length=0xc0000000;
    p.framebuffer_bytes=3*1024*1024;assert(reist_video_resources_admit(&p,map,2,&out)==-19);
    p.framebuffer_bytes=16777216;p.bar[1]=0xfd000004;
    assert(reist_video_resources_admit(&p,map,2,&out)==-19);p.bar[1]=0xfd000008;
    p.profile=0;assert(reist_video_resources_admit(&p,map,2,&out)==-19);
    p.profile=REIST_VIDEO_VMWARE;p.framebuffer_bytes=134217728;p.fifo_bytes=8388608;
    p.bar[1]=0xe8000008;p.bar[2]=0xfe000008;
    assert(!reist_video_resources_admit(&p,map,2,&out));
    map[1].base=UINT64_MAX;map[1].length=2;
    assert(reist_video_resources_admit(&p,map,2,&out)==-22);
    puts("VIDEO_RESOURCES_OK: proven apertures, RAM/region overlap, 64-bit BAR and overflow denial");
}
int main(void) {
    probe();
    fifo();policy();
    resources();
    reist_video_state s,before;
    reist_video_init(&s);assert(reist_video_valid(&s));
    reist_video_request_v1 q=request(REIST_VIDEO_BIND);
    before=s;
    for(unsigned f=0;f<3;f++)assert(reist_video_apply(&s,&q,parent,10,f,&io)==-1);
    assert(!memcmp(&s,&before,sizeof s)&&!calls&&!fences);
    assert(reist_video_apply(&s,&q,parent,10,3,&io)==1);
    q=request(REIST_VIDEO_STEP);before=s;
    assert(reist_video_apply(&s,&q,parent,11,0,&io)==-1);
    q.epoch++;assert(reist_video_apply(&s,&q,owner,11,0,&io)==-116);q.epoch--;
    q.step=1;assert(reist_video_apply(&s,&q,owner,11,0,&io)==-22);q.step=0;
    q.reserved[3]=1;assert(reist_video_apply(&s,&q,owner,11,0,&io)==-22);q.reserved[3]=0;
    assert(!memcmp(&s,&before,sizeof s)&&!calls&&!fences);
    for(unsigned i=0;i<=REIST_VIDEO_READY;i++) {
        q.step=i;assert(reist_video_apply(&s,&q,owner,11+i,0,&io)==0);
    }
    assert(calls==9&&s.word[VM_PHASE]==REIST_VIDEO_GRAPHICS);
    before=s;
    assert(reist_video_apply(&s,&q,owner,22,0,&io)==-22);
    assert(!memcmp(&s,&before,sizeof s)&&calls==9);
    q=request(REIST_VIDEO_HEARTBEAT);
    assert(reist_video_apply(&s,&q,owner,1000,0,&io)==0);
    q=request(REIST_VIDEO_STATUS);
    assert(reist_video_apply(&s,&q,parent,1999,0,&io)==REIST_VIDEO_GRAPHICS);
    assert(reist_video_apply(&s,&q,parent,2000,0,&io)==-110);
    assert(reist_video_retire(&s,owner+1,&io)==0&&!fences);
    assert(reist_video_retire(&s,owner,&io)==0&&fences==1&&s.word[VM_FENCED]);
    assert(reist_video_retire(&s,owner,&io)==0&&fences==1);
    q=request(REIST_VIDEO_FENCE);
    assert(reist_video_apply(&s,&q,parent,2000,0,&io)==0&&fences==1&&reist_video_valid(&s));
    q=request(REIST_VIDEO_STEP);
    assert(reist_video_apply(&s,&q,owner,2000,0,&io)==-32);
    before=s;
    for(unsigned i=0;i<24;i++) {
        ((uint64_t*)&s)[i]^=1;assert(!reist_video_valid(&s));s=before;
    }
    /* Each failed step fences exactly once and denies future operations. */
    for(fail_step=0;fail_step<=REIST_VIDEO_READY;fail_step++) {
        reist_video_init(&s);expected=0;calls=0;fences=0;
        q=request(REIST_VIDEO_BIND);assert(reist_video_apply(&s,&q,parent,10,3,&io)==1);
        q=request(REIST_VIDEO_STEP);
        for(unsigned i=0;i<=fail_step;i++) {
            q.step=i;
            assert(reist_video_apply(&s,&q,owner,11+i,0,&io)==(i==fail_step?-5:0));
        }
        assert(fences==1&&s.word[VM_FENCED]&&reist_video_valid(&s));
        assert(reist_video_apply(&s,&q,owner,30,0,&io)==-32);
    }
    /* Heartbeats cannot renew the absolute preparation deadline. */
    reist_video_init(&s);q=request(REIST_VIDEO_BIND);
    assert(reist_video_apply(&s,&q,parent,10,3,&io)==1);
    q=request(REIST_VIDEO_HEARTBEAT);
    assert(reist_video_apply(&s,&q,owner,900,0,&io)==0);
    assert(reist_video_apply(&s,&q,owner,1800,0,&io)==0);
    before=s;
    assert(reist_video_apply(&s,&q,owner,2010,0,&io)==-110);
    assert(!memcmp(&s,&before,sizeof s));
    fail_fence=1;q=request(REIST_VIDEO_FENCE);
    assert(reist_video_apply(&s,&q,parent,2010,0,&io)==-5&&reist_video_valid(&s));
    assert(s.word[VM_FENCED]&&s.word[VM_FAULT]);
    q=request(REIST_VIDEO_BIND);
    assert(reist_video_apply(&s,&q,parent,2011,3,&io)==-5);
    puts("VIDEO_CORE_OK: exact authority, ordering, health, corrupt seals and step failure fencing");
    return 0;
}
