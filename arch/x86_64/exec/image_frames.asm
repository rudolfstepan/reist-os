bits 64
%include "arch/x86_64/mm/memory_profile.inc"
; Private SysV AMD64 mechanism. RDI is a trusted aligned88-byte image record,
; never a user pointer. Caller has fenced all consumers and serialized ownership
; (current profile: one CPU, IF=0). No shared-RX refcount or loader policy here.
; Validate all8 records before effects, then account only this release's delta.
global reist_x64_image_release
extern physical_frame_free64
extern physical_free_frame_count64
FLAGS equ 64
ERROR equ 78
ACTIVE equ 79
LIMIT equ MEMORY_LIMIT_VALUE

section .text
reist_x64_image_release:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    mov r12, rdi
    test r12, r12
    jz .bad
    test r12, 7
    jnz .bad
    mov rax, r12
    add rax, 87
    jc .bad
    cmp byte [r12 + ACTIVE], 1
    ja .bad
    cmp byte [r12 + ERROR], 1
    ja .bad
    cmp byte [r12 + 77], 1
    ja .bad
    xor ecx, ecx
.validate:
    movzx edx, byte [r12 + FLAGS + rcx]
    test edx, edx
    jz .flag_valid
    ; ELF PF_R, PF_R|PF_X or PF_R|PF_W; never W+X/unknown flags.
    cmp edx, 4
    jb .bad
    cmp edx, 6
    ja .bad
.flag_valid:
    mov rax, [r12 + rcx*8]
    test rax, rax
    jz .next
    test edx, edx
    jz .bad
    cmp byte [r12 + ACTIVE], 1
    jne .bad
    test rax, 4095
    jnz .bad
    MEMORY_COMPARE_LIMIT rax
    jae .bad
    xor edx, edx
.unique:
    cmp edx, ecx
    jae .next
    cmp rax, [r12 + rdx*8]
    je .bad
    inc edx
    jmp .unique
.next:
    inc ecx
    cmp ecx, 8
    jb .validate
    call physical_free_frame_count64
    cmp eax, LIMIT / 4096
    ja .bad
    mov r13d, eax
    xor r14d, r14d
    xor ebx, ebx
    mov byte [r12 + ERROR], 0
.release:
    mov rdi, [r12 + rbx*8]
    test rdi, rdi
    jz .clear_flag
    call physical_frame_free64
    cmp eax, 1
    jne .failed_free
    mov qword [r12 + rbx*8], 0
    inc r14d
.clear_flag:
    ; Unallocated marked pages are valid during load/OOM rollback.
    mov byte [r12 + FLAGS + rbx], 0
    jmp .advance
.failed_free:
    ; Keep failed ownership intact; a bounded retry never repeats a good free.
    mov byte [r12 + ERROR], 1
.advance:
    inc ebx
    cmp ebx, 8
    jb .release
    call physical_free_frame_count64
    add r13d, r14d
    cmp r13d, LIMIT / 4096
    ja .accounting_failed
    cmp eax, r13d
    jne .accounting_failed
    cmp byte [r12 + ERROR], 0
    jne .bad
    mov byte [r12 + ACTIVE], 0
    mov byte [r12 + 76], 0
    mov byte [r12 + 77], 0
    mov qword [r12 + 80], 0
    mov eax, 1
    jmp .return
.accounting_failed:
    mov byte [r12 + ERROR], 1
.bad:
    xor eax, eax
.return:
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
