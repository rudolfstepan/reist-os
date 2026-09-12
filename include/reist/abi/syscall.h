/**
 * @file include/reist/abi/syscall.h
 * @brief Authoritative append-only REIST syscall ABI.
 *
 * The three fields are the legacy Kernel name, public SDK name and immutable
 * numeric index.  Compatibility projections are generated from this list.
 */
#ifndef REIST_ABI_SYSCALL_H
#define REIST_ABI_SYSCALL_H

#include <stdint.h>

#define REIST_SYSCALL_ABI_VERSION 1U
#define REIST_SYSCALL_COUNT 133U

#define REIST_SYSCALL_LIST(X) \
    X(TERMINAL_PUTCHAR, PUTCHAR, 0U) \
    X(PRINT, PRINT_NUMBER, 1U) \
    X(DELAY, DELAY, 2U) \
    X(WAIT_ENTER, WAIT_ENTER, 3U) \
    X(MALLOC, MALLOC, 4U) \
    X(FREE, FREE, 5U) \
    X(REALLOC, REALLOC, 6U) \
    X(TERMINAL_GETCHAR, GETCHAR, 7U) \
    X(INSTALL_IRQ, RESERVED_INSTALL_IRQ, 8U) \
    X(EXIT, EXIT, 9U) \
    X(GET_DATE, GET_DATE, 10U) \
    X(GET_TIME, GET_TIME, 11U) \
    X(UPTIME_MS, UPTIME_MS, 12U) \
    X(MEMORY_KB, MEMORY_KB, 13U) \
    X(OPEN, OPEN, 14U) \
    X(READ, READ, 15U) \
    X(CLOSE, CLOSE, 16U) \
    X(STAT, STAT, 17U) \
    X(READDIR, READDIR, 18U) \
    X(CREATE, CREATE, 19U) \
    X(WRITE, WRITE, 20U) \
    X(UNLINK, UNLINK, 21U) \
    X(GETPID, GETPID, 22U) \
    X(SPAWN, SPAWN, 23U) \
    X(WAIT, WAIT, 24U) \
    X(READDIR_BATCH, READDIR_BATCH, 25U) \
    X(PROCESS_INFO, PROCESS_INFO, 26U) \
    X(KILL, KILL, 27U) \
    X(GETCWD, GETCWD, 28U) \
    X(CHDIR, CHDIR, 29U) \
    X(SPAWNV, SPAWNV, 30U) \
    X(DRIVE_INFO, DRIVE_INFO, 31U) \
    X(SPACE, SPACE, 32U) \
    X(MKDIR, MKDIR, 33U) \
    X(RMDIR, RMDIR, 34U) \
    X(CLEAR, CLEAR, 35U) \
    X(SET_CURSOR, SET_CURSOR, 36U) \
    X(TERMINAL_WRITE, TERMINAL_WRITE, 37U) \
    X(TERMINAL_DRAW, TERMINAL_DRAW, 38U) \
    X(GETCHAR_NONBLOCKING, GETCHAR_NONBLOCKING, 39U) \
    X(YIELD, YIELD, 40U) \
    X(SLEEP_MS, SLEEP_MS, 41U) \
    X(MONOTONIC_MS, MONOTONIC_MS, 42U) \
    X(MEMORY_STATS, MEMORY_STATS, 43U) \
    X(DISPLAY_INFO, DISPLAY_INFO, 44U) \
    X(FILL_RECT, FILL_RECT, 45U) \
    X(DRAW_TEXT, DRAW_TEXT, 46U) \
    X(RENAME, RENAME, 47U) \
    X(FSYNC, FSYNC, 48U) \
    X(IPC_CREATE, IPC_CREATE, 49U) \
    X(IPC_SEND, IPC_SEND, 50U) \
    X(IPC_RECEIVE, IPC_RECEIVE, 51U) \
    X(IPC_CLOSE, IPC_CLOSE, 52U) \
    X(IPC_SEND_TIMEOUT, IPC_SEND_TIMEOUT, 53U) \
    X(IPC_RECEIVE_TIMEOUT, IPC_RECEIVE_TIMEOUT, 54U) \
    X(IPC_DELEGATE, IPC_DELEGATE, 55U) \
    X(REIST_REPORT, REIST_REPORT, 56U) \
    X(SERVICE_CONNECT, SERVICE_CONNECT, 57U) \
    X(IPC_RELEASE, IPC_RELEASE, 58U) \
    X(NETWORK_PROBE, NETWORK_PROBE, 59U) \
    X(NETWORK_PROBE_ID, NETWORK_PROBE_ID, 60U) \
    X(NETWORK_PROBE_STATS, NETWORK_PROBE_STATS, 61U) \
    X(REIST_ARP_BINDING, REIST_ARP_BINDING, 62U) \
    X(REIST_ARP_REPLY, REIST_ARP_REPLY, 63U) \
    X(REIST_ARP_RESOLUTION, REIST_ARP_RESOLUTION, 64U) \
    X(NETWORK_ARP_RESOLVE, NETWORK_ARP_RESOLVE, 65U) \
    X(STORAGE_BIND, STORAGE_BIND, 66U) \
    X(STORAGE_SUBMIT, STORAGE_SUBMIT, 67U) \
    X(STORAGE_CLAIM, STORAGE_CLAIM, 68U) \
    X(STORAGE_BLOCK_READ, STORAGE_BLOCK_READ, 69U) \
    X(STORAGE_COMPLETE, STORAGE_COMPLETE, 70U) \
    X(STORAGE_COLLECT, STORAGE_COLLECT, 71U) \
    X(REIST_ICMP_ECHO_REPLY, REIST_ICMP_ECHO_REPLY, 72U) \
    X(REIST_DHCP_COMMIT, REIST_DHCP_COMMIT, 73U) \
    X(REIST_UDP_ECHO_REPLY, REIST_UDP_ECHO_REPLY, 74U) \
    X(REIST_UDP_BIND, REIST_UDP_BIND, 75U) \
    X(REIST_UDP_UNBIND, REIST_UDP_UNBIND, 76U) \
    X(REIST_UDP_REPLY, REIST_UDP_REPLY, 77U) \
    X(REIST_DHCP_RENEW, REIST_DHCP_RENEW, 78U) \
    X(REIST_NETWORK_FRAME, REIST_NETWORK_FRAME, 79U) \
    X(REIST_UDP_INGRESS, REIST_UDP_INGRESS, 80U) \
    X(REIST_DHCP_INGRESS, REIST_DHCP_INGRESS, 81U) \
    X(REIST_DHCP_BOOT_START, REIST_DHCP_BOOT_START, 82U) \
    X(REIST_ICMP_INGRESS, REIST_ICMP_INGRESS, 83U) \
    X(SCHEDULER_STATS, SCHEDULER_STATS, 84U) \
    X(STORAGE_BLOCK_WRITE, STORAGE_BLOCK_WRITE, 85U) \
    X(STORAGE_MAINT_ACQUIRE, STORAGE_MAINT_ACQUIRE, 86U) \
    X(STORAGE_MAINT_RENEW, STORAGE_MAINT_RENEW, 87U) \
    X(STORAGE_MAINT_RELEASE, STORAGE_MAINT_RELEASE, 88U) \
    X(DRIVE_STATUS, DRIVE_STATUS, 89U) \
    X(ADMIN_STORAGE, ADMIN_STORAGE, 90U) \
    X(COMPONENT_CONTROL, COMPONENT_CONTROL, 91U) \
    X(PARTITION_CREATE, PARTITION_CREATE, 92U) \
    X(STORAGE_BLOCK_FLUSH, STORAGE_BLOCK_FLUSH, 93U) \
    X(STORAGE_MEDIA_COMMIT, STORAGE_MEDIA_COMMIT, 94U) \
    X(STORAGE_FORMAT_PROBE, STORAGE_FORMAT_PROBE, 95U) \
    X(NETWORK_CONTROL, NETWORK_CONTROL, 96U) \
    X(UDP_SOCKET_CONTROL, UDP_SOCKET_CONTROL, 97U) \
    X(UDP_SOCKET_SENDTO, UDP_SOCKET_SENDTO, 98U) \
    X(UDP_SOCKET_RECVFROM, UDP_SOCKET_RECVFROM, 99U) \
    X(UDP_SOCKET_INGRESS, UDP_SOCKET_INGRESS, 100U) \
    X(TCP_SOCKET_CONTROL, TCP_SOCKET_CONTROL, 101U) \
    X(TCP_SOCKET_CONNECT, TCP_SOCKET_CONNECT, 102U) \
    X(TCP_SOCKET_SEND, TCP_SOCKET_SEND, 103U) \
    X(TCP_SOCKET_RECEIVE, TCP_SOCKET_RECEIVE, 104U) \
    X(TCP_SOCKET_INGRESS, TCP_SOCKET_INGRESS, 105U) \
    X(TCP_SOCKET_LISTEN, TCP_SOCKET_LISTEN, 106U) \
    X(TCP_SOCKET_ACCEPT, TCP_SOCKET_ACCEPT, 107U) \
    X(TOUCH, TOUCH, 108U) \
    X(DISPLAY_CONTROL, DISPLAY_CONTROL, 109U) \
    X(MOUSE_EVENT, MOUSE_EVENT, 110U) \
    X(POINTER_UPDATE, POINTER_UPDATE, 111U) \
    X(USB_DIAGNOSTICS, USB_DIAGNOSTICS, 112U) \
    X(DEVICE_CONTROL, DEVICE_CONTROL, 113U) \
    X(PROCESS_IDENTITY, PROCESS_IDENTITY, 114U) \
    X(DRAW_TEXT_CLIPPED, DRAW_TEXT_CLIPPED, 115U) \
    X(RUNTIME_TIMING, RUNTIME_TIMING, 116U) \
    X(BOOT_STATUS, BOOT_STATUS, 117U) \
    X(STORAGE_CANCEL, STORAGE_CANCEL, 118U) \
    X(STORAGE_CLAIM_IDENTITY, STORAGE_CLAIM_IDENTITY, 119U) \
    X(OPEN_FLAGS, OPEN_FLAGS, 120U) \
    X(LSEEK, LSEEK, 121U) \
    X(FSTAT, FSTAT, 122U) \
    X(FTRUNCATE, FTRUNCATE, 123U) \
    X(STORAGE_BULK, STORAGE_BULK, 124U) \
    X(KERNEL_LOG_READ, KERNEL_LOG_READ, 125U) \
    X(CPU_TOPOLOGY, CPU_TOPOLOGY, 126U) \
    X(TERMINAL_INPUT, TERMINAL_INPUT, 127U) \
    X(PROCESS_RESTRICT, PROCESS_RESTRICT, 128U) \
    X(FILE_OBJECT_GUARD, FILE_OBJECT_GUARD, 129U) \
    X(STORAGE_JOURNAL_IO, STORAGE_JOURNAL_IO, 130U) \
    X(TERMINAL_WRITE_COLOR, TERMINAL_WRITE_COLOR, 131U) \
    X(TASK_CONTROL, TASK_CONTROL, 132U)

/* Bounded prepared-image family adapter; not path-based spawn or POSIX wait.
 * Available only to explicitly admitted native root generations. */
#define REIST_TASK_CONTROL_VERSION 1U
#define REIST_TASK_CREATE 1U
#define REIST_TASK_WAIT 2U
#define REIST_TASK_CANCEL 3U
#define REIST_TASK_EXITED 0U
#define REIST_TASK_FAULTED 1U
#define REIST_TASK_CANCELLED 2U
#define REIST_TASK_OWNER_LOST 3U
typedef struct {
    uint32_t version, struct_size, operation, flags;
    uint64_t target, image, timeout_ms, syscalls, cpu_samples, reserved;
} reist_task_control_request_t;
typedef char reist_task_control_size_check[
    sizeof(reist_task_control_request_t)==64U ? 1 : -1];

/* ECMA-48 base palette order; 8..15 are the REIST bright extension.
 * A typed, stateless span, not an escape-sequence/ANSI terminal protocol. */
#define REIST_TERMINAL_COLOR_VERSION 1U
#define REIST_TERMINAL_COLOR_MAX_TEXT 64U
typedef struct {
    uint32_t version;
    uint32_t struct_size;
    uint32_t descriptor;
    uint32_t length;
    uint32_t foreground;
    uint32_t background;
    uint32_t reserved[2];
    char text[REIST_TERMINAL_COLOR_MAX_TEXT];
} reist_terminal_color_request_t;

typedef char reist_terminal_color_size_check[
    sizeof(reist_terminal_color_request_t) == 96U ? 1 : -1];

/* REIST single-terminal foreground adapter, not POSIX termios/job control. */
#define REIST_TERMINAL_INPUT_VERSION 1U
#define REIST_TERMINAL_ATTACH_CONSOLE 1U
#define REIST_TERMINAL_TRANSFER 2U
#define REIST_TERMINAL_RELEASE 3U
#define REIST_TERMINAL_ACQUIRE_SERVICE 4U
#define REIST_TERMINAL_CHECK 5U
typedef struct {
    uint32_t version, struct_size, operation, reserved;
    int32_t target_pid;
    uint32_t target_generation;
} reist_terminal_input_request_t;

/* Irreversible attenuation of the calling process; no target PID or grants.
 * Only profile SCRIPT is defined. Reserved must be zero. */
#define REIST_PROCESS_RESTRICT_VERSION 1U
#define REIST_PROCESS_RESTRICT_SCRIPT 1U
typedef struct {
    uint32_t version, struct_size, profile, reserved;
} reist_process_restrict_request_t;

/* R3.38 deny-only file identity. Not a pathname, descriptor or write grant. */
#define REIST_FILE_OBJECT_VERSION 1U
#define REIST_FILE_OBJECT_FAT12 1U
#define REIST_FILE_OBJECT_FAT32 2U
#define REIST_FILE_OBJECT_EXT2 3U
#define REIST_FILE_OBJECT_SNAPSHOT 1U
#define REIST_FILE_OBJECT_PIN 2U
#define REIST_FILE_OBJECT_RELEASE 3U
#define REIST_FILE_OBJECT_MUTATION_BEGIN 4U
#define REIST_FILE_OBJECT_MUTATION_END 5U
#define REIST_FILE_OBJECT_VERIFY 6U
#define REIST_FILE_OBJECT_EXCLUSIVE 1U
#define REIST_FILE_OBJECT_EXTERNAL_JOURNAL 2U

/* Versioned capability mediator, not a POSIX raw-device interface. Sectors
 * are relative to the canonical resource; deferred writes are NOT durable. */
#define REIST_STORAGE_JOURNAL_VERSION 1U
#define REIST_STORAGE_JOURNAL_READ 1U
#define REIST_STORAGE_JOURNAL_WRITE_DEFERRED 2U
#define REIST_STORAGE_JOURNAL_FLUSH 3U
#define REIST_STORAGE_JOURNAL_MAX_SECTORS 256U
typedef struct {
    uint32_t version, struct_size, operation, token;
    uint32_t resource, sector, count, reserved;
} reist_storage_journal_request_t;
#define REIST_FILE_OBJECT_NO_EFFECT 1U
#define REIST_FILE_OBJECT_DURABLE_COMMIT 2U
#define REIST_FILE_OBJECT_UNKNOWN 3U

typedef struct {
    uint32_t kind, resource, object_a, object_b;
    uint8_t alias[12];
    uint32_t reserved;
} reist_file_object_key_t;

typedef struct {
    uint32_t version, struct_size, operation, flags;
    reist_file_object_key_t keys[2];
    uint64_t epoch, deadline_ms;
    uint32_t token;
    int32_t client_pid;
    uint32_t client_generation, reserved;
} reist_file_object_guard_request_t;

/* Syscall129 arg3=2: owned FAT32 BEGIN only. The original112-byte prefix and
 * v1 entry remain unchanged. Neither a pin nor a request alone grants IO. */
#define REIST_FILE_OBJECT_OWNED_VERSION 2U
typedef struct {
    reist_file_object_guard_request_t base;
    uint32_t pin, request, reserved[2];
} reist_file_object_owned_request_t;

/* Syscall129 arg3=3: Storage-only fenced repair protocol. QUERY has only a
 * resource; BEGIN echoes the immutable queried extent/generation/fingerprint
 * with an absolute deadline <=5000ms. COMMIT/ABORT echo the admitted token.
 * QUERY/BEGIN copy out; COMMIT/ABORT return errno only, never a new grant.
 * All sectors are relative to that resource, in512-byte units. No mount,
 * normal write authority, format operation or caller-chosen recovery range. */
#define REIST_FILE_REPAIR_VERSION 3U
#define REIST_FILE_REPAIR_QUERY 1U
#define REIST_FILE_REPAIR_BEGIN 2U
#define REIST_FILE_REPAIR_COMMIT 3U
#define REIST_FILE_REPAIR_ABORT 4U
typedef struct {
    uint32_t version, struct_size, operation, resource;
    uint32_t token, generation, fingerprint, flags;
    uint64_t deadline_ms;
    uint32_t first_sector, sector_count, reserved_sectors, backup_sector;
    uint32_t reserved[2];
} reist_file_repair_request_t;

/* R3.42: separate namespace carried ONLY by Storage operation35. No old
 * OPEN/DATA/ALL gains authority. Byte units, POSIX write/pwrite/append/fsync
 * terminology; resize_step is explicitly incremental, not ftruncate.
 * Entire input is published before claim. Only OPEN permits NOFOLLOW flags;
 * all reserved fields and the input reply are zero.
 * request in replies is the original kernel request handle, never a new lease. */
#define REIST_VFS_WRITE_VERSION 2U
#define REIST_VFS_WRITE_RESULT_VERSION 1U
#define REIST_VFS_WRITE_OPEN 1U
#define REIST_VFS_WRITE_DELEGATE 2U
#define REIST_VFS_WRITE_ADOPT 3U
#define REIST_VFS_WRITE_DATA 4U
#define REIST_VFS_WRITE_APPEND 5U
#define REIST_VFS_WRITE_RESIZE 6U
#define REIST_VFS_WRITE_SYNC 7U
#define REIST_VFS_WRITE_RIGHT_WRITE (1U << 4U)
#define REIST_VFS_WRITE_RIGHT_APPEND (1U << 5U)
#define REIST_VFS_WRITE_RIGHT_RESIZE (1U << 6U)
#define REIST_VFS_WRITE_RIGHT_SYNC (1U << 7U)
#define REIST_VFS_WRITE_RIGHT_MUTATIONS 240U
#define REIST_VFS_WRITE_RIGHT_MASK 255U
#define REIST_VFS_WRITE_SIZE_KNOWN 1U
#define REIST_VFS_WRITE_DONE 2U

typedef struct {
    uint32_t version, struct_size, request;
    int32_t result;
    uint32_t outcome, flags, durable_bytes, released_clusters;
    uint64_t effective_offset, previous_size, resulting_size;
    uint32_t reserved[2];
} reist_vfs_write_result_t;

typedef struct {
    uint32_t version, struct_size, operation, flags;
    uint32_t object_token, service_generation, rights, path_length;
    uint64_t offset, target_size;
    uint32_t length, data_crc32;
    int32_t target_pid;
    uint32_t target_generation;
    char path[192];
    reist_vfs_write_result_t reply;
    uint32_t reserved[48];
} reist_vfs_write_frame_t;

#if defined(__cplusplus)
static_assert(sizeof(reist_file_repair_request_t) == 64U, "repair ABI");
static_assert(__builtin_offsetof(reist_file_repair_request_t, deadline_ms) == 32U, "repair deadline offset");
static_assert(sizeof(reist_vfs_write_result_t) == 64U, "write result ABI");
static_assert(sizeof(reist_vfs_write_frame_t) == 512U, "write frame ABI");
static_assert(__builtin_offsetof(reist_vfs_write_frame_t, reply) == 256U, "write reply offset");
static_assert(__builtin_offsetof(reist_vfs_write_result_t, effective_offset) == 32U, "write byte offset");
#else
_Static_assert(sizeof(reist_file_repair_request_t) == 64U, "repair ABI");
_Static_assert(__builtin_offsetof(reist_file_repair_request_t, deadline_ms) == 32U, "repair deadline offset");
_Static_assert(sizeof(reist_vfs_write_result_t) == 64U, "write result ABI");
_Static_assert(sizeof(reist_vfs_write_frame_t) == 512U, "write frame ABI");
_Static_assert(__builtin_offsetof(reist_vfs_write_frame_t, reply) == 256U, "write reply offset");
_Static_assert(__builtin_offsetof(reist_vfs_write_result_t, effective_offset) == 32U, "write byte offset");
#endif

#define REIST_DECLARE_SYSCALL(kernel_name, sdk_name, number) \
    REIST_SYS_##sdk_name = number,
typedef enum {
    REIST_SYSCALL_LIST(REIST_DECLARE_SYSCALL)
} reist_syscall_number_t;
#undef REIST_DECLARE_SYSCALL

/* Positive POSIX errno values; syscall failures return their negation. */
typedef enum {
    REIST_EPERM = 1,
    REIST_ENOENT = 2,
    REIST_EIO = 5,
    REIST_EBADF = 9,
    REIST_EAGAIN = 11,
    REIST_ENOMEM = 12,
    REIST_EACCES = 13,
    REIST_EFAULT = 14,
    REIST_EBUSY = 16,
    REIST_EEXIST = 17,
    REIST_ENODEV = 19,
    REIST_ENOTDIR = 20,
    REIST_EISDIR = 21,
    REIST_EINVAL = 22,
    REIST_EMFILE = 24,
    REIST_ENOSPC = 28,
    REIST_ESPIPE = 29,
    REIST_EROFS = 30,
    REIST_ERANGE = 34,
    REIST_ENAMETOOLONG = 36,
    REIST_EOVERFLOW = 75,
    REIST_ENOTSUP = 95,
    REIST_ETIMEDOUT = 110,
    REIST_ESTALE = 116,
} reist_errno_t;

#endif
