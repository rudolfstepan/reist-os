/* Private root-only backend quanta, included by the full desktop supervisor.
 * Native WAIT consumes a receipt. Keep its exact owner/reason/status until
 * both service WAIT and supervisor retirement have observed it. */
#include <reist/x86_64/desktop_services.h>
#include <reist/x86_64/filesystem.h>
typedef struct {
    uint64_t owner,receipt;
    unsigned reaped,delivered;
} full_desktop_child;
typedef struct {
    reist_desktop_broker broker;
    full_desktop_child children[2];
    uint64_t service_generation,read_sequence,last_io_ms;
    unsigned read_used;
    unsigned fs_phase;
    uint64_t fs_clock;
    reist_fs_header fs_header;
    reist_fs_frame fs_request;
    reist_desktop_service_frame pending_reply;
    reist_desktop_service_manifest *manifest;
} full_desktop_backend;
_Static_assert(sizeof(full_desktop_backend)<16384,"fixed supervisor desktop backend");

#ifdef REIST_NATIVE_FULL_DESKTOP
static int full_fs_send(const x86os_ipc_bulk_message_t *q) {
    return (int)SESSION_S3(IPC_SEND_TIMEOUT,session_service.filesystem_endpoint,q,0);
}
static int full_fs_receive(x86os_ipc_bulk_message_t *q) {
    return (int)SESSION_S3(IPC_RECEIVE_TIMEOUT,session_service.filesystem_endpoint,q,0);
}
#endif
static int full_equal(const void *a,const void *b,unsigned bytes) {
    const unsigned char *x=a,*y=b;
    for(unsigned n=0;n<bytes;n++)if(x[n]!=y[n])return 0;
    return 1;
}
static int full_empty(const void *p,unsigned bytes) {
    const unsigned char *x=p;
    for(unsigned n=0;n<bytes;n++)if(x[n])return 0;
    return 1;
}
static int full_fs_fail(full_desktop_backend *s,int error) {
    s->fs_phase=3;session_fs.busy=0;session_fs.failed=1;
    return error<0 && error>=-4095?error:-71;
}
static int full_fs_begin(full_desktop_backend *s,const reist_fs_frame *q,uint64_t end) {
    uint64_t now=session_now();
    if(s->fs_phase || session_fs.busy || session_fs.failed ||
       session_fs.owner!=s->service_generation)return -116;
    if(end<=now || end-now>1000)return -110;
    if(session_fs.sequence==UINT64_MAX)return -75;
    s->fs_request=*q;s->fs_clock=now;
    s->fs_header=(reist_fs_header){1,64,q->stat.operation,0,session_fs.owner,
        ++session_fs.sequence,end,0,512,0,0};
    session_fs.busy=1;s->fs_phase=1;return 0;
}
/* One nonblocking transport operation per call. A pending response never
 * prevents root control/health handling and never renews the original end. */
static int full_fs_progress(full_desktop_backend *s,reist_fs_frame *out) {
    if(s->fs_phase<1 || s->fs_phase>2 || !session_fs.busy || session_fs.failed ||
       session_fs.owner!=s->service_generation)return full_fs_fail(s,-116);
    uint64_t now=session_now();
    if(now<s->fs_clock)return full_fs_fail(s,-84);
    s->fs_clock=now;
    if(now>=s->fs_header.deadline_ms)return full_fs_fail(s,-110);
    x86os_ipc_bulk_message_t wire={0};wire.version=2;wire.struct_size=2060;
    int r;
    if(s->fs_phase==1) {
        wire.length=576;session_bytes(wire.payload,&s->fs_header,64);
        session_bytes(wire.payload+64,&s->fs_request,512);
        r=full_fs_send(&wire);
        if(r==-11)return 1;
        if(r)return full_fs_fail(s,r);
        s->fs_phase=2;return 1;
    }
    wire.length=2048;r=full_fs_receive(&wire);
    if(r==-11)return 1;
    if(r)return full_fs_fail(s,r);
    now=session_now();
    if(now<s->fs_clock)return full_fs_fail(s,-84);
    if(now>=s->fs_header.deadline_ms)return full_fs_fail(s,-110);
    if(wire.version!=2 || wire.struct_size!=2060 || (wire.length!=64 && wire.length!=576) ||
       !full_empty(wire.payload+wire.length,2048-wire.length))return full_fs_fail(s,-71);
    reist_fs_header h,expected=s->fs_header;session_bytes(&h,wire.payload,64);
    expected.flags=1;expected.status=h.status;expected.length=h.status<0?0:512;
    if(!full_equal(&h,&expected,64) || h.status>0 ||
       wire.length!=(h.status<0?64U:576U))return full_fs_fail(s,-71);
    if(h.status<0) {
        switch(h.status) {
        case -2:case -5:case -11:case -13:case -19:case -20:case -21:
        case -22:case -36:case -40:case -71:case -84:case -110:case -116:
            return full_fs_fail(s,h.status);
        default:return full_fs_fail(s,-71);
        }
    }
    reist_fs_frame answer,canonical=s->fs_request;
    session_bytes(&answer,wire.payload+64,512);
    if(h.operation==5) {
        x86os_file_info_t *i=&answer.stat.info;unsigned n=0;
        while(n<sizeof(i->name) && i->name[n])n++;
        if(!n || n==sizeof(i->name) || !full_empty(i->name+n,sizeof(i->name)-n) ||
           (i->type!=X86OS_FILE && i->type!=X86OS_DIRECTORY && i->type!=X86OS_SYMLINK))return full_fs_fail(s,-71);
        canonical.stat.info=*i;
    } else if(h.operation==6) {
        unsigned n=answer.read.transferred;
        if(n>s->fs_request.read.requested || !full_empty(answer.read.data+n,256-n))return full_fs_fail(s,-71);
        canonical.read.transferred=n;session_bytes(canonical.read.data,answer.read.data,256);
    } else return full_fs_fail(s,-71);
    if(session_fs.owner!=s->service_generation)return full_fs_fail(s,-116);
    if(!full_equal(&canonical,&answer,512))return full_fs_fail(s,-71);
    *out=answer;session_fs.busy=0;s->fs_phase=0;s->last_io_ms=now;
    return 0;
}

static int full_desktop_observe(full_desktop_child *child) {
    if(!child || (uint32_t)child->owner<6 || (uint32_t)child->owner>7 ||
       !(child->owner>>32) || child->owner>>32>0x7ffffffe)return -116;
    if(child->reaped)return 1;
    x86os_process_identity_t identity;
    int r=x86os_process_identity_of((int)(child->owner>>32),&identity);
    if(!r) {
        if(identity.version!=1 || identity.struct_size!=16 ||
           identity.pid!=(int)(child->owner>>32) || identity.generation!=child->owner>>32)return -71;
        return 0;
    }
    if(r!=-3)return r;
    /* Root's existing PROCESS_IDENTITY114 proves the direct child is no
     * longer live. TASK_CONTROL WAIT requires1..1000ms, even for a receipt. */
    int64_t receipt=service_task(0,2,child->owner,1);
    if(receipt<0)return receipt>=-4095?(int)receipt:-71;
    if((uint64_t)receipt>>32>3)return -71;
    child->receipt=(uint64_t)receipt;child->reaped=1;return 1;
}
static int full_desktop_child_step(full_desktop_backend *s,
        const reist_desktop_service_frame *q,reist_desktop_service_frame *out) {
    if(!s || !q || !out)return -22;
    unsigned slot=(uint32_t)q->object-6;
    if(slot>=2 || s->children[slot].owner!=q->object)return -116;
    full_desktop_child *child=&s->children[slot];
    if(child->delivered){out->status=-3;return 0;}
    if(q->operation!=REIST_DESKTOP_IDENTITY && q->operation!=REIST_DESKTOP_WAIT &&
       q->operation!=REIST_DESKTOP_CANCEL)return -22;
    int r=full_desktop_observe(child);if(r<0)return r;
    if(q->operation==REIST_DESKTOP_IDENTITY)out->status=r?-3:0;
    else if(q->operation==REIST_DESKTOP_WAIT) {
        if(!r)out->status=-11;
        else {out->offset=(uint32_t)child->receipt;child->delivered=1;}
    } else if(!r) {
        int64_t cancelled=service_task(0,3,child->owner,0);
        if(cancelled)return cancelled<0 && cancelled>=-4095?(int)cancelled:-71;
        /* CANCEL success is not a reap receipt; WAIT still has to prove it. */
    }
    return 0;
}
static int full_desktop_read_step(full_desktop_backend *s,
        const reist_desktop_service_frame *q,const reist_desktop_service_manifest *m,
        reist_desktop_service_frame *out) {
    if(!s || !q || !m || !out || q->operation!=REIST_DESKTOP_READ ||
       !q->sequence || !q->count || q->count>1792 || m->info.type!=X86OS_FILE ||
       !(m->rights&REIST_DESKTOP_MANIFEST_READ) || q->offset>m->info.size ||
       q->count>m->info.size-q->offset)return -22;
    if(!s->service_generation || s->service_generation!=session_fs.owner ||
       session_service.phase!=REIST_SESSION_HEALTHY || session_fs.failed)return -116;
    if(s->read_sequence && s->read_sequence!=q->sequence)return -84;
    if(s->read_used>=q->count || session_operation_deadline)return -84;
    unsigned length=0;while(length<192 && m->path[length])length++;
    if(!length || length==192)return -22;
    uint64_t now=session_now();if(now>=q->deadline_ms)return -110;
    unsigned count=q->count-s->read_used;if(count>256)count=256;
    reist_fs_frame frame;
    if(s->fs_phase && s->fs_header.operation==5)return 1;
    if(!s->fs_phase) {
        int r=reist_fs_request_init(&frame,6,m->path,length,q->offset+s->read_used,count);
        if(r)return r;
        s->read_sequence=q->sequence;
        r=full_fs_begin(s,&frame,q->deadline_ms);return r?r:1;
    }
    if(s->fs_header.operation!=6)return -84;
    int r=full_fs_progress(s,&frame);
    if(r)return r;
    uint64_t finished=session_now();
    if(finished<now)return -84;
    if(finished>=q->deadline_ms)return -110;
    if(session_fs.owner!=s->service_generation || session_fs.failed)return -116;
    if(frame.read.transferred!=count)return -84;
    s->last_io_ms=finished;
    session_bytes(out->payload.bytes+s->read_used,frame.read.data,count);
    s->read_used+=count;
    if(s->read_used<q->count)return 1;
    out->count=s->read_used;s->read_used=0;s->read_sequence=0;return 0;
}

static int full_desktop_service_poll(full_desktop_backend *s) {
    if(!s || !s->service_generation || s->service_generation!=session_fs.owner ||
       session_service.phase!=REIST_SESSION_HEALTHY || session_fs.failed)return -116;
    uint64_t now=session_now();
    if(now<s->last_io_ms)return -84;
    if(s->fs_phase && s->fs_header.operation==6)return 0;
    reist_fs_frame frame;
    if(s->fs_phase) {
        int r=full_fs_progress(s,&frame);
        if(r)return r<0?r:0;
        return frame.stat.info.type==X86OS_DIRECTORY?0:full_fs_fail(s,-84);
    }
    if(s->read_sequence || now-s->last_io_ms<250)return 0;
    if(session_operation_deadline || now>INT64_MAX-1000)return -84;
    int r=reist_fs_request_init(&frame,5,"/",1,0,0);if(r)return r;
    return full_fs_begin(s,&frame,now+1000);
}

#ifdef REIST_NATIVE_FULL_DESKTOP
#include "full_desktop_manifest.h"
static full_desktop_backend *full_backend;
#define full_reply (full_backend->pending_reply)
static unsigned full_reply_pending,full_retire_degraded,full_start_stage;
static int full_graphical_clock(void *unused,uint64_t *out) {
    (void)unused;*out=session_now();return 0;
}
static int full_graphical_abort(void *unused) {
    (void)unused;full_reply_pending=0;session_zero(&full_reply,sizeof(full_reply));
    int r=graphical_retire(full_retire_degraded);if(r)return r;
    /* Cancel/fence/reap storage before abandoning a pending receive. Retain
     * the old client owner so only a strictly newer generation can bind. */
    r=session_retire();if(r)return r;
    session_fs.busy=0;session_fs.failed=1;full_backend->fs_phase=3;
    return 0;
}
static int full_graphical_step(void *context,const reist_desktop_service_frame *q,
        const reist_desktop_service_manifest *m,reist_desktop_service_frame *out) {
    full_desktop_backend *s=context;
    if(q->operation==REIST_DESKTOP_READ)return full_desktop_read_step(s,q,m,out);
    if(q->operation==REIST_DESKTOP_LAUNCH) {out->status=-95;return 0;}
    return full_desktop_child_step(s,q,out);
}
static int full_graphical_storage_start(void) {
    /* Initialize storage before publishing GUI children. All dependencies
     * share the original graphical startup deadline. */
    int r=session_retire();if(r)return r;
    uint64_t now=session_now(),end=graphical.start_end;
    if(end<=now)return -110;
    if(end-now>1000)end=now+1000;
    return session_ensure(end,0);
}
static int full_graphical_open(void) {
    if(!full_backend) {
        int64_t allocation=SESSION_S1(MALLOC,sizeof(*full_backend));
        if(allocation<=0)return -12;
        full_backend=(void *)(uintptr_t)allocation;session_zero(full_backend,sizeof(*full_backend));
    }
    if(session_service.phase!=REIST_SESSION_HEALTHY || session_fs.failed)return -116;
    if(!full_backend->manifest) {
        enum { count=sizeof(full_desktop_manifest)/sizeof(full_desktop_manifest[0]) };
        _Static_assert(count>0 && count<=64,"bounded immutable desktop manifest");
        int64_t allocation=SESSION_S1(MALLOC,count*sizeof(reist_desktop_service_manifest));
        if(allocation<=0)return -12;
        full_backend->manifest=(void *)(uintptr_t)allocation;
        session_zero(full_backend->manifest,count*sizeof(reist_desktop_service_manifest));
        for(unsigned n=0;n<count;n++) {
            reist_desktop_service_manifest *m=full_backend->manifest+n;
            const full_desktop_manifest_entry *source=full_desktop_manifest+n;
            unsigned length=0;while(length<192 && source->path[length])length++;
            if(!length || length==192)session_stop(-84);
            session_bytes(m->path,source->path,length);
            session_bytes(m->info.name,source->path+(length>1),length-(length>1));
            m->info.size=source->bytes;m->info.type=length==1?X86OS_DIRECTORY:X86OS_FILE;
            m->rights=source->rights;session_bytes(m->digest,source->digest,32);
        }
    }
    reist_desktop_broker_config cfg={graphical.root,graphical.roles[0].owner,
        graphical.epoch,session_fs.owner,full_backend->manifest,
        sizeof(full_desktop_manifest)/sizeof(full_desktop_manifest[0]),full_backend,
        full_graphical_clock,full_graphical_step,full_graphical_abort};
    int r=reist_desktop_broker_init(&full_backend->broker,&cfg,session_now());if(r)return r;
    full_backend->service_generation=session_fs.owner;
    full_backend->last_io_ms=session_now();
    full_backend->read_sequence=0;full_backend->read_used=0;
    uint64_t owners[2]={graphical.roles[2].owner,graphical.roles[3].owner};
    for(unsigned n=0;n<2;n++)full_backend->children[n]=(full_desktop_child){owners[n],0,0,0};
    return reist_desktop_broker_adopt(&full_backend->broker,owners,session_now());
}
static int full_graphical_receive(reist_graphical_control *control) {
    if(full_backend && full_backend->broker.phase==1) {
        int status=full_desktop_service_poll(full_backend);
        if(status){full_start_stage=0x100;return status;}
    }
    if(full_reply_pending) {
        if(session_now()>=full_reply.deadline_ms)return -110;
        x86os_ipc_bulk_message_t reply;session_zero(&reply,sizeof(reply));
        reply.version=2;reply.struct_size=2060;reply.length=2048;
        session_bytes(reply.payload,&full_reply,sizeof(full_reply));
        int r=(int)SESSION_S3(IPC_SEND_TIMEOUT,graphical_control,&reply,0);
        if(r && r!=-11)return r;
        if(!r){full_reply_pending=0;session_zero(&full_reply,sizeof(full_reply));}
    }
    x86os_ipc_bulk_message_t wire;session_zero(&wire,sizeof(wire));
    wire.version=2;wire.struct_size=2060;wire.length=2048;
    int r=(int)SESSION_S3(IPC_RECEIVE_TIMEOUT,graphical_control,&wire,0);
    if(!r) {
        if(wire.version==1 && wire.struct_size==140 && wire.length==64) {
            for(unsigned n=64;n<2048;n++)if(wire.payload[n])return -71;
            session_bytes(control,wire.payload,64);
            if(control->version!=1 || control->size!=64 || control->epoch!=graphical.epoch ||
               control->role>=4 || control->reserved)return -71;
            return 0;
        }
        if(wire.version!=2 || wire.struct_size!=2060 || wire.length!=2048 ||
           !full_backend || full_reply_pending)return -71;
        reist_desktop_service_frame q;session_bytes(&q,wire.payload,sizeof(q));
        r=reist_desktop_broker_submit(&full_backend->broker,&q,session_now());
        if(r) {
            if(reist_desktop_service_reject(&q,r,&full_reply))return -71;
            full_reply_pending=1;
        }
        return -11;
    }
    if(r!=-11)return r;
    if(full_backend && full_backend->broker.phase==1 && !full_reply_pending) {
        r=reist_desktop_broker_step(&full_backend->broker,&full_reply,session_now());
        if(r<0)return r;
        if(r==2)full_reply_pending=1;
    }
    return -11;
}
static int64_t full_graphical_reap(unsigned role) {
    uint64_t owner=graphical.roles[role].owner;
    full_desktop_child *child=full_backend && role>=2?&full_backend->children[role-2]:0;
    if(child && child->owner==owner && child->reaped)return (int64_t)child->receipt;
    if(service_task(0,3,owner,0))return -117;
    int64_t receipt=service_task(0,2,owner,1000);
    if(receipt<0 || (uint64_t)receipt>>32>3)return -117;
    if(child && child->owner==owner){child->receipt=(uint64_t)receipt;child->reaped=1;}
    return receipt;
}
static int full_graphical_replace_binding(unsigned role,uint64_t owner) {
    if(!full_backend || role<2 || role>3 || graphical.roles[role].owner!=owner)return -116;
    full_desktop_child *child=&full_backend->children[role-2];
    if(!child->owner || child->owner==owner || !child->reaped || child->receipt>>32>3 ||
       full_reply_pending)return -16;
    int r=reist_desktop_broker_replace(&full_backend->broker,child->owner,owner,session_now());
    if(r)return r;
    *child=(full_desktop_child){owner,0,0,0};return 0;
}
static void full_graphical_free(void) {
    if(!full_backend)return;
    if(full_backend->broker.phase && full_backend->broker.phase!=2)session_stop(-117);
    if(full_backend->manifest) {
        session_zero(full_backend->manifest,
            sizeof(full_desktop_manifest)/sizeof(full_desktop_manifest[0])*sizeof(reist_desktop_service_manifest));
        if(SESSION_S1(FREE,full_backend->manifest))session_stop(-5);
    }
    session_zero(full_backend,sizeof(*full_backend));
    if(SESSION_S1(FREE,full_backend))session_stop(-5);
    full_backend=0;full_reply_pending=0;
}
#undef full_reply
#endif
