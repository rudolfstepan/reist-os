#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_tcp.h>
#include <reist/x86_64/syscall.h>
static reist_app_tcp_state state;
static reist_app_tcp_request response;
static uint64_t stamp=100;
static unsigned calls,transmits,delayed;
static unsigned writes,output_length;
static char output[1024];
extern volatile uint64_t reist_tcp_app_selection[2];
int64_t tcp_host_call(unsigned number,uint64_t a,uint64_t b,uint64_t c) {
    calls++;
    if(number==REIST_X64_SYS_GETPID)return 4;
    if(number==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)stamp;
    if(number==REIST_X64_SYS_TERMINAL_INPUT)return 0;
    if(number==REIST_X64_SYS_SLEEP_MS){assert(a&&a<=100);stamp+=a;return 0;}
    if(number==REIST_X64_SYS_WRITE){
        assert(a==1&&b&&c&&c<=64);writes++;
        if(writes==1){assert(c==64);return -11;}
        unsigned count=writes==2?3:(unsigned)c;assert(count<=c&&output_length+count<=sizeof(output));
        memcpy(output+output_length,(void*)(uintptr_t)b,count);output_length+=count;return count;
    }
    if(number==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        assert(a==0x100&&c&&c<=100);transmits++;
        x86os_ipc_bulk_message_t *m=(void*)(uintptr_t)b;
        assert(m->version==2&&m->struct_size==sizeof(*m)&&m->length==608);
        reist_app_tcp_request q;memcpy(&q,m->payload,608);
        if(!q.operation) {
            assert(!q.sequence&&!q.grant.root&&!q.grant.epoch&&q.grant.local_port==49164);
            response=q;response.grant.root=1ULL<<32;response.grant.service=(3ULL<<32)|5;
            response.grant.epoch=1;response.grant.expires=6100;
            assert(!reist_app_tcp_grant_set(&state,&response.grant,stamp));
        } else {
            int r=reist_app_tcp_begin(&state,&q,&response,stamp);assert(r==0||r==1);
            if(r==1) {
                reist_app_tcp_socket *p=&state.sockets[q.handle-1];
                if(q.operation==REIST_APP_TCP_CONNECT)p->state=REIST_TCP_ESTABLISHED;
                if(q.operation==REIST_APP_TCP_SEND)p->send_unacknowledged=p->send_next;
                if(q.operation==REIST_APP_TCP_RECV){memset(p->receive,0xa5,512);p->receive_count=512;}
                if(q.operation==REIST_APP_TCP_CLOSE)p->state=REIST_TCP_TIME_WAIT;
                assert(!reist_app_tcp_finish(&state,&q,&response,0,stamp));
            }
        }
        return 0;
    }
    if(number==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT) {
        assert(a==0x200&&c&&c<=100);
        if(!delayed){delayed=1;stamp+=c;return -110;}
        x86os_ipc_bulk_message_t *m=(void*)(uintptr_t)b;
        assert(m->length==2048);m->length=608;memcpy(m->payload,&response,608);return 0;
    }
    assert(!"unexpected syscall authority");return -38;
}
int __real_main(int argc,char **argv) {
    assert(argc==4&&!argv[4]);
    uint32_t socket=0;assert(!x86os_tcp_socket_open(&socket)&&socket==1);
    x86os_tcp_connect_t connect={.version=1,.struct_size=sizeof(connect),.socket=socket,
        .destination_ip=REIST_APP_TCP_PEER,.destination_port=5000,.timeout_ms=2000};
    unsigned before=transmits;connect.destination_ip++;
    assert(x86os_tcp_connect(&connect)==-22&&transmits==before);connect.destination_ip--;
    connect.reserved=1;assert(x86os_tcp_connect(&connect)==-22&&transmits==before);connect.reserved=0;
    assert(!x86os_tcp_connect(&connect));
    uint8_t bytes[2048];memset(bytes,0x5a,sizeof(bytes));
    x86os_tcp_io_t io={.version=1,.struct_size=sizeof(io),.socket=socket,.length=512,.timeout_ms=2000};
    before=transmits;io.length=513;assert(x86os_tcp_send(&io,bytes)==-22&&transmits==before);io.length=512;
    assert(x86os_tcp_send(&io,bytes)==512);
    io.length=sizeof(bytes);assert(x86os_tcp_receive(&io,bytes)==512&&io.length==512&&bytes[511]==0xa5&&bytes[512]==0x5a);
    x86os_tcp_socket_control_t stats;assert(!x86os_tcp_socket_stats(&stats));
    assert(stats.version==1&&stats.struct_size==sizeof(stats)&&stats.active_sockets==1&&stats.established_sockets==1);
    before=transmits;
    assert(x86os_tcp_socket_ingress(0,0)==-13&&x86os_tcp_listen(0)==-13&&x86os_tcp_accept(0)==-13);
    assert(x86os_dns_resolve("example",1000,0)==-13&&transmits==before);
    assert(!x86os_tcp_socket_close(socket,1000));
    assert(!x86os_tcp_socket_open(&socket)&&socket==2);
    connect.socket=socket;assert(!x86os_tcp_connect(&connect));
    io.socket=socket;io.length=512;reist_tcp_app_selection[1]=8;
    assert(x86os_tcp_send(&io,bytes)==-9&&!state.sockets[1].handle);
    reist_tcp_app_selection[1]=0;
    for(unsigned n=0;n<512;n++)x86os_putchar('A');
    x86os_puts("\nsdk ok\n");return 0;
}
extern int __wrap_main(int,char **);
int main(void) {
    assert(!reist_app_tcp_init(&state,1ULL<<32,(3ULL<<32)|5,stamp));
    char *args[]={"nc","192.0.2.3","5000","hello","@at1:00000100","@at1:00000200",0};
    assert(!__wrap_main(6,args));assert(!state.active&&calls&&transmits==12&&delayed);
    assert(output_length==520&&writes<=12&&!memcmp(output+512,"\nsdk ok\n",8));
    for(unsigned n=0;n<512;n++)assert(output[n]=='A');
    return 0;
}
