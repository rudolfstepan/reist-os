; Shared production/host SysV core. All storage fixed; no pointer/port effects.
global native_display_core_init64, native_display_core_admit64
global native_display_core_apply64, native_display_core_fence64
global native_display_rectangle64
native_display_rectangle64:
    movzx eax,word [rdi+56]
    test eax,eax
    jz .bad
    cmp eax,64
    ja .bad
    mov ecx,[rdi+48]
    add rcx,rax
    cmp rcx,rsi
    ja .bad
    shl eax,2
    cmp eax,[rdi+60]
    jne .bad
    movzx ecx,word [rdi+58]
    test ecx,ecx
    jz .bad
    cmp ecx,64
    ja .bad
    mov r8d,[rdi+52]
    add r8,rcx
    cmp r8,rdx
    ja .bad
    imul eax,ecx
    ret
.bad:
    xor eax,eax
    ret
native_display_core_init64:
    mov r8,rdi
    xor eax,eax
    mov ecx,8
    rep stosq
    mov rdi,r8
    mov qword [rdi+24],1
    jmp native_display_core_seal64
native_display_core_seal64:
    xor r9d,r9d
.word:
    mov rax,[rdi+r9]
    not rax
    mov [rdi+r9+64],rax
    add r9d,8
    cmp r9d,64
    jb .word
    xor eax,eax
    ret
native_display_core_admit64:
    xor r9d,r9d
.word:
    mov rax,[rdi+r9]
    not rax
    cmp [rdi+r9+64],rax
    jne .bad
    add r9d,8
    cmp r9d,64
    jb .word
    cmp qword [rdi+24],1
    ja .bad
    cmp qword [rdi+48],64
    ja .bad
    cmp qword [rdi+56],1048576
    ja .bad
    mov rax,[rdi+32]
    cmp rax,[rdi+40]
    ja .bad
    mov rax,[rdi+40]
    shr rax,60
    jnz .bad
    bt qword [rdi+16],63
    jc .bad
    mov rax,[rdi]
    test rax,rax
    jz .empty
    cmp eax,2
    jb .bad
    cmp eax,7
    ja .bad
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .bad
    cmp dword [rdi+8],0
    jne .bad
    mov rax,[rdi+8]
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .bad
    cmp qword [rdi+16],0
    je .bad
    xor eax,eax
    ret
.empty:
    cmp qword [rdi+8],0
    jne .bad
    cmp qword [rdi+24],1
    jne .bad
    xor eax,eax
    ret
.bad:
    mov rax,-84
    ret

native_display_core_apply64:
    ; RDI state, RSI pinned request, RDX exact caller, RCX ms, R8 bind flags.
    call native_display_core_admit64
    test rax,rax
    jnz .return
    mov rax,rcx
    shr rax,60
    jnz .corrupt
    cmp rcx,[rdi+40]
    jb .corrupt
%ifdef REIST_NATIVE_DISPLAY_INFO
    cmp dword [rsi],2
    je .info
%endif
    cmp dword [rsi],1
    jne .invalid
    cmp dword [rsi+4],64
    jne .invalid
    cmp dword [rsi+12],0
    jne .invalid
    mov eax,[rsi+8]
    dec eax
    cmp eax,3
    ja .invalid
    cmp eax,2
    je .commit_shape
    mov rax,[rsi+32]
    or rax,[rsi+40]
    or rax,[rsi+48]
    or rax,[rsi+56]
    jnz .invalid
    cmp dword [rsi+8],1
    je .bind
    cmp dword [rsi+8],4
    je .fence
    cmp qword [rsi+24],0
    jne .invalid
    call .owner
    test rax,rax
    jnz .return
    mov rax,[rdi+16]
    ret
%ifdef REIST_NATIVE_DISPLAY_INFO
.info:
    cmp dword [rsi+4],64
    jne .invalid
    cmp dword [rsi+8],5
    jne .invalid
    cmp dword [rsi+12],0
    jne .invalid
    mov rax,[rsi+32]
    or rax,[rsi+40]
    or rax,[rsi+48]
    or rax,[rsi+56]
    jnz .invalid
    call .owner
    test rax,rax
    jnz .return
    mov rax,[rsi+24]
    cmp rax,[rdi+16]
    jne .stale
    xor eax,eax
    ret
%endif
.bind:
    test edx,edx
    jnz .denied
    mov rax,rdx
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .denied
    cmp qword [rsi+24],0
    jne .invalid
    mov rax,[rsi+16]
    cmp eax,2
    jb .invalid
    cmp eax,7
    ja .invalid
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .invalid
    cmp r8,3
    jne .denied
    cmp qword [rdi+24],1
    jne .busy
    mov rax,0x7fffffffffffffff
    cmp [rdi+16],rax
    je .overflow
    mov rax,[rsi+16]
    mov [rdi],rax
    mov [rdi+8],rdx
    inc qword [rdi+16]
    mov qword [rdi+24],0
    mov [rdi+32],rcx
    mov [rdi+40],rcx
    mov qword [rdi+48],0
    mov qword [rdi+56],0
    call native_display_core_seal64
    mov rax,[rdi+16]
    ret
.fence:
    cmp rdx,[rdi+8]
    jne .denied
    mov rax,[rsi+16]
    cmp rax,[rdi]
    jne .stale
    mov rax,[rsi+24]
    cmp rax,[rdi+16]
    jne .stale
    mov qword [rdi+24],1
    mov [rdi+40],rcx
    jmp native_display_core_seal64
.commit_shape:
    movzx eax,word [rsi+56]
    dec eax
    cmp eax,63
    ja .invalid
    movzx eax,word [rsi+58]
    dec eax
    cmp eax,63
    ja .invalid
    movzx eax,word [rsi+56]
    shl eax,2
    cmp eax,[rsi+60]
    jne .invalid
    cmp qword [rsi+40],0
    je .invalid
    call .owner
    test rax,rax
    jnz .return
    mov rax,[rsi+24]
    cmp rax,[rdi+16]
    jne .stale
    mov rax,[rsi+32]
    cmp rax,rcx
    jbe .timeout
    sub rax,rcx
    cmp rax,1000
    ja .invalid
    ; Every shape, identity and deadline check precedes budget publication.
    mov rax,rcx
    sub rax,[rdi+32]
    cmp rax,100
    jb .budget
    mov [rdi+32],rcx
    mov qword [rdi+48],0
    mov qword [rdi+56],0
.budget:
    movzx eax,word [rsi+58]
    imul eax,[rsi+60]
    add rax,[rdi+56]
    cmp rax,1048576
    ja .quota
    cmp qword [rdi+48],64
    jae .quota
    mov [rdi+56],rax
    inc qword [rdi+48]
    mov [rdi+40],rcx
    jmp native_display_core_seal64
.quota:
    mov qword [rdi+24],1
    mov [rdi+40],rcx
    call native_display_core_seal64
    mov rax,-122
    ret
.owner:
    cmp rdx,[rdi]
    jne .denied
    mov rax,[rsi+16]
    cmp rax,rdx
    jne .stale
    cmp qword [rdi+24],0
    jne .denied
    xor eax,eax
    ret
.busy: mov rax,-16
    ret
.overflow: mov rax,-75
    ret
.timeout: mov rax,-110
    ret
.invalid: mov rax,-22
    ret
.stale: mov rax,-116
    ret
.denied: mov rax,-13
    ret
.corrupt: mov rax,-84
.return: ret

native_display_core_fence64:
    ; RDI state, RSI exact retiring handle. Idempotent, never grants authority.
    call native_display_core_admit64
    test rax,rax
    jnz .done
    cmp rsi,[rdi]
    je .fence
    cmp rsi,[rdi+8]
    jne .done
.fence:
    mov qword [rdi+24],1
    jmp native_display_core_seal64
.done: ret
