/* Serial byte qualification, not another shell or command dispatcher. */
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/console.h>
#define CALL0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define CALL1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define IO(n,fd,p,size) reist_x64_syscall3(REIST_X64_SYS_##n,fd,(uintptr_t)(p),size)
#define REQUIRE(x,e) do { if(!(x))return (e); } while(0)
static volatile uint64_t console_witness[8] __attribute__((used));
int main(uint64_t argc,char **argv,char **envp) {
    REQUIRE(argc==2 && argv[1][0]=='0'+PROGRAM_ID && !argv[1][1] && !argv[2] && !envp[0],200);
    uint64_t pid=(uint64_t)CALL0(GETPID);console_witness[0]=pid;
#if PROGRAM_ID!=0
    unsigned char byte=0x5a;
    REQUIRE(IO(READ,0,&byte,1)==-13 && IO(WRITE,1,&byte,1)==-13 && byte==0x5a,201);
    console_witness[1]=0x44454e494544;
    for(unsigned n=0;n<5;n++) REQUIRE(!CALL1(SLEEP_MS,100),202);
    console_witness[2]=5;return 61+PROGRAM_ID;
#else
    uint32_t done=0;unsigned char *bytes=(void *)(uintptr_t)CALL1(MALLOC,128);
    REQUIRE((intptr_t)bytes>0 && (uintptr_t)bytes>=0x100000000ULL,203);
    for(unsigned n=0;n<128;n++) bytes[n]=0xa5;
    REQUIRE(IO(READ,1,bytes,1)==-9 && IO(WRITE,0,bytes,1)==-9,204);
    REQUIRE(IO(READ,0,bytes,65)==-22 && IO(WRITE,1,bytes,UINT64_MAX)==-22,205);
    REQUIRE(IO(READ,0,0,0)==0 && IO(WRITE,1,0,0)==0,206);
    REQUIRE(IO(READ,0,0,1)==-14 && IO(WRITE,1,0,1)==-14,207);
    REQUIRE(IO(READ,0,(void *)0x400000,1)==-14 &&
            IO(WRITE,1,(void *)0xffff800000000000ULL,1)==-14,208);
    REQUIRE(IO(READ,0,(void *)UINT64_MAX,64)==-14,209);
    REQUIRE(reist_x64_syscall4(REIST_X64_SYS_WRITE,1,(uintptr_t)bytes,1,1)==-22,210);
    for(unsigned n=0;n<128;n++) REQUIRE(bytes[n]==0xa5,211);
    console_witness[1]=0x4e45474154495645ULL;
    const char ready[]="NATIVE_CONSOLE_READY\n";
    REQUIRE(!reist_x64_console_write(ready,sizeof(ready)-1,500,&done) && done==sizeof(ready)-1,212);
    REQUIRE(!reist_x64_console_read(bytes,1,500,&done) && done==1,213);
    unsigned mode=bytes[0];REQUIRE(mode=='N' || mode=='F' || mode=='C' || mode=='T',214);
    console_witness[2]=mode;
    if(mode=='F') __asm__ volatile("ud2");
    if(mode=='C') for(;;) __asm__ volatile("pause");
    if(mode=='T') {
        REQUIRE(reist_x64_console_read(bytes+1,64,200,&done)==-110 && !done,215);
        for(unsigned n=1;n<128;n++) REQUIRE(bytes[n]==0xa5,216);
    } else {
        REQUIRE(!reist_x64_console_read(bytes+1,64,500,&done) && done==64,217);
        for(unsigned n=0;n<64;n++) REQUIRE(bytes[n+1]=='a'+n%26,218);
        REQUIRE(!reist_x64_console_write(bytes+1,64,500,&done) && done==64,219);
        for(unsigned n=65;n<128;n++) REQUIRE(bytes[n]==0xa5,220);
        console_witness[3]=64;
    }
    REQUIRE(!CALL1(FREE,bytes),221);console_witness[4]=1;return mode=='T'?65:61;
#endif
}
