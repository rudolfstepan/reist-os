; Existing PROCESS_IDENTITY114/v1, explicit native shell-session root only.
; Pure lookup: RDI eight tasks, RSI eight families, RDX root0 handle,
; RCX requested positive PID/generation (zero=self). No writes, bounded8 slots.
global native_identity_lookup64
native_identity_lookup64:
    test rdx,rdx
    jz .denied
    test edx,edx
    jnz .denied
    mov r8,rdx
    shr r8,32
    cmp r8,0x7fffffff
    ja .denied
    cmp rcx,0x7fffffff
    ja .invalid
    test rdi,rdi
    jz .invalid
    test rsi,rsi
    jz .invalid
    cmp [rsi],rdx
    jne .corrupt
    cmp [rdi+TASK_GENERATION],r8
    jne .corrupt
    cmp qword [rdi+TASK_STATE],TASK_RUNNING
    jne .corrupt
    cmp qword [rsi+40],1
    jne .corrupt
    test rcx,rcx
    cmovz rcx,r8
    xor r9d,r9d
.slot:
    cmp [rdi+TASK_GENERATION],rcx
    jne .next
    mov rax,[rdi+TASK_STATE]
    cmp rax,TASK_READY
    je .live
    cmp rax,TASK_RUNNING
    je .live
    cmp rax,TASK_BLOCKED
    jne .missing
.live:
    mov rax,rcx
    shl rax,32
    or rax,r9
    cmp [rsi],rax
    jne .corrupt
    test r9d,r9d
    jz .found
    cmp [rsi+8],rdx
    jne .denied
    cmp qword [rsi+40],2
    jne .corrupt
.found:
    mov rax,rcx
    ret
.next:
    add rdi,1<<NATIVE_TASK_SHIFT
    add rsi,64
    inc r9d
    cmp r9d,NATIVE_POOL_TASKS
    jb .slot
.missing: mov rax,-3
    ret
.denied: mov rax,-13
    ret
.invalid: mov rax,-22
    ret
.corrupt: mov rax,-117
    ret

%ifdef REIST_NATIVE_SHELL_SESSION
native_identity_syscall64:
    mov rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz .invalid
    cmp qword [rel syscall_rsi],0x7fffffff
    ja .invalid
    cmp dword [rel scheduler_current_slot],0
    jne .denied
    mov rax,[rel syscall_rdi]
    test rax,rax
    jz .invalid
    mov edx,16
    mov ecx,PF_W
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    lea rdi,[rel scheduler_tasks]
    lea rsi,[rel family_records]
    mov rdx,[rel family_records]
    mov rcx,[rel syscall_rsi]
    call native_identity_lookup64
    cmp rax,-117
    je scheduler_fail
    test rax,rax
    js process_run_resume64
    mov rdi,[rel syscall_rdi]
    mov rdx,(16<<32)|1
    mov [rdi],rdx
    mov [rdi+8],eax
    mov [rdi+12],eax
    xor eax,eax
    jmp process_run_resume64
.invalid: mov rax,-22
    jmp process_run_resume64
.denied: mov rax,-13
    jmp process_run_resume64
.pointer: mov rax,-14
    jmp process_run_resume64
%endif
