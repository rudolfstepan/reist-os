"""One frozen native64 CLI delivery transaction, full evidence before acceptance."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,ast,hashlib,inspect,json,shlex,subprocess,time,tomllib,types
import check_x86_64_cli_media as check
import build_x86_64_cli_media as producer
import run_qemu_x86_64_cli_media as guest
import run_x86_64_cli as launcher
import verify_x86_64_shell_boot_media as az
import verify_x86_64_wide_shell_media as bb
ROOT=check.ROOT
BASE=ROOT/'build/codex-agent/r83bd-cli-delivery/candidate02'
ORIGIN=BASE.parent/'candidate01'
MEDIA=ORIGIN/'media';IMAGE=check.INPUT/check.KERNEL
ORIGINAL_CANDIDATE='6744b90071ae9684d63bedd7e8ccd69a450e6308f60ce5464501750c9f2c7e95'
ORIGINAL_STOP='b69ecb7b565499bc60ebc0972e873f8357bdeca2145a8fc9f3b650b5d36a2d76'
ORIGINAL_BUILD='d85281c38fd80deeef44e454e3f6d52e0100be0ea636a87079c61f43a7c1a2a0'
HEAD='9617ed96';LIMITS=(300,300,180,180,300,2100,180,300,180)
PRIOR=ROOT/'build/codex-agent/r83bc-application-files/candidate08/verification-status-app-files-final.json'
PRIOR_SHA='b2efe4c60b7894b188084dbe09bf8d1aed24f84a765fb69ed2334f9072246326'
BB=ROOT/'build/codex-agent/r83bb-wide-shell-media/candidate02/verification-status-wide-shell-media-final.json'
BB_SHA='496442d7a594b347915ad28313474ab6bec2728e84d80e74bd33acd61d7ae4d4'
DOCS={'automation/reist-s03b.toml','docs/architecture/NATIVE_CLI_DELIVERY_CONTRACT.md',
      'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md','docs/NATIVE64_CLI_QUICKSTART.md'}
need=check.need
read=bb.read;save=bb.save;git=bb.git;changed=bb.changed;command=bb.command

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))

def hashes(paths):
    names=sorted(set(paths));need(len(names)<=100000,'bounded file hash inventory')
    with ThreadPoolExecutor(max_workers=8) as pool:return dict(zip(names,pool.map(lambda n:digest(ROOT/n),names)))

def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3bd-cli-delivery' and p['status']=='active','BD active package')
    return p

def sources():
    names=set(git('ls-files').splitlines())|set(read(BASE/'frozen.json')['package']['allowed_files'] if (BASE/'frozen.json').exists() else package()['allowed_files'])
    need(all((ROOT/n).is_file() for n in names),'complete tracked/candidate files')
    return hashes(names)

def retained():
    need(digest(PRIOR)==PRIOR_SHA and digest(BB)==BB_SHA,'exact accepted BC/BB receipts')
    prior=read(PRIOR);previous=read(BB)
    for receipt,commit in ((prior,'abe3cc7d7016671e5b644e01fb73976680f5ca0c'),
                           (previous,'813606cf7f6fcd6eb42fe8e8a38658f8ce2cf0e7')):
        need(receipt['accepted'] and receipt['clean_worktree'] and receipt['implementation_commit']==commit,'accepted predecessor boundary')
        for name in ('seal','commit_ready'):need(link(ROOT/receipt[name]['path'])==receipt[name],'retained predecessor '+name)
    allowed=set(package()['allowed_files']);state=hashes(prior['sources'])
    need(all(state[n]==sha for n,sha in prior['sources'].items() if n not in allowed),'unchanged BC implementation/dependencies')
    for name in ('scripts/build_x86_64_shell_media.py','scripts/check_x86_64_shell_media.py',
                 'scripts/run_qemu_x86_64_shell_boot_media.py','scripts/run_qemu_x86_64_wide_shell_media.py'):
        need(digest(ROOT/name)==previous['sources'][name],'unchanged accepted BIOS adapter '+name)
    need(hashes(prior['artifacts'])==prior['artifacts'],'exact accepted BC build/artifacts')
    for name,sha in prior['tools'].items():need(digest(name)==sha,'unchanged accepted tool '+name)
    producer.inputs(check.INPUT);return prior

def canonical_descriptor(value):return bb.canonical_descriptor(value)

def require_ext2_failure(error):
    need(isinstance(error,ValueError) and str(error).startswith('application media '),
         'signed malformed EXT2 must reach independent filesystem oracle')

def reused_evidence(state):
    need(digest(ORIGIN/'stopped.json')==ORIGINAL_STOP and digest(ORIGIN/'build-media.json')==ORIGINAL_BUILD,'preserved original stop and only media build')
    old=read(ORIGIN/'frozen.json');stop=read(ORIGIN/'stopped.json');matrix=read(ORIGIN/'runtime/summary.json')
    need(old['candidate']==stop['candidate']==ORIGINAL_CANDIDATE and stop['failed_gate']==6 and
         not matrix['passed'] and matrix['closed'] and len(matrix['cases'])==5 and
         [r['passed'] for r in matrix['cases']]==[True,True,True,True,False] and
         matrix['guest_seconds']==477.85895260004327,'five retained captures; original failed outcome remains failed')
    allowed=DOCS|{'scripts/run_qemu_x86_64_cli_media.py','scripts/verify_x86_64_cli_delivery.py','test/test_x86_64_cli_runtime.py'}
    need(set(state)==set(old['sources']) and {n for n in state if state[n]!=old['sources'][n]}<=allowed,'same complete source graph except declared proof/window correction')
    for path,sha in old['tools'].items():need(digest(path)==sha,'same original capture tool')
    return dict(candidate=ORIGINAL_CANDIDATE,matrix=matrix,
        files=hashes(p.relative_to(ROOT).as_posix() for p in ORIGIN.rglob('*') if p.is_file()),
        diagnosis=link(BASE.parent/'hang-diagnosis.json'),red_green=link(BASE.parent/'hang-host-result.json'))

def freeze():
    need(git('rev-parse','--short=8','HEAD')==HEAD and not BASE.exists(),'fresh clean BD contract boundary')
    p=package();need(set(changed())<=set(p['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'BD exact scope/index/whitespace')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    original=tomllib.loads(subprocess.check_output(['git','show',HEAD+':automation/reist-s03b.toml'],cwd=ROOT,timeout=30).decode())
    projected=json.loads(json.dumps(q));projected['packages'][0]['execution_window']=original['packages'][0]['execution_window']
    projected['packages'][0].pop('correction_evidence',None)
    need(projected==original,'only recorded administrative correction window, no queue/gate/safety transition')
    prior=retained();state=sources();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==9 and all((ROOT/n).is_file() for n in p['allowed_files']),'complete BD source/gate inventory')
    reuse=reused_evidence(state)
    value=dict(head=git('rev-parse','HEAD'),package=p,sources=state,changed=changed(),commands=commands,limits=LIMITS,reused=reuse,
        tools=prior['tools'],prior=link(PRIOR),bb=link(BB),artifacts=prior['artifacts'],
        reserved=dict(kernel_builds=0,program_builds=0,test_client_builds=0,media_builds=0,bios_assemblies=0,guests=5,guest_seconds=120),
        previous=dict(guests=5,guest_seconds=477.85895260004327,media_builds=1,kernel_builds=0),
        candidate=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest())
    save(BASE/'frozen.json',value)
    for name in changed():
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    print('BD_FROZEN',value['candidate'],flush=True)

def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and sources()==f['sources'] and package()==f['package'] and changed()==f['changed'],'exact frozen BD source/queue/scope')
    for path,sha in f['tools'].items():need(digest(path)==sha,'BD frozen tool '+path)
    need(link(PRIOR)==f['prior'] and link(BB)==f['bb'] and hashes(f['artifacts'])==f['artifacts'],'bound accepted inputs retained')
    need(link(BASE.parent/'hang-diagnosis.json')==f['reused']['diagnosis'] and
         link(BASE.parent/'hang-host-result.json')==f['reused']['red_green'],'bound cause and targeted regression')
    return f

def openssl():return next(p for p in read(PRIOR)['tools'] if Path(p).name.lower()=='openssl.exe')

def dependencies():
    f=binding();retained()
    for label in guest.LABELS.values():
        selected=guest.namespace(label);original=guest.apps.namespace(label)
        for name in ('validate_capture','validate_storage','validate_policy','validate_cpu','validate_identity',
                     'validate_terminal','validate_ipc_delivery','observer','evaluate','SessionFeeder'):
            need(ast.dump(ast.parse(inspect.getsource(getattr(selected.ay,name))))==
                 ast.dump(ast.parse(inspect.getsource(getattr(original,name)))),'exact BC safety predicate '+name)
        need(selected.ay.validate_objects is guest.apps.validate_objects,'complete unchanged BC object oracle')
    need(guest.CASES[5:]==guest.bios.CASES[5:],'unchanged complete BIOS negative matrix')
    save(BASE/'dependencies.json',dict(candidate=f['candidate'],passed=True))

def build_media():
    f=binding();need(not (BASE/'build-media.json').exists(),'one exact media reuse gate')
    need(digest(ORIGIN/'build-media.json')==ORIGINAL_BUILD,'only original media build receipt')
    old=read(ORIGIN/'build-media.json');started=time.monotonic()
    need(old['passed'] and old['media_builds']==1 and old['kernel_builds']==0 and old['index']==link(MEDIA/'cli-media.json'),'unchanged only published pair')
    attempt=check.verify(MEDIA,openssl=openssl());need(attempt.relative_to(ROOT).as_posix()==old['attempt'],'independent same media')
    save(BASE/'build-media.json',dict(old,candidate=f['candidate'],media_builds=0,bios_assemblies=0,
        reused_from=link(ORIGIN/'build-media.json'),elapsed=time.monotonic()-started))

def package_path():
    row=read(BASE/'build-media.json')
    need(row['passed'] and row['kernel_builds']==0 and row['media_builds']==0 and row['reused_from']==link(ORIGIN/'build-media.json') and row['directory']==MEDIA.relative_to(ROOT).as_posix() and
        row['index']==link(MEDIA/'cli-media.json'),'one unchanged published CLI pair')
    attempt=check.verify(MEDIA,openssl=openssl());need(attempt.relative_to(ROOT).as_posix()==row['attempt'],'same admitted attempt')
    return attempt

def package_hosts():
    binding();namespace=dict(vars(az),binding=binding,package_path=package_path,BASE=BASE,MEDIA=MEDIA,
        check=check,producer=producer,canonical_descriptor=canonical_descriptor,require_ext2_failure=require_ext2_failure,cli_openssl=openssl)
    replay=guest.bb.function(az.package_hosts,namespace,[
        ("index=folder/'shell-media.json'","index=folder/'cli-media.json'"),
        ("MEDIA/'shell-media.json'","MEDIA/'cli-media.json'"),
        ('check.digest(path,131072)','check.digest(path,1048576)'),
        ("(target/'package.json').write_text(json.dumps(package,sort_keys=True,separators=(',',':'))+'\\n',encoding='ascii')",
         "(target/'package.json').write_bytes(canonical_descriptor(package))"),
        ("shutil.which('openssl') or 'openssl'","cli_openssl()"),
        ("except ValueError as error:results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))",
         "except ValueError as error:require_ext2_failure(error);results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))")])
    # The historical function's default consumer resolves OpenSSL from PATH.
    # Bind the accepted executable locally without changing any shared module.
    namespace['check']=types_check=types.SimpleNamespace(**vars(check))
    types_check.verify=lambda directory,index=None:check.verify(directory,index,openssl())
    replay();folder=BASE/'package-hosts';attempt=package_path();target=folder/attempt.name
    index=folder/'cli-media.json';original=index.read_bytes();rows=[]
    def reject(case):
        try:check.verify(folder,openssl=openssl())
        except (ValueError,OSError,KeyError,TypeError) as error:rows.append(dict(case=case,rejected=True,error=str(error)[:256]))
        else:raise ValueError('invalid package admitted '+case)
    for name in check.FILES:
        path=target/name;size=path.stat().st_size
        with path.open('rb') as stream:stream.seek(size-1);tail=stream.read(1)
        with path.open('r+b') as stream:stream.truncate(size-1)
        try:reject('truncated-'+name)
        finally:
            with path.open('ab') as stream:stream.write(tail)
    envelope=read(index);envelope['package']['profile']='research-native-wide-shell-two-media-v1'
    index.write_bytes(canonical_descriptor(envelope))
    try:reject('foreign-profile')
    finally:index.write_bytes(original)
    candidate=folder/'shell-index-rejected.json';candidate.write_bytes(b'{}')
    before=digest(index)
    try:producer.publish(folder,candidate,openssl(),folder/'atomic-failure.log')
    except (ValueError,RuntimeError,subprocess.CalledProcessError):pass
    else:raise ValueError('invalid atomic publication passed')
    need(digest(index)==before and candidate.read_bytes()==b'{}','failed publication preserves previous index and candidate')
    rows.append(dict(case='atomic-failure',rejected=True))
    launcher.launch(MEDIA,check_only=True,openssl=openssl())
    row=command(['powershell','-NoProfile','-NonInteractive','-File','scripts/start-x86_64-cli.ps1',
        '-Directory',str(MEDIA),'-CheckOnly','-OpenSSL',openssl()],60,BASE/'launcher-check-only.log')
    need(row['passed'],'actual PowerShell to Python check-only integration')
    package_path();save(folder/'extra-result.json',dict(passed=True,results=rows,launcher=row))

def runtime():
    f=binding();attempt=package_path()
    need(reused_evidence(f['sources'])==f['reused'],'exact complete old sources/tools/raw before independent reuse')
    rows=[];catalog=(IMAGE.parent/'boot-programs.bin').read_bytes()
    for old,spec in zip(f['reused']['matrix']['cases'],guest.CASES[:5]):
        name,layout,case,session,ram=spec
        need(tuple(old[k] for k in ('name','layout','case','session','ram'))==spec and
            old['evidence_directory']==(ORIGIN/'runtime'/name).relative_to(ROOT).as_posix(),'exact old positive capture')
        label=guest.LABELS[name];module=guest.namespace(label).ay
        config,records,files=guest.apps.image_config(IMAGE,label);module.app_files=files
        proof=module.evaluate(ROOT/old['evidence_directory'],config,records,catalog,session,2,files)
        if old['passed']:need(proof==old['proof'],'unchanged complete prior positive proof')
        row=dict(old,proof=proof,passed=True,reused=True,original_passed=old['passed'],origin_candidate=ORIGINAL_CANDIDATE)
        rows.append(row);print('CLI_REPLAY_OK',name,'original_passed='+str(old['passed']),flush=True)
    save(BASE/'positive-replay.json',dict(candidate=f['candidate'],passed=True,cases=rows))
    summary=guest.run_matrix(IMAGE,attempt,BASE/'runtime',binding,cases=guest.CASES[5:])
    need(summary['passed'] and len(summary['cases'])==5 and summary['fresh_guests']==5 and summary['guest_seconds']<=120,'five remaining unchanged BIOS negatives')
    save(BASE/'matrix.json',dict(summary,candidate=f['candidate'],cases=rows+summary['cases'],fresh_guests=5,reused_guests=5,
        physical_guest_seconds=summary['guest_seconds'],previous_guests=5,previous_guest_seconds=f['previous']['guest_seconds'],
        guest_seconds=f['previous']['guest_seconds']+summary['guest_seconds']))

def review():
    ns=dict(vars(az),binding=binding,package_path=package_path,BASE=BASE,MEDIA=MEDIA,IMAGE=IMAGE,
        check=check,guest=guest,evidence_origin=lambda spec:ORIGIN if spec[3] is not None else BASE)
    replay=guest.bb.function(az.review,ns,[
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
        ("data['logical_bytes']==131072","data['logical_bytes']==1048576"),
        ("end==131072","end==1048576")])
    replay();f=binding();need(reused_evidence(f['sources'])==f['reused'],'complete original archive unchanged after review')
    raw=hashes(p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file())
    raw.update(f['reused']['files']);save(BASE/'raw-hashes.json',raw)

def scope():
    f=binding();retained();need(not git('diff','--check') and not git('diff','--cached','--name-only'),'BD scope/index')
    need(read(BASE/'review.json')['passed'] and read(BASE/'package-hosts/extra-result.json')['passed'],'full review/package proof before scope')
    save(BASE/'scope.json',dict(candidate=f['candidate'],passed=True,changed=changed()))

def all_gates():
    f=binding();need(not (BASE/'started.json').exists(),'BD single frozen execution')
    save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();row=command(shlex.split(cmd),limit,BASE/f'gate-{n:02d}.log')
        row.update(candidate=f['candidate'],gate=n);save(BASE/f'gate-{n:02d}.json',row)
        print('BD_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:
            save(BASE/'stopped.json',dict(candidate=f['candidate'],failed_gate=n,receipt=row))
            raise ValueError('first failed BD gate; no subsequent execution')
    save(BASE/'gates-passed.json',dict(candidate=f['candidate'],passed=True,gates=9))

def evidence():return hashes(p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file())

def seal():
    f=binding();need(read(BASE/'gates-passed.json')==dict(candidate=f['candidate'],passed=True,gates=9),'all nine gates')
    for n,cmd in enumerate(f['commands'],1):
        r=read(BASE/f'gate-{n:02d}.json');need(r['passed'] and r['command']==shlex.split(cmd) and r['candidate']==f['candidate'] and
            r['log']==link(ROOT/r['log']['path']),'exact passed gate/log')
    need(hashes(read(BASE/'raw-hashes.json'))==read(BASE/'raw-hashes.json'),'complete raw review evidence unchanged')
    save(BASE/'acceptance-seal.json',dict(passed=True,candidate=f['candidate'],evidence=evidence(),frozen=link(BASE/'frozen.json')))

def ready():
    f=read(BASE/'frozen.json');s=read(BASE/'acceptance-seal.json');state=sources()
    need(git('rev-parse','HEAD')==f['head'] and not git('diff','--cached','--name-only') and not git('diff','--check'),'clean precommit boundary/index')
    need(set(state)==set(f['sources']) and {n for n in state if state[n]!=f['sources'][n]}<=DOCS,'only outcome documentation after gates')
    need(s['passed'] and s['candidate']==f['candidate'] and hashes(s['evidence'])==s['evidence'],'sealed complete acceptance evidence')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());old=tomllib.loads(subprocess.check_output(['git','show',f['head']+':automation/reist-s03b.toml'],cwd=ROOT,timeout=30).decode())
    expected=dict(old);expected['active_id']='';expected['packages']=[dict(f['package'],status='done')]+old['packages'][1:]
    need(q==expected,'exact completed delivery queue; explicitly deferred work stays deferred')
    need(set(changed())<=set(f['package']['allowed_files']),'exact final allowed files')
    save(BASE/'commit-ready.json',dict(passed=True,candidate=f['candidate'],sources=state,changed=changed(),seal=link(BASE/'acceptance-seal.json'),evidence=evidence()))

def final():
    f=read(BASE/'frozen.json');r=read(BASE/'commit-ready.json');head=git('rev-parse','HEAD')
    need(not git('status','--porcelain') and git('rev-parse','HEAD^')==f['head'],'accepted child commit/clean worktree')
    need(r['passed'] and sources()==r['sources'] and hashes(r['evidence'])==r['evidence'],'unchanged ready sources/evidence')
    need(sorted(git('diff','--name-only',f['head'],head).splitlines())==r['changed'],'exact committed scope')
    matrix=read(BASE/'matrix.json')
    save(BASE/'verification-status-cli-delivery-final.json',dict(accepted=True,clean_worktree=True,implementation_commit=head,
        package='R8.3bd-cli-delivery',candidate=f['candidate'],sources=r['sources'],tools=f['tools'],artifacts=f['artifacts'],
        scope=r['changed'],gates=9,cases=10,physical_guests=10,guest_seconds=matrix['guest_seconds'],kernel_builds=0,media_builds=1,
        index=link(MEDIA/'cli-media.json'),seal=link(BASE/'acceptance-seal.json'),commit_ready=link(BASE/'commit-ready.json')))
    print('CLI_DELIVERY_ACCEPTED',head,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for flag in ('freeze','all','dependencies','build-media','package-hosts','runtime','review','scope','seal','ready','final'):
        g.add_argument('--'+flag,action='store_true')
    a=p.parse_args();action=next(k for k,v in vars(a).items() if v)
    {'freeze':freeze,'all':all_gates,'dependencies':dependencies,'build_media':build_media,'package_hosts':package_hosts,
     'runtime':runtime,'review':review,'scope':scope,'seal':seal,'ready':ready,'final':final}[action]()
