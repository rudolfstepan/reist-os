"""Actual freestanding adapter through existing parsers and block protocol."""
from pathlib import Path
import subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_fs_media as media
class NativeFilesystem(unittest.TestCase):
    def test_actual_o0_o2_all_layouts(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            for opt in ('-O0','-O2'):
                exe=base/(opt[1:]+'.exe')
                args=['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-I.','-Iuserspace/sdk/include',
                    'test/x86_64_filesystem_host.c',*['userspace/storage/lib/'+n+'.c' for n in
                    ('native_block','vfs_shadow_fat32','vfs_shadow_ext2')],'-o',str(exe)]
                done=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=90)
                self.assertEqual(done.returncode,0,done.stdout.decode(errors='replace')+done.stderr.decode(errors='replace'))
                for layout in media.LAYOUTS:
                    with self.subTest(opt=opt,layout=layout):
                        disk=base/(layout+'.raw');disk.write_bytes(media.image(layout))
                        result=subprocess.run([str(exe),str(disk),layout],cwd=ROOT,capture_output=True,timeout=30)
                        output=(result.stdout+result.stderr).decode(errors='replace')
                        self.assertEqual(result.returncode,0,output)
                        self.assertIn('NATIVE_FS_HOST_PASS',output);print(opt,layout,output.strip())
if __name__=='__main__':unittest.main()
