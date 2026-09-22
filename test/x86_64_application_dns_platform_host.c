#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_dns.h>
#include <reist/x86_64/syscall.h>
static reist_app_udp_state udp;
static reist_app_tcp_state tcp;
static reist_app_tcp_grant base;
static reist_app_tcp_request response;
static uint64_t sequences[2],stamp=100,public_sequence;
static unsigned sends,releases;
int64_t tcp_host_call(unsigned n,uint64_t a,uint64_t b,uint64_t c) {
    if(n==REIST_X64_SYS_GETPID)return 4;
    if(n==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)stamp;
    if(n==REIST_X64_SYS_TERMINAL_INPUT)return 0;
    if(n==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        assert(a==0x100&&c&&c<=100);sends++;
        x86os_ipc_bulk_message_t *m=(void *)(uintptr_t)b;
        assert(m->version==2&&m->struct_size==sizeof(*m)&&m->length==608);
        reist_app_tcp_request q,wire;memcpy(&q,m->payload,sizeof(q));
        if(!q.operation) {
            assert(!q.sequence&&q.grant.protocol==17&&q.grant.peer_port==53);
            response=q;base=q.grant;base.root=1ULL<<32;base.service=(3ULL<<32)|5;
            base.epoch=1;base.expires=6100;response.grant=base;
            assert(!reist_app_dns_grant_set(&udp,&tcp,&base,stamp));return 0;
        }
        assert(q.sequence==++public_sequence);
        assert(!reist_app_dns_translate(&base,&q,&wire,sequences));
        if(q.grant.protocol==17) {
            reist_app_udp_request uq,ur;memcpy(&uq,&wire,sizeof(uq));
            int r=reist_app_udp_begin(&udp,&uq,&ur,stamp);assert(r==0||r==1);
            if(r)assert(!reist_app_udp_finish(&udp,&uq,&ur,
                q.operation==REIST_APP_UDP_RECEIVE?-110:0,stamp));
            memcpy(&response,&ur,sizeof(response));
        } else {
            int r=reist_app_tcp_begin(&tcp,&wire,&response,stamp);assert(r==0||r==1);
            if(r) {
                reist_app_tcp_socket *s=&tcp.sockets[q.handle-1];
                if(q.operation==REIST_APP_TCP_CONNECT)s->state=REIST_TCP_ESTABLISHED;
                if(q.operation==REIST_APP_TCP_SEND)s->send_unacknowledged=s->send_next;
                if(q.operation==REIST_APP_TCP_RECV){s->receive[0]=0x42;s->receive_count=1;}
                if(q.operation==REIST_APP_TCP_CLOSE)s->state=REIST_TCP_TIME_WAIT;
                assert(!reist_app_tcp_finish(&tcp,&wire,&response,0,stamp));
            }
        }
        assert(response.sequence==wire.sequence);response.sequence=q.sequence;
        if(q.operation==REIST_APP_TCP_RELEASE&&!response.result) {
            reist_app_dns_revoke(&udp,&tcp);releases++;
        }
        return 0;
    }
    if(n==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT) {
        assert(a==0x200&&c&&c<=100);
        x86os_ipc_bulk_message_t *m=(void *)(uintptr_t)b;
        assert(m->length==2048);m->length=608;memcpy(m->payload,&response,608);return 0;
    }
    assert(!"unexpected syscall authority");return -38;
}
int __real_main(int argc,char **argv) {
    assert(argc==2&&!strcmp(argv[1],"test.local")&&!argv[2]);
    x86os_network_control_request_t nq={.version=X86OS_NETWORK_CONTROL_VERSION,
        .struct_size=sizeof(nq),.operation=X86OS_NETWORK_STATUS};
    x86os_network_control_result_t nr;
    assert(!x86os_network_control(&nq,&nr));
    assert(nr.version==X86OS_NETWORK_CONTROL_VERSION&&nr.struct_size==sizeof(nr));
    assert(nr.configured&&nr.dns_server==REIST_APP_UDP_PEER);
    unsigned before=sends;nq.operation++;
    assert(x86os_network_control(&nq,&nr)==-13&&sends==before);
    x86os_udp_socket_t us;assert(!x86os_udp_socket_open(&us));
    before=sends;assert(x86os_udp_socket_bind(us,1234)==-13&&sends==before);
    assert(!x86os_udp_socket_bind(us,0));
    unsigned char bytes[512]={1,2,3};
    x86os_udp_datagram_t d={.version=1,.struct_size=sizeof(d),.socket=us,
        .ip=REIST_APP_UDP_PEER,.destination_port=53,.length=3,.timeout_ms=1000};
    before=sends;d.ip++;assert(x86os_udp_sendto(&d,bytes)==-22&&sends==before);d.ip--;
    assert(x86os_udp_sendto(&d,bytes)==3);
    d.length=512;assert(x86os_udp_recvfrom(&d,bytes)==-110&&d.length==512);
    x86os_tcp_socket_t ts;assert(!x86os_tcp_socket_open(&ts));
    x86os_udp_socket_t second;assert(!x86os_udp_socket_open(&second));
    x86os_tcp_connect_t connect={.version=1,.struct_size=sizeof(connect),.socket=ts,
        .destination_ip=REIST_APP_TCP_PEER,.destination_port=53,.timeout_ms=1000};
    assert(!x86os_tcp_connect(&connect));
    /* Closing UDP must not change which transport subsequent TCP APIs use. */
    assert(!x86os_udp_socket_close(us));
    x86os_tcp_io_t io={.version=1,.struct_size=sizeof(io),.socket=ts,.length=3,.timeout_ms=1000};
    assert(x86os_tcp_send(&io,bytes)==3);io.length=512;
    assert(!x86os_udp_socket_bind(second,0));
    assert(x86os_tcp_receive(&io,bytes)==1&&bytes[0]==0x42&&io.length==1);
    assert(!x86os_udp_socket_close(second));
    x86os_tcp_socket_control_t stats;assert(!x86os_tcp_socket_stats(&stats));
    assert(stats.active_sockets==1&&stats.established_sockets==1);
    assert(!x86os_udp_socket_open(&second));
    assert(!x86os_tcp_socket_close(ts,1000));
    assert(!x86os_udp_socket_close(second));return 0;
}
extern int __wrap_main(int,char **);
int main(void) {
    assert(!reist_app_udp_init(&udp,1ULL<<32,(3ULL<<32)|5,stamp));
    assert(!reist_app_tcp_init(&tcp,1ULL<<32,(3ULL<<32)|5,stamp));
    char *args[]={"nslookup","test.local","@at1:00000100","@at1:00000200",0};
    assert(!__wrap_main(4,args));assert(releases==1&&!udp.active&&!tcp.active);
    assert(sequences[0]==11&&sequences[1]==6&&public_sequence==17&&sends==18);
    return 0;
}
