#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_udp.h>
#include <reist_udp_parser.h>
static uint64_t now=100;
static uint64_t original_end;
static unsigned sent,pending,mode,reads;
static uint8_t arp_reply[42],datagram[554];
static unsigned datagram_size;
static const uint8_t local[6]={2,0,0,0,0,2},peer[6]={2,0,0,0,0,3};
static uint64_t clock_now(void *p){(void)p;if(mode==7)now++;return now;}
static int sleep_ms(void *p,unsigned n){(void)p;assert(n&&n<=10);now+=n;return 0;}
static void put16(uint8_t *p,unsigned n){p[0]=(uint8_t)(n>>8);p[1]=(uint8_t)n;}
static unsigned checksum(const uint8_t *p,unsigned n) {
    unsigned sum=0;for(unsigned i=0;i<n;i+=2)sum+=((unsigned)p[i]<<8)|(i+1<n?p[i+1]:0);
    sum=(sum&65535)+(sum>>16);sum=(sum&65535)+(sum>>16);return (~sum)&65535;
}
static int send_frame(void *p,const uint8_t *f,unsigned n,uint64_t end) {
    (void)p;assert(now<end&&end==original_end);sent++;
    if(f[13]==6) {
        assert(n==42);memcpy(arp_reply,f,42);memcpy(arp_reply,local,6);memcpy(arp_reply+6,peer,6);
        arp_reply[21]=2;memcpy(arp_reply+22,peer,6);memcpy(arp_reply+28,f+38,4);
        memcpy(arp_reply+32,local,6);memcpy(arp_reply+38,f+28,4);pending=1;
    } else {
        reist_udp_parse_result_t result;assert(!reist_udp_parse_frame(f,n,&result));
        assert(result.source_port==4000&&result.destination_port==5000&&result.payload_length==512&&result.checksum);
        memcpy(datagram,f,n);datagram_size=n;
        memcpy(datagram,local,6);memcpy(datagram+6,peer,6);
        memcpy(datagram+26,f+30,4);memcpy(datagram+30,f+26,4);
        put16(datagram+34,5000);put16(datagram+36,4000);
        /* IPv4 UDP explicitly permits a zero checksum; test that parser path too. */
        put16(datagram+40,0);put16(datagram+24,0);put16(datagram+24,checksum(datagram+14,20));
    }
    return 0;
}
static int receive_frame(void *p,uint8_t *f,unsigned cap,uint64_t end) {
    (void)p;assert(now<end&&end==original_end&&cap==1514);reads++;
    if(mode==1)return -11;
    if(pending){pending=0;memcpy(f,arp_reply,42);return 42;}
    if(datagram_size) {
        unsigned n=datagram_size;datagram_size=0;memcpy(f,datagram,n);
        if(mode==2)f[0]^=1;
        if(mode==3)f[40]=1;
        if(mode==4)f[35]^=1;
        if(mode==5){f[20]|=0x20;put16(f+24,0);put16(f+24,checksum(f+14,20));}
        if(mode==6)now=end;
        return (int)n;
    }
    return -11;
}
int main(void) {
    for(mode=0;mode<=7;mode++) {
        now=100;sent=pending=reads=datagram_size=0;
        reist_app_udp_state state;reist_net_protocol net;
        assert(!reist_app_udp_init(&state,1ULL<<32,(3ULL<<32)|5,now));
        reist_app_udp_grant grant={1,64,1ULL<<32,(4ULL<<32)|6,(3ULL<<32)|5,1,6100,17,REIST_APP_UDP_PEER,4000,5000,0};
        assert(!reist_app_udp_grant_set(&state,&grant,now));
        assert(!reist_net_protocol_init(&net,local,19));net.configured=1;net.ip=0xc0000202;net.mask=0xffffff00;
        reist_net_io io={0,clock_now,sleep_ms,send_frame,receive_frame};
        reist_app_udp_request q={.grant=grant,.sequence=1,.deadline=1100,.operation=REIST_APP_UDP_OPEN},r;
        assert(!reist_app_udp_exchange(&state,&net,&io,&q,&r)&&!r.result);
        q.handle=r.handle;q.sequence++;q.operation=REIST_APP_UDP_BIND;
        assert(!reist_app_udp_exchange(&state,&net,&io,&q,&r)&&!r.result);
        q.sequence++;q.operation=REIST_APP_UDP_SEND;q.length=512;memset(q.payload,0x5a,512);
        original_end=q.deadline;
        assert(!reist_app_udp_exchange(&state,&net,&io,&q,&r)&&r.result==(mode==1?-110:0));
        if(mode==1)assert(reads<=10);
        q.sequence++;q.operation=REIST_APP_UDP_RECEIVE;q.deadline=now+1000;memset(q.payload,0,512);
        original_end=q.deadline;
        assert(!reist_app_udp_exchange(&state,&net,&io,&q,&r));
        assert(r.result==((mode&&mode!=7)?-110:0));if(!mode||mode==7)assert(r.length==512&&r.payload[511]==0x5a);
        assert(reads<=1600&&now<=2100);
        unsigned before=sent;q.sequence++;q.grant.peer++;
        assert(reist_app_udp_exchange(&state,&net,&io,&q,&r)==-116&&sent==before);
    }
    return 0;
}
