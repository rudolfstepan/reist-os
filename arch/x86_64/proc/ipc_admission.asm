BITS 64
section .text
global reist_x64_ipc_admit
global reist_x64_ipc_plan

; SysV AMD64; pure bounded validation of a kernel-owned snapshot.
reist_x64_ipc_admit:
    test rdi, rdi
    jz .corrupt
    test rdi, 7
    jnz .corrupt
    mov rax, [rdi + 8]
    test rax, rax
    jz .corrupt
    shr rax, 32
    jnz .corrupt
    mov rax, [rdi + 24]
    test rax, ~7
    jnz .corrupt
    mov rcx, [rdi]
    cmp rcx, 50
    jb .unsupported
    cmp rcx, 55
    jbe .operation
    cmp rcx, 58
    jne .unsupported
.operation:
    cmp qword [rdi + 48], 0
    je .bad_handle
    mov rax, [rdi + 32]
    cmp rax, [rdi + 48]
    jne .bad_handle
    cmp qword [rdi + 16], 0
    jne .cap_present
    cmp qword [rdi + 24], 0
    jne .corrupt
    cmp qword [rdi + 40], 0
    jne .corrupt
    jmp .denied
.cap_present:
    cmp qword [rdi + 24], 0
    je .corrupt
    mov rax, [rdi + 16]
    cmp rax, [rdi + 8]
    jne .corrupt
    mov rax, [rdi + 40]
    cmp rax, [rdi + 48]
    jne .corrupt
    mov eax, 1
    cmp ecx, 51
    je .receive_right
    cmp ecx, 54
    je .receive_right
    cmp ecx, 52
    je .control_right
    cmp ecx, 55
    je .control_right
    cmp ecx, 58
    je .arguments
    jmp .rights
.receive_right:
    mov eax, 2
    jmp .rights
.control_right:
    mov eax, 4
.rights:
    test [rdi + 24], rax
    jz .denied
.arguments:
    mov rax, [rdi + 80]
    cmp ecx, 55
    je .delegate
    cmp ecx, 53
    je .timeout
    cmp ecx, 54
    je .timeout
    test rax, rax
    jnz .invalid
    jmp .buffer_or_empty
.delegate:
    cmp rax, 1
    jne .invalid
    cmp qword [rdi + 56], 301 ; existing admitted pair, no new process authority
    jne .invalid
    jmp .ok
.timeout:
    cmp rax, 10 ; existing isolated one-tick REIST profile, not arbitrary ms
    jne .invalid
.buffer_or_empty:
    cmp ecx, 52
    je .empty
    cmp ecx, 58
    je .empty
    mov r8, [rdi + 64]
    test r8, 4095
    jnz .corrupt
    cmp r8, 4096
    jb .corrupt
    mov r10, [rdi + 88]
    cmp r10, 4096
    jb .corrupt
    cmp r10, 65536
    ja .corrupt
    test r10, 4095
    jnz .corrupt
    mov rax, r8
    add rax, r10
    jc .corrupt
    mov rdx, 0x0000800000000000
    cmp rax, rdx
    jae .corrupt
    mov r9, [rdi + 72]
    test r9, r9
    jz .corrupt
    mov rax, r9
    add rax, r10
    jc .corrupt
    mov rax, [rdi + 56]
    sub rax, r8
    jc .pointer
    sub r10, 140
    cmp rax, r10
    ja .pointer
    test rax, 7
    jnz .pointer
    add r9, rax
    cmp dword [r9], 1
    jne .invalid
    cmp dword [r9 + 4], 140
    jne .invalid
    mov eax, [r9 + 8]
    cmp ecx, 51
    je .receive_length
    cmp ecx, 54
    je .receive_length
    cmp eax, 128
    ja .invalid
    jmp .ok
.receive_length:
    test eax, eax
    jnz .invalid
    jmp .ok
.empty:
    cmp qword [rdi + 56], 0
    jne .invalid
.ok:
    mov eax, 1
    ret
.corrupt:
    mov rax, -4096
    ret
.unsupported:
    mov rax, -38
    ret
.bad_handle:
    mov rax, -9
    ret
.denied:
    mov rax, -13
    ret
.invalid:
    mov rax, -22
    ret
.pointer:
    mov rax, -14
    ret

reist_x64_ipc_plan:
    cmp rsi, 15
    ja .corrupt
    test esi, 8
    jnz .closed
    test esi, 2
    jz .receiver
    test esi, 1
    jz .corrupt
.receiver:
    test esi, 4
    jz .op
    test esi, 3
    jnz .corrupt
.op:
    cmp rdi, 50
    je .send
    cmp rdi, 53
    je .send
    cmp rdi, 51
    je .receive
    cmp rdi, 54
    je .receive
    cmp rdi, 52
    je .close
    cmp rdi, 58
    je .release
    mov rax, -38
    ret
.send:
    mov eax, 3
    test esi, 4
    jnz .done
    mov eax, 1
    test esi, 1
    jz .done
    test esi, 2
    jnz .again
    cmp edi, 53
    jne .again
    mov eax, 2
    ret
.receive:
    mov eax, 4
    test esi, 1
    jnz .done
    test esi, 4
    jnz .again
    cmp edi, 54
    jne .again
    mov eax, 5
    ret
.close:
    mov eax, 6
    ret
.release:
    mov eax, 7
.done:
    ret
.closed:
    cmp esi, 8
    jne .corrupt
    cmp rdi, 52
    je .close
    mov rax, -9
    ret
.again:
    mov rax, -11
    ret
.corrupt:
    mov rax, -4096
    ret
