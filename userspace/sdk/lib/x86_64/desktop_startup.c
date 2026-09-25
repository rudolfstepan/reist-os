/* Native desktop startup adapters. Input decoding remains in the PS/2 process;
 * this layer validates its normalized, generation-scoped input-v2 messages. */
#include <reist/x86_64/desktop_platform.h>
#include <reist/x86_64/desktop_display.h>
#include <reist/x86_64/syscall.h>
#include "../../../gui/compositor/desktop_surface_runtime.h"
#include "../../../gui/compositor/desktop_wm.h"
/* Private adapter transition; no wire/syscall or public SDK ABI addition. */
extern int reist_desktop_platform_begin_present(void);
extern int reist_desktop_platform_render_checkpoint(unsigned wait);

static int frontend_scene_ready(const desktop_surface_runtime_t *runtime,
    const desktop_surface_manager_t *manager,const desktop_wm_t *windows,unsigned presented) {
    reist_desktop_channels *s=reist_desktop_platform_channels();
    if(!runtime || !manager || !windows)return -22;
    if(!s || s->phase!=1)return -116;
    if(s->frontend_ready)return 1;
    uint64_t now;int r=x86os_monotonic_ms(&now);if(r)return r;
    if(!s->config.start_deadline_ms || now>=s->config.start_deadline_ms)return -110;
    const reist_desktop_input_state *input=s->config.input;
    if(input->phase!=1)return -116;
    if(!input->sequence)return 0;
    if(now<input->healthy_ms || now-input->healthy_ms>=1000)return -110;
    for(unsigned n=0;n<2;n++) {
        if(s->application_failed[n] || s->application_closed[n])return -116;
        if(!s->health_sequence[n])return 0;
        if(now<s->health_ms[n] || now-s->health_ms[n]>=1000)return -110;
        const desktop_surface_runtime_client_t *client=&runtime->clients[n];
        unsigned pid=(unsigned)(s->config.children[n]>>32);
        if(client->active!=DESKTOP_SURFACE_RUNTIME_BOUND || client->owner.pid!=pid ||
           client->owner.process_generation!=pid || client->endpoint!=s->config.application_endpoints[n])return -116;
        unsigned found=0;
        for(unsigned k=0;k<DESKTOP_SURFACE_CAPACITY;k++) {
            const desktop_surface_slot_t *slot=&manager->slots[k];
            if(slot->active && slot->owner.pid==pid && slot->owner.process_generation==pid &&
               slot->role==REIST_GUI_SURFACE_ROLE_TOPLEVEL && slot->window_index<DESKTOP_WM_CAPACITY &&
               slot->configured_serial && slot->acknowledged_serial==slot->configured_serial &&
               slot->paint_generation && (!presented || slot->presented_generation==slot->paint_generation) &&
               !slot->paint_active && slot->committed_paint_count) {
                const desktop_window_t *window=&windows->windows[slot->window_index];
                if(window->visible && !window->minimized && window->generation &&
                   window->width && window->height &&
                   window->content_id==(0x80000000U|slot->handle.id))found=1;
            }
        }
        if(!found)return 0;
    }
    return 1;
}
int reist_desktop_frontend_scene_ready(const desktop_surface_runtime_t *runtime,
    const desktop_surface_manager_t *manager,const desktop_wm_t *windows) {
    return frontend_scene_ready(runtime,manager,windows,0);
}
int reist_desktop_frontend_presented(const desktop_surface_runtime_t *runtime,
    const desktop_surface_manager_t *manager,const desktop_wm_t *windows) {
    int r=frontend_scene_ready(runtime,manager,windows,1);if(r<=0)return r;
    reist_desktop_channels *s=reist_desktop_platform_channels();
    if(s->frontend_ready)return 0;
    r=reist_desktop_platform_begin_present();if(r)return r;
    r=reist_desktop_display_idle();if(r)return r<0?r:0;
    r=x86os_reist_report(X86OS_REIST_REPORT_SERVICE_READY,1);if(r)return r;
    s->frontend_ready=1;x86os_puts("DESKTOP_OK\n");return 0;
}

/* A raster pass can span a health interval. Consume queued application
 * messages before evaluating freshness, using the existing bounded runtime.
 * New paint still needs a later raster/presented generation before READY. */
int reist_desktop_frontend_finish_frame(desktop_surface_runtime_t *runtime,
    desktop_surface_manager_t *manager,const desktop_wm_t *windows) {
    if(!runtime || !manager || !windows)return -22;
    reist_desktop_channels *live=reist_desktop_platform_channels();
    if(!live || live->phase!=1)return -116;
    if(live->frontend_ready && !live->recovery[0] && !live->recovery[1]) {
        /* Publish the completed live raster, then return immediately to the
         * main loop's input/control/health drain. Startup/recovery below still
         * require their full lifecycle and scene validation. */
        extern int reist_desktop_display_service(void);
        return reist_desktop_display_service();
    }
    /* Complete the initial physical drain without re-running the whole GUI
     * between tile batches. A new unpresented paint returns to the renderer.
     * Every turn retains control/health checks and the original deadline. */
    for(unsigned turn=0;turn<24;turn++) {
        (void)desktop_surface_runtime_poll(runtime,manager);
        int r=reist_desktop_platform_pump();if(r)return r;
        r=reist_desktop_frontend_presented(runtime,manager,windows);if(r)return r;
        reist_desktop_channels *s=reist_desktop_platform_channels();
        if(!s || s->phase!=1)return -116;
        if(s->frontend_ready) {
            if(reist_desktop_display_idle()==0)for(unsigned n=0;n<2;n++) {
                if(s->recovery[n]!=REIST_DESKTOP_RECOVERY_WAIT_READY || !s->health_sequence[n])continue;
                uint64_t now;if(x86os_monotonic_ms(&now))return -5;
                if(now>=s->recovery_end[n] || now<s->health_ms[n] || now-s->health_ms[n]>=1000)return -110;
                const desktop_surface_runtime_client_t *client=&runtime->clients[n];
                unsigned pid=(unsigned)(s->config.children[n]>>32);
                if(client->active!=DESKTOP_SURFACE_RUNTIME_BOUND || client->owner.pid!=pid ||
                   client->owner.process_generation!=pid || client->endpoint!=s->config.application_endpoints[n])return -116;
                for(unsigned k=0;k<DESKTOP_SURFACE_CAPACITY;k++) {
                    const desktop_surface_slot_t *slot=&manager->slots[k];
                    if(slot->active && slot->owner.pid==s->config.children[n]>>32 &&
                       slot->owner.process_generation==s->config.children[n]>>32 &&
                       slot->acknowledged_serial && slot->acknowledged_serial==slot->configured_serial &&
                       slot->paint_generation && slot->paint_generation==slot->presented_generation &&
                       slot->committed_paint_count && !slot->paint_active &&
                       slot->role==REIST_GUI_SURFACE_ROLE_TOPLEVEL && slot->window_index<DESKTOP_WM_CAPACITY) {
                        const desktop_window_t *window=&windows->windows[slot->window_index];
                        if(window->visible && !window->minimized && window->generation &&
                           window->width && window->height &&
                           window->content_id==(0x80000000U|slot->handle.id))s->recovery_ready[n]=1;
                    }
                }
            }
            /* A replacement awaiting presentation must not consume the
             * compositor CPU window by repeatedly polling already healthy
             * peers. Keep the existing absolute recovery deadline. */
            if(s->recovery[0] || s->recovery[1])
                return reist_desktop_platform_render_checkpoint(50);
            return 0;
        }
        r=frontend_scene_ready(runtime,manager,windows,1);if(r<=0)return r;
        /* Generic sleep services the display both before and after each10ms
         * slice. Use one direct bounded wait to keep tile work paced. */
        if(turn+1<24) { r=reist_desktop_platform_render_checkpoint(20);if(r)return r; }
    }
    return 0;
}

int reist_desktop_frontend_adopt(desktop_surface_runtime_t *runtime) {
    reist_desktop_channels *s=reist_desktop_platform_channels();
    if(!runtime)return -22;
    if(!s || s->phase!=1)return -116;
    const unsigned char *raw=(const unsigned char *)runtime;
    for(unsigned n=0;n<sizeof(*runtime);n++)if(raw[n])return -16;
    desktop_surface_runtime_client_t clients[2]={{0}};
    for(unsigned n=0;n<2;n++) {
        if(s->application_failed[n] || s->application_closed[n])return -116;
        int pid=(int)(s->config.children[n]>>32);
        x86os_process_identity_t identity;
        int r=x86os_process_identity_of(pid,&identity);if(r)return r;
        if(identity.version!=1 || identity.struct_size!=sizeof(identity) ||
           identity.pid!=pid || identity.generation!=(unsigned)pid)return -116;
        clients[n].endpoint=s->config.application_endpoints[n];
        clients[n].owner.pid=pid;clients[n].owner.process_generation=identity.generation;
        clients[n].active=DESKTOP_SURFACE_RUNTIME_BOUND;
    }
    for(unsigned n=0;n<2;n++) {
        reist_graphical_control hello={1,64,REIST_GRAPHICAL_HELLO,n+2,s->config.epoch,
            1,s->config.children[n],clients[n].endpoint,0,0,0};
        x86os_ipc_message_t message={0};message.version=1;message.struct_size=sizeof(message);
        message.length=sizeof(hello);
        const unsigned char *bytes=(const unsigned char *)&hello;
        for(unsigned k=0;k<sizeof(hello);k++)message.payload[k]=bytes[k];
        int r=x86os_ipc_send_timeout(clients[n].endpoint,&message,100);if(r)return r;
    }
    /* The handshake already granted both endpoints. Publish the ordinary
     * runtime records only after both live checks and HELLO sends succeed.
     * Re-delegating an existing peer is rejected by the native IPC contract. */
    runtime->clients[0]=clients[0];runtime->clients[1]=clients[1];return 0;
}

static int startup_clock(void *context,uint64_t *out) {
    const reist_desktop_platform_config *p=context;
    int64_t now=p->call(p->context,REIST_X64_SYS_MONOTONIC_MS,0,0,0);
    if(now<0)return now>=-4095?(int)now:-84;
    *out=(uint64_t)now;return 0;
}
static int startup_commit(void *context,const reist_display_request_v1 *q) {
    const reist_desktop_platform_config *p=context;
    int64_t r=p->call(p->context,REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)q,0);
    return r>0 || r<INT32_MIN?-5:(int)r;
}
static int startup_allocation_pause(const reist_desktop_platform_config *p) {
    if(!p->channels)return 0;
    /* Separate the two large page-backed allocations from the handshake and
     * each other. Each sleep remains within the native100ms syscall limit;
     * the original root startup deadline remains authoritative. */
    uint64_t end=p->channels->config.start_deadline_ms,previous=0;
    for(unsigned n=0;n<2;n++) {
        uint64_t now=0;int r=startup_clock((void *)p,&now);if(r)return r;
        if((n && now<=previous) || now>=end || end-now<=50)return -110;
        previous=now;
        int64_t slept=p->call(p->context,REIST_X64_SYS_SLEEP_MS,50,0,0);
        if(slept)return slept<0 && slept>=-4095?(int)slept:-5;
    }
    uint64_t now=0;int r=startup_clock((void *)p,&now);if(r)return r;
    return now<=previous || now>=end?-110:0;
}
int reist_desktop_startup_run(const reist_desktop_startup_config *c,int argc,char **argv) {
    if(!c || !c->entry || !c->font || c->font_bytes!=4096 || argc<1 || argc>8 ||
       !argv || !argv[0])return -22;
    /* Copy caller configuration before invoking callbacks. It outlives the
     * synchronous entry; no pointers to this stack survive detach. */
    reist_desktop_startup_config cfg=*c;
    int result=reist_desktop_platform_attach(&cfg.platform);
    if(result)return result;
    reist_desktop_platform_config *p=&cfg.platform;
    uint32_t *front=0,*back=0;unsigned attached=0;
    uint64_t owner=p->service->config.desktop;
    reist_display_request_v1 query={1,64,REIST_DISPLAY_QUERY,0,owner,0,0,0,0,0,0,0,0};
    int64_t epoch=p->call(p->context,REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&query,0);
    if(epoch<=0){result=epoch<INT32_MIN || !epoch?-5:(int)epoch;goto done;}
    reist_display_info_v2 info={2,64,REIST_DISPLAY_INFO,0,owner,(uint64_t)epoch,0,0,0,0,0,0,0,0};
    int64_t r=p->call(p->context,REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&info,0);
    if(r){result=r>0 || r<INT32_MIN?-5:(int)r;goto done;}
    if(info.version!=2 || info.size!=64 || info.operation!=REIST_DISPLAY_INFO ||
       info.flags || info.owner!=owner || info.epoch!=(uint64_t)epoch || info.reserved ||
       info.width<320 || info.width>1024 || info.height<240 || info.height>768 ||
       info.pitch<info.width*4 || info.pitch%4 || info.bits_per_pixel!=32 ||
       info.red_field_position!=16 || info.green_field_position!=8 || info.blue_field_position) {
        result=-71;goto done;
    }
    size_t capacity=(size_t)info.width*info.height;
    r=p->call(p->context,REIST_X64_SYS_MALLOC,capacity*4,0,0);
    if(r<=0){result=-12;goto done;}front=(uint32_t *)(uintptr_t)r;
    result=startup_allocation_pause(p);if(result)goto done;
    r=p->call(p->context,REIST_X64_SYS_MALLOC,capacity*4,0,0);
    if(r<=0){result=-12;goto done;}back=(uint32_t *)(uintptr_t)r;
    if(back==front){back=0;result=-84;goto done;}
    result=startup_allocation_pause(p);if(result)goto done;
    reist_desktop_display_config display={1,sizeof(display),info.width,info.height,
        owner,(uint64_t)epoch,front,back,capacity,cfg.font,cfg.font_bytes,p,startup_clock,startup_commit};
    result=reist_desktop_display_attach(&display);if(result)goto done;
    attached=1;
    result=reist_desktop_platform_adopt(cfg.children);if(result)goto done;
    result=cfg.entry(argc,argv);
done:
    if(attached)reist_desktop_display_detach();
    reist_desktop_platform_detach();
    int cleanup=0;
    if(back && p->call(p->context,REIST_X64_SYS_FREE,(uintptr_t)back,0,0))cleanup=-5;
    if(front && p->call(p->context,REIST_X64_SYS_FREE,(uintptr_t)front,0,0))cleanup=-5;
    if(cleanup){p->failed(p->context,cleanup);return cleanup;}
    return result;
}

static int input_fail(reist_desktop_input_state *s,int error) {
    s->phase=2;s->mouse_head=s->mouse_count=s->key_head=s->key_count=0;
    unsigned char *p=(unsigned char *)s->mice;
    for(unsigned n=0;n<sizeof(s->mice);n++)p[n]=0;
    for(unsigned n=0;n<sizeof(s->keys);n++)s->keys[n]=0;
    for(unsigned n=0;n<32;n++)s->mouse_sequence[n]=0;
    for(unsigned n=0;n<64;n++)s->key_sequence[n]=0;
    return error;
}
int reist_desktop_input_bind(reist_desktop_input_state *s,uint64_t owner,
                            uint64_t driver,uint64_t epoch,uint64_t now) {
    if(!s || (uint32_t)owner!=4 || !(owner>>32) || owner>>32>0x7ffffffe ||
       (uint32_t)driver!=5 || driver>>32<=owner>>32 || driver>>32>0x7ffffffe ||
       !epoch || epoch>INT64_MAX || now>INT64_MAX-1000)return -22;
    if(s->phase)return -16;
    const unsigned char *p=(const unsigned char *)s;
    for(unsigned n=0;n<sizeof(*s);n++)if(p[n])return -22;
    s->owner=owner;s->driver=driver;s->epoch=epoch;s->previous=now;s->phase=1;
    return 0;
}
static unsigned input_key_bytes(const reist_input_event_v1 *e,unsigned char out[3]) {
    static const char plain[89]="\0\0331234567890-=\b\tqwertyuiop[]\n\0asdfghjkl;'`\0\\zxcvbnm,./\0*\0 \0";
    static const char shifted[89]="\0\033!@#$%^&*()_+\b\tQWERTYUIOP{}\n\0ASDFGHJKL:\"~\0|ZXCVBNM<>?\0*\0 \0";
    if(e->flags&1)return 0; /* release, not a new character */
    if(e->flags&2) {
        unsigned char arrow=e->code==0x48?'A':e->code==0x50?'B':e->code==0x4d?'C':e->code==0x4b?'D':0;
        if(arrow){out[0]=27;out[1]='[';out[2]=arrow;return 3;}
        if(e->code==0x1c){out[0]='\n';return 1;}
        if(e->code==0x53){out[0]=127;return 1;}
        return 0;
    }
    unsigned char key=(unsigned char)((e->flags&4)?shifted[e->code]:plain[e->code]);
    if(e->flags&32) {
        if(key>='a' && key<='z')key-=32;
        else if(key>='A' && key<='Z')key+=32;
    }
    if(e->flags&8) {
        if(key>='a' && key<='z')key=(unsigned char)(key-'a'+1);
        else if(key>='A' && key<='Z')key=(unsigned char)(key-'A'+1);
    }
    if(!key)return 0;
    if(e->flags&16){out[0]=27;out[1]=key;return 2;}
    out[0]=key;return 1;
}
int reist_desktop_input_push(reist_desktop_input_state *s,const reist_input_event_v1 *event,uint64_t now) {
    if(!s || !event)return -22;
    if(s->phase!=1)return -116;
    if(now<s->previous || now>INT64_MAX-1000)return input_fail(s,-84);
    if(s->mouse_head>=32 || s->mouse_count>32 || s->key_head>=64 || s->key_count>64)return input_fail(s,-84);
    reist_input_event_v1 e=*event;
    if(e.version!=2 || e.size!=64 || e.owner!=s->driver || e.target!=s->owner ||
       e.epoch!=s->epoch || s->sequence==UINT64_MAX || e.sequence!=s->sequence+1 ||
       (!s->sequence && e.type!=REIST_INPUT_HEALTHY))return input_fail(s,-116);
    unsigned char bytes[3]={0};unsigned count=0;
    if(e.type==REIST_INPUT_HEALTHY) {
        if(e.flags || e.code || e.dx || e.dy || e.buttons)return input_fail(s,-71);
    } else if(e.type==REIST_INPUT_KEY) {
        if(e.flags&~63U || e.code<=0 || e.code>0x58 || e.dx || e.dy || e.buttons)return input_fail(s,-71);
        count=input_key_bytes(&e,bytes);
        if(count>64-s->key_count)return input_fail(s,-122);
    } else if(e.type==REIST_INPUT_POINTER) {
        if(e.flags || e.code || e.dx< -256 || e.dx>255 || e.dy< -256 || e.dy>255 || e.buttons>7)return input_fail(s,-71);
        if(s->mouse_count==32)return input_fail(s,-122);
    } else return input_fail(s,-71);
    int r=reist_graphical_charge(&s->rate,now,128);if(r)return input_fail(s,r);
    s->sequence=e.sequence;s->previous=s->healthy_ms=now;
    if(e.type==REIST_INPUT_POINTER) {
        unsigned at=(s->mouse_head+s->mouse_count)%32;
        s->mice[at]=(x86os_mouse_event_t){1,sizeof(x86os_mouse_event_t),e.dx,-e.dy,0,e.buttons,(uint32_t)(s->driver>>32),0};
        s->mouse_sequence[at]=e.sequence;
        s->mouse_count++;
    }
    for(unsigned n=0;n<count;n++) {
        unsigned at=(s->key_head+s->key_count++)%64;
        s->keys[at]=bytes[n];s->key_sequence[at]=e.sequence;
    }
    return 0;
}
static int input_heads_valid(const reist_desktop_input_state *s) {
    if(s->mouse_head>=32 || s->mouse_count>32 || s->key_head>=64 || s->key_count>64)return 0;
    if(s->mouse_count && (!s->mouse_sequence[s->mouse_head] ||
       s->mouse_sequence[s->mouse_head]>s->sequence))return 0;
    if(s->key_count && (!s->key_sequence[s->key_head] ||
       s->key_sequence[s->key_head]>s->sequence))return 0;
    if(s->mouse_count && s->key_count &&
       s->mouse_sequence[s->mouse_head]==s->key_sequence[s->key_head])return 0;
    return 1;
}
int reist_desktop_input_mouse(reist_desktop_input_state *s,x86os_mouse_event_t *out) {
    if(!s || !out)return -22;
    if(s->phase!=1)return -116;
    if(!input_heads_valid(s))return input_fail(s,-84);
    if(!s->mouse_count)return -11;
    if(s->key_count && s->key_sequence[s->key_head]<s->mouse_sequence[s->mouse_head])return -11;
    s->mouse_sequence[s->mouse_head]=0;
    *out=s->mice[s->mouse_head];s->mouse_head=(s->mouse_head+1)%32;s->mouse_count--;
    return 0;
}
int reist_desktop_input_peek_key(reist_desktop_input_state *s) {
    if(!s)return -22;
    if(s->phase!=1)return -116;
    if(!input_heads_valid(s))return input_fail(s,-84);
    if(!s->key_count)return -11;
    if(s->mouse_count && s->mouse_sequence[s->mouse_head]<s->key_sequence[s->key_head])return -11;
    return s->keys[s->key_head];
}
int reist_desktop_input_key(reist_desktop_input_state *s) {
    int key=reist_desktop_input_peek_key(s);if(key<0)return key;
    s->keys[s->key_head]=0;s->key_sequence[s->key_head]=0;
    s->key_head=(s->key_head+1)%64;s->key_count--;return key;
}

static void channel_zero(void *p,size_t bytes) {
    unsigned char *d=p;for(size_t n=0;n<bytes;n++)d[n]=0;
}
static void channel_copy(void *out,const void *in,size_t bytes) {
    unsigned char *d=out;const unsigned char *s=in;for(size_t n=0;n<bytes;n++)d[n]=s[n];
}
static int channel_fail(reist_desktop_channels *s,int error) {
    s->phase=2;s->head=s->count=s->reply_pending=0;
    channel_zero(s->controls,sizeof(s->controls));channel_zero(&s->reply,sizeof(s->reply));
    return error;
}
int reist_desktop_channels_init(reist_desktop_channels *s,const reist_desktop_channels_config *c,uint64_t now) {
    if(!s || !c || !c->call || !c->input || c->input->phase!=1 ||
       c->input->owner!=c->desktop || (uint32_t)c->root || !(c->root>>32) ||
       c->root>>32>=c->desktop>>32 || (uint32_t)c->desktop!=4 ||
       c->desktop>>32>0x7ffffffe || !c->epoch || c->epoch>INT64_MAX ||
       now<c->input->previous || now>INT64_MAX-REIST_GRAPHICAL_START_MS ||
       (c->start_deadline_ms && (c->start_deadline_ms<=now || c->start_deadline_ms-now>REIST_GRAPHICAL_START_MS)))return -22;
    if(s->phase)return -16;
    const unsigned char *raw=(const unsigned char *)s;
    for(unsigned n=0;n<sizeof(*s);n++)if(raw[n])return -22;
    uint32_t endpoints[4]={c->root_endpoint,c->input_endpoint,
        c->application_endpoints[0],c->application_endpoints[1]};
    for(unsigned n=0;n<4;n++) {
        if(!endpoints[n])return -22;
        for(unsigned k=0;k<n;k++)if(endpoints[k]==endpoints[n])return -22;
    }
    for(unsigned n=0;n<2;n++)
        if((uint32_t)c->children[n]!=6+n || c->children[n]>>32<=c->desktop>>32 ||
           c->children[n]>>32>0x7ffffffe)return -22;
    if(c->children[0]>>32==c->children[1]>>32)return -22;
    s->config=*c;s->previous=now;s->phase=1;return 0;
}
static int channel_clock(reist_desktop_channels *s,uint64_t *now) {
    int64_t r=s->config.call(s->config.context,REIST_X64_SYS_MONOTONIC_MS,0,0,0);
    if(r<0 || (uint64_t)r<s->previous || r>INT64_MAX-1000)return channel_fail(s,-84);
    s->previous=*now=(uint64_t)r;return 0;
}
static int channel_read_wait(reist_desktop_channels *s,uint32_t endpoint,x86os_ipc_bulk_message_t *m,unsigned wait) {
    /* Only the root service channel carries bulk frames. Input and Surface
     * peers are bounded to the existing IPC-v1 envelope. */
    unsigned admitted=endpoint==s->config.root_endpoint?2048U:128U;
    channel_zero(m,12U+admitted);m->version=admitted==128U?1U:2U;
    m->struct_size=12U+admitted;m->length=admitted;
    int64_t r=s->config.call(s->config.context,REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,
        endpoint,(uintptr_t)m,wait);
    if(r==-11 || (wait && r==-110))return -11;
    if(r)return r>0 || r<INT32_MIN?-5:(int)r;
    unsigned capacity=m->version==1 && m->struct_size==140?128:
        m->version==2 && m->struct_size==2060?2048:0;
    if(!m->length || m->length>capacity || capacity>admitted)return -71;
    for(unsigned n=m->length;n<capacity;n++)if(m->payload[n])return -71;
    return 0;
}
static int channel_read(reist_desktop_channels *s,uint32_t endpoint,x86os_ipc_bulk_message_t *m) {
    return channel_read_wait(s,endpoint,m,0);
}
static int channel_root_wait(reist_desktop_channels *s,unsigned wait) {
    if(!s || s->phase!=1)return -116;
    uint64_t now;int r=channel_clock(s,&now);if(r)return r;
    for(unsigned n=0;n<8;n++) {
        x86os_ipc_bulk_message_t m;r=channel_read_wait(s,s->config.root_endpoint,&m,n?0:wait);
        if(r==-11)return 0;
        if(r)return channel_fail(s,r);
        if(m.version==1 && m.length==64) {
            reist_graphical_control c;channel_copy(&c,m.payload,sizeof(c));
            if(c.version!=1 || c.size!=64 || c.epoch!=s->config.epoch || c.reserved ||
               c.role>=4 || (c.type!=REIST_GRAPHICAL_BIND && c.type!=REIST_GRAPHICAL_READY &&
               c.type!=REIST_GRAPHICAL_STOP && c.type!=REIST_GRAPHICAL_CLIENT_REAPED))
                return channel_fail(s,-71);
            if(s->count>=4)return channel_fail(s,-122);
            s->controls[(s->head+s->count++)%4]=c;
        } else if(m.version==2 && m.length==2048) {
            reist_desktop_service_frame *q=&s->reply;
            if(s->reply_pending)return channel_fail(s,-122);
            channel_copy(q,m.payload,sizeof(*q));
            if(q->version!=1 || q->size!=2048 || q->root!=s->config.root ||
               q->desktop!=s->config.desktop || q->epoch!=s->config.epoch)
                return channel_fail(s,-116);
            s->reply_pending=1;
        } else return channel_fail(s,-71);
    }
    return 0;
}
static int channel_root(reist_desktop_channels *s) { return channel_root_wait(s,0); }
int reist_desktop_channels_control(reist_desktop_channels *s,reist_graphical_control *out) {
    if(!s || !out)return -22;
    if(s->phase!=1)return -116;
    if(!s->count){int r=channel_root(s);if(r)return r;}
    if(!s->count)return -11;
    *out=s->controls[s->head];channel_zero(&s->controls[s->head],sizeof(*out));
    s->head=(s->head+1)%4;s->count--;return 0;
}
int reist_desktop_channels_receive(void *context,reist_desktop_service_frame *out) {
    reist_desktop_channels *s=context;
    if(!s || !out)return -22;
    if(s->phase!=1)return -116;
    if(!s->reply_pending){int r=channel_root(s);if(r)return r;}
    if(!s->reply_pending)return -11;
    *out=s->reply;s->reply_pending=0;channel_zero(&s->reply,sizeof(s->reply));return 0;
}
int reist_desktop_channels_send(void *context,const reist_desktop_service_frame *q) {
    reist_desktop_channels *s=context;
    if(!s || !q)return -22;
    if(s->phase!=1)return -116;
    if(q->version!=1 || q->size!=2048 || q->root!=s->config.root ||
       q->desktop!=s->config.desktop || q->epoch!=s->config.epoch)return -22;
    uint64_t now;int r=channel_clock(s,&now);if(r)return r;
    if(q->deadline_ms<=now || q->deadline_ms-now>1000)return -110;
    x86os_ipc_bulk_message_t m={0};m.version=2;m.struct_size=sizeof(m);m.length=sizeof(*q);
    channel_copy(m.payload,q,sizeof(*q));
    int64_t result=s->config.call(s->config.context,REIST_X64_SYS_IPC_SEND_TIMEOUT,
        s->config.root_endpoint,(uintptr_t)&m,0);
    if(!result || result==-11)return (int)result;
    return channel_fail(s,result>0 || result<INT32_MIN?-5:(int)result);
}
int reist_desktop_channels_input(reist_desktop_channels *s) {
    if(!s || s->phase!=1)return -116;
    for(unsigned n=0;n<8;n++) {
        uint64_t now;int r=channel_clock(s,&now);if(r)return r;
        x86os_ipc_bulk_message_t m;r=channel_read(s,s->config.input_endpoint,&m);
        if(r==-11)return 0;
        if(r)return channel_fail(s,r);
        if(m.version!=1 || m.length!=64)return channel_fail(s,-71);
        reist_input_event_v1 e;channel_copy(&e,m.payload,sizeof(e));
        r=reist_desktop_input_push(s->config.input,&e,now);if(r)return channel_fail(s,r);
    }
    return 0;
}
static int channel_application_fail(reist_desktop_channels *s,unsigned slot,int error) {
    s->application_failed[slot]=1;return error;
}
int reist_desktop_channels_surface(reist_desktop_channels *s,unsigned slot,x86os_ipc_message_t *out) {
    if(!s || !out || slot>=2)return -22;
    if(s->phase!=1 || s->application_failed[slot] || s->application_closed[slot])return -116;
    for(unsigned n=0;n<8;n++) {
        uint64_t now;int r=channel_clock(s,&now);if(r)return r;
        x86os_ipc_bulk_message_t m;r=channel_read(s,s->config.application_endpoints[slot],&m);
        if(r==-11)return r;
        if(r)return channel_application_fail(s,slot,r);
        if(m.version!=1)return channel_application_fail(s,slot,-71);
        r=reist_graphical_charge(&s->application_rate[slot],now,128);
        if(r)return channel_application_fail(s,slot,r);
        if(m.length==64) {
            reist_graphical_control c;channel_copy(&c,m.payload,sizeof(c));
            if(c.version!=1 || c.size!=64 || c.type!=REIST_GRAPHICAL_HEALTH || c.role!=slot+2 ||
               c.epoch!=s->config.epoch || c.owner!=s->config.children[slot] ||
               s->health_sequence[slot]==UINT64_MAX || c.sequence!=s->health_sequence[slot]+1 ||
               c.endpoint || c.flags!=1 || c.value || c.reserved)return channel_application_fail(s,slot,-71);
            s->health_sequence[slot]=c.sequence;s->health_ms[slot]=now;continue;
        }
        uint32_t header[2];channel_copy(header,m.payload,sizeof(header));
        if(m.length!=124 || header[0]!=6 || header[1]!=124)return channel_application_fail(s,slot,-71);
        channel_copy(out,&m,sizeof(*out));return 0;
    }
    return -11;
}

int reist_desktop_channels_recovery_control(reist_desktop_channels *s,const reist_graphical_control *message,uint64_t now) {
    if(!s || !message)return -22;
    if(s->phase!=1 || !s->frontend_ready)return -116;
    reist_graphical_control q=*message;
    if(q.version!=1 || q.size!=64 || q.epoch!=s->config.epoch || q.reserved)return -71;
    if(now<s->previous || now>INT64_MAX-REIST_GRAPHICAL_START_MS)return -84;
        if(q.role<2 || q.role>3 || q.flags || q.value)return -71;
        unsigned slot=q.role-2;
        if(q.type==REIST_GRAPHICAL_CLIENT_REAPED) {
            if(q.sequence!=2 || q.endpoint || s->recovery[slot]!=REIST_DESKTOP_RECOVERY_WAIT_REAP ||
               q.owner!=s->recovery_old[slot] || now>=s->recovery_end[slot])return -116;
            if(now>INT64_MAX-REIST_GRAPHICAL_START_MS)return -75;
            s->recovery_end[slot]=now+REIST_GRAPHICAL_START_MS;
            s->recovery[slot]=REIST_DESKTOP_RECOVERY_REAPED;
        } else if(q.type==REIST_GRAPHICAL_BIND) {
            if(q.sequence!=1 || s->recovery[slot]!=REIST_DESKTOP_RECOVERY_WAIT_BIND ||
               q.endpoint!=s->recovery_endpoint[slot] || (uint32_t)q.owner!=slot+6 ||
               q.owner>>32<=s->recovery_old[slot]>>32 ||
               q.owner>>32<=s->config.children[1-slot]>>32 || q.owner>>32>0x7ffffffe ||
               now>=s->recovery_end[slot])return -116;
            s->recovery_owner[slot]=q.owner;
            s->recovery[slot]=REIST_DESKTOP_RECOVERY_BIND;
        } else return -71;
    return 0;
}
static int recovery_send(reist_desktop_channels *s,uint32_t endpoint,const reist_graphical_control *q) {
    x86os_ipc_message_t m={0};m.version=1;m.struct_size=sizeof(m);m.length=sizeof(*q);
    channel_copy(m.payload,q,sizeof(*q));
    int64_t r=s->config.call(s->config.context,REIST_X64_SYS_IPC_SEND_TIMEOUT,endpoint,(uintptr_t)&m,0);
    return r>0 || r<INT32_MIN?-5:(int)r;
}
static int frontend_recover_step(desktop_surface_runtime_t *runtime,desktop_surface_manager_t *manager) {
    reist_desktop_channels *s=reist_desktop_platform_channels();
    if(!s || !runtime || !manager || s->phase!=1)return -116;
    for(unsigned n=0;n<2;n++) {
        unsigned phase=s->recovery[n];
        if(!phase || phase==REIST_DESKTOP_RECOVERY_WAIT_REAP)continue;
        uint64_t now;int r=channel_clock(s,&now);if(r)return r;
        if(now>=s->recovery_end[n])return -110;
        desktop_surface_runtime_client_t *c=&runtime->clients[n];
        if(phase==REIST_DESKTOP_RECOVERY_REAPED) {
            if(!s->application_closed[n] || c->active==DESKTOP_SURFACE_RUNTIME_BOUND ||
               (c->owner.pid && c->owner.pid!=(uint32_t)(s->recovery_old[n]>>32)))return -116;
            uint32_t ep=0;
            int64_t created=s->config.call(s->config.context,REIST_X64_SYS_IPC_CREATE,(uintptr_t)&ep,0,0);
            if(created)return created<0 && created>=-4095?(int)created:-5;
            if(!ep || ep==s->config.root_endpoint || ep==s->config.input_endpoint ||
               ep==s->config.application_endpoints[1-n])return -71;
            s->recovery_endpoint[n]=ep;channel_zero(c,sizeof(*c));
            s->recovery[n]=phase=REIST_DESKTOP_RECOVERY_HELLO;
        }
        reist_graphical_control q={1,64,REIST_GRAPHICAL_HELLO,n+2,s->config.epoch,1,
            s->recovery_old[n],s->recovery_endpoint[n],0,0,0};
        if(phase==REIST_DESKTOP_RECOVERY_HELLO) {
            r=recovery_send(s,s->config.root_endpoint,&q);if(r==-11)continue;if(r)return r;
            s->recovery[n]=REIST_DESKTOP_RECOVERY_WAIT_BIND;continue;
        }
        if(phase==REIST_DESKTOP_RECOVERY_BIND) {
            uint64_t owner=s->recovery_owner[n];
            int64_t delegated=s->config.call(s->config.context,REIST_X64_SYS_IPC_DELEGATE,
                s->recovery_endpoint[n],owner>>32,3);
            if(delegated)return delegated<0 && delegated>=-4095?(int)delegated:-5;
            r=reist_desktop_platform_replace(s->recovery_old[n],owner);if(r)return r;
            s->config.children[n]=owner;s->config.application_endpoints[n]=s->recovery_endpoint[n];
            channel_zero(&s->application_rate[n],sizeof(s->application_rate[n]));
            s->health_sequence[n]=s->health_ms[n]=0;
            s->application_failed[n]=s->application_closed[n]=0;
            c->owner=(reist_gui_surface_owner_t){(uint32_t)(owner>>32),(uint32_t)(owner>>32)};
            c->endpoint=s->recovery_endpoint[n];c->active=DESKTOP_SURFACE_RUNTIME_RESERVED;
            s->recovery[n]=phase=REIST_DESKTOP_RECOVERY_APP_HELLO;
        }
        if(phase==REIST_DESKTOP_RECOVERY_APP_HELLO) {
            q.owner=s->config.children[n];
            r=recovery_send(s,c->endpoint,&q);if(r==-11)continue;if(r)return r;
            c->active=DESKTOP_SURFACE_RUNTIME_BOUND;
            s->recovery[n]=phase=REIST_DESKTOP_RECOVERY_BOUND;
        }
        if(phase==REIST_DESKTOP_RECOVERY_BOUND) {
            q.type=REIST_GRAPHICAL_BOUND;q.owner=s->config.children[n];
            r=recovery_send(s,s->config.root_endpoint,&q);if(r==-11)continue;if(r)return r;
            s->recovery[n]=REIST_DESKTOP_RECOVERY_WAIT_READY;
        }
    }
    return 0;
}

int reist_desktop_frontend_recover(desktop_surface_runtime_t *runtime,desktop_surface_manager_t *manager) {
    reist_desktop_channels *s=reist_desktop_platform_channels();
    if(!s || s->phase!=1)return -116;
    int r=frontend_recover_step(runtime,manager);
    return r?channel_fail(s,r):0;
}

static int handshake_hex(const char *text,uint32_t *out) {
    if(!text)return -22;
    uint32_t value=0;
    for(unsigned n=0;n<8;n++) {
        unsigned c=(unsigned char)text[n];
        unsigned digit=c>='0' && c<='9'?c-'0':c>='a' && c<='f'?c-'a'+10:16;
        if(digit>15)return -22;
        value=value<<4|digit;
    }
    if(text[8])return -22;
    *out=value;return 0;
}
static int handshake_pause(reist_desktop_channels *s,uint64_t end) {
    uint64_t now;int r=channel_clock(s,&now);if(r)return r;
    if(now>=end)return -110;
    unsigned delay=end-now<10?(unsigned)(end-now):10;
    int64_t result=s->config.call(s->config.context,REIST_X64_SYS_SLEEP_MS,delay,0,0);
    return result>0 || result<INT32_MIN?-5:(int)result;
}
static int handshake_send(reist_desktop_channels *s,uint64_t end,const reist_graphical_control *q) {
    x86os_ipc_message_t m={0};m.version=1;m.struct_size=sizeof(m);m.length=sizeof(*q);
    channel_copy(m.payload,q,sizeof(*q));
    for(unsigned n=0;n<300;n++) {
        uint64_t now;int r=channel_clock(s,&now);if(r)return r;
        if(now>=end)return -110;
        unsigned timeout=end-now<100?(unsigned)(end-now):100;
        int64_t result=s->config.call(s->config.context,REIST_X64_SYS_IPC_SEND_TIMEOUT,
            s->config.root_endpoint,(uintptr_t)&m,timeout);
        if(!result)return 0;
        /* CREATE publishes before root can delegate its control endpoint. */
        if(result!=-11 && !(result==-9 && q->type==REIST_GRAPHICAL_HELLO))
            return result>0 || result<INT32_MIN?-5:(int)result;
        r=handshake_pause(s,end);if(r)return r;
    }
    return -110;
}
int reist_desktop_handshake_close(reist_desktop_handshake_result *s) {
    if(!s || !s->channels.call)return -22;
    uint32_t *endpoints[3]={&s->channels.input_endpoint,
        &s->channels.application_endpoints[0],&s->channels.application_endpoints[1]};
    int failure=0;
    for(unsigned n=3;n>0;n--) {
        uint32_t *ep=endpoints[n-1];if(!*ep)continue;
        int64_t r=s->channels.call(s->channels.context,REIST_X64_SYS_IPC_CLOSE,*ep,0,0);
        if(r)failure=-5;else *ep=0;
    }
    if(!failure)channel_zero(&s->input,sizeof(s->input));
    return failure;
}
int reist_desktop_handshake(int argc,char **argv,
    int64_t (*call)(void *,unsigned,uint64_t,uint64_t,uint64_t),void *context,
    reist_desktop_handshake_result *out) {
    if(argc!=8 || !argv || !argv[0] || !call || !out)return -22;
    const unsigned char *bytes=(const unsigned char *)out;
    for(unsigned n=0;n<sizeof(*out);n++)if(bytes[n])return -22;
    uint32_t ep,peer,eh,el,dh,dl;
    if(handshake_hex(argv[1],&ep) || handshake_hex(argv[2],&peer) ||
       handshake_hex(argv[3],&eh) || handshake_hex(argv[4],&el) ||
       handshake_hex(argv[5],&dh) || handshake_hex(argv[6],&dl) ||
       !ep || !peer || peer>0x7ffffffe || !argv[7] || !argv[7][0] || argv[7][1])return -22;
    uint64_t epoch=(uint64_t)eh<<32|el,end=(uint64_t)dh<<32|dl;
    int64_t pid=call(context,REIST_X64_SYS_GETPID,0,0,0);
    if(pid<=peer || pid>0x7ffffffe || !epoch || epoch>INT64_MAX)return -22;
    reist_desktop_channels transport={0};
    transport.config.call=call;transport.config.context=context;transport.config.root_endpoint=ep;
    transport.phase=1;
    uint64_t now;int result=channel_clock(&transport,&now);if(result)return result;
    if(end<=now || end-now>REIST_GRAPHICAL_START_MS || end>INT64_MAX-500)return -22;
    if(argv[7][0]=='s') {
        /* Private startup-stall diagnostic: the original deadline remains
         * authoritative, with no endpoints or READY published. */
        for(unsigned turn=0;turn<=REIST_GRAPHICAL_START_MS/10;turn++) {
            result=handshake_pause(&transport,end);
            if(result)return result;
        }
        return -110;
    }
    reist_desktop_handshake_result built={0};
    built.deadline=end;built.mode=(unsigned char)argv[7][0];
    built.channels.call=call;built.channels.context=context;built.channels.root_endpoint=ep;
    built.channels.root=(uint64_t)peer<<32;built.channels.desktop=(uint64_t)pid<<32|4;
    built.channels.epoch=epoch;
    built.channels.start_deadline_ms=end;
    uint32_t *endpoints[3]={&built.channels.input_endpoint,
        &built.channels.application_endpoints[0],&built.channels.application_endpoints[1]};
    uint64_t owners[3]={0};unsigned bound=0;
    for(unsigned n=0;n<3;n++) {
        result=channel_clock(&transport,&now);if(result)goto fail;
        if(now>=end){result=-110;goto fail;}
        int64_t r=call(context,REIST_X64_SYS_IPC_CREATE,(uintptr_t)endpoints[n],0,0);
        if(r || !*endpoints[n]){*endpoints[n]=0;result=r<0 && r>=INT32_MIN?(int)r:-5;goto fail;}
        if(*endpoints[n]==ep){*endpoints[n]=0;result=-84;goto fail;}
        for(unsigned k=0;k<n;k++)if(*endpoints[k]==*endpoints[n]){*endpoints[n]=0;result=-84;goto fail;}
    }
    for(unsigned n=0;n<3;n++) {
        reist_graphical_control hello={1,64,REIST_GRAPHICAL_HELLO,n+1,epoch,1,0,*endpoints[n],0,0,0};
        result=handshake_send(&transport,end,&hello);if(result)goto fail;
    }
    for(unsigned turn=0;turn<300;turn++) {
        result=channel_clock(&transport,&now);if(result)goto fail;
        if(now>=end){result=-110;goto fail;}
        x86os_ipc_bulk_message_t m;result=channel_read(&transport,ep,&m);
        if(result==-11){result=handshake_pause(&transport,end);if(result)goto fail;continue;}
        if(result)goto fail;
        if(m.version!=1 || m.length!=64){result=-71;goto fail;}
        reist_graphical_control q;channel_copy(&q,m.payload,sizeof(q));
        if(q.version!=1 || q.size!=64 || q.epoch!=epoch || q.sequence!=1 || q.reserved) {
            result=-71;goto fail;
        }
        if(q.type==REIST_GRAPHICAL_BIND) {
            if(q.role<1 || q.role>3 || q.flags || q.value ||
               (uint32_t)q.owner!=q.role+4 || q.owner>>32<=(uint64_t)pid ||
               q.owner>>32>0x7ffffffe || bound&(1U<<q.role) || q.endpoint!=*endpoints[q.role-1]) {
                result=-71;goto fail;
            }
            for(unsigned n=0;n<3;n++)if(owners[n] && owners[n]>>32==q.owner>>32){result=-71;goto fail;}
            int64_t r=call(context,REIST_X64_SYS_IPC_DELEGATE,q.endpoint,q.owner>>32,q.role==1?1:3);
            if(r){result=r>0 || r<INT32_MIN?-5:(int)r;goto fail;}
            owners[q.role-1]=q.owner;bound|=1U<<q.role;q.type=REIST_GRAPHICAL_BOUND;
            result=handshake_send(&transport,end,&q);if(result)goto fail;
            continue;
        }
        if(q.type!=REIST_GRAPHICAL_READY || q.role || bound!=14 || q.owner!=built.channels.root ||
           q.endpoint || q.flags!=31 || !q.value || q.value>INT64_MAX) {result=-71;goto fail;}
        result=channel_clock(&transport,&now);if(result)goto fail;
        if(now>=end){result=-110;goto fail;}
        result=reist_desktop_input_bind(&built.input,built.channels.desktop,owners[0],q.value,now);
        if(result)goto fail;
        built.channels.children[0]=owners[1];built.channels.children[1]=owners[2];
        *out=built;out->channels.input=&out->input;return 0;
    }
    result=-110;
fail:
    if(reist_desktop_handshake_close(&built))return -5;
    return result;
}

typedef struct {
    reist_desktop_handshake_result handshake;
    reist_desktop_channels channels;
    reist_desktop_service_client service;
    void *context;
    int64_t (*call)(void *,unsigned,uint64_t,uint64_t,uint64_t);
    uint64_t previous,heartbeat,reports[4],wait_pump_ms;
    unsigned ready,stopped,failed_apps,progress,heartbeat_next;
    int failure;
} desktop_launch_state;
_Static_assert(sizeof(desktop_launch_state)<16384,"bounded native startup context");
static int launch_clock(void *context,uint64_t *out) {
    desktop_launch_state *s=context;
    int64_t now=s->call(s->context,REIST_X64_SYS_MONOTONIC_MS,0,0,0);
    if(now<0 || (uint64_t)now<s->previous || now>INT64_MAX-REIST_GRAPHICAL_START_MS)return -84;
    *out=s->previous=(uint64_t)now;return 0;
}
static void launch_failed(void *context,int error) {
    desktop_launch_state *s=context;
    if(!s->failure) {
        s->failure=error<0?error:-5;
        char message[]="DESKTOP_ADAPTER_ERROR 00000000 00000000000000000000000000000000\n";
        _Static_assert(sizeof(message)-1<=64,"native console write bound");
        uint64_t values[2]={s->previous,s->handshake.deadline};
        const char digits[]="0123456789abcdef";
        unsigned value=(unsigned)s->failure;
        for(unsigned n=0;n<8;n++)message[sizeof("DESKTOP_ADAPTER_ERROR ")-1+n]=digits[(value>>(28-4*n))&15];
        for(unsigned field=0;field<2;field++)for(unsigned n=0;n<16;n++)
            message[31+field*16+n]=digits[(values[field]>>(60-4*n))&15];
        /* One bounded best-effort raw diagnostic: the platform has already
         * latched failure, so its normal text adapter is unavailable. */
        (void)s->call(s->context,REIST_X64_SYS_WRITE,1,(uintptr_t)message,sizeof(message)-1);
    }
}
static int64_t launch_call(void *context,unsigned operation,uint64_t a,uint64_t b,uint64_t c) {
    desktop_launch_state *s=context;return s->call(s->context,operation,a,b,c);
}
static int launch_send(desktop_launch_state *s,unsigned type,unsigned role,unsigned flags) {
    if(role>=4)return -22;
    uint64_t now;int r=launch_clock(s,&now);if(r)return r;
    uint64_t owner=role==0?s->handshake.channels.desktop:role==1?s->handshake.input.driver:
        s->channels.config.children[role-2];
    if(s->reports[role]==UINT64_MAX)return -75;
    unsigned timeout=100;
    if(!s->ready) {
        if(now>=s->handshake.deadline)return -110;
        if(s->handshake.deadline-now<timeout)timeout=(unsigned)(s->handshake.deadline-now);
    }
    uint64_t sequence=type==REIST_GRAPHICAL_READY || type==REIST_GRAPHICAL_STOP?1:s->reports[role]+1;
    uint32_t endpoint=0;
    if(type==REIST_GRAPHICAL_HEALTH && role)
        endpoint=role==1?s->handshake.channels.input_endpoint:s->channels.config.application_endpoints[role-2];
    reist_graphical_control q={1,64,type,role,s->handshake.channels.epoch,sequence,owner,
        endpoint,flags,0,0};
    x86os_ipc_message_t m={0};m.version=1;m.struct_size=sizeof(m);m.length=sizeof(q);
    channel_copy(m.payload,&q,sizeof(q));
    int64_t sent=s->call(s->context,REIST_X64_SYS_IPC_SEND_TIMEOUT,
        s->handshake.channels.root_endpoint,(uintptr_t)&m,timeout);
    if(sent)return sent>0 || sent<INT32_MIN?-5:(int)sent;
    if(type!=REIST_GRAPHICAL_READY && type!=REIST_GRAPHICAL_STOP)s->reports[role]=sequence;
    return 0;
}
static int launch_report(void *context,unsigned operation,unsigned value) {
    desktop_launch_state *s=context;
    if(s->failure)return s->failure;
    if(operation==X86OS_REIST_REPORT_SELF_TEST)return value==1 && s->channels.phase==1?0:-71;
    if(operation==X86OS_REIST_REPORT_PROGRESS) {
        if(!value || value<=s->progress)return -71;
        s->progress=value;
        if(!s->ready) {
            /* Fixed startup work must share the admitted64-sample windows
             * with input/services. Yield between completed bounded phases;
             * never extend the original absolute startup deadline. */
            uint64_t now;int r=launch_clock(s,&now);if(r)return r;
            if(now>=s->handshake.deadline || s->handshake.deadline-now<=50)return -110;
            int64_t slept=s->call(s->context,REIST_X64_SYS_SLEEP_MS,50,0,0);
            if(slept)return slept<0 && slept>=-4095?(int)slept:-5;
            uint64_t after;r=launch_clock(s,&after);if(r)return r;
            if(after<=now)return -84;
            if(after>=s->handshake.deadline)return -110;
        }
        return 0;
    }
    if(operation!=X86OS_REIST_REPORT_SERVICE_READY || value!=1 || s->ready)return -71;
    int r=launch_send(s,REIST_GRAPHICAL_READY,0,31);if(r)return r;
    r=launch_clock(s,&s->heartbeat);if(r)return r;
    s->ready=1;return 0;
}
static int launch_pump(void *context) {
    desktop_launch_state *s=context;
    if(s->failure)return s->failure;
    uint64_t now;int r=launch_clock(s,&now);if(r)return r;
    if(!s->ready && now>=s->handshake.deadline)return -110;
    for(unsigned n=0;n<4;n++) {
        reist_graphical_control q;r=reist_desktop_channels_control(&s->channels,&q);
        if(r==-11)break;
        if(r)return r;
        if(q.type==REIST_GRAPHICAL_STOP && !q.role && q.sequence==2 &&
           q.owner==s->handshake.channels.root && !q.endpoint && !q.flags && !q.value) {
            s->stopped=1;return -125;
        }
        r=channel_clock(&s->channels,&now);if(r)return r;
        r=reist_desktop_channels_recovery_control(&s->channels,&q,now);if(r)return r;
        if(q.type==REIST_GRAPHICAL_BIND)s->reports[q.role]=0;
    }
    if(!s->ready)return 0;
    if(!s->handshake.input.sequence || now<s->handshake.input.healthy_ms ||
       now-s->handshake.input.healthy_ms>=1000)return -110;
    for(unsigned n=0;n<2;n++) {
        if(s->channels.recovery[n]) {
            if(s->channels.recovery_end[n] && now>=s->channels.recovery_end[n])return -110;
            if(s->channels.recovery[n]==REIST_DESKTOP_RECOVERY_WAIT_READY && s->channels.recovery_ready[n]) {
                s->channels.recovery[n]=0;s->channels.recovery_ready[n]=0;
                s->failed_apps&=~(1U<<n);
            } else continue;
        }
        if(!s->channels.application_closed[n] && (!s->channels.health_sequence[n] ||
           now<s->channels.health_ms[n] || now-s->channels.health_ms[n]>=1000))
            s->channels.application_failed[n]=1;
        if(s->channels.application_closed[n] && !(s->failed_apps&(1U<<n))) {
            r=launch_send(s,REIST_GRAPHICAL_FAILED,n+2,s->channels.application_failed[n]?(unsigned)-71:0);if(r)return r;
            s->failed_apps|=1U<<n;
            if(s->channels.application_failed[n]) {
                if(now>INT64_MAX-REIST_GRAPHICAL_START_MS)return -75;
                s->channels.recovery_old[n]=s->channels.config.children[n];
                s->channels.recovery_end[n]=now+REIST_GRAPHICAL_START_MS;
                s->channels.recovery[n]=REIST_DESKTOP_RECOVERY_WAIT_REAP;
            }
        }
    }
    if(now-s->heartbeat>=250 || s->heartbeat_next) {
        /* One normal scheduling handoff per pump, then return to input.
         * Every role retains the original health deadline and round rate. */
        if(!s->heartbeat_next){s->heartbeat_next=1;s->heartbeat=now;}
        for(unsigned role=s->heartbeat_next-1;role<4;role++) {
            s->heartbeat_next=role+2;
            if(role>=2 && ((s->failed_apps&(1U<<(role-2))) ||
               s->channels.application_failed[role-2] || s->channels.application_closed[role-2] ||
               s->channels.recovery[role-2]))continue;
            r=launch_send(s,REIST_GRAPHICAL_HEALTH,role,1);if(r)return r;
            if(s->heartbeat_next>4)s->heartbeat_next=0;
            return 0;
        }
        s->heartbeat_next=0;
    }
    return 0;
}
static int launch_service_send(void *context,const reist_desktop_service_frame *q) {
    desktop_launch_state *s=context;return reist_desktop_channels_send(&s->channels,q);
}
static int launch_service_receive(void *context,reist_desktop_service_frame *q) {
    desktop_launch_state *s=context;
    if(!s->ready && !s->channels.reply_pending) {
        uint64_t now;int r=launch_clock(s,&now);if(r)return r;
        uint64_t end=s->service.request.deadline_ms;
        if(end>s->handshake.deadline)end=s->handshake.deadline;
        if(now>=end)return -110;
        unsigned wait=end-now<100?(unsigned)(end-now):100;
        r=channel_root_wait(&s->channels,wait);if(r)return r;
        if(!s->channels.reply_pending)return -11;
    }
    return reist_desktop_channels_receive(&s->channels,q);
}
static int launch_wait(void *context,unsigned delay) {
    desktop_launch_state *s=context;
    if(!delay || delay>10)return -22;
    if(s->previous<s->wait_pump_ms)return -84;
    /* Service exchange already checks the clock and root receive on every
     * attempt. Before READY, avoid a second full pump on every10ms wait. */
    if(s->ready || !s->wait_pump_ms || s->previous-s->wait_pump_ms>=50) {
        int r=reist_desktop_platform_pump();if(r)return r;
        s->wait_pump_ms=s->previous;
    }
    int64_t result=s->call(s->context,REIST_X64_SYS_SLEEP_MS,delay,0,0);
    return result>0 || result<INT32_MIN?-5:(int)result;
}
static int launch_mouse(void *context,x86os_mouse_event_t *out) {
    desktop_launch_state *s=context;return reist_desktop_input_mouse(&s->handshake.input,out);
}
static int launch_key(void *context) {
    desktop_launch_state *s=context;return reist_desktop_input_key(&s->handshake.input);
}
int reist_desktop_launch(int argc,char **argv,const unsigned char *font,size_t font_bytes,
        int (*entry)(int,char **),int64_t (*call)(void *,unsigned,uint64_t,uint64_t,uint64_t),void *context) {
    if(!call || !entry || !font || font_bytes!=4096 || argc!=8 || !argv || !argv[0])return -22;
    int64_t allocation=call(context,REIST_X64_SYS_MALLOC,sizeof(desktop_launch_state),0,0);
    if(allocation<=0)return -12;
    desktop_launch_state *s=(void *)(uintptr_t)allocation;channel_zero(s,sizeof(*s));
    s->call=call;s->context=context;
    int result=reist_desktop_handshake(argc,argv,call,context,&s->handshake);
    if(result)goto done;
    uint64_t now;result=launch_clock(s,&now);if(result)goto done;
    result=reist_desktop_channels_init(&s->channels,&s->handshake.channels,now);if(result)goto done;
    reist_desktop_service_client_config service={s->handshake.channels.root,s->handshake.channels.desktop,
        s->handshake.channels.epoch,s,launch_clock,launch_service_send,launch_service_receive,launch_wait,launch_failed};
    result=reist_desktop_service_client_init(&s->service,&service);if(result)goto done;
    reist_desktop_platform_config platform={&s->service,s,launch_call,launch_pump,
        launch_mouse,launch_key,launch_report,launch_failed,&s->channels};
    reist_desktop_startup_config startup={platform,font,font_bytes,
        {s->handshake.channels.children[0],s->handshake.channels.children[1]},entry};
    char *frontend_args[]={argv[0]};
    result=reist_desktop_startup_run(&startup,1,frontend_args);
    if(s->failure)result=s->stopped && s->failure==-125?0:s->failure;
    if(!result && !s->stopped)result=launch_send(s,REIST_GRAPHICAL_STOP,0,0);
done:
    reist_desktop_service_client_detach(&s->service);
    if(s->handshake.channels.call) {
        /* Successful ordinary runtime close transferred no remaining ownership
         * back to startup. Preserve failed closes for this final bounded pass. */
        for(unsigned n=0;n<2;n++) {
            if(s->channels.application_closed[n] && (!s->channels.recovery_endpoint[n] ||
               s->channels.recovery_endpoint[n]==s->channels.config.application_endpoints[n]))
                s->handshake.channels.application_endpoints[n]=0;
            else if(s->channels.recovery_endpoint[n])
                s->handshake.channels.application_endpoints[n]=s->channels.recovery_endpoint[n];
        }
        if(reist_desktop_handshake_close(&s->handshake))result=-5;
    }
    channel_zero(s,sizeof(*s));
    if(call(context,REIST_X64_SYS_FREE,(uintptr_t)s,0,0))result=-5;
    return result;
}

#ifdef REIST_NATIVE_DESKTOP_ENTRY
#include "full_desktop_font.h"
extern int reist_desktop_frontend_main(int,char **);
static int64_t desktop_entry_call(void *unused,unsigned operation,uint64_t a,uint64_t b,uint64_t c) {
    (void)unused;return reist_x64_syscall3(operation,a,b,c);
}
int main(int argc,char **argv) {
    int r=reist_desktop_launch(argc,argv,full_desktop_font,sizeof(full_desktop_font),
        reist_desktop_frontend_main,desktop_entry_call,0);
    return r<0?-r:r;
}
#endif
