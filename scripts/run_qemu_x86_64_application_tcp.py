"""Bounded TCP development capture; acceptance requires separate raw review."""
from pathlib import Path
import argparse,ast,hashlib,json,struct
import run_qemu_x86_64_network_session as base
import run_qemu_x86_64_application_udp as udp
from check_x86_64_wide_shell_media import clone
CONFIGURE='ifconfig 192.0.2.2 255.255.255.0 192.0.2.1'
CONNECT='nc 192.0.2.3 5000 hello'
CASES=('healthy4g','healthy8g','wrong-grant','foreign-owner','stale-grant','malformed-ipc',
       'syn-retry','data-retry','peer-loss','bad-segments','receive-capacity','zero-window','peer-reset','close-paths',
       'app-crash','app-hang','app-cpu','stack-crash','stack-hang','stack-cpu',
       'driver-crash','driver-hang','driver-cpu','exhaustion','parent-crash')
def dialogue_text(raw):return base.command_echo(raw)
def specification(name):
    base.need(name in CASES or name=='root-console','frozen TCP case or reserved console diagnostic')
    app={'wrong-grant':[1],'foreign-owner':[2],'stale-grant':[0,3,8],
         'malformed-ipc':[4],'app-crash':[5],'app-hang':[6],'app-cpu':[7]}.get(name,[])
    root={'driver-crash':1,'driver-hang':2,'driver-cpu':3,'stack-crash':4,'stack-hang':5,
          'stack-cpu':6,'exhaustion':7,'parent-crash':8}.get(name,0)
    dialogue=['net status',CONFIGURE,CONNECT,CONNECT,'net status']
    if name=='root-console':dialogue=['net status']+[CONFIGURE]*8+[CONNECT,CONNECT,'net status']
    if name in ('healthy4g','healthy8g'):dialogue[-1:-1]=[udp.SEND,udp.RECEIVE]
    if name=='wrong-grant':dialogue[2:2]=['nc example 5000 hello','nc 192.0.2.4 5000 hello']
    if name=='stale-grant':dialogue[3:3]=[CONNECT,CONNECT]
    if name=='exhaustion':dialogue=['net status',CONFIGURE,CONNECT,CONNECT,CONNECT,'net status','net status']
    if name=='parent-crash':dialogue.insert(3,CONFIGURE)
    markers=[b'Network interface configured.']
    if name not in ('exhaustion','peer-loss','peer-reset','zero-window'):markers.append(b'tcp-local-peer')
    return dict(name=name,app=app,root=root,dialogue=dialogue,markers=markers,
                ram=8192 if name=='healthy8g' else 4096,cohorts=2 if name=='parent-crash' else 1)

class PeerModel:
    def __init__(self,name):self.name=name;self.connections={};self.old=None;self.udp_seen=False
    def frame(self,tx,port,seq,ack,flags,data=b'',window=2048):
        header=24 if flags&2 else 20
        raw=bytearray(14+20+header+len(data));raw[:12]=tx[6:12]+tx[:6];raw[12:14]=b'\x08\0'
        raw[14]=0x45;struct.pack_into('>H',raw,16,len(raw)-14);raw[20]=0x40;raw[22]=64;raw[23]=6
        raw[26:34]=tx[30:34]+tx[26:30];struct.pack_into('>H',raw,24,base.checksum(raw[14:34]))
        struct.pack_into('>HHII',raw,34,5000,port,seq&0xffffffff,ack&0xffffffff)
        raw[46]=header<<2;raw[47]=flags;struct.pack_into('>H',raw,48,window)
        if flags&2:raw[54:58]=bytes([2,4,2,0])
        raw[34+header:]=data;pseudo=raw[26:34]+bytes([0,6])+struct.pack('>H',len(raw)-34)
        struct.pack_into('>H',raw,50,base.checksum(pseudo+raw[34:]))
        return bytes(raw)
    def replies(self,tx):
        if tx[12:14]==b'\x08\x06':return udp.packet_replies(tx) if self.udp_seen else [base.reply(tx)]
        if len(tx)>34 and tx[23]==17:
            self.udp_seen=True;return udp.packet_replies(tx)
        base.need(len(tx)>=54 and tx[12:14]==b'\x08\0' and tx[14]==0x45 and tx[23]==6,'TCP frame')
        length=struct.unpack_from('>H',tx,16)[0]-20;header=(tx[46]>>4)*4
        base.need(20<=header<=length<=536 and length+34<=len(tx),'TCP lengths')
        base.need(base.checksum(tx[14:34])==0 and tx[26:34]==bytes([192,0,2,2,192,0,2,3]),'TCP IPv4 tuple/checksum')
        base.need(tx[:12]==bytes.fromhex('525400123457525400123456'),'TCP Ethernet peer')
        pseudo=tx[26:34]+bytes([0,6])+struct.pack('>H',length)
        base.need(base.checksum(pseudo+tx[34:34+length])==0,'TCP checksum')
        port,destination,seq,ack=struct.unpack_from('>HHII',tx,34);flags=tx[47];data=tx[34+header:34+length]
        base.need(49152<=port<=65535 and destination==5000,'explicit TCP ports')
        if flags==2:
            c=self.connections.setdefault(port,dict(syns=0,sends=0,client=(seq+1)&0xffffffff,server=0xfffffff1,fin=False))
            c['syns']+=1
            if self.name=='peer-loss' or self.name=='syn-retry' and c['syns']==1:return []
            return [self.frame(tx,port,c['server']-1,c['client'],18,window=0 if self.name=='zero-window' else 2048)]
        base.need(port in self.connections,'established tuple');c=self.connections[port]
        if data:
            base.need(flags==24 and data==b'hello','ordinary nc payload');c['sends']+=1
            c['client']=(seq+len(data))&0xffffffff
            if self.name=='data-retry' and c['sends']==1:return []
            if self.name=='peer-reset':return [self.frame(tx,port,c['server'],c['client'],20)]
            payload=b'tcp-local-peer'
            if self.name=='receive-capacity':
                result=[self.frame(tx,port,c['server']+n*512,c['client'],24,
                        payload+bytes([82+n])*(512-len(payload))) for n in range(5)]
                c['server']=(c['server']+2560)&0xffffffff
                return result
            valid=self.frame(tx,port,c['server'],c['client'],24,payload);result=[valid]
            if self.name=='bad-segments':
                bad=bytearray(valid);bad[50]^=1
                foreign=bytearray(valid);foreign[0]^=1
                impossible=self.frame(tx,port,c['server'],c['client']+512,24,payload)
                result=([self.old] if self.old else [])+[bytes(bad),bytes(foreign),impossible,valid]
                self.old=valid
            c['server']=(c['server']+len(payload))&0xffffffff
            if self.name!='close-paths':
                result.append(self.frame(tx,port,c['server'],c['client'],17));c['server']=(c['server']+1)&0xffffffff;c['fin']=True
            return result
        if flags==17:
            c['client']=(seq+1)&0xffffffff
            result=[self.frame(tx,port,c['server'],c['client'],16)]
            if not c['fin']:
                result.append(self.frame(tx,port,c['server'],c['client'],17));c['server']=(c['server']+1)&0xffffffff;c['fin']=True
            return result
        base.need(flags in (16,20),'TCP ACK or abort');return []

TCP_OBSERVER=r'''
tcp_entered=set();tcp_events=0
def tcp_save(kind,owner,spans,**fields):
    global tcp_events
    tcp_events+=1;assert tcp_events<=256
    paths={}
    for name,raw in spans.items():
        path=F/('tcp-%03d-%s.bin'%(tcp_events,name));path.write_bytes(raw)
        paths[name]=dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest())
    emit(kind,owner=owner,ordinal=tcp_events,raw=paths,ms=q(S['scheduler_last_tick'])*10,**fields)
def tcp_set(t,key,magic,value):
    address,size=CONFIG['tcp_symbols'][key];assert size==16
    before=user(t,address,16);assert before==struct.pack('<2Q',magic,0)
    leaf=walk(t[2],address+8);assert leaf&7==7 and leaf&(1<<63)
    physical=(leaf&MASK)+((address+8)&4095)
    gdb.selected_inferior().write_memory(DM+physical,struct.pack('<Q',value))
    tcp_save('tcp-injection',t[1]<<32|d(S['scheduler_current_slot']),{'before':before},
             target=key,value=value,physical=physical)
def tcp_enter():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);owner=t[1]<<32|slot
    if owner in tcp_entered:return
    if slot==0:
        tcp_entered.add(owner)
        tcp_set(t,'root_selection',0x31544f4f52544352,CONFIG['tcp_case']['root'] if not roots else 0)
    elif slot==6:
        tcp_entered.add(owner)
        index=sum(x&0xffffffff==6 for x in tcp_entered)-1
        values=CONFIG['tcp_case']['app'];value=values[index] if index<len(values) and len(roots)==1 else 0
        address,_=CONFIG['tcp_symbols']['app_selection']
        protocol=6 if user(t,address,16)==struct.pack('<2Q',0x3150504150435452,0) else 17
        if protocol==6:tcp_set(t,'app_selection',0x3150504150435452,value)
        else:
            address,_=CONFIG['tcp_symbols']['udp_selection']
            assert user(t,address,16)==struct.pack('<2Q',0x3150504144505552,0) and not value
        tcp_save('tcp-app-start',owner,{'profile':mem(S['family_profiles']+slot*32,32),
                 'family':mem(S['family_records']+slot*64,64)},parent=task(0)[1]<<32,protocol=protocol)
def tcp_response():
    if mode()!=8 or d(S['scheduler_current_slot'])!=5:return
    t=task(5);address,size=CONFIG['tcp_symbols']['applications']
    message=user(t,reg('rsi'),1600)
    if struct.unpack_from('<I',message,8)[0]==5:
        tcp_save('tcp-wire',t[1]<<32|5,{'applications':user(t,address,size),'message':message})
        return
    if struct.unpack_from('<I',message,8)[0]!=4:return
    ca,cn=CONFIG['roles'][5]['control'];control=user(t,ca,cn)
    operation=struct.unpack_from('<I',control,8)[0]
    if operation not in (10,11,12,13,14,15):return
    if operation<=12:address,size=CONFIG['tcp_symbols']['udp_applications']
    tcp_save('tcp-response',t[1]<<32|5,{'applications':user(t,address,size),'message':message,'control':control,
             'capabilities':mem(CS['ipc_capability_records'],2048),'endpoints':mem(CS['ipc_endpoints'],43648),
             'device':mem(CS['native_network_state'],384)},protocol=17 if operation<=12 else 6)
def tcp_exchange():
    if mode()!=8 or d(S['scheduler_current_slot'])!=5:return
    t=task(5);address,size=CONFIG['tcp_symbols']['applications'];assert reg('rdi')==address
    tcp_save('tcp-exchange',t[1]<<32|5,{'applications':user(t,address,size),
             'request':user(t,reg('rcx'),608)})

def tcp_ipc():
    if mode()!=8 or d(S['scheduler_current_slot'])!=6 or q(S['syscall_rax'])!=53:return
    t=task(6)
    tcp_save('tcp-request',t[1]<<32|6,{'request':user(t,q(S['syscall_rsi']),2060),
             'capabilities':mem(CS['ipc_capability_records'],2048),'endpoints':mem(CS['ipc_endpoints'],43648)},
             endpoint=q(S['syscall_rdi']),timeout=q(S['syscall_rdx']))
def tcp_finish():
    tcp_save('tcp-finish',0,{'capabilities':mem(CS['ipc_capability_records'],2048),
             'endpoints':mem(CS['ipc_endpoints'],43648)})
def tcp_root_terminal():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    t=task(0);spans={}
    for key in ('network_restarts','network_blocked','tcp_grant'):
        address,size=CONFIG['tcp_symbols'][key];spans[key]=user(t,address,size)
    if CONFIG['tcp_case']['name']=='root-console':
        rsp=t[69];assert 0x408000<=rsp<0x410000
        spans['stack']=user(t,rsp,min(512,0x410000-rsp))
        tcp_save('tcp-root-terminal',t[1]<<32,spans,rsp=rsp,pc=t[68])
    else:tcp_save('tcp-root-terminal',t[1]<<32,spans)
Hook('network_user_entry',tcp_enter)
Hook('network_stack_send',tcp_response)
Hook('tcp_exchange_entry',tcp_exchange)
# Count actual application sends at this shared kernel entry. Filesystem
# capture also uses IPC; unrelated calls must not consume this probe's budget.
class TCPIPCHook(Hook):
    def stop(self):
        if mode()!=8 or d(S['scheduler_current_slot'])!=6 or q(S['syscall_rax'])!=53:return False
        return super().stop()
TCPIPCHook('process_ipc_syscall64',tcp_ipc)
Hook('x86_64_c_process_run64.restore',tcp_finish)
Hook('family_terminal64.restore',tcp_root_terminal)
'''
def observer(selected,image,folder,spec):
    script=selected.original_observer(image,folder,0)
    source=script.read_text();line=next(line for line in source.splitlines() if line.startswith('CONFIG='))
    config=ast.literal_eval(line[7:]);catalog=(image.parent/'boot-programs.bin').read_bytes()
    attempts=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    base.need(len(attempts)==1,'one TCP producer')
    names={'program0':{'reist_tcp_root_selection':'root_selection','network_restarts':'network_restarts',
                      'network_blocked':'network_blocked','tcp_grant':'tcp_grant'},'tcp':{'reist_tcp_app_selection':'app_selection'},
           'udp':{'reist_udp_app_selection':'udp_selection'},
           'netstack':{'tcp_applications':'applications','applications':'udp_applications','reist_app_tcp_exchange':'exchange'}}
    symbols={}
    for program,wanted in names.items():
        for row in (attempts[0]/(program+'.map')).read_text().splitlines():
            words=row.split()
            if len(words)==5 and words[-1] in wanted:symbols[wanted[words[-1]]]=(int(words[0],16),int(words[2],16))
    base.need(set(symbols)=={'root_selection','app_selection','udp_selection','applications','udp_applications','exchange','network_restarts','network_blocked','tcp_grant'},'actual TCP observer symbols')
    config['tcp_symbols']=symbols;config['tcp_case']={k:spec[k] for k in ('name','app','root','cohorts')}
    config['s']['tcp_exchange_entry']=symbols['exchange'][0]
    source=source.replace(line,'CONFIG='+repr(config),1)
    from run_qemu_x86_64_runtime_clock import once
    source=once(source,"(2 if CONFIG['selector']==12 else 1)","CONFIG['tcp_case']['cohorts']")
    source=once(source,"Hook('family_terminal64.restore',terminal)",TCP_OBSERVER+"\nHook('family_terminal64.restore',terminal)")
    # Record the expanded configuration that actually drives the debugger.
    base.save(folder/'tcp-observer-config.json',config)
    extended=folder/'observe-tcp.gdb';extended.write_text(source,encoding='ascii');return extended
def controller(spec):
    source=Path(base.__file__).read_text();begin=source.index('            dialogue=')
    finish=source.index("            at=send('cat /data.txt')",begin)
    selected=clone(base,[
        ('import build_x86_64_network_media as media','import build_x86_64_application_tcp_media as media'),
        ('import check_x86_64_network_media as check','import check_x86_64_application_tcp_media as check'),
        ('row=dict(passed=False,qualified=False,selector=selector,ram=ram',
         "row=dict(passed=False,qualified=False,name=CASE['name'],selector=selector,ram=ram"),
        (source[begin:finish],"            def trace_events():\n                return stream_events((folder/'frame-trace.log').read_text(errors='replace'))\n            for text in CASE['dialogue']:command(text)\n"),
        ("sum(e['kind']=='finish' for e in trace_events())==(2 if selector==12 else 1)",
         "sum(e['kind']=='finish' for e in trace_events())==CASE['cohorts']"),
        ("(b'Network interface configured.',b'configured=yes',b'reply: received')","CASE['markers']"),
        ('all(marker in raw for marker in','all(marker in dialogue_text(raw) for marker in'),
        ("b'Read-only, generation-bound, revocable.' in raw","b'Read-only, generation-bound, revocable.' in dialogue_text(raw)"),
        ("need(peer is not None and len(peer.rows)>=5,'actual ARP/echo across TX ring wrap')",
         "need(peer is not None,'owned local TCP peer')"),
        ("need(len(self.rows)<64,'packet history bound');rx=reply(tx);responses=[rx]",
         "need(len(self.rows)<64,'packet history bound');responses=packet_replies(tx);rx=responses[0] if responses else b''")
    ],'reist_application_tcp_capture')
    selected.CASE=spec;selected.dialogue_text=dialogue_text;selected.packet_replies=PeerModel(spec['name']).replies
    selected.original_observer=selected.observer
    selected.observer=lambda image,folder,selector:observer(selected,image,folder,spec)
    return selected
def diagnostic(image,evidence,ram=4096,name=None):
    spec=specification(name or ('healthy8g' if ram==8192 else 'healthy4g'))
    selected=controller(spec)
    return selected.diagnostic(Path(image).resolve(),Path(evidence).resolve(),0,spec['ram'])
def review(image,folder,name):
    """Independent binary authority, packet, lifecycle and resource review."""
    spec=specification(name);folder=Path(folder);image=Path(image);need=base.need
    read=lambda n:json.loads((folder/n).read_text())
    result=read('result.json');config=read('tcp-observer-config.json')
    need(result['passed'] and result['closed'] and result['name']==name and result['selector']==0 and
         result['ram']==spec['ram'] and result['image_sha256']==hashlib.sha256(image.read_bytes()).hexdigest() and
         0<result['elapsed']<=180,'exact successful bounded capture')
    need(config['tcp_case']=={k:spec[k] for k in ('name','app','root','cohorts')},'exact injected case')
    serial=(folder/'guest.log').read_bytes();trace=(folder/'frame-trace.log').read_text()
    need(not any(x.encode() in serial for x in base.boot.FAILURES) and 'OBSERVER_FAIL' not in trace,'healthy kernel and observer')
    need(b'Read-only, generation-bound, revocable.' in dialogue_text(serial),'independent cat progress')
    before=read('media-before.json');after=read('media-after.json')
    need(before.pop('phase')=='before' and after.pop('phase')=='after' and before==after and
         after['overlay_allocated_data']==0 and after['logical_bytes']==1048576,'no media writes')
    events=[json.loads(line[11:]) for line in trace.splitlines() if line.startswith('NETSESSION ')]
    kinds={'selection','role-start','terminal','finish','group-retire','tcp-injection','tcp-app-start',
           'tcp-response','tcp-exchange','tcp-wire','tcp-request','tcp-finish','tcp-root-terminal'}
    need(all(e['kind'] in kinds for e in events),'known evidence stream')
    snapshots=[e for e in events if 'sequence' in e];extra=[e for e in events if 'ordinal' in e]
    need([e['sequence'] for e in snapshots]==list(range(1,len(snapshots)+1)) and len(snapshots)<=128,'bounded contiguous kernel capture')
    need([e['ordinal'] for e in extra]==list(range(1,len(extra)+1)) and len(extra)<=256,'bounded contiguous TCP capture')
    def raw(e,key,size=None):
        item=e['raw'][key];path=folder/item['file'];need(path.parent==folder,'local raw extent')
        value=path.read_bytes();need(hashlib.sha256(value).hexdigest()==item['sha256'] and
                                   (size is None or len(value)==size),'raw size/hash '+key)
        return value
    def device(value):
        state=struct.unpack('<48Q',value)
        need(all(state[n]^state[n+24]==(1<<64)-1 for n in range(24)),'protected device mirror')
        return state
    roots=[e['owner'] for e in events if e['kind']=='selection']
    need(len(roots)==spec['cohorts'] and len(set(roots))==len(roots) and
         all(e['value']==0 for e in events if e['kind']=='selection'),'exact root cohorts, no hidden legacy fault')
    starts={e['owner']:e for e in events if e['kind']=='role-start'}
    need(len(starts)==sum(e['kind']=='role-start' for e in events),'unique service starts')
    receipts=[struct.unpack('<4I2Q',bytes.fromhex(m.decode())) for m in base.re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',serial)]
    reaped={r[1]:r for r in receipts};need(len(reaped)==len(receipts),'unique serial receipts')
    terminals={};roles={};finishes=[];early=[]
    retirements=[e for e in events if e['kind']=='group-retire']
    for e in retirements:
        state=device(bytes.fromhex(e['state']))
        need(state[3]==1 and state[7]==state[11]==0 and not any(bytes.fromhex(e['dma'])),'fence before root CANCEL/WAIT')
    for e in snapshots:
        values={k:raw(e,k) for k in e['raw']}
        for k,size in dict(state=384,dma=18432,tasks=8192,profiles=256,family=512,cpu=256,windows=256).items():need(len(values[k])==size,'kernel extent '+k)
        state=device(values['state'])
        if e['kind']=='finish':
            need(state[0]==state[1]==0 and state[3]==1 and
                 not any(b''.join(values[k] for k in ('dma','staging','tasks','profiles','family','cpu','windows'))),
                 'all cohort authority, staging and DMA scrubbed')
            need(e['free']==e['initial'] and e['free']>0,'all frames restored');finishes.append(e);continue
        r=struct.unpack('<4I2Q',values['receipt']);slot,gen,status,phase,cpu,pc=r;owner=(gen<<32)|slot
        need(slot==e['slot'] and r==reaped.get(gen) and phase in (3,4) and cpu<=18000 and pc>=0x400000,'exact kernel terminal receipt')
        task=struct.unpack_from('<128Q',values['tasks'],slot*1024)
        profile=struct.unpack_from('<4Q',values['profiles'],slot*32);family=struct.unpack_from('<8Q',values['family'],slot*64)
        need(task[:2]==(phase,gen) and profile[0]==gen and family[0]==owner,'exact task/profile/family generation')
        need(owner not in terminals,'one terminal per owner');terminals[owner]=r
        budget=struct.unpack_from('<4Q',values['cpu'],slot*32);window=struct.unpack_from('<4Q',values['windows'],slot*32)
        need(budget[:3]==(gen,32,cpu) and budget[3]<=e['ms']//10,'exact generation CPU budget and usage')
        if owner in starts or window[0]:
            need(window[0]==100 and window[3]<=32,'CPU32/100 ticks unchanged')
            if status==256:need(window[3]==32 and phase==3,'actual exhausted CPU window')
        else:
            need(window==(0,0,0,0) and cpu<=32,'unchanged stricter foreground lifetime budget')
            if status==256:need(cpu==32 and phase==3,'actual exhausted lifetime CPU budget')
        if owner not in starts:continue
        need(profile[1]&(1<<54) and profile[2]==((1<<49) if slot==4 else 0) and profile[3]==0,'separate service device rights')
        need(family[1] in roots and starts[owner]['slot']==slot,'exact service parent')
        if slot==5 and state[3]==0:
            need(name in ('driver-hang','driver-cpu','stack-crash','stack-hang','stack-cpu','exhaustion') and
                 (status,phase) in ((5,4),(134,3),(256,3)),'bounded autonomous stack failure only')
            early.append((owner,e['ms']))
        else:need(state[3]==1 and state[7]==state[11]==0 and not any(values['dma']),'device-owner retirement fenced')
        need(state[0]==(owner if slot==4 else ((gen-1)<<32|4)) and state[1]==family[1] and state[2]>0,'actual device owner and epoch')
        roles[owner]=(r,state)
    need(len(finishes)==spec['cohorts'] and set(roles)==set(starts),'all cohorts and services retired')
    for owner,stamp in early:
        matches=[e for e in retirements if e['owner']==owner]
        need(matches and 0<=matches[0]['ms']-stamp<=1000,'failed dependency fenced within health deadline')
    parent_faults=[r for owner,r in terminals.items() if owner in roots and r[2:4]==(134,3)]
    need(len(parent_faults)==(1 if name=='parent-crash' else 0),'exact parent fault count')
    apps={};injections={};grants={};requests=[];responses=[];ipc_finishes=0;root_counters={};epochs={};wire=[];connections={}
    wanted_mask=sum(1<<n for n in (9,15,20,22,40,41,42,53,54))
    def capabilities(e,owner,parent):
        caps=raw(e,'capabilities',2048);endpoints=raw(e,'endpoints',43648);found=[]
        for n in range(64):
            at=n*32;active=caps[at]
            need(active in (0,1),'capability active bit')
            if not active:continue
            handle,holder,pid,generation,rights,slot=struct.unpack_from('<IQiIIB',caps,at+4)
            if pid!=owner>>32:continue
            need(holder and generation==pid and 0<=slot<16 and rights in (1,2),'attenuated application capability')
            ep=slot*2728
            need(endpoints[ep]==1 and struct.unpack_from('<iI',endpoints,ep+8)==(parent>>32,parent>>32),
                 'application endpoint is root-owned, never driver/stack-owned')
            found.append((handle,rights,slot))
        need(len(found)==2 and {x[1] for x in found}=={1,2} and len({x[2] for x in found})==2,'exact two directional application capabilities')
        return found
    def table(value,protocol):
        need(len(value)==(9432 if protocol==6 else 17360),'exact fixed application table')
        if protocol==17:return struct.unpack_from('<I',value,40)[0],48,720
        active,issued=struct.unpack_from('<2I',value,48)
        need(active in (0,1) and issued<=4,'bounded TCB issuance')
        for index in range(4):
            at=728+2176*index;handle,state,una,nxt,rcv,iss,window,mss,head,count,fin,retries=struct.unpack_from('<12I',value,at)
            need(handle in (0,index+1) and state<=8 and head<2048 and count<=2048 and fin<=1 and window<=65535,
                 'bounded TCP object/state/ring/window')
            if handle and state not in (0,1):need(0<mss<=65535,'negotiated bounded MSS')
            if handle:need(struct.unpack_from('<I',value,at+104)[0]==struct.unpack_from('<H',value,112)[0]+index,'unique port per TCB')
            need((nxt-una)&0xffffffff<=512,'single bounded flight')
        return active,56,728
    for e in extra:
        kind=e['kind'];owner=e['owner']
        if kind=='tcp-injection':
            before=raw(e,'before',16);target=e['target'];value=e['value']
            magic=0x31544f4f52544352 if target=='root_selection' else 0x3150504150435452
            need(before==struct.pack('<2Q',magic,0) and target in ('root_selection','app_selection'),'exact private zero-input injection')
            if target=='root_selection':need(owner in roots and value==(spec['root'] if owner==roots[0] else 0),'first-root fault only')
            else:
                need(owner not in injections,'one fault selection per TCP app');index=len(injections)
                need(value==(spec['app'][index] if index<len(spec['app']) else 0),'declared app fault');injections[owner]=value
        elif kind=='tcp-app-start':
            profile=struct.unpack('<4Q',raw(e,'profile',32));family=struct.unpack('<8Q',raw(e,'family',64))
            need(e['protocol'] in (6,17) and owner&0xffffffff==6 and profile==(owner>>32,wanted_mask,1<<63,0) and
                 family[:2]==(owner,e['parent']) and e['parent'] in roots,'exact attenuated foreground profile and parent')
            need((owner in injections)==(e['protocol']==6),'only matching application fixture')
            apps[owner]=(e['parent'],e['protocol'])
        elif kind=='tcp-request':
            need(owner in apps,'request from entered application');caps=capabilities(e,owner,apps[owner][0])
            need((e['endpoint'],1) in [(handle,right) for handle,right,_ in caps] and 0<e['timeout']<=100,'request uses root send capability')
            m=raw(e,'request',2060);need(struct.unpack_from('<3I',m)==(2,2060,608) and not any(m[620:]),'exact padded bulk request')
            q=m[12:620];need(struct.unpack_from('<I',q,48)[0]==apps[owner][1],'application protocol selector')
            requests.append((owner,q))
        elif kind=='tcp-response':
            protocol=e['protocol'];value=raw(e,'applications');active,grant_at,sockets_at=table(value,protocol)
            message=raw(e,'message',1600);control=raw(e,'control',1600);ds=device(raw(e,'device',384));op=struct.unpack_from('<I',control,8)[0]
            need(struct.unpack_from('<3I',message)==(1,1600,4) and struct.unpack_from('<Q',message,32)[0]==owner and
                 not any(message[52:64]),'canonical stack response')
            need(struct.unpack_from('<2I',control)==(1,1600) and message[16:24]==control[16:24] and not any(control[48:64]),'root control correlation')
            length=struct.unpack_from('<I',message,12)[0];result=struct.unpack_from('<i',message,48)[0]
            need(length in (0,608) and not any(message[64+length:]) and result==0,'successful stack transport and scrubbed tail')
            need(struct.unpack_from('<2Q',value)==(struct.unpack_from('<Q',control,32)[0],owner) and
                 ds[0]==(((owner>>32)-1)<<32|4) and ds[1]==struct.unpack_from('<Q',value)[0],'root/stack/device generation relation')
            first=13 if protocol==6 else 10
            if op==first:
                g=control[64:128];root,app,service,epoch,expires=struct.unpack_from('<5Q',g,8)
                port=49152+4*((app>>32)-1) if protocol==6 else 4000
                need(not length and active==1 and value[grant_at:grant_at+64]==g and struct.unpack_from('<2I',g)==(1,64) and
                     root in roots and service==owner and app&0xffffffff==6 and epoch>0 and
                     e['ms']<expires<=e['ms']+6000 and struct.unpack_from('<IIHHI',g,48)==(protocol,0xc0000203,port,5000,0),
                     'explicit destination and incarnation grant')
                key=(root,protocol);need(app not in grants and epoch>epochs.get(key,0),'fresh grant epoch and application')
                if protocol==6:need(1<=app>>32<=4096,'finite never-reused port range')
                grants[app]=g;epochs[key]=epoch
            elif op==first+2:
                need(not length and not active and not any(value[grant_at:]),'revoke scrubs grant, pending and objects')
            else:
                need(op==first+1 and length==608,'application operation response')
                q=control[64:672];reply=message[64:672];operation,handle,amount,status=struct.unpack_from('<IIIi',reply,80)
                app=struct.unpack_from('<Q',q,16)[0]
                need(app in grants and q[:64]==grants[app] and reply[:84]==q[:84] and
                     (operation==1 or reply[84:88]==q[84:88]) and -4095<=status<=0 and amount<=512,'exact object response')
                capabilities(e,app,struct.unpack_from('<Q',q,8)[0]);responses.append((app,operation,status,reply))
                if operation==6:need(not active and not any(value[grant_at:]),'release invalidates before ACK')
                elif protocol==6:
                    need(not any(value[120:728]),'no pending operation after response')
                    if not status and operation==3 and name=='receive-capacity':
                        at=sockets_at+(handle-1)*2176
                        expected=b''.join(b'tcp-local-peer'+bytes([82+n])*(512-14) for n in range(4))
                        need(struct.unpack_from('<2I',value,at+32)==(0,2048) and value[at+128:at+2176]==expected,
                             'four distinct segments fill ring; fifth cannot overwrite admitted bytes')
                    if not status and operation==4:
                        expected=(b'tcp-local-peer'+b'R'*(512-14)) if name=='receive-capacity' else b'tcp-local-peer'
                        need(reply[96:96+amount]==expected and amount==len(expected),'exact once bounded receive payload')
                    if not status and operation==5:
                        need(not struct.unpack_from('<I',value,sockets_at+(handle-1)*2176)[0],'close retires handle')
                    if operation in (2,3,4) and status:
                        at=sockets_at+(handle-1)*2176
                        if status==-9:
                            need(struct.unpack_from('<I',value,at)[0]==0 and
                                 struct.unpack_from('<I',value,at+4)[0] in (0,8),'retired handle has no authority, including TIME_WAIT')
                        else:
                            need(struct.unpack_from('<I',value,at+4)[0]==0 and not any(value[at+128:at+2176]),'failed operation aborts and scrubs receive state')
        elif kind in ('tcp-exchange','tcp-wire'):
            value=raw(e,'applications',9432);table(value,6)
            if kind=='tcp-exchange':
                q=raw(e,'request',608);need(q[:64]==value[56:120],'service receives exact current grant')
            else:
                message=raw(e,'message',1600);length=struct.unpack_from('<I',message,12)[0]
                need(struct.unpack_from('<3I',message)==(1,1600,5) and 14<=length<=1514 and not any(message[64+length:]),'bounded TX record')
                wire.append((e['ms'],message[64:64+length],value))
        elif kind=='tcp-root-terminal':
            need(owner in roots and owner not in root_counters,'one root lifecycle snapshot')
            counters=tuple(int.from_bytes(raw(e,k,config['tcp_symbols'][k][1]),'little') for k in ('network_restarts','network_blocked'))
            need(counters[0]<=2 and counters[1]<=1,'unchanged recovery limits')
            if name!='parent-crash' or owner!=roots[0]:need(not any(raw(e,'tcp_grant',64)),'root revokes before exit')
            root_counters[owner]=counters
        else:
            need(kind=='tcp-finish' and owner==0,'known TCP evidence event')
            need(not any(raw(e,'capabilities',2048)),'all IPC capabilities revoked')
            need(all(raw(e,'endpoints',43648)[n*2728]==0 for n in range(16)),'all endpoints retired');ipc_finishes+=1
    need(ipc_finishes==spec['cohorts'] and set(root_counters)==set(roots) and all(owner in terminals for owner in apps),'all app and root lifecycles complete')
    for owner,(_,protocol) in apps.items():
        r=terminals[owner];mode=injections.get(owner,0)
        if mode in (5,6,7):need(r[2:4]=={5:(134,3),6:(0,3),7:(256,3)}[mode],'exact application fault termination')
        elif protocol==17 or name in ('healthy4g','healthy8g','syn-retry','data-retry','bad-segments','receive-capacity','close-paths') or (name not in ('exhaustion','peer-loss','parent-crash','zero-window','peer-reset') and owner==max(apps)):
            need(r[2:4]==(0,4),'healthy foreground exits zero')
    if spec['root'] in range(1,8):
        slot=4 if spec['root'] in (1,2,3,7) else 5
        wanted={1:(134,3),2:(0,3),3:(256,3),4:(134,3),5:(0,3),6:(256,3),7:(134,3)}[spec['root']]
        victims=[r for owner,(r,_) in roles.items() if owner&0xffffffff==slot and r[2:4]==wanted]
        if wanted!=(0,3):need(len(victims)==(3 if name=='exhaustion' else 1),'exact selected service fault count')
        if name!='exhaustion':
            owners=sorted(owner for owner in roles if owner&0xffffffff==slot)
            need(len(owners)>=2 and roles[owners[1]][0][2:4]==wanted,'exact selected service generation fault')
            if name=='stack-hang':
                event=next(e for e in snapshots if e['kind']=='terminal' and e['slot']==5 and
                           struct.unpack_from('<I',raw(e,'receipt'),4)[0]==owners[1]>>32)
                control=raw(event,'control',1600)
                need(struct.unpack_from('<2I',control,8)==(14,608) and
                     struct.unpack_from('<I',control,144)[0]==2,'selected hung stack CONNECT')
        need(root_counters[roots[0]]==((2,1) if name=='exhaustion' else (1,0)),'exact bounded replacements')
    if spec['root']==0:need(all(x==(0,0) for x in root_counters.values()),'application and packet faults do not restart healthy services')
    packets=read('packets.json');need(packets['closed'] and packets['error'] is None and len(packets['frames'])<=64,'closed bounded peer')
    peer=PeerModel(name);transmissions=[]
    for row in packets['frames']:
        tx=bytes.fromhex(row['tx']);expected=peer.replies(tx)
        need(row['sent']==[x.hex() for x in expected] and row['rx']==(expected[0].hex() if expected else ''),'exact delivered peer frames')
        transmissions.append(tx)
    need([tx.ljust(60,b'\0') for _,tx,_ in wire]==transmissions,
         'every wire packet matches captured Ring3 TX and exact Ethernet zero padding')
    retries=0;tcp_frames=[]
    for stamp,tx,value in wire:
        if len(tx)<54 or tx[23]!=6:continue
        tcp_frames.append(tx);port=struct.unpack_from('>H',tx,34)[0];seq=struct.unpack_from('>I',tx,38)[0]
        length=struct.unpack_from('>H',tx,16)[0]-20;header=(tx[46]>>4)*4;payload=tx[34+header:34+length];flags=tx[47]
        if flags&2 or payload:
            key=(port,seq,flags,payload)
            if key in connections:
                need(stamp-connections[key]>=1000,'RFC6298 never early retransmission');retries+=1
            connections[key]=stamp
        if flags&2:
            g=value[56:120];app=struct.unpack_from('<Q',g,16)[0]
            need(app in grants and port==struct.unpack_from('<H',g,56)[0] and flags==2,'SYN only under current unique grant')
    if name in ('syn-retry','data-retry'):need(retries==2,'one real retransmission per connection')
    if name=='peer-loss':need(retries==2 and not any(op==3 for _,op,_,_ in responses),'no SEND after connect timeout')
    if name in ('healthy4g','healthy8g'):need(peer.udp_seen and sum(p==17 for _,p in apps.values())==2,'UDP coexists with TCP in same signed profile')
    if name=='bad-segments':
        need(len(peer.connections)==2 and peer.old is not None,'fresh generations and old tuple replay')
        ports=list(peer.connections);need(ports[1]>ports[0],'old tuple never assigned to next application')
    if name=='stale-grant':
        need(list(injections.values())==[0,3,8,0],'actual old epoch and retired handle fixtures')
        victim=next(o for o,m in injections.items() if m==3)
        q=next(q for o,q in requests if o==victim and struct.unpack_from('<I',q,80)[0]==3)
        epoch=struct.unpack_from('<Q',q,32)[0]
        need(epoch>0 and any(struct.unpack_from('<Q',g,32)[0]==epoch for o,g in grants.items() if o!=victim),'previously issued epoch replay')
        victim=next(o for o,m in injections.items() if m==8)
        need([(op,r) for o,op,r,_ in responses if o==victim][:4]==[(1,0),(2,0),(5,0),(3,-9)],'closed handle fails before wire SEND')
    if name=='exhaustion':need(serial.count(b'-11')>=2,'sticky exhausted network admission')
    exempt={roots[0]} if name=='parent-crash' else set()
    need(all(terminals[o][2:4]==(0,4) for o in roots if o not in exempt),'unrelated root exits normally')
    need(not any(r[2] in (134,256) for o,r in terminals.items() if o&0xffffffff in (2,3)),'no unrelated filesystem crash/quota fault')
    return dict(name=name,applications=len(apps),services=len(roles),packets=len(transmissions),tcp_frames=len(tcp_frames),
                retries=retries,cohorts=len(finishes),raw_events=len(extra))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--case',choices=CASES,default='healthy4g');a=p.parse_args()
    print(json.dumps(diagnostic(a.image,a.evidence,name=a.case)))
