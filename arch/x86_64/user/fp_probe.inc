; Test-fixture-only FP witnesses. Never a production application binding.
%macro FP_BEGIN 1
    mov [abs fp_saved_rdi], rdi
    mov edi, %1
    mov qword [abs fp_return], %%resume
    jmp fp_probe_begin
%%resume:
%endmacro
%macro FP_CHECK 0
    mov [abs fp_saved_rdi], rdi
    mov qword [abs fp_return], %%resume
    jmp fp_probe_check
%%resume:
%endmacro
%macro FP_PROBE_CODE 0
section .text
DEFAULT ABS ; fixed ET_EXEC fixture addresses, including the child's stack area
fp_probe_begin:
    mov [fp_saved_rax], rax
    mov [fp_saved_rcx], rcx
    mov [fp_saved_rdx], rdx
    mov [fp_saved_rsi], rsi
    fxsave64 [fp_observed]
    cmp word [fp_observed], 0x037f
    jne fp_probe_bad
    cmp byte [fp_observed+4], 0
    jne fp_probe_bad
    cmp dword [fp_observed+24], 0x1f80
    jne fp_probe_bad
    ; Every architectural payload byte must be clean on each new generation.
    lea rsi, [fp_observed]
    xor ecx, ecx
%%fresh_st:
    cmp qword [rsi+rcx+32], 0
    jne fp_probe_bad
    cmp word [rsi+rcx+40], 0
    jne fp_probe_bad
    add ecx, 16
    cmp ecx, 128
    jb %%fresh_st
    mov ecx, 160
%%fresh_xmm:
    cmp qword [rsi+rcx], 0
    jne fp_probe_bad
    add ecx, 8
    cmp ecx, 416
    jb %%fresh_xmm
    mov edx, edi
    lea rdi, [fp_expected]
    xor eax, eax
    mov ecx, 64
    cld
    rep stosq
    lea rdi, [fp_expected]
    mov eax, edx
    and eax, 3
    shl eax, 10
    or eax, 0x037f
    mov [rdi], ax
    mov eax, edx
    and eax, 3
    shl eax, 13
    or eax, 0x1f80
    mov [rdi+24], eax
    mov byte [rdi+4], 0xff
    xor ecx, ecx
%%st:
    mov rax, 0x8000000000000000
    or rax, rdx
    or rax, rcx
    mov [rdi+rcx+32], rax
    mov word [rdi+rcx+40], 0x3fff
    add ecx, 16
    cmp ecx, 128
    jb %%st
    mov ecx, 160
%%xmm:
    mov rax, 0x0123456700000000
    or rax, rdx
    mov [rdi+rcx], rax
    add rdx, 0x100
    add ecx, 8
    cmp ecx, 416
    jb %%xmm
    fxrstor64 [rdi]
    jmp fp_probe_return
fp_probe_check:
    mov [fp_saved_rax], rax
    mov [fp_saved_rcx], rcx
    mov [fp_saved_rdx], rdx
    mov [fp_saved_rsi], rsi
    fxsave64 [fp_observed]
    lea rsi, [fp_observed]
    lea rdi, [fp_expected]
    mov eax, [rdi]
    cmp [rsi], eax
    jne fp_probe_bad
    mov al, [rdi+4]
    cmp [rsi+4], al
    jne fp_probe_bad
    mov eax, [rdi+24]
    cmp [rsi+24], eax
    jne fp_probe_bad
    xor ecx, ecx
%%check_st:
    mov rax, [rdi+rcx+32]
    cmp [rsi+rcx+32], rax
    jne fp_probe_bad
    mov ax, [rdi+rcx+40]
    cmp [rsi+rcx+40], ax
    jne fp_probe_bad
    add ecx, 16
    cmp ecx, 128
    jb %%check_st
    mov ecx, 160
%%check_xmm:
    mov rax, [rdi+rcx]
    cmp [rsi+rcx], rax
    jne fp_probe_bad
    add ecx, 8
    cmp ecx, 416
    jb %%check_xmm
fp_probe_return:
    mov rdi, [fp_saved_rdi]
    mov rsi, [fp_saved_rsi]
    mov rdx, [fp_saved_rdx]
    mov rcx, [fp_saved_rcx]
    mov rax, [fp_saved_rax]
    jmp [fp_return]
fp_probe_bad:
    int3
    ud2
%ifdef FP_STACK_BASE
fp_expected equ FP_STACK_BASE
fp_observed equ FP_STACK_BASE + 512
fp_saved_rax equ FP_STACK_BASE + 1024
fp_saved_rcx equ FP_STACK_BASE + 1032
fp_saved_rdx equ FP_STACK_BASE + 1040
fp_saved_rsi equ FP_STACK_BASE + 1048
fp_saved_rdi equ FP_STACK_BASE + 1056
fp_return equ FP_STACK_BASE + 1064
%else
section .bss
alignb 16
fp_expected: resb 512
fp_observed: resb 512
fp_saved_rax: resq 1
fp_saved_rcx: resq 1
fp_saved_rdx: resq 1
fp_saved_rsi: resq 1
fp_saved_rdi: resq 1
fp_return: resq 1
%endif
%endmacro
