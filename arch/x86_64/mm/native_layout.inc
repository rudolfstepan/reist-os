; Private compile-time layouts. Old profiles remain byte-for-byte layouts.
%ifndef REIST_NATIVE_LAYOUT_INC
%define REIST_NATIVE_LAYOUT_INC 1
%ifdef REIST_NATIVE_WIDE
%define NATIVE_IMAGE_PAGES 64
%define NATIVE_IMAGE_VECTOR_SHIFT 9
%define NATIVE_TASK_SHIFT 10
%define NATIVE_IMPORT_BYTES 266336
%else
%define NATIVE_IMAGE_PAGES 8
%define NATIVE_IMAGE_VECTOR_SHIFT 6
%define NATIVE_TASK_SHIFT 8
%define NATIVE_IMPORT_BYTES 36896
%endif
%define NATIVE_TASK_BYTES (1 << NATIVE_TASK_SHIFT)
%define NATIVE_REG_DELTA ((NATIVE_IMAGE_PAGES-8)*8)
%define NATIVE_IMAGE_FLAGS (NATIVE_IMAGE_PAGES*8)
%define NATIVE_IMAGE_DIAG (NATIVE_IMAGE_PAGES*9)
%define NATIVE_IMAGE_RECORD (NATIVE_IMAGE_DIAG+16)
%define NATIVE_CLAIM_FRAMES (NATIVE_IMAGE_PAGES+5)
%define NATIVE_CLAIM_BYTES (NATIVE_CLAIM_FRAMES*8+16)
%define NATIVE_PLAN_FLAGS (32+NATIVE_IMAGE_PAGES*8)
%define NATIVE_PLAN_PRIVATE (32+NATIVE_IMAGE_PAGES*9)
%define NATIVE_PLAN_STACK (32+NATIVE_IMAGE_PAGES*17)
%define NATIVE_PLAN_KERNEL (NATIVE_PLAN_STACK+8)
%define NATIVE_PLAN_BYTES (NATIVE_PLAN_KERNEL+16)
%define NATIVE_PLAN_FRAMES (NATIVE_IMAGE_PAGES*2+5)
%define NATIVE_PREPARED_V2_BYTES 266336
; Exact per-task comparison. POP preserves comparison flags and all registers.
%macro NATIVE_STACK_CMP_RAX 0
%ifdef REIST_NATIVE_WIDE
    push rax
    call scheduler_stack_top64
    test rax,rax
    jnz %%valid
    pop rax
    jmp scheduler_fail
%%valid:
    cmp [rsp],rax
    pop rax
%else
    cmp rax,USER_STACK_TOP
%endif
%endmacro
%endif
