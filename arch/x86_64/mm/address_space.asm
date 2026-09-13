bits 64
%include "arch/x86_64/mm/memory_profile.inc"
; Private layout-derived physical plan; no ELF selector, task roles or allocator.
; All ownership is held by the caller. Validate everything before writing pages.
; At most133 frame records,69 zero pages and64 copy pages with NativeWide;
; default21 records/13 zero/8 copy pages. Caller serializes with IF=0.
global reist_x64_address_space_build
extern reist_x64_mapping_pointer64
LIMIT equ 0x08000000
FRAME_MASK equ MEMORY_PTE_FRAME_MASK
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
    sub rsp, NATIVE_PLAN_FRAMES*8+16 ; bounded pointer cache, SysV call alignment
    mov r12, rdi
    test r12, r12
    jz .bad
    test r12, 7
    jnz .bad
    mov rax, r12
    add rax, NATIVE_PLAN_BYTES
    jc .bad
    xor ecx, ecx
.flags:
    movzx eax, byte [r12 + NATIVE_PLAN_FLAGS + rcx]
    mov rdx, [r12 + 32 + rcx*8]
    mov r8, [r12 + NATIVE_PLAN_PRIVATE + rcx*8]
%ifdef REIST_NATIVE_WIDE
    cmp ecx,8
    jne .not_stack_slot
    test eax,eax
    jnz .bad
.not_stack_slot:
%endif
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
    cmp ecx, NATIVE_IMAGE_PAGES
    jb .flags
    xor ecx, ecx
.kernel:
    mov rax, [r12 + NATIVE_PLAN_KERNEL + rcx*8]
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
    MEMORY_MASK_FRAME rax
    jz .bad
    inc ecx
    cmp ecx, 2
    jb .kernel
    xor ebx, ebx
.frames:
    lea rax, [r12 + rbx*8]
    cmp ebx, 4+NATIVE_IMAGE_PAGES
    jb .frame_address
    add rax, NATIVE_IMAGE_PAGES ; skip the layout's flag bytes
.frame_address:
    mov rdi, [rax]
    test rdi, rdi
    jnz .nonzero
    cmp ebx, 4
    jb .bad
    cmp ebx, NATIVE_PLAN_FRAMES-1
    je .bad
    jmp .next_frame
.nonzero:
    test rdi, 4095
    jnz .bad
    MEMORY_COMPARE_LIMIT rdi
    jae .bad
    xor ecx, ecx
.not_kernel_frame:
    mov rax, [r12 + NATIVE_PLAN_KERNEL + rcx*8]
    MEMORY_MASK_FRAME rax
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
    cmp ecx, 4+NATIVE_IMAGE_PAGES
    jb .compare_frame
    add rax, NATIVE_IMAGE_PAGES
.compare_frame:
    cmp rdi, [rax]
    je .bad
    inc ecx
    jmp .unique_frame
.next_frame:
    inc ebx
    cmp ebx, NATIVE_PLAN_FRAMES
    jb .frames
    xor ebx, ebx
.pointers:
    lea rax, [r12 + rbx*8]
    cmp ebx, 4+NATIVE_IMAGE_PAGES
    jb .pointer_address
    add rax, NATIVE_IMAGE_PAGES
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
    lea rcx, [r12 + NATIVE_PLAN_BYTES]
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
    cmp ebx, NATIVE_PLAN_FRAMES
    jb .pointers
    cld
    xor ebx, ebx
.zero_destinations:
    ; Source slots follow the four tables. All writable destinations must be0.
    cmp ebx, 4
    jb .check_zero
    cmp ebx, 4+NATIVE_IMAGE_PAGES
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
    cmp ebx, NATIVE_PLAN_FRAMES
    jb .zero_destinations
.validated:
    ; No fallible operation remains after this point; all pointers are cached.
    mov r13, [rsp]
    mov rax, [r12 + 8]
    or rax, 7
    mov [r13], rax
    mov rax, [r12 + NATIVE_PLAN_KERNEL]
    mov [r13 + 256*8], rax
    mov rax, [r12 + NATIVE_PLAN_KERNEL+8]
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
    movzx r14d, byte [r12 + NATIVE_PLAN_FLAGS + rbx]
    test r14d, r14d
    jz .next_page
    mov r15, [r12 + 32 + rbx*8]
    cmp r14d, 6
    jne .shared
    mov rsi, [rsp + 32 + rbx*8]
    mov rdi, [rsp + 32+NATIVE_IMAGE_PAGES*8 + rbx*8]
    mov ecx, 512
    rep movsq
    mov r15, [r12 + NATIVE_PLAN_PRIVATE + rbx*8]
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
    cmp ebx, NATIVE_IMAGE_PAGES
    jb .map_pages
    mov rax, [r12 + NATIVE_PLAN_STACK]
    or rax, 7
    mov rdx, NX
    or rax, rdx
    mov [r13 + 8*8], rax
    mov eax, 1
    jmp .return
.bad:
    xor eax, eax
.return:
    add rsp, NATIVE_PLAN_FRAMES*8+16
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
