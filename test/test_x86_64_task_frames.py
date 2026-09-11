"""Execute native task retirement assembly and retain the actual old defect."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class TaskFrameTests(unittest.TestCase):
    def build(self,asm,c,label):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83p-retirement'/(label+'-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=60,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2500:]);return r.stdout
        if isinstance(asm,str):
            (folder/'source.asm').write_text(asm,encoding='ascii');asm=folder/'source.asm'
        if isinstance(c,str):
            (folder/'source.c').write_text(c,encoding='ascii');c=folder/'source.c'
        obj=folder/'code.o';run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',asm,'-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',c,obj,'-o',exe],opt+'-build')
            self.assertIn(label+'_OK',run([exe],opt+'-run'))

    def test_previous_duplicate_regression(self):
        old=subprocess.check_output(['git','show','a0f919a3:arch/x86_64/proc/cooperative_scheduler.asm'],cwd=ROOT,text=True,timeout=10)
        body='scheduler_release_task_frames64:'+old.split('scheduler_release_task_frames64:',1)[1].split('scheduler_append_event64:',1)[0]
        asm='''BITS 64
TASK_RECORD_SIZE equ 256
TASK_SLOT_CAPACITY equ 4
TASK_PRIVATE_FRAMES equ 32
TASK_STACK_FRAME equ 24
TASK_CR3 equ 16
USER_PAGE_COUNT equ 8
TASK_TABLE_LEVELS equ 4
section .bss
align 16
global scheduler_tasks
scheduler_tasks: resq 128
scheduler_table_frames: resq 16
scheduler_fp_states: resb 2048
section .text
global run_legacy
extern physical_frame_free64
run_legacy:
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    lea r12,[rel scheduler_tasks]
    call scheduler_release_task_frames64
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
x86_64_fp_clear64:
    mov eax,1
    ret
'''+body
        c='''#include <stdio.h>
#include <stdint.h>
extern uint64_t scheduler_tasks[128];
extern int __attribute__((sysv_abi)) run_legacy(void);
static int calls,owned=1;
int __attribute__((sysv_abi)) physical_frame_free64(uint64_t frame) {
    ++calls;if(frame!=0x4000000 || !owned)return 0;owned=0;return 1;
}
int main(void) {
    scheduler_tasks[4]=scheduler_tasks[5]=0x4000000;
    if(run_legacy()!=0 || calls!=2 || owned || scheduler_tasks[4]!=0 || scheduler_tasks[5]!=0x4000000)return 1;
    puts("LEGACY_DUPLICATE_OK observed_first_free_before_duplicate_failure=1");return 0;
}
'''
        self.build(asm,c,'LEGACY_DUPLICATE')

    def test_actual_core(self):
        self.build(ROOT/'arch/x86_64/mm/task_frames.asm',ROOT/'test/x86_64_task_frames_host.c','TASK_FRAMES_HOST')

    def test_runtime_oracle(self):
        from run_qemu_x86_64_task_frames import validate
        cases=[(m,slot,slot+1,4 if slot==0 else 3 if m==1 else 5)
               for m in (1,2,3) for slot in (0,1)]
        cases += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]
        cases += [(5,s,20+s,4) for s in range(4)]
        cases += [(6,1,31,8),(6,1,32,8),(6,0,30,4),(7,1,41,8),(7,1,42,8),(7,0,40,4)]
        frames=[0,0x4001000]+[0]*6+[0x4002000,0x4006000,0x4005000,0x4004000,0x4003000]
        trace=''
        for seq,(mode,slot,gen,state) in enumerate(cases,1):
            trace+=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=4003000 active=115000 before=100 fp=1 frames='+','.join(f'{f:x}' for f in frames)+'\n'
            trace+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in frames if f)
            trace+=f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=106 zero=1\n'
        serial=''.join(f'CHILD_EXIT_REAP_OK status=0000004D generation={g:02X} parent=07 queued=00 rip=0000000000400444\nREIST_X86_64_RING3_SHELL_RUN_OK\n' for g in (41,42))
        validate(serial,trace,0x400444)
        for bad in (trace+trace,trace.replace('TASK_FRAMES_FREE','MISSING',1),trace.replace('frame=4001000','frame=4002000',1),
                    trace.replace('root=4003000','root=115000',1),trace.replace('after=106','after=105',1),
                    trace.replace('zero=1','zero=0',1),trace.replace('result=1','result=0',1),trace.replace('fp=1','fp=0',1),
                    trace.replace('state=4','state=5',1),trace.replace('gen=42','gen=41'),trace.replace('slot=0','slot=4',1),
                    trace.replace('4001000','8000000'),trace+'TASK_FRAMES_FREE seq=20 frame=4003000\n'):
            with self.assertRaises(RuntimeError):validate(serial,bad,0x400444)
        for bad in (serial+serial,serial.replace('queued=00','queued=01',1),serial.replace('400444','400442',1),
                    serial.replace('0000004D','0000004E',1),serial.replace('generation=2A','generation=29')):
            with self.assertRaises(RuntimeError):validate(bad,trace,0x400444)

    def test_shared_cleanup_and_active_root_guard(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body=source.split('scheduler_release_task_frames64:',1)[1].split('scheduler_append_event64:',1)[0]
        self.assertEqual(body.count('call reist_x64_task_frames_release'),1)
        self.assertNotIn('call physical_frame_free64',body)
        self.assertLess(body.index('cmp rax, [rdx + TASK_TABLE_PML4]'),body.index('call reist_x64_task_frames_release'))
        self.assertLess(body.index('call reist_x64_task_frames_release'),body.index('call x86_64_fp_clear64'))
        self.assertIn('call scheduler_release_task_frames64',source.split('scheduler_force_cleanup64:',1)[1])
        core=(ROOT/'arch/x86_64/mm/task_frames.asm').read_text()
        self.assertNotIn('physical_frame_alloc64',core)
        self.assertNotIn('scheduler_',core)
        self.assertLess(core.index('.validated:'),core.index('call physical_frame_free64'))

if __name__=='__main__':unittest.main()
