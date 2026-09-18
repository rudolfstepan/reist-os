/* Console-only normal-shell platform, not a complete x86os SDK.
 * NATIVE_SHELL_CONTRACT.md: no implicit namespace or terminal delegation. */
#include <x86os.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/console.h>
#include <reist/vfs_stat_client.h>
#include <reist/vfs_read_client.h>

static uint64_t shell_deadline, shell_previous;
static unsigned shell_operations, shell_received, shell_written;
static char shell_output[64];
static unsigned shell_output_used;
static void shell_flush(void);

static _Noreturn void shell_stop(int error) {
    /* Normalize arbitrary backend errors without signed overflow. */
    unsigned status=error==-110?110U:error==-22?22U:5U;
    (void)reist_x64_syscall1(REIST_X64_SYS_EXIT,status);
    __builtin_trap();
}

static uint64_t shell_clock(void) {
    if(++shell_operations>4096U)shell_stop(-110);
    int64_t stamp=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    if(stamp<0)shell_stop(-5);
    uint64_t now=(uint64_t)stamp;
    if(!shell_deadline) {
        if(now>UINT64_MAX-1000U)shell_stop(-5);
        shell_deadline=now+1000U;
    } else if(now<shell_previous)shell_stop(-5);
    shell_previous=now;
    if(now>=shell_deadline)shell_stop(-110);
    return now;
}

int x86os_monotonic_ms(uint64_t *value) {
    if(!value)return -22;
    *value=shell_clock();return 0;
}

int x86os_sleep_ms(uint32_t duration) {
    if(!duration || duration>10U)return -22;
    uint64_t now=shell_clock(),remaining=shell_deadline-now;
    if(duration>remaining)duration=(uint32_t)remaining;
    int64_t result=reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,duration);
    if(result)shell_stop(-5);
    (void)shell_clock();return 0;
}

int x86os_getchar_nonblocking(void) {
    (void)shell_clock();
    if(shell_received>=1024U)shell_stop(-110);
    unsigned char value=0;
    int64_t result=reist_x64_syscall3(REIST_X64_SYS_READ,0,(uintptr_t)&value,1);
    if(result==-11) {
        /* Make the prompt/echo visible before the shell blocks for input. */
        shell_flush();return 0;
    }
    if(result!=1)shell_stop(-5);
    ++shell_received;return value;
}

static void shell_flush(void) {
    if(!shell_output_used)return;
    uint64_t now=shell_clock();
    uint64_t timeout=shell_deadline-now;if(timeout>1000U)timeout=1000U;
    uint32_t completed=0;
    int status=reist_x64_console_write(shell_output,shell_output_used,(uint32_t)timeout,&completed);
    shell_written+=completed;
    if(status || completed!=shell_output_used)shell_stop(status?status:-5);
    shell_output_used=0;
    (void)shell_clock();
}
static void shell_write(const char *text,uint32_t count) {
    if(++shell_operations>4096U || count>16384U-shell_written-shell_output_used)shell_stop(-110);
    if(!shell_deadline)(void)shell_clock();
    for(uint32_t i=0;i<count;++i) {
        shell_output[shell_output_used++]=text[i];
        if(shell_output_used==sizeof(shell_output) || text[i]=='\n')shell_flush();
    }
}
void x86os_putchar(char value) { shell_write(&value,1); }
void x86os_puts(const char *text) {
    if(!text)shell_stop(-22);
    uint32_t length=0;
    while(length<4096U && text[length])++length;
    if(length==4096U)shell_stop(-22);
    if(length)shell_write(text,length);
}
void x86os_print_number(int value) {
    char buffer[12];unsigned length=0;
    uint32_t magnitude=value<0?0U-(uint32_t)value:(uint32_t)value;
    do { buffer[length++]=(char)('0'+magnitude%10U);magnitude/=10U; } while(magnitude);
    if(value<0)buffer[length++]='-';
    for(unsigned i=0;i<length/2U;++i) {
        char c=buffer[i];buffer[i]=buffer[length-1U-i];buffer[length-1U-i]=c;
    }
    shell_write(buffer,length);
}
int x86os_terminal_input(uint32_t operation,int pid,uint32_t generation) {
    if(operation!=REIST_TERMINAL_CHECK && operation!=REIST_TERMINAL_ATTACH_CONSOLE)return -95;
    if(pid || generation)return -22;
    (void)shell_clock();
    int64_t result=reist_x64_syscall3(REIST_X64_SYS_READ,0,0,0);
    return result<=0 && result>=-4095?(int)result:-5;
}

/* Not bound in this finite profile: no output writes, syscall, fallback or
 * fake success. Keep real public signatures for later service adapters. */
int x86os_getcwd(char *buffer,size_t size) { (void)buffer;(void)size;return -38; }
int x86os_chdir(const char *path) { (void)path;return -38; }
int x86os_drive_info(uint32_t index,x86os_drive_info_t *info) { (void)index;(void)info;return -38; }
int x86os_spawnv(const char *path,int argc,const char *const *argv) { (void)path;(void)argc;(void)argv;return -38; }
int x86os_wait(int pid,int *status) { (void)pid;(void)status;return -38; }
int x86os_kill(int pid) { (void)pid;return -38; }
int x86os_process_identity_of(int pid,x86os_process_identity_t *identity) { (void)pid;(void)identity;return -38; }
int x86os_usb_diagnostics(x86os_usb_diagnostics_t *info) { (void)info;return -38; }
int x86os_network_control(const x86os_network_control_request_t *request,x86os_network_control_result_t *result) {
    (void)request;(void)result;return -38;
}
int reist_vfs_stat(const char *path,x86os_file_info_t *info,uint32_t timeout_ms) {
    (void)path;(void)info;(void)timeout_ms;return -38;
}
int reist_vfs_readdir_at(const char *path,uint32_t index,x86os_file_info_t *info,uint32_t timeout_ms) {
    (void)path;(void)index;(void)info;(void)timeout_ms;return -38;
}
