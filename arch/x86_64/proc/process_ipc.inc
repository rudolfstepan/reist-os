%include "arch/x86_64/mm/native_layout.inc"
; Private IPC binding v2,2136-byte request in a2144-byte scrubbed stack slot.
; C owns copied messages and
; capabilities; this adapter alone admits user memory and scheduler effects.
; All calls are serialized IF0; no suspended C frame or second wait node.

; RDI four24-byte records; RSI query/bind/wait/ready/consume/reap/end/audit;
; RDX slot, RCX generation. Return0 invalid,1 success/no-work,2 ready query.
; A value, complement and rotated-XOR word detect one/two-word corruption.
; No writes precede validation of the entire pool and requested transition.
process_ipc_completion_apply64:
    test rdi,rdi
    jz .bad
    test rdi,7
    jnz .bad
    cmp rsi,7
    ja .bad
    cmp rdx,3
    ja .bad
    cmp rcx,0x7fffffff
    ja .bad
    mov r11,0x936da17cb852e40f
    mov r8,rdi
    lea rax,[rdi+96]
.verify:
    mov r9,[r8]
    mov r10,r9
    not r10
    cmp [r8+8],r10
    jne .bad
    mov r10,r9
    rol r10,17
    xor r10,r11
    cmp [r8+16],r10
    jne .bad
    test r9,r9
    js .bad
    mov r10d,r9d
    cmp r10d,3
    ja .bad
    cmp esi,6
    jne .generation
    test r10d,r10d
    jnz .bad
.generation:
    shr r9,32
    jnz .next
    test r10d,r10d
    jnz .bad
.next:
    add r8,24
    cmp r8,rax
    jb .verify
    cmp esi,6
    jae .success
    test rcx,rcx
    jz .bad
    lea r8,[rdx+rdx*2]
    lea r8,[rdi+r8*8]
    mov r9,[r8]
    mov r10,r9
    shr r10,32
    cmp esi,1
    je .bind
    cmp r10,rcx
    jne .bad
    test r9d,r9d
    jz .bad
    test esi,esi
    jz .query
    cmp esi,5
    je .reap
    cmp esi,2
    je .wait
    cmp esi,3
    je .ready
    cmp r9d,3
    jne .bad
    mov eax,1
    jmp .publish
.bind:
    test r9d,r9d
    jnz .bad
    cmp rcx,r10
    jbe .bad
    mov eax,1
    jmp .publish
.wait:
    cmp r9d,1
    jne .bad
    mov eax,2
    jmp .publish
.ready:
    cmp r9d,2
    jne .bad
    mov eax,3
    jmp .publish
.reap:
    xor eax,eax
.publish:
    mov r9,rcx
    shl r9,32
    or r9,rax
    mov [r8],r9
    mov r10,r9
    not r10
    mov [r8+8],r10
    rol r9,17
    xor r9,r11
    mov [r8+16],r9
.success:
    mov eax,1
    ret
.query:
    cmp r9d,1
    je .success
    cmp r9d,3
    jne .bad
    mov eax,2
    ret
.bad:
    xor eax,eax
    ret

; Preserve caller registers except RAX. EAX operation, ESI slot, RDX generation.
process_ipc_completion64:
    push rax
    pushfq
    pop rax
    test eax,512
    jnz scheduler_fail
    pop rax
    push rdi
    push rsi
    push rdx
    push rcx
    push r8
    push r9
    push r10
    push r11
    mov rcx,rdx
    mov edx,esi
    mov esi,eax
    lea rdi,[rel process_ipc_completions]
    call process_ipc_completion_apply64
    pop r11
    pop r10
    pop r9
    pop r8
    pop rcx
    pop rdx
    pop rsi
    pop rdi
    test eax,eax
    jz scheduler_fail
    ret

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
    mov eax,7
    test edi,edi
    jnz .not_bind
    mov eax,1
.not_bind:
    cmp edi,4
    jne .not_reap
    mov eax,5
.not_reap:
    cmp edi,5
    jne .admit
    mov eax,6
.admit:
    call process_ipc_completion64
    push r13
    sub rsp, 2144
    mov r13, rsp
    call process_ipc_zero64
    mov r8, r13
%ifdef REIST_NATIVE_RUNTIME
    mov rcx, [rel scheduler_last_tick]
%else
    mov ecx, [rel scheduler_last_tick]
%endif
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
    shl eax, NATIVE_TASK_SHIFT
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
    push rsi
    mov rdx,rsi
    mov esi,ebx
    mov eax,3
    call process_ipc_completion64
    pop rsi
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
    mov esi,[rel scheduler_current_slot]
    mov rdx,[r12+TASK_GENERATION]
    xor eax,eax
    call process_ipc_completion64
    cmp eax,1
    je .no_work
    sub rsp, 2144
    mov r13, rsp
    call process_ipc_zero64
    mov edi, 3
    mov esi, [rel scheduler_current_slot]
    mov rdx, [r12+TASK_GENERATION]
%ifdef REIST_NATIVE_RUNTIME
    mov rcx, [rel scheduler_last_tick]
%else
    mov ecx, [rel scheduler_last_tick]
%endif
    mov r8, r13
    call process_ipc_call64
    mov rax, [r13+40]
    cmp rax, -4095
    je scheduler_fail
    mov eax,4
    call process_ipc_completion64
    mov rax,[r13+40]
    mov [r12+TASK_RAX], rax
    call process_ipc_copyout64
.done:
    call process_ipc_zero64
    add rsp, 2144
.no_work:
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
    xor eax,eax
    call process_ipc_completion64
    cmp eax,1
    jne scheduler_fail
%ifdef REIST_NATIVE_RUNTIME
    mov rcx, [rel scheduler_last_tick]
%else
    mov ecx, [rel scheduler_last_tick]
%endif
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
    mov eax,2
    call process_ipc_completion64
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

section .data
align 8
process_ipc_completions:
    times 4 dq 0,-1,0x936da17cb852e40f
section .text
