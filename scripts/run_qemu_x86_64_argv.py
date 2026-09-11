"""Real native startup-data checks, negative SPAWNV admission and exact reaps."""
from pathlib import Path
import argparse
import json
import struct
import subprocess
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu,run_boot
from run_qemu_x86_64_exit import validate_receipts
ROOT=Path(__file__).resolve().parents[1]
SIZES={1:96,2:144,3:1152,4:128}


def validate_exit_code(code,symbols,case):
    probe=symbols['child_argv_probe'];offset=symbols['child_argv_exit_instruction']
    prefix=b'\x48\x81\xfc'+struct.pack('<I',0x409000-SIZES[case])
    packet=b'\xbf'+struct.pack('<I',90+case)+bytes.fromhex('b8090000000f050f0b')
    if code[probe:probe+7]!=prefix or offset<probe+17 or code[offset-10:offset+4]!=packet or \
            symbols['child_argv_exit_return']!=offset+2 or symbols['child_argv_fail']!=offset+2:
        raise RuntimeError('missing actual stack/result/EXIT fixture instructions')
    return offset+2


def exit_address(folder,case):
    obj=(folder/'user_child.o').read_bytes();linked=(folder/'reist-x86_64-user-child.elf').read_bytes()
    def sections(data):
        if not 64<=len(data)<=65536 or data[:6]!=b'\x7fELF\x02\x01':raise RuntimeError('invalid ELF64')
        offset=struct.unpack_from('<Q',data,40)[0];size,count=struct.unpack_from('<HH',data,58)
        if size!=64 or not 0<count<=64 or offset+size*count>len(data):raise RuntimeError('invalid sections')
        table=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
        if any(s[1]!=8 and s[4]+s[5]>len(data) for s in table):raise RuntimeError('section outside file')
        return table
    table=sections(obj)
    code=[s for s in table if s[1]==1 and s[2]&4];text=[s for s in sections(linked) if s[1]==1 and s[2]&4]
    if len(code)!=1 or len(text)!=1 or code[0][5]!=text[0][5]:raise RuntimeError('invalid executable layout')
    code,text=code[0],text[0];symbols={}
    for sec in table:
        if sec[1]!=2:continue
        if sec[6]>=len(table) or sec[9]!=24 or sec[5]%24:raise RuntimeError('invalid symbol table')
        strings=table[sec[6]];names=obj[strings[4]:strings[4]+strings[5]]
        for offset in range(sec[4],sec[4]+sec[5],24):
            name,_,_,index,value,_=struct.unpack_from('<IBBHQQ',obj,offset)
            if name>=len(names) or b'\0' not in names[name:]:raise RuntimeError('invalid symbol name')
            label=names[name:].split(b'\0',1)[0].decode('ascii')
            if not label.startswith('child_argv_'):continue
            if label in symbols or index>=len(table) or table[index]!=code or value>code[5]:
                raise RuntimeError('duplicate/invalid fixture symbol')
            symbols[label]=value
    offset=validate_exit_code(obj[code[4]:code[4]+code[5]],symbols,case)
    if validate_exit_code(linked[text[4]:text[4]+text[5]],symbols,case)!=offset:
        raise RuntimeError('object/linked fixture mismatch')
    return text[3]+offset


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    summary=dict(passed=False,cases=[]);started=time.monotonic()
    try:
        for case in range(1,5):
            folder=attempt/str(case);folder.mkdir()
            command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                'scripts/build-x86_64-bootstrap.ps1','-OutputDirectory',folder.relative_to(ROOT).as_posix(),'-ArgvCase',str(case)]
            with (folder/'build.log').open('wb') as output:
                result=subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,timeout=90,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
            native=folder/'x86_64';rip=exit_address(native,case)
            captured=run_boot(resolve_qemu(None),native/'reist-x86_64-bootstrap.elf',folder/'guest.log',10)
            validate_receipts(captured,90+case,0,rip)
            summary['cases'].append(dict(case=case,passed=True,argc=(0,3,8,2)[case-1],rip=hex(rip)))
            print('X86_64_ARGV_CASE_OK case='+str(case),flush=True)
        summary.update(passed=True,generations=8)
        print('X86_64_ARGV_RUNTIME_OK cases=4 generations=8 evidence='+str(attempt));return 0
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.TimeoutExpired,struct.error) as exc:
        print('X86_64_ARGV_RUNTIME_FAIL '+str(exc));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
