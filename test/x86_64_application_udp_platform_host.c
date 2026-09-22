#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_udp.h>
#include <reist/x86_64/syscall.h>
static reist_app_udp_state state;
static reist_app_udp_request response;
static uint64_t stamp=100;
static unsigned calls,transmits;
extern volatile uint64_t reist_udp_app_selection[2];
int64_t udp_host_call(unsigned number,uint64_t a,uint64_t b,uint64_t c) {
    calls++;
    if(number==REIST_X64_SYS_GETPID)return 4;
    if(number==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)stamp;
    if(number==REIST_X64_SYS_TERMINAL_INPUT)return 0;
    if(number==REIST_X64_SYS_SLEEP_MS){assert(a&&a<=100);stamp+=a;return 0;}
    if(number==REIST_X64_SYS_WRITE){assert(a==1&&b&&c==1);return 1;}
    if(number==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        assert(a==0x100&&c&&c<=100);transmits++;
        x86os_ipc_bulk_message_t *m=(void*)(uintptr_t)b;
        assert(m->version==2&&m->struct_size==sizeof(*m)&&m->length==608);
        reist_app_udp_request q;memcpy(&q,m->payload,608);
        if(!q.operation) {
            assert(!q.sequence&&!q.grant.root&&!q.grant.epoch);
            response=q;response.grant.root=1ULL<<32;response.grant.service=(3ULL<<32)|5;
            response.grant.epoch=1;response.grant.expires=6100;
            assert(!reist_app_udp_grant_set(&state,&response.grant,stamp));
        } else {
            int r=reist_app_udp_begin(&state,&q,&response,stamp);assert(r==0||r==1);
            if(r==1) {
                if(q.operation==REIST_APP_UDP_RECEIVE){uint8_t bytes[512];memset(bytes,0xa5,512);
                    assert(!reist_app_udp_enqueue(&state,&q.grant,bytes,512,stamp));}
                assert(!reist_app_udp_finish(&state,&q,&response,0,stamp));
            }
        }
        return 0;
    }
    if(number==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT) {
        assert(a==0x200&&!c);x86os_ipc_bulk_message_t *m=(void*)(uintptr_t)b;
        assert(m->length==2048);m->length=608;memcpy(m->payload,&response,608);return 0;
    }
    assert(!"unexpected syscall authority");return -38;
}
int __real_main(int argc,char **argv) {
    assert(argc==6&&!argv[6]);
    uint32_t socket=0;assert(!x86os_udp_socket_open(&socket)&&socket);
    unsigned before=transmits;
    assert(x86os_udp_socket_bind(socket,4001)==-13&&transmits==before);
    assert(!x86os_udp_socket_bind(socket,4000));
    uint8_t bytes[512];memset(bytes,0x5a,512);
    x86os_udp_datagram_t d={.version=1,.struct_size=sizeof(d),.socket=socket,
        .ip=REIST_APP_UDP_PEER,.destination_port=5000,.length=512,.timeout_ms=2000};
    before=transmits;d.ip++;
    assert(x86os_udp_sendto(&d,bytes)==-22&&transmits==before);d.ip--;
    assert(!x86os_udp_sendto(&d,bytes));
    d.ip=0;d.destination_port=0;
    assert(!x86os_udp_recvfrom(&d,bytes)&&d.length==512&&d.ip==REIST_APP_UDP_PEER&&
        d.source_port==5000&&d.destination_port==4000&&bytes[511]==0xa5);
    assert(x86os_udp_socket_ingress(&d,bytes)==-13);
    assert(!x86os_udp_socket_close(socket));
    assert(!x86os_udp_socket_open(&socket)&&!x86os_udp_socket_bind(socket,4000));
    d.socket=socket;d.ip=REIST_APP_UDP_PEER;d.source_port=0;d.destination_port=5000;
    reist_udp_app_selection[1]=8;
    assert(x86os_udp_sendto(&d,bytes)==-9&&!state.sockets[0].handle);
    reist_udp_app_selection[1]=0;
    x86os_puts("sdk ok\n");return 0;
}
extern int __wrap_main(int,char **);
int main(void) {
    assert(!reist_app_udp_init(&state,1ULL<<32,(3ULL<<32)|5,stamp));
    char *args[]={"udp","send","192.0.2.3","5000","4000","hello","@au1:00000100","@au1:00000200",0};
    assert(!__wrap_main(8,args));assert(!state.active&&calls&&transmits==11);
    return 0;
}
