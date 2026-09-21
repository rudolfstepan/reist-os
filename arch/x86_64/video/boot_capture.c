/* BIOS-only capture while the verified low-memory handoff is still reachable.
 * This code is compiled for i386 and runs before paging, never in a syscall. */
#include "arch/x86_64/video/boot_framebuffer.h"

static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint64_t get64(const uint8_t *p) {
    return (uint64_t)get32(p) | (uint64_t)get32(p + 4) << 32;
}
int reist_x64_display_capture32(uint32_t address, ReistX64BootFramebuffer *out) {
    if (!address || address > 0x100000 - 116) return 0;
    const uint8_t *info = (const uint8_t *)(uintptr_t)address;
    if ((get32(info) & ((1u << 12) | (1u << 6))) != ((1u << 12) | (1u << 6)))
        return 0;
    uint32_t length = get32(info + 44), start = get32(info + 48);
    if (!start || !length || length > 32 * 28 || start > 0x100000 - length)
        return 0;
    const uint8_t *map = (const uint8_t *)(uintptr_t)start;
    ReistX64BootMemoryRange ranges[32];
    unsigned count = 0, offset = 0;
    while (offset < length) {
        if (count == 32 || length - offset < 24) return 0;
        const uint8_t *entry = map + offset;
        uint32_t size = get32(entry);
        if ((size != 20 && size != 24) || size + 4 > length - offset)
            return 0;
        ranges[count].base = get64(entry + 4);
        ranges[count].length = get64(entry + 12);
        ranges[count].type = get32(entry + 20);
        ++count;
        offset += size + 4;
    }
    return reist_x64_boot_framebuffer_parse(info, 116, ranges, count, out);
}
