"""Read-only observation of shared native C integrity and its bounded faults."""
from pathlib import Path
import argparse, hashlib, json, re, time, uuid
import build_x86_64_c_payload as payload
from run_qemu_x86_64_c_payload import capture, REQUIRED_MARKERS, FAILURES

ROOT=Path(__file__).resolve().parents[1]
MARKER='REIST_X86_64_C_INTEGRITY_OK'
COUNTS=(1,1561,1641,1642,1643,1644,1645,1646,1647,1648,1649,1650)
RESULTS=(0,1,2,-1,-1,-2,-1,-1,-1,-1,0,0)
# GDB may expose a GPR as signed long while RIP/RSP are pointer typed.
REGISTER_READER="def reg(name):return int(gdb.parse_and_eval('$'+name)) & 0xffffffffffffffff"


def expected_trace(bss):
    lines=['C_INTEGRITY_CALL operation=read result=0 if=0 stack=1']
    for phase,(count,result) in enumerate(zip(COUNTS,RESULTS),1):
        if phase==9:lines.append('C_INTEGRITY_CALL operation=update result=-1 if=0 stack=1')
        lines.append(f'C_INTEGRITY_PHASE phase={phase} result={result} count={count} lock={int(phase==10)} if=0')
    lines.append(f'C_INTEGRITY_ZERO bytes={bss} if=0')
    return lines


def validate(serial,trace,bss):
    if len(serial)>262144 or len(trace)>65536:raise ValueError('evidence capacity')
    if any(m in serial for m in FAILURES):raise ValueError('guest failure')
    positions=[serial.find(m) for m in REQUIRED_MARKERS]
    if min(positions)<0 or positions!=sorted(set(positions)):raise ValueError('legacy proof/order missing')
    for m in REQUIRED_MARKERS:
        if serial.count(m)!=(2 if m=='REIST_X86_64_RING3_SHELL_RUN_OK' else 1):raise ValueError('legacy marker count')
    if serial.count(MARKER)!=1 or not serial.index('REIST_X86_64_EXCEPTION_RECOVERY_OK')<serial.index(MARKER)<serial.index('REIST_X86_64_C_CALLBACK_OK'):
        raise ValueError('shared C execution missing')
    if [line for line in trace.splitlines() if line.startswith('C_INTEGRITY_')]!=expected_trace(bss):
        raise ValueError('exact native integrity/IRQ/cleanup observations missing')


def commands(c,o):
    s={n:v['value'] for n,v in c['symbols'].items()}
    outer={n:v['value']+payload.HIGH for n,v in o['symbols'].items()}
    text=c['sections']['.text'];bss=c['sections']['.bss']
    for name in ('critical_object_init','critical_object_read','critical_object_update','reist_x64_integrity_checkpoint'):
        symbol=c['symbols'][name]
        payload.require(symbol['index']==text['index'] and symbol['type']==2 and symbol['size']>0 and
                        text['address']<=symbol['value']<symbol['value']+symbol['size']<=text['address']+text['size'],'integrity code binding')
    for name,size in (('specimen',212),('input',64),('output',64),('output_length',8)):
        symbol=c['symbols'][name]
        payload.require(symbol['index']==bss['index'] and symbol['size']==size and bss['address']+32<=symbol['value'] and
                        symbol['value']+size<=bss['address']+bss['size'],'integrity object binding')
    return f'''python
import gdb
inferior=gdb.selected_inferior()
def memory(address,size):return bytes(inferior.read_memory(address,size))
def word(address):return int.from_bytes(memory(address,8),'little')
{REGISTER_READER}
def need(ok,message):
    if not ok:raise gdb.GdbError(message)
def stop(address):
    gdb.execute('tbreak *'+hex(address));gdb.execute('continue')
    need(reg('rip')==address,'wrong observation PC')
def environment():
    need(reg('cr3')=={outer['pml4_table']-payload.HIGH} and reg('eflags')&0x200==0,'root/IRQ changed')
    need({outer['c_core_stack_bottom']}<=reg('rsp')<{outer['c_core_stack_top']},'foreign C stack')
def call(address,name,wanted):
    stop(address);environment()
    stack=reg('rsp');target=word(stack)
    need(stack%16==8 and reg('rdi')=={s['specimen']} and reg('rsi')==7 and reg('rcx')==64,
         'SysV call contract rsp=%x rdi=%x rsi=%x rcx=%x'%(stack,reg('rdi'),reg('rsi'),reg('rcx')))
    need({text['address']}<=target<{text['address']+text['size']},'foreign return PC')
    stop(target);environment()
    result=reg('rax')&0xffffffff
    if result&0x80000000:result-=1<<32
    need(result==wanted and reg('rsp')==stack+8,'real C result/stack mismatch')
    need(int.from_bytes(memory({s['specimen']},4),'little')==0,'publication lock leaked')
    print('C_INTEGRITY_CALL operation=%s result=%d if=0 stack=1'%(name,result))
call({s['critical_object_read']},'read',0)
need(word({s['output_length']})==64 and memory({s['input']},64)==memory({s['output']},64),'real copyout mismatch')
for phase in range(1,13):
    if phase==9:call({s['critical_object_update']},'update',-1)
    stop({s['reist_x64_integrity_checkpoint']});environment()
    need(reg('rdi')==phase and reg('rsi')=={s['specimen']},'checkpoint identity')
    result=reg('rdx')&0xffffffffffffffff
    if result>>63:result-=1<<64
    count=reg('rcx');lock=int.from_bytes(memory({s['specimen']},4),'little')
    print('C_INTEGRITY_PHASE phase=%d result=%d count=%d lock=%d if=0'%(phase,result,count,lock))
stop({outer['x86_64_c_core_handoff64.verify_handoff_zero']})
need(reg('eflags')&0x200==0,'final IRQ leak')
need(not any(memory({bss['address']},{bss['size']})),'integrity or boot BSS not scrubbed')
need(not any(memory({payload.BINDINGS['x86_64_c_handoff']},192)),'handoff leaked')
print('C_INTEGRITY_ZERO bytes={bss['size']} if=0')
gdb.execute('detach')
end
quit
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    started=time.monotonic();summary=dict(passed=False)
    try:
        inner=payload.read_bounded(args.image.parent/'reist-x86_64-c-core.elf');outer=payload.read_bounded(args.image)
        payload.verify_outer(inner,outer);c=payload.validate(inner);o=payload.elf(outer,32)
        serial,trace=capture(args.image,attempt,commands(c,o));validate(serial,trace,c['sections']['.bss']['size'])
        summary.update(passed=True,reads=1650,checkpoints=12,sha256=hashlib.sha256(outer).hexdigest())
        print('C_INTEGRITY_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,ValueError,RuntimeError,KeyError) as exc:
        summary['error']=str(exc);print('C_INTEGRITY_RUNTIME_FAIL '+str(exc)+' evidence='+str(attempt));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
