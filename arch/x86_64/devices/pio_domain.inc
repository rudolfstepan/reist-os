; Pure SysV fixed-request admission. Device protocol stays in Ring3.
global native_pio_admit64
native_pio_admit64:
    cmp dword [rdi],1
    jne .bad
    cmp dword [rdi+4],64
    jne .bad
    mov eax,[rdi+12]
    or eax,[rdi+36]
    mov rcx,[rdi+48]
    or rcx,[rdi+56]
    or rax,rcx
    jnz .bad
    mov rax,[rdi+16]
    cmp eax,2
    jb .bad
    cmp eax,3
    ja .bad
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .bad
    mov eax,[rdi+8]
    cmp eax,1
    je .control
    cmp eax,5
    je .control
    cmp eax,4
    je .words
    cmp qword [rdi+40],0
    jne .bad
    cmp dword [rdi+32],0
    jne .bad
    cmp eax,2
    je .read
    cmp eax,3
    jne .bad
    mov eax,[rdi+28]
    cmp eax,255
    ja .bad
    mov ecx,[rdi+24]
    cmp ecx,0x1f2
    je .count
    cmp ecx,0x1f3
    jb .bad
    cmp ecx,0x1f5
    jbe .ok
    cmp ecx,0x1f6
    je .master
    cmp ecx,0x1f7
    je .command
    cmp ecx,0x3f6
    jne .bad
    cmp eax,2
    je .ok
    cmp eax,6
    je .ok
    jmp .bad
.command:
    cmp eax,0xec
    je .ok
    cmp eax,0x20
    je .ok
    jmp .bad
.master:
    and eax,0xf0
    cmp eax,0xe0
    je .ok
    jmp .bad
.count:
    cmp eax,1
    je .ok
    jmp .bad
.read:
    cmp dword [rdi+28],0
    jne .bad
    mov eax,[rdi+24]
    cmp eax,0x3f6
    je .ok
    sub eax,0x1f1
    cmp eax,6
    jbe .ok
    jmp .bad
.words:
    cmp dword [rdi+24],0x1f0
    jne .bad
    cmp dword [rdi+28],0
    jne .bad
    mov eax,[rdi+32]
    dec eax
    cmp eax,15
    ja .bad
    mov rax,[rdi+40]
    test rax,rax
    jz .bad
    test al,1
    jnz .bad
    add rax,32
    jc .bad
    jmp .ok
.control:
    mov rax,[rdi+24]
    or rax,[rdi+32]
    or rax,[rdi+40]
    jnz .bad
.ok:
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret

; Shared read-only integrity admission, also mandatory before lifecycle cleanup.
; RDI pinned state64; only RAX is clobbered. No port or metadata side effects.
global native_pio_state_admit64
native_pio_state_admit64:
    mov rax,[rdi]
    not rax
    cmp rax,[rdi+8]
    jne .bad
    cmp qword [rdi+16],1
    ja .bad
    cmp qword [rdi+40],64
    ja .bad
    cmp qword [rdi+56],0
    jne .bad
    mov rax,1<<60
    cmp [rdi+32],rax
    jae .bad
    mov rax,[rdi+48]
    cmp rax,[rdi+32]
    ja .bad
    mov rax,[rdi+24]
    cmp rax,[rdi+32]
    ja .bad
    mov rax,[rdi]
    test rax,rax
    jnz .owner
    cmp qword [rdi+16],1
    jne .bad
    mov rax,[rdi+24]
    or rax,[rdi+32]
    or rax,[rdi+40]
    or rax,[rdi+48]
    jnz .bad
    jmp .ok
.owner:
    cmp eax,2
    jb .bad
    cmp eax,3
    ja .bad
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .bad
.ok:
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret

; State64: owner/inverse/fenced/window/last/count/reset_tick/reserved.
; RDI state, RSI pinned request, RDX caller handle, RCX monotonic PIT tick,
; R8 bind witness bits (1 old generation reaped,2 target live). All pointers
; are trusted pinned objects; the runtime adapter validates user buffers.
global native_pio_apply64
native_pio_apply64:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    sub rsp,8
    mov r12,rdi
    mov r13,rsi
    mov r14,rdx
    mov r15,rcx
    mov rbx,r8
    call native_pio_state_admit64
    cmp eax,1
    jne .corrupt
    mov rdi,r13
    call native_pio_admit64
    cmp eax,1
    jne .invalid
    mov rax,1<<60
    cmp r15,rax
    jae .clock
    cmp r15,[r12+32]
    jb .clock
    cmp dword [r13+8],1
    je .bind
    mov rax,[r13+16]
    cmp rax,[r12]
    jne .denied
    cmp dword [r13+8],5
    je .fence_request
    cmp r14,rax
    jne .denied
    cmp qword [r12+16],0
    jne .denied
    cmp dword [r13+8],3
    jne .time
    cmp dword [r13+24],0x3f6
    jne .time
    cmp dword [r13+28],2
    jne .time
    cmp r15,[r12+48]
    jbe .denied
.time:
    mov [r12+32],r15
    mov rax,r15
    sub rax,[r12+24]
    cmp rax,10
    jb .charge
    mov [r12+24],r15
    mov qword [r12+40],0
.charge:
    cmp qword [r12+40],64
    je .quota
    inc qword [r12+40]
    mov edi,[r13+24]
    mov eax,[r13+8]
    cmp eax,2
    je .read8
    cmp eax,4
    je .read16
    mov esi,[r13+28]
    cmp edi,0x3f6
    jne .write
    cmp esi,2
    je .write
.reset:
    mov [r12+48],r15
.write:
    call native_pio_out8
    jmp .ok
.read8:
    call native_pio_in8
    movzx eax,al
    jmp .return
.read16:
    xor ebp,ebp
.word:
    mov edi,0x1f0
    call native_pio_in16
    mov rdx,[r13+40]
    mov [rdx+rbp*2],ax
    inc ebp
    cmp ebp,[r13+32]
    jb .word
.transfer_done:
    jmp .ok
.bind:
    test r14d,r14d
    jnz .denied
    cmp ebx,3
    jne .denied
    cmp qword [r12+16],1
    jne .denied
    mov rax,[r13+16]
    cmp rax,[r12]
    je .denied
    mov [r12],rax
    not rax
    mov [r12+8],rax
    mov qword [r12+16],0
    mov [r12+24],r15
    mov [r12+32],r15
    mov qword [r12+40],0
    mov [r12+48],r15
    mov edi,0x3f6
    mov esi,6
    call native_pio_out8
    jmp .ok
.fence_request:
    test r14d,r14d
    jnz .denied
    call .fence
.ok:
    xor eax,eax
    jmp .return
.clock:
    call .fence
    jmp .corrupt
.quota:
    call .fence
    mov rax,-11
    jmp .return
.fence:
    cmp qword [r12+16],1
    je .fence_done
    mov qword [r12+16],1
    mov edi,0x3f6
    mov esi,6
    sub rsp,8
    call native_pio_out8
    add rsp,8
.fence_done:
    ret
.invalid:
    mov rax,-22
    jmp .return
.denied:
    mov rax,-13
    jmp .return
.corrupt:
    mov rax,-84
.return:
    add rsp,8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret
; END_PIO_CORE

; Runtime adapter: no protocol parsing, allocation or wait in Ring0.
native_pio_in8:
    mov edx,edi
    xor eax,eax
    in al,dx
    ret
native_pio_in16:
    mov edx,edi
    xor eax,eax
    in ax,dx
    ret
native_pio_out8:
    mov edx,edi
    mov eax,esi
    out dx,al
.done:
    ret

native_pio_syscall64:
    lea rdi,[rel native_pio_state]
    call native_pio_state_admit64
    cmp eax,1
    jne native_pio_fail64
    cmp qword [rel syscall_rdi],29
    jne process_run_syscall64.invalid
    mov rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz process_run_syscall64.invalid
    mov rax,[rel syscall_rsi]
    mov edx,64
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    mov rsi,[rel syscall_rsi]
    lea rdi,[rel native_pio_request]
    mov ecx,8
    rep movsq
    lea rdi,[rel native_pio_request]
    call native_pio_admit64
    cmp eax,1
    jne .invalid
    cmp dword [rel native_pio_request+8],4
    jne .buffer_ready
    mov rax,[rel native_pio_request+40]
    mov edx,[rel native_pio_request+32]
    shl edx,1
    mov ecx,PF_W
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
.buffer_ready:
    xor r8d,r8d
    cmp dword [rel native_pio_request+8],1
    jne .invoke
    ; A generation can only be replaced after its task retirement completed.
    mov rax,[rel native_pio_state]
    test rax,rax
    jz .old_reaped
    mov ecx,eax
    sub ecx,2
    cmp ecx,1
    ja native_pio_fail64
    add ecx,2
    shl ecx,8
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
    mov rax,[rel native_pio_request+16]
    mov ecx,eax
    shl ecx,8
    lea rdi,[rel scheduler_tasks]
    add rdi,rcx
    shr rax,32
    cmp [rdi+TASK_GENERATION],rax
    jne .invoke
    mov rax,[rdi+TASK_STATE]
    cmp rax,TASK_READY
    je .owned
    cmp rax,TASK_BLOCKED
    jne .invoke
.owned:
    mov ecx,[rel native_pio_request+16]
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
    mov rdx,[r12+TASK_GENERATION]
    shl rdx,32
    mov eax,[rel scheduler_current_slot]
    or rdx,rax
    lea rdi,[rel native_pio_state]
    lea rsi,[rel native_pio_request]
    mov rcx,[rel scheduler_last_tick]
    call native_pio_apply64
    cmp rax,-84
    je native_pio_fail64
    jmp .result
.invalid:
    mov rax,-22
    jmp .result
.pointer:
    mov rax,-14
.result:
    push rax
    lea rdi,[rel native_pio_request]
    xor eax,eax
    mov ecx,8
    rep stosq
    pop rax
    jmp process_run_resume64

; Called before any task/profile retirement. Preserve the lifecycle adapter's
; registers. Root loss fences immediately, even before child cancellation.
native_pio_terminal64:
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    lea rdi,[rel native_pio_state]
    call native_pio_state_admit64
    cmp eax,1
    jne native_pio_fail64
    mov rax,[rel native_pio_state]
    test rax,rax
    jz .done
    cmp dword [rel scheduler_current_slot],0
    je .fence
    mov ecx,[rel scheduler_current_slot]
    cmp eax,ecx
    jne .done
    shr rax,32
    cmp [r12+TASK_GENERATION],rax
    je .fence
    jb native_pio_fail64
    ; A newer task may die before BIND. Leave the already-fenced older owner
    ; intact; never forgive an unfenced or future-generation mismatch.
    cmp qword [rel native_pio_state+16],1
    jne native_pio_fail64
    jmp .done
.fence:
    cmp qword [rel native_pio_state+16],1
    je .done
    mov qword [rel native_pio_state+16],1
    mov edi,0x3f6
    mov esi,6
    call native_pio_out8
.done:
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    ret

native_pio_finish64:
    lea rdi,[rel native_pio_state]
    call native_pio_state_admit64
    cmp eax,1
    jne native_pio_fail64
    cmp qword [rel native_pio_state+16],1
    jne native_pio_fail64
    cmp qword [rel scheduler_tasks+512+TASK_STATE],TASK_FREE
    jne native_pio_fail64
    cmp qword [rel scheduler_tasks+768+TASK_STATE],TASK_FREE
    jne native_pio_fail64
    lea rdi,[rel native_pio_state]
    xor eax,eax
    mov ecx,8
    rep stosq
    mov qword [rel native_pio_state+8],-1
    mov qword [rel native_pio_state+16],1
    ret

; Emergency fencing is independent of all possibly corrupt domain metadata.
; One bounded physical operation, no heap, ownership traversal or cleanup.
global native_pio_emergency_fence64
native_pio_emergency_fence64:
    cli
    mov edi,0x3f6
    mov esi,6
    call native_pio_out8
    ret

; Kernel corruption never enters the bootstrap's recoverable force-cleanup.
; Keep damaged records for diagnosis and halt this instance after fencing.
extern serial_init64
extern halt64
native_pio_fail64:
    call native_pio_emergency_fence64
    call serial_init64
    lea rsi,[rel native_pio_fatal_message]
    call serial_write64
    jmp halt64

section .data
native_pio_fatal_message: db "REIST_X86_64_EXCEPTION_FATAL pio=1",13,10,0
align 8
native_pio_state: dq 0,-1,1,0,0,0,0,0
section .bss
alignb 8
native_pio_request: resb 64
section .text
