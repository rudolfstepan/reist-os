; User-only IPC fixture: two independent pairs, no privileged role checks.
; Handle candidates are deliberately guessed to prove that a number alone
; grants nothing. Only successful explicit delegation makes one usable.
%ifdef IPC_DEMO_BULK
%define IPC_DEMO_MESSAGE rbx
%define IPC_DEMO_DEPTH 1
%else
%define IPC_DEMO_MESSAGE r15
%define IPC_DEMO_DEPTH 4
%endif
process_demo:
    mov r12, rdi
    FP_BEGIN edi
    sub rsp, 256
    mov r15, rsp
%ifdef REIST_NATIVE_RUNTIME
    ; User-only finite long-horizon fixture, no kernel test policy or clock set.
    ; Retain timestamp in a callee-saved register across all waits.
    xor edi,edi
    xor esi,esi
    xor edx,edx
    mov eax,42
    call ipc_demo_call
    mov r13,rax
    mov ebx,30
.runtime_sleep:
    mov edi,100
    xor esi,esi
    xor edx,edx
    mov eax,41
    call ipc_demo_call
    test rax,rax
    jnz ipc_demo_bad
    dec ebx
    jnz .runtime_sleep
    xor edi,edi
    mov eax,42
    call ipc_demo_call
    cmp rax,r13
    jb ipc_demo_bad
    sub rax,r13
    cmp rax,3000
    jb ipc_demo_bad
%endif
%if X86_64_NATIVE_HEAP
    call heap_demo
    lea r15,[rax+4000]
%endif
    mov rdi, r15
    xor eax, eax
    mov ecx, 32
    rep stosq
%ifdef IPC_DEMO_BULK
    lea rbx, [rel bulk_demo_buffer]
%endif
    mov dword [IPC_DEMO_MESSAGE], 1
    mov dword [IPC_DEMO_MESSAGE+4], 140
    mov dword [IPC_DEMO_MESSAGE+8], 4
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
%ifdef IPC_DEMO_BULK
    call bulk_demo_negative
%endif
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
    lea rsi, [rel ipc_demo_readonly_message]
    xor edx, edx
    mov eax, 54
    call ipc_demo_call
    cmp rax, -14
    jne ipc_demo_bad
    mov rsi, IPC_DEMO_MESSAGE
    mov eax, 51
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov eax, r12d
    and eax, 2
    add eax, 0xa5
    cmp [IPC_DEMO_MESSAGE+12], al
    jne ipc_demo_bad
    xor r14d, r14d
.fill:
    mov eax, r12d
    and eax, 2
    shl eax, 4
    add eax, r14d
    mov [IPC_DEMO_MESSAGE+12], al
    mov edi, r13d
    mov rsi, IPC_DEMO_MESSAGE
    xor edx, edx
    mov eax, 53
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    inc r14d
    cmp r14d, IPC_DEMO_DEPTH
    jb .fill
    inc byte [IPC_DEMO_MESSAGE+12]
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
    cmp byte [IPC_DEMO_MESSAGE+12], 0xee
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
    mov [IPC_DEMO_MESSAGE+12], al
.discover:
    mov edi, r13d
    mov rsi, IPC_DEMO_MESSAGE
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
    mov rsi, IPC_DEMO_MESSAGE
    xor edx, edx
    mov eax, 51
    call ipc_demo_call
    test rax, rax
    jnz ipc_demo_bad
    mov eax, r12d
    and eax, 2
    shl eax, 4
    add eax, r14d
    cmp [IPC_DEMO_MESSAGE+12], al
    jne ipc_demo_bad
    inc r14d
    cmp r14d, IPC_DEMO_DEPTH+1
    jb .drain
    mov byte [IPC_DEMO_MESSAGE+12], 0xee
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
    mov rsi, IPC_DEMO_MESSAGE
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
%ifdef IPC_DEMO_BULK
    call bulk_demo_prepare
%endif
    inc dword [r15+160]
ipc_demo_transport_call:
    xor r10d, r10d
    xor r8d, r8d
    xor r9d, r9d
    syscall
    FP_CHECK
    ret
align 4
ipc_demo_readonly_message:
    dd 1,140,0
    ; The following text bytes complete the readable140-byte range; content
    ; is irrelevant because the valid header must be denied write access.
%if X86_64_NATIVE_HEAP
%include "arch/x86_64/user/heap_demo.inc"
%endif
