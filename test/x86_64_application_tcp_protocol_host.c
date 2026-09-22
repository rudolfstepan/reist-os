#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_tcp.h>
#include <reist_tcp_parser.h>
static uint64_t stamp,deadline,first_syn,first_data;
static unsigned mode,head,count,syns,data_sends,delivered,fin_sends,rx_calls,partial,window_update,zero_acks;
static unsigned receiving,inbound_sent;
static uint32_t client_next,server_next,last_ack;
static uint16_t client_port;
static uint8_t frames[16][600];static unsigned lengths[16];
static const uint8_t local[6]={2,0,0,0,0,2},peer[6]={2,0,0,0,0,3};
static void put16(uint8_t *p,unsigned v){p[0]=(uint8_t)(v>>8);p[1]=(uint8_t)v;}
static void put32(uint8_t *p,uint32_t v){for(unsigned n=0;n<4;n++)p[n]=(uint8_t)(v>>(24-n*8));}
static uint32_t sum(const uint8_t *p,unsigned n,uint32_t v){for(unsigned i=0;i<n;i+=2)v+=((unsigned)p[i]<<8)|(i+1<n?p[i+1]:0);return v;}
static uint16_t checksum(uint32_t n){n=(n&65535)+(n>>16);n=(n&65535)+(n>>16);return (uint16_t)~n;}
static void enqueue(const uint8_t *frame,unsigned length){assert(count<16&&length<=600);unsigned at=(head+count++)%16;memcpy(frames[at],frame,length);lengths[at]=length;}
static void segment(uint32_t seq,uint32_t ack,unsigned flags,const uint8_t *data,unsigned length) {
    uint8_t frame[600]={0};unsigned header=(flags&2)?24:20,total=20+header+length;
    memcpy(frame,local,6);memcpy(frame+6,peer,6);put16(frame+12,0x800);frame[14]=0x45;
    put16(frame+16,total);frame[20]=0x40;frame[22]=64;frame[23]=6;
    put32(frame+26,0xc0000203);put32(frame+30,0xc0000202);put16(frame+24,checksum(sum(frame+14,20,0)));
    put16(frame+34,5000);put16(frame+36,client_port);put32(frame+38,seq);put32(frame+42,ack);
    frame[46]=(uint8_t)(header<<2);frame[47]=(uint8_t)flags;
    put16(frame+48,((mode==9||mode==10)&&!window_update)?0:2048);
    if(flags&2){frame[54]=2;frame[55]=4;put16(frame+56,mode==12?256:512);}
    if(length)memcpy(frame+34+header,data,length);
    put16(frame+50,checksum(sum(frame+34,header+length,sum(frame+26,8,6+header+length))));
    if(mode==4&&length){uint8_t bad[600];memcpy(bad,frame,14+total);bad[50]^=1;enqueue(bad,14+total);}
    enqueue(frame,14+total);
}
static uint64_t clock_now(void *p){(void)p;return stamp;}
static int pause_ms(void *p,unsigned n){(void)p;assert(n&&n<=10&&stamp+n<=deadline);stamp+=n;return 0;}
static int send_frame(void *p,const uint8_t *frame,unsigned length,uint64_t end) {
    (void)p;assert(stamp<end&&end==deadline);
    if(frame[13]==6) {
        assert(length==42);uint8_t reply[42];memcpy(reply,frame,42);memcpy(reply,local,6);memcpy(reply+6,peer,6);
        reply[21]=2;memcpy(reply+22,peer,6);memcpy(reply+28,frame+38,4);memcpy(reply+32,local,6);memcpy(reply+38,frame+28,4);
        enqueue(reply,42);return 0;
    }
    reist_tcp_parse_result_t tcp;assert(!reist_tcp_parse_frame(frame,length,&tcp));
    assert(tcp.source_port==49164&&tcp.destination_port==5000);client_port=tcp.source_port;
    assert(!memcmp(frame,peer,6)&&!memcmp(frame+6,local,6));
    if(tcp.flags==2) {
        assert(tcp.header_length==24&&frame[54]==2&&frame[55]==4&&frame[56]==2&&frame[57]==0);
        if(!syns)first_syn=stamp;else assert(stamp-first_syn>=1000);
        syns++;client_next=tcp.sequence+1;server_next=0xfffffff1U;
        if(mode==3||(mode==1&&syns==1))return 0;
        segment(server_next-1,client_next,18,0,0);return 0;
    }
    if(tcp.payload_length) {
        unsigned offset=(mode==8&&data_sends)||mode==12?256:0;
        assert(tcp.flags==24&&tcp.payload_length==512-offset);
        for(unsigned n=0;n<tcp.payload_length;n++)assert(frame[tcp.payload_offset+n]==(uint8_t)(n+offset));
        if(!data_sends)first_data=stamp;else if(mode!=12)assert(stamp-first_data>=1000);
        if(mode==8&&data_sends)assert(stamp-first_data>=1500);
        if(mode==9)assert(window_update&&stamp-first_syn>=500);
        data_sends++;
        if(mode==12){client_next=tcp.sequence+tcp.payload_length;delivered+=tcp.payload_length;}
        else if(!delivered){client_next=tcp.sequence+tcp.payload_length;delivered=512;}
        else assert(tcp.sequence+tcp.payload_length==client_next);
        if(mode==12&&delivered<512){segment(server_next,client_next,16,0,0);return 0;}
        if(mode==13){segment(server_next+32,client_next,16,0,0);return 0;}
        if((mode==2||mode==8)&&data_sends==1)return 0;
        if(mode==6){segment(server_next,client_next,20,0,0);return 0;}
        segment(server_next,client_next,16,0,0);
        uint8_t bytes[512];for(unsigned n=0;n<512;n++)bytes[n]=(uint8_t)n;
        if(mode==11) {
            /* Out of order, overlapping retransmit, ring saturation, then
             * a segment beyond a zero receive window. Every byte is unique
             * in sequence space even though the byte pattern wraps at 256. */
            const unsigned offsets[]={512,0,256,768,1280,1792,2048};
            for(unsigned index=0;index<7;index++) {
                for(unsigned n=0;n<512;n++)bytes[n]=(uint8_t)((offsets[index]+n)/256);
                segment(server_next+offsets[index],client_next,24,bytes,512);
            }
            server_next+=2048;return 0;
        }
        segment(server_next,client_next,24,bytes,512);server_next+=512;
        if(mode!=7){segment(server_next,client_next,17,0,0);server_next++;}
        return 0;
    }
    if(tcp.flags==17) {
        fin_sends++;client_next=tcp.sequence+1;segment(server_next,client_next,16,0,0);
        if(mode==7||mode==11){segment(server_next,client_next,17,0,0);server_next++;}
        return 0;
    }
    assert(tcp.flags==16);
    if(!tcp.window)zero_acks++;
    /* The peer can queue data and FIN before either cumulative ACK arrives. */
    assert(tcp.acknowledgement-last_ack<=server_next-last_ack);
    last_ack=tcp.acknowledgement;return 0;
}
static int receive_frame(void *p,uint8_t *frame,unsigned cap,uint64_t end) {
    (void)p;assert(cap==1514&&stamp<end&&end==deadline);rx_calls++;
    if(mode==13&&receiving&&!inbound_sent) {
        uint8_t bytes[512];for(unsigned n=0;n<512;n++)bytes[n]=(uint8_t)n;
        segment(server_next,client_next,24,bytes,512);server_next+=512;
        segment(server_next,client_next,17,0,0);server_next++;inbound_sent=1;
    }
    if(mode==8&&data_sends==1&&!partial&&stamp-first_data>=500) {
        partial=1;segment(server_next,client_next-256,16,0,0);
    }
    if(mode==9&&!window_update&&syns&&stamp-first_syn>=500) {
        window_update=1;segment(server_next,client_next,16,0,0);
    }
    if(!count)return -11;unsigned n=lengths[head];memcpy(frame,frames[head],n);head=(head+1)%16;count--;return (int)n;
}
int main(void) {
    for(mode=0;mode<=13;mode++) {
        stamp=mode==5?0xffff3f:100;head=count=syns=data_sends=delivered=fin_sends=rx_calls=partial=window_update=zero_acks=0;last_ack=0xfffffff1U;
        receiving=inbound_sent=0;
        reist_app_tcp_state state;reist_net_protocol net;
        reist_app_tcp_grant grant={1,64,1ULL<<32,(4ULL<<32)|6,(3ULL<<32)|5,1,stamp+6000,6,0xc0000203,49164,5000,0};
        assert(!reist_app_tcp_init(&state,grant.root,grant.service,stamp));assert(!reist_app_tcp_grant_set(&state,&grant,stamp));
        assert(!reist_net_protocol_init(&net,local,11));net.configured=1;net.ip=0xc0000202;net.mask=0xffffff00;
        reist_net_io io={0,clock_now,pause_ms,send_frame,receive_frame};
        reist_app_tcp_request q={.grant=grant,.sequence=1,.deadline=stamp+2000,.operation=REIST_APP_TCP_OPEN},r;
        deadline=q.deadline;assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r)&&!r.result);q.handle=r.handle;
        q.sequence++;q.operation=REIST_APP_TCP_CONNECT;
        assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r));
        if(mode==3){assert(r.result==-110&&syns==2&&rx_calls<=22);continue;}
        assert(!r.result&&state.sockets[0].state==REIST_TCP_ESTABLISHED);
        assert(syns==(mode==1?2U:1U));
        q.sequence++;q.operation=REIST_APP_TCP_SEND;q.length=512;q.deadline=stamp+2000;deadline=q.deadline;
        for(unsigned n=0;n<512;n++)q.payload[n]=(uint8_t)n;
        assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r));
        if(mode==6){assert(r.result==-104&&state.sockets[0].error==-104);continue;}
        if(mode==10){assert(r.result==-110&&!data_sends&&state.sockets[0].error==-110);continue;}
        assert(!r.result&&r.length==512&&delivered==512&&data_sends==((mode==2||mode==8||mode==12)?2U:1U));
        if(mode==11)assert(zero_acks==2);
        q.sequence++;q.operation=REIST_APP_TCP_RECV;q.deadline=stamp+1000;deadline=q.deadline;memset(q.payload,0,512);
        receiving=1;
        assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r)&&!r.result&&r.length==512);
        for(unsigned n=0;n<512;n++)assert(r.payload[n]==(uint8_t)(mode==11?n/256:n));
        if(mode==11) {
            assert(state.sockets[0].receive_count==1536);
            for(unsigned part=0;part<3;part++) {
                q.sequence++;
                assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r)&&!r.result&&r.length==512);
                for(unsigned n=0;n<512;n++)assert(r.payload[n]==(uint8_t)(((part+1)*512+n)/256));
            }
            assert(!state.sockets[0].receive_count);
        }
        q.sequence++;q.operation=REIST_APP_TCP_CLOSE;q.length=0;q.deadline=stamp+1000;deadline=q.deadline;
        assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r)&&!r.result&&fin_sends==1&&!state.sockets[0].handle);
        if(mode==7)assert(state.sockets[0].state==REIST_TCP_TIME_WAIT);
        q.sequence++;q.operation=REIST_APP_TCP_RELEASE;q.handle=0;
        assert(!reist_app_tcp_exchange(&state,&net,&io,&q,&r)&&!r.result&&!state.active);
    }
    return 0;
}
