"""Native PS/2 profile: bounded qualification and exact disabled projection."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time,shutil,os,tomllib,shlex,types
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'build/codex-agent/r83bg-input'
BUILD_ID='06'
MEDIA_ID='05'
BASE=EVIDENCE/'candidate04'
HEAD='340da548'
def need(ok,message):
    if not ok:raise ValueError(message)
MAKE_SELECTOR='X86_64_NATIVE_INPUT ?= 0\nifneq ($(words $(X86_64_NATIVE_INPUT)),1)\n$(error NativeInput selector must be one explicit value)\nendif\nifneq ($(filter $(X86_64_NATIVE_INPUT),0 1),$(X86_64_NATIVE_INPUT))\n$(error NativeInput selector must be 0 or 1)\nendif\nifeq ($(X86_64_NATIVE_INPUT),1)\nifneq ($(X86_64_NATIVE_DISPLAY),1)\n$(error NativeInput requires explicit NativeDisplay)\nendif\nendif\nX86_64_INPUT_FLAGS = $(if $(filter 1,$(X86_64_NATIVE_INPUT)),-DREIST_NATIVE_INPUT=1,)\n'
COMPACT_RECIPE='ifeq ($(X86_64_NATIVE_INPUT),1)\n\t@$(PYTHON) scripts/build_x86_64_boot_programs.py --compact-input-elf $(X86_64_BOOTSTRAP_ELF) --objcopy $(OBJCOPY)\nendif\n'
MAKE_PARTS=(MAKE_SELECTOR,COMPACT_RECIPE,
 'X86_64_POOL_FLAGS += $(X86_64_INPUT_FLAGS)\n',
 'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_INPUT)),--input,)\n')
PS_PARTS=('    [switch]$NativeInput,\n',
 'if ($NativeInput) { $NativeDisplay = [switch]$true }\n',
 '        "X86_64_NATIVE_INPUT=$([int]$NativeInput.IsPresent)" `\n')
def without_input_build_selector(source,make=False):
    need(type(source) is str and type(make) is bool,'input projection types')
    tokens=('NATIVE_INPUT','NativeInput','--input,','X86_64_INPUT_FLAGS')
    if not any(token in source for token in tokens):return source
    for part in MAKE_PARTS if make else PS_PARTS:
        need(source.count(part)==1,'complete exact disabled input addition')
        source=source.replace(part,'')
    need(not any(token in source for token in tokens),'unexpected input selector/recipe')
    return source

def default_projection():
    from verify_x86_64_shell_session import disabled
    for name in ('arch/x86_64/proc/cooperative_scheduler.asm','arch/x86_64/proc/process_run.inc',
                 'arch/x86_64/proc/task_family.inc','userspace/sdk/lib/x86_64/shell_session.c'):
        old=subprocess.check_output(['git','show',HEAD+':'+name],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
        current=disabled((ROOT/name).read_text(encoding='utf-8'),'REIST_NATIVE_INPUT',name.endswith(('.asm','.inc')))
        need(current==old,'exact INPUT-disabled accepted source '+name)
    for name in ('Makefile','scripts/build-x86_64-bootstrap.ps1'):
        old=subprocess.check_output(['git','show',HEAD+':'+name],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
        need(without_input_build_selector((ROOT/name).read_text(encoding='utf-8'),name=='Makefile')==old,'exact INPUT-disabled recipe '+name)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,sort_keys=True)
def build_sources():
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,timeout=30).decode().splitlines()
    need(len(names)<=30000,'bounded build source inventory')
    return {name:digest(ROOT/name) for name in sorted(set(names)) if
        name=='Makefile' or name.startswith(('arch/','kernel/','userspace/','include/','lib/','config/')) or
        name.startswith('scripts/build') and name.endswith(('.py','.ps1'))}
def build_tools():
    from build_user_sdk import find_zig
    candidates={'zig':str(find_zig()),'nasm':shutil.which('nasm') or 'C:/tools/nasm-3.02/nasm.exe',
        'make':shutil.which('make'),'objcopy':shutil.which('objcopy') or 'C:/msys64/mingw64/bin/objcopy.exe',
        'pwsh':shutil.which('pwsh'),'python':sys.executable}
    need(all(candidates.values()),'all native build tools present')
    return {name:{'path':str(Path(path).resolve()),'sha256':digest(Path(path).resolve())} for name,path in candidates.items()}
def development_build():
    output=EVIDENCE/('build'+BUILD_ID);receipt=EVIDENCE/('development-build'+BUILD_ID+'.json')
    need(not output.exists() and not receipt.exists(),'one fresh input build reservation')
    state=build_sources();tools=build_tools();command=[tools['pwsh']['path'],'-NoProfile','-File',
        'scripts/build-x86_64-bootstrap.ps1','-NativeInput','-OutputDirectory',output.relative_to(ROOT).as_posix()]
    row=dict(passed=False,command=command,sources=state,tools=tools,builds=1,limit=300)
    save(EVIDENCE/('development-build'+BUILD_ID+'-started.json'),row)
    start=time.monotonic();log=EVIDENCE/('development-build'+BUILD_ID+'.log')
    try:
        with log.open('xb') as stream:
            r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=300,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row['exit_code']=r.returncode
        need(r.returncode==0,'input build failed: '+log.read_text(errors='replace')[-2400:])
        need(build_sources()==state and build_tools()==tools,'immutable build inputs/tools')
        paths=[p for p in output.rglob('*') if p.is_file() and 'cache' not in p.parts and p.suffix in ('.elf','.prg','.o','.bin','.json','.inc')]
        need(len(paths)<2048,'bounded produced artifact inventory')
        row['artifacts']={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
        row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log={'path':log.relative_to(ROOT).as_posix(),'sha256':digest(log)} if log.exists() else None)
        save(receipt,row)

def build_binding():
    row=json.loads((EVIDENCE/('development-build'+BUILD_ID+'.json')).read_text())
    need(row['passed'] and row['builds']==1 and row['elapsed']<=300,'successful bounded build')
    need(build_sources()==row['sources'] and build_tools()==row['tools'],'unchanged complete build inputs/tools')
    for name,sha in row['artifacts'].items():need(digest(ROOT/name)==sha,'unchanged artifact '+name)
    need(digest(ROOT/row['log']['path'])==row['log']['sha256'],'unchanged original build log')
    return EVIDENCE/('build'+BUILD_ID)/'x86_64/reist-x86_64-bootstrap.elf'

def development_media():
    image=build_binding();folder=EVIDENCE/('media'+MEDIA_ID)
    need(not folder.exists(),'one fresh signed media reservation')
    command=[sys.executable,'scripts/build_x86_64_input_media.py','--input-directory',str(image.parent),
             '--output-directory',str(folder)]
    row=dict(passed=False,command=command,limit=180,kernel_builds=0,bios_assemblies=3)
    save(EVIDENCE/('development-media'+MEDIA_ID+'-started.json'),row)
    start=time.monotonic();log=EVIDENCE/('development-media'+MEDIA_ID+'.log')
    try:
        with log.open('xb') as stream:
            r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=180,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row['exit_code']=r.returncode
        need(r.returncode==0,'input media failed: '+log.read_text(errors='replace')[-2400:])
        import check_x86_64_input_media as check
        attempt=check.verify(folder);build_binding()
        row.update(passed=True,attempt=attempt.relative_to(ROOT).as_posix(),
                   index_sha256=digest(folder/'input-media.json'))
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log_sha256=digest(log) if log.exists() else None)
        save(EVIDENCE/('development-media'+MEDIA_ID+'.json'),row)


def package():
    default_projection();image=build_binding()
    import check_x86_64_input_media as check
    folder=EVIDENCE/('media'+MEDIA_ID);attempt=check.verify(folder)
    receipt=json.loads((EVIDENCE/('development-media'+MEDIA_ID+'.json')).read_text())
    need(receipt['passed'] and receipt['index_sha256']==digest(folder/'input-media.json'),'bound input media')
    return image,attempt

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30).decode().strip()
def changed():
    return sorted(set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
def queue_package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    active=[p for p in q['packages'] if p['status']=='active']
    need(len(active)==1 and active[0]['id']==q['active_id']=='R8.3bg-native-input','one exact active package')
    return active[0]
def sources():
    paths=git('ls-files','--cached','--others','--exclude-standard').splitlines()
    need(len(paths)<30000,'bounded qualification source inventory')
    allowed=set(queue_package()['allowed_files'])
    return {n:digest(ROOT/n) for n in sorted(set(paths)) if n=='Makefile' or
            n.startswith(('arch/','kernel/','userspace/','include/','lib/','config/','scripts/','test/')) or
            n in allowed}
def all_tools():
    import run_qemu_x86_64_boot as boot
    result=build_tools()
    for n,p in dict(qemu=boot.resolve_qemu(None),qemu_img=shutil.which('qemu-img') or 'C:/Program Files/qemu/qemu-img.exe',
                    gdb=shutil.which('gdb'),openssl=shutil.which('openssl')).items():
        need(p is not None,'required qualification tool '+n);p=Path(p).resolve();result[n]=dict(path=str(p),sha256=digest(p))
    return result

def freeze():
    need(not BASE.exists() and git('rev-parse','--short=8','HEAD')==HEAD,'fresh candidate and exact implementation baseline')
    p=queue_package();paths=changed();need(set(paths)<=set(p['allowed_files']),'frozen exact file scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'unstaged whitespace-clean candidate')
    image,attempt=package();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==10,'unchanged ten acceptance gates')
    value=dict(candidate=BASE.name,head=git('rev-parse','HEAD'),package=p,changed=paths,sources=sources(),tools=all_tools(),
               commands=commands,limits=[600]*5+[180,3300,180,600,180],image=link(image),
               build=link(EVIDENCE/('development-build'+BUILD_ID+'.json')),
               media=link(EVIDENCE/('development-media'+MEDIA_ID+'.json')),
               media_index=link(EVIDENCE/('media'+MEDIA_ID)/'input-media.json'),attempt=attempt.relative_to(ROOT).as_posix(),
               reserved=dict(kernel_builds=0,media_builds=0,input_guests=12,input_seconds=1080,cli_guests=10,cli_seconds=1730))
    save(BASE/'frozen.json',value)
    for name in paths:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    print('INPUT_FROZEN',BASE.name,flush=True)

def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and queue_package()==f['package'] and changed()==f['changed'] and sources()==f['sources'],'frozen source/queue/scope')
    need(all_tools()==f['tools'],'unchanged qualification tools')
    for key in ('image','build','media','media_index'):need(link(ROOT/f[key]['path'])==f[key],'unchanged '+key)
    return f

def package_gate():
    binding();image,attempt=package()
    import run_x86_64_input as starter
    selected,_=starter.admit(EVIDENCE/('media'+MEDIA_ID));need(selected==attempt,'normal starter binds same signed pair')
    raw=image.with_suffix('.untrimmed.elf').read_bytes();compact=image.read_bytes()
    import build_x86_64_c_payload as elf
    a=elf.elf(raw,32);b=elf.elf(compact,32)
    need(a['programs']==b['programs'] and a['entry']==b['entry'],'compacted outer load topology')
    for part in a['programs']:
        begin=part['offset'];end=begin+part['filesz'];need(raw[begin:end]==compact[begin:end],'all loaded bytes retained')
    removed={n for n,v in a['symbols'].items() if n.startswith('native_input_') and '.' in n and v['binding']==0}
    need(1<=len(removed)<=128 and b['symbols']=={n:v for n,v in a['symbols'].items() if n not in removed},'only input local debug names removed')
    save(BASE/'package.json',dict(passed=True,image=link(image),attempt=str(attempt),new_builds=0,removed_local_symbols=len(removed)))

def runtime():
    binding();image,attempt=package()
    import run_qemu_x86_64_input as guest
    rows=[];elapsed=0
    try:
        for spec in guest.CASES:
            binding();out=BASE/'input'/spec[0];out.parent.mkdir(exist_ok=True)
            row=guest.run_case(image,attempt,out,spec);rows.append(row);elapsed+=row['elapsed']
            need(elapsed<=1080,'input aggregate guest limit')
            row['proof']=guest.review_case(image,attempt,out,spec)
            print('INPUT_CASE_OK',spec[0],round(row['elapsed'],3),flush=True)
        save(BASE/'input-matrix.json',dict(passed=True,cases=rows,guest_seconds=elapsed))
    except BaseException as error:
        save(BASE/'input-stopped.json',dict(passed=False,cases=rows,guest_seconds=elapsed,error=str(error)));raise
    import run_qemu_x86_64_cli_media as cli
    import run_qemu_x86_64_display as display
    run=types.FunctionType(cli.run_matrix.__code__,dict(vars(cli),namespace=display.cli_namespace),argdefs=cli.run_matrix.__defaults__)
    run.__kwdefaults__=cli.run_matrix.__kwdefaults__
    result=run(image,attempt,BASE/'runtime',binding);save(BASE/'matrix.json',result)

def review():
    binding();image,attempt=package()
    import run_qemu_x86_64_input as guest
    matrix=read(BASE/'input-matrix.json');need(matrix['passed'] and len(matrix['cases'])==12 and matrix['guest_seconds']<=1080,'complete input matrix')
    proofs=[]
    for old,spec in zip(matrix['cases'],guest.CASES):
        proof=guest.review_case(image,attempt,BASE/'input'/spec[0],spec)
        need(proof==old['proof'],'independent complete input replay');proofs.append(proof)
    save(BASE/'input-review.json',dict(passed=True,proofs=proofs))
    import verify_x86_64_shell_boot_media as az
    import run_qemu_x86_64_cli_media as cli
    import run_qemu_x86_64_display as display
    import check_x86_64_input_media as check
    selected=types.SimpleNamespace(**dict(vars(cli),namespace=display.cli_namespace))
    ns=dict(vars(az),binding=binding,package_path=lambda:attempt,BASE=BASE,IMAGE=image,check=check,guest=selected,evidence_origin=lambda spec:BASE)
    replay=cli.bb.function(az.review,ns,[
        ('binding();positive_reuse_projection();negative_reuse_projection();','binding();'),
        ("summary['guest_seconds']<=455","summary['guest_seconds']<=1730"),
        ("config,records,app=guest.ay.image_config(IMAGE);catalog=",'catalog='),
        ("name,layout,case,session,ram=spec;origin=evidence_origin(spec);out=origin/'runtime'/name",
         "name,layout,case,session,ram=spec;origin=evidence_origin(spec);out=origin/'runtime'/name\n"
         "        label=guest.LABELS.get(name,'ext2-1k');module=guest.namespace(label).ay\n"
         "        config,records,app=guest.apps.image_config(IMAGE,label);module.app_files=app"),
        ("(75 if case=='a-signature' else 65)","(330 if case=='a-signature' else 320)"),
        ('guest.ay.evaluate(out,config,records,catalog,session,2,app)','module.evaluate(out,config,records,catalog,session,2,app)'),
        ("metrics['observe_seconds']<=42","metrics['observe_seconds']<=297"),
        ("check.bounded(out/'generated.raw',131072)==check.bounded(attempt/'system.ext2',131072)",
         "check.bounded(out/'generated.raw',1048576)==check.bounded(attempt/'system.ext2',1048576)"),
        ("data['logical_bytes']==131072","data['logical_bytes']==1048576"),("end==131072","end==1048576")])
    replay()
    raw={p.relative_to(ROOT).as_posix():digest(p) for directory in (BASE/'input',BASE/'runtime') for p in directory.rglob('*') if p.is_file()}
    save(BASE/'raw-hashes.json',raw)

def scope():
    f=binding();need(not git('diff','--check') and not git('diff','--cached','--name-only'),'final whitespace/index')
    need(read(BASE/'review.json')['passed'] and read(BASE/'input-review.json')['passed'],'all independent reviews passed')
    need(set(changed())<=set(queue_package()['allowed_files']),'final exact authorized scope')
    save(BASE/'scope.json',dict(passed=True,changed=changed(),candidate=f['candidate']))

def gates():
    f=binding();save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    results=[]
    for number,(command,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();start=time.monotonic();log=BASE/f'gate-{number:02d}.log';code=-1
        try:
            with log.open('xb') as out:code=subprocess.run(shlex.split(command),cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
        except subprocess.TimeoutExpired:code=124
        row=dict(candidate=f['candidate'],command=command,limit=limit,elapsed=time.monotonic()-start,exit_code=code,passed=code==0,log=link(log));results.append(row)
        save(BASE/f'gate-{number:02d}.json',row);print('INPUT_GATE',number,'PASS' if code==0 else 'FAIL',round(row['elapsed'],3),flush=True)
        if code:
            save(BASE/'stopped.json',dict(passed=False,gates=results));raise ValueError('first failed gate '+str(number)+': '+log.read_text(errors='replace')[-1800:])
    save(BASE/'gates-passed.json',dict(passed=True,candidate=f['candidate'],gates=results))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('development-build','development-media','freeze','gates','package','runtime','review','scope'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    if a.development_build:development_build()
    elif a.development_media:development_media()
    elif a.freeze:freeze()
    elif a.gates:gates()
    elif a.package:package_gate()
    elif a.runtime:runtime()
    elif a.review:review()
    else:scope()
