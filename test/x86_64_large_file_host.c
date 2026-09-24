/* Real parser/block/capture code with only physical I/O and clocks modeled. */
#include <reist/x86_64/large_file.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(v) do {if(!(v)){fprintf(stderr,"WIDE check %d trial%u size%u\n",__LINE__,trial,bytes);return 1;}}while(0)
static unsigned trial,bytes;
typedef struct {
    unsigned char *media;
    unsigned sectors,reads,calls,receives,fault,at;
    uint64_t now,previous_read;
    reist_fs_server_v3 fs;
    reist_block_server block;
    reist_block_profile_v3 profile;
    x86os_ipc_bulk_message_t block_reply,fs_reply;
} Host;
static uint64_t clock_ms(void *p){return ((Host*)p)->now;}
static int sleep_ms(void *p,unsigned ms){Host *h=p;h->now+=h->fault==20?ms/2:ms;return 0;}
static int read_sector(void *p,uint32_t lba,unsigned char *data,uint64_t deadline){
    Host *h=p;
    if(lba>=h->sectors || h->now>=deadline ||
       h->now-h->previous_read<(h->reads?25:100))return -5;
    h->previous_read=h->now;h->reads++;
    memcpy(data,h->media+lba*512,512);return 0;
}
static int block_send(void *p,const x86os_ipc_message_t *q,unsigned ms){
    Host *h=p;if(!ms || ms>1000)return -22;
    reist_block_backend b={h,clock_ms,sleep_ms,read_sector};
    (void)reist_block_dispatch_profile_v3(&h->block,&h->profile,&b,q,&h->block_reply);return 0;
}
static int block_receive(void *p,x86os_ipc_bulk_message_t *q,unsigned ms){
    if(!ms || ms>1000)return -22;
    *q=((Host*)p)->block_reply;return 0;
}
static int fs_send(void *p,const x86os_ipc_bulk_message_t *q,unsigned ms){
    Host *h=p;if(!ms || ms>1000)return -22;h->calls++;
    (void)reist_fs_dispatch_v3(&h->fs,q,&h->fs_reply);return 0;
}
static int fs_receive(void *p,x86os_ipc_bulk_message_t *q,unsigned ms){
    Host *h=p;if(!ms || ms>1000)return -22;h->receives++;*q=h->fs_reply;
    if(h->receives==h->at){
        reist_fs_header *header=(void*)q->payload;
        reist_fs_frame *f=(void*)(q->payload+64);
        if(h->fault==1)header->owner+=1ULL<<32;
        if(h->fault==2 && f->read.transferred)f->read.data[--f->read.transferred]=0;
        if(h->fault==3)return -5;
        if(h->fault==4)h->now+=REIST_LARGE_FILE_MS;
        if(h->fault==5)h->now=0;
        if(h->fault==6)f->read.data[18]^=1;
    }
    return 0;
}
static int uniform(const void *p,size_t n,unsigned char value){
    const unsigned char *b=p;while(n--)if(*b++!=value)return 0;return 1;
}
static reist_file_image_workspace_v3 work;
static unsigned char output[REIST_X64_PREPARED_V3_BYTES],expected[REIST_X64_PREPARED_V3_BYTES];
static unsigned char input[REIST_LARGE_FILE_BYTES];
int main(int argc,char **argv){
    CHECK(argc==4 || argc==5);static Host h;
    FILE *f=fopen(argv[1],"rb");CHECK(f && !fseek(f,0,SEEK_END));
    long length=ftell(f);CHECK(length>0 && length<=70000*512 && !(length%512));rewind(f);
    h.media=malloc((size_t)length);CHECK(h.media && fread(h.media,1,(size_t)length,f)==(size_t)length && !fclose(f));
    h.sectors=(unsigned)length/512;f=fopen(argv[3],"rb");CHECK(f);
    bytes=(unsigned)fread(input,1,sizeof(input),f);CHECK(bytes>=121 && !fclose(f));
    CHECK(!reist_x64_image_prepare_v3(expected,input,bytes));
    /* A rejected request must not consume the first physical-read guard. */
    uint64_t pacing_owner=(UINT64_C(3)<<32)|2;
    for(unsigned rejected=0;rejected<5;rejected++) {
    h.now=h.previous_read=100;h.reads=0;h.fault=0;
    CHECK(!reist_block_server_init(&h.block,pacing_owner,h.sectors,h.now));
    h.profile=(reist_block_profile_v3){3,24,REIST_LARGE_BLOCK_REQUESTS,0,h.now+REIST_LARGE_FILE_MS};
    x86os_ipc_message_t pacing_request;memset(&pacing_request,0,sizeof(pacing_request));
    pacing_request.struct_size=sizeof(pacing_request);pacing_request.length=64;
    reist_block_header pacing_header={1,64,1,0,pacing_owner,1,0,1100,512,0,0};
    pacing_request.version=rejected?1:0;
    if(rejected==1)pacing_header.sequence=2;
    if(rejected==2)pacing_header.deadline_ms=150;
    if(rejected==3)h.fault=20;
    if(rejected==4)pacing_header.owner++;
    memcpy(pacing_request.payload,&pacing_header,sizeof(pacing_header));
    reist_block_backend pacing_backend={&h,clock_ms,sleep_ms,read_sector};
    int rejected_result=reist_block_dispatch_profile_v3(&h.block,&h.profile,&pacing_backend,&pacing_request,&h.block_reply);
    CHECK(rejected_result==(rejected==0?-22:rejected==1?-116:rejected==4?-13:-110));
    CHECK(!h.reads && h.block.ready==1);
    h.fault=0;pacing_request.version=1;pacing_header.owner=pacing_owner;
    pacing_header.sequence=h.block.next_sequence;pacing_header.deadline_ms=1100;
    memcpy(pacing_request.payload,&pacing_header,sizeof(pacing_header));
    int pacing_result=reist_block_dispatch_profile_v3(&h.block,&h.profile,&pacing_backend,&pacing_request,&h.block_reply);
    printf("WIDE_INITIAL_PACING result=%d elapsed=%llu reads=%u\n",pacing_result,(unsigned long long)(h.now-100),h.reads);
    CHECK(!pacing_result && h.now==200 && h.reads==1);
    CHECK(h.block.ready==2 && h.block.requests==2);
    pacing_header.sequence=h.block.next_sequence;
    memcpy(pacing_request.payload,&pacing_header,sizeof(pacing_header));
    CHECK(!reist_block_dispatch_profile_v3(&h.block,&h.profile,&pacing_backend,&pacing_request,&h.block_reply));
    CHECK(h.now==225 && h.reads==2 && h.block.requests==3);
    }
    h.now=h.previous_read=100;h.reads=0;h.fault=0;
    CHECK(!reist_block_server_init(&h.block,pacing_owner,h.sectors,h.now));
    reist_block_profile_v1 legacy_pacing={1,24,16,0,3100};
    x86os_ipc_message_t legacy_request;memset(&legacy_request,0,sizeof(legacy_request));
    legacy_request.struct_size=sizeof(legacy_request);legacy_request.length=64;
    reist_block_header legacy_header={1,64,1,0,pacing_owner,1,0,1100,512,0,0};
    memcpy(legacy_request.payload,&legacy_header,sizeof(legacy_header));
    reist_block_backend legacy_backend={&h,clock_ms,sleep_ms,read_sector};
    CHECK(reist_block_dispatch_profile(&h.block,&legacy_pacing,&legacy_backend,&legacy_request,&h.block_reply)==-22);
    legacy_request.version=1;
    CHECK(!reist_block_dispatch_profile(&h.block,&legacy_pacing,&legacy_backend,&legacy_request,&h.block_reply));
    CHECK(h.now==200 && h.reads==1 && h.block.ready==1);
    legacy_header.sequence=2;memcpy(legacy_request.payload,&legacy_header,sizeof(legacy_header));
    CHECK(!reist_block_dispatch_profile(&h.block,&legacy_pacing,&legacy_backend,&legacy_request,&h.block_reply));
    CHECK(h.now==300 && h.reads==2 && h.block.ready==1);
    int unsupported=!strcmp(argv[2],"ext2-1k") && bytes>(12+256)*1024;
    /* A byte ceiling never overrides the unchanged deadline. This FAT32
     * geometry's full FAT chain exceeds the16-sector working set at1MiB. */
    int deadline_limited=!strcmp(argv[2],"fat32") && bytes==1048576;
    for(trial=0;trial<(unsupported||deadline_limited?1U:20U);trial++){
        h.now=h.previous_read=100;h.reads=h.calls=h.receives=h.fault=h.at=0;
        uint64_t gen=4+trial*2,owner=(gen<<32)|3,driver=((gen-1)<<32)|2;
        h.profile=(reist_block_profile_v3){3,24,REIST_LARGE_BLOCK_REQUESTS,0,h.now+REIST_LARGE_FILE_MS};
        CHECK(!reist_block_profile_admit_v3(&h.profile,h.now));
        CHECK(reist_block_profile_admit((const reist_block_profile_v1*)&h.profile,h.now)==-22);
        CHECK(!reist_block_server_init(&h.block,driver,h.sectors,h.now));
        reist_block_transport bt={&h,clock_ms,block_send,block_receive};
        reist_fs_profile_v3 fp={3,40,argv[2][0]=='f'?REIST_FS_FAT:REIST_FS_EXT2,h.sectors,owner,driver,h.profile.deadline_ms};
        CHECK(!reist_fs_server_init_v3(&h.fs,&fp,&bt));
        reist_fs_client client={0};CHECK(!reist_fs_client_bind(&client,owner));
        reist_fs_transport ft={&h,clock_ms,fs_send,fs_receive};
        reist_file_capture_v3 observation;
        const char *path=argc==5?argv[4]:argv[2][0]=='f'?"/BOOT.PRG":"/boot.prg";
        CHECK(strlen(path)<=128);
        CHECK(!reist_x64_file_stat_v3(&observation,&client,&ft,path,(unsigned)strlen(path),h.profile.deadline_ms));
        CHECK(observation.version==3 && observation.deadline_ms==h.profile.deadline_ms);
        unsigned before=h.calls;int error=unsupported?-110:deadline_limited?-116:0,untouched=0;
        memset(&work,0x5a,sizeof(work));memset(output,0xa5,sizeof(output));
        if(trial==1){observation.version=1;error=-22;untouched=1;}
        if(trial==2){observation.owner+=1ULL<<32;error=-116;untouched=1;}
        if(trial==3){observation.sequence++;error=-116;untouched=1;}
        if(trial==4){observation.frame.stat.info.size=REIST_LARGE_FILE_BYTES+1;error=-27;untouched=1;}
        if(trial==5){observation.frame.stat.info.type=X86OS_DIRECTORY;error=-13;untouched=1;}
        if(trial==6){h.now=observation.deadline_ms;error=-110;}
        if(trial==7){h.now=0;error=-84;}
        if(trial>=8 && trial<=13){h.fault=trial-7;h.at=h.receives+1;error=trial==8?-71:trial==11?-110:trial==12?-84:trial==13?-22:-5;}
        if(trial==14){observation.frame.stat.info.size--;error=-5;}
        if(trial==15){client.sequence=observation.sequence=REIST_LARGE_FS_REQUESTS-1;error=-11;untouched=1;}
        if(trial==16){observation.frame.bytes[511]=1;error=-22;untouched=1;}
        if(trial==17){client.failed=1;error=-116;untouched=1;}
        if(trial==18){client.busy=1;error=-16;untouched=1;}
        if(trial==19){observation.deadline_ms=UINT64_MAX;error=-22;untouched=1;}
        int result=reist_x64_file_finish_v4(output,&work,&client,&ft,&observation);
        if(result!=error)fprintf(stderr,"got%d expected%d reads%u calls%u now%llu\n",result,error,h.reads,h.calls,(unsigned long long)h.now);
        CHECK(result==error);
        if(deadline_limited)CHECK(h.fs.state.failed && h.profile.deadline_ms==120100 &&
            h.now<=h.profile.deadline_ms && h.profile.deadline_ms-h.now<=50);
        CHECK(result?uniform(output,sizeof(output),0xa5):!memcmp(output,expected,sizeof(output)));
        CHECK(uniform(&work,sizeof(work),untouched?0x5a:0));
        CHECK(h.calls<=REIST_LARGE_FS_REQUESTS && h.reads<=REIST_LARGE_BLOCK_REQUESTS);
        if(untouched)CHECK(h.calls==before);
        if(!result){
            CHECK(h.calls==(bytes+255)/256+2);
            CHECK(reist_x64_file_finish_v4(output,&work,&client,&ft,&observation)==-116);
        }
        CHECK(!reist_fs_server_fence_v3(&h.fs));
        CHECK(h.fs.state.failed && !h.fs.state.used && !h.fs.next_slot);
        CHECK(uniform(h.fs.state.data,sizeof(h.fs.state.data),0));
    }
    free(h.media);puts("LARGE_FILE_PASS");return 0;
}
