OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { text PT_LOAD FILEHDR PHDRS FLAGS(5); }
SECTIONS {
  . = 0x410000 + SIZEOF_HEADERS;
  .text : { *(.text.start) *(.text*) *(.rodata*) } :text
  ASSERT(. <= 0x411000, "file program exceeds one RX page")
  .unexpected : { *(.data*) *(.bss*) *(COMMON) } :text
  ASSERT(SIZEOF(.unexpected) == 0, "file program requires unexpected writable storage")
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
