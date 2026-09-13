/* Actual end-to-end native FS -> native block -> generated media behavior. */
#include <reist/x86_64/filesystem.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../userspace/storage/lib/native_filesystem.c"
#define CHECK(v) do { if(!(v)) { fprintf(stderr,"FS check line %d\n",__LINE__); return 1; } } while(0)
typedef struct {
    uint8_t *media; unsigned sectors,physical,mutate,send_calls,receive_calls;
    uint64_t now; unsigned clock_fault,backend_fault; int send_fault,receive_fault;
    reist_fs_server fs; reist_block_server block; reist_block_profile_v1 profile;
    x86os_ipc_bulk_message_t block_reply,fs_reply;
} Host;
static uint64_t clock_ms(void *p) { Host *h=p; return h->now; }
static int sleep_ms(void *p,unsigned ms) { ((Host*)p)->now+=ms; return 0; }
static int read_data(void *p,uint32_t lba,uint8_t *out,uint64_t deadline) {
    Host *h=p; h->physical++;
    if(h->backend_fault || lba>=h->sectors || h->now>=deadline) return -5;
    memcpy(out,h->media+lba*512,512); return 0;
}
static int block_send(void *p,const x86os_ipc_message_t *q,unsigned ms) {
    Host *h=p; if(!ms || ms>1000) return -22;
    reist_block_backend backend={h,clock_ms,sleep_ms,read_data};
    (void)reist_block_dispatch_profile(&h->block,&h->profile,&backend,q,&h->block_reply);return 0;
}
static int block_receive(void *p,x86os_ipc_bulk_message_t *r,unsigned ms) {
    Host *h=p; if(!ms || ms>1000) return -22;
    *r=h->block_reply; if(h->backend_fault==2) r->payload[24]^=1; return 0;
}
static int fs_send(void *p,const x86os_ipc_bulk_message_t *q,unsigned ms) {
    Host *h=p; h->send_calls++; if(!ms || ms>3000) return -22;
    if(h->send_fault) return h->send_fault;
    (void)reist_fs_dispatch(&h->fs,q,&h->fs_reply); return 0;
}
static int fs_receive(void *p,x86os_ipc_bulk_message_t *r,unsigned ms) {
    Host *h=p; h->receive_calls++; if(!ms || ms>3000) return -22;
    if(h->receive_fault) return h->receive_fault;
    *r=h->fs_reply;
    if(h->mutate) {
        unsigned index=h->mutate-1;
        if(index<sizeof(*r)) ((uint8_t*)r)[index]^=0x80;
    }
    if(h->clock_fault==1) h->now=0;
    if(h->clock_fault==2) h->now+=3000;
    return 0;
}
static int start(Host *h,unsigned kind,uint64_t generation) {
    h->now=100; h->physical=h->mutate=h->clock_fault=h->backend_fault=0;
    h->send_calls=h->receive_calls=0;
    h->send_fault=h->receive_fault=0;
    uint64_t driver=((generation-1)<<32)|2,owner=(generation<<32)|3;
    h->profile=(reist_block_profile_v1){1,24,16,0,3000};
    if(reist_block_server_init(&h->block,driver,h->sectors,h->now)) return -1;
    reist_block_transport transport={h,clock_ms,block_send,block_receive};
    reist_fs_profile_v1 profile={1,40,kind,h->sectors,owner,driver,3000};
    return reist_fs_server_init(&h->fs,&profile,&transport);
}
int main(int argc,char **argv) {
    CHECK(argc==3); FILE *in=fopen(argv[1],"rb"); CHECK(in);
    CHECK(!fseek(in,0,SEEK_END)); long size=ftell(in); CHECK(size>0 && size<=70000*512 && !(size%512));
    rewind(in); static Host h; h.media=malloc((size_t)size); CHECK(h.media);
    CHECK(fread(h.media,1,(size_t)size,in)==(size_t)size); CHECK(!fclose(in)); h.sectors=(unsigned)size/512;
    unsigned kind=argv[2][0]=='f'?1:2; const char *path=kind==1?"/README.TXT":"/readme.txt";
    unsigned length=(unsigned)strlen(path); uint64_t gen=4;
    reist_fs_transport transport={&h,clock_ms,fs_send,fs_receive}; reist_fs_client client={0};
    reist_fs_frame frame,before; const char content[]="REIST NATIVE FILESYSTEM\n";
    CHECK(!start(&h,kind,gen)); CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
    for(unsigned op=5;op<=7;op++) {
        CHECK(!reist_fs_request_init(&frame,op,op==7?"/":path,op==7?1:length,0,op==6?256:0));
        CHECK(!reist_fs_call(&client,&transport,&frame,2000));
        if(op==6) CHECK(frame.read.transferred==sizeof(content)-1 && !memcmp(frame.read.data,content,sizeof(content)-1));
        else CHECK((op==5?frame.stat.info.size:frame.directory.info.size)==sizeof(content)-1);
    }
    unsigned physical=h.physical,normal_physical=h.physical;
    CHECK(physical<=14);
    CHECK(!reist_fs_request_init(&frame,6,path,length,5,5));
    CHECK(!reist_fs_call(&client,&transport,&frame,2000) && !memcmp(frame.read.data,content+5,5));
    CHECK(h.physical==physical);
    CHECK(!reist_fs_request_init(&frame,7,"/",1,1,0));
    CHECK(reist_fs_call(&client,&transport,&frame,2000)==1 && frame.directory.result==1);
    CHECK(!reist_fs_request_init(&frame,5,"/absent",7,0,0)); before=frame;
    CHECK(reist_fs_call(&client,&transport,&frame,2000)==-2 && !memcmp(&frame,&before,512) && !client.failed);
    for(unsigned n=0;n<2;n++) {
        CHECK(!reist_fs_request_init(&frame,5,path,length,0,0));
        CHECK(!reist_fs_call(&client,&transport,&frame,2000));
    }
    CHECK(!reist_fs_request_init(&frame,5,path,length,0,0)); before=frame;
    CHECK(reist_fs_call(&client,&transport,&frame,2000)==-11 && client.failed && !memcmp(&frame,&before,512));
    CHECK(h.physical==physical && h.fs.failed && !h.fs.used);
    for(unsigned i=0;i<sizeof(h.fs.data);i++) CHECK(!((uint8_t*)h.fs.data)[i]);
    CHECK(reist_fs_call(&client,&transport,&frame,2000)==-116);
    CHECK(reist_fs_client_bind(&client,(gen<<32)|3)==-22);
    CHECK(start(&h,kind,gen)==-22);
    gen+=2; CHECK(!start(&h,kind,gen)); CHECK(h.physical>0);
    /* Canonical request validation: each nonzero output/padding/header byte is
     * rejected before a block callback; generation becomes unusable. */
    unsigned rejected=0;
    const unsigned invalid[]={0,4,12,24,40,56,64,68,72,76,80,84,64+36+191,64+228,575,576,2047};
    for(unsigned n=0;n<sizeof(invalid)/sizeof(invalid[0]);n++) {
        gen+=2; CHECK(!start(&h,kind,gen)); physical=h.physical;
        CHECK(!reist_fs_request_init(&frame,6,path,length,0,256));
        x86os_ipc_bulk_message_t q={2,sizeof(q),576,{0}},r;
        reist_fs_header header={1,64,6,0,(gen<<32)|3,1,h.now+2000,0,512,0,0};
        memcpy(q.payload,&header,64);memcpy(q.payload+64,&frame,512);q.payload[invalid[n]]^=0x80;
        CHECK(reist_fs_dispatch(&h.fs,&q,&r)<0 && r.length==64 && h.physical==physical);
        rejected++;
    }
    /* Mutate structural fields and zero tail in real successful replies;
     * data bytes themselves are checked by the independent media/RPC oracle. */
    const unsigned corrupt[]={0,4,8,12,16,20,24,28,36,44,52,60,64,68,72,76,80,84,88,
        96,100,104,109,112,116,120,128,140,200,587,588,2059};
    for(unsigned n=0;n<sizeof(corrupt)/sizeof(corrupt[0]);n++) {
        gen+=2; CHECK(!start(&h,kind,gen)); CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
        CHECK(!reist_fs_request_init(&frame,6,path,length,0,256)); before=frame;
        h.mutate=corrupt[n]+1;
        int result=reist_fs_call(&client,&transport,&frame,2000);
        if(result!=-71) fprintf(stderr,"mutation byte=%u result=%d\n",corrupt[n],result);
        CHECK(result==-71 && client.failed && !memcmp(&frame,&before,512)); rejected++;
    }
    for(unsigned fault=1;fault<=2;fault++) {
        gen+=2; CHECK(!start(&h,kind,gen)); CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
        CHECK(!reist_fs_request_init(&frame,6,path,length,0,256)); before=frame;h.clock_fault=fault;
        CHECK(reist_fs_call(&client,&transport,&frame,2000)==(fault==1?-84:-110));
        CHECK(client.failed && !memcmp(&frame,&before,512));
    }
    for(unsigned fault=0;fault<4;fault++) {
        gen+=2; CHECK(!start(&h,kind,gen)); CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
        CHECK(!reist_fs_request_init(&frame,6,path,length,0,256)); before=frame;
        int error=fault&1?-2:1;
        if(fault<2) h.send_fault=error;else h.receive_fault=error;
        CHECK(reist_fs_call(&client,&transport,&frame,2000)==(error>0?-71:error));
        CHECK(client.failed && !memcmp(&frame,&before,512));
    }
    gen+=2; CHECK(!start(&h,kind,gen)); CHECK(!reist_fs_server_fence(&h.fs));
    CHECK(!reist_fs_server_fence(&h.fs) && h.fs.failed && h.fs.used==0);
    /* Exercise the actual private cache boundary through the actual block
     * protocol, without widening its public surface just for a test. */
    gen+=2; CHECK(!start(&h,kind,gen));
    uint8_t sector[512]; int cache_result=0;
    for(unsigned lba=0;lba<32 && !cache_result;lba++) {
        memset(sector,0xcc,512);cache_result=fs_sector(&h.fs,0,lba,sector);
    }
    CHECK(cache_result==-11 && h.physical==16 && h.fs.block.sequence==16);
    CHECK(h.fs.failed && !h.fs.used);
    for(unsigned n=0;n<512;n++) CHECK(sector[n]==0xcc);
    for(unsigned n=0;n<sizeof(h.fs.data);n++) CHECK(!((uint8_t*)h.fs.data)[n]);
    for(unsigned fault=0;fault<4;fault++) {
        gen+=2; CHECK(!start(&h,kind,gen)); physical=h.physical;
        unsigned lba=fault<2?h.fs.lba[0]:h.sectors-1;
        if(fault==0) h.now=0;
        else if(fault==1) h.now=h.fs.profile.deadline_ms;
        else h.backend_fault=fault-1;
        memset(sector,0xcc,512);cache_result=fs_sector(&h.fs,0,lba,sector);
        CHECK(cache_result==(fault==0?-84:fault==1?-110:fault==2?-5:-71));
        CHECK(h.physical==physical+(fault>=2) && h.fs.failed && !h.fs.used);
        for(unsigned n=0;n<512;n++) CHECK(sector[n]==0xcc);
    }
    printf("NATIVE_FS_HOST_PASS kind=%u normal_distinct=%u structural_negatives=%u\n",kind,normal_physical,rejected);
    free(h.media); return 0;
}
