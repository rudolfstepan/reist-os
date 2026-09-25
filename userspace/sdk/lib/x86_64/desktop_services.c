#include <reist/x86_64/desktop_services.h>
#include <reist/utf.h>

static void zero(void *p,size_t n) { unsigned char *d=p; for(size_t i=0;i<n;i++) d[i]=0; }
static void copy(void *p,const void *q,size_t n) { unsigned char *d=p; const unsigned char *s=q; for(size_t i=0;i<n;i++) d[i]=s[i]; }
static int empty(const void *p,size_t n) { const unsigned char *s=p; for(size_t i=0;i<n;i++) if(s[i]) return 0; return 1; }
static int string(const char *p,unsigned capacity) {
    unsigned n=0; while(n<capacity && p[n]) n++;
    return n && n<capacity && empty(p+n,capacity-n)?(int)n:-1;
}
static int path(const char *p) {
    int length=string(p,192); if(length<0 || p[0]!='/') return 0;
    size_t scalars; if(!reist_utf8_scan(p,(size_t)length,&scalars)) return 0;
    if(length==1) return 1;
    unsigned start=1;
    for(unsigned n=1;n<=(unsigned)length;n++) {
        if(p[n]=='\\' || (p[n] && (unsigned char)p[n]<32)) return 0;
        if(p[n]=='/' || !p[n]) {
            unsigned size=n-start;
            if(!size || (size==1 && p[start]=='.') ||
                (size==2 && p[start]=='.' && p[start+1]=='.')) return 0;
            start=n+1;
        }
    }
    return length;
}
static int equal(const char *a,const char *b) {
    for(unsigned n=0;n<192;n++) { if(a[n]!=b[n]) return 0; if(!a[n]) return 1; }
    return 0;
}
static int shape(const reist_desktop_broker *s) {
    if(!s || s->version!=1 || s->size!=sizeof(*s) || s->phase<1 || s->phase>3 ||
        s->head>=4 || s->count>4 || s->started>1 || s->rate_head>=16 ||
        s->rate_count>16 || s->config.manifest_count>64 || !s->config.manifest_count) return -84;
    return s->phase==1?0:-116;
}
int reist_desktop_broker_init(reist_desktop_broker *s,const reist_desktop_broker_config *c,uint64_t now) {
    if(!s || !c) return -22;
    if(s->phase==1) return -16;
    if(s->phase && s->phase!=2) return -117;
    if(!s->phase && !empty(s,sizeof(*s))) return -22;
    if(s->phase==2 && (s->version!=1 || s->size!=sizeof(*s))) return -84;
    if(!c->root || (uint32_t)c->root || !(c->root>>32) || c->root>>32>0x7ffffffe ||
        (uint32_t)c->desktop!=4 || !(c->desktop>>32) || c->desktop>>32>0x7ffffffe ||
        !c->epoch || c->epoch>INT64_MAX || !c->service_generation ||
        !c->manifest || !c->manifest_count || c->manifest_count>64 ||
        !c->clock_ms || !c->step || !c->abort || now>INT64_MAX-120000) return -22;
    if(c->epoch<=s->last_epoch) return -116;
    for(unsigned n=0;n<c->manifest_count;n++) {
        const reist_desktop_service_manifest *m=c->manifest+n;
        if(!path(m->path) || string(m->info.name,256)<0 || !m->rights || (m->rights&~3U) ||
            (m->info.type!=X86OS_FILE && m->info.type!=X86OS_DIRECTORY) ||
            m->info.size>1048576 || (m->info.type==X86OS_DIRECTORY && (m->info.size || m->rights!=1)) ||
            ((m->rights&2) && empty(m->digest,32))) return -22;
        for(unsigned i=0;i<n;i++) if(equal(m->path,c->manifest[i].path)) return -22;
    }
    /* Permit reinitialization from the retained config without zeroing its
     * source, and retain retired child generations across desktop epochs. */
    reist_desktop_broker_config saved=*c;
    uint64_t children[2]={s->last_children[0],s->last_children[1]};
    zero(s,sizeof(*s)); s->version=1; s->size=sizeof(*s); s->phase=1;
    s->config=saved; s->last_epoch=saved.epoch; s->previous=now;
    s->last_children[0]=children[0]; s->last_children[1]=children[1];
    return 0;
}
int reist_desktop_broker_revoke(reist_desktop_broker *s) {
    if(!s || s->version!=1 || s->size!=sizeof(*s)) return -22;
    if(s->phase==2) return 0;
    if(s->phase!=1) return -117;
    s->phase=3; /* fail closed before cleanup */
    if(s->config.abort(s->config.context)) return -117;
    zero(s->objects,sizeof(s->objects)); zero(s->children,sizeof(s->children));
    zero(s->queue,sizeof(s->queue)); zero(&s->reply,sizeof(s->reply));
    s->count=s->head=s->started=0; s->phase=2;
    return 0;
}
static int fail(reist_desktop_broker *s,int reason) {
    return reist_desktop_broker_revoke(s)?-117:reason;
}
static int clock_admit(reist_desktop_broker *s,uint64_t now) {
    int r=shape(s); if(r) return r;
    if(now<s->previous || now>INT64_MAX-120000) return fail(s,-84);
    return 0;
}
int reist_desktop_broker_adopt(reist_desktop_broker *s,const uint64_t owners[2],uint64_t now) {
    if(!owners)return -22;
    int r=clock_admit(s,now);if(r)return r;
    if(s->sequence || s->count || s->started || s->object_sequence ||
       s->children[0] || s->children[1])return -16;
    uint64_t values[2]={owners[0],owners[1]};
    for(unsigned n=0;n<2;n++) {
        uint64_t gen=values[n]>>32;
        if((uint32_t)values[n]!=6+n || gen<=s->config.desktop>>32 || gen>0x7ffffffe)return -22;
        if(gen<=s->last_children[n]>>32)return -116;
    }
    if(values[0]>>32==values[1]>>32)return -22;
    s->children[0]=s->last_children[0]=values[0];
    s->children[1]=s->last_children[1]=values[1];s->previous=now;
    return 0;
}
int reist_desktop_broker_replace(reist_desktop_broker *s,uint64_t old,uint64_t owner,uint64_t now) {
    int r=clock_admit(s,now);if(r)return r;
    unsigned slot=(uint32_t)old-6;
    if(slot>=2 || (uint32_t)owner!=6+slot || owner>>32>0x7ffffffe)return -22;
    if(!old || s->last_children[slot]!=old ||
       (s->children[slot] && s->children[slot]!=old) ||
       owner>>32<=old>>32 || owner>>32<=s->config.desktop>>32 ||
       owner>>32<=s->last_children[1-slot]>>32)return -116;
    for(unsigned n=0;n<s->count;n++)
        if(s->queue[(s->head+n)%4].object==old)return -16;
    s->children[slot]=s->last_children[slot]=owner;s->previous=now;
    return 0;
}
static int manifest_index(const reist_desktop_broker *s,const char *name) {
    for(unsigned n=0;n<s->config.manifest_count;n++) if(equal(name,s->config.manifest[n].path)) return (int)n;
    return -1;
}
static int object_index(const reist_desktop_broker *s,uint64_t id) {
    if(!id) return -1;
    for(unsigned n=0;n<8;n++) if(s->objects[n].id==id) return (int)n;
    return -1;
}
static int child_index(const reist_desktop_broker *s,uint64_t id) {
    for(unsigned n=0;n<2;n++) if(id && s->children[n]==id) return (int)n;
    return -1;
}
static int admit(reist_desktop_broker *s,const reist_desktop_service_frame *q,uint64_t now) {
    if(!q || q->version!=1 || q->size!=sizeof(*q) || q->flags || q->status ||
        !empty(q->reserved,sizeof(q->reserved))) return -22;
    if(q->root!=s->config.root || q->desktop!=s->config.desktop) return -13;
    if(q->epoch!=s->config.epoch) return -116;
    if(q->deadline_ms<=now || q->deadline_ms-now>1000) return -110;
    unsigned op=q->operation;
    if(op<1 || op>REIST_DESKTOP_CANCEL) return -95;
    if(op==REIST_DESKTOP_STAT || op==REIST_DESKTOP_OPEN || op==REIST_DESKTOP_READDIR || op==REIST_DESKTOP_LAUNCH) {
        if(q->object || !path(q->payload.command.path) || !empty(q->payload.command.reserved,704)) return -22;
        int index=manifest_index(s,q->payload.command.path); if(index<0) return -13;
        const reist_desktop_service_manifest *m=s->config.manifest+index;
        if(op==REIST_DESKTOP_LAUNCH) {
            if(!(m->rights&2)) return -13;
            if(q->offset || q->count || !q->argc || q->argc>8) return -22;
            for(unsigned n=0;n<8;n++) {
                if(n<q->argc) { if(string(q->payload.command.argv[n],128)<0) return -22; }
                else if(!empty(q->payload.command.argv[n],128)) return -22;
            }
            if(s->children[0] && s->children[1]) return -11;
        } else {
            if(!(m->rights&1)) return -13;
            if(q->argc || !empty(q->payload.command.argv,sizeof(q->payload.command.argv))) return -22;
            if(op==REIST_DESKTOP_READDIR) {
                if(m->info.type!=X86OS_DIRECTORY) return -20;
                if(!q->count || q->count>32 || q->offset>64) return -22;
            } else if(q->offset || q->count) return -22;
            if(op==REIST_DESKTOP_OPEN) {
                if(m->info.type!=X86OS_FILE) return -21;
                unsigned free_slot=0; for(unsigned n=0;n<8;n++) free_slot+=!s->objects[n].id;
                if(!free_slot) return -24;
                if(s->object_sequence>=UINT64_MAX/16) return -75;
            }
        }
    } else {
        if(q->argc || !empty(&q->payload,sizeof(q->payload))) return -22;
        if(op==REIST_DESKTOP_READ || op==REIST_DESKTOP_CLOSE) {
            int i=object_index(s,q->object); if(i<0) return -116;
            const reist_desktop_read_object *object=s->objects+i;
            if(object->service_generation!=s->config.service_generation) return -116;
            if(op==REIST_DESKTOP_READ) {
                if(now>=object->deadline) return -110;
                unsigned size=s->config.manifest[object->manifest_index].info.size;
                if(!q->count || q->count>REIST_DESKTOP_SERVICE_READ_BYTES || q->offset>size || q->count>size-q->offset) return -22;
            } else if(q->offset || q->count) return -22;
        } else {
            if(q->offset || q->count) return -22;
            if(child_index(s,q->object)<0) return -13;
        }
    }
    return 0;
}
int reist_desktop_broker_submit(reist_desktop_broker *s,const reist_desktop_service_frame *q,uint64_t now) {
    int r=clock_admit(s,now); if(r) return r;
    r=admit(s,q,now); if(r) return r;
    if(s->sequence==UINT64_MAX || q->sequence!=s->sequence+1) return -116;
    unsigned head=s->rate_head,count=s->rate_count;
    while(count && now-s->timestamps[head]>=1000) { head=(head+1)%16; count--; }
    if(s->count==4 || count==16) return -11;
    copy(s->queue+(s->head+s->count)%4,q,sizeof(*q));
    s->timestamps[(head+count)%16]=now; s->rate_head=head; s->rate_count=count+1;
    s->count++; s->sequence=q->sequence; s->previous=now;
    return 0;
}
static void reply_begin(reist_desktop_service_frame *out,const reist_desktop_service_frame *q) {
    zero(out,sizeof(*out));
    out->version=1; out->size=sizeof(*out); out->operation=q->operation;
    out->flags=REIST_DESKTOP_REPLY_ADMITTED;
    out->root=q->root; out->desktop=q->desktop; out->epoch=q->epoch;
    out->sequence=q->sequence; out->deadline_ms=q->deadline_ms; out->object=q->object; out->offset=q->offset;
}
static int reply_valid(const reist_desktop_service_frame *out,const reist_desktop_service_frame *q) {
    if(out->version!=1 || out->size!=sizeof(*out) || out->operation!=q->operation || out->flags!=REIST_DESKTOP_REPLY_ADMITTED ||
        out->root!=q->root || out->desktop!=q->desktop || out->epoch!=q->epoch ||
        out->sequence!=q->sequence || out->deadline_ms!=q->deadline_ms || out->argc ||
        out->status>0 || out->status< -4095 || !empty(out->reserved,sizeof(out->reserved))) return 0;
    if(out->status) return !out->count && out->object==q->object && out->offset==q->offset && empty(&out->payload,sizeof(out->payload));
    if(q->operation==REIST_DESKTOP_READ) return out->object==q->object && out->offset==q->offset &&
        out->count && out->count<=REIST_DESKTOP_SERVICE_READ_BYTES && out->count==q->count &&
        empty(out->payload.bytes+out->count,sizeof(out->payload)-out->count);
    if(out->count || !empty(&out->payload,sizeof(out->payload))) return 0;
    if(q->operation==REIST_DESKTOP_LAUNCH) return !out->offset && (uint32_t)out->object>=6 &&
        (uint32_t)out->object<=7 && out->object>>32 && out->object>>32<=0x7ffffffe;
    /* WAIT preserves the complete native32-bit exit status, including CPU256
     * and cancellation257. The SDK returns the reaped PID separately. */
    if(q->operation==REIST_DESKTOP_WAIT) return out->object==q->object;
    return out->object==q->object && out->offset==q->offset;
}
int reist_desktop_service_reject(const reist_desktop_service_frame *q,int error,reist_desktop_service_frame *out) {
    if(!q || !out || error>=0 || error< -4095) return -22;
    reply_begin(out,q); out->flags=0; out->status=error; return 0;
}
int reist_desktop_service_reply_valid(const reist_desktop_service_frame *q,const reist_desktop_service_frame *out) {
    if(!q || !out || out->flags>1 || out->version!=1 || out->size!=sizeof(*out) ||
        out->operation!=q->operation || out->root!=q->root || out->desktop!=q->desktop ||
        out->epoch!=q->epoch || out->sequence!=q->sequence || out->deadline_ms!=q->deadline_ms ||
        out->argc || !empty(out->reserved,sizeof(out->reserved)) || out->status>0 || out->status< -4095) return -71;
    if(out->status) return !out->count && out->object==q->object && out->offset==q->offset &&
        empty(&out->payload,sizeof(out->payload))?0:-71;
    if(out->flags!=1) return -71;
    if(q->operation==REIST_DESKTOP_STAT || q->operation==REIST_DESKTOP_OPEN) {
        const x86os_file_info_t *info=&out->payload.info;
        if(out->count!=sizeof(*info) || out->offset || string(info->name,256)<0 || info->size>1048576 ||
            (info->type!=X86OS_FILE && info->type!=X86OS_DIRECTORY) ||
            (info->type==X86OS_DIRECTORY && info->size) ||
            !empty(out->payload.bytes+sizeof(*info),sizeof(out->payload)-sizeof(*info))) return -71;
        if(q->operation==REIST_DESKTOP_STAT) return !out->object?0:-71;
        return info->type==X86OS_FILE && (out->object&15)>=1 && (out->object&15)<=8 && (out->object>>4)?0:-71;
    }
    if(q->operation==REIST_DESKTOP_READDIR) {
        if(out->object || out->offset!=q->offset || out->count>q->count || out->count>6 ||
            !empty(out->payload.bytes+out->count*sizeof(x86os_file_info_t),
                   sizeof(out->payload)-out->count*sizeof(x86os_file_info_t))) return -71;
        for(unsigned n=0;n<out->count;n++) {
            const x86os_file_info_t *info=out->payload.entries+n;
            if(string(info->name,256)<0 || info->size>1048576 ||
                (info->type!=X86OS_FILE && info->type!=X86OS_DIRECTORY) ||
                (info->type==X86OS_DIRECTORY && info->size)) return -71;
        }
        return 0;
    }
    return reply_valid(out,q)?0:-71;
}
static int immediate_child(const char *parent,const char *name) {
    unsigned n=0; while(parent[n]) { if(parent[n]!=name[n]) return 0; n++; }
    if(n>1) { if(name[n]!='/') return 0; n++; }
    if(!name[n]) return 0;
    for(;name[n];n++) if(name[n]=='/') return 0;
    return 1;
}
int reist_desktop_broker_step(reist_desktop_broker *s,reist_desktop_service_frame *out,uint64_t now) {
    if(!out) return -22;
    int r=clock_admit(s,now); if(r) return r;
    s->previous=now;
    if(!s->count) return 0;
    const reist_desktop_service_frame *q=s->queue+s->head;
    r=admit(s,q,now); if(r) return fail(s,r);
    reist_desktop_service_frame *reply=&s->reply;
    if(!s->started) { reply_begin(reply,q); s->started=1; }
    int index=-1;
    if(q->operation==REIST_DESKTOP_STAT || q->operation==REIST_DESKTOP_OPEN ||
        q->operation==REIST_DESKTOP_READDIR || q->operation==REIST_DESKTOP_LAUNCH)
        index=manifest_index(s,q->payload.command.path);
    if(q->operation==REIST_DESKTOP_STAT || q->operation==REIST_DESKTOP_OPEN) {
        copy(&reply->payload.info,&s->config.manifest[index].info,sizeof(reply->payload.info));
        reply->count=sizeof(reply->payload.info);
        if(q->operation==REIST_DESKTOP_OPEN) {
            unsigned n=0; while(n<8 && s->objects[n].id) n++;
            if(n==8) return fail(s,-84);
            uint64_t id=(++s->object_sequence)*16+n+1;
            s->objects[n]=(reist_desktop_read_object){id,now+120000,s->config.service_generation,(uint32_t)index};
            reply->object=id;
        }
    } else if(q->operation==REIST_DESKTOP_CLOSE) {
        zero(s->objects+object_index(s,q->object),sizeof(s->objects[0]));
    } else if(q->operation==REIST_DESKTOP_READDIR) {
        unsigned skipped=0;
        for(unsigned n=0;n<s->config.manifest_count && reply->count<q->count && reply->count<6;n++) {
            const reist_desktop_service_manifest *m=s->config.manifest+n;
            if(!immediate_child(q->payload.command.path,m->path)) continue;
            if(skipped++<q->offset) continue;
            copy(reply->payload.entries+reply->count++,&m->info,sizeof(m->info));
        }
    } else {
        if(q->operation==REIST_DESKTOP_READ) index=(int)s->objects[object_index(s,q->object)].manifest_index;
        r=s->config.step(s->config.context,q,index<0?0:s->config.manifest+index,reply);
        if(r==1) return 1;
        if(r) return fail(s,r>=-4095 && r<0?r:-71);
        if(!reply_valid(reply,q)) return fail(s,-71);
        if(!reply->status && q->operation==REIST_DESKTOP_LAUNCH) {
            unsigned slot=(unsigned)reply->object-6;
            if(s->children[slot] || reply->object>>32<=s->last_children[slot]>>32) return fail(s,-71);
            s->children[slot]=s->last_children[slot]=reply->object;
        } else if(!reply->status && q->operation==REIST_DESKTOP_WAIT) s->children[child_index(s,q->object)]=0;
    }
    uint64_t finished=0;
    r=s->config.clock_ms(s->config.context,&finished);
    if(r || finished<now || finished<s->previous) return fail(s,-84);
    if(finished>=q->deadline_ms) return fail(s,-110);
    s->previous=finished;
    copy(out,reply,sizeof(*out)); zero(s->queue+s->head,sizeof(*q)); zero(reply,sizeof(*reply));
    s->head=(s->head+1)%4; s->count--; s->started=0;
    return 2;
}
