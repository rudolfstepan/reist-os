; Private pure terminal classifier. Preserve every GPR except RAX.
BITS 64
section .text
global reist_x64_terminal_status
reist_x64_terminal_status:
    cmp rdi, 1
    ja .invalid
    mov rax, rsi
    shr rax, 32
    jnz .invalid
    test rdi, rdi
    jnz .valid
    cmp esi, 256
    jb .exception
    cmp esi, 258
    ja .invalid
    jmp .valid
.exception:
    cmp esi, 128
    jb .invalid
    cmp esi, 159
    ja .invalid
    ; bt uses the low five index bits: status128 maps to Intel vector0.
    mov eax, (1<<0)|(1<<1)|(1<<3)|(1<<4)|(1<<5)|(1<<6)|(1<<13)|(1<<14)|(1<<16)|(1<<17)|(1<<19)
    bt eax, esi
    jnc .invalid
.valid:
    mov rax, rsi
    ret
.invalid:
    mov rax, -22
    ret
