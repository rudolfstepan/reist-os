; Fixed input transport; PS/2 protocol and parsing remain in Ring3.
%include "arch/x86_64/devices/input_core.inc"
global native_input_syscall64,native_input_state,native_input_transfers,native_input_finishes
native_input_syscall64:
    lea rdi,[rel native_input_state]
    call native_input_core_admit64
    test rax,rax
    jnz scheduler_fail
    mov rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz .invalid
    mov rax,[rel syscall_rsi]
    mov edx,64
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    mov rsi,[rel syscall_rsi]
    lea rdi,[rel native_input_request]
    mov ecx,8
    rep movsq
.shape_ready:
    xor r8d,r8d
    cmp dword [rel native_input_request+8],1
    jne .invoke
    ; No bind may precede old reap, even when the old generation is fenced.
    mov rax,[rel native_input_state]
    test rax,rax
    jz .old_reaped
    mov ecx,eax
    cmp ecx,2
    jb scheduler_fail
    cmp ecx,7
    ja scheduler_fail
    shl ecx,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    add rdi,rcx
    shr rax,32
    cmp qword [rdi+TASK_STATE],TASK_FREE
    je .old_reaped
    cmp [rdi+TASK_GENERATION],rax
    jbe .target
.old_reaped:
    or r8d,1
.target:
    mov rax,[rel native_input_request+16]
    mov ecx,eax
    cmp ecx,2
    jb .invoke
    cmp ecx,7
    ja .invoke
    shl ecx,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    add rdi,rcx
    shr rax,32
    cmp [rdi+TASK_GENERATION],rax
    jne .invoke
    cmp qword [rdi+TASK_STATE],TASK_READY
    je .parent
    cmp qword [rdi+TASK_STATE],TASK_BLOCKED
    jne .invoke
.parent:
    mov ecx,[rel native_input_request+16]
    shl ecx,6
    lea rdi,[rel family_records]
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    cmp [rdi+rcx+8],rax
    jne .invoke
    or r8d,2
.invoke:
    lea rdi,[rel native_input_state]
    lea rsi,[rel native_input_request]
    mov rdx,[r12+TASK_GENERATION]
    shl rdx,32
    mov eax,[rel scheduler_current_slot]
    or rdx,rax
    mov rcx,[rel scheduler_last_tick]
    imul rcx,10
    call native_input_core_apply64
    cmp rax,-84
    je scheduler_fail
    test rax,rax
    jnz .result
    mov ecx,[rel native_input_request+8]
    cmp ecx,3
    jb .result
    cmp ecx,5
    ja .result
    mov dx,0x64
    in al,dx
    movzx r10d,al
    cmp ecx,3
    je .read
    test al,2
    jnz .again
    mov eax,[rel native_input_request+40]
    cmp ecx,4
    je .write
    mov dx,0x60
.write:
    out dx,al
    inc qword [rel native_input_transfers]
    lea rdi,[rel native_input_state]
    mov esi,ecx
    mov edx,[rel native_input_request+40]
    call native_input_core_written64
    jmp .result
.read:
    test al,1
    jz .again
    mov dx,0x60
    in al,dx
    movzx eax,al
    shl r10d,8
    or eax,r10d
    inc eax
    inc qword [rel native_input_transfers]
    jmp .result
.again: mov rax,-11
    jmp .result
.invalid: mov rax,-22
    jmp .result
.pointer: mov rax,-14
.result:
%ifdef REIST_NATIVE_DESKTOP_CPU
    mov r8d,[rel native_input_request+8]
%endif
    push rax
    lea rdi,[rel native_input_request]
    xor eax,eax
    mov ecx,8
    rep stosq
    pop rax
%ifdef REIST_NATIVE_DESKTOP_CPU
    ; Only completed/empty reads share the existing bounded query burst.
    ; All request checks and scratch erasure precede this return decision.
    cmp r8d,3
    jne .dispatch_result
    cmp rax,-11
    je .read_return
    lea rdx,[rax-1]
    cmp rdx,65535
    ja .dispatch_result
.read_return:
    jmp query_resume64
.dispatch_result:
%endif
    jmp process_run_resume64

native_input_terminal64:
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    lea rdi,[rel native_input_state]
    mov rsi,[r12+TASK_GENERATION]
    shl rsi,32
    mov eax,[rel scheduler_current_slot]
    or rsi,rax
    call native_input_core_fence64
    test rax,rax
    jnz scheduler_fail
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    ret

native_input_finish64:
    lea rdi,[rel native_input_state]
    call native_input_core_admit64
    test rax,rax
    jnz scheduler_fail
    cmp qword [rdi+24],1
    jne scheduler_fail
    mov r10,[rdi+16]
    call native_input_core_init64
    mov [rdi+16],r10
    call native_input_core_seal64
    inc qword [rel native_input_finishes]
    ret

section .data
align 8
native_input_state:
    dq 0,0,0,1,0,0,0,0
    dq -1,-1,-1,-2,-1,-1,-1,-1
native_input_transfers: dq 0
native_input_finishes: dq 0
section .bss
alignb 8
native_input_request: resb 64
section .text
