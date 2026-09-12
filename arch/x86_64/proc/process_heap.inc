; Native private64-byte C request. No user pointer or C stack survives a step.
; EDI operation, ESI slot, R8/R9 copied arguments. Preserve input registers.
process_heap_service64:
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
    sub rsp,80
    and rsp,-16
    cmp esi,TASK_SLOT_CAPACITY
    jae scheduler_fail
    mov eax,edi
    mov [rsp],rax
    mov eax,esi
    mov [rsp+8],rax
    shl eax,8
    lea r10,[rel scheduler_tasks]
    add r10,rax
    mov rax,[r10+TASK_GENERATION]
    mov [rsp+16],rax
    mov rax,[r10+TASK_CR3]
    mov [rsp+24],rax
    mov eax,esi
    shl eax,5
    lea r11,[rel scheduler_table_frames]
    mov rax,[r11+rax+TASK_TABLE_PDPT]
    mov [rsp+32],rax
    mov [rsp+40],r8
    mov [rsp+48],r9
    mov qword [rsp+56],0
    mov rdi,rsp
    mov rax,C_NATIVE_HEAP_ENTRY
    call rax
    cmp eax,1
    jne scheduler_fail
    mov r10,[rsp+56]
    mov rdi,rsp
    xor eax,eax
    mov ecx,8
    rep stosq
    mov rax,r10
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

process_heap_syscall64:
    mov rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz process_run_syscall64.invalid
    mov edi,[rel syscall_rax]
    sub edi,2
    cmp edi,4
    je .arguments
    cmp qword [rel syscall_rsi],0
    jne process_run_syscall64.invalid
.arguments:
    mov esi,[rel scheduler_current_slot]
    mov r8,[rel syscall_rdi]
    mov r9,[rel syscall_rsi]
    call process_heap_service64
    cmp rax,-4095
    jne process_run_resume64
    bts dword [rel process_heap_pending_mask],esi
    jc scheduler_fail
    jmp process_run_resume64

process_heap_enter64:
    mov esi,edi
    mov edi,5
    xor r8d,r8d
    xor r9d,r9d
    call process_heap_service64
.step_complete:
    cmp rax,-4095
    je .pending
    btr dword [rel process_heap_pending_mask],esi
    jnc scheduler_fail
    mov [r11+TASK_RAX],rax
    mov qword [r11+TASK_STATE],TASK_RUNNING
    jmp scheduler_enter_task64.state_published
.pending:
    mov edi,esi
    mov rsi,[r11+TASK_GENERATION]
    call scheduler_runqueue_enqueue64
    test eax,eax
    jz scheduler_fail
    jmp process_run_dispatch64.kernel_work

process_heap_retire64:
    call process_heap_begin_retire64
    jmp process_run_dispatch64

; Same receipt/heap transition for current exit and an already fenced peer.
; Caller has removed queue membership and revoked profile/IPC authority.
process_heap_begin_retire64:
    mov esi,[rel scheduler_current_slot]
    bt dword [rel process_heap_pending_mask],esi
    jc scheduler_fail
    mov eax,esi
    shl eax,5
    lea rdi,[rel process_heap_receipts]
    add rdi,rax
    push rsi
    lea rsi,[rel process_run_receipt]
    mov ecx,4
    rep movsq
    pop rsi
    mov edi,6
    xor r8d,r8d
    xor r9d,r9d
    call process_heap_service64
    cmp rax,-4095
    jne scheduler_fail
    bts dword [rel process_heap_retire_mask],esi
    jc scheduler_fail
    ret

; At most one64-item retirement step per dispatch, round-robin across slots.
process_heap_reapers64:
    cmp dword [rel process_heap_retire_mask],0
    je .done
    push rbx
    push r12
    mov ebx,[rel process_heap_reaper_cursor]
    mov ecx,4
.find:
    inc ebx
    and ebx,3
    bt dword [rel process_heap_retire_mask],ebx
    jc .found
    loop .find
    jmp scheduler_fail
.found:
    mov [rel process_heap_reaper_cursor],ebx
    mov edi,5
    mov esi,ebx
    xor r8d,r8d
    xor r9d,r9d
    call process_heap_service64
.step_complete:
    cmp rax,-4095
    je .return
    test rax,rax
    jnz scheduler_fail
    btr dword [rel process_heap_retire_mask],ebx
    mov [rel scheduler_current_slot],ebx
    mov eax,ebx
    shl eax,8
    lea r12,[rel scheduler_tasks]
    add r12,rax
    mov eax,ebx
    shl eax,5
    lea rsi,[rel process_heap_receipts]
    add rsi,rax
    lea rdi,[rel process_run_receipt]
    mov ecx,4
    rep movsq
    lea rdi,[rel process_heap_receipts]
    add rdi,rax
    xor eax,eax
    mov ecx,4
    rep stosq
    call process_run_complete_retire64
.return:
    pop r12
    pop rbx
.done:
    ret

section .bss
alignb 8
process_heap_pending_mask: resd 1
process_heap_retire_mask: resd 1
process_heap_reaper_cursor: resd 1
alignb 8
process_heap_receipts: resb 4*32
section .text
