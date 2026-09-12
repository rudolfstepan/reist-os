"""Execute the real final-verifier assembly, not a model of the scheduler."""
from pathlib import Path
import re, subprocess, sys, unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'test'))
sys.path.insert(0, str(ROOT/'scripts'))
import test_x86_64_task_frames as host_builder


def harness(source):
    def function(name):
        return re.search(r'^'+name+r':\n.*?(?=^[A-Za-z_][\w]*:|\Z)', source, re.M|re.S).group()
    constants = '\n'.join(re.findall(r'^\w+\s+equ\s+[^\n]+', source, re.M))
    data = source[source.index('scheduler_expected_events:'):]
    # All production BSS offsets, sizes, zero guards and identity core retained.
    exported = re.findall(r'^(\w+):', data, re.M)
    body = ''.join(function(n) for n in ('scheduler_verify_final_events64',
        'scheduler_verify_shell_ipc_zero64', 'scheduler_verify_shell_deadline_zero64',
        'scheduler_identity_apply64'))
    return 'BITS 64\n'+constants+'\nsection .data\n'+'\n'.join('global '+n for n in exported)+'\n'+data+'''
section .text
global final_verify
final_verify:
    ; Host entry is Win64; the extracted production body remains SysV.
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
    call scheduler_verify_final_events64
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
'''+body+(ROOT/'arch/x86_64/proc/identity_core.asm').read_text()


class ShellExitTests(unittest.TestCase):
    def test_actual_final_verifier(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        host_builder.TaskFrameTests().build(harness(source), ROOT/'test/x86_64_shell_exit_host.c', 'SHELL_EXIT_HOST')

    def test_retained_old_defect(self):
        old=subprocess.check_output(['git','show','1e7645c8:arch/x86_64/proc/cooperative_scheduler.asm'],cwd=ROOT,text=True,timeout=10)
        c=(ROOT/'test/x86_64_shell_exit_host.c').read_text()
        host_builder.TaskFrameTests().build(harness(old), '#define LEGACY 1\n'+c, 'SHELL_EXIT_LEGACY')

    def test_runtime_oracle(self):
        from run_qemu_x86_64_shell_exit import validate, sample
        for n in range(3):
            for info in (False, True):
                for status in (0,42,0x80000000,0xffffffff):
                    good=sample(n,info,status)
                    validate(good,n,info,status)
                    for bad in (good+good,good.replace('reaps=', 'absent=',1),
                        good.replace('status='+f'{status:08X}', 'status=00000001'),
                        good.replace('parent=28','parent=29'),good.replace('last=', 'missing=',1),
                        good.replace('C_KERNEL_CONTROL_OK','C_KERNEL_CONTROL_ERROR'),
                        good.replace('SHELL_EXIT_OK','SHELL_EXIT_MISSING')):
                        with self.assertRaises(RuntimeError):validate(bad,n,info,status)
        good=sample(1,True,0)
        for bad in (good.replace('generation=29','generation=2A'),good.replace('0000004D','0000004E'),
                    good.replace('CHILD_EXIT_REAP_OK','CHILD_FAULT_REAP_OK'),
                    good.replace('queued=00','queued=01')):
            with self.assertRaises(RuntimeError):validate(bad,1,True,0)

    def test_loader_metadata_is_not_a_code_exception(self):
        from run_qemu_x86_64_shell_exit import loader_code
        import struct
        # Extract the old loader's actual .text using its ELF32 section table;
        # no synthetic opcode corpus and no current candidate needed.
        path=ROOT/'build/codex-agent/r83r-instruction/normal/x86_64/elf64_loader.o'
        data=path.read_bytes()
        self.assertEqual(data[:6],b'\x7fELF\x01\x01')
        offset=struct.unpack_from('<I',data,32)[0]
        size,count=struct.unpack_from('<HH',data,46)
        self.assertEqual(size,40)
        text=None
        for i in range(count):
            header=struct.unpack_from('<10I',data,offset+i*size)
            if header[1]==1 and header[2]&4:
                self.assertIsNone(text)
                text=data[header[4]:header[4]+header[5]]
        self.assertIsNotNone(text)
        loader_code(text,3856)
        for index in (0,0x4b,0x150,0x2da,0x30c,0x459,0x46e,len(text)-1):
            bad=bytearray(text);bad[index]^=1
            with self.assertRaises(RuntimeError):loader_code(bad,3856)
        with self.assertRaises(RuntimeError):loader_code(text,3857)
        with self.assertRaises(RuntimeError):loader_code(text[:-1],3856)

if __name__=='__main__':unittest.main()
