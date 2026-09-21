#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define REIST_APP_HOST_TEST 1
#include "../userspace/sdk/lib/x86_64/app_file_platform.c"
#define main cat_main
#include "../userspace/programs/cat.c"
#undef main
#define main ls_main
#include "../userspace/programs/ls.c"
#undef main
#define CHECK(c) do { if(!(c)){printf("line%d: %s\n",__LINE__,#c);return 1;} }while(0)
static reist_app_snapshot snap;
static reist_app_grant server;
static reist_app_frame response;
static uint64_t host_now;
static unsigned corrupt,send_delay,calls,output_length;
static char output[32768];
int __real_main(int argc,char **argv){(void)argc;(void)argv;return 0;}
int64_t app_host_call(unsigned call,uint64_t a,uint64_t b,uint64_t c) {
    if(call==REIST_X64_SYS_MONOTONIC_MS)return host_now;
    if(call==REIST_X64_SYS_GETPID)return 10;
    if(call==REIST_X64_SYS_TERMINAL_INPUT) {
        const reist_terminal_input_request_t *t=(const void*)(uintptr_t)a;
        if(a<4096 || b || c || t->version!=1 || t->struct_size!=24 ||
           t->operation!=REIST_TERMINAL_CHECK || t->reserved || t->target_pid || t->target_generation)abort();
        return 0;
    }
    if(call==REIST_X64_SYS_SLEEP_MS){host_now+=a;return 0;}
    if(call==REIST_X64_SYS_WRITE) {
        if(a!=1 || c>64 || output_length+c>=sizeof(output))abort();
        memcpy(output+output_length,(void*)(uintptr_t)b,(size_t)c);output_length+=(unsigned)c;return (int64_t)c;
    }
    if(call==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        const x86os_ipc_bulk_message_t *m=(const void*)(uintptr_t)b;
        if(a!=17 || !c || c>1000 || m->version!=2 || m->length!=512 || m->struct_size!=sizeof(*m))abort();
        reist_app_frame q;memcpy(&q,m->payload,512);calls++;host_now+=send_delay;
        return reist_app_dispatch(&server,&snap,&q,&response,host_now);
    }
    if(call==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT) {
        x86os_ipc_bulk_message_t *m=(void*)(uintptr_t)b;
        if(a!=18 || !c || c>1000)abort();
        memset(m,0,sizeof(*m));m->version=2;m->struct_size=sizeof(*m);m->length=512;
        memcpy(m->payload,&response,512);if(corrupt)m->payload[corrupt-1]^=0x80;return 0;
    }
    abort();
}
static int reset(unsigned directory) {
    memset(&snap,0,sizeof(snap));memset(&server,0,sizeof(server));
    strcpy(snap.info.name,directory?"/":"data.txt");snap.info.type=directory?X86OS_DIRECTORY:X86OS_FILE;
    if(directory){snap.count=2;strcpy(snap.entries[0].name,"cat.prg");strcpy(snap.entries[1].name,"data.txt");
        snap.entries[0].type=snap.entries[1].type=X86OS_FILE;snap.entries[1].size=5;}
    else {snap.length=snap.info.size=5;memcpy(snap.bytes,"DATA\n",5);}
    host_now=100;send_delay=corrupt=calls=output_length=0;memset(output,0,sizeof(output));
    app_request=17;app_reply=18;app_offset=app_opened=app_closed=0;
    app_root=app_epoch=app_sequence=0;app_child=10;app_end=1100;app_previous=100;
    app_failed=app_output_used=app_output_total=app_input_total=app_operations=0;
    strcpy(app_path,directory?".":"/data.txt");
    CHECK(!reist_app_grant_init(&server,&snap,7,10,1,100));
    reist_app_frame r;CHECK(!transact(REIST_APP_HELLO,0,0,1000,&r));return 0;
}
int main(void) {
    CHECK(!reset(0));char *cat[]={"cat.prg","/data.txt",0};
    CHECK(cat_main(2,cat)==0);flush();CHECK(!strcmp(output,"DATA\n"));
    CHECK(server.phase==REIST_APP_CLOSED && app_closed && app_sequence==5);
    char data[256];CHECK(reist_vfs_file_read(0x101,data,sizeof(data))==-9);
    CHECK(reist_vfs_file_close(0x101)==-9);
    CHECK(!reset(1));char *ls[]={"ls.prg","-1",0};
    CHECK(ls_main(2,ls)==0);flush();CHECK(!strcmp(output,"cat.prg\ndata.txt\n"));
    x86os_file_info_t info,untouched;memset(&info,0xa5,sizeof(info));untouched=info;
    CHECK(reist_vfs_stat("/not-granted",&info,1000)==-13 && !memcmp(&info,&untouched,sizeof(info)));
    CHECK(reist_vfs_readdir_at("../",0,&info,1000)==-13);
    CHECK(reist_vfs_read_at("/data.txt",0,data,1,1000)==-13);
    for(unsigned i=0;i<80;i++) {
        CHECK(!reset(0));corrupt=i+1;
        memset(&info,0xa5,sizeof(info));untouched=info;
        CHECK(reist_vfs_stat("/data.txt",&info,1000)==-71 && app_failed && !memcmp(&info,&untouched,sizeof(info)));
        unsigned before=calls;CHECK(reist_vfs_stat("/data.txt",&info,1000)==-116 && calls==before);
    }
    CHECK(!reset(0));send_delay=10;
    CHECK(reist_vfs_stat("/data.txt",&info,10)==-110 && app_failed);
    CHECK(!reset(0));send_delay=0;host_now=1100;
    CHECK(reist_vfs_stat("/data.txt",&info,1000)==-110 && calls==1);
    CHECK(!reset(0));corrupt=512;
    CHECK(reist_vfs_stat("/data.txt",&info,1000)==-71);
    const char *operand=0;const char *args[]={"ls","-lap","/selected"};
    CHECK(!reist_app_operand(2,3,args,&operand) && !strcmp(operand,"/selected"));
    CHECK(reist_app_operand(1,3,args,&operand)==-22);
    CHECK(channel("@af1:00000011")==17 && !channel("@af1:0000001z"));
    CHECK(!reset(0));memset(&server,0,sizeof(server));
    CHECK(!reist_app_grant_init(&server,&snap,7,10,2,100));
    app_sequence=app_root=app_epoch=0;app_request=app_reply=0;
    char *startup[]={"cat.prg","/data.txt","@af1:00000011","@af1:00000012",0};
    CHECK(!__wrap_main(4,startup) && !startup[2] && app_closed && app_sequence==2);
    puts("APP_FILE_PLATFORM_HOST_OK");return 0;
}
