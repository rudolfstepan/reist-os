"""One finite, source-bound BB qualification; never builds a kernel."""
from pathlib import Path
import argparse,hashlib,inspect,json,os,shlex,shutil,subprocess,time,tomllib
import check_x86_64_wide_shell_media as check
import build_x86_64_wide_shell_media as producer
import run_qemu_x86_64_wide_shell_media as guest
import verify_x86_64_shell_boot_media as az
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83bb-wide-shell-media/candidate02'
ORIGIN=BASE.parent/'candidate01'
MEDIA=ORIGIN/'media'
ORIGINAL_CANDIDATE='297a8cedcb58589fe0799e6cb0f5c520e079f11fcbbd4dd00f4860925c967407'
ORIGINAL_SEAL='95a67f49f05341c6052bdb7c9b826fc2c4e9d20cf59db7d84d05a758def576ad'
REJECTED_SHA='08872e9545a2df1f05088d984ac670ed161b8be1712da7e9006d2af13ea588c1'
ORIGINAL_BUILD='2ec2293f5c10a720c925b0962afa66f169a4fcc316ab3485b833627a34c9e4b8'
IMAGE=ROOT/'build/codex-agent/r83ba-wide-file/wide-pacing/x86_64/reist-x86_64-bootstrap.elf'
PRIOR=ROOT/'build/codex-agent/r83ba-wide-file/candidate12/verification-status-wide-file-final.json'
PRIOR_SHA='470f37033ca735de54c0d044b7a1b50b5592691e12cff6dc38c9503e917736c0'
AZ=ROOT/'build/codex-agent/r83az-shell-boot-media/candidate10/verification-status-shell-boot-media-final.json'
AZ_SHA='f38a35397b14d6073e5c99f289ab6d7ede550fd55348b6b3e1705731b169b79f'
HEAD='946621b8'
LIMITS=(300,180,180,300,2100,180,180,180)
need=check.need

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2)
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def git(*args):return subprocess.check_output(['git','-c','core.safecrlf=false',*args],cwd=ROOT,timeout=30).decode().strip()
def changed():return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3bb-wide-shell-media' and p['status']=='active','BB active package')
    return p
def sources():
    return {n:digest(ROOT/n) for n in sorted(set(git('ls-files').splitlines())|set(package()['allowed_files'])) if (ROOT/n).is_file()}

def canonical_descriptor(value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    need(0<len(raw)<=16384,'canonical signed descriptor bound')
    return raw

def require_ext2_failure(error):
    need(isinstance(error,ValueError) and str(error).startswith('wide EXT2 '),
         'signed malformed filesystem must reach the EXT2 predicate, not fail JSON/signature admission')

def reused_evidence(state):
    need(digest(ORIGIN/'acceptance-seal.json')==ORIGINAL_SEAL and
         digest(ORIGIN/'direct-review-rejected.json')==REJECTED_SHA,'preserved rejected precommit seal')
    seal=read(ORIGIN/'acceptance-seal.json');old=read(ORIGIN/'frozen.json')
    need(seal['passed'] and not seal['accepted'] and seal['candidate']==old['candidate']==ORIGINAL_CANDIDATE,
         'eight green gates are not acceptance after direct-review rejection')
    allowed={'scripts/verify_x86_64_wide_shell_media.py','test/test_x86_64_wide_shell_media.py',
             'docs/architecture/NATIVE_WIDE_SHELL_MEDIA_CONTRACT.md','docs/development/CURRENT_WORK.md',
             'docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
    need(set(state)==set(old['sources']) and {n for n in state if state[n]!=old['sources'][n]}<=allowed,
         'reuse requires exact complete runtime/consumer/producer/production sources')
    files=dict(seal['evidence'])
    for name in ('acceptance-seal.json','direct-review-rejected.json'):files[(ORIGIN/name).relative_to(ROOT).as_posix()]=digest(ORIGIN/name)
    need(set(files)=={p.relative_to(ROOT).as_posix() for p in ORIGIN.rglob('*') if p.is_file()},'complete original file inventory')
    for name,sha in files.items():need(digest(ROOT/name)==sha,'exact original evidence '+name)
    for path,sha in old['tools'].items():need(digest(path)==sha,'same original runtime tool '+path)
    need(digest(ORIGIN/'build-media.json')==ORIGINAL_BUILD,'original media build receipt')
    matrix=read(ORIGIN/'matrix.json')
    need(matrix['candidate']==ORIGINAL_CANDIDATE and matrix['passed'] and matrix['closed'] and
         len(matrix['cases'])==10 and matrix['fresh_guests']==10 and matrix['reused_guests']==0,'complete original ten-case matrix')
    for row,spec in zip(matrix['cases'],guest.CASES):
        name,layout,case,session,ram=spec
        limit=300+guest.bios_budget(case) if session is not None else guest.negative_budget(layout,case)
        need(row['passed'] and row['reused'] is False and tuple(row[k] for k in ('name','layout','case','session','ram'))==spec and
             0<row['elapsed']<=limit and row['evidence_directory']==(ORIGIN/'runtime'/name).relative_to(ROOT).as_posix(),
             'exact complete original case '+name)
    return dict(matrix=matrix,files=files,original_seal=ORIGINAL_SEAL)

def retained():
    need(digest(PRIOR)==PRIOR_SHA and digest(AZ)==AZ_SHA,'accepted BA/AZ receipts')
    prior=read(PRIOR);old=read(AZ)
    for receipt,commit in ((prior,'02202bd37e46683bc85b92307dfc9c4582d78afc'),
                           (old,'5db38510b205d1a8fdcecc28bdf437fac5978212')):
        need(receipt['accepted'] and receipt['clean_worktree'] and receipt['implementation_commit']==commit,'accepted clean predecessor')
        for path,sha in receipt['tools'].items():need(digest(path)==sha,'same tool '+path)
        for name in ('seal','commit_ready'):
            need(link(ROOT/receipt[name]['path'])==receipt[name],'immutable predecessor '+name)
    allowed=set(package()['allowed_files'])
    for name,sha in prior['sources'].items():
        if name not in allowed:need(digest(ROOT/name)==sha,'unchanged BA dependency '+name)
    for name in ('scripts/build_x86_64_shell_media.py','scripts/check_x86_64_shell_media.py',
                 'scripts/run_qemu_x86_64_shell_boot_media.py','scripts/verify_x86_64_shell_boot_media.py',
                 'test/test_x86_64_shell_boot_media.py'):
        need(digest(ROOT/name)==old['sources'][name],'unchanged AZ integration '+name)
    for path,sha in prior['artifacts'].items():need(digest(ROOT/path)==sha,'exact retained artifact '+path)
    need(link(IMAGE)==prior['image'],'same accepted wide image')
    before=subprocess.check_output(['git','show',HEAD+':Makefile'],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
    need(producer.without_wide_media_target((ROOT/'Makefile').read_text(encoding='utf-8'))==before,'exact old Make defaults')
    name='scripts/verify_x86_64_shell_session.py';text=(ROOT/name).read_text()
    text=check.once(text,'    from build_x86_64_wide_shell_media import without_wide_media_target\n','')
    text=check.once(text,"without_wide_build_selector(without_wide_media_target((ROOT/name).read_text(encoding='utf-8')),make=True)",
                         "without_wide_build_selector((ROOT/name).read_text(encoding='utf-8'),make=True)")
    before=subprocess.check_output(['git','show',HEAD+':'+name],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
    need(text==before,'exact historical adapter except packaging projection')
    producer.inputs(IMAGE.parent)
    return prior

def freeze():
    need(git('rev-parse','--short=8','HEAD')==HEAD and not BASE.exists(),'fresh BB contract boundary')
    p=package();need(set(changed())<=set(p['allowed_files']),'BB scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'BB index/whitespace')
    prior=retained();state=sources();reuse=reused_evidence(state);commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==8 and all((ROOT/n).is_file() for n in p['allowed_files']),'complete BB source/gate inventory')
    need((ROOT/'automation/reist-s03b.toml').read_bytes().replace(b'\r\n',b'\n')==
         subprocess.check_output(['git','show',HEAD+':automation/reist-s03b.toml'],cwd=ROOT,timeout=30).replace(b'\r\n',b'\n'),
         'no premature queue transition')
    value=dict(head=git('rev-parse','HEAD'),package=p,sources=state,changed=changed(),commands=commands,limits=LIMITS,
        tools=prior['tools'],prior=link(PRIOR),az=link(AZ),
        reused=reuse,reserved=dict(kernel_builds=0,media_builds=0,guests=0,guest_seconds=0),
        previous=dict(kernel_builds=0,media_builds=1,guests=10,guest_seconds=521.0947888000519,
            rejected=link(ORIGIN/'direct-review-rejected.json')),
        candidate=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest())
    save(BASE/'frozen.json',value)
    for name in changed():
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    print('BB_FROZEN',value['candidate'],flush=True)

def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and sources()==f['sources'] and package()==f['package'] and
         changed()==f['changed'],'exact BB frozen source/queue/scope')
    for path,sha in f['tools'].items():need(digest(path)==sha,'BB frozen tool '+path)
    need(link(PRIOR)==f['prior'] and link(AZ)==f['az'],'accepted predecessors retained')
    need(reused_evidence(f['sources'])==f['reused'],'exact original source/tool/all-raw-bound reuse')
    return f

def command(args,limit,log):
    started=time.monotonic();result=dict(command=list(args),passed=False)
    with log.open('xb') as out:
        proc=subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:result['returncode']=proc.wait(timeout=limit);result['passed']=result['returncode']==0
        except subprocess.TimeoutExpired:
            result['error']='absolute command deadline'
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=3)
            else:proc.kill()
            proc.wait(timeout=3)
        finally:result['elapsed']=time.monotonic()-started
    result['log']=link(log);return result

def dependencies():
    f=binding();retained()
    import ast
    import run_qemu_x86_64_wide_file as ba
    original=ba.namespace()
    for name in ('validate_capture','validate_storage','validate_policy','validate_cpu','validate_identity',
                 'validate_io_and_faults','validate_image_start','validate_terminal','validate_ipc_delivery'):
        need(ast.dump(ast.parse(inspect.getsource(getattr(guest.ay,name))))==
             ast.dump(ast.parse(inspect.getsource(getattr(original,name)))),'exact BA safety predicate '+name)
    save(BASE/'dependencies.json',dict(candidate=f['candidate'],passed=True))

def build_media():
    f=binding();retained();old=read(ORIGIN/'build-media.json')
    need(old['passed'] and old['kernel_builds']==0 and old['media_builds']==1 and
         old['index']==link(MEDIA/'wide-shell-media.json'),'same previously published media pair')
    attempt=check.verify(MEDIA);need(attempt.relative_to(ROOT).as_posix()==old['attempt'],'same independent media validation')
    save(BASE/'build-media.json',dict(old,candidate=f['candidate'],media_builds=0,reused_from=link(ORIGIN/'build-media.json')))

def package_path():
    row=read(BASE/'build-media.json');need(row['passed'] and row['kernel_builds']==0 and row['media_builds']==0 and
        row['reused_from']==link(ORIGIN/'build-media.json'),'one unchanged reused pair')
    need(row['directory']==MEDIA.relative_to(ROOT).as_posix() and row['index']==link(MEDIA/'wide-shell-media.json'),'same published index')
    attempt=check.verify(MEDIA);need(attempt.relative_to(ROOT).as_posix()==row['attempt'],'same published attempt')
    return attempt

def package_hosts():
    binding();started=time.monotonic();rows=[]
    for n,name in enumerate(('test/test_x86_64_shell_boot_media.py','test/test_x86_64_wide_file_runtime.py')):
        row=command(['python',name,'-v'],120,BASE/f'legacy-host-{n}.log');rows.append(row)
        need(row['passed'],'unchanged dependency host '+name)
    save(BASE/'legacy-hosts.json',dict(passed=True,commands=rows,elapsed=time.monotonic()-started))
    namespace=dict(vars(az),binding=binding,package_path=package_path,BASE=BASE,MEDIA=MEDIA,check=check,producer=producer,
        canonical_descriptor=canonical_descriptor,require_ext2_failure=require_ext2_failure)
    replay=guest.function(az.package_hosts,namespace,[
        ("index=folder/'shell-media.json'","index=folder/'wide-shell-media.json'"),
        ("MEDIA/'shell-media.json'","MEDIA/'wide-shell-media.json'"),
        ('check.digest(path,131072)','check.digest(path,1048576)'),
        ("(target/'package.json').write_text(json.dumps(package,sort_keys=True,separators=(',',':'))+'\\n',encoding='ascii')",
         "(target/'package.json').write_bytes(canonical_descriptor(package))"),
        ("except ValueError as error:results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))",
         "except ValueError as error:require_ext2_failure(error);results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))")])
    replay()

def runtime():
    f=binding();package_path();summary=f['reused']['matrix']
    rows=[dict(r,reused=True) for r in summary['cases']]
    save(BASE/'matrix.json',dict(summary,cases=rows,candidate=f['candidate'],fresh_guests=0,reused_guests=10,
        original_elapsed=summary['elapsed'],physical_guest_seconds=0,origin=link(ORIGIN/'matrix.json')))

def review():
    namespace=dict(vars(az),binding=binding,package_path=package_path,BASE=BASE,MEDIA=MEDIA,IMAGE=IMAGE,
        check=check,guest=guest,evidence_origin=lambda spec:ORIGIN)
    replay=guest.function(az.review,namespace,[
        ('binding();positive_reuse_projection();negative_reuse_projection();','binding();'),
        ("summary['guest_seconds']<=455","summary['guest_seconds']<=1730"),
        ("(75 if case=='a-signature' else 65)","(330 if case=='a-signature' else 320)"),
        ("metrics['observe_seconds']<=42","metrics['observe_seconds']<=297"),
        ("check.bounded(out/'generated.raw',131072)==check.bounded(attempt/'system.ext2',131072)",
         "check.bounded(out/'generated.raw',1048576)==check.bounded(attempt/'system.ext2',1048576)"),
        ("data['logical_bytes']==131072","data['logical_bytes']==1048576"),
        ("end==131072","end==1048576")])
    replay()
    files={p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
    files.update(read(BASE/'frozen.json')['reused']['files']);save(BASE/'raw-hashes.json',files)

def scope():
    f=binding();retained();need(not git('diff','--check') and not git('diff','--cached','--name-only'),'BB final whitespace/index')
    need(read(BASE/'review.json')['passed'],'full raw review before scope')
    save(BASE/'scope.json',dict(candidate=f['candidate'],passed=True,changed=changed()))

def all_gates():
    f=binding();need(not (BASE/'started.json').exists(),'BB single frozen execution')
    save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();row=command(shlex.split(cmd),limit,BASE/f'gate-{n:02d}.log')
        row.update(candidate=f['candidate'],gate=n);save(BASE/f'gate-{n:02d}.json',row)
        print('BB_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:
            save(BASE/'stopped.json',dict(candidate=f['candidate'],failed_gate=n,receipt=row))
            raise ValueError('first failed BB gate; no subsequent execution')
    save(BASE/'gates-passed.json',dict(candidate=f['candidate'],passed=True,gates=8))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for flag in ('freeze','all','dependencies','build-media','package-hosts','runtime','review','scope'):g.add_argument('--'+flag,action='store_true')
    a=p.parse_args();action=next(k for k,v in vars(a).items() if v)
    {'freeze':freeze,'all':all_gates,'dependencies':dependencies,'build_media':build_media,
     'package_hosts':package_hosts,'runtime':runtime,'review':review,'scope':scope}[action]()
