; Private, fixed48-byte SysV AMD64 burst ownership core. No privileged work.
; All invalid transitions leave state unchanged. See query_return.h.
global qr_reset,qr_bind,qr_take

; RDI state. EAX1 live,2 empty,-1 invalid; preserves RSI/RDX.
qr_validate:
    test rdi,rdi
    jz .bad
    test rdi,7
    jnz .bad
    xor eax,eax
    mov ecx,6
.empty:
    or rax,[rdi+rcx*8-8]
    loop .empty
    test rax,rax
    jz .zero
    mov rax,[rdi]
    test rax,rax
    jz .bad
    cmp rax,0x7fffffff
    ja .bad
    cmp qword [rdi+8],8
    jae .bad
    mov rax,[rdi+16]
    dec rax
    cmp rax,7
    ja .bad
    mov ecx,3
.inverse:
    mov rax,[rdi+rcx*8-8]
    xor rax,[rdi+rcx*8+16]
    cmp rax,-1
    jne .bad
    loop .inverse
    mov eax,1
    ret
.zero:
    mov eax,2
    ret
.bad:
    mov eax,-1
    ret

qr_reset:
    call qr_validate
    test eax,eax
    js .bad
    xor eax,eax
    mov ecx,6
    cld
    rep stosq
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret

qr_bind:
    cmp esi,8
    jae .bad
    test rdx,rdx
    jz .bad
    cmp rdx,0x7fffffff
    ja .bad
    call qr_validate
    cmp eax,2
    jne .bad
    mov [rdi],rdx
    mov eax,esi
    mov [rdi+8],rax
    not rax
    mov [rdi+32],rax
    mov rax,rdx
    not rax
    mov [rdi+24],rax
    mov qword [rdi+16],8
    mov qword [rdi+40],~8
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret

qr_take:
    call qr_validate
    cmp eax,1
    jne .bad
    mov eax,esi
    cmp [rdi+8],rax
    jne .bad
    cmp [rdi],rdx
    jne .bad
    mov rax,[rdi+16]
    cmp eax,1
    je .dispatch
    dec rax
    mov [rdi+16],rax
    not rax
    mov [rdi+40],rax
    mov eax,1
    ret
.dispatch:
    xor eax,eax
    ret
.bad:
    mov eax,-1
    ret
