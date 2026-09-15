/* Finite Ring3 pool qualification fixture, not a service or public ABI.
 * The observer may change only root_witness.mode (initially zero) once per
 * admitted root. All kernel authority still comes from ordinary syscalls.
 */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define REQUIRE(x,e) do {if(!(x))return (e);}while(0)

#if PROGRAM_ID<3
static void message_init(volatile uint32_t *message,unsigned length) {
    for(unsigned i=0;i<35;i++)message[i]=0;
    message[0]=1;message[1]=140;message[2]=length;
}
#endif
#if PROGRAM_ID<2
/* First initialized data, kept by the existing memory-witness linker adapter.
 * Private 72-byte v1: magic, fixture selector, owner generation, phase,
 * three child handles, prepared-record VA, acquisition-failure count.
 */
static volatile struct {
    uint64_t magic,mode,owner,phase,children[3],record,oom;
} root_witness __attribute__((section(".data.memory_witness")))={
    0x31544f4f524c4f50ULL,0,0,0,{0,0,0},0,0};

static int64_t control(unsigned op,uint64_t handle,unsigned timeout) {
    reist_task_control_request_t q={1,64,op,0,handle,0,timeout,0,0,0};
    return reist_x64_task_control(&q);
}
static void hex32(char *text,uint32_t value) {
    for(unsigned i=0;i<8;i++)text[i]="0123456789abcdef"[(value>>(28-4*i))&15];
    text[8]=0;
}
static int64_t create(void *record,unsigned index,uint32_t endpoint,unsigned mode) {
    char port[9],owner[9],id[2]={(char)('0'+index),0};
    char fault[2]={(char)('0'+mode),0},role[2]={(char)('0'+PROGRAM_ID),0};
    hex32(port,endpoint);hex32(owner,(uint32_t)root_witness.owner);
    const char *arguments[]={"pool-child",port,owner,id,fault,role};
    reist_task_startup_v1_t startup;
    reist_task_profile_v1_t profile={1,40,{MASK,0,0},0};
    if(reist_x64_startup_init(&startup,6,arguments)!=0 ||
       reist_x64_image_prepare_v2(record,import_blob,sizeof(import_blob))!=0)return -22;
    int64_t child=reist_x64_task_import_wide(record,&profile,32,&startup);
    /* Neither the admitted immutable image nor any private page may alias this. */
    for(unsigned i=0;i<REIST_X64_PREPARED_V2_BYTES;i++)((volatile unsigned char*)record)[i]=0xa5;
    return child;
}
static int release(uint32_t endpoint,unsigned index) {
    volatile uint32_t message[35];message_init(message,4);message[3]=0x504f4c00U+index;
    return (int)S3(IPC_SEND_TIMEOUT,endpoint,message,0);
}
#elif PROGRAM_ID==2
/* Identical initial bytes must become six independently owned copies. */
static volatile struct {
    uint64_t magic,owner,parent,index,role,phase,heap,checksum;
} child_witness __attribute__((section(".data.memory_witness")))={
    0x31444c48434c4f50ULL,0,0,0,0,0,0,0};
static volatile unsigned char private_bytes[4096];
static uint32_t parse_hex(const char *text) {
    uint32_t value=0;
    if(!text)return 0;
    for(unsigned i=0;i<8;i++) {
        unsigned c=(unsigned char)text[i];
        if(!((c>='0' && c<='9') || (c>='a' && c<='f')))return 0;
        value=(value<<4)|(c<='9'?c-'0':c-'a'+10);
    }
    return text[8]?0:value;
}
#endif

int main(int argc,char **argv) {
#if PROGRAM_ID<2
    (void)argc;(void)argv;
    unsigned mode=(unsigned)root_witness.mode;
    REQUIRE(root_witness.mode<=9,201);
    root_witness.owner=(uint64_t)S0(GETPID);root_witness.phase=1;
    REQUIRE(root_witness.owner && root_witness.owner<=UINT32_MAX,202);
    void *record=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    REQUIRE((int64_t)(uintptr_t)record>0,203);root_witness.record=(uintptr_t)record;
    uint32_t ports[3]={0,0,0};
    for(unsigned i=0;i<3;i++) {
        REQUIRE(S1(IPC_CREATE,&ports[i])==0 && ports[i],204);
        unsigned fault=PROGRAM_ID==0 && !i && (mode==2 || mode==3)?mode:0;
        int64_t child=create(record,i,ports[i],fault);
        if(PROGRAM_ID==0 && !i && mode>=7) {
            REQUIRE(child==-12,205);root_witness.oom=1;
            child=create(record,i,ports[i],fault);
        }
        REQUIRE(child>0,206);root_witness.children[i]=(uint64_t)child;
        REQUIRE(S3(IPC_DELEGATE,ports[i],(uint64_t)child>>32,2)==0,207);
    }
    root_witness.phase=2;
    /* One finite blocking barrier. All six children wait for explicit grants
     * and release messages; the real observer must witness eight live tasks.
     * The retained-receipt case keeps the unrelated peer's slots occupied. */
    for(unsigned i=0;i<(PROGRAM_ID==1 && mode==6?5U:2U);i++)
        REQUIRE(S1(SLEEP_MS,100)==0,208);
    if(PROGRAM_ID==0 && mode==5)__asm__ volatile("ud2");
    if(PROGRAM_ID==0 && mode==6) {
        REQUIRE(create(record,0,ports[0],0)==-11,209);root_witness.phase=3;
        REQUIRE(release(ports[0],0)==0 && S1(SLEEP_MS,50)==0,210);
        /* The uncollected terminal receipt still occupies its slot. */
        REQUIRE(create(record,0,ports[0],0)==-11,211);root_witness.phase=4;
        uint64_t previous=root_witness.children[0];
        REQUIRE(control(2,previous,1000)==80,212);
        REQUIRE(S1(IPC_CLOSE,ports[0])==0 && S1(IPC_CREATE,&ports[0])==0,213);
        int64_t replacement=create(record,0,ports[0],0);
        REQUIRE(replacement>0 && (uint32_t)replacement==(uint32_t)previous &&
                ((uint64_t)replacement>>32)>(previous>>32),214);
        root_witness.children[0]=(uint64_t)replacement;
        REQUIRE(control(2,previous,1)==-10,215);
        REQUIRE(S3(IPC_DELEGATE,ports[0],(uint64_t)replacement>>32,2)==0,216);
    }
    if(PROGRAM_ID==0 && mode==4)
        REQUIRE(control(3,root_witness.children[0],0)==0,217);
    root_witness.phase=5;
    for(unsigned i=0;i<3;i++) {
        if(!(PROGRAM_ID==0 && mode==4 && !i))REQUIRE(release(ports[i],i)==0,218);
        int64_t expected=80+i+3*PROGRAM_ID;
        if(PROGRAM_ID==0 && !i) {
            if(mode==2)expected=(1LL<<32)|134;
            if(mode==3)expected=(1LL<<32)|256;
            if(mode==4)expected=2LL<<32;
        }
        REQUIRE(control(2,root_witness.children[i],1000)==expected,219);
        REQUIRE(S1(IPC_CLOSE,ports[i])==0,220);
    }
    REQUIRE(S1(FREE,record)==0,221);root_witness.phase=6;
    return 90+PROGRAM_ID;
#elif PROGRAM_ID==2
    REQUIRE(argc==6 && argv && argv[3] && argv[4] && argv[5],230);
    uint32_t port=parse_hex(argv[1]),parent=parse_hex(argv[2]);
    unsigned index=(unsigned char)argv[3][0]-'0';
    unsigned mode=(unsigned char)argv[4][0]-'0',role=(unsigned char)argv[5][0]-'0';
    REQUIRE(port && parent && index<3 && mode<=3 && mode!=1 && role<2 &&
            !argv[3][1] && !argv[4][1] && !argv[5][1],231);
    uint64_t pid=(uint64_t)S0(GETPID);
    REQUIRE(pid && pid<=UINT32_MAX && pid!=parent,232);
    REQUIRE(!child_witness.owner && !child_witness.parent && !child_witness.phase,233);
    child_witness.owner=pid;child_witness.parent=parent;
    child_witness.index=index;child_witness.role=role;
    volatile unsigned char *heap=(void*)(uintptr_t)S1(MALLOC,8192);
    REQUIRE((int64_t)(uintptr_t)heap>0,234);child_witness.heap=(uintptr_t)heap;
    uint64_t checksum=0;
    for(unsigned i=0;i<4096;i++) {
        REQUIRE(private_bytes[i]==0,235);
        private_bytes[i]=(unsigned char)(i^pid);
        heap[i]=(unsigned char)(i+pid);heap[i+4096]=(unsigned char)(i^parent);
        checksum+=private_bytes[i]+heap[i]+heap[i+4096];
    }
    child_witness.checksum=checksum;child_witness.phase=1;
    unsigned ready=0;
    for(unsigned attempt=0;attempt<20;attempt++) {
        volatile uint32_t message[35];message_init(message,0);
        int64_t result=S3(IPC_RECEIVE_TIMEOUT,port,message,1000);
        if(result==0){REQUIRE(message[2]==4 && message[3]==0x504f4c00U+index,236);ready=1;break;}
        REQUIRE(result==-9 || result==-13,237);
        REQUIRE(S1(SLEEP_MS,10)==0,238);
    }
    REQUIRE(ready,239);child_witness.phase=2;
    if(mode==2)__asm__ volatile("ud2");
    if(mode==3)for(;;)__asm__ volatile("pause"); /* deliberate CPU32 fault */
    for(unsigned i=0;i<4096;i++)
        REQUIRE(private_bytes[i]==(unsigned char)(i^pid) && heap[i]==(unsigned char)(i+pid) &&
                heap[i+4096]==(unsigned char)(i^parent),240);
    REQUIRE(S1(FREE,heap)==0,241);child_witness.phase=3;
    return 80+index+3*role;
#else
    (void)argc;(void)argv;return 97;
#endif
}
