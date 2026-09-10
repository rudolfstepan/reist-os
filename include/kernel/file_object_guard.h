/* Bounded deny-only metadata; callers normalize trusted volume identities and
 * hold the VFS operation mutex before consulting legacy nodes and this guard.
 * No callback, allocation, path lookup or device I/O occurs under its lock. */
#ifndef KERNEL_FILE_OBJECT_GUARD_H
#define KERNEL_FILE_OBJECT_GUARD_H

#include "include/kernel/critical_object.h"
#include "include/reist/abi/syscall.h"

#define FILE_OBJECT_GUARD_CAPACITY 16U
#define FILE_OBJECT_GUARD_PER_CLIENT 4U
#define FILE_OBJECT_GUARD_RESOURCES 32U
#define FILE_OBJECT_GUARD_MAX_MS 5000U
#define FILE_OBJECT_GUARD_GENERATION_MAX 0x00ffffffU
#define FILE_OBJECT_GUARD_OWNED_VERSION 1U
#define FILE_OBJECT_GUARD_REPAIR_MODE 4U /* kernel-private, not an old BEGIN flag */

typedef struct {
    int32_t pid;
    uint32_t generation;
} file_object_owner_t;

/* Kernel-private storage. Zero-initialized once; init is idempotent and never
 * clears a fence or resets generations. Individual records fit 64 bytes. */
typedef struct {
    volatile uint32_t lock, poisoned;
    uint32_t initialized;
    critical_object_t control;
    critical_object_t pins[FILE_OBJECT_GUARD_CAPACITY];
    critical_object_t media[FILE_OBJECT_GUARD_RESOURCES];
} file_object_guard_t;

int file_object_guard_init(file_object_guard_t *guard);
bool file_object_guard_key_valid(const reist_file_object_key_t *key);
/* Validate a complete kernel-owned copy, never dereference a user pointer. */
bool file_object_guard_request_valid(const reist_file_object_guard_request_t *request);
bool file_object_guard_owned_valid(const reist_file_object_owned_request_t *request);
/* Correlation for END/abort, including an expired reservation. This snapshot
 * never grants IO; all device entries separately revalidate the live deadline. */
typedef struct { uint64_t deadline_ms; uint32_t request, resource, attempted, repair, pending; } file_object_mutation_context_t;
int file_object_guard_context(file_object_guard_t *guard, file_object_owner_t owner,
    uint32_t token, file_object_mutation_context_t *context);
int file_object_guard_snapshot(file_object_guard_t *guard, uint64_t *epoch,
                                uint64_t now_ms);
int file_object_guard_pin(file_object_guard_t *guard,
    const reist_file_object_key_t *key, file_object_owner_t service,
    file_object_owner_t client, uint64_t epoch, uint64_t now_ms, uint32_t *token);
int file_object_guard_verify(file_object_guard_t *guard, uint32_t token,
    file_object_owner_t service, file_object_owner_t client, uint64_t now_ms);
int file_object_guard_lookup(file_object_guard_t *guard, uint32_t token,
    file_object_owner_t service, file_object_owner_t client, uint64_t now_ms,
    reist_file_object_key_t *key);
/* Legacy VFS holds its operation mutex for the ENTIRE transaction. Advancing
 * admission before effects suffices because every Ring-3 admission also takes
 * that mutex. No extra lease or journal owner is created for this path. */
int file_object_guard_legacy_enter(file_object_guard_t *guard, uint64_t now_ms);
int file_object_guard_can_open(file_object_guard_t *guard, uint32_t resource,
                               uint64_t now_ms);
int file_object_guard_key_busy(file_object_guard_t *guard,
    const reist_file_object_key_t *key, uint64_t now_ms);
int file_object_guard_release(file_object_guard_t *guard, uint32_t token,
    file_object_owner_t service, file_object_owner_t client);
/* Exactly one or two keys, same normalized resource. For creates/recovery,
 * a valid parent/root key identifies the resource; exclusive checks all pins.
 * Legacy owners are checked by the caller under the preceding VFS mutex. */
int file_object_guard_begin(file_object_guard_t *guard,
    const reist_file_object_key_t *keys, uint32_t count, bool exclusive,
    file_object_owner_t owner, uint64_t epoch, uint64_t now_ms,
    uint64_t deadline_ms, uint32_t *token);
int file_object_guard_begin_mode(file_object_guard_t *guard,
    const reist_file_object_key_t *keys, uint32_t count, uint32_t mode,
    file_object_owner_t owner, uint64_t epoch, uint64_t now_ms,
    uint64_t deadline_ms, uint32_t *token);
/* Kernel-only admission. The mediator must first validate the claimed request,
 * exact client/service identity and its original deadline under the VFS lock.
 * Only this live pin is exempt, not another pin of the same client. */
int file_object_guard_begin_owned(file_object_guard_t *guard,
    const reist_file_object_key_t *key, uint32_t pin, uint32_t request,
    file_object_owner_t service, file_object_owner_t client, uint64_t epoch,
    uint64_t now_ms, uint64_t deadline_ms, uint32_t *token);
/* Checked correlation, not independent IO authority. Zero outputs on refusal. */
int file_object_guard_owned_request(file_object_guard_t *guard,
    file_object_owner_t service, uint32_t token, uint32_t resource,
    uint64_t now_ms, uint32_t *request, uint64_t *deadline_ms);
/* The VFS mutex orders check -> device operation -> completion. WRITE marks
 * possible effects BEFORE entering the transport. FLUSHED is kernel-only,
 * used solely after a verified successful physical flush. */
#define FILE_OBJECT_JOURNAL_CHECK 0U
#define FILE_OBJECT_JOURNAL_WRITE 1U
#define FILE_OBJECT_JOURNAL_FLUSHED 2U
#define FILE_OBJECT_JOURNAL_PROBE_VERSION 1U
/* One checked snapshot per IO boundary, not a reusable authority/cache.
 * Validates reservation, owner, resource, deadline, owned pin and media together.
 * VFS must still authorize the claimed request before marking any effect. */
int file_object_guard_journal_probe(file_object_guard_t *guard,
    file_object_owner_t owner, uint32_t token, uint32_t resource,
    uint64_t now_ms, file_object_mutation_context_t *context);
int file_object_guard_journal_io(file_object_guard_t *guard,
    file_object_owner_t owner, uint32_t token, uint32_t resource,
    uint32_t event, uint64_t now_ms, bool *was_pending);
/* Internal admission snapshot; zero outputs on refusal, no new authority. */
int file_object_guard_journal_io_deadline(file_object_guard_t *guard,
    file_object_owner_t owner, uint32_t token, uint32_t resource,
    uint32_t event, uint64_t now_ms, bool *was_pending, uint64_t *deadline_ms);
bool file_object_guard_journal_request_valid(const reist_storage_journal_request_t *request);
int file_object_guard_end(file_object_guard_t *guard, uint32_t token,
    file_object_owner_t owner, uint32_t outcome, uint64_t now_ms);
/* Per-device-effect check; the VFS mutex orders it with expiry/media revoke. */
int file_object_guard_mutation_authorized(file_object_guard_t *guard,
    file_object_owner_t owner, uint32_t resource, uint64_t now_ms);
/* Kernel-only failed-copyout rollback. The reservation was never delivered,
 * so no effect was possible. This is not an additional userspace operation. */
int file_object_guard_cancel_undelivered(file_object_guard_t *guard,
    uint32_t operation, uint32_t token, file_object_owner_t service,
    file_object_owner_t client);
int file_object_guard_cleanup(file_object_guard_t *guard, file_object_owner_t owner);
/* Fixed sweep slots 0..15 pins, 16 mutation owner. Empty returns zero owners.
 * Liveness checks happen outside the metadata lock; cleanup rechecks identity. */
int file_object_guard_owner_at(file_object_guard_t *guard, uint32_t slot,
    file_object_owner_t *service, file_object_owner_t *client);
int file_object_guard_revoke_media(file_object_guard_t *guard, uint32_t resource);
/* Deny-only transfer of kernel-recorded uncertainty. Idempotent, no regrant. */
int file_object_guard_merge_fences(file_object_guard_t *guard, uint32_t mask);
/* Kernel-only repair reservation. Caller proves the previous owner reaped,
 * immutable retained extent/media identity and bounded restart admission under
 * the VFS mutex. Ordinary pins/raw writes remain fenced. A verified finish is
 * only the FINAL publication after Ring-3 recovery/qualification and all other
 * fence layers agree; an ordinary END can never clear a repair fence. */
int file_object_guard_repair_begin(file_object_guard_t *guard, uint32_t resource,
    file_object_owner_t owner, uint64_t epoch, uint64_t now_ms,
    uint64_t deadline_ms, uint32_t *token);
int file_object_guard_repair_finish(file_object_guard_t *guard, uint32_t token,
    file_object_owner_t owner, bool verified, uint64_t now_ms);
int file_object_guard_poll(file_object_guard_t *guard, uint64_t now_ms);
/* Sticky mask, propagated to the supervisor AFTER dropping the metadata lock.
 * EBUSY is ordinary contention and leaves mask unchanged. EIO publishes the
 * all-resources fence; callers must not confuse contention with corruption. */
int file_object_guard_fenced(file_object_guard_t *guard, uint32_t *mask);
int file_object_guard_count(file_object_guard_t *guard, uint32_t resource,
                            uint32_t *count, uint64_t now_ms);
int file_object_guard_detach_ready(file_object_guard_t *guard, uint32_t resource, uint64_t now_ms);

#endif
