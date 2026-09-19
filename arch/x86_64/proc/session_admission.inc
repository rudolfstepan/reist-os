; NativeSession-v1 pure SysV bounded admission. RDI seven aligned qwords,
; RSI INIT1/CHECK2/CHARGE3, RDX exact root generation, RCX monotonic10ms tick.
; Returns1 admitted,2 exhausted,0 invalid. Invalid/exhausted/CHECK never write.
; Layout: generation,period100,anchor,last,window-spent,total-spent,version1.
global session_admission64
session_admission64:
    test rdi,rdi
    jz .bad
    test rdi,7
    jnz .bad
    test rdx,rdx
    jz .bad
    cmp rdx,0x7fffffff
    ja .bad
    mov rax,rcx
    shr rax,60
    jnz .bad
    cmp esi,1
    jne .existing
    cmp rsi,1
    jne .bad
    mov rax,[rdi]
    or rax,[rdi+8]
    or rax,[rdi+16]
    or rax,[rdi+24]
    or rax,[rdi+32]
    or rax,[rdi+40]
    or rax,[rdi+48]
    jnz .bad
    mov [rdi],rdx
    mov qword [rdi+8],100
    mov [rdi+16],rcx
    mov [rdi+24],rcx
    mov qword [rdi+48],1
    jmp .ok
.existing:
    cmp rsi,2
    je .validate
    cmp rsi,3
    jne .bad
.validate:
    cmp [rdi],rdx
    jne .bad
    cmp qword [rdi+8],100
    jne .bad
    cmp qword [rdi+48],1
    jne .bad
    mov r8,[rdi+16]
    mov rax,[rdi+24]
    cmp rax,r8
    jb .bad
    cmp rax,rcx
    ja .bad
    sub rax,r8
    cmp rax,100
    jae .bad
    mov r9,[rdi+32]
    cmp r9,8
    ja .bad
    mov rax,[rdi+40]
    cmp rax,0x7fffffff
    ja .bad
    cmp r9,rax
    ja .bad
    cmp esi,2
    je .ok
    cmp rax,0x7fffffff
    je .full
    mov rax,rcx
    sub rax,r8
    cmp rax,100
    jb .same
    ; Advance by whole windows, no loop and no credit for unused windows.
    xor edx,edx
    mov r9d,100
    div r9
    mov r8,rcx
    sub r8,rdx
    xor r9d,r9d
.same:
    cmp r9,8
    je .full
    inc r9
    mov [rdi+16],r8
    mov [rdi+24],rcx
    mov [rdi+32],r9
    inc qword [rdi+40]
.ok:
    mov eax,1
    ret
.full:
    mov eax,2
    ret
.bad:
    xor eax,eax
    ret

%ifdef REIST_NATIVE_LIFECYCLE
; Runtime adapter preserves the construction/validation caller's registers.
; RDI operation; exact family owner and cumulative mirror are kernel-owned.
family_session_apply64:
    push rdi
    push rsi
    push rdx
    push rcx
    push r8
    push r9
    push r10
    push r11
    mov rsi,rdi
    lea rdi,[rel family_session_window]
    mov rax,[rel family_records+48]
    cmp [rdi+40],rax
    jne .bad
    mov rdx,[rel family_records]
    test edx,edx
    jnz .bad
    shr rdx,32
    mov rcx,[rel scheduler_last_tick]
    call session_admission64
    jmp .done
.bad:
    xor eax,eax
.done:
    pop r11
    pop r10
    pop r9
    pop r8
    pop rcx
    pop rdx
    pop rsi
    pop rdi
    ret
%endif
