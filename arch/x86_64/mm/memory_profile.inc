; Private physical-address profile shared by all current native consumers.
%ifndef REIST_NATIVE_MEMORY_PROFILE
%define REIST_NATIVE_MEMORY_PROFILE 1
%ifndef X86_64_NATIVE_RAM
%define X86_64_NATIVE_RAM 0
%endif
%if X86_64_NATIVE_RAM
%define MEMORY_LIMIT_VALUE 0x400000000
%define MEMORY_FRAME_CAPACITY 0x400000
%define MEMORY_PTE_FRAME_MASK 0x3fffff000
section .rodata
align 8
native_profile_limit: dq MEMORY_LIMIT_VALUE
native_profile_mask: dq MEMORY_PTE_FRAME_MASK
section .text
%macro MEMORY_COMPARE_LIMIT 1
    cmp %1, [rel native_profile_limit]
%endmacro
%macro MEMORY_MASK_FRAME 1
    and %1, [rel native_profile_mask]
%endmacro
%else
%define MEMORY_LIMIT_VALUE 0x08000000
%define MEMORY_FRAME_CAPACITY 32768
%define MEMORY_PTE_FRAME_MASK 0x07fff000
%macro MEMORY_COMPARE_LIMIT 1
    cmp %1, 0x08000000
%endmacro
%macro MEMORY_MASK_FRAME 1
    and %1, 0x07fff000
%endmacro
%endif
%endif
