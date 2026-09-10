/**
 * @file kernel/init/storage_request_pool.c
 * @brief Verwaltet feste Slots für generationsgebundene Storage-Requests.
 *
 * Layer: Ring-0 storage request allocator.
 * Contract: Zustandswechsel akzeptieren nur passende Slotgenerationen.
 * Safety: Erschöpfung und stale Completion verändern keine fremden Requests.
 */
#include "include/kernel/storage_request_pool.h"

#include <stdbool.h>

#include "include/kernel/critical_object.h"
#include "lib/libc/string.h"

#ifdef REIST_HOST_TEST
static uint32_t storage_pool_lock(void) { return 0U; }
static void storage_pool_unlock(uint32_t flags) { (void)flags; }
#else
#include "arch/x86/include/interrupt.h"
#include "include/lib/spinlock.h"
static spinlock_t storage_state_lock = SPINLOCK_INIT;
static uint32_t storage_pool_lock(void) {
    return spinlock_acquire_irq(&storage_state_lock);
}
static void storage_pool_unlock(uint32_t flags) {
    spinlock_release_irq(&storage_state_lock, flags);
}
#endif

#define STORAGE_POOL_METADATA_VERSION 1U
#define STORAGE_HANDLE_SLOT_MASK 0xFFU
#define STORAGE_HANDLE_GENERATION_MAX 0x00FFFFFFU

#define STORAGE_EAGAIN (-11)
#define STORAGE_EACCES (-13)
#define STORAGE_EINVAL (-22)
#define STORAGE_ENOSPC (-28)
#define STORAGE_EINTEGRITY (-84)
#define STORAGE_EMSGSIZE (-90)
#define STORAGE_ECANCELED (-125)

typedef enum {
    STORAGE_SLOT_FREE = 0,
    STORAGE_SLOT_QUEUED = 1,
    STORAGE_SLOT_CLAIMED = 2,
    STORAGE_SLOT_COMPLETE = 3,
    STORAGE_SLOT_RETIRED = 4,
    STORAGE_SLOT_CANCEL_PENDING = 5,
    STORAGE_SLOT_INPUT_PENDING = 6,
    STORAGE_SLOT_DELIVERING = 7,
    STORAGE_SLOT_DELIVERY_CANCELLED = 8,
    STORAGE_SLOT_DELIVERED = 9,
} storage_slot_state_t;

enum { MUTATION_UNBOUND, MUTATION_BOUND, MUTATION_ATTEMPTED,
       MUTATION_FINISHED_NO_EFFECT, MUTATION_FINISHED_DURABLE, MUTATION_FINISHED_UNKNOWN };

typedef struct {
    uint32_t state;
    uint32_t generation;
    uint32_t operation;
    int32_t client_pid;
    uint32_t client_generation;
    int32_t service_pid;
    uint32_t service_generation;
    uint32_t resource;
    uint32_t offset;
    uint32_t length;
    int32_t result;
    uint64_t deadline_ms;
    uint32_t mutation_resource_plus_one, mutation_state;
} storage_slot_metadata_t;

typedef struct {
    int32_t pid;
    uint32_t generation;
} storage_service_identity_t;

typedef struct {
    uint8_t bytes[STORAGE_REQUEST_BLOCK_SIZE];
    uint32_t length;
    uint32_t crc32;
} storage_data_copy_t;

typedef struct {
    critical_object_t metadata;
    storage_data_copy_t primary;
    storage_data_copy_t shadow;
} storage_slot_t;

typedef enum {
    STORAGE_BULK_FREE = 0,
    STORAGE_BULK_RESERVED = 1,
    STORAGE_BULK_WRITING = 2,
    STORAGE_BULK_PUBLISHED = 3,
    STORAGE_BULK_READING = 4,
    STORAGE_BULK_REVOKED = 5,
    STORAGE_BULK_CONSUMED = 6,
} storage_bulk_state_t;

typedef struct {
    uint32_t state;
    storage_request_handle_t request_handle;
    uint32_t length;
    uint32_t crc32;
    uint8_t bytes[STORAGE_REQUEST_BULK_MAX_BYTES];
} storage_bulk_slot_t;

static storage_slot_t slots[STORAGE_REQUEST_POOL_CAPACITY];
static storage_bulk_slot_t bulk_slots[STORAGE_REQUEST_BULK_CAPACITY];
static critical_object_t protected_service_identity;
/* Independent checked record: the existing per-request record stays <=64.
 * This deny-only handoff cannot be cleared by completion, cancellation or bind. */
static critical_object_t protected_mutation_fences;
static bool mutation_fences_initialized;
static uint32_t mutation_poisoned;
static storage_request_stats_t request_stats;
#ifdef REIST_HOST_TEST
static void (*input_copy_hook)(void);
void storage_request_test_set_input_hook(void (*hook)(void)) { input_copy_hook = hook; }
#endif

static void increment_saturating(uint32_t *value) {
    if (*value != UINT32_MAX) ++*value;
}

static void request_added(void) {
    increment_saturating(&request_stats.active_requests);
    if (request_stats.active_requests > request_stats.request_high_water)
        request_stats.request_high_water = request_stats.active_requests;
}

static void request_removed(void) {
    if (request_stats.active_requests != 0U)
        --request_stats.active_requests;
}

_Static_assert(sizeof(storage_slot_metadata_t) <= CRITICAL_OBJECT_MAX_PAYLOAD,
               "storage request metadata exceeds protected payload");
_Static_assert(sizeof(storage_service_identity_t) <=
                   CRITICAL_OBJECT_MAX_PAYLOAD,
               "storage service identity exceeds protected payload");
_Static_assert(sizeof(storage_request_stats_t) == 6U * sizeof(uint32_t),
               "storage request stats ABI drift");
_Static_assert(sizeof(storage_request_descriptor_v3_t) == 48U, "descriptor v3 ABI");
_Static_assert(offsetof(storage_request_descriptor_v3_t, deadline_ms) == 40U, "v3 prefix");

static uint32_t crc32_bytes(const uint8_t *data, size_t length) {
    uint32_t crc = 0xFFFFFFFFU;
    for (size_t index = 0U; index < length; ++index) {
        crc ^= data[index];
        for (uint32_t bit = 0U; bit < 8U; ++bit)
            crc = (crc >> 1U) ^ (0xEDB88320U &
                  (uint32_t)-(int32_t)(crc & 1U));
    }
    return crc ^ 0xFFFFFFFFU;
}

static bool metadata_valid(const void *payload, size_t length) {
    if (payload == NULL || length != sizeof(storage_slot_metadata_t))
        return false;
    const storage_slot_metadata_t *value = payload;
    if (value->state > STORAGE_SLOT_DELIVERED ||
        value->generation > STORAGE_HANDLE_GENERATION_MAX ||
        value->length > STORAGE_REQUEST_BLOCK_SIZE) return false;
    if (value->mutation_state > MUTATION_FINISHED_UNKNOWN ||
        value->mutation_resource_plus_one > 32U ||
        (!!value->mutation_state != !!value->mutation_resource_plus_one)) return false;
    if (value->mutation_state && (value->operation != STORAGE_REQUEST_VFS_OBJECT_MUTATE ||
        value->service_pid <= 0 || !value->service_generation ||
        value->state == STORAGE_SLOT_QUEUED || value->state == STORAGE_SLOT_INPUT_PENDING)) return false;
    if (value->state >= STORAGE_SLOT_DELIVERING && value->operation != STORAGE_REQUEST_VFS_OBJECT_MUTATE)
        return false;
    if (value->state == STORAGE_SLOT_FREE ||
        value->state == STORAGE_SLOT_RETIRED)
        return value->operation == 0U && value->client_pid == 0 &&
               value->client_generation == 0U && value->service_pid == 0 &&
               value->service_generation == 0U && value->resource == 0U &&
               value->offset == 0U &&
               value->length == 0U && value->result == 0 &&
               value->deadline_ms == 0U && !value->mutation_state;
    if (value->generation == 0U || value->client_pid <= 0 ||
        value->client_generation == 0U ||
        value->deadline_ms == 0U ||
        value->operation < STORAGE_REQUEST_READ ||
        value->operation > STORAGE_REQUEST_VFS_OBJECT_MUTATE)
        return false;
    if ((value->state == STORAGE_SLOT_QUEUED || value->state == STORAGE_SLOT_INPUT_PENDING) &&
        (value->service_pid != 0 || value->service_generation != 0U))
        return false;
    if (value->state == STORAGE_SLOT_INPUT_PENDING &&
        (value->operation != STORAGE_REQUEST_VFS_OBJECT_MUTATE || !value->offset)) return false;
    if (value->operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE &&
        (value->resource || value->length != STORAGE_REQUEST_BLOCK_SIZE ||
         value->offset > STORAGE_REQUEST_BULK_MAX_BYTES)) return false;
    if ((value->state == STORAGE_SLOT_CLAIMED ||
         value->state == STORAGE_SLOT_CANCEL_PENDING) &&
        (value->service_pid <= 0 || value->service_generation == 0U))
        return false;
    if (value->state == STORAGE_SLOT_COMPLETE &&
        !((value->service_pid == 0 && value->service_generation == 0U) ||
          (value->service_pid > 0 && value->service_generation != 0U)))
        return false;
    if (value->operation == STORAGE_REQUEST_BLOCK_FLUSH ||
        value->operation == STORAGE_REQUEST_VFS_SYNC ||
        value->operation == STORAGE_REQUEST_FORMAT_FAT12 ||
        value->operation == STORAGE_REQUEST_FORMAT_FAT32 ||
        value->operation == STORAGE_REQUEST_FORMAT_FAT32_SCAN ||
        value->operation == STORAGE_REQUEST_FORMAT_FAT32_PREPARE ||
        value->operation == STORAGE_REQUEST_CHECK_FAT12 ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_MIRROR ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_CHAINS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_SHORT_FILES ||
        value->operation == STORAGE_REQUEST_RECLAIM_FAT12_ORPHANS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_LOOPS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_LOOPS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_SHORT_LOOPS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_CROSSLINKS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_SIZE ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_VOLUME_LABEL ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_ZERO_FILES ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_ZERO_START_FILES ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_DOT_SIZE ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_DOT_CLUSTER ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_REQUIRED_CROSSLINKS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_CROSSLINKS ||
        value->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_TOPOLOGY ||
        value->operation == STORAGE_REQUEST_SALVAGE_FAT12_ORPHANS ||
        value->operation == STORAGE_REQUEST_RECORD_FAT12_BAD_SECTOR)
        return value->length == 0U;
    if (value->operation == STORAGE_REQUEST_BLOCK_READ ||
        value->operation == STORAGE_REQUEST_BLOCK_WRITE)
        return value->length == STORAGE_REQUEST_BLOCK_SIZE;
    return value->length != 0U && value->length <= STORAGE_REQUEST_BLOCK_SIZE;
}

static uint64_t deadline_after(uint64_t now_ms, uint32_t timeout_ms) {
    return UINT64_MAX - now_ms < timeout_ms
        ? UINT64_MAX : now_ms + timeout_ms;
}

static bool operation_has_input(uint32_t operation) {
    return operation == STORAGE_REQUEST_BLOCK_WRITE ||
           operation == STORAGE_REQUEST_VFS_WRITE ||
           operation == STORAGE_REQUEST_VFS_SHADOW_STAT ||
           operation == STORAGE_REQUEST_VFS_BULK_READ ||
           operation == STORAGE_REQUEST_VFS_SYMLINK ||
           operation == STORAGE_REQUEST_VFS_NAMESPACE ||
           operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE;
}

static bool operation_has_output(uint32_t operation) {
    return operation == STORAGE_REQUEST_BLOCK_READ ||
           operation == STORAGE_REQUEST_VFS_READ ||
           operation == STORAGE_REQUEST_VFS_SHADOW_STAT ||
           operation == STORAGE_REQUEST_VFS_BULK_READ ||
           operation == STORAGE_REQUEST_VFS_SYMLINK ||
           operation == STORAGE_REQUEST_VFS_NAMESPACE ||
           operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE;
}

static bool identity_valid(const void *payload, size_t length) {
    if (payload == NULL || length != sizeof(storage_service_identity_t))
        return false;
    const storage_service_identity_t *identity = payload;
    return (identity->pid == 0 && identity->generation == 0U) ||
           (identity->pid > 0 && identity->generation != 0U);
}

static int load_metadata(size_t slot, storage_slot_metadata_t *value) {
    size_t length = 0U;
    int result = critical_object_read(&slots[slot].metadata,
        STORAGE_POOL_METADATA_VERSION, value, sizeof(*value), &length,
        metadata_valid) < 0 || length != sizeof(*value)
        ? STORAGE_EINTEGRITY : 0;
    if (result) mutation_poisoned = UINT32_MAX;
    return result;
}

static int store_metadata(size_t slot, const storage_slot_metadata_t *value) {
    int result = critical_object_update(&slots[slot].metadata,
        STORAGE_POOL_METADATA_VERSION, value, sizeof(*value), metadata_valid)
        == 0 ? 0 : STORAGE_EINTEGRITY;
    if (result) mutation_poisoned = UINT32_MAX;
    return result;
}

static bool mutation_fences_valid(const void *payload, size_t length) {
    return payload && length == sizeof(uint32_t);
}

static int mutation_fences_read(uint32_t *mask) {
    *mask = 0;
    if (mutation_poisoned) { *mask = UINT32_MAX; return STORAGE_EINTEGRITY; }
    if (!mutation_fences_initialized) return 0; /* VFS boot before pool init. */
    size_t length = 0;
    if (protected_mutation_fences.publication_lock || critical_object_read(
        &protected_mutation_fences, STORAGE_POOL_METADATA_VERSION, mask, sizeof(*mask),
        &length, mutation_fences_valid) < 0 || length != sizeof(*mask)) {
        mutation_poisoned = *mask = UINT32_MAX;
        return STORAGE_EINTEGRITY;
    }
    return 0;
}

static int mutation_fence_lost(const storage_slot_metadata_t *metadata) {
    if (metadata->mutation_state != MUTATION_ATTEMPTED &&
        metadata->mutation_state != MUTATION_FINISHED_DURABLE &&
        metadata->mutation_state != MUTATION_FINISHED_UNKNOWN) return 0;
    uint32_t mask;
    int result = mutation_fences_read(&mask);
    if (result) return result;
    uint32_t bit = 1U << (metadata->mutation_resource_plus_one - 1U);
    if (mask & bit) return 0;
    mask |= bit;
    if (!mutation_fences_initialized || protected_mutation_fences.publication_lock ||
        critical_object_update(&protected_mutation_fences, STORAGE_POOL_METADATA_VERSION,
            &mask, sizeof(mask), mutation_fences_valid) != 0) {
        mutation_poisoned = UINT32_MAX;
        return STORAGE_EINTEGRITY;
    }
    return 0;
}

static int load_identity(storage_service_identity_t *identity) {
    size_t length = 0U;
    return critical_object_read(&protected_service_identity,
        STORAGE_POOL_METADATA_VERSION, identity, sizeof(*identity), &length,
        identity_valid) < 0 || length != sizeof(*identity)
        ? STORAGE_EINTEGRITY : 0;
}

static int store_identity(const storage_service_identity_t *identity) {
    return critical_object_update(&protected_service_identity,
        STORAGE_POOL_METADATA_VERSION, identity, sizeof(*identity),
        identity_valid) == 0 ? 0 : STORAGE_EINTEGRITY;
}

static void clear_data(size_t slot) {
    memset(&slots[slot].primary, 0, sizeof(slots[slot].primary));
    memset(&slots[slot].shadow, 0, sizeof(slots[slot].shadow));
}

static void store_data(size_t slot, const uint8_t *data, uint32_t length) {
    clear_data(slot);
    if (length != 0U) memcpy(slots[slot].primary.bytes, data, length);
    slots[slot].primary.length = length;
    slots[slot].primary.crc32 = crc32_bytes(slots[slot].primary.bytes, length);
    slots[slot].shadow = slots[slot].primary;
}

static int load_data(size_t slot, uint8_t *data, uint32_t expected_length) {
    storage_data_copy_t *primary = &slots[slot].primary;
    storage_data_copy_t *shadow = &slots[slot].shadow;
    bool primary_valid = primary->length == expected_length &&
        primary->crc32 == crc32_bytes(primary->bytes, primary->length);
    bool shadow_valid = shadow->length == expected_length &&
        shadow->crc32 == crc32_bytes(shadow->bytes, shadow->length);
    if (!primary_valid && !shadow_valid) return STORAGE_EINTEGRITY;
    storage_data_copy_t *source = primary_valid ? primary : shadow;
    if (!primary_valid) *primary = *shadow;
    if (!shadow_valid) *shadow = *primary;
    if (expected_length != 0U && data != NULL)
        memcpy(data, source->bytes, expected_length);
    return 0;
}

static storage_request_handle_t make_handle(size_t slot, uint32_t generation) {
    return (generation << 8U) | (uint32_t)(slot + 1U);
}

static storage_bulk_slot_t *bulk_find(storage_request_handle_t handle) {
    for (size_t slot = 0U; slot < STORAGE_REQUEST_BULK_CAPACITY; ++slot)
        if (bulk_slots[slot].state != STORAGE_BULK_FREE &&
            bulk_slots[slot].request_handle == handle) return &bulk_slots[slot];
    return NULL;
}

static storage_bulk_slot_t *bulk_reserve(storage_request_handle_t handle) {
    for (size_t slot = 0U; slot < STORAGE_REQUEST_BULK_CAPACITY; ++slot) {
        if (bulk_slots[slot].state != STORAGE_BULK_FREE) continue;
        bulk_slots[slot].state = STORAGE_BULK_RESERVED;
        bulk_slots[slot].request_handle = handle;
        bulk_slots[slot].length = 0U;
        bulk_slots[slot].crc32 = 0U;
        return &bulk_slots[slot];
    }
    return NULL;
}

static void bulk_release(storage_request_handle_t handle) {
    storage_bulk_slot_t *bulk = bulk_find(handle);
    if (bulk == NULL) return;
    if (bulk->state == STORAGE_BULK_WRITING ||
        bulk->state == STORAGE_BULK_READING || bulk->state == STORAGE_BULK_REVOKED) {
        bulk->state = STORAGE_BULK_REVOKED;
        return;
    }
    bulk->state = STORAGE_BULK_FREE;
    bulk->request_handle = 0U;
    bulk->length = 0U;
    bulk->crc32 = 0U;
}

static void bulk_clear(storage_bulk_slot_t *bulk) {
    if (bulk == NULL) return;
    bulk->state = STORAGE_BULK_FREE;
    bulk->request_handle = 0U;
    bulk->length = 0U;
    bulk->crc32 = 0U;
}

static int resolve_handle(storage_request_handle_t handle, size_t *slot_out,
                          storage_slot_metadata_t *metadata) {
    uint32_t encoded_slot = handle & STORAGE_HANDLE_SLOT_MASK;
    uint32_t generation = handle >> 8U;
    if (encoded_slot == 0U || encoded_slot > STORAGE_REQUEST_POOL_CAPACITY ||
        generation == 0U) return STORAGE_EINVAL;
    size_t slot = encoded_slot - 1U;
    int result = load_metadata(slot, metadata);
    if (result != 0) return result;
    if (metadata->generation != generation ||
        metadata->state == STORAGE_SLOT_FREE ||
        metadata->state == STORAGE_SLOT_RETIRED) return STORAGE_EINVAL;
    *slot_out = slot;
    return 0;
}

static int release_slot(size_t slot,
                        const storage_slot_metadata_t *metadata) {
    /* Default release is abandonment. Only validated reply ACK supplies a
     * local zero-effect copy; forgetting possible effects first fences them. */
    int fenced = mutation_fence_lost(metadata);
    if (fenced) return fenced;
    uint32_t generation = metadata->generation;
    storage_slot_metadata_t replacement =
        generation == STORAGE_HANDLE_GENERATION_MAX
        ? (storage_slot_metadata_t){
            .state = STORAGE_SLOT_RETIRED,
            .generation = STORAGE_HANDLE_GENERATION_MAX,
        }
        : (storage_slot_metadata_t){.generation = generation + 1U};
    bulk_release(make_handle(slot, metadata->generation));
    clear_data(slot);
    int result = store_metadata(slot, &replacement);
    if (result == 0) request_removed();
    return result;
}

int storage_request_pool_init(void) {
#ifdef REIST_HOST_TEST
    input_copy_hook = NULL;
#endif
    request_stats = (storage_request_stats_t){0};
    mutation_poisoned = 0;
    mutation_fences_initialized = false;
    uint32_t no_fences = 0;
    if (critical_object_init(&protected_mutation_fences, STORAGE_POOL_METADATA_VERSION,
        &no_fences, sizeof(no_fences)) != 0) return STORAGE_EINTEGRITY;
    mutation_fences_initialized = true;
    storage_service_identity_t identity = {0};
    if (critical_object_init(&protected_service_identity,
            STORAGE_POOL_METADATA_VERSION, &identity, sizeof(identity)) != 0)
        return STORAGE_EINTEGRITY;
    for (size_t slot = 0U; slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
        storage_slot_metadata_t metadata = {0};
        if (critical_object_init(&slots[slot].metadata,
                STORAGE_POOL_METADATA_VERSION, &metadata,
                sizeof(metadata)) != 0) return STORAGE_EINTEGRITY;
        clear_data(slot);
    }
    memset(bulk_slots, 0, sizeof(bulk_slots));
    request_stats = (storage_request_stats_t){
        .version = STORAGE_REQUEST_STATS_VERSION,
        .struct_size = sizeof(storage_request_stats_t),
    };
    return 0;
}

static int bind_service_locked(int pid, uint32_t generation) {
    if (pid <= 0 || generation == 0U) return STORAGE_EINVAL;
    storage_service_identity_t identity;
    int result = load_identity(&identity);
    if (result != 0) return result;
    if (identity.pid != 0 &&
        (identity.pid != pid || identity.generation != generation))
        return STORAGE_EACCES;
    identity.pid = pid;
    identity.generation = generation;
    return store_identity(&identity);
}

static void cancel_process_locked(int pid, uint32_t generation);

static void unbind_service_locked(int pid, uint32_t generation) {
    storage_service_identity_t identity;
    if (load_identity(&identity) == 0 && identity.pid == pid &&
        identity.generation == generation) {
        identity = (storage_service_identity_t){0};
        (void)store_identity(&identity);
    }
    cancel_process_locked(pid, generation);
}

static int submit_locked(int client_pid, uint32_t client_generation,
        const storage_request_submit_t *request, const uint8_t *block_data,
        uint64_t now_ms, storage_request_handle_t *handle_out) {
    if (client_pid <= 0 || client_generation == 0U || request == NULL ||
        handle_out == NULL || request->version != STORAGE_REQUEST_VERSION ||
        request->struct_size < sizeof(*request) ||
        request->operation < STORAGE_REQUEST_READ ||
        request->operation > STORAGE_REQUEST_VFS_OBJECT_MUTATE ||
        request->timeout_ms == 0U ||
        request->timeout_ms > STORAGE_REQUEST_MAX_TIMEOUT_MS)
        return STORAGE_EINVAL;
    uint32_t expected = request->length;
    if (request->operation == STORAGE_REQUEST_BLOCK_FLUSH ||
        request->operation == STORAGE_REQUEST_VFS_SYNC ||
        request->operation == STORAGE_REQUEST_FORMAT_FAT12 ||
        request->operation == STORAGE_REQUEST_FORMAT_FAT32 ||
        request->operation == STORAGE_REQUEST_FORMAT_FAT32_SCAN ||
        request->operation == STORAGE_REQUEST_FORMAT_FAT32_PREPARE ||
        request->operation == STORAGE_REQUEST_CHECK_FAT12 ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_MIRROR ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_CHAINS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_SHORT_FILES ||
        request->operation == STORAGE_REQUEST_RECLAIM_FAT12_ORPHANS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_LOOPS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_LOOPS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_SHORT_LOOPS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_CROSSLINKS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_SIZE ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_VOLUME_LABEL ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_ZERO_FILES ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_ZERO_START_FILES ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_DOT_SIZE ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_DOT_CLUSTER ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_REQUIRED_CROSSLINKS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_CROSSLINKS ||
        request->operation == STORAGE_REQUEST_REPAIR_FAT12_DIRECTORY_TOPOLOGY ||
        request->operation == STORAGE_REQUEST_SALVAGE_FAT12_ORPHANS ||
        request->operation == STORAGE_REQUEST_RECORD_FAT12_BAD_SECTOR)
        expected = 0U;
    if ((request->operation == STORAGE_REQUEST_BLOCK_READ ||
         request->operation == STORAGE_REQUEST_BLOCK_WRITE) &&
        request->length != STORAGE_REQUEST_BLOCK_SIZE) return STORAGE_EMSGSIZE;
    if ((request->operation == STORAGE_REQUEST_VFS_READ ||
         request->operation == STORAGE_REQUEST_VFS_WRITE) &&
        (request->length == 0U ||
         request->length > STORAGE_REQUEST_BLOCK_SIZE)) return STORAGE_EMSGSIZE;
    if ((request->operation == STORAGE_REQUEST_VFS_SHADOW_STAT ||
         request->operation == STORAGE_REQUEST_VFS_BULK_READ ||
         request->operation == STORAGE_REQUEST_VFS_SYMLINK ||
         request->operation == STORAGE_REQUEST_VFS_NAMESPACE ||
         request->operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE) &&
        request->length != STORAGE_REQUEST_BLOCK_SIZE) return STORAGE_EMSGSIZE;
    if (request->operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE &&
        (request->struct_size != sizeof(*request) || request->resource ||
         request->offset > STORAGE_REQUEST_BULK_MAX_BYTES)) return STORAGE_EINVAL;
    if ((request->operation == STORAGE_REQUEST_VFS_SYMLINK ||
         request->operation == STORAGE_REQUEST_VFS_NAMESPACE) &&
        (request->resource != 0U || request->offset != 0U))
        return STORAGE_EINVAL;
    if (request->length != expected) return STORAGE_EMSGSIZE;
    if (operation_has_input(request->operation) && block_data == NULL)
        return STORAGE_EINVAL;
    uint32_t client_requests = 0U;
    for (size_t slot = 0U; slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
        storage_slot_metadata_t metadata;
        int result = load_metadata(slot, &metadata);
        if (result != 0) return result;
        if (metadata.state != STORAGE_SLOT_FREE &&
            metadata.state != STORAGE_SLOT_RETIRED &&
            metadata.client_pid == client_pid &&
            metadata.client_generation == client_generation)
            ++client_requests;
    }
    if (client_requests >= STORAGE_REQUEST_MAX_PER_CLIENT) {
        increment_saturating(&request_stats.client_capacity_rejections);
        return STORAGE_ENOSPC;
    }
    bool needs_bulk = request->operation == STORAGE_REQUEST_VFS_BULK_READ ||
        (request->operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE && request->offset);
    if (needs_bulk) {
        bool bulk_available = false;
        for (size_t slot = 0U; slot < STORAGE_REQUEST_BULK_CAPACITY; ++slot)
            if (bulk_slots[slot].state == STORAGE_BULK_FREE) {
                bulk_available = true;
                break;
            }
        if (!bulk_available) {
            increment_saturating(&request_stats.pool_capacity_rejections);
            return STORAGE_ENOSPC;
        }
    }
    for (size_t slot = 0U; slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
        storage_slot_metadata_t metadata;
        int result = load_metadata(slot, &metadata);
        if (result != 0) return result;
        if (metadata.state != STORAGE_SLOT_FREE) continue;
        if (metadata.generation == STORAGE_HANDLE_GENERATION_MAX) {
            metadata = (storage_slot_metadata_t){
                .state = STORAGE_SLOT_RETIRED,
                .generation = STORAGE_HANDLE_GENERATION_MAX,
            };
            if (store_metadata(slot, &metadata) != 0)
                return STORAGE_EINTEGRITY;
            continue;
        }
        uint32_t generation = metadata.generation + 1U;
        metadata = (storage_slot_metadata_t){
            .state = request->operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE && request->offset
                ? STORAGE_SLOT_INPUT_PENDING : STORAGE_SLOT_QUEUED,
            .generation = generation,
            .operation = request->operation,
            .client_pid = client_pid,
            .client_generation = client_generation,
            .resource = request->resource,
            .offset = request->offset,
            .length = expected,
            .deadline_ms = deadline_after(now_ms, request->timeout_ms),
        };
        store_data(slot, operation_has_input(request->operation)
                                  ? block_data : NULL,
                   operation_has_input(request->operation) ? expected : 0U);
        result = store_metadata(slot, &metadata);
        if (result != 0) {
            clear_data(slot);
            return result;
        }
        storage_request_handle_t handle = make_handle(slot, generation);
        if (needs_bulk && bulk_reserve(handle) == NULL) {
            storage_slot_metadata_t replacement = {.generation = generation + 1U};
            clear_data(slot);
            (void)store_metadata(slot, &replacement);
            increment_saturating(&request_stats.pool_capacity_rejections);
            return STORAGE_ENOSPC;
        }
        request_added();
        *handle_out = handle;
        return 0;
    }
    increment_saturating(&request_stats.pool_capacity_rejections);
    return STORAGE_ENOSPC;
}

static int claim_locked(int service_pid, uint32_t service_generation,
        uint64_t now_ms,
        storage_request_descriptor_t *request_v1_out,
        storage_request_descriptor_v2_t *request_v2_out,
        storage_request_descriptor_v3_t *request_v3_out,
        uint8_t *block_data_out) {
    if ((request_v1_out != NULL) + (request_v2_out != NULL) + (request_v3_out != NULL) != 1)
        return STORAGE_EINVAL;
    storage_service_identity_t identity;
    int result = load_identity(&identity);
    if (result != 0) return result;
    if (identity.pid != service_pid || identity.generation != service_generation)
        return STORAGE_EACCES;
    for (size_t slot = 0U; slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
        storage_slot_metadata_t metadata;
        result = load_metadata(slot, &metadata);
        if (result != 0) return result;
        if (metadata.state != STORAGE_SLOT_QUEUED && metadata.state != STORAGE_SLOT_INPUT_PENDING) continue;
        if (now_ms >= metadata.deadline_ms) {
            metadata.state = STORAGE_SLOT_COMPLETE;
            metadata.result = -110;
            result = store_metadata(slot, &metadata);
            if (result != 0) return result;
            continue;
        }
        if (metadata.state == STORAGE_SLOT_INPUT_PENDING) continue;
        if (metadata.operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE && !request_v3_out) continue;
        if (operation_has_input(metadata.operation) &&
            load_data(slot, block_data_out, metadata.length) != 0)
            return STORAGE_EINTEGRITY;
        metadata.state = STORAGE_SLOT_CLAIMED;
        metadata.service_pid = service_pid;
        metadata.service_generation = service_generation;
        result = store_metadata(slot, &metadata);
        if (result != 0) return result;
        if (request_v1_out != NULL) {
            *request_v1_out = (storage_request_descriptor_t){
                .version = STORAGE_REQUEST_VERSION,
                .struct_size = sizeof(*request_v1_out),
                .handle = make_handle(slot, metadata.generation),
                .operation = metadata.operation,
                .resource = metadata.resource,
                .offset = metadata.offset,
                .length = metadata.length,
            };
        } else if (request_v2_out != NULL) {
            *request_v2_out = (storage_request_descriptor_v2_t){
                .version = STORAGE_REQUEST_DESCRIPTOR_V2_VERSION,
                .struct_size = sizeof(*request_v2_out),
                .handle = make_handle(slot, metadata.generation),
                .operation = metadata.operation,
                .resource = metadata.resource,
                .offset = metadata.offset,
                .length = metadata.length,
                .client_pid = metadata.client_pid,
                .client_generation = metadata.client_generation,
                .service_generation = metadata.service_generation,
            };
        } else {
            *request_v3_out = (storage_request_descriptor_v3_t){
                .version = STORAGE_REQUEST_DESCRIPTOR_V3_VERSION,
                .struct_size = sizeof(*request_v3_out),
                .handle = make_handle(slot, metadata.generation),
                .operation = metadata.operation, .resource = metadata.resource,
                .offset = metadata.offset, .length = metadata.length,
                .client_pid = metadata.client_pid, .client_generation = metadata.client_generation,
                .service_generation = metadata.service_generation, .deadline_ms = metadata.deadline_ms,
            };
        }
        return 0;
    }
    return STORAGE_EAGAIN;
}

static int complete_locked(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, int32_t result_code,
        const uint8_t *block_data) {
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &slot, &metadata);
    if (result != 0) return result;
    if ((metadata.state != STORAGE_SLOT_CLAIMED &&
         metadata.state != STORAGE_SLOT_CANCEL_PENDING) ||
        metadata.service_pid != service_pid ||
        metadata.service_generation != service_generation)
        return STORAGE_EACCES;
    if (metadata.state == STORAGE_SLOT_CANCEL_PENDING)
        return release_slot(slot, &metadata);
    if (metadata.operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE &&
        (metadata.mutation_state == MUTATION_BOUND || metadata.mutation_state == MUTATION_ATTEMPTED)) {
        if (!result_code) return STORAGE_EAGAIN; /* Guard END must precede success. */
        result = mutation_fence_lost(&metadata);
        if (result) return result;
        metadata.mutation_state = metadata.mutation_state == MUTATION_BOUND ?
            MUTATION_FINISHED_NO_EFFECT : MUTATION_FINISHED_UNKNOWN;
    }
    if (metadata.operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE && result_code != 0) {
        result = mutation_fence_lost(&metadata);
        if (result) return result;
    }
    if (result_code == 0 &&
        metadata.operation == STORAGE_REQUEST_VFS_BULK_READ) {
        storage_bulk_slot_t *bulk = bulk_find(handle);
        if (bulk == NULL || bulk->state != STORAGE_BULK_PUBLISHED)
            return STORAGE_EINVAL;
    }
    if (result_code != 0 &&
        metadata.operation == STORAGE_REQUEST_VFS_BULK_READ)
        bulk_release(handle);
    if (result_code == 0 && operation_has_output(metadata.operation)) {
        if (block_data == NULL) return STORAGE_EINVAL;
        store_data(slot, block_data, metadata.length);
    }
    metadata.state = STORAGE_SLOT_COMPLETE;
    metadata.result = result_code;
    return store_metadata(slot, &metadata);
}

static int collect_locked(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, int32_t *result_out,
        uint8_t *block_data_out, uint32_t *data_length_out) {
    if (result_out == NULL) return STORAGE_EINVAL;
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &slot, &metadata);
    if (result != 0) return result;
    if (metadata.client_pid != client_pid ||
        metadata.client_generation != client_generation)
        return STORAGE_EACCES;
    if (metadata.operation == STORAGE_REQUEST_VFS_OBJECT_MUTATE) return STORAGE_EINVAL;
    if (metadata.state == STORAGE_SLOT_CANCEL_PENDING)
        return STORAGE_ECANCELED;
    if (metadata.state != STORAGE_SLOT_COMPLETE) return STORAGE_EAGAIN;
    if (metadata.operation == STORAGE_REQUEST_VFS_BULK_READ)
        return STORAGE_EINVAL;
    uint32_t data_length = metadata.result == 0 &&
        operation_has_output(metadata.operation) ? metadata.length : 0U;
    if (metadata.result == 0 && operation_has_output(metadata.operation)) {
        if (block_data_out == NULL) return STORAGE_EINVAL;
        result = load_data(slot, block_data_out, metadata.length);
        if (result != 0) return result;
    }
    *result_out = metadata.result;
    if (data_length_out != NULL) *data_length_out = data_length;
    return release_slot(slot, &metadata);
}

static int cancel_locked(int client_pid, uint32_t client_generation,
                         storage_request_handle_t handle) {
    if (client_pid <= 0 || client_generation == 0U)
        return STORAGE_EINVAL;
    size_t slot = 0U;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &slot, &metadata);
    if (result != 0) return result;
    if (metadata.client_pid != client_pid ||
        metadata.client_generation != client_generation)
        return STORAGE_EACCES;
    result = mutation_fence_lost(&metadata);
    if (result) return result;
    if (metadata.state == STORAGE_SLOT_DELIVERY_CANCELLED) return 0;
    if (metadata.state == STORAGE_SLOT_DELIVERING) {
        metadata.state = STORAGE_SLOT_DELIVERY_CANCELLED;
        return store_metadata(slot, &metadata);
    }
    if (metadata.state == STORAGE_SLOT_CANCEL_PENDING) return 0;
    if (metadata.state == STORAGE_SLOT_QUEUED ||
        metadata.state == STORAGE_SLOT_INPUT_PENDING ||
        metadata.state == STORAGE_SLOT_COMPLETE || metadata.state == STORAGE_SLOT_DELIVERED)
        return release_slot(slot, &metadata);
    if (metadata.state != STORAGE_SLOT_CLAIMED) return STORAGE_EINVAL;
    metadata.state = STORAGE_SLOT_CANCEL_PENDING;
    return store_metadata(slot, &metadata);
}

static void cancel_process_locked(int pid, uint32_t generation) {
    if (pid <= 0 || generation == 0U) return;
    for (size_t slot = 0U; slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
        storage_slot_metadata_t metadata;
        if (load_metadata(slot, &metadata) != 0) continue;
        if ((metadata.client_pid == pid &&
             metadata.client_generation == generation) ||
            (metadata.service_pid == pid &&
             metadata.service_generation == generation)) {
            if (metadata.state == STORAGE_SLOT_DELIVERING || metadata.state == STORAGE_SLOT_DELIVERY_CANCELLED) {
                if (!mutation_fence_lost(&metadata)) {
                    metadata.state = STORAGE_SLOT_DELIVERY_CANCELLED;
                    (void)store_metadata(slot, &metadata);
                }
                continue; /* The kernel copy owner must quiesce before slot reuse. */
            }
            (void)release_slot(slot, &metadata);
        }
    }
}

int storage_request_bind_service(int pid, uint32_t generation) {
    uint32_t flags = storage_pool_lock();
    int result = bind_service_locked(pid, generation);
    storage_pool_unlock(flags);
    return result;
}

void storage_request_unbind_service(int pid, uint32_t generation) {
    uint32_t flags = storage_pool_lock();
    unbind_service_locked(pid, generation);
    storage_pool_unlock(flags);
}

int storage_request_submit(int client_pid, uint32_t client_generation,
        const storage_request_submit_t *request, const uint8_t *block_data,
        uint64_t now_ms, storage_request_handle_t *handle_out) {
    uint32_t flags = storage_pool_lock();
    int result = submit_locked(client_pid, client_generation, request,
                               block_data, now_ms, handle_out);
    storage_pool_unlock(flags);
    return result;
}

int storage_request_claim(int service_pid, uint32_t service_generation,
        uint64_t now_ms, storage_request_descriptor_t *request_out,
        uint8_t *block_data_out) {
    uint32_t flags = storage_pool_lock();
    int result = claim_locked(service_pid, service_generation, now_ms,
                              request_out, NULL, NULL, block_data_out);
    storage_pool_unlock(flags);
    return result;
}

int storage_request_claim_v2(int service_pid, uint32_t service_generation,
        uint64_t now_ms, storage_request_descriptor_v2_t *request_out,
        uint8_t *block_data_out) {
    uint32_t flags = storage_pool_lock();
    int result = claim_locked(service_pid, service_generation, now_ms,
                              NULL, request_out, NULL, block_data_out);
    storage_pool_unlock(flags);
    return result;
}

int storage_request_claim_v3(int service_pid, uint32_t service_generation,
        uint64_t now_ms, storage_request_descriptor_v3_t *request_out,
        uint8_t *block_data_out) {
    uint32_t flags = storage_pool_lock();
    int result = claim_locked(service_pid, service_generation, now_ms,
                              NULL, NULL, request_out, block_data_out);
    storage_pool_unlock(flags);
    return result;
}

int storage_request_complete(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, int32_t result_code,
        const uint8_t *block_data) {
    uint32_t flags = storage_pool_lock();
    int result = complete_locked(service_pid, service_generation, handle,
                                 result_code, block_data);
    storage_pool_unlock(flags);
    return result;
}

int storage_request_completion_context(int service_pid,
        uint32_t service_generation, storage_request_handle_t handle,
        uint32_t *operation_out, uint32_t *resource_out) {
    if (operation_out == NULL || resource_out == NULL) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t slot = 0U;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &slot, &metadata);
    if (result == 0 &&
        ((metadata.state != STORAGE_SLOT_CLAIMED &&
          metadata.state != STORAGE_SLOT_CANCEL_PENDING) ||
         metadata.service_pid != service_pid ||
         metadata.service_generation != service_generation))
        result = STORAGE_EACCES;
    if (result == 0) {
        *operation_out = metadata.operation;
        *resource_out = metadata.resource;
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_collect(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, int32_t *result_out,
        uint8_t *block_data_out) {
    return storage_request_collect_ex(client_pid, client_generation, handle,
                                      result_out, block_data_out, NULL);
}

int storage_request_collect_ex(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, int32_t *result_out,
        uint8_t *block_data_out, uint32_t *data_length_out) {
    uint32_t flags = storage_pool_lock();
    int result = collect_locked(client_pid, client_generation, handle,
                                result_out, block_data_out, data_length_out);
    storage_pool_unlock(flags);
    return result;
}

int storage_request_input_publish(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, const uint8_t *data, uint32_t length,
        uint64_t now_ms) {
    if (client_pid <= 0 || !client_generation || !data || !length ||
        length > STORAGE_REQUEST_BULK_MAX_BYTES) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &slot, &metadata);
    storage_bulk_slot_t *bulk = result ? NULL : bulk_find(handle);
    if (!result && (metadata.client_pid != client_pid || metadata.client_generation != client_generation ||
        metadata.operation != STORAGE_REQUEST_VFS_OBJECT_MUTATE)) result = STORAGE_EACCES;
    if (!result && metadata.offset != length) result = STORAGE_EMSGSIZE;
    if (!result && now_ms >= metadata.deadline_ms) result = -110;
    if (!result && (metadata.state != STORAGE_SLOT_INPUT_PENDING ||
        !bulk || bulk->state != STORAGE_BULK_RESERVED)) result = STORAGE_EINVAL;
    if (!result) bulk->state = STORAGE_BULK_WRITING;
    storage_pool_unlock(flags);
    if (result) return result;

    memcpy(bulk->bytes, data, length);
#ifdef REIST_HOST_TEST
    if (input_copy_hook) input_copy_hook();
#endif
    uint32_t crc = crc32_bytes(bulk->bytes, length);
    flags = storage_pool_lock();
    result = resolve_handle(handle, &slot, &metadata);
    if (bulk->request_handle != handle) result = STORAGE_EINTEGRITY;
    else if (result || bulk->state == STORAGE_BULK_REVOKED) {
        bulk_clear(bulk); /* The copying owner has now quiesced. */
        result = STORAGE_ECANCELED;
    } else if (bulk->state != STORAGE_BULK_WRITING || metadata.state != STORAGE_SLOT_INPUT_PENDING ||
               metadata.client_pid != client_pid || metadata.client_generation != client_generation) {
        bulk_clear(bulk);
        result = STORAGE_EINTEGRITY;
    } else {
        bulk->length = length;
        bulk->crc32 = crc;
        bulk->state = STORAGE_BULK_PUBLISHED;
        metadata.state = STORAGE_SLOT_QUEUED;
        result = store_metadata(slot, &metadata);
        if (result) bulk_clear(bulk);
    }
    storage_pool_unlock(flags);
    return result;
}

static int mutation_claimed_locked(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint64_t now_ms, size_t *slot,
        storage_slot_metadata_t *metadata) {
    storage_service_identity_t identity;
    int result = load_identity(&identity);
    if (!result && (service_pid <= 0 || !service_generation ||
        identity.pid != service_pid || identity.generation != service_generation)) result = STORAGE_EACCES;
    if (!result) result = resolve_handle(handle, slot, metadata);
    if (!result && (metadata->operation != STORAGE_REQUEST_VFS_OBJECT_MUTATE ||
        metadata->service_pid != service_pid || metadata->service_generation != service_generation))
        result = STORAGE_EACCES;
    if (!result && metadata->state == STORAGE_SLOT_CANCEL_PENDING) result = STORAGE_ECANCELED;
    if (!result && metadata->state != STORAGE_SLOT_CLAIMED) result = STORAGE_EACCES;
    if (!result && now_ms >= metadata->deadline_ms) result = -110;
    return result;
}

int storage_request_input_take(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint8_t *data, uint32_t capacity,
        uint32_t *transferred, uint64_t now_ms) {
    if (transferred) *transferred = 0;
    if (!transferred || !data || !capacity || capacity > STORAGE_REQUEST_BULK_MAX_BYTES)
        return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_claimed_locked(service_pid, service_generation, handle, now_ms, &slot, &metadata);
    storage_bulk_slot_t *bulk = result ? NULL : bulk_find(handle);
    uint32_t length = 0, crc = 0;
    if (!result && (!bulk || bulk->state != STORAGE_BULK_PUBLISHED)) result = STORAGE_EINVAL;
    if (!result && (!bulk->length || bulk->length != metadata.offset ||
        bulk->length > STORAGE_REQUEST_BULK_MAX_BYTES)) result = STORAGE_EINTEGRITY;
    if (!result && bulk->length > capacity) result = STORAGE_EMSGSIZE;
    if (!result) {
        length = bulk->length;
        crc = bulk->crc32;
        bulk->state = STORAGE_BULK_READING;
    }
    storage_pool_unlock(flags);
    if (result) return result;

    memcpy(data, bulk->bytes, length);
    bool valid = crc32_bytes(data, length) == crc;
#ifdef REIST_HOST_TEST
    if (input_copy_hook) input_copy_hook();
#endif
    flags = storage_pool_lock();
    result = mutation_claimed_locked(service_pid, service_generation, handle, now_ms, &slot, &metadata);
    if (bulk->request_handle != handle) result = STORAGE_EINTEGRITY;
    else if (result || bulk->state == STORAGE_BULK_REVOKED) {
        bulk_clear(bulk);
        if (!result) result = STORAGE_ECANCELED;
    } else if (bulk->state != STORAGE_BULK_READING || !valid) {
        bulk_clear(bulk);
        result = STORAGE_EINTEGRITY;
    } else {
        bulk->state = STORAGE_BULK_CONSUMED;
        *transferred = length;
    }
    storage_pool_unlock(flags);
    if (result) memset(data, 0, length);
    return result;
}

int storage_request_mutation_context(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint64_t now_ms,
        storage_request_descriptor_v3_t *request_out) {
    if (!request_out) return STORAGE_EINVAL;
    memset(request_out, 0, sizeof(*request_out));
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_claimed_locked(service_pid, service_generation, handle, now_ms, &slot, &metadata);
    if (!result && metadata.offset) {
        storage_bulk_slot_t *bulk = bulk_find(handle);
        if (!bulk || bulk->state != STORAGE_BULK_CONSUMED || bulk->length != metadata.offset)
            result = STORAGE_EAGAIN;
    }
    if (!result) *request_out = (storage_request_descriptor_v3_t){
        .version=STORAGE_REQUEST_DESCRIPTOR_V3_VERSION, .struct_size=sizeof(*request_out),
        .handle=handle, .operation=metadata.operation, .resource=metadata.resource,
        .offset=metadata.offset, .length=metadata.length, .client_pid=metadata.client_pid,
        .client_generation=metadata.client_generation, .service_generation=metadata.service_generation,
        .deadline_ms=metadata.deadline_ms,
    };
    storage_pool_unlock(flags);
    return result;
}

int storage_request_mutation_bind(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint32_t resource, uint64_t now_ms) {
    if (resource >= 32U) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_claimed_locked(service_pid, service_generation, handle, now_ms, &slot, &metadata);
    uint32_t mask = 0;
    if (!result) result = mutation_fences_read(&mask);
    if (!result && (mask & (1U << resource))) result = -5;
    if (!result && metadata.mutation_state != MUTATION_UNBOUND) result = STORAGE_EACCES;
    if (!result && metadata.offset) {
        storage_bulk_slot_t *bulk = bulk_find(handle);
        if (!bulk || bulk->state != STORAGE_BULK_CONSUMED || bulk->length != metadata.offset)
            result = STORAGE_EAGAIN;
    }
    if (!result) {
        metadata.mutation_resource_plus_one = resource + 1U;
        metadata.mutation_state = MUTATION_BOUND;
        result = store_metadata(slot, &metadata);
    }
    storage_pool_unlock(flags);
    return result;
}

static int mutation_io(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint32_t resource, uint64_t now_ms, bool effect) {
    if (resource >= 32U) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_claimed_locked(service_pid, service_generation, handle, now_ms, &slot, &metadata);
    uint32_t mask = 0;
    if (!result) result = mutation_fences_read(&mask);
    if (!result && (mask & (1U << resource))) result = -5;
    if (!result && (metadata.mutation_resource_plus_one != resource + 1U ||
        (metadata.mutation_state != MUTATION_BOUND && metadata.mutation_state != MUTATION_ATTEMPTED)))
        result = STORAGE_EACCES;
    if (!result && effect && metadata.mutation_state != MUTATION_ATTEMPTED) {
        metadata.mutation_state = MUTATION_ATTEMPTED;
        result = store_metadata(slot, &metadata);
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_mutation_effect(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint32_t resource, uint64_t now_ms) {
    return mutation_io(service_pid, service_generation, handle, resource, now_ms, true);
}

int storage_request_mutation_authorized(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint32_t resource, uint64_t now_ms) {
    return mutation_io(service_pid, service_generation, handle, resource, now_ms, false);
}

int storage_request_mutation_finish(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, uint32_t resource, uint32_t outcome, uint64_t now_ms) {
    if (resource >= 32U || outcome < STORAGE_MUTATION_NO_EFFECT || outcome > STORAGE_MUTATION_UNKNOWN)
        return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_claimed_locked(service_pid, service_generation, handle, now_ms, &slot, &metadata);
    if (!result && (metadata.mutation_resource_plus_one != resource + 1U ||
        (metadata.mutation_state != MUTATION_BOUND && metadata.mutation_state != MUTATION_ATTEMPTED) ||
        (outcome == STORAGE_MUTATION_NO_EFFECT && metadata.mutation_state == MUTATION_ATTEMPTED)))
        result = STORAGE_EACCES;
    if (!result) {
        metadata.mutation_state = outcome == STORAGE_MUTATION_NO_EFFECT ? MUTATION_FINISHED_NO_EFFECT :
            outcome == STORAGE_MUTATION_DURABLE ? MUTATION_FINISHED_DURABLE : MUTATION_FINISHED_UNKNOWN;
        if (outcome == STORAGE_MUTATION_UNKNOWN) result = mutation_fence_lost(&metadata);
        if (!result) result = store_metadata(slot, &metadata);
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_mutation_fences(uint64_t now_ms, uint32_t *mask) {
    if (!mask) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    if (mutation_fences_initialized && now_ms) {
        for (size_t slot = 0; slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
            storage_slot_metadata_t metadata;
            if (load_metadata(slot, &metadata) != 0) break;
            if (metadata.deadline_ms && now_ms >= metadata.deadline_ms && mutation_fence_lost(&metadata)) break;
        }
    }
    int result = mutation_fences_read(mask);
    storage_pool_unlock(flags);
    return result;
}

static int mutation_recovery(int service_pid, uint32_t service_generation,
    uint32_t resource, bool clear) {
    if (resource >= 32U || service_pid <= 0 || !service_generation) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock(), mask = 0;
    storage_service_identity_t identity;
    int result = mutation_fences_read(&mask);
    if (!result && !mutation_fences_initialized) result = STORAGE_EACCES;
    if (!result) result = load_identity(&identity);
    if (!result && (identity.pid != service_pid || identity.generation != service_generation))
        result = STORAGE_EACCES;
    for (size_t slot = 0; !result && slot < STORAGE_REQUEST_POOL_CAPACITY; ++slot) {
        storage_slot_metadata_t metadata;
        result = load_metadata(slot, &metadata);
        /* Includes cancelled/delivering copies and durable receipts not ACKed
         * yet: none may later re-publish an old resource's lost-reply fence. */
        if (!result && metadata.mutation_resource_plus_one == resource+1U) result = -16;
    }
    if (!result && clear && (mask & (1U << resource))) {
        mask &= ~(1U << resource);
        if (protected_mutation_fences.publication_lock || critical_object_update(
            &protected_mutation_fences, STORAGE_POOL_METADATA_VERSION, &mask,
            sizeof(mask), mutation_fences_valid)) {
            mutation_poisoned = UINT32_MAX; result = STORAGE_EINTEGRITY;
        }
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_recovery_ready(int service_pid, uint32_t service_generation, uint32_t resource) {
    return mutation_recovery(service_pid, service_generation, resource, false);
}
int storage_request_recovery_clear(int service_pid, uint32_t service_generation, uint32_t resource) {
    return mutation_recovery(service_pid, service_generation, resource, true);
}
int storage_request_recovery_refence(uint32_t resource) {
    if (resource >= 32U) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    storage_slot_metadata_t lost = {.mutation_resource_plus_one=resource+1U,
        .mutation_state=MUTATION_FINISHED_UNKNOWN};
    int result = mutation_fence_lost(&lost);
    storage_pool_unlock(flags);
    return result;
}

static int mutation_client_locked(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, size_t *slot, storage_slot_metadata_t *metadata) {
    int result = resolve_handle(handle, slot, metadata);
    if (!result && (metadata->client_pid != client_pid || metadata->client_generation != client_generation))
        result = STORAGE_EACCES;
    if (!result && metadata->operation != STORAGE_REQUEST_VFS_OBJECT_MUTATE) result = STORAGE_EINVAL;
    return result;
}

int storage_request_mutation_reply_begin(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, uint64_t now_ms, int32_t *result_out, uint8_t *frame) {
    if (!result_out || !frame) return STORAGE_EINVAL;
    *result_out = 0;
    memset(frame, 0, STORAGE_REQUEST_BLOCK_SIZE);
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_client_locked(client_pid, client_generation, handle, &slot, &metadata);
    if (!result && metadata.state != STORAGE_SLOT_COMPLETE) result = STORAGE_EAGAIN;
    if (!result && now_ms >= metadata.deadline_ms) {
        result = release_slot(slot, &metadata);
        if (!result) result = -110;
    }
    if (!result && metadata.result == 0) {
        result = load_data(slot, frame, metadata.length);
        if (result) (void)mutation_fence_lost(&metadata);
    }
    if (!result) {
        metadata.state = STORAGE_SLOT_DELIVERING;
        result = store_metadata(slot, &metadata);
        if (!result) *result_out = metadata.result;
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_mutation_reply_end(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, bool copied, uint64_t now_ms) {
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_client_locked(client_pid, client_generation, handle, &slot, &metadata);
    if (!result && metadata.state != STORAGE_SLOT_DELIVERING && metadata.state != STORAGE_SLOT_DELIVERY_CANCELLED)
        result = STORAGE_EACCES;
    if (!result) {
        bool cancelled = metadata.state == STORAGE_SLOT_DELIVERY_CANCELLED;
        bool expired = now_ms >= metadata.deadline_ms;
        if (!copied || cancelled || expired) {
            result = release_slot(slot, &metadata);
            if (!result) result = cancelled ? STORAGE_ECANCELED : expired ? -110 : 0;
        } else {
            metadata.state = STORAGE_SLOT_DELIVERED;
            result = store_metadata(slot, &metadata);
        }
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_mutation_reply_ack(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, uint64_t now_ms) {
    uint32_t flags = storage_pool_lock();
    size_t slot;
    storage_slot_metadata_t metadata;
    int result = mutation_client_locked(client_pid, client_generation, handle, &slot, &metadata);
    if (!result && metadata.state != STORAGE_SLOT_DELIVERED) result = STORAGE_EACCES;
    if (!result) {
        bool expired = now_ms >= metadata.deadline_ms;
        if (!expired) {
            /* Only a successfully copied and subsequently validated reply may
             * release without recording loss. Existing UNKNOWN fences persist. */
            metadata.mutation_state = MUTATION_UNBOUND;
            metadata.mutation_resource_plus_one = 0;
        }
        result = release_slot(slot, &metadata);
        if (!result && expired) result = -110;
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_bulk_publish(int service_pid, uint32_t service_generation,
        storage_request_handle_t handle, const uint8_t *data,
        uint32_t length) {
    if (service_pid <= 0 || service_generation == 0U ||
        length > STORAGE_REQUEST_BULK_MAX_BYTES ||
        (length != 0U && data == NULL)) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t request_slot = 0U;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &request_slot, &metadata);
    (void)request_slot;
    storage_bulk_slot_t *bulk = result == 0 ? bulk_find(handle) : NULL;
    if (result == 0 &&
        (metadata.operation != STORAGE_REQUEST_VFS_BULK_READ ||
         metadata.state != STORAGE_SLOT_CLAIMED ||
         metadata.service_pid != service_pid ||
         metadata.service_generation != service_generation))
        result = STORAGE_EACCES;
    if (result == 0 &&
        (bulk == NULL || bulk->state != STORAGE_BULK_RESERVED))
        result = STORAGE_EINVAL;
    if (result == 0) bulk->state = STORAGE_BULK_WRITING;
    storage_pool_unlock(flags);
    if (result != 0) return result;

    if (length != 0U) memcpy(bulk->bytes, data, length);
    uint32_t crc = crc32_bytes(bulk->bytes, length);

    flags = storage_pool_lock();
    if (bulk->request_handle != handle || bulk->state == STORAGE_BULK_REVOKED) {
        bulk_clear(bulk);
        result = STORAGE_ECANCELED;
    } else if (bulk->state != STORAGE_BULK_WRITING) {
        bulk_clear(bulk);
        result = STORAGE_EINTEGRITY;
    } else {
        bulk->length = length;
        bulk->crc32 = crc;
        bulk->state = STORAGE_BULK_PUBLISHED;
        result = 0;
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_bulk_collect(int client_pid, uint32_t client_generation,
        storage_request_handle_t handle, int32_t *result_out,
        uint8_t *frame_out, uint8_t *data_out, uint32_t capacity,
        uint32_t *transferred_out) {
    if (client_pid <= 0 || client_generation == 0U || result_out == NULL ||
        frame_out == NULL || transferred_out == NULL ||
        capacity > STORAGE_REQUEST_BULK_MAX_BYTES ||
        (capacity != 0U && data_out == NULL)) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    size_t request_slot = 0U;
    storage_slot_metadata_t metadata;
    int result = resolve_handle(handle, &request_slot, &metadata);
    if (result == 0 &&
        (metadata.client_pid != client_pid ||
         metadata.client_generation != client_generation))
        result = STORAGE_EACCES;
    if (result == 0 && metadata.state != STORAGE_SLOT_COMPLETE)
        result = STORAGE_EAGAIN;
    if (result == 0 && metadata.operation != STORAGE_REQUEST_VFS_BULK_READ)
        result = STORAGE_EINVAL;
    storage_bulk_slot_t *bulk = result == 0 ? bulk_find(handle) : NULL;
    uint32_t length = 0U;
    uint32_t crc = 0U;
    if (result == 0 && metadata.result == 0) {
        if (bulk == NULL || bulk->state != STORAGE_BULK_PUBLISHED)
            result = STORAGE_EINTEGRITY;
        else if (bulk->length > capacity)
            result = STORAGE_EMSGSIZE;
        else {
            length = bulk->length;
            crc = bulk->crc32;
            bulk->state = STORAGE_BULK_READING;
        }
    }
    if (result == 0 && load_data(request_slot, frame_out,
                                  STORAGE_REQUEST_BLOCK_SIZE) != 0)
        result = STORAGE_EINTEGRITY;
    if (result != 0) {
        storage_pool_unlock(flags);
        return result;
    }
    if (metadata.result != 0) {
        *result_out = metadata.result;
        *transferred_out = 0U;
        result = release_slot(request_slot, &metadata);
        storage_pool_unlock(flags);
        return result;
    }
    storage_pool_unlock(flags);

    bool payload_valid = crc == crc32_bytes(bulk->bytes, length);
    if (payload_valid && length != 0U) memcpy(data_out, bulk->bytes, length);

    flags = storage_pool_lock();
    if (bulk->request_handle != handle || bulk->state == STORAGE_BULK_REVOKED) {
        bulk_clear(bulk);
        result = STORAGE_ECANCELED;
    } else if (bulk->state != STORAGE_BULK_READING || !payload_valid) {
        bulk_clear(bulk);
        (void)release_slot(request_slot, &metadata);
        result = STORAGE_EINTEGRITY;
    } else {
        bulk_clear(bulk);
        *result_out = metadata.result;
        *transferred_out = length;
        result = release_slot(request_slot, &metadata);
    }
    storage_pool_unlock(flags);
    return result;
}

int storage_request_cancel(int client_pid, uint32_t client_generation,
                           storage_request_handle_t handle) {
    uint32_t flags = storage_pool_lock();
    int result = cancel_locked(client_pid, client_generation, handle);
    storage_pool_unlock(flags);
    return result;
}

void storage_request_cancel_process(int pid, uint32_t generation) {
    uint32_t flags = storage_pool_lock();
    cancel_process_locked(pid, generation);
    storage_pool_unlock(flags);
}

int storage_request_stats(storage_request_stats_t *stats_out) {
    if (stats_out == NULL) return STORAGE_EINVAL;
    uint32_t flags = storage_pool_lock();
    *stats_out = request_stats;
    storage_pool_unlock(flags);
    return 0;
}

#ifdef REIST_HOST_TEST
int storage_request_test_corrupt_data(storage_request_handle_t handle,
                                      bool corrupt_both_copies) {
    uint32_t encoded_slot = handle & STORAGE_HANDLE_SLOT_MASK;
    if (encoded_slot == 0U || encoded_slot > STORAGE_REQUEST_POOL_CAPACITY)
        return STORAGE_EINVAL;
    size_t slot = encoded_slot - 1U;
    slots[slot].primary.bytes[0] ^= 1U;
    if (corrupt_both_copies) slots[slot].shadow.bytes[1] ^= 2U;
    return 0;
}

int storage_request_test_corrupt_metadata(storage_request_handle_t handle,
                                          bool corrupt_both_copies) {
    uint32_t encoded_slot = handle & STORAGE_HANDLE_SLOT_MASK;
    if (encoded_slot == 0U || encoded_slot > STORAGE_REQUEST_POOL_CAPACITY)
        return STORAGE_EINVAL;
    size_t slot = encoded_slot - 1U;
    slots[slot].metadata.primary.crc32 ^= 1U;
    if (corrupt_both_copies) slots[slot].metadata.shadow.crc32 ^= 2U;
    return 0;
}

int storage_request_test_corrupt_bulk(storage_request_handle_t handle) {
    storage_bulk_slot_t *bulk = bulk_find(handle);
    if (bulk == NULL || bulk->state != STORAGE_BULK_PUBLISHED)
        return STORAGE_EINVAL;
    bulk->bytes[0] ^= 1U;
    return 0;
}
#endif
