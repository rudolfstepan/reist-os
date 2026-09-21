/* Conventional SDK wrappers over existing native IPC/clock/sleep operations. */
#include "native_surface.h"
volatile reist_native_audit_buffer reist_native_audit;
void reist_native_audit_init(uint64_t owner,uint64_t epoch) {
    volatile unsigned char *p=(volatile unsigned char*)&reist_native_audit;
    for(unsigned n=0;n<sizeof(reist_native_audit);n++)p[n]=0;
    reist_native_audit.magic=0x3154494455414752ULL;
    reist_native_audit.owner=owner;reist_native_audit.epoch=epoch;
    reist_native_audit.version=1;reist_native_audit.capacity=128;
    reist_native_audit.bytes=sizeof(reist_native_audit);
}
void reist_native_audit_append(uint32_t endpoint,const x86os_ipc_message_t *m,uint64_t ms) {
    if(!m || m->version!=1 || m->struct_size!=140 || !endpoint ||
       !reist_native_audit.owner || reist_native_audit.exhausted)return;
    const unsigned char *payload=m->payload;
    unsigned version=payload[0]|(unsigned)payload[1]<<8|(unsigned)payload[2]<<16|(unsigned)payload[3]<<24;
    unsigned type=payload[8]|(unsigned)payload[9]<<8|(unsigned)payload[10]<<16|(unsigned)payload[11]<<24;
    if(!((m->length==64 && version==2)||(m->length==124 && version==6 && type==129)))return;
    uint64_t seq=reist_native_audit.sequence;
    if(seq==UINT64_MAX){reist_native_audit.exhausted=1;return;}
    volatile reist_native_audit_entry *entry=&reist_native_audit.entries[seq%128];
    entry->sequence=0;entry->ms=ms;entry->endpoint=endpoint;
    const unsigned char *wire=(const unsigned char*)m;
    for(unsigned n=0;n<140;n++)entry->wire[n]=wire[n];
    entry->sequence=seq+1;reist_native_audit.sequence=seq+1;
}
static void audit_received(uint32_t ep,const x86os_ipc_message_t *m) {
    if(m->version==1 && m->struct_size==140 &&
       ((m->length==64 && m->payload[0]==2) ||
        (m->length==124 && m->payload[0]==6 && m->payload[8]==129)))
        reist_native_audit_append(ep,m,reist_native_now());
}
void *memcpy(void *to,const void *from,size_t n) {
    unsigned char *d=to;const unsigned char *s=from;for(size_t i=0;i<n;i++)d[i]=s[i];return to;
}
void *memset(void *to,int v,size_t n){unsigned char *d=to;for(size_t i=0;i<n;i++)d[i]=(unsigned char)v;return to;}
void reist_native_zero(void *p,size_t n){volatile unsigned char *d=p;while(n--)*d++=0;}
uint64_t reist_native_now(void) {
    int64_t t=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);if(t<0)__builtin_trap();return (uint64_t)t;
}
int reist_native_sleep(unsigned ms){return (int)reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,ms);}
static int hex(const char *s,uint32_t *out) {
    if(!s||!out)return -22;
    uint32_t v=0;for(unsigned n=0;n<8;n++) {
        unsigned c=(unsigned char)s[n];if(!c)return -22;
        unsigned d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;
        if(d>15)return -22;v=v<<4|d;
    }
    if(s[8])return -22;*out=v;return 0;
}
int reist_native_role_arguments(int argc,char **argv,unsigned slot,reist_native_role_args *out) {
    if(argc!=8 || !argv || !out || slot<4 || slot>7)return -22;
    uint32_t ep,peer,eh,el,dh,dl;
    if(hex(argv[1],&ep)||hex(argv[2],&peer)||hex(argv[3],&eh)||hex(argv[4],&el)||
       hex(argv[5],&dh)||hex(argv[6],&dl)||!argv[7]||!argv[7][0]||argv[7][1]||
       !ep||!peer||peer>0x7fffffff)return -22;
    uint64_t epoch=(uint64_t)eh<<32|el,end=(uint64_t)dh<<32|dl,now=reist_native_now();
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);
    if(pid<=0||pid>0x7fffffff||!epoch||end<=now||end-now>3000||end>UINT64_MAX-500)return -22;
    *out=(reist_native_role_args){ep,peer,(unsigned char)argv[7][0],epoch,end,(uint64_t)pid<<32|slot};
    reist_native_audit_init(out->owner,epoch);return 0;
}
int reist_native_send(uint32_t ep,const void *data,unsigned length,unsigned timeout) {
    if(!data||!length||length>128||timeout>100)return -22;
    x86os_ipc_message_t m;reist_native_zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=length;
    memcpy(m.payload,data,length);
    return (int)reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT,ep,(uintptr_t)&m,timeout);
}
int reist_native_receive(uint32_t ep,void *data,unsigned capacity,unsigned *length,unsigned timeout) {
    if(!data||!length||!capacity||capacity>128||timeout>1000)return -22;
    x86os_ipc_message_t m;reist_native_zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=128;
    int r=(int)reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,ep,(uintptr_t)&m,timeout);
    if(r)return r;
    if(m.version!=1||m.struct_size!=140||!m.length||m.length>capacity)return -71;
    for(unsigned n=m.length;n<128;n++)if(m.payload[n])return -71;
    audit_received(ep,&m);
    memcpy(data,m.payload,m.length);*length=m.length;return 0;
}
int reist_native_control_send(uint32_t ep,const reist_graphical_control *c){return reist_native_send(ep,c,64,100);}
int reist_native_control_valid(const reist_graphical_control *c,unsigned type,
    unsigned role,uint64_t epoch,uint64_t owner,uint64_t sequence) {
    return c && c->version==1 && c->size==64 && c->type==type && c->role==role &&
        c->epoch==epoch && c->owner==owner && c->sequence==sequence && !c->reserved;
}
int reist_native_fault(unsigned mode) {
    if(mode=='u')__builtin_trap();
    if(mode=='q')for(;;)__asm__ volatile("pause");
    if(mode=='h'){for(unsigned n=0;n<60;n++)if(reist_native_sleep(100))return -5;return -110;}
    return 0;
}
int reist_native_fault_due(uint64_t now,uint64_t deadline) {
    return deadline<=UINT64_MAX-500 && now>=deadline+500;
}
int x86os_sleep_ms(uint32_t ms){return reist_native_sleep(ms);}
int x86os_yield(void){return (int)reist_x64_syscall0(REIST_X64_SYS_YIELD);}
int x86os_monotonic_ms(uint64_t *value){if(!value)return -22;*value=reist_native_now();return 0;}
int x86os_ipc_send_timeout(x86os_ipc_handle_t ep,const x86os_ipc_message_t *m,uint32_t ms) {
    if(!m||ms>1000)return -22;
    return (int)reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT,ep,(uintptr_t)m,ms>100?100:ms);
}
int x86os_ipc_receive_timeout(x86os_ipc_handle_t ep,x86os_ipc_message_t *m,uint32_t ms) {
    if(!m||ms>1000)return -22;
    int r=(int)reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,ep,(uintptr_t)m,ms);
    if(!r)audit_received(ep,m);
    return r;
}
