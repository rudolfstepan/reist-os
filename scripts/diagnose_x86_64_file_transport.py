"""Finite same-image transport controls; measurements are never OS acceptance."""
from pathlib import Path
import argparse
import hashlib
import inspect
import json
import re
import struct
import time
import tomllib
import uuid

import run_qemu_x86_64_file_launch as launch

ROOT=launch.ROOT
BASE=ROOT/'build/codex-agent/r83am-file-launch'
INITIAL=('detached','finish','full','full-profile')
FOLLOWUP=('full-span-profile','full-batch-profile')

# Fixed symbol-relative kernel RAM only; never follow a captured guest pointer.
TIMELINE_RANGES={name:(name,0,size) for name,size in (
    ('scheduler_mode',1),('scheduler_active',1),('scheduler_current_slot',4),
    ('process_run_live',4),('process_run_generation',4),('process_run_generations',16),
    ('timer_active',1),('timer_mode',1),('timer_generation',4),('timer_deadline',8),
    ('timer_runtime_ticks',8),('timer_runtime_eois',8),('scheduler_last_tick',8),
    ('scheduler_runqueue_count',1),('scheduler_deadline_count',1),
    ('scheduler_runqueue_membership',4),('scheduler_deadline_membership',4),
    ('scheduler_runqueue_entries',32),('scheduler_deadline_entries',64))}
TIMELINE_RANGES.update(root_head=('scheduler_tasks',0,16),peer_head=('scheduler_tasks',1024,16),
                      peer_registers=('scheduler_tasks',1024+544,256))


def timeline_sample(symbols,read):
    state={};total=0
    for name,(symbol,offset,size) in TIMELINE_RANGES.items():
        total+=size;assert total<=1280
        raw=read(symbols[symbol]+offset,size);assert len(raw)==size
        state[name]=raw.hex()
        if name=='scheduler_mode' and raw!=b'\x08':break
    return state


class Timeline:
    """Monotonic callback lower bounds, not an invented guest/transport split."""
    def __init__(self,clock,save,sample=None):
        self.clock=clock;self.save=save;self.sample=sample;self.started=clock()
        self.sequence=0;self.callbacks=0;self.events=0;self.samples=0
        self.active=None;self.last_sample=-200000000;self.last_ns=0

    def emit(self,event,*,state=None):
        ns=self.clock()-self.started
        assert self.last_ns<=ns<24000000000 and self.sequence<16384
        self.last_ns=ns;self.sequence+=1
        call,name=self.active if self.active else (0,'')
        self.save(dict(version=1,seq=self.sequence,ns=ns,event=event,call=call,name=name,state=state))

    def notify(self,event):
        assert event in ('cont','stop') and self.events<8192
        self.events+=1;self.emit(event)

    def wrap_stop(self,original):
        def stop(hook):
            assert self.active is None and self.callbacks<4096
            name=hook.fn.__name__ if hasattr(hook,'fn') else type(hook).__name__
            assert 1<=len(name)<=64
            self.callbacks+=1;self.active=(self.callbacks,name)
            self.emit('enter')
            try:
                now=self.clock()-self.started
                if self.sample and (now-self.last_sample>=200000000 or name in ('ReleaseEnd','finish')):
                    assert self.samples<192
                    state=self.sample()
                    if state is not None:
                        self.samples+=1;self.last_sample=now;self.emit('sample',state=state)
                return original(hook)
            finally:
                self.emit('leave');self.active=None
        return stop


TIMELINE_BINDING=r'''
import time
timeline_file=open(TIMELINE_FILE,'x',encoding='ascii',buffering=65536)
timeline_pending=0;timeline_flush_at=time.perf_counter_ns()
def timeline_flush():
    global timeline_pending,timeline_flush_at
    timeline_file.flush();timeline_pending=0;timeline_flush_at=time.perf_counter_ns()
def timeline_save(row):
    global timeline_pending
    raw=json.dumps(row,separators=(',',':'))+'\n';assert len(raw)<=2048
    timeline_file.write(raw);timeline_pending+=1
    if timeline_pending>=32 or time.perf_counter_ns()-timeline_flush_at>=200000000 or row['event']=='sample':timeline_flush()
def timeline_read():
    if not boot_seen:return None
    return timeline_sample(S,mem)
timeline=Timeline(time.perf_counter_ns,timeline_save,timeline_read if TIMELINE_KIND=='peer-clock' else None)
def timeline_failed(error):
    timeline_flush();gdb.write('TIMELINE_OBSERVER_FAIL '+repr(error)+'\n');gdb.execute('quit 74')
def timeline_guard(original):
    wrapped=timeline.wrap_stop(original)
    def stop(hook):
        try:return wrapped(hook)
        except Exception as error:timeline_failed(error);return True
    return stop
Hook.stop=timeline_guard(Hook.stop)
ReleaseEnd.stop=timeline_guard(ReleaseEnd.stop)
def timeline_cont(event):
    try:timeline.notify('cont')
    except Exception as error:timeline_failed(error)
def timeline_stop(event):
    try:timeline.notify('stop');timeline_flush()
    except Exception as error:timeline_failed(error)
gdb.events.cont.connect(timeline_cont)
gdb.events.stop.connect(timeline_stop)
'''


def timeline_observer(kind,original,folder):
    if kind not in ('stops','peer-clock'):raise ValueError('timeline selector')
    code=observer('full',original,folder,{})
    code=code.replace("gdb.execute('detach')","timeline_flush();gdb.execute('detach')")
    code=code.replace("gdb.execute('quit", "timeline_flush();gdb.execute('quit")
    tail='\nend\ncontinue\n'
    addition='\nTIMELINE_FILE='+repr((folder/'timeline.jsonl').as_posix())+'\nTIMELINE_KIND='+repr(kind)
    addition+='\nTIMELINE_RANGES='+repr(TIMELINE_RANGES)+'\n'+inspect.getsource(timeline_sample)+inspect.getsource(Timeline)+TIMELINE_BINDING
    return code[:-len(tail)]+addition+tail


def timeline_records(path):
    if not path.is_file() or not 0<path.stat().st_size<=16384*2048:raise ValueError('timeline extent')
    lines=path.read_text(encoding='ascii').splitlines()
    if not 1<=len(lines)<=16384:raise ValueError('timeline record bound')
    result=dict(callbacks=0,completed_callbacks=0,callback_ns=0,gap_ns=0,
                notifications=dict(cont=0,stop=0),samples=[],functions={})
    active=None;previous_end=None;last_ns=0
    for index,line in enumerate(lines,1):
        if len(line)+1>2048:raise ValueError('timeline line bound')
        row=json.loads(line)
        if type(row) is not dict or set(row)!=set(('version','seq','ns','event','call','name','state')):raise ValueError('timeline schema')
        if type(row['version']) is not int or row['version']!=1 or type(row['seq']) is not int or row['seq']!=index:raise ValueError('timeline sequence')
        if type(row['ns']) is not int or not last_ns<=row['ns']<24000000000:raise ValueError('timeline clock')
        last_ns=row['ns'];event=row['event'];name=row['name'];call=row['call']
        if type(name) is not str or len(name)>64 or type(call) is not int or not 0<=call<=4096:raise ValueError('timeline identity')
        if event=='enter':
            if active is not None or not name or call!=result['callbacks']+1:raise ValueError('timeline callback entry')
            if previous_end is not None:result['gap_ns']+=row['ns']-previous_end
            active=row;result['callbacks']+=1
        elif event in ('leave','sample'):
            if active is None or (call,name)!=(active['call'],active['name']):raise ValueError('timeline callback boundary')
            if event=='leave':
                elapsed=row['ns']-active['ns'];result['callback_ns']+=elapsed;result['completed_callbacks']+=1
                f=result['functions'].setdefault(name,dict(calls=0,ns=0));f['calls']+=1;f['ns']+=elapsed
                if len(result['functions'])>64:raise ValueError('timeline function capacity')
                active=None;previous_end=row['ns']
        elif event in ('cont','stop'):
            if (call,name)!=((active['call'],active['name']) if active else (0,'')):raise ValueError('timeline event identity')
            result['notifications'][event]+=1
            if sum(result['notifications'].values())>8192:raise ValueError('timeline event capacity')
        else:raise ValueError('timeline event type')
        state=row['state']
        if event=='sample':
            if type(state) is not dict or 'scheduler_mode' not in state:raise ValueError('timeline sample schema')
            keys=set(TIMELINE_RANGES) if state['scheduler_mode']=='08' else {'scheduler_mode'}
            if set(state)!=keys or len(result['samples'])>=192:raise ValueError('timeline sample extent')
            for key,raw in state.items():
                if type(raw) is not str or len(raw)!=TIMELINE_RANGES[key][2]*2 or len(bytes.fromhex(raw))!=TIMELINE_RANGES[key][2]:raise ValueError('timeline sample bytes')
            result['samples'].append(row)
        elif state is not None:raise ValueError('timeline unexpected sample')
    result.update(last_ns=last_ns,records=len(lines),active=active['name'] if active else None,
                  active_ns=last_ns-active['ns'] if active else 0,tail_may_be_unflushed=True)
    if result['callback_ns']+result['gap_ns']+result['active_ns']>last_ns:raise ValueError('timeline accounting')
    return result


class Cost:
    """Actual debugger wrappers use this pure bounded accountant on the host."""
    def __init__(self,clock,save):
        self.clock=clock;self.save=save;self.active=None;self.records=0
        self.started=self.last=clock()
        self.value=dict(version=1,callbacks=0,reads=0,bytes=0,registers=0,
                        callback_ns=0,read_ns=0,register_ns=0,functions={})

    def checkpoint(self,force=False):
        now=self.clock()
        if not force and now-self.last<250000000:return
        assert self.records<128
        value=dict(self.value,functions={name:dict(row) for name,row in self.value['functions'].items()})
        value.update(sequence=self.records+1,elapsed_ns=now-self.started,active=None)
        if self.active is not None:
            name,start=self.active;elapsed=now-start
            value['active']=name;value['callback_ns']+=elapsed;value['functions'][name]['ns']+=elapsed
        self.records+=1;self.last=now;self.save(value)

    def wrap_stop(self,original):
        def stop(hook):
            assert self.active is None
            name=hook.fn.__name__ if hasattr(hook,'fn') else type(hook).__name__
            assert len(name)<=64
            value=self.value;value['callbacks']+=1;assert value['callbacks']<=4096
            row=value['functions'].setdefault(name,dict(calls=0,ns=0,read_ns=0,register_ns=0))
            assert len(value['functions'])<=64
            row['calls']+=1;self.active=(name,self.clock())
            self.checkpoint()
            try:return original(hook)
            finally:
                elapsed=self.clock()-self.active[1];row['ns']+=elapsed;value['callback_ns']+=elapsed
                self.active=None;self.checkpoint()
        return stop

    def wrap_read(self,original):
        def read(address,size):
            assert type(size)==int and 0<=size<=270336
            self.value['reads']+=1;self.value['bytes']+=size
            assert self.value['reads']<=1000000 and self.value['bytes']<=134217728
            start=self.clock()
            try:return original(address,size)
            finally:
                elapsed=self.clock()-start;self.value['read_ns']+=elapsed
                if self.active:self.value['functions'][self.active[0]]['read_ns']+=elapsed
        return read

    def wrap_register(self,original):
        def register(name):
            self.value['registers']+=1;assert self.value['registers']<=1000000
            start=self.clock()
            try:return original(name)
            finally:
                elapsed=self.clock()-start;self.value['register_ns']+=elapsed
                if self.active:self.value['functions'][self.active[0]]['register_ns']+=elapsed
        return register


SIMPLE=r'''
import gdb,json
S=CONFIG['s'];runs=0
def reg(name):return int(gdb.parse_and_eval('$'+name))&0xffffffffffffffff
def mem(address,size):return bytes(gdb.selected_inferior().read_memory(address,size))
class Hook(gdb.Breakpoint):
    def __init__(self,name,fn):
        super().__init__('*'+hex(S[name]),internal=True);self.fn=fn
    def stop(self):self.fn();return False
def finish():
    global runs
    runs+=1;assert runs<=2
    gdb.write('FILE_TRANSPORT_FINISH '+str(runs)+'\n')
    if runs==2:gdb.execute('detach');gdb.execute('quit 0')
if KIND=='finish':Hook('x86_64_c_process_run64.restore',finish)
'''

PROFILE=r'''
import time
def save_cost(value):
    raw=json.dumps(value,sort_keys=True)+'\n';assert len(raw)<=8192
    with open(COST_FILE,'x' if value['sequence']==1 else 'a',encoding='ascii') as output:output.write(raw)
cost=Cost(time.perf_counter_ns,save_cost)
mem=cost.wrap_read(mem);reg=cost.wrap_register(reg)
Hook.stop=cost.wrap_stop(Hook.stop)
if 'ReleaseEnd' in globals():ReleaseEnd.stop=cost.wrap_stop(ReleaseEnd.stop)
cost.checkpoint(True)
'''


def observer(kind,original,folder,symbols):
    if kind not in INITIAL+FOLLOWUP:raise ValueError('transport control kind')
    tail='\nend\ncontinue\n'
    if kind.startswith('full'):
        if not original.endswith(tail):raise ValueError('transport observer boundary')
        code=launch.once(original,'set logging enabled on\n','set logging redirect on\nset logging enabled on\n')
    else:
        code=('set logging file '+(folder/'frame-trace.log').as_posix()+
              '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(dict(s=symbols))+
              '\nKIND='+repr(kind)+'\n'+SIMPLE+tail)
    if kind.endswith('profile'):
        code=code.replace("gdb.execute('detach')","cost.checkpoint(True);gdb.execute('detach')")
        code=code.replace("gdb.execute('quit", "cost.checkpoint(True);gdb.execute('quit")
        code=code[:-len(tail)]+'\nCOST_FILE='+repr((folder/'cost.jsonl').as_posix())+'\n'+inspect.getsource(Cost)+PROFILE+tail
    if kind=='detached':code=code[:-len(tail)]+"\ngdb.execute('detach');gdb.execute('quit 0')"+tail
    return code


def costs(path):
    if not path.is_file():raise ValueError('missing cost checkpoints')
    if path.stat().st_size>128*8192:raise ValueError('cost file bound')
    lines=path.read_text(encoding='ascii').splitlines();rows=[]
    if not 1<=len(lines)<=128:raise ValueError('cost checkpoint capacity')
    for index,line in enumerate(lines,1):
        if len(line)>8192:raise ValueError('cost checkpoint extent')
        row=json.loads(line)
        if type(row) is not dict or set(row)!={'version','sequence','elapsed_ns','active','callbacks','reads','bytes','registers','callback_ns','read_ns','register_ns','functions'}:raise ValueError('cost checkpoint schema')
        if type(row['version']) is not int or row['version']!=1 or type(row['sequence']) is not int or row['sequence']!=index:raise ValueError('cost identity')
        for key,bound in [('callbacks',4096),('reads',1000000),('bytes',134217728),('registers',1000000),('elapsed_ns',24000000000),('callback_ns',24000000000),('read_ns',24000000000),('register_ns',24000000000)]:
            if type(row[key]) is not int or not 0<=row[key]<=bound:raise ValueError('cost bounds '+key)
            if rows and row[key]<rows[-1][key]:raise ValueError('cost regression')
        f=row['functions']
        if type(f) is not dict or len(f)>64:raise ValueError('cost function capacity')
        for name,item in f.items():
            if type(name) is not str or not 1<=len(name)<=64 or type(item) is not dict or set(item)!={'calls','ns','read_ns','register_ns'}:raise ValueError('cost function schema')
            if any(type(v) is not int or v<0 for v in item.values()):raise ValueError('cost function type')
            if not 1<=item['calls']<=4096 or item['read_ns']+item['register_ns']>item['ns']:raise ValueError('cost function accounting')
        if row['active'] is not None and (type(row['active']) is not str or row['active'] not in f):raise ValueError('cost active')
        if sum(i['calls'] for i in f.values())!=row['callbacks'] or sum(i['ns'] for i in f.values())!=row['callback_ns']:raise ValueError('cost accounting')
        if row['read_ns']+row['register_ns']>row['callback_ns'] or row['callback_ns']>row['elapsed_ns']:raise ValueError('cost time accounting')
        rows.append(row)
    return rows


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        while raw:=source.read(1024*1024):h.update(raw)
    return h.hexdigest()


def fixture(image):
    wide=launch.wide
    inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=wide.payload.validate(inner)
    wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32));symbols=wide.transport.symbols(image)
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    paths=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(paths)!=1:raise ValueError('transport producer provenance')
    producer=paths[0];raw=(producer/'file-program.prg').read_bytes()
    if hashlib.sha256(raw).hexdigest()!='42144aa3215c49586c4b30adc5195f63d8cf87f304b5bd6e3e5cc80258baff2a':raise ValueError('transport file provenance')
    records={'program':wide.producer.prepare(raw,[],True)}
    for n in range(4):
        program=(producer/f'program{n}.prg').read_bytes()
        if wide.producer.prepare(program,[f'program{n}.prg',str(n)],True)!=catalog[n*wide.SIZE:(n+1)*wide.SIZE]:raise ValueError('transport catalog binding')
        if n>=2:records['driver' if n==2 else 'fs']=wide.producer.prepare(program,[],True)
    counts={name:wide.allocations(record) for name,record in records.items()};counts['sha']={name:hashlib.sha256(record).hexdigest() for name,record in records.items()}
    addresses={name:launch.block.map_symbol(producer/f'program{n}.map',symbol) for name,n,symbol in (
        ('result_address',0,'file_launch_record'),('block_address',2,'filesystem_block_service'),('fs_address',3,'filesystem_service'))}
    return symbols,core,counts,addresses,raw


def reserve_timeline(base,kind):
    if kind not in ('stops','peer-clock'):raise ValueError('timeline mode')
    previous=list(base.iterdir())
    if kind=='stops':
        if previous:raise ValueError('timeline stops already reserved')
    else:
        if len(previous)!=1 or not previous[0].name.startswith('stops-'):raise ValueError('timeline pair already spent or order invalid')
        path=previous[0]/'summary.json'
        if not path.is_file() or not json.loads(path.read_text())['completed']:raise ValueError('first timeline did not complete diagnosis')
    folder=base/(kind+'-'+uuid.uuid4().hex);folder.mkdir()
    return folder


def timeline_main(kind):
    prior_path=BASE/'verification-status-file-transport.json';prior=json.loads(prior_path.read_text())
    if prior['accepted'] or not prior['diagnostic_budget_exhausted']:raise ValueError('timeline prerequisite')
    for name,sha in prior['evidence_sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('preserved transport evidence changed')
    mutable={'automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md',
        'scripts/diagnose_x86_64_file_transport.py','test/test_x86_64_file_transport.py'}
    for name,sha in prior['source_sha256'].items():
        if name not in mutable and digest(ROOT/name)!=sha:raise ValueError('timeline changes frozen source '+name)
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    if package['id']!=prior['package'] or 'python scripts/diagnose_x86_64_file_transport.py --timeline '+kind not in package['file_timeline_diagnostic']:raise ValueError('timeline authority')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('timeline image')
    base=BASE/'file-timeline';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    folder=reserve_timeline(base,kind)
    summary=dict(accepted=False,diagnostic_only=True,completed=False,kind=kind,full_oracle_passed=False,
        previous_manifest=dict(path=prior_path.relative_to(ROOT).as_posix(),sha256=digest(prior_path)),image_sha256=digest(image),
        source_sha256={name:digest(ROOT/name) for name in prior['source_sha256']})
    started=time.monotonic()
    try:
        symbols,core,counts,addresses,raw=fixture(image)
        original=launch.observer(symbols,core,folder,0,0,None,addresses,raw)
        code=timeline_observer(kind,original,folder);capture_error=None
        try:serial,trace=launch.wide.transport.capture(image,folder,code,4096,launch.pio.Fixture(folder,filesystem='fat12',file_program=raw),diagnostic_metrics=True)
        except (ValueError,RuntimeError,OSError) as error:
            capture_error=str(error);serial=(folder/'guest.log').read_text() if (folder/'guest.log').is_file() else ''
            trace=(folder/'frame-trace.log').read_text() if (folder/'frame-trace.log').is_file() else ''
        summary['capture_error']=capture_error;summary['capture']=json.loads((folder/'capture-metrics.json').read_text())
        summary['reaps']=serial.count('PROCESS_REAP_OK');summary['runs']=serial.count(launch.wide.process.DONE)
        summary['timeline']=timeline_records(folder/'timeline.jsonl')
        if any(marker in serial for marker in launch.wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('unexpected timeline guest/observer failure')
        if capture_error and summary['capture']['stop_reason']!='deadline':raise ValueError('unexpected timeline transport failure')
        if not capture_error:
            launch.validate(serial,trace,0,0,None,counts,raw);summary['full_oracle_passed']=True
        summary['completed']=True
        print('FILE_TIMELINE_DIAGNOSED',kind,'stop='+summary['capture']['stop_reason'],
              'callbacks='+str(summary['timeline']['callbacks']),'samples='+str(len(summary['timeline']['samples'])),
              'full_oracle='+str(summary['full_oracle_passed']),flush=True)
        return 0
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('FILE_TIMELINE_BLOCKED',error);return 1
    finally:
        summary['elapsed_with_cleanup']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('FILE_TIMELINE_EVIDENCE',folder)


def reserve_binary(base,kind,source_sha256):
    if kind not in ('equivalence','full'):raise ValueError('binary mode')
    previous=[]
    for path in base.iterdir():
        report=path/'summary.json'
        if not report.is_file():raise ValueError('incomplete binary attempt')
        previous.append(json.loads(report.read_text()))
    if len(previous)>=4:raise ValueError('binary guest budget spent')
    same=[row for row in previous if row['kind']==kind]
    implementation=('scripts/qemu_binary_memory.py','scripts/run_qemu_x86_64_boot_programs.py',
                    'scripts/run_qemu_x86_64_file_launch.py')
    if any(row['passed'] or all(row['source_sha256'][name]==source_sha256[name] for name in implementation) for row in same):raise ValueError('binary unchanged retry or already passed')
    # Initial equivalence plus at most two source-changed corrections, then full.
    if len(previous)-sum(r['passed'] for r in previous)>=3:raise ValueError('binary directed correction budget')
    if kind=='full' and not any(row['kind']=='equivalence' and row['passed'] for row in previous):raise ValueError('binary equivalence prerequisite')
    folder=base/(kind+'-'+uuid.uuid4().hex);folder.mkdir();return folder


def binary_main(kind):
    prior_path=BASE/'verification-status-file-timeline.json';prior=json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status']!='blocked':raise ValueError('binary resume state')
    for name,sha in prior['evidence_sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('preserved timeline evidence changed')
    mutable={'automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md',
        'scripts/run_qemu_x86_64_boot_programs.py','scripts/run_qemu_x86_64_file_launch.py',
        'scripts/diagnose_x86_64_file_transport.py','test/test_x86_64_file_transport.py',
        'test/test_x86_64_block_transport.py','docs/architecture/X86_64_BOOTSTRAP.md',
        'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
    for name,sha in prior['source_sha256'].items():
        if name not in mutable and digest(ROOT/name)!=sha:raise ValueError('binary changes frozen source '+name)
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    if package['id']!=prior['package'] or 'python scripts/diagnose_x86_64_file_transport.py --binary '+kind not in package['binary_memory_diagnostic']:raise ValueError('binary authority')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('binary image')
    source_sha256={name:digest(ROOT/name) for name in (*prior['source_sha256'],*package['binary_memory_files'])}
    base=BASE/'file-binary';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    folder=reserve_binary(base,kind,source_sha256)
    summary=dict(accepted=False,passed=False,kind=kind,full_oracle_passed=False,source_sha256=source_sha256,
        previous_manifest=dict(path=prior_path.relative_to(ROOT).as_posix(),sha256=digest(prior_path)),image_sha256=digest(image))
    started=time.monotonic()
    try:
        symbols,core,counts,addresses,raw=fixture(image)
        original=launch.observer(symbols,core,folder,0,0,None,addresses,raw)
        code=observer('full',original,folder,symbols)
        media=launch.pio.Fixture(folder,filesystem='fat12',file_program=raw)
        begin=time.monotonic()
        try:
            serial,trace=launch.wide.transport.capture(image,folder,code,4096,media,diagnostic_metrics=True,binary_memory=kind)
        finally:summary['capture_with_cleanup_seconds']=round(time.monotonic()-begin,6)
        launch.validate(serial,trace,0,0,None,counts,raw);summary['full_oracle_passed']=True
        rows=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
        if not rows or len(rows)>2048 or sum(r['bytes'] for r in rows)>128*1024*1024:raise ValueError('binary ledger capacity')
        for index,row in enumerate(rows,1):
            path=folder/'binary-memory'/('ram-%04d.bin'%index)
            if row['sequence']!=index or row['file']!=path.name or path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:raise ValueError('binary ledger binding')
        if kind=='equivalence' and {r['equivalence'] for r in rows if r['equivalence']}!={'kernel','high'}:raise ValueError('binary equivalence coverage')
        summary.update(binary_reads=len(rows),binary_bytes=sum(r['bytes'] for r in rows))
        if summary['capture_with_cleanup_seconds']>20:raise ValueError('binary original file guest deadline')
        summary['passed']=True;print('FILE_BINARY_OK',kind,'reads='+str(len(rows)),'seconds='+str(summary['capture_with_cleanup_seconds']));return 0
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('FILE_BINARY_BLOCKED',kind,error);return 1
    finally:
        metrics=folder/'capture-metrics.json'
        if metrics.is_file():summary['capture']=json.loads(metrics.read_text())
        summary['elapsed_with_cleanup']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('FILE_BINARY_EVIDENCE',folder)


class StageCost:
    """Bounded nested spans: inclusive for attribution, exclusive for sums."""
    def __init__(self,clock,save):
        self.clock=clock;self.save=save;self.started=clock();self.last=0;self.last_save=0
        self.stack=[];self.stages={};self.calls=0;self.records=0

    def now(self):
        value=self.clock()-self.started
        assert self.last<=value<24000000000
        self.last=value;return value

    def wrap(self,name,original):
        assert type(name) is str and 1<=len(name)<=64
        def call(*args,**kwargs):
            assert self.calls<1000000 and len(self.stack)<8
            assert name in self.stages or len(self.stages)<16
            start=self.now();row=self.stages.setdefault(name,dict(calls=0,errors=0,inclusive_ns=0,exclusive_ns=0))
            frame=[start,0];self.calls+=1;row['calls']+=1;self.stack.append(frame)
            try:return original(*args,**kwargs)
            except BaseException:
                row['errors']+=1;raise
            finally:
                elapsed=self.now()-start
                assert self.stack.pop() is frame and 0<=frame[1]<=elapsed
                row['inclusive_ns']+=elapsed;row['exclusive_ns']+=elapsed-frame[1]
                if self.stack:self.stack[-1][1]+=elapsed
        return call

    def checkpoint(self,force=False):
        now=self.now()
        if not force and now-self.last_save<250000000:return
        assert not self.stack and self.records<128
        self.records+=1;self.last_save=now
        self.save(dict(version=1,sequence=self.records,elapsed_ns=now,calls=self.calls,
                       stages={name:dict(row) for name,row in self.stages.items()}))


def stage_costs(path):
    if not path.is_file() or path.stat().st_size>128*16384:raise ValueError('stage file bound')
    lines=path.read_text(encoding='ascii').splitlines();rows=[];previous=None
    if not 1<=len(lines)<=128:raise ValueError('stage checkpoint bound')
    for index,line in enumerate(lines,1):
        if len(line)>16384:raise ValueError('stage record bound')
        row=json.loads(line)
        if type(row) is not dict or set(row)!={'version','sequence','elapsed_ns','calls','stages'}:raise ValueError('stage schema')
        if any(type(row[k]) is not int for k in ('version','sequence','elapsed_ns','calls')):raise ValueError('stage integer')
        if row['version']!=1 or row['sequence']!=index or not 0<=row['elapsed_ns']<24000000000 or not 0<=row['calls']<=1000000:raise ValueError('stage counter')
        if type(row['stages']) is not dict or len(row['stages'])>16:raise ValueError('stage table')
        for name,value in row['stages'].items():
            if type(name) is not str or not 1<=len(name)<=64 or type(value) is not dict or set(value)!={'calls','errors','inclusive_ns','exclusive_ns'}:raise ValueError('stage entry')
            if any(type(n) is not int or n<0 for n in value.values()):raise ValueError('stage nonnegative')
            if not 0<=value['errors']<=value['calls']<=1000000 or not value['exclusive_ns']<=value['inclusive_ns']<=row['elapsed_ns']:raise ValueError('stage accounting')
        if sum(v['calls'] for v in row['stages'].values())!=row['calls'] or sum(v['exclusive_ns'] for v in row['stages'].values())>row['elapsed_ns']:raise ValueError('stage total')
        if previous:
            if any(row[k]<previous[k] for k in ('elapsed_ns','calls')) or not set(previous['stages'])<=set(row['stages']):raise ValueError('stage monotonicity')
            for name,value in previous['stages'].items():
                if any(row['stages'][name][k]<v for k,v in value.items()):raise ValueError('stage regression')
        rows.append(row);previous=row
    return rows


COMBINED_BINDING=r'''
import sys
sys.path.insert(0,COMBINED_SCRIPTS)
import qemu_binary_memory as binary
def combined_save_cost(value):
    raw=json.dumps(value,sort_keys=True)+'\n';assert len(raw)<=8192
    with open(COMBINED_COST,'x' if value['sequence']==1 else 'a',encoding='ascii') as output:output.write(raw)
def combined_save_stage(value):
    raw=json.dumps(value,sort_keys=True)+'\n';assert len(raw)<=16384
    with open(COMBINED_STAGE,'x' if value['sequence']==1 else 'a',encoding='ascii') as output:output.write(raw)
cost=Cost(time.perf_counter_ns,combined_save_cost)
stages=StageCost(time.perf_counter_ns,combined_save_stage)
mem=stages.wrap('gdb_read',cost.wrap_read(mem))
reg=stages.wrap('register',cost.wrap_register(reg))
timeline.sample=stages.wrap('snapshot',timeline.sample)
binary.translate=stages.wrap('translate',binary.translate)
binary.QMP.__init__=stages.wrap('qmp_connect',binary.QMP.__init__)
binary.QMP.stopped=stages.wrap('qmp_status',binary.QMP.stopped)
binary.QMP.save=stages.wrap('qmp_save',binary.QMP.save)
binary.QMP.request=stages.wrap('qmp_request',binary.QMP.request)
binary.QMP.close=stages.wrap('qmp_close',binary.QMP.close)
combined_original_read=binary.Reader.read
combined_large_read=stages.wrap('binary_read',combined_original_read)
def combined_read(self,address,size):
    if type(size) is int and size>=32768:return combined_large_read(self,address,size)
    return combined_original_read(self,address,size)
binary.Reader.read=combined_read
def combined_flush():
    cost.checkpoint(True);stages.checkpoint(True);timeline_flush()
def combined_guard(original):
    wrapped=cost.wrap_stop(original)
    def stop(hook):
        try:return wrapped(hook)
        except Exception as error:
            combined_flush();gdb.write('COMBINED_OBSERVER_FAIL '+repr(error)+'\n');gdb.execute('quit 75')
        finally:stages.checkpoint()
    return stop
Hook.stop=combined_guard(Hook.stop)
ReleaseEnd.stop=combined_guard(ReleaseEnd.stop)
combined_flush()
'''


def combined_observer(original,folder):
    code=timeline_observer('peer-clock',original,folder)
    # Original assertions/traps remain byte-for-byte; only flush before exits.
    code=code.replace("timeline_flush();gdb.execute(","combined_flush();gdb.execute(")
    tail='\nend\ncontinue\n'
    setup='\nCOMBINED_SCRIPTS='+repr(str(ROOT/'scripts'))
    setup+='\nCOMBINED_COST='+repr((folder/'cost.jsonl').as_posix())
    setup+='\nCOMBINED_STAGE='+repr((folder/'stages.jsonl').as_posix())+'\n'
    setup+=inspect.getsource(Cost)+inspect.getsource(StageCost)+COMBINED_BINDING
    return code[:-len(tail)]+setup+tail


def reserve_combined(base,kind):
    if kind not in ('binary','gdb'):raise ValueError('combined mode')
    previous=list(base.iterdir())
    if kind=='binary':
        if previous:raise ValueError('combined binary already reserved')
    else:
        if len(previous)!=1 or not previous[0].name.startswith('binary-'):raise ValueError('combined pair order/budget')
        report=previous[0]/'summary.json'
        if not report.is_file() or not json.loads(report.read_text())['completed']:raise ValueError('combined first diagnosis incomplete')
    folder=base/(kind+'-'+uuid.uuid4().hex);folder.mkdir();return folder


def combined_main(kind):
    prior_path=BASE/'verification-status-file-binary.json';prior=json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status']!='blocked':raise ValueError('combined resume state')
    for name,sha in prior['evidence_sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('preserved binary evidence changed')
    mutable={'automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md',
        'scripts/diagnose_x86_64_file_transport.py','test/test_x86_64_file_transport.py',
        'docs/architecture/X86_64_BOOTSTRAP.md','docs/development/CURRENT_WORK.md',
        'docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
    for name,sha in prior['source_sha256'].items():
        if name not in mutable and digest(ROOT/name)!=sha:raise ValueError('combined changes frozen source '+name)
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    if package['id']!=prior['package'] or 'python scripts/diagnose_x86_64_file_transport.py --combined '+kind not in package['combined_timing_diagnostic']:raise ValueError('combined authority')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('combined image')
    base=BASE/'file-combined';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    folder=reserve_combined(base,kind)
    summary=dict(accepted=False,completed=False,kind=kind,full_oracle_passed=False,
        source_sha256={name:digest(ROOT/name) for name in prior['source_sha256']},
        previous_manifest=dict(path=prior_path.relative_to(ROOT).as_posix(),sha256=digest(prior_path)),image_sha256=digest(image))
    started=time.monotonic()
    try:
        symbols,core,counts,addresses,raw=fixture(image)
        original=launch.observer(symbols,core,folder,0,0,None,addresses,raw)
        code=combined_observer(original,folder);capture_error=None
        media=launch.pio.Fixture(folder,filesystem='fat12',file_program=raw)
        options={'binary_memory':'full'} if kind=='binary' else {}
        begin=time.monotonic()
        try:serial,trace=launch.wide.transport.capture(image,folder,code,4096,media,diagnostic_metrics=True,**options)
        except (ValueError,RuntimeError,OSError) as error:
            capture_error=str(error)
            serial=(folder/'guest.log').read_text() if (folder/'guest.log').is_file() else ''
            trace=(folder/'frame-trace.log').read_text() if (folder/'frame-trace.log').is_file() else ''
        summary['capture_with_cleanup_seconds']=round(time.monotonic()-begin,6)
        summary['capture_error']=capture_error;summary['capture']=json.loads((folder/'capture-metrics.json').read_text())
        summary['reaps']=serial.count('PROCESS_REAP_OK');summary['runs']=serial.count(launch.wide.process.DONE)
        summary['timeline']=timeline_records(folder/'timeline.jsonl')
        summary['cost']=costs(folder/'cost.jsonl')[-1];summary['stages']=stage_costs(folder/'stages.jsonl')[-1]
        if any(marker in serial for marker in launch.wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('combined unexpected guest/observer failure')
        if capture_error and summary['capture']['stop_reason']!='deadline':raise ValueError('combined unexpected capture failure')
        if not capture_error:
            launch.validate(serial,trace,0,0,None,counts,raw);summary['full_oracle_passed']=True
        summary['completed']=True
        print('FILE_COMBINED_DIAGNOSED',kind,'stop='+summary['capture']['stop_reason'],
              'reaps='+str(summary['reaps']),'callbacks='+str(summary['timeline']['callbacks']),
              'samples='+str(len(summary['timeline']['samples'])),'full_oracle='+str(summary['full_oracle_passed']),flush=True)
        return 0
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('FILE_COMBINED_BLOCKED',kind,error);return 1
    finally:
        summary['elapsed_with_cleanup']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('FILE_COMBINED_EVIDENCE',folder)


def continuation_step_probe(execute,save):
    state={}
    for command in ('maintenance packet qqemu.sstepbits','maintenance packet qqemu.sstep'):
        answer=execute(command,to_string=True)
        if type(answer) is not str or len(answer)>8192:raise ValueError('continuation step reply bound')
        state[command.split()[-1]]=answer
    save(state)


def continuation_observer(kind,original,folder):
    if kind not in ('plain','measured'):raise ValueError('continuation mode')
    code=observer('full',original,folder,{}) if kind=='plain' else combined_observer(original,folder)
    tail='\nend\ncontinue\n'
    assert code.endswith(tail)
    setup='\n'+inspect.getsource(continuation_step_probe)
    setup+='def continuation_save_step(state):\n    with open('+repr((folder/'step-state.json').as_posix())+",'x',encoding='ascii') as out:json.dump(state,out)\n"
    setup+='continuation_step_probe(gdb.execute,continuation_save_step)\n'
    return code[:-len(tail)]+setup+tail


def continuation_records(path):
    from datetime import datetime,timezone
    if not path.is_file() or not 0<path.stat().st_size<=8*1024*1024:raise ValueError('continuation trace bytes')
    rows=[]
    pattern=re.compile(r'^\[(\d+)@(\d+)\.(\d{6})\] (\w+)(?: (.*))?$')
    iso=re.compile(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\.(\d{6})Z (.*)$')
    for line in path.read_text(encoding='ascii').splitlines():
        if len(line)>512 or len(rows)>=131072:raise ValueError('continuation trace record cap')
        match=pattern.fullmatch(line)
        if match:row=dict(thread=int(match[1]),ns=int(match[2])*1000000000+int(match[3])*1000,event=match[4],payload=match[5] or '')
        else:
            match=iso.fullmatch(line)
            if not match:raise ValueError('continuation trace schema '+line[:128])
            ns=int(datetime.strptime(match[1],'%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc).timestamp())*1000000000+int(match[2])*1000
            event,_,payload=match[3].partition(' ')
            row=dict(thread=None,ns=ns,event=event,payload=payload)
            # Installed Windows QEMU emits this host-only startup warning.
            # Retain it explicitly; do not ignore arbitrary stderr failures.
            if re.fullmatch(r"C:\\Program Files\\qemu\\qemu-system-x86_64.exe: warning: GLib-GIO: Failed to open application manifest `C:\\Windows\\SystemApps\\[^`\r\n]{1,160}' for package #\d+ \(`[^`\r\n]{1,160}'\): error code 0x2",match[3]):
                if any(r['event']=='host_warning' for r in rows):raise ValueError('continuation repeated host warning')
                row.update(event='host_warning',payload=match[3])
        if row['event'] not in (*launch.wide.transport.CONTINUATION_EVENTS,'host_warning'):raise ValueError('continuation trace event '+line[:128])
        rows.append(row)
    if not rows:raise ValueError('continuation trace empty')
    return rows


def reserve_continuation(base,kind):
    if kind not in ('plain','measured'):raise ValueError('continuation mode')
    previous=list(base.iterdir())
    if kind=='plain':
        if previous:raise ValueError('continuation plain already reserved')
    else:
        if len(previous)!=1 or not previous[0].name.startswith('plain-'):raise ValueError('continuation order/budget')
        report=previous[0]/'summary.json'
        if not report.is_file():raise ValueError('continuation first diagnosis incomplete')
        prior=json.loads(report.read_text())
        if not prior['completed']:
            decoded=previous[0]/'decoded.json'
            if not prior.get('error','').startswith('continuation trace schema ') or not decoded.is_file():raise ValueError('continuation first diagnosis incomplete')
            proof=json.loads(decoded.read_text())
            if not proof['completed'] or proof['previous_summary_sha256']!=digest(report):raise ValueError('continuation decoded source binding')
    folder=base/(kind+'-'+uuid.uuid4().hex);folder.mkdir();return folder


def continuation_main(kind):
    prior_path=BASE/'verification-status-file-combined.json';prior=json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status']!='blocked':raise ValueError('continuation resume state')
    for name,sha in prior['evidence_sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('preserved combined evidence changed')
    mutable={'automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md',
        'scripts/run_qemu_x86_64_boot_programs.py','scripts/diagnose_x86_64_file_transport.py',
        'test/test_x86_64_file_transport.py','test/test_x86_64_block_transport.py',
        'docs/architecture/X86_64_BOOTSTRAP.md','docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
    for name,sha in prior['source_sha256'].items():
        if digest(BASE/'continuation-source'/name.replace('/','__'))!=sha:raise ValueError('continuation source snapshot '+name)
        if name not in mutable and digest(ROOT/name)!=sha:raise ValueError('continuation changes frozen source '+name)
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    if package['id']!=prior['package'] or 'python scripts/diagnose_x86_64_file_transport.py --continuation '+kind not in package['continuation_diagnostic']:raise ValueError('continuation authority')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('continuation image')
    base=BASE/'file-continuation';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    folder=reserve_continuation(base,kind)
    summary=dict(accepted=False,completed=False,kind=kind,full_oracle_passed=False,
        source_sha256={name:digest(ROOT/name) for name in prior['source_sha256']},
        previous_manifest=dict(path=prior_path.relative_to(ROOT).as_posix(),sha256=digest(prior_path)),image_sha256=digest(image))
    started=time.monotonic()
    try:
        import subprocess
        qemu=launch.wide.transport.resolve_qemu(None)
        inventory={}
        for name,args in (('version',['--version']),('events',['-trace','help'])):
            result=subprocess.run([str(qemu),*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode or len(result.stdout)>1048576:raise ValueError('continuation QEMU inventory')
            (folder/('qemu-'+name+'.txt')).write_bytes(result.stdout);inventory[name]=result.stdout.decode('ascii')
        if not set(launch.wide.transport.CONTINUATION_EVENTS)<=set(inventory['events'].splitlines()):raise ValueError('continuation QEMU events unavailable')
        summary['qemu']=dict(path=str(qemu),sha256=digest(qemu),version=inventory['version'].strip())
        symbols,core,counts,addresses,raw=fixture(image)
        original=launch.observer(symbols,core,folder,0,0,None,addresses,raw)
        code=continuation_observer(kind,original,folder);capture_error=None
        media=launch.pio.Fixture(folder,filesystem='fat12',file_program=raw);begin=time.monotonic()
        try:serial,trace=launch.wide.transport.capture(image,folder,code,4096,media,diagnostic_metrics=True,binary_memory='full',trace_continuation=True)
        except (ValueError,RuntimeError,OSError) as error:
            capture_error=str(error)
            serial=(folder/'guest.log').read_text() if (folder/'guest.log').is_file() else ''
            trace=(folder/'frame-trace.log').read_text() if (folder/'frame-trace.log').is_file() else ''
        summary['capture_with_cleanup_seconds']=round(time.monotonic()-begin,6)
        summary['capture_error']=capture_error;summary['capture']=json.loads((folder/'capture-metrics.json').read_text())
        summary['reaps']=serial.count('PROCESS_REAP_OK');summary['runs']=serial.count(launch.wide.process.DONE)
        rows=continuation_records(folder/'stderr.log');summary['trace_events']={name:sum(row['event']==name for row in rows) for name in launch.wide.transport.CONTINUATION_EVENTS}
        summary['trace_records']=len(rows);summary['step_state']=json.loads((folder/'step-state.json').read_text())
        if kind=='measured':
            summary['timeline']=timeline_records(folder/'timeline.jsonl')
            summary['cost']=costs(folder/'cost.jsonl')[-1];summary['stages']=stage_costs(folder/'stages.jsonl')[-1]
        if any(marker in serial for marker in launch.wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('continuation unexpected guest/observer failure')
        if capture_error and (summary['capture']['stop_reason']!='deadline' or capture_error!='program capture/detach failure'):raise ValueError('continuation unexpected capture failure '+capture_error)
        if not capture_error:
            launch.validate(serial,trace,0,0,None,counts,raw);summary['full_oracle_passed']=True
        summary['completed']=True
        print('FILE_CONTINUATION_DIAGNOSED',kind,'stop='+summary['capture']['stop_reason'],'reaps='+str(summary['reaps']),
              'events='+str(len(rows)),'full_oracle='+str(summary['full_oracle_passed']),flush=True);return 0
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('FILE_CONTINUATION_BLOCKED',kind,error);return 1
    finally:
        summary['elapsed_with_cleanup']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('FILE_CONTINUATION_EVIDENCE',folder)


class EquivalenceReadCost:
    """Time only the two original large GDB comparisons, without another read."""
    def __init__(self,clock,save):
        self.clock=clock;self.save=save;self.started=clock();self.last=0
        self.seen=set();self.sequence=0;self.active=False

    def now(self):
        value=self.clock()-self.started
        if not self.last<=value<24000000000:raise ValueError('equivalence cost monotonic deadline')
        self.last=value;return value

    def emit(self,**fields):
        if self.sequence>=4:raise ValueError('equivalence cost record capacity')
        self.sequence+=1
        row=dict(version=1,sequence=self.sequence,ns=self.now(),**fields)
        if len(json.dumps(row))+1>1024:raise ValueError('equivalence cost record extent')
        self.save(row)

    def wrap(self,original):
        def read(address,size):
            if type(size) is not int or not 0<=size<=270336:raise ValueError('equivalence cost read extent')
            if size<32768:return original(address,size)
            if type(address) is not int:raise ValueError('equivalence cost address')
            if 0xffffffff80100000<=address and address+size<=0xffffffff88000000:kind='kernel'
            elif 0xffff800100000000<=address and address+size<=0xffff800140000000:kind='high'
            else:raise ValueError('equivalence cost RAM alias')
            if kind in self.seen or len(self.seen)>=2 or self.active:raise ValueError('equivalence cost call capacity/nesting')
            self.seen.add(kind);self.active=True
            fields=dict(kind=kind,address=address,bytes=size)
            self.emit(event='enter',**fields);start=self.now()
            try:
                raw=original(address,size)
            except BaseException as error:
                elapsed=self.now()-start
                self.emit(event='exception',read_ns=elapsed,error=type(error).__name__[:64],**fields)
                raise
            else:
                elapsed=self.now()-start
                self.emit(event='return',read_ns=elapsed,returned_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),**fields)
                return raw
            finally:self.active=False
        return read


EQUIVALENCE_COST_BINDING=r'''
import time
def equivalence_cost_save(value):
    raw=json.dumps(value,sort_keys=True)+'\n';assert len(raw)<=1024
    with open(EQUIVALENCE_COST_FILE,'x' if value['sequence']==1 else 'a',encoding='ascii') as output:output.write(raw)
equivalence_read_cost=EquivalenceReadCost(time.perf_counter_ns,equivalence_cost_save)
mem=equivalence_read_cost.wrap(mem)
'''


def equivalence_cost_observer(kind,original,folder):
    if kind not in ('minimal','profiled'):raise ValueError('equivalence cost mode')
    code=observer('full' if kind=='minimal' else 'full-profile',original,folder,{})
    tail='\nend\ncontinue\n';assert code.endswith(tail)
    setup='\nEQUIVALENCE_COST_FILE='+repr((folder/'equivalence-cost.jsonl').as_posix())+'\n'
    return code[:-len(tail)]+setup+inspect.getsource(EquivalenceReadCost)+EQUIVALENCE_COST_BINDING+tail


def equivalence_cost_records(path,ledger):
    if not path.is_file() or not 0<path.stat().st_size<=4096:raise ValueError('equivalence cost file capacity')
    lines=path.read_text(encoding='ascii').splitlines()
    if len(lines)!=4 or any(len(line)+1>1024 for line in lines):raise ValueError('equivalence cost complete records')
    rows=[json.loads(line) for line in lines];comparisons=[];last=0
    common={'version','sequence','ns','kind','address','bytes','event'}
    for index,row in enumerate(rows):
        expected=common if index%2==0 else common|{'read_ns','returned_bytes','sha256'}
        if type(row) is not dict or set(row)!=expected:raise ValueError('equivalence cost schema')
        for key in ('version','sequence','ns','address','bytes'):
            if type(row[key]) is not int:raise ValueError('equivalence cost integer')
        if row['version']!=1 or row['sequence']!=index+1 or not last<=row['ns']<24000000000:raise ValueError('equivalence cost sequence/time')
        last=row['ns']
        if row['kind']!=('kernel' if index<2 else 'high') or not 32768<=row['bytes']<=270336:raise ValueError('equivalence cost role/extent')
        if row['event']!=('enter' if index%2==0 else 'return'):raise ValueError('equivalence cost event')
        if index%2:
            enter=rows[index-1]
            if any(row[k]!=enter[k] for k in ('kind','address','bytes')):raise ValueError('equivalence cost call identity')
            if type(row['read_ns']) is not int or not 0<=row['read_ns']<=row['ns']-enter['ns']:raise ValueError('equivalence cost read interval')
            if type(row['returned_bytes']) is not int or row['returned_bytes']!=row['bytes']:raise ValueError('equivalence cost returned extent')
            if type(row['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('equivalence cost hash')
            matches=[r for r in ledger if r['equivalence']==row['kind']]
            if len(matches)!=1 or any(matches[0][k]!=row[k] for k in ('address','bytes','sha256')):raise ValueError('equivalence cost dump binding')
            comparisons.append(dict(row,enter_ns=enter['ns']))
    return dict(comparison_ns=sum(r['read_ns'] for r in comparisons),comparison_bytes=sum(r['bytes'] for r in comparisons),comparisons=comparisons)


def reserve_equivalence_cost(base,kind):
    if kind not in ('minimal','profiled'):raise ValueError('equivalence cost mode')
    previous=list(base.iterdir())
    if kind=='minimal':
        if previous:raise ValueError('equivalence cost minimal already reserved')
    else:
        if len(previous)!=1 or not previous[0].name.startswith('minimal-'):raise ValueError('equivalence cost order/budget')
        report=previous[0]/'summary.json'
        if not report.is_file() or not json.loads(report.read_text())['completed']:raise ValueError('equivalence cost first diagnosis incomplete')
    folder=base/(kind+'-'+uuid.uuid4().hex);folder.mkdir();return folder


def equivalence_cost_main(kind):
    prior_path=BASE/'verification-status-file-continuation.json';prior=json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status']!='blocked':raise ValueError('equivalence cost resume state')
    for name,sha in prior['evidence_sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('preserved continuation evidence changed')
    mutable={'automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md',
        'scripts/diagnose_x86_64_file_transport.py','test/test_x86_64_file_transport.py',
        'docs/architecture/X86_64_BOOTSTRAP.md','docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
    for name,sha in prior['source_sha256'].items():
        if digest(BASE/'equivalence-cost-source'/name.replace('/','__'))!=sha:raise ValueError('equivalence cost source snapshot '+name)
        if name not in mutable and digest(ROOT/name)!=sha:raise ValueError('equivalence cost frozen source '+name)
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    if package['id']!=prior['package'] or 'python scripts/diagnose_x86_64_file_transport.py --equivalence-cost '+kind not in package['equivalence_cost_diagnostic']:raise ValueError('equivalence cost authority')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('equivalence cost image')
    qemu=prior['guests'][0]['qemu']
    if digest(Path(qemu['path']))!=qemu['sha256']:raise ValueError('equivalence cost QEMU changed')
    base=BASE/'file-equivalence-cost';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    folder=reserve_equivalence_cost(base,kind)
    summary=dict(accepted=False,completed=False,kind=kind,full_oracle_passed=False,within_original_deadline=False,
        source_sha256={name:digest(ROOT/name) for name in prior['source_sha256']},qemu=qemu,
        previous_manifest=dict(path=prior_path.relative_to(ROOT).as_posix(),sha256=digest(prior_path)),image_sha256=digest(image))
    started=time.monotonic()
    try:
        symbols,core,counts,addresses,raw=fixture(image)
        original=launch.observer(symbols,core,folder,0,0,None,addresses,raw)
        code=equivalence_cost_observer(kind,original,folder);capture_error=None
        media=launch.pio.Fixture(folder,filesystem='fat12',file_program=raw);begin=time.monotonic()
        try:serial,trace=launch.wide.transport.capture(image,folder,code,4096,media,diagnostic_metrics=True,binary_memory='equivalence')
        except (ValueError,RuntimeError,OSError) as error:
            capture_error=str(error)
            serial=(folder/'guest.log').read_text() if (folder/'guest.log').is_file() else ''
            trace=(folder/'frame-trace.log').read_text() if (folder/'frame-trace.log').is_file() else ''
        summary['capture_with_cleanup_seconds']=round(time.monotonic()-begin,6)
        summary['capture_error']=capture_error;summary['capture']=json.loads((folder/'capture-metrics.json').read_text())
        summary['reaps']=serial.count('PROCESS_REAP_OK');summary['runs']=serial.count(launch.wide.process.DONE)
        ledger=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
        if not 1<=len(ledger)<=2048 or sum(r['bytes'] for r in ledger)>128*1024*1024:raise ValueError('equivalence cost dump capacity')
        for index,row in enumerate(ledger,1):
            dump=folder/'binary-memory'/('ram-%04d.bin'%index)
            if row['sequence']!=index or row['file']!=dump.name or dump.stat().st_size!=row['bytes'] or digest(dump)!=row['sha256']:raise ValueError('equivalence cost dump identity')
        summary['comparisons']=equivalence_cost_records(folder/'equivalence-cost.jsonl',ledger)
        if kind=='profiled':summary['cost']=costs(folder/'cost.jsonl')[-1]
        if any(marker in serial for marker in launch.wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('equivalence cost unexpected guest/observer failure')
        if capture_error and (summary['capture']['stop_reason']!='deadline' or capture_error!='program capture/detach failure'):raise ValueError('equivalence cost unexpected capture failure '+capture_error)
        if not capture_error:
            launch.validate(serial,trace,0,0,None,counts,raw);summary['full_oracle_passed']=True
            summary['within_original_deadline']=summary['capture_with_cleanup_seconds']<=20
        summary['completed']=True
        print('FILE_EQUIVALENCE_COST_DIAGNOSED',kind,'stop='+summary['capture']['stop_reason'],'reaps='+str(summary['reaps']),
              'comparison_ns='+str(summary['comparisons']['comparison_ns']),'full_oracle='+str(summary['full_oracle_passed']),flush=True);return 0
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('FILE_EQUIVALENCE_COST_BLOCKED',kind,error);return 1
    finally:
        summary['elapsed_with_cleanup']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('FILE_EQUIVALENCE_COST_EVIDENCE',folder)


def case6_timing_observer(kind,original,folder):
    if kind=='minimal':return timeline_observer('stops',original,folder)
    if kind=='profiled':return combined_observer(original,folder)
    raise ValueError('case6 timing selector')


def case6_timing_capture(image,folder,code,media):
    return launch.wide.transport.capture(image,folder,code,4096,media,diagnostic_metrics=True,binary_memory='full')


def case6_timing_image(package):
    name='build/codex-agent/r83am-file-launch/oom-boundary-renewal/guests/attempt-34ee1dafaa1c4d80bb67d75e6c11aa47/build-6-2/x86_64/reist-x86_64-bootstrap.elf'
    sha='6a5d2859f8d57112c4884d42d9afaee2ea552c735f7110d244668895238104b3'
    if package['case6_timing_image']!=name or package['case6_timing_image_sha256']!=sha:raise ValueError('case6 timing image identity')
    image=ROOT/name
    if image.resolve()!=image or digest(image)!=sha:raise ValueError('case6 timing image bytes/path')
    return image


def reserve_case6_timing(base,kind):
    # Same exclusive two-control protocol; independent, never reused directory.
    return reserve_equivalence_cost(base,kind)


def case6_timing_main(kind):
    return timing_main(kind,'case6')


def fat12_timing_image(package):
    name='build/codex-agent/r83am-file-launch/post-case6-renewal/guests/attempt-399aa05cf7914430afdf9bda934882a9/build-0-0/x86_64/reist-x86_64-bootstrap.elf'
    sha='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8'
    if package['fat12_timing_image']!=name or package['fat12_timing_image_sha256']!=sha:raise ValueError('fat12 timing image identity')
    image=ROOT/name
    if image.resolve()!=image or digest(image)!=sha:raise ValueError('fat12 timing image bytes/path')
    return image


def timing_profile(profile):
    if profile=='case6':return 6,2,'ext2-1k','verification-status-oom-boundary.json',case6_timing_image
    if profile=='fat12':return 0,0,'fat12','verification-status-post-case6.json',fat12_timing_image
    raise ValueError('fixed timing profile')


def timing_main(kind,profile):
    case,layout,filesystem,previous,image_reader=timing_profile(profile)
    if kind not in ('minimal','profiled'):raise ValueError('fixed timing control')
    frozen_path=BASE/(profile+'-timing-freeze.json');frozen=json.loads(frozen_path.read_text())
    prior_path=BASE/previous;prior=json.loads(prior_path.read_text())
    if prior['accepted'] or prior['status']!='blocked' or digest(prior_path)!=frozen['previous_manifest']['sha256']:raise ValueError('case6 timing resume state')
    for name,sha in {**frozen['source_sha256'],**frozen['helper_sha256'],**frozen['tools_sha256']}.items():
        if digest(ROOT/name)!=sha:raise ValueError('case6 timing frozen input '+name)
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    if package['id']!=prior['package'] or 'python scripts/diagnose_x86_64_file_transport.py --'+profile+'-timing '+kind not in package[profile+'_timing_commands']:raise ValueError('file timing authority')
    image=image_reader(package)
    if package[profile+'_timing_prefix']!='build/codex-agent/r83am-file-launch/'+profile+'-timing/':raise ValueError('file timing evidence scope')
    base=BASE/(profile+'-timing');base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    folder=reserve_case6_timing(base,kind)
    summary=dict(accepted=False,completed=False,kind=kind,case=case,layout=layout,ram=4096,oom=None,
        full_oracle_passed=False,within_original_deadline=False,source_sha256=frozen['source_sha256'],
        frozen_sha256=digest(frozen_path),image_sha256=digest(image))
    started=time.monotonic()
    try:
        symbols,core,counts,addresses,raw=fixture(image)
        original=launch.observer(symbols,core,folder,case,layout,None,addresses,raw)
        code=case6_timing_observer(kind,original,folder);capture_error=None
        media=launch.pio.Fixture(folder,filesystem=filesystem,file_program=raw);begin=time.monotonic()
        try:serial,trace=case6_timing_capture(image,folder,code,media)
        except (ValueError,RuntimeError,OSError) as error:
            capture_error=str(error)
            serial=(folder/'guest.log').read_text() if (folder/'guest.log').is_file() else ''
            trace=(folder/'frame-trace.log').read_text() if (folder/'frame-trace.log').is_file() else ''
        summary['capture_with_cleanup_seconds']=round(time.monotonic()-begin,6)
        summary['capture_error']=capture_error;summary['capture']=json.loads((folder/'capture-metrics.json').read_text())
        summary['reaps']=serial.count('PROCESS_REAP_OK');summary['runs']=serial.count(launch.wide.process.DONE)
        summary['timeline']=timeline_records(folder/'timeline.jsonl')
        if kind=='profiled':
            summary['cost']=costs(folder/'cost.jsonl')[-1];summary['stages']=stage_costs(folder/'stages.jsonl')[-1]
        ledger=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
        if not 1<=len(ledger)<=2048 or sum(r['bytes'] for r in ledger)>128*1024*1024:raise ValueError('case6 timing dump capacity')
        for index,row in enumerate(ledger,1):
            dump=folder/'binary-memory'/('ram-%04d.bin'%index)
            if row['sequence']!=index or row['file']!=dump.name or dump.stat().st_size!=row['bytes'] or digest(dump)!=row['sha256'] or row['equivalence'] is not None:raise ValueError('case6 timing dump identity')
        if any(marker in serial for marker in launch.wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('case6 timing unexpected guest/observer failure')
        if capture_error and (summary['capture']['stop_reason']!='deadline' or capture_error!='program capture/detach failure'):raise ValueError('case6 timing unexpected capture failure '+capture_error)
        if not capture_error:
            launch.validate(serial,trace,case,layout,None,counts,raw);summary['full_oracle_passed']=True
            summary['within_original_deadline']=summary['capture_with_cleanup_seconds']<=20
        summary['completed']=True
        print(profile.upper()+'_TIMING_DIAGNOSED',kind,'stop='+summary['capture']['stop_reason'],'reaps='+str(summary['reaps']),
            'samples='+str(len(summary['timeline']['samples'])),'full_oracle='+str(summary['full_oracle_passed']),flush=True)
        return 0
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print(profile.upper()+'_TIMING_BLOCKED',kind,error);return 1
    finally:
        summary['elapsed_with_cleanup']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        with (folder/'summary.json').open('x',encoding='utf-8') as output:json.dump(summary,output,indent=2);output.write('\n')
        print(profile.upper()+'_TIMING_EVIDENCE',folder)


def main():
    parser=argparse.ArgumentParser();select=parser.add_mutually_exclusive_group()
    select.add_argument('--followup',choices=FOLLOWUP);select.add_argument('--timeline',choices=('stops','peer-clock'))
    select.add_argument('--binary',choices=('equivalence','full'))
    select.add_argument('--combined',choices=('binary','gdb'))
    select.add_argument('--continuation',choices=('plain','measured'))
    select.add_argument('--equivalence-cost',choices=('minimal','profiled'))
    select.add_argument('--case6-timing',choices=('minimal','profiled'))
    select.add_argument('--fat12-timing',choices=('minimal','profiled'));args=parser.parse_args()
    if args.fat12_timing:return timing_main(args.fat12_timing,'fat12')
    if args.case6_timing:return case6_timing_main(args.case6_timing)
    if args.equivalence_cost:return equivalence_cost_main(args.equivalence_cost)
    if args.continuation:return continuation_main(args.continuation)
    if args.combined:return combined_main(args.combined)
    if args.binary:return binary_main(args.binary)
    if args.timeline:return timeline_main(args.timeline)
    prior_path=BASE/'verification-status-legacy-sleep.json';prior=json.loads(prior_path.read_text())
    for path,expected in prior['evidence_sha256'].items():
        if digest(ROOT/path)!=expected:raise ValueError('preserved legacy evidence changed')
    image=BASE/'timer-idle-fixed/x86_64/reist-x86_64-bootstrap.elf'
    if digest(image)!='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8':raise ValueError('fixed transport image')
    base=BASE/'file-transport';base.mkdir(exist_ok=True);launch.pio.safe_folder(base)
    if args.followup:
        initial=list(base.glob('initial-*/summary.json'))
        if len(initial)!=1 or not json.loads(initial[0].read_text())['completed']:raise ValueError('complete initial controls first')
        queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
        package=next(p for p in queue['packages'] if p['id']=='R8.3am-x86_64-file-launch')
        if args.followup not in package['file_transport_followups']:raise ValueError('followup not frozen')
        previous=list(base.glob('followup-*'))
        if len(previous)>=2 or any(json.loads((p/'summary.json').read_text())['cases'][0]['kind']==args.followup for p in previous):raise ValueError('followup already spent')
    elif any(base.glob('initial-*')):raise ValueError('initial controls already reserved')
    folder=base/(('followup-' if args.followup else 'initial-')+uuid.uuid4().hex);folder.mkdir()
    symbols,core,counts,addresses,raw=fixture(image)
    summary=dict(accepted=False,diagnostic_only=True,completed=False,cases=[],image_sha256=digest(image),
                 previous_manifest=dict(path=str(prior_path.relative_to(ROOT)),sha256=digest(prior_path)))
    summary['source_sha256']={name:digest(ROOT/name) for name in ('scripts/run_qemu_x86_64_file_launch.py','scripts/diagnose_x86_64_file_transport.py','scripts/run_qemu_x86_64_boot_programs.py')}
    started=time.monotonic()
    try:
        for kind in (args.followup,) if args.followup else INITIAL:
            out=folder/kind;out.mkdir()
            original=launch.observer(symbols,core,out,0,0,None,addresses,raw)
            code=observer(kind,original,out,symbols);error=None;begin=time.monotonic()
            try:serial,trace=launch.wide.transport.capture(image,out,code,4096,launch.pio.Fixture(out,filesystem='fat12',file_program=raw),diagnostic_metrics=True)
            except (ValueError,RuntimeError,OSError) as failure:
                error=str(failure);serial=(out/'guest.log').read_text() if (out/'guest.log').exists() else '';trace=(out/'frame-trace.log').read_text() if (out/'frame-trace.log').exists() else ''
            metrics=json.loads((out/'capture-metrics.json').read_text())
            row=dict(kind=kind,elapsed_with_cleanup=round(time.monotonic()-begin,3),capture_error=error,capture=metrics,full_oracle_passed=False)
            summary['cases'].append(row)
            row['receipts']=[struct.unpack('<4I2Q',bytes.fromhex(match[1])) for match in launch.wide.process.REAP.finditer(serial)]
            row['runs']=serial.count(launch.wide.process.DONE)
            if kind.endswith('profile'):row['cost']=costs(out/'cost.jsonl')[-1]
            if not error and kind.startswith('full'):
                launch.validate(serial,trace,0,0,None,counts,raw);row['full_oracle_passed']=True
            if any(marker in serial for marker in launch.wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('unexpected guest/observer failure; inspect bounded evidence')
            if error and metrics.get('stop_reason')!='deadline':raise ValueError('unexpected transport failure')
            print('FILE_TRANSPORT_CONTROL',kind,'stop='+metrics.get('stop_reason','unknown'),'elapsed='+str(row['elapsed_with_cleanup']), 'full_oracle='+str(row['full_oracle_passed']),flush=True)
        summary['completed']=True
    except (ValueError,RuntimeError,OSError) as error:
        summary['error']=str(error);print('FILE_TRANSPORT_DIAGNOSTIC_BLOCKED',error);return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        summary['evidence_sha256']={str(p.relative_to(folder)):digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('FILE_TRANSPORT_EVIDENCE',folder)
    return 0


if __name__=='__main__':raise SystemExit(main())
