"""Behavior of the production startup lifecycle and role parser, both profiles."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig

class StartupTests(unittest.TestCase):
    def test_client_idle_receive(self):
        source=(ROOT/'userspace/gui/apps/native_client.c').read_text()
        start=source.index('        for(unsigned n=0;n<8;n++)')
        end=source.index('        now=reist_native_now();',start)
        fragment=source[start:end]
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('client-wait-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        code=r'''#include <assert.h>
#define REIST_GRAPHICAL_START_MS 10000U
#define REIST_NATIVE_CLIENT 0
#define REIST_GUI_SURFACE_CLOSE 128
#define REIST_GUI_SURFACE_INPUT 129
#define REIST_GUI_SURFACE_INPUT_KEYBOARD 3
#define REIST_GUI_SURFACE_INPUT_POINTER_MOTION 1
#define REIST_GUI_SURFACE_INPUT_POINTER_BUTTON 2
typedef struct {unsigned type;struct {unsigned serial,reserved,type,pressed,key;int x,y;} input;} reist_gui_surface_message_t;
static int client,mode;static unsigned calls,first_wait,text_size,pointer_x,pointer_y,pressed;static char text[40];
static int reist_gui_surface_client_receive(int *c,reist_gui_surface_message_t *m,unsigned wait){
 (void)c;if(!calls)first_wait=wait;calls++;
 if(mode==0)return -110;
 if(mode==1 && calls==1){*m=(reist_gui_surface_message_t){129,{1,0,3,1,97,0,0}};return 0;}
 if(mode==2)return -71;
 return -11;}
static int step(unsigned dirty){unsigned idle_waited=0;int r;
'''+fragment+r'''
 (void)dirty;return (int)idle_waited;}
int main(void){
 assert(step(0)==1 && calls==1 && first_wait==50);
 calls=0;mode=1;assert(step(0)==0 && calls==2 && first_wait==50 && text_size==1);
 calls=0;assert(step(1)==0 && first_wait==0);
 calls=0;mode=2;assert(step(0)==71 && calls==1);
 (void)pointer_x;(void)pointer_y;(void)pressed;return 0;}
'''
        from verify_x86_64_desktop_startup import run
        (folder/'wait.c').write_text(code)
        exe=folder/'wait.exe'
        run(['C:/msys64/mingw64/bin/gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',folder/'wait.c','-o',exe],folder/'build.log',40)
        run([exe],folder/'run.log',10)

    def test_text_damage_extent(self):
        source=(ROOT/'userspace/gui/apps/native_client.c').read_text()
        start=source.index('static int paint_update(void)')
        end=source.index('\n#else',start)
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('text-extent-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        code=r'''#include <assert.h>
#include <stdint.h>
#define REIST_GUI_SURFACE_INPUT 129
#define REIST_GUI_SURFACE_INPUT_KEYBOARD 3
typedef struct {unsigned id,generation;} handle;
typedef struct {unsigned type;struct {unsigned type,pressed,key,serial,reserved;} input;handle surface;} reist_gui_surface_message_t;
typedef struct client {struct client *event_owner;unsigned deferred_count,deferred_head;reist_gui_surface_message_t deferred[8];handle surface;} reist_gui_surface_client_t;
static reist_gui_surface_client_t client;
static unsigned text_size,width_seen;static char text[40];static int result;
static int reist_gui_surface_client_receive(reist_gui_surface_client_t *c,reist_gui_surface_message_t *m,unsigned timeout){(void)c;(void)m;(void)timeout;return -1;}
static int reist_gui_surface_client_dynamic_text(reist_gui_surface_client_t *c,unsigned x,unsigned y,unsigned width,const char *s,unsigned size,unsigned fg,unsigned bg){
 (void)c;(void)s;assert(x==12 && y==48 && size && size<=37 && fg==0xeaf2fa && bg==0x18222d);width_seen=width;return result;}
'''+source[start:end]+r'''
int main(void){
 text_size=1;assert(!paint_update() && width_seen==8);
 text_size=3;assert(!paint_update() && width_seen==24);
 text_size=2;assert(!paint_update() && width_seen==24);
 text_size=1;assert(!paint_update() && width_seen==16);
 text_size=37;assert(!paint_update() && width_seen==296);
 text_size=0;result=-11;assert(paint_update()==-11 && width_seen==296);
 result=0;text_size=1;assert(!paint_update() && width_seen==296);
 text_size=0;assert(!paint_update() && width_seen==8);
 return 0;}
'''
        from verify_x86_64_desktop_startup import run
        (folder/'extent.c').write_text(code)
        exe=folder/'extent.exe'
        run(['C:/msys64/mingw64/bin/gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror',folder/'extent.c','-o',exe],folder/'build.log',40)
        run([exe],folder/'run.log',10)

    def test_heartbeat_dispatch_slice(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/desktop_startup.c').read_text(encoding='utf-8')
        start=source.index('    if(now-s->heartbeat>=250')
        end=source.index('static int launch_service_send(',start)
        fragment=source[start:end]
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('heartbeat-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        code='''#include <stdint.h>
#include <assert.h>
#define REIST_GRAPHICAL_HEALTH 5
typedef struct {unsigned application_failed[2],application_closed[2],recovery[2];} channels;
typedef struct {channels channels;unsigned failed_apps,heartbeat_next;uint64_t heartbeat;} state;
static unsigned calls,roles[32];static uint64_t clock_value;
static int launch_send(state *s,unsigned type,unsigned role,unsigned flags){
 (void)s;assert(type==REIST_GRAPHICAL_HEALTH && flags==1 && calls<32);roles[calls++]=role;return 0;}
static int launch_clock(void *s,uint64_t *out){(void)s;*out=clock_value;return 0;}
static int step(state *s,uint64_t now){int r;clock_value=now;
'''+fragment+'''
int main(void){state s={0};
 assert(!step(&s,249) && !calls);
 assert(!step(&s,250) && calls==1 && roles[0]==0);
 assert(!step(&s,260) && calls==2 && roles[1]==1);
 assert(!step(&s,270) && calls==3 && roles[2]==2);
 assert(!step(&s,280) && calls==4 && roles[3]==3 && !s.heartbeat_next);
 assert(!step(&s,499) && calls==4);
 s.channels.recovery[0]=1;s.channels.application_closed[1]=1;
 assert(!step(&s,500) && calls==5 && roles[4]==0);
 assert(!step(&s,510) && calls==6 && roles[5]==1);
 assert(!step(&s,520) && calls==6 && !s.heartbeat_next);
 (void)launch_clock;return 0;}
'''
        (folder/'heartbeat.c').write_text(code,encoding='utf-8')
        from verify_x86_64_desktop_startup import run
        exe=folder/'heartbeat.exe'
        run(['C:/msys64/mingw64/bin/gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror',folder/'heartbeat.c','-o',exe],folder/'build.log',40)
        run([exe],folder/'run.log',10)

    def test_text_frame_start_cadence(self):
        source=(ROOT/'userspace/gui/apps/native_client.c').read_text(encoding='utf-8')
        start=source.index('        if(dirty && now-last_paint>=100)')
        end=source.index('        now=reist_native_now();if(now-heartbeat',start)
        fragment=source[start:end]
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('cadence-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        code='''#include <stdint.h>
#include <assert.h>
static uint64_t clock_value,last_paint;
static unsigned dirty,calls,paint_delay=150;
static int paint_error;
static uint64_t reist_native_now(void){return clock_value;}
static int paint_update(void){calls++;clock_value+=paint_delay;return paint_error;}
static int step(void){uint64_t now=reist_native_now();
'''+fragment+'''return 0;}
int main(void){
 clock_value=99;dirty=1;assert(!step() && !calls && dirty);
 clock_value=100;assert(!step() && calls==1 && !dirty && last_paint==100);
 paint_delay=50;dirty=1;assert(!step() && calls==2 && last_paint==250);
 clock_value=349;dirty=1;assert(!step() && calls==2 && dirty);
 clock_value=350;paint_error=-5;assert(step()==71 && dirty && last_paint==250);
 return 0;
}
'''
        (folder/'cadence.c').write_text(code,encoding='utf-8')
        from verify_x86_64_desktop_startup import run
        exe=folder/'cadence.exe'
        run(['C:/msys64/mingw64/bin/gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror',
             '-DREIST_GRAPHICAL_START_MS=10000','-DREIST_NATIVE_CLIENT=0',folder/'cadence.c','-o',exe],folder/'build.log',40)
        run([exe],folder/'run.log',10)

    def test_atomic_surface_behavior(self):
        from test_gui_surface_source import GuiSurfaceSourceTests
        for name in ('test_surface_manager_host_behavior',
                     'test_client_drains_input_backpressure_without_losing_events'):
            case=GuiSurfaceSourceTests(name)
            getattr(case,name)()

    def test_live_pointer_precedes_client_work(self):
        source=(ROOT/'userspace/gui/compositor/desktop.c').read_text(encoding='utf-8')
        start=source.index('        if (surface_input_queued) {')
        live=source.rfind('/* Native live pointer precedes client work.',0,start)
        self.assertGreater(live,source.index('        actions |= dispatch_pointer_motion(',source.index('    for (;;) {',source.index('int native_adopt_status'))))
        block=source[live:start]
        self.assertIn('desktop_pointer_present(',block)
        self.assertIn('desktop_pointer_present_completed(',block)

    def test_keyboard_pixel_proof(self):
        from verify_x86_64_desktop_startup import keyboard_glyphs
        font=(ROOT/'assets/fonts/reist-vga.psf').read_bytes()[32:32+4096]
        foreground=bytes.fromhex('eaf2fa');background=bytes.fromhex('18222d')
        pixels=bytearray(background*32*20)
        for y in range(16):
            for i,c in enumerate(b'abc'):
                for x in range(8):
                    at=((y+2)*32+4+i*8+x)*3
                    pixels[at:at+3]=foreground if font[c*16+y]&(128>>x) else background
        header=b'P6\n32 20\n255\n'
        self.assertEqual(keyboard_glyphs(header+pixels),[(4,2)])
        at=pixels.index(foreground);pixels[at]^=1
        self.assertEqual(keyboard_glyphs(header+pixels),[])
        cursor=bytearray(background*32*20);cursor[100:103]=bytes([255])*3
        self.assertEqual(keyboard_glyphs(header+cursor),[])

    def test_text_focus_oracle(self):
        from verify_x86_64_desktop_startup import text_focus_ready
        font=(ROOT/'assets/fonts/reist-vga.psf').read_bytes()[32:32+4096]
        bg=bytes.fromhex('18222d');fg=bytes.fromhex('a7bbce')
        pixels=bytearray(bg*1024*768);header=b'P6\n1024 768\n255\n'
        active=(750*1024+590)*3
        pixels[active:active+3]=bytes.fromhex('000088')
        self.assertFalse(text_focus_ready(header+pixels))
        for y in range(16):
            for i,c in enumerate(b'Type'):
                for x in range(8):
                    at=((y+20)*1024+20+i*8+x)*3
                    pixels[at:at+3]=fg if font[c*16+y]&(128>>x) else bg
        self.assertTrue(text_focus_ready(header+pixels))
        pixels[active:active+3]=bytes.fromhex('c8c8c8')
        self.assertFalse(text_focus_ready(header+pixels))

    def test_pixel_adapter(self):
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('pixel-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        p=subprocess.run([sys.executable,'test/test_x86_64_desktop_display.py','-v'],
                         cwd=ROOT,capture_output=True,timeout=120)
        (folder/'host.log').write_bytes(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-3000:])

    def test_selected_display_transactions(self):
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('selected-display-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        for level in ('-O0','-O2'):
            exe=folder/(level[1:]+'.exe')
            command=['C:/msys64/mingw64/bin/gcc.exe','-std=c11',level,'-Wall','-Wextra','-Werror',
                     '-DREIST_NATIVE_FULL_DESKTOP=1','-Iuserspace/sdk/include','-Iinclude',
                     'test/x86_64_desktop_display_host.c','userspace/sdk/lib/x86_64/desktop_display.c','-o',str(exe)]
            for stage,args in (('build',command),('run',[str(exe)])):
                p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60)
                (folder/(level[1:]+'-'+stage+'.log')).write_bytes(p.stdout+p.stderr)
                self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-3000:])

    def test_render_slices(self):
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('render-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        source=(ROOT/'userspace/gui/compositor/desktop.c').read_text(encoding='utf-8')
        start=source.index('static int render_native_startup(')
        end=source.index('/* End native startup slicing. */',start)
        (folder/'render.inc').write_text(source[start:end],encoding='utf-8')
        start=source.index('static int desktop_file_icon_cache_initialize(')
        end=source.index('static uint32_t draw_cached_file_icon(',start)
        (folder/'icons.inc').write_text(source[start:end],encoding='utf-8')
        start=source.index('static desktop_pointer_present_result_t desktop_pointer_present(')
        end=source.index('static void hover_probe_initialize(',start)
        (folder/'pointer.inc').write_text(source[start:end],encoding='utf-8')
        start=source.index('static desktop_rect_t native_surface_raster_damage(')
        end=source.index('\n#endif',start)
        (folder/'damage.inc').write_text(source[start:end],encoding='utf-8')
        start=source.index('static void native_surface_input_flush(')
        end=source.index('\n#endif',start)
        (folder/'flush.inc').write_text(source[start:end],encoding='utf-8')
        start=source.index('static void native_surface_keyboard_batch(')
        end=source.index('\n#endif',start)
        (folder/'batch.inc').write_text(source[start:end],encoding='utf-8')
        runtime=(ROOT/'userspace/gui/compositor/desktop_surface_runtime.c').read_text()
        start=runtime.index('static int poll_clients(')
        end=runtime.index('\nint desktop_surface_runtime_send_close(',start)
        (folder/'runtime.inc').write_text(runtime[start:end],encoding='utf-8')
        for variant,level in ((v,o) for v in ('old','full') for o in ('-O0','-O2')):
            exe=folder/(variant+level[1:]+'.exe')
            command=['C:/msys64/mingw64/bin/gcc.exe',level,'-Wall','-Wextra','-Werror',
                     '-DTEST_NATIVE_SURFACE_FAIR='+('1' if variant=='full' else '0'),
                     '-I'+str(folder),'test/x86_64_desktop_render_host.c','-o',str(exe)]
            for stage,args in (('build',command),('run',[str(exe)])):
                p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60)
                (folder/(variant+level[1:]+'-'+stage+'.log')).write_bytes(p.stdout+p.stderr)
                self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-3000:])

    def test_keyboard_observer_admission(self):
        import verify_x86_64_desktop_startup as v
        from unittest.mock import patch
        class Q:
            def __init__(self,failures,error):self.failures=failures;self.error=error;self.calls=0
            def call(self,name,args):
                self.calls+=1
                if self.calls<=self.failures:raise ValueError(self.error)
                return 'delivered'
        with patch.object(v.time,'sleep'):
            q=Q(3,"'desc': 'VM not running'")
            self.assertEqual(v.observer_inject(q,{}),'delivered');self.assertEqual(q.calls,4)
            q=Q(100,"'desc': 'VM not running'")
            with self.assertRaises(TimeoutError):v.observer_inject(q,{})
            self.assertEqual(q.calls,100)
            q=Q(1,'unrelated transport failure')
            with self.assertRaises(ValueError):v.observer_inject(q,{})
            self.assertEqual(q.calls,1)

    def test_sdk_startup(self):
        from verify_x86_64_desktop_startup import EVIDENCE,fixture_files,overlay,run
        folder=EVIDENCE/('sdk-host-'+uuid.uuid4().hex);folder.mkdir()
        with overlay(fixture_files(),folder/'fixture-overlay'):
            run([sys.executable,'test/test_x86_64_full_desktop.py',
                 'FullDesktopTests.test_platform','-v'],folder/'host.log',120)

    def test_replacement_broker(self):
        from verify_x86_64_desktop_startup import EVIDENCE,fixture_files,overlay,run
        folder=EVIDENCE/('broker-host-'+uuid.uuid4().hex);folder.mkdir()
        with overlay(fixture_files(),folder/'fixture-overlay'):
            run([sys.executable,'test/test_x86_64_full_desktop.py',
                 'FullDesktopTests.test_service_broker','-v'],folder/'host.log',120)

    def test_profiles(self):
        folder=ROOT/'build/codex-agent/r83cf-desktop-startup'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for full in (False,True):
            for opt in ('-O0','-O2'):
                name=('full' if full else 'old')+opt; exe=folder/(name+'.exe')
                command=[str(find_zig()),'cc','-target','x86_64-windows-gnu',opt,
                    '-Wall','-Wextra','-Werror','-fno-sanitize=all','-Wno-unused-command-line-argument',
                    '-Iuserspace/sdk/include','-Iuserspace/gui/include',
                    *(['-DTEST_FULL=1','-DREIST_NATIVE_FULL_DESKTOP_STARTUP=1'] if full else []),
                    'test/x86_64_desktop_startup_host.c',
                    'userspace/sdk/lib/x86_64/graphical_session.c',
                    'userspace/sdk/lib/x86_64/service_session.c','-o',str(exe)]
                for step,cmd in (('build',command),('run',[str(exe)])):
                    p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=40,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    (folder/(name+'-'+step+'.log')).write_bytes(p.stdout+p.stderr)
                    self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-2000:])
                    if step=='run':self.assertIn(b'DESKTOP_STARTUP_OK',p.stdout)

if __name__=='__main__':unittest.main()
