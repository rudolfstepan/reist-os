#include <reist/x86_64/task.h>
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#if FAMILY_CASE == 2
#define CHILD_RESULT ((1LL<<32)|134)
#elif FAMILY_CASE == 3
#define CHILD_RESULT ((1LL<<32)|256)
#else
#define CHILD_RESULT 42
#endif
static volatile unsigned marker=0x12345678;
static volatile unsigned char zeroes[4096];
#if PROGRAM_ID == 0 || PROGRAM_ID == 2
static int64_t create(unsigned image) {
    reist_task_control_request_t q={1,64,1,0,0,image,0,MASK,32,0};
    return reist_x64_task_control(&q);
}
#endif
#if PROGRAM_ID == 0
static int64_t control(unsigned op,uint64_t target,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,target,0,timeout,0,0,0};
    return reist_x64_task_control(&q);
}
#endif
int main(int argc,char **argv,char **envp) {
    if(argc!=2 || argv[2] || envp[0] || argv[1][0]!='0'+PROGRAM_ID || marker!=0x12345678) return 200;
    for(unsigned i=0;i<sizeof(zeroes);i++) if(zeroes[i]) return 201;
    marker=PROGRAM_ID;
#if PROGRAM_ID == 0
    if(reist_x64_task_control((void*)(uintptr_t)0x100500000)!=-14) return 214;
    reist_task_control_request_t invalid={2,64,1,0,0,5,0,MASK,32,0};
    if(reist_x64_task_control(&invalid)!=-22) return 215;
    uint64_t peer=((reist_x64_syscall0(REIST_X64_SYS_GETPID)+1)<<32)|1;
    if(control(2,peer,1)!=-10) return 216;
#if FAMILY_CASE == 4
    if(create(5)!=-12) return 217;
#endif
    int64_t a=create(5), b=create(6);
    if(a<=0 || b<=0 || a==b || create(5)!=-11) return 202;
#if FAMILY_CASE == 1
    reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,20);
    __asm__ volatile("ud2");
#endif
#if FAMILY_CASE == 5
    reist_x64_syscall0(REIST_X64_SYS_YIELD);
    if(control(3,b,0)!=0) return 218;
#endif
    if(control(2,a,1)!=-110) return 203;
    if(control(2,a,1000)!=CHILD_RESULT) return 204;
    if(control(2,a,1)!=-10) return 205;
    if(control(3,b,0)!=0) return 206;
    if(control(2,b,1000)!=(2LL<<32)) return 207;
    for(unsigned n=0;n<(FAMILY_CASE==4?5U:6U);n++) {
        int64_t c=create(5);
        if(c<=0 || c==a || c==b) return 208;
        if(control(2,c,1000)!=CHILD_RESULT) return 209;
    }
    if(create(5)!=-11) return 210;
    return 40;
#elif PROGRAM_ID == 1
    for(unsigned n=0;n<12;n++) reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,100);
    return 41;
#elif PROGRAM_ID == 2
    if(create(5)!=-13) return 211;
    int64_t p=reist_x64_syscall1(REIST_X64_SYS_MALLOC,65536);
    if(p<=0) return 212;
    ((volatile unsigned char *)(uintptr_t)p)[65535]=42;
    reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,100);
#if FAMILY_CASE == 2
    __asm__ volatile("ud2");
#elif FAMILY_CASE == 3
    for(;;) __asm__ volatile("pause");
#endif
    return 42;
#else
    /* Cancellation must also fence a sleeping child with an owned heap. */
    int64_t p=reist_x64_syscall1(REIST_X64_SYS_MALLOC,FAMILY_CASE==5?0x8000000:65536);
    if(p<=0) return 213;
    ((volatile unsigned char *)(uintptr_t)p)[0]=43;
    uint32_t endpoint=0;
    volatile uint32_t message[35];
    for(unsigned i=0;i<35;i++) message[i]=0;
    message[0]=1;message[1]=140;
    if(reist_x64_syscall1(REIST_X64_SYS_IPC_CREATE,(uintptr_t)&endpoint)!=0) return 219;
    if(reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,endpoint,(uintptr_t)message,1000)!=-110) return 220;
    return 43;
#endif
}
