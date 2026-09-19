/* REIST terminal-v1 adapter; not POSIX job control. No implicit child grant. */
#ifndef REIST_X86_64_TERMINAL_H
#define REIST_X86_64_TERMINAL_H
#include <reist/x86_64/syscall.h>
static inline int reist_x64_terminal_input(uint32_t operation,int32_t pid,uint32_t generation) {
    if(operation<REIST_TERMINAL_ATTACH_CONSOLE || operation>REIST_TERMINAL_CHECK)return -22;
    if(operation==REIST_TERMINAL_TRANSFER) {
        if(pid<=0 || !generation || generation>0x7fffffffU)return -22;
    } else if(pid || generation)return -22;
    reist_terminal_input_request_t request={1,sizeof(request),operation,0,pid,generation};
    int64_t result=reist_x64_syscall1(REIST_X64_SYS_TERMINAL_INPUT,(uintptr_t)&request);
    return result<=0 && result>=-4095?(int)result:-5;
}
#endif
