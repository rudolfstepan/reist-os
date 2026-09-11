; Private bounded AMD64 argc/argv/envp/auxv construction, no direct user access.
BITS 64
section .text
global reist_x64_startup_stack
reist_x64_startup_stack:
    test rdi, rdi
    jz .bad_entry
    test rdi, 7
    jnz .bad_entry
    cmp rsi, 1
    ja .bad_entry
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp, 160 ; eight source offsets, eight lengths, op/RSP/head/total
    mov rbp, rdi
    mov [rsp + 128], rsi
    mov r12, [rbp]
    test r12, r12
    jz .metadata
    test r12, 7
    jnz .metadata
    mov rax, r12
    add rax, 4096
    jc .metadata
    mov r15, [rbp + 16]
    cmp r15, 4096
    jb .metadata
    test r15, 4095
    jnz .metadata
    mov rax, r15
    add rax, 4096
    jc .metadata
    mov rdx, 0x0000800000000000
    cmp rax, rdx
    jae .metadata
    mov rax, [rbp + 24]
    cmp rax, 8192
    jb .metadata
    cmp rax, rdx
    jae .metadata
    test rax, 4095
    jnz .metadata
    mov r14, [rbp + 40]
    cmp r14, 8
    ja .too_big
    xor ebx, ebx
    mov rax, [rbp + 32]
    test r14, r14
    jnz .vector
    test rax, rax
    jnz .pointer
    jmp .size
.vector:
    sub rax, r15
    jc .pointer
    test rax, 7
    jnz .pointer
    mov rdx, r14
    shl rdx, 3
    mov ecx, 4096
    sub rcx, rdx
    cmp rax, rcx
    ja .pointer
    lea r10, [r12 + rax]
    xor ecx, ecx
.argument:
    mov rax, [r10 + rcx*8]
    sub rax, r15
    jc .pointer
    cmp rax, 4096
    jae .pointer
    mov [rsp + rcx*8], rax
    xor edx, edx
.scan:
    cmp edx, 128
    jae .too_big
    lea r8, [rax + rdx]
    cmp r8, 4096
    jae .pointer
    cmp byte [r12 + r8], 0
    je .length
    inc edx
    jmp .scan
.length:
    inc edx
    mov [rsp + 64 + rcx*8], rdx
    add edx, 15
    and edx, -16
    add rbx, rdx
    inc ecx
    cmp rcx, r14
    jb .argument
.size:
    lea rax, [r14*8 + 56 + 15]
    and eax, -16
    cmp eax, 96
    jae .head
    mov eax, 96 ; preserves the existing two-argument initial stack exactly
.head:
    mov [rsp + 144], rax
    add rax, rbx
    cmp rax, 1152
    ja .too_big
    mov [rsp + 152], rax
    mov rdx, [rbp + 24]
    sub rdx, rax
    mov [rsp + 136], rdx
    cmp qword [rsp + 128], 0
    je .success
    mov r13, [rbp + 8]
    test r13, r13
    jz .metadata
    test r13, 7
    jnz .metadata
    mov rax, r13
    add rax, 4096
    jc .metadata
    cmp rax, r12
    jbe .disjoint
    lea rdx, [r12 + 4096] ; source end already checked for overflow
    cmp rdx, r13
    ja .metadata
.disjoint:
    add r13, 4096
    sub r13, [rsp + 152]
    mov rdi, r13
    mov rcx, [rsp + 152]
    xor eax, eax
    cld
    rep stosb
    mov [r13], r14
    lea rdx, [r14*8 + 24]
    mov qword [r13 + rdx], 0x52534901 ; AT_REIST_IPC_HANDLE
    mov rax, [rbp + 48]
    mov [r13 + rdx + 8], rax
    ; argv/envp/AT_NULL sentinels and all alignment padding remain zero.
    mov rdi, r13
    add rdi, [rsp + 144]
    xor r11d, r11d
.copy_next:
    cmp r11, r14
    jae .success
    mov rax, rdi
    sub rax, r13
    add rax, [rsp + 136]
    mov [r13 + 8 + r11*8], rax
    mov rsi, [rsp + r11*8]
    add rsi, r12
    mov rcx, [rsp + 64 + r11*8]
    lea rdx, [rcx + 15]
    and edx, -16
    add rdx, rdi
    rep movsb
    mov rdi, rdx
    inc r11
    jmp .copy_next
.success:
    mov rax, [rsp + 136]
    jmp .return
.pointer:
    mov rax, -14
    jmp .return
.too_big:
    mov rax, -7
    jmp .return
.metadata:
    mov rax, -22
.return:
    add rsp, 160
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
.bad_entry:
    mov rax, -22
    ret
