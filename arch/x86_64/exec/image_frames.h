#ifndef REIST_X64_IMAGE_FRAMES_H
#define REIST_X64_IMAGE_FRAMES_H
#include <stdint.h>
#include <stddef.h>
/* Private existing ELF staging record; not a public ABI or capability.
 * Caller supplies trusted memory, fences consumers and serializes frame owners.
 * System V AMD64, ELF PF_* flags. Returns1 on complete release,0 on corruption
 * or backend failure (never ENOMEM). Successful partial frees clear their own
 * entries; failed entries remain owned. initial_free is diagnostic only. */
typedef struct {
    uint64_t frames[8];
    uint8_t flags[8];
    uint32_t initial_free;
    uint8_t segments, executable, cleanup_error, active;
    uint64_t entry;
} ReistX64Image;
_Static_assert(sizeof(ReistX64Image)==88,"private image layout");
_Static_assert(offsetof(ReistX64Image,flags)==64,"ELF flags offset");
_Static_assert(offsetof(ReistX64Image,initial_free)==72,"diagnostic offset");
_Static_assert(offsetof(ReistX64Image,active)==79,"ownership offset");
_Static_assert(offsetof(ReistX64Image,entry)==80,"entry offset");
int __attribute__((sysv_abi)) reist_x64_image_release(ReistX64Image *image);
#endif
