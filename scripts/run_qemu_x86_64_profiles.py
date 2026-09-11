"""Read-only actual profile lifecycle and complete ungranted syscall probes."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,time,uuid
from run_qemu_x86_64_spawn_oom import observed_boot,symbols
from run_qemu_x86_64_requests import exit_address,MECHANISMS
from run_qemu_x86_64_ipc_handoff import REAP
ROOT=Path(__file__).resolve().parents[1]
PARENT=frozenset((9,15,20,22,23,24,30,40,49,50,51,52,53,54,55))
CHILD=frozenset((9,40,50,51,53,58))
LIFE=re.compile(r'PROFILE_LIFE op=(\d+) gen=(\d+) task=([0-9a-f]+) profile=([0-9a-f]+) state=(\d+) live=(\d+) mask=([0-9a-f]+) result=(\d+)')
DENY=re.compile(r'PROFILE_DENY gen=(\d+) number=(\d+)')
def commands(s,log_path):
    # Redirect verbose receipts directly to bounded evidence, not the shared
    # boot helper's small Windows stdout pipe (drained only at guest completion).
    c=f'set logging file {log_path.resolve().as_posix()}\nset logging redirect on\nset logging enabled on\nset $hits = 0\n'
    c+=f'break *{s["reist_x64_profile_apply.return"]:#x} if $rsi == 1 || $rsi == 3\ncommands 1\nsilent\n'
    c+='set $hits = $hits + 1\nif $hits > 512\nquit 2\nend\n'
    c+='printf "PROFILE_LIFE op=%llu gen=%llu task=%llx profile=%llx state=%llu live=%llu mask=%llx result=%llu\\n", $rsi,$r10,$r8,$r9,*(unsigned long long*)$r8,*(unsigned long long*)$r9,*(unsigned long long*)($r9+8),$rax\ncontinue\nend\n'
    c+=f'break *{s["reist_x64_profile_apply.denied"]:#x}\ncommands 2\nsilent\n'
    c+='set $hits = $hits + 1\nif $hits > 512\nquit 2\nend\n'
    c+='printf "PROFILE_DENY gen=%llu number=%llu\\n",$r10,$rbx\ncontinue\nend\n'
    c+=f'break *{s["scheduler_return64"]:#x} if *(unsigned char*){s["scheduler_mode"]:#x} == 7\ncommands 3\nsilent\ndetach\nquit\nend\ncontinue\n'
    return c
def validate(serial,trace,task_base,profile_base,rip):
    life=list(LIFE.finditer(trace));denials=list(DENY.finditer(trace))
    if len(life)!=6 or len(denials)!=444:raise RuntimeError('profile receipt count')
    expected=((1,40),(1,41),(3,41),(1,42),(3,42),(3,40))
    for row,(op,gen) in zip(life,expected):
        a,g,t,p,state,live,mask,result=row.groups()
        t,p,mask=int(t,16),int(p,16),int(mask,16)
        role=0 if gen==40 else 1;bits=PARENT if role==0 else CHILD
        expected_mask=sum(1<<n for n in bits) if op==1 else 0
        if (int(a),int(g),t,p,int(state),int(live),mask,int(result)) != (
            op,gen,task_base+role*256,profile_base+role*16,9 if op==1 else 8 if role else 4,
            gen if op==1 else 0,expected_mask,1):raise RuntimeError('profile binding/publication/revoke')
    for gen,bits,count in ((40,PARENT,4),(41,CHILD,2),(42,CHILD,2)):
        numbers=[int(r[2]) for r in denials if int(r[1])==gen]
        expected_numbers=set(range(64))-bits|{1<<32,(1<<64)-1}
        if set(numbers)!=expected_numbers or any(numbers.count(n)!=count for n in expected_numbers):
            raise RuntimeError('missing/aliased/unexpected denied syscall')
        installed=next(r for r in life if (r[1],r[2])==('1',str(gen)))
        revoked=next(r for r in life if (r[1],r[2])==('3',str(gen)))
        if any(not installed.end()<=r.start()<r.end()<=revoked.start() for r in denials if int(r[1])==gen):
            raise RuntimeError('denial outside owned lifecycle')
    receipts=list(REAP.finditer(serial));runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    done=list(re.finditer('PROFILE_OK',serial))
    if any(len(x)!=2 for x in (receipts,runs,done)) or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:
        raise RuntimeError('profile fixture did not complete normal reap')
    for i,row in enumerate(receipts):
        status,g,parent,q,address=(int(v,16) for v in row.groups())
        if (status,g,q,address)!=(91,41+i,0,rip) or parent not in (1,6,7):raise RuntimeError('terminal profile receipt')
        if not (done[i-1].end() if i else -1)<row.start()<row.end()<=runs[i].start()<runs[i].end()<=done[i].start():
            raise RuntimeError('profile/reap order')
def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    summary=dict(passed=False);start=time.monotonic()
    try:
        with (attempt/'build.log').open('wb') as out:
            build=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-OutputDirectory',attempt.relative_to(ROOT).as_posix(),'-ProfileCase','1'],cwd=ROOT,
                stdout=out,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if build.returncode:raise RuntimeError('build failed: '+str(attempt/'build.log'))
        native=attempt/'x86_64';image=native/'reist-x86_64-bootstrap.elf';s=symbols(image)
        receipt_log=attempt/'profile-trace.log'
        serial,_=observed_boot(image,attempt,commands(s,receipt_log))
        if receipt_log.stat().st_size>128*1024:raise RuntimeError('profile receipt byte limit')
        trace=receipt_log.read_text(encoding='utf-8')
        validate(serial,trace,s['scheduler_tasks'],s['scheduler_syscall_profiles'],exit_address(native))
        summary.update(passed=True,generations=2,denial_observations=444,
            mechanism_sha256={n:hashlib.sha256((native/(n+'.o')).read_bytes()).hexdigest() for n in (*MECHANISMS,'frame_claim','syscall_profile')})
        print('X86_64_PROFILE_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        print('X86_64_PROFILE_RUNTIME_FAIL '+str(e));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-start,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
if __name__=='__main__':raise SystemExit(main())
