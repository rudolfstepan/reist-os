"""Six pinned transport controls, never a replacement for profile acceptance."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time
import run_qemu_x86_64_block_profile as profile
ROOT=profile.ROOT
BASE=ROOT/'build/codex-agent/r83ak-block-profile/transport-diagnostic'
INITIAL=('detached','finish','rpc-noop','rpc-metadata','full','full-hardware')
FOLLOWUP=('rpc-pio-page','full-lifecycle')

SIMPLE=r'''
import gdb,struct,json
S=CONFIG['s'];runs=0;callbacks=0
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def q(a):return struct.unpack('<Q',mem(a,8))[0]
class Hook(gdb.Breakpoint):
    def __init__(self,name,fn):
        super().__init__('*'+hex(S[name]),internal=True);self.fn=fn
    def stop(self):
        global callbacks
        callbacks+=1
        if callbacks>4096:raise ValueError('diagnostic callback cap')
        self.fn();return False
def finish():
    global runs
    runs+=1;assert runs<=2
    if runs==2:gdb.execute('detach');gdb.execute('quit')
def rpc():
    if CONFIG['diagnostic_kind'] not in ('rpc-metadata','rpc-pio-page'):return
    slot=struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0];assert slot<4
    number=q(S['syscall_rax'])
    if number!=53:return
    gen=q(S['scheduler_tasks']+slot*1024+8)
    tick=q(S['scheduler_last_tick']);budget=struct.unpack('<4Q',mem(S['scheduler_cpu_budgets']+slot*32,32))
    assert gen==budget[0] and 0<=budget[2]<=budget[1]<=32
    gdb.write('TRANSPORT_SAMPLE '+json.dumps(dict(slot=slot,gen=gen,tick=tick,cpu=budget[2]))+'\n')
def pid():pass
def parked():pass
if CONFIG['diagnostic_kind']!='detached':Hook('x86_64_c_process_run64.restore',finish)
if CONFIG['diagnostic_kind'].startswith('rpc-'):
    Hook('process_ipc_syscall64',rpc);Hook('process_run_syscall64.pid',pid)
if CONFIG['diagnostic_kind']=='rpc-pio-page':Hook('native_pio_finish64.trace_before_clear',parked)
'''

MEASURE=r'''
import time
cost=dict(version=1,callbacks=0,reads=0,bytes=0,registers=0,host_ns=0,functions={})
cost_active=None;cost_reported=False
def cost_leave():
    global cost_active
    if cost_active is not None:
        name,started=cost_active;elapsed=time.perf_counter_ns()-started
        cost['host_ns']+=elapsed;cost['functions'][name]['host_ns']+=elapsed;cost_active=None
def cost_report():
    global cost_reported
    if cost_reported:return
    cost_leave();cost_reported=True
    gdb.write('TRANSPORT_COST '+json.dumps(cost,sort_keys=True)+'\n')
original_mem=mem;original_reg=reg
def measured_mem(a,n):
    assert type(n)==int and 0<=n<=270336
    cost['reads']+=1;cost['bytes']+=n
    assert cost['reads']<=1000000 and cost['bytes']<=33554432
    return original_mem(a,n)
def measured_reg(n):
    cost['registers']+=1;assert cost['registers']<=1000000
    return original_reg(n)
mem=measured_mem;reg=measured_reg
def measured_stop(original):
    def stop(self):
        global cost_active
        name=self.fn.__name__ if hasattr(self,'fn') else type(self).__name__
        assert cost_active is None
        cost['callbacks']+=1;assert cost['callbacks']<=4096
        item=cost['functions'].setdefault(name,dict(calls=0,host_ns=0));item['calls']+=1
        assert len(cost['functions'])<=32
        cost_active=(name,time.perf_counter_ns())
        try:return original(self)
        except Exception:
            cost_report();raise
        finally:cost_leave()
    return stop
Hook.stop=measured_stop(Hook.stop)
if 'ReleaseEnd' in globals():ReleaseEnd.stop=measured_stop(ReleaseEnd.stop)
for query in ('qqemu.sstepbits','qqemu.sstep'):
    reply=gdb.execute('maintenance packet '+query,to_string=True)
    assert len(reply)<=1024
    gdb.write('TRANSPORT_QUERY '+json.dumps(dict(query=query,reply=reply))+'\n')
'''


def body(kind):
    if kind not in INITIAL+FOLLOWUP:raise ValueError('diagnostic kind')
    code=profile.observer_body(scoped=False) if kind.startswith('full') else SIMPLE
    if kind=='full-lifecycle':code=profile.scope_pio_page_hooks(code)
    if kind=='full-hardware':
        for old,new in (("super().__init__('*'+hex(S[name]),internal=True)","super().__init__('*'+hex(S[name]),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)"),
                        ("super().__init__('*'+hex(addr),internal=True,temporary=True)","super().__init__('*'+hex(addr),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True,temporary=True)")):
            code=profile.once(code,old,new)
    code=code.replace("gdb.execute('detach')","cost_report();gdb.execute('detach')")
    code=code.replace("gdb.execute('quit", "cost_report();gdb.execute('quit")
    return code+MEASURE+("\ncost_report();gdb.execute('detach');gdb.execute('quit')\n" if kind=='detached' else '')


def costs(trace):
    rows=re.findall(r'^TRANSPORT_COST (.*)$',trace,re.M)
    if len(rows)!=1 or trace.count('TRANSPORT_COST')!=1:raise ValueError('diagnostic exact cost record')
    v=json.loads(rows[0]);fields={'version','callbacks','reads','bytes','registers','host_ns','functions'}
    if not isinstance(v,dict) or set(v)!=fields or type(v['version'])!=int or v['version']!=1:raise ValueError('diagnostic metric fields')
    for name,limit in (('callbacks',4096),('reads',1000000),('bytes',33554432),('registers',1000000),('host_ns',20000000000)):
        if type(v[name])!=int or not 0<=v[name]<=limit:raise ValueError('diagnostic metric bound')
    f=v['functions']
    if not isinstance(f,dict) or len(f)>32:raise ValueError('diagnostic function bound')
    for name,item in f.items():
        if not re.fullmatch('[A-Za-z_]{1,32}',name) or not isinstance(item,dict) or set(item)!={'calls','host_ns'} or type(item['calls'])!=int or not 0<item['calls']<=4096 or type(item['host_ns'])!=int or not 0<=item['host_ns']<=v['host_ns']:raise ValueError('diagnostic function record')
    if sum(i['calls'] for i in f.values())!=v['callbacks'] or sum(i['host_ns'] for i in f.values())!=v['host_ns']:raise ValueError('diagnostic metric accounting')
    return v


def outcome(serial,trace,kind,capture_error,count):
    if any(m in serial for m in profile.wide.transport.FAILURES):raise ValueError('diagnostic kernel failure')
    matches=list(profile.wide.process.REAP.finditer(serial))
    rows=[struct.unpack('<4I2Q',bytes.fromhex(m[1])) for m in matches]
    if len(rows)!=serial.count('PROCESS_REAP_OK') or not 3<=len(rows)<=8:raise ValueError('diagnostic receipt bounds')
    try:
        profile.receipts(serial,0)
        if capture_error or 'OBSERVER_FAIL' in trace:raise ValueError('diagnostic normal observer error')
        if kind.startswith('full'):profile.validate(serial,trace,0,None,count)
        return dict(classification='normal',receipts=rows,accepted=False)
    except ValueError:
        # A known fail-closed reference outcome, never a pass of the OS gate.
        if len(rows) not in (3,6):raise ValueError('diagnostic unclassified outcome')
        ends=list(re.finditer(profile.wide.process.DONE,serial))
        if len(ends)!=len(rows)//3:raise ValueError('diagnostic run boundary')
        for run in range(len(rows)//3):
            expected={(0,run*3+1):(221,4),(1,run*3+2):(77,4),(2,run*3+3):(256,3)}
            for slot,gen,status,state,ticks,rip in rows[run*3:run*3+3]:
                if expected.pop((slot,gen),None)!=(status,state) or ticks>32 or status==256 and ticks!=32 or not 0x410000<=rip<0x440000:raise ValueError('diagnostic unexpected receipt')
            if expected:raise ValueError('diagnostic missing receipt')
            if any(not (ends[run-1].end() if run else -1)<m.start()<m.end()<ends[run].start() for m in matches[run*3:run*3+3]):raise ValueError('diagnostic receipt ordering')
        failures=[json.loads(line[8:]) for line in trace.splitlines() if line.startswith('PROFILE ') and 'OBSERVER_FAIL' in line]
        if capture_error:
            if capture_error!='program capture/detach failure' or not kind.startswith('full') or len(failures)!=1 or failures[0].get('where')!='finish':raise ValueError('diagnostic unexpected transport failure')
        elif failures or serial.count(profile.wide.process.SUCCESS)!=1 or len(rows)!=6:raise ValueError('diagnostic missing continuation')
        return dict(classification='cpu_bound',receipts=rows,accepted=False)


def catalog_source(directory,catalog):
    if len(catalog)!=4*profile.wide.SIZE:raise ValueError('diagnostic catalog size')
    paths=sorted(directory.glob('programs-*'))
    if len(paths)>128:raise ValueError('diagnostic build history cap')
    for p in paths:
        path=p/'boot-programs.bin'
        if not p.is_dir() or not path.is_file() or path.stat().st_size!=len(catalog):continue
        if path.read_bytes()==catalog:return p
    raise ValueError('diagnostic catalog provenance')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--follow-up',choices=FOLLOWUP);args=parser.parse_args()
    image=args.image.resolve()
    if not image.is_relative_to(ROOT/'build/codex-agent'):raise ValueError('diagnostic image scope')
    inner=profile.wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=profile.wide.payload.validate(inner)
    profile.wide.payload.verify_outer(inner,profile.wide.payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    count=profile.wide.allocations(catalog[2*profile.wide.SIZE:3*profile.wide.SIZE])
    candidate=catalog_source(image.parent,catalog)
    files=(image,image.parent/'reist-x86_64-c-core.elf',image.parent/'boot-programs.bin')
    def hashes():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=hashes()
    pinned=json.loads((BASE.parent/'verification-status-trace.json').read_text())['artifacts']
    if any(pinned.get(p.relative_to(ROOT).as_posix())!=original[p.name] for p in files):raise ValueError('diagnostic pinned image mismatch')
    s=profile.wide.transport.symbols(image)
    config=dict(s=s,cs={n:v['value'] for n,v in c['symbols'].items()},case=0,oom=None,trace_fault=None,
                result_address=profile.map_symbol(candidate/'program0.map','block_profile_result_record'),service_address=profile.map_symbol(candidate/'program2.map','service'))
    used=0;previous_time=0
    if args.follow_up:
        initial=json.loads((BASE/'initial/summary.json').read_text())
        if not initial['completed'] or initial['image_hashes']!=original:raise ValueError('diagnostic initial prerequisite')
        used=len(initial['cases']);previous_time=initial['guest_elapsed']
        for other in FOLLOWUP:
            path=BASE/other
            if path.exists():
                used+=1
                record=json.loads((path/'summary.json').read_text());previous_time+=record['guest_elapsed']
        if used>=8:raise ValueError('diagnostic guest capacity')
    folder=BASE/(args.follow_up or 'initial');folder.mkdir(parents=True,exist_ok=False);profile.pio.safe_folder(folder)
    summary=dict(diagnostic_only=True,accepted=False,completed=False,image_hashes=original,cases=[]);started=time.monotonic();total=0
    try:
        for kind in (args.follow_up,) if args.follow_up else INITIAL:
            if hashes()!=original:raise ValueError('diagnostic image drift')
            out=folder/kind;out.mkdir();config['diagnostic_kind']=kind
            code='set breakpoint always-inserted on\nset logging file '+(out/'frame-trace.log').as_posix()+'\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+repr(config)+'\n'+body(kind)+'\nend\ncontinue\n'
            (out/'selection.json').write_text(json.dumps(dict(kind=kind,ram=4096,limit_seconds=20,image_hashes=original)),encoding='utf-8')
            begin=time.monotonic();capture_error=None
            try:serial,trace=profile.wide.transport.capture(image,out,code,4096,profile.pio.Fixture(out,block=True),diagnostic_metrics=True)
            except ValueError as error:
                capture_error=str(error)
                serial=(out/'guest.log').read_text(encoding='ascii');trace=(out/'frame-trace.log').read_text(encoding='utf-8')
            elapsed=time.monotonic()-begin;total+=elapsed
            if elapsed>20 or total+previous_time>160:raise ValueError('diagnostic guest deadline')
            metrics=json.loads((out/'capture-metrics.json').read_text())
            if not metrics['spawned'] or not metrics['cpu'] or 'cpu_error' in metrics:raise ValueError('diagnostic process counters')
            row=dict(kind=kind,elapsed=round(elapsed,3),capture=metrics,cost=costs(trace),**outcome(serial,trace,kind,capture_error,count))
            summary['cases'].append(row)
            (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print('TRANSPORT_DIAGNOSTIC',kind,row['classification'],'cpu_ns='+str(sum(metrics['cpu'].values())),'callbacks='+str(row['cost']['callbacks']),flush=True)
        if hashes()!=original:raise ValueError('diagnostic final image drift')
        summary['completed']=True;return 0
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('TRANSPORT_DIAGNOSTIC_FAIL',error);return 1
    finally:
        summary.update(elapsed=round(time.monotonic()-started,3),guest_elapsed=round(total,3))
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print('TRANSPORT_DIAGNOSTIC_EVIDENCE',folder)


if __name__=='__main__':raise SystemExit(main())
