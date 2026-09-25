/* Persistent GUI input role. Existing bounded i8042 mediator and PS/2 decoder. */
#include "native_input.h"
#include "../../gui/lib/native_surface.h"
static reist_native_role_args args;
static uint64_t epoch,sequence;
static reist_graphical_rate rate;
static uint64_t clock_ms(void *p){(void)p;return reist_native_now();}
static int sleep_ms(void *p,unsigned ms){(void)p;return reist_native_sleep(ms);}
static int64_t transfer(void *p,unsigned op,unsigned value,uint64_t end) {
    (void)p;reist_input_request_v1 q={1,64,op,0,args.owner,epoch,end,value,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
}
static int publish(reist_input_event_v1 *e) {
#if REIST_GRAPHICAL_START_MS == 10000U
    uint64_t stamp=reist_native_now();
    int r=reist_graphical_charge(&rate,stamp,128);if(r)return r;
#else
    int r=reist_graphical_charge(&rate,reist_native_now(),128);if(r)return r;
#endif
    if(sequence==UINT64_MAX)return -75;
    e->version=2;e->size=64;e->owner=args.owner;e->target=(uint64_t)args.peer_generation<<32|4;
    e->epoch=epoch;e->sequence=++sequence;
#if REIST_GRAPHICAL_START_MS == 10000U
    r=reist_native_send(args.endpoint,e,64,100);
    if(!r) {
        x86os_ipc_message_t sent={0};sent.version=1;sent.struct_size=140;sent.length=64;
        const unsigned char *bytes=(const unsigned char*)e;
        for(unsigned n=0;n<64;n++)sent.payload[n]=bytes[n];
        reist_native_audit_append(args.endpoint,&sent,stamp);
    }
    return r;
#else
    return reist_native_send(args.endpoint,e,64,100);
#endif
}
static int input_failure(unsigned site,int status,int exit_status) {
#if REIST_GRAPHICAL_START_MS == 10000U
    char message[]="INPUT_FAILURE site=00000000 status=00000000\n";
    const char digits[]="0123456789abcdef";
    for(unsigned n=0;n<8;n++) {
        message[19+n]=digits[(site>>(28-4*n))&15];
        message[35+n]=digits[((unsigned)status>>(28-4*n))&15];
    }
    (void)reist_x64_syscall3(REIST_X64_SYS_WRITE,1,(uintptr_t)message,sizeof(message)-1);
#else
    (void)site;(void)status;
#endif
    return exit_status;
}
int main(int argc,char **argv) {
    if(reist_native_role_arguments(argc,argv,5,&args))return 22;
    reist_input_request_v1 q={1,64,REIST_INPUT_QUERY,0,args.owner,0,0,0,{0,0}};
    int64_t r=-13;
    for(unsigned n=0;n<REIST_GRAPHICAL_START_MS/10&&reist_native_now()<args.deadline;n++) {
        r=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
        if(r!=-13)break;if(reist_native_sleep(10))return 5;
    }
    if(r<=0)return 110;epoch=(uint64_t)r;
    reist_ps2_decoder decoder;reist_ps2_clear(&decoder);
    reist_ps2_transport transport={0,clock_ms,transfer,sleep_ms};
    uint64_t selftest_end=reist_native_now()+1000;
    if(selftest_end>args.deadline)selftest_end=args.deadline;
    if(reist_ps2_initialize(&transport,selftest_end))return 71;
    reist_input_event_v1 event={0};event.type=REIST_INPUT_HEALTHY;
    if(publish(&event))return 71;
    uint64_t heartbeat=reist_native_now(),last=heartbeat;
    for(;;) {
        uint64_t now=reist_native_now();if(now<last||now>UINT64_MAX-1000)return 75;last=now;
        if(args.mode!='0' && reist_native_fault_due(now,args.deadline) && reist_native_fault(args.mode))return 110;
        if((decoder.keyboard_end&&now>=decoder.keyboard_end)||
           (decoder.mouse_end&&now>=decoder.mouse_end))return 110;
#if REIST_GRAPHICAL_START_MS == 10000U
        unsigned received=0;
#endif
        for(unsigned n=0;n<8;n++) {
#if REIST_GRAPHICAL_START_MS == 10000U
            /* The first read uses the clock just validated above. Further
             * bytes still get a fresh timestamp for decoder deadlines. */
            if(n)now=reist_native_now();if(now>UINT64_MAX-100)return 75;
#else
            now=reist_native_now();if(now>UINT64_MAX-100)return 75;
#endif
            r=transfer(0,REIST_INPUT_READ,0,now+100);
            if(r==-11)break;if(r<=0||r>65536)return input_failure(1,(int)r,r==-122?122:71);
#if REIST_GRAPHICAL_START_MS == 10000U
            received=1;
#endif
            unsigned raw=(unsigned)r-1;
            int decoded=reist_ps2_decode(&decoder,(uint8_t)(raw>>8),(uint8_t)raw,now,&event);
            if(decoded<0)return input_failure(2,decoded,71);
            if(decoded){int sent=publish(&event);if(sent)return input_failure(3,sent,71);}
        }
        now=reist_native_now();
        if(now-heartbeat>=250) {
            reist_native_zero(&event,sizeof(event));event.type=REIST_INPUT_HEALTHY;
            int sent=publish(&event);if(sent)return input_failure(4,sent,71);heartbeat=now;
        }
#if REIST_GRAPHICAL_START_MS == 10000U
        /* Idle polling remains below the decoder's bounded packet deadline;
         * avoid spending the periodic CPU allowance on empty reads. */
        if(reist_native_sleep(received?10:50))return 5;
#else
        if(reist_native_sleep(10))return 5;
#endif
    }
}
