"""Real filesystem/hash negative tests; no image parser or VM is mocked."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_x86_64_reference_artifacts as guard


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'build')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'build/programs').mkdir(parents=True)
        for name, data in {'main.img': b'accepted main', 'vmware.img': b'accepted vmware',
                           'fb.img': b'historical framebuffer',
                           'build/programs/SHELL.PRG': b'shell',
                           'build/programs/BROWSER.PRG': b'browser'}.items():
            (self.root / name).write_bytes(data)
        self.pins = {name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                     for name in ('main.img', 'vmware.img', 'fb.img')}
        # Independent fixed reference grammar, not the production serializer.
        canonical = ('BROWSER.PRG:' + hashlib.sha256(b'browser').hexdigest() + '\n' +
                     'SHELL.PRG:' + hashlib.sha256(b'shell').hexdigest() + '\n')
        self.programs = hashlib.sha256(canonical.encode()).hexdigest()

    def check(self):
        return guard.verify(self.root, self.pins, 2, self.programs)

    def test_accepted_and_read_only(self):
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.check()['artifacts'], self.pins)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_each_image_and_program_changed_or_missing(self):
        for name in (*self.pins, 'build/programs/SHELL.PRG', 'build/programs/BROWSER.PRG'):
            path = self.root / name
            original = path.read_bytes()
            for value in (original + b'x', b'', bytes([original[0] ^ 1]) + original[1:]):
                with self.subTest(name=name, value=value):
                    path.write_bytes(value)
                    with self.assertRaises(ValueError):
                        self.check()
            path.unlink()
            with self.assertRaises((OSError, ValueError)):
                self.check()
            path.write_bytes(original)
        self.check()

    def test_inventory_add_rename_subdirectory_and_case(self):
        directory = self.root / 'build/programs'
        for name in ('EXTRA.PRG', 'unexpected.txt', 'lower.prg'):
            path = directory / name
            path.write_bytes(b'new')
            with self.assertRaises(ValueError):
                self.check()
            path.unlink()
        (directory / 'subdir').mkdir()
        with self.assertRaises(ValueError):
            self.check()
        (directory / 'subdir').rmdir()
        (directory / 'SHELL.PRG').rename(directory / 'RENAMED.PRG')
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_pin_no_learning(self):
        for value in (None, '', '0' * 63, 'G' * 64):
            with self.subTest(value=value):
                self.pins['main.img'] = value
                with self.assertRaises(ValueError):
                    self.check()
                self.assertEqual(self.pins['main.img'], value)
        with self.assertRaises(ValueError):
            guard.verify(self.root, {}, 2, self.programs)

    def test_unreadable_and_bounded_files(self):
        with patch.object(Path, 'open', side_effect=PermissionError('locked by VM')):
            with self.assertRaises(PermissionError):
                self.check()
        with patch.object(guard, 'MAX_FILE_BYTES', 2):
            with self.assertRaises(ValueError):
                self.check()


if __name__ == '__main__':
    unittest.main()
