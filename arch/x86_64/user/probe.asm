; Freestanding ELF64 ET_EXEC fixture built by the normal x86_64 toolchain.
; R8.1e validates and stages this image. R8.1f executes modes 0 and 1;
; R8.1g executes the isolated cooperative task modes 0x0A and 0x0B.

BITS 64
%include "arch/x86_64/user/fp_probe.inc"

section .text
global _start
_start:
    cmp edi, 0x0a
    jb .early_integer_probe
    FP_BEGIN edi
.early_integer_probe:
    push rdi
    pop rdi
    test edi, edi
    jz probe_exit
    cmp edi, 1
    je probe_fault
    cmp edi, 0x0A
    je scheduler_task_a
    cmp edi, 0x0B
    je scheduler_task_b
    cmp edi, 0x0C
    je preempt_task_a
    cmp edi, 0x0D
    je preempt_task_b
    cmp edi, 0x0E
    je quantum_task_a
    cmp edi, 0x0F
    je quantum_task_b
    cmp edi, 0x10
    je runqueue_task_0
    cmp edi, 0x11
    je runqueue_task_1
    cmp edi, 0x12
    je runqueue_task_2
    cmp edi, 0x13
    je runqueue_task_3
    cmp edi, 0x14
    je sleep_task_0
    cmp edi, 0x15
    je sleep_task_1
    cmp edi, 0x16
    je sleep_task_2
    cmp edi, 0x17
    je sleep_task_3
    cmp edi, 0x18
    je dynamic_parent
    cmp edi, 0x19
    je dynamic_child
    int3

probe_exit:
    mov eax, 9
    mov edi, 100
    syscall
    FP_CHECK
    ud2

probe_fault:
    ud2

scheduler_task_a:
    mov rax, 0xA11A11A11A11A11A
    mov qword [rel probe_data], rax
    mov eax, 40
    syscall
    FP_CHECK
    mov rax, 0xA11A11A11A11A11A
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
    mov eax, 40
    syscall
    FP_CHECK
    mov rax, 0xA11A11A11A11A11A
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 101
    syscall
    FP_CHECK
    ud2

scheduler_task_b:
    mov rax, 0xB22B22B22B22B22B
    mov qword [rel probe_data], rax
    mov eax, 40
    syscall
    FP_CHECK
    mov rax, 0xB22B22B22B22B22B
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
scheduler_fault:
    ud2

scheduler_isolation_failure:
    int3

preempt_task_a:
    mov rax, 0xC33C33C33C33C33C
    mov qword [rel probe_data], rax
    mov eax, 40
    syscall
    FP_CHECK
    mov rax, 0xC33C33C33C33C33C
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 102
    syscall
    FP_CHECK
    ud2

preempt_task_b:
    sub rsp, 64
    mov rbx, rdx
.bounded_cpu_loop:
    pause
    rdtsc
    shl rdx, 32
    mov eax, eax
    or rax, rdx
    cmp rax, rbx
    jb .bounded_cpu_loop
    int3

quantum_task_a:
    sub rsp, 64
    mov r14, 0xE44E44E44E44E44E
    mov r13, r14
    mov qword [rel probe_data], r14
    xor r15d, r15d
    mov qword [rsp], r14
    mov qword [rsp + 56], r13
.quantum_a_loop:
    FP_CHECK
    push r14
    pop rax
    cmp rax, r14
    jne scheduler_isolation_failure
    cmp qword [rsp], r14
    jne scheduler_isolation_failure
    cmp qword [rsp + 56], r13
    jne scheduler_isolation_failure
    cmp r14, r13
    jne scheduler_isolation_failure
    inc qword [rel probe_progress]
    test r15, r15
    jnz .quantum_a_complete
    rdtsc
    shl rdx, 32
    mov eax, eax
    or rax, rdx
    cmp rax, rbx
    jb .quantum_a_loop
    int3
.quantum_a_complete:
    mov rax, 0xE44E44E44E44E44E
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
    cmp qword [rel probe_progress], 1
    jbe scheduler_isolation_failure
    mov eax, 9
    mov edi, 103
    syscall
    FP_CHECK
    ud2

quantum_task_b:
    sub rsp, 64
    mov r14, 0xF55F55F55F55F55F
    mov r13, r14
    mov qword [rel probe_data], r14
    mov qword [rsp], r14
    mov qword [rsp + 56], r13
.quantum_b_loop:
    FP_CHECK
    push r14
    pop rax
    cmp rax, r14
    jne scheduler_isolation_failure
    cmp qword [rsp], r14
    jne scheduler_isolation_failure
    cmp qword [rsp + 56], r13
    jne scheduler_isolation_failure
    cmp r14, r13
    jne scheduler_isolation_failure
    inc qword [rel probe_progress]
    rdtsc
    shl rdx, 32
    mov eax, eax
    or rax, rdx
    cmp rax, rbx
    jb .quantum_b_loop
    int3

runqueue_task_0:
    mov rax, 0x1010101010101010
    mov qword [rel probe_data], rax
    mov eax, 40
    syscall
    FP_CHECK
    mov rax, 0x1010101010101010
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 110
    syscall
    FP_CHECK
    ud2

runqueue_task_1:
    mov rax, 0x1111111111111111
    mov qword [rel probe_data], rax
    mov eax, 9
    mov edi, 111
    syscall
    FP_CHECK
    ud2

runqueue_task_2:
    mov rax, 0x1212121212121212
    mov qword [rel probe_data], rax
    mov eax, 40
    syscall
    FP_CHECK
    mov rax, 0x1212121212121212
    cmp qword [rel probe_data], rax
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 112
    syscall
    FP_CHECK
    ud2

runqueue_task_3:
    mov rax, 0x1313131313131313
    mov qword [rel probe_data], rax
runqueue_fault:
    int3
    ud2

sleep_task_0:
    mov rbx, 0x1414141414141414
    mov qword [rel probe_data], rbx
    mov eax, 41
    mov edi, 30
    syscall
    FP_CHECK
    cmp qword [rel probe_data], rbx
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 120
    syscall
    FP_CHECK
    ud2

sleep_task_1:
    mov rbx, 0x1515151515151515
    mov qword [rel probe_data], rbx
    mov eax, 41
    mov edi, 10
    syscall
    FP_CHECK
    cmp qword [rel probe_data], rbx
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 121
    syscall
    FP_CHECK
    ud2

sleep_task_2:
    mov rbx, 0x1616161616161616
    mov qword [rel probe_data], rbx
    mov eax, 41
    mov edi, 20
    syscall
    FP_CHECK
    cmp qword [rel probe_data], rbx
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 122
    syscall
    FP_CHECK
    ud2

sleep_task_3:
    mov rbx, 0x1717171717171717
    mov qword [rel probe_data], rbx
    mov eax, 42
    syscall
    FP_CHECK
    cmp rax, 80
    ja scheduler_isolation_failure
    mov qword [rel probe_progress], rax
    cmp qword [rel probe_data], rbx
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 123
    syscall
    FP_CHECK
    ud2

dynamic_parent:
    mov rbx, 0x1818181818181818
    mov qword [rel probe_data], rbx
    mov eax, 22
    syscall
    FP_CHECK
    cmp rax, 200
    jne scheduler_isolation_failure

    mov eax, 23
    xor edi, edi
    syscall
    FP_CHECK
    cmp rax, -14
    jne scheduler_isolation_failure

    mov eax, 23
    lea rdi, [rel dynamic_child_path]
    syscall
    FP_CHECK
    cmp rax, 201
    jne scheduler_isolation_failure
    mov r14, rax

    mov eax, 23
    lea rdi, [rel dynamic_child_path]
    syscall
    FP_CHECK
    cmp rax, -16
    jne scheduler_isolation_failure

    mov eax, 24
    mov edi, 202
    lea rsi, [rel dynamic_wait_status]
    syscall
    FP_CHECK
    cmp rax, -10
    jne scheduler_isolation_failure

    mov eax, 24
    mov rdi, r14
    xor esi, esi
    syscall
    FP_CHECK
    cmp rax, -14
    jne scheduler_isolation_failure

    mov eax, 24
    mov rdi, r14
    lea rsi, [rel dynamic_wait_status]
    syscall
    FP_CHECK
    cmp rax, 201
    jne scheduler_isolation_failure
    cmp dword [rel dynamic_wait_status], 77
    jne scheduler_isolation_failure

    mov eax, 24
    mov rdi, r14
    lea rsi, [rel dynamic_wait_status]
    syscall
    FP_CHECK
    cmp rax, -10
    jne scheduler_isolation_failure

    mov dword [rel dynamic_wait_status], 0x55555555
    mov eax, 23
    lea rdi, [rel dynamic_child_path]
    syscall
    FP_CHECK
    cmp rax, 201
    jne scheduler_isolation_failure
    mov r14, rax

    mov eax, 24
    mov rdi, r14
    lea rsi, [rel dynamic_wait_status]
    syscall
    FP_CHECK
    cmp rax, 201
    jne scheduler_isolation_failure
    cmp dword [rel dynamic_wait_status], 77
    jne scheduler_isolation_failure
    cmp qword [rel probe_data], rbx
    jne scheduler_isolation_failure
    mov eax, 9
    mov edi, 130
    syscall
    FP_CHECK
    ud2

dynamic_child:
    mov rbx, 0x1919191919191919
    mov qword [rel probe_data], rbx
    mov eax, 9
    mov edi, 77
    syscall
    FP_CHECK
    ud2

section .data
align 8
probe_data:
    dq 0x3634464C45545349
    dq scheduler_fault
probe_progress:
    dq 0
probe_runqueue_fault:
    dq runqueue_fault
align 4
dynamic_child_path:
    db "/probe/child", 0
align 4
dynamic_wait_status:
    dd 0x55555555

section .bss
alignb 16
probe_zero_tail:
    resb 64

FP_PROBE_CODE
