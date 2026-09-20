; Same real terminal/exit/fault behavior, now a multi-page ELF read from media.
%include "arch/x86_64/user/shell_session_program.asm"
section .rodata
align 16
times 16384 db 0x5a
section .data
dq 0x32505247464c4957
