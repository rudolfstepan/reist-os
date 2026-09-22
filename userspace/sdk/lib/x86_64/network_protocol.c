/* RFC826/RFC791/RFC792 control plane. No device access or kernel dependency. */
#include <reist/x86_64/network_session.h>
#include <reist_ipv4_parser.h>
#include <reist_icmp_parser.h>

static void copy(uint8_t *to,const uint8_t *from,unsigned n){for(unsigned i=0;i<n;i++)to[i]=from[i];}
static int equal(const uint8_t *a,const uint8_t *b,unsigned n){unsigned d=0;for(unsigned i=0;i<n;i++)d|=a[i]^b[i];return !d;}
static void be16(uint8_t *p,uint16_t v){p[0]=(uint8_t)(v>>8);p[1]=(uint8_t)v;}
static void be32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(24-8*i));}
static void be64(uint8_t *p,uint64_t v){for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(v>>(56-8*i));}
static uint32_t read32(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static unsigned read16(const uint8_t *p){return ((unsigned)p[0]<<8)|p[1];}
static uint16_t checksum(const uint8_t *p,unsigned n) {
    uint32_t sum=0;for(unsigned i=0;i<n;i+=2)sum+=((uint16_t)p[i]<<8)|(i+1<n?p[i+1]:0);
    sum=(sum&65535)+(sum>>16);sum=(sum&65535)+(sum>>16);return (uint16_t)~sum;
}
static int unicast(uint32_t ip){return ip && (ip>>24)!=127 && (ip>>24)!=0 && (ip>>24)<224;}
static int valid_mac(const uint8_t *mac) {
    unsigned bits=0;for(unsigned i=0;i<6;i++)bits|=mac[i];return bits && !(mac[0]&1);
}
int reist_net_protocol_init(reist_net_protocol *s,const uint8_t mac[6],uint64_t epoch) {
    if(!s||!mac||!epoch||!valid_mac(mac))return -22;
    *s=(reist_net_protocol){.epoch=epoch};copy(s->mac,mac,6);return 0;
}
static int check_time(reist_net_protocol *s,const reist_net_io *io,uint64_t end) {
    uint64_t now=io->now(io->context);
    if(now<s->last_ms)return -84;
    s->last_ms=now;return now>=end?-110:0;
}
static int request_valid(const x86os_network_control_request_t *q) {
    if(!q||q->version!=X86OS_NETWORK_CONTROL_VERSION||q->struct_size!=sizeof(*q)||q->reserved||
       q->operation<1||q->operation>4)return 0;
    if(q->operation==1)return !(q->ip_address|q->netmask|q->gateway|q->target_ip|q->identifier|q->sequence|q->timeout_ms);
    if(q->operation==2) {
        uint32_t host=~q->netmask;
        if(!unicast(q->ip_address)||host<3||host>=0x80000000U||(host&(host+1))||
           !(q->ip_address&host)||(q->ip_address&host)==host||
           q->target_ip||q->identifier||q->sequence||q->timeout_ms)return 0;
        return !q->gateway||(unicast(q->gateway)&&q->gateway!=q->ip_address&&
            (q->gateway&q->netmask)==(q->ip_address&q->netmask)&&
            (q->gateway&host)&&(q->gateway&host)!=host);
    }
    return !q->ip_address&&!q->netmask&&!q->gateway&&unicast(q->target_ip)&&
        q->timeout_ms&&q->timeout_ms<=REIST_NET_OPERATION_MS&&q->identifier<=65535&&q->sequence<=65535&&
        (q->operation==3||(!q->identifier&&!q->sequence));
}
int reist_net_protocol_control(reist_net_protocol *s,const x86os_network_control_request_t *q,const reist_net_io *io) {
    if(!s||!s->epoch||!valid_mac(s->mac)||s->reserved[0]||s->reserved[1]||!request_valid(q))return -22;
    if(q->operation==1)return 0;
    if(q->operation==2){s->ip=q->ip_address;s->mask=q->netmask;s->gateway=q->gateway;s->configured=1;return 0;}
    if(!s->configured)return -99;
    if(!io||!io->now||!io->sleep||!io->send||!io->receive)return -22;
    uint32_t host=~s->mask;
    if(q->target_ip==s->ip || ((q->target_ip&s->mask)==(s->ip&s->mask)&&
        (!(q->target_ip&host)||(q->target_ip&host)==host)))return -22;
    uint32_t next=(q->target_ip&s->mask)==(s->ip&s->mask)?q->target_ip:s->gateway;
    if(!next)return -101;
    if(q->operation==4&&next!=q->target_ip)return -101;
    uint64_t now=io->now(io->context);
    if(now<s->last_ms)return -84;
    if(now>UINT64_MAX-q->timeout_ms||s->sequence==UINT64_MAX)return -75;
    s->last_ms=now;uint64_t end=now+q->timeout_ms;uint64_t sequence=++s->sequence;
    uint8_t tx[60]={0},rx[REIST_NET_FRAME],peer[6]={0},nonce[16];
    be64(nonce,s->epoch);be64(nonce+8,sequence);
    for(unsigned i=0;i<6;i++)tx[i]=255;
    copy(tx+6,s->mac,6);be16(tx+12,0x0806);be16(tx+14,1);be16(tx+16,0x0800);
    tx[18]=6;tx[19]=4;be16(tx+20,1);copy(tx+22,s->mac,6);be32(tx+28,s->ip);be32(tx+38,next);
    int r=io->send(io->context,tx,42,end);if(r)return r;
    unsigned phase=0;
    for(unsigned turn=0;turn<200;turn++) {
        if((r=check_time(s,io,end)))return r;
        for(unsigned batch=0;batch<8;batch++) {
            if((r=check_time(s,io,end)))return r;
            int n=io->receive(io->context,rx,sizeof(rx),end);
            if(n==-11)break;if(n<0)return n;if(n>(int)sizeof(rx))return -71;
            if((r=check_time(s,io,end)))return r;
            if(n<14||!equal(rx,s->mac,6)||!valid_mac(rx+6))continue;
            if(!phase) {
                if(n<42||read16(rx+12)!=0x0806||read16(rx+14)!=1||read16(rx+16)!=0x0800||
                   rx[18]!=6||rx[19]!=4||read16(rx+20)!=2||!equal(rx+6,rx+22,6)||
                   read32(rx+28)!=next||!equal(rx+32,s->mac,6)||read32(rx+38)!=s->ip)continue;
                copy(peer,rx+6,6);if(q->operation==4)return 0;
                for(unsigned i=0;i<sizeof(tx);i++)tx[i]=0;
                copy(tx,peer,6);copy(tx+6,s->mac,6);be16(tx+12,0x0800);
                tx[14]=0x45;be16(tx+16,44);be16(tx+18,(uint16_t)sequence);tx[20]=0x40;
                tx[22]=64;tx[23]=1;be32(tx+26,s->ip);be32(tx+30,q->target_ip);
                be16(tx+24,checksum(tx+14,20));tx[34]=8;
                be16(tx+38,(uint16_t)q->identifier);be16(tx+40,(uint16_t)q->sequence);
                copy(tx+42,nonce,16);be16(tx+36,checksum(tx+34,24));
                if((r=check_time(s,io,end)))return r;
                r=io->send(io->context,tx,58,end);if(r)return r;phase=1;
            } else {
                reist_icmp_parse_result_t result;
                if(n<58||!equal(rx+6,peer,6)||(rx[20]&0x80)||reist_icmp_parse_frame(rx,(uint32_t)n,&result)||
                   result.source_ip!=q->target_ip||result.destination_ip!=s->ip||result.type||result.code||
                   result.identifier!=q->identifier||result.sequence!=q->sequence||result.payload_length!=16||
                   !equal(rx+result.payload_offset,nonce,16))continue;
                return 0;
            }
        }
        if((r=check_time(s,io,end)))return r;
        unsigned delay=(unsigned)(end-s->last_ms);if(delay>10)delay=10;
        if((r=io->sleep(io->context,delay)))return r;
    }
    return -110;
}
