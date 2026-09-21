; Serialized IF0 adapter. Only fixed capability, identity and lease mediation.
%include "arch/x86_64/proc/terminal_service_core.inc"
global native_terminal_service_state,native_terminal_service_proposal,native_terminal_service_acquisitions
native_terminal_service_validate64:
    lea rdi,[rel native_terminal_service_state]
    call native_terminal_service_shape64
    test eax,eax
    jz scheduler_fail
    cmp qword [rdi+24],0
    jne .done
    mov rax,[rdi]
    cmp [rel native_terminal_state],rax
    jne scheduler_fail
    mov rdx,[rdi+8]
    mov ecx,edx
    shl ecx,6
    lea r8,[rel family_records]
    cmp [r8+rcx],rdx
    jne scheduler_fail
    cmp [r8+rcx+8],rax
    jne scheduler_fail
    cmp qword [r8+rcx+40],2
    jne scheduler_fail
    mov rax,[rel native_terminal_state+8]
    test rax,rax
    jz .done
    cmp rax,rdx
    jne scheduler_fail
.done: mov eax,1
    ret

; Same adapter arguments as native_terminal_plan64; protected proposal is private.
native_terminal_service_runtime_plan64:
    push rbx
    push r12
    push r13
    push r14
    sub rsp,8
    mov rbx,rcx
    mov r12,rdi
    mov r13,rsi
    mov r14,rdx
    call native_terminal_service_validate64
    mov r9d,1
    mov rax,[rel native_terminal_service_state+8]
    test rax,rax
    jz .invoke
    mov ecx,eax
    shl ecx,NATIVE_TASK_SHIFT
    lea r8,[rel scheduler_tasks]
    cmp qword [r8+rcx+TASK_STATE],TASK_FREE
    je .invoke
    shr rax,32
    cmp [r8+rcx+TASK_GENERATION],rax
    ja .invoke
    xor r9d,r9d
.invoke:
    lea rdi,[rel native_terminal_service_state]
    mov rsi,r12
    mov rdx,r13
    mov rcx,r14
    lea r8,[rel native_terminal_service_proposal]
    call native_terminal_service_plan64
    test rax,rax
    jnz .done
    mov rdx,[rel native_terminal_service_proposal+64]
    mov [rbx],rdx
.done:
    add rsp,8
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

native_terminal_service_publish64:
    lea rdi,[rel native_terminal_service_state]
    lea rsi,[rel native_terminal_service_proposal]
    mov ecx,8
    repe cmpsq
    jne .transition
    mov rax,[rel native_terminal_state+8]
    cmp [rel native_terminal_service_proposal+64],rax
    jne .transition
    xor eax,eax
    ret
.transition:
    call native_terminal_drain64
    test rax,rax
    jnz .failed
    lea rdi,[rel native_terminal_service_state]
    lea rsi,[rel native_terminal_service_proposal]
    mov ecx,8
    rep movsq
    mov rax,[rel native_terminal_service_proposal+64]
    mov [rel native_terminal_state+8],rax
    xor eax,eax
    ret
.failed:
    lea rdi,[rel native_terminal_service_state]
    mov qword [rdi+24],1
    call native_terminal_service_seal64
    mov rax,-5
    ret
native_terminal_service_scrub64:
    push rax
    lea rdi,[rel native_terminal_service_proposal]
    xor eax,eax
    mov ecx,9
    rep stosq
    pop rax
    ret
native_terminal_service_io64:
    call native_terminal_service_validate64
    cmp qword [rel native_terminal_service_state+24],0
    jne .allowed
    cmp qword [rel syscall_rax],15
    jne .allowed
    cmp dword [rel scheduler_current_slot],0
    jne .allowed
    mov rax,-11
    ret
.allowed: xor eax,eax
    ret
native_terminal_service_finish64:
    call native_terminal_service_validate64
    cmp qword [rel native_terminal_service_state+24],1
    jne scheduler_fail
    lea rsi,[rel native_terminal_service_proposal]
    mov ecx,9
.scratch:
    cmp qword [rsi],0
    jne scheduler_fail
    add rsi,8
    loop .scratch
    lea rdi,[rel native_terminal_service_state]
    mov qword [rdi],0
    mov qword [rdi+8],0
    jmp native_terminal_service_seal64
section .data
align 8
native_terminal_service_state: dq 0,0,0,1,-1,-1,-1,-2
native_terminal_service_acquisitions: dq 0
section .bss
alignb 8
native_terminal_service_proposal: resq 9
section .text
