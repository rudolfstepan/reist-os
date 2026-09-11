"""Read-only witness of independent staged image lifetimes, not process parity."""
from pathlib import Path
import argparse,hashlib,itertools,json,re,struct,subprocess,time,uuid
from run_qemu_x86_64_spawn_oom import symbols,observed_boot
from run_qemu_x86_64_requests import MECHANISMS
from run_qemu_x86_64_ipc_handoff import REAP
ROOT=Path(__file__).resolve().parents[1]
ROUND='REIST_X86_64_IMAGE_CONTEXT_ROUND_OK'
DONE='REIST_X86_64_IMAGE_CONTEXTS_OK'
ROW=re.compile(r'IMAGE_RELEASE round=(\d+) cursor=(\d+) image=(\d+) before=(\d+) freed=(\d+) after=(\d+) load=(\d+) held=(\d+) result=(\d+) active=(\d+)')

def exit_address(folder):
    # Normal (IPC0) child exits77; do not borrow the IPC1 fixture's EXIT91 RIP.
    data=(folder/'reist-x86_64-user-child.elf').read_bytes()
    if not 64<=len(data)<=4096 or data[:6]!=b'\x7fELF\x02\x01':raise RuntimeError('invalid child ELF64')
    ph=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
    if size!=56 or not 1<=count<=4 or ph+size*count>len(data):raise RuntimeError('invalid program headers')
    packet=bytes.fromhex('b80900000031f631d20f05');candidates=[]
    for i in range(count):
        kind,flags,offset,address,_,length,_,_=struct.unpack_from('<IIQQQQQQ',data,ph+i*size)
        if kind!=1 or not flags&1:continue
        if offset+length>len(data):raise RuntimeError('invalid executable bounds')
        for hit in re.finditer(re.escape(packet),data[offset:offset+length]):
            candidates.append(address+hit.start()+len(packet))
    if len(candidates)!=1:raise RuntimeError('missing unique normal EXIT instruction')
    return candidates[0]

def commands(s,log):
    def at(name,kind='unsigned char'):return f'*({kind}*){s[name]:#x}'
    active=at('elf_context_selftest_active')
    c=f'set logging file {log.resolve().as_posix()}\nset logging redirect on\nset logging enabled on\nset $hits = 0\n'
    c+=f'break *{s["reist_x64_image_release"]:#x} if {active} == 1\ncommands 1\nsilent\n'
    c+='set $hits = $hits+1\nif $hits > 18 || ($eflags & 512) != 0\nquit 2\nend\n'
    c+=f'set $before = {at("free_frame_count","unsigned int")}\nset $load = *(unsigned int*)($rdi+72)\n'
    c+='set $owned = 0\nset $i = 0\nwhile $i < 8\nif *(unsigned long long*)($rdi+$i*8) != 0\nset $owned = $owned+1\nend\nset $i = $i+1\nend\ncontinue\nend\n'
    c+=f'break *{s["reist_x64_image_release.return"]:#x} if {active} == 1\ncommands 2\nsilent\n'
    c+='if $rax != 1 || $r14 != $owned\nquit 3\nend\nset $i = 0\n'
    c+='while $i < 8\nif *(unsigned long long*)($r12+$i*8) != 0 || *(unsigned char*)($r12+64+$i) != 0\nquit 4\nend\nset $i = $i+1\nend\n'
    c+='if *(unsigned int*)($r12+76) != 0 || *(unsigned long long*)($r12+80) != 0\nquit 5\nend\n'
    c+='printf "IMAGE_RELEASE round=%u cursor=%u image=%u before=%u freed=%u after=%u load=%u held=%llu result=%u active=%u\\n", '
    c+=', '.join([at('elf_context_selftest_round'),at('elf_context_selftest_cursor'),at('elf_image_selector'),
        '$before','$owned',at('free_frame_count','unsigned int'),'$load',at('elf_context_selftest_held','unsigned long long'),
        '$rax','*(unsigned char*)($r12+79)'])+'\ncontinue\nend\n'
    c+=f'break *{s["scheduler_return64"]:#x} if {at("scheduler_mode")} == 7\ncommands 3\nsilent\ndetach\nquit\nend\ncontinue\n'
    return c

def validate(serial,trace,rip):
    rows=list(ROW.finditer(trace));rounds=list(re.finditer(ROUND,serial));done=list(re.finditer(DONE,serial))
    if len(rows)!=18 or len(rounds)!=6 or len(done)!=1:raise RuntimeError('image receipt count')
    if not rounds[-1].end()<=done[0].start()<done[0].end()<=serial.find('REIST_X86_64_ELF64_LOAD_OK'):
        raise RuntimeError('image selftest must precede normal ELF execution')
    for round_id,order in enumerate(itertools.permutations(range(3))):
        previous=None;held_frame=None
        for cursor,image in enumerate(order):
            r,c,im,before,freed,after,load,held,result,active=map(int,rows[round_id*3+cursor].groups())
            if (r,c,im,result,active)!=(round_id,cursor,image,1,0):raise RuntimeError('image release order/state')
            if not (0<before<after<=32768 and 1<=freed<=8 and after==before+freed and 0<load<=32768):
                raise RuntimeError('image release delta')
            if not (0<held<0x08000000 and held%4096==0):raise RuntimeError('held frame')
            if previous is not None and (before!=previous or held!=held_frame):raise RuntimeError('owner continuity')
            if image==0 and after==load:raise RuntimeError('old load-baseline dependency not exercised')
            previous=after;held_frame=held
    receipts=list(REAP.finditer(serial));runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    if len(receipts)!=2 or len(runs)!=2 or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:
        raise RuntimeError('normal image process reaping missing')
    for i,row in enumerate(receipts):
        status,g,parent,q,address=(int(v,16) for v in row.groups())
        if (status,g,q,address)!=(77,41+i,0,rip) or parent not in (1,6,7):raise RuntimeError('terminal image witness')
        if not (runs[i-1].end() if i else done[0].end())<row.start()<row.end()<=runs[i].start():
            raise RuntimeError('normal reap/run order')

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();image=args.image.resolve();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent') or not image.is_relative_to(ROOT/'build/codex-agent'):
        p.error('image/evidence outside workspace evidence root')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    summary=dict(passed=False);start=time.monotonic()
    try:
        s=symbols(image);log=attempt/'image-trace.log'
        serial,_=observed_boot(image,attempt,commands(s,log))
        if log.stat().st_size>32*1024:raise RuntimeError('image receipt byte limit')
        validate(serial,log.read_text(encoding='utf-8'),exit_address(image.parent))
        summary.update(passed=True,permutations=6,releases=18,
            mechanism_sha256={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest()
                for n in (*MECHANISMS,'frame_claim','syscall_profile','image_frames')})
        print('X86_64_IMAGE_CONTEXTS_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        print('X86_64_IMAGE_CONTEXTS_RUNTIME_FAIL '+str(e));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-start,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
if __name__=='__main__':raise SystemExit(main())
