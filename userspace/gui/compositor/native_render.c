#include "native_render.h"
#include "native_font.h"
/* One batch per absolute100ms interval, no catch-up burst. Polling input and
 * health continues at10ms while pending damage remains merged in fixed bits. */
int reist_native_render_due(reist_native_renderer *r,uint64_t now) {
    if(!r)return -22;
    if(now<r->last_draw || now>UINT64_MAX-100)return -75;
    r->last_draw=now;
    if(now<r->next_draw)return 0;
    r->next_draw=now+100;return 1;
}
/* Raster each clipped rectangle once. Window order is resolved once per tile,
 * preserving the committed layer order and exact legacy pixel semantics. */
typedef struct {
    uint32_t *pixels;
    unsigned x,y,height;
    desktop_rect_t clip;
} raster;
static int bounds(const raster *r,int x,int y,unsigned w,unsigned h,
                  int *left,int *top,int *right,int *bottom) {
    int64_t l=x,t=y,endx=(int64_t)x+w,endy=(int64_t)y+h;
    int64_t cl=r->clip.x,ct=r->clip.y,cr=cl+r->clip.width,cb=ct+r->clip.height;
    if(l<cl)l=cl;if(t<ct)t=ct;if(endx>cr)endx=cr;if(endy>cb)endy=cb;
    if(l<r->x)l=r->x;if(t<r->y)t=r->y;
    if(endx>r->x+64)endx=r->x+64;if(endy>r->y+r->height)endy=r->y+r->height;
    if(l>=endx || t>=endy)return 0;
    *left=(int)l;*top=(int)t;*right=(int)endx;*bottom=(int)endy;return 1;
}
static void fill(raster *r,int x,int y,unsigned width,unsigned height,uint32_t color) {
    int l,t,right,bottom;if(!bounds(r,x,y,width,height,&l,&t,&right,&bottom))return;
    for(int py=t;py<bottom;py++)for(int px=l;px<right;px++)
        r->pixels[((unsigned)py-r->y)*64+(unsigned)px-r->x]=color;
}
static void text(raster *r,const char *value,unsigned count,int x,int y,unsigned width,
                 uint32_t foreground,uint32_t background) {
    int l,t,right,bottom;if(!bounds(r,x,y,width,16,&l,&t,&right,&bottom))return;
    for(int py=t;py<bottom;py++)for(int px=l;px<right;px++) {
        unsigned offset=(unsigned)(px-x),character=offset/8;uint32_t color=background;
        if(character<count) {
            unsigned c=(unsigned char)value[character];if(c>=128)c='?';
            if(native_font[c*16+(unsigned)(py-y)]&(0x80U>>(offset%8)))color=foreground;
        }
        r->pixels[((unsigned)py-r->y)*64+(unsigned)px-r->x]=color;
    }
}
static void paint(raster *r,const desktop_surface_paint_command_t *commands,unsigned count,int x,int y) {
    for(unsigned n=0;n<count;n++) {
        const desktop_surface_paint_command_t *p=&commands[n];
        if(p->type==DESKTOP_SURFACE_PAINT_FILL)
            fill(r,x+p->rect.x,y+p->rect.y,p->rect.width,p->rect.height,p->foreground);
        else if(p->type==DESKTOP_SURFACE_PAINT_TEXT)
            text(r,p->text,p->text_length,x+p->rect.x,y+p->rect.y,p->rect.width,p->foreground,p->background);
    }
}
static void tile(raster *r,const reist_native_compositor *c) {
    r->clip=(desktop_rect_t){0,0,640,480};
    fill(r,0,0,640,480,0x24374a);fill(r,0,0,640,28,0x172334);
    text(r,"REIST OS  |  Alt+Tab: focus  Esc: shell",38,12,6,38*8,0xe2ecf5,0x172334);
    for(unsigned position=0;position<DESKTOP_WM_CAPACITY;position++) {
        unsigned at=c->wm.z_order[position];if(at>=2 || !c->wm.windows[at].visible)continue;
        const desktop_window_t *w=&c->wm.windows[at];
        r->clip=(desktop_rect_t){w->x,w->y,w->width,w->height};
        int l,t,right,bottom;if(!bounds(r,w->x,w->y,w->width,w->height,&l,&t,&right,&bottom))continue;
        uint32_t frame=c->wm.keyboard_focus==(int)at?0x3b82b8:0x485563;
        fill(r,w->x,w->y,w->width,w->height,frame);
        r->clip.height=24;
        const reist_native_gui_client *client=&c->clients[at];
        const char *title=at?"Pointer pad":"Text pad";unsigned length=at?11:8;
        if(client->active && client->surface.id) {
            const char *custom=c->surfaces.slots[client->surface.id-1].title;
            if(custom[0]){title=custom;length=0;while(length<REIST_GUI_SURFACE_PAINT_TEXT_CAPACITY && custom[length])length++;}
        }
        text(r,title,length,w->x+8,w->y+4,length*8,0xffffff,frame);
        desktop_rect_t close=desktop_wm_close_rect(&c->wm,at);
        fill(r,close.x,close.y,close.width,close.height,0x973d40);
        text(r,"x",1,close.x,close.y,8,0xffffff,0x973d40);
        r->clip=(desktop_rect_t){w->x+3,w->y+24,320,192};
        fill(r,w->x+3,w->y+24,320,192,0x151c24);
        if(!client->active || !client->surface.id)continue;
        const desktop_surface_slot_t *s=&c->surfaces.slots[client->surface.id-1];
        paint(r,s->committed_paint,s->committed_paint_count,w->x+3,w->y+24);
        paint(r,s->committed_overlay_paint,s->committed_overlay_paint_count,w->x+3,w->y+24);
        paint(r,s->committed_dynamic_paint,s->committed_dynamic_paint_count,w->x+3,w->y+24);
        paint(r,s->committed_hover_paint,s->committed_hover_paint_count,w->x+3,w->y+24);
    }
    r->clip=(desktop_rect_t){0,0,640,480};
    for(unsigned y=0;y<12;y++)for(unsigned x=0;x<8;x++)
        if(!x||!y||x==y/2)fill(r,c->x+(int)x,c->y+(int)y,1,1,0xffffff);
}
void reist_native_render_damage(reist_native_renderer *r,reist_native_compositor *c) {
    for(unsigned n=0;n<c->dirty.count;n++) {
        desktop_rect_t d=c->dirty.rects[n];
        unsigned left=(unsigned)d.x/64,top=(unsigned)d.y/64;
        unsigned right=((unsigned)d.x+d.width+63)/64,bottom=((unsigned)d.y+d.height+63)/64;
        if(right>10)right=10;if(bottom>8)bottom=8;
        for(unsigned y=top;y<bottom;y++)for(unsigned x=left;x<right;x++) {
            unsigned bit=y*10+x;r->tiles[bit/64]|=1ULL<<(bit%64);
        }
    }
    desktop_dirty_initialize(&c->dirty,640,480);
}
int reist_native_render_tile(reist_native_renderer *r,const reist_native_compositor *c,
    unsigned *x,unsigned *y,unsigned *width,unsigned *height) {
    if(!r||!c||!x||!y||!width||!height)return -22;
    unsigned selected=80,feedback=(unsigned)c->y/64*10+(unsigned)c->x/64;
    if(feedback<80 && r->tiles[feedback/64]&(1ULL<<(feedback%64)))selected=feedback;
    else for(unsigned n=0;n<80;n++) {
        unsigned bit=(r->cursor+n)%80;
        if(r->tiles[bit/64]&(1ULL<<(bit%64))){selected=bit;break;}
    }
    if(selected==80)return 0;
    *x=(selected%10)*64;*y=(selected/10)*64;*width=64;*height=*y==448?32:64;
    raster output={r->pixels,*x,*y,*height,{0,0,640,480}};tile(&output,c);
    r->tiles[selected/64]&=~(1ULL<<(selected%64));r->cursor=(selected+1)%80;return 1;
}
