"""Actual syscall-free ELF64 spin: IRQ parent progress, budget and two reaps."""
from pathlib import Path
import argparse
import json
import re
import struct
import subprocess
import time
import uuid
from run_qemu_x86_64_boot import resolve_qemu,run_boot
ROOT=Path(__file__).resolve().parents[1]
MARKER='REIST_X86_64_CHILD_CPU_REAP_OK'
STACK_MARKER='REIST_X86_64_CHILD_STACK_REAP_OK'
RUN='REIST_X86_64_RING3_SHELL_RUN_OK'
RECEIPT=re.compile(MARKER+r' generation=([0-9A-F]{2}) ticks=([0-9A-F]{2}) parent=([0-9A-F]{2}) rip=([0-9A-F]{16})\r?\n')
STACK_RECEIPT=re.compile(STACK_MARKER+r' generation=([0-9A-F]{2}) parent=([0-9A-F]{2}) rip=([0-9A-F]{16})\r?\n')


def validate_receipts(text,low,high,invalid_stack=False):
    marker,other,pattern=(STACK_MARKER,MARKER,STACK_RECEIPT) if invalid_stack else (MARKER,STACK_MARKER,RECEIPT)
    receipts=list(pattern.finditer(text));runs=list(re.finditer(RUN,text))
    if text.count(marker)!=2 or other in text or len(receipts)!=2 or len(runs)!=2:
        raise RuntimeError('expected two CPU retirement and RUN receipts')
    for i,r in enumerate(receipts):
        fields=tuple(int(v,16) for v in r.groups())
        expected=(41+i,1) if invalid_stack else (41+i,32,7)
        rip=fields[-1]
        if fields[:-1]!=expected or not low<=rip<high or rip not in (low,low+2):
            raise RuntimeError('wrong identity, budget, parent or instruction address')
        if not (runs[i-1].end() if i else -1)<r.start()<r.end()<=runs[i].start():
            raise RuntimeError('reap must precede matching WAIT/RUN')


def loop_bounds(folder,invalid_stack=False):
    obj=(folder/'user_child.o').read_bytes()
    linked=(folder/'reist-x86_64-user-child.elf').read_bytes()
    def sections(data):
        if not 64<=len(data)<=65536 or data[:6]!=b'\x7fELF\x02\x01':
            raise RuntimeError('invalid ELF64 fixture')
        off=struct.unpack_from('<Q',data,40)[0]
        size,count=struct.unpack_from('<HH',data,58)
        if size!=64 or not 0<count<=64 or off+size*count>len(data):
            raise RuntimeError('invalid section bounds')
        return [struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
    table=sections(obj);found={}
    for sec in table:
        if sec[1]!=2:continue
        if sec[6]>=len(table) or sec[9]!=24 or sec[5]%24 or sec[4]+sec[5]>len(obj):
            raise RuntimeError('invalid symbols')
        strings=table[sec[6]]
        if strings[4]+strings[5]>len(obj):raise RuntimeError('invalid strings')
        names=obj[strings[4]:strings[4]+strings[5]]
        for offset in range(sec[4],sec[4]+sec[5],24):
            name,_,_,index,value,_=struct.unpack_from('<IBBHQQ',obj,offset)
            label=names[name:].split(b'\0',1)[0]
            if label not in (b'child_cpu_spin',b'child_cpu_spin_end',b'child_cpu_poison_stack'):continue
            if label in found or index>=len(table):raise RuntimeError('duplicate/invalid loop symbol')
            found[label]=(index,value)
    low=found[b'child_cpu_spin'];high=found[b'child_cpu_spin_end']
    if low[0]!=high[0] or high[1]-low[1]!=4:raise RuntimeError('invalid loop range')
    code=table[low[0]]
    text=[s for s in sections(linked) if s[1]==1 and s[2]&4]
    if len(text)!=1 or text[0][5]!=code[5]:raise RuntimeError('unexpected linked text')
    instructions=b'\xf3\x90\xeb\xfc'
    if obj[code[4]+low[1]:code[4]+high[1]]!=instructions or linked[text[0][4]+low[1]:text[0][4]+high[1]]!=instructions:
        raise RuntimeError('fixture is not the syscall-free PAUSE/JMP loop')
    if invalid_stack:
        index,value=found[b'child_cpu_poison_stack']
        if index!=low[0] or value+7>low[1]:raise RuntimeError('invalid stack-poison entry')
        for data,offset in ((obj,code[4]),(linked,text[0][4])):
            ins=data[offset+value:offset+value+7]
            if len(ins)!=7 or ins[:3]!=b'\x31\xe4\xe9' or value+7+struct.unpack_from('<i',ins,3)[0]!=low[1]:
                raise RuntimeError('missing XOR ESP,ESP and direct branch into loop')
    elif b'child_cpu_poison_stack' in found:raise RuntimeError('unexpected stack poison in CPU fixture')
    return text[0][3]+low[1],text[0][3]+high[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence outside workspace')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();summary={'passed':False,'cases':[]}
    try:
        for invalid_stack in (False,True):
            case=folder/('bad-stack' if invalid_stack else 'cpu');case.mkdir()
            command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                     'scripts/build-x86_64-bootstrap.ps1','-OutputDirectory',case.relative_to(ROOT).as_posix(),'-BusyChild']
            if invalid_stack:command.append('-InvalidBusyStack')
            with (case/'build.log').open('wb') as log:
                result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                    timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode:raise RuntimeError('busy build failed; see '+str(case/'build.log'))
            native=case/'x86_64';low,high=loop_bounds(native,invalid_stack)
            captured=run_boot(resolve_qemu(None),native/'reist-x86_64-bootstrap.elf',case/'guest.log',10)
            validate_receipts(captured,low,high,invalid_stack)
            summary['cases'].append(dict(passed=True,invalid_stack=invalid_stack,loop=[hex(low),hex(high)]))
        summary.update(passed=True,generations=4,budget=32)
        print('X86_64_BUSY_RUNTIME_OK cases=2 generations=4 budget=32 evidence='+str(folder))
        return 0
    except (OSError,KeyError,ValueError,RuntimeError,subprocess.TimeoutExpired,struct.error) as exc:
        print('X86_64_BUSY_RUNTIME_FAIL '+str(exc));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
