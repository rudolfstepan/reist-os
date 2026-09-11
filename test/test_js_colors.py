"""Independent negative oracles for JS colors; engine/host run in their own gates."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from run_qemu_js_colors import expected_colors, validate_transcript, validate_pixels, validate_boot, guest_failed
from run_qemu_js_runner import mandelbrot_reference
from verify_js_colors_artifacts import copy_checked, CHANGED
import verify_js_colors_artifacts as artifacts
from run_qemu_math import digest
import run_qemu_smoke as smoke


def complete():
    colors = '\n'.join(expected_colors())+'\n'
    return colors+'js: script exception\n'+colors+'MANDELC_BEGIN width=64 height=24 iterations=48\n'+\
        '\n'.join(mandelbrot_reference())+'\nMANDELC_END\nJS_COLOR_MANDEL_OK\nHOST_JS_COLOR_SHELL_OK\n'


class ColorTests(unittest.TestCase):
    def test_exact_records_recovery_and_mandelbrot(self):
        text = complete(); validate_transcript(text); validate_transcript(text.replace('\n', '\r\n'))
        for old, new in [('PALETTE 0 black', 'PALETTE 0 white'), ('x'*130, 'x'*129),
                         ('SANITIZE ????', 'SANITIZE \x1b???'), ('MULTI_A\nMULTI_B', 'MULTI_B\nMULTI_A'),
                         ('BLUE_STDERR', 'BLUE'), ('js: script exception\n', ''),
                         ('JS_COLOR_MANDEL_OK', 'missing'), ('|', '!')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                validate_transcript(text.replace(old, new, 1))
        for extra in ('JS_COLOR_BEGIN\n', 'JS_COLOR_OK rejected=8\n', 'MANDELC_END\n',
                      'KERNEL PANIC', '*** USER PROCESS PAGE FAULT ***', 'REJECTED_COLOR_PREFIX'):
            with self.subTest(extra=extra), self.assertRaises(ValueError): validate_transcript(text+extra)

    def test_pixel_modes_and_negatives(self):
        for framebuffer, level in ((False, 168), (True, 170)):
            data = b''.join(bytes(rgb)*32 for rgb in ((level,0,0),(0,level,0),(0,0,level),(255,255,255)))
            validate_pixels((128, 1, data), framebuffer)
            with self.assertRaises(ValueError): validate_pixels((128, 1, data), not framebuffer)
            with self.assertRaises(ValueError): validate_pixels((128, 1, data[:-3]), framebuffer)
            with self.assertRaises(ValueError): validate_pixels((128, 1, bytes(len(data))), framebuffer)
        with self.assertRaises(ValueError): validate_pixels(None)

    def test_boot_receipts(self):
        markers = [*smoke.REIST_PROBE_MARKERS, smoke.REIST_PROBE_COMPLETION_MARKER, 'BOOT_OK']
        text = '\n'.join(markers)+'\n';validate_boot(text)
        for marker in markers:
            with self.assertRaises(ValueError): validate_boot(text.replace(marker+'\n', ''))
            with self.assertRaises(ValueError): validate_boot(text+marker+'\n')
        fault = '*** USER PROCESS EXCEPTION ***\n'
        self.assertFalse(guest_failed(fault+text, None))
        self.assertFalse(guest_failed(fault+text, len(fault+text)))
        self.assertTrue(guest_failed(fault+text+fault, len(fault+text)))
        self.assertTrue(guest_failed('KERNEL PANIC\n', None))

    def test_layouts_and_protected_inventory(self):
        windows = (ROOT/'scripts/build-windows.ps1').read_text()
        make = (ROOT/'Makefile').read_text()
        for name in ('jscolors.js', 'mandelc.js'):
            self.assertIn("'"+name+"'", windows)
            self.assertIn('htdocs/'+name+'=htdocs/'+name, make)
            self.assertLess((ROOT/'htdocs'/name).stat().st_size, 4096)
        self.assertEqual(CHANGED, {'JS.PRG', 'JSWORK.PRG', 'JSRUNTST.PRG'})

    def test_archive_authentication_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            source = Path(directory)/'source';target = Path(directory)/'archive'
            source.write_bytes(b'accepted')
            with self.assertRaises(ValueError): copy_checked(source, target, 'invalid')
            self.assertFalse(target.exists())
            copy_checked(source, target, digest(source));self.assertEqual(target.read_bytes(), b'accepted')
            with self.assertRaises(FileExistsError): copy_checked(source, target, digest(source))
            self.assertEqual(target.read_bytes(), b'accepted')

    def test_reference_configuration_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            root = Path(directory); (root/'build').mkdir()
            config = root/'build/.windows-build-config.json'
            with patch.object(artifacts, 'ROOT', root):
                for target, video in (('qemu', 'vga'), ('vmware', 'vga'),
                                      ('qemu', 'framebuffer'), ('vmware', 'framebuffer'),
                                      ('unknown', 'vga'), ('qemu', 'unknown')):
                    config.write_text(json.dumps(dict(target=target, video=video)))
                    if video == 'vga' and target in ('qemu', 'vmware'):
                        self.assertEqual(artifacts.build_config('vga')['target'], target)
                    else:
                        with self.assertRaises(ValueError): artifacts.build_config('vga')
                    if (target, video) == ('qemu', 'framebuffer'):
                        self.assertEqual(artifacts.build_config('framebuffer')['target'], 'qemu')
                    else:
                        with self.assertRaises(ValueError): artifacts.build_config('framebuffer')
                config.write_text('{}')
                with self.assertRaises((ValueError, KeyError)): artifacts.build_config('vga')

    def test_image_profiles_and_binary_drift(self):
        # Small fixture images; FAT extraction/kernel extraction are mocked, but
        # payload comparisons, inventory, archive hashes and profile dispatch are real.
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory, ExitStack() as stack:
            root = Path(directory); baseline = root/'baseline'
            for subdir in ('baseline', 'build/programs', 'scripts', 'htdocs'):
                (root/subdir).mkdir(parents=True)
            names = sorted(CHANGED | {'SHELL.PRG', 'BENCHMARK.PRG', 'BROWSER.PRG'})
            names += [f'T{i:03}.PRG' for i in range(95-len(names))]
            (root/'scripts/build-windows.ps1').write_text('\n'.join(
                f"'bin/{name}' = '{name}'" for name in names))
            payloads = {artifacts.short_path('bin/'+name): name.encode() for name in names}
            for name in names: (root/'build/programs'/name).write_bytes(name.encode())
            for name in artifacts.EXAMPLES:
                payloads['htdocs/'+name] = name.encode()
                (root/'htdocs'/name).write_bytes(name.encode())
            images = {target: root/(target+'.current') for target in ('qemu', 'vmware', 'framebuffer')}
            base_images = {}; kernels = {}; files = {}
            for target, image in images.items():
                previous = baseline/(target+'.img')
                previous.write_bytes(('baseline-'+target).encode()); image.write_bytes(target.encode())
                base_images[target] = (previous if target == 'framebuffer' else image, digest(previous))
                kernels[previous] = kernels[image] = target+'-kernel'
                files[previous] = dict(payloads); files[image] = dict(payloads)
            fb = images['framebuffer']
            fb.with_suffix('.json').write_text(json.dumps(dict(passed=True, sha256=digest(fb))))
            for key, value in dict(ROOT=root, BASELINE=baseline, BASE_IMAGES=base_images, FB_IMAGE=fb).items():
                stack.enter_context(patch.object(artifacts, key, value))
            stack.enter_context(patch.object(artifacts, 'kernel_digest', side_effect=lambda image: kernels[image]))
            reader = stack.enter_context(patch.object(artifacts, 'read_fat_file',
                side_effect=lambda image, path: files[image][path]))
            for target in ('qemu', 'vmware'):
                (root/'build/.windows-build-config.json').write_text(json.dumps(dict(target=target, video='vga')))
                kernels[images['qemu']] = target+'-kernel'
                reader.reset_mock(); result = artifacts.verify()
                main_label = 'qemu' if target == 'qemu' else 'main-vmware'
                self.assertEqual(set(result), {main_label, 'vmware', 'framebuffer'})
                self.assertEqual(result[main_label]['profile'], target)
                self.assertEqual(result[main_label]['image'], str(images['qemu']))
                for report in result.values(): self.assertEqual(set(report['programs']), set(names))
                for image in images.values():
                    for path in payloads: self.assertIn(unittest.mock.call(image, path), reader.call_args_list)
                    saved = kernels[image]; kernels[image] = 'wrong-kernel'
                    with self.assertRaisesRegex(ValueError, 'kernel drift'): artifacts.verify()
                    kernels[image] = saved
                    # Both historically changed JS binaries and protected programs
                    # must still match the current build, in every image.
                    for path in payloads:
                        saved = files[image][path]; files[image][path] = b'corrupt'
                        with self.assertRaisesRegex(ValueError, 'payload'): artifacts.verify()
                        files[image][path] = saved
                reference = baseline/(target+'.img')
                files[reference]['bin/SHELL.PRG'] = b'wrong-baseline-program'
                with self.assertRaisesRegex(ValueError, 'protected/'): artifacts.verify()
                files[reference]['bin/SHELL.PRG'] = payloads['bin/SHELL.PRG']
            baseline.joinpath('vmware.img').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'unauthenticated baseline'): artifacts.verify()


if __name__ == '__main__':
    unittest.main()
