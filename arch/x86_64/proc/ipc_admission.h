#ifndef REIST_X64_IPC_ADMISSION_H
#define REIST_X64_IPC_ADMISSION_H
#include <stdint.h>
/* Private, serialized kernel snapshot. The adapter pins and validates the
 * requested source range before exposing its stable mapped window here.
 * The core reads only the bounded header after independent range admission.
 * -4096 means corrupt trusted metadata; all other negatives are local errno.
 * Header admission neither grants capabilities nor publishes a message. */
struct reist_x64_ipc_request {
    uint64_t operation, generation, cap_generation, rights;
    uint64_t handle, cap_handle, endpoint_handle, address, user_base;
    const unsigned char *page;
    uint64_t argument2;
    uint64_t extent;
};
_Static_assert(sizeof(struct reist_x64_ipc_request) == 96, "IPC snapshot ABI");
int64_t __attribute__((sysv_abi)) reist_x64_ipc_admit(const struct reist_x64_ipc_request *);
/* Queue bits: 1 message, 2 sender wait, 4 receiver wait, 8 closed.
 * Actions: 1 enqueue, 2 block sender, 3 deliver, 4 consume, 5 block receiver,
 * 6 close, 7 release. Invalid trusted combinations return -4096. */
int64_t __attribute__((sysv_abi)) reist_x64_ipc_plan(uint64_t operation, uint64_t bits);
#endif
