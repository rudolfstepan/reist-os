"""Full-width production timer and IPC boundaries, not a clock model."""
from pathlib import Path
import os, re, subprocess, sys, unittest, uuid, tempfile
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
import test_x86_64_task_frames as frames
from build_user_sdk import find_zig


class RuntimeClockTests(unittest.TestCase):
    def test_actual_admitted_page_selector(self):
        text=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body=re.search(r'^scheduler_probe_data_index64:\n.*?(?=^[A-Za-z_]\w*:)',text,re.M|re.S)
        self.assertIsNotNone(body,'missing admitted-page selector')
        consumers=text[text.index('scheduler_probe_data_index64:'):text.index('scheduler_verify_runqueue_magic64:')]
        asm='''BITS 64
%define REIST_NATIVE_RUNTIME 1
USER_PAGE_COUNT equ 8
TASK_RECORD_SIZE equ 256
TASK_CR3 equ 16
TASK_STACK_FRAME equ 24
TASK_PRIVATE_FRAMES equ 32
PF_R equ 4
PF_W equ 2
PF_X equ 1
section .bss
global runtime_page_flags
runtime_page_flags: resb 8
alignb 16
global runtime_tasks
runtime_tasks:
scheduler_tasks: resb 512
section .text
global scheduler_probe_data_index64
global runtime_isolation
runtime_isolation:
    push r12
    push r13
    push rbx
    call scheduler_verify_isolation64
    pop rbx
    pop r13
    pop r12
    ret
x86_64_elf64_page_frame64:
    mov eax,4096
    ret
x86_64_elf64_page_flags64:
    lea rax,[rel runtime_page_flags]
    movzx eax,byte [rax+rcx]
    ret
%ifdef REIST_NATIVE_RUNTIME
'''+consumers
        c='#define RUNTIME_LAYOUT_TEST 1\n'+(ROOT/'test/x86_64_runtime_clock_host.c').read_text()
        frames.TaskFrameTests().build(asm,c,'RUNTIME_CLOCK_HOST')

    def test_actual_timer_and_tick_admission(self):
        text=(ROOT/'arch/x86_64/cpu/timer_interrupt.asm').read_text()
        body=re.search(r'^timer_runtime_progress64:\n.*?(?=^[A-Za-z_]\w*:)',text,re.M|re.S)
        self.assertIsNotNone(body,'missing full-width runtime timer')
        inc=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        tick=re.search(r'^process_run_tick_admit64:\n.*?(?=^[A-Za-z_]\w*:)',inc,re.M|re.S).group()
        asm='''BITS 64
%define REIST_NATIVE_RUNTIME 1
TSC_DEADLINE_CYCLES equ 3000000000
section .bss
global scheduler_last_tick
scheduler_last_tick: resq 1
section .text
global timer_runtime_progress64
global runtime_admit
runtime_admit:
    mov rsi,rdi
    jmp process_run_tick_admit64
'''+body.group()+tick+(ROOT/'arch/x86_64/proc/cpu_budget.asm').read_text()
        frames.TaskFrameTests().build(asm,ROOT/'test/x86_64_runtime_clock_host.c','RUNTIME_CLOCK_HOST')

    def test_runtime_observer_oracles(self):
        import run_qemu_x86_64_runtime_clock as runtime
        for seed in (0,(1<<32)-200):
            trace='';rows=[]
            for run in (1,2):
                start=seed+(run-1)*320;end=start+320
                trace+=f'RUNTIME_CLOCK_BEGIN run={run} tick={start}\n'
                for slot in range(4):
                    gen=(run-1)*4+slot+1;used=32 if slot==0 else 1
                    rows.append(dict(slot=slot,generation=gen,ticks=used))
                    trace+=f'RUNTIME_CPU_WITNESS gen={gen} used={used} last={end-1} now={end}\n'
                trace+=f'RUNTIME_CLOCK_END run={run} tick={end} delta=320\n'
                trace+=f'PROCESS_ZERO_OK run={run} zero=1 free=200 initial=200 reaps=4 generation={run*4} ticks={end}\n'
            with patch.object(runtime.heap,'validate_heap') as remaining:
                runtime.validate(trace,rows,3,seed);remaining.assert_called_once()
                projected=remaining.call_args.args[0]
                self.assertEqual(runtime.ZERO.sub('',projected),runtime.ZERO.sub('',trace))
                self.assertEqual([z[7] for z in runtime.ZERO.finditer(projected)],['32','32'])
                bads=[trace+trace,trace.replace('delta=320','delta=319',1),
                      trace.replace('RUNTIME_CLOCK_END','MISSING',1),trace.replace('RUNTIME_CPU_WITNESS','MISSING',1),
                      trace.replace('used=32','used=31',1),trace.replace(f'last={seed+319}','last=0',1),
                      trace.replace(f'ticks={seed+320}',f'ticks={seed+321}',1),
                      trace.replace(f'tick={seed+320}',f'tick={seed+321}',1)]
                for bad in bads:
                    remaining.reset_mock()
                    with self.assertRaises(ValueError):runtime.validate(bad,rows,3,seed)
                    remaining.assert_not_called()

    def test_capture_start_failure_and_build_exclusion(self):
        import run_qemu_x86_64_runtime_clock as runtime
        vm=Mock()
        with tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent',prefix='runtime-start-') as folder:
            with patch.object(runtime,'resolve_qemu',return_value=Path('qemu')), \
                 patch.object(runtime.subprocess,'Popen',side_effect=[vm,OSError('no debugger')]), \
                 patch.object(runtime,'terminate_bounded') as stop:
                with self.assertRaises(OSError):runtime.capture(Path('image'),Path(folder),'continue\n')
                stop.assert_called_once_with(vm);vm.stdin.close.assert_called_once();vm.stdout.close.assert_called_once()
        for switch in ('-NativeImages','-NativeBulkIPC'):
            result=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                                   '-NativeRuntime',switch],cwd=ROOT,capture_output=True,text=True,timeout=10,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertNotEqual(result.returncode,0)
            self.assertIn('NativeRuntime excludes',result.stderr)
        for target,message in (('x86_64-native-image','NativeRuntime excludes NativeImages'),
                               ('x86_64-bootstrap','NativeRuntime requires Processes/IPC/RAM/Heap')):
            result=subprocess.run(['C:/msys64/usr/bin/make.exe','--no-print-directory','-n',target,
                                   'X86_64_NATIVE_RUNTIME=1'],cwd=ROOT,capture_output=True,text=True,timeout=10,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertNotEqual(result.returncode,0)
            self.assertIn(message,result.stderr)

    def test_actual_ipc_o0_o2(self):
        folder=ROOT/'build/codex-agent/r83ac-clock'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/('ipc-'+opt+'.exe')
            command=[str(find_zig()),'cc','-O'+opt,'-Wall','-Wextra','-Werror',
                     '-DREIST_NATIVE_RUNTIME','-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST',
                     '-DREIST_HOST_TEST','-DRUNTIME_IPC_TEST','-I.',
                     'test/x86_64_runtime_clock_host.c','kernel/ipc/ipc.c','kernel/init/critical_object.c','-o',str(exe)]
            for label,args in [('build',command),('run',[str(exe)]),
                               ('backward',[str(exe),'backward']),('horizon',[str(exe),'horizon'])]:
                result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,
                                      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(opt+'-'+label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
                if label!='build':self.assertIn('RUNTIME_CLOCK_HOST_OK',result.stdout)


if __name__=='__main__':unittest.main()
