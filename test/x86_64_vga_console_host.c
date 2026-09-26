#undef NDEBUG
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "userspace/drivers/vga/text.h"
#include "arch/x86_64/video/vga_text_core.h"
#include <stdlib.h>

uint64_t syscall_rdx,syscall_r10,syscall_r8,syscall_r9,syscall_rsi;
uint64_t scheduler_current_slot,scheduler_last_tick;
uint8_t native_vga_status_lock;
uint64_t scheduler_tasks[8][128],family_records[8][8];
extern reist_vga_state native_vga_state;
extern uint8_t native_vga_request[64];
extern int64_t VGA_ABI vga_test_syscall(void);
static reist_vga_request_v1 domain_request;
static uint8_t user_buffer[256];
static unsigned buffer_rights=6;
void VGA_ABI scheduler_fail(void) { abort(); }
void VGA_ABI native_vga_status64(void) { }
int64_t VGA_ABI vga_test_range(uint64_t pointer,uint64_t size,uint64_t rights) {
    if(!size||pointer>UINT64_MAX-size)return 0;
    if(pointer==(uintptr_t)&domain_request && size==64 && rights==4)return 1;
    return pointer>=(uintptr_t)user_buffer && pointer+size<=(uintptr_t)user_buffer+sizeof user_buffer
        && (buffer_rights&rights)==rights;
}
static int64_t domain_call(void) {
    syscall_rsi=(uintptr_t)&domain_request;
    int64_t r=vga_test_syscall();
    for(unsigned i=0;i<64;i++)assert(!native_vga_request[i]);
    return r;
}
static void domain(void) {
    assert(native_vga_core_init64(&native_vga_state)==0);
    scheduler_tasks[0][1]=1;
    scheduler_tasks[4][0]=1;scheduler_tasks[4][1]=2;
    family_records[4][1]=UINT64_C(1)<<32;
    scheduler_current_slot=0;scheduler_last_tick=1;
    domain_request=(reist_vga_request_v1){1,64,REIST_VGA_BIND,0,(UINT64_C(2)<<32)|4,0,0,0,0,{0,0}};
    syscall_rsi=UINT64_MAX-16;
    assert(vga_test_syscall()==-14 && !native_vga_state.owner);
    family_records[4][1]=UINT64_C(2)<<32;
    assert(domain_call()==-1 && !native_vga_state.owner);
    family_records[4][1]=UINT64_C(1)<<32;
    assert(domain_call()==1);
    domain_request.operation=REIST_VGA_STATUS;domain_request.epoch=1;
    assert(domain_call()==-11); /* no health publication before self-test */
    domain_request.operation=REIST_VGA_REVOKE;
    assert(domain_call()==0);
    domain_request.operation=REIST_VGA_BIND;domain_request.epoch=0;
    assert(domain_call()==-1); /* fenced but still unreaped generation */
    scheduler_tasks[4][1]=3;domain_request.owner=(UINT64_C(3)<<32)|4;
    assert(domain_call()==2);
    scheduler_current_slot=4;domain_request.epoch=2;
    domain_request.operation=REIST_VGA_HEARTBEAT;
    assert(domain_call()==0);
    domain_request.operation=REIST_VGA_READ_OUTPUT;
    domain_request.buffer=(uintptr_t)user_buffer;domain_request.count=64;
    buffer_rights=4;
    assert(domain_call()==-14); /* output requires writable user memory */
    buffer_rights=6;
    domain_request.buffer=UINT64_MAX-16;
    assert(domain_call()==-14);
    domain_request.buffer=(uintptr_t)user_buffer;
    domain_request.count=65;
    assert(domain_call()==-22);
    domain_request.operation=REIST_VGA_WRITE_CELLS;domain_request.count=80;domain_request.offset=1841;
    assert(domain_call()==-22); /* must not reach the physical VGA store */
    domain_request.operation=REIST_VGA_SET_CURSOR;domain_request.count=0;domain_request.buffer=0;
    domain_request.offset=1920;
    assert(domain_call()==-22); /* must not reach privileged CRTC OUTs */
    domain_request.offset=0;domain_request.count=1;
    assert(domain_call()==-22);
    domain_request.buffer=(uintptr_t)user_buffer;
    domain_request.operation=REIST_VGA_READ_OUTPUT;domain_request.count=64;domain_request.offset=0;
    memcpy(user_buffer,"test",4);
    assert(native_vga_core_transfer64(&native_vga_state,user_buffer,4,0)==4);
    memset(user_buffer,0xaa,sizeof user_buffer);
    domain_request.owner-=UINT64_C(1)<<32;
    assert(domain_call()==-116 && user_buffer[0]==0xaa);
    domain_request.owner+=UINT64_C(1)<<32;
    assert(domain_call()==4 && !memcmp(user_buffer,"test",4) && user_buffer[4]==0xaa);
    syscall_rdx=1;
    assert(domain_call()==-22);
    syscall_rdx=0;
    puts("VGA production adapter: user permissions/ranges, parent, old reap and staging scrub passed");
}

static reist_vga_state state,snapshot;
static const uint64_t parent=UINT64_C(1)<<32,owner=(UINT64_C(2)<<32)|4;
static reist_vga_request_v1 request(unsigned op) {
    reist_vga_request_v1 q={0};
    q.version=1; q.size=64; q.operation=op; q.owner=owner;
    q.epoch=op==REIST_VGA_BIND||op==REIST_VGA_QUERY?0:state.epoch;
    return q;
}
static void core(void) {
    assert(native_vga_core_init64(&state)==0);
    assert(native_vga_core_admit64(&state)==0);
    reist_vga_request_v1 q=request(REIST_VGA_BIND);
    snapshot=state;
    for(unsigned flags=0;flags<3;flags++) {
        assert(native_vga_core_apply64(&state,&q,parent,1,flags)==-1);
        assert(!memcmp(&state,&snapshot,sizeof state));
    }
    assert(native_vga_core_apply64(&state,&q,parent|1,1,3)==-1);
    q.reserved[0]=1;
    assert(native_vga_core_apply64(&state,&q,parent,1,3)==-22);
    q.reserved[0]=0;
    assert(native_vga_core_apply64(&state,&q,parent,1,3)==1);
    assert(native_vga_core_apply64(&state,&q,parent,1,3)==-16);
    q=request(REIST_VGA_QUERY);
    assert(native_vga_core_apply64(&state,&q,owner,1,0)==1);
    assert(native_vga_core_apply64(&state,&q,owner+1,1,0)==-1);
    q=request(REIST_VGA_WRITE_CELLS); q.buffer=0x400000; q.count=80; q.offset=1840;
    assert(native_vga_core_apply64(&state,&q,owner,2,0)==0);
    snapshot=state;
    q.offset++;
    assert(native_vga_core_apply64(&state,&q,owner,3,0)==-22);
    assert(!memcmp(&state,&snapshot,sizeof state));
    q.offset=0; q.count=81;
    assert(native_vga_core_apply64(&state,&q,owner,3,0)==-22);
    q.count=80; q.epoch++;
    assert(native_vga_core_apply64(&state,&q,owner,3,0)==-116);
    q.epoch--; q.buffer=0;
    assert(native_vga_core_apply64(&state,&q,owner,3,0)==-14);
    q=request(9); /* appended SET_CURSOR, same generation-scoped device */
    assert(native_vga_core_apply64(&state,&q,owner,3,0)==0);
    q.offset=1919;
    assert(native_vga_core_apply64(&state,&q,owner,3,0)==0);
    snapshot=state;
    q.offset=1920;
    assert(native_vga_core_apply64(&state,&q,owner,4,0)==-22);
    q.offset=UINT32_MAX;
    assert(native_vga_core_apply64(&state,&q,owner,4,0)==-22);
    q.offset=0; q.count=1;
    assert(native_vga_core_apply64(&state,&q,owner,4,0)==-22);
    q.count=0; q.buffer=1;
    assert(native_vga_core_apply64(&state,&q,owner,4,0)==-22);
    q.buffer=0;
    assert(native_vga_core_apply64(&state,&q,parent,4,0)==-1);
    q.epoch++;
    assert(native_vga_core_apply64(&state,&q,owner,4,0)==-116);
    assert(!memcmp(&state,&snapshot,sizeof state));
    uint8_t bytes[64],readback[64];
    for(unsigned i=0;i<64;i++) bytes[i]=(uint8_t)i;
    for(unsigned i=0;i<32;i++) assert(native_vga_core_transfer64(&state,bytes,64,0)==64);
    snapshot=state;
    assert(native_vga_core_transfer64(&state,bytes,1,0)==-11);
    assert(!memcmp(&state,&snapshot,sizeof state));
    for(unsigned i=0;i<32;i++) {
        assert(native_vga_core_transfer64(&state,readback,64,1)==64);
        assert(!memcmp(bytes,readback,64));
    }
    assert(native_vga_core_transfer64(&state,readback,64,1)==-11);
    for(unsigned i=0;i<2048;i++) assert(!state.output[i]);
    assert(native_vga_core_transfer64(&state,bytes,63,2)==63);
    assert(native_vga_core_transfer64(&state,readback,62,3)==62);
    assert(native_vga_core_transfer64(&state,bytes,63,2)==63);
    assert(native_vga_core_transfer64(&state,readback,64,3)==64);
    assert(readback[0]==62 && !memcmp(bytes,readback+1,63));
    q=request(REIST_VGA_HEARTBEAT);
    assert(native_vga_core_apply64(&state,&q,owner,1000,0)==0);
    snapshot=state;
    assert(native_vga_core_apply64(&state,&q,owner,2000,0)==-110);
    assert(!memcmp(&state,&snapshot,sizeof state));
    q=request(REIST_VGA_STATUS);
    assert(native_vga_core_apply64(&state,&q,owner,1000,0)==-1);
    assert(native_vga_core_apply64(&state,&q,parent,1999,0)==0);
    assert(native_vga_core_fence64(&state,owner+1)==0 && state.fenced==2);
    assert(native_vga_core_transfer64(&state,bytes,64,0)==64);
    assert(native_vga_core_fence64(&state,owner)==0 && state.fenced);
    for(unsigned i=0;i<2048;i++) assert(!state.output[i]);
    assert(native_vga_core_transfer64(&state,bytes,1,0)==-32);
    q=request(9);
    assert(native_vga_core_apply64(&state,&q,owner,1999,0)==-32);
    assert(native_vga_core_fence64(&state,owner)==0);
    q=request(REIST_VGA_BIND); q.owner+=UINT64_C(1)<<32;
    assert(native_vga_core_apply64(&state,&q,parent,2000,3)==2);
    q=request(REIST_VGA_HEARTBEAT);
    assert(native_vga_core_apply64(&state,&q,owner,2000,0)==-116);
    snapshot=state;
    for(unsigned i=0;i<20;i++) {
        ((uint64_t *)&state)[i]^=1;
        assert(native_vga_core_admit64(&state)==-84);
        state=snapshot;
    }
    assert(native_vga_core_fence64(&state,parent)==0);
    assert(native_vga_core_admit64(&state)==0);
    puts("VGA production core: authority, generations, queues, health and fencing passed");
}

static struct { uint64_t before; reist_vga_text text; uint64_t after; } guarded;
static reist_vga_text *const t = &guarded.text;
static void feed(const char *s) {
    while (*s) assert(reist_vga_text_byte(t, (uint8_t)*s++) == 0);
}
static void fresh(void) {
    memset(&guarded, 0, sizeof guarded);
    guarded.before = guarded.after = UINT64_C(0xabcd012398765432);
    reist_vga_text_init(t);
    /* The final line belongs to early/fatal kernel status, never to scrolling. */
    for (unsigned i=1920;i<2000;i++) t->cells[i]=0x4f21;
}
static void boundaries(void) {
    assert(guarded.before == UINT64_C(0xabcd012398765432));
    assert(guarded.after == guarded.before);
    for(unsigned i=1920;i<2000;i++) assert(t->cells[i]==0x4f21);
    assert(t->row<24 && t->column<80);
}
int main(void) {
    domain();
    core();
    fresh(); feed("REIST\r\n> no-such-command\r\nERROR\r\n> ");
    assert(t->cells[0]==0x0752 && t->cells[160]==0x0745);
    assert(t->row==3 && t->column==2); boundaries();
    fresh(); feed("abc\bX\tY\rZ");
    assert(t->cells[0]==0x075a && t->cells[2]==0x0758 && t->cells[8]==0x0759);
    fresh(); for(unsigned i=0;i<80;i++) feed("a");
    assert(t->row==0 && t->column==79); feed("b");
    assert(t->row==1 && t->column==1 && t->cells[80]==0x0762);
    fresh(); for(unsigned i=0;i<80;i++) feed("a"); feed("\r\nB");
    assert(t->row==1 && t->cells[80]==0x0742);
    fresh(); for(unsigned i=0;i<25;i++) { feed("x"); feed("\r\n"); }
    assert(t->row==23 && t->column==0 && t->cells[22*80]==0x0778);
    assert(t->cells[23*80]==0x0720); boundaries();
    fresh(); feed("\033[24;80HX!");
    assert(t->cells[22*80+79]==0x0758 && t->cells[23*80]==0x0721); boundaries();
    fresh(); feed("\033[31mR\033[1mB\033[0mN");
    assert(t->cells[0]==0x0452 && t->cells[1]==0x0c42 && t->cells[2]==0x074e);
    feed("\033[2J\033[Hhello\033[3D\033[K");
    assert(t->cells[0]==0x0768 && t->cells[1]==0x0765 && t->cells[2]==0x0720);
    /* Split escape input, unsupported/overflowed parameters and cancellation. */
    fresh(); feed("\033["); feed("2;"); feed("3HX");
    assert(t->cells[82]==0x0758);
    feed("\033[999999999999999999999999999999999999H"); boundaries();
    feed("\033[1;2;3;4;5;6;7;8;9m"); boundaries();
    feed("\033[12\030Q"); assert((t->cells[83]&255)=='Q');
    /* Every byte class is bounded, including random and incomplete sequences. */
    uint32_t seed=1;
    for(unsigned i=0;i<100000;i++) {
        seed=seed*1664525u+1013904223u;
        assert(reist_vga_text_byte(t,(uint8_t)(seed>>24))==0);
        boundaries();
    }
    reist_vga_text saved=*t;
    t->row=24;
    reist_vga_text bad=*t;
    assert(reist_vga_text_byte(t,'x')==-84 && !memcmp(t,&bad,sizeof bad));
    *t=saved; t->column=80; bad=*t;
    assert(reist_vga_text_byte(t,'x')==-84 && !memcmp(t,&bad,sizeof bad));
    assert(reist_vga_text_byte(NULL,'x')==-22);
    puts("VGA production renderer: controls, scroll, split CSI, bounds and corrupt-state denial passed");
    return 0;
}
