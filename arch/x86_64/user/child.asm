BITS 64
%ifndef X86_64_MAPPING_CASE
%define X86_64_MAPPING_CASE 0
%endif
%ifndef X86_64_PROFILE_CASE
%define X86_64_PROFILE_CASE 0
%endif
%ifndef X86_64_IPC_CASE
%define X86_64_IPC_CASE 0
%endif
%ifndef X86_64_ARGV_CASE
%define X86_64_ARGV_CASE 0
%endif
%ifndef X86_64_EXIT_STATUS
%define X86_64_EXIT_STATUS -1
%endif
%ifndef X86_64_CONTEXT_CASE
%define X86_64_CONTEXT_CASE 0
%endif
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
%if X86_64_EXIT_STATUS >= 0 && X86_64_FAULT_PHASE = %1
    jmp child_exit_probe
%endif
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
REIST_ETIMEDOUT equ -110
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
%if X86_64_MAPPING_CASE
    call child_mapping_probe
%if X86_64_MAPPING_CASE >= 2
    ud2 ; no fault means the mapping failed to enforce its protection
%endif
%endif
%if X86_64_PROFILE_CASE
    xor r14d, r14d
    mov r15, (1<<9)|(1<<40)|(1<<50)|(1<<51)|(1<<53)|(1<<58)
.profile_numbers:
    bt r15, r14
    jc .profile_next
    mov rax, r14
    mov rdi, -1
    mov rsi, -1
    mov rdx, -1
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    jne .profile_bad
.profile_next:
    inc r14d
    cmp r14d, 64
    jb .profile_numbers
    mov rax, 0x100000000
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    jne .profile_bad
    mov rax, -1
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    jne .profile_bad
    jmp .profile_done
.profile_bad:
    ud2
.profile_done:
%endif
%if X86_64_IPC_CASE
    jmp child_ipc_handoff
%endif
%if X86_64_ARGV_CASE
    jmp child_argv_probe
%endif
%if X86_64_CONTEXT_CASE
    jmp child_context_probe
%endif
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
    mov r13d, 8 ; bounded fixture-only admission attempts, no implicit grant
.revocation_send:
    mov eax, REIST_SYS_IPC_SEND_TIMEOUT
    mov rdi, r12
    mov rsi, rsp
    mov edx, IPC_SEND_TIMEOUT_MS
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    je .revocation_retry
    cmp rax, REIST_ETIMEDOUT
    jne .revocation_reply
.revocation_retry:
    ; Deadline expiry does not revoke SEND. Observe CLOSE on another bounded
    ; attempt, giving the owner time to run; never interpret timeout as success.
    dec r13d
    jz .fail
    mov eax, REIST_SYS_YIELD
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz .fail
    jmp .revocation_send
.revocation_reply:
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

%if X86_64_IPC_CASE
child_ipc_handoff:
    cmp rsp, CHILD_RSP
    jne .bad
    cmp qword [rsp+40], AT_REIST_IPC_HANDLE
    jne .bad
    mov r12, [rsp+48]
%if X86_64_IPC_CASE = 2
    mov eax, REIST_SYS_YIELD
    syscall
    FP_CHECK
%endif
    sub rsp, IPC_STACK_BYTES
    mov dword [rsp], 1
    mov dword [rsp+4], 140
    mov dword [rsp+8], 128
    lea rdi, [rsp+12]
    mov ecx, 128
    mov al, 0x5a
    cld
    rep stosb
    mov r14d, 8
child_ipc_initial_send_retry:
    mov eax, REIST_SYS_IPC_SEND_TIMEOUT
    mov rdi, r12
    mov rsi, rsp
    mov edx, 10
child_ipc_first_send:
    syscall
    FP_CHECK
    cmp rax, REIST_EACCES
    jne child_ipc_initial_send_result
    ; SPAWN publishes READY before the parent can delegate SEND. The denial
    ; is authoritative; yield within a fixed fixture budget, never gain rights.
    dec r14d
    jz child_ipc_handoff.bad
    mov eax, REIST_SYS_YIELD
    syscall
    FP_CHECK
    test rax, rax
    jnz child_ipc_handoff.bad
    jmp child_ipc_initial_send_retry
child_ipc_initial_send_result:
%if X86_64_IPC_CASE = 3
    cmp rax, REIST_EBADF
    je child_ipc_handoff.exit
%endif
    test rax, rax
    jnz child_ipc_handoff.bad
%if X86_64_IPC_CASE = 2
    mov eax, REIST_SYS_YIELD
    syscall
    FP_CHECK
%endif
    lea rdi, [rsp+12]
    mov ecx, 128
    mov al, 0x5b
    rep stosb
    mov eax, REIST_SYS_IPC_SEND_TIMEOUT
    mov rdi, r12
    mov rsi, rsp
    mov edx, 10
child_ipc_second_send:
    syscall
    FP_CHECK
%if X86_64_IPC_CASE = 3
    cmp rax, REIST_EBADF
    jne child_ipc_handoff.bad
%else
    test rax, rax
    jnz child_ipc_handoff.bad
%if X86_64_PROFILE_CASE
    ; The parent closes after verifying both payloads. Do not RELEASE a queued
    ; payload before that acknowledgement. A third bounded send observes CLOSE.
    mov r14d, 8
child_profile_close_wait:
    mov eax, REIST_SYS_IPC_SEND_TIMEOUT
    mov rdi, r12
    mov rsi, rsp
    mov edx, 10
    syscall
    FP_CHECK
    cmp rax, REIST_EBADF
    je child_ipc_handoff.exit
    test rax, rax
    jz child_profile_close_yield
    cmp rax, -110
    jne child_ipc_handoff.bad
child_profile_close_yield:
    dec r14d
    jz child_ipc_handoff.bad
    mov eax, REIST_SYS_YIELD
    syscall
    FP_CHECK
    test rax, rax
    jnz child_ipc_handoff.bad
    jmp child_profile_close_wait
%else
    mov eax, REIST_SYS_IPC_RELEASE
    mov rdi, r12
    xor esi, esi
    xor edx, edx
    syscall
    FP_CHECK
    test rax, rax
    jnz child_ipc_handoff.bad
%endif
%endif
child_ipc_handoff.exit:
    mov edi, 90 + X86_64_IPC_CASE
    mov eax, REIST_SYS_EXIT
    syscall
    ud2
child_ipc_handoff.bad:
    ud2
%endif

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
%if X86_64_CONTEXT_CASE
child_context_probe:
%if X86_64_CONTEXT_CASE = 1
    xor esp, esp
%elif X86_64_CONTEXT_CASE = 2 || X86_64_CONTEXT_CASE = 3
    mov rsp, 0x0000800000000000
%else
    pushfq
%if X86_64_CONTEXT_CASE = 4
    or qword [rsp], 0x240400 ; AC, ID and DF, without IOPL authority
%elif X86_64_CONTEXT_CASE = 7
    or qword [rsp], 0x100 ; actual single-step exception
%else
    or qword [rsp], 0x4000 ; user can set NT, unsafe for IRETQ
%endif
    popfq
%endif
%if X86_64_CONTEXT_CASE = 7
child_context_fault:
    nop
child_context_resume:
    ud2
%elif X86_64_CONTEXT_CASE = 3 || X86_64_CONTEXT_CASE = 6
child_context_spin:
    pause
    jmp short child_context_spin
child_context_spin_end:
%else
    mov eax, REIST_SYS_GETPID
child_context_fault:
    syscall
child_context_resume:
%if X86_64_CONTEXT_CASE = 4
    pushfq
    pop rdx
    cmp rax, REIST_EACCES
    jne child_context_fail
    and edx, 0x240400
    cmp edx, 0x240400
    jne child_context_fail
    mov eax, REIST_SYS_YIELD
    xor edi, edi
    xor esi, esi
    xor edx, edx
    syscall
    test rax, rax
    jnz child_context_fail
child_context_spin:
    ; Check after every possible IRQ return, including an interrupted PUSHFQ.
    pushfq
    pop rdx
    and edx, 0x240400
    cmp edx, 0x240400
    jne child_context_fail
    pause
    jmp short child_context_spin
child_context_spin_end:
%endif
%endif
child_context_fail:
    ud2
%endif
%if X86_64_EXIT_STATUS >= 0
child_exit_probe:
    ; A rejected wide status is resumable, not truncated or terminal.
    mov rdi, 0x10000004d
    mov eax, REIST_SYS_EXIT
    syscall
    cmp rax, -22
    jne child_exit_fail
    ; YIELD is independent of IPC phase and unused argument registers.
    mov rdi, 0xfedcba9876543210
    mov rsi, 0x1111222233334444
    mov rdx, 0x5555666677778888
    mov eax, REIST_SYS_YIELD
    syscall
    test rax, rax
    jnz child_exit_fail
    mov edi, X86_64_EXIT_STATUS
    mov eax, REIST_SYS_EXIT
child_exit_instruction:
    syscall
child_exit_return:
child_exit_fail:
    ud2
%endif
%if X86_64_ARGV_CASE
%if X86_64_ARGV_CASE = 1
%define START_ARGC 0
%define START_BYTES 96
%elif X86_64_ARGV_CASE = 2
%define START_ARGC 3
%define START_BYTES 144
%elif X86_64_ARGV_CASE = 3
%define START_ARGC 8
%define START_BYTES 1152
%else
%define START_ARGC 2
%define START_BYTES 128
%endif
child_argv_probe:
    cmp rsp, USER_STACK_TOP - START_BYTES
    jne child_argv_fail
    test rsp, 15
    jnz child_argv_fail
    cmp qword [rsp], START_ARGC
    jne child_argv_fail
    cmp qword [rsp + (START_ARGC + 1)*8], 0
    jne child_argv_fail
    cmp qword [rsp + (START_ARGC + 2)*8], 0
    jne child_argv_fail
    cmp qword [rsp + (START_ARGC + 3)*8], AT_REIST_IPC_HANDLE
    jne child_argv_fail
    mov rax, [rsp + (START_ARGC + 4)*8]
    cmp rax, 0x101
    je .handle_ok
    cmp rax, 0x201
    jne child_argv_fail
.handle_ok:
    cmp qword [rsp + (START_ARGC + 5)*8], 0
    jne child_argv_fail
    cmp qword [rsp + (START_ARGC + 6)*8], 0
    jne child_argv_fail
%if X86_64_ARGV_CASE = 2
    cmp qword [rsp + 8], USER_STACK_TOP - 48
    jne child_argv_fail
    cmp dword [abs USER_STACK_TOP - 48], 0x72746e65
    jne child_argv_fail
    cmp word [abs USER_STACK_TOP - 44], 0x0079
    jne child_argv_fail
    cmp qword [rsp + 16], USER_STACK_TOP - 32
    jne child_argv_fail
    cmp byte [abs USER_STACK_TOP - 32], 0
    jne child_argv_fail
    cmp qword [rsp + 24], USER_STACK_TOP - 16
    jne child_argv_fail
    cmp dword [abs USER_STACK_TOP - 16], 0xa9cea4c3
    jne child_argv_fail
    cmp byte [abs USER_STACK_TOP - 12], 0
    jne child_argv_fail
%elif X86_64_ARGV_CASE = 3
    xor r10d, r10d
.argument:
    mov rax, r10
    shl rax, 7
    add rax, USER_STACK_TOP - 1024
    cmp [rsp + 8 + r10*8], rax
    jne child_argv_fail
    mov edx, 'A'
    add edx, r10d
    xor r11d, r11d
.byte:
    cmp byte [rax + r11], dl
    jne child_argv_fail
    inc r11d
    cmp r11d, 127
    jb .byte
    cmp byte [rax + 127], 0
    jne child_argv_fail
    inc r10d
    cmp r10d, 8
    jb .argument
%elif X86_64_ARGV_CASE = 4
    cmp qword [rsp + 8], USER_STACK_TOP - 32
    jne child_argv_fail
    cmp qword [rsp + 16], USER_STACK_TOP - 16
    jne child_argv_fail
    mov rax, 0x632f6c6c6568732f
    cmp qword [abs USER_STACK_TOP - 32], rax
    jne child_argv_fail
    cmp dword [abs USER_STACK_TOP - 24], 0x646c6968
    jne child_argv_fail
    cmp byte [abs USER_STACK_TOP - 20], 0
    jne child_argv_fail
    mov rax, 0x0037376e656b6f74
    cmp qword [abs USER_STACK_TOP - 16], rax
    jne child_argv_fail
%endif
    mov edi, 90 + X86_64_ARGV_CASE
    mov eax, REIST_SYS_EXIT
child_argv_exit_instruction:
    syscall
child_argv_exit_return:
child_argv_fail:
    ud2
%endif
FP_PROBE_CODE
%if X86_64_MAPPING_CASE
child_mapping_probe:
    mov rax, 0x4e58524f444154c3
    cmp [rel child_mapping_readonly], rax
    jne .bad
%if X86_64_MAPPING_CASE = 2
child_mapping_write_instruction:
    mov byte [rel child_mapping_readonly], 0x90
    ud2
%elif X86_64_MAPPING_CASE = 3
    lea rax, [rel child_mapping_readonly]
child_mapping_execute_instruction:
    jmp rax
%else
    ret
%endif
child_mapping_probe.bad:
    ud2
section .rodata align=4096
child_mapping_readonly:
    dq 0x4e58524f444154c3 ; starts with RET, but must never be fetched from R/NX
%endif
section .note.GNU-stack noalloc noexec nowrite progbits
