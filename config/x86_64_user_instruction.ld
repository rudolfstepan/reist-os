OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS
{
  text PT_LOAD FILEHDR PHDRS FLAGS(5);
  instruction PT_LOAD FLAGS(5);
}
SECTIONS
{
  . = 0x00400000 + SIZEOF_HEADERS;
  .text : { *(.text .text.*) *(.rodata .rodata.*) } :text
  ASSERT(. <= 0x00401000, "instruction fixture exceeds first RX page")
  . = 0x00401000;
  .instruction : { *(.instruction) } :instruction
  ASSERT(. <= 0x00402000, "instruction fixture exceeds second RX page")
  /DISCARD/ : {
    *(.data .data.*) *(.bss .bss.*) *(.comment) *(.note .note.*)
    *(.eh_frame .eh_frame.*)
  }
}
