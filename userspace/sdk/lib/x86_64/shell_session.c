/* Normal shell adapter for the explicit NativeShellSession profile only.
 * Device/protocol parsing stays in the separate existing driver/FS processes. */
#include <x86os.h>
#include <reist/x86_64/shell_session.h>
#include <reist/x86_64/service_session.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/task.h>
#include <reist/x86_64/terminal.h>
#ifdef REIST_NATIVE_VIDEO_MODE
static unsigned session_video_active,video_driver_reaped;
static int session_video_start(int);
static int session_video_wait(int *);
static int video_stop(int);
#endif
#ifdef REIST_NATIVE_VGA_CONSOLE
static void session_vga_poll(uint64_t);
static void session_vga_health(uint64_t);
static int64_t session_vga_wait3(unsigned,uintptr_t,uintptr_t,uintptr_t);
#define SESSION_APPLICATION_SLOT 5U
#else
#define SESSION_APPLICATION_SLOT 4U
#endif
#ifdef REIST_NATIVE_APP_NETWORK
#ifdef REIST_NATIVE_APP_TCP
static unsigned session_tcp_active;
#ifdef REIST_NATIVE_APP_HTTP
static unsigned session_http_selected;
#endif
static unsigned session_input_idle;
#ifdef REIST_NATIVE_APP_DNS
static unsigned session_dns_selected;
#endif
static int64_t session_tcp_import(int,const char *const *,reist_task_startup_v1_t *,reist_task_profile_v1_t *);
static int64_t session_tcp_wait(int *);
static int session_tcp_revoke(void);
#endif
static unsigned session_udp_active;
static int64_t session_udp_import(int,const char *const *,reist_task_startup_v1_t *,reist_task_profile_v1_t *);
static int64_t session_udp_wait(int *);
static int session_udp_revoke(void);
#endif
#ifdef REIST_NATIVE_NETWORK_SESSION
static int session_network_retire(void);
static void session_network_poll(void);
static void session_network_free(void);
#endif
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
static unsigned session_graphical_active;
static int session_graphical_start(int,uint64_t);
static int session_graphical_wait(int *);
static int session_graphical_kill(void);
#endif
#ifdef REIST_NATIVE_TERMINAL_SERVICE
#include <reist/x86_64/terminal_service.h>
static uint64_t session_terminal_service,session_previous_terminal_service,session_input_service_pending;
#endif
#include <reist/x86_64/console.h>
#include <reist/x86_64/file_image.h>
#include <reist/x86_64/pio.h>
#ifdef REIST_NATIVE_DISPLAY
#include <reist/x86_64/display.h>
#endif
#ifdef REIST_NATIVE_LARGE_FILE
#include <reist/x86_64/large_file.h>
/* Local selected adapter: every ordinary app snapshot is RNPGv3. Driver/FS
 * startup below explicitly retains the independently admitted v2/v6 path. */
#define reist_file_image_workspace reist_file_image_workspace_v3
#define reist_service_session_init reist_service_session_init_v3
#define reist_x64_file_finish_v2 reist_x64_file_finish_v4
#define reist_x64_task_import_wide reist_x64_task_import_large
#define REIST_FS_SESSION_REQUESTS REIST_LARGE_FS_REQUESTS
#define SESSION_CAPTURE_VERSION 3
#define SESSION_PREPARED_BYTES REIST_X64_PREPARED_V3_BYTES
#elif defined(REIST_NATIVE_WIDE_FILE)
#include <reist/x86_64/wide_file.h>
#define reist_file_image_workspace reist_file_image_workspace_v2
#define reist_service_session_init reist_service_session_init_v2
#define reist_x64_file_finish_v2 reist_x64_file_finish_v3
#define REIST_FS_SESSION_REQUESTS REIST_WIDE_FS_REQUESTS
#define SESSION_CAPTURE_VERSION 2
#else
#define SESSION_CAPTURE_VERSION 1
#endif
#ifndef SESSION_PREPARED_BYTES
#define SESSION_PREPARED_BYTES REIST_X64_PREPARED_V2_BYTES
#endif
#define SESSION_S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define SESSION_S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#ifdef REIST_NATIVE_VGA_CONSOLE
#define SESSION_S3(n,a,b,c) session_vga_wait3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#else
#define SESSION_S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#endif
#define SESSION_MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
/* Private qualification selector, default healthy ext2. Not a syscall/API.
 * The host may select a declared case only before the first user instruction. */
volatile uint64_t reist_shell_session_selection[4] __attribute__((section(".data.memory_witness")))={
    0x3153455353484c53ULL,1,2,0};
static reist_session_policy_v1 session_policy;
static reist_service_session_v1 session_service;
static reist_fs_client session_fs;
static reist_file_capture_v1 session_observation;
static reist_file_image_workspace *session_workspace;
static void *session_prepared;
static uint64_t session_child;
static uint64_t session_operation_deadline;
static unsigned session_case,session_failed,session_mount,session_sectors;
static char session_cwd[192]="/",session_output[64];
static unsigned session_output_used;
static void session_flush(void);
static int session_retire(void);
static _Noreturn void session_stop(int error) {
    /* Kernel root retirement is the final fail-closed fence when Ring3 cannot
     * confirm its own cleanup. Never resume an uncertain supervisor state. */
    (void)SESSION_S1(EXIT,error==-110?110:error==-22?22:5);__builtin_trap();
}
static void session_bytes(void *to,const void *from,size_t bytes) {
    volatile unsigned char *a=to;const unsigned char *b=from;
    for(size_t n=0;n<bytes;n++)a[n]=b[n];
}
static void session_zero(void *to,size_t bytes) {
    typedef uint64_t word __attribute__((may_alias,aligned(1)));
    volatile unsigned char *a=to;
    while(bytes>=8){*(volatile word*)a=0;a+=8;bytes-=8;}
    while(bytes--)*a++=0;
}
static uint64_t session_now(void) {
    int64_t stamp=SESSION_S0(MONOTONIC_MS);
    if(stamp<0)session_stop(-5);
    int result=reist_session_policy_charge(&session_policy,(uint64_t)stamp,1,0,0);
    if(result)session_stop(result);
#ifdef REIST_NATIVE_VGA_CONSOLE
    session_vga_health((uint64_t)stamp);
#endif
    return (uint64_t)stamp;
}
#ifdef REIST_NATIVE_VGA_CONSOLE
/* A timed-out wait publishes no IPC delivery. Keep one absolute deadline
 * across slices and probe health without recursive service recreation. */
static int64_t session_vga_wait3(unsigned op,uintptr_t a,uintptr_t b,uintptr_t timeout) {
    if((op!=REIST_X64_SYS_IPC_SEND_TIMEOUT && op!=REIST_X64_SYS_IPC_RECEIVE_TIMEOUT)
       || !timeout || timeout>1000)return reist_x64_syscall3(op,a,b,timeout);
    uint64_t now=session_now(),end=now+timeout;
    for(unsigned attempt=0;attempt<11 && now<end;attempt++) {
        uint64_t slice=end-now;if(slice>100)slice=100;
        int64_t r=reist_x64_syscall3(op,a,b,slice);
        now=session_now();
        if(r!=-110)return r;
    }
    return -110;
}
#endif
static uint64_t service_clock(void *context){(void)context;return session_now();}
static int service_endpoint(void *context,uint32_t *out){(void)context;return (int)SESSION_S1(IPC_CREATE,out);}
static int service_close(void *context,uint32_t ep){(void)context;return (int)SESSION_S1(IPC_CLOSE,ep);}
static int service_delegate(void *context,uint32_t ep,uint64_t owner){
    (void)context;return (int)SESSION_S3(IPC_DELEGATE,ep,owner,3);
}
static int service_pio(void *context,uint64_t owner,unsigned operation) {
    (void)context;reist_native_pio_request q={1,64,operation,0,owner,0,0,0,0,0,0,0};
#ifdef REIST_NATIVE_LARGE_FILE
    if(operation==REIST_PIO_BIND && session_service.version==3) {
        int result=reist_x64_pio_throughput_bind_prepare(&q,owner);
        if(result)return result;
    }
#endif
    return (int)reist_x64_pio(&q);
}
static int64_t service_task(void *context,unsigned operation,uint64_t owner,unsigned timeout) {
    (void)context;reist_task_control_request_t q={1,64,operation,0,owner,0,timeout,0,0,0};
#ifdef REIST_NATIVE_VGA_CONSOLE
    if(operation==2 && timeout && timeout<=1000) {
        uint64_t now=session_now(),end=now+timeout;
        for(unsigned attempt=0;attempt<11 && now<end;attempt++) {
            q.timeout_ms=(unsigned)(end-now);if(q.timeout_ms>100)q.timeout_ms=100;
            int64_t r=reist_x64_task_control(&q);
            now=session_now();
            if(r!=-110)return r;
        }
        return -110;
    }
#endif
    return reist_x64_task_control(&q);
}
static void session_hex(char *text,uint32_t value) {
    for(unsigned n=0;n<8;n++)text[n]="0123456789abcdef"[(value>>(28-4*n))&15];
    text[8]=0;
}
static int64_t service_create(void *context,unsigned role,uint32_t endpoint,unsigned options) {
    (void)context;char channel[9],option[9];session_hex(channel,endpoint);session_hex(option,options);
    const char *args[]={channel,option};reist_task_startup_v1_t startup;
    if(role!=2 && role!=3)return -22;
    /* Qualification case17 cancels the driver on partial FS OOM. Let its
     * two real console-denial probes run first; never renew the operation
     * deadline or replace a blocked wait with a userspace spin. */
    if(role==3 && session_case==17 && session_service.starts==2)
        (void)x86os_sleep_ms(100);
    int result=reist_x64_startup_init(&startup,2,args);if(result)return result;
    const unsigned char *blob=role==2?reist_native_shell_images.driver:reist_native_shell_images.filesystem;
    size_t bytes=role==2?reist_native_shell_images.driver_bytes:reist_native_shell_images.filesystem_bytes;
    result=reist_x64_image_prepare_v2(session_prepared,blob,bytes);if(result)return result;
    reist_task_profile_v1_t profile={1,40,{SESSION_MASK,role==2?1ULL<<49:0,0},0};
    int64_t child=reist_x64_task_import_periodic(session_prepared,&profile,32,1000,&startup);
    session_zero(session_prepared,SESSION_PREPARED_BYTES);session_zero(&startup,sizeof(startup));
    return child;
}
static int service_send(void *context,uint32_t endpoint,const reist_session_control *c,unsigned timeout) {
    (void)context;x86os_ipc_message_t message;session_zero(&message,sizeof(message));
    message.version=1;message.struct_size=140;message.length=sizeof(*c);
    session_bytes(message.payload,c,sizeof(*c));return (int)SESSION_S3(IPC_SEND_TIMEOUT,endpoint,&message,timeout);
}
static int service_receive(void *context,uint32_t endpoint,reist_session_control *c,unsigned timeout) {
    (void)context;x86os_ipc_message_t message;session_zero(&message,sizeof(message));
    message.version=1;message.struct_size=140;message.length=128;
    int result=(int)SESSION_S3(IPC_RECEIVE_TIMEOUT,endpoint,&message,timeout);if(result)return result;
    if(message.version!=1 || message.struct_size!=140 || message.length!=sizeof(*c))return -71;
    for(unsigned n=sizeof(*c);n<128;n++)if(message.payload[n])return -71;
    session_bytes(c,message.payload,sizeof(*c));return c->reserved?-71:0;
}
static const reist_service_session_ops session_ops={0,service_clock,service_endpoint,service_close,
    service_create,service_delegate,service_pio,service_send,service_receive,service_task};
static int session_rpc_remaining(unsigned timeout) {
    if(!session_operation_deadline || !timeout || timeout>1000)return -22;
    uint64_t now=session_now();if(now>=session_operation_deadline)return -110;
    uint64_t remaining=session_operation_deadline-now;
    return (int)(remaining<timeout?remaining:timeout);
}
static int session_fs_send(void *context,const x86os_ipc_bulk_message_t *q,unsigned timeout) {
    (void)context;int remaining=session_rpc_remaining(timeout);if(remaining<0)return remaining;
#ifdef REIST_NATIVE_NETWORK_SESSION
    /* Shared by service-image and ordinary foreground file capture. */
    if(remaining<=40)return -110;
    int paced=x86os_sleep_ms(40);if(paced)return paced;
    remaining=session_rpc_remaining(timeout);if(remaining<0)return remaining;
#endif
    return (int)SESSION_S3(IPC_SEND_TIMEOUT,session_service.filesystem_endpoint,q,(unsigned)remaining);
}
static int session_fs_receive(void *context,x86os_ipc_bulk_message_t *q,unsigned timeout) {
    (void)context;int remaining=session_rpc_remaining(timeout);if(remaining<0)return remaining;
    return (int)SESSION_S3(IPC_RECEIVE_TIMEOUT,session_service.filesystem_endpoint,q,(unsigned)remaining);
}
static const reist_fs_transport session_transport={0,service_clock,session_fs_send,session_fs_receive};
static int session_retire(void) {
#ifdef REIST_NATIVE_NETWORK_SESSION
    session_network_retire();
#endif
    int result=reist_service_session_retire(&session_service,&session_ops);
    session_zero(&session_observation,sizeof(session_observation));
    if(result)session_stop(result);
    return 0;
}
static int session_ensure(uint64_t deadline,int fresh_stat) {
    uint64_t now=session_now();
    if(now>=deadline)return -110;
    if(session_policy.degraded)return -11;
#ifdef REIST_NATIVE_APP_NETWORK
    /* A cached network launch can leave a sequence-zero filesystem whose
     * existing idle receive has expired. A new STAT requires a fresh capture
     * generation even when no earlier file request consumed its sequence. */
    if(fresh_stat && session_service.phase==REIST_SESSION_HEALTHY)session_retire();
#endif
    if(session_service.phase==REIST_SESSION_HEALTHY && (session_fs.failed ||
       session_fs.sequence>=REIST_FS_SESSION_REQUESTS || (fresh_stat && session_fs.sequence) ||
       session_service.deadline_ms<=now || session_service.deadline_ms-now<deadline-now))session_retire();
    if(session_service.phase==REIST_SESSION_HEALTHY)return 0;
    now=session_now();if(now>=deadline)return -110;
    if(session_failed) {
        int result=reist_session_policy_restart(&session_policy,now);if(result)return result;
    }
    unsigned fault=0;
    if(session_service.starts==1 || session_case==16)
        fault=session_case==7?5:session_case==8?6:session_case==9 || session_case==16?1:
            session_case==10?2:session_case==11?4:0;
#ifdef REIST_NATIVE_LARGE_FILE
    int result=reist_service_session_open_v3(&session_service,&session_ops,deadline,now+REIST_LARGE_FILE_MS,fault);
#elif defined(REIST_NATIVE_WIDE_FILE)
    int result=reist_service_session_open_v2(&session_service,&session_ops,deadline,now+REIST_WIDE_FILE_MS,fault);
#else
    int result=reist_service_session_open(&session_service,&session_ops,deadline,fault);
#endif
    if(result==-117)session_stop(result);
    if(result){if(result!=-11 && result!=-12)session_failed=1;return result;}
    result=reist_fs_client_bind(&session_fs,session_service.filesystem);
    if(result)session_stop(result);
    /* The real FS init self-test has validated its root on this immutable
     * medium. Cwd/drive metadata are observations, not live endpoint rights. */
    session_failed=0;session_sectors=session_service.sectors;session_mount=1;return 0;
}
static int session_operation_result(int result) {
    if(result<0 && session_fs.failed){session_failed=1;session_retire();}
    return result;
}
static int session_path(const char *path,char out[192]) {
    if(!path)return -22;
    unsigned length=0;while(length<192 && path[length])length++;
    if(!length || length==192)return -36;
    char joined[384];unsigned used=0;
    if(path[0]!='/' && path[0]!='\\') {
        /* Resolve only a candidate string here. An actual service request
         * must still validate it; no namespace success follows from joining. */
        for(unsigned n=0;session_cwd[n];n++)joined[used++]=session_cwd[n];
        joined[used++]='/';
    }
    for(unsigned n=0;n<length;n++)joined[used++]=path[n]=='\\'?'/':path[n];
    unsigned positions[96],depth=0,cursor=0,output=1;out[0]='/';
    while(cursor<used) {
        if(joined[cursor]=='/'){cursor++;continue;}
        unsigned begin=cursor;while(cursor<used && joined[cursor]!='/')cursor++;
        unsigned bytes=cursor-begin;
        if(bytes==1 && joined[begin]=='.')continue;
        if(bytes==2 && joined[begin]=='.' && joined[begin+1]=='.') {
            if(depth)output=positions[--depth];
            continue;
        }
        if(depth>=96 || output+(output>1)+bytes>=192)return -36;
        positions[depth++]=output;if(output>1)out[output++]='/';
        for(unsigned n=0;n<bytes;n++)out[output++]=joined[begin+n];
    }
    out[output]=0;return (int)output;
}
int x86os_monotonic_ms(uint64_t *out){if(!out)return -22;*out=session_now();return 0;}
int x86os_sleep_ms(uint32_t duration) {
    if(!duration || duration>100)return -22;
#ifdef REIST_NATIVE_APP_TCP
    /* A sampled CPU quota must not be consumed by waking on every tick just
     * to find an empty terminal. Only the immediate input-loop sleep is paced. */
    if(session_input_idle){session_input_idle=0;if(duration==10)duration=50;}
#endif
    (void)session_now();int64_t result=SESSION_S1(SLEEP_MS,duration);
    if(result)session_stop(-5);
    (void)session_now();return 0;
}
int x86os_getchar_nonblocking(void) {
#ifdef REIST_NATIVE_VGA_CONSOLE
    session_vga_poll(session_now());
#endif
#ifdef REIST_NATIVE_APP_TCP
    session_input_idle=0;
    uint64_t now=session_now();
#ifdef REIST_NATIVE_NETWORK_SESSION
    /* The health deadline cannot advance within one monotonic clock value.
     * Check once per value, retaining byte-at-a-time terminal ownership. */
    static uint64_t checked_ms=UINT64_MAX;
    if(now!=checked_ms){session_network_poll();now=session_policy.previous_ms;checked_ms=now;}
#endif
#else
#ifdef REIST_NATIVE_NETWORK_SESSION
    session_network_poll();
#endif
    uint64_t now=session_now();
#endif
    int result=reist_session_policy_charge(&session_policy,now,0,1,0);
    if(result)session_stop(result);
    unsigned char byte=0;int64_t status=SESSION_S3(READ,0,&byte,1);
    if(status==-11){session_flush();
#ifdef REIST_NATIVE_APP_TCP
        session_input_idle=1;
#endif
        return 0;}
    if(status!=1)session_stop(-5);
    return byte;
}
static void session_flush(void) {
    if(!session_output_used)return;
    int result=reist_session_policy_charge(&session_policy,session_now(),0,0,session_output_used);
    if(result)session_stop(result);
    uint32_t completed=0;result=reist_x64_console_write(session_output,session_output_used,1000,&completed);
    if(result || completed!=session_output_used)session_stop(result?result:-5);
    session_output_used=0;(void)session_now();
}
static void session_write(const char *text,unsigned bytes) {
#ifdef REIST_NATIVE_APP_TCP
    /* Private buffered bytes have no external side effect. The existing
     * flush checks the clock and byte quota before each <=64-byte write. */
    if(bytes>4096)session_stop(-22);
#else
    (void)session_now();
#endif
    for(unsigned n=0;n<bytes;n++) {
        session_output[session_output_used++]=text[n];
        if(session_output_used==64 || text[n]=='\n')session_flush();
    }
}
void x86os_putchar(char byte){session_write(&byte,1);}
void x86os_puts(const char *text) {
    if(!text)session_stop(-22);
    unsigned length=0;while(length<4096 && text[length])length++;
    if(length==4096)session_stop(-22);
    session_write(text,length);
}
void x86os_print_number(int value) {
    char text[12];unsigned length=0;uint32_t number=value<0?0U-(uint32_t)value:(uint32_t)value;
    do {text[length++]=(char)('0'+number%10);number/=10;}while(number);
    if(value<0)text[length++]='-';
    for(unsigned n=0;n<length/2;n++){char c=text[n];text[n]=text[length-n-1];text[length-n-1]=c;}
    session_write(text,length);
}
int x86os_terminal_input(uint32_t operation,int pid,uint32_t generation) {
#ifdef REIST_NATIVE_VIDEO_MODE
    /* As with the supervised desktop, COM1 remains the root recovery console;
     * the exact active renderer has no terminal-input capability. */
    if(session_video_active && session_child && operation==REIST_TERMINAL_TRANSFER &&
       (unsigned)pid==session_child>>32 && generation==(unsigned)pid)return 0;
#endif
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
    if(session_graphical_active && operation==REIST_TERMINAL_TRANSFER &&
       (unsigned)pid==session_child>>32 && generation==(unsigned)pid)return 0;
#endif
#ifdef REIST_NATIVE_TERMINAL_SERVICE
    if(operation==REIST_TERMINAL_TRANSFER && session_child &&
       (unsigned)pid==session_child>>32 && generation==(unsigned)pid &&
       session_input_service_pending) {
        if(session_terminal_service)session_stop(-5);
        if(reist_x64_terminal_service(6,session_input_service_pending)!=-13)session_stop(-5);
        int r=reist_x64_terminal_service(6,session_child);if(r)return r;
        session_terminal_service=session_child;
        if(reist_x64_terminal_service(6,session_child)!=-16 ||
           reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0)!=-11 ||
           reist_x64_syscall3(REIST_X64_SYS_READ,0,0,0)!=-11)session_stop(-5);
        if(session_previous_terminal_service &&
           reist_x64_terminal_service(7,session_previous_terminal_service)!=-116)session_stop(-5);
    }
#endif
    (void)session_now();return reist_x64_terminal_input(operation,pid,generation);
}
int x86os_process_identity_of(int pid,x86os_process_identity_t *out) {
    if(!out || pid<=0)return -22;
    x86os_process_identity_t result;
    int64_t status=reist_x64_syscall2(REIST_X64_SYS_PROCESS_IDENTITY,(uintptr_t)&result,(unsigned)pid);
    if(status)return status>=-4095 && status<0?(int)status:-5;
    if(result.version!=1 || result.struct_size!=16 || result.pid!=pid || result.generation!=(uint32_t)pid)return -5;
    session_bytes(out,&result,sizeof(result));return 0;
}
static void session_denied_identity(unsigned pid,int expected) {
    /* Check the actual ABI output, not an SDK cache or a fabricated liveness
     * result. This self-test grants nothing and never changes terminal state. */
    x86os_process_identity_t result={0xa5a5a5a5U,0xa5a5a5a5U,(int32_t)0xa5a5a5a5U,0xa5a5a5a5U};
    if(reist_x64_syscall2(REIST_X64_SYS_PROCESS_IDENTITY,(uintptr_t)&result,pid)!=expected)session_stop(-5);
    const unsigned char *bytes=(const void*)&result;
    for(unsigned n=0;n<sizeof(result);n++)if(bytes[n]!=0xa5)session_stop(-5);
}
static void session_authority_selftest(unsigned owner) {
    x86os_process_identity_t result;
    if(x86os_process_identity_of((int)owner,&result))session_stop(-5);
    /* The explicit two-root boot profile constructs the independent peer
     * immediately after root0, before either root enters userspace. */
    if(owner>=0x7fffffffU)session_stop(-5);
#ifdef REIST_NATIVE_TERMINAL_SERVICE
    reist_terminal_input_request_t service_request={1,24,6,0,(int)(owner+1),owner+1};
    if(reist_x64_syscall1(REIST_X64_SYS_TERMINAL_INPUT,(uintptr_t)&service_request)!=-13)session_stop(-5);
#endif
    session_denied_identity(owner+1,-13);
    if(reist_x64_terminal_input(REIST_TERMINAL_TRANSFER,(int)(owner+1),owner+1)!=-13 ||
       reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0))session_stop(-5);
}
int x86os_getcwd(char *out,size_t size) {
    if(!out || !size)return -22;
    if(!session_mount)return -5;
    unsigned length=0;while(session_cwd[length])length++;
    if(size<=length)return -34;
    session_bytes(out,session_cwd,length+1);return 0;
}
int reist_vfs_stat(const char *path,x86os_file_info_t *out,uint32_t timeout) {
    if(!out || !timeout || timeout>1000)return -22;
    char canonical[192];int length=session_path(path,canonical);if(length<0)return length;
    uint64_t deadline=session_now()+timeout;
#ifdef REIST_NATIVE_LARGE_FILE
    uint64_t capture_end=deadline-timeout+REIST_LARGE_FILE_MS;
#elif defined(REIST_NATIVE_WIDE_FILE)
    /* Establish the whole-file end before dependency startup or STAT. */
    uint64_t capture_end=deadline-timeout+REIST_WIDE_FILE_MS;
#endif
    int result=session_ensure(deadline,1);if(result)return result;
    uint64_t now=session_now();if(now>=deadline)return -110;
    reist_file_capture_v1 observation;
    if(session_operation_deadline)session_stop(-5);
    session_operation_deadline=deadline;
#ifdef REIST_NATIVE_LARGE_FILE
    if(capture_end>session_service.deadline_ms)capture_end=session_service.deadline_ms;
    result=reist_x64_file_stat_v3(&observation,&session_fs,&session_transport,canonical,(unsigned)length,capture_end);
#elif defined(REIST_NATIVE_WIDE_FILE)
    if(capture_end>session_service.deadline_ms)capture_end=session_service.deadline_ms;
    result=reist_x64_file_stat_v2(&observation,&session_fs,&session_transport,canonical,(unsigned)length,capture_end);
#else
    result=reist_x64_file_stat_v1(&observation,&session_fs,&session_transport,canonical,(unsigned)length,(unsigned)(deadline-now));
#endif
    session_operation_deadline=0;
    if(!result && session_now()>=deadline)result=-110;
    if(result)return session_operation_result(result);
    /* Relative-time SDK entrypoints must not replenish time spent constructing
     * dependencies. Narrow the ordinary observation to this operation's
     * original absolute end; later SPAWN capture inherits that same bound. */
#ifndef REIST_NATIVE_WIDE_FILE
    if(observation.deadline_ms>deadline)observation.deadline_ms=deadline;
#endif
    session_bytes(&session_observation,&observation,sizeof(observation));
    session_bytes(out,&observation.frame.stat.info,sizeof(*out));return 0;
}
int reist_vfs_readdir_at(const char *path,uint32_t index,x86os_file_info_t *out,uint32_t timeout) {
    if(!out || !timeout || timeout>1000)return -22;
    char canonical[192];int length=session_path(path,canonical);if(length<0)return length;
    uint64_t deadline=session_now()+timeout;int result=session_ensure(deadline,0);if(result)return result;
    reist_fs_frame frame;result=reist_fs_request_init(&frame,7,canonical,(unsigned)length,index,0);if(result)return result;
    uint64_t now=session_now();if(now>=deadline)return -110;
    if(session_operation_deadline)session_stop(-5);
    session_operation_deadline=deadline;
    result=reist_fs_call(&session_fs,&session_transport,&frame,(unsigned)(deadline-now));
    session_operation_deadline=0;
    if(result>=0 && session_now()>=deadline)result=-110;
    session_zero(&session_observation,sizeof(session_observation));
    if(result)return result==1?0:session_operation_result(result);
    session_bytes(out,&frame.directory.info,sizeof(*out));return 1;
}
int x86os_chdir(const char *path) {
    char canonical[192];int length=session_path(path,canonical);if(length<0)return length;
    x86os_file_info_t info;int result=reist_vfs_stat(canonical,&info,1000);if(result)return result;
    if(info.type!=X86OS_DIRECTORY)return -20;
    session_bytes(session_cwd,canonical,(unsigned)length+1);return 0;
}
int x86os_drive_info(uint32_t index,x86os_drive_info_t *out) {
    if(!out)return -22;
    if(!session_mount)return -5;
    if(index)return 0;
    x86os_drive_info_t info;session_zero(&info,sizeof(info));info.type=X86OS_DRIVE_ATA;
    session_bytes(info.name,"ata0",5);info.mount_point[0]='/';info.sectors=session_sectors;
    session_bytes(out,&info,sizeof(info));return 1;
}
#ifdef REIST_NATIVE_APP_FILES
#include "shell_app_files.inc"
#endif
#ifdef REIST_NATIVE_INPUT
#include "shell_input.inc"
#endif
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
#include "shell_graphical.inc"
#endif
int x86os_spawnv(const char *path,int argc,const char *const *argv) {
    if(session_child)return -16;
    if(argc<1 || argc>8 || !argv)return -22;
    char canonical[192];int length=session_path(path,canonical);if(length<0)return length;
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
    if(graphical.restart_blocked && session_app_equal(canonical,"/desktop.prg"))return -11;
#endif
    if(session_service.phase!=REIST_SESSION_HEALTHY || session_fs.failed)return -116;
    if(session_observation.version!=SESSION_CAPTURE_VERSION || session_observation.frame.stat.path_length!=(unsigned)length)return -116;
    for(int n=0;n<length;n++)if(session_observation.frame.stat.path[n]!=canonical[n])return -116;
    reist_task_startup_v1_t startup;int result=reist_x64_startup_init(&startup,(unsigned)argc,argv);if(result)return result;
    if(session_operation_deadline)session_stop(-5);
    session_operation_deadline=session_observation.deadline_ms;
#ifdef REIST_NATIVE_APP_FILES
    uint64_t app_capture_end=session_observation.deadline_ms;
#endif
    result=reist_x64_file_finish_v2(session_prepared,session_workspace,&session_fs,&session_transport,&session_observation);
    session_operation_deadline=0;
    session_zero(&session_observation,sizeof(session_observation));if(result)return session_operation_result(result);
#ifdef REIST_NATIVE_APP_NETWORK
    /* Cached role images can leave a fresh, sequence-zero FS alongside live
     * network slots4/5. Ordinary foreground programs retain their slot4 ABI. */
    if(!session_app_equal(canonical,"/udp.prg")
#ifdef REIST_NATIVE_APP_TCP
       &&!session_app_equal(canonical,"/nc.prg")
#ifdef REIST_NATIVE_APP_HTTP
       &&!session_app_equal(canonical,"/curl.prg")
#endif
#ifdef REIST_NATIVE_APP_DNS
       &&!session_app_equal(canonical,"/nslookup.prg")
#endif
#endif
       )session_network_retire();
#endif
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
    if(session_app_equal(canonical,"/desktop.prg")) {
        session_zero(&startup,sizeof(startup));
        int launched=session_graphical_start(argc,app_capture_end);
        session_zero(session_prepared,SESSION_PREPARED_BYTES);return launched;
    }
#endif
    reist_task_profile_v1_t profile={1,40,{SESSION_MASK|(1ULL<<15)|(1ULL<<20),1ULL<<63,0},0};
#ifdef REIST_NATIVE_VIDEO_MODE
    if(session_app_equal(canonical,"/video.prg")) {
        session_zero(&startup,sizeof(startup));
        return session_video_start(argc);
    }
#endif
#ifdef REIST_NATIVE_DISPLAY
    int display_program=session_app_equal(canonical,"/boot.prg");
    if(display_program)profile.masks[1]|=1ULL<<49;
#endif
#ifdef REIST_NATIVE_INPUT
    if(display_program) {
        result=session_input_arguments(argc,argv,&startup,&profile);
        if(result){session_zero(session_prepared,SESSION_PREPARED_BYTES);session_zero(&startup,sizeof(startup));return result;}
    }
#endif
#ifdef REIST_NATIVE_APP_FILES
#ifdef REIST_NATIVE_APP_NETWORK
#ifdef REIST_NATIVE_APP_DNS
    session_dns_selected=session_app_equal(canonical,"/nslookup.prg");
#ifdef REIST_NATIVE_APP_HTTP
    session_http_selected=session_app_equal(canonical,"/curl.prg");
#endif
#endif
    int64_t child=
#ifdef REIST_NATIVE_APP_HTTP
        session_http_selected?session_tcp_import(argc,argv,&startup,&profile):
#endif
#ifdef REIST_NATIVE_APP_DNS
        session_dns_selected?session_tcp_import(argc,argv,&startup,&profile):
#endif
#ifdef REIST_NATIVE_APP_TCP
        session_app_equal(canonical,"/nc.prg")?session_tcp_import(argc,argv,&startup,&profile):
#endif
        session_app_equal(canonical,"/udp.prg")?
        session_udp_import(argc,argv,&startup,&profile):
        session_app_import(canonical,argc,argv,app_capture_end,&startup,&profile);
#else
    int64_t child=session_app_import(canonical,argc,argv,app_capture_end,&startup,&profile);
#endif
#else
    int64_t child=reist_x64_task_import_wide(session_prepared,&profile,32,&startup);
#endif
    session_zero(session_prepared,SESSION_PREPARED_BYTES);session_zero(&startup,sizeof(startup));
    if(child<-4095)session_stop(-5);
#ifdef REIST_NATIVE_INPUT
    if(child<0)session_input_retire();
#endif
    if(child<0)return (int)child;
#ifdef REIST_NATIVE_APP_NETWORK
    if(!child || (uint32_t)child!=((session_udp_active
#ifdef REIST_NATIVE_APP_TCP
        ||session_tcp_active
#endif
        )?6U:4U) || (uint64_t)child>>32>0x7fffffff)session_stop(-5);
#else
    if(!child || (uint32_t)child!=SESSION_APPLICATION_SLOT || (uint64_t)child>>32>0x7fffffff)session_stop(-5);
#endif
#ifdef REIST_NATIVE_DISPLAY
    if(display_program) {
        reist_display_request_v1 request;session_zero(&request,sizeof(request));
        request.version=1;request.size=64;request.operation=REIST_DISPLAY_BIND;
        request.owner=(uint64_t)child;
        int64_t bound=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&request);
        if(bound<=0) {
#ifdef REIST_NATIVE_INPUT
            session_input_retire();
#endif
            if(service_task(0,3,(uint64_t)child,0))session_stop(-5);
            int64_t retired=service_task(0,2,(uint64_t)child,1000);
            if(retired<0 || (uint64_t)retired>>32>3)session_stop(-5);
            return bound>=-4095 && bound<0?(int)bound:-5;
        }
    }
#endif
#ifdef REIST_NATIVE_INPUT
    if(display_program && (result=session_input_start((uint64_t)child))) {
        session_input_retire();
        if(service_task(0,3,(uint64_t)child,0))session_stop(-5);
        int64_t retired=service_task(0,2,(uint64_t)child,1000);
        if(retired<0 || (uint64_t)retired>>32>3)session_stop(-5);
        return result;
    }
#endif
    session_child=(uint64_t)child;
    if(session_case==15) {
        /* Owner-loss qualification includes an actually entered foreground
         * process. Yield once through the existing bounded blocking sleep;
         * the child still has no terminal lease and must wait for authority. */
        if(SESSION_S1(SLEEP_MS,10))session_stop(-5);
        __asm__ volatile("ud2");
    }
    return (int)(session_child>>32);
}
int x86os_kill(int pid) {
    if(pid<=0 || !session_child || (uint32_t)pid!=session_child>>32)return -3;
#ifdef REIST_NATIVE_VIDEO_MODE
    if(session_video_active)return video_stop(0);
#endif
#ifdef REIST_NATIVE_APP_TCP
    if(session_tcp_active)session_tcp_revoke();
#endif
#ifdef REIST_NATIVE_APP_NETWORK
    if(session_udp_active)session_udp_revoke();
#endif
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
    if(session_graphical_active)return session_graphical_kill();
#endif
    int64_t result=service_task(0,3,session_child,0);return result>=-4095 && result<=0?(int)result:-5;
}
int x86os_wait(int pid,int *out) {
    if(!out || pid<=0)return -22;
    if(!session_child || (uint32_t)pid!=session_child>>32)return -3;
#ifdef REIST_NATIVE_VIDEO_MODE
    if(session_video_active)return session_video_wait(out);
#endif
#ifdef REIST_NATIVE_GRAPHICAL_SESSION
    if(session_graphical_active)return session_graphical_wait(out);
#endif
#ifdef REIST_NATIVE_APP_FILES
    int timed_out=0;
#ifdef REIST_NATIVE_INPUT
    int64_t result=session_input_end?session_input_wait(session_child):
        session_app_request?session_app_wait(&timed_out):service_task(0,2,session_child,1000);
#else
#ifdef REIST_NATIVE_APP_NETWORK
    int64_t result=
#ifdef REIST_NATIVE_APP_TCP
        session_tcp_active?session_tcp_wait(&timed_out):
#endif
        session_udp_active?session_udp_wait(&timed_out):
        session_app_request?session_app_wait(&timed_out):service_task(0,2,session_child,1000);
#else
    int64_t result=session_app_request?session_app_wait(&timed_out):service_task(0,2,session_child,1000);
#endif
#endif
    if(result==-110)timed_out=1;
    if(result==-110){if(service_task(0,3,session_child,0))session_stop(-5);result=service_task(0,2,session_child,1000);}
#else
    int64_t result=service_task(0,2,session_child,1000);int timed_out=result==-110;
    if(timed_out){if(service_task(0,3,session_child,0))session_stop(-5);result=service_task(0,2,session_child,1000);}
#endif
    if(result<0 || (uint64_t)result>>32>3)session_stop(-5);
#ifdef REIST_NATIVE_INPUT
    session_input_retire();
#endif
    session_child=0;
    if(reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0))session_stop(-5);
    session_denied_identity((unsigned)pid,-3);
    if(reist_x64_terminal_input(REIST_TERMINAL_TRANSFER,pid,(unsigned)pid)!=-116)session_stop(-5);
    session_retire();if(timed_out)return -110;
    *out=(int)(uint32_t)result;return 0;
}
int x86os_usb_diagnostics(x86os_usb_diagnostics_t *out){(void)out;return -38;}
#ifdef REIST_NATIVE_NETWORK_SESSION
#include "shell_network.inc"
#ifdef REIST_NATIVE_APP_NETWORK
#include "shell_application_udp.inc"
#ifdef REIST_NATIVE_APP_TCP
#include "shell_application_tcp.inc"
#endif
#endif
#else
int x86os_network_control(const x86os_network_control_request_t *q,x86os_network_control_result_t *out){(void)q;(void)out;return -38;}
#endif
extern int __real_main(int,char **);
#ifdef REIST_NATIVE_VGA_CONSOLE
#include "shell_vga_console.inc"
#ifdef REIST_NATIVE_VIDEO_MODE
#include "shell_video_mode.inc"
#endif
#endif
int __wrap_main(int argc,char **argv) {
    if(reist_shell_session_selection[0]!=0x3153455353484c53ULL || reist_shell_session_selection[1]!=1 ||
       reist_shell_session_selection[2]>4 || reist_shell_session_selection[3]>17)session_stop(-22);
    unsigned selected_case=(unsigned)reist_shell_session_selection[3];
    int64_t owner=SESSION_S0(GETPID),now=SESSION_S0(MONOTONIC_MS);
    if(owner<=0 || now<0 || reist_session_policy_init(&session_policy,(uint64_t)owner,(uint64_t)now) ||
       reist_service_session_init(&session_service,(uint64_t)owner,(unsigned)reist_shell_session_selection[2]))session_stop(-5);
    session_authority_selftest((unsigned)owner);
    session_prepared=(void*)(uintptr_t)SESSION_S1(MALLOC,SESSION_PREPARED_BYTES);
    session_workspace=(void*)(uintptr_t)SESSION_S1(MALLOC,sizeof(*session_workspace));
    if((intptr_t)session_prepared<=0 || (intptr_t)session_workspace<=0)session_stop(-5);
    x86os_file_info_t root;
    int mounted=reist_vfs_stat("/",&root,1000);
    if(!mounted && root.type==X86OS_DIRECTORY) {
        session_mount=1;
        /* Exercise the real directory adapter during namespace startup, too.
         * A failed RPC follows its ordinary isolation path; it is not turned
         * into a successful directory entry or a synthetic empty directory. */
        x86os_file_info_t first;
        (void)reist_vfs_readdir_at("/",0,&first,1000);
    }
#ifdef REIST_NATIVE_VGA_CONSOLE
    uint64_t vga_end=session_now()+2000;
    int vga_result=session_ensure(vga_end-1000,0);
    if(!vga_result)vga_result=session_vga_start(vga_end);
    if(vga_result)session_vga_disabled=1;
#endif
    session_retire();
    /* First mount/self-test is healthy. Qualification faults belong to the
     * following actual command/file transaction, not a cached root STAT that
     * can retire a fault fixture without ever exercising its failing path. */
    session_case=selected_case;
    int result=__real_main(argc,argv);
    session_flush();session_retire();
#ifdef REIST_NATIVE_VGA_CONSOLE
    session_vga_retire();
#endif
#ifdef REIST_NATIVE_NETWORK_SESSION
    session_network_free();
#endif
#ifdef REIST_NATIVE_INPUT
    if(session_input_driver||session_input_endpoint||session_input_ingress||session_input_epoch||session_input_end)session_stop(-5);
#endif
    if(session_child)session_stop(-5);
    session_zero(session_prepared,SESSION_PREPARED_BYTES);session_zero(session_workspace,sizeof(*session_workspace));
    if(SESSION_S1(FREE,session_prepared) || SESSION_S1(FREE,session_workspace))session_stop(-5);
    return result;
}
