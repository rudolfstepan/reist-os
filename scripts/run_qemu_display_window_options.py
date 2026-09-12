"""Real native Display checkbox/persistence and shadow/drag pixel acceptance."""
from pathlib import Path
import re, sys, time, uuid
import run_qemu_display_settings as runtime
from run_qemu_runtime_desktop import read_ppm

BLUE=b'\x00\x00\x88'; DARK=b'\x18\x18\x18'; WHITE=b'\xff\xff\xff'
INITIAL_COMMAND='config set desktop resolution 1024x768'

def pixel(ppm,x,y):
    width,height,data=ppm
    if not (0<=x<width and 0<=y<height):raise RuntimeError('pixel outside scanout')
    at=(y*width+x)*3;return data[at:at+3]

def check_boxes(ppm,rect,shadows,contents):
    x,y,w,h=rect
    for index,expected in enumerate((shadows,contents)):
        # Inside the native check glyph, away from bevel, text and focus.
        observed=pixel(ppm,x+24,y+h-130+index*26+14)
        if observed!=(b'\x20\x20\x20' if expected else WHITE):
            raise RuntimeError(f'checkbox pixel mismatch index={index} actual={observed.hex()}')

def check_shadow(ppm,rect,enabled):
    x,y,w,h=rect
    samples=[pixel(ppm,x+offset,y+h+4) for offset in range(50,201,10)]
    if enabled and any(p!=DARK for p in samples):raise RuntimeError('window shadow missing')
    if not enabled and any(p==DARK for p in samples):raise RuntimeError('disabled window shadow still drawn')

def check_drag(ppm,rect,dx,dy,contents):
    x,y,w,h=rect
    stripe=[pixel(ppm,x+dx+i,y+dy-12) for i in range(400,440)]
    if contents and any(p!=BLUE for p in stripe):raise RuntimeError('moved title/content absent')
    if not contents:
        if any(p==BLUE for p in stripe):raise RuntimeError('content moved during outline capture')
        if any(pixel(ppm,x+i,y-12)!=BLUE for i in range(400,440)):
            raise RuntimeError('original title moved during outline capture')
        # Sample beyond the old client's right edge: its white background
        # must not impersonate a missing outline. Require both edge colors.
        for i in range(w-40,w-20):
            if (pixel(ppm,x+dx+i,y+dy-27)!=WHITE or
                pixel(ppm,x+dx+i,y+dy+h+1)!=DARK):
                raise RuntimeError('outline top/bottom edge absent')
        if any(pixel(ppm,x+dx+w+1,y+dy+i)!=DARK for i in range(40,161,10)):
            raise RuntimeError('outline right edge absent')

class WindowOptionsProof(runtime.DisplayProof):
    def capture(self,name,rect=None):
        path=self.screenshot(name,rect)
        ppm=read_ppm(path)
        if ppm is None:raise RuntimeError('missing ppm '+name)
        return ppm

    def options(self,shadows,contents,offset):
        self.wait(f'DISPLAY_OPTIONS_READY shadows={shadows} contents={contents}'+r'\r?\n',offset)

    def drag(self,rect,contents,name):
        x,y,w,h=rect;dx,dy=80,50
        self.move(x+120,y-12)
        self.monitor.mouse(self.process,'mouse_button 1');time.sleep(.08)
        self.move(x+120+dx,y-12+dy)
        check_drag(self.capture(name+'-held'),rect,dx,dy,contents)
        self.monitor.mouse(self.process,'mouse_button 0');time.sleep(.08)
        moved=(x+dx,y+dy,w,h)
        check_drag(self.capture(name+'-released',moved),rect,dx,dy,1)
        return moved

    def run(self):
        first=self.wait(r'DESKTOP_OK|'+re.escape(runtime.SHELL_PROMPT))
        if first[0]=='DESKTOP_OK':
            mode=re.findall(r'DESKTOP_MODE_ACTIVE width=(\d+) height=(\d+)',self.text())[-1]
            self.width,self.height=map(int,mode);self.x,self.y=self.width//2,self.height//2
            self.close_desktop(False)
        self.command('help',runtime.SHELL_HELP_MARKER)
        self.command('display --list','DISPLAY_COMMAND_READY')
        # A snapshot-only config update fixes geometry for exact pixel probes.
        # Both new defaults must be read from the actual packaged config;
        # the existing PS/2 injector intentionally has no underscore mapping.
        self.command(INITIAL_COMMAND,'CONFIG_UPDATE_OK')
        states=((1,1),(0,0),(1,0),(0,1))
        results=[]
        for index,(shadows,contents) in enumerate(states):
            offset,control=self.desktop((1024,768))
            self.wait(f'DESKTOP_WINDOW_OPTIONS shadows={shadows} contents={contents}',offset)
            _,rect=self.open_applet(control)
            self.options(shadows,contents,offset)
            ppm=self.capture(f'{index}-initial',rect)
            check_boxes(ppm,rect,shadows,contents);check_shadow(ppm,rect,shadows)
            rect=self.drag(rect,contents,str(index))
            check_shadow(self.capture(f'{index}-shadow-after-move'),rect,shadows)
            if index+1<len(states):
                target=states[index+1];draft=[shadows,contents]
                for field in range(2):
                    if draft[field]==target[field]:continue
                    offset=len(self.text());x,y,w,h=rect
                    # Full label click, not only the checkbox square.
                    self.click(x+140,y+h-130+field*26+12)
                    draft[field]=target[field];self.options(*draft,offset)
                check_boxes(self.capture(f'{index}-draft',rect),rect,*target)
                offset=len(self.text());x,y,w,h=rect
                self.click(x+50,y+h-57)
                self.wait('DISPLAY_SETTINGS_SAVED 1024x768',offset)
                if 'DESKTOP_MODE_ACTIVE' in self.text()[offset:]:raise RuntimeError('unexpected live mode change')
            self.close_desktop()
            results.append(dict(shadows=shadows,contents=contents,pixels=True,persisted=True))
        text=self.text().replace('\r\n','\n')
        if text.count('\nBOOT_OK\n')!=1:raise RuntimeError('missing unique boot witness')
        boot,guest=text.split('\nBOOT_OK\n')
        if any(s in guest for s in ('USER PROCESS EXCEPTION','USER PROCESS PAGE FAULT','DISPLAY_APPLET_FAULT')):
            raise RuntimeError('unexpected applet/client fault')
        for marker in (*runtime.REIST_PROBE_MARKERS,runtime.REIST_PROBE_COMPLETION_MARKER):
            if marker not in boot:raise RuntimeError('missing original boot self-test')
        return dict(options=results,shell_return=True)

def main():
    # Reuse the unchanged 180s/1CPU/1GiB snapshot VM lifecycle and stop handling.
    runtime.DisplayProof=WindowOptionsProof
    # Every focused retry retains the previous failure and its raw screenshots.
    index=sys.argv.index('--evidence')+1
    sys.argv[index]=str(Path(sys.argv[index])/('attempt-'+uuid.uuid4().hex))
    sys.argv[1:1]=['--qemu','C:/Program Files/qemu/qemu-system-i386.exe']
    return runtime.main()

if __name__=='__main__':raise SystemExit(main())
