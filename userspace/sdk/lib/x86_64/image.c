#include <reist/x86_64/image.h>
#include <stdint.h>
static uint64_t get(const unsigned char *p,unsigned n) {
    uint64_t v=0;for(unsigned i=0;i<n;i++) v|=(uint64_t)p[i]<<(8*i);return v;
}
static void put(unsigned char *p,uint64_t v,unsigned n) {
    for(unsigned i=0;i<n;i++) p[i]=(unsigned char)(v>>(8*i));
}
int reist_x64_image_prepare(void *output,const void *elf,size_t length) {
    uintptr_t a=(uintptr_t)output,b=(uintptr_t)elf;
    if(!a || !b || length<64 || length>65536 || a>UINTPTR_MAX-36896 ||
       b>UINTPTR_MAX-length || (a<b+length && b<a+36896)) return -22;
    const unsigned char *p=elf;
    if(get(p,8)!=0x00010102464c457fULL || get(p+8,8) ||
       get(p+16,2)!=2 || get(p+18,2)!=62 || get(p+20,4)!=1 ||
       get(p+48,4) || get(p+52,2)!=64 || get(p+54,2)!=56) return -22;
    uint64_t entry=get(p+24,8),ph=get(p+32,8),count=get(p+56,2),previous=0;
    if(!count || count>8 || count>length/56 || ph<64 || ph>length-count*56) return -22;
    unsigned char flags[8]={0};unsigned executable=0;
    /* Capture all segment descriptors before output publication. */
    struct { uint64_t offset,va,size; } segments[8];
    for(unsigned i=0;i<count;i++) {
        const unsigned char *s=p+ph+i*56;
        uint64_t kind=get(s,4),rights=get(s+4,4),off=get(s+8,8),va=get(s+16,8);
        uint64_t files=get(s+32,8),memory=get(s+40,8),align=get(s+48,8);
        segments[i].size=0;
        if(!kind) continue;
        if(kind!=1 || rights<4 || rights>6 || align!=4096 || !memory || memory>32768 ||
           files>memory || off>length || files>length-off || va<0x400000 || va>=0x408000 ||
           memory>0x408000-va || va<previous || ((off^va)&4095)) return -22;
        unsigned first=(unsigned)(va-0x400000)/4096,last=(unsigned)(va+memory-1-0x400000)/4096;
        for(unsigned j=first;j<=last;j++) { if(flags[j]) return -22;flags[j]=(unsigned char)rights; }
        executable|=rights==5 && va<=entry && entry<va+files;
        previous=va+memory;segments[i].offset=off;segments[i].va=va;segments[i].size=files;
    }
    if(!executable) return -22;
    volatile unsigned char *zero=output;for(unsigned i=0;i<36896;i++) zero[i]=0;
    unsigned char *r=output;
    put(r,0x0000317647504e52ULL,8);put(r+8,1,4);put(r+12,36896,4);put(r+16,entry,8);
    for(unsigned i=0;i<8;i++) r[24+i]=flags[i];
    for(unsigned i=0;i<count;i++) for(unsigned j=0;j<segments[i].size;j++)
        r[32+segments[i].va-0x400000+j]=p[segments[i].offset+j];
    return 0;
}
