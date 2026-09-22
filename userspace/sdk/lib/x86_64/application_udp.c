/* Ring3 object authority and bounded queues. No syscall, allocator or IRQ use. */
#include <reist/x86_64/application_udp.h>
#include <stddef.h>
static void zero(void *p,size_t n){volatile uint8_t *b=p;while(n--)*b++=0;}
static void copy(void *p,const void *q,size_t n){uint8_t *a=p;const uint8_t *b=q;while(n--)*a++=*b++;}
static int equal(const void *p,const void *q,size_t n){const uint8_t *a=p,*b=q;unsigned d=0;while(n--)d|=*a++^*b++;return !d;}
static int empty(const void *p,size_t n){const uint8_t *b=p;while(n--)if(*b++)return 0;return 1;}
static int identity(uint64_t id,unsigned slot){return (uint32_t)id==slot&&(id>>32)&&id>>32<=0x7fffffff;}
static int overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x>UINTPTR_MAX-an||y>UINTPTR_MAX-bn||(x<y+bn&&y<x+an);
}
static int valid(const reist_app_udp_state *s,const reist_app_udp_grant *g,uint64_t now) {
    if(!s||!g)return -22;
    if(!s->active||!equal(g,&s->grant,sizeof(*g)))return -116;
    if(now<s->last_ms)return -84;
    if(now>=g->expires)return -110;
    return 0;
}
int reist_app_udp_init(reist_app_udp_state *s,uint64_t root,uint64_t service,uint64_t now) {
    if(!s||!identity(root,0)||!identity(service,5)||root>>32>=service>>32)return -22;
    zero(s,sizeof(*s));s->root=root;s->service=service;s->last_ms=now;return 0;
}
int reist_app_udp_grant_set(reist_app_udp_state *s,const reist_app_udp_grant *g,uint64_t now) {
    if(!s||!g||overlap(s,sizeof(*s),g,sizeof(*g)))return -22;
    if(s->active)return -16;
    if(!identity(s->root,0)||!identity(s->service,5)||g->version!=1||g->size!=64||g->reserved||
       g->root!=s->root||g->service!=s->service||!identity(g->application,6)||
       g->application>>32<=s->root>>32||g->application>>32==s->service>>32||
       g->protocol!=17||g->peer!=REIST_APP_UDP_PEER||!g->local_port||!g->peer_port)return -22;
    if(!g->epoch||g->epoch<=s->last_epoch)return -116;
    if(now<s->last_ms)return -84;
    if(g->expires<=now||g->expires-now>REIST_APP_UDP_MS)return -110;
    s->grant=*g;s->last_epoch=g->epoch;s->last_ms=now;s->sequence=0;s->active=1;return 0;
}
void reist_app_udp_revoke(reist_app_udp_state *s) {
    if(!s)return;
    s->active=0;zero(&s->grant,sizeof(s->grant));zero(&s->pending,sizeof(s->pending));
    zero(s->sockets,sizeof(s->sockets));s->sequence=0;
    /* issued and last_epoch survive close/revoke; no handle/epoch wrap reuse. */
}
static reist_app_udp_socket *resolve(reist_app_udp_state *s,unsigned handle) {
    if(!handle)return 0;
    for(unsigned n=0;n<REIST_APP_UDP_SOCKETS;n++)if(s->sockets[n].handle==handle)return &s->sockets[n];
    return 0;
}
static int take(reist_app_udp_socket *p,reist_app_udp_request *r) {
    if(!p->count)return -11;
    if(p->head>=REIST_APP_UDP_QUEUE||p->count>REIST_APP_UDP_QUEUE)return -84;
    reist_app_udp_datagram *d=&p->queue[p->head];
    if(d->length>REIST_APP_UDP_BYTES)return -84;
    if(d->length>r->length)return -90;
    r->length=d->length;copy(r->payload,d->payload,d->length);zero(d,sizeof(*d));
    p->head=(p->head+1)%REIST_APP_UDP_QUEUE;p->count--;return 0;
}
int reist_app_udp_begin(reist_app_udp_state *s,const reist_app_udp_request *q,reist_app_udp_request *r,uint64_t now) {
    if(!s||!q||!r||overlap(s,sizeof(*s),q,sizeof(*q))||overlap(s,sizeof(*s),r,sizeof(*r))||
       overlap(q,sizeof(*q),r,sizeof(*r)))return -22;
    int result=valid(s,&q->grant,now);if(result)return result;
    if(q->result||q->operation<REIST_APP_UDP_OPEN||q->operation>REIST_APP_UDP_RELEASE||q->length>512)return -22;
    if(q->operation==REIST_APP_UDP_SEND) {
        if(!empty(q->payload+q->length,512-q->length))return -22;
    } else if(!empty(q->payload,512))return -22;
    if(((q->operation==REIST_APP_UDP_OPEN||q->operation==REIST_APP_UDP_RELEASE)&&q->handle)||
       (q->operation!=REIST_APP_UDP_SEND&&q->operation!=REIST_APP_UDP_RECEIVE&&q->length))return -22;
    if(q->deadline<=now||q->deadline>q->grant.expires||q->deadline-now>2000)return -110;
    if(s->sequence>=REIST_APP_UDP_REQUESTS)return -122;
    if(q->sequence!=s->sequence+1)return -116;
    if(s->pending.operation)return -16;
    *r=*q;zero(r->payload,512);s->sequence=q->sequence;s->last_ms=now;
    if(q->operation==REIST_APP_UDP_RELEASE){reist_app_udp_revoke(s);return 0;}
    reist_app_udp_socket *p=resolve(s,q->handle);
    if(q->operation==REIST_APP_UDP_OPEN) {
        if(s->issued==UINT32_MAX){r->result=-75;return 0;}
        for(unsigned n=0;n<REIST_APP_UDP_SOCKETS;n++)if(!s->sockets[n].handle) {
            p=&s->sockets[n];zero(p,sizeof(*p));p->handle=++s->issued;r->handle=p->handle;return 0;
        }
        r->result=-24;return 0;
    }
    if(!p){r->result=-9;return 0;}
    if(q->operation==REIST_APP_UDP_CLOSE){zero(p,sizeof(*p));return 0;}
    if(q->operation==REIST_APP_UDP_BIND) {
        if(p->bound){r->result=-22;return 0;}
        for(unsigned n=0;n<REIST_APP_UDP_SOCKETS;n++)if(s->sockets[n].bound){r->result=-98;return 0;}
        p->bound=1;return 0;
    }
    if(!p->bound){r->result=-99;return 0;}
    if(q->operation==REIST_APP_UDP_RECEIVE&&p->count){r->result=take(p,r);return 0;}
    s->pending=*q;return 1;
}
int reist_app_udp_finish(reist_app_udp_state *s,const reist_app_udp_request *q,reist_app_udp_request *r,int wire_result,uint64_t now) {
    if(!s||!q||!r||overlap(s,sizeof(*s),q,sizeof(*q))||overlap(s,sizeof(*s),r,sizeof(*r))||
       overlap(q,sizeof(*q),r,sizeof(*r))||wire_result>0||wire_result< -4095)return -22;
    if(!s->active||!s->pending.operation||!equal(q,&s->pending,sizeof(*q)))return -116;
    if(now<s->last_ms)return -84;
    reist_app_udp_socket *p=resolve(s,q->handle);if(!p||!p->bound)return -116;
    *r=*q;zero(r->payload,512);r->result=wire_result;
    if(now>=q->deadline||now>=s->grant.expires)r->result=-110;
    else if(!wire_result&&q->operation==REIST_APP_UDP_RECEIVE)r->result=take(p,r);
    zero(&s->pending,sizeof(s->pending));s->last_ms=now;return 0;
}
int reist_app_udp_enqueue(reist_app_udp_state *s,const reist_app_udp_grant *g,const uint8_t *data,unsigned length,uint64_t now) {
    if(!s||!g||length>512||(length&&!data)||overlap(s,sizeof(*s),g,sizeof(*g))||
       (length&&overlap(s,sizeof(*s),data,length)))return -22;
    int r=valid(s,g,now);if(r)return r;
    for(unsigned n=0;n<REIST_APP_UDP_SOCKETS;n++)if(s->sockets[n].handle&&s->sockets[n].bound) {
        reist_app_udp_socket *p=&s->sockets[n];
        if(p->head>=REIST_APP_UDP_QUEUE||p->count>REIST_APP_UDP_QUEUE)return -84;
        if(p->count==REIST_APP_UDP_QUEUE)return -105;
        reist_app_udp_datagram *d=&p->queue[(p->head+p->count)%REIST_APP_UDP_QUEUE];
        zero(d,sizeof(*d));d->length=length;if(length)copy(d->payload,data,length);
        p->count++;s->last_ms=now;return 0;
    }
    return -99;
}
static int text_equal(const char *a,const char *b) {
    if(!a)return 0;
    for(unsigned n=0;n<16;n++){if(a[n]!=b[n])return 0;if(!a[n])return 1;}return 0;
}
static int port(const char *p,uint16_t *out) {
    if(!p||!*p)return -22;unsigned value=0;
    for(unsigned n=0;n<6;n++) {
        unsigned c=(unsigned char)p[n];
        if(!c){if(!value)return -22;*out=(uint16_t)value;return 0;}
        if(c<'0'||c>'9')return -22;value=value*10+c-'0';if(value>65535)return -22;
    }
    return -22;
}
int reist_app_udp_operand(int argc,const char *const *argv,reist_app_udp_grant *out) {
    if(!argv||!out||argc<5||argc>6)return -22;
    int send=text_equal(argv[1],"send"),receive=text_equal(argv[1],"recv");
    if((!send&&!receive)||(send&&argc!=6)||!text_equal(argv[2],"192.0.2.3"))return -22;
    reist_app_udp_grant result={.version=1,.size=64,.protocol=17,.peer=REIST_APP_UDP_PEER};
    if(port(argv[3],&result.peer_port)||port(argv[4],&result.local_port))return -22;
    if(send) {
        if(!argv[5])return -22;
        unsigned n=0;while(n<=512&&argv[5][n])n++;if(n>512)return -90;
    } else if(argc==6) {
        uint16_t timeout;if(port(argv[5],&timeout)||timeout>2000)return -22;
    }
    *out=result;return 0;
}
