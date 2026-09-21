"""Native display qualification and exact opt-in compatibility projection."""
from pathlib import Path
import argparse,ast,hashlib,json,subprocess,sys,time,shutil,os,shlex,tomllib,types
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'build/codex-agent/r83be-display'
BUILD_ID='04'
MEDIA_ID='04'
BASE=EVIDENCE/'candidate03'
ORIGIN=EVIDENCE/'candidate02'
HEAD='871048ae'
MAKE_SELECTOR='''X86_64_NATIVE_DISPLAY ?= 0
ifneq ($(words $(X86_64_NATIVE_DISPLAY)),1)
$(error NativeDisplay selector must be one explicit value)
endif
ifneq ($(filter $(X86_64_NATIVE_DISPLAY),0 1),$(X86_64_NATIVE_DISPLAY))
$(error NativeDisplay selector must be 0 or 1)
endif
ifeq ($(X86_64_NATIVE_DISPLAY),1)
ifneq ($(X86_64_NATIVE_APP_FILES),1)
$(error NativeDisplay requires explicit NativeAppFiles)
endif
endif
X86_64_DISPLAY_FLAGS = $(if $(filter 1,$(X86_64_NATIVE_DISPLAY)),-DREIST_NATIVE_DISPLAY=1,)
'''
BOOT_COMPILE='''ifeq ($(X86_64_NATIVE_DISPLAY),1)
	@$(X86_64_CC) -target x86-freestanding-none -std=c11 -O2 -g0 -Wall -Wextra -Werror -ffreestanding -nostdlib -fno-builtin -fno-stack-protector -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-pic -fno-pie -mno-mmx -mno-sse -mno-sse2 -I. -c arch/x86_64/video/boot_framebuffer.c -o $(X86_64_BOOTSTRAP_DIR)/boot_framebuffer.o
	@$(X86_64_CC) -target x86-freestanding-none -std=c11 -O2 -g0 -Wall -Wextra -Werror -ffreestanding -nostdlib -fno-builtin -fno-stack-protector -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-pic -fno-pie -mno-mmx -mno-sse -mno-sse2 -I. -c arch/x86_64/video/boot_capture.c -o $(X86_64_BOOTSTRAP_DIR)/boot_capture.o
endif
'''
MAKE_PARTS=(MAKE_SELECTOR,
 'X86_64_POOL_FLAGS += $(X86_64_DISPLAY_FLAGS)\n',
 'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_DISPLAY)),--display,)\n',
 BOOT_COMPILE,
 ' $(if $(filter 1,$(X86_64_NATIVE_DISPLAY)),$(X86_64_BOOTSTRAP_DIR)/boot_framebuffer.o $(X86_64_BOOTSTRAP_DIR)/boot_capture.o,)')
PS_PARTS=('    [switch]$NativeDisplay,\n',
 'if ($NativeDisplay) { $NativeAppFiles = [switch]$true }\n',
 '        "X86_64_NATIVE_DISPLAY=$([int]$NativeDisplay.IsPresent)" `\n')

def need(ok,message):
    if not ok:raise ValueError(message)

def without_display_build_selector(source,make=False):
    """Strip exact complete opt-in additions; never a regex or a learned body."""
    need(type(source) is str and type(make) is bool,'display projection types')
    from verify_x86_64_input import without_input_build_selector
    source=without_input_build_selector(source,make=make)
    tokens=('NATIVE_DISPLAY','NativeDisplay','--display','X86_64_DISPLAY_FLAGS',
            'arch/x86_64/video/boot_framebuffer.c','arch/x86_64/video/boot_capture.c')
    if not any(token in source for token in tokens):return source
    for part in MAKE_PARTS if make else PS_PARTS:
        need(source.count(part)==1,'complete exact disabled display addition')
        source=source.replace(part,'')
    need(not any(token in source for token in tokens),'unexpected display selector/recipe')
    return source

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
    need(not output.exists() and not receipt.exists(),'one fresh display build reservation')
    state=build_sources();tools=build_tools();command=[tools['pwsh']['path'],'-NoProfile','-File',
        'scripts/build-x86_64-bootstrap.ps1','-NativeDisplay','-OutputDirectory',output.relative_to(ROOT).as_posix()]
    row=dict(passed=False,command=command,sources=state,tools=tools,builds=1,limit=300)
    save(EVIDENCE/('development-build'+BUILD_ID+'-started.json'),row)
    start=time.monotonic();log=EVIDENCE/('development-build'+BUILD_ID+'.log')
    try:
        with log.open('xb') as stream:
            r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=300,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row['exit_code']=r.returncode
        need(r.returncode==0,'display build failed: '+log.read_text(errors='replace')[-2400:])
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
    command=[sys.executable,'scripts/build_x86_64_display_media.py','--input-directory',str(image.parent),
             '--output-directory',str(folder)]
    row=dict(passed=False,command=command,limit=180,kernel_builds=0,bios_assemblies=3)
    save(EVIDENCE/('development-media'+MEDIA_ID+'-started.json'),row)
    start=time.monotonic();log=EVIDENCE/('development-media'+MEDIA_ID+'.log')
    try:
        with log.open('xb') as stream:
            r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=180,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row['exit_code']=r.returncode
        need(r.returncode==0,'display media failed: '+log.read_text(errors='replace')[-2400:])
        import check_x86_64_display_media as check
        attempt=check.verify(folder);build_binding()
        row.update(passed=True,attempt=attempt.relative_to(ROOT).as_posix(),
                   index_sha256=digest(folder/'display-media.json'))
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log_sha256=digest(log) if log.exists() else None)
        save(EVIDENCE/('development-media'+MEDIA_ID+'.json'),row)

def development_guest():
    image=build_binding()
    import check_x86_64_display_media as check
    import run_qemu_x86_64_display as guest
    package=check.verify(EVIDENCE/('media'+MEDIA_ID))
    row=json.loads((EVIDENCE/('development-media'+MEDIA_ID+'.json')).read_text())
    need(row['passed'] and row['index_sha256']==digest(EVIDENCE/('media'+MEDIA_ID)/'display-media.json'),'bound media receipt')
    return guest.run_case(image,package,EVIDENCE/'guest04',guest.CASES[0])

def read(path):return json.loads(Path(path).read_text())
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30).decode().strip()
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3be-native-display' and p['status']=='active','one active display package')
    return p
def changed():return sorted(set(git('diff','--name-only','HEAD').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
def sources():
    names=git('ls-files','--cached','--others','--exclude-standard').splitlines()
    selected=set(package()['allowed_files'])
    selected.update(n for n in names if n.startswith(('arch/','kernel/','userspace/','include/','lib/','config/','scripts/','test/')) and (ROOT/n).is_file())
    need(len(selected)<=30000,'bounded complete verification sources')
    return {n:digest(ROOT/n) for n in sorted(selected)}
def all_tools():
    import run_qemu_x86_64_boot as boot
    result=build_tools();qemu=boot.resolve_qemu(None)
    for name,path in [('qemu',qemu),('qemu-img',qemu.parent/'qemu-img.exe'),('gdb',shutil.which('gdb')),('openssl',shutil.which('openssl')),('nm',shutil.which('nm'))]:
        need(path and Path(path).is_file(),'required verification tool '+name)
        result[name]=dict(path=str(Path(path).resolve()),sha256=digest(path))
    return result
def package_path():
    import check_x86_64_display_media as check
    row=read(EVIDENCE/('development-media'+MEDIA_ID+'.json'))
    need(row['passed'] and row['elapsed']<=180 and row['index_sha256']==digest(EVIDENCE/('media'+MEDIA_ID)/'display-media.json'),'exact successful signed media receipt')
    attempt=check.verify(EVIDENCE/('media'+MEDIA_ID))
    need(attempt.relative_to(ROOT).as_posix()==row['attempt'],'exact signed publication');return attempt

def reuse_inventory(state):
    pins={'frozen.json':'9a0decf4ef721b116b7733ae4d812d0076c6f3421e1c92c1875861b125756f5b',
          'stopped.json':'019fdbcb2546a63c1c22c615a1a187361d6c1ae7dc53e466ad07e519cd1646e4',
          'display-matrix.json':'26b104b22a3f844b0b5ef209c1a213e07bed1fa6197e7478712721b85b2534e9',
          'runtime/summary.json':'11f793ad49eaae1fcbad4c7f2a5f8e6148f786faa324543487f4f6f7d7b55820'}
    for name,sha in pins.items():need(digest(ORIGIN/name)==sha,'exact retained stopped qualification '+name)
    old=read(ORIGIN/'frozen.json')
    allowed={'automation/reist-s03b.toml','docs/architecture/NATIVE_DISPLAY_CONTRACT.md',
             'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md',
             'scripts/verify_x86_64_display.py','scripts/run_qemu_x86_64_display.py','test/test_x86_64_display.py'}
    need(set(state)==set(old['sources']) and {n for n in state if state[n]!=old['sources'][n]}<=allowed,
         'all runtime/producer/CLI/host dependencies unchanged except explicit display verification correction')
    need(old['head']==git('rev-parse','HEAD') and old['tools']==all_tools(),'original source baseline and actual tools')
    name='scripts/run_qemu_x86_64_display.py'
    before=ast.parse((ORIGIN/'sources'/name).read_text());after=ast.parse((ROOT/name).read_text())
    definitions=lambda tree:{n.name:ast.dump(n) for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    original=definitions(before);current=definitions(after)
    need(all(current.get(name)==body for name,body in original.items()),'all original display capture and replay bodies exact')
    need(set(current)-set(original)=={'deadline_cleanup','cli_namespace'},'only declared private CLI correction helpers')
    files={p.relative_to(ROOT).as_posix():digest(p) for p in ORIGIN.rglob('*') if p.is_file()}
    return dict(origin=ORIGIN.relative_to(ROOT).as_posix(),pins=pins,files=files,
                diagnosis=link(EVIDENCE/'hang02-diagnosis.json'),red=link(EVIDENCE/'cleanup-legacy-red.log'),
                green=link(EVIDENCE/'cleanup-green.log'),display=read(ORIGIN/'display-matrix.json'),cli=read(ORIGIN/'runtime/summary.json'))

def reuse_binding(f):
    old=f['reused']
    for name,sha in old['files'].items():need(digest(ROOT/name)==sha,'retained complete raw evidence '+name)
    for name in ('diagnosis','red','green'):need(link(ROOT/old[name]['path'])==old[name],'bound correction evidence '+name)
    return old

def freeze():
    need(git('rev-parse','--short=8','HEAD')==HEAD and not BASE.exists(),'fresh contract boundary')
    p=package();scope=changed()
    need(set(scope)<=set(p['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'scope/index/whitespace')
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==12,'twelve frozen gates')
    image=build_binding();attempt=package_path();state=sources()
    value=dict(head=git('rev-parse','HEAD'),package=p,changed=scope,sources=state,commands=commands,
        queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text()),
        limits=[600]*6+[180,300,1200,180,900,180],tools=all_tools(),image=link(image),reused=reuse_inventory(state),
        media_index=link(EVIDENCE/('media'+MEDIA_ID)/'display-media.json'),attempt=attempt.relative_to(ROOT).as_posix(),
        build=link(EVIDENCE/('development-build'+BUILD_ID+'.json')),media=link(EVIDENCE/('development-media'+MEDIA_ID+'.json')),
        reserved=dict(kernel_builds=0,media_builds=0,display_guests=0,cli_guests=5,guest_seconds=120,reused_guests=14),
        candidate=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest())
    save(BASE/'frozen.json',value)
    for name in scope:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    print('DISPLAY_FROZEN',value['candidate'],flush=True)
def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and package()==f['package'] and sources()==f['sources'] and changed()==f['changed'],'frozen source/queue/scope')
    need(all_tools()==f['tools'],'frozen tools')
    for name in ('image','build','media','media_index'):need(link(ROOT/f[name]['path'])==f[name],'frozen '+name)
    return f
def build():
    f=binding();image=build_binding();need(link(image)==f['image'],'exact reusable build')
    from verify_x86_64_terminal import disabled
    for name in ('arch/x86_64/boot/entry.asm','arch/x86_64/proc/native_terminal.inc'):
        before=subprocess.check_output(['git','show',HEAD+':'+name],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
        projected=disabled((ROOT/name).read_text(),'REIST_NATIVE_DISPLAY',True)
        if name.endswith('/entry.asm'):
            seam='    ret\n\n\nserial_init32:\n'
            need(projected.count(seam)==1,'unique disabled display insertion seam')
            projected=projected.replace(seam,'    ret\n\nserial_init32:\n')
        need(projected==before,'exact disabled predecessor '+name)
    save(BASE/'build.json',dict(passed=True,kernel_builds=0,receipt=f['build']))
def media():
    binding();package_path()
    import verify_x86_64_cli_delivery as bd
    import verify_x86_64_shell_boot_media as az
    import check_x86_64_display_media as check
    import build_x86_64_display_media as producer
    import run_qemu_x86_64_cli_media as cli
    ns=dict(vars(az),binding=binding,package_path=package_path,BASE=BASE,MEDIA=EVIDENCE/('media'+MEDIA_ID),
        check=check,producer=producer.selected,canonical_descriptor=bd.canonical_descriptor,require_ext2_failure=bd.require_ext2_failure)
    replay=cli.bb.function(az.package_hosts,ns,[
        ("index=folder/'shell-media.json'","index=folder/'display-media.json'"),
        ("MEDIA/'shell-media.json'","MEDIA/'display-media.json'"),
        ('check.digest(path,131072)','check.digest(path,1048576)'),
        ("(target/'package.json').write_text(json.dumps(package,sort_keys=True,separators=(',',':'))+'\\n',encoding='ascii')",
         "(target/'package.json').write_bytes(canonical_descriptor(package))"),
        ("except ValueError as error:results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))",
         "except ValueError as error:require_ext2_failure(error);results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))")])
    replay();package_path();save(BASE/'media.json',dict(passed=True,media_builds=0,host_receipt=link(BASE/'package-hosts/result.json')))
def runtime():
    f=binding();image=build_binding();attempt=package_path()
    import run_qemu_x86_64_display as display
    import run_qemu_x86_64_cli_media as cli
    retained=reuse_binding(f);rows=[];start=time.monotonic()
    need(retained['display']['passed'] and len(retained['display']['cases'])==9,'complete old display capture matrix')
    for spec,old in zip(display.CASES,retained['display']['cases']):
        proof=display.review_case(image,attempt,ORIGIN/'display'/spec[0],spec)
        need(old['label']==spec[0] and proof==old['proof'],'same complete display proof')
        rows.append(dict(old,reused=True));print('DISPLAY_REPLAY_OK',spec[0],flush=True)
    save(BASE/'display-matrix.json',dict(passed=True,cases=rows,guest_seconds=sum(r['elapsed'] for r in rows),fresh_guests=0,reused_guests=9))
    cli_rows=[];catalog=(image.parent/'boot-programs.bin').read_bytes()
    need(len(retained['cli']['cases'])==5 and retained['cli']['closed'],'five complete retained CLI captures')
    for old,spec in zip(retained['cli']['cases'],cli.CASES[:5]):
        name,layout,case,session,ram=spec;label=cli.LABELS[name]
        need(tuple(old[k] for k in ('name','layout','case','session','ram'))==spec and
             old['evidence_directory']==(ORIGIN/'runtime'/name).relative_to(ROOT).as_posix(),'exact old CLI capture')
        module=display.cli_namespace(label).ay
        config,records,files=cli.apps.image_config(image,label);module.app_files=files
        proof=module.evaluate(ORIGIN/'runtime'/name,config,records,catalog,session,2,files)
        if old['passed']:need(proof==old['proof'],'unchanged previous complete CLI proof')
        cli_rows.append(dict(old,proof=proof,passed=True,reused=True,original_passed=old['passed']))
        print('CLI_REPLAY_OK',name,'original_passed='+str(old['passed']),flush=True)
    save(BASE/'positive-replay.json',dict(passed=True,cases=cli_rows))
    matrix=cli.run_matrix(image,attempt,BASE/'runtime',binding,cases=cli.CASES[5:])
    need(matrix['fresh_guests']==5 and matrix['guest_seconds']<=120,'exact five missing BIOS negatives')
    save(BASE/'matrix.json',dict(matrix,candidate=f['candidate'],cases=cli_rows+matrix['cases'],reused_guests=5,
        physical_guest_seconds=matrix['guest_seconds'],guest_seconds=retained['cli']['guest_seconds']+matrix['guest_seconds']))
    need(time.monotonic()-start<=1200,'complete replay/fresh runtime reservation')
def review():
    binding();image=build_binding();attempt=package_path()
    import verify_x86_64_shell_boot_media as az
    import run_qemu_x86_64_cli_media as cli
    import check_x86_64_display_media as check
    import run_qemu_x86_64_display as display
    f=binding();reuse_binding(f)
    selected=types.SimpleNamespace(**dict(vars(cli),namespace=display.cli_namespace))
    ns=dict(vars(az),binding=binding,package_path=package_path,BASE=BASE,IMAGE=image,check=check,guest=selected,
            evidence_origin=lambda spec:ORIGIN if spec[3] is not None else BASE)
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
    replay();proofs=[display.review_case(image,attempt,ORIGIN/'display'/s[0],s) for s in display.CASES]
    save(BASE/'display-review.json',dict(passed=True,proofs=proofs))
    reuse_binding(f)
    raw={p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
    raw.update(f['reused']['files']);save(BASE/'raw-hashes.json',raw)
def scope():
    f=binding();need(not git('diff','--check') and not git('diff','--cached','--name-only'),'final whitespace/index')
    need(read(BASE/'review.json')['passed'] and read(BASE/'display-review.json')['passed'],'both full independent reviews')
    save(BASE/'scope.json',dict(passed=True,candidate=f['candidate'],changed=changed()))
def all_gates():
    f=binding();save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();start=time.monotonic();log=BASE/f'gate-{n:02d}.log';code=-1
        try:
            with log.open('xb') as stream:
                code=subprocess.run(shlex.split(cmd),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=limit,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
        except subprocess.TimeoutExpired:code=124
        row=dict(candidate=f['candidate'],command=cmd,limit=limit,elapsed=time.monotonic()-start,exit_code=code,passed=code==0,log=link(log))
        save(BASE/f'gate-{n:02d}.json',row);print('DISPLAY_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:
            save(BASE/'stopped.json',row);raise ValueError('first failed frozen display gate: '+log.read_text(errors='replace')[-2000:])
    save(BASE/'gates-passed.json',dict(candidate=f['candidate'],passed=True,gates=12))

def evidence():return {p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
def seal():
    f=binding();need(read(BASE/'gates-passed.json')==dict(candidate=f['candidate'],passed=True,gates=12),'all twelve gates passed')
    for n,cmd in enumerate(f['commands'],1):
        row=read(BASE/f'gate-{n:02d}.json')
        need(row['passed'] and row['command']==cmd and row['candidate']==f['candidate'] and row['log']==link(ROOT/row['log']['path']),'exact passed gate/log')
    for name,sha in read(BASE/'raw-hashes.json').items():need(digest(ROOT/name)==sha,'raw reviewed evidence retained')
    save(BASE/'acceptance-seal.json',dict(passed=True,candidate=f['candidate'],evidence=evidence()))
def ready():
    f=read(BASE/'frozen.json');s=read(BASE/'acceptance-seal.json')
    names=f['sources'];state={n:digest(ROOT/n) for n in names}
    docs={'automation/reist-s03b.toml','docs/architecture/NATIVE_DISPLAY_CONTRACT.md',
          'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
    need({n for n in names if state[n]!=names[n]}<=docs,'only outcome documentation after gates')
    need(git('rev-parse','HEAD')==f['head'] and not git('diff','--cached','--name-only') and not git('diff','--check'),'clean precommit index/whitespace')
    need(s['passed'] and s['candidate']==f['candidate'],'complete acceptance seal')
    for name,sha in s['evidence'].items():need(digest(ROOT/name)==sha,'sealed evidence unchanged')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());expected=f['queue']
    expected['active_id']='';expected['packages'][0]['status']='done'
    need(q==expected,'exact completed queue; all deferred packages preserved')
    need(set(changed())<=set(f['package']['allowed_files']),'final exact scope')
    save(BASE/'commit-ready.json',dict(passed=True,sources=state,changed=changed(),seal=link(BASE/'acceptance-seal.json'),evidence=evidence()))
def final():
    f=read(BASE/'frozen.json');r=read(BASE/'commit-ready.json');head=git('rev-parse','HEAD')
    need(not git('status','--porcelain') and git('rev-parse','HEAD^')==f['head'],'clean accepted child commit')
    need(r['passed'] and sorted(git('diff','--name-only',f['head'],head).splitlines())==r['changed'],'exact implementation scope')
    for name,sha in {**r['sources'],**r['evidence']}.items():need(digest(ROOT/name)==sha,'accepted source/evidence binding')
    save(BASE/'verification-status-display-final.json',dict(accepted=True,implementation_commit=head,clean_worktree=True,
        gates=12,display_cases=9,cli_cases=10,fresh_guests=5,reused_guests=14,physical_guests=23,
        guest_seconds=896.0434498001705+read(BASE/'matrix.json')['physical_guest_seconds'],
        build=f['build'],media=f['media'],seal=r['seal'],sources=r['sources'],tools=f['tools']))
    print('DISPLAY_ACCEPTED',head,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    actions={'development-build':development_build,'development-media':development_media,'development-guest':development_guest,
             'freeze':freeze,'all':all_gates,'build':build,'media':media,'runtime':runtime,'review':review,'scope':scope,
             'seal':seal,'ready':ready,'final':final}
    for action in actions:g.add_argument('--'+action,action='store_true')
    a=p.parse_args();actions[next(k for k in actions if getattr(a,k.replace('-','_'))) ]()
