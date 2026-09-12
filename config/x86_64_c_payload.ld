/* Private native C payload layout v2; Multiboot container stays ELF32. */
OUTPUT_FORMAT(elf64-x86-64)
ENTRY(x86_64_c_core_entry)
PHDRS {
  text PT_LOAD FLAGS(5);
  rodata PT_LOAD FLAGS(4);
  data PT_LOAD FLAGS(6);
  bss PT_LOAD FLAGS(6);
  memory PT_LOAD FLAGS(6);
}
SECTIONS {
  .text 0xFFFFFFFF80185000 : {
    KEEP(*(.text.entry))
    *(.text .text.*)
  } :text
  .rodata 0xFFFFFFFF80195000 : { *(.rodata .rodata.*) } :rodata
  .data 0xFFFFFFFF8019D000 : {
    KEEP(*(.data.boot_state))
    *(.data .data.*)
  } :data
  .bss 0xFFFFFFFF801A1000 (NOLOAD) : {
    KEEP(*(.bss.boot_state))
    *(.bss .bss.*) *(COMMON)
  } :bss
  .memory_state 0xFFFFFFFF80200000 (NOLOAD) : {
    KEEP(*(.memory_state))
  } :memory
  ASSERT(SIZEOF(.memory_state) <= 5242880, "native memory metadata capacity")
  .init_array : { *(.init_array .init_array.* .ctors .ctors.*) } :NONE
  .fini_array : { *(.fini_array .fini_array.* .dtors .dtors.*) } :NONE
  .eh_frame : { *(.eh_frame .eh_frame.* .eh_frame_hdr) } :NONE
  .gcc_except_table : { *(.gcc_except_table .gcc_except_table.*) } :NONE
  .tls : { *(.tdata .tdata.* .tbss .tbss.*) } :NONE
  /DISCARD/ : { *(.comment) *(.note .note.*) }
  x86_64_c_serial_write64 = 0xFFFFFFFF80184000;
  x86_64_c_process_shell64 = 0xFFFFFFFF80184100;
  x86_64_c_process_run64 = 0xFFFFFFFF80184200;
  x86_64_c_handoff = 0xFFFFFFFF801FF000;
  x86_64_c_control_handoff = 0xFFFFFFFF801FF080;
  ASSERT(x86_64_c_core_entry == ADDR(.text), "native C entry is not first")
  ASSERT(x86_64_c_data_state == ADDR(.data), "native C data boot state moved")
  ASSERT(x86_64_c_bss_state == ADDR(.bss), "native C BSS boot state moved")
  ASSERT(SIZEOF(.text) > 0 && SIZEOF(.text) <= 65536, "native C text capacity")
  ASSERT(SIZEOF(.rodata) > 0 && SIZEOF(.rodata) <= 32768, "native C rodata capacity")
  ASSERT(SIZEOF(.data) >= 32 && SIZEOF(.data) <= 16384, "native C data capacity")
  ASSERT(SIZEOF(.bss) >= 32 && SIZEOF(.bss) <= 262144, "native C BSS capacity")
  ASSERT(SIZEOF(.init_array) == 0, "native C constructors forbidden")
  ASSERT(SIZEOF(.fini_array) == 0, "native C destructors forbidden")
  ASSERT(SIZEOF(.eh_frame) == 0, "native C unwind forbidden")
  ASSERT(SIZEOF(.gcc_except_table) == 0, "native C exceptions forbidden")
  ASSERT(SIZEOF(.tls) == 0, "native C TLS forbidden")
}
