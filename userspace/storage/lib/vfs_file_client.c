/** Fixed, generation-safe client sessions over service-owned VFS objects. */
#include "../include/reist/vfs_file_client.h"

#include "../include/reist/vfs_path.h"

#define FILE_HANDLE_SLOT_MASK 0xFFU
#define FILE_HANDLE_GENERATION_MAX 0x00FFFFFFU

typedef struct {
    uint32_t object_token;
    uint32_t service_generation;
    uint32_t offset;
    uint32_t timeout_ms;
    uint32_t rights;
    uint32_t generation;
    uint8_t in_use;
    uint8_t retired;
    uint8_t mutation_stale;
} file_session_t;

static file_session_t sessions[REIST_VFS_FILE_CAPACITY];
static uint8_t file_bulk_staging[X86OS_STORAGE_BULK_MAX_BYTES];

static void file_zero(void *target, uint32_t length) {
    uint8_t *bytes = target;
    for (uint32_t index = 0U; index < length; ++index) bytes[index] = 0U;
}

static void file_copy(void *target, const void *source, uint32_t length) {
    uint8_t *out = target;
    const uint8_t *in = source;
    for (uint32_t index = 0U; index < length; ++index) out[index] = in[index];
}

static int file_bytes_zero(const void *source, uint32_t length) {
    const uint8_t *bytes = source;
    for (uint32_t index = 0U; index < length; ++index)
        if (bytes[index] != 0U) return 0;
    return 1;
}

static uint32_t file_crc32(const uint8_t *data, uint32_t length) {
    uint32_t crc = 0xFFFFFFFFU;
    for (uint32_t index = 0U; index < length; ++index) {
        crc ^= data[index];
        for (uint32_t bit = 0U; bit < 8U; ++bit)
            crc = (crc >> 1U) ^ (0xEDB88320U &
                  (uint32_t)-(int32_t)(crc & 1U));
    }
    return crc ^ 0xFFFFFFFFU;
}

static reist_vfs_file_handle_t file_handle(uint32_t slot,
                                           uint32_t generation) {
    return (generation << 8U) | (slot + 1U);
}

static int file_resolve(reist_vfs_file_handle_t handle, uint32_t *slot_out,
                        file_session_t **session_out) {
    uint32_t encoded_slot = handle & FILE_HANDLE_SLOT_MASK;
    uint32_t generation = handle >> 8U;
    if (encoded_slot == 0U || encoded_slot > REIST_VFS_FILE_CAPACITY ||
        generation == 0U || slot_out == 0 || session_out == 0) return -9;
    uint32_t slot = encoded_slot - 1U;
    file_session_t *session = &sessions[slot];
    if (session->in_use == 0U || session->retired != 0U ||
        session->generation != generation) return -9;
    *slot_out = slot;
    *session_out = session;
    return 0;
}

static int file_transact(void *frame, uint32_t timeout_ms) {
    x86os_storage_submit_t request = {
        .version = X86OS_STORAGE_REQUEST_VERSION,
        .struct_size = sizeof(request),
        .operation = X86OS_STORAGE_VFS_SHADOW_STAT,
        .resource = 0U,
        .offset = 0U,
        .length = X86OS_STORAGE_BLOCK_SIZE,
        .timeout_ms = timeout_ms,
    };
    x86os_storage_handle_t request_handle = 0U;
    int status = x86os_storage_submit(&request, frame, &request_handle);
    if (status != 0 || request_handle == 0U)
        return status != 0 ? status : -5;
    uint64_t start = 0U;
    if (x86os_monotonic_ms(&start) != 0) {
        (void)x86os_storage_cancel(request_handle);
        return -5;
    }
    uint64_t deadline = UINT64_MAX - start < timeout_ms
        ? UINT64_MAX : start + timeout_ms;
    for (;;) {
        uint64_t now = 0U;
        if (x86os_monotonic_ms(&now) != 0 || now < start) {
            (void)x86os_storage_cancel(request_handle);
            return -5;
        }
        if (now >= deadline) {
            (void)x86os_storage_cancel(request_handle);
            return -110;
        }
        int32_t service_result = 0;
        status = x86os_storage_collect(request_handle, &service_result, frame);
        if (status == 0) return service_result;
        if (status != -11) {
            (void)x86os_storage_cancel(request_handle);
            return status;
        }
        if (x86os_sleep_ms(1U) != 0 && x86os_yield() != 0) {
            (void)x86os_storage_cancel(request_handle);
            return -5;
        }
    }
}

static int file_control(file_session_t *session, uint32_t operation,
                        x86os_file_info_t *info) {
    x86os_vfs_shadow_object_frame_t frame;
    file_zero(&frame, sizeof(frame));
    frame.version = X86OS_VFS_SHADOW_FRAME_VERSION;
    frame.struct_size = sizeof(frame);
    frame.operation = operation;
    frame.object_token = session->object_token;
    frame.service_generation = session->service_generation;
    int status = file_transact(&frame, session->timeout_ms);
    if (status != 0) return status;
    if (frame.version != X86OS_VFS_SHADOW_FRAME_VERSION ||
        frame.struct_size != sizeof(frame) || frame.operation != operation ||
        frame.flags != 0U || frame.path_length != 0U ||
        frame.object_token != session->object_token ||
        frame.service_generation != session->service_generation)
        return -84;
    if (frame.result != 0) return frame.result;
    if (info != 0) file_copy(info, &frame.info, sizeof(*info));
    return 0;
}

static void file_release(file_session_t *session) {
    session->object_token = 0U;
    session->service_generation = 0U;
    session->offset = 0U;
    session->timeout_ms = 0U;
    session->rights = 0U;
    session->mutation_stale = 0U;
    session->in_use = 0U;
    if (session->generation == FILE_HANDLE_GENERATION_MAX) {
        session->retired = 1U;
    } else {
        ++session->generation;
    }
}

static int file_open(const char *path, uint32_t timeout_ms, uint32_t rights,
                     uint32_t operation, uint32_t open_flags,
                     reist_vfs_file_handle_t *handle) {
    if (handle == 0 || timeout_ms == 0U || timeout_ms > 60000U ||
        rights == 0U || (rights & ~X86OS_VFS_OBJECT_RIGHT_ALL) != 0U ||
        (open_flags & ~X86OS_O_NOFOLLOW) != 0U ||
        (operation != X86OS_VFS_SHADOW_OBJECT_OPEN &&
         operation != X86OS_VFS_SHADOW_OBJECT_OPEN_RIGHTS &&
         operation != X86OS_VFS_SHADOW_OBJECT_OPEN_FLAGS) ||
        (operation != X86OS_VFS_SHADOW_OBJECT_OPEN_FLAGS &&
         open_flags != 0U)) return -22;
    *handle = REIST_VFS_FILE_INVALID_HANDLE;
    uint32_t free_slot = UINT32_MAX;
    for (uint32_t slot = 0U; slot < REIST_VFS_FILE_CAPACITY; ++slot)
        if (sessions[slot].in_use == 0U && sessions[slot].retired == 0U) {
            free_slot = slot;
            break;
        }
    if (free_slot == UINT32_MAX) return -24;
    char resolved[X86OS_VFS_SHADOW_PATH_CAPACITY];
    uint32_t length = 0U;
    int status = reist_vfs_resolve_path(path, resolved, &length);
    if (status != 0) return status;
    x86os_vfs_shadow_object_frame_t frame;
    file_zero(&frame, sizeof(frame));
    frame.version = X86OS_VFS_SHADOW_FRAME_VERSION;
    frame.struct_size = sizeof(frame);
    frame.operation = operation;
    frame.flags = operation == X86OS_VFS_SHADOW_OBJECT_OPEN ? 0U
        : rights | open_flags;
    frame.path_length = length;
    file_copy(frame.path, resolved, length + 1U);
    status = file_transact(&frame, timeout_ms);
    if (status != 0) return status;
    if (frame.version != X86OS_VFS_SHADOW_FRAME_VERSION ||
        frame.struct_size != sizeof(frame) ||
        frame.operation != operation ||
        frame.flags != (operation == X86OS_VFS_SHADOW_OBJECT_OPEN
            ? 0U : rights | open_flags) || frame.path_length != length ||
        frame.result != 0 || frame.object_token == 0U ||
        frame.service_generation == 0U) return frame.result != 0
            ? frame.result : -84;
    if (frame.info.type != X86OS_FILE) return -21;
    file_session_t *session = &sessions[free_slot];
    if (session->generation == 0U) session->generation = 1U;
    session->object_token = frame.object_token;
    session->service_generation = frame.service_generation;
    session->offset = 0U;
    session->timeout_ms = timeout_ms;
    session->rights = rights;
    session->in_use = 1U;
    *handle = file_handle(free_slot, session->generation);
    return 0;
}

int reist_vfs_file_open(const char *path, uint32_t timeout_ms,
                        reist_vfs_file_handle_t *handle) {
    return file_open(path, timeout_ms, X86OS_VFS_OBJECT_RIGHT_DATA,
                     X86OS_VFS_SHADOW_OBJECT_OPEN, 0U, handle);
}

int reist_vfs_file_open_rights(const char *path, uint32_t timeout_ms,
                               uint32_t rights,
                               reist_vfs_file_handle_t *handle) {
    return file_open(path, timeout_ms, rights,
                     X86OS_VFS_SHADOW_OBJECT_OPEN_RIGHTS, 0U, handle);
}

int reist_vfs_file_open_flags(const char *path, uint32_t timeout_ms,
                              uint32_t rights, uint32_t open_flags,
                              reist_vfs_file_handle_t *handle) {
    return file_open(path, timeout_ms, rights,
                     X86OS_VFS_SHADOW_OBJECT_OPEN_FLAGS, open_flags, handle);
}

int reist_vfs_file_read(reist_vfs_file_handle_t handle, void *data,
                        size_t capacity) {
    if (data == 0 || capacity == 0U ||
        capacity > X86OS_VFS_SHADOW_READ_CAPACITY) return -22;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    if ((session->rights & X86OS_VFS_OBJECT_RIGHT_READ) == 0U) return -13;
    x86os_vfs_shadow_object_read_frame_t frame;
    file_zero(&frame, sizeof(frame));
    frame.version = X86OS_VFS_SHADOW_FRAME_VERSION;
    frame.struct_size = sizeof(frame);
    frame.operation = X86OS_VFS_SHADOW_OBJECT_READ;
    frame.object_token = session->object_token;
    frame.service_generation = session->service_generation;
    frame.offset = session->offset;
    frame.requested = (uint32_t)capacity;
    status = file_transact(&frame, session->timeout_ms);
    if (status != 0) return status;
    if (frame.version != X86OS_VFS_SHADOW_FRAME_VERSION ||
        frame.struct_size != sizeof(frame) ||
        frame.operation != X86OS_VFS_SHADOW_OBJECT_READ ||
        frame.flags != 0U || frame.object_token != session->object_token ||
        frame.service_generation != session->service_generation ||
        frame.offset != session->offset || frame.requested != capacity ||
        frame.transferred > capacity) return -84;
    if (frame.result != 0) return frame.result;
    if (UINT32_MAX - session->offset < frame.transferred) return -75;
    file_copy(data, frame.data, frame.transferred);
    session->offset += frame.transferred;
    return (int)frame.transferred;
}

int reist_vfs_file_read_bulk(reist_vfs_file_handle_t handle, void *data,
                             size_t capacity) {
    if (data == 0 || capacity == 0U ||
        capacity > X86OS_STORAGE_BULK_MAX_BYTES) return -22;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    if ((session->rights & X86OS_VFS_OBJECT_RIGHT_READ) == 0U) return -13;

    x86os_vfs_shadow_object_bulk_read_frame_t frame;
    file_zero(&frame, sizeof(frame));
    frame.version = X86OS_VFS_SHADOW_FRAME_VERSION;
    frame.struct_size = sizeof(frame);
    frame.operation = X86OS_VFS_SHADOW_OBJECT_BULK_READ;
    frame.object_token = session->object_token;
    frame.service_generation = session->service_generation;
    frame.offset = session->offset;
    frame.requested = (uint32_t)capacity;
    x86os_storage_submit_t request = {
        .version = X86OS_STORAGE_REQUEST_VERSION,
        .struct_size = sizeof(request),
        .operation = X86OS_STORAGE_VFS_BULK_READ,
        .resource = 0U,
        .offset = 0U,
        .length = X86OS_STORAGE_BLOCK_SIZE,
        .timeout_ms = session->timeout_ms,
    };
    x86os_storage_handle_t request_handle = 0U;
    status = x86os_storage_submit(&request, &frame, &request_handle);
    if (status != 0 || request_handle == 0U)
        return status != 0 ? status : -5;
    uint64_t start = 0U;
    if (x86os_monotonic_ms(&start) != 0) {
        (void)x86os_storage_cancel(request_handle);
        return -5;
    }
    uint64_t deadline = UINT64_MAX - start < session->timeout_ms
        ? UINT64_MAX : start + session->timeout_ms;
    uint32_t transferred = 0U;
    int32_t service_result = 0;
    for (;;) {
        uint64_t now = 0U;
        if (x86os_monotonic_ms(&now) != 0 || now < start) {
            (void)x86os_storage_cancel(request_handle);
            return -5;
        }
        if (now >= deadline) {
            (void)x86os_storage_cancel(request_handle);
            return -110;
        }
        status = x86os_storage_bulk_collect(
            request_handle, &service_result, &frame, file_bulk_staging,
            (uint32_t)capacity, &transferred);
        if (status == 0) break;
        if (status != -11) {
            (void)x86os_storage_cancel(request_handle);
            return status;
        }
        if (x86os_sleep_ms(1U) != 0 && x86os_yield() != 0) {
            (void)x86os_storage_cancel(request_handle);
            return -5;
        }
    }
    if (service_result != 0) return service_result;
    if (frame.version != X86OS_VFS_SHADOW_FRAME_VERSION ||
        frame.struct_size != sizeof(frame) ||
        frame.operation != X86OS_VFS_SHADOW_OBJECT_BULK_READ ||
        frame.flags != 0U || frame.object_token != session->object_token ||
        frame.service_generation != session->service_generation ||
        frame.offset != session->offset || frame.requested != capacity ||
        frame.transferred != transferred || transferred > capacity ||
        !file_bytes_zero(frame.reserved, sizeof(frame.reserved)) ||
        frame.data_crc32 != file_crc32(file_bulk_staging, transferred))
        return -84;
    if (frame.result != 0) return frame.result;
    if (UINT32_MAX - session->offset < transferred) return -75;
    file_copy(data, file_bulk_staging, transferred);
    session->offset += transferred;
    return (int)transferred;
}

int reist_vfs_file_set_timeout(reist_vfs_file_handle_t handle,
                               uint32_t timeout_ms) {
    if (timeout_ms == 0U || timeout_ms > 60000U) return -22;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    session->timeout_ms = timeout_ms;
    return 0;
}

int reist_vfs_file_fstat(reist_vfs_file_handle_t handle,
                         x86os_file_info_t *info) {
    if (info == 0) return -22;
    file_zero(info, sizeof(*info));
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    if ((session->rights & X86OS_VFS_OBJECT_RIGHT_STAT) == 0U) return -13;
    return file_control(session, X86OS_VFS_SHADOW_OBJECT_FSTAT, info);
}

int reist_vfs_file_seek(reist_vfs_file_handle_t handle, int64_t offset,
                        uint32_t whence, uint32_t *new_offset) {
    if (new_offset == 0 || whence > REIST_VFS_SEEK_END) return -22;
    *new_offset = 0U;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    if ((session->rights & X86OS_VFS_OBJECT_RIGHT_SEEK) == 0U) return -13;
    uint32_t base = whence == REIST_VFS_SEEK_CUR ? session->offset : 0U;
    if (whence == REIST_VFS_SEEK_END) {
        x86os_file_info_t info;
        status = file_control(session, X86OS_VFS_SHADOW_OBJECT_FSTAT, &info);
        if (status != 0) return status;
        if (info.type != X86OS_FILE) return -21;
        base = info.size;
    }
    uint32_t candidate;
    if (offset >= 0) {
        uint64_t positive = (uint64_t)offset;
        if (positive > UINT32_MAX - base) return -75;
        candidate = base + (uint32_t)positive;
    } else {
        uint64_t magnitude = (uint64_t)(-(offset + 1)) + 1U;
        if (magnitude > base) return -22;
        candidate = base - (uint32_t)magnitude;
    }
    session->offset = candidate;
    *new_offset = candidate;
    return 0;
}

int reist_vfs_file_rights(reist_vfs_file_handle_t handle,
                          uint32_t *rights) {
    if (rights == 0) return -22;
    *rights = 0U;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    *rights = session->rights;
    return 0;
}

int reist_vfs_file_delegate(
        reist_vfs_file_handle_t handle,
        const x86os_process_identity_t *target, uint32_t rights) {
    if (target == 0 || target->version != 1U ||
        target->struct_size != sizeof(*target) || target->pid <= 0 ||
        target->generation == 0U || rights == 0U ||
        (rights & ~X86OS_VFS_OBJECT_RIGHT_ALL) != 0U) return -22;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    if ((session->rights & X86OS_VFS_OBJECT_RIGHT_DELEGATE) == 0U ||
        (rights & ~session->rights) != 0U) return -13;
    x86os_vfs_shadow_object_delegate_frame_t frame;
    file_zero(&frame, sizeof(frame));
    frame.version = X86OS_VFS_SHADOW_FRAME_VERSION;
    frame.struct_size = sizeof(frame);
    frame.operation = X86OS_VFS_SHADOW_OBJECT_DELEGATE;
    frame.object_token = session->object_token;
    frame.service_generation = session->service_generation;
    frame.target_pid = target->pid;
    frame.target_generation = target->generation;
    frame.rights = rights;
    status = file_transact(&frame, session->timeout_ms);
    if (status != 0) return status;
    if (frame.version != X86OS_VFS_SHADOW_FRAME_VERSION ||
        frame.struct_size != sizeof(frame) ||
        frame.operation != X86OS_VFS_SHADOW_OBJECT_DELEGATE ||
        frame.flags != 0U || frame.object_token != session->object_token ||
        frame.service_generation != session->service_generation ||
        frame.target_pid != target->pid ||
        frame.target_generation != target->generation ||
        frame.rights != rights ||
        !file_bytes_zero(frame.reserved, sizeof(frame.reserved))) return -84;
    return frame.result;
}

int reist_vfs_file_adopt(uint32_t timeout_ms,
                         reist_vfs_file_handle_t *handle) {
    if (handle == 0 || timeout_ms == 0U || timeout_ms > 60000U) return -22;
    *handle = REIST_VFS_FILE_INVALID_HANDLE;
    uint32_t free_slot = UINT32_MAX;
    for (uint32_t slot = 0U; slot < REIST_VFS_FILE_CAPACITY; ++slot)
        if (sessions[slot].in_use == 0U && sessions[slot].retired == 0U) {
            free_slot = slot;
            break;
        }
    if (free_slot == UINT32_MAX) return -24;
    x86os_vfs_shadow_object_frame_t frame;
    file_zero(&frame, sizeof(frame));
    frame.version = X86OS_VFS_SHADOW_FRAME_VERSION;
    frame.struct_size = sizeof(frame);
    frame.operation = X86OS_VFS_SHADOW_OBJECT_ADOPT;
    int status = file_transact(&frame, timeout_ms);
    if (status != 0) return status;
    if (frame.version != X86OS_VFS_SHADOW_FRAME_VERSION ||
        frame.struct_size != sizeof(frame) ||
        frame.operation != X86OS_VFS_SHADOW_OBJECT_ADOPT ||
        frame.path_length != 0U ||
        !file_bytes_zero(frame.path, sizeof(frame.path)) ||
        !file_bytes_zero(&frame.info, sizeof(frame.info)) ||
        !file_bytes_zero(frame.reserved, sizeof(frame.reserved))) return -84;
    if (frame.result != 0) return frame.result;
    if (frame.object_token == 0U || frame.service_generation == 0U ||
        frame.flags == 0U ||
        (frame.flags & ~X86OS_VFS_OBJECT_RIGHT_ALL) != 0U) return -84;
    for (uint32_t slot = 0U; slot < REIST_VFS_FILE_CAPACITY; ++slot)
        if (sessions[slot].in_use != 0U &&
            sessions[slot].object_token == frame.object_token &&
            sessions[slot].service_generation == frame.service_generation)
            return -17;
    file_session_t *session = &sessions[free_slot];
    if (session->generation == 0U) session->generation = 1U;
    session->object_token = frame.object_token;
    session->service_generation = frame.service_generation;
    session->offset = 0U;
    session->timeout_ms = timeout_ms;
    session->rights = frame.flags;
    session->in_use = 1U;
    *handle = file_handle(free_slot, session->generation);
    return 0;
}

int reist_vfs_file_close(reist_vfs_file_handle_t handle) {
    uint32_t slot = 0U;
    file_session_t *session = 0;
    int status = file_resolve(handle, &slot, &session);
    (void)slot;
    if (status != 0) return status;
    status = file_control(session, X86OS_VFS_SHADOW_OBJECT_CLOSE, 0);
    file_release(session);
    return status;
}

/* Separate optional writable support in the ELF input object. Existing read-
 * only consumers must not retain these unreferenced functions merely because
 * they share this source file. The standard linker's --gc-sections then keeps
 * the old rescue-program footprint; this grants or removes no runtime right.
 * Host GCC tests still execute all functions, without a target-only pragma. */
#if defined(__clang__)
#pragma clang section text=".text.reist_vfs_write"
#endif
static void file_write_result_init(reist_vfs_write_result_t *result) {
    file_zero(result, sizeof(*result));
    result->version = REIST_VFS_WRITE_RESULT_VERSION;
    result->struct_size = sizeof(*result);
    result->outcome = REIST_FILE_OBJECT_NO_EFFECT;
}

static void file_write_frame_init(reist_vfs_write_frame_t *frame, uint32_t operation) {
    file_zero(frame, sizeof(*frame));
    frame->version = REIST_VFS_WRITE_VERSION;
    frame->struct_size = sizeof(*frame);
    frame->operation = operation;
}

/* Validate semantics before ACK, not just the copy/CRC or envelope. A successful
 * transport alone does not say what reached stable media. This frame represents
 * ONE transaction; an UNKNOWN step cannot report any durable prefix of itself. */
static int file_write_reply_valid(const reist_vfs_write_frame_t *sent,
    const reist_vfs_write_frame_t *frame, uint32_t handle) {
    reist_vfs_write_frame_t expected;
    file_copy(&expected, sent, sizeof(expected));
    const reist_vfs_write_result_t *r = &frame->reply;
    uint32_t op = sent->operation;
    if (r->version != REIST_VFS_WRITE_RESULT_VERSION ||
        r->struct_size != sizeof(*r) || r->request != handle ||
        r->result > 0 || r->outcome < REIST_FILE_OBJECT_NO_EFFECT ||
        r->outcome > REIST_FILE_OBJECT_UNKNOWN ||
        (r->flags & ~(REIST_VFS_WRITE_SIZE_KNOWN | REIST_VFS_WRITE_DONE)) ||
        !file_bytes_zero(r->reserved, sizeof(r->reserved)) ||
        r->previous_size > UINT32_MAX || r->resulting_size > UINT32_MAX ||
        r->effective_offset > UINT32_MAX) return 0;
    if ((op == REIST_VFS_WRITE_OPEN || op == REIST_VFS_WRITE_ADOPT) && !r->result) {
        if (!frame->object_token || !frame->service_generation) return 0;
        expected.object_token = frame->object_token;
        expected.service_generation = frame->service_generation;
        if (op == REIST_VFS_WRITE_ADOPT) {
            if (!(frame->rights & REIST_VFS_WRITE_RIGHT_MUTATIONS) ||
                (frame->rights & ~REIST_VFS_WRITE_RIGHT_MASK)) return 0;
            expected.rights = frame->rights;
        }
        for (uint32_t i = 0U; i < REIST_VFS_FILE_CAPACITY; ++i)
            if (sessions[i].in_use && sessions[i].object_token == frame->object_token &&
                sessions[i].service_generation == frame->service_generation) return 0;
    }
    file_copy(&expected.reply, r, sizeof(expected.reply));
    for (uint32_t i = 0U; i < sizeof(expected); ++i)
        if (((const uint8_t *)&expected)[i] != ((const uint8_t *)frame)[i]) return 0;
    if (r->outcome == REIST_FILE_OBJECT_UNKNOWN)
        return r->result < 0 && !r->flags && !r->durable_bytes &&
            !r->released_clusters && !r->previous_size && !r->resulting_size &&
            !r->effective_offset && op >= REIST_VFS_WRITE_DATA;
    if (!(r->flags & REIST_VFS_WRITE_SIZE_KNOWN)) {
        if (r->previous_size || r->resulting_size || r->effective_offset ||
            r->outcome != REIST_FILE_OBJECT_NO_EFFECT || !r->result) return 0;
    }
    if (r->outcome == REIST_FILE_OBJECT_NO_EFFECT &&
        (r->durable_bytes || r->released_clusters || r->resulting_size != r->previous_size)) return 0;
    if (op != REIST_VFS_WRITE_RESIZE &&
        (r->released_clusters || (r->flags & REIST_VFS_WRITE_DONE))) return 0;
    if (op < REIST_VFS_WRITE_DATA)
        return r->outcome == REIST_FILE_OBJECT_NO_EFFECT && !r->effective_offset;
    if (op == REIST_VFS_WRITE_SYNC)
        return !r->durable_bytes && !r->effective_offset &&
            r->previous_size == r->resulting_size &&
            (r->result || r->outcome == REIST_FILE_OBJECT_DURABLE_COMMIT);
    if (op == REIST_VFS_WRITE_RESIZE) {
        if (r->durable_bytes || r->effective_offset) return 0;
        if (!(r->flags & REIST_VFS_WRITE_SIZE_KNOWN)) return r->flags == 0U;
        if ((r->previous_size < sent->target_size &&
             (r->resulting_size < r->previous_size || r->resulting_size > sent->target_size || r->released_clusters)) ||
            (r->previous_size == sent->target_size && r->resulting_size != sent->target_size) ||
            (r->previous_size > sent->target_size &&
             (r->resulting_size > r->previous_size || r->resulting_size < sent->target_size))) return 0;
        if ((r->flags & REIST_VFS_WRITE_DONE) && r->resulting_size != sent->target_size) return 0;
        return r->result || (r->flags & REIST_VFS_WRITE_DONE) ||
            r->resulting_size != r->previous_size || r->released_clusters;
    }
    if (op != REIST_VFS_WRITE_DATA && op != REIST_VFS_WRITE_APPEND) return 0;
    if (r->durable_bytes > sent->length) return 0;
    if (!(r->flags & REIST_VFS_WRITE_SIZE_KNOWN)) return 1;
    if (r->effective_offset != (op == REIST_VFS_WRITE_APPEND ? r->previous_size : sent->offset)) return 0;
    if (!sent->length)
        return r->outcome == REIST_FILE_OBJECT_NO_EFFECT && r->resulting_size == r->previous_size;
    if (r->durable_bytes) {
        uint64_t end = r->effective_offset + r->durable_bytes;
        uint64_t size = end > r->previous_size ? end : r->previous_size;
        /* DATA beyond EOF is a separate, explicit zero-growth step. */
        return r->outcome == REIST_FILE_OBJECT_DURABLE_COMMIT &&
            r->effective_offset <= r->previous_size && end <= UINT32_MAX && r->resulting_size == size;
    }
    if (r->resulting_size != r->previous_size)
        return op == REIST_VFS_WRITE_DATA &&
            (sent->rights & REIST_VFS_WRITE_RIGHT_RESIZE) &&
            r->outcome == REIST_FILE_OBJECT_DURABLE_COMMIT &&
            sent->offset > r->previous_size && r->resulting_size > r->previous_size &&
            r->resulting_size <= sent->offset;
    return r->result < 0;
}

typedef struct { uint64_t last, deadline; } file_write_budget_t;

static int file_write_time(file_write_budget_t *budget) {
    uint64_t now = 0U;
    if (x86os_monotonic_ms(&now) != 0 || now < budget->last) return -5;
    budget->last = now;
    return now >= budget->deadline ? -110 : 0;
}

static int file_write_budget_begin(uint32_t timeout_ms, file_write_budget_t *budget) {
    if (!timeout_ms || x86os_monotonic_ms(&budget->last) != 0) return -5;
    uint32_t bounded = timeout_ms < 5000U ? timeout_ms : 5000U;
    budget->deadline = UINT64_MAX-budget->last < bounded ? UINT64_MAX : budget->last+bounded;
    return 0;
}

static int file_write_remaining(file_write_budget_t *budget, uint32_t *remaining) {
    *remaining = 0U;
    int status = file_write_time(budget);
    if (status) return status;
    uint64_t amount = budget->deadline-budget->last;
    if (amount > 5000U) return -5;
    *remaining = (uint32_t)amount;
    return 0;
}

static int file_write_exchange(reist_vfs_write_frame_t *frame, const void *input,
    uint32_t timeout_ms, file_write_budget_t *outer_budget, reist_vfs_write_result_t *result) {
    file_write_result_init(result);
    file_write_budget_t local_budget;
    int status = outer_budget ? 0 : file_write_budget_begin(timeout_ms, &local_budget);
    if (status) { result->result = status; return status; }
    file_write_budget_t *budget = outer_budget ? outer_budget : &local_budget;
    /* One budget includes staging, submit, input copy, reply validation and ACK.
     * The kernel additionally retains its original descriptor-v3 deadline. */
    status = file_write_time(budget);
    if (status) { result->result = status; return status; }
    if (frame->length) {
        file_copy(file_bulk_staging, input, frame->length);
        frame->data_crc32 = file_crc32(file_bulk_staging, frame->length);
    }
    reist_vfs_write_frame_t sent;
    file_copy(&sent, frame, sizeof(sent));
    x86os_storage_submit_t request = {X86OS_STORAGE_REQUEST_VERSION, sizeof(request),
        X86OS_STORAGE_VFS_OBJECT_MUTATE, 0U, frame->length, sizeof(*frame), 0U};
    x86os_storage_handle_t handle = 0U;
    /* Staging consumed part of the same budget. Submit only the remaining
     * duration; do not reset it at a new short transaction or after copying. */
    status = file_write_remaining(budget, &request.timeout_ms);
    if (!status) status = x86os_storage_submit(&request, frame, &handle);
    if (status || !handle) {
        result->result = status ? status : -5;
        /* A successful submit with missing correlation cannot prove no effect. */
        if (!status) result->outcome = REIST_FILE_OBJECT_UNKNOWN;
        return result->result;
    }
    result->request = handle;
    status = file_write_time(budget);
    if (!status && frame->length)
        status = x86os_storage_input_publish(handle, file_bulk_staging, frame->length);
    while (!status) {
        status = file_write_time(budget);
        if (status) break;
        int32_t service_result = 0;
        status = x86os_storage_mutation_collect(handle, &service_result, (uint8_t *)frame);
        if (!status) {
            if (service_result) { status = service_result < 0 ? service_result : -84; break; }
            if (!file_write_reply_valid(&sent, frame, handle)) { status = -84; break; }
            status = file_write_time(budget);
            if (!status) status = x86os_storage_mutation_ack(handle);
            if (status) break;
            file_copy(result, &frame->reply, sizeof(*result));
            return result->result;
        }
        if (status != -11) break;
        status = 0;
        if (x86os_sleep_ms(1U) != 0 && x86os_yield() != 0) status = -5;
    }
    /* Cancel preserves any kernel UNKNOWN/lost-receipt fence. Do not ACK a bad
     * reply, retry, reopen, or advance a seek position from untrusted counts. */
    (void)x86os_storage_cancel(handle);
    result->result = status;
    result->outcome = REIST_FILE_OBJECT_UNKNOWN;
    return status;
}

static int file_write_free_slot(uint32_t timeout_ms, reist_vfs_file_handle_t *handle,
    uint32_t *free_slot) {
    if (!handle || !timeout_ms || timeout_ms > 60000U) return -22;
    *handle = REIST_VFS_FILE_INVALID_HANDLE;
    for (uint32_t i = 0U; i < REIST_VFS_FILE_CAPACITY; ++i)
        if (!sessions[i].in_use && !sessions[i].retired) { *free_slot = i; return 0; }
    return -24;
}

static int file_write_publish(uint32_t slot, uint32_t timeout_ms,
    const reist_vfs_write_frame_t *frame, reist_vfs_file_handle_t *handle) {
    for (uint32_t i = 0U; i < REIST_VFS_FILE_CAPACITY; ++i)
        if (sessions[i].in_use && sessions[i].object_token == frame->object_token &&
            sessions[i].service_generation == frame->service_generation) return -17;
    file_session_t *session = &sessions[slot];
    if (!session->generation) session->generation = 1U;
    session->object_token = frame->object_token;
    session->service_generation = frame->service_generation;
    session->rights = frame->rights;
    session->timeout_ms = timeout_ms;
    session->offset = 0U;
    session->mutation_stale = 0U;
    session->in_use = 1U;
    *handle = file_handle(slot, session->generation);
    return 0;
}

int reist_vfs_file_open_writable(const char *path, uint32_t timeout_ms,
    uint32_t rights, uint32_t open_flags, reist_vfs_file_handle_t *handle) {
    uint32_t slot;
    int status = file_write_free_slot(timeout_ms, handle, &slot);
    if (status) return status;
    if (!(rights & REIST_VFS_WRITE_RIGHT_MUTATIONS) ||
        (rights & ~REIST_VFS_WRITE_RIGHT_MASK) || (open_flags & ~X86OS_O_NOFOLLOW)) return -22;
    reist_vfs_write_frame_t frame;
    file_write_frame_init(&frame, REIST_VFS_WRITE_OPEN);
    frame.rights = rights;
    frame.flags = open_flags;
    status = reist_vfs_resolve_path(path, frame.path, &frame.path_length);
    if (status) return status;
    if (!frame.path_length || frame.path_length >= sizeof(frame.path) ||
        frame.path[frame.path_length] || frame.path[0] != '/') return -22;
    reist_vfs_write_result_t result;
    status = file_write_exchange(&frame, 0, timeout_ms, 0, &result);
    return status ? status : file_write_publish(slot, timeout_ms, &frame, handle);
}

int reist_vfs_file_adopt_writable(uint32_t timeout_ms, reist_vfs_file_handle_t *handle) {
    uint32_t slot;
    int status = file_write_free_slot(timeout_ms, handle, &slot);
    if (status) return status;
    reist_vfs_write_frame_t frame;
    file_write_frame_init(&frame, REIST_VFS_WRITE_ADOPT);
    reist_vfs_write_result_t result;
    status = file_write_exchange(&frame, 0, timeout_ms, 0, &result);
    return status ? status : file_write_publish(slot, timeout_ms, &frame, handle);
}

int reist_vfs_file_delegate_writable(reist_vfs_file_handle_t handle,
    const x86os_process_identity_t *target, uint32_t rights) {
    if (!target || target->version != 1U || target->struct_size != sizeof(*target) ||
        target->pid <= 0 || !target->generation || !(rights & REIST_VFS_WRITE_RIGHT_MUTATIONS) ||
        (rights & ~REIST_VFS_WRITE_RIGHT_MASK)) return -22;
    uint32_t slot;
    file_session_t *session;
    int status = file_resolve(handle, &slot, &session);
    if (status) return status;
    if (session->mutation_stale) return -116;
    if (!(session->rights & X86OS_VFS_OBJECT_RIGHT_DELEGATE) ||
        (rights & ~session->rights)) return -13;
    reist_vfs_write_frame_t frame;
    file_write_frame_init(&frame, REIST_VFS_WRITE_DELEGATE);
    frame.object_token = session->object_token;
    frame.service_generation = session->service_generation;
    frame.rights = rights;
    frame.target_pid = target->pid;
    frame.target_generation = target->generation;
    reist_vfs_write_result_t result;
    status = file_write_exchange(&frame, 0, session->timeout_ms, 0, &result);
    if (result.outcome == REIST_FILE_OBJECT_UNKNOWN) session->mutation_stale = 1U;
    return status;
}

static int file_write_step(reist_vfs_file_handle_t handle, uint32_t operation,
    const void *input, size_t length, uint64_t offset, uint64_t target,
    int advance, file_write_budget_t *budget, reist_vfs_write_result_t *result) {
    if (!result) return -22;
    file_write_result_init(result);
    int status = 0;
    uint32_t slot = 0U;
    file_session_t *session = 0;
    if (length > X86OS_STORAGE_BULK_MAX_BYTES || (length && !input)) status = -22;
    else if (offset > UINT32_MAX || length > UINT32_MAX - offset || target > UINT32_MAX) status = -75;
    else status = file_resolve(handle, &slot, &session);
    uint32_t right = operation == REIST_VFS_WRITE_DATA ? REIST_VFS_WRITE_RIGHT_WRITE :
        operation == REIST_VFS_WRITE_APPEND ? REIST_VFS_WRITE_RIGHT_APPEND :
        operation == REIST_VFS_WRITE_RESIZE ? REIST_VFS_WRITE_RIGHT_RESIZE : REIST_VFS_WRITE_RIGHT_SYNC;
    if (!status && session->mutation_stale) status = -116;
    if (!status && !(session->rights & right)) status = -13;
    if (!status && advance && operation == REIST_VFS_WRITE_DATA) {
        offset = session->offset;
        if (length > UINT32_MAX - offset) status = -75;
    }
    if (status) { result->result = status; return status; }
    reist_vfs_write_frame_t frame;
    file_write_frame_init(&frame, operation);
    frame.object_token = session->object_token;
    frame.service_generation = session->service_generation;
    frame.rights = session->rights;
    frame.offset = offset;
    frame.target_size = target;
    frame.length = (uint32_t)length;
    status = file_write_exchange(&frame, input, session->timeout_ms, budget, result);
    if (result->outcome == REIST_FILE_OBJECT_UNKNOWN) session->mutation_stale = 1U;
    else if (advance && result->durable_bytes)
        session->offset = (uint32_t)(result->effective_offset + result->durable_bytes);
    return status;
}

int reist_vfs_file_write_step(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_write_result_t *result) {
    return file_write_step(handle, REIST_VFS_WRITE_DATA, data, length, 0U, 0U, 1, 0, result);
}
int reist_vfs_file_pwrite_step(reist_vfs_file_handle_t handle, const void *data,
    size_t length, uint64_t offset, reist_vfs_write_result_t *result) {
    return file_write_step(handle, REIST_VFS_WRITE_DATA, data, length, offset, 0U, 0, 0, result);
}
int reist_vfs_file_append_step(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_write_result_t *result) {
    return file_write_step(handle, REIST_VFS_WRITE_APPEND, data, length, 0U, 0U, 1, 0, result);
}
int reist_vfs_file_resize_step(reist_vfs_file_handle_t handle, uint64_t target,
    reist_vfs_write_result_t *result) {
    return file_write_step(handle, REIST_VFS_WRITE_RESIZE, 0, 0U, 0U, target, 0, 0, result);
}
int reist_vfs_file_fsync(reist_vfs_file_handle_t handle, reist_vfs_write_result_t *result) {
    return file_write_step(handle, REIST_VFS_WRITE_SYNC, 0, 0U, 0U, 0U, 0, 0, result);
}

static int file_progress_error(reist_vfs_file_progress_t *p, int status) {
    file_write_result_init(&p->last);
    p->last.result = p->result = status;
    return status;
}

static void file_progress_add(reist_vfs_file_progress_t *p, const reist_vfs_write_result_t *r) {
    file_copy(&p->last, r, sizeof(p->last));
    p->result = r->result;
    if (r->outcome == REIST_FILE_OBJECT_UNKNOWN) { p->outcome = r->outcome; return; }
    if (r->outcome == REIST_FILE_OBJECT_DURABLE_COMMIT) p->outcome = r->outcome;
    if (r->flags & REIST_VFS_WRITE_SIZE_KNOWN) {
        if (!(p->flags & REIST_VFS_FILE_PROGRESS_SIZE_KNOWN)) p->initial_size = r->previous_size;
        p->durable_size = r->resulting_size;
        p->flags |= REIST_VFS_FILE_PROGRESS_SIZE_KNOWN;
    }
    if (r->durable_bytes && !(p->flags & REIST_VFS_FILE_PROGRESS_OFFSET_KNOWN)) {
        p->first_offset = r->effective_offset;
        p->flags |= REIST_VFS_FILE_PROGRESS_OFFSET_KNOWN;
    }
    p->durable_bytes += r->durable_bytes;
    p->released_clusters += r->released_clusters;
}

static int file_write_bounded(reist_vfs_file_handle_t handle, uint32_t operation,
    const void *input, size_t length, uint64_t offset, uint64_t target, int advance,
    reist_vfs_file_progress_t *progress) {
    if (!progress) return -22;
    file_zero(progress, sizeof(*progress));
    progress->version = REIST_VFS_FILE_PROGRESS_VERSION;
    progress->struct_size = sizeof(*progress);
    progress->outcome = REIST_FILE_OBJECT_NO_EFFECT;
    if (length && !input) return file_progress_error(progress, -22);
    if (length > UINT32_MAX || offset > UINT32_MAX || target > UINT32_MAX)
        return file_progress_error(progress, -75);
    uint32_t slot;
    file_session_t *session;
    int status = file_resolve(handle, &slot, &session);
    if (status) return file_progress_error(progress, status);
    if (session->mutation_stale) return file_progress_error(progress, -116);
    if (operation == REIST_VFS_WRITE_DATA && advance) offset = session->offset;
    if (length > UINT32_MAX-offset) return file_progress_error(progress, -75);
    uint32_t right = operation == REIST_VFS_WRITE_DATA ? REIST_VFS_WRITE_RIGHT_WRITE :
        operation == REIST_VFS_WRITE_APPEND ? REIST_VFS_WRITE_RIGHT_APPEND : REIST_VFS_WRITE_RIGHT_RESIZE;
    if (!(session->rights & right)) return file_progress_error(progress, -13);
    file_write_budget_t budget;
    status = file_write_budget_begin(session->timeout_ms, &budget);
    if (status) return file_progress_error(progress, status);
    for (;;) {
        status = file_write_time(&budget);
        if (status) return file_progress_error(progress, status);
        if (progress->steps == UINT32_MAX) return file_progress_error(progress, -75);
        uint64_t remaining = length-progress->durable_bytes;
        uint32_t amount = remaining > X86OS_STORAGE_BULK_MAX_BYTES ? X86OS_STORAGE_BULK_MAX_BYTES : (uint32_t)remaining;
        uint64_t position = operation == REIST_VFS_WRITE_DATA ? offset+progress->durable_bytes : 0U;
        const uint8_t *data = amount ? (const uint8_t *)input+(size_t)progress->durable_bytes : 0;
        reist_vfs_write_result_t step;
        ++progress->steps;
        status = file_write_step(handle, operation, data, amount, position, target, advance, &budget, &step);
        file_progress_add(progress, &step);
        /* Only confirmed progress is continued; every error/UNKNOWN stops.
         * No NO_EFFECT retry, new handle, renewed timeout, or hidden resize. */
        if (status) return status;
        if (operation == REIST_VFS_WRITE_RESIZE ? (step.flags & REIST_VFS_WRITE_DONE) != 0U :
            progress->durable_bytes == length) {
            progress->flags |= REIST_VFS_FILE_PROGRESS_COMPLETE;
            return 0;
        }
        /* Reply validation already excludes zero-progress success. Keep a
         * local invariant so a future wire extension cannot add a busy loop. */
        if (!step.durable_bytes && !step.released_clusters && step.resulting_size == step.previous_size)
            return file_progress_error(progress, -84);
    }
}

int reist_vfs_file_write_bounded(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_file_progress_t *progress) {
    return file_write_bounded(handle, REIST_VFS_WRITE_DATA, data, length, 0U, 0U, 1, progress);
}
int reist_vfs_file_pwrite_bounded(reist_vfs_file_handle_t handle, const void *data,
    size_t length, uint64_t offset, reist_vfs_file_progress_t *progress) {
    return file_write_bounded(handle, REIST_VFS_WRITE_DATA, data, length, offset, 0U, 0, progress);
}
int reist_vfs_file_append_bounded(reist_vfs_file_handle_t handle, const void *data,
    size_t length, reist_vfs_file_progress_t *progress) {
    return file_write_bounded(handle, REIST_VFS_WRITE_APPEND, data, length, 0U, 0U, 1, progress);
}
int reist_vfs_file_resize_bounded(reist_vfs_file_handle_t handle, uint64_t target,
    reist_vfs_file_progress_t *progress) {
    return file_write_bounded(handle, REIST_VFS_WRITE_RESIZE, 0, 0U, 0U, target, 0, progress);
}
#if defined(__clang__)
#pragma clang section text=""
#endif
