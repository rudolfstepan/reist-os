; Compatible v2 specialization of the same independent-pair lifecycle fixture.
; Only user ELF differs. Both send and receive cross a real private page edge.
%define IPC_DEMO_BULK 1
%include "arch/x86_64/user/ipc_demo.inc"

bulk_demo_prepare:
    cmp rsi, rbx
    jne .done
    cmp eax, 51
    je .receive
    cmp eax, 54
    je .receive
    cmp eax, 50
    je .send
    cmp eax, 53
    jne .done
.send:
    test r12b, 1
    jnz .small
    push rax
    movzx eax, byte [rbx+12]
    xor ecx, ecx
.fill:
    mov [rbx+rcx+12], al
    add al, 17
    inc ecx
    cmp ecx, 2048
    jb .fill
    pop rax
.receive:
    mov dword [rbx], 2
    mov dword [rbx+4], 2060
    mov dword [rbx+8], 2048
    jmp .done
.small:
    mov dword [rbx], 1
    mov dword [rbx+4], 140
    mov dword [rbx+8], 4
.done:
    ret

bulk_demo_negative:
    ; Complete readable header at the last12 bytes of the last image page.
    ; Header errors precede range errors; the following page is unmapped.
    xor edi, edi
    xor edx, edx
    mov esi, 0x403ff4
    mov dword [rsi], 3
    mov dword [rsi+4], 2060
    mov dword [rsi+8], 2048
    mov eax, 53
    call ipc_demo_call
    cmp rax, -22
    jne ipc_demo_bad
    mov dword [rsi], 2
    mov eax, 53
    call ipc_demo_call
    cmp rax, -14
    jne ipc_demo_bad
    mov eax, 54
    call ipc_demo_call
    cmp rax, -14
    jne ipc_demo_bad
    ret

section .bss
alignb 4096
    resb 3072
bulk_demo_buffer: resb 2060
section .text
