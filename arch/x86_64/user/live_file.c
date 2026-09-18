/* Opt-in composition only: the real filesystem/ATA helpers remain in Ring3. */
#ifndef REIST_NATIVE_LIVE_FILE
#error NativeLiveFile requires explicit admission
#endif
#define REIST_FILE_LAUNCH 1
#include "filesystem.c"
#if PROGRAM_ID==0
#include <reist/x86_64/file_image.h>
static volatile uint32_t live_file_selection[4] __attribute__((used))={1,0,2,0};
static volatile uint64_t live_file_record[10] __attribute__((used));

static void fill(void *p,unsigned size,unsigned char value) {
    typedef uint64_t word __attribute__((may_alias,aligned(1)));
    unsigned char *bytes=p;uint64_t v=value*0x0101010101010101ULL;
    while(size>=8) { *(volatile word *)bytes=v;bytes+=8;size-=8; }
    while(size--) *bytes++=value;
}
static void witness(unsigned phase,uint64_t fs,uint64_t driver,uint64_t app,
                    int result,void *record,void *workspace,unsigned round) {
    live_file_record[1]=phase;live_file_record[2]=fs;live_file_record[3]=driver;
    live_file_record[4]=app;live_file_record[5]=(uint64_t)(int64_t)result;
    live_file_record[6]=(uintptr_t)record;live_file_record[7]=(uintptr_t)workspace;
    live_file_record[8]=round;live_file_record[9]=live_layout;
    live_file_record[0]=0x4c49564546494c31ULL;
#ifdef REIST_NATIVE_SERVICE_CONSOLE
    if(phase==2)service_console_probe();
#endif
}
static int retire(uint64_t fs,uint64_t driver,int64_t fs_status,int64_t driver_status) {
    REQUIRE(!port_control(driver,REIST_PIO_FENCE),240);
    /* A failed init has already sent its error but may not have exited90 yet.
     * Preserve that receipt and an exhausted service's quota receipt. */
    if(fs_status!=90 && fs_status!=((1LL<<32)|256))
        REQUIRE(!task_control(3,fs,0),241);
    REQUIRE(task_control(2,fs,1000)==fs_status,242);
    if(driver_status!=((1LL<<32)|256)) REQUIRE(!task_control(3,driver,0),243);
    REQUIRE(task_control(2,driver,1000)==driver_status,244);
    REQUIRE(!port_control(driver,REIST_PIO_FENCE) && task_control(2,fs,1)==-10 &&
            task_control(2,driver,1)==-10,245);
    REQUIRE(!S1(IPC_CLOSE,control_ep) && !S1(IPC_CLOSE,driver_control),246);
    return 0;
}
int main(int argc,char **argv,char **envp) {
    REQUIRE(argc==2 && !argv[2] && !envp[0] && argv[1][0]=='0',200);
    unsigned version=live_file_selection[0],test=live_file_selection[1];
    live_layout=live_file_selection[2];
    REQUIRE(version==1 && test<=17 && live_layout<=4 && !live_file_selection[3],201);
    void *record=(void *)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    reist_file_image_workspace *workspace=(void *)(uintptr_t)S1(MALLOC,sizeof(*workspace));
    REQUIRE((intptr_t)record>0 && (intptr_t)workspace>0,202);
    reist_fs_transport transport={0,now,fs_send,fs_receive};
    const char *path=live_layout<2?"/BOOT.PRG":"/boot.prg";
    uint64_t previous_fs=0,previous_driver=0,previous_program=0;
    for(unsigned round=0;round<2;round++) {
        mode=round?0:test==5?1:test==6?5:test==7||test==13?6:test==10?4:
             test==11?2:test==12?3:test==14?7:0;
        unsigned options=mode|(round?16:0)|(live_layout<<8);
        REQUIRE(!S1(IPC_CREATE,&driver_control) && !S1(IPC_CREATE,&control_ep),203);
        int64_t driver=create(record,2,options,driver_control);
        int64_t fs=create(record,3,options,control_ep);
        REQUIRE(driver>0 && fs>0 && (uint64_t)driver>previous_driver && (uint64_t)fs>previous_fs,204);
        REQUIRE(!port_control(driver,REIST_PIO_BIND),205);
        if(previous_driver) REQUIRE(port_control(previous_driver,REIST_PIO_FENCE)==-13,206);
        Control c={driver,fs,0,0,0,0,1,0,0};
        REQUIRE(!control_send(driver_control,&c) && !control_receive(driver_control,&c),207);
        REQUIRE(c.owner==(uint64_t)driver && c.peer==(uint64_t)fs && c.phase==2 &&
                !c.result && c.request && c.reply &&
                c.sectors==(live_layout==0?2880:live_layout==1?70000:256),208);
        c.owner=fs;c.peer=driver;c.phase=3;REQUIRE(!control_send(control_ep,&c),209);
        if(mode==6 || mode==7) {
            REQUIRE(!control_receive(driver_control,&c) && c.owner==(uint64_t)driver && c.phase==9,210);
            if(test==7) __asm__ volatile("ud2");
        }
        REQUIRE(!control_receive(control_ep,&c) && c.owner==(uint64_t)fs &&
                c.peer==(uint64_t)driver && c.phase==4,211);
        fill(record,REIST_X64_PREPARED_V2_BYTES,0xa5);fill(workspace,sizeof(*workspace),0x5a);
        int result=c.result;reist_fs_client client={0};
        int failed_init=mode>=5;
        if(failed_init) REQUIRE(result<0,212);
        else {
            REQUIRE(!result && !reist_fs_client_bind(&client,fs),213);
            result=reist_x64_file_prepare_v2(record,workspace,&client,&transport,path,9,1800);
            int expected=test==4?-22:test==9?-27:mode==4?-71:0;
            if(mode>=1 && mode<=3) REQUIRE(result==-32 || result==-110,214);
            else REQUIRE(result==expected,215);
            const volatile uint8_t *p=(const void *)workspace;
            for(unsigned n=0;n<sizeof(*workspace);n++) REQUIRE(!p[n],216);
        }
        if(result) {
            const volatile uint8_t *p=record;
            for(unsigned n=0;n<REIST_X64_PREPARED_V2_BYTES;n++) REQUIRE(p[n]==0xa5,217);
        }
        witness(1,fs,driver,0,result,record,workspace,round);
        uint32_t app_ep=0;
        if(!result) {
            REQUIRE(!S1(IPC_CREATE,&app_ep),218);
            char channel[9],option[2]={(char)('0'+(!round && test<=3?test:0)),0};number(channel,app_ep);
            const char *args[]={"/boot.prg",channel,option};reist_task_startup_v1_t startup;
            REQUIRE(!reist_x64_startup_init(&startup,3,args),219);
            reist_task_profile_v1_t profile={1,40,{MASK,0,0},0};
            int64_t program=reist_x64_task_import_wide(record,&profile,32,&startup);
            if(test==8 && !round) {
                REQUIRE(program==-12,220);program=reist_x64_task_import_wide(record,&profile,32,&startup);
            }
            REQUIRE(program>0 && (uint32_t)program==4 && (uint64_t)program>previous_program,221);
            fill(record,REIST_X64_PREPARED_V2_BYTES,0x5a);fill(&startup,sizeof(startup),0x5a);
            REQUIRE(!S3(IPC_DELEGATE,app_ep,(uint64_t)program>>32,3),222);
            x86os_ipc_message_t ack;zero(&ack,sizeof(ack));ack.version=1;ack.struct_size=140;ack.length=128;
            REQUIRE(!S3(IPC_RECEIVE_TIMEOUT,app_ep,&ack,1000) && ack.version==1 &&
                    ack.struct_size==140 && ack.length==16,223);
            uint64_t identity=0;
            for(unsigned n=0;n<128;n++) {
                if(n<8) identity|=(uint64_t)ack.payload[n]<<(8*n);
                else REQUIRE(ack.payload[n]==(n<16?(uint8_t)"ELF64RO!"[n-8]:0),224);
            }
            REQUIRE(identity==(uint64_t)program>>32,225);
            witness(2,fs,driver,program,0,record,workspace,round);
            reist_fs_frame frame;
            REQUIRE(!reist_fs_request_init(&frame,5,path,9,0,0),226);
            REQUIRE(!reist_fs_call(&client,&transport,&frame,500) &&
                    frame.stat.info.size>=64 && frame.stat.info.size<=1280,227);
            witness(3,fs,driver,program,0,record,workspace,round);
            if(!round && test==15) __asm__ volatile("ud2");
            if(!round && (test==16 || test==17)) {
                REQUIRE(!port_control(driver,REIST_PIO_FENCE),228);
                REQUIRE(!task_control(3,test==16?fs:driver,0),229);
            }
            x86os_ipc_message_t go={1,140,16,{0}};
            for(unsigned n=0;n<8;n++) {go.payload[n]=(uint8_t)(identity>>(8*n));go.payload[n+8]="LIVE64GO"[n];}
            REQUIRE(!S3(IPC_SEND_TIMEOUT,app_ep,&go,1000),230);
            if(!round && test==3) REQUIRE(!task_control(3,program,0),231);
            int64_t expected=!round && test==1?((1LL<<32)|134):!round && test==2?((1LL<<32)|256):
                             !round && test==3?(2LL<<32):82;
            REQUIRE(task_control(2,program,1000)==expected && task_control(2,program,1)==-10,232);
            if(previous_program) REQUIRE(task_control(2,previous_program,1)==-10,233);
            REQUIRE(!S1(IPC_CLOSE,app_ep),234);previous_program=program;
        }
        int64_t fs_status=failed_init?90:mode==1?((1LL<<32)|134):mode==3?((1LL<<32)|256):(2LL<<32);
        int64_t driver_status=mode==5?((1LL<<32)|134):mode==7?((1LL<<32)|256):(2LL<<32);
        int retired=retire(fs,driver,fs_status,driver_status);REQUIRE(!retired,retired);
        if(previous_fs) REQUIRE(task_control(2,previous_fs,1)==-10,235);
        previous_driver=driver;previous_fs=fs;
    }
    return test==4 || test==9?84:83;
}
#endif
