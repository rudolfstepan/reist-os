/* Finite hardware-boundary qualification consumer. No shell command or stack. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#include <reist/x86_64/network.h>
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define CHECK(x,n) do {if(!(x))return (n);}while(0)
volatile uint64_t network_witness[12] __attribute__((section(".data.memory_witness")))={0x31414d4454454e52ULL};
#if PROGRAM_ID==0 || PROGRAM_ID==2
static uint64_t now(void){int64_t r=S0(MONOTONIC_MS);if(r<0)__builtin_trap();return (uint64_t)r;}
static int64_t device(reist_network_request_v1 *q){return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,32,(uintptr_t)q);}
static void zero(void *p,unsigned bytes){volatile unsigned char *b=p;while(bytes--)*b++=0;}
static int message(uint32_t ep,unsigned send,unsigned value) {
    uint32_t m[35];zero(m,sizeof(m));m[0]=1;m[1]=140;m[2]=send?4:128;m[3]=value;
    int r=send?(int)S3(IPC_SEND_TIMEOUT,ep,m,100):(int)S3(IPC_RECEIVE_TIMEOUT,ep,m,1000);
    return r?r:(int)m[3];
}
#endif
#if PROGRAM_ID==0
static void hex(char *p,uint32_t v){for(unsigned n=0;n<8;n++)p[n]="0123456789abcdef"[(v>>(28-n*4))&15];p[8]=0;}
static int64_t task(unsigned op,uint64_t child,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,child,0,timeout,0,0,0};return reist_x64_task_control(&q);
}
int main(int argc,char **argv) {
    (void)argc;(void)argv;uint64_t root=(uint64_t)S0(GETPID)<<32;network_witness[2]=root;
    unsigned mode=(unsigned)network_witness[1];CHECK(mode<=7,10);
    void *record=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);CHECK((intptr_t)record>0,11);
    uint64_t last_epoch=0,old=0;
    for(unsigned turn=0;turn<2;turn++) {
        uint32_t ep=0;CHECK(S1(IPC_CREATE,&ep)==0,12);char endpoint[9],fault[2]={(char)('0'+(turn?0:mode)),0};hex(endpoint,ep);
        const char *args[]={"network-driver",endpoint,fault};reist_task_startup_v1_t startup;
        reist_task_profile_v1_t profile={1,40,{(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(1ULL<<53),1ULL<<49,0},0};
        CHECK(!reist_x64_startup_init(&startup,3,args),13);
        CHECK(!reist_x64_image_prepare_v2(record,import_blob,sizeof(import_blob)),14);
        int64_t child=reist_x64_task_import_wide(record,&profile,32,&startup);CHECK(child>0,15);
        CHECK(S3(IPC_DELEGATE,ep,(uint64_t)child>>32,1)==0,16);
        reist_network_request_v1 q={1,64,1,0,(uint64_t)child,0,0,0,0,0,0};
        int64_t epoch=device(&q);CHECK(epoch>0 && (uint64_t)epoch>last_epoch,17);last_epoch=(uint64_t)epoch;
        network_witness[3]=(uint64_t)child;network_witness[4]=last_epoch;
        q.operation=5;q.epoch=last_epoch;q.deadline_ms=now()+100;q.address=(uintptr_t)record;q.length=64;
        CHECK(device(&q)==-13,18);
        int ready=message(ep,0,0);CHECK(ready==(mode==7?19:42),19);network_witness[5]=turn+1;
        if(mode==4 && !turn)__builtin_trap();
        int64_t result=task(2,(uint64_t)child,1000);
        if(result==-110){CHECK(!task(3,(uint64_t)child,0),20);result=task(2,(uint64_t)child,1000);}
        CHECK(result>=0,21);network_witness[6+turn]=(uint64_t)result;
        CHECK(!S1(IPC_CLOSE,ep),22);
        q=(reist_network_request_v1){1,64,8,0,(uint64_t)child,last_epoch,0,0,0,0,0};CHECK(!device(&q),23);
        if(old){q.owner=old;q.epoch=last_epoch-1;CHECK(device(&q)==-116,24);}
        old=(uint64_t)child;
        if(mode==7)break;
    }
    CHECK(!S1(FREE,record),25);network_witness[8]=1;return 82;
}
#elif PROGRAM_ID==2
static uint32_t unhex(const char *p){uint32_t v=0;for(unsigned n=0;n<8;n++){unsigned c=(unsigned char)p[n];unsigned d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;if(d>15)return 0;v=v<<4|d;}return p[8]?0:v;}
static unsigned char buffer[1536];
int main(int argc,char **argv) {
    CHECK(argc==3,30);uint32_t ep=unhex(argv[1]);CHECK(ep,31);unsigned mode=(unsigned)(argv[2][0]-'0');CHECK(mode<=7,32);
    uint64_t owner=(uint64_t)S0(GETPID)<<32|2;network_witness[2]=owner;network_witness[1]=mode;
    reist_network_request_v1 q={1,64,2,0,owner,1,0,0,0,0,0};
    int64_t epoch=-13;
    /* Root publishes binding immediately; query requires the actual epoch.
     * Epoch is monotonically bounded by the two roots/two imports here. */
    for(unsigned n=0;n<100 && epoch<0;n++) {
        for(unsigned e=1;e<=4;e++){q.epoch=e;epoch=device(&q);if(epoch>0)break;}
        if(epoch<0)CHECK(!S1(SLEEP_MS,10),33);
    }
    CHECK(epoch>0,34);q.epoch=(uint64_t)epoch;network_witness[4]=(uint64_t)epoch;
    q.operation=3;q.deadline_ms=now()+1000;int64_t r=device(&q);
    if(mode==7){CHECK(r==-19,35);CHECK(message(ep,1,19)==19,36);return 19;}
    CHECK(!r,37);q.operation=4;
    for(unsigned n=0;n<100;n++){r=device(&q);if(r!=-11)break;CHECK(!S1(SLEEP_MS,10),38);}
    CHECK(!r,39);network_witness[3]=1;
    q.operation=9;r=device(&q);CHECK(r==0x563412005452LL,40);
    for(unsigned n=0;n<64;n++)buffer[n]=(unsigned char)n;
    const unsigned char dest[6]={0x52,0x54,0,0x12,0x34,0x57},src[6]={0x52,0x54,0,0x12,0x34,0x56};
    for(unsigned n=0;n<6;n++){buffer[n]=dest[n];buffer[n+6]=src[n];}buffer[12]=0x88;buffer[13]=0xb5;
    q.operation=5;q.address=(uintptr_t)buffer;q.length=64;q.deadline_ms=now()+100;
    q.flags=1;CHECK(device(&q)==-22,41);q.flags=0;
    q.address=UINT64_MAX-32;CHECK(device(&q)==-14,43);q.address=(uintptr_t)buffer;
    CHECK(!device(&q),44);q.operation=7;q.address=0;q.length=0;
    for(unsigned n=0;n<10;n++){r=device(&q);if(r!=-11)break;CHECK(!S1(SLEEP_MS,10),45);}
    CHECK(!r,46);q.operation=6;q.address=(uintptr_t)buffer;q.length=1536;q.deadline_ms=now()+1000;
    for(unsigned n=0;n<100;n++){r=device(&q);if(r!=-11)break;CHECK(!S1(SLEEP_MS,10),47);}
    CHECK(r==64,48);
    for(unsigned n=0;n<6;n++)CHECK(buffer[n]==src[n] && buffer[n+6]==dest[n],49);
    for(unsigned n=14;n<64;n++)CHECK(buffer[n]==n,50);
    network_witness[5]=64;CHECK(message(ep,1,42)==42,51);
    if(mode==1)__builtin_trap();
    if(mode==2 || mode==4)for(unsigned n=0;n<200;n++)CHECK(!S1(SLEEP_MS,10),52);
    if(mode==3)for(;;)__asm__ volatile("pause");
    if(mode==6) {
        q.operation=9;q.address=0;q.length=0;q.deadline_ms=now()+1000;
        for(unsigned n=0;n<256;n++){r=device(&q);if(r==-122)break;CHECK(r>=0,53);}
        CHECK(r==-122,54);
    }
    q=(reist_network_request_v1){1,64,8,0,owner,(uint64_t)epoch,0,0,0,0,0};CHECK(!device(&q),55);
    network_witness[8]=1;return 82;
}
#else
int main(int argc,char **argv){(void)argc;(void)argv;return 77;}
#endif
