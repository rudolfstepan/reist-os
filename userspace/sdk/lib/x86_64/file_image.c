#include <reist/x86_64/file_image.h>
typedef uint64_t file_word __attribute__((may_alias,aligned(1)));
static void file_clear(void *object,unsigned length) {
    volatile unsigned char *p=object;
    while(length>=8) { *(volatile file_word *)p=0;p+=8;length-=8; }
    while(length--) *p++=0;
}
static void file_copy(void *output,const void *input,unsigned length) {
    unsigned char *a=output;const unsigned char *b=input;
    while(length>=8) { *(volatile file_word *)a=*(const file_word *)b;a+=8;b+=8;length-=8; }
    while(length--) *a++=*b++;
}
static int file_range(const void *p,size_t bytes) {
    return p && bytes && (uintptr_t)p<=UINTPTR_MAX-bytes;
}
static int file_overlap(const void *a,size_t an,const void *b,size_t bn) {
    return (uintptr_t)a<(uintptr_t)b+bn && (uintptr_t)b<(uintptr_t)a+an;
}
int reist_x64_file_prepare_v2(void *output,reist_file_image_workspace *w,
    reist_fs_client *c,const reist_fs_transport *t,const char *path,unsigned length,unsigned timeout) {
    if(!length || length>=192 || !timeout || timeout>3000) return -22;
    const void *objects[]={output,w,c,t,path};
    const size_t sizes[]={REIST_X64_PREPARED_V2_BYTES,sizeof(*w),sizeof(*c),sizeof(*t),length};
    for(unsigned i=0;i<5;i++) if(!file_range(objects[i],sizes[i])) return -22;
    for(unsigned i=0;i<3;i++) for(unsigned j=i+1;j<5;j++)
        if(file_overlap(objects[i],sizes[i],objects[j],sizes[j])) return -22;
    if(c->busy) return -16;
    if(c->failed) return -116;
    if(c->sequence || (uint32_t)c->owner!=3 || !(c->owner>>32) || c->owner>INT64_MAX ||
       !t->clock || !t->send || !t->receive || path[0]!='/') return -22;
    for(unsigned i=0;i<length;i++) if(!path[i]) return -22;
    reist_fs_transport transport=*t;uint64_t owner=c->owner;
    uint64_t last=transport.clock(transport.context);
    if(last>UINT64_MAX-timeout) return -22;
    uint64_t deadline=last+timeout;unsigned size=0,offset=0;
    int result=0;
    file_clear(w,sizeof(*w));
    /* Fresh stat, <=6 complete data reads, one exact EOF. No retry or rebind. */
    for(unsigned call=0;call<8;call++) {
        unsigned requested=call?(offset<size?(size-offset<256?size-offset:256):1):0;
        result=reist_fs_request_init(&w->frame,call?6:5,path,length,offset,requested);
        if(result) break;
        uint64_t now=transport.clock(transport.context);
        if(now<last || now>=deadline) {result=now<last?-84:-110;break;}
        if(c->owner!=owner || c->sequence!=call) {result=-116;break;}
        result=reist_fs_call(c,&transport,&w->frame,(unsigned)(deadline-now));
        if(result) break;
        last=transport.clock(transport.context);
        if(last<now || last>=deadline) {result=last<now?-84:-110;break;}
        if(c->owner!=owner || c->sequence!=call+1) {result=-116;break;}
        if(!call) {
            if(w->frame.stat.info.type!=X86OS_FILE) {result=-13;break;}
            size=w->frame.stat.info.size;
            if(size<64 || size>REIST_X64_FILE_IMAGE_BYTES) {result=-27;break;}
        } else if(offset<size) {
            if(w->frame.read.transferred!=requested) {result=-5;break;}
            file_copy(w->file+offset,w->frame.read.data,requested);offset+=requested;
        } else {
            if(w->frame.read.transferred) {result=-5;break;}
            result=reist_x64_image_prepare_v2(w->prepared,w->file,size);
            if(result) break;
            now=transport.clock(transport.context);
            if(now<last || now>=deadline) {result=now<last?-84:-110;break;}
            if(c->owner!=owner || c->sequence!=call+1) {result=-116;break;}
            /* Single publication after full ELF validation and deadline admission. */
            file_copy(output,w->prepared,REIST_X64_PREPARED_V2_BYTES);
            file_clear(w,sizeof(*w));return 0;
        }
    }
    if(!result) result=-5;
    file_clear(w,sizeof(*w));return result;
}
