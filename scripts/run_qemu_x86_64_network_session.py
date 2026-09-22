"""Bounded loopback-only native network dialogue and packet evidence."""
from pathlib import Path
import argparse,json,queue,socket,struct,subprocess,threading,time,os,hashlib,shutil,re
import run_qemu_x86_64_boot as boot
import run_qemu_x86_64_network_dma as boundary
from run_qemu_x86_64_graphical_session import Data
import build_x86_64_network_media as media
import check_x86_64_network_media as check
ROOT=Path(__file__).resolve().parents[1]
need=check.need
save=boundary.save
CASES=(('healthy4g',0,4096),('healthy8g',0,8192),
       ('driver-crash',1,4096),('driver-hang',2,4096),('driver-cpu',3,4096),
       ('stack-crash',4,4096),('stack-hang',5,4096),('stack-cpu',6,4096),
       ('bad-control',7,4096),('bad-packets',8,4096),('missing',9,4096),
       ('altered-service',10,4096),('exhaustion',11,4096),('parent-crash',12,4096))

def command_echo(raw):
    """Remove only complete fixed-format kernel reap records for echo pacing.
    Original bytes remain the evidence; no guest verdict uses this projection.
    """
    return re.sub(rb'REIST_X86_64_PROCESS_REAP_OK v1=[0-9A-F]{64}\r?\n',b'',raw)

def stream_events(text):
    """Only complete lines may drive live pacing; final review stays strict."""
    return [json.loads(line[11:]) for line in text.splitlines(keepends=True)
            if line.endswith('\n') and line.startswith('NETSESSION ')]

def observer(image,folder,selector=0):
    wide=boundary.wide
    parsed=wide.payload.validate((image.parent/'reist-x86_64-c-core.elf').read_bytes())
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    attempts=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    need(len(attempts)==1,'exact observer producer')
    from run_qemu_x86_64_task_pool import fixture_sections
    section=fixture_sections((attempts[0]/'program0.prg').read_bytes())['.data']
    start=96+section['address']-0x400000;data=catalog[start:start+section['size']]
    tag=struct.pack('<2Q',0x3153454e54454e52,0);need(data.count(tag)==1,'one actual root selection object')
    selection=section['address']+data.index(tag)
    roles={}
    stack_send=None
    for slot,name in ((4,'netdrv'),(5,'netstack')):
        entries={}
        for line in (attempts[0]/(name+'.map')).read_text().splitlines():
            words=line.split()
            if slot==5 and len(words)==5 and words[-1]=='reist_net_send':stack_send=int(words[0],16)
            if len(words)==5 and words[-1] in ('root','frames','binding','message','reply','packet','control','protocol',
                                              'reist_network_driver_witness','reist_netstack_witness'):
                entries[words[-1]]=(int(words[0],16),int(words[2],16))
        roles[slot]=entries
    config=dict(s=boundary.transport.symbols(image),cs={n:v['value'] for n,v in parsed['symbols'].items()},
                case=0,oom=None,folder=folder.as_posix(),roles=roles,selector=selector,selection=selection)
    config['s']['network_user_entry']=0x410000
    need(stack_send is not None,'actual stack transport entry');config['s']['network_stack_send']=stack_send
    save(folder/'observer-config.json',config)
    prefix=wide.OBSERVER[:wide.OBSERVER.index('def poison():')].replace("'WIDE '","'NETSESSION '")
    body=r'''
from pathlib import Path
F=Path(CONFIG['folder']);sequence=0;roots=set();injected=[]

def retire():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    operation=d(S['family_request']+8);owner=q(S['family_request']+16)
    if operation not in (2,3):return
    if owner>>32 not in starts or starts[owner>>32]!=(owner&0xffffffff):return
    state=mem(CS['native_network_state'],384);dma=mem(CS['native_network_dma'],18432)
    emit('group-retire',owner=owner,operation=operation,state=state.hex(),dma=dma.hex(),ms=q(S['scheduler_last_tick'])*10)
def corrupt_reply():
    if CONFIG['selector']!=7 or len(roots)!=1 or mode()!=8 or d(S['scheduler_current_slot'])!=5:return
    t=task(5)
    if t[1] in injected or len(injected)==2:return
    if reg('rdi')!=CONFIG['roles'][5]['root'][0]:return
    address=reg('rsi');message=user(t,address,64)
    if struct.unpack_from('<2I',message,8)!=(4,64):return
    offset=52 if not injected else 16;before=user(t,address+offset,4 if not injected else 8)
    after=struct.pack('<I',1) if not injected else struct.pack('<Q',struct.unpack('<Q',before)[0]-1)
    leaf=walk(t[2],address+offset);assert leaf&7==7 and leaf&(1<<63)
    physical=(leaf&MASK)+((address+offset)&4095)
    gdb.selected_inferior().write_memory(DM+physical,after)
    injected.append(t[1]);emit('control-injection',owner=t[1]<<32|5,offset=offset,before=before.hex(),after=after.hex())
def enter():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot'])
    if slot in (4,5):
        t=task(slot);key='reist_network_driver_witness' if slot==4 else 'reist_netstack_witness'
        address,size=CONFIG['roles'][slot][key]
        magic=0x3156524454454e52 if slot==4 else 0x314b545354454e52
        if t[1] not in starts and user(t,address,8)==struct.pack('<Q',magic):
            starts[t[1]]=slot;emit('role-start',owner=t[1]<<32|slot,slot=slot)
        return
    if slot!=0:return
    t=task(0)
    if t[1] in roots:return
    assert t[0]==2 and reg('cs')&3==3
    address=CONFIG['selection'];assert user(t,address,16)==struct.pack('<2Q',0x3153454e54454e52,0)
    value=CONFIG['selector'] if not roots else 0;roots.add(t[1])
    leaf=walk(t[2],address+8);assert leaf&7==7 and leaf&(1<<63)
    physical=(leaf&MASK)+((address+8)&4095)
    gdb.selected_inferior().write_memory(DM+physical,struct.pack('<Q',value))
    emit('selection',owner=t[1]<<32,value=value,physical=physical)
def terminal():
    global sequence
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);sequence+=1;assert sequence<=128
    spans={'receipt':mem(S['process_run_receipt'],32),'tasks':mem(S['scheduler_tasks'],8192),
           'cpu':mem(S['scheduler_cpu_budgets'],256),'windows':mem(S['scheduler_cpu_windows'],256),
           'profiles':mem(S['family_profiles'],256),'family':mem(S['family_records'],512),
           'state':mem(CS['native_network_state'],384),'dma':mem(CS['native_network_dma'],18432)}
    if slot in CONFIG['roles']:
        for name,(address,size) in CONFIG['roles'][slot].items():spans[name]=user(task(slot),address,size)
    paths={}
    for name,raw in spans.items():
        path=F/('%03d-%s.bin'%(sequence,name));path.write_bytes(raw)
        paths[name]=dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest())
    emit('terminal',slot=slot,sequence=sequence,raw=paths,free=free(),ms=q(S['scheduler_last_tick'])*10)
def finish():
    global sequence
    sequence+=1
    spans={'state':mem(CS['native_network_state'],384),'dma':mem(CS['native_network_dma'],18432),
           'cpu':mem(S['scheduler_cpu_budgets'],256),'windows':mem(S['scheduler_cpu_windows'],256),
           'staging':mem(S['native_network_call'],1656),'tasks':mem(S['scheduler_tasks'],8192),
           'profiles':mem(S['family_profiles'],256),'family':mem(S['family_records'],512)}
    paths={}
    for name,raw in spans.items():
        path=F/('%03d-%s.bin'%(sequence,name));path.write_bytes(raw)
        paths[name]=dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest())
    emit('finish',sequence=sequence,raw=paths,free=free(),initial=d(S['scheduler_initial_free']))
    if len(roots)==(2 if CONFIG['selector']==12 else 1):
        gdb.execute('detach');gdb.execute('quit')
Hook('family_terminal64.restore',terminal)
Hook('network_user_entry',enter)
Hook('network_stack_send',corrupt_reply)
Hook('family_syscall64.admitted',retire)
Hook('x86_64_c_process_run64.restore',finish)
'''
    script=folder/'observe.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'
        'set breakpoint always-inserted on\ntarget remote 127.0.0.1:12491\nset logging file '+
        (folder/'frame-trace.log').as_posix()+'\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+
        repr(config)+'\n'+prefix+body+'\nend\ncontinue\n',encoding='ascii')
    return script

def checksum(raw):
    padded=raw+b'\0'*(len(raw)%2);s=sum(struct.unpack('>'+str(len(padded)//2)+'H',padded))
    s=(s&65535)+(s>>16);s=(s&65535)+(s>>16);return (~s)&65535

def reply(frame):
    need(60<=len(frame)<=1514,'bounded Ethernet transmission')
    source=bytes.fromhex('525400123457');local=bytes.fromhex('525400123456')
    need(frame[6:12]==local,'actual configured sender MAC')
    rx=bytearray(frame);rx[:6]=local;rx[6:12]=source
    if frame[12:14]==b'\x08\x06':
        need(frame[:6]==b'\xff'*6 and frame[14:22]==bytes.fromhex('0001080006040001'),'RFC826 Ethernet request')
        need(frame[22:28]==local and frame[28:32]==bytes([192,0,2,2]) and frame[38:42]==bytes([192,0,2,3]),'exact ARP addresses')
        rx[20:22]=b'\0\2';rx[22:28]=source;rx[28:32]=frame[38:42];rx[32:38]=local;rx[38:42]=frame[28:32]
    elif frame[12:14]==b'\x08\0':
        need(frame[:6]==source and frame[14]==0x45 and frame[23]==1 and checksum(frame[14:34])==0,'valid IPv4 ICMP header')
        total=struct.unpack_from('>H',frame,16)[0];need(total==44 and frame[34:36]==b'\x08\0' and checksum(frame[34:14+total])==0,'bounded valid echo request')
        need(frame[26:30]==bytes([192,0,2,2]) and frame[30:34]==bytes([192,0,2,3]),'exact ICMP addresses')
        rx[26:30]=frame[30:34];rx[30:34]=frame[26:30];rx[34]=0;rx[36:38]=b'\0\0'
        struct.pack_into('>H',rx,36,checksum(bytes(rx[34:14+total])));rx[24:26]=b'\0\0'
        struct.pack_into('>H',rx,24,checksum(bytes(rx[14:34])))
    else:raise ValueError('unexpected EtherType')
    return bytes(rx)

class Peer(boundary.Peer):
    def __init__(self,folder,fault=False):
        self.fault=fault;self.old_echo=None;self.arps=0
        super().__init__(folder);self.deadline=time.monotonic()+175
    def work(self):
        try:
            while not self.stop.is_set():
                need(time.monotonic()<self.deadline,'peer accept deadline')
                try:self.connection,address=self.listener.accept();break
                except socket.timeout:continue
            if self.connection is None:return
            need(address[0]=='127.0.0.1','loopback peer');self.connection.settimeout(.1)
            while not self.stop.is_set():
                header=self.receive(4)
                if header is None:break
                length=struct.unpack('>I',header)[0];need(14<=length<=1514,'frame bound')
                tx=self.receive(length)
                if tx is None:break
                need(len(self.rows)<64,'packet history bound');rx=reply(tx);responses=[rx]
                if self.fault:
                    if tx[12:14]==b'\x08\x06':
                        self.arps+=1
                        if self.arps==1:responses=[]
                    elif self.old_echo is None:
                        self.old_echo=rx
                        bad=bytearray(rx);bad[36]^=1
                        foreign=bytearray(rx);foreign[0]^=2
                        responses=[bytes(bad),bytes(foreign)]
                    else:responses=[self.old_echo,rx]
                self.rows.append(dict(tx=tx.hex(),rx=rx.hex(),sent=[p.hex() for p in responses]))
                for packet in responses:self.connection.sendall(struct.pack('>I',len(packet))+packet)
        except BaseException as error:
            if not self.stop.is_set():self.error=repr(error)
        finally:
            if self.connection:self.connection.close()

def diagnostic(image,folder,selector=0,ram=4096):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();end=start+180;vm=None;peer=None;fixture=None;raw=bytearray();reader=None;debugger=None;debuglog=None
    need(selector in range(13) and ram in (4096,8192),'declared diagnostic selector/RAM')
    row=dict(passed=False,qualified=False,selector=selector,ram=ram,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),limit=180)
    save(folder/'started.json',row);pending=queue.Queue(maxsize=512);overflow=threading.Event()
    try:
        values=media.inputs(image.parent);files=check.medium_files(values)
        if selector==10:
            changed=bytearray(files['netdrv.prg']);ph=struct.unpack_from('<Q',changed,32)[0]
            count=struct.unpack_from('<H',changed,56)[0]
            loads=[struct.unpack_from('<II6Q',changed,ph+n*56) for n in range(count)]
            load=next(p for p in loads if p[0]==1 and p[1]==5 and p[5]>64)
            offset=load[2]+64;changed[offset]^=1
            row['altered_service']=dict(offset=offset,before=hashlib.sha256(files['netdrv.prg']).hexdigest(),after=hashlib.sha256(changed).hexdigest())
            files['netdrv.prg']=bytes(changed)
        volume=media.image('ext2-1k',files);check.verify_volume(volume,files)
        fixture=Data(folder,volume,end);fixture.verify('before')
        if selector!=9:peer=Peer(folder,selector==8)
        command=[str(boot.resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m',str(ram)+'M','-smp','1',
                 '-display','none','-monitor','none','-nic','none','-serial','stdio','-no-reboot','-no-shutdown',
                 '-kernel',str(image),'-S','-gdb','tcp:127.0.0.1:12491',*fixture.arguments(folder)]
        if peer:command+=['-netdev',f'socket,id=net0,connect=127.0.0.1:{peer.port}',
                         '-device','rtl8139,netdev=net0,addr=04.0,mac=52:54:00:12:34:56']
        save(folder/'command.json',command)
        with (folder/'stderr.log').open('wb') as errors:
            vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,bufsize=0,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            script=observer(image,folder,selector);debuglog=(folder/'observer.log').open('wb')
            debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],stdout=debuglog,
                                      stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            def read():
                while chunk:=os.read(vm.stdout.fileno(),4096):
                    try:pending.put_nowait(chunk)
                    except queue.Full:overflow.set();return
            reader=threading.Thread(target=read,daemon=True);reader.start()
            def pump():
                for _ in range(512):
                    try:raw.extend(pending.get_nowait())
                    except queue.Empty:break
                need(len(raw)<=1048576 and not overflow.is_set(),'serial capacity')
                need(not any(f.encode() in raw for f in boot.FAILURES),'guest fatal')
                need(vm.poll() is None,'unexpected QEMU exit')
            def wait(predicate,seconds):
                deadline=min(end-5,time.monotonic()+seconds)
                while time.monotonic()<deadline:
                    pump()
                    if predicate():return
                    time.sleep(.005)
                raise TimeoutError(raw[-1000:].decode(errors='replace'))
            def send(text):
                at=len(raw);prefix=b'';wire=text.encode('ascii')
                for offset in range(0,len(wire),8):
                    chunk=wire[offset:offset+8];vm.stdin.write(chunk);vm.stdin.flush();prefix+=chunk
                    wait(lambda:prefix in command_echo(raw[at:]),5)
                vm.stdin.write(b'\n');vm.stdin.flush();return at
            wait(lambda:b'C:\\>' in raw,35)
            def command(text):
                at=send(text);wait(lambda:b'C:\\>' in raw[at:],50);return at
            dialogue=['net status','ifconfig 192.0.2.2 255.255.255.0 192.0.2.1','arp 192.0.2.3','net status']
            if selector==7:dialogue.insert(2,'ifconfig 192.0.2.2 255.255.255.0 192.0.2.1')
            if selector in (9,10):dialogue=['net status','net status']
            if selector==11:dialogue=dialogue[:2]+['arp 192.0.2.3']*3+['net status','net status']
            fault_requests=0
            def trace_events():
                return stream_events((folder/'frame-trace.log').read_text(errors='replace'))
            for text in dialogue:
                at=command(text)
                if text.startswith('arp ') and selector==11:
                    fault_requests+=1
                    if fault_requests<3:
                        wait(lambda:sum(e['kind']=='role-start' and e['slot']==5 for e in trace_events())>=fault_requests+1,8)
                    else:
                        wait(lambda:sum(e['kind']=='group-retire' and e['operation']==2 and e['owner']&0xffffffff==4 for e in trace_events())==3,8)
                if text.startswith('arp ') and selector in (1,2,3):
                    def replacement_started():
                        trace=(folder/'frame-trace.log').read_text(errors='replace')
                        events=stream_events(trace)
                        return sum(e['kind']=='role-start' and e['slot']==5 for e in events)>=2
                    wait(replacement_started,8)
                    save(folder/'automatic-recovery.json',dict(before_next_command=True,elapsed=time.monotonic()-start))
            if selector==12:
                at=send('ping 192.0.2.3');wait(lambda:b'C:\\>' in raw[at:],15)
                for text in dialogue:command(text)
            if selector not in (9,10,11):
                at=send('ping 192.0.2.3');wait(lambda:raw[at:].count(b'reply: received')>=2,20)
                vm.stdin.write(b'\x03');vm.stdin.flush();wait(lambda:b'C:\\>' in raw[at:],5)
            at=send('cat /data.txt');wait(lambda:b'C:\\>' in raw[at:],30)
            at=send('exit');wait(lambda:b'REIST_X86_64_PROCESS_RUN_OK' in raw[at:],10)
            wait(lambda:debugger.poll()==0 and sum(e['kind']=='finish' for e in trace_events())==(2 if selector==12 else 1),10)
            row['dialogue_complete']=True
            need(b'Read-only, generation-bound, revocable.' in raw,'independent file command progress')
            if selector not in (9,10,11):
                need(all(marker in raw for marker in (b'Network interface configured.',b'configured=yes',b'reply: received')),
                     'complete ordinary shell configuration/ping dialogue')
                need(peer is not None and len(peer.rows)>=5,'actual ARP/echo across TX ring wrap')
            if peer:need(peer.error is None,'peer stayed healthy')
            row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        if vm is not None:
            if vm.stdin:vm.stdin.close()
            boot.terminate_bounded(vm)
            if reader:reader.join(timeout=1)
            for _ in range(512):
                try:raw.extend(pending.get_nowait())
                except queue.Empty:break
            vm.stdout.close()
        if debugger:boot.terminate_bounded(debugger)
        if debuglog:debuglog.close()
        (folder/'guest.log').write_bytes(raw)
        try:
            if peer:peer.close()
            if fixture:row['media_after']=fixture.verify('after')
            row['closed']=True
        finally:
            row['elapsed']=time.monotonic()-start;save(folder/'result.json',row)
    need(row['elapsed']<=180,'guest deadline')
    return row

def review(image,folder,spec):
    """Check raw authority, terminal receipts and Ethernet independently."""
    name,selector,ram=spec;folder=Path(folder)
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    result=read('result.json');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    need(result['closed'] and 0<result['elapsed']<=180,'owned bounded cleanup')
    need((result['selector'],result['ram'],result['image_sha256'])==(selector,ram,sha(image)),'exact guest binding')
    serial=(folder/'guest.log').read_bytes();trace=(folder/'frame-trace.log').read_text()
    need(not any(m.encode() in serial for m in boot.FAILURES) and 'OBSERVER_FAIL' not in trace,'healthy kernel/observer')
    need(b'Read-only, generation-bound, revocable.' in serial,'independent file progress')
    before=read('media-before.json');after=read('media-after.json')
    need(before.pop('phase')=='before' and after.pop('phase')=='after' and before==after and
         after['overlay_allocated_data']==0 and after['logical_bytes']==1048576,'unchanged read-only medium')
    events=[json.loads(line[11:]) for line in trace.splitlines() if line.startswith('NETSESSION ')]
    need(all(e['kind'] in ('selection','role-start','terminal','finish','control-injection','group-retire') for e in events),'known evidence stream')
    snapshots=[e for e in events if 'sequence' in e]
    need([e['sequence'] for e in snapshots]==list(range(1,len(snapshots)+1)) and len(snapshots)<=128,'contiguous bounded snapshots')
    selections=[e for e in events if e['kind']=='selection']
    need(1<=len(selections)<=3 and selections[0]['value']==selector and all(e['value']==0 for e in selections[1:]),'first cohort only injection')
    starts={e['owner']:e for e in events if e['kind']=='role-start'}
    need(len(starts)==sum(e['kind']=='role-start' for e in events),'unique role starts')
    receipts=[struct.unpack('<4I2Q',bytes.fromhex(m.decode())) for m in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',serial)]
    reaped={r[1]:r for r in receipts};need(len(reaped)==len(receipts),'unique exact reaps')
    roles={};finishes=[];parent_fault=False;states=[];early=[]
    retirements=[e for e in events if e['kind']=='group-retire']
    for e in retirements:
        state=struct.unpack('<48Q',bytes.fromhex(e['state']))
        need(all(state[n]^state[n+24]==(1<<64)-1 for n in range(24)) and state[3]==1 and
             state[7]==state[11]==0 and not any(bytes.fromhex(e['dma'])),'fenced and scrubbed before root cancel/wait')
    for e in snapshots:
        raw={}
        for k,item in e['raw'].items():
            p=folder/item['file'];need(p.parent==folder and sha(p)==item['sha256'],'raw extent/hash '+k);raw[k]=p.read_bytes()
        for k,size in dict(state=384,dma=18432,tasks=8192,profiles=256,family=512,cpu=256,windows=256).items():need(len(raw[k])==size,'raw size '+k)
        state=struct.unpack('<48Q',raw['state'])
        need(all(state[n]^state[n+24]==(1<<64)-1 for n in range(24)),'protected state mirror')
        if e['kind']=='finish':
            need(state[0]==state[1]==0 and state[3]==1 and not any(raw['dma']+raw['staging']+raw['tasks']+raw['profiles']+raw['family']+raw['cpu']+raw['windows']),
                 'all cohort authority/DMA/staging scrubbed')
            need(e['free']==e['initial'] and e['free']>0,'all cohort frames restored');finishes.append(e);continue
        receipt=struct.unpack('<4I2Q',raw['receipt']);slot,gen,status,phase,cpu,pc=receipt;owner=gen<<32|slot
        need(slot==e['slot'] and receipt==reaped.get(gen) and phase in (3,4) and cpu<=18000 and pc>=0x400000,'actual terminal and serial receipt')
        task=struct.unpack_from('<128Q',raw['tasks'],slot*1024);profile=struct.unpack_from('<4Q',raw['profiles'],slot*32)
        family=struct.unpack_from('<8Q',raw['family'],slot*64)
        need(task[:2]==(phase,gen) and profile[0]==gen and family[0]==owner,'generation-scoped task/profile/family')
        if slot==0 and status==134 and phase==3:parent_fault=True
        if owner not in starts:continue
        budget=struct.unpack_from('<4Q',raw['cpu'],slot*32);window=struct.unpack_from('<4Q',raw['windows'],slot*32)
        need(budget[:3]==(gen,32,cpu) and window[0]==100 and window[3]<=32 and budget[3]<=e['ms']//10,
             'actual unchanged CPU32/100-tick profile and lifetime ledger')
        if status==256:need(window[3]==32 and phase==3,'actual exhausted current CPU window')
        need(owner not in roles and starts[owner]['slot']==slot,'one role retirement')
        need(profile[1]&(1<<54) and profile[2]==((1<<49) if slot==4 else 0),'isolated role rights')
        need(family[1] in {s['owner'] for s in selections},'exact parent generation')
        if slot==5 and state[3]==0:
            need(selector in (2,3,4,5,6,11) and not any(k&0xffffffff==5 for k in roles) and
                 (status,phase) in ((5,4),(134,3),(256,3)),'only first autonomous stack failure before group fence')
            early.append((owner,e['ms']))
        else:need(state[3]==1 and state[7]==state[11]==0 and not any(raw['dma']),'fence and scrub before device-owner retirement')
        if selector!=9:
            need(state[0]&0xffffffff==4 and state[1]==family[1] and state[2]>0,'actual device owner/epoch')
            need(state[0]==(owner if slot==4 else ((gen-1)<<32|4)),'matching driver generation')
        roles[owner]=(receipt,state,e['ms']);states.append(state)
    need(len(finishes)==(2 if selector==12 else 1),'completed cohort count')
    need(set(roles)==set(starts),'all launched network roles retired')
    for owner,stamp in early:
        collected=[e for e in retirements if e['owner']==owner]
        need(collected and 0<=collected[0]['ms']-stamp<=1000,'dependency failure fenced within health deadline')
    for owner,(receipt,state,stamp) in roles.items():
        if selector==12 and state[1]==selections[0]['owner']:continue
        need({e['operation'] for e in retirements if e['owner']==owner}=={2,3},'root exact-generation cancel and wait')
    drivers=[v for k,v in roles.items() if k&0xffffffff==4];stacks=[v for k,v in roles.items() if k&0xffffffff==5]
    expected=0 if selector==10 else 3 if selector in (7,9,11) else 2 if selector in (1,2,3,4,5,6,12) else 1
    need(len(drivers)==len(stacks)==expected,'bounded exact replacements')
    if selector in (1,2,3,4,5,6,11):
        victims=drivers if selector in (1,2,3,11) else stacks
        wanted={1:(134,3),2:(0,3),3:(256,3),4:(134,3),5:(0,3),6:(256,3),11:(134,3)}[selector]
        for victim in victims if selector==11 else victims[:1]:
            need(victim[0][2:4]==wanted,'exact injected fault outcome')
    need(parent_fault==(selector==12),'exact parent fault scope')
    injections=[e for e in events if e['kind']=='control-injection']
    if selector==7:
        need(len(injections)==2 and [e['offset'] for e in injections]==[52,16],'malformed then stale control injection')
        need(injections[0]['before']=='00000000' and injections[0]['after']=='01000000','one reserved bit')
        need(int.from_bytes(bytes.fromhex(injections[1]['before']),'little')==int.from_bytes(bytes.fromhex(injections[1]['after']),'little')+1,'old epoch only')
    else:need(not injections,'no unintended control mutation')
    frames=[]
    if selector!=9:
        packets=read('packets.json');need(packets['closed'] and packets['error'] is None,'owned peer cleanup');frames=packets['frames']
    need(len(frames)<=64,'bounded packets');echoes=[]
    for p in frames:
        tx=bytes.fromhex(p['tx']);rx=reply(tx);need(rx.hex()==p['rx'],'actual RFC826/791/792 reply')
        if selector!=8:need(p['sent']==[rx.hex()],'exact delivered frame')
        if tx[12:14]==b'\x08\0':echoes.append(tx)
    if selector not in (9,10,11):
        need(serial.count(b'reply: received')==2 and len(echoes)==(3 if selector==8 else 2),'exact successful echo count')
        need(serial.index(b'Read-only, generation-bound, revocable.')>serial.rindex(b'reply: received'),'file command after recovery')
        for a,b in zip(echoes,echoes[1:]):need(a[42:50]==b[42:50] and int.from_bytes(b[50:58],'big')==int.from_bytes(a[50:58],'big')+1,'fresh wire operation nonce')
        need(int.from_bytes(echoes[-1][42:50],'big')==drivers[-1][1][2],'wire nonce uses actual device epoch')
        need(drivers[-1][1][17]>=4 and drivers[-1][1][18]>=4,'actual kernel TX/RX progress')
    else:
        need(not echoes and b'reply: received' not in serial,'no packet progress after failed admission')
        if selector in (9,10):need(not frames,'no traffic from missing/altered role')
        if selector in (9,11):need(serial.count(b'-11')>=1,'sticky exhausted manual admission')
    if selector==8:
        need(frames[0]['sent']==[],'withheld solicited ARP')
        echo_rows=[p for p in frames if bytes.fromhex(p['tx'])[12:14]==b'\x08\0']
        first=bytes.fromhex(echo_rows[0]['rx']);bad=bytearray(first);bad[36]^=1;foreign=bytearray(first);foreign[0]^=2
        need(echo_rows[0]['sent']==[bad.hex(),foreign.hex()],'only bad checksum/foreign replies first')
        need(all(p['sent']==[first.hex(),p['rx']] for p in echo_rows[1:]),'late old reply before each valid current reply')
        need(b'Packets sent=3 received=2' in serial and b'ARP request failed code=' in serial,'timeouts did not satisfy current request')
    if selector==10:need(result['altered_service']['before']!=result['altered_service']['after'],'mutated service hash')
    return dict(case=name,roles=len(roles),packets=len(frames),finishes=len(finishes),image=sha(image),trace=sha(folder/'frame-trace.log'))

def review_diagnostic(image,folder):
    """Replay the healthy control plane from retained bytes, not its verdict."""
    folder=Path(folder);read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    result=read('result.json');need(result['closed'] and result['elapsed']<=180,'closed bounded guest')
    need(result['image_sha256']==hashlib.sha256(image.read_bytes()).hexdigest(),'exact diagnostic image')
    packets=read('packets.json');need(packets['closed'] and packets['error'] is None,'closed local peer')
    need(len(packets['frames'])==5,'five transmissions crossing TX ring wrap')
    kinds=[]
    for row in packets['frames']:
        tx=bytes.fromhex(row['tx']);rx=bytes.fromhex(row['rx']);need(reply(tx)==rx,'exact valid wire reply')
        kinds.append(tx[12:14])
    need(kinds==[b'\x08\x06',b'\x08\x06',b'\x08\0',b'\x08\x06',b'\x08\0'],'ARP and two echo exchanges')
    a=bytes.fromhex(packets['frames'][2]['tx']);b=bytes.fromhex(packets['frames'][4]['tx'])
    need(a[42:50]==b[42:50] and int.from_bytes(b[50:58],'big')==int.from_bytes(a[50:58],'big')+1,
         'new operation correlation in actual echo payload')
    text=(folder/'guest.log').read_text(encoding='ascii')
    need(not any(m in text for m in boot.FAILURES),'no kernel fatal marker')
    need(text.count('reply: received')==2 and 'Packets sent=2 received=2' in text,'ordinary shell echo results')
    need(text.index('Read-only, generation-bound, revocable.')>text.index('Packets sent=2 received=2'),'independent file progress afterward')
    events=[json.loads(line[11:]) for line in (folder/'frame-trace.log').read_text().splitlines() if line.startswith('NETSESSION ')]
    events=[event for event in events if event['kind']=='terminal']
    need(1<=len(events)<=128,'bounded actual terminal captures');roles={};owners={};previous=0
    for event in events:
        need(event['sequence']==previous+1 and event['kind']=='terminal','contiguous terminal events');previous+=1
        raw={}
        for name,item in event['raw'].items():
            path=folder/item['file'];need(path.parent==folder and path.is_file(),'local raw extent')
            raw[name]=path.read_bytes();need(hashlib.sha256(raw[name]).hexdigest()==item['sha256'],'raw byte binding')
        state=struct.unpack('<48Q',raw['state'])
        need(all(state[n]^state[n+24]==(1<<64)-1 for n in range(24)),'valid protected network state')
        slot,generation,status,phase,cpu,pc=struct.unpack('<4I2Q',raw['receipt'])
        # Receipt CPU is lifetime ticks, not the existing 32/1000ms periodic
        # window. A long-lived healthy root can legitimately exceed 32 total.
        need(slot==event['slot'] and slot<8 and phase in (3,4) and cpu<=18000 and pc>=0x400000,'actual terminal receipt')
        if slot in (4,5) and state[0] and generation==((state[0]>>32)+(slot-4)):
            need(slot not in roles,'unique network role terminal')
            profile=struct.unpack_from('<QQ',raw['profiles'],slot*32+8)
            need(profile[0]&(1<<54) and profile[1]==((1<<49) if slot==4 else 0),'actual separate receive/device permissions')
            need(state[0]&0xffffffff==4 and state[1]&0xffffffff==0 and state[2]==1,'generation-scoped bound driver and parent')
            need(state[3]==1 and not any(raw['dma']),'device fenced and DMA scrubbed before group reaping')
            need(state[17:19]==(5,5) and state[11]==0,'five actual kernel TX/RX records and no pending descriptors')
            channel=struct.unpack('<6Q2I',raw['frames']);need(channel[0]==generation<<32|slot,'actual channel owner')
            if slot==5:
                protocol=struct.unpack('<3Q4I8s',raw['protocol'])
                need(protocol[0:2]==(1,3) and protocol[3:7]==(0xc0000202,0xffffff00,0xc0000201,1),'real stack state and completed operations')
            roles[slot]=generation;owners[slot]=state[0]
    need(set(roles)=={4,5} and owners[4]==owners[5],'both exact network generations retired')
    return dict(qualified=False,packets=5,echoes=2,roles=roles,terminals=len(events),image=result['image_sha256'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--selector',type=int,default=0)
    a=p.parse_args();print(json.dumps(diagnostic(a.image.resolve(),a.evidence.resolve(),a.selector)))
