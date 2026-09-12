; Bounded Multiboot-v1 physical-memory foundation for the isolated x86_64
; bootstrap. The 32-bit half captures and validates the handoff before paging;
; the 64-bit half provides a fixed single-CPU frame allocator and self-test.

%include "arch/x86_64/mm/memory_profile.inc"
%if X86_64_NATIVE_RAM
%include C_CORE_LAYOUT_PATH
%if C_CORE_LAYOUT_VERSION != 3 || C_NATIVE_MEMORY_ENTRY == 0
%error "native memory requires validated layout3"
%endif
%endif

MULTIBOOT_BOOT_MAGIC equ 0x2BADB002
MULTIBOOT_MMAP_FLAG equ (1 << 6)
MULTIBOOT_MODS_FLAG equ (1 << 3)
MB_INFO_CAPTURE_SIZE equ 116
MB_INFO_FLAGS        equ 0
MB_INFO_MODS_COUNT   equ 20
MB_INFO_MODS_ADDR    equ 24
MB_INFO_MMAP_LENGTH  equ 44
MB_INFO_MMAP_ADDR    equ 48
MMAP_ENTRY_MIN_SIZE equ 20
MMAP_ENTRY_TYPE     equ 20
MAX_MMAP_BYTES      equ 4096
MAX_MMAP_ENTRIES    equ 128
MAX_MODULES         equ 32
MODULE_ENTRY_SIZE   equ 16

FRAME_SIZE          equ 4096
MANAGED_LIMIT       equ MEMORY_LIMIT_VALUE
FRAME_COUNT         equ MEMORY_FRAME_CAPACITY
FRAME_BITMAP_BYTES  equ FRAME_COUNT / 8
HIGH_MEMORY_BASE    equ 0x04000000
HIGH_MEMORY_FRAME   equ HIGH_MEMORY_BASE / FRAME_SIZE
DIRECT_MAP_BASE     equ 0xFFFF800000000000
%if X86_64_NATIVE_RAM
DIRECT_PT_COUNT     equ 512
%else
DIRECT_PT_COUNT     equ 64
%endif
DIRECT_TABLE_COUNT  equ (2 + DIRECT_PT_COUNT)
PAGE_PRESENT_WRITE equ 0x003
PAGE_NX_HIGH        equ 0x80000000

BITS 32

section .text
global x86_64_physical_memory_init32
global x86_64_physical_memory_selftest64
global physical_frame_alloc64
global physical_frame_test_high_window64
global physical_frame_test_window_clear64
global physical_frame_test_window_is_clear64
global physical_frame_free64
global physical_free_frame_count64
extern pml4_table
extern _x86_64_bootstrap_end
extern serial_write64

x86_64_physical_memory_init32:
    cld
    cmp eax, MULTIBOOT_BOOT_MAGIC
    jne physical_memory_fail32
    test ebx, ebx
    jz physical_memory_fail32
    mov edx, ebx
    add edx, MB_INFO_CAPTURE_SIZE
    jc physical_memory_fail32
    mov dword [multiboot_info_address], ebx

    mov ecx, dword [ebx + MB_INFO_FLAGS]
    mov dword [multiboot_flags], ecx
    test ecx, MULTIBOOT_MMAP_FLAG
    jz physical_memory_fail32

    mov eax, dword [ebx + MB_INFO_MMAP_LENGTH]
    test eax, eax
    jz physical_memory_fail32
    cmp eax, MAX_MMAP_BYTES
    ja physical_memory_fail32
    mov esi, dword [ebx + MB_INFO_MMAP_ADDR]
    test esi, esi
    jz physical_memory_fail32
    mov edi, esi
    add edi, eax
    jc physical_memory_fail32
    mov dword [multiboot_mmap_address], esi
    mov dword [multiboot_mmap_length], eax
    mov dword [multiboot_mmap_end], edi

%if X86_64_NATIVE_RAM
    xor eax, eax
    mov edi, native_memory_arena
    mov ecx, (native_memory_arena_end - native_memory_arena) / 4
    rep stosd
%endif
    xor eax, eax
    mov edi, usable_bitmap
    mov ecx, (2 * FRAME_BITMAP_BYTES) / 4
    rep stosd
    mov dword [managed_frame_count], 0
    mov dword [free_frame_count], 0

    call parse_usable_pass32
    jc physical_memory_fail32
    call parse_reserved_pass32
    jc physical_memory_fail32

    ; The entire bootstrap image, including its fixed paging and bitmap state,
    ; must never receive a writable direct-map alias.
    xor eax, eax
    mov edx, _x86_64_bootstrap_end
    call reserve_range32
    jc physical_memory_fail32

    mov eax, dword [multiboot_info_address]
    mov edx, MB_INFO_CAPTURE_SIZE
    call reserve_range32
    jc physical_memory_fail32
    mov eax, dword [multiboot_mmap_address]
    mov edx, dword [multiboot_mmap_length]
    call reserve_range32
    jc physical_memory_fail32

    mov ebx, dword [multiboot_info_address]
    mov eax, dword [multiboot_flags]
    test eax, MULTIBOOT_MODS_FLAG
    jz .modules_done
    mov ecx, dword [ebx + MB_INFO_MODS_COUNT]
    cmp ecx, MAX_MODULES
    ja physical_memory_fail32
    test ecx, ecx
    jz .modules_done
    mov esi, dword [ebx + MB_INFO_MODS_ADDR]
    test esi, esi
    jz physical_memory_fail32
    mov ebp, ecx
    mov eax, ecx
    shl eax, 4
    jc physical_memory_fail32
    mov edx, eax
    mov eax, esi
    call reserve_range32
    jc physical_memory_fail32

.module_loop:
    mov eax, dword [esi]
    mov edx, dword [esi + 4]
    cmp edx, eax
    jb physical_memory_fail32
    sub edx, eax
    call reserve_range32
    jc physical_memory_fail32
    add esi, MODULE_ENTRY_SIZE
    dec ebp
    jnz .module_loop
.modules_done:

    xor ecx, ecx
    xor edx, edx
.count_loop:
    bt dword [usable_bitmap], ecx
    adc edx, 0
    inc ecx
    cmp ecx, FRAME_COUNT
    jb .count_loop
    test edx, edx
    jz physical_memory_fail32
    mov dword [managed_frame_count], edx
    mov dword [free_frame_count], edx

    call build_direct_map32
    jc physical_memory_fail32
    mov eax, 1
    ret

physical_memory_fail32:
    xor eax, eax
    mov edi, usable_bitmap
    mov ecx, (2 * FRAME_BITMAP_BYTES) / 4
    rep stosd
    mov dword [managed_frame_count], 0
    mov dword [free_frame_count], 0
    xor eax, eax
    ret

parse_usable_pass32:
    mov byte [parse_reserved_mode], 0
    jmp parse_memory_map32

parse_reserved_pass32:
    mov byte [parse_reserved_mode], 1

parse_memory_map32:
    mov esi, dword [multiboot_mmap_address]
    mov edi, dword [multiboot_mmap_end]
    xor ebp, ebp
.entry_loop:
    cmp esi, edi
    je .done
    ja .fail
    mov eax, edi
    sub eax, esi
    cmp eax, 4
    jb .fail
    mov edx, dword [esi]
    cmp edx, MMAP_ENTRY_MIN_SIZE
    jb .fail
    add edx, 4
    jc .fail
    cmp edx, eax
    ja .fail
    inc ebp
    cmp ebp, MAX_MMAP_ENTRIES
    ja .fail
    push edx

    mov eax, dword [esi + 4]
    mov edx, dword [esi + 8]
    mov ebx, dword [esi + 12]
    mov ecx, dword [esi + 16]
    add ebx, eax
    adc ecx, edx
    jc .entry_fail

    cmp byte [parse_reserved_mode], 0
    jne .reserved_pass
    cmp dword [esi + MMAP_ENTRY_TYPE], 1
    jne .entry_done
    mov byte [range_set_operation], 1
    call apply_managed_range32
    jmp .entry_done
.reserved_pass:
    cmp dword [esi + MMAP_ENTRY_TYPE], 1
    je .entry_done
    mov byte [range_set_operation], 0
    call apply_managed_range32
.entry_done:
    pop edx
    add esi, edx
    jmp .entry_loop
.entry_fail:
    pop edx
.fail:
    stc
    ret
.done:
    test ebp, ebp
    jz .fail
    clc
    ret

; Input range is [EDX:EAX, ECX:EBX). Only complete frames below 128 MiB can
; affect the bitmap. This routine preserves the parser cursor and entry count.
apply_managed_range32:
    push esi
    push edi
    push ebp
%if X86_64_NATIVE_RAM
    ; Full byte addresses until clamped; frame indices fit32 bits at16GiB.
    cmp edx, 4
    jae .done
    cmp ecx, 4
    jae .native_clamp
    jmp .native_end
.native_clamp:
    mov ecx, 4
    xor ebx, ebx
.native_end:
    cmp edx, ecx
    ja .done
    jb .native_nonempty
    cmp eax, ebx
    jae .done
.native_nonempty:
    cmp byte [range_set_operation], 0
    je .native_reserved
    add eax, FRAME_SIZE - 1
    adc edx, 0
    jmp .native_indices
.native_reserved:
    add ebx, FRAME_SIZE - 1
    adc ecx, 0
.native_indices:
    shrd eax, edx, 12
    shrd ebx, ecx, 12
    cmp eax, ebx
    jae .done
    jmp .frame_loop
%else
    test edx, edx
    jnz .done
    cmp eax, MANAGED_LIMIT
    jae .done
    test ecx, ecx
    jnz .clamp_end
    cmp ebx, MANAGED_LIMIT
    jbe .end_ready
.clamp_end:
    mov ebx, MANAGED_LIMIT
.end_ready:
    cmp eax, ebx
    jae .done
    cmp byte [range_set_operation], 0
    je .reserved_alignment
    add eax, FRAME_SIZE - 1
    jc .done
    and eax, -FRAME_SIZE
    and ebx, -FRAME_SIZE
    jmp .aligned
.reserved_alignment:
    and eax, -FRAME_SIZE
    add ebx, FRAME_SIZE - 1
    jc .reserved_clamp
    and ebx, -FRAME_SIZE
    cmp ebx, MANAGED_LIMIT
    jbe .aligned
.reserved_clamp:
    mov ebx, MANAGED_LIMIT
.aligned:
    cmp eax, ebx
    jae .done
    shr eax, 12
    shr ebx, 12
%endif
.frame_loop:
    cmp byte [range_set_operation], 0
    je .clear_frame
    bts dword [usable_bitmap], eax
    jmp .next_frame
.clear_frame:
    btr dword [usable_bitmap], eax
.next_frame:
    inc eax
    cmp eax, ebx
    jb .frame_loop
.done:
    pop ebp
    pop edi
    pop esi
    ret

; Reserve one 32-bit physical byte range. CF reports wraparound.
reserve_range32:
    mov ebx, eax
    add ebx, edx
    jc .overflow
    xor edx, edx
    xor ecx, ecx
    mov byte [range_set_operation], 0
    call apply_managed_range32
    clc
    ret
.overflow:
    stc
    ret

build_direct_map32:
%if X86_64_NATIVE_RAM
    ; The arena was zeroed before capture. Publish PML4 only after all leaves.
    mov ecx, 16
    mov edi, direct_pdpt
    mov eax, direct_page_directory
.pdpt_loop:
    mov edx, eax
    or edx, PAGE_PRESENT_WRITE
    mov [edi], edx
    mov dword [edi + 4], PAGE_NX_HIGH
    add eax, 4096
    add edi, 8
    loop .pdpt_loop
    xor ebp, ebp
    mov esi, direct_page_tables
.region_loop:
    mov edi, ebp
    shl edi, 6
    add edi, usable_bitmap
    mov ecx, 16
    mov eax, -1
    xor ebx, ebx
.bits:
    and eax, [edi]
    or ebx, [edi]
    add edi, 4
    loop .bits
    test ebx, ebx
    jz .next_region
    cmp eax, -1
    jne .mixed
    mov eax, ebp
    shl eax, 21
    or eax, 0x083
    mov edx, ebp
    shr edx, 11
    or edx, PAGE_NX_HIGH
    jmp .publish_pde
.mixed:
    cmp esi, direct_page_tables + DIRECT_PT_COUNT * 4096
    jae .capacity
    xor ecx, ecx
.leaf:
    mov ebx, ebp
    shl ebx, 9
    add ebx, ecx
    bt dword [usable_bitmap], ebx
    jnc .next_leaf
    mov eax, ebx
    shl eax, 12
    or eax, PAGE_PRESENT_WRITE
    shr ebx, 20
    or ebx, PAGE_NX_HIGH
    mov [esi + ecx * 8], eax
    mov [esi + ecx * 8 + 4], ebx
.next_leaf:
    inc ecx
    cmp ecx, 512
    jb .leaf
    mov eax, esi
    or eax, PAGE_PRESENT_WRITE
    mov edx, PAGE_NX_HIGH
    add esi, 4096
.publish_pde:
    mov [direct_page_directory + ebp * 8], eax
    mov [direct_page_directory + ebp * 8 + 4], edx
.next_region:
    inc ebp
    cmp ebp, 8192
    jb .region_loop
    mov eax, direct_pdpt
    or eax, PAGE_PRESENT_WRITE
    mov [pml4_table + 256 * 8], eax
    mov dword [pml4_table + 256 * 8 + 4], PAGE_NX_HIGH
    clc
    ret
.capacity:
    stc
    ret
%else
    xor eax, eax
    mov edi, direct_pdpt
    mov ecx, (DIRECT_TABLE_COUNT * 4096) / 4
    rep stosd

    mov eax, direct_pdpt
    or eax, PAGE_PRESENT_WRITE
    mov dword [pml4_table + (256 * 8)], eax
    mov dword [pml4_table + (256 * 8) + 4], PAGE_NX_HIGH

    mov eax, direct_page_directory
    or eax, PAGE_PRESENT_WRITE
    mov dword [direct_pdpt], eax
    mov dword [direct_pdpt + 4], PAGE_NX_HIGH

    xor ecx, ecx
    mov esi, direct_page_tables
.directory_loop:
    mov eax, esi
    or eax, PAGE_PRESENT_WRITE
    mov dword [direct_page_directory + ecx * 8], eax
    mov dword [direct_page_directory + ecx * 8 + 4], PAGE_NX_HIGH
    add esi, 4096
    inc ecx
    cmp ecx, DIRECT_PT_COUNT
    jb .directory_loop

    xor eax, eax
.pte_loop:
    bt dword [usable_bitmap], eax
    jnc .next_pte
    mov edx, eax
    shl edx, 12
    or edx, PAGE_PRESENT_WRITE
    mov dword [direct_page_tables + eax * 8], edx
    mov dword [direct_page_tables + eax * 8 + 4], PAGE_NX_HIGH
.next_pte:
    inc eax
    cmp eax, FRAME_COUNT
    jb .pte_loop
    clc
    ret
%endif

BITS 64

x86_64_physical_memory_selftest64:
%if X86_64_NATIVE_RAM
    xor edi, edi
    xor esi, esi
    call native_memory_call64
    cmp eax, 1
    jne .fail
%endif
    mov eax, dword [rel free_frame_count]
    mov dword [rel selftest_initial_free], eax

    call physical_frame_alloc64
    test rax, rax
    jz .fail
    test rax, FRAME_SIZE - 1
    jnz .fail
    MEMORY_COMPARE_LIMIT rax
    jae .fail
    mov qword [rel selftest_frame0], rax

    call physical_frame_alloc64
    test rax, rax
    jz .fail
    test rax, FRAME_SIZE - 1
    jnz .fail
    MEMORY_COMPARE_LIMIT rax
    jae .fail
    mov qword [rel selftest_frame1], rax
    cmp rax, qword [rel selftest_frame0]
    je .fail

    call physical_frame_alloc64
    test rax, rax
    jz .fail
    test rax, FRAME_SIZE - 1
    jnz .fail
    MEMORY_COMPARE_LIMIT rax
    jae .fail
    mov qword [rel selftest_frame2], rax
    cmp rax, qword [rel selftest_frame0]
    je .fail
    cmp rax, qword [rel selftest_frame1]
    je .fail

    mov rdi, qword [rel selftest_frame0]
    mov rax, 0x0123456789ABCDEF
    call verify_direct_frame64
    test eax, eax
    jz .fail
    mov rdi, qword [rel selftest_frame1]
    mov rax, 0xF0E1D2C3B4A59687
    call verify_direct_frame64
    test eax, eax
    jz .fail
    mov rdi, qword [rel selftest_frame2]
    mov rax, 0x55AA55AA33CC33CC
    call verify_direct_frame64
    test eax, eax
    jz .fail

    ; Require one Multiboot-authorized frame from the newly managed half.
    ; The scan and all mutation still use the allocator's fixed bitmap bound.
    call physical_frame_alloc_high_selftest64
    test rax, rax
    jz .fail
    cmp rax, HIGH_MEMORY_BASE
    jb .fail
    MEMORY_COMPARE_LIMIT rax
    jae .fail
    mov qword [rel selftest_high_frame], rax
    mov rdi, rax
    mov rax, 0x1280ABCD55AA33CC
    call verify_direct_frame64
    test eax, eax
    jz .fail
    mov rdi, qword [rel selftest_high_frame]
    call physical_frame_free64
    test eax, eax
    jz .fail
    mov rdi, qword [rel selftest_high_frame]
    call physical_frame_free64
    test eax, eax
    jnz .fail

    mov rdi, qword [rel selftest_frame2]
    call physical_frame_free64
    test eax, eax
    jz .fail
    call physical_frame_alloc64
    cmp rax, qword [rel selftest_frame2]
    jne .fail
    mov qword [rel selftest_reused_frame], rax
    mov rdi, rax
    mov rax, 0xA5A5A5A55A5A5A5A
    call verify_direct_frame64
    test eax, eax
    jz .fail

    mov rdi, qword [rel selftest_reused_frame]
    call physical_frame_free64
    test eax, eax
    jz .fail
    mov rdi, qword [rel selftest_frame1]
    call physical_frame_free64
    test eax, eax
    jz .fail
    mov rdi, qword [rel selftest_frame0]
    call physical_frame_free64
    test eax, eax
    jz .fail

    mov rdi, 1
    call physical_frame_free64
    test eax, eax
    jnz .fail
    mov rdi, qword [rel selftest_frame0]
    call physical_frame_free64
    test eax, eax
    jnz .fail

    mov eax, dword [rel selftest_initial_free]
    cmp eax, dword [rel free_frame_count]
    jne .fail
    lea rsi, [rel physical_memory_ok_message]
    call serial_write64
    lea rsi, [rel physical_memory_128m_ok_message]
    call serial_write64
    mov eax, 1
    ret
.fail:
    xor eax, eax
    ret

%if X86_64_NATIVE_RAM
; Private SysV call on the current trusted stack, IF0, no suspended C frame.
; Preserve all legacy allocator input registers except the result.
native_memory_call64:
    push rbp
    mov rbp, rsp
    and rsp, -16
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    mov rax, C_NATIVE_MEMORY_ENTRY
    call rax
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    mov rsp, rbp
    pop rbp
    ret

physical_frame_alloc64:
    mov esi, [rel allocation_test_floor]
    shl rsi, 12
    test rsi, rsi
    jnz .explicit
    ; Prefer upper RAM, preserving low memory without limiting capacity.
    mov edi, 4
    call native_memory_call64
    mov rsi, rax
    mov edi, 1
    call native_memory_call64
    test rax, rax
    jnz .done
    xor esi, esi
.explicit:
    mov edi, 1
    call native_memory_call64
.done:
    ret

physical_frame_test_high_window64:
    cmp dword [rel allocation_test_floor], 0
    jne .fail
    mov edi, 4
    xor esi, esi
    call native_memory_call64
    shr rax, 12
    mov [rel allocation_test_floor], eax
    mov eax, 1
    ret
.fail:
    xor eax, eax
    ret

physical_frame_alloc_high_selftest64:
    mov edi, 1
    mov esi, HIGH_MEMORY_BASE
    jmp native_memory_call64

physical_frame_free64:
    mov rsi, rdi
    mov edi, 2
    jmp native_memory_call64

physical_free_frame_count64:
    xor esi, esi
    mov edi, 3
    jmp native_memory_call64
%else
physical_frame_alloc64:
    cld
    mov ecx, dword [rel allocation_test_floor]
    mov r9d, FRAME_COUNT
    jmp physical_frame_alloc_from_index64

physical_frame_test_high_window64:
    cmp dword [rel allocation_test_floor], 0
    jne .fail
    mov dword [rel allocation_test_floor], HIGH_MEMORY_FRAME
    mov eax, 1
    ret
.fail:
    xor eax, eax
    ret

physical_frame_alloc_high_selftest64:
    cld
    mov ecx, HIGH_MEMORY_FRAME
    mov r9d, FRAME_COUNT

physical_frame_alloc_from_index64:
    cmp r9d, FRAME_COUNT
    ja .none
.scan:
    cmp ecx, r9d
    jae .none
    bt dword [rel usable_bitmap], ecx
    jnc .next
    bt dword [rel allocation_bitmap], ecx
    jc .next
    bts dword [rel allocation_bitmap], ecx
    dec dword [rel free_frame_count]
    mov eax, ecx
    shl rax, 12
    mov rdx, rax
    mov rdi, DIRECT_MAP_BASE
    add rdi, rax
    xor eax, eax
    mov ecx, FRAME_SIZE / 8
    rep stosq
    mov rax, rdx
    ret
.next:
    inc ecx
    jmp .scan
.none:
    xor eax, eax
    ret

physical_frame_free64:
    cld
    test rdi, FRAME_SIZE - 1
    jnz .invalid
    cmp rdi, MANAGED_LIMIT
    jae .invalid
    mov r8d, edi
    shr r8d, 12
    bt dword [rel usable_bitmap], r8d
    jnc .invalid
    bt dword [rel allocation_bitmap], r8d
    jnc .invalid
    mov rdx, rdi
    mov rdi, DIRECT_MAP_BASE
    add rdi, rdx
    xor eax, eax
    mov ecx, FRAME_SIZE / 8
    rep stosq
    btr dword [rel allocation_bitmap], r8d
    inc dword [rel free_frame_count]
    mov eax, 1
    ret
.invalid:
    xor eax, eax
    ret

physical_free_frame_count64:
    mov eax, dword [rel free_frame_count]
    ret

%endif

physical_frame_test_window_clear64:
    mov dword [rel allocation_test_floor], 0
    mov eax, 1
    ret

physical_frame_test_window_is_clear64:
    xor eax, eax
    cmp dword [rel allocation_test_floor], 0
    sete al
    ret

verify_direct_frame64:
    mov rdx, DIRECT_MAP_BASE
    add rdx, rdi
    cmp qword [rdx], 0
    jne .bad
    mov qword [rdx], rax
    cmp qword [rdx], rax
    jne .bad
    mov eax, 1
    ret
.bad:
    xor eax, eax
    ret

section .rodata
physical_memory_ok_message db "REIST_X86_64_PHYSICAL_MEMORY_OK", 13, 10, 0
physical_memory_128m_ok_message db "REIST_X86_64_PHYSICAL_MEMORY_128M_OK", 13, 10, 0

section .bss
align 4
allocation_test_floor resd 1

section .bss
alignb 16
multiboot_info_address:
    resd 1
multiboot_flags:
    resd 1
multiboot_mmap_address:
    resd 1
multiboot_mmap_length:
    resd 1
multiboot_mmap_end:
    resd 1
%if !X86_64_NATIVE_RAM
managed_frame_count:
    resd 1
free_frame_count:
    resd 1
%endif
selftest_initial_free:
    resd 1
parse_reserved_mode:
    resb 1
range_set_operation:
    resb 1

%if !X86_64_NATIVE_RAM
alignb 16
usable_bitmap:
    resb FRAME_BITMAP_BYTES
allocation_bitmap:
    resb FRAME_BITMAP_BYTES

alignb 4096
direct_pdpt:
    resb 4096
direct_page_directory:
    resb 4096
direct_page_tables:
    resb DIRECT_PT_COUNT * 4096
%else
section .memory_state nobits alloc noexec write align=4096
native_memory_arena:
    resb C_NATIVE_MEMORY_STATE_BYTES
managed_frame_count equ native_memory_arena
free_frame_count equ native_memory_arena + 4
usable_bitmap equ native_memory_arena + 64
allocation_bitmap equ usable_bitmap + FRAME_BITMAP_BYTES
alignb 4096
direct_pdpt: resb 4096
direct_page_directory: resb 16 * 4096
direct_page_tables: resb DIRECT_PT_COUNT * 4096
native_memory_arena_end:
section .bss
%endif

alignb 8
selftest_frame0:
    resq 1
selftest_frame1:
    resq 1
selftest_frame2:
    resq 1
selftest_reused_frame:
    resq 1
selftest_high_frame:
    resq 1
