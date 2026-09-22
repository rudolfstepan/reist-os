"""Behavior of production native UDP authority; all outputs stay in ignored evidence."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid, json, struct, hashlib, shutil, ast
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_sdk import find_zig

class ApplicationUDP(unittest.TestCase):
    def test_actual_interleaved_application_output(self):
        import run_qemu_x86_64_application_udp as udp
        raw=(ROOT/'build/codex-agent/r83bm-application-udp/candidate03/guests/app-hang/guest.log').read_bytes()
        self.assertNotIn(b'udp-local-peer',raw)
        self.assertIn(b'udp-local-peer',udp.dialogue_text(raw))
        damaged=raw.replace(b'REIST_X86_64_PROCESS_REAP_OK v1=',b'REIST_X86_64_PROCESS_REAP_OK v1=G')
        self.assertEqual(udp.dialogue_text(damaged),damaged)

    def test_terminal_ipc_failure_invalidates_transport(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/network_session.c').read_text()
        function=source[source.index('int reist_net_receive('):source.index('static int hex(')]
        prefix=r'''
#include <assert.h>
#include <reist/x86_64/network_session.h>
static x86os_ipc_bulk_message_t transport;
static int failure;
#define REIST_X64_SYS_IPC_RECEIVE_TIMEOUT 54
static int64_t reist_x64_syscall3(unsigned n,uint64_t a,uint64_t b,uint64_t c){
 (void)b;assert(n==54&&a==1&&!c);return failure;
}
uint64_t reist_net_now(void){return 100;}
'''
        suffix=r'''
int main(void){
 reist_net_channel channel={.endpoint=1};reist_net_message message;
 failure=-11;assert(reist_net_receive(&channel,&message,0)==-11&&!channel.failed);
 failure=-110;assert(reist_net_receive(&channel,&message,0)==-110&&!channel.failed);
 failure=-32;assert(reist_net_receive(&channel,&message,0)==-32&&channel.failed);
 return 0;
}
'''
        self.host('terminal-transport',None,['userspace/sdk/lib/x86_64/network_session.c'],
                  ['-DREIST_NATIVE_APP_NETWORK=1'],source=prefix+function+suffix)

    def test_observer_counts_only_application_sends(self):
        import run_qemu_x86_64_application_udp as udp
        values={'mode':8,'slot':3,'syscall':53};calls=[]
        class Hook:
            def stop(self):calls.append(1);return False
        namespace=dict(Hook=Hook,mode=lambda:values['mode'],d=lambda n:values[n],q=lambda n:values[n],
                       S={'scheduler_current_slot':'slot','syscall_rax':'syscall'})
        node=next(n for n in ast.parse(udp.UDP_OBSERVER).body if isinstance(n,ast.ClassDef) and n.name=='UDPIPCHook')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual UDP breakpoint>','exec'),namespace)
        hook=namespace['UDPIPCHook']()
        for _ in range(5000):self.assertFalse(hook.stop())
        self.assertEqual(calls,[])
        values['slot']=6;hook.stop();self.assertEqual(calls,[1])
        values['syscall']=54;hook.stop();self.assertEqual(calls,[1])

    def test_raw_replay_rejects_rehashed_authority_mutations(self):
        import run_qemu_x86_64_application_udp as udp
        base=ROOT/'build/codex-agent/r83bm-application-udp'
        original=base/'diagnostic08';image=base/'build08/x86_64/reist-x86_64-bootstrap.elf'
        self.assertEqual(udp.review(image,original,'stack-hang')['applications'],2)
        lines=(original/'frame-trace.log').read_text().splitlines()
        cases=[('udp-app-start','profile',8,8,1<<49,'exact foreground profile'),
               ('udp-request','capabilities',None,4,3,'attenuated application capability'),
               ('udp-response','applications',100,4,0xc0000204,'explicit fixed-peer'),
               ('udp-root-terminal','network_restarts',0,4,3,'bounded root network'),
               ('udp-finish','capabilities',0,1,1,'all IPC capabilities revoked')]
        for kind,key,offset,size,value,reason in cases:
            with self.subTest(kind=kind,key=key):
                out=base/('mutation-'+uuid.uuid4().hex);out.mkdir()
                for path in original.iterdir():
                    if path.is_file() and (path.suffix in ('.bin','.json') or path.name in ('guest.log','frame-trace.log')):
                        shutil.copyfile(path,out/path.name)
                edited=list(lines)
                for n,line in enumerate(edited):
                    if not line.startswith('NETSESSION '):continue
                    e=json.loads(line[11:])
                    if e['kind']!=kind:continue
                    path=out/e['raw'][key]['file'];raw=bytearray(path.read_bytes())
                    if offset is None:
                        offset=next(at+24 for at in range(0,2048,32) if raw[at] and struct.unpack_from('<i',raw,at+16)[0]==e['owner']>>32)
                    raw[offset:offset+size]=value.to_bytes(size,'little');path.write_bytes(raw)
                    e['raw'][key]['sha256']=hashlib.sha256(raw).hexdigest()
                    edited[n]='NETSESSION '+json.dumps(e);break
                else:self.fail('missing actual evidence '+kind)
                (out/'frame-trace.log').write_text('\n'.join(edited)+'\n')
                with self.assertRaisesRegex(ValueError,reason):udp.review(image,out,'stack-hang')

    def test_frozen_controllers(self):
        import run_qemu_x86_64_application_udp as udp
        self.assertEqual(len(udp.CASES),20)
        original=udp.base.diagnostic
        for name in udp.CASES:
            spec=udp.specification(name);controller=udp.controller(spec)
            self.assertEqual(controller.CASE['name'],name)
            self.assertIs(udp.base.diagnostic,original)
        with self.assertRaises(ValueError):udp.specification('unknown')

    def test_objects(self):
        self.host('objects', 'test/x86_64_application_udp_host.c', [])

    def test_protocol(self):
        self.host('protocol', 'test/x86_64_application_udp_protocol_host.c', [
            'userspace/sdk/lib/x86_64/application_udp_protocol.c',
            'userspace/sdk/lib/x86_64/network_protocol.c',
            'userspace/sdk/lib/x86_64/network_session.c',
            'userspace/sdk/reist_ipv4_parser.c', 'userspace/sdk/reist_icmp_parser.c',
            'userspace/sdk/reist_udp_parser.c'])

    def test_platform(self):
        self.host('platform', 'test/x86_64_application_udp_platform_host.c', [
            'userspace/sdk/lib/x86_64/application_udp_platform.c',
            'userspace/sdk/lib/x86_64/network_session.c'], ['-DREIST_APP_UDP_HOST_TEST=1'])

    def test_root_release_order(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_udp.inc').read_text()
        function=source[source.index('static int64_t session_udp_wait('):]
        prefix=r'''
#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <reist/x86_64/application_udp.h>
#define REIST_NET_APP_REQUEST 11
#define REIST_NET_APP_REVOKE 12
static reist_app_udp_grant udp_grant;
static reist_net_message network_message;
static uint64_t udp_sequence,session_child=(4ULL<<32)|6,network_health=100;
static unsigned udp_request=1,udp_reply=2,session_udp_active=1,network_busy=1;
static unsigned udp_transport_failed;
static uint64_t reist_udp_root_selection[2];
static unsigned received,closed,revoked,reaped;
static uint64_t session_now(void){return 100;}
static void session_zero(void *p,unsigned n){memset(p,0,n);}
static void session_bytes(void *p,const void *q,unsigned n){memcpy(p,q,n);}
static int udp_equal(const void *p,const void *q,unsigned n){return !memcmp(p,q,n);}
static void session_stop(int r){(void)r;abort();}
int x86os_sleep_ms(unsigned n){(void)n;abort();return -5;}
static void udp_close_channels(void){assert(reaped);closed=1;udp_request=udp_reply=0;}
static int session_udp_revoke(void){abort();return 0;}
static int64_t service_task(void *p,unsigned operation,uint64_t owner,unsigned timeout){
 (void)p;assert(operation==2&&owner==session_child&&timeout==1000);
 assert(revoked&&!closed);reaped=1;return 0;
}
static int udp_stack(unsigned op,const void *p,unsigned n,uint64_t end){
 assert(op==REIST_NET_APP_REQUEST&&n==608&&end==1000);
 const reist_app_udp_request *q=p;assert(q->operation==REIST_APP_UDP_RELEASE);
 memcpy(network_message.payload,q,608);network_message.length=608;revoked=1;return 0;
}
static int receive(unsigned ep,x86os_ipc_bulk_message_t *m,unsigned timeout){
 assert(ep==1&&!timeout);reist_app_udp_request q={0};q.deadline=1000;
 if(!received){q.grant=udp_grant;q.grant.root=q.grant.service=q.grant.epoch=q.grant.expires=0;}
 else {assert(received==1);q.grant=udp_grant;q.operation=REIST_APP_UDP_RELEASE;q.sequence=1;}
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
 udp_grant=(reist_app_udp_grant){1,64,1ULL<<32,(4ULL<<32)|6,(3ULL<<32)|5,1,6100,17,REIST_APP_UDP_PEER,4000,5000,0};
 int timeout=0;assert(!session_udp_wait(&timeout));
 assert(!timeout&&received==2&&closed&&revoked&&reaped&&!session_udp_active&&!network_busy);return 0;
}
'''
        self.host('root-release', None, [], source=prefix+function+suffix)

    def test_failed_transport_fences_without_another_rpc(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_udp.inc').read_text()
        function=source[source.index('static int session_udp_revoke('):source.index('static int64_t session_udp_import(')]
        prefix=r'''
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_udp.h>
#define REIST_NET_APP_REVOKE 12
static reist_app_udp_grant udp_grant;
static reist_net_message network_message;
static unsigned network_active=1,network_failed,udp_transport_failed,closed,fenced;
static uint64_t session_now(void){return 100;}
static void session_zero(void *p,unsigned n){memset(p,0,n);}
static void udp_close_channels(void){closed=1;}
static int udp_stack(unsigned op,const void *p,unsigned n,uint64_t end){
 (void)p;assert(!udp_transport_failed);assert(op==12&&!n&&end==1100);return 0;
}
static int session_network_retire(void){assert(closed);fenced++;return 0;}
'''
        suffix=r'''
int main(void){
 udp_grant.epoch=1;udp_transport_failed=1;
 assert(session_udp_revoke()<0);assert(closed&&fenced==1&&network_failed&&!udp_grant.epoch);return 0;
}
'''
        self.host('failed-transport',None,[],source=prefix+function+suffix)

    def test_fresh_stat_retires_sequence_zero_dependency(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_session.c').read_text()
        begin=source.index('static int session_ensure(')
        stop=source.index('    now=session_now();if(now>=deadline)',begin)
        function=source[begin:stop]+'    return 1;\n}\n'
        prefix=r'''
#include <stdint.h>
#include <assert.h>
#define REIST_SESSION_HEALTHY 2
#define REIST_FS_SESSION_REQUESTS 100
static struct {unsigned phase;uint64_t deadline_ms;} session_service;
static struct {unsigned failed;uint64_t sequence;} session_fs;
static struct {unsigned degraded;} session_policy;
static unsigned retired;
static uint64_t session_now(void){return 100;}
static int session_retire(void){retired++;session_service.phase=0;return 0;}
'''
        suffix=r'''
int main(void){
 session_service.phase=REIST_SESSION_HEALTHY;session_service.deadline_ms=10000;
 assert(session_ensure(1000,1)==1&&retired==1);
 session_service.phase=REIST_SESSION_HEALTHY;
 assert(session_ensure(1000,0)==0&&retired==1);return 0;
}
'''
        self.host('fresh-stat',None,[],['-DREIST_NATIVE_APP_NETWORK=1'],source=prefix+function+suffix)

    def host(self, name, entry, sources, flags=(), source=None):
        out = ROOT / 'build/codex-agent/r83bm-application-udp' / ('host-' + uuid.uuid4().hex)
        out.mkdir(parents=True)
        if source is not None:
            entry=out/'actual-root-wait.c';entry.write_text(source)
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(out / 'cache')
        for opt in ('0', '2'):
            exe = out / (name + '-O' + opt + '.exe')
            command = [str(find_zig()), 'cc', '-std=c11', '-O' + opt, '-Wall', '-Wextra',
                       '-Werror', '-Wno-unused-command-line-argument', '-UNDEBUG',
                       '-Iuserspace/sdk/include', *flags, entry,
                       'userspace/sdk/lib/x86_64/application_udp.c', *sources, '-o', str(exe)]
            for name, args, timeout in [('compile', command, 90), ('run', [str(exe)], 10)]:
                p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
                (out / (name + '-O' + opt + '.log')).write_bytes(p.stdout + p.stderr)
                self.assertEqual(p.returncode, 0, (p.stdout + p.stderr).decode(errors='replace')[-2500:])

if __name__ == '__main__':
    unittest.main()
