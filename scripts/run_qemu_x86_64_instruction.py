"""Real second-page execution, IRQ spin and absent syscall-return containment."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid
from run_qemu_x86_64_boot import resolve_qemu,run_boot
from run_qemu_x86_64_mappings import elf_pages
from run_qemu_x86_64_ipc_handoff import REAP
from run_qemu_x86_64_busy import validate_receipts as validate_cpu
from run_qemu_x86_64_requests import MECHANISMS
ROOT=Path(__file__).resolve().parents[1]

def validate(serial,case,rip):
    runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    done=list(re.finditer('INSTRUCTION_OK',serial))
    if any(len(x)!=2 for x in (runs,done)) or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:
        raise RuntimeError('missing instruction lifecycle witnesses')
    if case==2:
        validate_cpu(serial,0x401000,0x401004)
        receipts=list(re.finditer(r'REIST_X86_64_CHILD_CPU_REAP_OK[^\r\n]*',serial))
    elif case==3:
        receipts=list(re.finditer(r'REIST_X86_64_CHILD_CONTEXT_REAP_OK generation=([0-9A-F]{2}) parent=01 rip=0000000000402000',serial))
        if len(receipts)!=2 or [int(r.group(1),16) for r in receipts]!=[41,42]:raise RuntimeError('absent return context')
    else:
        receipts=list(REAP.finditer(serial))
        if len(receipts)!=2:raise RuntimeError('normal second-page return')
        for i,r in enumerate(receipts):
            status,g,parent,q,ip=(int(x,16) for x in r.groups())
            if (status,g,q,ip)!=(77,41+i,0,rip) or parent not in (1,6,7):raise RuntimeError('normal instruction reap')
    for i,r in enumerate(receipts):
        if not (done[i-1].end() if i else -1)<r.start()<r.end()<=runs[i].start()<runs[i].end()<=done[i].start():
            raise RuntimeError('instruction reap/RUN ordering')

def fixture(native,case):
    pages=elf_pages((native/'reist-x86_64-user-child.elf').read_bytes())
    if set(pages)!={0,1} or [pages[i][0] for i in range(2)]!=[5,5]:raise RuntimeError('expected two RX pages')
    code=pages[1][1]
    prefix=bytes.fromhex('b8280000000f054885c07501c30f0b') if case==1 else bytes.fromhex('f390ebfc')
    if case in (1,2) and code!=prefix+bytes(4096-len(prefix)):raise RuntimeError('second RX instructions differ')
    if case==3:
        if code[:6]!=bytes.fromhex('b828000000e9') or 0x40100a+struct.unpack_from('<i',code,6)[0]!=0x401ffe or code[10:4094]!=bytes(4084) or code[4094:]!=b'\x0f\x05':
            raise RuntimeError('missing page-end syscall to absent return')
    # Entry must really call that separate page, not an unused fixture section.
    calls=list(re.finditer(rb'\xe8....',pages[0][1],re.S))
    if sum(0x400000+r.end()+struct.unpack_from('<i',pages[0][1],r.start()+1)[0]==0x401000 for r in calls)!=1:
        raise RuntimeError('missing actual second-page call')
    exits=list(re.finditer(re.escape(bytes.fromhex('b80900000031f631d20f05')),pages[0][1]))
    if len(exits)!=1:raise RuntimeError('normal EXIT identity')
    return 0x400000+exits[0].end()

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    result=dict(passed=False,cases=[]);start=time.monotonic()
    try:
        for case in (1,2,3):
            folder=attempt/str(case);folder.mkdir()
            with (folder/'build.log').open('wb') as out:
                build=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                    '-OutputDirectory',folder.relative_to(ROOT).as_posix(),'-InstructionCase',str(case)],cwd=ROOT,
                    stdout=out,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if build.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
            native=folder/'x86_64';normal=base.parent/'normal/x86_64'
            names=(*MECHANISMS,'frame_claim','syscall_profile','image_frames','address_space','task_frames','user_access')
            hashes={n:hashlib.sha256((native/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if any(hashes[n]!=hashlib.sha256((normal/(n+'.o')).read_bytes()).hexdigest() for n in names):raise RuntimeError('kernel fixture drift')
            rip=fixture(native,case)
            serial=run_boot(resolve_qemu(None),native/'reist-x86_64-bootstrap.elf',folder/'guest.log',10)
            validate(serial,case,rip)
            result['cases'].append(dict(case=case,passed=True,exit_rip=hex(rip)))
            print('X86_64_INSTRUCTION_CASE_OK case='+str(case),flush=True)
        result.update(passed=True,generations=6,mechanism_sha256=hashes)
        print('X86_64_INSTRUCTION_RUNTIME_OK cases=3 generations=6 evidence='+str(attempt));return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired,struct.error) as e:
        print('X86_64_INSTRUCTION_RUNTIME_FAIL '+str(e));return 1
    finally:
        result['elapsed']=round(time.monotonic()-start,3)
        (attempt/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
if __name__=='__main__':raise SystemExit(main())
