; Ordinary bounded System V argc/argv program, no private RPC startup protocol.
BITS 64
section .text
global main
main:
    push rbx
    push r12
    push r13
    sub rsp,32
    xor r13d,r13d
    cmp edi,2
    jb .arguments
    mov rax,[rsi+8]
    movzx r13d,byte [rax]
.arguments:
    mov rax,(24<<32)|1
    mov [rsp],rax
    mov qword [rsp+8],5 ; CHECK
    mov qword [rsp+16],0
    mov ebx,20
.lease:
    mov rdi,rsp
    xor esi,esi
    xor edx,edx
    xor r10d,r10d
    xor r8d,r8d
    xor r9d,r9d
    mov eax,127
    syscall
    test rax,rax
    jz .ready
    cmp rax,-11
    jne .error
    mov edi,50
    mov eax,41
    syscall
    test rax,rax
    jnz .error
    dec ebx
    jnz .lease
    jmp .error
.ready:
    cmp r13b,'u'
    jne .quota_check
    ud2
.quota_check:
    cmp r13b,'q'
    jne .cancel_check
.quota:
    pause
    jmp .quota
.cancel_check:
    cmp r13b,'c'
    jne .normal
    mov ebx,20
.cancel:
    mov edi,100
    mov eax,41
    syscall
    test rax,rax
    jnz .error
    dec ebx
    jnz .cancel
    jmp .error
.normal:
    lea r12,[rel message]
    mov ebx,10
    mov qword [rsp+24],20
.write:
    dec qword [rsp+24]
    js .error
    mov edi,1
    mov rsi,r12
    mov edx,ebx
    mov eax,20
    syscall
    cmp rax,-11
    je .write_wait
    test rax,rax
    jle .error
    cmp rax,rbx
    ja .error
    add r12,rax
    sub ebx,eax
    jnz .write
    jmp .release
.write_wait:
    mov edi,10
    xor esi,esi
    xor edx,edx
    mov eax,41
    syscall
    test rax,rax
    jnz .error
    jmp .write
.release:
    mov qword [rsp+8],3 ; RELEASE
    mov rdi,rsp
    xor esi,esi
    xor edx,edx
    mov eax,127
    syscall
    test rax,rax
    jnz .error
    mov eax,82
    jmp .done
.error:
    mov eax,250
.done:
    add rsp,32
    pop r13
    pop r12
    pop rbx
    ret
section .rodata
message: db 'SESSION64',10
section .note.GNU-stack noalloc noexec nowrite progbits
