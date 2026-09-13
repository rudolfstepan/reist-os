/* QEMU read-only reference consumer. All deliberate faults are Ring3-only. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#include "../../../userspace/drivers/ata/native_pio.h"
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define REQUIRE(x,e) do {if(!(x))return (e);}while(0)
#if PROGRAM_ID == 0 || PROGRAM_ID == 2
static void message(uint32_t m[35]) {for(unsigned n=0;n<35;n++)m[n]=0;m[0]=1;m[1]=140;m[2]=16;}
static int64_t pio(uint64_t owner,unsigned operation,unsigned port,unsigned value) {
    reist_native_pio_request q={1,64,operation,0,owner,port,value,0,0,0,0,0};return reist_x64_pio(&q);
}
#endif
#if PROGRAM_ID == 0
static int64_t control(unsigned op,uint64_t h,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,h,0,timeout,0,0,0};return reist_x64_task_control(&q);
}
static void number(char *out,uint32_t v) {for(unsigned n=0;n<8;n++)out[n]="0123456789abcdef"[(v>>(28-4*n))&15];out[8]=0;}
static void image_words(void *out,const void *source) {
    typedef uint64_t word_t __attribute__((may_alias,aligned(1)));
    volatile word_t *p=out;const word_t *q=source;
    for(unsigned n=0;n<36896/8;n++)p[n]=q?q[n]:0x5a5a5a5a5a5a5a5aULL;
}
static int64_t create(void *record,reist_task_startup_v1_t *s,reist_task_profile_v1_t *p) {
    /* One parsed immutable fixture, copied to the mutable import transport.
     * Neither record is borrowed by the kernel after CREATE returns. */
    static void *prepared;
    if(!prepared) {
        int64_t allocated=S1(MALLOC,36896);if(allocated<=0)return -12;
        prepared=(void*)(uintptr_t)allocated;
        if(reist_x64_image_prepare(prepared,import_blob,sizeof(import_blob))) {
            S1(FREE,prepared);prepared=0;return -22;
        }
    }
    image_words(record,prepared);
    int64_t result=reist_x64_task_import_profile(record,p,32,s);
    image_words(record,0);
    return result;
}
#elif PROGRAM_ID == 2
static volatile uint32_t private_marker=0x12345678;
static volatile unsigned char private_zeroes[4096];
static unsigned char sector[512];
typedef struct {uint64_t owner;uint32_t endpoint,mode;unsigned reading,chunks;} Driver;
static int notice(Driver *d,unsigned phase,unsigned value) {
    uint32_t m[35];message(m);m[3]=(uint32_t)S0(GETPID);m[4]=d->mode;m[5]=phase;m[6]=value;
    return (int)S3(IPC_SEND_TIMEOUT,d->endpoint,m,1000);
}
static int64_t port(void *v,reist_native_pio_request *q) {
    Driver *d=v;int64_t r=reist_x64_pio(q);
    if(!r && q->operation==REIST_PIO_WRITE8 && q->port==0x1f7 && q->value==0x20)d->reading=1;
    if(!r && d->reading && q->operation==REIST_PIO_READ16 && ++d->chunks==8 && (d->mode==1 || d->mode==2 || d->mode==4)) {
        if(notice(d,1,256))return -5;
        if(d->mode==1)__asm__ volatile("ud2");
        if(d->mode==4)for(;;)__asm__ volatile("pause"); /* Explicit CPU-quota fault. */
        for(unsigned n=0;n<20;n++)if(S1(SLEEP_MS,100))return -5;
        return -110;
    }
    return r;
}
static uint64_t clock_ms(void *v) {(void)v;return (uint64_t)S0(MONOTONIC_MS);}
static int sleep_ms(void *v,unsigned ms) {(void)v;return (int)S1(SLEEP_MS,ms);}
static uint32_t number(const char *p) {
    uint32_t v=0;for(unsigned n=0;n<8;n++) {unsigned c=(unsigned char)p[n];if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return 0;v=(v<<4)|c;}return p[8]?0:v;
}
#endif
int main(int argc,char **argv,char **envp) {
    REQUIRE(argc>=0 && argc<=8 && !argv[argc] && !envp[0],200);
#if PROGRAM_ID == 0
    REQUIRE(argc==2 && argv[1][0]=='0',201);
    void *record=(void*)(uintptr_t)S1(MALLOC,36896);
    reist_task_startup_v1_t *s=(void*)(uintptr_t)S1(MALLOC,1040);
    REQUIRE((intptr_t)record>0 && (intptr_t)s>0,202);
    reist_task_profile_v1_t profile={1,40,{MASK,1ULL<<49,0},0};
    REQUIRE(!reist_x64_startup_init(s,0,0),203);
    profile.reserved=1;REQUIRE(create(record,s,&profile)==-22,204);profile.reserved=0;
    profile.masks[1]|=1;REQUIRE(create(record,s,&profile)==-13,205);profile.masks[1]&=~1ULL;
    REQUIRE(create(record,s,(void*)(uintptr_t)0x100500000)==-14,206);
#if PIO_CASE == 1
    REQUIRE(create(record,s,&profile)==-12,207);
#endif
    const unsigned modes[8]={0,1,0,2,0,3,4,0};uint64_t previous=0;
    uint32_t endpoint=0;REQUIRE(S1(IPC_CREATE,&endpoint)==0,208);
    char ep[9];number(ep,endpoint);
    for(unsigned iteration=PIO_CASE==1?1:0;iteration<(PIO_CASE>=2?1U:8U);iteration++) {
        unsigned mode=PIO_CASE==3?2:modes[iteration];
        char kind[9];number(kind,mode);
        const char *args[2]={ep,kind};REQUIRE(!reist_x64_startup_init(s,2,args),209);
        int64_t child=create(record,s,&profile);REQUIRE(child>0 && (uint32_t)child==2,210);
        REQUIRE(S3(IPC_DELEGATE,endpoint,(uint64_t)child>>32,1)==0,211);
        REQUIRE(pio(child,REIST_PIO_BIND,0,0)==0,212);
        if(previous)REQUIRE(pio(previous,REIST_PIO_FENCE,0,0)==-13,213);
        REQUIRE(pio(child,REIST_PIO_BIND,0,0)==-13,214);
        uint32_t m[35];message(m);
        REQUIRE(S3(IPC_RECEIVE_TIMEOUT,endpoint,m,1000)==0,215);
        REQUIRE(m[2]==16 && m[3]==(uint32_t)((uint64_t)child>>32) && m[4]==mode,216);
#if PIO_CASE == 3
        REQUIRE(m[5]==1 && m[6]==256,217);__asm__ volatile("ud2");
#endif
        if(mode==2) {
            REQUIRE(m[5]==1 && m[6]==256,218);
            REQUIRE(pio(child,REIST_PIO_FENCE,0,0)==0,219);
            REQUIRE(control(3,child,0)==0,220);
        } else if(mode==1 || mode==4) REQUIRE(m[5]==1 && m[6]==256,221);
        else REQUIRE(m[5]==0 && m[6]==(PIO_CASE==2?19U:0xc0deU),222);
        int64_t expected=mode==1?((1LL<<32)|134):mode==2?(2LL<<32):mode==4?((1LL<<32)|256):PIO_CASE==2?89:80;
        REQUIRE(control(2,child,1000)==expected,223);
        /* Explicit and automatic recovery converge on the same fence/reap. */
        REQUIRE(pio(child,REIST_PIO_FENCE,0,0)==0,224);
        REQUIRE(control(2,child,1)==-10,225);
        previous=child;
    }
    REQUIRE(S1(IPC_CLOSE,endpoint)==0,225);
#if PIO_CASE < 2
    REQUIRE(create(record,s,&profile)==-11,226);
#endif
    return PIO_CASE==2?79:78;
#elif PROGRAM_ID == 1
    REQUIRE(argc==2 && argv[1][0]=='1',227);
    /* Peer must have no DEVICE_CONTROL grant. */
    REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,228);
    for(unsigned n=0;n<18;n++)REQUIRE(S1(SLEEP_MS,100)==0,229);
    return 77;
#elif PROGRAM_ID == 2
    REQUIRE(argc==2 && private_marker==0x12345678,230);
    for(unsigned n=0;n<4096;n++)REQUIRE(!private_zeroes[n],231);
    private_marker=(uint32_t)S0(GETPID);private_zeroes[0]=1;private_zeroes[4095]=2;
    Driver d={((uint64_t)private_marker<<32)|2,number(argv[0]),number(argv[1]),0,0};
    REQUIRE(d.endpoint && d.mode<=4,232);
    int64_t ready=-13;
    for(unsigned n=0;n<20 && ready==-13;n++) {REQUIRE(S1(SLEEP_MS,10)==0,233);ready=pio(d.owner,REIST_PIO_READ8,0x1f7,0);}
    REQUIRE(ready>=0,234);
    reist_pio_ops ops={&d,port,clock_ms,sleep_ms};uint32_t sectors=0;
    int result=reist_pio_identify(&ops,d.owner,&sectors);
    if(result==-19) {REQUIRE(!notice(&d,0,19),235);return 89;}
    REQUIRE(!result && sectors==128,236);
    if(d.mode==3) {
        REQUIRE(pio(d.owner,REIST_PIO_WRITE8,0x1f7,0x30)==-22,237);
        REQUIRE(pio(d.owner,REIST_PIO_WRITE8,0x1f7,0xca)==-22,238);
        REQUIRE(pio(d.owner,REIST_PIO_WRITE8,0x1f0,0)==-22,239);
    }
    REQUIRE(!reist_pio_read(&ops,d.owner,sectors,0,sector),240);
    for(unsigned n=0;n<512;n++)REQUIRE(sector[n]==(unsigned char)(n^0xa5),241);
    REQUIRE(!notice(&d,0,0xc0de),242);return 80;
#else
    return 243;
#endif
}
