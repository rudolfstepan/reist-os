; Pure SysV protected capability planner. No port IO or ambient task state.
; Service64={root,service,epoch,fenced,inverses}; proposal72 adds lease child.
global native_terminal_service_shape64,native_terminal_service_plan64
global native_terminal_service_retire64
native_terminal_service_seal64:
    xor r10d,r10d
.next:
    mov rax,[rdi+r10]
    not rax
    mov [rdi+r10+32],rax
    add r10d,8
    cmp r10d,32
    jb .next
    xor eax,eax
    ret
native_terminal_service_shape64:
    xor r10d,r10d
.next:
    mov rax,[rdi+r10]
    not rax
    cmp [rdi+r10+32],rax
    jne .bad
    add r10d,8
    cmp r10d,32
    jb .next
    cmp qword [rdi+24],1
    ja .bad
    bt qword [rdi+16],63
    jc .bad
    mov rax,[rdi]
    test rax,rax
    jz .empty
    test eax,eax
    jnz .bad
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .bad
    mov rax,[rdi+8]
    cmp eax,2
    jb .bad
    cmp eax,7
    ja .bad
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .bad
    cmp qword [rdi+16],0
    je .bad
    jmp .good
.empty:
    cmp qword [rdi+8],0
    jne .bad
    cmp qword [rdi+24],1
    jne .bad
.good: mov eax,1
    ret
.bad: xor eax,eax
    ret

; RDI service, RSI lease, RDX view72, RCX request24, R8 proposal72,
; R9 exact old-reaped flag. Inputs and output remain untouched on every error.
native_terminal_service_plan64:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    sub rsp,40
    mov r12,rdi
    mov r13,rsi
    mov r14,rdx
    mov r15,rcx
    mov rbx,r8
    mov rbp,r9
    call native_terminal_service_shape64
    test eax,eax
    jz .corrupt
    mov rdi,r13
    call native_terminal_shape64
    test eax,eax
    jz .corrupt
    mov rax,[r14+16]
    cmp [r13],rax
    jne .corrupt
    cmp qword [r12+24],0
    jne .request
    cmp [r12],rax
    jne .corrupt
    mov rax,[r13+8]
    test rax,rax
    jz .request
    cmp [r12+8],rax
    jne .corrupt
.request:
    cmp dword [r15],1
    jne .invalid
    cmp dword [r15+4],24
    jne .invalid
    cmp dword [r15+12],0
    jne .invalid
    mov eax,[r15+8]
    dec eax
    cmp eax,6
    ja .invalid
    cmp dword [r15+8],2
    je .target_shape
    cmp dword [r15+8],6
    jae .target_shape
    cmp qword [r15+16],0
    jne .invalid
    jmp .lease_shape
.target_shape:
    mov eax,[r15+16]
    test eax,eax
    jle .invalid
    cmp [r15+20],eax
    jne .stale
.lease_shape:
    cmp qword [r13],0
    je .denied
    cmp qword [r13+16],0
    jne .io_error
    cmp dword [r15+8],6
    jae .administration
    cmp dword [r15+8],4
    je .acquire
    cmp qword [r12+24],0
    jne .ordinary
    mov rax,[r14]
    cmp [r12],rax
    jne .ordinary
    cmp dword [r15+8],5
    je .again
    cmp dword [r15+8],2
    jne .ordinary
    mov rax,[r12+8]
    cmp [r14+24],rax
    jne .busy
.ordinary:
    mov rdi,r13
    mov rsi,r14
    mov rdx,r15
    lea rcx,[rbx+64]
    call native_terminal_plan64
    test rax,rax
    jnz .return
    call .copy
    cmp dword [r15+8],3
    jne .success
    mov rax,[r14]
    cmp [r12+8],rax
    jne .success
    mov qword [rbx+24],1
    jmp .seal
.administration:
    mov eax,[r15+16]
    test eax,eax
    jle .invalid
    cmp [r15+20],eax
    jne .stale
    mov rax,[r13]
    cmp [r14],rax
    jne .denied
    cmp qword [r14+8],0
    jne .corrupt
    cmp dword [r15+8],7
    je .revoke
    cmp qword [r12+24],1
    jne .busy
    cmp rbp,1
    jne .denied
    cmp qword [r13+8],0
    jne .busy
    mov rax,0x7fffffffffffffff
    cmp [r12+16],rax
    je .overflow
    ; Existing root-to-own-live-child and terminal profile admission.
    mov rax,[r15]
    mov [rsp],rax
    mov rax,[r15+8]
    mov [rsp+8],rax
    mov rax,[r15+16]
    mov [rsp+16],rax
    mov dword [rsp+8],2
    mov rdi,r13
    mov rsi,r14
    mov rdx,rsp
    lea rcx,[rsp+24]
    call native_terminal_plan64
    test rax,rax
    jnz .return
    call .copy
    mov rax,[r13]
    mov [rbx],rax
    mov rax,[rsp+24]
    mov [rbx+8],rax
    inc qword [rbx+16]
    mov qword [rbx+24],0
    mov qword [rbx+64],0
    jmp .seal
.revoke:
    cmp [r12],rax
    jne .stale
    mov rax,[r12+8]
    shr rax,32
    cmp eax,[r15+16]
    jne .stale
    call .copy
    mov qword [rbx+24],1
    mov rax,[r13+8]
    cmp [r12+8],rax
    jne .revoke_child
    xor eax,eax
.revoke_child:
    mov [rbx+64],rax
    jmp .seal
.acquire:
    cmp qword [r15+16],0
    jne .invalid
    cmp qword [r12+24],0
    jne .denied
    mov rax,[r14]
    cmp [r12+8],rax
    jne .denied
    mov rax,[r14+8]
    cmp [r12],rax
    jne .denied
    mov rax,[r14+56]
    and eax,(1<<15)|(1<<20)
    cmp eax,(1<<15)|(1<<20)
    jne .denied
    mov rax,[r14+64]
    btr rax,49
    mov rdx,1<<63
    cmp rax,rdx
    jne .denied
    call .copy
    mov rax,[r12+8]
    mov [rbx+64],rax
    jmp .success
.copy:
    mov rdi,rbx
    mov rsi,r12
    mov ecx,8
    rep movsq
    ret
.seal:
    mov rdi,rbx
    call native_terminal_service_seal64
.success: xor eax,eax
    jmp .return
.corrupt: mov rax,-117
    jmp .return
.invalid: mov rax,-22
    jmp .return
.stale: mov rax,-116
    jmp .return
.denied: mov rax,-13
    jmp .return
.again: mov rax,-11
    jmp .return
.busy: mov rax,-16
    jmp .return
.overflow: mov rax,-75
    jmp .return
.io_error: mov rax,-5
.return:
    add rsp,40
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret

native_terminal_service_retire64:
    call native_terminal_service_shape64
    test eax,eax
    jz .corrupt
    test rsi,rsi
    jz .done
    cmp [rdi],rsi
    je .fence
    cmp [rdi+8],rsi
    jne .done
.fence:
    mov qword [rdi+24],1
    jmp native_terminal_service_seal64
.done: xor eax,eax
    ret
.corrupt: mov rax,-117
    ret
