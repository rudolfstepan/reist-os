OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS
{
  text PT_LOAD FILEHDR PHDRS FLAGS(5);
  rodata PT_LOAD FLAGS(4);
}
SECTIONS
{
  . = 0x00400000 + SIZEOF_HEADERS;
  .text : { *(.text .text.*) } :text
  ASSERT(. <= 0x00401000, "mapping fixture exceeds compact RX page")
  . = 0x00401000;
  .rodata : { *(.rodata .rodata.*) } :rodata
  ASSERT(. <= 0x00403000, "mapping fixture exceeds two compact R/NX pages")
  /DISCARD/ : {
    *(.data .data.*) *(.bss .bss.*) *(.comment) *(.note .note.*)
    *(.eh_frame .eh_frame.*)
  }
}
