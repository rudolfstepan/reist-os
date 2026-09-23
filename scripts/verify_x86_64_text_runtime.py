"""Frozen native formatter qualification and retained accepted artifacts."""
from pathlib import Path
import argparse,ast,inspect,re,subprocess,sys,time,tempfile
import verify_x86_64_application_http as http
import verify_x86_64_network_dma as previous
from check_x86_64_wide_shell_media import clone
import run_qemu_x86_64_text_runtime as guest
evidence=clone(previous,[
    ("EVIDENCE=ROOT/'build/codex-agent/r83bj-network-dma'","EVIDENCE=ROOT/'build/codex-agent/r83bt-native-text'"),
    ("BASE=EVIDENCE/'candidate02'","BASE=EVIDENCE/'candidate03'"),
    ("HEAD='c6533954'","HEAD='a72eebe4'"),
    ("PACKAGE='R8.3bj-network-dma'","PACKAGE='R8.3bt-native-text'")],'reist_text_runtime_evidence')
ROOT=evidence.ROOT
PORTABLE=ROOT/'build/codex-agent/r83bt-native-text/portable-production01/binary-binding01.json'

def tools():
    result=http.tools()
    exe,_=guest.portable_toolchain(PORTABLE)
    result['hardware_qemu']=dict(path=str(exe),sha256=evidence.digest(exe))
    result['hardware_binding']=evidence.link(PORTABLE)
    for name in ('nm','objdump','objcopy'):
        path=Path('C:/msys64/mingw64/bin')/(name+'.exe')
        evidence.need(path.is_file(),'BT binary inspection tool')
        result[name]=dict(path=str(path),sha256=evidence.digest(path))
    return result

def archive_review(image):
    from build_user_program import validate_cpp_object
    folder=next(Path(image).parent.glob('programs-*'));archive=folder/'cpp-sysroot/usr/lib/libreisttext.a'
    validate_cpp_object(archive.read_bytes(),architecture='x86_64')
    validate_cpp_object((folder/'texttest.prg').read_bytes(),architecture='x86_64')
    pinned=tools()
    def run(tool,*args):
        p=subprocess.run([pinned[tool]['path'],*map(str,args)],cwd=ROOT,capture_output=True,timeout=30,check=True)
        return p.stdout.decode('ascii').replace('\r','')
    names=set(re.findall(r'(?m)^\S+\s+[A-Za-z]\s+(\S+)$',run('nm','--defined-only','--extern-only',archive)))
    needs=set(re.findall(r'(?m)^\s+U\s+(\S+)$',run('nm','-u',archive)))
    evidence.need({'snprintf','vsnprintf'}<=names and
        needs-names=={'memcpy','memset','scalbn','reist_libc_errno'} and
        not {'vfprintf','FILE','stdout','frexpl','wctomb','strerror'}&names,'BT exact memory formatter closure')
    origins={};current=''
    for line in (folder/'text.map').read_text().splitlines():
        if '.a(' in line:current=line
        if line.split() and line.split()[-1] in ('memcpy','memset','reist_libc_errno','scalbn'):
            origins[line.split()[-1]]=current
    for name in ('memcpy','memset','reist_libc_errno','scalbn'):
        evidence.need(('libm.a' if name=='scalbn' else 'libreistc.a') in origins.get(name,''),'BT strong accepted provider '+name)
    text=run('objdump','-d','--no-show-raw-insn',archive)
    instructions=re.findall(r'(?m)^[ \t]*[0-9a-f]+:[ \t]+([a-z0-9]+)[ \t]*(.*)$',text)
    evidence.need(instructions and not any(op.startswith('v') or op.startswith(('xsave','xrstor')) or
        re.search(r'%mm[0-7]\b',args) for op,args in instructions),'BT no AVX/XSAVE/MMX instructions')
    simd={op for op,args in instructions if re.search(r'%xmm\d+\b',args)}
    allowed=set('addsd subsd mulsd divsd sqrtsd minsd maxsd movsd movss movaps movups movapd movupd movd movq movdqa movdqu '
        'xorpd xorps andpd andps orpd orps andnpd andnps ucomisd comisd cvtsd2si cvttsd2si cvtsi2sd cvtsi2sdl cvtsd2ss cvtss2sd movhpd movlpd '
        'unpcklpd unpckhpd shufpd shufps pshufd punpcklqdq punpckhqdq pxor pand por pandn pcmpeqd pcmpeqb '
        'paddq psubq psllq psrlq psrldq pslldq movmskpd movmskps pmuludq punpckldq'.split())
    evidence.need(simd<=allowed,'BT SSE2 instruction closure '+str(sorted(simd-allowed)))
    # Keep the full raw archive binding. Compare relocatable contents separately
    # because Zig's DWARF records the unique build source directory. Strip only
    # debugging information from a temporary copy, retaining code/data/relocations.
    parent=evidence.EVIDENCE/'archive-review';parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        stripped=Path(tmp)/'libreisttext.a';run('objcopy','--strip-debug',archive,stripped)
        content=evidence.digest(stripped)
    return dict(exports=sorted(names),undefined=sorted(needs),simd=sorted(simd),archive=evidence.link(archive),
                relocatable_sha256=content)

def projection():
    v=evidence
    def exact(s,a,b=''):
        v.need(s.count(a)==1,'BT projection addition '+a[:60]);return s.replace(a,b)
    path='scripts/build-x86_64-bootstrap.ps1';s=(ROOT/path).read_text(encoding='utf-8')
    for value in ('    [switch]$NativeText,\n','if ($NativeText) { $NativeMath = [switch]$true }\n',
                  '        "X86_64_NATIVE_TEXT=$([int]$NativeText.IsPresent)" `\n'):s=exact(s,value)
    v.need(s==v.original(path),'BT complete default Windows build')
    path='Makefile';s=(ROOT/path).read_text(encoding='utf-8')
    a=s.index('# Explicit native bounded text formatter;');z=s.index('# Explicit native numeric profile;',a);s=s[:a]+s[z:]
    s=exact(s,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_TEXT)),--text-runtime,)\n')
    a=s.index('.PHONY: x86_64-text-runtime-media');z=s.index('.PHONY: x86_64-math-runtime-media',a);s=s[:a]+s[z:]
    v.need(s==v.original(path),'BT complete default Make build')
    class Disabled(ast.NodeTransformer):
        def visit_If(self,n):
            if any(isinstance(x,ast.Name) and x.id=='text_runtime' for x in ast.walk(n.test)):
                v.need(not n.orelse,'BT no hidden alternative');return None
            return self.generic_visit(n)
        def visit_FunctionDef(self,n):
            if n.name=='build':
                v.need(n.args.args[-1].arg=='text_runtime' and n.args.defaults[-1].value is False,'BT default false')
                n.args.args.pop();n.args.defaults.pop()
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call) and any(isinstance(a,ast.Constant) and a.value=='--text-runtime' for a in n.value.args):return None
            return self.generic_visit(n)
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if n.args and isinstance(n.args[-1],ast.Attribute) and n.args[-1].attr=='text_runtime':n.args.pop()
            return n
    path='scripts/build_x86_64_boot_programs.py'
    v.need(ast.dump(Disabled().visit(ast.parse((ROOT/path).read_text())))==ast.dump(ast.parse(v.original(path))),'BT entire default program builder')
    class I386(ast.NodeTransformer):
        def visit_FunctionDef(self,n):
            if n.name=='compile_text' and n.args.kwonlyargs:
                v.need([x.arg for x in n.args.kwonlyargs]==['architecture'] and n.args.kw_defaults[0].value=='i386','BT default i386 architecture')
                n.args.kwonlyargs=[];n.args.kw_defaults=[]
            return self.generic_visit(n)
        def visit_ImportFrom(self,n):
            if n.module=='build_user_math' and [x.name for x in n.names]==['selected_architecture']:return None
            return n
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='selected_architecture':return None
            return self.generic_visit(n)
        def visit_If(self,n):
            if any(isinstance(x,ast.Name) and x.id=='architecture' for x in ast.walk(n.test)):
                return [self.visit(x) for x in n.orelse]
            return self.generic_visit(n)
        def visit_Assign(self,n):
            if any(isinstance(x,ast.Name) and x.id=='content' for x in n.targets):return None
            return self.generic_visit(n)
        def visit_Name(self,n):
            if n.id=='content':return ast.parse('adapt(name,source.read_text())',mode='eval').body
            return n
    path='scripts/build_user_text.py'
    v.need(ast.dump(I386().visit(ast.parse((ROOT/path).read_text())))==ast.dump(I386().visit(ast.parse(v.original(path)))),'BT complete i386 formatter build')
    def disabled(s):
        lines=s.splitlines(keepends=True);out=[];i=0
        while i<len(lines):
            if lines[i].strip()!='#ifdef REIST_NATIVE_TEXT_RUNTIME':out.append(lines[i]);i+=1;continue
            i+=1;depth=1;alternate=None
            while depth:
                word=lines[i].strip()
                if word.startswith('#if'):depth+=1
                if word=='#endif':depth-=1
                if depth==1 and word=='#else':alternate=i
                if depth:i+=1
            if alternate is not None:out.extend(lines[alternate+1:i])
            i+=1
        return ''.join(out)
    path='userspace/programs/texttest.c'
    v.need(disabled((ROOT/path).read_text())==v.original(path),'BT complete legacy consumer')
    return True

def defaults():
    v=evidence;projection()
    for test in ('test/test_text.py',):
        subprocess.run([sys.executable,test,'-v'],cwd=ROOT,timeout=300,check=True)
    for receipt in ('r83bi-graphical-session/development-build07.json','r83bk-network-fatal/build01.json','r83bl-network-session/build14.json'):
        old=v.read(ROOT/'build/codex-agent'/receipt)
        v.need(all(v.digest(ROOT/n)==sha for n,sha in old['artifacts'].items()),'BT accepted profile artifacts '+receipt)
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=ROOT,timeout=120,check=True)
    for name in ('r83bm-application-udp/candidate04','r83bn-application-tcp/candidate06',
                 'r83bp-application-dns/candidate04','r83bq-application-http/candidate01',
                 'r83br-cpp-runtime/candidate01','r83bs-native-math/candidate07'):
        seal=v.read(ROOT/'build/codex-agent'/name/'acceptance-seal.json');v.need(seal['passed'],'BT retained accepted predecessor')
        for path,sha in seal['package']['artifacts'].items():v.need(v.digest(ROOT/path)==sha,'BT unchanged accepted artifact '+path)
    print('TEXT_RUNTIME_DEFAULTS_OK')

def regression_inputs():
    v=evidence;paths=[]
    for p in v.EVIDENCE.iterdir():
        if p.is_file() and p.suffix in ('.json','.log','.py'):paths.append(p)
    for pattern in ('diagnostic[0-9][0-9]','build[0-9][0-9]','media[0-9][0-9]'):
        for folder in v.EVIDENCE.glob(pattern):
            if folder.is_dir():paths.extend(p for p in folder.rglob('*') if p.is_file() and ('cache' not in str(p) or p.suffix=='.su'))
    for folder in (v.EVIDENCE/'candidate01',v.EVIDENCE/'candidate02',*v.EVIDENCE.glob('portable-*')):
        paths.extend(p for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p))
    prior=ROOT/'build/codex-agent/r83bs-native-math/candidate07'
    paths.extend(prior/n for n in ('acceptance-seal.json','final-verification.json','gates-passed.json'))
    return {p.relative_to(ROOT).as_posix():v.digest(p) for p in paths}

# Reuse the exact source/scope/tool binding and one-pass gate executor.
for name in ('freeze','binding'):
    source=inspect.getsource(getattr(http,name))
    if name=='freeze':source=guest.replace(source,'[600,600,600,4800,600]','[600,600,600,2200,600]')
    exec(compile(source,'<BT-frozen-'+name+'>','exec'),globals())

def stack_review(image):
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    evidence.need(len(folders)==1,'BT stack unique program inputs');folder=folders[0]
    reports=list((folder/'zig-cache/tmp').glob('*.su'))+list(folder.glob('math-native/cache-*/tmp/*.su'))+list(folder.glob('math-cache/tmp/*.su'))+list(folder.glob('text-native/cache-*/tmp/*.su'))+list(folder.glob('text-cache/tmp/*.su'))
    evidence.need(len(reports)==72,'BT all native runtime and numeric compiler stack reports')
    total=0;rows={}
    for p in reports:
        evidence.need(p.stat().st_size<=65536,'BT stack report bound')
        for line in p.read_text(encoding='utf-8').splitlines():
            name,size,kind=line.split('\t');size=int(size)
            evidence.need(kind=='static' and 0<=size<=8192,'BT no dynamic/unbounded native stack')
            evidence.need(name not in rows,'BT unique compiled function stack');rows[name]=size;total+=size
    # All functions together are a conservative bound for the reviewed acyclic
    # graph; fixed provider callbacks point only to process_acquire/release.
    evidence.need(rows and total+2048<=32768,'BT aggregate static frames plus entry/call margin')
    return dict(functions=rows,aggregate=total,margin=2048,stack=32768)

def image():
    v=evidence;row=v.read(v.BASE/'package.json');path=ROOT/row['image']['path']
    v.need(row['passed'] and v.link(path)==row['image'] and stack_review(path)==row['stack'] and
        archive_review(path)==row['archive'],'BT bound reference/stack/archive');return path

def stack_signature(image,review):
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and
             (p/'boot-programs.bin').read_bytes()==catalog]
    evidence.need(len(folders)==1,'BT stack signature source root')
    prefixes=(folders[0].relative_to(ROOT).as_posix()+'/',folders[0].as_posix()+'/')
    result={}
    for name,size in review['functions'].items():
        key=name.replace('\\','/')
        for prefix in prefixes:
            if key.startswith(prefix):key=key[len(prefix):];break
        evidence.need(key not in result,'BT stack signature unique source/function')
        result[key]=size
    return dict(functions=result,aggregate=review['aggregate'],margin=review['margin'],stack=review['stack'])

def hardware_image():
    v=evidence;row=v.read(v.BASE/'package.json');path=ROOT/row['hardware_image']['path']
    v.need(row['passed'] and v.link(path)==row['hardware_image'],'BT bound hardware image')
    reference=image()
    # Exactly the same Ring-3 catalog, numeric library and consumers run on
    # both builds. The opt-in assembly bootstrap is the sole kernel exception.
    for name in ('boot-programs.bin',):
        v.need((path.parent/name).read_bytes()==(reference.parent/name).read_bytes(),'BT identical hardware catalog')
    _,_,a=guest.image_config(reference,'healthy4g');_,_,b=guest.image_config(path,'healthy4g')
    hardware_stack=stack_review(path)
    v.need(a==b and hardware_stack==row['hardware_stack'] and
           stack_signature(path,hardware_stack)==stack_signature(reference,row['stack']) and
           archive_review(path)==row['hardware_archive'] and
           row['archive']['relocatable_sha256']==row['hardware_archive']['relocatable_sha256'],
           'BT identical hardware userspace/stack/archive')
    return path

def package():
    import check_x86_64_text_runtime_media as consumer
    v=evidence;f=binding();folder=v.BASE/'build';media=v.BASE/'media'
    def run(name,command,limit):
        binding();v.save(v.BASE/(name+'-started.json'),dict(command=command,limit=limit,sources=f['sources'],tools=f['tools']))
        log=v.BASE/(name+'.log');start=time.monotonic()
        with log.open('xb') as out:p=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
        row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,passed=p.returncode==0,log=v.link(log))
        v.save(v.BASE/(name+'.json'),row);v.need(row['passed'] and row['elapsed']<=limit,name+' failed: '+log.read_text(errors='replace')[-1800:]);binding()
    run('reference-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeText','-OutputDirectory',folder.relative_to(ROOT).as_posix()],300)
    run('reference-media',[sys.executable,'scripts/build_x86_64_text_runtime_media.py','--input-directory',
        str(folder/'x86_64'),'--output-directory',str(media)],180)
    consumer.verify(media);path=folder/'x86_64/reist-x86_64-bootstrap.elf'
    hardware=v.BASE/'hardware'
    run('hardware-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeText','-NativeMathHardware','-OutputDirectory',hardware.relative_to(ROOT).as_posix()],300)
    hardware_path=hardware/'x86_64/reist-x86_64-bootstrap.elf'
    v.save(v.BASE/'package.json',dict(passed=True,stack=stack_review(path),archive=archive_review(path),image=v.link(path),
        hardware_image=v.link(hardware_path),hardware_archive=archive_review(hardware_path),hardware_stack=stack_review(hardware_path),
        index=v.link(media/'text-runtime-media.json'),artifacts={p.relative_to(ROOT).as_posix():v.digest(p)
        for root in (folder,hardware) for p in root.rglob('*') if p.is_file() and 'cache' not in str(p) and (p.suffix in ('.elf','.prg','.bin','.map','.o','.a') or 'cpp-sysroot' in p.parts)}))
    hardware_image()

def runtime():
    v=evidence;binding();img=hardware_image();rows=[]
    for name,_,_,_ in guest.CASES:
        binding();folder=v.BASE/'guests'/name
        row=guest.run_portable_hardware_case(img,folder,name,PORTABLE)
        config,_,_=guest.image_config(img,name)
        row['hardware']=guest.validate_hardware_bootstrap(folder,config);rows.append(row)
        v.save(v.BASE/(name+'.json'),row);print('TEXT_RUNTIME_CASE_OK',name,flush=True)
    v.need(sum(row['guest_elapsed'] for row in rows)<=1800,'BT ten-guest bound')
    v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows))

def review():
    v=evidence;f=binding();img=hardware_image();matrix=v.read(v.BASE/'matrix.json')
    v.need(matrix['passed'] and len(matrix['cases'])==10,'BT ten fresh guests')
    for row,(name,case,_,_) in zip(matrix['cases'],guest.CASES):
        v.need(row['label']==name and row['passed'] and row['closed'] and row['guest_elapsed']<=180,'BT ordered bounded cases')
        module=guest.namespace(name);config,records,files=guest.image_config(img,name);module.app_files=files
        proof=module.evaluate(v.BASE/'guests'/name,config,records,(img.parent/'boot-programs.bin').read_bytes(),case,2,files)
        v.need(proof==row['proof'],'BT independent complete replay '+name)
        v.need(guest.validate_hardware_bootstrap(v.BASE/'guests'/name,config)==row['hardware'],
               'BT independent hardware bootstrap replay '+name)
    for name,sha in v.read(v.BASE/'package.json')['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'BT artifact '+name)
    v.need(set(v.changed())<=set(v.package_row()['allowed_files']) and not v.git('diff','--cached','--name-only'),'BT final scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    raw={p.relative_to(ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}
    v.save(v.BASE/'acceptance-seal.json',dict(passed=True,frozen=f,raw=raw,package=v.read(v.BASE/'package.json'),
        gates=[v.read(v.BASE/f'gate-{n:02d}.json') for n in range(1,5)]))
    print('TEXT_RUNTIME_REVIEW_OK')

def gates():evidence.binding=binding;evidence.gates()

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args();globals()[next(n for n in vars(a) if getattr(a,n))]()
