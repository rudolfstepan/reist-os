/* Bounded System V ELF64 ET_EXEC adapter, not a file or authority interface.
 * Source and output are disjoint mapped objects; rejection leaves output intact.
 * See NATIVE_IMAGE_IMPORT_CONTRACT.md for the supported PT_LOAD subset. */
#ifndef REIST_X86_64_IMAGE_H
#define REIST_X86_64_IMAGE_H
#include <stddef.h>
#define REIST_X64_PREPARED_BYTES 36896U
int reist_x64_image_prepare(void *output,const void *elf,size_t length);
#endif
