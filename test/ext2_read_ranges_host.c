/* Actual parser/range behavior, including the existing object suite. */
#define main existing_fixture_main
#include "test_vfs_shadow_ext2_host.c"
#undef main
#include "../userspace/storage/lib/vfs_shadow_ext2.c"
#include <stdio.h>
#define CHECK(v) do { if (!(v)) { fprintf(stderr,"range check line %d\n",__LINE__); return 1; } } while (0)
static uint32_t calls, fail_at, lbas[256];
static unsigned guard_calls;
static int guard_clock(void *v,uint64_t *milliseconds) { (void)v;*milliseconds=100;return 0; }
static int guard_snapshot(void *v,reist_file_object_guard_request_t *request) {
    (void)v;guard_calls++;
    if(request->operation!=REIST_FILE_OBJECT_SNAPSHOT) return -13;
    request->epoch=42;return 0;
}
static int counted(void *context, uint32_t resource, uint32_t lba, uint8_t *data) {
    if (calls == 256) return -5;
    lbas[calls++] = lba;
    if (fail_at && calls == fail_at) return -5;
    return read_sector(context, resource, lba, data);
}
static void layout(test_context_t *context, uint32_t log) {
    uint32_t bs = 1024U << log;
    memset(context,0,sizeof(*context));
    uint8_t *sb=context->image+1024;
    put32(sb,16); put32(sb+4,32); put32(sb+20,log?0:1);
    put32(sb+24,log); put32(sb+28,log); put32(sb+32,32);
    put32(sb+36,32); put32(sb+40,16); put16(sb+56,0xef53);
    put16(sb+58,1); put32(sb+76,1); put32(sb+84,11);
    put16(sb+88,128); put32(sb+96,2);
    uint8_t *gd=context->image+(log?1:2)*bs;
    put32(gd,3); put32(gd+4,4); put32(gd+8,5);
    uint8_t *root=context->image+5*bs+128;
    put16(root,0x41ed); put32(root+4,bs); put16(root+26,2);
    put32(root+28,bs/512); put32(root+40,21);
    uint8_t *file=context->image+5*bs+11*128;
    put16(file,0x81a4); put32(file+4,bs*2); put16(file+26,1);
    put32(file+28,bs/256); put32(file+40,22); put32(file+44,23);
    uint8_t *dir=context->image+21*bs;
    uint32_t off=add_entry(dir,0,2,".",2,12);
    off=add_entry(dir,off,2,"..",2,12);
    add_entry(dir,off,12,"readme.txt",1,(uint16_t)(bs-off));
    for (uint32_t n=0;n<bs*2;n++) context->image[22*bs+n]=(uint8_t)(n^(n>>8)^0xa5);
}
int main(void) {
    CHECK(existing_fixture_main()==0);
    static test_context_t context;
    const reist_vfs_shadow_io_t io={&context,drive_info,counted};
    uint8_t output[256]; uint32_t got;
    unsigned vectors=0;
    for (uint32_t log=0;log<3;log++) {
        uint32_t bs=1024U<<log;
        layout(&context,log);
        const uint32_t offsets[]={0,1,255,256,511,512,513,1023,1024,2047,2048,4095,4096,8191,UINT32_MAX};
        for (unsigned n=0;n<sizeof(offsets)/sizeof(offsets[0]);n++) {
            uint32_t offset=offsets[n];
            calls=fail_at=0; got=99; memset(output,0xcc,sizeof(output));
            CHECK(reist_vfs_shadow_ext2_read(&io,"/mnt/ext2/readme.txt",20,offset,output,256,&got)==0);
            uint32_t expected=offset>=bs*2?0:(bs*2-offset<256?bs*2-offset:256);
            CHECK(got==expected);
            for (uint32_t b=0;b<256;b++) CHECK(output[b]==(b<expected?(uint8_t)((offset+b)^((offset+b)>>8)^0xa5):0));
            uint32_t data_calls=0;
            for (uint32_t r=0;r<calls;r++) if (lbas[r]>=22*bs/512 && lbas[r]<24*bs/512) data_calls++;
            CHECK(data_calls==(expected?1+(offset%512+expected-1)/512:0));
            uint32_t successful_calls=calls;
            for (uint32_t failure=1;failure<=successful_calls;failure++) {
                calls=0; fail_at=failure; got=99; memset(output,0xcc,sizeof(output));
                CHECK(reist_vfs_shadow_ext2_read(&io,"/mnt/ext2/readme.txt",20,offset,output,256,&got)==-5);
                CHECK(calls==failure && got==0);
                for (uint32_t b=0;b<256;b++) CHECK(output[b]==0);
            }
            vectors++;
        }
        /* Whole physical block admission, even if requested sector fits. */
        ext2_request_t request; ext2_shadow_volume_t volume;
        ext2_shadow_inode_t inode; char visible[256];
        calls=fail_at=0;
        CHECK(ext2_request_from_legacy(&request,&io)==0);
        CHECK(ext2_resolve(&request,"/mnt/ext2/readme.txt",20,0,&volume,&inode,visible,0)==0);
        uint32_t saved=volume.sectors;
        volume.sectors=22*bs/512+1; calls=0; got=0;
        CHECK(ext2_read_file(&volume,&inode,0,output,1,&got)==-5 && calls==0 && got==0);
        volume.sectors=saved;
        /* A subrange crossing two sectors in one single-indirect data block
         * must read its pointer sector only once, including bulk consumers. */
        ext2_shadow_inode_t indirect=inode;
        put32(indirect.bytes+4,13*bs);put32(indirect.bytes+40+12*4,24);
        put32(context.image+24*bs,22);
        calls=0;got=0;
        CHECK(ext2_read_file(&volume,&indirect,12*bs+511,output,256,&got)==0);
        CHECK(got==256 && calls==3);
        /* Unsupported sparse/malformed mappings stay fail-closed, not zero-filled. */
        for (unsigned bad=0;bad<3;bad++) {
            ext2_shadow_inode_t broken=inode;
            put32(broken.bytes+40,bad==0?0:bad==1?32:UINT32_MAX);
            calls=0; got=0;
            CHECK(ext2_read_file(&volume,&broken,0,output,1,&got)==-5 && calls==0 && got==0);
        }
        /* Short-file sector working set for the native16-request profile. */
        put32(context.image+5*bs+11*128+4,15);
        calls=fail_at=0; got=0;
        CHECK(reist_vfs_shadow_ext2_read(&io,"/mnt/ext2/readme.txt",20,0,output,256,&got)==0 && got==15);
        unsigned unique=0;
        for (uint32_t n=0;n<calls;n++) {
            uint32_t p=0; while(p<n && lbas[p]!=lbas[n]) p++;
            if(p==n) unique++;
        }
        CHECK(unique==(log==0?8:log==1?10:14));
        reist_vfs_shadow_ext2_guarded_io_t guarded={
            {&context,drive_info,counted,0,0,guard_clock},0,guard_snapshot};
        calls=fail_at=guard_calls=0;got=99;
        CHECK(reist_vfs_shadow_ext2_read_bounded_guarded(&guarded,
            "/mnt/ext2/readme.txt",20,0,output,256,1000,&got)==0);
        CHECK(guard_calls==1 && got==15 && output[0]==0xa5);
        printf("EXT2_RANGE block=%u short_distinct=%u\n",bs,unique);
    }
    printf("EXT2_RANGE_PASS vectors=%u legacy_object=1\n",vectors);
    return 0;
}
