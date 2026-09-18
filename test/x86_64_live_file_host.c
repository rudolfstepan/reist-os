/* Actual application body and actual FS/block/file-image implementations.
 * Only application syscall scheduling/device boundaries are modeled here. */
#define main original_filesystem_host_main
#include "x86_64_filesystem_host.c"
#undef main
#include <reist/x86_64/file_image.h>
#include <reist/x86_64/syscall.h>

static unsigned app_fault,app_sent,app_waited,app_sleep,app_attempts;
static int64_t app0(uint64_t n) { CHECK(n==REIST_X64_SYS_GETPID);return 9; }
static int64_t app1(uint64_t n,uint64_t a) {
    if(n==REIST_SYS_TASK_CONTROL) { CHECK(!a);return app_fault==1?0:-13; }
    CHECK(n==REIST_X64_SYS_SLEEP_MS && a==10);app_sleep++;return app_fault==2?-5:0;
}
static int64_t app2(uint64_t n,uint64_t a,uint64_t b) {
    CHECK(n==REIST_SYS_DEVICE_CONTROL && a==29 && !b);return app_fault==3?0:-13;
}
static int64_t app3(uint64_t n,uint64_t channel,uint64_t ptr,uint64_t ms) {
    CHECK(channel==0x101 && ms==1000);
    x86os_ipc_message_t *m=(void *)(uintptr_t)ptr;
    CHECK(m && m->version==1 && m->struct_size==140);
    if(n==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        CHECK(!app_waited && m->length==16 && m->payload[0]==9);
        CHECK(!memcmp(m->payload+8,"ELF64RO!",8));
        for(unsigned k=1;k<8;k++) CHECK(!m->payload[k]);
        for(unsigned k=16;k<128;k++) CHECK(!m->payload[k]);
        app_attempts++;
        if(app_fault==2 || app_fault==4 || (app_fault==5 && app_attempts<20)) return -9;
        if(app_fault==6) return -32;
        app_sent++;return 0;
    }
    CHECK(n==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT && app_sent==1 && !app_waited++);
    CHECK(m->length==128);
    for(unsigned k=0;k<128;k++) CHECK(!m->payload[k]);
    if(app_fault==7) return -110;
    if(app_fault==8) return -32;
    *m=(x86os_ipc_message_t){1,140,16,{9}};memcpy(m->payload+8,"LIVE64GO",8);
    if(app_fault==9) m->version=2;
    if(app_fault==10) m->struct_size=139;
    if(app_fault==11) m->length=15;
    if(app_fault==12) m->payload[0]=8;
    if(app_fault==13) m->payload[8]^=1;
    if(app_fault>=14 && app_fault<126) m->payload[app_fault+2]=1;
    return 0;
}
#define reist_x64_syscall0 app0
#define reist_x64_syscall1 app1
#define reist_x64_syscall2 app2
#define reist_x64_syscall3 app3
#define REIST_NATIVE_LIVE_FILE 1
#define main actual_file_program
#include "../arch/x86_64/user/file_program.c"
#undef main
#undef reist_x64_syscall0
#undef reist_x64_syscall1
#undef reist_x64_syscall2
#undef reist_x64_syscall3

static int application(void) {
    char *args[]={"/boot.prg","00000101","0",NULL};char *env[]={NULL};
    for(app_fault=0;app_fault<126;app_fault++) {
        app_sent=app_waited=app_sleep=app_attempts=0;
        int result=actual_file_program(3,args,env);
        int expected=app_fault==0 || app_fault==5?82:
            app_fault==1 || app_fault==3?204:app_fault==2?205:
            app_fault==4 || app_fault==6?206:app_fault==7 || app_fault==8?208:
            app_fault<=11?209:210;
        CHECK(result==expected);
        if(!app_fault || app_fault==5) CHECK(app_sent==1 && app_waited==1);
        if(app_fault==4) CHECK(app_attempts==20 && app_sleep==20 && !app_waited);
        if(app_fault==5) CHECK(app_attempts==20 && app_sleep==19);
    }
    app_fault=0;app_sent=app_waited=app_sleep=app_attempts=0;
    CHECK(actual_file_program(2,args,env)==200 && !app_attempts);
    args[0]="/evil.prg";CHECK(actual_file_program(3,args,env)==201 && !app_attempts);
    args[0]="/boot.prg";args[1]="0000010g";
    CHECK(actual_file_program(3,args,env)==202 && !app_attempts);
    args[1]="00000000";CHECK(actual_file_program(3,args,env)==203 && !app_attempts);
    args[1]="00000101";args[2]="4";CHECK(actual_file_program(3,args,env)==203 && !app_attempts);
    return 0;
}
int main(int argc,char **argv) {
    CHECK(!application());
    CHECK(argc==4);FILE *in=fopen(argv[1],"rb");CHECK(in && !fseek(in,0,SEEK_END));
    long length=ftell(in);CHECK(length>0 && length<=70000*512);rewind(in);
    static Host h;h.media=malloc((size_t)length);CHECK(h.media && fread(h.media,1,(size_t)length,in)==(size_t)length);
    CHECK(!fclose(in));h.sectors=(unsigned)length/512;
    unsigned kind=argv[2][0]=='f'?1:2;const char *path=kind==1?"/BOOT.PRG":"/boot.prg";
    unsigned char raw[1280];in=fopen(argv[3],"rb");CHECK(in);size_t size=fread(raw,1,sizeof(raw),in);
    CHECK(size>=64 && size<=1280 && fgetc(in)==EOF && !fclose(in));
    static unsigned char output[REIST_X64_PREPARED_V2_BYTES],expected[REIST_X64_PREPARED_V2_BYTES];
    static reist_file_image_workspace workspace;
    CHECK(!reist_x64_image_prepare_v2(expected,raw,(unsigned)size));
    reist_fs_transport transport={&h,clock_ms,fs_send,fs_receive};
    for(uint64_t gen=4;gen<=6;gen+=2) {
        CHECK(!start(&h,kind,gen));reist_fs_client client={0};
        CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
        memset(output,0xa5,sizeof(output));memset(&workspace,0x5a,sizeof(workspace));
        CHECK(!reist_x64_file_prepare_v2(output,&workspace,&client,&transport,path,9,1800));
        CHECK(!memcmp(output,expected,sizeof(output)));
        for(unsigned n=0;n<sizeof(workspace);n++) CHECK(!((unsigned char *)&workspace)[n]);
        unsigned before=h.physical;
        reist_fs_frame stat;CHECK(!reist_fs_request_init(&stat,5,path,9,0,0));
        CHECK(!reist_fs_call(&client,&transport,&stat,500));
        CHECK(stat.stat.info.size==size && stat.stat.info.type==X86OS_FILE);
        CHECK(client.sequence==3+(size+255)/256 && client.sequence<=8);
        CHECK(h.physical==before && h.physical<=16);
        CHECK(!memcmp(output,expected,sizeof(output)));
    }
    free(h.media);puts("LIVE_FILE_HOST_PASS actual-app actual-FS file-capture concurrent-stat requests<=8");return 0;
}
