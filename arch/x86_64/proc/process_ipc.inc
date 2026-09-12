; Private IPC binding v2,2136-byte request in a2144-byte scrubbed stack slot.
; C owns copied messages and
; capabilities; this adapter alone admits user memory and scheduler effects.
; All calls are serialized IF0; no suspended C frame or second wait node.

process_ipc_call64:
    push rbp
    mov rbp, rsp
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    and rsp, -16
    mov r11, C_NATIVE_IPC_ENTRY
    call r11
    lea rsp, [rbp-64]
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbp
    cmp eax, 1
    jne scheduler_fail
    ret

process_ipc_zero64:
    push rax
    push rcx
    push rdi
    mov rdi, r13
    xor eax, eax
    mov ecx, 2144/8
    rep stosq
    pop rdi
    pop rcx
    pop rax
    ret

; EDI operation, ESI slot, RDX generation. No request input for lifecycle.
process_ipc_service64:
    push r13
    sub rsp, 2144
    mov r13, rsp
    call process_ipc_zero64
    mov r8, r13
    mov ecx, [rel scheduler_last_tick]
    call process_ipc_call64
    call process_ipc_ready64
    call process_ipc_zero64
    add rsp, 2144
    pop r13
    ret

; Publish only newly completed waiters. A C completion does not copy to a
; different address space; the owner consumes it when next dispatched.
process_ipc_ready64:
    push rbx
    push r12
    push r14
    push r15
    mov r15, [r13+56]
    test r15, ~15
    jnz scheduler_fail
    xor ebx, ebx
.next:
    bt r15, rbx
    jnc .skip
    mov eax, ebx
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    cmp qword [r12+TASK_STATE], TASK_BLOCKED
    jne scheduler_fail
    mov rsi, [r12+TASK_GENERATION]
    lea rax, [rel process_run_generations]
    cmp [rax+rbx*4], esi
    jne scheduler_fail
    lea r14, [rel scheduler_deadline_entries]
    xor ecx, ecx
.find:
    cmp [r14+8], esi
    je .found
    add r14, 16
    inc ecx
    cmp ecx, 4
    jb .find
    jmp scheduler_fail
.found:
    cmp [r14+12], bl
    jne scheduler_fail
    mov rdx, [r14]
    mov edi, ebx
    mov r9d, 1
    mov eax, 3
    call scheduler_queue_apply64
    test eax, eax
    jz scheduler_fail
    mov qword [r12+TASK_STATE], TASK_READY
    call scheduler_runqueue_enqueue64
    test eax, eax
    jz scheduler_fail
.skip:
    inc ebx
    cmp ebx, 4
    jb .next
    pop r15
    pop r14
    pop r12
    pop rbx
    ret

; Current CR3 and task have been published by the shared dispatcher.
process_ipc_take64:
    push r11
    push r12
    push r13
    mov r12, r11
    sub rsp, 2144
    mov r13, rsp
    call process_ipc_zero64
    mov edi, 3
    mov esi, [rel scheduler_current_slot]
    mov rdx, [r12+TASK_GENERATION]
    mov ecx, [rel scheduler_last_tick]
    mov r8, r13
    call process_ipc_call64
    mov rax, [r13+40]
    cmp rax, -4095
    je .done
    mov [r12+TASK_RAX], rax
    call process_ipc_copyout64
.done:
    call process_ipc_zero64
    add rsp, 2144
    pop r13
    pop r12
    pop r11
    ret

process_ipc_copyout64:
    cmp qword [r13+40], 0
    jne .done
    cmp qword [r13], 49
    je .handle
    cmp qword [r13], 51
    je .message
    cmp qword [r13], 54
    jne .done
.message:
    mov rax, [r13+16]
    mov rdx, [r13+2128]
    mov ecx, PF_W
    call process_ipc_validate64
    test eax, eax
    jz scheduler_fail
    mov rdi, [r13+16]
    lea rsi, [r13+64]
    mov rcx, [r13+2128]
    rep movsb
.message_written:
    ret
.handle:
    mov rax, [r13+8]
    mov edx, 4
    mov ecx, PF_W
    call scheduler_validate_shell_ipc_buffer64
    test eax, eax
    jz scheduler_fail
    mov rdi, [r13+8]
    mov eax, [r13+2124]
    mov [rdi], eax
.done:
    ret

process_ipc_syscall64:
    ; Profile/context admission has already run; unused registers still need
    ; rejecting before reading a message or changing endpoint ownership.
    mov rax, [rel syscall_r10]
    or rax, [rel syscall_r8]
    or rax, [rel syscall_r9]
    jnz process_run_syscall64.invalid
    sub rsp, 2144
    mov r13, rsp
    call process_ipc_zero64
    mov rax, [rel syscall_rax]
    mov [r13], rax
    mov rax, [rel syscall_rdi]
    mov [r13+8], rax
    mov rax, [rel syscall_rsi]
    mov [r13+16], rax
    mov rax, [rel syscall_rdx]
    mov [r13+24], rax
    cmp qword [r13], 49
    je .create
    cmp qword [r13], 52
    je .call
    cmp qword [r13], 55
    je .call
    cmp qword [r13], 58
    je .call
    mov rax, [r13+16]
    mov edx, 12
    mov ecx, PF_R
    call process_ipc_validate64
    test eax, eax
    jz .pointer
    mov rsi, [r13+16]
    lea rdi, [r13+64]
    mov ecx, 12
    rep movsb
    cmp dword [r13+64], 1
    je .v1
    cmp dword [r13+64], 2
    jne .invalid
    cmp dword [r13+68], 2060
    jne .invalid
    mov edx, 2060
    jmp .capacity
.v1:
    cmp dword [r13+68], 140
    jne .invalid
    mov edx, 140
.capacity:
    mov [r13+2128], rdx
    mov rax, [r13+16]
    mov ecx, PF_R
    call process_ipc_validate64
    test eax, eax
    jz .pointer
    cmp qword [r13], 51
    je .write
    cmp qword [r13], 54
    jne .copy
.write:
    mov rax, [r13+16]
    mov ecx, PF_W
    call process_ipc_validate64
    test eax, eax
    jz .pointer
.copy:
    mov rsi, [r13+16]
    lea rdi, [r13+64]
    mov rcx, [r13+2128]
    rep movsb
    jmp .call
.create:
    mov rax, [r13+8]
    mov edx, 4
    mov ecx, PF_W
    call scheduler_validate_shell_ipc_buffer64
    test eax, eax
    jz .pointer
.call:
    mov edi, 1
    mov esi, [rel scheduler_current_slot]
    mov rdx, [r12+TASK_GENERATION]
    mov ecx, [rel scheduler_last_tick]
    mov r8, r13
    call process_ipc_call64
    cmp qword [r13+40], -4095
    je .block
    call process_ipc_ready64
    call process_ipc_copyout64
    mov rax, [r13+40]
    jmp .return
.pointer:
    mov rax, -14
    jmp .return
.invalid:
    mov rax, -22
.return:
    call process_ipc_zero64
    add rsp, 2144
    jmp process_run_resume64
.block:
    cmp qword [r13+56], 0
    jne scheduler_fail
    call scheduler_save_syscall_context64
    mov qword [r12+TASK_RAX], 0
    mov qword [r12+TASK_STATE], TASK_BLOCKED
    mov edi, [rel scheduler_current_slot]
    mov rsi, [r12+TASK_GENERATION]
    mov rdx, [r13+48]
    mov eax, 1
    mov r9d, 1
    call scheduler_queue_apply64
    test eax, eax
    jz scheduler_fail
    call process_ipc_zero64
    add rsp, 2144
    jmp process_run_dispatch64

; Only explicit fixed ABI capacities; generic helper retains all registers
; except RAX and checks the executing generation/current CR3 on every page.
process_ipc_validate64:
    cmp rdx, 12
    je .rights
    cmp rdx, 140
    je .rights
    cmp rdx, 2060
    jne .invalid
.rights:
    cmp ecx, PF_R
    je .valid
    cmp ecx, PF_W
    jne .invalid
.valid:
    jmp scheduler_validate_shell_range64
.invalid:
    xor eax, eax
    ret
