"""Read-only acceptance bindings for the explicit eight-owner native profile.

Receipts are exclusive, ignored evidence files; never rewrite a reference pin,
old gate receipt or existing result. This verifier does not build or launch VMs.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,time,tomllib,uuid
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83an-task-pool'
PACKAGE='R8.3an-x86_64-task-pool'


def need(value,message):
    if not value:raise ValueError(message)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def link(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=digest(path))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=30).strip()


def verify_files(files):
    for name,sha in files.items():need(digest(ROOT/name)==sha,'changed binding: '+name)


def active_candidate():
    paths=sorted(BASE.glob('candidate-*/frozen-candidate.json'))
    need(1<=len(paths)<=7,'pool bounded candidate transactions')
    need([p.parent.name for p in paths]==[f'candidate-{i:02d}' for i in range(1,len(paths)+1)],'pool candidate sequence')
    for old in paths[:-1]:
        stopped=read(old.parent/'stopped.json')
        need(stopped['candidate']==read(old)['candidate'] and stopped['passed'] is False,'pool prior candidate closed on failure')
    if len(paths)==4:
        renewal=read(BASE/'ipc-check-renewal/baseline.json')
        need(renewal['head']==git('rev-parse','d35d6856')==git('rev-parse','HEAD'),'pool exact renewal contract')
        need(renewal['original_baseline']==link(BASE/'baseline.json') and
             renewal['original_status']==link(BASE/'verification-status-task-pool-stopped.json'),'pool original renewal receipts')
        original=read(BASE/'baseline.json')['package']
        selected=renewal['package']
        need({k:v for k,v in selected.items() if not k.startswith('ipc_check_renewal_')}==original and
             selected['ipc_check_renewal_files']==['test/x86_64_task_pool_host.c','test/test_x86_64_task_pool.py','scripts/verify_x86_64_task_pool.py'] and
             selected['ipc_check_renewal_prefix']=='build/codex-agent/r83an-task-pool/ipc-check-renewal/','pool renewal-only authority')
    if len(paths)==5:
        renewal=read(BASE/'output-check-renewal/baseline.json')
        need(renewal['head']==git('rev-parse','18bf314b')==git('rev-parse','HEAD'),'pool exact output renewal contract')
        need(renewal['original_baseline']==link(BASE/'baseline.json') and
             renewal['original_status']==link(BASE/'verification-status-ipc-check-renewal.json'),'pool original output renewal receipts')
        previous=read(BASE/'ipc-check-renewal/baseline.json')['package'];selected=renewal['package']
        need({k:v for k,v in selected.items() if not k.startswith('output_check_renewal_')}==previous and
             selected['output_check_renewal_files']==['test/test_x86_64_task_pool.py','scripts/verify_x86_64_task_pool.py'] and
             selected['output_check_renewal_prefix']=='build/codex-agent/r83an-task-pool/output-check-renewal/','pool output-only authority')
    if len(paths)==6:
        renewal=read(BASE/'family-layout-renewal/baseline.json')
        need(renewal['head']==git('rev-parse','171b25b8')==git('rev-parse','HEAD'),'pool exact family layout renewal contract')
        need(renewal['original_baseline']==link(BASE/'baseline.json') and
             renewal['original_status']==link(BASE/'verification-status-output-check-renewal.json'),'pool original family layout renewal receipts')
        previous=read(BASE/'output-check-renewal/baseline.json')['package'];selected=renewal['package']
        need({k:v for k,v in selected.items() if not k.startswith('family_layout_renewal_')}==previous and
             selected['family_layout_renewal_files']==['arch/x86_64/proc/task_family.inc','scripts/verify_x86_64_task_pool.py'] and
             selected['family_layout_renewal_prefix']=='build/codex-agent/r83an-task-pool/family-layout-renewal/','pool family-layout-only authority')
    if len(paths)==7:
        renewal=read(BASE/'context-owner-renewal/baseline.json')
        need(renewal['head']==git('rev-parse','d5764fb9')==git('rev-parse','HEAD'),'pool exact context owner renewal contract')
        need(renewal['original_baseline']==link(BASE/'baseline.json') and
             renewal['original_status']==link(BASE/'verification-status-family-layout-renewal.json'),'pool original context owner receipts')
        previous=read(BASE/'family-layout-renewal/baseline.json')['package'];selected=renewal['package']
        need({k:v for k,v in selected.items() if not k.startswith('context_owner_renewal_')}==previous and
             selected['context_owner_renewal_files']==list(CONTEXT_RENEWAL_SOURCES) and
             selected['context_owner_renewal_prefix']=='build/codex-agent/r83an-task-pool/context-owner-renewal/','pool context-owner-only authority')
    return paths[-1]


def candidate_dir(frozen):
    path=ROOT/frozen['directory']
    need(path.parent==BASE and re.fullmatch('candidate-0[1234567]',path.name),'pool candidate directory')
    return path


def source_binding():
    path=active_candidate();frozen=read(path)
    baseline_name={'candidate-04':'ipc-check-renewal/baseline.json','candidate-05':'output-check-renewal/baseline.json','candidate-06':'family-layout-renewal/baseline.json','candidate-07':'context-owner-renewal/baseline.json'}.get(path.parent.name,'baseline.json')
    baseline=read(BASE/baseline_name)
    need(candidate_dir(frozen)==path.parent,'pool candidate location')
    need(frozen['head']==baseline['head']==git('rev-parse','HEAD'),'pool baseline HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==PACKAGE)
    need(package==baseline['package']==frozen['package'] and queue['active_id']==PACKAGE,'pool frozen scope/gates')
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed<=set(package['allowed_files']) and not git('diff','--cached','--name-only'),'pool candidate scope/index')
    need(not git('diff','--check'),'pool whitespace')
    verify_files(frozen['source_inputs']);verify_files(frozen['sources']);verify_files(frozen['tools_sha256'])
    for name,sha in baseline['source_inputs'].items():
        if name not in package['allowed_files']:need(frozen['source_inputs'].get(name)==sha,'pool unrelated input '+name)
    candidate=hashlib.sha256(json.dumps(frozen['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    need(candidate==frozen['candidate'],'pool candidate digest')
    return frozen


def binary_map(folder):
    result={}
    for path in folder.rglob('*'):
        if not path.is_file() or 'zig-cache' in path.parts or path.suffix not in ('.o','.elf','.bin','.prg','.inc','.json'):continue
        relative=path.relative_to(folder).as_posix()
        if path.suffix=='.json' and path.name!='bootstrap_core_layout.json':continue
        key=re.sub(r'^programs-[0-9a-f]{32}/','programs/',relative)
        need(key not in result,'duplicate producer payload '+key)
        result[key]=dict(path=path.relative_to(ROOT).as_posix(),sha256=digest(path))
    need(20<=len(result)<=120,'pool default payload capacity')
    return result


def defaults():
    frozen=source_binding();baseline=read(BASE/'baseline.json');bindings={}
    verify_files(baseline['preserved_reference_artifacts'])
    for profile,target in (('normal','normal'),('native','file-reference')):
        verify_files(baseline['baseline_profiles'][profile])
        original=ROOT/'build/codex-agent/r83am-file-launch/make-stdio-check'/profile/'x86_64'
        old=binary_map(original);new=binary_map(BASE/target/'x86_64')
        need(set(old)==set(new),'default payload set drift '+profile)
        for name in old:need(old[name]['sha256']==new[name]['sha256'],'default binary drift '+profile+'/'+name)
        bindings[profile]=dict(before=old,after=new)
    accepted=read(ROOT/baseline['accepted_am']['path']);qualified=read(ROOT/baseline['qualified_am']['path'])
    for receipt in (baseline['accepted_am'],baseline['qualified_am']):
        need(digest(ROOT/receipt['path'])==receipt['sha256'],'accepted AM receipt changed')
    need(accepted['accepted'] and accepted['qualification_passed']==30 and
         accepted['implementation_commit']=='0f4efd173a02ce711d38da9713382b41808b4efd','AM acceptance binding')
    verify_files(accepted['evidence_sha256']);verify_files(qualified['evidence_sha256'])
    # Reuse old native guest evidence only after full default binary equality
    # and unchanged original observer/validator inputs, not from marker text.
    for name,sha in baseline['source_inputs'].items():
        if name.startswith('scripts/run_qemu_') or name in ('scripts/qemu_binary_memory.py','scripts/verify_x86_64_file_launch.py'):
            need(digest(ROOT/name)==sha,'original observer changed '+name)
    return dict(passed=True,kind='defaults',candidate=frozen['candidate'],payloads=bindings,
                source_sha256=frozen['source_inputs'],old_acceptance=baseline['accepted_am'],old_qualification=baseline['qualified_am'],
                frozen=link(candidate_dir(frozen)/'frozen-candidate.json'),new_builds=0,new_guests=0)


def matching_receipt(kind,candidate):
    matches=[]
    for path in BASE.glob(kind+'-*.json'):
        receipt=read(path)
        if receipt.get('passed') and receipt.get('candidate')==candidate:matches.append((path,receipt))
    need(len(matches)==1,'exact qualified '+kind+' receipt')
    return matches[0]


CONTEXT_RENEWAL_SOURCES=('scripts/run_qemu_x86_64_task_pool.py','test/test_x86_64_task_pool.py','scripts/verify_x86_64_task_pool.py')
CONTEXT_RENEWAL_DOCS=('automation/reist-s03b.toml','docs/architecture/NATIVE_TASK_POOL_CONTRACT.md','docs/development/CURRENT_WORK.md')


def build_reuse_binding(frozen,original,gate,index):
    """Pure, fail-closed input/profile/result admission for the three old builds."""
    need(type(index) is int and index in (18,19,20),'reuse build index')
    need(frozen['directory']=='build/codex-agent/r83an-task-pool/candidate-07' and
         original['directory']=='build/codex-agent/r83an-task-pool/candidate-06','reuse exact candidates')
    permitted=set(CONTEXT_RENEWAL_SOURCES+CONTEXT_RENEWAL_DOCS)
    need(set(frozen['source_inputs'])==set(original['source_inputs']),'reuse input inventory')
    need(all(sha==frozen['source_inputs'][name] for name,sha in original['source_inputs'].items() if name not in permitted),'reuse build source drift')
    for candidate in (frozen,original):
        value=hashlib.sha256(json.dumps(candidate['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        need(candidate['candidate']==value,'reuse candidate source digest')
    need(frozen['tools_sha256']==original['tools_sha256'],'reuse tool drift')
    need({k:v for k,v in frozen['package'].items() if not k.startswith('context_owner_renewal_')}==original['package'],'reuse profile/contract drift')
    need(frozen['commands']==original['commands'] and len(frozen['commands'])==24,'reuse commands')
    need(gate['candidate']==original['candidate'] and gate['command']==original['commands'][index-1] and
         gate['passed'] is True and gate['exit_code']==0 and 0<=gate['elapsed']<=180 and
         'execution' not in gate and bool(gate['artifacts']),'reuse original build result')


def build_reuse_proof(frozen,index):
    admission=read(BASE/'context-owner-renewal/admission.json')
    original_path=BASE/'candidate-06/frozen-candidate.json'
    need(admission['build_frozen']==link(original_path),'reuse original source receipt')
    need(type(index) is int and index in (18,19,20),'reuse proof index')
    path=BASE/'candidate-06'/f'gate-{index:02d}.json'
    need(admission['build_receipts'][index-18]==link(path),'reuse original build receipt')
    original=read(original_path);gate=read(path)
    build_reuse_binding(frozen,original,gate,index)
    verify_files(gate['artifacts']);verify_files({gate['log']['path']:gate['log']['sha256']})
    return path,gate


def admit_runtime(image):
    frozen=source_binding();path,receipt=matching_receipt('defaults',frozen['candidate'])
    need(receipt['frozen']==link(candidate_dir(frozen)/'frozen-candidate.json'),'pool default frozen input binding')
    for profile in receipt['payloads'].values():
        for side in ('before','after'):
            verify_files({row['path']:row['sha256'] for row in profile[side].values()})
    need(image==(BASE/'native/x86_64/reist-x86_64-bootstrap.elf').resolve(),'pool runtime exact image')
    # Controller receipt binds the three successful frozen builds, including
    # every native image/object. Admission only verifies, never repeats builds.
    builds=read(candidate_dir(frozen)/'build-receipts.json')
    need(builds['candidate']==frozen['candidate'] and len(builds['gates'])==3,'pool build receipts')
    for index,(gate,command) in enumerate(zip(builds['gates'],frozen['package']['package_tests']),18):
        need(gate['command']==command and gate['passed'] and gate['exit_code']==0 and gate['elapsed']<=180,'pool frozen build result')
        if frozen['directory'].endswith('candidate-07'):
            origin,original=build_reuse_proof(frozen,index)
            need(gate['execution']=='REUSED' and gate['original_receipt']==link(origin) and
                 gate['original_elapsed']==original['elapsed'] and gate['artifacts']==original['artifacts'] and
                 gate['candidate']==frozen['candidate'] and gate['argv']==[],'pool exact reused build proof')
        verify_files(gate['artifacts']);verify_files({gate['log']['path']:gate['log']['sha256']})
    return dict(candidate=frozen['candidate'],defaults=link(path))


def review():
    import run_qemu_x86_64_task_pool as runtime
    frozen=source_binding();image=(BASE/'native/x86_64/reist-x86_64-bootstrap.elf').resolve();admit_runtime(image)
    commands=frozen['package']['targeted_tests']+frozen['package']['package_tests']+frozen['package']['runtime_tests']
    need(len(commands)==24,'pool gate count')
    receipts=[]
    for index,command in enumerate(commands[:-1],1):
        path=candidate_dir(frozen)/f'gate-{index:02d}.json';receipt=read(path)
        limit=300 if index<=17 else 180 if index<=21 else 600 if index==22 else 180
        need(receipt['candidate']==frozen['candidate'] and receipt['command']==command and receipt['passed'] and
             receipt['exit_code']==0 and 0<=receipt['elapsed']<=limit,'pool frozen gate '+str(index))
        verify_files({receipt['log']['path']:receipt['log']['sha256']});receipts.append(link(path))
    attempts=[(p,read(p)) for p in (BASE/'guests').glob('attempt-*/summary.json')]
    need(1<=len(attempts)<=3 and all(r.get('closed') for p,r in attempts),'pool bounded closed attempts')
    need(len({r['candidate'] for p,r in attempts})==len(attempts),'pool unchanged matrix retry')
    need(sum(len(r['cases']) for p,r in attempts)<=30 and sum(r['guest_elapsed'] for p,r in attempts)<=600,'pool cumulative guest bound')
    current=[(p,r) for p,r in attempts if r['candidate']==frozen['candidate']]
    need(len(current)==1,'pool current matrix');path,result=current[0]
    need(result['passed'] and result['image_sha256']==digest(image) and result['guest_elapsed']<=200,'pool successful same-image matrix')
    need([(e['case'],e['ram']) for e in result['cases']]==list(runtime.CASES),'pool original ten-case matrix')
    config=runtime.image_config(image);count=runtime.wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
    need((result['allocations'],result['child_sha256'])==(count,sha),'pool actual image count')
    evidence={}
    for row in result['cases']:
        need(row['passed'] and 0<row['elapsed']<=20,'pool guest deadline/result')
        folder=path.parent/f'guest-{row["case"]}-{row["ram"]}'
        rows=runtime.validate((folder/'guest.log').read_text(),(folder/'frame-trace.log').read_text(),row['case'],row['oom'],count,sha)
        need(row['tasks']==len(rows),'pool exact guest task count')
        reads=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
        need(0<len(reads)<=2048 and sum(r['bytes'] for r in reads)<=128*1024*1024,'pool bounded physical evidence')
        need([r['equivalence'] for r in reads if r['equivalence'] is not None]==['kernel','high'],'pool independent same-stop comparisons')
        for index,r in enumerate(reads,1):
            dump=folder/'binary-memory'/r['file']
            need(r['sequence']==index and dump.name==f'ram-{index:04d}.bin' and dump.stat().st_size==r['bytes'] and digest(dump)==r['sha256'],'pool raw capture binding')
        for f in folder.rglob('*'):
            if f.is_file():evidence[f.relative_to(ROOT).as_posix()]=digest(f)
    verify_files(read(BASE/'baseline.json')['preserved_reference_artifacts'])
    return dict(passed=True,kind='review',candidate=frozen['candidate'],matrix=link(path),evidence_sha256=evidence,
                gates=receipts,cases=10,new_guests=0,new_builds=0,guest_elapsed=result['guest_elapsed'],scope=sorted(frozen['sources']))


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--defaults',action='store_true');group.add_argument('--review',action='store_true');args=parser.parse_args()
    kind='defaults' if args.defaults else 'review';started=time.monotonic();result=dict(passed=False,kind=kind)
    path=BASE/(kind+'-'+uuid.uuid4().hex+'.json')
    try:
        result=defaults() if args.defaults else review()
        print('TASK_POOL_'+kind.upper()+'_OK',flush=True);return 0
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result['error']=str(error);print('TASK_POOL_'+kind.upper()+'_FAIL '+str(error),flush=True);return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,6)
        with path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
        print('TASK_POOL_RECEIPT '+str(path),flush=True)


if __name__=='__main__':raise SystemExit(main())
