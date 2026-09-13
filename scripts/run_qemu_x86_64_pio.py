"""Bounded real ATA PIO proof; generated media only, never user disks."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid,stat,inspect
import run_qemu_x86_64_task_startup as startup
import build_x86_64_boot_programs as producer
from run_qemu_x86_64_runtime_clock import once
ROOT=Path(__file__).resolve().parents[1]
SECTOR=bytes((n^0xa5)&255 for n in range(512))
DISK=SECTOR*128

def regular(path,limit):
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400 or
            info.st_nlink!=1 or not 0<info.st_size<=limit):raise ValueError('unsafe fixture file')

def safe_folder(folder):
    folder=Path(folder).absolute()
    anchor=ROOT/'build/codex-agent'
    if not folder.is_relative_to(anchor) or folder==anchor:raise ValueError('fixture scope')
    for part in (folder,*folder.parents):
        if part==ROOT:break
        info=part.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400 or part.is_symlink():
            raise ValueError('fixture alias')
    if folder!=folder.resolve():raise ValueError('fixture traversal')
    return folder

class Fixture:
    def __init__(self,folder):
        self.folder=safe_folder(folder)
        self.base=self.folder/'generated.raw';self.overlay=self.folder/'disposable.qcow2'
        self.tool=startup.family.programs.resolve_qemu(None).parent/'qemu-img.exe'
        self.commands=[]
        if self.base.exists() or self.overlay.exists():raise ValueError('fixture already exists')
        with self.base.open('xb') as out:out.write(DISK)
        self.run('create','-f','qcow2','-F','raw','-b',str(self.base),str(self.overlay))

    def run(self,*args):
        r=subprocess.run([str(self.tool),*args],cwd=ROOT,capture_output=True,text=True,timeout=10,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.commands.append(dict(args=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (self.folder/'media-commands.json').write_text(json.dumps(self.commands,indent=2),encoding='utf-8')
        if r.returncode:raise ValueError('fixture tool: '+r.stderr[-1000:])
        return r.stdout

    def paths(self):
        if safe_folder(self.folder)!=self.folder or self.base!=self.folder/'generated.raw' or self.overlay!=self.folder/'disposable.qcow2':
            raise ValueError('fixture path change')
        regular(self.base,65536);regular(self.overlay,4*1024*1024)

    def arguments(self,folder):
        self.paths()
        if safe_folder(folder)!=self.folder:raise ValueError('fixture wrong guest')
        nodes=[{'driver':'file','filename':str(self.base),'node-name':'pio-base-file','read-only':True},
               {'driver':'raw','file':'pio-base-file','node-name':'pio-base','read-only':True},
               {'driver':'qcow2','file':{'driver':'file','filename':str(self.overlay)},
                'backing':'pio-base','node-name':'pio-layer'}]
        args=[]
        for node in nodes:args+=['-blockdev',json.dumps(node,separators=(',',':'))]
        return args+['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0']

    def verify(self,phase):
        result=dict(passed=False,phase=phase)
        try:
            self.paths()
            raw=self.base.read_bytes();result['base_sha256']=hashlib.sha256(raw).hexdigest()
            if raw!=DISK:raise ValueError('generated base changed')
            info=json.loads(self.run('info','--output=json','-f','qcow2',str(self.overlay)))
            if (info['format']!='qcow2' or info['virtual-size']!=65536 or
                    Path(info['full-backing-filename'])!=self.base or info['backing-filename-format']!='raw'):
                raise ValueError('overlay backing mismatch')
            extents=json.loads(self.run('map','--output=json','-f','qcow2',str(self.overlay)))
            end=0
            for item in extents:
                if item['start']!=end or item['length']<=0 or item['depth']!=1:
                    raise ValueError('allocated overlay data or incomplete map')
                end+=item['length']
            if end!=65536:raise ValueError('overlay extent')
            self.run('compare','-f','qcow2','-F','raw',str(self.overlay),str(self.base))
            result.update(passed=True,overlay_allocated_data=0,logical_bytes=65536,extents=extents)
        except Exception as error:
            result['error']=str(error);raise
        finally:
            (self.folder/('media-'+phase+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')

def modes(case):
    return [2] if case==3 else [0] if case==2 else [0,1,0,2,0,3,4,0][case==1:]

def minimum_scrubs(case):
    # Three rejected profiles, optional injected create, each actual create,
    # stale WAIT after reap (except owner loss), and final exhausted CREATE.
    count=len(modes(case))
    return 2*(3+(case==1)+count+(count if case!=3 else 0)+(case<2))

def observer(s,c,folder,ram,case,oom,record):
    code=startup.observer(s,c,folder,ram,oom,record)
    # Observe the actual completed scrub, not every unrelated PIO/sleep syscall.
    code=once(code,"class StartupScrub(gdb.Breakpoint):\n    def __init__(self):super().__init__('*'+hex("+str(s['process_run_resume64'])+"),internal=True)",
              "class StartupScrub(gdb.Breakpoint):\n    def __init__(self):super().__init__('*'+hex("+str(s['family_result64.scrubbed'])+"),internal=True)")
    code=once(code,"[0]==3","[0]==4")
    code=once(code,'(gen,plan[1],0,16 if slot<2 else 0)',
              '(gen,plan[1],(1<<49) if slot!=1 else 0,16 if slot<2 else 0)')
    # No simultaneous pair is requested by this consumer; retain independent
    # mapping, profile, startup copy and every frame-retirement assertion.
    pair=re.search(r'            if slot==3:\n.*?private=1.*?\n',code,re.S)
    if pair is None:raise ValueError('import pair observer inventory')
    code=code[:pair.start()]+code[pair.end():]
    fence=f'''assert not any(mem({s['family_extended_masks']}+slot*16,16))
pio_retire(slot,gen)
'''
    code=once(code,"gdb.write('FAMILY_FENCE",fence+"gdb.write('FAMILY_FENCE")
    code=once(code,"gdb.write('FAMILY_ZERO",f"assert struct.unpack('<8Q',mem({s['native_pio_state']},64))==(0,0xffffffffffffffff,1,0,0,0,0,0)\nassert not any(mem({s['native_pio_request']},64))\ngdb.write('PIO_ZERO run=%d complete=1\\n'%int(gdb.parse_and_eval('$runs')))\ngdb.write('FAMILY_ZERO")
    extra=f'''python
import hashlib
pio_seen={{}};pio_owner=0;pio_events=0
def pio_state():
    v=struct.unpack('<8Q',mem({s['native_pio_state']},64))
    assert v[1]==(v[0]^0xffffffffffffffff) and v[2] in (0,1) and v[5]<=64
    assert v[3]<=v[4]<1<<60 and v[6]<=v[4] and not v[7]
    return v
def pio_retire(slot,gen):
    v=pio_state();assert not any(mem({s['native_pio_request']},64))
    if slot in (0,2):assert v[2]==1
    if slot==2:
        owner=(gen<<32)|slot;d=pio_seen[owner]
        assert v[0]==owner and d['reset'] and d['released'] and not d['retired']
        d['retired']=True
        ident=bytes(d['identify']);data=bytes(d['data'])
        if {case}==2:assert len(ident)==len(data)==0
        else:
            assert len(ident)==512 and struct.unpack_from('<H',ident,98)[0]&512
            assert struct.unpack_from('<I',ident,120)[0]==128
            assert data==bytes((n^0xa5)&255 for n in range(len(data))) and len(data) in (256,512)
        gdb.write('PIO_RETIRE gen=%d identify=%d data=%d sha256=%s fenced=1\\n'%(gen,len(ident),len(data),hashlib.sha256(data).hexdigest()))
class PioOut(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['native_pio_out8.done']}),internal=True)
    def stop(self):
        global pio_owner,pio_events
        try:
            pio_events+=1;assert pio_events<=512
            port=reg('edx')&65535;value=reg('eax')&255;v=pio_state();owner=v[0]
            slot=struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]
            gen=u64({s['scheduler_tasks']}+slot*256+8)
            if port==0x3f6 and value==6:
                assert owner
                if owner!=pio_owner:
                    if pio_owner:assert pio_seen[pio_owner]['retired']
                    assert slot==0 and not v[2] and owner not in pio_seen
                    assert u64({s['family_records']}+(owner&3)*64+8)==gen<<32
                    pio_owner=owner
                    pio_seen[owner]=dict(reset=True,released=False,retired=False,command=0,identify=bytearray(),data=bytearray())
                    gdb.write('PIO_BIND gen=%d recycled=1\\n'%(owner>>32))
                else:pio_seen[owner]['reset']=True
            else:
                assert owner==((gen<<32)|slot) and slot==2 and not v[2]
                d=pio_seen[owner];assert not d['retired']
                if port==0x3f6:
                    assert value==2 and d['reset'] and v[4]>v[6];d['released']=True
                else:
                    assert d['released']
                    if port==0x1f7:
                        assert value in (0xec,0x20)
                        if value==0xec:assert d['command']==0
                        else:assert d['command']==0xec and len(d['identify'])==512
                        d['command']=value
                    elif port==0x1f6:assert 0xe0<=value<=0xef
                    elif port==0x1f2:assert value==1
                    else:assert port in (0x1f3,0x1f4,0x1f5) and value==0
        except Exception as e:
            gdb.write('PIO_OBSERVER_FAIL OUT '+repr(e)+'\\n');gdb.execute('quit 71')
        return False
class PioData(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['native_pio_apply64.transfer_done']}),internal=True)
    def stop(self):
        try:
            q=struct.unpack('<4IQ4I3Q',mem(reg('r13'),64));v=pio_state()
            assert q[:4]==(1,64,4,0) and q[4]==v[0] and not v[2]
            assert q[5:9]==(0x1f0,0,16,0) and q[10:]==(0,0) and reg('ebp')==16
            d=pio_seen[v[0]];assert not d['retired'] and d['released']
            key='identify' if d['command']==0xec else 'data'
            assert d['command'] in (0xec,0x20) and len(d[key])<=480
            d[key].extend(mem(q[9],32))
        except Exception as e:
            gdb.write('PIO_OBSERVER_FAIL DATA '+repr(e)+'\\n');gdb.execute('quit 72')
        return False
PioOut();PioData()
class PioFailure(gdb.Breakpoint):
    def __init__(self,address,label):
        super().__init__('*'+hex(address),internal=True);self.label=label;self.seen=False
    def stop(self):
        if self.seen:return False
        self.seen=True
        gdb.write('PIO_DIAGNOSTIC '+self.label+' regs='+str([reg(n) for n in ('rax','rdi','rsi','rdx','rcx','r8','r9','rsp')])+' clock='+str([u64({s['timer_deadline']}),u64({s['timer_runtime_ticks']}),u64({s['timer_runtime_eois']})])+'\\n')
        return False
PioFailure({s['timer_runtime_progress64.fail']},'clock-lease')
PioFailure({s['x86_64_timer_interrupt64.shell_clock_invalid']},'timer-context')
PioFailure({s['scheduler_fail']},'scheduler')
end
'''
    return code[:-len('continue\n')]+extra+'continue\n'

def validate(serial,trace,case,oom=None):
    if 'OBSERVER_FAIL' in trace:raise ValueError('PIO observer failure')
    common=[m for m in startup.family.REQUIRED_MARKERS if 'SHELL' not in m]+[startup.family.process.SUCCESS]
    if any(m in serial for m in startup.family.FAILURES) or any(serial.count(m)!=1 for m in common):raise ValueError('PIO kernel progress')
    if [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):raise ValueError('PIO kernel order')
    sequence=modes(case);count=len(sequence)+2
    ends=list(re.finditer(startup.family.process.DONE,serial))
    receipts=list(startup.family.process.REAP.finditer(serial));rows=[]
    if len(ends)!=2 or len(receipts)!=count*2 or serial.count('PROCESS_REAP_OK')!=len(receipts):raise ValueError('PIO receipt count')
    expected={}
    for run in range(2):
        base=run*count
        expected[(0,base+1)]=(134,3) if case==3 else (79 if case==2 else 78,4)
        expected[(1,base+2)]=(77,4)
        for i,mode in enumerate(sequence,3):
            expected[(2,base+i)]=(0,3) if case==3 or mode==2 else (134,3) if mode==1 else (256,3) if mode==4 else (89 if case==2 else 80,4)
        for m in receipts[run*count:(run+1)*count]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]))
            if expected.get((slot,gen))!=(status,state) or ticks>32 or status==256 and ticks!=32:raise ValueError('PIO outcome '+str((slot,gen,status,state,ticks)))
            if not 0x400000<=rip<(0x402000 if slot==0 else 0x401000):raise ValueError('PIO RIP')
            if not (ends[run-1].end() if run else -1)<m.start()<m.end()<ends[run].start():raise ValueError('PIO receipt order')
            rows.append((slot,gen,state))
    if len(set((s,g) for s,g,_ in rows))!=len(expected) or ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('PIO lifetime identity')
    # Existing exact17 baseline retirements, plus every native task. No marker
    # substitution: compare each backend free against its actual saved frame.
    before=list(startup.BEFORE.finditer(trace));after=list(startup.AFTER.finditer(trace));frees=list(startup.FREE.finditer(trace))
    if len(before)!=17+len(rows) or len(after)!=len(before):raise ValueError('PIO frame count')
    frames_expected={(m,s,s+1):(4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)}
    frames_expected.update({(4,s,10+s):3 if s==3 else 4 for s in range(4)})
    frames_expected.update({(5,s,20+s):4 for s in range(4)})
    frames_expected.update({(6,0,30):4,(6,1,31):8,(6,1,32):8})
    frames_expected.update({(8,s,g):state for s,g,state in rows});seen=set();native=[];consumed=0
    for i,(b,a) in enumerate(zip(before,after),1):
        seq,mode,slot,gen,state,root,active,free,fp,fs=b.groups()
        seq,mode,slot,gen,state,free,fp=map(int,(seq,mode,slot,gen,state,free,fp))
        key=(mode,slot,gen);frames=[int(f,16) for f in fs.split(',')];owned=[f for f in frames if f]
        if seq!=i or key in seen or frames_expected.get(key)!=state or fp!=1:raise ValueError('PIO frame identity')
        seen.add(key)
        if mode==8:native.append((slot,gen,state))
        if len(frames)!=13 or not all(frames[8:]) or len(set(owned))!=len(owned) or any(not 0<f<0x400000000 or f%4096 for f in owned):raise ValueError('PIO frame ownership')
        if int(root,16)!=frames[-1] or root==active or not 0<int(active,16)<0x400000000 or int(active,16)%4096:raise ValueError('PIO active root')
        if tuple(map(int,a.groups()))!=(i,gen,state,1,free+len(owned),1) or not 0<free<free+len(owned)<=4194304:raise ValueError('PIO free balance')
        if not (after[i-2].end() if i>1 else -1)<b.start()<b.end()<a.start():raise ValueError('PIO frame order')
        calls=[f for f in frees if b.end()<=f.start()<a.start()];consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(i,f) for f in owned]:raise ValueError('PIO backend free')
    if consumed!=len(frees) or seen!=set(frames_expected) or native!=rows:raise ValueError('PIO unowned release')
    fences=list(re.finditer(r'FAMILY_FENCE slot=(\d+) gen=(\d+) ipc=1 heap=1 profile=1',trace))
    if [tuple(map(int,m.groups())) for m in fences]!=[(s,g) for s,g,_ in rows]:raise ValueError('PIO fences')
    starts=list(re.finditer(r'FAMILY_START slot=(\d+) gen=(\d+) image=(\d+) high=1 wx=1 argv=1',trace))
    if len(starts)!=len(rows) or {tuple(map(int,m.groups())) for m in starts}!={(s,g,7 if s==2 else s+3) for s,g,_ in rows}:raise ValueError('PIO mapping')
    for i,f in enumerate(fences,17):
        start=next(m for m in starts if m[2]==f[2])
        if not after[i-1].end()<f.start()<f.end()<before[i].start() or start.end()>f.start():raise ValueError('PIO fence order')
    children=[g for s,g,_ in rows if s==2]
    binds=list(re.finditer(r'PIO_BIND gen=(\d+) recycled=1',trace))
    data=list(re.finditer(r'PIO_RETIRE gen=(\d+) identify=(\d+) data=(\d+) sha256=([0-9a-f]{64}) fenced=1',trace))
    if [int(m[1]) for m in binds]!=children or [int(m[1]) for m in data]!=children:raise ValueError('PIO generation binding')
    for i,m in enumerate(data):
        mode=sequence[i%len(sequence)];length=0 if case==2 else 256 if mode in (1,2,4) else 512
        if (int(m[2]),int(m[3]),m[4])!=(0 if case==2 else 512,length,hashlib.sha256(SECTOR[:length]).hexdigest()):raise ValueError('PIO actual data')
        fence=next(f for f in fences if f[2]==m[1])
        if not binds[i].end()<m.start()<m.end()<fence.start():raise ValueError('PIO transfer fence order')
    zeros=list(re.finditer(r'PROCESS_ZERO_OK run=(\d+) zero=1 free=(\d+) initial=(\d+) reaps=(\d+) generation=(\d+) ticks=(\d+)',trace))
    if len(zeros)!=2:raise ValueError('PIO zero count')
    for i,z in enumerate(zeros,1):
        run,free,initial,reaps,gen,ticks=map(int,z.groups())
        if (run,reaps,gen)!=(i,count,i*count) or not 0<free==initial<=4194304 or not 0<ticks<1<<60:raise ValueError('PIO final balance')
        if after[16+i*count].end()>z.start() or i==1 and z.end()>before[17+count].start():raise ValueError('PIO zero order')
    for label in ('PIO_ZERO','FAMILY_ZERO'):
        if re.findall(label+r' run=(\d+) complete=1',trace)!=['1','2']:raise ValueError('PIO complete zero')
    cancel=list(re.finditer(r'FAMILY_CANCEL slot=(\d+) gen=(\d+) state=(\d+) ipc=(\d+) heap=(\d+) reason=(\d+)',trace))
    wanted=[(2,run*count+i,3 if case==3 else 2) for run in range(2) for i,mode in enumerate(sequence,3) if mode==2]
    if [(int(m[1]),int(m[2]),int(m[6])) for m in cancel]!=wanted or any(int(m[3]) not in (1,6) or int(m[4]) or int(m[5]) for m in cancel):raise ValueError('PIO cancellation')
    for m in cancel:
        start=next(x for x in starts if x[2]==m[2]);fence=next(x for x in fences if x[2]==m[2])
        if not start.end()<m.start()<m.end()<fence.start():raise ValueError('PIO cancel order')
    if re.findall(r'FAMILY_OOM acquired=(\d+)',trace)!=([str(oom)]*2 if oom is not None else []):raise ValueError('PIO OOM count')
    boundaries=list(re.finditer(r'STARTUP_OOM_BOUNDARY owner=(\d+) acquired=(\d+) result=-12',trace))
    if [tuple(map(int,m.groups())) for m in boundaries]!=([((run*count+1)<<32,oom) for run in range(2)] if oom is not None else []):raise ValueError('PIO OOM boundary')
    for i,b in enumerate(boundaries):
        if b.end()>next(m for m in starts if int(m[2])==i*count+3).start():raise ValueError('PIO OOM outside create')
    copies=re.findall(r'IMPORT_COPY gen=(\d+) bytes=36896 immutable=1',trace)
    args=re.findall(r'STARTUP_ARGS gen=(\d+) argc=2 immutable=1',trace)
    if list(map(int,copies))!=children or list(map(int,args))!=children:raise ValueError('PIO immutable source')
    scrub=trace.count('STARTUP_SCRUB bytes=4096 complete=1')
    if scrub<minimum_scrubs(case) or trace.count('IMPORT_SCRUB bytes=36896 complete=1')!=scrub:raise ValueError('PIO temporary scrub')
    for label,n in (('PIO_BIND',len(binds)),('PIO_RETIRE',len(data)),('PIO_ZERO',2),('FAMILY_ZERO',2),('FAMILY_START',len(starts)),('FAMILY_FENCE',len(fences)),('FAMILY_CANCEL',len(cancel)),('PROCESS_ZERO_OK',2),('TASK_FRAMES_BEFORE',len(before)),('TASK_FRAMES_AFTER',len(after)),('TASK_FRAMES_FREE',len(frees)),('IMPORT_COPY',len(copies)),('STARTUP_ARGS',len(args)),('STARTUP_OOM_BOUNDARY',len(boundaries)),('FAMILY_OOM',len(boundaries))):
        if trace.count(label)!=n:raise ValueError('PIO malformed '+label)
    return len(rows)

FATAL_CASES={'expired':4,'backward':5,'lease':3,'eoi':2,'context':7,
             'kernel':0,'metadata':0,'scheduler':0}

def fatal_clock_inputs(kind,now,deadline,ticks,eois):
    if not 0<=now<(1<<63) or not 0<=ticks<(1<<60):raise ValueError('clock injection bounds')
    if kind=='expired':
        # A short boot may still be below one lease. Inject a valid expired
        # sample pair, not a malformed deadline and not a changed timer quota.
        now=max(now,3000000001);deadline=now-1
    elif kind=='backward':deadline=now+3000000001
    elif kind=='lease':deadline=0
    elif kind=='eoi':eois=ticks+1
    else:raise ValueError('clock injection kind')
    return now,deadline,ticks,eois

def validate_fatal(serial,trace,kind):
    expected=['PIO_FATAL_RELEASE','PIO_FATAL_INJECT '+kind]
    reason=FATAL_CASES[kind]
    if reason:expected+=['PIO_FATAL_REASON '+str(reason)]
    expected+=['PIO_FATAL_FENCE physical=1 unchanged=1',
               'PIO_FATAL_DIAG fenced=1 unchanged=1','PIO_FATAL_HALT unchanged=1']
    events=[line for line in trace.splitlines() if line.startswith('PIO_FATAL_')]
    if events!=expected or 'OBSERVER_FAIL' in trace:raise ValueError('fatal exact ordered witnesses')
    marker='REIST_X86_64_EXCEPTION_FATAL '+('pio=1' if kind in ('metadata','scheduler') else 'vector=06' if kind=='kernel' else 'vector=20')
    if serial.count('REIST_X86_64_EXCEPTION_FATAL')!=1 or marker not in serial:
        raise ValueError('fatal exact terminal diagnostic')
    if any(m in serial for m in ('PROCESS_REAP_OK',startup.family.process.SUCCESS)):
        raise ValueError('fatal runtime continued')

def fatal_observer(s,folder,kind):
    if kind not in FATAL_CASES:raise ValueError('unknown fatal injection')
    ranges=[(s['native_pio_state'],64),(s['scheduler_tasks'],1024),
            (s['family_records'],256),(s['family_profiles'],128),
            (s['family_extended_masks'],64)]
    return f'''set logging file {str(folder/'frame-trace.log').replace(chr(92),'/')}
set logging overwrite on
set logging redirect on
set logging enabled on
python
import gdb,struct
{inspect.getsource(fatal_clock_inputs)}
kind={kind!r};released=False;injected=False;fenced=False;diagnosed=False;saved=None;events=0
inferior=gdb.selected_inferior()
def reg(name):return int(gdb.parse_and_eval('$'+name)) & ((1<<64)-1)
def mem(address,size):return bytes(inferior.read_memory(address,size))
def u64(address):return struct.unpack('<Q',mem(address,8))[0]
def state():return [mem(a,n) for a,n in {ranges!r}]
def write(address,value):inferior.write_memory(address,struct.pack('<Q',value))
def event(text):gdb.write('PIO_FATAL_'+text+'\\n')
def inject():
    global injected,saved
    assert released and not injected
    injected=True;saved=state();event('INJECT '+kind)
    for b in forbidden:b.enabled=True
class Probe(gdb.Breakpoint):
    def __init__(self,address,label,enabled=True):
        super().__init__('*'+hex(address),internal=True);self.label=label;self.enabled=enabled
    def stop(self):
        try:self.observe()
        except Exception as error:
            gdb.write('PIO_FATAL_OBSERVER_FAIL '+self.label+' '+repr(error)+'\\n');gdb.execute('quit 71')
        return False
    def observe(self):
        global released,injected,fenced,diagnosed,saved,events
        label=self.label
        if label=='port':
            events+=1;assert events<=128
            port=reg('edx')&65535;value=reg('eax')&255
            if injected:
                assert not fenced and port==0x3f6 and value==6 and state()==saved
                fenced=True;event('FENCE physical=1 unchanged=1')
            elif not released and port==0x3f6 and value==2:
                assert u64({s['native_pio_state']}+16)==0
                released=True;event('RELEASE')
                if kind in ('kernel','scheduler'):
                    inject()
                    address={s['x86_64_ud2_resume']} if kind=='kernel' else {s['scheduler_fail']}
                    if kind=='kernel':inferior.write_memory(address,bytes([15,11]))
                    gdb.execute('set $rip='+hex(address))
                else:trigger.enabled=True
        elif label=='trigger':
            self.enabled=False
            if kind in ('expired','backward','lease','eoi'):
                names=('rdi','rsi','rdx','rcx')
                values=fatal_clock_inputs(kind,*(reg(n) for n in names))
                for name,value in zip(names,values):gdb.execute('set $'+name+'='+str(value))
            elif kind=='context':write(reg('rdi')+144,0) # Saved CS, never a valid Ring3 selector.
            else:write({s['native_pio_state']}+8,u64({s['native_pio_state']}+8)^1)
            inject()
        elif label=='clock':
            assert injected and not fenced and reg('r9')=={FATAL_CASES[kind]}
            assert state()==saved;event('REASON '+str(reg('r9')))
        elif label=='context':
            assert injected and kind=='context' and not fenced and state()==saved
            event('REASON 7')
        elif label=='diagnostic' and injected:
            assert fenced and not diagnosed and state()==saved and not reg('eflags')&512
            diagnosed=True;event('DIAG fenced=1 unchanged=1')
        elif label=='exception' and released and not injected:
            frame=reg('rsp')
            event('UNEXPECTED frame='+str([u64(frame+n) for n in (120,128,136,144,152,160,168)])+
                  ' cr2='+hex(reg('cr2'))+' regs='+str([reg(n) for n in ('rax','rdi','rsi','rdx','rcx','r8','r9','r12')]))
        elif label=='diagnostic' and released:
            raise AssertionError('unexpected kernel fatal before injection; frame retained')
        elif label=='halt' and injected:
            assert fenced and diagnosed and state()==saved
            assert mem({s['halt64']},4)==bytes([0xfa,0xf4,0xeb,0xfd]) # CLI; HLT; JMP HLT.
            event('HALT unchanged=1');gdb.execute('detach');gdb.execute('quit 0')
        elif label=='forbidden':raise AssertionError('runtime cleanup/resume after fatal injection')
Probe({s['native_pio_out8.done']},'port')
trigger=Probe({s['timer_runtime_progress64'] if kind in ('expired','backward','lease','eoi') else s['x86_64_scheduler_shell_timer_validate64'] if kind=='context' else s['native_pio_apply64']},'trigger',False)
Probe({s['timer_runtime_progress64.fail']},'clock')
Probe({s['x86_64_timer_interrupt64.shell_clock_invalid']},'context')
Probe({s['serial_init64']},'diagnostic')
Probe({s['exception_fatal']},'exception')
Probe({s['halt64']},'halt')
forbidden=[Probe(a,'forbidden',False) for a in {[s[n] for n in ('process_run_resume64','family_terminal64','scheduler_force_cleanup64')]!r}]
end
continue
'''

def fatal_matrix(image,folder,summary):
    s=startup.family.symbols(image)
    for kind in FATAL_CASES:
        out=folder/kind;out.mkdir()
        fixture=Fixture(out)
        serial,trace=startup.family.programs.capture(image,out,fatal_observer(s,out,kind),4096,
                                                   fixture,halt_witness=True)
        validate_fatal(serial,trace,kind)
        summary['cases'].append(dict(fault=kind,reason=FATAL_CASES[kind],passed=True))
        print('PIO_FATAL_GUEST_OK '+kind,flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--fatal',action='store_true');a=p.parse_args()
    folder=startup.family.evidence_directory(a.evidence)/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();summary=dict(passed=False,cases=[])
    try:
        image=a.image.resolve();reference=None
        if not image.is_relative_to(ROOT/'build'):raise ValueError('PIO image scope')
        if a.fatal:
            fatal_matrix(image,folder,summary)
            summary['passed']=True
            return 0
        for case in range(4):
            if case:
                out=folder/f'build-{case}';out.mkdir()
                with (out/'build.log').open('wb') as f:
                    r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativePIO','-PIOCase',str(case),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode:raise ValueError('PIO fixture build')
                image=out/'x86_64/reist-x86_64-bootstrap.elf'
            names=('cooperative_scheduler','syscall_profile','bootstrap_core','identity_core','queue_core','cpu_budget','task_frames','fp_context','timer_interrupt','startup_stack')
            hashes={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if reference is not None and reference!=hashes:raise ValueError('PIO kernel mechanism drift')
            reference=hashes
            catalog=(image.parent/'boot-programs.bin').read_bytes()
            if len(catalog)!=4*36896:raise ValueError('PIO catalog length')
            candidates=[d for d in image.parent.glob('programs-*') if d.is_dir() and (d/'boot-programs.bin').is_file() and (d/'boot-programs.bin').read_bytes()==catalog]
            if not candidates:raise ValueError('PIO catalog provenance')
            child=(candidates[0]/'program2.prg').read_bytes()
            if any((d/'program2.prg').read_bytes()!=child for d in candidates):raise ValueError('PIO ambiguous child')
            record=producer.prepare(child,[])
            if record[:32800]!=catalog[73792:106592] or startup.creation_allocations(record)!=10:raise ValueError('PIO child extent')
            inner=startup.family.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=startup.family.payload.validate(inner)
            startup.family.payload.verify_outer(inner,startup.family.payload.read_bounded(image))
            if c['layout_version']!=4:raise ValueError('PIO C layout')
            s=startup.family.symbols(image)
            variants=[(4096,n) for n in (0,1,2,3,6,9)] if case==1 else [(4096,None),(8192,None)] if case==0 else [(4096,None)]
            for ram,oom in variants:
                out=folder/f'guest-{case}-{ram}-{oom}';out.mkdir()
                fixture=None if case==2 else Fixture(out)
                serial,trace=startup.family.programs.capture(image,out,observer(s,c,out,ram,case,oom,record),ram,fixture)
                tasks=validate(serial,trace,case,oom)
                summary['cases'].append(dict(case=case,ram=ram,oom=oom,tasks=tasks,record_sha256=hashlib.sha256(record).hexdigest()))
                print('PIO_GUEST_OK',case,ram,oom,flush=True)
        summary.update(passed=True,mechanisms=reference)
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('PIO_FAIL',error);return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('PIO_EVIDENCE',folder)
    return 0

if __name__=='__main__':
    # Use the same canonical Fixture class as capture's strict type admission.
    from run_qemu_x86_64_pio import main as entry
    raise SystemExit(entry())
