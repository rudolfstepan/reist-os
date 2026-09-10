/**
 * @file userspace/storage/include/reist/vfs_file_client.h
 * @brief Fixed-capacity Ring-3 sessions over service-owned VFS objects.
 */
#ifndef REIST_VFS_FILE_CLIENT_H
#define REIST_VFS_FILE_CLIENT_H

#include <stddef.h>
#include <stdint.h>

#include "x86os.h"

#define REIST_VFS_FILE_CAPACITY 4U
#define REIST_VFS_FILE_INVALID_HANDLE 0U
#define REIST_VFS_FILE_DEFAULT_TIMEOUT_MS 1000U
#define REIST_VFS_FILE_RIGHT_READ X86OS_VFS_OBJECT_RIGHT_READ
#define REIST_VFS_FILE_RIGHT_SEEK X86OS_VFS_OBJECT_RIGHT_SEEK
#define REIST_VFS_FILE_RIGHT_STAT X86OS_VFS_OBJECT_RIGHT_STAT
#define REIST_VFS_FILE_RIGHT_DELEGATE X86OS_VFS_OBJECT_RIGHT_DELEGATE
#define REIST_VFS_FILE_RIGHT_DATA X86OS_VFS_OBJECT_RIGHT_DATA
#define REIST_VFS_FILE_RIGHT_ALL X86OS_VFS_OBJECT_RIGHT_ALL
#define REIST_VFS_SEEK_SET 0U
#define REIST_VFS_SEEK_CUR 1U
#define REIST_VFS_SEEK_END 2U

typedef uint32_t reist_vfs_file_handle_t;

/* Explicit compatibility-host API, never routed through old read-only OPEN.
 * rights uses old read bits plus REIST_VFS_WRITE_RIGHT_*; requires at least
 * one explicit mutation bit. NOFOLLOW is the only supported open flag.
 * No create, truncation-on-open, implicit grants, or Script-domain access.
 * Open/adopt must receive their first verified use within5000ms to confirm
 * handoff; otherwise the service reaps the pin of an unconfirmed reply. */
int reist_vfs_file_open_writable(const char *path, uint32_t timeout_ms,
    uint32_t rights, uint32_t open_flags, reist_vfs_file_handle_t *handle);
int reist_vfs_file_delegate_writable(reist_vfs_file_handle_t handle,
    const x86os_process_identity_t *target, uint32_t rights);
int reist_vfs_file_adopt_writable(uint32_t timeout_ms, reist_vfs_file_handle_t *handle);

/* Each step admits at most128KiB and one independently durable transaction.
 * Return is errno (0 or negative), NEVER a byte count. Inspect result even on
 * error: durable progress may precede failure. No automatic replay. UNKNOWN
 * makes this session mutation-stale until close and explicit requalification.
 * pwrite does not advance seek; write/append advance only acknowledged bytes.
 * A gap beyond EOF may report size-only durable progress with zero bytes;
 * that requires RESIZE as well as WRITE. resize_step DONE marks final size
 * AND allocation-tail completion. fsync/close never invent dirty writeback. */
int reist_vfs_file_write_step(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_write_result_t *result);
int reist_vfs_file_pwrite_step(reist_vfs_file_handle_t handle, const void *data,
    size_t length, uint64_t offset, reist_vfs_write_result_t *result);
int reist_vfs_file_append_step(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_write_result_t *result);
int reist_vfs_file_resize_step(reist_vfs_file_handle_t handle, uint64_t target,
    reist_vfs_write_result_t *result);
int reist_vfs_file_fsync(reist_vfs_file_handle_t handle, reist_vfs_write_result_t *result);

#define REIST_VFS_FILE_PROGRESS_VERSION 1U
#define REIST_VFS_FILE_PROGRESS_SIZE_KNOWN 1U
#define REIST_VFS_FILE_PROGRESS_OFFSET_KNOWN 2U
#define REIST_VFS_FILE_PROGRESS_COMPLETE 4U
/* Client-only128-byte aggregate, NOT a Storage wire reply or new capability.
 * durable_size is the LAST CONFIRMED size, not the current size after UNKNOWN.
 * durable_bytes/released_clusters survive a failed/uncertain later step.
 * first_offset describes only the first confirmed data step: separate appends
 * may interleave, so a long call is not a single atomic contiguous append.
 * last retains the single-step outcome; request0 means no suffix was submitted.
 * steps counts attempted step calls, including a locally refused last step. */
typedef struct {
    uint32_t version, struct_size;
    int32_t result;
    uint32_t outcome;
    uint64_t durable_bytes, released_clusters, first_offset, initial_size, durable_size;
    uint32_t flags, steps;
    reist_vfs_write_result_t last;
} reist_vfs_file_progress_t;
#ifdef __cplusplus
static_assert(sizeof(reist_vfs_file_progress_t) == 128U, "file progress ABI");
static_assert(offsetof(reist_vfs_file_progress_t, last) == 64U, "last step offset");
#else
_Static_assert(sizeof(reist_vfs_file_progress_t) == 128U, "file progress ABI");
_Static_assert(offsetof(reist_vfs_file_progress_t, last) == 64U, "last step offset");
#endif
/* Continue acknowledged short steps under ONE original monotonic budget,
 * min(session timeout,5000ms), including staging/transport/validation/ACK.
 * Never retry a refusal, renew a lease, reopen, or conceal partial progress.
 * All return errno; always inspect progress. A pwrite gap is explicit size
 * progress even if a later failure occurs before the first user byte.
 * These bounded adapters are not POSIX write/ftruncate compatibility wrappers. */
int reist_vfs_file_write_bounded(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_file_progress_t *progress);
int reist_vfs_file_pwrite_bounded(reist_vfs_file_handle_t handle, const void *data,
    size_t length, uint64_t offset, reist_vfs_file_progress_t *progress);
int reist_vfs_file_append_bounded(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_file_progress_t *progress);
int reist_vfs_file_resize_bounded(reist_vfs_file_handle_t handle, uint64_t target,
    reist_vfs_file_progress_t *progress);

/* The path is resolved only by open. Follow-up operations carry an owner-bound
 * service token and service generation, never path authority. Handles remain
 * process-local and are not cross-process descriptors. */

int reist_vfs_file_open(const char *path, uint32_t timeout_ms,
                        reist_vfs_file_handle_t *handle);
int reist_vfs_file_open_rights(const char *path, uint32_t timeout_ms,
                               uint32_t rights,
                               reist_vfs_file_handle_t *handle);
/** Opens a regular object with explicit rights and POSIX-shaped open flags.
 * The only currently accepted open flag is X86OS_O_NOFOLLOW. */
int reist_vfs_file_open_flags(const char *path, uint32_t timeout_ms,
                              uint32_t rights, uint32_t open_flags,
                              reist_vfs_file_handle_t *handle);
int reist_vfs_file_read(reist_vfs_file_handle_t handle, void *data,
                        size_t capacity);
int reist_vfs_file_read_bulk(reist_vfs_file_handle_t handle, void *data,
                             size_t capacity);
/** Updates only the local bound used by subsequent object requests. */
int reist_vfs_file_set_timeout(reist_vfs_file_handle_t handle,
                               uint32_t timeout_ms);
int reist_vfs_file_seek(reist_vfs_file_handle_t handle, int64_t offset,
                        uint32_t whence, uint32_t *new_offset);
int reist_vfs_file_fstat(reist_vfs_file_handle_t handle,
                         x86os_file_info_t *info);
int reist_vfs_file_rights(reist_vfs_file_handle_t handle,
                          uint32_t *rights);
int reist_vfs_file_delegate(
    reist_vfs_file_handle_t handle,
    const x86os_process_identity_t *target, uint32_t rights);
int reist_vfs_file_adopt(uint32_t timeout_ms,
                         reist_vfs_file_handle_t *handle);
int reist_vfs_file_close(reist_vfs_file_handle_t handle);

#endif
