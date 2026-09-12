"""Executable native physical-memory contract, never host-RAM exhaustion."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid, re, ast, inspect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class NativeMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        cls.folder=ROOT/'build/codex-agent/r83z-memory'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True)
        cls.env=os.environ.copy();cls.env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        cls.env['ZIG_LOCAL_CACHE_DIR']=str(cls.folder/'cache')

    def run_command(self,cmd,name):
        r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=self.env,capture_output=True,text=True,
                         timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (self.folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
        self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2500:]);return r.stdout

    def test_actual_multiboot32_parser_and_paging(self):
        source=(ROOT/'arch/x86_64/mm/physical_memory.asm').read_text()
        # Exact production32-bit instructions and state; only private C64
        # bindings omitted and a cdecl register adapter added for WOW64.
        code=source.split('BITS 64',1)[0]
        code=code.replace('%include C_CORE_LAYOUT_PATH',
            '%define C_CORE_LAYOUT_VERSION 3\n%define C_NATIVE_MEMORY_ENTRY 1\n%define C_NATIVE_MEMORY_STATE_BYTES 4531096')
        code=re.sub(r'^global .*\n','',code,flags=re.M)
        code=code.replace('extern pml4_table','').replace('extern _x86_64_bootstrap_end','_x86_64_bootstrap_end equ 0xa00000')
        code=code.replace('extern serial_write64','')
        code+='\n'+source[source.index('section .bss\nalign 4'):]
        # NASM COFF uses 'bss', not ELF's nobits/alloc/write attributes.
        code=code.replace('section .memory_state nobits alloc noexec write align=4096',
                          'section .ram bss align=4096')
        code+='''
section .bss
alignb 4096
pml4_table: resb 4096
global _probe_bitmap,_probe_free,_probe_pd,_probe_pdpt,_probe_pml4
_probe_bitmap equ usable_bitmap
_probe_free equ free_frame_count
_probe_pd equ direct_page_directory
_probe_pdpt equ direct_pdpt
_probe_pml4 equ pml4_table
section .text
global _probe_init
_probe_init:
    push ebx
    push esi
    push edi
    push ebp
    mov eax,[esp+20]
    mov ebx,[esp+24]
    call x86_64_physical_memory_init32
    pop ebp
    pop edi
    pop esi
    pop ebx
    ret
'''
        asm=self.folder/'capture.asm';asm.write_text(code,encoding='ascii')
        obj=self.folder/'capture.o'
        self.run_command(['C:/tools/nasm-3.02/nasm.exe','-f','win32','-DX86_64_NATIVE_RAM=1',asm,'-o',obj],'capture-asm')
        for opt in ('0','2'):
            exe=self.folder/('capture-'+opt+'.exe')
            self.run_command([find_zig(),'cc','-target','x86-windows-gnu','-O'+opt,
                '-Wall','-Wextra','-Werror','test/x86_64_memory_map_host.c',obj,'-o',exe],'capture-compile-'+opt)
            self.assertIn('NATIVE_MEMORY_MAP_OK',self.run_command([exe],'capture-run-'+opt))

    def test_actual_protected_allocator_o0_o2(self):
        for opt in ('0','2'):
            exe=self.folder/('frames-'+opt+'.exe')
            cmd=[str(find_zig()),'cc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror','-DREIST_HOST_TEST',
                 '-DREIST_NATIVE_MEMORY_HOST_TEST','-I.','arch/x86_64/mm/native_memory.c',
                 'kernel/init/critical_object.c','test/x86_64_native_memory_host.c','-o',str(exe)]
            r=subprocess.run(cmd,cwd=ROOT,env=self.env,capture_output=True,text=True,timeout=60,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/('compile-'+opt+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stderr[-2500:])
            for case in ('normal','root','raw','summary','dual','busy','entered','region','hierarchy'):
                r=subprocess.run([str(exe),case],cwd=ROOT,capture_output=True,text=True,timeout=30,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (self.folder/(case+'-'+opt+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                self.assertIn('NATIVE_MEMORY_'+('HOST_OK' if case=='normal' else 'FAULT_CLOSED_OK'),r.stdout)

    def test_full_width_production_consumers(self):
        # Reuse the complete existing behavior matrices. Rebase only physical
        # fixture addresses/capacity, not expected lifetime/permission outcomes.
        cases=(
            ('user_access','mm/user_access','x86_64_user_access_host.c',
             {'0x4000000':'UINT64_C(0x100000000)','0x5000000':'UINT64_C(0x105000000)',
              '0x5008000':'UINT64_C(0x105008000)','0x8000000':'UINT64_C(0x400000000)'}),
            ('task_frames','mm/task_frames','x86_64_task_frames_host.c',
             {'0x04000000':'0x100000000','0x08000000':'UINT64_C(0x400000000)',
              '32769':'4194305','32768':'4194304'}),
            ('claim','mm/frame_claim','x86_64_spawn_oom_host.c',
             {'0x8000000':'UINT64_C(0x400000000)',
              '(uint64_t)(calls+1)*4096':'UINT64_C(0x100000000)+(uint64_t)(calls+1)*4096'}),
            ('mappings','mm/address_space','x86_64_mappings_host.c',
             {'0x07fff000':'UINT64_C(0x3fffff000)','0x04000000':'UINT64_C(0x100000000)',
              '0x08000000':'UINT64_C(0x400000000)'}),
            ('images','exec/image_frames','x86_64_image_contexts_host.c',
             {'0x08000000':'UINT64_C(0x400000000)',
              'address>>12':'(address-UINT64_C(0x100000000))>>12',
              '(uint64_t)page<<12':'UINT64_C(0x100000000)+((uint64_t)page<<12)',
              'free_count=32760':'free_count=4194296',
              'skew_before=32769':'skew_before=4194305'}))
        for name,source,fixture,changes in cases:
            code=(ROOT/'test'/fixture).read_text()
            for before,after in changes.items():
                pattern=(r'(?<!\w)'+re.escape(before)+r'(?!\w)') if before.startswith('0x') else re.escape(before)
                self.assertRegex(code,pattern);code=re.sub(pattern,lambda _:after,code)
            c=self.folder/(name+'.c');c.write_text(code,encoding='ascii')
            obj=self.folder/(name+'.o')
            self.run_command(['C:/tools/nasm-3.02/nasm.exe','-f','win64','-DX86_64_NATIVE_RAM=1',
                ROOT/('arch/x86_64/'+source+'.asm'),'-o',obj],name+'-asm')
            for opt in ('0','2'):
                exe=self.folder/(name+'-'+opt+'.exe')
                self.run_command([find_zig(),'cc','-target','x86_64-windows-gnu','-O'+opt,
                    '-Itest','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                    '-mno-red-zone','-fno-sanitize=all',
                    c,obj,'-o',exe],name+'-compile-'+opt)
                self.assertIn('_HOST_OK',self.run_command([exe],name+'-run-'+opt))

    def test_memory_oracle_preserves_exact_retirement_contract(self):
        import run_qemu_x86_64_native_memory as guest
        import run_qemu_x86_64_process_run as old
        class Capacity(ast.NodeTransformer):
            def visit_Constant(self,node):
                if type(node.value)==int:
                    node.value={0x8000000:0x400000000,32768:4194304}.get(node.value,node.value)
                return node
        self.assertEqual(ast.dump(Capacity().visit(ast.parse(inspect.getsource(old.validate_trace)))),
                         ast.dump(ast.parse(inspect.getsource(guest.validate_trace))))
        rows=[dict(slot=s,generation=r*4+s+1,state=4) for r in range(2) for s in range(4)]
        records=[(m,s,s+1,4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)]
        records += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]
        records += [(5,s,20+s,4) for s in range(4)]+[(6,1,31,8),(6,1,32,8),(6,0,30,4)]
        records += [(8,x['slot'],x['generation'],x['state']) for x in rows]
        frames=[0,0x100001000]+[0]*6+[0x100002000,0x100006000,0x100005000,0x100004000,0x100003000]
        trace='NATIVE_MEMORY_MAP_OK ram=4096 managed=1046000 huge=2042 mixed=3 high=1\n'
        for seq,(mode,slot,gen,state) in enumerate(records,1):
            if mode==8:
                if not slot&1:
                    for nr,result in ((50,0),(54,-110)):
                        trace+=f'NATIVE_IPC_BLOCK slot={slot} gen={gen} nr={nr} deadline=20 result=-4095\n'
                        trace+=f'NATIVE_IPC_READY slot={slot} gen={gen} nr={nr} deadline=20 result={result}\n'
                trace+=f'NATIVE_IPC_COPYOUT slot={slot} gen={gen} bytes=140 cr3=1\n'*(5 if slot&1 else 2)
                trace+=f'NATIVE_IPC_FENCE slot={slot} gen={gen}\nPROCESS_FENCE_OK seq={seq} slot={slot} gen={gen}\n'
            trace+=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=100003000 active=117000 before=1000000 fp=1 frames='+','.join(f'{f:x}' for f in frames)+'\n'
            trace+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in frames if f)
            trace+=f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=1000006 zero=1\n'
            if seq in (21,25):
                run=1 if seq==21 else 2
                trace+=f'PROCESS_ZERO_OK run={run} zero=1 free=1000000 initial=1000000 reaps=4 generation={run*4} ticks=32\n'
        guest.validate_memory(trace,rows,4096)
        bads=(trace+trace,trace.replace('PROCESS_FENCE_OK','MISSING',1),trace.replace('zero=1','zero=0',1),
              trace.replace('100001000','400000000'),trace.replace('100001000','100001001'),
              trace.replace('100001000','4001000'),trace.replace('managed=1046000','managed=1048577'),
              trace.replace('high=1','high=0'),trace.replace('mixed=3','mixed=513'),
              trace.replace('after=1000006','after=1000007',1),trace.replace('fp=1','fp=0',1),
              trace.replace('gen=8','gen=7'),trace.replace('TASK_FRAMES_FREE','MISSING',1),
              trace.replace('bytes=140','bytes=139',1))
        for bad in bads:
            with self.assertRaises((ValueError,RuntimeError)):guest.validate_memory(bad,rows,4096)
        for ram in (0,512,16384):
            with self.assertRaises(ValueError):guest.ipc.capture(Path('unused'),self.folder,'',ram)

if __name__=='__main__':unittest.main()
