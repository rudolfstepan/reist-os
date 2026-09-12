"""Negative oracles supplement actual context assembly and seven guest cases."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from run_qemu_x86_64_user_context import validate_receipts, instruction_offsets, RUN


class UserContextTests(unittest.TestCase):
    def test_receipt_nonacceptance(self):
        for case in range(1, 8):
            kind = 'STACK' if case <= 3 else 'CPU' if case == 4 else 'FAULT' if case == 7 else 'CONTEXT'
            prefix = 'REIST_X86_64_CHILD_'+kind+'_REAP_OK'+(' vector=01' if case == 7 else '')
            suffix = ' ticks=20 parent=07' if case == 4 else ' parent=01'
            if case == 7: suffix += ' queued=00'
            text = ''.join(prefix+f' generation={gen:02X}'+suffix+' rip=0000000000401234\n'+RUN+'\n' for gen in (41, 42))
            validate_receipts(text, case, {0x401234})
            for bad in (text.replace('generation=2A', 'generation=29'),
                        text.replace('0000000000401234', '0000000000401235'),
                        text.replace('parent=0', 'parent=F'), text+text,
                        text.replace(RUN, '', 1), text.replace('_REAP_OK', '_REAP_OK wrong'),
                        RUN+'\n'+text, text.replace('\n'+RUN, RUN+'\n', 1)):
                with self.assertRaises(RuntimeError): validate_receipts(bad, case, {0x401234})
    def test_instruction_oracle(self):
        for case, prefix in ((1,'31e4'), (2,'48bc0000000000800000'), (5,'9c48810c24004000009d')):
            setup = bytes.fromhex(prefix)
            code = setup+bytes.fromhex('b8160000000f050f0b')
            symbols = dict(child_context_probe=0, child_context_fault=len(setup)+5,
                           child_context_resume=len(setup)+7)
            self.assertEqual(instruction_offsets(code, symbols, case), {len(setup)+7})
            for i in range(len(code)):
                changed = bytearray(code); changed[i] ^= 1
                with self.assertRaises(RuntimeError): instruction_offsets(changed, symbols, case)
        for case, prefix in ((3,'48bc0000000000800000'), (6,'9c48810c24004000009d')):
            setup = bytes.fromhex(prefix)
            code = setup+bytes.fromhex('f390ebfc')
            symbols = dict(child_context_probe=0, child_context_spin=len(setup), child_context_spin_end=len(code))
            self.assertEqual(instruction_offsets(code, symbols, case), {len(setup), len(setup)+2})
            for i in range(len(code)):
                changed=bytearray(code); changed[i]^=1
                with self.assertRaises(RuntimeError): instruction_offsets(changed,symbols,case)
    def test_trusted_entry_before_local_reap(self):
        source = (ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        admission = source.split('scheduler_shell_admit_syscall_context64:',1)[1].split('scheduler_context_apply64:',1)[0]
        self.assertLess(admission.index('scheduler_validate_shell_syscall_profile64'), admission.index('SYSCALL_CONTEXT_USER_RSP'))
        self.assertIn('call scheduler_retire_shell_context64', admission)
        route=source.split('scheduler_retire_shell_context64:',1)[1].split('scheduler_retire_shell_owner64:',1)[0]
        self.assertIn('jne scheduler_retire_shell_child_fault64.classified', route)
        self.assertNotIn('mov rsp, [rel scheduler_syscall_context', admission)
        for bit in ('0x244fd7', '0x254fd7', 'SHELL_CONTEXT_STATUS'):
            self.assertIn(bit, source)
        for path in ('arch/x86_64/cpu/exceptions.asm', 'arch/x86_64/proc/cooperative_scheduler.asm'):
            self.assertIn('cld', (ROOT/path).read_text())

    def test_flags_and_trap_instruction_oracles(self):
        code = bytes.fromhex('9c48810c24000424009db8160000000f05'
            '9c5a4883f8f3753481e20004240081fa000424007526'
            'b82800000031ff31f631d20f054885c07514'
            '9c5a81e20004240081fa000424007504f390ebec0f0b')
        symbols = dict(child_context_probe=0, child_context_fault=15, child_context_resume=17,
                       child_context_spin=57, child_context_spin_end=77, child_context_fail=77)
        self.assertEqual(instruction_offsets(code, symbols, 4), {57+i for i in (0,1,2,8,14,16,18)})
        for i in range(len(code)):
            changed=bytearray(code); changed[i]^=1
            with self.assertRaises(RuntimeError): instruction_offsets(changed,symbols,4)
        code=bytes.fromhex('9c48810c24000100009d900f0b')
        symbols=dict(child_context_probe=0, child_context_fault=10, child_context_resume=11)
        self.assertEqual(instruction_offsets(code,symbols,7),{11})
        for i in range(len(code)):
            changed=bytearray(code); changed[i]^=1
            with self.assertRaises(RuntimeError): instruction_offsets(changed,symbols,7)


if __name__ == '__main__': unittest.main()
