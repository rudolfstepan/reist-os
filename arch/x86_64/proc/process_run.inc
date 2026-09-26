%include "arch/x86_64/mm/native_layout.inc"
; Role-independent private adapter. Included in the existing scheduler object;
; all allocation, queue, context, generation, profile and FP cores are shared.
; The caller admits a finite independent set; no task is another task's owner.

; Pure read-only SysV descriptor admission. Arguments remain opaque64 bits.
process_run_admit64:
%ifdef REIST_NATIVE_DESKTOP_CPU
    xor r10d,r10d
.body:
%endif
    test rdi, rdi
    jz .bad
    test rdi, 7
    jnz .bad
%ifdef REIST_NATIVE_TASK_POOL
%ifdef REIST_NATIVE_SERVICE_CPU
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp dword [rdi],6
    je .service_header
%endif
    cmp dword [rdi],5
    je .service_header
%endif
    cmp dword [rdi],4
    je .pool_header
%endif
    cmp dword [rdi], 1
%ifdef REIST_NATIVE_PROGRAMS
    je .version_ok
    cmp dword [rdi],2
%ifdef REIST_NATIVE_LIFECYCLE
    je .version_ok
    cmp dword [rdi],3
%endif
    jne .bad
.version_ok:
%else
    jne .bad
%endif
    cmp dword [rdi+4], 144
    jne .bad
    mov edx, [rdi+8]
    dec edx
    cmp edx, 3
    ja .bad
    inc edx
%ifdef REIST_NATIVE_TASK_POOL
    jmp .dimensions
.pool_header:
    cmp dword [rdi+4],272
    jne .bad
%ifdef REIST_NATIVE_SERVICE_CPU
    jmp .pool_count
.service_header:
    cmp dword [rdi+4],336
    jne .bad
.pool_count:
%endif
    cmp dword [rdi+8],8
    jne .bad
    mov edx,8
.dimensions:
%endif
    cmp dword [rdi+12], 0
    jne .bad
    mov r8, (1<<9)|(1<<22)|(1<<40)|(1<<41)|(1<<42)
%ifdef REIST_NATIVE_CONSOLE
    or r8,(1<<15)|(1<<20)
%endif
%ifdef REIST_NATIVE_HEAP_BINDING
    or r8,(1<<4)|(1<<5)|(1<<6)
%endif
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
%ifdef REIST_NATIVE_CONSOLE
    test rax,(1<<15)|(1<<20)
    jz .console_admitted
%ifdef REIST_NATIVE_TERMINAL
    cmp ecx,2
    jb .console_root
    and eax,(1<<15)|(1<<20)
    cmp eax,(1<<15)|(1<<20)
    jne .bad
    mov rax,[r9+8]
    jmp .console_version
.console_root:
%endif
    test ecx,ecx
    jnz .bad
%ifdef REIST_NATIVE_TERMINAL
.console_version:
%endif
%ifdef REIST_NATIVE_SERVICE_CONSOLE
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp dword [rdi],6
    je .console_admitted
%endif
    cmp dword [rdi],5
%else
    cmp dword [rdi],2
%endif
    jne .bad
.console_admitted:
%endif
    test rax, 1<<9 ; an orderly exit must always be available
    jz .bad
    mov rax, [r9+16]
    dec rax
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp dword [rdi],6
    jne .old_plan_limit
    test ecx,ecx
    jz .desktop_limit
    ; Only the internal live-plan gate admits an already published child64.
    ; Initial admission keeps every other slot at32; peer1 always stays32.
    test r10d,r10d
    jz .old_plan_limit
    cmp ecx,2
    jb .old_plan_limit
    cmp qword [rdi+272+rcx*8],100
    jne .old_plan_limit
    cmp qword [rdi+272],100
    jne .bad
    mov r11,[r9+16]
    cmp r11,[rdi+32]
    ja .bad
.desktop_limit:
    cmp rax,63
    ja .bad
    jmp .plan_limit_valid
.old_plan_limit:
%endif
    cmp rax, 31
    ja .bad
%ifdef REIST_NATIVE_DESKTOP_CPU
.plan_limit_valid:
%endif
%ifdef REIST_NATIVE_PROGRAMS
    cmp dword [rdi],2
    jb .v1
%ifdef REIST_NATIVE_LIFECYCLE
    cmp dword [rdi],3
%ifdef REIST_NATIVE_TASK_POOL
    je .family_entry
%ifdef REIST_NATIVE_SERVICE_CPU
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp dword [rdi],6
    je .family_entry
%endif
    cmp dword [rdi],5
    je .family_entry
%endif
    cmp dword [rdi],4
%endif
    jne .image
%ifdef REIST_NATIVE_TASK_POOL
.family_entry:
%ifdef REIST_NATIVE_SERVICE_CPU
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp dword [rdi],6
    je .family_dimensions
%endif
    cmp dword [rdi],5
    je .family_dimensions
%endif
    cmp dword [rdi],4
    je .family_dimensions
%endif
    cmp dword [rdi+8],4
    jne .bad
%ifdef REIST_NATIVE_TASK_POOL
.family_dimensions:
%endif
    xor eax,eax
    cmp ecx,2
    setb al
    cmp [r9],rax
    jne .bad
    cmp ecx,2
    jb .image
    lea eax,[rcx+5]
    cmp [r9+24],rax
    je .next
.image:
%endif
    mov rax,[r9+24]
    sub rax,3
    cmp rax,3
    ja .bad
    jmp .next
.v1:
%endif
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
%ifdef REIST_NATIVE_SERVICE_CPU
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp dword [rdi],6
    je .desktop_period
%endif
    cmp dword [rdi],5
    jne .nonperiodic_entry
%ifdef REIST_NATIVE_DESKTOP_CPU
.desktop_period:
%endif
    mov rax,[rdi+272+rcx*8]
    cmp ecx,2
    jb .root_period
    test rax,rax
    jz .period_valid
.root_period:
    cmp rax,100
    jne .bad
.period_valid:
    inc ecx
    cmp ecx,8
    jb .entry
    jmp .admitted
.nonperiodic_entry:
%endif
    inc ecx
%ifdef REIST_NATIVE_TASK_POOL
    cmp dword [rdi],4
    jne .legacy_next
    cmp ecx,8
    jb .entry
    jmp .admitted
.legacy_next:
%endif
    cmp ecx, 4
    jb .entry
%ifdef REIST_NATIVE_TASK_POOL
.admitted:
%endif
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret

%ifdef REIST_NATIVE_DESKTOP_CPU
process_run_live_admit64:
    mov r10d,1
    jmp process_run_admit64.body
%endif

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
%ifdef REIST_NATIVE_TASK_POOL
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    jne .bad
%endif
    lea rdi, [rel process_run_plan]
%ifdef REIST_NATIVE_DESKTOP_CPU
    call process_run_live_admit64
%else
    call process_run_admit64
%endif
    test eax, eax
    jz .bad
    lea rax, [rel scheduler_tasks]
    cmp [rel scheduler_identity_pool], rax
    jne .bad
    lea rax, [rel scheduler_identity_retired]
    cmp [rel scheduler_identity_pool+8], rax
    jne .bad
    cmp dword [rel scheduler_identity_pool+16], NATIVE_POOL_TASKS
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
%ifdef REIST_NATIVE_RUNTIME
    mov rax,1<<60
    cmp [rel scheduler_last_tick],rax
%else
    cmp dword [rel scheduler_last_tick], SHELL_CLOCK_LIMIT
%endif
    jae .bad
%ifdef REIST_NATIVE_HEAP_BINDING
    mov eax,[rel process_heap_pending_mask]
    mov edx,[rel process_heap_retire_mask]
    test eax,edx
    jnz .bad
    or eax,edx
    test eax,~NATIVE_POOL_MASK
    jnz .bad
%endif
    xor ebx, ebx
    xor ebp, ebp ; live task count
    xor r14d, r14d ; running task count
.task:
    mov eax, ebx
    shl eax, NATIVE_TASK_SHIFT
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
%ifdef REIST_NATIVE_HEAP_BINDING
    bt dword [rel process_heap_pending_mask],ebx
    jnc .not_heap_pending
    cmp qword [r12+TASK_STATE],TASK_READY
    jne .bad
.not_heap_pending:
    bt dword [rel process_heap_retire_mask],ebx
    jnc .not_heap_retiring
    cmp qword [r12+TASK_STATE],TASK_FAULTED
    je .not_heap_retiring
    cmp qword [r12+TASK_STATE],TASK_EXITED
    jne .bad
.not_heap_retiring:
%endif
    cmp ebx, [rel process_run_plan+8]
    jae .outside
    test esi, esi
%ifdef REIST_NATIVE_LIFECYCLE
    jnz .has_generation
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    je .outside
.has_generation:
%endif
    jz .bad
    cmp esi, [rel process_run_generation]
    ja .bad
%ifdef REIST_NATIVE_LIFECYCLE
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    je .generation_ready
%endif
    mov eax, [rel process_run_generation]
    sub eax, [rel process_run_plan+8]
    inc eax
    add eax, ebx
    cmp esi, eax
    jne .bad
.generation_ready:
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
%ifdef REIST_NATIVE_HEAP_BINDING
    jne .heap_terminal
%else
    jne .bad
%endif
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
    cmp ecx, NATIVE_POOL_TASKS
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
%ifdef REIST_NATIVE_RUNTIME
    mov rax, [rel scheduler_last_tick]
%else
    mov eax, [rel scheduler_last_tick]
%endif
    cmp [rdx], rax
    jbe .bad
%ifdef REIST_NATIVE_RUNTIME
    mov rax,1<<60
    cmp [rdx],rax
%else
    cmp qword [rdx], SHELL_CLOCK_LIMIT
%endif
    jae .bad
    inc r8d
.deadline_next:
    add rdx, 16
    inc ecx
    cmp ecx, NATIVE_POOL_TASKS
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
%ifdef REIST_NATIVE_RUNTIME
    mov rax, [rel scheduler_last_tick]
%else
    mov eax, [rel scheduler_last_tick]
%endif
    cmp [r15+24], rax
    ja .bad
    jmp .next
%ifdef REIST_NATIVE_HEAP_BINDING
.heap_terminal:
    cmp qword [r12+TASK_STATE],TASK_FAULTED
    je .heap_terminal_state
    cmp qword [r12+TASK_STATE],TASK_EXITED
    jne .bad
.heap_terminal_state:
    bt dword [rel process_heap_retire_mask],ebx
    jnc .bad
    lea rax,[rel scheduler_runqueue_membership]
    cmp byte [rax+rbx],0
    jne .bad
    lea rax,[rel scheduler_deadline_membership]
    cmp byte [rax+rbx],0
    jne .bad
    mov eax,ebx
    shl eax,4
    lea rdx,[rel scheduler_syscall_profiles]
    mov rcx,[rdx+rax]
    or rcx,[rdx+rax+8]
    jnz .bad
    mov edi,ebx
    xor edx,edx
    xor eax,eax
    call scheduler_budget_apply64
    cmp eax,1
    jne .bad
    jmp .next
%endif
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
%ifdef REIST_NATIVE_SERVICE_CPU
    mov eax,ebx
    shl eax,5
    lea rdx,[rel scheduler_cpu_windows]
    add rdx,rax
    mov rax,[rdx]
    or rax,[rdx+8]
    or rax,[rdx+16]
    or rax,[rdx+24]
    jnz .bad
%endif
.next:
    inc ebx
    cmp ebx, NATIVE_POOL_TASKS
    jb .task
    cmp r14d, 1
    ja .bad
    cmp ebp, [rel process_run_live]
    jne .bad
    add ebp, [rel scheduler_reap_count]
%ifdef REIST_NATIVE_LIFECYCLE
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    jne .legacy_total
    cmp ebp,[rel family_total]
    jne .bad
    call family_validate_runtime64
    test eax,eax
    jz .bad
    jmp .total_ready
.legacy_total:
%endif
    cmp ebp, [rel process_run_plan+8]
    jne .bad
.total_ready:
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
%ifdef REIST_NATIVE_LARGE_IMAGE
%ifdef REIST_NATIVE_TASK_POOL
%define REIST_LARGE_POOL_FRAME_SCAN 1
%endif
%endif
%ifndef REIST_LARGE_POOL_FRAME_SCAN
    sub rsp, NATIVE_POOL_TASKS*NATIVE_CLAIM_FRAMES*8
%endif
%ifdef REIST_NATIVE_WIDE
    ; Invocation-local negative filter, never cached authority. Collisions
    ; still execute the exact full-width scan below; every frame is recorded.
    sub rsp,64
    xor eax,eax
%assign frame_filter_word 0
%rep 8
%ifdef REIST_LARGE_POOL_FRAME_SCAN
    mov [rsp+frame_filter_word*8],rax
%else
    mov [rsp+NATIVE_POOL_TASKS*NATIVE_CLAIM_FRAMES*8+frame_filter_word*8],rax
%endif
%assign frame_filter_word frame_filter_word+1
%endrep
%endif
    xor r8d, r8d
    xor ebx, ebx
.slot:
    mov eax, ebx
    shl eax, NATIVE_TASK_SHIFT
    lea r12, [rel scheduler_tasks]
    add r12, rax
    shr eax, NATIVE_TASK_SHIFT-5
    lea r13, [rel scheduler_table_frames]
    add r13, rax
    xor ecx, ecx
.frame:
    cmp ecx, NATIVE_IMAGE_PAGES
    jb .private
    je .stack
    mov edx, ecx
    sub edx, NATIVE_IMAGE_PAGES+1
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
    cmp ecx, NATIVE_IMAGE_PAGES
    jae .bad
    jmp .next
.present:
    test rax, PAGE_SIZE-1
    jnz .bad
%ifdef REIST_NATIVE_MEMORY_PROFILE
    MEMORY_COMPARE_LIMIT rax
%else
    ; Standalone legacy binding retains its caller-supplied128MiB constant.
    cmp rax, MANAGED_LIMIT
%endif
    jae .bad
    cmp rax, [rel scheduler_original_cr3]
    je .bad
    cmp ecx, NATIVE_IMAGE_PAGES+1
    jne .distinct
    cmp [r12+TASK_CR3], rax
    jne .bad
.distinct:
%ifdef REIST_NATIVE_WIDE
    mov r9,rax
    shr r9,12
    mov r10,r9
    shr r10,9
    xor r9,r10
    mov r10,rax
    shr r10,30
    xor r9,r10
    and r9d,511
%ifdef REIST_LARGE_POOL_FRAME_SCAN
    bts qword [rsp],r9
%else
    bts qword [rsp+NATIVE_POOL_TASKS*NATIVE_CLAIM_FRAMES*8],r9
%endif
    jnc .record
%endif
%ifdef REIST_LARGE_POOL_FRAME_SCAN
    ; A collision proves nothing: compare the exact full-width frame against
    ; every preceding position in the authoritative, read-only owner arrays.
    ; At most8*261 positions; only the64-byte local filter occupies the stack.
    ; IRQ/dispatch callers have interrupts disabled; no shared scratch or cache.
%ifdef REIST_NATIVE_DESKTOP_CPU
    xor r8d,r8d
    lea r10,[rel scheduler_tasks]
    lea r11,[rel scheduler_table_frames]
..@ci_slot:
    ; Compare the same exact prefix as contiguous regions. Region selection
    ; is once per slot, instead of once per private-frame position.
    mov r9d,NATIVE_IMAGE_PAGES
    cmp r8d,ebx
    jne ..@ci_private_range
    cmp ecx,r9d
    cmovb r9d,ecx
..@ci_private_range:
    test r9d,r9d
    jz ..@ci_private_end
    lea rdi,[r10+TASK_PRIVATE_FRAMES]
    mov esi,ecx
    mov ecx,r9d
    cld
    repne scasq
    mov ecx,esi
    je .bad
..@ci_private_end:
    cmp r8d,ebx
    jne ..@ci_stack
    cmp ecx,NATIVE_IMAGE_PAGES
    jbe .record
..@ci_stack:
    cmp rax,[r10+TASK_STACK_FRAME]
    je .bad
    mov r9d,NATIVE_CLAIM_FRAMES-NATIVE_IMAGE_PAGES-1
    cmp r8d,ebx
    jne ..@ci_table_range
    mov r9d,ecx
    sub r9d,NATIVE_IMAGE_PAGES+1
..@ci_table_range:
    test r9d,r9d
    jz ..@ci_table_end
    mov rdi,r11
    mov esi,ecx
    mov ecx,r9d
    cld
    repne scasq
    mov ecx,esi
    je .bad
..@ci_table_end:
    cmp r8d,ebx
    je .record
    inc r8d
    add r10,NATIVE_TASK_BYTES
    add r11,32
    jmp ..@ci_slot
%else
    xor r8d,r8d
    lea r10,[rel scheduler_tasks]
    lea r11,[rel scheduler_table_frames]
.prior_slot:
    xor r9d,r9d
.prior_frame:
    cmp r8d,ebx
    jne .prior_read
    cmp r9d,ecx
    jae .record
.prior_read:
    cmp r9d,NATIVE_IMAGE_PAGES
    jb .prior_private
    je .prior_stack
    mov edx,r9d
    sub edx,NATIVE_IMAGE_PAGES+1
    mov rdx,[r11+rdx*8]
    jmp .prior_compare
.prior_private:
    mov rdx,[r10+TASK_PRIVATE_FRAMES+r9*8]
    jmp .prior_compare
.prior_stack:
    mov rdx,[r10+TASK_STACK_FRAME]
.prior_compare:
    cmp rax,rdx
    je .bad
    inc r9d
    cmp r9d,NATIVE_CLAIM_FRAMES
    jb .prior_frame
    inc r8d
    add r10,NATIVE_TASK_BYTES
    add r11,32
    jmp .prior_slot
%endif
.record:
%else
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
%endif
.next:
    inc ecx
    cmp ecx, NATIVE_CLAIM_FRAMES
    jb .frame
    inc ebx
    cmp ebx, NATIVE_POOL_TASKS
    jb .slot
    mov eax, 1
    jmp .return
.bad:
    xor eax, eax
.return:
%ifdef REIST_NATIVE_WIDE
    add rsp,64
%endif
%ifndef REIST_LARGE_POOL_FRAME_SCAN
    add rsp, NATIVE_POOL_TASKS*NATIVE_CLAIM_FRAMES*8
%endif
    ret
%undef REIST_LARGE_POOL_FRAME_SCAN

; Trusted caller pointer is pinned to C rodata by the bridge. No user pointer.
global x86_64_process_run64
x86_64_process_run64:
    cli
    cld
    call process_run_admit64
    test eax, eax
    jz .reject
%ifdef REIST_NATIVE_TASK_POOL
    ; Pure admission also understands legacy descriptors. This selected
    ; runtime may copy its full extent only from its explicitly admitted ABI.
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rdi]
%else
    cmp dword [rdi],NATIVE_POOL_RUN_VERSION
%endif
    jne .reject
%endif
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
    mov ecx, NATIVE_POOL_RUN_BYTES/8
    rep movsq
    lea rdi, [rel scheduler_state_begin]
    xor eax, eax
    mov ecx, (scheduler_state_end-scheduler_state_begin)/8
    rep stosq
    lea rdi, [rel process_run_generations]
    mov ecx, NATIVE_POOL_TASKS*4/8
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
    mov dword [rel scheduler_identity_pool+16], NATIVE_POOL_TASKS
    mov eax, [rel process_run_generation]
    mov [rel scheduler_identity_pool+20], eax
%ifdef REIST_NATIVE_RUNTIME
    call x86_64_timer_runtime_peek64
    cmp rax,-1
    je scheduler_fail
    mov [rel scheduler_last_tick],rax
%endif
    call physical_free_frame_count64
    mov [rel scheduler_initial_free], eax
%ifdef REIST_NATIVE_PROGRAMS
    cmp dword [rel process_run_plan],2
    jae .prepare_build
%endif
    mov edi, ELF_IMAGE_PROBE
    call x86_64_elf64_select_image64
    test eax, eax
    jz scheduler_fail
    call x86_64_elf64_load64
    test eax, eax
    jz scheduler_fail
    call x86_64_elf64_entry64
    mov [rel scheduler_entry], rax
.prepare_build:
%ifdef REIST_NATIVE_LIFECYCLE
    call family_initialize64
%endif
    mov dword [rel process_run_build_slot], 0
.build:
%ifdef REIST_NATIVE_PROGRAMS
    cmp dword [rel process_run_plan],2
    jb .selected
    mov eax,[rel process_run_build_slot]
    shl eax,5
    lea rdi,[rel process_run_plan+16]
    mov edi,[rdi+rax+24]
    call x86_64_elf64_select_image64
    cmp eax,1
    jne scheduler_fail
    call x86_64_elf64_entry64
    test rax,rax
    jnz .entry_ready
    call x86_64_elf64_load64
    cmp eax,1
    jne scheduler_fail
    call x86_64_elf64_entry64
.entry_ready:
    mov [rel scheduler_entry],rax
.selected:
%endif
    mov edi, [rel process_run_build_slot]
    call scheduler_build_task64
    test eax, eax
    jz scheduler_fail
%ifdef REIST_NATIVE_PROGRAMS
    cmp dword [rel process_run_plan],2
    jb .stack_ready
%ifdef REIST_NATIVE_WIDE
    call scheduler_stack_page64
%else
    mov rdi,DIRECT_MAP_BASE
    add rdi,[r12+TASK_STACK_FRAME]
%endif
    call x86_64_boot_program_stack64
    test rax,rax
    jle scheduler_fail
    mov [r12+TASK_RSP],rax
.stack_ready:
%endif
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
%ifdef REIST_NATIVE_LIFECYCLE
    call family_root_built64
%endif
    inc dword [rel process_run_build_slot]
    mov eax, [rel process_run_build_slot]
%ifdef REIST_NATIVE_LIFECYCLE
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    jne .all_initial
    cmp eax,2
    jb .build
    jmp .initial_built
.all_initial:
%endif
    cmp eax, [rel process_run_plan+8]
    jb .build
.initial_built:
%ifdef REIST_NATIVE_IPC_BINDING
    xor ebx, ebx
.ipc_bind:
    mov edi, 0
    mov esi, ebx
    lea rax, [rel process_run_generations]
    mov edx, [rax+rbx*4]
    call process_ipc_service64
    inc ebx
%ifdef REIST_NATIVE_LIFECYCLE
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    jne .all_ipc
    cmp ebx,2
    jb .ipc_bind
    jmp .ipc_bound
.all_ipc:
%endif
    cmp ebx, [rel process_run_plan+8]
    jb .ipc_bind
.ipc_bound:
%endif
%ifdef REIST_NATIVE_HEAP_BINDING
    xor ebx,ebx
.heap_bind:
    mov edi,1
    mov esi,ebx
    xor r8d,r8d
    xor r9d,r9d
    call process_heap_service64
    test rax,rax
    jnz scheduler_fail
    inc ebx
%ifdef REIST_NATIVE_LIFECYCLE
%ifdef REIST_NATIVE_DESKTOP_CPU
    NATIVE_POOL_PLAN_CMP dword [rel process_run_plan]
%else
    cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION
%endif
    jne .all_heap
    cmp ebx,2
    jb .heap_bind
    jmp .heap_bound
.all_heap:
%endif
    cmp ebx,[rel process_run_plan+8]
    jb .heap_bind
.heap_bound:
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
%ifdef REIST_NATIVE_RUNTIME
    call x86_64_timer_runtime_arm64
%else
    call x86_64_timer_shell_arm64
%endif
    test eax, eax
    jz scheduler_fail
    jmp process_run_dispatch64
.reject:
    xor eax, eax
    ret

process_run_dispatch64:
%ifdef REIST_NATIVE_DESKTOP_CPU
    lea rdi, [rel query_state64]
    call qr_reset
    cmp eax, 1
    jne scheduler_fail
%endif
    call process_run_validate64
    test eax, eax
    jz scheduler_fail
%ifdef REIST_NATIVE_HEAP_BINDING
    call process_heap_reapers64
%endif
%ifdef REIST_NATIVE_LIFECYCLE
    call family_dispatch64
%endif
    lea rdx, [rel scheduler_tasks]
    mov ecx, NATIVE_POOL_TASKS
.quiescent:
    cmp qword [rdx+TASK_STATE], TASK_RUNNING
    je scheduler_fail
    add rdx, TASK_RECORD_SIZE
    loop .quiescent
    cmp dword [rel process_run_live], 0
    je process_run_finish64
    cmp byte [rel scheduler_runqueue_count], 0
    jne scheduler_runqueue_dispatch64
%ifdef REIST_NATIVE_HEAP_BINDING
    cmp dword [rel process_heap_retire_mask],0
    jne .kernel_work
%endif
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
%ifdef REIST_NATIVE_HEAP_BINDING
.kernel_work:
    ; A retiring task still has useful bounded work. Admit IRQs between steps
    ; without sleeping until a deadline that does not own this work.
    mov rax,[rel scheduler_original_cr3]
    mov cr3,rax
    lea rsp,[rel scheduler_kernel_stack_top]
    call scheduler_restore_kernel_segments64
    call x86_64_fp_reset64
.work_wait:
    sti
    nop
    cli
.work_resume:
    jmp process_run_dispatch64
%endif

process_run_enter64:
    ; EDI slot, R11 task, queue already popped by the shared dispatcher.
    mov rax, [r11+TASK_GENERATION]
    lea rdx, [rel process_run_generations]
    cmp [rdx+rdi*4], eax
    jne scheduler_fail
%ifdef REIST_NATIVE_DESKTOP_CPU
    push rdi
    push r11
    mov esi, edi
    mov rdx, [r11+TASK_GENERATION]
    lea rdi, [rel query_state64]
    call qr_bind
    pop r11
    pop rdi
    cmp eax, 1
    jne scheduler_fail
%endif
%ifdef REIST_NATIVE_HEAP_BINDING
    bt dword [rel process_heap_pending_mask],edi
    jc process_heap_enter64
%endif
    mov qword [r11+TASK_STATE], TASK_RUNNING
%ifdef REIST_NATIVE_DESKTOP_CPU
.query_admitted:
%endif
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
    NATIVE_STACK_CMP_RAX
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
%ifdef REIST_NATIVE_SHELL_SESSION
    call native_session_probe_request64
%endif
%ifdef REIST_NATIVE_TERMINAL
    cmp qword [rel syscall_rax],REIST_SYS_TERMINAL_INPUT
    je native_terminal_syscall64
%endif
%ifdef REIST_NATIVE_SHELL_SESSION
    cmp qword [rel syscall_rax],114
    je native_identity_syscall64
%endif
%ifdef REIST_NATIVE_CONSOLE
    cmp qword [rel syscall_rax],REIST_SYS_READ
    je native_console_syscall64
    cmp qword [rel syscall_rax],REIST_SYS_WRITE
    je native_console_syscall64
%endif
%ifdef REIST_NATIVE_LIFECYCLE
    cmp qword [rel syscall_rax],132
    je family_syscall64
%endif
%ifdef REIST_NATIVE_NETWORK_DMA
    cmp qword [rel syscall_rax],113
    jne .not_network_control
    cmp qword [rel syscall_rdi],32
    je native_network_syscall64
.not_network_control:
%endif
%ifdef REIST_NATIVE_PIO
%ifdef REIST_NATIVE_VGA_CONSOLE
    cmp qword [rel syscall_rax],113
    jne .not_vga_control
    cmp qword [rel syscall_rdi],33
    je native_vga_syscall64
    cmp qword [rel syscall_rdi],31
    je native_input_syscall64
.not_vga_control:
%endif
    cmp qword [rel syscall_rax],113
%ifdef REIST_NATIVE_DISPLAY
    jne .not_display_control
%ifdef REIST_NATIVE_INPUT
    cmp qword [rel syscall_rdi],31
    je native_input_syscall64
%endif
    cmp qword [rel syscall_rdi],30
    je native_display_syscall64
    jmp native_pio_syscall64
.not_display_control:
%else
    je native_pio_syscall64
%endif
%endif
%ifdef REIST_NATIVE_HEAP_BINDING
    cmp qword [rel syscall_rax],4
    jb .not_heap
    cmp qword [rel syscall_rax],6
    jbe process_heap_syscall64
.not_heap:
%endif
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
%ifdef REIST_NATIVE_RUNTIME
    mov rax, [rel scheduler_last_tick]
%else
    mov eax, [rel scheduler_last_tick]
%endif
    imul rax, 10
%ifdef REIST_NATIVE_DESKTOP_CPU
    jmp query_resume64
%else
    jmp process_run_resume64
%endif
.pid:
    mov rax, [r12+TASK_GENERATION]
%ifdef REIST_NATIVE_DESKTOP_CPU
    jmp query_resume64
%else
    jmp process_run_resume64
%endif
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
%ifdef REIST_NATIVE_RUNTIME
    add rax, [rel scheduler_last_tick]
    jc .invalid
    mov rdx,1<<60
    cmp rax,rdx
%else
    add eax, [rel scheduler_last_tick]
    cmp eax, SHELL_CLOCK_LIMIT
%endif
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
%ifdef REIST_NATIVE_SHELL_SESSION
    call native_session_probe_denied64
%endif
    mov rax, REIST_EACCES
    jmp process_run_resume64

%ifdef REIST_NATIVE_DESKTOP_CPU
query_resume64:
    ; Admitted queries/empty IPC polls share one cap; preserve result/ownership.
    push rax
    lea rdi, [rel query_state64]
    mov esi, [rel scheduler_current_slot]
    mov rdx, [r12+TASK_GENERATION]
    call qr_take
    test eax, eax
    js scheduler_fail
    jz .dispatch
    pop rax
%ifdef REIST_NATIVE_SHELL_SESSION
    call native_session_probe_return64
%endif
    mov r15, rax
    call scheduler_save_syscall_context64
    mov [r12+TASK_RAX], r15
    cmp qword [r12+TASK_STATE], TASK_RUNNING
    jne scheduler_fail
    mov r11, r12
    mov edi, [rel scheduler_current_slot]
    jmp scheduler_enter_task64.state_published
.dispatch:
    pop rax
    jmp process_run_resume64
; QUERY_RETURN_ADAPTER_END
%endif

process_run_resume64:
%ifdef REIST_NATIVE_SHELL_SESSION
    call native_session_probe_return64
%endif
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
%ifdef REIST_NATIVE_SHELL_SESSION
    call native_session_probe_fault_site64
%endif
    call process_run_validate64
    test eax, eax
    jz .bad
    mov eax, [rel scheduler_current_slot]
    cmp eax, NATIVE_POOL_TASKS
    jae .bad
    shl eax, NATIVE_TASK_SHIFT
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
    cmp eax, NATIVE_POOL_TASKS
    jae .bad
    shl eax, NATIVE_TASK_SHIFT
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
    NATIVE_STACK_CMP_RAX
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
%ifdef REIST_NATIVE_HEAP_BINDING
    mov rax,[rdi+EXCEPTION_FRAME_RIP]
    lea rdx,[rel process_run_dispatch64.work_wait]
    cmp rax,rdx
    jb .deadline_idle
    lea rdx,[rel process_run_dispatch64.work_resume]
    cmp rax,rdx
    ja .deadline_idle
    mov eax,[rel process_heap_retire_mask]
    mov edx,[rel process_heap_pending_mask]
    or edx,eax
%ifdef REIST_NATIVE_TASK_POOL
    test edx,~NATIVE_POOL_MASK
%else
    test edx,~15
%endif
    jnz .bad
    test edx,edx
    jz .bad
%ifdef REIST_NATIVE_TASK_POOL
    test eax,~NATIVE_POOL_MASK
%else
    test eax,~15
%endif
    jnz .bad
    xor edx,edx
%ifdef REIST_NATIVE_TASK_POOL
    mov ecx,NATIVE_POOL_TASKS
%else
    mov ecx,4
%endif
.retiring_count:
    shr eax,1
    adc edx,0
    loop .retiring_count
    movzx eax,byte [rel scheduler_deadline_count]
    add eax,edx
    movzx edx,byte [rel scheduler_runqueue_count]
    add eax,edx
    cmp eax,[rel process_run_live]
    jne .bad
    test qword [rdi+EXCEPTION_FRAME_RFLAGS],0x200
    jz .bad
    jmp .kernel_stack
.deadline_idle:
%endif
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
.kernel_stack:
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
%ifdef REIST_NATIVE_RUNTIME
    mov rax, [rel scheduler_last_tick]
    add rax,1
    jc .bad
    cmp rax,rsi
    jne .bad
    mov rax,1<<60
    cmp rsi,rax
%else
    mov eax, [rel scheduler_last_tick]
    inc eax
    cmp eax, esi
    jne .bad
    cmp eax, SHELL_CLOCK_LIMIT
%endif
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
    shl eax, NATIVE_TASK_SHIFT
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
%ifdef REIST_NATIVE_RUNTIME
    mov rdx, rsi
%else
    mov edx, esi
%endif
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
    ; Wake has changed the queues. IRETQ to the pre-CLI idle instruction must
    ; not re-enable IRQs and admit a second IRQ against the old idle premise.
    ; Only this validated CPL0 frame changes; dispatcher STI or the separately
    ; admitted user context restores interruptibility after queue re-admission.
    and qword [rdi+EXCEPTION_FRAME_RFLAGS],~0x200
.idle_return:
    mov eax, 1
    ret

process_run_wake64:
%ifdef REIST_NATIVE_RUNTIME
    mov [rel scheduler_last_tick], rsi
%else
    mov [rel scheduler_last_tick], esi
%endif
%ifdef REIST_NATIVE_IPC_BINDING
    cmp byte [rel scheduler_deadline_count], 0
    je .ipc_not_due
%ifdef REIST_NATIVE_RUNTIME
    mov rax, rsi
%else
    mov eax, esi
%endif
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
%ifdef REIST_NATIVE_RUNTIME
    mov rbp, rsi
%else
    mov ebp, esi
%endif
    xor ebx, ebx
.next:
    cmp byte [rel scheduler_deadline_count], 0
    je .done
    lea r10, [rel scheduler_deadline_entries]
    cmp [r10], rbp
    ja .done
    cmp ebx, NATIVE_POOL_TASKS
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
    shl eax, NATIVE_TASK_SHIFT
    lea r12, [rel scheduler_tasks]
    add r12, rax
    mov qword [r12+TASK_STATE], TASK_READY
%ifdef REIST_NATIVE_LIFECYCLE
    call family_wait_expired64
%endif
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
    shl eax, NATIVE_TASK_SHIFT
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
%ifdef REIST_NATIVE_LIFECYCLE
    call family_terminal64
%endif
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
%ifdef REIST_NATIVE_HEAP_BINDING
    jmp process_heap_retire64
process_run_complete_retire64:
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
%ifdef REIST_NATIVE_LIFECYCLE
    call family_reaped64
%endif
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
%ifdef REIST_NATIVE_HEAP_BINDING
    ret
%else
    jmp process_run_dispatch64
%endif

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
%ifdef REIST_NATIVE_LIFECYCLE
    call family_finish64
%endif
    ; Per-task state was validated empty, and common cleanup proves frame balance.
    lea rdi, [rel process_run_plan]
    xor eax, eax
    mov ecx, NATIVE_POOL_RUN_BYTES/8
    rep stosq
    lea rdi, [rel process_run_generations]
    mov ecx, NATIVE_POOL_TASKS*4/8
    rep stosq
    mov [rel process_run_build_slot], eax
    lea rdi, [rel scheduler_syscall_context]
    mov ecx, 2
    rep stosq
    lea rdi, [rel syscall_rax]
    mov ecx, (scheduler_state_end-syscall_rax)/8
    rep stosq
    lea rsi, [rel process_run_ok_message]
%ifdef REIST_NATIVE_SHELL_SESSION
    lea rdi,[rel native_session_probe_seen]
    mov ecx,(72+12320+16)/8
    rep stosq
%endif
    call serial_write64
    mov byte [rel scheduler_final_result], 1
    jmp scheduler_return64
%ifdef REIST_NATIVE_SHELL_SESSION
; AY_COLD_PROBES_BEGIN
; Private qualification sites only. Fixed eight-slot bookkeeping never changes
; authority, counters, saved task registers or deadlines. IF/registers preserved.
native_session_probe_request64:
    pushfq
    push rax
    push rcx
    push rdx
    xor edx,edx
    jmp native_session_probe_request_common64
native_session_probe_denied64:
    pushfq
    push rax
    push rcx
    push rdx
    mov edx,1
native_session_probe_request_common64:
    cmp byte [rel scheduler_mode],SCHEDULER_MODE_PROCESS
    jne .done
    mov ecx,[rel scheduler_current_slot]
    cmp ecx,8
    jae .done
    mov rax,[rel syscall_rax]
    ; Private qualification witness only: retain the actual blocked OOM
    ; fixture pause without tracing ordinary 10ms shell polling sleeps.
    cmp rax,41
    jne .not_fixture_sleep
    test ecx,ecx
    jnz .done
    cmp qword [rel syscall_rdi],100
    jne .done
    jmp .watched
.not_fixture_sleep:
    cmp rax,63
    ja .extended
    mov rcx,(1<<9)|(1<<15)|(1<<20)|(127<<49)
    bt rcx,rax
    jnc .done
    jmp .watched
.extended:
    cmp rax,113
    je .watched
    cmp rax,114
    je .watched
    cmp rax,127
    je .watched
    cmp rax,132
    jne .done
.watched:
    mov ecx,[rel scheduler_current_slot]
    ; Independent, non-authoritative execution tickets for diagnostic READs.
    ; Saturation is sticky and outside the valid observer bound; never wrap.
    test ecx,ecx
    jnz .read_ticket_done
    cmp rax,15
    jne .read_ticket_done
    cmp qword [rel native_session_read_tickets],8193
    jae .read_ticket_done
    inc qword [rel native_session_read_tickets]
.read_ticket_done:
    cmp rax,113
    jne .ordinary
    test edx,edx
    jnz .ordinary
    push rdx
    lea rdx,[rel native_session_probe_pending]
    mov byte [rdx+rcx],2
    pop rdx
    call native_session_pio_enter64
    jmp .done
.ordinary:
    cmp rax,9
    setne al
    push rdx
    lea rdx,[rel native_session_probe_pending]
    mov [rdx+rcx],al
    pop rdx
    test edx,edx
    jnz .denied
    pop rdx
    pop rcx
    pop rax
    popfq
    jmp native_session_probe_request_site64
.denied:
    pop rdx
    pop rcx
    pop rax
    popfq
    jmp native_session_probe_denied_site64
.done:
    pop rdx
    pop rcx
    pop rax
    popfq
    ret
native_session_probe_return64:
    pushfq
    push rax
    push rcx
    cmp byte [rel scheduler_mode],SCHEDULER_MODE_PROCESS
    jne .done
    mov ecx,[rel scheduler_current_slot]
    cmp ecx,8
    jae .done
    lea rax,[rel native_session_probe_pending]
    cmp byte [rax+rcx],0
    je .done
    cmp byte [rax+rcx],2
    je .pio
    test ecx,ecx
    jnz .read_ticket_done
    cmp qword [rel syscall_rax],15
    jne .read_ticket_done
    cmp qword [rel native_session_read_tickets+8],8193
    jae .read_ticket_done
    inc qword [rel native_session_read_tickets+8]
.read_ticket_done:
    mov byte [rax+rcx],0
    pop rcx
    pop rax
    popfq
    jmp native_session_probe_return_site64
.pio:
    mov byte [rax+rcx],0
    pop rcx
    pop rax
    popfq
    jmp native_session_pio_return64
.done:
    pop rcx
    pop rax
    popfq
    ret
native_session_probe_start64:
    pushfq
    push rax
    push rcx
    push rdx
    cmp byte [rel scheduler_mode],SCHEDULER_MODE_PROCESS
    jne .done
    mov ecx,[rel scheduler_current_slot]
    cmp ecx,8
    jae .done
    lea rax,[rel native_session_probe_seen]
    mov rdx,[r11+TASK_GENERATION]
    cmp [rax+rcx*8],rdx
    jne .first
    lea rax,[rel native_session_probe_pending]
    cmp byte [rax+rcx],0
    je .done
    jmp .observe
.first:
    mov [rax+rcx*8],rdx
    lea rax,[rel native_session_probe_pending]
.observe:
    mov byte [rax+rcx],0
    pop rdx
    pop rcx
    pop rax
    popfq
    jmp native_session_probe_start_site64
.done:
    pop rdx
    pop rcx
    pop rax
    popfq
    ret
; Keep debugger breakpoints off every ordinary scheduling/syscall code page.
align 4096,db 0x90
native_session_probe_page:
native_session_probe_request_site64:
    ret
native_session_probe_denied_site64:
    ret
native_session_probe_return_site64:
    ret
native_session_probe_start_site64:
    ret
native_session_probe_pio_site64:
    ret
native_session_probe_terminal_site64:
    ret
native_session_probe_fault_site64:
    ret
align 4096,db 0x90
native_session_probe_page_end:
; AY_COLD_PROBES_END
; AY_PIO_RECORD_BEGIN
; Non-authoritative fixed capture, no allocation, acknowledgement or wait.
; Syscall113 is synchronous with IF=0. Denied profiles keep the original
; no-user-read observer route. Every GPR/RFLAGS is preserved on every path.
%macro ay_pio_save 0
    pushfq
    push rax
    push rbx
    push rcx
    push rdx
    push rsi
    push rdi
    push rbp
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    push r14
    push r15
%endmacro
%macro ay_pio_restore 0
    pop r15
    pop r14
    pop r13
    pop r12
    pop r11
    pop r10
    pop r9
    pop r8
    pop rbp
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbx
    pop rax
    popfq
%endmacro
native_session_pio_enter64:
    ay_pio_save
    lea r14,[rel native_session_pio_trace]
    cmp qword [r14+8],0
    jne .done
    cmp qword [r14+16],0
    jne .error
    cmp qword [r14+24],0
    jne .error
    cmp byte [rel scheduler_mode],8
    jne .error
    cmp dword [rel scheduler_current_slot],8
    jae .error
    mov rax,[r12+TASK_GENERATION]
    test rax,rax
    jz .error
    shr rax,31
    jnz .error
    mov rax,[rel scheduler_last_tick]
    shr rax,60
    jnz .error
    mov rax,[r14]
%ifdef REIST_NATIVE_WIDE_FILE
    cmp rax,262144
%else
    cmp rax,2048
%endif
    jae .error
    and eax,31
    imul eax,384
    lea r13,[r14+rax+32]
    mov rdi,r13
    xor eax,eax
    mov ecx,48
    rep stosq
    mov dword [r13],1
    mov rax,[r14]
    inc rax
    mov [r13+8],rax
    mov eax,[rel scheduler_current_slot]
    mov [r13+16],rax
    mov rax,[r12+TASK_GENERATION]
    mov [r13+24],rax
    mov rax,[rel scheduler_last_tick]
    mov [r13+32],rax
    mov rax,[rel syscall_rdi]
    mov [r13+64],rax
    mov rax,[rel syscall_rsi]
    mov [r13+72],rax
    mov rax,[rel syscall_rdx]
    mov [r13+80],rax
    mov rax,[rel syscall_r10]
    mov [r13+88],rax
    mov rax,[rel syscall_r8]
    mov [r13+96],rax
    mov rax,[rel syscall_r9]
    mov [r13+104],rax
    mov rax,[rsp+120]
    mov [r13+352],rax
    test rax,512
    jnz .error
    mov qword [r13+368],8
    mov rax,[r13+72]
    mov edx,64
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .error
    mov rsi,[r13+72]
    lea rdi,[r13+112]
    mov ecx,8
    rep movsq
    lea rsi,[rel native_terminal_state]
    lea rdi,[r13+240]
    mov ecx,3
    rep movsq
    mov qword [r14+16],1
    jmp .done
.error:
    mov qword [r14+8],1
.done:
    ay_pio_restore
    ret
native_session_pio_return64:
    ay_pio_save
    lea r14,[rel native_session_pio_trace]
    cmp qword [r14+8],0
    jne .done
    cmp qword [r14+16],1
    jne .error
    cmp qword [r14+24],0
    jne .error
    cmp byte [rel scheduler_mode],8
    jne .error
    mov rax,[r14]
%ifdef REIST_NATIVE_WIDE_FILE
    cmp rax,262144
%else
    cmp rax,2048
%endif
    jae .error
    and eax,31
    imul eax,384
    lea r13,[r14+rax+32]
    mov eax,[rel scheduler_current_slot]
    cmp rax,[r13+16]
    jne .error
    mov rax,[r12+TASK_GENERATION]
    cmp rax,[r13+24]
    jne .error
    mov rax,[rel scheduler_last_tick]
    cmp rax,[r13+32]
    jb .error
    mov [r13+40],rax
    shr rax,60
    jnz .error
    mov rax,[rsp+112]
    mov [r13+48],rax
    mov rax,[rsp+120]
    mov [r13+360],rax
    test rax,512
    jnz .error
    mov qword [r13+376],8
    mov rax,[r13+72]
    mov edx,64
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .error
    mov rsi,[r13+72]
    lea rdi,[r13+176]
    mov ecx,8
    rep movsq
    lea rsi,[rel native_terminal_state]
    lea rdi,[r13+264]
    mov ecx,3
    rep movsq
    lea rsi,[rel native_pio_state]
    lea rdi,[r13+288]
    mov ecx,8
    rep movsq
    mov qword [r14+16],0
    inc qword [r14]
    test qword [r14],31
    jz .notify
    jmp .done
.error:
    mov qword [r14+8],1
.done:
    ay_pio_restore
    ret
.notify:
    ay_pio_restore
    jmp native_session_probe_pio_site64
%unmacro ay_pio_save 0
%unmacro ay_pio_restore 0
; AY_PIO_RECORD_END
%endif
