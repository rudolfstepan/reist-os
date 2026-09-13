/* Explicit bounded Ring3 block profile; no filesystem parser or shell command. */
#include <reist/x86_64/task.h>
#include <reist/x86_64/image.h>
#include "../../../userspace/drivers/ata/native_service.h"
#define MASK ((1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(0x7fULL<<49)|(1ULL<<58))
#define S0(n) reist_x64_syscall0(REIST_X64_SYS_##n)
#define S1(n,a) reist_x64_syscall1(REIST_X64_SYS_##n,(uintptr_t)(a))
#define S3(n,a,b,c) reist_x64_syscall3(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
#define REQUIRE(x,e) do {if(!(x))return (e);}while(0)
#if PROGRAM_ID==0 || PROGRAM_ID==2
static uint32_t request_ep,reply_ep,notice_ep;
static x86os_ipc_message_t notice_message;
#if PROGRAM_ID==2 || BLOCK_PROFILE_CASE==6
static x86os_ipc_message_t request;
#endif
#if PROGRAM_ID==2
static x86os_ipc_bulk_message_t reply;
#endif
static void zero(void *p,unsigned n){volatile unsigned char *b=p;for(unsigned i=0;i<n;i++)b[i]=0;}
static void copy(void *p,const void *s,unsigned n){unsigned char *a=p;const unsigned char *b=s;for(unsigned i=0;i<n;i++)a[i]=b[i];}
#if PROGRAM_ID==2 || BLOCK_PROFILE_CASE!=5
static uint64_t clock_ms(void *v){(void)v;return (uint64_t)S0(MONOTONIC_MS);}
#endif
static int64_t pio(uint64_t owner,unsigned operation){
    reist_native_pio_request q={1,64,operation,0,owner,operation==REIST_PIO_READ8?0x1f7:0,0,0,0,0,0,0};
    return reist_x64_pio(&q);
}
#endif
#if PROGRAM_ID==0
#if BLOCK_PROFILE_CASE!=5
static unsigned char output[512];
static volatile uint64_t block_profile_result_record[6] __attribute__((used));
static void witness(uint64_t owner,uint64_t sequence,uint64_t lba,int result){
    block_profile_result_record[0]=0x424c4b5052465631ULL;block_profile_result_record[1]=owner;
    block_profile_result_record[2]=sequence;block_profile_result_record[3]=lba;
    block_profile_result_record[4]=(uint64_t)(int64_t)result;block_profile_result_record[5]=(uintptr_t)output;
    (void)S0(GETPID);
}
#endif
static void number(char *out,uint32_t n){for(unsigned i=0;i<8;i++)out[i]="0123456789abcdef"[(n>>(28-i*4))&15];out[8]=0;}
static int64_t control(unsigned op,uint64_t owner,unsigned timeout){
    reist_task_control_request_t q={1,64,op,0,owner,0,timeout,0,0,0};return reist_x64_task_control(&q);
}
#if BLOCK_PROFILE_CASE!=5
static int sending(void *v,const x86os_ipc_message_t *q,unsigned ms){(void)v;return (int)S3(IPC_SEND_TIMEOUT,request_ep,q,ms);}
static int receiving(void *v,x86os_ipc_bulk_message_t *r,unsigned ms){(void)v;return (int)S3(IPC_RECEIVE_TIMEOUT,reply_ep,r,ms);}
#endif
static int notice(uint64_t owner,unsigned mode,unsigned phase,unsigned value){
    zero(&notice_message,sizeof(notice_message));notice_message.version=1;notice_message.struct_size=140;notice_message.length=128;
    if(S3(IPC_RECEIVE_TIMEOUT,notice_ep,&notice_message,1000))return -1;
    uint32_t words[4];copy(words,notice_message.payload,16);
    return notice_message.length!=16 || words[0]!=(uint32_t)(owner>>32) || words[1]!=mode || words[2]!=phase || words[3]!=value?-1:0;
}
#elif PROGRAM_ID==2
static reist_native_profile_service service;
typedef struct {uint64_t owner;unsigned mode,reads,chunks;} Driver;
static uint32_t number(const char *text){
    uint32_t n=0;for(unsigned i=0;i<8;i++){unsigned c=(unsigned char)text[i];
        if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return 0;n=(n<<4)|c;
    }return text[8]?0:n;
}
static int notice(unsigned mode,unsigned phase,unsigned value){
    zero(&notice_message,sizeof(notice_message));notice_message.version=1;notice_message.struct_size=140;notice_message.length=16;
    uint32_t words[4]={(uint32_t)S0(GETPID),mode,phase,value};copy(notice_message.payload,words,16);
    return (int)S3(IPC_SEND_TIMEOUT,notice_ep,&notice_message,1000);
}
static int sleep_ms(void *v,unsigned ms){(void)v;return (int)S1(SLEEP_MS,ms);}
static int64_t port(void *v,reist_native_pio_request *q){
    Driver *d=v;int64_t result=reist_x64_pio(q);
    if(!result && q->operation==REIST_PIO_WRITE8 && q->port==0x1f7 && q->value==0x20){++d->reads;d->chunks=0;}
    if(!result && d->reads==2 && q->operation==REIST_PIO_READ16 && ++d->chunks==8 && d->mode>=1 && d->mode<=3){
        if(notice(d->mode,1,256))return -5;
        if(d->mode==1)__asm__ volatile("ud2");
        if(d->mode==3)for(;;)__asm__ volatile("pause");
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
    void *record=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    REQUIRE((intptr_t)record>0,202);
    REQUIRE(!S1(IPC_CREATE,&request_ep) && !S1(IPC_CREATE,&reply_ep) && !S1(IPC_CREATE,&notice_ep),203);
    char rq[9],rp[9],np[9];number(rq,request_ep);number(rp,reply_ep);number(np,notice_ep);
#if BLOCK_PROFILE_CASE!=5
    reist_block_client client={0};reist_block_transport transport={0,clock_ms,sending,receiving};
#endif
    uint64_t previous=0;
    for(unsigned round=0;round<2;round++){
        unsigned mode=round?0:BLOCK_PROFILE_CASE;
        if(mode==6)mode=2;if(mode==7 || mode==5)mode=0;
        char kind[9];number(kind,mode|(round?16:0));const char *args[4]={rq,rp,np,kind};
        reist_task_startup_v1_t startup;REQUIRE(!reist_x64_startup_init(&startup,4,args),204);
        REQUIRE(!reist_x64_image_prepare_v2(record,import_blob,sizeof(import_blob)),205);
        reist_task_profile_v1_t profile={1,40,{MASK,1ULL<<49,0},0};
        int64_t child=reist_x64_task_import_wide(record,&profile,32,&startup);
#if BLOCK_PROFILE_CASE==7
        if(!round){REQUIRE(child==-12,206);child=reist_x64_task_import_wide(record,&profile,32,&startup);}
#endif
        REQUIRE(child>0 && (uint32_t)child==2 && (uint64_t)child>previous,207);
        typedef uint64_t word __attribute__((may_alias,aligned(1)));
        for(unsigned n=0;n<REIST_X64_PREPARED_V2_BYTES/8;n++)((volatile word*)record)[n]=0x5a5a5a5a5a5a5a5aULL;
        REQUIRE(!S3(IPC_DELEGATE,request_ep,(uint64_t)child>>32,2),208);
        REQUIRE(!S3(IPC_DELEGATE,reply_ep,(uint64_t)child>>32,1),209);
        REQUIRE(!S3(IPC_DELEGATE,notice_ep,(uint64_t)child>>32,1),210);
        REQUIRE(!pio(child,REIST_PIO_BIND),211);
        if(previous)REQUIRE(pio(previous,REIST_PIO_FENCE)==-13,212);
        REQUIRE(!notice(child,mode,0,BLOCK_PROFILE_CASE==5?19:128),213);
#if BLOCK_PROFILE_CASE==5
        REQUIRE(control(2,child,1000)==89,214);
#else
        REQUIRE(!reist_block_client_bind(&client,child),215);
#if BLOCK_PROFILE_CASE==6
        reist_block_header h={1,64,1,0,child,1,1,clock_ms(0)+1000,512,0,0};
        zero(&request,sizeof(request));request.version=1;request.struct_size=140;request.length=64;copy(request.payload,&h,64);
        REQUIRE(!sending(0,&request,1000) && !notice(child,mode,1,256),216);__asm__ volatile("ud2");
#endif
        unsigned limit=round?1:9;
        for(unsigned n=0;n<(mode?1:limit+1);n++){
            for(unsigned i=0;i<512;i++)output[i]=0xcc;
            unsigned lba=n+1;int result=reist_block_read(&client,&transport,lba,output,1000);
            witness(child,client.sequence,lba,result);
            if(mode){
                REQUIRE(mode==4?result==-71:(result==-32 || result==-110),217);
                if(mode!=4)REQUIRE(!notice(child,mode,1,256),218);
                if(mode==2 || mode==4){REQUIRE(!pio(child,REIST_PIO_FENCE),219);REQUIRE(!control(3,child,0),220);}
            }else REQUIRE(result==(n==limit?-11:0),221);
            for(unsigned i=0;i<512;i++)REQUIRE(output[i]==(result?0xcc:(unsigned char)(i^(lba*17)^0xa5)),222);
        }
        int64_t expected=mode==1?((1LL<<32)|134):mode==2||mode==4?(2LL<<32):mode==3?((1LL<<32)|256):80;
        REQUIRE(control(2,child,1000)==expected,223);
#endif
        REQUIRE(!pio(child,REIST_PIO_FENCE) && control(2,child,1)==-10,224);previous=child;
    }
    return BLOCK_PROFILE_CASE==5?79:78;
#elif PROGRAM_ID==1
    REQUIRE(argc==2 && argv[1][0]=='1',225);
    REQUIRE(reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,0)==-13,226);
    for(unsigned i=0;i<25;i++)REQUIRE(!S1(SLEEP_MS,100),227);
    return 77;
#elif PROGRAM_ID==2
    REQUIRE(argc==4,228);
    request_ep=number(argv[0]);reply_ep=number(argv[1]);notice_ep=number(argv[2]);unsigned options=number(argv[3]);
    Driver d={((uint64_t)S0(GETPID)<<32)|2,options&15,0,0};
    REQUIRE(request_ep && reply_ep && notice_ep && d.mode<=4 && options<=20,229);
    int64_t ready=-13;for(unsigned n=0;n<20 && ready==-13;n++){REQUIRE(!S1(SLEEP_MS,10),230);ready=pio(d.owner,REIST_PIO_READ8);}
    REQUIRE(ready>=0,231);
    reist_pio_ops ops={&d,port,clock_ms,sleep_ms};
    unsigned limit=options&16?1:9;reist_block_profile_v1 profile={1,24,limit,0,clock_ms(0)+2500};
    int result=reist_native_service_init_profile(&service,d.owner,&ops,&profile);
    if(result==-19){REQUIRE(!notice(d.mode,0,19),232);return 89;}
    REQUIRE(!result && service.service.server.capacity==128 && !notice(d.mode,0,128),233);
    for(unsigned n=0;n<limit+1;n++){
        zero(&request,sizeof(request));request.version=1;request.struct_size=140;request.length=128;
        REQUIRE(!S3(IPC_RECEIVE_TIMEOUT,request_ep,&request,1000),234);
        result=reist_native_service_dispatch_profile(&service,&request,&reply);
        if(d.mode==4 && !result)reply.payload[24]^=1;
        reist_block_header h;copy(&h,reply.payload,64);uint64_t now=clock_ms(0);
        unsigned timeout=h.deadline_ms>now && h.deadline_ms-now<=1000?(unsigned)(h.deadline_ms-now):1;
        REQUIRE(!S3(IPC_SEND_TIMEOUT,reply_ep,&reply,timeout),235);
    }
    return 80;
#else
    return 236;
#endif
}
