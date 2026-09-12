; SysV, pinned immutable36896-byte record. No user pointer or ELF parsing.
; Return1 iff complete fixed metadata/argument admission, no writes.
boot_program_admit64:
    test rdi,rdi
    jz .bad
    test rdi,15
    jnz .bad
    cmp rsi,36896
    jne .bad
    mov rax,rdi
    add rax,rsi
    jc .bad
    mov rax,0x0000317647504e52 ; RNPGv1\0\0
    cmp [rdi],rax
    jne .bad
    cmp dword [rdi+8],1
    jne .bad
    cmp dword [rdi+12],36896
    jne .bad
    mov rax,[rdi+16]
    sub rax,0x400000
    cmp rax,32768
    jae .bad
    shr eax,12
    cmp byte [rdi+rax+24],5
    jne .bad
    xor ecx,ecx
.flags:
    movzx eax,byte [rdi+rcx+24]
    test eax,eax
    jz .next
    sub eax,4
    cmp eax,2
    ja .bad
.next:
    inc ecx
    cmp ecx,8
    jb .flags
    sub rsp,56
    lea rax,[rdi+32800]
    mov [rsp],rax
    lea rax,[rdi+32] ; op0 never writes, disjoint pinned destination
    mov [rsp+8],rax
    mov qword [rsp+16],0x1000
    mov qword [rsp+24],0x409000
    xor eax,eax
    mov rcx,[rdi+32800]
    test rcx,rcx
    jz .empty
    mov eax,0x1008
.empty:
    mov [rsp+32],rax
    mov [rsp+40],rcx
    mov qword [rsp+48],0
    mov rdi,rsp
    xor esi,esi
    call reist_x64_startup_stack
    add rsp,56
    test rax,rax
    setg al
    movzx eax,al
    ret
.bad:
    xor eax,eax
    ret
; END_PURE_ADMISSION

; Selected immutable catalog pointer, never a caller supplied address.
boot_program_record64:
    movzx eax,byte [rel elf_image_selector]
    sub eax,3
    cmp eax,3
    ja .bad
    imul eax,36896
    lea rdi,[rel boot_program_catalog]
    add rdi,rax
    ret
.bad:
    xor edi,edi
    ret

boot_program_load64:
    call boot_program_record64
    push rdi
    mov esi,36896
    call boot_program_admit64
    pop r12
    cmp eax,1
    jne elf64_load_fail
    mov rax,[r12+16]
    mov [rel elf_entry_address],rax
    mov rax,[r12+24]
    mov [rel elf_page_flags],rax
    mov byte [rel elf_entry_is_executable],1
    mov byte [rel elf_load_segment_count],1
    xor ebx,ebx
.page:
    cmp byte [r12+rbx+24],0
    je .next
    call physical_frame_alloc64
    test rax,rax
    jz elf64_load_oom
    lea rdx,[rel elf_page_frames]
    mov [rdx+rbx*8],rax ; ownership precedes copy and next acquisition
    mov rdi,DIRECT_MAP_BASE
    add rdi,rax
    mov esi,ebx
    shl esi,12
    lea rsi,[r12+rsi+32]
    mov ecx,512
    rep movsq
.next:
    inc ebx
    cmp ebx,8
    jb .page
    mov qword [rel elf_last_load_error],0
    mov eax,1
    ret

; SysV: destination mapped private stack page RDI; preserves callee-saved.
global x86_64_boot_program_stack64
x86_64_boot_program_stack64:
    push rbx
    mov rbx,rdi
    call boot_program_record64
    test rdi,rdi
    jz .bad
    sub rsp,64
    lea rax,[rdi+32800]
    mov [rsp],rax
    mov [rsp+8],rbx
    mov qword [rsp+16],0x1000
    mov qword [rsp+24],0x409000
    xor eax,eax
    mov rcx,[rdi+32800]
    test rcx,rcx
    jz .empty
    mov eax,0x1008
.empty:
    mov [rsp+32],rax
    mov [rsp+40],rcx
    mov qword [rsp+48],0
    mov rdi,rsp
    mov esi,1
    call reist_x64_startup_stack
    add rsp,64
    pop rbx
    ret
.bad:
    xor eax,eax
    pop rbx
    ret
