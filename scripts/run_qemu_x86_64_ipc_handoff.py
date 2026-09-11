"""Bounded real IPC interleavings with read-only GDB state witnesses.

No kernel test flags: only the embedded userspace fixture changes. Software
breakpoints observe production planning inputs; they grant no guest authority.
"""
from pathlib import Path
import argparse
import hashlib
import json
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, REQUIRED_MARKERS, FAILURES, SUCCESS

ROOT = Path(__file__).resolve().parents[1]
PLAN = re.compile(r'IPC_PLAN op=(\d+) bits=(\d+) generation=(\d+)')
REAP = re.compile(r'CHILD_EXIT_REAP_OK status=([0-9A-F]{8}) generation=([0-9A-F]{2}) '
                  r'parent=([0-9A-F]{2}) queued=([0-9A-F]{2}) rip=([0-9A-F]{16})')


def validate_trace(serial, trace, case):
    rows = [tuple(map(int, row)) for row in PLAN.findall(trace)]
    receipts = [tuple(int(v, 16) for v in row) for row in REAP.findall(serial)]
    runs = list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK', serial))
    markers = list(REAP.finditer(serial))
    if len(rows) > 256 or len(receipts) != 2 or len(runs) != 2 or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial)) != 2:
        raise RuntimeError('bounded IPC witnesses or two exit receipts missing')
    status = 77 if case == 0 else 90 + case
    for i, (value, generation, parent, queued, rip) in enumerate(receipts):
        if (value, generation) != (status, 41+i) or parent not in (1, 6, 7) or queued or not 0x400000 <= rip < 0x408000:
            raise RuntimeError('wrong IPC exit ownership, queue or status')
        if not (runs[i-1].end() if i else -1) < markers[i].start() < markers[i].end() <= runs[i].start():
            raise RuntimeError('IPC reap must precede its matching RUN')
    # Two different generations must actually visit the intended production
    # branches. Merely finding a fixture opcode cannot satisfy these witnesses.
    expected = ((52, 3, 40),) if case == 0 else \
        tuple((53, 0, g) for g in (41, 42)) if case == 1 else \
        tuple((53, 4, g) for g in (41, 42)) if case == 2 else ((52, 1, 40),)
    for item in expected:
        if rows.count(item) < (2 if item[2] == 40 else 1):
            raise RuntimeError('intended IPC interleaving not demonstrated: ' + str(item))
    if case:
        for item in ((53, 0, 40), (53, 1, 40), (50, 1, 40), (51, 0, 40)):
            if rows.count(item) != 2:
                raise RuntimeError('parent queue/timeout/negative fixture incomplete: ' + str(item))


def traced_boot(image, folder):
    nm, gdb = shutil.which('nm'), shutil.which('gdb')
    if not nm or not gdb:
        raise RuntimeError('bounded IPC witness requires nm and gdb')
    listing = subprocess.check_output([nm, str(image)], timeout=10, text=True)
    if len(listing) > 2 * 1024 * 1024:
        raise RuntimeError('symbol listing exceeds diagnostic bound')
    symbols = {r[2]: int(r[0], 16) + 0xffffffff80000000
               for line in listing.splitlines() if len(r := line.split()) == 3}
    commands = ('set confirm off\nset pagination off\nset architecture i386:x86-64\n'
        'target remote 127.0.0.1:12484\nset $hits = 0\n'
        f'break *{symbols["reist_x64_ipc_plan"]:#x}\ncommands 1\nsilent\n'
        'set $hits = $hits + 1\nif $hits > 256\nquit 2\nend\n'
        'printf "IPC_PLAN op=%llu bits=%llu generation=%llu\\n", $rdi, $rsi, *(unsigned long long*)($r12+8)\n'
        'continue\nend\n'
        f'break *{symbols["scheduler_return64"]:#x} if *(unsigned char*){symbols["scheduler_mode"]:#x} == 7\n'
        'commands 2\nsilent\ndetach\nquit\nend\ncontinue\n')
    script = folder / 'observe.gdb'
    script.write_text(commands, encoding='ascii')
    qemu = subprocess.Popen([str(resolve_qemu(None)), '-machine', 'pc,accel=tcg',
        '-cpu', 'qemu64', '-m', '128M', '-smp', '1', '-display', 'none', '-monitor', 'none',
        '-serial', 'stdio', '-no-reboot', '-no-shutdown', '-kernel', str(image),
        '-S', '-gdb', 'tcp:127.0.0.1:12484'], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    chunks = queue.Queue()
    def read():
        for block in iter(lambda: qemu.stdout.read(256), b''):
            chunks.put(block)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    started = time.monotonic()
    debugger = None
    captured = bytearray()
    step = 0
    trace = ''
    try:
        debugger = subprocess.Popen([gdb, '-q', '-nx', '-batch', '-x', str(script)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while time.monotonic() - started < 10:
            try:
                captured.extend(chunks.get(timeout=0.01))
            except queue.Empty:
                pass
            text = captured.decode('ascii', errors='replace')
            milestones = [('RING3_SHELL_READY', b'INFO\n'), ('RING3_SHELL_INFO_OK', b'RUN\n'),
                          ('RING3_SHELL_RUN_OK', b'RUN\n')]
            if step < 3 and milestones[step][0] in text:
                qemu.stdin.write(milestones[step][1]); qemu.stdin.flush(); step += 1
            if step == 3 and text.count('REIST_X86_64_RING3_SHELL_RUN_OK') == 2:
                qemu.stdin.write(b'EXIT\n'); qemu.stdin.flush(); step += 1
            if SUCCESS in text or any(x in text for x in FAILURES):
                break
            if qemu.poll() is not None:
                break
    finally:
        terminate_bounded(qemu)
        reader.join(timeout=1)
        while not chunks.empty():
            captured.extend(chunks.get_nowait())
        if debugger:
            try:
                trace = debugger.communicate(timeout=2)[0].decode('utf-8', errors='replace')
            except subprocess.TimeoutExpired:
                terminate_bounded(debugger)
                trace = debugger.communicate(timeout=2)[0].decode('utf-8', errors='replace')
        (folder / 'guest.log').write_bytes(captured)
        (folder / 'gdb.log').write_text(trace, encoding='utf-8')
    text = captured.decode('ascii', errors='replace')
    if step != 4 or text.count('REIST_X86_64_RING3_SHELL_RUN_OK') != 2 or any(x in text for x in FAILURES):
        raise RuntimeError('guest failure or incomplete IPC dialogue: ' + text[-700:])
    positions = [text.find(x) for x in REQUIRED_MARKERS]
    if min(positions) < 0 or positions != sorted(set(positions)):
        raise RuntimeError('missing/reordered native completion markers')
    if debugger.returncode != 0:
        raise RuntimeError('IPC observer did not detach cleanly: ' + trace[-700:])
    return text, trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    base = args.evidence.resolve()
    if not base.is_relative_to(ROOT / 'build/codex-agent'):
        parser.error('evidence outside workspace')
    attempt = base / ('attempt-' + uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    started = time.monotonic()
    summary = dict(passed=False, cases=[])
    mechanisms = None
    try:
        for case in range(4):
            folder = attempt / str(case); folder.mkdir()
            with (folder / 'build.log').open('wb') as output:
                build = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                    '-File', 'scripts/build-x86_64-bootstrap.ps1', '-OutputDirectory',
                    folder.relative_to(ROOT).as_posix(), '-IpcCase', str(case)], cwd=ROOT,
                    stdout=output, stderr=subprocess.STDOUT, timeout=90,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if build.returncode:
                raise RuntimeError('build failed: ' + str(folder / 'build.log'))
            names = ('cooperative_scheduler','ipc_admission','timer_interrupt','queue_core',
                'context_core','identity_core','cpu_budget','fp_context','user_fault',
                'terminal_status','physical_memory','user_execution','exceptions')
            # elf64_loader.o embeds the intentionally different userspace ELFs;
            # it is not a byte-identical standalone mechanism object.
            hashes = {name: hashlib.sha256((folder / 'x86_64' / (name+'.o')).read_bytes()).hexdigest()
                      for name in names}
            if mechanisms is not None and hashes != mechanisms:
                raise RuntimeError('kernel mechanism changed with userspace fixture')
            mechanisms = hashes
            serial, trace = traced_boot(folder / 'x86_64/reist-x86_64-bootstrap.elf', folder)
            validate_trace(serial, trace, case)
            summary['cases'].append(dict(case=case, passed=True))
            print(f'X86_64_IPC_HANDOFF_CASE_OK case={case}', flush=True)
        summary.update(passed=True, generations=8, mechanism_sha256=mechanisms)
        print('X86_64_IPC_HANDOFF_RUNTIME_OK evidence=' + str(attempt))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print('X86_64_IPC_HANDOFF_RUNTIME_FAIL ' + str(exc)); return 1
    finally:
        summary['elapsed'] = round(time.monotonic()-started, 3)
        (attempt / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
