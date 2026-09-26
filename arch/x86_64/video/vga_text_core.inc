; SysV core executed unchanged by kernel and host tests. No hardware access.
global native_vga_core_init64,native_vga_core_admit64,native_vga_core_apply64
global native_vga_core_fence64,native_vga_core_transfer64

native_vga_core_init64:
    mov r10,rdi
    xor eax,eax
    mov ecx,284
    rep stosq
    mov rdi,r10
    mov qword [rdi+24],1
    jmp native_vga_core_seal64

native_vga_core_seal64:
    xor r9d,r9d
.word:
    mov rax,[rdi+r9]
    not rax
    mov [rdi+r9+80],rax
    add r9d,8
    cmp r9d,80
    jb .word
    xor eax,eax
    ret

native_vga_core_admit64:
    xor r9d,r9d
.word:
    mov rax,[rdi+r9]
    not rax
    cmp [rdi+r9+80],rax
    jne .bad
    add r9d,8
    cmp r9d,80
    jb .word
    cmp qword [rdi+24],2
    ja .bad
    cmp qword [rdi+48],2048
    jae .bad
    cmp qword [rdi+56],2048
    ja .bad
    cmp qword [rdi+64],64
    jae .bad
    cmp qword [rdi+72],64
    ja .bad
    mov rax,[rdi+32]
    shr rax,60
    jnz .bad
    mov rax,[rdi+40]
    cmp rax,[rdi+32]
    ja .bad
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
    jmp .fenced
.empty:
    cmp qword [rdi+8],0
    jne .bad
    cmp qword [rdi+24],1
    jne .bad
.fenced:
    cmp qword [rdi+24],1
    jne .ok
    mov rax,[rdi+48]
    or rax,[rdi+56]
    or rax,[rdi+64]
    or rax,[rdi+72]
    jnz .bad
.ok:
    xor eax,eax
    ret
.bad:
    mov rax,-84
    ret

; Scrub queues while retaining owner, epoch and monotonic history.
native_vga_core_clear64:
    push rdi
    lea rdi,[rdi+48]
    xor eax,eax
    mov ecx,4
    rep stosq
    pop rdi
    push rdi
    add rdi,160
    mov ecx,264
    rep stosq
    pop rdi
    jmp native_vga_core_seal64

native_vga_core_fence64:
    call native_vga_core_admit64
    test rax,rax
    jnz .return
    test rsi,rsi
    jz .return
    cmp rsi,[rdi]
    je .fence
    cmp rsi,[rdi+8]
    jne .return
.fence:
    mov qword [rdi+24],1
    jmp native_vga_core_clear64
.return:
    ret

native_vga_core_apply64:
    call native_vga_core_admit64
    test rax,rax
    jnz .return
    mov rax,rcx
    shr rax,60
    jnz .corrupt
    cmp rcx,[rdi+32]
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
    cmp eax,8
    ja .invalid
    cmp eax,0
    je .bind
    mov rax,[rsi+16]
    cmp rax,[rdi]
    jne .stale
    test rax,rax
    jz .stale
    cmp dword [rsi+8],3
    je .query
    mov rax,[rsi+24]
    cmp rax,[rdi+16]
    jne .stale
    cmp dword [rsi+8],2
    je .parent
    cmp dword [rsi+8],8
    je .parent
    cmp rdx,[rdi]
    jne .denied
    cmp qword [rdi+24],1
    je .pipe
    mov rax,rcx
    sub rax,[rdi+40]
    cmp rax,1000
    jae .timeout
    cmp dword [rsi+8],7
    je .heartbeat
    cmp dword [rsi+8],9
    je .cursor
    cmp qword [rsi+32],0
    je .pointer
    mov eax,[rsi+40]
    test eax,eax
    jz .invalid
    cmp dword [rsi+8],6
    je .cells
    cmp eax,64
    ja .invalid
    cmp dword [rsi+44],0
    jne .invalid
    jmp .accept
.cells:
    cmp eax,80
    ja .invalid
    mov r9d,[rsi+44]
    add rax,r9
    ; row 24 remains reserved for early/fatal status.
    cmp rax,1920
    ja .invalid
    jmp .accept
.cursor:
    cmp qword [rsi+32],0
    jne .invalid
    cmp dword [rsi+40],0
    jne .invalid
    cmp dword [rsi+44],1920
    jae .invalid
.accept:
    mov [rdi+32],rcx
    jmp native_vga_core_seal64
.heartbeat:
    mov rax,[rsi+32]
    or rax,[rsi+40]
    jnz .invalid
    mov qword [rdi+24],2
    mov [rdi+40],rcx
    jmp .accept
.parent:
    cmp rdx,[rdi+8]
    jne .denied
    mov rax,[rsi+32]
    or rax,[rsi+40]
    jnz .invalid
    cmp dword [rsi+8],2
    je .revoke
    cmp qword [rdi+24],1
    je .pipe
    mov rax,rcx
    sub rax,[rdi+40]
    cmp rax,1000
    jae .timeout
    cmp qword [rdi+24],2
    jne .again
    jmp .accept
.revoke:
    mov [rdi+32],rcx
    mov qword [rdi+24],1
    jmp native_vga_core_clear64
.query:
    mov rax,[rsi+24]
    or rax,[rsi+32]
    or rax,[rsi+40]
    jnz .invalid
    cmp rdx,[rdi]
    je .query_ok
    cmp rdx,[rdi+8]
    jne .denied
.query_ok:
    cmp qword [rdi+24],1
    je .pipe
    mov rax,[rdi+16]
    ret
.bind:
    mov rax,[rsi+24]
    or rax,[rsi+32]
    or rax,[rsi+40]
    jnz .invalid
    test edx,edx
    jnz .denied
    mov rax,rdx
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .denied
    cmp r8,3 ; independently verified old reap and new direct child
    jne .denied
    cmp qword [rdi+24],1
    jne .busy
    mov rax,[rsi+16]
    cmp eax,2
    jb .invalid
    cmp eax,7
    ja .invalid
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .invalid
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
    call native_vga_core_clear64
    mov rax,[rdi+16]
    ret
.invalid: mov rax,-22
    ret
.pointer: mov rax,-14
    ret
.denied: mov rax,-1
    ret
.stale: mov rax,-116
    ret
.pipe: mov rax,-32
    ret
.busy: mov rax,-16
    ret
.timeout: mov rax,-110
    ret
.again: mov rax,-11
    ret
.overflow: mov rax,-75
    ret
.corrupt: mov rax,-84
.return: ret

native_vga_core_transfer64:
    call native_vga_core_admit64
    test rax,rax
    jnz .return
    cmp qword [rdi+24],1
    je .pipe
    test rsi,rsi
    jz .pointer
    lea rax,[rdx-1]
    cmp rax,63
    ja .invalid
    cmp rcx,3
    ja .invalid
    mov r8,rcx
    mov r10d,2048
    lea r11,[rdi+160]
    lea r9,[rdi+48]
    cmp ecx,2
    jb .queue
    mov r10d,64
    add r11,2048
    add r9,16
.queue:
    test r8b,1
    jnz .consume
    mov rax,r10
    sub rax,[r9+8]
    cmp rax,rdx
    jb .again
    mov rcx,[r9]
    add rcx,[r9+8]
    dec r10
    and rcx,r10
    add [r9+8],rdx
    mov r8,rdx
.put:
    mov al,[rsi]
    mov [r11+rcx],al
    inc rsi
    inc rcx
    and rcx,r10
    dec rdx
    jnz .put
    jmp .done
.consume:
    cmp qword [r9+8],0
    je .again
    cmp rdx,[r9+8]
    jbe .count
    mov rdx,[r9+8]
.count:
    sub [r9+8],rdx
    mov r8,rdx
    mov rcx,[r9]
    dec r10
.get:
    mov al,[r11+rcx]
    mov [rsi],al
    mov byte [r11+rcx],0
    inc rsi
    inc rcx
    and rcx,r10
    dec rdx
    jnz .get
    mov [r9],rcx
.done:
    call native_vga_core_seal64
    mov rax,r8
    ret
.again: mov rax,-11
    ret
.pipe: mov rax,-32
    ret
.pointer: mov rax,-14
    ret
.invalid: mov rax,-22
.return: ret
