/* Private opt-in shell ownership; no controller protocol in the root. */
#include <reist/x86_64/input.h>
extern const unsigned char reist_native_input_image[];
extern const size_t reist_native_input_image_bytes;
static uint64_t session_input_driver,session_input_epoch,session_input_end;
static uint32_t session_input_endpoint,session_input_ingress;
static char session_input_mode[2];
static void session_input_retire(void) {
#ifdef REIST_NATIVE_TERMINAL_SERVICE
    if(session_terminal_service) {
        if(reist_x64_terminal_service(7,session_terminal_service) ||
           reist_x64_terminal_service(7,session_terminal_service))session_stop(-5);
        session_previous_terminal_service=session_terminal_service;session_terminal_service=0;
    }
    session_input_service_pending=0;
#endif
    if(session_input_epoch) {
        reist_input_request_v1 q={1,64,REIST_INPUT_FENCE,0,session_input_driver,session_input_epoch,0,0,{0,0}};
        if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q))session_stop(-5);
        session_input_epoch=0;
    }
    if(session_input_driver) {
        if(service_task(0,3,session_input_driver,0))session_stop(-5);
        int64_t r=service_task(0,2,session_input_driver,1000);
        if(r<0||(uint64_t)r>>32>3)session_stop(-5);
        session_input_driver=0;
    }
    if(session_input_ingress) {
        if(SESSION_S1(IPC_CLOSE,session_input_ingress))session_stop(-5);
        session_input_ingress=0;
    }
    if(session_input_endpoint) {
        if(SESSION_S1(IPC_CLOSE,session_input_endpoint))session_stop(-5);
        session_input_endpoint=0;
    }
    session_input_end=0;session_input_mode[0]=0;
}
static int session_input_arguments(int argc,const char *const *argv,reist_task_startup_v1_t *startup,reist_task_profile_v1_t *profile) {
    if(session_input_driver||session_input_endpoint||session_input_ingress||session_input_end)session_stop(-5);
    if(argc>2)return -22;
    profile->masks[0]&=~((1ULL<<49)|(1ULL<<52)|(1ULL<<55));
    unsigned mode=argc==2&&argv[1]?(unsigned char)argv[1][0]:0;
    if(argc==2&&(!mode||argv[1][1]))return -22;
#ifdef REIST_NATIVE_TERMINAL_SERVICE
    if(mode&&mode!='u'&&mode!='q'&&mode!='h'&&mode!='b'&&mode!='s'&&mode!='m'&&mode!='c'&&mode!='d'&&mode!='e')return -22;
#else
    if(mode&&mode!='u'&&mode!='q'&&mode!='h'&&mode!='b'&&mode!='s'&&mode!='m')return -22;
#endif
    int r=(int)SESSION_S1(IPC_CREATE,&session_input_endpoint);if(r)return r;
    r=(int)SESSION_S1(IPC_CREATE,&session_input_ingress);if(r){session_input_retire();return r;}
    session_input_end=session_now()+5000;session_input_mode[0]=(char)mode;
    char ep[9],hi[9],lo[9];session_hex(ep,session_input_endpoint);
    session_hex(hi,(uint32_t)(session_input_end>>32));session_hex(lo,(uint32_t)session_input_end);
    const char *args[]={argv[0],session_input_mode,ep,hi,lo};
    r=reist_x64_startup_init(startup,5,args);if(r)session_input_retire();return r;
}
static int session_input_start(uint64_t child) {
    char ep[9],target[9],hi[9],lo[9];session_hex(ep,session_input_ingress);session_hex(target,(uint32_t)(child>>32));
    session_hex(hi,(uint32_t)(session_input_end>>32));session_hex(lo,(uint32_t)session_input_end);
    const char *args[]={"ps2",ep,target,hi,lo,session_input_mode};reist_task_startup_v1_t startup;
    int r=reist_x64_startup_init(&startup,6,args);
    if(!r)r=reist_x64_image_prepare_v2(session_prepared,reist_native_input_image,reist_native_input_image_bytes);
    int64_t driver=r;
    if(!r) {
        /* Only clock/sleep/exit/identity and this endpoint's SEND operation. */
        reist_task_profile_v1_t profile={1,40,{(1ULL<<9)|(1ULL<<22)|(1ULL<<41)|(1ULL<<42)|(1ULL<<53),1ULL<<49,0},0};
        driver=reist_x64_task_import_periodic(session_prepared,&profile,32,1000,&startup);
    }
    session_zero(session_prepared,REIST_X64_PREPARED_V2_BYTES);session_zero(&startup,sizeof(startup));
    if(driver<-4095)session_stop(-5);
    if(driver<0)return (int)driver;
    if((uint32_t)driver!=5 || !((uint64_t)driver>>32) || (uint64_t)driver>>32>0x7fffffff)session_stop(-5);
    session_input_driver=(uint64_t)driver;
#ifdef REIST_NATIVE_TERMINAL_SERVICE
    session_input_service_pending=session_input_driver;
#endif
    r=(int)SESSION_S3(IPC_DELEGATE,session_input_ingress,(uint64_t)driver>>32,1);
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,session_input_endpoint,child>>32,2);
    if(r)return r;
    reist_input_request_v1 q={1,64,REIST_INPUT_BIND,0,(uint64_t)driver,0,0,0,{0,0}};
    int64_t epoch=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
    if(epoch<=0)return epoch>=-4095&&epoch<0?(int)epoch:-5;
    session_input_epoch=(uint64_t)epoch;return 0;
}
static int64_t session_input_wait(uint64_t child) {
    unsigned delivered=0,empty=0;uint64_t end=session_input_end;int isolate=0;
    for(unsigned turn=0;turn<82 && delivered<32 && empty<50;turn++) {
        uint64_t now=session_now();if(now>=session_input_end)break;
        unsigned remaining=(unsigned)(session_input_end-now>100?100:session_input_end-now);
        x86os_ipc_message_t m;session_zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=128;
        int64_t r=SESSION_S3(IPC_RECEIVE_TIMEOUT,session_input_ingress,&m,remaining);
        if(r==-110){empty++;continue;}if(r){if(r!=-32)isolate=1;break;}
        unsigned bad=m.version!=1||m.struct_size!=140||m.length!=64;
        for(unsigned n=64;n<128;n++)bad|=m.payload[n];
        reist_input_event_v1 event;session_bytes(&event,m.payload,64);
        if(bad||!reist_input_event_valid(&event,session_input_driver,child,session_input_epoch,delivered+1)||
           event.owner!=session_input_driver||event.epoch!=session_input_epoch){isolate=1;break;}
        now=session_now();if(now>=session_input_end)break;
        remaining=(unsigned)(session_input_end-now>100?100:session_input_end-now);
        r=SESSION_S3(IPC_SEND_TIMEOUT,session_input_endpoint,&m,remaining);
        if(r){isolate=1;break;}delivered++;
        if(event.type==REIST_INPUT_ERROR)break;
    }
    if(isolate)session_input_retire();
    for(unsigned n=0;n<5;n++) {
        uint64_t now=session_now();if(now>=end)return -110;
        unsigned remaining=(unsigned)(end-now>1000?1000:end-now);
        int64_t result=service_task(0,2,child,remaining);if(result!=-110)return result;
    }
    return -110;
}
