/* Ordinary shell network adapter. Root supervises; packet parsing is Ring3
 * netstack's responsibility. Filesystem retirement also retires this group
 * before its slot4/5 lifetime can outlive the required slot2/3 dependencies. */
#include <reist/x86_64/network_session.h>
#include <reist/x86_64/network.h>
#include <reist/x86_64/graphical_session.h> /* existing vendor hash adapter */
#include "network_manifest.h"
static void *network_images[2];
static uint64_t network_owners[2],network_epoch,network_device_epoch,network_health;
static reist_net_channel network_channels[2];
static reist_net_message network_message;
static unsigned network_active,network_busy,network_failed,network_blocked,network_restarts;
static x86os_network_control_request_t network_config;
static const char *const network_paths[2]={"/netdrv.prg","/netstack.prg"};
volatile uint64_t reist_network_selection[2] __attribute__((section(".data.memory_witness")))={0x3153454e54454e52ULL,0};
static unsigned network_fault;
static uint8_t network_mac[6];
static uint64_t network_hash_now(void *p){(void)p;return session_now();}
static int network_hash_sleep(void *p,unsigned n){(void)p;return x86os_sleep_ms(n);}
static const reist_graphical_hash_ops network_hash_ops={0,network_hash_now,network_hash_sleep};
static int session_network_retire(void) {
    uint64_t end=session_now()+5000;
    network_active=0;
    if(network_device_epoch) {
        reist_network_request_v1 q={1,64,REIST_NETWORK_FENCE,0,network_owners[0],network_device_epoch,0,0,0,0,0};
        if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,32,(uintptr_t)&q))session_stop(-5);
        network_device_epoch=0;
    }
    for(unsigned n=0;n<2;n++) {
        if(network_channels[n].endpoint&&service_close(0,network_channels[n].endpoint))session_stop(-5);
        session_zero(&network_channels[n],sizeof(network_channels[n]));
    }
    /* Stack owns the frame endpoint. Cancel/reap it before the driver. */
    for(unsigned n=2;n>0;n--)if(network_owners[n-1]) {
        uint64_t owner=network_owners[n-1];
        if(service_task(0,3,owner,0))session_stop(-5);
        int64_t status=service_task(0,2,owner,1000);
        if(status<0||(uint64_t)status>>32>3||session_now()>=end)session_stop(-5);
        network_owners[n-1]=0;
    }
    return 0;
}
static void session_network_free(void) {
    for(unsigned n=0;n<2;n++)if(network_images[n]) {
        session_zero(network_images[n],REIST_X64_PREPARED_V2_BYTES);
        if(SESSION_S1(FREE,network_images[n]))session_stop(-5);network_images[n]=0;
    }
}
static int network_capture(void) {
    for(unsigned n=0;n<2;n++) {
        if(network_images[n])continue;
        x86os_file_info_t info;int r=reist_vfs_stat(network_paths[n],&info,1000);if(r)return r;
        if(info.type!=X86OS_FILE)return -22;
        uint64_t end=session_observation.deadline_ms;
        if(session_operation_deadline)session_stop(-5);session_operation_deadline=end;
        r=reist_x64_file_finish_v2(session_prepared,session_workspace,&session_fs,&session_transport,&session_observation);
        session_operation_deadline=0;session_zero(&session_observation,sizeof(session_observation));
        if(r)return session_operation_result(r);
        r=reist_graphical_hash_admit(session_prepared,REIST_GRAPHICAL_PREPARED_HASH_BYTES,network_hashes[n],&network_hash_ops);
        if(!r&&session_now()>=end)r=-110;
        if(!r) {
            void *image=(void*)(uintptr_t)SESSION_S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
            if((intptr_t)image<=0)r=-12;
            else {session_bytes(image,session_prepared,REIST_X64_PREPARED_V2_BYTES);network_images[n]=image;}
        }
        session_zero(session_prepared,REIST_X64_PREPARED_V2_BYTES);if(r)return r;
    }
    return 0;
}
static int network_send(unsigned role,unsigned type,const void *data,unsigned n,uint64_t end) {
    int r=reist_net_encode(&network_channels[role],&network_message,type,data,n,0,session_now(),end);
    return r?r:reist_net_send(&network_channels[role],&network_message);
}
static int network_wait(unsigned role,unsigned type,uint64_t end) {
    uint64_t health_end=session_now()+1000;
    for(unsigned turn=0;turn<3000&&session_now()<end;turn++) {
        if(network_active&&session_now()>=health_end)return -110;
        int r=reist_net_receive(&network_channels[role],&network_message,0);
        if(r==-11){if(x86os_sleep_ms(1))return -5;continue;}
        if(r)return r;
        if(role==1&&network_message.type==REIST_NET_HEALTH&&!network_message.length&&!network_message.result){health_end=session_now()+1000;continue;}
        return network_message.type==type?network_message.result:-71;
    }
    return -110;
}
static int network_create(unsigned role,uint64_t end) {
    uint32_t ep=0;int r=service_endpoint(0,&ep);if(r)return r;
    network_channels[role].endpoint=ep;
    char eptext[9],root[9],eh[9],el[9],dh[9],dl[9],mode[2]={'0',0};
    session_hex(eptext,ep);session_hex(root,(uint32_t)session_policy.owner);
    session_hex(eh,(uint32_t)(network_epoch>>32));session_hex(el,(uint32_t)network_epoch);
    session_hex(dh,(uint32_t)(end>>32));session_hex(dl,(uint32_t)end);
    if(network_fault>=1&&network_fault<=6&&(network_fault-1)/3==role)mode[0]=(char)('1'+(network_fault-1)%3);
    const char *args[]={network_paths[role],eptext,root,eh,el,dh,dl,mode};
    reist_task_startup_v1_t startup;r=reist_x64_startup_init(&startup,8,args);if(r)return r;
    uint64_t mask=(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(1ULL<<53)|(1ULL<<54);
    if(role==1)mask|=(1ULL<<49)|(1ULL<<52)|(1ULL<<54)|(1ULL<<55);
    reist_task_profile_v1_t profile={1,40,{mask,role?0:1ULL<<49,0},0};
    int64_t child=reist_x64_task_import_periodic(network_images[role],&profile,32,1000,&startup);
    session_zero(&startup,sizeof(startup));if(child<0)return (int)child;
    network_owners[role]=(uint64_t)child;
    if((uint32_t)child!=4+role)session_stop(-5);
    r=reist_net_channel_init(&network_channels[role],ep,session_policy.owner<<32,(uint64_t)child,network_epoch);
    return r?r:service_delegate(0,ep,(uint64_t)child>>32);
}
static int network_restart_budget(void) {
    if(network_blocked)return -11;
    if(network_restarts>=2){network_blocked=1;return -11;}
    reist_session_policy_v1 proposal;session_bytes(&proposal,&session_policy,sizeof(proposal));
    int r=reist_session_policy_restart(&proposal,session_now());
    if(r&&r!=-11)return r;
    if(r==-11){proposal.degraded=session_policy.degraded;network_blocked=1;}
    session_bytes(&session_policy,&proposal,sizeof(proposal));if(!r)network_restarts++;
    return r;
}
static int network_control_pause(uint64_t end,unsigned milliseconds) {
    unsigned delay=milliseconds/4;if(delay>250)delay=250;
    for(unsigned n=0;n<3&&delay;n++) {
        unsigned part=delay>100?100:delay;uint64_t now=session_now();
        if(now>=end||end-now<=part)return -110;
        int r=x86os_sleep_ms(part);if(r)return r;delay-=part;
    }
    return session_now()>=end?-110:0;
}
static int network_rpc(const x86os_network_control_request_t *q,x86os_network_control_result_t *out) {
    uint64_t now=session_now();unsigned ms=q->timeout_ms?q->timeout_ms:1000;
    uint64_t end=now+ms;int r=network_control_pause(end,ms);if(r)return r;
    r=network_send(1,REIST_NET_CONTROL,q,sizeof(*q),end);if(r)return r;
    r=network_wait(1,REIST_NET_RESULT,end+100);if(r)return r;
    if(network_message.length!=sizeof(*out))return -71;
    x86os_network_control_result_t candidate;session_bytes(&candidate,network_message.payload,sizeof(candidate));
    if(candidate.version!=2||candidate.struct_size!=sizeof(candidate)||candidate.available!=1||candidate.ready!=1||
       candidate.configured>1||candidate.reserved[0]||candidate.reserved[1]||candidate.dns_server||
       candidate.operation_result>0||candidate.operation_result< -4095)return -71;
    static const char backend[16]="rtl8139-ring3";
    for(unsigned n=0;n<16;n++)if(candidate.backend[n]!=backend[n])return -71;
    for(unsigned n=0;n<6;n++)if(candidate.mac_address[n]!=network_mac[n])return -71;
    const x86os_network_control_request_t *expected=
        q->operation==X86OS_NETWORK_CONFIGURE&&!candidate.operation_result?q:&network_config;
    if(candidate.configured!=(expected->version!=0)||candidate.ip_address!=expected->ip_address||
       candidate.netmask!=expected->netmask||candidate.gateway!=expected->gateway)return -71;
    session_bytes(out,&candidate,sizeof(candidate));network_health=session_now();return 0;
}
static int network_restart_pause(uint64_t end) {
    for(unsigned n=0;n<10;n++) {
        uint64_t now=session_now();if(now>=end||end-now<=100)return -110;
        int r=x86os_sleep_ms(100);if(r)return r;
    }
    return session_now()>=end?-110:0;
}
static int network_launch(void) {
    if(network_active)return 0;if(network_blocked||session_policy.degraded)return -11;
    unsigned recovering=network_failed;
    if(network_failed){int r=network_restart_budget();if(r)return r;network_failed=0;}
    int r=network_capture();if(r)return r;
    /* Recreate normal filesystem dependencies before assigning exact slots. */
    r=session_ensure(session_now()+1000,0);if(r)return r;
    if(network_epoch==UINT64_MAX)return -75;network_epoch++;
    uint64_t end=session_now()+3000;
    if(recovering&&(r=network_restart_pause(end)))return r;
    if((r=network_create(0,end))||(r=network_create(1,end)))return r;
    /* Both children now own their immutable injected startup arguments. A
     * one-shot startup fault must not be repeated merely because READY fails. */
    if(reist_network_selection[1]!=11)network_fault=0;
    if((r=network_wait(1,REIST_NET_HELLO,end)))return r;
    if(network_message.length!=4)return -71;uint32_t ep;session_bytes(&ep,network_message.payload,4);if(!ep)return -71;
    reist_network_request_v1 device={1,64,REIST_NETWORK_BIND,0,network_owners[0],0,0,0,0,0,0};
    int64_t epoch=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,32,(uintptr_t)&device);
    if(epoch<=0)return epoch<0?(int)epoch:-5;network_device_epoch=(uint64_t)epoch;
    reist_net_binding binding={network_owners[0],network_owners[1],network_device_epoch,ep,0};
    if((r=network_send(1,REIST_NET_BIND,&binding,sizeof(binding),end))||
       (r=network_wait(1,REIST_NET_BIND,end)))return r;
    if(network_message.length)return -71;
    if((r=network_send(0,REIST_NET_INIT,&binding,sizeof(binding),end))||
       (r=network_wait(0,REIST_NET_READY,end)))return r;
    if(network_message.length!=6)return -71;
    uint8_t mac[6];session_bytes(mac,network_message.payload,6);
    if((r=network_send(1,REIST_NET_INIT,0,0,end))||
       (r=network_wait(1,REIST_NET_READY,end)))return r;
    if(network_message.length!=6)return -71;
    for(unsigned n=0;n<6;n++)if(mac[n]!=network_message.payload[n])return -71;
    unsigned bits=0;for(unsigned n=0;n<6;n++)bits|=mac[n];if(!bits||(mac[0]&1))return -71;
    session_bytes(network_mac,mac,6);
    network_active=1;network_health=session_now();
    if(network_config.version) {
        x86os_network_control_result_t out;r=network_rpc(&network_config,&out);
        if(!r)r=out.operation_result;
    }
    return r;
}
static void network_failure(void) {session_network_retire();network_failed=1;}
static void session_network_poll(void) {
    if(network_busy)return;
    if(!network_active) {
        if(network_failed&&!network_blocked) {
            network_busy=1;
            int r=network_launch();if(r)network_failure();
            network_busy=0;
        }
        return;
    }
    if(session_now()-network_health<400)return;
    network_busy=1;uint64_t end=session_now()+500;
    int r=network_send(1,REIST_NET_HEALTH,0,0,end);
    if(!r)r=network_wait(1,REIST_NET_RESULT,end);
    if(!r&&network_message.length)r=-71;
    if(r)network_failure();else network_health=session_now();network_busy=0;
}
int x86os_network_control(const x86os_network_control_request_t *q,x86os_network_control_result_t *out) {
    if(!q||!out||q->version!=2||q->struct_size!=sizeof(*q)||q->reserved||
       q->operation<1||q->operation>4||q->timeout_ms>2000)return -22;
    if(network_busy)return -16;
    if(reist_network_selection[0]!=0x3153454e54454e52ULL||reist_network_selection[1]>12)return -22;
    x86os_network_control_request_t admitted;session_bytes(&admitted,q,sizeof(admitted));
    /* Existing ordinary arp submits timeout0. Its native synchronous adapter
     * uses a bounded1000ms synchronous lifetime, including control pacing. */
    if(admitted.operation==X86OS_NETWORK_ARP_REQUEST&&!admitted.timeout_ms)admitted.timeout_ms=1000;
    network_busy=1;
    if(!network_epoch)network_fault=reist_network_selection[1]==11?1:(unsigned)reist_network_selection[1];
    int r=network_launch();
    if(!r&&reist_network_selection[1]==12&&q->operation==X86OS_NETWORK_PING)__builtin_trap();
    if(!r)r=network_rpc(&admitted,out);
    if(!r&&q->operation==X86OS_NETWORK_CONFIGURE&&!out->operation_result)session_bytes(&network_config,q,sizeof(*q));
    if(r)network_failure();network_busy=0;return r?r:out->operation_result;
}
