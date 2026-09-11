; Private SysV AMD64, identical host/guest code. Caller serializes and owns
; descriptor/backing arrays; every loop is bounded by validated capacity<=64.
BITS 64
section .text
global reist_x64_queue_apply
reist_x64_queue_apply:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    mov r12, rdi
    mov r13, rsi
    mov r14, rdx
    mov r15, rcx
    mov rbp, r8
    cmp r13, 3
    ja .fail
    call queue_validate
    test eax, eax
    jz .fail
    test r13, r13
    jz .success
    cmp r13, 2
    je .pop
    cmp r14, r8
    jae .fail
    test r15, r15
    jz .fail
    mov rax, r15
    shr rax, 32
    jnz .fail
    cmp r13, 3
    je .remove
    cmp ebx, r8d
    jae .fail
    cmp byte [r10 + r14], 0
    jne .fail
    cmp dword [r12 + 28], 1
    je .deadline_insert
    movzx ecx, byte [r11 + 1]
    mov rax, r15
    shl rax, 32
    or rax, r14
    mov [r9 + rcx*8], rax
    mov byte [r10 + r14], 1
    inc ecx
    cmp ecx, r8d
    jb .tail_ready
    xor ecx, ecx
.tail_ready:
    mov [r11 + 1], cl
    inc byte [r11 + 2]
    jmp .success
.deadline_insert:
    test rbp, rbp
    jz .fail
    xor r13d, r13d
.find_insert:
    cmp r13d, ebx
    jae .shift_insert
    mov rdx, r13
    shl rdx, 4
    cmp rbp, [r9 + rdx]
    jb .shift_insert
    ja .next_insert
    movzx eax, byte [r9 + rdx + 12]
    cmp r14d, eax
    jb .shift_insert
.next_insert:
    inc r13d
    jmp .find_insert
.shift_insert:
    mov ecx, ebx
.shift_insert_loop:
    cmp ecx, r13d
    jbe .publish_deadline
    mov edx, ecx
    shl rdx, 4
    mov rax, [r9 + rdx - 16]
    mov rsi, [r9 + rdx - 8]
    mov [r9 + rdx], rax
    mov [r9 + rdx + 8], rsi
    dec ecx
    jmp .shift_insert_loop
.publish_deadline:
    mov rdx, r13
    shl rdx, 4
    mov [r9 + rdx], rbp
    mov rax, r14
    shl rax, 32
    or rax, r15
    mov [r9 + rdx + 8], rax
    mov byte [r10 + r14], 1
    inc byte [r11]
    jmp .success
.pop:
    test ebx, ebx
    jz .fail
    xor r13d, r13d
    call queue_key_at
    mov rbp, rax ; return exact selected identity
    mov r14d, eax
    cmp dword [r12 + 28], 0
    je .fifo_pop
    jmp .erase
.fifo_pop:
    movzx ecx, byte [r11]
    mov qword [r9 + rcx*8], 0
    mov byte [r10 + r14], 0
    inc ecx
    cmp ecx, r8d
    jb .head_ready
    xor ecx, ecx
.head_ready:
    mov [r11], cl
    dec byte [r11 + 2]
    jnz .erased
    mov word [r11], 0
    jmp .erased
.remove:
    cmp byte [r10 + r14], 1
    jne .fail
    shl r15, 32
    or r15, r14
    xor r13d, r13d
.find_remove:
    cmp r13d, ebx
    jae .fail
    call queue_key_at
    cmp rax, r15
    je .remove_found
    inc r13d
    jmp .find_remove
.remove_found:
    mov ebp, 1
.erase:
    ; Shape/ownership/exact identity were checked before any write.
    mov byte [r10 + r14], 0
    cmp dword [r12 + 28], 1
    je .deadline_erase
    movzx ecx, byte [r11]
    add ecx, r13d
    cmp ecx, r8d
    jb .fifo_erase_loop
    sub ecx, r8d
.fifo_erase_loop:
    inc r13d
    cmp r13d, ebx
    jae .fifo_erase_last
    lea edx, [rcx + 1]
    cmp edx, r8d
    jb .fifo_source
    xor edx, edx
.fifo_source:
    mov rax, [r9 + rdx*8]
    mov [r9 + rcx*8], rax
    mov ecx, edx
    jmp .fifo_erase_loop
.fifo_erase_last:
    mov qword [r9 + rcx*8], 0
    mov [r11 + 1], cl
    dec byte [r11 + 2]
    jnz .erased
    mov word [r11], 0
    jmp .erased
.deadline_erase:
    mov rdx, r13
    shl rdx, 4
.deadline_erase_loop:
    inc r13d
    cmp r13d, ebx
    jae .deadline_erase_last
    mov rax, [r9 + rdx + 16]
    mov rsi, [r9 + rdx + 24]
    mov [r9 + rdx], rax
    mov [r9 + rdx + 8], rsi
    add rdx, 16
    jmp .deadline_erase_loop
.deadline_erase_last:
    mov qword [r9 + rdx], 0
    mov qword [r9 + rdx + 8], 0
    dec byte [r11]
.erased:
    mov rax, rbp
    jmp .return
.success:
    mov eax, 1
    jmp .return
.fail:
    xor eax, eax
.return:
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret

; Logical index R13, validated pointers/count. No mutation; RAX packed key.
queue_key_at:
    mov rdx, r13
    cmp dword [r12 + 28], 1
    je .deadline
    movzx eax, byte [r11]
    add edx, eax
    cmp edx, r8d
    jb .fifo
    sub edx, r8d
.fifo:
    mov rax, [r9 + rdx*8]
    ret
.deadline:
    shl rdx, 4
    mov eax, [r9 + rdx + 8]
    shl rax, 32
    movzx edx, byte [r9 + rdx + 12]
    or rax, rdx
    ret

; Verify the complete queue before mutation. Leave R8 capacity, R9 entries,
; R10 membership, R11 metadata, EBX count. Preserve operation arguments.
queue_validate:
    push rbp
    push r13
    push r14
    push r15
    test r12, r12
    jz .fail
    mov r8d, [r12 + 24]
    test r8d, r8d
    jz .fail
    cmp r8d, 64
    ja .fail
    cmp dword [r12 + 28], 1
    ja .fail
    mov r9, [r12]
    mov r10, [r12 + 8]
    mov r11, [r12 + 16]
    test r9, r9
    jz .fail
    test r9, 7
    jnz .fail
    test r10, r10
    jz .fail
    test r11, r11
    jz .fail
    xor r13d, r13d
    movzx ebx, byte [r11]
    cmp dword [r12 + 28], 1
    je .count
    mov r13d, ebx ; FIFO head
    cmp r13d, r8d
    jae .fail
    movzx ebx, byte [r11 + 2]
    movzx eax, byte [r11 + 1]
    cmp eax, r8d
    jae .fail
    lea edx, [r13 + rbx]
    cmp edx, r8d
    jb .tail
    sub edx, r8d
.tail:
    cmp eax, edx
    jne .fail
    test ebx, ebx
    jnz .count
    test r13d, r13d
    jnz .fail
.count:
    cmp ebx, r8d
    ja .fail
    xor edi, edi ; membership bitset
    xor ecx, ecx
    xor r15d, r15d ; previous deadline
    xor ebp, ebp ; previous deadline slot
.entries:
    cmp dword [r12 + 28], 1
    je .deadline
    lea edx, [r13 + rcx]
    cmp edx, r8d
    jb .fifo_index
    sub edx, r8d
.fifo_index:
    mov rax, [r9 + rdx*8]
    cmp ecx, ebx
    jae .empty
    mov esi, eax
    shr rax, 32
    test eax, eax
    jz .fail
    jmp .member
.deadline:
    mov edx, ecx
    shl rdx, 4
    mov rax, [r9 + rdx]
    cmp ecx, ebx
    jae .empty_deadline
    test rax, rax
    jz .fail
    cmp dword [r9 + rdx + 8], 0
    je .fail
    mov esi, [r9 + rdx + 12] ; also rejects nonzero reserved bytes
    test ecx, ecx
    jz .ordered
    cmp rax, r15
    jb .fail
    ja .ordered
    cmp esi, ebp
    jbe .fail
.ordered:
    mov r15, rax
    mov ebp, esi
.member:
    cmp rsi, r8
    jae .fail
    bts rdi, rsi
    jc .fail
    cmp byte [r10 + rsi], 1
    jne .fail
    jmp .next
.empty_deadline:
    or rax, [r9 + rdx + 8]
.empty:
    test rax, rax
    jnz .fail
.next:
    inc ecx
    cmp ecx, r8d
    jb .entries
    xor ecx, ecx
.members:
    bt rdi, rcx
    setc al
    cmp [r10 + rcx], al
    jne .fail
    inc ecx
    cmp ecx, r8d
    jb .members
    mov eax, 1
    jmp .return
.fail:
    xor eax, eax
.return:
    pop r15
    pop r14
    pop r13
    pop rbp
    ret
