"""Bounded UDP development capture; no acceptance verdict is inferred here."""
from pathlib import Path
import argparse,ast,hashlib,json,struct
import run_qemu_x86_64_network_session as base
from check_x86_64_wide_shell_media import clone
CONFIGURE='ifconfig 192.0.2.2 255.255.255.0 192.0.2.1'
SEND='udp send 192.0.2.3 5000 4000 hello'
RECEIVE='udp recv 192.0.2.3 5000 4000 2000'
CASES=('healthy4g','healthy8g','wrong-grant','foreign-owner','stale-grant','malformed-ipc',
       'peer-loss','bad-packets','queue-full','app-crash','app-hang','app-cpu',
       'stack-crash','stack-hang','stack-cpu','driver-crash','driver-hang','driver-cpu',
       'exhaustion','parent-crash')

def dialogue_text(raw):
    """Project application text across complete kernel records only.

    Original serial receipts and independent binary authority/packet evidence
    remain mandatory; this projection alone never proves fault containment.
    """
    return base.command_echo(raw)
def specification(name):
    base.need(name in CASES,'frozen UDP case')
    app={'wrong-grant':[1],'foreign-owner':[2],'stale-grant':[0,3,8],
         'malformed-ipc':[4],'app-crash':[5],'app-hang':[6],'app-cpu':[7]}.get(name,[])
    root={'driver-crash':1,'driver-hang':2,'driver-cpu':3,'stack-crash':4,'stack-hang':5,
          'stack-cpu':6,'exhaustion':7,'parent-crash':8}.get(name,0)
    dialogue=['net status',CONFIGURE,SEND,RECEIVE,'net status']
    if name=='wrong-grant':dialogue[2:2]=['udp recv 4000','udp send 192.0.2.4 5000 4000 hello']
    if name=='stale-grant':dialogue[3:3]=[SEND,SEND]
    if name=='exhaustion':dialogue=['net status',CONFIGURE,SEND,SEND,SEND,'net status','net status']
    if name=='parent-crash':dialogue.insert(3,CONFIGURE)
    markers=[b'Network interface configured.']
    if name not in ('exhaustion','peer-loss'):markers.append(b'udp-local-peer')
    if name in ('healthy4g','healthy8g','bad-packets','queue-full'):markers.append(b'datagram sent')
    return dict(name=name,app=app,root=root,dialogue=dialogue,markers=markers,
                ram=8192 if name=='healthy8g' else 4096,cohorts=2 if name=='parent-crash' else 1)
def packet_replies(frame,name='healthy4g'):
    if frame[12:14]==b'\x08\x06':
        arp=base.reply(frame)
        data=b'udp-local-peer';rx=bytearray(42+len(data))
        rx[:12]=arp[:12];rx[12:14]=b'\x08\0';rx[14]=0x45
        struct.pack_into('>H',rx,16,28+len(data));rx[20]=0x40;rx[22]=64;rx[23]=17
        rx[26:30]=bytes([192,0,2,3]);rx[30:34]=bytes([192,0,2,2])
        struct.pack_into('>H',rx,24,base.checksum(bytes(rx[14:34])))
        struct.pack_into('>4H',rx,34,5000,4000,8+len(data),0);rx[42:]=data
        if name=='peer-loss':return []
        if name=='queue-full':return [arp]+[bytes(rx) for _ in range(6)]
        if name=='bad-packets':
            checksum=bytearray(rx);checksum[40]=1
            foreign=bytearray(rx);foreign[0]^=1
            port=bytearray(rx);port[35]^=1
            fragment=bytearray(rx);fragment[20]|=0x20;fragment[24:26]=b'\0\0'
            struct.pack_into('>H',fragment,24,base.checksum(bytes(fragment[14:34])))
            return [arp,bytes(checksum),bytes(foreign),bytes(port),bytes(fragment),bytes(rx)]
        return [arp,bytes(rx)]
    base.need(len(frame)>=42 and frame[12:14]==b'\x08\0' and frame[14]==0x45 and frame[23]==17,'UDP frame')
    total=struct.unpack_from('>H',frame,16)[0];length=struct.unpack_from('>H',frame,38)[0]
    base.need(total==20+length and 8<=length<=520 and total+14<=len(frame),'UDP lengths')
    base.need(base.checksum(frame[14:34])==0 and frame[26:34]==bytes([192,0,2,2,192,0,2,3]),'IPv4 source/destination/checksum')
    base.need(frame[:12]==bytes.fromhex('525400123457525400123456'),'UDP Ethernet peer')
    base.need(struct.unpack_from('>2H',frame,34)==(4000,5000),'explicit UDP ports')
    pseudo=frame[26:34]+bytes([0,17])+struct.pack('>H',length)
    base.need(base.checksum(pseudo+frame[34:34+length])==0 and frame[40:42]!=b'\0\0','UDP checksum')
    base.need(frame[42:34+length]==b'hello','ordinary application payload')
    return []
UDP_OBSERVER=r'''
udp_entered=set();udp_events=0
def udp_save(kind,owner,spans,**fields):
    global udp_events
    udp_events+=1;assert udp_events<=256
    paths={}
    for name,raw in spans.items():
        path=F/('udp-%03d-%s.bin'%(udp_events,name));path.write_bytes(raw)
        paths[name]=dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest())
    emit(kind,owner=owner,ordinal=udp_events,raw=paths,ms=q(S['scheduler_last_tick'])*10,**fields)
def udp_set(t,key,magic,value):
    address,size=CONFIG['udp_symbols'][key];assert size==16
    before=user(t,address,16);assert before==struct.pack('<2Q',magic,0)
    leaf=walk(t[2],address+8);assert leaf&7==7 and leaf&(1<<63)
    physical=(leaf&MASK)+((address+8)&4095)
    gdb.selected_inferior().write_memory(DM+physical,struct.pack('<Q',value))
    udp_save('udp-injection',t[1]<<32|d(S['scheduler_current_slot']),{'before':before},
             target=key,value=value,physical=physical)
def udp_enter():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);owner=t[1]<<32|slot
    if owner in udp_entered:return
    if slot==0:
        udp_entered.add(owner)
        udp_set(t,'root_selection',0x31544f4f52445552,CONFIG['udp_case']['root'] if not roots else 0)
    elif slot==6:
        udp_entered.add(owner)
        index=sum(x&0xffffffff==6 for x in udp_entered)-1
        values=CONFIG['udp_case']['app'];value=values[index] if index<len(values) and len(roots)==1 else 0
        udp_set(t,'app_selection',0x3150504144505552,value)
        udp_save('udp-app-start',owner,{'profile':mem(S['family_profiles']+slot*32,32),
                 'family':mem(S['family_records']+slot*64,64)},parent=task(0)[1]<<32)
def udp_response():
    if mode()!=8 or d(S['scheduler_current_slot'])!=5:return
    t=task(5);address,size=CONFIG['udp_symbols']['applications']
    message=user(t,reg('rsi'),1600)
    if struct.unpack_from('<I',message,8)[0]!=4:return
    ca,cn=CONFIG['roles'][5]['control'];control=user(t,ca,cn)
    operation=struct.unpack_from('<I',control,8)[0]
    if operation not in (10,11,12):return
    udp_save('udp-response',t[1]<<32|5,{'applications':user(t,address,size),'message':message,'control':control,
             'capabilities':mem(CS['ipc_capability_records'],2048),'endpoints':mem(CS['ipc_endpoints'],43648),
             'device':mem(CS['native_network_state'],384)})
def udp_enqueue():
    if mode()!=8 or d(S['scheduler_current_slot'])!=5:return
    t=task(5);address,size=CONFIG['udp_symbols']['applications'];assert reg('rdi')==address
    length=reg('rcx');assert length<=512
    udp_save('udp-enqueue',t[1]<<32|5,{'applications':user(t,address,size),
             'grant':user(t,reg('rsi'),64),'payload':user(t,reg('rdx'),length)},length=length)
def udp_ipc():
    if mode()!=8 or d(S['scheduler_current_slot'])!=6 or q(S['syscall_rax'])!=53:return
    t=task(6)
    udp_save('udp-request',t[1]<<32|6,{'request':user(t,q(S['syscall_rsi']),2060),
             'capabilities':mem(CS['ipc_capability_records'],2048),'endpoints':mem(CS['ipc_endpoints'],43648)},
             endpoint=q(S['syscall_rdi']),timeout=q(S['syscall_rdx']))
def udp_finish():
    udp_save('udp-finish',0,{'capabilities':mem(CS['ipc_capability_records'],2048),
             'endpoints':mem(CS['ipc_endpoints'],43648)})
def udp_root_terminal():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    t=task(0);spans={}
    for key in ('network_restarts','network_blocked','udp_grant'):
        address,size=CONFIG['udp_symbols'][key];spans[key]=user(t,address,size)
    udp_save('udp-root-terminal',t[1]<<32,spans)
Hook('network_user_entry',udp_enter)
Hook('network_stack_send',udp_response)
Hook('udp_enqueue_entry',udp_enqueue)
# Count actual application sends at this shared kernel entry. Filesystem
# capture also uses IPC; unrelated calls must not consume this probe's budget.
class UDPIPCHook(Hook):
    def stop(self):
        if mode()!=8 or d(S['scheduler_current_slot'])!=6 or q(S['syscall_rax'])!=53:return False
        return super().stop()
UDPIPCHook('process_ipc_syscall64',udp_ipc)
Hook('x86_64_c_process_run64.restore',udp_finish)
Hook('family_terminal64.restore',udp_root_terminal)
'''
def observer(selected,image,folder,spec):
    script=selected.original_observer(image,folder,0)
    source=script.read_text();line=next(line for line in source.splitlines() if line.startswith('CONFIG='))
    config=ast.literal_eval(line[7:]);catalog=(image.parent/'boot-programs.bin').read_bytes()
    attempts=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    base.need(len(attempts)==1,'one UDP producer')
    names={'program0':{'reist_udp_root_selection':'root_selection','network_restarts':'network_restarts',
                      'network_blocked':'network_blocked','udp_grant':'udp_grant'},'udp':{'reist_udp_app_selection':'app_selection'},
           'netstack':{'applications':'applications','reist_app_udp_enqueue':'enqueue'}}
    symbols={}
    for program,wanted in names.items():
        for row in (attempts[0]/(program+'.map')).read_text().splitlines():
            words=row.split()
            if len(words)==5 and words[-1] in wanted:symbols[wanted[words[-1]]]=(int(words[0],16),int(words[2],16))
    base.need(set(symbols)=={'root_selection','app_selection','applications','enqueue','network_restarts','network_blocked','udp_grant'},'actual UDP observer symbols')
    config['udp_symbols']=symbols;config['udp_case']={k:spec[k] for k in ('name','app','root','cohorts')}
    config['s']['udp_enqueue_entry']=symbols['enqueue'][0]
    source=source.replace(line,'CONFIG='+repr(config),1)
    from run_qemu_x86_64_runtime_clock import once
    source=once(source,"(2 if CONFIG['selector']==12 else 1)","CONFIG['udp_case']['cohorts']")
    source=once(source,"Hook('family_terminal64.restore',terminal)",UDP_OBSERVER+"\nHook('family_terminal64.restore',terminal)")
    # Record the expanded configuration that actually drives the debugger.
    base.save(folder/'udp-observer-config.json',config)
    extended=folder/'observe-udp.gdb';extended.write_text(source,encoding='ascii');return extended
def controller(spec):
    source=Path(base.__file__).read_text();begin=source.index('            dialogue=')
    finish=source.index("            at=send('cat /data.txt')",begin)
    selected=clone(base,[
        ('import build_x86_64_network_media as media','import build_x86_64_application_udp_media as media'),
        ('import check_x86_64_network_media as check','import check_x86_64_application_udp_media as check'),
        ('row=dict(passed=False,qualified=False,selector=selector,ram=ram',
         "row=dict(passed=False,qualified=False,name=CASE['name'],selector=selector,ram=ram"),
        (source[begin:finish],"            def trace_events():\n                return stream_events((folder/'frame-trace.log').read_text(errors='replace'))\n            for text in CASE['dialogue']:command(text)\n"),
        ("sum(e['kind']=='finish' for e in trace_events())==(2 if selector==12 else 1)",
         "sum(e['kind']=='finish' for e in trace_events())==CASE['cohorts']"),
        ("(b'Network interface configured.',b'configured=yes',b'reply: received')","CASE['markers']"),
        ('all(marker in raw for marker in','all(marker in dialogue_text(raw) for marker in'),
        ("b'Read-only, generation-bound, revocable.' in raw","b'Read-only, generation-bound, revocable.' in dialogue_text(raw)"),
        ("need(peer is not None and len(peer.rows)>=5,'actual ARP/echo across TX ring wrap')",
         "need(peer is not None,'owned local UDP peer')"),
        ("need(len(self.rows)<64,'packet history bound');rx=reply(tx);responses=[rx]",
         "need(len(self.rows)<64,'packet history bound');responses=packet_replies(tx);rx=responses[0] if responses else b''")
    ],'reist_application_udp_capture')
    selected.CASE=spec;selected.dialogue_text=dialogue_text;selected.packet_replies=lambda frame:packet_replies(frame,spec['name'])
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
    result=read('result.json');config=read('udp-observer-config.json')
    need(result['passed'] and result['closed'] and result['name']==name and result['selector']==0 and
         result['ram']==spec['ram'] and result['image_sha256']==hashlib.sha256(image.read_bytes()).hexdigest() and
         0<result['elapsed']<=180,'exact successful bounded capture')
    need(config['udp_case']=={k:spec[k] for k in ('name','app','root','cohorts')},'exact injected case')
    serial=(folder/'guest.log').read_bytes();trace=(folder/'frame-trace.log').read_text()
    need(not any(x.encode() in serial for x in base.boot.FAILURES) and 'OBSERVER_FAIL' not in trace,'healthy kernel and observer')
    need(b'Read-only, generation-bound, revocable.' in dialogue_text(serial),'independent cat progress')
    before=read('media-before.json');after=read('media-after.json')
    need(before.pop('phase')=='before' and after.pop('phase')=='after' and before==after and
         after['overlay_allocated_data']==0 and after['logical_bytes']==1048576,'no media writes')
    events=[json.loads(line[11:]) for line in trace.splitlines() if line.startswith('NETSESSION ')]
    kinds={'selection','role-start','terminal','finish','group-retire','udp-injection','udp-app-start',
           'udp-response','udp-enqueue','udp-request','udp-finish','udp-root-terminal'}
    need(all(e['kind'] in kinds for e in events),'known evidence stream')
    snapshots=[e for e in events if 'sequence' in e];extra=[e for e in events if 'ordinal' in e]
    need([e['sequence'] for e in snapshots]==list(range(1,len(snapshots)+1)) and len(snapshots)<=128,'bounded contiguous kernel capture')
    need([e['ordinal'] for e in extra]==list(range(1,len(extra)+1)) and len(extra)<=256,'bounded contiguous UDP capture')
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
    apps={};injections={};grants={};requests=[];responses=[];queues=[];ipc_finishes=0;root_counters={};epochs={}
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
    for e in extra:
        kind=e['kind'];owner=e['owner']
        if kind=='udp-injection':
            before=raw(e,'before',16);target=e['target'];value=e['value']
            magic=0x31544f4f52445552 if target=='root_selection' else 0x3150504144505552
            need(before==struct.pack('<2Q',magic,0) and target in ('root_selection','app_selection'),'exact private zero-input injection')
            if target=='root_selection':need(owner in roots and value==(spec['root'] if owner==roots[0] else 0),'first-root fault input only')
            else:
                need(owner not in injections,'one app fault input');index=len(injections)
                expected=spec['app'][index] if index<len(spec['app']) else 0
                need(value==expected,'declared app fault input');injections[owner]=value
        elif kind=='udp-app-start':
            profile=struct.unpack('<4Q',raw(e,'profile',32));family=struct.unpack('<8Q',raw(e,'family',64))
            need(owner&0xffffffff==6 and owner in injections and profile==(owner>>32,wanted_mask,1<<63,0) and
                 family[:2]==(owner,e['parent']) and e['parent'] in roots,'exact foreground profile/parent, no device or delegation rights')
            apps[owner]=e['parent']
        elif kind=='udp-request':
            need(owner in apps,'request from entered foreground');caps=capabilities(e,owner,apps[owner])
            need((e['endpoint'],1) in {(h,r) for h,r,_ in caps} and 0<e['timeout']<=100,'actual send capability and bounded IPC')
            bulk=raw(e,'request',2060);need(struct.unpack_from('<3I',bulk)==(2,2060,608) and not any(bulk[620:]),'exact zero-padded IPC request')
            q=bulk[12:620];requests.append((owner,q))
            need(owner in grants,'published service grant before application use')
            expected=bytearray(grants[owner]);op=struct.unpack_from('<I',q,80)[0];fault=injections[owner]
            if op==0:expected[8:16]=b'\0'*8;expected[24:48]=b'\0'*24
            if op==3:
                if fault==1:struct.pack_into('<I',expected,52,struct.unpack_from('<I',expected,52)[0]+1)
                if fault==2:struct.pack_into('<Q',expected,16,owner+(1<<32))
                if fault==3:struct.pack_into('<Q',expected,32,struct.unpack_from('<Q',expected,32)[0]-1)
                if fault==4:struct.pack_into('<I',expected,60,1)
            need(q[:64]==expected and 0<=op<=6 and struct.unpack_from('<i',q,92)[0]==0,'exact declared request authority or mutation')
        elif kind=='udp-response':
            state=raw(e,'applications',17360);message=raw(e,'message',1600);control=raw(e,'control',1600)
            ds=device(raw(e,'device',384));op=struct.unpack_from('<I',control,8)[0]
            need(struct.unpack_from('<2I',message)==(1,1600) and struct.unpack_from('<I',message,8)[0]==4 and
                 struct.unpack_from('<Q',message,32)[0]==owner and not any(message[52:64]),'actual stack response envelope')
            need(struct.unpack_from('<2I',control)==(1,1600) and message[16:24]==control[16:24] and
                 not any(control[48:64]),'same group epoch and canonical root control')
            length=struct.unpack_from('<I',message,12)[0];result=struct.unpack_from('<i',message,48)[0]
            need(length in (0,608) and not any(message[64+length:]) and result==0,'successful internal result with scrubbed tail')
            need(struct.unpack_from('<2Q',state)==(struct.unpack_from('<Q',control,32)[0],owner) and
                 ds[0]==(((owner>>32)-1)<<32|4) and ds[1]==struct.unpack_from('<Q',state)[0],
                 'actual root/stack/device generation relation')
            active=struct.unpack_from('<I',state,40)[0]
            if op==10:
                g=control[64:128];root,app,service,epoch,expires=struct.unpack_from('<5Q',g,8)
                need(not length and active==1 and state[48:112]==g and struct.unpack_from('<2I',g)==(1,64) and
                     root in roots and service==owner and app&0xffffffff==6 and epoch>0 and
                     e['ms']<expires<=e['ms']+6000 and struct.unpack_from('<IIHHI',g,48)==(17,0xc0000203,4000,5000,0),
                     'explicit fixed-peer generation-bound service grant')
                need(app not in grants and epoch>epochs.get(root,0),'fresh application and increasing root grant epoch');grants[app]=g;epochs[root]=epoch
            elif op==12:
                need(not length and not active and not any(state[48:112]+state[112:]),'revocation clears grant, pending operation and queues')
            else:
                need(op==11 and length==608,'application operation response')
                q=control[64:672];reply=message[64:672];operation=struct.unpack_from('<I',q,80)[0]
                app=struct.unpack_from('<Q',q,16)[0]
                need(app in grants and q[:64]==grants[app] and reply[:84]==q[:84] and
                     (operation==1 or reply[84:88]==q[84:88]),'exact object reply correlation')
                capabilities(e,app,struct.unpack_from('<Q',q,8)[0]);responses.append((app,operation,struct.unpack_from('<i',reply,92)[0]))
                if operation==6:need(not active and not any(state[48:]),'release revokes every object before acknowledging')
        elif kind=='udp-enqueue':
            state=raw(e,'applications',17360);g=raw(e,'grant',64);payload=raw(e,'payload',e['length'])
            need(state[48:112]==g and struct.unpack_from('<Q',g,24)[0]==owner and payload==b'udp-local-peer','only validated bounded peer payload enters queue')
            handle,bound,head,count=struct.unpack_from('<4I',state,720)
            need(handle and bound==1 and head<4 and count<=4,'fixed-capacity UDP queue');queues.append((count,state[720:2800]))
        elif kind=='udp-root-terminal':
            need(owner in roots and owner not in root_counters,'one root lifecycle snapshot')
            counters=tuple(int.from_bytes(raw(e,k,config['udp_symbols'][k][1]),'little') for k in ('network_restarts','network_blocked'))
            need(config['udp_symbols']['network_restarts'][1]==4 and config['udp_symbols']['network_blocked'][1] in (1,4),'actual compiler counter extents')
            need(counters[0]<=2 and counters[1]<=1,'bounded root network recovery counters')
            if name!='parent-crash' or owner!=roots[0]:need(not any(raw(e,'udp_grant',64)),'root grant revoked before normal exit')
            root_counters[owner]=counters
        else:
            need(kind=='udp-finish' and owner==0,'known UDP terminal evidence')
            need(not any(raw(e,'capabilities',2048)),'all IPC capabilities revoked at cohort end')
            endpoints=raw(e,'endpoints',43648)
            need(all(endpoints[n*2728]==0 for n in range(16)),'no live endpoint after cohort');ipc_finishes+=1
    need(ipc_finishes==spec['cohorts'] and set(root_counters)==set(roots) and set(apps)==set(injections) and
         all(owner in terminals for owner in apps),'all app owners and IPC cohorts retired')
    for owner in apps:
        r=terminals[owner];mode=injections[owner]
        if mode==5:need(r[2:4]==(134,3),'exact app crash')
        elif mode==6:need(r[2:4]==(0,3),'bounded app hang cancellation')
        elif mode==7:need(r[2:4]==(256,3),'exact app CPU quota')
        elif name in ('healthy4g','healthy8g','bad-packets','queue-full') or name not in ('exhaustion','peer-loss','parent-crash') and owner==max(apps):
            need(r[2:4]==(0,4),'healthy application exits zero')
    if spec['root'] in range(1,8):
        slot=4 if spec['root'] in (1,2,3,7) else 5
        wanted={1:(134,3),2:(0,3),3:(256,3),4:(134,3),5:(0,3),6:(256,3),7:(134,3)}[spec['root']]
        if name=='exhaustion':
            victims=[r for owner,(r,_) in roles.items() if owner&0xffffffff==slot and r[2:4]==wanted]
            need(len(victims)==3 and root_counters[roots[0]]==(2,1),'three faults, exactly two replacements and sticky exhaustion')
        else:
            owners=sorted(owner for owner in roles if owner&0xffffffff==slot)
            need(len(owners)>=2 and roles[owners[1]][0][2:4]==wanted,'exact selected service generation fault')
            need(root_counters[roots[0]]==(1,0),'one automatic replacement after the selected service failure')
    if spec['root']==0:need(all(value==(0,0) for value in root_counters.values()),'application and packet faults never consume service restarts')
    packets=read('packets.json');need(packets['closed'] and packets['error'] is None and len(packets['frames'])<=64,'bounded owned peer')
    udp=[]
    for p in packets['frames']:
        tx=bytes.fromhex(p['tx']);expected=packet_replies(tx,name)
        need(p['sent']==[x.hex() for x in expected] and p['rx']==(expected[0].hex() if expected else ''),'exact actual peer behavior')
        if tx[12:14]==b'\x08\0':udp.append(tx)
    need(len(udp)==(1 if name in ('healthy4g','healthy8g','bad-packets','queue-full','stale-grant') else 0),'wire sends only after authorized successful operation')
    if name=='stale-grant':
        need(list(injections.values())==[0,3,8,0],'healthy grant before actual stale epoch and closed handle')
        victim=next(owner for owner,mode in injections.items() if mode==3)
        request=next(q for owner,q in requests if owner==victim and struct.unpack_from('<I',q,80)[0]==3)
        epoch=struct.unpack_from('<Q',request,32)[0]
        need(epoch>0 and any(struct.unpack_from('<Q',g,32)[0]==epoch for owner,g in grants.items() if owner!=victim),'replayed previously issued epoch')
        victim=next(owner for owner,mode in injections.items() if mode==8)
        operations=[(op,result) for owner,op,result in responses if owner==victim]
        need(operations[:4]==[(1,0),(2,0),(5,0),(3,-9)],'close precedes stale handle denial without wire output')
    if name=='queue-full':
        need([count for count,_ in queues]==[0,1,2,3,4,4] and queues[4][1]==queues[5][1],'full queue rejects additional packets without overwrite')
    elif name=='bad-packets':need(len(queues)==1,'all four malformed/foreign packets rejected before enqueue')
    if name=='exhaustion':need(serial.count(b'-11')>=2,'sticky network exhaustion')
    if name=='peer-loss':need(len(roles)==8 and not queues,'packet loss does not restart healthy services')
    exempt={roots[0]} if name=='parent-crash' else set()
    need(all(terminals[owner][2:4]==(0,4) for owner in roots if owner not in exempt),'unrelated root exits normally')
    need(not any(r[2] in (134,256) for owner,r in terminals.items() if owner&0xffffffff in (2,3)),
         'no unrelated filesystem crash or CPU quota fault')
    return dict(name=name,applications=len(apps),services=len(roles),packets=len(packets['frames']),
                udp_sends=len(udp),enqueues=len(queues),cohorts=len(finishes),raw_events=len(extra))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--ram',type=int,choices=(4096,8192),default=4096)
    p.add_argument('--case',choices=CASES)
    a=p.parse_args();print(json.dumps(diagnostic(a.image,a.evidence,a.ram,a.case)))
