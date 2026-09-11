; Pure classification of a kernel-owned normalized Intel exception frame.
; RDI frame; EAX REIST raw terminal status, or 0 for kernel-fatal/unsupported.
; Never dereference saved RIP/RSP. No public ABI and no exception retry.
BITS 64
section .text
global x86_64_user_fault_status64
x86_64_user_fault_status64:
    cmp qword [rdi + 18*8], 0x33
    jne .fatal
    cmp qword [rdi + 21*8], 0x2b
    jne .fatal
    mov rax, [rdi + 15*8]
    cmp rax, 31
    ja .fatal
    mov edx, (1<<0)|(1<<1)|(1<<3)|(1<<4)|(1<<5)|(1<<6)|(1<<13)|(1<<14)|(1<<16)|(1<<17)|(1<<19)
    bt edx, eax
    jnc .fatal
    mov rdx, [rdi + 16*8]
    shr rdx, 32
    jnz .fatal
    cmp eax, 13
    je .status
    cmp eax, 14
    je .status
    cmp qword [rdi + 16*8], 0 ; includes architecturally zero #AC error code
    jne .fatal
.status:
    add eax, 128
    ret
.fatal:
    xor eax, eax
    ret
