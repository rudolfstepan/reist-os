/* Native block-service reference processes. Faults remain Ring3-only. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#include <reist/x86_64/block.h>
#include "../../../userspace/drivers/ata/native_service.h"
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define REQUIRE(x,e) do {if(!(x))return (e);}while(0)
#if PROGRAM_ID==0 || PROGRAM_ID==2
static x86os_ipc_message_t notice_message;
#if PROGRAM_ID==2 || PIO_CASE!=2
static x86os_ipc_message_t request;
static x86os_ipc_bulk_message_t reply;
#if PROGRAM_ID==0
static unsigned char output[512];
#endif
#endif
static uint32_t request_ep,reply_ep,notice_ep;
static void zero(void *p,unsigned n){unsigned char *b=p;for(unsigned i=0;i<n;i++)b[i]=0;}
static void copy(void *p,const void *q,unsigned n){unsigned char *a=p;const unsigned char *b=q;for(unsigned i=0;i<n;i++)a[i]=b[i];}
#if PROGRAM_ID==2 || PIO_CASE!=2
static uint64_t clock_ms(void *v){(void)v;return (uint64_t)S0(MONOTONIC_MS);}
#endif
static int64_t pio(uint64_t owner,unsigned operation,unsigned port,unsigned value){
    reist_native_pio_request q={1,64,operation,0,owner,port,value,0,0,0,0,0};return reist_x64_pio(&q);
}
#if PROGRAM_ID==2
static int notice(unsigned mode,unsigned phase,unsigned value){
    zero(&notice_message,sizeof(notice_message));notice_message.version=1;
    notice_message.struct_size=140;notice_message.length=16;
    uint32_t words[4]={(uint32_t)S0(GETPID),mode,phase,value};copy(notice_message.payload,words,16);
    return (int)S3(IPC_SEND_TIMEOUT,notice_ep,&notice_message,1000);
}
#endif
#endif
#if PROGRAM_ID==0
static volatile uint64_t block_result_record[5] __attribute__((used));
#if PIO_CASE!=2
static void block_result_witness(uint64_t owner,uint64_t sequence,uint64_t lba,int result,const unsigned char *data){
    block_result_record[0]=owner;block_result_record[1]=sequence;block_result_record[2]=lba;
    block_result_record[3]=(uint64_t)(int64_t)result;block_result_record[4]=(uintptr_t)data;
    (void)S0(GETPID); /* Observe at a kernel boundary, never a shared user VA breakpoint. */
}
#endif
static void number(char *out,uint32_t n){for(unsigned i=0;i<8;i++)out[i]="0123456789abcdef"[(n>>(28-4*i))&15];out[8]=0;}
static void image_words(void *out,const void *source){
    typedef uint64_t word __attribute__((may_alias,aligned(1)));
    volatile word *p=out;const word *q=source;
    for(unsigned n=0;n<36896/8;n++)p[n]=q?q[n]:0x5a5a5a5a5a5a5a5aULL;
}
static int64_t create(void *record,reist_task_startup_v1_t *s){
    static void *prepared;
    static unsigned mutation_witness;
    if(!prepared){
        int64_t p=S1(MALLOC,36896);if(p<=0)return -12;
        if(reist_x64_image_prepare((void*)(uintptr_t)p,import_blob,sizeof(import_blob))){
            if(S1(FREE,p))return -5;
            return -22;
        }
        prepared=(void*)(uintptr_t)p;
    }
    if(!mutation_witness)image_words(record,prepared);
    reist_task_profile_v1_t profile={1,40,{MASK,1ULL<<49,0},0};
    int64_t result=reist_x64_task_import_profile(mutation_witness?prepared:record,&profile,32,s);
    if(!mutation_witness && result>0){image_words(record,0);mutation_witness=1;}
    return result;
}
static int64_t control(unsigned op,uint64_t owner,unsigned timeout){
    reist_task_control_request_t q={1,64,op,0,owner,0,timeout,0,0,0};return reist_x64_task_control(&q);
}
#if PIO_CASE!=2
static int sending(void *v,const x86os_ipc_message_t *q,unsigned ms){(void)v;return (int)S3(IPC_SEND_TIMEOUT,request_ep,q,ms);}
static int receiving(void *v,x86os_ipc_bulk_message_t *r,unsigned ms){(void)v;return (int)S3(IPC_RECEIVE_TIMEOUT,reply_ep,r,ms);}
#endif
static int wait_notice(uint64_t child,unsigned mode,unsigned phase,unsigned value){
    zero(&notice_message,sizeof(notice_message));notice_message.version=1;
    notice_message.struct_size=140;notice_message.length=128;
    if(S3(IPC_RECEIVE_TIMEOUT,notice_ep,&notice_message,1000))return -1;
    uint32_t words[4];copy(words,notice_message.payload,16);
    return notice_message.length!=16 || words[0]!=(uint32_t)(child>>32) || words[1]!=mode || words[2]!=phase || words[3]!=value?-1:0;
}
#if PIO_CASE!=2
static int invalid_requests(uint64_t child){
    for(unsigned kind=0;kind<4;kind++){
        reist_block_header h={1,64,1,0,child,1,0,clock_ms(0)+1000,512,0,0};
        int expected=kind==1?-13:kind==3?-110:-22;
        if(kind==0)h.operation=2;
        if(kind==1)h.owner-=1ULL<<32;
        if(kind==2)h.lba=128;
        if(kind==3)h.deadline_ms=clock_ms(0);
        zero(&request,sizeof(request));request.version=1;request.struct_size=140;request.length=64;
        copy(request.payload,&h,64);
        if(sending(0,&request,1000))return -1;
        zero(&reply,sizeof(reply));reply.version=2;reply.struct_size=2060;reply.length=2048;
        if(receiving(0,&reply,1000))return -1;
        copy(&h,reply.payload,64);
        if(reply.length!=64 || h.status!=expected || h.owner!=child || h.sequence!=1)return -1;
        for(unsigned i=64;i<2048;i++)if(reply.payload[i])return -1;
    }
    return 0;
}
#endif
#elif PROGRAM_ID==2
static volatile uint32_t private_marker=0x12345678;
static volatile unsigned char private_zeroes[4096];
static reist_native_service service;
typedef struct {uint64_t owner;unsigned mode,reads,chunks,probes;} Driver;
static uint32_t number(const char *p){
    uint32_t v=0;for(unsigned i=0;i<8;i++){unsigned c=(unsigned char)p[i];
        if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return 0;v=(v<<4)|c;
    }return p[8]?0:v;
}
static int sleep_ms(void *v,unsigned ms){(void)v;return (int)S1(SLEEP_MS,ms);}
static int64_t port(void *v,reist_native_pio_request *q){
    Driver *d=v;int64_t result=reist_x64_pio(q);
    if(!result && q->operation==REIST_PIO_WRITE8 && q->port==0x1f7 && q->value==0x20){d->reads++;d->chunks=0;}
    if(!result && d->reads==2 && q->operation==REIST_PIO_READ16 && ++d->chunks==8 &&
       (d->mode==1 || d->mode==2 || d->mode==4)){
        if(notice(d->mode,1,256))return -5;
        if(d->mode==1)__asm__ volatile("ud2");
        if(d->mode==4)for(;;)__asm__ volatile("pause");
        for(unsigned i=0;i<20;i++)if(S1(SLEEP_MS,100))return -5;
        return -110;
    }
    return result;
}
#endif
int main(int argc,char **argv,char **envp){
    REQUIRE(argc>=0 && argc<=8 && !argv[argc] && !envp[0],200);
#if PROGRAM_ID==0
    REQUIRE(argc==2 && argv[1][0]=='0',201);
    void *record=(void*)(uintptr_t)S1(MALLOC,36896);
    reist_task_startup_v1_t *s=(void*)(uintptr_t)S1(MALLOC,1040);
    REQUIRE((intptr_t)record>0 && (intptr_t)s>0,202);
    REQUIRE(!reist_x64_startup_init(s,0,0),203);
#if PIO_CASE==1
    REQUIRE(create(record,s)==-12,204);
#endif
    REQUIRE(!S1(IPC_CREATE,&request_ep) && !S1(IPC_CREATE,&reply_ep) && !S1(IPC_CREATE,&notice_ep),205);
    char rq[9],rp[9],np[9];number(rq,request_ep);number(rp,reply_ep);number(np,notice_ep);
    const unsigned modes[8]={0,1,0,2,0,3,4,0};uint64_t previous=0;
#if PIO_CASE!=2
    reist_block_client client={0};reist_block_transport transport={0,clock_ms,sending,receiving};
#endif
    for(unsigned i=PIO_CASE==1?1:0;i<(PIO_CASE>=2?1U:8U);i++){
        unsigned mode=PIO_CASE==3?2:modes[i];unsigned probes=i==(PIO_CASE==1?1U:0U);
        char kind[9];number(kind,mode|(probes?16:0));
        const char *args[4]={rq,rp,np,kind};REQUIRE(!reist_x64_startup_init(s,4,args),206);
        int64_t child=create(record,s);REQUIRE(child>0 && (uint32_t)child==2,207);
        REQUIRE(!S3(IPC_DELEGATE,request_ep,(uint64_t)child>>32,2),208);
        REQUIRE(!S3(IPC_DELEGATE,reply_ep,(uint64_t)child>>32,1),209);
        REQUIRE(!S3(IPC_DELEGATE,notice_ep,(uint64_t)child>>32,1),210);
        REQUIRE(!pio(child,REIST_PIO_BIND,0,0),211);
        if(previous)REQUIRE(pio(previous,REIST_PIO_FENCE,0,0)==-13,212);
        REQUIRE(!wait_notice(child,mode,2,110),244);
        REQUIRE(!wait_notice(child,mode,0,PIO_CASE==2?19:128),213);
#if PIO_CASE==2
        REQUIRE(control(2,child,1000)==89,214);
#else
        if(probes)REQUIRE(!invalid_requests(child),215);
        REQUIRE(!reist_block_client_bind(&client,child),216);
#if PIO_CASE==3
        reist_block_header h={1,64,1,0,child,1,1,clock_ms(0)+1000,512,0,0};
        zero(&request,sizeof(request));request.version=1;request.struct_size=140;request.length=64;
        copy(request.payload,&h,64);REQUIRE(!sending(0,&request,1000),217);
        REQUIRE(!wait_notice(child,mode,1,256),218);__asm__ volatile("ud2");
#endif
        for(unsigned n=0;n<(mode?1U:2U);n++){
            for(unsigned b=0;b<512;b++)output[b]=0xcc;
            unsigned lba=n&1?127:1;
            int result=reist_block_read(&client,&transport,lba,output,1000);
            block_result_witness(child,client.sequence,lba,result,output);
            if(mode){
                REQUIRE(mode==3?result==-71:(result==-32 || result==-110),219);
                for(unsigned b=0;b<512;b++)REQUIRE(output[b]==0xcc,220);
                if(mode!=3)REQUIRE(!wait_notice(child,mode,1,256),221);
                if(mode==2 || mode==3){REQUIRE(!pio(child,REIST_PIO_FENCE,0,0),222);REQUIRE(!control(3,child,0),223);}
            }else{
                REQUIRE(!result,224);
                for(unsigned b=0;b<512;b++)REQUIRE(output[b]==(unsigned char)(b^(lba*17)^0xa5),225);
            }
        }
        int64_t expected=mode==1?((1LL<<32)|134):mode==2||mode==3?(2LL<<32):mode==4?((1LL<<32)|256):80;
        REQUIRE(control(2,child,1000)==expected,226);
#endif
        REQUIRE(!pio(child,REIST_PIO_FENCE,0,0),227);
        REQUIRE(control(2,child,1)==-10,228);previous=child;
    }
#if PIO_CASE==2
    REQUIRE(!S1(IPC_CLOSE,request_ep) && !S1(IPC_CLOSE,reply_ep) && !S1(IPC_CLOSE,notice_ep),229);
#endif
#if PIO_CASE<2
    /* The existing owner-reap path must revoke these three live endpoints
     * before our frames are freed; the exhaustion observer witnesses them. */
    REQUIRE(create(record,s)==-11,230);
#endif
    return PIO_CASE==2?79:78;
#elif PROGRAM_ID==1
    REQUIRE(argc==2 && argv[1][0]=='1',231);
    REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,232);
    for(unsigned i=0;i<18;i++)REQUIRE(!S1(SLEEP_MS,100),233);
    return 77;
#elif PROGRAM_ID==2
    REQUIRE(argc==4 && private_marker==0x12345678,234);
    for(unsigned i=0;i<4096;i++)REQUIRE(!private_zeroes[i],235);
    private_marker=(uint32_t)S0(GETPID);private_zeroes[0]=1;private_zeroes[4095]=2;
    request_ep=number(argv[0]);reply_ep=number(argv[1]);notice_ep=number(argv[2]);
    unsigned options=number(argv[3]);
    Driver d={((uint64_t)private_marker<<32)|2,options&15,0,0,!!(options&16)};
    REQUIRE(request_ep && reply_ep && notice_ep && d.mode<=4,236);
    int64_t ready=-13;
    for(unsigned n=0;n<20 && ready==-13;n++){REQUIRE(!S1(SLEEP_MS,10),237);ready=pio(d.owner,REIST_PIO_READ8,0x1f7,0);}
    REQUIRE(ready>=0,238);
    reist_native_pio_request probe={1,64,REIST_PIO_READ8,0,d.owner,0x1f7,0,0,0,0,0,0},expired;
    REQUIRE(!reist_x64_pio_deadline_prepare(&expired,&probe,clock_ms(0)),245);
    REQUIRE(reist_x64_pio(&expired)==-110 && !notice(d.mode,2,110),246);
    reist_pio_ops ops={&d,port,clock_ms,sleep_ms};
    int result=reist_native_service_init(&service,d.owner,&ops);
    if(result==-19){REQUIRE(!notice(d.mode,0,19),239);return 89;}
    REQUIRE(!result && service.server.capacity==128 && !notice(d.mode,0,128),240);
    /* Six reference requests: four distinct invalid headers and both LBAs.
     * The reusable service's independent maximum remains eight. */
    while(service.server.requests<(d.mode?8U:d.probes?6U:2U)){
        zero(&request,sizeof(request));request.version=1;request.struct_size=140;request.length=128;
        REQUIRE(!S3(IPC_RECEIVE_TIMEOUT,request_ep,&request,1000),241);
        result=reist_native_service_dispatch(&service,&request,&reply);
        if(d.mode==3 && !result)reply.payload[24]^=1; /* Bad sequence, never trusted by client. */
        reist_block_header h;copy(&h,reply.payload,64);uint64_t now=clock_ms(0);
        /* Expired invalid requests still get a bounded error receipt. The
         * service may spend no device authority on them; client ignores late success. */
        unsigned timeout=h.deadline_ms>now && h.deadline_ms-now<=1000?(unsigned)(h.deadline_ms-now):1;
        REQUIRE(!S3(IPC_SEND_TIMEOUT,reply_ep,&reply,timeout),242);
    }
    return 80;
#else
    return 243;
#endif
}
