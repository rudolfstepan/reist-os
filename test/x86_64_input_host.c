#ifdef REIST_INPUT_SERVICE_HOST
#undef NDEBUG
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <x86os.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/input.h>
static uint64_t fake_time;
static unsigned fifo[8],head,tail,prefix_state,sleep_count,healthy_count;
static int64_t fake0(uint64_t op){if(op==REIST_X64_SYS_GETPID)return 2;assert(op==REIST_X64_SYS_MONOTONIC_MS);return (int64_t)fake_time;}
static int64_t fake1(uint64_t op,uint64_t value){assert(op==REIST_X64_SYS_SLEEP_MS);if(!value||value>100)return -22;fake_time+=value;sleep_count++;return 0;}
static void enqueue(unsigned aux,unsigned byte){assert(tail-head<8);fifo[tail++%8]=((aux?0x21:1)<<8|byte)+1;}
static int64_t fake2(uint64_t op,uint64_t number,uint64_t pointer) {
    assert(op==REIST_X64_SYS_DEVICE_CONTROL&&number==31);const reist_input_request_v1 *r=(const void*)(uintptr_t)pointer;
    assert(r->owner==(2ULL<<32|5));if(r->operation==REIST_INPUT_QUERY)return 1;
    assert(r->epoch==1&&r->deadline_ms==1000&&fake_time<1000);
    if(r->operation==REIST_INPUT_READ)return head==tail?-11:(int64_t)fifo[head++%8];
    if(r->operation==REIST_INPUT_CONTROLLER){assert(r->value==0x60||r->value==0xd4||r->value==0x20);if(r->value==0x20)enqueue(0,0x40);else prefix_state=(unsigned)r->value;return 0;}
    assert(r->operation==REIST_INPUT_DATA);
    if(prefix_state==0x60){assert(r->value==0x70||r->value==0x40);prefix_state=0;return 0;}
    unsigned auxiliary=prefix_state==0xd4;prefix_state=0;
    assert(r->value==0xff||r->value==0xf5||r->value==0xf6||r->value==0xf4);enqueue(auxiliary,0xfa);
    if(r->value==0xff){enqueue(auxiliary,0xaa);if(auxiliary)enqueue(1,0);}return 0;
}
static int64_t fake3(uint64_t op,uint64_t ep,uint64_t pointer,uint64_t timeout) {
    assert(op==REIST_X64_SYS_IPC_SEND_TIMEOUT&&ep==1&&timeout<=100&&timeout>0);
    const x86os_ipc_message_t *m=(const void*)(uintptr_t)pointer;reist_input_event_v1 e;memcpy(&e,m->payload,64);
    assert(m->version==1&&m->struct_size==140&&m->length==64&&e.type==REIST_INPUT_HEALTHY&&e.sequence==1);
    healthy_count++;return 0;
}
#define reist_x64_syscall0 fake0
#define reist_x64_syscall1 fake1
#define reist_x64_syscall2 fake2
#define reist_x64_syscall3 fake3
#define main actual_service_main
#include "arch/x86_64/user/input_service.c"
#undef main
int main(void) {
    char *args[]={"ps2","00000001","00000003","00000000","00001388","h"};
    int result=actual_service_main(6,args);
    assert(result==110&&healthy_count==1&&sleep_count==60&&fake_time==6000&&head==tail);
    puts("INPUT_SERVICE_HANG_HOST_OK");return 0;
}
#else
#undef NDEBUG
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "arch/x86_64/devices/input_core.h"
#include "userspace/drivers/ps2/native_input.h"
#include <reist/x86_64/syscall.h>
static unsigned output_bytes,output_calls,output_busy;
static uint64_t output_time;
static unsigned char output_data[256];
static int64_t client_syscall0(uint64_t op){assert(op==REIST_X64_SYS_MONOTONIC_MS);return (int64_t)output_time;}
static int64_t client_syscall1(uint64_t op,uint64_t value){assert(op==REIST_X64_SYS_SLEEP_MS&&value==10);output_time+=value;return 0;}
static int64_t client_syscall3(uint64_t op,uint64_t fd,uint64_t pointer,uint64_t bytes) {
    assert(op==REIST_X64_SYS_WRITE&&fd==1);output_calls++;
    if(bytes>64)return -22;
    if(output_busy){output_busy--;return -11;}
    assert(bytes&&output_bytes+bytes<=sizeof(output_data));memcpy(output_data+output_bytes,(const void*)(uintptr_t)pointer,(size_t)bytes);output_bytes+=(unsigned)bytes;return (int64_t)bytes;
}
#define reist_x64_syscall0 client_syscall0
#define reist_x64_syscall1 client_syscall1
#define reist_x64_syscall3 client_syscall3
#define main input_client_unexecuted_main
#include "arch/x86_64/user/input_client.c"
#undef main
#undef reist_x64_syscall0
#undef reist_x64_syscall1
#undef reist_x64_syscall3
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
/* Execute the actual root composition with a single-peer endpoint model. */
static unsigned char prepared[REIST_X64_PREPARED_V2_BYTES];
static void *session_prepared=prepared;
const unsigned char reist_native_input_image[]={0};
const size_t reist_native_input_image_bytes=1;
static unsigned created,grants[4],sends,closes,cancels,reaps,binds,fences,received,scenario;
static uint64_t root_now,root_child=3ULL<<32|4,root_driver=2ULL<<32|5;
static unsigned order[32],order_count;
static void session_zero(void *p,size_t n){memset(p,0,n);}
static void session_bytes(void *p,const void *q,size_t n){memcpy(p,q,n);}
static uint64_t session_now(void){return root_now;}
static _Noreturn void session_stop(int error){(void)error;assert(!"unexpected uncertain root cleanup");__builtin_trap();}
static void session_hex(char *s,uint32_t v){snprintf(s,9,"%08x",v);}
static int64_t service_task(void *p,unsigned op,uint64_t task,unsigned timeout) {
    (void)p;assert(task==root_child||task==root_driver);assert(order_count<32);order[order_count++]=op;
    if(op==3){assert(!timeout);cancels++;return 0;}
    assert(op==2&&timeout>0&&timeout<=1000);reaps++;return task==root_child?82:0;
}
static int64_t root_call(unsigned number,uintptr_t a,uintptr_t b,uintptr_t c) {
    if(number==REIST_X64_SYS_IPC_CREATE){assert(created<2);*(uint32_t*)a=++created;return 0;}
    if(number==REIST_X64_SYS_IPC_CLOSE){assert(a>=1&&a<=2);closes++;order[order_count++]=52;return 0;}
    if(number==REIST_X64_SYS_IPC_DELEGATE){assert(a>=1&&a<=2);if(grants[a])return -13;grants[a]=(unsigned)b;assert((a==1&&b==3&&c==2)||(a==2&&b==2&&c==1));return 0;}
    if(number==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT) {
        assert(a==2&&c>0&&c<=100);x86os_ipc_message_t *m=(void*)b;memset(m,0,sizeof(*m));m->version=1;m->struct_size=140;m->length=64;
        if(received==2)return -32;
        reist_input_event_v1 e={1,64,received?REIST_INPUT_KEY:REIST_INPUT_HEALTHY,0,root_driver,root_child,1,received+1,received?0x1e:0,0,0,0};
        if(scenario==1)e.owner+=1ULL<<32;
        if(scenario==2)e.epoch++;
        memcpy(m->payload,&e,64);received++;return 0;
    }
    if(number==REIST_X64_SYS_IPC_SEND_TIMEOUT){assert(a==1&&c>0&&c<=100);sends++;return 0;}
    if(number==REIST_X64_SYS_DEVICE_CONTROL) {
        assert(a==31&&!c);const reist_input_request_v1 *q=(void*)b;
        assert(q->owner==root_driver&&q->version==1&&q->size==64);
        if(q->operation==REIST_INPUT_BIND){binds++;return 1;}
        assert(q->operation==REIST_INPUT_FENCE&&q->epoch==1);fences++;order[order_count++]=31;return 0;
    }
    assert(!"unexpected root syscall");return -5;
}
static int64_t root_import(const void *p,const reist_task_profile_v1_t *profile,unsigned budget,unsigned window,const reist_task_startup_v1_t *startup) {
    (void)p;assert(budget==32&&window==1000&&startup->argc==6);
    assert(profile->masks[0]==((1ULL<<9)|(1ULL<<22)|(1ULL<<41)|(1ULL<<42)|(1ULL<<53)));
    assert(profile->masks[1]==1ULL<<49&&profile->masks[2]==0);return (int64_t)root_driver;
}
#define SESSION_S1(n,a) root_call(REIST_X64_SYS_##n,(uintptr_t)(a),0,0)
#define SESSION_S3(n,a,b,c) root_call(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define reist_x64_syscall2(n,a,b) root_call(n,a,b,0)
#define reist_x64_image_prepare_v2(p,b,n) ((void)(p),(void)(b),(void)(n),0)
#define reist_x64_task_import_periodic root_import
#include "userspace/sdk/lib/x86_64/shell_input.inc"
#undef reist_x64_syscall2
#undef reist_x64_image_prepare_v2
#undef reist_x64_task_import_periodic
static const uint64_t root=1ULL<<32,driver=2ULL<<32|5;
static reist_input_request_v1 req(unsigned op) {
    reist_input_request_v1 r={1,64,op,0,driver,1,100,0,{0,0}};return r;
}
static void core(void) {
    native_input_state s,before;assert(!native_input_core_init64(&s));
    reist_input_request_v1 r=req(1);r.epoch=r.deadline_ms=0;
    assert(native_input_core_apply64(&s,&r,root,0,3)==1);
    assert(s.owner==driver && !s.fenced && s.epoch==1);
    r=req(3);
    for(unsigned n=0;n<64;n++)assert(!native_input_core_apply64(&s,&r,driver,0,0));
    assert(native_input_core_apply64(&s,&r,driver,0,0)==-122 && s.fenced);
    assert(native_input_core_apply64(&s,&r,driver,100,0)==-13);
    assert(!native_input_core_fence64(&s,driver));
    r=req(1);r.epoch=r.deadline_ms=0;
    assert(native_input_core_apply64(&s,&r,root,100,2)==-13);
    assert(native_input_core_apply64(&s,&r,root,100,3)==2);
    r=req(4);r.epoch=2;r.deadline_ms=200;
    for(unsigned value=0;value<256;value++) {
        r.value=value;before=s;
        int64_t rc=native_input_core_apply64(&s,&r,driver,100,0);
        int allowed=value==0x20||value==0x60||value==0xa7||value==0xa8||value==0xad||value==0xae||value==0xd4;
        assert(rc==(allowed?0:-22));if(!allowed)assert(!memcmp(&s,&before,sizeof s));
    }
    r=req(5);r.epoch=2;r.deadline_ms=200;
    for(unsigned prefix=0;prefix<3;prefix++) {
        if(prefix)assert(!native_input_core_written64(&s,4,prefix==1?0x60:0xd4));
        for(unsigned v=0;v<256;v++) {
            r.value=v;before=s;int allowed=prefix==1?(v==0x40||v==0x70):(v==0xf4||v==0xf5||v==0xf6||v==0xff);
            int64_t rc=native_input_core_apply64(&s,&r,driver,100,0);
            assert(rc==(allowed?0:-22));if(!allowed)assert(!memcmp(&s,&before,sizeof s));
        }
        assert(!native_input_core_written64(&s,5,prefix==1?0x40:0xf4));
    }
    r=req(3);r.epoch=2;r.deadline_ms=200;
    before=s;r.flags=1;assert(native_input_core_apply64(&s,&r,driver,100,0)==-22);assert(!memcmp(&s,&before,sizeof s));
    r.flags=0;r.epoch=1;assert(native_input_core_apply64(&s,&r,driver,100,0)==-116);
    r.epoch=2;assert(native_input_core_apply64(&s,&r,driver+1,100,0)==-13);
    r.deadline_ms=100;assert(native_input_core_apply64(&s,&r,driver,100,0)==-110);
    r.deadline_ms=1101;assert(native_input_core_apply64(&s,&r,driver,100,0)==-22);
    for(unsigned n=0;n<16;n++){native_input_state bad=s;((uint64_t*)&bad)[n]^=1;assert(native_input_core_admit64(&bad)==-84);}
    assert(!native_input_core_fence64(&s,root));assert(s.fenced && !s.prefix);
}
static void decode(void) {
    reist_ps2_decoder s;reist_input_event_v1 e;reist_ps2_clear(&s);
    assert(reist_ps2_decode(&s,1,0x2a,1,&e)==1 && (e.flags&4));
    assert(reist_ps2_decode(&s,1,0x1e,2,&e)==1 && e.code==0x1e && (e.flags&4));
    assert(reist_ps2_decode(&s,1,0xaa,3,&e)==1 && !(e.flags&4) && (e.flags&1));
    assert(!reist_ps2_decode(&s,0x21,0x29,4,&e));
    assert(!reist_ps2_decode(&s,0x21,12,5,&e));
    assert(reist_ps2_decode(&s,0x21,250,6,&e)==1 && e.dx==12 && e.dy==-6 && e.buttons==1);
    assert(!reist_ps2_decode(&s,1,0xe0,7,&e));
    assert(reist_ps2_decode(&s,1,0x4b,8,&e)==1 && e.code==0x4b && (e.flags&2));
    assert(!reist_ps2_decode(&s,1,0xe0,9,&e));
    assert(reist_ps2_decode(&s,1,0x1e,109,&e)==-110);
    assert(!s.modifiers && !s.extended);
    assert(reist_ps2_decode(&s,0xc1,0x1e,110,&e)==-71);
    assert(reist_ps2_decode(&s,0x21,0xc8,111,&e)==-75);
    assert(reist_ps2_decode(&s,0x21,0,112,&e)==-71);
    for(unsigned n=0;n<6;n++)assert(!reist_ps2_decode(&s,1,((uint8_t[]){0xe1,0x1d,0x45,0xe1,0x9d,0xc5})[n],120+n,&e));
    assert(reist_ps2_decode(&s,1,0x1e,119,&e)==-84);
}
typedef struct { unsigned op,value;int result; } step;
#define C(v) {REIST_INPUT_CONTROLLER,v,0}
#define D(v) {REIST_INPUT_DATA,v,0}
#define R(s,v) {REIST_INPUT_READ,0,((s)<<8|(v))+1}
static const step golden[]={
    C(0x60),D(0x70),{REIST_INPUT_READ,0,-11},C(0x60),D(0x40),C(0x20),R(1,0x40),
    D(0xff),R(1,0xfa),R(1,0xaa),D(0xf5),R(1,0xfa),D(0xf6),R(1,0xfa),
    C(0xd4),D(0xff),R(0x21,0xfa),R(0x21,0xaa),R(0x21,0),
    C(0xd4),D(0xf5),R(0x21,0xfa),C(0xd4),D(0xf6),R(0x21,0xfa),
    D(0xf4),R(1,0xfa),C(0xd4),D(0xf4),R(0x21,0xfa)};
typedef struct { uint64_t now;unsigned at,calls,sleeps,mode,busy; } transcript;
static uint64_t stamp(void *p){return ((transcript*)p)->now;}
static int pause_ms(void *p,unsigned ms){transcript *s=p;assert(ms==10);s->now+=ms;s->sleeps++;return 0;}
static int64_t io(void *p,unsigned op,unsigned value,uint64_t end) {
    transcript *s=p;assert(end==1000&&s->now<end);s->calls++;
    assert(s->at<sizeof(golden)/sizeof(*golden));const step *next=golden+s->at;
    assert(next->op==op&&next->value==value);
    if(s->mode==1&&op!=REIST_INPUT_READ&&!s->busy){s->busy=1;return -11;}
    s->busy=0;
    if(s->at==2&&s->mode==3)return 0x011f+1; /* old FIFO never empties */
    if(s->at==8&&s->mode==4)return -11; /* missing keyboard ACK */
    s->at++;
    if(s->at==9&&s->mode==2)return 0x01fe + 1; /* RESEND is not a successful ACK */
    return next->result;
}
static void controller(void) {
    for(unsigned mode=0;mode<5;mode++) {
        transcript s={0};s.mode=mode;reist_ps2_transport t={&s,stamp,io,pause_ms};
        int r=reist_ps2_initialize(&t,1000);
        if(mode<2){assert(!r&&s.at==sizeof(golden)/sizeof(*golden));assert(mode==0?s.sleeps==0:s.sleeps==17);}
        if(mode==2)assert(r==-71&&s.at==9);
        if(mode==3)assert(r==-75&&s.at==2&&s.sleeps==64);
        if(mode==4)assert(r==-110&&s.at==8&&s.now==1000&&s.sleeps==100);
        assert(s.calls<=108);
    }
    transcript s={0};reist_ps2_transport t={&s,stamp,io,pause_ms};
    assert(reist_ps2_initialize(&t,0)==-22&&s.calls==0);
    assert(reist_ps2_initialize(&t,1001)==-22&&s.calls==0);
}
static void consumer(void) {
    reist_input_event_v1 e={1,64,REIST_INPUT_HEALTHY,0,driver,3ULL<<32|4,1,1,0,0,0,0};
    uint64_t target=e.target;assert(reist_input_event_valid(&e,0,target,0,1));
    assert(!reist_input_event_valid(0,0,target,0,1));e.sequence=0;assert(!reist_input_event_valid(&e,0,target,0,0));e.sequence=1;
    for(unsigned n=0;n<4;n++){reist_input_event_v1 bad=e;((uint32_t*)&bad)[n]^=64;assert(!reist_input_event_valid(&bad,0,target,0,1));}
    e.type=REIST_INPUT_KEY;e.code=0x1e;e.sequence=2;
    assert(reist_input_event_valid(&e,driver,target,1,2));
    assert(!reist_input_event_valid(&e,driver+(1ULL<<32),target,1,2));
    assert(!reist_input_event_valid(&e,driver,target+(1ULL<<32),1,2));
    assert(!reist_input_event_valid(&e,driver,target,2,2));assert(!reist_input_event_valid(&e,driver,target,1,3));
    e.flags=64;assert(!reist_input_event_valid(&e,driver,target,1,2));e.flags=0;
    e.type=REIST_INPUT_POINTER;e.code=0;e.dx=-256;e.dy=255;e.buttons=7;
    assert(reist_input_event_valid(&e,driver,target,1,2));e.dx=-257;assert(!reist_input_event_valid(&e,driver,target,1,2));
    e.dx=0;e.buttons=8;assert(!reist_input_event_valid(&e,driver,target,1,2));e.buttons=0;
    e.type=REIST_INPUT_ERROR;e.code=-122;e.dy=0;assert(reist_input_event_valid(&e,driver,target,1,2));
    e.sequence=33;assert(!reist_input_event_valid(&e,driver,target,1,33));
}
static void composition(void) {
    for(scenario=0;scenario<3;scenario++) {
        created=sends=closes=cancels=reaps=binds=fences=received=order_count=0;memset(grants,0,sizeof(grants));root_now=100;
        reist_task_startup_v1_t startup;const char *args[]={"boot.prg"};
        reist_task_profile_v1_t profile={1,40,{UINT64_MAX,1ULL<<63,0},0};
        assert(!session_input_arguments(1,args,&startup,&profile));assert(startup.argc==5&&created==2);
        assert(profile.masks[0]==(UINT64_MAX^((1ULL<<49)|(1ULL<<52)|(1ULL<<55)))&&profile.masks[1]==1ULL<<63);
        assert(!session_input_start(root_child)&&binds==1&&grants[1]==3&&grants[2]==2);
        assert(session_input_wait(root_child)==82);assert(sends==(scenario?0:2));
        if(scenario)assert(fences==1&&closes==2&&order[0]==31&&order[1]==3&&order[2]==2&&order[3]==52&&order[4]==52);
        session_input_retire();assert(fences==1&&cancels==1&&closes==2&&reaps==2);
        session_input_retire();assert(fences==1&&cancels==1&&closes==2&&reaps==2);
        assert(!session_input_driver&&!session_input_epoch&&!session_input_end&&!session_input_endpoint&&!session_input_ingress);
    }
}
static void console_record(void) {
    reist_input_event_v1 e={1,64,REIST_INPUT_HEALTHY,0,driver,3ULL<<32|4,1,1,0,0,0,0};
    output_bytes=output_calls=output_busy=0;output_time=0;
    assert(record(&e));assert(output_bytes==144&&output_calls==3&&output_time==0);
    unsigned char expected[144];memcpy(expected,output_data,144);
    output_bytes=output_calls=0;output_busy=1;
    assert(record(&e));assert(output_bytes==144&&output_calls==4&&output_time==10&&!memcmp(expected,output_data,144));
    output_bytes=output_calls=0;output_busy=100;output_time=0;
    assert(!record(&e)&&output_bytes==0&&output_calls==20&&output_time==200);
}
int main(void){core();decode();controller();consumer();composition();console_record();puts("INPUT_HOST_OK");return 0;}

#endif
