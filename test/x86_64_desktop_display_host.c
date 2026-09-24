#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <x86os.h>
#include <reist/x86_64/desktop_display.h>

static uint32_t a[1024*768], b[1024*768], screen[1024*768];
static unsigned char font[4096];
static uint64_t now = 1000, epoch = 1;
static unsigned calls, fail_at;
static unsigned edge_tiles;
static uint64_t times[1024];
static int clock_ms(void *unused, uint64_t *out) { (void)unused; *out=now; return 0; }
static int copy(void *unused, const reist_display_request_v1 *q) {
    (void)unused;
    assert(q->version==1 && q->size==64 && q->operation==REIST_DISPLAY_COMMIT);
    assert(q->owner==((1ULL<<32)|4) && q->epoch==epoch && q->deadline_ms==now+100);
    assert(!q->flags && q->width && q->width<=64 && q->height && q->height<=64);
    assert(q->stride==q->width*4 && q->x+q->width<=1024 && q->y+q->height<=768);
    if(q->width<64 || q->height<64) edge_tiles++;
    assert(calls<1024);
    if(calls>=64) assert(now-times[calls-64]>=100);
    times[calls++]=now;
    if(fail_at && calls==fail_at) return -116;
    const uint32_t *pixels=(const uint32_t *)(uintptr_t)q->pixels;
    for(unsigned y=0;y<q->height;y++) for(unsigned x=0;x<q->width;x++)
        screen[(q->y+y)*1024+q->x+x]=pixels[y*q->width+x];
    return 0;
}
static reist_desktop_display_config config(void) {
    reist_desktop_display_config c={0};
    c.version=1; c.size=sizeof(c); c.width=1024; c.height=768;
    c.owner=(1ULL<<32)|4; c.epoch=epoch;
    c.front=a; c.back=b; c.pixel_capacity=1024*768; c.font=font; c.font_bytes=sizeof(font);
    c.clock_ms=clock_ms; c.commit=copy;
    return c;
}
static void drain(void) {
    uint64_t next;
    for(unsigned turn=0;turn<100;turn++) {
        unsigned before=calls;
        int r=reist_desktop_display_pump(&next);
        assert(r>=0 && calls-before<=8);
        if(!r) return;
        if(next>now) now=next;
    }
    assert(!"bounded drain");
}
int main(void) {
    memset(a,0x5a,sizeof(a)); memset(b,0xa5,sizeof(b));
    memset(font+65*16,0xff,16);
    font[142*16]=0x80; /* CP437 capital A umlaut, addressed through UTF-8. */
    reist_desktop_display_config c=config();
    reist_desktop_display_config bad=c; bad.back=a;
    assert(reist_desktop_display_attach(&bad)==-22 && a[0]==0x5a5a5a5a);
    bad=c; bad.pixel_capacity--; assert(reist_desktop_display_attach(&bad)==-22);
    bad=c; bad.width=UINT32_MAX; assert(reist_desktop_display_attach(&bad)==-22);
    bad=c; bad.font_bytes=4095; assert(reist_desktop_display_attach(&bad)==-22);
    assert(reist_desktop_display_attach(&c)==0);
    assert(reist_desktop_display_attach(&c)==-16);
    assert(x86os_display_activate()==0);
    x86os_display_info_t info; assert(x86os_display_info(&info)==0 && info.width==1024 && info.font_height==16);
    assert(x86os_display_activate_mode(800,600)==-95);
    reist_display_mode_request_t mode;
    assert(x86os_display_mode_query(&mode)==0 && reist_display_mode_supported(1024,768,&mode));
    uint32_t serial=0;
    assert(x86os_display_frame_begin(&serial)==0 && serial);
    assert(x86os_fill_rect(-2,-2,4,4,0xabcdef12)==0);
    assert(x86os_display_frame_commit(serial+1)==-116);
    assert(x86os_display_frame_cancel(serial)==0);
    drain(); assert(screen[0]==0);
    assert(x86os_display_frame_begin(&serial)==0);
    assert(x86os_fill_rect(-2,-2,4,4,0xabcdef12)==0);
    unsigned before=calls; uint64_t next=0;
    assert(reist_desktop_display_pump(&next)==-16 && calls==before);
    assert(x86os_display_frame_commit(serial)==0);
    drain(); assert(screen[0]==0xcdef12 && screen[1]==0xcdef12 && screen[2]==0);
    assert(x86os_fill_rect(INT32_MAX,INT32_MIN,UINT32_MAX,UINT32_MAX,7)==0);
    uint32_t pix[6]={1,2,3,4,5,6};
    assert(x86os_draw_pixels(-1,5,3,2,pix,3)==0);
    assert(x86os_draw_pixels(0,0,3,2,pix,2)==-22);
    assert(x86os_draw_pixels(0,0,2,2,(const uint32_t *)(UINTPTR_MAX-3),2)==-22);
    assert(x86os_draw_text_pixels(20,20,"A",1,0xffffff,0)==0);
    assert(x86os_draw_text_pixels(0,0,"\xc0\x80",2,0xffffff,0)==-22);
    assert(x86os_draw_text_pixels(0,0,(const char *)a,1,1,0)==-22);
    assert(x86os_draw_text_pixels(70,70,"\xc3\x84",2,0x789abc,0)==0);
    assert(x86os_draw_text_pixels_clipped(40,20,"A",1,0x123456,0,42,22,1,1)==0);
    drain(); assert(screen[5*1024]==2 && screen[6*1024]==5);
    assert(screen[20*1024+20]==0xffffff && screen[22*1024+42]==0x123456 && !screen[22*1024+41]);
    assert(screen[70*1024+70]==0x789abc && !screen[70*1024+71]);
    assert(x86os_display_frame_begin(&serial)==0);
    assert(x86os_fill_rect(20,20,8,16,0)==0);
    assert(x86os_display_frame_stage_blit(serial,20,20,21,20,8,16)==-95);
    assert(x86os_display_frame_cancel(serial)==0);
    assert(x86os_display_frame_begin(&serial)==0);
    assert(x86os_display_frame_stage_blit(serial,20,20,21,20,8,16)==0);
    assert(x86os_display_frame_stage_blit(serial,20,20,21,20,8,16)==-16);
    assert(x86os_fill_rect(20,20,8,16,0)==0);
    assert(x86os_display_frame_commit(serial)==0);
    drain(); assert(!screen[20*1024+20] && screen[20*1024+21]==0xffffff);
    assert(x86os_pointer_update(100,100,1)==0); drain();
    assert(screen[100*1024+100]==0xffffff);
    assert(x86os_pointer_update(200,200,1)==0); drain();
    assert(!screen[100*1024+100] && screen[200*1024+200]==0xffffff);
    assert(x86os_pointer_update(0,0,0)==0); drain(); assert(!screen[200*1024+200]);
    assert(x86os_fill_rect(0,0,1024,768,0x112233)==0);
    now+=100; /* Begin this boundary check after all prior sends have expired. */
    before=calls; unsigned full=0;
    while(calls-before<64) { assert(reist_desktop_display_pump(&next)==1); if(next>now) now=next; assert(++full<100); }
    unsigned held=calls; assert(reist_desktop_display_pump(&next)==1 && calls==held && next>now);
    drain(); assert(screen[1024*768-1]==0x112233);
    assert(x86os_display_surface_buffer_draw(1,1,1,1,0,0,0,0,1,1)==-95);
    assert(x86os_display_frame_mark_accelerated(1)==-95);
    assert(x86os_fill_rect(0,0,1,1,0)==0);
    fail_at=calls+1; now+=100;
    assert(reist_desktop_display_pump(&next)==-116);
    before=calls; assert(reist_desktop_display_pump(&next)==-116 && calls==before);
    reist_desktop_display_detach();
    assert(reist_desktop_display_attach(&c)==-116);
    epoch++; c=config(); fail_at=0; assert(reist_desktop_display_attach(&c)==0);
    assert(x86os_display_activate()==0); now--;
    assert(reist_desktop_display_pump(&next)==-84);
    reist_desktop_display_detach(); reist_desktop_display_detach();
    assert(x86os_fill_rect(0,0,1,1,1)==-19);
    epoch++; now+=200; c=config(); c.width=800; c.height=600;
    assert(reist_desktop_display_attach(&c)==0 && x86os_display_activate()==0);
    assert(x86os_fill_rect(0,0,800,600,0x654321)==0);
    drain(); assert(edge_tiles && screen[599*1024+799]==0x654321);
    assert(x86os_display_deactivate()==0 && reist_desktop_display_pump(&next)==-19);
    assert(x86os_display_activate()==0); drain();
    reist_desktop_display_detach();
    puts("display: raster, transaction, cursor, quota and lifecycle passed");
    return 0;
}
