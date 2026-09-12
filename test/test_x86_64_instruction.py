from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_qemu_x86_64_instruction import validate

class InstructionTests(unittest.TestCase):
    def test_receipt_oracle(self):
        for case in (1,2,3):
            serial=''
            for g in (41,42):
                kind={1:f'EXIT_REAP_OK status=0000004D generation={g:02X} parent=07 queued=00 rip=0000000000400444',
                      2:f'CPU_REAP_OK generation={g:02X} ticks=20 parent=07 rip=0000000000401002',
                      3:f'CONTEXT_REAP_OK generation={g:02X} parent=01 rip=0000000000402000'}[case]
                serial+='REIST_X86_64_CHILD_'+kind+'\nREIST_X86_64_RING3_SHELL_RUN_OK\nINSTRUCTION_OK\n'
            validate(serial,case,0x400444)
            for bad in (serial+serial,serial.replace('INSTRUCTION_OK','',1),serial.replace('generation=2A','generation=29'),
                        serial.replace('parent=07','parent=00').replace('parent=01','parent=00'),serial.replace('rip=000000000040','rip=000000000041')):
                with self.assertRaises(RuntimeError):validate(bad,case,0x400444)

    def test_context_admission_before_capture(self):
        s=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body=s.split('scheduler_context_apply64:',1)[1].split('scheduler_budget_apply64:',1)[0]
        self.assertLess(body.index('call scheduler_validate_task_instruction64'),body.index('call reist_x64_context_apply'))
        for name,end in [('scheduler_shell_admit_syscall_context64','scheduler_context_apply64'),
                         ('x86_64_scheduler_shell_timer_validate64','x86_64_scheduler_shell_timer_tail64')]:
            part=s.split(name+':',1)[1].split(end+':',1)[0]
            self.assertIn('call scheduler_validate_task_instruction64',part)
            self.assertNotIn('call x86_64_elf64_address_flags64',part)
        build=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text()
        self.assertIn('InstructionCase is exclusive',build)
        make=(ROOT/'Makefile').read_text()
        self.assertEqual(make.count('-DX86_64_INSTRUCTION_CASE=$(X86_64_INSTRUCTION_CASE)'),2)

if __name__=='__main__':unittest.main()
