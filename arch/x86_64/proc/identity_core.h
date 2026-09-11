#ifndef REIST_X64_IDENTITY_CORE_H
#define REIST_X64_IDENTITY_CORE_H
#include <stdint.h>
#include <stddef.h>
/* Private kernel namespace; caller serializes and owns disjoint backing arrays.
 * No allocator, profile or mapping authority is conferred by this interface.
 * 0 validate, 1 reserve (generation argument zero), 2 publish, 3 retire.
 * Reserve returns generation32:slot32; other success=1, failure=0 unchanged.
 */
struct reist_x64_identity_pool {
    uint64_t (*tasks)[32];
    uint32_t *retired;
    uint32_t capacity, last_generation;
};
enum { REIST_X64_ID_FREE=0, REIST_X64_ID_READY=1, REIST_X64_ID_RUNNING=2,
       REIST_X64_ID_FAULTED=3, REIST_X64_ID_EXITED=4, REIST_X64_ID_BLOCKED=6,
       REIST_X64_ID_ZOMBIE=8, REIST_X64_ID_RESERVED=9 };
_Static_assert(sizeof(struct reist_x64_identity_pool)==24,"pool layout");
_Static_assert(offsetof(struct reist_x64_identity_pool,last_generation)==20,"counter layout");
uint64_t __attribute__((sysv_abi)) reist_x64_identity_apply(
    struct reist_x64_identity_pool *, uint64_t operation, uint64_t slot, uint64_t generation);
#endif
