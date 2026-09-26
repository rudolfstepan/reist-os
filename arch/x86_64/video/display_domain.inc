; Opt-in syscall and retirement adapter. Kernel copy only; no user MMIO PTE.
%include "arch/x86_64/video/display_core.inc"
extern native_display_boot,native_display_boot_inverse
extern native_display_pd,native_display_pts,pdpt_table

native_display_boot_admit64:
    lea rdi,[rel native_display_boot]
    lea rsi,[rel native_display_boot_inverse]
    cmp qword [rdi],0
    je .absent
    mov ecx,4
.word:
    mov rax,[rdi]
    not rax
    cmp [rsi],rax
    jne scheduler_fail
    add rdi,8
    add rsi,8
    loop .word
    mov rax,[rel pdpt_table+509*8]
    and rax,~0x60
    mov edx,native_display_pd
    or edx,3
    cmp rax,rdx
    jne scheduler_fail
    mov eax,[rel native_display_boot+8]
    mov [rel native_display_pitch],rax
    xor eax,eax
    ret
.absent:
    mov rax,[rel pdpt_table+509*8]
    test rax,rax
    jnz scheduler_fail
    mov rax,-19
    ret

; RAX byte offset in LFB, all fields already boot-admitted and pinned.
native_display_leaf64:
    shr rax,12
    mov rdx,rax
    shr rdx,9
    cmp edx,6
    jae scheduler_fail
    lea rsi,[rel native_display_pd]
    mov rsi,[rsi+rdx*8]
    and rsi,~0x60
    shl rdx,12
    add edx,native_display_pts
    or edx,3
    cmp rsi,rdx
    jne scheduler_fail
    lea rsi,[rel native_display_pts]
    mov rsi,[rsi+rax*8]
    and rsi,~0x60
    shl rax,12
    mov edx,[rel native_display_boot+24]
    add rax,rdx
    mov rdx,0x800000000000001b
    or rax,rdx
    cmp rax,rsi
    jne scheduler_fail
    ret

; RDI user base, ESI bytes. Reuse unchanged <=2060-byte pointer admission.
; Complete all <=16 chunks before copying; overflow is rejected up front.
global native_display_user_tile_range64
native_display_user_tile_range64:
    test esi,esi
    jz .invalid
    cmp esi,16384
    ja .invalid
    mov r8,rdi
    mov r9d,esi
    mov rax,rdi
    add rax,r9
    jc .invalid
.chunk:
    mov edx,1024
    cmp r9,rdx
    cmovb rdx,r9
    mov rax,r8
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .invalid
    add r8,rdx
    sub r9,rdx
    jnz .chunk
    mov eax,1
    ret
.invalid:
    xor eax,eax
    ret

native_display_syscall64:
    call native_display_boot_admit64
    test rax,rax
    jnz .result
    lea rdi,[rel native_display_state]
    call native_display_core_admit64
    test rax,rax
    jnz scheduler_fail
    mov rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz .invalid
    mov rax,[rel syscall_rsi]
    mov edx,64
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    mov rsi,[rel syscall_rsi]
    lea rdi,[rel native_display_request]
    mov ecx,8
    rep movsq
%ifdef REIST_NATIVE_DISPLAY_INFO
    cmp dword [rel native_display_request],2
    jne .info_pointer_ready
    cmp dword [rel native_display_request+8],5
    jne .info_pointer_ready
    mov rax,[rel syscall_rsi]
    mov edx,64
    mov ecx,PF_W
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
.info_pointer_ready:
%endif
    cmp dword [rel native_display_request+8],3
    jne .shape_ready
    lea rdi,[rel native_display_request]
    mov esi,[rel native_display_boot+12]
    mov edx,[rel native_display_boot+16]
    call native_display_rectangle64
    test eax,eax
    jz .invalid
    mov [rel native_display_tile_bytes],eax
    mov esi,eax
    mov rdi,[rel native_display_request+40]
    call native_display_user_tile_range64
    cmp eax,1
    jne .pointer
    mov rsi,[rel native_display_request+40]
    lea rdi,[rel native_display_tile]
    mov ecx,[rel native_display_tile_bytes]
    rep movsb
.shape_ready:
    xor r8d,r8d
    cmp dword [rel native_display_request+8],1
    jne .invoke
    ; No bind may precede old reap, even when the old generation is fenced.
    mov rax,[rel native_display_state]
    test rax,rax
    jz .old_reaped
    mov ecx,eax
    cmp ecx,2
    jb scheduler_fail
    cmp ecx,7
    ja scheduler_fail
    shl ecx,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    add rdi,rcx
    shr rax,32
    cmp qword [rdi+TASK_STATE],TASK_FREE
    je .old_reaped
    cmp [rdi+TASK_GENERATION],rax
    jbe .target
.old_reaped:
    or r8d,1
.target:
    mov rax,[rel native_display_request+16]
    mov ecx,eax
    cmp ecx,2
    jb .invoke
    cmp ecx,7
    ja .invoke
    shl ecx,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    add rdi,rcx
    shr rax,32
    cmp [rdi+TASK_GENERATION],rax
    jne .invoke
    cmp qword [rdi+TASK_STATE],TASK_READY
    je .parent
    cmp qword [rdi+TASK_STATE],TASK_BLOCKED
    jne .invoke
.parent:
    mov ecx,[rel native_display_request+16]
    shl ecx,6
    lea rdi,[rel family_records]
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    cmp [rdi+rcx+8],rax
    jne .invoke
    or r8d,2
.invoke:
    lea rdi,[rel native_display_state]
    lea rsi,[rel native_display_request]
    mov rdx,[r12+TASK_GENERATION]
    shl rdx,32
    mov eax,[rel scheduler_current_slot]
    or rdx,rax
    mov rcx,[rel scheduler_last_tick]
    imul rcx,10
    call native_display_core_apply64
    cmp rax,-84
    je scheduler_fail
    test rax,rax
    jnz .result
%ifdef REIST_NATIVE_DISPLAY_INFO
    cmp dword [rel native_display_request+8],5
    jne .not_info
    ; Both complete user ranges admitted, owner/epoch validated, no quota use.
    mov eax,[rel native_display_boot+12]
    mov [rel native_display_request+32],eax
    mov eax,[rel native_display_boot+16]
    mov [rel native_display_request+36],eax
    mov eax,[rel native_display_boot+8]
    mov [rel native_display_request+40],eax
    mov dword [rel native_display_request+44],32
    mov dword [rel native_display_request+48],16
    mov dword [rel native_display_request+52],8
    lea rsi,[rel native_display_request]
    mov rdi,[rel syscall_rsi]
    mov ecx,8
    rep movsq
    xor eax,eax
    jmp .result
.not_info:
%endif
    cmp dword [rel native_display_request+8],3
    jne .result
%ifdef REIST_NATIVE_VIDEO_MODE
    call native_video_reserve64
    test rax,rax
    jnz .result
%endif
    ; Validate all touched leaves before the first MMIO store.
    xor r10d,r10d
.check_row:
    mov eax,[rel native_display_request+52]
    add eax,r10d
    imul rax,qword [rel native_display_pitch]
    mov edx,[rel native_display_request+48]
    lea r11,[rax+rdx*4]
    mov rax,r11
    call native_display_leaf64
    mov eax,[rel native_display_request+60]
    lea rax,[r11+rax-1]
    call native_display_leaf64
    inc r10d
    movzx eax,word [rel native_display_request+58]
    cmp r10d,eax
    jb .check_row
    xor r10d,r10d
    lea rsi,[rel native_display_tile]
.copy_row:
    mov eax,[rel native_display_request+52]
    add eax,r10d
    imul rax,qword [rel native_display_pitch]
    mov edx,[rel native_display_request+48]
    lea rdi,[rax+rdx*4]
    mov rax,0xffffffff40000000
    add rdi,rax
    movzx ecx,word [rel native_display_request+56]
    rep movsd
    inc r10d
    movzx eax,word [rel native_display_request+58]
    cmp r10d,eax
    jb .copy_row
    mfence
    inc qword [rel native_display_commits]
%ifdef REIST_NATIVE_VIDEO_MODE
    call native_video_publish64
    test rax,rax
    jnz .result
%endif
    xor eax,eax
    jmp .result
.invalid:
    mov rax,-22
    jmp .result
.pointer:
    mov rax,-14
.result:
    push rax
    xor eax,eax
    lea rdi,[rel native_display_request]
    mov ecx,(64+16384+8)/8
    rep stosq
    pop rax
    jmp process_run_resume64

native_display_terminal64:
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    lea rdi,[rel native_display_state]
    mov rsi,[r12+TASK_GENERATION]
    shl rsi,32
    mov eax,[rel scheduler_current_slot]
    or rsi,rax
    call native_display_core_fence64
    test rax,rax
    jnz scheduler_fail
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    ret

native_display_finish64:
    lea rdi,[rel native_display_state]
    call native_display_core_admit64
    test rax,rax
    jnz scheduler_fail
    cmp qword [rdi+24],1
    jne scheduler_fail
    mov r10,[rdi+16]
    call native_display_core_init64
    mov [rdi+16],r10
    call native_display_core_seal64
    inc qword [rel native_display_finishes]
    ret

section .data
align 8
global native_display_state,native_display_commits,native_display_finishes
native_display_state:
    dq 0,0,0,1,0,0,0,0
    dq -1,-1,-1,-2,-1,-1,-1,-1
native_display_commits: dq 0
native_display_finishes: dq 0
section .bss
alignb 8
native_display_request: resb 64
native_display_tile: resb 16384
native_display_tile_bytes: resq 1
native_display_pitch: resq 1
section .text
