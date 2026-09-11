#ifndef REIST_X64_CONTEXT_CORE_H
#define REIST_X64_CONTEXT_CORE_H
#include <stdint.h>
#include <stddef.h>
/* Private SysV AMD64. Kernel owns disjoint descriptor/frame/record storage.
 * Frame: R15..R8,RDI,RSI,RBP,RDX,RCX,RBX,RAX,vector,error,RIP,CS,flags,RSP,SS.
 * kind0 = normalized SYSCALL (vector256), kind1 = IRQ0 (vector32).
 * operation0 validates only, operation1 captures; returns1 or0 unchanged.
 * Mapping permission, profiles and FP ownership remain caller obligations.
 */
struct reist_x64_context {
    uint64_t *task;
    uint64_t generation, cr3, stack_low, stack_top, kind;
};
_Static_assert(sizeof(struct reist_x64_context)==48,"context descriptor");
_Static_assert(offsetof(struct reist_x64_context,kind)==40,"kind offset");
uint64_t __attribute__((sysv_abi)) reist_x64_context_apply(
    const struct reist_x64_context *, const uint64_t frame[22], uint64_t operation);
#endif
