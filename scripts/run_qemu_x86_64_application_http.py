"""Bounded ordinary curl capture. A capture alone is not acceptance evidence."""
from pathlib import Path
import argparse,struct,inspect,hashlib
import run_qemu_x86_64_application_dns as dns
import run_qemu_x86_64_application_tcp as tcp
from check_x86_64_wide_shell_media import clone
from run_qemu_x86_64_runtime_clock import once
base=tcp.base
FETCH='curl http://192.0.2.3/'
BODY=b'http-local-peer\n'
CASES=('healthy4g','healthy8g','chunked','fragmented','header-limit','body-limit',
       'bad-header','short-body','peer-loss','denied-operands','wrong-grant',
       'foreign-owner','stale-grant','malformed-ipc','app-crash','app-hang','app-cpu',
       'stack-crash','stack-hang','stack-cpu','driver-crash','driver-hang','driver-cpu',
       'exhaustion','parent-crash')
DENIED=('curl https://192.0.2.3/','curl http://192.0.2.4/',
        'curl http://test.local/','curl http://192.0.2.3:81/',
        'curl -o /file http://192.0.2.3/','curl --max-bytes 513 http://192.0.2.3/')

def specification(name):
    base.need(name in CASES,'frozen HTTP case')
    spec=tcp.specification(name if name in tcp.CASES else 'healthy4g')
    spec['name']=name
    spec['dialogue']=[FETCH if q==tcp.CONNECT else q for q in spec['dialogue']]
    if name not in ('healthy4g','healthy8g'):
        spec['dialogue']=[q for q in spec['dialogue'] if q not in (tcp.udp.SEND,tcp.udp.RECEIVE)]
    else:spec['dialogue'][-1:-1]=[tcp.CONNECT,dns.LOOKUP]
    if name=='wrong-grant':
        spec['dialogue']=[q for q in spec['dialogue'] if not q.startswith('nc ')]
    if name=='denied-operands':spec['dialogue'][2:2]=DENIED
    spec['markers']=[b'Network interface configured.']
    if name!='exhaustion':spec['markers'].append(BODY.rstrip())
    return spec

def response(name):
    """Exact peer bytes; invalid framing is deliberate and case-specific."""
    if name=='chunked':
        return b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'+b'%x\r\n'%len(BODY)+BODY+b'\r\n0\r\n\r\n'
    if name=='header-limit':return b'HTTP/1.1 200 OK\r\nX-Limit: '+b'a'*512+b'\r\nContent-Length: 0\r\n\r\n'
    if name=='body-limit':return b'HTTP/1.1 200 OK\r\nContent-Length: 513\r\n\r\n'+b'a'*513
    if name=='bad-header':return b'HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\nx'
    if name=='short-body':return b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\nshort'
    return b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(BODY)).encode()+b'\r\n\r\n'+BODY

class PeerModel:
    def __init__(self,name):
        self.name=name;self.connections={};self.first_port=None
        self.other=dns.PeerModel('healthy4g');self.frames=tcp.PeerModel('healthy4g')
    def frame(self,tx,port,seq,ack,flags,data=b''):
        raw=bytearray(self.frames.frame(tx,port,seq,ack,flags,data))
        struct.pack_into('>H',raw,34,80);raw[50:52]=b'\0\0'
        pseudo=raw[26:34]+b'\0\x06'+struct.pack('>H',len(raw)-34)
        struct.pack_into('>H',raw,50,base.checksum(pseudo+raw[34:]))
        return bytes(raw)
    def replies(self,tx):
        if tx[12:14]==b'\x08\x06':return self.other.replies(tx)
        base.need(len(tx)>=42,'complete network header')
        destination=struct.unpack_from('>H',tx,36)[0]
        if destination in (53,5000):return self.other.replies(tx)
        base.need(len(tx)>=54 and tx[12:14]==b'\x08\0' and tx[14]==0x45 and tx[23]==6,'HTTP TCP frame')
        length=struct.unpack_from('>H',tx,16)[0]-20;header=(tx[46]>>4)*4
        base.need(20<=header<=length<=536 and length+34<=len(tx),'bounded TCP extent')
        base.need(tx[:12]==bytes.fromhex('525400123457525400123456') and
                  tx[26:34]==bytes([192,0,2,2,192,0,2,3]),'owned HTTP peer')
        pseudo=tx[26:34]+b'\0\x06'+struct.pack('>H',length)
        base.need(base.checksum(tx[14:34])==0 and base.checksum(pseudo+tx[34:34+length])==0,'wire checksums')
        port,destination,seq,ack=struct.unpack_from('>HHII',tx,34)
        base.need(destination==80 and 49152<=port<=65535,'exact HTTP ports')
        if self.first_port is None:self.first_port=port
        mode=self.name if port==self.first_port else 'healthy4g'
        flags=tx[47];data=tx[34+header:34+length]
        if flags==2:
            if mode=='peer-loss':return []
            c=self.connections.setdefault(port,dict(client=(seq+1)&0xffffffff,server=0xfffffff1,
                request=bytearray(),sent=False,fin=False))
            base.need(c['client']==(seq+1)&0xffffffff and not data,'consistent SYN retransmission')
            return [self.frame(tx,port,0xfffffff0,c['client'],18)]
        base.need(port in self.connections,'known HTTP connection');c=self.connections[port]
        if data:
            base.need(flags==24,'HTTP request flags')
            if seq==c['client']:
                base.need(not c['sent'] and len(c['request'])+len(data)<=512,'one bounded request')
                c['request']+=data;c['client']=(seq+len(data))&0xffffffff
            else:
                base.need((seq+len(data))&0xffffffff==c['client'] and bytes(c['request']).endswith(data),'exact retransmitted request')
            result=[self.frame(tx,port,c['server'],c['client'],16)]
            if not c['request'].endswith(b'\r\n\r\n') or c['sent']:return result
            expected=(b'GET / HTTP/1.1\r\nHost: 192.0.2.3\r\nUser-Agent: REIST-curl/1\r\n'
                      b'Accept: */*\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n')
            base.need(bytes(c['request'])==expected,'actual ordinary curl HTTP request')
            payload=response(mode)
            pieces=([payload[:1],payload[1:17],payload[17:]] if mode=='fragmented' else
                    [payload[n:n+512] for n in range(0,len(payload),512)])
            for piece in pieces:
                result.append(self.frame(tx,port,c['server'],c['client'],24,piece))
                c['server']=(c['server']+len(piece))&0xffffffff
            result.append(self.frame(tx,port,c['server'],c['client'],17))
            c['server']=(c['server']+1)&0xffffffff;c['fin']=True;c['sent']=True
            return result
        if flags==17:
            base.need(seq==c['client'],'in-order client FIN');c['client']=(seq+1)&0xffffffff
            result=[self.frame(tx,port,c['server'],c['client'],16)]
            if not c['fin']:
                result.append(self.frame(tx,port,c['server'],c['client'],17))
                c['server']=(c['server']+1)&0xffffffff;c['fin']=True
            return result
        base.need(flags in (16,20),'TCP acknowledgement or abort');return []

selected=clone(tcp,[
    ('build_x86_64_application_tcp_media','build_x86_64_application_http_media'),
    ('check_x86_64_application_tcp_media','check_x86_64_application_http_media'),
    ("'tcp_grant':'tcp_grant'","'tcp_grant':'tcp_grant','session_http_selected':'http_selected'"),
    ("'udp':{'reist_udp_app_selection':'udp_selection'},",
     "'udp':{'reist_udp_app_selection':'udp_selection'},'dns':{'reist_dns_app_selection':'dns_selection'},'http':{'reist_http_app_selection':'http_selection'},"),
    ("'tcp_grant'},'actual TCP observer symbols'",
     "'tcp_grant','dns_selection','http_selection','http_selected'},'actual TCP observer symbols'")
], 'reist_application_http_capture')
# Inspect the root's mapped selector before reading any application marker:
# smaller DNS/UDP images need not map the larger HTTP image's marker address.
observer=dns.selected.TCP_OBSERVER
begin=observer.index("        address,_=CONFIG['tcp_symbols']['app_selection']")
finish=observer.index("        tcp_save('tcp-app-start'",begin)
classification=observer[begin:finish]
observer=once(observer,classification,
    "        selector=user(task(0),*CONFIG['tcp_symbols']['http_selected'])\n"
    "        http=int.from_bytes(selector,'little')==1\n"
    "        if http:\n            dns=False;protocol=6;tcp_set(t,'http_selection',0x3150504150545448,value)\n"
    "        else:\n"+''.join('    '+line+'\n' for line in classification.splitlines()))
observer=once(observer,"'family':mem(S['family_records']+slot*64,64)",
              "'family':mem(S['family_records']+slot*64,64),'http_selected':selector")
observer=once(observer,'protocol=protocol,dns=dns)','protocol=protocol,dns=dns,http=http)')
selected.TCP_OBSERVER=observer;selected.PeerModel=PeerModel;selected.specification=specification

def diagnostic(image,evidence,ram=4096,name=None):
    stack_review(image)
    return selected.diagnostic(image,evidence,ram,name)

def stack_review(image):
    network=dns.stack_review(image);sizes={}
    image=Path(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    base.need(len(folders)==1,'one HTTP stack producer')
    for p in folders[0].rglob('*.su'):
        for row in p.read_text(encoding='utf-8').splitlines():
            label,amount,kind=row.split('\t');source,_,function=label.rsplit(':',2)
            base.need(kind=='static','fixed stack frames')
            sizes[source,function]=max(sizes.get((source,function),0),int(amount))
    sdk='userspace/sdk/lib/x86_64/'
    chain=[(sdk+'application_tcp_platform.c','__wrap_main'),('userspace/programs/curl.c','main'),
        ('userspace/programs/curl.c','receive_response'),('userspace/programs/curl.c','receive_chunked'),
        ('userspace/programs/curl.c','reader_line'),('userspace/programs/curl.c','reader_available'),
        ('userspace/programs/curl.c','plain_receive'),(sdk+'application_tcp_platform.c','x86os_tcp_receive'),
        (sdk+'application_tcp_platform.c','transact'),
        (sdk+'network_session.c','reist_net_copy')]
    base.need(all(k in sizes for k in chain),'all concrete HTTP receive frames')
    bound=sum(sizes[k] for k in chain)+256
    base.need(bound<=8192,'HTTP chunk/IPC stack fits fixed8KiB')
    return dict(network=network,http=dict(bound=bound,limit=8192,frames={s+':'+f:sizes[s,f] for s,f in chain}))

# Reuse accepted raw kernel/CPU/device checks and exact paired transport
# parsers. Each textual substitution is cardinality-checked against source.
_namespace={**vars(tcp),'specification':specification}
exec(compile(dns._prefix+dns._helpers+'    return locals()\n','<http-kernel-review>','exec'),_namespace)
_kernel_review=_namespace['review']
_authority=inspect.getsource(dns.review)
_authority=_authority[:_authority.index('    dns_apps=')]
_authority=once(_authority,"'dns_selection':0x31505041534e4452}",
    "'dns_selection':0x31505041534e4452,'http_selection':0x3150504150545448}")
_authority=once(_authority,"index=sum(t=='dns_selection' for t,v in injections.values())",
    "index=sum(t=='http_selection' for t,v in injections.values())")
_authority=once(_authority,"target=='dns_selection' and index<len(spec['app'])",
    "target=='http_selection' and index<len(spec['app'])")
_authority=once(_authority,"            if e['dns']:need(",
    "            need(type(e['http']) is bool and int.from_bytes(raw(e,'http_selected',c['config']['tcp_symbols']['http_selected'][1]),'little')==int(e['http']),'raw root HTTP selector')\n"
    "            if e['http']:need(not e['dns'] and e['protocol']==6 and injections.get(owner,(None,))[0]=='http_selection','actual curl fixture identity')\n"
    "            elif e['dns']:need(")
_authority=once(_authority,'53 if dns else 5000,0)',
    "53 if dns else (struct.unpack_from('<H',g,58)[0] if protocol==6 else 5000),0)")
_authority=once(_authority,"                need(app not in grants",
    "                need(struct.unpack_from('<H',g,58)[0] in ((53,) if dns else (80,5000) if protocol==6 else (5000,)),'bounded service destination')\n"
    "                need(app not in grants")
_authority_namespace={**vars(dns),'_kernel_review':_kernel_review}
exec(compile(_authority+'    return locals()\n','<http-authority-review>','exec'),_authority_namespace)
_authority_review=_authority_namespace['review']

def review(image,folder,name):
    a=_authority_review(image,folder,name);c=a['c'];need=base.need
    apps=a['apps'];grants=a['grants'];responses=a['responses'];requests=a['requests']
    terminals=a['terminals'];injections=a['injections'];u32=a['u32'];u64=a['u64'];raw=a['raw']
    http_apps=[o for o,e in apps.items() if e['http']]
    need(http_apps,'actual ordinary curl launch')
    for owner,e in apps.items():
        need(owner in grants,'issued grant before app request');g,paired=grants[owner]
        need(paired==e['dns'] and struct.unpack_from('<H',g,58)[0]==(80 if e['http'] else 53 if e['dns'] else 5000),'application identity and exact peer port')
    for owner in http_apps:
        fault=injections[owner][1];terminal=terminals[owner][2:4]
        if fault in (5,6,7):need(terminal=={5:(134,3),6:(0,3),7:(256,3)}[fault],'exact HTTP app fault')
        if terminal==(0,4):need(owner in a['released'],'successful HTTP release acknowledged')
        if fault in (1,2,3,4):
            q=next(q for o,q in requests if o==owner and u32(q,80)==3)
            g,_=grants[owner];expected=bytearray(g)
            if fault==1:struct.pack_into('<I',expected,52,u32(g,52)+1)
            if fault==2:struct.pack_into('<Q',expected,16,u64(g,16)+(1<<32))
            if fault==3:
                struct.pack_into('<Q',expected,32,u64(g,32)-1)
                need(any(o!=owner and u64(old,32)==u64(expected,32) for o,(old,_) in grants.items()),'previous issued epoch replay')
            if fault==4:struct.pack_into('<I',expected,60,1)
            need(q[:64]==bytes(expected) and terminal!=(0,4),'exact rejected HTTP grant mutation')
        if fault==8:
            need(any(o==owner and op==3 and status==-9 for o,p,op,status,r in responses),'retired TCP handle denied')
    if name!='exhaustion':need(terminals[http_apps[-1]][2:4]==(0,4),'fresh healthy HTTP after fault')
    if name in ('header-limit','body-limit','bad-header','short-body','peer-loss','wrong-grant','foreign-owner','malformed-ipc'):
        need(terminals[http_apps[0]][2:4]!=(0,4),'invalid/incomplete response cannot succeed')
    spec=c['spec'];roots=c['roots'];roles=c['roles'];counters=a['counters']
    if not spec['root']:need(all(v==(0,0) for v in counters.values()),'application faults do not restart services')
    if spec['root'] in range(1,8):
        slot=4 if spec['root'] in (1,2,3,7) else 5
        wanted={1:(134,3),2:(0,3),3:(256,3),4:(134,3),5:(0,3),6:(256,3),7:(134,3)}[spec['root']]
        victims=[r for o,(r,_) in roles.items() if o&0xffffffff==slot and r[2:4]==wanted]
        if wanted!=(0,3):need(len(victims)==(3 if name=='exhaustion' else 1),'exact service fault count')
        if name!='exhaustion':
            owners=sorted(o for o in roles if o&0xffffffff==slot)
            need(len(owners)>=2 and roles[owners[1]][0][2:4]==wanted,'selected service generation fault')
            if name=='stack-hang':
                event=next(e for e in c['snapshots'] if e['kind']=='terminal' and e['slot']==5 and u32(raw(e,'receipt'),4)==owners[1]>>32)
                control=raw(event,'control',1600)
                need(struct.unpack_from('<2I',control,8)==(14,608) and u32(control,144)==2,'hung HTTP stack CONNECT')
        need(counters[roots[0]]==((2,1) if name=='exhaustion' else (1,0)),'exact replacement/exhaustion count')
    packets=c['read']('packets.json');need(packets['closed'] and packets['error'] is None and len(packets['frames'])<=64,'closed bounded peer')
    peer=PeerModel(name);transmissions=[]
    for row in packets['frames']:
        tx=bytes.fromhex(row['tx']);expected=peer.replies(tx)
        need(row['sent']==[p.hex() for p in expected] and row['rx']==(expected[0].hex() if expected else ''),'independent exact HTTP peer replay')
        transmissions.append(tx)
    need([tx.ljust(60,b'\0') for _,tx,_ in a['wire']]==transmissions,'physical TX matches Ring3 payload')
    for owner in http_apps:
        mode=name if owner==http_apps[0] else 'healthy4g'
        stream=b''.join(r[96:96+u32(r,88)] for o,p,op,status,r in responses if o==owner and p==6 and op==4 and not status)
        expected=response(mode);need(expected.startswith(stream),'exact ordered HTTP SDK bytes')
        if terminals[owner][2:4]==(0,4):need(stream==expected,'complete HTTP framing before success')
    if name in ('healthy4g','healthy8g'):
        need(sum(e['http'] for e in apps.values())==2 and sum(e['dns'] for e in apps.values())==1 and
             sum(not e['http'] and not e['dns'] and e['protocol']==6 for e in apps.values())==1 and
             sum(not e['dns'] and e['protocol']==17 for e in apps.values())==2,'retained UDP/TCP/DNS coexistence')
        need(all(terminals[o][2:4]==(0,4) for o in apps),'all ordinary commands succeed')
        for owner,e in apps.items():
            if e['dns']:
                queries=[q[96:96+u32(q,88)] for o,q in requests if o==owner and u32(q,48)==17 and u32(q,80)==3]
                delivered=[r[96:96+u32(r,88)] for o,p,op,status,r in responses if o==owner and p==17 and op==4 and not status]
                need(len(queries)==1 and delivered==[dns.answer(queries[0],'healthy4g')],'retained exact DNS response')
                need(not any(o==owner and p==6 for o,p,op,status,r in responses),'direct DNS datagram resolution')
            elif not e['http'] and e['protocol']==6:
                delivered=b''.join(r[96:96+u32(r,88)] for o,p,op,status,r in responses if o==owner and op==4 and not status)
                need(delivered==b'tcp-local-peer','retained ordinary nc response')
    if name=='denied-operands':need(len(apps)==2,'denied operands launch no application')
    exempt={roots[0]} if name=='parent-crash' else set()
    need(all(terminals[o][2:4]==(0,4) for o in roots if o not in exempt),'unrelated root exits normally')
    need(not any(r[2] in (134,256) for o,r in terminals.items() if o&0xffffffff in (2,3)),'unrelated filesystem remains healthy')
    return dict(name=name,applications=len(apps),http=len(http_apps),services=len(roles),packets=len(transmissions),raw_events=len(c['extra']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--case',choices=CASES,default='healthy4g')
    a=p.parse_args();print(diagnostic(a.image,a.evidence,name=a.case))
