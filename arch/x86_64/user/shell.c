#include <reist/x86_64/syscall.h>
typedef unsigned long long shell_u64;
typedef long long shell_i64;
typedef unsigned int shell_u32;
typedef unsigned char shell_u8;

#define REIST_STDIN 0ULL
#define REIST_STDOUT 1ULL
#define REIST_EAGAIN (-11LL)
#define REIST_EBADF (-9LL)
#define REIST_EPIPE (-32LL)
#define REIST_ETIMEDOUT (-110LL)
#define SHELL_COMMAND_CAPACITY 16U
#define SHELL_POLL_LIMIT 67108864U
#define SHELL_PARENT_PID 300LL
#define SHELL_CHILD_PID 301LL
#define SHELL_CHILD_STATUS 77U
#ifndef X86_64_INSTRUCTION_CASE
#define X86_64_INSTRUCTION_CASE 0
#endif
#ifndef X86_64_MAPPING_CASE
#define X86_64_MAPPING_CASE 0
#endif
#ifndef X86_64_REQUEST_CASE
#define X86_64_REQUEST_CASE 0
#endif
#ifndef X86_64_OOM_CASE
#define X86_64_OOM_CASE 0
#endif
#ifndef X86_64_PROFILE_CASE
#define X86_64_PROFILE_CASE 0
#endif
#ifndef X86_64_IPC_CASE
#define X86_64_IPC_CASE 0
#endif
#ifndef X86_64_ARGV_CASE
#define X86_64_ARGV_CASE 0
#endif
#ifndef X86_64_EXIT_STATUS
#define X86_64_EXIT_STATUS -1
#endif
#ifndef X86_64_BUSY_CHILD
#define X86_64_BUSY_CHILD 0
#endif
#ifndef X86_64_CONTEXT_CASE
#define X86_64_CONTEXT_CASE 0
#endif
#if X86_64_INSTRUCTION_CASE >= 2
#undef X86_64_BUSY_CHILD
#define X86_64_BUSY_CHILD 1
#endif
#if X86_64_CONTEXT_CASE
#undef X86_64_BUSY_CHILD
#define X86_64_BUSY_CHILD 1
#endif
#ifndef X86_64_BUSY_INVALID_STACK
#define X86_64_BUSY_INVALID_STACK 0
#endif
#ifndef X86_64_FAULT_VECTOR
#define X86_64_FAULT_VECTOR -1
#endif
#ifndef X86_64_FAULT_PHASE
#define X86_64_FAULT_PHASE 0
#endif
#if X86_64_INSTRUCTION_CASE == 3
#define SHELL_EXPECTED_CHILD_STATUS 258U
#elif X86_64_MAPPING_CASE == 2 || X86_64_MAPPING_CASE == 3
#define SHELL_EXPECTED_CHILD_STATUS 142U
#elif X86_64_IPC_CASE
#define SHELL_EXPECTED_CHILD_STATUS (90U + X86_64_IPC_CASE)
#elif X86_64_ARGV_CASE
#define SHELL_EXPECTED_CHILD_STATUS (90U + X86_64_ARGV_CASE)
#elif X86_64_EXIT_STATUS >= 0
#define SHELL_EXPECTED_CHILD_STATUS ((shell_u32)X86_64_EXIT_STATUS)
#elif X86_64_CONTEXT_CASE
#define SHELL_EXPECTED_CHILD_STATUS (X86_64_CONTEXT_CASE <= 3 ? 257U : \
    X86_64_CONTEXT_CASE == 4 ? 256U : X86_64_CONTEXT_CASE == 7 ? 129U : 258U)
#elif X86_64_BUSY_CHILD
#define SHELL_EXPECTED_CHILD_STATUS (X86_64_BUSY_INVALID_STACK ? 257U : 256U)
#elif X86_64_FAULT_VECTOR >= 0
#define SHELL_EXPECTED_CHILD_STATUS (128U + X86_64_FAULT_VECTOR)
#else
#define SHELL_EXPECTED_CHILD_STATUS SHELL_CHILD_STATUS
#endif
#define IPC_MESSAGE_VERSION 1U
#define IPC_MESSAGE_SIZE 140U
#define IPC_MESSAGE_LENGTH 8U
#define IPC_RIGHT_SEND 0x01U
#define IPC_RECEIVE_TIMEOUT_MS 10ULL

typedef struct {
    shell_u32 version;
    shell_u32 struct_size;
    shell_u32 length;
    shell_u8 payload[128];
} shell_ipc_message_t;

_Static_assert(sizeof(shell_ipc_message_t) == IPC_MESSAGE_SIZE,
               "REIST-v1 IPC message size changed");

static shell_i64 shell_write(const char *message, shell_u64 length)
{
    return reist_x64_syscall3(REIST_X64_SYS_WRITE, REIST_STDOUT,
                          (shell_u64)message, length);
}

#if !X86_64_PROFILE_CASE && X86_64_IPC_CASE != 3
static shell_i64 ipc_receive_peer(shell_u64 handle, shell_ipc_message_t *message)
{
    /* A runnable peer need not complete within one PIT tick. Each wait keeps
     * the original 10-ms deadline; the fixture has at most eight attempts.
     * Payload and terminal status checks remain with the caller. */
    shell_i64 result = REIST_ETIMEDOUT;
    for (shell_u32 attempt = 0; attempt < 8; ++attempt) {
        result = reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,
                                   handle, (shell_u64)message,
                                   IPC_RECEIVE_TIMEOUT_MS);
        if (result != REIST_ETIMEDOUT) break;
    }
    return result;
}
#endif

static int shell_write_exact(const char *message, shell_u64 length)
{
    return shell_write(message, length) == (shell_i64)length;
}

static __attribute__((noreturn)) void shell_exit(shell_u64 status)
{
    (void)reist_x64_syscall3(REIST_X64_SYS_EXIT, status, 0ULL, 0ULL);
    __asm__ volatile("ud2");
    __builtin_unreachable();
}

static int command_equals(const shell_u8 *command, const char *expected,
                          shell_u32 expected_length,
                          shell_u32 actual_length)
{
    shell_u32 index;

    if (actual_length != expected_length) {
        return 0;
    }
    for (index = 0U; index < expected_length; ++index) {
        if (command[index] != (shell_u8)expected[index]) {
            return 0;
        }
    }
    return 1;
}

static void clear_command(shell_u8 *command)
{
    shell_u32 index;

    for (index = 0U; index < SHELL_COMMAND_CAPACITY; ++index) {
        command[index] = 0U;
    }
}

static void clear_ipc_message(shell_ipc_message_t *message)
{
    shell_u32 index;
    shell_u8 *bytes = (shell_u8 *)message;

    for (index = 0U; index < IPC_MESSAGE_SIZE; ++index) {
        bytes[index] = 0U;
    }
}

#if !X86_64_IPC_CASE
static __attribute__((noinline)) int
ipc_message_is_token(const shell_ipc_message_t *message, shell_u8 final_digit)
{
    static const shell_u8 prefix[IPC_MESSAGE_LENGTH - 2U] = {
        (shell_u8)'t', (shell_u8)'o', (shell_u8)'k',
        (shell_u8)'e', (shell_u8)'n', (shell_u8)'7'
    };
    shell_u32 index;

    if (message->version != IPC_MESSAGE_VERSION ||
        message->struct_size != IPC_MESSAGE_SIZE ||
        message->length != IPC_MESSAGE_LENGTH) {
        return 0;
    }
    for (index = 0U; index < IPC_MESSAGE_LENGTH - 2U; ++index) {
        if (message->payload[index] != prefix[index]) {
            return 0;
        }
    }
    if (message->payload[index] != final_digit ||
        message->payload[index + 1U] != 0U) {
        return 0;
    }
    index += 2U;
    for (; index < sizeof(message->payload); ++index) {
        if (message->payload[index] != 0U) {
            return 0;
        }
    }
    return 1;
}

#endif
static void prepare_ipc_token(shell_ipc_message_t *message,
                              shell_u8 final_digit)
{
    clear_ipc_message(message);
    message->version = IPC_MESSAGE_VERSION;
    message->struct_size = IPC_MESSAGE_SIZE;
    message->length = IPC_MESSAGE_LENGTH;
    message->payload[0] = (shell_u8)'t';
    message->payload[1] = (shell_u8)'o';
    message->payload[2] = (shell_u8)'k';
    message->payload[3] = (shell_u8)'e';
    message->payload[4] = (shell_u8)'n';
    message->payload[5] = (shell_u8)'7';
    message->payload[6] = final_digit;
}

#if !X86_64_IPC_CASE
static int ipc_message_is_empty(const shell_ipc_message_t *message)
{
    shell_u32 index;

    if (message->version != IPC_MESSAGE_VERSION ||
        message->struct_size != IPC_MESSAGE_SIZE || message->length != 0U) {
        return 0;
    }
    for (index = 0U; index < sizeof(message->payload); ++index) {
        if (message->payload[index] != 0U) {
            return 0;
        }
    }
    return 1;
}

#endif
void _start(void)
{
    static const char ready[] = "REIST_X86_64_RING3_SHELL_READY\r\n";
    static const char prompt[] = "C:\\>";
    static const char info[] = "REIST_X86_64_RING3_SHELL_INFO_OK\r\n";
    static const char help[] = "HELP INFO RUN EXIT\r\n";
#if X86_64_INSTRUCTION_CASE
    static const char run_ok[] = "REIST_X86_64_RING3_SHELL_RUN_OK\r\nINSTRUCTION_OK\r\n";
#elif X86_64_MAPPING_CASE
    static const char run_ok[] = "REIST_X86_64_RING3_SHELL_RUN_OK\r\nMAPPING_OK\r\n";
#elif X86_64_PROFILE_CASE
    static const char run_ok[] = "REIST_X86_64_RING3_SHELL_RUN_OK\r\nPROFILE_OK\r\n";
#elif X86_64_OOM_CASE
    static const char run_ok[] = "REIST_X86_64_RING3_SHELL_RUN_OK\r\nOOM_OK\r\n";
#elif X86_64_REQUEST_CASE
#define REQUEST_STRING_INNER(n) #n
#define REQUEST_STRING(n) REQUEST_STRING_INNER(n)
    static const char run_ok[] = "REIST_X86_64_RING3_SHELL_RUN_OK\r\nREQUEST_" REQUEST_STRING(X86_64_REQUEST_CASE) "_OK\r\n";
#else
    static const char run_ok[] = "REIST_X86_64_RING3_SHELL_RUN_OK\r\n";
#endif
    static const char unknown[] = "Unknown command\r\n";
    shell_u8 command[SHELL_COMMAND_CAPACITY];
    shell_u8 input_byte = 0U;
    shell_u32 command_length = 0U;
    shell_u32 polls = 0U;
#if X86_64_REQUEST_CASE == 2
    shell_u32 request_runs = 0U;
#endif

    clear_command(command);
    if (!shell_write_exact(ready, sizeof(ready) - 1U) ||
        !shell_write_exact(prompt, sizeof(prompt) - 1U)) {
        shell_exit(2ULL);
    }

    while (polls < SHELL_POLL_LIMIT) {
        shell_i64 result = reist_x64_syscall3(REIST_X64_SYS_READ, REIST_STDIN,
                                          (shell_u64)&input_byte, 1ULL);
        ++polls;
        if (result == REIST_EAGAIN) {
            (void)reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL);
            continue;
        }
        if (result != 1LL) {
            shell_exit(3ULL);
        }
        polls = 0U;
        if (input_byte == '\r' || input_byte == '\n') {
            if (command_equals(command, "INFO", 4U, command_length)) {
                if (!shell_write_exact(info, sizeof(info) - 1U) ||
                    !shell_write_exact(prompt, sizeof(prompt) - 1U)) {
                    shell_exit(4ULL);
                }
            } else if (command_equals(command, "HELP", 4U, command_length)) {
                if (!shell_write_exact(help, sizeof(help) - 1U) ||
                    !shell_write_exact(prompt, sizeof(prompt) - 1U)) {
                    shell_exit(5ULL);
                }
            } else if (command_equals(command, "RUN", 3U, command_length)) {
                shell_u8 child_path[SHELL_COMMAND_CAPACITY] __attribute__((aligned(8))) =
                    "/shell/child";
                shell_u8 child_token[SHELL_COMMAND_CAPACITY] __attribute__((aligned(8))) =
                    "token77";
                shell_u64 child_argv[2] __attribute__((aligned(8))) = {
                    (shell_u64)child_path, (shell_u64)child_token
                };
                shell_u32 child_status __attribute__((aligned(4))) = 0U;
                shell_u32 ipc_handle __attribute__((aligned(4))) = 0U;
                shell_ipc_message_t ipc_message __attribute__((aligned(8)));
                shell_i64 parent_pid = reist_x64_syscall3(REIST_X64_SYS_GETPID, 0ULL, 0ULL, 0ULL);
                shell_i64 child_pid;
                shell_i64 waited_pid;

                if (parent_pid != SHELL_PARENT_PID) {
                    shell_exit(11ULL);
                }
#if X86_64_PROFILE_CASE
                /* Independent explicit list of the existing parent policy.
                 * Probe only ungranted calls, with deliberately invalid args. */
                const shell_u64 granted=(1ULL<<9)|(1ULL<<15)|(1ULL<<20)|(1ULL<<22)|
                    (1ULL<<23)|(1ULL<<24)|(1ULL<<30)|(1ULL<<40)|(1ULL<<49)|
                    (1ULL<<50)|(1ULL<<51)|(1ULL<<52)|(1ULL<<53)|(1ULL<<54)|(1ULL<<55);
                for(shell_u64 n=0;n<64;n++) if(!(granted&(1ULL<<n))) {
                    if(reist_x64_syscall3(n,~0ULL,~0ULL,~0ULL)!=-REIST_EACCES) shell_exit(50);
                }
                if(reist_x64_syscall3(0x100000000ULL,~0ULL,~0ULL,~0ULL)!=-REIST_EACCES ||
                   reist_x64_syscall3(~0ULL,~0ULL,~0ULL,~0ULL)!=-REIST_EACCES) shell_exit(50);
#endif
#if X86_64_REQUEST_CASE == 1
                static const struct {shell_u8 op,fd,size; signed char result;} cases[] = {
                    {15,1,1,-9},{20,0,1,-9},{15,0,2,-22},{20,1,65,-22},
                    {15,0,0,0},{20,1,0,0},{20,2,0,0},{15,0,1,-14},{20,1,1,-14}
                };
                for (shell_u32 i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
                    if(reist_x64_syscall3(cases[i].op,cases[i].fd,0,cases[i].size)!=cases[i].result) shell_exit(48);
                }
                if(reist_x64_syscall3(REIST_X64_SYS_GETPID,~0ULL,~0ULL,~0ULL)!=SHELL_PARENT_PID ||
                   reist_x64_syscall3(REIST_X64_SYS_WRITE,0x100000001ULL,0,0)!=REIST_EBADF ||
                   reist_x64_syscall3(REIST_X64_SYS_WRITE,1,0,~0ULL)!=-22LL) shell_exit(48);
#elif X86_64_REQUEST_CASE == 2
                if(reist_x64_syscall3(REIST_X64_SYS_SPAWN,(shell_u64)child_path,0,0)!=REIST_EBADF ||
                   reist_x64_syscall3(REIST_X64_SYS_SPAWN,0,0,0)!=-14LL ||
                   reist_x64_syscall3(REIST_X64_SYS_SPAWN,(shell_u64)child_path,1,0)!=-22LL) shell_exit(48);
                child_path[0]='!';
                if(reist_x64_syscall3(REIST_X64_SYS_SPAWN,(shell_u64)child_path,0,0)!=-2LL) shell_exit(48);
                child_path[0]='/';
#elif X86_64_REQUEST_CASE == 3
                if(reist_x64_syscall3(REIST_X64_SYS_WAIT,SHELL_CHILD_PID,(shell_u64)&child_status,0)!=-10LL ||
                   reist_x64_syscall3(REIST_X64_SYS_WAIT,SHELL_CHILD_PID,(shell_u64)&child_status,1)!=-22LL ||
                   child_status!=0) shell_exit(48);
#endif
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_CREATE,
                                   (shell_u64)&ipc_handle, 0ULL, 0ULL) != 0LL ||
                    ipc_handle == 0U) {
                    shell_exit(15ULL);
                }
                prepare_ipc_token(&ipc_message, (shell_u8)'5');
#if X86_64_REQUEST_CASE == 2
                if(reist_x64_syscall3(REIST_X64_SYS_IPC_SEND,ipc_handle,(shell_u64)&ipc_message,0)!=0 ||
                   reist_x64_syscall3(REIST_X64_SYS_SPAWNV,(shell_u64)child_path,(shell_u64)child_argv,2)!=REIST_EAGAIN) shell_exit(48);
                ipc_message.length=0;
                if(reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE,ipc_handle,(shell_u64)&ipc_message,0)!=0 ||
                   ipc_message.length!=8) shell_exit(48);
#elif X86_64_IPC_CASE && !X86_64_REQUEST_CASE
                /* Verify local rejection without consuming the sole queue. */
                if(reist_x64_syscall3(REIST_X64_SYS_IPC_CREATE,0,0,0)!=-14LL ||
                   reist_x64_syscall3(REIST_X64_SYS_IPC_CREATE,(shell_u64)&ipc_handle,1,0)!=-22LL ||
                   reist_x64_syscall3(REIST_X64_SYS_IPC_CREATE,(shell_u64)&ipc_handle,0,0)!=REIST_EAGAIN ||
                   reist_x64_syscall3(REIST_X64_SYS_IPC_DELEGATE,ipc_handle,SHELL_CHILD_PID,1)!=-22LL) shell_exit(45);
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND, ipc_handle + 256U,
                        (shell_u64)&ipc_message, 0) != REIST_EBADF ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_SEND, ipc_handle, 0, 0) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_SEND, ipc_handle,
                        (shell_u64)&ipc_message + 1, 0) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT, ipc_handle,
                        (shell_u64)&ipc_message, ~0ULL) != -22LL) shell_exit(34);
                ipc_message.version = 2;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND, ipc_handle,
                        (shell_u64)&ipc_message, 0) != -22LL) shell_exit(35);
                ipc_message.version = 1;
                ipc_message.length = 129;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND, ipc_handle,
                        (shell_u64)&ipc_message, 0) != -22LL) shell_exit(36);
                ipc_message.length = 128;
                for (shell_u32 i=0;i<128;i++) ipc_message.payload[i]=(shell_u8)(i+1);
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT, ipc_handle,
                        (shell_u64)&ipc_message, 10) != 0 ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_SEND, ipc_handle,
                        (shell_u64)&ipc_message, 0) != REIST_EAGAIN ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT, ipc_handle,
                        (shell_u64)&ipc_message, 10) != REIST_ETIMEDOUT) shell_exit(37);
                ipc_message.length=0;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE, ipc_handle,
                        (shell_u64)&ipc_message, 0) != 0 || ipc_message.length!=128) shell_exit(38);
                for (shell_u32 i=0;i<128;i++) if(ipc_message.payload[i]!=(shell_u8)(i+1)) shell_exit(39);
                ipc_message.length=0;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE, ipc_handle,
                        (shell_u64)&ipc_message, 0) != REIST_EAGAIN) shell_exit(40);
#elif !X86_64_IPC_CASE
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message, 0ULL) != 0LL) {
                    shell_exit(22ULL);
                }
                prepare_ipc_token(&ipc_message, (shell_u8)'4');
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message,
                                   IPC_RECEIVE_TIMEOUT_MS) != REIST_ETIMEDOUT ||
                    !ipc_message_is_token(&ipc_message, (shell_u8)'4')) {
                    shell_exit(23ULL);
                }
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message, 0ULL) != 0LL ||
                    !ipc_message_is_token(&ipc_message, (shell_u8)'5')) {
                    shell_exit(24ULL);
                }
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message,
                                   IPC_RECEIVE_TIMEOUT_MS) != REIST_ETIMEDOUT ||
                    !ipc_message_is_empty(&ipc_message)) {
                    shell_exit(19ULL);
                }
#endif
#if X86_64_ARGV_CASE
                shell_u8 startup_bytes[8][128] __attribute__((aligned(8)));
                shell_u64 startup_argv[8] __attribute__((aligned(8)));
                shell_u64 bad_argv[2] __attribute__((aligned(8))) = {0ULL, (shell_u64)child_token};
                shell_u64 startup_argc = 2ULL;
                for (shell_u32 i = 0; i < (X86_64_ARGV_CASE == 3 ? 8U : X86_64_ARGV_CASE == 2 ? 3U : 1U); ++i) {
                    startup_argv[i] = (shell_u64)startup_bytes[i];
                    for (shell_u32 j = 0; j < 128U; ++j) startup_bytes[i][j] = (shell_u8)('A' + i);
                }
                if (reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, (shell_u64)child_argv, 9ULL) != -7LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, (shell_u64)child_argv, ~0ULL) != -7LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, 0ULL, 1ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, ~0ULL, 1ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, (shell_u64)child_argv + 1ULL, 2ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, 0x409000ULL - 8ULL, 2ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, (shell_u64)bad_argv, 2ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, (shell_u64)child_argv, 0ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, 0ULL, (shell_u64)child_argv, 2ULL) != -14LL ||
                    reist_x64_syscall3(REIST_X64_SYS_SPAWNV, (shell_u64)child_path, (shell_u64)startup_argv, 1ULL) != -7LL) {
                    shell_exit(33ULL);
                }
                for (shell_u32 i = 0; i < (X86_64_ARGV_CASE == 3 ? 8U : X86_64_ARGV_CASE == 2 ? 3U : 1U); ++i) startup_bytes[i][127] = 0;
#if X86_64_ARGV_CASE == 1
                startup_argc = 0;
#elif X86_64_ARGV_CASE == 2
                startup_argc = 3;
                startup_bytes[0][0]='e'; startup_bytes[0][1]='n'; startup_bytes[0][2]='t';
                startup_bytes[0][3]='r'; startup_bytes[0][4]='y'; startup_bytes[0][5]=0;
                startup_bytes[1][0]=0;
                startup_bytes[2][0]=0xc3; startup_bytes[2][1]=0xa4;
                startup_bytes[2][2]=0xce; startup_bytes[2][3]=0xa9; startup_bytes[2][4]=0;
#elif X86_64_ARGV_CASE == 3
                startup_argc = 8;
#else
                startup_argv[0] = (shell_u64)child_path;
                startup_argv[1] = (shell_u64)child_token;
#endif
                child_pid = reist_x64_syscall3(REIST_X64_SYS_SPAWNV,
                    (shell_u64)child_path, startup_argc ? (shell_u64)startup_argv : 0ULL, startup_argc);
#else
#if X86_64_OOM_CASE
                /* The external guest verifier injects exactly one allocator
                 * failure before each generation. No kernel fixture flags. */
                if(reist_x64_syscall3(REIST_X64_SYS_SPAWNV,
                     (shell_u64)child_path,(shell_u64)child_argv,2ULL)!=-12LL)
                    shell_exit(49);
#endif
                child_pid = reist_x64_syscall3(REIST_X64_SYS_SPAWNV,
                                           (shell_u64)child_path,
                                           (shell_u64)child_argv, 2ULL);
#endif
                if (child_pid != SHELL_CHILD_PID) {
                    shell_exit(12ULL);
                }
#if X86_64_REQUEST_CASE == 3
                /* Force an early child request before SEND is delegated. */
                if(reist_x64_syscall3(REIST_X64_SYS_YIELD,0,0,0)!=0) shell_exit(48);
#endif
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_DELEGATE,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)child_pid,
                                   IPC_RIGHT_SEND) != 0LL) {
                    shell_exit(16ULL);
                }
#if X86_64_IPC_CASE
#if X86_64_REQUEST_CASE == 2
                if(reist_x64_syscall3(REIST_X64_SYS_SPAWNV,(shell_u64)child_path,(shell_u64)child_argv,2)!=REIST_EAGAIN) shell_exit(48);
#endif
#if X86_64_IPC_CASE != 3
                for (shell_u32 n=0;n<2;n++) {
                    clear_ipc_message(&ipc_message);
                    ipc_message.version=1;ipc_message.struct_size=140;
#if X86_64_PROFILE_CASE
                    /* Complete the denied-call table without starting a peer
                     * deadline first. Nonblocking receive plus bounded YIELD. */
                    shell_i64 received=REIST_EAGAIN;
                    for(shell_u32 attempt=0;attempt<128 && received==REIST_EAGAIN;attempt++) {
                        received=reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE,ipc_handle,
                            (shell_u64)&ipc_message,0);
                        if(received==REIST_EAGAIN &&
                           reist_x64_syscall3(REIST_X64_SYS_YIELD,0,0,0)!=0) shell_exit(41);
                    }
                    if(received!=0 || ipc_message.length!=128) shell_exit(41);
#else
                    if(ipc_receive_peer(ipc_handle,&ipc_message)!=0 ||
                       ipc_message.length!=128) shell_exit(41);
#endif
                    for(shell_u32 i=0;i<128;i++) if(ipc_message.payload[i]!=(shell_u8)(0x5a+n)) shell_exit(42);
                }
#if !X86_64_PROFILE_CASE
                ipc_message.length=0;
                if(ipc_receive_peer(ipc_handle,&ipc_message)!=REIST_EPIPE) shell_exit(43);
#endif
#endif
                if(reist_x64_syscall3(REIST_X64_SYS_IPC_CLOSE,ipc_handle,0,0)!=0) shell_exit(44);
#else
#if X86_64_BUSY_CHILD
                /* The child has no syscall in its loop: this yield can only
                 * return through real timer preemption. Keep normal IPC tests
                 * in the default image; quota retirement fences the endpoint. */
                if (reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL) {
                    shell_exit(31ULL);
                }
                goto cpu_budget_wait;
#endif
#if X86_64_EXIT_STATUS >= 0
                /* Wide EXIT rejection and noisy YIELD each schedule the parent.
                 * Keep the admitted test phase pending until both checks finish. */
                for (shell_u32 extra_yield = 0; extra_yield < 4U; ++extra_yield) {
                    if (reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL) {
                        shell_exit(32ULL);
                    }
                }
#endif
                if (reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL ||
                    reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL ||
                    reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL ||
                    reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL) {
                    shell_exit(20ULL);
                }
#if (X86_64_FAULT_VECTOR >= 0 || X86_64_EXIT_STATUS >= 0 || X86_64_ARGV_CASE || X86_64_MAPPING_CASE == 2 || X86_64_MAPPING_CASE == 3) && X86_64_FAULT_PHASE < 2
                goto child_fault_cleanup;
#endif
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message, 0ULL) != 0LL ||
                    !ipc_message_is_token(&ipc_message, (shell_u8)'6')) {
                    shell_exit(21ULL);
                }
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message, 0ULL) != 0LL ||
                    !ipc_message_is_token(&ipc_message, (shell_u8)'7')) {
                    shell_exit(25ULL);
                }
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (ipc_receive_peer(ipc_handle, &ipc_message) !=
#if (X86_64_FAULT_VECTOR >= 0 || X86_64_EXIT_STATUS >= 0) && X86_64_FAULT_PHASE == 2
                    REIST_EPIPE || !ipc_message_is_empty(&ipc_message)) {
#else
                    0LL ||
                    !ipc_message_is_token(&ipc_message, (shell_u8)'7')) {
#endif
                    shell_exit(17ULL);
                }
#if (X86_64_FAULT_VECTOR >= 0 || X86_64_EXIT_STATUS >= 0) && X86_64_FAULT_PHASE == 2
                goto child_fault_cleanup;
#endif
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (ipc_receive_peer(ipc_handle, &ipc_message) != REIST_EPIPE ||
                    !ipc_message_is_empty(&ipc_message)) {
                    shell_exit(26ULL);
                }
                /* Publish the owner's message before granting the peer SEND.
                 * Capability publication, not a YIELD count, is the barrier. */
                prepare_ipc_token(&ipc_message, (shell_u8)'8');
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_SEND,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)&ipc_message, 0ULL) != 0LL) {
                    shell_exit(28ULL);
                }
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_DELEGATE,
                                   (shell_u64)ipc_handle,
                                   (shell_u64)child_pid,
                                   IPC_RIGHT_SEND) != 0LL) {
                    shell_exit(27ULL);
                }
                if (reist_x64_syscall3(REIST_X64_SYS_YIELD, 0ULL, 0ULL, 0ULL) != 0LL) {
                    shell_exit(29ULL);
                }
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_CLOSE,
                                   (shell_u64)ipc_handle, 0ULL, 0ULL) != 0LL) {
                    shell_exit(18ULL);
                }
#if (X86_64_FAULT_VECTOR >= 0 || X86_64_EXIT_STATUS >= 0 || X86_64_ARGV_CASE || X86_64_MAPPING_CASE == 2 || X86_64_MAPPING_CASE == 3) && X86_64_FAULT_PHASE < 3
child_fault_cleanup:
                clear_ipc_message(&ipc_message);
                ipc_message.version = IPC_MESSAGE_VERSION;
                ipc_message.struct_size = IPC_MESSAGE_SIZE;
                if (reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE,
                                     ipc_handle, (shell_u64)&ipc_message, 0ULL) != REIST_EPIPE ||
                    !ipc_message_is_empty(&ipc_message) ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_CLOSE, ipc_handle, 0ULL, 0ULL) != 0LL ||
                    reist_x64_syscall3(REIST_X64_SYS_IPC_CLOSE, ipc_handle, 0ULL, 0ULL) != 0LL) {
                    shell_exit(30ULL);
                }
#endif
#if X86_64_BUSY_CHILD
cpu_budget_wait:
#endif
#endif
#if X86_64_REQUEST_CASE == 3
                child_status=0x12345678U;
                if(reist_x64_syscall3(REIST_X64_SYS_WAIT,SHELL_CHILD_PID,0,0)!=-14LL ||
                   reist_x64_syscall3(REIST_X64_SYS_WAIT,SHELL_CHILD_PID,(shell_u64)&child_status+1,0)!=-14LL ||
                   reist_x64_syscall3(REIST_X64_SYS_WAIT,0x10000012dULL,(shell_u64)&child_status,0)!=-10LL ||
                   reist_x64_syscall3(REIST_X64_SYS_WAIT,SHELL_CHILD_PID,(shell_u64)&child_status,~0ULL)!=-22LL ||
                   child_status!=0x12345678U) shell_exit(48);
#endif
                waited_pid = reist_x64_syscall3(REIST_X64_SYS_WAIT, (shell_u64)child_pid,
                                            (shell_u64)&child_status, 0ULL);
                if (waited_pid != SHELL_CHILD_PID ||
                    child_status != SHELL_EXPECTED_CHILD_STATUS) {
                    shell_exit(13ULL);
                }
#if X86_64_REQUEST_CASE == 3
                if(reist_x64_syscall3(REIST_X64_SYS_WAIT,SHELL_CHILD_PID,(shell_u64)&child_status,0)!=-10LL ||
                   child_status!=SHELL_EXPECTED_CHILD_STATUS) shell_exit(48);
#elif X86_64_REQUEST_CASE == 2
                if(++request_runs==2 && reist_x64_syscall3(REIST_X64_SYS_SPAWN,(shell_u64)child_path,0,0)!=REIST_EAGAIN) shell_exit(48);
#endif
#if X86_64_IPC_CASE
                if(reist_x64_syscall3(REIST_X64_SYS_IPC_CLOSE,ipc_handle,0,0)!=0 ||
                   reist_x64_syscall3(REIST_X64_SYS_IPC_CLOSE,ipc_handle+256U,0,0)!=REIST_EBADF ||
                   reist_x64_syscall3(REIST_X64_SYS_IPC_SEND,ipc_handle,(shell_u64)&ipc_message,0)!=REIST_EBADF) shell_exit(46);
#endif
                if (!shell_write_exact(run_ok, sizeof(run_ok) - 1U) ||
                    !shell_write_exact(prompt, sizeof(prompt) - 1U)) {
                    shell_exit(14ULL);
                }
            } else if (command_equals(command, "EXIT", 4U, command_length)) {
                shell_exit(0ULL);
            } else if (command_length != 0U) {
                if (!shell_write_exact(unknown, sizeof(unknown) - 1U) ||
                    !shell_write_exact(prompt, sizeof(prompt) - 1U)) {
                    shell_exit(6ULL);
                }
            } else if (!shell_write_exact(prompt, sizeof(prompt) - 1U)) {
                shell_exit(7ULL);
            }
            clear_command(command);
            command_length = 0U;
            continue;
        }
        if (command_length + 1U >= SHELL_COMMAND_CAPACITY) {
            shell_exit(8ULL);
        }
        command[command_length] = input_byte;
        ++command_length;
        command[command_length] = 0U;
    }
    shell_exit(9ULL);
}
