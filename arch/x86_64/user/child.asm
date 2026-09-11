BITS 64
; Lower 1072 bytes of this task's private stack, disjoint from argv/IPC.
%define FP_STACK_BASE 0x00408000
%ifndef X86_64_BUSY_CHILD
%define X86_64_BUSY_CHILD 0
%endif
%ifndef X86_64_BUSY_INVALID_STACK
%define X86_64_BUSY_INVALID_STACK 0
%endif
%include "arch/x86_64/user/fp_probe.inc"
%ifndef X86_64_FAULT_VECTOR
%define X86_64_FAULT_VECTOR -1
%endif
%ifndef X86_64_FAULT_PHASE
%define X86_64_FAULT_PHASE 0
%endif
%macro FAULT_PROBE 1
%if X86_64_FAULT_VECTOR >= 0 && X86_64_FAULT_PHASE = %1
    jmp child_fault_probe
%endif
%endmacro

REIST_SYS_EXIT equ 9
REIST_SYS_GETPID equ 22
REIST_SYS_YIELD equ 40
REIST_SYS_IPC_SEND equ 50
REIST_SYS_IPC_RECEIVE equ 51
REIST_SYS_IPC_SEND_TIMEOUT equ 53
REIST_SYS_IPC_RELEASE equ 58
REIST_EACCES    equ -13
REIST_EAGAIN    equ -11
REIST_EBADF     equ -9
CHILD_STATUS   equ 77
FAIL_STATUS    equ 78
USER_STACK_TOP equ 0x00409000
CHILD_RSP      equ USER_STACK_TOP - 128
ARGV0_ADDRESS  equ USER_STACK_TOP - 32
ARGV1_ADDRESS  equ USER_STACK_TOP - 16
AT_REIST_IPC_HANDLE equ 0x52534901
IPC_MESSAGE_VERSION equ 1
IPC_MESSAGE_SIZE equ 140
IPC_MESSAGE_LENGTH equ 8
IPC_STACK_BYTES equ 144
IPC_SEND_TIMEOUT_MS equ 10

section .text
global _start

_start:
    FP_BEGIN 0x1b
%if X86_64_BUSY_CHILD
%if X86_64_BUSY_INVALID_STACK
child_cpu_poison_stack:
    xor esp, esp
%endif
    jmp child_cpu_spin
%endif
    FAULT_PROBE 0
    mov eax, REIST_SYS_GETPID
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    jne .fail
    cmp rsp, CHILD_RSP
    jne .fail
    test rsp, 15
    jnz .fail
    cmp qword [rsp], 2
    jne .fail
    cmp qword [rsp + 8], ARGV0_ADDRESS
    jne .fail
    cmp qword [rsp + 16], ARGV1_ADDRESS
    jne .fail
    cmp qword [rsp + 24], 0
    jne .fail
    cmp qword [rsp + 32], 0
    jne .fail
    cmp qword [rsp + 40], AT_REIST_IPC_HANDLE
    jne .fail
    mov r12, qword [rsp + 48]
    test r12, r12
    jz .fail
    cmp qword [rsp + 56], 0
    jne .fail
    cmp qword [rsp + 64], 0
    jne .fail
    mov rsi, qword [rsp + 8]
    mov rax, 0x632F6C6C6568732F
    cmp qword [rsi], rax
    jne .fail
    cmp dword [rsi + 8], 0x646C6968
    jne .fail
    cmp byte [rsi + 12], 0
    jne .fail
    mov rsi, qword [rsp + 16]
    mov rax, 0x0037376E656B6F74
    cmp qword [rsi], rax
    jne .fail
    sub rsp, IPC_STACK_BYTES
    cld
    mov rdi, rsp
    xor eax, eax
    mov ecx, IPC_STACK_BYTES / 8
    rep stosq
    mov dword [rsp], IPC_MESSAGE_VERSION
    mov dword [rsp + 4], IPC_MESSAGE_SIZE
    mov dword [rsp + 8], IPC_MESSAGE_LENGTH
    mov rax, 0x0036376E656B6F74
    mov qword [rsp + 12], rax
    mov eax, REIST_SYS_IPC_RECEIVE
    mov rdi, r12
    mov rsi, rsp
    xor edx, edx
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    jne .fail
    mov eax, REIST_SYS_IPC_SEND
    mov rdi, r12
    mov rsi, rsp
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov byte [rsp + 18], '7'
    FAULT_PROBE 1
    mov eax, REIST_SYS_IPC_SEND
    mov rdi, r12
    mov rsi, rsp
    xor edx, edx
    syscall
    FP_CHECK
    cmp rax, REIST_EAGAIN
    jne .fail
    mov eax, REIST_SYS_IPC_SEND_TIMEOUT
    mov rdi, r12
    mov rsi, rsp
    mov edx, IPC_SEND_TIMEOUT_MS
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov eax, REIST_SYS_YIELD
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov eax, REIST_SYS_YIELD
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    FAULT_PROBE 2
    mov eax, REIST_SYS_IPC_SEND
    mov rdi, r12
    mov rsi, rsp
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov eax, REIST_SYS_YIELD
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov eax, REIST_SYS_IPC_RELEASE
    mov rdi, r12
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov eax, REIST_SYS_YIELD
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    mov byte [rsp + 18], '9'
    mov eax, REIST_SYS_IPC_SEND_TIMEOUT
    mov rdi, r12
    mov rsi, rsp
    mov edx, IPC_SEND_TIMEOUT_MS
    syscall
    FP_CHECK
    cmp rax, REIST_EBADF
    jne .fail
    mov edi, CHILD_STATUS
    FAULT_PROBE 3
    jmp .exit
.fail:
    mov edi, FAIL_STATUS
.exit:
    mov eax, REIST_SYS_EXIT
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    ud2

child_fault_probe:
%if X86_64_FAULT_VECTOR = 0
    xor edx, edx
    xor eax, eax
child_fault_instruction:
    div eax
%elif X86_64_FAULT_VECTOR = 3
child_fault_instruction:
    int3
%elif X86_64_FAULT_VECTOR = 6
child_fault_instruction:
    ud2
%elif X86_64_FAULT_VECTOR = 13
child_fault_instruction:
    mov rax, cr0
%elif X86_64_FAULT_VECTOR = 14
    xor eax, eax
child_fault_instruction:
    mov byte [rax], 1
%elif X86_64_FAULT_VECTOR = 16
    fninit
    mov word [abs FP_STACK_BASE], 0x037e
    fldcw [abs FP_STACK_BASE]
    fldz
    fldz
    fdivp st1, st0
child_fault_instruction:
    fwait
%endif
    ; Reaching this means the expected exception did not occur: no fallback.
    mov edi, FAIL_STATUS
    mov eax, REIST_SYS_EXIT
    syscall
    FP_CHECK
    ud2

%if X86_64_BUSY_CHILD
child_cpu_spin:
    pause
    jmp short child_cpu_spin
child_cpu_spin_end:
%endif
FP_PROBE_CODE
section .note.GNU-stack noalloc noexec nowrite progbits
