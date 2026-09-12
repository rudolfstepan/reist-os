"""Production read-only owner admission, O0/O2, and strict guest oracle."""
from pathlib import Path
import re, struct, sys, tempfile, unittest
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'test'))
sys.path.insert(0, str(ROOT/'scripts'))
import test_x86_64_task_frames as host_builder


def harness(source):
    def function(name):
        return re.search(r'^'+name+r':\n.*?(?=^[A-Za-z_][\w]*:|\Z)', source, re.M|re.S).group()
    names = ('scheduler_validate_owner_terminal64', 'scheduler_owner_zero64',
        'scheduler_owner_frames_valid64', 'scheduler_identity_apply64',
        'scheduler_profile_apply64', 'scheduler_budget_apply64', 'scheduler_queue_apply64',
        'scheduler_verify_shell_ipc_zero64', 'scheduler_verify_shell_ipc_wait_zero64',
        'scheduler_verify_shell_ipc_send_wait_zero64', 'scheduler_validate_shell_ipc_endpoint64',
        'scheduler_validate_shell_ipc_send_wait64', 'scheduler_validate_shell_send_deadline64',
        'scheduler_verify_shell_deadline_zero64')
    data = source[source.index('scheduler_expected_events:'):]
    constants = '\n'.join(re.findall(r'^\w+\s+equ\s+[^\n]+', source, re.M))
    exports = '\n'.join('global '+n for n in re.findall(r'^(\w+):', data, re.M))
    body = ''.join(function(n) for n in names)
    cores = ''.join((ROOT/f'arch/x86_64/proc/{n}.asm').read_text()
                    for n in ('identity_core','syscall_profile','cpu_budget','queue_core','terminal_status'))
    return 'BITS 64\n'+constants+'\nsection .data\n'+exports+'\n'+data+'''
section .text
global owner_admit
owner_admit:
    push rdi
    push rsi
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp, 8
    cld
    call scheduler_validate_owner_terminal64
    add rsp, 8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    pop rsi
    pop rdi
    ret
'''+body+cores


class OwnerTerminalTests(unittest.TestCase):
    def test_observer_start_failure_reaps_own_vm(self):
        import run_qemu_x86_64_owner_terminal as runner
        vm=Mock()
        with tempfile.TemporaryDirectory(prefix='owner-observer-',dir=ROOT/'build/codex-agent') as directory:
            with patch.object(runner,'resolve_qemu',return_value=Path('qemu')), \
                 patch.object(runner,'symbols',return_value={}), \
                 patch.object(runner,'observer_commands',return_value='continue\n'), \
                 patch.object(runner.subprocess,'Popen',side_effect=[vm,OSError('observer unavailable')]), \
                 patch.object(runner,'terminate_bounded') as terminate:
                with self.assertRaises(OSError):runner.capture(Path('fixture.elf'),Path(directory),1,0,0,observe=True)
                terminate.assert_called_once_with(vm)
                vm.stdin.close.assert_called_once()
                vm.stdout.close.assert_called_once()

    def test_terminal_oracle(self):
        from run_qemu_x86_64_owner_terminal import validate, STATUS
        from run_qemu_x86_64_shell_exit import sample, PARENT, REAP
        for kind in range(10):
            for phase in range(5):
                for previous in (0,1):
                    n=previous+int(phase>=2)
                    good=sample(previous,False,STATUS[kind])
                    parent=PARENT.search(good)
                    prefix=good[:parent.start()]
                    if phase==4:
                        prefix+=f'REIST_X86_64_CHILD_EXIT_REAP_OK status=0000004D generation={41+previous:02X} parent=01 queued=00 rip=0000000000400010\n'
                    data=struct.pack('<6I2Q',(1,1,2,3,4)[phase],int(kind!=0),
                        ((previous+1)<<8)|1 if phase in (1,2,3) else 0,
                        int(phase==3),int(phase==3),41+previous if phase>=2 else 0,0x400010,128 if kind==9 else 0)
                    receipt='REIST_X86_64_OWNER_CONTAINED_OK v1='+data.hex().upper()+'\n'
                    good=prefix+receipt+f'REIST_X86_64_SHELL_REAP_OK status={STATUS[kind]:08X} children={n:02X} reaps={n+1:02X} parent=28 last={40+n:02X}'+good[parent.end():]
                    validate(good,kind,phase,previous)
                    bads=[good+receipt,good.replace('OWNER_CONTAINED_OK','MISSING',1),
                          good.replace('parent=28','parent=29'),good.replace('SHELL_ERROR','ABSENT'),
                          good.replace('C_KERNEL_CONTROL_OK','C_KERNEL_CONTROL_ERROR'),
                          good.replace(f'status={STATUS[kind]:08X}', 'status=00000BAD'),
                          good.replace('SHELL_REAP_OK','ABSENT'),good+REAP.pattern]
                    for offset in (0,4,8,12,16,20):
                        broken=bytearray(data);broken[offset]^=0x80
                        bads.append(good.replace(data.hex().upper(),broken.hex().upper()))
                    for bad in bads:
                        with self.assertRaises(RuntimeError):validate(bad,kind,phase,previous)

    def test_retirement_oracle(self):
        from run_qemu_x86_64_owner_terminal import validate_trace
        for kind,phase,previous in ((0,2,0),(1,3,1),(1,4,1),(7,0,0),(9,1,1)):
            rows=[(m,slot,slot+1,4 if slot==0 else 3 if m==1 else 5) for m in (1,2,3) for slot in (0,1)]
            rows += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]
            rows += [(5,s,20+s,4) for s in range(4)]
            rows += [(6,1,31,8),(6,1,32,8),(6,0,30,4)]
            n=previous+int(phase>=2);plan=(1,1,2,3,4)[phase]
            rows += [(7,1,41+i,3 if i==previous and phase in (2,3) else 8) for i in range(n)]
            rows += [(7,0,40,3 if kind else 4)]
            trace=''
            for seq,(mode,slot,gen,state) in enumerate(rows,1):
                if mode==7 and (slot==0 or gen==41+previous and phase in (2,3)):
                    trace+=f'OWNER_FENCE_OK slot={slot} plan={plan}\n'
                trace+=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=4001000 active=115000 before=100 fp=1 frames=0,0,0,0,0,0,0,0,0,0,0,0,4001000\n'
                trace+=f'TASK_FRAMES_FREE seq={seq} frame=4001000\n'
                trace+=f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=101 zero=1\n'
            trace+=f'OWNER_ZERO_OK zero=1 frames=200 initial=200 reaps={n+1} parent=40 child={40+n if n else 0}\n'
            validate_trace(trace,kind,phase,previous)
            for bad in (trace+trace,trace.replace('OWNER_FENCE_OK','MISSING',1),
                        trace.replace('zero=1','zero=0'),trace.replace('after=101','after=102',1),
                        trace.replace('frame=4001000','frame=4002000',1),trace.replace('gen=40','gen=41'),
                        trace.replace('fp=1','fp=0'),trace.replace('initial=200','initial=201'),
                        trace.replace('TASK_FRAMES_FREE','MISSING',1),trace+'TASK_FRAMES_FREE seq=30 frame=1000\n'):
                with self.assertRaises(RuntimeError):validate_trace(bad,kind,phase,previous)

    def test_actual_timer_progress(self):
        source=(ROOT/'arch/x86_64/cpu/timer_interrupt.asm').read_text()
        body=re.search(r'^timer_shell_progress64:\n.*?(?=^x86_64_timer_shell_now64:)',source,re.M|re.S).group()
        asm='BITS 64\nSHELL_MAX_TICKS equ 256\nTSC_DEADLINE_CYCLES equ 3000000000\nsection .text\nglobal timer_shell_progress64\n'+body
        c='''#include <stdint.h>
#include <stdio.h>
extern uint64_t __attribute__((sysv_abi)) timer_shell_progress64(uint64_t,uint64_t,uint64_t,uint64_t);
#define CHECK(c) do {if(!(c)){printf("line %d\\n",__LINE__);return 1;}}while(0)
int main(void) {
    const uint64_t gap=3000000000ULL;
    /* Same real128 samples on representative0.5..6GHz TSC rates. */
    for(uint64_t step=5000000;step<=60000000;step+=5000000) {
        uint64_t now=10000000,deadline=now+gap;
        for(unsigned tick=0;tick<256;tick++) {
            now+=step;
            deadline=timer_shell_progress64(now,deadline,tick,tick);
            CHECK(deadline==now+gap);
        }
        CHECK(!timer_shell_progress64(now,deadline,256,256));
    }
    CHECK(timer_shell_progress64(1,gap+1,0,0)==gap+1);
    CHECK(timer_shell_progress64(gap+1,gap+1,255,255)==2*gap+1);
    CHECK(!timer_shell_progress64(0,gap+1,0,0));
    CHECK(!timer_shell_progress64(gap+2,gap+1,1,1));
    CHECK(!timer_shell_progress64(1,gap-1,0,0));
    CHECK(!timer_shell_progress64(1,gap+1,1,0));
    CHECK(!timer_shell_progress64(1,gap+1,0,1));
    CHECK(!timer_shell_progress64(UINT64_MAX,UINT64_MAX,0,0));
    CHECK(!timer_shell_progress64(1,gap+1,UINT64_MAX,UINT64_MAX));
    CHECK(!timer_shell_progress64(1,gap+1,1ULL<<32,1ULL<<32));
    puts("OWNER_TIMER_HOST_OK finite_progress_lease_and_tick_limit=1");return 0;
}'''
        host_builder.TaskFrameTests().build(asm,c,'OWNER_TIMER_HOST')

    def test_actual_admission(self):
        source = (ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        host_builder.TaskFrameTests().build(harness(source), ROOT/'test/x86_64_owner_terminal_host.c', 'OWNER_TERMINAL_HOST')


if __name__ == '__main__': unittest.main()
