"""Production assembly authority state machine, with no emulated device proof."""
from pathlib import Path
import ast,copy,inspect,os,struct,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class DisplayTests(unittest.TestCase):
    def test_broker_cleanup_deadline_and_negative_mutations(self):
        from run_qemu_x86_64_display import cli_qualified_outcome,cli_namespace
        import run_qemu_x86_64_cli_media as old
        sys.path.insert(0,str(ROOT/'test'))
        from test_x86_64_cli_runtime import CliRuntimeTests
        fixture=CliRuntimeTests()
        def events(delay=10):
            spec,start,rows,receipts=fixture.hang_events(delay)
            rows[2]['entered']+=delay;rows[3]['entered']+=delay;rows[3]['now']+=delay
            return spec,start,rows,receipts
        spec,start,rows,receipts=events()
        with self.assertRaises(ValueError):old.qualified_outcome(spec,start,[start],rows,receipts)
        for delay in (0,10,20,40):
            spec,start,rows,receipts=events(delay)
            self.assertEqual(cli_qualified_outcome(spec,start,[start],rows,receipts),(1,4))
        spec,start,rows,receipts=events()
        for n in range(len(rows)):
            with self.assertRaises(ValueError):cli_qualified_outcome(spec,start,[start],rows[:n]+rows[n+1:],receipts)
        for n,key,value in ((1,'now',4651),(2,'entered',4649),(3,'result',-9),(3,'entered',4661),
                            (4,'entered',4649),(5,'result',-9),(5,'now',4661),(6,'entered',4650),
                            (6,'now',4700),(6,'result',0),(7,'entered',5651)):
            bad=copy.deepcopy(rows);bad[n][key]=value
            with self.subTest(n=n,key=key),self.assertRaises(ValueError):cli_qualified_outcome(spec,start,[start],bad,receipts)
        for at in (2,4,6):
            for op in (49,53,54,55,132):
                bad=copy.deepcopy(rows);bad.insert(at,dict(kind='call',gen=1,op=op,args=[262],entered=4650))
                with self.assertRaises(ValueError):cli_qualified_outcome(spec,start,[start],bad,receipts)
        for delay in (-1,50,1000):
            spec,start,rows,receipts=events(delay)
            with self.assertRaises(ValueError):cli_qualified_outcome(spec,start,[start],rows,receipts)
        for label in old.LABELS.values():
            current=cli_namespace(label).ay;previous=old.namespace(label).ay
            for name in ('validate_capture','validate_storage','validate_policy','validate_cpu','validate_identity',
                         'validate_terminal','validate_ipc_delivery','evaluate','observer','SessionFeeder'):
                self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(current,name)))),
                                 ast.dump(ast.parse(inspect.getsource(getattr(previous,name)))))
            self.assertIs(current.validate_objects,previous.validate_objects)

    def test_mapping_and_pixels_reject_mutations(self):
        import run_qemu_x86_64_display as runtime
        folder=ROOT/'build/codex-agent/r83be-display'/('host-oracle-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        symbols=dict(pdpt_table=0x101000,native_display_pd=0x102000,native_display_pts=0x103000)
        base=0xe0000000;length=800*600*4
        pml4=[0]*512;pml4[511]=symbols['pdpt_table']|3
        pdpt=[0]*512;pdpt[509]=symbols['native_display_pd']|3
        tables=[0]*3584
        for n in range(6):tables[n]=(symbols['native_display_pts']+4096*n)|3
        for n in range((length+4095)//4096):tables[512+n]=(base+4096*n)|0x800000000000001b
        for name,values in [('pml4',pml4),('pdpt',pdpt),('pd',tables)]:
            (folder/(name+'.bin')).write_bytes(struct.pack('<'+'Q'*len(values),*values))
        runtime.validate_mapping(folder,symbols,base,(length+4095)&~4095)
        original=(folder/'pd.bin').read_bytes()
        for index,bit in [(0,4),(512,4),(512,1<<63),(512,8),(512,4096),(3583,1)]:
            changed=bytearray(original);struct.pack_into('<Q',changed,index*8,tables[index]^bit)
            (folder/'pd.bin').write_bytes(changed)
            with self.assertRaises(ValueError):runtime.validate_mapping(folder,symbols,base,(length+4095)&~4095)
        (folder/'pd.bin').write_bytes(original)
        old=bytearray(length//4*3);new=bytearray(old)
        for y in range(64):
            for x in range(64):new[((y+32)*800+x+32)*3:((y+32)*800+x+32)*3+3]=bytes((x*4,y*4,90))
        header=b'P6\n800 600\n255\n'
        (folder/'before.ppm').write_bytes(header+old);(folder/'after.ppm').write_bytes(header+new)
        runtime.validate_pixels(folder/'before.ppm',folder/'after.ppm')
        new[-1]^=1;(folder/'after.ppm').write_bytes(header+new)
        with self.assertRaises(ValueError):runtime.validate_pixels(folder/'before.ppm',folder/'after.ppm')

    def test_freestanding_objects_and_media_composition(self):
        import build_x86_64_display_media,check_x86_64_display_media
        self.assertEqual(check_x86_64_display_media.PROFILE,'research-native-display-two-media-v1')
        folder=ROOT/'build/codex-agent/r83be-display'/('host-compile-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for source,bits in [('arch/x86_64/video/boot_framebuffer.c',32),('arch/x86_64/video/boot_capture.c',32),
                            ('arch/x86_64/user/display_probe.c',64)]:
            obj=folder/(Path(source).stem+'.o')
            cmd=[find_zig(),'cc','-target','x86-freestanding-none' if bits==32 else 'x86_64-freestanding-none',
                 '-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin',
                 '-fno-stack-protector','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2',
                 '-I.','-Iuserspace/sdk/include','-c',source,'-o',obj]
            r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(obj.stem+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stderr[-2000:])
            self.assertEqual(obj.read_bytes()[:7],b'\x7fELF'+bytes((1 if bits==32 else 2,1,1)))

    def test_disabled_projection_and_mutations(self):
        from verify_x86_64_display import without_display_build_selector,MAKE_PARTS,PS_PARTS
        for name,make,parts in [('Makefile',True,MAKE_PARTS),('scripts/build-x86_64-bootstrap.ps1',False,PS_PARTS)]:
            source=(ROOT/name).read_text()
            projected=without_display_build_selector(source,make)
            self.assertEqual(without_display_build_selector(projected,make),projected)
            for part in parts:
                with self.assertRaises(ValueError):without_display_build_selector(source.replace(part,'',1),make)
                with self.assertRaises(ValueError):without_display_build_selector(source+part,make)
            with self.assertRaises(ValueError):without_display_build_selector(source+'\nNATIVE_DISPLAY hidden drift\n',make)
            self.assertIn('unrelated changed default',without_display_build_selector(source+'\nunrelated changed default\n',make))
        from verify_x86_64_terminal import default_sources
        from verify_x86_64_shell_session import default_projection
        self.assertEqual(len(default_sources()),9)
        self.assertEqual(len(default_projection()),8)

    def test_actual_core_o0_o2(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83be-display'/('host-core-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        asm=folder/'core.asm';obj=folder/'core.o'
        family=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        family=family[family.index('global family_profile_admit64'):family.index('; RDI profile-v1, RSI live profile-v2')]
        terminal=(ROOT/'arch/x86_64/proc/native_terminal.inc').read_text().split('; RUNTIME ADAPTER',1)[0]
        domain=(ROOT/'arch/x86_64/video/display_domain.inc').read_text()
        aggregate=domain[domain.index('global native_display_user_tile_range64'):domain.index('native_display_syscall64:')]
        validator='''
extern display_validate_backend
scheduler_validate_shell_range64:
    push r8
    push r9
    push r10
    push rcx
    push rdx
    push rsi
    push rdi
    mov rdi,rax
    mov rsi,rdx
    mov rdx,rcx
    call display_validate_backend
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop r10
    pop r9
    pop r8
    ret
'''
        def run(cmd,name):
            r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,text=True,
                timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2000:])
        for display in (0,1):
            asm.write_text('BITS 64\nsection .text\n%define REIST_NATIVE_PIO 1\n%define REIST_NATIVE_TERMINAL 1\n'+
                ('%define REIST_NATIVE_DISPLAY 1\n' if display else '')+
                '%define PF_R 4\n%include "arch/x86_64/video/display_core.inc"\n'+family+terminal+aggregate+validator,encoding='ascii')
            run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',asm,'-o',obj],'assemble-'+str(display))
            for level in ('0','2'):
                tag=str(display)+'-'+level;exe=folder/('core-'+tag+'.exe')
                run([find_zig(),'cc','-target','x86_64-windows-gnu','-O'+level,'-Wall','-Wextra','-Werror','-I.',
                     '-DEXPECT_DISPLAY='+str(display),'test/x86_64_display_host.c',obj,'-o',exe],'compile-'+tag)
                run([exe],'run-'+tag)

if __name__=='__main__':unittest.main()
