"""Paired read-only IPC witnesses must never hide extra actual plan calls."""
from pathlib import Path
import ast
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_qemu_x86_64_ipc_handoff import (validate_observations, validate_trace,
    expected_plan, plan_return_site, observer_commands, MAX_TRACE)

HH = 0xffffffff80000000
SITE = HH + 0x12340c


def pair(number=1, op=53, bits=0, generation=40):
    common = (f'id={number} op={op} bits={bits} task={HH+0x180000:x} '
              f'generation={generation} rip=400123 handle=101 ')
    return (f'IPC_ENTER {common}rsp={HH+0x190000:x} site={SITE:x} flags=2\n'
            f'IPC_LEAVE {common}rsp={HH+0x190008:x} site={SITE:x} flags=46 '
            f'result={expected_plan(op, bits)}\n'
            f'IPC_PLAN op={op} bits={bits} generation={generation}\n')


def finish(trace, calls=1):
    return trace + f'IPC_OBSERVER_DONE calls={calls}\n'


def elf_fixture():
    image = bytearray(0x200)
    image[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<I', image, 28, 52)
    struct.pack_into('<HH', image, 42, 32, 1)
    struct.pack_into('<8I', image, 52, 1, 0x100, 0x123400, 0x123400, 32, 32, 5, 4096)
    image[0x100:0x112] = (b'\x48\x8b\x3d' + struct.pack('<i', 0x170000-0x123407)
        + b'\xe8' + struct.pack('<i', 0x160000-0x12340c) + b'\x48\x3d\x00\xf0\xff\xff')
    symbols = {'scheduler_ipc_plan64.plan': HH+0x123400,
               'reist_x64_ipc_plan': HH+0x160000, 'syscall_rax': HH+0x170000}
    return image, symbols


class ObserverTests(unittest.TestCase):
    def test_pairs_and_finite_plan_model(self):
        # Literal contract outcomes, independent of the assembly source text.
        expected = {0: (1,-11,6,1,5,7), 1: (-11,4,6,2,4,7),
                    3: (-11,4,6,-11,4,7), 4: (3,-11,6,3,-11,7),
                    8: (-9,-9,6,-9,-9,-9)}
        for bits in range(17):
            for index, op in enumerate((50,51,52,53,54,58)):
                result = expected.get(bits, (-4096,)*6)[index]
                self.assertEqual(expected_plan(op,bits), result, (op,bits))
                self.assertEqual(validate_observations(finish(pair(op=op,bits=bits)),SITE), 1)
        self.assertEqual(expected_plan(99,0), -38)
        self.assertEqual(validate_observations(finish(''.join(pair(i) for i in range(1,257)),256),SITE),256)

    def test_reject_ambiguous_incomplete_or_corrupt_receipts(self):
        lines = pair().splitlines(keepends=True)
        bad = [finish(''), finish(lines[0]), finish(''.join(lines[1:])),
               finish(lines[0]+pair()), finish(pair()+lines[1]), finish(pair()+lines[2]),
               finish(pair(),2), finish(pair())+finish(''), finish(pair(2)),
               pair()+lines[0], 'x'*(MAX_TRACE+1), finish(pair())+lines[2],
               finish(pair().replace('IPC_ENTER','IPC_ENTER_BROKEN')),
               finish(pair().replace('IPC_LEAVE','IPC_LEAVE_BROKEN')),
               finish(pair().replace('IPC_PLAN','IPC_PLAN_BROKEN')),
               finish(pair().replace('IPC_PLAN op=53','IPC_PLAN op=50')),
               finish(''.join(pair(i) for i in range(1,258)),257)]
        # Change only returned observations; no identity/input/stack drift allowed.
        for before, after in [('id=1','id=2'),('op=53','op=50'),('bits=0','bits=1'),
            ('generation=40','generation=41'),('task=ffffffff80180000','task=ffffffff80180100'),
            ('rip=400123','rip=400124'),('handle=101','handle=102'),
            ('rsp=ffffffff80190008','rsp=ffffffff80190000'),
            ('site=ffffffff8012340c','site=ffffffff8012340d'),('flags=46','flags=246'),
            ('result=1','result=3')]:
            bad.append(finish(lines[0]+lines[1].replace(before,after)+lines[2]))
        bad += [finish(pair().replace('flags=2\n','flags=202\n')),
                finish(pair().replace(f'site={SITE:x}',f'site={SITE+1:x}'))]
        for index, trace in enumerate(bad):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                validate_observations(trace,SITE)

    def test_extra_real_call_still_fails_original_oracle(self):
        serial = ''.join(f'CHILD_EXIT_REAP_OK status=0000005B generation={g:02X} '
            'parent=01 queued=00 rip=0000000000400123\nREIST_X86_64_RING3_SHELL_RUN_OK\n'
            for g in (41,42))
        rows = [(53,0,g) for g in (41,42)] + [(op,bits,40)
            for _ in range(2) for op,bits in ((53,0),(53,1),(50,1),(51,0))]
        trace = ''.join(pair(i,*row) for i,row in enumerate(rows,1))
        validate_observations(finish(trace,len(rows)),SITE)
        validate_trace(serial,trace,1)
        extra = trace + pair(len(rows)+1)
        validate_observations(finish(extra,len(rows)+1),SITE)
        with self.assertRaisesRegex(RuntimeError,'parent queue/timeout'):
            validate_trace(serial,extra,1)
        # The frozen semantic gate has not changed at all.
        old = subprocess.check_output(['git','show',
            'a0f919a3:scripts/run_qemu_x86_64_ipc_handoff.py'],cwd=ROOT,text=True,timeout=10)
        current = (ROOT/'scripts/run_qemu_x86_64_ipc_handoff.py').read_text()
        def oracle(source):
            return ast.dump(next(n for n in ast.parse(source).body
                if isinstance(n,ast.FunctionDef) and n.name=='validate_trace'))
        self.assertEqual(oracle(old),oracle(current))

    def test_actual_call_site_decoder_and_rejections(self):
        image, symbols = elf_fixture()
        self.assertEqual(plan_return_site(image,symbols),SITE)
        for position in (0,4,5,28,42,44,52,56,60,68,0x100,0x107,0x108,0x10c):
            damaged = bytearray(image); damaged[position] ^= 0x80
            with self.subTest(position=position), self.assertRaises(RuntimeError):
                plan_return_site(damaged,symbols)
        for size in (0,31,51,83,0x110):
            with self.assertRaises(RuntimeError): plan_return_site(image[:size],symbols)
        for name in ('reist_x64_ipc_plan','syscall_rax'):
            with self.assertRaises(RuntimeError):
                plan_return_site(image,{**symbols,name:symbols[name]+1})
        # Two load segments claiming the same call bytes are ambiguous.
        struct.pack_into('<H',image,44,2);image[84:116]=image[52:84]
        with self.assertRaises(RuntimeError): plan_return_site(image,symbols)

    def test_read_only_hardware_observer(self):
        _, symbols = elf_fixture()
        symbols.update(scheduler_return64=HH+0x110000,scheduler_mode=HH+0x170100,
                       syscall_rcx=HH+0x170010,syscall_rdi=HH+0x170020)
        script = observer_commands(symbols,SITE)
        self.assertEqual(script.count('hbreak *'),3)
        self.assertNotIn('\nbreak *',script)
        self.assertIn('IPC_ENTER',script);self.assertIn('IPC_LEAVE',script)
        self.assertIn('IPC_OBSERVER_DONE',script)
        self.assertIn('> 256',script)
        self.assertIn('disable 1\nstepi\nenable 1\n',script)
        self.assertIn('disable 2\nstepi\nenable 2\n',script)
        self.assertIn('if *(unsigned int*)$pc != 0x0ffe8348',script)
        self.assertIn(f'if $pc != {symbols["reist_x64_ipc_plan"]+4:#x}',script)
        self.assertIn(f'if $pc != {SITE+6:#x}',script)
        for line in script.splitlines():
            if line.startswith('set $'):
                self.assertRegex(line,r'^set \$ipc_[a-z_]+ = ')
        self.assertNotIn('set {',script)


if __name__ == '__main__': unittest.main()
