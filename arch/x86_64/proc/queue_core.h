#ifndef REIST_X64_QUEUE_CORE_H
#define REIST_X64_QUEUE_CORE_H
#include <stdint.h>
#include <stddef.h>
/* Private serialized kernel interface; no user pointers or allocation.
 * FIFO entries: generation32:slot32; meta: head,tail,count.
 * Deadline entries: tick64,generation32,slot8,reserved24; meta: count.
 * apply: validate=0, insert=1, pop=2, remove-exact=3.
 * Failure returns zero without mutation; pop returns generation32:slot32.
 */
struct reist_x64_queue {
    void *entries;
    uint8_t *membership;
    uint8_t *metadata;
    uint32_t capacity;
    uint32_t kind; /* FIFO=0, deadline=1 */
};
struct reist_x64_deadline { uint64_t tick; uint32_t generation; uint8_t slot, reserved[3]; };
_Static_assert(sizeof(struct reist_x64_queue)==32, "queue descriptor ABI");
_Static_assert(offsetof(struct reist_x64_queue,capacity)==24, "queue capacity ABI");
_Static_assert(sizeof(struct reist_x64_deadline)==16, "deadline entry ABI");
uint64_t __attribute__((sysv_abi)) reist_x64_queue_apply(
    const struct reist_x64_queue *, uint64_t operation, uint64_t slot,
    uint64_t generation, uint64_t tick);
#endif
