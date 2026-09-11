BITS 64
section .text
extern x86_64_fp_init64
extern x86_64_fp_clear64
extern x86_64_fp_save64
extern x86_64_fp_restore64
global fp_witness
; Windows entry; preserve all host FP state and nonvolatile GPRs, even on failure.
fp_witness:
    push rdi
    push rsi
    push rbx
    push r12
    push r13
    lea rdi, [rel host_state]
    call x86_64_fp_save64
    lea rdi, [rel state_a]
    call x86_64_fp_init64
    call x86_64_fp_restore64
    lea rdi, [rel snapshot]
    call x86_64_fp_save64
    mov ebx, 1
    cmp word [rdi], 0x037f
    jne .done
    cmp byte [rdi+4], 0
    jne .done
    cmp dword [rdi+24], 0x1f80
    jne .done
    lea rsi, [rel state_a]
    call compare_payload
    test eax, eax
    jz .done
    lea rdi, [rel state_b]
    call x86_64_fp_init64
    lea rdi, [rel state_a]
    mov rdx, 0x8123456789abcdef
    call fill_pattern
    mov word [rdi], 0x077f
    mov dword [rdi+24], 0x3f80
    lea rdi, [rel state_b]
    mov rdx, 0xfedcba9876543210
    call fill_pattern
    mov word [rdi], 0x0b7f
    mov dword [rdi+24], 0x5f80
    mov r12d, 64
.switch:
    mov ebx, 2
    lea rdi, [rel state_a]
    call x86_64_fp_restore64
    lea rdi, [rel snapshot]
    call x86_64_fp_save64
    lea rsi, [rel state_a]
    call compare_state
    test eax, eax
    jz .done
    mov ebx, 3
    lea rdi, [rel state_b]
    call x86_64_fp_restore64
    lea rdi, [rel snapshot]
    call x86_64_fp_save64
    lea rsi, [rel state_b]
    call compare_state
    test eax, eax
    jz .done
    dec r12d
    jnz .switch
    mov ebx, 4
    lea rdi, [rel state_a]
    call x86_64_fp_clear64
    xor ecx, ecx
.scrub:
    cmp qword [rdi+rcx*8], 0
    jne .done
    inc ecx
    cmp ecx, 64
    jb .scrub
    call x86_64_fp_init64
    call x86_64_fp_restore64
    lea rdi, [rel snapshot]
    call x86_64_fp_save64
    lea rsi, [rel state_a]
    call compare_state
    test eax, eax
    jz .done
    xor ebx, ebx
.done:
    lea rdi, [rel host_state]
    call x86_64_fp_restore64
    mov eax, ebx
    pop r13
    pop r12
    pop rbx
    pop rsi
    pop rdi
    ret

fill_pattern:
    mov byte [rdi+4], 0xff
    xor ecx, ecx
.st:
    mov rax, 0x8000000000000000
    or rax, rcx
    mov [rdi+rcx+32], rax
    mov word [rdi+rcx+40], 0x3fff
    add ecx, 16
    cmp ecx, 128
    jb .st
    xor ecx, ecx
.xmm:
    mov [rdi+rcx+160], rdx
    inc rdx
    add ecx, 8
    cmp ecx, 256
    jb .xmm
    ret
compare_state:
    mov eax, [rsi]
    cmp [rdi], eax
    jne .bad
    mov al, [rsi+4]
    cmp [rdi+4], al
    jne .bad
    mov eax, [rsi+24]
    cmp [rdi+24], eax
    jne .bad
    jmp compare_payload
.bad:
    xor eax, eax
    ret
compare_payload:
    xor ecx, ecx
.st:
    mov rax, [rsi+rcx+32]
    cmp [rdi+rcx+32], rax
    jne .bad
    mov ax, [rsi+rcx+40]
    cmp [rdi+rcx+40], ax
    jne .bad
    add ecx, 16
    cmp ecx, 128
    jb .st
    xor ecx, ecx
.xmm:
    mov rax, [rsi+rcx+160]
    cmp [rdi+rcx+160], rax
    jne .bad
    add ecx, 8
    cmp ecx, 256
    jb .xmm
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret
section .bss
alignb 16
host_state: resb 512
state_a: resb 512
state_b: resb 512
snapshot: resb 512
