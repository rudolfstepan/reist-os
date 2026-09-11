"""Normal child exit across every existing IPC ownership phase, real ELF code."""
from pathlib import Path
import argparse
import json
import re
import struct
import subprocess
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu, run_boot

ROOT=Path(__file__).resolve().parents[1]
STATUSES=(0,77,128,256,258,0xffffffff)
MARKER='REIST_X86_64_CHILD_EXIT_REAP_OK'
RUN='REIST_X86_64_RING3_SHELL_RUN_OK'
RECEIPT=re.compile(MARKER+r' status=([0-9A-F]{8}) generation=([0-9A-F]{2})'
    r' parent=([0-9A-F]{2}) queued=([0-9A-F]{2}) rip=([0-9A-F]{16})\r?\n')


def fixture_bytes(status):
    return bytes.fromhex('48bf4d00000001000000b8090000000f054883f8ea7536'
        '48bf1032547698badcfe48be444433332222111148ba8888777766665555'
        'b8280000000f054885c0750cbf')+struct.pack('<I',status)+bytes.fromhex('b8090000000f050f0b')


def validate_instructions(code,symbols,status):
    start=symbols['child_exit_probe']
    expected=fixture_bytes(status)
    if code[start:start+len(expected)]!=expected or symbols['child_exit_instruction']!=start+75 or \
            symbols['child_exit_return']!=start+77 or symbols['child_exit_fail']!=start+77:
        raise RuntimeError('missing wide EXIT/EINVAL, noisy YIELD/result or terminal EXIT instructions')
    return start+77


def exit_address(folder,status):
    obj=(folder/'user_child.o').read_bytes()
    linked=(folder/'reist-x86_64-user-child.elf').read_bytes()
    def sections(data):
        if not 64<=len(data)<=65536 or data[:6]!=b'\x7fELF\x02\x01':
            raise RuntimeError('invalid ELF64')
        offset=struct.unpack_from('<Q',data,40)[0]
        size,count=struct.unpack_from('<HH',data,58)
        if size!=64 or not 0<count<=64 or offset+size*count>len(data):
            raise RuntimeError('invalid section bounds')
        table=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
        if any(s[1]!=8 and s[4]+s[5]>len(data) for s in table):
            raise RuntimeError('section outside ELF')
        return table
    table=sections(obj)
    text=[s for s in table if s[1]==1 and s[2]&4]
    executable=[s for s in sections(linked) if s[1]==1 and s[2]&4]
    if len(text)!=1 or len(executable)!=1 or text[0][5]!=executable[0][5]:
        raise RuntimeError('unexpected executable layout')
    text,executable=text[0],executable[0]
    symbols={}
    for sec in table:
        if sec[1]!=2:continue
        if sec[6]>=len(table) or sec[9]!=24 or sec[5]%24:
            raise RuntimeError('invalid symbol table')
        strings=table[sec[6]]
        names=obj[strings[4]:strings[4]+strings[5]]
        for offset in range(sec[4],sec[4]+sec[5],24):
            name,_,_,index,value,_=struct.unpack_from('<IBBHQQ',obj,offset)
            if name>=len(names) or b'\0' not in names[name:]:
                raise RuntimeError('invalid symbol name')
            label=names[name:].split(b'\0',1)[0].decode('ascii')
            if not label.startswith('child_exit_'):continue
            if label in symbols or index>=len(table) or table[index]!=text or value>text[5]:
                raise RuntimeError('duplicate/invalid exit symbol')
            symbols[label]=value
    code=obj[text[4]:text[4]+text[5]]
    linked_code=linked[executable[4]:executable[4]+executable[5]]
    relative=validate_instructions(code,symbols,status)
    if validate_instructions(linked_code,symbols,status)!=relative:
        raise RuntimeError('linked exit proof differs')
    return executable[3]+relative


def validate_receipts(text,status,phase,rip):
    receipts=list(RECEIPT.finditer(text));runs=list(re.finditer(RUN,text))
    if len(re.findall(r'REIST_X86_64_CHILD_[A-Z]+_REAP_OK',text))!=2 or len(receipts)!=2 or len(runs)!=2:
        raise RuntimeError('expected two normal terminal and RUN receipts, no fault/quota alias')
    for i,receipt in enumerate(receipts):
        fields=tuple(int(v,16) for v in receipt.groups())
        if fields!=(status,41+i,(1,1,6,7)[phase],int(phase==1),rip):
            raise RuntimeError('wrong raw status, identity, IPC state or instruction address: '+str(fields))
        if not (runs[i-1].end() if i else -1)<receipt.start()<receipt.end()<=runs[i].start():
            raise RuntimeError('normal reap must precede matching WAIT/RUN')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    summary=dict(passed=False,cases=[]);started=time.monotonic()
    try:
        for status in STATUSES:
            for phase in range(4):
                folder=attempt/f's{status}-p{phase}';folder.mkdir()
                command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    'scripts/build-x86_64-bootstrap.ps1','-OutputDirectory',folder.relative_to(ROOT).as_posix(),
                    '-ExitStatus',str(status),'-FaultPhase',str(phase)]
                with (folder/'build.log').open('wb') as output:
                    result=subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
                        timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
                native=folder/'x86_64';rip=exit_address(native,status)
                text=run_boot(resolve_qemu(None),native/'reist-x86_64-bootstrap.elf',folder/'guest.log',10)
                validate_receipts(text,status,phase,rip)
                summary['cases'].append(dict(status=status,phase=phase,rip=hex(rip),passed=True))
                print(f'X86_64_EXIT_CASE_OK status={status} phase={phase}',flush=True)
        summary.update(passed=True,generations=48)
        print('X86_64_EXIT_RUNTIME_OK cases=24 generations=48 evidence='+str(attempt))
        return 0
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.TimeoutExpired,struct.error) as exc:
        print('X86_64_EXIT_RUNTIME_FAIL '+str(exc));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
