"""Actual O0/O2 EXT2 range/failure behavior; no source-pattern substitute."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class Ext2ReadRanges(unittest.TestCase):
    def test_actual_range_and_legacy_consumers(self):
        with tempfile.TemporaryDirectory() as directory:
            for optimization in ('-O0','-O2'):
                with self.subTest(optimization=optimization):
                    exe=Path(directory)/(optimization[1:]+'.exe')
                    subprocess.run(['gcc','-std=c11',optimization,'-Wall','-Wextra','-Werror','-I.',
                        '-Iuserspace/sdk/include','test/ext2_read_ranges_host.c','-o',str(exe)],
                        cwd=ROOT,check=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    result=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=30)
                    output=(result.stdout+result.stderr).decode(errors='replace')
                    self.assertEqual(result.returncode,0,output)
                    self.assertIn('EXT2_RANGE_PASS',output);print(optimization,output.strip())
    def test_existing_bounded_symlink_consumer(self):
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'bounded.exe'
            result=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I.',
                '-Iuserspace/sdk/include','test/test_reist_vfs_symlink_host.c',
                'userspace/storage/lib/vfs_shadow_ext2.c','userspace/storage/lib/vfs_symlink_client.c',
                'userspace/storage/lib/vfs_path.c','-o',str(exe)],cwd=ROOT,capture_output=True,timeout=90)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))
            result=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))
if __name__=='__main__':unittest.main()
