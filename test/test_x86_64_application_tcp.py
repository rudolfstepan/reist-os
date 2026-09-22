"""Production native TCP objects and transport, O0/O2, bounded evidence."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,sys,tempfile,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig

class ApplicationTCP(unittest.TestCase):
    def test_actual_selected_service_generation(self):
        import run_qemu_x86_64_application_tcp as guest
        base=ROOT/'build/codex-agent/r83bn-application-tcp/candidate04'
        folder=base/'guests/stack-hang';image=base/'build/x86_64/reist-x86_64-bootstrap.elf'
        self.assertEqual(guest.review(image,folder,'stack-hang')['applications'],2)
        with tempfile.TemporaryDirectory(dir=base.parent) as d:
            target=Path(d)
            for p in folder.iterdir():
                if p.is_file() and (p.suffix in ('.json','.bin') or p.name in ('guest.log','frame-trace.log')):
                    shutil.copyfile(p,target/p.name)
            path=target/'frame-trace.log';lines=path.read_text().splitlines();changed=False
            for n,line in enumerate(lines):
                if not line.startswith('NETSESSION '):continue
                event=json.loads(line[11:])
                if event['kind']!='terminal' or event.get('slot')!=5:continue
                item=event['raw']['control'];p=target/item['file'];data=bytearray(p.read_bytes())
                if struct.unpack_from('<I',data,8)[0]!=14:continue
                receipt=(target/event['raw']['receipt']['file']).read_bytes()
                if struct.unpack_from('<II',receipt,8)!=(0,3):continue
                struct.pack_into('<I',data,144,1);p.write_bytes(data)
                item['sha256']=hashlib.sha256(data).hexdigest();lines[n]='NETSESSION '+json.dumps(event);changed=True;break
            self.assertTrue(changed);path.write_text('\n'.join(lines)+'\n')
            with self.assertRaisesRegex(ValueError,'selected hung stack CONNECT'):
                guest.review(image,target,'stack-hang')

    def test_actual_root_console_recovery(self):
        import run_qemu_x86_64_application_tcp as guest
        base=ROOT/'build/codex-agent/r83bn-application-tcp'
        proof=guest.review(base/'build08/x86_64/reist-x86_64-bootstrap.elf',base/'diagnostic08','root-console')
        self.assertEqual(proof['applications'],2)
        for name in ('diagnostic05','diagnostic06','diagnostic07'):
            old=json.loads((base/name/'result.json').read_text())
            self.assertFalse(old['passed'])
            self.assertTrue(old['closed'])

    def test_actual_root_console_clock_work(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_session.c').read_text()
        first=source[source.index('int x86os_sleep_ms('):source.index('void x86os_putchar(',source.index('int x86os_sleep_ms('))]
        prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
static uint64_t stamp=100;
static unsigned clocks,polls,received,written,emitted,session_output_used;
static unsigned session_input_idle __attribute__((unused));
static unsigned available=1,last_sleep;
static char session_output[64];
static struct {uint64_t previous_ms;} session_policy;
static uint64_t session_now(void){clocks++;session_policy.previous_ms=stamp;return stamp;}
static void session_network_poll(void){polls++;}
static void session_stop(int n){(void)n;abort();}
static int reist_session_policy_charge(void *p,uint64_t now,unsigned op,unsigned in,unsigned out){
 (void)p;assert(now==stamp&&!op);received+=in;written+=out;return 0;
}
static int64_t read_byte(unsigned fd,unsigned char *p,unsigned n){assert(!fd&&n==1);*p='A';return available?1:-11;}
#define SESSION_S3(op,a,b,c) read_byte(a,b,c)
static int64_t sleep_call(unsigned n){assert(n&&n<=100);last_sleep=n;stamp+=n;return 0;}
#define SESSION_S1(op,n) sleep_call(n)
static int reist_x64_console_write(const void *p,unsigned n,unsigned timeout,unsigned *done){
 (void)p;assert(n==64&&timeout==1000&&written>=emitted+n);emitted+=n;*done=n;return 0;
}
static void session_flush(void);
'''
        suffix=r'''
int main(void){
 for(unsigned n=0;n<512;n++) {
  assert(x86os_getchar_nonblocking()=='A');session_write("A",1);
  if(n%64==63)stamp+=10;
 }
 assert(polls==8&&received==512&&written==512&&emitted==512&&!session_output_used);
 assert(clocks<=540);
 available=0;
 for(unsigned n=0;n<20;n++){assert(!x86os_getchar_nonblocking());assert(!x86os_sleep_ms(10)&&last_sleep==50);}
 assert(!x86os_getchar_nonblocking());assert(!x86os_sleep_ms(1)&&last_sleep==1);
 assert(!x86os_sleep_ms(10)&&last_sleep==10);
 assert(!x86os_getchar_nonblocking());available=1;assert(x86os_getchar_nonblocking()=='A');
 assert(!x86os_sleep_ms(10)&&last_sleep==10);return 0;
}
'''
        self.host('root-console',None,[],['-DREIST_NATIVE_APP_TCP=1','-DREIST_NATIVE_NETWORK_SESSION=1'],source=prefix+first+suffix)

    def test_actual_output_capacity_and_unchanged_cpu_quota(self):
        import run_qemu_x86_64_application_tcp as guest
        base=ROOT/'build/codex-agent/r83bn-application-tcp'
        image=base/'build04/x86_64/reist-x86_64-bootstrap.elf'
        self.assertEqual(guest.review(image,base/'diagnostic03','receive-capacity')['applications'],2)
        self.assertEqual(guest.review(image,base/'diagnostic04','app-cpu')['applications'],2)
        old=base/'candidate02/guests/receive-capacity';receipts=[]
        for line in (old/'frame-trace.log').read_text().splitlines():
            if not line.startswith('NETSESSION '):continue
            event=json.loads(line[11:])
            if event['kind']!='terminal' or event['slot']!=6:continue
            item=event['raw']['receipt'];value=(old/item['file']).read_bytes()
            self.assertEqual(hashlib.sha256(value).hexdigest(),item['sha256'])
            receipts.append(struct.unpack('<4I2Q',value))
        self.assertEqual([r[2:5] for r in receipts],[(256,3,32),(256,3,32)])

    def test_actual_retired_time_wait_handle(self):
        import run_qemu_x86_64_application_tcp as guest
        base=ROOT/'build/codex-agent/r83bn-application-tcp/candidate01'
        result=guest.review(base/'build/x86_64/reist-x86_64-bootstrap.elf',base/'guests/stale-grant','stale-grant')
        self.assertEqual(result['applications'],4)

    def test_actual_raw_review_and_mutations(self):
        import run_qemu_x86_64_application_tcp as guest
        folder=ROOT/'build/codex-agent/r83bn-application-tcp/diagnostic02'
        image=ROOT/'build/codex-agent/r83bn-application-tcp/build03/x86_64/reist-x86_64-bootstrap.elf'
        self.assertEqual(guest.review(image,folder,'healthy4g')['applications'],4)
        for mutation in ('ring','authority','padding'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory(dir=folder.parent) as d:
                target=Path(d)
                for path in folder.iterdir():
                    if path.is_file() and (path.suffix in ('.json','.bin') or path.name in ('guest.log','frame-trace.log')):
                        shutil.copyfile(path,target/path.name)
                if mutation=='padding':
                    p=target/'packets.json';value=json.loads(p.read_text());frame=bytearray.fromhex(value['frames'][0]['tx'])
                    frame[-1]=1;value['frames'][0]['tx']=frame.hex();p.write_text(json.dumps(value))
                else:
                    p=target/'frame-trace.log';lines=p.read_text().splitlines()
                    for index,line in enumerate(lines):
                        if not line.startswith('NETSESSION '):continue
                        event=json.loads(line[11:])
                        if event['kind']!=('tcp-wire' if mutation=='ring' else 'tcp-app-start'):continue
                        key='applications' if mutation=='ring' else 'profile';item=event['raw'][key]
                        raw=bytearray((target/item['file']).read_bytes())
                        if mutation=='ring':raw[728+36:728+40]=(2049).to_bytes(4,'little')
                        else:raw[16:24]=(1<<49).to_bytes(8,'little')
                        (target/item['file']).write_bytes(raw);item['sha256']=hashlib.sha256(raw).hexdigest()
                        lines[index]='NETSESSION '+json.dumps(event);break
                    p.write_text('\n'.join(lines)+'\n')
                with self.assertRaises(ValueError):guest.review(image,target,'healthy4g')

    def test_disabled_projection(self):
        from verify_x86_64_application_tcp import source_projection
        self.assertTrue(source_projection())

    def test_frozen_controllers(self):
        import run_qemu_x86_64_application_tcp as guest
        self.assertEqual(len(guest.CASES),25)
        for name in guest.CASES:
            controller=guest.controller(guest.specification(name))
            self.assertEqual(controller.CASE['name'],name)
        self.assertIn('nc 192.0.2.3 5000 hello',guest.specification('healthy4g')['dialogue'])

    def test_objects(self):
        self.host('objects','test/x86_64_application_tcp_host.c',[])

    def test_protocol(self):
        self.host('protocol','test/x86_64_application_tcp_protocol_host.c',[
            'userspace/sdk/lib/x86_64/application_tcp_protocol.c',
            'userspace/sdk/lib/x86_64/network_protocol.c',
            'userspace/sdk/lib/x86_64/network_session.c',
            'userspace/sdk/reist_ipv4_parser.c','userspace/sdk/reist_icmp_parser.c',
            'userspace/sdk/reist_tcp_parser.c'])

    def test_platform(self):
        self.host('platform','test/x86_64_application_tcp_platform_host.c',[
            'userspace/sdk/lib/x86_64/application_tcp_platform.c',
            'userspace/sdk/lib/x86_64/network_session.c'],['-DREIST_APP_TCP_HOST_TEST'])

    def test_root_blocking_result_deadlines(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_tcp.inc').read_text()
        function=source[source.index('static int tcp_stack('):source.index('static int session_tcp_revoke(')]
        prefix=r'''
#include <assert.h>
#include <reist/x86_64/application_tcp.h>
#define REIST_NET_TCP_REQUEST 14
static reist_net_channel network_channels[2];
static reist_net_message network_message;
static unsigned tcp_transport_failed,network_active=1,mode,calls;
static uint64_t clock_ms=100,network_health;
static uint64_t session_now(void){return clock_ms;}
static int network_send(unsigned role,unsigned op,const void *p,unsigned n,uint64_t end){
 (void)op;(void)p;(void)n;assert(role==1&&end>clock_ms);return 0;
}
static int reist_net_receive(reist_net_channel *c,reist_net_message *m,unsigned wait){
 assert(c==network_channels+1&&wait>0&&wait<=100);calls++;clock_ms+=wait;
 if(mode==1&&calls==1){m->type=REIST_NET_HEALTH;m->length=m->result=0;return 0;}
 if(mode==1&&calls==2){m->type=REIST_NET_RESULT;m->length=m->result=0;return 0;}
 if(mode==2){c->failed=1;return -32;}
 return -110;
}
'''
        suffix=r'''
int main(void){
 assert(tcp_stack(14,0,0,350)==-110&&clock_ms==450&&calls==4);
 clock_ms=100;calls=0;tcp_transport_failed=0;
 assert(tcp_stack(14,0,0,2100)==-110&&clock_ms==1100&&calls==10);
 clock_ms=100;calls=0;tcp_transport_failed=0;mode=1;
 assert(!tcp_stack(14,0,0,1000)&&calls==2&&network_health==300&&!tcp_transport_failed);
 clock_ms=100;calls=0;mode=2;
 assert(tcp_stack(14,0,0,1000)==-32&&tcp_transport_failed&&calls==1);
 return 0;
}
'''
        self.host('root-blocking',None,[],source=prefix+function+suffix)

    def test_root_release_order(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_tcp.inc').read_text()
        function=source[source.index('static int64_t session_tcp_wait('):]
        prefix=r'''
#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <reist/x86_64/application_tcp.h>
#define REIST_NET_TCP_REQUEST 14
#define REIST_NET_TCP_REVOKE 15
static reist_app_tcp_grant tcp_grant;
static reist_net_message network_message;
static uint64_t tcp_sequence,session_child=(4ULL<<32)|6,network_health=100;
static unsigned tcp_request=1,tcp_reply=2,session_tcp_active=1,network_busy=1;
static unsigned tcp_transport_failed;
static uint64_t reist_tcp_root_selection[2];
static unsigned received,closed,revoked,reaped;
static uint64_t session_now(void){return 100;}
static void session_zero(void *p,unsigned n){memset(p,0,n);}
static void session_bytes(void *p,const void *q,unsigned n){memcpy(p,q,n);}
static int tcp_equal(const void *p,const void *q,unsigned n){return !memcmp(p,q,n);}
static void session_stop(int r){(void)r;abort();}
int x86os_sleep_ms(unsigned n){(void)n;abort();return -5;}
static void tcp_close_channels(void){assert(reaped);closed=1;tcp_request=tcp_reply=0;}
static int session_tcp_revoke(void){abort();return 0;}
static int64_t service_task(void *p,unsigned operation,uint64_t owner,unsigned timeout){
 (void)p;assert(operation==2&&owner==session_child&&timeout==1000);
 assert(revoked&&!closed);reaped=1;return 0;
}
static int tcp_stack(unsigned op,const void *p,unsigned n,uint64_t end){
 assert(op==REIST_NET_TCP_REQUEST&&n==608&&end==1000);
 const reist_app_tcp_request *q=p;assert(q->operation==REIST_APP_TCP_RELEASE);
 memcpy(network_message.payload,q,608);network_message.length=608;revoked=1;return 0;
}
static int receive(unsigned ep,x86os_ipc_bulk_message_t *m,unsigned timeout){
 assert(ep==1&&timeout==100);reist_app_tcp_request q={0};q.deadline=1000;
 if(!received){q.grant=tcp_grant;q.grant.root=q.grant.service=q.grant.epoch=q.grant.expires=0;}
 else {assert(received==1);q.grant=tcp_grant;q.operation=REIST_APP_TCP_RELEASE;q.sequence=1;}
 received++;m->length=608;memcpy(m->payload,&q,608);return 0;
}
static int send(unsigned ep,x86os_ipc_bulk_message_t *m,unsigned timeout){
 assert(ep==2&&m->length==608&&timeout==100&&!closed);return 0;
}
#define IPC_RECEIVE_TIMEOUT receive
#define IPC_SEND_TIMEOUT send
#define SESSION_S3(n,a,b,c) n(a,b,c)
'''
        suffix=r'''
int main(void){
 tcp_grant=(reist_app_tcp_grant){1,64,1ULL<<32,(4ULL<<32)|6,(3ULL<<32)|5,1,6100,6,REIST_APP_TCP_PEER,49164,5000,0};
 int timeout=0;assert(!session_tcp_wait(&timeout));
 assert(!timeout&&received==2&&closed&&revoked&&reaped&&!session_tcp_active&&!network_busy);return 0;
}
'''
        self.host('root-release', None, [], source=prefix+function+suffix)

    def test_failed_transport_fences_without_another_rpc(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_tcp.inc').read_text()
        function=source[source.index('static int session_tcp_revoke('):source.index('static int64_t session_tcp_import(')]
        prefix=r'''
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_tcp.h>
#define REIST_NET_TCP_REVOKE 15
static reist_app_tcp_grant tcp_grant;
static reist_net_message network_message;
static unsigned network_active=1,network_failed,tcp_transport_failed,closed,fenced;
static uint64_t session_now(void){return 100;}
static void session_zero(void *p,unsigned n){memset(p,0,n);}
static void tcp_close_channels(void){closed=1;}
static int tcp_stack(unsigned op,const void *p,unsigned n,uint64_t end){
 (void)p;assert(!tcp_transport_failed);assert(op==15&&!n&&end==1100);return 0;
}
static int session_network_retire(void){assert(closed);fenced++;return 0;}
'''
        suffix=r'''
int main(void){
 tcp_grant.epoch=1;tcp_transport_failed=1;
 assert(session_tcp_revoke()<0);assert(closed&&fenced==1&&network_failed&&!tcp_grant.epoch);return 0;
}
'''
        self.host('failed-transport',None,[],source=prefix+function+suffix)

    def host(self,name,entry,sources,flags=(),source=None):
        out=ROOT/'build/codex-agent/r83bn-application-tcp'/('host-'+uuid.uuid4().hex)
        out.mkdir(parents=True)
        if source is not None:
            entry=out/'actual-production.c';entry.write_text(source,encoding='utf-8')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(out/'cache')
        for opt in ('0','2'):
            exe=out/(name+'-O'+opt+'.exe')
            command=[str(find_zig()),'cc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror',
                     '-Wno-unused-command-line-argument','-UNDEBUG','-Iuserspace/sdk/include',
                     *flags,str(entry),'userspace/sdk/lib/x86_64/application_tcp.c',*sources,'-o',str(exe)]
            for step,args,limit in [('compile',command,90),('run',[str(exe)],10)]:
                result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,timeout=limit)
                (out/(step+'-O'+opt+'.log')).write_bytes(result.stdout+result.stderr)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-2200:])

if __name__=='__main__':unittest.main()
