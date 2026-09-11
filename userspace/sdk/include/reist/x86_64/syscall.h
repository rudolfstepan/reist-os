/* Native AMD64 raw syscall transport. No libc policy or implicit authority.
 * Reference and limits: docs/development/X86_64_COMPLETION_WORK_PAPER.md.
 * Guest flags: freestanding LP64, -mno-red-zone; kernel preserves all GPRs
 * except result RAX and architectural SYSCALL clobbers RCX/R11.
 */
#ifndef REIST_X86_64_SYSCALL_H
#define REIST_X86_64_SYSCALL_H
#include <stdint.h>
#include <reist/abi/syscall.h>
#if !defined(__x86_64__) || UINTPTR_MAX != UINT64_MAX
#error "REIST AMD64 transport requires native 64-bit pointers"
#endif

/* The table names operations; availability and authority remain kernel policy. */
#define REIST_X64_NUMBER(kernel_name, sdk_name, number) REIST_X64_SYS_##sdk_name = number,
enum { REIST_SYSCALL_LIST(REIST_X64_NUMBER) };
#undef REIST_X64_NUMBER

static inline int64_t reist_x64_syscall6(uint64_t number, uint64_t a1,
    uint64_t a2, uint64_t a3, uint64_t a4, uint64_t a5, uint64_t a6)
{
    register uint64_t rax __asm__("rax") = number;
    register uint64_t r10 __asm__("r10") = a4;
    register uint64_t r8 __asm__("r8") = a5;
    register uint64_t r9 __asm__("r9") = a6;
    __asm__ volatile(
#ifdef REIST_X64_TEST_TRAP
        /* Host register witness only. Never enabled in an OS build. */
        "call reist_sdk64_test_trap"
#else
        "syscall"
#endif
        : "+a"(rax)
        : "D"(a1), "S"(a2), "d"(a3), "r"(r10), "r"(r8), "r"(r9)
        : "rcx", "r11", "cc", "memory");
    return (int64_t)rax;
}

static inline int64_t reist_x64_syscall0(uint64_t number)
{
    return reist_x64_syscall6(number, 0, 0, 0, 0, 0, 0);
}

static inline int64_t reist_x64_syscall1(uint64_t number, uint64_t a1)
{
    return reist_x64_syscall6(number, a1, 0, 0, 0, 0, 0);
}

static inline int64_t reist_x64_syscall2(uint64_t number, uint64_t a1, uint64_t a2)
{
    return reist_x64_syscall6(number, a1, a2, 0, 0, 0, 0);
}

static inline int64_t reist_x64_syscall3(uint64_t number, uint64_t a1, uint64_t a2, uint64_t a3)
{
    return reist_x64_syscall6(number, a1, a2, a3, 0, 0, 0);
}

static inline int64_t reist_x64_syscall4(uint64_t number, uint64_t a1, uint64_t a2, uint64_t a3, uint64_t a4)
{
    return reist_x64_syscall6(number, a1, a2, a3, a4, 0, 0);
}

static inline int64_t reist_x64_syscall5(uint64_t number, uint64_t a1, uint64_t a2, uint64_t a3, uint64_t a4, uint64_t a5)
{
    return reist_x64_syscall6(number, a1, a2, a3, a4, a5, 0);
}

#endif
