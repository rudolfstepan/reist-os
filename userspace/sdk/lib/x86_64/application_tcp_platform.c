/* Ordinary TCP SDK adapter over root-owned, directional IPC capabilities. */
#include <reist/x86_64/application_tcp.h>
#ifdef REIST_NATIVE_APP_DNS
#include <reist/x86_64/application_dns.h>
#endif
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/terminal.h>
#ifdef REIST_APP_TCP_HOST_TEST
extern int64_t tcp_host_call(unsigned,uint64_t,uint64_t,uint64_t);
#define CALL(n,a,b,c) tcp_host_call(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#else
#define CALL(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#endif
static uint32_t request_endpoint,reply_endpoint;
static reist_app_tcp_grant grant;
static uint64_t sequence,previous,end;
static unsigned failed,closed,output_count;
/* Same fixed chunk size as the native console adapter; no heap or lease
 * extension. Keep this adapter's original absolute application deadline. */
static char output[64];
static unsigned output_used;
static x86os_ipc_bulk_message_t message;
/* Private debugger-selected qualification input; never a command operand or
 * authority grant. Ordinary signed images start at zero. */
#ifdef REIST_NATIVE_APP_HTTP
#include <reist/x86_64/application_http.h>
volatile uint64_t reist_http_app_selection[2] __attribute__((section(".data.memory_witness")))={0x3150504150545448ULL,0};
#define reist_tcp_app_selection reist_http_app_selection
#define reist_app_tcp_operand reist_app_http_operand
#else
#ifdef REIST_NATIVE_APP_DNS
volatile uint64_t reist_dns_app_selection[2] __attribute__((section(".data.memory_witness")))={0x31505041534e4452ULL,0};
#define reist_tcp_app_selection reist_dns_app_selection
#else
volatile uint64_t reist_tcp_app_selection[2] __attribute__((section(".data.memory_witness")))={0x3150504150435452ULL,0};
#endif
#endif
#ifndef REIST_APP_TCP_HOST_TEST
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
static int transact(unsigned op,unsigned handle,unsigned length,const void *data,unsigned timeout,reist_app_tcp_request *out) {
    if(failed||closed||!request_endpoint||!reply_endpoint)return -116;
    if(!timeout||timeout>2000||length>512||(op==REIST_APP_TCP_SEND&&length&&!data))return -22;
    uint64_t start=now();if(start>=end){failed=1;return -110;}
    if(sequence>=64)return -122;
    if(op==REIST_APP_TCP_SEND&&reist_tcp_app_selection[1]==8) {
        /* Exercise an actually retired handle, not an unissued number. */
        reist_app_tcp_request retired;int r=transact(REIST_APP_TCP_CLOSE,handle,0,0,1000,&retired);
        if(r)return r;
        start=now();if(start>=end){failed=1;return -110;}
    }
    reist_app_tcp_request q={.grant=grant,.sequence=op?sequence+1:0,.deadline=start+timeout,
        .operation=op,.handle=handle,.length=length};
    if(q.deadline>end)q.deadline=end;
    if(op==REIST_APP_TCP_SEND&&length)reist_net_copy(q.payload,data,length);
    if(op==REIST_APP_TCP_SEND) {
        unsigned fault=(unsigned)reist_tcp_app_selection[1];
        if(fault==1)q.grant.peer++;
        if(fault==2)q.grant.application+=1ULL<<32;
        if(fault==3)q.grant.epoch--;
        if(fault==4)q.grant.reserved=1;
    }
    reist_net_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=608;
    reist_net_copy(message.payload,&q,608);
    unsigned remaining=(unsigned)(q.deadline-start);if(remaining>100)remaining=100;
    int r=(int)CALL(IPC_SEND_TIMEOUT,request_endpoint,&message,remaining);if(r)goto bad;
    for(unsigned turn=0;turn<20;turn++) {
        if(now()>=q.deadline){r=-110;goto bad;}
        remaining=(unsigned)(q.deadline-previous);if(remaining>100)remaining=100;
        reist_net_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=2048;
        r=(int)CALL(IPC_RECEIVE_TIMEOUT,reply_endpoint,&message,remaining);
        if(r!=-110)break;
    }
    if(r)goto bad;
    if(now()>=q.deadline){r=-110;goto bad;}
    reist_app_tcp_request response;reist_net_copy(&response,message.payload,608);
    if(message.version!=2||message.struct_size!=sizeof(message)||message.length!=608||
       !empty(message.payload+608,2048-608)||response.operation!=op||response.sequence!=q.sequence||
       response.result>0||response.result< -4095||response.length>512||
       !empty(response.payload+((op==REIST_APP_TCP_RECV||op==REIST_APP_TCP_STATS)&&!response.result?response.length:0),
              512-((op==REIST_APP_TCP_RECV||op==REIST_APP_TCP_STATS)&&!response.result?response.length:0))){r=-71;goto bad;}
    if(!op) {
        reist_app_tcp_grant *g=&response.grant;
#ifdef REIST_NATIVE_APP_DNS
        if(g->version!=1||g->size!=64||g->reserved||g->protocol!=17||g->peer!=grant.peer||
#else
        if(g->version!=1||g->size!=64||g->reserved||g->protocol!=6||g->peer!=grant.peer||
#endif
           g->local_port!=grant.local_port||g->peer_port!=grant.peer_port||g->application!=grant.application||
           (uint32_t)g->root||!(g->root>>32)||g->root>>32>=g->application>>32||
           (uint32_t)g->service!=5||!(g->service>>32)||g->service>>32>0x7fffffff||
           g->service>>32>=g->application>>32||!g->epoch||g->expires<=previous||g->expires>end||
           response.result||response.handle||response.length||response.deadline!=q.deadline){r=-71;goto bad;}
        grant=*g;end=g->expires;
    } else {
        if(!equal(&response.grant,&grant,sizeof(grant))||response.deadline!=q.deadline||
           (op!=REIST_APP_TCP_OPEN&&response.handle!=handle)||
           (op==REIST_APP_TCP_OPEN&&!response.result&&(!response.handle||
#ifdef REIST_NATIVE_APP_DNS
             (grant.protocol==6&&response.handle>4)))||
#else
             response.handle>4))||
#endif
#ifdef REIST_NATIVE_APP_DNS
           (grant.protocol==6&&response.result&&response.length)||
#else
           (response.result&&response.length)||
#endif
           (!response.result&&op==REIST_APP_TCP_SEND&&response.length!=length)||
           (!response.result&&op==REIST_APP_TCP_STATS&&response.length!=sizeof(x86os_tcp_socket_control_t))||
           (op!=REIST_APP_TCP_RECV&&op!=REIST_APP_TCP_SEND&&op!=REIST_APP_TCP_STATS&&response.length)||
           (op==REIST_APP_TCP_RECV&&response.length>length)){r=-71;goto bad;}
        sequence=q.sequence;
    }
    *out=response;reist_net_zero(&message,sizeof(message));return response.result;
bad:
    failed=1;reist_net_zero(&message,sizeof(message));return r;
}
int x86os_tcp_socket_open(x86os_tcp_socket_t *out) {
    if(!out)return -22;
#ifdef REIST_NATIVE_APP_DNS
    grant.protocol=6;
#endif
    reist_app_tcp_request r;
    int status=transact(REIST_APP_TCP_OPEN,0,0,0,1000,&r);if(!status)*out=r.handle;return status;
}
int x86os_tcp_socket_close(x86os_tcp_socket_t socket,uint32_t timeout) {
#ifdef REIST_NATIVE_APP_DNS
    grant.protocol=6;
#endif
    reist_app_tcp_request r;return transact(REIST_APP_TCP_CLOSE,socket,0,0,timeout,&r);
}
int x86os_tcp_socket_stats(x86os_tcp_socket_control_t *out) {
    if(!out)return -22;reist_app_tcp_request r;
#ifdef REIST_NATIVE_APP_DNS
    grant.protocol=6;
#endif
    int status=transact(REIST_APP_TCP_STATS,0,0,0,1000,&r);
    if(status)return status;
    x86os_tcp_socket_control_t stats;reist_net_copy(&stats,r.payload,sizeof(stats));
    if(stats.version!=1||stats.struct_size!=sizeof(stats)||stats.operation!=X86OS_TCP_SOCKET_STATS||
       stats.socket||stats.timeout_ms||stats.active_sockets>4||stats.established_sockets>stats.active_sockets||
       stats.retransmissions>64*512){failed=1;return -71;}
    *out=stats;return 0;
}
int x86os_tcp_socket_ingress(const x86os_tcp_segment_t *s,const void *p){(void)s;(void)p;return -13;}
int x86os_tcp_listen(const x86os_tcp_listen_t *q){(void)q;return -13;}
int x86os_tcp_accept(x86os_tcp_accept_t *q){(void)q;return -13;}
#ifndef REIST_NATIVE_APP_DNS
int x86os_dns_resolve(const char *host,uint32_t timeout,x86os_dns_result_t *r){(void)host;(void)timeout;(void)r;return -13;}
#endif
int x86os_tcp_connect(const x86os_tcp_connect_t *q) {
    if(!q||q->version!=1||q->struct_size!=sizeof(*q)||q->reserved||
       q->destination_ip!=grant.peer||q->destination_port!=grant.peer_port)return -22;
#ifdef REIST_NATIVE_APP_DNS
    grant.protocol=6;
#endif
    reist_app_tcp_request r;return transact(REIST_APP_TCP_CONNECT,q->socket,0,0,q->timeout_ms,&r);
}
int x86os_tcp_send(const x86os_tcp_io_t *q,const void *p) {
    if(!q||q->version!=1||q->struct_size!=sizeof(*q))return -22;
#ifdef REIST_NATIVE_APP_DNS
    grant.protocol=6;
#endif
    reist_app_tcp_request r;int status=transact(REIST_APP_TCP_SEND,q->socket,q->length,p,q->timeout_ms,&r);
    return status?status:(int)r.length;
}
int x86os_tcp_receive(x86os_tcp_io_t *q,void *p) {
    if(!q||q->version!=1||q->struct_size!=sizeof(*q)||!q->length||!p)return -22;
#ifdef REIST_NATIVE_APP_DNS
    grant.protocol=6;
#endif
    unsigned capacity=q->length;if(capacity>512)capacity=512;
    reist_app_tcp_request r;int status=transact(REIST_APP_TCP_RECV,q->socket,capacity,0,q->timeout_ms,&r);
    if(status)return status;
    if(r.length)reist_net_copy(p,r.payload,r.length);q->length=r.length;return (int)r.length;
}
static void output_flush(void) {
    unsigned done=0;
    for(unsigned n=0;n<100;n++) {
        if(done==output_used)break;
        if(failed||now()>=end){failed=1;break;}
        int r=(int)CALL(WRITE,1,output+done,output_used-done);
        if(r>0&&(unsigned)r<=output_used-done){done+=(unsigned)r;continue;}
        if(r!=-11||pause_ms(1)){failed=1;break;}
    }
    if(done!=output_used)failed=1;
    reist_net_zero(output,sizeof(output));output_used=0;
}
void x86os_putchar(char c) {
    if(failed)return;
    if(output_count>=1024){failed=1;return;}
    output_count++;output[output_used++]=c;
    if(output_used==sizeof(output)||c=='\n')output_flush();
}
void x86os_puts(const char *p){if(!p){failed=1;return;}for(unsigned n=0;n<1024&&p[n];n++)x86os_putchar(p[n]);}
#ifdef REIST_NATIVE_APP_HTTP
int x86os_monotonic_ms(uint64_t *out) {
    if(!out)return -22;uint64_t n=now();if(failed)return -84;*out=n;return 0;
}
void x86os_print_number(int value) {
    uint32_t n=(uint32_t)value;if(value<0){x86os_putchar('-');n=0U-n;}
    char digits[10];unsigned count=0;do{digits[count++]=(char)('0'+n%10);n/=10;}while(n);
    while(count)x86os_putchar(digits[--count]);
}
int x86os_write(int fd,const void *data,size_t length) {
    if(fd!=X86OS_STDOUT_FILENO)return -13;
    if((length&&!data)||length>1024-output_count)return -90;
    if(failed||closed)return -116;
    const char *bytes=data;for(size_t n=0;n<length;n++){x86os_putchar(bytes[n]);if(failed)return -5;}
    output_flush();return failed?-5:(int)length;
}
int x86os_sleep_ms(uint32_t ms){if(!ms||ms>100)return -22;return pause_ms(ms);}
int x86os_create(const char *p){(void)p;return -13;}
int x86os_close(int fd){(void)fd;return -13;}
int x86os_rename(const char *a,const char *b){(void)a;(void)b;return -13;}
int x86os_unlink(const char *p){(void)p;return -13;}
void *x86os_malloc(size_t n){(void)n;return 0;}
void x86os_free(void *p){if(p)failed=1;}
int x86os_ipc_send_bulk_timeout(x86os_ipc_handle_t ep,const x86os_ipc_bulk_message_t *m,uint32_t timeout) {
    (void)ep;(void)m;(void)timeout;return -13;
}
#endif
#ifdef REIST_NATIVE_APP_DNS
int x86os_monotonic_ms(uint64_t *out) {
    if(!out)return -22;uint64_t n=now();if(failed)return -84;*out=n;return 0;
}
int x86os_getpid(void){return (int)CALL(GETPID,0,0,0);}
int x86os_network_control(const x86os_network_control_request_t *q,x86os_network_control_result_t *out) {
    if(!q||!out||q->version!=X86OS_NETWORK_CONTROL_VERSION||q->struct_size!=sizeof(*q)||q->operation!=X86OS_NETWORK_STATUS)return -13;
    if(failed||closed||!grant.epoch||now()>=end)return -116;
    /* The root already validated this interface before issuing the grant. */
    reist_net_zero(out,sizeof(*out));out->version=X86OS_NETWORK_CONTROL_VERSION;
    out->struct_size=sizeof(*out);out->configured=1;out->dns_server=grant.peer;return 0;
}
void x86os_print_number(int value) {
    uint32_t n=(uint32_t)value;if(value<0){x86os_putchar('-');n=0U-n;}
    char digits[10];unsigned count=0;do{digits[count++]=(char)('0'+n%10);n/=10;}while(n);
    while(count)x86os_putchar(digits[--count]);
}
int x86os_udp_socket_open(x86os_udp_socket_t *out) {
    if(!out)return -22;grant.protocol=17;reist_app_tcp_request r;
    int status=transact(REIST_APP_UDP_OPEN,0,0,0,1000,&r);if(!status)*out=r.handle;return status;
}
int x86os_udp_socket_bind(x86os_udp_socket_t socket,uint16_t port) {
    if(port&&port!=grant.local_port)return -13;grant.protocol=17;reist_app_tcp_request r;
    return transact(REIST_APP_UDP_BIND,socket,0,0,1000,&r);
}
int x86os_udp_socket_close(x86os_udp_socket_t socket) {
    grant.protocol=17;reist_app_tcp_request r;return transact(REIST_APP_UDP_CLOSE,socket,0,0,1000,&r);
}
int x86os_udp_socket_stats(x86os_udp_socket_control_t *out){(void)out;return -38;}
int x86os_udp_socket_ingress(const x86os_udp_datagram_t *d,const void *p){(void)d;(void)p;return -13;}
int x86os_udp_sendto(const x86os_udp_datagram_t *d,const void *p) {
    if(!d||d->version!=1||d->struct_size!=sizeof(*d)||d->ip!=grant.peer||
       d->destination_port!=53||(d->source_port&&d->source_port!=grant.local_port))return -22;
    grant.protocol=17;reist_app_tcp_request r;int status=transact(REIST_APP_UDP_SEND,d->socket,d->length,p,d->timeout_ms,&r);
    return status?status:(int)r.length;
}
int x86os_udp_recvfrom(x86os_udp_datagram_t *d,void *p) {
    if(!d||d->version!=1||d->struct_size!=sizeof(*d)||d->length>512||(d->length&&!p))return -22;
    grant.protocol=17;reist_app_tcp_request r;int status=transact(REIST_APP_UDP_RECEIVE,d->socket,d->length,0,d->timeout_ms,&r);
    if(status)return status;reist_net_copy(p,r.payload,r.length);d->length=r.length;
    d->ip=grant.peer;d->source_port=grant.peer_port;d->destination_port=grant.local_port;return (int)r.length;
}
#endif
static uint32_t endpoint(const char *p) {
    if(!p||p[0]!='@'||p[1]!='a'||p[2]!='t'||p[3]!='1'||p[4]!=':')return 0;
    uint32_t value=0;
    for(unsigned n=5;n<13;n++){unsigned c=(unsigned char)p[n];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return 0;
        value=value*16+(c<='9'?c-'0':c-'a'+10);}
    return p[13]?0:value;
}
extern int __real_main(int,char **);
int __wrap_main(int argc,char **argv) {
    int64_t pid=CALL(GETPID,0,0,0);uint64_t start=now();
#ifdef REIST_NATIVE_APP_HTTP
    if(pid<=0||pid>0x7fffffff||start>UINT64_MAX-6000||argc<4||argc>7)return 22;
#else
#ifdef REIST_NATIVE_APP_DNS
    if(pid<=0||pid>0x7fffffff||start>UINT64_MAX-6000||argc<4||argc>5)return 22;
#else
    if(pid<=0||pid>0x7fffffff||start>UINT64_MAX-6000||argc<5||argc>6)return 22;
#endif
#endif
    end=start+6000;
    request_endpoint=endpoint(argv[argc-2]);reply_endpoint=endpoint(argv[argc-1]);
    if(!request_endpoint||!reply_endpoint||request_endpoint==reply_endpoint)return 22;
    argc-=2;argv[argc]=0;
#ifdef REIST_NATIVE_APP_DNS
    if(reist_app_dns_operand(argc,(const char *const *)argv,&grant))return 22;
#else
    if(reist_app_tcp_operand(argc,(const char *const *)argv,&grant))return 22;
#endif
    grant.application=((uint64_t)pid<<32)|6;
    grant.local_port=reist_app_tcp_port_base(grant.application);if(!grant.local_port)return 22;
    for(unsigned n=0;n<100;n++) {
        reist_terminal_input_request_t q={1,sizeof(q),REIST_TERMINAL_CHECK,0,0,0};
        if(!CALL(TERMINAL_INPUT,&q,0,0))break;
        if(n==99||pause_ms(10))return 110;
    }
    reist_app_tcp_request response;if(transact(0,0,0,0,1000,&response))return 5;
#ifdef REIST_NATIVE_APP_HTTP
    if(reist_tcp_app_selection[0]!=0x3150504150545448ULL||reist_tcp_app_selection[1]>8)return 22;
#else
#ifdef REIST_NATIVE_APP_DNS
    if(reist_tcp_app_selection[0]!=0x31505041534e4452ULL||reist_tcp_app_selection[1]>8)return 22;
#else
    if(reist_tcp_app_selection[0]!=0x3150504150435452ULL||reist_tcp_app_selection[1]>8)return 22;
#endif
#endif
    if(reist_tcp_app_selection[1]==5)__builtin_trap();
    if(reist_tcp_app_selection[1]==6)for(;;)(void)CALL(SLEEP_MS,100,0,0);
    if(reist_tcp_app_selection[1]==7)for(;;)__asm__ volatile("pause");
    int status=__real_main(argc,argv);
    output_flush();
    if(!failed&&!transact(REIST_APP_TCP_RELEASE,0,0,0,1000,&response))closed=1;
    reist_net_zero(&grant,sizeof(grant));return failed||!closed?5:status;
}
