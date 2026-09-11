"""Execute the actual Ring-3 retry code with bounded syscall-result sequences.

Only SYSCALL/FP probes are substituted; no copied retry implementation.
The unchanged real IPC guest gate must still prove its original interleavings.
"""
from pathlib import Path
import os, subprocess, sys, unittest, uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class FixtureTests(unittest.TestCase):
    def test_actual_child_retry(self):
        source = (ROOT / 'arch/x86_64/user/child.asm').read_text()
        body = source.split('    mov r13d, 8 ; bounded fixture-only', 1)[1]
        body = body[body.index('\n'):].split('    mov edi, CHILD_STATUS', 1)[0]
        asm = '''BITS 64
REIST_SYS_IPC_SEND_TIMEOUT equ 53
REIST_SYS_YIELD equ 40
REIST_EACCES equ -13
REIST_EBADF equ -9
REIST_ETIMEDOUT equ -110
IPC_SEND_TIMEOUT_MS equ 10
%macro FP_CHECK 0
%endmacro
section .text
global run_child
extern mock_send
extern mock_yield
run_child:
    push r12
    push r13
    sub rsp, 8
    mov r12, 0x101
    mov r13d, 8
'''+body.replace('    syscall', '    call test_syscall')+'''
    mov eax, 1
    jmp .done
.fail:
    xor eax, eax
.done:
    add rsp, 8
    pop r13
    pop r12
    ret
test_syscall:
    cmp eax, 53
    je mock_send
    cmp eax, 40
    je mock_yield
    ud2
'''
        c = r'''
#include <stdio.h>
#include <stdint.h>
#define ABI __attribute__((sysv_abi))
extern int ABI run_child(void);
static int count, position, yields, bad;
static long long values[8], yield_result;
long long ABI mock_send(uint64_t handle, void *message, uint64_t ms) {
    if(handle!=0x101 || !message || ms!=10 || position>=count) {
        bad=1; return -999;
    }
    return values[position++];
}
long long ABI mock_yield(void) { ++yields; return yield_result; }
int main(void) {
    for(int prefix=0;prefix<8;prefix++) for(int mask=0;mask<(1<<prefix);mask++) {
        for(int i=0;i<prefix;i++) values[i]=(mask&(1<<i))?-13:-110;
        values[prefix]=-9;count=prefix+1;position=yields=bad=0;yield_result=0;
        if(run_child()!=1 || bad || position!=count || yields!=prefix) return 1;
    }
    const long long terminal[]={0,-11,-32,-14,-22,1,0x100000000LL};
    for(unsigned i=0;i<sizeof(terminal)/sizeof(*terminal);i++) {
        values[0]=terminal[i];count=1;position=yields=bad=0;
        if(run_child()!=0 || bad || position!=1 || yields!=0) return 2;
    }
    for(int denied=0;denied<2;denied++) {
        for(int i=0;i<8;i++) values[i]=denied?-13:-110;
        count=8;position=yields=bad=0;
        if(run_child()!=0 || bad || position!=8 || yields!=7) return 3;
    }
    values[0]=-110;count=1;position=yields=bad=0;yield_result=-22;
    if(run_child()!=0 || bad || position!=1 || yields!=1) return 4;
    puts("IPC_CHILD_RETRY_OK"); return 0;
}
'''
        self.compile_run(asm, c, 'IPC_CHILD_RETRY_OK')

    def test_actual_parent_retry(self):
        source = (ROOT / 'arch/x86_64/user/shell.c').read_text()
        start = source.index('static shell_i64 ipc_receive_peer(')
        body = source[start:source.index('\n}\n', start)+3]
        c = r'''
#include <stdio.h>
typedef unsigned long long shell_u64;
typedef long long shell_i64;
typedef unsigned int shell_u32;
typedef struct { unsigned char data[140]; } shell_ipc_message_t;
#define REIST_ETIMEDOUT (-110LL)
#define REIST_X64_SYS_IPC_RECEIVE_TIMEOUT 54
#define IPC_RECEIVE_TIMEOUT_MS 10ULL
static int count,position,bad;
static shell_i64 values[8];
static shell_ipc_message_t message;
static shell_i64 reist_x64_syscall3(shell_u64 op,shell_u64 handle,shell_u64 ptr,shell_u64 ms) {
    if(op!=54 || handle!=0x101 || ptr!=(shell_u64)&message || ms!=10 || position>=count) {
        bad=1; return -999;
    }
    return values[position++];
}
'''+body+r'''
int main(void) {
    const shell_i64 terminal[]={0,-9,-13,-11,-32,-14,-22,1,0x100000000LL};
    for(int prefix=0;prefix<8;prefix++) for(unsigned t=0;t<sizeof(terminal)/sizeof(*terminal);t++) {
        for(int i=0;i<prefix;i++) values[i]=-110;
        values[prefix]=terminal[t];count=prefix+1;position=bad=0;
        if(ipc_receive_peer(0x101,&message)!=terminal[t] || bad || position!=count) return 1;
    }
    for(int i=0;i<8;i++) values[i]=-110;
    count=8;position=bad=0;
    if(ipc_receive_peer(0x101,&message)!=-110 || bad || position!=8) return 2;
    puts("IPC_PARENT_RETRY_OK"); return 0;
}
'''
        self.compile_run(None, c, 'IPC_PARENT_RETRY_OK')

    def compile_run(self, asm, c, marker):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83o-mappings'/('ipc-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,label):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=60,
                capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2000:])
            return r.stdout
        objects=[]
        if asm:
            (folder/'retry.asm').write_text(asm,encoding='ascii')
            obj=folder/'retry.o'
            run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',folder/'retry.asm','-o',obj],'assemble')
            objects.append(obj)
        (folder/'retry.c').write_text(c,encoding='ascii')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                 '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                 folder/'retry.c',*objects,'-o',exe],opt+'-build')
            self.assertIn(marker,run([exe],opt+'-run'))


if __name__=='__main__': unittest.main()
