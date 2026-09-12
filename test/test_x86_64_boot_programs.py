"""Prepared executable authority: producer, actual admission and guest oracle."""
from pathlib import Path
import re, struct, sys, unittest, tempfile, subprocess
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
import test_x86_64_task_frames as host

def elf():
    b=bytearray(8194)
    b[:16]=b'\x7fELF\x02\x01\x01'+bytes(9)
    struct.pack_into('<HHIQQQIHHHHHH',b,16,2,62,1,0x400000,64,0,0,64,56,2,0,0,0)
    struct.pack_into('<II6Q',b,64,1,5,4096,0x400000,0,2,2,4096)
    struct.pack_into('<II6Q',b,120,1,6,8192,0x404000,0,2,8192,4096)
    b[4096:4098]=b'\x90\xc3';b[8192:]=b'RW'
    return bytes(b)

class BootProgramTests(unittest.TestCase):
    @staticmethod
    def sample(case=0):
        import run_qemu_x86_64_boot_programs as r
        common=[m for m in r.REQUIRED_MARKERS if 'SHELL' not in m]
        cut=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
        serial='\n'.join(common[:cut])+'\n';native=[]
        for run in range(2):
            for slot in range(4):
                ident=slot if run==0 else 3-slot;bad=case and ident==2
                status=(134 if case==1 else 256) if bad else 40+ident
                row=(slot,run*4+slot+1,status,3 if bad else 4,32 if bad and case==2 else 0,0x400100)
                native.append(row);serial+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',*row).hex().upper()+'\n'
            serial+=r.process.DONE+'\n'
        serial+='\n'.join(common[cut:])+'\n'+r.process.SUCCESS+'\n'
        records=[(m,s,s+1,4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)]
        records += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]
        records += [(5,s,20+s,4) for s in range(4)]+[(6,1,31,8),(6,1,32,8),(6,0,30,4)]
        records += [(8,x[0],x[1],x[3]) for x in native]
        trace='PREEMPT_PENDING_IRQ pending=1 unmasked=1\n'
        trace+=''.join(f'PREEMPT_IF_ADMISSION slot={s} if={s} armed={s}\n' for s in (0,1,0))
        trace+='NATIVE_MEMORY_MAP_OK ram=4096 managed=1041000 huge=2040 mixed=2 high=1\n'
        for seq,(mode,slot,gen,state) in enumerate(records,1):
            if seq in (18,22):
                run=1 if seq==18 else 2
                for s in range(4):
                    ident=s if run==1 else 3-s
                    trace+=f'BOOT_PROGRAM_START run={run} slot={s} gen={(run-1)*4+s+1} image={ident+3} layout={ident+2} argc=2 private=1\n'
            base=0x100000000+seq*0x10000
            frames=[0,base+4096,0,0,0,0,0,0]+[base+4096*n for n in (2,3,4,5,6)]
            if mode==8:
                trace+=f'NATIVE_IPC_FENCE slot={slot} gen={gen}\nPROCESS_FENCE_OK seq={seq} slot={slot} gen={gen}\n'
            trace+=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root={frames[-1]:x} active=13d000 before=1000 fp=1 frames='+','.join(f'{f:x}' for f in frames)+'\n'
            trace+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in frames if f)
            trace+=f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=1006 zero=1\n'
            if seq in (21,25):
                run=1 if seq==21 else 2;tick=run*70
                trace+=f'PROCESS_ZERO_OK run={run} zero=1 free=10000 initial=10000 reaps=4 generation={run*4} ticks={tick}\n'
                trace+=f'BOOT_PROGRAM_ZERO run={run} images=1 heap=1 tick={tick}\n'
        return serial,trace

    def test_guest_oracles(self):
        import run_qemu_x86_64_boot_programs as r
        for case in range(3):
            serial,trace=self.sample(case);self.assertEqual(len(r.validate(serial,trace,case,4096)),8)
            for old,new in [('argc=2','argc=3'),('image=3','image=9'),('images=1','images=0'),
                ('heap=1','heap=0'),('if=0','if=1'),('pending=1','pending=2'),('ticks=70','ticks=71'),
                ('initial=10000','initial=10001'),('zero=1','zero=0'),('gen=8','gen=7'),
                ('TASK_FRAMES_FREE','MISSING'),('NATIVE_IPC_FENCE','MISSING')]:
                with self.subTest(case=case,old=old),self.assertRaises((ValueError,RuntimeError)):
                    r.validate(serial,trace.replace(old,new,1),case,4096)
            for old,new in [('PROCESS_REAP_OK','MISSING'),('C_KERNEL_CONTROL_OK','C_KERNEL_CONTROL_ERROR'),
                            ('NATIVE_PROCESSES_OK','MISSING')]:
                with self.assertRaises((ValueError,RuntimeError)):r.validate(serial.replace(old,new,1),trace,case,4096)
            with self.assertRaises((ValueError,RuntimeError)):r.validate(serial,trace+trace,case,4096)
        prefix='PREEMPT_PENDING_IRQ pending=1 unmasked=1\n'+''.join(f'PREEMPT_IF_ADMISSION slot={s} if={s} armed={s}\n' for s in (0,1,0))
        for kind in ('header','rights','arguments',0,1,2):
            trace=prefix+f'BOOT_PROGRAM_REJECT kind={kind} before=100 after=100 zero=1\n'
            if isinstance(kind,int):trace+=f'BOOT_PROGRAM_ALLOC_INJECT acquired={kind}\n'
            serial='REIST_X86_64_C_KERNEL_CONTROL_ERROR'
            r.validate_rejection(serial,trace,kind)
            for bad in (trace+trace,trace.replace('after=100','after=99'),trace.replace('zero=1','zero=0')):
                with self.assertRaises(ValueError):r.validate_rejection(serial,bad,kind)
            with self.assertRaises(ValueError):r.validate_rejection(serial+r.process.SUCCESS,trace,kind)

    def test_capture_failure_cleanup(self):
        import run_qemu_x86_64_boot_programs as r
        vm=Mock()
        with tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent') as folder:
            with patch.object(r,'resolve_qemu',return_value=Path('qemu')), \
                 patch.object(r.subprocess,'Popen',side_effect=[vm,OSError('debugger missing')]), \
                 patch.object(r,'terminate_bounded') as stop:
                with self.assertRaises(OSError):r.capture(Path('fixture.elf'),Path(folder),'continue\n',4096)
                stop.assert_called_once_with(vm);vm.stdin.close.assert_called_once();vm.stdout.close.assert_called_once()

    def test_publication_failure_preserves_catalog(self):
        import build_x86_64_boot_programs as p
        with tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent') as folder:
            folder=Path(folder);old=folder/'boot-programs.bin';old.write_bytes(b'old accepted catalog')
            def command(args,**_):
                output=Path(args[args.index('-o')+1])
                if output.suffix=='.prg':output.write_bytes(b'bad' if output.name=='program2.prg' else elf())
                return subprocess.CompletedProcess(args,0,b'',b'')
            with patch.object(p.subprocess,'run',side_effect=command):
                with self.assertRaises(ValueError):p.build(folder,['cc'],['nasm'],['ld'],0)
            self.assertEqual(old.read_bytes(),b'old accepted catalog')
            self.assertEqual(len(list(folder.glob('programs-*'))),1)

    def test_actual_preemption_if(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        names=('TASK_RFLAGS','TASK_RDI','TASK_ID','TASK_A_PREEMPT_ID','TASK_B_PREEMPT_ID',
               'RFLAGS_PREEMPT_FORBIDDEN','SCHEDULER_MODE_PREEMPTION')
        constants='\n'.join(re.search(r'^'+n+r'\s+equ\s+[^\n]+',source,re.M)[0] for n in names)
        build=source.split('.preempt_ids:',1)[1].split('.quantum_ids:',1)[0]
        flags=source.split('.preempt_syscall_flags:',1)[1].split('.syscall_flags_valid:',1)[0]
        asm='BITS 64\n'+constants+'''
section .bss
scheduler_mode: resb 1
scheduler_current_slot: resd 1
section .text
global build_start
build_start:
    push rbx
    push r12
    mov ebx,edi
    mov r12,rsi
.preempt_ids:
'''+build+'''
.done:
    pop r12
    pop rbx
    ret
global check_flags
check_flags:
    mov rax,rdi
    mov [rel scheduler_mode],sil
    mov [rel scheduler_current_slot],edx
.preempt_syscall_flags:
'''+flags+'''
.syscall_flags_valid:
    mov eax,1
    ret
scheduler_fail:
    xor eax,eax
    ret
'''
        c='''#include <stdint.h>
#include <stdio.h>
extern void __attribute__((sysv_abi)) build_start(unsigned,uint64_t*);
extern unsigned __attribute__((sysv_abi)) check_flags(uint64_t,unsigned,unsigned);
int main(void) {
    for(unsigned slot=0;slot<2;slot++) {
        uint64_t task[32]={0};task[14]=2;build_start(slot,task);
        if(task[14]!=(slot?514:2))return 1;
        for(unsigned mode=2;mode<=7;mode++)for(unsigned flags=0;flags<4096;flags++) {
            unsigned expected_if=(mode==2 && slot==0)?0:512;
            unsigned valid=!(flags&0xd00) && (flags&512)==expected_if;
            if(check_flags(flags,mode,slot)!=valid)return 2;
        }
    }
    puts("PREEMPT_IF_HOST_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'PREEMPT_IF_HOST')

    def test_producer(self):
        import build_x86_64_boot_programs as p
        raw=elf();r=p.prepare(raw,['program.prg','hello'])
        self.assertEqual(len(r),36896)
        self.assertEqual(struct.unpack_from('<Q',r,16)[0],0x400000)
        self.assertEqual(r[24:32],bytes([5,0,0,0,6,6,0,0]))
        self.assertEqual(r[32+0x4000:32+0x4002],b'RW')
        self.assertEqual(r[32+0x4002:32+0x6000],bytes(8190))
        for off,fmt,values in [(4,'B',[1,3]),(5,'B',[0,2]),(7,'B',[3]),(16,'H',[1,3]),
            (18,'H',[3,0]),(24,'Q',[0x400002,0x404000,2**64-1]),(32,'Q',[0,2**64-1]),
            (52,'H',[0,63]),(54,'H',[0,55]),(56,'H',[0,9]),(64,'I',[2,3,7]),
            (68,'I',[0,1,2,3,7,0x105]),(72,'Q',[4097,2**64-1]),
            (80,'Q',[0x3ff000,0x408000,2**64-1]),(96,'Q',[3,2**64-1]),
            (104,'Q',[0,32769,2**64-1]),(112,'Q',[3,8192]),(136,'Q',[0x400000])]:
            for value in values:
                b=bytearray(raw);struct.pack_into('<'+fmt,b,off,value)
                with self.subTest(off=off,value=value),self.assertRaises(ValueError):p.prepare(bytes(b),[])
        for b in (b'',raw[:63],raw[:175],raw[:8193],raw+bytes(65537)):
            with self.assertRaises(ValueError):p.prepare(b,[])
        for args in (['x']*9,['x'*128],['a\0b'],['\u2603']):
            with self.assertRaises(ValueError):p.prepare(raw,args)
        self.assertEqual(len(p.prepare(raw,['x'*127]*8)),36896)

    def test_actual_admission_and_startup(self):
        body=(ROOT/'arch/x86_64/exec/boot_programs.inc').read_text().split('; END_PURE_ADMISSION')[0]
        run=(ROOT/'arch/x86_64/proc/process_run.inc').read_text().split('process_run_admit64:',1)[1].split('process_run_validate64:',1)[0]
        asm='BITS 64\n%define REIST_NATIVE_PROGRAMS 1\nsection .text\nglobal boot_program_admit64\nglobal process_run_admit64\n'+body
        asm+='\nprocess_run_admit64:\n'+run
        asm+=(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        host.TaskFrameTests().build(asm,ROOT/'test/x86_64_boot_programs_host.c','BOOT_PROGRAMS_HOST')

if __name__=='__main__':unittest.main()
