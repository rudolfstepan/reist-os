"""Behavioral C tests for explicit native application objects; no OS builds."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class AppFilesTests(unittest.TestCase):
    def test_exact_old_disabled_paths_and_selector_mutations(self):
        from build_x86_64_app_files import without_app_build_selector
        from verify_x86_64_shell_session import disabled,default_projection
        source='userspace/sdk/lib/x86_64/shell_session.c'
        before=subprocess.check_output(['git','show','2e05a01d:'+source],cwd=ROOT,timeout=10).decode().replace('\r\n','\n')
        self.assertEqual(disabled((ROOT/source).read_text(encoding='utf-8'),'REIST_NATIVE_APP_FILES',False),before)
        for name,make in (('Makefile',True),('scripts/build-x86_64-bootstrap.ps1',False)):
            text=(ROOT/name).read_text(encoding='utf-8');before=subprocess.check_output(['git','show','2e05a01d:'+name],cwd=ROOT,timeout=10).decode().replace('\r\n','\n')
            self.assertEqual(without_app_build_selector(text,make),before)
            for changed in (text+'\n# NativeAppFiles extra\n',text.replace('NativeAppFiles','BrokenAppFiles',1)):
                with self.assertRaises(ValueError):without_app_build_selector(changed,make)
        self.assertIn('Makefile',default_projection())

    def test_broker_c(self):
        self.c_program('test/x86_64_app_files_host.c','APP_FILES_HOST_OK')

    def test_platform_and_real_cat_ls_c(self):
        self.c_program('test/x86_64_app_file_platform_host.c','APP_FILE_PLATFORM_HOST_OK')

    def test_selected_freestanding_units(self):
        from build_user_program import find_zig
        folder=ROOT/'build/codex-agent/r83bc-application-files/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'zig-cache')
        for n,source in enumerate(('userspace/sdk/lib/x86_64/shell_platform.c',
                'userspace/sdk/lib/x86_64/app_files.c','userspace/sdk/lib/x86_64/app_file_platform.c',
                'arch/x86_64/user/app_files_probe.c','userspace/programs/cat.c','userspace/programs/ls.c')):
            command=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-Oz',
                '-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector',
                '-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-Iuserspace/storage/include',
                '-DREIST_NATIVE_WIDE_FILE=1','-DREIST_NATIVE_SHELL_SESSION=1','-DREIST_NATIVE_APP_FILES=1',
                '-c',source,'-o',str(folder/f'{n}.o')]
            r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/f'{n}.log').write_bytes(r.stdout+r.stderr)
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-3000:])
            symbols=subprocess.check_output(['nm','-u',str(folder/f'{n}.o')],cwd=ROOT,timeout=10).decode()
            self.assertNotRegex(symbols,r'\b(memset|memcpy|memmove)\b','freestanding units must not require implicit libc')

    def test_root_capture_publication_and_cleanup(self):
        folder=ROOT/'build/codex-agent/r83bc-application-files/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe')
            command=['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',
                '-Iuserspace/sdk/include','-Iuserspace/storage/include','test/x86_64_app_files_shell_host.c',
                'userspace/bin/shell_vfs.c','userspace/sdk/lib/x86_64/service_session.c',
                'userspace/sdk/lib/x86_64/file_image.c','userspace/sdk/lib/x86_64/image.c',
                'userspace/sdk/lib/x86_64/app_files.c',
                *['userspace/storage/lib/'+n+'.c' for n in ('native_filesystem','native_block','vfs_shadow_fat32','vfs_shadow_ext2')],
                '-Wl,--gc-sections','-o',str(exe)]
            for n,args in enumerate([command,*[[str(exe),str(case)] for case in (0,2,3,4,5,6,7)]]):
                r=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60 if n==0 else 5,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/f'{opt}-{n}.log').write_bytes(r.stdout+r.stderr)
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-3000:])
                if n:self.assertIn(b'APP_FILES_SHELL_HOST_OK',r.stdout)

    def c_program(self,source,marker):
        folder=ROOT/'build/codex-agent/r83bc-application-files/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe')
            commands=[['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-Iuserspace/sdk/include','-Iuserspace/storage/include',
                source,'userspace/sdk/lib/x86_64/app_files.c',
                *(['userspace/storage/lib/vfs_shadow_ext2.c','userspace/storage/lib/vfs_shadow_fat32.c'] if source.endswith('app_files_host.c') else []),
                '-o',str(exe)], [str(exe)]]
            for n,command in enumerate(commands):
                result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=60,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/f'{opt}-{n}.log').write_bytes(result.stdout+result.stderr)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])
            self.assertIn(marker.encode(),result.stdout)

    def test_all_generated_media_actual_parsers(self):
        from build_x86_64_app_files_media import image,LAYOUTS,NAMES,DATA
        from check_x86_64_app_files_media import verify
        folder=ROOT/'build/codex-agent/r83bc-application-files/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        files={name:(bytes((n+17)%256 for n in range(size))) for name,size in zip(NAMES,(29032,20000,24000,17000,len(DATA)))}
        files['data.txt']=DATA
        for name,data in files.items():(folder/name).write_bytes(data)
        exe=folder/'media.exe'
        command=['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iuserspace/sdk/include','-Iuserspace/storage/include',
            'test/x86_64_app_files_host.c','userspace/sdk/lib/x86_64/app_files.c',
            'userspace/storage/lib/vfs_shadow_ext2.c','userspace/storage/lib/vfs_shadow_fat32.c','-o',str(exe)]
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/'compile.log').write_bytes(r.stdout+r.stderr)
        self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-2500:])
        for layout in LAYOUTS:
            raw=image(layout,files);self.assertTrue(verify(raw,layout,files))
            path=folder/(layout+'.raw');path.write_bytes(raw)
            r=subprocess.run([str(exe),str(path),layout,str(folder)],cwd=ROOT,capture_output=True,timeout=20,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(layout+'.log')).write_bytes(r.stdout+r.stderr)
            self.assertEqual(r.returncode,0,layout+': '+(r.stdout+r.stderr).decode(errors='replace')[-2500:])
            self.assertIn(b'APP_FILES_MEDIA_HOST_OK',r.stdout)
            for offset in (0 if layout.startswith('fat') else 1024, len(raw)-1):
                mutated=bytearray(raw);mutated[offset]^=0x80
                if offset==0:mutated[510]^=1
                with self.assertRaises(ValueError):verify(bytes(mutated),layout,files)

if __name__=='__main__':unittest.main()
