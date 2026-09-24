from pathlib import Path
import shutil
import subprocess
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


class DesktopDisplayTests(unittest.TestCase):
    def test_actual_display_adapter(self):
        folder = ROOT / 'build/codex-agent/native-vmware-desktop' / ('display-host-' + uuid.uuid4().hex)
        folder.mkdir()
        cc = shutil.which('gcc') or 'C:/msys64/mingw64/bin/gcc.exe'
        for level in ('-O0', '-O2'):
            with self.subTest(optimization=level):
                exe = folder / (level[1:] + '.exe')
                commands = [[cc, '-std=c11', level, '-Wall', '-Wextra', '-Werror',
                    '-Iuserspace/sdk/include', '-Iinclude',
                    'test/x86_64_desktop_display_host.c',
                    'userspace/sdk/lib/x86_64/desktop_display.c', '-o', str(exe)], [str(exe)]]
                for index, command in enumerate(commands):
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
                    (folder / f'{level[1:]}-{index}.log').write_bytes(result.stdout + result.stderr)
                    self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode(errors='replace'))


if __name__ == '__main__':
    unittest.main()
