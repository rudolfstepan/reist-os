"""Actual bounded WM/parser behavior for the two Display options."""
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'test'))
import test_display_settings as builder
from test_display_abi_minimal import function

class WindowOptionsTests(unittest.TestCase):
    def test_initial_command_uses_existing_injector(self):
        from run_qemu_display_window_options import INITIAL_COMMAND
        from run_qemu_runtime_desktop import monitor_key_commands
        with self.assertRaises(ValueError):monitor_key_commands('config set desktop window_shadows true')
        self.assertTrue(monitor_key_commands(INITIAL_COMMAND))

    def test_pixel_oracles_fail_closed(self):
        from run_qemu_display_window_options import check_boxes,check_shadow,check_drag
        rect=(90,80,620,452)
        data=bytearray(b'\xff'*1024*768*3)
        def set_pixel(x,y,color):
            at=(y*1024+x)*3;data[at:at+3]=color
        def ppm():return (1024,768,bytes(data))
        check_boxes(ppm(),rect,0,0)
        with self.assertRaises(RuntimeError):check_boxes(ppm(),rect,1,0)
        set_pixel(114,416,b'\x20'*3);check_boxes(ppm(),rect,1,0)
        with self.assertRaises(RuntimeError):check_boxes(ppm(),rect,0,0)
        check_shadow(ppm(),rect,0)
        with self.assertRaises(RuntimeError):check_shadow(ppm(),rect,1)
        for i in range(50,201,10):set_pixel(90+i,536,b'\x18'*3)
        check_shadow(ppm(),rect,1)
        with self.assertRaises(RuntimeError):check_shadow(ppm(),rect,0)
        with self.assertRaises(RuntimeError):check_drag(ppm(),rect,80,50,0)
        for i in range(400,440):set_pixel(90+i,68,b'\x00\x00\x88')
        # Keeping the original title on a white canvas is not an outline.
        with self.assertRaises(RuntimeError):check_drag(ppm(),rect,80,50,0)
        for i in range(580,600):
            set_pixel(170+i,103,b'\xff'*3);set_pixel(170+i,583,b'\x18'*3)
        for i in range(40,161,10):set_pixel(791,130+i,b'\x18'*3)
        check_drag(ppm(),rect,80,50,0)
        # Each missing or wrong-color edge independently fails closed.
        for x,y in ((750,103),(750,583),(791,170)):
            old=pixel=bytes(data[(y*1024+x)*3:(y*1024+x)*3+3])
            set_pixel(x,y,b'\x88'*3)
            with self.assertRaises(RuntimeError):check_drag(ppm(),rect,80,50,0)
            set_pixel(x,y,old)
        with self.assertRaises(RuntimeError):check_drag(ppm(),rect,80,50,1)
        for i in range(400,440):set_pixel(90+80+i,118,b'\x00\x00\x88')
        check_drag(ppm(),rect,80,50,1)
        with self.assertRaises(RuntimeError):check_drag(ppm(),rect,80,50,0)

    def generated(self,name,code,sources):
        folder=ROOT/'build/codex-agent/r346-window-options/host';folder.mkdir(parents=True,exist_ok=True)
        path=folder/(name+'.c');path.write_text(code,encoding='utf-8')
        builder.DisplaySettingsTests().compile_and_run(name,[str(path),*sources])

    def test_actual_window_manager(self):
        builder.DisplaySettingsTests().compile_and_run('window-options',
            ['test/display_window_options_host.c','userspace/gui/compositor/desktop_wm.c',
             'userspace/config/lib/display_settings.c'])

    def test_actual_config_validation(self):
        source=(ROOT/'userspace/services/config/config_service.c').read_text()
        code=source[source.index('typedef struct config_target'):source.index('static const config_target_t targets')]
        code+='\n'.join(function(source,n) for n in ('static size_t text_length(',
            'static uint32_t text_equal(','static uint32_t one_of(',
            'static uint32_t sound_path_valid(','static int parse_unsigned(','static int validate_setting('))
        self.generated('option-config','''#include <assert.h>
#include <stdio.h>
#include "reist/config.h"
#include "reist/display_settings.h"
'''+code+'''
int main(void) {
    config_target_t target={"desktop",0,0,0};
    const char *keys[]={"window_shadows","drag_contents"};
    const char *bad[]={"", "1", "0", "TRUE", "false ", " true"};
    for(unsigned k=0;k<2;++k) {
        assert(!validate_setting(&target,keys[k],"true"));
        assert(!validate_setting(&target,keys[k],"false"));
        for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);++i) assert(validate_setting(&target,keys[k],bad[i])==-22);
        target.name="input";assert(validate_setting(&target,keys[k],"true")==-22);target.name="desktop";
    }
    assert(!validate_setting(&target,"resolution","1280x720"));
    puts("DISPLAY_TEST_OK actual_config_validation");return 0;
}
''',['userspace/config/lib/display_settings.c'])

    def test_actual_outline_renderer(self):
        source=(ROOT/'userspace/gui/compositor/desktop.c').read_text()
        self.generated('option-render','''#include <assert.h>
#include <stdio.h>
#include "userspace/gui/compositor/desktop_wm.h"
typedef struct {int ignored;} desktop_render_context_t;
static const uint32_t color_title_text=0xffffff,color_dark=0x181818;
static desktop_rect_t rects[4];static unsigned count;
static void fill_rect_clipped(const desktop_render_context_t *c,desktop_rect_t r,uint32_t color) {
    (void)c;assert(color==color_title_text || color==color_dark);assert(count<4);rects[count++]=r;
}
'''+function(source,'static void render_move_outline(')+'''
int main(void) {
    desktop_wm_t wm;desktop_wm_initialize(&wm,1024,768,4,730,24);desktop_wm_open(&wm,0);
    wm.drag_contents=0;wm.capture_kind=DESKTOP_WM_CAPTURE_MOVE;wm.capture_window=0;
    wm.move_generation=wm.windows[0].generation;
    wm.move_preview=(desktop_rect_t){80,90,wm.windows[0].width,wm.windows[0].height};
    desktop_render_context_t context={0};render_move_outline(&context,&wm);assert(count==4);
    unsigned area=0;for(unsigned i=0;i<4;++i)area+=rects[i].width*rects[i].height;
    assert(area==4*(wm.move_preview.width+wm.move_preview.height)-16);
    assert(rects[0].x==80 && rects[0].y==90 && rects[0].height==2);
    count=0;wm.drag_contents=1;render_move_outline(&context,&wm);assert(!count);
    wm.drag_contents=0;++wm.move_generation;render_move_outline(&context,&wm);assert(!count);
    puts("DISPLAY_TEST_OK actual_outline_renderer");return 0;
}
''',['userspace/gui/compositor/desktop_wm.c'])

if __name__=='__main__':unittest.main()
