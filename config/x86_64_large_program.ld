OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS {
 text PT_LOAD FLAGS(5); rodata PT_LOAD FLAGS(4); data PT_LOAD FLAGS(6);
 middle PT_LOAD FLAGS(6); last PT_LOAD FLAGS(6); high PT_LOAD FLAGS(5);
}
SECTIONS {
 . = 0x410000;
 .text : { *(.text.start) *(.text*) } :text
 . = ALIGN(4096);
 .rodata : { KEEP(*(.rodata.memory_witness)) *(.rodata*) } :rodata
 . = ALIGN(4096);
 .data : { KEEP(*(.data.memory_witness)) *(.data*) } :data
 .bss (NOLOAD) : { *(.bss*) *(COMMON) } :data
 ASSERT(. <= 0x480000, "large fixture low image capacity")
 .large_middle 0x480000 (NOLOAD) : { KEEP(*(.large_middle)) } :middle
 .large_last 0x4fe000 (NOLOAD) : { KEEP(*(.large_last)) } :last
 .large_end_text 0x4ff000 : { KEEP(*(.large_end_text)) } :high
 ASSERT(. <= 0x500000, "large image upper bound")
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
