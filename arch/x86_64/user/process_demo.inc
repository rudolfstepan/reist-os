; Ring-3 demonstration only. No kernel mechanism examines these arguments,
; test case, expected status, private memory or FP witnesses.
%ifndef X86_64_PROCESS_CASE
%define X86_64_PROCESS_CASE 0
%endif
%ifndef X86_64_NATIVE_IPC
%define X86_64_NATIVE_IPC 0
%endif
%if X86_64_NATIVE_IPC
%if X86_64_NATIVE_BULK_IPC
%include "arch/x86_64/user/bulk_ipc_demo.inc"
%else
%include "arch/x86_64/user/ipc_demo.inc"
%endif
%else
process_demo:
    mov r12, rdi
    FP_BEGIN edi
    mov [rel probe_data], r12
    mov r14, 0xBAD00BAD11223344
    xor edi, edi
    xor esi, esi
    xor edx, edx
    xor r10d, r10d
    xor r8d, r8d
    xor r9d, r9d
    mov eax, 22
    syscall
    FP_CHECK
    test eax, eax
    jz process_demo_bad
    mov r13, rax
    ; Explicitly denied authority does not terminate the task.
    mov eax, 49
    syscall
    FP_CHECK
    cmp rax, -13
    jne process_demo_bad
    mov edi, 101 ; invalid bounded sleep, no state mutation
    mov eax, 41
    syscall
    FP_CHECK
    cmp rax, -22
    jne process_demo_bad
    ; Full GPR/FP/private RW preservation across round robin and idle wake.
    mov ebp, 3
.loop:
    xor edi, edi
    mov eax, 40
    syscall
    FP_CHECK
    test rax, rax
    jnz process_demo_bad
    mov edi, 20
    mov eax, 41
    syscall
    FP_CHECK
    test rax, rax
    jnz process_demo_bad
    cmp [rel probe_data], r12
    jne process_demo_bad
    mov rax, 0xBAD00BAD11223344
    cmp r14, rax
    jne process_demo_bad
    xor edi, edi
    mov eax, 22
    syscall
    FP_CHECK
    cmp rax, r13
    jne process_demo_bad
    dec ebp
    jnz .loop
%if X86_64_PROCESS_CASE
    mov eax, r12d
    shr eax, 8
    and eax, 1
    add eax, X86_64_PROCESS_CASE
    and eax, 3
    mov edx, r12d
    and edx, 3
    cmp eax, edx
    jne .normal
    xor edx, edx
%if X86_64_PROCESS_CASE == 1
    ud2
%elif X86_64_PROCESS_CASE == 2
    mov rax, [abs 0x500000]
%elif X86_64_PROCESS_CASE == 3
    xor eax, eax
    div eax
%elif X86_64_PROCESS_CASE == 4 || X86_64_PROCESS_CASE == 6
    pushfq
    or qword [rsp], 0x4000
    popfq
%elif X86_64_PROCESS_CASE == 5 || X86_64_PROCESS_CASE == 7
    mov rsp, 0x500000
%endif
%if X86_64_PROCESS_CASE == 4 || X86_64_PROCESS_CASE == 5
    xor edi, edi
    mov eax, 40
    syscall
%endif
%if X86_64_PROCESS_CASE >= 6
.spin:
    pause
    jmp .spin
%endif
    ud2
%endif
.normal:
    xor edx, edx
    mov eax, r12d
    and eax, 3
    lea rdi, [rel process_demo_status]
    mov edi, [rdi+rax*4]
    mov eax, 9
    syscall
process_demo_bad:
    int3
    ud2
align 4
process_demo_status: dd 0, 42, 0x80000000, 0xFFFFFFFF
%endif
