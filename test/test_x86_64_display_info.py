"""Execute the production display core and syscall copy path on host."""
from pathlib import Path
import json, os, subprocess, sys, unittest, uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class DisplayInfoTests(unittest.TestCase):
    def test_projection_and_geometry_replay_rejects_mutations(self):
        import verify_x86_64_display_info as v
        self.assertTrue(v.projection())
        folder=v.BASE/('host-geometry-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        for width,height in ((1024,768),(800,600)):
            raw=(f'DISPLAY_INFO_{width}\n'*3).encode()
            row={'snapshots':[{'proof':dict(width=width,height=height)} for _ in range(8)]}
            (folder/'guest.log').write_bytes(raw);(folder/'result.json').write_text(json.dumps(row))
            self.assertEqual(v.geometry(folder,width)['self_tests'],3)
            for bad in (raw[:-1],raw+f'DISPLAY_INFO_{width}\n'.encode(),raw.replace(b'INFO_',b'INFO_9',1)):
                (folder/'guest.log').write_bytes(bad)
                with self.assertRaises(ValueError):v.geometry(folder,width)
            (folder/'guest.log').write_bytes(raw);row['snapshots'][3]['proof']['height']+=1
            (folder/'result.json').write_text(json.dumps(row))
            with self.assertRaises(ValueError):v.geometry(folder,width)

    def test_actual_syscall_and_core(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83cc-display-info'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        domain=(ROOT/'arch/x86_64/video/display_domain.inc').read_text()
        body=domain[domain.index('global native_display_user_tile_range64'):domain.index('native_display_terminal64:')]
        asm='''BITS 64
default rel
%define PF_R 4
%define PF_W 2
%define TASK_GENERATION 0
%define TASK_STATE 8
%define TASK_FREE 0
%define TASK_READY 1
%define TASK_BLOCKED 2
%define NATIVE_TASK_SHIFT 10
section .text
%include "arch/x86_64/video/display_core.inc"
extern display_validate_backend
global display_invoke
display_invoke:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    sub rsp,8
    mov [syscall_rsi],rdi
    lea r12,[fake_task]
    call native_display_syscall64
    add rsp,8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret
native_display_boot_admit64:
    mov eax,[native_display_boot+8]
    mov [native_display_pitch],rax
    xor eax,eax
    ret
native_display_leaf64:
scheduler_fail:
    ud2
process_run_resume64:
    ret
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
'''+body+'''
section .data
global native_display_boot, scheduler_current_slot, fake_task
native_display_boot: dq 1
    dd 4096,1024,768,0
    dq 0xe0000000
scheduler_current_slot: dq 4
scheduler_last_tick: dq 10
fake_task: dq 7,1
section .bss
alignb 8
global native_display_state,native_display_request,native_display_commits
native_display_state: resb 128
native_display_request: resb 64
native_display_tile: resb 16384
native_display_tile_bytes: resq 1
native_display_pitch: resq 1
native_display_commits: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
scheduler_tasks: resb 8192
family_records: resb 512
'''
        def run(cmd,label):
            r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=40,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(r.stdout+r.stderr)
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:])
        for enabled in (0,1):
            source=folder/('adapter'+str(enabled)+'.asm');obj=source.with_suffix('.o')
            source.write_text(('%define REIST_NATIVE_DISPLAY_INFO 1\n' if enabled else '')+asm)
            run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',source,'-o',obj],'asm'+str(enabled))
            for level in (0,2):
                tag=f'{enabled}-{level}';exe=folder/(tag+'.exe')
                run([find_zig(),'cc','-target','x86_64-windows-gnu','-O'+str(level),'-Wall','-Wextra','-Werror',
                    '-I.','-DEXPECT_INFO='+str(enabled),'test/x86_64_display_info_host.c',obj,'-o',exe],'cc'+tag)
                run([exe],'run'+tag)

if __name__=='__main__':unittest.main()
