; CPU-window-v1: private fixed records, SysV AMD64, no caller policy/reset.
; RDI budget32, RSI window32, RDX operation, RCX generation, R8 arg, R9 now.
; All input validation precedes writes. Work is constant; no skipped-period loop.
global reist_x64_period_apply
reist_x64_period_apply:
    push rbx
    push r12
    push r13
    push r14
    push r15
    mov rbx,rdx
    mov r12,rcx
    mov r13,r8
    mov r14,r9
    test rdi,rdi
    jz .bad
    test rsi,rsi
    jz .bad
    mov rax,rdi
    or rax,rsi
    test rax,7
    jnz .bad
    lea rax,[rdi+32]
    cmp rax,rdi
    jb .bad
    lea r10,[rsi+32]
    cmp r10,rsi
    jb .bad
    cmp rdi,r10
    jae .disjoint
    cmp rsi,rax
    jb .bad
.disjoint:
    cmp rbx,3
    ja .bad
    mov rax,r12
    shr rax,32
    jnz .bad
    mov rax,1<<60
    cmp r14,rax
    jae .bad
    mov rax,[rsi]
    or rax,[rsi+8]
    or rax,[rsi+16]
    or rax,[rsi+24]
    jnz .periodic
    cmp ebx,1
    jne .legacy
    mov rax,r13
    shr rax,32
    test rax,rax
    jz .legacy
    cmp rax,100
    jne .bad
    test r12,r12
    jz .bad
    mov eax,r13d
    dec rax
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp rax,63
%else
    cmp rax,31
%endif
    ja .bad
    mov rax,[rdi]
    or rax,[rdi+8]
    or rax,[rdi+16]
    or rax,[rdi+24]
    jnz .bad
    mov [rdi],r12
    mov eax,r13d
    mov [rdi+8],rax
    mov qword [rsi],100
    mov [rsi+8],r14
    jmp .okay
.legacy:
    ; Preserve the original core and its finite limits. No periodic metadata
    ; can be hidden by selecting an old CREATE version or bootstrap operation.
    cmp [rdi+24],r14
    ja .bad
    cmp ebx,2
    jne .legacy_call
    cmp r13,r14
    jne .bad
.legacy_call:
    mov rsi,rbx
    mov rdx,r12
    mov rcx,r13
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    jmp reist_x64_budget_apply
.periodic:
    cmp qword [rsi],100
    jne .bad
    test r12,r12
    jz .bad
    cmp [rdi],r12
    jne .bad
    mov rax,[rdi+8]
    dec rax
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp rax,63
%else
    cmp rax,31
%endif
    ja .bad
    cmp [rsi+8],r14
    ja .bad
    cmp ebx,1
    je .bad
    mov rax,[rdi+16]
    test rax,rax
    jnz .used
    mov rax,[rdi+24]
    or rax,[rsi+16]
    or rax,[rsi+24]
    jnz .bad
    jmp .valid
.used:
    mov rax,[rdi+24]
    cmp rax,r14
    ja .bad
    sub rax,[rsi+8]
    jbe .bad
    cmp [rdi+16],rax
    ja .bad
    xor edx,edx
    mov r10d,100
    div r10
    cmp [rsi+16],rax
    jne .bad
    mov r10,[rsi+24]
    test r10,r10
    jz .bad
    cmp r10,[rdi+8]
    ja .bad
    cmp r10,[rdi+16]
    ja .bad
    inc rdx
    cmp r10,rdx
    ja .bad
    ; index <2^60/100 and limit<=64: multiplication cannot overflow64 bits.
    inc rax
    imul rax,[rdi+8]
    cmp [rdi+16],rax
    ja .bad
.valid:
    cmp ebx,2
    je .charge
    test r13,r13
    jnz .bad
    test ebx,ebx
    jz .okay
    cmp ebx,3
    jne .bad
    xor eax,eax
    mov [rdi],rax
    mov [rdi+8],rax
    mov [rdi+16],rax
    mov [rdi+24],rax
    mov [rsi],rax
    mov [rsi+8],rax
    mov [rsi+16],rax
    mov [rsi+24],rax
    jmp .okay
.charge:
    mov r10,[rsi+24]
    cmp r10,[rdi+8]
    jae .charge_bad             ; terminal exhaustion is never replenished
    cmp r13,r14
    jne .charge_bad
    cmp r13,[rdi+24]
    jbe .charge_bad
    mov rax,r13
    sub rax,[rsi+8]
    jbe .charge_bad
    xor edx,edx
    mov r11d,100
    div r11
    cmp rax,[rsi+16]
    jb .charge_bad
    je .same_window
    xor r10d,r10d
.same_window:
    inc r10
    mov r11,[rdi+16]
    inc r11
    mov [rdi+16],r11
    mov [rdi+24],r13
    mov [rsi+16],rax
    mov [rsi+24],r10
    cmp r10,[rdi+8]
    jne .charge_okay
    mov eax,2
    jmp .charge_result
.charge_okay:
    mov eax,1
    jmp .charge_result
.charge_bad:
    xor eax,eax
.charge_result:
    ; Charge-only boundary includes rejected charges with the real EAX=0.
    jmp .return
.okay:
    mov eax,1
    jmp .return
.bad:
    xor eax,eax
.return:
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    ret
