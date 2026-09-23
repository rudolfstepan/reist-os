/* Bounded System V ELF64 ET_EXEC adapter, not a file or authority interface.
 * Source and output are disjoint mapped objects; rejection leaves output intact.
 * See NATIVE_IMAGE_IMPORT_CONTRACT.md for the supported PT_LOAD subset. */
#ifndef REIST_X86_64_IMAGE_H
#define REIST_X86_64_IMAGE_H
#include <stddef.h>
#define REIST_X64_PREPARED_BYTES 36896U
#define REIST_X64_PREPARED_V2_BYTES 266336U
int reist_x64_image_prepare(void *output,const void *elf,size_t length);
/* RNPGv2 reserves a guarded32KiB stack and up to64 image page slots.
 * Only the opt-in NativeWide CREATE-v5 admits this mapping adapter. */
int reist_x64_image_prepare_v2(void *output,const void *elf,size_t length);
#ifdef REIST_NATIVE_LARGE_IMAGE
/* Explicit RNPGv3/CREATE-v7 profile; v1/v2 limits are unchanged. */
#define REIST_X64_PREPARED_V3_BYTES 1052960U
int reist_x64_image_prepare_v3(void *output,const void *elf,size_t length);
#endif
#endif
