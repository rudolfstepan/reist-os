#ifndef REIST_X64_BOOT_FRAMEBUFFER_H
#define REIST_X64_BOOT_FRAMEBUFFER_H
#include <stddef.h>
#include <stdint.h>

/* Private Multiboot-v1/VBE capture. No device mapping or ownership is granted
 * by a successful parse. The caller must separately establish a supervisor
 * MMIO mapping and a generation-scoped display domain. */
typedef struct {
    uint64_t base;
    uint32_t pitch, width, height, bytes;
    uint32_t map_base, map_bytes;
} ReistX64BootFramebuffer;
typedef struct {
    uint64_t base, length;
    uint32_t type;
} ReistX64BootMemoryRange;

int reist_x64_boot_framebuffer_parse(const uint8_t *info, size_t info_bytes,
                                     const ReistX64BootMemoryRange *ranges,
                                     size_t range_count,
                                     ReistX64BootFramebuffer *out);
#endif
