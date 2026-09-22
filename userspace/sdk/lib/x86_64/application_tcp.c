/* Ring3 TCP object authority. No kernel, scheduler, allocation or IO dependency. */
#include <reist/x86_64/application_tcp.h>
#include <stddef.h>
static void zero(void *p,size_t n){volatile uint8_t *b=p;while(n--)*b++=0;}
static void copy(void *p,const void *q,size_t n){uint8_t *a=p;const uint8_t *b=q;while(n--)*a++=*b++;}
static int equal(const void *a,const void *b,size_t n){const uint8_t *p=a,*q=b;unsigned d=0;while(n--)d|=*p++^*q++;return !d;}
static int empty(const void *p,size_t n){const uint8_t *b=p;while(n--)if(*b++)return 0;return 1;}
static int identity(uint64_t id,unsigned slot){return (uint32_t)id==slot&&(id>>32)&&id>>32<=0x7fffffff;}
static int overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x>UINTPTR_MAX-an||y>UINTPTR_MAX-bn||(x<y+bn&&y<x+an);
}
uint16_t reist_app_tcp_port_base(uint64_t application) {
    uint64_t generation=application>>32;
    if((uint32_t)application!=6||!generation||generation>4096)return 0;
    return (uint16_t)(49152+4*(generation-1));
}
int reist_app_tcp_init(reist_app_tcp_state *s,uint64_t root,uint64_t service,uint64_t now) {
    if(!s||!identity(root,0)||!identity(service,5)||root>>32>=service>>32)return -22;
    zero(s,sizeof(*s));s->root=root;s->service=service;s->last_ms=now;return 0;
}
int reist_app_tcp_grant_set(reist_app_tcp_state *s,const reist_app_tcp_grant *g,uint64_t now) {
    if(!s||!g||overlap(s,sizeof(*s),g,sizeof(*g)))return -22;
    if(s->active)return -16;
    uint16_t base=reist_app_tcp_port_base(g->application);
    if(!identity(s->root,0)||!identity(s->service,5)||g->version!=1||g->size!=64||g->reserved||
       g->root!=s->root||g->service!=s->service||!base||g->local_port!=base||
       g->application>>32<=s->service>>32||g->protocol!=6||g->peer!=REIST_APP_TCP_PEER||!g->peer_port)return -22;
    if(!g->epoch||g->epoch<=s->last_epoch||g->application<=s->last_application)return -116;
    if(now<s->last_ms)return -84;
    if(g->expires<=now||g->expires-now>REIST_APP_TCP_MS)return -110;
    s->grant=*g;s->last_epoch=g->epoch;s->last_application=g->application;
    s->last_ms=now;s->sequence=0;s->issued=0;s->active=1;return 0;
}
void reist_app_tcp_revoke(reist_app_tcp_state *s) {
    if(!s)return;
    s->active=0;s->sequence=0;
    zero(&s->grant,sizeof(s->grant));zero(&s->pending,sizeof(s->pending));zero(s->sockets,sizeof(s->sockets));
    /* Last application/epoch survive revocation: its port range cannot return. */
}
static reist_app_tcp_socket *resolve(reist_app_tcp_state *s,unsigned handle) {
    if(!handle||handle>4)return 0;
    reist_app_tcp_socket *p=&s->sockets[handle-1];return p->handle==handle?p:0;
}
static void abort_connection(reist_app_tcp_socket *p,int error) {
    p->state=REIST_TCP_CLOSED;p->error=error;p->receive_head=p->receive_count=0;
    zero(p->receive,sizeof(p->receive));p->tx_length=p->tx_flags=0;
}
int reist_app_tcp_begin(reist_app_tcp_state *s,const reist_app_tcp_request *q,reist_app_tcp_request *r,uint64_t now) {
    if(!s||!q||!r||overlap(s,sizeof(*s),q,sizeof(*q))||overlap(s,sizeof(*s),r,sizeof(*r))||overlap(q,sizeof(*q),r,sizeof(*r)))return -22;
    if(!s->active||!equal(&s->grant,&q->grant,sizeof(q->grant)))return -116;
    if(now<s->last_ms)return -84;
    if(now>=q->grant.expires||q->deadline<=now||q->deadline>q->grant.expires||q->deadline-now>2000)return -110;
    if(q->result||q->operation<1||q->operation>7||q->length>512)return -22;
    if(!empty(q->payload+(q->operation==REIST_APP_TCP_SEND?q->length:0),512-(q->operation==REIST_APP_TCP_SEND?q->length:0)))return -22;
    if(((q->operation==REIST_APP_TCP_OPEN||q->operation==REIST_APP_TCP_RELEASE||q->operation==REIST_APP_TCP_STATS)&&q->handle)||
       (q->operation!=REIST_APP_TCP_SEND&&q->operation!=REIST_APP_TCP_RECV&&q->length)||
       (q->operation==REIST_APP_TCP_RECV&&!q->length))return -22;
    if(s->sequence>=64)return -122;
    if(q->sequence!=s->sequence+1)return -116;
    if(s->pending.operation)return -16;
    *r=*q;r->length=0;zero(r->payload,512);s->sequence=q->sequence;s->last_ms=now;
    if(q->operation==REIST_APP_TCP_RELEASE){reist_app_tcp_revoke(s);return 0;}
    if(q->operation==REIST_APP_TCP_STATS) {
        x86os_tcp_socket_control_t stats={.version=1,.struct_size=sizeof(stats),.operation=X86OS_TCP_SOCKET_STATS};
        for(unsigned n=0;n<4;n++) {
            const reist_app_tcp_socket *p=&s->sockets[n];if(!p->handle)continue;
            stats.active_sockets++;
            if(p->state==REIST_TCP_ESTABLISHED||p->state==REIST_TCP_CLOSE_WAIT)stats.established_sockets++;
            stats.retransmissions+=p->retransmissions;
        }
        copy(r->payload,&stats,sizeof(stats));r->length=sizeof(stats);return 0;
    }
    if(q->operation==REIST_APP_TCP_OPEN) {
        if(s->issued>=4){r->result=-24;return 0;}
        reist_app_tcp_socket *p=&s->sockets[s->issued];zero(p,sizeof(*p));
        p->local_port=(unsigned)s->grant.local_port+s->issued;
        p->handle=++s->issued;p->rto_ms=1000;p->peer_mss=536;r->handle=p->handle;return 0;
    }
    reist_app_tcp_socket *p=resolve(s,q->handle);
    if(!p){r->result=-9;return 0;}
    if(q->operation==REIST_APP_TCP_CLOSE&&p->state==REIST_TCP_CLOSED){zero(p,sizeof(*p));return 0;}
    if(p->error){r->result=p->error;return 0;}
    if(q->operation==REIST_APP_TCP_CONNECT) {
        if(p->state!=REIST_TCP_CLOSED){r->result=-106;return 0;}
        p->state=REIST_TCP_SYN_SENT;
        p->initial_sequence=(uint32_t)((now<<8)^(s->service>>32)^(s->grant.application>>32)^p->local_port);
        p->send_next=p->send_unacknowledged=p->initial_sequence;
    } else if(p->state!=REIST_TCP_ESTABLISHED&&p->state!=REIST_TCP_CLOSE_WAIT){r->result=-107;return 0;}
    if(q->operation==REIST_APP_TCP_SEND&&!q->length)return 0;
    s->pending=*q;return 1;
}
int reist_app_tcp_finish(reist_app_tcp_state *s,const reist_app_tcp_request *q,reist_app_tcp_request *r,int wire_result,uint64_t now) {
    if(!s||!q||!r||overlap(s,sizeof(*s),q,sizeof(*q))||overlap(s,sizeof(*s),r,sizeof(*r))||overlap(q,sizeof(*q),r,sizeof(*r))||wire_result>0||wire_result< -4095)return -22;
    if(!s->active||!s->pending.operation||!equal(q,&s->pending,sizeof(*q)))return -116;
    if(now<s->last_ms)return -84;
    reist_app_tcp_socket *p=resolve(s,q->handle);if(!p)return -116;
    *r=*q;r->length=0;zero(r->payload,512);
    if(now>=q->deadline||now>=s->grant.expires)wire_result=-110;
    if(!wire_result&&q->operation==REIST_APP_TCP_CONNECT&&p->state!=REIST_TCP_ESTABLISHED&&p->state!=REIST_TCP_CLOSE_WAIT)wire_result=-71;
    if(!wire_result&&q->operation==REIST_APP_TCP_SEND) {
        if(p->send_unacknowledged!=p->send_next)wire_result=-71;
        else r->length=q->length;
    }
    if(!wire_result&&q->operation==REIST_APP_TCP_RECV) {
        if(p->receive_count>2048||p->receive_head>=2048)wire_result=-84;
        else if(!p->receive_count&&!p->peer_fin)wire_result=-11;
        else {
            unsigned n=p->receive_count;if(n>q->length)n=q->length;r->length=n;
            for(unsigned i=0;i<n;i++){r->payload[i]=p->receive[p->receive_head];p->receive[p->receive_head]=0;p->receive_head=(p->receive_head+1)%2048;}
            p->receive_count-=n;
        }
    }
    if(wire_result)abort_connection(p,wire_result);
    if(q->operation==REIST_APP_TCP_CLOSE) {
        if(!wire_result&&p->state!=REIST_TCP_CLOSED&&p->state!=REIST_TCP_TIME_WAIT){wire_result=-71;abort_connection(p,wire_result);}
        if(p->state==REIST_TCP_TIME_WAIT)p->handle=0;else zero(p,sizeof(*p));
    }
    r->result=wire_result;zero(&s->pending,sizeof(s->pending));s->last_ms=now;return 0;
}
static int text_equal(const char *p,const char *q) {
    if(!p||!q)return 0;
    for(unsigned n=0;n<128;n++){if(p[n]!=q[n])return 0;if(!p[n])return 1;}return 0;
}
int reist_app_tcp_operand(int argc,const char *const *argv,reist_app_tcp_grant *out) {
    if(!argv||!out||(argc!=3&&argc!=4)||!text_equal(argv[1],"192.0.2.3")||!argv[2])return -22;
    unsigned port=0;
    for(unsigned n=0;;n++) {
        if(n>=6)return -22;unsigned c=(unsigned char)argv[2][n];if(!c)break;
        if(c<'0'||c>'9')return -22;port=port*10+c-'0';if(port>65535)return -22;
    }
    if(!port)return -22;
    if(argc==4){if(!argv[3])return -22;unsigned n=0;for(;n<=512&&argv[3][n];n++){}if(n>512)return -90;}
    reist_app_tcp_grant g={.version=1,.size=64,.protocol=6,.peer=REIST_APP_TCP_PEER,.peer_port=(uint16_t)port};
    copy(out,&g,sizeof(g));return 0;
}
