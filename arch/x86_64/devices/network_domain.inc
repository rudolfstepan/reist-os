; Device32: all user ranges admitted before C or device side effects.
section .text
global native_network_syscall64,native_network_call,native_network_staging
native_network_call64:
    push rbp
    mov rbp,rsp
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    sub rsp,16
    and rsp,-16
    lea rdi,[rel native_network_call]
    mov rax,C_NATIVE_NETWORK_ENTRY
    call rax
    cmp eax,1
    jne scheduler_fail
    mov rax,[rel native_network_call+104]
    lea rsp,[rbp-64]
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbp
    ret
native_network_clear64:
    push rax
    push rcx
    push rdi
    xor eax,eax
    lea rdi,[rel native_network_call]
    mov ecx,(112+1536+8)/8
    rep stosq
    pop rdi
    pop rcx
    pop rax
    ret
native_network_syscall64:
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
    lea rdi,[rel native_network_call]
    mov ecx,8
    rep movsq
    mov rax,[rel native_network_call+40]
    mov [rel native_network_user],rax
    mov edx,[rel native_network_call+48]
    cmp dword [rel native_network_call+8],5
    je .tx
    cmp dword [rel native_network_call+8],6
    jne .relationship
    cmp edx,1536
    jne .invalid
    mov ecx,PF_W
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    jmp .relationship
.tx:
    cmp edx,14
    jb .invalid
    cmp edx,1514
    ja .invalid
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    mov rsi,[rel native_network_user]
    lea rdi,[rel native_network_staging]
    mov ecx,[rel native_network_call+48]
    rep movsb
.relationship:
    cmp dword [rel native_network_call+8],1
    jne .invoke
    mov qword [rel native_network_call+88],3
    call native_network_call64
    mov qword [rel native_network_call+88],0
    test rax,rax
    jz .old_reaped
    mov ecx,eax
    shl ecx,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    add rdi,rcx
    shr rax,32
    cmp qword [rdi+TASK_STATE],TASK_FREE
    je .old_reaped
    cmp [rdi+TASK_GENERATION],rax
    jbe .target
.old_reaped:
    or qword [rel native_network_call+80],1
.target:
    mov rax,[rel native_network_call+16]
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
    mov ecx,[rel native_network_call+16]
    shl ecx,6
    lea rdi,[rel family_records]
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    cmp [rdi+rcx+8],rax
    jne .invoke
    or qword [rel native_network_call+80],2
.invoke:
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    mov [rel native_network_call+64],rax
    mov rax,[rel scheduler_last_tick]
    imul rax,10
    mov [rel native_network_call+72],rax
    lea rax,[rel native_network_staging]
    mov [rel native_network_call+96],rax
    call native_network_call64
    cmp dword [rel native_network_call+8],6
    jne .result
    test rax,rax
    jle .result
    cmp rax,1514
    ja scheduler_fail
    mov rcx,rax
    lea rsi,[rel native_network_staging]
    mov rdi,[rel native_network_user]
    rep movsb
    jmp .result
.pointer: mov rax,-14
    jmp .result
.invalid: mov rax,-22
.result:
    call native_network_clear64
    jmp process_run_resume64
native_network_terminal64:
    push rax
    push rdx
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    mov [rel native_network_call+64],rax
    mov qword [rel native_network_call+88],1
    call native_network_call64
    call native_network_clear64
    pop rdx
    pop rax
    ret
native_network_finish64:
    mov qword [rel native_network_call+88],2
    call native_network_call64
    call native_network_clear64
    ret
native_network_emergency64:
    push rbp
    mov rbp,rsp
    and rsp,-16
    mov qword [rel native_network_call+88],4
    lea rdi,[rel native_network_call]
    mov rax,C_NATIVE_NETWORK_ENTRY
    call rax
    mov rsp,rbp
    pop rbp
    ret
section .bss
alignb 8
native_network_call: resb 112
native_network_staging: resb 1536
native_network_user: resq 1
section .text
