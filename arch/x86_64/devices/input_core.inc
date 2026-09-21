; Fixed SysV admission shared by production and actual host execution.
global native_input_core_init64,native_input_core_admit64
global native_input_core_apply64,native_input_core_fence64,native_input_core_written64
native_input_core_init64:
    mov r8,rdi
    xor eax,eax
    mov ecx,8
    rep stosq
    mov rdi,r8
    mov qword [rdi+24],1
native_input_core_seal64:
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
native_input_core_admit64:
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
    cmp qword [rdi+56],2
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
    cmp qword [rdi+56],0
    jne .bad
    xor eax,eax
    ret
.bad:
    mov rax,-84
    ret
native_input_core_apply64:
    call native_input_core_admit64
    test rax,rax
    jnz .return
    mov rax,rcx
    shr rax,60
    jnz .corrupt
    cmp rcx,[rdi+40]
    jb .corrupt
    cmp dword [rsi],1
    jne .invalid
    cmp dword [rsi+4],64
    jne .invalid
    mov eax,[rsi+12]
    or rax,[rsi+48]
    or rax,[rsi+56]
    jnz .invalid
    mov eax,[rsi+8]
    dec eax
    cmp eax,5
    ja .invalid
    cmp eax,2
    jb .control
    cmp eax,5
    je .control
    ; All IO belongs to the exact live, unfenced owner.
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
    mov rax,[rsi+40]
    cmp rax,255
    ja .invalid
    cmp dword [rsi+8],3
    jne .write
    test rax,rax
    jnz .invalid
    jmp .charge
.write:
    cmp dword [rsi+8],5
    je .data
    cmp eax,0x60 ; safe configuration prefix also aborts an old prefix
    je .charge
    cmp qword [rdi+56],0
    jne .invalid
    cmp eax,0x20
    je .charge
    cmp eax,0xa7
    je .charge
    cmp eax,0xa8
    je .charge
    cmp eax,0xad
    je .charge
    cmp eax,0xae
    je .charge
    cmp eax,0xd4
    je .charge
    jmp .invalid
.data:
    cmp qword [rdi+56],1
    je .config
    cmp eax,0xf4
    je .charge
    cmp eax,0xf5
    je .charge
    cmp eax,0xf6
    je .charge
    cmp eax,0xff
    je .charge
    jmp .invalid
.config:
    cmp eax,0x40
    je .charge
    cmp eax,0x70
    jne .invalid
.charge:
    mov rax,rcx
    sub rax,[rdi+32]
    cmp rax,100
    jb .budget
    mov [rdi+32],rcx
    mov qword [rdi+48],0
.budget:
    mov [rdi+40],rcx
    cmp qword [rdi+48],64
    jae .quota
    inc qword [rdi+48]
    jmp native_input_core_seal64
.quota:
    mov qword [rdi+24],1
    mov qword [rdi+56],0
    call native_input_core_seal64
    mov rax,-122
    ret
.control:
    mov rax,[rsi+32]
    or rax,[rsi+40]
    jnz .invalid
    cmp dword [rsi+8],1
    je .bind
    cmp dword [rsi+8],6
    je .fence
    cmp qword [rsi+24],0
    jne .invalid
    call .owner
    test rax,rax
    jnz .return
    mov rax,[rdi+16]
    ret
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
    call native_input_core_seal64
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
    mov [rdi+40],rcx
    mov qword [rdi+24],1
    mov qword [rdi+56],0
    jmp native_input_core_seal64
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
.invalid: mov rax,-22
    ret
.denied: mov rax,-13
    ret
.stale: mov rax,-116
    ret
.timeout: mov rax,-110
    ret
.busy: mov rax,-16
    ret
.overflow: mov rax,-75
    ret
.corrupt: mov rax,-84
.return: ret
native_input_core_written64:
    ; Trusted admitted and successful write only, no user entry.
    xor eax,eax
    cmp esi,4
    jne .publish
    cmp edx,0x60
    jne .mouse
    mov eax,1
    jmp .publish
.mouse:
    cmp edx,0xd4
    jne .publish
    mov eax,2
.publish:
    mov [rdi+56],rax
    jmp native_input_core_seal64
native_input_core_fence64:
    call native_input_core_admit64
    test rax,rax
    jnz .done
    cmp rsi,[rdi]
    je .fence
    cmp rsi,[rdi+8]
    jne .done
.fence:
    mov qword [rdi+24],1
    mov qword [rdi+56],0
    jmp native_input_core_seal64
.done: ret
