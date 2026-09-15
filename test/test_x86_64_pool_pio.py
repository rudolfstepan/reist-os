"""Actual eight-slot PIO mechanisms; hardware adapters only, no model kernel."""
from pathlib import Path
import ast,copy,hashlib,json,os,struct,subprocess,sys,types,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


def kernel_asm():
    source=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
    core=source.split('; END_PIO_CORE',1)[0]
    adapter=source.split('native_pio_syscall64:',1)[1].split('section .data',1)[0]
    adapter=adapter.replace('    cli','    nop').replace('extern serial_init64\n','').replace('extern halt64\n','')
    return '''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_POOL_PIO 1
%define REIST_NATIVE_WIDE 1
%include "arch/x86_64/mm/native_layout.inc"
TASK_STATE equ 0
TASK_GENERATION equ 8
TASK_FREE equ 0
TASK_READY equ 1
TASK_BLOCKED equ 6
PF_R equ 4
PF_W equ 2
section .text
extern native_pio_in8,native_pio_in16,native_pio_out8
'''+core+'\nnative_pio_syscall64:'+adapter+'''
section .rodata
native_pio_fatal_message: db 0
section .bss
align 16
global native_pio_state,native_pio_request,scheduler_tasks,family_records
global syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9
global scheduler_current_slot,scheduler_last_tick,host_fatal
native_pio_state: resq 8
native_pio_request: resq 8
scheduler_tasks: resb 8192
family_records: resb 512
scheduler_current_slot: resq 1
scheduler_last_tick: resq 1
syscall_rdi: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
host_fatal: resq 1
host_stack: resq 1
section .text
global pio_adapter
pio_adapter:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    sub rsp,8
    mov [rel host_stack],rsp
    mov qword [rel host_fatal],0
    mov eax,[rel scheduler_current_slot]
    shl eax,NATIVE_TASK_SHIFT
    lea r12,[rel scheduler_tasks]
    add r12,rax
    cmp edi,1
    je .terminal
    cmp edi,2
    je .finish
    jmp native_pio_syscall64
.terminal:
    call native_pio_terminal64
    xor eax,eax
    jmp process_run_resume64
.finish:
    call native_pio_finish64
    xor eax,eax
    jmp process_run_resume64
serial_init64:
serial_write64:
    ret
halt64:
    mov qword [rel host_fatal],1
    mov rax,-84
    jmp process_run_resume64
; All C test requests are pinned valid objects. Pointer validation is a
; hardware/address-space boundary fake, not a new pointer acceptance proof.
scheduler_validate_shell_range64:
    mov eax,1
    ret
process_run_syscall64:
.invalid:
    mov rax,-22
process_run_resume64:
    mov rsp,[rel host_stack]
    add rsp,8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret
'''


class PoolPioTests(unittest.TestCase):
    def test_pool_fixture_optimization_commands(self):
        # Execute the actual producer's complete argument expression; no
        # compiler, output publication or modeled replacement build policy.
        current=ROOT/'scripts/build_x86_64_boot_programs.py'
        original=ROOT/'build/codex-agent/r83ao-pool-pio/candidate-02/source/scripts__build_x86_64_boot_programs.py'
        def expression(path):
            tree=ast.parse(path.read_text())
            calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and
                   n.func.id=='run' and n.args and isinstance(n.args[0],ast.List) and '-DPROGRAM_ID=' in ast.unparse(n)]
            self.assertEqual(len(calls),1)
            return compile(ast.Expression(calls[0].args[0]),str(path),'eval')
        a,b=expression(original),expression(current)
        for profile in ('plain','family','startup','import','pio','block','wide','block_profile','filesystem','file_launch','task_pool','pool_pio'):
            flags={k:False for k in ('pio','pool_pio','task_pool','wide','block','block_profile','filesystem','file_launch','import_image','startup','family')}
            if profile!='plain':flags[profile if profile!='import' else 'import_image']=True
            if profile in ('pool_pio','file_launch','filesystem','block_profile','block','pio'):flags['pio']=True
            for n in range(4):
                env=dict(flags,cc=['cc'],case=0,family_case=0,startup_case=0,pio_case=0,memory_case=0,block_profile_case=0,
                         filesystem_case=0,filesystem_layout=2,file_launch_case=0,n=n,extra=['-DTEST_ONLY=1'],obj=Path('unit.o'))
                old=eval(a,{'__builtins__':{}},env);new=eval(b,{'__builtins__':{}},env)
                if profile=='pool_pio':
                    self.assertEqual([v for v in new if isinstance(v,str) and v.startswith('-O')],['-O2'],
                                     'PoolPIO fixture must use deadline-oriented O2')
                    old[old.index('-Oz')]='-O2'
                self.assertEqual(new,old)

    @staticmethod
    def metadata_pairs():
        import verify_x86_64_pool_pio as v
        baseline=v.read(v.BASE/'baseline.json');current=v.binary_map(v.BASE/'pool-reference/x86_64')
        result=[]
        for name in ('programs/program0.o','programs/program1.o'):
            old=ROOT/baseline['old_profiles']['pool'][name]['path'];new=ROOT/current[name]['path']
            result.append((old.read_bytes(),new.read_bytes(),'./'+str(old.parent.relative_to(ROOT)),'./'+str(new.parent.relative_to(ROOT))))
        return result

    def test_runtime_reference_reuse_is_exact(self):
        import tomllib
        import verify_x86_64_pool_pio as v
        old=v.read(v.BASE/'candidate-01/frozen-candidate.json')
        before=(v.BASE/'candidate-01/source'/v.PRODUCER.replace('/','__')).read_bytes()
        after=(ROOT/v.PRODUCER).read_bytes();v.producer_optimization_binding(before,after)
        for raw in (after+b'\n',after.replace(b"and not pool_pio",b"or pool_pio"),
                    after.replace(b"'-Oz'",b"'-O2'"),after.replace(b'--strip-all',b'--discard-all')):
            with self.assertRaises(ValueError):v.producer_optimization_binding(before,raw)
        new=copy.deepcopy(old);new['directory']='build/codex-agent/r83ao-pool-pio/candidate-03'
        new['runtime_correction']=v.link(v.RUNTIME/'expected-red.json')
        new['package']=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())['packages'][0]
        new['commands']=sum((new['package'][name] for name in ('targeted_tests','package_tests','runtime_tests')),[])
        new['source_inputs']={name:v.digest(ROOT/name) for name in old['source_inputs']}
        def sign(obj):obj['candidate']=hashlib.sha256(json.dumps(obj['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        sign(new)
        for index in (13,14):
            receipt=v.read(v.BASE/'candidate-01'/f'gate-{index:02d}.json')
            v.build_reuse_binding(new,old,receipt,index)
            for name in ('Makefile','arch/x86_64/user/pool_pio.c','scripts/run_qemu_x86_64_pool_pio.py',v.PRODUCER):
                bad=copy.deepcopy(new);bad['source_inputs'][name]='0'*64;sign(bad)
                with self.subTest(dependency=name),self.assertRaises(ValueError):v.build_reuse_binding(bad,old,receipt,index)
            for key in ('runtime_tests','package_tests','targeted_tests'):
                bad=copy.deepcopy(new);bad['package'][key][0]+=' --changed'
                with self.assertRaises(ValueError):v.build_reuse_binding(bad,old,receipt,index)
        with self.assertRaises(ValueError):v.build_reuse_binding(new,old,v.read(v.BASE/'candidate-01/gate-15.json'),15)
        original=v.runtime_package_original(new['package'])
        self.assertEqual(original,v.read(v.BASE/'candidate-02/frozen-candidate.json')['package'])

    def test_original_cpu32_record_still_fails(self):
        import run_qemu_x86_64_pool_pio as r
        folder=r.BASE/'guests/attempt-afed6bc3d70348c19ec9ff868f7bf0c9'
        summary=json.loads((folder/'summary.json').read_text());guest=folder/'guest-6-8192'
        self.assertFalse(summary['passed']);self.assertEqual(summary['error'],'pool PIO terminal outcome')
        with self.assertRaisesRegex(ValueError,'terminal outcome'):
            r.validate((guest/'guest.log').read_text(),(guest/'frame-trace.log').read_text(),6,None,
                       summary['allocations'],summary['child_sha256'])

    def test_debug_metadata_real_objects(self):
        import verify_x86_64_pool_pio as v
        self.assertTrue(hasattr(v,'debug_object_equivalent'),'bounded debug metadata comparison missing')
        for old,new,old_directory,new_directory in self.metadata_pairs():
            self.assertNotEqual(old,new)
            self.assertRegex(v.debug_object_equivalent(old,new,old_directory,new_directory),'^[0-9a-f]{64}$')

    def test_debug_metadata_rejects_non_path_drift(self):
        import verify_x86_64_pool_pio as v
        for old,new,old_directory,new_directory in self.metadata_pairs():
            h,sections,order=v.debug_object_sections(new)
            def reject(raw,other=new_directory):
                with self.assertRaises(ValueError):v.debug_object_equivalent(old,bytes(raw),old_directory,other)
            for size in (0,63,len(new)-1,len(new)+1,1048577):reject(new[:size] if size<=len(new) else new+bytes(size-len(new)))
            for offset,fmt,value in ((4,'B',1),(5,'B',2),(16,'H',2),(18,'H',3),(20,'I',0),(24,'Q',1),
                (32,'Q',64),(40,'Q',0),(48,'I',1),(52,'H',63),(54,'H',56),(56,'H',1),(58,'H',63),(60,'H',129),(62,'H',65535)):
                bad=bytearray(new);struct.pack_into('<'+fmt,bad,offset,value);reject(bad)
            field_offsets=(0,4,8,16,24,32,40,44,48,56)
            for name,section in sections.items():
                row=section['header'];index=section['index']
                for field,offset in enumerate(field_offsets):
                    bad=bytearray(new);fmt='I' if field in (0,1,6,7) else 'Q'
                    struct.pack_into('<'+fmt,bad,h[5]+index*64+offset,row[field]^(1<<(31 if fmt=='I' else 63)))
                    with self.subTest(section=name,field=field):reject(bad)
                if not section['data']:continue
                offsets=range(len(section['data'])) if name in ('.debug_line','.rela.debug_line') else {0,len(section['data'])//2,len(section['data'])-1}
                for pos in offsets:
                    bad=bytearray(new);bad[row[4]+pos]^=1
                    with self.subTest(section=name,byte=pos):reject(bad)
            cursor=64
            for index in order:
                entry=next(e for e in sections.values() if e['index']==index);first=entry['header'][4]
                for pos in range(cursor,first):
                    bad=bytearray(new);bad[pos]=1;reject(bad)
                cursor=first+len(entry['data'])
            for directory in (old_directory,new_directory.replace('pool-reference','other'),new_directory+'/..',new_directory+'\0',new_directory.replace('programs-','programs-0')):
                reject(new,directory)
            # A nonzero gap or relocation/program mismatch remains a failure
            # even if every loadable byte would still be unchanged.
            self.assertEqual(len(sections['.rela.debug_line']['data']),24)

    def test_build_reuse_exact_dependencies_and_receipts(self):
        import verify_x86_64_pool_pio as v
        def sign(obj):obj['candidate']=hashlib.sha256(json.dumps(obj['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        old=dict(directory='build/codex-agent/r83ao-pool-pio/candidate-01',source_inputs={'Makefile':'a'*64,
            **{n:'b'*64 for n in v.METADATA_FILES}},tools_sha256={'compiler':'c'*64},commands=['gate'+str(n) for n in range(20)],package=dict(profile='pool'))
        sign(old);new=copy.deepcopy(old);new['directory']='build/codex-agent/r83ao-pool-pio/candidate-02'
        new['package']['metadata_renewal_files']=list(v.METADATA_FILES);new['source_inputs'][v.METADATA_FILES[-1]]='d'*64;sign(new)
        for index in (13,14,15):
            receipt=dict(candidate=old['candidate'],command=old['commands'][index-1],passed=True,exit_code=0,elapsed=1,artifacts={'build/kernel':'e'*64})
            v.build_reuse_binding(new,old,receipt,index)
            for where,keys,value in (('new',['source_inputs','Makefile'],'z'*64),('new',['tools_sha256','compiler'],'z'*64),
                ('new',['directory'],'wrong'),('old',['directory'],'wrong'),('new',['package','profile'],'changed'),
                ('new',['commands'],['wrong']*20),('new',['candidate'],'wrong'),('receipt',['candidate'],'wrong'),
                ('receipt',['command'],'wrong'),('receipt',['passed'],False),('receipt',['exit_code'],1),('receipt',['elapsed'],181),
                ('receipt',['elapsed'],-1),('receipt',['execution'],'REUSED'),('receipt',['artifacts'],{})):
                values=dict(new=copy.deepcopy(new),old=copy.deepcopy(old),receipt=copy.deepcopy(receipt));target=values[where]
                for key in keys[:-1]:target=target[key]
                target[keys[-1]]=value
                if keys[0]=='source_inputs':sign(values[where])
                with self.subTest(index=index,where=where,keys=keys):
                    with self.assertRaises(ValueError):v.build_reuse_binding(values['new'],values['old'],values['receipt'],index)
            for add in (False,True):
                bad=copy.deepcopy(new)
                if add:bad['source_inputs']['new.c']='x'*64
                else:del bad['source_inputs']['Makefile']
                sign(bad)
                with self.assertRaises(ValueError):v.build_reuse_binding(bad,old,receipt,index)
        for index in (12,16,True):
            with self.assertRaises(ValueError):v.build_reuse_binding(new,old,receipt,index)

    @staticmethod
    def functions(code,*names,**environment):
        tree=ast.parse(code);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
        if {n.name for n in nodes}!=set(names):raise ValueError('generated function binding')
        exec(compile(ast.Module(nodes,[]),'<actual observer>','exec'),environment)
        return environment

    def build(self,asm,source,label,defines=()):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ao-pool-pio'/('host-'+label+'-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        (folder/'source.asm').write_text(asm,encoding='ascii')
        if isinstance(source,str):
            (folder/'source.c').write_text(source,encoding='ascii');source=folder/'source.c'
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name,timeout):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,capture_output=True,text=True,
                timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:]);return r.stdout
        obj=folder/'code.o';run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',folder/'source.asm','-o',obj],'asm',90)
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                *defines,source,obj,'-o',exe],opt+'-build',90)
            self.assertIn(label+'_OK',run([exe],opt+'-run',30))

    def test_actual_slot_owner_admission(self):
        self.build(kernel_asm(),ROOT/'test/x86_64_pool_pio_host.c','POOL_PIO_KERNEL')

    def test_actual_ring3_service_all_owners(self):
        source=(ROOT/'test/x86_64_block_profile_host.c').read_text()
        source=source.replace('"x86_64_block_service_host.c"','"'+(ROOT/'test/x86_64_block_service_host.c').as_posix()+'"')
        source=source.replace('int main(void){limits();','int profile_vectors_main(void){limits();')
        source+=USER_VECTORS
        self.build('BITS 64\nsection .text\n',source,'POOL_PIO_USER',['-DREIST_NATIVE_POOL_PIO=1'])

    def test_actual_trace_eight_slot_bounds(self):
        source=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
        body=source.split('; BEGIN_PIO_TRACE',1)[1].split('; END_PIO_TRACE',1)[0]
        harness=(ROOT/'test/x86_64_pio_trace_host.c').read_text()
        asm='BITS 64\n%define REIST_NATIVE_TASK_POOL 1\n%define REIST_NATIVE_POOL_PIO 1\n%define REIST_NATIVE_WIDE 1\n%include "arch/x86_64/mm/native_layout.inc"\nsection .text\n'+body
        asm+='\nglobal native_pio_trace_out64,native_pio_trace_data64,native_pio_trace_clear64\n'
        asm+=harness.split('/* ASM\n',1)[1].split('\nASM */',1)[0]
        asm+='\nsection .bss\nalign 16\nglobal trace_guard_before,native_pio_trace,trace_guard_after,native_pio_state,native_pio_request,scheduler_tasks,scheduler_current_slot,family_records,capture_registers,capture_after,trace_data\n'
        asm+='trace_guard_before: resq 2\nnative_pio_trace: resb 12304\ntrace_guard_after: resq 2\nnative_pio_state: resb 64\nnative_pio_request: resb 64\nscheduler_tasks: resb 8192\nscheduler_current_slot: resq 1\nalignb 16\nfamily_records: resb 512\ncapture_registers: resq 17\nalignb 16\ncapture_after: resq 17\nalignb 16\ntrace_data: resb 64\n'
        # Same exhaustive actual register/ring/data/zero tests for the explicit
        # new capacity. Move the formerly invalid4 witness to invalid8.
        harness=harness.replace('scheduler_tasks[512]','scheduler_tasks[1024]').replace('family_records[32]','family_records[64]')
        harness=harness.replace('n&3','n&7').replace('scheduler_current_slot=4','scheduler_current_slot=8')
        harness=harness.replace(' puts("pio_trace_OK',r'''
 for(unsigned owner=2;owner<8;owner++)for(unsigned caller=0;caller<8;caller++){
  setup();scheduler_current_slot=caller;scheduler_tasks[caller*128+1]=19;
  family_records[owner*8+1]=1ULL<<32;
  native_pio_state[0]=(23ULL<<32)|owner;native_pio_state[1]=~native_pio_state[0];
  capture_out();C(intact() && native_pio_trace[0]==1 && !native_pio_trace[1]);
  uint64_t *r=native_pio_trace+2;C(r[2]==native_pio_state[0] && r[12]==caller && r[13]==19 && r[14]==1ULL<<32);
 }
 puts("POOL_PIO_TRACE_OK''')
        self.build(asm,harness,'POOL_PIO_TRACE')

    def test_generated_observer_and_oom_scope(self):
        import run_qemu_x86_64_pool_pio as r
        code=r.observer_body();tree=ast.parse(code)
        writes=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_memory']
        self.assertEqual(len(writes),1);self.assertEqual(ast.unparse(writes[0].args[1]),"struct.pack('<Q', CASE)")
        sets=[ast.unparse(n) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and
              n.func.attr=='execute' and n.args and isinstance(n.args[0],(ast.Constant,ast.BinOp)) and 'set $' in ast.unparse(n.args[0])]
        self.assertEqual(len(sets),3);self.assertTrue(all(any(s in n for s in ('set $rax=0','set $rsp=$rsp+8','set $rip=')) for n in sets))
        for symbol in ('cold_control_paths','image_context','release_begin','finish','trace_before_clear','trace_after_clear','rpc','source_pending'):
            self.assertIn(symbol,code)
        for case in range(16):
            self.assertEqual(r.dimensions(case),(case if case<=5 else 5,(case if case<=5 else 5)+2,(case if case<=5 else 5)+(3 if case==11 else 4)))
        for bad in (-1,16,True,1.0):
            with self.assertRaises(ValueError):r.dimensions(bad)
        for driver in (False,True):
            for owner in (1<<32,10<<32):
                commands=[];events=[]
                env=self.functions(code,'allocation',OOM=2,inject_driver=driver,allocation_owner=owner,
                    injected=set(),allocation_count=2,allocator=types.SimpleNamespace(enabled=True),
                    q=lambda a:0x1234,reg=lambda n:0x9876,gdb=types.SimpleNamespace(execute=commands.append),emit=lambda *a,**k:events.append((a,k)))
                env['allocation']();self.assertEqual(len(commands),3 if driver else 0)
                self.assertEqual(env['allocation_count'],2 if driver else 3)
                if driver:
                    self.assertEqual(env['injected'],{owner});self.assertFalse(env['allocator'].enabled)
                    env['allocation']();self.assertEqual(len(commands),3);self.assertEqual(env['allocation_count'],3)
        # Exact copied-source isolation before another CREATE, not a hot-loop
        # observer writing guest bytes or reading an incompletely filled heap.
        self.assertIn("call==22",r.SYSCALL);self.assertNotIn('call==41',r.SYSCALL)
        self.assertIn("slot!=entry['slot']:continue",r.SYSCALL)
        self.assertIn('source_pending=gen',r.CREATE_END)
        compile(r.fatal_observer(dict(s={n:n for n in ()}),ROOT/'build/codex-agent',r.FATAL_CASES[0]).split('python\n',1)[1].rsplit('\nend\n',1)[0],'<fatal>','exec')

    def test_build_selectors_and_actual_fixture_compile(self):
        import build_x86_64_boot_programs as producer
        base=dict(case=0,family=True,startup=True,import_image=True,wide=True,task_pool=True,pool_pio=True,pio=True,block=True,block_profile=True)
        for name,value in [('pool_pio',1),('task_pool',False),('wide',False),('import_image',False),('startup',False),
            ('family',False),('pio',False),('block',False),('block_profile',False),('filesystem',True),('file_launch',True),
            ('memory_case',1),('case',1),('family_case',1),('startup_case',1),('pio_case',1),('block_profile_case',1),
            ('filesystem_case',1),('file_launch_case',1),('filesystem_layout',0)]:
            with self.subTest(selector=name),patch.object(producer.Path,'mkdir') as mkdir,patch.object(producer.subprocess,'run') as run:
                with self.assertRaises(ValueError):producer.build(ROOT/'build/codex-agent/r83ao-pool-pio/rejected',[],[],[],**{**base,name:value})
                mkdir.assert_not_called();run.assert_not_called()
        # Compile the actual new Ring3 C units as a targeted host toolchain
        # check, not another kernel/catalog build. All PROGRAM_ID branches.
        folder=ROOT/'build/codex-agent/r83ao-pool-pio'/('host-producer-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        header=folder/'blob.h';header.write_text('static const unsigned char import_blob[1]={0};\n')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for n in range(4):
            command=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror',
                '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
                '-Iuserspace/sdk/include','-DREIST_NATIVE_POOL_PIO=1','-DPROGRAM_ID='+str(n),
                *(['-include',str(header)] if n==0 else []),'-c','arch/x86_64/user/pool_pio.c','-o',str(folder/f'program{n}.o')]
            result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/f'program{n}.log').write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])
        # Both entrypoints fail before creating output for incompatible targets.
        for args in (['-NativePoolPIO','-NativeFileLaunch'],['-NativeTaskPool','-NativePIO'],['-NativePoolPIO','-MemoryCase','1']):
            target=folder/('rejected-'+str(len(list(folder.glob('reject-*.log')))))
            result=subprocess.run(['C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                *args,'-OutputDirectory',target.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/('reject-'+str(len(list(folder.glob('reject-*.log'))))+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertNotEqual(result.returncode,0);self.assertIn(b'excludes',result.stdout+result.stderr);self.assertFalse(target.exists())
        make=(ROOT/'Makefile').read_text();ps=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text()
        self.assertIn('$(if $(filter 1,$(X86_64_NATIVE_POOL_PIO)),--pool-pio,)',make)
        self.assertIn('-DREIST_NATIVE_POOL_PIO=1',make)
        self.assertIn('X86_64_NATIVE_POOL_PIO=$([int]$NativePoolPIO.IsPresent)',ps)
        self.assertLess(ps.index('if ($NativePoolPIO)'),ps.index('if ($NativeTaskPool)'))

    @staticmethod
    def sample(case):
        import run_qemu_x86_64_pool_pio as r
        fillers,driver,per=r.dimensions(case);count=30;sha='9'*64;oom={13:0,14:15,15:29}.get(case)
        common=[m for m in r.transport.REQUIRED_MARKERS if 'SHELL' not in m];cut=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
        serial='\n'.join(common[:cut])+'\n';events=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]
        def emit(kind,**fields):events.append(dict(kind=kind,**fields))
        def retire(slot,gen,status,state=4):
            nonlocal serial
            serial+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,state,32 if status==256 else 1,0x410078).hex().upper()+'\n'
            emit('release',slot=slot,gen=gen,frames=14,before=1000000,after=1000014,fenced=1)
        def start(slot,gen,parent=0,kind=-1,round_=-1):
            if slot>=2:
                emit('copy',gen=gen,bytes=r.SIZE,sha=sha);emit('create',gen=gen,owner=parent<<32,slot=slot,acquired=count)
            emit('start',slot=slot,gen=gen,parent=parent,role=kind,round=round_,image=slot+3 if slot<2 else slot+5,pages=20,private=10,live=slot+1)
            if slot==0:emit('mode',slot=0,gen=gen,address=0x415008,physical=0x100000008+gen*4096,before=0,value=case)
            if slot>=2:
                emit('source',gen=gen,bytes=r.SIZE,poison=165)
                data=bytes((i^slot^0x5a)&255 for i in range(8192));emit('witness',gen=gen,parent=parent,heap=8192,immutable=1,sha=hashlib.sha256(data).hexdigest())
        for run in range(2):
            base=run*per;start(0,base+1);start(1,base+2)
            for n in range(fillers):start(n+2,base+n+3,base+1,256)
            if oom is not None:
                emit('oom',owner=(base+1)<<32,acquired=oom);emit('rollback',owner=(base+1)<<32,acquired=oom,free=1000000,before=1000000)
            for round_ in range(1 if case==11 else 2):
                gen=base+fillers+3+round_;kind=0 if round_ else 8 if case==11 else case if case in (7,8,9,10) else 0
                start(driver,gen,base+1,kind,round_);emit('bind',gen=gen,owner=gen<<32|driver)
                emit('ready',gen=gen,limit=1,capacity=19 if case==12 else 128,deadline=3000)
                if case!=12:
                    emit('request',gen=gen,sequence=1,lba=1,deadline=2000)
                    if kind in (7,8,9):emit('partial',gen=gen,bytes=256,mode=kind)
                    if kind in (0,10):emit('reply',gen=gen,sequence=1,status=0,bytes=512,bad=int(kind==10),deadline=2000)
                    if case!=11:
                        data=bytes([0xcc])*512 if kind else bytes((i^17^0xa5)&255 for i in range(512))
                        emit('result',gen=gen,sequence=1,status=-71 if kind==10 else -32 if kind else 0,bytes=512,sha=hashlib.sha256(data).hexdigest())
                if kind==7:emit('fault',slot=driver,gen=gen,vector=6)
                if case==11:emit('fault',slot=0,gen=base+1,vector=6)
                if case==11 or kind in (8,10):emit('cancel',slot=driver,gen=gen,state=6,reason=3 if case==11 else 2)
                count_=0 if case==12 else 768 if kind in (7,8,9) else 1024
                raw=b''.join(bytes((i^lba*17^0xa5)&255 for i in range(512)) for lba in (0,1))[:count_]
                emit('retire',gen=gen,identify=0 if case==12 else 512,data=count_,lbas=[] if case==12 else [0,1],sha=hashlib.sha256(raw).hexdigest(),fenced=1)
                status=0 if case==11 or kind in (8,10) else 134 if kind==7 else 256 if kind==9 else 89 if case==12 else 80
                retire(driver,gen,status,3 if kind or case==11 else 4)
            for n in range(fillers):
                gen=base+n+3;emit('cancel',slot=n+2,gen=gen,state=6,reason=3 if case==11 else 2);retire(n+2,gen,0,3)
            retire(0,base+1,134 if case==11 else 79 if case==12 else 78,3 if case==11 else 4)
            emit('peer',gen=base+2,sleeps=25);retire(1,base+2,77)
            serial+=r.wide.process.DONE+'\n'
            emit('trace_drained',run=run+1,events=100,sha='1'*64);emit('trace_clean',run=run+1,bytes=12304)
            emit('finish',run=run+1,free=1000010,initial=1000010,tasks=per,generation=(run+1)*per,zero=1)
        serial+='\n'.join(common[cut:])+'\n'+r.wide.process.SUCCESS+'\n'
        return serial,events,oom,count,sha

    def test_actual_lifecycle_oracle_mutations(self):
        import run_qemu_x86_64_pool_pio as r
        for case in range(16):
            serial,events,oom,count,sha=self.sample(case)
            def trace(rows):return '\n'.join('POOL_PIO '+json.dumps(e) for e in rows)+'\n'
            self.assertEqual(len(r.validate(serial,trace(events),case,oom,count,sha)),2*r.dimensions(case)[2])
            for index,event in enumerate(events):
                for rows in (events[:index]+events[index+1:],events[:index]+[event]+events[index:]):
                    with self.subTest(case=case,row=index):
                        with self.assertRaises(ValueError):r.validate(serial,trace(rows),case,oom,count,sha)
            for kind,key,value in (('start','image',13),('start','parent',0),('start','live',9),('copy','sha','0'*64),
                ('create','owner',0),('source','poison',0),('witness','immutable',0),('witness','heap',4096),('witness','sha','0'*64),
                ('mode','before',1),('mode','physical',0),('peer','sleeps',24),('bind','owner',1),('ready','capacity',0),
                ('ready','limit',2),('release','fenced',0),('release','after',1000000),('retire','fenced',0),('retire','sha','0'*64),
                ('retire','identify',1),('finish','zero',0),('finish','initial',1),('trace_drained','events',4097),('trace_clean','bytes',0),
                ('request','lba',0),('request','sequence',2),('reply','bad',2),('result','sha','0'*64),('partial','bytes',257),('cancel','reason',1)):
                changed=copy.deepcopy(events);selected=[e for e in changed if e['kind']==kind and (kind!='start' or e['slot']>=2)]
                if not selected:continue
                selected[0][key]=value
                with self.subTest(case=case,kind=kind,key=key):
                    with self.assertRaises(ValueError):r.validate(serial,trace(changed),case,oom,count,sha)
            for bad in (serial+serial,serial.replace(r.wide.process.DONE,'MISSING',1),serial.replace(r.wide.process.SUCCESS,'MISSING')):
                with self.assertRaises(ValueError):r.validate(bad,trace(events),case,oom,count,sha)
            first=r.wide.process.REAP.search(serial)
            for offset in (0,4,8,12,16,24):
                raw=bytearray.fromhex(first[1]);raw[offset+3]^=128
                with self.assertRaises(ValueError):r.validate(serial.replace(first[1],raw.hex().upper(),1),trace(events),case,oom,count,sha)

    def test_trace_eight_slot_decoder_and_physical_bytes(self):
        import run_qemu_x86_64_pool_pio as r
        import test_x86_64_pio_trace as old
        for slot in range(2,8):
            for caller in range(8):
                owner=3<<32|slot;raw=bytearray(12304);struct.pack_into('<Q',raw,0,1)
                struct.pack_into('<2Q8Q5Q',raw,16,1,1,owner,owner^0xffffffffffffffff,0,1,2,3,1,0,0x3f6,6,caller,1,1<<32)
                self.assertEqual(r.trace_decode(bytes(raw),0)[0][3][2],caller)
                for offset,value in ((0,4097),(8,1),(16,3),(24,2),(40,0),(72,65),(112,8),(128,1),(136,1)):
                    bad=bytearray(raw);struct.pack_into('<Q',bad,offset,value)
                    with self.assertRaises(ValueError):r.trace_decode(bytes(bad),0)
                for wrong in (0,1,8,0xffffffff,0x8000000000000007):
                    bad=bytearray(raw);bad_owner=wrong if wrong>0xffffffff else (3<<32)|wrong
                    struct.pack_into('<2Q',bad,32,bad_owner,bad_owner^0xffffffffffffffff)
                    with self.assertRaises(ValueError):r.trace_decode(bytes(bad),0)
        # The entire existing exhaustive data/ring/gap/snapshot behavior oracle
        # runs with the new decoder, without changing any of its assertions.
        adapter=types.SimpleNamespace(EXTRA=old.profile.EXTRA,trace_decode=r.trace_decode,trace_snapshot=r.trace_snapshot)
        with patch.object(old,'profile',adapter):old.PioTraceTests().test_exact_data_oracle_and_ring_sequence()
        for slot in range(2,8):
            owner=(3<<32)|slot;state=(owner,owner^0xffffffffffffffff,0,1,2,3,1,0)
            ns=self.functions(r.EXTRA,'out','data',DRIVER_SLOT=slot,starts={3:dict(parent=1)},devices={},pio_owner=0,port_events=0,emit=lambda *a,**k:None)
            ns['out']((1,1,state,(0x3f6,6,0,1,1<<32),b'',0))
            ns['out']((1,2,state,(0x3f6,2,slot,3,1<<32),b'',0))
            item=ns['devices'][owner];item['command']=0x20;item['lba']=1;item['lbas']=[1]
            q=(2,64,4,0,owner,0x1f0,0,16,0,0x408000,100,0);data=bytes(n^17^0xa5 for n in range(32))
            event=(2,3,state,q,data,16);ns['data'](event);self.assertEqual(item['data'],data)
            for n in range(32):
                bad=bytearray(data);bad[n]^=1;item['data'].clear()
                with self.assertRaises(AssertionError):ns['data']((2,3,state,q,bytes(bad),16))
            for name,value in (('released',False),('retired',True),('command',0x30)):
                original=item[name];item[name]=value
                with self.assertRaises(AssertionError):ns['data'](event)
                item[name]=original
            # A receipt without full retirement cannot authorize replacement.
            next_owner=4<<32|slot;ns['starts'][4]=dict(parent=1)
            with self.assertRaises(AssertionError):ns['out']((1,4,(next_owner,next_owner^0xffffffffffffffff,*state[2:]),(0x3f6,6,0,1,1<<32),b'',0))
        r.trace_clean(bytes(12304))
        for n in range(12304):
            bad=bytearray(12304);bad[n]=1
            with self.assertRaises(ValueError):r.trace_clean(bad)

    def test_fatal_exact_mutations_snapshots_and_order(self):
        import run_qemu_x86_64_pool_pio as r
        folder=ROOT/'build/codex-agent/r83ao-pool-pio'/('host-fatal-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        for kind in r.FATAL_CASES:
            out=folder/kind;out.mkdir();owner=3<<32|2
            before=[struct.pack('<8Q',owner,owner^0xffffffffffffffff,int(kind=='retirement-slot7'),1,2,3,1,0),bytes(8192),bytes(512),bytes(256),bytes(128),bytes(192)]
            changed,writes=r.fatal_mutation(kind,before)
            self.assertEqual(sum(len(w[2]) for w in writes),16 if kind=='owner-slot8' else 8)
            bad=list(before);bad[0]=bytes(64)
            with self.assertRaises(ValueError):r.fatal_mutation(kind,bad)
            for index in range(6):
                bad=list(before);bad[index]=bad[index][:-1]
                with self.assertRaises(ValueError):r.fatal_mutation(kind,bad)
            if kind=='retirement-slot7':
                for slot in range(8):
                    bad=list(before);bad[1]=bytearray(bad[1]);struct.pack_into('<Q',bad[1],1024*slot,1)
                    with self.assertRaises(ValueError):r.fatal_mutation(kind,bad)
            original=b''.join(before);damaged=b''.join(changed);sha=hashlib.sha256(damaged).hexdigest()
            (out/'before.bin').write_bytes(original)
            for name in ('damaged','fenced','diagnostic','halt'):(out/(name+'.bin')).write_bytes(damaged)
            events=[dict(kind='release')];serial=''
            if kind=='retirement-slot7':
                for slot,gen,status in ((2,3,80),(2,4,80),(0,1,78),(1,2,77)):
                    serial+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,4,1,0x410078).hex().upper()+'\n'
                    events.append(dict(kind='reap_before',slot=slot,gen=gen))
            events+=[dict(kind='inject',case=kind,original=hashlib.sha256(original).hexdigest(),sha=sha,writes=16 if kind=='owner-slot8' else 8),
                dict(kind='fence',physical=1,sha=sha),dict(kind='diagnostic',sha=sha,interrupts=0),dict(kind='halt',sha=sha,cli_hlt=1)]
            serial+='REIST_X86_64_EXCEPTION_FATAL pio=1\n'
            def trace(rows):return '\n'.join('POOL_PIO_FATAL '+json.dumps(e) for e in rows)+'\n'
            r.validate_fatal(serial,trace(events),kind,out)
            for n,e in enumerate(events):
                for changed_ in (events[:n]+events[n+1:],events[:n]+[e]+events[n:],list(reversed(events))):
                    with self.assertRaises(ValueError):r.validate_fatal(serial,trace(changed_),kind,out)
            for name in ('damaged','fenced','diagnostic','halt'):
                file=out/(name+'.bin');bad=bytearray(damaged);bad[-1]^=1;file.write_bytes(bad)
                with self.assertRaises(ValueError):r.validate_fatal(serial,trace(events),kind,out)
                file.write_bytes(damaged)
            for extra in ('REIST_X86_64_PROCESS_REAP_OK v1=BAD',r.wide.process.SUCCESS,r.wide.process.DONE):
                with self.assertRaises(ValueError):r.validate_fatal(serial+extra,trace(events),kind,out)

    def test_actual_fatal_observer_fence_before_diagnosis(self):
        import run_qemu_x86_64_pool_pio as r
        # Execute the actual generated Probe callbacks. Only GDB registers,
        # memory and files are hardware fakes; no replacement failure policy.
        for kind in r.FATAL_CASES:
            for bad_step in (None,'early_diagnostic','wrong_port','changed_after_fence','cleanup'):
                names=('native_pio_state','scheduler_tasks','family_records','family_profiles','family_extended_masks','process_ipc_completions')
                sizes=(64,8192,512,256,128,192);s={name:(i+1)*0x10000 for i,name in enumerate(names)}
                s.update(native_pio_out8=0x99000,halt64=0x88000,scheduler_mode=0x77000)
                s['native_pio_out8.done']=s['native_pio_out8']+1
                owner=3<<32|2;state=struct.pack('<8Q',owner,owner^0xffffffffffffffff,0,1,2,3,1,0)
                regions={s[n]:bytearray(state if i==0 else bytes(size)) for i,(n,size) in enumerate(zip(names,sizes))}
                regions[s['native_pio_out8']]=bytearray(b'\xee');regions[s['halt64']]=bytearray(b'\xfa\xf4\xeb\xfd');regions[s['scheduler_mode']]=bytearray(b'\x08')
                registers=dict(edx=0x3f6,eax=2,eflags=0,rdi=4,rsi=0,rdx=0);writes=[];events=[];commands=[];snapshots={}
                def mem(a,n):
                    for base,data in regions.items():
                        if base<=a and a+n<=base+len(data):return bytes(data[a-base:a-base+n])
                    raise AssertionError('unbounded hardware read')
                def write(a,data):
                    writes.append((a,bytes(data)))
                    for base,raw in regions.items():
                        if base<=a and a+len(data)<=base+len(raw):raw[a-base:a-base+len(data)]=data;return
                    raise AssertionError('unbounded hardware write')
                def snapshot(name,values):snapshots[name]=b''.join(values);return hashlib.sha256(snapshots[name]).hexdigest()
                gdb=types.SimpleNamespace(Breakpoint=object,execute=commands.append)
                env=self.functions(r.FATAL_BODY,'Probe','state',S=s,KIND=kind,RANGES=list(zip((s[n] for n in names),sizes)),
                    released=False,injected=False,fenced=False,diagnosed=False,saved=None,ports=0,retired=[],
                    mem=mem,q=lambda a:struct.unpack('<Q',mem(a,8))[0],reg=lambda n:registers[n],
                    inferior=types.SimpleNamespace(write_memory=write),fatal_mutation=r.fatal_mutation,snapshot=snapshot,
                    event=lambda *a,**k:events.append((a,k)),gdb=gdb,port_hook=types.SimpleNamespace(enabled=True),
                    trigger=types.SimpleNamespace(enabled=False),forbidden=[types.SimpleNamespace(enabled=False) for _ in range(4)])
                probes={'port':env['port_hook'],'trigger':env['trigger']}
                def observe(label):
                    probe=probes.setdefault(label,types.SimpleNamespace(enabled=True));probe.label=label
                    env['Probe'].observe(probe)
                observe('port');self.assertTrue(env['released']);self.assertFalse(env['port_hook'].enabled)
                if kind=='retirement-slot7':
                    for slot,gen in ((2,3),(2,4),(0,1),(1,2)):
                        registers.update(rsi=slot,rdx=gen);struct.pack_into('<Q',regions[s['scheduler_tasks']],slot*1024+8,gen);observe('reap')
                    struct.pack_into('<Q',regions[s['native_pio_state']],16,1)
                observe('trigger');self.assertEqual(sum(len(b) for _,b in writes),16 if kind=='owner-slot8' else 8)
                registers.update(edx=0x3f6,eax=6)
                if bad_step=='early_diagnostic':
                    with self.assertRaises(AssertionError):observe('diagnostic')
                    continue
                if bad_step=='wrong_port':
                    registers['eax']=2
                    with self.assertRaises(AssertionError):observe('port')
                    continue
                if bad_step=='cleanup':
                    with self.assertRaises(AssertionError):observe('forbidden')
                    continue
                observe('port')
                if bad_step=='changed_after_fence':
                    regions[s['family_profiles']][-1]^=1
                    with self.assertRaises(AssertionError):observe('diagnostic')
                    continue
                observe('diagnostic');observe('halt')
                self.assertEqual(commands,['detach','quit 0']);self.assertTrue(all(h.enabled for h in env['forbidden']))
                self.assertEqual(snapshots['damaged'],snapshots['fenced']);self.assertEqual(snapshots['fenced'],snapshots['halt'])

    def test_frozen_gate_result_admission(self):
        import verify_x86_64_pool_pio as v
        frozen=dict(candidate='a'*64,commands=['command'+str(n) for n in range(20)])
        for index in range(1,21):
            receipt=dict(candidate=frozen['candidate'],command=frozen['commands'][index-1],passed=True,exit_code=0,
                elapsed=v.gate_limit(index),log=dict(path='build/test.log',sha256='b'*64),artifacts={'build/test.elf':'c'*64})
            with patch.object(v,'verify_files') as verify:
                v.gate_binding(frozen,index,receipt);self.assertTrue(verify.called)
                for key,value in (('candidate','wrong'),('command','wrong'),('passed',False),('passed',1),('exit_code',1),('elapsed',-1),('elapsed',v.gate_limit(index)+1)):
                    with self.assertRaises(ValueError):v.gate_binding(frozen,index,{**receipt,key:value})
                if index in (13,14,15,17,18):
                    with self.assertRaises(ValueError):v.gate_binding(frozen,index,{**receipt,'artifacts':{}})
        for bad in (0,21,True,1.0):
            with self.assertRaises(ValueError):v.gate_limit(bad)


USER_VECTORS=r'''
int main(void){
 CHECK(!profile_vectors_main());
 for(unsigned slot=2;slot<8;slot++)for(unsigned boundary=0;boundary<3;boundary++){
  const uint64_t gens[]={1,7,0x7fffffff};uint64_t owner=(gens[boundary]<<32)|slot;
  Ata a={0};reist_pio_ops ops={&a,ata_port,ata_clock,ata_sleep};
  reist_native_profile_service s={0};reist_block_profile_v1 profile={1,24,1,0,3000};
  CHECK(!reist_native_service_init_profile(&s,owner,&ops,&profile));
  CHECK(s.service.owner==owner && s.service.server.owner==owner && s.service.server.ready);
  unsigned calls=a.calls;reist_native_profile_service before=s;
  for(unsigned other=2;other<8;other++){
   CHECK(reist_native_service_init_profile(&s,(gens[boundary]<<32)|other,&ops,&profile)==-22);
   CHECK(a.calls==calls && !memcmp(&s,&before,sizeof s));
  }
  x86os_ipc_message_t q={1,140,64,{0}};x86os_ipc_bulk_message_t reply;
  reist_block_header h={1,64,1,0,owner,1,1,a.now+1000,512,0,0};memcpy(q.payload,&h,64);
  CHECK(!reist_native_service_dispatch_profile(&s,&q,&reply));
  for(unsigned n=0;n<512;n++)CHECK(reply.payload[64+n]==(unsigned char)(n^17^0xa5));
  calls=a.calls;CHECK(reist_native_service_dispatch_profile(&s,&q,&reply)==-11 && a.calls==calls);
  for(unsigned failure=1;failure<=calls;failure++){
   a=(Ata){.fail=failure};s=(reist_native_profile_service){0};
   int result=reist_native_service_init_profile(&s,owner,&ops,&profile);
   if(result){CHECK(!s.service.server.ready);unsigned count=a.calls;
    CHECK(reist_native_service_init_profile(&s,owner,&ops,&profile)==-22 && a.calls==count);}
  }
 }
 const uint32_t slots[]={0,1,8,9,0x7fffffff,UINT32_MAX};
 for(unsigned i=0;i<sizeof slots/sizeof *slots;i++){
  Ata a={0};reist_pio_ops ops={&a,ata_port,ata_clock,ata_sleep};
  reist_native_profile_service s={0},before=s;reist_block_profile_v1 profile={1,24,1,0,3000};
  CHECK(reist_native_service_init_profile(&s,(3ULL<<32)|slots[i],&ops,&profile)==-22);
  CHECK(!a.calls && !memcmp(&s,&before,sizeof s));
 }
 for(unsigned slot=2;slot<8;slot++)for(unsigned i=0;i<3;i++){
  const uint64_t generations[]={0,0x80000000,UINT32_MAX};
  Ata a={0};reist_pio_ops ops={&a,ata_port,ata_clock,ata_sleep};
  reist_native_profile_service s={0};reist_block_profile_v1 profile={1,24,1,0,3000};
  CHECK(reist_native_service_init_profile(&s,(generations[i]<<32)|slot,&ops,&profile)==-22 && !a.calls);
 }
 puts("POOL_PIO_USER_OK");return 0;
}
'''


if __name__=='__main__':unittest.main()
