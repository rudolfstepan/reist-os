#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "userspace/gui/compositor/desktop_wm.h"
#include "reist/display_settings.h"
static desktop_wm_t wm;
static desktop_wm_dispatch_result_t out;
static void event(unsigned type,int x,int y,unsigned pressed) {
    desktop_wm_event_t e={.type=type,.x=x,.y=y,.button=DESKTOP_WM_BUTTON_LEFT,.pressed=pressed};
    assert(!desktop_wm_dispatch(&wm,&e,&out));
}
static void setup(unsigned shadows,unsigned contents) {
    desktop_wm_initialize(&wm,1024,768,4,730,24);
    assert(wm.window_shadows==1 && wm.drag_contents==1);
    assert(!desktop_wm_set_visual_options(&wm,shadows,contents));
    desktop_wm_open(&wm,0);
    wm.windows[0].x=120;wm.windows[0].y=110;wm.windows[0].width=400;wm.windows[0].height=260;
}
int main(void) {
    uint32_t value=77;
    assert(!reist_display_bool_parse(NULL,&value) && value==1);
    assert(!reist_display_bool_parse("false",&value) && value==0);
    assert(!reist_display_bool_parse("true",&value) && value==1);
    const char *bad[]={"","0","1","TRUE","False"," true","false ","truex"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);++i) {
        assert(reist_display_bool_parse(bad[i],&value)==-22 && value==1);
    }
    assert(reist_display_bool_parse("true",NULL)==-22);
    for(unsigned s=0;s<2;++s)for(unsigned c=0;c<2;++c) {
        setup(s,c);
        assert(desktop_wm_window_bounds(&wm,0).width==400+4*s);
        desktop_wm_t before=wm;
        assert(desktop_wm_set_visual_options(&wm,2,0)==-22 && !memcmp(&wm,&before,sizeof(wm)));
        event(DESKTOP_WM_EVENT_POINTER_BUTTON,220,122,1);
        assert(wm.capture_kind==DESKTOP_WM_CAPTURE_MOVE);
        assert(desktop_wm_set_visual_options(&wm,1,1)==-16);
        event(DESKTOP_WM_EVENT_POINTER_MOTION,320,202,0);
        desktop_rect_t r;
        assert(desktop_wm_move_outline(&wm,&r)==!c);
        assert(wm.windows[0].x==(c?220:120) && wm.windows[0].y==(c?190:110));
        if(!c) {
            assert(r.x==220 && r.y==190 && r.width==400 && r.height==260);
            uint64_t area=0;
            for(unsigned i=0;i<out.dirty.count;++i)area+=(uint64_t)out.dirty.rects[i].width*out.dirty.rects[i].height;
            assert(!out.dirty.full && area<20000); /* Edge bands, never full client. */
        }
        event(DESKTOP_WM_EVENT_POINTER_BUTTON,320,202,0);
        assert(wm.windows[0].x==220 && wm.windows[0].y==190);
        assert(!desktop_wm_move_outline(&wm,&r) && !wm.move_generation);
        /* Same geometry constraints, including integer extremes. */
        event(DESKTOP_WM_EVENT_POINTER_BUTTON,320,202,1);
        event(DESKTOP_WM_EVENT_POINTER_MOTION,INT32_MAX,INT32_MAX,0);
        event(DESKTOP_WM_EVENT_POINTER_BUTTON,INT32_MAX,INT32_MAX,0);
        assert(wm.windows[0].x+400<=wm.work_right && wm.windows[0].y+260<=wm.work_bottom);
    }
    for(unsigned cancel=0;cancel<3;++cancel) {
        setup(1,0);event(DESKTOP_WM_EVENT_POINTER_BUTTON,220,122,1);
        event(DESKTOP_WM_EVENT_POINTER_MOTION,320,202,0);
        if(cancel==0) {
            desktop_wm_event_t e={.type=DESKTOP_WM_EVENT_KEYBOARD,.key=DESKTOP_WM_KEY_ESCAPE};
            assert(!desktop_wm_dispatch(&wm,&e,&out));
            assert(!(out.flags&DESKTOP_WM_RESULT_EXIT));
        } else if(cancel==1) {
            desktop_wm_event_t e={.type=DESKTOP_WM_EVENT_CLOSE,.target=0};
            assert(!desktop_wm_dispatch(&wm,&e,&out));desktop_wm_open(&wm,0);
        } else ++wm.windows[0].generation;
        event(DESKTOP_WM_EVENT_POINTER_BUTTON,320,202,0);
        assert(wm.windows[0].x==120 && wm.windows[0].y==110);
        desktop_rect_t r;assert(!desktop_wm_move_outline(&wm,&r));
    }
    puts("DISPLAY_TEST_OK options defaults parser bounded_outline cancel_generation release");return 0;
}
