#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_tcp.h>

int main(void) {
    reist_app_tcp_state state,before;
    reist_app_tcp_grant g={1,64,1ULL<<32,(4ULL<<32)|6,(3ULL<<32)|5,1,6100,6,
                           0xc0000203,49164,5000,0};
    assert(reist_app_tcp_port_base(g.application)==49164);
    assert(reist_app_tcp_port_base((4096ULL<<32)|6)==65532);
    assert(!reist_app_tcp_port_base((4097ULL<<32)|6));
    assert(!reist_app_tcp_port_base((4ULL<<32)|5));
    assert(!reist_app_tcp_init(&state,g.root,g.service,100));
    before=state;g.local_port++;
    assert(reist_app_tcp_grant_set(&state,&g,100)==-22&&!memcmp(&state,&before,sizeof(state)));
    g.local_port--;assert(!reist_app_tcp_grant_set(&state,&g,100));
    reist_app_tcp_request q={.grant=g,.sequence=1,.deadline=1100,.operation=REIST_APP_TCP_OPEN},r;
    before=state;
    for(unsigned n=0;n<64;n++) {
        ((unsigned char*)&q.grant)[n]^=1;
        assert(reist_app_tcp_begin(&state,&q,&r,100)==-116&&!memcmp(&state,&before,sizeof(state)));
        ((unsigned char*)&q.grant)[n]^=1;
    }
    assert(reist_app_tcp_begin(&state,&q,&q,100)==-22&&!memcmp(&state,&before,sizeof(state)));
    assert(reist_app_tcp_begin(&state,&q,&r,99)==-84&&!memcmp(&state,&before,sizeof(state)));
    q.sequence=2;assert(reist_app_tcp_begin(&state,&q,&r,100)==-116);q.sequence=1;
    q.deadline=2101;assert(reist_app_tcp_begin(&state,&q,&r,100)==-110);q.deadline=1100;
    q.result=1;assert(reist_app_tcp_begin(&state,&q,&r,100)==-22);q.result=0;
    assert(!memcmp(&state,&before,sizeof(state)));
    before=state;q.grant.peer++;
    assert(reist_app_tcp_begin(&state,&q,&r,100)==-116&&!memcmp(&state,&before,sizeof(state)));
    q.grant=g;q.payload[0]=1;
    assert(reist_app_tcp_begin(&state,&q,&r,100)==-22&&!memcmp(&state,&before,sizeof(state)));
    q.payload[0]=0;
    assert(!reist_app_tcp_begin(&state,&q,&r,100)&&!r.result&&r.handle==1);
    assert(state.sockets[0].local_port==49164);
    q.sequence++;q.operation=REIST_APP_TCP_CLOSE;q.handle=1;
    assert(!reist_app_tcp_begin(&state,&q,&r,100)&&!r.result&&!state.sockets[0].handle);
    q.sequence++;q.operation=REIST_APP_TCP_SEND;q.length=1;
    assert(!reist_app_tcp_begin(&state,&q,&r,100)&&r.result==-9);
    for(unsigned handle=2;handle<=4;handle++) {
        q.sequence++;q.operation=REIST_APP_TCP_OPEN;q.handle=0;q.length=0;
        assert(!reist_app_tcp_begin(&state,&q,&r,100)&&!r.result&&r.handle==handle);
        assert(state.sockets[handle-1].local_port==49163+handle);
    }
    q.sequence++;assert(!reist_app_tcp_begin(&state,&q,&r,100)&&r.result==-24);
    q.sequence++;q.operation=REIST_APP_TCP_CONNECT;q.handle=2;
    assert(reist_app_tcp_begin(&state,&q,&r,100)==1);
    before=state;q.sequence++;
    assert(reist_app_tcp_begin(&state,&q,&r,100)==-16&&!memcmp(&state,&before,sizeof(state)));
    q.sequence--;assert(!reist_app_tcp_finish(&state,&q,&r,-110,1100)&&r.result==-110);
    assert(state.sockets[1].state==REIST_TCP_CLOSED&&state.sockets[1].error==-110);
    reist_app_tcp_revoke(&state);assert(!state.active&&!state.pending.operation);
    before=state;assert(reist_app_tcp_grant_set(&state,&g,1200)==-116&&!memcmp(&state,&before,sizeof(state)));
    g.epoch++;assert(reist_app_tcp_grant_set(&state,&g,1200)==-116);
    g.application=(5ULL<<32)|6;g.local_port=49168;g.expires=7200;
    assert(!reist_app_tcp_grant_set(&state,&g,1200)&&!state.issued);
    q=(reist_app_tcp_request){.grant=g,.sequence=1,.deadline=2200,.operation=REIST_APP_TCP_RELEASE};
    assert(!reist_app_tcp_begin(&state,&q,&r,1200)&&!state.active);
    const char *args[]={"nc","192.0.2.3","5000","hello"};
    assert(!reist_app_tcp_operand(4,args,&g)&&g.protocol==6&&g.peer_port==5000&&!g.local_port);
    args[1]="192.0.2.4";assert(reist_app_tcp_operand(4,args,&g)==-22);
    return 0;
}
