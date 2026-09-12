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

; v2 uses the same operation/state model with one atomic three-word binding.
; No call to the mutating v1 entry: high-word corruption must fail before the
; first low-word write. All caller-owned ranges are disjoint and fixed-sized.
global reist_x64_profile_apply_v2
reist_x64_profile_apply_v2:
    push rbx
    push r12
    mov rbx,rdx
    cmp rsi,3
    ja .bad
    test rdi,rdi
    jz .bad
    test rdi,7
    jnz .bad
    mov rcx,rdi
    add rcx,48
    jc .bad
    mov r8,[rdi]
    mov r9,[rdi+8]
    test r8,r8
    jz .bad
    test r9,r9
    jz .bad
    mov rax,r8
    or rax,r9
    test rax,7
    jnz .bad
    mov rax,r8
    add rax,256
    jc .bad
    mov rdx,r9
    add rdx,32
    jc .bad
    cmp r8,rcx
    jae .task_ok
    cmp rax,rdi
    ja .bad
.task_ok:
    cmp r9,rcx
    jae .profile_ok
    cmp rdx,rdi
    ja .bad
.profile_ok:
    cmp r8,rdx
    jae .ranges_ok
    cmp rax,r9
    ja .bad
.ranges_ok:
    mov r10,[rdi+16]
    test r10,r10
    jz .bad
    mov rax,r10
    shr rax,32
    jnz .bad
    cmp [r8+8],r10
    jne .bad
    mov rcx,[r8]
    test rcx,rcx
    jz .bad
    cmp rcx,9
    ja .bad
    mov rax,[rdi+40]
    test rax,~31
    jnz .bad
    cmp rsi,1
    je .install
    cmp rsi,3
    je .revoke
    test rsi,rsi
    jz .live
    cmp rcx,2
    jne .bad
.live:
    cmp [r9],r10
    jne .bad
    xor r12d,r12d
.compare:
    mov rax,[rdi+24+r12*8]
    cmp [r9+8+r12*8],rax
    jne .bad
    inc r12d
    cmp r12d,3
    jb .compare
    test rsi,rsi
    jz .ok
    cmp rsi,3
    je .clear
    cmp rbx,133
    jae .denied
    mov rax,rbx
    shr rax,6
    mov rax,[r9+8+rax*8]
    and ebx,63
    bt rax,rbx
    jnc .denied
    jmp .ok
.install:
    cmp rcx,9
    jne .bad
    mov rax,[r9]
    or rax,[r9+8]
    or rax,[r9+16]
    or rax,[r9+24]
    jnz .bad
    mov rax,[rdi+24]
    mov [r9+8],rax
    mov rax,[rdi+32]
    mov [r9+16],rax
    mov rax,[rdi+40]
    mov [r9+24],rax
    mov [r9],r10
    jmp .ok
.revoke:
    cmp rcx,3
    je .terminal
    cmp rcx,4
    je .terminal
    cmp rcx,8
    je .terminal
    cmp rcx,9
    jne .bad
.terminal:
    cmp qword [r9],0
    jne .live
    mov rax,[r9+8]
    or rax,[r9+16]
    or rax,[r9+24]
    jnz .bad
    jmp .ok
.clear:
    mov qword [r9+8],0
    mov qword [r9+16],0
    mov qword [r9+24],0
    mov qword [r9],0
.ok:
    mov eax,1
    jmp .return
.denied:
    mov eax,2
    jmp .return
.bad:
    xor eax,eax
.return:
    pop r12
    pop rbx
    ret
