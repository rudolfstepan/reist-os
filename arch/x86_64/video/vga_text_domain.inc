; Pointer/device adapter. All calls execute with IF0 after syscall-profile admission.
%include "arch/x86_64/video/vga_text_core.inc"
global native_vga_state,native_vga_syscall64
extern native_vga_status64
extern native_vga_status_lock
native_vga_syscall64:
    lea rdi,[rel native_vga_state]
    call native_vga_core_admit64
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
    lea rdi,[rel native_vga_request]
    mov ecx,8
    rep movsq
    mov eax,[rel native_vga_request+8]
    cmp eax,4
    jb .bound_buffer
    cmp eax,6
    ja .bound_buffer
    mov edx,[rel native_vga_request+40]
    test edx,edx
    jz .invalid
    mov ecx,PF_R
    cmp eax,6
    jne .bytes
    cmp edx,80
    ja .invalid
    shl edx,1
    jmp .range
.bytes:
    cmp edx,64
    ja .invalid
    cmp eax,4
    jne .range
    mov ecx,PF_W
.range:
    mov rax,[rel native_vga_request+32]
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
.bound_buffer:
    xor r8d,r8d
    cmp dword [rel native_vga_request+8],1
    jne .invoke
    mov rax,[rel native_vga_state]
    test rax,rax
    jz .old_reaped
    mov ecx,eax
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
    mov rax,[rel native_vga_request+16]
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
    mov ecx,[rel native_vga_request+16]
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
    mov r13,[rel native_vga_state+24]
    lea rdi,[rel native_vga_state]
    lea rsi,[rel native_vga_request]
    mov rdx,[r12+TASK_GENERATION]
    shl rdx,32
    mov eax,[rel scheduler_current_slot]
    or rdx,rax
    mov rcx,[rel scheduler_last_tick]
    imul rcx,10
    call native_vga_core_apply64
    cmp rax,-84
    je scheduler_fail
    test rax,rax
    jnz .result
    mov eax,[rel native_vga_request+8]
    cmp eax,9
    je .cursor
    cmp eax,4
    jb .zero
    cmp eax,6
    ja .zero
    cmp eax,6
    je .cells
    lea rdi,[rel native_vga_state]
    mov rsi,[rel native_vga_request+32]
    mov edx,[rel native_vga_request+40]
    lea ecx,[eax-3]
    call native_vga_core_transfer64
    cmp rax,-84
    je scheduler_fail
    jmp .result
.cells:
    ; Complete range/authority validation precedes the first hardware write.
    mov rsi,[rel native_vga_request+32]
    mov ecx,[rel native_vga_request+40]
    mov eax,[rel native_vga_request+44]
    mov rdi,0xffffffff800b8000
    lea rdi,[rdi+rax*2]
    rep movsw
    jmp .zero
.cursor:
    ; Validated mode03 location only: no caller-controlled port or register.
    ; IF0 keeps the two CRTC index/data pairs together.
    mov ecx,[rel native_vga_request+44]
    mov dx,0x3d4
    mov al,0x0e
    out dx,al
    inc dx
    mov al,ch
    out dx,al
    dec dx
    mov al,0x0f
    out dx,al
    inc dx
    mov al,cl
    out dx,al
.zero:
    cmp dword [rel native_vga_request+8],2
    je .stopped
    cmp dword [rel native_vga_request+8],7
    jne .success
    test r13,r13
    jnz .success
    mov byte [rel native_vga_status_lock],0
    lea rsi,[rel native_vga_ready_message]
    call native_vga_status64
    jmp .success
.stopped:
    mov byte [rel native_vga_status_lock],1
    lea rsi,[rel native_vga_stopped_message]
    call native_vga_status64
.success:
    xor eax,eax
    jmp .result
.invalid: mov rax,-22
    jmp .result
.pointer: mov rax,-14
.result:
    push rax
    lea rdi,[rel native_vga_request]
    xor eax,eax
    mov ecx,8
    rep stosq
    pop rax
    jmp process_run_resume64

native_vga_terminal64:
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push qword [rel native_vga_state+24]
    lea rdi,[rel native_vga_state]
    mov rsi,[r12+TASK_GENERATION]
    shl rsi,32
    mov eax,[rel scheduler_current_slot]
    or rsi,rax
    call native_vga_core_fence64
    test rax,rax
    jnz scheduler_fail
    pop rax
    cmp rax,1
    je .restore
    cmp qword [rel native_vga_state+24],1
    jne .restore
    mov byte [rel native_vga_status_lock],1
    lea rsi,[rel native_vga_stopped_message]
    call native_vga_status64
.restore:
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    ret

native_vga_finish64:
    lea rdi,[rel native_vga_state]
    call native_vga_core_admit64
    test rax,rax
    jnz scheduler_fail
    cmp qword [rdi+24],1
    jne scheduler_fail
    push qword [rdi+16]
    call native_vga_core_init64
    pop qword [rdi+16]
    jmp native_vga_core_seal64

section .rodata
native_vga_ready_message: db "VGA CONSOLE READY - native64 text shell",0
native_vga_stopped_message: db "VGA CONSOLE STOPPED - supervised recovery / COM1 rescue",0
section .data
align 8
native_vga_state:
    dq 0,0,0,1,0,0,0,0,0,0
    dq -1,-1,-1,-2,-1,-1,-1,-1,-1,-1
    times 2112 db 0
section .bss
alignb 8
native_vga_request: resb 64
section .text
