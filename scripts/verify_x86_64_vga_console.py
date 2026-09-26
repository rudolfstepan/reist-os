"""Frozen CJ gates. Raw guest replay is independent of the capture predicates."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import tomllib
import zipfile

import verify_x86_64_desktop_cpu as common
import check_x86_64_vga_console_media as media
from verify_x86_64_service_console import disabled

ROOT = media.ROOT
BASE = ROOT / 'build/codex-agent/r83cj-vga'
IDENT = os.environ.get('REIST_VGA_QUALIFICATION', 'qualification01')
media.need(re.fullmatch(r'qualification[0-9]{2}', IDENT), 'qualification identifier')
GATES = BASE / IDENT
CONTRACT = ROOT / 'docs/architecture/NATIVE_VGA_CONSOLE_CONTRACT.md'
CAPTURE = ROOT / 'build/vmware/reist-native64-full-desktop-20260926-input-diagnostic/mouse_stress.py'
CAPTURE_SHA = '8bef880daa1959e0ffbc5fc11ead370ae6201cca31401221c775031c4dc4088f'
VMRUN = Path('C:/Program Files/VMware/VMware Workstation/vmrun.exe')
REFERENCE = BASE / 'reference-898f30d5'
need = media.need
save = common.save
read = common.read
digest = common.digest
git = common.common.git
run = common.run
LIMITS = (180, 300, 600, 2400, 600)
COMMANDS = [['python', 'test/test_x86_64_vga_console.py', '-v']] + [
    ['python', 'scripts/verify_x86_64_vga_console.py', '--' + mode]
    for mode in ('defaults', 'package', 'runtime', 'review')]


def package():
    queue = tomllib.loads((ROOT / 'automation/reist-s03b.toml').read_text())
    active = [p for p in queue['packages'] if p['status'] == 'active']
    need(len(active) == 1 and active[0]['id'] == queue['active_id'] == 'R8.3cj-vga-console', 'one active CJ package')
    need(active[0]['targeted_tests'] + active[0]['package_tests'] + active[0]['runtime_tests'] ==
         [' '.join(c) for c in COMMANDS], 'unchanged five frozen commands')
    return active[0]


def scope():
    need(set(common.common.changed()) <= set(package()['allowed_files']), 'CJ allowed files')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True, capture_output=True, timeout=30)


def freeze():
    scope()
    need(git('rev-parse', '--short=8', 'HEAD') == '01106c77', 'clean contract baseline')
    need(not GATES.exists(), 'fresh qualification; retain every previous failure')
    need(digest(CAPTURE) == CAPTURE_SHA, 'reviewed exact-window capture helper')
    reference = read(REFERENCE/'reference.json')
    need(reference['commit'] == git('rev-parse', '898f30d5') and reference['artifacts'] == common.artifacts(REFERENCE/'source/build/reference'), 'exact committed reference build')
    save(GATES / 'frozen.json', dict(head=git('rev-parse', 'HEAD'), sources=common.sources(),
         tools=common.common.all_tools(), package=package(), contract=digest(CONTRACT),
         capture=CAPTURE_SHA, vmrun=digest(VMRUN), vmware=digest(VMRUN.parent/'vmware.exe'),
         reference=digest(REFERENCE/'reference.json'), commands=COMMANDS, limits=LIMITS))


def binding():
    scope()
    f = read(GATES / 'frozen.json')
    need(f['head'] == git('rev-parse', 'HEAD') and f['sources'] == common.sources() and
         f['tools'] == common.common.all_tools() and f['package'] == package(), 'immutable sources/tools/scope')
    need(f['contract'] == digest(CONTRACT) and f['capture'] == digest(CAPTURE) and
         f['vmrun'] == digest(VMRUN) and f['vmware'] == digest(VMRUN.parent/'vmware.exe'), 'immutable contract/host observer')
    need(f['reference'] == digest(REFERENCE/'reference.json'), 'immutable reference receipt')
    return f


def once(text, before, after=''):
    need(text.count(before) == 1, 'unique complete disabled addition: ' + before[:90])
    return text.replace(before, after)


def source_projection():
    names = ('arch/x86_64/boot/entry.asm', 'arch/x86_64/proc/cooperative_scheduler.asm',
             'arch/x86_64/proc/native_console.inc', 'arch/x86_64/proc/process_run.inc',
             'arch/x86_64/proc/task_family.inc', 'userspace/sdk/lib/x86_64/shell_session.c',
             'userspace/sdk/lib/x86_64/shell_app_files.inc', 'Makefile',
             'scripts/build-x86_64-bootstrap.ps1', 'scripts/build_x86_64_boot_programs.py')
    result = {}
    for name in names:
        old = subprocess.check_output(['git', 'show', '898f30d5:' + name], cwd=ROOT, timeout=30).decode().replace('\r\n', '\n')
        text = (ROOT / name).read_text(encoding='utf-8')
        if name.startswith(('arch/', 'userspace/')):
            text = disabled(text, 'REIST_NATIVE_VGA_CONSOLE', name.startswith('arch/'))
            if name.startswith('userspace/'):
                text = text.replace('#define SESSION_APPLICATION_SLOT 4U\n', '').replace('SESSION_APPLICATION_SLOT', '4')
        elif name == 'Makefile':
            begin = text.index('X86_64_NATIVE_VGA_CONSOLE ?= 0\n')
            end = text.index('ifneq ($(words $(X86_64_NATIVE_INPUT)),1)', begin)
            block = text[begin:end]
            need(block.count('endif\n') == 5 and block.count('$(error ') == 4, 'complete separate VGA selector')
            text = once(text, block)
            text = once(text, 'X86_64_INPUT_FLAGS += $(if $(filter 1,$(X86_64_NATIVE_VGA_CONSOLE)),-DREIST_NATIVE_VGA_CONSOLE=1 -DREIST_NATIVE_INPUT=1,)\n')
            text = once(text, 'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_VGA_CONSOLE)),--vga-console,)\n')
            text = once(text, 'else ifneq ($(filter 1,$(X86_64_NATIVE_INPUT) $(X86_64_NATIVE_VGA_CONSOLE)),)', 'else ifeq ($(X86_64_NATIVE_INPUT),1)')
        elif name.endswith('.ps1'):
            text = once(text, '    [switch]$NativeVgaConsole,\n')
            text = once(text, '        "X86_64_NATIVE_VGA_CONSOLE=$([int]$NativeVgaConsole.IsPresent)" `\n')
            text = once(text, "if ($NativeVgaConsole) {\n    if ($NativeDisplay -or $NativeInput -or $NativeTerminalService -or $NativeGraphicalSession -or $NativeNetworkSession -or $NativeNetworkDMA) {\n        throw 'NativeVgaConsole requires the separate text shell profile.'\n    }\n    $NativeAppFiles = [switch]$true\n}\n")
        else:
            # Remove only explicit vga_console-only AST branches and appended
            # selector plumbing; compare the complete remaining module AST.
            class Off(ast.NodeTransformer):
                def visit_If(self, node):
                    test = ast.unparse(node.test)
                    if test in ('vga_console', 'vga_console and n == 0') or test.startswith('type(vga_console) is not bool or '):
                        need(not node.orelse, 'no hidden default branch')
                        return None
                    return self.generic_visit(node)

                def visit_FunctionDef(self, node):
                    if node.name == 'build':
                        need(node.args.args[-1].arg == 'vga_console' and ast.literal_eval(node.args.defaults[-1]) is False, 'append-only false selector')
                        node.args.args.pop(); node.args.defaults.pop()
                    return self.generic_visit(node)

                def visit_Expr(self, node):
                    if isinstance(node.value, ast.Call) and node.value.args and isinstance(node.value.args[0], ast.Constant) and node.value.args[0].value == '--vga-console':
                        need(ast.unparse(node.value.func) == 'p.add_argument', 'exact VGA CLI declaration')
                        return None
                    return self.generic_visit(node)

                def visit_Call(self, node):
                    if isinstance(node.func, ast.Name) and node.func.id == 'build':
                        need(ast.unparse(node.args[-1]) == 'a.vga_console', 'appended VGA CLI argument')
                        node.args.pop()
                    return self.generic_visit(node)
            projected = Off().visit(ast.parse(text))
            need(ast.dump(projected) == ast.dump(ast.parse(old)), 'complete disabled producer AST')
            result[name] = hashlib.sha256(ast.dump(projected).encode()).hexdigest()
            continue
        need(text == old, 'complete exact disabled source ' + name)
        result[name] = hashlib.sha256(text.encode()).hexdigest()
    return result


def build(label, selected):
    out = GATES / label
    need(not out.exists(), 'fresh build directory')
    run(['powershell.exe', '-NoProfile', '-File', 'scripts/build-x86_64-bootstrap.ps1',
         '-NativeVgaConsole' if selected else '-NativeAppFiles', '-OutputDirectory',
         out.relative_to(ROOT).as_posix()], GATES / (label + '.log'), 300)
    return out / 'x86_64'


def defaults():
    binding()
    projected = source_projection()
    out = build('disabled', False)
    reference = read(REFERENCE/'reference.json')
    need(digest(REFERENCE/'source.zip') == reference['archive'], 'unchanged committed reference archive')
    need(reference['artifacts'] == common.artifacts(REFERENCE/'source/build/reference'), 'immutable reference artifacts')
    comparison = compare_reference(out.parent)
    save(GATES / 'defaults.json', dict(projection=projected,
         artifacts=common.artifacts(out.parent), comparison=comparison, reference=digest(REFERENCE/'reference.json')))


def canonical_object(path, source_root):
    """ELF64 relocatable comparison, resolving only DWARF string relocations.

    LLVM interns compilation-directory strings in path-dependent order.
    Preserve every other section byte and all section/symbol/relocation metadata.
    Delivery ELFs are never normalized.
    """
    raw=path.read_bytes()
    need(raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',raw,16)==(1,62), 'AMD64 relocatable object')
    offset=struct.unpack_from('<Q',raw,40)[0]
    size,count,names=struct.unpack_from('<HHH',raw,58)
    need(size==64 and 1<=count<=256 and names<count and offset+64*count<=len(raw), 'bounded ELF section table')
    headers=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+64*i) for i in range(count)]
    def contents(h):
        if h[1]==8:return b''
        need(h[4]+h[5]<=len(raw),'bounded object section')
        return raw[h[4]:h[4]+h[5]]
    strings=contents(headers[names])
    labels=[strings[h[0]:].split(b'\0')[0].decode('ascii') for h in headers]
    need(len(set(labels))==len(labels),'unique section names')
    def normalize(value):
        return value.replace(source_root.as_posix().encode(),b'<source>').replace(str(source_root).encode(),b'<source>')
    result=[]
    for label,h in zip(labels,headers):
        data=contents(h)
        metadata=list(h);metadata[4]=0  # File offsets vary only with string-table size.
        if label=='.debug_str':
            metadata[5]=0
            value=sorted(normalize(v).hex() for v in data.split(b'\0'))
        elif label=='.rela.debug_info':
            need(h[1]==4 and h[9]==24 and len(data)%24==0,'DWARF RELA shape')
            symbol_header=headers[h[6]];symbols=contents(symbol_header)
            need(symbol_header[1]==2 and symbol_header[9]==24,'DWARF symbol table')
            value=[]
            for pos in range(0,len(data),24):
                at,info,addend=struct.unpack_from('<QQq',data,pos);index=info>>32
                need(index*24+24<=len(symbols),'bounded relocation symbol')
                section=struct.unpack_from('<H',symbols,index*24+6)[0]
                if section<count and labels[section]=='.debug_str':
                    table=contents(headers[section]);need(0<=addend<len(table),'bounded DWARF string reference')
                    value.append((at,info,normalize(table[addend:].split(b'\0')[0]).hex()))
                else:value.append((at,info,addend))
        else:value=hashlib.sha256(data).hexdigest()
        result.append((label,metadata,value))
    header=bytearray(raw[:64]);header[40:48]=bytes(8)
    return hashlib.sha256(json.dumps((header.hex(),result),sort_keys=True).encode()).hexdigest()


def compare_reference(current):
    previous=REFERENCE/'source/build/reference'
    old=common.artifacts(previous);new=common.artifacts(current)
    need(set(old)==set(new),'complete same artifact set')
    def actual(folder,name):
        if '/programs/' in name:
            attempts=list((folder/'x86_64').glob('programs-*'));need(len(attempts)==1,'one artifact producer')
            return attempts[0]/name.split('/programs/',1)[1]
        return folder/name
    changed={}
    for name in old:
        if old[name]==new[name]:continue
        need(name.endswith('.o'),'delivery artifact must remain byte-identical: '+name)
        a=canonical_object(actual(previous,name),REFERENCE/'source')
        b=canonical_object(actual(current,name),ROOT)
        need(a==b,'complete object comparison after DWARF directory normalization: '+name)
        changed[name]=dict(reference=old[name],current=new[name],canonical=a)
    return dict(count=len(old),byte_identical=len(old)-len(changed),dwarf_directory_only=changed)


def reference_build():
    """Unmodified committed source fixture, no Git checkout/worktree or edits."""
    need(not REFERENCE.exists(), 'fresh exact baseline fixture')
    REFERENCE.mkdir()
    archive=REFERENCE/'source.zip'; source=REFERENCE/'source'; source.mkdir()
    subprocess.run(['git','archive','--format=zip','--output='+str(archive),'898f30d5'],cwd=ROOT,check=True,timeout=30)
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            target=(source/item.filename).resolve()
            need(target.is_relative_to(source) and (item.external_attr>>16)&0xf000!=0xa000, 'safe committed reference member')
            zipped.extract(item,source)
    started=time.monotonic()
    command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeAppFiles','-OutputDirectory','build/reference']
    with (REFERENCE/'build.log').open('xb') as log:
        result=subprocess.run(command,cwd=source,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    save(REFERENCE/'build-result.json',dict(command=command,exit=result.returncode,elapsed=time.monotonic()-started))
    need(result.returncode==0,'reference build failed')
    # Confirm the fixture's source bytes are still exactly the Git archive.
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            if not item.is_dir():need((source/item.filename).read_bytes()==zipped.read(item),'unchanged committed reference source')
    save(REFERENCE/'reference.json',dict(commit=git('rev-parse','898f30d5'),archive=digest(archive),
         tools=common.common.all_tools(),artifacts=common.artifacts(source/'build/reference')))


def make_package():
    binding()
    out = build('enabled', True)
    run([sys.executable, 'scripts/build_x86_64_vga_console_media.py', '--input-directory', str(out),
         '--output-directory', str(GATES / 'media')], GATES / 'media.log', 180)
    image = media.verify(GATES / 'media')
    attempts = list(out.glob('programs-*'))
    need(len(attempts) == 1, 'unique producer')
    worker = attempts[0] / 'vga-console.prg'
    media.selected.programs.prepare(worker.read_bytes(), [], True)
    need((attempts[0] / 'root/bin/shell.prg').read_bytes() == (image / 'program0.prg').read_bytes(), 'ordinary /bin/shell.prg image binding')
    # Both frontends use the same builder and install its root/bin/shell.prg;
    # no independent handwritten boot-shell replacement is admitted.
    for name in ('Makefile', 'scripts/build-x86_64-bootstrap.ps1'):
        text = (ROOT / name).read_text()
        need('X86_64_NATIVE_VGA_CONSOLE' in text, 'explicit frontend selector ' + name)
    usage = []
    for path in out.rglob('*.su'):
        for line in path.read_text().splitlines():
            if line.startswith(('userspace/drivers/vga/', 'userspace/drivers/ps2/native_input.c:')):
                location, size, kind = line.split('\t')
                need(kind == 'static' and 0 <= int(size) <= 4096, 'bounded actual service stack frame')
                usage.append((location, int(size)))
    need(usage and sum(size for _, size in usage) <= 16384, 'conservative total service stack frames')
    save(GATES / 'package.json', dict(image=str(image.relative_to(ROOT)),
         artifacts=common.artifacts(GATES / 'enabled'), worker=digest(worker), stack=usage,
         media={p.name: digest(p) for p in image.iterdir() if p.is_file()}))


def image_binding():
    p = read(GATES / 'package.json')
    need(p['artifacts'] == common.artifacts(GATES / 'enabled'), 'immutable selected build')
    image = ROOT / p['image']
    need({f.name: digest(f) for f in image.iterdir() if f.is_file()} == p['media'], 'immutable signed media')
    need(media.verify(GATES / 'media') == image, 'independent media verification')
    return image


def replay(folder, case, image, *, historical_host_fixture=False):
    """Reconstruct cells, owner/profile, mapping, lifecycle and command output."""
    row = read(folder / 'result.json')
    need(row['passed'] and row['stopped'] and row['case'] == case and row['elapsed'] <= 90 and
         row['kernel_sha256'] == digest(image / media.KERNEL) and 'cleanup_error' not in row, 'complete fresh capture')
    raw = (folder / 'serial.log').read_bytes()
    need(len(raw) <= 262144, 'bounded independent serial replay')
    for phase in ('before', 'after'):
        boot = read(folder/'boot-medium'/ (phase+'.json'))
        data = read(folder/('media-'+phase+'.json'))
        for receipt, size in ((boot, 1474560), (data, 1048576)):
            need(receipt['passed'] and receipt['phase'] == phase and receipt['overlay_allocated_data'] == 0,
                 'unchanged media and no guest writes')
            end = 0
            for extent in receipt['extents']:
                need(extent['start'] == end and extent['length'] > 0 and extent['depth'] == 1, 'complete unchanged backing extents')
                end += extent['length']
            need(end == size, 'complete medium extent coverage')
        need(boot['base'] == dict(size=1474560, sha256=digest(image/'reist-x86_64-floppy.img')) and
             data['base_sha256'] == digest(image/'system.ext2'), 'exact signed test-media identity')
    reaps = []
    for match in re.finditer(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})\r\n', raw):
        record = struct.unpack('<4I2Q', bytes.fromhex(match[1].decode()))
        need(record[0] <= 7 and 0 < record[1] < 2**31 and record[3] in (1, 2, 3, 4), 'canonical reap record')
        reaps.append(record)
    user = re.sub(rb'REIST_X86_64_PROCESS_REAP_OK v1=[0-9A-F]{64}\r\n', b'', raw)
    states = {}; screens = {}
    for path in sorted(folder.iterdir()):
        if not path.is_dir() or not (path / 'vga.bin').exists():
            continue
        data = (path / 'vga.bin').read_bytes()
        need(len(data) == 2272, 'complete raw VGA state')
        v = struct.unpack_from('<20Q', data)
        need(all(v[i] ^ v[i+10] == 2**64-1 for i in range(10)), 'all VGA complement seals')
        need(v[3] in (0, 1, 2) and v[6] < 2048 and v[7] <= 2048 and v[8] < 64 and v[9] <= 64, 'bounded transport state')
        cells = (path / 'cells.bin').read_bytes(); bda = (path / 'bios.bin').read_bytes()
        need(len(cells) == 4000 and len(bda) == 256 and bda[0x49] == 3 and
             struct.unpack_from('<H', bda, 0x4a)[0] == 80 and bda[0x84] == 24, 'real mode03 80x25')
        screens[path.name] = '\n'.join(cells[n*160:n*160+160:2].decode('cp437') for n in range(25))
        need(screens[path.name] == (path / 'screen.txt').read_text(encoding='utf-8'), 'raw cell text equality')
        states[path.name] = v[:10]
        if v[3] == 2:
            tasks = (path / 'tasks.bin').read_bytes(); family = (path / 'family.bin').read_bytes(); profiles = (path / 'profiles.bin').read_bytes()
            need((len(tasks), len(family), len(profiles)) == (8192, 512, 256), 'complete authority raw storage')
            owner, parent = v[:2]
            need(owner & 0xffffffff == 4 and struct.unpack_from('<Q', tasks, 4104)[0] == owner >> 32, 'exact console task generation')
            need(struct.unpack_from('<2Q', family, 256) == (owner, parent) and
                 parent == struct.unpack_from('<Q', tasks, 8)[0] << 32, 'exact controlling live parent')
            need(struct.unpack_from('<4Q', profiles, 128) == (owner >> 32, sum(1 << n for n in (9, 22, 41, 42)), 1 << 49, 0), 'attenuated console syscall profile')
            if not historical_host_fixture:
                budgets=(path/'budgets.bin').read_bytes(); windows=(path/'windows.bin').read_bytes()
                need(len(budgets)==len(windows)==256, 'complete CPU resource snapshot')
                cpu=struct.unpack_from('<4Q',budgets,128); window=struct.unpack_from('<4Q',windows,128)
                need(cpu[:2]==(owner>>32,32) and window[0]==100 and window[3]<=32,
                     'same exact-generation32-sample/1000ms console quota')
                need(cpu[2]<=32*(window[2]+1), 'bounded cumulative periodic CPU use')
            for level, shift in enumerate((39, 30, 21, 12)):
                page = (path / ('vga-page-' + str(level) + '.bin')).read_bytes()
                need(len(page) == 4096, 'complete VGA page table')
                entry = struct.unpack_from('<Q', page, ((0xffffffff800b8000 >> shift) & 511)*8)[0]
                need(entry & 1 and not entry & 4, 'no user VGA mapping')
                if level < 3:
                    need(not entry & 128, 'small VGA page')
                else:
                    need(entry & 0x800000000000001b == 0x800000000000001b and entry & 0x000ffffffffff000 == 0xb8000, 'exact VGA physical mapping and NX/cache flags')
        elif v[3] == 1:
            need(not any(data[160:]) and v[6:10] == (0, 0, 0, 0), 'fenced queues scrubbed')
    if case == 'early':
        marker = 'REIST_X86_64_PHYSICAL_MEMORY_ERROR'
        need(marker in screens['startup'] and marker.encode() in raw and b'Type HELP' not in raw, 'early error and serial parity')
        inject = read(folder / 'early-injection.json')
        symbols = media.payload.elf((image / media.KERNEL).read_bytes(), 32)['symbols']
        need(inject['before'] == 0xffffffff80000000 + symbols['x86_64_nx_resume']['value'] and
             inject['after'] == 0xffffffff80000000 + symbols['physical_memory_state_error']['value'], 'exact existing early error-branch injection')
    else:
        need('REIST OS userspace shell' in screens['startup'] and states['startup'][3] == 2, 'ordinary healthy shell')
        console_reaps = [r for r in reaps if r[0] == 4]
        if case in ('crash', 'hang'):
            injected = read(folder / 'fault-injection.json')
            before = struct.unpack('<4Q', bytes.fromhex(injected['before']))
            after = struct.unpack('<4Q', bytes.fromhex(injected['after']))
            need(before == (0x31414756434a5253, 1, 0, 0) and after == (before[0], 1, 1 if case == 'crash' else 2, 0), 'declared supervisor fault selection only')
            need(len(console_reaps) == (1 if case == 'crash' else 3), 'exact bounded console retirement count')
            need(console_reaps[0][1] == states['startup'][0] >> 32, 'old owner actually reaped')
            need(len({r[1] for r in console_reaps}) == len(console_reaps), 'distinct retired generations')
        if case == 'hang':
            need(states['recovery'][3] == 1 and states['recovery'][2] == 3 and
                 'VGA CONSOLE STOPPED' in screens['recovery'] and b'Built-ins:' in user and
                 b'VGA console unavailable: fffffff5' in user, 'exhausted budget visible; ordinary rescue alive')
        else:
            need(not console_reaps if case == 'healthy' else states['recovery'][0] != states['startup'][0] and
                 states['recovery'][2] == states['startup'][2]+1, 'expected healthy/replacement generation')
            for label, token in (('command-cat', 'REIST native application file objects'), ('command-ls', 'data.txt'),
                                 ('commands', 'Bad command or program file.')):
                need(token in screens[label] and token.encode() in user and 'C:\\>' in screens[label], 'actual application output and shell return')
                if not historical_host_fixture:
                    import run_qemu_x86_64_vga_console as observer
                    proof=read(folder/label/'cursor.json')
                    lines=screens[label].splitlines()[:24]
                    cursor_row=max(i for i,line in enumerate(lines) if line.rstrip()=='C:\\>')
                    need(proof['row']==cursor_row and proof['column']==4 and 1<=len(proof['frames'])<=8,
                         'cursor follows latest prompt row')
                    need(proof['frames']==['cursor-'+str(i)+'.ppm' for i in range(len(proof['frames']))],
                         'bounded consecutive cursor frames')
                    need(observer.cursor_pixels(folder/label/proof['frames'][-1],cursor_row,4),
                         'actual hardware cursor pixels at blank prompt cell')
            apps = [r for r in reaps if r[0] == 5]
            need(len(apps) == 2 and all(r[2] == 0 for r in apps) and apps[0][1] != apps[1][1], 'CAT/LS run in slot5 and exit successfully')
            need(states['commands'][3] == 2, 'healthy console after commands')
    return dict(case=case, states=states, reaps=reaps, elapsed=row['elapsed'])


def runtime():
    binding(); image = image_binding(); groups = []; start = time.monotonic()
    import run_qemu_x86_64_vga_console as guest
    for group, cases in (('healthy', ('healthy', 'early')), ('crash', ('crash',)), ('hang', ('hang',))):
        begin = time.monotonic(); captures = []
        for case in cases:
            folder = GATES / ('guest-' + case)
            need(not folder.exists(), 'fresh complete qualification capture')
            proof = guest.diagnostic(GATES / 'media', folder, case)
            need(proof['passed'] and proof['stopped'], 'fresh runtime capture ' + case)
            captures.append(replay(folder, case, image))
            print('CJ_GUEST_OK', case, proof['elapsed'], flush=True)
        elapsed = time.monotonic()-begin
        need(elapsed <= 600 and time.monotonic()-start <= 1800, 'unchanged group/aggregate budget')
        groups.append(dict(group=group, elapsed=elapsed, captures=captures))
    evidence = {p.relative_to(GATES).as_posix(): digest(p) for folder in GATES.glob('guest-*')
                if folder.is_dir() for p in folder.rglob('*') if p.is_file()}
    save(GATES / 'runtime.json', dict(groups=groups, elapsed=time.monotonic()-start, evidence=evidence))


def vmware(image):
    """One owned visual VM; bounded stop with PID/start-time verified fallback."""
    folder = GATES / 'vmware'; folder.mkdir()
    shutil.copyfile(image / 'reist-x86_64-floppy.img', folder / 'boot.img')
    shutil.copyfile(image / 'system.ext2', folder / 'system-flat.vmdk')
    title = 'REIST native64 - CJ ' + IDENT
    vmx = folder / 'reist-native64.vmx'
    settings = {'.encoding':'UTF-8', 'config.version':'8', 'virtualHW.version':'12', 'displayName':title,
                'guestOS':'other-64', 'firmware':'bios', 'bios.bootOrder':'floppy,hdd', 'memsize':'4096', 'numvcpus':'1',
                'uuid.action':'create', 'floppy0.present':'TRUE', 'floppy0.fileType':'file', 'floppy0.fileName':'boot.img',
                'floppy0.startConnected':'TRUE', 'floppy0.clientDevice':'FALSE', 'ide0:0.present':'TRUE',
                'ide0:0.fileName':'system.vmdk', 'ide0:0.deviceType':'disk', 'ide0:0.mode':'independent-nonpersistent',
                'usb.present':'FALSE', 'mouse.vusb.enable':'FALSE', 'ehci.present':'FALSE', 'usb_xhci.present':'FALSE',
                'ethernet0.present':'FALSE', 'sound.present':'FALSE', 'sharedFolder.maxNum':'0',
                'RemoteDisplay.vnc.enabled':'FALSE', 'svga.present':'TRUE', 'mks.enable3d':'FALSE',
                'gui.viewModeAtPowerOn':'windowed', 'gui.fullScreenAtPowerOn':'FALSE', 'serial0.present':'TRUE',
                'serial0.fileType':'file', 'serial0.fileName':'serial.log', 'serial0.startConnected':'TRUE', 'tools.syncTime':'FALSE'}
    vmx.write_text(''.join(f'{k} = "{v}"\n' for k, v in settings.items()), encoding='utf-8')
    (folder / 'system.vmdk').write_text('# Disk DescriptorFile\nversion=1\nencoding="UTF-8"\nCID=26092601\nparentCID=ffffffff\ncreateType="monolithicFlat"\nRW 2048 FLAT "system-flat.vmdk" 0\nddb.adapterType = "ide"\nddb.geometry.cylinders = "3"\nddb.geometry.heads = "16"\nddb.geometry.sectors = "63"\n')
    pinned = {n: digest(folder/n) for n in ('boot.img', 'system-flat.vmdk')}
    start = time.monotonic(); result = dict(passed=False, stopped=False, media=pinned); child = None
    def command(args):
        return subprocess.run([str(VMRUN), '-T', 'ws', *args], capture_output=True, timeout=8,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        listed = command(['list']); need(listed.returncode == 0 and str(vmx).encode() not in listed.stdout, 'owned VM not running')
        child = subprocess.Popen([str(VMRUN.parent/'vmware.exe'), '-x', str(vmx)], cwd=folder,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        ready = None
        for _ in range(1200):
            need(time.monotonic()-start < 130, 'VMware boot deadline')
            serial = folder/'serial.log'
            if serial.exists():
                raw = serial.read_bytes(); need(len(raw) <= 262144 and b'EXCEPTION_FATAL' not in raw, 'VMware bounded healthy serial')
                if b'C:\\>' in raw: ready = time.monotonic(); break
            time.sleep(.1)
        need(ready is not None, 'actual VMware shell ready')
        result['shell_ready_seconds'] = ready-start
        spec = importlib.util.spec_from_file_location('cj_owned_capture', CAPTURE)
        capture = importlib.util.module_from_spec(spec); spec.loader.exec_module(capture)
        time.sleep(2)
        hwnd = capture.u.FindWindowW(None, title+' - VMware Workstation')
        need(hwnd, 'exact owned VMware window')
        capture.u.ShowWindow(hwnd, 3); capture.u.SetForegroundWindow(hwnd); time.sleep(.3)
        need(capture.u.GetForegroundWindow() == hwnd, 'exact foreground window')
        pixels, width, height, _ = capture.capture(hwnd, folder/'screen.png')
        need(len(pixels) == width*height*4, 'complete VMware capture')
        result['capture'] = dict(width=width, height=height, sha256=digest(folder/'screen.png'))
        while time.monotonic() < ready+20:
            raw = (folder/'serial.log').read_bytes()
            need(len(raw) <= 262144 and b'EXCEPTION_FATAL' not in raw and b'VGA console unavailable' not in raw, 'VMware remains healthy')
            time.sleep(.1)
        result['passed'] = True
    except BaseException as error:
        result['error'] = str(error)
    finally:
        try:
            try:
                stop = command(['stop', str(vmx), 'hard']); result['stop_exit'] = stop.returncode
            except subprocess.TimeoutExpired:
                result['stop_timeout'] = True
            listed = command(['list'])
            if listed.returncode == 0 and str(vmx).lower() in listed.stdout.decode(errors='replace').lower():
                line = (folder/'vmware.log').read_text(errors='replace').splitlines()[0]
                match = re.match(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\.\d+Z .*?pid=(\d+)\b', line)
                need(match, 'owned VM PID and creation timestamp')
                stamp, pid = match.groups()
                script = "$p=Get-Process -Id "+pid+" -ErrorAction Stop; if ($p.ProcessName -ne 'vmware-vmx' -or $p.StartTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss') -ne '"+stamp+"') { throw 'VM identity mismatch' }; Stop-Process -InputObject $p -Force -ErrorAction Stop"
                stopped = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script], capture_output=True, timeout=8)
                result['pid_cleanup'] = dict(pid=int(pid), start=stamp, exit=stopped.returncode,
                                             stdout=stopped.stdout.decode(errors='replace'), stderr=stopped.stderr.decode(errors='replace'))
                if stopped.returncode:
                    # The interactive host tool has the process permission that
                    # a nested sandbox shell can lack. Request only this owned
                    # PID/start identity; independently verify absence below.
                    save(folder/'host-cleanup-request.json',dict(pid=int(pid),start=stamp,vmx=str(vmx)))
                    print('CJ_HOST_CLEANUP_REQUIRED',str(folder/'host-cleanup-request.json'),flush=True)
                    cleanup_end=min(start+165,time.monotonic()+35)
                    for _ in range(35):
                        if time.monotonic()>=cleanup_end:break
                        time.sleep(1)
                        listed=command(['list'])
                        if listed.returncode==0 and str(vmx).lower() not in listed.stdout.decode(errors='replace').lower():break
                # A VM may finish stopping between list and Get-Process.
                # Preserve the action result, then independently observe the
                # final state even when the already-absent process yields1.
                listed = command(['list'])
            result['stopped'] = listed.returncode == 0 and str(vmx).lower() not in listed.stdout.decode(errors='replace').lower()
        except BaseException as error:
            result['cleanup_error'] = str(error)
        result['elapsed'] = time.monotonic()-start
        result['media_unchanged'] = all(digest(folder/n) == sha for n, sha in pinned.items())
        result['passed'] = result['passed'] and result['stopped'] and result['media_unchanged'] and result['elapsed'] <= 180
        save(folder/'result.json', result)
    need(result['passed'], 'bounded VMware visual proof: '+str(result))
    return result


def review():
    binding(); image = image_binding()
    for n in range(1, 5):
        need(read(GATES/f'gate-{n:02d}.json')['passed'], 'all prior frozen gates passed')
    rows = [replay(GATES/('guest-'+case), case, image) for case in ('healthy', 'early', 'crash', 'hang')]
    matrix = read(GATES/'runtime.json')
    need(len(matrix['groups']) == 3 and matrix['elapsed'] <= 1800, 'complete runtime matrix')
    for name, sha in matrix['evidence'].items():
        need(digest(GATES/name) == sha, 'unchanged raw runtime evidence')
    visual = vmware(image)
    # Hash every retained raw proof, including command lines, overlays and
    # before/after media receipts. Do not silently accept edited captures.
    evidence = {p.relative_to(GATES).as_posix(): digest(p) for pattern in ('guest-*', 'vmware')
                for folder in GATES.glob(pattern) if folder.is_dir() for p in folder.rglob('*') if p.is_file()}
    save(GATES/'review.json', dict(passed=True, replay=rows, vmware=visual, evidence=evidence))
    binding()


def qualify():
    freeze()
    for n, (command, limit) in enumerate(zip(COMMANDS, LIMITS), 1):
        binding()
        row = run([sys.executable, *command[1:]], GATES/f'gate-{n:02d}.log', limit)
        print('CJ_GATE_OK', n, round(row['elapsed'], 3), flush=True)
    binding()
    save(GATES/'final.json', dict(passed=True, accepted=False, reason='manual final diff and visual review/local commit pending',
         frozen=digest(GATES/'frozen.json'), review=digest(GATES/'review.json'),
         gates=[digest(GATES/f'gate-{n:02d}.json') for n in range(1, 6)]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    for mode in ('qualify', 'defaults', 'package', 'runtime', 'review', 'audit', 'reference'):
        group.add_argument('--'+mode, action='store_true')
    args = parser.parse_args()
    if args.reference:
        reference_build()
    elif args.audit:
        print(json.dumps(source_projection(), sort_keys=True))
    else:
        action = qualify if args.qualify else defaults if args.defaults else make_package if args.package else runtime if args.runtime else review
        action()
