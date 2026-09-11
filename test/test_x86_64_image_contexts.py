"""Actual image ownership assembly and independent guest witness mutations."""
from pathlib import Path
import itertools,os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class ImageContextTests(unittest.TestCase):
    def test_oracle(self):
        from run_qemu_x86_64_image_contexts import validate,ROUND,DONE
        trace=''
        for r,order in enumerate(itertools.permutations(range(3))):
            before=32000
            for c,im in enumerate(order):
                freed=2 if im==0 else 1
                trace+=f'IMAGE_RELEASE round={r} cursor={c} image={im} before={before} freed={freed} after={before+freed} load=32005 held=67117056 result=1 active=0\n'
                before+=freed
        serial=(ROUND+'\n')*6+DONE+'\nREIST_X86_64_ELF64_LOAD_OK\n'
        for gen in (41,42):
            serial+=f'CHILD_EXIT_REAP_OK status=0000004D generation={gen:02X} parent=07 queued=00 rip=0000000000400123\nREIST_X86_64_RING3_SHELL_RUN_OK\n'
        validate(serial,trace,0x400123)
        for bad in (trace+trace,trace.replace('IMAGE_RELEASE','MISSING',1),trace.replace('image=0','image=1',1),
                    trace.replace('freed=2','freed=1',1),trace.replace('before=32002','before=32001',1),
                    trace.replace('result=1','result=0',1),trace.replace('active=0','active=1',1),
                    trace.replace('load=32005','load=32002',1),trace.replace('held=67117056','held=0',1),
                    trace.replace('held=67117056','held=67117057',1),trace.replace('round=1','round=0')):
            with self.assertRaises(RuntimeError):validate(serial,bad,0x400123)
        for bad in (serial.replace(ROUND,'',1),serial+DONE,serial.replace('generation=2A','generation=29'),
                    serial.replace('400123','400121',1),serial.replace('queued=00','queued=01',1),
                    DONE+'\n'+serial.replace(DONE,'',1),serial.replace('0000004D','0000005B',1)):
            with self.assertRaises(RuntimeError):validate(bad,trace,0x400123)

    def test_shared_core_and_bounds(self):
        source=(ROOT/'arch/x86_64/exec/elf64_loader.asm').read_text()
        cleanup=source.split('elf64_cleanup64:',1)[1].split('section .rodata',1)[0]
        self.assertIn('call reist_x64_image_release',cleanup)
        self.assertNotIn('elf_initial_free_count',cleanup)
        for token in ('cmp byte [rel elf_context_selftest_round], 6','repe cmpsq','repe scasq',
                      'call elf64_context_checksum64','cmp eax, [rel elf_context_selftest_initial]'):
            self.assertIn(token,source)
        self.assertIn('ELF_CONTEXT_SIZE    equ 88',source)
        core=(ROOT/'arch/x86_64/exec/image_frames.asm').read_text()
        self.assertNotIn('physical_frame_alloc64',core)
        self.assertLess(core.index('.validate:'),core.index('call physical_frame_free64'))
        self.assertIn('cmp r13d, LIMIT / 4096',core)
        self.assertIn('cmp eax, r13d',core)

    def test_host(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83n-images'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,label,timeout=90):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:]);return r.stdout
        obj=folder/'image_frames.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/exec/image_frames.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                'test/x86_64_image_contexts_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('X86_64_IMAGE_CONTEXTS_HOST_OK',run([exe],opt+'-run',10))
if __name__=='__main__':unittest.main()
