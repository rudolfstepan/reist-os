/* Native-only append to terminal-v1; no implicit grant or legacy fallback. */
#ifndef REIST_X64_TERMINAL_SERVICE_H
#define REIST_X64_TERMINAL_SERVICE_H
#include <reist/x86_64/terminal.h>
enum { REIST_NATIVE_TERMINAL_AUTHORIZE_SERVICE=6,REIST_NATIVE_TERMINAL_REVOKE_SERVICE=7 };
static inline int reist_x64_terminal_service(unsigned operation,uint64_t target) {
    unsigned slot=(unsigned)target,generation=(unsigned)(target>>32);
    if((operation!=6&&operation!=7)||slot<2||slot>7||!generation||generation>0x7fffffff)return -22;
    reist_terminal_input_request_t q={1,24,operation,0,(int)generation,generation};
    int64_t r=reist_x64_syscall1(REIST_X64_SYS_TERMINAL_INPUT,(uintptr_t)&q);
    return r<=0&&r>=-4095?(int)r:-5;
}
#endif
