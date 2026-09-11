#ifndef REIST_X64_STARTUP_STACK_H
#define REIST_X64_STARTUP_STACK_H
#include <stdint.h>
/* Private SysV AMD64. Caller owns mapped, stable 4096-byte source/destination
 * pages disjoint from this descriptor and serializes mutation. Source offsets
 * are checked, never dereferenced as user virtual pointers. op0 validates,
 * op1 builds only after complete validation. Positive return: initial RSP;
 * -14 user range, -7 argument quota/terminator, -22 invalid kernel metadata.
 * source_base/stack_top describe page-aligned low canonical user addresses.
 * Source is not modified; destination outside the startup span is preserved. */
struct reist_x64_startup {
    const unsigned char *source;
    unsigned char *destination;
    uint64_t source_base, stack_top, argv, argc, ipc_handle;
};
_Static_assert(sizeof(struct reist_x64_startup)==56,"startup descriptor");
int64_t __attribute__((sysv_abi)) reist_x64_startup_stack(const struct reist_x64_startup *,uint64_t operation);
#endif
