/* Real desktop SDK over explicitly bound native mechanisms and root services. */
#include <reist/x86_64/desktop_platform.h>
#include <reist/x86_64/desktop_display.h>
#include <reist/x86_64/syscall.h>
#include <reist/abi/syscall.h>

static reist_desktop_platform_config config;
static unsigned phase,pumping,presentation_started,input_display_deferred;
static uint64_t previous,last_epoch,children[2];
static reist_desktop_service_frame request,reply;
static char startup_console[128];
static unsigned startup_console_used;
static int console_flush(void);
typedef struct {
    uint64_t remote,deadline;
    uint32_t token,rights,offset,length;
    x86os_file_info_t info;
    unsigned char data[REIST_DESKTOP_SERVICE_READ_BYTES];
} file_object;
static file_object objects[8];
static uint32_t object_sequence,storage_sequence,storage_handle;
static uint32_t storage_timeout;
static uint64_t storage_deadline;
static union {
    uint32_t words[128];
    x86os_vfs_shadow_frame_t stat;
    x86os_vfs_shadow_object_frame_t object;
    x86os_vfs_shadow_object_read_frame_t read;
    x86os_vfs_shadow_object_bulk_read_frame_t bulk;
    x86os_vfs_shadow_read_frame_t path_read;
    x86os_vfs_shadow_readdir_frame_t directory;
} storage;
static void zero(void *p,size_t n){unsigned char *d=p;for(size_t i=0;i<n;i++)d[i]=0;}
static void copy(void *p,const void *q,size_t n){unsigned char *d=p;const unsigned char *s=q;for(size_t i=0;i<n;i++)d[i]=s[i];}
static int empty(const void *p,size_t n){const unsigned char *s=p;for(size_t i=0;i<n;i++)if(s[i])return 0;return 1;}
static int text(char *out,unsigned capacity,const char *in) {
    if(!in)return -22;
    for(unsigned n=0;n<capacity;n++){out[n]=in[n];if(!in[n])return (int)n;}
    return -36;
}
static int fail(int error){phase=2;if(config.failed)config.failed(config.context,error);return error;}
static int64_t raw(unsigned n,uint64_t a,uint64_t b,uint64_t c) {
    if(phase!=1)return -116;
    return config.call(config.context,n,a,b,c);
}
#define CALL(n,a,b,c) raw(REIST_X64_SYS_##n,(uintptr_t)(a),(uintptr_t)(b),(uintptr_t)(c))
/* Legacy inline adapters outside this read-only profile get an explicit
 * unavailable result; never turn generic SDK numbers into native authority. */
uintptr_t x86os_syscall(uint32_t n,uintptr_t a,uintptr_t b,uintptr_t c) {
    (void)n;(void)a;(void)b;(void)c;return (uintptr_t)(intptr_t)-38;
}
int x86os_monotonic_ms(uint64_t *out) {
    if(!out)return -22;
    int64_t n=CALL(MONOTONIC_MS,0,0,0);if(n<0)return (int)n;
    if((uint64_t)n<previous || (uint64_t)n>INT64_MAX-120000)return fail(-84);
    *out=previous=(uint64_t)n;return 0;
}
int reist_desktop_platform_attach(const reist_desktop_platform_config *c) {
    if(phase==1)return -16;
    if(!c || !c->service || c->service->phase!=1 || !c->call || !c->pump || !c->mouse ||
       !c->key || !c->report || !c->failed || c->service->config.epoch>UINT32_MAX ||
       c->service->config.epoch<=last_epoch)return -22;
    if(c->channels && (c->channels->phase!=1 ||
       c->channels->config.root!=c->service->config.root ||
       c->channels->config.desktop!=c->service->config.desktop ||
       c->channels->config.epoch!=c->service->config.epoch))return -116;
    int64_t pid=c->call(c->context,REIST_X64_SYS_GETPID,0,0,0);
    if(pid<=0 || (uint64_t)pid!=c->service->config.desktop>>32)return -116;
    int64_t now=c->call(c->context,REIST_X64_SYS_MONOTONIC_MS,0,0,0);
    if(now<0 || (uint64_t)now<previous || (uint64_t)now>INT64_MAX-120000)return -84;
    config=*c;phase=1;pumping=0;previous=(uint64_t)now;last_epoch=c->service->config.epoch;
    presentation_started=c->channels?0:1;input_display_deferred=0;
    startup_console_used=0;zero(startup_console,sizeof(startup_console));
    zero(objects,sizeof(objects));zero(children,sizeof(children));zero(&storage,sizeof(storage));
    storage_handle=0;return 0;
}
void reist_desktop_platform_detach(void) {
    if(phase==1)(void)console_flush();
    phase=2;presentation_started=0;input_display_deferred=0;storage_handle=0;zero(objects,sizeof(objects));zero(children,sizeof(children));
    startup_console_used=0;zero(startup_console,sizeof(startup_console));
    zero(&request,sizeof(request));zero(&reply,sizeof(reply));zero(&storage,sizeof(storage));
}
int reist_desktop_platform_pump(void) {
    if(phase!=1 || config.service->phase!=1)return -116;
    if(pumping)return -16;
    pumping=1;
    int r=config.channels?reist_desktop_channels_input(config.channels):0;
    if(!r)r=config.pump(config.context);
    if(!r && presentation_started) {
        reist_desktop_channels *s=config.channels;
        unsigned pending=s && s->frontend_ready && s->config.input &&
            (s->config.input->key_count || s->config.input->mouse_count);
        /* Let the WM publish waiting input before one display batch. A second
         * pump always services display, even under continuous input traffic. */
        if(pending && !input_display_deferred)input_display_deferred=1;
        else {input_display_deferred=0;r=reist_desktop_display_service();}
    }
    pumping=0;
    return r?fail(r<0?r:-5):0;
}
/* Private startup transition, called only after both actual Surface scenes are painted.
 * Until then raster changes coalesce in the existing bounded display buffers. */
int reist_desktop_platform_begin_present(void) {
    if(phase!=1 || !config.channels || config.channels->phase!=1)return -116;
    presentation_started=1;return 0;
}
/* Private startup-render checkpoint: never renew the root deadline and never
 * publish the open frame. Pump checks input/control/health before yielding. */
int reist_desktop_platform_render_checkpoint(unsigned wait) {
    if (wait != 0 && wait != 20 && wait != 50 && wait != 100) return -22;
    if (phase != 1 || !config.channels || config.channels->phase != 1) return -116;
    uint64_t before, after;
    int r=x86os_monotonic_ms(&before);if(r)return fail(r);
    uint64_t end=config.channels->config.start_deadline_ms;
    if(config.channels->frontend_ready) {
        end=0;
        for(unsigned n=0;n<2;n++)if(config.channels->recovery[n]) {
            uint64_t recovery_end=config.channels->recovery_end[n];
            if(!recovery_end)return fail(-110);
            if(!end || recovery_end<end)end=recovery_end;
        }
    }
    if (!end || before>=end || end-before<=wait) return fail(-110);
    r=reist_desktop_platform_pump();if(r)return r;
    if (wait) { int64_t result=CALL(SLEEP_MS,wait,0,0);
        if(result)return fail(result<0 && result>=-4095?(int)result:-5); }
    r=x86os_monotonic_ms(&after);if(r)return fail(r);
    if ((wait && after<=before) || after>=end) return fail(-110);
    return 0;
}
/* A large live frame supplies one fixed deadline; checkpoints never renew it. */
int reist_desktop_platform_live_checkpoint(unsigned wait,uint64_t end) {
    if(wait!=0 && wait!=50)return -22;
    if(phase!=1 || !config.channels || config.channels->phase!=1 ||
       !config.channels->frontend_ready)return -116;
    uint64_t before,after;
    int r=x86os_monotonic_ms(&before);if(r)return fail(r);
    if(!end || before>=end || end-before>1000 || end-before<=wait)return fail(-110);
    r=reist_desktop_platform_pump();if(r)return r;
    if(wait) {
        int64_t slept=CALL(SLEEP_MS,wait,0,0);
        if(slept)return fail(slept<0 && slept>=-4095?(int)slept:-5);
    }
    r=x86os_monotonic_ms(&after);if(r)return fail(r);
    if((wait && after<=before) || after>=end)return fail(-110);
    return 0;
}
reist_desktop_channels *reist_desktop_platform_channels(void) {
    return phase==1?config.channels:0;
}
int x86os_sleep_ms(uint32_t ms) {
    if(!ms || ms>1000)return -22;
    for(unsigned used=0;used<ms;) {
        int r=reist_desktop_platform_pump();if(r)return r;
        unsigned part=ms-used;if(part>10)part=10;
        uint64_t before; r=x86os_monotonic_ms(&before);if(r)return r;
        r=(int)CALL(SLEEP_MS,part,0,0);if(r)return r;
        uint64_t after;r=x86os_monotonic_ms(&after);if(r)return r;
        if(after<=before)return fail(-84);
        used+=part;
    }
    return reist_desktop_platform_pump();
}
/* Private compositor idle tail. The next loop services input, control and
 * Surface health before dispatch. Avoid repeating those same empty polls
 * inside a one-millisecond wait; raster/startup still use their full drain. */
int reist_desktop_platform_idle_wait(void) {
    if(phase!=1 || !config.channels || config.channels->phase!=1 ||
       !config.channels->frontend_ready)return -116;
    uint64_t before,after;
    int r=x86os_monotonic_ms(&before);if(r)return fail(r);
    int64_t slept=CALL(SLEEP_MS,1,0,0);
    if(slept)return fail(slept<0 && slept>=-4095?(int)slept:-5);
    r=x86os_monotonic_ms(&after);if(r)return fail(r);
    return after>before?0:fail(-84);
}
int x86os_yield(void){int r=reist_desktop_platform_pump();return r?r:(int)CALL(YIELD,0,0,0);}
static void begin(unsigned operation) {
    zero(&request,sizeof(request));request.version=1;request.size=sizeof(request);request.operation=operation;
}
static int exchange(unsigned timeout) {
    if(phase!=1 || config.service->phase!=1)return -116;
    if(!timeout || timeout>1000)return -22;
    uint64_t now;int r=x86os_monotonic_ms(&now);if(r)return r;
    uint64_t end=now+timeout;
    if(config.channels && !config.channels->frontend_ready &&
       request.operation>=REIST_DESKTOP_STAT && request.operation<=REIST_DESKTOP_OPEN) {
        uint64_t startup_end=config.channels->config.start_deadline_ms;
        if(now>=startup_end)return -110;
        /* Optional asset probes must not monopolize the startup CPU window.
         * Spend at most one quarter of either remaining deadline waiting,
         * capped50ms for the admitted64-sample frontend, below the native100ms sleep limit. */
        unsigned delay=timeout/4;if(delay>50)delay=50;
        uint64_t available=(startup_end-now)/4;
        if(delay>available)delay=(unsigned)available;
        if(delay) {
            int64_t slept=CALL(SLEEP_MS,delay,0,0);
            if(slept)return slept<0 && slept>=-4095?(int)slept:-5;
            uint64_t before=now;r=x86os_monotonic_ms(&now);if(r)return r;
            if(now<=before)return fail(-84);
            if(now>=end || now>=startup_end)return -110;
        }
    }
    /* Wait only for local transport admission; never retry an executed RPC. */
    for(unsigned n=0;n<=100;n++) {
        reist_desktop_service_client *c=config.service;
        if(c->count<16 || now-c->timestamps[c->head]>=1000)
            return reist_desktop_service_exchange(c,&request,&reply,(unsigned)(end-now));
        if(end-now<=10)return -11;
        r=x86os_sleep_ms(10);if(r)return r;
        r=x86os_monotonic_ms(&now);if(r)return r;
        if(now>=end)return -110;
    }
    return -110;
}
static int path_request(unsigned op,const char *path,unsigned timeout) {
    begin(op);int n=text(request.payload.command.path,192,path);if(n<=0)return n?n:-22;
    return exchange(timeout);
}
int x86os_stat(const char *path,x86os_file_info_t *out) {
    if(!out)return -22;
    int r=path_request(REIST_DESKTOP_STAT,path,1000);
    if(!r)*out=reply.payload.info;
    return r;
}
int x86os_readdir_batch(const char *path,uint32_t index,x86os_file_info_t *out) {
    if(!out)return -22;
    begin(REIST_DESKTOP_READDIR);
    int n=text(request.payload.command.path,192,path);if(n<=0)return n?n:-22;
    request.offset=index;request.count=6;int r=exchange(1000);if(r)return r;
    copy(out,reply.payload.entries,reply.count*sizeof(*out));return (int)reply.count;
}
static file_object *resolve(uint32_t token,uint32_t generation) {
    if(phase!=1 || config.service->phase!=1 || generation!=last_epoch)return 0;
    for(unsigned n=0;n<8;n++)if(objects[n].remote && objects[n].token==token)return objects+n;
    return 0;
}
static int open_object(const char *path,uint32_t rights,unsigned timeout,file_object **out) {
    unsigned slot=8;for(unsigned n=0;n<8;n++)if(!objects[n].remote){slot=n;break;}
    if(slot==8)return -24;
    if(object_sequence==UINT32_MAX)return -75;
    if(!rights || rights&~X86OS_VFS_OBJECT_RIGHT_DATA)return -13;
    uint64_t start;int r=x86os_monotonic_ms(&start);if(r)return r;
    r=path_request(REIST_DESKTOP_OPEN,path,timeout);if(r)return r;
    file_object *o=objects+slot;zero(o,sizeof(*o));o->remote=reply.object;o->deadline=start+120000;
    o->token=++object_sequence;o->rights=rights;o->info=reply.payload.info;*out=o;return 0;
}
static int close_object(file_object *o,unsigned timeout) {
    begin(REIST_DESKTOP_CLOSE);request.object=o->remote;int r=exchange(timeout);
    if(!r)zero(o,sizeof(*o));
    return r;
}
static int read_object(file_object *o,unsigned offset,unsigned count,void *out,unsigned timeout) {
    if(!(o->rights&X86OS_VFS_OBJECT_RIGHT_READ))return -13;
    if(!count || count>sizeof(o->data) || offset>o->info.size)return -22;
    uint64_t now;int r=x86os_monotonic_ms(&now);if(r)return r;
    if(now>=o->deadline)return -110;
    if(count>o->info.size-offset)count=o->info.size-offset;
    if(!count)return 0;
    if(offset<o->offset || offset-o->offset>o->length || count>o->length-(offset-o->offset)) {
        begin(REIST_DESKTOP_READ);request.object=o->remote;request.offset=offset;
        request.count=o->info.size-offset;if(request.count>sizeof(o->data))request.count=sizeof(o->data);
        r=exchange(timeout);if(r)return r;
        r=x86os_monotonic_ms(&now);if(r)return r;if(now>=o->deadline)return -110;
        copy(o->data,reply.payload.bytes,reply.count);o->offset=offset;o->length=reply.count;
    }
    copy(out,o->data+offset-o->offset,count);return (int)count;
}
static int path_valid(const char *path,unsigned n) {
    return n>0 && n<192 && path[0]=='/' && !path[n] && empty(path+n,192-n);
}
int x86os_storage_submit(const x86os_storage_submit_t *q,const void *data,x86os_storage_handle_t *out) {
    if(phase!=1 || config.service->phase!=1)return -116;
    if(!q || !data || !out || q->version!=1 || q->struct_size!=sizeof(*q) || q->resource || q->offset ||
       (q->operation!=X86OS_STORAGE_VFS_SHADOW_STAT && q->operation!=X86OS_STORAGE_VFS_BULK_READ) ||
       q->length!=512 || !q->timeout_ms || q->timeout_ms>60000)return -22;
    if(storage_handle)return -16;
    if(storage_sequence==UINT32_MAX)return -75;
    /* Fixed private staging; unsupported operations never reach root or disk. */
    copy(&storage,data,512);
    if(storage.words[0]!=1 || storage.words[1]!=512){zero(&storage,512);return -22;}
    unsigned op=storage.words[2];int valid=0;
    if((op==15)!=(q->operation==X86OS_STORAGE_VFS_BULK_READ)){zero(&storage,512);return -22;}
    if(op==5)valid=!storage.stat.flags && !storage.stat.result && path_valid(storage.stat.path,storage.stat.path_length) &&
        empty(&storage.stat.info,sizeof(storage.stat.info)) && empty(storage.stat.reserved,sizeof(storage.stat.reserved));
    else if(op==8 || op==12 || op==19) {
        x86os_vfs_shadow_object_frame_t *f=&storage.object;
        unsigned rights=op==8?7:f->flags&15;
        valid=!f->result && !f->object_token && !f->service_generation && path_valid(f->path,f->path_length) &&
            empty(&f->info,sizeof(f->info)) && empty(f->reserved,sizeof(f->reserved)) && rights && !(rights&~7U) &&
            (op==8?!f->flags:!(f->flags&~(7U|(op==19?X86OS_O_NOFOLLOW:0U))));
    } else if(op==9) {
        x86os_vfs_shadow_object_read_frame_t *f=&storage.read;
        valid=!f->flags && !f->result && !f->transferred && f->requested && f->requested<=256 &&
            empty(f->data,sizeof(f->data)) && empty(f->reserved,sizeof(f->reserved));
    } else if(op==15) {
        x86os_vfs_shadow_object_bulk_read_frame_t *f=&storage.bulk;
        valid=!f->flags && !f->result && !f->transferred && !f->data_crc32 && f->requested &&
            f->requested<=X86OS_STORAGE_BULK_MAX_BYTES && empty(f->reserved,sizeof(f->reserved));
    } else if(op==10 || op==11) {
        x86os_vfs_shadow_object_frame_t *f=&storage.object;
        valid=!f->flags && !f->result && !f->path_length && empty(f->path,sizeof(f->path)) &&
            empty(&f->info,sizeof(f->info)) && empty(f->reserved,sizeof(f->reserved));
    } else if(op==7) {
        x86os_vfs_shadow_readdir_frame_t *f=&storage.directory;
        valid=!f->flags && !f->result && path_valid(f->path,f->path_length) && empty(&f->info,sizeof(f->info)) &&
            empty(f->reserved,sizeof(f->reserved));
    } else if(op==6) {
        x86os_vfs_shadow_read_frame_t *f=&storage.path_read;
        valid=!f->flags && !f->result && !f->transferred && f->requested && f->requested<=256 &&
            path_valid(f->path,f->path_length) && empty(f->data,sizeof(f->data)) && empty(f->reserved,sizeof(f->reserved));
    } else {zero(&storage,512);return op>=18 && op<=21?-30:-95;}
    if(!valid){zero(&storage,512);return -22;}
    uint64_t now;int clock=x86os_monotonic_ms(&now);if(clock){zero(&storage,512);return clock;}
    storage_timeout=q->timeout_ms>1000?1000:q->timeout_ms;
    storage_deadline=now+storage_timeout;
    storage_handle=++storage_sequence;*out=storage_handle;return 0;
}
static int storage_remaining(void) {
    uint64_t now;int r=x86os_monotonic_ms(&now);if(r)return r;
    return now<storage_deadline?(int)(storage_deadline-now):-110;
}
int x86os_storage_collect(x86os_storage_handle_t handle,int32_t *result,void *out) {
    if(!handle || handle!=storage_handle || !result || !out)return -22;
    if(phase!=1 || config.service->phase!=1)return -116;
    unsigned op=storage.words[2];int r=0;
    if(op==15)return -22;
    r=storage_remaining();if(r<0)return r;storage_timeout=(unsigned)r;
    if(op==5) {
        r=path_request(REIST_DESKTOP_STAT,storage.stat.path,storage_timeout);
        if(!r)storage.stat.info=reply.payload.info;
        storage.stat.result=r;
    } else if(op==8 || op==12 || op==19) {
        file_object *o=0;r=open_object(storage.object.path,op==8?7:storage.object.flags&15,storage_timeout,&o);
        if(!r){storage.object.object_token=o->token;storage.object.service_generation=(uint32_t)last_epoch;storage.object.info=o->info;}
        storage.object.result=r;
    } else if(op==9) {
        file_object *o=resolve(storage.read.object_token,storage.read.service_generation);
        r=o?read_object(o,storage.read.offset,storage.read.requested,storage.read.data,storage_timeout):-116;
        storage.read.result=r<0?r:0;storage.read.transferred=r<0?0:(unsigned)r;
    } else if(op==10 || op==11) {
        file_object *o=resolve(storage.object.object_token,storage.object.service_generation);
        r=!o?-116:op==11?close_object(o,storage_timeout):!(o->rights&4)?-13:previous>=o->deadline?-110:0;
        if(!r && op==10)storage.object.info=o->info;
        storage.object.result=r;
    } else if(op==7) {
        begin(REIST_DESKTOP_READDIR);copy(request.payload.command.path,storage.directory.path,192);
        request.offset=storage.directory.index;request.count=1;r=exchange(storage_timeout);
        /* Existing VFS frame: result0 carries one entry; result1 is EOF
         * with an empty info field. The public helper returns1 for an entry. */
        if(!r){if(reply.count)storage.directory.info=reply.payload.entries[0];else r=1;}
        storage.directory.result=r;
    } else if(op==6) {
        file_object *o=0;r=open_object(storage.path_read.path,7,storage_timeout,&o);
        if(!r) {
            int remaining=storage_remaining();
            r=remaining<0?remaining:read_object(o,storage.path_read.offset,storage.path_read.requested,
                storage.path_read.data,(unsigned)remaining);
            remaining=storage_remaining();
            int closed=close_object(o,remaining<0?1:(unsigned)remaining);
            if(closed){zero(storage.path_read.data,256);return fail(closed);}
        }
        if(r<0)zero(storage.path_read.data,256);
        storage.path_read.result=r<0?r:0;storage.path_read.transferred=r<0?0:(unsigned)r;
    } else return fail(-84);
    copy(out,&storage,512);*result=0;storage_handle=0;zero(&storage,512);return 0;
}
int x86os_storage_cancel(x86os_storage_handle_t handle) {
    if(!handle || handle!=storage_handle)return -22;
    storage_handle=0;zero(&storage,512);return 0;
}
int x86os_storage_bulk_collect(x86os_storage_handle_t h,int32_t *r,void *f,void *d,uint32_t c,uint32_t *n) {
    if(!h || h!=storage_handle || !r || !f || !d || !n || storage.words[2]!=15 || c<storage.bulk.requested)return -22;
    if(phase!=1 || config.service->phase!=1)return -116;
    int remaining=storage_remaining();if(remaining<0)return remaining;storage_timeout=(unsigned)remaining;
    file_object *o=resolve(storage.bulk.object_token,storage.bulk.service_generation);
    /* Short reads are part of the existing file ABI. One bounded IPC payload
     * per collection keeps health/input live, including for128KiB requests. */
    unsigned count=storage.bulk.requested;if(count>1792)count=1792;
    unsigned char staging[1792];
    int result=o?read_object(o,storage.bulk.offset,count,staging,storage_timeout):-116;
    unsigned used=result<0?0:(unsigned)result;
    uint32_t crc=UINT32_MAX;
    for(unsigned i=0;i<used;i++) {
        crc^=staging[i];for(unsigned bit=0;bit<8;bit++)crc=(crc>>1)^(0xedb88320U&(0U-(crc&1)));
    }
    storage.bulk.result=result<0?result:0;storage.bulk.transferred=used;storage.bulk.data_crc32=crc^UINT32_MAX;
    copy(f,&storage,512);copy(d,staging,used);*n=used;*r=0;
    storage_handle=0;zero(&storage,512);zero(staging,sizeof(staging));return 0;
}
static int child_slot(int pid) {
    if(pid<=0 || phase!=1)return -1;
    for(unsigned n=0;n<2;n++)if(children[n] && children[n]>>32==(unsigned)pid)return (int)n;
    return -1;
}
int reist_desktop_platform_replace(uint64_t old,uint64_t owner) {
    if(phase!=1 || !config.channels || config.service->phase!=1)return -116;
    unsigned slot=(uint32_t)old-6;
    if(slot>=2 || (uint32_t)owner!=slot+6 || owner>>32>0x7ffffffe)return -22;
    if(children[slot]!=old || config.channels->config.children[slot]!=old ||
       !config.channels->application_closed[slot] || owner>>32<=old>>32 ||
       owner>>32<=children[1-slot]>>32)return -116;
    if(config.service->busy)return -16;
    children[slot]=owner;return 0;
}
int reist_desktop_platform_adopt(const uint64_t owners[2]) {
    if(!owners)return -22;
    if(phase!=1 || config.service->phase!=1)return -116;
    if(children[0] || children[1])return -16;
    uint64_t values[2]={owners[0],owners[1]};
    for(unsigned n=0;n<2;n++)
        if((uint32_t)values[n]!=6+n || values[n]>>32<=config.service->config.desktop>>32 ||
           values[n]>>32>0x7ffffffe)return -22;
    if(values[0]>>32==values[1]>>32)return -22;
    for(unsigned n=0;n<2;n++) {
        begin(REIST_DESKTOP_IDENTITY);request.object=values[n];
        int r=exchange(1000);if(r)return r;
        if(reply.object!=values[n])return fail(-71);
    }
    children[0]=values[0];children[1]=values[1];return 0;
}
int x86os_spawnv(const char *path,int argc,const char *const *argv) {
    if(argc<1 || argc>8 || !argv)return -22;
    unsigned slot=children[0]?1:0;if(children[slot])return -11;
    begin(REIST_DESKTOP_LAUNCH);int n=text(request.payload.command.path,192,path);if(n<=0)return n?n:-22;
    request.argc=(unsigned)argc;
    for(int i=0;i<argc;i++){n=text(request.payload.command.argv[i],128,argv[i]);if(n<0)return n;}
    int r=exchange(1000);if(r)return r;
    if(children[0]==reply.object || children[1]==reply.object)return fail(-71);
    children[slot]=reply.object;return (int)(reply.object>>32);
}
int x86os_spawn(const char *path){const char *args[]={path};return x86os_spawnv(path,1,args);}
static int child_request(int pid,unsigned op) {
    int slot=child_slot(pid);if(slot<0)return -13;
    begin(op);request.object=children[slot];return exchange(1000);
}
int x86os_process_identity_of(int pid,x86os_process_identity_t *out) {
    if(!out)return -22;
    int r=child_request(pid,REIST_DESKTOP_IDENTITY);if(r)return r;
    *out=(x86os_process_identity_t){1,sizeof(*out),pid,(unsigned)pid};return 0;
}
int x86os_process_identity(x86os_process_identity_t *out) {
    if(!out)return -22;
    int64_t pid=CALL(GETPID,0,0,0);if(pid<0)return (int)pid;
    if((uint64_t)pid!=config.service->config.desktop>>32)return fail(-116);
    *out=(x86os_process_identity_t){1,sizeof(*out),(int)pid,(unsigned)pid};return 0;
}
int x86os_kill(int pid){return child_request(pid,REIST_DESKTOP_CANCEL);}
int x86os_wait(int pid,int *status) {
    if(!status)return -22;
    int slot=child_slot(pid);if(slot<0)return -13;
    int r=child_request(pid,REIST_DESKTOP_WAIT);if(r)return r;
    *status=(int)reply.offset;children[slot]=0;return pid;
}
int x86os_ipc_create(x86os_ipc_handle_t *out) {if(!out)return -22;return (int)CALL(IPC_CREATE,out,0,0);}
int x86os_ipc_close(x86os_ipc_handle_t h){
    int r=(int)CALL(IPC_CLOSE,h,0,0);
    if(!r && config.channels)
        for(unsigned n=0;n<2;n++)if(config.channels->config.application_endpoints[n]==h)
            config.channels->application_closed[n]=1;
    return r;
}
int x86os_ipc_release(x86os_ipc_handle_t h){return (int)CALL(IPC_RELEASE,h,0,0);}
int x86os_ipc_delegate(x86os_ipc_handle_t h,int pid,uint32_t rights) {
    if(!h || !rights || rights&~3U)return -22;
    int r=child_request(pid,REIST_DESKTOP_IDENTITY);return r?r:(int)CALL(IPC_DELEGATE,h,pid,rights);
}
int x86os_ipc_send_timeout(x86os_ipc_handle_t h,const x86os_ipc_message_t *m,uint32_t timeout) {
    if(!m || timeout>1000)return -22;
    return (int)CALL(IPC_SEND_TIMEOUT,h,m,timeout);
}
int x86os_ipc_receive_timeout(x86os_ipc_handle_t h,x86os_ipc_message_t *m,uint32_t timeout) {
    if(!m || timeout>1000)return -22;
    if(phase!=1)return -116;
    if(config.channels)
        for(unsigned n=0;n<2;n++)if(config.channels->config.application_endpoints[n]==h)
            return timeout?-95:reist_desktop_channels_surface(config.channels,n,m);
    return (int)CALL(IPC_RECEIVE_TIMEOUT,h,m,timeout);
}
int x86os_terminal_input(uint32_t op,int pid,uint32_t generation) {
    if(op!=REIST_TERMINAL_CHECK && op!=REIST_TERMINAL_ACQUIRE_SERVICE && op!=REIST_TERMINAL_RELEASE)return -13;
    if(pid || generation)return -22;
    reist_terminal_input_request_t q={1,sizeof(q),op,0,0,0};
    return (int)CALL(TERMINAL_INPUT,&q,0,0);
}
int x86os_reist_report(uint32_t op,uint32_t value){
    if(phase!=1)return -116;
    if(op==X86OS_REIST_REPORT_SERVICE_READY){int r=console_flush();if(r)return r;}
    return config.report(config.context,op,value);
}
int x86os_mouse_event(x86os_mouse_event_t *out){
    if(!out)return -22;
    if(phase!=1)return -116;
    if(config.channels) {
        if(config.channels->phase!=1)return -116;
        return reist_desktop_input_mouse(config.channels->config.input,out);
    }
    return config.mouse(config.context,out);
}
int x86os_getchar_nonblocking(void) {
    if(phase!=1)return -116;
    if(config.channels && config.channels->phase!=1)return -116;
    int r=config.channels?reist_desktop_input_key(config.channels->config.input):config.key(config.context);
    return r==-11?0:r; /* Conventional SDK: zero means no pending byte. */
}
void *x86os_malloc(size_t size){
    if(!size || size>16U*1024*1024 || phase!=1)return 0;
    /* Fixed workspace initialization must also service input/root messages.
     * Pace admission before allocating, so failure creates no new ownership.
     * One pump and one bounded50ms sleep leave room in the admitted64-sample CPU
     * budget without repeatedly polling empty channels. The sleep obeys the
     * native per-call bound and the original, never renewed startup deadline. */
    if(size>=65536 && config.channels && !config.channels->frontend_ready) {
        if(reist_desktop_platform_pump())return 0;
        uint64_t now;
        if(x86os_monotonic_ms(&now))return 0;
        for(unsigned n=0;n<1;n++) {
            uint64_t end=config.channels->config.start_deadline_ms,before=now;
            if(now>=end || end-now<=50){fail(-110);return 0;}
            int64_t slept=CALL(SLEEP_MS,50,0,0);
            if(slept){fail(slept<0 && slept>=-4095?(int)slept:-5);return 0;}
            if(x86os_monotonic_ms(&now))return 0;
            if(now<=before){fail(-84);return 0;}
            if(now>=end){fail(-110);return 0;}
        }
    }
    int64_t p=CALL(MALLOC,size,0,0);return p>0?(void *)(uintptr_t)p:0;
}
void x86os_free(void *p){if(p && CALL(FREE,p,0,0))fail(-5);}
int x86os_write(int fd,const void *p,size_t n) {
    if(fd!=1 && fd!=2)return -30;
    if(!p || n>4096)return -22;
    int r=console_flush();if(r)return r;
    return (int)CALL(WRITE,fd,p,n);
}
static int console_write(const char *s,unsigned length) {
    if(!length)return 0;
    uint64_t start;int error=x86os_monotonic_ms(&start);if(error)return error;
    unsigned sent=0;
    for(unsigned n=0;n<128 && sent<length;n++) {
        uint64_t now=start;
        if(n && (error=x86os_monotonic_ms(&now)))return error;
        if(now-start>=200)return fail(-110);
        unsigned count=length-sent;if(count>64)count=64;
        int r=(int)CALL(WRITE,1,s+sent,count);
        if(r>0 && (unsigned)r<=count)sent+=(unsigned)r;
        else if(r!=-11)return fail(-5);
        if(r==-11 && (error=x86os_sleep_ms(1)))return error;
    }
    return sent!=length?fail(-110):0;
}
static int console_flush(void) {
    if(!startup_console_used)return 0;
    unsigned length=startup_console_used;startup_console_used=0;
    int r=console_write(startup_console,length);
    zero(startup_console,sizeof(startup_console));return r;
}
void x86os_puts(const char *s) {
    if(!s){fail(-22);return;}
    unsigned length=0;while(length<4096 && s[length])length++;
    if(length==4096){fail(-36);return;}
    if(!length || phase!=1)return;
    /* The private startup log is line-buffered, like a conventional terminal
     * stream. Explicit writes, READY and detach flush the bounded tail. */
    if(config.channels && !config.channels->frontend_ready) {
        for(unsigned n=0;n<length;n++) {
            startup_console[startup_console_used++]=s[n];
            if((s[n]=='\n' || startup_console_used==sizeof(startup_console)) && console_flush())return;
        }
    } else {
        if(console_flush())return;
        (void)console_write(s,length);
    }
}
void x86os_putchar(char c){char s[2]={c,0};x86os_puts(s);}
void x86os_print_number(int v) {
    char out[12];unsigned at=11;out[at]=0;unsigned n=v<0?0U-(unsigned)v:(unsigned)v;
    do{out[--at]=(char)('0'+n%10);n/=10;}while(n);
    if(v<0)out[--at]='-';
    x86os_puts(out+at);
}
int x86os_getcwd(char *out,size_t n){if(!out || n<2)return -22;if(phase!=1)return -116;out[0]='/';out[1]=0;return 0;}
int x86os_cpu_topology(x86os_cpu_topology_t *out){if(!out)return -22;return (int)CALL(CPU_TOPOLOGY,out,0,0);}
uint32_t x86os_get_date(void){return 0;} /* No calendar service in this profile. */
uint32_t x86os_get_time(void){return 0;}
int x86os_drive_info(uint32_t n,x86os_drive_info_t *out){(void)n;(void)out;return -95;}
int x86os_service_connect(uint32_t id,x86os_ipc_handle_t *out){(void)id;(void)out;return -95;}
int x86os_close(int fd){(void)fd;return -9;}
int x86os_create(const char *p){(void)p;return -30;}
int x86os_fsync(int fd){(void)fd;return -30;}
int x86os_mkdir(const char *p){(void)p;return -30;}
int x86os_rmdir(const char *p){(void)p;return -30;}
int x86os_unlink(const char *p){(void)p;return -30;}
int x86os_rename(const char *a,const char *b){(void)a;(void)b;return -30;}
void x86os_clear(void){ /* Text-console clearing has no graphical authority. */ }
