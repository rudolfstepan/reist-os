"""Read-only receipts of every normal native task-frame release and FP scrub."""
from pathlib import Path
import argparse, json, re, time, uuid
from run_qemu_x86_64_spawn_oom import observed_boot, symbols
from run_qemu_x86_64_image_contexts import exit_address
from run_qemu_x86_64_ipc_handoff import REAP
ROOT=Path(__file__).resolve().parents[1]
BEFORE=re.compile(r'TASK_FRAMES_BEFORE seq=(\d+) mode=(\d+) slot=(\d+) gen=(\d+) state=(\d+) root=([0-9a-f]+) active=([0-9a-f]+) before=(\d+) fp=(\d+) frames=([0-9a-f,]+)')
FREE=re.compile(r'TASK_FRAMES_FREE seq=(\d+) frame=([0-9a-f]+)')
AFTER=re.compile(r'TASK_FRAMES_AFTER seq=(\d+) gen=(\d+) state=(\d+) result=(\d+) after=(\d+) zero=(\d+)')


def commands(s,log):
    def at(name,kind='unsigned char'):return f'*({kind}*){s[name]:#x}'
    c=f'set logging file {log.resolve().as_posix()}\nset logging redirect on\nset logging enabled on\nset $seq=0\nset $inside=0\n'
    c+=f'break *{s["scheduler_release_task_frames64"]:#x}\ncommands 1\nsilent\n'
    c+='if $inside || $seq>=20 || ($eflags&512)!=0\nquit 2\nend\nset $inside=1\nset $seq=$seq+1\nset $task=$r12\n'
    c+=f'set $slot=($task-{s["scheduler_tasks"]:#x})/256\nset $tables={s["scheduler_table_frames"]:#x}+$slot*32\nset $task_fp={s["scheduler_fp_states"]:#x}+$slot*512\n'
    c+='set $fp_nonzero=0\nset $i=0\nwhile $i<64\nif *(unsigned long long*)($task_fp+$i*8)!=0\nset $fp_nonzero=1\nend\nset $i=$i+1\nend\n'
    c+='printf "TASK_FRAMES_BEFORE seq=%u mode=%u slot=%u gen=%u state=%u root=%llx active=%llx before=%u fp=%u frames=",'
    c+=','.join(('$seq',at('scheduler_mode'),'$slot','*(unsigned long long*)($task+8)','*(unsigned long long*)$task',
                 '*(unsigned long long*)($task+16)','$cr3',at('free_frame_count','unsigned int'),'$fp_nonzero'))+'\n'
    addresses=[f'$task+{32+i*8}' for i in range(8)]+['$task+24']+[f'$tables+{i*8}' for i in (3,2,1,0)]
    c+='printf "'+','.join(['%llx']*13)+'\\n",'+','.join('*(unsigned long long*)('+a+')' for a in addresses)+'\nenable 2\ncontinue\nend\n'
    c+=f'break *{s["physical_frame_free64"]:#x}\ncommands 2\nsilent\n'
    c+='if !$inside\nquit 3\nend\nprintf "TASK_FRAMES_FREE seq=%u frame=%llx\\n",$seq,$rdi\ncontinue\nend\ndisable 2\n'
    c+=f'break *{s["scheduler_release_task_frames64.return"]:#x}\ncommands 3\nsilent\n'
    c+='if !$inside || ($eflags&512)!=0\nquit 4\nend\ndisable 2\nset $zero=1\n'
    for address in addresses+['$task+16']:
        c+=f'if *(unsigned long long*)({address})!=0\nset $zero=0\nend\n'
    c+='set $i=0\nwhile $i<64\nif *(unsigned long long*)($task_fp+$i*8)!=0\nset $zero=0\nend\nset $i=$i+1\nend\n'
    c+='printf "TASK_FRAMES_AFTER seq=%u gen=%u state=%u result=%u after=%u zero=%u\\n",$seq,*(unsigned long long*)($task+8),*(unsigned long long*)$task,$rax,'+at('free_frame_count','unsigned int')+',$zero\nset $inside=0\ncontinue\nend\n'
    c+=f'break *{s["scheduler_return64"]:#x} if {at("scheduler_mode")} == 7\ncommands 4\nsilent\nif $inside\nquit 5\nend\ndetach\nquit\nend\ncontinue\n'
    return c


def validate(serial,trace,rip):
    starts=list(BEFORE.finditer(trace));ends=list(AFTER.finditer(trace));frees=list(FREE.finditer(trace))
    if len(starts)!=20 or len(ends)!=20 or len(frees)>260:raise RuntimeError('release receipt count')
    expected={(m,slot,1+slot):(4 if slot==0 else 3 if m==1 else 5)
              for m in (1,2,3) for slot in (0,1)}
    expected.update({(4,slot,10+slot):(3 if slot==3 else 4) for slot in range(4)})
    expected.update({(5,slot,20+slot):4 for slot in range(4)})
    expected.update({(6,0,30):4,(6,1,31):8,(6,1,32):8,(7,0,40):4,(7,1,41):8,(7,1,42):8})
    seen=set();consumed=0
    for i,(start,end) in enumerate(zip(starts,ends)):
        seq,mode,slot,gen,state,root,active,before,fp,frames=start.groups()
        seq,mode,slot,gen,state,before,fp=map(int,(seq,mode,slot,gen,state,before,fp))
        root,active=int(root,16),int(active,16);frames=[int(f,16) for f in frames.split(',')]
        if seq!=i+1 or (mode,slot,gen) in seen or expected.get((mode,slot,gen))!=state or fp!=1:
            raise RuntimeError('release task identity/state/FP')
        seen.add((mode,slot,gen))
        if len(frames)!=13:raise RuntimeError('frame record count')
        owned=[f for f in frames if f]
        if len(set(owned))!=len(owned) or any(not 0<f<0x8000000 or f%4096 for f in owned):raise RuntimeError('frame ownership')
        if not root or root!=frames[-1] or root==active or not 0<active<0x8000000 or active%4096:
            raise RuntimeError('active address-space/root lifetime')
        row=tuple(map(int,end.groups()))
        if row!=(seq,gen,state,1,before+len(owned),1) or not 0<before<row[4]<=32768:
            raise RuntimeError('release balance/metadata/FP cleanup')
        if not (ends[i-1].end() if i else -1)<start.start()<start.end()<end.start():raise RuntimeError('release ordering')
        calls=[f for f in frees if start.end()<=f.start()<end.start()]
        consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(seq,f) for f in owned]:raise RuntimeError('actual free ownership/order')
    if consumed!=len(frees) or seen!=set(expected):raise RuntimeError('unowned free or missing release')
    receipts=list(REAP.finditer(serial));runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    if len(receipts)!=2 or len(runs)!=2 or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:raise RuntimeError('normal reap count')
    for i,r in enumerate(receipts):
        status,gen,parent,queued,address=(int(v,16) for v in r.groups())
        if (status,gen,queued,address)!=(77,41+i,0,rip) or parent not in (1,6,7):raise RuntimeError('normal child completion')
        if not (runs[i-1].end() if i else -1)<r.start()<r.end()<=runs[i].start():raise RuntimeError('parent progress')


def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();base=args.evidence.resolve();image=args.image.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True);start=time.monotonic();summary=dict(passed=False)
    try:
        s=symbols(image);rip=exit_address(image.parent);log=folder/'retirement-trace.log'
        serial,_=observed_boot(image,folder,commands(s,log))
        if log.stat().st_size>65536:raise RuntimeError('bounded retirement trace exceeded')
        validate(serial,log.read_text(encoding='utf-8'),rip)
        summary.update(passed=True,releases=20,child_generations=2)
        print('X86_64_TASK_FRAMES_RUNTIME_OK evidence='+str(folder));return 0
    except (OSError,RuntimeError,ValueError,KeyError) as e:
        print('X86_64_TASK_FRAMES_RUNTIME_FAIL '+str(e));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-start,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')

if __name__=='__main__':raise SystemExit(main())
