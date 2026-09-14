/* Reuse the actual FS/driver implementation and lifecycle helpers verbatim. */
#define REIST_FILE_LAUNCH 1
#include "filesystem.c"
#if PROGRAM_ID==0
#include <reist/x86_64/file_image.h>
static volatile uint64_t file_launch_record[7] __attribute__((used));
static void fill(void *p,unsigned size,unsigned char value) {
    typedef uint64_t word __attribute__((may_alias,aligned(1)));
    unsigned char *bytes=p;uint64_t v=value*0x0101010101010101ULL;
    while(size>=8) { *(volatile word *)bytes=v;bytes+=8;size-=8; }
    while(size--) *bytes++=value;
}
int main(int argc,char **argv,char **envp) {
    REQUIRE(argc==2 && !argv[2] && !envp[0] && argv[1][0]=='0',200);
    void *record=(void *)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    reist_file_image_workspace *workspace=(void *)(uintptr_t)S1(MALLOC,sizeof(*workspace));
    REQUIRE((intptr_t)record>0 && (intptr_t)workspace>0,201);
    reist_fs_transport transport={0,now,fs_send,fs_receive};
    uint64_t previous_fs=0,previous_driver=0,previous_program=0;
    for(unsigned round=0;round<2;round++) {
        mode=round?0:FILE_LAUNCH_CASE==5?1:FILE_LAUNCH_CASE==6?5:FILE_LAUNCH_CASE==7?6:FILE_LAUNCH_CASE==10?4:0;
        REQUIRE(!S1(IPC_CREATE,&driver_control) && !S1(IPC_CREATE,&control_ep),202);
        int64_t driver=create(record,2,mode|(round?16:0),driver_control);
        int64_t fs=create(record,3,mode|(round?16:0),control_ep);
        REQUIRE(driver>0 && fs>0 && (uint64_t)driver>previous_driver && (uint64_t)fs>previous_fs,203);
        REQUIRE(!port_control(driver,REIST_PIO_BIND),204);
        if(previous_driver) REQUIRE(port_control(previous_driver,REIST_PIO_FENCE)==-13,205);
        Control c={driver,fs,0,0,0,0,1,0,0};
        REQUIRE(!control_send(driver_control,&c) && !control_receive(driver_control,&c),206);
        REQUIRE(c.owner==(uint64_t)driver && c.peer==(uint64_t)fs && c.phase==2 && !c.result && c.request && c.reply,207);
        REQUIRE(c.sectors==(FILESYSTEM_LAYOUT==0?2880:FILESYSTEM_LAYOUT==1?70000:256),208);
        c.owner=fs;c.peer=driver;c.phase=3;REQUIRE(!control_send(control_ep,&c),209);
        if(mode==6) {
            REQUIRE(!control_receive(driver_control,&c) && c.owner==(uint64_t)driver && c.phase==9,210);
            __asm__ volatile("ud2");
        }
        REQUIRE(!control_receive(control_ep,&c) && c.owner==(uint64_t)fs && c.peer==(uint64_t)driver && c.phase==4,211);
        fill(record,REIST_X64_PREPARED_V2_BYTES,0xa5);fill(workspace,sizeof(*workspace),0x5a);
        int result=c.result;
        if(mode==5) REQUIRE(result<0,212);
        else {
            REQUIRE(!result,213);reist_fs_client client={0};REQUIRE(!reist_fs_client_bind(&client,fs),214);
            const char *path=FILESYSTEM_LAYOUT<2?"/BOOT.PRG":"/boot.prg";
            result=reist_x64_file_prepare_v2(record,workspace,&client,&transport,path,9,1800);
            int expected=FILE_LAUNCH_CASE==4?-22:FILE_LAUNCH_CASE==9?-27:mode==4?-71:0;
            if(mode==1) REQUIRE(result==-32 || result==-110,215);else REQUIRE(result==expected,216);
            const volatile uint8_t *p=(const void *)workspace;
            for(unsigned n=0;n<sizeof(*workspace);n++) REQUIRE(!p[n],217);
        }
        if(result) {
            const volatile uint8_t *p=record;for(unsigned n=0;n<REIST_X64_PREPARED_V2_BYTES;n++) REQUIRE(p[n]==0xa5,218);
        }
        file_launch_record[1]=fs;file_launch_record[2]=(uint64_t)(int64_t)result;
        file_launch_record[3]=(uintptr_t)record;file_launch_record[4]=(uintptr_t)workspace;
        file_launch_record[5]=driver;file_launch_record[6]=round;
        file_launch_record[0]=0x46494c4550525032ULL;
        REQUIRE(!port_control(driver,REIST_PIO_FENCE),219);
        /* Failed init replies before its natural exit90. Fence then WAIT;
         * cancelling here can replace that required exit with cancellation. */
        if(mode!=5) REQUIRE(!task_control(3,fs,0),220);
        REQUIRE(task_control(2,fs,1000)==(mode==5?90:mode==1?((1LL<<32)|134):(2LL<<32)),221);
        REQUIRE(!task_control(3,driver,0),222);
        REQUIRE(task_control(2,driver,1000)==(mode==5?((1LL<<32)|134):(2LL<<32)),223);
        REQUIRE(!port_control(driver,REIST_PIO_FENCE) && task_control(2,fs,1)==-10 && task_control(2,driver,1)==-10,224);
        REQUIRE(!S1(IPC_CLOSE,control_ep) && !S1(IPC_CLOSE,driver_control),225);
        previous_driver=driver;previous_fs=fs;
        if(result) continue;
        REQUIRE(!S1(IPC_CREATE,&control_ep),226);
        char channel[9],option[2]={(char)('0'+(!round && FILE_LAUNCH_CASE<=3?FILE_LAUNCH_CASE:0)),0};number(channel,control_ep);
        const char *args[]={"/boot.prg",channel,option};reist_task_startup_v1_t startup;
        REQUIRE(!reist_x64_startup_init(&startup,3,args),227);
        reist_task_profile_v1_t profile={1,40,{MASK,0,0},0};
        int64_t program=reist_x64_task_import_wide(record,&profile,32,&startup);
        if(FILE_LAUNCH_CASE==8 && !round) {
            REQUIRE(program==-12,228);program=reist_x64_task_import_wide(record,&profile,32,&startup);
        }
        REQUIRE(program>0 && (uint32_t)program==2 && (uint64_t)program>previous_program,229);
        fill(record,REIST_X64_PREPARED_V2_BYTES,0x5a);fill(&startup,sizeof(startup),0x5a);
        REQUIRE(!S3(IPC_DELEGATE,control_ep,(uint64_t)program>>32,1),230);
        x86os_ipc_message_t ack;zero(&ack,sizeof(ack));ack.version=1;ack.struct_size=140;ack.length=128;
        REQUIRE(!S3(IPC_RECEIVE_TIMEOUT,control_ep,&ack,1000) && ack.length==16,231);
        uint64_t identity=0;for(unsigned n=0;n<8;n++) {identity|=(uint64_t)ack.payload[n]<<(8*n);REQUIRE(ack.payload[8+n]==(uint8_t)"ELF64RO!"[n],232);}
        REQUIRE(identity==(uint64_t)program>>32,233);
        if(!round && FILE_LAUNCH_CASE==3) REQUIRE(!task_control(3,program,0),234);
        int64_t expected=!round && FILE_LAUNCH_CASE==1?((1LL<<32)|134):!round && FILE_LAUNCH_CASE==2?((1LL<<32)|256):!round && FILE_LAUNCH_CASE==3?(2LL<<32):82;
        REQUIRE(task_control(2,program,1000)==expected && task_control(2,program,1)==-10,235);
        if(previous_program) REQUIRE(task_control(2,previous_program,1)==-10,236);
        REQUIRE(!S1(IPC_CLOSE,control_ep),237);previous_program=program;
    }
    return FILE_LAUNCH_CASE==4 || FILE_LAUNCH_CASE==9?84:83;
}
#endif
