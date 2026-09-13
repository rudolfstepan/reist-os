#include <reist/x86_64/filesystem.h>
#include "../include/reist/vfs_shadow_ext2.h"

typedef uint64_t fs_word __attribute__((may_alias,aligned(1)));
static void fs_zero(void *p,unsigned n) {
    unsigned char *b=p;
    while(n>=8) { *(volatile fs_word *)b=0; b+=8; n-=8; }
    while(n--) *b++=0;
}
static void fs_copy(void *p,const void *q,unsigned n) {
    unsigned char *a=p; const unsigned char *b=q;
    while(n>=8) { *(volatile fs_word *)a=*(const fs_word *)b; a+=8; b+=8; n-=8; }
    while(n--) *a++=*b++;
}
static int fs_empty(const void *p,unsigned n) {
    const unsigned char *b=p; while(n--) if(*b++) return 0; return 1;
}
static int fs_equal(const void *p,const void *q,unsigned n) {
    const unsigned char *a=p,*b=q; while(n--) if(*a++!=*b++) return 0; return 1;
}
static int fs_owner(uint64_t owner,unsigned slot) {
    return (uint32_t)owner==slot && owner>>32 && owner<=INT64_MAX;
}
static int fs_path(const char *p,unsigned n) {
    if(!p || !n || n>=192 || p[0]!='/') return 0;
    for(unsigned i=0;i<n;i++) if(!p[i]) return 0;
    return 1;
}
int reist_fs_request_init(reist_fs_frame *f,unsigned op,const char *path,unsigned n,
                          uint32_t position,uint32_t requested) {
    if(!f || !fs_path(path,n) || op<5 || op>7 ||
       (op==6?(!requested || requested>256):(requested || (op==5 && position)))) return -22;
    reist_fs_frame next; fs_zero(&next,sizeof(next));
    next.stat.version=1; next.stat.struct_size=512; next.stat.operation=op; next.stat.path_length=n;
    if(op==6) {
        next.read.offset=position; next.read.requested=requested; fs_copy(next.read.path,path,n);
    } else if(op==7) { next.directory.index=position; fs_copy(next.directory.path,path,n); }
    else fs_copy(next.stat.path,path,n);
    fs_copy(f,&next,512); return 0;
}
/* Canonical reconstruction checks all padding/output-only fields at once. */
static int fs_request(const reist_fs_frame *f) {
    unsigned op=f->stat.operation,n=f->stat.path_length;
    const char *path=op==6?f->read.path:op==7?f->directory.path:f->stat.path;
    reist_fs_frame canonical;
    if(reist_fs_request_init(&canonical,op,path,n,op==6?f->read.offset:op==7?f->directory.index:0,
                             op==6?f->read.requested:0)) return 0;
    return fs_equal(&canonical,f,512);
}
static int fs_error(int e) {
    return e==-2 || e==-5 || e==-11 || e==-13 || e==-19 || e==-20 || e==-21 ||
        e==-22 || e==-36 || e==-40 || e==-71 || e==-84 || e==-110 || e==-116;
}
static int fs_application_error(int e) { return e==-2 || e==-20 || e==-21 || e==-36 || e==-40; }
static int fs_deadline(reist_fs_server *s) {
    if(s->failed || s->ready==0) return -116;
    uint64_t now=s->transport.clock(s->transport.context);
    if(now<s->last_clock) return -84;
    s->last_clock=now;
    return now>=s->profile.deadline_ms || now>=s->request_deadline?-110:0;
}
static void fs_poison(reist_fs_server *s) {
    s->failed=1; s->ready=0; s->used=0;
    fs_zero(s->lba,sizeof(s->lba)); fs_zero(s->data,sizeof(s->data));
}
int reist_fs_server_fence(reist_fs_server *s) {
    if(!s) return -22;
    if(s->busy) return -16;
    fs_poison(s); return 0;
}
static int fs_drive(void *v,uint32_t resource,x86os_drive_info_t *info) {
    reist_fs_server *s=v;
    int result=fs_deadline(s);
    if(result) { fs_poison(s); return result; }
    fs_zero(info,sizeof(*info));
    if(resource) return 0;
    info->type=X86OS_DRIVE_ATA; info->sectors=s->profile.sectors;
    info->name[0]='n'; info->mount_point[0]='/'; return 1;
}
static int fs_sector(void *v,uint32_t resource,uint32_t lba,uint8_t *data) {
    reist_fs_server *s=v;
    int result=fs_deadline(s);
    if(result) { fs_poison(s); return result; }
    if(resource || lba>=s->profile.sectors || s->used>16) { fs_poison(s); return -5; }
    for(unsigned n=0;n<s->used;n++) if(s->lba[n]==lba) {
        fs_copy(data,s->data[n],512); return 0;
    }
    if(s->used==16) { fs_poison(s); return -11; }
    uint64_t remaining=s->request_deadline-s->last_clock;
    if(remaining>s->profile.deadline_ms-s->last_clock) remaining=s->profile.deadline_ms-s->last_clock;
    unsigned index=s->used;
    result=reist_block_read(&s->block,&s->transport,lba,s->data[index],remaining>1000?1000:(unsigned)remaining);
    if(!result) result=fs_deadline(s);
    if(result) { fs_poison(s); return result; }
    s->lba[index]=lba; s->used=index+1;
    fs_copy(data,s->data[index],512); return 0;
}
int reist_fs_server_init(reist_fs_server *s,const reist_fs_profile_v1 *p,const reist_block_transport *t) {
    if(!s || !p || !t || !t->clock || !t->send || !t->receive || p->version!=1 || p->size!=40 ||
       (p->filesystem!=REIST_FS_FAT && p->filesystem!=REIST_FS_EXT2) || !p->sectors ||
       p->sectors>0x10000000U || !fs_owner(p->owner,3) || !fs_owner(p->block_owner,2) ||
       p->owner<=s->profile.owner || p->block_owner<=s->profile.block_owner) return -22;
    if(s->busy) return -16;
    reist_fs_profile_v1 profile=*p; reist_block_transport transport=*t;
    uint64_t now=transport.clock(transport.context);
    if(profile.deadline_ms<=now || profile.deadline_ms-now>3000) return -22;
    fs_zero(s,sizeof(*s)); s->profile=profile; s->transport=transport;
    s->last_clock=now; s->request_deadline=profile.deadline_ms; s->next_sequence=1; s->ready=1; s->busy=1;
    int result=reist_block_client_bind(&s->block,profile.block_owner);
    reist_vfs_shadow_io_t io={s,fs_drive,fs_sector}; x86os_file_info_t info;
    if(!result) result=profile.filesystem==REIST_FS_EXT2?
        reist_vfs_shadow_ext2_stat(&io,"/",1,&info):reist_vfs_shadow_fat_stat(&io,"/",1,&info);
    if(!result && info.type!=X86OS_DIRECTORY) result=-5;
    if(!result) result=fs_deadline(s);
    s->busy=0;
    if(result) fs_poison(s); else s->ready=2;
    return result;
}
int reist_fs_dispatch(reist_fs_server *s,const x86os_ipc_bulk_message_t *q,x86os_ipc_bulk_message_t *reply) {
    if(!s || !q || !reply || q==reply || !s->transport.clock) return -22;
    if(s->busy) return -16;
    reist_fs_header h; reist_fs_frame frame;
    fs_copy(&h,q->payload,64); fs_copy(&frame,q->payload+64,512);
    /* No partially initialized reply on local-pointer/reentry admission errors. */
    fs_zero(reply,sizeof(*reply)); reply->version=2; reply->struct_size=sizeof(*reply); reply->length=64;
    reist_fs_header r={1,64,h.operation,1,s->profile.owner,h.sequence,h.deadline_ms,0,0,-22,0};
    int result=-22;
    if(s->ready!=2 || s->failed) { result=-116; goto done; }
    if(s->requests>=8) { result=-11; goto done; }
    s->requests++;
    if(q->version!=2 || q->struct_size!=sizeof(*q) || q->length!=576 ||
       !fs_empty(q->payload+576,1472) || h.version!=1 || h.size!=64 || h.flags || h.length!=512 ||
       h.status || h.reserved || h.reserved_tail || h.operation!=frame.stat.operation || !fs_request(&frame)) goto done;
    if(h.owner!=s->profile.owner) { result=-13; goto done; }
    if(!h.sequence || h.sequence!=s->next_sequence || h.sequence==UINT64_MAX) { result=-116; goto done; }
    result=fs_deadline(s); if(result) goto done;
    if(h.deadline_ms<=s->last_clock) { result=-110; goto done; }
    if(h.deadline_ms-s->last_clock>3000) { result=-22; goto done; }
    s->request_deadline=h.deadline_ms<s->profile.deadline_ms?h.deadline_ms:s->profile.deadline_ms;
    s->next_sequence++; s->busy=1;
    reist_vfs_shadow_io_t io={s,fs_drive,fs_sector};
    int ext=s->profile.filesystem==REIST_FS_EXT2;
    if(h.operation==5) result=ext?reist_vfs_shadow_ext2_stat(&io,frame.stat.path,frame.stat.path_length,&frame.stat.info):
        reist_vfs_shadow_fat_stat(&io,frame.stat.path,frame.stat.path_length,&frame.stat.info);
    else if(h.operation==6) result=ext?reist_vfs_shadow_ext2_read(&io,frame.read.path,frame.read.path_length,frame.read.offset,frame.read.data,frame.read.requested,&frame.read.transferred):
        reist_vfs_shadow_fat_read(&io,frame.read.path,frame.read.path_length,frame.read.offset,frame.read.data,frame.read.requested,&frame.read.transferred);
    else result=ext?reist_vfs_shadow_ext2_readdir(&io,frame.directory.path,frame.directory.path_length,frame.directory.index,&frame.directory.info):
        reist_vfs_shadow_fat_readdir(&io,frame.directory.path,frame.directory.path_length,frame.directory.index,&frame.directory.info);
    s->busy=0;
    int end=fs_deadline(s); if(end) result=end;
    s->request_deadline=s->profile.deadline_ms;
    if(result<0) goto done;
    if(result>1 || (result==1 && h.operation!=7)) { result=-5; goto done; }
    frame.stat.result=result; r.length=512; reply->length=576;
    fs_copy(reply->payload+64,&frame,512);
done:
    if(result<0) {
        if(!fs_error(result)) result=-5;
        if(!fs_application_error(result)) fs_poison(s);
    }
    r.status=result; fs_copy(reply->payload,&r,64); return result;
}
int reist_fs_client_bind(reist_fs_client *c,uint64_t owner) {
    if(!c || !fs_owner(owner,3) || owner<=c->owner) return -22;
    if(c->busy) return -16;
    c->owner=owner; c->sequence=0; c->failed=0; return 0;
}
static int fs_client_end(reist_fs_client *c,int error) {
    c->busy=0; if(error<0 && !fs_application_error(error)) c->failed=1; return error;
}
static int fs_transport_error(reist_fs_client *c,int error) {
    /* Only a fully matched FS reply can report an application errno or EOF.
     * Any failed transport consumes this generation, even ENOENT or a bogus
     * positive callback result; never publish that as successful readdir. */
    c->busy=0; c->failed=1; return error<0?error:-71;
}
static int fs_info(const x86os_file_info_t *i) {
    unsigned n=0; while(n<sizeof(i->name) && i->name[n]) n++;
    return n && n<sizeof(i->name) && fs_empty(i->name+n,sizeof(i->name)-n) &&
        (i->type==X86OS_FILE || i->type==X86OS_DIRECTORY || i->type==X86OS_SYMLINK);
}
int reist_fs_call(reist_fs_client *c,const reist_fs_transport *t,reist_fs_frame *f,unsigned timeout) {
    if(!c || !t || !t->clock || !t->send || !t->receive || !f || !fs_owner(c->owner,3) ||
       !timeout || timeout>3000 || !fs_request(f)) return -22;
    if(c->busy) return -16;
    if(c->failed || c->sequence==UINT64_MAX) return -116;
    uint64_t now=t->clock(t->context);
    if(now>UINT64_MAX-timeout) return -22;
    reist_fs_header h={1,64,f->stat.operation,0,c->owner,++c->sequence,now+timeout,0,512,0,0};
    x86os_ipc_bulk_message_t message; fs_zero(&message,sizeof(message));
    message.version=2; message.struct_size=sizeof(message); message.length=576;
    fs_copy(message.payload,&h,64); fs_copy(message.payload+64,f,512); c->busy=1;
    uint64_t next=t->clock(t->context);
    if(next<now || next>=h.deadline_ms) return fs_client_end(c,next<now?-84:-110);
    int result=t->send(t->context,&message,(unsigned)(h.deadline_ms-next));
    if(result) return fs_transport_error(c,result);
    now=t->clock(t->context);
    if(now<next || now>=h.deadline_ms) return fs_client_end(c,now<next?-84:-110);
    fs_zero(&message,sizeof(message)); message.version=2; message.struct_size=sizeof(message); message.length=2048;
    result=t->receive(t->context,&message,(unsigned)(h.deadline_ms-now));
    if(result) return fs_transport_error(c,result);
    next=t->clock(t->context);
    if(next<now || next>=h.deadline_ms) return fs_client_end(c,next<now?-84:-110);
    if(message.version!=2 || message.struct_size!=sizeof(message) || (message.length!=64 && message.length!=576) ||
       !fs_empty(message.payload+message.length,2048-message.length)) return fs_client_end(c,-71);
    reist_fs_header r; reist_fs_frame answer,canonical;
    fs_copy(&r,message.payload,64);
    if(r.version!=1 || r.size!=64 || r.operation!=h.operation || r.flags!=1 || r.owner!=h.owner ||
       r.sequence!=h.sequence || r.deadline_ms!=h.deadline_ms || r.reserved || r.reserved_tail ||
       (r.status<0?(!fs_error(r.status) || r.length || message.length!=64):
         (r.status>1 || (r.status==1 && h.operation!=7) || r.length!=512 || message.length!=576))) return fs_client_end(c,-71);
    if(r.status<0) return fs_client_end(c,r.status);
    fs_copy(&answer,message.payload+64,512); fs_copy(&canonical,f,512);
    canonical.stat.result=r.status;
    if(h.operation==6) {
        if(answer.read.transferred>f->read.requested || !fs_empty(answer.read.data+answer.read.transferred,256-answer.read.transferred)) return fs_client_end(c,-71);
        canonical.read.transferred=answer.read.transferred;
        fs_copy(canonical.read.data,answer.read.data,256);
    } else {
        x86os_file_info_t *i=h.operation==5?&answer.stat.info:&answer.directory.info;
        if(r.status==1?!fs_empty(i,sizeof(*i)):!fs_info(i)) return fs_client_end(c,-71);
        fs_copy(h.operation==5?&canonical.stat.info:&canonical.directory.info,i,sizeof(*i));
    }
    if(!fs_equal(&canonical,&answer,512)) return fs_client_end(c,-71);
    fs_copy(f,&answer,512); return fs_client_end(c,r.status);
}
