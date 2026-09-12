"""Real Ring3 ELF adapter and production admission at O0/O2; no model kernel."""
from pathlib import Path
import os,sys,subprocess,uuid,unittest,struct,re
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class ImportTests(unittest.TestCase):
    def test_import_oracles(self):
        from test_x86_64_task_startup import StartupTests
        import run_qemu_x86_64_task_startup as r
        for oom in (None,0,1,2,3,6,9):
            serial,trace=StartupTests.sample(oom);count=9 if oom is not None else 10
            def slot(gen):return 3 if (gen-1)%count+1==4 else 2
            def receipt(m):
                fields=list(struct.unpack('<4I2Q',bytes.fromhex(m[1])))
                if fields[0]>=2:fields[0]=slot(fields[1])
                return 'REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',*fields).hex().upper()
            serial=r.family.process.REAP.sub(receipt,serial)
            def frame(m):
                return m[0].replace('slot='+m[3],'slot='+str(slot(int(m[4])))) if int(m[2])==8 and int(m[3])>=2 else m[0]
            trace=r.BEFORE.sub(frame,trace)
            def entry(m):
                label,s,g,rest=m.groups();s=int(s);g=int(g)
                if s>=2:
                    s=slot(g);rest=re.sub(r'image=\d+',f'image={s+5}',rest)
                row=f'{label} slot={s} gen={g}{rest}'
                if label=='FAMILY_START' and s>=2:
                    prefix=f'IMPORT_COPY gen={g} bytes=36896 immutable=1\n'
                    if s==3:prefix+=f'IMPORT_PAIR first={g-1} second={g} private=1\n'
                    row=prefix+row
                return row
            trace=re.sub(r'(FAMILY_START|FAMILY_FENCE) slot=(\d+) gen=(\d+)([^\n]*)',entry,trace)
            trace=trace.replace('STARTUP_SCRUB','IMPORT_SCRUB bytes=36896 complete=1\nSTARTUP_SCRUB')
            self.assertEqual(r.validate(serial,trace,oom,True),count*2)
            for old,new in (('image=7','image=5'),('image=8','image=7'),('IMPORT_COPY','MISSING'),('IMPORT_PAIR','MISSING'),('IMPORT_SCRUB','MISSING'),('immutable=1','immutable=0'),('private=1','private=0')):
                with self.assertRaises(ValueError):r.validate(serial,trace.replace(old,new,1),oom,True)
            with self.assertRaises(ValueError):r.validate(serial,trace,oom,False)

    def test_actual_parser_and_admission(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ag-import'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        source='BITS 64\n%define REIST_NATIVE_PROGRAMS 1\n%define REIST_NATIVE_LIFECYCLE 1\nsection .text\nglobal process_run_admit64\n'
        source+=(ROOT/'arch/x86_64/proc/process_run.inc').read_text().split('; Read-only whole-run')[0]
        source+=(ROOT/'arch/x86_64/proc/task_family.inc').read_text().split('; RUNTIME ADAPTER')[0]
        source+=(ROOT/'arch/x86_64/exec/boot_programs.inc').read_text().split('; END_PURE_ADMISSION')[0]
        source+=(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        family=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        source+='\nPF_R equ 4\n'+family[family.index('family_import_range64:'):family.index('family_syscall64:')]
        source+='''
extern range_count,range_fail,range_base
global import_range_test
import_range_test:
    sub rsp,8
    mov rax,rdi
    call family_import_range64
    add rsp,8
    ret
scheduler_validate_shell_range64:
    cmp ecx,4
    jne .bad
    cmp rax,[rel range_base]
    jne .bad
    cmp dword [rel range_count],36
    je .last
    cmp edx,1024
    jne .bad
    jmp .admit
.last:
    cmp edx,32
    jne .bad
.admit:
    add [rel range_base],rdx
    mov eax,[rel range_count]
    inc dword [rel range_count]
    cmp eax,[rel range_fail]
    je .bad
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret
'''
        (folder/'source.asm').write_text(source,encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name,expected=0):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,expected,(r.stdout+r.stderr)[-2000:]);return r.stdout
        obj=folder/'code.o';run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',folder/'source.asm','-o',obj],'asm')
        import test_x86_64_boot_programs as old
        import build_x86_64_boot_programs as producer
        vectors=[old.elf()]
        for rights in (4,6):
            b=bytearray(old.elf());struct.pack_into('<I',b,124,rights);vectors.append(bytes(b))
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include','test/x86_64_image_import_host.c','userspace/sdk/lib/x86_64/image.c',obj,'-o',exe],opt+'-build')
            self.assertIn('IMAGE_IMPORT_HOST_OK',run([exe],opt+'-run'))
            for n,raw in enumerate(vectors):
                inp=folder/f'{n}.elf';out=folder/f'{opt}-{n}.bin';inp.write_bytes(raw)
                run([exe,inp,out],f'{opt}-vector-{n}');self.assertEqual(out.read_bytes(),producer.prepare(raw,[]))
            for n,offset in enumerate((0,4,16,18,20,24,32,48,52,54,56,64,68,72,80,96,111,112,120,124,135,143,159,167,168)):
                raw=bytearray(old.elf());raw[offset]^=128
                try:producer.prepare(raw,[])
                except ValueError:pass
                else:continue
                inp=folder/f'bad-{n}.elf';out=folder/f'bad-{opt}-{n}.bin';inp.write_bytes(raw);out.write_bytes(b'preserve')
                run([exe,inp,out],f'{opt}-bad-{n}',1);self.assertEqual(out.read_bytes(),b'preserve')

if __name__=='__main__':unittest.main()
