/* Execute the real existing media/FS/block/ELF transport and both SDK stages. */
#define main original_filesystem_host_main
#include "x86_64_filesystem_host.c"
#undef main
#include <reist/x86_64/file_image.h>
static unsigned fault,at;
static int file_receive(void *p,x86os_ipc_bulk_message_t *reply,unsigned ms) {
    Host *h=p;int result=fs_receive(p,reply,ms);if(result)return result;
    reist_fs_header *header=(void *)reply->payload;
    reist_fs_frame *frame=(void *)(reply->payload+64);
    if(h->receive_calls==at && !header->status) {
        if(fault==5) {CHECK(frame->read.transferred);frame->read.data[--frame->read.transferred]=0;}
        if(fault==7)frame->read.data[18]^=1;
        if(fault==8)header->owner+=1ULL<<32;
        if(fault==9)return -5;
        if(fault==10)h->now=3100;
        if(fault==11)h->now=0;
    }
    return 0;
}
static int uniform(const void *p,unsigned n,unsigned value) {
    const unsigned char *b=p;while(n--)if(*b++!=value)return 0;return 1;
}
static reist_file_capture_v1 observation,saved;
static reist_file_image_workspace capture_workspace;
static unsigned char capture_output[REIST_X64_PREPARED_V2_BYTES];
static unsigned char capture_expected[REIST_X64_PREPARED_V2_BYTES];
int main(int argc,char **argv) {
    CHECK(argc==4);static Host h;
    FILE *in=fopen(argv[1],"rb");CHECK(in && !fseek(in,0,SEEK_END));
    long disk_size=ftell(in);CHECK(disk_size>0 && disk_size<=70000*512);rewind(in);
    h.media=malloc((size_t)disk_size);CHECK(h.media);
    CHECK(fread(h.media,1,(size_t)disk_size,in)==(size_t)disk_size && !fclose(in));
    h.sectors=(unsigned)disk_size/512;
    unsigned kind=argv[2][0]=='f'?1:2;const char *path=kind==1?"/BOOT.PRG":"/boot.prg";
    unsigned char raw[1536];in=fopen(argv[3],"rb");CHECK(in);
    unsigned bytes=(unsigned)fread(raw,1,sizeof(raw),in);CHECK(bytes>=121 && !fclose(in));
    CHECK(!reist_x64_image_prepare_v2(capture_expected,raw,bytes));
    reist_fs_transport transport={&h,clock_ms,fs_send,file_receive};
    for(unsigned trial=0;trial<34;trial++) {
        uint64_t gen=4+trial*2;CHECK(!start(&h,kind,gen));
        reist_fs_client client={0};CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
        memset(&observation,0xa5,sizeof(observation));saved=observation;
        memset(capture_output,0xa5,sizeof(capture_output));
        memset(&capture_workspace,0x5a,sizeof(capture_workspace));fault=at=0;
        /* A real preceding query consumes capacity; never reset its sequence. */
        if(trial==1 || trial==2) {
            for(unsigned n=0;n<(trial==1?1U:8U);n++) {
                reist_fs_frame frame;CHECK(!reist_fs_request_init(&frame,5,path,9,0,0));
                CHECK(!reist_fs_call(&client,&transport,&frame,1000));
            }
        }
        if(trial==3)client.busy=1;
        if(trial==4)client.failed=1;
        if(trial==5) {fault=8;at=1;}
        int status=reist_x64_file_stat_v1(&observation,&client,&transport,path,9,1800);
        if(trial>=2 && trial<=5) {
            CHECK(status==(trial==2?-11:trial==3?-16:trial==4?-116:-71));
            CHECK(!memcmp(&observation,&saved,sizeof(saved)));
            CHECK(uniform(capture_output,sizeof(capture_output),0xa5));continue;
        }
        CHECK(!status && observation.version==1 && observation.struct_size==552);
        CHECK(observation.owner==client.owner && observation.sequence==client.sequence);
        CHECK(observation.deadline_ms>observation.observed_ms && observation.frame.stat.info.size==bytes);
        saved=observation;unsigned before=h.send_calls;int expected=0,untouched=0;
        if(trial==1 && bytes>1280) {expected=-11;untouched=1;}
        if(trial==6) {observation.version++;expected=-22;untouched=1;}
        if(trial==7) {observation.struct_size--;expected=-22;untouched=1;}
        if(trial==8) {observation.owner+=1ULL<<32;expected=-116;untouched=1;}
        if(trial==9) {observation.sequence++;expected=-116;untouched=1;}
        if(trial==10) {observation.deadline_ms=observation.observed_ms;expected=-22;untouched=1;}
        if(trial==11) {observation.frame.stat.operation=6;expected=-22;untouched=1;}
        if(trial==12) {observation.frame.stat.path_length=192;expected=-22;untouched=1;}
        if(trial==13) {observation.frame.bytes[511]=1;expected=-22;untouched=1;}
        if(trial==14) {observation.frame.stat.info.type=X86OS_DIRECTORY;expected=-13;untouched=1;}
        if(trial==15) {observation.frame.stat.info.size=1537;expected=-27;untouched=1;}
        if(trial==16) {h.now=0;expected=-84;}
        if(trial==17) {h.now=observation.deadline_ms;expected=-110;}
        if(trial==18) {
            reist_fs_frame frame;CHECK(!reist_fs_request_init(&frame,5,path,9,0,0));
            CHECK(!reist_fs_call(&client,&transport,&frame,1000));
            before=h.send_calls;expected=-116;untouched=1;
        }
        if(trial>=19 && trial<=24) {
            fault=trial==19?5:trial==20?8:trial==21?9:trial==22?10:trial==23?11:7;
            at=2;expected=trial==19?-5:trial==20?-71:trial==21?-5:trial==22?-110:trial==23?-84:-22;
        }
        if(trial==25) {observation.frame.stat.info.size=0;expected=-27;untouched=1;}
        if(trial==26) {observation.frame.stat.result=1;expected=-22;untouched=1;}
        if(trial==27) {observation.frame.stat.info.name[255]='x';expected=-22;untouched=1;}
        if(trial==28) {observation.deadline_ms=UINT64_MAX;expected=-22;untouched=1;}
        if(trial==29) {client.busy=1;expected=-16;untouched=1;}
        if(trial==30) {client.failed=1;expected=-116;untouched=1;}
        if(trial==31) {observation.sequence=0;expected=-22;untouched=1;}
        if(trial==32) {observation.frame.stat.path[0]='x';expected=-22;untouched=1;}
        if(trial==33) {observation.frame.stat.info.size=bytes-1;expected=-5;}
        status=reist_x64_file_finish_v2(capture_output,&capture_workspace,&client,&transport,&observation);
        if(status!=expected)fprintf(stderr,"capture trial%u got%d expected%d\n",trial,status,expected);
        CHECK(status==expected);
        CHECK(status?uniform(capture_output,sizeof(capture_output),0xa5):!memcmp(capture_output,capture_expected,sizeof(capture_output)));
        CHECK(uniform(&capture_workspace,sizeof(capture_workspace),untouched?0x5a:0));
        CHECK(h.send_calls<=8 && h.physical<=16);
        if(untouched)CHECK(h.send_calls==before);
        if(!status) {
            CHECK(h.send_calls==(bytes+255)/256+2+(trial==1));
            memset(&capture_workspace,0x5a,sizeof(capture_workspace));
            CHECK(reist_x64_file_finish_v2(capture_output,&capture_workspace,&client,&transport,&observation)==-116);
            CHECK(uniform(&capture_workspace,sizeof(capture_workspace),0x5a));
        }
    }
    CHECK(sizeof(observation)==552);
    CHECK(!start(&h,kind,100));reist_fs_client client={0};
    CHECK(!reist_fs_client_bind(&client,(100ULL<<32)|3));fault=at=0;
    memset(&observation,0xa5,sizeof(observation));saved=observation;
    CHECK(reist_x64_file_stat_v1((void *)&client,&client,&transport,path,9,100)==-22);
    CHECK(reist_x64_file_stat_v1(&observation,&client,&transport,(void *)&observation,9,100)==-22);
    CHECK(reist_x64_file_stat_v1(&observation,&client,&transport,path,192,100)==-22);
    CHECK(reist_x64_file_stat_v1(&observation,&client,&transport,path,9,0)==-22);
    CHECK(reist_x64_file_stat_v1((void *)(UINTPTR_MAX-32),&client,&transport,path,9,100)==-22);
    CHECK(!h.send_calls && !memcmp(&observation,&saved,sizeof(saved)));
    uint64_t after_selftest=h.now;
    h.now=UINT64_MAX;memset(&capture_workspace,0x5a,sizeof(capture_workspace));
    CHECK(reist_x64_file_prepare_v2(capture_output,&capture_workspace,&client,&transport,path,9,100)==-22);
    CHECK(uniform(&capture_workspace,sizeof(capture_workspace),0x5a) && !h.send_calls);
    h.now=after_selftest;int final_stat=reist_x64_file_stat_v1(&observation,&client,&transport,path,9,1800);
    if(final_stat)fprintf(stderr,"final stat=%d now=%llu failed=%u seq=%llu requests=%u\n",final_stat,
        (unsigned long long)h.now,client.failed,(unsigned long long)client.sequence,h.fs.requests);
    CHECK(!final_stat);
    CHECK(reist_x64_file_finish_v2(capture_workspace.prepared,&capture_workspace,&client,&transport,&observation)==-22);
    CHECK(reist_x64_file_finish_v2(capture_output,&capture_workspace,&client,&transport,(void *)&capture_workspace)==-22);
    CHECK(reist_x64_file_finish_v2((void *)(UINTPTR_MAX-32),&capture_workspace,&client,&transport,&observation)==-22);
    CHECK(h.send_calls==1 && uniform(&capture_workspace,sizeof(capture_workspace),0x5a));
    free(h.media);puts("FILE_CAPTURE_PASS real-stat/read/EOF/ELF single-publication bounds<=8");return 0;
}
