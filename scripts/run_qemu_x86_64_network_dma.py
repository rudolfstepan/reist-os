"""Bounded local Ethernet peer and raw native lifetime/DMA replay."""
from pathlib import Path
import argparse,hashlib,json,socket,struct,threading,time
import run_qemu_x86_64_program_memory as wide
transport=wide.transport;ROOT=wide.ROOT
CASES=(('healthy4g',4096,0),('healthy8g',8192,0),('child-crash',4096,1),
       ('child-hang',4096,2),('child-cpu',4096,3),('parent-crash',4096,4),
       ('quota',4096,6),('missing',4096,7))
MAGIC=0x31414d4454454e52

def need(ok,why):
    if not ok:raise ValueError(why)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,sort_keys=True,indent=2)

def config(image,folder,mode):
    inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    c=wide.payload.validate(inner);wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes();need(len(catalog)==4*wide.SIZE,'catalog')
    from run_qemu_x86_64_task_pool import fixture_sections
    attempts=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    need(len(attempts)==1,'exact program producer');addresses=[]
    for n in (0,2):
        record=catalog[n*wide.SIZE:(n+1)*wide.SIZE];tag=struct.pack('<12Q',MAGIC,*([0]*11))
        va=fixture_sections((attempts[0]/f'program{n}.prg').read_bytes())['.data']['address']
        offset=96+va-0x400000;need(record[offset:offset+96]==tag,'linked data witness')
        need(record[24+(va-0x400000)//4096]==6,'writable witness');addresses.append(va)
    symbols=transport.symbols(image);symbols['network_user_entry']=0x410000
    need(all(struct.unpack_from('<Q',catalog,n*wide.SIZE+16)[0]==0x410000 for n in range(4)),'common actual ELF entry')
    return dict(s=symbols,cs={n:v['value'] for n,v in c['symbols'].items()},
                folder=folder.as_posix(),case=mode,oom=None,addresses=addresses)

BODY=r'''
from pathlib import Path
F=Path(CONFIG['folder']);root_seen=0;finished=0;sequence=0
def dump(name,raw):
    with (F/name).open('xb') as output:output.write(raw)
    return dict(file=name,sha256=hashlib.sha256(raw).hexdigest())
def snapshot(kind,slot=None):
    global sequence
    sequence+=1;assert sequence<=24
    data={}
    spans={'state':(CS['native_network_state'],384),'dma':(CS['native_network_dma'],18432),
      'staging':(S['native_network_call'],1656),'tasks':(S['scheduler_tasks'],8192),
      'profiles':(S['family_profiles'],256),'family':(S['family_records'],512),
      'cpu':(S['scheduler_cpu_budgets'],256),'receipt':(S['process_run_receipt'],32)}
    for name,(address,size) in spans.items():data[name]=dump('%02d-%s.bin'%(sequence,name),mem(address,size))
    if slot in (0,2):data['witness']=dump('%02d-witness.bin'%sequence,user(task(slot),CONFIG['addresses'][slot//2],96))
    emit(kind,sequence=sequence,slot=slot,raw=data,free=free(),initial=d(S['scheduler_initial_free']),
         ticks=q(S['timer_runtime_ticks']),eois=q(S['timer_runtime_eois']))
def start():
    global root_seen
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    if gen in starts:return
    assert slot in (0,1,2) and t[0]==2 and reg('cs')&3==3,('start',slot,t[0],reg('cs'))
    starts[gen]=slot
    high=q(S['family_profiles']+slot*32+16)
    assert high==((1<<49) if slot in (0,2) else 0),('profile',slot,high)
    if slot==0:
        address=CONFIG['addresses'][0];raw=user(t,address,96)
        assert raw==struct.pack('<12Q',0x31414d4454454e52,*([0]*11))
        value=CASE if not root_seen or CASE==7 else 0;root_seen+=1
        leaf=walk(t[2],address+8);assert leaf&7==7 and leaf&(1<<63)
        physical=(leaf&MASK)+((address+8)&4095)
        gdb.selected_inferior().write_memory(DM+physical,struct.pack('<Q',value))
        emit('mode',gen=gen,slot=slot,value=value,physical=physical)
    emit('start',gen=gen,slot=slot,profile=high,parent=q(S['family_records']+slot*64+8))
def terminal():
    if mode()==8:snapshot('terminal',d(S['scheduler_current_slot']))
def finish():
    global finished
    finished+=1;assert finished<=2
    snapshot('finish')
    if finished==2:gdb.execute('detach');gdb.execute('quit')
def fail():
    emit('OBSERVER_FAIL',stage=mem(S['scheduler_failure_stage'],1)[0],rax=reg('rax'),rip=reg('rip'))
    gdb.execute('info registers');gdb.execute('quit 73')
def fatal():
    emit('OBSERVER_FAIL',where='exception',cr2=reg('cr2'),frame=mem(reg('rsp'),176).hex())
    gdb.execute('info registers');gdb.execute('quit 74')
Hook('network_user_entry',start)
Hook('family_terminal64.restore',terminal)
Hook('x86_64_c_process_run64.restore',finish)
Hook('scheduler_fail',fail)
Hook('exception_fatal',fatal)
'''

def observer(c,folder):
    prefix=wide.OBSERVER[:wide.OBSERVER.index('def poison():')].replace("'WIDE '","'NETWORK '").replace('callbacks<=4096','callbacks<=128')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
            '\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+repr(c)+'\n'+prefix+BODY+'\nend\ncontinue\n')

class Peer:
    def __init__(self,folder):
        self.folder=folder;self.stop=threading.Event();self.rows=[];self.error=None;self.connection=None
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(1);self.listener.settimeout(.1)
        self.port=self.listener.getsockname()[1];self.deadline=time.monotonic()+43
        self.thread=threading.Thread(target=self.work,daemon=True);self.thread.start()
    def receive(self,n):
        data=bytearray()
        while len(data)<n:
            if self.stop.is_set():return None
            need(time.monotonic()<self.deadline,'peer deadline')
            try:chunk=self.connection.recv(n-len(data))
            except socket.timeout:continue
            except ConnectionResetError:
                if not data:return None
                raise
            if not chunk:return None
            data+=chunk
        return bytes(data)
    def work(self):
        try:
            while not self.stop.is_set():
                need(time.monotonic()<self.deadline,'peer accept deadline')
                try:self.connection,address=self.listener.accept();break
                except socket.timeout:continue
            if self.connection is None:return
            need(address[0]=='127.0.0.1','local peer');self.connection.settimeout(.1)
            while not self.stop.is_set():
                header=self.receive(4)
                if header is None:break
                length=struct.unpack('>I',header)[0];need(14<=length<=1514,'Ethernet frame extent')
                tx=self.receive(length)
                if tx is None:break
                need(len(self.rows)<16,'peer frame capacity')
                rx=tx[6:12]+tx[:6]+tx[12:];self.rows.append(dict(tx=tx.hex(),rx=rx.hex()))
                self.connection.sendall(struct.pack('>I',len(rx))+rx)
        except BaseException as e:
            if not self.stop.is_set():self.error=repr(e)
        finally:
            if self.connection:self.connection.close()
    def close(self):
        self.stop.set();self.thread.join(timeout=.3);self.listener.close()
        need(not self.thread.is_alive(),'peer owned cleanup')
        save(self.folder/'packets.json',dict(closed=True,error=self.error,frames=self.rows))

def run(image,folder,spec):
    name,ram,mode=spec;folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    row=dict(case=name,ram=ram,mode=mode,image_sha256=sha(image),passed=False,closed=False)
    save(folder/'started.json',row);begin=time.monotonic();peer=None
    try:
        c=config(image,folder,mode);save(folder/'config.json',c);args=[]
        if mode!=7:
            peer=Peer(folder)
            args=['-netdev',f'socket,id=net0,connect=127.0.0.1:{peer.port}',
                  '-device','rtl8139,netdev=net0,addr=04.0,mac=52:54:00:12:34:56']
        transport._capture(image,folder,observer(c,folder),ram,args,diagnostic_metrics=True,service_pio_budget=True)
        row['passed']=True
    except BaseException as e:row['error']=str(e);raise
    finally:
        try:
            if peer:peer.close()
            else:save(folder/'packets.json',dict(closed=True,error=None,frames=[]))
            row['closed']=True
        finally:
            row['elapsed']=time.monotonic()-begin;save(folder/'result.json',row)
    need(row['elapsed']<=45,'total guest deadline');return row

def review(image,folder,spec):
    name,ram,mode=spec;folder=Path(folder)
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    need(read('config.json')==config(image,folder,mode),'exact observer image/configuration')
    row=read('result.json');need(row['passed'] and row['closed'] and row['elapsed']<=45,'bounded closed capture')
    need((row['case'],row['ram'],row['mode'],row['image_sha256'])==(name,ram,mode,sha(image)),'guest binding')
    serial=(folder/'guest.log').read_text(encoding='ascii');trace=(folder/'frame-trace.log').read_text(encoding='utf-8')
    need(not any(m in serial for m in transport.FAILURES) and 'OBSERVER_FAIL' not in trace,'kernel/observer healthy')
    need(serial.count(wide.process.SUCCESS)==1 and serial.count(wide.process.DONE)==2,'two completed cohorts')
    packets=read('packets.json');need(packets['closed'] and packets['error'] is None,'peer closure')
    expected=bytes.fromhex('52540012345752540012345688b5')+bytes(range(14,64))
    for p in packets['frames']:need(bytes.fromhex(p['tx'])==expected and bytes.fromhex(p['rx'])==expected[6:12]+expected[:6]+expected[12:],'exact real Ethernet round trip')
    events=[json.loads(line[8:]) for line in trace.splitlines() if line.startswith('NETWORK ')]
    need(all(e.get('kind') in ('mode','start','terminal','finish') for e in events),'known event stream')
    starts=[e for e in events if e['kind']=='start'];term=[e for e in events if e['kind']=='terminal'];fin=[e for e in events if e['kind']=='finish']
    need(len(fin)==2 and len(term)==len(starts) and len({e['gen'] for e in starts})==len(starts),'lifetime counts')
    modes=[e for e in events if e['kind']=='mode'];roots=[e for e in starts if e['slot']==0]
    need(len(roots)==2 and [(e['gen'],e['slot'],e['value']) for e in modes]==[(roots[0]['gen'],0,mode),(roots[1]['gen'],0,7 if mode==7 else 0)],'exact selector authority')
    need([e['sequence'] for e in events if e['kind'] in ('terminal','finish')]==list(range(1,len(term)+3)),'raw snapshot order')
    sizes=dict(state=384,dma=18432,staging=1656,tasks=8192,profiles=256,family=512,cpu=256,receipt=32)
    receipts=[struct.unpack('<4I2Q',bytes.fromhex(m[1])) for m in wide.process.REAP.finditer(serial)]
    need(len(receipts)==len(term),'serial receipt count')
    bygen={r[1]:r for r in receipts};need(len(bygen)==len(receipts),'unique serial generations')
    seen=[];children=0
    for e in term+fin:
        raw={}
        need(set(e['raw'])==set(sizes)|({'witness'} if e['slot'] in (0,2) else set()),'complete raw set')
        for k,v in e['raw'].items():
            p=folder/v['file'];need(p.parent==folder and sha(p)==v['sha256'],'raw hash');raw[k]=p.read_bytes()
            need(len(raw[k])==(96 if k=='witness' else sizes[k]),'exact raw extent')
        state=struct.unpack('<48Q',raw['state']);need(all(a^b==0xffffffffffffffff for a,b in zip(state[:24],state[24:])),'state mirror')
        need(state[3]==1 and state[7]==state[11]==0 and not any(raw['dma']) and not any(raw['staging']),'fenced and scrubbed DMA')
        need(e['ticks']==e['eois'],'IRQ balance')
        if e['kind']=='finish':
            need(not any(raw['tasks']+raw['profiles']+raw['family']+raw['cpu']+raw['receipt']) and state[0]==state[1]==0,'final authority cleared')
            need(e['free']==e['initial'] and e['free']>0,'frame restoration');continue
        r=struct.unpack('<4I2Q',raw['receipt']);slot,gen,status,phase,ticks,rip=r
        need(slot==e['slot'] and r==bygen.get(gen) and ticks<=32 and 0x410000<=rip<0x440000,'exact bounded receipt');seen.append(r)
        start=next((s for s in starts if s['gen']==gen),None);need(start and start['slot']==slot,'receipt generation')
        task=struct.unpack_from('<128Q',raw['tasks'],slot*1024)
        profile=struct.unpack_from('<4Q',raw['profiles'],slot*32)
        family=struct.unpack_from('<8Q',raw['family'],slot*64)
        cpu=struct.unpack_from('<4Q',raw['cpu'],slot*32)
        need(task[:2]==(phase,gen) and profile[0]==gen and profile[2]==start['profile']==((1<<49) if slot in (0,2) else 0),'actual task/profile binding')
        need(family[0]==(gen<<32|slot) and family[1]==start['parent'] and family[5]==(3 if slot==2 else 5),'actual parent/lifecycle binding')
        need(cpu[:3]==(gen,32,ticks),'actual CPU ledger')
        wanted=(77,4) if slot==1 else (82,4)
        if slot==0 and gen==1 and mode==4:wanted=(134,3)
        if slot==2:
            first=children==0;children+=1
            if mode==7:wanted=(19,4)
            elif first and mode in (1,2,3,4):wanted=({1:134,2:0,3:256,4:0}[mode],3)
            if first and mode==3:need(ticks==32,'CPU exhaustion reason')
        need((status,phase)==wanted,'exact terminal outcome '+str((r,wanted)))
        if slot in (0,2):
            w=struct.unpack('<12Q',raw['witness']);need(w[0]==MAGIC and w[2]==gen<<32|slot,'real witness identity')
            if slot==2 and mode!=7:need(w[3]==1 and w[5]==64,'real initialized receive witness')
            if status==82:need(w[8]==1,'complete consumer path')
    need(children==(2 if mode==7 else 3 if mode==4 else 4),'fresh replacement count')
    ordered=list(seen)
    if mode==4:
        need(ordered[1][:4]==(0,1,134,3) and ordered[2][:4]==(2,3,0,3),'parent fence before dependent terminal')
        ordered[1],ordered[2]=ordered[2],ordered[1]
    need(ordered==receipts,'exact child-before-parent reap ordering')
    need(len(packets['frames'])==(0 if mode==7 else children),'one actual frame per healthy device generation')
    return dict(tasks=len(term),children=children,packets=len(packets['frames']),image=sha(image),raw=sha(folder/'frame-trace.log'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    row=run(a.image.resolve(),a.evidence.resolve(),CASES[0]);row['proof']=review(a.image.resolve(),a.evidence.resolve(),CASES[0]);print(json.dumps(row))
