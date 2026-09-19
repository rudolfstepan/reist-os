"""Execute production session admission, including mutation-free failures."""
from pathlib import Path
import ast,inspect,struct,subprocess,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host

class SessionAdmissionTests(unittest.TestCase):
    def test_actual_window_core(self):
        source=(ROOT/'arch/x86_64/proc/session_admission.inc').read_text()
        host.TaskFrameTests().build('BITS 64\nsection .text\n'+source,
            ROOT/'test/x86_64_session_admission_host.c','SESSION_ADMISSION')

    def test_actual_construction_charge_boundary(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        body=source.split('family_create64:',1)[1].split('    call scheduler_save_syscall_context64',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_SESSION 1
%define REIST_NATIVE_LIFECYCLE 1
%define NATIVE_POOL_TASKS 8
TASK_GENERATION equ 8
section .bss
alignb 8
global family_records,family_session_window,scheduler_last_tick,family_request
global process_run_plan,process_run_generation
family_records: resq 64
family_session_window: resq 7
scheduler_last_tick: resq 1
family_request: resq 10
process_run_plan: resq 42
process_run_generation: resd 1
scheduler_current_slot: resd 1
family_build_slot: resd 1
family_admitted_profile: resq 5
family_profiles: resq 32
section .text
%include "arch/x86_64/proc/session_admission.inc"
global test_create
test_create:
    mov [rel scheduler_current_slot],edi
    shl edi,6
    lea r10,[rel family_records]
    add r10,rdi
    jmp family_create64
family_create64:
'''+body+'''
    mov eax,42 ; reached allocation boundary after actual charge, no allocator model
    ret
family_result64: ret
scheduler_fail:
    mov rax,-999
    ret
family_profile_attenuate64:
    mov rax,-13
    ret
family_record64:
    mov eax,edi
    shl eax,6
    lea r10,[rel family_records]
    add r10,rax
    ret
'''
        c=r'''#include <stdint.h>
#include <string.h>
#include <stdio.h>
typedef uint64_t U;
extern U family_records[64],family_session_window[7],scheduler_last_tick,family_request[10],process_run_plan[42];
extern uint32_t process_run_generation;
extern int64_t __attribute__((sysv_abi)) test_create(unsigned);
extern U __attribute__((sysv_abi)) session_admission64(U*,U,U,U);
#define CHECK(x) do {if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
int main(void) {
    family_records[0]=7ULL<<32;family_records[8]=(8ULL<<32)|1;
    scheduler_last_tick=100;process_run_generation=10;
    family_request[0]=1;family_request[3]=6;family_request[5]=1ULL<<9;
    process_run_plan[3]=process_run_plan[7]=1ULL<<9;
    CHECK(session_admission64(family_session_window,1,7,100)==1);
    for(unsigned i=0;i<8;i++)CHECK(test_create(0)==42 && family_records[6]==i+1);
    U saved[7];memcpy(saved,family_session_window,56);
    CHECK(test_create(0)==-11 && !memcmp(saved,family_session_window,56));
    scheduler_last_tick=200;CHECK(test_create(0)==42 && family_records[6]==9);
    family_records[14]=8;scheduler_last_tick=300;
    CHECK(test_create(1)==-11 && family_records[14]==8);
    memcpy(saved,family_session_window,56);
    for(unsigned s=2;s<8;s++)family_records[s*8+5]=4;
    CHECK(test_create(0)==-11 && !memcmp(saved,family_session_window,56));
    family_records[2*8+5]=0;family_request[5]|=1ULL<<22;
    CHECK(test_create(0)==-13 && !memcmp(saved,family_session_window,56));
    family_request[5]=1ULL<<9;process_run_generation=0x7fffffff;
    CHECK(test_create(0)==-11 && !memcmp(saved,family_session_window,56));
    process_run_generation=10;family_records[6]++;
    CHECK(test_create(0)==-999 && !memcmp(saved,family_session_window,56));
    family_records[6]--;scheduler_last_tick=199;
    CHECK(test_create(0)==-999 && !memcmp(saved,family_session_window,56));
    puts("SESSION_BOUNDARY_OK");return 0;
}'''
        host.TaskFrameTests().build(asm,c,'SESSION_BOUNDARY')

    def test_selector_rejects_before_build_effects(self):
        import build_x86_64_boot_programs as producer
        with patch.object(producer.Path,'mkdir',side_effect=AssertionError('build effect')):
            for value in (True,1,'1',None):
                with self.subTest(value=value),self.assertRaises(ValueError):
                    producer.build('unused',[],[],[],0,session=value)

    def test_separate_guest_preserves_accepted_cpu_fixture(self):
        name='arch/x86_64/user/task_pool.c'
        before=subprocess.check_output(['git','show','fee850d2:'+name],cwd=ROOT,timeout=10).decode().replace('\r\n','\n')
        self.assertEqual(before,(ROOT/name).read_text())
        guest=(ROOT/'test/x86_64_session_admission_host.c').read_text().split('#else\n',1)[0]
        self.assertIn('#include "../arch/x86_64/user/task_pool.c"',guest)
        self.assertIn('if(root_witness.mode!=12)return __real_main(argc,argv);',guest)
        source=(ROOT/'scripts/build_x86_64_boot_programs.py').read_text()
        self.assertIn("*(['--wrap=main'] if session and n<2 else [])",source)

    def test_window_oracle_mutations(self):
        import run_qemu_x86_64_session_admission as run
        a=[7,100,91,99,8,8,1];b=[7,100,191,191,1,9,1]
        self.assertEqual(run.window_charge(a,7,191),(1,b))
        self.assertEqual(run.window_charge(a,7,190),(2,a))
        self.assertEqual(run.window_charge(a,7,1000091),(1,[7,100,1000091,1000091,1,9,1]))
        for index,value in ((0,8),(1,99),(2,101),(3,191),(4,9),(5,7),(6,2)):
            bad=a.copy();bad[index]=value
            with self.assertRaises(ValueError):run.window_charge(bad,7,191)
        with self.assertRaises(ValueError):run.window_charge(a,7,98)
        for index in range(7):
            bad=b.copy();bad[index]^=1
            with self.assertRaises(ValueError):run.validate_charge(a,bad,7,191,1)

    def test_actual_session_selector_precedes_first_user_instruction(self):
        import run_qemu_x86_64_session_admission as run
        config=dict(s={},cs={},root_data=[1,2],child_record=b'')
        code=run.observer(config,ROOT/'build/codex-agent')
        body=code.split('python\n',1)[1].rsplit('\nend\n',1)[0]
        hooks=[node for node in ast.walk(ast.parse(body)) if isinstance(node,ast.Call)
               and isinstance(node.func,ast.Name) and node.func.id=='Hook'
               and len(node.args)==2 and isinstance(node.args[1],ast.Name) and node.args[1].id=='start']
        self.assertEqual(len(hooks),1)
        hook=ast.literal_eval(hooks[0].args[0])
        # The actual callback mutates only the private selector. The fixture
        # reads it before GETPID, so a syscall-return hook is observably late.
        t=[0]*128;t[0]=2;t[1]=7;t[2]=0x100004000;t[3]=0x100001000;t[4]=0x100002000
        tables=struct.pack('<4Q',0x100004000,0x100005000,0x100006000,0x100007000)
        symbols=dict(scheduler_current_slot=1,scheduler_tasks=1024,scheduler_table_frames=10000,family_records=20000)
        writes=[];seen=[];values={1032:7}
        dm=0xffff800000000000;physical=dm+0x100002008;values[physical]=0
        def write(address,raw):
            self.assertEqual((address,raw),(physical,struct.pack('<Q',12)))
            writes.append((address,raw));values[address]=struct.unpack('<Q',raw)[0]
        def memory(address,size):
            return {(1024,1024):struct.pack('<128Q',*t),(10000,32):tables,(20000,64):bytes(64)}[(address,size)]
        class Inferior:
            write_memory=staticmethod(write)
        class GDB:
            selected_inferior=staticmethod(lambda:Inferior())
        namespace=dict(S=symbols,CONFIG=dict(root_data=[0x420000,0x430000]),DM=dm,MASK=0x3fffff000,
            gdb=GDB,struct=struct,starts={},runs=0,mode=lambda:8,task=lambda slot:t,
            d=lambda address:0,q=lambda address:values[address],mem=memory,reg=lambda name:0,
            walk=lambda root,address:0x100002007,snapshot=lambda raw:seen.append(raw),emit=lambda *a,**k:None)
        exec(run.source_node(run.BODY,'start'),namespace)
        if hook=='scheduler_enter_task64.state_published':namespace['start']()
        selected_by_wrapper=values[physical]
        if hook=='process_run_resume64':namespace['start']()
        self.assertEqual(selected_by_wrapper,12,'selector must precede __wrap_main branch')
        self.assertEqual(len(writes),1);self.assertEqual(len(seen[0]),1120)
        namespace['start']();self.assertEqual(len(writes),1,'no second write for one generation')
        self.assertEqual(hook,'scheduler_enter_task64.state_published')
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        self.assertIn('jmp scheduler_enter_task64.state_published',source.split('process_run_enter64:',1)[1].split('process_run_syscall64:',1)[0])

    def test_actual_generated_observer_and_fatal_mutations(self):
        import run_qemu_x86_64_session_admission as run
        config=dict(s={},cs={},root_data=[1,2],child_record=b'')
        for code in (run.observer(config,ROOT/'build/codex-agent'),
                     *(run.fatal_observer(config,ROOT/'build/codex-agent',k) for k in run.FATAL_CASES)):
            body=code.split('python\n',1)[1].rsplit('\nend\n',1)[0]
            ast.parse(body)
            self.assertNotIn('def stop(self):\n        global injected',body)
        saved=[bytes(n) for _,n in run.FATAL_RANGES]
        family=bytearray(saved[4]);struct.pack_into('<Q',family,0,7<<32);saved[4]=bytes(family)
        saved[-1]=struct.pack('<7Q',7,100,0,0,0,0,1)
        for kind in run.FATAL_CASES:
            changed,writes=run.fatal_mutation(kind,saved)
            self.assertEqual(len(writes),1);self.assertEqual(len(writes[0][2]),8)
            self.assertEqual(changed[:-1],saved[:-1])
            with self.assertRaises(ValueError):run.window_charge(list(struct.unpack('<7Q',changed[-1])),7,0)
        # The retained fatal oracle executes exactly its original code object.
        with patch.object(run.types,'FunctionType',wraps=run.types.FunctionType) as factory:
            with self.assertRaises(ValueError):run.validate_fatal('','',run.FATAL_CASES[0],ROOT)
            self.assertIs(factory.call_args.args[0],run.cpu.validate_fatal.__code__)

    def test_actual_retirement_barrier_blocks_and_fails_closed(self):
        text=(ROOT/'test/x86_64_session_admission_host.c').read_text()
        pause='static int session_pause'+text.split('static int session_pause',1)[1].split('#if PROGRAM_ID==0',1)[0]
        helper='static int session_retained'+text.split('static int session_retained',1)[1].split('static int session_case6',1)[0]
        old=(ROOT/'arch/x86_64/user/task_pool.c').read_text()
        old='static int service_retained'+old.split('static int service_retained',1)[1].split('#endif',1)[0]
        c=r'''#include <stdint.h>
#include <stdio.h>
enum {IPC_RECEIVE_TIMEOUT=1,SLEEP_MS,YIELD,IPC_CREATE,IPC_CLOSE};
static unsigned receives,sleeps,yields,delays,creates,closes;static int64_t answer,idle_answer=-110;
static int sleep_error,bad,create_error,close_error;
static void message_init(volatile uint32_t *p,unsigned n){for(unsigned i=0;i<35;i++)p[i]=0;p[0]=1;p[1]=140;p[2]=n;}
static int64_t S0(unsigned op){if(op!=YIELD)bad=1;return ++yields==32?-1:0;}
static int64_t s1(unsigned op,uintptr_t arg){
 if(op==IPC_CREATE){creates++;if(!create_error)*(uint32_t*)arg=9;return create_error;}
 if(op==IPC_CLOSE){closes++;if(arg!=9)bad=1;return close_error;}
 bad=1;return -1;
}
#define S1(op,arg) s1(op,(uintptr_t)(arg))
static int64_t S3(unsigned op,unsigned ep,volatile uint32_t *p,unsigned timeout){
 if(op!=IPC_RECEIVE_TIMEOUT || (ep!=7 && ep!=9) || p[0]!=1 || p[1]!=140 || p[2] || timeout!=1000)bad=1;
 if(ep==9){sleeps++;return sleep_error?0:idle_answer;}
 return ++receives<=delays?-110:answer;
}
'''+old+pause+helper+r'''
#define CHECK(x) do {if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
int main(void){
 answer=-32;CHECK(service_retained(7)==-1 && yields==32 && !sleeps && !bad);
 int errors[]={-32,-110,0,1,-9,-13,-22};
 for(unsigned e=0;e<sizeof(errors)/sizeof(*errors);e++)for(delays=0;delays<=8;delays++)for(sleep_error=0;sleep_error<=1;sleep_error++) {
  receives=sleeps=yields=bad=creates=closes=0;answer=errors[e];int result=session_retained(7);
  CHECK(!bad && !yields && receives<=8);
  CHECK(result==((delays<8 && answer==-32 && !sleep_error)?0:-1));
  CHECK(sleeps==(delays<8 && answer==-32));
  CHECK(creates==sleeps && closes==sleeps);
 }
 sleep_error=0;create_error=-28;creates=closes=sleeps=0;CHECK(session_pause()==-1 && creates==1 && !closes && !sleeps);
 create_error=0;close_error=-9;creates=closes=sleeps=0;CHECK(session_pause()==-1 && creates==1 && closes==1 && sleeps==1);
 close_error=0;
 int unexpected[]={0,1,-9,-13,-32};for(unsigned n=0;n<sizeof(unexpected)/sizeof(*unexpected);n++) {
  idle_answer=unexpected[n];creates=closes=sleeps=0;
  CHECK(session_pause()==-1 && creates==1 && closes==1 && sleeps==1 && !bad);
 }
 puts("SESSION_RETENTION_OK");return 0;
}'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'SESSION_RETENTION')

    def test_actual_case6_workflow_matches_old_except_blocking_barrier(self):
        import test_x86_64_service_cpu as old_tests
        captured=[]
        with patch.object(host.TaskFrameTests,'build',side_effect=lambda *args:captured.append(args)):
            old_tests.ServiceCPUTests().test_actual_retention_barrier_bounds_and_phase_order()
        self.assertEqual(len(captured),1)
        code=captured[0][1].split('int main(void){',1)[0].replace('actual_root','old_root')
        old='if(op==IPC_DELEGATE)return 0;'
        self.assertEqual(code.count(old),1)
        code=code.replace(old,old+'\n if(op==IPC_RECEIVE_TIMEOUT && a==4){if(c!=1000 || root_witness.phase!=3)bad=1;sleeps++;return fail_sleep?0:-110;}')
        self.assertEqual(code.count('sleeps!=56 || receives'),1)
        code=code.replace('sleeps!=56 || receives','(sleeps!=56 && sleeps!=1) || receives')
        text=(ROOT/'test/x86_64_session_admission_host.c').read_text()
        pause='static int session_pause'+text.split('static int session_pause',1)[1].split('#if PROGRAM_ID==0',1)[0]
        functions='static int session_retained'+text.split('static int session_retained',1)[1].split('\n#endif\nint __wrap_main',1)[0]
        code+=pause+functions+r'''
int main(void){
 for(delay=0;delay<8;delay++)for(fail_sleep=0;fail_sleep<=1;fail_sleep++) {
  answer=-32;reset();CHECK(old_root(0,0)==(fail_sleep?244:90) && !bad);
  unsigned old_waits=waits,old_barriers=barriers,old_receives=receives,old_phase=root_witness.phase;
  CHECK(sleeps==(fail_sleep?1:56));
  reset();CHECK(session_case6()==(fail_sleep?244:90) && !bad && sleeps==1);
  CHECK(waits==old_waits && barriers==old_barriers && receives==old_receives && root_witness.phase==old_phase);
 }
 puts("SESSION_WORKFLOW_OK");return 0;
}'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',code,'SESSION_WORKFLOW')

    def test_actual_native_sleep_admission_rejects_long_delay(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('\n.sleep:\n',1)[1].split('%ifdef REIST_NATIVE_RUNTIME',1)[0]
        asm='''BITS 64
section .bss
alignb 8
syscall_rdi: resq 1
section .text
global native_sleep_admit
native_sleep_admit:
    mov [rel syscall_rdi],rdi
'''+body+'''
    ret
.invalid:
    mov rax,-22
    ret
'''
        c=r'''#include <stdint.h>
#include <stdio.h>
extern int64_t __attribute__((sysv_abi)) native_sleep_admit(uint64_t);
int main(void){
 for(uint64_t n=0;n<=2000;n++)if(native_sleep_admit(n)!=(n>=1 && n<=100?(int64_t)((n+9)/10):-22))return 1;
 if(native_sleep_admit(UINT64_MAX)!=-22)return 1;
 puts("SESSION_SLEEP_BOUND_OK");return 0;
}'''
        host.TaskFrameTests().build(asm,c,'SESSION_SLEEP_BOUND')


if __name__=='__main__':unittest.main()
