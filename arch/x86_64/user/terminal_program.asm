; Compact System V ELF64 qualification child. No file-format/quota change.
BITS 64
SYS_GETPID equ 22
SYS_SLEEP_MS equ 41
SYS_SEND_TIMEOUT equ 53
SYS_RECEIVE_TIMEOUT equ 54
SYS_TERMINAL_INPUT equ 127
%macro NUMBER 1
    push byte %1
    pop rax
%endmacro
section .text
global main
main:
    push rbx
    push r12
    push r13
    push r15
    sub rsp,184
    mov eax,200
    cmp edi,3
    jne .return
    cmp qword [rsi+24],0
    jne .return
    cmp qword [rdx],0
    jne .return
    mov rdx,[rsi]
    mov rax,0x72702e746f6f622f
    cmp [rdx],rax
    jne .invalid_start
    cmp word [rdx+8],0x0067
    jne .invalid_start
    mov rdx,[rsi+8]
    xor ebx,ebx
    xor ecx,ecx
.hex:
    movzx eax,byte [rdx+rcx]
    sub eax,'0'
    cmp eax,9
    jbe .digit
    sub eax,'a'-'0'
    cmp eax,5
    ja .invalid_start
    add eax,10
.digit:
    shl ebx,4
    or ebx,eax
    inc ecx
    cmp ecx,8
    jb .hex
    test ebx,ebx
    jz .invalid_start
    cmp byte [rdx+8],0
    jne .invalid_start
    mov rdx,[rsi+16]
    movzx r13d,byte [rdx]
    sub r13d,'0'
    cmp r13d,3
    ja .invalid_start
    cmp byte [rdx+1],0
    jne .invalid_start
    jmp .startup_valid
.invalid_start:
    jmp .bad
.startup_valid:
    ; No device, child-management or IO before actual foreground grant.
    xor r15d,r15d
.denials:
    lea rax,[rel .calls]
    movzx eax,byte [rax+r15]
    xor edi,edi
    test r15d,r15d
    jnz .not_device
    mov edi,29
.not_device:
    cmp r15d,3
    jne .deny_call
    mov edi,1
.deny_call:
    call .zero_call
    cmp rax,-13
    jne .bad
    inc r15d
    cmp r15d,4
    jb .denials
    NUMBER SYS_GETPID
    xor edi,edi
    call .zero_call
    mov r12,rax
    mov rdi,rsp
    xor eax,eax
    mov ecx,23
    rep stosq
    mov rax,0x8c00000001
    mov [rsp],rax
    mov dword [rsp+8],16
    mov [rsp+12],r12
    mov rax,0x214f523436464c45
    mov [rsp+20],rax
    mov r15d,20
.send:
    NUMBER SYS_SEND_TIMEOUT
    mov edi,ebx
    mov rsi,rsp
    mov edx,1000
    call .call
    cmp rax,-9
    jne .sent
    NUMBER SYS_SLEEP_MS
    mov edi,10
    call .zero_call
    test rax,rax
    jnz .bad
    dec r15d
    jnz .send
    jmp .bad
.sent:
    test rax,rax
    jnz .bad
    mov rdi,rsp
    xor eax,eax
    mov ecx,18
    rep stosq
    mov rax,0x8c00000001
    mov [rsp],rax
    mov dword [rsp+8],128
    NUMBER SYS_RECEIVE_TIMEOUT
    mov edi,ebx
    mov rsi,rsp
    mov edx,1000
    call .call
    test rax,rax
    jnz .bad
    mov rax,0x8c00000001
    cmp [rsp],rax
    jne .bad
    cmp dword [rsp+8],16
    jne .bad
    cmp [rsp+12],r12
    jne .bad
    mov rax,0x4f4734364556494c
    cmp [rsp+20],rax
    jne .bad
    mov ecx,14
    lea rdx,[rsp+28]
.padding:
    cmp qword [rdx],0
    jne .bad
    add rdx,8
    loop .padding
    mov rax,0x1800000001
    mov [rsp+152],rax
    mov edi,5
    call .terminal
    test rax,rax
    jnz .bad
    mov byte [rsp+144],'T'
    mov byte [rsp+145],0xa5
    NUMBER 15
    xor edi,edi
    lea rsi,[rsp+145]
    mov edx,1
    call .call
    cmp rax,-11
    jne .bad
    cmp byte [rsp+145],0xa5
    jne .bad
    mov r15d,10
.write:
    NUMBER 20
    mov edi,1
    lea rsi,[rsp+144]
    mov edx,1
    call .call
    cmp rax,1
    je .written
    cmp rax,-11
    jne .bad
    NUMBER SYS_SLEEP_MS
    mov edi,10
    call .zero_call
    test rax,rax
    jnz .bad
    dec r15d
    jnz .write
    jmp .bad
.written:
    cmp r13d,1
    jne .not_fault
    ud2
.not_fault:
    cmp r13d,2
    jne .not_spin
.spin:
    pause
    jmp .spin
.not_spin:
    cmp r13d,3
    jne .release
    mov r15d,20
.sleep:
    NUMBER SYS_SLEEP_MS
    mov edi,100
    call .zero_call
    test rax,rax
    jnz .bad
    dec r15d
    jnz .sleep
.release:
    mov edi,3
    call .terminal
    test rax,rax
    jnz .bad
    mov edi,3
    call .terminal
    test rax,rax
    jnz .bad
    mov edi,5
    call .terminal
    cmp rax,-11
    jne .bad
    NUMBER 15
    xor edi,edi
    call .zero_call
    cmp rax,-13
    jne .bad
    NUMBER 20
    mov edi,1
    call .zero_call
    cmp rax,-13
    jne .bad
    NUMBER 82
    jmp .return
.bad:
    mov eax,204
.return:
    add rsp,184
    pop r15
    pop r13
    pop r12
    pop rbx
    ret
.terminal:
    mov [rsp+168],edi ; caller request at caller RSP+152; return address adds8
    lea rdi,[rsp+160]
    NUMBER SYS_TERMINAL_INPUT
.zero_call:
    xor esi,esi
    xor edx,edx
.call:
    xor r10d,r10d
    xor r8d,r8d
    xor r9d,r9d
    syscall
    ret
.calls: db 113,132,15,20
section .note.GNU-stack noalloc noexec nowrite progbits
