#include "native_pio.h"
static int64_t io(const reist_pio_ops *o,uint64_t owner,unsigned op,unsigned port,
                  unsigned value,unsigned count,void *data) {
    reist_native_pio_request q={1,64,op,0,owner,port,value,count,0,(uintptr_t)data,0,0};
    return o->call(o->context,&q);
}
static int valid(const reist_pio_ops *o,uint64_t owner) {
#if REIST_NATIVE_POOL_PIO
    return o && o->call && o->clock && o->sleep && reist_pio_pool_owner_valid(owner);
#else
    return o && o->call && o->clock && o->sleep && (uint32_t)owner>=2 &&
        (uint32_t)owner<=3 && (owner>>32) && (owner>>32)<=0x7fffffff;
#endif
}
static int wait_status(const reist_pio_ops *o,uint64_t owner,int data) {
    uint64_t last=o->clock(o->context);if(last>UINT64_MAX-200) return -84;
    uint64_t deadline=last+200;
    for(unsigned polls=0;polls<21;polls++) {
        int64_t s=io(o,owner,REIST_PIO_READ8,0x1f7,0,0,0);
        if(s<0) return (int)s;
        if(s==0 || s==255) return -19;
        if(!(s&128)) {
            if(s&0x21) return -5;
            if(!!(s&8)==data) return 0;
        }
        uint64_t now=o->clock(o->context);
        if(now<last) return -84;
        if(now>=deadline) return -110;
        last=now;
        int rc=o->sleep(o->context,10);if(rc) return rc;
    }
    return -110;
}
static int select_master(const reist_pio_ops *o,uint64_t owner,uint32_t lba) {
    int64_t rc=io(o,owner,REIST_PIO_WRITE8,0x1f6,0xe0|(lba>>24),0,0);
    if(rc) return (int)rc;
    /* ATA device-select settling: four alternate-status port accesses. */
    for(unsigned i=0;i<4;i++) {
        rc=io(o,owner,REIST_PIO_READ8,0x3f6,0,0,0);if(rc<0) return (int)rc;
    }
    return 0;
}
static int transfer(const reist_pio_ops *o,uint64_t owner,uint16_t words[256]) {
    int rc=wait_status(o,owner,1);if(rc) return rc;
    for(unsigned n=0;n<256;n+=16) {
        int64_t result=io(o,owner,REIST_PIO_READ16,0x1f0,0,16,words+n);
        if(result) return (int)result;
    }
    return wait_status(o,owner,0);
}
int reist_pio_identify(const reist_pio_ops *o,uint64_t owner,uint32_t *sectors) {
    if(!valid(o,owner) || !sectors) return -22;
    int rc=o->sleep(o->context,10);if(rc) return rc;
    int64_t r=io(o,owner,REIST_PIO_WRITE8,0x3f6,2,0,0);if(r) return (int)r;
    rc=select_master(o,owner,0);if(rc) return rc;
    r=io(o,owner,REIST_PIO_WRITE8,0x1f7,0xec,0,0);if(r) return (int)r;
    uint16_t words[256];rc=transfer(o,owner,words);if(rc) return rc;
    uint32_t total=words[60]|((uint32_t)words[61]<<16);
    if(!(words[49]&(1U<<9)) || !total || total>0x10000000U) return -19;
    *sectors=total;return 0;
}
int reist_pio_read(const reist_pio_ops *o,uint64_t owner,uint32_t sectors,
                   uint32_t lba,unsigned char output[512]) {
    if(!valid(o,owner) || !output || !sectors || sectors>0x10000000U || lba>=sectors) return -22;
    int rc=select_master(o,owner,lba);if(rc) return rc;
    for(unsigned reg=2;reg<=5;reg++) {
        unsigned value=reg==2?1:(lba>>(8*(reg-3)))&255;
        int64_t r=io(o,owner,REIST_PIO_WRITE8,0x1f0+reg,value,0,0);if(r) return (int)r;
    }
    int64_t r=io(o,owner,REIST_PIO_WRITE8,0x1f7,0x20,0,0);if(r) return (int)r;
    uint16_t words[256];rc=transfer(o,owner,words);if(rc) return rc;
    for(unsigned i=0;i<256;i++) {output[2*i]=(unsigned char)words[i];output[2*i+1]=(unsigned char)(words[i]>>8);}
    return 0;
}
