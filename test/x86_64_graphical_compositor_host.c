#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../userspace/gui/compositor/native_session.h"
#include "../userspace/gui/compositor/native_render.h"
#ifdef REIST_RENDER_EQUIVALENCE
#include "native_font.h"
static unsigned render_lookups;
int instrumented_window_at(const desktop_wm_t *wm,int32_t x,int32_t y) {
    render_lookups++;return desktop_wm_window_at(wm,x,y);
}
static int reference_inside(int x,int y,int rx,int ry,unsigned w,unsigned h) {
    return x>=rx && y>=ry && (unsigned)(x-rx)<w && (unsigned)(y-ry)<h;
}
static uint32_t reference_text_reference_pixel(const char *s,unsigned bytes,int x,int y,uint32_t fg,uint32_t bg) {
    if(x<0||y<0||y>=16||(unsigned)x/8>=bytes)return bg;
    unsigned c=(unsigned char)s[(unsigned)x/8];if(c>=128)c='?';
    return native_font[c*16+(unsigned)y]&(0x80U>>((unsigned)x%8))?fg:bg;
}
static uint32_t reference_paint(const desktop_surface_paint_command_t *commands,unsigned count,
                       int x,int y,uint32_t pixel) {
    for(unsigned n=0;n<count;n++) {
        const desktop_surface_paint_command_t *p=&commands[n];
        unsigned height=p->type==DESKTOP_SURFACE_PAINT_TEXT?16:p->rect.height;
        if(!reference_inside(x,y,p->rect.x,p->rect.y,p->rect.width,height))continue;
        if(p->type==DESKTOP_SURFACE_PAINT_FILL)pixel=p->foreground;
        else if(p->type==DESKTOP_SURFACE_PAINT_TEXT)
            pixel=reference_text_reference_pixel(p->text,p->text_length,x-p->rect.x,y-p->rect.y,p->foreground,p->background);
    }
    return pixel;
}
static uint32_t reference_pixel(const reist_native_compositor *c,int x,int y) {
    if(reference_inside(x,y,c->x,c->y,8,12) && (x==c->x||y==c->y||x-c->x==(y-c->y)/2))return 0xffffff;
    int at=desktop_wm_window_at(&c->wm,x,y);
    if(at<0 || at>=2) {
        if(y<28)return reference_text_reference_pixel("REIST OS  |  Alt+Tab: focus  Esc: shell",38,x-12,y-6,0xe2ecf5,0x172334);
        return 0x24374a;
    }
    const desktop_window_t *w=&c->wm.windows[at];
    unsigned active=c->wm.keyboard_focus==at;
    uint32_t frame=active?0x3b82b8:0x485563;
    int lx=x-w->x,ly=y-w->y;
    if(ly<24) {
        desktop_rect_t close=desktop_wm_close_rect(&c->wm,(unsigned)at);
        if(reference_inside(x,y,close.x,close.y,close.width,close.height))
            return reference_text_reference_pixel("x",1,x-close.x,y-close.y,0xffffff,0x973d40);
        const char *title=at?"Pointer pad":"Text pad";unsigned length=at?11:8;
        const reist_native_gui_client *client=&c->clients[at];
        if(client->active && client->surface.id) {
            const char *custom=c->surfaces.slots[client->surface.id-1].title;
            if(custom[0]){title=custom;length=0;while(length<REIST_GUI_SURFACE_PAINT_TEXT_CAPACITY && custom[length])length++;}
        }
        return reference_text_reference_pixel(title,length,lx-8,ly-4,0xffffff,frame);
    }
    if(lx<3||lx>=323||ly>=216)return frame;
    const reist_native_gui_client *client=&c->clients[at];
    if(!client->active || !client->surface.id)return 0x151c24;
    const desktop_surface_slot_t *surface=&c->surfaces.slots[client->surface.id-1];
    lx-=3;ly-=24;
    uint32_t color=reference_paint(surface->committed_paint,surface->committed_paint_count,lx,ly,0x151c24);
    color=reference_paint(surface->committed_overlay_paint,surface->committed_overlay_paint_count,lx,ly,color);
    color=reference_paint(surface->committed_dynamic_paint,surface->committed_dynamic_paint_count,lx,ly,color);
    return reference_paint(surface->committed_hover_paint,surface->committed_hover_paint_count,lx,ly,color);
}
#endif
static reist_native_compositor c;
static reist_native_renderer renderer;
static uint32_t framebuffer[640*480];
static const uint64_t driver=8ULL<<32|5,compositor=7ULL<<32|4;
static reist_gui_surface_message_t request(unsigned type) {
    reist_gui_surface_message_t q={0};q.protocol_version=6;q.message_size=sizeof(q);q.type=type;return q;
}
static void client(unsigned n,unsigned generation) {
    assert(!reist_native_client_bind(&c,n,(uint64_t)generation<<32|(6+n),100+n));
    reist_gui_surface_message_t q=request(REIST_GUI_SURFACE_CREATE),reply;
    q.flags=REIST_GUI_SURFACE_ROLE_TOPLEVEL;q.width=320;q.height=192;
    assert(!reist_native_surface(&c,n,&q,&reply,10));
    assert(reply.type==REIST_GUI_SURFACE_CONFIGURE && reply.width==320 && reply.height==192);
    q=request(REIST_GUI_SURFACE_ACK_CONFIGURE);q.surface=reply.surface;q.serial=reply.serial;
    assert(!reist_native_surface(&c,n,&q,&reply,11));
}
static reist_input_event_v1 event(unsigned type,uint64_t seq) {
    reist_input_event_v1 e={2,64,type,0,driver,compositor,3,seq,0,0,0,0};return e;
}
static void motion(uint64_t sequence,int dx,int dy,unsigned buttons) {
    reist_input_event_v1 e=event(REIST_INPUT_POINTER,sequence);e.dx=dx;e.dy=dy;e.buttons=buttons;
    assert(!reist_native_input(&c,&e,20+sequence));
}
static unsigned render(void) {
#ifdef REIST_RENDER_EQUIVALENCE
    render_lookups=0;
#endif
    reist_native_render_damage(&renderer,&c);unsigned count=0;
    for(unsigned n=0;n<81;n++) {
        unsigned x,y,w,h;int r=reist_native_render_tile(&renderer,&c,&x,&y,&w,&h);
        assert(r>=0);if(!r){
#ifdef REIST_RENDER_EQUIVALENCE
            assert(render_lookups<=160);
#endif
            return count;
        }
        assert(x+w<=640&&y+h<=480&&w==64&&(h==64||h==32));
        for(unsigned py=0;py<h;py++)for(unsigned px=0;px<w;px++)
            framebuffer[(y+py)*640+x+px]=renderer.pixels[py*64+px];
#ifdef REIST_RENDER_EQUIVALENCE
        for(unsigned py=0;py<h;py++)for(unsigned px=0;px<w;px++)
            assert(renderer.pixels[py*64+px]==reference_pixel(&c,(int)(x+px),(int)(y+py)));
#endif
        count++;
    }
    assert(!"unbounded dirty tiles");return 0;
}
static void paint(unsigned n,uint32_t color,unsigned commit) {
    reist_gui_surface_message_t q=request(REIST_GUI_SURFACE_PAINT_BEGIN),reply;q.surface=c.clients[n].surface;
    assert(!reist_native_surface(&c,n,&q,&reply,50));
    q=request(REIST_GUI_SURFACE_PAINT_FILL);q.surface=c.clients[n].surface;
    q.damage=(reist_gui_rect_t){0,0,320,192};q.flags=color;
    assert(!reist_native_surface(&c,n,&q,&reply,50));
    q=request(REIST_GUI_SURFACE_PAINT_TEXT);q.surface=c.clients[n].surface;
    q.damage=(reist_gui_rect_t){290,188,30,1};q.flags=0xffffff;q.buffer_id=0x123456;
    q.byte_size=5;memcpy(&q.input,"Abc!?",5);
    assert(!reist_native_surface(&c,n,&q,&reply,50));
    if(commit){q=request(REIST_GUI_SURFACE_PAINT_COMMIT);q.surface=c.clients[n].surface;assert(!reist_native_surface(&c,n,&q,&reply,50));}
}
int main(void) {
#ifdef REIST_RENDER_PACING
    extern int reist_native_render_due(reist_native_renderer *,uint64_t);
    reist_native_renderer paced={0};unsigned batches=0;
    for(uint64_t now=0;now<1000;now++) {
        int due=reist_native_render_due(&paced,now);assert(due==0||due==1);
        if(due){assert(now%100==0);batches++;}
    }
    assert(batches==10); /* <=40 commits even under a continuously dirty frame */
    assert(reist_native_render_due(&paced,998)==-75);
    assert(reist_native_render_due(&paced,1000)==1);
    assert(reist_native_render_due(&paced,5000)==1); /* no accumulated catch-up */
    for(uint64_t now=5000;now<5100;now++)assert(reist_native_render_due(&paced,now)==0);
    assert(reist_native_render_due(&paced,5100)==1);
    assert(reist_native_render_due(&paced,UINT64_MAX-99)==-75);
    assert(reist_native_render_due(0,0)==-22);
#endif
    assert(sizeof(c)<2*1024*1024);
    assert(!reist_native_compositor_init(&c,640,480,compositor,driver,3));
    client(0,9);client(1,10);
    assert(!reist_native_client_ready(&c,0,1));
    reist_input_event_v1 e=event(REIST_INPUT_HEALTHY,1);
    assert(!reist_native_input(&c,&e,20));
    uint64_t last=c.sequence;e.epoch=4;assert(reist_native_input(&c,&e,21)==-116);assert(c.sequence==last);
    motion(2,42,-72,0);motion(3,0,0,1);
    assert(c.wm.keyboard_focus==0 && c.wm.capture_kind==DESKTOP_WM_CAPTURE_CLIENT);
    motion(4,255,-255,1);motion(5,255,-100,1);motion(6,0,0,0);
    assert(c.wm.capture_kind==DESKTOP_WM_CAPTURE_NONE);
    reist_gui_surface_input_t local;unsigned press=0,release=0,count=0;
    while(!reist_native_client_event(&c,0,&local)) {
        assert(local.x>=0&&local.x<320&&local.y>=0&&local.y<192);
        if(local.type==REIST_GUI_SURFACE_INPUT_POINTER_BUTTON){if(local.pressed)press++;else release++;}
        ++count;
    }
    assert(press==1&&release==1&&count>=3);
    assert(reist_native_client_event(&c,1,&local)==-114);
    e=event(REIST_INPUT_KEY,7);e.code=0x1e;
    assert(!reist_native_input(&c,&e,30));
    assert(!reist_native_client_event(&c,0,&local)&&local.key=='a');
    assert(reist_native_client_event(&c,1,&local)==-114);
    e=event(REIST_INPUT_KEY,8);e.code=0x0f;e.flags=16;
    assert(!reist_native_input(&c,&e,31));assert(c.wm.keyboard_focus==1);
    e=event(REIST_INPUT_KEY,9);e.code=0x30;
    assert(!reist_native_input(&c,&e,32));
    assert(!reist_native_client_event(&c,1,&local)&&local.key=='b');
    reist_gui_surface_message_t q=request(REIST_GUI_SURFACE_PAINT_BEGIN),reply;
    q.surface=c.clients[0].surface;
    assert(reist_native_surface(&c,1,&q,&reply,33)==-116);
    q.surface=c.clients[1].surface;q.reserved=1;
    assert(reist_native_surface(&c,1,&q,&reply,34)==-22);
    uint64_t old=c.clients[0].owner;
    reist_gui_surface_handle_t old_surface=c.clients[0].surface;
    assert(!reist_native_client_revoke(&c,0,old));
    assert(reist_native_client_bind(&c,0,old,110)==-116);
    client(0,11);
    q=request(REIST_GUI_SURFACE_PAINT_BEGIN);q.surface=old_surface;
    unsigned requests=c.clients[0].requests.used;
    assert(reist_native_surface(&c,0,&q,&reply,35)==-116);
    assert(c.clients[0].requests.used==requests);
    assert(reist_native_client_revoke(&c,0,old)==-116);
    assert(c.clients[1].owner==(10ULL<<32|7));
    for(unsigned i=0;i<64;i++) {
        reist_input_event_v1 bad=event(REIST_INPUT_HEALTHY,10);
        ((unsigned char*)&bad)[i]^=128;
        assert(reist_native_input(&c,&bad,40)==-116);
        assert(c.sequence==9);
    }
    paint(0,0xe04020,1);paint(1,0x2070c0,1);
    assert(!reist_native_client_ready(&c,0,0));assert(reist_native_client_ready(&c,0,1));
    assert(!reist_native_client_ready(&c,2,1));
    desktop_surface_slot_t *checked=&c.surfaces.slots[c.clients[0].surface.id-1];
    checked->acknowledged_serial--;assert(!reist_native_client_ready(&c,0,1));checked->acknowledged_serial++;
    checked->owner.process_generation--;assert(!reist_native_client_ready(&c,0,1));checked->owner.process_generation++;
    assert(render()==80);
    assert(framebuffer[100*640+100]==0xe04020);
    assert(framebuffer[300*640+400]==0x2070c0);
    assert(framebuffer[240*640+300]==0xe04020); /* selected0 occludes1 */
    paint(0,0xeecc30,0);assert(render()==0);assert(framebuffer[100*640+100]==0xe04020);
    q=request(REIST_GUI_SURFACE_PAINT_COMMIT);q.surface=c.clients[0].surface;
    assert(!reist_native_surface(&c,0,&q,&reply,50));assert(render()>0);
    assert(framebuffer[100*640+100]==0xeecc30);
    assert(framebuffer[300*640+400]==0x2070c0);
    assert(render()==0);
    for(unsigned layer=0;layer<3;layer++) {
        unsigned begin=REIST_GUI_SURFACE_PAINT_OVERLAY_BEGIN+layer*2;
        q=request(begin);q.surface=c.clients[0].surface;
        assert(!reist_native_surface(&c,0,&q,&reply,60));
        q=request(REIST_GUI_SURFACE_PAINT_FILL);q.surface=c.clients[0].surface;
        q.damage=(reist_gui_rect_t){1+(int)layer,1+(int)layer,7,7};q.flags=0x305070+layer;
        assert(!reist_native_surface(&c,0,&q,&reply,60));
        q=request(begin+1);q.surface=c.clients[0].surface;
        assert(!reist_native_surface(&c,0,&q,&reply,60));assert(render()>0);
    }
    c.wm.windows[0].x=620;c.wm.windows[0].y=470;desktop_dirty_full(&c.dirty);assert(render()==80);
    c.wm.windows[0].x=-300;c.wm.windows[0].y=-180;desktop_dirty_full(&c.dirty);assert(render()==80);
    /* Frame/title motion is compositor-owned. An outside implicit grab is
     * the only case that clamps a pointer into an application's client area. */
    assert(!reist_native_compositor_init(&c,640,480,compositor,driver,4));
    client(0,12);client(1,13);
    e=event(REIST_INPUT_HEALTHY,1);e.epoch=4;assert(!reist_native_input(&c,&e,100));
    e=event(REIST_INPUT_POINTER,2);e.epoch=4;e.dx=42;e.dy=-40;
    assert(!reist_native_input(&c,&e,101));
    assert(reist_native_client_event(&c,0,&local)==-114);
    assert(reist_native_client_event(&c,1,&local)==-114);
    paint(0,0xe04020,1);paint(1,0x2070c0,1);assert(render()==80);
    uint64_t unaffected=c.clients[1].owner;
    assert(!reist_native_client_revoke(&c,0,c.clients[0].owner));
    client(0,14);paint(0,0xe04020,1);
    unsigned replacement_tiles=render();
    printf("REPLACEMENT_DAMAGE_TILES=%u\n",replacement_tiles);
    assert(replacement_tiles>40 && replacement_tiles<=80);
    assert(c.clients[1].owner==unaffected && reist_native_client_ready(&c,0,1));
    puts("GRAPHICAL_COMPOSITOR_OK");return 0;
}
