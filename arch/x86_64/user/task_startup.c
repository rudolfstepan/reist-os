#include <reist/x86_64/task.h>
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define REQUIRE(x,e) do { if(!(x)) return (e); } while(0)
#if PROGRAM_ID == 0 || PROGRAM_ID == 2
static void message(volatile uint32_t m[35]) {
    for(unsigned i=0;i<35;i++) m[i]=0;
    m[0]=1;m[1]=140;m[2]=16;
}
#endif
#if PROGRAM_ID == 0
static __attribute__((noinline)) int64_t control(unsigned op,uint64_t handle,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,handle,0,timeout,0,0,0};
    return reist_x64_task_control(&q);
}
static void number(char *out,uint32_t n) {
    for(unsigned i=0;i<8;i++) out[i]="0123456789abcdef"[(n>>(28-i*4))&15];
    out[8]=0;
}
static __attribute__((noinline)) int64_t create(reist_task_startup_v1_t *s) {
    return reist_x64_task_create(5,MASK,32,s);
}
#elif PROGRAM_ID == 2
/* Two genuinely private RW pages exercise all ten CREATE acquisitions:
 * three image pages, four tables, two private pages and the stack. */
static volatile uint32_t private_marker=0x12345678;
static volatile unsigned char private_zeroes[4096];
static uint32_t number(const char *p) {
    uint32_t n=0;
    for(unsigned i=0;i<8;i++) {
        unsigned c=(unsigned char)p[i];
        if(c>='0' && c<='9') c-='0';
        else if(c>='a' && c<='f') c=c-'a'+10;
        else return 0;
        n=(n<<4)|c;
    }
    return p[8]?0:n;
}
#endif
int main(int argc,char **argv,char **envp) {
    REQUIRE(argc>=0 && argc<=8 && !argv[argc] && !envp[0],200);
#if PROGRAM_ID == 0
    REQUIRE(argc==2 && argv[1][0]=='0',201);
    REQUIRE(S1(SLEEP_MS,1000)==-22,242); /* Existing per-call bound stays exact. */
    int64_t heap=S1(MALLOC,4096);REQUIRE(heap>0,202);
    reist_task_startup_v1_t *s=(void*)(uintptr_t)heap;
    const char *empty[1]={""};
    REQUIRE(reist_x64_startup_init(s,0,0)==0,203);
    s->version=2;REQUIRE(create(s)==-22,204);s->version=1;
    s->struct_size=1039;REQUIRE(create(s)==-22,205);s->struct_size=1040;
    s->argc=9;REQUIRE(create(s)==-7,206);s->argc=0;
    s->arguments[7][127]=1;REQUIRE(create(s)==-22,207);s->arguments[7][127]=0;
    REQUIRE(create((void*)(uintptr_t)0x100500000)==-14,208);
    s->argc=1;for(unsigned j=0;j<128;j++) s->arguments[0][j]='x';
    REQUIRE(create(s)==-7,209);
    REQUIRE(reist_x64_startup_init(s,0,0)==0,210);
#if STARTUP_CASE == 1
    REQUIRE(create(s)==-12,211);
#endif
    int64_t child=create(s);REQUIRE(child>0 && control(2,child,1000)==60,212);
    REQUIRE(reist_x64_startup_init(s,1,empty)==0,213);
    child=create(s);REQUIRE(child>0 && control(2,child,1000)==61,214);
    uint32_t previous=0;
    for(unsigned iteration=0;iteration<(STARTUP_CASE==1?5U:6U);iteration++) {
        unsigned mode=iteration==1?1:iteration==2?2:iteration==4?3:0;
        uint32_t endpoint=0;REQUIRE(S1(IPC_CREATE,&endpoint)==0 && endpoint!=previous,215);
        char current[9],old[9],parent[9],sequence[9],kind[9],maximum[128];
        number(current,endpoint);number(old,previous);number(parent,(uint32_t)S0(GETPID));
        number(sequence,iteration+1);number(kind,mode);
        for(unsigned i=0;i<127;i++) maximum[i]='Z';
        maximum[127]=0;
        const char *args[8]={"worker",current,old,parent,sequence,kind,"",maximum};
        REQUIRE(reist_x64_startup_init(s,8,args)==0,216);
        child=create(s);REQUIRE(child>0,217);
        /* Parent source is mutable; the child must already own a full copy. */
        for(unsigned i=0;i<sizeof(*s);i++) ((volatile unsigned char*)s)[i]='X';
        S1(SLEEP_MS,20);
        REQUIRE(S3(IPC_DELEGATE,endpoint,(uint64_t)child>>32,1)==0,218);
        volatile uint32_t m[35];message(m);
        REQUIRE(S3(IPC_RECEIVE_TIMEOUT,endpoint,m,1000)==0,219);
        REQUIRE(m[2]==16 && m[3]==(uint32_t)((uint64_t)child>>32) && m[4]==(uint32_t)S0(GETPID) && m[6]==1,220);
        if(mode==3) REQUIRE(m[5]!=iteration+1,221);
        else REQUIRE(m[5]==iteration+1,222);
        if(mode==2 || mode==3) {
            REQUIRE(control(2,child,1)==-110,223);
            REQUIRE(control(3,child,0)==0 && control(2,child,1000)==(2LL<<32),224);
        } else REQUIRE(control(2,child,1000)==(mode==1?((1LL<<32)|134):68),225);
        REQUIRE(control(2,child,1)==-10,226);
        REQUIRE(S3(IPC_DELEGATE,endpoint,(uint64_t)child>>32,1)==-3,227);
        REQUIRE(S1(IPC_CLOSE,endpoint)==0,228);previous=endpoint;
    }
    REQUIRE(reist_x64_startup_init(s,0,0)==0 && create(s)==-11,229);
    return 70;
#elif PROGRAM_ID == 1
    REQUIRE(argc==2 && argv[1][0]=='1',230);
    for(unsigned i=0;i<12;i++) S1(SLEEP_MS,100);
    return 71;
#elif PROGRAM_ID == 2
    REQUIRE(private_marker==0x12345678,244);
    for(unsigned i=0;i<sizeof(private_zeroes);i++) REQUIRE(!private_zeroes[i],245);
    private_marker=(uint32_t)S0(GETPID);
    private_zeroes[0]=1;private_zeroes[4095]=2;
    if(argc==0) return 60;
    if(argc==1) { REQUIRE(!argv[0][0],231);return 61; }
    REQUIRE(argc==8 && argv[0][0]=='w' && !argv[6][0],232);
    for(unsigned i=0;i<127;i++) REQUIRE(argv[7][i]=='Z',233);
    REQUIRE(!argv[7][127],234);
    uint32_t endpoint=number(argv[1]),old=number(argv[2]),parent=number(argv[3]);
    uint32_t sequence=number(argv[4]),mode=number(argv[5]);
    REQUIRE(endpoint && parent && sequence && mode<=3,235);
    volatile uint32_t m[35];message(m);
    m[3]=(uint32_t)S0(GETPID);m[4]=parent;m[5]=mode==3?sequence+1:sequence;m[6]=1;
    if(old) REQUIRE(S3(IPC_SEND_TIMEOUT,old,m,0)==-9,236);
    uint64_t deadline=(uint64_t)S0(MONOTONIC_MS)+200;
    int64_t sent=S3(IPC_SEND_TIMEOUT,endpoint,m,0);
    REQUIRE(sent==-9 || sent==-13,237); /* Numeric handle alone is no authority. */
    while(sent==-9 || sent==-13) {
        REQUIRE((uint64_t)S0(MONOTONIC_MS)<deadline,238);
        S1(SLEEP_MS,10);sent=S3(IPC_SEND_TIMEOUT,endpoint,m,0);
    }
    REQUIRE(sent==0,239);
    if(mode==1) __asm__ volatile("ud2");
    if(mode==2 || mode==3) {
        for(unsigned i=0;i<10;i++) REQUIRE(S1(SLEEP_MS,100)==0,243);
        return 240;
    }
    return 68;
#else
    return 241; /* This catalog role must never be published in this profile. */
#endif
}
