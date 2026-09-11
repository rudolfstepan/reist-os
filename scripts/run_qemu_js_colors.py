"""Real shell JavaScript colors: exact transcripts, pixels and recovery."""
from collections import Counter
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import uuid
import run_qemu_smoke as smoke
from run_qemu_runtime_desktop import BrowserInputMonitor, read_ppm
from measure_cpp_baseline import suppress_windows_test_dialogs
from verify_js_colors_artifacts import ROOT, EVIDENCE, FB_IMAGE
from run_qemu_js_runner import mandelbrot_reference

def validate_boot(text):
    # TEST_OK belongs to explicitly invoked GTEST, not normal shell boot.
    # Require the actual ordered automatic recovery self-test and BOOT_OK.
    after = 0
    for marker in (*smoke.REIST_PROBE_MARKERS, smoke.REIST_PROBE_COMPLETION_MARKER, 'BOOT_OK'):
        matches = list(re.finditer(r'(?m)^'+re.escape(marker)+r'\r?$', text))
        if len(matches) != 1 or matches[0].start() < after:
            raise ValueError('missing/duplicate/reordered boot self-test: '+marker)
        after = matches[0].end()


def validate_pixels(picture, framebuffer=True):
    if not picture:
        raise ValueError('missing screenshot')
    width, height, pixels = picture
    if width <= 0 or height <= 0 or width*height > 16*1024*1024 or len(pixels) != width*height*3:
        raise ValueError('invalid screenshot geometry')
    colors = Counter(zip(pixels[0::3], pixels[1::3], pixels[2::3]))
    # The reference VGA DAC screenshot expands the base channel to168;
    # the explicit ARGB framebuffer palette uses170. No fuzzy color match.
    level = 170 if framebuffer else 168
    for rgb in ((level,0,0), (0,level,0), (0,0,level), (255,255,255)):
        if colors[rgb] < 32:
            raise ValueError('missing glyph pixels: '+str(rgb))


def expected_colors():
    names = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
    return ['JS_COLOR_BEGIN'] + [
        f"PALETTE {i} "+('bright-' if i >= 8 else '')+names[i % 8] for i in range(16)
    ] + ['x'*130, 'MULTI_A', 'MULTI_B', 'SANITIZE ????',
         'RED xxxxxxxxxxxxxxxx', 'GREEN xxxxxxxxxxxxxxxx',
         'BLUE_STDERR xxxxxxxxxxxxxxxx', 'DEFAULT wwwwwwwwwwwwwwww',
         'JS_COLOR_OK rejected=8']


def validate_transcript(text):
    normalized = text.replace('\r\n', '\n')
    if smoke.failure_marker(text) or any(s in text for s in
            ('KERNEL PANIC', 'REJECTED_COLOR_PREFIX', 'USER PROCESS PAGE FAULT', '*** USER PROCESS')):
        raise ValueError('failed JS color guest')
    colors = re.findall(r'^JS_COLOR_BEGIN\n(.*?)^JS_COLOR_OK rejected=8\n', normalized, re.M | re.S)
    wanted = '\n'.join(expected_colors()[1:-1])+'\n'
    if colors != [wanted, wanted] or normalized.count('JS_COLOR_BEGIN') != 2 or normalized.count('JS_COLOR_OK rejected=8') != 2:
        raise ValueError('missing/duplicate/changed color records')
    pattern = r'^MANDELC_BEGIN width=64 height=24 iterations=48\n(.*?)^MANDELC_END\nJS_COLOR_MANDEL_OK\n'
    pictures = re.findall(pattern, normalized, re.M | re.S)
    if pictures != ['\n'.join(mandelbrot_reference())+'\n'] or normalized.count('MANDELC_BEGIN') != 1 or normalized.count('MANDELC_END') != 1 or normalized.count('JS_COLOR_MANDEL_OK') != 1:
        raise ValueError('missing/changed Mandelbrot')
    receipts = re.findall(r'(?m)^(?:JS_COLOR_BEGIN|JS_COLOR_OK rejected=8|js: script exception|MANDELC_BEGIN width=64 height=24 iterations=48|JS_COLOR_MANDEL_OK|HOST_JS_COLOR_SHELL_OK)$', normalized)
    if receipts != ['JS_COLOR_BEGIN', 'JS_COLOR_OK rejected=8', 'js: script exception',
                    'JS_COLOR_BEGIN', 'JS_COLOR_OK rejected=8',
                    'MANDELC_BEGIN width=64 height=24 iterations=48', 'JS_COLOR_MANDEL_OK', 'HOST_JS_COLOR_SHELL_OK']:
        raise ValueError('missing/reordered shell recovery receipts')

def guest_failed(text, boot_end):
    # Automatic recovery intentionally faults a process during boot. Admission
    # requires every ordered boot receipt; no fault is allowed in the JS phase.
    return bool(smoke.failure_marker(text)) or 'KERNEL PANIC' in text or (
        boot_end is not None and '*** USER PROCESS' in text[boot_end:])


def run(image, folder, framebuffer):
    start = time.monotonic(); deadline = start+180
    listener, port = smoke.open_injection_listener()
    command = smoke.qemu_command(Path('C:/Program Files/qemu/qemu-system-i386.exe'),
                                 image, memory='1024M', nic='e1000', smp=1)
    command += ['-device', 'VGA', '-qmp', f'tcp:127.0.0.1:{port},server=off,nodelay=on']
    process = None; monitor = None
    stopped = threading.Event(); overflow = threading.Event(); chunks = queue.Queue(65536)
    transcript = ''; thread = None; begin = None

    def reader():
        while not stopped.is_set():
            c = process.stdout.read(1)
            if not c: return
            try: chunks.put(c, timeout=1)
            except queue.Full: overflow.set(); return

    def drain():
        nonlocal transcript
        batch = []
        for _ in range(65536):
            try: batch.append(chunks.get_nowait())
            except queue.Empty: break
        if len(transcript)+len(batch) > 4*1024*1024:
            raise ValueError('transcript capacity')
        transcript += ''.join(batch)

    def wait(marker, after):
        while time.monotonic() < deadline:
            drain()
            if overflow.is_set() or guest_failed(transcript, begin):
                raise ValueError('guest failed/overflow')
            found = transcript.find(marker, after)
            if found >= 0: return found+len(marker)
            if process.poll() is not None: raise ValueError('QEMU exited before '+marker)
            stopped.wait(0.01)
        raise TimeoutError('guest deadline before '+marker)

    def send(text):
        special = {' ': 'spc', '-': 'minus', '/': 'slash', '.': 'dot'}
        for c in text:
            if time.monotonic() >= deadline: raise TimeoutError('injection deadline')
            monitor.key(special.get(c, c)); stopped.wait(0.075)
        monitor.key('ret')

    error = None
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=0,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        thread = threading.Thread(target=reader, daemon=True); thread.start()
        smoke.configure_qemu_host_timers(process)
        monitor = BrowserInputMonitor.accept(listener, deadline)
        at = wait(smoke.SHELL_PROMPT, 0)
        validate_boot(transcript[:at])
        begin = at
        for repetition in range(2):
            send('cls'); at = wait(smoke.SHELL_PROMPT, at)
            send('js /htdocs/jscolors.js')
            at = wait('JS_COLOR_OK rejected=8\n', at); at = wait(smoke.SHELL_PROMPT, at)
            picture = folder/f'colors-{repetition}.ppm'
            monitor.execute('screendump', {'filename': str(picture)})
            decoded = read_ppm(picture); validate_pixels(decoded, framebuffer)
            if framebuffer != (decoded[0] >= 800 and decoded[1] >= 600):
                raise ValueError('wrong VGA/framebuffer display mode')
            if not repetition:
                send('js /htdocs/jscolors.js fail')
                at = wait('js: script exception\n', at); at = wait(smoke.SHELL_PROMPT, at)
        send('js /htdocs/mandelc.js')
        at = wait('JS_COLOR_MANDEL_OK\n', at); at = wait(smoke.SHELL_PROMPT, at)
        picture = folder/'mandelc.ppm'
        monitor.execute('screendump', {'filename': str(picture)})
        validate_pixels(read_ppm(picture), framebuffer)
        send('help'); at = wait('Built-ins: cd path pwd history help exit', at)
        at = wait(smoke.SHELL_PROMPT, at)
        transcript += '\nHOST_JS_COLOR_SHELL_OK\n'
        validate_transcript(transcript[begin:])
    except (OSError, ValueError, RuntimeError, TimeoutError) as caught:
        error = str(caught)
    finally:
        stopped.set()
        if monitor: monitor.peer.close()
        listener.close()
        if process: smoke.stop_process(process)
        if thread: thread.join(timeout=2)
        try: drain()
        except ValueError as caught: error = str(caught)
        if process:
            for stream in (process.stdin, process.stdout):
                if stream: stream.close()
        (folder/'guest.log').write_text(transcript, encoding='utf-8')
    print(f"JS_COLOR_GUEST {'framebuffer' if framebuffer else 'vga'} "+
          ('FAIL: '+error if error else 'PASS')+f' elapsed={time.monotonic()-start:.3f}s log={folder}')
    return error is None


def main():
    suppress_windows_test_dialogs()
    subprocess.run(['C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-Command',
        "$busy=@(Get-Process qemu-system-i386,qemu-system-x86_64,vmware-vmx,zig,clang,gcc,cc1,nasm,ld,lld -ErrorAction SilentlyContinue); if ($busy.Count) { throw 'Concurrent VM/compiler' }; exit 0"],
        check=True, capture_output=True, timeout=15, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for mode, image in (('vga', ROOT/'build/reist-os.img'), ('framebuffer', FB_IMAGE)):
        folder = EVIDENCE/(mode+'-'+uuid.uuid4().hex); folder.mkdir(parents=True)
        if not run(image, folder, mode=='framebuffer'): return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
