/**
 * @file include/kernel/storage_request_pool.h
 * @brief Fester Request-Pool für begrenzte Storage-Operationen.
 *
 * Layer: Ring-0 public subsystem interface.
 * Contract: Slots folgen definierten Zuständen und bleiben generationsgebunden.
 * Safety: Keine Heap-Allokation; Erschöpfung und stale Completion werden abgewiesen.
 */
#ifndef KERNEL_STORAGE_REQUEST_POOL_H
#define KERNEL_STORAGE_REQUEST_POOL_H

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

#define STORAGE_REQUEST_VERSION 1U
#define STORAGE_REQUEST_DESCRIPTOR_V2_VERSION 2U
#define STORAGE_REQUEST_DESCRIPTOR_V3_VERSION 3U
#define STORAGE_REQUEST_INPUT_VERSION 1U
#define STORAGE_REQUEST_RECEIPT_VERSION 1U
#define STORAGE_REQUEST_POOL_CAPACITY 8U
#define STORAGE_REQUEST_BLOCK_SIZE 512U
#define STORAGE_REQUEST_MAX_PER_CLIENT 2U
#define STORAGE_REQUEST_MAX_TIMEOUT_MS 60000U
#define STORAGE_REQUEST_INVALID_HANDLE 0U
#define STORAGE_REQUEST_STATS_VERSION 1U
#define STORAGE_REQUEST_BULK_VERSION 1U
#define STORAGE_REQUEST_BULK_CAPACITY 2U
#define STORAGE_REQUEST_BULK_MAX_BYTES (128U * 1024U)

typedef uint32_t storage_request_handle_t;

typedef enum {
    STORAGE_REQUEST_BLOCK_READ = 1,
    STORAGE_REQUEST_BLOCK_WRITE = 2,
    STORAGE_REQUEST_BLOCK_FLUSH = 3,
    STORAGE_REQUEST_VFS_READ = 4,
    STORAGE_REQUEST_VFS_WRITE = 5,
    STORAGE_REQUEST_VFS_SYNC = 6,
    STORAGE_REQUEST_FORMAT_FAT12 = 7,
    STORAGE_REQUEST_FORMAT_FAT32 = 8,
    STORAGE_REQUEST_FORMAT_FAT32_SCAN = 9,
    STORAGE_REQUEST_FORMAT_FAT32_PREPARE = 10,
    STORAGE_REQUEST_CHECK_FAT12 = 11,
    STORAGE_REQUEST_REPAIR_FAT12_MIRROR = 12,
    STORAGE_REQUEST_REPAIR_FAT12_CHAINS = 13,
    STORAGE_REQUEST_REPAIR_FAT12_SHORT_FILES = 14,
    STORAGE_REQUEST_RECLAIM_FAT12_ORPHANS = 15,
    STORAGE_REQUEST_REPAIR_FAT12_LOOPS = 16,
    STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_LOOPS = 17,
    STORAGE_REQUEST_REPAIR_FAT12_SHORT_LOOPS = 18,
    STORAGE_REQUEST_REPAIR_FAT12_CROSSLINKS = 19,
    STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_SIZE = 20,
    STORAGE_REQUEST_REPAIR_FAT12_VOLUME_LABEL = 21,
    STORAGE_REQUEST_REPAIR_FAT12_ZERO_FILES = 22,
    STORAGE_REQUEST_REPAIR_FAT12_ZERO_START_FILES = 23,
    STORAGE_REQUEST_REPAIR_FAT12_DOT_SIZE = 24,
    STORAGE_REQUEST_REPAIR_FAT12_DOT_CLUSTER = 25,
    STORAGE_REQUEST_REPAIR_FAT12_REQUIRED_CROSSLINKS = 26,
    STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_CROSSLINKS = 27,
    STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_TOPOLOGY = 28,
    STORAGE_REQUEST_SALVAGE_FAT12_ORPHANS = 29,
    STORAGE_REQUEST_RECORD_FAT12_BAD_SECTOR = 30,
    STORAGE_REQUEST_VFS_SHADOW_STAT = 31,
    STORAGE_REQUEST_VFS_BULK_READ = 32,
    STORAGE_REQUEST_VFS_SYMLINK = 33,
    STORAGE_REQUEST_VFS_NAMESPACE = 34,
    STORAGE_REQUEST_VFS_OBJECT_MUTATE = 35,
} storage_request_operation_t;

#define STORAGE_REQUEST_READ STORAGE_REQUEST_BLOCK_READ
#define STORAGE_REQUEST_WRITE STORAGE_REQUEST_BLOCK_WRITE
#define STORAGE_REQUEST_FLUSH STORAGE_REQUEST_BLOCK_FLUSH

typedef struct {
    uint32_t version;
    uint32_t struct_size;
    uint32_t operation;
    uint32_t resource;
    uint32_t offset;
    uint32_t length;
    uint32_t timeout_ms;
} storage_request_submit_t;

typedef struct {
    uint32_t version;
    uint32_t struct_size;
    storage_request_handle_t handle;
    uint32_t operation;
    uint32_t resource;
    uint32_t offset;
    uint32_t length;
} storage_request_descriptor_t;

typedef struct {
    uint32_t version;
    uint32_t struct_size;
    storage_request_handle_t handle;
    uint32_t operation;
    uint32_t resource;
    uint32_t offset;
    uint32_t length;
    int32_t client_pid;
    uint32_t client_generation;
    uint32_t service_generation;
} storage_request_descriptor_v2_t;

/* v2 prefix is unchanged; the deadline is the original kernel admission time. */
typedef struct {
    uint32_t version, struct_size;
    storage_request_handle_t handle;
    uint32_t operation, resource, offset, length;
    int32_t client_pid;
    uint32_t client_generation, service_generation;
    uint64_t deadline_ms;
} storage_request_descriptor_v3_t;

typedef struct {
    uint32_t version;
    uint32_t struct_size;
    uint32_t active_requests;
    uint32_t request_high_water;
    uint32_t client_capacity_rejections;
    uint32_t pool_capacity_rejections;
} storage_request_stats_t;

typedef struct {
    uint32_t version;
    uint32_t struct_size;
    uint32_t operation;
    storage_request_handle_t handle;
    uint32_t length;
    int32_t result;
    uint32_t transferred;
    uint32_t reserved;
} storage_request_bulk_control_t;

#define STORAGE_REQUEST_BULK_PUBLISH 1U
#define STORAGE_REQUEST_BULK_COLLECT 2U
#define STORAGE_REQUEST_BULK_INPUT_VERSION 2U
#define STORAGE_REQUEST_BULK_INPUT_PUBLISH 3U
#define STORAGE_REQUEST_BULK_INPUT_TAKE 4U
#define STORAGE_REQUEST_BULK_RECEIPT_VERSION 3U
#define STORAGE_REQUEST_BULK_RECEIPT_COLLECT 5U
#define STORAGE_REQUEST_BULK_RECEIPT_ACK 6U

int storage_request_pool_init(void);
int storage_request_bind_service(int pid, uint32_t generation);
void storage_request_unbind_service(int pid, uint32_t generation);
int storage_request_submit(int client_pid, uint32_t client_generation,
                           const storage_request_submit_t *request,
                           const uint8_t *block_data, uint64_t now_ms,
                           storage_request_handle_t *handle_out);
int storage_request_claim(int service_pid, uint32_t service_generation,
                          uint64_t now_ms,
                          storage_request_descriptor_t *request_out,
                          uint8_t *block_data_out);
int storage_request_claim_v2(int service_pid, uint32_t service_generation,
                             uint64_t now_ms,
                             storage_request_descriptor_v2_t *request_out,
                             uint8_t *block_data_out);
int storage_request_claim_v3(int service_pid, uint32_t service_generation,
                             uint64_t now_ms,
                             storage_request_descriptor_v3_t *request_out,
                             uint8_t *block_data_out);
/* New input path: op35 uses offset as byte count, resource=0 and a512-byte
 * opaque control frame. No file/sector parsing in the request pool. */
int storage_request_input_publish(int client_pid, uint32_t client_generation,
    storage_request_handle_t handle, const uint8_t *data, uint32_t length,
    uint64_t now_ms);
int storage_request_input_take(int service_pid, uint32_t service_generation,
    storage_request_handle_t handle, uint8_t *data, uint32_t capacity,
    uint32_t *transferred, uint64_t now_ms);
int storage_request_mutation_context(int service_pid, uint32_t service_generation,
    storage_request_handle_t handle, uint64_t now_ms,
    storage_request_descriptor_v3_t *request_out);
/* Kernel-only effect correlation. The VFS mediator supplies a canonical
 * resource after owned-pin admission; these functions confer no device right.
 * Finish follows the guard's checked journal END, never a Ring-3 assertion alone. */
#define STORAGE_MUTATION_NO_EFFECT 1U
#define STORAGE_MUTATION_DURABLE 2U
#define STORAGE_MUTATION_UNKNOWN 3U
int storage_request_mutation_bind(int service_pid, uint32_t service_generation,
    storage_request_handle_t handle, uint32_t resource, uint64_t now_ms);
int storage_request_mutation_effect(int service_pid, uint32_t service_generation,
    storage_request_handle_t handle, uint32_t resource, uint64_t now_ms);
int storage_request_mutation_authorized(int service_pid, uint32_t service_generation,
    storage_request_handle_t handle, uint32_t resource, uint64_t now_ms);
int storage_request_mutation_finish(int service_pid, uint32_t service_generation,
    storage_request_handle_t handle, uint32_t resource, uint32_t outcome, uint64_t now_ms);
/* Sticky deny-only mask. Nonzero now also sweeps eight request deadlines. No callbacks
 * under the pool lock; the VFS consumes this before any new IO/admission. */
int storage_request_mutation_fences(uint64_t now_ms, uint32_t *mask);
/* Kernel recovery coordinator only, under the VFS repair reservation. READY
 * and CLEAR require the current bound service and no retained mutation/copy
 * for this resource. CLEAR follows verified recovery; REFENCE is deny-only
 * rollback on any subsequent publication failure. Not a userspace API. */
int storage_request_recovery_ready(int service_pid, uint32_t service_generation, uint32_t resource);
int storage_request_recovery_clear(int service_pid, uint32_t service_generation, uint32_t resource);
int storage_request_recovery_refence(uint32_t resource);
/* Copy into a kernel frame without releasing correlation. END brackets only
 * kernel copyout; a separate ACK follows client-side reply validation. Cancel,
 * lost copyout, deadline and reap fence possible effects before forgetting. */
int storage_request_mutation_reply_begin(int client_pid, uint32_t client_generation,
    storage_request_handle_t handle, uint64_t now_ms, int32_t *result, uint8_t *frame);
int storage_request_mutation_reply_end(int client_pid, uint32_t client_generation,
    storage_request_handle_t handle, bool copied, uint64_t now_ms);
int storage_request_mutation_reply_ack(int client_pid, uint32_t client_generation,
    storage_request_handle_t handle, uint64_t now_ms);
int storage_request_complete(int service_pid, uint32_t service_generation,
                             storage_request_handle_t handle, int32_t result,
                             const uint8_t *block_data);
int storage_request_completion_context(int service_pid,
                                       uint32_t service_generation,
                                       storage_request_handle_t handle,
                                       uint32_t *operation_out,
                                       uint32_t *resource_out);
int storage_request_collect(int client_pid, uint32_t client_generation,
                            storage_request_handle_t handle,
                            int32_t *result_out, uint8_t *block_data_out);
int storage_request_collect_ex(int client_pid, uint32_t client_generation,
                               storage_request_handle_t handle,
                               int32_t *result_out, uint8_t *block_data_out,
                               uint32_t *data_length_out);
int storage_request_bulk_publish(int service_pid, uint32_t service_generation,
                                 storage_request_handle_t handle,
                                 const uint8_t *data, uint32_t length);
int storage_request_bulk_collect(int client_pid, uint32_t client_generation,
                                 storage_request_handle_t handle,
                                 int32_t *result_out, uint8_t *frame_out,
                                 uint8_t *data_out, uint32_t capacity,
                                 uint32_t *transferred_out);
int storage_request_cancel(int client_pid, uint32_t client_generation,
                           storage_request_handle_t handle);
void storage_request_cancel_process(int pid, uint32_t generation);
int storage_request_stats(storage_request_stats_t *stats_out);

#ifdef REIST_HOST_TEST
int storage_request_test_corrupt_data(storage_request_handle_t handle,
                                      bool corrupt_both_copies);
int storage_request_test_corrupt_metadata(storage_request_handle_t handle,
                                          bool corrupt_both_copies);
int storage_request_test_corrupt_bulk(storage_request_handle_t handle);
void storage_request_test_set_input_hook(void (*hook)(void));
#endif

#endif
