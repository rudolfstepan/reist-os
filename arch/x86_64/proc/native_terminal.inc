; Pure SysV helpers. State={root,child,fenced}; view={caller,parent,root,
; target,target_parent,target_mask,target_extended,caller_mask,caller_extended}.
; No device operations or hidden state in these helpers.
global native_terminal_shape64, native_terminal_plan64
global native_terminal_io64, native_terminal_retire64
native_terminal_shape64:
    cmp qword [rdi+16],1
    ja .bad
    mov rax,[rdi]
    test rax,rax
    jz .empty
    test eax,eax
    jnz .bad
    shr rax,32
    dec eax
    cmp eax,0x7ffffffe
    ja .bad
    mov rax,[rdi+8]
    test rax,rax
    jz .good
    cmp eax,2
    jb .bad
    cmp eax,8
    jae .bad
    shr rax,32
    dec eax
    cmp eax,0x7ffffffe
    ja .bad
    jmp .good
.empty:
    cmp qword [rdi+8],0
    jne .bad
.good:
    mov eax,1
    ret
.bad:
    xor eax,eax
    ret

; RDI state, RSI view, RDX request24, RCX proposed child output.
; Only success publishes one qword to proposal. The state is always read-only.
native_terminal_plan64:
    call native_terminal_shape64
    test eax,eax
    jz .corrupt
    cmp dword [rdx],1
    jne .invalid
    cmp dword [rdx+4],24
    jne .invalid
    cmp dword [rdx+12],0
    jne .invalid
    mov eax,[rdx+8]
    dec eax
    cmp eax,4
    ja .invalid
    cmp dword [rdx+8],2
    je .target_fields
    cmp qword [rdx+16],0
    jne .invalid
    jmp .identity
.target_fields:
    mov eax,[rdx+16]
    test eax,eax
    jle .invalid
    cmp [rdx+20],eax
    jne .stale
.identity:
    mov rax,[rsi+16]
    cmp [rdi],rax
    jne .corrupt
    test rax,rax
    jz .denied
    cmp qword [rdi+16],0
    jne .io_error
    cmp dword [rdx+8],4
    je .unsupported
    cmp [rsi],rax
    je .root
    cmp [rsi+8],rax
    jne .denied
    mov rax,[rsi+56]
    and eax,(1<<15)|(1<<20)
    cmp eax,(1<<15)|(1<<20)
    jne .denied
    mov rax,1<<63
    cmp [rsi+64],rax
    jne .denied
    cmp dword [rdx+8],5
    je .check_child
    cmp dword [rdx+8],3
    jne .denied
    mov rax,[rsi]
    cmp [rdi+8],rax
    jne .unchanged
    xor eax,eax
    jmp .publish
.check_child:
    mov rax,[rsi]
    cmp [rdi+8],rax
    jne .again
    jmp .unchanged
.root:
    cmp qword [rsi+8],0
    jne .corrupt
    cmp dword [rdx+8],1
    je .unchanged
    cmp dword [rdx+8],5
    je .check_root
    cmp dword [rdx+8],2
    jne .denied
    mov rax,[rsi+24]
    test rax,rax
    jz .stale
    cmp eax,2
    jb .denied
    cmp eax,8
    jae .stale
    shr rax,32
    cmp eax,[rdx+16]
    jne .stale
    mov rax,[rdi]
    cmp [rsi+32],rax
    jne .denied
    mov rax,[rsi+40]
    and eax,(1<<15)|(1<<20)
    cmp eax,(1<<15)|(1<<20)
    jne .denied
    mov rax,1<<63
    cmp [rsi+48],rax
    jne .denied
    mov rax,[rsi+24]
    cmp qword [rdi+8],0
    je .publish
    cmp [rdi+8],rax
    jne .busy
    jmp .publish
.check_root:
    cmp qword [rdi+8],0
    jne .again
.unchanged:
    mov rax,[rdi+8]
.publish:
    mov [rcx],rax
    xor eax,eax
    ret
.corrupt: mov rax,-117
    ret
.invalid: mov rax,-22
    ret
.stale: mov rax,-116
    ret
.denied: mov rax,-13
    ret
.again: mov rax,-11
    ret
.busy: mov rax,-16
    ret
.unsupported: mov rax,-95
    ret
.io_error: mov rax,-5
    ret

; RDI state, RSI exact caller handle, EDX READ15 or WRITE20.
native_terminal_io64:
    push rdx
    call native_terminal_shape64
    pop rdx
    test eax,eax
    jz .corrupt
    cmp qword [rdi],0
    je .denied
    cmp qword [rdi+16],0
    jne .io_error
    cmp edx,15
    je .operation
    cmp edx,20
    jne .denied
.operation:
    cmp [rdi],rsi
    jne .child
    cmp edx,20
    je .good
    cmp qword [rdi+8],0
    jne .again
    jmp .good
.child:
    cmp [rdi+8],rsi
    jne .denied
.good: mov eax,1
    ret
.corrupt: mov rax,-117
    ret
.denied: mov rax,-13
    ret
.again: mov rax,-11
    ret
.io_error: mov rax,-5
    ret

; RDI state, RSI exact retiring handle. Idempotent, return1 iff changed.
native_terminal_retire64:
    call native_terminal_shape64
    test eax,eax
    jz .corrupt
    test rsi,rsi
    jz .none
    cmp [rdi],rsi
    je .root
    cmp [rdi+8],rsi
    jne .none
    mov qword [rdi+8],0
    mov eax,1
    ret
.root:
    mov qword [rdi],0
    mov qword [rdi+8],0
    mov eax,1
    ret
.none: xor eax,eax
    ret
.corrupt: mov rax,-117
    ret

; RUNTIME ADAPTER
; IF0 throughout. Validate private identities before UART effects. Terminal task
; states are allowed here because the same validator precedes retirement clear.
native_terminal_validate64:
    lea rdi,[rel native_terminal_state]
    call native_terminal_shape64
    test eax,eax
    jz .bad
    mov rax,[rdi]
    test rax,rax
    jz .good
    cmp [rel family_records],rax
    jne .bad
    cmp qword [rel family_records+40],1
    jne .bad
    mov rdx,rax
    shr rdx,32
    cmp [rel scheduler_tasks+TASK_GENERATION],rdx
    jne .bad
    mov rsi,[rdi+8]
    test rsi,rsi
    jz .good
    mov ecx,esi
    shl ecx,6
    lea r8,[rel family_records]
    add r8,rcx
    cmp [r8],rsi
    jne .bad
    cmp [r8+8],rax
    jne .bad
    cmp qword [r8+40],2
    jne .bad
    mov ecx,esi
    shl ecx,NATIVE_TASK_SHIFT
    lea r8,[rel scheduler_tasks]
    mov rdx,rsi
    shr rdx,32
    cmp [r8+rcx+TASK_GENERATION],rdx
    jne .bad
    mov ecx,esi
    shl ecx,5
    lea r8,[rel family_profiles]
    cmp [r8+rcx],rdx
    jne .bad
    mov rax,[r8+rcx+8]
    and eax,(1<<15)|(1<<20)
    cmp eax,(1<<15)|(1<<20)
    jne .bad
    mov rax,1<<63
    cmp [r8+rcx+16],rax
    jne .bad
    cmp qword [r8+rcx+24],0
    jne .bad
.good: mov eax,1
    ret
.bad: xor eax,eax
    ret

; Bounded ownership-transition RX discard, no TX write/setup or wait.
native_terminal_drain64:
    mov ecx,64
.next:
    mov dx,COM1_LSR
    in al,dx
    test al,0x1e
    jnz .fenced
    test al,1
    jz .empty
    test ecx,ecx
    jz .fenced
    mov dx,COM1_DATA
    in al,dx
    dec ecx
    jmp .next
.empty: xor eax,eax
    ret
.fenced:
    mov qword [rel native_terminal_state+16],1
    mov rax,-5
    ret

native_terminal_io_admit64:
    call native_terminal_validate64
    test eax,eax
    jz scheduler_fail
    mov esi,[rel scheduler_current_slot]
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    or rsi,rax
    mov edx,[rel syscall_rax]
    lea rdi,[rel native_terminal_state]
    call native_terminal_io64
    cmp rax,-117
    je scheduler_fail
    ret

native_terminal_syscall64:
    mov rax,[rel syscall_rsi]
    or rax,[rel syscall_rdx]
    or rax,[rel syscall_r10]
    or rax,[rel syscall_r8]
    or rax,[rel syscall_r9]
    jnz .invalid
    mov rax,[rel syscall_rdi]
    mov edx,24
    mov ecx,PF_R
    call scheduler_validate_shell_range64
    cmp eax,1
    jne .pointer
    call native_terminal_validate64
    test eax,eax
    jz scheduler_fail
    sub rsp,128
    mov rsi,[rel syscall_rdi]
    mov rax,[rsi]
    mov [rsp],rax
    mov rax,[rsi+8]
    mov [rsp+8],rax
    mov rax,[rsi+16]
    mov [rsp+16],rax
    mov edi,[rel scheduler_current_slot]
    call family_record64
    mov rax,[r10]
    mov [rsp+32],rax
    mov rax,[r10+8]
    mov [rsp+40],rax
    mov rax,[rel family_records]
    mov [rsp+48],rax
    mov qword [rsp+56],0
    mov qword [rsp+64],0
    mov qword [rsp+72],0
    mov qword [rsp+80],0
    mov eax,edi
    shl eax,5
    lea rsi,[rel family_profiles]
    mov rdx,[rsi+rax+8]
    mov [rsp+88],rdx
    mov rdx,[rsi+rax+16]
    mov [rsp+96],rdx
    cmp dword [rsp+8],2
    jne .plan
    xor ecx,ecx
    lea r8,[rel scheduler_tasks]
    lea r9,[rel family_records]
    lea r10,[rel family_profiles]
.find:
    mov eax,[rsp+16]
    cmp [r8+TASK_GENERATION],rax
    jne .next
    cmp qword [r8+TASK_STATE],TASK_READY
    je .found
    cmp qword [r8+TASK_STATE],TASK_RUNNING
    je .found
    cmp qword [r8+TASK_STATE],TASK_BLOCKED
    jne .next
.found:
    mov rax,[r9]
    mov [rsp+56],rax
    mov rax,[r9+8]
    mov [rsp+64],rax
    mov rax,[r10+8]
    mov [rsp+72],rax
    mov rax,[r10+16]
    mov [rsp+80],rax
    jmp .plan
.next:
    add r8,1<<NATIVE_TASK_SHIFT
    add r9,64
    add r10,32
    inc ecx
    cmp ecx,NATIVE_POOL_TASKS
    jb .find
.plan:
    lea rdi,[rel native_terminal_state]
    lea rsi,[rsp+32]
    mov rdx,rsp
    lea rcx,[rsp+104]
    call native_terminal_plan64
    cmp rax,-117
    je scheduler_fail
    test rax,rax
    jnz .result
    mov r13,[rsp+104]
    cmp [rel native_terminal_state+8],r13
    je .result
    call native_terminal_drain64
    test rax,rax
    jnz .result
    mov [rel native_terminal_state+8],r13
.result:
    add rsp,128
    jmp process_run_resume64
.invalid: mov rax,-22
    jmp process_run_resume64
.pointer: mov rax,-14
    jmp process_run_resume64

; All caller registers survive, including the terminal-state/receipt inputs.
native_terminal_retire_hook64:
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    call native_terminal_validate64
    test eax,eax
    jz scheduler_fail
    mov esi,[rel scheduler_current_slot]
    mov rax,[r12+TASK_GENERATION]
    shl rax,32
    or rsi,rax
    lea rdi,[rel native_terminal_state]
    call native_terminal_retire64
    cmp rax,-117
    je scheduler_fail
    test eax,eax
    jz .done
    call native_terminal_drain64
.done:
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    ret
