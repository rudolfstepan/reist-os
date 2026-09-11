; Private serialized SysV AMD64 context validate/capture. No user dereference.
BITS 64
section .text
global reist_x64_context_apply
reist_x64_context_apply:
    test rdi, rdi
    jz .fail
    test rsi, rsi
    jz .fail
    test rdi, 7
    jnz .fail
    test rsi, 7
    jnz .fail
    cmp rdx, 1
    ja .fail
    mov r8, [rdi]
    test r8, r8
    jz .fail
    test r8, 7
    jnz .fail
    cmp qword [r8], 2
    jne .fail
    mov rax, [rdi + 8]
    test rax, rax
    jz .fail
    mov rcx, rax
    shr rcx, 32
    jnz .fail
    cmp [r8 + 8], rax
    jne .fail
    mov rax, [rdi + 16]
    test rax, rax
    jz .fail
    test rax, 4095
    jnz .fail
    cmp [r8 + 16], rax
    jne .fail
    mov r9, 0x0000800000000000
    mov rax, [rdi + 24]
    cmp rax, 4096
    jb .fail
    mov rcx, [rdi + 32]
    cmp rcx, r9
    jae .fail
    cmp rax, rcx
    jae .fail
    cmp [rsi + 160], rax
    jb .fail
    cmp [rsi + 160], rcx
    ja .fail
    mov rax, [rsi + 136]
    cmp rax, 4096
    jb .fail
    cmp rax, r9
    jae .fail
    cmp qword [rsi + 144], 0x33
    jne .fail
    cmp qword [rsi + 168], 0x2b
    jne .fail
    cmp qword [rsi + 128], 0
    jne .fail
    mov rax, [rsi + 152]
    test rax, 2
    jz .fail
    mov rcx, ~0xad7
    cmp qword [rdi + 40], 1
    jne .flags_mask_ready
    ; Intel event frames may carry RF; preserve it for IRETQ, not SYSCALL.
    mov rcx, ~0x10ad7
.flags_mask_ready:
    test rax, rcx
    jnz .fail
    cmp qword [rdi + 40], 1
    ja .fail
    je .irq
    cmp qword [rsi + 120], 256
    jne .fail
    cmp [rsi + 32], rax ; architectural R11 flags
    jne .fail
    mov rax, [rsi + 136]
    cmp [rsi + 96], rax ; architectural RCX return RIP
    jne .fail
    jmp .validated
.irq:
    cmp qword [rsi + 120], 32
    jne .fail
    test rax, 512
    jz .fail
.validated:
    test rdx, rdx
    jz .success
    ; Only context fields are published. Identity/resources/accounting unchanged.
%macro CAPTURE 2
    mov rax, [rsi + %1]
    mov [r8 + %2], rax
%endmacro
    CAPTURE 0, 208
    CAPTURE 8, 200
    CAPTURE 16, 192
    CAPTURE 24, 184
    CAPTURE 32, 248
    CAPTURE 40, 176
    CAPTURE 48, 168
    CAPTURE 56, 160
    CAPTURE 64, 152
    CAPTURE 72, 144
    CAPTURE 80, 136
    CAPTURE 88, 128
    CAPTURE 96, 240
    CAPTURE 104, 120
    CAPTURE 112, 232
    CAPTURE 136, 96
    CAPTURE 152, 112
    CAPTURE 160, 104
    cmp qword [rdi + 40], 0
    jne .success
    mov qword [r8 + 232], 0
.success:
    mov eax, 1
    ret
.fail:
    xor eax, eax
    ret
