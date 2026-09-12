BITS 64
section .text.start
global _start
extern main
_start:
    xor ebp,ebp
    mov rdi,[rsp]
    lea rsi,[rsp+8]
    lea rdx,[rsi+rdi*8+8]
    call main
    mov edi,eax
    xor esi,esi
    xor edx,edx
    xor r10d,r10d
    xor r8d,r8d
    xor r9d,r9d
    mov eax,9
    syscall
    ud2
section .note.GNU-stack noalloc noexec nowrite progbits
