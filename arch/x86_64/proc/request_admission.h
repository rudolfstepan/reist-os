#ifndef REIST_X64_REQUEST_ADMISSION_H
#define REIST_X64_REQUEST_ADMISSION_H
#include <stdint.h>
/* Private SysV AMD64 snapshot, stable under IF=0. No user dereference:
 * page is the kernel-owned mapping of one private stack page. Endpoint bits:
 * live=1, queued=2, sender-wait=4, receiver-wait=8. This bootstrap adapter
 * does not grant authority or allocate; caller validates identity/capabilities.
 * Return 1: continue through checked pointer/backend adapter; 0: zero IO;
 * negative errno: local rejection; -4096: corrupt trusted metadata. */
struct reist_x64_request {
    uint64_t operation, arg0, arg1, arg2;
    const unsigned char *page;
    uint64_t user_base, active_child, spawned, completed, endpoint;
};
_Static_assert(sizeof(struct reist_x64_request)==80,"request descriptor");
int64_t __attribute__((sysv_abi)) reist_x64_request_admit(const struct reist_x64_request *);
#endif
