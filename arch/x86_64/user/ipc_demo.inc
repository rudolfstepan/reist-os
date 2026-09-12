; User-only IPC fixture: two independent pairs, no privileged role checks.
; Handle candidates are deliberately guessed to prove that a number alone
; grants nothing. Only successful explicit delegation makes one usable.
process_demo:
    mov r12, rdi
    FP_BEGIN edi
    sub rsp, 256
    mov r15, rsp
    mov rdi, r15
    xor eax, eax
    mov ecx, 32
    rep stosq
    mov dword [r15], 1
    mov dword [r15+4], 140
    mov dword [r15+8], 4
    xor edi, edi
    xor esi, esi
    xor edx, edx
    mov eax, 22
    call ipc_demo_call
    mov rbp, rax
    mov edx, r12d
    and edx, 3
    mov eax, r12d
    shr eax, 8
    and eax, 1
    shl eax, 2
    lea eax, [rax+rdx+1]
    cmp rax, rbp
    jne ipc_demo_bad
    test r12b, 1
    jnz ipc_demo_peer
    ; Reject an unmapped64-bit output before consuming an endpoint.
    mov rdi, 0x100500000
    xor esi, esi
    xor edx, edx
    mov eax, 49
    call ipc_demo_call
    cmp rax, -14
    jne ipc_demo_bad
    lea rdi, [r15+144]
    mov eax, 49
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov r13d, [r15+144]
    mov edi, r13d
    lea rsi, [rbp+1]
    mov edx, 4
    mov eax, 55
    call ipc_demo_call
    cmp rax, -22
    jne ipc_demo_bad
    mov edx, 3
    mov eax, 55
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    ; A writable receive buffer is required; executable text is not one.
    lea rsi, [rel process_demo]
    xor edx, edx
    mov eax, 54
    call ipc_demo_call
    cmp rax, -14
    jne ipc_demo_bad
    mov rsi, r15
    mov eax, 51
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov eax, r12d
    and eax, 2
    add eax, 0xa5
    cmp [r15+12], al
    jne ipc_demo_bad
    xor r14d, r14d
.fill:
    mov eax, r12d
    and eax, 2
    shl eax, 4
    add eax, r14d
    mov [r15+12], al
    mov edi, r13d
    mov rsi, r15
    xor edx, edx
    mov eax, 53
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    inc r14d
    cmp r14d, 4
    jb .fill
    inc byte [r15+12]
    mov eax, 53
    call ipc_demo_call
    cmp rax, -11
    jne ipc_demo_bad
    mov eax, 50
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov eax, 51
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    cmp byte [r15+12], 0xee
    jne ipc_demo_bad
    mov edx, 20
%if X86_64_NATIVE_IPC_CASE == 2
    test r12b, 2
    jnz .release_timeout_ready
    mov edx, 1000
.release_timeout_ready:
%endif
    mov eax, 54
    call ipc_demo_call
%if X86_64_NATIVE_IPC_CASE == 2
    test r12b, 2
    jnz .normal_timeout
    cmp rax, -32
    jne ipc_demo_bad
    jmp .close
.normal_timeout:
%endif
    cmp rax, -110
    jne ipc_demo_bad
%if X86_64_NATIVE_IPC_CASE == 1
    test r12b, 2
    jnz .close
    ud2
%elif X86_64_NATIVE_IPC_CASE == 3
    test r12b, 2
    jnz .close
.spin:
    pause
    jmp .spin
%endif
.close:
    mov edi, r13d
    xor esi, esi
    xor edx, edx
    mov eax, 52
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    jmp ipc_demo_done

ipc_demo_peer:
    mov r13d, r12d
    shr r13d, 8
    and r13d, 1
    inc r13d
    shl r13d, 8
    inc r13d
    mov r14d, 64
    mov eax, r12d
    and eax, 2
    add eax, 0xa5
    mov [r15+12], al
.discover:
    mov edi, r13d
    mov rsi, r15
    xor edx, edx
    mov eax, 53
    call ipc_demo_call
    test rax, rax
    jz .delegated
    cmp rax, -9
    jne ipc_demo_bad
    dec r14d
    jz ipc_demo_bad
    inc r13b
    cmp r13b, 16
    jbe .discover
    mov r13b, 1
    xor edi, edi
    xor esi, esi
    xor edx, edx
    mov eax, 40
    call ipc_demo_call
    jmp .discover
.delegated:
    mov edi, r13d
    xor esi, esi
    xor edx, edx
    mov eax, 52
    call ipc_demo_call
    cmp rax, -13
    jne ipc_demo_bad
    mov edi, 100
    mov eax, 41
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    xor r14d, r14d
.drain:
    mov edi, r13d
    mov rsi, r15
    xor edx, edx
    mov eax, 51
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov eax, r12d
    and eax, 2
    shl eax, 4
    add eax, r14d
    cmp [r15+12], al
    jne ipc_demo_bad
    inc r14d
    cmp r14d, 5
    jb .drain
    mov byte [r15+12], 0xee
    mov eax, 50
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
%if X86_64_NATIVE_IPC_CASE == 2
    test r12b, 2
    jnz .wait_close
    mov edi, 50
    xor esi, esi
    xor edx, edx
    mov eax, 41
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov edi, r13d
    mov eax, 58
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    jmp .stale
.wait_close:
%endif
    mov eax, 51
    call ipc_demo_call
    cmp rax, -32
    jne ipc_demo_bad
.stale:
    mov rsi, r15
    xor edx, edx
    mov eax, 54
    call ipc_demo_call
    cmp rax, -9
    jne ipc_demo_bad
ipc_demo_done:
    mov edi, r12d
    and edi, 3
    or edi, 0xc100
    xor esi, esi
    xor edx, edx
    mov eax, 9
    call ipc_demo_call
    ud2
ipc_demo_bad:
    mov edi, r12d
    and edi, 3
    shl edi, 8
    or edi, [r15+160]
    or edi, 0xbad00000
    xor esi, esi
    xor edx, edx
    mov eax, 9
    call ipc_demo_call
    ud2
ipc_demo_call:
    inc dword [r15+160]
    xor r10d, r10d
    xor r8d, r8d
    xor r9d, r9d
    syscall
    FP_CHECK
    ret
