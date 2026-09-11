/* Register witness only: never executes an OS syscall on the development host. */
#define REIST_X64_TEST_TRAP 1
#include <reist/x86_64/syscall.h>
#include <stdio.h>
#ifdef __cplusplus
extern "C" {
#endif
volatile uint64_t reist_sdk64_test_snapshot[7];
volatile uint64_t reist_sdk64_test_result;
__asm__(".text\n.globl reist_sdk64_test_trap\nreist_sdk64_test_trap:\n"
        "movq %rax,reist_sdk64_test_snapshot(%rip)\n"
        "movq %rdi,reist_sdk64_test_snapshot+8(%rip)\n"
        "movq %rsi,reist_sdk64_test_snapshot+16(%rip)\n"
        "movq %rdx,reist_sdk64_test_snapshot+24(%rip)\n"
        "movq %r10,reist_sdk64_test_snapshot+32(%rip)\n"
        "movq %r8,reist_sdk64_test_snapshot+40(%rip)\n"
        "movq %r9,reist_sdk64_test_snapshot+48(%rip)\n"
        "movabsq $0xabcdef9876543210,%rcx\n"
        "movabsq $0x123456789abcdef0,%r11\n"
        "cmpq %rcx,%r11\n"
        "movq reist_sdk64_test_result(%rip),%rax\nret\n");
#ifdef __cplusplus
}
#endif
static volatile uint64_t values[] = {
    UINT64_C(0x1234567887654321), UINT64_C(0x100000001),
    UINT64_C(0x7fffffffffff0000), UINT64_C(0xfedcba9876543210),
    UINT64_C(0x100000000), UINT64_C(0xfffffffffffffff3), UINT64_C(0x0123456789abcdef)
};
static int64_t invoke(unsigned argc) {
    switch(argc) {
    case 0:return reist_x64_syscall0(values[0]);
    case 1:return reist_x64_syscall1(values[0],values[1]);
    case 2:return reist_x64_syscall2(values[0],values[1],values[2]);
    case 3:return reist_x64_syscall3(values[0],values[1],values[2],values[3]);
    case 4:return reist_x64_syscall4(values[0],values[1],values[2],values[3],values[4]);
    case 5:return reist_x64_syscall5(values[0],values[1],values[2],values[3],values[4],values[5]);
    default:return reist_x64_syscall6(values[0],values[1],values[2],values[3],values[4],values[5],values[6]);
    }
}
int main(void) {
    const uint64_t results[]={42,UINT64_C(0xfffffffffffffff3),UINT64_C(0x8123456789abcdef)};
    for(unsigned run=0;run<3;++run) {
        reist_sdk64_test_result=results[run];
        for(unsigned argc=0;argc<=6;++argc) {
            for(unsigned j=0;j<7;++j)reist_sdk64_test_snapshot[j]=UINT64_MAX;
            int64_t result=invoke(argc);
            if((uint64_t)result!=results[run] || (run==1 && result!=-13))return 1;
            for(unsigned j=0;j<7;++j)
                if(reist_sdk64_test_snapshot[j]!=(j<=argc?values[j]:0))return 2;
        }
    }
    puts("X86_64_SDK_HOST_OK arities=7 results=3 full_width=1");return 0;
}
