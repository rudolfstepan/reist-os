"""Bounded real-user context entry matrix; no synthetic kernel frames."""
from pathlib import Path
import argparse
import json
import re
import struct
import subprocess
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu, run_boot

ROOT = Path(__file__).resolve().parents[1]
RUN = 'REIST_X86_64_RING3_SHELL_RUN_OK'


def code_and_symbols(folder):
    obj = (folder/'user_child.o').read_bytes()
    linked = (folder/'reist-x86_64-user-child.elf').read_bytes()
    def sections(data):
        if not 64 <= len(data) <= 65536 or data[:6] != b'\x7fELF\x02\x01':
            raise RuntimeError('invalid ELF64')
        offset = struct.unpack_from('<Q', data, 40)[0]
        size, count = struct.unpack_from('<HH', data, 58)
        if size != 64 or not 0 < count <= 64 or offset+size*count > len(data):
            raise RuntimeError('invalid section table')
        result = [struct.unpack_from('<IIQQQQIIQQ', data, offset+i*size) for i in range(count)]
        for sec in result:
            if sec[1] != 8 and sec[4]+sec[5] > len(data):
                raise RuntimeError('section outside file')
        return result
    table = sections(obj)
    text = [s for s in table if s[1] == 1 and s[2]&4]
    executable = [s for s in sections(linked) if s[1] == 1 and s[2]&4]
    if len(text) != 1 or len(executable) != 1:
        raise RuntimeError('not one executable section')
    text, executable = text[0], executable[0]
    code = obj[text[4]:text[4]+text[5]]
    linked_code = linked[executable[4]:executable[4]+executable[5]]
    if len(code) != len(linked_code):
        raise RuntimeError('linked code size differs')
    symbols = {}
    for sec in table:
        if sec[1] != 2:
            continue
        if sec[6] >= len(table) or sec[9] != 24 or sec[5]%24:
            raise RuntimeError('invalid symbol table')
        strings = table[sec[6]]
        names = obj[strings[4]:strings[4]+strings[5]]
        for offset in range(sec[4], sec[4]+sec[5], 24):
            name, _, _, index, value, _ = struct.unpack_from('<IBBHQQ', obj, offset)
            if name >= len(names) or b'\0' not in names[name:]:
                raise RuntimeError('invalid symbol name')
            label = names[name:].split(b'\0', 1)[0].decode('ascii')
            if not label.startswith('child_context_'):
                continue
            if label in symbols or index >= len(table) or table[index] != text or value > len(code):
                raise RuntimeError('duplicate or invalid context symbol')
            symbols[label] = value
    return code, linked_code, symbols, executable[3]


def instruction_offsets(code, symbols, case):
    def at(name):
        return symbols['child_context_'+name]
    begin = at('probe')
    prefix = {1: bytes.fromhex('31e4'), 2: bytes.fromhex('48bc0000000000800000'),
              3: bytes.fromhex('48bc0000000000800000'),
              4: bytes.fromhex('9c48810c24000424009d'),
              5: bytes.fromhex('9c48810c24004000009d'),
              6: bytes.fromhex('9c48810c24004000009d'),
              7: bytes.fromhex('9c48810c24000100009d')}[case]
    cursor = begin+len(prefix)
    if code[begin:cursor] != prefix:
        raise RuntimeError('wrong context setup instructions')
    if case in (3, 6):
        if at('spin') != cursor or at('spin_end') != cursor+4 or code[cursor:cursor+4] != bytes.fromhex('f390ebfc'):
            raise RuntimeError('not syscall-free PAUSE/JMP')
        return {cursor, cursor+2}
    if case == 7:
        if at('fault') != cursor or at('resume') != cursor+1 or code[cursor:cursor+3] != b'\x90\x0f\x0b':
            raise RuntimeError('not TF followed by NOP and failure sentinel')
        return {cursor+1}
    if code[cursor:cursor+7] != bytes.fromhex('b8160000000f05') or at('fault') != cursor+5 or at('resume') != cursor+7:
        raise RuntimeError('not denied GETPID with exact return instruction')
    cursor += 7
    if case != 4:
        if code[cursor:cursor+2] != b'\x0f\x0b':
            raise RuntimeError('missing failed-return sentinel')
        return {cursor}
    # Independent exact byte oracle: denied GETPID, successful YIELD, and flags
    # checked after each entry and on every loop iteration/IRQ return.
    def part(data):
        nonlocal cursor
        data = bytes.fromhex(data)
        if code[cursor:cursor+len(data)] != data:
            raise RuntimeError('missing flags/result check')
        cursor += len(data)
    def jne():
        nonlocal cursor
        if code[cursor] != 0x75 or cursor+2+struct.unpack_from('<b', code, cursor+1)[0] != at('fail'):
            raise RuntimeError('missing fail-closed check branch')
        cursor += 2
    part('9c5a4883f8f3'); jne()
    part('81e20004240081fa00042400'); jne()
    part('b82800000031ff31f631d20f054885c0'); jne()
    if at('spin') != cursor:
        raise RuntimeError('unexpected loop entry')
    part('9c5a81e20004240081fa000424007504f390ebec')
    if at('spin_end') != cursor or at('fail') != cursor or code[cursor:cursor+2] != b'\x0f\x0b':
        raise RuntimeError('unexpected loop/sentinel range')
    return {at('spin')+i for i in (0, 1, 2, 8, 14, 16, 18)}


def validate_receipts(text, case, rips):
    kind = 'STACK' if case <= 3 else 'CPU' if case == 4 else 'FAULT' if case == 7 else 'CONTEXT'
    marker = 'REIST_X86_64_CHILD_'+kind+'_REAP_OK'
    prefix = marker+(r' vector=01' if case == 7 else '')+r' generation=([0-9A-F]{2})'
    suffix = r' ticks=20' if case == 4 else ''
    suffix += r' parent=07' if case == 4 else r' parent=01'
    if case == 7:
        suffix += r' queued=00'
    receipts = list(re.finditer(prefix+suffix+r' rip=([0-9A-F]{16})\r?\n', text))
    runs = list(re.finditer(RUN, text))
    if len(re.findall(r'REIST_X86_64_CHILD_[A-Z]+_REAP_OK', text)) != 2 or len(receipts) != 2 or len(runs) != 2:
        raise RuntimeError('expected exactly two complete matching terminal/RUN receipts')
    for index, receipt in enumerate(receipts):
        gen, rip = (int(v, 16) for v in receipt.groups())
        if gen != 41+index or rip not in rips:
            raise RuntimeError('wrong generation or actual instruction address')
        if not (runs[index-1].end() if index else -1) < receipt.start() < receipt.end() <= runs[index].start():
            raise RuntimeError('terminal reap must precede matching RUN')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    base = args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):
        parser.error('evidence outside workspace')
    attempt = base/('attempt-'+uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    summary = dict(passed=False, cases=[])
    started = time.monotonic()
    try:
        for case in range(1, 8):
            folder = attempt/str(case)
            folder.mkdir()
            command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                       'scripts/build-x86_64-bootstrap.ps1', '-OutputDirectory',
                       folder.relative_to(ROOT).as_posix(), '-ContextCase', str(case)]
            with (folder/'build.log').open('wb') as output:
                result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                    timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                raise RuntimeError('build failed: '+str(folder/'build.log'))
            native = folder/'x86_64'
            code, linked_code, symbols, address = code_and_symbols(native)
            offsets = instruction_offsets(code, symbols, case)
            if instruction_offsets(linked_code, symbols, case) != offsets:
                raise RuntimeError('object/linked fixture mismatch')
            rips = {address+i for i in offsets}
            text = run_boot(resolve_qemu(None), native/'reist-x86_64-bootstrap.elf', folder/'guest.log', 10)
            validate_receipts(text, case, rips)
            summary['cases'].append(dict(case=case, passed=True, rips=[hex(i) for i in sorted(rips)]))
            print('X86_64_USER_CONTEXT_CASE_OK case='+str(case), flush=True)
        summary.update(passed=True, generations=14)
        print('X86_64_USER_CONTEXT_RUNTIME_OK cases=7 generations=14 evidence='+str(attempt))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired, struct.error) as exc:
        print('X86_64_USER_CONTEXT_RUNTIME_FAIL '+str(exc))
        return 1
    finally:
        summary['elapsed'] = round(time.monotonic()-started, 3)
        (attempt/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
