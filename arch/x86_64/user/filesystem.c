/* Explicit native FS qualification consumer: supervisor, peer, driver, parser. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#include <reist/x86_64/filesystem.h>
#include "../../../userspace/drivers/ata/native_service.h"
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define REQUIRE(v,e) do { if(!(v)) return (e); } while(0)
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define CONTENT "REIST NATIVE FILESYSTEM\n"
typedef struct {
    uint64_t owner,peer,deadline;
    uint32_t request,reply,sectors,phase;
    int32_t result; uint32_t reserved;
} Control;
#if PROGRAM_ID!=1
static uint32_t control_ep;
static unsigned mode;
#ifdef REIST_NATIVE_LIVE_FILE
#undef FILESYSTEM_LAYOUT
static unsigned live_layout;
#define FILESYSTEM_LAYOUT live_layout
#endif
#if PROGRAM_ID!=0
static uint32_t request_ep,reply_ep;
static uint64_t self;
#endif
static void zero(void *p,unsigned n) { unsigned char *b=p; while(n--) *b++=0; }
static void copy(void *p,const void *q,unsigned n) { unsigned char *a=p;const unsigned char *b=q;while(n--) *a++=*b++; }
static uint64_t now(void *p) { (void)p; return (uint64_t)S0(MONOTONIC_MS); }
static int control_send(uint32_t ep,const Control *c) {
    x86os_ipc_message_t m; zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=sizeof(*c);
    copy(m.payload,c,sizeof(*c)); return (int)S3(IPC_SEND_TIMEOUT,ep,&m,1000);
}
static int control_receive(uint32_t ep,Control *c) {
    x86os_ipc_message_t m;zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=128;
    int r=(int)S3(IPC_RECEIVE_TIMEOUT,ep,&m,1000);if(r) return r;
    if(m.length!=sizeof(*c)) return -71;copy(c,m.payload,sizeof(*c));return c->reserved?-71:0;
}
#if PROGRAM_ID==0
static int64_t port_control(uint64_t owner,unsigned operation) {
    reist_native_pio_request q={1,64,operation,0,owner,0,0,0,0,0,0,0};return reist_x64_pio(&q);
}
#endif
#if PROGRAM_ID==0
static void number(char *s,uint32_t n) {
    for(unsigned i=0;i<8;i++) s[i]="0123456789abcdef"[(n>>(28-4*i))&15];s[8]=0;
}
static int64_t task_control(unsigned op,uint64_t owner,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,owner,0,timeout,0,0,0};return reist_x64_task_control(&q);
}
static uint32_t driver_control;
#ifndef REIST_FILE_LAUNCH
static reist_fs_frame frame;
static volatile reist_fs_frame filesystem_result_snapshot;
static volatile uint64_t filesystem_result_record[7] __attribute__((used));
static void witness(reist_fs_client *c,unsigned operation,int result) {
    /* Single-outstanding-call snapshot. The next real IPC boundary precedes
     * its overwrite; no extra syscall, clock, authority or queue is needed. */
    for(unsigned n=0;n<512;n++) filesystem_result_snapshot.bytes[n]=frame.bytes[n];
    filesystem_result_record[1]=c->owner;filesystem_result_record[2]=c->sequence;
    filesystem_result_record[3]=operation;filesystem_result_record[4]=(uint64_t)(int64_t)result;
    filesystem_result_record[5]=(uintptr_t)&filesystem_result_snapshot;filesystem_result_record[6]=mode;
    filesystem_result_record[0]=0x4e46535250435631ULL;
}
#endif
static int fs_send(void *p,const x86os_ipc_bulk_message_t *m,unsigned timeout) {
    (void)p;return (int)S3(IPC_SEND_TIMEOUT,control_ep,m,timeout);
}
static int fs_receive(void *p,x86os_ipc_bulk_message_t *m,unsigned timeout) {
    (void)p;return (int)S3(IPC_RECEIVE_TIMEOUT,control_ep,m,timeout);
}
static int64_t create(void *record,unsigned slot,unsigned options,uint32_t ep) {
    char channel[9],option[9];number(channel,ep);number(option,options);
    const char *args[]={channel,option};reist_task_startup_v1_t startup;
    if(reist_x64_startup_init(&startup,2,args)) return -22;
    const unsigned char *blob=slot==2?import_blob:filesystem_blob;
    unsigned size=slot==2?sizeof(import_blob):sizeof(filesystem_blob);
    if(reist_x64_image_prepare_v2(record,blob,size)) return -22;
    reist_task_profile_v1_t profile={1,40,{MASK,slot==2?1ULL<<49:0,0},0};
#ifdef REIST_NATIVE_LIVE_FILE
    int64_t child=reist_x64_task_import_periodic(record,&profile,32,1000,&startup);
#else
    int64_t child=reist_x64_task_import_wide(record,&profile,32,&startup);
#endif
#if FILESYSTEM_CASE==7
    if(slot==3 && !options) {
        if(child!=-12) return -22;
        child=reist_x64_task_import_wide(record,&profile,32,&startup);
    }
#endif
    if(child<=0 || (uint32_t)child!=slot) return -22;
    typedef uint64_t word __attribute__((may_alias,aligned(1)));
    for(unsigned n=0;n<REIST_X64_PREPARED_V2_BYTES/8;n++) ((volatile word*)record)[n]=0x5a5a5a5a5a5a5a5aULL;
    if(S3(IPC_DELEGATE,ep,(uint64_t)child>>32,3)) return -13;
    return child;
}
#else
static uint32_t number(const char *s) {
    uint32_t n=0;for(unsigned i=0;i<8;i++) {
        unsigned c=(unsigned char)s[i];if(c>='0'&&c<='9') c-='0';else if(c>='a'&&c<='f') c=c-'a'+10;else return 0;
        n=(n<<4)|c;
    }return s[8]?0:n;
}
static int startup(Control *c) {
    for(unsigned n=0;n<20;n++) {
        /* The child may run before the root's one atomic capability grant.
         * EBADF means no local handle yet; EACCES is a real rights failure. */
        int r=control_receive(control_ep,c);if(r!=-9) return r;
        if(S1(SLEEP_MS,10)) return -5;
    }return -110;
}
#endif
#ifdef REIST_NATIVE_LIVE_FILE
#if PROGRAM_ID!=0
static int live_options(const char *s) {
    for(unsigned n=0;n<8;n++)
        if(!((s[n]>='0' && s[n]<='9') || (s[n]>='a' && s[n]<='f'))) return -22;
    uint32_t value=number(s);
    if(s[8] || value&~0x71fU || (value&15)>7 || (value>>8)>4) return -22;
    mode=value&15;live_layout=value>>8;return 0;
}
#endif
#endif
#if PROGRAM_ID==2
static reist_native_profile_service filesystem_block_service;
static unsigned reads,chunks;
static int sleep_ms(void *p,unsigned ms) { (void)p; return (int)S1(SLEEP_MS,ms); }
static int64_t port(void *p,reist_native_pio_request *q) {
    (void)p;int64_t result=reist_x64_pio(q);
    if(!result && q->operation==REIST_PIO_WRITE8 && q->port==0x1f7 && q->value==0x20) { reads++;chunks=0; }
    if(!result && reads==2 && q->operation==REIST_PIO_READ16 && ++chunks==8) {
        if(mode==5) __asm__ volatile("ud2");
#ifdef REIST_NATIVE_LIVE_FILE
        if(mode==6 || mode==7) {
#else
        if(mode==6) {
#endif
            Control c={self,0,0,0,0,0,9,0,0};if(control_send(control_ep,&c)) return -5;
#ifdef REIST_NATIVE_LIVE_FILE
            if(mode==7) for(;;) __asm__ volatile("pause");
#endif
            for(unsigned n=0;n<20;n++) if(S1(SLEEP_MS,100)) return -5;
            return -110;
        }
    }return result;
}
#elif PROGRAM_ID==3
static reist_fs_server filesystem_service;
static unsigned exercising;
static int block_send(void *p,const x86os_ipc_message_t *q,unsigned timeout) {
    (void)p;return (int)S3(IPC_SEND_TIMEOUT,request_ep,q,timeout);
}
static int block_receive(void *p,x86os_ipc_bulk_message_t *q,unsigned timeout) {
    (void)p;int r=(int)S3(IPC_RECEIVE_TIMEOUT,reply_ep,q,timeout);
    if(!r && exercising) {
        if(mode==1) __asm__ volatile("ud2");
        if(mode==2) { for(unsigned n=0;n<20;n++) if(S1(SLEEP_MS,100)) return -5;return -110; }
        if(mode==3) for(;;) __asm__ volatile("pause");
    }return r;
}
#endif
#endif
#if !defined(REIST_FILE_LAUNCH) || PROGRAM_ID!=0
int main(int argc,char **argv,char **envp) {
    REQUIRE(argc==2 && !argv[2] && !envp[0],200);
#if PROGRAM_ID==0
    REQUIRE(argv[1][0]=='0',201);
    void *record=(void *)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    REQUIRE((intptr_t)record>0,202);
    reist_fs_client client={0};reist_fs_transport transport={0,now,fs_send,fs_receive};
    const char *path=FILESYSTEM_LAYOUT<2?"/README.TXT":"/readme.txt";
    uint64_t previous_fs=0,previous_driver=0;
    for(unsigned round=0;round<2;round++) {
        mode=round?0:FILESYSTEM_CASE;
        if(mode==7) mode=0;
        REQUIRE(!S1(IPC_CREATE,&driver_control) && !S1(IPC_CREATE,&control_ep),203);
        int64_t driver=create(record,2,mode|(round?16:0),driver_control);
        int64_t fs=create(record,3,mode|(round?16:0),control_ep);
        REQUIRE(driver>0 && fs>0 && (uint64_t)driver>previous_driver && (uint64_t)fs>previous_fs,204);
        REQUIRE(!port_control(driver,REIST_PIO_BIND),205);
        if(previous_driver) REQUIRE(port_control(previous_driver,REIST_PIO_FENCE)==-13,206);
        Control c={driver,fs,0,0,0,0,1,0,0};
        REQUIRE(!control_send(driver_control,&c) && !control_receive(driver_control,&c),207);
        REQUIRE(c.owner==(uint64_t)driver && c.peer==(uint64_t)fs && c.phase==2 && !c.result && c.request && c.reply,208);
        REQUIRE(c.sectors==(FILESYSTEM_LAYOUT==0?2880:FILESYSTEM_LAYOUT==1?70000:256),209);
        c.owner=fs;c.peer=driver;c.phase=3;
        REQUIRE(!control_send(control_ep,&c),210);
        if(mode==6) {
            REQUIRE(!control_receive(driver_control,&c) && c.owner==(uint64_t)driver && c.phase==9,211);
            __asm__ volatile("ud2");
        }
        REQUIRE(!control_receive(control_ep,&c) && c.owner==(uint64_t)fs && c.peer==(uint64_t)driver && c.phase==4,212);
        int failed_init=mode==5 || FILESYSTEM_CASE==8;
        if(failed_init) REQUIRE(c.result<0,213);
        else {
            REQUIRE(!c.result && !reist_fs_client_bind(&client,fs),214);
            for(unsigned n=0;n<(mode?1:9);n++) {
                unsigned op=n==1 || n>=6?5:n==2 || n==5?7:6;
                unsigned pos=n==3?5:n==4?0xffffffffU:n==5?1:0;
                const char *name=op==7?"/":n==6?"/absent":path;
                unsigned length=op==7?1:n==6?7:11;
                REQUIRE(!reist_fs_request_init(&frame,op,name,length,pos,op==6?(n==3?5:256):0),215);
                reist_fs_frame unchanged;copy(&unchanged,&frame,512);
                int result=reist_fs_call(&client,&transport,&frame,1800);
                witness(&client,op,result);
                int expected=n==5?1:n==6?-2:n==8?-11:0;
                if(mode) REQUIRE(mode==4?result==-71:result==-32 || result==-110,216);
                else REQUIRE(result==expected,217);
                if(result<0) {
                    const uint8_t *a=frame.bytes,*b=unchanged.bytes;
                    for(unsigned k=0;k<512;k++) REQUIRE(a[k]==b[k],218);
                } else if(op==6) {
                    unsigned amount=n==3?5:n==4?0:sizeof(CONTENT)-1;
                    REQUIRE(frame.read.transferred==amount,219);
                    for(unsigned k=0;k<256;k++) REQUIRE(frame.read.data[k]==(k<amount?(unsigned char)CONTENT[k+(n==3?5:0)]:0),220);
                } else if(!result) REQUIRE((op==5?frame.stat.info.size:frame.directory.info.size)==sizeof(CONTENT)-1,221);
            }
        }
        /* Same state machine for normal retirement, fault and timeout. Fence
         * outputs before cancelling either dependent; WAIT performs reap. */
        REQUIRE(!port_control(driver,REIST_PIO_FENCE),222);
        if(mode==2 || mode==4) REQUIRE(!task_control(3,fs,0),223);
        int64_t fs_expected=failed_init?90:mode==1?((1LL<<32)|134):mode==2||mode==4?(2LL<<32):mode==3?((1LL<<32)|256):80;
        REQUIRE(task_control(2,fs,1000)==fs_expected,224);
        REQUIRE(!task_control(3,driver,0),225);
        REQUIRE(task_control(2,driver,1000)==(mode==5?((1LL<<32)|134):(2LL<<32)),226);
        REQUIRE(!port_control(driver,REIST_PIO_FENCE) && task_control(2,fs,1)==-10 && task_control(2,driver,1)==-10,227);
        if(previous_fs) {
            REQUIRE(task_control(2,previous_fs,1)==-10,228);
            if(client.owner) REQUIRE(reist_fs_client_bind(&client,previous_fs)==-22,228);
        }
        REQUIRE(!S1(IPC_CLOSE,control_ep) && !S1(IPC_CLOSE,driver_control),229);
        previous_driver=driver;previous_fs=fs;
    }
    return FILESYSTEM_CASE==8?81:78;
#elif PROGRAM_ID==1
    REQUIRE(argv[1][0]=='1',230);
    REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,231);
    for(unsigned n=0;n<45;n++) REQUIRE(!S1(SLEEP_MS,100),232);
    return 77;
#elif PROGRAM_ID==2
    control_ep=number(argv[0]);mode=number(argv[1])&15;self=((uint64_t)S0(GETPID)<<32)|2;
#ifdef REIST_NATIVE_LIVE_FILE
    REQUIRE(!live_options(argv[1]),248);
#endif
    Control c;REQUIRE(control_ep && !startup(&c) && c.owner==self && (uint32_t)c.peer==3 && c.phase==1,233);
    REQUIRE(!S1(IPC_CREATE,&request_ep) && !S1(IPC_CREATE,&reply_ep),234);
    REQUIRE(!S3(IPC_DELEGATE,request_ep,c.peer>>32,1) && !S3(IPC_DELEGATE,reply_ep,c.peer>>32,2),235);
    reist_pio_ops ops={0,port,now,sleep_ms};
    reist_block_profile_v1 profile={1,24,16,0,now(0)+2800};
    REQUIRE(!reist_native_service_init_profile(&filesystem_block_service,self,&ops,&profile),236);
    c.deadline=profile.deadline_ms;c.request=request_ep;c.reply=reply_ep;c.sectors=filesystem_block_service.service.server.capacity;c.phase=2;
    REQUIRE(!control_send(control_ep,&c),237);
    for(unsigned n=0;n<17;n++) {
        x86os_ipc_message_t q;zero(&q,sizeof(q));q.version=1;q.struct_size=140;q.length=128;
        int result=(int)S3(IPC_RECEIVE_TIMEOUT,request_ep,&q,1000);
        if(result==-32 || result==-110) { REQUIRE(!S1(SLEEP_MS,100),238); continue; }
        REQUIRE(!result,239);
        x86os_ipc_bulk_message_t reply;
        (void)reist_native_service_dispatch_profile(&filesystem_block_service,&q,&reply);
        REQUIRE(!S3(IPC_SEND_TIMEOUT,reply_ep,&reply,1000),240);
    }
    return 241;
#else
    control_ep=number(argv[0]);mode=number(argv[1])&15;self=((uint64_t)S0(GETPID)<<32)|3;
#ifdef REIST_NATIVE_LIVE_FILE
    REQUIRE(!live_options(argv[1]),248);
#endif
    Control c;REQUIRE(control_ep && !startup(&c) && c.owner==self && (uint32_t)c.peer==2 && c.phase==3,242);
    REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,243);
    request_ep=c.request;reply_ep=c.reply;
    reist_block_transport transport={0,now,block_send,block_receive};
    reist_fs_profile_v1 profile={1,40,FILESYSTEM_LAYOUT<2?REIST_FS_FAT:REIST_FS_EXT2,c.sectors,self,c.peer,c.deadline};
    int result=reist_fs_server_init(&filesystem_service,&profile,&transport);
    c.phase=4;c.result=result;REQUIRE(!control_send(control_ep,&c),244);
    if(result) return 90;
    exercising=1;
    for(unsigned n=0;n<9;n++) {
        x86os_ipc_bulk_message_t q,reply;zero(&q,sizeof(q));q.version=2;q.struct_size=sizeof(q);q.length=2048;
        REQUIRE(!S3(IPC_RECEIVE_TIMEOUT,control_ep,&q,1000),245);
        (void)reist_fs_dispatch(&filesystem_service,&q,&reply);
        if(mode==4) reply.payload[16]^=1;
        REQUIRE(!S3(IPC_SEND_TIMEOUT,control_ep,&reply,1000),246);
    }
    REQUIRE(!reist_fs_server_fence(&filesystem_service),247);return 80;
#endif
}
#endif
