; Pure SysV fixed-request admission. Device protocol stays in Ring3.
global native_pio_admit64
native_pio_admit64:
    mov eax,[rdi]
    dec eax
    cmp eax,2
    ja .bad
    cmp dword [rdi+4],64
    jne .bad
    mov eax,[rdi+12]
    or eax,[rdi+36]
    mov rcx,[rdi+56]
    cmp dword [rdi],3
    je .throughput_format
    cmp dword [rdi],2
    je .deadline_format
    or rcx,[rdi+48]
    jmp .reserved
.throughput_format:
    cmp dword [rdi+8],1
    jne .bad
    cmp qword [rdi+48],128
    jne .bad
    jmp .reserved
.deadline_format:
    cmp qword [rdi+48],0
    je .bad
    mov edx,[rdi+8]
    sub edx,2
    cmp edx,2
    ja .bad
.reserved:
    or rax,rcx
    jnz .bad
    mov rax,[rdi+16]
    cmp eax,2
    jb .bad
%ifdef REIST_NATIVE_POOL_PIO
    cmp eax,NATIVE_POOL_TASKS-1
%else
    cmp eax,3
%endif
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
    cmp qword [rdi+56],0
    je .legacy_quota
    mov rax,0xffffff7f00000080
    cmp [rdi+56],rax
    jne .bad
    cmp qword [rdi],0
    je .bad
    cmp qword [rdi+40],128
    ja .bad
    jmp .quota_valid
.legacy_quota:
    cmp qword [rdi+40],64
    ja .bad
.quota_valid:
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
%ifdef REIST_NATIVE_POOL_PIO
    cmp eax,NATIVE_POOL_TASKS-1
%else
    cmp eax,3
%endif
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

; State64: owner/inverse/fenced/window/last/count/reset_tick/profile_tag.
; Profile tag0 preserves legacy64; 0xffffff7f00000080 admits128. A fenced
; tag is diagnostic only; rebind selects anew and final reap clears it.
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
    cmp dword [r13],2
    jne .deadline_ready
    ; Same trusted monotonic tick as quota accounting; no second syscall and
    ; no state, quota, port or buffer effect on deadline rejection.
    lea rax,[r15+r15*4]
    add rax,rax
    mov rcx,[r13+48]
    cmp rcx,rax
    jbe .expired
    sub rcx,rax
    cmp rcx,1000
    ja .invalid
.deadline_ready:
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
    mov eax,64
    cmp qword [r12+56],0
    je .quota_selected
    mov eax,128
.quota_selected:
    cmp [r12+40],rax
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
%ifdef REIST_NATIVE_PIO_TRACE
    call native_pio_trace_data64
%endif
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
    mov qword [r12+56],0
    cmp dword [r13],3
    jne .bind_profile_ready
    mov rcx,0xffffff7f00000080
    mov [r12+56],rcx
.bind_profile_ready:
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
.expired:
    mov rax,-110
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
%ifdef REIST_NATIVE_PIO_TRACE
    call native_pio_trace_out64
%endif
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
%ifdef REIST_NATIVE_POOL_PIO
    cmp ecx,NATIVE_POOL_TASKS-3
%else
    cmp ecx,1
%endif
    ja native_pio_fail64
    add ecx,2
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
    mov rax,[rel native_pio_request+16]
    mov ecx,eax
    shl ecx,NATIVE_TASK_SHIFT
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
%ifdef REIST_NATIVE_POOL_PIO
    lea rdx,[rel scheduler_tasks+2*NATIVE_TASK_BYTES+TASK_STATE]
    mov ecx,NATIVE_POOL_TASKS-2
.children_free:
    cmp qword [rdx],TASK_FREE
    jne native_pio_fail64
    add rdx,NATIVE_TASK_BYTES
    loop .children_free
%else
    cmp qword [rel scheduler_tasks+2*NATIVE_TASK_BYTES+TASK_STATE],TASK_FREE
    jne native_pio_fail64
    cmp qword [rel scheduler_tasks+3*NATIVE_TASK_BYTES+TASK_STATE],TASK_FREE
    jne native_pio_fail64
%endif
%ifdef REIST_NATIVE_PIO_TRACE
.trace_before_clear:
%endif
    lea rdi,[rel native_pio_state]
    xor eax,eax
    mov ecx,8
    rep stosq
    mov qword [rel native_pio_state+8],-1
    mov qword [rel native_pio_state+16],1
%ifdef REIST_NATIVE_PIO_TRACE
    call native_pio_trace_clear64
.trace_after_clear:
%endif
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

%ifdef REIST_NATIVE_PIO_TRACE
; BEGIN_PIO_TRACE
; Private diagnostic v1: sequence/error QWords, 64 x 192-byte records.
; No consumer cursor or authority. Physical OUT / IN+store precede capture.
; Every address copied is fixed or from the just-completed admitted READ16.
%macro pio_trace_save 0
    pushfq
    push rax
    push rbx
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
%endmacro
native_pio_trace_out64:
    pio_trace_save
    mov r10d,1
    jmp native_pio_trace_capture64
native_pio_trace_data64:
    pio_trace_save
    mov r10d,2
native_pio_trace_capture64:
    cld
    cmp qword [rel native_pio_trace+8],0
    jne .done
    mov r9,[rel native_pio_trace]
%ifdef REIST_NATIVE_WIDE_FILE
    cmp r9,262144
%else
    cmp r9,4096
%endif
    jae .error
    ; Bounds BEFORE either diagnostic task/family indexing, including fatal OUT.
    mov ecx,[rel scheduler_current_slot]
%ifdef REIST_NATIVE_POOL_PIO
    cmp ecx,NATIVE_POOL_TASKS-1
%else
    cmp ecx,3
%endif
    ja .error
    shl ecx,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    mov rax,[rdi+rcx+8]
    dec rax
    cmp rax,0x7ffffffe
    ja .error
    mov eax,[rel native_pio_state]
    sub eax,2
%ifdef REIST_NATIVE_POOL_PIO
    cmp eax,NATIVE_POOL_TASKS-3
%else
    cmp eax,1
%endif
    ja .error
    cmp r10d,2
    jne .reserve
    lea rax,[rel native_pio_state]
    cmp r12,rax
    jne .error
    lea rax,[rel native_pio_request]
    cmp r13,rax
    jne .error
    cmp dword [r13],2
    jne .error
    cmp dword [r13+4],64
    jne .error
    cmp dword [r13+8],4
    jne .error
    lea rax,[rbp-1]
    cmp rax,15
    ja .error
    cmp ebp,[r13+32]
    jne .error
    ; RDX is the base of the stores that just completed, not a new user pointer.
    mov rax,[r13+40]
    cmp rax,rdx
    jne .error
    test rax,rax
    jz .error
    test al,1
    jnz .error
    add rax,32
    jc .error
.reserve:
    mov eax,r9d
    and eax,63
    imul eax,192
    lea r8,[rel native_pio_trace+16]
    add r8,rax
    mov rdi,r8
    xor eax,eax
    mov ecx,24
    rep stosq
    mov [r8],r10
    lea rdi,[r8+16]
    lea rsi,[rel native_pio_state]
    mov ecx,8
    rep movsq
    cmp r10d,2
    je .data
    mov rax,[rsp+40]             ; original RDX (physical port)
    movzx eax,ax
    mov [r8+80],rax
    mov rax,[rsp+64]             ; original RAX (physical value)
    movzx eax,al
    mov [r8+88],rax
    mov eax,[rel scheduler_current_slot]
    mov [r8+96],rax
    shl eax,NATIVE_TASK_SHIFT
    lea rdi,[rel scheduler_tasks]
    mov rax,[rdi+rax+8]
    mov [r8+104],rax
    mov eax,[rel native_pio_state]
    shl eax,6
    lea rdi,[rel family_records]
    mov rax,[rdi+rax+8]
    mov [r8+112],rax
    jmp .publish
.data:
    lea rdi,[r8+80]
    mov rsi,r13
    mov ecx,8
    rep movsq
    mov rsi,[r13+40]
    mov rcx,rbp
    rep movsw
    mov [r8+176],rbp
.publish:
    inc r9
    mov [r8+8],r9
    mov [rel native_pio_trace],r9 ; final store; never wraps or repairs metadata
    jmp .done
.error:
    mov qword [rel native_pio_trace+8],1
.done:
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbx
    pop rax
    popfq
    ret
%unmacro pio_trace_save 0

; Invoked only after normal fence/retirement. Fatal instances retain evidence.
native_pio_trace_clear64:
    pushfq
    push rax
    push rcx
    push rdi
    cld
    lea rdi,[rel native_pio_trace]
    xor eax,eax
    mov ecx,1538
    rep stosq
    pop rdi
    pop rcx
    pop rax
    popfq
    ret
; END_PIO_TRACE
%endif

section .data
native_pio_fatal_message: db "REIST_X86_64_EXCEPTION_FATAL pio=1",13,10,0
align 8
native_pio_state: dq 0,-1,1,0,0,0,0,0
section .bss
alignb 8
native_pio_request: resb 64
%ifdef REIST_NATIVE_PIO_TRACE
native_pio_trace: resb 12304
%endif
section .text
