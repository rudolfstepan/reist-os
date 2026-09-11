#ifndef REIST_X64_SYSCALL_PROFILE_H
#define REIST_X64_SYSCALL_PROFILE_H
#include <stdint.h>
#include <stddef.h>
/* Private serialized SysV AMD64. Disjoint, kernel-owned descriptor,256-byte
 * task and16-byte profile. Trusted expected mask is supplied by policy.
 * 0 validate binding,1 install RESERVED,2 query RUNNING,3 revoke terminal.
 * Return0 corrupt/invalid without mutation,1 success,2 local query denial.
 * Empty revoke is idempotent only for the still-owned terminal generation.
 * No role, PID, allocation or public syscall authority in this mechanism. */
struct reist_x64_profile { uint64_t generation, mask; };
struct reist_x64_profile_binding {
    const uint64_t *task;
    struct reist_x64_profile *profile;
    uint64_t generation, mask;
};
_Static_assert(sizeof(struct reist_x64_profile)==16,"profile size");
_Static_assert(sizeof(struct reist_x64_profile_binding)==32,"binding size");
_Static_assert(offsetof(struct reist_x64_profile_binding,mask)==24,"mask offset");
uint64_t __attribute__((sysv_abi)) reist_x64_profile_apply(
    const struct reist_x64_profile_binding *, uint64_t operation, uint64_t number);
#endif
