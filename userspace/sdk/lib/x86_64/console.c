#include <reist/x86_64/console.h>
#include <reist/x86_64/syscall.h>
static int transfer(void *buffer,uint32_t bytes,uint32_t timeout,uint32_t *completed,int writing) {
    uintptr_t start=(uintptr_t)buffer,out=(uintptr_t)completed;
    if(!completed || bytes>REIST_X64_CONSOLE_MAX_BYTES || !timeout || timeout>1000 ||
       (bytes && !buffer) || start>UINTPTR_MAX-bytes || out>UINTPTR_MAX-sizeof(*completed) ||
       (bytes && start<out+sizeof(*completed) && out<start+bytes)) return -22;
    if(!bytes) { *completed=0;return 0; }
    int64_t stamp=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    if(stamp<0) return (int)stamp;
    uint64_t previous=(uint64_t)stamp;
    if(previous>UINT64_MAX-timeout) return -22;
    uint64_t deadline=previous+timeout;uint32_t done=0;*completed=0;
    for(unsigned attempt=0;attempt<REIST_X64_CONSOLE_ATTEMPTS;attempt++) {
        stamp=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
        if(stamp<0) return (int)stamp;
        uint64_t now=(uint64_t)stamp;
        if(now<previous) return -5;
        if(now>=deadline) return -110;
        previous=now;
        uint32_t count=bytes-done;
        if(count>REIST_X64_CONSOLE_CHUNK) count=REIST_X64_CONSOLE_CHUNK;
        int64_t result=reist_x64_syscall3(writing?REIST_X64_SYS_WRITE:REIST_X64_SYS_READ,
                                         writing?1:0,start+done,count);
        if(result>count || !result) return -5;
        if(result>0) { done+=(uint32_t)result;*completed=done;if(done==bytes) return 0; }
        else if(result!=-11) return (int)result;
        stamp=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
        if(stamp<0) return (int)stamp;
        now=(uint64_t)stamp;
        if(now<previous) return -5;
        if(now>=deadline) return -110;
        previous=now;
        uint64_t pause=deadline-now;if(pause>10) pause=10;
        result=reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,pause);
        if(result) return result<0?(int)result:-5;
    }
    return -110;
}
int reist_x64_console_read(void *buffer,uint32_t bytes,uint32_t timeout,uint32_t *completed) {
    return transfer(buffer,bytes,timeout,completed,0);
}
int reist_x64_console_write(const void *buffer,uint32_t bytes,uint32_t timeout,uint32_t *completed) {
    return transfer((void *)buffer,bytes,timeout,completed,1);
}
