/* Qualification of console authority in the existing live service domain. */
#ifndef REIST_NATIVE_SERVICE_CONSOLE
#error Explicit service console profile required
#endif
#include <reist/x86_64/syscall.h>
#ifdef REIST_NATIVE_TERMINAL
#include <reist/x86_64/terminal.h>
#if PROGRAM_ID==0
static int terminal_target(uint64_t handle) {
    return reist_x64_terminal_input(REIST_TERMINAL_TRANSFER,(int32_t)(handle>>32),(uint32_t)(handle>>32));
}
#endif
#endif
static void service_console_probe(void) {
#if PROGRAM_ID==0
    if(reist_x64_syscall3(REIST_X64_SYS_READ,0,0,0))goto failed;
    /* One byte while live dependencies are retained. No unbounded UART wait. */
    const char byte='\n';
    for(unsigned n=0;n<10;n++) {
        int64_t r=reist_x64_syscall3(REIST_X64_SYS_WRITE,1,(uintptr_t)&byte,1);
        if(r==1)return;
        if(r!=-11 || reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))goto failed;
    }
#else
    if(reist_x64_syscall3(REIST_X64_SYS_READ,0,0,0)==-13 &&
       reist_x64_syscall3(REIST_X64_SYS_WRITE,1,0,0)==-13)return;
#endif
#if PROGRAM_ID==0
failed:
#endif
    (void)reist_x64_syscall1(REIST_X64_SYS_EXIT,250);
    __builtin_trap();
}
#define main service_console_live_main
#include "live_file.c"
#undef main
int main(int argc,char **argv,char **envp) {
    service_console_probe();
    return service_console_live_main(argc,argv,envp);
}
