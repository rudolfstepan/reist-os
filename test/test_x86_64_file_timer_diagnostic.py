"""Exercise the exact read-only register collector without starting a guest."""
from pathlib import Path
import ast
import copy
import json
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import diagnose_x86_64_file_timer as diagnostic


class TimerDiagnosticTests(unittest.TestCase):
    def fixture(self):
        symbols = {name: 0x10000 + i * 8192
                   for i, name in enumerate(diagnostic.RANGES)}
        symbols.update(scheduler_kernel_stack_bottom=0x200000,
                       scheduler_kernel_stack_top=0x204000)
        registers = dict.fromkeys(diagnostic.REGISTERS, 0)
        registers.update(rsp=0x203000, rdi=3500000000, rsi=3400000000,
                         rdx=101, rcx=101, r9=4)
        data = {symbols[n]: bytes(size) for n, size in diagnostic.RANGES.items()}
        data[registers['rsp']] = struct.pack('<32Q', 0, 0x203100, *([0] * 30))
        frame = [0] * 22
        frame[15:22] = [32, 0, 0xffff800000010000, 8, 0x202, 0x204000, 16]
        data[0x203100] = struct.pack('<22Q', *frame)
        reads = []
        def read(address, size):
            self.assertLessEqual(size, 4096)
            reads.append((address, size))
            for start, raw in data.items():
                if start <= address and address + size <= start + len(raw):
                    return raw[address-start:address-start+size]
            raise ValueError('unmapped fixture read')
        return symbols, registers, read, reads

    def test_actual_clock_frame_and_fixed_extents(self):
        symbols, registers, read, reads = self.fixture()
        record = diagnostic.collect('timer_runtime_progress64.fail', symbols,
                                    read, registers.__getitem__)
        self.assertEqual(record['registers'], registers)
        self.assertEqual(record['frame'][15:17], [32, 0])
        self.assertEqual(record['frame_address'], 0x203100)
        self.assertEqual(len(bytes.fromhex(record['memory']['scheduler_tasks'])), 4096)
        self.assertLess(len(json.dumps(record)), 16384)
        self.assertLess(len(reads), 40)

    def test_bad_frame_pointer_is_not_dereferenced(self):
        symbols, registers, read, reads = self.fixture()
        registers['rdi'] = (1 << 64) - 1
        record = diagnostic.collect('process_run_irq_validate64.bad', symbols,
                                    read, registers.__getitem__)
        self.assertIsNone(record['frame'])
        self.assertNotIn((registers['rdi'], 176), reads)

    def test_clock_frame_at_actual_kernel_stack_top(self):
        symbols, registers, read, reads = self.fixture()
        registers['rsp']=symbols['scheduler_kernel_stack_top']-200
        frame_address=symbols['scheduler_kernel_stack_top']-176
        words=[0]*25;words[1]=frame_address;words[3+15]=32;words[3+18]=8
        raw=struct.pack('<25Q',*words)
        def near_top(address,size):
            if registers['rsp']<=address and address+size<=symbols['scheduler_kernel_stack_top']:
                return raw[address-registers['rsp']:address-registers['rsp']+size]
            return read(address,size)
        record=diagnostic.collect('timer_runtime_progress64.fail',symbols,near_top,registers.__getitem__)
        self.assertEqual(len(record['stack']),25)
        self.assertEqual(record['frame_address'],frame_address)
        self.assertEqual(record['frame'][15],32)

    def test_instrumentation_is_append_only_and_bounded(self):
        old = 'python\nCONFIG={}\nUNCHANGED_OBSERVER\nend\ncontinue\n'
        code = diagnostic.instrument(old, Path('build/codex-agent/test'))
        self.assertEqual(code.split('\n# TIMER_DIAGNOSTIC_APPEND_ONLY\n')[0],
                         old.removesuffix('\nend\ncontinue\n'))
        self.assertIn('diagnostic_records >= 8', code)
        self.assertIn('len(encoded) > 16384', code)
        self.assertIn('return False', code)
        extra = code.split('# TIMER_DIAGNOSTIC_APPEND_ONLY\n', 1)[1]
        ast.parse(extra.removesuffix('\nend\ncontinue\n'))
        for forbidden in ('write_memory', 'set $', 'gdb.execute', 'sleep(',
                          'subprocess', 'continue', 'setattr('):
            self.assertNotIn(forbidden, extra.removesuffix('\nend\ncontinue\n'))
        with self.assertRaises(ValueError):
            diagnostic.instrument(old + 'unexpected', Path('build/codex-agent/test'))

    def test_legacy_final_state_is_bounded_and_has_no_invented_frame(self):
        symbols,registers,read,reads=self.fixture()
        extra={}
        for n,(name,size) in enumerate(diagnostic.LEGACY_RANGES.items()):
            symbols[name]=0x300000+n*4096;extra[symbols[name]]=bytes([n])*size
        def legacy_read(address,size):
            if address in extra:
                self.assertEqual(size,len(extra[address]));return extra[address]
            return read(address,size)
        record=diagnostic.legacy_collect('final',symbols,legacy_read,registers.__getitem__)
        self.assertIsNone(record['frame']);self.assertEqual(record['frame_address'],0)
        self.assertEqual(record['kind'],'final');self.assertLess(len(json.dumps(record)),16384)
        self.assertEqual(set(record['memory']),set(diagnostic.RANGES)|set(diagnostic.LEGACY_RANGES))
        old='set logging enabled on\npython\nCONFIG={}\nUNCHANGED_OBSERVER\nend\ncontinue\n'
        for events in (False,True):
            code=diagnostic.legacy_instrument(old,Path('build/codex-agent/test'),events)
            extra=code.split('UNCHANGED_OBSERVER\n',1)[1].removesuffix('\nend\ncontinue\n')
            ast.parse(extra)
            self.assertIn('legacy_records<2',extra);self.assertIn('legacy_events<40',extra)
            self.assertIn('install_cold(gdb.breakpoints(),cold_fail,legacy_cold)',extra)
            for forbidden in ('write_memory','set $','gdb.execute','sleep('):self.assertNotIn(forbidden,extra)

    def test_cold_frame_uses_post_call_stack_not_clobbered_rdi(self):
        symbols, registers, read, reads = self.fixture()
        registers.update(rsp=0x2030f8, rdi=0x3f6, rsi=6)
        # At serial_init, the IRQ frame immediately follows the return address.
        original_read = read
        def cold_read(address, size):
            if address == registers['rsp'] and size == 256:
                return bytes(256)
            return original_read(address, size)
        record = diagnostic.collect('cold_exception_fatal', symbols, cold_read,
                                    registers.__getitem__)
        self.assertEqual(record['frame_address'], 0x203100)
        self.assertEqual(record['frame'][15], 32)
        self.assertNotIn((0x3f6, 176), reads)

    def test_cold_routes_bind_both_calls_and_exact_return(self):
        symbols = dict(scheduler_kernel_stack_bottom=0x1000,
                       scheduler_kernel_stack_top=0x2000,
                       exception_fatal=0x3000, native_pio_fail64=0x4000,
                       native_pio_emergency_fence64=0x5000, serial_init64=0x6000)
        data = {}
        def read(address, size):
            return data[address][:size]
        for entry, expected in (('exception_fatal', 'cold_exception_fatal'),
                                ('native_pio_fail64', 'cold_native_pio_fail64')):
            address = symbols[entry]
            raw = (b'\xe8' + struct.pack('<i', 0x5000-address-5) +
                   b'\xe8' + struct.pack('<i', 0x6000-address-10))
            data.update({0x1100: struct.pack('<Q', address+10), address: raw})
            self.assertEqual(diagnostic.cold_route(symbols, read, 0x1100), expected)
            for offset in (0, 1, 5, 6):
                broken = bytearray(raw)
                broken[offset] ^= 1
                data[address] = bytes(broken)
                with self.assertRaises(ValueError):
                    diagnostic.cold_route(symbols, read, 0x1100)
            data[address] = raw
            data[0x1100] = struct.pack('<Q', address+9)
            self.assertIsNone(diagnostic.cold_route(symbols, read, 0x1100))
        self.assertIsNone(diagnostic.cold_route(symbols, read, (1 << 64)-1))

    def test_existing_callback_wrapped_once_and_always_delegated(self):
        class Hook:
            pass
        events = []
        def original():
            events.append('original')
        def capture():
            events.append('capture')
        hook = Hook()
        hook.fn = original
        diagnostic.install_cold([hook], original, capture)
        hook.fn()
        self.assertEqual(events, ['capture', 'original'])
        with self.assertRaises(ValueError):
            diagnostic.install_cold([hook], original, capture)
        hook.fn = original
        def bad_capture():
            raise RuntimeError('diagnostic read failed')
        diagnostic.install_cold([hook], original, bad_capture)
        with self.assertRaises(RuntimeError):
            hook.fn()
        self.assertEqual(events[-1], 'original')
        original_code = 'python\nCONFIG={}\nUNCHANGED_OBSERVER\nend\ncontinue\n'
        cold = diagnostic.instrument(original_code, Path('build/codex-agent/test'), cold=True)
        extra = cold.split('# TIMER_DIAGNOSTIC_APPEND_ONLY\n', 1)[1].removesuffix('\nend\ncontinue\n')
        ast.parse(extra)
        for forbidden in ('gdb.Breakpoint', 'write_memory', 'gdb.execute',
                          'TimerDiagnostic(', 'diagnostic_hooks=', 'set $'):
            self.assertNotIn(forbidden, extra)
        self.assertIn('diagnostic_records >= 1', extra)
        self.assertIn('install_cold(gdb.breakpoints(),cold_fail,diagnostic_cold_capture)', extra)

    def test_irq_regression_oracle_rejects_missing_mutated_and_reordered(self):
        for kind in diagnostic.IRQ_KINDS:
            events=[dict(event='armed',root=1),dict(event='input',kind=kind,now=7000000000,deadline=7000000001,ticks=100,eois=100)]
            if kind=='idle':
                events.append(dict(event='admitted',ticks=101,eois=101,deadline=10000000000))
                events.append(dict(event='masked_return',ready=1,deadlines=0,if_bit=0))
                serial='normal companion oracle is separate'
            else:
                events += [dict(event='injected',kind=kind),dict(event='fence',port=0x3f6,value=6,unchanged=1),
                           dict(event='fatal',reason={'expired':4,'context':0,'eoi':2}[kind],vector=32,unchanged=1,fenced=1),
                           dict(event='halt',unchanged=1)]
                serial='PROCESS_REAP_OK\n'*7+'REIST_X86_64_EXCEPTION_FATAL vector=20\n'
            def trace(items):return '\n'.join('IRQ_REGRESSION '+json.dumps(e) for e in items)
            self.assertEqual(diagnostic.validate_irq(serial,trace(events),kind),events)
            bads=[events+events,list(reversed(events))]
            for index,event in enumerate(events):
                bads.append(events[:index]+events[index+1:])
                for name in event:
                    changed=copy.deepcopy(events)
                    changed[index][name]=False if isinstance(event[name],int) else 'changed'
                    bads.append(changed)
            for bad in bads:
                with self.assertRaises(ValueError):diagnostic.validate_irq(serial,trace(bad),kind)
            with self.assertRaises(ValueError):diagnostic.validate_irq(serial,trace(events)+'\nOBSERVER_FAIL',kind)
            with self.assertRaises(ValueError):diagnostic.validate_irq(serial,'IRQ_REGRESSION []',kind)
            if kind!='idle':
                for bad_serial in (serial+'PROCESS_RUN_OK',serial+'PROCESS_REAP_OK',serial.replace('vector=20','vector=06')):
                    with self.assertRaises(ValueError):diagnostic.validate_irq(bad_serial,trace(events),kind)
            original='set logging enabled on\npython\nCONFIG={}\nUNCHANGED_OBSERVER\nend\ncontinue\n'
            code=diagnostic.irq_observer(original,Path('build/codex-agent/test'),kind)
            self.assertEqual(code.count('set logging redirect on\n'),1)
            extra=code.split('# TIMER_DIAGNOSTIC_APPEND_ONLY\n',1)[1].removesuffix('\nend\ncontinue\n')
            ast.parse(extra)
            self.assertNotIn('diagnostic_hooks=',extra)
            self.assertIn('irq_probe.enabled=False',extra)
            self.assertIn("kind=='release' and fields['gen']==1 and fields['slot']==0",extra)
            self.assertIn('irq_visits<=32',extra)


if __name__ == '__main__':
    unittest.main()
