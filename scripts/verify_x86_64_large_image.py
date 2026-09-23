"""Frozen native large image build and complete guest qualification."""
from pathlib import Path
import argparse,ast,hashlib,inspect,json,re,shlex,subprocess,sys,time
import verify_x86_64_network_dma as previous
from check_x86_64_wide_shell_media import clone
import run_qemu_x86_64_large_image as guest
import build_x86_64_c_payload as payload
v=clone(previous,[("EVIDENCE=ROOT/'build/codex-agent/r83bj-network-dma'","EVIDENCE=ROOT/'build/codex-agent/r83bu-large-image'"),
    ("BASE=EVIDENCE/'candidate02'","BASE=EVIDENCE/'candidate01'"),("HEAD='c6533954'","HEAD='3a835501'"),
    ("PACKAGE='R8.3bj-network-dma'","PACKAGE='R8.3bu-large-image'")],'large_image_evidence')
ROOT=v.ROOT

def freeze():
    v.need(not v.BASE.exists() and v.git('rev-parse','--short=8','HEAD')==v.HEAD,'fresh BU candidate')
    p=v.package_row();paths=v.changed();v.need(set(paths)<=set(p['allowed_files']) and not v.git('diff','--cached','--name-only'),'BU candidate scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];v.need(len(commands)==5,'five gates')
    retained={n:v.link(v.EVIDENCE/n) for n in ('baseline01.json','build06.json','diagnostic06/result.json','host11.json')}
    history={p.relative_to(ROOT).as_posix():v.digest(p) for p in v.EVIDENCE.rglob('*') if p.is_file() and 'cache' not in str(p)}
    v.save(v.BASE/'frozen.json',dict(head=v.git('rev-parse','HEAD'),package=p,changed=paths,sources=v.sources(),tools=v.tools(),commands=commands,limits=[900,900,600,2200,900],retained=retained,history=history))

def binding():return v.binding()

def run(name,command,limit):
    binding();v.save(v.BASE/(name+'-started.json'),dict(command=command,limit=limit))
    log=v.BASE/(name+'.log');start=time.monotonic()
    with log.open('xb') as out:r=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
    row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,passed=r.returncode==0,log=v.link(log))
    v.save(v.BASE/(name+'.json'),row);v.need(row['passed'],name+': '+log.read_text(errors='replace')[-1800:]);binding()

def image():return v.BASE/'build/x86_64/reist-x86_64-bootstrap.elf'

def package():
    f=binding();folder=v.BASE/'build'
    run('reference-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeLargeImage','-OutputDirectory',folder.relative_to(ROOT).as_posix()],300)
    inner=(image().parent/'reist-x86_64-c-core.elf').read_bytes();payload.verify_outer(inner,image().read_bytes(),large_image=True)
    fixture=next(image().parent.glob('programs-*'));child=(fixture/'program2.prg').read_bytes()
    from build_x86_64_large_image import prepare
    record=prepare(child,[]);count=guest.allocations(record)
    maps=(fixture/'program0.map').read_text(encoding='utf-8');hits=[line.split()[0] for line in maps.splitlines() if line.split() and line.split()[-1]=='reist_large_image_selection']
    v.need(len(hits)==1,'exact root selector symbol');selection=int(hits[0],16)
    v.need(record[24+128]==6 and record[24+254]==6 and record[24+255]==5,'middle/final RW and final RX fixture')
    artifacts={p.relative_to(ROOT).as_posix():v.digest(p) for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p) and p.suffix in ('.elf','.prg','.bin','.map','.o','.inc')}
    v.save(v.BASE/'package.json',dict(passed=True,image=v.link(image()),count=count,selection=selection,artifacts=artifacts))

def runtime():
    binding();package=v.read(v.BASE/'package.json');count=package['count'];img=image()
    points=[0,1,2,count//4,count//2,count-1];v.need(len(set(points))==6,'six distinct OOM points')
    specs=[(0,4096,None),(0,8192,None)]+[(case,4096,None) for case in range(1,6)]+[(6,4096,n) for n in points]
    rows=[];c=payload.validate((img.parent/'reist-x86_64-c-core.elf').read_bytes());symbols=guest.transport.symbols(img)
    for case,ram,oom in specs:
        binding();folder=v.BASE/'guests'/f'large-{case}-{ram}-{oom}';folder.mkdir(parents=True)
        start=time.monotonic();v.save(folder/'started.json',dict(case=case,ram=ram,oom=oom,limit=120,image=v.link(img)))
        serial,trace=guest.transport.capture(img,folder,guest.observer(symbols,c,folder,case,oom,package['selection']),ram)
        (folder/'serial.txt').write_text(serial);(folder/'trace.txt').write_text(trace)
        proof=guest.replay(folder,serial,trace,count);elapsed=time.monotonic()-start
        v.need(elapsed<=120,'large guest deadline');row=dict(folder=folder.relative_to(ROOT).as_posix(),case=case,ram=ram,oom=oom,elapsed=elapsed,proof=proof)
        v.save(folder/'passed.json',row);rows.append(row);print('LARGE_GUEST_OK',case,ram,oom,flush=True)
    v.need(sum(r['elapsed'] for r in rows)<=1560,'large matrix deadline')
    # Legacy execution and replay are supplied by the same bounded raw adapter.
    legacy_rows=legacy_runtime()
    v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows,legacy=legacy_rows))

def review():
    f=binding();package=v.read(v.BASE/'package.json');matrix=v.read(v.BASE/'matrix.json')
    v.need(matrix['passed'] and len(matrix['cases'])==13 and len(matrix['legacy'])==2,'fifteen fresh guests')
    for row in matrix['cases']:
        folder=ROOT/row['folder'];proof=guest.replay(folder,(folder/'serial.txt').read_text(encoding='utf-8'),(folder/'trace.txt').read_text(encoding='utf-8'),package['count'])
        v.need([list(x) for x in proof]==row['proof'],'independent large replay')
    review_legacy(matrix['legacy'])
    for name,sha in package['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'immutable package artifact '+name)
    for name,sha in f['history'].items():v.need(v.digest(ROOT/name)==sha,'retained development evidence '+name)
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    raw={p.relative_to(ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}
    v.save(v.BASE/'acceptance-seal.json',dict(passed=True,frozen=f,package=package,matrix=matrix,raw=raw,gates=[v.read(v.BASE/f'gate-{n:02d}.json') for n in range(1,5)]))

def gates():v.binding=binding_gate;v.gates()
# Avoid recursion when v.gates resolves the locally overridden binding.
binding_gate=v.binding

def legacy_namespace():
    """Project only physical layout constants; preserve all applicable raw checks."""
    import types
    source=inspect.getsource(guest)
    changes=[('SIZE=1052960','SIZE=266336'),("b'RNPGv3\\0\\0'+struct.pack('<II',3,SIZE)","b'RNPGv2\\0\\0'+struct.pack('<II',2,SIZE)"),
        ("b'RNPGv3\\0\\0'+struct.pack('<II',3,1052960)","b'RNPGv2\\0\\0'+struct.pack('<II',2,266336)"),
        ('flags=record[24:280]','flags=record[24:88]'),("'<512Q'","'<128Q'"),
        ("+slot*4096,4096","+slot*1024,1024"),("mem(reg('r12'),4096)","mem(reg('r12'),1024)"),
        ("memory(registers['r12'],4096)","memory(registers['r12'],1024)"),
        ('t[260]','t[68]'),('t[261]','t[69]'),('t[4:260]','t[4:68]'),('t[2:260]','t[2:68]'),('task(slot)[2:260]','task(slot)[2:68]'),
        ('0x500000','0x440000'),('1056768','270336'),('0xc07000','0xb47000'),('scratch=258,reserved=3079','scratch=66,reserved=2887'),
        ('else (256,288)','else (64,96)'),('for page in range(256):','for page in range(64):'),('for p in range(256):','for p in range(64):'),
        ("mem(S['elf_import_record'],1052960)","mem(S['elf_import_record'],266336)"),('288+p*4096','96+p*4096'),('296+p*4096','104+p*4096'),
        ('range(16,256)','range(16,64)'),('0x31474d494752414c','0x594d454d45444957'),('hits[0]-288','hits[0]-96'),
        ('user(parent,ptr,1052960)==bytes([0x5a])*1052960','user(parent,ptr,266336)==bytes([0x5a])*266336'),
        ('288+(p+1)*4096','96+(p+1)*4096'),('288+page*4096','96+page*4096'),('288+(page+1)*4096','96+(page+1)*4096'),
        ("len(release['freed'])<=261","len(release['freed'])<=69"),("e['frames']<=261","e['frames']<=69"),
        ("('scheduler_tasks',16384)","('scheduler_tasks',4096)"),("('elf_import_record',1052960)","('elf_import_record',266336)"),
        ('i*2320','i*592'),('mem(a,2320)','mem(a,592)'),('r[:2304]','r[:576]'),('r[2308:]','r[580:]'),
        ("memory(s['usable_bitmap'],385)","memory(s['usable_bitmap'],361)"),('1<<3079','1<<2887'),
        ('+9*2320','+9*592'),('len(data)==2320','len(data)==592'),('data[:2304]','data[:576]'),('data[2308:]','data[580:]'),
        ("    if slot==0:\n        magic=", "    if slot==0 and CONFIG['selection'] is not None:\n        magic=")]
    for before,after in changes:
        v.need(before in source,'legacy layout projection '+before);source=source.replace(before,after)
    for line in source.splitlines(keepends=True):
        if ('assert user(t,0x480000' in line or 'assert user(t,0x4fe000' in line or
            "need(user(t,0x480000" in line or "need(user(t,0x4fe000" in line):source=source.replace(line,'')
    module=types.ModuleType('large_legacy_raw');module.__file__=guest.__file__
    exec(compile(source,guest.__file__,'exec'),module.__dict__);return module

def legacy_runtime():
    module=legacy_namespace();img=v.EVIDENCE/'baseline01/x86_64/reist-x86_64-bootstrap.elf'
    old=v.read(v.EVIDENCE/'baseline01.json')
    for name,sha in old['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'unchanged clean legacy artifact')
    inner=(img.parent/'reist-x86_64-c-core.elf').read_bytes();payload.verify_outer(inner,img.read_bytes())
    c=payload.validate(inner);s=module.transport.symbols(img);catalog=(img.parent/'boot-programs.bin').read_bytes()
    count=module.allocations(catalog[2*266336:3*266336]);rows=[]
    for ram in (4096,8192):
        binding();folder=v.BASE/'guests'/f'legacy-{ram}';folder.mkdir(parents=True);start=time.monotonic()
        v.save(folder/'started.json',dict(ram=ram,limit=90,image=v.link(img)))
        serial,trace=module.transport.capture(img,folder,module.observer(s,c,folder,0,None,None),ram)
        (folder/'serial.txt').write_text(serial);(folder/'trace.txt').write_text(trace)
        proof=module.replay(folder,serial,trace,count);elapsed=time.monotonic()-start;v.need(elapsed<=90,'legacy deadline')
        row=dict(folder=folder.relative_to(ROOT).as_posix(),ram=ram,count=count,elapsed=elapsed,proof=proof)
        v.save(folder/'passed.json',row);rows.append(row);print('LEGACY_GUEST_OK',ram,flush=True)
    return rows

def review_legacy(rows):
    module=legacy_namespace();v.need([r['ram'] for r in rows]==[4096,8192],'ordered legacy guests')
    for row in rows:
        folder=ROOT/row['folder'];proof=module.replay(folder,(folder/'serial.txt').read_text(encoding='utf-8'),(folder/'trace.txt').read_text(encoding='utf-8'),row['count'])
        v.need([list(x) for x in proof]==row['proof'],'independent legacy raw replay')

def projection():
    from verify_x86_64_service_console import disabled
    macro='REIST_NATIVE_LARGE_IMAGE'
    files=('arch/x86_64/boot/entry.asm','arch/x86_64/exec/elf64_loader.asm','arch/x86_64/proc/task_family.inc',
        'userspace/sdk/include/reist/x86_64/image.h','userspace/sdk/include/reist/x86_64/task.h',
        'userspace/sdk/lib/x86_64/image.c','arch/x86_64/mm/native_layout.inc','arch/x86_64/mm/native_layout.h',
        'arch/x86_64/mm/user_access.asm','arch/x86_64/exec/boot_programs.inc')
    compact=lambda text:re.sub(r'\s+','',text)
    for path in files:
        source=(ROOT/path).read_text(encoding='utf-8');asm=path.endswith(('.asm','.inc'))
        if path.endswith('native_layout.inc'):
            source=re.sub(r'%ifdef REIST_NATIVE_LARGE_IMAGE\n%ifndef REIST_NATIVE_WIDE\n.*?%elifdef REIST_NATIVE_WIDE\n','%ifdef REIST_NATIVE_WIDE\n',source,flags=re.S)
            source=source.replace('%define NATIVE_PREPARED_V3_BYTES 1052960\n','')
        elif path.endswith('native_layout.h'):
            source=re.sub(r'#ifdef REIST_NATIVE_LARGE_IMAGE\n#ifndef REIST_NATIVE_WIDE\n.*?#elif defined\(REIST_NATIVE_WIDE\)\n','#ifdef REIST_NATIVE_WIDE\n',source,flags=re.S)
        if path.endswith('task_family.inc'):
            source=re.sub(r'%elifdef REIST_NATIVE_LARGE_IMAGE\n    jb \.[a-z0-9_]+\n','',source)
        source=disabled(source,macro,asm)
        if path.endswith('image.c'):
            source=source.replace('    const size_t input_limit=wide?524288U:65536U;\n','').replace('length>input_limit','length>(wide?524288U:65536U)')
            source=source.replace('{put(r,wide?', 'put(r,wide?').replace('put(r+8,wide?2:1,4);}','put(r+8,wide?2:1,4);')
        if path.endswith('user_access.asm'):
            source=source.replace('%include "arch/x86_64/mm/native_layout.inc"\n','').replace('0x400000+NATIVE_IMAGE_PAGES*4096','0x440000')
        if path.endswith('boot_programs.inc'):
            a=source.index('%macro NATIVE_RECORD_ADMISSION 6\n');b=source.index('%endmacro\n',a)
            body=source[a+len('%macro NATIVE_RECORD_ADMISSION 6\n'):b]
            values=['boot_program_admit_v2_64','NATIVE_PREPARED_V2_BYTES','0x0000327647504e52','2','64','96']
            for n,value in enumerate(values,1):body=body.replace('%'+str(n),value)
            body=body.replace('96-8','88').replace('96+64*4096','262240').replace('64*4096','262144')
            end=b+len('%endmacro\n');call='NATIVE_RECORD_ADMISSION '+','.join(values)+'\n'
            v.need(source[end:].startswith(call),'exact v2 shared admission invocation')
            source=source[:a]+body+source[end+len(call):]
        v.need(compact(source)==compact(v.original(path)),'entire disabled source '+path)
    path='scripts/build-x86_64-bootstrap.ps1';source=(ROOT/path).read_text(encoding='utf-8')
    for addition in ('    [switch]$NativeLargeImage,\n','if ($NativeLargeImage) { $NativeWide = [switch]$true }\n','        "X86_64_NATIVE_LARGE_IMAGE=$([int]$NativeLargeImage.IsPresent)" `\n'):
        v.need(source.count(addition)==1,'Windows selector projection');source=source.replace(addition,'')
    v.need(source==v.original(path),'complete Windows default build')
    path='Makefile';source=(ROOT/path).read_text(encoding='utf-8')
    a=source.index('# Explicit larger prepared imports;');b=source.index('X86_64_NATIVE_WIDE ?= 0',a);source=source[:a]+source[b:]
    source=source.replace('X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_LARGE_IMAGE)),--large-image,)\n','')
    source=source.replace('X86_64_WIDE_ASM += $(if $(filter 1,$(X86_64_NATIVE_LARGE_IMAGE)),-DREIST_NATIVE_LARGE_IMAGE=1,)\n','')
    source=source.replace(' $(if $(filter 1,$(X86_64_NATIVE_LARGE_IMAGE)),--large-image,)','')
    v.need(source==v.original(path),'complete Make default build')
    class Off(ast.NodeTransformer):
        def has(self,node):return any(isinstance(x,ast.Name) and x.id=='large_image' or isinstance(x,ast.Attribute) and x.attr=='large_image' for x in ast.walk(node))
        def visit_If(self,node):
            if self.has(node.test):return [self.visit(n) for n in node.orelse]
            return self.generic_visit(node)
        def visit_IfExp(self,node):
            if self.has(node.test):return self.visit(node.orelse)
            return self.generic_visit(node)
        def visit_FunctionDef(self,node):
            if node.args.args and node.args.args[-1].arg=='large_image':node.args.args.pop();node.args.defaults.pop()
            if node.args.kwonlyargs and node.args.kwonlyargs[-1].arg=='large_image':node.args.kwonlyargs.pop();node.args.kw_defaults.pop()
            return self.generic_visit(node)
        def visit_Expr(self,node):
            if isinstance(node.value,ast.Call):
                call=node.value
                if any(isinstance(a,ast.Constant) and a.value=='--large-image' for a in call.args):return None
                if isinstance(call.func,ast.Name) and call.func.id=='require' and self.has(call.args[0]):return None
            return self.generic_visit(node)
        def visit_Assign(self,node):
            if any(isinstance(n,ast.Name) and n.id in ('wide_layout','wide_end') for n in node.targets):return None
            return self.generic_visit(node)
        def visit_Name(self,node):
            if node.id in ('wide_layout','wide_end'):node.id={'wide_layout':'WIDE_LAYOUT','wide_end':'WIDE_END'}[node.id]
            return node
        def visit_Call(self,node):
            node=self.generic_visit(node);node.keywords=[k for k in node.keywords if k.arg!='large_image']
            if node.args and isinstance(node.args[-1],ast.Attribute) and node.args[-1].attr=='large_image':node.args.pop()
            node.args=[a for a in node.args if not(isinstance(a,ast.Starred) and isinstance(a.value,ast.List) and not a.value.elts)]
            return node
        def visit_List(self,node):
            node=self.generic_visit(node)
            node.elts=[a for a in node.elts if not(isinstance(a,ast.Starred) and isinstance(a.value,ast.List) and not a.value.elts)]
            return node
    for path in ('scripts/build_x86_64_boot_programs.py','scripts/build_x86_64_c_payload.py'):
        current=Off().visit(ast.parse((ROOT/path).read_text(encoding='utf-8')))
        v.need(ast.dump(current)==ast.dump(ast.parse(v.original(path))),'complete disabled Python '+path)

def defaults():
    binding();projection()
    for name in ('test/test_x86_64_program_memory.py','test/test_x86_64_program_memory_boot.py',
                 'test/test_x86_64_image_import.py','test/test_x86_64_c_payload.py'):
        run('legacy-'+Path(name).stem,[sys.executable,name,'-v'],300)
    for name,sha in v.read(v.EVIDENCE/'baseline01.json')['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'clean baseline unchanged')
    predecessor=v.read(ROOT/'build/codex-agent/r83bt-native-text/candidate03/acceptance-seal.json')
    v.need(predecessor['passed'],'accepted native text predecessor')
    for name,sha in predecessor['package']['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'accepted text artifact unchanged')
    v.save(v.BASE/'defaults.json',dict(passed=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    args=p.parse_args();globals()[next(n for n in vars(args) if getattr(args,n))]()
