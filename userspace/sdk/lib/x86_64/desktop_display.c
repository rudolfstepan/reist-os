/* Software display backend for the real desktop; all raster state is Ring3. */
#include <x86os.h>
#include <reist/x86_64/desktop_display.h>
#include <reist/utf.h>
#include <reist/unicode_vga_font.h>

static struct {
    reist_desktop_display_config config;
    uint32_t serial, frame, active, attached, columns, cursor, blit;
    uint32_t sx, sy, dx, dy, bw, bh;
    int32_t px, py;
    unsigned visible, history_count, history_head;
    int failure;
    uint64_t previous, history[64], dirty[3], staged[3];
    uint32_t tile[64*64];
} state;
static uint64_t last_epoch;

/* AMD64 integer string copy for validated, disjoint pixel buffers. MOVSQ
 * accepts the adapter's four-byte alignment; retain an odd final pixel.
 * No SIMD state or toolchain memcpy dependency is required. */
static void copy_pixels(uint32_t *destination,const uint32_t *source,size_t pixels) {
    size_t pairs=pixels/2;
    __asm__ volatile("cld; rep movsq"
        : "+D"(destination), "+S"(source), "+c"(pairs) : : "memory", "cc");
    if(pixels&1) *destination=*source;
}
static void clear_pixels(uint32_t *destination,size_t pixels) {
    size_t pairs=pixels/2;
    __asm__ volatile("cld; rep stosq"
        : "+D"(destination), "+c"(pairs) : "a"(UINT64_C(0)) : "memory", "cc");
    if(pixels&1) *destination=0;
}

static int status(void) {
    if (!state.attached) return -19;
    if (state.failure) return state.failure;
    return state.active ? 0 : -19;
}
static int clock_read(uint64_t *now) {
    int r=state.config.clock_ms(state.config.context,now);
    if (r || *now<state.previous || *now>UINT64_MAX-100) {
        state.failure=r<0?r:(r?-5:(*now<state.previous?-84:-75));
        return state.failure;
    }
    state.previous=*now;
    return 0;
}
static int region(uintptr_t start,size_t bytes) {
    return start && bytes && start<=UINTPTR_MAX-bytes;
}
static int overlaps(uintptr_t a,size_t an,uintptr_t b,size_t bn) {
    return a<b+bn && b<a+an;
}
int reist_desktop_display_attach(const reist_desktop_display_config *c) {
    if (state.attached) return -16;
    if (!c || c->version!=1 || c->size!=sizeof(*c) ||
        c->width<320 || c->height<240 || c->width>1024 || c->height>768 ||
        c->pixel_capacity<(size_t)c->width*c->height || c->pixel_capacity>1024*768 ||
        !c->epoch || c->epoch>INT64_MAX || (uint32_t)c->owner<2 ||
        (uint32_t)c->owner>7 || !(c->owner>>32) || (c->owner>>32)>0x7ffffffe ||
        !c->clock_ms || !c->commit || c->font_bytes!=4096) return -22;
    size_t bytes=c->pixel_capacity*4;
    uintptr_t a=(uintptr_t)c->front,b=(uintptr_t)c->back,f=(uintptr_t)c->font;
    if ((a|b)%4 || !region(a,bytes) || !region(b,bytes) || !region(f,4096) ||
        overlaps(a,bytes,b,bytes) || overlaps(a,bytes,f,4096) ||
        overlaps(b,bytes,f,4096) ||
        overlaps(a,bytes,(uintptr_t)c,sizeof(*c)) ||
        overlaps(b,bytes,(uintptr_t)c,sizeof(*c))) return -22;
    if (c->epoch<=last_epoch) return -116;
    uint64_t now=0; int r=c->clock_ms(c->context,&now);
    if (r || now>UINT64_MAX-100) return r<0?r:-75;
    state.config=*c; state.previous=now; state.attached=1;
    state.columns=(c->width+63)/64; last_epoch=c->epoch;
    const size_t pixels=(size_t)c->width*c->height;
    uint32_t *front=c->front,*back=c->back;
    clear_pixels(front,pixels);
    clear_pixels(back,pixels);
    return 0;
}
void reist_desktop_display_detach(void) {
    /* No ownership transfer: the caller releases buffers after detach. */
    volatile unsigned char *p=(volatile unsigned char *)&state;
    for (size_t n=0;n<sizeof(state);n++) p[n]=0;
}
static int bounds(int64_t x,int64_t y,uint32_t w,uint32_t h,
                  int32_t *l,int32_t *t,int32_t *r,int32_t *b) {
    int64_t right=x+w,bottom=y+h;
    if (x<0) x=0;
    if (y<0) y=0;
    if (right>state.config.width) right=state.config.width;
    if (bottom>state.config.height) bottom=state.config.height;
    if (x>=right || y>=bottom) return 0;
    *l=(int32_t)x; *t=(int32_t)y; *r=(int32_t)right; *b=(int32_t)bottom;
    return 1;
}
static void mark(uint64_t *set,int32_t l,int32_t t,int32_t r,int32_t b) {
    for (unsigned y=(unsigned)t/64;y<((unsigned)b+63)/64;y++)
        for (unsigned x=(unsigned)l/64;x<((unsigned)r+63)/64;x++) {
            unsigned bit=y*state.columns+x;
            set[bit/64]|=1ULL<<(bit%64);
        }
}
static void damage(int32_t l,int32_t t,int32_t r,int32_t b) {
    mark(state.frame?state.staged:state.dirty,l,t,r,b);
#ifdef REIST_NATIVE_FULL_DESKTOP
    if(!state.frame)mark(state.staged,l,t,r,b);
#endif
}
static uint32_t *target(void) { return state.frame?state.config.back:state.config.front; }
int x86os_display_activate(void) {
    if (!state.attached) return -19;
    if (state.failure) return state.failure;
    state.active=1;
    mark(state.dirty,0,0,(int32_t)state.config.width,(int32_t)state.config.height);
    return 0;
}
int x86os_display_deactivate(void) {
    if (!state.attached) return -19;
    state.active=state.frame=state.blit=0;
    for (unsigned n=0;n<3;n++) {
        state.dirty[n]=0;
#ifndef REIST_NATIVE_FULL_DESKTOP
        state.staged[n]=0;
#endif
    }
    return 0;
}
int x86os_display_info(x86os_display_info_t *out) {
    if (!out) return -22;
    int r=status(); if (r) return r;
    *out=(x86os_display_info_t){1,sizeof(*out),state.config.width,state.config.height,
        state.config.width*4,32,16,8,8,8,0,8,8,16};
    return 0;
}
int x86os_display_mode_query(reist_display_mode_request_t *out) {
    if (!out) return -22;
    if (!state.attached) return -19;
    if (state.failure) return state.failure;
    unsigned w=state.config.width,h=state.config.height;
    *out=(reist_display_mode_request_t){1,sizeof(*out),REIST_DISPLAY_MODE_QUERY,0,
        REIST_DISPLAY_BACKEND_VBE,w,h,w*h*4,w*h*4,w,h,w,h,32,
        state.active?REIST_DISPLAY_MODE_ACTIVE:0,0};
    return 0;
}
int x86os_display_activate_mode(uint32_t width,uint32_t height) {
    if (!state.attached) return -19;
    if (width!=state.config.width || height!=state.config.height) return -95;
    return x86os_display_activate();
}
int x86os_display_frame_begin(uint32_t *serial) {
    if (!serial) return -22;
    int r=status(); if (r) return r;
    if (state.frame) return -16;
    if (state.serial==UINT32_MAX) return -75;
#ifdef REIST_NATIVE_FULL_DESKTOP
    /* Between frames staged describes back-buffer tiles differing from front.
     * Repair before any draw; within a frame the same bitmap tracks new writes.
     * Caller-owned buffers remain exclusively adapter-written while attached. */
    const unsigned width=state.config.width,height=state.config.height;
    for(unsigned tile=0;tile<state.columns*((height+63)/64);tile++) {
        if(!(state.staged[tile/64]&(UINT64_C(1)<<(tile%64))))continue;
        unsigned x=(tile%state.columns)*64,y=(tile/state.columns)*64;
        unsigned w=width-x<64?width-x:64,h=height-y<64?height-y:64;
        for(unsigned row=0;row<h;row++) {
            size_t offset=(size_t)(y+row)*width+x;
            copy_pixels(state.config.back+offset,state.config.front+offset,w);
        }
    }
    for(unsigned n=0;n<3;n++)state.staged[n]=0;
#else
    const size_t count=(size_t)state.config.width*state.config.height;
    copy_pixels(state.config.back,state.config.front,count);
#endif
    state.frame=++state.serial; *serial=state.frame;
    return 0;
}
int x86os_display_frame_cancel(uint32_t serial) {
    int r=status(); if (r) return r;
    if (!serial || serial!=state.frame) return -116;
    state.frame=state.blit=0;
#ifndef REIST_NATIVE_FULL_DESKTOP
    for (unsigned n=0;n<3;n++) state.staged[n]=0;
#endif
    return 0;
}
int x86os_display_frame_stage_blit(uint32_t serial,uint32_t sx,uint32_t sy,
    uint32_t dx,uint32_t dy,uint32_t w,uint32_t h) {
    int r=status(); if (r) return r;
    if (!serial || serial!=state.frame) return -116;
    if (state.blit) return -16;
    if (!w || !h || w>state.config.width || h>state.config.height ||
        sx>state.config.width-w || dx>state.config.width-w ||
        sy>state.config.height-h || dy>state.config.height-h) return -22;
    /* The desktop stages before drawing. A modified source would need a third
     * snapshot buffer: report unsupported so its ordinary redraw fallback runs. */
    if (state.staged[0] || state.staged[1] || state.staged[2]) return -95;
    state.sx=sx; state.sy=sy; state.dx=dx; state.dy=dy; state.bw=w; state.bh=h; state.blit=1;
    return 0;
}
int x86os_display_frame_commit(uint32_t serial) {
    int r=status(); if (r) return r;
    if (!serial || serial!=state.frame) return -116;
    if (state.blit) {
        for (unsigned y=0;y<state.bh;y++) for (unsigned x=0;x<state.bw;x++)
            state.config.back[(state.dy+y)*state.config.width+state.dx+x]=
                state.config.front[(state.sy+y)*state.config.width+state.sx+x];
        mark(state.staged,(int32_t)state.dx,(int32_t)state.dy,
            (int32_t)(state.dx+state.bw),(int32_t)(state.dy+state.bh));
    }
    uint32_t *swap=state.config.front; state.config.front=state.config.back; state.config.back=swap;
    for (unsigned n=0;n<3;n++) {
        state.dirty[n]|=state.staged[n];
#ifndef REIST_NATIVE_FULL_DESKTOP
        state.staged[n]=0;
#endif
    }
    state.frame=state.blit=0;
    return 0;
}
int x86os_fill_rect(int32_t x,int32_t y,uint32_t w,uint32_t h,uint32_t rgb) {
    int result=status(); if (result) return result;
    int32_t l,t,r,b; if (!bounds(x,y,w,h,&l,&t,&r,&b)) return 0;
    /* The dimensions are validated at attach and fixed for this transaction.
     * Snapshot them before stores: uint32_t output otherwise forces the
     * compiler to reload possibly aliased config.width for every pixel. */
    uint32_t *pixels=target();
    const unsigned width=state.config.width,count=(unsigned)(r-l);
    rgb&=0xffffff;
    for (int32_t py=t;py<b;py++) {
        uint32_t *row=pixels+(size_t)(unsigned)py*width+(unsigned)l;
        for (unsigned px=0;px<count;px++) row[px]=rgb;
    }
    damage(l,t,r,b); return 0;
}
int x86os_draw_pixels(int32_t x,int32_t y,uint32_t w,uint32_t h,
    const uint32_t *pixels,uint32_t stride) {
    int result=status(); if (result) return result;
    if (!w || !h || w>1024 || h>768 || stride<w || stride>1024 ||
        (uintptr_t)pixels%4 || !region((uintptr_t)pixels,((size_t)(h-1)*stride+w)*4)) return -22;
    size_t bytes=((size_t)(h-1)*stride+w)*4, frame_bytes=state.config.pixel_capacity*4;
    if (overlaps((uintptr_t)pixels,bytes,(uintptr_t)state.config.front,frame_bytes) ||
        overlaps((uintptr_t)pixels,bytes,(uintptr_t)state.config.back,frame_bytes)) return -22;
    int32_t l,t,r,b; if (!bounds(x,y,w,h,&l,&t,&r,&b)) return 0;
    uint32_t *out=target();
    const unsigned width=state.config.width,count=(unsigned)(r-l);
    for (int32_t py=t;py<b;py++) {
        uint32_t *row=out+(size_t)(unsigned)py*width+(unsigned)l;
        const uint32_t *source=pixels+(size_t)((int64_t)py-y)*stride+(size_t)((int64_t)l-x);
        for (unsigned px=0;px<count;px++) row[px]=source[px]&0xffffff;
    }
    damage(l,t,r,b); return 0;
}
int x86os_draw_text_pixels_clipped(int32_t x,int32_t y,const char *text,size_t length,
    uint32_t fg,uint32_t bg,int32_t cx,int32_t cy,uint32_t cw,uint32_t ch) {
    int result=status(); if (result) return result;
    size_t scalars=0;
    size_t frame_bytes=state.config.pixel_capacity*4;
    if (length>X86OS_DISPLAY_MAX_TEXT || (length && (!region((uintptr_t)text,length) ||
        overlaps((uintptr_t)text,length,(uintptr_t)state.config.front,frame_bytes) ||
        overlaps((uintptr_t)text,length,(uintptr_t)state.config.back,frame_bytes))) ||
        !reist_utf8_scan(text,length,&scalars)) return -22;
    int32_t cl,ct,cr,cb; if (!bounds(cx,cy,cw,ch,&cl,&ct,&cr,&cb)) return 0;
    uint32_t *out=target(); size_t at=0;
    for (size_t cell=0;cell<scalars;cell++) {
        uint32_t scalar=0; size_t consumed=0;
        (void)reist_utf8_decode_one(text+at,length-at,&consumed,&scalar); at+=consumed;
        int64_t gx=(int64_t)x+(int64_t)cell*8;
        int32_t l,t,r,b; if (!bounds(gx,y,8,16,&l,&t,&r,&b)) continue;
        if (l<cl) l=cl;
        if (t<ct) t=ct;
        if (r>cr) r=cr;
        if (b>cb) b=cb;
        if (l>=r || t>=b) continue;
        const unsigned char *glyph=state.config.font+reist_unicode_vga_glyph(scalar)*16;
        for (int32_t py=t;py<b;py++) for (int32_t px=l;px<r;px++)
            out[(unsigned)py*state.config.width+(unsigned)px]=
                (glyph[py-y]&(0x80U>>(px-gx))?fg:bg)&0xffffff;
        damage(l,t,r,b);
    }
    return 0;
}
int x86os_draw_text_pixels(int32_t x,int32_t y,const char *text,size_t length,uint32_t fg,uint32_t bg) {
    return x86os_draw_text_pixels_clipped(x,y,text,length,fg,bg,0,0,state.config.width,state.config.height);
}
static void cursor_damage(void) {
    int32_t l,t,r,b;
    if (state.visible && bounds(state.px,state.py,8,12,&l,&t,&r,&b)) mark(state.dirty,l,t,r,b);
}
int x86os_pointer_update(int32_t x,int32_t y,uint32_t visible) {
    int r=status(); if (r) return r;
    if (visible>1 || (visible && (x<0 || y<0 || (uint32_t)x>=state.config.width || (uint32_t)y>=state.config.height))) return -22;
    cursor_damage(); state.px=x; state.py=y; state.visible=visible; cursor_damage(); return 0;
}
int x86os_display_frame_mark_accelerated(uint32_t serial) { (void)serial; return -95; }
int x86os_display_surface_buffer_draw(int owner,uint32_t generation,uint32_t buffer,
    uint32_t buffer_generation,uint32_t sx,uint32_t sy,int32_t dx,int32_t dy,uint32_t w,uint32_t h) {
    (void)owner; (void)generation; (void)buffer; (void)buffer_generation;
    (void)sx; (void)sy; (void)dx; (void)dy; (void)w; (void)h; return -95;
}
static int pending(void) { return !!(state.dirty[0]|state.dirty[1]|state.dirty[2]); }
int reist_desktop_display_idle(void) {
    int result=status();
    if (result) return result;
    return !!state.frame || pending();
}
int reist_desktop_display_service(void) {
    if (state.failure) return state.failure;
    if (!state.attached || !state.active || state.frame) return 0;
    uint64_t next;
    int r=reist_desktop_display_pump(&next);
    return r<0?r:0;
}
int reist_desktop_display_pump(uint64_t *next) {
    if (!next) return -22;
    int result=status(); if (result) return result;
    if (state.frame) return -16;
    uint64_t now=0; if ((result=clock_read(&now))) return result;
    *next=now;
    unsigned total=state.columns*((state.config.height+63)/64);
    for (unsigned turn=0;turn<8 && pending();turn++) {
        while (state.history_count && now-state.history[state.history_head]>=100) {
            state.history_head=(state.history_head+1)%64; state.history_count--;
        }
        if (state.history_count==64) { *next=state.history[state.history_head]+100; return 1; }
        unsigned bit=total;
        for (unsigned n=0;n<total;n++) {
            unsigned candidate=(state.cursor+n)%total;
            if (state.dirty[candidate/64]&(1ULL<<(candidate%64))) { bit=candidate; break; }
        }
        if (bit==total) { state.failure=-84; return state.failure; }
        unsigned x=(bit%state.columns)*64,y=(bit/state.columns)*64;
        unsigned w=state.config.width-x,h=state.config.height-y;
        if (w>64) w=64;
        if (h>64) h=64;
        const unsigned width=state.config.width;
        const uint32_t *front=state.config.front;
        for (unsigned py=0;py<h;py++) {
            const uint32_t *source=front+(size_t)(y+py)*width+x;
            uint32_t *row=state.tile+py*w;
            copy_pixels(row,source,w);
        }
        /* Cursor work is bounded by its8x12 bitmap, not by every screen pixel. */
        int64_t left=(int64_t)state.px-x,top=(int64_t)state.py-y;
        if (state.visible && left<(int64_t)w && top<(int64_t)h && left+8>0 && top+12>0) {
            for (unsigned cy=0;cy<12;cy++) for (unsigned cx=0;cx<8;cx++) {
                int64_t tx=left+cx,ty=top+cy;
                if ((!cx || !cy || cx==cy/2) && tx>=0 && ty>=0 && tx<w && ty<h)
                    state.tile[(unsigned)ty*w+(unsigned)tx]=0xffffff;
            }
        }
        reist_display_request_v1 q={1,64,REIST_DISPLAY_COMMIT,0,state.config.owner,state.config.epoch,
            now+100,(uintptr_t)state.tile,x,y,(uint16_t)w,(uint16_t)h,w*4};
        result=state.config.commit(state.config.context,&q);
        if (result) { state.failure=result<0?result:-5; return state.failure; }
        if ((result=clock_read(&now))) return result;
        state.history[(state.history_head+state.history_count)%64]=now; state.history_count++;
        state.dirty[bit/64]&=~(1ULL<<(bit%64)); state.cursor=(bit+1)%total;
        *next=now;
    }
    return pending();
}
