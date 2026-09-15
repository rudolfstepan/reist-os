"""Actual multipage C linking, strict ELF publication, and guest layout oracle."""
from pathlib import Path
import os, shutil, struct, subprocess, sys, unittest, uuid
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs
import build_x86_64_c_payload as p
import run_qemu_x86_64_c_payload as guest


class CPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83v-c-payload'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        cls.folder=folder;cls.zig=find_zig();cls.nasm=shutil.which('nasm') or 'C:/tools/nasm-3.02/nasm.exe'
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        cls.env=env
        cls.flags=['-target','x86_64-freestanding-none','-O2','-ffreestanding','-fno-builtin',
                   '-mno-red-zone','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                   '-fno-pic','-mcmodel=kernel','-mno-sse','-mno-sse2']
        cls.link=[cls.zig,'ld.lld','-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined']
        def run(args,name):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=60,capture_output=True,text=True,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');return r
        cls.run_command=staticmethod(run)
        for source,name in (('arch/x86_64/kernel/bootstrap_core.c','core'),('test/x86_64_c_payload_fixture.c','large')):
            r=run([cls.zig,'cc',*cls.flags,'-DX86_64_C_PAYLOAD_PROBE=1','-c',source,'-o',folder/(name+'.o')],name)
            if r.returncode:raise RuntimeError(r.stderr[-2000:])
        r=run([*cls.link,'-T','config/x86_64_c_payload.ld','-o',folder/'core.elf',folder/'core.o',folder/'large.o'],'new-link')
        if r.returncode:raise RuntimeError(r.stderr[-2000:])
        cls.inner=p.read_bounded(folder/'core.elf');cls.parsed=p.validate(cls.inner)
        p.publish(cls.inner,folder)
        # Actual small ELF32 adapter, not a second reference-system build.
        asm='BITS 32\nsection .multiboot alloc noexec nowrite\ndd 0x1badb002,0,-0x1badb002\n'
        asm+='section .text alloc exec nowrite\nglobal x86_64_bootstrap_start\nx86_64_bootstrap_start: hlt\n'
        asm+='section .rodata alloc noexec nowrite\ndb 1\nsection .data alloc noexec write\ndd 1\nsection .bss nobits alloc noexec write\nresb 8\n'
        asm+='section .c_core_bridge alloc exec nowrite align=256\n'
        for name in ('x86_64_c_serial_write64','x86_64_c_process_shell64','x86_64_c_process_run64'):
            asm+=f'align 256\nglobal {name}\n{name}: ret\n'
        for name,flags,binding in (('text','exec nowrite','x86_64_c_core_entry'),('rodata','noexec nowrite',None),('data','noexec write','x86_64_c_data_state')):
            asm+=f'section .c_core_{name} progbits alloc {flags} align=16\n'
            if binding:asm+=f'global {binding}\n{binding}:\n'
            asm+=f'incbin "{(folder/("bootstrap_core_"+name+".bin")).as_posix()}"\n'
        asm+=f'section .c_core_bss nobits alloc noexec write align=16\nglobal x86_64_c_bss_state\nx86_64_c_bss_state: resb {cls.parsed["sections"][".bss"]["size"]}\n'
        asm+='section .c_core_handoff nobits alloc noexec write align=16\nglobal x86_64_c_handoff,x86_64_c_control_handoff\nx86_64_c_handoff: resb 128\nx86_64_c_control_handoff: resb 64\n'
        (folder/'outer.asm').write_text(asm,encoding='ascii')
        r=run([cls.nasm,'-f','elf32',folder/'outer.asm','-o',folder/'outer.o'],'outer-asm')
        if r.returncode:raise RuntimeError(r.stderr[-2000:])
        r=run([cls.zig,'ld.lld','-m','elf_i386','-T','config/x86_64_bootstrap.ld','-o',folder/'outer.elf',folder/'outer.o'],'outer-link')
        if r.returncode:raise RuntimeError(r.stderr[-2000:])
        cls.outer=p.read_bounded(folder/'outer.elf');p.verify_outer(cls.inner,cls.outer)

    def test_actual_multimodule_sections_and_bindings(self):
        self.assertEqual(p.VERSION,2)
        self.assertEqual(self.parsed['entry'],self.parsed['symbols']['x86_64_c_core_entry']['value'])
        for name in p.LAYOUT:self.assertGreater(self.parsed['sections'][name]['size'],4096)
        for name in ('payload_ro','payload_data','payload_bss','x86_64_c_payload_probe'):self.assertIn(name,self.parsed['symbols'])
        expected=p.outputs(self.inner)
        self.assertEqual(set(expected),set(p.OUTPUTS))
        self.assertEqual(expected,p.outputs(self.inner))
        for name,data in expected.items():self.assertEqual((self.folder/name).read_bytes(),data)

    def test_native_memory_layout3_exact_production_state(self):
        for source,name in (('arch/x86_64/kernel/bootstrap_core.c','ram-core'),
                            ('arch/x86_64/mm/native_memory.c','ram-state'),
                            ('kernel/init/critical_object.c','ram-integrity'),
                            ('lib/libc/string.c','ram-memory-full')):
            r=self.run_command([self.zig,'cc',*self.flags,'-I.','-DX86_64_NATIVE_RAM=1',
                 '-ffunction-sections','-fdata-sections','-c',source,'-o',self.folder/(name+'.o')],name)
            self.assertEqual(r.returncode,0,r.stderr[-2000:])
        r=self.run_command([self.zig,'ld.lld','-m','elf_x86_64','-r','--gc-sections',
            '--undefined=memcpy','--undefined=memset','-o',self.folder/'ram-memory.o',
            self.folder/'ram-memory-full.o'],'ram-memory-select')
        self.assertEqual(r.returncode,0,r.stderr)
        r=self.run_command([*self.link,'-T','config/x86_64_c_payload.ld','-o',self.folder/'ram.elf',
            *[self.folder/(n+'.o') for n in ('ram-core','ram-state','ram-integrity','ram-memory')]],'ram-link')
        self.assertEqual(r.returncode,0,r.stderr)
        raw=p.read_bounded(self.folder/'ram.elf');parsed=p.validate(raw)
        self.assertEqual(parsed['layout_version'],3)
        state=parsed['sections']['.memory_state']
        self.assertEqual(state['size'],4531096)
        self.assertEqual((state['type'],state['flags'],state['address']),(8,3,p.HIGH+0x200000))
        self.assertIn(b'C_CORE_LAYOUT_VERSION 3',p.outputs(raw)['bootstrap_core_layout.inc'])
        sh=struct.unpack_from('<Q',raw,40)[0]+64*state['index']
        mutations=[(sh+4,'I',1),(sh+8,'Q',7),(sh+16,'Q',state['address']+4096),
                   (sh+32,'Q',state['size']-8),(sh+48,'Q',8192)]
        table=parsed['sections']['.symtab'];strings=parsed['sections']['.strtab']['data']
        for pos in range(table['offset'],table['offset']+table['size'],24):
            n=struct.unpack_from('<I',raw,pos)[0]
            name=strings[n:strings.find(b'\0',n)].decode('ascii')
            if name in ('native_memory_state','reist_native_memory'):
                mutations += [(pos+4,'B',0),(pos+5,'B',1),(pos+6,'H',0xfff1),
                              (pos+8,'Q',0),(pos+16,'Q',0)]
        self.assertEqual(len(mutations),15)
        for off,fmt,value in mutations:
            with self.subTest(offset=off):self.reject(self.changed(off,fmt,value,raw))
        # Real ELF32 wrapper for layout3 and exact appended load envelope.
        published=self.folder/'ram-publication';p.publish(raw,published)
        asm=(self.folder/'outer.asm').read_text().replace(
            self.folder.as_posix()+'/bootstrap_core_',published.as_posix()+'/bootstrap_core_')
        asm=asm.replace('x86_64_c_bss_state: resb '+str(self.parsed['sections']['.bss']['size']),
                        'x86_64_c_bss_state: resb '+str(parsed['sections']['.bss']['size']))
        asm+='section .memory_state nobits alloc noexec write align=4096\nresb '+str(p.MEMORY_ARENA_BYTES)+'\n'
        (self.folder/'ram-outer.asm').write_text(asm,encoding='ascii')
        r=self.run_command([self.nasm,'-f','elf32',self.folder/'ram-outer.asm','-o',self.folder/'ram-outer.o'],'ram-outer-asm')
        self.assertEqual(r.returncode,0,r.stderr)
        r=self.run_command([self.zig,'ld.lld','-m','elf_i386','-T','config/x86_64_bootstrap.ld',
            '-o',self.folder/'ram-outer.elf',self.folder/'ram-outer.o'],'ram-outer-link')
        self.assertEqual(r.returncode,0,r.stderr)
        outer=p.read_bounded(self.folder/'ram-outer.elf');p.verify_outer(raw,outer)
        arena=p.elf(outer,32)['sections']['.memory_state']
        header=struct.unpack_from('<I',outer,32)[0]+arena['index']*40
        for off,value in ((4,1),(8,7),(12,0x201000),(20,arena['size']-4096),(32,8192)):
            with self.subTest(outer=off):
                with self.assertRaises(ValueError):p.verify_outer(raw,self.changed(header+off,'I',value,outer))
        ph=struct.unpack_from('<I',outer,28)[0];number=struct.unpack_from('<H',outer,44)[0]
        extended=0
        for i in range(number):
            at=ph+i*32
            address=struct.unpack_from('<I',outer,at+8)[0]
            size=struct.unpack_from('<I',outer,at+20)[0]
            if address+size>0x200000:
                extended+=1
                for off,value in ((20,size+4096),(16,4096),(8,address+4096)):
                    with self.assertRaises(ValueError):
                        p.verify_outer(raw,self.changed(at+off,'I',value,outer))
        self.assertEqual(extended,1)

        # Exact opt-in initialized catalog / NOLOAD scratch, real ELF32 link.
        wide_asm=asm+'section .native_catalog progbits alloc noexec nowrite align=4096\n' \
            +'catalog: times 1065344 db 0x5a\nglobal native_catalog_used\nnative_catalog_used equ $-catalog\nalign 4096, db 0\n' \
            +'section .native_scratch nobits alloc noexec write align=4096\nscratch: resb 266336\n' \
            +'global native_scratch_used\nnative_scratch_used equ $-scratch\nalignb 4096\n'
        def link_wide(text,name):
            (self.folder/(name+'.asm')).write_text(text,encoding='ascii')
            r=self.run_command([self.nasm,'-f','elf32',self.folder/(name+'.asm'),
                                '-o',self.folder/(name+'.o')],name+'-asm')
            self.assertEqual(r.returncode,0,r.stderr)
            return self.run_command([self.zig,'ld.lld','-m','elf_i386','-T','config/x86_64_bootstrap.ld',
                     '-o',self.folder/(name+'.elf'),self.folder/(name+'.o')],name+'-link')
        r=link_wide(wide_asm,'wide');self.assertEqual(r.returncode,0,r.stderr)
        wide=p.read_bounded(self.folder/'wide.elf',bits=32);p.verify_outer(raw,wide)
        o=p.elf(wide,32)
        self.assertGreater(len(wide),1048576)
        self.assertEqual(o['symbols']['_x86_64_bootstrap_end']['value'],0xb47000)
        with self.assertRaises(ValueError):p.read_bounded(self.folder/'wide.elf')
        with self.assertRaises(ValueError):p.elf(wide,64)
        for name,addr,size,flags,typ in (('.native_catalog',0xa00000,1069056,2,1),
                                        ('.native_scratch',0xb05000,270336,3,8)):
            s=o['sections'][name];at=struct.unpack_from('<I',wide,32)[0]+s['index']*40
            self.assertEqual((s['address'],s['size'],s['flags'],s['type']),(addr,size,flags,typ))
            for off,value in ((4,8 if typ==1 else 1),(8,flags^1),(8,flags|4),(12,addr+4096),
                              (16,0),(20,size-4096),(20,size+4096),(32,8192)):
                with self.subTest(wide_section=name,offset=off,value=value):
                    with self.assertRaises(ValueError):p.verify_outer(raw,self.changed(at+off,'I',value,wide))
        padding=o['sections']['.native_catalog']['offset']+1065344
        with self.assertRaises(ValueError):p.verify_outer(raw,self.changed(padding,'B',1,wide))
        ph=struct.unpack_from('<I',wide,28)[0]
        for i in range(struct.unpack_from('<H',wide,44)[0]):
            at=ph+32*i;addr=struct.unpack_from('<I',wide,at+8)[0]
            if addr<0xa00000:continue
            for off,value in ((8,addr+4096),(12,addr+4096),(16,1),(20,0x200000),(24,7)):
                with self.subTest(wide_segment=addr,offset=off):
                    with self.assertRaises(ValueError):p.verify_outer(raw,self.changed(at+off,'I',value,wide))
        table=o['sections']['.symtab'];strings=o['sections']['.strtab']['data'];count=0
        for at in range(table['offset'],table['offset']+table['size'],16):
            n=struct.unpack_from('<I',wide,at)[0];name=strings[n:strings.find(b'\0',n)].decode('ascii')
            if name.startswith('_native_') or name=='_x86_64_bootstrap_end':
                count+=1
                with self.assertRaises(ValueError):p.verify_outer(raw,self.changed(at+4,'I',0x200000,wide))
        self.assertEqual(count,7)
        for i,(before,after) in enumerate((('1065344','1065343'),('1065344','1065345'),
                                          ('266336','266335'),('266336','266337'),
                                          ('resb 266336','resb 0'),('times 1065344 db 0x5a',''))):
            r=link_wide(wide_asm.replace(before,after),'wide-reject-'+str(i))
            self.assertNotEqual(r.returncode,0)
            self.assertIn('native boot area exact pair/capacity',r.stderr)

    def test_actual_old_envelope_failure(self):
        r=self.run_command([*self.link,
               '-e','x86_64_c_payload_probe','--section-start=.text=0xFFFFFFFF80185000',
               '--section-start=.rodata=0xFFFFFFFF80186000','--section-start=.data=0xFFFFFFFF80187000',
               '--section-start=.bss=0xFFFFFFFF80188000','--defsym=x86_64_c_serial_write64=0xFFFFFFFF80184000',
               '-o',self.folder/'old.elf',self.folder/'large.o'],'old-link')
        self.assertNotEqual(r.returncode,0)
        self.assertRegex(r.stderr,r'overlap|overlapping')

    def test_native_heap_layout4_exact_state_and_export(self):
        names=[]
        for source,name in (('arch/x86_64/kernel/bootstrap_core.c','heap-core'),
                            ('arch/x86_64/mm/native_memory.c','heap-memory'),
                            ('arch/x86_64/mm/native_heap.c','heap-state'),
                            ('kernel/init/critical_object.c','heap-integrity')):
            names.append(name)
            r=self.run_command([self.zig,'cc',*self.flags,'-I.','-DX86_64_NATIVE_RAM=1',
                '-DX86_64_NATIVE_PROCESSES=1','-DX86_64_NATIVE_HEAP=1',
                '-c',source,'-o',self.folder/(name+'.o')],name)
            self.assertEqual(r.returncode,0,r.stderr[-2000:])
        # Core is freestanding; retain only the two required memory primitives.
        r=self.run_command([self.zig,'cc',*self.flags,'-I.','-ffunction-sections',
            '-c','lib/libc/string.c','-o',self.folder/'heap-string-full.o'],'heap-string')
        self.assertEqual(r.returncode,0,r.stderr)
        r=self.run_command([self.zig,'ld.lld','-m','elf_x86_64','-r','--gc-sections',
            '--undefined=memcpy','--undefined=memset','-o',self.folder/'heap-string.o',
            self.folder/'heap-string-full.o'],'heap-string-select')
        self.assertEqual(r.returncode,0,r.stderr)
        r=self.run_command([*self.link,'-T','config/x86_64_c_payload.ld','-o',self.folder/'heap.elf',
            *[self.folder/(n+'.o') for n in names+['heap-string']]],'heap-link')
        self.assertEqual(r.returncode,0,r.stderr)
        raw=p.read_bounded(self.folder/'heap.elf');parsed=p.validate(raw)
        self.assertEqual(parsed['layout_version'],4)
        state=parsed['sections']['.heap_state']
        self.assertEqual((state['type'],state['flags'],state['address'],state['size']),
                         (8,3,p.HIGH+0x653000,397704))
        self.assertIn(b'C_CORE_LAYOUT_VERSION 4',p.outputs(raw)['bootstrap_core_layout.inc'])
        sh=struct.unpack_from('<Q',raw,40)[0]+64*state['index']
        mutations=[(sh+4,'I',1),(sh+8,'Q',7),(sh+16,'Q',state['address']+4096),
                   (sh+32,'Q',state['size']-8),(sh+48,'Q',8192)]
        table=parsed['sections']['.symtab'];strings=parsed['sections']['.strtab']['data']
        for pos in range(table['offset'],table['offset']+table['size'],24):
            n=struct.unpack_from('<I',raw,pos)[0]
            if strings[n:strings.find(b'\0',n)].decode('ascii') in ('native_heap_state','reist_native_heap'):
                mutations += [(pos+4,'B',0),(pos+5,'B',1),(pos+6,'H',0xfff1),
                              (pos+8,'Q',0),(pos+16,'Q',0)]
        self.assertEqual(len(mutations),15)
        for off,fmt,value in mutations:
            with self.subTest(offset=off):self.reject(self.changed(off,fmt,value,raw))

    def test_native_task_pool_layout5_exact_inner_outer(self):
        names=[]
        for source,name in (('arch/x86_64/kernel/bootstrap_core.c','pool-core'),
                            ('arch/x86_64/mm/native_memory.c','pool-memory'),
                            ('arch/x86_64/mm/native_heap.c','pool-heap'),
                            ('arch/x86_64/ipc/native_ipc.c','pool-ipc'),
                            ('kernel/ipc/ipc.c','pool-ipc-core'),
                            ('kernel/init/critical_object.c','pool-integrity')):
            names.append(name)
            result=self.run_command([self.zig,'cc',*self.flags,'-I.','-DREIST_NATIVE_TASK_POOL=1',
                '-DX86_64_NATIVE_PROCESSES=1','-DX86_64_NATIVE_RAM=1','-DX86_64_NATIVE_HEAP=1',
                '-DX86_64_NATIVE_IPC=1','-DX86_64_NATIVE_PROGRAMS=1','-DX86_64_NATIVE_LIFECYCLE=1',
                '-DREIST_NATIVE_IPC','-DREIST_NATIVE_RUNTIME','-c',source,'-o',self.folder/(name+'.o')],name)
            self.assertEqual(result.returncode,0,result.stderr[-2000:])
        result=self.run_command([self.zig,'cc',*self.flags,'-I.','-ffunction-sections',
            '-c','lib/libc/string.c','-o',self.folder/'pool-string-full.o'],'pool-string')
        self.assertEqual(result.returncode,0,result.stderr)
        result=self.run_command([self.zig,'ld.lld','-m','elf_x86_64','-r','--gc-sections',
            '--undefined=memcpy','--undefined=memset','-o',self.folder/'pool-string.o',
            self.folder/'pool-string-full.o'],'pool-string-select')
        self.assertEqual(result.returncode,0,result.stderr)
        result=self.run_command([*self.link,'-T','config/x86_64_c_payload.ld','-o',self.folder/'pool.elf',
            *[self.folder/(n+'.o') for n in names+['pool-string']]],'pool-link')
        self.assertEqual(result.returncode,0,result.stderr)
        raw=p.read_bounded(self.folder/'pool.elf');parsed=p.validate(raw)
        self.assertEqual(parsed['layout_version'],5)
        self.assertEqual(parsed['sections']['.heap_state']['size'],232+8*99368)
        self.assertEqual(parsed['sections']['.heap_state']['address'],p.HIGH+0x653000)
        self.assertEqual(p.POOL_HEAP_ARENA_BYTES,(((4531096+4095)&~4095)+795176+4095&~4095)+529*4096)
        marker=parsed['symbols']['native_task_pool_capacity'];ro=parsed['sections']['.rodata']
        at=ro['offset']+marker['value']-ro['address']
        for value in (0,4,7,9,1<<32):self.reject(self.changed(at,'Q',value,raw))
        table=parsed['sections']['.symtab'];strings=parsed['sections']['.strtab']['data']
        for pos in range(table['offset'],table['offset']+table['size'],24):
            offset=struct.unpack_from('<I',raw,pos)[0];name=strings[offset:strings.find(b'\0',offset)].decode('ascii')
            if name in ('native_task_pool_capacity','native_heap_state'):
                for off,fmt,value in ((4,'B',0),(5,'B',1),(6,'H',0xfff1),(8,'Q',0),(16,'Q',0)):
                    self.reject(self.changed(pos+off,fmt,value,raw))
            if name=='native_task_pool_capacity':
                self.reject(self.changed(parsed['sections']['.strtab']['offset']+offset,'B',ord('x'),raw))
        section=parsed['sections']['.heap_state'];sh=struct.unpack_from('<Q',raw,40)[0]+section['index']*64
        for off,fmt,value in ((4,'I',1),(8,'Q',7),(16,'Q',p.HIGH+0x654000),
                              (32,'Q',397704),(32,'Q',795175),(32,'Q',795177),(48,'Q',8192)):
            self.reject(self.changed(sh+off,fmt,value,raw))
        published=self.folder/'pool-publication';p.publish(raw,published)
        asm=(self.folder/'outer.asm').read_text().replace(self.folder.as_posix()+'/bootstrap_core_',published.as_posix()+'/bootstrap_core_')
        asm=asm.replace('x86_64_c_bss_state: resb '+str(self.parsed['sections']['.bss']['size']),
                        'x86_64_c_bss_state: resb '+str(parsed['sections']['.bss']['size']))
        asm+='section .memory_state nobits alloc noexec write align=4096\nresb 7499776\n'
        asm+='section .native_catalog progbits alloc noexec nowrite align=4096\ncatalog: times 1065344 db 0x5a\n'
        asm+='global native_catalog_used\nnative_catalog_used equ $-catalog\nalign 4096, db 0\n'
        asm+='section .native_scratch nobits alloc noexec write align=4096\nscratch: resb 266336\n'
        asm+='global native_scratch_used\nnative_scratch_used equ $-scratch\nalignb 4096\n'
        (self.folder/'pool-outer.asm').write_text(asm,encoding='ascii')
        result=self.run_command([self.nasm,'-f','elf32',self.folder/'pool-outer.asm','-o',self.folder/'pool-outer.o'],'pool-outer-asm')
        self.assertEqual(result.returncode,0,result.stderr)
        result=self.run_command([self.zig,'ld.lld','-m','elf_i386','-T','config/x86_64_bootstrap.ld',
            '-o',self.folder/'pool-outer.elf',self.folder/'pool-outer.o'],'pool-outer-link')
        self.assertEqual(result.returncode,0,result.stderr)
        outer=p.read_bounded(self.folder/'pool-outer.elf',bits=32);p.verify_outer(raw,outer)
        section=p.elf(outer,32)['sections']['.memory_state'];sh=struct.unpack_from('<I',outer,32)[0]+section['index']*40
        for off,value in ((4,1),(8,7),(12,0x201000),(20,7102464),(20,7499776-4096),(20,7499776+4096),(32,8192)):
            with self.assertRaises(ValueError):p.verify_outer(raw,self.changed(sh+off,'I',value,outer))

    def changed(self,offset,fmt,value,data=None):
        result=bytearray(self.inner if data is None else data);struct.pack_into(fmt,result,offset,value);return bytes(result)

    def section(self,name,bits=64):
        blob=self.inner if bits==64 else self.outer
        parsed=self.parsed if bits==64 else p.elf(blob,32)
        offset=struct.unpack_from('<Q' if bits==64 else '<I',blob,40 if bits==64 else 32)[0]
        return offset+parsed['sections'][name]['index']*(64 if bits==64 else 40)

    def symbol(self,name,bits=64):
        blob=self.inner if bits==64 else self.outer;parsed=p.elf(blob,bits)
        table=parsed['sections']['.symtab'];strings=parsed['sections']['.strtab']['data'];stride=24 if bits==64 else 16
        for pos in range(table['offset'],table['offset']+table['size'],stride):
            start=struct.unpack_from('<I',blob,pos)[0]
            if strings[start:strings.find(b'\0',start)].decode('ascii')==name:return pos
        self.fail('symbol not found')

    def reject(self,blob):
        with mock.patch.object(p.os,'replace') as replace:
            with self.assertRaises((ValueError,struct.error)):p.publish(blob,self.folder/'reject-no-output')
            replace.assert_not_called()
        self.assertFalse((self.folder/'reject-no-output').exists())

    def test_header_table_and_truncation_rejected_before_publication(self):
        cases=[(4,'B',1),(5,'B',2),(6,'B',0),(7,'B',255),(8,'B',1),(16,'H',1),(18,'H',3),
               (20,'I',0),(24,'Q',p.HIGH+0x185010),(32,'Q',8),(40,'Q',8),(48,'I',1),
               (52,'H',52),(54,'H',55),(56,'H',33),(58,'H',63),(60,'H',129),(62,'H',0)]
        for off,fmt,value in cases:
            with self.subTest(offset=off):self.reject(self.changed(off,fmt,value))
        for length in (0,63,len(self.inner)-1):
            with self.subTest(length=length):self.reject(self.inner[:length])
        self.reject(bytes(1048577))

    def test_section_capacities_permissions_and_file_aliases(self):
        for name,(addr,cap,flags,typ,_) in p.LAYOUT.items():
            at=self.section(name)
            for off,value in ((8,flags|4|1),(16,addr+4096),(32,cap+1),(48,3)):
                with self.subTest(section=name,offset=off):self.reject(self.changed(at+off,'Q',value))
        for off,fmt,value in ((4,'I',9),(8,'Q',0x402),(24,'Q',0),(32,'Q',0),(48,'Q',8192)):
            with self.subTest(rodata=off):self.reject(self.changed(self.section('.rodata')+off,fmt,value))
        self.reject(self.changed(self.section('.rodata')+24,'Q',self.parsed['sections']['.text']['offset']))

    def test_unknown_allocated_and_forbidden_runtime_sections(self):
        names=self.parsed['sections']['.shstrtab'];at=self.section('.shstrtab')
        for name in ('.got','.init_array','.fini_array','.ctors','.dtors','.eh_frame','.gcc_except_table','.tdata','.tbss','.tls'):
            with self.subTest(name=name):
                table=names['data']+name.encode()+b'\0'
                blob=self.changed(at+24,'Q',len(self.inner))
                blob=self.changed(at+32,'Q',len(table),blob)
                blob=self.changed(self.section('.rodata'),'I',len(names['data']),blob)+table
                self.reject(blob)

    def test_segments_and_symbol_authority(self):
        ph=struct.unpack_from('<Q',self.inner,32)[0]
        for off,value in ((0,2),(4,7),(8,0),(16,p.HIGH+0x195000),(24,0),(32,1),(40,65537),(48,3)):
            with self.subTest(program=off):self.reject(self.changed(ph+off,'I' if off<8 else 'Q',value))
        for name in p.BINDINGS:
            at=self.symbol(name)
            for off,fmt,value in ((4,'B',0),(5,'B',1),(6,'H',0),(6,'H',0xfff2),(8,'Q',p.BINDINGS[name]+1)):
                with self.subTest(symbol=name,offset=off,value=value):self.reject(self.changed(at+off,fmt,value))
        for name in ('x86_64_c_data_state','x86_64_c_bss_state'):
            self.reject(self.changed(self.symbol(name)+16,'Q',31))

    def test_linker_rejects_capacity_and_hosted_state(self):
        cases=[('.text',65536),('.rodata',32768),('.data',16384),('.bss',262144),('.init_array',8),('.fini_array',8)]
        for ordinal,(section,size) in enumerate(cases):
            with self.subTest(section=section):
                source=self.folder/f'excess-{ordinal}.asm';obj=source.with_suffix('.o')
                flags='nobits alloc noexec write' if section=='.bss' else 'progbits alloc '+('exec nowrite' if section=='.text' else 'noexec nowrite' if section=='.rodata' else 'noexec write')
                source.write_text(f'section {section} {flags}\n'+(f'resb {size}\n' if section=='.bss' else f'times {size} db 0\n'),encoding='ascii')
                r=self.run_command([self.nasm,'-f','elf64',source,'-o',obj],f'excess-{ordinal}-asm')
                self.assertEqual(r.returncode,0,r.stderr)
                r=self.run_command([*self.link,'-T','config/x86_64_c_payload.ld','-o',self.folder/f'excess-{ordinal}.elf',self.folder/'core.o',self.folder/'large.o',obj],f'excess-{ordinal}-link')
                self.assertNotEqual(r.returncode,0)
                self.assertRegex(r.stderr,'capacity|forbidden')

    def test_publication_failure_preserves_prior_files_and_foreign_staging(self):
        before={n:(self.folder/n).read_bytes() for n in p.OUTPUTS}
        with mock.patch.object(p.os,'replace',side_effect=OSError('injected replace failure')):
            with self.assertRaises(OSError):p.publish(self.inner,self.folder)
        self.assertEqual(before,{n:(self.folder/n).read_bytes() for n in p.OUTPUTS})
        self.assertFalse(list(self.folder.glob('.c-payload-*')))
        collision=self.folder/'.c-payload-collision';collision.write_bytes(b'foreign')
        with mock.patch.object(p.uuid,'uuid4',return_value=mock.Mock(hex='collision')):
            with self.assertRaises(FileExistsError):p.publish(self.inner,self.folder)
        self.assertEqual(collision.read_bytes(),b'foreign')
        self.assertEqual(before,{n:(self.folder/n).read_bytes() for n in p.OUTPUTS})
        with self.assertRaises(ValueError):p.publish(self.inner,ROOT/'not-a-build-directory')
        self.assertFalse((ROOT/'not-a-build-directory').exists())

    def test_outer_bytes_symbols_load_permissions_and_handoff(self):
        o=p.elf(self.outer,32);cases=[]
        for name in ('.c_core_text','.c_core_rodata','.c_core_data'):
            off=o['sections'][name]['offset'];cases.append(self.changed(off,'B',self.outer[off]^0xff,self.outer))
        cases.append(self.changed(self.symbol('x86_64_c_core_entry',32)+14,'H',0xfff1,self.outer))
        cases.append(self.changed(self.symbol('x86_64_c_control_handoff',32)+4,'I',0x1880a0,self.outer))
        cases.append(self.changed(self.section('.c_core_handoff',32)+20,'I',193,self.outer))
        ph=struct.unpack_from('<I',self.outer,28)[0]
        for off,value in ((12,0),(24,7),(20,0xffffffff)):
            cases.append(self.changed(ph+off,'I',value,self.outer))
        for i,blob in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ValueError):p.verify_outer(self.inner,blob)

    def test_guest_oracle_rejects_missing_duplicate_and_reordered_witnesses(self):
        c,_,leaves=guest.layout(self.inner,self.outer)
        serial='\n'.join(guest.REQUIRED_MARKERS).replace('REIST_X86_64_C_CALLBACK_OK',guest.MARKER+'\nREIST_X86_64_C_CALLBACK_OK')
        serial=serial.replace('REIST_X86_64_RING3_SHELL_RUN_OK','REIST_X86_64_RING3_SHELL_RUN_OK\nREIST_X86_64_RING3_SHELL_RUN_OK')
        bss=c['sections']['.bss']['size'];data=c['sections']['.data']['size']
        proofs=[f'C_PAYLOAD_LAYOUT phase={i} pages={len(leaves)} gaps={124-len(leaves)} wp=1 nxe=1 direct=0' for i in (1,2)]
        lines=['C_PAYLOAD_POISON count=4',f'C_PAYLOAD_ZERO bss={bss} handoff=192',proofs[0],f'C_PAYLOAD_CLEAN data={data} bss={bss} handoff=192',proofs[1]]
        trace='\n'.join(lines);guest.validate(serial,trace,c,leaves)
        for i in range(5):
            for bad in ('\n'.join(lines[:i]+lines[i+1:]),trace+'\n'+lines[i],'\n'.join(reversed(lines))):
                with self.assertRaises(ValueError):guest.validate(serial,bad,c,leaves)
        for before,after in (('wp=1','wp=0'),('nxe=1','nxe=0'),('direct=0','direct=1'),('count=4','count=3'),('pages=13','pages=12'),('handoff=192','handoff=128')):
            with self.subTest(before=before):
                with self.assertRaises(ValueError):guest.validate(serial,trace.replace(before,after),c,leaves)
        for bad in (serial.replace(guest.MARKER,''),serial+'\n'+guest.MARKER,serial+'\n'+guest.FAILURES[0],serial.replace(guest.SUCCESS,'')):
            with self.assertRaises(ValueError):guest.validate(bad,trace,c,leaves)

    def test_debugger_start_failure_terminates_only_owned_vm(self):
        folder=self.folder/'spawn-failure';folder.mkdir()
        vm=mock.Mock()
        with mock.patch.object(guest,'resolve_qemu',return_value=Path('qemu')),mock.patch.object(guest,'terminate_bounded') as stop, \
             mock.patch.object(guest.subprocess,'Popen',side_effect=[vm,OSError('debugger unavailable')]):
            with self.assertRaises(OSError):guest.capture(self.folder/'outer.elf',folder,'quit\n')
        stop.assert_called_once_with(vm);vm.stdin.close.assert_called_once();vm.stdout.close.assert_called_once()


if __name__=='__main__':unittest.main()
