; Private serialized SysV AMD64 authority lifecycle. No roles or user pointers.
BITS 64
section .text
global reist_x64_profile_apply
reist_x64_profile_apply:
    push rbx
    mov rbx, rdx
    cmp rsi, 3
    ja .bad
    test rdi, rdi
    jz .bad
    test rdi, 7
    jnz .bad
    mov rcx, rdi
    add rcx, 32
    jc .bad
    mov r8, [rdi]
    mov r9, [rdi + 8]
    test r8, r8
    jz .bad
    test r8, 7
    jnz .bad
    test r9, r9
    jz .bad
    test r9, 7
    jnz .bad
    mov rax, r8
    add rax, 256
    jc .bad
    mov rdx, r9
    add rdx, 16
    jc .bad
    ; Disjoint descriptor, task and writable authority record before effects.
    cmp r8, rcx
    jae .task_descriptor_ok
    cmp rax, rdi
    ja .bad
.task_descriptor_ok:
    cmp r9, rcx
    jae .profile_descriptor_ok
    cmp rdx, rdi
    ja .bad
.profile_descriptor_ok:
    cmp r8, rdx
    jae .ranges_ok
    cmp rax, r9
    ja .bad
.ranges_ok:
    mov r10, [rdi + 16]
    test r10, r10
    jz .bad
    mov rax, r10
    shr rax, 32
    jnz .bad
    cmp [r8 + 8], r10
    jne .bad
    mov rcx, [r8]
    test rcx, rcx
    jz .bad
    cmp rcx, 9
    ja .bad
    mov r11, [rdi + 24]
    cmp rsi, 1
    je .install
    cmp rsi, 3
    je .revoke
    test rsi, rsi
    jz .live
    cmp rcx, 2
    jne .bad
.live:
    cmp [r9], r10
    jne .bad
    cmp [r9 + 8], r11
    jne .bad
    test rsi, rsi
    jz .ok
    cmp rbx, 64
    jae .denied
    bt r11, rbx
    jnc .denied
    jmp .ok
.install:
    cmp rcx, 9
    jne .bad
    cmp qword [r9], 0
    jne .bad
    cmp qword [r9 + 8], 0
    jne .bad
    mov [r9 + 8], r11
    mov [r9], r10
    jmp .ok
.revoke:
    cmp rcx, 3
    je .terminal
    cmp rcx, 4
    je .terminal
    cmp rcx, 8
    je .terminal
    cmp rcx, 9
    jne .bad
.terminal:
    cmp qword [r9], 0
    jne .live_revoke
    cmp qword [r9 + 8], 0
    jne .bad
    jmp .ok
.live_revoke:
    cmp [r9], r10
    jne .bad
    cmp [r9 + 8], r11
    jne .bad
    mov qword [r9 + 8], 0
    mov qword [r9], 0
.ok:
    mov eax, 1
    jmp .return
.denied:
    mov eax, 2
    jmp .return
.bad:
    xor eax, eax
.return:
    pop rbx
    ret
