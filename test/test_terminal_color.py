"""R3.44 actual bounded publication code, CLI, ABI and guest-oracle negatives."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs
from test_memory_r12 import function_block


class TerminalColorTests(unittest.TestCase):
    def test_actual_admission_and_backends_o0_o2(self):
        suppress_windows_test_dialogs()
        pieces = []
        functions = (
            ('drivers/video/video.c', 'int vga_write_color(const char *text, unsigned int length, unsigned char color)'),
            ('drivers/video/framebuffer.c', 'int framebuffer_write_color(const char *text, unsigned int length, uint32_t foreground, uint32_t background)'),
            ('drivers/video/display.c', 'static uint32_t vga_to_fb_color(char vga_color)'),
            ('drivers/video/display.c', 'int display_write_color(const char *text, unsigned int length, unsigned int foreground, unsigned int background)'),
            ('drivers/video/display_control.c', 'int display_control_console_color(const char *text, unsigned int length, unsigned int foreground, unsigned int background)'),
            ('kernel/syscall/syscall_table.c', 'static int syscall_terminal_write_color(const reist_terminal_color_request_t *user_request)'),
        )
        for path, signature in functions:
            source = (ROOT / path).read_text(encoding='utf-8')
            start = signature.split('(')[0] + '('
            self.assertTrue(start in source, 'missing production function: ' + path)
            pieces.append(signature + ' ' + function_block(source, start))
        folder = ROOT / 'build/codex-agent/r344-terminal-color' / ('host-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        fixture = (ROOT / 'test/terminal_color_host.c').read_text()
        echo = (ROOT / 'userspace/programs/echo.c').read_text()
        echo_code = '\n'.join(signature + ' ' + function_block(echo, original) for signature, original in (
            ('static int equal(const char *a, const char *b)', 'static int equal('),
            ('static int color_echo(int argc, char **argv)', 'static int color_echo('),
            ('static int echo_main(int argc, char **argv)', 'int main(')))
        (folder / 'host.c').write_text(fixture.replace('/* PRODUCTION */', '\n'.join(pieces))
                                      .replace('/* ECHO */', echo_code))
        env = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(ROOT / 'build/zig-global-cache'),
                   ZIG_LOCAL_CACHE_DIR=str(folder / 'cache'))
        for opt in ('-O0', '-O2'):
            exe = folder / (opt + '.exe')
            for command, timeout in (([find_zig(), 'cc', '-target', 'x86-windows-gnu', opt,
                    '-std=c11', '-fno-sanitize=all', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wno-unused-command-line-argument',
                    '-I', ROOT, folder/'host.c', '-o', exe], 90), ([exe], 20)):
                result = subprocess.run(list(map(str, command)), env=env, capture_output=True,
                    text=True, timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('TERMINAL_COLOR_HOST_OK', result.stdout)

    def test_shell_resolution_and_no_script_grant(self):
        sdk = (ROOT/'userspace/sdk/x86os.c').read_text()
        self.assertIn('__attribute__((section(".text.x86os_terminal_write_color")))', sdk)
        windows = (ROOT/'scripts/build-windows.ps1').read_text()
        make = (ROOT/'Makefile').read_text()
        for name in ('ECHO', 'COLORTST'):
            self.assertIn("'bin/"+name.lower()+".prg' = '"+name+".PRG'", windows)
            self.assertIn('bin/'+name.lower()+'.prg=$(SYSTEM_PROGRAM_DIR)/'+name+'.PRG', make)
        shell = (ROOT/'userspace/bin/shell.c').read_text()
        self.assertIn('"/bin"', shell)
        self.assertIn('x86os_spawnv(executable, argc, child_argv)', shell)
        domains = (ROOT/'kernel/proc/process.c').read_text()
        script = domains.split('static const uint8_t script_syscalls[]', 1)[1].split('};', 1)[0]
        self.assertNotIn('TERMINAL_WRITE_COLOR', script)
        control = function_block((ROOT/'drivers/video/display_control.c').read_text(),
                                 'int display_control_console_color(')
        self.assertLess(control.index('kernel_mutex_lock_for'), control.index('display_write_color'))
        self.assertIn('active_backend', control)

    def test_guest_oracles_reject_missing_pixels_and_receipts(self):
        from run_qemu_terminal_color import validate_pixels, validate_transcript, validate_boot
        from run_qemu_smoke import REIST_PROBE_MARKERS, REIST_PROBE_COMPLETION_MARKER
        boot = '\n'.join((*REIST_PROBE_MARKERS, REIST_PROBE_COMPLETION_MARKER, 'BOOT_OK'))+'\n'
        validate_boot(boot)
        for marker in (*REIST_PROBE_MARKERS, REIST_PROBE_COMPLETION_MARKER, 'BOOT_OK'):
            with self.assertRaises(ValueError): validate_boot(boot.replace(marker, ''))
        with self.assertRaises(ValueError): validate_boot(boot+boot)
        with self.assertRaises(ValueError): validate_boot('\n'.join(reversed(boot.splitlines())))
        colors = [(170,0,0),(0,170,0),(0,0,170),(255,255,255)]
        pixels = bytes(c for rgb in colors for _ in range(32) for c in rgb)
        validate_pixels((128,1,pixels))
        vga_pixels = pixels.replace(bytes([170]), bytes([168]))
        validate_pixels((128,1,vga_pixels), framebuffer=False)
        with self.assertRaises(ValueError): validate_pixels((128,1,vga_pixels))
        with self.assertRaises(ValueError): validate_pixels((128,1,pixels), framebuffer=False)
        for rgb in colors:
            with self.assertRaises(ValueError):
                validate_pixels((128,1,pixels.replace(bytes(rgb), b'\0\0\0')))
        valid = '\n'.join(['COLOR_ABI_OK','COLOR_DENIAL_OK','COLOR_REAP_OK',
                           'COLOR_RESTART_OK','COLOR_TEST_OK','HOST_COLOR_SHELL_OK'])+'\n'
        validate_transcript(valid)
        for bad in (valid.replace('COLOR_REAP_OK',''), valid+valid,
                    valid+'KERNEL PANIC', valid+'COLOR_TEST_FAIL', valid+'USER PROCESS PAGE FAULT'):
            with self.assertRaises(ValueError): validate_transcript(bad)


if __name__ == '__main__':
    unittest.main()
