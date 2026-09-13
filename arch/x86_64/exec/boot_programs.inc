; SysV, pinned immutable36896-byte record. No user pointer or ELF parsing.
; Return1 iff complete fixed metadata/argument admission, no writes.
global boot_program_admit64
boot_program_admit64:
%ifdef REIST_NATIVE_WIDE
    cmp rsi,NATIVE_PREPARED_V2_BYTES
    je boot_program_admit_v2_64
%endif
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
%ifdef REIST_NATIVE_WIDE
; Independent bounded mapping metadata admission; never an ELF parser.
boot_program_admit_v2_64:
    test rdi,rdi
    jz .bad
    test rdi,15
    jnz .bad
    mov rax,rdi
    add rax,NATIVE_PREPARED_V2_BYTES
    jc .bad
    mov rax,0x0000327647504e52
    cmp [rdi],rax
    jne .bad
    cmp dword [rdi+8],2
    jne .bad
    cmp dword [rdi+12],NATIVE_PREPARED_V2_BYTES
    jne .bad
    cmp qword [rdi+88],0
    jne .bad
    mov rax,[rdi+16]
    sub rax,0x400000
    cmp rax,262144
    jae .bad
    shr eax,12
    cmp byte [rdi+rax+24],5
    jne .bad
    xor ecx,ecx
.flags:
    movzx eax,byte [rdi+rcx+24]
    cmp ecx,7
    jb .ordinary
    cmp ecx,15
    ja .ordinary
    cmp ecx,9
    jb .guard
    cmp eax,6
    jne .bad
    jmp .next
.guard:
    test eax,eax
    jnz .bad
    jmp .next
.ordinary:
    test eax,eax
    jz .next
    sub eax,4
    cmp eax,2
    ja .bad
.next:
    inc ecx
    cmp ecx,64
    jb .flags
    lea rdx,[rdi+96+7*4096]
    mov ecx,9*512
.zero_stack:
    cmp qword [rdx],0
    jne .bad
    add rdx,8
    dec ecx
    jnz .zero_stack
    sub rsp,56
    lea rax,[rdi+262240]
    mov [rsp],rax
    lea rax,[rdi+96]
    mov [rsp+8],rax
    mov qword [rsp+16],0x1000
    mov qword [rsp+24],0x410000
    xor eax,eax
    mov rcx,[rdi+262240]
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
%endif
; END_PURE_ADMISSION

; Selected immutable catalog pointer, never a caller supplied address.
boot_program_record64:
    movzx eax,byte [rel elf_image_selector]
    sub eax,3
    cmp eax,3
    ja .bad
    imul eax,NATIVE_IMPORT_BYTES
    lea rdi,[rel boot_program_catalog]
    add rdi,rax
    ret
.bad:
    xor edi,edi
    ret

boot_program_load64:
%ifdef REIST_NATIVE_LIFECYCLE
    cmp byte [rel elf_image_selector],7
    jb .catalog
    lea rdi,[rel elf_import_record]
    jmp .record
.catalog:
%endif
    call boot_program_record64
.record:
    push rdi
%ifdef REIST_NATIVE_WIDE
    mov esi,[rdi+12]
%else
    mov esi,36896
%endif
    call boot_program_admit64
    pop r12
    cmp eax,1
    jne elf64_load_fail
    mov rax,[r12+16]
    mov [rel elf_entry_address],rax
    mov rax,[r12+24]
    mov [rel elf_page_flags],rax
%ifdef REIST_NATIVE_WIDE
    mov r13d,8
    mov r14d,32
    cmp dword [r12+8],2
    jne .layout_ready
    mov r13d,64
    mov r14d,96
    lea rsi,[r12+24]
    lea rdi,[rel elf_page_flags]
    mov ecx,8
    rep movsq
.layout_ready:
%endif
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
%ifdef REIST_NATIVE_WIDE
    add rsi,r14
    add rsi,r12
%else
    lea rsi,[r12+rsi+32]
%endif
    mov ecx,512
    rep movsq
.next:
    inc ebx
%ifdef REIST_NATIVE_WIDE
    cmp ebx,r13d
%else
    cmp ebx,8
%endif
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
%ifdef REIST_NATIVE_WIDE
    lea rax,[rdi+262240]
%else
    lea rax,[rdi+32800]
%endif
    mov [rsp],rax
    mov [rsp+8],rbx
    mov qword [rsp+16],0x1000
%ifdef REIST_NATIVE_WIDE
    mov qword [rsp+24],0x410000
%else
    mov qword [rsp+24],0x409000
%endif
    xor eax,eax
%ifdef REIST_NATIVE_WIDE
    mov rcx,[rdi+262240]
%else
    mov rcx,[rdi+32800]
%endif
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
