#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_udp.h>
static reist_app_udp_state state, before;
static reist_app_udp_grant grant;
static reist_app_udp_request request, reply;
static uint64_t now=100;
static unsigned request_count;
static void prepare(unsigned op,unsigned handle,unsigned length) {
    request=(reist_app_udp_request){.grant=grant,.sequence=++request_count,
        .deadline=now+1000,.operation=op,.handle=handle,.length=length};
}
static void denied(int result) {
    before=state;
    assert(reist_app_udp_begin(&state,&request,&reply,now)==result);
    assert(!memcmp(&state,&before,sizeof(state)));
}
int main(void) {
    const char *args[]={"udp","recv","192.0.2.3","5000","4000","2000"};
    reist_app_udp_grant operand={0};
    assert(!reist_app_udp_operand(6,args,&operand)&&operand.peer==REIST_APP_UDP_PEER&&operand.local_port==4000);
    args[2]="192.0.2.4";assert(reist_app_udp_operand(6,args,&operand)==-22);args[2]="192.0.2.3";
    args[5]="2001";assert(reist_app_udp_operand(6,args,&operand)==-22);args[5]="2000";
    args[3]="65536";assert(reist_app_udp_operand(6,args,&operand)==-22);args[3]="5000";
    assert(reist_app_udp_operand(4,args,&operand)==-22);
    const uint64_t root=1ULL<<32,stack=(3ULL<<32)|5,app=(4ULL<<32)|6;
    assert(!reist_app_udp_init(&state,root,stack,now));
    grant=(reist_app_udp_grant){.version=1,.size=64,.root=root,.application=app,
        .service=stack,.epoch=1,.expires=now+6000,.protocol=17,
        .peer=REIST_APP_UDP_PEER,.local_port=4000,.peer_port=5000};
    assert(!reist_app_udp_grant_set(&state,&grant,now));
    prepare(REIST_APP_UDP_OPEN,0,0);
    request.grant.application+=1ULL<<32;denied(-116);request.grant=grant;
    request.grant.service+=1ULL<<32;denied(-116);request.grant=grant;
    request.grant.peer++;denied(-116);request.grant=grant;
    request.grant.epoch++;denied(-116);request.grant=grant;
    request.payload[511]=1;denied(-22);request.payload[511]=0;
    request.deadline=now;denied(-110);request.deadline=now+1000;
    request.sequence++;denied(-116);request.sequence--;
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result);
    unsigned first=reply.handle;
    assert(first);
    denied(-116); /* A transport replay cannot open another socket. */
    for(unsigned n=1;n<8;n++) {
        prepare(REIST_APP_UDP_OPEN,0,0);
        assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result);
    }
    prepare(REIST_APP_UDP_OPEN,0,0);
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&reply.result==-24);
    prepare(REIST_APP_UDP_BIND,first,0);
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result);
    uint8_t payload[512];memset(payload,0x5a,sizeof(payload));
    for(unsigned n=0;n<4;n++) {
        payload[0]=(uint8_t)n;
        assert(!reist_app_udp_enqueue(&state,&grant,payload,sizeof(payload),now));
    }
    before=state;
    assert(reist_app_udp_enqueue(&state,&grant,payload,sizeof(payload),now)==-105);
    assert(!memcmp(&state,&before,sizeof(state)));
    for(unsigned n=0;n<4;n++) {
        prepare(REIST_APP_UDP_RECEIVE,first,512);
        assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result);
        assert(reply.length==512&&reply.payload[0]==n&&reply.payload[511]==0x5a);
    }
    prepare(REIST_APP_UDP_RECEIVE,first,512);
    assert(reist_app_udp_begin(&state,&request,&reply,now)==1);
    assert(!reist_app_udp_finish(&state,&request,&reply,-110,now)&&reply.result==-110);
    prepare(REIST_APP_UDP_SEND,first,513);denied(-22);request_count--;
    prepare(REIST_APP_UDP_CLOSE,first,0);
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result);
    prepare(REIST_APP_UDP_SEND,first,1);
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&reply.result==-9);
    reist_app_udp_revoke(&state);
    before=state;reist_app_udp_revoke(&state);assert(!memcmp(&state,&before,sizeof(state)));
    assert(!state.active);
    assert(reist_app_udp_grant_set(&state,&grant,now)==-116);
    grant.epoch++;
    assert(!reist_app_udp_grant_set(&state,&grant,now));request_count=0;
    prepare(REIST_APP_UDP_OPEN,0,0);
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result&&reply.handle>first);
    for(unsigned n=1;n<64;n++) {
        prepare(REIST_APP_UDP_CLOSE,first,0);
        assert(!reist_app_udp_begin(&state,&request,&reply,now)&&reply.result==-9);
    }
    prepare(REIST_APP_UDP_OPEN,0,0);denied(-122);
    reist_app_udp_revoke(&state);
    grant.epoch++;grant.peer++;
    assert(reist_app_udp_grant_set(&state,&grant,now)==-22);
    grant.peer=REIST_APP_UDP_PEER;grant.expires=now;
    assert(reist_app_udp_grant_set(&state,&grant,now)==-110);
    grant.expires=now+6000;
    assert(!reist_app_udp_grant_set(&state,&grant,now));request_count=0;
    prepare(REIST_APP_UDP_RELEASE,0,0);
    assert(!reist_app_udp_begin(&state,&request,&reply,now)&&!reply.result&&!state.active);
    return 0;
}
