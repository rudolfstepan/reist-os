"""Frozen native-shell source/evidence bindings; no builds or guest launches."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'build/codex-agent/r83at-shell'
BASE=PARENT/'buffered'
AS=ROOT/'build/codex-agent/r83as-console'
PRIOR=AS/'queue-drain/verification-status-console-final.json'
PRIOR_SHA='cc22acfe52aae31a38325cd76446144b832f64f1d0cbc7d0b45cdecdc187b2c4'
IMAGE=PARENT/'native-buffered/x86_64/reist-x86_64-bootstrap.elf'
def shared_shell_delta(before,after):
    old=before.decode('utf-8').replace('\r\n','\n')
    current=after.decode('utf-8').replace('\r\n','\n')
    def omit(source,name):
        start=source.index('static int '+name+'(');end=source.index('\n}',start)+2
        return source[:start]+source[end:]
    for name in ('find_drive','current_drive'):old=omit(old,name);current=omit(current,name)
    need(old==current,'shell exact source outside approved two functions')
def binding():
    f=read(BASE/'frozen.json')
    need(digest(PARENT/'verification-status-shell-blocked.json')=='550c61fc8419a3030c82190b64e9b3d4b5d3d6423cc421cd8f8134f588c0ad06','shell retained blocked boundary')
    need(digest(PARENT/'stopped.json')=='e9d5fc683b3c473e68b1f36d6b5af759951921bc25fd7a12440207d0ec545502','shell retained host stop')
    need(git('rev-parse','HEAD')==f['head'],'shell frozen HEAD')
    p=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    need(p['active_id']=='R8.3at-x86_64-shell' and p['packages'][0]==f['package'],'shell frozen queue')
    verify_files(f['sources']);verify_files(f['tools']);verify_files(f['helpers'])
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(f['changed']) and changed<=set(f['package']['allowed_files']),'shell exact scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'shell clean staging/whitespace')
    return f
def defaults():
    f=binding();need(digest(PRIOR)==PRIOR_SHA,'shell exact AS acceptance');prior=read(PRIOR)
    need(prior['accepted'] and prior['clean_worktree'] and prior['qualified_guests']==7 and prior['gates_passed']==12,'shell AS qualification')
    verify_files(prior['evidence_sha256']);verify_files(prior['tools_sha256'])
    allowed=set(f['package']['allowed_files'])|set(prior['documentation_sha256'])
    for name,sha in prior['source_inputs'].items():
        if name not in allowed:need(digest(ROOT/name)==sha,'shell unchanged source '+name)
    # Exact shared sources + unchanged compiler switches for old selections.
    # No preprocessor macro references the new shell selector in kernel code.
    for name in ('arch/x86_64/kernel/bootstrap_core.c','arch/x86_64/proc/cooperative_scheduler.asm',
                 'arch/x86_64/proc/process_run.inc','arch/x86_64/proc/native_console.inc',
                 'userspace/bin/shell_vfs.c','scripts/run_qemu_x86_64_boot_programs.py'):
        raw=subprocess.check_output(['git','show','f2e93446:'+name],cwd=ROOT,timeout=10)
        need(raw.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'shell exact accepted '+name)
    old=subprocess.check_output(['git','show','f2e93446:userspace/bin/shell.c'],cwd=ROOT,timeout=10)
    shared_shell_delta(old,(ROOT/'userspace/bin/shell.c').read_bytes())
    return dict(passed=True,prior=link(PRIOR),reused_fault_cases=['UD2','CPU32','peer-mask','legacy-mask'],new_builds=0)
def review():
    import run_qemu_x86_64_native_shell as shell
    import run_qemu_x86_64_console as console
    f=binding()
    for i in range(1,8):need(read(BASE/f'gate-{i:02d}.json')['passed'],'shell previous gate '+str(i))
    summary_paths=list((BASE/'guests').glob('attempt-*/summary.json'));need(len(summary_paths)==1,'shell unique matrix')
    summary=read(summary_paths[0]);need(summary['passed'] and summary['closed'] and summary['image']==link(IMAGE),'shell matrix accepted')
    need([(r['case'],r['ram']) for r in summary['cases']]==list(shell.CASES),'shell all four cases')
    need(summary['guest_elapsed']<=80 and summary['elapsed']<=120,'shell aggregate deadlines')
    feeder=shell.capture_namespace()['ConsoleFeeder'];evidence={}
    for row in summary['cases']:
        need(row['passed'] and 0<row['elapsed']<=20,'shell guest deadline');folder=ROOT/row['folder']
        serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
        shell.validate(serial,trace,row['case'],row['ram'])
        feeder.validate(shell.inputs(row['case']),trace,read(folder/'console-chunks.json'),read(folder/'console-input.json'))
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','shell cleanup')
        dumps=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
        need(0<len(dumps)<=2048 and sum(r['bytes'] for r in dumps)<=128*1024*1024,'shell raw memory limits')
        need([r['equivalence'] for r in dumps if r['equivalence'] is not None]==['kernel','high'],'shell independent raw equivalence')
        for index,r in enumerate(dumps,1):
            path=folder/'binary-memory'/r['file']
            need(r['sequence']==index and path.name==f'ram-{index:04d}.bin' and path.stat().st_size==r['bytes'] and digest(path)==r['sha256'],'shell binary bytes')
        for path in folder.rglob('*'):
            if path.is_file():need(not path.is_symlink(),'shell symlink');evidence[path.relative_to(ROOT).as_posix()]=digest(path)
    console.image_config(IMAGE)
    attempt=list(IMAGE.parent.glob('programs-*'));need(len(attempt)==1,'shell one producer attempt')
    need((attempt[0]/'root/bin/shell.prg').read_bytes()==(attempt[0]/'program0.prg').read_bytes(),'shell actual staged ELF')
    old=list((AS/'native/x86_64').glob('programs-*'));need(len(old)==1,'shell accepted peer source')
    for n in (1,2,3):need((attempt[0]/f'program{n}.prg').read_bytes()==(old[0]/f'program{n}.prg').read_bytes(),'shell exact denied peer')
    need(digest(IMAGE.parent/'bootstrap_core.o')==digest(AS/'native/x86_64/bootstrap_core.o'),'shell unchanged compiled core')
    return dict(passed=True,cases=4,image=link(IMAGE),matrix=link(summary_paths[0]),evidence_sha256=evidence)
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--defaults',action='store_true');g.add_argument('--review',action='store_true');a=p.parse_args()
    name='defaults' if a.defaults else 'review';started=time.monotonic();result=dict(passed=False)
    try:result=defaults() if a.defaults else review();print('NATIVE_SHELL_'+name.upper()+'_OK');return 0
    except Exception as error:result['error']=str(error);print('NATIVE_SHELL_VERIFY_FAIL',error);return 1
    finally:
        result.update(elapsed=time.monotonic()-started)
        with (BASE/(name+'-'+uuid.uuid4().hex+'.json')).open('x') as out:json.dump(result,out,indent=2)
if __name__=='__main__':raise SystemExit(main())
