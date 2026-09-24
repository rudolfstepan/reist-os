/* One bounded device owner within the existing eight-task family. Ring0 has
 * no ATA protocol or restart policy; all operations use the existing service. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#include "../../../userspace/drivers/ata/native_service.h"
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define REQUIRE(x,e) do{if(!(x))return(e);}while(0)
#if PROGRAM_ID==0 || PROGRAM_ID==2
#if defined(REIST_NATIVE_PIO_THROUGHPUT) && PROGRAM_ID==0
static unsigned pio_throughput_selected;
#endif
static uint32_t request_ep,reply_ep,notice_ep;
static x86os_ipc_message_t message,request;
static void zero(void *p,unsigned n){unsigned char *b=p;for(unsigned i=0;i<n;i++)b[i]=0;}
static void copy(void *p,const void *s,unsigned n){unsigned char *a=p;const unsigned char *b=s;for(unsigned i=0;i<n;i++)a[i]=b[i];}
static uint64_t clock_ms(void *v){(void)v;return (uint64_t)S0(MONOTONIC_MS);}
static int64_t pio(uint64_t owner,unsigned op){
    reist_native_pio_request q={1,64,op,0,owner,op==REIST_PIO_READ8?0x1f7:0,0,0,0,0,0,0};
#if defined(REIST_NATIVE_PIO_THROUGHPUT) && PROGRAM_ID==0
    if(op==REIST_PIO_BIND && pio_throughput_selected) {
        int result=reist_x64_pio_throughput_bind_prepare(&q,owner);
        if(result)return result;
    }
#endif
    return reist_x64_pio(&q);
}
#endif
#if PROGRAM_ID==0
/* v1: magic/mode/gen/phase/driver/sequence/lba/result/output/filler_count,
 * five filler handles, mutable import source, immutable prepared template.
 * Only mode is debugger-writable, after original-zero/image validation. */
static volatile uint64_t pool_pio_root[17] __attribute__((used))={0x31544f4f52504950ULL};
static unsigned char output[512];
static void number(char *s,uint32_t n){for(unsigned i=0;i<8;i++)s[i]="0123456789abcdef"[(n>>(28-i*4))&15];s[8]=0;}
static int64_t control(unsigned op,uint64_t target,unsigned timeout){
    reist_task_control_request_t q={1,64,op,0,target,0,timeout,0,0,0};return reist_x64_task_control(&q);
}
static int sending(void *v,const x86os_ipc_message_t *q,unsigned ms){(void)v;return (int)S3(IPC_SEND_TIMEOUT,request_ep,q,ms);}
static int receiving(void *v,x86os_ipc_bulk_message_t *r,unsigned ms){(void)v;return (int)S3(IPC_RECEIVE_TIMEOUT,reply_ep,r,ms);}
static int notice(uint64_t owner,unsigned mode,unsigned phase,unsigned value){
    zero(&message,sizeof message);message.version=1;message.struct_size=140;message.length=128;
    if(S3(IPC_RECEIVE_TIMEOUT,notice_ep,&message,1000))return -1;
    uint32_t words[4];copy(words,message.payload,16);
    return message.length!=16||words[0]!=(uint32_t)(owner>>32)||words[1]!=mode||words[2]!=phase||words[3]!=value?-1:0;
}
static int64_t create(void *record,const void *template,unsigned slot,unsigned kind){
    char rq[9],rp[9],np[9],role[9],position[9];
    number(rq,request_ep);number(rp,reply_ep);number(np,notice_ep);number(role,kind);number(position,slot);
    const char *args[5]={rq,rp,np,role,position};reist_task_startup_v1_t startup;
    if(reist_x64_startup_init(&startup,5,args))return -22;
    typedef uint64_t word __attribute__((may_alias,aligned(1)));
    for(unsigned n=0;n<REIST_X64_PREPARED_V2_BYTES/8;n++)((word*)record)[n]=((const word*)template)[n];
    reist_task_profile_v1_t profile={1,40,{MASK,kind==256?0:1ULL<<49,0},0};
#if REIST_NATIVE_SERVICE_PIO
    int64_t child=reist_x64_task_import_periodic(record,&profile,32,1000,&startup);
#else
    int64_t child=reist_x64_task_import_wide(record,&profile,32,&startup);
#endif
    for(unsigned n=0;n<REIST_X64_PREPARED_V2_BYTES/8;n++)((volatile word*)record)[n]=0xa5a5a5a5a5a5a5a5ULL;
    (void)S0(GETPID); /* Observe completed source overwrite before another CREATE. */
    return child;
}
#elif PROGRAM_ID==1
static volatile uint64_t pool_pio_peer[3] __attribute__((used))={0x3152454550504950ULL};
#elif PROGRAM_ID==2
static reist_native_profile_service service;
static x86os_ipc_bulk_message_t reply;
/* v1: magic/handle/kind/phase/service/heap; own immutable startup binds slot. */
static volatile uint64_t pool_pio_child[6] __attribute__((used))={0x31444c4948504950ULL};
typedef struct {uint64_t owner;unsigned mode,reads,chunks;} Driver;
static uint32_t number(const char *s){
    uint32_t n=0;for(unsigned i=0;i<8;i++){unsigned c=(unsigned char)s[i];
        if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return UINT32_MAX;n=(n<<4)|c;}
    return s[8]?UINT32_MAX:n;
}
static int notice(unsigned mode,unsigned phase,unsigned value){
    zero(&message,sizeof message);message.version=1;message.struct_size=140;message.length=16;
    uint32_t words[4]={(uint32_t)S0(GETPID),mode,phase,value};copy(message.payload,words,16);
    return (int)S3(IPC_SEND_TIMEOUT,notice_ep,&message,1000);
}
static int sleep_ms(void *v,unsigned ms){(void)v;return (int)S1(SLEEP_MS,ms);}
#if REIST_NATIVE_SERVICE_PIO
#include "service_pio_workload.h"
#endif
static int64_t port(void *v,reist_native_pio_request *q){
    Driver *d=v;int64_t result=reist_x64_pio(q);
    if(!result&&q->operation==REIST_PIO_WRITE8&&q->port==0x1f7&&q->value==0x20){d->reads++;d->chunks=0;}
    if(!result&&d->reads==2&&q->operation==REIST_PIO_READ16&&++d->chunks==8&&d->mode>=7&&d->mode<=9){
        pool_pio_child[3]=3;if(notice(d->mode,1,256))return -5;
        if(d->mode==7)__asm__ volatile("ud2");
        if(d->mode==9)for(;;)__asm__ volatile("pause");
        for(unsigned n=0;n<20;n++)if(S1(SLEEP_MS,100))return -5;
        return -110;
    }
    return result;
}
#endif

int main(int argc,char **argv,char **envp){
    REQUIRE(argc>=0&&argc<=8&&!argv[argc]&&!envp[0],200);
#if PROGRAM_ID==0
    REQUIRE(argc==2&&argv[1][0]=='0'&&pool_pio_root[1]<=15,201);
    unsigned mode=(unsigned)pool_pio_root[1],fillers=mode<=5?mode:5,slot=fillers+2;
#ifdef REIST_NATIVE_PIO_THROUGHPUT
    pio_throughput_selected=mode!=0; /* Same image retains one old-profile case. */
#endif
    pool_pio_root[2]=(uint64_t)S0(GETPID);pool_pio_root[3]=1;pool_pio_root[9]=fillers;
    void *template=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    void *record=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    REQUIRE((intptr_t)template>0&&(intptr_t)record>0,202);
    pool_pio_root[15]=(uintptr_t)record;pool_pio_root[16]=(uintptr_t)template;
    REQUIRE(!reist_x64_image_prepare_v2(template,import_blob,sizeof import_blob),203);
    REQUIRE(!S1(IPC_CREATE,&request_ep)&&!S1(IPC_CREATE,&reply_ep)&&!S1(IPC_CREATE,&notice_ep),204);
    for(unsigned i=0;i<fillers;i++){
        int64_t child=create(record,template,i+2,256);
        REQUIRE(child>0&&(uint32_t)child==i+2,205);pool_pio_root[10+i]=(uint64_t)child;
    }
    uint64_t previous=0;reist_block_client client={0};reist_block_transport transport={0,clock_ms,sending,receiving};
    for(unsigned round=0;round<2;round++){
        unsigned fault=round?0:mode==11?8:mode>=7&&mode<=10?mode:0;
        pool_pio_root[3]=2;
        int64_t child=create(record,template,slot,fault);
        if(!round&&mode>=13){REQUIRE(child==-12,206);child=create(record,template,slot,fault);}
        REQUIRE(child>0&&(uint32_t)child==slot&&(uint64_t)child>previous,207);
        pool_pio_root[4]=(uint64_t)child;
        REQUIRE(!S3(IPC_DELEGATE,request_ep,(uint64_t)child>>32,2)&&
                !S3(IPC_DELEGATE,reply_ep,(uint64_t)child>>32,1)&&
                !S3(IPC_DELEGATE,notice_ep,(uint64_t)child>>32,1),208);
        REQUIRE(!pio(child,REIST_PIO_BIND),209);
        if(previous)REQUIRE(pio(previous,REIST_PIO_FENCE)==-13&&control(2,previous,1)==-10,210);
#if REIST_NATIVE_SERVICE_PIO
        for(unsigned batch=5;batch<=40;batch+=5)REQUIRE(!notice(child,fault,2,batch),242);
        for(unsigned idle=6;idle<=12;idle+=6)REQUIRE(!notice(child,fault,3,idle),244);
#endif
        REQUIRE(!notice(child,fault,0,mode==12?19:128),211);
        if(mode!=12){
#if REIST_NATIVE_SERVICE_PIO
            zero(&message,sizeof message);message.version=1;message.struct_size=140;message.length=128;
            REQUIRE(S3(IPC_RECEIVE_TIMEOUT,notice_ep,&message,800)==-110,245);
#endif
            REQUIRE(!reist_block_client_bind(&client,child),212);
            pool_pio_root[3]=3;
            if(mode==11){
                reist_block_header h={1,64,1,0,child,1,1,clock_ms(0)+1000,512,0,0};
                zero(&request,sizeof request);request.version=1;request.struct_size=140;request.length=64;copy(request.payload,&h,64);
                REQUIRE(!sending(0,&request,1000)&&!notice(child,fault,1,256),213);__asm__ volatile("ud2");
            }
            for(unsigned i=0;i<512;i++)output[i]=0xcc;
            int result=reist_block_read(&client,&transport,1,output,1000);
            pool_pio_root[5]=client.sequence;pool_pio_root[6]=1;pool_pio_root[7]=(uint64_t)(int64_t)result;
            pool_pio_root[8]=(uintptr_t)output;pool_pio_root[3]=4;(void)S0(GETPID);
            REQUIRE(fault==10?result==-71:fault?(result==-32||result==-110):result==0,214);
            for(unsigned i=0;i<512;i++)REQUIRE(output[i]==(result?0xcc:(unsigned char)(i^17^0xa5)),215);
            if(fault&&fault!=10)REQUIRE(!notice(child,fault,1,256),216);
            if(fault==8||fault==10){REQUIRE(!pio(child,REIST_PIO_FENCE)&&!control(3,child,0),217);}
        }
        int64_t expected=mode==12?89:fault==7?((1LL<<32)|134):fault==9?((1LL<<32)|256):fault==8||fault==10?(2LL<<32):80;
        REQUIRE(control(2,child,1000)==expected,218);
        REQUIRE(!pio(child,REIST_PIO_FENCE)&&control(2,child,1)==-10,219);previous=(uint64_t)child;
    }
    for(unsigned i=0;i<fillers;i++){
        REQUIRE(!control(3,pool_pio_root[10+i],0),220);
        REQUIRE(control(2,pool_pio_root[10+i],1000)==(2LL<<32),221);
    }
    REQUIRE(!S1(IPC_CLOSE,request_ep)&&!S1(IPC_CLOSE,reply_ep)&&!S1(IPC_CLOSE,notice_ep),222);
    REQUIRE(!S1(FREE,record)&&!S1(FREE,template),223);pool_pio_root[3]=5;
    return mode==12?79:78;
#elif PROGRAM_ID==1
    REQUIRE(argc==2&&argv[1][0]=='1',224);
    pool_pio_peer[1]=(uint64_t)S0(GETPID);
    REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,225);
#if REIST_NATIVE_SERVICE_PIO
    for(unsigned i=0;i<60;i++){REQUIRE(!S1(SLEEP_MS,100),226);pool_pio_peer[2]=i+1;}
#else
    for(unsigned i=0;i<25;i++){REQUIRE(!S1(SLEEP_MS,100),226);pool_pio_peer[2]=i+1;}
#endif
    (void)S0(GETPID);return 77;
#elif PROGRAM_ID==2
    REQUIRE(argc==5,227);
    request_ep=number(argv[0]);reply_ep=number(argv[1]);notice_ep=number(argv[2]);
    unsigned kind=number(argv[3]),slot=number(argv[4]);uint64_t owner=((uint64_t)S0(GETPID)<<32)|slot;
    REQUIRE(slot>=2&&slot<8&&(kind==256||kind==0||(kind>=7&&kind<=10)),228);
    pool_pio_child[1]=owner;pool_pio_child[2]=kind;pool_pio_child[3]=1;
    void *heap=(void*)(uintptr_t)S1(MALLOC,8192);REQUIRE((intptr_t)heap>0,229);
    pool_pio_child[5]=(uintptr_t)heap;for(unsigned n=0;n<8192;n++)((unsigned char*)heap)[n]=(unsigned char)(n^slot^0x5a);
    if(kind==256){
        REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,230);(void)S0(GETPID);
#if REIST_NATIVE_SERVICE_PIO
        for(unsigned i=0;i<160;i++)REQUIRE(!S1(SLEEP_MS,100),231);
#else
        for(unsigned i=0;i<25;i++)REQUIRE(!S1(SLEEP_MS,100),231);
#endif
        return 75; /* Healthy supervisor must cancel before this finite limit. */
    }
    REQUIRE(request_ep&&reply_ep&&notice_ep,232);
    Driver d={owner,kind,0,0};int64_t ready=-13;
    for(unsigned n=0;n<20&&ready==-13;n++){REQUIRE(!S1(SLEEP_MS,10),233);ready=pio(owner,REIST_PIO_READ8);}
    REQUIRE(ready>=0,234);
#if REIST_NATIVE_SERVICE_PIO
    REQUIRE(!service_pio_prepare(kind)&&!service_pio_idle(kind),243);
#endif
    reist_pio_ops ops={&d,port,clock_ms,sleep_ms};reist_block_profile_v1 profile={1,24,1,0,clock_ms(0)+2500};
    pool_pio_child[4]=(uintptr_t)&service;
    int result=reist_native_service_init_profile(&service,owner,&ops,&profile);
    if(result==-19){REQUIRE(!notice(kind,0,19),235);return 89;}
    REQUIRE(!result&&service.service.server.capacity==128,236);
    pool_pio_child[3]=2;REQUIRE(!notice(kind,0,128),237);
    zero(&request,sizeof request);request.version=1;request.struct_size=140;request.length=128;
    REQUIRE(!S3(IPC_RECEIVE_TIMEOUT,request_ep,&request,1000),238);
    result=reist_native_service_dispatch_profile(&service,&request,&reply);
    if(kind==10&&!result)reply.payload[24]^=1;
    reist_block_header h;copy(&h,reply.payload,64);uint64_t now=clock_ms(0);
    unsigned timeout=h.deadline_ms>now&&h.deadline_ms-now<=1000?(unsigned)(h.deadline_ms-now):1;
    REQUIRE(!S3(IPC_SEND_TIMEOUT,reply_ep,&reply,timeout),239);
    if(kind==10)for(unsigned n=0;n<20;n++)REQUIRE(!S1(SLEEP_MS,100),240);
    pool_pio_child[3]=4;return 80;
#else
    return 241;
#endif
}
