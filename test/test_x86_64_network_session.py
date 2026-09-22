"""Execute the native control-plane production code with bounded wire peers."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid, shutil, json, hashlib, struct
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_sdk import find_zig

class NetworkSession(unittest.TestCase):
    def test_live_trace_fragment(self):
        from run_qemu_x86_64_network_session import stream_events
        path=ROOT/'build/codex-agent/r83bl-network-session/diagnostic27/frame-trace.log'
        lines=[line for line in path.read_text().splitlines(keepends=True) if line.startswith('NETSESSION ')]
        complete=lines[0];next_line=lines[1]
        for n in range(min(100,len(next_line)-1)):
            self.assertEqual(stream_events(complete+next_line[:n]),[json.loads(complete[11:])])
        with self.assertRaises(json.JSONDecodeError):stream_events(complete+'NETSESSION {broken}\n')

    def test_control_pause_deadline(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_network.inc').read_text(encoding='utf-8')
        function=source[source.index('static int network_control_pause('):source.index('static int network_rpc(')]
        harness='''#ifdef NDEBUG
#undef NDEBUG
#endif
#include <stdint.h>
#include <assert.h>
static uint64_t stamp;
static unsigned calls,extra;
static uint64_t session_now(void){return stamp;}
static int x86os_sleep_ms(unsigned n){assert(n&&n<=100);calls++;stamp+=n+extra;return 0;}
'''+function+'''
int main(void){
 assert(!network_control_pause(2000,2000)&&calls==3&&stamp==250);
 calls=0;stamp=0;assert(!network_control_pause(100,100)&&calls==1&&stamp==25);
 calls=0;stamp=0;assert(!network_control_pause(1,1)&&calls==0);
 calls=0;stamp=0;extra=2000;assert(network_control_pause(2000,2000)==-110&&calls==1&&stamp==2100);
 return 0;
}
'''
        self.host('control-pause',[],harness)

    def test_restart_pause_deadline(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_network.inc').read_text(encoding='utf-8')
        function=source[source.index('static int network_restart_pause('):source.index('static int network_launch(')]
        harness='''#ifdef NDEBUG
#undef NDEBUG
#endif
#include <stdint.h>
#include <assert.h>
static uint64_t stamp;
static unsigned calls,extra;
static int error;
static uint64_t session_now(void){return stamp;}
static int x86os_sleep_ms(unsigned n){assert(n==100);calls++;stamp+=n+extra;return error;}
'''+function+'''
int main(void){
 assert(!network_restart_pause(3000)&&calls==10&&stamp==1000);
 calls=0;stamp=0;assert(network_restart_pause(100)==-110&&!calls);
 calls=0;stamp=0;extra=200;assert(network_restart_pause(1000)==-110&&calls==3&&stamp==900);
 calls=0;stamp=0;extra=0;error=-5;assert(network_restart_pause(3000)==-5&&calls==1);
 return 0;
}
'''
        self.host('restart-pause',[],harness)

    def test_frame_deadline_admission(self):
        source=(ROOT/'userspace/programs/native_netstack.c').read_text(encoding='utf-8')
        functions=source[source.index('static int exchange('):source.index('static int receive_frame(')]
        harness='''#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <reist/x86_64/network_session.h>
static reist_net_channel frames;
static reist_net_message packet;
static uint64_t stamp,last_end;
static unsigned sends;
static int response,absent;
static uint64_t clock_now(void *p){(void)p;return stamp;}
int reist_net_encode(reist_net_channel *c,reist_net_message *m,unsigned type,const void *data,unsigned n,int result,uint64_t now,uint64_t end){(void)c;(void)m;(void)type;(void)data;(void)n;(void)result;assert(now==stamp);last_end=end;return 0;}
int reist_net_send(reist_net_channel *c,reist_net_message *m){(void)c;(void)m;sends++;return 0;}
int reist_net_receive(reist_net_channel *c,reist_net_message *m,unsigned timeout){(void)c;assert(!timeout);if(absent)return -11;m->type=REIST_NET_RESULT;m->length=0;m->result=response;return 0;}
int reist_net_pause(unsigned n){stamp+=n;return 0;}
'''+functions+'''
int main(void){
 unsigned char data[14]={0};stamp=100;
 assert(send_frame(0,data,14,300)==-110&&!sends&&!frames.failed);
 assert(exchange(REIST_NET_RX,0,0,299)==-110&&!sends&&!frames.failed);
 assert(!send_frame(0,data,14,301)&&sends==1&&last_end==300&&!frames.failed);
 response=-110;assert(send_frame(0,data,14,1000)==-110&&frames.failed&&sends==2);
 frames.failed=0;response=0;absent=1;
 assert(exchange(REIST_NET_RX,0,0,1000)==-110&&frames.failed&&stamp==300);
 return 0;
}
'''
        self.host('frame-deadline',[],harness)

    def test_capture_pacing_deadline(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_session.c').read_text(encoding='utf-8')
        function=source[source.index('static int session_fs_send('):source.index('static int session_fs_receive(')]
        harness='''#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
typedef struct {unsigned marker;} x86os_ipc_bulk_message_t;
static struct {unsigned filesystem_endpoint;} session_service={12};
#define REIST_NATIVE_NETWORK_SESSION 1
#define SESSION_S3(op,ep,q,timeout) fake_send(ep,q,timeout)
static uint64_t now,end;
static unsigned sent,slept;
static int sleep_error,extra;
static int session_rpc_remaining(unsigned timeout){return !timeout?-22:now>=end?-110:(int)(end-now<timeout?end-now:timeout);}
static int x86os_sleep_ms(unsigned n){assert(n==40);slept++;now+=n+extra;return sleep_error;}
static int fake_send(unsigned ep,const x86os_ipc_bulk_message_t *q,unsigned timeout){assert(ep==12&&q->marker==123);int r=session_rpc_remaining(timeout);if(r<0)return r;sent++;return 0;}
'''+function+'''
int main(void){
 x86os_ipc_bulk_message_t q={123};end=1000;
 assert(!session_fs_send(0,&q,1000)&&now==40&&sent==1&&slept==1&&end==1000);
 now=960;assert(session_fs_send(0,&q,1000)==-110&&sent==1&&slept==1);
 now=959;extra=1;assert(session_fs_send(0,&q,1000)==-110&&sent==1&&slept==2);
 now=0;extra=0;sleep_error=-5;assert(session_fs_send(0,&q,1000)==-5&&sent==1);
 sleep_error=0;assert(session_fs_send(0,&q,0)==-22&&sent==1);
 return 0;
}
'''
        self.host('capture',[],harness)

    def test_final_raw_review_rejects_semantic_mutations(self):
        import run_qemu_x86_64_network_session as guest
        from verify_x86_64_network_session import evidence
        base=evidence.EVIDENCE;image=base/'build14/x86_64/reist-x86_64-bootstrap.elf'
        self.assertEqual(guest.review(image,base/'diagnostic34',guest.CASES[4])['roles'],4)
        self.assertEqual(guest.review(image,base/'diagnostic32',guest.CASES[7])['roles'],4)
        for key in ('state','dma','profiles','packets','windows'):
            folder=base/('mutation-'+uuid.uuid4().hex);shutil.copytree(base/'diagnostic34',folder)
            if key=='packets':
                path=folder/'packets.json';value=json.loads(path.read_text());value['frames'][0]['sent']=[]
                path.write_text(json.dumps(value),encoding='utf-8')
            else:
                path=folder/'frame-trace.log';lines=path.read_text().splitlines()
                for index,line in enumerate(lines):
                    if not line.startswith('NETSESSION '):continue
                    e=json.loads(line[11:])
                    if e['kind']!='terminal' or e['slot']!=(5 if key=='profiles' else 4):continue
                    item=e['raw'][key];raw=bytearray((folder/item['file']).read_bytes())
                    if key=='state':struct.pack_into('<Q',raw,24,0);struct.pack_into('<Q',raw,216,0xffffffffffffffff)
                    elif key=='profiles':raw[5*32+16+6]^=2
                    elif key=='windows':struct.pack_into('<Q',raw,4*32+24,33)
                    else:raw[0]=1
                    (folder/item['file']).write_bytes(raw);item['sha256']=hashlib.sha256(raw).hexdigest()
                    lines[index]='NETSESSION '+json.dumps(e);break
                path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError,msg=key):guest.review(image,folder,guest.CASES[4])

    def test_actual_symbol_compaction(self):
        from build_x86_64_boot_programs import compact_input_elf
        base=ROOT/'build/codex-agent/r83bl-network-session'
        out=base/('compact-host-'+uuid.uuid4().hex);out.mkdir()
        image=out/'kernel.elf';shutil.copyfile(base/'build05/x86_64/reist-x86_64-bootstrap.elf',image)
        compact_input_elf(image,shutil.which('objcopy'),network_session=True)
        self.assertLessEqual(image.stat().st_size,1391616)
        self.assertTrue(image.with_suffix('.untrimmed.elf').exists())
    def test_protocol(self):
        self.host('protocol', ['userspace/sdk/lib/x86_64/network_protocol.c',
                   'userspace/sdk/reist_ipv4_parser.c', 'userspace/sdk/reist_icmp_parser.c'])

    def test_channel(self):
        self.host('session', ['userspace/sdk/lib/x86_64/network_session.c'])

    def test_freestanding_roles(self):
        from build_x86_64_network_programs import build_roles
        out = ROOT / 'build/codex-agent/r83bl-network-session' / ('roles-' + uuid.uuid4().hex)
        out.mkdir(parents=True)
        zig = str(find_zig())
        roles = build_roles(out, [zig, 'cc'], ['C:/tools/nasm-3.02/nasm.exe'], [zig, 'ld.lld'])
        self.assertEqual(len(roles), 2)
        for role in roles:
            self.assertEqual(role.read_bytes()[:5], b'\x7fELF\x02')

    def test_media_roundtrip(self):
        import build_x86_64_network_media as producer
        import check_x86_64_network_media as consumer
        from verify_x86_64_network_session import evidence
        values=producer.inputs(evidence.EVIDENCE/('build'+evidence.BUILD)/'x86_64')
        files=consumer.medium_files(values)
        raw=producer.image('ext2-1k',files)
        self.assertEqual(consumer.verify_volume(raw,files)['files'],7)
        damaged=bytearray(raw);damaged[4098]^=4
        with self.assertRaises(ValueError):consumer.verify_volume(bytes(damaged),files)

    def test_actual_healthy_raw(self):
        import run_qemu_x86_64_network_session as guest
        base=ROOT/'build/codex-agent/r83bl-network-session'
        result=guest.review_diagnostic(base/'build04/x86_64/reist-x86_64-bootstrap.elf',base/'diagnostic05')
        self.assertEqual(result['echoes'],2)

    def test_actual_restart_budget(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_network.inc').read_text(encoding='utf-8')
        budget=source[source.index('static int network_restart_budget(void)'):source.index('static int network_control_pause(')]
        policy=(ROOT/'userspace/sdk/lib/x86_64/service_session.c').read_text(encoding='utf-8').split('static int service_ops(')[0]
        harness='''#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
'''+policy+'''
static reist_session_policy_v1 session_policy;
static unsigned network_blocked,network_restarts;
static uint64_t stamp=100;
static uint64_t session_now(void){return stamp;}
static void session_bytes(void *d,const void *s,size_t n){memcpy(d,s,n);}
'''+budget+'''
int main(void) {
    assert(!reist_session_policy_init(&session_policy,1,stamp));
    assert(!network_restart_budget()&&!network_restart_budget());
    assert(network_restart_budget()==-11&&network_blocked&&network_restarts==2);
    assert(!session_policy.degraded&&session_policy.total_restarts==2);
    stamp+=20000;assert(network_restart_budget()==-11); /* sticky after shared window */
    assert(!reist_session_policy_charge(&session_policy,stamp,1,0,0)); /* independent shell progress */
    memset(&session_policy,0,sizeof(session_policy));network_blocked=network_restarts=0;
    assert(!reist_session_policy_init(&session_policy,1,stamp));
    assert(!reist_session_policy_restart(&session_policy,stamp)); /* FS already spent one */
    assert(!network_restart_budget());assert(network_restart_budget()==-11&&network_blocked);
    assert(!session_policy.degraded&&session_policy.total_restarts==2);
    network_blocked=network_restarts=0;session_policy.degraded=1;
    assert(network_restart_budget()==-11&&session_policy.degraded==1); /* never clear parent latch */
    return 0;
}
'''
        self.host('policy', [], harness)

    def test_interleaved_actual_echo(self):
        from run_qemu_x86_64_network_session import command_echo
        raw=(ROOT/'build/codex-agent/r83bl-network-session/diagnostic08/guest.log').read_bytes()
        tail=raw[raw.rindex(b'C:\\>net stat'):]
        self.assertNotIn(b'net status',tail)
        self.assertIn(b'net status',command_echo(tail))
        self.assertIn(b'REIST_X86_64_PROCESS_REAP_OK',tail)
        malformed=tail.replace(b'F5000000',b'G5000000')
        self.assertEqual(command_echo(malformed),malformed)

    def host(self, name, sources, harness=None):
        out = ROOT / 'build/codex-agent/r83bl-network-session' / ('host-' + uuid.uuid4().hex)
        out.mkdir(parents=True)
        entry='test/x86_64_network_' + name + '_host.c'
        if harness is not None:
            entry=out/'actual-policy.c';entry.write_text(harness,encoding='utf-8')
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(out / 'cache')
        for opt in ('0', '2'):
            exe = out / (name + '-O' + opt + '.exe')
            cmd = [str(find_zig()), 'cc', '-std=c11', '-O' + opt, '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-command-line-argument', '-UNDEBUG', '-Iuserspace/sdk/include',
                   str(entry), *sources, '-o', str(exe)]
            p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, timeout=90)
            (out / ('compile-O' + opt + '.log')).write_bytes(p.stdout + p.stderr)
            self.assertEqual(p.returncode, 0, (p.stdout + p.stderr).decode(errors='replace')[-3000:])
            p = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, timeout=10)
            (out / ('run-O' + opt + '.log')).write_bytes(p.stdout + p.stderr)
            self.assertEqual(p.returncode, 0, (p.stdout + p.stderr).decode(errors='replace'))

if __name__ == '__main__':
    unittest.main()
