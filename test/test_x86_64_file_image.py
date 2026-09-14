"""Actual FS/block/ELF64/file adapter, not a model loader or synthetic pass."""
from pathlib import Path
import subprocess,sys,tempfile,unittest,struct
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_fs_media as media
class FileImageTests(unittest.TestCase):
    def test_real_o0_o2_all_media_and_fail_closed(self):
        # Independent ordinary ELF64 with RX file headers and a legal AMD64 RET.
        raw=bytearray(1536);raw[:7]=b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
        struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096);raw[120]=0xc3
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);elf=base/'file.prg';elf.write_bytes(raw)
            for opt in ('-O0','-O2'):
                exe=base/(opt[1:]+'.exe')
                args=['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-I.','-Iuserspace/sdk/include',
                    'test/x86_64_file_image_host.c','userspace/sdk/lib/x86_64/file_image.c','userspace/sdk/lib/x86_64/image.c',
                    *['userspace/storage/lib/'+n+'.c' for n in ('native_block','vfs_shadow_fat32','vfs_shadow_ext2')],'-o',str(exe)]
                result=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=90)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))
                for layout in media.LAYOUTS:
                    with self.subTest(opt=opt,layout=layout):
                        disk=base/(layout+'.raw');disk.write_bytes(media.image(layout,program=bytes(raw)))
                        result=subprocess.run([str(exe),str(disk),layout,str(elf)],cwd=ROOT,capture_output=True,timeout=30)
                        output=(result.stdout+result.stderr).decode(errors='replace')
                        self.assertEqual(result.returncode,0,output);self.assertIn('FILE_IMAGE_HOST_PASS',output)
                        print(opt,layout,output.strip())
if __name__=='__main__':unittest.main()
