"""Execute the actual completion authority and private dispatch adapter."""
from pathlib import Path
import unittest
import test_x86_64_task_frames as host
ROOT=Path(__file__).resolve().parents[1]

class CompletionTests(unittest.TestCase):
    def test_actual_completion_and_adapter(self):
        body=(ROOT/'arch/x86_64/proc/process_ipc.inc').read_text()
        self.assertIn('process_ipc_completion_apply64:',body)
        self.assertEqual(body.count('    pushfq'),1)
        asm='''BITS 64
%define REIST_NATIVE_RUNTIME
%define C_NATIVE_IPC_ENTRY fake_ipc
TASK_STATE equ 0
TASK_GENERATION equ 8
TASK_RAX equ 232
TASK_BLOCKED equ 6
TASK_READY equ 1
PF_R equ 4
PF_W equ 2
extern fake_ipc
section .data
global scheduler_current_slot,scheduler_tasks,process_run_generations
global scheduler_deadline_entries,host_counters,host_result
global syscall_rax,syscall_rdi,syscall_rsi,syscall_rdx
global host_flags
host_flags: dq 0
scheduler_current_slot: dq 0
scheduler_last_tick: dq 10
scheduler_tasks: times 128 dq 0
process_run_generations: times 4 dd 0
scheduler_deadline_entries: times 8 dq 0
host_counters: times 4 dq 0
host_result: dq 0
saved_rsp: dq 0
syscall_rax: dq 0
syscall_rdi: dq 0
syscall_rsi: dq 0
syscall_rdx: dq 0
syscall_r10: dq 0
syscall_r8: dq 0
syscall_r9: dq 0
section .text
global host_adapter,process_ipc_completion_apply64,process_ipc_completions
; kind0 take,1 service,2 syscall; following args operation,slot,generation.
host_adapter:
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    mov [rel saved_rsp],rsp
    mov r10,rdi
    mov edi,esi
    mov esi,edx
    mov rdx,rcx
    mov [rel scheduler_current_slot],esi
    mov eax,esi
    shl eax,8
    lea r11,[rel scheduler_tasks]
    add r11,rax
    mov r12,r11
    cmp r10,1
    je .service
    cmp r10,2
    je process_ipc_syscall64
    call process_ipc_take64
    jmp host_success
.service:
    call process_ipc_service64
    jmp host_success
process_run_resume64:
    mov [rel host_result],rax
process_run_dispatch64:
host_success:
    mov eax,1
    jmp host_return
process_run_syscall64.invalid:
scheduler_fail:
    xor eax,eax
host_return:
    mov rsp,[rel saved_rsp]
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
scheduler_queue_apply64:
    inc qword [rel host_counters]
    mov eax,1
    ret
scheduler_runqueue_enqueue64:
    inc qword [rel host_counters+8]
    mov eax,1
    ret
scheduler_validate_shell_range64:
scheduler_validate_shell_ipc_buffer64:
    inc qword [rel host_counters+16]
    mov eax,1
    ret
scheduler_save_syscall_context64:
    ret
'''+body.replace('    pushfq','    push qword [rel host_flags]') # Model flags only; actual IF check executes.
        host.TaskFrameTests().build(asm,ROOT/'test/x86_64_ipc_completion_host.c','IPC_COMPLETION_HOST')

if __name__=='__main__':unittest.main()
