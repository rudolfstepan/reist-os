"""Real C regression of the separately versioned read/capture profile."""
from pathlib import Path
import os,struct,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class WideFileTests(unittest.TestCase):
    def test_selected_freestanding_guest_units(self):
        from build_user_program import find_zig
        folder=ROOT/'build/codex-agent/r83ba-wide-file/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'zig-cache')
        common=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-Oz',
            '-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector',
            '-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include',
            '-DREIST_NATIVE_WIDE_FILE=1','-DREIST_NATIVE_SHELL_SESSION=1','-DREIST_NATIVE_POOL_PIO=1',
            '-DREIST_NATIVE_LIVE_FILE=1','-DREIST_NATIVE_SERVICE_CONSOLE=1','-DREIST_NATIVE_TERMINAL=1',
            '-DFILESYSTEM_LAYOUT=2','-DFILESYSTEM_CASE=0','-DFILE_LAUNCH_CASE=0']
        units=[('arch/x86_64/user/service_console.c',2),('arch/x86_64/user/service_console.c',3),
            ('userspace/sdk/lib/x86_64/shell_platform.c',0),
            ('userspace/sdk/lib/x86_64/service_session.c',0),
            ('userspace/drivers/ata/native_service.c',2)]
        for n,(source,role) in enumerate(units):
            with self.subTest(source=source,role=role):
                r=subprocess.run([*common,f'-DPROGRAM_ID={role}','-c',source,'-o',str(folder/f'{n}.o')],
                    cwd=ROOT,env=env,capture_output=True,timeout=60,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/f'{n}.log').write_bytes(r.stdout+r.stderr)
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-4000:])

    def test_actual_c_profiles_and_capture(self):
        folder=ROOT/'build/codex-agent/r83ba-wide-file/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        def run(command,timeout=90):
            result=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,
                timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-4000:])
            return result.stdout
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe')
            run(['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-DREIST_NATIVE_SHELL_SESSION=1','-I.','-Iuserspace/sdk/include',
                'test/x86_64_wide_file_host.c','userspace/sdk/lib/x86_64/file_image.c',
                'userspace/sdk/lib/x86_64/image.c','userspace/storage/lib/native_block.c',
                'userspace/storage/lib/native_filesystem.c','userspace/storage/lib/vfs_shadow_fat32.c',
                'userspace/storage/lib/vfs_shadow_ext2.c','-o',exe])
            import build_x86_64_wide_file_media as media
            for size in (1536,1537,32769,163160,524288):
                raw=bytearray(size);raw[:7]=b'\x7fELF\x02\x01\x01'
                struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
                struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096)
                raw[120]=0xc3
                elf=folder/f'file-{size}.prg';elf.write_bytes(raw)
                for layout in media.LAYOUTS:
                    with self.subTest(opt=opt,size=size,layout=layout):
                        disk=folder/f'{layout}-{size}.raw';disk.write_bytes(media.image(layout,bytes(raw)))
                        self.assertIn(b'WIDE_FILE_PASS',run([exe,disk,layout,elf],60))
                        print(opt,size,layout,'PASS',flush=True)

if __name__=='__main__':unittest.main()
