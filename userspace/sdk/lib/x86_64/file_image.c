#include <reist/x86_64/file_image.h>
#include <reist/x86_64/wide_file.h>
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
static int file_objects(const void *const *objects,const size_t *sizes,unsigned count,unsigned mutable) {
    for(unsigned i=0;i<count;i++) if(!file_range(objects[i],sizes[i])) return -22;
    for(unsigned i=0;i<mutable;i++) for(unsigned j=i+1;j<count;j++)
        if(file_overlap(objects[i],sizes[i],objects[j],sizes[j])) return -22;
    return 0;
}
static int file_client(const reist_fs_client *c,const reist_fs_transport *t) {
    if(c->busy) return -16;
    if(c->failed) return -116;
    if((uint32_t)c->owner!=3 || !(c->owner>>32) || c->owner>INT64_MAX ||
       !t->clock || !t->send || !t->receive) return -22;
    return 0;
}
static int file_path(const char *path,unsigned length) {
    if(path[0]!='/') return -22;
    for(unsigned i=0;i<length;i++) if(!path[i]) return -22;
    return 0;
}
static int file_stat_call(reist_file_capture_v1 *out,reist_fs_client *c,
    const reist_fs_transport *t,const char *path,unsigned length,unsigned timeout,
    uint64_t start,uint64_t owner,uint64_t sequence,unsigned version,unsigned rpc_ms) {
    reist_file_capture_v1 next;file_clear(&next,sizeof(next));
    next.version=version;next.struct_size=sizeof(next);next.owner=owner;next.sequence=sequence;
    int result=reist_fs_request_init(&next.frame,5,path,length,0,0);if(result)return result;
    reist_fs_transport transport=*t;
    next.deadline_ms=start+timeout;
    uint64_t now=transport.clock(transport.context);
    if(now<start || now>=next.deadline_ms)return now<start?-84:-110;
    if(c->owner!=next.owner || c->sequence!=next.sequence-1)return -116;
    uint64_t remaining=next.deadline_ms-now;
    result=reist_fs_call(c,&transport,&next.frame,remaining>rpc_ms?rpc_ms:(unsigned)remaining);
    if(result)return result;
    next.observed_ms=transport.clock(transport.context);
    if(next.observed_ms<now || next.observed_ms>=next.deadline_ms)
        return next.observed_ms<now?-84:-110;
    if(c->owner!=next.owner || c->sequence!=next.sequence)return -116;
    file_copy(out,&next,sizeof(next));return 0;
}
int reist_x64_file_stat_v1(reist_file_capture_v1 *out,reist_fs_client *c,
    const reist_fs_transport *t,const char *path,unsigned length,unsigned timeout) {
    if(!length || length>=192 || !timeout || timeout>3000)return -22;
    const void *objects[]={out,c,t,path};
    const size_t sizes[]={sizeof(*out),sizeof(*c),sizeof(*t),length};
    int result=file_objects(objects,sizes,4,2);if(result)return result;
    result=file_client(c,t);if(result)return result;
    if(file_path(path,length))return -22;
    if(c->sequence>=REIST_FS_SESSION_REQUESTS)return -11;
    reist_fs_transport transport=*t;
    uint64_t owner=c->owner,sequence=c->sequence+1,start=transport.clock(transport.context);
    if(start>UINT64_MAX-timeout)return -22;
    return file_stat_call(out,c,&transport,path,length,timeout,start,owner,sequence,1,3000);
}
static int file_observation(const reist_file_capture_v1 *p,unsigned version,unsigned requests,
    unsigned milliseconds,unsigned capacity) {
    if(p->version!=version || p->struct_size!=sizeof(*p) || !p->sequence ||
       p->sequence>requests || p->deadline_ms<=p->observed_ms ||
       p->deadline_ms-p->observed_ms>milliseconds)return -22;
    unsigned length=p->frame.stat.path_length;
    if(!length || length>=192 || file_path(p->frame.stat.path,length))return -22;
    reist_fs_frame canonical;
    if(reist_fs_request_init(&canonical,5,p->frame.stat.path,length,0,0))return -22;
    file_copy(&canonical.stat.info,&p->frame.stat.info,sizeof(canonical.stat.info));
    for(unsigned n=0;n<512;n++)if(canonical.bytes[n]!=p->frame.bytes[n])return -22;
    unsigned n=0;while(n<sizeof(canonical.stat.info.name) && canonical.stat.info.name[n])n++;
    if(!n || n==sizeof(canonical.stat.info.name))return -22;
    for(;n<sizeof(canonical.stat.info.name);n++)if(canonical.stat.info.name[n])return -22;
    if(canonical.stat.info.type!=X86OS_FILE)return -13;
    if(canonical.stat.info.size<64 || canonical.stat.info.size>capacity)return -27;
    return 0;
}
static int file_finish(void *output,void *w,unsigned workspace_bytes,
    unsigned char *file,reist_fs_frame *frame,unsigned char *prepared,
    reist_fs_client *c,const reist_fs_transport *t,const reist_file_capture_v1 *p,
    unsigned version,unsigned requests,unsigned milliseconds,unsigned capacity,unsigned rpc_ms) {
    const void *objects[]={output,w,c,t,p};
    const size_t sizes[]={REIST_X64_PREPARED_V2_BYTES,workspace_bytes,sizeof(*c),sizeof(*t),sizeof(*p)};
    int result=file_objects(objects,sizes,5,3);if(result)return result;
    result=file_client(c,t);if(result)return result;
    result=file_observation(p,version,requests,milliseconds,capacity);if(result)return result;
    if(c->owner!=p->owner || c->sequence!=p->sequence)return -116;
    unsigned size=p->frame.stat.info.size,offset=0;
    unsigned calls=(size+255)/256+1;
    if(calls>requests-c->sequence)return -11;
    reist_fs_transport transport=*t;uint64_t owner=c->owner;
    uint64_t sequence=c->sequence,last=p->observed_ms,deadline=p->deadline_ms;
    /* Snapshot the observation before callbacks, including the exact path. */
    char path[192];unsigned length=p->frame.stat.path_length;
    file_copy(path,p->frame.stat.path,length);path[length]=0;
    file_clear(w,workspace_bytes);
    /* Fixed profile capacity determines complete reads plus one exact EOF. */
    for(unsigned call=0;call<calls;call++) {
        unsigned requested=offset<size?(size-offset<256?size-offset:256):1;
        result=reist_fs_request_init(frame,6,path,length,offset,requested);
        if(result) break;
        uint64_t now=transport.clock(transport.context);
        if(now<last || now>=deadline) {result=now<last?-84:-110;break;}
        if(c->owner!=owner || c->sequence!=sequence+call) {result=-116;break;}
        uint64_t remaining=deadline-now;
        result=reist_fs_call(c,&transport,frame,remaining>rpc_ms?rpc_ms:(unsigned)remaining);
        if(result) break;
        last=transport.clock(transport.context);
        if(last<now || last>=deadline) {result=last<now?-84:-110;break;}
        if(c->owner!=owner || c->sequence!=sequence+call+1) {result=-116;break;}
        if(offset<size) {
            if(frame->read.transferred!=requested) {result=-5;break;}
            file_copy(file+offset,frame->read.data,requested);offset+=requested;
        } else {
            if(frame->read.transferred) {result=-5;break;}
            result=reist_x64_image_prepare_v2(prepared,file,size);
            if(result) break;
            now=transport.clock(transport.context);
            if(now<last || now>=deadline) {result=now<last?-84:-110;break;}
            if(c->owner!=owner || c->sequence!=sequence+call+1) {result=-116;break;}
            /* Single publication after full ELF validation and deadline admission. */
            file_copy(output,prepared,REIST_X64_PREPARED_V2_BYTES);
            file_clear(w,workspace_bytes);return 0;
        }
    }
    if(!result) result=-5;
    file_clear(w,workspace_bytes);return result;
}
int reist_x64_file_finish_v2(void *output,reist_file_image_workspace *w,
    reist_fs_client *c,const reist_fs_transport *t,const reist_file_capture_v1 *p) {
    if(!file_range(w,sizeof(*w)))return -22;
    return file_finish(output,w,sizeof(*w),w->file,&w->frame,w->prepared,c,t,p,
        1,REIST_FS_SESSION_REQUESTS,3000,REIST_X64_FILE_IMAGE_BYTES,3000);
}
int reist_x64_file_finish_v3(void *output,reist_file_image_workspace_v2 *w,
    reist_fs_client *c,const reist_fs_transport *t,const reist_file_capture_v2 *p) {
    if(!file_range(w,sizeof(*w)))return -22;
    return file_finish(output,w,sizeof(*w),w->file,&w->frame,w->prepared,c,t,p,
        2,REIST_WIDE_FS_REQUESTS,REIST_WIDE_FILE_MS,REIST_WIDE_FILE_BYTES,1000);
}
int reist_x64_file_stat_v2(reist_file_capture_v2 *out,reist_fs_client *c,
    const reist_fs_transport *t,const char *path,unsigned length,uint64_t deadline) {
    if(!length || length>=192)return -22;
    const void *objects[]={out,c,t,path};
    const size_t sizes[]={sizeof(*out),sizeof(*c),sizeof(*t),length};
    int result=file_objects(objects,sizes,4,2);if(result)return result;
    result=file_client(c,t);if(result)return result;
    if(file_path(path,length))return -22;
    if(c->sequence>=REIST_WIDE_FS_REQUESTS)return -11;
    reist_fs_transport transport=*t;
    uint64_t start=transport.clock(transport.context),owner=c->owner,sequence=c->sequence+1;
    if(deadline<=start)return -110;
    if(deadline-start>REIST_WIDE_FILE_MS)return -22;
    return file_stat_call(out,c,&transport,path,length,(unsigned)(deadline-start),start,owner,sequence,2,1000);
}
int reist_x64_file_prepare_v2(void *output,reist_file_image_workspace *w,
    reist_fs_client *c,const reist_fs_transport *t,const char *path,unsigned length,unsigned timeout) {
    if(!length || length>=192 || !timeout || timeout>3000)return -22;
    const void *objects[]={output,w,c,t,path};
    const size_t sizes[]={REIST_X64_PREPARED_V2_BYTES,sizeof(*w),sizeof(*c),sizeof(*t),length};
    int result=file_objects(objects,sizes,5,3);if(result)return result;
    result=file_client(c,t);if(result)return result;
    if(c->sequence || file_path(path,length))return -22;
    /* Preserve the fresh-client entrypoint and its scrub-on-admitted-failure
     * contract while sharing the actual new two-stage capture implementation. */
    reist_file_capture_v1 observation;
    reist_fs_transport transport=*t;uint64_t owner=c->owner,start=transport.clock(transport.context);
    if(start>UINT64_MAX-timeout)return -22;
    file_clear(w,sizeof(*w));
    result=file_stat_call(&observation,c,&transport,path,length,timeout,start,owner,1,1,3000);
    if(!result)result=reist_x64_file_finish_v2(output,w,c,&transport,&observation);
    file_clear(w,sizeof(*w));return result;
}
