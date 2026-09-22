"""Real active-DMA fatal transitions, preserved state and post-fence RX probe."""
from pathlib import Path
import argparse,json,socket,struct,threading,time
import run_qemu_x86_64_network_dma as normal
wide=normal.wide;transport=normal.transport;need=normal.need;save=normal.save;sha=normal.sha
CASES=('kernel-nx','scheduler-fatal','corrupt-io')

# QEMU may report the same stopped instruction twice. Keep a separate raw
# receipt; suppress only an adjacent, byte-identical second observation.
REPEAT_TERMINAL=r'''
terminal_last=None;terminal_repeats=set()
def terminal():
    global terminal_last
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);receipt=mem(S['process_run_receipt'],32)
    key=struct.unpack('<2I',receipt[:8]);assert key[0]==slot
    spans=[(CS['native_network_state'],384),(CS['native_network_dma'],18432),
        (S['native_network_call'],1656),(S['scheduler_tasks'],8192),
        (S['family_profiles'],256),(S['family_records'],512),
        (S['scheduler_cpu_budgets'],256),(S['process_run_receipt'],32)]
    raw=b''.join(mem(a,n) for a,n in spans)
    if slot in (0,2):raw+=user(task(slot),CONFIG['addresses'][slot//2],96)
    stamp=(free(),d(S['scheduler_initial_free']),q(S['timer_runtime_ticks']),q(S['timer_runtime_eois']))
    if terminal_last and key==terminal_last[0]:
        assert key not in terminal_repeats and len(terminal_repeats)<16
        assert raw==terminal_last[1] and stamp==terminal_last[2],'changed repeated terminal'
        terminal_repeats.add(key);name='repeat-%d.bin'%len(terminal_repeats)
        with (F/name).open('xb') as f:f.write(raw)
        row=dict(sequence=sequence,slot=slot,generation=key[1],file=name,sha256=hashlib.sha256(raw).hexdigest(),stamp=stamp)
        with (F/'repeated-stops.jsonl').open('a',encoding='ascii') as f:f.write(json.dumps(row)+'\n')
        return
    assert key not in terminal_repeats
    terminal_last=(key,raw,stamp);snapshot('terminal',slot)
'''

def ordinary_observer(c,folder):
    code=normal.observer(c,folder)
    old="def terminal():\n    if mode()==8:snapshot('terminal',d(S['scheduler_current_slot']))\n"
    need(code.count(old)==1,'exact accepted terminal observer');return code.replace(old,REPEAT_TERMINAL)

def ordinary_run(image,folder,spec):
    from unittest.mock import patch
    original=normal.observer
    def adapted(c,f):
        # The temporary adapter must call the original, never itself.
        code=original(c,f);old="def terminal():\n    if mode()==8:snapshot('terminal',d(S['scheduler_current_slot']))\n"
        need(code.count(old)==1,'exact accepted terminal observer');return code.replace(old,REPEAT_TERMINAL)
    with patch.object(normal,'observer',adapted):return normal.run(image,folder,spec)

def ordinary_review(image,folder,spec):
    proof=normal.review(image,folder,spec);c=normal.config(image,folder,spec[2])
    script=(folder/'observe.gdb').read_text(encoding='ascii');marker='set breakpoint always-inserted on\n'
    need(marker+script.split(marker,1)[1]==ordinary_observer(c,folder),'bound terminal observer')
    path=folder/'repeated-stops.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    need(len(rows)<=16 and len({(r['slot'],r['generation']) for r in rows})==len(rows),'bounded unique repeat receipts')
    events=[json.loads(l[8:]) for l in (folder/'frame-trace.log').read_text().splitlines() if l.startswith('NETWORK ')]
    keys=('state','dma','staging','tasks','profiles','family','cpu','receipt')
    for r in rows:
        e=next((e for e in events if e.get('sequence')==r['sequence']),None)
        need(e and e['kind']=='terminal' and e['slot']==r['slot'],'repeat source observation')
        raw=b''.join((folder/e['raw'][k]['file']).read_bytes() for k in keys)
        if 'witness' in e['raw']:raw+=(folder/e['raw']['witness']['file']).read_bytes()
        p=folder/r['file'];need(p.parent==folder and sha(p)==r['sha256'] and p.read_bytes()==raw,'identical repeated raw bytes')
        receipt=(folder/e['raw']['receipt']['file']).read_bytes()
        need(struct.unpack('<2I',receipt[:8])==(r['slot'],r['generation']) and r['stamp']==[e['free'],e['initial'],e['ticks'],e['eois']],'same generation/clock/frame ledger')
    return dict(proof,repeat_receipts=len(rows),observer=sha(folder/'observe.gdb'))

BODY=r'''
from pathlib import Path
import time
F=Path(CONFIG['folder']);injected=False;fenced=False;diagnosed=False;fence_count=0
def dump(name,raw):
    with (F/name).open('xb') as f:f.write(raw)
    return dict(file=name,sha256=hashlib.sha256(raw).hexdigest())
def state():
    return mem(CS['native_network_state'],384)+mem(CS['native_network_dma'],18432)+mem(S['scheduler_tasks'],8192)+mem(S['family_records'],512)+mem(S['family_profiles'],256)
def inject():
    global injected,saved
    if injected or mode()!=8:return
    call=mem(S['native_network_call'],112)
    operation=7 if CONFIG['kind']=='corrupt-io' else 5
    if struct.unpack_from('<I',call,8)[0]!=operation:return
    if operation==5 and reg('rax')!=0:return
    assert reg('cs')==8 and not reg('eflags')&512
    owner=q(CS['native_network_state']);t=task(2)
    assert d(S['scheduler_current_slot'])==2 and owner==(t[1]<<32|2) and t[0]==2
    s=struct.unpack('<48Q',mem(CS['native_network_state'],384))
    assert s[3]==0 and s[7]==2 and s[11]==1 and s[17]==1 and s[18]==0
    assert all(a^b==0xffffffffffffffff for a,b in zip(s[:24],s[24:]))
    before=state();injected=True
    if CONFIG['kind']=='corrupt-io':
        target=CS['native_network_state']+64
        gdb.selected_inferior().write_memory(target,bytes([mem(target,1)[0]^1]))
    else:
        target=S['native_network_staging'] if CONFIG['kind']=='kernel-nx' else S['scheduler_fail']
        gdb.execute('set $rip='+hex(target))
    saved=state()
    emit('inject',kind_name=CONFIG['kind'],owner=owner,target=target,call=dump('call.bin',call),before=dump('before.bin',before),damaged=dump('damaged.bin',saved))
    trigger.enabled=False
def exception():
    assert injected and CONFIG['kind']=='kernel-nx' and not fenced
    frame=mem(reg('rsp'),176);f=struct.unpack('<22Q',frame)
    assert f[15:19]==(14,17,S['native_network_staging'],8) and reg('cr2')==S['native_network_staging']
    emit('exception',frame=dump('exception.bin',frame),cr2=reg('cr2'))
def fence():
    global fenced,fence_count
    assert injected and not fenced and not reg('eflags')&512 and state()==saved
    receipt=mem(S['native_network_fatal_receipt'],64);r=struct.unpack('<8Q',receipt)
    assert r[0]==0x3145434e45464e52 and r[1]==0x813910ec and r[2]==0xc001
    assert r[3]&5==5 and r[4]&5==1 and r[5]&12==0 and r[6]==0 and r[7]==1
    fenced=True;fence_count+=1
    for h in forbidden:h.enabled=True
    emit('fence',receipt=dump('fence.bin',receipt),preserved=dump('fenced-state.bin',state()),interrupts=reg('eflags')&512)
    with (F/'fenced.signal').open('x') as f:f.write('fenced')
def diagnostic():
    global diagnosed
    if not injected:return
    assert fenced and not diagnosed and not reg('eflags')&512 and state()==saved
    diagnosed=True;emit('diagnostic',preserved=dump('diagnostic-state.bin',state()),interrupts=reg('eflags')&512)
def halt():
    assert injected and fenced and diagnosed and fence_count==1 and state()==saved and not reg('eflags')&512
    assert mem(S['halt64'],4)==b'\xfa\xf4\xeb\xfd'
    end=time.monotonic()+1
    while not (F/'probe-sent.json').exists():
        assert time.monotonic()<end,'post-fence packet deadline'
        time.sleep(.01)
    time.sleep(.05)
    assert state()==saved,'DMA after disabled RX probe'
    emit('halt',preserved=dump('halt-state.bin',state()),receipt=dump('halt-fence.bin',mem(S['native_network_fatal_receipt'],64)),instructions=mem(S['halt64'],4).hex(),interrupts=reg('eflags')&512)
    gdb.execute('detach');gdb.execute('quit 0')
def forbidden_path():raise AssertionError('cleanup/resume after fatal fence')
trigger=Hook('native_network_call64' if CONFIG['kind']=='corrupt-io' else 'native_network_syscall64.result',inject)
Hook('exception_fatal',exception)
Hook('native_network_emergency64.published',fence)
Hook('serial_init64',diagnostic)
Hook('halt64',halt)
forbidden=[Hook(n,forbidden_path) for n in ('process_run_resume64','family_terminal64','scheduler_force_cleanup64','scheduler_release_task_frames64')]
for h in forbidden:h.enabled=False
'''

def configuration(image,folder,kind):
    c=normal.config(image,folder,0);c['kind']=kind;return c

def observer(c,folder):
    prefix=wide.OBSERVER[:wide.OBSERVER.index('def poison():')].replace("'WIDE '","'NETFATAL '").replace('callbacks<=4096','callbacks<=128')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
            '\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+repr(c)+'\n'+prefix+BODY+'\nend\ncontinue\n')

class Peer(normal.Peer):
    def work(self):
        try:
            while not self.stop.is_set():
                need(time.monotonic()<self.deadline,'peer accept deadline')
                try:self.connection,address=self.listener.accept();break
                except socket.timeout:continue
            if self.connection is None:return
            need(address[0]=='127.0.0.1','local peer');self.connection.settimeout(.1)
            header=self.receive(4);need(header is not None,'real outgoing frame')
            n=struct.unpack('>I',header)[0];need(n==64,'one bounded frame');tx=self.receive(n);need(tx is not None,'complete TX')
            while not (self.folder/'fenced.signal').exists():
                if self.stop.wait(.01):return
                need(time.monotonic()<self.deadline,'fence deadline')
            rx=tx[6:12]+tx[:6]+tx[12:];self.connection.sendall(struct.pack('>I',len(rx))+rx)
            self.rows.append(dict(tx=tx.hex(),rx=rx.hex()))
            save(self.folder/'probe-sent.json',dict(after_fence=True,tx=tx.hex(),rx=rx.hex()))
            while not self.stop.is_set():
                extra=self.receive(4)
                if extra is None:break
                raise ValueError('unexpected frame after fatal fence')
        except BaseException as e:
            if not self.stop.is_set():self.error=repr(e)
        finally:
            if self.connection:self.connection.close()

def run(image,folder,kind):
    need(kind in CASES,'fatal selector');folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    row=dict(case=kind,image_sha256=sha(image),passed=False,closed=False);save(folder/'started.json',row)
    t=time.monotonic();peer=None
    try:
        c=configuration(image,folder,kind);save(folder/'config.json',c);peer=Peer(folder)
        args=['-netdev',f'socket,id=net0,connect=127.0.0.1:{peer.port}','-device','rtl8139,netdev=net0,addr=04.0,mac=52:54:00:12:34:56']
        transport._capture(image,folder,observer(c,folder),4096,args,diagnostic_metrics=True,service_pio_budget=True,halt_witness=True)
        row['passed']=True
    except BaseException as e:row['error']=str(e);raise
    finally:
        try:
            if peer:peer.close()
            row['closed']=True
        finally:row['elapsed']=time.monotonic()-t;save(folder/'result.json',row)
    need(row['elapsed']<=45,'total fatal guest deadline');return row

def review(image,folder,kind):
    folder=Path(folder);read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    c=configuration(image,folder,kind);need(read('config.json')==c,'bound observer configuration')
    row=read('result.json');need(row['passed'] and row['closed'] and row['case']==kind and row['image_sha256']==sha(image) and row['elapsed']<=45,'closed bound guest')
    trace=(folder/'frame-trace.log').read_text(encoding='utf-8');serial=(folder/'guest.log').read_text(encoding='ascii')
    need('OBSERVER_FAIL' not in trace and wide.process.SUCCESS not in serial and wide.process.DONE not in serial,'fatal never resumes cohort')
    events=[json.loads(line[9:]) for line in trace.splitlines() if line.startswith('NETFATAL ')]
    need([e['kind'] for e in events]==['inject']+(['exception'] if kind=='kernel-nx' else [])+['fence','diagnostic','halt'],'exact fatal order')
    def raw(item,n):
        p=folder/item['file'];need(p.parent==folder and sha(p)==item['sha256'] and p.stat().st_size==n,'exact raw bytes');return p.read_bytes()
    n=384+18432+8192+512+256;first=events[0];before=raw(first['before'],n);damaged=raw(first['damaged'],n);call=raw(first['call'],112)
    state=struct.unpack_from('<48Q',before);need(state[3]==0 and state[7]==2 and state[11]==1 and state[17]==1 and state[18]==0,'real active transmitter')
    need(all(a^b==0xffffffffffffffff for a,b in zip(state[:24],state[24:])),'before mirror')
    need(first['owner']==state[0] and first['kind_name']==kind and struct.unpack_from('<I',call,8)[0]==(7 if kind=='corrupt-io' else 5),'real owner/request')
    if kind=='corrupt-io':
        wanted=bytearray(before);wanted[64]^=1;need(damaged==wanted and first['target']==c['cs']['native_network_state']+64,'one exact protected bit')
    else:need(damaged==before and first['target']==c['s']['native_network_staging' if kind=='kernel-nx' else 'scheduler_fail'],'one exact RIP injection')
    if kind=='kernel-nx':
        e=events[1];frame=struct.unpack('<22Q',raw(e['frame'],176));need(frame[15:19]==(14,17,c['s']['native_network_staging'],8) and e['cr2']==frame[17],'actual supervisor NX exception')
        need(serial.count('REIST_X86_64_EXCEPTION_FATAL vector=0E')==1,'fatal exception diagnostic')
    else:need(serial.count('REIST_X86_64_PROCESS_SCHEDULER_STAGE_')==1,'fatal scheduler diagnostic')
    fence,diagnostic,halt=events[-3:]
    receipt=raw(fence['receipt'],64);r=struct.unpack('<8Q',receipt)
    need(r[0:3]==(0x3145434e45464e52,0x813910ec,0xc001) and r[3]&5==5 and r[4]==r[3]&~4 and r[5]&12==0 and r[6]==0 and r[7]==1,'actual PCI/IMR/RX/TX readback')
    for e in (fence,diagnostic,halt):need(raw(e['preserved'],n)==damaged and e['interrupts']==0,'no repair/reap/DMA after fatal')
    need(raw(halt['receipt'],64)==receipt and halt['instructions']=='faf4ebfd','retained fence and CLI/HLT path')
    peer=read('packets.json');probe=read('probe-sent.json');need(peer['closed'] and peer['error'] is None and probe['after_fence'],'local post-fence probe')
    packet=bytes.fromhex('52540012345752540012345688b5')+bytes(range(14,64));response=packet[6:12]+packet[:6]+packet[12:]
    need(before[384+10240:384+10240+64]==packet,'actual pinned DMA transmitter bytes')
    reaps=[struct.unpack('<4I2Q',bytes.fromhex(m[1])) for m in wide.process.REAP.finditer(serial)]
    need(len(reaps)==1 and reaps[0][:4]==(1,2,77,4) and reaps[0][4]<=32,'unrelated peer done and no fatal reap')
    need(peer['frames']==[dict(tx=packet.hex(),rx=response.hex())] and probe['tx']==packet.hex() and probe['rx']==response.hex(),'exact TX and post-fence RX')
    return dict(kind=kind,owner=first['owner'],fenced=True,preserved=True,probe=True,raw=sha(folder/'frame-trace.log'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--case',choices=CASES,default=CASES[0]);a=p.parse_args()
    row=run(a.image.resolve(),a.evidence.resolve(),a.case);row['proof']=review(a.image.resolve(),a.evidence.resolve(),a.case);print(json.dumps(row))
