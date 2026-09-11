#ifndef REIST_X64_TASK_FRAMES_H
#define REIST_X64_TASK_FRAMES_H
#include <stdint.h>
#include <stddef.h>
/* Private System V AMD64 binding, not a userspace ABI. All record storage is
 * trusted, pinned, disjoint and serialized by the caller (current profile IF0).
 * The target cannot execute or own active CR3; revoke before calling. Only the
 * thirteen recorded private frames belong to this operation, not shared ELF
 * pages. Failure retains every unfreed record; kernel corruption stays fatal. */
typedef struct {
    uint64_t *frames, *stack, *tables, *cr3;
} ReistX64TaskFrames;
_Static_assert(sizeof(ReistX64TaskFrames)==32,"task frame binding size");
_Static_assert(offsetof(ReistX64TaskFrames,cr3)==24,"CR3 binding offset");
int __attribute__((sysv_abi)) reist_x64_task_frames_release(const ReistX64TaskFrames *binding);
#endif
