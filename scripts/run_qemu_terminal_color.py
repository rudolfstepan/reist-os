"""Headless real VGA and boot-framebuffer color/denial/reap/shell proof."""
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
from verify_terminal_color_artifacts import ROOT, EVIDENCE, FB_IMAGE

MARKERS = ['COLOR_ABI_OK', 'COLOR_DENIAL_OK', 'COLOR_REAP_OK',
           'COLOR_RESTART_OK', 'COLOR_TEST_OK', 'HOST_COLOR_SHELL_OK']


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


def validate_transcript(text):
    rows = re.findall(r'(?m)^(?:COLOR_[A-Z_]+|HOST_COLOR_SHELL_OK)\r?$', text)
    if [s.rstrip('\r') for s in rows] != MARKERS:
        raise ValueError('missing/duplicate/reordered color receipts')
    if smoke.failure_marker(text) or any(s in text for s in
            ('KERNEL PANIC', 'COLOR_TEST_FAIL', 'USER PROCESS PAGE FAULT', '*** USER PROCESS')):
        raise ValueError('failed color guest')


def run(image, folder, framebuffer):
    start = time.monotonic(); deadline = start+180
    listener, port = smoke.open_injection_listener()
    command = smoke.qemu_command(Path('C:/Program Files/qemu/qemu-system-i386.exe'),
                                 image, memory='1024M', nic='e1000', smp=1)
    command += ['-device', 'VGA', '-qmp', f'tcp:127.0.0.1:{port},server=off,nodelay=on']
    process = None; monitor = None
    stopped = threading.Event(); overflow = threading.Event(); chunks = queue.Queue(65536)
    transcript = ''; thread = None

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
            if overflow.is_set() or smoke.failure_marker(transcript) or 'COLOR_TEST_FAIL' in transcript:
                raise ValueError('guest failed/overflow')
            found = transcript.find(marker, after)
            if found >= 0: return found+len(marker)
            if process.poll() is not None: raise ValueError('QEMU exited before '+marker)
            stopped.wait(0.01)
        raise TimeoutError('guest deadline before '+marker)

    def send(text):
        special = {' ': 'spc', '-': 'minus'}
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
        send('colortst'); at = wait('COLOR_TEST_OK\n', at); at = wait(smoke.SHELL_PROMPT, at)
        # Native unknown-color handling must not publish its argument prefix.
        send('echo --color invalid rejected-prefix'); at = wait('echo: invalid color or text', at)
        at = wait(smoke.SHELL_PROMPT, at)
        send('cls'); at = wait(smoke.SHELL_PROMPT, at)
        for color in ('red', 'green', 'blue'):
            send('echo --color '+color+' xxxxxxxxxxxxxxxx')
            at = wait('\nxxxxxxxxxxxxxxxx\n', at); at = wait(smoke.SHELL_PROMPT, at)
        send('echo wwwwwwwwwwwwwwww'); at = wait('\nwwwwwwwwwwwwwwww\n', at)
        at = wait(smoke.SHELL_PROMPT, at)
        picture = folder/'colors.ppm'
        monitor.execute('screendump', {'filename': str(picture)})
        decoded = read_ppm(picture); validate_pixels(decoded, framebuffer)
        if framebuffer != (decoded[0] >= 800 and decoded[1] >= 600):
            raise ValueError('wrong VGA/framebuffer display mode')
        send('help'); at = wait('Built-ins: cd path pwd history help exit', at)
        at = wait(smoke.SHELL_PROMPT, at)
        transcript += '\nHOST_COLOR_SHELL_OK\n'
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
    print(f"TERMINAL_COLOR_GUEST {'framebuffer' if framebuffer else 'vga'} "+
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
