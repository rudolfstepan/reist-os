; Qualification-only CPU trace-v1. Private LE192 records, no public ABI.
; Fixed256-entry ring /2048 lifetime charges, single IRQ-disabled producer.
; Records are observational: error/overflow never changes accounting/recovery.
; No consumer acknowledgement, allocation, wait, output or metadata repair.
%if REIST_NATIVE_CPU_TRACE != 1
%error "CPU trace must be explicitly enabled"
%endif
%ifndef REIST_NATIVE_SERVICE_CPU
%error "CPU trace requires periodic service accounting"
%endif
%ifdef REIST_NATIVE_DEVICE_FREE_CPU_TRACE
%if REIST_NATIVE_DEVICE_FREE_CPU_TRACE != 1
%error "Device-free CPU trace must be explicitly enabled"
%endif
%ifdef REIST_NATIVE_POOL_PIO
%error "Device-free CPU trace excludes PIO authority"
%endif
%else
%ifndef REIST_NATIVE_POOL_PIO
%error "CPU trace requires an explicit qualification profile"
%endif
%endif
%macro cpu_trace_save 0
    pushfq
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    cld
%endmacro
%macro cpu_trace_restore 0
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    popfq
    ret
%endmacro
section .text
native_cpu_trace_before64:
    cpu_trace_save
    cmp byte [rel scheduler_mode],8
    jne .error
    cmp edx,2
    jne .error
    cmp qword [rel native_cpu_trace+8],0
    jne .done
    cmp qword [rel native_cpu_trace+16],0
    jne .error
    cmp qword [rel native_cpu_trace+24],0
    jne .error
    mov r10,[rel native_cpu_trace]
%ifdef REIST_NATIVE_WIDE_FILE
    cmp r10,262144
%else
    cmp r10,2048
%endif
    jae .error
    lea r11,[rel scheduler_cpu_budgets]
    mov r8,rdi
    sub r8,r11
    cmp r8,256
    jae .error
    test r8b,31
    jnz .error
    lea r11,[rel scheduler_cpu_windows]
    add r11,r8
    cmp rsi,r11
    jne .error
    shr r8d,5
    cmp r8d,[rel scheduler_current_slot]
    jne .error
    lea r11,[rel native_cpu_trace_pending]
    mov qword [rel native_cpu_trace+16],1
    mov dword [r11],1
    mov dword [r11+4],1
    inc r10d
    mov [r11+8],r10d
    mov [r11+12],r8d
    imul r8,TASK_RECORD_SIZE
    lea r10,[rel scheduler_tasks]
    mov r8,[r10+r8+8]
    mov [r11+16],r8
    mov [r11+24],r9
    mov qword [r11+32],0
    mov r10,[rsp+72]
    mov [r11+168],r10
    mov qword [r11+176],0
    mov qword [r11+184],8
    mov r10,rsi
    mov rsi,rdi
    lea rdi,[r11+40]
    mov ecx,4
    rep movsq
    mov rsi,r10
    mov ecx,4
    rep movsq
    jmp .done
.error:
    mov qword [rel native_cpu_trace+8],1
.done:
    cpu_trace_restore

native_cpu_trace_after64:
    cpu_trace_save
    cmp qword [rel native_cpu_trace+8],0
    jne .done
    cmp qword [rel native_cpu_trace+16],1
    jne .error
    cmp qword [rel native_cpu_trace+24],0
    jne .error
    mov r10,[rel native_cpu_trace]
%ifdef REIST_NATIVE_WIDE_FILE
    cmp r10,262144
%else
    cmp r10,2048
%endif
    jae .error
    lea r11,[rel native_cpu_trace_pending]
    mov r8d,[r11+12]
    cmp r8d,8
    jae .error
    cmp r8d,[rel scheduler_current_slot]
    jne .error
    mov r9,r10
    inc r9d
    cmp [r11+8],r9d
    jne .error
    mov rax,[rsp+64]
    mov [r11+32],rax
    mov rax,[rsp+72]
    mov [r11+176],rax
    shl r8d,5
    lea rsi,[rel scheduler_cpu_budgets]
    add rsi,r8
    lea rdi,[r11+104]
    mov ecx,4
    rep movsq
    lea rsi,[rel scheduler_cpu_windows]
    add rsi,r8
    mov ecx,4
    rep movsq
    mov eax,r10d
    and eax,255
    imul eax,192
    lea rdi,[rel native_cpu_trace+32]
    add rdi,rax
    mov rsi,r11
    mov ecx,24
    rep movsq
    mov qword [rel native_cpu_trace+16],0
    inc r10
    mov [rel native_cpu_trace],r10 ; commit complete record last
    test r10d,255
    jnz .done
.full:
    nop ; optional debugger drain, no guest trap or consumer wait
    jmp .done
.error:
    mov qword [rel native_cpu_trace+8],1
.done:
    cpu_trace_restore
%unmacro cpu_trace_save 0
%unmacro cpu_trace_restore 0

; Outside scheduler_state_begin/end: never reset a live observation sequence.
section .bss
alignb 16
global native_cpu_trace,native_cpu_trace_end
native_cpu_trace: resq 4
    resb 256*192
native_cpu_trace_pending: resb 192
native_cpu_trace_end:
section .text
