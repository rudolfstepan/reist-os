#ifndef REIST_NATIVE_IPC_PLATFORM_H
#define REIST_NATIVE_IPC_PLATFORM_H
#include "include/kernel/ipc.h"
#include "include/kernel/critical_object.h"
#include "kernel/sched/wait_queue.h"
#ifdef REIST_NATIVE_IPC_HOST_TEST
#include <string.h>
#else
#include "lib/libc/string.h"
#endif

/* Explicit architecture-owned IPC view, not the legacy process/task layout. */
typedef struct Process {
    int pid;
    uint32_t generation;
    bool is_running;
    ipc_capability_t ipc_capabilities[IPC_MAX_CAPABILITIES_PER_PROCESS];
} Process;
typedef struct { uint32_t held; } spinlock_t;
#define TASK_BLOCK_WAITING 0

_Noreturn void reist_native_ipc_fault(void);
void native_ipc_require(bool condition);
uint32_t native_ipc_lock(spinlock_t *lock);
void native_ipc_unlock(spinlock_t *lock,uint32_t flags);
uint64_t pit_monotonic_ms(void);
static inline void native_empty_queue(const wait_queue_t *q) {
    native_ipc_require(q && !q->head && !q->tail);
}
static inline bool wait_queue_wake_one_locked(wait_queue_t *q) {
    native_empty_queue(q);return false;
}
static inline size_t wait_queue_wake_all_locked(wait_queue_t *q) {
    native_empty_queue(q);return 0;
}
static inline bool scheduler_set_wait_owner_locked(int pid,uint32_t gen) {
    (void)pid;(void)gen;reist_native_ipc_fault();
}
static inline void scheduler_clear_wait_owner_locked(void) { reist_native_ipc_fault(); }
static inline int wait_queue_block_until_spinlocked(wait_queue_t *q,int kind,
        uint64_t deadline,spinlock_t *lock,uint32_t flags) {
    (void)q;(void)kind;(void)deadline;(void)lock;(void)flags;
    reist_native_ipc_fault(); /* Shared kernel-stack continuations are forbidden. */
}
#ifdef REIST_HOST_TEST
/* The common source selects this signature only in the hosted unit harness.
 * It remains unreachable there too; no fake scheduler success. */
static inline int wait_queue_block_until_locked(wait_queue_t *q,int kind,uint64_t deadline) {
    (void)q;(void)kind;(void)deadline;reist_native_ipc_fault();
}
#endif
int native_critical_init(critical_object_t *,uint32_t,const void *,size_t);
int native_critical_update(critical_object_t *,uint32_t,const void *,size_t,critical_object_validator_t);
critical_read_result_t native_critical_read(critical_object_t *,uint32_t,void *,size_t,size_t *,critical_object_validator_t);
#ifndef REIST_NATIVE_IPC_PRIMITIVES
#define critical_object_init native_critical_init
#define critical_object_update native_critical_update
#define critical_object_read native_critical_read
#endif
#endif
