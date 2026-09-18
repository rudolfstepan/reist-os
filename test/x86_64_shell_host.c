/* Actual normal shell/platform; only the syscall boundary is modeled. */
#ifdef NDEBUG
#error "Shell behavior tests require active assertions"
#endif
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <reist/x86_64/syscall.h>
static int64_t trap(uint64_t op,uint64_t a,uint64_t b,uint64_t c);
#define reist_x64_syscall0(n) trap(n,0,0,0)
#define reist_x64_syscall1(n,a) trap(n,a,0,0)
#define reist_x64_syscall3(n,a,b,c) trap(n,a,b,c)
#include "../userspace/sdk/lib/x86_64/console.c"
#include "../userspace/sdk/lib/x86_64/shell_platform.c"
#include "../userspace/bin/shell_vfs.c"
#define main normal_shell_main
#include "../userspace/bin/shell.c"
#undef main
static jmp_buf stopped;
static int mode,exit_code,calls,sleeps,reads,writes;
static uint64_t now;
static const char *input;
static size_t consumed,produced;
static char output[32768];
static int64_t trap(uint64_t op,uint64_t a,uint64_t b,uint64_t c) {
    assert(++calls<30000);
    switch(op) {
    case REIST_X64_SYS_EXIT:exit_code=(int)a;longjmp(stopped,1);
    case REIST_X64_SYS_MONOTONIC_MS:
        if(mode==3 && calls>8)return -5;
        if(mode==4 && calls>8)return 9;
        return (int64_t)now;
    case REIST_X64_SYS_SLEEP_MS:
        assert(a>0 && a<=10);++sleeps;
        if(mode==5)return -5;
        if(mode!=6)now+=a;
        return 0;
    case REIST_X64_SYS_READ:
        assert(a==0 && c<=1);++reads;
        if(!c)return mode==7?-13:0;
        if(mode==8)return 2;
        if(mode==9)return -5;
        if(!input[consumed])return -11;
        *(char*)(uintptr_t)b=input[consumed++];return 1;
    case REIST_X64_SYS_WRITE: {
        assert(a==1 && c>0 && c<=64);++writes;
        if(mode==10)return 0;
        if(mode==11)return -11;
        if(mode==12)return (int64_t)c+1;
        size_t n=c>17?17:(size_t)c;
        assert(produced+n<sizeof(output));
        memcpy(output+produced,(void*)(uintptr_t)b,n);produced+=n;return (int64_t)n;
    }
    default:assert(!"unadmitted native syscall");return -38;
    }
}
int main(int argc,char **argv) {
    assert(argc==2);mode=atoi(argv[1]);now=10;
    input=mode==1?"helx\bp\r\033[A\rhistory\rpwd\rexit\r":
          mode==0?"help\rpath\rhistory\runavailable\rexit\r":
          mode==17?"help\npath\nhistory\nx\nexit\n":"";
    if(mode==13) {
        unsigned char before[sizeof(x86os_file_info_t)];memset(before,0xa5,sizeof(before));
        x86os_file_info_t info;memcpy(&info,before,sizeof(info));
        assert(reist_vfs_stat("/bin/shell.prg",&info,10)==-38);
        assert(!memcmp(&info,before,sizeof(info)));
        assert(reist_vfs_readdir_at("/",0,&info,10)==-38);
        assert(!memcmp(&info,before,sizeof(info)));
        char cwd[16]="unchanged";assert(x86os_getcwd(cwd,sizeof(cwd))==-38);
        assert(!strcmp(cwd,"unchanged"));
        assert(x86os_terminal_input(REIST_TERMINAL_TRANSFER,1,1)==-95);
        assert(x86os_terminal_input(REIST_TERMINAL_CHECK,1,0)==-22);
        assert(x86os_spawnv("/bin/test.prg",0,0)==-38);
        assert(calls==0);puts("NATIVE_SHELL_HOST_OK");return 0;
    }
    if(mode==18) {
        x86os_puts("prompt>");assert(produced==0 && shell_output_used==7);
        assert(x86os_getchar_nonblocking()==0 && !strcmp(output,"prompt>") && shell_output_used==0);
        x86os_puts("line\n");assert(!strcmp(output,"prompt>line\n") && shell_output_used==0);
        char full[65];memset(full,'x',64);full[64]=0;
        x86os_puts(full);assert(produced==76 && shell_output_used==0);
        puts("NATIVE_SHELL_HOST_OK");return 0;
    }
    if(!setjmp(stopped)) {
        if(mode==14) { char huge[4097];memset(huge,'x',sizeof(huge));x86os_puts(huge);assert(0); }
        if(mode==15) { for(int i=0;i<17000;i++)x86os_putchar('x');assert(0); }
        if(mode==16) { for(int i=0;i<4100;i++){uint64_t t;x86os_monotonic_ms(&t);}assert(0); }
        char *args[]={"/bin/shell.prg",0};exit_code=normal_shell_main(1,args);
    }
    if(mode<=1 || mode==17) {
        assert(exit_code==0 && consumed==strlen(input));
        assert(strstr(output,"REIST OS userspace shell"));
        assert(strstr(output,"HELP") && strstr(output,"history"));
        if(mode!=1)assert(strstr(output,"Program lookup unavailable."));
        else assert(strstr(output,"Unable to read working directory."));
        if(mode==0)assert(writes<70); /* Was91 for the same partial-write model. */
    } else {
        assert(exit_code!=0);
        if(mode==2 || mode==6)assert(exit_code==110 && sleeps>0);
        if(mode==4)assert(exit_code==5);
        if(mode==14)assert(produced==0);
    }
    printf("NATIVE_SHELL_HOST_OK mode=%d exit=%d calls=%d sleeps=%d rx=%d tx=%d\n",mode,exit_code,calls,sleeps,reads,writes);
    return 0;
}
