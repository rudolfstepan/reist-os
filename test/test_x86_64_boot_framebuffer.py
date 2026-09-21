"""Host execution of the production Multiboot-v1 framebuffer parser."""
from pathlib import Path
import os
import subprocess
import sys
import uuid
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_sdk import find_zig


class BootFramebufferTests(unittest.TestCase):
    def test_production_parser_o0_o2(self):
        temp=ROOT/'build/codex-agent/r83be-display'/('host-boot-'+uuid.uuid4().hex)
        temp.mkdir(parents=True)
        if True:
            env = os.environ.copy()
            env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
            env['ZIG_LOCAL_CACHE_DIR'] = str(Path(temp) / 'zig-cache')
            for level in ('0', '2'):
                exe = Path(temp) / ('framebuffer-' + level + '.exe')
                cmd = [str(find_zig()), 'cc', '-target', 'x86_64-windows-gnu',
                       '-O' + level, '-Wall', '-Wextra', '-Werror', '-I.',
                       'arch/x86_64/video/boot_framebuffer.c',
                       'test/x86_64_boot_framebuffer_host.c', '-o', str(exe)]
                result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True,
                                        text=True, timeout=60,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                (temp/('compile-'+level+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                result = subprocess.run([str(exe)], cwd=ROOT, capture_output=True,
                                        text=True, timeout=20,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                (temp/('run-'+level+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
