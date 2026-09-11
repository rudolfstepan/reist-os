"""Independent negative oracles for JS colors; engine/host run in their own gates."""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from run_qemu_js_colors import expected_colors, validate_transcript, validate_pixels, validate_boot, guest_failed
from run_qemu_js_runner import mandelbrot_reference
from verify_js_colors_artifacts import copy_checked, CHANGED
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


if __name__ == '__main__':
    unittest.main()
