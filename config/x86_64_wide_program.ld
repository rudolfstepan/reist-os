OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { text PT_LOAD FLAGS(5); rodata PT_LOAD FLAGS(4); data PT_LOAD FLAGS(6); }
SECTIONS {
  /* RNPGv2 owns guard/stack slots7..15; they are not ELF segments. */
  . = 0x410000;
  .text : { *(.text.start) *(.text*) } :text
  . = ALIGN(4096);
  .rodata : { KEEP(*(.rodata.memory_witness)) *(.rodata*) } :rodata
  . = ALIGN(4096);
  .data : { KEEP(*(.data.memory_witness)) *(.data*) } :data
  .bss (NOLOAD) : { *(.bss*) *(COMMON) } :data
  ASSERT(. <= 0x440000, "wide program exceeds admitted image")
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
