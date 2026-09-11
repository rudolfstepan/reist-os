bits 64
; Private192-byte physical plan; no global ELF selector, task roles or allocator.
; All ownership is held by the caller. Validate everything before writing pages.
; Loops: <=21 records/pairs, <=21 pointer pairs, <=13*512 zero-check qwords,
; <=8*512 copy qwords. Caller serializes this bounded operation with IF=0.
global reist_x64_address_space_build
extern reist_x64_mapping_pointer64
LIMIT equ 0x08000000
FRAME_MASK equ 0x07fff000
NX equ 0x8000000000000000

section .text
reist_x64_address_space_build:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp, 184 ;21 cached page pointers, SysV call alignment
    mov r12, rdi
    test r12, r12
    jz .bad
    test r12, 7
    jnz .bad
    mov rax, r12
    add rax, 192
    jc .bad
    xor ecx, ecx
.flags:
    movzx eax, byte [r12 + 96 + rcx]
    mov rdx, [r12 + 32 + rcx*8]
    mov r8, [r12 + 104 + rcx*8]
    test eax, eax
    jz .absent
    cmp eax, 4
    jb .bad
    cmp eax, 6
    ja .bad
    test rdx, rdx
    jz .bad
    cmp eax, 6
    je .writable
    test r8, r8
    jnz .bad
    jmp .next_flags
.writable:
    test r8, r8
    jz .bad
    jmp .next_flags
.absent:
    or rdx, r8
    jnz .bad
.next_flags:
    inc ecx
    cmp ecx, 8
    jb .flags
    xor ecx, ecx
.kernel:
    mov rax, [r12 + 176 + rcx*8]
    ; Preserve the existing NX direct map and executable higher-half template.
    test ecx, ecx
    jnz .kernel_text
    test rax, rax
    jns .bad
    jmp .kernel_bits
.kernel_text:
    test rax, rax
    js .bad
.kernel_bits:
    mov rdx, NX | FRAME_MASK | 0x23 ;P/RW and accessed, never USER
    and rdx, rax
    cmp rax, rdx
    jne .bad
    and edx, 3
    cmp edx, 3
    jne .bad
    and rax, FRAME_MASK
    jz .bad
    inc ecx
    cmp ecx, 2
    jb .kernel
    xor ebx, ebx
.frames:
    lea rax, [r12 + rbx*8]
    cmp ebx, 12
    jb .frame_address
    add rax, 8 ;skip the8 flag bytes
.frame_address:
    mov rdi, [rax]
    test rdi, rdi
    jnz .nonzero
    cmp ebx, 4
    jb .bad
    cmp ebx, 20
    je .bad
    jmp .next_frame
.nonzero:
    test rdi, 4095
    jnz .bad
    cmp rdi, LIMIT
    jae .bad
    xor ecx, ecx
.not_kernel_frame:
    mov rax, [r12 + 176 + rcx*8]
    and eax, FRAME_MASK
    cmp rdi, rax
    je .bad
    inc ecx
    cmp ecx, 2
    jb .not_kernel_frame
    xor ecx, ecx
.unique_frame:
    cmp ecx, ebx
    jae .next_frame
    lea rax, [r12 + rcx*8]
    cmp ecx, 12
    jb .compare_frame
    add rax, 8
.compare_frame:
    cmp rdi, [rax]
    je .bad
    inc ecx
    jmp .unique_frame
.next_frame:
    inc ebx
    cmp ebx, 21
    jb .frames
    xor ebx, ebx
.pointers:
    lea rax, [r12 + rbx*8]
    cmp ebx, 12
    jb .pointer_address
    add rax, 8
.pointer_address:
    mov rdi, [rax]
    test rdi, rdi
    jz .zero_pointer
    call reist_x64_mapping_pointer64
    test rax, rax
    jz .bad
    test rax, 4095
    jnz .bad
    mov rdx, rax
    add rdx, 4096
    jc .bad
    ; Do not allow even a trusted malformed backend to alias the plan.
    cmp rdx, r12
    jbe .unique_pointer_start
    lea rcx, [r12 + 192]
    cmp rax, rcx
    jb .bad
.unique_pointer_start:
    xor ecx, ecx
.unique_pointer:
    cmp ecx, ebx
    jae .store_pointer
    cmp rax, [rsp + rcx*8]
    je .bad
    inc ecx
    jmp .unique_pointer
.zero_pointer:
    xor eax, eax
.store_pointer:
    mov [rsp + rbx*8], rax
    inc ebx
    cmp ebx, 21
    jb .pointers
    cld
    xor ebx, ebx
.zero_destinations:
    ; Source slots4..11 are immutable. Tables, private data and stack must be0.
    cmp ebx, 4
    jb .check_zero
    cmp ebx, 12
    jb .next_zero
.check_zero:
    mov rdi, [rsp + rbx*8]
    test rdi, rdi
    jz .next_zero
    xor eax, eax
    mov ecx, 512
    repe scasq
    jne .bad
.next_zero:
    inc ebx
    cmp ebx, 21
    jb .zero_destinations
.validated:
    ; No fallible operation remains after this point; all pointers are cached.
    mov r13, [rsp]
    mov rax, [r12 + 8]
    or rax, 7
    mov [r13], rax
    mov rax, [r12 + 176]
    mov [r13 + 256*8], rax
    mov rax, [r12 + 184]
    mov [r13 + 511*8], rax
    mov r13, [rsp + 8]
    mov rax, [r12 + 16]
    or rax, 7
    mov [r13], rax
    mov r13, [rsp + 16]
    mov rax, [r12 + 24]
    or rax, 7
    mov [r13 + 2*8], rax
    mov r13, [rsp + 24]
    xor ebx, ebx
.map_pages:
    movzx r14d, byte [r12 + 96 + rbx]
    test r14d, r14d
    jz .next_page
    mov r15, [r12 + 32 + rbx*8]
    cmp r14d, 6
    jne .shared
    mov rsi, [rsp + 32 + rbx*8]
    mov rdi, [rsp + 96 + rbx*8]
    mov ecx, 512
    rep movsq
    mov r15, [r12 + 104 + rbx*8]
    or r15, 2
.shared:
    or r15, 5
    cmp r14d, 5
    je .store_page
    mov rax, NX
    or r15, rax
.store_page:
    mov [r13 + rbx*8], r15
.next_page:
    inc ebx
    cmp ebx, 8
    jb .map_pages
    mov rax, [r12 + 168]
    or rax, 7
    mov rdx, NX
    or rax, rdx
    mov [r13 + 8*8], rax
    mov eax, 1
    jmp .return
.bad:
    xor eax, eax
.return:
    add rsp, 184
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
