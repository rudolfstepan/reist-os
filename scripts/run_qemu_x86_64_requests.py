"""Actual bounded shell request failures followed by IPC, WAIT and full reap."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import subprocess
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu, run_boot
from run_qemu_x86_64_ipc_handoff import REAP
ROOT=Path(__file__).resolve().parents[1]
MECHANISMS=('cooperative_scheduler','request_admission','startup_stack','ipc_admission',
    'timer_interrupt','queue_core','context_core','identity_core','cpu_budget','fp_context',
    'user_fault','terminal_status','physical_memory','user_execution','exceptions')


def exit_address(folder):
    data=(folder/'reist-x86_64-user-child.elf').read_bytes()
    packet=bytes.fromhex('bf5b000000b8090000000f050f0b')
    if not 64<=len(data)<=4096 or data[:6]!=b'\x7fELF\x02\x01':
        raise RuntimeError('invalid child ELF64')
    ph=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54)
    if size!=56 or not 1<=count<=4 or ph+count*size>len(data):raise RuntimeError('invalid ELF program headers')
    candidates=[]
    for i in range(count):
        kind,flags,offset,address,_,length,_,_=struct.unpack_from('<IIQQQQQQ',data,ph+i*size)
        if kind!=1 or not flags&1:continue
        if offset+length>len(data):raise RuntimeError('invalid executable bounds')
        code=data[offset:offset+length]
        for hit in re.finditer(re.escape(packet),code):candidates.append(address+hit.start()+12)
    if len(candidates)!=1:raise RuntimeError('missing unique real EXIT91 instruction')
    return candidates[0]


def validate(serial,case,rip):
    marker='REQUEST_'+str(case)+'_OK'
    done=list(re.finditer(marker,serial));runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    receipts=list(REAP.finditer(serial))
    if len(done)!=2 or len(runs)!=2 or len(receipts)!=2 or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:
        raise RuntimeError('missing exact request/normal-reap/RUN witnesses')
    for i,row in enumerate(receipts):
        status,generation,parent,queued,address=(int(v,16) for v in row.groups())
        if (status,generation,queued,address)!=(91,41+i,0,rip) or parent not in (1,6,7):
            raise RuntimeError('invalid request-fixture terminal receipt')
        if not (done[i-1].end() if i else -1)<row.start()<row.end()<=runs[i].start()<runs[i].end()<=done[i].start():
            raise RuntimeError('request success must follow the matching reap and RUN')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    summary=dict(passed=False,cases=[]);started=time.monotonic();expected=None
    try:
        for case in (1,2,3):
            folder=attempt/str(case);folder.mkdir()
            command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-OutputDirectory',folder.relative_to(ROOT).as_posix(),'-RequestCase',str(case)]
            with (folder/'build.log').open('wb') as out:
                result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=90,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
            native=folder/'x86_64'
            hashes={name:hashlib.sha256((native/(name+'.o')).read_bytes()).hexdigest() for name in MECHANISMS}
            if expected is not None and expected!=hashes:raise RuntimeError('kernel mechanisms differ across fixtures')
            expected=hashes
            if ('REQUEST_'+str(case)+'_OK').encode() not in (native/'reist-x86_64-user-shell.elf').read_bytes():
                raise RuntimeError('request fixture missing from actual ELF')
            rip=exit_address(native)
            serial=run_boot(resolve_qemu(None),native/'reist-x86_64-bootstrap.elf',folder/'guest.log',10)
            validate(serial,case,rip)
            summary['cases'].append(dict(case=case,passed=True,rip=hex(rip)))
            print('X86_64_REQUEST_CASE_OK case='+str(case),flush=True)
        summary.update(passed=True,generations=6,mechanism_sha256=expected)
        print('X86_64_REQUEST_RUNTIME_OK cases=3 generations=6 evidence='+str(attempt));return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired,struct.error) as exc:
        print('X86_64_REQUEST_RUNTIME_FAIL '+str(exc));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
