"""Execute production task-family admission and full-width profile authority."""
from pathlib import Path
import sys, unittest,re,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host

class FamilyTests(unittest.TestCase):
    @staticmethod
    def sample(case,oom=None):
        import run_qemu_x86_64_task_family as r
        common=[m for m in r.REQUIRED_MARKERS if 'SHELL' not in m]
        cut=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
        serial='\n'.join(common[:cut])+'\n';trace='';seq=0
        baseline=[(m,s,s+1,4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)]
        baseline += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]+[(5,s,20+s,4) for s in range(4)]
        baseline += [(6,0,30,4),(6,1,31,8),(6,1,32,8)]
        def frames(mode,slot,gen,state):
            nonlocal seq
            seq+=1
            fs=[0,0,0x100001000,0x100002000,0,0,0,0,0x100003000,0x100004000,0x100005000,0x100006000,0x100007000]
            text=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=100007000 active=13e000 before=1000000 fp=1 frames='+','.join(f'{f:x}' for f in fs)+'\n'
            text+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in fs if f)
            return text+f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=1000007 zero=1\n'
        for row in baseline:trace+=frames(*row)
        count=4 if case==1 else 9 if case==4 else 10
        for run in range(2):
            order=[1,3,4,2] if case==1 else list(range(3,count+1))+[1,2]
            for n in order:
                slot=n-1 if n<=4 else 2;gen=run*count+n
                if case==1 and slot==0:status,state=134,3
                elif slot==3 or case==1 and slot==2:status,state=0,3
                elif slot==2 and case in (2,3):status,state=(134 if case==2 else 256),3
                else:status,state=40+slot,4
                trace+=f'FAMILY_START slot={slot} gen={gen} image={3+slot} high=1 wx=1 argv=1\n'
                if slot==3 or case==1 and slot==2:
                    trace+=f'FAMILY_CANCEL slot={slot} gen={gen} state=6 ipc={int(slot==3 and case!=5)} heap={int(case==5)} reason={3 if case==1 else 2}\n'
                trace+=f'FAMILY_FENCE slot={slot} gen={gen} ipc=1 heap=1 profile=1\n'+frames(8,slot,gen,state)
                receipt=struct.pack('<4I2Q',slot,gen,status,state,32 if slot==2 and case==3 else 1,0x40002b)
                serial+='REIST_X86_64_PROCESS_REAP_OK v1='+receipt.hex().upper()+'\n'
            trace+=f'PROCESS_ZERO_OK run={run+1} zero=1 free=1000010 initial=1000010 reaps={count} generation={(run+1)*count} ticks={100+run*100}\nFAMILY_ZERO run={run+1} complete=1\n'
            if oom is not None:trace+=f'FAMILY_OOM acquired={oom}\n'
            serial+=r.process.DONE+'\n'
        return serial+'\n'.join(common[cut:])+'\n'+r.process.SUCCESS+'\n',trace

    def test_guest_oracle_mutations(self):
        import run_qemu_x86_64_task_family as r
        for case in range(6):
            oom=3 if case==4 else None
            serial,trace=self.sample(case,oom);self.assertGreater(r.validate(serial,trace,case,oom),0)
            for label in ('TASK_FRAMES_BEFORE','TASK_FRAMES_AFTER','TASK_FRAMES_FREE','FAMILY_START','FAMILY_FENCE','PROCESS_ZERO_OK','FAMILY_ZERO','FAMILY_CANCEL'):
                with self.assertRaises(ValueError):r.validate(serial,trace.replace(label,'MISSING',1),case,oom)
            for before,after in (('high=1','high=0'),('wx=1','wx=0'),('argv=1','argv=0'),('ipc=1 heap=1','ipc=0 heap=1'),('after=1000007','after=1000008'),('zero=1','zero=0'),('initial=1000010','initial=1000009'),('image=5','image=4'),('mode=1','mode=0'),('fp=1','fp=0')):
                with self.assertRaises(ValueError):r.validate(serial,trace.replace(before,after,1),case,oom)
            for bad in (serial+serial,serial.replace(r.process.SUCCESS,'MISSING'),serial+r.FAILURES[0],serial.replace(r.process.DONE,'MISSING',1)):
                with self.assertRaises(ValueError):r.validate(bad,trace,case,oom)
            first=r.process.REAP.search(serial)
            for offset in (0,4,8,12,16,24):
                data=bytearray.fromhex(first[1]);data[offset+3]^=128
                with self.assertRaises(ValueError):r.validate(serial.replace(first[1],data.hex().upper(),1),trace,case,oom)

    def test_evidence_scope(self):
        import run_qemu_x86_64_task_family as r
        relative=Path('build/codex-agent/r83ae-family/guests')
        absolute=ROOT/relative
        self.assertEqual(r.evidence_directory(relative),absolute.resolve())
        self.assertEqual(r.evidence_directory(absolute),absolute.resolve())
        self.assertEqual((r.evidence_directory(relative)/'build-1').relative_to(ROOT),relative/'build-1')
        for path in (ROOT,ROOT/'build',ROOT/'build/codex-agent/../outside',ROOT.parent):
            with self.assertRaises(ValueError):r.evidence_directory(path)

    def test_actual_admission_and_profiles(self):
        family=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        pure=family.split('; RUNTIME ADAPTER')[0]
        profiles=(ROOT/'arch/x86_64/proc/syscall_profile.asm').read_text()
        names=('family_record64','family_initialize64','family_validate_runtime64','family_terminal64','family_reaped64','family_wait_expired64')
        core=''.join(re.search(r'^'+n+r':\n.*?(?=^[A-Za-z_]\w*:|^section |\Z)',family,re.M|re.S).group() for n in names)
        data=family[family.index('family_begin:'):family.index('section .text\n%endif')]
        externals={'process_run_plan':144,'scheduler_tasks':1024,'process_run_generations':16,
            'process_heap_retire_mask':4,'scheduler_current_slot':4,'scheduler_last_tick':8,
            'scheduler_deadline_entries':64,'process_run_receipt':32}
        data='core_begin:\n'+data+''.join('alignb 8\n'+n+': resb '+str(size)+'\n' for n,size in externals.items())+'core_end:\n'
        exports=''.join('global '+n+'\n' for n in re.findall(r'^(\w+):',data,re.M))
        constants='''TASK_STATE equ 0
TASK_GENERATION equ 8
TASK_RAX equ 232
TASK_FREE equ 0
TASK_READY equ 1
TASK_RUNNING equ 2
TASK_FAULTED equ 3
TASK_BLOCKED equ 6
'''
        adapter='''global family_expire_test
family_expire_test:
    push rbp
    push r12
    sub rsp,8
    mov rbp,rsi
    mov eax,edi
    shl eax,8
    lea r12,[rel scheduler_tasks]
    add r12,rax
    call family_wait_expired64
    add rsp,8
    pop r12
    pop rbp
    ret
scheduler_fail:
    ud2
'''
        asm='BITS 64\n'+constants+'section .bss\nalignb 8\n'+exports+data+'section .text\n'+pure+'\n'+profiles
        asm+='\n'+(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        asm+='\n'+''.join('global '+n+'\n' for n in names)+core+adapter
        host.TaskFrameTests().build(asm,
            ROOT/'test/x86_64_task_family_host.c','TASK_FAMILY_HOST')

if __name__=='__main__':unittest.main()
