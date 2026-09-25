#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/graphical_session.h>
static uint64_t clock_value;
static unsigned driver_test,driver_clocks,driver_sleeps,driver_reads,driver_delay;
static unsigned client_test,client_receives,client_sleeps;
static int64_t mock0(uint64_t op) {
    if(op==REIST_X64_SYS_MONOTONIC_MS){if(driver_test)driver_clocks++;return (int64_t)clock_value;}
    assert(op==REIST_X64_SYS_GETPID);return 9;
}
static int64_t mock1(uint64_t op,uint64_t a) {
    if(client_test && op==REIST_X64_SYS_SLEEP_MS){assert(a==10);clock_value+=a;client_sleeps++;return 0;}
    if(driver_test && op==REIST_X64_SYS_SLEEP_MS){driver_delay=(unsigned)a;clock_value+=a;return ++driver_sleeps==20?-5:0;}
    (void)op;(void)a;assert(0);return -5;
}
static int64_t mock3(uint64_t op,uint64_t a,uint64_t b,uint64_t c) {
    if(client_test && op==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT){assert(a==1 && b && c<=100);clock_value+=c;client_receives++;return c?-110:-11;}
    if(driver_test && op==REIST_X64_SYS_IPC_SEND_TIMEOUT){assert(a==1 && b && c==100);return 0;}
    (void)op;(void)a;(void)b;(void)c;assert(0);return -5;
}
#define reist_x64_syscall0 mock0
#define reist_x64_syscall1 mock1
#define reist_x64_syscall3 mock3
#define memcpy startup_memcpy
#define memset startup_memset
#include "../userspace/gui/lib/native_surface.c"
#undef memcpy
#undef memset
#include "../userspace/drivers/ps2/native_input.h"
static int64_t mock2(uint64_t op,uint64_t a,uint64_t b) {
    assert(driver_test && op==REIST_X64_SYS_DEVICE_CONTROL && a==31);
    const reist_input_request_v1 *q=(void *)(uintptr_t)b;
    if(q->operation==REIST_INPUT_QUERY)return 7;
    assert(q->operation==REIST_INPUT_READ && q->deadline_ms==clock_value+100);
    driver_reads++;return -11;
}
#define reist_x64_syscall2 mock2
#define main startup_driver_main
#include "../userspace/drivers/ps2/native_session.c"
#undef main
void reist_ps2_clear(reist_ps2_decoder *s){memset(s,0,sizeof(*s));}
int reist_ps2_initialize(const reist_ps2_transport *t,uint64_t end){assert(t && end>clock_value);return 0;}
int reist_ps2_decode(reist_ps2_decoder *s,uint8_t a,uint8_t b,uint64_t now,reist_input_event_v1 *e) {
    (void)s;(void)a;(void)b;(void)now;(void)e;assert(0);return -5;
}
static void driver_idle(void) {
    char *argv[]={"input","00000001","00000002","00000000","00000001","00000000","000007d0","0"};
    clock_value=100;driver_test=1;
    assert(startup_driver_main(8,argv)==5);
    assert(driver_sleeps==20 && driver_reads==20);
#ifdef TEST_FULL
    assert(driver_delay==50 && driver_clocks<=49);
    assert(reist_native_audit.sequence && reist_native_audit.sequence<=4);
    const volatile reist_native_audit_entry *entry=&reist_native_audit.entries[0];
    assert(entry->sequence==1 && entry->ms==100 && entry->endpoint==1);
    assert(entry->wire[0]==1 && entry->wire[8]==64 && entry->wire[12]==2);
#else
    assert(driver_delay==10 && driver_clocks<=67);
#endif
    driver_test=0;
}
#include <reist/gui/surface_client.h>
static unsigned paint_calls,paint_failure,paint_length;
static const char *paint_expected;
static int line_text(reist_gui_surface_client_t *c,int32_t x,int32_t y,uint32_t width,
                     const char *value,uint32_t length,uint32_t fg,uint32_t bg) {
    assert(c && ++paint_calls==1 && x==12 && y==48);
#ifdef TEST_FULL
    static unsigned previous_length;
    unsigned extent=paint_length>previous_length?paint_length:previous_length;
    assert(width==extent*8);
    if(!paint_failure)previous_length=paint_length;
#else
    assert(width==296);
#endif
    assert(length==paint_length && !memcmp(value,paint_expected,length));
    assert(fg==0xeaf2fa && bg==0x18222d);
    return paint_failure ? -(int)paint_failure : 0;
}
#ifdef TEST_FULL
static void inject_keys(reist_gui_surface_client_t *c) {
    c->event_owner=c;c->deferred_head=0;c->deferred_count=3;
    for(unsigned n=0;n<3;n++) {
        memset(&c->deferred[n],0,sizeof(c->deferred[n]));
        c->deferred[n].surface=c->surface;
        c->deferred[n].type=n==2?REIST_GUI_SURFACE_CLOSE:REIST_GUI_SURFACE_INPUT;
        c->deferred[n].input.type=REIST_GUI_SURFACE_INPUT_KEYBOARD;
        c->deferred[n].input.serial=n+1;c->deferred[n].input.pressed=1;
        c->deferred[n].input.key='b'+n;
    }
}
#define reist_gui_surface_client_dynamic_text line_text
#endif
static int unexpected_surface_call(int unused,...){(void)unused;assert(0);return -5;}
#define reist_gui_surface_client_init(...) unexpected_surface_call(0,__VA_ARGS__)
#define reist_gui_surface_client_create(...) unexpected_surface_call(0,__VA_ARGS__)
#define reist_gui_surface_client_ack_configure(...) unexpected_surface_call(0,__VA_ARGS__)
#define reist_gui_surface_client_paint_begin(...) unexpected_surface_call(0,__VA_ARGS__)
#define reist_gui_surface_client_paint_fill(...) unexpected_surface_call(0,__VA_ARGS__)
#define reist_gui_surface_client_paint_text line_text
#define reist_gui_surface_client_paint_commit(...) unexpected_surface_call(0,__VA_ARGS__)
static int deferred_receive(reist_gui_surface_client_t *c,reist_gui_surface_message_t *m,uint32_t timeout) {
    reist_gui_surface_client_t *q=c->event_owner;assert(!timeout && q && q->deferred_count);
    *m=q->deferred[q->deferred_head];q->deferred_head=(q->deferred_head+1)%REIST_GUI_SURFACE_MAX_PENDING_EVENTS;
    --q->deferred_count;return 0;
}
#define reist_gui_surface_client_receive deferred_receive
#define args startup_client_args
#define main startup_client_main
#include "../userspace/gui/apps/native_client.c"
#undef main
#undef args
static void paint_reply_audit(void) {
    reist_native_audit_init(9,1);clock_value=700;
    x86os_ipc_message_t m={0};m.version=1;m.struct_size=140;m.length=124;
    m.payload[0]=6;m.payload[4]=124;
    for(unsigned type=16;type<=17;type++) {
        m.payload[8]=type;audit_received(1,&m);
#ifdef TEST_FULL
        assert(reist_native_audit.sequence==type-15);
        assert(reist_native_audit.entries[type-16].ms==700);
        assert(!memcmp((const void*)reist_native_audit.entries[type-16].wire,&m,140));
#else
        assert(!reist_native_audit.sequence);
#endif
    }
    uint64_t count=reist_native_audit.sequence;
    m.payload[8]=11;audit_received(1,&m);assert(reist_native_audit.sequence==count);
}
static void text_line_frames(void) {
#ifdef TEST_FULL
    const unsigned lengths[]={0,3,37};
    for(unsigned n=0;n<3;n++) {
        text_size=lengths[n];memset(text,'a',text_size);text[text_size]=0;
        paint_expected=text_size?text:" ";paint_length=text_size?text_size:1;
        paint_failure=0;paint_calls=0;
        assert(paint_update()==0 && paint_calls==1);
        const unsigned failures[]={0,32,71,110};
        for(unsigned fail=1;fail<=3;fail++) {
            paint_calls=0;paint_failure=failures[fail];
            assert(paint_update()==-(int)failures[fail] && paint_calls==1);
        }
    }
#endif
}
static void text_already_queued(void) {
#ifdef TEST_FULL
    text_size=1;text[0]='a';text[1]=0;
    paint_expected="abc";paint_length=3;paint_failure=0;paint_calls=0;inject_keys(&client);
    assert(paint_update()==0 && paint_calls==1 && text_size==3);
    assert(client.deferred_count==1 && client.deferred[client.deferred_head].type==REIST_GUI_SURFACE_CLOSE);
    client.deferred_count=0;
#endif
}
static void client_idle(void) {
    char *argv[]={"text","00000001","00000002","00000000","00000001","00000000","000001f4","0"};
    clock_value=100;client_test=1;
    assert(startup_client_main(8,argv)==71 && clock_value==500);
#ifdef TEST_FULL
    assert(client_receives==4 && !client_sleeps);
#else
    assert(client_receives==40 && client_sleeps==40);
#endif
    client_test=0;
}
static uint64_t owner(unsigned r,unsigned gen) {return (uint64_t)gen<<32|(4+r);}
static void bound(reist_graphical_state *s,uint64_t now) {
    assert(!reist_graphical_init(s,1ULL<<32,now));
    assert(!reist_graphical_begin(s,now));
    for(unsigned r=0;r<4;r++)assert(!reist_graphical_bind(s,r,owner(r,2+r),now));
}
static void parser(unsigned limit) {
    char end[9];char *args[]={"role","00000001","00000002","00000000","00000001","00000000",end,"0"};
    reist_native_role_args out,before;clock_value=100;
    memset(&out,0x55,sizeof(out));before=out;
    snprintf(end,sizeof(end),"%08x",100+limit+1);
    assert(reist_native_role_arguments(8,args,6,&out)==-22);
    assert(!memcmp(&out,&before,sizeof(out)));
    snprintf(end,sizeof(end),"%08x",100+limit);
    assert(!reist_native_role_arguments(8,args,6,&out));
    assert(out.deadline==100+limit && out.owner==owner(2,9));
    before=out;clock_value=out.deadline;
    assert(reist_native_role_arguments(8,args,6,&out)==-22);
    assert(!memcmp(&out,&before,sizeof(out)));
}
int main(void) {
#ifdef TEST_FULL
    const unsigned limit=10000;
#else
    const unsigned limit=3000;
#endif
    assert(REIST_GRAPHICAL_START_MS==limit);
    assert(REIST_GRAPHICAL_HEALTH_MS==1000 && REIST_GRAPHICAL_RETIRE_MS==5000);
    parser(limit);
    reist_graphical_state s,before,late;
    bound(&s,100);assert(s.start_end==100+limit);before=s;
    assert(reist_graphical_begin(&s,101)==-16 && !memcmp(&s,&before,sizeof(s)));
    assert(reist_graphical_bind(&s,0,owner(0,20),101)==-16 && !memcmp(&s,&before,sizeof(s)));
    assert(reist_graphical_ready(&s,2,31,101)==-116 && !memcmp(&s,&before,sizeof(s)));
    assert(reist_graphical_ready(&s,1,15,101)==-71 && !memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_expired(&s,99+limit));
    assert(reist_graphical_expired(&s,100+limit)==15);
    late=s;assert(reist_graphical_ready(&late,1,31,100+limit)==-110);
    assert(!memcmp(&late,&s,sizeof(s)));
    assert(!reist_graphical_isolate(&late,0,100+limit));
    for(unsigned r=0;r<4;r++) {
        assert(reist_graphical_reaped(&late,r,late.roles[r].owner,101+limit)==-13);
        assert(!reist_graphical_fenced(&late,r,late.roles[r].owner,15,101+limit));
        assert(!reist_graphical_reaped(&late,r,late.roles[r].owner,101+limit));
    }
    assert(!reist_graphical_finish(&late,0,102+limit));
    assert(late.phase==REIST_GRAPHICAL_OFF && !late.start_end);
    assert(!reist_graphical_ready(&s,1,31,99+limit));
    assert(!reist_graphical_expired(&s,1098+limit));
    assert(reist_graphical_expired(&s,1099+limit)==15);
    uint64_t t=100+limit,old=s.roles[2].owner;
    assert(!reist_graphical_isolate(&s,2,t));
    assert(!reist_graphical_fenced(&s,2,old,1,t));
    assert(!reist_graphical_reaped(&s,2,old,t));before=s;
    assert(reist_graphical_bind(&s,2,old,t)==-116 && !memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_bind(&s,2,owner(2,10),t));before=s;
    assert(reist_graphical_heartbeat(&s,2,old,1,1,t+1)==-116 && !memcmp(&s,&before,sizeof(s)));
    assert(!(reist_graphical_expired(&s,t+limit-1)&4));
    assert(reist_graphical_expired(&s,t+limit)&4);
    late=s;assert(reist_graphical_heartbeat(&late,2,owner(2,10),1,1,t+limit)==-110);
    assert(!memcmp(&late,&s,sizeof(s)));
    assert(!reist_graphical_heartbeat(&s,2,owner(2,10),1,1,t+limit-1));before=s;
    assert(reist_graphical_heartbeat(&s,2,owner(2,10),1,1,t+limit)==-116);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(!(reist_graphical_expired(&s,t+limit+998)&4));
    assert(reist_graphical_expired(&s,t+limit+999)&4);
    assert(!reist_graphical_init(&s,1ULL<<32,0));before=s;
    assert(reist_graphical_begin(&s,UINT64_MAX-limit+1)==-75);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_begin(&s,UINT64_MAX-limit));
    assert(s.start_end==UINT64_MAX);
    driver_idle();client_idle();paint_reply_audit();text_line_frames();text_already_queued();puts("DESKTOP_STARTUP_OK");return 0;
}
