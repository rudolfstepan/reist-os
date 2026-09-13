"""Actual native mediator and Ring3 transfer behavior at O0/O2."""
from pathlib import Path
import sys,unittest,os,subprocess,uuid,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'test'))
sys.path.insert(0,str(ROOT/'scripts'))
import test_x86_64_task_frames as host

class PioTests(unittest.TestCase):
    def test_generated_fatal_injection_points(self):
        from collections import defaultdict
        import run_qemu_x86_64_pio as p
        symbols=defaultdict(int,{'native_pio_out8.done':1000,'native_pio_syscall64':1001,
                                'native_pio_apply64':2000,'timer_runtime_progress64':3000,'process_ipc_take64':5000,
                                'x86_64_scheduler_shell_timer_validate64':4000})
        for kind in p.FATAL_CASES:
            code=p.fatal_observer(symbols,ROOT/'build/codex-agent/r83ah-pio',kind)
            expected=3000 if kind in ('expired','backward','lease','eoi') else 4000 if kind=='context' else 5000 if kind=='ipc-ticket' else 2000
            self.assertIn("trigger=Probe("+str(expected)+",'trigger',False)",code)
            self.assertNotIn("trigger=Probe(1001",code) # No adjacent RET/entry debugger traps.
            compile(code.split('python\n',1)[1].rsplit('end\ncontinue',1)[0],'<actual-fatal-observer>','exec')

    def test_clock_injection_at_short_boot(self):
        import run_qemu_x86_64_pio as p
        for now in (0,1,3000000000,3000000001,1<<62):
            values=(now,now+3000000000,2,2)
            expired=p.fatal_clock_inputs('expired',*values)
            self.assertGreaterEqual(expired[1],3000000000)
            self.assertEqual(expired[0],expired[1]+1)
            backward=p.fatal_clock_inputs('backward',*values)
            self.assertEqual(backward[1]-backward[0],3000000001)
            self.assertEqual(p.fatal_clock_inputs('lease',*values)[1],0)
            self.assertEqual(p.fatal_clock_inputs('eoi',*values)[2:],(2,3))
        with self.assertRaises(ValueError):p.fatal_clock_inputs('unknown',0,0,0,0)
        with self.assertRaises(ValueError):p.fatal_clock_inputs('expired',1<<63,0,0,0)

    def test_fatal_oracle_rejects_missing_reordered_and_resumed(self):
        import run_qemu_x86_64_pio as p
        for kind,reason in p.FATAL_CASES.items():
            events=['PIO_FATAL_RELEASE','PIO_FATAL_INJECT '+kind]
            if reason:events+=['PIO_FATAL_REASON '+str(reason)]
            events+=['PIO_FATAL_FENCE physical=1 unchanged=1','PIO_FATAL_DIAG fenced=1 unchanged=1',
                     'PIO_FATAL_HALT unchanged=1']
            trace='\n'.join(events)
            serial='REIST_X86_64_EXCEPTION_FATAL '+('pio=1' if kind in ('metadata','scheduler','ipc-ticket') else 'vector=06' if kind=='kernel' else 'vector=20')
            p.validate_fatal(serial,trace,kind)
            for i in range(len(events)):
                with self.assertRaises(ValueError):p.validate_fatal(serial,'\n'.join(events[:i]+events[i+1:]),kind)
            for bad in (trace+trace,trace.replace('unchanged=1','unchanged=0',1),
                        '\n'.join(events[:-2]+events[-2:][::-1]),trace+'\nPIO_FATAL_OBSERVER_FAIL'):
                with self.assertRaises(ValueError):p.validate_fatal(serial,bad,kind)
            for bad in ('',serial+serial,serial+'\nPROCESS_REAP_OK',serial.replace('FATAL','OK')):
                with self.assertRaises(ValueError):p.validate_fatal(bad,trace,kind)

    def test_actual_common_fatal_fence(self):
        pio=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
        match=re.search(r'^native_pio_emergency_fence64:\n.*?(?=^[A-Za-z_]\w*:)',pio,re.M|re.S)
        self.assertIsNotNone(match,'missing unconditional physical fatal fence')
        fatal=(ROOT/'arch/x86_64/cpu/exceptions.asm').read_text()
        body=fatal[fatal.index('exception_fatal:'):fatal.index('serial_hex8:')]
        self.assertLess(body.index('call native_pio_emergency_fence64'),body.index('call serial_init64'))
        # Privileged CLI is a NOP only in the host adapter; actual port call is
        # witnessed. Every remaining fatal instruction is assembled unchanged.
        asm='''BITS 64
%define REIST_NATIVE_PIO 1
EXCEPTION_FRAME_VECTOR equ 120
section .bss
events: resq 1
section .rodata
exception_fatal_message: db 0
newline_message: db 0
section .text
global fatal_test
fatal_test:
    mov qword [rel events],0
    sub rsp,176
    mov qword [rsp+120],32
    jmp exception_fatal
native_pio_out8:
    cmp edi,0x3f6
    jne wrong
    cmp esi,6
    jne wrong
    cmp qword [rel events],0
    jne wrong
    inc qword [rel events]
    ret
serial_init64:
    cmp qword [rel events],1
    jne wrong
    inc qword [rel events]
    ret
serial_write64:
serial_hex8:
    cmp qword [rel events],2
    jne wrong
    ret
wrong:
    mov qword [rel events],99
    ret
halt64:
    mov rax,[rel events]
    add rsp,176
    ret
'''+match.group().replace('    cli','    nop')+body.replace('    cli','    nop')
        code='''#include <stdint.h>
#include <stdio.h>
extern uint64_t __attribute__((sysv_abi)) fatal_test(void);
int main(void) {for(unsigned n=0;n<16;n++)if(fatal_test()!=2)return 1;
puts("PIO_FATAL_HOST_OK");return 0;}
'''
        host.TaskFrameTests().build(asm,code,'PIO_FATAL_HOST')

    def test_actual_clock_failure_reasons(self):
        source=(ROOT/'arch/x86_64/cpu/timer_interrupt.asm').read_text()
        body=re.search(r'^timer_runtime_progress64:\n.*?(?=^[A-Za-z_]\w*:)',source,re.M|re.S).group()
        asm='''BITS 64
TSC_DEADLINE_CYCLES equ 3000000000
section .text
global clock_reason
clock_reason:
    call timer_runtime_progress64
    mov rax,r9
    ret
'''+body
        code='''#include <stdint.h>
#include <stdio.h>
extern uint64_t __attribute__((sysv_abi)) clock_reason(uint64_t,uint64_t,uint64_t,uint64_t);
int main(void) {
    uint64_t d=3000000100ULL,h=1ULL<<60;
    if(clock_reason(100,d,2,2)!=0 || clock_reason(d,d,2,2)!=0)return 1;
    if(clock_reason(d+1,d,2,2)!=4 || clock_reason(99,d,2,2)!=5)return 2;
    if(clock_reason(100,2999999999ULL,2,2)!=3)return 3;
    if(clock_reason(100,d,2,3)!=2 || clock_reason(100,d,h-1,h-1)!=1)return 4;
    if(clock_reason(UINT64_MAX,UINT64_MAX,2,2)!=6)return 5;
    puts("PIO_CLOCK_REASON_HOST_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,code,'PIO_CLOCK_REASON_HOST')

    def test_actual_image_transport_copy(self):
        source=(ROOT/'arch/x86_64/user/pio_domain.c').read_text()
        helper=re.search(r'static void image_words\(.*?^}',source,re.M|re.S).group()
        code='#include <stdint.h>\n#include <stdio.h>\n'+helper+'''
int main(void) {
    unsigned char from[36928],to[36928];
    for(unsigned offset=0;offset<16;offset++) {
        for(unsigned n=0;n<sizeof(from);n++){from[n]=(unsigned char)(n^0xa5);to[n]=0xcc;}
        image_words(to+offset+8,from+offset+8);
        for(unsigned n=0;n<sizeof(to);n++)
            if(to[n]!=(n>=offset+8 && n<offset+8+36896?from[n]:0xcc))return 1;
        image_words(to+offset+8,0);
        for(unsigned n=0;n<sizeof(to);n++)
            if(to[n]!=(n>=offset+8 && n<offset+8+36896?0x5a:0xcc) || from[n]!=(unsigned char)(n^0xa5))return 2;
    }
    puts("PIO_IMAGE_COPY_HOST_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',code,'PIO_IMAGE_COPY_HOST')

    @staticmethod
    def sample(case,oom,*,block=False):
        import run_qemu_x86_64_pio as r
        import struct,hashlib
        common=[m for m in r.startup.family.REQUIRED_MARKERS if 'SHELL' not in m]
        cut=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
        serial='\n'.join(common[:cut])+'\n';trace='';seq=0
        def frames(mode,slot,gen,state):
            nonlocal seq
            seq+=1;fs=[0,0,0x100001000,0x100002000,0,0,0,0,0x100003000,0x100004000,0x100005000,0x100006000,0x100007000]
            text=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=100007000 active=13e000 before=1000000 fp=1 frames='+','.join(f'{f:x}' for f in fs)+'\n'
            text+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in fs if f)
            return text+f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=1000007 zero=1\n'
        for mode in (1,2,3):
            for slot in (0,1):trace+=frames(mode,slot,slot+1,4 if slot==0 else 3 if mode==1 else 5)
        for slot in range(4):trace+=frames(4,slot,10+slot,3 if slot==3 else 4)
        for slot in range(4):trace+=frames(5,slot,20+slot,4)
        for slot,gen,state in ((0,30,4),(1,31,8),(1,32,8)):trace+=frames(6,slot,gen,state)
        modes=r.modes(case);count=len(modes)+2
        for run in range(2):
            base=run*count
            trace+=f'FAMILY_START slot=0 gen={base+1} image=3 high=1 wx=1 argv=1\nFAMILY_START slot=1 gen={base+2} image=4 high=1 wx=1 argv=1\n'
            if oom is not None:trace+=f'FAMILY_OOM acquired={oom}\nSTARTUP_OOM_BOUNDARY owner={(base+1)<<32} acquired={oom} result=-12\n'
            order=[]
            for i,mode in enumerate(modes,3):
                gen=base+i;length=0 if case==2 else 256 if mode in (1,2,4) else 512
                trace+=f'IMPORT_COPY gen={gen} bytes=36896 immutable=1\nSTARTUP_ARGS gen={gen} argc={4 if block else 2} immutable=1\nFAMILY_START slot=2 gen={gen} image=7 high=1 wx=1 argv=1\nPIO_BIND gen={gen} recycled=1\n'
                if mode==2:trace+=f'FAMILY_CANCEL slot=2 gen={gen} state=6 ipc=0 heap=0 reason={3 if case==3 else 2}\n'
                if block and mode==3:trace+=f'FAMILY_CANCEL slot=2 gen={gen} state=6 ipc=1 heap=0 reason=2\n'
                payload=r.SECTOR[:length]
                if block:
                    length=0 if case==2 else 768 if mode in (1,2,4) else 1024 if mode==3 else 1536
                    payload=(r.BLOCK_DISK[:1024]+r.BLOCK_DISK[127*512:])[:length]
                trace+=f'PIO_RETIRE gen={gen} identify={0 if case==2 else 512} data={length} sha256={hashlib.sha256(payload).hexdigest()} fenced=1\n'
                status,state=(0,3) if case==3 or mode==2 or block and mode==3 else (134,3) if mode==1 else (256,3) if mode==4 else (89 if case==2 else 80,4)
                order.append((2,gen,status,state))
                trace+=f'FAMILY_FENCE slot=2 gen={gen} ipc=1 heap=1 profile=1\n'+frames(8,2,gen,state)
            for slot,status,state in ((0,134 if case==3 else 79 if case==2 else 78,3 if case==3 else 4),(1,77,4)):
                gen=base+slot+1;order.append((slot,gen,status,state))
                trace+=f'FAMILY_FENCE slot={slot} gen={gen} ipc=1 heap=1 profile=1\n'+frames(8,slot,gen,state)
            for slot,gen,status,state in order:
                serial+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,state,32 if status==256 else 1,0x40002b).hex().upper()+'\n'
            serial+=r.startup.family.process.DONE+'\n'
            trace+=f'PROCESS_ZERO_OK run={run+1} zero=1 free=1000007 initial=1000007 reaps={count} generation={(run+1)*count} ticks={(run+1)*100}\nPIO_ZERO run={run+1} complete=1\nFAMILY_ZERO run={run+1} complete=1\n'
        trace+=('IMPORT_SCRUB bytes=36896 complete=1\nSTARTUP_SCRUB bytes=4096 complete=1\n')*r.minimum_scrubs(case,block)
        return serial+'\n'.join(common[cut:])+'\n'+r.startup.family.process.SUCCESS+'\n',trace

    def test_guest_oracle(self):
        import run_qemu_x86_64_pio as r
        for case,oom in [(0,None),*((1,n) for n in (0,1,2,3,6,9)),(2,None),(3,None)]:
            serial,trace=self.sample(case,oom)
            self.assertEqual(r.validate(serial,trace,case,oom),2*(len(r.modes(case))+2))
            self.assertEqual(r.minimum_scrubs(case),{0:40,1:38,2:10,3:8}[case])
            with self.assertRaisesRegex(ValueError,'temporary scrub'):
                r.validate(serial,trace.replace('IMPORT_SCRUB bytes=36896 complete=1\nSTARTUP_SCRUB bytes=4096 complete=1\n','',1),case,oom)
            for label in ('PIO_BIND','PIO_RETIRE','PIO_ZERO','FAMILY_ZERO','FAMILY_START','FAMILY_FENCE','PROCESS_ZERO_OK','TASK_FRAMES_BEFORE','TASK_FRAMES_AFTER','TASK_FRAMES_FREE','IMPORT_COPY','STARTUP_ARGS','IMPORT_SCRUB'):
                with self.assertRaises(ValueError):r.validate(serial,trace.replace(label,'MISSING',1),case,oom)
            for a,b in (('recycled=1','recycled=0'),('fenced=1','fenced=0'),('data=512','data=511'),('data=256','data=255'),('identify=512','identify=510'),('argc=2','argc=3'),('reason=2','reason=3'),('reason=3','reason=2'),('after=1000007','after=1000008')):
                if a in trace:
                    with self.assertRaises(ValueError):r.validate(serial,trace.replace(a,b,1),case,oom)
            for bad in (serial+serial,serial+r.startup.family.FAILURES[0]):
                with self.assertRaises(ValueError):r.validate(bad,trace,case,oom)

    def test_generated_cow_boundary(self):
        import run_qemu_x86_64_pio as r
        from unittest.mock import patch
        folder=ROOT/'build/codex-agent/r83ah-pio'/('media-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        fixture=r.Fixture(folder);fixture.verify('created')
        args=fixture.arguments(folder)
        self.assertIn('"read-only":true',args[1]);self.assertIn('"read-only":true',args[3])
        self.assertEqual(args[-1],'ide-hd,drive=pio-layer,bus=ide.0,unit=0')
        for other in (ROOT,ROOT/'build',folder.parent):
            with self.assertRaises(ValueError):fixture.arguments(other)
        with self.assertRaises(ValueError):r.Fixture(folder)
        with patch.object(r.startup.family.programs,'_capture',side_effect=RuntimeError('capture failure')):
            with self.assertRaisesRegex(RuntimeError,'capture failure'):
                r.startup.family.programs.capture(Path('unused'),folder,'',4096,fixture)
        self.assertIn('"passed": true',(folder/'media-after.json').read_text())
        original=fixture.run
        def allocated(*args):
            if args[0]=='map':return '[{"start":0,"length":65536,"depth":0}]'
            return original(*args)
        with patch.object(fixture,'run',side_effect=allocated):
            with self.assertRaisesRegex(ValueError,'allocated overlay'):
                fixture.verify('bad-map')
        with fixture.base.open('r+b') as raw:raw.write(b'X') # Only this generated negative-test medium.
        with self.assertRaisesRegex(ValueError,'base changed'):fixture.verify('bad-base')

    def test_production_cores(self):
        pio=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
        core=pio.split('; END_PIO_CORE')[0]
        family_source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        family=family_source.split('; RUNTIME ADAPTER')[0]
        asm='BITS 64\n%define REIST_NATIVE_PIO 1\nsection .text\nextern native_pio_in8,native_pio_in16,native_pio_out8\n'
        asm+=core+family+(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        asm+='\n'+re.search(r'^family_profile_apply64:\n.*?(?=^family_initialize64:)',family_source,re.M|re.S).group()
        asm+='\n'+(ROOT/'arch/x86_64/proc/syscall_profile.asm').read_text()
        asm+='\nTASK_STATE equ 0\nTASK_GENERATION equ 8\nTASK_FREE equ 0\nTASK_READY equ 1\nTASK_BLOCKED equ 6\nPF_R equ 4\nPF_W equ 2\n'
        adapter=pio[pio.index('native_pio_syscall64:'):pio.index('section .data')]
        # Only privileged CLI and the platform's halt/serial endpoints are
        # adapted; the actual fatal path must still fence before the halt.
        asm+=adapter.replace('    cli','    nop').replace('extern serial_init64\n','').replace('extern halt64\n','')
        asm+='''
section .rodata
native_pio_fatal_message: db 0
section .text
serial_init64:
serial_write64:
    ret
halt64:
    jmp scheduler_fail
section .bss
alignb 8
global native_pio_state,native_pio_request,scheduler_tasks,family_records
global family_extended_masks,family_profiles
global syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9
global scheduler_current_slot,scheduler_last_tick,host_faulted,host_output
native_pio_state: resq 8
native_pio_request: resq 8
scheduler_tasks: resq 128
family_records: resq 32
family_extended_masks: resq 8
family_profiles: resq 16
scheduler_current_slot: resq 1
scheduler_last_tick: resq 1
syscall_rdi: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
host_faulted: resq 1
host_output: resq 1
host_stack: resq 1
section .text
global profile_adapter_test
profile_adapter_test:
    mov eax,ecx
    jmp family_profile_apply64
global pio_adapter_test
pio_adapter_test:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    sub rsp,8
    mov [rel host_stack],rsp
    mov qword [rel host_faulted],0
    mov eax,[rel scheduler_current_slot]
    shl eax,8
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
scheduler_fail:
    mov qword [rel host_faulted],1
    mov rax,-84
    jmp process_run_resume64
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
scheduler_validate_shell_range64:
    cmp ecx,PF_W
    je .output
    cmp edx,64
    jne .bad
    cmp rax,[rel syscall_rsi]
    jne .bad
    cmp rax,4096
    jbe .bad
    mov eax,1
    ret
.output:
    cmp rax,[rel host_output]
    jne .bad
    test edx,edx
    jz .bad
    cmp edx,32
    ja .bad
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret
'''
        host.suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ah-pio'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        source=folder/'core.asm';source.write_text(asm,encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2500:]);return r.stdout
        obj=folder/'core.o';run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',source,'-o',obj],'asm')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([host.find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include',ROOT/'test/x86_64_pio_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('NATIVE_PIO_HOST_OK',run([exe],opt+'-run'))

if __name__=='__main__':unittest.main()
