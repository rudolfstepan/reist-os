/* Real independently linked ELF; supplied only through the generated disk. */
#include <reist/x86_64/syscall.h>
#include <x86os.h>
int main(unsigned long long argc,char **argv,char **envp) {
    if(argc!=3 || argv[3] || envp[0]) return 200;
    const char *name="/boot.prg";
    for(unsigned n=0;n<10;n++) if(argv[0][n]!=name[n]) return 201;
    uint32_t channel=0;
    for(unsigned n=0;n<8;n++) {
        unsigned c=(unsigned char)argv[1][n];
        if(c>='0'&&c<='9') c-='0';else if(c>='a'&&c<='f') c=c-'a'+10;else return 202;
        channel=(channel<<4)|c;
    }
    if(!channel || argv[1][8] || argv[2][1] || argv[2][0]<'0' || argv[2][0]>'3') return 203;
    if(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)!=-13 ||
       reist_x64_syscall1(REIST_SYS_TASK_CONTROL,0)!=-13) return 204;
    x86os_ipc_message_t m={1,140,16,{0}};
    uint64_t pid=(uint64_t)reist_x64_syscall0(REIST_X64_SYS_GETPID);
    for(unsigned n=0;n<8;n++) {m.payload[n]=(unsigned char)(pid>>(8*n));m.payload[n+8]="ELF64RO!"[n];}
    /* Same bounded startup race as an imported child: wait for its exact grant. */
    int result=-9;
    for(unsigned n=0;n<20 && result==-9;n++) {
        result=(int)reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT,channel,(uintptr_t)&m,1000);
        if(result==-9 && reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10)) return 205;
    }
    if(result) return 206;
    if(argv[2][0]=='1') __asm__ volatile("ud2");
    if(argv[2][0]=='2') for(;;) __asm__ volatile("pause");
    if(argv[2][0]=='3') for(unsigned n=0;n<20;n++)
        if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,100)) return 207;
    return 82;
}
