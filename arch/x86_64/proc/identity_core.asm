; Private serialized SysV AMD64 task-identity lifecycle. No role/profile policy.
BITS 64
section .text
global reist_x64_identity_apply
reist_x64_identity_apply:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    mov r12, rdi
    mov r13, rsi
    mov r14, rdx
    mov r15, rcx
    cmp r13, 3
    ja .fail
    call identity_validate
    test eax, eax
    jz .fail
    test r13, r13
    jz .success
    cmp r14, r10
    jae .fail
    mov rbx, r14
    shl rbx, 8
    add rbx, r8
    cmp r13, 1
    je .reserve
    test r15, r15
    jz .fail
    mov rax, r15
    shr rax, 32
    jnz .fail
    cmp qword [rbx], 0
    je .already_retired
    cmp [rbx + 8], r15
    jne .fail
    cmp r13, 2
    je .publish
    mov rax, [rbx]
    cmp rax, 3
    je .retire
    cmp rax, 4
    je .retire
    cmp rax, 8
    je .retire
    cmp rax, 9
    jne .fail
.retire:
    ; The adapter has already fenced profiles/IPC and released frames/FP.
    mov ecx, 2
.resource_zero:
    cmp qword [rbx + rcx*8], 0
    jne .fail
    inc ecx
    cmp ecx, 12
    jb .resource_zero
    mov [r9 + r14*4], r15d
    mov rdi, rbx
    xor eax, eax
    mov ecx, 32
    cld
    rep stosq
    jmp .success
.already_retired:
    cmp r13, 3
    jne .fail
    cmp [r9 + r14*4], r15d
    jne .fail
    jmp .success
.reserve:
    test r15, r15
    jnz .fail
    cmp qword [rbx], 0
    jne .fail
    cmp r11d, 0xffffffff
    je .fail
    inc r11d
    mov [r12 + 20], r11d
    mov [rbx + 8], r11
    mov qword [rbx], 9
    mov rax, r11
    shl rax, 32
    or rax, r14
    jmp .return
.publish:
    cmp qword [rbx], 9
    jne .fail
    mov rax, [rbx + 16] ; owned CR3
    test rax, rax
    jz .fail
    test rax, 4095
    jnz .fail
    mov rax, [rbx + 24] ; owned stack frame
    test rax, rax
    jz .fail
    test rax, 4095
    jnz .fail
    cmp qword [rbx + 96], 0 ; adapter validated executable entry
    je .fail
    cmp qword [rbx + 104], 0
    je .fail
    mov qword [rbx], 1
.success:
    mov eax, 1
    jmp .return
.fail:
    xor eax, eax
.return:
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret

; Complete bounded namespace validation. No memory mutation or user pointers.
; R8 records, R9 tombstones, R10 capacity, R11 last generation.
identity_validate:
    test r12, r12
    jz .fail
    mov r10d, [r12 + 16]
    test r10d, r10d
    jz .fail
    cmp r10d, 64
    ja .fail
    mov r8, [r12]
    mov r9, [r12 + 8]
    test r8, r8
    jz .fail
    test r8, 7
    jnz .fail
    test r9, r9
    jz .fail
    test r9, 3
    jnz .fail
    mov r11d, [r12 + 20]
    xor ecx, ecx
.slot:
    mov edi, [r9 + rcx*4]
    cmp rdi, r11
    ja .fail
    mov edx, ecx
    shl rdx, 8
    add rdx, r8
    mov rsi, [rdx]
    test rsi, rsi
    jz .free
    cmp rsi, 9
    ja .fail
    mov rax, [rdx + 8]
    test rax, rax
    jz .fail
    cmp rax, r11
    ja .fail
    cmp rax, rdi
    jbe .fail
    jmp .next
.free:
    xor eax, eax
    xor ebp, ebp
.zero:
    cmp qword [rdx + rbp*8], 0
    jne .fail
    inc ebp
    cmp ebp, 32
    jb .zero
.next:
    xor ebp, ebp
.unique:
    cmp ebp, ecx
    jae .advance
    mov ebx, ebp
    shl rbx, 8
    test rax, rax
    jz .retired_unique
    cmp [r8 + rbx + 8], rax
    je .fail
    mov esi, [r9 + rbp*4]
    cmp rax, rsi
    je .fail
.retired_unique:
    test edi, edi
    jz .unique_next
    cmp [r8 + rbx + 8], rdi
    je .fail
    cmp [r9 + rbp*4], edi
    je .fail
.unique_next:
    inc ebp
    jmp .unique
.advance:
    inc ecx
    cmp ecx, r10d
    jb .slot
    mov eax, 1
    ret
.fail:
    xor eax, eax
    ret
