"""Frozen BR qualification; retained earlier profiles and ten fresh guests."""
from pathlib import Path
import argparse,ast,copy,hashlib,inspect,json,re,subprocess,sys,time,types
import verify_x86_64_application_http as http
import verify_x86_64_network_dma as previous
from check_x86_64_wide_shell_media import clone
import run_qemu_x86_64_cpp_runtime as guest
evidence=clone(previous,[
    ("EVIDENCE=ROOT/'build/codex-agent/r83bj-network-dma'","EVIDENCE=ROOT/'build/codex-agent/r83br-cpp-runtime'"),
    ("BASE=EVIDENCE/'candidate02'","BASE=EVIDENCE/'candidate01'"),
    ("HEAD='c6533954'","HEAD='4acbf3fb'"),
    ("PACKAGE='R8.3bj-network-dma'","PACKAGE='R8.3br-cpp-runtime'")],'reist_cpp_runtime_evidence')
ROOT=evidence.ROOT

def tools():return http.tools()

def projection():
    v=evidence
    def exact(s,a,b=''):
        v.need(s.count(a)==1,'BR projection addition '+a[:60]);return s.replace(a,b)
    def tokens(s):return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))
    def disabled(s):
        lines=s.splitlines(keepends=True);out=[];i=0
        while i<len(lines):
            word=lines[i].strip()
            if word not in ('#ifdef REIST_NATIVE_CPP_RUNTIME','#ifndef REIST_NATIVE_CPP_RUNTIME'):
                out.append(lines[i]);i+=1;continue
            positive=word.startswith('#ifdef');i+=1;start=i;depth=1;alternate=None
            while depth:
                word=lines[i].strip()
                if word.startswith('#if'):depth+=1
                if word=='#endif':depth-=1
                if depth==1 and word=='#else':alternate=i
                if depth:i+=1
            chosen=('' if alternate is None else ''.join(lines[alternate+1:i])) if positive else ''.join(lines[start:alternate if alternate is not None else i])
            out.append(disabled(chosen));i+=1
        return ''.join(out)
    path='userspace/programs/cpptest.cpp'
    current=disabled((ROOT/path).read_text(encoding='utf-8'))
    v.need(tokens(current)==tokens(v.original(path)),'BR complete disabled C++ consumer')
    path='userspace/libc/lib/process_heap.c';s=(ROOT/path).read_text(encoding='utf-8')
    start=s.index('#if UINTPTR_MAX == UINT64_MAX\n');end=s.index('#endif\n',start)
    alternate=s.index('#else\n',start);s=s[:start]+s[alternate+6:end]+s[end+7:]
    s=exact(s,'_Static_assert(sizeof(reist_libc_stats_t)==24U,"fixed-width stats v1 ABI changed");\n')
    v.need(tokens(s)==tokens(v.original(path)),'BR complete i386 process provider')
    for path in ('userspace/libc/include/reist/libc.h','userspace/libc/lib/heap.c',
                 'userspace/libc/lib/bytes.c','userspace/libc/lib/runtime.c','userspace/cpp/runtime.cpp'):
        v.need(tokens((ROOT/path).read_text(encoding='utf-8'))==tokens(v.original(path)),'BR retained allocator/type ABI '+path)
    path='scripts/build-x86_64-bootstrap.ps1';s=(ROOT/path).read_text(encoding='utf-8')
    for a in ('    [switch]$NativeCppRuntime,\n','if ($NativeCppRuntime) { $NativeAppFiles = [switch]$true }\n',
              '        "X86_64_NATIVE_CPP_RUNTIME=$([int]$NativeCppRuntime.IsPresent)" `\n'):s=exact(s,a)
    v.need(s==v.original(path),'BR complete default Windows build')
    path='Makefile';s=(ROOT/path).read_text(encoding='utf-8')
    # Remove only the named opt-in selector and independent media target.
    a=s.index('# Explicit native C/C++');b=s.index('# BC explicit Ring3 application objects;',a);s=s[:a]+s[b:]
    s=exact(s,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_CPP_RUNTIME)),--app-cpp-runtime,)\n')
    a=s.index('.PHONY: x86_64-cpp-runtime-media');b=s.index('.PHONY: x86_64-application-http-media',a);s=s[:a]+s[b:]
    v.need(s==v.original(path),'BR complete default Make build')
    class Disabled(ast.NodeTransformer):
        def visit_If(self,n):
            if any(isinstance(x,ast.Name) and x.id=='app_cpp_runtime' for x in ast.walk(n.test)):
                v.need(not n.orelse,'BR no hidden build alternative');return None
            return self.generic_visit(n)
        def visit_FunctionDef(self,n):
            if n.name=='build':
                v.need(n.args.args[-1].arg=='app_cpp_runtime' and n.args.defaults[-1].value is False,'BR explicit default false')
                n.args.args.pop();n.args.defaults.pop()
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call) and any(isinstance(a,ast.Constant) and a.value=='--app-cpp-runtime' for a in n.value.args):return None
            return self.generic_visit(n)
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if n.args and isinstance(n.args[-1],ast.Attribute) and n.args[-1].attr=='app_cpp_runtime':n.args.pop()
            return n
    path='scripts/build_x86_64_boot_programs.py'
    v.need(ast.dump(Disabled().visit(ast.parse((ROOT/path).read_text(encoding='utf-8'))))==ast.dump(ast.parse(v.original(path))),
           'BR complete default program builder')
    class Admission(ast.NodeTransformer):
        """Specialize the explicit i386 default and compare the entire old AST."""
        aliases={'header_type':'ELF_HEADER','section_type':'ELF_SECTION_HEADER'}
        def visit_Assign(self,n):
            if len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('native','header_type','section_type','symbol_type','identity'):return None
            return self.generic_visit(n)
        def visit_If(self,n):
            if isinstance(n.test,ast.Name) and n.test.id=='native':return n.orelse
            if isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='architecture':return None
            return self.generic_visit(n)
        def visit_IfExp(self,n):
            return self.visit(n.orelse) if isinstance(n.test,ast.Name) and n.test.id=='native' else self.generic_visit(n)
        def visit_Name(self,n):
            if n.id in self.aliases:return ast.Name(id=self.aliases[n.id],ctx=n.ctx)
            if n.id=='identity':return ast.Constant(value=b'\x7fELF\x01\x01\x01')
            return n
        def visit_Attribute(self,n):
            if isinstance(n.value,ast.Name) and n.value.id=='symbol_type' and n.attr=='size':return ast.Constant(value=16)
            return self.generic_visit(n)
        def visit_Call(self,n):
            if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='symbol_type':
                v.need(n.func.attr=='unpack_from','BR i386 symbol operation')
                n.func.value.id='struct';n.args.insert(0,ast.Constant(value='<IIIBBH'))
            if isinstance(n.func,ast.Name) and n.func.id=='validate_cpp_object':n.keywords=[]
            return self.generic_visit(n)
    path='scripts/build_user_program.py';tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    for n in tree.body:
        if isinstance(n,ast.FunctionDef) and n.name=='validate_cpp_object':
            v.need([x.arg for x in n.args.kwonlyargs]==['architecture'] and n.args.kw_defaults[0].value=='i386','BR explicit i386 admission default')
            n.args.kwonlyargs=[];n.args.kw_defaults=[];Admission().visit(n)
    v.need(ast.dump(tree)==ast.dump(ast.parse(v.original(path))),'BR full i386 admission projection')
    return True

def defaults():
    v=evidence;projection()
    for test in ('test/test_user_cpp.py',):
        subprocess.run([sys.executable,test,'-v'],cwd=ROOT,timeout=300,check=True)
    for receipt in ('r83bi-graphical-session/development-build07.json','r83bk-network-fatal/build01.json','r83bl-network-session/build14.json'):
        old=v.read(ROOT/'build/codex-agent'/receipt)
        v.need(all(v.digest(ROOT/n)==sha for n,sha in old['artifacts'].items()),'BR accepted profile artifacts '+receipt)
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=ROOT,timeout=120,check=True)
    for name in ('r83bm-application-udp/candidate04','r83bn-application-tcp/candidate06',
                 'r83bp-application-dns/candidate04','r83bq-application-http/candidate01'):
        seal=v.read(ROOT/'build/codex-agent'/name/'acceptance-seal.json');v.need(seal['passed'],'BR retained accepted predecessor')
        for path,sha in seal['package']['artifacts'].items():v.need(v.digest(ROOT/path)==sha,'BR unchanged accepted artifact '+path)
    print('CPP_RUNTIME_DEFAULTS_OK')

def regression_inputs():
    v=evidence;paths=[]
    for name in ('diagnostic01','diagnostic02','diagnostic03'):
        folder=v.EVIDENCE/name;v.need(folder.is_dir(),'BR retained diagnostic '+name)
        paths.extend(p for p in folder.rglob('*') if p.is_file())
    paths.extend(v.EVIDENCE.glob('development-host*.json'))
    paths.extend(v.EVIDENCE.glob('build[0-9][0-9].json'))
    paths.extend(v.EVIDENCE.glob('media[0-9][0-9].json'))
    paths.extend(p for p in (v.EVIDENCE/'build03/x86_64').rglob('*') if p.is_file() and 'cache' not in str(p))
    return {p.relative_to(ROOT).as_posix():v.digest(p) for p in paths}

# Reuse the exact source/scope/tool binding and one-pass gate executor.
for name in ('freeze','binding'):
    source=inspect.getsource(getattr(http,name))
    if name=='freeze':source=guest.replace(source,'[600,600,600,4800,600]','[600,600,600,2000,600]')
    exec(compile(source,'<BR-frozen-'+name+'>','exec'),globals())

def stack_review(image):
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    evidence.need(len(folders)==1,'BR stack unique program inputs');folder=folders[0]
    reports=list((folder/'zig-cache/tmp').glob('*.su'));evidence.need(len(reports)==7,'BR seven real compiler stack reports')
    total=0;rows={}
    for p in reports:
        evidence.need(p.stat().st_size<=65536,'BR stack report bound')
        for line in p.read_text(encoding='utf-8').splitlines():
            name,size,kind=line.split('\t');size=int(size)
            evidence.need(kind=='static' and 0<=size<=2048,'BR no dynamic/unbounded native stack')
            evidence.need(name not in rows,'BR unique compiled function stack');rows[name]=size;total+=size
    # All functions together are a conservative bound for the reviewed acyclic
    # graph; fixed provider callbacks point only to process_acquire/release.
    evidence.need(rows and total+2048<=32768,'BR aggregate static frames plus entry/call margin')
    return dict(functions=rows,aggregate=total,margin=2048,stack=32768)

def image():
    v=evidence;row=v.read(v.BASE/'package.json');path=ROOT/row['image']['path']
    v.need(row['passed'] and v.link(path)==row['image'] and stack_review(path)==row['stack'],'BR bound reference/stack');return path

def package():
    import check_x86_64_cpp_runtime_media as consumer
    v=evidence;f=binding();folder=v.BASE/'build';media=v.BASE/'media'
    def run(name,command,limit):
        binding();v.save(v.BASE/(name+'-started.json'),dict(command=command,limit=limit,sources=f['sources'],tools=f['tools']))
        log=v.BASE/(name+'.log');start=time.monotonic()
        with log.open('xb') as out:p=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
        row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,passed=p.returncode==0,log=v.link(log))
        v.save(v.BASE/(name+'.json'),row);v.need(row['passed'] and row['elapsed']<=limit,name+' failed: '+log.read_text(errors='replace')[-1800:]);binding()
    run('reference-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeCppRuntime','-OutputDirectory',folder.relative_to(ROOT).as_posix()],300)
    run('reference-media',[sys.executable,'scripts/build_x86_64_cpp_runtime_media.py','--input-directory',
        str(folder/'x86_64'),'--output-directory',str(media)],180)
    consumer.verify(media);path=folder/'x86_64/reist-x86_64-bootstrap.elf'
    v.save(v.BASE/'package.json',dict(passed=True,stack=stack_review(path),image=v.link(path),
        index=v.link(media/'cpp-runtime-media.json'),artifacts={p.relative_to(ROOT).as_posix():v.digest(p)
        for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p) and p.suffix in ('.elf','.prg','.bin','.map','.o','.a')}))

def runtime():
    v=evidence;binding();img=image();rows=[]
    for name,_,_,_ in guest.CASES:
        binding();row=guest.run_case(img,v.BASE/'guests'/name,name);rows.append(row)
        v.save(v.BASE/(name+'.json'),row);print('CPP_RUNTIME_CASE_OK',name,flush=True)
    v.need(sum(row['guest_elapsed'] for row in rows)<=1800,'BR ten-guest bound')
    v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows))

def review():
    v=evidence;f=binding();img=image();matrix=v.read(v.BASE/'matrix.json')
    v.need(matrix['passed'] and len(matrix['cases'])==10,'BR ten fresh guests')
    for row,(name,case,_,_) in zip(matrix['cases'],guest.CASES):
        v.need(row['label']==name and row['passed'] and row['closed'] and row['guest_elapsed']<=180,'BR ordered bounded cases')
        module=guest.namespace(name);config,records,files=guest.image_config(img,name);module.app_files=files
        proof=module.evaluate(v.BASE/'guests'/name,config,records,(img.parent/'boot-programs.bin').read_bytes(),case,2,files)
        v.need(proof==row['proof'],'BR independent complete replay '+name)
    for name,sha in v.read(v.BASE/'package.json')['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'BR artifact '+name)
    v.need(set(v.changed())<=set(v.package_row()['allowed_files']) and not v.git('diff','--cached','--name-only'),'BR final scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    raw={p.relative_to(ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}
    v.save(v.BASE/'acceptance-seal.json',dict(passed=True,frozen=f,raw=raw,package=v.read(v.BASE/'package.json'),
        gates=[v.read(v.BASE/f'gate-{n:02d}.json') for n in range(1,5)]))
    print('CPP_RUNTIME_REVIEW_OK')

def gates():evidence.binding=binding;evidence.gates()

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args();globals()[next(n for n in vars(a) if getattr(a,n))]()
