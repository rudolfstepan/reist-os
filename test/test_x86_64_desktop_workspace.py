from pathlib import Path
import re
import shutil
import subprocess
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


class DesktopWorkspaceTests(unittest.TestCase):
    def test_actual_allocator_lifecycle(self):
        folder = ROOT / 'build/codex-agent/native-vmware-desktop' / ('workspace-host-' + uuid.uuid4().hex)
        folder.mkdir()
        cc = shutil.which('gcc') or 'C:/msys64/mingw64/bin/gcc.exe'
        for level in ('-O0', '-O2'):
            exe = folder / (level[1:] + '.exe')
            subprocess.run([cc, '-std=c11', level, '-Wall', '-Wextra', '-Werror',
                '-Iuserspace/sdk/include', 'test/x86_64_desktop_workspace_host.c',
                'userspace/gui/compositor/desktop_native_workspace.c', '-o', str(exe)],
                cwd=ROOT, check=True, capture_output=True, timeout=30)
            subprocess.run([str(exe)], check=True, capture_output=True, timeout=30)

    def test_complete_default_desktop_projection(self):
        source = (ROOT / 'userspace/gui/compositor/desktop.c').read_text(encoding='utf-8')
        pattern = r'#ifdef REIST_NATIVE_DESKTOP_WORKSPACE\n(.*?)#endif /\* REIST_NATIVE_DESKTOP_WORKSPACE \*/\n'
        def old(match):
            _, sep, original = match.group(1).partition('#else\n')
            return original if sep else ''
        projected, count = re.subn(pattern, old, source, flags=re.S)
        self.assertGreaterEqual(count, 19)
        self.assertNotIn('REIST_NATIVE_DESKTOP_WORKSPACE', projected)
        original = subprocess.check_output(['git', 'show', '5f0debf9:userspace/gui/compositor/desktop.c'],
                                           cwd=ROOT, timeout=30).decode('utf-8').replace('\r\n', '\n')
        self.assertEqual(projected, original)


if __name__ == '__main__':
    unittest.main()
