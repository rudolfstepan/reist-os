; Private compile-time layouts. Old profiles remain byte-for-byte layouts.
%ifndef REIST_NATIVE_LAYOUT_INC
%define REIST_NATIVE_LAYOUT_INC 1
; Physical backing differs only in the explicit new profile. Legacy active
; pools remain four; native run-v4 separately admits all eight owners.
%ifdef REIST_NATIVE_TASK_POOL
%define NATIVE_POOL_TASKS 8
%ifdef REIST_NATIVE_SERVICE_CPU
%define NATIVE_POOL_RUN_VERSION 5
%define NATIVE_POOL_RUN_BYTES 336
%else
%define NATIVE_POOL_RUN_VERSION 4
%define NATIVE_POOL_RUN_BYTES 272
%endif
%else
%define NATIVE_POOL_TASKS 4
%define NATIVE_POOL_RUN_VERSION 3
%define NATIVE_POOL_RUN_BYTES 144
%endif
; ZF-only plan membership test; no register clobber. Selected v6 shares
; lifecycle/cleanup with v5. Disabled expansion is the original comparison.
%macro NATIVE_POOL_PLAN_CMP 1
%ifdef REIST_NATIVE_DESKTOP_CPU
    cmp %1,6
    je %%done
%endif
    cmp %1,NATIVE_POOL_RUN_VERSION
%ifdef REIST_NATIVE_DESKTOP_CPU
%%done:
%endif
%endmacro
%define NATIVE_POOL_MASK ((1 << NATIVE_POOL_TASKS)-1)
%define NATIVE_POOL_CHILD_MASK (NATIVE_POOL_MASK & ~3)
%ifdef REIST_NATIVE_SERVICE_CPU
%define NATIVE_FAMILY_REQUEST_BYTES 80
%else
%define NATIVE_FAMILY_REQUEST_BYTES 64
%endif
; Compare without clobbering registers. Only admitted native run-v4 activates
; the larger pool; all legacy bootstrap modes retain four active entries.
%macro NATIVE_ACTIVE_CMP 1
%ifdef REIST_NATIVE_TASK_POOL
    cmp byte [rel scheduler_mode],SCHEDULER_MODE_PROCESS
    jne %%legacy
    cmp %1,NATIVE_POOL_TASKS
    jmp %%done
%%legacy:
    cmp %1,4
%%done:
%else
    cmp %1,4
%endif
%endmacro
%ifdef REIST_NATIVE_LARGE_IMAGE
%ifndef REIST_NATIVE_WIDE
%error NativeLargeImage requires NativeWide
%endif
%define NATIVE_IMAGE_PAGES 256
%define NATIVE_IMAGE_VECTOR_SHIFT 11
%define NATIVE_TASK_SHIFT 12
%define NATIVE_IMPORT_BYTES 1052960
%elifdef REIST_NATIVE_WIDE
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
%define NATIVE_PREPARED_V3_BYTES 1052960
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

%ifdef REIST_NATIVE_DESKTOP_CPU
%if REIST_NATIVE_DESKTOP_CPU != 1
%error NativeDesktopCPU must be an explicit enabled selector
%endif
%ifndef REIST_NATIVE_LARGE_PERIODIC
%error NativeDesktopCPU requires NativeLargePeriodic
%endif
%endif
