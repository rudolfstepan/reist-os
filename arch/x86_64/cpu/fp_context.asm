; Fixed-size eager legacy FP context mechanism. Kernel-owned pointers only.
; Intel FXSAVE64 format: x87/MMX and XMM0..15, no AVX/XSAVE admission.
BITS 64
section .text
global x86_64_fp_clear64
global x86_64_fp_init64
global x86_64_fp_save64
global x86_64_fp_restore64

; RDI points to an aligned private 512-byte area. Preserve every GPR.
x86_64_fp_clear64:
    push rax
    push rcx
    push rdi
    xor eax, eax
    mov ecx, 64
    cld
    rep stosq
    pop rdi
    pop rcx
    pop rax
    ret
x86_64_fp_init64:
    call x86_64_fp_clear64
    mov word [rdi], 0x037f
    mov dword [rdi + 24], 0x1f80
    ret
x86_64_fp_save64:
    fxsave64 [rdi]
    ret
x86_64_fp_restore64:
    fxrstor64 [rdi]
    ret

%ifndef FP_HOST_TEST
global x86_64_fp_cpu_init64
global x86_64_fp_reset64
x86_64_fp_cpu_init64:
    push rbx
    mov eax, 1
    cpuid
    and edx, 0x07000001 ; FPU/FXSR/SSE/SSE2
    cmp edx, 0x07000001
    jne .unsupported
    mov rax, cr4
    test eax, (1 << 18) ; do not silently discard existing XSAVE state
    jnz .unsupported
    or eax, 0x600
    mov cr4, rax
    mov rax, cr0
    and rax, ~0x0c ; EM/TS off
    or rax, 0x22   ; MP/NE on
    mov cr0, rax
    mov rax, cr0
    and eax, 0x2e
    cmp eax, 0x22
    jne .unsupported
    mov rax, cr4
    and eax, 0x40600
    cmp eax, 0x600
    jne .unsupported
    lea rdi, [rel fp_clean_state]
    call x86_64_fp_init64
    call x86_64_fp_restore64
    mov eax, 1
    pop rbx
    ret
.unsupported:
    xor eax, eax
    pop rbx
    ret
x86_64_fp_reset64:
    push rdi
    lea rdi, [rel fp_clean_state]
    call x86_64_fp_restore64
    pop rdi
    ret
section .bss
alignb 16
fp_clean_state: resb 512
%endif
