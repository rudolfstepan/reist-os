"""Actual native terminal admission/state machinery, not pattern-only claims."""
from pathlib import Path
import ast,copy,hashlib,inspect,json,re,struct,subprocess,sys,textwrap,types,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host

class TerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'build/codex-agent/r83av-terminal/host'/uuid.uuid4().hex
        cls.folder.mkdir(parents=True)

    def test_actual_explicit_profile_admission(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        body=source.split('family_profile_admit64:',1)[1].split('; RDI profile-v1,',1)[0]
        asm='BITS 64\n%define REIST_NATIVE_PIO 1\n%define REIST_NATIVE_TERMINAL 1\nsection .text\nglobal family_profile_admit64\nfamily_profile_admit64:\n'+body
        c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int64_t __attribute__((sysv_abi)) family_profile_admit64(const void *);
#define CHECK(c) do { if(!(c)){printf("line %d\\n",__LINE__);return 1;} }while(0)
int main(void) {
    const uint64_t io=(1ULL<<15)|(1ULL<<20),ctl=1ULL<<63;
    uint64_t p[5]={1ULL|(40ULL<<32),(1ULL<<9)|io,ctl,0,0};
    CHECK(family_profile_admit64(p)==1);
    for(unsigned bits=0;bits<8;bits++) {
        p[1]=(1ULL<<9)|((bits&1)?1ULL<<15:0)|((bits&2)?1ULL<<20:0);p[2]=(bits&4)?ctl:0;
        uint64_t before[5];memcpy(before,p,sizeof p);
        CHECK(family_profile_admit64(p)==(bits==0||bits==7?1:-13));
        CHECK(!memcmp(before,p,sizeof p));
    }
    p[1]=(1ULL<<9)|io;p[2]=ctl|(1ULL<<49);CHECK(family_profile_admit64(p)==-13);
    p[2]=ctl;p[3]=1ULL<<4;CHECK(family_profile_admit64(p)==-13);
    p[1]=1ULL<<9;p[2]=1ULL<<49;p[3]=0;CHECK(family_profile_admit64(p)==1);
    puts("TERMINAL_PROFILE_OK");return 0;
}'''
        host.TaskFrameTests().build(asm,c,'TERMINAL_PROFILE')

    def test_actual_dynamic_descriptor_readmission(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('process_run_admit64:',1)[1].split('process_run_validate64:',1)[0]
        asm='BITS 64\n'+''.join('%define REIST_NATIVE_'+n+' 1\n' for n in
            ('PROGRAMS','LIFECYCLE','TASK_POOL','SERVICE_CPU','CONSOLE','SERVICE_CONSOLE','TERMINAL'))
        asm+='section .text\nglobal process_run_admit64\nprocess_run_admit64:\n'+body
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int64_t __attribute__((sysv_abi)) process_run_admit64(const void *);
typedef struct {uint32_t version,size,count,reserved;uint64_t tasks[8][4],periods[8];} Plan;
#define CHECK(x) do {if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
int main(void) {
    Plan original={5,336,8,0,{{0}},{100,100,0,0,0,0,0,0}};
    for(unsigned n=0;n<8;n++) {
        original.tasks[n][0]=n<2;original.tasks[n][1]=1ULL<<9;
        original.tasks[n][2]=32;original.tasks[n][3]=n<2?n+3:n+5;
    }
    CHECK(process_run_admit64(&original)==1);
    for(unsigned slot=0;slot<8;slot++)for(unsigned bits=0;bits<4;bits++) {
        Plan p=original;p.tasks[slot][1]|=((bits&1)?1ULL<<15:0)|((bits&2)?1ULL<<20:0);
        Plan before=p;CHECK(process_run_admit64(&p)==(!bits || !slot || (slot>=2 && bits==3)));
        CHECK(!memcmp(&before,&p,sizeof p));
        if(bits) {p.version=4;p.size=272;memset(p.periods,0,sizeof p.periods);CHECK(!process_run_admit64(&p));}
    }
    puts("TERMINAL_DESCRIPTOR_OK");return 0;
}'''
        host.TaskFrameTests().build(asm,c,'TERMINAL_DESCRIPTOR')

    def test_actual_state_machine(self):
        source=(ROOT/'arch/x86_64/proc/native_terminal.inc').read_text().split('; RUNTIME ADAPTER',1)[0]
        host.TaskFrameTests().build('BITS 64\nsection .text\n'+source,ROOT/'test/x86_64_terminal_host.c','TERMINAL_STATE')

    def test_actual_compact_child_and_syscall_abi(self):
        source=(ROOT/'arch/x86_64/user/terminal_program.asm').read_text()
        abi=(ROOT/'userspace/sdk/include/reist/abi/syscall.h').read_text()
        for name,value in re.findall(r'^SYS_(\w+) equ (\d+)$',source,re.M):
            abi_name='IPC_'+name if name in ('SEND_TIMEOUT','RECEIVE_TIMEOUT') else name
            self.assertRegex(abi,r'X\('+abi_name+r', '+abi_name+r', '+value+r'U\)')
        source=source.replace('global main\nmain:','global terminal_program_main\nterminal_program_main:')
        source=source.split('section .note.GNU-stack',1)[0].replace('    syscall','    call host_trap')
        source+='''
extern terminal_backend
host_trap:
    push rbp
    mov rbp,rsp
    push rdi
    push rsi
    push rdx
    push r8
    push r9
    push r10
    mov rcx,rdx
    mov rdx,rsi
    mov rsi,rdi
    mov rdi,rax
    and rsp,-16
    call terminal_backend
    lea rsp,[rbp-48]
    pop r10
    pop r9
    pop r8
    pop rdx
    pop rsi
    pop rdi
    pop rbp
    ret
'''
        c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int __attribute__((sysv_abi)) terminal_program_main(uint64_t,char **,char **);
static int held,ready,denials,writes,releases,fault,error,attempts;
#define NEED(c) do {if(!(c)){error=__LINE__;return -5;}}while(0)
int64_t __attribute__((sysv_abi)) terminal_backend(uint64_t n,uint64_t a,uint64_t b,uint64_t c) {
    if(n==22){NEED(!a&&!b&&!c);return 5;}
    if(n==41){NEED(a==10&&!b&&!c);return 0;}
    if(n==53){
        unsigned char *m=(void*)(uintptr_t)b;uint32_t *h=(void*)m;uint64_t pid=0,magic=0;
        NEED(a==0x1234 && c==1000 && h[0]==1 && h[1]==140 && h[2]==16);
        memcpy(&pid,m+12,8);memcpy(&magic,m+20,8);NEED(pid==5 && magic==0x214f523436464c45ULL);
        for(unsigned i=28;i<140;i++)NEED(!m[i]);
        return ++attempts==1?-9:fault==1?-32:0;
    }
    if(n==54){
        unsigned char *m=(void*)(uintptr_t)b;uint32_t *h=(void*)m;
        NEED(a==0x1234 && c==1000 && h[0]==1 && h[1]==140 && h[2]==128);
        uint64_t pid=5,magic=0x4f4734364556494cULL;h[2]=16;
        memcpy(m+12,&pid,8);memcpy(m+20,&magic,8);
        if(fault==2)m[139]=1;
        if(fault==3)h[2]=15;
        held=ready=1;return 0;
    }
    if(n==127){
        const uint32_t *q=(void*)(uintptr_t)a;
        NEED(!b&&!c && q[0]==1 && q[1]==24 && !q[3]&&!q[4]&&!q[5]);
        if(q[2]==5)return held?0:-11;
        NEED(q[2]==3);held=0;releases++;return 0;
    }
    if(n==113||n==132){NEED(!ready&&!b&&!c && a==(n==113?29:0));denials++;return -13;}
    if(n==15){
        NEED(!a);
        if(!held){NEED(!b&&!c);denials++;return -13;}
        NEED(c==1 && *(unsigned char*)(uintptr_t)b==0xa5);return fault==4?1:-11;
    }
    if(n==20){
        NEED(a==1);
        if(!held){NEED(!b&&!c);denials++;return -13;}
        NEED(c==1 && *(unsigned char*)(uintptr_t)b=='T');writes++;return 1;
    }
    error=__LINE__;return -5;
}
int main(void) {
    char *args[]={"/boot.prg","00001234","0",0},*env[]={0};
    for(fault=0;fault<5;fault++) {
        held=ready=denials=writes=releases=error=attempts=0;
        int r=terminal_program_main(3,args,env);
        if(error || r!=(fault?204:82)){printf("mode%d result%d backend%d\\n",fault,r,error);return 1;}
        if(!fault && (held||denials!=6||writes!=1||releases!=2||attempts!=2))return 2;
    }
    puts("TERMINAL_PROGRAM_OK");return 0;
}'''
        host.TaskFrameTests().build(source,c,'TERMINAL_PROGRAM')

    def test_actual_fixture_compilation_and_file_bound(self):
        import test_x86_64_live_file as old
        source=textwrap.dedent(inspect.getsource(old.LiveFileTests.test_actual_new_role_syntax_and_file_extent))
        source=source.replace('arch/x86_64/user/live_file.c','arch/x86_64/user/service_console.c')
        source=source.replace("'-DREIST_NATIVE_LIVE_FILE=1'","'-DREIST_NATIVE_LIVE_FILE=1','-DREIST_NATIVE_SERVICE_CONSOLE=1','-DREIST_NATIVE_TERMINAL=1'")
        ns=dict(vars(old));exec(source,ns);ns['test_actual_new_role_syntax_and_file_extent'](self)

    def test_actual_kernel_adapter_io_and_retirement(self):
        terminal=(ROOT/'arch/x86_64/proc/native_terminal.inc').read_text()
        console=(ROOT/'arch/x86_64/proc/native_console.inc').read_text()
        body=(terminal+'\n'+console).replace('    in al,dx','    call port_in').replace('    out dx,al','    call port_out')
        asm='''BITS 64
%define REIST_NATIVE_TERMINAL 1
TASK_GENERATION equ 8
TASK_STATE equ 0
TASK_READY equ 1
TASK_RUNNING equ 2
TASK_BLOCKED equ 6
NATIVE_TASK_SHIFT equ 10
NATIVE_POOL_TASKS equ 8
NATIVE_POOL_RUN_VERSION equ 5
REIST_SYS_READ equ 15
REIST_SYS_WRITE equ 20
PF_R equ 4
PF_W equ 2
COM1_DATA equ 0x3f8
COM1_LSR equ 0x3fd
section .bss
global scheduler_tasks,family_records,family_profiles,native_terminal_state,scheduler_current_slot
global syscall_rax,syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9
scheduler_tasks: resb 8192
family_records: resb 512
family_profiles: resb 256
native_terminal_state: resq 3
scheduler_current_slot: resq 1
syscall_rax: resq 1
syscall_rdi: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
section .text
global terminal_apply,console_apply,terminal_retire
extern host_in,host_out,host_range,host_fatal
terminal_apply:
    xor eax,eax
    jmp enter
console_apply:
    mov eax,1
    jmp enter
terminal_retire:
    mov eax,2
enter:
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp,8
    mov ecx,[rel scheduler_current_slot]
    shl ecx,10
    lea r12,[rel scheduler_tasks]
    add r12,rcx
    test eax,eax
    jz native_terminal_syscall64
    cmp eax,1
    je native_console_syscall64
    call native_terminal_retire_hook64
    xor eax,eax
process_run_resume64:
    add rsp,8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
scheduler_fail:
    and rsp,-16
    call host_fatal
    ud2
family_record64:
    mov eax,edi
    shl eax,6
    lea r10,[rel family_records]
    add r10,rax
    ret
scheduler_validate_shell_range64:
    push rbp
    mov rbp,rsp
    and rsp,-16
    mov rdi,rax
    mov rsi,rdx
    mov edx,ecx
    call host_range
    mov rsp,rbp
    pop rbp
    ret
port_in:
    push rbp
    mov rbp,rsp
    push rcx
    push rdx
    and rsp,-16
    movzx edi,dx
    call host_in
    lea rsp,[rbp-16]
    pop rdx
    pop rcx
    pop rbp
    ret
port_out:
    push rbp
    mov rbp,rsp
    and rsp,-16
    movzx edi,dx
    movzx esi,al
    call host_out
    mov rsp,rbp
    pop rbp
    ret
'''+body
        c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
extern uint64_t scheduler_tasks[8][128],family_records[8][8],family_profiles[8][4],native_terminal_state[3],scheduler_current_slot;
extern uint64_t syscall_rax,syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9;
extern int64_t __attribute__((sysv_abi)) terminal_apply(void),console_apply(void),terminal_retire(void);
static uint32_t request[6];static unsigned char byte;static unsigned rx,reads,writes,ranges,fail_uart;
static jmp_buf fatal;
static const uint64_t root=1ULL<<32,child=(5ULL<<32)|4;
#define CHECK(c) do {if(!(c)){printf("line %d\\n",__LINE__);return 1;}}while(0)
void __attribute__((sysv_abi,noreturn)) host_fatal(void){longjmp(fatal,1);}
int __attribute__((sysv_abi)) host_range(uint64_t p,uint64_t n,unsigned flags) {
    ranges++;return (p==(uintptr_t)request && n==24 && flags==4) || (p==(uintptr_t)&byte && n==1);
}
unsigned __attribute__((sysv_abi)) host_in(unsigned port) {
    reads++;if(port==0x3fd)return fail_uart?2:0x20|(rx?1:0);
    if(port==0x3f8 && rx){--rx;return 'x';}return 0;
}
void __attribute__((sysv_abi)) host_out(unsigned port,unsigned value){if(port==0x3f8&&value=='T')writes++;}
static void reset(void) {
    memset(scheduler_tasks,0,8192);memset(family_records,0,512);memset(family_profiles,0,256);
    for(unsigned i=0;i<5;i++) {
        scheduler_tasks[i][0]=i?6:2;scheduler_tasks[i][1]=i+1;
        family_records[i][0]=((uint64_t)(i+1)<<32)|i;family_records[i][1]=i>=2?root:0;
        family_records[i][5]=i<2?1:2;family_profiles[i][0]=i+1;
    }
    family_profiles[0][1]=family_profiles[4][1]=(1ULL<<9)|(1ULL<<15)|(1ULL<<20);
    family_profiles[0][2]=(1ULL<<49)|(1ULL<<63);family_profiles[4][2]=1ULL<<63;
    family_profiles[2][2]=1ULL<<49;
    native_terminal_state[0]=root;native_terminal_state[1]=native_terminal_state[2]=0;
    syscall_rax=127;syscall_rdi=(uintptr_t)request;syscall_rsi=syscall_rdx=syscall_r10=syscall_r8=syscall_r9=0;
    scheduler_current_slot=0;rx=reads=writes=ranges=fail_uart=0;
    request[0]=1;request[1]=24;request[2]=2;request[3]=0;request[4]=request[5]=5;
}
int main(void) {
    reset();rx=3;CHECK(terminal_apply()==0 && native_terminal_state[1]==child && !rx && reads==7);
    reads=0;CHECK(terminal_apply()==0 && !reads);
    syscall_rax=15;syscall_rdi=0;CHECK(console_apply()==-11 && !reads);
    scheduler_current_slot=4;syscall_rsi=(uintptr_t)&byte;syscall_rdx=1;byte=0xa5;rx=1;
    CHECK(console_apply()==1 && byte=='x' && !rx);
    syscall_rax=20;syscall_rdi=1;byte='T';CHECK(console_apply()==1 && writes==1);
    syscall_rax=127;syscall_rdi=(uintptr_t)request;syscall_rsi=syscall_rdx=0;
    request[2]=3;request[4]=request[5]=0;
    CHECK(terminal_apply()==0 && !native_terminal_state[1]);reads=0;CHECK(terminal_apply()==0 && !reads);
    syscall_rax=15;syscall_rdi=0;CHECK(console_apply()==-13 && !reads);
    reset();rx=64;CHECK(terminal_apply()==0 && !rx && reads==129);
    reset();rx=65;CHECK(terminal_apply()==-5 && rx==1 && reads==129 && native_terminal_state[2]==1 && !native_terminal_state[1]);
    reset();fail_uart=1;CHECK(terminal_apply()==-5 && reads==1 && native_terminal_state[2]==1);
    for(unsigned i=0;i<7;i++) {
        reset();rx=10;
        if(i==0)request[0]=2;
        if(i==1)request[1]=23;
        if(i==2)request[3]=1;
        if(i==3)request[4]=request[5]=3;
        if(i==4)request[4]=request[5]=99;
        if(i==5)syscall_rdi=0;
        if(i==6)syscall_r10=1;
        CHECK(terminal_apply()==(i==3?-13:i==4?-116:i==5?-14:-22));
        CHECK(!reads && rx==10 && native_terminal_state[0]==root && !native_terminal_state[1]);
    }
    reset();CHECK(terminal_apply()==0);scheduler_current_slot=4;rx=2;
    CHECK(terminal_retire()==0 && !native_terminal_state[1] && !rx);
    reads=0;CHECK(terminal_retire()==0 && !reads);
    reset();CHECK(terminal_apply()==0);rx=2;CHECK(terminal_retire()==0 && !native_terminal_state[0] && !native_terminal_state[1] && !rx);
    reset();CHECK(terminal_apply()==0);native_terminal_state[1]+=(1ULL<<32);
    if(setjmp(fatal)==0){(void)terminal_apply();return 2;}
    CHECK(!writes);
    puts("TERMINAL_ADAPTER_OK");return 0;
}'''
        host.TaskFrameTests().build(asm,c,'TERMINAL_ADAPTER')

    def test_actual_sdk_and_shell_adapter(self):
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/syscall.h>
static int64_t trap(uint64_t,uint64_t,uint64_t,uint64_t);
#define reist_x64_syscall0(n) trap(n,0,0,0)
#define reist_x64_syscall1(n,a) trap(n,a,0,0)
#define reist_x64_syscall3(n,a,b,c) trap(n,a,b,c)
#define REIST_NATIVE_TERMINAL 1
#include "userspace/sdk/lib/x86_64/console.c"
#include "userspace/sdk/lib/x86_64/shell_platform.c"
static int calls,clocks,error;
static int64_t answer;
static reist_terminal_input_request_t captured;
static int64_t trap(uint64_t op,uint64_t a,uint64_t b,uint64_t c) {
    if(op==REIST_X64_SYS_MONOTONIC_MS){clocks++;return 10;}
    if(op!=REIST_X64_SYS_TERMINAL_INPUT || b || c){error=1;return -5;}
    calls++;memcpy(&captured,(void*)(uintptr_t)a,sizeof captured);return answer;
}
#define CHECK(x) do{if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
int main(void) {
    CHECK(sizeof captured==24);
    for(unsigned op=1;op<=5;op++) {
        int pid=op==2?7:0;unsigned gen=op==2?7:0;
        CHECK(reist_x64_terminal_input(op,pid,gen)==0);
        CHECK(captured.version==1 && captured.struct_size==24 && captured.operation==op && !captured.reserved && captured.target_pid==pid && captured.target_generation==gen);
    }
    int before=calls;
    CHECK(reist_x64_terminal_input(0,0,0)==-22 && reist_x64_terminal_input(6,0,0)==-22);
    CHECK(reist_x64_terminal_input(2,0,1)==-22 && reist_x64_terminal_input(2,-1,1)==-22);
    CHECK(reist_x64_terminal_input(2,1,0)==-22 && reist_x64_terminal_input(2,1,0x80000000U)==-22);
    CHECK(reist_x64_terminal_input(1,1,0)==-22 && reist_x64_terminal_input(5,0,1)==-22 && calls==before);
    const int64_t results[]={0,-11,-13,-95,-116,-4095,1,-4096,INT64_MIN,INT64_MAX};
    for(unsigned n=0;n<sizeof results/sizeof *results;n++) {
        answer=results[n];CHECK(x86os_terminal_input(2,7,7)==(answer<=0 && answer>=-4095?answer:-5));
        CHECK(captured.target_pid==7 && captured.target_generation==7);
    }
    CHECK(clocks==10 && !error);puts("TERMINAL_SDK_OK");return 0;
}'''
        # Add only include search paths to the existing actual O0/O2 builder.
        c=c.replace('"userspace/', '"'+ROOT.as_posix()+'/userspace/')
        actual_run=subprocess.run
        def compile_with_sdk(command,**kwargs):
            command=list(command)
            if len(command)>1 and command[1]=='cc':command+=['-Iuserspace/sdk/include','-Iuserspace/storage/include']
            return actual_run(command,**kwargs)
        with patch.object(host.subprocess,'run',side_effect=compile_with_sdk):
            host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'TERMINAL_SDK')

    def test_old_producer_commands_exact(self):
        import test_x86_64_service_console as old
        import test_x86_64_live_file as prior
        source=textwrap.dedent(inspect.getsource(old.ServiceConsoleTests.test_old_producer_commands))
        # Execute the established full-vector producer comparison against the
        # immediately accepted predecessor, including its console profile.
        source=source.replace("'473da11c:scripts'","'53dd42d5:scripts'")
        source=source.replace('dict(pio_profile,filesystem=True,file_launch=True,live_file=True)])',
            'dict(pio_profile,filesystem=True,file_launch=True,live_file=True),dict(pio_profile,filesystem=True,file_launch=True,live_file=True,service_console=True)])')
        ns=dict(vars(old));exec(source,ns);ns['test_old_producer_commands'](self)

    def test_selectors_before_effects(self):
        import build_x86_64_boot_programs as producer
        from test_x86_64_live_file import PROFILE
        from test_x86_64_file_launch import direct_make_plan,MAKE_FILE_PROFILE
        for change in (dict(terminal=1),dict(terminal='1'),dict(service_console=False),dict(live_file=False),dict(console=True),dict(native_shell=True)):
            target=self.folder/('absent-'+uuid.uuid4().hex)
            with patch.object(producer.subprocess,'run',side_effect=AssertionError('premature tool')):
                with self.assertRaises(ValueError):producer.build(target,['cc'],['as'],['ld'],0,**(dict(PROFILE,service_console=True,terminal=True)|change))
            self.assertFalse(target.exists())
        options={'X86_64_NATIVE_'+n:'0' for n in MAKE_FILE_PROFILE}
        options.update({'X86_64_NATIVE_'+n:'1' for n in ('PROCESSES','IPC','RAM','HEAP','RUNTIME','PROGRAMS','LIFECYCLE','STARTUP','IMPORT','PIO','BLOCK','WIDE','BLOCK_PROFILE','FILESYSTEM','FILE_LAUNCH','TASK_POOL','POOL_PIO','LIVE_FILE','SERVICE_CONSOLE','TERMINAL')})
        result=direct_make_plan(self.folder,options);self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('--terminal',result.stdout);self.assertIn('-DREIST_NATIVE_TERMINAL=1',result.stdout)
        for change in ({'X86_64_NATIVE_TERMINAL':'2'},{'X86_64_NATIVE_TERMINAL':'1 0'},{'X86_64_NATIVE_SERVICE_CONSOLE':'0'}):
            self.assertNotEqual(direct_make_plan(self.folder,options|change).returncode,0)
        source=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text().split('$RepoRoot =',1)[0]
        source+='\n@{terminal=[int]$NativeTerminal.IsPresent;service=[int]$NativeServiceConsole.IsPresent;live=[int]$NativeLiveFile.IsPresent} | ConvertTo-Json -Compress\n'
        path=self.folder/'admit.ps1';path.write_text(source)
        for flags in ([],['-NativeConsole'],['-NativeShell'],['-NativeServiceCPU'],['-NativeServicePIO']):
            result=subprocess.run(['powershell.exe','-NoProfile','-File',str(path),'-NativeTerminal',*flags],capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if flags:self.assertNotEqual(result.returncode,0)
            else:self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),dict(terminal=1,service=1,live=1))

    def test_actual_observer_composition_and_scoped_start(self):
        import run_qemu_x86_64_terminal as run
        import test_x86_64_file_launch as fixture
        raw=fixture.sample()[-1]
        code=run.observer({},self.folder,0,2,None,raw)
        compile(code.split('\npython\n',1)[1].rsplit('\nend\ncontinue\n',1)[0],'<terminal GDB observer>','exec')
        self.assertEqual(code.count(run.EXTRA),1)
        original=run.live.observer({},self.folder,0,2,None,raw)
        self.assertIn("assert not any(mem(S['family_extended_masks']+slot*16,16))\n    record=copies[gen]",original)
        source=run.live.function(run.EXTRA,'terminal_started')
        modes=[7];current=[0,1];starts={};events=[];called=[];hook=types.SimpleNamespace(enabled=False)
        def previous():
            called.append(tuple(current))
            if modes[0]==8:starts.setdefault(current[1],{})
        ns=dict(terminal_original_start=previous,mode=lambda:modes[0],starts=starts,task=lambda slot:[2,current[1]],
            d=lambda address:current[0],S=dict(scheduler_current_slot=0,family_profiles=100),
            terminal_state=lambda:[1<<32,0,0],struct=struct,mem=lambda a,n:struct.pack('<4Q',current[1],0,0,0),
            terminal_emit=lambda kind,**row:events.append((kind,row)),terminal_denials=set(),terminal_denial_hook=hook,
            terminal_scope=run.TerminalProbeScope(),terminal_sync=lambda:None)
        exec(source,ns);invoke=ns['terminal_started'];invoke();self.assertFalse(events or hook.enabled)
        modes[0]=8
        for slot,gen in ((0,1),(0,1),(1,2),(2,3),(3,4),(4,5),(2,3)):
            current[:]=[slot,gen];invoke()
        self.assertEqual(len(called),8);self.assertEqual(len(events),5)
        self.assertEqual(ns['terminal_denials'],{2,3,4});self.assertTrue(hook.enabled)

    def test_fatal_mutation_and_raw_oracle(self):
        import run_qemu_x86_64_terminal as run
        saved=[bytearray(n) for _,n in run.FATAL_RANGES]
        struct.pack_into('<3Q',saved[0],0,1<<32,5<<32|4,0)
        struct.pack_into('<3Q',saved[1],0,3<<32|2,(3<<32|2)^0xffffffffffffffff,0)
        for slot,gen in ((0,1),(2,3),(3,4),(4,5)):struct.pack_into('<2Q',saved[2],slot*1024,2 if slot==4 else 6,gen)
        saved=list(map(bytes,saved))
        # The existing PIO corruption oracle validates its real complement
        # and range contract, independently of the new terminal oracle.
        import run_qemu_x86_64_pool_pio as accepted_pio
        accepted_pio.fatal_mutation('owner-slot8',saved[1:])
        wrong=list(saved);wrong[1]=wrong[1][:8]+struct.pack('<Q',1<<32)+wrong[1][16:]
        for kind in run.FATAL_CASES:
            with self.assertRaises(ValueError):run.fatal_mutation(kind,wrong)
        for kind in run.FATAL_CASES:
            changed,writes=run.fatal_mutation(kind,saved);self.assertEqual(sum(len(w[2]) for w in writes),8)
            self.assertEqual(saved[1:],changed[1:])
            folder=self.folder/kind;folder.mkdir();before=b''.join(saved);damage=b''.join(changed)
            for name,raw in [('before',before)]+[(n,damage) for n in ('damaged','fenced','diagnostic','halt')]:
                (folder/(name+'.bin')).write_bytes(raw)
            sha=hashlib.sha256(damage).hexdigest()
            events=[dict(kind='inject',case=kind,original=hashlib.sha256(before).hexdigest(),sha=sha,writes=8),
                dict(kind='fence',physical=1,sha=sha),dict(kind='diagnostic',sha=sha,interrupts=0),dict(kind='halt',sha=sha,cli_hlt=1)]
            def trace(rows):return ''.join('TERMINAL_FATAL '+json.dumps(r)+'\n' for r in rows)
            serial='REIST_X86_64_EXCEPTION_FATAL pio=1'
            run.validate_fatal(serial,trace(events),kind,folder)
            for index,key,value in ((0,'writes',16),(1,'physical',0),(2,'interrupts',1),(3,'cli_hlt',0)):
                bad=copy.deepcopy(events);bad[index][key]=value
                with self.assertRaises(ValueError):run.validate_fatal(serial,trace(bad),kind,folder)
            with self.assertRaises(ValueError):run.validate_fatal(serial,trace(events[:-1]),kind,folder)
            (folder/'halt.bin').write_bytes(before)
            with self.assertRaises(ValueError):run.validate_fatal(serial,trace(events),kind,folder)
            for index,offset in ((0,0),(0,8),(1,16),(2,4*1024+8)):
                bad=list(saved);part=bytearray(bad[index]);part[offset]^=1;bad[index]=bytes(part)
                with self.assertRaises(ValueError):run.fatal_mutation(kind,bad)

    def test_actual_scheduler_assembly_integration(self):
        flags=('PROCESSES','IPC','RAM','HEAP','RUNTIME','PROGRAMS','LIFECYCLE','STARTUP','IMPORT',
            'PIO','BLOCK','WIDE','BLOCK_PROFILE','FILESYSTEM','FILE_LAUNCH','TASK_POOL','POOL_PIO',
            'SERVICE_CPU','LIVE_FILE','CONSOLE','SERVICE_CONSOLE','TERMINAL')
        layout=ROOT/'build/codex-agent/r83au-service-console/native/x86_64/bootstrap_core_layout.inc'
        command=['C:/tools/nasm-3.02/nasm.exe','-f','elf64',*['-DREIST_NATIVE_'+n+'=1' for n in flags],
            '-DC_CORE_LAYOUT_PATH="'+layout.as_posix()+'"','arch/x86_64/proc/cooperative_scheduler.asm',
            '-o',str(self.folder/'scheduler-integration.o')]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (self.folder/'scheduler-integration.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))

    def test_complete_terminal_oracle_mutations(self):
        import run_qemu_x86_64_terminal as run
        def sample(case):
            plan=run.live.roles(case);rows=[];state=[0,0,0]
            def profile(g):
                slot=plan[g]['slot'];return [g,run.IO if slot in (0,4) else 0,
                    ((1<<49)|run.CTL) if slot==0 else 1<<49 if slot==2 else run.CTL if slot==4 else 0,16 if slot<2 else 0]
            def start(g):
                if plan[g]['slot']==0:state[:]=[g<<32,0,0]
                rows.append(dict(kind='start',gen=g,slot=plan[g]['slot'],state=state[:],profile=profile(g)))
            def call(g,op,result,operation=0,target=0):
                slot=plan[g]['slot'];before=state[:];size=24 if op==127 else int(slot in (0,4) and ((op==20 and result!=-13) or slot==4 and op==15 and result==-11))
                address=0x408000 if size else 0
                args=[address,0,0,0,0,0] if op==127 else [int(op==20),address,size,0,0,0]
                data=struct.pack('<4IiI',1,24,operation,0,target,target).hex() if op==127 else ('0a' if slot==0 else '54') if op==20 and size else 'a5' if size else ''
                if op==127 and operation==2 and result==0:state[1]=target<<32|4
                if op==127 and operation==3:state[1]=0
                rows.append(dict(kind='call',gen=g,slot=slot,profile=profile(g),op=op,args=args,state=before,after=state[:],
                    result=result,denied=slot in (1,2,3),size=size,address=address,data=data,data_after=data))
            def retire(g):
                before=state[:];handle=g<<32|plan[g]['slot']
                if state[0]==handle:state[:]=[0,0,0]
                elif state[1]==handle:state[1]=0
                rows.append(dict(kind='retire',gen=g,slot=plan[g]['slot'],state=before,after=state[:],task_state=plan[g]['state']))
            for iteration,root in enumerate([g for g,i in plan.items() if i['slot']==0],1):
                start(root);call(root,15,0);call(root,20,1)
                peer=root+1;start(peer);call(peer,15,-13);call(peer,20,-13);retire(peer)
                for n in range(1 if case in (7,15) else 2):
                    members=[g for g,i in plan.items() if i['root']==root and i['slot']>=2 and i['round']==n]
                    for g in members:start(g);call(g,15,-13);call(g,20,-13)
                    apps=[g for g in members if plan[g]['slot']==4]
                    for app in apps:
                        call(root,15,0);call(root,20,1)
                        for op,target,result in ((2,app-1,-13),(2,app-2,-13),(1,0,0),(2,app,0),(2,app,0),(5,0,-11)):
                            call(root,127,result,op,target)
                        call(root,15,-11)
                        if case!=15:
                            call(app,127,0,5);call(app,15,-11);call(app,20,1)
                            if plan[app]['status']==82:
                                call(app,127,0,3);call(app,127,0,3);call(app,127,-11,5);call(app,15,-13);call(app,20,-13)
                            retire(app)
                            call(root,127,0,5);call(root,127,-116,2,app);call(root,15,0)
                    if case in (7,15):retire(root)
                    for g in members:
                        if plan[g]['slot']!=4 or case==15:retire(g)
                if case not in (7,15):retire(root)
                rows.append(dict(kind='finish',run=iteration,state=[0,0,0]))
            return rows
        def evidence(rows):
            raw=b''.join((json.dumps(r)+'\n').encode() for r in rows)
            return 'TERMINAL_LEDGER '+str(len(rows))+' '+hashlib.sha256(raw).hexdigest()+'\n',raw
        for case in range(18):
            rows=sample(case);run.validate_terminal(*evidence(rows),case)
            call_index=next(n for n,r in enumerate(rows) if r['kind']=='call')
            mutations=[(call_index,'result',-13),(call_index,'denied',True),(call_index,'args',[0,0,1,0,0,0]),
                (call_index,'after',[1<<32,5<<32|4,0]),(0,'profile',[1,run.IO,1<<49,16]),(0,'state',[0,0,0])]
            for index,key,value in mutations:
                bad=copy.deepcopy(rows);bad[index][key]=value
                with self.assertRaises(ValueError):run.validate_terminal(*evidence(bad),case)
            for index in (0,call_index,len(rows)-1):
                with self.assertRaises((ValueError,KeyError)):run.validate_terminal(*evidence(rows[:index]+rows[index+1:]),case)
            trace,raw=evidence(rows)
            with self.assertRaises(ValueError):run.validate_terminal(trace,raw[:-1],case)
            with self.assertRaises(ValueError):run.validate_terminal(trace.replace('TERMINAL_LEDGER','LOST'),raw,case)

    def test_disabled_source_exact_predecessor(self):
        import verify_x86_64_terminal as verify
        self.assertEqual(len(verify.default_sources()),9)

    def test_actual_phase_scoped_probes(self):
        import run_qemu_x86_64_terminal as run
        scope=run.TerminalProbeScope()
        for g,s in ((1,0),(2,1),(3,2),(4,3)):scope.start(g,s)
        self.assertEqual((scope.io,scope.control),({1},set()))
        def result(g,s,op,value,operation=0):
            scope.returned(dict(gen=g,slot=s,op=op,result=value,
                data=struct.pack('<4IiI',1,24,operation,0,0,0).hex() if op==127 else ''))
        result(1,0,20,-11);self.assertEqual(scope.io,{1})
        result(1,0,20,1);self.assertFalse(scope.io or scope.control)
        for app in (5,8):
            scope.start(app,4);self.assertEqual(scope.io,{app})
            result(app,4,15,-13);result(app,4,20,-13);self.assertFalse(scope.io or scope.control)
            scope.ready(1);self.assertEqual((scope.io,scope.control),({1},{1}))
            result(1,0,20,1);self.assertEqual(scope.io,{1})
            result(1,0,127,-11,5);result(1,0,15,-11);self.assertFalse(scope.io or scope.control)
            scope.go(app);self.assertEqual((scope.io,scope.control),({app},{app}))
            result(app,4,127,0,5);result(app,4,15,-11);result(app,4,20,-11);result(app,4,20,1)
            if app==5:
                result(app,4,127,0,3);result(app,4,127,0,3);result(app,4,127,-11,5)
                self.assertFalse(scope.control);result(app,4,15,-13);result(app,4,20,-13)
                self.assertFalse(scope.io)
            # Fault/quota/cancel also close all app probes and reclaim root.
            scope.retire(app,4,[1<<32,0,0]);self.assertEqual((scope.io,scope.control),({1},{1}))
            result(1,0,127,0,5);result(1,0,127,-116,2);result(1,0,15,0)
            self.assertFalse(scope.io or scope.control)
        scope.start(11,4);result(11,4,15,-13);result(11,4,20,-13);scope.ready(1)
        result(1,0,15,-11);scope.retire(1,0,[0,0,0]);scope.retire(11,4,[0,0,0])
        self.assertFalse(scope.io or scope.control)
        # Independent later root generation never resurrects prior interests.
        scope.start(12,0);result(12,0,20,1);scope.start(16,4);scope.go(16)
        scope.retire(12,0,[0,0,0]);scope.retire(16,4,[0,0,0]);self.assertFalse(scope.io or scope.control)
        family=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        between=family.split('family_terminal64:',1)[1].split('    call native_pio_terminal64',1)[0]
        self.assertEqual(between.strip(),'cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION\n    jne .done\n%ifdef REIST_NATIVE_TERMINAL\n    call native_terminal_retire_hook64\n%endif\n%ifdef REIST_NATIVE_PIO')

    def test_exact_reuse_and_six_case_prefix(self):
        import verify_x86_64_terminal as verify
        f=verify.read(verify.REUSE_BASE/'frozen.json')
        prefix=verify.qualified_prefix(f);self.assertEqual(len(prefix),6)
        self.assertEqual(len(verify.qualified_normal(f)['cases']),25)
        for n in verify.REUSE:self.assertTrue(verify.reuse(n,f)['passed'])
        for change in (lambda m:m['sources'].__setitem__('arch/x86_64/proc/process_run.inc','0'*64),
                       lambda m:m['sources'].pop('arch/x86_64/proc/task_family.inc'),
                       lambda m:m['tools'].pop(next(iter(m['tools'])))):
            bad=copy.deepcopy(f);change(bad)
            with self.assertRaises(ValueError):verify.qualified_prefix(bad)
            with self.assertRaises(ValueError):verify.reuse(10,bad)
        path=ROOT/verify.read(verify.PREVIOUS/'stopped.json')['matrix'][0]['path'];original=verify.read
        for change in (lambda m:m.__setitem__('passed',True),lambda m:m.__setitem__('closed',False),
                       lambda m:m['cases'][0].__setitem__('passed',False),lambda m:m['cases'][6].__setitem__('passed',True),
                       lambda m:m['cases'][0].__setitem__('elapsed',46),lambda m:m['cases'][1].__setitem__('layout',3),
                       lambda m:m['image'].__setitem__('sha256','0'*64)):
            def changed_read(p):
                value=original(p)
                if Path(p)==path:change(value)
                return value
            with patch.object(verify,'read',side_effect=changed_read),self.assertRaises(ValueError):verify.qualified_prefix(f)
        normal_path=next((verify.REUSE_BASE/'guests').glob('attempt-*/summary.json'))
        for change in (lambda m:m.__setitem__('passed',False),lambda m:m['cases'].pop(),
                       lambda m:m['cases'][10].__setitem__('passed',False),lambda m:m['cases'][20].__setitem__('elapsed',46)):
            def bad_normal(p):
                value=original(p)
                if Path(p)==normal_path:change(value)
                return value
            with patch.object(verify,'read',side_effect=bad_normal),self.assertRaises(ValueError):verify.qualified_normal(f)

    def test_actual_fatal_probe_dispatch_return_and_failure(self):
        import run_qemu_x86_64_terminal as run
        code=run.live.cpu.defer_observer_callbacks(run.FATAL_BODY,('Probe',))
        node=next(n for n in ast.parse(code).body if isinstance(n,ast.ClassDef) and n.name=='Probe')
        class Breakpoint:
            def __init__(self,*args,**kwargs):pass
            def is_valid(self):return True
        class Quit(Exception):pass
        messages=[];events=[]
        def execute(command):raise Quit(command)
        ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,write=messages.append,execute=execute),
            injected=False,fenced=False,diagnosed=False,saved=None,struct=struct,S={'scheduler_current_slot':1,'native_pio_out8.done':9},
            mem=lambda address,size:struct.pack('<I',0) if address==1 else b'\xee',
            reg=lambda name:0x3f6 if name=='edx' else 6 if name=='eax' else 0,
            event=lambda kind,**row:events.append((kind,row)),snapshot=lambda name,values:'bound',state=lambda:[])
        ns['service_stops']=run.live.cpu.StopDispatcher(ns)
        exec(ast.get_source_segment(code,node),ns);dispatch=ns['service_stops']
        for label in ('diagnostic','trigger'):
            probe=ns['Probe'](100,label);self.assertTrue(probe.stop());dispatch.drain()
            self.assertFalse(dispatch.failed or dispatch.pending or events or messages)
        ns.update(injected=True,saved=[])
        for label in ('port','diagnostic'):
            probe=ns['Probe'](100,label);self.assertTrue(probe.stop());dispatch.drain()
        self.assertEqual([e[0] for e in events],['fence','diagnostic'])
        self.assertTrue(ns['fenced'] and ns['diagnosed'])
        probe=ns['Probe'](100,'forbidden');self.assertTrue(probe.stop())
        with self.assertRaises(Quit) as caught:dispatch.drain()
        self.assertEqual(str(caught.exception),'quit 71');self.assertTrue(dispatch.failed)
        self.assertIn('TERMINAL_FATAL_OBSERVER_FAIL forbidden',messages[-1])

if __name__=='__main__':unittest.main()
