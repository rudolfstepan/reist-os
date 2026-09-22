"""Actual native DNS implementation tests, bounded C behavior at O0/O2."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig

class ApplicationDNS(unittest.TestCase):
    def host(self,name,entry,sources,flags=(),source=None):
        folder=ROOT/'build/codex-agent/r83bp-application-dns'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True);env=os.environ.copy()
        if source is not None:
            entry=str(folder/(name+'.c'));Path(entry).write_text(source,encoding='utf-8')
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/(name+'-O'+opt+'.exe')
            cmd=[str(find_zig()),'cc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','-UNDEBUG','-Iuserspace/sdk/include',*flags,entry,*sources,'-o',str(exe)]
            p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=120)
            (folder/('compile-O'+opt+'.log')).write_bytes(p.stdout+p.stderr)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-1800:])
            p=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=30)
            (folder/('run-O'+opt+'.log')).write_bytes(p.stdout+p.stderr)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-1800:])
    def test_resolver(self):
        self.host('resolver','test/x86_64_application_dns_host.c',['userspace/sdk/reist_dns.c'])
    def test_paired_authority(self):
        self.host('pair','test/x86_64_application_dns_host.c',[
            'userspace/sdk/lib/x86_64/application_dns.c','userspace/sdk/lib/x86_64/application_udp.c',
            'userspace/sdk/lib/x86_64/application_tcp.c','userspace/sdk/lib/x86_64/network_session.c'],['-DREIST_DNS_CORE_TEST'])
    def test_retained_packet_validation(self):
        self.host('parser','test/test_dns_response_validation.c',['userspace/sdk/reist_dns.c'])
    def test_platform(self):
        self.host('platform','test/x86_64_application_dns_platform_host.c',[
            'userspace/sdk/lib/x86_64/application_tcp_platform.c',
            'userspace/sdk/lib/x86_64/application_dns.c','userspace/sdk/lib/x86_64/application_udp.c',
            'userspace/sdk/lib/x86_64/application_tcp.c','userspace/sdk/lib/x86_64/network_session.c'],
            ['-DREIST_APP_TCP_HOST_TEST','-DREIST_NATIVE_APP_DNS','-DREIST_NATIVE_APP_TCP'])
    def test_media_geometry_and_corruption(self):
        import build_x86_64_application_dns_media as producer
        import check_x86_64_application_dns_media as consumer
        files={name:bytes([n+1])*(14000 if name.endswith('.prg') else 17)
               for n,name in enumerate(consumer.NAMES)}
        raw=producer.image('ext2-1k',files)
        proof=consumer.verify_volume(raw,files)
        self.assertEqual((proof['files'],proof['free_inodes']),(10,11))
        for offset in (1040,2062,4098,21*1024+8,31*1024,32*1024):
            damaged=bytearray(raw);damaged[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(Exception):
                consumer.verify_volume(bytes(damaged),files)
    def test_actual_root_sequence_and_release(self):
        import ast
        from run_qemu_x86_64_runtime_clock import once
        tree=ast.parse((ROOT/'test/test_x86_64_application_tcp.py').read_text(encoding='utf-8'))
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='test_root_release_order')
        literals={n.targets[0].id:ast.literal_eval(n.value) for n in method.body
                  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
                  and n.targets[0].id in ('prefix','suffix')}
        prefix=literals['prefix']
        prefix=once(prefix,'#include <reist/x86_64/application_tcp.h>',
                    '#include <reist/x86_64/application_dns.h>\nstatic unsigned tcp_dns=1;\nstatic uint64_t tcp_dns_sequence[2];')
        prefix=once(prefix,'assert(q->operation==REIST_APP_TCP_RELEASE);',
                    'assert(q->sequence==(q->operation==REIST_APP_TCP_RELEASE?2:1));\n'
                    ' assert(q->grant.protocol==(received==3?6:17));')
        prefix=once(prefix,'network_message.length=608;revoked=1;',
                    'network_message.length=608;if(q->operation==REIST_APP_TCP_RELEASE)revoked=1;')
        prefix=once(prefix,'assert(received==1);q.grant=tcp_grant;q.operation=REIST_APP_TCP_RELEASE;q.sequence=1;',
                    'assert(received<=3);q.grant=tcp_grant;q.operation=received==3?REIST_APP_TCP_RELEASE:REIST_APP_TCP_OPEN;'
                    'q.sequence=received;if(received==2)q.grant.protocol=6;')
        prefix=once(prefix,'assert(ep==2&&m->length==608&&timeout==100&&!closed);return 0;',
                    'assert(ep==2&&m->length==608&&timeout==100&&!closed);'
                    'reist_app_tcp_request r;memcpy(&r,m->payload,608);'
                    'assert(r.sequence==received-1&&r.grant.protocol==(received==3?6:17));return 0;')
        suffix=once(literals['suffix'],'6100,6,REIST_APP_TCP_PEER,49164,5000,0',
                    '6100,17,REIST_APP_TCP_PEER,49164,53,0')
        suffix=once(suffix,'received==2','received==4&&tcp_dns_sequence[0]==2&&tcp_dns_sequence[1]==1')
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_tcp.inc').read_text(encoding='utf-8')
        function=source[source.index('static int64_t session_tcp_wait('):]
        self.host('root-sequence',None,[
            'userspace/sdk/lib/x86_64/application_dns.c','userspace/sdk/lib/x86_64/application_udp.c',
            'userspace/sdk/lib/x86_64/application_tcp.c','userspace/sdk/lib/x86_64/network_session.c'],
            ['-DREIST_NATIVE_APP_DNS'],source=prefix+function+suffix)
    def test_peer_query_bounds(self):
        import run_qemu_x86_64_application_dns as guest
        query=b'\x12\x34\x01\0\0\x01\0\0\0\0\0\0\x04test\x05local\0\0\x01\0\x01'
        result=guest.answer(query,'healthy4g')
        self.assertEqual(result[:2],query[:2]);self.assertEqual(result[-4:],bytes([192,0,2,3]))
        self.assertEqual(guest.answer(query,'cname')[6:8],b'\0\x02')
        self.assertNotEqual(guest.answer(query,'wrong-question')[13],query[13])
        for bad in (query+b'\0',query[:10],query[:-1]):
            with self.assertRaises(Exception):guest.answer(bad,'healthy4g')
        self.assertEqual(len(guest.CASES),25)
    def test_actual_udp_response_before_repeated_arp(self):
        from run_qemu_x86_64_runtime_clock import once
        source=(ROOT/'test/x86_64_application_udp_protocol_host.c').read_text(encoding='utf-8')
        # Real FIFO order: the response to SEND arrived before the subsequent
        # RECEIVE operation emitted another ARP request. The accepted old
        # fixture always prioritized ARP, concealing this packet loss.
        pending='    if(pending){pending=0;memcpy(f,arp_reply,42);return 42;}\n'
        source=once(source,pending,'')
        source=once(source,'    return -11;\n}',pending+'    return -11;\n}')
        source=once(source,'static unsigned datagram_size;','static unsigned datagram_size,duplicates;')
        source=once(source,'datagram_size=n;','datagram_size=n;duplicates=6;')
        source=once(source,'unsigned n=datagram_size;datagram_size=0;memcpy(f,datagram,n);',
                    'unsigned n=datagram_size;if(mode!=8||!--duplicates)datagram_size=0;memcpy(f,datagram,n);')
        source=once(source,'mode<=7','mode<=8')
        source=once(source,'mode&&mode!=7','mode&&mode<7')
        source=once(source,'if(!mode||mode==7)','if(!mode||mode>=7)')
        source=once(source,'assert(reads<=1600&&now<=2100);',
                    'assert(reads<=1600&&now<=2100);if(mode==8)assert(state.sockets[0].count==3);')
        source=once(source,'static unsigned datagram_size,duplicates;',
                    'static unsigned datagram_size,duplicates,nested;\n'
                    'static reist_app_udp_state *test_state;static reist_net_protocol *test_net;\n'
                    'static const reist_net_io *test_io;static reist_app_udp_request *test_request;')
        source=once(source,'reads++;',
                    'reads++;reist_app_udp_request untouched,before;memset(&untouched,0xa5,sizeof(untouched));before=untouched;'
                    'assert(reist_app_udp_exchange(test_state,test_net,test_io,test_request,&untouched)==-16);'
                    'assert(!memcmp(&before,&untouched,sizeof(before)));nested++;')
        source=once(source,'q.handle=r.handle;',
                    'test_state=&state;test_net=&net;test_io=&io;test_request=&q;q.handle=r.handle;')
        source=source[:source.rindex('    return 0;')]+source[source.rindex('    return 0;'):].replace(
            '    return 0;','    assert(nested);return 0;',1)
        self.host('udp-fifo',None,[
            'userspace/sdk/lib/x86_64/application_udp.c',
            'userspace/sdk/lib/x86_64/application_udp_protocol.c',
            'userspace/sdk/lib/x86_64/network_protocol.c',
            'userspace/sdk/lib/x86_64/network_session.c',
            'userspace/sdk/reist_ipv4_parser.c','userspace/sdk/reist_icmp_parser.c',
            'userspace/sdk/reist_udp_parser.c'],source=source)
    def test_actual_dns_raw_review(self):
        import run_qemu_x86_64_application_dns as guest
        base=ROOT/'build/codex-agent/r83bp-application-dns'
        proof=guest.review(base/'build05/x86_64/reist-x86_64-bootstrap.elf',base/'diagnostic04','healthy4g')
        self.assertEqual(proof['dns'],2)
    def test_review_rejects_unplanned_cpu_exhaustion(self):
        import run_qemu_x86_64_application_dns as guest
        base=ROOT/'build/codex-agent/r83bp-application-dns'
        with self.assertRaisesRegex(ValueError,'bounded autonomous stack failure only'):
            guest.review(base/'candidate02/build/x86_64/reist-x86_64-bootstrap.elf',
                         base/'candidate02/guests/tcp-fragmented','tcp-fragmented')
    def test_review_rejects_rehashed_corruption(self):
        import run_qemu_x86_64_application_dns as guest
        import tempfile,shutil,json,hashlib,struct
        base=ROOT/'build/codex-agent/r83bp-application-dns';original=base/'diagnostic04'
        with tempfile.TemporaryDirectory(dir=base) as temporary:
            folder=Path(temporary)
            for p in original.iterdir():
                if p.is_file() and (p.suffix in ('.bin','.json') or p.name in ('guest.log','frame-trace.log')):
                    shutil.copyfile(p,folder/p.name)
            trace=(folder/'frame-trace.log').read_text(encoding='utf-8')
            for field,offset,value in (('tcp_state',104,17),('udp_state',40,0)):
                lines=trace.splitlines()
                for i,line in enumerate(lines):
                    if not line.startswith('NETSESSION '):continue
                    e=json.loads(line[11:])
                    if e['kind']!='tcp-response':continue
                    control=(folder/e['raw']['control']['file']).read_bytes()
                    if struct.unpack_from('<I',control,8)[0]!=16:continue
                    p=folder/e['raw'][field]['file'];old=p.read_bytes();bad=bytearray(old)
                    struct.pack_into('<I',bad,offset,value);p.write_bytes(bad)
                    e['raw'][field]['sha256']=hashlib.sha256(bad).hexdigest()
                    lines[i]='NETSESSION '+json.dumps(e);break
                else:self.fail('paired grant snapshot missing')
                (folder/'frame-trace.log').write_text('\n'.join(lines)+'\n',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'atomic paired grant'):
                    guest.review(base/'build05/x86_64/reist-x86_64-bootstrap.elf',folder,'healthy4g')
                p.write_bytes(old)
            (folder/'frame-trace.log').write_text(trace,encoding='utf-8')
    def test_retained_udp_protocol(self):
        self.host('udp-original','test/x86_64_application_udp_protocol_host.c',[
            'userspace/sdk/lib/x86_64/application_udp.c','userspace/sdk/lib/x86_64/application_udp_protocol.c',
            'userspace/sdk/lib/x86_64/network_protocol.c','userspace/sdk/lib/x86_64/network_session.c',
            'userspace/sdk/reist_ipv4_parser.c','userspace/sdk/reist_icmp_parser.c','userspace/sdk/reist_udp_parser.c'])
    def test_tcp_cumulative_ack_batch(self):
        source=(ROOT/'test/x86_64_application_tcp_protocol_host.c').read_text(encoding='utf-8')
        source=source.replace('static unsigned receiving,inbound_sent;', 'static unsigned receiving,inbound_sent,ack_count;')
        source=source.replace('n<=10&&stamp+n<=deadline','n<=100&&stamp+n<=deadline')
        source=source.replace('assert(tcp.flags==16);','assert(tcp.flags==16);ack_count++;')
        source=source.replace('receiving=inbound_sent=0;','receiving=inbound_sent=ack_count=0;')
        source=source.replace('if(mode==7)assert(', 'if(mode==0)assert(ack_count==3);\n        if(mode==7)assert(')
        self.host('tcp-ack',None,[
            'userspace/sdk/lib/x86_64/application_tcp.c','userspace/sdk/lib/x86_64/application_tcp_protocol.c',
            'userspace/sdk/lib/x86_64/network_protocol.c','userspace/sdk/lib/x86_64/network_session.c',
            'userspace/sdk/reist_ipv4_parser.c','userspace/sdk/reist_icmp_parser.c',
            'userspace/sdk/reist_tcp_parser.c'],['-DREIST_NATIVE_APP_DNS'],source=source)

    def test_transport_idle_sleep(self):
        for transport,kind,counter,clock in (('udp','operation_io','turns','stamp'),('tcp','tcp_operation','sleeps','now')):
            source=(ROOT/f'userspace/sdk/lib/x86_64/application_{transport}_protocol.c').read_text(encoding='utf-8')
            a=source.index('static int time_check(');b=source.index('static int send_frame(',a)
            prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <reist/x86_64/network_session.h>
static uint64_t ticks;static unsigned calls,delay;static int mode;
static int sleeper(void *p,unsigned ms){(void)p;calls++;delay=ms;if(mode==1)return -5;if(mode==2)ticks--;else ticks+=ms;return 0;}
'''+f'typedef struct {{const reist_net_io *io;uint64_t end,last;unsigned {counter};}} {kind};\n'+f'static uint64_t {clock}(void *p){{(void)p;return ticks;}}\n'
            suffix=r'''
int main(void){reist_net_io io={.sleep=sleeper};
 for(unsigned scenario=0;scenario<7;scenario++){
  ticks=100;calls=delay=0;mode=scenario==3?1:scenario==4?2:0;
  KIND o={.io=&io,.end=scenario==1?135:1000,.last=100};
  if(scenario==2)o.COUNTER=200;
  if(scenario==5)o.end=100;
  int r=pause_ms(&o,scenario==6?0:10);
  if(scenario==0)assert(r==0&&calls==1&&delay==100&&o.COUNTER==10);
  if(scenario==1)assert(r==-110&&calls==1&&delay==35&&ticks==135);
  if(scenario==2||scenario==5)assert(r==-110&&!calls);
  if(scenario==3)assert(r==-5&&calls==1);
  if(scenario==4)assert(r==-84&&calls==1);
  if(scenario==6)assert(r==-22&&!calls);
 }return 0;}
'''.replace('KIND',kind).replace('COUNTER',counter)
            self.host(transport+'-idle',None,[],['-DREIST_NATIVE_APP_DNS'],source=prefix+source[a:b]+suffix)

    def test_actual_driver_reply_wait(self):
        source=(ROOT/'userspace/programs/native_netstack.c').read_text(encoding='utf-8')
        a=source.index('static int exchange(');b=source.index('static int send_frame(',a)
        prefix=r'''
#include <assert.h>
#include <string.h>
#include <reist/x86_64/network_session.h>
static reist_net_channel frames;
static reist_net_message packet;
static unsigned receives,sends,mode;static uint64_t stamp;
static uint64_t clock_now(void *p){(void)p;return stamp;}
int reist_net_encode(reist_net_channel *s,reist_net_message *m,unsigned type,const void *p,unsigned n,int result,uint64_t now,uint64_t end){
 (void)s;(void)p;(void)n;(void)result;assert(now==100&&end==300);m->type=type;m->deadline_ms=end;return 0;
}
int reist_net_send(reist_net_channel *s,reist_net_message *m){(void)s;assert(m->deadline_ms==300);sends++;return 0;}
int reist_net_receive(reist_net_channel *s,reist_net_message *m,unsigned timeout){
 (void)s;assert(timeout&&timeout<=100&&stamp+timeout<=300);receives++;
 if(mode==1||(mode==2&&receives==1)){stamp+=timeout;return -110;}
 if(mode==4){stamp+=timeout<17?timeout:17;return -11;}
 stamp+=1;m->type=mode==3?REIST_NET_HEALTH:REIST_NET_RESULT;m->result=0;return 0;
}
int reist_net_pause(unsigned ms){assert(ms==1);stamp+=ms;return 0;}
'''
        suffix=r'''
int main(void){
 for(mode=0;mode<5;mode++){
  stamp=100;sends=receives=0;memset(&frames,0,sizeof(frames));memset(&packet,0,sizeof(packet));
  int r=exchange(REIST_NET_RX,0,0,1100);
  assert(sends==1&&stamp<=301);
  if(mode==0)assert(r==0&&receives==1&&!frames.failed);
  if(mode==1)assert(r==-110&&receives==2&&frames.failed);
  if(mode==2)assert(r==0&&receives==2&&!frames.failed);
  if(mode==3)assert(r==-71&&receives==1&&frames.failed);
  if(mode==4)assert(r==-110&&receives<=12&&frames.failed);
 }
 stamp=100;sends=receives=0;assert(exchange(REIST_NET_RX,0,0,300)==-110&&!sends&&!receives);
 return 0;
}
'''
        self.host('driver-wait',None,[],['-DREIST_NATIVE_APP_DNS'],source=prefix+source[a:b]+suffix)

if __name__=='__main__':unittest.main()
