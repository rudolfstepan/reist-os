/* Separate Ring3 RFC826/IPv4/ICMP service; no DEVICE_CONTROL permission. */
#include <reist/x86_64/network_session.h>
#include <reist/x86_64/syscall.h>
#ifdef REIST_NATIVE_APP_NETWORK
#include <reist/x86_64/application_udp.h>
static reist_app_udp_state applications;
#endif
#ifdef REIST_NATIVE_APP_TCP
#include <reist/x86_64/application_tcp.h>
static reist_app_tcp_state tcp_applications;
#endif
static reist_net_channel root,frames;
static reist_net_message control,packet,response;
static reist_net_protocol protocol;
static uint64_t last_progress,operation_end;
volatile uint64_t reist_netstack_witness[8] __attribute__((section(".data.memory_witness")))={0x314b545354454e52ULL};
static int report(unsigned type,const void *data,unsigned n,int result,uint64_t end) {
    int r=reist_net_encode(&root,&response,type,data,n,result,reist_net_now(),end);
    return r?r:reist_net_send(&root,&response);
}
static uint64_t clock_now(void *p) {
    (void)p;uint64_t now=reist_net_now();
    if(operation_end>now&&now-last_progress>=250) {
        if(report(REIST_NET_HEALTH,0,0,0,operation_end))__builtin_trap();last_progress=now;
    }
    return now;
}
static int pause_ms(void *p,unsigned ms){(void)p;return reist_net_pause(ms);}
static int exchange(unsigned type,const void *data,unsigned n,uint64_t end) {
    uint64_t now=clock_now(0);if(now>=end)return -110;
    /* Do not publish a frame request that cannot retain its complete bounded
     * transport lifetime inside the packet operation. An ordinary packet
     * timeout must not poison a healthy generation's IPC sequence. */
    if(end-now<=200)return -110;
    uint64_t rpc_end=now+200;
    int r=reist_net_encode(&frames,&packet,type,data,n,0,now,rpc_end);if(r)return r;
    if((r=reist_net_send(&frames,&packet)))return r;
    for(unsigned i=0;i<200&&clock_now(0)<rpc_end;i++) {
        r=reist_net_receive(&frames,&packet,0);
        if(r!=-11)break;if(reist_net_pause(1))return -5;
    }
    if(r==-11){frames.failed=1;return -110;}if(r)return r;
    if(packet.type!=REIST_NET_RESULT){frames.failed=1;return -71;}
    if(type==REIST_NET_TX&&packet.result)frames.failed=1;
    return packet.result;
}
static int send_frame(void *p,const uint8_t *data,unsigned n,uint64_t end) {
    (void)p;int r=exchange(REIST_NET_TX,data,n,end);
    if(!r&&packet.length){frames.failed=1;return -71;}
    return r;
}
static int receive_frame(void *p,uint8_t *data,unsigned cap,uint64_t end) {
    (void)p;int r=exchange(REIST_NET_RX,0,0,end);if(r)return r;
    if(packet.length<14||packet.length>cap)return -71;
    reist_net_copy(data,packet.payload,packet.length);return (int)packet.length;
}
int main(int argc,char **argv) {
    uint64_t end;unsigned mode;if(reist_net_startup(&root,argc,argv,5,&end,&mode))return 22;
    uint32_t ep=0;
    if(reist_x64_syscall1(REIST_X64_SYS_IPC_CREATE,(uintptr_t)&ep)||!ep||report(REIST_NET_HELLO,&ep,4,0,end))return 5;
    int r=-11;
    for(unsigned n=0;n<300&&reist_net_now()<end;n++) {
        r=reist_net_receive(&root,&control,0);if(r!=-11)break;if(reist_net_pause(10))return 5;
    }
    reist_net_binding binding;
    if(r||control.type!=REIST_NET_BIND||control.length!=sizeof(binding)||control.result)return 71;
    reist_net_copy(&binding,control.payload,sizeof(binding));
    if(binding.reserved||binding.stack!=root.owner||binding.endpoint!=ep||!binding.device_epoch||
       reist_net_channel_init(&frames,ep,binding.stack,binding.driver,root.epoch)||
       reist_x64_syscall3(REIST_X64_SYS_IPC_DELEGATE,ep,binding.driver>>32,3))return 22;
    if(report(REIST_NET_BIND,0,0,0,end))return 5;
    r=-11;
    for(unsigned n=0;n<300&&reist_net_now()<end;n++) {
        r=reist_net_receive(&root,&control,0);if(r!=-11)break;if(reist_net_pause(10))return 5;
    }
    if(r||control.type!=REIST_NET_INIT||control.length||control.result)return 71;
    if(exchange(REIST_NET_HEALTH,0,0,end)||packet.length!=6||
       reist_net_protocol_init(&protocol,packet.payload,binding.device_epoch)||report(REIST_NET_READY,packet.payload,6,0,end))return 5;
    reist_netstack_witness[1]=root.owner;reist_netstack_witness[2]=root.epoch;reist_netstack_witness[3]=1;
    reist_net_io io={0,clock_now,pause_ms,send_frame,receive_frame};
#ifdef REIST_NATIVE_APP_NETWORK
    if(reist_app_udp_init(&applications,root.peer,root.owner,reist_net_now()))return 22;
#endif
#ifdef REIST_NATIVE_APP_TCP
    if(reist_app_tcp_init(&tcp_applications,root.peer,root.owner,reist_net_now()))return 22;
#endif
    for(;;) {
        r=reist_net_receive(&root,&control,50);if(r==-11||r==-110)continue;if(r)return 71;
        if(control.result)return 71;
#ifdef REIST_NATIVE_APP_TCP
        if(control.type==REIST_NET_TCP_GRANT&&control.length==64) {
            reist_app_tcp_grant grant;reist_net_copy(&grant,control.payload,sizeof(grant));
            r=applications.active?-16:reist_app_tcp_grant_set(&tcp_applications,&grant,reist_net_now());
            if(report(REIST_NET_RESULT,0,0,r,control.deadline_ms))return 5;
            continue;
        }
        if(control.type==REIST_NET_TCP_REVOKE&&!control.length) {
            reist_app_tcp_revoke(&tcp_applications);
            if(report(REIST_NET_RESULT,0,0,0,control.deadline_ms))return 5;
            continue;
        }
        if(control.type==REIST_NET_TCP_REQUEST&&control.length==608) {
            reist_app_tcp_request q,reply={0};reist_net_copy(&q,control.payload,sizeof(q));
            if(q.deadline>control.deadline_ms)return 71;
            operation_end=q.deadline;last_progress=reist_net_now();
            if(q.operation==REIST_APP_TCP_CONNECT) {
                if(mode==1)__builtin_trap();
                if(mode==2)for(;;)(void)reist_net_pause(100);
                if(mode==3)for(;;)__asm__ volatile("pause");
            }
            r=reist_app_tcp_exchange(&tcp_applications,&protocol,&io,&q,&reply);
            operation_end=0;if(frames.failed)return 5;
            if(report(REIST_NET_RESULT,r?0:&reply,r?0:sizeof(reply),r,reist_net_now()+100))return 5;
            continue;
        }
#endif
#ifdef REIST_NATIVE_APP_NETWORK
        if(control.type==REIST_NET_APP_GRANT&&control.length==64) {
#ifdef REIST_NATIVE_APP_TCP
            if(tcp_applications.active) {
                if(report(REIST_NET_RESULT,0,0,-16,control.deadline_ms))return 5;
                continue;
            }
#endif
            reist_app_udp_grant grant;reist_net_copy(&grant,control.payload,sizeof(grant));
            r=reist_app_udp_grant_set(&applications,&grant,reist_net_now());
            if(report(REIST_NET_RESULT,0,0,r,control.deadline_ms))return 5;
            continue;
        }
        if(control.type==REIST_NET_APP_REVOKE&&!control.length) {
            reist_app_udp_revoke(&applications);
            if(report(REIST_NET_RESULT,0,0,0,control.deadline_ms))return 5;
            continue;
        }
        if(control.type==REIST_NET_APP_REQUEST&&control.length==608) {
            reist_app_udp_request q,reply={0};reist_net_copy(&q,control.payload,sizeof(q));
            if(q.deadline>control.deadline_ms)return 71;
            operation_end=q.deadline;last_progress=reist_net_now();
            if(q.operation==REIST_APP_UDP_SEND||q.operation==REIST_APP_UDP_RECEIVE) {
                if(mode==1)__builtin_trap();
                if(mode==2)for(;;)(void)reist_net_pause(100);
                if(mode==3)for(;;)__asm__ volatile("pause");
            }
            r=reist_app_udp_exchange(&applications,&protocol,&io,&q,&reply);
            operation_end=0;if(frames.failed)return 5;
            if(report(REIST_NET_RESULT,r?0:&reply,r?0:sizeof(reply),r,reist_net_now()+100))return 5;
            continue;
        }
#endif
        if(control.type==REIST_NET_HEALTH&&!control.length) {
            r=exchange(REIST_NET_HEALTH,0,0,control.deadline_ms);
            if(!r&&(packet.length!=6))r=-71;
            if(report(REIST_NET_RESULT,0,0,r,control.deadline_ms))return 5;
        } else if(control.type==REIST_NET_CONTROL&&control.length==sizeof(x86os_network_control_request_t)) {
            x86os_network_control_request_t request;reist_net_copy(&request,control.payload,sizeof(request));
            operation_end=control.deadline_ms;last_progress=reist_net_now();
            if(request.operation==X86OS_NETWORK_PING) {
                if(mode==1)__builtin_trap();
                if(mode==2)for(;;)(void)reist_net_pause(100);
                if(mode==3)for(;;)__asm__ volatile("pause");
            }
            uint64_t now=clock_now(0);
            if(now>=operation_end)r=-110;
            else {
                if(request.timeout_ms>operation_end-now)request.timeout_ms=(uint32_t)(operation_end-now);
                r=reist_net_protocol_control(&protocol,&request,&io);
            }
            operation_end=0;if(frames.failed)return 5;
            x86os_network_control_result_t result={0};
            result.version=2;result.struct_size=sizeof(result);result.operation_result=r;
            result.available=result.ready=1;result.configured=protocol.configured;
            result.ip_address=protocol.ip;result.netmask=protocol.mask;result.gateway=protocol.gateway;
            const char backend[]="rtl8139-ring3";reist_net_copy(result.backend,backend,sizeof(backend));
            reist_net_copy(result.mac_address,protocol.mac,6);
            /* Result delivery has a distinct bounded transport grace; it
             * cannot extend the expired packet operation or accept late RX. */
            if(report(REIST_NET_RESULT,&result,sizeof(result),0,reist_net_now()+100))return 5;
            reist_netstack_witness[4]++;
        } else return 71;
    }
}
