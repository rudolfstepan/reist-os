; Pure SysV admission over a pinned64-byte snapshot. No output or authority.
global family_request_admit64
family_request_admit64:
    cmp dword [rdi],1
    je .v1
    cmp dword [rdi],2
    jne .invalid
    cmp dword [rdi+8],1
    jne .invalid
    cmp qword [rdi+56],0
    je .invalid
    jmp .header
.v1:
    cmp qword [rdi+56],0
    jne .invalid
.header:
    cmp dword [rdi+4],64
    jne .invalid
    cmp dword [rdi+12],0
    jne .invalid
    mov eax,[rdi+8]
    cmp eax,1
    je .create
    cmp eax,2
    je .wait
    cmp eax,3
    jne .invalid
    cmp qword [rdi+32],0
    jne .invalid
    jmp .target
.wait:
    mov rax,[rdi+32]
    dec rax
    cmp rax,999
    ja .invalid
.target:
    mov rax,[rdi+16]
    test rax,rax
    jz .invalid
    cmp eax,4
    jae .invalid
    shr rax,32
    dec rax
    cmp rax,0x7ffffffe
    ja .invalid
    mov rax,[rdi+24]
    or rax,[rdi+40]
    or rax,[rdi+48]
    jnz .invalid
    jmp .ok
.create:
    mov rax,[rdi+16]
    or rax,[rdi+32]
    jnz .invalid
    mov rax,[rdi+24]
    sub rax,3
    cmp rax,3
    ja .invalid
    mov rax,[rdi+48]
    dec rax
    cmp rax,31
    ja .invalid
    mov rax,[rdi+40]
    test rax,1<<9
    jz .denied
    mov rdx,~((1<<4)|(1<<5)|(1<<6)|(1<<9)|(1<<22)|(1<<40)|(1<<41)|(1<<42)|(0x7f<<49)|(1<<58))
    test rax,rdx
    jnz .denied
.ok:
    mov eax,1
    ret
.denied:
    mov rax,-13
    ret
.invalid:
    mov rax,-22
    ret

; Fixed startup-v1 snapshot, read-only before argument/attempt publication.
global family_startup_admit64
family_startup_admit64:
    cmp dword [rdi],1
    jne .invalid
    cmp dword [rdi+4],1040
    jne .invalid
    cmp dword [rdi+12],0
    jne .invalid
    mov r8d,[rdi+8]
    cmp r8d,8
    ja .large
    xor ecx,ecx
    lea rsi,[rdi+16]
.cell:
    xor r9d,r9d
    cmp ecx,r8d
    setae r9b
    xor edx,edx
.byte:
    movzx eax,byte [rsi+rdx]
    test r9d,r9d
    jnz .padding
    test eax,eax
    setz r9b
    jmp .next
.padding:
    test eax,eax
    jnz .invalid
.next:
    inc edx
    cmp edx,128
    jb .byte
    test r9d,r9d
    jz .large
    add rsi,128
    inc ecx
    cmp ecx,8
    jb .cell
    mov eax,1
    ret
.large:
    mov rax,-7
    ret
.invalid:
    mov rax,-22
    ret

; SysV RDI pinned4096-byte scratch, RSI disjoint private stack page.
; Only the private vector tail is adapted; reuse the existing stack builder.
global family_startup_build64
family_startup_build64:
    push rbx
    push rbp
    sub rsp,72
    mov rbx,rdi
    mov rbp,rsi
    call family_startup_admit64
    cmp rax,1
    jne .return
    xor ecx,ecx
.vector:
    mov eax,ecx
    shl eax,7
    add eax,0x1010
    mov [rbx+1040+rcx*8],rax
    inc ecx
    cmp ecx,8
    jb .vector
    mov [rsp],rbx
    mov [rsp+8],rbp
    mov qword [rsp+16],0x1000
    mov qword [rsp+24],0x409000
    mov eax,[rbx+8]
    mov [rsp+40],rax
    test eax,eax
    jz .empty
    mov eax,0x1410
.empty:
    mov [rsp+32],rax
    mov qword [rsp+48],0
    mov rdi,rsp
    mov esi,1
    call reist_x64_startup_stack
.return:
    add rsp,72
    pop rbp
    pop rbx
    ret

; RUNTIME ADAPTER
%ifdef REIST_NATIVE_LIFECYCLE

; Records: handle,owner,wait-target,wait-deadline,result,phase,attempts,reserved.
; phase0 empty,1 root,2 child,3 retiring child,4 receipt,5 retiring root,6 dead root.
; No private record grants a right without the authoritative task generation.
family_record64:
    mov eax,edi
    shl eax,6
    lea r10,[rel family_records]
    add r10,rax
    ret

family_profile_apply64:
    cmp edi,4
    jae .bad
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
    sub rsp,48
    and rsp,-16
    mov r9d,eax
    mov eax,edi
    shl eax,8
    lea r10,[rel scheduler_tasks]
    add r10,rax
    mov [rsp],r10
    mov eax,edi
    shl eax,5
    lea r10,[rel family_profiles]
    add r10,rax
    mov [rsp+8],r10
    mov [rsp+16],rsi
    mov [rsp+24],rdx
    mov qword [rsp+32],0
    xor eax,eax
    cmp edi,2
    setb al
    shl eax,4
    mov [rsp+40],rax
    mov rdx,r8
    mov esi,r9d
    mov rdi,rsp
    call reist_x64_profile_apply_v2
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
.bad:
    xor eax,eax
    ret

family_initialize64:
    lea rdi,[rel family_begin]
    xor eax,eax
    mov ecx,(family_end-family_begin)/8
    rep stosq
    ret

family_root_built64:
    cmp dword [rel process_run_plan],3
    jne .done
    mov edi,[rel process_run_build_slot]
    call family_record64
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    or rax,rdi
    mov [r10],rax
    mov qword [r10+40],1
    inc dword [rel family_total]
.done:
    ret

; Additional read-only invariants; process_run_validate64 already checks
; task/queue/CPU/frame identity and the complete live syscall profile.
family_validate_runtime64:
    push rbx
    push r12
    push r13
    cmp dword [rel family_total],18
    ja .bad
    test dword [rel family_cancel_mask],~12
    jnz .bad
    xor ebx,ebx
.slot:
    mov edi,ebx
    call family_record64
    mov eax,ebx
    shl eax,8
    lea r12,[rel scheduler_tasks]
    add r12,rax
    mov eax,ebx
    shl eax,5
    lea r13,[rel family_profiles]
    add r13,rax
    cmp qword [r10+56],0
    jne .bad
    cmp qword [r10+48],8
    ja .bad
    mov rax,[r10+40]
    test rax,rax
    jz .empty
    cmp rax,6
    ja .bad
    mov rdx,[r10]
    cmp edx,ebx
    jne .bad
    shr rdx,32
    test edx,edx
    jz .bad
    cmp edx,0x7fffffff
    ja .bad
    lea rcx,[rel process_run_generations]
    cmp [rcx+rbx*4],edx
    jne .bad
    cmp ebx,2
    jae .child
    cmp qword [r10+8],0
    jne .bad
    cmp qword [r10+32],0
    jne .bad
    mov rcx,[r10+16]
    test rcx,rcx
    jz .not_waiting
    cmp rax,1
    jne .bad
    cmp qword [r12+TASK_STATE],TASK_BLOCKED
    jne .bad
    mov edi,ecx
    sub edi,2
    cmp edi,1
    ja .bad
    add edi,2
    shl edi,6
    lea rdx,[rel family_records]
    add rdx,rdi
    cmp [rdx],rcx
    jne .bad
    mov rcx,[r10]
    cmp [rdx+8],rcx
    jne .bad
    mov rcx,[r10+24]
    cmp rcx,[rel scheduler_last_tick]
    jbe .bad
    mov rsi,[r12+TASK_GENERATION]
    lea rdx,[rel scheduler_deadline_entries]
    mov edi,4
.wait_entry:
    cmp [rdx+8],esi
    je .wait_found
    add rdx,16
    dec edi
    jnz .wait_entry
    jmp .bad
.wait_found:
    cmp [rdx],rcx
    jne .bad
    jmp .root_state
.not_waiting:
    cmp qword [r10+24],0
    jne .bad
.root_state:
    cmp rax,1
    je .live
    cmp rax,5
    je .retiring
    cmp rax,6
    jne .bad
    jmp .free
.child:
    cmp qword [r10+48],0
    jne .bad
    cmp qword [r10+16],0
    jne .bad
    cmp qword [r10+24],0
    jne .bad
    mov rcx,[r10+32]
    shr rcx,32
    cmp rcx,3
    ja .bad
    mov rcx,[r10+8]
    cmp ecx,2
    jae .bad
    mov edi,ecx
    shl edi,6
    lea rdx,[rel family_records]
    cmp [rdx+rdi],rcx
    jne .bad
    cmp rax,2
    je .live
    cmp rax,3
    je .retiring
    cmp rax,4
    jne .bad
.free:
    cmp qword [r12+TASK_STATE],TASK_FREE
    jne .bad
    jmp .profile_zero
.empty:
    cmp qword [r12+TASK_STATE],TASK_FREE
    jne .bad
    mov rax,[r10]
    or rax,[r10+8]
    or rax,[r10+16]
    or rax,[r10+24]
    or rax,[r10+32]
    or rax,[r10+48]
    jnz .bad
    jmp .profile_zero
.retiring:
    bt dword [rel process_heap_retire_mask],ebx
    jnc .bad
.profile_zero:
    mov rax,[r13]
    or rax,[r13+8]
    or rax,[r13+16]
    or rax,[r13+24]
    jnz .bad
    jmp .next
.live:
    mov rax,[r12+TASK_STATE]
    cmp rax,TASK_READY
    je .next
    cmp rax,TASK_RUNNING
    je .next
    cmp rax,TASK_BLOCKED
    jne .bad
.next:
    inc ebx
    cmp ebx,4
    jb .slot
    mov eax,1
    jmp .return
.bad:
    xor eax,eax
.return:
    pop r13
    pop r12
    pop rbx
    ret

; Pointer/unused-register admission before copying the complete request once.
family_syscall64:
    mov rax,[rel syscall_rsi]
    or rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz process_run_syscall64.invalid
    mov rax,[rel syscall_rdi]
    mov edx,64
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    test eax,eax
    jz .pointer
    mov rsi,[rel syscall_rdi]
    lea rdi,[rel family_request]
    mov ecx,8
    rep movsq
    lea rdi,[rel family_request]
    call family_request_admit64
    cmp rax,1
    jne family_result64
    cmp dword [rel family_request],2
    jne .admitted
    mov rax,[rel family_request+56]
    mov edx,1040
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    test eax,eax
    jz .pointer
    mov rsi,[rel family_request+56]
    lea rdi,[rel family_startup]
    mov ecx,130
    rep movsq
    lea rdi,[rel family_startup]
    call family_startup_admit64
    cmp rax,1
    jne family_result64
.admitted:
    mov edi,[rel scheduler_current_slot]
    cmp edi,2
    jae process_run_syscall64.denied
    call family_record64
    cmp qword [r10+40],1
    jne scheduler_fail
    cmp dword [rel family_request+8],1
    je family_create64
    mov rax,[rel family_request+16]
    mov edi,eax
    cmp edi,2
    jb .child
    call family_record64
    mov rax,[rel family_request+16]
    cmp [r10],rax
    jne .child
    mov ecx,[rel scheduler_current_slot]
    shl ecx,6
    lea rdx,[rel family_records]
    mov rdx,[rdx+rcx]
    cmp [r10+8],rdx
    jne .child
    cmp dword [rel family_request+8],2
    je family_wait64
    cmp qword [r10+40],2
    jne .cancel_done
    bts dword [rel family_cancel_mask],edi
    lea rax,[rel family_reasons]
    mov dword [rax+rdi*4],2
.cancel_done:
    xor eax,eax
    jmp family_result64
.child:
    mov rax,-10
    jmp family_result64
.pointer:
    mov rax,-14
    jmp family_result64

family_result64:
    push rax
    lea rdi,[rel family_request]
    xor eax,eax
    mov ecx,8
    rep stosq
    lea rdi,[rel family_startup]
    mov ecx,512
    rep stosq
    pop rax
    jmp process_run_resume64

family_create64:
    cmp qword [r10+48],8
    jae .capacity
    ; Capacity admission precedes attempt charging; retained receipts own slots.
    mov edi,2
.slot:
    mov ecx,edi
    shl ecx,6
    lea rax,[rel family_records]
    cmp qword [rax+rcx+40],0
    je .found
    inc edi
    cmp edi,4
    jb .slot
.capacity:
    mov rax,-11
    jmp family_result64
.found:
    mov [rel family_build_slot],edi
    mov rax,[rel family_request+40]
    mov ecx,[rel scheduler_current_slot]
    shl ecx,5
    lea rdx,[rel process_run_plan+16]
    mov rdx,[rdx+rcx+8]
    not rdx
    test rax,rdx
    jz .attenuated
    mov rax,-13
    jmp family_result64
.attenuated:
    cmp dword [rel process_run_generation],0x7fffffff
    jae .capacity
    inc qword [r10+48]
    call scheduler_save_syscall_context64
    call physical_free_frame_count64
    mov [rel family_initial_free],eax
    mov byte [rel family_loaded_image],0
    mov edi,[rel family_request+24]
    call x86_64_elf64_select_image64
    cmp eax,1
    jne scheduler_fail
    call x86_64_elf64_entry64
    test rax,rax
    jnz .loaded
    call x86_64_elf64_load64
    test eax,eax
    jz .load_failed
    mov byte [rel family_loaded_image],1
    call x86_64_elf64_entry64
.loaded:
    mov [rel scheduler_entry],rax
    call scheduler_claim_child_frames64
    cmp rax,-12
    je .oom
    cmp rax,1
    jne scheduler_fail
    mov byte [rel scheduler_frame_claim_active],1
    mov edi,[rel family_build_slot]
    call scheduler_build_task64
    cmp eax,1
    jne scheduler_fail
    call scheduler_abort_frame_claim64
    cmp eax,1
    jne scheduler_fail
    mov rdi,DIRECT_MAP_BASE
    add rdi,[r12+TASK_STACK_FRAME]
    cmp dword [rel family_request],2
    jne .catalog_stack
    mov rsi,rdi
    lea rdi,[rel family_startup]
    call family_startup_build64
    jmp .stack_ready
.catalog_stack:
    call x86_64_boot_program_stack64
.stack_ready:
    test rax,rax
    jle scheduler_fail
    mov [r12+TASK_RSP],rax
    mov edi,[rel family_build_slot]
    mov rsi,[r12+TASK_GENERATION]
    mov [rel process_run_generation],esi
    lea rdx,[rel process_run_generations]
    mov [rdx+rdi*4],esi
    mov eax,edi
    shl eax,5
    lea r13,[rel process_run_plan+16]
    add r13,rax
    mov rdx,[rel family_request+40]
    mov [r13+8],rdx
    mov rax,[rel family_request+48]
    mov [r13+16],rax
    mov rax,[rel family_request+24]
    mov [r13+24],rax
    mov eax,1
    call scheduler_profile_apply64
    cmp eax,1
    jne scheduler_fail
    mov rdx,[r13+16]
    mov eax,1
    call scheduler_budget_apply64
    cmp eax,1
    jne scheduler_fail
    mov esi,edi
    mov edi,0
    mov rdx,[r12+TASK_GENERATION]
    call process_ipc_service64
    mov edi,1
    mov esi,[rel family_build_slot]
    xor r8d,r8d
    xor r9d,r9d
    call process_heap_service64
    test rax,rax
    jnz scheduler_fail
    mov edi,[rel family_build_slot]
    mov rsi,[r12+TASK_GENERATION]
    mov eax,2
    call scheduler_identity_apply64
    cmp eax,1
    jne scheduler_fail
    call scheduler_runqueue_enqueue64
    cmp eax,1
    jne scheduler_fail
    call family_record64
    mov rax,rsi
    shl rax,32
    or rax,rdi
    mov [r10],rax
    mov qword [r10+40],2
    mov ecx,[rel scheduler_current_slot]
    shl ecx,6
    lea rdx,[rel family_records]
    mov rdx,[rdx+rcx]
    mov [r10+8],rdx
    inc dword [rel process_run_live]
    inc dword [rel family_total]
    jmp .parent_result
.load_failed:
    call x86_64_elf64_load_error64
    cmp rax,-12
    jne scheduler_fail
.oom:
    call scheduler_abort_frame_claim64
    cmp eax,1
    jne scheduler_fail
    cmp byte [rel family_loaded_image],0
    je .balance
    call x86_64_elf64_release64
    cmp eax,1
    jne scheduler_fail
.balance:
    call physical_free_frame_count64
    cmp eax,[rel family_initial_free]
    jne scheduler_fail
    mov rax,-12
.parent_result:
    mov ecx,[rel scheduler_current_slot]
    shl ecx,8
    lea r12,[rel scheduler_tasks]
    add r12,rcx
    jmp family_result64

family_wait64:
    cmp qword [r10+40],4
    je .receipt
    mov rax,[rel scheduler_last_tick]
    mov rcx,[rel family_request+32]
    add rcx,9
    push rax
    mov rax,rcx
    xor edx,edx
    mov ecx,10
    div rcx
    pop rcx
    add rax,rcx
    jc process_run_syscall64.invalid
    mov rcx,1<<60
    cmp rax,rcx
    jae process_run_syscall64.invalid
    mov r15,rax
    call scheduler_save_syscall_context64
    mov edi,[rel scheduler_current_slot]
    call family_record64
    mov rax,[rel family_request+16]
    mov [r10+16],rax
    mov [r10+24],r15
    lea rdi,[rel family_request]
    xor eax,eax
    mov ecx,8
    rep stosq
    mov qword [r12+TASK_STATE],TASK_BLOCKED
    mov edi,[rel scheduler_current_slot]
    mov rsi,[r12+TASK_GENERATION]
    mov rdx,r15
    mov r9d,1
    mov eax,1
    call scheduler_queue_apply64
    cmp eax,1
    jne scheduler_fail
    jmp process_run_dispatch64
.receipt:
    mov r15,[r10+32]
    mov rdi,r10
    xor eax,eax
    mov ecx,8
    rep stosq
    mov rax,r15
    jmp family_result64

family_wait_expired64:
    cmp dword [rel process_run_plan],3
    jne .done
    push rax
    push r10
    call family_record64
    cmp qword [r10+16],0
    je .restore
    cmp [r10+24],rbp
    ja scheduler_fail
    mov qword [r10+16],0
    mov qword [r10+24],0
    mov qword [r12+TASK_RAX],-110
.restore:
    pop r10
    pop rax
.done:
    ret

family_terminal64:
    cmp dword [rel process_run_plan],3
    jne .done
    push rax
    push rdi
    push r10
    mov edi,[rel scheduler_current_slot]
    call family_record64
    cmp edi,2
    jb .root
    cmp qword [r10+40],2
    jne scheduler_fail
    mov qword [r10+40],3
    xor eax,eax
    cmp dword [rel process_run_receipt+12],TASK_FAULTED
    sete al
    lea rcx,[rel family_reasons]
    cmp dword [rcx+rdi*4],0
    je .reason
    mov eax,[rcx+rdi*4]
    mov dword [rcx+rdi*4],0
.reason:
    shl rax,32
    mov ecx,[rel process_run_receipt+8]
    or rax,rcx
    mov [r10+32],rax
    jmp .restore
.root:
    cmp qword [r10+40],1
    jne scheduler_fail
    mov qword [r10+40],5
    mov qword [r10+16],0
    mov qword [r10+24],0
    mov rax,[r10]
    lea r10,[rel family_records+128]
    mov ecx,2
.children:
    cmp [r10+8],rax
    jne .next
    cmp qword [r10+40],2
    jne .next
    bts dword [rel family_cancel_mask],ecx
    lea rdi,[rel family_reasons]
    mov dword [rdi+rcx*4],3
.next:
    add r10,64
    inc ecx
    cmp ecx,4
    jb .children
.restore:
    pop r10
    pop rdi
    pop rax
.done:
    ret

family_reaped64:
    cmp dword [rel process_run_plan],3
    jne .done
    mov edi,[rel scheduler_current_slot]
    call family_record64
    cmp edi,2
    jb .root
    cmp qword [r10+40],3
    jne scheduler_fail
    mov qword [r10+40],4
    ret
.root:
    cmp qword [r10+40],5
    jne scheduler_fail
    mov qword [r10+40],6
.done:
    ret

family_dispatch64:
    cmp dword [rel process_run_plan],3
    jne .done
    call process_run_validate64
    cmp eax,1
    jne scheduler_fail
    push rbx
    xor ebx,ebx
.cancel:
    bt dword [rel family_cancel_mask],ebx
    jnc .cancel_next
    mov edi,ebx
    call family_cancel_one64
    btr dword [rel family_cancel_mask],ebx
.cancel_next:
    inc ebx
    cmp ebx,4
    jb .cancel
    mov ebx,2
.receipt:
    mov edi,ebx
    call family_record64
    cmp qword [r10+40],4
    jne .receipt_next
    mov r15,r10
    mov rax,[r10+8]
    mov edi,eax
    call family_record64
    cmp qword [r10+40],1
    jne .discard
    mov rax,[r15]
    cmp [r10+16],rax
    jne .receipt_next
    mov rdx,[r10+24]
    mov qword [r10+16],0
    mov qword [r10+24],0
    mov rsi,[r10]
    shr rsi,32
    mov r9d,1
    mov eax,3
    call scheduler_queue_apply64
    cmp eax,1
    jne scheduler_fail
    mov eax,edi
    shl eax,8
    lea r12,[rel scheduler_tasks]
    add r12,rax
    mov rax,[r15+32]
    mov [r12+TASK_RAX],rax
    mov qword [r12+TASK_STATE],TASK_READY
    call scheduler_runqueue_enqueue64
    cmp eax,1
    jne scheduler_fail
.discard:
    mov rdi,r15
    xor eax,eax
    mov ecx,8
    rep stosq
.receipt_next:
    inc ebx
    cmp ebx,4
    jb .receipt
    pop rbx
.done:
    ret

; All targets are quiescent on this CPU. Preserve kernel stack, and remove
; the sole queue membership before profile/IPC/heap fencing. No user copyout.
family_cancel_one64:
    push rbx
    push r12
    push r13
    mov ebx,edi
    mov eax,edi
    shl eax,8
    lea r12,[rel scheduler_tasks]
    add r12,rax
    mov rsi,[r12+TASK_GENERATION]
    mov rax,[rel scheduler_original_cr3]
    mov cr3,rax
    cmp qword [r12+TASK_STATE],TASK_READY
    jne .blocked
    xor r9d,r9d
    xor edx,edx
    mov eax,3
    call scheduler_queue_apply64
    cmp eax,1
    jne scheduler_fail
    jmp .removed
.blocked:
    cmp qword [r12+TASK_STATE],TASK_BLOCKED
    jne scheduler_fail
    lea r13,[rel scheduler_deadline_entries]
    mov ecx,4
.deadline:
    cmp [r13+8],esi
    je .found
    add r13,16
    loop .deadline
    jmp scheduler_fail
.found:
    cmp [r13+12],bl
    jne scheduler_fail
    mov rdx,[r13]
    mov r9d,1
    mov eax,3
    call scheduler_queue_apply64
    cmp eax,1
    jne scheduler_fail
.removed:
    btr dword [rel process_heap_pending_mask],ebx
    mov [rel scheduler_current_slot],ebx
    mov [rel process_run_receipt],ebx
    mov eax,[r12+TASK_GENERATION]
    mov [rel process_run_receipt+4],eax
    mov dword [rel process_run_receipt+8],0
    mov dword [rel process_run_receipt+12],TASK_FAULTED
    mov rax,[r12+TASK_RIP]
    mov [rel process_run_receipt+24],rax
    mov eax,ebx
    shl eax,5
    lea rcx,[rel scheduler_cpu_budgets]
    mov rdx,[rcx+rax+16]
    mov [rel process_run_receipt+16],rdx
    mov qword [r12+TASK_STATE],TASK_FAULTED
    call family_terminal64
    mov edi,ebx
    mov rsi,[r12+TASK_GENERATION]
    lea rdx,[rel process_run_plan+16]
    mov eax,ebx
    shl eax,5
    mov rdx,[rdx+rax+8]
    mov eax,3
    call scheduler_profile_apply64
    cmp eax,1
    jne scheduler_fail
    mov edi,4
    mov esi,ebx
    mov rdx,[r12+TASK_GENERATION]
    call process_ipc_service64
    call process_heap_begin_retire64
    pop r13
    pop r12
    pop rbx
    ret

family_finish64:
    cmp dword [rel process_run_plan],3
    jne .done
    cmp dword [rel family_cancel_mask],0
    jne scheduler_fail
    cmp qword [rel family_records+128+40],0
    jne scheduler_fail
    cmp qword [rel family_records+192+40],0
    jne scheduler_fail
    call family_initialize64
.done:
    ret

section .bss
alignb 8
family_begin:
family_records: resb 4*64
family_profiles: resb 4*32
family_request: resb 64
family_reasons: resd 4
family_total: resd 1
family_cancel_mask: resd 1
family_build_slot: resd 1
family_initial_free: resd 1
family_loaded_image: resb 1
alignb 8
family_startup: resb 4096
family_end:
section .text
%endif
