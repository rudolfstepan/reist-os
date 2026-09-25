#ifdef REIST_TEST_LAZY_FONT
#include <assert.h>
#include <string.h>
#define main desktop_unused_entry
#include "../userspace/gui/compositor/desktop.c"
#undef main
void *reist_desktop_workspaces[REIST_DESKTOP_WORKSPACE_SLOTS];
static uint64_t placeholders[2];
static desktop_font_file_native_type font_memory;
static desktop_startup_workspace_native_type mapping_memory;
static unsigned font_case,font_allocated,font_freed,font_stat;
static unsigned acceleration_attempts,acceleration_sleeps;
int x86os_service_connect(uint32_t service,x86os_ipc_handle_t *out) {
    assert(service==X86OS_SERVICE_DISPLAY_DRIVER && !*out);acceleration_attempts++;return -95;
}
int x86os_sleep_ms(uint32_t ms){assert(ms==50);acceleration_sleeps++;return 0;}
void x86os_puts(const char *s){assert(s);}
void x86os_putchar(char c){(void)c;}
void x86os_print_number(int n){(void)n;}
int x86os_monotonic_ms(uint64_t *out){(void)out;assert(0);return -5;}
int x86os_ipc_release(x86os_ipc_handle_t ep){(void)ep;assert(0);return -5;}
int x86os_ipc_send_timeout(x86os_ipc_handle_t ep,const x86os_ipc_message_t *m,uint32_t ms){
    (void)ep;(void)m;(void)ms;assert(0);return -5;
}
int x86os_ipc_receive_timeout(x86os_ipc_handle_t ep,x86os_ipc_message_t *m,uint32_t ms){
    (void)ep;(void)m;(void)ms;assert(0);return -5;
}
int x86os_stat(const char *path,x86os_file_info_t *out) {
    assert(!strcmp(path,DESKTOP_FONT_PATH));font_stat++;
    if(font_case==0)return -13;
    memset(out,0,sizeof(*out));out->type=font_case==1?X86OS_DIRECTORY:X86OS_FILE;
    out->size=font_case==2?DESKTOP_FONT_FILE_CAPACITY+1:4096;
    return 0;
}
void *x86os_malloc(size_t size) {
    font_allocated++;
    assert(font_allocated<=2);
    assert(size==(font_allocated==1?sizeof(font_memory):sizeof(mapping_memory)));
    if((font_case==3 && font_allocated==1) || (font_case==4 && font_allocated==2))return 0;
    return font_allocated==1?(void *)&font_memory:(void *)&mapping_memory;
}
void x86os_free(void *p) {
    assert(p==&font_memory || p==&mapping_memory || p==placeholders || p==placeholders+1);
    font_freed++;
}
int main(void) {
    assert(desktop_svga2d_activate_bounded()==-95);
    assert(acceleration_attempts==1 && !acceleration_sleeps);
    const int expected[]={-13,-84,-84,-12,-12,0};
    for(font_case=0;font_case<6;font_case++) {
        desktop_font_storage_ready=font_allocated=font_freed=font_stat=0;
        reist_desktop_workspaces[0]=placeholders;
        reist_desktop_workspaces[1]=placeholders+1;
        assert(desktop_font_storage_prepare()==expected[font_case]);
        assert(font_stat==1);
        if(font_case<5) {
            assert(!desktop_font_storage_ready);
            assert(reist_desktop_workspaces[0]==placeholders && reist_desktop_workspaces[1]==placeholders+1);
            assert(font_allocated==(font_case<3?0:font_case==3?1:2));
            assert(font_freed==(font_case==4));
        } else {
            assert(desktop_font_storage_ready && font_allocated==2 && font_freed==2);
            assert(reist_desktop_workspaces[0]==&font_memory && reist_desktop_workspaces[1]==&mapping_memory);
            assert(!desktop_font_storage_prepare() && font_stat==1 && font_allocated==2);
            x86os_free(reist_desktop_workspaces[1]);x86os_free(reist_desktop_workspaces[0]);
            assert(font_freed==4);
        }
    }
    return 0;
}
#else
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/desktop_platform.h>
#include <reist/x86_64/desktop_display.h>
#include <reist/x86_64/syscall.h>
#include <reist/vfs_file_client.h>
#include <reist/vfs_read_client.h>
#include "../userspace/gui/compositor/desktop_surface_runtime.h"
#include "../userspace/gui/compositor/desktop_wm.h"
static reist_desktop_broker broker;
static reist_desktop_service_client client;
static reist_desktop_service_manifest manifest[3];
static uint64_t ms=100;
static uint64_t wire_time=100;
static unsigned reads,calls,failures,wait_status;
static unsigned console_capture,console_partial,console_bytes;
static char console_output[512];
static unsigned rejected;
static uint32_t startup_pixels[2][1024*768];
static unsigned char startup_font[4096];
static unsigned startup_case,allocations,frees,entered,commits;
static unsigned freed[2];
static uint64_t display_epoch=100;
static unsigned frontend_test,greetings,delegations,app_closes,ready_reports;
static reist_gui_surface_message_t surface_reply[2];
static reist_desktop_service_frame rejection;
static int clock_read(void *p,uint64_t *out){(void)p;*out=ms;return 0;}
static int abort_all(void *p){(void)p;return 0;}
static int step(void *p,const reist_desktop_service_frame *q,const reist_desktop_service_manifest *m,reist_desktop_service_frame *r) {
    (void)p;(void)m;
    if(q->operation==REIST_DESKTOP_READ) {
        reads++;r->count=q->count;
        for(unsigned n=0;n<q->count;n++)r->payload.bytes[n]=(unsigned char)(q->offset+n);
    } else if(q->operation==REIST_DESKTOP_LAUNCH)r->object=UINT64_C(20)<<32|6;
    else if(q->operation==REIST_DESKTOP_WAIT)r->offset=wait_status;
    return 0;
}
static int send_frame(void *p,const reist_desktop_service_frame *q) {
    (void)p;int r=reist_desktop_broker_submit(&broker,q,ms);
    if(r){assert(!rejected);assert(!reist_desktop_service_reject(q,r,&rejection));rejected=1;}
    return 0;
}
static int receive_frame(void *p,reist_desktop_service_frame *r) {
    (void)p;if(rejected){*r=rejection;rejected=0;return 0;}
    int n=reist_desktop_broker_step(&broker,r,ms);return n==2?0:n>=0?-11:n;
}
static int wait_frame(void *p,unsigned delay){(void)p;ms+=delay;return 0;}
static void failed(void *p,int error){(void)p;(void)error;failures++;}
static int64_t call(void *p,unsigned op,uint64_t a,uint64_t b,uint64_t c) {
    (void)p;(void)b;(void)c;calls++;
    if(op==REIST_X64_SYS_GETPID)return 10;
    if(op==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)ms;
    if(op==REIST_X64_SYS_SLEEP_MS){assert(a<=100);ms+=a;if(frontend_test)wire_time=ms;return 0;}
    if(op==REIST_X64_SYS_WRITE){
        unsigned count=(unsigned)c;if(console_partial && count>7)count=7;
        if(console_capture){assert(console_bytes+count<=sizeof(console_output));
            memcpy(console_output+console_bytes,(const void *)(uintptr_t)b,count);console_bytes+=count;}
        return count;
    }
    if(frontend_test && op==REIST_X64_SYS_YIELD)return 0;
    if(frontend_test && op==REIST_X64_SYS_IPC_DELEGATE) {
        assert((a==3 && b==100) || (a==4 && b==101));assert(c==3);
        /* The completed supervisor handshake already delegated these peers.
         * ipc_delegate rejects a second delegation with EACCES. */
        delegations++;return -13;
    }
    if(frontend_test && op==REIST_X64_SYS_IPC_CLOSE) {
        assert(a==3 || a==4 || a==5);app_closes++;return 0;
    }
    if(frontend_test && op==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        assert(a==3 || a==4);
        const x86os_ipc_message_t *m=(void *)(uintptr_t)b;
        assert(m->version==1 && m->struct_size==140);
        if(m->length==64) {
            reist_graphical_control hello;memcpy(&hello,m->payload,64);
            assert(c==100 && hello.type==REIST_GRAPHICAL_HELLO && hello.role==a-1);
            assert(hello.owner==broker.children[a-3] && hello.endpoint==a && hello.epoch==broker.config.epoch);
            greetings++;
        } else {
            assert(m->length==124 && !c);memcpy(&surface_reply[a-3],m->payload,124);
        }
        return 0;
    }
    if(op==REIST_X64_SYS_MALLOC) {
        assert(a==800*600*4 && allocations<2);allocations++;
        if(startup_case==allocations)return -12;
        return (intptr_t)startup_pixels[allocations-1];
    }
    if(op==REIST_X64_SYS_FREE) {
        assert(frees<2);
        assert(a==(uintptr_t)startup_pixels[0] || a==(uintptr_t)startup_pixels[1]);
        freed[frees++]=a==(uintptr_t)startup_pixels[0]?0:1;
        return startup_case==6?-5:0;
    }
    if(op==REIST_X64_SYS_DEVICE_CONTROL) {
        assert(a==30 && !c);
        reist_display_request_v1 *q=(void *)(uintptr_t)b;
        assert(q->owner==(10ULL<<32|4));
        if(q->operation==REIST_DISPLAY_QUERY) {
            assert(q->version==1 && q->size==64 && !q->epoch);
            return (int64_t)display_epoch;
        }
        assert(q->epoch==display_epoch);
        if(q->operation==REIST_DISPLAY_INFO) {
            reist_display_info_v2 *i=(void *)q;
            assert(i->version==2 && i->size==64 && !i->width && !i->height && !i->pitch);
            i->width=startup_case==3?UINT32_MAX:800;i->height=600;i->pitch=3200;
            i->bits_per_pixel=32;i->red_field_position=16;i->green_field_position=8;
            return 0;
        }
        assert(q->operation==REIST_DISPLAY_COMMIT && q->width<=64 && q->height<=64);
        assert(q->deadline_ms==ms+100);commits++;return startup_case==7?-19:0;
    }
    return -38;
}
static int pump(void *p){(void)p;return 0;}
static int key(void *p){(void)p;return -11;}
static int mouse(void *p,x86os_mouse_event_t *out){(void)p;(void)out;return -11;}
static int report(void *p,unsigned op,unsigned value){
    (void)p;
    if(frontend_test && op==X86OS_REIST_REPORT_SERVICE_READY){assert(value==1);ready_reports++;}
    return 0;
}
static int frontend_commit(void *p,const reist_display_request_v1 *q) {
    return (int)call(p,REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)q,0);
}
static int startup_entry(int argc,char **argv) {
    assert(argc==1 && !strcmp(argv[0],"/desktop.prg"));entered++;
    assert(!x86os_display_activate());
    x86os_display_info_t info;
    assert(!x86os_display_info(&info) && info.width==800 && info.height==600);
    assert(!x86os_fill_rect(0,0,800,600,0x123456));
    uint32_t serial=0;assert(!x86os_display_frame_begin(&serial));
    assert(!reist_desktop_platform_pump() && !commits); /* No half-frame output. */
    assert(!x86os_display_frame_cancel(serial));
    if(startup_case==7) {
        assert(x86os_sleep_ms(10)==-19 && commits==1);
        assert(reist_desktop_platform_pump()==-116);return -19;
    }
    for(unsigned n=0;n<30 && reist_desktop_display_idle();n++)assert(!x86os_sleep_ms(10));
    assert(!reist_desktop_display_idle() && commits==130);
    x86os_process_identity_t identity;
    int pid=(int)(30+startup_case*2);
    assert(!x86os_process_identity_of(pid,&identity) && identity.pid==pid);
    return startup_case==5?-110:0;
}
static void input_tests(void) {
    reist_desktop_input_state input={0};
    uint64_t owner=10ULL<<32|4,driver=11ULL<<32|5;
    assert(!reist_desktop_input_bind(&input,owner,driver,7,100));
    reist_input_event_v1 e={2,64,REIST_INPUT_HEALTHY,0,driver,owner,7,1,0,0,0,0};
    assert(!reist_desktop_input_push(&input,&e,100));
    e.sequence++;e.type=REIST_INPUT_KEY;e.code=0x1e;e.flags=4;
    assert(!reist_desktop_input_push(&input,&e,100));
    reist_desktop_input_state saved_input=input;
    assert(reist_desktop_input_peek_key(&input)=='A');
    assert(!memcmp(&input,&saved_input,sizeof(input)));
    assert(reist_desktop_input_peek_key(&input)=='A');
    assert(reist_desktop_input_key(&input)=='A');
    assert(reist_desktop_input_key(&input)==-11);
    e.sequence++;e.flags=1;assert(!reist_desktop_input_push(&input,&e,100));
    assert(reist_desktop_input_key(&input)==-11);
    e.sequence++;e.flags=2;e.code=0x48;assert(!reist_desktop_input_push(&input,&e,100));
    assert(reist_desktop_input_key(&input)==27);assert(reist_desktop_input_key(&input)=='[');
    assert(reist_desktop_input_key(&input)=='A');
    e.sequence++;e.type=REIST_INPUT_POINTER;e.code=0;e.flags=0;e.dx=12;e.dy=-6;e.buttons=1;
    assert(!reist_desktop_input_push(&input,&e,100));x86os_mouse_event_t mouse={0};
    assert(!reist_desktop_input_mouse(&input,&mouse));
    assert(mouse.version==1 && mouse.struct_size==sizeof(mouse) && mouse.delta_x==12 &&
        mouse.delta_y==6 && mouse.buttons==1 && mouse.generation==11 && !mouse.reserved);
    x86os_mouse_event_t unchanged=mouse;assert(reist_desktop_input_mouse(&input,&mouse)==-11);
    assert(!memcmp(&unchanged,&mouse,sizeof(mouse)));
    e.sequence++;e.epoch++;
    assert(reist_desktop_input_push(&input,&e,100)==-116);
    assert(reist_desktop_input_mouse(&input,&mouse)==-116);
    assert(!memcmp(&unchanged,&mouse,sizeof(mouse)));
    memset(&input,0,sizeof(input));assert(!reist_desktop_input_bind(&input,owner,driver,7,100));
    e=(reist_input_event_v1){2,64,REIST_INPUT_HEALTHY,0,driver,owner,7,1,0,0,0,0};
    assert(!reist_desktop_input_push(&input,&e,100));
    e.type=REIST_INPUT_POINTER;
    for(unsigned n=0;n<32;n++){e.sequence++;assert(!reist_desktop_input_push(&input,&e,100));}
    e.sequence++;assert(reist_desktop_input_push(&input,&e,100)==-122);
    memset(&input,0,sizeof(input));assert(!reist_desktop_input_bind(&input,owner,driver,7,100));
    e=(reist_input_event_v1){2,64,REIST_INPUT_HEALTHY,0,driver,owner,7,1,0,0,0,0};
    for(unsigned n=1;n<=128;n++){e.sequence=n;assert(!reist_desktop_input_push(&input,&e,100));}
    reist_desktop_input_state saved=input;e.sequence=129;
    assert(reist_desktop_input_push(&input,&e,100)==-122);
    input=saved;assert(!reist_desktop_input_push(&input,&e,1100));
    e.sequence++;assert(reist_desktop_input_push(&input,&e,1099)==-84);
}
static int input_order_tests(void) {
    unsigned failures=0;
    for(unsigned mouse_first=0;mouse_first<2;mouse_first++) {
        reist_desktop_input_state input={0};
        uint64_t owner=10ULL<<32|4,driver=11ULL<<32|5;
        assert(!reist_desktop_input_bind(&input,owner,driver,7,100));
        reist_input_event_v1 e={2,64,REIST_INPUT_HEALTHY,0,driver,owner,7,1,0,0,0,0};
        assert(!reist_desktop_input_push(&input,&e,100));
        for(unsigned n=0;n<2;n++) {
            e.sequence++;
            unsigned mouse=n==0?mouse_first:!mouse_first;
            e.type=mouse?REIST_INPUT_POINTER:REIST_INPUT_KEY;e.code=mouse?0:0x1e;
            e.buttons=mouse?1:0;
            assert(!reist_desktop_input_push(&input,&e,100));
        }
        x86os_mouse_event_t mouse={0};
        if(mouse_first) {
            assert(reist_desktop_input_peek_key(&input)==-11);
            if(reist_desktop_input_key(&input)!=-11) {
                fprintf(stderr,"key overtook earlier focus click\n");failures++;continue;
            }
            assert(!reist_desktop_input_mouse(&input,&mouse));
            assert(reist_desktop_input_key(&input)=='a');
        } else {
            if(reist_desktop_input_mouse(&input,&mouse)!=-11) {
                fprintf(stderr,"mouse overtook earlier keyboard event\n");failures++;continue;
            }
            assert(reist_desktop_input_key(&input)=='a');
            assert(!reist_desktop_input_mouse(&input,&mouse));
        }
    }
    /* Exercise both ring wraps and keep each ANSI CSI event indivisible. */
    reist_desktop_input_state input={0};
    uint64_t owner=10ULL<<32|4,driver=11ULL<<32|5;
    assert(!reist_desktop_input_bind(&input,owner,driver,7,100));
    reist_input_event_v1 e={2,64,REIST_INPUT_HEALTHY,0,driver,owner,7,1,0,0,0,0};
    assert(!reist_desktop_input_push(&input,&e,100));
    for(unsigned n=0;n<40;n++) {
        uint64_t now=100+n*1000;
        e.sequence++;e.type=REIST_INPUT_KEY;e.flags=2;e.code=0x48;
        assert(!reist_desktop_input_push(&input,&e,now));
        e.sequence++;e.type=REIST_INPUT_POINTER;e.flags=e.code=0;
        assert(!reist_desktop_input_push(&input,&e,now));
        x86os_mouse_event_t mouse={0};
        const int csi[]={27,'[','A'};
        for(unsigned k=0;k<3;k++) {
            assert(reist_desktop_input_mouse(&input,&mouse)==-11);
            assert(reist_desktop_input_key(&input)==csi[k]);
        }
        assert(!reist_desktop_input_mouse(&input,&mouse));
        assert(!input.mouse_count && !input.key_count);
        for(unsigned k=0;k<32;k++)assert(!input.mouse_sequence[k]);
        for(unsigned k=0;k<64;k++)assert(!input.key_sequence[k]);
    }
    /* A corrupted cross-queue head fences before publishing output. */
    e.sequence++;e.type=REIST_INPUT_POINTER;
    assert(!reist_desktop_input_push(&input,&e,40100));
    input.mouse_sequence[input.mouse_head]=0;
    x86os_mouse_event_t mouse={0},unchanged=mouse;
    assert(reist_desktop_input_mouse(&input,&mouse)==-84 && input.phase==2);
    assert(!memcmp(&mouse,&unchanged,sizeof(mouse)));
    for(unsigned k=0;k<32;k++)assert(!input.mouse_sequence[k]);
    for(unsigned k=0;k<64;k++)assert(!input.key_sequence[k]);
    return failures!=0;
}
static x86os_ipc_bulk_message_t wire[4][16];
static unsigned wire_head[4],wire_count[4],wire_reads,wire_sends;
static unsigned recovery_creates,recovery_delegates,recovery_root_sends,recovery_app_sends;
static int64_t recovery_call(void *unused,unsigned op,uint64_t a,uint64_t b,uint64_t c) {
    (void)unused;
    if(op==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)wire_time;
    if(op==REIST_X64_SYS_IPC_CREATE){assert(!recovery_creates++);*(uint32_t *)(uintptr_t)a=5;return 0;}
    if(op==REIST_X64_SYS_IPC_DELEGATE){assert(a==5 && b==102 && c==3 && !recovery_delegates++);return 0;}
    assert(op==REIST_X64_SYS_IPC_SEND_TIMEOUT && !c);
    const x86os_ipc_message_t *m=(void *)(uintptr_t)b;reist_graphical_control q;
    assert(m->version==1 && m->struct_size==140 && m->length==64);memcpy(&q,m->payload,64);
    assert(q.role==2 && q.sequence==1 && q.endpoint==5 && !q.flags && !q.value && !q.reserved);
    if(a==1){recovery_root_sends++;return recovery_root_sends==1?-11:0;}
    assert(a==5 && q.type==REIST_GRAPHICAL_HELLO && q.owner==(102ULL<<32|6));
    recovery_app_sends++;return recovery_app_sends==1?-11:0;
}
static int64_t wire_call(void *context,unsigned op,uint64_t a,uint64_t b,uint64_t c) {
    (void)context;
    if(op==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)wire_time;
    assert(a>=1 && a<=4 && !c);
    x86os_ipc_bulk_message_t *m=(void *)(uintptr_t)b;
    if(op==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        assert(a==1 && m->version==2 && m->struct_size==2060 && m->length==2048);
        wire_sends++;return 0;
    }
    assert(op==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT);
    assert(m->version==(a==1?2U:1U) && m->struct_size==(a==1?2060U:140U));
    wire_reads++;
    unsigned slot=(unsigned)a-1;
    if(!wire_count[slot])return -11;
    *m=wire[slot][wire_head[slot]++%16];wire_count[slot]--;return 0;
}
static void wire_push(unsigned endpoint,const void *payload,unsigned bytes) {
    unsigned slot=endpoint-1;assert(slot<4 && wire_count[slot]<16);
    x86os_ipc_bulk_message_t *m=&wire[slot][(wire_head[slot]+wire_count[slot]++)%16];
    memset(m,0,sizeof(*m));m->version=bytes>128?2:1;m->struct_size=bytes>128?2060:140;
    m->length=bytes;memcpy(m->payload,payload,bytes);
}
static void channel_tests(void) {
    reist_desktop_input_state input={0};reist_desktop_channels s={0};
    uint64_t owner=10ULL<<32|4,driver=11ULL<<32|5;
    assert(!reist_desktop_input_bind(&input,owner,driver,7,100));
    reist_desktop_channels_config cfg={0,wire_call,1ULL<<32,owner,9,
        {12ULL<<32|6,13ULL<<32|7},1,2,{3,4},&input,0};
    assert(!reist_desktop_channels_init(&s,&cfg,100));
    assert(reist_desktop_channels_init(&s,&cfg,100)==-16);
    reist_graphical_control stop={1,64,REIST_GRAPHICAL_STOP,0,9,2,cfg.root,0,0,0,0},control;
    reist_desktop_service_frame reply={0},out;
    reply.version=1;reply.size=2048;reply.root=cfg.root;reply.desktop=owner;reply.epoch=9;
    reply.deadline_ms=500;
    wire_push(1,&stop,sizeof(stop));wire_push(1,&reply,sizeof(reply));
    assert(!reist_desktop_channels_receive(&s,&out) && !memcmp(&reply,&out,sizeof(out)));
    assert(!reist_desktop_channels_control(&s,&control) && !memcmp(&stop,&control,sizeof(stop)));
    assert(!reist_desktop_channels_send(&s,&reply) && wire_sends==1);
    reply.deadline_ms=100;assert(reist_desktop_channels_send(&s,&reply)==-110 && wire_sends==1);
    memset(&out,0x5a,sizeof(out));reist_desktop_service_frame unchanged=out;
    assert(reist_desktop_channels_receive(&s,&out)==-11 && !memcmp(&out,&unchanged,sizeof(out)));
    reist_input_event_v1 e={2,64,REIST_INPUT_HEALTHY,0,driver,owner,7,1,0,0,0,0};
    wire_push(2,&e,64);e.sequence++;e.type=REIST_INPUT_KEY;e.code=0x1e;wire_push(2,&e,64);
    assert(!reist_desktop_channels_input(&s) && reist_desktop_input_key(&input)=='a');
    reist_graphical_control health={1,64,REIST_GRAPHICAL_HEALTH,2,9,1,cfg.children[0],0,1,0,0};
    uint32_t surface[31]={6,124,1};x86os_ipc_message_t message;
    wire_push(3,&health,64);wire_push(3,surface,124);
    assert(!reist_desktop_channels_surface(&s,0,&message));
    assert(message.version==1 && message.struct_size==140 && message.length==124);
    assert(!memcmp(message.payload,surface,124) && s.health_sequence[0]==1 && s.health_ms[0]==100);
    wire_push(3,&health,64); /* Duplicate health isolates only this application. */
    x86os_ipc_message_t saved=message;
    assert(reist_desktop_channels_surface(&s,0,&message)==-71);
    assert(!memcmp(&saved,&message,sizeof(message)) && s.phase==1 && s.application_failed[0]);
    wire_push(4,surface,124);assert(!reist_desktop_channels_surface(&s,1,&message));
    assert(reist_desktop_channels_surface(&s,0,&message)==-116);
    /* Eight health frames per poll, with no premature Surface publication. */
    health.role=3;health.owner=cfg.children[1];
    for(unsigned n=1;n<=9;n++){health.sequence=n;wire_push(4,&health,64);}
    unsigned before=wire_reads;
    assert(reist_desktop_channels_surface(&s,1,&message)==-11 && wire_reads-before==8);
    assert(s.health_sequence[1]==8);
    wire_push(4,surface,124);assert(!reist_desktop_channels_surface(&s,1,&message));
    assert(s.health_sequence[1]==9);
    /* A fifth queued supervisor control is a bounded session failure. */
    for(unsigned n=0;n<5;n++)wire_push(1,&stop,64);
    assert(reist_desktop_channels_receive(&s,&out)==-122 && s.phase==2 && !s.count);
    assert(!memcmp(&out,&unchanged,sizeof(out)));
    assert(reist_desktop_channels_input(&s)==-116);
    memset(&s,0,sizeof(s));assert(!reist_desktop_channels_init(&s,&cfg,100));
    reply.deadline_ms=500;reply.epoch++;
    wire_push(1,&reply,sizeof(reply));assert(reist_desktop_channels_receive(&s,&out)==-116);
    assert(!memcmp(&out,&unchanged,sizeof(out)));
    memset(&s,0,sizeof(s));assert(!reist_desktop_channels_init(&s,&cfg,100));
    wire_push(1,&stop,64);wire[0][wire_head[0]%16].payload[127]=1;
    assert(reist_desktop_channels_control(&s,&control)==-71);
    memset(&s,0,sizeof(s));assert(!reist_desktop_channels_init(&s,&cfg,100));
    wire_time=99;assert(reist_desktop_channels_input(&s)==-84);
}
static unsigned handshake_case,created,delegated,bounds,closed,not_yet_delegated,close_error;
static unsigned live_endpoints[3];
static int64_t handshake_call(void *context,unsigned op,uint64_t a,uint64_t b,uint64_t c) {
    (void)context;
    if(op==REIST_X64_SYS_GETPID)return 10;
    if(op==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)wire_time;
    if(op==REIST_X64_SYS_SLEEP_MS){assert(a && a<=10);if(handshake_case==8)return -5;wire_time+=a;return 0;}
    if(op==REIST_X64_SYS_IPC_CREATE) {
        assert(created<3);
        if(handshake_case==1 && created==1)return -12;
        *(uint32_t *)(uintptr_t)a=10+created;live_endpoints[created++]=1;return 0;
    }
    if(op==REIST_X64_SYS_IPC_CLOSE) {
        assert(a>=10 && a<13 && live_endpoints[a-10]);
        if(handshake_case==7 && !close_error){close_error=1;return -5;}
        live_endpoints[a-10]=0;closed++;return 0;
    }
    if(op==REIST_X64_SYS_IPC_DELEGATE) {
        assert(a==10+delegated && b==11+delegated && c==(delegated?3:1));
        delegated++;return handshake_case==3 && delegated==2?-13:0;
    }
    if(op==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        assert(a==1 && c && c<=100);
        if(!not_yet_delegated++){return -9;}
        const x86os_ipc_message_t *m=(void *)(uintptr_t)b;
        assert(m->version==1 && m->struct_size==140 && m->length==64);
        reist_graphical_control q;memcpy(&q,m->payload,64);
        assert(q.epoch==9 && q.role>=1 && q.role<=3 && q.sequence==1);
        if(q.type==REIST_GRAPHICAL_HELLO) {
            assert(!q.owner && q.endpoint==9+q.role);
            q.type=REIST_GRAPHICAL_BIND;q.owner=(uint64_t)(10+q.role)<<32|(4+q.role);
            if(handshake_case==2)q.flags=1;
            if(handshake_case==5)q.sequence=2;
            if(handshake_case!=4)wire_push(1,&q,64);
        } else {
            assert(q.type==REIST_GRAPHICAL_BOUND && delegated>=q.role);
            if(++bounds==3) {
                q=(reist_graphical_control){1,64,REIST_GRAPHICAL_READY,0,9,1,1ULL<<32,0,31,7,0};
                if(handshake_case==6)q.owner=2ULL<<32;
                wire_push(1,&q,64);
            }
        }
        return 0;
    }
    assert(op==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT && a==1 && !c);
    if(!wire_count[0])return -11;
    *(x86os_ipc_bulk_message_t *)(uintptr_t)b=wire[0][wire_head[0]++%16];wire_count[0]--;return 0;
}
static void handshake_tests(void) {
    char *args[]={"/desktop.prg","00000001","00000001","00000000","00000009",
        "00000000","000003e8","0"};
    for(handshake_case=0;handshake_case<8;handshake_case++) {
        created=delegated=bounds=closed=not_yet_delegated=close_error=0;
        memset(live_endpoints,0,sizeof(live_endpoints));
        memset(wire_head,0,sizeof(wire_head));memset(wire_count,0,sizeof(wire_count));wire_time=100;
        reist_desktop_handshake_result out={0},empty={0};
        int result=reist_desktop_handshake(8,args,handshake_call,0,&out);
        int expected[]={0,-12,-71,-13,-110,-71,-71,0};
        assert(result==expected[handshake_case]);
        if(!result) {
            assert(created==3 && delegated==3 && bounds==3 && !closed);
            assert(out.channels.input==&out.input && out.channels.children[0]==(12ULL<<32|6));
            assert(out.channels.children[1]==(13ULL<<32|7) && out.input.driver==(11ULL<<32|5));
            assert(out.deadline==1000 && out.input.epoch==7 && out.mode=='0');
            reist_desktop_channels channels={0};
            assert(!reist_desktop_channels_init(&channels,&out.channels,wire_time));
            int r=reist_desktop_handshake_close(&out);assert(r==(handshake_case==7?-5:0));
            assert(!reist_desktop_handshake_close(&out));assert(closed==3);
        } else {
            assert(!memcmp(&out,&empty,sizeof(out)) && closed==created);
            if(handshake_case==4)assert(wire_time==1000);
        }
        assert(!live_endpoints[0] && !live_endpoints[1] && !live_endpoints[2]);
    }
    for(unsigned sleep_failure=0;sleep_failure<2;sleep_failure++) {
        created=delegated=bounds=closed=not_yet_delegated=close_error=0;
        memset(live_endpoints,0,sizeof(live_endpoints));
        memset(wire_head,0,sizeof(wire_head));memset(wire_count,0,sizeof(wire_count));
        wire_time=100;handshake_case=sleep_failure?8:0;args[7]="s";
        reist_desktop_handshake_result delayed={0},empty={0};
        int status=reist_desktop_handshake(8,args,handshake_call,0,&delayed);
        assert(status==(sleep_failure?-5:-110));
        assert(wire_time==(sleep_failure?100:1000));
        assert(!created && !delegated && !bounds && !closed);
        assert(!memcmp(&delayed,&empty,sizeof(delayed)));
    }
    args[7]="0";handshake_case=0;
    reist_desktop_handshake_result out={0};
    unsigned before=created;args[1]="0000000g";
    assert(reist_desktop_handshake(8,args,handshake_call,0,&out)==-22 && created==before);
}
static union { uint64_t align; unsigned char bytes[16384]; } launch_memory;
static unsigned launch_case,launch_allocated,launch_freed,launch_entered,launch_stop;
static unsigned startup_pauses,startup_pause_ms;
static uint64_t workspace_memory[16384];
static unsigned workspace_allocated,workspace_freed;
static unsigned launch_input_polls,launch_blocking_reads;
static uint64_t launch_reply_after;
static int64_t launch_host_call(void *context,unsigned op,uint64_t a,uint64_t b,uint64_t c) {
    if(op==REIST_X64_SYS_SLEEP_MS && a>0 && (a<=10 || (a==50 && !allocations) || (launch_entered && a<=100))) {
        assert(!b && !c);wire_time+=a;ms=wire_time;return 0;
    }
    if(op==REIST_X64_SYS_MALLOC && a==sizeof(workspace_memory)) {
        assert(launch_entered && !workspace_allocated);workspace_allocated++;
        return (intptr_t)workspace_memory;
    }
    if(op==REIST_X64_SYS_FREE && a==(uintptr_t)workspace_memory) {
        assert(workspace_allocated && !workspace_freed);workspace_freed++;return 0;
    }
    if(op==REIST_X64_SYS_SLEEP_MS && (a==50 || a==100)) {
        assert(!b && !c && !launch_entered && allocations && allocations<=2);
        assert(startup_pauses<4);startup_pauses++;startup_pause_ms+=(unsigned)a;
        if(launch_case==6)wire_time=950;
        else if(launch_case!=7)wire_time+=a;
        ms=wire_time;return 0;
    }
    if(op==REIST_X64_SYS_MONOTONIC_MS && launch_case==8 && startup_pauses)
        return -INT64_C(4294967296); /* must not truncate to apparent success */
    if(op==REIST_X64_SYS_SLEEP_MS && a==25) {
        assert(!b && !c && launch_entered);wire_time+=25;return 0;
    }
    if(op==REIST_X64_SYS_MALLOC && a<16384) {
        assert(!launch_allocated && a>4096);
        if(launch_case==1)return -12;
        launch_allocated=1;memset(&launch_memory,0xa5,sizeof(launch_memory));
        return (intptr_t)&launch_memory;
    }
    if(op==REIST_X64_SYS_FREE && a==(uintptr_t)&launch_memory) {
        assert(launch_allocated && !launch_freed);launch_freed=1;
        /* The whole used context must have been erased before relinquishing it. */
        assert(!launch_memory.bytes[0]);return launch_case==5?-5:0;
    }
    if(op==REIST_X64_SYS_DEVICE_CONTROL || op==REIST_X64_SYS_MALLOC ||
       op==REIST_X64_SYS_FREE || op==REIST_X64_SYS_WRITE) {
        ms=wire_time;return call(context,op,a,b,c);
    }
    if(bounds==3 && op==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        const x86os_ipc_bulk_message_t *m=(void *)(uintptr_t)b;
        if(m->version==1) {
            assert(a==1 && c>0 && c<=100 && m->struct_size==140 && m->length==64);
            reist_graphical_control q;memcpy(&q,m->payload,sizeof(q));
            assert(q.type==REIST_GRAPHICAL_STOP && q.sequence==1 && !q.role && !q.flags && !q.endpoint && !q.value);
            assert(q.owner==(10ULL<<32|4) && q.epoch==9);launch_stop++;return 0;
        }
        assert(a==1 && !c && m->version==2 && m->struct_size==2060 && m->length==2048);
        reist_desktop_service_frame q;memcpy(&q,m->payload,sizeof(q));
        if(launch_reply_after==UINT64_MAX)launch_reply_after=wire_time+140;
        assert(!reist_desktop_broker_submit(&broker,&q,wire_time));return 0;
    }
    if(bounds==3 && op==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT) {
        assert(c<=100);
        if(a==10){assert(!c);launch_input_polls++;return -11;}
        assert(a==1);
        if(c)launch_blocking_reads++;
        if(wire_count[0])return handshake_call(context,op,a,b,0);
        if(launch_reply_after && wire_time<launch_reply_after) {
            uint64_t remaining=launch_reply_after-wire_time;
            if(!c)return -11;
            wire_time+=c<remaining?c:remaining;ms=wire_time;
            if(wire_time<launch_reply_after)return -110;
        }
        reist_desktop_service_frame reply;
        int r=reist_desktop_broker_step(&broker,&reply,wire_time);
        assert(r>=0);if(r!=2)return -11;
        x86os_ipc_bulk_message_t *m=(void *)(uintptr_t)b;
        memset(m,0,sizeof(*m));m->version=2;m->struct_size=2060;m->length=2048;
        memcpy(m->payload,&reply,sizeof(reply));return 0;
    }
    return handshake_call(context,op,a,b,c);
}
static int launch_host_entry(int argc,char **argv) {
    if(startup_pauses!=4 || startup_pause_ms!=200){fprintf(stderr,"frame allocation pacing %u ms\n",startup_pause_ms);return -84;}
    assert(argc==1 && !strcmp(argv[0],"/desktop.prg"));launch_entered++;
    uint64_t allocation_start=wire_time;
    assert(x86os_malloc(sizeof(workspace_memory))==workspace_memory);
    if(wire_time!=allocation_start+50){fprintf(stderr,"workspace pacing took %llu ms\n",(unsigned long long)(wire_time-allocation_start));return -84;}
    x86os_free(workspace_memory);assert(workspace_freed==1);
    if(!launch_case) {
        x86os_file_info_t info;
        unsigned before=launch_input_polls;uint64_t requested_at=wire_time;
        launch_reply_after=UINT64_MAX;
        assert(!x86os_stat("/text.prg",&info) && info.size==100);
        if(wire_time<=requested_at+140 || wire_time>requested_at+200){fprintf(stderr,"asset probe delay %llu ms\n",(unsigned long long)(wire_time-requested_at));return -84;}
        assert(launch_input_polls-before==1 && launch_blocking_reads>=2);launch_reply_after=0;
    }
    assert(!x86os_reist_report(X86OS_REIST_REPORT_SELF_TEST,1));
    uint64_t progress_start=wire_time;
    assert(!x86os_reist_report(X86OS_REIST_REPORT_PROGRESS,1));
    if(wire_time!=progress_start+50){fprintf(stderr,"phase pacing too long\n");return -84;}
    assert(x86os_reist_report(X86OS_REIST_REPORT_PROGRESS,1)==-71);
    if(launch_case==2)wire_time=1000;
    if(launch_case==3 || launch_case==4) {
        reist_graphical_control stop={1,64,REIST_GRAPHICAL_STOP,0,9,2,1ULL<<32,0,0,0,0};
        if(launch_case==4)stop.flags=1;
        wire_push(1,&stop,64);
    }
    return reist_desktop_platform_pump();
}
static int launch_tests(unsigned which) {
    assert(which<=8);launch_case=which;handshake_case=0;
    strcpy(manifest[0].path,"/text.prg");strcpy(manifest[0].info.name,"text.prg");
    manifest[0].info.type=X86OS_FILE;manifest[0].info.size=100;manifest[0].rights=3;manifest[0].digest[0]=1;
    reist_desktop_broker_config bc={1ULL<<32,10ULL<<32|4,9,1,manifest,1,0,clock_read,step,abort_all};
    assert(!reist_desktop_broker_init(&broker,&bc,100));
    uint64_t owners[2]={12ULL<<32|6,13ULL<<32|7};assert(!reist_desktop_broker_adopt(&broker,owners,100));
    char *args[]={"/desktop.prg","00000001","00000001","00000000","00000009",
        "00000000","000003e8","0"};
    if(!which)args[6]="000007d0"; /* room for the140ms intermediate-timeout case */
    int r=reist_desktop_launch(8,args,startup_font,sizeof(startup_font),launch_host_entry,launch_host_call,0);
    int expected[]={0,-12,-110,0,-116,-5,-110,-110,-84};assert(r==expected[which]);
    assert(launch_allocated==(which!=1) && launch_freed==launch_allocated);
    assert(launch_entered==(which!=1 && which<6));
    if(which>=6)assert(allocations==1 && frees==1 && startup_pauses==1);
    assert(created==closed && allocations==frees && !ready_reports);
    assert(launch_stop==(which==0 || which==5));
    puts("native role launch, unchanged deadline, root stop and cleanup passed");return 0;
}
#include "../userspace/gui/compositor/desktop_explorer.h"
int main(int argc,char **argv) {
    if(argc==2 && argv[1][0]>='0' && argv[1][0]<='8' && !argv[1][1])return launch_tests((unsigned)(argv[1][0]-'0'));
    input_tests();
    if(input_order_tests())return 1;
    channel_tests();
    handshake_tests();
    strcpy(manifest[0].path,"/");strcpy(manifest[0].info.name,"/");manifest[0].info.type=X86OS_DIRECTORY;manifest[0].rights=1;
    strcpy(manifest[1].path,"/asset");strcpy(manifest[1].info.name,"asset");manifest[1].info.type=X86OS_FILE;manifest[1].info.size=4096;manifest[1].rights=1;
    strcpy(manifest[2].path,"/text.prg");strcpy(manifest[2].info.name,"text.prg");manifest[2].info.type=X86OS_FILE;manifest[2].info.size=100;manifest[2].rights=3;manifest[2].digest[0]=1;
    uint64_t root=UINT64_C(3)<<32,desktop=UINT64_C(10)<<32|4;
    reist_desktop_broker_config bc={root,desktop,1,4,manifest,3,0,clock_read,step,abort_all};
    assert(!reist_desktop_broker_init(&broker,&bc,ms));
    reist_desktop_service_client_config cc={root,desktop,1,0,clock_read,send_frame,receive_frame,wait_frame,failed};
    assert(!reist_desktop_service_client_init(&client,&cc));
    reist_desktop_platform_config pc={&client,0,call,pump,mouse,key,report,failed,0};
    assert(!reist_desktop_platform_attach(&pc));
    unsigned console_calls=calls;
    x86os_puts("");assert(calls==console_calls);
    x86os_puts("startup\n");assert(calls==console_calls+2);
    assert(x86os_getchar_nonblocking()==0);
    static desktop_explorer_t explorer;
    desktop_explorer_initialize(&explorer);
    assert(desktop_explorer_open(&explorer,0,"/")==DESKTOP_EXPLORER_OK);
    assert(explorer.windows[0].entry_count==2);
    /* Start the unrelated file tests in a fresh unchanged rate window. */
    ms+=1000;
    reist_vfs_file_handle_t file=0;assert(!reist_vfs_file_open("/asset",1000,&file));
    unsigned char out[256];
    for(unsigned n=0;n<7;n++) {
        memset(out,0xa5,sizeof(out));assert(reist_vfs_file_read(file,out,sizeof(out))==256);
        for(unsigned i=0;i<256;i++)assert(out[i]==(unsigned char)(n*256+i));
    }
    assert(reads==1); /*1792-byte prefetch serves seven existing SDK reads. */
    unsigned char bulk[4096];
    assert(reist_vfs_file_read_bulk(file,bulk,sizeof(bulk))==1792);
    for(unsigned n=0;n<1792;n++)assert(bulk[n]==(unsigned char)(1792+n));
    assert(reist_vfs_file_read_bulk(file,bulk,sizeof(bulk))==512);
    assert(reist_vfs_file_read_bulk(file,bulk,1)==0);
    assert(!reist_vfs_file_close(file));assert(reist_vfs_file_read(file,out,1)<0);
    unsigned before=calls;assert(x86os_create("/asset")==-30);assert(x86os_unlink("/asset")==-30);
    assert(calls==before);
    assert(x86os_spawn("/asset")==-13);
    assert(x86os_spawn("/text.prg")==20);
    x86os_process_identity_t id={0};assert(!x86os_process_identity_of(20,&id) && id.pid==20 && id.generation==20);
    before=calls;assert(x86os_process_identity_of(21,&id)==-13);assert(x86os_kill(21)==-13);assert(calls==before);
    assert(!x86os_kill(20));int status=-1;assert(x86os_wait(20,&status)==20 && status==0);
    assert(x86os_process_identity_of(20,&id)==-13);
    assert(!x86os_process_identity(&id) && id.pid==10 && id.generation==10);
    uint64_t sleep_start=ms;assert(!x86os_sleep_ms(25));assert(ms==sleep_start+25);
    assert(reist_vfs_read_at("/asset",9,out,17,1000)==17);
    for(unsigned n=0;n<17;n++)assert(out[n]==(unsigned char)(9+n));
    x86os_storage_submit_t sq={1,sizeof(sq),X86OS_STORAGE_VFS_SHADOW_STAT,0,0,512,1};
    x86os_vfs_shadow_frame_t sf={0};sf.version=1;sf.struct_size=512;sf.operation=5;
    sf.path_length=6;memcpy(sf.path,"/asset",7);
    x86os_storage_handle_t sh=0;
    assert(!x86os_storage_submit(&sq,&sf,&sh));
    x86os_vfs_shadow_frame_t poisoned;memset(&poisoned,0x5a,sizeof(poisoned));
    x86os_vfs_shadow_frame_t unchanged=poisoned;int32_t sr=44;
    ms++;unsigned sequence=(unsigned)client.sequence;
    assert(x86os_storage_collect(sh,&sr,&poisoned)==-110);
    assert(client.sequence==sequence && sr==44 && !memcmp(&poisoned,&unchanged,sizeof(poisoned)));
    assert(!x86os_storage_cancel(sh));assert(x86os_storage_cancel(sh)==-22);
    sf.reserved[0]=1;sh=0;assert(x86os_storage_submit(&sq,&sf,&sh)==-22 && !sh);
    reist_desktop_platform_detach();assert(x86os_stat("/asset",&(x86os_file_info_t){0})<0);
    assert(!reist_desktop_broker_revoke(&broker));
    reist_desktop_service_client_detach(&client);bc.epoch++;cc.epoch++;
    assert(!reist_desktop_broker_init(&broker,&bc,ms));
    assert(!reist_desktop_service_client_init(&client,&cc));
    assert(!reist_desktop_platform_attach(&pc));
    uint64_t owners[2]={UINT64_C(21)<<32|6,UINT64_C(22)<<32|7};
    unsigned rejected_before=(unsigned)client.sequence;
    assert(reist_desktop_platform_adopt(owners)==-13); /* no supervisor grant */
    assert(client.sequence==rejected_before);
    assert(!reist_desktop_broker_adopt(&broker,owners,ms));
    uint64_t bad[2]={owners[0],UINT64_C(23)<<32|7};
    assert(reist_desktop_platform_adopt(bad)==-13);
    before=calls;assert(x86os_process_identity_of(21,&id)==-13 && calls==before);
    assert(!reist_desktop_platform_adopt(owners));
    assert(reist_desktop_platform_adopt(owners)==-16);
    assert(!x86os_process_identity_of(21,&id) && id.pid==21);
    assert(!x86os_process_identity_of(22,&id) && id.pid==22);
    assert(x86os_spawn("/text.prg")==-11);
    wait_status=256;assert(x86os_wait(21,&status)==21 && status==256);assert(x86os_process_identity_of(21,&id)==-13);
    assert(!reist_desktop_broker_revoke(&broker));
    reist_desktop_platform_detach();reist_desktop_service_client_detach(&client);
    assert(!failures);
    for(startup_case=0;startup_case<=7;startup_case++) {
        allocations=frees=entered=commits=0;display_epoch++;ms+=1000;
        bc.epoch++;cc.epoch++;
        assert(!reist_desktop_broker_init(&broker,&bc,ms));
        assert(!reist_desktop_service_client_init(&client,&cc));
        /* Fresh incarnations are mandatory across root broker epochs. */
        uint64_t pair[2]={(uint64_t)(30+startup_case*2)<<32|6,
                          (uint64_t)(31+startup_case*2)<<32|7};
        assert(!reist_desktop_broker_adopt(&broker,pair,ms));
        reist_desktop_startup_config cfg={pc,startup_font,sizeof(startup_font),
            {pair[0],pair[1]},startup_entry};
        if(startup_case==4)cfg.children[1]+=1ULL<<32;
        char *args[]={"/desktop.prg"};
        int result=reist_desktop_startup_run(&cfg,1,args);
        int expected[]={0,-12,-12,-71,-13,-110,-5,-19};
        assert(result==expected[startup_case]);
        assert(entered==(startup_case==0 || startup_case>=5));
        assert(frees==(startup_case==1 || startup_case==3?0:startup_case==2?1:2));
        if(frees==2)assert(freed[0]==1 && freed[1]==0);
        if(frees==1)assert(freed[0]==0);
        assert(reist_desktop_display_idle()==-19 && x86os_getchar_nonblocking()==-116);
        assert(!reist_desktop_broker_revoke(&broker));reist_desktop_service_client_detach(&client);
    }
    assert(failures==2);
    frontend_test=1;ms+=1000;wire_time=ms;bc.epoch++;cc.epoch++;
    memset(wire_head,0,sizeof(wire_head));memset(wire_count,0,sizeof(wire_count));
    assert(!reist_desktop_broker_init(&broker,&bc,ms));
    assert(!reist_desktop_service_client_init(&client,&cc));
    uint64_t pair[2]={100ULL<<32|6,101ULL<<32|7};
    assert(!reist_desktop_broker_adopt(&broker,pair,ms));
    reist_desktop_input_state input={0};reist_desktop_channels channels={0};
    assert(!reist_desktop_input_bind(&input,desktop,11ULL<<32|5,7,ms));
    reist_desktop_channels_config cconfig={0,wire_call,root,desktop,bc.epoch,
        {pair[0],pair[1]},1,2,{3,4},&input,ms+3000};
    assert(!reist_desktop_channels_init(&channels,&cconfig,ms));pc.channels=&channels;
    assert(!reist_desktop_platform_attach(&pc));assert(!reist_desktop_platform_adopt(pair));
    extern int reist_desktop_platform_render_checkpoint(unsigned wait);
    uint64_t render_before=ms, render_end=channels.config.start_deadline_ms;
    assert(reist_desktop_platform_render_checkpoint(101)==-22);
    assert(ms==render_before && !reist_desktop_platform_render_checkpoint(100));
    assert(ms==render_before+100 && channels.config.start_deadline_ms==render_end);
    assert(!reist_desktop_platform_render_checkpoint(0) && ms==render_before+100);
    assert(!reist_desktop_platform_render_checkpoint(50) && ms==render_before+150);
    assert(!reist_desktop_platform_render_checkpoint(20) && ms==render_before+170);
    assert(channels.config.start_deadline_ms==render_end);
    unsigned startup_console_calls=calls;
    console_capture=1;console_bytes=0;
    x86os_puts("startup=");x86os_print_number(42);
    assert(calls==startup_console_calls && !console_bytes);
    x86os_putchar('\n');assert(calls==startup_console_calls+2);
    assert(console_bytes==11 && !memcmp(console_output,"startup=42\n",11));
    console_bytes=0;console_partial=1;
    char full_line[129];memset(full_line,'x',128);full_line[128]=0;
    x86os_puts(full_line);assert(console_bytes==128);
    assert(!memcmp(console_output,full_line,128));
    x86os_puts("pending");assert(console_bytes==128);
    assert(x86os_write(1,"tail",4)==4);
    assert(console_bytes==139 && !memcmp(console_output+128,"pendingtail",11));
    console_capture=console_partial=0;
    reist_input_event_v1 event={2,64,REIST_INPUT_HEALTHY,0,11ULL<<32|5,desktop,7,1,0,0,0,0};
    wire_push(2,&event,64);event.sequence++;event.type=REIST_INPUT_KEY;event.code=0x1e;
    wire_push(2,&event,64);event.sequence++;event.type=REIST_INPUT_POINTER;
    event.code=0;event.dx=13;event.dy=-7;event.buttons=1;wire_push(2,&event,64);
    assert(!reist_desktop_platform_pump());
    assert(x86os_getchar_nonblocking()=='a' && x86os_getchar_nonblocking()==0);
    x86os_mouse_event_t actual_mouse;
    assert(!x86os_mouse_event(&actual_mouse) && actual_mouse.delta_x==13 &&
        actual_mouse.delta_y==7 && actual_mouse.buttons==1 && actual_mouse.generation==11);
    assert(x86os_mouse_event(&actual_mouse)==-11);
    desktop_surface_runtime_t runtime;assert(!desktop_surface_runtime_initialize(&runtime));
    desktop_surface_runtime_t empty=runtime;
    display_epoch++;commits=0;
    reist_desktop_display_config display_config={1,sizeof(display_config),800,600,desktop,display_epoch,
        startup_pixels[0],startup_pixels[1],800*600,startup_font,sizeof(startup_font),0,clock_read,frontend_commit};
    assert(!reist_desktop_display_attach(&display_config) && !x86os_display_activate());
    assert(!x86os_fill_rect(0,0,800,600,0x123456));
    assert(!reist_desktop_platform_pump() && !commits);
    channels.config.children[1]+=1ULL<<32;
    assert(reist_desktop_frontend_adopt(&runtime)==-13 && !greetings);
    assert(!memcmp(&empty,&runtime,sizeof(empty)));
    assert(!reist_desktop_platform_pump() && !commits);
    channels.config.children[1]=pair[1];
    assert(!reist_desktop_frontend_adopt(&runtime) && greetings==2);
    assert(!reist_desktop_platform_pump() && !commits);
    assert(!delegations);
    assert(reist_desktop_frontend_adopt(&runtime)==-16);
    assert(runtime.clients[0].owner.pid==100 && runtime.clients[1].owner.pid==101);
    static desktop_surface_manager_t manager;desktop_surface_initialize(&manager);
    reist_gui_surface_message_t request={0};request.protocol_version=6;request.message_size=124;
    request.type=REIST_GUI_SURFACE_CREATE;request.flags=REIST_GUI_SURFACE_ROLE_TOPLEVEL;
    request.width=320;request.height=192;
    for(unsigned n=0;n<2;n++)wire_push(3+n,&request,124);
    assert(!desktop_surface_runtime_poll(&runtime,&manager));
    for(unsigned n=0;n<2;n++) {
        assert(surface_reply[n].type==REIST_GUI_SURFACE_CONFIGURE && !surface_reply[n].flags);
        request=(reist_gui_surface_message_t){0};request.protocol_version=6;request.message_size=124;
        request.surface=surface_reply[n].surface;request.serial=surface_reply[n].serial;
        request.type=REIST_GUI_SURFACE_ACK_CONFIGURE;wire_push(3+n,&request,124);
        request.type=REIST_GUI_SURFACE_PAINT_BEGIN;request.serial=0;wire_push(3+n,&request,124);
        request.type=REIST_GUI_SURFACE_PAINT_FILL;request.flags=0x123456;
        request.damage=(reist_gui_rect_t){0,0,320,192};wire_push(3+n,&request,124);
        request.type=REIST_GUI_SURFACE_PAINT_COMMIT;request.flags=0;wire_push(3+n,&request,124);
        reist_graphical_control health={1,64,REIST_GRAPHICAL_HEALTH,n+2,bc.epoch,1,pair[n],0,1,0,0};
        wire_push(3+n,&health,64);
    }
    assert(!desktop_surface_runtime_poll(&runtime,&manager));
    assert(channels.health_sequence[0]==1 && channels.health_sequence[1]==1);
    assert(manager.slots[0].committed_paint_count==1 && manager.slots[1].committed_paint_count==1);
    /* Explicit renderer-state fixtures: the guest gate must prove real pixels
     * from desktop.c. Here the actual adapter proves delayed physical drain. */
    desktop_wm_t windows={0};
    extern int reist_desktop_frontend_scene_ready(const desktop_surface_runtime_t *,
        const desktop_surface_manager_t *,const desktop_wm_t *);
    assert(!reist_desktop_frontend_scene_ready(&runtime,&manager,&windows));
    assert(!reist_desktop_frontend_presented(&runtime,&manager,&windows) && !ready_reports);
    for(unsigned n=0;n<2;n++) {
        manager.slots[n].window_index=n;
        manager.slots[n].presented_generation=manager.slots[n].paint_generation;
        windows.windows[n].visible=1;windows.windows[n].generation=1;
        windows.windows[n].width=340;windows.windows[n].height=212;
        windows.windows[n].content_id=0x80000000U|manager.slots[n].handle.id;
    }
    assert(!reist_desktop_frontend_presented(&runtime,&manager,&windows) && !ready_reports);
    assert(reist_desktop_frontend_scene_ready(&runtime,&manager,&windows)==1);
    /* Rendering crossed a health interval while real HEALTH messages queued.
     * Refresh through the production end-of-frame path before judging age. */
    extern int reist_desktop_frontend_finish_frame(desktop_surface_runtime_t *,
        desktop_surface_manager_t *,const desktop_wm_t *);
    ms+=1001;wire_time=ms;
    assert(reist_desktop_frontend_presented(&runtime,&manager,&windows)==-110);
    reist_input_event_v1 fresh_input={2,64,REIST_INPUT_HEALTHY,0,11ULL<<32|5,desktop,7,input.sequence+1,0,0,0,0};
    wire_push(2,&fresh_input,64);
    for(unsigned n=0;n<2;n++) {
        reist_graphical_control fresh={1,64,REIST_GRAPHICAL_HEALTH,n+2,bc.epoch,2,pair[n],0,1,0,0};
        wire_push(3+n,&fresh,64);
    }
    /* Invalid scenes must never initiate the startup drain or earn READY. */
    windows.windows[0].visible=0;
    assert(!reist_desktop_frontend_finish_frame(&runtime,&manager,&windows) && !ready_reports);
    windows.windows[0].visible=1;windows.windows[0].content_id++;
    assert(!reist_desktop_frontend_presented(&runtime,&manager,&windows) && !ready_reports);
    windows.windows[0].content_id--;windows.windows[0].minimized=1;
    assert(!reist_desktop_frontend_presented(&runtime,&manager,&windows) && !ready_reports);
    windows.windows[0].minimized=0;
    uint64_t drain_start=ms;
    assert(!reist_desktop_frontend_finish_frame(&runtime,&manager,&windows));
    assert(channels.health_sequence[0]==2 && channels.health_sequence[1]==2);
    assert(channels.health_ms[0]<=ms && ms-channels.health_ms[0]<1000);
    assert(channels.health_ms[1]<=ms && ms-channels.health_ms[1]<1000);
    if(ms-drain_start<100 || ms-drain_start>250){fprintf(stderr,"startup drain took %llu ms\n",(unsigned long long)(ms-drain_start));return 1;}
    assert(!reist_desktop_display_idle() && commits==130 && ready_reports==1);
    assert(!reist_desktop_frontend_presented(&runtime,&manager,&windows) && ready_reports==1);
    /* A normal completed raster publishes before another application drain. */
    assert(!x86os_fill_rect(0,0,1,1,0x223344));
    unsigned normal_reads=wire_reads,normal_commits=commits;
    assert(!reist_desktop_frontend_finish_frame(&runtime,&manager,&windows));
    assert(wire_reads==normal_reads && commits==normal_commits+1);
    extern int reist_desktop_platform_live_checkpoint(unsigned,uint64_t);
    uint64_t live_before=ms,live_end=ms+1000;
    assert(reist_desktop_platform_live_checkpoint(1,live_end)==-22);
    assert(!reist_desktop_platform_live_checkpoint(50,live_end) && ms>=live_before+50);
    assert(!reist_desktop_platform_live_checkpoint(0,live_end));
    /* Recovery raster uses its original deadline after startup has expired. */
    uint64_t saved_start=channels.config.start_deadline_ms;
    channels.config.start_deadline_ms=ms;
    channels.recovery[0]=REIST_DESKTOP_RECOVERY_WAIT_BIND;
    channels.recovery_end[0]=ms+100;
    uint64_t recovery_deadline=channels.recovery_end[0],recovery_before=ms;
    assert(!reist_desktop_platform_render_checkpoint(20));
    assert(ms>=recovery_before+20 && channels.recovery_end[0]==recovery_deadline);
    recovery_before=ms;
    assert(!reist_desktop_frontend_finish_frame(&runtime,&manager,&windows));
    assert(ms>=recovery_before+50 && channels.recovery_end[0]==recovery_deadline);
    channels.recovery[0]=0;channels.recovery_end[0]=0;
    channels.config.start_deadline_ms=saved_start;
    extern int reist_desktop_platform_idle_wait(void);
    uint64_t idle_before=ms;unsigned idle_calls=calls;
    assert(!reist_desktop_platform_idle_wait());
    assert(ms==idle_before+1 && calls==idle_calls+3);
    assert(!x86os_fill_rect(0,0,1,1,0x123456));
    fresh_input.sequence=input.sequence+1;fresh_input.type=REIST_INPUT_KEY;fresh_input.code=0x30;
    wire_push(2,&fresh_input,64);
    unsigned before_input_commits=commits;
    assert(!reist_desktop_platform_pump() && input.key_count==1 && commits==before_input_commits);
    assert(!reist_desktop_platform_pump() && input.key_count==1 && commits>before_input_commits);
    assert(x86os_getchar_nonblocking()=='b');
    channels.frontend_ready=0;
    assert(reist_desktop_platform_idle_wait()==-116);
    channels.config.start_deadline_ms=ms;
    assert(reist_desktop_frontend_presented(&runtime,&manager,&windows)==-110 && ready_reports==1);
    reist_desktop_display_detach();
    /* Malformed first peer is fenced without losing the other Surface. */
    reist_graphical_control badhealth={1,64,REIST_GRAPHICAL_HEALTH,2,bc.epoch,1,pair[0],0,1,0,0};
    wire_push(3,&badhealth,64);
    assert(desktop_surface_runtime_poll(&runtime,&manager)==-71);
    assert(channels.application_closed[0] && !channels.application_closed[1]);
    assert(runtime.clients[0].active==DESKTOP_SURFACE_RUNTIME_RETIRING);
    assert(runtime.clients[1].active==DESKTOP_SURFACE_RUNTIME_BOUND && manager.slots[1].active);
    assert(!manager.slots[0].active && app_closes==1);
    /* Recovery starts from the established desktop, after the separate
     * startup-deadline rejection above. */
    channels.frontend_ready=1;
    desktop_surface_runtime_client_t other_client=runtime.clients[1];
    desktop_surface_slot_t other_surface=manager.slots[1];
    reist_desktop_channels saved_channels=channels;
    channels.recovery[0]=REIST_DESKTOP_RECOVERY_WAIT_REAP;channels.recovery_old[0]=pair[0];
    channels.recovery_end[0]=wire_time+10000;
    reist_graphical_control reaped={1,64,REIST_GRAPHICAL_CLIENT_REAPED,2,channels.config.epoch,2,pair[0],0,0,0,0};
    saved_channels=channels;reaped.owner++;
    assert(reist_desktop_channels_recovery_control(&channels,&reaped,wire_time)==-116);
    assert(!memcmp(&channels,&saved_channels,sizeof(channels)));reaped.owner--;
    assert(reist_desktop_channels_recovery_control(&channels,&reaped,channels.recovery_end[0])==-116);
    assert(!memcmp(&channels,&saved_channels,sizeof(channels)));
    int recovery_result=reist_desktop_channels_recovery_control(&channels,&reaped,wire_time);
    if(recovery_result){fprintf(stderr,"reaped result=%d phase=%u ready=%u rec=%u owner=%llx old=%llx now=%llu prev=%llu\n",
        recovery_result,channels.phase,channels.frontend_ready,channels.recovery[0],
        (unsigned long long)reaped.owner,(unsigned long long)channels.recovery_old[0],
        (unsigned long long)wire_time,(unsigned long long)channels.previous);return 1;}
    assert(reist_desktop_channels_recovery_control(&channels,&reaped,wire_time)==-116);
    channels.config.call=recovery_call;
    assert(!reist_desktop_frontend_recover(&runtime,&manager));
    assert(channels.recovery[0]==REIST_DESKTOP_RECOVERY_HELLO);
    assert(!reist_desktop_frontend_recover(&runtime,&manager));
    assert(channels.recovery[0]==REIST_DESKTOP_RECOVERY_WAIT_BIND);
    reist_graphical_control binding={1,64,REIST_GRAPHICAL_BIND,2,channels.config.epoch,1,102ULL<<32|6,5,0,0,0};
    saved_channels=channels;binding.owner=pair[0];
    assert(reist_desktop_channels_recovery_control(&channels,&binding,wire_time)==-116);
    assert(!memcmp(&channels,&saved_channels,sizeof(channels)));binding.owner=102ULL<<32|6;
    binding.endpoint=4;assert(reist_desktop_channels_recovery_control(&channels,&binding,wire_time)==-116);binding.endpoint=5;
    assert(reist_desktop_channels_recovery_control(&channels,&binding,channels.recovery_end[0])==-116);
    assert(!reist_desktop_channels_recovery_control(&channels,&binding,wire_time));
    assert(!reist_desktop_broker_replace(&broker,pair[0],binding.owner,ms));
    assert(!reist_desktop_frontend_recover(&runtime,&manager));
    assert(channels.recovery[0]==REIST_DESKTOP_RECOVERY_APP_HELLO);
    assert(!reist_desktop_frontend_recover(&runtime,&manager));
    assert(channels.recovery[0]==REIST_DESKTOP_RECOVERY_WAIT_READY && !channels.recovery_ready[0]);
    assert(runtime.clients[0].owner.pid==102 && runtime.clients[0].endpoint==5);
    assert(!memcmp(&other_client,&runtime.clients[1],sizeof(other_client)));
    assert(!memcmp(&other_surface,&manager.slots[1],sizeof(other_surface)));
    assert(recovery_creates==1 && recovery_delegates==1 && recovery_app_sends==2 && recovery_root_sends==3);
    channels.recovery[0]=0;channels.config.call=wire_call;
    desktop_surface_runtime_shutdown(&runtime);assert(app_closes==3);
    assert(!reist_desktop_broker_revoke(&broker));
    reist_desktop_platform_detach();reist_desktop_service_client_detach(&client);
    assert(failures==2);puts("actual native desktop SDK/startup and Surface runtime integration passed");return 0;
}
#endif /* REIST_TEST_LAZY_FONT */
