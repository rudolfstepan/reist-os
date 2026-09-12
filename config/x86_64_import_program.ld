OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { text PT_LOAD FLAGS(5); data PT_LOAD FLAGS(6); }
SECTIONS {
  . = 0x400000;
  .text : { *(.text.start) *(.text*) *(.rodata*) } :text
  ASSERT(. <= 0x402000, "import root text exceeds two pages")
  . = 0x402000;
  .data : { *(.data*) } :data
  .bss (NOLOAD) : { *(.bss*) *(COMMON) } :data
  ASSERT(. <= 0x408000, "import root exceeds eight pages")
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
