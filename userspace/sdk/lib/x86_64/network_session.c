/* Pure IPC admission. Transport success, lifecycle and device ownership are
 * separate facts; an admitted message itself never grants device authority. */
#include <reist/x86_64/network_session.h>
void reist_net_zero(void *p,unsigned n){volatile uint8_t *b=p;while(n--)*b++=0;}
void reist_net_copy(void *to,const void *from,unsigned n){uint8_t *a=to;const uint8_t *b=from;for(unsigned i=0;i<n;i++)a[i]=b[i];}
static int owner_valid(uint64_t owner){return owner>>32&&owner>>32<=0x7fffffff&&(uint32_t)owner<8;}
int reist_net_channel_init(reist_net_channel *s,uint32_t ep,uint64_t owner,uint64_t peer,uint64_t epoch) {
    if(!s||!ep||!epoch||!owner_valid(owner)||!owner_valid(peer)||owner==peer||owner>>32==peer>>32)return -22;
    *s=(reist_net_channel){.owner=owner,.peer=peer,.epoch=epoch,.endpoint=ep};return 0;
}
static int valid(const reist_net_channel *s,uint64_t now) {
    return s&&s->endpoint&&s->epoch&&owner_valid(s->owner)&&owner_valid(s->peer)&&
        s->owner!=s->peer&&!s->failed&&now>=s->last_ms;
}
int reist_net_encode(reist_net_channel *s,reist_net_message *m,unsigned type,const void *data,
                     unsigned n,int result,uint64_t now,uint64_t end) {
    if(!valid(s,now)||!m||type<REIST_NET_INIT||type>REIST_NET_HELLO||n>sizeof(m->payload)||
       (n&&!data)||result>0||result< -4095||end<=now||end-now>3000)return -22;
    if(s->sent==UINT64_MAX)return -75;
    /* Reject aliasing before zeroing output or advancing correlation. */
    uintptr_t a=(uintptr_t)m,b=(uintptr_t)data,c=(uintptr_t)s;
    if(a>UINTPTR_MAX-sizeof(*m)||c>UINTPTR_MAX-sizeof(*s)||b>UINTPTR_MAX-n||
       (n&&b<a+sizeof(*m)&&a<b+n)||(c<a+sizeof(*m)&&a<c+sizeof(*s)))return -22;
    reist_net_zero(m,sizeof(*m));m->version=1;m->size=sizeof(*m);m->type=type;m->length=n;
    m->epoch=s->epoch;m->sequence=s->sent+1;m->owner=s->owner;m->deadline_ms=end;m->result=result;
    if(n)reist_net_copy(m->payload,data,n);
    s->sent++;s->last_ms=now;return 0;
}
int reist_net_decode(reist_net_channel *s,const reist_net_message *m,uint64_t now) {
    if(!valid(s,now)||!m)return -22;
    if(m->version!=1||m->size!=sizeof(*m)||m->type<REIST_NET_INIT||m->type>REIST_NET_HELLO||
       m->length>sizeof(m->payload)||m->reserved||m->reserved2||m->result>0||m->result< -4095)return -71;
    if(m->epoch!=s->epoch||m->owner!=s->peer||s->received==UINT64_MAX||m->sequence!=s->received+1)return -116;
    if(m->deadline_ms<=now||m->deadline_ms-now>3000)return -110;
    for(unsigned i=m->length;i<sizeof(m->payload);i++)if(m->payload[i])return -71;
    s->received=m->sequence;s->last_ms=now;return 0;
}
#ifdef REIST_NATIVE_NETWORK_SESSION
#include <reist/x86_64/syscall.h>
static x86os_ipc_bulk_message_t transport;
uint64_t reist_net_now(void) {
    int64_t n=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    if(n<0)__builtin_trap();return (uint64_t)n;
}
int reist_net_pause(unsigned ms) {
    if(!ms||ms>100)return -22;
    return (int)reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,ms);
}
int reist_net_send(reist_net_channel *s,reist_net_message *m) {
    if(!s||!m||s->failed)return -22;
    uint64_t now=reist_net_now();if(m->deadline_ms<=now)return -110;
    unsigned timeout=(unsigned)(m->deadline_ms-now);if(timeout>100)timeout=100;
    reist_net_zero(&transport,sizeof(transport));transport.version=2;transport.struct_size=sizeof(transport);
    transport.length=sizeof(*m);reist_net_copy(transport.payload,m,sizeof(*m));
    int r=(int)reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT,s->endpoint,(uintptr_t)&transport,timeout);
    reist_net_zero(&transport,sizeof(transport));if(r)s->failed=1;return r;
}
int reist_net_receive(reist_net_channel *s,reist_net_message *m,unsigned timeout) {
    if(!s||!m||s->failed||timeout>100)return -22;
    reist_net_zero(&transport,sizeof(transport));transport.version=2;transport.struct_size=sizeof(transport);transport.length=2048;
    int r=(int)reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,s->endpoint,(uintptr_t)&transport,timeout);
    if(r){reist_net_zero(&transport,sizeof(transport));return r;}
    if(transport.version!=2||transport.struct_size!=sizeof(transport)||transport.length!=sizeof(*m))r=-71;
    for(unsigned i=sizeof(*m);i<2048;i++)if(transport.payload[i])r=-71;
    if(!r){reist_net_copy(m,transport.payload,sizeof(*m));r=reist_net_decode(s,m,reist_net_now());}
    reist_net_zero(&transport,sizeof(transport));if(r)s->failed=1;return r;
}
static int hex(const char *s,uint32_t *v) {
    if(!s)return -22;uint32_t n=0;
    for(unsigned i=0;i<8;i++){unsigned c=(unsigned char)s[i],d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;
        if(d==16)return -22;n=(n<<4)|d;}
    if(s[8])return -22;*v=n;return 0;
}
int reist_net_startup(reist_net_channel *c,int argc,char **argv,unsigned slot,uint64_t *end,unsigned *mode) {
    uint32_t v[6];if(argc!=8||!argv||slot<4||slot>5||!end||!mode)return -22;
    for(unsigned i=0;i<6;i++)if(hex(argv[i+1],&v[i]))return -22;
    if(!argv[7]||argv[7][0]<'0'||argv[7][0]>'3'||argv[7][1])return -22;
    *mode=(unsigned)(argv[7][0]-'0');*end=((uint64_t)v[4]<<32)|v[5];
    uint64_t now=reist_net_now();if(*end<=now||*end-now>3000)return -110;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);if(pid<=0||pid>0x7fffffff)return -22;
    return reist_net_channel_init(c,v[0],((uint64_t)pid<<32)|slot,(uint64_t)v[1]<<32,((uint64_t)v[2]<<32)|v[3]);
}
#ifdef REIST_NET_ROLE_RUNTIME
void *memcpy(void *d,const void *s,size_t n){uint8_t *a=d;const uint8_t *b=s;for(size_t i=0;i<n;i++)a[i]=b[i];return d;}
void *memset(void *d,int v,size_t n){uint8_t *a=d;for(size_t i=0;i<n;i++)a[i]=(uint8_t)v;return d;}
#endif
#endif
