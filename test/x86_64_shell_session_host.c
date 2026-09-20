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
#include "../userspace/sdk/lib/x86_64/console.c"
#include "../userspace/sdk/lib/x86_64/shell_platform.c"
#define main native_normal_shell_main
#include "../userspace/bin/shell.c"
#undef main
static jmp_buf terminated;
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
    int root=!strcmp(path,"/"),file=!strcmp(path,"/boot.prg");
    if(!root && !file){h.status=-2;h.length=0;}
    else if(h.operation==6) {
        unsigned offset=frame.read.offset,count=offset>=sizeof(program)?0:(unsigned)sizeof(program)-offset;
        if(count>frame.read.requested)count=frame.read.requested;
        frame.read.transferred=count;memcpy(frame.read.data,program+ (offset<sizeof(program)?offset:sizeof(program)),count);
    } else {
        x86os_file_info_t *info=h.operation==5?&frame.stat.info:&frame.directory.info;
        memset(info,0,sizeof(*info));
        if(h.operation==7 && frame.directory.index)h.status=1;
        else {strcpy(info->name,root && h.operation==5?"/":"boot.prg");info->type=root && h.operation==5?X86OS_DIRECTORY:X86OS_FILE;info->size=info->type==X86OS_FILE?sizeof(program):0;}
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
        const char *input="help\ncd /\npwd\nboot\nhistory\nexit\n";
        REQUIRE(input_bytes<strlen(input));*(char*)(uintptr_t)b=input[input_bytes++];return 1;
    }
    case REIST_X64_SYS_WRITE: {
        REQUIRE(a==1 && c>0 && c<=64);unsigned n=c>7?7:(unsigned)c;
        REQUIRE(output_bytes+n<sizeof(output));memcpy(output+output_bytes,(void*)(uintptr_t)b,n);output_bytes+=n;return n;
    }
    case REIST_X64_SYS_IPC_CREATE:*(uint32_t*)(uintptr_t)a=++next_endpoint;return 0;
    case REIST_X64_SYS_IPC_CLOSE:REQUIRE(!driver_live && !fs_live && !bound);return 0;
    case REIST_X64_SYS_IPC_DELEGATE:REQUIRE(c==3 && ((a==driver_ep && b==driver_handle>>32)||(a==fs_ep && b==fs_handle>>32)));return 0;
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
            else {REQUIRE(!app_live && startup->argc==1 && !strcmp(startup->arguments[0],"boot.prg"));app_handle=handle;app_live=1;spawned++;}
            return (int64_t)handle;
        }
        REQUIRE(q->operation==2 || q->operation==3);
        if(q->target==app_handle && app_live){
            if(q->operation==3){canceled++;return 0;}
            if(armed && mode==8)return 4LL<<32;
            if(armed && mode==7 && !canceled){clock_ms+=1000;return -110;}
            app_live=foreground=0;reaped++;return canceled?2LL<<32:82;
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
        else {REQUIRE(header[0]==2 && a==fs_ep);memcpy(&pending_fs,header,sizeof(pending_fs));}
        return 0;
    }
    case REIST_X64_SYS_IPC_RECEIVE_TIMEOUT: {
        REQUIRE(c && c<=1000);uint32_t *header=(void*)(uintptr_t)b;
        if(header[0]==2){REQUIRE(a==fs_ep);fs_reply((void*)header);return 0;}
        if(armed && mode==6){clock_ms+=c;injected++;return -110;}
        reist_session_control answer=pending_control;
        if(a==driver_ep){answer.phase=2;answer.request=51;answer.reply=52;answer.sectors=256;answer.deadline=clock_ms+2800;}
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
static void adapter_cases(void) {
    armed=1;
    x86os_file_info_t info,saved;memset(&info,0xa5,sizeof(info));saved=info;
    if(mode==14) {
        uint64_t deadline=clock_ms+1000;
        REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
        REQUIRE(session_observation.deadline_ms==deadline && session_observation.observed_ms<deadline);
        clock_ms=deadline;const char *args[]={"boot.prg"};
        REQUIRE(x86os_spawnv("/boot.prg",1,args)==-110 && !spawned);return;
    }
    if(mode==13) {
        REQUIRE(option_count==2 && service_options[0]==0x200 && service_options[1]==0x200);
        REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
        REQUIRE(option_count==4 && service_options[2]==0x201 && service_options[3]==0x201);
        REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
        REQUIRE(option_count==6 && service_options[4]==0x200 && service_options[5]==0x200);return;
    }
    if(mode==3) {
        char cwd[4]={'A','B','C','D'},canonical[192];
        REQUIRE(x86os_getcwd(cwd,1)==-34 && !memcmp(cwd,"ABCD",4));
        REQUIRE(reist_vfs_stat(0,&info,1000)==-22 && !memcmp(&info,&saved,sizeof(info)));
        REQUIRE(reist_vfs_stat("/",&info,1001)==-22 && !memcmp(&info,&saved,sizeof(info)));
        REQUIRE(reist_vfs_stat("/missing",&info,1000)==-2 && !memcmp(&info,&saved,sizeof(info)));
        REQUIRE(x86os_chdir("/missing")==-2 && !strcmp(session_cwd,"/"));
        REQUIRE(x86os_chdir("/boot.prg")==-20 && !strcmp(session_cwd,"/"));
        REQUIRE(session_path("\\one\\..\\..\\boot.prg",canonical)==9 && !strcmp(canonical,"/boot.prg"));
        x86os_drive_info_t drive,old;memset(&drive,0xa5,sizeof(drive));old=drive;
        REQUIRE(x86os_drive_info(1,&drive)==0 && !memcmp(&drive,&old,sizeof(drive)));
        REQUIRE(x86os_drive_info(0,&drive)==1 && drive.sectors==256 && drive.type==X86OS_DRIVE_ATA);
        REQUIRE(reist_vfs_readdir_at("/",1,&info,1000)==0 && !memcmp(&info,&saved,sizeof(info)));
        REQUIRE(reist_vfs_readdir_at("/",0,&info,1000)==1 && !strcmp(info.name,"boot.prg"));
        REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
        unsigned before=spawned;const char *args[]={"boot.prg"};
        REQUIRE(x86os_spawnv("/other.prg",1,args)==-116 && before==spawned);
        REQUIRE(x86os_spawnv("/boot.prg",0,args)==-22 && before==spawned);
        return;
    }
    if(mode==5) {
        REQUIRE(reist_vfs_stat("/boot.prg",&info,1000)==-71 && !memcmp(&info,&saved,sizeof(info)));
        REQUIRE(session_failed && session_service.phase==REIST_SESSION_COLD && !bound);
        uint64_t old=session_service.last_filesystem;
        REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
        REQUIRE(session_service.filesystem>old && session_policy.total_restarts==1 && !session_failed);
        return;
    }
    if(mode==6) {
        for(unsigned n=0;n<3;n++){
            REQUIRE(reist_vfs_stat("/boot.prg",&info,1000)==-110 && !memcmp(&info,&saved,sizeof(info)));
            REQUIRE(!bound && !driver_live && !fs_live);
        }
        REQUIRE(reist_vfs_stat("/boot.prg",&info,1000)==-11 && session_policy.degraded && session_policy.total_restarts==2);
        unsigned effects=next_gen;clock_ms+=10000;
        REQUIRE(reist_vfs_stat("/boot.prg",&info,1000)==-11 && next_gen==effects && injected==3);
        x86os_puts("DEGRADED console remains available\n");return;
    }
    if(mode==9 || mode==16) {
        REQUIRE(reist_vfs_stat("/boot.prg",&info,1000)==-12 && !memcmp(&info,&saved,sizeof(info)));
        REQUIRE(!bound && !driver_live && !fs_live && session_service.phase==REIST_SESSION_COLD);
        REQUIRE(!session_policy.total_restarts && !session_failed);
        REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
        REQUIRE(oom_pauses==(mode==16));return;
    }
    REQUIRE(!reist_vfs_stat("/boot.prg",&info,1000));
    const char *args[]={"boot.prg"};
    if(mode==4) {
        clock_ms+=1000;
        REQUIRE(x86os_spawnv("/boot.prg",1,args)==-110 && !spawned);
        REQUIRE(!session_observation.version);return;
    }
    if(mode==11){session_retire();REQUIRE(0);}
    int pid=x86os_spawnv("/boot.prg",1,args);REQUIRE(pid>0);
    x86os_process_identity_t identity,old;memset(&identity,0xa5,sizeof(identity));old=identity;
    if(mode==10) {
        REQUIRE(x86os_process_identity_of(pid,&identity)==-5 && !memcmp(&identity,&old,sizeof(identity)));
        armed=0;
    }
    REQUIRE(!x86os_process_identity_of(pid,&identity) && identity.pid==pid && identity.generation==(unsigned)pid);
    REQUIRE(!x86os_terminal_input(REIST_TERMINAL_TRANSFER,pid,identity.generation));
    int status=12345,result=x86os_wait(pid,&status);
    REQUIRE(mode!=8);
    REQUIRE(result==(mode==7?-110:0) && status==(mode==7?12345:82));
    REQUIRE(!session_child && !foreground && !bound && canceled==(mode==7));
    identity=old;REQUIRE(x86os_process_identity_of(pid,&identity)==-3 && !memcmp(&identity,&old,sizeof(identity)));
    REQUIRE(x86os_wait(pid,&status)==-3 && x86os_kill(pid)==-3);
}
int __real_main(int argc,char **argv) {
    if(mode!=2) {
        x86os_process_identity_t identity,saved;memset(&identity,0xa5,sizeof(identity));saved=identity;
        REQUIRE(x86os_process_identity_of(8,&identity)==-13 && !memcmp(&identity,&saved,sizeof(identity)));
        char cwd[192];REQUIRE(!x86os_getcwd(cwd,sizeof(cwd)) && !strcmp(cwd,"/"));
        char canonical[192];REQUIRE(session_path("/one/../boot.prg",canonical)==9 && !strcmp(canonical,"/boot.prg"));
    }
    if(mode>=3){adapter_cases();return 0;}
    return native_normal_shell_main(argc,argv);
}
int main(int argc,char **argv) {
    REQUIRE(argc==2);mode=(unsigned)atoi(argv[1]);elf_program();
    if(mode==13)reist_shell_session_selection[3]=9;
    if(mode==15)reist_shell_session_selection[3]=15;
    if(mode==16 || mode==17)reist_shell_session_selection[3]=17;
    if(!setjmp(terminated)){char *args[]={"/bin/shell.prg",0};exit_status=(unsigned)__wrap_main(1,args);}
    if(mode==15){REQUIRE(exit_status==134 && app_live && !foreground);puts("SHELL_SESSION_PLATFORM_OK owner loss after blocking child admission");return 0;}
    if(mode==17){REQUIRE(exit_status==5 && oom_pauses==1 && driver_live && !fs_live && !bound && option_count==3);puts("SHELL_SESSION_PLATFORM_OK failed OOM pause closes root");return 0;}
    if(mode==2 || mode==8 || mode==11 || mode==12){REQUIRE(exit_status==5);puts("SHELL_SESSION_PLATFORM_OK contained backend error");return 0;}
    REQUIRE(!exit_status && !allocations && !driver_live && !fs_live && !app_live && !bound);
    REQUIRE(oom_pauses==(mode==16));
    if(mode>=3){puts("SHELL_SESSION_PLATFORM_OK adapter failure/publication checks");return 0;}
    REQUIRE(spawned==1 && reaped==1 && leases==1 && fences>=2);
    REQUIRE(self_identity==1 && foreign_terminal==1 && stale_terminal==1);
    REQUIRE(directory_requests==1);
    REQUIRE(strstr(output,"REIST OS userspace shell") && strstr(output,"Built-ins:") && strstr(output,"boot"));
    REQUIRE(!strstr(output,"Bad command") && !strstr(output,"Unable to wait") && !strstr(output,"Unable to transfer"));
    if(mode==1)REQUIRE(clock_ms>=3500 && session_policy.io_anchor_ms>=3100 && session_policy.total_operations>session_policy.operations);
    puts("SHELL_SESSION_PLATFORM_OK");return 0;
}
