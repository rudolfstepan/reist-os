/* Explicit destructive exercise of an EXISTING disposable test file.
 * Ordinary Ring-3 file-object APIs only. No raw IO, guard or repair grants. */
#include "x86os.h"
#include "../storage/include/reist/vfs_file_client.h"

static uint8_t payload[128U*1024U], readback[128U*1024U];
static int equal(const char* a, const char* b) {
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}
static int number(const char* text, uint32_t* value) {
    uint32_t result = 0; unsigned n = 0;
    if (!text || !*text) return -22;
    for (; text[n]; ++n) {
        if (n >= 10 || text[n] < '0' || text[n] > '9') return -22;
        uint32_t digit = (uint32_t)(text[n]-'0');
        if (result > (UINT32_MAX-digit)/10) return -75;
        result = result*10+digit;
    }
    *value = result; return 0;
}
static void decimal(uint64_t value) {
    char reversed[20]; unsigned count = 0;
    do { reversed[count++] = (char)('0'+value%10); value /= 10; } while (value && count < sizeof(reversed));
    while (count) x86os_putchar(reversed[--count]);
}
static int progress(const char* operation, int result, const reist_vfs_file_progress_t* p) {
    x86os_puts("FWRITE STEP op="); x86os_puts(operation);
    x86os_puts(" result="); x86os_print_number(result);
    x86os_puts(" outcome="); decimal(p->outcome);
    x86os_puts(" bytes="); decimal(p->durable_bytes);
    x86os_puts(" size="); decimal(p->durable_size);
    x86os_puts(" released="); decimal(p->released_clusters);
    x86os_puts(" steps="); decimal(p->steps); x86os_putchar('\n');
    if (result) return result; /* never replay an uncertain/partial request */
    return p->flags & REIST_VFS_FILE_PROGRESS_COMPLETE ? 0 : -5;
}
static int resize(reist_vfs_file_handle_t handle, uint32_t size) {
    reist_vfs_file_progress_t p;
    int result = reist_vfs_file_resize_bounded(handle, size, &p);
    return progress("resize", result, &p);
}
static int pwrite(reist_vfs_file_handle_t handle, uint32_t offset) {
    reist_vfs_file_progress_t p;
    int result = reist_vfs_file_pwrite_bounded(handle, payload, sizeof(payload), offset, &p);
    return progress("pwrite", result, &p);
}
static int append(reist_vfs_file_handle_t handle, uint32_t length) {
    reist_vfs_file_progress_t p;
    int result = reist_vfs_file_append_bounded(handle, payload, length, &p);
    return progress("append", result, &p);
}
static int verify(reist_vfs_file_handle_t handle, uint32_t offset, uint32_t length, int zero) {
    uint32_t actual = 0;
    if (length > sizeof(readback)) return -22;
    int result = reist_vfs_file_seek(handle, offset, REIST_VFS_SEEK_SET, &actual);
    if (result || actual != offset) return result ? result : -5;
    uint32_t done = 0;
    /* read_bulk is one bounded call, but a filesystem may report a short read. */
    uint64_t start, now;
    if (x86os_monotonic_ms(&start)) return -5;
    uint64_t last = start;
    while (done < length) {
        if (x86os_monotonic_ms(&now) || now < last || now-start >= 5000) return -110;
        last = now;
        result = reist_vfs_file_set_timeout(handle, (uint32_t)(5000-(now-start)));
        if (result) return result;
        result = reist_vfs_file_read_bulk(handle, readback+done, length-done);
        if (result <= 0 || (uint32_t)result > length-done) return result < 0 ? result : -5;
        done += (uint32_t)result;
    }
    for (uint32_t i = 0; i < length; ++i)
        if (readback[i] != (zero ? 0 : payload[i])) return -84;
    return reist_vfs_file_set_timeout(handle, 5000);
}
static int sync_file(reist_vfs_file_handle_t handle) {
    reist_vfs_write_result_t result;
    int status = reist_vfs_file_fsync(handle, &result);
    x86os_puts("FWRITE SYNC result="); x86os_print_number(status);
    x86os_puts(" outcome="); decimal(result.outcome); x86os_putchar('\n');
    return status;
}
int main(int argc, char** argv) {
    const char* mode = argc >= 4 ? argv[3] : "exercise";
    uint32_t value = equal(mode, "append") ? 4097 : 3;
    if (argc < 3 || argc > 5 || !argv[1] || argv[1][0] != '/' || !equal(argv[2], "--test-data") ||
        (argc == 5 && number(argv[4], &value)) ||
        (!equal(mode, "exercise") && !equal(mode, "pwrite") && !equal(mode, "append") && !equal(mode, "resize") && !equal(mode, "sync")) ||
        (equal(mode, "resize") && argc != 5) ||
        ((equal(mode, "exercise") || equal(mode, "sync")) && argc == 5) ||
        (equal(mode, "append") && value > sizeof(payload))) {
        x86os_puts("Usage: fwritest /existing/test-file --test-data [exercise|pwrite [offset]|append [bytes<=131072]|resize size|sync]\n");
        x86os_puts("WARNING: changes the selected disposable test file; does not create it.\n");
        return 2;
    }
    for (unsigned i = 0; i < sizeof(payload); ++i) payload[i] = (uint8_t)(i*17U+23U);
    reist_vfs_file_handle_t handle = 0;
    uint32_t rights = REIST_VFS_FILE_RIGHT_DATA | REIST_VFS_WRITE_RIGHT_MUTATIONS;
    int result = reist_vfs_file_open_writable(argv[1], 5000, rights, X86OS_O_NOFOLLOW, &handle);
    int stage = 1;
    if (!result) {
        x86os_file_info_t info;
        result = reist_vfs_file_fstat(handle, &info);
        if (!result) { x86os_puts("FWRITE OPEN size="); decimal(info.size); x86os_putchar('\n'); }
    }
    if (!result) {
        stage = 2;
        if (equal(mode, "pwrite")) result = pwrite(handle, value);
        else if (equal(mode, "append")) result = append(handle, value);
        else if (equal(mode, "resize")) result = resize(handle, value);
        else if (equal(mode, "sync")) result = sync_file(handle);
        else {
            result = pwrite(handle, 3);
            if (!result) { stage = 3; result = verify(handle, 3, sizeof(payload), 0); }
            x86os_file_info_t info;
            if (!result) { stage = 4; result = reist_vfs_file_fstat(handle, &info); }
            uint32_t old_size = result ? 0 : info.size;
            if (!result && old_size > UINT32_MAX-12290U) result = -75;
            if (!result) result = append(handle, 4097);
            if (!result) result = verify(handle, old_size, 4097, 0);
            if (!result) { stage = 5; result = resize(handle, old_size+12290U); }
            if (!result) result = verify(handle, old_size+4097U, 8193, 1);
            if (!result) { stage = 6; result = resize(handle, 513); }
            if (!result) result = verify(handle, 3, 510, 0);
            if (!result) { stage = 7; result = sync_file(handle); }
        }
    }
    if (handle) { int closed = reist_vfs_file_close(handle); if (!result) result = closed; }
    x86os_puts(result ? "FWRITE FAIL stage=" : "FWRITE OK stage=");
    x86os_print_number(stage); x86os_puts(" result="); x86os_print_number(result); x86os_putchar('\n');
    return result ? stage : 0;
}
