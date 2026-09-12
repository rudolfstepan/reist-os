"""Execute the actual native run admission/ownership code, not a model."""
from pathlib import Path
import re, struct, sys, tempfile, unittest
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'test'), str(ROOT/'scripts')]
import test_x86_64_task_frames as host_builder


class ProcessRunTests(unittest.TestCase):
    @staticmethod
    def sample(case):
        import run_qemu_x86_64_process_run as r
        from run_qemu_x86_64_boot import REQUIRED_MARKERS
        common=[m for m in REQUIRED_MARKERS if 'SHELL' not in m]
        cut=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
        serial='\n'.join(common[:cut])+'\n'
        for run in range(2):
            for slot in range(4):
                bad=case!=0 and slot==(case+run)%4
                status=r.STATUS[case] if bad else r.NORMAL[slot]
                quota=4+slot*4+run*16
                data=struct.pack('<4I2Q',slot,run*4+slot+1,status,3 if bad else 4,
                                 quota if bad and case==8 else 0,0x400120)
                serial+='REIST_X86_64_PROCESS_REAP_OK v1='+data.hex().upper()+'\n'
            serial+=r.DONE+'\n'
        return serial+'\n'.join(common[cut:])+'\n'+r.SUCCESS+'\n'

    def test_serial_oracle(self):
        import run_qemu_x86_64_process_run as r
        for case in range(9):
            serial=self.sample(case);self.assertEqual(len(r.validate(serial,case)),8)
            first=r.REAP.search(serial)
            bads=[serial+serial,serial.replace(r.DONE,'MISSING',1),serial.replace(r.SUCCESS,'MISSING'),
                  serial.replace('C_KERNEL_CONTROL_OK','C_KERNEL_CONTROL_ERROR'),serial+first[0]]
            for offset in (0,4,8,12,16,24):
                data=bytearray.fromhex(first[1]);data[offset]^=0x80
                bads.append(serial[:first.start(1)]+data.hex().upper()+serial[first.end(1):])
            # Bad RIP can still lie within the image; mutate to an unmapped window.
            bads.pop() # replace the incidental in-window low-bit mutation
            data=bytearray.fromhex(first[1]);struct.pack_into('<Q',data,24,0x500000)
            bads.append(serial.replace(first[1],data.hex().upper(),1))
            for bad in bads:
                with self.assertRaises(RuntimeError):r.validate(bad,case)

    def test_frame_oracle(self):
        import run_qemu_x86_64_process_run as r
        for case in range(9):
            rows=r.validate(self.sample(case),case)
            records=[(m,s,s+1,4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)]
            records += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]
            records += [(5,s,20+s,4) for s in range(4)]+[(6,1,31,8),(6,1,32,8),(6,0,30,4)]
            records += [(8,x['slot'],x['generation'],x['state']) for x in rows]
            frames=[0,0x4001000]+[0]*6+[0x4002000,0x4006000,0x4005000,0x4004000,0x4003000]
            trace=''
            for seq,(mode,slot,gen,state) in enumerate(records,1):
                if mode==8:trace+=f'PROCESS_FENCE_OK seq={seq} slot={slot} gen={gen}\n'
                trace+=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=4003000 active=115000 before=100 fp=1 frames='+','.join(f'{f:x}' for f in frames)+'\n'
                trace+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in frames if f)
                trace+=f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=106 zero=1\n'
                if seq in (21,25):
                    run=1 if seq==21 else 2
                    trace+=f'PROCESS_ZERO_OK run={run} zero=1 free=200 initial=200 reaps=4 generation={run*4} ticks=32\n'
            r.validate_trace(trace,rows)
            for bad in (trace+trace,trace.replace('PROCESS_FENCE_OK','MISSING',1),trace.replace('zero=1','zero=0',1),
                        trace.replace('after=106','after=107',1),trace.replace('frame=4001000','frame=4002000',1),
                        trace.replace('initial=200','initial=199',1),trace.replace('fp=1','fp=0',1),
                        trace.replace('gen=8','gen=7'),trace.replace('TASK_FRAMES_FREE','MISSING',1),
                        trace+'TASK_FRAMES_FREE seq=25 frame=1000\n'):
                with self.assertRaises(RuntimeError):r.validate_trace(bad,rows)

    def test_observer_start_cleanup(self):
        import run_qemu_x86_64_process_run as r
        vm=Mock()
        with tempfile.TemporaryDirectory(prefix='process-observer-',dir=ROOT/'build/codex-agent') as folder:
            with patch.object(r,'resolve_qemu',return_value=Path('qemu')),patch.object(r,'symbols',return_value={}), \
                 patch.object(r,'observer_commands',return_value='continue\n'), \
                 patch.object(r.subprocess,'Popen',side_effect=[vm,OSError('missing debugger')]), \
                 patch.object(r,'terminate_bounded') as stop:
                with self.assertRaises(OSError):r.capture(Path('fixture.elf'),Path(folder),observe=True)
                stop.assert_called_once_with(vm);vm.stdin.close.assert_called_once();vm.stdout.close.assert_called_once()

    def test_actual_admission(self):
        source = (ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body = source.split('process_run_admit64:', 1)[1].split('process_run_validate64:', 1)[0]
        asm = '''BITS 64
section .text
global process_run_admit64
process_run_admit64:
''' + body
        host_builder.TaskFrameTests().build(asm, ROOT/'test/x86_64_process_run_host.c', 'PROCESS_RUN_HOST')

    def test_actual_ownership(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        inc=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        def function(text,name):
            return re.search(r'^'+name+r':\n.*?(?=^[A-Za-z_][\w]*:|^global |\Z)',text,re.M|re.S).group()
        constants='\n'.join(re.findall(r'^\w+\s+equ\s+[^\n]+',source,re.M))
        data=source[source.index('scheduler_expected_events:'):]
        data=data.replace('scheduler_state_begin:', 'process_run_host_begin:\nscheduler_state_begin:')
        exports='\n'.join('global '+n for n in re.findall(r'^(\w+):',data,re.M))
        body=''.join(function(inc,n) for n in ('process_run_admit64','process_run_validate64','process_run_frames64',
                                             'process_run_tick_admit64','process_run_wake64'))
        body+=''.join(function(source,n) for n in ('scheduler_identity_apply64','scheduler_profile_apply64',
                                                 'scheduler_budget_apply64','scheduler_queue_apply64',
                                                 'scheduler_runqueue_enqueue64'))
        cores=''.join((ROOT/f'arch/x86_64/proc/{n}.asm').read_text() for n in
                      ('identity_core','syscall_profile','cpu_budget','queue_core'))
        asm='BITS 64\n'+constants+'\nsection .data\n'+exports+'''
global process_run_host_end
'''+data+'''
process_run_host_end:
section .text
global run_ownership
run_ownership:
    push rdi
    push rsi
    sub rsp, 8
    call process_run_validate64
    add rsp, 8
    pop rsi
    pop rdi
    ret
global run_wake
run_wake:
    push rbx
    push rbp
    push rdi
    push rsi
    push r12
    push r13
    push r14
    push r15
    sub rsp, 8
    mov esi, ecx
    call process_run_validate64
    test eax, eax
    jz .done
    call process_run_tick_admit64
    test eax, eax
    jz .done
    call process_run_wake64
.done:
    add rsp, 8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rsi
    pop rdi
    pop rbp
    pop rbx
    ret
'''+body+cores
        c=(ROOT/'test/x86_64_process_run_host.c').read_text()
        c='#define PROCESS_OWNERSHIP 1\n'+c.replace('../arch/x86_64/proc/process_run.h',
                                                 (ROOT/'arch/x86_64/proc/process_run.h').as_posix())
        host_builder.TaskFrameTests().build(asm,c,'PROCESS_RUN_HOST')


if __name__ == '__main__': unittest.main()
