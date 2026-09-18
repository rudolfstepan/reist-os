; Already generation/profile-admitted native call, IF0, current task in R12.
; Minimal initialized-UART byte mediation. No setup/poll loop/driver policy.
native_console_syscall64:
    cmp dword [rel scheduler_current_slot],0
    jne .denied
    mov rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz .invalid
    mov ebx,REIST_SYS_READ
    mov ecx,PF_W
    xor edx,edx
    cmp qword [rel syscall_rax],REIST_SYS_READ
    je .descriptor
    cmp qword [rel syscall_rax],REIST_SYS_WRITE
    jne .invalid
    mov ebx,REIST_SYS_WRITE
    mov ecx,PF_R
    mov edx,1
.descriptor:
    cmp [rel syscall_rdi],rdx
    jne .badfd
    mov r13,[rel syscall_rdx]
    cmp r13,64
    ja .invalid
    test r13,r13
    jz .zero
    mov r14,[rel syscall_rsi]
    mov rax,r14
    mov rdx,r13
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    xor r15d,r15d
.byte:
    mov dx,COM1_LSR
    in al,dx
    test al,0x1e
    jnz .io_error
    cmp ebx,REIST_SYS_READ
    jne .write
    test al,1
    jz .again
    mov dx,COM1_DATA
    in al,dx
    mov [r14+r15],al
    jmp .progress
.write:
    test al,0x20
    jz .again
    mov al,[r14+r15]
    mov dx,COM1_DATA
    out dx,al
.progress:
    inc r15
    cmp r15,r13
    jb .byte
.partial:
    mov rax,r15
    jmp process_run_resume64
.again:
    test r15,r15
    jnz .partial
    mov rax,-11
    jmp process_run_resume64
.io_error:
    test r15,r15
    jnz .partial
    mov rax,-5
    jmp process_run_resume64
.zero:
    xor eax,eax
    jmp process_run_resume64
.pointer:
    mov rax,-14
    jmp process_run_resume64
.badfd:
    mov rax,-9
    jmp process_run_resume64
.invalid:
    mov rax,-22
    jmp process_run_resume64
.denied:
    mov rax,-13
    jmp process_run_resume64
