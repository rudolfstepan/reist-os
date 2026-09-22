/* Fixed paired transport authority; DNS packet parsing stays in the app. */
#include <reist/x86_64/application_dns.h>
static int equal(const void *a,const void *b,unsigned n) {
    const uint8_t *p=a,*q=b;unsigned d=0;for(unsigned i=0;i<n;i++)d|=p[i]^q[i];return !d;
}
static int text_equal(const char *a,const char *b) {
    if(!a||!b)return 0;
    for(unsigned n=0;n<254;n++){if(a[n]!=b[n])return 0;if(!a[n])return 1;}return 0;
}
int reist_app_dns_operand(int argc,const char *const *argv,reist_app_tcp_grant *out) {
    if(!out||!argv||(argc!=2&&argc!=3)||!argv[1])return -22;
    if(argc==3&&!text_equal(argv[2],"192.0.2.3"))return -13;
    unsigned n=0;while(n<254&&argv[1][n])n++;
    if(!n||n>253)return -22;
    /* Root bounds the operand only; the app validates DNS label syntax. */
    reist_app_tcp_grant g={.version=1,.size=64,.protocol=17,.peer=REIST_APP_TCP_PEER,.peer_port=53};
    *out=g;return 0;
}
void reist_app_dns_revoke(reist_app_udp_state *udp,reist_app_tcp_state *tcp) {
    reist_app_udp_revoke(udp);reist_app_tcp_revoke(tcp);
}
/* Keep the accepted UDP storage ABI; DNS admits at most four live objects.
 * Denial precedes allocation and leaves the service sequence unconsumed. */
int reist_app_dns_udp_admit(const reist_app_udp_state *udp,const reist_app_udp_request *q) {
    if(!udp||!q)return -22;
    if(q->operation!=REIST_APP_UDP_OPEN)return 0;
    unsigned count=0;
    for(unsigned n=0;n<REIST_APP_UDP_SOCKETS;n++)count+=udp->sockets[n].handle!=0;
    return count>=4?-24:0;
}
int reist_app_dns_grant_set(reist_app_udp_state *udp,reist_app_tcp_state *tcp,const reist_app_tcp_grant *g,uint64_t now) {
    if(!udp||!tcp||!g||udp->active||tcp->active)return -16;
    if(g->protocol!=17||g->peer_port!=53||g->local_port!=reist_app_tcp_port_base(g->application)||!g->local_port)return -22;
    reist_app_udp_grant u;reist_net_copy(&u,g,sizeof(u));
    reist_app_tcp_grant t=*g;t.protocol=6;
    int r=reist_app_udp_grant_set(udp,&u,now);
    if(!r)r=reist_app_tcp_grant_set(tcp,&t,now);
    if(r)reist_app_dns_revoke(udp,tcp);
    return r;
}
int reist_app_dns_translate(const reist_app_tcp_grant *g,const reist_app_tcp_request *q,reist_app_tcp_request *out,uint64_t sequence[2]) {
    if(!g||!q||!out||!sequence||q==out)return -22;
    if(q->grant.protocol!=6&&q->grant.protocol!=17)return -13;
    reist_app_tcp_grant selected=q->grant;selected.protocol=17;
    if(!equal(g,&selected,64))return -116;
    unsigned index=q->grant.protocol==6;
    if(sequence[index]>=64)return -122;
    *out=*q;out->sequence=++sequence[index];return 0;
}
