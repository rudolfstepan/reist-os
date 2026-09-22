/* Root-only delegation and supervision. The separate stack validates every
 * object operation; the application never obtains its frame endpoint. */
#include <reist/x86_64/application_tcp.h>
static reist_app_tcp_grant tcp_grant;
static uint64_t tcp_epoch,tcp_sequence;
static uint32_t tcp_request,tcp_reply;
static unsigned tcp_transport_failed;
#ifdef REIST_NATIVE_APP_DNS
#include <reist/x86_64/application_dns.h>
static unsigned tcp_dns;
static uint64_t tcp_dns_sequence[2];
#endif
volatile uint64_t reist_tcp_root_selection[2] __attribute__((section(".data.memory_witness")))={0x31544f4f52544352ULL,0};
static int tcp_equal(const void *a,const void *b,unsigned n) {
    const uint8_t *p=a,*q=b;unsigned d=0;for(unsigned i=0;i<n;i++)d|=p[i]^q[i];return !d;
}
static void tcp_close_channels(void) {
    if(tcp_request){if(SESSION_S1(IPC_CLOSE,tcp_request))session_stop(-5);tcp_request=0;}
    if(tcp_reply){if(SESSION_S1(IPC_CLOSE,tcp_reply))session_stop(-5);tcp_reply=0;}
}
static int tcp_stack(unsigned operation,const void *p,unsigned length,uint64_t end) {
#ifdef REIST_NATIVE_APP_DNS
    unsigned wire_operation=operation;
    if(tcp_dns) {
        if(operation==REIST_NET_TCP_GRANT)wire_operation=REIST_NET_DNS_GRANT;
        if(operation==REIST_NET_TCP_REVOKE)wire_operation=REIST_NET_DNS_REVOKE;
        if(operation==REIST_NET_TCP_REQUEST&&((const reist_app_tcp_request *)p)->grant.protocol==17)wire_operation=REIST_NET_APP_REQUEST;
    }
    int r=network_send(1,wire_operation,p,length,end);if(r){tcp_transport_failed=1;return r;}
#else
    int r=network_send(1,operation,p,length,end);if(r){tcp_transport_failed=1;return r;}
#endif
    /* Drain the already admitted operation's bounded result grace even when
     * packet time expires; never confuse that reply with a later revoke ACK. */
    end+=(operation==REIST_NET_TCP_REQUEST?100:0);
    uint64_t health_end=session_now()+1000;
    for(unsigned turn=0;turn<3000;turn++) {
        uint64_t now=session_now(),limit=end;
        if(network_active&&health_end<limit)limit=health_end;
        if(now>=limit){r=-110;break;}
        unsigned wait=(unsigned)(limit-now);if(wait>100)wait=100;
        r=reist_net_receive(&network_channels[1],&network_message,wait);
        if(r==-11||r==-110)continue;
        if(r)break;
        if(network_message.type==REIST_NET_HEALTH&&!network_message.length&&!network_message.result){health_end=session_now()+1000;r=-110;continue;}
        r=network_message.type==REIST_NET_RESULT?network_message.result:-71;break;
    }
    if(r&&(network_channels[1].failed||network_message.type!=REIST_NET_RESULT))tcp_transport_failed=1;
    if(!r)network_health=session_now();return r;
}
static int session_tcp_revoke(void) {
    /* Close app capability publication before service revocation or fencing. */
    tcp_close_channels();
    int r=tcp_transport_failed?-5:0;
    if(!r&&tcp_grant.epoch&&network_active) {
        r=tcp_stack(REIST_NET_TCP_REVOKE,0,0,session_now()+1000);
        if(!r&&network_message.length)r=-71;
    }
    session_zero(&tcp_grant,sizeof(tcp_grant));
    if(r) {
        /* If service acknowledgement is uncertain, NIC fencing is mandatory
         * before app cancellation; no grant may survive a future group. */
        session_network_retire();network_failed=1;
    }
    return r;
}
static int64_t session_tcp_import(int argc,const char *const *argv,reist_task_startup_v1_t *startup,
                                 reist_task_profile_v1_t *profile) {
#ifdef REIST_NATIVE_APP_DNS
    tcp_dns=session_dns_selected;tcp_dns_sequence[0]=tcp_dns_sequence[1]=0;
    reist_app_tcp_grant selected;int r=tcp_dns?reist_app_dns_operand(argc,argv,&selected):reist_app_tcp_operand(argc,argv,&selected);if(r)return r;
#else
    reist_app_tcp_grant selected;int r=reist_app_tcp_operand(argc,argv,&selected);if(r)return r;
#endif
    if(reist_tcp_root_selection[0]!=0x31544f4f52544352ULL||reist_tcp_root_selection[1]>8)return -22;
    if(tcp_request||tcp_reply||session_tcp_active||network_busy)return -16;
    if(tcp_epoch==UINT64_MAX)return -75;
    void *image=(void*)(uintptr_t)SESSION_S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    if((intptr_t)image<=0)return -12;
    session_bytes(image,session_prepared,REIST_X64_PREPARED_V2_BYTES);
    network_busy=1;tcp_transport_failed=0;
#ifdef REIST_NATIVE_APP_DNS
    if(tcp_dns)session_network_retire();
#endif
    unsigned fault=(unsigned)reist_tcp_root_selection[1];
    if(fault>=1&&fault<=7) {
        session_network_retire();network_fault=fault==7?1:fault;
        if(fault!=7)reist_tcp_root_selection[1]=0;
    }
    r=network_launch();
    session_bytes(session_prepared,image,REIST_X64_PREPARED_V2_BYTES);
    session_zero(image,REIST_X64_PREPARED_V2_BYTES);if(SESSION_S1(FREE,image))session_stop(-5);
    if(r){network_failure();network_busy=0;return r;}
    if(!network_config.version||network_config.ip_address!=0xc0000202||network_config.netmask!=0xffffff00){network_busy=0;return -99;}
    r=(int)SESSION_S1(IPC_CREATE,&tcp_request);if(r)goto failed;
    r=(int)SESSION_S1(IPC_CREATE,&tcp_reply);if(r)goto failed;
    if(!tcp_request||!tcp_reply||tcp_request==tcp_reply)session_stop(-5);
    char request[14]="@at1:",reply[14]="@at1:";
    session_hex(request+5,tcp_request);session_hex(reply+5,tcp_reply);
    const char *args[8];for(int n=0;n<argc;n++)args[n]=argv[n];args[argc]=request;args[argc+1]=reply;
    r=reist_x64_startup_init(startup,(unsigned)argc+2,args);if(r)goto failed;
    /* Minimum ordinary program and two directional IPC rights only. */
    /* Existing terminal admission requires its READ/WRITE pair together. */
    profile->masks[0]=(1ULL<<9)|(1ULL<<15)|(1ULL<<20)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(1ULL<<53)|(1ULL<<54);
    profile->masks[1]=1ULL<<63;profile->masks[2]=0;
    uint64_t issued=session_now();
    int64_t child=reist_x64_task_import_wide(session_prepared,profile,32,startup);
    if(child<0){r=(int)child;goto failed;}
    if((uint32_t)child!=6||(uint64_t)child>>32>0x7fffffff)session_stop(-5);
    selected.root=session_policy.owner<<32;selected.service=network_owners[1];selected.application=(uint64_t)child;
    selected.local_port=reist_app_tcp_port_base((uint64_t)child);
    selected.epoch=++tcp_epoch;selected.expires=issued+6000;tcp_grant=selected;tcp_sequence=0;
    r=selected.local_port?tcp_stack(REIST_NET_TCP_GRANT,&tcp_grant,sizeof(tcp_grant),session_now()+1000):-75;
    if(!r&&network_message.length)r=-71;
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,tcp_request,(uint64_t)child>>32,1);
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,tcp_reply,(uint64_t)child>>32,2);
    if(!r&&session_now()<tcp_grant.expires){session_tcp_active=1;return child;}
    if(!r)r=-110;
    session_tcp_revoke();
    if(service_task(0,3,(uint64_t)child,0))session_stop(-5);
    int64_t retired=service_task(0,2,(uint64_t)child,1000);
    if(retired<0||(uint64_t)retired>>32>3)session_stop(-5);
failed:
    tcp_close_channels();network_busy=0;return r;
}
static int64_t session_tcp_wait(int *timed_out) {
    uint64_t end=tcp_grant.expires;unsigned hello=0,released=0;int fault=0;
    /* Each poll is bounded; total lifetime and64 requests are independent caps. */
    for(unsigned turn=0;tcp_request&&turn<6000;turn++) {
        uint64_t now=session_now();if(now>=end){fault=-110;break;}
        x86os_ipc_bulk_message_t message;session_zero(&message,sizeof(message));
        message.version=2;message.struct_size=sizeof(message);message.length=2048;
        unsigned wait=(unsigned)(end-now);if(wait>100)wait=100;
        int r=(int)SESSION_S3(IPC_RECEIVE_TIMEOUT,tcp_request,&message,wait);
        if(r==-11||r==-110){
            now=session_now();
            if(now-network_health>=500&&end-now>1000) {
                r=tcp_stack(REIST_NET_HEALTH,0,0,now+1000);
                if(r||network_message.length){fault=r?r:-71;break;}
            }
            continue;
        }
        if(r){fault=r;break;}
        if(message.version!=2||message.struct_size!=sizeof(message)||message.length!=608){fault=-71;break;}
        for(unsigned n=608;n<2048;n++)if(message.payload[n]){fault=-71;break;}
        if(fault)break;
        reist_app_tcp_request q,response;session_bytes(&q,message.payload,608);response=q;
        now=session_now();
        if(q.result||q.deadline<=now||q.deadline>end||q.deadline-now>2000){fault=-110;break;}
        if(!hello) {
            reist_app_tcp_request expected={0};expected.grant.version=1;expected.grant.size=64;
            expected.grant.application=session_child;expected.grant.protocol=6;expected.grant.peer=tcp_grant.peer;
#ifdef REIST_NATIVE_APP_DNS
            if(tcp_dns)expected.grant.protocol=17;
#endif
            expected.grant.local_port=tcp_grant.local_port;expected.grant.peer_port=tcp_grant.peer_port;expected.deadline=q.deadline;
            if(!tcp_equal(&q,&expected,608)){fault=-116;break;}
            response.grant=tcp_grant;hello=1;
        } else {
#ifdef REIST_NATIVE_APP_DNS
            reist_app_tcp_grant checked=q.grant;if(tcp_dns)checked.protocol=17;
            if(!tcp_equal(&checked,&tcp_grant,64)||tcp_sequence>=64||q.sequence!=tcp_sequence+1){fault=-116;break;}
#else
            if(!tcp_equal(&q.grant,&tcp_grant,64)||tcp_sequence>=64||q.sequence!=tcp_sequence+1){fault=-116;break;}
#endif
            if(reist_tcp_root_selection[1]==8&&q.operation==REIST_APP_TCP_SEND)__builtin_trap();
#ifdef REIST_NATIVE_APP_DNS
            uint64_t service_sequence=q.sequence;
            if(tcp_dns) {
                r=reist_app_dns_translate(&tcp_grant,&q,&response,tcp_dns_sequence);
                if(r){fault=r;break;}service_sequence=response.sequence;
                r=tcp_stack(REIST_NET_TCP_REQUEST,&response,608,q.deadline);
            } else
#endif
            r=tcp_stack(REIST_NET_TCP_REQUEST,&q,608,q.deadline);
            if(r){fault=r;break;}
            if(network_message.length!=608){tcp_transport_failed=1;fault=-71;break;}
            session_bytes(&response,network_message.payload,608);
#ifdef REIST_NATIVE_APP_DNS
            if(tcp_dns) {
                if(!tcp_equal(&response.grant,&q.grant,64)||response.sequence!=service_sequence){tcp_transport_failed=1;fault=-71;break;}
                response.grant.protocol=17;response.sequence=q.sequence;
            }
#endif
            if(!tcp_equal(&response.grant,&tcp_grant,64)||response.operation!=q.operation||
               response.sequence!=q.sequence||response.deadline!=q.deadline||response.result>0||response.result< -4095||
               response.length>512||(q.operation!=REIST_APP_TCP_OPEN&&response.handle!=q.handle)){tcp_transport_failed=1;fault=-71;break;}
            tcp_sequence=q.sequence;
#ifdef REIST_NATIVE_APP_DNS
            if(tcp_dns)response.grant=q.grant;
#endif
            if(q.operation==REIST_APP_TCP_RELEASE&&!response.result)released=1;
        }
        now=session_now();if(now>=q.deadline){fault=-110;break;}
        session_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=608;
        session_bytes(message.payload,&response,608);wait=(unsigned)(q.deadline-now);if(wait>100)wait=100;
        r=(int)SESSION_S3(IPC_SEND_TIMEOUT,tcp_reply,&message,wait);if(r){fault=r;break;}
        if(released)break;
        if(turn==5999)fault=-110;
    }
    *timed_out=fault==-110||session_now()>=end;
    /* Successful RELEASE already invalidated the stack grant. Keep the ACK
     * endpoint alive until the child consumes it and exits; closing it here
     * would purge that queued reply before the child can resume. */
    if(fault||!released)session_tcp_revoke();
    if(fault||!released)if(service_task(0,3,session_child,0))session_stop(-5);
    int64_t status=service_task(0,2,session_child,1000);
    if(status==-110) {
        *timed_out=1;if(service_task(0,3,session_child,0))session_stop(-5);
        status=service_task(0,2,session_child,1000);
    }
    if(released){tcp_close_channels();session_zero(&tcp_grant,sizeof(tcp_grant));}
    session_tcp_active=0;network_busy=0;return status;
}
