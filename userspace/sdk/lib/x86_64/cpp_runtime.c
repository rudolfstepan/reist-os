/* Explicit native libc/C++ provider. Kernel profiles remain authoritative. */
#include <x86os.h>
#include <reist/libc.h>
#include <reist/x86_64/cpp_runtime.h>
#include <reist/x86_64/syscall.h>
#ifdef REIST_CPP_RUNTIME_HOST_TEST
extern int64_t cpp_host_call(unsigned,uint64_t,uint64_t,uint64_t);
#define CALL(n,a,b,c) cpp_host_call(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#else
#define CALL(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#endif
volatile uint64_t reist_cpp_runtime_selection[2]
    __attribute__((section(".data.memory_witness")))={0x3150504354525352ULL,0};
static uint64_t deadline,previous;
static unsigned operations,failed,written;
static int clock_read(uint64_t *out) {
    if(failed)return -116;
    if(++operations>4096){failed=1;return -122;}
    int64_t r=CALL(MONOTONIC_MS,0,0,0);
    if(r<0||(uint64_t)r<previous){failed=1;return -84;}
    previous=(uint64_t)r;
    if(!deadline||previous>=deadline){failed=1;return -110;}
    *out=previous;return 0;
}
int reist_cpp_runtime_begin(void) {
    if(deadline||failed)return -16;
    int64_t r=CALL(MONOTONIC_MS,0,0,0);
    if(r<0||(uint64_t)r>UINT64_MAX-5000){failed=1;return -84;}
    previous=(uint64_t)r;deadline=previous+5000;return 0;
}
void x86os_exit(int status) {(void)CALL(EXIT,status,0,0);__builtin_trap();}
uintptr_t x86os_syscall(uint32_t number,uintptr_t a,uintptr_t b,uintptr_t c) {
    if(number!=X86OS_SYS_MALLOC&&number!=X86OS_SYS_FREE&&number!=X86OS_SYS_REALLOC)return (uintptr_t)-13;
    if(c||(number!=X86OS_SYS_REALLOC&&b))return (uintptr_t)-22;
    if((number==X86OS_SYS_MALLOC&&a>REIST_LIBC_PROCESS_LIMIT)||
       (number==X86OS_SYS_REALLOC&&b>REIST_LIBC_PROCESS_LIMIT))return (uintptr_t)-12;
    uint64_t now;int r=clock_read(&now);if(r)return (uintptr_t)r;
    int64_t result=number==X86OS_SYS_MALLOC?CALL(MALLOC,a,0,0):
        number==X86OS_SYS_FREE?CALL(FREE,a,0,0):CALL(REALLOC,a,b,0);
    /* Return acquired backing even if the syscall consumed the remaining
     * time; the owner must be able to release it or undergo kernel reaping. */
    return (uintptr_t)result;
}
void *x86os_malloc(size_t size) {
    uintptr_t r=x86os_syscall(X86OS_SYS_MALLOC,size,0,0);
    return r>=(uintptr_t)-4095?0:(void*)r;
}
void *x86os_realloc(void *p,size_t size) {
    uintptr_t r=x86os_syscall(X86OS_SYS_REALLOC,(uintptr_t)p,size,0);
    return r>=(uintptr_t)-4095?0:(void*)r;
}
void x86os_free(void *p) {
    if(x86os_syscall(X86OS_SYS_FREE,(uintptr_t)p,0,0))reist_libc_fail(REIST_LIBC_FAULT_HEAP);
}
int x86os_monotonic_ms(uint64_t *out) {if(!out)return -22;return clock_read(out);}
int x86os_sleep_ms(uint32_t ms) {
    if(!ms||ms>100)return -22;uint64_t now;int r=clock_read(&now);if(r)return r;
    if(ms>deadline-now)ms=(uint32_t)(deadline-now);
    r=(int)CALL(SLEEP_MS,ms,0,0);return r?r:clock_read(&now);
}
int x86os_write(int descriptor,const void *data,size_t size) {
    if(descriptor!=1)return -13;
    if((size&&!data)||size>1024-written)return -90;
    uint64_t now;int r=clock_read(&now);if(r)return r;
    size_t done=0;
    for(unsigned turn=0;done<size&&turn<100;turn++) {
        r=clock_read(&now);if(r)return r;
        size_t n=size-done;if(n>64)n=64;
        r=(int)CALL(WRITE,1,(const unsigned char*)data+done,n);
        if(r>0&&(size_t)r<=n){done+=(unsigned)r;written+=(unsigned)r;continue;}
        if(r!=-11)return r<0?r:-5;
        r=x86os_sleep_ms(1);if(r)return r;
    }
    if(done!=size)return -110;
    r=clock_read(&now);return r?r:(int)done;
}
void x86os_putchar(char c) {if(x86os_write(1,&c,1)!=1)x86os_exit(74);}
void x86os_puts(const char *s) {
    if(!s)x86os_exit(74);unsigned n=0;while(n<=1024&&s[n])n++;
    if(n>1024||x86os_write(1,s,n)!=(int)n)x86os_exit(74);
}
void x86os_print_number(int value) {
    char buffer[11];unsigned n=0;uint32_t u=(uint32_t)value;
    if(value<0){x86os_putchar('-');u=0U-u;}
    do{buffer[n++]=(char)('0'+u%10);u/=10;}while(u);
    while(n)x86os_putchar(buffer[--n]);
}
int x86os_ipc_create(x86os_ipc_handle_t *out) {
    if(!out)return -22;uint64_t now;int r=clock_read(&now);if(r)return r;
    return (int)CALL(IPC_CREATE,out,0,0);
}
int x86os_ipc_close(x86os_ipc_handle_t ep) {
    uint64_t now;int r=clock_read(&now);return r?r:(int)CALL(IPC_CLOSE,ep,0,0);
}
static int message(unsigned send,x86os_ipc_handle_t ep,void *p,uint32_t timeout) {
    if(!p||timeout>1000)return -22;uint64_t now;int r=clock_read(&now);if(r)return r;
    if(timeout>deadline-now)timeout=(uint32_t)(deadline-now);
    return (int)(send?CALL(IPC_SEND_TIMEOUT,ep,p,timeout):CALL(IPC_RECEIVE_TIMEOUT,ep,p,timeout));
}
int x86os_ipc_send_timeout(x86os_ipc_handle_t ep,const x86os_ipc_message_t *p,uint32_t timeout) {
    return message(1,ep,(void*)p,timeout);
}
int x86os_ipc_receive_timeout(x86os_ipc_handle_t ep,x86os_ipc_message_t *p,uint32_t timeout) {
    return message(0,ep,p,timeout);
}
