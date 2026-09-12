bits 64
%include "arch/x86_64/mm/memory_profile.inc"
; Private SysV AMD64 transaction, trusted aligned120-byte kernel record.
; No user pointers, heap, waits or new authority. All loops <=13 (pair checks <=169).
; Allocator/free are the production physical-frame mechanism, replaceable only
; at link time by host-test backends. ENOMEM requires complete rollback.
global reist_x64_frame_claim_begin
global reist_x64_frame_claim_take
global reist_x64_frame_claim_abort
extern physical_frame_alloc64
extern physical_frame_free64
COUNT equ 104
CURSOR equ 112
CAPACITY equ 13
LIMIT equ 0x08000000

section .text
reist_x64_frame_claim_begin:
    mov edx, 1
    jmp claim_dispatch
reist_x64_frame_claim_take:
    mov edx, 2
    jmp claim_dispatch
reist_x64_frame_claim_abort:
    mov edx, 3
claim_dispatch:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    mov r12, rdi
    mov r13, rsi
    mov r14d, edx
    test r12, r12
    jz .bad
    test r12, 7
    jnz .bad
    mov rax, r12
    add rax, 119
    jc .bad
    cmp qword [r12 + COUNT], CAPACITY
    ja .bad
    mov rax, [r12 + CURSOR]
    cmp rax, [r12 + COUNT]
    ja .bad
    xor ecx, ecx
.validate:
    cmp ecx, CAPACITY
    jae .validated
    mov rax, [r12 + rcx*8]
    cmp rcx, [r12 + CURSOR]
    jb .must_zero
    cmp rcx, [r12 + COUNT]
    jae .must_zero
    test rax, rax
    jz .bad
    test rax, 4095
    jnz .bad
    MEMORY_COMPARE_LIMIT rax
    jae .bad
    mov rdx, [r12 + CURSOR]
.unique:
    cmp rdx, rcx
    jae .next
    cmp rax, [r12 + rdx*8]
    je .bad
    inc edx
    jmp .unique
.must_zero:
    test rax, rax
    jnz .bad
.next:
    inc ecx
    jmp .validate
.validated:
    cmp r14d, 1
    je .begin
    cmp r14d, 2
    je .take
    mov r14, 1
    jmp .release
.begin:
    cmp qword [r12 + COUNT], 0
    jne .bad
    test r13, r13
    jz .bad
    cmp r13, CAPACITY
    ja .bad
.allocate:
    call physical_frame_alloc64
    test rax, rax
    jz .oom
    test rax, 4095
    jnz .bad
    MEMORY_COMPARE_LIMIT rax
    jae .bad
    xor ecx, ecx
.new_unique:
    cmp rcx, [r12 + COUNT]
    jae .store
    cmp rax, [r12 + rcx*8]
    je .bad
    inc ecx
    jmp .new_unique
.store:
    mov [r12 + rcx*8], rax
    inc qword [r12 + COUNT]
    cmp [r12 + COUNT], r13
    jb .allocate
    mov eax, 1
    jmp .out
.take:
    mov rcx, [r12 + CURSOR]
    cmp rcx, [r12 + COUNT]
    jae .bad
    mov rax, [r12 + rcx*8]
    mov qword [r12 + rcx*8], 0
    inc qword [r12 + CURSOR]
    jmp .out
.oom:
    mov r14, -12
.release:
    mov rbx, [r12 + CURSOR]
    cmp rbx, [r12 + COUNT]
    jae .released
    mov rdi, [r12 + rbx*8]
    call physical_frame_free64
    cmp eax, 1
    jne .bad
    mov qword [r12 + rbx*8], 0
    inc qword [r12 + CURSOR]
    jmp .release
.released:
    mov qword [r12 + COUNT], 0
    mov qword [r12 + CURSOR], 0
    mov rax, r14
    jmp .out
.bad:
    mov rax, -4096
.out:
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
