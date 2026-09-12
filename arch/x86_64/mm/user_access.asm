BITS 64
global reist_x64_user_access
extern reist_x64_mapping_pointer64
LIMIT equ 0x08000000
section .text
reist_x64_user_access:
    push rbp
    mov rbp,rsp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp,72
    mov r12,rdi
    mov [rsp+32],rsi
    mov [rsp+40],rdx
    mov [rsp+48],rcx
    test r12,r12
    jz .corrupt
    test r12,7
    jnz .corrupt
    mov rax,r12
    add rax,32
    jc .corrupt
    mov r14,[r12]
    mov r13,[r12+8]
    mov rax,r14
    call .record
    mov rax,r13
    call .record
    cmp qword [r14],2
    jne .corrupt
    mov rax,[r12+16]
    test rax,rax
    jz .corrupt
    mov edx,eax
    cmp rax,rdx
    jne .corrupt
    cmp rax,[r14+8]
    jne .corrupt
    mov rax,[r12+24]
    cmp rax,[r14+16]
    jne .corrupt
    cmp rax,[r13]
    jne .corrupt
    ; Validate every frame before asking the side-effect-free pointer adapter.
    xor ebx,ebx
.frames:
    mov rax,[r13+rbx*8]
    call .frame
    xor ecx,ecx
.unique:
    cmp ecx,ebx
    jae .next_frame
    cmp rax,[r13+rcx*8]
    je .corrupt
    inc ecx
    jmp .unique
.next_frame:
    inc ebx
    cmp ebx,4
    jb .frames
    xor ebx,ebx
.pointers:
    mov rdi,[r13+rbx*8]
    call reist_x64_mapping_pointer64
    test rax,rax
    jz .corrupt
    test rax,4095
    jnz .corrupt
    mov rdx,rax
    add rdx,4096
    jc .corrupt
    xor ecx,ecx
.pointer_unique:
    cmp ecx,ebx
    jae .save_pointer
    cmp rax,[rsp+rcx*8]
    je .corrupt
    inc ecx
    jmp .pointer_unique
.save_pointer:
    mov [rsp+rbx*8],rax
    inc ebx
    cmp ebx,4
    jb .pointers
    ; Resolve the existing single PT topology for [0x400000,0x409000).
    mov r15d,7
    xor ebx,ebx
.levels:
    mov rdx,[rsp+rbx*8]
    xor ecx,ecx
    cmp ebx,2
    jne .entry
    mov ecx,2
.entry:
    mov rax,[rdx+rcx*8]
    mov rdx,0x8000000007fff027 ;address, NX, P/W/U/A only
    not rdx
    test rax,rdx
    jnz .corrupt
    and r15d,eax
    and eax,0x07fff000
    cmp rax,[r13+rbx*8+8]
    jne .corrupt
    inc ebx
    cmp ebx,3
    jb .levels
    mov rax,[rsp+48]
    cmp rax,4
    je .read
    cmp rax,2
    jne .invalid
    mov r14d,7
    jmp .rights
.read:
    mov r14d,5
.rights:
    and r15d,r14d
    cmp r15d,r14d
    jne .invalid
    mov rax,[rsp+32]
    cmp rax,0x400000
    jb .invalid
    mov rdx,[rsp+40]
    test rdx,rdx
    jz .invalid
    cmp rdx,140
    ja .invalid
    add rdx,rax
    jc .invalid
    cmp rdx,0x409000
    ja .invalid
    dec rdx
    sub rax,0x400000
    sub rdx,0x400000
    shr eax,12
    shr edx,12
    mov ebx,eax
    mov r15d,edx
.leaf:
    mov rdx,[rsp+24]
    mov rax,[rdx+rbx*8]
    test rax,rax
    jz .invalid
    mov rdx,0x8000000007fff067 ;4KiB leaf, NX plus P/W/U/A/D
    not rdx
    test rax,rdx
    jnz .corrupt
    mov ecx,eax
    and ecx,r14d
    cmp ecx,r14d
    jne .invalid
    and eax,0x07fff000
    call .frame
    xor ecx,ecx
.leaf_alias:
    cmp rax,[r13+rcx*8]
    je .corrupt
    inc ecx
    cmp ecx,4
    jb .leaf_alias
    cmp ebx,8
    jne .next_leaf
    mov rdx,[r12]
    cmp rax,[rdx+24]
    jne .corrupt
.next_leaf:
    inc ebx
    cmp ebx,r15d
    jbe .leaf
    mov eax,1
    jmp .return
.invalid:
    xor eax,eax
    jmp .return
.corrupt:
    mov rax,-4096
.return:
    lea rsp,[rbp-40]
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
.record:
    test rax,rax
    jz .corrupt
    test rax,7
    jnz .corrupt
    add rax,32
    jc .corrupt
    ret
.frame:
    test rax,rax
    jz .corrupt
    test rax,4095
    jnz .corrupt
    cmp rax,LIMIT
    jae .corrupt
    ret
