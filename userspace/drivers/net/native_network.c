/* Separate Ring3 device client. Ethernet/protocol interpretation is forbidden. */
#include <reist/x86_64/network_session.h>
#include <reist/x86_64/network.h>
#include <reist/x86_64/syscall.h>
static reist_net_channel root,frames;
static reist_net_message message,reply;
static reist_net_binding binding;
static unsigned tx_slot;
/* Device32 requires its fixed 1536-byte writable admission span; Ethernet
 * wire length remains independently limited to 1514 bytes. */
static uint8_t buffer[1536],mac[6];
volatile uint64_t reist_network_driver_witness[8] __attribute__((section(".data.memory_witness")))={0x3156524454454e52ULL};
static int64_t device(unsigned op,uint64_t end,void *data,unsigned bytes) {
    uint64_t now=reist_net_now();if(end<=now)return -110;if(end-now>1000)end=now+1000;
    reist_network_request_v1 q={1,64,op,0,binding.driver,binding.device_epoch,end,(uintptr_t)data,bytes,
        op==REIST_NETWORK_TX||op==REIST_NETWORK_COMPLETE?tx_slot:0,0};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,32,(uintptr_t)&q);
}
static int answer(reist_net_channel *channel,unsigned type,const void *data,unsigned n,int result,uint64_t end) {
    int r=reist_net_encode(channel,&reply,type,data,n,result,reist_net_now(),end);
    return r?r:reist_net_send(channel,&reply);
}
int main(int argc,char **argv) {
    uint64_t end;unsigned mode;
    if(reist_net_startup(&root,argc,argv,4,&end,&mode))return 22;
    int r=-11;
    for(unsigned n=0;n<300&&reist_net_now()<end;n++) {
        r=reist_net_receive(&root,&message,0);if(r!=-11)break;if(reist_net_pause(10))return 5;
    }
    if(r||message.type!=REIST_NET_INIT||message.result||message.length!=sizeof(binding))return 71;
    reist_net_copy(&binding,message.payload,sizeof(binding));
    if(binding.reserved||binding.driver!=root.owner||!binding.device_epoch||
       reist_net_channel_init(&frames,binding.endpoint,binding.driver,binding.stack,root.epoch))return 22;
    reist_network_driver_witness[1]=binding.driver;reist_network_driver_witness[2]=binding.device_epoch;
    r=(int)device(REIST_NETWORK_RESET,end,0,0);if(r)return 19;
    for(unsigned n=0;n<100&&reist_net_now()<end;n++) {
        r=(int)device(REIST_NETWORK_START,end,0,0);if(r!=-11)break;if(reist_net_pause(10))return 5;
    }
    if(r)return 5;
    int64_t packed=device(REIST_NETWORK_MAC,end,0,0);if(packed<0)return 5;
    for(unsigned n=0;n<6;n++)mac[n]=(uint8_t)((uint64_t)packed>>(n*8));
    /* CPU qualification runs with the NIC initialized, before READY. The
     * startup deadline can contain a complete CPU window; a later200ms frame
     * RPC is intentionally allowed to fence first and cannot prove CPU32. */
    if(mode==3)for(;;)__asm__ volatile("pause");
    if(answer(&root,REIST_NET_READY,mac,6,0,end))return 5;
    reist_network_driver_witness[3]=1;
    for(;;) {
        r=reist_net_receive(&frames,&message,50);if(r==-11||r==-110)continue;if(r)return 71;
        if(message.result)return 71;end=message.deadline_ms;
        if(message.type==REIST_NET_HEALTH && !message.length) {
            if(answer(&frames,REIST_NET_RESULT,mac,6,0,end))return 5;
        } else if(message.type==REIST_NET_RX && !message.length) {
            int64_t count=device(REIST_NETWORK_RX,end,buffer,sizeof(buffer));
            if(count>REIST_NET_FRAME)return 71;
            if(answer(&frames,REIST_NET_RESULT,count>0?buffer:0,count>0?(unsigned)count:0,count<0?(int)count:0,end))return 5;
            reist_net_zero(buffer,sizeof(buffer));
        } else if(message.type==REIST_NET_TX && message.length>=14&&message.length<=REIST_NET_FRAME) {
            r=(int)device(REIST_NETWORK_TX,end,message.payload,message.length);
            if(!r) {
                reist_network_driver_witness[4]++;
                if(mode==1)__builtin_trap();
                if(mode==2)for(;;)(void)reist_net_pause(100);
                uint64_t limit=reist_net_now()+100;if(limit>end)limit=end;
                for(unsigned n=0;n<100&&reist_net_now()<limit;n++) {
                    r=(int)device(REIST_NETWORK_COMPLETE,limit,0,0);if(r!=-11)break;
                    if(reist_net_pause(1))return 5;
                }
                if(r==-11)r=-110;
                if(!r)tx_slot=(tx_slot+1)&3U;
            }
            if(answer(&frames,REIST_NET_RESULT,0,0,r,end))return 5;
        } else return 71;
        reist_network_driver_witness[5]++;
    }
}
