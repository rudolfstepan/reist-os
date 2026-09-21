#include <reist/x86_64/app_files.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <reist/vfs_shadow_ext2.h>
#define CHECK(c) do { if(!(c)){printf("line%d: %s\n",__LINE__,#c);return 1;} }while(0)
static reist_app_snapshot snapshot;
static reist_app_grant grant,saved;
static reist_app_frame request,reply,sentinel;
static unsigned char *disk;
static unsigned disk_sectors,disk_reads;
static int drive(void *p,uint32_t resource,x86os_drive_info_t *out) {
    (void)p;if(resource)return 0;memset(out,0,sizeof(*out));
    out->type=X86OS_DRIVE_ATA;out->sectors=disk_sectors;strcpy(out->name,"ata0");strcpy(out->mount_point,"/");return 1;
}
static int sector(void *p,uint32_t resource,uint32_t lba,uint8_t *out) {
    (void)p;if(resource || lba>=disk_sectors || ++disk_reads>250000)return -5;
    memcpy(out,disk+512*lba,512);return 0;
}
static int media_case(char **argv) {
    FILE *f=fopen(argv[1],"rb");CHECK(f && !fseek(f,0,SEEK_END));long length=ftell(f);
    CHECK(length>0 && length<=70000*512 && !(length%512));rewind(f);disk=malloc((size_t)length);
    CHECK(disk && fread(disk,1,(size_t)length,f)==(size_t)length && !fclose(f));disk_sectors=(unsigned)length/512;
    int ext=!strncmp(argv[2],"ext2",4);reist_vfs_shadow_io_t io={0,drive,sector};
    const char *names[]={"boot.prg","cat.prg","ls.prg","probe.prg","data.txt"};
    for(unsigned n=0;n<5;n++) {
        char path[32],source[1024];snprintf(path,sizeof(path),"/%s",names[n]);
        CHECK(snprintf(source,sizeof(source),"%s/%s",argv[3],names[n])<(int)sizeof(source));
        f=fopen(source,"rb");CHECK(f && !fseek(f,0,SEEK_END));long size=ftell(f);rewind(f);
        CHECK(size>0 && size<=274432);x86os_file_info_t info;
        CHECK(!(ext?reist_vfs_shadow_ext2_stat(&io,path,(uint32_t)strlen(path),&info):
                    reist_vfs_shadow_fat_stat(&io,path,(uint32_t)strlen(path),&info)));
        CHECK(info.type==X86OS_FILE && info.size==(unsigned)size);
        for(unsigned offset=0;offset<=(unsigned)size;offset+=256) {
            unsigned count=(unsigned)size-offset;if(count>256)count=256;
            unsigned char data[256],expected[256];uint32_t got=0;
            CHECK(!(ext?reist_vfs_shadow_ext2_read(&io,path,(uint32_t)strlen(path),offset,data,256,&got):
                        reist_vfs_shadow_fat_read(&io,path,(uint32_t)strlen(path),offset,data,256,&got)));
            CHECK(got==count && fread(expected,1,count,f)==count && !memcmp(data,expected,count));
        }
        CHECK(!fclose(f));
    }
    unsigned seen=0;
    for(unsigned n=0;n<=5;n++) {
        x86os_file_info_t info;int r=ext?reist_vfs_shadow_ext2_readdir(&io,"/",1,n,&info):reist_vfs_shadow_fat_readdir(&io,"/",1,n,&info);
        CHECK(r==(n==5?1:0));
        if(!r){
            /* FAT short names preserve on-disk uppercase; EXT2 preserves bytes. */
            if(!ext)for(unsigned i=0;i<sizeof(info.name) && info.name[i];i++)
                if(info.name[i]>='A' && info.name[i]<='Z')info.name[i]+='a'-'A';
            unsigned k=0;while(k<5 && strcmp(info.name,names[k]))k++;CHECK(k<5 && !(seen&(1U<<k)));seen|=1U<<k;
        }
    }
    CHECK(seen==31);free(disk);puts("APP_FILES_MEDIA_HOST_OK");return 0;
}
static void query(unsigned operation) {
    memset(&request,0,sizeof(request));request.version=1;request.size=512;
    request.operation=operation;request.child=grant.child;request.sequence=grant.sequence+1;
    if(operation!=REIST_APP_HELLO){request.root=grant.root;request.epoch=grant.epoch;request.deadline=grant.deadline;}
}
static int rejected(int error,uint64_t now) {
    saved=grant;memset(&reply,0xa5,sizeof(reply));sentinel=reply;
    CHECK(reist_app_dispatch(&grant,&snapshot,&request,&reply,now)==error);
    CHECK(!memcmp(&reply,&sentinel,sizeof(reply)) && !memcmp(&grant,&saved,sizeof(grant)));return 0;
}
int main(int argc,char **argv) {
    if(argc==4)return media_case(argv);
    CHECK(argc==1);
    snapshot.info.type=X86OS_FILE;snapshot.info.size=16384;strcpy(snapshot.info.name,"data.txt");
    snapshot.length=16384;for(unsigned i=0;i<16384;i++)snapshot.bytes[i]=(unsigned char)i;
    CHECK(!reist_app_grant_init(&grant,&snapshot,7,10,1,100));
    CHECK(grant.deadline==1100 && grant.phase==REIST_APP_READY);
    saved=grant;CHECK(reist_app_grant_init(&grant,&snapshot,7,11,2,100)==-22 && !memcmp(&grant,&saved,sizeof(grant)));
    query(REIST_APP_STAT);CHECK(!rejected(-116,100));
    query(REIST_APP_HELLO);request.child++;CHECK(!rejected(-13,100));
    query(REIST_APP_HELLO);request.payload[431]=1;CHECK(!rejected(-22,100));
    query(REIST_APP_HELLO);CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,101));
    CHECK(reply.root==7 && reply.child==10 && reply.epoch==1 && reply.deadline==1100 && reply.length==sizeof(snapshot.info));
    CHECK(!memcmp(reply.payload,&snapshot.info,sizeof(snapshot.info)) && grant.phase==REIST_APP_BOUND);
    query(REIST_APP_READ);request.offset=16128;request.requested=256;
    CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,102));
    CHECK(reply.length==256 && !memcmp(reply.payload,snapshot.bytes+16128,256));
    query(REIST_APP_READ);request.offset=16384;request.requested=256;
    CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,103) && reply.length==0 && !reply.status);
    query(REIST_APP_READ);request.offset=UINT32_MAX;request.requested=256;CHECK(!rejected(-22,104));
    query(REIST_APP_READ);request.requested=257;CHECK(!rejected(-22,104));
    query(REIST_APP_STAT);request.epoch++;CHECK(!rejected(-13,104));
    query(REIST_APP_STAT);request.sequence--;CHECK(!rejected(-116,104));
    query(REIST_APP_STAT);request.deadline++;CHECK(!rejected(-116,104));
    query(99);CHECK(!rejected(-95,104));
    query(REIST_APP_STAT);CHECK(!rejected(-110,1100));CHECK(!rejected(-84,99));
    query(REIST_APP_READDIR);CHECK(!rejected(-20,104));
    query(REIST_APP_STAT);
    for(unsigned byte=0;byte<sizeof(request);byte++) {
        reist_app_frame original=request;((unsigned char*)&request)[byte]^=0x80;
        saved=grant;memset(&reply,0xa5,sizeof(reply));sentinel=reply;
        int status=reist_app_dispatch(&grant,&snapshot,&request,&reply,104);
        CHECK(status<0 && !memcmp(&grant,&saved,sizeof(grant)) && !memcmp(&reply,&sentinel,sizeof(reply)));
        request=original;
    }
    while(grant.sequence<80){query(REIST_APP_STAT);CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,105));}
    query(REIST_APP_STAT);CHECK(!rejected(-110,106));
    reist_app_revoke(&grant);CHECK(grant.phase==REIST_APP_CLOSED);saved=grant;
    reist_app_revoke(&grant);CHECK(!memcmp(&grant,&saved,sizeof(grant)));
    query(REIST_APP_HELLO);CHECK(!rejected(-116,107));
    memset(&grant,0,sizeof(grant));memset(&snapshot,0,sizeof(snapshot));
    snapshot.info.type=X86OS_DIRECTORY;strcpy(snapshot.info.name,"/");snapshot.count=32;
    for(unsigned i=0;i<32;i++){strcpy(snapshot.entries[i].name,"entry");snapshot.entries[i].type=X86OS_FILE;snapshot.entries[i].size=i;}
    CHECK(!reist_app_grant_init(&grant,&snapshot,8,12,2,0));
    query(REIST_APP_HELLO);CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,0));
    for(unsigned i=0;i<=32;i++) {query(REIST_APP_READDIR);request.offset=i;
        CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,1));
        CHECK(reply.status==(i<32?1:0) && reply.length==(i<32?sizeof(snapshot.info):0));}
    query(REIST_APP_READ);request.requested=1;CHECK(!rejected(-21,2));
    query(REIST_APP_CLOSE);CHECK(!reist_app_dispatch(&grant,&snapshot,&request,&reply,2));
    CHECK(!reply.status && !reply.length && grant.phase==REIST_APP_CLOSED);
    memset(&grant,0,sizeof(grant));snapshot.count=33;
    CHECK(reist_app_grant_init(&grant,&snapshot,8,12,2,0)==-22 && !grant.version);
    snapshot.count=32;snapshot.entries[0].name[255]=1;
    CHECK(reist_app_grant_init(&grant,&snapshot,8,12,2,0)==-22 && !grant.version);
    puts("APP_FILES_HOST_OK");return 0;
}
