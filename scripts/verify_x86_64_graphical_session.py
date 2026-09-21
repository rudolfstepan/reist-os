"""Native graphical-session scope and immutable qualification boundary."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys,tomllib,time,shutil,argparse,shlex,types
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'build/codex-agent/r83bi-graphical-session'
HEAD='6f0a9275'
PACKAGE='R8.3bi-graphical-session'
BUILD_ID='07'
MEDIA_ID='07'
BASE=EVIDENCE/'candidate07'
def need(ok,message):
    if not ok:raise ValueError(message)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def original(name):return subprocess.check_output(['git','show',HEAD+':'+name],cwd=ROOT,timeout=30).decode('utf-8').replace('\r\n','\n')

def python_disabled(source):
    """Specialize only the new explicit False selector; compare full old AST."""
    validation='    if type(graphical_session) is not bool or graphical_session and not terminal_service:raise ValueError("graphical session requires terminal service profile")\n'
    need(source.count(validation)==1,'one exact graphical selector admission')
    source=source.replace(validation,'')
    class Disabled(ast.NodeTransformer):
        def visit_Name(self,n):return ast.Constant(False) if n.id=='graphical_session' else n
        def visit_UnaryOp(self,n):
            n=self.generic_visit(n)
            return ast.Constant(not n.operand.value) if isinstance(n.op,ast.Not) and isinstance(n.operand,ast.Constant) and type(n.operand.value) is bool else n
        def visit_BoolOp(self,n):
            n=self.generic_visit(n);values=[]
            for v in n.values:
                if isinstance(v,ast.Constant) and type(v.value) is bool:
                    if isinstance(n.op,ast.And) and not v.value:return v
                    if isinstance(n.op,ast.Or) and v.value:return v
                else:values.append(v)
            return values[0] if len(values)==1 else ast.BoolOp(n.op,values) if values else ast.Constant(isinstance(n.op,ast.And))
        def visit_If(self,n):
            n=self.generic_visit(n)
            if isinstance(n.test,ast.Constant) and type(n.test.value) is bool:return n.body if n.test.value else n.orelse
            return n
        def visit_FunctionDef(self,n):
            if n.name=='build':
                need(n.args.args[-1].arg=='graphical_session' and isinstance(n.args.defaults[-1],ast.Constant) and n.args.defaults[-1].value is False,'explicit False default')
                n.args.args.pop();n.args.defaults.pop()
            return self.generic_visit(n)
        def visit_Expr(self,n):
            c=n.value
            if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='add_argument' and c.args and isinstance(c.args[0],ast.Constant) and c.args[0].value=='--graphical-session':return None
            return self.generic_visit(n)
        def visit_Call(self,n):
            if isinstance(n.func,ast.Name) and n.func.id=='build' and n.args and isinstance(n.args[-1],ast.Attribute) and n.args[-1].attr=='graphical_session':n.args.pop()
            return self.generic_visit(n)
    return ast.dump(Disabled().visit(ast.parse(source)),include_attributes=False)

def default_projection():
    from verify_x86_64_service_console import disabled
    from build_x86_64_graphical_programs import without_graphical_build_selector
    for name in ('userspace/sdk/lib/x86_64/shell_session.c','userspace/sdk/lib/x86_64/shell_input.inc'):
        source=disabled((ROOT/name).read_text(encoding='utf-8'),'REIST_NATIVE_GRAPHICAL_SESSION',False)
        need(source==original(name),'exact graphical-disabled source '+name)
    for name in ('Makefile','scripts/build-x86_64-bootstrap.ps1'):
        need(without_graphical_build_selector((ROOT/name).read_text(encoding='utf-8'),name=='Makefile')==original(name),
            'exact graphical-disabled build '+name)
    name='scripts/build_x86_64_boot_programs.py'
    need(python_disabled((ROOT/name).read_text(encoding='utf-8'))==ast.dump(ast.parse(original(name)),include_attributes=False),
        'complete old boot-program builder AST when graphical selector is False')
    return True

def scope():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    active=[p for p in q['packages'] if p['status']=='active']
    need(q['active_id']==PACKAGE and len(active)==1 and active[0]['id']==PACKAGE,'one active GUI package')
    changed=subprocess.check_output(['git','diff','--name-only',HEAD],cwd=ROOT,timeout=30).decode().splitlines()
    changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,timeout=30).decode().splitlines()
    need(set(changed)<=set(active[0]['allowed_files']),'frozen graphical source scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,timeout=30,check=True)
    return sorted(set(changed))

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,sort_keys=True)

def build_sources():
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,timeout=30).decode().splitlines()
    need(len(names)<=30000,'bounded build inventory')
    # Includes all possible compilation headers and the build-helper closure.
    scripts={'scripts/build-x86_64-bootstrap.ps1','scripts/build_x86_64_boot_programs.py',
        'scripts/build_x86_64_graphical_programs.py','scripts/build_x86_64_app_files.py',
        'scripts/build_x86_64_app_files_media.py','scripts/check_x86_64_app_files_media.py',
        'scripts/build_x86_64_fs_media.py','scripts/build_x86_64_c_payload.py',
        'scripts/generate_syscall_abi.py','scripts/build_user_sdk.py','scripts/build_user_program.py',
        'scripts/build_user_math.py','scripts/build_user_text.py','scripts/build_user_js.py'}
    names={n for n in names if n=='Makefile' or n.startswith(('arch/','kernel/','userspace/','include/','lib/','config/')) or n in scripts}
    names|={'assets/fonts/reist-vga.psf','third_party/mbedtls-4.1.1.tar.bz2'}
    need(scripts<=names,'complete named native helper closure')
    return {n:digest(ROOT/n) for n in sorted(names)}

def build_tools():
    from verify_x86_64_terminal_service import build_tools as previous
    values=previous();openssl=shutil.which('openssl');need(openssl,'OpenSSL tool present')
    values['openssl']={'path':str(Path(openssl).resolve()),'sha256':digest(openssl)}
    return values

def development_build():
    scope();default_projection()
    folder=EVIDENCE/('build'+BUILD_ID);receipt=EVIDENCE/('development-build'+BUILD_ID+'.json')
    need(not folder.exists() and not receipt.exists(),'fresh reserved kernel build')
    sources=build_sources();tools=build_tools()
    command=[tools['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeGraphicalSession','-OutputDirectory',folder.relative_to(ROOT).as_posix()]
    row=dict(passed=False,command=command,sources=sources,tools=tools,builds=1,limit=300)
    save(EVIDENCE/('development-build'+BUILD_ID+'-started.json'),row)
    start=time.monotonic();log=EVIDENCE/('development-build'+BUILD_ID+'.log')
    try:
        with log.open('xb') as out:
            result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=300,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row['exit_code']=result.returncode
        need(result.returncode==0,'graphical build: '+log.read_text(errors='replace')[-2800:])
        need(build_sources()==sources and build_tools()==tools,'unchanged build sources/tools')
        paths=[p for p in folder.rglob('*') if p.is_file() and not any('cache' in a for a in p.parts)
               and p.suffix in ('.elf','.prg','.bin','.o','.json','.inc','.map')]
        need(len(paths)<2048,'bounded build artifacts')
        row['artifacts']={p.relative_to(ROOT).as_posix():digest(p) for p in paths};row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log={'path':log.relative_to(ROOT).as_posix(),'sha256':digest(log)} if log.exists() else None)
        save(receipt,row)
    return row

def build_binding():
    row=json.loads((EVIDENCE/('development-build'+BUILD_ID+'.json')).read_text(encoding='utf-8'))
    need(row['passed'] and row['builds']==1 and row['elapsed']<=300,'successful bounded GUI build')
    need(row['sources']==build_sources() and row['tools']==build_tools(),'exact build sources/tools')
    for name,sha in row['artifacts'].items():need(digest(ROOT/name)==sha,'exact artifact '+name)
    need(digest(ROOT/row['log']['path'])==row['log']['sha256'],'exact original build log')
    return EVIDENCE/('build'+BUILD_ID)/'x86_64/reist-x86_64-bootstrap.elf'

def media_sources():
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','scripts','arch/x86/boot/bios'],cwd=ROOT,timeout=30).decode().splitlines()
    exclude={'scripts/verify_x86_64_graphical_session.py','scripts/run_qemu_x86_64_graphical_session.py'}
    names={n for n in names if n.endswith(('.py','.asm','.inc')) and n not in exclude}
    names.add('safety/boot_trust_policy.json')
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'test/fixtures').glob('*.pem'))
    return {n:digest(ROOT/n) for n in sorted(names)}

def development_media():
    from check_x86_64_graphical_media import verify
    image=build_binding();folder=EVIDENCE/('media'+MEDIA_ID);receipt=EVIDENCE/('development-media'+MEDIA_ID+'.json')
    need(not folder.exists() and not receipt.exists(),'fresh reserved graphical media')
    tools=build_tools();sources=media_sources()
    command=[sys.executable,'scripts/build_x86_64_graphical_media.py','--input-directory',str(image.parent),
        '--output-directory',str(folder),'--nasm',tools['nasm']['path'],'--openssl',tools['openssl']['path']]
    row=dict(passed=False,command=command,sources=sources,tools=tools,media=1,bios_assemblies=3,limit=180)
    save(EVIDENCE/('development-media'+MEDIA_ID+'-started.json'),row)
    start=time.monotonic();log=EVIDENCE/('development-media'+MEDIA_ID+'.log')
    try:
        with log.open('xb') as out:
            result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=180,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row['exit_code']=result.returncode
        need(result.returncode==0,'graphical media: '+log.read_text(errors='replace')[-2600:])
        need(sources==media_sources() and tools==build_tools(),'unchanged media inputs/tools')
        row['package']=str(verify(folder));row['index_sha256']=digest(folder/'graphical-media.json');row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log={'path':log.relative_to(ROOT).as_posix(),'sha256':digest(log)} if log.exists() else None)
        save(receipt,row)
    return row



def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30).decode().strip()

def changed():
    return sorted(set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))

def queue_package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    active=[p for p in q['packages'] if p['status']=='active']
    need(len(active)==1 and active[0]['id']==q['active_id']=='R8.3bi-graphical-session','one exact active package')
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
    need(len(commands)==8,'unchanged eight acceptance gates')
    value=dict(candidate=BASE.name,head=git('rev-parse','HEAD'),package=p,changed=paths,sources=sources(),tools=all_tools(),
               commands=commands,limits=[600]*3+[180,5400,180,900,180],image=link(image),
               build=link(EVIDENCE/('development-build'+BUILD_ID+'.json')),
               media=link(EVIDENCE/('development-media'+MEDIA_ID+'.json')),
               media_index=link(EVIDENCE/('media'+MEDIA_ID)/'graphical-media.json'),attempt=attempt.relative_to(ROOT).as_posix(),
               reserved=dict(kernel_builds=0,media_builds=0,graphical_guests=18,graphical_seconds=3240,cli_guests=10,cli_seconds=1730))
    save(BASE/'frozen.json',value)
    for name in paths:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    print('GRAPHICAL_FROZEN',BASE.name,flush=True)

def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and queue_package()==f['package'] and changed()==f['changed'] and sources()==f['sources'],'frozen source/queue/scope')
    need(all_tools()==f['tools'],'unchanged qualification tools')
    for key in ('image','build','media','media_index'):need(link(ROOT/f[key]['path'])==f[key],'unchanged '+key)
    return f

def package_gate():
    binding();image,attempt=package()
    raw=image.with_suffix('.untrimmed.elf').read_bytes();compact=image.read_bytes()
    import build_x86_64_c_payload as elf
    a=elf.elf(raw,32);b=elf.elf(compact,32)
    need(a['programs']==b['programs'] and a['entry']==b['entry'],'compacted outer load topology')
    for part in a['programs']:
        begin=part['offset'];end=begin+part['filesz'];need(raw[begin:end]==compact[begin:end],'all loaded bytes retained')
    removed={n for n,v in a['symbols'].items() if n.startswith(('native_input_','native_terminal_')) and '.' in n and v['binding']==0}
    need(1<=len(removed)<=128 and b['symbols']=={n:v for n,v in a['symbols'].items() if n not in removed},'only input local debug names removed')
    save(BASE/'package.json',dict(passed=True,image=link(image),attempt=str(attempt),new_builds=0,removed_local_symbols=len(removed)))

def gates():
    f=binding();save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    results=[]
    for number,(command,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();start=time.monotonic();log=BASE/f'gate-{number:02d}.log';code=-1
        try:
            with log.open('xb') as out:code=subprocess.run(shlex.split(command),cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
        except subprocess.TimeoutExpired:code=124
        row=dict(candidate=f['candidate'],command=command,limit=limit,elapsed=time.monotonic()-start,exit_code=code,passed=code==0,log=link(log));results.append(row)
        save(BASE/f'gate-{number:02d}.json',row);print('GRAPHICAL_GATE',number,'PASS' if code==0 else 'FAIL',round(row['elapsed'],3),flush=True)
        if code:
            save(BASE/'stopped.json',dict(passed=False,gates=results));raise ValueError('first failed gate '+str(number)+': '+log.read_text(errors='replace')[-1800:])
    save(BASE/'gates-passed.json',dict(passed=True,candidate=f['candidate'],gates=results))

def package():
    import check_x86_64_graphical_media as check
    default_projection();image=build_binding();media=EVIDENCE/('media'+MEDIA_ID)
    row=read(EVIDENCE/('development-media'+MEDIA_ID+'.json'))
    need(row['passed'] and row['sources']==media_sources() and row['tools']==build_tools() and
         row['index_sha256']==digest(media/'graphical-media.json'),'exact immutable graphical media')
    return image,check.verify(media)

def cli_files(package,files):
    """The inherited five-file CLI regression fixture uses exact packaged tools.

    The nine-file public GUI volume is independently admitted by package().
    Keep original CLI directory/EOF expectations and binary safety oracles.
    """
    import run_qemu_x86_64_cli_media as cli
    need(set(files)==set(cli.apps.media.NAMES),'exact inherited five-file CLI fixture')
    for name,raw in files.items():
        path=package/('file-program.prg' if name=='boot.prg' else name)
        need(path.read_bytes()==raw,'CLI fixture retains exact packaged '+name)
    return cli.apps.media.image('ext2-1k',files)

def cli_runner():
    import run_qemu_x86_64_cli_media as cli
    import run_qemu_x86_64_terminal_service as prior
    return cli.bb.function(cli.run_matrix,dict(vars(cli),namespace=prior.cli_namespace,cli_files=cli_files),[
        ("check.need(apps.media.image('ext2-1k',files)==check.bounded(package/'system.ext2',1048576),'actual published CLI volume')",
         "cli_files(package,files)")])

def runtime():
    binding();image,attempt=package()
    import run_qemu_x86_64_graphical_session as guest
    rows=[];elapsed=0
    try:
        for spec in guest.CASES:
            binding();out=BASE/'graphical'/spec[0]
            row=guest.run_case(image,attempt,out,spec);rows.append(row);elapsed+=row['elapsed']
            need(elapsed<=3240,'graphical aggregate guest reservation')
            row['proof']=guest.review_case(image,attempt,out,spec)
            print('GRAPHICAL_CASE_OK',spec[0],round(row['elapsed'],3),flush=True)
        save(BASE/'graphical-matrix.json',dict(passed=True,cases=rows,guest_seconds=elapsed))
    except BaseException as error:
        save(BASE/'graphical-stopped.json',dict(passed=False,cases=rows,guest_seconds=elapsed,error=str(error)));raise
    save(BASE/'matrix.json',cli_runner()(image,attempt,BASE/'runtime',binding))

def cli_reviewer(image,attempt):
    import verify_x86_64_shell_boot_media as az
    import run_qemu_x86_64_cli_media as cli
    import run_qemu_x86_64_terminal_service as prior
    import check_x86_64_graphical_media as check
    selected=types.SimpleNamespace(**dict(vars(cli),namespace=prior.cli_namespace))
    ns=dict(vars(az),binding=binding,package_path=lambda:attempt,BASE=BASE,IMAGE=image,
        check=check,guest=selected,evidence_origin=lambda spec:BASE,cli_files=cli_files)
    return cli.bb.function(az.review,ns,[
        ('binding();positive_reuse_projection();negative_reuse_projection();','binding();'),
        ("summary['guest_seconds']<=455","summary['guest_seconds']<=1730"),
        ("config,records,app=guest.ay.image_config(IMAGE);catalog=",'catalog='),
        ("name,layout,case,session,ram=spec;origin=evidence_origin(spec);out=origin/'runtime'/name",
         "name,layout,case,session,ram=spec;origin=evidence_origin(spec);out=origin/'runtime'/name\n"
         "        label=guest.LABELS.get(name,'ext2-1k');module=guest.namespace(label).ay\n"
         "        config,records,app=guest.apps.image_config(IMAGE,label);module.app_files=app\n"
         "        need(check.bounded(out/'generated.raw',1048576)==cli_files(attempt,app),'exact inherited CLI fixture')"),
        ("(75 if case=='a-signature' else 65)","(330 if case=='a-signature' else 320)"),
        ('guest.ay.evaluate(out,config,records,catalog,session,2,app)','module.evaluate(out,config,records,catalog,session,2,app)'),
        ("metrics['observe_seconds']<=42","metrics['observe_seconds']<=297"),
        ("check.bounded(out/'generated.raw',131072)==check.bounded(attempt/'system.ext2',131072)",
         "check.bounded(out/'generated.raw',1048576)==cli_files(attempt,app)"),
        ("data['logical_bytes']==131072","data['logical_bytes']==1048576"),("end==131072","end==1048576")])

def review():
    binding();image,attempt=package()
    import run_qemu_x86_64_graphical_session as guest
    matrix=read(BASE/'graphical-matrix.json')
    need(matrix['passed'] and len(matrix['cases'])==18 and matrix['guest_seconds']<=3240,'complete graphical matrix')
    proofs=[]
    for old,spec in zip(matrix['cases'],guest.CASES):
        proof=guest.review_case(image,attempt,BASE/'graphical'/spec[0],spec)
        need(proof==old['proof'],'complete independent graphical replay');proofs.append(proof)
    save(BASE/'graphical-review.json',dict(passed=True,proofs=proofs))
    cli_reviewer(image,attempt)()
    raw={p.relative_to(ROOT).as_posix():digest(p) for directory in (BASE/'graphical',BASE/'runtime')
        for p in directory.rglob('*') if p.is_file()}
    save(BASE/'raw-hashes.json',raw)

def scope_gate():
    f=binding();paths=scope()
    need(not git('diff','--cached','--name-only'),'final clean index')
    need(read(BASE/'review.json')['passed'] and read(BASE/'graphical-review.json')['passed'],'all independent reviews passed')
    save(BASE/'scope.json',dict(passed=True,changed=paths,candidate=f['candidate']))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for option in ('development-build','development-media','freeze','gates','package','runtime','review','scope'):g.add_argument('--'+option,action='store_true')
    a=p.parse_args()
    if a.development_build:print('GRAPHICAL_BUILD_OK',development_build()['elapsed'])
    elif a.development_media:print('GRAPHICAL_MEDIA_OK',development_media()['elapsed'])
    elif a.freeze:freeze()
    elif a.gates:gates()
    elif a.package:package_gate()
    elif a.runtime:runtime()
    elif a.review:review()
    elif a.scope:scope_gate()
