"""One frozen diagnostic guest, never an acceptance or retry entry point."""
from pathlib import Path
import argparse
import hashlib
import inspect
import json
import struct
import time
import uuid

import run_qemu_x86_64_file_launch as launch

ROOT = launch.ROOT
BASE = ROOT / 'build/codex-agent/r83am-file-launch'
PREVIOUS = BASE / 'guests/attempt-19bf6f9b71af490786906d4dc0c079be'
REGISTERS = ('rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
             'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
             'rip', 'eflags', 'cr2', 'cr3')
RANGES = dict(timer_active=1, timer_mode=1, timer_generation=4,
              timer_deadline=8, timer_runtime_ticks=8, timer_runtime_eois=8,
              scheduler_active=1, scheduler_mode=1, scheduler_current_slot=4,
              scheduler_original_cr3=8, scheduler_last_tick=8,
              scheduler_runqueue_head=1, scheduler_runqueue_tail=1,
              scheduler_runqueue_count=1, scheduler_runqueue_membership=4,
              scheduler_runqueue_entries=32, scheduler_deadline_count=1,
              scheduler_deadline_membership=4, scheduler_deadline_entries=64,
              process_run_live=4, process_run_generation=4,
              process_run_generations=16, process_run_plan=144,
              process_heap_pending_mask=4, process_heap_retire_mask=4,
              scheduler_cpu_budgets=128, scheduler_tasks=4096,
              native_pio_state=64, native_pio_trace=16)
HOOKS = ('timer_runtime_progress64.fail', 'process_run_validate64.bad',
         'process_run_irq_validate64.bad', 'process_run_tick_admit64.bad',
         'x86_64_timer_interrupt64.shell_clock_invalid',
         'x86_64_timer_interrupt64.shell_invalid', 'exception_fatal',
         'scheduler_fail')


def collect(kind, symbols, read, register):
    """Fixed reads only; invalid frame pointers remain opaque diagnostic data."""
    registers = {name: register(name) for name in REGISTERS}
    memory = {name: read(symbols[name], size).hex() for name, size in RANGES.items()}
    bottom = symbols['scheduler_kernel_stack_bottom']
    top = symbols['scheduler_kernel_stack_top']
    stack = None
    if bottom <= registers['rsp'] <= top - 8:
        count = min(32, (top - registers['rsp']) // 8)
        stack = list(struct.unpack('<' + 'Q' * count, read(registers['rsp'], count * 8)))
    address = registers['rdi']
    if kind == 'timer_runtime_progress64.fail':
        address = stack[1] if stack and len(stack) >= 2 else 0
    elif kind == 'process_run_validate64.bad':
        address = stack[8] if stack and len(stack) >= 9 else 0  # fourteen preserved registers
    elif kind == 'exception_fatal':
        address = registers['rsp']
    elif kind == 'cold_exception_fatal':
        address = registers['rsp'] + 8  # serial_init return precedes IRQ frame
    elif kind == 'cold_native_pio_fail64':
        address = 0  # Unknown failure: do not invent an IRQ frame.
    frame = None
    if not address % 8 and bottom <= address <= top - 176:
        frame = list(struct.unpack('<22Q', read(address, 176)))
    return dict(version=1, kind=kind, registers=registers, memory=memory,
                stack=stack, frame_address=address, frame=frame)


GDB = '''
diagnostic_records=0
class TimerDiagnostic(gdb.Breakpoint):
    def __init__(self,name):
        super().__init__('*'+hex(S[name]),internal=True)
        self.diagnostic_name=name
    def stop(self):
        global diagnostic_records
        if mem(S['scheduler_mode'],1)!=b'\\x08':return False
        if diagnostic_records >= 8:return False
        diagnostic_records+=1
        try:
            record=collect(self.diagnostic_name,S,mem,reg)
            record['sequence']=diagnostic_records
            encoded=json.dumps(record,sort_keys=True)+'\\n'
            if len(encoded) > 16384:raise ValueError('diagnostic record bound')
            with open(DIAGNOSTIC_FILE,'x' if diagnostic_records==1 else 'a',encoding='ascii') as output:
                output.write(encoded)
            gdb.write('TIMER_DIAGNOSTIC '+self.diagnostic_name+' r9='+str(record['registers']['r9'])+'\\n')
        except Exception as error:
            gdb.write('TIMER_DIAGNOSTIC_ERROR '+str(error)[:256]+'\\n')
        return False
diagnostic_hooks=[TimerDiagnostic(name) for name in DIAGNOSTIC_HOOKS]
'''


def cold_route(symbols, read, rsp):
    """Bind both CALLs: completed emergency fencing then serial initialization."""
    if rsp % 8 or not symbols['scheduler_kernel_stack_bottom'] <= rsp <= symbols['scheduler_kernel_stack_top'] - 8:
        return None
    returned = struct.unpack('<Q', read(rsp, 8))[0]
    for name in ('exception_fatal', 'native_pio_fail64'):
        address = symbols[name]
        if returned != address + 10:
            continue
        code = read(address, 10)
        if (code[0] != 0xe8 or code[5] != 0xe8 or
            address + 5 + struct.unpack_from('<i', code, 1)[0] != symbols['native_pio_emergency_fence64'] or
            address + 10 + struct.unpack_from('<i', code, 6)[0] != symbols['serial_init64']):
            raise ValueError('cold fatal route drift')
        return 'cold_' + name
    return None


def install_cold(hooks, original, capture):
    """Only a host callback reference changes; no guest breakpoint is added."""
    if hooks is None or len(hooks) > 64:
        raise ValueError('cold callback inventory')
    selected = [hook for hook in hooks if getattr(hook, 'fn', None) is original]
    if len(selected) != 1:
        raise ValueError('cold callback identity')
    def wrapped():
        try:
            capture()
        finally:
            original()
    selected[0].fn = wrapped


COLD_GDB = '''
diagnostic_records=0
def diagnostic_cold_capture():
    global diagnostic_records
    if mem(S['scheduler_mode'],1)!=b'\\x08' or diagnostic_records >= 1:return
    kind=cold_route(S,mem,reg('rsp'))
    if kind is None:return
    diagnostic_records+=1
    record=collect(kind,S,mem,reg)
    record['sequence']=diagnostic_records
    encoded=json.dumps(record,sort_keys=True)+'\\n'
    if len(encoded) > 16384:raise ValueError('diagnostic record bound')
    with open(DIAGNOSTIC_FILE,'x',encoding='ascii') as output:
        output.write(encoded)
    gdb.write('TIMER_DIAGNOSTIC '+kind+' r9='+str(record['registers']['r9'])+'\\n')
install_cold(gdb.breakpoints(),cold_fail,diagnostic_cold_capture)
'''


def instrument(original, folder, *, cold=False):
    tail = '\nend\ncontinue\n'
    if not original.endswith(tail):
        raise ValueError('diagnostic observer boundary')
    extra = ('\n# TIMER_DIAGNOSTIC_APPEND_ONLY\nREGISTERS=' + repr(REGISTERS) +
             '\nRANGES=' + repr(RANGES) + '\nDIAGNOSTIC_HOOKS=' + repr(HOOKS) +
             '\nDIAGNOSTIC_FILE=' + repr((folder / 'registers.jsonl').as_posix()) +
             '\n' + inspect.getsource(collect))
    if cold:
        extra += '\n' + inspect.getsource(cold_route) + '\n' + inspect.getsource(install_cold) + COLD_GDB
    else:
        extra += GDB
    return original[:-len(tail)] + extra + tail


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        while data := source.read(1024 * 1024):
            value.update(data)
    return value.hexdigest()


def main():
    # The sole new selector names a separately authorized one-shot diagnostic.
    parser = argparse.ArgumentParser()
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--irq-regression', action='store_true')
    parser.add_argument('--legacy-sleep', action='store_true')
    parser.add_argument('--legacy-sleep-events', action='store_true')
    args = parser.parse_args()
    if sum(vars(args).values()) > 1:raise ValueError('exclusive diagnostic selections')
    if args.legacy_sleep or args.legacy_sleep_events:
        return legacy_sleep(events=args.legacy_sleep_events)
    if args.irq_regression:
        if args.cold:raise ValueError('exclusive diagnostic selections')
        return irq_matrix()
    prior_path = BASE / ('verification-status-timer-diagnostic.json' if args.cold else 'verification-status.json')
    prior = json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status'] != 'blocked':
        raise ValueError('diagnostic requires original blocked candidate')
    for name, expected in prior['evidence_sha256'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('prior evidence changed: ' + name)
    changed = {'automation/reist-s03b.toml', 'docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md'}
    if args.cold:
        source_snapshots = {
            'scripts/diagnose_x86_64_file_timer.py': 'diagnose_x86_64_file_timer-5ad56853.py',
            'test/test_x86_64_file_timer_diagnostic.py': 'test_x86_64_file_timer_diagnostic-5ad56853.py'}
        changed.update(source_snapshots)
        for name, snapshot in source_snapshots.items():
            if digest(BASE / 'timer-diagnostic' / snapshot) != prior['source_sha256'][name]:
                raise ValueError('previous diagnostic source snapshot')
        original_path = ROOT / prior['previous_manifest']['path']
        if digest(original_path) != prior['previous_manifest']['sha256']:
            raise ValueError('original manifest changed')
        original_prior = json.loads(original_path.read_text())
        for name, expected in original_prior['evidence_sha256'].items():
            if digest(ROOT / name) != expected:
                raise ValueError('original failed evidence changed: ' + name)
    for name, expected in prior['source_sha256'].items():
        if name not in changed:
            if digest(ROOT / name) != expected:
                raise ValueError('candidate changed: ' + name)
    base = BASE / ('timer-diagnostic-cold' if args.cold else 'timer-diagnostic')
    if base.exists() and any(base.glob('attempt-*')):
        raise ValueError('one diagnostic guest already reserved; no retry')
    image = PREVIOUS / 'build-0-0/x86_64/reist-x86_64-bootstrap.elf'
    wide = launch.wide
    inner = wide.payload.read_bounded(image.parent / 'reist-x86_64-c-core.elf')
    core = wide.payload.validate(inner)
    wide.payload.verify_outer(inner, wide.payload.read_bounded(image, bits=32))
    symbols = wide.transport.symbols(image)
    for name in (*HOOKS, *RANGES, 'scheduler_kernel_stack_bottom',
                 'scheduler_kernel_stack_top'):
        if name not in symbols:
            raise ValueError('diagnostic symbol missing: ' + name)
    catalog = (image.parent / 'boot-programs.bin').read_bytes()
    producers = [p for p in image.parent.glob('programs-*')
                 if (p / 'boot-programs.bin').is_file() and
                 (p / 'boot-programs.bin').read_bytes() == catalog]
    if len(producers) != 1:
        raise ValueError('diagnostic producer provenance')
    producer = producers[0]
    raw = (producer / 'file-program.prg').read_bytes()
    records = {}
    for n in range(4):
        program = (producer / f'program{n}.prg').read_bytes()
        if wide.producer.prepare(program, [f'program{n}.prg', str(n)], True) != catalog[n*wide.SIZE:(n+1)*wide.SIZE]:
            raise ValueError('diagnostic catalog bytes')
        if n >= 2:
            records['driver' if n == 2 else 'fs'] = wide.producer.prepare(program, [], True)
    records['program'] = wide.producer.prepare(raw, [], True)
    counts = {name: wide.allocations(record) for name, record in records.items()}
    counts['sha'] = {name: hashlib.sha256(record).hexdigest() for name, record in records.items()}
    addresses = {name: launch.block.map_symbol(producer / f'program{n}.map', symbol)
                 for name, n, symbol in (('result_address', 0, 'file_launch_record'),
                     ('block_address', 2, 'filesystem_block_service'),
                     ('fs_address', 3, 'filesystem_service'))}
    base.mkdir(exist_ok=True)
    launch.pio.safe_folder(base)
    folder = base / ('attempt-' + uuid.uuid4().hex)
    folder.mkdir()
    original = launch.observer(symbols, core, folder, 0, 0, None, addresses, raw)
    code = instrument(original, folder, cold=args.cold)
    (folder / 'observer-original.gdb').write_text(original, encoding='ascii')
    fixture = launch.pio.Fixture(folder, filesystem='fat12', file_program=raw)
    report = dict(accepted=False, diagnostic_only=True, guest_attempts=1,
                  cold=args.cold, previous_manifest=dict(path=str(prior_path.relative_to(ROOT)), sha256=digest(prior_path)),
                  source_attempt=PREVIOUS.name, image_sha256=digest(image),
                  file_sha256=hashlib.sha256(raw).hexdigest(),
                  observer_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  instrumented_sha256=hashlib.sha256(code.encode()).hexdigest(),
                  source_sha256={name: digest(ROOT/name) for name in
                     (*prior['source_sha256'], 'scripts/diagnose_x86_64_file_timer.py',
                      'test/test_x86_64_file_timer_diagnostic.py')})
    started = time.monotonic()
    try:
        serial, trace = wide.transport.capture(image, folder, code, 4096, fixture)
        launch.validate(serial, trace, 0, 0, None, counts, raw)
        report['guest_oracle_passed'] = True
    except (ValueError, RuntimeError, OSError) as error:
        report.update(guest_oracle_passed=False, error=str(error))
    finally:
        report['elapsed'] = round(time.monotonic() - started, 3)
        snapshots = folder / 'registers.jsonl'
        report['register_records'] = 0
        if snapshots.is_file():
            if snapshots.stat().st_size > (1 if args.cold else 8) * 16384:
                raise ValueError('diagnostic evidence bound')
            report['register_records'] = len(snapshots.read_text().splitlines())
        report['evidence_sha256'] = {p.name: digest(p) for p in folder.iterdir() if p.is_file()}
        (folder / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('TIMER_DIAGNOSTIC_ONLY', folder, 'records=' + str(report['register_records']),
              'elapsed=' + str(report['elapsed']), 'accepted=False')
    return 0  # Diagnostic completion, never a runtime acceptance result.


IRQ_KINDS = ('idle', 'expired', 'context', 'eoi')

LEGACY_RANGES = dict(timer_ticks=4, timer_eoi_count=4, scheduler_final_tick=4,
    scheduler_failure_stage=1, scheduler_handoffs=4, scheduler_fault_count=4,
    scheduler_reap_count=4, scheduler_idle_wakes=4, scheduler_event_count=1,
    scheduler_events=40, scheduler_sleep_events=27)


def legacy_collect(kind, symbols, read, register):
    record=collect('cold_native_pio_fail64',symbols,read,register)
    record['kind']=kind
    record['memory'].update({name:read(symbols[name],size).hex() for name,size in LEGACY_RANGES.items()})
    return record


LEGACY_GDB = r'''
legacy_records=0;legacy_events=0
def legacy_record(kind):
    global legacy_records
    assert legacy_records<2
    record=legacy_collect(kind,S,mem,reg);legacy_records+=1;record['sequence']=legacy_records
    raw=json.dumps(record,sort_keys=True)+'\n';assert len(raw)<=16384
    with open(LEGACY_FILE,'x' if legacy_records==1 else 'a',encoding='ascii') as f:f.write(raw)
    gdb.write('LEGACY_SLEEP_STATE '+kind+'\n')
def legacy_final():
    assert mode()==5 and legacy_records==0
    legacy_record('final');legacy_final_hook.enabled=False
    if LEGACY_EVENTS:legacy_event_hook.enabled=False
def legacy_cold():
    if mode()==5 and cold_route(S,mem,reg('rsp')) is not None:legacy_record('post_fence')
def legacy_event():
    global legacy_events
    if mode()!=5:return
    assert legacy_events<40;legacy_events+=1
    gdb.write('LEGACY_SLEEP_EVENT '+json.dumps(dict(seq=legacy_events,event=reg('rax')&255,tick=d(S['timer_ticks']),last=d(S['scheduler_last_tick']),slot=d(S['scheduler_current_slot'])),sort_keys=True)+'\n')
legacy_final_hook=Hook('scheduler_handle_sleep_exit64.final',legacy_final)
if LEGACY_EVENTS:legacy_event_hook=Hook('scheduler_append_event64',legacy_event)
install_cold(gdb.breakpoints(),cold_fail,legacy_cold)
'''


def legacy_instrument(original,folder,events=False):
    tail='\nend\ncontinue\n'
    if not original.endswith(tail):raise ValueError('legacy observer boundary')
    original=launch.once(original,'set logging enabled on\n','set logging redirect on\nset logging enabled on\n')
    extra='\nREGISTERS='+repr(REGISTERS)+'\nRANGES='+repr(RANGES)+'\nLEGACY_RANGES='+repr(LEGACY_RANGES)
    extra+='\nLEGACY_EVENTS='+repr(events)+'\nLEGACY_FILE='+repr((folder/'legacy-state.jsonl').as_posix())+'\n'
    extra+='\n'.join(inspect.getsource(fn) for fn in (collect,legacy_collect,cold_route,install_cold))+LEGACY_GDB
    return original[:-len(tail)]+extra+tail


def legacy_sleep(*,events=False):
    prior_path=BASE/'verification-status-timer-idle.json';prior=json.loads(prior_path.read_text())
    for name,expected in prior['evidence_sha256'].items():
        if digest(ROOT/name)!=expected:raise ValueError('preserved idle evidence changed: '+name)
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('legacy fixed image')
    base=BASE/('legacy-sleep-events' if events else 'legacy-sleep');base.mkdir(exist_ok=True)
    launch.pio.safe_folder(base)
    if any(base.glob('attempt-*')):raise ValueError('single legacy diagnostic already reserved')
    if events and not any((BASE/'legacy-sleep').glob('attempt-*/summary.json')):raise ValueError('final-only diagnosis first')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir()
    wide=launch.wide
    inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=wide.payload.validate(inner)
    wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32));symbols=wide.transport.symbols(image)
    for name in (*RANGES,*LEGACY_RANGES,'scheduler_handle_sleep_exit64.final','scheduler_append_event64'):
        if name not in symbols:raise ValueError('legacy symbol '+name)
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    producers=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(producers)!=1:raise ValueError('legacy producer provenance')
    producer=producers[0];raw=(producer/'file-program.prg').read_bytes();records={}
    if hashlib.sha256(raw).hexdigest()!='42144aa3215c49586c4b30adc5195f63d8cf87f304b5bd6e3e5cc80258baff2a':raise ValueError('legacy file binding')
    for n in range(4):
        program=(producer/f'program{n}.prg').read_bytes()
        if wide.producer.prepare(program,[f'program{n}.prg',str(n)],True)!=catalog[n*wide.SIZE:(n+1)*wide.SIZE]:raise ValueError('legacy catalog binding')
        if n>=2:records['driver' if n==2 else 'fs']=wide.producer.prepare(program,[],True)
    records['program']=wide.producer.prepare(raw,[],True)
    counts={name:wide.allocations(record) for name,record in records.items()};counts['sha']={name:hashlib.sha256(record).hexdigest() for name,record in records.items()}
    addresses={name:launch.block.map_symbol(producer/f'program{n}.map',symbol) for name,n,symbol in (
        ('result_address',0,'file_launch_record'),('block_address',2,'filesystem_block_service'),('fs_address',3,'filesystem_service'))}
    original=launch.observer(symbols,core,folder,0,0,None,addresses,raw)
    code=legacy_instrument(original,folder,events)
    report=dict(accepted=False,diagnostic_only=True,events=events,guest_oracle_passed=False,
        previous_manifest=dict(path=str(prior_path.relative_to(ROOT)),sha256=digest(prior_path)),image_sha256=digest(image))
    started=time.monotonic()
    try:
        serial,trace=wide.transport.capture(image,folder,code,4096,launch.pio.Fixture(folder,filesystem='fat12',file_program=raw))
        launch.validate(serial,trace,0,0,None,counts,raw);report['guest_oracle_passed']=True
    except (ValueError,RuntimeError,OSError) as error:report['error']=str(error)
    finally:
        report['elapsed']=round(time.monotonic()-started,3)
        state=folder/'legacy-state.jsonl'
        report['records']=[json.loads(line) for line in state.read_text().splitlines()] if state.is_file() else []
        report['evidence_sha256']={p.name:digest(p) for p in folder.iterdir() if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('LEGACY_SLEEP_DIAGNOSTIC',folder,'records='+str(len(report['records'])),'guest_oracle='+str(report['guest_oracle_passed']),'elapsed='+str(report['elapsed']))
    return 0


IRQ_GDB = r'''
irq_armed=False;irq_seen=False;irq_fenced=False;irq_fatal_seen=False;irq_visits=0
irq_saved=None;irq_input=None
def irq_event(event,**fields):
    gdb.write('IRQ_REGRESSION '+json.dumps(dict(event=event,**fields),sort_keys=True)+'\n')
def irq_state():
    return {name:mem(S[name],size).hex() for name,size in RANGES.items() if name!='native_pio_trace'}
def irq_check_saved():
    assert irq_saved==irq_state()
def irq_clock_sample():
    global irq_seen,irq_visits,irq_saved,irq_input
    irq_visits+=1;assert irq_visits<=32 and irq_armed and not irq_seen
    frame=q(reg('rsp')+8)
    assert S['scheduler_kernel_stack_bottom']<=frame<=S['scheduler_kernel_stack_top']-176
    words=struct.unpack('<22Q',mem(frame,176))
    if words[18]!=8:return
    assert words[15:17]==(32,0) and words[21]==16 and words[19]&512
    assert d(S['process_run_live'])==1 and mem(S['scheduler_deadline_count'],1)==b'\x01'
    assert mem(S['scheduler_runqueue_count'],1)==b'\0' and task(1)[:2]==(6,2)
    assert task(0)[0]==0 and task(2)[0]==0 and task(3)[0]==0
    # Exercise the actual wake transition, not an arbitrary empty idle tick.
    if q(S['scheduler_deadline_entries'])!=reg('rdx')+1:return
    irq_seen=True;irq_probe.enabled=False
    before=collect('timer_runtime_progress64.fail',S,mem,reg)
    irq_input=dict(now=reg('rdi'),deadline=reg('rsi'),ticks=reg('rdx'),eois=reg('rcx'))
    irq_event('input',kind=IRQ_KIND,**irq_input)
    with open(IRQ_INPUT_FILE,'x',encoding='ascii') as output:output.write(json.dumps(before,sort_keys=True)+'\n')
    if IRQ_KIND=='idle':irq_tail.enabled=True;return
    if IRQ_KIND in ('expired','eoi'):
        inputs=fatal_clock_inputs(IRQ_KIND,*(irq_input[n] for n in ('now','deadline','ticks','eois')))
        for name,value in zip(('rdi','rsi','rdx','rcx'),inputs):gdb.execute('set $'+name+'='+str(value))
    else:
        assert IRQ_KIND=='context'
        gdb.selected_inferior().write_memory(frame+168,bytes(8))
    irq_saved=irq_state()
    irq_event('injected',kind=IRQ_KIND)
    irq_port.enabled=True;irq_halt.enabled=True
    for hook in irq_forbidden:hook.enabled=True
def irq_admitted():
    irq_tail.enabled=False
    assert IRQ_KIND=='idle' and irq_seen and reg('rdx')==1
    assert q(S['timer_runtime_ticks'])==q(S['timer_runtime_eois'])==irq_input['ticks']+1
    assert q(S['scheduler_last_tick'])==irq_input['ticks']
    assert q(S['timer_deadline'])==irq_input['now']+3000000000
    irq_event('admitted',ticks=q(S['timer_runtime_ticks']),eois=q(S['timer_runtime_eois']),deadline=q(S['timer_deadline']))
    irq_return.enabled=True
def irq_masked_return():
    irq_return.enabled=False
    words=struct.unpack('<22Q',mem(reg('rdi'),176))
    assert words[18]==8 and not words[19]&512
    assert mem(S['scheduler_runqueue_count'],1)==b'\x01' and mem(S['scheduler_deadline_count'],1)==b'\0'
    assert task(1)[:2]==(1,2)
    irq_event('masked_return',ready=1,deadlines=0,if_bit=0)
def irq_physical_fence():
    global irq_fenced
    assert irq_seen and not irq_fenced and mem(S['native_pio_out8.done']-1,1)==b'\xee'
    assert reg('edx')&65535==0x3f6 and reg('eax')&255==6
    irq_check_saved();irq_fenced=True;irq_port.enabled=False
    irq_event('fence',port=0x3f6,value=6,unchanged=1)
def irq_fatal():
    global irq_fatal_seen
    if mode()!=8:return
    kind=cold_route(S,mem,reg('rsp'))
    if kind is None:return
    diagnostic_cold_capture()
    assert IRQ_KIND!='idle' and irq_seen and irq_fenced and not irq_fatal_seen
    assert kind=='cold_exception_fatal' and not reg('eflags')&512
    expected={'expired':4,'eoi':2,'context':0}[IRQ_KIND]
    assert reg('r9')==expected
    irq_check_saved();words=struct.unpack('<22Q',mem(reg('rsp')+8,176))
    assert words[15:17]==(32,0) and words[21]==(0 if IRQ_KIND=='context' else 16)
    irq_fatal_seen=True;irq_event('fatal',reason=expected,vector=32,unchanged=1,fenced=1)
def irq_halted():
    assert irq_fatal_seen and irq_fenced and mem(S['halt64'],4)==b'\xfa\xf4\xeb\xfd'
    irq_check_saved();irq_event('halt',unchanged=1)
    gdb.execute('detach');gdb.execute('quit 0')
def irq_forbidden_resume():raise AssertionError('runtime resumed after injected timer fault')
irq_probe=Hook('timer_runtime_progress64',irq_clock_sample);irq_probe.enabled=False
irq_tail=Hook('process_run_irq_tail64',irq_admitted);irq_tail.enabled=False
irq_return=Hook('process_run_irq_tail64.idle_return',irq_masked_return);irq_return.enabled=False
irq_port=Hook('native_pio_out8.done',irq_physical_fence);irq_port.enabled=False
irq_halt=Hook('halt64',irq_halted);irq_halt.enabled=False
irq_forbidden=[Hook(name,irq_forbidden_resume) for name in ('process_run_resume64','family_terminal64','scheduler_force_cleanup64')]
for hook in irq_forbidden:hook.enabled=False
irq_original_emit=emit
def emit(kind,**fields):
    global irq_armed
    irq_original_emit(kind,**fields)
    if kind=='release' and fields['gen']==1 and fields['slot']==0:
        assert not irq_armed
        irq_armed=True;irq_probe.enabled=True;irq_event('armed',root=1)
install_cold(gdb.breakpoints(),cold_fail,irq_fatal)
'''


def irq_observer(original, folder, kind):
    if kind not in IRQ_KINDS:raise ValueError('IRQ regression kind')
    # Retain every GDB witness in frame-trace.log, like the existing PIO fatal
    # runner. Avoid synchronously duplicating it to the unused console log.
    original=launch.once(original,'set logging enabled on\n',
                         'set logging redirect on\nset logging enabled on\n')
    code=instrument(original,folder,cold=True)
    code=launch.once(code,'install_cold(gdb.breakpoints(),cold_fail,diagnostic_cold_capture)','')
    tail='\nend\ncontinue\n'
    return code[:-len(tail)]+ '\nIRQ_KIND='+repr(kind)+'\nIRQ_INPUT_FILE='+repr((folder/'irq-input.json').as_posix())+'\n'+inspect.getsource(launch.pio.fatal_clock_inputs)+IRQ_GDB+tail


def _validate_irq(serial,trace,kind):
    if kind not in IRQ_KINDS:raise ValueError('IRQ regression kind')
    try:events=[json.loads(line[15:]) for line in trace.splitlines() if line.startswith('IRQ_REGRESSION ')]
    except (ValueError,TypeError) as error:raise ValueError('IRQ regression encoding') from error
    if any(type(e) is not dict or any(type(v) not in (str,int) for v in e.values()) for e in events):
        raise ValueError('IRQ exact scalar types')
    wanted=['armed','input','admitted','masked_return'] if kind=='idle' else ['armed','input','injected','fence','fatal','halt']
    if [e.get('event') for e in events]!=wanted or 'OBSERVER_FAIL' in trace:raise ValueError('IRQ exact witnesses')
    if events[0]!={'event':'armed','root':1}:raise ValueError('IRQ exact arm')
    sample=events[1]
    if set(sample)!=set(('event','kind','now','deadline','ticks','eois')) or sample['kind']!=kind:raise ValueError('IRQ sample shape')
    if any(type(sample[n]) is not int or not 0<=sample[n]<1<<64 for n in ('now','deadline','ticks','eois')):raise ValueError('IRQ sample bounds')
    if not 0<=sample['ticks']==sample['eois']<(1<<60)-1 or not sample['now']<=sample['deadline']<=sample['now']+3000000000:raise ValueError('IRQ initial admission')
    if kind=='idle':
        if events[2]!=dict(event='admitted',ticks=sample['ticks']+1,eois=sample['eois']+1,deadline=sample['now']+3000000000):raise ValueError('IRQ publication')
        if events[3]!=dict(event='masked_return',ready=1,deadlines=0,if_bit=0):raise ValueError('IRQ return window')
        if 'EXCEPTION_FATAL' in serial:raise ValueError('IRQ idle fatal')
    else:
        expected=[dict(event='injected',kind=kind),dict(event='fence',port=0x3f6,value=6,unchanged=1),
                  dict(event='fatal',reason={'expired':4,'eoi':2,'context':0}[kind],vector=32,unchanged=1,fenced=1),dict(event='halt',unchanged=1)]
        if events[2:]!=expected:raise ValueError('IRQ fail-closed sequence')
        if serial.count('REIST_X86_64_EXCEPTION_FATAL vector=20')!=1 or serial.count('EXCEPTION_FATAL')!=1:raise ValueError('IRQ exact fatal')
        if 'PROCESS_RUN_OK' in serial or serial.count('PROCESS_REAP_OK')!=7:raise ValueError('IRQ unexpected continuation')
    return events


def validate_irq(serial,trace,kind):
    try:return _validate_irq(serial,trace,kind)
    except (KeyError,TypeError,AttributeError) as error:
        raise ValueError('malformed IRQ regression evidence') from error


def irq_matrix():
    prior_path=BASE/'verification-status-timer-cold.json';prior=json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status']!='blocked':raise ValueError('IRQ candidate boundary')
    for path,expected in prior['evidence_sha256'].items():
        if digest(ROOT/path)!=expected:raise ValueError('cold evidence changed: '+path)
    for name,snapshot in (('scripts/diagnose_x86_64_file_timer.py','diagnose_x86_64_file_timer-d0263b65.py'),
                          ('test/test_x86_64_file_timer_diagnostic.py','test_x86_64_file_timer_diagnostic-d0263b65.py')):
        if digest(BASE/'timer-diagnostic-cold'/snapshot)!=prior['source_sha256'][name]:raise ValueError('cold source snapshot')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    base=BASE/'timer-idle-regression';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    candidate_key=hashlib.sha256((digest(image)+digest(Path(__file__))+digest(ROOT/'arch/x86_64/proc/process_run.inc')).encode()).hexdigest()
    existing=list(base.glob('attempt-*'))
    # One demonstrated kernel-reentry correction, then at most two focused
    # corrections for the distinct20s observer failure; frozen queue accounting.
    if len(existing)>=4 or any(json.loads((p/'summary.json').read_text()).get('candidate_key')==candidate_key for p in existing):
        raise ValueError('IRQ matrix unchanged retry or focused repair bound')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir()
    # Reuse the exact saved observer configuration: no build or new fixture policy.
    import ast
    cold_folder=BASE/'timer-diagnostic-cold/attempt-13b8dc8dccc648d0be09aa505c33ea2e'
    original=(cold_folder/'observer-original.gdb').read_text(encoding='ascii')
    config_line=next(line for line in original.splitlines() if line.startswith('CONFIG='))
    config=ast.literal_eval(config_line[len('CONFIG='):])
    if (config['case'],config['layout'],config['oom'])!=(0,0,None):raise ValueError('IRQ frozen selectors')
    config['s']=launch.wide.transport.symbols(image)
    inner=launch.wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    core=launch.wide.payload.validate(inner)
    launch.wide.payload.verify_outer(inner,launch.wide.payload.read_bounded(image,bits=32))
    config['cs']={name:info['value'] for name,info in core['symbols'].items()}
    original=('set breakpoint always-inserted on\nset logging file '+(cold_folder/'frame-trace.log').as_posix()+
              '\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+repr(config)+'\n'+launch.observer_body()+'\nend\ncontinue\n')
    producers=[p for p in image.parent.glob('programs-*') if (p/'file-program.prg').is_file()]
    if len(producers)!=1:raise ValueError('IRQ file provenance')
    raw=(producers[0]/'file-program.prg').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=prior['diagnostic_guest']['file_sha256']:raise ValueError('IRQ file bytes')
    if config['prepared']!=launch.wide.producer.prepare(raw,[],True):raise ValueError('IRQ prepared file binding')
    counts={};records={}
    for role,n in (('driver',2),('fs',3)):
        records[role]=launch.wide.producer.prepare((producers[0]/f'program{n}.prg').read_bytes(),[],True)
    records['program']=launch.wide.producer.prepare(raw,[],True)
    counts={k:launch.wide.allocations(v) for k,v in records.items()};counts['sha']={k:hashlib.sha256(v).hexdigest() for k,v in records.items()}
    summary=dict(accepted=False,regression_passed=False,candidate_key=candidate_key,attempts=[],previous_manifest=dict(path=str(prior_path.relative_to(ROOT)),sha256=digest(prior_path)))
    total=0;begin=time.monotonic()
    try:
        for kind in IRQ_KINDS:
            out=folder/kind;out.mkdir()
            code=launch.once(original,(cold_folder/'frame-trace.log').as_posix(),(out/'frame-trace.log').as_posix())
            code=irq_observer(code,out,kind)
            fixture=launch.pio.Fixture(out,filesystem='fat12',file_program=raw)
            trial=dict(kind=kind,passed=False);summary['attempts'].append(trial);started=time.monotonic()
            try:
                serial,trace=launch.wide.transport.capture(image,out,code,4096,fixture,halt_witness=kind!='idle')
            finally:
                trial['elapsed']=round(time.monotonic()-started,3);total+=trial['elapsed']
            if trial['elapsed']>20 or total>80:raise ValueError('IRQ guest bound')
            trial['events']=validate_irq(serial,trace,kind)
            if kind=='idle':launch.validate(serial,trace,0,0,None,counts,raw)
            trial['passed']=True;print('IRQ_REGRESSION_GUEST_OK',kind,trial['elapsed'],flush=True)
        summary['regression_passed']=True
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('IRQ_REGRESSION_FAIL',error);return 1
    finally:
        summary.update(elapsed=round(time.monotonic()-begin,3),guest_elapsed=round(total,3),image_sha256=digest(image))
        summary['evidence_sha256']={str(p.relative_to(folder)):digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('IRQ_REGRESSION_EVIDENCE',folder)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
