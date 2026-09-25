/* Execute production slicing with a deterministic clipped pixel sink.
 * Full compositor scene equivalence remains a guest acceptance requirement. */
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct { int32_t x,y;uint32_t width,height; } desktop_rect_t;
typedef struct { unsigned unused; struct { unsigned active,paint_generation,presented_generation; } slots[8]; } x86os_display_info_t;
#define DESKTOP_SURFACE_CAPACITY 8
typedef x86os_display_info_t desktop_wm_t;
typedef x86os_display_info_t desktop_explorer_t;
typedef x86os_display_info_t desktop_surface_manager_t;
typedef x86os_display_info_t desktop_ui_state_t;
typedef struct { unsigned count;desktop_rect_t rects[8]; } desktop_dirty_region_t;
typedef struct { const x86os_display_info_t *display;desktop_rect_t clip;
    unsigned omitted_kind,omitted_window; } desktop_render_context_t;
#define DESKTOP_MOVE_CACHE_NONE 0U
#define DESKTOP_WM_NO_TARGET UINT32_MAX
static unsigned pixels[768][1024], expected[768][1024], checkpoints, fail_at, draws;
static int reist_desktop_platform_render_checkpoint(unsigned wait) {
    if(wait!=0 && wait!=50){fprintf(stderr,"startup wait %u\n",wait);return -110;}
    ++checkpoints;
    return checkpoints==fail_at?-110:0;
}
static uint64_t live_deadline;
static unsigned live_checkpoints;
static int reist_desktop_platform_live_checkpoint(unsigned wait,uint64_t end) {
    assert(end==live_deadline && end==1000);++live_checkpoints;
    return reist_desktop_platform_render_checkpoint(wait);
}
static void render_desktop_clip(const desktop_render_context_t *c,
    const desktop_wm_t *m,const desktop_explorer_t *e,
    const desktop_surface_manager_t *s,const desktop_ui_state_t *u) {
    (void)m;(void)e;(void)s;(void)u;++draws;
    assert(c->clip.height<=128 && c->omitted_kind==0 && c->omitted_window==UINT32_MAX);
    for(unsigned y=0;y<c->clip.height;y++)for(unsigned x=0;x<c->clip.width;x++) {
        int px=c->clip.x+(int)x,py=c->clip.y+(int)y;
        if(px>=0 && px<1024 && py>=0 && py<768)++pixels[py][px];
    }
}
static int x86os_display_frame_begin(uint32_t *serial) {
    assert(checkpoints==1 && fail_at!=1);*serial=1;return 0;
}
#include "render.inc"
static int render_start(const desktop_dirty_region_t *dirty) {
    uint32_t serial=0;
    int r=begin_native_startup_frame(&serial,live_deadline);if(r){assert(!serial);return r;}
    assert(serial==1);return render_native_startup(0,0,0,0,0,dirty,live_deadline);
}
#define REIST_NATIVE_FULL_DESKTOP 1
#define DESKTOP_EXPLORER_ICON_COUNT 9
#define DESKTOP_TRASH_ICON_COUNT 2
typedef struct { unsigned valid; } cache_entry;
typedef struct { unsigned type; } x86os_file_info_t;
static cache_entry desktop_file_icon_cache[9],desktop_trash_icon_cache[2];
static const char *desktop_file_icon_paths[9],*desktop_trash_icon_paths[2];
static int theme_status;static unsigned opens,progress;
static int x86os_stat(const char *path,x86os_file_info_t *out) {
    assert(!strcmp(path,"/usr/share/icons"));out->type=2;return theme_status;
}
static void desktop_icon_cache_load(cache_entry *entry,const char *path) {
    (void)path;entry->valid=1;++opens;
}
static int desktop_lifecycle_publish_progress(unsigned supervised,unsigned *sequence,uint64_t *heartbeat) {
    (void)supervised;(void)sequence;(void)heartbeat;++progress;return 0;
}
#include "icons.inc"
typedef struct { int status;unsigned clock_valid;uint64_t started_ms,finished_ms; } desktop_pointer_present_result_t;
typedef struct { unsigned key_count,mouse_count; } pending_native_input;
typedef struct { unsigned frontend_ready,phase; struct { pending_native_input *input; } config; } reist_desktop_channels;
static reist_desktop_channels channel;
static unsigned pointer_steps;
static int pointer_error,pump_error;
static int x86os_monotonic_ms(uint64_t *out){*out=100+pointer_steps;return 0;}
static int x86os_pointer_update(int32_t x,int32_t y,uint32_t visible){
    if(x!=536 || y!=396 || visible!=1 || pointer_steps)return -22;
    pointer_steps=1;return pointer_error;
}
reist_desktop_channels *reist_desktop_platform_channels(void){return &channel;}
int reist_desktop_platform_pump(void){return -95;}
int reist_desktop_display_service(void){if(pointer_steps!=1)return -22;pointer_steps=2;return pump_error;}
#include "pointer.inc"
static int pointer_tests(void){
    for(unsigned ready=0;ready<2;ready++)for(unsigned error=0;error<3;error++){
        channel.frontend_ready=ready;pointer_steps=0;
        pointer_error=error==1?-116:0;pump_error=error==2?-71:0;
        desktop_pointer_present_result_t r=desktop_pointer_present(536,396,1);
        unsigned pumped=ready && !pointer_error;
        if(pointer_steps!=(pumped?2U:1U) || r.status!=(pointer_error?pointer_error:pumped?pump_error:0) ||
           !r.clock_valid || r.finished_ms!=100+pointer_steps){
            fprintf(stderr,"pointer publish order ready=%u error=%u steps=%u\n",ready,error,pointer_steps);return 1;
        }
    }
    return 0;
}
typedef struct { unsigned active,slot; } desktop_surface_runtime_client_t;
typedef struct { desktop_surface_runtime_client_t clients[2]; } desktop_surface_runtime_t;
static unsigned runtime_probe,runtime_yields;
static unsigned flush_step,flush_cpu;
static int desktop_surface_runtime_poll(desktop_surface_runtime_t *runtime,desktop_surface_manager_t *surfaces) {
    (void)runtime;(void)surfaces;
    assert(flush_step==0 || (flush_cpu==1 && flush_step==2));flush_step++;return 0;
}
static int x86os_yield(void){if(runtime_probe){runtime_yields++;return 0;}assert(flush_step==1 && flush_cpu==1);flush_step++;return 0;}
static desktop_wm_t flush_manager;
static unsigned flush_keyboard;
static void native_surface_route_during_poll(void *wm,void *surfaces){(void)wm;(void)surfaces;}
static int desktop_surface_runtime_poll_routed(desktop_surface_runtime_t *r,
    desktop_surface_manager_t *s,void (*route)(void *,void *),void *context) {
    assert(route==(flush_keyboard?native_surface_route_during_poll:0));
    assert(context==&flush_manager);
    return desktop_surface_runtime_poll(r,s);
}
#include "flush.inc"
#include "damage.inc"
typedef struct { int bytes[12];unsigned head,count,blocked; } reist_desktop_input_state;
static unsigned batch_capacity,batch_sent;
static int reist_desktop_input_peek_key(reist_desktop_input_state *s) {
    return s->blocked || !s->count?-11:s->bytes[s->head];
}
static int reist_desktop_input_key(reist_desktop_input_state *s) {
    assert(s->count && !s->blocked);--s->count;return s->bytes[s->head++];
}
static unsigned enqueue_surface_keyboard(const desktop_wm_t *m,desktop_surface_manager_t *s,int key) {
    (void)m;(void)s;assert(key>=32 && key<=126);
    if(batch_sent==batch_capacity)return 0;
    ++batch_sent;return 1;
}
#include "batch.inc"
static void batch_tests(void) {
    reist_desktop_input_state input={{'a','b','c','d','e','f','g','h','i'},0,9,0};
    batch_capacity=12;batch_sent=0;
    native_surface_keyboard_batch(&input,0,0);
    assert(batch_sent==7 && input.head==7 && input.count==2);
    input.blocked=1;native_surface_keyboard_batch(&input,0,0);
    assert(batch_sent==7 && input.head==7);
    input.blocked=0;batch_capacity=7;native_surface_keyboard_batch(&input,0,0);
    assert(input.head==7 && input.count==2);
    batch_capacity=12;input.bytes[7]=27;native_surface_keyboard_batch(&input,0,0);
    assert(input.head==7 && input.count==2);
    input.bytes[7]='h';native_surface_keyboard_batch(&input,0,0);
    assert(input.count==0 && batch_sent==9);
}
#define DESKTOP_SURFACE_EINVAL -22
#define DESKTOP_SURFACE_RUNTIME_CAPACITY 2
#define DESKTOP_SURFACE_RUNTIME_BOUND 1
#define DESKTOP_SURFACE_RUNTIME_DRAIN_ROUNDS 16
#define X86OS_IPC_QUEUE_DEPTH 8
static unsigned poll_calls[2],event_count[2],sent_count[2],send_attempt[2],backpressure;
static unsigned send_order[32],send_count,paint_traffic;
static void poll_retiring_client(desktop_surface_runtime_client_t *c){(void)c;}
static void disconnect_client(desktop_surface_runtime_client_t *c,desktop_surface_manager_t *s){(void)s;c->active=0;}
static int poll_client(desktop_surface_runtime_client_t *c,desktop_surface_manager_t *s){
    (void)s;
    if(TEST_NATIVE_SURFACE_FAIR && event_count[c->slot] && !poll_calls[c->slot] && !send_attempt[c->slot]) {
        fprintf(stderr,"queued input waited behind paint polling\n");exit(1);
    }
    return paint_traffic && (poll_calls[c->slot]++%2)==0?1:0;
}
static int send_pending_input(desktop_surface_runtime_client_t *c,desktop_surface_manager_t *s){
    (void)s;unsigned n=c->slot;++send_attempt[n];
    if(backpressure && n==0)return -11;
    if(!event_count[n])return 0;
    --event_count[n];++sent_count[n];assert(send_count<32);send_order[send_count++]=n;return 1;
}
#define desktop_surface_runtime_poll actual_surface_runtime_poll
#define desktop_surface_runtime_poll_routed actual_surface_runtime_poll_routed
#if !TEST_NATIVE_SURFACE_FAIR
#undef REIST_NATIVE_FULL_DESKTOP
#endif
#if TEST_NATIVE_SURFACE_FAIR
static int reist_desktop_frontend_recover(desktop_surface_runtime_t *r,desktop_surface_manager_t *m) {
    assert(r && m);return 0;
}
#endif
#include "runtime.inc"
#undef desktop_surface_runtime_poll
#undef desktop_surface_runtime_poll_routed
static void runtime_fairness_tests(void){
    for(paint_traffic=0;paint_traffic<2;paint_traffic++)
    for(backpressure=0;backpressure<2;backpressure++){
        desktop_surface_runtime_t r={{{1,0},{1,1}}};desktop_surface_manager_t m={0};
        memset(poll_calls,0,sizeof(poll_calls));memset(sent_count,0,sizeof(sent_count));
        memset(send_attempt,0,sizeof(send_attempt));event_count[0]=event_count[1]=16;
        runtime_probe=1;runtime_yields=send_count=0;
        assert(!actual_surface_runtime_poll(&r,&m));runtime_probe=0;
        unsigned limit=TEST_NATIVE_SURFACE_FAIR?16:1;
        if(sent_count[0]!=(backpressure?0:limit) || sent_count[1]!=limit){
            fprintf(stderr,"input fairness full=%u paint=%u blocked=%u sent=%u/%u expected=%u\n",
                TEST_NATIVE_SURFACE_FAIR,paint_traffic,backpressure,sent_count[0],sent_count[1],limit);
            exit(1);
        }
        assert(event_count[0]==(backpressure?16:16-limit) && event_count[1]==16-limit);
        assert(runtime_yields==((TEST_NATIVE_SURFACE_FAIR || paint_traffic)?15U:0U));
        assert(r.clients[0].active && r.clients[1].active);
        for(unsigned i=0;i<send_count;i++)assert(send_order[i]==(backpressure?1:i%2));
    }
}
#if TEST_NATIVE_SURFACE_FAIR
static void route_pending(void *context,void *manager) {
    assert(context && manager);
    ++*(unsigned *)context;
    channel.config.input->key_count=0;
}
static void routed_rounds(void) {
    pending_native_input input={3,0};channel.phase=channel.frontend_ready=1;
    channel.config.input=&input;
    desktop_surface_runtime_t r={{{1,0},{1,1}}};desktop_surface_manager_t m={0};
    unsigned routed=0;paint_traffic=1;backpressure=0;
    memset(poll_calls,0,sizeof(poll_calls));memset(sent_count,0,sizeof(sent_count));
    event_count[0]=event_count[1]=16;runtime_probe=1;runtime_yields=send_count=0;
    assert(!actual_surface_runtime_poll_routed(&r,&m,route_pending,&routed));
    assert(routed==16 && !input.key_count && sent_count[0]==16 && sent_count[1]==16);
    assert(actual_surface_runtime_poll_routed(&r,&m,route_pending,0)==-22);
    runtime_probe=0;memset(&channel,0,sizeof(channel));
}
#endif
int main(void) {
    desktop_dirty_region_t small={1,{{0,0,1024,128}}};
    assert(!native_large_frame(&small));small.rects[0].height++;
    assert(native_large_frame(&small));
    live_deadline=1000;checkpoints=draws=live_checkpoints=0;
    assert(!render_start(&small) && live_checkpoints==3);
    for(unsigned y=0;y<129;y++)for(unsigned x=0;x<1024;x++)assert(pixels[y][x]==1);
    live_deadline=0;memset(pixels,0,sizeof(pixels));checkpoints=draws=0;

#if TEST_NATIVE_SURFACE_FAIR
    for(unsigned ready=0;ready<2;ready++) {
        desktop_surface_runtime_t runtime={{{1,0},{1,1}}};desktop_surface_manager_t m={0};
        m.slots[0].active=1;m.slots[0].paint_generation=1;
        channel.phase=1;channel.frontend_ready=ready;channel.config.input=0;
        memset(poll_calls,0,sizeof(poll_calls));memset(event_count,0,sizeof(event_count));
        paint_traffic=1;backpressure=0;runtime_probe=1;runtime_yields=0;
        if(actual_surface_runtime_poll(&runtime,&m) || runtime_yields!=(ready?0:15) ||
           !poll_calls[0] || !poll_calls[1]) {
            fprintf(stderr,"committed frame waited behind drain yields ready=%u yields=%u\n",ready,runtime_yields);exit(1);
        }
    }
    runtime_probe=0;memset(&channel,0,sizeof(channel));
#endif
#if TEST_NATIVE_SURFACE_FAIR
    routed_rounds();
#endif
    runtime_fairness_tests();
    /* A complete fair round must return newly queued native input to the WM.
     * Neither startup nor inactive channels may change the legacy drain. */
    for(unsigned ready=0;ready<2;ready++)for(unsigned live=0;live<2;live++)
    for(unsigned mouse=0;mouse<2;mouse++) {
        pending_native_input pending={!mouse,mouse};
        channel.frontend_ready=ready;channel.phase=live;channel.config.input=&pending;
        desktop_surface_runtime_t r={{{1,0},{1,1}}};desktop_surface_manager_t m={0};
        memset(poll_calls,0,sizeof(poll_calls));memset(sent_count,0,sizeof(sent_count));
        event_count[0]=event_count[1]=16;paint_traffic=1;backpressure=0;
        runtime_probe=1;runtime_yields=send_count=0;
        assert(!actual_surface_runtime_poll(&r,&m));runtime_probe=0;
        unsigned shortened=TEST_NATIVE_SURFACE_FAIR && ready && live;
        unsigned limit=TEST_NATIVE_SURFACE_FAIR?(shortened?1:16):1;
        assert(sent_count[0]==limit && sent_count[1]==limit);
        assert(runtime_yields==(shortened?0:15));
        assert(pending.key_count==!mouse && pending.mouse_count==mouse);
        assert(r.clients[0].active && r.clients[1].active);
    }
    memset(&channel,0,sizeof(channel));
    flush_step=0;flush_cpu=1;
    assert(!native_surface_poll_before_input(0,0,1) && !flush_step);
    assert(!native_surface_poll_before_input(0,0,0) && flush_step==1);

    batch_tests();
    for(flush_keyboard=0;flush_keyboard<2;flush_keyboard++)
    for(flush_cpu=1;flush_cpu<=2;flush_cpu++) {
        flush_step=0;native_surface_input_flush(0,0,flush_cpu,&flush_manager,flush_keyboard);
        assert(flush_step==(flush_cpu==1?3U:1U));
    }
    for(unsigned pending=0;pending<2;pending++) {
        desktop_surface_manager_t ready_surface={0};
        ready_surface.slots[0].active=1;
        ready_surface.slots[0].paint_generation=2;
        ready_surface.slots[0].presented_generation=pending?1:2;
        flush_cpu=1;flush_keyboard=1;flush_step=0;
        native_surface_input_flush(0,&ready_surface,1,&flush_manager,1);
        assert(flush_step==(pending?1U:3U));
    }
    desktop_rect_t text_damage=native_surface_raster_damage((desktop_rect_t){12,48,296,1},320,192);
    assert(text_damage.x==12 && text_damage.y==48 && text_damage.width==296 && text_damage.height==16);
    text_damage=native_surface_raster_damage((desktop_rect_t){12,190,296,1},320,192);
    assert(text_damage.height==2);
    text_damage=native_surface_raster_damage((desktop_rect_t){0,0,320,192},320,192);
    assert(text_damage.height==192);
    text_damage=native_surface_raster_damage((desktop_rect_t){-1,0,1,1},320,192);
    assert(!text_damage.width && !text_damage.height);
    if(pointer_tests())return 1;
    desktop_dirty_region_t dirty={3,{{0,0,1024,768},{7,13,31,129},{-2,-1,8,7}}};
    for(unsigned n=0;n<dirty.count;n++) {
        desktop_rect_t r=dirty.rects[n];
        for(unsigned y=0;y<r.height;y++)for(unsigned x=0;x<r.width;x++) {
            int px=r.x+(int)x,py=r.y+(int)y;
            if(px>=0 && px<1024 && py>=0 && py<768)++expected[py][px];
        }
    }
    if(render_start(&dirty)){fprintf(stderr,"startup render failed\n");return 1;}
    assert(draws==9 && checkpoints==8 && !memcmp(pixels,expected,sizeof(pixels)));
    for(fail_at=1;fail_at<=8;fail_at++) {
        checkpoints=draws=0;
        assert(render_start(&dirty)==-110);
        const unsigned completed[]={0,0,1,2,3,4,5,6,9};
        assert(checkpoints==fail_at && draws==completed[fail_at]);
    }
    const int cases[]={-2,-13,0,-5};
    for(unsigned n=0;n<4;n++) {
        theme_status=cases[n];opens=progress=0;
        memset(desktop_file_icon_cache,1,sizeof(desktop_file_icon_cache));
        memset(desktop_trash_icon_cache,1,sizeof(desktop_trash_icon_cache));
        assert(!desktop_file_icon_cache_initialize(1,0,0));
        assert(opens==(n<2?0:11) && progress==(n<2?1:11));
        for(unsigned k=0;k<9;k++)assert(desktop_file_icon_cache[k].valid==(n>=2));
        for(unsigned k=0;k<2;k++)assert(desktop_trash_icon_cache[k].valid==(n>=2));
    }
    puts("NATIVE_RENDER_SLICES_OK");return 0;
}
