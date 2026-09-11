BITS 64
section .text
global reist_x64_request_admit
reist_x64_request_admit:
    test rdi, rdi
    jz .corrupt
    test rdi, 7
    jnz .corrupt
    mov rax, [rdi]
    cmp rax, 15
    je .read
    cmp rax, 20
    je .write
    cmp rax, 22
    je .allow
    cmp rax, 23
    je .process
    cmp rax, 30
    je .process
    cmp rax, 24
    jne .unsupported
.process:
    cmp qword [rdi + 48], 1
    ja .corrupt
    cmp qword [rdi + 56], 2
    ja .corrupt
    mov rcx, [rdi + 56]
    sub rcx, [rdi + 64]
    jc .corrupt
    cmp rcx, [rdi + 48]
    jne .corrupt
    mov rcx, [rdi + 72]
    cmp rcx, 15
    ja .corrupt
    test rcx, rcx
    jz .state_ok
    test cl, 1
    jz .corrupt
    test cl, 4
    jz .receiver
    test cl, 2
    jz .corrupt
.receiver:
    test cl, 8
    jz .state_ok
    test cl, 6
    jnz .corrupt
.state_ok:
    cmp rax, 24
    je .wait
    cmp rax, 23
    jne .path
    mov rcx, [rdi + 16]
    or rcx, [rdi + 24]
    jnz .invalid
.path:
    mov rsi, [rdi + 32]
    test rsi, rsi
    jz .corrupt
    test rsi, 7
    jnz .corrupt
    mov rcx, rsi
    add rcx, 4096
    jc .corrupt
    mov rdx, [rdi + 40]
    test rdx, 4095
    jnz .corrupt
    cmp rdx, 4096
    jb .corrupt
    mov rcx, rdx
    add rcx, 4096
    jc .corrupt
    mov r8, 0x0000800000000000
    cmp rcx, r8
    jae .corrupt
    mov rcx, [rdi + 8]
    sub rcx, rdx
    jc .pointer
    xor edx, edx
    xor r8d, r8d
    lea r9, [rel .child_path]
.scan:
    cmp edx, 16
    jae .long_path
    cmp rcx, 4096
    jae .pointer
    movzx r10d, byte [rsi + rcx]
    cmp r10b, [r9 + rdx]
    je .same
    mov r8d, 1
.same:
    test r10b, r10b
    jz .path_end
    inc rcx
    inc edx
    jmp .scan
.path_end:
    test r8d, r8d
    jnz .not_found
    cmp qword [rdi + 48], 0
    jne .again
    cmp qword [rdi + 56], 2
    jae .again
    cmp qword [rdi + 72], 0
    je .descriptor
    cmp qword [rdi + 72], 1
    jne .again
    jmp .allow
.wait:
    cmp qword [rdi + 24], 0
    jne .invalid
    cmp qword [rdi + 8], 301
    jne .no_child
    cmp qword [rdi + 48], 1
    jne .no_child
    jmp .allow
.read:
    cmp qword [rdi + 8], 0
    jne .descriptor
    cmp qword [rdi + 24], 1
    ja .invalid
    jmp .io
.write:
    mov rax, [rdi + 8]
    sub rax, 1
    cmp rax, 1
    ja .descriptor
    cmp qword [rdi + 24], 64
    ja .invalid
.io:
    cmp qword [rdi + 24], 0
    je .zero
.allow:
    mov eax, 1
    ret
.zero:
    xor eax, eax
    ret
.descriptor:
    mov rax, -9
    ret
.invalid:
    mov rax, -22
    ret
.pointer:
    mov rax, -14
    ret
.not_found:
    mov rax, -2
    ret
.long_path:
    mov rax, -36
    ret
.no_child:
    mov rax, -10
    ret
.again:
    mov rax, -11
    ret
.unsupported:
    mov rax, -38
    ret
.corrupt:
    mov rax, -4096
    ret
.child_path: db "/shell/child", 0, 0, 0, 0
