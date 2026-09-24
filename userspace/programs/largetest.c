/* Ordinary native shell consumer of the explicit large image/capture profile. */
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/terminal.h>
#include <reist/x86_64/console.h>
#include <stdint.h>
static const unsigned char immutable[65536] __attribute__((section(".rodata.memory_witness")))={[0]=0x53,[65535]=0xa7};
volatile uint64_t reist_large_file_witness[8] __attribute__((section(".data.memory_witness")))={0x31454c494647524cULL};
static volatile unsigned char low[8192];
static volatile unsigned char middle[4096] __attribute__((section(".large_middle")));
static volatile unsigned char last[4096] __attribute__((section(".large_last")));
static __attribute__((noinline,section(".large_end_text"))) int high_check(void) {
    for(unsigned n=0;n<4096;n++)if(middle[n]!=(unsigned char)(n^0x31) || last[n]!=(unsigned char)(n^0x93))return 1;
    return 0;
}
int main(int argc,char **argv) {
    if(argc<1 || argc>2 || !argv || !argv[0])return 21;
    if((uintptr_t)middle!=0x480000 || (uintptr_t)last!=0x4fe000 || (uintptr_t)high_check<0x4ff000)return 22;
    for(unsigned n=0;n<65536;n++)if(((const volatile unsigned char*)immutable)[n]!=(n==0?0x53:n==65535?0xa7:0))return 23;
    for(unsigned n=0;n<8192;n++){if(low[n])return 24;low[n]=(unsigned char)(n^0xc7);}
    for(unsigned n=0;n<4096;n++){
        if(middle[n] || last[n])return 25;
        middle[n]=(unsigned char)(n^0x31);last[n]=(unsigned char)(n^0x93);
    }
    if(high_check())return 26;
    reist_large_file_witness[1]=1;
    reist_large_file_witness[2]=(uint64_t)reist_x64_syscall0(REIST_X64_SYS_GETPID);
    reist_large_file_witness[3]=(uintptr_t)low;reist_large_file_witness[4]=(uintptr_t)middle;
    reist_large_file_witness[5]=(uintptr_t)last;reist_large_file_witness[6]=(uintptr_t)high_check;
    if(argc==2 && argv[1] && argv[1][0]=='c')__asm__ volatile("ud2");
    /* CREATE can enter this child before the shell transfers the terminal.
     * Use the same bounded CHECK/sleep handshake as the ordinary app adapter. */
    int64_t previous=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    if(previous<0 || previous>INT64_MAX-1000)return 28;
    int64_t deadline=previous+1000;
    unsigned ready=0;
    for(unsigned n=0;n<100;n++) {
        int64_t now=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
        if(now<previous || now>=deadline)return 28;
        previous=now;
        if(!reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0)){ready=1;break;}
        if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))return 28;
    }
    if(!ready)return 28;
    static const char message[]="LARGETEST_OK\n";
    uint32_t completed=0;
    int result=reist_x64_console_write(message,sizeof(message)-1,1000,&completed);
    return !result && completed==sizeof(message)-1?0:27;
}
