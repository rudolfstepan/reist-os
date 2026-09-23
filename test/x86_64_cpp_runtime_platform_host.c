#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <x86os.h>
#include <reist/libc.h>
#include <reist/x86_64/cpp_runtime.h>
#include <reist/x86_64/syscall.h>
extern _Noreturn void _Exit(int);
static uint64_t stamp=100;
static unsigned calls,writes,output_size,allocation_failure,blocked;
static uintptr_t pointer=UINT64_C(0x100200000),last_free;
static char output[1024];
static reist_libc_backing_t provider;
void reist_libc_fail(unsigned code){assert(code==REIST_LIBC_FAULT_HEAP);_Exit(70);}
int reist_libc_init_backing(const reist_libc_backing_t *p){provider=*p;return 0;}
int64_t cpp_host_call(unsigned number,uint64_t a,uint64_t b,uint64_t c) {
    calls++;
    if(number==REIST_X64_SYS_MONOTONIC_MS)return (int64_t)stamp;
    if(number==REIST_X64_SYS_EXIT)_Exit((int)a);
    if(number==REIST_X64_SYS_MALLOC){assert(a&&a<=512U*1024U*1024U&&!b&&!c);return allocation_failure?-12:(int64_t)pointer;}
    if(number==REIST_X64_SYS_FREE){assert(a==pointer&&!b&&!c);last_free=(uintptr_t)a;return 0;}
    if(number==REIST_X64_SYS_REALLOC){assert(a==pointer&&b==8192&&!c);return allocation_failure?-12:(int64_t)(pointer+4096);}
    if(number==REIST_X64_SYS_SLEEP_MS){assert(a&&a<=100&&!b&&!c);stamp+=a;return 0;}
    if(number==REIST_X64_SYS_WRITE){
        assert(a==1&&b&&c&&c<=64);writes++;
        if(blocked){stamp=5100;return -11;}
        if(writes==1)return -11;
        unsigned n=writes==2?3:(unsigned)c;assert(n<=c&&output_size+n<=sizeof(output));
        memcpy(output+output_size,(void*)(uintptr_t)b,n);output_size+=n;return n;
    }
    if(number==REIST_X64_SYS_IPC_CREATE){assert(a&&!b&&!c);*(uint32_t*)(uintptr_t)a=0x100;return 0;}
    if(number==REIST_X64_SYS_IPC_CLOSE){assert(a==0x100&&!b&&!c);return 0;}
    if(number==REIST_X64_SYS_IPC_SEND_TIMEOUT||number==REIST_X64_SYS_IPC_RECEIVE_TIMEOUT){
        assert(a==0x100&&b&&c<=1000);return number==REIST_X64_SYS_IPC_SEND_TIMEOUT?0:-11;
    }
    assert(!"unexpected native runtime authority");return -38;
}
int main(int argc,char **argv) {
    (void)argv;assert(!reist_cpp_runtime_begin());assert(reist_cpp_runtime_begin()==-16);
    unsigned before=calls;
    assert(!x86os_malloc(SIZE_MAX)&&!x86os_malloc(UINT64_C(0x100000010))&&calls==before);
    assert((intptr_t)x86os_syscall(128,0,0,0)==-13&&calls==before);
    assert((intptr_t)x86os_syscall(X86OS_SYS_FREE,pointer,1,0)==-22&&calls==before);
    assert(!reist_libc_init_process(8U*1024U*1024U));
    assert(provider.struct_size==40&&provider.budget==8U*1024U*1024U&&provider.quantum==256U*1024U);
    assert((uintptr_t)provider.acquire(provider.context,4096)==pointer);
    provider.release(provider.context,(void*)pointer,4096);assert(last_free==pointer);
    assert((uintptr_t)x86os_malloc(4096)==pointer);
    assert((uintptr_t)x86os_realloc((void*)pointer,8192)==pointer+4096);
    allocation_failure=1;assert(!x86os_malloc(4096)&&!x86os_realloc((void*)pointer,8192));
    x86os_free((void*)pointer);assert(last_free==pointer);
    char data[100];memset(data,'x',sizeof(data));
    before=calls;assert(x86os_write(2,data,1)==-13&&x86os_write(1,0,1)==-90);
    assert(x86os_write(1,data,1025)==-90&&calls==before);
    if(argc==2){blocked=1;assert(x86os_write(1,data,1)==-110&&!output_size);return 0;}
    assert(x86os_write(1,data,sizeof(data))==100&&output_size==100&&writes==4&&!memcmp(data,output,100));
    uint32_t ep=0;assert(x86os_ipc_create(0)==-22&&!x86os_ipc_create(&ep)&&ep==0x100);
    x86os_ipc_message_t m={1,sizeof(m),0,{0}};
    assert(!x86os_ipc_send_timeout(ep,&m,1000)&&x86os_ipc_receive_timeout(ep,&m,0)==-11);
    assert(x86os_ipc_send_timeout(ep,&m,1001)==-22&&!x86os_ipc_close(ep));
    assert(x86os_sleep_ms(0)==-22&&x86os_sleep_ms(101)==-22&&!x86os_sleep_ms(1));
    uint64_t value=0;assert(!x86os_monotonic_ms(&value)&&value==stamp);
    stamp--;value=1234;assert(x86os_monotonic_ms(&value)==-84&&value==1234);
    before=calls;assert(!x86os_malloc(1)&&calls==before);
    return 0;
}
