; Role-independent private adapter. Included in the existing scheduler object;
; all allocation, queue, context, generation, profile and FP cores are shared.
; The caller admits a finite independent set; no task is another task's owner.

; Pure read-only SysV descriptor admission. Arguments remain opaque64 bits.
process_run_admit64:
    test rdi, rdi
    jz .bad
    test rdi, 7
    jnz .bad
    cmp dword [rdi], 1
    jne .bad
    cmp dword [rdi+4], 144
    jne .bad
    mov edx, [rdi+8]
    dec edx
    cmp edx, 3
    ja .bad
    inc edx
    cmp dword [rdi+12], 0
    jne .bad
    mov r8, (1<<9)|(1<<22)|(1<<40)|(1<<41)|(1<<42)
%ifdef REIST_NATIVE_IPC_BINDING
    mov rax, (0x7f<<49)|(1<<58)
    or r8, rax
%endif
    not r8
    xor ecx, ecx
.entry:
    mov eax, ecx
    shl eax, 5
    lea r9, [rdi+rax+16]
    cmp ecx, edx
    jae .unused
    mov rax, [r9+8]
    test rax, r8
    jnz .bad
    test rax, 1<<9 ; an orderly exit must always be available
    jz .bad
    mov rax, [r9+16]
    dec rax
    cmp rax, 31
    ja .bad
    cmp qword [r9+24], 0
    jne .bad
    jmp .next
.unused:
    mov rax, [r9]
    or rax, [r9+8]
    or rax, [r9+16]
    or rax, [r9+24]
    jnz .bad
.next:
    inc ecx
    cmp ecx, 4
    jb .entry
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret

; Read-only whole-run ownership gate; all registers except RAX preserved.
process_run_validate64:
    push rbx
    push rbp
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    push r14
    push r15
    cmp byte [rel scheduler_mode], SCHEDULER_MODE_PROCESS
    jne .bad
    cmp byte [rel scheduler_active], 1
    jne .bad
    lea rdi, [rel process_run_plan]
    call process_run_admit64
    test eax, eax
    jz .bad
    lea rax, [rel scheduler_tasks]
    cmp [rel scheduler_identity_pool], rax
    jne .bad
    lea rax, [rel scheduler_identity_retired]
    cmp [rel scheduler_identity_pool+8], rax
    jne .bad
    cmp dword [rel scheduler_identity_pool+16], TASK_SLOT_CAPACITY
    jne .bad
    mov eax, [rel process_run_generation]
    cmp [rel scheduler_identity_pool+20], eax
    jne .bad
    xor eax, eax
    xor edi, edi
    xor esi, esi
    call scheduler_identity_apply64
    cmp eax, 1
    jne .bad
    xor eax, eax
    xor r9d, r9d
    call scheduler_queue_apply64
    cmp eax, 1
    jne .bad
    xor eax, eax
    mov r9d, 1
    call scheduler_queue_apply64
    cmp eax, 1
    jne .bad
    cmp dword [rel scheduler_last_tick], SHELL_CLOCK_LIMIT
    jae .bad
    xor ebx, ebx
    xor ebp, ebp ; live task count
    xor r14d, r14d ; running task count
.task:
    mov eax, ebx
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    mov eax, ebx
    shl eax, 5
    lea r13, [rel process_run_plan+16]
    add r13, rax
    lea r15, [rel scheduler_cpu_budgets]
    add r15, rax
    lea rdx, [rel process_run_generations]
    mov esi, [rdx+rbx*4]
    cmp ebx, [rel process_run_plan+8]
    jae .outside
    test esi, esi
    jz .bad
    cmp esi, [rel process_run_generation]
    ja .bad
    mov eax, [rel process_run_generation]
    sub eax, [rel process_run_plan+8]
    inc eax
    add eax, ebx
    cmp esi, eax
    jne .bad
    cmp qword [r12+TASK_STATE], TASK_FREE
    je .retired
    cmp [r12+TASK_GENERATION], rsi
    jne .bad
    inc ebp
    cmp qword [r12+TASK_STATE], TASK_READY
    je .ready
    cmp qword [r12+TASK_STATE], TASK_BLOCKED
    je .blocked
    cmp qword [r12+TASK_STATE], TASK_RUNNING
    jne .bad
    inc r14d
    cmp ebx, [rel scheduler_current_slot]
    jne .bad
    xor r10d, r10d
    xor r11d, r11d
    jmp .members
.ready:
    mov r10d, 1
    xor r11d, r11d
    jmp .members
.blocked:
    xor r10d, r10d
    mov r11d, 1
.members:
    lea rdx, [rel scheduler_runqueue_membership]
    cmp [rdx+rbx], r10b
    jne .bad
    lea rdx, [rel scheduler_deadline_membership]
    cmp [rdx+rbx], r11b
    jne .bad
    ; Both queues' entries must refer to this exact task generation.
    mov rax, rsi
    shl rax, 32
    or rax, rbx
    lea rdx, [rel scheduler_runqueue_entries]
    xor ecx, ecx
    xor r8d, r8d
.fifo:
    cmp [rdx+rcx*8], rax
    jne .fifo_next
    inc r8d
.fifo_next:
    inc ecx
    cmp ecx, TASK_SLOT_CAPACITY
    jb .fifo
    cmp r8d, r10d
    jne .bad
    lea rdx, [rel scheduler_deadline_entries]
    xor ecx, ecx
    xor r8d, r8d
.deadline:
    cmp [rdx+8], esi
    jne .deadline_next
    cmp [rdx+12], bl
    jne .bad
    mov eax, [rel scheduler_last_tick]
    cmp [rdx], rax
    jbe .bad
    cmp qword [rdx], SHELL_CLOCK_LIMIT
    jae .bad
    inc r8d
.deadline_next:
    add rdx, 16
    inc ecx
    cmp ecx, TASK_SLOT_CAPACITY
    jb .deadline
    cmp r8d, r11d
    jne .bad
    mov edi, ebx
    mov rdx, [r13+8]
    xor eax, eax
    call scheduler_profile_apply64
    cmp eax, 1
    jne .bad
    xor edx, edx
    xor eax, eax
    call scheduler_budget_apply64
    cmp eax, 1
    jne .bad
    mov rax, [r13+16]
    cmp [r15+8], rax
    jne .bad
    mov eax, [rel scheduler_last_tick]
    cmp [r15+24], rax
    ja .bad
    jmp .next
.outside:
    test esi, esi
    jnz .bad
    cmp qword [r12+TASK_STATE], TASK_FREE
    jne .bad
    jmp .empty
.retired:
    lea rdx, [rel scheduler_identity_retired]
    cmp [rdx+rbx*4], esi
    jne .bad
.empty:
    lea rdx, [rel scheduler_runqueue_membership]
    cmp byte [rdx+rbx], 0
    jne .bad
    lea rdx, [rel scheduler_deadline_membership]
    cmp byte [rdx+rbx], 0
    jne .bad
    mov eax, ebx
    shl eax, 4
    lea rdx, [rel scheduler_syscall_profiles]
    add rdx, rax
    mov rax, [rdx]
    or rax, [rdx+8]
    or rax, [r15]
    or rax, [r15+8]
    or rax, [r15+16]
    or rax, [r15+24]
    jnz .bad
.next:
    inc ebx
    cmp ebx, TASK_SLOT_CAPACITY
    jb .task
    cmp r14d, 1
    ja .bad
    cmp ebp, [rel process_run_live]
    jne .bad
    add ebp, [rel scheduler_reap_count]
    cmp ebp, [rel process_run_plan+8]
    jne .bad
    call process_run_frames64
    jmp .return
.bad:
    xor eax, eax
.return:
    pop r15
    pop r14
    pop r13
    pop r12
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbp
    pop rbx
    ret

; Read-only uniqueness across ALL private resources, including retired slots.
process_run_frames64:
    sub rsp, 52*8
    xor r8d, r8d
    xor ebx, ebx
.slot:
    mov eax, ebx
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    shr eax, 3
    lea r13, [rel scheduler_table_frames]
    add r13, rax
    xor ecx, ecx
.frame:
    cmp ecx, 8
    jb .private
    je .stack
    mov edx, ecx
    sub edx, 9
    mov rax, [r13+rdx*8]
    jmp .check
.stack:
    mov rax, [r12+TASK_STACK_FRAME]
    jmp .check
.private:
    mov rax, [r12+TASK_PRIVATE_FRAMES+rcx*8]
.check:
    cmp qword [r12+TASK_STATE], TASK_FREE
    jne .live
    test rax, rax
    jnz .bad
    jmp .next
.live:
    test rax, rax
    jnz .present
    cmp ecx, 8
    jae .bad
    jmp .next
.present:
    test rax, PAGE_SIZE-1
    jnz .bad
    cmp rax, MANAGED_LIMIT
    jae .bad
    cmp rax, [rel scheduler_original_cr3]
    je .bad
    cmp ecx, 9
    jne .distinct
    cmp [r12+TASK_CR3], rax
    jne .bad
.distinct:
    xor edx, edx
.compare:
    cmp edx, r8d
    jae .record
    cmp [rsp+rdx*8], rax
    je .bad
    inc edx
    jmp .compare
.record:
    mov [rsp+r8*8], rax
    inc r8d
.next:
    inc ecx
    cmp ecx, 13
    jb .frame
    inc ebx
    cmp ebx, TASK_SLOT_CAPACITY
    jb .slot
    mov eax, 1
    jmp .return
.bad:
    xor eax, eax
.return:
    add rsp, 52*8
    ret

; Trusted caller pointer is pinned to C rodata by the bridge. No user pointer.
global x86_64_process_run64
x86_64_process_run64:
    cli
    cld
    call process_run_admit64
    test eax, eax
    jz .reject
    cmp byte [rel scheduler_active], 0
    jne .reject
    mov eax, [rel process_run_generation]
    add eax, [rdi+8]
    jc .reject
%ifdef REIST_NATIVE_IPC_BINDING
    test eax, eax ; existing common IPC PID is positive int32
    js .reject
%endif
    mov rax, cr3
    mov edx, pml4_table
    cmp rax, rdx
    jne .reject
    mov rsi, rdi
    lea rdi, [rel process_run_plan]
    mov ecx, 144/8
    rep movsq
    lea rdi, [rel scheduler_state_begin]
    xor eax, eax
    mov ecx, (scheduler_state_end-scheduler_state_begin)/8
    rep stosq
    lea rdi, [rel process_run_generations]
    mov ecx, 16/8
    rep stosq
    mov [rel process_run_live], eax
    mov [rel scheduler_caller_rsp], rsp
    mov rax, cr3
    mov [rel scheduler_original_cr3], rax
    mov byte [rel scheduler_mode], SCHEDULER_MODE_PROCESS
    mov byte [rel scheduler_failure_stage], 0xE0
    lea rax, [rel scheduler_tasks]
    mov [rel scheduler_identity_pool], rax
    lea rax, [rel scheduler_identity_retired]
    mov [rel scheduler_identity_pool+8], rax
    mov dword [rel scheduler_identity_pool+16], TASK_SLOT_CAPACITY
    mov eax, [rel process_run_generation]
    mov [rel scheduler_identity_pool+20], eax
    call physical_free_frame_count64
    mov [rel scheduler_initial_free], eax
    mov edi, ELF_IMAGE_PROBE
    call x86_64_elf64_select_image64
    test eax, eax
    jz scheduler_fail
    call x86_64_elf64_load64
    test eax, eax
    jz scheduler_fail
    call x86_64_elf64_entry64
    mov [rel scheduler_entry], rax
    mov dword [rel process_run_build_slot], 0
.build:
    mov edi, [rel process_run_build_slot]
    call scheduler_build_task64
    test eax, eax
    jz scheduler_fail
    mov edi, [rel process_run_build_slot]
    mov rsi, [r12+TASK_GENERATION]
    lea rdx, [rel process_run_generations]
    mov [rdx+rdi*4], esi
    mov [rel process_run_generation], esi
    mov eax, edi
    shl eax, 5
    lea r13, [rel process_run_plan+16]
    add r13, rax
    mov rax, [r13]
    mov [r12+TASK_RDI], rax
    mov [r12+TASK_ID], rsi
    mov rdx, [r13+8]
    mov eax, 1
    call scheduler_profile_apply64
    test eax, eax
    jz scheduler_fail
    mov rdx, [r13+16]
    mov eax, 1
    call scheduler_budget_apply64
    test eax, eax
    jz scheduler_fail
    mov eax, 2
    call scheduler_identity_apply64
    test eax, eax
    jz scheduler_fail
    call scheduler_runqueue_enqueue64
    test eax, eax
    jz scheduler_fail
    inc dword [rel process_run_live]
    inc dword [rel process_run_build_slot]
    mov eax, [rel process_run_build_slot]
    cmp eax, [rel process_run_plan+8]
    jb .build
%ifdef REIST_NATIVE_IPC_BINDING
    xor ebx, ebx
.ipc_bind:
    mov edi, 0
    mov esi, ebx
    lea rax, [rel process_run_generations]
    mov edx, [rax+rbx*4]
    call process_ipc_service64
    inc ebx
    cmp ebx, [rel process_run_plan+8]
    jb .ipc_bind
%endif
    mov byte [rel scheduler_failure_stage], 0xE1
    call scheduler_setup_syscalls64
    test eax, eax
    jz scheduler_fail
    lea rax, [rel scheduler_kernel_stack_top]
    mov [rel scheduler_syscall_context], rax
    mov rdi, rax
    call x86_64_exception_set_rsp0
    test eax, eax
    jz scheduler_fail
    call scheduler_enable_user_breakpoint64
    test eax, eax
    jz scheduler_fail
    mov byte [rel scheduler_active], 1
    call x86_64_timer_shell_arm64
    test eax, eax
    jz scheduler_fail
    jmp process_run_dispatch64
.reject:
    xor eax, eax
    ret

process_run_dispatch64:
    call process_run_validate64
    test eax, eax
    jz scheduler_fail
    lea rdx, [rel scheduler_tasks]
    mov ecx, TASK_SLOT_CAPACITY
.quiescent:
    cmp qword [rdx+TASK_STATE], TASK_RUNNING
    je scheduler_fail
    add rdx, TASK_RECORD_SIZE
    loop .quiescent
    cmp dword [rel process_run_live], 0
    je process_run_finish64
    cmp byte [rel scheduler_runqueue_count], 0
    jne scheduler_runqueue_dispatch64
    cmp byte [rel scheduler_deadline_count], 0
    je scheduler_fail
    mov rax, [rel scheduler_original_cr3]
    mov cr3, rax
    lea rsp, [rel scheduler_kernel_stack_top]
    call scheduler_restore_kernel_segments64
    call x86_64_fp_reset64
.idle_wait:
    sti
    hlt
    cli
.idle_resume:
    jmp process_run_dispatch64

process_run_enter64:
    ; EDI slot, R11 task, queue already popped by the shared dispatcher.
    mov rax, [r11+TASK_GENERATION]
    lea rdx, [rel process_run_generations]
    cmp [rdx+rdi*4], eax
    jne scheduler_fail
    mov qword [r11+TASK_STATE], TASK_RUNNING
    jmp scheduler_enter_task64.state_published

process_run_syscall64:
    call process_run_validate64
    test eax, eax
    jz scheduler_fail
    mov rax, [rel syscall_r11]
    mov rdx, ~0x244fd7
    test rax, rdx
    jnz scheduler_fail
    and eax, 0x202
    cmp eax, 0x202
    jne scheduler_fail
    mov r8d, SHELL_STACK_STATUS
    mov rax, [rel scheduler_syscall_context+8]
    cmp rax, USER_STACK_BASE
    jb .context
    cmp rax, USER_STACK_TOP
    ja .context
    mov r8d, SHELL_CONTEXT_STATUS
    test qword [rel syscall_r11], 0x4000
    jnz .context
    mov rax, [rel syscall_rcx]
    call scheduler_validate_task_instruction64
    test eax, eax
    jz .context
    mov edi, [rel scheduler_current_slot]
    mov rsi, [r12+TASK_GENERATION]
    mov eax, edi
    shl eax, 5
    lea rdx, [rel process_run_plan+16]
    mov rdx, [rdx+rax+8]
    mov r8, [rel syscall_rax]
    mov eax, 2
    call scheduler_profile_apply64
    test eax, eax
    jz scheduler_fail
    cmp eax, 2
    je .denied
%ifdef REIST_NATIVE_IPC_BINDING
    cmp qword [rel syscall_rax], 49
    jae process_ipc_syscall64
%endif
    ; Unused arguments must be zero before syscall-visible effects.
    mov rax, [rel syscall_rsi]
    or rax, [rel syscall_rdx]
    or rax, [rel syscall_r10]
    or rax, [rel syscall_r8]
    or rax, [rel syscall_r9]
    jnz .invalid
    mov rax, [rel syscall_rax]
    cmp eax, REIST_SYS_EXIT
    je .exit
    cmp eax, REIST_SYS_SLEEP_MS
    je .sleep
    cmp qword [rel syscall_rdi], 0
    jne .invalid
    cmp eax, REIST_SYS_YIELD
    je .yield
    cmp eax, REIST_SYS_GETPID
    je .pid
    cmp eax, REIST_SYS_MONOTONIC_MS
    jne scheduler_fail
    mov eax, [rel scheduler_last_tick]
    imul rax, 10
    jmp process_run_resume64
.pid:
    mov rax, [r12+TASK_GENERATION]
    jmp process_run_resume64
.yield:
    xor eax, eax
    jmp process_run_resume64
.sleep:
    mov rax, [rel syscall_rdi]
    dec rax
    cmp rax, 99
    ja .invalid
    add eax, 10
    xor edx, edx
    mov ecx, 10
    div ecx
    add eax, [rel scheduler_last_tick]
    cmp eax, SHELL_CLOCK_LIMIT
    jae .invalid
    mov r15, rax
    call scheduler_save_syscall_context64
    mov qword [r12+TASK_RAX], 0
    mov qword [r12+TASK_STATE], TASK_BLOCKED
    mov edi, [rel scheduler_current_slot]
    mov rsi, [r12+TASK_GENERATION]
    mov rdx, r15
    mov eax, 1
    mov r9d, 1
    call scheduler_queue_apply64
    test eax, eax
    jz scheduler_fail
    jmp process_run_dispatch64
.exit:
    mov r8, [rel syscall_rdi]
    mov rax, r8
    shr rax, 32
    jnz .invalid
    mov edx, TASK_EXITED
    mov r9, [rel syscall_rcx]
    jmp process_run_retire64
.context:
    mov edx, TASK_FAULTED
    mov r9, [rel syscall_rcx]
    jmp process_run_retire64
.invalid:
    mov rax, REIST_EINVAL
    jmp process_run_resume64
.denied:
    mov rax, REIST_EACCES
    jmp process_run_resume64

process_run_resume64:
    mov r15, rax
    call scheduler_save_syscall_context64
    mov [r12+TASK_RAX], r15
    mov qword [r12+TASK_STATE], TASK_READY
    mov edi, [rel scheduler_current_slot]
    mov rsi, [r12+TASK_GENERATION]
    call scheduler_runqueue_enqueue64
    test eax, eax
    jz scheduler_fail
    jmp process_run_dispatch64

process_run_exception64:
    call process_run_validate64
    test eax, eax
    jz .bad
    mov eax, [rel scheduler_current_slot]
    cmp eax, TASK_SLOT_CAPACITY
    jae .bad
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    cmp qword [r12+TASK_STATE], TASK_RUNNING
    jne .bad
    mov rax, cr3
    cmp [r12+TASK_CR3], rax
    jne .bad
    call x86_64_user_fault_status64
    test eax, eax
    jz .bad
    mov r8d, eax
    mov r9, [rdi+EXCEPTION_FRAME_RIP]
    mov edx, TASK_FAULTED
    jmp process_run_retire64
.bad:
    xor eax, eax
    ret

; IRQ admission is read-only. Every effect below occurs after EOI in the tail.
process_run_irq_validate64:
    call process_run_validate64
    test eax, eax
    jz .bad
    cmp qword [rdi+EXCEPTION_FRAME_CS], KERNEL_CODE_SELECTOR
    je .idle
    cmp qword [rdi+EXCEPTION_FRAME_CS], USER_CODE_SELECTOR
    jne .bad
    cmp qword [rdi+EXCEPTION_FRAME_SS], USER_DATA_SELECTOR
    jne .bad
    mov eax, [rel scheduler_current_slot]
    cmp eax, TASK_SLOT_CAPACITY
    jae .bad
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    cmp qword [r12+TASK_STATE], TASK_RUNNING
    jne .bad
    mov rax, cr3
    cmp [r12+TASK_CR3], rax
    jne .bad
    mov rax, [rdi+EXCEPTION_FRAME_RFLAGS]
    mov rcx, ~0x254fd7
    test rax, rcx
    jnz .bad
    and eax, 0x202
    cmp eax, 0x202
    jne .bad
    test qword [rdi+EXCEPTION_FRAME_RFLAGS], 0x4000
    jnz .context
    mov rax, [rdi+EXCEPTION_FRAME_RSP]
    cmp rax, USER_STACK_BASE
    jb .stack
    cmp rax, USER_STACK_TOP
    ja .stack
    mov rax, [rdi+EXCEPTION_FRAME_RIP]
    call scheduler_validate_task_instruction64
    test eax, eax
    jz .context
    push rsi
    xor eax, eax
    mov esi, 1
    call scheduler_context_apply64
    pop rsi
    ret
.stack:
    mov eax, 2
    ret
.context:
    mov eax, 3
    ret
.idle:
    cmp qword [rdi+EXCEPTION_FRAME_SS], KERNEL_DATA_SELECTOR
    jne .bad
    mov rax, cr3
    cmp rax, [rel scheduler_original_cr3]
    jne .bad
    cmp byte [rel scheduler_runqueue_count], 0
    jne .bad
    cmp byte [rel scheduler_deadline_count], 0
    je .bad
    movzx eax, byte [rel scheduler_deadline_count]
    cmp eax, [rel process_run_live]
    jne .bad
    test qword [rdi+EXCEPTION_FRAME_RFLAGS], 0x200
    jz .bad
    mov rax, [rdi+EXCEPTION_FRAME_RIP]
    lea rdx, [rel process_run_dispatch64.idle_wait]
    cmp rax, rdx
    jb .bad
    lea rdx, [rel process_run_dispatch64.idle_resume]
    cmp rax, rdx
    ja .bad
    mov rax, [rdi+EXCEPTION_FRAME_RSP]
    lea rdx, [rel scheduler_kernel_stack_bottom]
    cmp rax, rdx
    jb .bad
    lea rdx, [rel scheduler_kernel_stack_top]
    cmp rax, rdx
    ja .bad
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret

; Legacy timer calls this before EOI; only validate the next tick here.
process_run_tick_admit64:
    mov eax, [rel scheduler_last_tick]
    inc eax
    cmp eax, esi
    jne .bad
    cmp eax, SHELL_CLOCK_LIMIT
    jae .bad
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret

process_run_irq_tail64:
    ; Preserve frame and classification; wake only after the completed IRQ.
    push rdi
    push rdx
    push rsi
    call process_run_wake64
    pop rsi
    pop rdx
    pop rdi
    test eax, eax
    jz scheduler_fail
    cmp qword [rdi+EXCEPTION_FRAME_CS], KERNEL_CODE_SELECTOR
    je .idle
    mov r8d, SHELL_STACK_STATUS
    cmp edx, 2
    je .retire
    mov r8d, SHELL_CONTEXT_STATUS
    cmp edx, 3
    je .retire
    mov eax, [rel scheduler_current_slot]
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    call scheduler_fp_save64
    push rsi
    mov esi, 1
    mov eax, 1
    call scheduler_context_apply64
    pop rsi
    test eax, eax
    jz scheduler_fail
    push rdi
    mov edx, esi
    mov rsi, [r12+TASK_GENERATION]
    mov edi, [rel scheduler_current_slot]
    mov eax, 2
    call scheduler_budget_apply64
    pop rdi
    test eax, eax
    jz scheduler_fail
    mov r8d, SHELL_CPU_STATUS
    cmp eax, 2
    je .retire
    mov qword [r12+TASK_STATE], TASK_READY
    mov edi, [rel scheduler_current_slot]
    mov rsi, [r12+TASK_GENERATION]
    call scheduler_runqueue_enqueue64
    test eax, eax
    jz scheduler_fail
    jmp process_run_dispatch64
.retire:
    mov r9, [rdi+EXCEPTION_FRAME_RIP]
    mov edx, TASK_FAULTED
    jmp process_run_retire64
.idle:
    mov eax, 1
    ret

process_run_wake64:
    mov [rel scheduler_last_tick], esi
%ifdef REIST_NATIVE_IPC_BINDING
    cmp byte [rel scheduler_deadline_count], 0
    je .ipc_not_due
    mov eax, esi
    cmp [rel scheduler_deadline_entries], rax
    ja .ipc_not_due
    push rsi
    mov edi, 2
    xor esi, esi
    mov edx, [rel process_run_generations]
    call process_ipc_service64
    pop rsi
.ipc_not_due:
%endif
    mov ebp, esi
    xor ebx, ebx
.next:
    cmp byte [rel scheduler_deadline_count], 0
    je .done
    lea r10, [rel scheduler_deadline_entries]
    cmp [r10], rbp
    ja .done
    cmp ebx, TASK_SLOT_CAPACITY
    jae .bad
    mov esi, [r10+8]
    movzx edi, byte [r10+12]
    mov rdx, [r10]
    mov r9d, 1
    mov eax, 3
    call scheduler_queue_apply64
    test eax, eax
    jz .bad
    mov eax, edi
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    mov qword [r12+TASK_STATE], TASK_READY
    call scheduler_runqueue_enqueue64
    test eax, eax
    jz .bad
    inc ebx
    jmp .next
.done:
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret

; EDX terminal state, R8 raw status, R9 RIP. No role/expected-status policy.
process_run_retire64:
    call process_run_validate64
    test eax, eax
    jz scheduler_fail
    mov edi, [rel scheduler_current_slot]
    mov eax, edi
    shl eax, 8
    lea r12, [rel scheduler_tasks]
    add r12, rax
    cmp qword [r12+TASK_STATE], TASK_RUNNING
    jne scheduler_fail
    mov rax, cr3
    cmp [r12+TASK_CR3], rax
    jne scheduler_fail
    mov [rel process_run_receipt], edi
    mov eax, [r12+TASK_GENERATION]
    mov [rel process_run_receipt+4], eax
    mov [rel process_run_receipt+8], r8d
    mov [rel process_run_receipt+12], edx
    mov [rel process_run_receipt+24], r9
    mov eax, edi
    shl eax, 5
    lea rcx, [rel scheduler_cpu_budgets]
    mov rax, [rcx+rax+16]
    mov [rel process_run_receipt+16], rax
    mov [r12+TASK_STATE], rdx
    mov rsi, [r12+TASK_GENERATION]
    mov eax, edi
    shl eax, 5
    lea rdx, [rel process_run_plan+16]
    mov rdx, [rdx+rax+8]
    mov eax, 3
    call scheduler_profile_apply64
    test eax, eax
    jz scheduler_fail
    mov rax, [rel scheduler_original_cr3]
    mov cr3, rax
    lea rsp, [rel scheduler_kernel_stack_top]
    call scheduler_restore_kernel_segments64
    call x86_64_fp_reset64
%ifdef REIST_NATIVE_IPC_BINDING
    mov edi, 4
    mov esi, [rel scheduler_current_slot]
    mov rdx, [r12+TASK_GENERATION]
    call process_ipc_service64
%endif
    call scheduler_release_task_frames64
    test eax, eax
    jz scheduler_fail
    mov edi, [rel scheduler_current_slot]
    mov rsi, [r12+TASK_GENERATION]
    xor edx, edx
    mov eax, 3
    call scheduler_budget_apply64
    test eax, eax
    jz scheduler_fail
    mov eax, 3
    call scheduler_identity_apply64
    test eax, eax
    jz scheduler_fail
    inc dword [rel scheduler_reap_count]
    dec dword [rel process_run_live]
    call process_run_validate64
    test eax, eax
    jz scheduler_fail
    lea rsi, [rel process_run_reap_message]
    call serial_write64
    mov r14d, 32
    lea r13, [rel process_run_receipt]
.hex:
    mov al, [r13]
    call scheduler_hex8_local64
    inc r13
    dec r14d
    jnz .hex
    lea rsi, [rel scheduler_newline]
    call serial_write64
    lea rdi, [rel process_run_receipt]
    xor eax, eax
    mov ecx, 4
    rep stosq
    jmp process_run_dispatch64

process_run_finish64:
    mov byte [rel scheduler_failure_stage], 0xE2
%ifdef REIST_NATIVE_IPC_BINDING
    mov edi, 5
    xor esi, esi
    mov edx, [rel process_run_generations]
    call process_ipc_service64
%endif
    call scheduler_cleanup_common64
    test eax, eax
    jz scheduler_fail
    ; Per-task state was validated empty, and common cleanup proves frame balance.
    lea rdi, [rel process_run_plan]
    xor eax, eax
    mov ecx, 144/8
    rep stosq
    lea rdi, [rel process_run_generations]
    mov ecx, 16/8
    rep stosq
    mov [rel process_run_build_slot], eax
    lea rdi, [rel scheduler_syscall_context]
    mov ecx, 2
    rep stosq
    lea rdi, [rel syscall_rax]
    mov ecx, (scheduler_state_end-syscall_rax)/8
    rep stosq
    lea rsi, [rel process_run_ok_message]
    call serial_write64
    mov byte [rel scheduler_final_result], 1
    jmp scheduler_return64
