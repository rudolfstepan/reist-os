"""Bounded real quiescent parent exits: counts, raw status, exact retirement."""
from pathlib import Path
import argparse
import hashlib
import json
import queue
import re
import shutil
import struct
import subprocess
import threading
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, REQUIRED_MARKERS, FAILURES, SUCCESS
from run_qemu_x86_64_ipc_handoff import REAP
from run_qemu_x86_64_image_contexts import exit_address

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'REIST_X86_64_'
READY = PREFIX + 'RING3_SHELL_READY'
INFO = PREFIX + 'RING3_SHELL_INFO_OK'
RUN = PREFIX + 'RING3_SHELL_RUN_OK'
ERROR = PREFIX + 'RING3_SHELL_ERROR'
PARENT = re.compile(r'REIST_X86_64_SHELL_REAP_OK status=([0-9A-F]{8}) children=([0-9A-F]{2}) '
                    r'reaps=([0-9A-F]{2}) parent=([0-9A-F]{2}) last=([0-9A-F]{2})')
COMMON = tuple(m for m in REQUIRED_MARKERS if m not in (INFO, RUN))
MAX_TRACE = 256 * 1024


def loader_code(text, shell_size):
    # ELF32 container for BITS64: exactly five R_386_PC32 .rodata addends
    # follow the embedded shell, plus its immediate byte length. The real
    # accepted loader's opcodes and all other bytes must remain identical.
    # Offsets are frozen from its disassembly, not inferred from differences.
    if not 64 <= shell_size <= 8192 or len(text) != 2542:
        raise RuntimeError('loader code/fixture bounds')
    normalized = bytearray(text)
    delta = ((shell_size + 15) & ~15) - 3856
    for offset, baseline in ((0x4b,0x469c), (0x150,0x46b9), (0x2da,0x46cb),
                             (0x30c,0x46f1), (0x459,0x3f2c), (0x46e,3856)):
        expected = shell_size if offset == 0x46e else baseline + delta
        if struct.unpack_from('<I', text, offset)[0] != expected:
            raise RuntimeError('wrong loader embedding metadata')
        struct.pack_into('<I', normalized, offset, baseline)
    wanted = '78ecfa956075ed134c01828901165897a8136c47bf2cdf31795769e2b8f84654'
    if hashlib.sha256(normalized).hexdigest() != wanted:
        raise RuntimeError('loader mechanism code drift')
    return wanted


def validate(serial, children, info, status, rip=0x400010):
    if children not in (0, 1, 2) or not 0 <= status <= 0xffffffff:
        raise RuntimeError('invalid expected exit')
    if any(marker in serial for marker in FAILURES if marker != ERROR):
        raise RuntimeError('kernel failure during orderly exit')
    if serial.count(ERROR) != int(status != 0):
        raise RuntimeError('wrong legacy failure visibility')
    positions = [serial.find(marker) for marker in COMMON]
    if any(serial.count(m) != 1 for m in COMMON) or positions != sorted(positions):
        raise RuntimeError('missing/duplicate/out-of-order kernel cleanup witness')
    infos = list(re.finditer(INFO, serial))
    runs = list(re.finditer(RUN, serial))
    reaps = list(REAP.finditer(serial))
    parent = list(PARENT.finditer(serial))
    if (len(infos) != int(info) or len(runs) != children or len(reaps) != children or
            len(re.findall(r'CHILD_[A-Z]+_REAP_OK', serial)) != children or
            serial.count('SHELL_REAP_OK') != 1 or len(parent) != 1):
        raise RuntimeError('exit/reap/dialog receipt count')
    previous = serial.index(READY) + len(READY)
    if info:
        if infos[0].start() <= previous:
            raise RuntimeError('INFO precedes ready')
        previous = infos[0].end()
    for i, row in enumerate(reaps):
        child_status, generation, state, queued, address = (int(v, 16) for v in row.groups())
        if (child_status, generation, queued, address) != (77, 41+i, 0, rip) or state not in (1, 6, 7):
            raise RuntimeError('wrong child generation/status/cleanup')
        if not previous < row.start() < row.end() <= runs[i].start():
            raise RuntimeError('child reap must precede matching RUN')
        previous = runs[i].end()
    row = parent[0]
    if tuple(int(v, 16) for v in row.groups()) != (status, children, children+1, 40, 40+children):
        raise RuntimeError('wrong parent terminal receipt')
    if not previous < row.start() < row.end() <= serial.index(PREFIX+'RING3_SHELL_EXIT_OK'):
        raise RuntimeError('parent cleanup receipt order')
    if status and not row.end() < serial.index(ERROR) < serial.index(PREFIX+'SCHEDULED_SHELL_OK'):
        raise RuntimeError('nonzero program status not reported after cleanup')


def sample(children, info, status):
    """Synthetic transcript for negative oracle tests, never guest evidence."""
    at = COMMON.index(READY)
    lines = list(COMMON[:at+1])
    if info:
        lines.append(INFO)
    for i in range(children):
        lines.extend([PREFIX+f'CHILD_EXIT_REAP_OK status=0000004D generation={41+i:02X} '
                      'parent=01 queued=00 rip=0000000000400010', RUN])
    lines += [PREFIX+f'SHELL_REAP_OK status={status:08X} children={children:02X} '
              f'reaps={children+1:02X} parent=28 last={40+children:02X}', COMMON[at+1]]
    if status:
        lines.append(ERROR)
    return '\n'.join(lines + list(COMMON[at+2:])) + '\n'


def capture(image, folder, children, info):
    """One finite dialogue; no retries or disk attachment, including legacy red."""
    command = [str(resolve_qemu(None)), '-machine', 'pc,accel=tcg', '-cpu', 'qemu64',
               '-m', '128M', '-smp', '1', '-display', 'none', '-monitor', 'none',
               '-serial', 'stdio', '-no-reboot', '-no-shutdown', '-kernel', str(image.resolve())]
    (folder/'command.json').write_text(json.dumps(command), encoding='utf-8')
    output = queue.Queue(maxsize=128)
    overflow = threading.Event()
    captured = bytearray()
    with (folder/'stderr.log').open('wb') as errors:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=errors, bufsize=0, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        def reader():
            while chunk := process.stdout.read(256):
                try:
                    output.put_nowait(chunk)
                except queue.Full:
                    overflow.set()
                    return
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        actions = ([(READY, b'INFO\n')] if info else [])
        actions += [((INFO if info else READY) if i == 0 else RUN, b'RUN\n') for i in range(children)]
        actions += [((RUN if children else INFO if info else READY), b'EXIT\n')]
        sent = 0
        deadline = time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                try:
                    captured.extend(output.get(timeout=0.02))
                except queue.Empty:
                    pass
                if len(captured) > MAX_TRACE or overflow.is_set():
                    raise RuntimeError('bounded serial capacity exceeded')
                serial = captured.decode('ascii', errors='replace')
                if sent < len(actions):
                    marker, text = actions[sent]
                    required = (sent - int(info)) if marker == RUN else 1
                    if serial.count(marker) >= required:
                        process.stdin.write(text)
                        process.stdin.flush()
                        sent += 1
                if SUCCESS in serial or any(m in serial for m in FAILURES if m != ERROR):
                    break
                if process.poll() is not None:
                    break
        finally:
            process.stdin.close()
            terminate_bounded(process)
            thread.join(timeout=1)
            while not output.empty():
                captured.extend(output.get_nowait())
            process.stdout.close()
            (folder/'guest.log').write_bytes(captured)
    if overflow.is_set() or len(captured) > MAX_TRACE:
        raise RuntimeError('serial overflow')
    return captured.decode('ascii', errors='replace')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--legacy-image', type=Path)
    args = parser.parse_args()
    base = args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):
        parser.error('evidence outside workspace')
    attempt = base/('attempt-'+uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    summary = dict(passed=False, cases=[])
    started = time.monotonic()
    try:
        if args.legacy_image:
            serial = capture(args.legacy_image, attempt, 0, False)
            if ('REIST_X86_64_PROCESS_SCHEDULER_STAGE_54' not in serial or
                    PREFIX+'C_KERNEL_CONTROL_ERROR' not in serial or READY not in serial or
                    PREFIX+'RING3_SHELL_EXIT_OK' in serial or SUCCESS in serial):
                raise RuntimeError('old early-EXIT failure not reproduced')
            summary.update(passed=True, legacy_image_sha256=hashlib.sha256(args.legacy_image.read_bytes()).hexdigest())
            print('SHELL_EXIT_LEGACY_GUEST_OK actual_quiescent_exit_rejected=1 evidence='+str(attempt))
            return 0
        expected = None
        for status in (-1, 0, 42, 0x80000000, 0xffffffff):
            folder = attempt/str(status)
            folder.mkdir()
            command = ['powershell.exe', '-NoProfile', '-File', 'scripts/build-x86_64-bootstrap.ps1',
                       '-OutputDirectory', folder.relative_to(ROOT).as_posix(), '-ShellExitStatus', str(status)]
            with (folder/'build.log').open('wb') as out:
                result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, timeout=90,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                raise RuntimeError('build failed: '+str(folder/'build.log'))
            native = folder/'x86_64'
            # The loader embeds different user ELFs in .rodata, not in its
            # mechanism code. Compare its actual .text separately; entry.o
            # embeds only the unchanged C core and must match in full.
            hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in native.glob('*.o')
                      if p.name not in ('elf64_loader.o', 'user_shell.o')}
            objcopy = shutil.which('objcopy') or 'C:/msys64/mingw64/bin/objcopy.exe'
            text = native/'loader-text.bin'
            extraction = subprocess.run([objcopy, '-O', 'binary', '--only-section=.text',
                                        str(native/'elf64_loader.o'), str(text)],
                                       capture_output=True, timeout=10,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if extraction.returncode or not text.is_file() or not text.stat().st_size:
                raise RuntimeError('cannot extract loader mechanism code')
            shell_size = (native/'reist-x86_64-user-shell.elf').stat().st_size
            hashes['elf64_loader.text'] = loader_code(text.read_bytes(), shell_size)
            if len(hashes) != 26 or (expected is not None and hashes != expected):
                raise RuntimeError('kernel mechanism or child/probe fixture drift')
            expected = hashes
            rip = exit_address(native)
            for n in range(3):
                for info in (False, True):
                    case = folder/f'{n}-{int(info)}'
                    case.mkdir()
                    serial = capture(native/'reist-x86_64-bootstrap.elf', case, n, info)
                    validate(serial, n, info, max(0, status), rip)
                    summary['cases'].append(dict(children=n, info=info, status=status, passed=True))
            print(f'SHELL_EXIT_CASE_OK status={status} dialogs=6', flush=True)
        summary.update(passed=True, mechanism_sha256=expected)
        print('SHELL_EXIT_RUNTIME_OK dialogs=30 evidence='+str(attempt))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        summary['error'] = str(error)
        print('SHELL_EXIT_RUNTIME_FAIL '+str(error))
        return 1
    finally:
        summary['elapsed_seconds'] = round(time.monotonic()-started, 3)
        (attempt/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
