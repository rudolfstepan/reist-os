; Private SysV AMD64 fixed sampled CPU accounting; caller owns lifecycle.
BITS 64
section .text
global reist_x64_budget_apply
reist_x64_budget_apply:
    test rdi, rdi
    jz .fail
    test rdi, 7
    jnz .fail
    cmp rsi, 3
    ja .fail
    mov rax, rdx
    shr rax, 32
    jnz .fail
    cmp qword [rdi], 0
    jne .live
    mov rax, [rdi + 8]
    or rax, [rdi + 16]
    or rax, [rdi + 24]
    jnz .fail
    cmp rsi, 1
    je .bind
    or rdx, rcx
    or rdx, rsi
    jnz .fail
    jmp .success
.bind:
    test rdx, rdx
    jz .fail
    test rcx, rcx
    jz .fail
    cmp rcx, 65536
    ja .fail
    mov [rdi], rdx
    mov [rdi + 8], rcx
    jmp .success
.live:
    test rdx, rdx
    jz .fail
    cmp [rdi], rdx
    jne .fail
    mov r8, [rdi + 8]
    test r8, r8
    jz .fail
    cmp r8, 65536
    ja .fail
    mov r9, [rdi + 16]
    cmp r9, r8
    ja .fail
    mov r10, [rdi + 24]
    test r9, r9
    jnz .used
    test r10, r10
    jnz .fail
    jmp .valid
.used:
    cmp r10, r9
    jb .fail
.valid:
    cmp rsi, 2
    je .charge
    test rcx, rcx
    jnz .fail
    test rsi, rsi
    jz .success
    cmp rsi, 3
    jne .fail
    xor eax, eax
    mov [rdi], rax
    mov [rdi + 8], rax
    mov [rdi + 16], rax
    mov [rdi + 24], rax
    jmp .success
.charge:
    cmp r9, r8
    jae .fail
    cmp rcx, r10
    jbe .fail
    inc r9
    mov [rdi + 16], r9
    mov [rdi + 24], rcx
    cmp r9, r8
    jne .success
    mov eax, 2
    ret
.success:
    mov eax, 1
    ret
.fail:
    xor eax, eax
    ret
