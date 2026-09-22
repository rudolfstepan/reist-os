/* Root-only delegation and supervision. The separate stack validates every
 * object operation; the application never obtains its frame endpoint. */
#include <reist/x86_64/application_udp.h>
static reist_app_udp_grant udp_grant;
static uint64_t udp_epoch,udp_sequence;
static uint32_t udp_request,udp_reply;
static unsigned udp_transport_failed;
volatile uint64_t reist_udp_root_selection[2] __attribute__((section(".data.memory_witness")))={0x31544f4f52445552ULL,0};
static int udp_equal(const void *a,const void *b,unsigned n) {
    const uint8_t *p=a,*q=b;unsigned d=0;for(unsigned i=0;i<n;i++)d|=p[i]^q[i];return !d;
}
static void udp_close_channels(void) {
    if(udp_request){if(SESSION_S1(IPC_CLOSE,udp_request))session_stop(-5);udp_request=0;}
    if(udp_reply){if(SESSION_S1(IPC_CLOSE,udp_reply))session_stop(-5);udp_reply=0;}
}
static int udp_stack(unsigned operation,const void *p,unsigned length,uint64_t end) {
    int r=network_send(1,operation,p,length,end);if(r){udp_transport_failed=1;return r;}
    /* Drain the already admitted operation's bounded result grace even when
     * packet time expires; never confuse that reply with a later revoke ACK. */
    r=network_wait(1,REIST_NET_RESULT,end+(operation==REIST_NET_APP_REQUEST?100:0));
    if(r&&(network_channels[1].failed||network_message.type!=REIST_NET_RESULT))udp_transport_failed=1;
    if(!r)network_health=session_now();return r;
}
static int session_udp_revoke(void) {
    /* Close app capability publication before service revocation or fencing. */
    udp_close_channels();
    int r=udp_transport_failed?-5:0;
    if(!r&&udp_grant.epoch&&network_active) {
        r=udp_stack(REIST_NET_APP_REVOKE,0,0,session_now()+1000);
        if(!r&&network_message.length)r=-71;
    }
    session_zero(&udp_grant,sizeof(udp_grant));
    if(r) {
        /* If service acknowledgement is uncertain, NIC fencing is mandatory
         * before app cancellation; no grant may survive a future group. */
        session_network_retire();network_failed=1;
    }
    return r;
}
static int64_t session_udp_import(int argc,const char *const *argv,reist_task_startup_v1_t *startup,
                                 reist_task_profile_v1_t *profile) {
    reist_app_udp_grant selected;int r=reist_app_udp_operand(argc,argv,&selected);if(r)return r;
    if(reist_udp_root_selection[0]!=0x31544f4f52445552ULL||reist_udp_root_selection[1]>8)return -22;
    if(udp_request||udp_reply||session_udp_active||network_busy)return -16;
    if(udp_epoch==UINT64_MAX)return -75;
    void *image=(void*)(uintptr_t)SESSION_S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    if((intptr_t)image<=0)return -12;
    session_bytes(image,session_prepared,REIST_X64_PREPARED_V2_BYTES);
    network_busy=1;udp_transport_failed=0;
    unsigned fault=(unsigned)reist_udp_root_selection[1];
    if(fault>=1&&fault<=7) {
        session_network_retire();network_fault=fault==7?1:fault;
        if(fault!=7)reist_udp_root_selection[1]=0;
    }
    r=network_launch();
    session_bytes(session_prepared,image,REIST_X64_PREPARED_V2_BYTES);
    session_zero(image,REIST_X64_PREPARED_V2_BYTES);if(SESSION_S1(FREE,image))session_stop(-5);
    if(r){network_failure();network_busy=0;return r;}
    if(!network_config.version||network_config.ip_address!=0xc0000202||network_config.netmask!=0xffffff00){network_busy=0;return -99;}
    r=(int)SESSION_S1(IPC_CREATE,&udp_request);if(r)goto failed;
    r=(int)SESSION_S1(IPC_CREATE,&udp_reply);if(r)goto failed;
    if(!udp_request||!udp_reply||udp_request==udp_reply)session_stop(-5);
    char request[14]="@au1:",reply[14]="@au1:";
    session_hex(request+5,udp_request);session_hex(reply+5,udp_reply);
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
    selected.epoch=++udp_epoch;selected.expires=issued+6000;udp_grant=selected;udp_sequence=0;
    r=udp_stack(REIST_NET_APP_GRANT,&udp_grant,sizeof(udp_grant),session_now()+1000);
    if(!r&&network_message.length)r=-71;
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,udp_request,(uint64_t)child>>32,1);
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,udp_reply,(uint64_t)child>>32,2);
    if(!r&&session_now()<udp_grant.expires){session_udp_active=1;return child;}
    if(!r)r=-110;
    session_udp_revoke();
    if(service_task(0,3,(uint64_t)child,0))session_stop(-5);
    int64_t retired=service_task(0,2,(uint64_t)child,1000);
    if(retired<0||(uint64_t)retired>>32>3)session_stop(-5);
failed:
    udp_close_channels();network_busy=0;return r;
}
static int64_t session_udp_wait(int *timed_out) {
    uint64_t end=udp_grant.expires;unsigned hello=0,released=0;int fault=0;
    /* Each poll is bounded; total lifetime and64 requests are independent caps. */
    for(unsigned turn=0;udp_request&&turn<6000;turn++) {
        uint64_t now=session_now();if(now>=end){fault=-110;break;}
        x86os_ipc_bulk_message_t message;session_zero(&message,sizeof(message));
        message.version=2;message.struct_size=sizeof(message);message.length=2048;
        int r=(int)SESSION_S3(IPC_RECEIVE_TIMEOUT,udp_request,&message,0);
        if(r==-11||r==-110){
            if(now-network_health>=500&&end-now>1000) {
                r=udp_stack(REIST_NET_HEALTH,0,0,now+1000);
                if(r||network_message.length){fault=r?r:-71;break;}
            }
            if(x86os_sleep_ms(1)){fault=-5;break;}continue;
        }
        if(r){fault=r;break;}
        if(message.version!=2||message.struct_size!=sizeof(message)||message.length!=608){fault=-71;break;}
        for(unsigned n=608;n<2048;n++)if(message.payload[n]){fault=-71;break;}
        if(fault)break;
        reist_app_udp_request q,response;session_bytes(&q,message.payload,608);response=q;
        now=session_now();
        if(q.result||q.deadline<=now||q.deadline>end||q.deadline-now>2000){fault=-110;break;}
        if(!hello) {
            reist_app_udp_request expected={0};expected.grant.version=1;expected.grant.size=64;
            expected.grant.application=session_child;expected.grant.protocol=17;expected.grant.peer=udp_grant.peer;
            expected.grant.local_port=udp_grant.local_port;expected.grant.peer_port=udp_grant.peer_port;expected.deadline=q.deadline;
            if(!udp_equal(&q,&expected,608)){fault=-116;break;}
            response.grant=udp_grant;hello=1;
        } else {
            if(!udp_equal(&q.grant,&udp_grant,64)||udp_sequence>=64||q.sequence!=udp_sequence+1){fault=-116;break;}
            if(reist_udp_root_selection[1]==8&&q.operation==REIST_APP_UDP_SEND)__builtin_trap();
            r=udp_stack(REIST_NET_APP_REQUEST,&q,608,q.deadline);
            if(r){fault=r;break;}
            if(network_message.length!=608){udp_transport_failed=1;fault=-71;break;}
            session_bytes(&response,network_message.payload,608);
            if(!udp_equal(&response.grant,&udp_grant,64)||response.operation!=q.operation||
               response.sequence!=q.sequence||response.deadline!=q.deadline||response.result>0||response.result< -4095||
               response.length>512||(q.operation!=REIST_APP_UDP_OPEN&&response.handle!=q.handle)){udp_transport_failed=1;fault=-71;break;}
            udp_sequence=q.sequence;
            if(q.operation==REIST_APP_UDP_RELEASE&&!response.result)released=1;
        }
        now=session_now();if(now>=q.deadline){fault=-110;break;}
        session_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=608;
        session_bytes(message.payload,&response,608);unsigned wait=(unsigned)(q.deadline-now);if(wait>100)wait=100;
        r=(int)SESSION_S3(IPC_SEND_TIMEOUT,udp_reply,&message,wait);if(r){fault=r;break;}
        if(released)break;
        if(turn==5999)fault=-110;
    }
    *timed_out=fault==-110||session_now()>=end;
    /* Successful RELEASE already invalidated the stack grant. Keep the ACK
     * endpoint alive until the child consumes it and exits; closing it here
     * would purge that queued reply before the child can resume. */
    if(fault||!released)session_udp_revoke();
    if(fault||!released)if(service_task(0,3,session_child,0))session_stop(-5);
    int64_t status=service_task(0,2,session_child,1000);
    if(status==-110) {
        *timed_out=1;if(service_task(0,3,session_child,0))session_stop(-5);
        status=service_task(0,2,session_child,1000);
    }
    if(released){udp_close_channels();session_zero(&udp_grant,sizeof(udp_grant));}
    session_udp_active=0;network_busy=0;return status;
}
