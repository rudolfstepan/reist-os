"""Bounded DNS development capture. Capture alone is not acceptance evidence."""
from pathlib import Path
import argparse,struct,inspect,json,hashlib
import run_qemu_x86_64_application_tcp as tcp
from check_x86_64_wide_shell_media import clone
from run_qemu_x86_64_runtime_clock import once
base=tcp.base
CASES=('healthy4g','healthy8g','cname','truncated','udp-loss','wrong-question',
       'bad-compression','peer-loss','tcp-fragmented','frame-limit',
       'wrong-grant','foreign-owner','stale-grant','malformed-ipc',
       'app-crash','app-hang','app-cpu','stack-crash','stack-hang','stack-cpu',
       'driver-crash','driver-hang','driver-cpu','exhaustion','parent-crash')
LOOKUP='nslookup test.local'

def specification(name):
    base.need(name in CASES,'frozen DNS case')
    spec=tcp.specification(name if name in tcp.CASES else 'healthy4g')
    spec['name']=name
    spec['dialogue']=[LOOKUP if q==tcp.CONNECT else q for q in spec['dialogue']]
    if name in ('healthy4g','healthy8g'):spec['dialogue'].insert(-1,tcp.CONNECT)
    if name=='wrong-grant':
        spec['dialogue']=[q.replace('nc example 5000 hello','nslookup test.local 192.0.2.4').replace(
            'nc 192.0.2.4 5000 hello','nslookup test.local 0.0.0.0') for q in spec['dialogue']]
    spec['markers']=[b'Network interface configured.']
    if name not in ('exhaustion','peer-loss','wrong-question','bad-compression','frame-limit'):
        spec['markers'].append(b'address: 192.0.2.3')
    return spec

def answer(query,name):
    base.need(17<=len(query)<=512 and query[2:12]==b'\x01\0\0\x01\0\0\0\0\0\0','bounded standard query')
    at=12
    for _ in range(128):
        size=query[at];at+=1
        if not size:break
        base.need(size<=63 and at+size<len(query),'query label');at+=size
    base.need(at+4==len(query) and query[at:]==b'\0\x01\0\x01','exact A/IN question')
    result=bytearray(query);result[2:4]=b'\x81\x80';result[6:8]=b'\0\x01'
    if name=='wrong-question':result[13]^=1
    record=b'\xc0\x0c\0\x01\0\x01\0\0\0\x3c\0\x04\xc0\0\x02\x03'
    if name=='cname':
        target=b'\x05alias\x05local\0';result[6:8]=b'\0\x02'
        result+=b'\xc0\x0c\0\x05\0\x01\0\0\0\x1e'+struct.pack('>H',len(target))+target
        result+=target+record[2:]
    else:result+=record
    if name=='bad-compression':result[len(query):len(query)+2]=b'\xff\xff'
    return bytes(result)

class PeerModel:
    def __init__(self,name):self.name=name;self.connections={};self.ordinary=tcp.PeerModel('healthy4g');self.first_port=None
    def frame(self,tx,port,seq,ack,flags,data=b''):
        raw=bytearray(self.ordinary.frame(tx,port,seq,ack,flags,data))
        struct.pack_into('>H',raw,34,53);raw[50:52]=b'\0\0'
        pseudo=raw[26:34]+b'\0\x06'+struct.pack('>H',len(raw)-34)
        struct.pack_into('>H',raw,50,base.checksum(pseudo+raw[34:]))
        return bytes(raw)
    def replies(self,tx):
        if tx[12:14]==b'\x08\x06':return tcp.udp.packet_replies(tx)
        base.need(len(tx)>=42 and tx[12:14]==b'\x08\0' and tx[14]==0x45,'IPv4 frame')
        total=struct.unpack_from('>H',tx,16)[0]
        base.need(total+14<=len(tx) and base.checksum(tx[14:34])==0,'IPv4 length/checksum')
        base.need(tx[:12]==bytes.fromhex('525400123457525400123456') and
                  tx[26:34]==bytes([192,0,2,2,192,0,2,3]),'owned local peer tuple')
        port,destination=struct.unpack_from('>HH',tx,34)
        if destination==5000:return self.ordinary.replies(tx)
        base.need(destination==53 and 49152<=port<=65535,'DNS grant ports')
        if self.first_port is None:self.first_port=port
        name=self.name
        if name in ('peer-loss','wrong-question','bad-compression','frame-limit') and port!=self.first_port:name='healthy4g'
        protocol=tx[23];length=total-20
        base.need(protocol in (6,17) and length>=8,'DNS transport')
        pseudo=tx[26:34]+bytes([0,protocol])+struct.pack('>H',length)
        base.need(base.checksum(pseudo+tx[34:34+length])==0,'transport checksum')
        if protocol==17:
            base.need(length==struct.unpack_from('>H',tx,38)[0] and length<=520,'UDP extent')
            query=tx[42:34+length]
            if name in ('udp-loss','peer-loss'):return []
            payload=answer(query,name)
            if name in ('truncated','tcp-fragmented','frame-limit'):
                payload=bytearray(query);payload[2:4]=b'\x83\x80'
            raw=bytearray(42+len(payload));raw[:34]=tx[:34]
            raw[:12]=tx[6:12]+tx[:6];raw[26:34]=tx[30:34]+tx[26:30]
            struct.pack_into('>H',raw,16,len(raw)-14);raw[24:26]=b'\0\0'
            struct.pack_into('>H',raw,24,base.checksum(raw[14:34]))
            struct.pack_into('>4H',raw,34,53,port,8+len(payload),0);raw[42:]=payload
            pseudo=raw[26:34]+b'\0\x11'+struct.pack('>H',len(raw)-34)
            struct.pack_into('>H',raw,40,base.checksum(pseudo+raw[34:]) or 65535)
            return [bytes(raw)]
        base.need(length>=20,'TCP header');header=(tx[46]>>4)*4
        base.need(20<=header<=length<=536,'TCP extent')
        seq,ack=struct.unpack_from('>II',tx,38);flags=tx[47];data=tx[34+header:34+length]
        if flags==2:
            if name=='peer-loss':return []
            c=self.connections.setdefault(port,dict(client=(seq+1)&0xffffffff,server=0xfffffff1,query=bytearray(),sent=False))
            return [self.frame(tx,port,c['server']-1,c['client'],18)]
        base.need(port in self.connections,'known TCP connection');c=self.connections[port]
        if data:
            base.need(flags==24,'TCP query flags')
            if seq==c['client']:
                base.need(len(c['query'])+len(data)<=514,'bounded TCP query')
                c['query']+=data;c['client']=(seq+len(data))&0xffffffff
            result=[self.frame(tx,port,c['server'],c['client'],16)]
            if len(c['query'])<2 or c['sent']:return result
            size=struct.unpack_from('>H',c['query'])[0];base.need(size<=512,'query framing')
            if len(c['query'])<size+2:return result
            base.need(len(c['query'])==size+2,'one exact DNS query')
            payload=answer(bytes(c['query'][2:]),name)
            payload=struct.pack('>H',513 if name=='frame-limit' else len(payload))+payload
            pieces=[payload[:1],payload[1:3],payload[3:]] if name=='tcp-fragmented' else [payload]
            for part in pieces:
                result.append(self.frame(tx,port,c['server'],c['client'],24,part))
                c['server']=(c['server']+len(part))&0xffffffff
            c['sent']=True;return result
        if flags==17:
            c['client']=(seq+1)&0xffffffff
            result=[self.frame(tx,port,c['server'],c['client'],17)]
            c['server']=(c['server']+1)&0xffffffff;return result
        base.need(flags in (16,20),'TCP ACK or abort');return []

selected=clone(tcp,[
    ('build_x86_64_application_tcp_media','build_x86_64_application_dns_media'),
    ('check_x86_64_application_tcp_media','check_x86_64_application_dns_media'),
    ("'udp':{'reist_udp_app_selection':'udp_selection'},",
     "'udp':{'reist_udp_app_selection':'udp_selection'},'dns':{'reist_dns_app_selection':'dns_selection'},"),
    ("'tcp_grant'},'actual TCP observer symbols'","'tcp_grant','dns_selection'},'actual TCP observer symbols'")
], 'reist_application_dns_capture')
observer=selected.TCP_OBSERVER
observer=once(observer,"        if protocol==6:tcp_set(t,'app_selection',0x3150504150435452,value)",
    "        ua,_=CONFIG['tcp_symbols']['udp_selection']\n"
    "        ordinary_udp=user(t,ua,16)==struct.pack('<2Q',0x3150504144505552,0)\n"
    "        dns=False\n"
    "        if protocol!=6 and not ordinary_udp:\n"
    "            da,_=CONFIG['tcp_symbols']['dns_selection']\n"
    "            dns=user(t,da,16)==struct.pack('<2Q',0x31505041534e4452,0)\n"
    "        if dns:\n            protocol=17;tcp_set(t,'dns_selection',0x31505041534e4452,value)\n"
    "        elif protocol==6:tcp_set(t,'app_selection',0x3150504150435452,value)")
observer=once(observer,'parent=task(0)[1]<<32,protocol=protocol)','parent=task(0)[1]<<32,protocol=protocol,dns=dns)')
observer=once(observer,'operation not in (10,11,12,13,14,15)','operation not in (10,11,12,13,14,15,16,17)')
observer=once(observer,"'control':control,","'control':control,'udp_state':user(t,*CONFIG['tcp_symbols']['udp_applications']),")
observer=once(observer,"'udp_state':user(t,*CONFIG['tcp_symbols']['udp_applications']),",
              "'udp_state':user(t,*CONFIG['tcp_symbols']['udp_applications']),'tcp_state':user(t,*CONFIG['tcp_symbols']['applications']),")
selected.TCP_OBSERVER=observer
selected.PeerModel=PeerModel
selected.specification=specification

def stack_review(image):
    """Conservative nested ARP/RX/IPC call-chain bound from compiler output."""
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    base.need(len(folders)==1,'exact stack-usage producer');sizes={};inputs={}
    for p in folders[0].rglob('*.su'):
        inputs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
        for line in p.read_text(encoding='utf-8').splitlines():
            label,amount,kind=line.split('\t');source,_,function=label.rsplit(':',2)
            base.need(kind=='static','no dynamic stack usage')
            sizes[source,function]=max(sizes.get((source,function),0),int(amount))
    prefix='userspace/sdk/lib/x86_64/'
    chain=[('userspace/programs/native_netstack.c','main'),
        (prefix+'application_udp_protocol.c','reist_app_udp_exchange'),
        (prefix+'application_udp_protocol.c','packet_operation'),
        (prefix+'network_protocol.c','reist_net_protocol_control'),
        (prefix+'application_udp_protocol.c','receive_frame'),
        ('userspace/programs/native_netstack.c','receive_frame'),
        ('userspace/programs/native_netstack.c','exchange'),
        ('userspace/programs/native_netstack.c','report'),
        (prefix+'network_session.c','reist_net_receive'),
        (prefix+'network_session.c','reist_net_encode'),
        (prefix+'network_session.c','reist_net_copy')]
    base.need(all(k in sizes for k in chain),'all concrete call-chain frames')
    bound=sum(sizes[k] for k in chain)+256
    base.need(bound<=8192,'ARP/IPC stack plus ABI margin fits existing8KiB')
    return dict(bound=bound,limit=8192,frames={s+':'+f:sizes[s,f] for s,f in chain},inputs=inputs)

def diagnostic(image,evidence,ram=4096,name=None):
    stack_review(image)
    return selected.diagnostic(image,evidence,ram,name)

# Reuse the complete accepted kernel/device/family/CPU/frame reviewer and
# its capability/table parsers verbatim. DNS-specific authority and packets
# are reviewed below, independently of the live debugger/controller.
_source=inspect.getsource(tcp.review)
_prefix=_source[:_source.index('    apps={};')]
_helpers=_source[_source.index('    wanted_mask='):_source.index('    for e in extra:')]
_namespace={**vars(tcp),'specification':specification}
exec(compile(_prefix+_helpers+'    return locals()\n','<dns-kernel-review>','exec'),_namespace)
_kernel_review=_namespace['review']

def review(image,folder,name):
    c=_kernel_review(image,folder,name);need=base.need;raw=c['raw'];table=c['table'];caps=c['capabilities']
    roots=c['roots'];terminals=c['terminals'];spec=c['spec'];roles=c['roles'];snapshots=c['snapshots']
    apps={};grants={};injections={};requests=[];responses=[];sequences={};forwarded=set()
    counters={};wire=[];finishes=0;epochs={};released=set()
    u32=lambda b,at:struct.unpack_from('<I',b,at)[0]
    u64=lambda b,at:struct.unpack_from('<Q',b,at)[0]
    def normalized(g):
        b=bytearray(g);struct.pack_into('<I',b,48,17);return bytes(b)
    def tables(e):
        t=raw(e,'tcp_state',9432);u=raw(e,'udp_state',17360);table(t,6);table(u,17)
        return t,u
    def scrubbed(t,u):
        return not u32(t,48) and not any(t[56:]) and not u32(u,40) and not any(u[48:])
    for e in c['extra']:
        kind=e['kind'];owner=e['owner']
        if kind=='tcp-injection':
            target=e['target'];value=e['value'];magic={'root_selection':0x31544f4f52544352,
                'app_selection':0x3150504150435452,'dns_selection':0x31505041534e4452}
            need(target in magic and raw(e,'before',16)==struct.pack('<2Q',magic[target],0),'exact private injection')
            if target=='root_selection':need(owner in roots and value==(spec['root'] if owner==roots[0] else 0),'selected root only')
            else:
                index=sum(t=='dns_selection' for t,v in injections.values())
                expected=spec['app'][index] if target=='dns_selection' and index<len(spec['app']) else 0
                need(owner not in injections and value==expected,'exact app injection order');injections[owner]=(target,value)
        elif kind=='tcp-app-start':
            profile=struct.unpack('<4Q',raw(e,'profile',32));family=struct.unpack('<8Q',raw(e,'family',64))
            need(owner&0xffffffff==6 and profile==(owner>>32,c['wanted_mask'],1<<63,0) and
                family[:2]==(owner,e['parent']) and e['parent'] in roots,'exact attenuated app profile')
            need(e['protocol'] in (6,17) and type(e['dns']) is bool,'explicit app kind')
            if e['dns']:need(injections.get(owner,(None,))[0]=='dns_selection','DNS fixture identity')
            elif e['protocol']==6:need(injections.get(owner)==('app_selection',0),'ordinary TCP fixture')
            else:need(owner not in injections,'ordinary UDP has no injected fault')
            apps[owner]=e
        elif kind=='tcp-request':
            need(owner in apps,'entered request owner');a=apps[owner];rights=caps(e,owner,a['parent'])
            need((e['endpoint'],1) in [(h,r) for h,r,s in rights] and 0<e['timeout']<=100,'root directional request channel')
            message=raw(e,'request',2060)
            need(struct.unpack_from('<3I',message)==(2,2060,608) and not any(message[620:]),'canonical request extent')
            q=message[12:620];protocol=u32(q,48)
            need(protocol in ((6,17) if a['dns'] else (a['protocol'],)),'bounded protocol selector')
            previous=sum(o==owner and u32(r,80)!=0 for o,r in requests)
            need(u64(q,64)==(previous+1 if u32(q,80) else 0),'single public request sequence')
            need(previous<64 and e['ms']<u64(q,72)<=e['ms']+2000,'request count/deadline')
            requests.append((owner,q))
        elif kind=='tcp-response':
            m=raw(e,'message',1600);control=raw(e,'control',1600);t,u=tables(e);op=u32(control,8)
            need(struct.unpack_from('<3I',m)==(1,1600,4) and u64(m,32)==owner and not any(m[52:64]),'canonical service reply')
            need(struct.unpack_from('<2I',control)==(1,1600) and m[16:24]==control[16:24] and not any(control[48:64]),'control correlation')
            length=u32(m,12);result=struct.unpack_from('<i',m,48)[0]
            need(length in (0,608) and not any(m[64+length:]) and result==0,'successful bounded service transport')
            ds=c['device'](raw(e,'device',384));parent=u64(control,32)
            need(u64(t,0)==u64(u,0)==parent and u64(t,8)==u64(u,8)==owner and
                ds[0]==((owner>>32)-1)<<32|4 and ds[1]==parent,'paired service/device generation')
            if op in (10,13,16):
                g=control[64:128];root,app,service,epoch,expires=struct.unpack_from('<5Q',g,8)
                dns=op==16;protocol=6 if op==13 else 17;port=49152+4*((app>>32)-1) if op!=10 else 4000
                need(not length and root in roots and service==owner and app&0xffffffff==6 and
                    struct.unpack_from('<2I',g)==(1,64) and e['ms']<expires<=e['ms']+6000 and
                    struct.unpack_from('<IIHHI',g,48)==(protocol,0xc0000203,port,53 if dns else 5000,0),'bounded exact grant')
                need(app not in grants and epoch>epochs.get((root,op),0),'fresh application/epoch')
                if op!=10:need(1<=app>>32<=4096,'unique finite port allocation')
                if dns:
                    need(u32(t,48)==u32(u,40)==1 and u32(t,104)==6 and u32(u,96)==17 and
                         normalized(t[56:120])==u[48:112]==g,'atomic paired grant before ACK')
                else:
                    v,offset=(t,56) if protocol==6 else (u,48)
                    need(u32(v,48 if protocol==6 else 40)==1 and v[offset:offset+64]==g,'ordinary grant retained')
                grants[app]=(g,dns);epochs[root,op]=epoch
            elif op in (12,15,17):
                need(not length,'revoke ACK has no payload')
                if op==17:need(scrubbed(t,u),'paired revoke scrubs both transports')
                else:
                    v,active,start=(u,40,48) if op==12 else (t,48,56)
                    need(not u32(v,active) and not any(v[start:]),'ordinary revoke cleanup')
            else:
                need(op in (11,14) and length==608,'object response operation')
                q=control[64:672];r=m[64:672];app=u64(q,16);protocol=17 if op==11 else 6
                need(app in grants and u32(q,48)==protocol,'current object owner/protocol');g,dns=grants[app]
                need((normalized(q[:64])==g if dns else q[:64]==g),'exact current grant')
                key=app,protocol;sequences[key]=sequences.get(key,0)+1
                need(u64(q,64)==sequences[key],'separate transport sequence')
                matches=[i for i,(o,p) in enumerate(requests) if o==app and i not in forwarded and p[:64]+p[72:]==q[:64]+q[72:]]
                need(len(matches)==1,'exact forwarded public request');forwarded.add(matches[0])
                operation,handle,amount,status=struct.unpack_from('<IIIi',r,80)
                need(r[:84]==q[:84] and (operation==1 or r[84:88]==q[84:88]) and -4095<=status<=0 and amount<=512,'exact bounded object response')
                used=amount if not status and operation in (4,7) else 0
                need(not any(r[96+used:]),'scrubbed response payload tail')
                caps(e,app,u64(q,8));responses.append((app,protocol,operation,status,r))
                if dns:need(sum(u32(u,720+n*2080)!=0 for n in range(8))<=4,'four live DNS UDP objects')
                if operation==6 and not status:
                    if dns:need(scrubbed(t,u),'paired release scrubs both before ACK')
                    released.add(app)
                elif protocol==6:need(not any(t[120:728]),'no pending TCP operation after response')
                else:need(not any(u[112:720]),'no pending UDP operation after response')
        elif kind in ('tcp-exchange','tcp-wire'):
            v=raw(e,'applications',9432);table(v,6)
            if kind=='tcp-exchange':need(raw(e,'request',608)[:64]==v[56:120],'current TCP exchange grant')
            else:
                m=raw(e,'message',1600);length=u32(m,12)
                need(struct.unpack_from('<3I',m)==(1,1600,5) and 14<=length<=1514 and not any(m[64+length:]),'exact raw TX')
                wire.append((e['ms'],m[64:64+length],v))
        elif kind=='tcp-root-terminal':
            need(owner in roots and owner not in counters,'one root lifecycle snapshot')
            value=tuple(int.from_bytes(raw(e,k,c['config']['tcp_symbols'][k][1]),'little') for k in ('network_restarts','network_blocked'))
            need(value[0]<=2 and value[1]<=1,'fixed recovery budget');counters[owner]=value
            if name!='parent-crash' or owner!=roots[0]:need(not any(raw(e,'tcp_grant',64)),'no root grant at exit')
        else:
            need(kind=='tcp-finish' and owner==0 and not any(raw(e,'capabilities',2048)),'final capability scrub')
            need(all(raw(e,'endpoints',43648)[n*2728]==0 for n in range(16)),'final endpoints retired');finishes+=1
    need(finishes==spec['cohorts'] and set(counters)==set(roots) and all(o in terminals for o in apps),'all lifecycles complete')
    dns_apps=[o for o,a in apps.items() if a['dns']]
    need(len(dns_apps)>=1,'real DNS apps')
    for o in dns_apps:
        fault=injections[o][1]
        if fault in (5,6,7):need(terminals[o][2:4]=={5:(134,3),6:(0,3),7:(256,3)}[fault],'exact app fault')
        if terminals[o][2:4]==(0,4):need(o in released,'successful app acknowledged paired release')
    if name!='exhaustion':need(terminals[dns_apps[-1]][2:4]==(0,4),'fresh healthy DNS progress')
    if name in ('peer-loss','wrong-question','bad-compression','frame-limit','wrong-grant','foreign-owner','malformed-ipc'):
        need(terminals[dns_apps[0]][2:4]!=(0,4),'selected invalid/lost input cannot resolve successfully')
    for o in dns_apps:
        fault=injections[o][1]
        if fault in (1,2,3,4):
            q=next(q for a,q in requests if a==o and u32(q,80)==3)
            g,_=grants[o];expected=bytearray(g)
            if fault==1:struct.pack_into('<I',expected,52,u32(g,52)+1)
            if fault==2:struct.pack_into('<Q',expected,16,u64(g,16)+(1<<32))
            if fault==3:
                struct.pack_into('<Q',expected,32,u64(g,32)-1)
                need(any(a!=o and u64(old,32)==u64(expected,32) for a,(old,_) in grants.items()),'previously issued epoch replay')
            if fault==4:struct.pack_into('<I',expected,60,1)
            need(q[:64]==bytes(expected) and terminals[o][2:4]!=(0,4),'exact grant mutation rejected')
        if fault==8:
            need([(op,status) for a,p,op,status,r in responses if a==o and p==17][:4]==[(1,0),(2,0),(5,0),(3,-9)],'retired UDP handle rejected before TX')
    if spec['root']==0:need(all(v==(0,0) for v in counters.values()),'app/packet failures do not restart services')
    if spec['root'] in range(1,8):
        slot=4 if spec['root'] in (1,2,3,7) else 5
        wanted={1:(134,3),2:(0,3),3:(256,3),4:(134,3),5:(0,3),6:(256,3),7:(134,3)}[spec['root']]
        victims=[r for o,(r,_) in roles.items() if o&0xffffffff==slot and r[2:4]==wanted]
        if wanted!=(0,3):need(len(victims)==(3 if name=='exhaustion' else 1),'exact selected service fault count')
        if name!='exhaustion':
            owners=sorted(o for o in roles if o&0xffffffff==slot)
            need(len(owners)>=2 and roles[owners[1]][0][2:4]==wanted,'exact selected service generation')
            if name=='stack-hang':
                e=next(e for e in snapshots if e['kind']=='terminal' and e['slot']==5 and u32(raw(e,'receipt'),4)==owners[1]>>32)
                control=raw(e,'control',1600)
                need(struct.unpack_from('<2I',control,8)==(11,608) and u32(control,144)==3,'hung DNS stack SEND')
        need(counters[roots[0]]==((2,1) if name=='exhaustion' else (1,0)),'exact replacement/exhaustion count')
    packets=c['read']('packets.json');need(packets['closed'] and packets['error'] is None and len(packets['frames'])<=64,'closed bounded peer')
    peer=PeerModel(name);transmissions=[]
    for row in packets['frames']:
        tx=bytes.fromhex(row['tx']);expected=peer.replies(tx)
        need(row['sent']==[p.hex() for p in expected] and row['rx']==(expected[0].hex() if expected else ''),'independent exact peer replay')
        transmissions.append(tx)
    need([tx.ljust(60,b'\0') for _,tx,_ in wire]==transmissions,'all physical TX matches Ring3 bytes/padding')
    for o in dns_apps:
        good=[r for a,p,op,status,r in responses if a==o and p==17 and op==4 and not status]
        queries=[q[96:96+u32(q,88)] for a,q in requests if a==o and u32(q,48)==17 and u32(q,80)==3]
        mode=name
        if mode in ('peer-loss','wrong-question','bad-compression','frame-limit') and o!=dns_apps[0]:mode='healthy4g'
        if queries:
            need(len(queries)==1,'one bounded UDP DNS query per app');payload=answer(queries[0],mode)
            udp_payload=payload
            if mode in ('truncated','tcp-fragmented','frame-limit'):
                b=bytearray(queries[0]);b[2:4]=b'\x83\x80';udp_payload=bytes(b)
            for r in good:need(u32(r,88)==len(udp_payload) and r[96:96+len(udp_payload)]==udp_payload,'exact peer DNS datagram delivered to app')
            stream=b''.join(r[96:96+u32(r,88)] for a,p,op,status,r in responses if a==o and p==6 and op==4 and not status)
            expected=struct.pack('>H',513 if mode=='frame-limit' else len(payload))+payload
            need(expected.startswith(stream),'exact ordered TCP DNS bytes')
            if any(a==o and p==6 and op==2 and not status for a,p,op,status,r in responses) and terminals[o][2:4]==(0,4):
                need(stream==expected,'complete TCP DNS result before successful exit')
        if name in ('healthy4g','healthy8g','cname'):
            need(len(good)==1 and not any(a==o and p==6 for a,p,op,status,r in responses),'direct UDP, no concealed TCP fallback')
        if name in ('truncated','tcp-fragmented'):
            need(len(good)==1 and good[0][98]&2 and any(a==o and p==6 and op==2 and not status for a,p,op,status,r in responses),'actual TC response before TCP fallback')
        if name=='udp-loss':need(any(a==o and p==17 and op==4 and status==-110 for a,p,op,status,r in responses),'actual UDP timeout')
    if name in ('healthy4g','healthy8g'):
        need(sum(not a['dns'] and a['protocol']==17 for a in apps.values())==2 and
             sum(not a['dns'] and a['protocol']==6 for a in apps.values())==1,'ordinary UDP/TCP coexistence')
    exempt={roots[0]} if name=='parent-crash' else set()
    need(all(terminals[o][2:4]==(0,4) for o in roots if o not in exempt),'unrelated root exits normally')
    need(not any(r[2] in (134,256) for o,r in terminals.items() if o&0xffffffff in (2,3)),'no unrelated filesystem crash/quota fault')
    return dict(name=name,applications=len(apps),dns=len(dns_apps),services=len(roles),packets=len(transmissions),
                cohorts=len(c['finishes']),raw_events=len(c['extra']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--case',choices=CASES,default='healthy4g')
    a=p.parse_args();print(diagnostic(a.image,a.evidence,name=a.case))
