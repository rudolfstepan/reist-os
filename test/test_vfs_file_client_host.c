/** Host behavior test for stable service-owned VFS read objects. */
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "userspace/storage/include/reist/vfs_file_client.h"

static int cwd_variant;
static int stat_failure;
static int read_failure;
static uint32_t observed_offset;
static uint32_t open_calls;
static uint32_t close_calls;
static uint32_t delegate_calls;
static uint32_t delegated_rights;
static uint32_t observed_timeout;
static int delegation_pending;
static int bulk_corrupt;
static uint32_t next_request = 1U;
static char opened_path[X86OS_VFS_SHADOW_PATH_CAPACITY];

#ifdef R342_WRITE_CLIENT_TEST
#include "write_service_validator.inc"
static reist_vfs_write_frame_t write_request;
static uint32_t write_handle, write_submits, write_publishes, write_acks, write_cancels;
static uint32_t write_mode, write_size = 10U, write_limit = 3U;
static uint64_t clock_now;
static uint32_t clock_step = 1U;
static uint32_t clock_calls, clock_fault_at, clock_fault_kind;
static int stream_active;
static uint32_t stream_calls, stream_fail_at, stream_fail_mode, stream_published, stream_acked;
static uint32_t stream_last_timeout, stream_committed, stream_gap;
static uint64_t stream_deadline;
static const uint8_t *stream_input;
static uint32_t stream_length;
static unsigned write_checks;
#define C_CHECK(x) do { ++write_checks; if (!(x)) { fprintf(stderr, "write-client:%d: %s\n", __LINE__, #x); exit(1); } } while (0)
static int write_submit(const x86os_storage_submit_t *request, const void *data,
                        x86os_storage_handle_t *handle) {
    C_CHECK(request->length == 512U && request->resource == 0U);
    write_request = *(const reist_vfs_write_frame_t *)data;
    C_CHECK(write_request.version == REIST_VFS_WRITE_VERSION);
    C_CHECK(write_request.struct_size == 512U && request->offset == write_request.length);
    C_CHECK(write_request.reply.version == 0U && write_request.reply.request == 0U);
    x86os_storage_descriptor_v3_t d = {3U, sizeof(d), 1U, 35U, 0U, request->offset,
        512U, 20, 3U, 9U, 5000U};
    C_CHECK(vfs_write_frame_valid(&write_request, &d) == 0);
    observed_timeout = request->timeout_ms;
    if (stream_active) {
        C_CHECK(request->timeout_ms > 0U && request->timeout_ms <= stream_last_timeout);
        C_CHECK(clock_now+request->timeout_ms <= stream_deadline);
        stream_last_timeout = request->timeout_ms;
        ++stream_calls;
        if (stream_calls == stream_fail_at) write_mode = stream_fail_mode;
    }
    ++write_submits;
    if (write_mode == 40U) return -13;
    *handle = write_handle = next_request++;
    return 0;
}
#endif

uintptr_t x86os_syscall(uint32_t number, uintptr_t a, uintptr_t b, uintptr_t c) {
#ifdef R342_WRITE_CLIENT_TEST
    C_CHECK(number == X86OS_SYS_STORAGE_BULK);
    x86os_storage_bulk_control_t *control = (void *)a;
    C_CHECK(control->struct_size == sizeof(*control) && control->handle == write_handle);
    if (control->operation == X86OS_STORAGE_BULK_INPUT_PUBLISH) {
        C_CHECK(control->version == 2U && b == 0U && c != 0U);
        C_CHECK(control->length == write_request.length);
        if (stream_active) {
            C_CHECK(stream_committed <= stream_length && control->length <= stream_length-stream_committed);
            C_CHECK(!memcmp((const void *)c, stream_input+stream_committed, control->length));
            ++stream_published;
        }
        ++write_publishes;
        return write_mode == 41U ? (uintptr_t)-5 : 0U;
    }
    C_CHECK(control->version == 3U && c == 0U);
    if (control->operation == X86OS_STORAGE_BULK_RECEIPT_ACK) {
        C_CHECK(b == 0U);
        ++write_acks;
        if (stream_active && write_mode != 42U) ++stream_acked;
        return write_mode == 42U ? (uintptr_t)-110 : 0U;
    }
    C_CHECK(control->operation == X86OS_STORAGE_BULK_RECEIPT_COLLECT && b != 0U);
    if (write_mode == 43U) return (uintptr_t)-11;
    if (write_mode == 44U) { control->result = -5; return 0U; }
    reist_vfs_write_frame_t *frame = (void *)b;
    *frame = write_request;
    reist_vfs_write_result_t *reply = &frame->reply;
    reply->version = REIST_VFS_WRITE_RESULT_VERSION;
    reply->struct_size = sizeof(*reply);
    reply->request = write_handle;
    reply->outcome = REIST_FILE_OBJECT_NO_EFFECT;
    reply->flags = REIST_VFS_WRITE_SIZE_KNOWN;
    reply->previous_size = reply->resulting_size = write_size;
    if (frame->operation == REIST_VFS_WRITE_OPEN || frame->operation == REIST_VFS_WRITE_ADOPT) {
        frame->object_token = 77U; frame->service_generation = 9U;
        if (frame->operation == REIST_VFS_WRITE_ADOPT) frame->rights = REIST_VFS_WRITE_RIGHT_APPEND;
    } else if (frame->operation == REIST_VFS_WRITE_DATA || frame->operation == REIST_VFS_WRITE_APPEND) {
        reply->effective_offset = frame->operation == REIST_VFS_WRITE_APPEND ? write_size : frame->offset;
        reply->durable_bytes = frame->length < write_limit ? frame->length : write_limit;
        if (reply->durable_bytes) reply->outcome = REIST_FILE_OBJECT_DURABLE_COMMIT;
        uint64_t end = reply->effective_offset + reply->durable_bytes;
        if (reply->durable_bytes && end > write_size) reply->resulting_size = end;
        if (stream_active && frame->operation == REIST_VFS_WRITE_DATA && frame->offset > write_size && frame->length) {
            reply->durable_bytes = 0U;
            reply->resulting_size = frame->offset-write_size > stream_gap ? write_size+stream_gap : frame->offset;
        }
    } else if (frame->operation == REIST_VFS_WRITE_RESIZE) {
        reply->resulting_size = frame->target_size;
        reply->outcome = REIST_FILE_OBJECT_DURABLE_COMMIT;
        reply->flags |= REIST_VFS_WRITE_DONE;
        if (stream_active && frame->target_size < write_size && write_size-frame->target_size > stream_gap) {
            reply->resulting_size = write_size-stream_gap;
            reply->released_clusters = 1U;
            reply->flags &= ~REIST_VFS_WRITE_DONE;
        }
    } else if (frame->operation == REIST_VFS_WRITE_SYNC) {
        reply->outcome = REIST_FILE_OBJECT_DURABLE_COMMIT;
    }
    /* One semantic corruption at a time: none may be acknowledged. */
    switch (write_mode) {
        case 1: frame->version++; break;
        case 2: frame->struct_size--; break;
        case 3: frame->operation++; break;
        case 4: frame->flags++; break;
        case 5: frame->object_token++; break;
        case 6: frame->service_generation++; break;
        case 7: frame->rights++; break;
        case 8: frame->offset++; break;
        case 9: frame->length++; break;
        case 10: frame->data_crc32++; break;
        case 11: frame->reserved[47]++; break;
        case 12: reply->version++; break;
        case 13: reply->struct_size--; break;
        case 14: reply->request++; break;
        case 15: reply->result = 1; break;
        case 16: reply->outcome = 0; break;
        case 17: reply->flags |= 128U; break;
        case 18: reply->durable_bytes = frame->length + 1U; break;
        case 19: reply->released_clusters = 1U; break;
        case 20: reply->effective_offset++; break;
        case 21: reply->resulting_size = UINT64_MAX; break;
        case 22: reply->reserved[1]++; break;
        case 23: reply->outcome = REIST_FILE_OBJECT_NO_EFFECT; break;
        case 24: reply->outcome = REIST_FILE_OBJECT_UNKNOWN; break;
        case 25: reply->flags = 0U; break;
        case 26: reply->previous_size = UINT64_MAX; break;
        case 27: reply->resulting_size = 0U; break;
        case 28: reply->flags |= REIST_VFS_WRITE_DONE; break;
        case 30: reply->result = -28; reply->outcome = REIST_FILE_OBJECT_NO_EFFECT;
                 reply->durable_bytes = 0U; reply->resulting_size = write_size; break;
        case 31: reply->result = -5; reply->outcome = REIST_FILE_OBJECT_UNKNOWN;
                 reply->durable_bytes = 0U; reply->flags = 0U;
                 reply->previous_size = reply->resulting_size = reply->effective_offset = 0U; break;
        case 32: reply->result = -116; break; /* committed, then locator refresh failed */
        case 33: reply->durable_bytes = 0U; reply->resulting_size = write_size;
                 reply->outcome = REIST_FILE_OBJECT_NO_EFFECT; break; /* invalid stalled success */
    }
    control->result = 0;
    if (stream_active && (!write_mode || write_mode == 32U || write_mode == 42U)) {
        write_size = (uint32_t)reply->resulting_size;
        stream_committed += reply->durable_bytes;
    }
    return 0U;
#else
    (void)number; (void)a; (void)b; (void)c;
    return (uintptr_t)-95;
#endif
}

int reist_vfs_resolve_path(const char *path, char *output, uint32_t *length) {
    if (path == 0 || output == 0 || length == 0) return -22;
    const char *resolved = path[0] == '/' ? path :
        (cwd_variant == 0 ? "/A/FILE.TXT" : "/B/FILE.TXT");
    size_t amount = strlen(resolved);
    if (amount >= X86OS_VFS_SHADOW_PATH_CAPACITY) return -36;
    memcpy(output, resolved, amount + 1U);
    *length = (uint32_t)amount;
    return 0;
}

int x86os_storage_submit(const x86os_storage_submit_t *request,
                         const void *data, x86os_storage_handle_t *handle) {
#ifdef R342_WRITE_CLIENT_TEST
    if (request && request->operation == X86OS_STORAGE_VFS_OBJECT_MUTATE)
        return write_submit(request, data, handle);
#endif
    if (request == 0 || data == 0 || handle == 0 ||
        (request->operation != X86OS_STORAGE_VFS_SHADOW_STAT &&
         request->operation != X86OS_STORAGE_VFS_BULK_READ) ||
        request->length != X86OS_STORAGE_BLOCK_SIZE) return -22;
    observed_timeout = request->timeout_ms;
    uint32_t operation = ((const x86os_vfs_shadow_object_frame_t *)data)->operation;
    if (request->operation == X86OS_STORAGE_VFS_BULK_READ) {
        if (operation != X86OS_VFS_SHADOW_OBJECT_BULK_READ) return -22;
        *handle = next_request++;
        return 0;
    }
    if (operation == X86OS_VFS_SHADOW_OBJECT_READ) {
        x86os_vfs_shadow_object_read_frame_t *frame =
            (x86os_vfs_shadow_object_read_frame_t *)(uintptr_t)data;
        if ((frame->object_token != 77U && frame->object_token != 88U) ||
            frame->service_generation != 9U)
            return -9;
        observed_offset = frame->offset;
        if (read_failure) {
            frame->result = -5;
        } else {
            uint32_t remaining = frame->offset < 10U
                ? 10U - frame->offset : 0U;
            frame->transferred = remaining < frame->requested
                ? remaining : frame->requested;
            for (uint32_t index = 0U; index < frame->transferred; ++index)
                frame->data[index] = (uint8_t)('0' + frame->offset + index);
        }
    } else if (operation == X86OS_VFS_SHADOW_OBJECT_DELEGATE) {
        x86os_vfs_shadow_object_delegate_frame_t *frame =
            (x86os_vfs_shadow_object_delegate_frame_t *)(uintptr_t)data;
        if (frame->object_token != 77U || frame->service_generation != 9U ||
            frame->target_pid != 42 || frame->target_generation != 7U ||
            frame->rights == 0U) return -22;
        delegated_rights = frame->rights;
        delegation_pending = 1;
        ++delegate_calls;
    } else {
        x86os_vfs_shadow_object_frame_t *frame =
            (x86os_vfs_shadow_object_frame_t *)(uintptr_t)data;
        if (operation == X86OS_VFS_SHADOW_OBJECT_OPEN ||
            operation == X86OS_VFS_SHADOW_OBJECT_OPEN_RIGHTS) {
            ++open_calls;
            strcpy(opened_path, frame->path);
            if (strstr(frame->path, "DIR") != 0) {
                frame->result = -21;
            } else {
                frame->object_token = 77U;
                frame->service_generation = 9U;
                frame->info.type = X86OS_FILE;
                frame->info.size = 10U;
                strcpy(frame->info.name, "FILE.TXT");
            }
        } else if (operation == X86OS_VFS_SHADOW_OBJECT_ADOPT) {
            if (!delegation_pending) {
                frame->result = -11;
            } else {
                delegation_pending = 0;
                frame->object_token = 88U;
                frame->service_generation = 9U;
                frame->flags = delegated_rights;
            }
        } else if (operation == X86OS_VFS_SHADOW_OBJECT_FSTAT) {
            if ((frame->object_token != 77U && frame->object_token != 88U) ||
                frame->service_generation != 9U)
                return -9;
            if (stat_failure) {
                frame->result = -2;
            } else {
                frame->info.type = X86OS_FILE;
                frame->info.size = 10U;
            }
        } else if (operation == X86OS_VFS_SHADOW_OBJECT_CLOSE) {
            if ((frame->object_token != 77U && frame->object_token != 88U) ||
                frame->service_generation != 9U)
                return -9;
            ++close_calls;
        } else {
            return -22;
        }
    }
    *handle = next_request++;
    return 0;
}

int x86os_storage_collect(x86os_storage_handle_t handle, int32_t *result,
                          void *data) {
    (void)data;
    if (handle == 0U || result == 0) return -22;
    *result = 0;
    return 0;
}

int x86os_storage_cancel(x86os_storage_handle_t handle) {
#ifdef R342_WRITE_CLIENT_TEST
    if (handle == write_handle) ++write_cancels;
#endif
    return handle == 0U ? -22 : 0;
}

static uint32_t test_crc32(const uint8_t *data, uint32_t length) {
    uint32_t crc = 0xFFFFFFFFU;
    for (uint32_t index = 0U; index < length; ++index) {
        crc ^= data[index];
        for (uint32_t bit = 0U; bit < 8U; ++bit)
            crc = (crc >> 1U) ^ (0xEDB88320U &
                  (uint32_t)-(int32_t)(crc & 1U));
    }
    return crc ^ 0xFFFFFFFFU;
}

int x86os_storage_bulk_collect(x86os_storage_handle_t handle,
        int32_t *result, void *frame_data, void *data, uint32_t capacity,
        uint32_t *transferred) {
    if (handle == 0U || result == 0 || frame_data == 0 || data == 0 ||
        transferred == 0) return -22;
    x86os_vfs_shadow_object_bulk_read_frame_t *frame = frame_data;
    observed_offset = frame->offset;
    uint32_t remaining = frame->offset < 10U ? 10U - frame->offset : 0U;
    uint32_t amount = remaining < frame->requested
        ? remaining : frame->requested;
    if (amount > capacity) return -90;
    for (uint32_t index = 0U; index < amount; ++index)
        ((uint8_t *)data)[index] = (uint8_t)('0' + frame->offset + index);
    frame->transferred = amount;
    frame->data_crc32 = test_crc32(data, amount) ^
        (bulk_corrupt ? 1U : 0U);
    *result = 0;
    *transferred = amount;
    return 0;
}

int x86os_monotonic_ms(uint64_t *value) {
#ifdef R342_WRITE_CLIENT_TEST
    if (!value) return -22;
    if (++clock_calls == clock_fault_at) {
        if (clock_fault_kind == 1U) return -5;
        *value = --clock_now; /* also test regressions still above the start */
        return 0;
    }
    clock_now += clock_step;
    *value = clock_now;
    return 0;
#else
    static uint64_t now;
    if (value == 0) return -22;
    *value = ++now;
    return 0;
#endif
}

int x86os_sleep_ms(uint32_t milliseconds) {
    return milliseconds == 0U ? -22 : 0;
}

int x86os_yield(void) { return 0; }

static int read_tests(void) {
    reist_vfs_file_handle_t first = 0U;
    uint8_t data[3];
    if (reist_vfs_file_open("FILE.TXT", 1000U, &first) != 0 || first == 0U ||
        strcmp(opened_path, "/A/FILE.TXT") != 0) return 1;
    if (reist_vfs_file_set_timeout(first, 17U) != 0 ||
        reist_vfs_file_set_timeout(first, 0U) != -22 ||
        reist_vfs_file_set_timeout(first, 60001U) != -22 ||
        reist_vfs_file_set_timeout(0U, 17U) != -9) return 25;
    cwd_variant = 1;
    if (reist_vfs_file_read(first, data, sizeof(data)) != 3 ||
        observed_offset != 0U || strcmp(opened_path, "/A/FILE.TXT") != 0 ||
        memcmp(data, "012", 3U) != 0 || observed_timeout != 17U) return 2;
    if (reist_vfs_file_read(first, data, sizeof(data)) != 3 ||
        observed_offset != 3U || memcmp(data, "345", 3U) != 0) return 3;

    uint32_t position = 99U;
    if (reist_vfs_file_seek(first, 2, REIST_VFS_SEEK_SET, &position) != 0 ||
        position != 2U) return 4;
    if (reist_vfs_file_read(first, data, sizeof(data)) != 3 ||
        observed_offset != 2U) return 5;
    if (reist_vfs_file_seek(first, -1, REIST_VFS_SEEK_CUR, &position) != 0 ||
        position != 4U) return 6;
    if (reist_vfs_file_seek(first, -2, REIST_VFS_SEEK_END, &position) != 0 ||
        position != 8U) return 7;
    stat_failure = 1;
    if (reist_vfs_file_seek(first, 0, REIST_VFS_SEEK_END, &position) != -2)
        return 8;
    stat_failure = 0;
    read_failure = 1;
    if (reist_vfs_file_read(first, data, sizeof(data)) != -5 ||
        observed_offset != 8U) return 9;
    read_failure = 0;
    if (reist_vfs_file_read(first, data, sizeof(data)) != 2 ||
        observed_offset != 8U) return 10;
    uint8_t bulk[10];
    if (reist_vfs_file_seek(first, 0, REIST_VFS_SEEK_SET, &position) != 0 ||
        reist_vfs_file_read_bulk(first, bulk, sizeof(bulk)) != 10 ||
        memcmp(bulk, "0123456789", sizeof(bulk)) != 0) return 21;
    if (reist_vfs_file_seek(first, 0, REIST_VFS_SEEK_SET, &position) != 0)
        return 22;
    bulk_corrupt = 1;
    if (reist_vfs_file_read_bulk(first, bulk, sizeof(bulk)) != -84) return 23;
    bulk_corrupt = 0;
    if (reist_vfs_file_read(first, data, sizeof(data)) != 3 ||
        observed_offset != 0U) return 24;
    x86os_file_info_t info;
    if (reist_vfs_file_fstat(first, &info) != 0 || info.size != 10U)
        return 11;
    uint32_t rights = 0U;
    x86os_process_identity_t target = {1U, sizeof(target), 42, 7U};
    if (reist_vfs_file_rights(first, &rights) != 0 ||
        rights != REIST_VFS_FILE_RIGHT_DATA ||
        reist_vfs_file_delegate(first, &target,
                                REIST_VFS_FILE_RIGHT_READ) != -13)
        return 18;
    if (reist_vfs_file_seek(first, -11, REIST_VFS_SEEK_END, &position) != -22 ||
        reist_vfs_file_seek(first, INT64_MAX, REIST_VFS_SEEK_CUR,
                            &position) != -75) return 12;
    if (reist_vfs_file_close(first) != 0 || close_calls != 1U ||
        reist_vfs_file_read(first, data, sizeof(data)) != -9 ||
        reist_vfs_file_close(first) != -9) return 13;

    reist_vfs_file_handle_t source = REIST_VFS_FILE_INVALID_HANDLE;
    reist_vfs_file_handle_t adopted = REIST_VFS_FILE_INVALID_HANDLE;
    if (reist_vfs_file_open_rights(
            "FILE.TXT", 1000U, REIST_VFS_FILE_RIGHT_ALL, &source) != 0 ||
        reist_vfs_file_delegate(source, &target,
                                REIST_VFS_FILE_RIGHT_READ) != 0 ||
        delegate_calls != 1U ||
        reist_vfs_file_adopt(1000U, &adopted) != 0 || adopted == 0U ||
        reist_vfs_file_rights(adopted, &rights) != 0 ||
        rights != REIST_VFS_FILE_RIGHT_READ ||
        reist_vfs_file_read(adopted, data, 1U) != 1 ||
        reist_vfs_file_fstat(adopted, &info) != -13 ||
        reist_vfs_file_seek(adopted, 0, REIST_VFS_SEEK_SET, &position) != -13)
        return 19;
    reist_vfs_file_handle_t duplicate = 99U;
    if (reist_vfs_file_adopt(1000U, &duplicate) != -11 || duplicate != 0U ||
        reist_vfs_file_close(adopted) != 0 ||
        reist_vfs_file_fstat(source, &info) != 0 ||
        reist_vfs_file_close(source) != 0) return 20;

    reist_vfs_file_handle_t handles[REIST_VFS_FILE_CAPACITY];
    for (uint32_t index = 0U; index < REIST_VFS_FILE_CAPACITY; ++index)
        if (reist_vfs_file_open("FILE.TXT", 1000U, &handles[index]) != 0)
            return 14;
    reist_vfs_file_handle_t excess = 123U;
    uint32_t calls_before_excess = open_calls;
    if (reist_vfs_file_open("FILE.TXT", 1000U, &excess) != -24 ||
        excess != REIST_VFS_FILE_INVALID_HANDLE ||
        open_calls != calls_before_excess) return 15;
    for (uint32_t index = 0U; index < REIST_VFS_FILE_CAPACITY; ++index)
        if (reist_vfs_file_close(handles[index]) != 0) return 16;
    if (reist_vfs_file_open("/DIR", 1000U, &excess) != -21) return 17;
    return 0;
}

#ifdef R342_WRITE_CLIENT_TEST
static void stream_begin(const uint8_t *data, uint32_t length, uint32_t timeout) {
    stream_active = 1; stream_calls = stream_published = stream_committed = stream_acked = 0U;
    stream_fail_at = stream_fail_mode = 0U; stream_last_timeout = timeout < 5000U ? timeout : 5000U;
    stream_deadline = clock_now + clock_step + stream_last_timeout;
    stream_input = data; stream_length = length; stream_gap = 7U;
}
static void stream_tests(void) {
    static uint8_t payload[2U*1024U*1024U+17U];
    for (uint32_t i = 0U; i < sizeof(payload); ++i) payload[i] = (uint8_t)(i*7U+i/256U);
    reist_vfs_file_handle_t handle;
    reist_vfs_file_progress_t progress;
    uint32_t position;
    uint32_t rights = REIST_VFS_FILE_RIGHT_ALL | REIST_VFS_WRITE_RIGHT_MUTATIONS;
    C_CHECK(sizeof(progress) == 128U);
    for (unsigned op = 0U; op < 3U; ++op) {
        stream_active = 0; write_mode = 0; write_size = 10U; write_limit = 10000U;
        C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 60000U, rights, 0U, &handle));
        stream_begin(payload, sizeof(payload), 60000U); /* still capped at5000ms */
        int result = op == 0U ? reist_vfs_file_write_bounded(handle, payload, sizeof(payload), &progress) :
            op == 1U ? reist_vfs_file_pwrite_bounded(handle, payload, sizeof(payload), 0U, &progress) :
                       reist_vfs_file_append_bounded(handle, payload, sizeof(payload), &progress);
        C_CHECK(result == 0 && progress.result == 0 && progress.version == REIST_VFS_FILE_PROGRESS_VERSION);
        C_CHECK(progress.durable_bytes == sizeof(payload) && progress.outcome == REIST_FILE_OBJECT_DURABLE_COMMIT);
        C_CHECK(progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE);
        C_CHECK(progress.first_offset == (op == 2U ? 10U : 0U) && progress.initial_size == 10U);
        C_CHECK(progress.durable_size == sizeof(payload)+(op == 2U ? 10U : 0U));
        C_CHECK(stream_calls > 200U && stream_calls == stream_published && stream_calls == stream_acked);
        C_CHECK(progress.steps == stream_calls);
        stream_active = 0;
        C_CHECK(!reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position));
        C_CHECK(position == (op == 1U ? 0U : sizeof(payload)+(op == 2U ? 10U : 0U)));
        C_CHECK(!reist_vfs_file_close(handle));
    }
    for (unsigned mode = 30U; mode <= 44U; ++mode) {
        if (mode > 31U && mode < 40U) continue;
        write_mode = 0; write_size = 10U; write_limit = 3U;
        C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
        stream_begin(payload, 10U, 300U); stream_fail_at = 3U; stream_fail_mode = mode;
        int result = reist_vfs_file_write_bounded(handle, payload, 10U, &progress);
        C_CHECK(result < 0 && result == progress.result);
        C_CHECK(progress.durable_bytes == 6U && progress.durable_size == 10U && progress.initial_size == 10U);
        C_CHECK(progress.outcome == (mode == 30U || mode == 40U ? REIST_FILE_OBJECT_DURABLE_COMMIT : REIST_FILE_OBJECT_UNKNOWN));
        C_CHECK(!(progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE) && progress.steps == 3U && stream_calls == 3U);
        C_CHECK(progress.last.durable_bytes == 0U && progress.last.result == result);
        stream_active = 0; write_mode = 0;
        C_CHECK(!reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) && position == 6U);
        C_CHECK(!reist_vfs_file_close(handle));
    }
    write_mode = 0; write_size = 10U; write_limit = 3U;
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    stream_begin(payload, 4U, 300U);
    C_CHECK(!reist_vfs_file_pwrite_bounded(handle, payload, 4U, 30U, &progress));
    C_CHECK(progress.durable_bytes == 4U && progress.initial_size == 10U && progress.durable_size == 34U);
    C_CHECK(progress.first_offset == 30U && stream_calls == 5U); /* three gap, two data steps */
    stream_active = 0;
    C_CHECK(!reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) && !position);
    C_CHECK(!reist_vfs_file_close(handle));
    write_size = 10U;
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    stream_begin(payload, 4U, 300U); stream_fail_at = 3U; stream_fail_mode = 31U;
    C_CHECK(reist_vfs_file_pwrite_bounded(handle, payload, 4U, 30U, &progress) == -5);
    C_CHECK(progress.outcome == REIST_FILE_OBJECT_UNKNOWN && !progress.durable_bytes && progress.durable_size == 24U);
    C_CHECK(progress.flags & REIST_VFS_FILE_PROGRESS_SIZE_KNOWN);
    stream_active = 0; write_mode = 0;
    C_CHECK(!reist_vfs_file_close(handle));
    write_size = 30U;
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    stream_begin(NULL, 0U, 300U);
    C_CHECK(!reist_vfs_file_resize_bounded(handle, 0U, &progress));
    C_CHECK(!progress.durable_bytes && !progress.durable_size && progress.released_clusters == 4U);
    C_CHECK(progress.steps == 5U && (progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE));
    C_CHECK(!stream_published);
    stream_active = 0;
    C_CHECK(!reist_vfs_file_close(handle));
    write_size = 10U;
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 20U, rights, 0U, &handle));
    stream_begin(payload, 100U, 20U);
    C_CHECK(reist_vfs_file_write_bounded(handle, payload, 100U, &progress) == -110);
    C_CHECK(progress.durable_bytes > 0U && progress.durable_bytes < 100U && stream_calls < 4U);
    C_CHECK(!(progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE));
    stream_active = 0;
    C_CHECK(!reist_vfs_file_close(handle));
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    uint32_t before = write_submits;
    C_CHECK(reist_vfs_file_pwrite_bounded(handle, payload, 2U, UINT32_MAX, &progress) == -75);
    C_CHECK(reist_vfs_file_write_bounded(handle, NULL, 1U, &progress) == -22);
    C_CHECK(reist_vfs_file_resize_bounded(handle, UINT64_MAX, &progress) == -75);
    C_CHECK(write_submits == before && !progress.steps && progress.outcome == REIST_FILE_OBJECT_NO_EFFECT);
    C_CHECK(reist_vfs_file_write_bounded(handle, payload, 1U, NULL) == -22 && write_submits == before);
    C_CHECK(!reist_vfs_file_seek(handle, UINT32_MAX, REIST_VFS_SEEK_SET, &position));
    C_CHECK(reist_vfs_file_write_bounded(handle, payload, 1U, &progress) == -75 && write_submits == before);
    C_CHECK(!reist_vfs_file_close(handle));
    /* A durable error is neither replayed nor stripped of its committed tail. */
    write_size = 10U;
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    stream_begin(payload, 10U, 300U); stream_fail_at = 3U; stream_fail_mode = 32U;
    C_CHECK(reist_vfs_file_write_bounded(handle, payload, 10U, &progress) == -116);
    C_CHECK(progress.durable_bytes == 9U && progress.last.durable_bytes == 3U && stream_calls == 3U);
    C_CHECK(progress.outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && !(progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE));
    stream_active = 0; write_mode = 0;
    C_CHECK(!reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) && position == 9U);
    C_CHECK(!reist_vfs_file_close(handle));
    /* No successful zero-progress response may turn into an unbounded loop. */
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    stream_begin(payload, 10U, 300U); stream_fail_at = 2U; stream_fail_mode = 33U;
    C_CHECK(reist_vfs_file_write_bounded(handle, payload, 10U, &progress) == -84);
    C_CHECK(progress.durable_bytes == 3U && progress.outcome == REIST_FILE_OBJECT_UNKNOWN && stream_calls == 2U);
    stream_active = 0; write_mode = 0;
    C_CHECK(!reist_vfs_file_close(handle));
    /* Empty input is still validated by the host, but cannot extend a gap. */
    for (unsigned op = 0U; op < 3U; ++op) {
        write_size = 10U;
        C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
        stream_begin(NULL, 0U, 300U);
        int status = op == 0U ? reist_vfs_file_write_bounded(handle, NULL, 0U, &progress) :
            op == 1U ? reist_vfs_file_pwrite_bounded(handle, NULL, 0U, UINT32_MAX, &progress) :
                       reist_vfs_file_append_bounded(handle, NULL, 0U, &progress);
        C_CHECK(!status && progress.outcome == REIST_FILE_OBJECT_NO_EFFECT && progress.durable_size == 10U);
        C_CHECK(!progress.durable_bytes && !stream_published && stream_calls == 1U);
        C_CHECK((progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE) && !(progress.flags & REIST_VFS_FILE_PROGRESS_OFFSET_KNOWN));
        stream_active = 0;
        C_CHECK(!reist_vfs_file_close(handle));
    }
    /* Each clock boundary: failure or backward time stops without inventing a
     * committed prefix or renewing the original deadline. No failure at the
     * initial sample can detect a rollback without a previous observation. */
    for (unsigned kind = 1U; kind <= 2U; ++kind) {
        for (unsigned at = kind == 1U ? 1U : 2U; at <= 19U; ++at) {
            write_size = 10U;
            C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
            stream_begin(payload, 9U, 300U);
            clock_calls = 0U; clock_fault_at = at; clock_fault_kind = kind;
            C_CHECK(reist_vfs_file_write_bounded(handle, payload, 9U, &progress) == -5);
            C_CHECK(clock_calls == at && progress.result == -5);
            C_CHECK(progress.durable_bytes == (at <= 7U ? 0U : at <= 13U ? 3U : 6U));
            C_CHECK(progress.durable_bytes == stream_acked*3U && !(progress.flags & REIST_VFS_FILE_PROGRESS_COMPLETE));
            stream_active = 0; clock_fault_at = 0U;
            C_CHECK(!reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) && position == progress.durable_bytes);
            C_CHECK(!reist_vfs_file_close(handle));
        }
    }
    /* Saturating addition must not wrap a near-UINT64_MAX deadline. */
    C_CHECK(!reist_vfs_file_open_writable("FILE.TXT", 300U, rights, 0U, &handle));
    clock_now = UINT64_MAX-3U;
    before = write_submits;
    C_CHECK(reist_vfs_file_write_bounded(handle, payload, 1U, &progress) == -110);
    C_CHECK(!progress.durable_bytes && progress.outcome == REIST_FILE_OBJECT_NO_EFFECT && write_submits == before);
    clock_now = 1U;
    C_CHECK(!reist_vfs_file_close(handle));
    stream_active = 0; write_size = 10U; write_limit = 3U; write_mode = 0;
}
#endif
int main(void) {
    int status = read_tests();
    if (status) return status;
#ifdef R342_WRITE_CLIENT_TEST
    reist_vfs_file_handle_t handle = 0U;
    reist_vfs_write_result_t result;
    uint32_t rights = REIST_VFS_FILE_RIGHT_ALL | REIST_VFS_WRITE_RIGHT_WRITE |
        REIST_VFS_WRITE_RIGHT_APPEND | REIST_VFS_WRITE_RIGHT_RESIZE | REIST_VFS_WRITE_RIGHT_SYNC;
    uint8_t input[10] = {1, 2, 3};
    uint32_t position = 0U;
    C_CHECK(REIST_VFS_FILE_RIGHT_DATA == 7U && REIST_VFS_FILE_RIGHT_ALL == 15U);
    C_CHECK(reist_vfs_file_open_rights("FILE.TXT", 1000U, rights, &handle) == -22);
    C_CHECK(reist_vfs_file_open_writable("FILE.TXT", 1000U, rights, 0U, &handle) == 0);
    C_CHECK(reist_vfs_file_pwrite_step(handle, input, 10U, 2U, &result) == 0);
    C_CHECK(result.durable_bytes == 3U && result.effective_offset == 2U);
    C_CHECK(reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) == 0 && position == 0U);
    C_CHECK(reist_vfs_file_write_step(handle, input, 10U, &result) == 0);
    C_CHECK(reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) == 0 && position == 3U);
    C_CHECK(reist_vfs_file_append_step(handle, input, 10U, &result) == 0);
    C_CHECK(result.resulting_size == 13U && result.previous_size == 10U);
    C_CHECK(reist_vfs_file_seek(handle, 0, REIST_VFS_SEEK_CUR, &position) == 0 && position == 13U);
    C_CHECK(reist_vfs_file_resize_step(handle, 5U, &result) == 0 && result.resulting_size == 5U);
    C_CHECK(reist_vfs_file_fsync(handle, &result) == 0 && result.durable_bytes == 0U);
    uint32_t before = write_submits;
    C_CHECK(reist_vfs_file_pwrite_step(handle, input, 2U, UINT32_MAX, &result) == -75);
    C_CHECK(reist_vfs_file_write_step(handle, 0, 1U, &result) == -22);
    C_CHECK(reist_vfs_file_write_step(handle, input, 131073U, &result) == -22);
    C_CHECK(reist_vfs_file_resize_step(handle, (uint64_t)UINT32_MAX+1U, &result) == -75);
    C_CHECK(write_submits == before);
    C_CHECK(reist_vfs_file_close(handle) == 0);
    for (uint32_t mode = 1U; mode <= 28U; ++mode) {
        write_mode = 0U;
        C_CHECK(reist_vfs_file_open_writable("FILE.TXT", 1000U, rights, 0U, &handle) == 0);
        uint32_t ack = write_acks, cancel = write_cancels;
        write_mode = mode;
        C_CHECK(reist_vfs_file_pwrite_step(handle, input, 10U, 2U, &result) == -84);
        C_CHECK(result.outcome == REIST_FILE_OBJECT_UNKNOWN && result.durable_bytes == 0U);
        C_CHECK(write_acks == ack && write_cancels == cancel+1U);
        before = write_submits;
        write_mode = 0U;
        C_CHECK(reist_vfs_file_write_step(handle, input, 10U, &result) == -116);
        C_CHECK(write_submits == before && reist_vfs_file_close(handle) == 0);
    }
    for (uint32_t mode = 30U; mode <= 44U; ++mode) {
        if (mode > 31U && mode < 40U) continue;
        write_mode = 0U;
        C_CHECK(reist_vfs_file_open_writable("FILE.TXT", 30U, rights, 0U, &handle) == 0);
        uint32_t ack = write_acks;
        before = write_submits;
        write_mode = mode;
        int expected = mode == 30U ? -28 : mode == 40U ? -13 : mode == 42U || mode == 43U ? -110 : -5;
        C_CHECK(reist_vfs_file_pwrite_step(handle, input, 10U, 0U, &result) == expected);
        C_CHECK(result.outcome == ((mode == 30U || mode == 40U) ?
            REIST_FILE_OBJECT_NO_EFFECT : REIST_FILE_OBJECT_UNKNOWN));
        C_CHECK(write_submits == before+1U);
        C_CHECK(write_acks == ack + ((mode == 30U || mode == 31U || mode == 42U) ? 1U : 0U));
        write_mode = 0U;
        C_CHECK(reist_vfs_file_close(handle) == 0);
    }
    C_CHECK(reist_vfs_file_open_writable("FILE.TXT", 1000U, REIST_VFS_WRITE_RIGHT_APPEND, 0U, &handle) == 0);
    before = write_submits;
    C_CHECK(reist_vfs_file_write_step(handle, input, 1U, &result) == -13);
    C_CHECK(reist_vfs_file_resize_step(handle, 0U, &result) == -13);
    C_CHECK(reist_vfs_file_fsync(handle, &result) == -13);
    C_CHECK(write_submits == before);
    C_CHECK(reist_vfs_file_append_step(handle, input, 1U, &result) == 0);
    C_CHECK(reist_vfs_file_close(handle) == 0);
    C_CHECK(reist_vfs_file_open_writable("FILE.TXT", 1000U, rights, 0U, &handle) == 0);
    x86os_process_identity_t target = {1U, sizeof(target), 42, 7U};
    C_CHECK(reist_vfs_file_delegate(handle, &target, REIST_VFS_WRITE_RIGHT_APPEND) == -22);
    C_CHECK(reist_vfs_file_delegate_writable(handle, &target, REIST_VFS_WRITE_RIGHT_APPEND) == 0);
    C_CHECK(reist_vfs_file_close(handle) == 0);
    C_CHECK(reist_vfs_file_adopt_writable(1000U, &handle) == 0);
    C_CHECK(reist_vfs_file_write_step(handle, input, 1U, &result) == -13);
    C_CHECK(reist_vfs_file_append_step(handle, input, 1U, &result) == 0);
    C_CHECK(reist_vfs_file_close(handle) == 0);
    stream_tests();
    printf("R342 write-client checks: %u\n", write_checks);
#endif
    return 0;
}
