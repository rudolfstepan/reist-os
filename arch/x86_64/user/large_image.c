/* Bounded Ring3 memory/lifecycle fixture, not a shell or filesystem service. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#ifdef REIST_NATIVE_LARGE_PERIODIC
#define reist_x64_task_import_large reist_x64_task_import_large_periodic
#endif
#line 4
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define REQUIRE(x,e) do {if(!(x))return (e);}while(0)
#if PROGRAM_ID==0 || PROGRAM_ID==2
static void initialize_message(volatile uint32_t *message,unsigned length) {
    for(unsigned i=0;i<35;i++)message[i]=0;
    message[0]=1;message[1]=140;message[2]=length;
}
#endif
#if PROGRAM_ID==0
#ifdef REIST_NATIVE_LARGE_PERIODIC
/* Qualification input: the observer supplies the actual admitted root epoch. */
volatile uint64_t reist_large_image_selection[3]={0x31474d494752414cULL,0,0};
static int wait_next_cpu_period(void) {
    uint64_t now=(uint64_t)S0(MONOTONIC_MS),origin=reist_large_image_selection[2];
    if(now<origin)return -1;
    unsigned remaining=1000-(unsigned)((now-origin)%1000);
    for(unsigned idle=0;idle<10 && remaining;idle++) {
        unsigned step=remaining>100?100:remaining;
        if(S1(SLEEP_MS,step)!=0)return -1;
        remaining-=step;
    }
    return remaining?-1:0;
}
#else
#line 16
volatile uint64_t reist_large_image_selection[2]={0x31474d494752414cULL,0};
#endif
#line 17
static int64_t control(unsigned op,uint64_t handle,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,handle,0,timeout,0,0,0};
    return reist_x64_task_control(&q);
}
static void mutate(void *p) {
    volatile unsigned char *b=p;
    for(unsigned i=0;i<REIST_X64_PREPARED_V3_BYTES;i++) b[i]=0x5a;
}
#elif PROGRAM_ID==2
#line 26
static const unsigned char immutable[81920] __attribute__((section(".rodata.memory_witness")))={[0]=0x53,[81919]=0xa7};
struct memory_witness {uint64_t magic,owner,stack,bytes,checksum,mode;};
static volatile struct memory_witness witness __attribute__((section(".data.memory_witness")))={0x31474d494752414cULL,0,0,0,0,0};
static volatile unsigned char private_bytes[8192];
static volatile unsigned char middle_bytes[4096] __attribute__((section(".large_middle")));
static volatile unsigned char last_bytes[4096] __attribute__((section(".large_last")));
static __attribute__((noinline,section(".large_end_text"))) int high_execute(void) {
    for(unsigned i=0;i<4096;i++) {
        if(middle_bytes[i]!=(unsigned char)(i^0x31) || last_bytes[i]!=(unsigned char)(i^0x93))return 231;
    }
    return 0;
}
static __attribute__((noinline)) int exercise(unsigned mode,unsigned replacement) {
    volatile unsigned char stack[12288];
    uint64_t sum=0;
    for(unsigned i=0;i<sizeof(stack);i++){stack[i]=(unsigned char)(i^0x6a);sum+=stack[i];}
    for(unsigned i=0;i<sizeof(immutable);i++) {
        unsigned expected=i==0?0x53:i==sizeof(immutable)-1?0xa7+replacement:0;
        REQUIRE(((const volatile unsigned char*)immutable)[i]==expected,211);
    }
    for(unsigned i=0;i<sizeof(private_bytes);i++){REQUIRE(private_bytes[i]==0,212);private_bytes[i]=(unsigned char)(i^0xc7);}
    REQUIRE((uintptr_t)middle_bytes==0x480000 && (uintptr_t)last_bytes==0x4fe000 &&
        (uintptr_t)high_execute>=0x4ff000 && (uintptr_t)high_execute<0x500000,232);
    for(unsigned i=0;i<4096;i++) {
        REQUIRE(middle_bytes[i]==0 && last_bytes[i]==0,233);
        middle_bytes[i]=(unsigned char)(i^0x31);last_bytes[i]=(unsigned char)(i^0x93);
    }
    REQUIRE(high_execute()==0,234);
    witness.owner=(uint64_t)S0(GETPID);witness.stack=(uintptr_t)stack;
    witness.bytes=sizeof(stack);witness.checksum=sum;witness.mode=mode;
    REQUIRE((uintptr_t)stack>=0x408000 && (uintptr_t)stack+sizeof(stack)<=0x410000,213);
    REQUIRE((uintptr_t)exercise>=0x410000,214);
    REQUIRE(S0(MONOTONIC_MS)>=0,215); /* observable while the real stack is live */
#ifdef REIST_NATIVE_LARGE_PERIODIC
    if(mode==0) {
        for(unsigned idle=0;idle<10;idle++)REQUIRE(S1(SLEEP_MS,100)==0,238);
        /* Six bounded bursts separated by idle periods; the observer verifies
         * actual sample accounting, never infers CPU samples from wall time. */
        for(unsigned period=0;period<6;period++) {
            uint64_t until=(uint64_t)S0(MONOTONIC_MS)+80;
            while((uint64_t)S0(MONOTONIC_MS)<until)
                for(unsigned spin=0;spin<32768;spin++)__asm__ volatile("pause");
            for(unsigned idle=0;idle<9;idle++)REQUIRE(S1(SLEEP_MS,100)==0,235);
        }
    }
#endif
#line 59
    if(mode==1)*(volatile unsigned char*)0x407fff=1;
    if(mode==2){stack[0]=0xc3;((void(*)(void))(uintptr_t)stack)();}
    if(mode==3)*(volatile unsigned char*)0x410000=1; /* first RX text page */
    if(mode==4)for(;;)__asm__ volatile("pause"); /* deliberate bounded-by-kernel fault */
    if(mode==5)for(unsigned i=0;i<20;i++)REQUIRE(S1(SLEEP_MS,100)==0,216);
    for(unsigned i=0;i<sizeof(stack);i++)REQUIRE(stack[i]==(unsigned char)(i^0x6a),217);
    return 80;
}
#endif
#line 68
int main(int argc,char **argv) {
#if PROGRAM_ID==0
    (void)argc;(void)argv;
    REQUIRE(reist_large_image_selection[0]==0x31474d494752414cULL && reist_large_image_selection[1]<=6,230);
    void *record=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V3_BYTES);
    REQUIRE((int64_t)(uintptr_t)record>0,201);
    uint64_t previous=0;
    for(unsigned round=0;round<2;round++) {
        unsigned mode=round?0:(unsigned)reist_large_image_selection[1];
        if(mode==6)mode=0;
        uint32_t endpoint=0;REQUIRE(S1(IPC_CREATE,&endpoint)==0 && endpoint,219);
        char port[9];for(unsigned i=0;i<8;i++)port[i]="0123456789abcdef"[(endpoint>>(28-i*4))&15];port[8]=0;
        char text[2]={(char)('0'+mode),0};const char *arguments[]={round?"wide-new":"wide-child",text,port};
        reist_task_startup_v1_t startup;
        reist_task_profile_v1_t profile={1,40,{MASK,0,0},0};
        REQUIRE(reist_x64_startup_init(&startup,3,arguments)==0,202);
        REQUIRE(reist_x64_image_prepare_v3(record,import_blob,sizeof(import_blob))==0,203);
        if(round) {
            /* Distinct valid immutable bytes force a fresh image on slot reuse. */
            unsigned matches=0;unsigned char *b=record;
            for(unsigned p=16;p+20<256;p++) {
                unsigned off=288+p*4096;
                if(b[24+p]==4 && b[off]==0x53 && b[off+81919]==0xa7) {
                    b[off+81919]=0xa8;++matches;
                }
            }
            REQUIRE(matches==1,218);
        }
        int64_t child=reist_x64_task_import_large(record,&profile,32,&startup);
        if(!round && reist_large_image_selection[1]==6){REQUIRE(child==-12,204);child=reist_x64_task_import_large(record,&profile,32,&startup);}
        REQUIRE(child>0 && (uint64_t)child>previous,205);previous=(uint64_t)child;
        REQUIRE(S3(IPC_DELEGATE,endpoint,(uint64_t)child>>32,2)==0,220);
        mutate(record); /* admitted image and stack remain immutable private copies */
        volatile uint32_t message[35];initialize_message(message,4);message[3]=0x57494445;
        REQUIRE(S3(IPC_SEND_TIMEOUT,endpoint,message,0)==0,221);
#ifdef REIST_NATIVE_LARGE_PERIODIC
        /* Separate fault cleanup from construction under the same CPU quota. */
        if(mode>=1 && mode<=4)REQUIRE(wait_next_cpu_period()==0,241);
#endif
#line 103
        int64_t status=control(2,(uint64_t)child,mode==5?100:1000);
#ifdef REIST_NATIVE_LARGE_PERIODIC
        /* Keep each WAIT <=1000ms; finite normal-service proof <=8 waits. */
        if(mode==0)for(unsigned poll=1;poll<8 && status==-110;poll++)
            status=control(2,(uint64_t)child,1000);
#endif
#line 104
#ifdef REIST_NATIVE_LARGE_PERIODIC
        if(mode==5) {
            REQUIRE(status==-110,206);
            /* The child deliberately remains asleep for2000ms. Keep the
             * supervisor's construction and cancellation in separate windows. */
            for(unsigned idle=0;idle<10;idle++)REQUIRE(S1(SLEEP_MS,100)==0,237);
            REQUIRE(control(3,(uint64_t)child,0)==0,207);
            status=control(2,(uint64_t)child,1000);
        }
#else
#line 104
        if(mode==5){REQUIRE(status==-110,206);REQUIRE(control(3,(uint64_t)child,0)==0,207);status=control(2,(uint64_t)child,1000);}
#endif
#line 105
        int64_t expected=mode>=1 && mode<=3?((1LL<<32)|142):
                         mode==4?((1LL<<32)|256):mode==5?(2LL<<32):80;
        REQUIRE(status==expected,208);
        REQUIRE(S1(IPC_CLOSE,endpoint)==0,222);
#ifdef REIST_NATIVE_LARGE_PERIODIC
        /* Construction/cancellation and the replacement each retain the same
         * immutable CPU quota. Separate this fixture's two startup bursts. */
        if(!round)REQUIRE(wait_next_cpu_period()==0,236);
#endif
#line 109
    }
    return 78;
#elif PROGRAM_ID==1
    (void)argc;(void)argv;
#line 113
    for(unsigned i=0;i<24;i++)REQUIRE(S1(SLEEP_MS,50)==0,209);
    return 77;
#elif PROGRAM_ID==2
#line 116
    REQUIRE(argc==3 && argv && argv[1] && argv[1][0]>='0' && argv[1][0]<='5' && !argv[1][1],210);
    uint32_t endpoint=0;for(unsigned i=0;i<8;i++) {
        unsigned ch=(unsigned char)argv[2][i];
        REQUIRE((ch>='0' && ch<='9') || (ch>='a' && ch<='f'),223);
        endpoint=(endpoint<<4)|(ch<='9'?ch-'0':ch-'a'+10);
    }
    REQUIRE(endpoint && !argv[2][8],223);
    unsigned ready=0;uint64_t deadline=(uint64_t)S0(MONOTONIC_MS)+500;
    for(unsigned attempt=0;attempt<20;attempt++) {
        volatile uint32_t message[35];initialize_message(message,0);
        int64_t received=S3(IPC_RECEIVE_TIMEOUT,endpoint,message,0);
        if(received==0){REQUIRE(message[2]==4 && message[3]==0x57494445,224);ready=1;break;}
        REQUIRE(received==-9 || received==-13 || received==-11 || received==-110,225);
        REQUIRE((uint64_t)S0(MONOTONIC_MS)<deadline && S1(SLEEP_MS,10)==0,226);
    }
    REQUIRE(ready,227);
    return exercise((unsigned)(argv[1][0]-'0'),argv[0][5]=='n');
#else
#line 134
    (void)argc;(void)argv;return 77;
#endif
#line 136
}
