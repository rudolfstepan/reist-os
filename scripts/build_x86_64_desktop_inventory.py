"""Compile the real desktop to an ELF64 porting object, never a boot image."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct('<16sHHIQQQIHHHHHH')
SECTION = struct.Struct('<IIQQQQIIQQ')
SYMBOL = struct.Struct('<IBBHQQ')
RELA = struct.Struct('<QQq')
DEFAULT_DESKTOP_OBJECT = 'fe63724133e5f3022efe450432c6cc2f9ee8b5f09be25ef1d8ef073621ab814f'
DISPLAY_IMPORTS = {
    'x86os_display_activate', 'x86os_display_activate_mode', 'x86os_display_deactivate',
    'x86os_display_info', 'x86os_display_mode_query', 'x86os_display_frame_begin',
    'x86os_display_frame_commit', 'x86os_display_frame_cancel',
    'x86os_display_frame_stage_blit', 'x86os_display_frame_mark_accelerated',
    'x86os_draw_pixels', 'x86os_draw_text_pixels', 'x86os_draw_text_pixels_clipped',
    'x86os_display_surface_buffer_draw', 'x86os_fill_rect', 'x86os_pointer_update',
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_object(data):
    """Follow ELF section relocations from main; retain unresolved imports.

    Section granularity is conservative for merged strings/data. This is not
    a load layout, a runtime quota calculation or proof of API compatibility.
    """
    need(64 <= len(data) <= 32 * 1024 * 1024, 'ELF input capacity')
    h = HEADER.unpack_from(data)
    need(h[0][:7] == b'\x7fELF\x02\x01\x01', 'ELF64 little endian required')
    need((h[1], h[2], h[3], h[8], h[9], h[10], h[11]) ==
         (1, 62, 1, 64, 0, 0, 64), 'relocatable x86-64 required')
    need(h[4] == h[5] == h[7] == 0, 'relocatable header')
    count, offset = h[12], h[6]
    need(1 < count <= 16384 and 64 <= offset <= len(data) - count * 64,
         'section table bounds')
    sections = [SECTION.unpack_from(data, offset + i * 64) for i in range(count)]
    need(0 < h[13] < count and sections[h[13]][1] == 3, 'section names')
    for s in sections:
        need(s[8] == 0 or s[8] & (s[8] - 1) == 0, 'section alignment')
        need(s[5] <= 64 * 1024 * 1024, 'section size bound')
        if s[1] != 8:
            need(s[4] <= len(data) and s[5] <= len(data) - s[4], 'section bounds')

    def content(s):
        return data[s[4]:s[4] + s[5]]

    def string(table, n):
        need(0 <= n < len(table), 'string offset')
        end = table.find(b'\0', n)
        need(n <= end <= n + 4096, 'terminated bounded ELF string')
        return table[n:end].decode('ascii')

    tables = [i for i, s in enumerate(sections) if s[1] == 2]
    need(len(tables) == 1, 'one symbol table')
    ti = tables[0]
    s = sections[ti]
    need(s[9] == 24 and s[5] % 24 == 0 and s[5] // 24 <= 65536,
         'symbol table capacity')
    need(0 < s[6] < count and sections[s[6]][1] == 3, 'symbol string table')
    strings = content(sections[s[6]])
    symbols = [SYMBOL.unpack_from(data, s[4] + i) for i in range(0, s[5], 24)]
    need(symbols and symbols[0] == (0, 0, 0, 0, 0, 0), 'null symbol')
    names = [string(strings, sym[0]) for sym in symbols]
    for sym in symbols:
        need(sym[3] < count or sym[3] == 0xfff1, 'symbol section index')
    roots = [sym[3] for name, sym in zip(names, symbols) if name == 'main' and sym[3]]
    need(len(roots) == 1 and roots[0] < count, 'one defined main')
    edges = {}
    for s in sections:
        need(s[1] != 9, 'x86-64 RELA required')
        if s[1] != 4:
            continue
        need(s[6] == ti and 0 < s[7] < count and s[9] == 24 and s[5] % 24 == 0,
             'relocation section')
        target = sections[s[7]]
        refs = edges.setdefault(s[7], set())
        for at in range(s[4], s[4] + s[5], 24):
            address, info, _ = RELA.unpack_from(data, at)
            need(address < target[5] and info >> 32 < len(symbols), 'relocation bounds')
            if info & 0xffffffff:
                refs.add(info >> 32)
    pending, reached, imports = roots[:], set(), set()
    while pending:
        index = pending.pop()
        if index in reached:
            continue
        reached.add(index)
        for si in edges.get(index, ()):
            sym = symbols[si]
            if not sym[3]:
                need(names[si], 'named unresolved reference')
                imports.add(names[si])
            elif sym[3] < count and sym[3] not in reached:
                pending.append(sym[3])
    section_names = content(sections[h[13]])
    rows = [{'name': string(section_names, s[0]), 'bytes': s[5],
             'alignment': s[8], 'writable': bool(s[2] & 1),
             'executable': bool(s[2] & 4), 'zero_fill': s[1] == 8}
            for i, s in enumerate(sections) if i in reached and s[2] & 2]
    workspace_sizes = []
    for name, sym in zip(names, symbols):
        if name != 'main.native_workspace_sizes':
            continue
        need(not workspace_sizes and 0 < sym[3] < count and sym[5] == 16 * 8,
             'one fixed native workspace size table')
        table = sections[sym[3]]
        need(table[1] == 1 and sym[4] <= table[5] - sym[5], 'workspace size table bounds')
        workspace_sizes = list(struct.unpack_from('<16Q', data, table[4] + sym[4]))
        need(all(workspace_sizes) and sum(workspace_sizes) <= 8 * 1024 * 1024,
             'compiled native startup workspace budget')
    return {'format': 'ELF64 x86-64 ET_REL', 'entry_root': 'main',
            'bootable': False, 'runtime_accepted': False,
            'reachable_imports': sorted(imports), 'reachable_sections': rows,
            'allocated_section_bytes': sum(r['bytes'] for r in rows),
            'zero_fill_bytes': sum(r['bytes'] for r in rows if r['zero_fill']),
            'native_workspace_sizes': workspace_sizes,
            'size_note': 'Conservative reachable section sum; not a linked PT_LOAD span.'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_paths(text):
    need(len(text) <= 1024 * 1024, 'dependency capacity')
    text = text.replace('\\\n', '')
    _, separator, dependencies = text.partition(': ')
    need(separator and '\n' not in dependencies.strip(), 'one dependency rule')
    tokens = re.findall(r'(?:\\.|[^\s])+', dependencies)
    need(0 < len(tokens) <= 4096, 'dependency count')
    return [Path(re.sub(r'\\([ #\\])', r'\1', token).replace('$$', '$'))
            for token in tokens]


def compile_batches(commands, execute, jobs=4):
    """Join every bounded batch, including failures, before starting more work."""
    need(type(jobs) is int and 1 <= jobs <= 4, 'compiler worker capacity')
    need(1 <= len(commands) <= 64, 'compile command capacity')
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for at in range(0, len(commands), jobs):
            pending = [pool.submit(execute, command)
                       for command in commands[at:at + jobs]]
            # Stable error selection; the executor joins the rest on failure.
            for future in pending:
                future.result()


def build(output, native_workspace=False, jobs=4, native_display=False):
    from build_user_program import find_zig
    from build_system_programs import PROGRAMS
    from build_user_sdk import (PUBLIC_INCLUDE_ROOTS, CORE_LIBRARY_SOURCES,
                                GUI_LIBRARY_SOURCES, IMAGE_LIBRARY_SOURCES)
    sources = list(dict.fromkeys([*PROGRAMS['DESKTOP.PRG'],
        *[p for p in CORE_LIBRARY_SOURCES if p.name not in
          ('x86os.c', 'reist_dns.c', 'reist_dhcp_state.c')],
        *GUI_LIBRARY_SOURCES, *IMAGE_LIBRARY_SOURCES]))
    need(type(native_workspace) is bool, 'explicit native workspace selector')
    need(type(native_display) is bool and (not native_display or native_workspace),
         'native display requires native workspace')
    need(type(jobs) is int and 1 <= jobs <= 4, 'compiler worker capacity')
    if native_workspace:
        sources.append(ROOT / 'userspace/gui/compositor/desktop_native_workspace.c')
    if native_display:
        sources.append(ROOT / 'userspace/sdk/lib/x86_64/desktop_display.c')
    need(1 <= len(sources) <= 64, 'source capacity')
    need(ROOT / 'userspace/gui/compositor/desktop.c' in sources, 'real desktop')
    includes = [*PUBLIC_INCLUDE_ROOTS, ROOT / 'include']
    output = output.resolve()
    need(output.is_relative_to(ROOT / 'build'), 'build output must stay in workspace build')
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    zig = find_zig()
    env = os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR'] = str(output / 'zig-cache')
    commands = []

    def run(index):
        remaining = 180 - (time.monotonic() - started)
        need(remaining > 0, 'whole build deadline')
        with (output / f'command-{index + 1:02}.log').open('xb') as log:
            r = subprocess.run(commands[index], cwd=ROOT, env=env, stdout=log,
                               stderr=subprocess.STDOUT, timeout=min(30, remaining),
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        need((output / f'command-{index + 1:02}.log').stat().st_size <= 1024 * 1024,
             'compiler log capacity')
        need(r.returncode == 0, f'command {index + 1} failed; inspect its log')

    common = [zig, 'cc', '-target', 'x86_64-freestanding-none', '-Oz',
              '-ffreestanding', '-nostdlib', '-fno-builtin', '-fno-stack-protector',
              '-mno-red-zone', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
              '-fno-pic', '-fno-pie', '-mno-mmx', '-mno-sse', '-mno-sse2',
              '-ffunction-sections', '-fdata-sections',
              *['-I' + str(p) for p in includes]]
    if native_workspace:
        common.append('-DREIST_NATIVE_DESKTOP_WORKSPACE=1')
    objects = []
    for index, source in enumerate(sources):
        obj = output / f'{index:02}-{source.stem}.o'
        if source.suffix == '.c':
            args = [*common, '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-MD', '-MF', output / f'{index:02}.d']
        else:
            need(source.suffix == '.s', 'known assembly input')
            args = [zig, 'cc', '-target', 'x86_64-freestanding-none']
        commands.append(list(map(str, [*args, '-c', source, '-o', obj])))
        objects.append(obj)
    # Only the coordinator writes manifests; workers own disjoint numbered logs.
    (output / 'commands.json').write_text(json.dumps(commands, indent=2))
    compile_batches(list(range(len(commands))), run, jobs)
    linked = output / 'desktop-port.o'
    commands.append(list(map(str,
        [zig, 'ld.lld', '-m', 'elf_x86_64', '-r', '-o', linked, *objects])))
    (output / 'commands.json').write_text(json.dumps(commands, indent=2))
    run(len(commands) - 1)
    report = inspect_object(linked.read_bytes())
    baseline_object = ROOT / 'build/codex-agent/native-vmware-desktop/qualification01/desktop-port.o'
    need(digest(baseline_object) == DEFAULT_DESKTOP_OBJECT,
         'accepted desktop inventory baseline')
    baseline = inspect_object(baseline_object.read_bytes())
    if native_workspace:
        need(report['allocated_section_bytes'] < 960 * 1024 and
             len(report['native_workspace_sizes']) == 16, 'native static/workspace capacity')
        expected_imports = set(baseline['reachable_imports']) | {'x86os_malloc', 'x86os_free'}
        if native_display:
            need(DISPLAY_IMPORTS <= expected_imports, 'actual desktop display imports')
            expected_imports -= DISPLAY_IMPORTS
        need(set(report['reachable_imports']) == expected_imports,
             'exact remaining desktop services')
    else:
        need(digest(linked) == DEFAULT_DESKTOP_OBJECT, 'exact original desktop object')
    inputs = set(sources) | {Path(__file__).resolve(),
        ROOT / 'scripts/build_system_programs.py', ROOT / 'scripts/build_user_sdk.py',
        ROOT / 'scripts/build_user_program.py', ROOT / 'assets/images/reist-splash.bmp'}
    for folder in includes:
        inputs.update(folder.rglob('*.h'))
    dependencies = set()
    for depfile in output.glob('*.d'):
        for p in dependency_paths(depfile.read_text(encoding='utf-8')):
            p = p.resolve()
            need(p.is_relative_to(ROOT) or p.is_relative_to(zig.parent),
                 'dependency outside workspace or compiler installation')
            dependencies.add(p)
    need(len(dependencies) <= 4096, 'aggregate dependency capacity')
    report.update({'source_count': len(sources), 'tool_sha256': digest(zig),
                   'compiler_jobs': jobs,
                   'native_display_adapter': native_display,
                   'inputs': {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(inputs)},
                   'objects': {p.name: digest(p) for p in [*objects, linked]},
                   'dependencies': {p.name: digest(p) for p in sorted(output.glob('*.d'))},
                   'dependency_contents': {str(p): digest(p) for p in sorted(dependencies)},
                   'elapsed_seconds': time.monotonic() - started})
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('source_count', 'allocated_section_bytes',
          'zero_fill_bytes', 'reachable_imports', 'elapsed_seconds')}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-workspace', action='store_true')
    parser.add_argument('--native-display', action='store_true')
    parser.add_argument('--jobs', type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    build(args.output, args.native_workspace, args.jobs, args.native_display)
