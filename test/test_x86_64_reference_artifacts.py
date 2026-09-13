"""Real filesystem/hash negative tests; no image parser or VM is mocked."""
from pathlib import Path
import hashlib
import json
import subprocess
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_x86_64_reference_artifacts as guard
import qualify_x86_64_reference_artifacts as qualification


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


class QualificationTests(unittest.TestCase):
    def test_exact_platform_matched_matrix(self):
        cases = qualification.reference_cases()
        self.assertEqual(cases, [
            ('vmware-main-apic', 'vmware', ROOT / qualification.DISKS[0], False),
            ('vmware-package-apic', 'vmware', ROOT / qualification.DISKS[1], False),
            ('qemu-apic', 'qemu', qualification.QEMU_REBUILD / 'reist-os.img', False),
            ('qemu-pit', 'qemu', qualification.QEMU_REBUILD / 'reist-os.img', True),
        ])
        self.assertEqual(len({c[0] for c in cases}), 4)
        self.assertTrue(all(not pit for _, target, _, pit in cases if target == 'vmware'))

    def test_vmware_requires_actual_timer_backend(self):
        apic = '[INFO][apic] Timer calibrated to 10 ms (40514 ticks) on vector 240'
        pit = '[WARN][apic] Local APIC unavailable; using PIT scheduler fallback'
        qualification.vmware_timer_backend(apic, False)
        qualification.vmware_timer_backend(pit, True)
        for text, expected_pit in ((apic, True), (pit, False), ('cpuid.1.edx = mask', True),
                                   ('', False), (apic + '\n' + pit, True),
                                   (apic + '\n' + pit, False)):
            with self.assertRaises(ValueError):
                qualification.vmware_timer_backend(text, expected_pit)

    def test_vmware_cleanup_after_failed_or_ambiguous_start(self):
        vm = qualification.VmwareCopy.__new__(qualification.VmwareCopy)
        vm.vmx = Path('test.vmx')
        for failure in (SimpleNamespace(returncode=1, stdout='cancelled', stderr=''),
                        subprocess.TimeoutExpired('vmrun', 20)):
            vm.inventory = Mock(return_value=[])
            vm.command = Mock(side_effect=failure if isinstance(failure, Exception) else None,
                              return_value=failure)
            vm.stop = Mock()
            with patch.object(qualification, 'vmware_processes', return_value=[]), \
                 patch.object(qualification, 'local_file'), self.assertRaises((ValueError, subprocess.TimeoutExpired)):
                vm.run()
            vm.command.assert_called_once_with('start', vm.vmx, 'nogui', timeout=20)
            vm.stop.assert_called_once()
        vm.inventory = Mock(return_value=['other.vmx'])
        vm.command = Mock()
        vm.stop = Mock()
        with self.assertRaises(ValueError):
            vm.run()
        vm.command.assert_not_called()
        vm.stop.assert_not_called()

    def test_vmware_commands_record_paths_and_timeouts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as tmp:
            vm = qualification.VmwareCopy.__new__(qualification.VmwareCopy)
            vm.folder = Path(tmp)
            vm.tool = Path('vmrun.exe')
            vm.commands = []
            result = SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch.object(qualification.subprocess, 'run', return_value=result) as run:
                vm.command('stop', Path(tmp) / 'owned.vmx', 'hard', timeout=10)
                self.assertEqual(run.call_args.kwargs['timeout'], 10)
                self.assertEqual(run.call_args.args[0][-1], 'hard')
            self.assertIsInstance(json.loads((Path(tmp) / 'commands.json').read_text())[0]['args'][1], str)
            with patch.object(qualification.subprocess, 'run', side_effect=subprocess.TimeoutExpired('vmrun', 10)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    vm.command('list', timeout=10)
            self.assertTrue(json.loads((Path(tmp) / 'commands.json').read_text())[-1]['timed_out'])

    def test_vmware_exact_authority(self):
        for pit in (False, True):
            config = qualification.vmware_config(5911, pit)
            self.assertEqual(config['numvcpus'], '1')
            self.assertEqual(config['memsize'], '1024')
            self.assertEqual(config['sata0:0.fileName'], 'reference.vmdk')
            self.assertEqual(config['RemoteDisplay.vnc.ip'], '127.0.0.1')
            for key in ('ethernet0.present', 'floppy0.present', 'usb.present',
                        'sound.present', 'usb.generic.allowHID'):
                self.assertEqual(config[key], 'FALSE')
            self.assertEqual('cpuid.1.edx' in config, pit)
            if pit:
                mask = config['cpuid.1.edx'].replace(':', '')
                self.assertEqual(len(mask), 32)
                self.assertEqual(mask.count('0'), 1)
                self.assertEqual(mask[-10], '0')
        for bad in (0, -1, 65536, '5911', True):
            with self.assertRaises(ValueError):
                qualification.vmware_config(bad, False)

    def test_vmware_vmrun_inventory_strict(self):
        self.assertEqual(qualification.parse_vm_list('Total running VMs: 0\n'), [])
        self.assertEqual(qualification.parse_vm_list('Total running VMs: 1\nC:/owned.vmx\n'), ['C:/owned.vmx'])
        for text in ('', 'Error: unavailable', 'Total running VMs: 1\n',
                     'Total running VMs: 0\nC:/other.vmx\n'):
            with self.assertRaises(ValueError):
                qualification.parse_vm_list(text)

    def test_vmware_process_ownership_exact_path(self):
        vmx = Path('D:/build/owned/reference.vmx')
        self.assertTrue(qualification.owns_vm_process('vmware-vmx.exe "D:/build/owned/reference.vmx"', vmx))
        for line in ('vmware-vmx.exe D:/user/reference.vmx',
                     'vmware-vmx.exe "D:/build/owned/reference.vmx.other"', '', None):
            self.assertFalse(qualification.owns_vm_process(line, vmx))

    def test_exact_payload_set_and_each_changed_program(self):
        expected = {f'P{i}.PRG': 'a' * 64 for i in range(96)}
        qualification.same_programs(expected, dict(expected))
        for name in expected:
            changed = dict(expected)
            changed[name] = 'b' * 64
            with self.assertRaises(ValueError):
                qualification.same_programs(expected, changed)
        for changed in ({}, {**expected, 'EXTRA.PRG': 'a' * 64},
                        {k: v for k, v in expected.items() if k != 'P0.PRG'}):
            with self.assertRaises(ValueError):
                qualification.same_programs(expected, changed)

    def test_snapshot_guest_authority_and_oracle(self):
        commands = qualification.guest_cases(Path('qemu.exe'), Path('disk.img'), 'qemu')
        self.assertEqual(len(commands), 2)
        for kwargs in commands:
            self.assertEqual(kwargs['timeout'], 60)
            self.assertFalse(kwargs['persistent'])
            self.assertEqual(kwargs['nic'], 'none')
            self.assertEqual(kwargs['smp'], 1)
            self.assertTrue(kwargs['expect_reist_probe'])
            self.assertFalse(kwargs['boot_only'])
        self.assertEqual([c['no_apic'] for c in commands], [False, True])
        with self.assertRaises(ValueError):
            qualification.guest_result(0, 'GTEST PASS', None)
        with self.assertRaises(ValueError):
            qualification.guest_result(1, '', 'capture failure')

    def test_reject_cross_profile_runtime_before_launch(self):
        for profile in ('vmware', 'real_hw', '', None):
            with self.assertRaisesRegex(ValueError, 'matching runtime'):
                qualification.guest_cases(Path('qemu.exe'), Path('disk.img'), profile)

    def test_postcheck_also_runs_after_failure(self):
        events = []
        def snapshot():
            events.append('snapshot')
            return {'disk': 'unchanged'}
        def failure():
            events.append('guest')
            raise ValueError('guest failure')
        with self.assertRaisesRegex(ValueError, 'guest failure'):
            qualification.unchanged_during(snapshot, failure)
        self.assertEqual(events, ['snapshot', 'guest', 'snapshot'])
        with self.assertRaisesRegex(ValueError, 'reference changed'):
            qualification.unchanged_during(iter([{'disk': 'a'}, {'disk': 'b'}]).__next__, lambda: None)


if __name__ == '__main__':
    unittest.main()
