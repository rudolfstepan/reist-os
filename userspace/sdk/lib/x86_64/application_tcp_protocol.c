/* Bounded Ring3 TCP client: RFC9293 state/sequence rules and RFC6298 timers. */
#include <reist/x86_64/application_tcp.h>
#include <reist_tcp_parser.h>
#define FIN 1U
#define SYN 2U
#define RST 4U
#define PSH 8U
#define ACK 16U
typedef struct {
    reist_app_tcp_state *table;
    reist_app_tcp_socket *socket;
    reist_net_protocol *net;
    const reist_net_io *io;
    const reist_app_tcp_request *request;
    uint64_t end,last;
    unsigned reads,sleeps,offset;
    uint8_t last_mac[6];
} tcp_operation;
static int equal(const uint8_t *p,const uint8_t *q,unsigned n){unsigned d=0;for(unsigned i=0;i<n;i++)d|=p[i]^q[i];return !d;}
static void put16(uint8_t *p,unsigned n){p[0]=(uint8_t)(n>>8);p[1]=(uint8_t)n;}
static void put32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(24-8*i));}
static uint32_t read32(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static uint32_t sum(const uint8_t *p,unsigned n,uint32_t v){for(unsigned i=0;i<n;i+=2)v+=((unsigned)p[i]<<8)|(i+1<n?p[i+1]:0);return v;}
static uint16_t checksum(uint32_t n){n=(n&65535)+(n>>16);n=(n&65535)+(n>>16);return (uint16_t)~n;}
static int before(uint32_t a,uint32_t b){return (int32_t)(a-b)<0;}
static uint64_t now(void *p){tcp_operation *o=p;return o->io->now(o->io->context);}
static int time_check(tcp_operation *o) {
    uint64_t n=now(o);if(n<o->last)return -84;o->last=n;
    return n>=o->end?-110:0;
}
static int pause_ms(void *p,unsigned ms) {
    tcp_operation *o=p;if(!ms||ms>10)return -22;int r=time_check(o);if(r)return r;
    for(unsigned n=0;n<10;n++) {
        if(++o->sleeps>200)return -110;
        unsigned delay=ms;if(delay>o->end-o->last)delay=(unsigned)(o->end-o->last);
        r=o->io->sleep(o->io->context,delay);if(r)return r;
        if((r=time_check(o)))return r;
    }
    return 0;
}
static int send_frame(void *p,const uint8_t *frame,unsigned length,uint64_t end) {
    tcp_operation *o=p;int r=time_check(o);if(r)return r;
    if(end>o->end)end=o->end;
    r=o->io->send(o->io->context,frame,length,end);return r?r:time_check(o);
}
static int receive_frame(void *p,uint8_t *frame,unsigned capacity,uint64_t end) {
    tcp_operation *o=p;int r=time_check(o);if(r)return r;
    if(end>o->end)end=o->end;if(o->reads++>=1600)return -110;
    r=o->io->receive(o->io->context,frame,capacity,end);if(r>(int)capacity)return -71;
    int checked=time_check(o);if(checked)return checked;
    if(r>=14)reist_net_copy(o->last_mac,frame+6,6);return r;
}
static int wire(tcp_operation *o,uint32_t sequence,unsigned flags,const uint8_t *data,unsigned length) {
    reist_app_tcp_socket *p=o->socket;
    if(length>512||p->receive_count>2048)return -84;
    unsigned header=(flags&SYN)?24:20,total=20+header+length;
    uint8_t frame[14+20+24+512]={0};
    reist_net_copy(frame,p->peer_mac,6);reist_net_copy(frame+6,o->net->mac,6);
    put16(frame+12,0x800);frame[14]=0x45;put16(frame+16,total);frame[20]=0x40;frame[22]=64;frame[23]=6;
    put32(frame+26,o->net->ip);put32(frame+30,o->request->grant.peer);
    put16(frame+24,checksum(sum(frame+14,20,0)));
    put16(frame+34,p->local_port);put16(frame+36,o->request->grant.peer_port);
    put32(frame+38,sequence);put32(frame+42,(flags&ACK)?p->receive_next:0);
    frame[46]=(uint8_t)(header<<2);frame[47]=(uint8_t)flags;put16(frame+48,2048-p->receive_count);
    if(flags&SYN){frame[54]=2;frame[55]=4;put16(frame+56,512);}
    if(length)reist_net_copy(frame+34+header,data,length);
    put16(frame+50,checksum(sum(frame+34,header+length,sum(frame+26,8,6+header+length))));
    return send_frame(o,frame,14+total,o->end);
}
static int acknowledge(tcp_operation *o){return wire(o,o->socket->send_next,ACK,0,0);}
static void sample_rtt(reist_app_tcp_socket *p,uint64_t stamp) {
    if(p->tx_retransmitted||!p->tx_retries||stamp<p->sent_at)return;
    uint64_t elapsed=stamp-p->sent_at;if(elapsed>2000)return;
    unsigned r=(unsigned)elapsed;if(!r)r=1;
    if(!p->srtt8){p->srtt8=8*r;p->rttvar4=2*r;}
    else {
        unsigned old=p->srtt8/8,difference=old>r?old-r:r-old;
        p->rttvar4=(3*p->rttvar4)/4+difference;
        p->srtt8=(7*p->srtt8)/8+r;
    }
    unsigned variance=p->rttvar4;if(variance<10)variance=10;
    p->rto_ms=p->srtt8/8+variance;if(p->rto_ms<1000)p->rto_ms=1000;
}
static int options(const uint8_t *frame,const reist_tcp_parse_result_t *segment,unsigned *mss) {
    unsigned length=segment->header_length,seen=0,base=segment->payload_offset-length;*mss=536;
    for(unsigned at=20;at<length;) {
        unsigned kind=frame[base+at];if(!kind)return 0;if(kind==1){at++;continue;}
        if(length-at<2)return -71;unsigned size=frame[base+at+1];if(size<2||size>length-at)return -71;
        if(kind==2){if(seen++||size!=4)return -71;*mss=((unsigned)frame[base+at+2]<<8)|frame[base+at+3];if(!*mss)return -71;}
        at+=size;
    }
    return 0;
}
static int ingress(tcp_operation *o,const uint8_t *frame,unsigned length) {
    reist_app_tcp_socket *p=o->socket;reist_tcp_parse_result_t segment;
    if(length<54||!equal(frame,o->net->mac,6)||!equal(frame+6,p->peer_mac,6)||
       read32(frame+26)!=o->request->grant.peer||read32(frame+30)!=o->net->ip||
       reist_tcp_parse_frame(frame,length,&segment)||segment.source_port!=o->request->grant.peer_port||
       segment.destination_port!=p->local_port||segment.payload_length>512)return 0;
    unsigned mss;if(options(frame,&segment,&mss))return 0;
    uint32_t seq=segment.sequence,ack=segment.acknowledgement;unsigned flags=segment.flags;
    if(p->state==REIST_TCP_SYN_SENT) {
        if(flags==(RST|ACK)&&ack==p->send_next&&!segment.payload_length)return -111;
        if(flags!=(SYN|ACK)||ack!=p->send_next||segment.payload_length)return 0;
        p->receive_next=seq+1;p->send_unacknowledged=ack;p->peer_window=segment.window;p->peer_mss=mss;
        p->window_sequence=seq;p->window_ack=ack;p->state=REIST_TCP_ESTABLISHED;
        sample_rtt(p,o->last);if(p->tx_retransmitted&&p->rto_ms<3000)p->rto_ms=3000;
        return acknowledge(o);
    }
    if(flags==(SYN|ACK)&&seq+1==p->receive_next&&ack==p->initial_sequence+1&&!segment.payload_length)return acknowledge(o);
    if(p->receive_count>2048||p->receive_head>=2048)return -84;
    unsigned available=2048-p->receive_count,span=segment.payload_length+((flags&FIN)?1:0);
    if(before(seq,p->receive_next)) {
        if(!span||p->receive_next-seq>=span)return span?acknowledge(o):0;
    } else if((span&&!available)||(!span&&!available&&seq!=p->receive_next)||
              (available&&seq-p->receive_next>=available))return (flags&RST)?0:acknowledge(o);
    if(flags&RST)return seq==p->receive_next?-104:acknowledge(o);
    if((flags&(SYN|32))||!(flags&ACK))return 0;
    if(before(p->send_next,ack))return acknowledge(o);
    if(!before(ack,p->send_unacknowledged)) {
        if(ack!=p->send_unacknowledged&&ack==p->tx_end)sample_rtt(p,o->last);
        /* RFC6298 5.3: newly acknowledged bytes restart the retransmission
         * timer for the remaining flight; the operation deadline stays fixed. */
        if(ack!=p->send_unacknowledged&&ack!=p->send_next)
            p->retry_at=o->last>UINT64_MAX-p->rto_ms?UINT64_MAX:o->last+p->rto_ms;
        p->send_unacknowledged=ack;
        if(before(p->window_sequence,seq)||(p->window_sequence==seq&&!before(ack,p->window_ack))) {
            p->peer_window=segment.window;p->window_sequence=seq;p->window_ack=ack;
        }
        if(ack==p->send_next) {
            if(p->state==REIST_TCP_FIN_WAIT_1)p->state=REIST_TCP_FIN_WAIT_2;
            else if(p->state==REIST_TCP_CLOSING)p->state=REIST_TCP_TIME_WAIT;
            else if(p->state==REIST_TCP_LAST_ACK){p->state=REIST_TCP_CLOSED;return 0;}
        }
    }
    if(before(p->receive_next,seq))return span?acknowledge(o):0;
    unsigned skip=p->receive_next-seq;
    unsigned count=segment.payload_length>skip?segment.payload_length-skip:0;
    if(p->peer_fin&&count)return acknowledge(o);
    if(count>available)count=available;
    for(unsigned n=0;n<count;n++)p->receive[(p->receive_head+p->receive_count+n)%2048]=frame[segment.payload_offset+skip+n];
    p->receive_count+=count;p->receive_next+=count;
    if((flags&FIN)&&!p->peer_fin&&seq+segment.payload_length==p->receive_next&&available>count) {
        p->peer_fin=1;p->receive_next++;
        if(p->state==REIST_TCP_ESTABLISHED)p->state=REIST_TCP_CLOSE_WAIT;
        else if(p->state==REIST_TCP_FIN_WAIT_1)p->state=REIST_TCP_CLOSING;
        else if(p->state==REIST_TCP_FIN_WAIT_2)p->state=REIST_TCP_TIME_WAIT;
    }
    return span?acknowledge(o):0;
}
static void prepare_tx(tcp_operation *o,unsigned flags,unsigned length) {
    reist_app_tcp_socket *p=o->socket;
    p->tx_start=p->send_next;p->tx_length=length;p->tx_flags=flags;p->tx_acked=0;
    p->send_next+=length+((flags&(SYN|FIN))?1:0);p->tx_end=p->send_next;
    p->tx_retries=p->tx_retransmitted=0;p->retry_at=0;
}
static int transmit(tcp_operation *o) {
    reist_app_tcp_socket *p=o->socket;int r=time_check(o);if(r)return r;
    if(p->send_unacknowledged==p->send_next||o->last<p->retry_at)return 0;
    if(p->tx_retries>=2)return -110;
    unsigned acknowledged=p->send_unacknowledged-p->tx_start;
    if(acknowledged>p->tx_length&&!(p->tx_flags&(SYN|FIN)))return -84;
    unsigned bytes=p->tx_length>acknowledged?p->tx_length-acknowledged:0;
    if(p->tx_retries){if(p->rto_ms>UINT32_MAX/2)return -75;p->rto_ms*=2;p->tx_retransmitted=1;p->retransmissions++;}
    r=wire(o,p->send_unacknowledged,p->tx_flags,bytes?o->request->payload+o->offset+acknowledged:0,bytes);
    if(r)return r;p->tx_retries++;p->sent_at=o->last;
    p->retry_at=o->last>UINT64_MAX-p->rto_ms?UINT64_MAX:o->last+p->rto_ms;return 0;
}
static int complete(tcp_operation *o,unsigned waiting) {
    reist_app_tcp_socket *p=o->socket;
    if(waiting==1)return p->send_unacknowledged==p->send_next;
    if(waiting==2)return p->receive_count||p->peer_fin;
    if(waiting==3)return p->state==REIST_TCP_CLOSED||p->state==REIST_TCP_TIME_WAIT;
    return p->peer_window!=0;
}
static int wait_for(tcp_operation *o,unsigned waiting) {
    uint8_t frame[REIST_NET_FRAME];
    for(unsigned turn=0;turn<200;turn++) {
        int r=time_check(o);if(r)return r;
        if(complete(o,waiting))return 0;
        if((waiting==1||waiting==3)&&(r=transmit(o)))return r;
        for(unsigned batch=0;batch<8;batch++) {
            int length=receive_frame(o,frame,sizeof(frame),o->end);
            if(length==-11)break;if(length<0)return length;
            if((r=ingress(o,frame,(unsigned)length)))return r;
        }
        if(complete(o,waiting))return 0;
        if((r=pause_ms(o,10)))return r;
    }
    return -110;
}
static int operate(tcp_operation *o) {
    reist_app_tcp_socket *p=o->socket;const reist_app_tcp_request *q=o->request;int r;
    if(!o->net->configured||o->net->ip!=0xc0000202||o->net->mask!=0xffffff00)return -99;
    if(q->operation==REIST_APP_TCP_CONNECT) {
        reist_net_io bounded={o,now,pause_ms,send_frame,receive_frame};
        x86os_network_control_request_t arp={.version=2,.struct_size=sizeof(arp),.operation=X86OS_NETWORK_ARP_REQUEST,
            .target_ip=q->grant.peer,.timeout_ms=(uint32_t)(o->end-o->last)};
        r=reist_net_protocol_control(o->net,&arp,&bounded);if(r)return r;
        reist_net_copy(p->peer_mac,o->last_mac,6);prepare_tx(o,SYN,0);return wait_for(o,1);
    }
    if(q->operation==REIST_APP_TCP_SEND) {
        for(unsigned fragment=0;o->offset<q->length&&fragment<512;fragment++) {
            if(!p->peer_window){r=wait_for(o,4);if(r)return r;}
            unsigned n=q->length-o->offset;if(n>p->peer_mss)n=p->peer_mss;if(n>p->peer_window)n=p->peer_window;
            if(!n)return -71;prepare_tx(o,ACK|PSH,n);r=wait_for(o,1);if(r)return r;o->offset+=n;
        }
        return o->offset==q->length?0:-110;
    }
    if(q->operation==REIST_APP_TCP_RECV)return wait_for(o,2);
    if(q->operation==REIST_APP_TCP_CLOSE) {
        if(p->receive_count){r=wire(o,p->send_next,RST|ACK,0,0);if(!r)p->state=REIST_TCP_CLOSED;return r;}
        p->state=p->state==REIST_TCP_CLOSE_WAIT?REIST_TCP_LAST_ACK:REIST_TCP_FIN_WAIT_1;
        prepare_tx(o,FIN|ACK,0);return wait_for(o,3);
    }
    return -22;
}
int reist_app_tcp_exchange(reist_app_tcp_state *s,reist_net_protocol *net,const reist_net_io *io,
                           const reist_app_tcp_request *q,reist_app_tcp_request *reply) {
    if(!net||!io||!io->now||!io->sleep||!io->send||!io->receive)return -22;
    uint64_t stamp=io->now(io->context);int r=reist_app_tcp_begin(s,q,reply,stamp);if(r!=1)return r;
    tcp_operation op={.table=s,.socket=&s->sockets[q->handle-1],.net=net,.io=io,.request=q,.end=q->deadline,.last=stamp};
    r=operate(&op);int result=reist_app_tcp_finish(s,q,reply,r,io->now(io->context));
    if(!result&&!reply->result&&q->operation==REIST_APP_TCP_RECV&&reply->length) {
        r=acknowledge(&op);
        if(r){op.socket->state=REIST_TCP_CLOSED;op.socket->error=r;
            op.socket->receive_head=op.socket->receive_count=0;reist_net_zero(op.socket->receive,2048);
            reply->result=r;reply->length=0;reist_net_zero(reply->payload,512);}
    }
    return result;
}
