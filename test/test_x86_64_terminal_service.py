"""Actual protected terminal service mechanism and unchanged disabled profile."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host
class TerminalServiceTests(unittest.TestCase):
    def test_cli_actual_capture_and_service_denial_mutations(self):
        import copy,json,struct
        import run_qemu_x86_64_terminal_service as guest
        import run_qemu_x86_64_display as display
        import run_qemu_x86_64_cli_media as cli
        import verify_x86_64_terminal_service as verify
        namespace=getattr(guest,'cli_namespace',display.cli_namespace)
        module=namespace('driver-crash').ay
        image,_=verify.package();config,records,files=cli.apps.image_config(image,'driver-crash');module.app_files=files
        folder=verify.EVIDENCE/'candidate01/runtime/hdd-fallback-recovery'
        module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),7,2,files)
        trace=module.decode_evidence(module.capture_text((folder/'frame-trace.log').read_bytes()))
        rows=[json.loads(line[14:]) for line in trace.splitlines() if line.startswith('SHELL_SESSION ')]
        probes=[r for r in rows if r['kind']=='return' and r['op']==127 and struct.unpack_from('<I',bytes.fromhex(r['before']),8)[0]==6]
        self.assertEqual(len(probes),2)
        for row in probes:
            starts,live=module.authority_state((folder/row['authority']['file']).read_bytes())
            module.validate_terminal(row,starts,live)
            for index in range(24):
                bad=copy.deepcopy(row);request=bytearray.fromhex(bad['before']);request[index]^=1
                bad['before']=bad['after']=request.hex()
                with self.assertRaises(ValueError):module.validate_terminal(bad,starts,live)
            for name,value in [('op',126),('slot',4),('gen',row['gen']+1),('profile_denied',True),('size',23),('result',0),('terminal','00'*24),('after','00'*24)]:
                bad=copy.deepcopy(row);bad[name]=value
                with self.assertRaises(ValueError):module.validate_terminal(bad,starts,live)
            peer=row['gen']+1
            for change in ('dead','slot','parent'):
                altered=copy.deepcopy(starts);alive=set(live)
                if change=='dead':alive.remove(peer)
                if change=='slot':altered[peer]['slot']=4
                if change=='parent':altered[peer]['parent']=row['gen']<<32
                with self.assertRaises(ValueError):module.validate_terminal(row,altered,alive)
    def test_live_service_oracle_rejects_corrupted_authority(self):
        import json,tempfile
        import run_qemu_x86_64_terminal_service as guest
        original=ROOT/'build/codex-agent/r83bh-terminal-service/guest02'
        proof=json.loads((original/'result.json').read_text())['live'][0]
        path=original/('live'+str(proof['number']));p=proof['proof']
        event=(1,64,1,0,p['driver'],p['consumer'],p['epoch'],1,0,0,0,0)
        self.assertEqual(guest.live_profile(path,event),p)
        with tempfile.TemporaryDirectory(dir=original.parent,prefix='oracle-') as temporary:
            out=Path(temporary)
            names=('tasks','profiles','family','terminal-service','terminal-lease')
            for name in names:(out/(name+'.bin')).write_bytes((path/(name+'.bin')).read_bytes())
            for name in ('terminal-service','terminal-lease'):
                target=out/(name+'.bin');raw=target.read_bytes()
                for index in range(len(raw)):
                    bad=bytearray(raw);bad[index]^=1;target.write_bytes(bad)
                    with self.assertRaises(ValueError,msg=name+':'+str(index)):guest.live_profile(out,event)
                target.write_bytes(raw)
    def test_actual_consumer_faults_and_complete_matrix(self):
        import run_qemu_x86_64_input as old
        import run_qemu_x86_64_terminal_service as new
        self.assertEqual(new.CASES[:12],old.CASES)
        self.assertEqual([r[1] for r in new.CASES[12:]],['c','d','e'])
        source=(ROOT/'arch/x86_64/user/input_client.c').read_text(encoding='utf-8')
        body=source[source.index('static int service_fault('):source.index('\n#endif',source.index('static int service_fault('))]
        # Instrument only the CPU instructions; execute the real finite sleep loop.
        body=body.replace('__asm__ volatile("pause")','quota()').replace('__builtin_trap()','crash()')
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <setjmp.h>
#define REIST_X64_SYS_SLEEP_MS 41
static jmp_buf recovery;static unsigned samples,sleeps;static int failure;
static void crash(void){longjmp(recovery,134);}
static void quota(void){if(++samples==32)longjmp(recovery,256);}
static int64_t reist_x64_syscall1(unsigned n,uint64_t ms){if(n!=41||ms!=100)return -22;sleeps++;return failure?-5:0;}
'''+body+r'''
int main(void){
 int r=setjmp(recovery);if(!r)service_fault('c');if(r!=134)return 1;
 r=setjmp(recovery);if(!r)service_fault('d');if(r!=256||samples!=32)return 2;
 if(service_fault('e')!=110||sleeps!=60)return 3;
 failure=1;if(service_fault('e')!=5||sleeps!=61)return 4;
 puts("TERMINAL_SERVICE_FAULT_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\nglobal unused_host_symbol\nunused_host_symbol: ret\n',c,'TERMINAL_SERVICE_FAULT')
    def test_compaction_preserves_all_loaded_bytes_and_public_symbols(self):
        import uuid,shutil
        from build_x86_64_boot_programs import compact_input_elf
        from build_x86_64_c_payload import elf
        folder=ROOT/'build/codex-agent/r83bh-terminal-service'/('compact-host-'+uuid.uuid4().hex)
        folder.mkdir();target=folder/'probe.elf'
        original=(ROOT/'build/codex-agent/r83bh-terminal-service/build01/x86_64/reist-x86_64-bootstrap.untrimmed.elf').read_bytes()
        target.write_bytes(original)
        compact_input_elf(target,shutil.which('objcopy') or 'C:/msys64/mingw64/bin/objcopy.exe',True)
        actual=target.read_bytes();before=elf(original,32);after=elf(actual,32)
        self.assertLessEqual(len(actual),1391616)
        self.assertEqual(before['programs'],after['programs']);self.assertEqual(before['entry'],after['entry'])
        for p in before['programs']:
            a=p['offset'];b=a+p['filesz'];self.assertEqual(original[a:b],actual[a:b])
        removed={n for n,v in before['symbols'].items() if n.startswith(('native_input_','native_terminal_')) and '.' in n and v['binding']==0}
        self.assertEqual(after['symbols'],{n:v for n,v in before['symbols'].items() if n not in removed})
    def test_default_projection_and_actual_freestanding_consumers(self):
        from verify_x86_64_terminal_service import default_projection
        default_projection()
        import subprocess
        from unittest import mock
        from test_x86_64_input import InputTests
        original=subprocess.run
        def compile_profile(args,*a,**kw):
            if isinstance(args,list) and 'x86_64-freestanding-none' in args:
                args=[*args,'-DREIST_NATIVE_TERMINAL_SERVICE=1']
            return original(args,*a,**kw)
        with mock.patch.object(subprocess,'run',side_effect=compile_profile):
            InputTests().test_disabled_profile_and_freestanding_units()
    def test_actual_shell_transfer_after_independent_peer_retirement(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_session.c').read_text(encoding='utf-8')
        body=source[source.index('int x86os_terminal_input('):source.index('int x86os_process_identity_of(')]
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define REIST_NATIVE_TERMINAL_SERVICE 1
#define REIST_TERMINAL_TRANSFER 2
#define REIST_TERMINAL_CHECK 5
#define REIST_X64_SYS_READ 15
static uint64_t session_child=(14ULL<<32)|4,session_input_service_pending=(15ULL<<32)|5;
static uint64_t session_terminal_service,session_previous_terminal_service=(7ULL<<32)|4;
static struct {uint64_t owner;} session_policy={1};
static unsigned grants,transfers,checks,reads,stale;
static void session_stop(int error){printf("STOP %d\n",error);exit(99);}
static uint64_t session_now(void){return 6000;}
static int reist_x64_terminal_service(unsigned op,uint64_t target){
 if(op==6 && target==session_input_service_pending)return -13;
 if(op==6 && target==session_child)return grants++?-16:0;
 if(op==7 && target==session_previous_terminal_service){stale++;return -116;}
 return -22;
}
static int reist_x64_terminal_input(unsigned op,int pid,unsigned generation){
 if(op==5&&!pid&&!generation){checks++;return -11;}
 if(op==2&&pid==2&&generation==2)return -116; /* Real peer has terminated. */
 if(op==2&&pid==14&&generation==14){transfers++;return 0;}
 return -22;
}
static int64_t reist_x64_syscall3(unsigned n,uint64_t a,uint64_t b,uint64_t c){
 if(n==15&&!a&&!b&&!c){reads++;return -11;}return -22;
}
'''+body+r'''
int main(void){
 int r=x86os_terminal_input(2,14,14);
 if(r||grants!=2||transfers!=1||checks!=1||reads!=1||stale!=1||session_terminal_service!=session_child||session_policy.owner!=1)return 1;
 puts("TERMINAL_SERVICE_SHELL_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\nglobal unused_host_symbol\nunused_host_symbol: ret\n',c,'TERMINAL_SERVICE_SHELL')
    def test_actual_service_planner_o0_o2(self):
        old=(ROOT/'arch/x86_64/proc/native_terminal.inc').read_text(encoding='utf-8').split('; RUNTIME ADAPTER',1)[0]
        core=(ROOT/'arch/x86_64/proc/terminal_service_core.inc').read_text(encoding='utf-8')
        host.TaskFrameTests().build('BITS 64\n%define REIST_NATIVE_DISPLAY 1\nsection .text\n'+old+'\n'+core,ROOT/'test/x86_64_terminal_service_host.c','TERMINAL_SERVICE')
if __name__=='__main__':unittest.main()
