; Device34 adapter; requests cannot select hardware addresses or kernel modes.
extern native_video_fifo_pt,native_video_ranges,native_video_range_count
extern native_video_ranges_inverse,native_video_count_inverse,native_vga_ready
global native_video_call,native_video_platform,native_video_syscall64
native_video_call64:
    push rbp
    mov rbp,rsp
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    mov rax,[rel native_video_range_count]
    not rax
    cmp rax,[rel native_video_count_inverse]
    jne scheduler_fail
    lea rsi,[rel native_video_ranges]
    lea rdi,[rel native_video_ranges_inverse]
    mov ecx,96
.map_seal:
    lodsq
    not rax
    cmp rax,[rdi]
    jne scheduler_fail
    add rdi,8
    loop .map_seal
    lea rdi,[rel native_video_platform]
    lea rax,[rel pdpt_table]
    mov [rdi],rax
    lea rax,[rel native_display_pd]
    mov [rdi+8],rax
    lea rax,[rel native_display_pts]
    mov [rdi+16],rax
    lea rax,[rel native_video_fifo_pt]
    mov [rdi+24],rax
    lea rax,[rel native_display_boot]
    mov [rdi+32],rax
    lea rax,[rel native_display_boot_inverse]
    mov [rdi+40],rax
    lea rax,[rel native_video_ranges]
    mov [rdi+48],rax
    mov rax,[rel native_video_range_count]
    mov [rdi+56],rax
    lea rax,[rel native_video_fence_display64]
    mov [rdi+64],rax
    lea rax,[rel native_vga_ready]
    mov [rdi+72],rax
    mov [rel native_video_call+104],rdi
    mov rax,[rel scheduler_last_tick]
    imul rax,10
    mov [rel native_video_call+72],rax
    sub rsp,16
    and rsp,-16
    lea rdi,[rel native_video_call]
    mov rax,C_NATIVE_VIDEO_ENTRY
    call rax
    cmp eax,1
    jne scheduler_fail
    mov rax,[rel native_video_call+96]
    lea rsp,[rbp-64]
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbp
    ret
native_video_fence_display64:
    mov rsi,rdi
    lea rdi,[rel native_display_state]
    jmp native_display_core_fence64
native_video_clear64:
    push rax
    push rcx
    push rdi
    xor eax,eax
    lea rdi,[rel native_video_call]
    mov ecx,(112+80)/8
    rep stosq
    pop rdi
    pop rcx
    pop rax
    ret
native_video_syscall64:
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
    lea rdi,[rel native_video_call]
    mov ecx,8
    rep movsq
    cmp dword [rel native_video_call+8],1
    jne .invoke
    mov qword [rel native_video_call+88],5
    call native_video_call64
    xor r8d,r8d
    test rax,rax
    jz .old_reaped
    ; Core admits only driver slot5; no untrusted index reaches task memory.
    cmp eax,5
    jne scheduler_fail
    shr rax,32
    lea rdi,[rel scheduler_tasks+5*NATIVE_TASK_BYTES]
    cmp qword [rdi+TASK_STATE],TASK_FREE
    je .old_reaped
    cmp [rdi+TASK_GENERATION],rax
    jbe .target
.old_reaped:
    or r8d,1
.target:
    mov rax,[rel native_video_call+16]
    cmp eax,5
    jne .relation
    shr rax,32
    lea rdi,[rel scheduler_tasks+5*NATIVE_TASK_BYTES]
    cmp [rdi+TASK_GENERATION],rax
    jne .relation
    cmp qword [rdi+TASK_STATE],TASK_READY
    je .parent
    cmp qword [rdi+TASK_STATE],TASK_BLOCKED
    jne .relation
.parent:
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    cmp [rel family_records+5*64+8],rax
    jne .relation
    or r8d,2
.relation:
    mov [rel native_video_call+80],r8
.invoke:
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    mov [rel native_video_call+64],rax
    mov qword [rel native_video_call+88],0
    call native_video_call64
    jmp .result
.pointer: mov rax,-14
    jmp .result
.invalid: mov rax,-22
.result:
    call native_video_clear64
    jmp process_run_resume64
native_video_terminal64:
    push rax
    push rdx
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    mov edx,[rel scheduler_current_slot]
    or rax,rdx
    mov [rel native_video_call+64],rax
    mov qword [rel native_video_call+88],1
    call native_video_call64
    call native_video_clear64
    pop rdx
    pop rax
    ret
native_video_finish64:
    mov qword [rel native_video_call+88],2
    call native_video_call64
    call native_video_clear64
    ret
native_video_reserve64:
    mov qword [rel native_video_call+88],3
    jmp native_video_update64
native_video_publish64:
    mov qword [rel native_video_call+88],4
native_video_update64:
    push rcx
    mov eax,[rel native_display_request+48]
    mov [rel native_video_call],eax
    mov eax,[rel native_display_request+52]
    mov [rel native_video_call+4],eax
    movzx eax,word [rel native_display_request+56]
    mov [rel native_video_call+8],eax
    movzx eax,word [rel native_display_request+58]
    mov [rel native_video_call+12],eax
    call native_video_call64
    call native_video_clear64
    pop rcx
    ret
section .bss
alignb 8
native_video_call: resb 112
native_video_platform: resb 80
section .text
