bits 64
%include "arch/x86_64/mm/memory_profile.inc"
; Private32-byte binding. At most4 record regions and13 physical frame records.
; Validate before all effects; caller fences execution and owns pinned storage.
global reist_x64_task_frames_release
extern physical_frame_free64
extern physical_free_frame_count64
LIMIT equ 0x08000000

section .text
reist_x64_task_frames_release:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp, 120 ;13 cached record pointers and SysV call alignment
    mov r12, rdi
    test r12, r12
    jz .bad
    test r12, 7
    jnz .bad
    mov rax, r12
    add rax, 32
    jc .bad
    xor ebx, ebx
.regions:
    mov r8, [r12 + rbx*8]
    test r8, r8
    jz .bad
    test r8, 7
    jnz .bad
    mov ecx, ebx
    call .region_size
    mov r9, r8
    add r9, rax
    jc .bad
    ; Binding and mutable records must not alias each other.
    cmp r9, r12
    jbe .previous_regions
    lea rax, [r12 + 32]
    cmp r8, rax
    jb .bad
.previous_regions:
    xor ecx, ecx
.region_pair:
    cmp ecx, ebx
    jae .next_region
    call .region_size
    mov rdx, [r12 + rcx*8]
    add rax, rdx ;previous region end already checked for overflow
    cmp r9, rdx
    jbe .next_pair
    cmp r8, rax
    jb .bad
.next_pair:
    inc ecx
    jmp .region_pair
.next_region:
    inc ebx
    cmp ebx, 4
    jb .regions
    xor ecx, ecx
    mov rax, [r12]
.data_pointers:
    lea rdx, [rax + rcx*8]
    mov [rsp + rcx*8], rdx
    inc ecx
    cmp ecx, 8
    jb .data_pointers
    mov rax, [r12 + 8]
    mov [rsp + 64], rax
    mov rax, [r12 + 16]
    lea rdx, [rax + 24]
    mov [rsp + 72], rdx ;PT
    lea rdx, [rax + 16]
    mov [rsp + 80], rdx ;PD
    lea rdx, [rax + 8]
    mov [rsp + 88], rdx ;PDPT
    mov [rsp + 96], rax ;PML4 last
    mov rdx, [r12 + 24]
    mov rdx, [rdx]
    test rdx, rdx
    jz .physical_start
    cmp rdx, [rax]
    jne .bad
.physical_start:
    xor ebx, ebx
    xor r14d, r14d
.physical:
    mov rax, [rsp + rbx*8]
    mov r8, [rax]
    test r8, r8
    jz .next_physical
    test r8, 4095
    jnz .bad
    MEMORY_COMPARE_LIMIT r8
    jae .bad
    xor ecx, ecx
.unique:
    cmp ecx, ebx
    jae .count
    mov rax, [rsp + rcx*8]
    cmp r8, [rax]
    je .bad
    inc ecx
    jmp .unique
.count:
    inc r14d
.next_physical:
    inc ebx
    cmp ebx, 13
    jb .physical
    call physical_free_frame_count64
    cmp eax, MEMORY_FRAME_CAPACITY
    ja .bad
    mov r13d, eax
    add eax, r14d
    cmp eax, MEMORY_FRAME_CAPACITY
    ja .bad
.validated:
    xor ebx, ebx
    xor r14d, r14d
    xor r15d, r15d
.release:
    mov rax, [rsp + rbx*8]
    mov rdi, [rax]
    test rdi, rdi
    jz .next_release
    call physical_frame_free64
    cmp eax, 1
    jne .failed_release
    mov rax, [rsp + rbx*8]
    mov qword [rax], 0
    inc r14d
.next_release:
    inc ebx
    cmp ebx, 13
    jb .release
    mov rax, [r12 + 24]
    mov qword [rax], 0
    jmp .balance
.failed_release:
    mov r15d, 1 ;stop: retain this and every subsequent record
.balance:
    call physical_free_frame_count64
    add r13d, r14d
    cmp eax, r13d
    jne .bad
    test r15d, r15d
    jnz .bad
    mov eax, 1
    jmp .return
.bad:
    xor eax, eax
.return:
    add rsp, 120
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
.region_size:
    mov eax, 8
    test ecx, ecx
    jnz .not_data
    mov eax, 64
.not_data:
    cmp ecx, 2
    jne .size_done
    mov eax, 32
.size_done:
    ret
