"""Frozen single-image Ring3 file-capture transaction; never retries a gate."""
from pathlib import Path
import argparse,hashlib,json,shlex,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'build/codex-agent/r83aw-file-capture';BASE=PARENT/'candidate02'
IMAGE=PARENT/'native-link-fix/x86_64/reist-x86_64-bootstrap.elf'
PRIOR=ROOT/'build/codex-agent/r83av-terminal/candidate05/verification-status-terminal-final.json'
PRIOR_SHA='cb07c12c335b1540dbbf9f33d4150fce91ba6c2a46300bdd033950102dad641a'
BASELINE='f05fcc86dfd5f8e6b61b911a349230c5a68c7b29'
DOCS={'automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_CAPTURE_CONTRACT.md',
      'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2,sort_keys=True)

def prior():
    need(digest(PRIOR)==PRIOR_SHA,'accepted AV receipt pin');p=read(PRIOR)
    need(p['accepted'] and p['clean_worktree'] and p['implementation_commit']==BASELINE,'accepted AV commit')
    verify_files(p['tools']);verify_files(p['evidence_sha256']);return p

def changed():
    return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))

def freeze():
    need(not (BASE/'frozen.json').exists() and not IMAGE.exists(),'one fresh capture candidate/image')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3aw-file-capture' and p['status']=='active','active capture package')
    old=prior();names=set(git('ls-files').splitlines())|set(p['allowed_files'])
    stop=PARENT/'candidate01/stopped.json'
    need(digest(stop)=='58ad4de92aa852f85a4eef7f369c0fbfc9337ed1264b2d3f0362a2aacd14d066','preserved first link stop')
    failed=read(stop);need(failed['failed_gate']==6 and failed['image'] is None and not failed['matrix'],'one failed build, zero guests')
    before=(PARENT/'candidate01/sources/userspace/sdk/lib/x86_64/file_image.c').read_text(encoding='utf-8')
    need(before.replace('canonical.stat.info=p->frame.stat.info;','file_copy(&canonical.stat.info,&p->frame.stat.info,sizeof(canonical.stat.info));')==
         (ROOT/'userspace/sdk/lib/x86_64/file_image.c').read_text(encoding='utf-8'),'only bounded copy correction')
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    edits=changed();need(set(edits)<=set(p['allowed_files']),'capture scope')
    for name in edits:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as output:output.write((ROOT/name).read_bytes())
    logs=list((ROOT/'build/codex-agent').glob('r83aw-capture-*.log'))
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in logs}
    for old_dir in (PARENT/'candidate01',PARENT/'native'):
        for path in old_dir.rglob('*'):
            if path.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in path.parts):
                retained[path.relative_to(ROOT).as_posix()]=digest(path)
    for path in (PARENT/'host').rglob('*'):
        if path.is_file():retained[path.relative_to(ROOT).as_posix()]=digest(path)
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==10,'ten capture gates')
    f=dict(head=git('rev-parse','HEAD'),package=p,commands=commands,changed=edits,sources=sources,
        tools=old['tools'],prior=link(PRIOR),retained=retained,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(build_invocations=1,complete_images=0,guests=0),
        reserved=dict(builds=1,guests=25,guest_seconds=45,total_guest_seconds=1125))
    save(BASE/'frozen.json',f);binding();print('CAPTURE_FROZEN',len(sources),flush=True)

def binding():
    f=read(BASE/'frozen.json');need(git('rev-parse','HEAD')==f['head'],'capture frozen HEAD')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    need(q['active_id']==f['package']['id'] and q['packages'][0]==f['package'],'capture frozen scope/gates')
    verify_files(f['sources']);verify_files(f['tools'])
    need(changed()==f['changed'] and set(f['changed'])<=set(f['package']['allowed_files']),'capture exact changed paths')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'capture empty staging/whitespace')
    need(digest(PRIOR)==PRIOR_SHA,'capture accepted predecessor');return f

def defaults():
    f=binding();prior()
    # There is no new selector: existing consumers execute the shared stages
    # through the compatibility wrapper. Only these two production files differ.
    production={'userspace/sdk/include/reist/x86_64/file_image.h','userspace/sdk/lib/x86_64/file_image.c'}
    allowed=production|DOCS|{'test/test_x86_64_file_capture.py','test/x86_64_file_capture_host.c',
                          'scripts/verify_x86_64_file_capture.py'}
    need(set(git('diff','--name-only',BASELINE).splitlines())|set(changed())<=allowed,'capture baseline scope')
    for n in range(1,5):need(read(BASE/f'gate-{n:02d}.json')['passed'],'capture actual host prerequisites')
    return dict(passed=True,production=sorted(production),prior=link(PRIOR))

def image_equivalence():
    import run_qemu_x86_64_terminal as run
    binding();old=prior();old_image=ROOT/old['image']['path'];need(link(old_image)==old['image'],'old immutable image')
    original=run.live.wide.payload.elf(old_image.read_bytes(),32)
    current=run.live.wide.payload.elf(IMAGE.read_bytes(),32)
    need(current['entry']==original['entry'] and current['symbols']==original['symbols'],'same kernel symbols/entry')
    def allocated(parsed):return {n:s for n,s in parsed['sections'].items() if s['flags']&2 and n!='.native_catalog'}
    need(allocated(current)==allocated(original),'all allocated kernel sections identical except catalog')
    objects=[]
    for path in old_image.parent.glob('*.o'):
        if path.name=='elf64_loader.o':continue # catalog is embedded here; allocated bytes checked above
        need(digest(path)==digest(IMAGE.parent/path.name),'kernel object equality '+path.name);objects.append(path.name)
    before=(old_image.parent/'boot-programs.bin').read_bytes();after=(IMAGE.parent/'boot-programs.bin').read_bytes()
    need(len(before)==len(after)==4*run.live.wide.SIZE and before[run.live.wide.SIZE:]==after[run.live.wide.SIZE:],
         'only root0 prepared image changes, other roles identical')
    _,counts,raw=run.live.image_config(IMAGE);_,old_counts,old_raw=run.live.image_config(old_image)
    need(raw==old_raw and counts==old_counts,'file child and driver/FS images exact')
    fatal=ROOT/'build/codex-agent/r83av-terminal/candidate05/fatal'
    matrices=list(fatal.glob('attempt-*/summary.json'));need(len(matrices)==1,'one AV fatal matrix')
    summary=read(matrices[0]);need(summary['passed'] and summary['closed'] and len(summary['cases'])==2,'two qualified fatal guests')
    for row in summary['cases']:
        folder=ROOT/row['folder'];run.validate_fatal((folder/'guest.log').read_text(),
            (folder/'frame-trace.log').read_text(),row['case'],folder)
    return dict(passed=True,image=link(IMAGE),objects=sorted(objects),fatal_reuse=link(matrices[0]))

def runtime():
    import run_qemu_x86_64_terminal as run
    f=binding()
    for n in range(1,8):need(read(BASE/f'gate-{n:02d}.json')['passed'],'capture runtime prerequisites')
    need(not list((BASE/'guests').glob('attempt-*')),'one capture matrix, no unchanged retry')
    config,counts,raw=run.live.image_config(IMAGE)
    folder=BASE/'guests'/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,closed=False,candidate=f['candidate'],image=link(IMAGE),cases=[],guest_elapsed=0.0)
    begin=time.monotonic()
    try:
        for case,layout,ram,point in run.CASES:
            binding();need(len(summary['cases'])<25 and summary['guest_elapsed']+45<=1125,'finite capture reserve')
            oom=None if point is None else 0 if point=='first' else counts['program']//2 if point=='middle' else counts['program']-1
            out=folder/f'guest-{case}-{layout}-{ram}-{point}';out.mkdir()
            row=dict(case=case,layout=layout,ram=ram,point=point,oom=oom,folder=out.relative_to(ROOT).as_posix(),passed=False)
            summary['cases'].append(row);started=time.monotonic()
            try:
                fixture=run.live.pio.Fixture(out,filesystem=run.live.media.LAYOUTS[layout],file_program=run.live.file.program_variant(raw,case))
                code=run.observer(config,out,case,layout,oom,raw)
                serial,trace=run.live.wide.transport.capture(IMAGE,out,code,ram,fixture,
                    binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True)
                run.validate(serial,trace,case,layout,oom,counts,raw,out)
                need(link(IMAGE)==summary['image'],'capture immutable image');row['passed']=True
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed']
            need(row['elapsed']<=45,'capture inclusive cleanup deadline')
            print('CAPTURE_GUEST_PASS',case,layout,ram,point,round(row['elapsed'],3),flush=True)
        need(len(summary['cases'])==25 and time.monotonic()-begin<=1200,'complete bounded capture matrix')
        summary['passed']=True;return dict(passed=True,matrix=link_after_save(folder,summary,begin))
    except Exception as error:
        summary['error']=str(error);link_after_save(folder,summary,begin);raise

def link_after_save(folder,summary,begin):
    summary.update(closed=True,elapsed=time.monotonic()-begin)
    path=folder/'summary.json';save(path,summary);return link(path)

def review():
    import run_qemu_x86_64_terminal as run
    f=binding();prior();verify_files(f['retained']);image_equivalence()
    for n in range(1,10):
        row=read(BASE/f'gate-{n:02d}.json')
        need(row['passed'] and row['candidate']==f['candidate'] and row['command']==f['commands'][n-1] and
             row['log']==link(ROOT/row['log']['path']),'nine exact completed gates')
    paths=list((BASE/'guests').glob('attempt-*/summary.json'));need(len(paths)==1,'unique complete capture matrix')
    matrix=read(paths[0]);need(matrix['passed'] and matrix['closed'] and matrix['candidate']==f['candidate'] and
        matrix['image']==link(IMAGE) and matrix['elapsed']<=1200,'bound successful capture matrix')
    need([(r['case'],r['layout'],r['ram'],r['point']) for r in matrix['cases']]==list(run.CASES),'full25 case coverage')
    need(matrix['guest_elapsed']==sum(r['elapsed'] for r in matrix['cases'])<=1125,'full guest ledger')
    _,counts,raw=run.live.image_config(IMAGE);evidence={}
    for row in matrix['cases']:
        need(row['passed'] and 0<row['elapsed']<=45,'each capture guest passed');folder=ROOT/row['folder']
        need(folder.is_relative_to(paths[0].parent),'capture folder binding')
        run.validate((folder/'guest.log').read_text(),(folder/'frame-trace.log').read_text(),
            row['case'],row['layout'],row['oom'],counts,raw,folder)
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
             metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','capture cleanup')
        dumps=run.live.cpu.binary_capacity(folder)
        extras=[folder/run.live.cpu.CPU_FILE,folder/'cpu-trace-v1.bin',folder/run.LEDGER]
        need(len(dumps)+3<=2048 and sum(r['bytes'] for r in dumps)+sum(p.stat().st_size for p in extras)<=128*1024*1024,
             'capture aggregate evidence bound')
        need([r['equivalence'] for r in dumps if r['equivalence'] is not None]==['kernel','high'],'independent memory transport equality')
        for n,r in enumerate(dumps,1):
            path=folder/'binary-memory'/r['file']
            need(r['sequence']==n and path.name==f'ram-{n:04d}.bin' and path.stat().st_size==r['bytes'] and digest(path)==r['sha256'],
                 'capture exact physical snapshot bytes')
        for path in folder.rglob('*'):
            if path.is_file():need(not path.is_symlink(),'capture no symlink');evidence[path.relative_to(ROOT).as_posix()]=digest(path)
    return dict(passed=True,cases=25,fatal_reused=2,builds=1,guest_elapsed=matrix['guest_elapsed'],
                image=link(IMAGE),matrix=link(paths[0]),evidence_sha256=evidence)

def gates():
    f=binding();need(not list(BASE.glob('gate-*.json')),'capture no unchanged gate retry')
    for n,command in enumerate(f['commands'],1):
        binding();limit=300 if n<=4 else 1200 if n==8 else 180
        log=BASE/f'gate-{n:02d}.log';begin=time.monotonic();result=dict(passed=False,candidate=f['candidate'],command=command,limit=limit)
        try:
            with log.open('xb') as output:
                child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,timeout=limit,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result.update(exit_code=child.returncode,passed=child.returncode==0)
        except Exception as error:result['error']=str(error)
        result.update(elapsed=time.monotonic()-begin,log=link(log));save(BASE/f'gate-{n:02d}.json',result)
        print('CAPTURE_GATE',n,'PASS' if result['passed'] else 'FAIL',round(result['elapsed'],3),flush=True)
        if not result['passed']:
            save(BASE/'stopped.json',dict(frozen=link(BASE/'frozen.json'),failed_gate=n,result=result,
                image=link(IMAGE) if IMAGE.exists() else None,matrix=[link(p) for p in BASE.glob('guests/attempt-*/summary.json')]))
            print(log.read_text(errors='replace')[-3500:],flush=True);return 1
    return 0

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','image-equivalence','runtime','review'):g.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.freeze:freeze();return 0
    if args.gates:return gates()
    name=next(n for n in ('defaults','image_equivalence','runtime','review') if getattr(args,n))
    begin=time.monotonic();result=dict(passed=False)
    try:
        result=globals()[name]();print('CAPTURE_'+name.upper()+'_PASS',flush=True);return 0
    except Exception as error:result['error']=str(error);print('CAPTURE_VERIFY_FAIL',error,flush=True);return 1
    finally:result['elapsed']=time.monotonic()-begin;save(BASE/(name+'-'+uuid.uuid4().hex+'.json'),result)

if __name__=='__main__':raise SystemExit(main())
