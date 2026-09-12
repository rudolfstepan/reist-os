; Ring3-only test: independent peers yield while large heap calls are pending.
; Every path retains an8KiB heap IPC buffer for terminal retirement.
heap_demo:
    push rbx
    push rbp
    push r13
    test r12b,1
    jz .allocate
    mov ebp,16
.peer:
    xor edi,edi
    xor esi,esi
    push 40
    pop rax
    call .syscall
    test rax,rax
    jnz .bad
    dec ebp
    jnz .peer
    jmp .message
.allocate:
    mov edi,0x100000
    xor esi,esi
    push 4
    pop rax
    call .syscall
    mov rbx,rax
    shr rax,32
    cmp eax,1
    jne .bad
    mov r13,0x17395b7da1c3e5f7
    xor r13,r12
    mov rdi,rbx
    mov rax,r13
    mov ecx,0x100000/8
    rep stosq
    mov rdi,rbx
    mov rsi,-1
    push 6
    pop rax
    call .syscall
    cmp rax,-12
    jne .bad
    mov rdi,rbx
    mov rax,r13
    mov ecx,0x100000/8
    repe scasq
    jne .bad
    mov rdi,rbx
    mov esi,0x200000
    push 6
    pop rax
    call .syscall
    mov rbp,rax
    shr rax,32
    cmp eax,1
    jne .bad
    mov rdi,rbp
    mov rax,r13
    mov ecx,0x100000/8
    repe scasq
    jne .bad
    xor eax,eax
    mov ecx,0x100000/8
    repe scasq
    jne .bad
    mov rdi,rbp
    xor esi,esi
    push 5
    pop rax
    call .syscall
    test rax,rax
    jnz .bad
    mov rdi,rbx
    push 5
    pop rax
    call .syscall
    cmp rax,-22
    jne .bad
.message:
    mov edi,8192
    xor esi,esi
    push 4
    pop rax
    call .syscall
    mov rbx,rax
    shr rax,32
    cmp eax,1
    jne .bad
    mov rax,rbx
    pop r13
    pop rbp
    pop rbx
    ret
.syscall:
    xor edx,edx
    jmp ipc_demo_transport_call
.bad:
    mov edi,0xbadf0011
    xor esi,esi
    mov eax,9
    syscall
    ud2
