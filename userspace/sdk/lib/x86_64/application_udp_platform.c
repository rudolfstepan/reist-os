/* Ordinary UDP SDK adapter over root-owned, directional IPC capabilities. */
#include <reist/x86_64/application_udp.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/terminal.h>
#ifdef REIST_APP_UDP_HOST_TEST
extern int64_t udp_host_call(unsigned,uint64_t,uint64_t,uint64_t);
#define CALL(n,a,b,c) udp_host_call(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#else
#define CALL(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#endif
static uint32_t request_endpoint,reply_endpoint;
static reist_app_udp_grant grant;
static uint64_t sequence,previous,end;
static unsigned failed,closed,output_count;
static x86os_ipc_bulk_message_t message;
/* Private debugger-selected qualification input; never a command operand or
 * authority grant. Ordinary signed images start at zero. */
volatile uint64_t reist_udp_app_selection[2] __attribute__((section(".data.memory_witness")))={0x3150504144505552ULL,0};
#ifndef REIST_APP_UDP_HOST_TEST
/* Compiler-generated structure copies also need the freestanding C runtime.
 * These are local memory operations, with no service or device transport. */
void *memcpy(void *d,const void *s,size_t n){uint8_t *a=d;const uint8_t *b=s;for(size_t i=0;i<n;i++)a[i]=b[i];return d;}
void *memset(void *d,int v,size_t n){uint8_t *a=d;for(size_t i=0;i<n;i++)a[i]=(uint8_t)v;return d;}
#endif
static uint64_t now(void) {
    int64_t n=CALL(MONOTONIC_MS,0,0,0);
    if(n<0||(uint64_t)n<previous){failed=1;return UINT64_MAX;}
    previous=(uint64_t)n;return previous;
}
static int pause_ms(unsigned ms) {
    if(now()>=end){failed=1;return -110;}
    return (int)CALL(SLEEP_MS,ms,0,0);
}
static int equal(const void *a,const void *b,unsigned n) {
    const uint8_t *p=a,*q=b;unsigned d=0;for(unsigned i=0;i<n;i++)d|=p[i]^q[i];return !d;
}
static int empty(const void *a,unsigned n){const uint8_t *p=a;for(unsigned i=0;i<n;i++)if(p[i])return 0;return 1;}
static int transact(unsigned op,unsigned handle,unsigned length,const void *data,unsigned timeout,reist_app_udp_request *out) {
    if(failed||closed||!request_endpoint||!reply_endpoint)return -116;
    if(!timeout||timeout>2000||length>512||(op==REIST_APP_UDP_SEND&&length&&!data))return -22;
    uint64_t start=now();if(start>=end){failed=1;return -110;}
    if(sequence>=64)return -122;
    if(op==REIST_APP_UDP_SEND&&reist_udp_app_selection[1]==8) {
        /* Exercise an actually retired handle, not an unissued number. */
        reist_app_udp_request retired;int r=transact(REIST_APP_UDP_CLOSE,handle,0,0,1000,&retired);
        if(r)return r;
        start=now();if(start>=end){failed=1;return -110;}
    }
    reist_app_udp_request q={.grant=grant,.sequence=op?sequence+1:0,.deadline=start+timeout,
        .operation=op,.handle=handle,.length=length};
    if(q.deadline>end)q.deadline=end;
    if(op==REIST_APP_UDP_SEND&&length)reist_net_copy(q.payload,data,length);
    if(op==REIST_APP_UDP_SEND) {
        unsigned fault=(unsigned)reist_udp_app_selection[1];
        if(fault==1)q.grant.peer++;
        if(fault==2)q.grant.application+=1ULL<<32;
        if(fault==3)q.grant.epoch--;
        if(fault==4)q.grant.reserved=1;
    }
    reist_net_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=608;
    reist_net_copy(message.payload,&q,608);
    unsigned remaining=(unsigned)(q.deadline-start);if(remaining>100)remaining=100;
    int r=(int)CALL(IPC_SEND_TIMEOUT,request_endpoint,&message,remaining);if(r)goto bad;
    for(unsigned turn=0;turn<2000;turn++) {
        if(now()>=q.deadline){r=-110;goto bad;}
        reist_net_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=2048;
        r=(int)CALL(IPC_RECEIVE_TIMEOUT,reply_endpoint,&message,0);
        if(r!=-11&&r!=-110)break;
        if((r=pause_ms(1)))goto bad;
        r=-110;
    }
    if(r)goto bad;
    if(now()>=q.deadline){r=-110;goto bad;}
    reist_app_udp_request response;reist_net_copy(&response,message.payload,608);
    if(message.version!=2||message.struct_size!=sizeof(message)||message.length!=608||
       !empty(message.payload+608,2048-608)||response.operation!=op||response.sequence!=q.sequence||
       response.result>0||response.result< -4095||response.length>512||
       !empty(response.payload+(op==REIST_APP_UDP_RECEIVE&&!response.result?response.length:0),
              512-(op==REIST_APP_UDP_RECEIVE&&!response.result?response.length:0))){r=-71;goto bad;}
    if(!op) {
        reist_app_udp_grant *g=&response.grant;
        if(g->version!=1||g->size!=64||g->reserved||g->protocol!=17||g->peer!=grant.peer||
           g->local_port!=grant.local_port||g->peer_port!=grant.peer_port||g->application!=grant.application||
           (uint32_t)g->root||!(g->root>>32)||g->root>>32>=g->application>>32||
           (uint32_t)g->service!=5||!(g->service>>32)||g->service>>32>0x7fffffff||
           g->service>>32==g->application>>32||!g->epoch||g->expires<=previous||g->expires>end||
           response.result||response.handle||response.length||response.deadline!=q.deadline){r=-71;goto bad;}
        grant=*g;end=g->expires;
    } else {
        if(!equal(&response.grant,&grant,sizeof(grant))||response.deadline!=q.deadline||
           (op!=REIST_APP_UDP_OPEN&&response.handle!=handle)||
           (op==REIST_APP_UDP_OPEN&&!response.result&&!response.handle)||
           (op!=REIST_APP_UDP_RECEIVE&&response.length!=length)||
           (op==REIST_APP_UDP_RECEIVE&&response.length>length)){r=-71;goto bad;}
        sequence=q.sequence;
    }
    *out=response;reist_net_zero(&message,sizeof(message));return response.result;
bad:
    failed=1;reist_net_zero(&message,sizeof(message));return r;
}
int x86os_udp_socket_open(x86os_udp_socket_t *out) {
    if(!out)return -22;reist_app_udp_request r;
    int status=transact(REIST_APP_UDP_OPEN,0,0,0,1000,&r);if(!status)*out=r.handle;return status;
}
int x86os_udp_socket_bind(x86os_udp_socket_t socket,uint16_t port) {
    if(port!=grant.local_port)return -13;reist_app_udp_request r;
    return transact(REIST_APP_UDP_BIND,socket,0,0,1000,&r);
}
int x86os_udp_socket_close(x86os_udp_socket_t socket) {
    reist_app_udp_request r;return transact(REIST_APP_UDP_CLOSE,socket,0,0,1000,&r);
}
int x86os_udp_socket_stats(x86os_udp_socket_control_t *out){(void)out;return -38;}
int x86os_udp_socket_ingress(const x86os_udp_datagram_t *d,const void *p){(void)d;(void)p;return -13;}
int x86os_udp_sendto(const x86os_udp_datagram_t *d,const void *p) {
    if(!d||d->version!=1||d->struct_size!=sizeof(*d)||d->ip!=grant.peer||
       d->destination_port!=grant.peer_port||(d->source_port&&d->source_port!=grant.local_port))return -22;
    reist_app_udp_request r;return transact(REIST_APP_UDP_SEND,d->socket,d->length,p,d->timeout_ms,&r);
}
int x86os_udp_recvfrom(x86os_udp_datagram_t *d,void *p) {
    if(!d||d->version!=1||d->struct_size!=sizeof(*d)||d->length>512||(d->length&&!p)||
       d->ip||d->source_port||d->destination_port)return -22;
    reist_app_udp_request r;int status=transact(REIST_APP_UDP_RECEIVE,d->socket,d->length,0,d->timeout_ms,&r);
    if(!status){if(r.length)reist_net_copy(p,r.payload,r.length);d->length=r.length;
        d->ip=grant.peer;d->source_port=grant.peer_port;d->destination_port=grant.local_port;}
    return status;
}
void x86os_putchar(char c) {
    if(output_count++>=1024||now()>=end){failed=1;return;}
    for(unsigned n=0;n<100;n++) {
        int r=(int)CALL(WRITE,1,&c,1);if(r==1)return;
        if(r!=-11||pause_ms(1)){failed=1;return;}
    }
    failed=1;
}
void x86os_puts(const char *p){if(!p){failed=1;return;}for(unsigned n=0;n<1024&&p[n];n++)x86os_putchar(p[n]);}
static uint32_t endpoint(const char *p) {
    if(!p||p[0]!='@'||p[1]!='a'||p[2]!='u'||p[3]!='1'||p[4]!=':')return 0;
    uint32_t value=0;
    for(unsigned n=5;n<13;n++){unsigned c=(unsigned char)p[n];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return 0;
        value=value*16+(c<='9'?c-'0':c-'a'+10);}
    return p[13]?0:value;
}
extern int __real_main(int,char **);
int __wrap_main(int argc,char **argv) {
    int64_t pid=CALL(GETPID,0,0,0);uint64_t start=now();
    if(pid<=0||pid>0x7fffffff||start>UINT64_MAX-6000||argc<7||argc>8)return 22;
    end=start+6000;
    request_endpoint=endpoint(argv[argc-2]);reply_endpoint=endpoint(argv[argc-1]);
    if(!request_endpoint||!reply_endpoint||request_endpoint==reply_endpoint)return 22;
    argc-=2;argv[argc]=0;
    if(reist_app_udp_operand(argc,(const char *const *)argv,&grant))return 22;
    grant.application=((uint64_t)pid<<32)|6;
    for(unsigned n=0;n<100;n++) {
        reist_terminal_input_request_t q={1,sizeof(q),REIST_TERMINAL_CHECK,0,0,0};
        if(!CALL(TERMINAL_INPUT,&q,0,0))break;
        if(n==99||pause_ms(10))return 110;
    }
    reist_app_udp_request response;if(transact(0,0,0,0,1000,&response))return 5;
    if(reist_udp_app_selection[0]!=0x3150504144505552ULL||reist_udp_app_selection[1]>8)return 22;
    if(reist_udp_app_selection[1]==5)__builtin_trap();
    if(reist_udp_app_selection[1]==6)for(;;)(void)CALL(SLEEP_MS,100,0,0);
    if(reist_udp_app_selection[1]==7)for(;;)__asm__ volatile("pause");
    int status=__real_main(argc,argv);
    if(!failed&&!transact(REIST_APP_UDP_RELEASE,0,0,0,1000,&response))closed=1;
    reist_net_zero(&grant,sizeof(grant));return failed||!closed?5:status;
}
