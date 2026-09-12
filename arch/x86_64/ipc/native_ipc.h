#ifndef REIST_NATIVE_IPC_H
#define REIST_NATIVE_IPC_H
#include <stdint.h>
#include "include/kernel/ipc.h"

/* Private SysV AMD64 binding v2. The scheduler owns the pinned request,
 * validates/copies user memory and serializes IF0. No user pointer is ever
 * dereferenced by this module. Tick units are the existing10ms native clock.
 * Bind/reap identify the exact slot+generation; GETPID uses that generation.
 * Pending requests are kernel snapshots, never suspended C stack frames. */
enum { NATIVE_IPC_BIND, NATIVE_IPC_REQUEST, NATIVE_IPC_PUMP,
       NATIVE_IPC_TAKE, NATIVE_IPC_REAP, NATIVE_IPC_END };
#define NATIVE_IPC_PENDING (-4095)
#define NATIVE_IPC_MASK ((UINT64_C(0x7f)<<49)|(UINT64_C(1)<<58))
typedef struct {
    uint64_t number, a0, a1, a2, a3;
    int64_t result;
    uint64_t deadline, ready;
    union { ipc_message_t message; ipc_bulk_message_t bulk; };
    ipc_handle_t handle;
    uint64_t copy_size; /* Admitted capacity, not the returned header size. */
} native_ipc_request_t;
_Static_assert(sizeof(native_ipc_request_t)==2136 &&
               offsetof(native_ipc_request_t,handle)==2124 &&
               offsetof(native_ipc_request_t,copy_size)==2128,"native IPC binding v2");
uint64_t reist_native_ipc(uint64_t operation, uint64_t slot,
                          uint64_t generation, uint64_t tick,
                          native_ipc_request_t *request);
#endif
