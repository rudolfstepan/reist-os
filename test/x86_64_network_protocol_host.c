#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#include <reist/x86_64/network_session.h>

static uint64_t stamp;
static unsigned sends,reads,mode;
static uint8_t pending[1514];
static unsigned pending_bytes;
static uint8_t first_nonce[16];
static const uint8_t local[6]={0x52,0x54,0,0x12,0x34,0x56};
static const uint8_t remote[6]={0x52,0x54,0,0x12,0x34,0x57};
static uint64_t now(void *p){(void)p;return stamp;}
static int pause_ms(void *p,unsigned ms){(void)p;assert(ms>0&&ms<=10);stamp+=ms;return 0;}
static uint16_t checksum(const uint8_t *p,unsigned n) {
    uint32_t sum=0;for(unsigned i=0;i<n;i+=2)sum+=((uint16_t)p[i]<<8)|(i+1<n?p[i+1]:0);
    sum=(sum&65535)+(sum>>16);sum=(sum&65535)+(sum>>16);return (uint16_t)~sum;
}
static void put16(uint8_t *p,uint16_t v){p[0]=(uint8_t)(v>>8);p[1]=(uint8_t)v;}
static int send_frame(void *p,const uint8_t *f,unsigned n,uint64_t end) {
    (void)p;assert(n>=42&&n<=1514&&stamp<end);sends++;memcpy(pending,f,n);pending_bytes=n;
    memcpy(pending,local,6);memcpy(pending+6,remote,6);
    if(f[13]==6) {
        assert(f[20]==0&&f[21]==1);pending[21]=2;
        memcpy(pending+22,remote,6);memcpy(pending+28,f+38,4);
        memcpy(pending+32,local,6);memcpy(pending+38,f+28,4);
    } else {
        assert(f[23]==1&&f[34]==8);memcpy(pending+26,f+30,4);memcpy(pending+30,f+26,4);
        if(!first_nonce[7])memcpy(first_nonce,f+42,16);
        pending[34]=0;pending[36]=pending[37]=0;put16(pending+36,checksum(pending+34,n-34));
        pending[24]=pending[25]=0;put16(pending+24,checksum(pending+14,20));
    }
    return 0;
}
static int receive_frame(void *p,uint8_t *f,unsigned cap,uint64_t end) {
    (void)p;assert(cap==1514&&stamp<end);reads++;
    if(!pending_bytes||mode==1)return -11;
    memcpy(f,pending,pending_bytes);unsigned n=pending_bytes;pending_bytes=0;
    if(mode==2)f[0]^=2; /* foreign L2 destination */
    if(mode==3&&f[13]==0)f[36]^=1; /* checksum */
    if(mode==4&&f[13]==6)f[31]^=1; /* unsolicited ARP IP */
    if(mode==5&&f[13]==0) {
        f[42]^=1;f[36]=f[37]=0;put16(f+36,checksum(f+34,n-34)); /* old nonce */
    }
    if(mode==6&&f[13]==0) {
        memcpy(f+42,first_nonce,16);f[36]=f[37]=0;put16(f+36,checksum(f+34,n-34));
    }
    return (int)n;
}
int main(void) {
    reist_net_protocol s={0};reist_net_io io={0,now,pause_ms,send_frame,receive_frame};
    assert(reist_net_protocol_init(&s,local,17)==0);
    x86os_network_control_request_t q={0};q.version=2;q.struct_size=sizeof(q);
    q.operation=2;q.ip_address=0xc0000202;q.netmask=0xffffff00;q.gateway=0xc0000201;
    assert(reist_net_protocol_control(&s,&q,&io)==0);
    reist_net_protocol before=s;q.netmask=0xff00ff00;
    assert(reist_net_protocol_control(&s,&q,&io)==-22&&memcmp(&s,&before,sizeof(s))==0&&sends==0);
    q.ip_address=q.netmask=q.gateway=0;q.operation=3;q.target_ip=0xc0000203;q.identifier=0x1234;q.sequence=7;q.timeout_ms=100;
    for(mode=0;mode<=5;mode++) {
        stamp=1000+mode*2000;sends=reads=pending_bytes=0;uint64_t end=stamp+100;
        int r=reist_net_protocol_control(&s,&q,&io);
        if(r!=(mode?-110:0)){fprintf(stderr,"mode=%u result=%d sends=%u reads=%u now=%llu\n",mode,r,sends,reads,(unsigned long long)stamp);fflush(stderr);}
        assert(r==(mode?-110:0));assert(stamp<=end&&reads<=80&&sends<=2);
    }
    mode=0;stamp=20000;assert(reist_net_protocol_control(&s,&q,&io)==0); /* fresh after timeout */
    q.reserved=1;unsigned previous=sends;before=s;
    assert(reist_net_protocol_control(&s,&q,&io)==-22&&sends==previous&&memcmp(&s,&before,sizeof(s))==0);
    q.reserved=0;q.timeout_ms=2001;assert(reist_net_protocol_control(&s,&q,&io)==-22);
    /* A fresh parent may reuse public IDs and its private group epoch. Its
     * distinct hardware binding epoch must reject the previous echo nonce. */
    reist_net_protocol replacement={0};assert(!reist_net_protocol_init(&replacement,local,18));
    x86os_network_control_request_t configure={0};configure.version=2;configure.struct_size=sizeof(configure);
    configure.operation=2;configure.ip_address=0xc0000202;configure.netmask=0xffffff00;configure.gateway=0xc0000201;
    assert(!reist_net_protocol_control(&replacement,&configure,&io));
    q.timeout_ms=100;mode=6;stamp=30000;
    assert(reist_net_protocol_control(&replacement,&q,&io)==-110);
    mode=0;assert(!reist_net_protocol_control(&replacement,&q,&io));
    q.timeout_ms=100;stamp=UINT64_MAX-50;assert(reist_net_protocol_control(&s,&q,&io)==-75);
    puts("NETWORK_PROTOCOL_HOST_OK");return 0;
}
