/* Reuse real old FS/block host transport and parser setup, no second model. */
#define main original_filesystem_host_main
#include "x86_64_filesystem_host.c"
#undef main
#include <reist/x86_64/file_image.h>
static unsigned fault,at;
static int file_receive(void *p,x86os_ipc_bulk_message_t *reply,unsigned ms) {
    Host *h=p; int r=fs_receive(p,reply,ms); if(r) return r;
    reist_fs_header *header=(void *)reply->payload;
    reist_fs_frame *frame=(void *)(reply->payload+64);
    if(h->receive_calls==at && header->status==0) {
        if(fault==1) frame->stat.info.size=1537;
        if(fault==2) frame->stat.info.size=0;
        if(fault==3) frame->stat.info.type=X86OS_DIRECTORY;
        if(fault==4) frame->stat.info.type=X86OS_SYMLINK;
        if(fault==5) { CHECK(frame->read.transferred);frame->read.data[--frame->read.transferred]=0; }
        if(fault==6) { CHECK(!frame->read.transferred);frame->read.transferred=1;frame->read.data[0]=0x7f; }
        if(fault==7) frame->read.data[18]^=1;
        if(fault==8) header->owner+=1ULL<<32;
        if(fault==9) return -5;
        if(fault==10) h->now=3100;
        if(fault==11) h->now=0;
    }
    return 0;
}
static int uniform(const void *p,unsigned n,unsigned value) {
    const unsigned char *b=p;while(n--) if(*b++!=value)return 0;return 1;
}
int main(int argc,char **argv) {
    CHECK(argc==4);FILE *in=fopen(argv[1],"rb");CHECK(in && !fseek(in,0,SEEK_END));
    long size=ftell(in);CHECK(size>0 && size<=70000*512);rewind(in);
    static Host h;h.media=malloc((size_t)size);CHECK(h.media && fread(h.media,1,(size_t)size,in)==(size_t)size);CHECK(!fclose(in));h.sectors=(unsigned)size/512;
    unsigned kind=argv[2][0]=='f'?1:2;const char *path=kind==1?"/BOOT.PRG":"/boot.prg";
    unsigned char raw[1536];in=fopen(argv[3],"rb");CHECK(in && fread(raw,1,sizeof(raw),in)==sizeof(raw));CHECK(!fclose(in));
    static unsigned char output[REIST_X64_PREPARED_V2_BYTES],expected[REIST_X64_PREPARED_V2_BYTES];
    static reist_file_image_workspace workspace;
    CHECK(!reist_x64_image_prepare_v2(expected,raw,sizeof(raw)));
    reist_fs_transport transport={&h,clock_ms,fs_send,file_receive};reist_fs_client client={0};uint64_t gen=4;
    for(unsigned trial=0;trial<34;trial++,gen+=2) {
        CHECK(!start(&h,kind,gen));client=(reist_fs_client){0};CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
        memset(output,0xa5,sizeof(output));memset(&workspace,0x5a,sizeof(workspace));
        fault=at=0;int expected_result=0;
        if(trial>=1 && trial<=4) {fault=trial;at=1;expected_result=trial<=2?-27:-13;}
        if(trial>=5 && trial<=10) {fault=5;at=trial-3;expected_result=-5;}
        if(trial==11) {fault=6;at=8;expected_result=-5;}
        if(trial==12) {fault=7;at=2;expected_result=-22;}
        if(trial>=13 && trial<=20) {fault=8;at=trial-12;expected_result=-71;}
        if(trial>=21 && trial<=28) {fault=9;at=trial-20;expected_result=-5;}
        if(trial==29) {fault=10;at=2;expected_result=-110;}
        if(trial==30) {fault=11;at=2;expected_result=-84;}
        if(trial==31) {client.sequence=1;expected_result=-22;}
        if(trial==32) {client.busy=1;expected_result=-16;}
        if(trial==33) {client.failed=1;expected_result=-116;}
        int result=reist_x64_file_prepare_v2(output,&workspace,&client,&transport,path,9,2000);
        if(result!=expected_result)fprintf(stderr,"file trial %u got%d expected%d\n",trial,result,expected_result);
        CHECK(result==expected_result);
        CHECK(result?uniform(output,sizeof(output),0xa5):!memcmp(output,expected,sizeof(output)));
        CHECK(uniform(&workspace,sizeof(workspace),trial>=31?0x5a:0));
        CHECK(h.send_calls<=8 && h.physical<=16);
        if(trial>=31) CHECK(!h.send_calls);
        if(!trial) CHECK(h.send_calls==8 && client.sequence==8);
        if(trial>=1 && trial<=4) CHECK(h.send_calls==1);
    }
    CHECK(!start(&h,kind,gen));client=(reist_fs_client){0};CHECK(!reist_fs_client_bind(&client,(gen<<32)|3));
    memset(&workspace,0x5a,sizeof(workspace));
    CHECK(reist_x64_file_prepare_v2(workspace.prepared,&workspace,&client,&transport,path,9,100)==-22);
    CHECK(reist_x64_file_prepare_v2(output,&workspace,&client,&transport,path,192,100)==-22);
    CHECK(reist_x64_file_prepare_v2(output,&workspace,&client,&transport,path,9,3001)==-22);
    CHECK(reist_x64_file_prepare_v2((void *)(UINTPTR_MAX-1024),&workspace,&client,&transport,path,9,100)==-22);
    CHECK(!h.send_calls && uniform(&workspace,sizeof(workspace),0x5a));
    free(h.media);puts("FILE_IMAGE_HOST_PASS requests<=8 sectors<=16 all-output-and-scrub");return 0;
}
