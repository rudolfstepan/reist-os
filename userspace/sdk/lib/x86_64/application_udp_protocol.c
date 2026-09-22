/* RFC768 over the existing Ring3 ARP/IPv4 service. All buffers are bounded. */
#include <reist/x86_64/application_udp.h>
#include <reist_udp_parser.h>
typedef struct {
    const reist_net_io *io;
    uint64_t end,last;
    unsigned reads,turns;
    uint8_t last_mac[6];
} operation_io;
static int equal(const uint8_t *a,const uint8_t *b,unsigned n){unsigned d=0;for(unsigned i=0;i<n;i++)d|=a[i]^b[i];return !d;}
static void put16(uint8_t *p,unsigned n){p[0]=(uint8_t)(n>>8);p[1]=(uint8_t)n;}
static void put32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(24-8*i));}
static uint32_t read32(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static uint32_t sum_bytes(const uint8_t *p,unsigned n,uint32_t sum) {
    for(unsigned i=0;i<n;i+=2)sum+=((unsigned)p[i]<<8)|(i+1<n?p[i+1]:0);
    return sum;
}
static uint16_t complement(uint32_t sum) {
    sum=(sum&65535)+(sum>>16);sum=(sum&65535)+(sum>>16);return (uint16_t)~sum;
}
static uint64_t stamp(void *p){operation_io *o=p;return o->io->now(o->io->context);}
static int time_check(operation_io *o) {
    uint64_t now=stamp(o);if(now<o->last)return -84;
    o->last=now;return now>=o->end?-110:0;
}
static int pause_ms(void *p,unsigned ms) {
    operation_io *o=p;int r=time_check(o);if(r)return r;
    if(!ms||ms>10)return -22;
    /* Empty RX must not drive a full IPC/device transaction every tick.
     * Sleep at most100ms before polling again, in the existing bounded
     * increments; all ten sleeps share the original absolute deadline. */
    for(unsigned idle=0;idle<10;idle++) {
        if(++o->turns>200)return -110;
        unsigned delay=ms;if(delay>o->end-o->last)delay=(unsigned)(o->end-o->last);
        r=o->io->sleep(o->io->context,delay);if(r)return r;
        r=time_check(o);if(r)return r;
    }
    return 0;
}
static int send_frame(void *p,const uint8_t *f,unsigned n,uint64_t end) {
    operation_io *o=p;int r=time_check(o);if(r)return r;
    /* ARP accepts a relative timeout and samples its clock again. Preserve
     * the caller's absolute packet deadline across that adapter boundary. */
    if(end>o->end)end=o->end;
    return o->io->send(o->io->context,f,n,end);
}
static int receive_frame(void *p,uint8_t *f,unsigned cap,uint64_t end) {
    operation_io *o=p;int r=time_check(o);if(r)return r;
    if(end>o->end)end=o->end;
    if(o->reads++>=1600)return -110;
    r=o->io->receive(o->io->context,f,cap,end);
    if(r>(int)cap)return -71;
    int checked=time_check(o);if(checked)return checked;
    if(r>=14)reist_net_copy(o->last_mac,f+6,6);
    return r;
}
static int packet_operation(reist_app_udp_state *s,reist_net_protocol *net,const reist_net_io *io,
                            const reist_app_udp_request *q) {
    if(!net->configured||net->ip!=UINT32_C(0xc0000202)||net->mask!=UINT32_C(0xffffff00))return -99;
    uint64_t now=io->now(io->context);if(now>=q->deadline)return -110;
    operation_io op={.io=io,.end=q->deadline,.last=now};
    reist_net_io bounded={&op,stamp,pause_ms,send_frame,receive_frame};
    x86os_network_control_request_t arp={.version=2,.struct_size=sizeof(arp),
        .operation=X86OS_NETWORK_ARP_REQUEST,.target_ip=q->grant.peer,.timeout_ms=(uint32_t)(q->deadline-now)};
    /* The existing ARP validator returns success on precisely its last RX.
     * Only after that success may the intercepted source MAC become a peer. */
    int r=reist_net_protocol_control(net,&arp,&bounded);if(r)return r;
    uint8_t peer[6];reist_net_copy(peer,op.last_mac,6);
    if(q->operation==REIST_APP_UDP_SEND) {
        uint8_t frame[14+20+8+512]={0};unsigned total=28+q->length;
        reist_net_copy(frame,peer,6);reist_net_copy(frame+6,net->mac,6);put16(frame+12,0x800);
        frame[14]=0x45;put16(frame+16,total);put16(frame+18,(uint16_t)net->sequence);
        frame[20]=0x40;frame[22]=64;frame[23]=17;
        put32(frame+26,net->ip);put32(frame+30,q->grant.peer);
        put16(frame+24,complement(sum_bytes(frame+14,20,0)));
        put16(frame+34,q->grant.local_port);put16(frame+36,q->grant.peer_port);put16(frame+38,q->length+8);
        reist_net_copy(frame+42,q->payload,q->length);
        uint16_t checksum=complement(sum_bytes(frame+34,q->length+8,sum_bytes(frame+26,8,17+q->length+8)));
        put16(frame+40,checksum?checksum:65535);
        r=send_frame(&op,frame,14+total,q->deadline);return r?r:time_check(&op);
    }
    uint8_t frame[REIST_NET_FRAME];
    for(unsigned turn=0;turn<200;turn++) {
        unsigned accepted=0;
        for(unsigned batch=0;batch<8;batch++) {
            int n=receive_frame(&op,frame,sizeof(frame),q->deadline);
            if(n==-11)break;if(n<0)return n;
            reist_udp_parse_result_t udp;
            if(n<42||!equal(frame,net->mac,6)||!equal(frame+6,peer,6)||
               read32(frame+26)!=q->grant.peer||read32(frame+30)!=net->ip||
               reist_udp_parse_frame(frame,(unsigned)n,&udp)||udp.source_port!=q->grant.peer_port||
               udp.destination_port!=q->grant.local_port||udp.payload_length>512)continue;
            r=reist_app_udp_enqueue(s,&q->grant,frame+udp.payload_offset,udp.payload_length,op.last);
            if(r&&r!=-105)return r;
            accepted=1;
        }
        if(accepted)return 0;
        r=pause_ms(&op,10);if(r)return r;
    }
    return -110;
}
int reist_app_udp_exchange(reist_app_udp_state *s,reist_net_protocol *net,const reist_net_io *io,
                           const reist_app_udp_request *q,reist_app_udp_request *reply) {
    if(!net||!io||!io->now||!io->sleep||!io->send||!io->receive)return -22;
    int r=reist_app_udp_begin(s,q,reply,io->now(io->context));if(r!=1)return r;
    r=packet_operation(s,net,io,q);
    return reist_app_udp_finish(s,q,reply,r,io->now(io->context));
}
