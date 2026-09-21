/* Native normal-tool SDK adapter over an explicit immutable object grant. */
#include <reist/x86_64/app_files.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/terminal.h>
#include <reist/vfs_file_client.h>
#include <reist/vfs_read_client.h>
#include <reist/vfs_stat_client.h>
#ifdef REIST_APP_HOST_TEST
extern int64_t app_host_call(unsigned,uint64_t,uint64_t,uint64_t);
#define CALL(n,a,b,c) app_host_call(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#else
#define CALL(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#endif
static uint32_t app_request,app_reply,app_offset,app_opened,app_closed;
static uint64_t app_root,app_child,app_epoch,app_sequence,app_end,app_previous;
static unsigned app_failed,app_output_used,app_output_total,app_input_total,app_operations;
static char app_path[128],app_output[64];
static x86os_file_info_t app_info;
static void bytes(void *to,const void *from,size_t n) {
    volatile unsigned char *a=to;const unsigned char *b=from;for(size_t i=0;i<n;i++)a[i]=b[i];
}
static void zero(void *p,size_t n) {volatile unsigned char *b=p;while(n--)*b++=0;}
static int empty(const void *p,size_t n) {const unsigned char *b=p;while(n--)if(*b++)return 0;return 1;}
static int info_valid(const x86os_file_info_t *p) {
    if(p->type!=X86OS_FILE && p->type!=X86OS_DIRECTORY)return 0;
    unsigned n=0;while(n<256 && p->name[n])n++;
    return n && n<256 && empty(p->name+n,256-n);
}
static int clock_read(uint64_t *out) {
    int64_t now=CALL(MONOTONIC_MS,0,0,0);
    if(now<0 || (uint64_t)now<app_previous){app_failed=1;return -84;}
    if(++app_operations>4096 || (uint64_t)now>=app_end){app_failed=1;return -110;}
    app_previous=(uint64_t)now;*out=(uint64_t)now;return 0;
}
static int remaining(void) {
    uint64_t now;int r=clock_read(&now);if(r)return r;
    return (int)(app_end-now>1000?1000:app_end-now);
}
static _Noreturn void stop(int error) {
    (void)CALL(EXIT,error==-110?110:5,0,0);__builtin_trap();
}
static int until(uint64_t end) {
    uint64_t now;int r=clock_read(&now);if(r)return r;
    if(now>=end){app_failed=1;return -110;}
    return (int)(end-now);
}
static int transact(unsigned operation,uint32_t offset,uint32_t requested,unsigned timeout,reist_app_frame *out) {
    if(!timeout || timeout>1000)return -22;
    if(app_failed || app_closed || !app_request || !app_reply)return -116;
    if(app_sequence==REIST_APP_REQUESTS)return -110;
    uint64_t start;int stamp=clock_read(&start);if(stamp)return stamp;
    uint64_t end=start+timeout;if(end>app_end)end=app_end;
    reist_app_frame q;zero(&q,sizeof(q));q.version=1;q.size=512;q.operation=operation;
    q.child=app_child;q.sequence=app_sequence+1;q.offset=offset;q.requested=requested;
    if(operation!=REIST_APP_HELLO){q.root=app_root;q.epoch=app_epoch;q.deadline=app_end;}
    x86os_ipc_bulk_message_t message;zero(&message,sizeof(message));
    message.version=2;message.struct_size=sizeof(message);message.length=512;
    bytes(message.payload,&q,512);
    int wait=until(end);if(wait<0)return wait;
    int result=(int)CALL(IPC_SEND_TIMEOUT,app_request,&message,(unsigned)wait);
    if(result){app_failed=1;return result;}
    zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=2048;
    wait=until(end);if(wait<0)return wait;
    result=(int)CALL(IPC_RECEIVE_TIMEOUT,app_reply,&message,(unsigned)wait);
    if(result){app_failed=1;return result;}
    wait=until(end);if(wait<0)return wait;
    reist_app_frame r;bytes(&r,message.payload,512);
    if(message.version!=2 || message.struct_size!=sizeof(message) || message.length!=512 ||
       !empty(message.payload+512,1536) || r.version!=1 || r.size!=512 || r.flags!=1 ||
       r.operation!=operation || r.child!=app_child || r.sequence!=q.sequence ||
       r.offset!=offset || r.requested!=requested || r.reserved || r.length>sizeof(r.payload))goto bad;
    if(operation==REIST_APP_HELLO) {
        if(!r.root || r.root>=app_child || !r.epoch || r.deadline<=app_previous || r.deadline>app_end)goto bad;
    } else if(r.root!=app_root || r.epoch!=app_epoch || r.deadline!=app_end)goto bad;
    if(operation==REIST_APP_HELLO || operation==REIST_APP_STAT || (operation==REIST_APP_READDIR && r.status==1)) {
        x86os_file_info_t info;bytes(&info,r.payload,sizeof(info));
        if(r.length!=sizeof(info) || !info_valid(&info) ||
           r.status!=(operation==REIST_APP_READDIR?1:0))goto bad;
        if(operation!=REIST_APP_READDIR && info.type==X86OS_FILE && info.size>REIST_APP_BYTES)goto bad;
        if(operation==REIST_APP_STAT) {
            const unsigned char *old=(const void*)&app_info;
            for(unsigned n=0;n<sizeof(info);n++)if(r.payload[n]!=old[n])goto bad;
        }
    } else if(operation==REIST_APP_READ) {
        if(app_info.type!=X86OS_FILE || offset>app_info.size)goto bad;
        unsigned expected=app_info.size-offset;if(expected>requested)expected=requested;
        if(r.status || r.length!=expected || r.length>256)goto bad;
    } else if(r.status || r.length)goto bad;
    if(!empty(r.payload+r.length,sizeof(r.payload)-r.length))goto bad;
    app_root=r.root;app_epoch=r.epoch;app_end=r.deadline;app_sequence=r.sequence;
    if(operation==REIST_APP_HELLO)bytes(&app_info,r.payload,sizeof(app_info));
    if(operation==REIST_APP_CLOSE)app_closed=1;
    bytes(out,&r,512);return 0;
bad:
    app_failed=1;return -71;
}
static int selected(const char *path) {
    if(!path || !app_path[0])return 0;
    for(unsigned n=0;n<128;n++){if(path[n]!=app_path[n])return 0;if(!path[n])return 1;}return 0;
}
int reist_vfs_stat(const char *path,x86os_file_info_t *out,uint32_t timeout) {
    if(!out || !timeout || timeout>1000)return -22;
    if(!selected(path))return -13;
    reist_app_frame r;int result=transact(REIST_APP_STAT,0,0,timeout,&r);
    if(!result)bytes(out,r.payload,sizeof(*out));
    return result;
}
int reist_vfs_readdir_at(const char *path,uint32_t index,x86os_file_info_t *out,uint32_t timeout) {
    if(!out || !timeout || timeout>1000)return -22;
    if(!selected(path))return -13;
    reist_app_frame r;int result=transact(REIST_APP_READDIR,index,0,timeout,&r);
    if(result)return result;
    if(r.status)bytes(out,r.payload,sizeof(*out));
    return r.status;
}
int reist_vfs_read_at(const char *path,uint32_t offset,void *out,size_t size,uint32_t timeout) {
    if(!out || !size || size>256 || !timeout || timeout>1000)return -22;
    if(!selected(path))return -13;
    reist_app_frame r;int result=transact(REIST_APP_READ,offset,(unsigned)size,timeout,&r);
    if(result)return result;
    bytes(out,r.payload,r.length);return (int)r.length;
}
int reist_vfs_file_open(const char *path,uint32_t timeout,reist_vfs_file_handle_t *out) {
    if(!out)return -22;
    if(app_opened || app_closed)return -24;
    x86os_file_info_t info;int result=reist_vfs_stat(path,&info,timeout);if(result)return result;
    if(info.type!=X86OS_FILE)return -21;
    app_opened=1;app_offset=0;*out=0x101;return 0;
}
int reist_vfs_file_read(reist_vfs_file_handle_t handle,void *out,size_t size) {
    if(handle!=0x101 || !app_opened || app_closed)return -9;
    int result=reist_vfs_read_at(app_path,app_offset,out,size,1000);
    if(result>=0)app_offset+=(unsigned)result;
    return result;
}
int reist_vfs_file_close(reist_vfs_file_handle_t handle) {
    if(handle!=0x101 || !app_opened || app_closed)return -9;
    reist_app_frame r;int result=transact(REIST_APP_CLOSE,0,0,1000,&r);
    if(!result)app_opened=0;
    return result;
}
int x86os_monotonic_ms(uint64_t *out){if(!out)return -22;return clock_read(out);}
int x86os_sleep_ms(uint32_t delay) {
    if(!delay || delay>100)return -22;
    int wait=remaining();if(wait<0)return wait;if(delay>(unsigned)wait)return -110;
    int result=(int)CALL(SLEEP_MS,delay,0,0);if(result)return result;return remaining()<0?-110:0;
}
static void flush(void) {
    if(!app_output_used)return;
    if(app_output_used>16384-app_output_total)stop(-110);
    unsigned sent=0;
    for(unsigned attempt=0;sent<app_output_used && attempt<128;attempt++) {
        if(remaining()<0)stop(-110);
        int result=(int)CALL(WRITE,1,app_output+sent,app_output_used-sent);
        if(result>0 && (unsigned)result<=app_output_used-sent)sent+=(unsigned)result;
        else if(result!=-11)stop(-5);
        if(sent<app_output_used && x86os_sleep_ms(10))stop(-110);
    }
    if(sent!=app_output_used)stop(-110);
    app_output_total+=app_output_used;app_output_used=0;
}
void x86os_putchar(char c){app_output[app_output_used++]=c;if(app_output_used==64 || c=='\n')flush();}
void x86os_puts(const char *s) {
    if(!s)stop(-22);
    unsigned n=0;while(n<4096 && s[n])x86os_putchar(s[n++]);if(n==4096)stop(-22);
}
int x86os_getchar(void) {
    for(unsigned n=0;n<100;n++) {
        if(remaining()<0)stop(-110);
        flush();
        unsigned char c=0;int result=(int)CALL(READ,0,&c,1);
        if(result==1){if(++app_input_total>1024)stop(-110);return c;}
        if(result!=-11)stop(-5);
        if(x86os_sleep_ms(10))stop(-110);
    }
    stop(-110);
}
static uint32_t channel(const char *s) {
    if(!s || s[0]!='@' || s[1]!='a' || s[2]!='f' || s[3]!='1' || s[4]!=':')return 0;
    uint32_t value=0;
    for(unsigned i=5;i<13;i++){unsigned c=(unsigned char)s[i];if(!((c>='0' && c<='9') || (c>='a' && c<='f')))return 0;value=value*16+(c<='9'?c-'0':c-'a'+10);}
    return s[13]?0:value;
}
extern int __real_main(int,char **);
int __wrap_main(int argc,char **argv) {
    int64_t now=CALL(MONOTONIC_MS,0,0,0),self=CALL(GETPID,0,0,0);
    if(now<0 || now>INT64_MAX-1000 || self<=0 || self>0x7fffffff)stop(-5);
    app_end=(uint64_t)now+1000;app_previous=(uint64_t)now;app_child=(uint64_t)self;
    for(unsigned n=0;n<100;n++) {
        reist_terminal_input_request_t terminal={1,sizeof(terminal),REIST_TERMINAL_CHECK,0,0,0};
        if(!CALL(TERMINAL_INPUT,&terminal,0,0))break;
        if(n==99 || x86os_sleep_ms(10))stop(-110);
    }
    if(argc>=3 && (app_request=channel(argv[argc-2]))!=0) {
        app_reply=channel(argv[argc-1]);if(!app_reply || app_reply==app_request)stop(-22);
        argc-=2;argv[argc]=0;
        const char *path=0;
#ifdef REIST_APP_LS
        unsigned tool=2;
#else
        unsigned tool=1;
#endif
        if(reist_app_operand(tool,argc,(const char *const *)argv,&path) || !path)stop(-22);
        unsigned n=0;while(n<127 && path[n]){app_path[n]=path[n];n++;}app_path[n]=0;
        reist_app_frame r;if(transact(REIST_APP_HELLO,0,0,1000,&r))stop(-5);
    }
    int result=__real_main(argc,argv);flush();
    if(app_request && !app_closed && !app_failed){reist_app_frame r;if(transact(REIST_APP_CLOSE,0,0,1000,&r))return 1;}
    return result;
}
