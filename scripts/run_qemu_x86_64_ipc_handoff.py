"""Bounded real IPC interleavings with read-only GDB state witnesses.

No kernel test flags: only the embedded userspace fixture changes. Three hardware
breakpoints pair production plan entry and caller return without patching code.
Missing/duplicate observations fail; no events are discarded or deduplicated.
"""
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

ROOT = Path(__file__).resolve().parents[1]
PLAN = re.compile(r'IPC_PLAN op=(\d+) bits=(\d+) generation=(\d+)')
REAP = re.compile(r'CHILD_EXIT_REAP_OK status=([0-9A-F]{8}) generation=([0-9A-F]{2}) '
                  r'parent=([0-9A-F]{2}) queued=([0-9A-F]{2}) rip=([0-9A-F]{16})')
MAX_TRACE = 256 * 1024
HH = 0xffffffff80000000
OBSERVATION = re.compile(r'IPC_(ENTER|LEAVE) id=(\d+) op=(\d+) bits=(\d+) '
    r'task=([0-9a-f]+) generation=(\d+) rip=([0-9a-f]+) handle=([0-9a-f]+) '
    r'rsp=([0-9a-f]+) site=([0-9a-f]+) flags=([0-9a-f]+)(?: result=(-?\d+))?')


def expected_plan(op, bits):
    """Independent finite private-plan contract, not a guest implementation."""
    if not 0 <= bits <= 15 or (bits & 8 and bits != 8):
        return -4096
    if bits == 8:
        return 6 if op == 52 else -9
    if (bits & 2 and not bits & 1) or (bits & 4 and bits & 3):
        return -4096
    if op in (50, 53):
        if bits & 4: return 3
        if not bits & 1: return 1
        return 2 if op == 53 and not bits & 2 else -11
    if op in (51, 54):
        if bits & 1: return 4
        return 5 if op == 54 and not bits & 4 else -11
    return {52: 6, 58: 7}.get(op, -38)


def plan_return_site(image, symbols):
    """Validate the actual ELF32 container's AMD64 MOV/CALL/return-site bytes."""
    if not 52 <= len(image) <= 2*1024*1024 or image[:7] != b'\x7fELF\x01\x01\x01':
        raise RuntimeError('invalid bounded bootstrap ELF32 container')
    offset = struct.unpack_from('<I',image,28)[0]
    size, count = struct.unpack_from('<HH',image,42)
    if size != 32 or not 1 <= count <= 16 or offset < 52 or offset+size*count > len(image):
        raise RuntimeError('invalid bootstrap program headers')
    address = symbols['scheduler_ipc_plan64.plan'] - HH
    matches = []
    for index in range(count):
        kind, pos, va, pa, length, memory, flags, align = struct.unpack_from('<8I',image,offset+index*size)
        if kind != 1: continue
        if pos+length > len(image) or length > memory or va+memory > 1<<32:
            raise RuntimeError('invalid bounded bootstrap load segment')
        if va <= address and address+18 <= va+length:
            if not flags & 1:
                raise RuntimeError('IPC call site is not executable')
            matches.append(bytes(image[pos+address-va:pos+address-va+18]))
    if len(matches) != 1:
        raise RuntimeError('missing or ambiguous IPC call site')
    code = matches[0]
    if (code[:3] != b'\x48\x8b\x3d' or code[7] != 0xe8 or
            code[12:] != b'\x48\x3d\x00\xf0\xff\xff' or
            HH+address+7+struct.unpack_from('<i',code,3)[0] != symbols['syscall_rax'] or
            HH+address+12+struct.unpack_from('<i',code,8)[0] != symbols['reist_x64_ipc_plan']):
        raise RuntimeError('unexpected actual IPC plan call encoding or target')
    return HH+address+12


def validate_observations(trace, site):
    if len(trace.encode('utf-8')) > MAX_TRACE:
        raise RuntimeError('IPC observer output exceeds bound')
    pending = receipt = None
    calls = 0
    done = False
    for line in trace.splitlines():
        if not line.startswith('IPC_'): continue
        match = OBSERVATION.fullmatch(line)
        if match:
            if done or receipt is not None:
                raise RuntimeError('IPC observation after completion or before plan receipt')
            phase, *raw = match.groups()
            values = [int(value,16 if index in (3,5,6,7,8,9) else 10)
                      for index,value in enumerate(raw) if value is not None]
            identity, op, bits, task, generation, rip, handle, rsp, actual_site, flags = values[:10]
            if (actual_site != site or flags & 0x200 or not HH <= task < HH+128*1024*1024 or
                    task & 7 or not 0 < generation < 1<<32 or not 0x400000 <= rip < 0x408000 or
                    not HH <= rsp < HH+128*1024*1024 or rsp & 7 or
                    any(value < 0 or value >= 1<<64 for value in values[:10])):
                raise RuntimeError('invalid IPC site, identity, stack or interrupt witness')
            if phase == 'ENTER':
                if pending is not None or identity != calls+1 or identity > 256 or len(values) != 10:
                    raise RuntimeError('duplicate, nested or unbounded IPC entry')
                pending = values
            else:
                if (pending is None or len(values) != 11 or values[:7] != pending[:7] or
                        rsp != pending[7]+8 or values[10] != expected_plan(op,bits)):
                    raise RuntimeError('unmatched IPC return, changed inputs or incorrect result')
                calls += 1
                pending = None
                receipt = (op,bits,generation)
        elif match := PLAN.fullmatch(line):
            if done or receipt is None or tuple(map(int,match.groups())) != receipt:
                raise RuntimeError('IPC plan receipt lacks its exact completed call')
            receipt = None
        elif match := re.fullmatch(r'IPC_OBSERVER_DONE calls=(\d+)',line):
            if done or pending is not None or receipt is not None or not calls or int(match[1]) != calls:
                raise RuntimeError('IPC observer completion does not match calls')
            done = True
        else:
            raise RuntimeError('malformed IPC observation: '+line[:120])
    if not done or pending is not None or receipt is not None:
        raise RuntimeError('IPC observer has incomplete call pairs')
    return calls


def observer_commands(symbols, site):
    # Convenience variables only. Three hardware execution breakpoints, no
    # writes to guest registers/memory, no software breakpoint byte patching.
    fields = ('id=%llu op=%llu bits=%llu task=%llx generation=%llu '
              'rip=%llx handle=%llx rsp=%llx site=%llx flags=%llx')
    values = (f'$ipc_hits, $rdi, $rsi, $r12, *(unsigned long long*)($r12+8), '
              f'*(unsigned long long*){symbols["syscall_rcx"]:#x}, '
              f'*(unsigned long long*){symbols["syscall_rdi"]:#x}, $rsp')
    return ('set confirm off\nset pagination off\nset architecture i386:x86-64\n'
        'target remote 127.0.0.1:12484\nset $ipc_hits = 0\nset $ipc_pending = 0\n'
        f'hbreak *{symbols["reist_x64_ipc_plan"]:#x}\n'
        f'hbreak *{site:#x}\n'
        f'hbreak *{symbols["scheduler_return64"]:#x} if *(unsigned char*){symbols["scheduler_mode"]:#x} == 7\n'
        'set $ipc_done = 0\nwhile $ipc_done == 0\ncontinue\n'
        f'if $pc == {symbols["reist_x64_ipc_plan"]:#x}\n'
        'set $ipc_hits = $ipc_hits + 1\n'
        f'printf "IPC_ENTER {fields}\\n", {values}, *(unsigned long long*)$rsp, $eflags\n'
        'if $ipc_pending != 0 || $ipc_hits > 256\nquit 2\nend\n'
        f'if *(unsigned long long*)$rsp != {site:#x}\nquit 2\nend\n'
        'set $ipc_pending = 1\n'
        # Do not resume on an armed execution breakpoint. Explicitly execute
        # only the checked, nonbranching CMP with this breakpoint disabled.
        # Re-arm immediately: a real second entry still fails the pending pair.
        'if *(unsigned int*)$pc != 0x0ffe8348 || ($eflags & 512) != 0\nquit 2\nend\n'
        'disable 1\nstepi\nenable 1\n'
        f'if $pc != {symbols["reist_x64_ipc_plan"]+4:#x}\nquit 2\nend\n'
        f'else\nif $pc == {site:#x}\n'
        f'printf "IPC_LEAVE {fields} result=%lld\\n", {values}, $pc, $eflags, $rax\n'
        'if $ipc_pending != 1\nquit 2\nend\nset $ipc_pending = 0\n'
        'printf "IPC_PLAN op=%llu bits=%llu generation=%llu\\n", $rdi, $rsi, *(unsigned long long*)($r12+8)\n'
        'if ($eflags & 512) != 0\nquit 2\nend\ndisable 2\nstepi\nenable 2\n'
        f'if $pc != {site+6:#x}\nquit 2\nend\n'
        'else\n'
        f'if $pc != {symbols["scheduler_return64"]:#x} || $ipc_pending != 0\nquit 2\nend\n'
        'set $ipc_done = 1\nend\nend\nend\n'
        'printf "IPC_OBSERVER_DONE calls=%llu\\n", $ipc_hits\ndetach\nquit\n')


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
    if image.stat().st_size > 2*1024*1024:
        raise RuntimeError('IPC image exceeds diagnostic bound')
    site = plan_return_site(image.read_bytes(),symbols)
    commands = observer_commands(symbols,site)
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
    # Drain directly to a file: verbose paired receipts must not block GDB on
    # an undrained Windows stdout pipe. Capacity and the original10s still apply.
    trace_path = folder / 'gdb.log'
    trace_output = trace_path.open('wb')
    try:
        debugger = subprocess.Popen([gdb, '-q', '-nx', '-batch', '-x', str(script)],
            stdout=trace_output, stderr=subprocess.STDOUT)
        while time.monotonic() - started < 10:
            if trace_path.stat().st_size > MAX_TRACE:
                raise RuntimeError('IPC observer output exceeds bound')
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
                debugger.wait(timeout=2)
            except subprocess.TimeoutExpired:
                terminate_bounded(debugger)
                debugger.wait(timeout=2)
        trace_output.close()
        with trace_path.open('rb') as output:
            trace = output.read(MAX_TRACE+1).decode('utf-8',errors='replace')
        (folder / 'guest.log').write_bytes(captured)
    text = captured.decode('ascii', errors='replace')
    if step != 4 or text.count('REIST_X86_64_RING3_SHELL_RUN_OK') != 2 or any(x in text for x in FAILURES):
        raise RuntimeError('guest failure or incomplete IPC dialogue: ' + text[-700:])
    positions = [text.find(x) for x in REQUIRED_MARKERS]
    if min(positions) < 0 or positions != sorted(set(positions)):
        raise RuntimeError('missing/reordered native completion markers')
    if debugger.returncode != 0:
        raise RuntimeError('IPC observer did not detach cleanly: ' + trace[-700:])
    validate_observations(trace,site)
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
