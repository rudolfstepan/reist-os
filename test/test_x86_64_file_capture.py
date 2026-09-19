"""Actual two-stage immutable file capture on every supported media layout."""
from pathlib import Path
import os,struct,subprocess,sys,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_fs_media as media

class FileCaptureTests(unittest.TestCase):
    def test_actual_freestanding_link_without_implicit_libc(self):
        from build_user_program import find_zig
        folder=ROOT/'build/codex-agent/r83aw-file-capture/host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        # Model only external FS/image calls; never provide memcpy/memset.
        # No section GC: every real SDK entrypoint must link freestanding.
        stub=folder/'boundaries.s'
        stub.write_text('.text\n.global _start,reist_fs_request_init,reist_fs_call,reist_x64_image_prepare_v2\n'
            '_start:\nreist_fs_request_init:\nreist_fs_call:\nreist_x64_image_prepare_v2:\nmov $-38,%eax\nret\n',encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'zig-cache')
        command=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-Oz','-ffreestanding','-nostdlib',
            '-fno-builtin','-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
            '-Iuserspace/sdk/include','userspace/sdk/lib/x86_64/file_image.c',str(stub),
            '-Wl,--no-undefined,--no-gc-sections,-e,_start','-o',str(folder/'capture.elf')]
        result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/'link.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3500:])
        self.assertTrue((folder/'capture.elf').read_bytes().startswith(b'\x7fELF\x02'))

    def test_actual_runtime_stops_and_seals_first_failure(self):
        import verify_x86_64_file_capture as verify
        import run_qemu_x86_64_terminal as run
        folder=ROOT/'build/codex-agent/r83aw-file-capture/host'/uuid.uuid4().hex
        folder.mkdir(parents=True);image=folder/'model-image';image.write_bytes(b'host model only')
        with patch.object(verify,'BASE',folder),patch.object(verify,'IMAGE',image),\
             patch.object(verify,'binding',return_value={'candidate':'host-model'}),\
             patch.object(verify,'read',return_value={'passed':True}),\
             patch.object(run.live,'image_config',return_value=({}, {'program':1},b'model')),\
             patch.object(run.live.pio,'Fixture'),patch.object(run.live.file,'program_variant',return_value=b'model'),\
             patch.object(run,'observer',return_value='host-only observer'),\
             patch.object(run.live.wide.transport,'capture',side_effect=RuntimeError('injected first failure')) as capture:
            with self.assertRaisesRegex(RuntimeError,'injected first failure'):verify.runtime()
            self.assertEqual(capture.call_count,1)
        summaries=list((folder/'guests').glob('attempt-*/summary.json'));self.assertEqual(len(summaries),1)
        summary=verify.read(summaries[0])
        self.assertTrue(summary['closed']);self.assertFalse(summary['passed'])
        self.assertEqual(len(summary['cases']),1);self.assertFalse(summary['cases'][0]['passed'])
        self.assertEqual(summary['error'],'injected first failure')

    def test_actual_c_o0_o2_all_media_and_boundaries(self):
        folder=ROOT/'build/codex-agent/r83aw-file-capture/host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        def run(command,limit):
            result=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=limit,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3500:])
            return result.stdout
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe')
            run(['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-I.','-Iuserspace/sdk/include',
                'test/x86_64_file_capture_host.c','userspace/sdk/lib/x86_64/file_image.c',
                'userspace/sdk/lib/x86_64/image.c',*['userspace/storage/lib/'+n+'.c' for n in
                ('native_block','vfs_shadow_fat32','vfs_shadow_ext2')],'-o',exe],90)
            for size in (121,1272,1536):
                raw=bytearray(size);raw[:7]=b'\x7fELF\x02\x01\x01'
                struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
                struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096);raw[120]=0xc3
                elf=folder/f'file-{size}.prg';elf.write_bytes(raw)
                for layout in media.LAYOUTS:
                    with self.subTest(opt=opt,size=size,layout=layout):
                        disk=folder/f'{layout}-{size}.raw';disk.write_bytes(media.image(layout,program=bytes(raw)))
                        out=run([exe,disk,layout,elf],30)
                        self.assertIn(b'FILE_CAPTURE_PASS',out)
                        print(opt,size,layout,'PASS',flush=True)

if __name__=='__main__':unittest.main()
