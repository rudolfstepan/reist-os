/* Execute real shell/platform/FS client/file capture. Only kernel syscalls and
 * remote service responses are modeled here; media/driver behavior has its
 * own retained host suites and the mandatory integrated guest matrix. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <reist/x86_64/syscall.h>
static int64_t trap(uint64_t,uint64_t,uint64_t,uint64_t);
#define reist_x64_syscall0(n) trap(n,0,0,0)
#define reist_x64_syscall1(n,a) trap(n,a,0,0)
#define reist_x64_syscall2(n,a,b) trap(n,a,b,0)
#define reist_x64_syscall3(n,a,b,c) trap(n,a,b,c)
#define REIST_NATIVE_SHELL_SESSION 1
#define REIST_NATIVE_WIDE_FILE 1
#define REIST_NATIVE_APP_FILES 1
#include "../userspace/sdk/lib/x86_64/console.c"
#include "../userspace/sdk/lib/x86_64/shell_platform.c"
#define main native_normal_shell_main
#include "../userspace/bin/shell.c"
#undef main
static jmp_buf terminated;
static unsigned object_case,broker_steps,broker_replies,broker_closed;
static unsigned mode,calls,next_endpoint=100,driver_ep,fs_ep,leases,spawned,reaped,fences,allocations;
static unsigned next_gen=8,driver_live,fs_live,app_live,bound,foreground;
static unsigned armed,injected,canceled;
static unsigned self_identity,foreign_terminal,stale_terminal;
static unsigned service_options[32],option_count;
static unsigned directory_requests;
static unsigned oom_pauses;
static uint64_t clock_ms=100,driver_handle,fs_handle,app_handle;
static reist_session_control pending_control;
static x86os_ipc_bulk_message_t pending_fs;
static char output[32768];static unsigned output_bytes,input_bytes,exit_status;
static unsigned char program[121];
const reist_shell_images reist_native_shell_images={program,sizeof(program),program,sizeof(program)};
#define REQUIRE(x) do {if(!(x)){fprintf(stderr,"host line %d: %s\n",__LINE__,#x);exit(99);}}while(0)
static void elf_program(void) {
    memcpy(program,"\177ELF\2\1\1",7);
    uint16_t h16[]={2,62};memcpy(program+16,h16,4);
    uint32_t version=1;memcpy(program+20,&version,4);
    uint64_t entry=0x410078,phoff=64;memcpy(program+24,&entry,8);memcpy(program+32,&phoff,8);
    uint16_t sizes[]={64,56,1,0,0,0};memcpy(program+52,sizes,12);
    uint32_t type=1,flags=5;memcpy(program+64,&type,4);memcpy(program+68,&flags,4);
    uint64_t ph[]={0,0x410000,0x410000,121,121,4096};memcpy(program+72,ph,48);program[120]=0xc3;
}
static void fs_reply(x86os_ipc_bulk_message_t *out) {
    reist_fs_header h;reist_fs_frame frame;memcpy(&h,pending_fs.payload,64);memcpy(&frame,pending_fs.payload+64,512);
    REQUIRE(h.owner==fs_handle && h.flags==0 && h.sequence && h.deadline_ms>clock_ms);
    if(h.operation==7)directory_requests++;
    h.flags=1;h.status=0;h.length=512;
    const char *path=h.operation==5?frame.stat.path:h.operation==6?frame.read.path:frame.directory.path;
    int root=!strcmp(path,"/"),object=!strcmp(path,"/data.txt"),file=!strcmp(path,"/cat.prg") || !strcmp(path,"/ls.prg") || object;
    unsigned extent=object?(object_case==2?16385U:5U):(unsigned)sizeof(program);
    const unsigned char *contents=object?(const unsigned char*)"DATA\n":program;
    if(!root && !file){h.status=-2;h.length=0;}
    else if(h.operation==6) {
        unsigned offset=frame.read.offset,count=offset>=extent?0:extent-offset;
        if(count>frame.read.requested)count=frame.read.requested;
        frame.read.transferred=count;memcpy(frame.read.data,contents+(offset<extent?offset:extent),count);
    } else {
        x86os_file_info_t *info=h.operation==5?&frame.stat.info:&frame.directory.info;
        memset(info,0,sizeof(*info));
        if(h.operation==7 && frame.directory.index>=3)h.status=1;
        else {const char *names[]={"cat.prg","ls.prg","data.txt"};
            strcpy(info->name,root && h.operation==5?"/":h.operation==7?names[frame.directory.index]:object?"data.txt":"cat.prg");
            info->type=root && h.operation==5?X86OS_DIRECTORY:X86OS_FILE;info->size=info->type==X86OS_FILE?extent:0;}
    }
    memset(out,0,sizeof(*out));out->version=2;out->struct_size=sizeof(*out);out->length=h.status<0?64:576;
    memcpy(out->payload,&h,64);
    if(h.status>=0){frame.stat.result=h.status;memcpy(out->payload+64,&frame,512);}
    if(armed && mode==5 && !injected){out->payload[16]^=1;injected++;}
}
static int64_t trap(uint64_t op,uint64_t a,uint64_t b,uint64_t c) {
    REQUIRE(++calls<20000);
    switch(op) {
    case REIST_X64_SYS_GETPID:return 7;
    case REIST_X64_SYS_MONOTONIC_MS:{uint64_t now=clock_ms;if(armed && mode==14)clock_ms+=10;return (int64_t)now;}
    case REIST_X64_SYS_SLEEP_MS:
        REQUIRE(a>=1 && a<=100);clock_ms+=a;
        if(mode==16 || mode==17) {
            REQUIRE(a==100 && session_case==17 && session_service.starts==2);
            REQUIRE(driver_live && !fs_live && !bound && option_count==3 && !oom_pauses++);
            REQUIRE(clock_ms==session_service.previous_ms+100 && !session_service.deadline_ms);
            if(mode==17)return -5;
        }
        if(mode==15 && session_child) {
            REQUIRE(a==10 && app_live && !foreground && !leases);
            exit_status=134;longjmp(terminated,1); /* actual UD2 is a guest proof */
        }
        return 0;
    case REIST_X64_SYS_EXIT:exit_status=(unsigned)a;longjmp(terminated,1);
    case REIST_X64_SYS_MALLOC:REQUIRE(a<=sizeof(reist_file_image_workspace));allocations++;return (int64_t)(uintptr_t)calloc(1,(size_t)a);
    case REIST_X64_SYS_FREE:REQUIRE(a && allocations);allocations--;free((void*)(uintptr_t)a);return 0;
    case REIST_X64_SYS_READ: {
        REQUIRE(a==0 && c<=1);if(!c)return 0;
        if(mode==2)return 2;
        if(mode==1 && clock_ms<3500)return -11;
        const char *input="cat /data.txt\nls -1 /\nexit\n";
        REQUIRE(input_bytes<strlen(input));*(char*)(uintptr_t)b=input[input_bytes++];return 1;
    }
    case REIST_X64_SYS_WRITE: {
        REQUIRE(a==1 && c>0 && c<=64);unsigned n=c>7?7:(unsigned)c;
        REQUIRE(output_bytes+n<sizeof(output));memcpy(output+output_bytes,(void*)(uintptr_t)b,n);output_bytes+=n;return n;
    }
    case REIST_X64_SYS_IPC_CREATE:*(uint32_t*)(uintptr_t)a=++next_endpoint;return 0;
    case REIST_X64_SYS_IPC_CLOSE:
        if(a==session_app_request || a==session_app_reply) {
            if(!object_case)REQUIRE(!app_live && broker_replies>=3);
            broker_closed++;return 0;
        }
        REQUIRE(!driver_live && !fs_live && !bound);return 0;
    case REIST_X64_SYS_IPC_DELEGATE:
        if(a==session_app_request || a==session_app_reply) {
            REQUIRE(b==app_handle>>32 && c==(a==session_app_request?1:2));
            if(object_case==5 && c==2)return -12;
            return 0;
        }
        REQUIRE(c==3 && ((a==driver_ep && b==driver_handle>>32)||(a==fs_ep && b==fs_handle>>32)));return 0;
    case REIST_X64_SYS_TASK_CONTROL: {
        const reist_task_control_request_t *q=(const void*)(uintptr_t)a;
        if(q->operation==1) {
            const reist_task_create_v4_t *create=(const void*)q;
            const reist_task_profile_v1_t *profile=(const void*)(uintptr_t)create->profile;
            const reist_task_startup_v1_t *startup=(const void*)(uintptr_t)create->startup;
            REQUIRE(!memcmp((const void*)(uintptr_t)create->prepared,"RNPGv2",6) && create->cpu_samples==32);
            unsigned slot=q->version==6?(profile->masks[1]&(1ULL<<49)?2:3):4;
            if(slot<4){REQUIRE(option_count<32);service_options[option_count++]=(unsigned)strtoul(startup->arguments[1],0,16);}
            if(armed && (mode==9 || mode==16) && slot==3 && !injected){
                REQUIRE(oom_pauses==(mode==16));injected++;return -12;
            }
            if(mode==17 && armed && slot==3)REQUIRE(0); /* failed sleep stops before FS import */
            if(armed && mode==12 && slot==4)return INT64_MIN;
            uint64_t handle=((uint64_t)++next_gen<<32)|slot;
            if(slot==2){REQUIRE(!driver_live);driver_handle=handle;driver_live=1;driver_ep=(unsigned)strtoul(startup->arguments[0],0,16);}
            else if(slot==3){REQUIRE(!fs_live);fs_handle=handle;fs_live=1;fs_ep=(unsigned)strtoul(startup->arguments[0],0,16);}
            else {REQUIRE(!app_live && startup->argc>=4 && startup->argc<=5);
                REQUIRE(!strncmp(startup->arguments[startup->argc-2],"@af1:",5));
                REQUIRE(!(profile->masks[0]&((1ULL<<49)|(1ULL<<52)|(1ULL<<55))) && profile->masks[1]==(1ULL<<63));
                app_handle=handle;app_live=1;spawned++;broker_steps=broker_replies=0;}
            return (int64_t)handle;
        }
        REQUIRE(q->operation==2 || q->operation==3);
        if(q->target==app_handle && app_live){
            if(q->operation==3){canceled++;return 0;}
            if(armed && mode==8)return 4LL<<32;
            if(armed && mode==7 && !canceled){clock_ms+=1000;return -110;}
            if(!object_case)REQUIRE(session_app_request && session_app_reply && broker_replies>=3);
            app_live=foreground=0;reaped++;return canceled?2LL<<32:0;
        }
        REQUIRE(!bound);
        unsigned *live=q->target==driver_handle?&driver_live:q->target==fs_handle?&fs_live:0;REQUIRE(live && *live);
        if(q->operation==2){*live=0;return 2LL<<32;}return 0;
    }
    case REIST_X64_SYS_DEVICE_CONTROL: {
        REQUIRE(a==29);const reist_native_pio_request *q=(const void*)(uintptr_t)b;
        REQUIRE(q->owner==driver_handle && (q->operation==1 || q->operation==5));
        if(q->operation==1){REQUIRE(driver_live && fs_live && !bound);bound=1;}
        else {if(armed && mode==11)return -5;bound=0;fences++;}return 0;
    }
    case REIST_X64_SYS_IPC_SEND_TIMEOUT: {
        REQUIRE(c && c<=1000);const uint32_t *header=(const void*)(uintptr_t)b;
        if(header[0]==1){const x86os_ipc_message_t *m=(const void*)header;REQUIRE(m->length==48);memcpy(&pending_control,m->payload,48);}
        else if(a==session_app_reply) {
            const x86os_ipc_bulk_message_t *m=(const void*)header;reist_app_frame r;memcpy(&r,m->payload,512);
            REQUIRE(m->length==512 && r.flags==1 && r.sequence==broker_steps);
            if(r.operation==REIST_APP_READ)REQUIRE(r.length==5 && !memcmp(r.payload,"DATA\n",5));
            broker_replies++;
        } else {REQUIRE(header[0]==2 && a==fs_ep);memcpy(&pending_fs,header,sizeof(pending_fs));}
        return 0;
    }
    case REIST_X64_SYS_IPC_RECEIVE_TIMEOUT: {
        REQUIRE(c && c<=1000);uint32_t *header=(void*)(uintptr_t)b;
        if(a==session_app_request) {
            if(object_case==4){clock_ms+=c;return -110;}
            reist_app_frame q={0};q.version=1;q.size=512;q.child=app_handle>>32;q.sequence=++broker_steps;
            q.operation=broker_steps==1?REIST_APP_HELLO:broker_steps==2?REIST_APP_STAT:
                broker_steps==3?(session_app_snapshot->info.type==X86OS_FILE?REIST_APP_READ:REIST_APP_READDIR):REIST_APP_CLOSE;
            if(q.operation!=REIST_APP_HELLO){q.root=7;q.epoch=session_app_epoch;q.deadline=session_app_grant.deadline;}
            if(q.operation==REIST_APP_READ)q.requested=256;
            if(object_case==3 && broker_steps==2)q.epoch++;
            if(object_case==6 && broker_steps==3)q.offset=UINT32_MAX;
            x86os_ipc_bulk_message_t *m=(void*)header;memset(m,0,sizeof(*m));m->version=2;m->struct_size=sizeof(*m);m->length=512;memcpy(m->payload,&q,512);return 0;
        }
        if(header[0]==2){REQUIRE(a==fs_ep);fs_reply((void*)header);return 0;}
        if(armed && mode==6){clock_ms+=c;injected++;return -110;}
        reist_session_control answer=pending_control;
        if(a==driver_ep){answer.phase=2;answer.request=51;answer.reply=52;answer.sectors=2048;answer.deadline=pending_control.deadline;}
        else {REQUIRE(a==fs_ep);answer.phase=4;}
        x86os_ipc_message_t *m=(void*)header;memset(m,0,sizeof(*m));m->version=1;m->struct_size=140;m->length=48;memcpy(m->payload,&answer,48);return 0;
    }
    case REIST_X64_SYS_PROCESS_IDENTITY: {
        if(b==0 || b==7){x86os_process_identity_t identity={1,16,7,7};memcpy((void*)(uintptr_t)a,&identity,16);self_identity++;return 0;}
        if(b!=app_handle>>32 || !app_live)return b==8?-13:-3;
        x86os_process_identity_t identity={1,16,(int)b,(uint32_t)b};
        if(armed && mode==10)identity.generation++;
        memcpy((void*)(uintptr_t)a,&identity,16);return 0;
    }
    case REIST_X64_SYS_TERMINAL_INPUT: {
        const reist_terminal_input_request_t *q=(const void*)(uintptr_t)a;
        if(q->operation==REIST_TERMINAL_TRANSFER){
            if(q->target_pid==8 && q->target_generation==8){foreign_terminal++;return -13;}
            if(!app_live && q->target_pid==(int)(app_handle>>32) && q->target_generation==app_handle>>32){stale_terminal++;return -116;}
            REQUIRE(app_live && q->target_pid==(int)(app_handle>>32) && q->target_generation==app_handle>>32);foreground=1;leases++;
        }
        else REQUIRE(q->operation==REIST_TERMINAL_CHECK || q->operation==REIST_TERMINAL_ATTACH_CONSOLE);
        return 0;
    }
    default:fprintf(stderr,"unmodeled syscall %llu\n",(unsigned long long)op);exit(99);
    }
}

int __real_main(int argc,char **argv) {
    if(!object_case)return native_normal_shell_main(argc,argv);
    x86os_file_info_t info;
    REQUIRE(!reist_vfs_stat("/cat.prg",&info,1000));
    const char *args[]={"cat.prg","/data.txt"};
    if(object_case==7)clock_ms=session_observation.deadline_ms;
    int pid=x86os_spawnv("/cat.prg",2,args);
    if(object_case==2 || object_case==5 || object_case==7) {
        REQUIRE(pid==(object_case==2?-27:object_case==5?-12:-110));
        REQUIRE(!app_live && !session_app_snapshot && !session_app_request && !session_app_reply);
        return 0;
    }
    REQUIRE(pid>0);REQUIRE(!x86os_terminal_input(REIST_TERMINAL_TRANSFER,pid,(unsigned)pid));
    int status=777;int result=x86os_wait(pid,&status);
    REQUIRE(result==(object_case==4?-110:0) && !session_child && !app_live && !bound);
    REQUIRE(!session_app_snapshot && !session_app_request && !session_app_reply && canceled==1);
    REQUIRE(session_app_grant.phase==REIST_APP_CLOSED);
    return 0;
}
int main(int argc,char **argv) {
    REQUIRE(argc==2);object_case=(unsigned)atoi(argv[1]);elf_program();
    if(!setjmp(terminated)){char *args[]={"/bin/shell.prg",0};exit_status=(unsigned)__wrap_main(1,args);}
    REQUIRE(!exit_status && !allocations && !driver_live && !fs_live && !app_live && !bound);
    if(!object_case) {
        REQUIRE(spawned==2 && reaped==2 && leases==2 && broker_closed==4 && session_app_epoch==2);
        REQUIRE(strstr(output,"REIST OS userspace shell") && !strstr(output,"Bad command") && !strstr(output,"Unable"));
    }
    puts("APP_FILES_SHELL_HOST_OK");return 0;
}
