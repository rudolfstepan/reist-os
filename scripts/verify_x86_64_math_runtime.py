"""Frozen BS qualification; retained earlier profiles and ten fresh guests."""
from pathlib import Path
import argparse,ast,inspect,re,subprocess,sys,time,tempfile
import verify_x86_64_application_http as http
import verify_x86_64_network_dma as previous
from check_x86_64_wide_shell_media import clone
import run_qemu_x86_64_math_runtime as guest
evidence=clone(previous,[
    ("EVIDENCE=ROOT/'build/codex-agent/r83bj-network-dma'","EVIDENCE=ROOT/'build/codex-agent/r83bs-native-math'"),
    ("BASE=EVIDENCE/'candidate02'","BASE=EVIDENCE/'candidate07'"),
    ("HEAD='c6533954'","HEAD='8d3ec6f7'"),
    ("PACKAGE='R8.3bj-network-dma'","PACKAGE='R8.3bs-native-math'")],'reist_math_runtime_evidence')
ROOT=evidence.ROOT
PORTABLE=evidence.EVIDENCE/'portable-qemu/binary-binding09.json'

def tools():
    result=http.tools()
    exe,_=guest.portable_toolchain(PORTABLE)
    result['hardware_qemu']=dict(path=str(exe),sha256=evidence.digest(exe))
    result['hardware_binding']=evidence.link(PORTABLE)
    for name in ('nm','objdump','objcopy'):
        path=Path('C:/msys64/mingw64/bin')/(name+'.exe')
        evidence.need(path.is_file(),'BS binary inspection tool')
        result[name]=dict(path=str(path),sha256=evidence.digest(path))
    return result

def archive_review(image):
    import build_user_math as math
    from build_user_program import validate_cpp_object
    folder=next(Path(image).parent.glob('programs-*'));archive=folder/'cpp-sysroot/usr/lib/libm.a'
    validate_cpp_object(archive.read_bytes(),architecture='x86_64')
    validate_cpp_object((folder/'mathtest.prg').read_bytes(),architecture='x86_64')
    pinned=tools()
    def run(tool,*args):
        p=subprocess.run([pinned[tool]['path'],*map(str,args)],cwd=ROOT,capture_output=True,timeout=30,check=True)
        return p.stdout.decode('ascii').replace('\r','')
    names=set(re.findall(r'(?m)^\S+\s+[A-Za-z]\s+(\S+)$',run('nm','--defined-only','--extern-only',archive)))
    needs=set(re.findall(r'(?m)^\s+U\s+(\S+)$',run('nm','-u',archive)))
    evidence.need(set(math.FUNCTIONS+math.INTEGER_FUNCTIONS+('fegetround','fesetround','feclearexcept','fetestexcept'))<=names
        and not needs-names and not {'sqrtl','drem'}&names,'BS complete public subset/internal symbol closure')
    text=run('objdump','-d','--no-show-raw-insn',archive)
    instructions=re.findall(r'(?m)^[ \t]*[0-9a-f]+:[ \t]+([a-z0-9]+)[ \t]*(.*)$',text)
    evidence.need(instructions and not any(op.startswith('v') or op.startswith(('xsave','xrstor')) or
        re.search(r'%mm[0-7]\b',args) for op,args in instructions),'BS no AVX/XSAVE/MMX instructions')
    simd={op for op,args in instructions if re.search(r'%xmm\d+\b',args)}
    allowed=set('addsd subsd mulsd divsd sqrtsd minsd maxsd movsd movss movaps movups movapd movupd movd movq movdqa movdqu '
        'xorpd xorps andpd andps orpd orps andnpd andnps ucomisd comisd cvtsd2si cvttsd2si cvtsi2sd cvtsi2sdl cvtsd2ss cvtss2sd movhpd movlpd '
        'unpcklpd unpckhpd shufpd shufps pshufd punpcklqdq punpckhqdq pxor pand por pandn pcmpeqd pcmpeqb '
        'paddq psubq psllq psrlq psrldq pslldq movmskpd movmskps'.split())
    evidence.need(simd<=allowed,'BS SSE2 instruction closure '+str(sorted(simd-allowed)))
    # Keep the full raw archive binding. Compare relocatable contents separately
    # because Zig's DWARF records the unique build source directory. Strip only
    # debugging information from a temporary copy, retaining code/data/relocations.
    parent=evidence.EVIDENCE/'archive-review';parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        stripped=Path(tmp)/'libm.a';run('objcopy','--strip-debug',archive,stripped)
        content=evidence.digest(stripped)
    return dict(exports=sorted(names),undefined=sorted(needs),simd=sorted(simd),archive=evidence.link(archive),
                relocatable_sha256=content)

def projection():
    v=evidence
    def exact(s,a,b=''):
        v.need(s.count(a)==1,'BS projection addition '+a[:60]);return s.replace(a,b)
    path='scripts/build-x86_64-bootstrap.ps1';s=(ROOT/path).read_text(encoding='utf-8')
    for a in ('    [switch]$NativeMathHardware,\n',
              'if ($NativeMathHardware) { $NativeMath = [switch]$true }\n',
              '        "X86_64_NATIVE_MATH_HARDWARE=$([int]$NativeMathHardware.IsPresent)" `\n',
              '    [switch]$NativeMath,\n','if ($NativeMath) { $NativeCppRuntime = [switch]$true }\n',
              '        "X86_64_NATIVE_MATH=$([int]$NativeMath.IsPresent)" `\n'):s=exact(s,a)
    v.need(s==v.original(path),'BS complete default Windows build')
    path='Makefile';s=(ROOT/path).read_text(encoding='utf-8')
    a=s.index('# Explicit native numeric profile;');b=s.index('# Explicit native C/C++',a);s=s[:a]+s[b:]
    s=exact(s,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_MATH)),--math-runtime,)\n')
    a=s.index('.PHONY: x86_64-math-runtime-media');b=s.index('.PHONY: x86_64-cpp-runtime-media',a);s=s[:a]+s[b:]
    s=exact(s,' $(X86_64_MATH_HARDWARE_ASM)')
    v.need(s==v.original(path),'BS complete default Make build')
    path='arch/x86_64/boot/entry.asm';s=(ROOT/path).read_text(encoding='utf-8')
    s,count=re.subn(r'%ifdef REIST_NATIVE_MATH_HARDWARE\n.*?%endif\n','',s,flags=re.S)
    v.need(count==2 and s==v.original(path),'BS complete disabled hardware bootstrap')
    class Disabled(ast.NodeTransformer):
        def visit_If(self,n):
            if any(isinstance(x,ast.Name) and x.id=='math_runtime' for x in ast.walk(n.test)):
                v.need(not n.orelse,'BS no hidden build alternative');return None
            return self.generic_visit(n)
        def visit_FunctionDef(self,n):
            if n.name=='build':
                v.need(n.args.args[-1].arg=='math_runtime' and n.args.defaults[-1].value is False,'BS explicit default false')
                n.args.args.pop();n.args.defaults.pop()
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call) and any(isinstance(a,ast.Constant) and a.value=='--math-runtime' for a in n.value.args):return None
            return self.generic_visit(n)
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if n.args and isinstance(n.args[-1],ast.Attribute) and n.args[-1].attr=='math_runtime':n.args.pop()
            return n
    path='scripts/build_x86_64_boot_programs.py'
    v.need(ast.dump(Disabled().visit(ast.parse((ROOT/path).read_text(encoding='utf-8'))))==ast.dump(ast.parse(v.original(path))),
           'BS complete default program builder')
    class I386(ast.NodeTransformer):
        def visit_FunctionDef(self,n):
            if n.name=='selected_architecture':return None
            if n.name in ('extract','source_files','compile_math') and n.args.kwonlyargs:
                v.need([x.arg for x in n.args.kwonlyargs]==['architecture'] and n.args.kw_defaults[0].value=='i386','BS exact default architecture')
                n.args.kwonlyargs=[];n.args.kw_defaults=[]
            return self.generic_visit(n)
        def visit_Assign(self,n):
            if any(isinstance(x,ast.Name) and x.id in ('NATIVE_MEMBERS','members') for x in n.targets):return None
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='selected_architecture':return None
            return self.generic_visit(n)
        def visit_If(self,n):
            if isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='architecture':
                return [self.visit(x) for x in n.orelse]
            return self.generic_visit(n)
        def visit_Name(self,n):
            if n.id=='members':return ast.Name(id='MEMBERS',ctx=n.ctx)
            if n.id=='architecture':return ast.Constant(value='i386')
            return n
        def visit_Call(self,n):
            if isinstance(n.func,ast.Name) and n.func.id=='source_files':n.keywords=[]
            return self.generic_visit(n)
        def visit_BinOp(self,n):
            n=self.generic_visit(n)
            if isinstance(n.op,ast.Add) and isinstance(n.left,ast.Constant) and isinstance(n.right,ast.Constant) and isinstance(n.left.value,str) and isinstance(n.right.value,str):
                return ast.Constant(value=n.left.value+n.right.value)
            return n
    path='scripts/build_user_math.py'
    v.need(ast.dump(I386().visit(ast.parse((ROOT/path).read_text(encoding='utf-8'))))==
           ast.dump(I386().visit(ast.parse(v.original(path)))),'BS entire i386 math implementation')
    def disabled(s):
        lines=s.splitlines(keepends=True);out=[];i=0
        while i<len(lines):
            if lines[i].strip()!='#ifdef REIST_NATIVE_MATH_RUNTIME':out.append(lines[i]);i+=1;continue
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
    path='userspace/programs/mathtest.c'
    v.need(disabled((ROOT/path).read_text(encoding='utf-8'))==v.original(path),'BS complete legacy consumer')
    return True

def defaults():
    v=evidence;projection()
    for test in ('test/test_math.py',):
        subprocess.run([sys.executable,test,'-v'],cwd=ROOT,timeout=300,check=True)
    for receipt in ('r83bi-graphical-session/development-build07.json','r83bk-network-fatal/build01.json','r83bl-network-session/build14.json'):
        old=v.read(ROOT/'build/codex-agent'/receipt)
        v.need(all(v.digest(ROOT/n)==sha for n,sha in old['artifacts'].items()),'BS accepted profile artifacts '+receipt)
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=ROOT,timeout=120,check=True)
    for name in ('r83bm-application-udp/candidate04','r83bn-application-tcp/candidate06',
                 'r83bp-application-dns/candidate04','r83bq-application-http/candidate01',
                 'r83br-cpp-runtime/candidate01'):
        seal=v.read(ROOT/'build/codex-agent'/name/'acceptance-seal.json');v.need(seal['passed'],'BS retained accepted predecessor')
        for path,sha in seal['package']['artifacts'].items():v.need(v.digest(ROOT/path)==sha,'BS unchanged accepted artifact '+path)
    print('MATH_RUNTIME_DEFAULTS_OK')

def regression_inputs():
    v=evidence;paths=[]
    for name in ('diagnostic%02d'%n for n in range(1,28)):
        folder=v.EVIDENCE/name;v.need(folder.is_dir(),'BS retained diagnostic '+name)
        paths.extend(p for p in folder.rglob('*') if p.is_file())
    paths.extend(v.EVIDENCE.glob('development-host*.json'))
    paths.extend(v.EVIDENCE.glob('diagnostic*-decoded.json'))
    paths.extend(v.EVIDENCE.glob('diagnostic[0-9][0-9].json'))
    paths.extend(v.EVIDENCE.glob('build[0-9][0-9].json'))
    paths.extend(v.EVIDENCE.glob('media[0-9][0-9].json'))
    paths.extend(v.EVIDENCE.glob('accelerator-probe*.json'))
    for folder in v.EVIDENCE.glob('accelerator-probe[0-9][0-9]'):
        if folder.is_dir():paths.extend(p for p in folder.rglob('*') if p.is_file())
    for name in ('build01','build02'):
        paths.extend(p for p in (v.EVIDENCE/name/'x86_64').rglob('*') if p.is_file() and 'cache' not in str(p))
    portable=PORTABLE.parent
    paths.extend(p for p in portable.iterdir() if p.is_file() and p.suffix in ('.json','.patch','.py','.sh','.log'))
    # Failed tool probes and source/build receipts remain immutable alongside
    # the explicitly selected deployment; no installed tool is replaced.
    paths=[p for p in paths if not p.name.startswith('rejected-binding-')]
    for name in ('candidate01','candidate02','candidate03','candidate04','candidate05','candidate06','archive-diagnosis01'):
        paths.extend(p for p in (v.EVIDENCE/name).rglob('*') if p.is_file() and
                     'cache' not in str(p) and p.suffix in ('.json','.log'))
    paths.extend(v.EVIDENCE/'candidate06/guests/owner-loss/binary-memory'/n for n in ('ram-0028.bin','ram-0029.bin'))
    return {p.relative_to(ROOT).as_posix():v.digest(p) for p in paths}

# Reuse the exact source/scope/tool binding and one-pass gate executor.
for name in ('freeze','binding'):
    source=inspect.getsource(getattr(http,name))
    if name=='freeze':source=guest.replace(source,'[600,600,600,4800,600]','[600,600,600,2000,600]')
    exec(compile(source,'<BS-frozen-'+name+'>','exec'),globals())

def stack_review(image):
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    evidence.need(len(folders)==1,'BS stack unique program inputs');folder=folders[0]
    reports=list((folder/'zig-cache/tmp').glob('*.su'))+list(folder.glob('math-native/cache-*/tmp/*.su'))+list(folder.glob('math-cache/tmp/*.su'))
    evidence.need(len(reports)==66,'BS all native runtime and numeric compiler stack reports')
    total=0;rows={}
    for p in reports:
        evidence.need(p.stat().st_size<=65536,'BS stack report bound')
        for line in p.read_text(encoding='utf-8').splitlines():
            name,size,kind=line.split('\t');size=int(size)
            evidence.need(kind=='static' and 0<=size<=2048,'BS no dynamic/unbounded native stack')
            evidence.need(name not in rows,'BS unique compiled function stack');rows[name]=size;total+=size
    # All functions together are a conservative bound for the reviewed acyclic
    # graph; fixed provider callbacks point only to process_acquire/release.
    evidence.need(rows and total+2048<=32768,'BS aggregate static frames plus entry/call margin')
    return dict(functions=rows,aggregate=total,margin=2048,stack=32768)

def image():
    v=evidence;row=v.read(v.BASE/'package.json');path=ROOT/row['image']['path']
    v.need(row['passed'] and v.link(path)==row['image'] and stack_review(path)==row['stack'] and
        archive_review(path)==row['archive'],'BS bound reference/stack/archive');return path

def stack_signature(image,review):
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and
             (p/'boot-programs.bin').read_bytes()==catalog]
    evidence.need(len(folders)==1,'BS stack signature source root')
    prefixes=(folders[0].relative_to(ROOT).as_posix()+'/',folders[0].as_posix()+'/')
    result={}
    for name,size in review['functions'].items():
        key=name.replace('\\','/')
        for prefix in prefixes:
            if key.startswith(prefix):key=key[len(prefix):];break
        evidence.need(key not in result,'BS stack signature unique source/function')
        result[key]=size
    return dict(functions=result,aggregate=review['aggregate'],margin=review['margin'],stack=review['stack'])

def hardware_image():
    v=evidence;row=v.read(v.BASE/'package.json');path=ROOT/row['hardware_image']['path']
    v.need(row['passed'] and v.link(path)==row['hardware_image'],'BS bound hardware image')
    reference=image()
    # Exactly the same Ring-3 catalog, numeric library and consumers run on
    # both builds. The opt-in assembly bootstrap is the sole kernel exception.
    for name in ('boot-programs.bin',):
        v.need((path.parent/name).read_bytes()==(reference.parent/name).read_bytes(),'BS identical hardware catalog')
    _,_,a=guest.image_config(reference,'healthy4g');_,_,b=guest.image_config(path,'healthy4g')
    hardware_stack=stack_review(path)
    v.need(a==b and hardware_stack==row['hardware_stack'] and
           stack_signature(path,hardware_stack)==stack_signature(reference,row['stack']) and
           archive_review(path)==row['hardware_archive'] and
           row['archive']['relocatable_sha256']==row['hardware_archive']['relocatable_sha256'],
           'BS identical hardware userspace/stack/archive')
    return path

def package():
    import check_x86_64_math_runtime_media as consumer
    v=evidence;f=binding();folder=v.BASE/'build';media=v.BASE/'media'
    def run(name,command,limit):
        binding();v.save(v.BASE/(name+'-started.json'),dict(command=command,limit=limit,sources=f['sources'],tools=f['tools']))
        log=v.BASE/(name+'.log');start=time.monotonic()
        with log.open('xb') as out:p=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
        row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,passed=p.returncode==0,log=v.link(log))
        v.save(v.BASE/(name+'.json'),row);v.need(row['passed'] and row['elapsed']<=limit,name+' failed: '+log.read_text(errors='replace')[-1800:]);binding()
    run('reference-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeMath','-OutputDirectory',folder.relative_to(ROOT).as_posix()],300)
    run('reference-media',[sys.executable,'scripts/build_x86_64_math_runtime_media.py','--input-directory',
        str(folder/'x86_64'),'--output-directory',str(media)],180)
    consumer.verify(media);path=folder/'x86_64/reist-x86_64-bootstrap.elf'
    hardware=v.BASE/'hardware'
    run('hardware-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeMathHardware','-OutputDirectory',hardware.relative_to(ROOT).as_posix()],300)
    hardware_path=hardware/'x86_64/reist-x86_64-bootstrap.elf'
    v.save(v.BASE/'package.json',dict(passed=True,stack=stack_review(path),archive=archive_review(path),image=v.link(path),
        hardware_image=v.link(hardware_path),hardware_archive=archive_review(hardware_path),hardware_stack=stack_review(hardware_path),
        index=v.link(media/'math-runtime-media.json'),artifacts={p.relative_to(ROOT).as_posix():v.digest(p)
        for root in (folder,hardware) for p in root.rglob('*') if p.is_file() and 'cache' not in str(p) and (p.suffix in ('.elf','.prg','.bin','.map','.o','.a') or 'cpp-sysroot' in p.parts)}))
    hardware_image()

def runtime():
    v=evidence;binding();img=hardware_image();rows=[]
    for name,_,_,_ in guest.CASES:
        binding();folder=v.BASE/'guests'/name
        row=guest.run_portable_hardware_case(img,folder,name,PORTABLE)
        config,_,_=guest.image_config(img,name)
        row['hardware']=guest.validate_hardware_bootstrap(folder,config);rows.append(row)
        v.save(v.BASE/(name+'.json'),row);print('MATH_RUNTIME_CASE_OK',name,flush=True)
    v.need(sum(row['guest_elapsed'] for row in rows)<=1800,'BS ten-guest bound')
    v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows))

def review():
    v=evidence;f=binding();img=hardware_image();matrix=v.read(v.BASE/'matrix.json')
    v.need(matrix['passed'] and len(matrix['cases'])==10,'BS ten fresh guests')
    for row,(name,case,_,_) in zip(matrix['cases'],guest.CASES):
        v.need(row['label']==name and row['passed'] and row['closed'] and row['guest_elapsed']<=180,'BS ordered bounded cases')
        module=guest.namespace(name);config,records,files=guest.image_config(img,name);module.app_files=files
        proof=module.evaluate(v.BASE/'guests'/name,config,records,(img.parent/'boot-programs.bin').read_bytes(),case,2,files)
        v.need(proof==row['proof'],'BS independent complete replay '+name)
        v.need(guest.validate_hardware_bootstrap(v.BASE/'guests'/name,config)==row['hardware'],
               'BS independent hardware bootstrap replay '+name)
    for name,sha in v.read(v.BASE/'package.json')['artifacts'].items():v.need(v.digest(ROOT/name)==sha,'BS artifact '+name)
    v.need(set(v.changed())<=set(v.package_row()['allowed_files']) and not v.git('diff','--cached','--name-only'),'BS final scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    raw={p.relative_to(ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}
    v.save(v.BASE/'acceptance-seal.json',dict(passed=True,frozen=f,raw=raw,package=v.read(v.BASE/'package.json'),
        gates=[v.read(v.BASE/f'gate-{n:02d}.json') for n in range(1,5)]))
    print('MATH_RUNTIME_REVIEW_OK')

def gates():evidence.binding=binding;evidence.gates()

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args();globals()[next(n for n in vars(a) if getattr(a,n))]()
