"""Bounded ELF64 dependency inventory: malformed files and reachable imports."""
from pathlib import Path
import struct
import sys
import unittest
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_x86_64_desktop_inventory import (
    HEADER, SECTION, SYMBOL, RELA, inspect_object, dependency_paths)


def fixture():
    strings = b'\0main\0x86os_display_info\0state\0unused_api\0dead\0'
    names = b'\0.names\0.strings\0.symbols\0.text\0.rela.text\0.bss\0.dead\0.rela.dead\0'
    def symbol(name, section):
        return SYMBOL.pack(strings.index(name.encode() + b'\0'), 0x10, 0, section, 0, 8)
    sym = bytes(24) + symbol('main', 4) + symbol('x86os_display_info', 0) + \
        symbol('state', 6) + symbol('unused_api', 0) + symbol('dead', 7)
    parts = [(0, 0, b'', 0, 0, 0, 0, 0, ''),
             (3, 0, names, 0, 0, 0, 1, 0, '.names'),
             (3, 0, strings, 0, 0, 0, 1, 0, '.strings'),
             (2, 0, sym, 2, 1, 24, 8, 0, '.symbols'),
             (1, 6, bytes(16), 0, 0, 0, 16, 0, '.text'),
             (4, 0, RELA.pack(0, (2 << 32) | 1, 0) + RELA.pack(8, (3 << 32) | 1, 0),
              3, 4, 24, 8, 0, '.rela.text'),
             (8, 3, b'', 0, 0, 0, 8, 1024, '.bss'),
             (1, 6, bytes(8), 0, 0, 0, 8, 0, '.dead'),
             (4, 0, RELA.pack(0, (4 << 32) | 1, 0), 3, 7, 24, 8, 0, '.rela.dead')]
    data = bytearray(64)
    sections = []
    for kind, flags, raw, link, info, entsize, align, bss, name in parts:
        data.extend(bytes((-len(data)) % max(align, 1)))
        sections.append((names.index(name.encode() + b'\0') if name else 0,
                         kind, flags, 0, len(data), bss or len(raw), link, info, align, entsize))
        data.extend(raw)
    data.extend(bytes((-len(data)) % 8))
    shoff = len(data)
    for section in sections:
        data.extend(SECTION.pack(*section))
    data[:64] = HEADER.pack(b'\x7fELF\x02\x01\x01' + bytes(9), 1, 62, 1,
                           0, 0, shoff, 0, 64, 0, 0, 64, len(sections), 1)
    return data


class DesktopInventoryTests(unittest.TestCase):
    def test_bounded_compile_batches(self):
        from build_x86_64_desktop_inventory import compile_batches
        barrier = threading.Barrier(4, timeout=5)
        lock = threading.Lock()
        active = 0
        peak = 0
        finished = []
        def compile_one(index):
            nonlocal active, peak
            with lock:
                if index >= 4:
                    self.assertTrue(set(range(4)).issubset(finished))
                active += 1
                peak = max(peak, active)
            barrier.wait()
            with lock:
                active -= 1
                finished.append(index)
        compile_batches(list(range(8)), compile_one, 4)
        self.assertEqual(peak, 4)
        self.assertEqual(active, 0)
        self.assertEqual(sorted(finished), list(range(8)))
        sequential = []
        compile_batches(list(range(6)), sequential.append, 1)
        self.assertEqual(sequential, list(range(6)))

    def test_compile_failure_joins_batch_and_stops(self):
        from build_x86_64_desktop_inventory import compile_batches
        barrier = threading.Barrier(4, timeout=5)
        finished = []
        failure = RuntimeError('compiler failed')
        def compile_one(index):
            barrier.wait()
            if index == 0:
                raise failure
            finished.append(index)
        with self.assertRaises(RuntimeError) as caught:
            compile_batches(list(range(8)), compile_one, 4)
        self.assertIs(caught.exception, failure)
        self.assertEqual(sorted(finished), [1, 2, 3])

    def test_compile_admission_before_work(self):
        from build_x86_64_desktop_inventory import compile_batches
        calls = []
        for count, jobs in ((0, 4), (65, 4), (1, 0), (1, 5), (1, True), (1, 1.5)):
            with self.subTest(count=count, jobs=jobs), self.assertRaises(ValueError):
                compile_batches(list(range(count)), calls.append, jobs)
        self.assertEqual(calls, [])

    def test_dependency_paths(self):
        self.assertEqual([str(p).replace('\\', '/') for p in dependency_paths(
            'D:/build/file.o: D:/source/file.c \\\n  C:/tool/header.h D:/space\\ name/local.h\n')],
            ['D:/source/file.c', 'C:/tool/header.h', 'D:/space name/local.h'])
        for text in ('', 'target:', 'a: x\nb: y', 'a: ' + 'x ' * 4097):
            with self.assertRaises(ValueError):
                dependency_paths(text)

    def test_reachable_platform_and_static_memory(self):
        result = inspect_object(fixture())
        self.assertEqual(result['reachable_imports'], ['x86os_display_info'])
        self.assertEqual(result['allocated_section_bytes'], 1040)
        self.assertEqual(result['zero_fill_bytes'], 1024)
        self.assertFalse(result['bootable'])
        self.assertFalse(result['runtime_accepted'])

    def test_reject_non_native_or_executable(self):
        for offset, fmt, value in ((4, 'B', 1), (5, 'B', 2), (16, 'H', 2),
                                   (18, 'H', 3), (40, 'Q', 2**64 - 1),
                                   (60, 'H', 0), (62, 'H', 65535)):
            with self.subTest(offset=offset):
                raw = fixture()
                struct.pack_into('<' + fmt, raw, offset, value)
                with self.assertRaises(ValueError):
                    inspect_object(raw)

    def test_reject_section_symbol_and_relocation_corruption(self):
        # Section field offsets: file offset24, size32, link40, info44, entsize56.
        for index, offset, fmt, value in ((4, 24, 'Q', 2**64 - 1),
                (4, 32, 'Q', 2**64 - 1), (3, 40, 'I', 99), (3, 56, 'Q', 1),
                (5, 40, 'I', 0), (5, 44, 'I', 99), (5, 56, 'Q', 8),
                (4, 48, 'Q', 3)):
            with self.subTest(index=index, offset=offset):
                raw = fixture()
                shoff = HEADER.unpack_from(raw)[6]
                struct.pack_into('<' + fmt, raw, shoff + index * 64 + offset, value)
                with self.assertRaises(ValueError):
                    inspect_object(raw)
        for address, symbol in ((16, 2), (0, 999)):
            raw = fixture()
            shoff = HEADER.unpack_from(raw)[6]
            at = SECTION.unpack_from(raw, shoff + 5 * 64)[4]
            RELA.pack_into(raw, at, address, (symbol << 32) | 1, 0)
            with self.assertRaises(ValueError):
                inspect_object(raw)


if __name__ == '__main__':
    unittest.main()
