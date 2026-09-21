#include "arch/x86_64/video/boot_framebuffer.h"

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint64_t le64(const uint8_t *p) {
    return (uint64_t)le32(p) | ((uint64_t)le32(p + 4) << 32);
}

int reist_x64_boot_framebuffer_parse(const uint8_t *info, size_t info_bytes,
                                     const ReistX64BootMemoryRange *ranges,
                                     size_t range_count,
                                     ReistX64BootFramebuffer *out) {
    if (!info || !out || info_bytes < 116 || !range_count ||
        range_count > 32 || !ranges ||
        !(le32(info) & (UINT32_C(1) << 12)))
        return 0;
    const uint64_t base = le64(info + 88);
    const uint32_t pitch = le32(info + 96), width = le32(info + 100);
    const uint32_t height = le32(info + 104);
    if (info[108] != 32 || info[109] != 1 ||
        info[110] != 16 || info[111] != 8 ||
        info[112] != 8 || info[113] != 8 ||
        info[114] != 0 || info[115] != 8 ||
        !((width == 1024 && height == 768) ||
          (width == 800 && height == 600)) ||
        pitch < width * 4 || pitch > 16384 || (pitch & 3) ||
        (base & 4095) || base < UINT64_C(0xc0000000) ||
        base >= UINT64_C(0x100000000))
        return 0;
    const uint64_t bytes = (uint64_t)pitch * height;
    const uint64_t end = base + bytes;
    const uint64_t map_base = base & ~UINT64_C(4095);
    const uint64_t map_end = (end + 4095) & ~UINT64_C(4095);
    if (!bytes || end <= base || end > UINT64_C(0x100000000) ||
        map_end <= map_base || map_end > UINT64_C(0x100000000) ||
        map_end - map_base > UINT32_MAX)
        return 0;
    for (size_t i = 0; i < range_count; ++i) {
        const uint64_t first = ranges[i].base;
        const uint64_t last = first + ranges[i].length;
        if (!ranges[i].length || last < first) return 0;
        if (ranges[i].type == 1 && first < map_end && map_base < last)
            return 0;
    }
    out->base = base;
    out->pitch = pitch;
    out->width = width;
    out->height = height;
    out->bytes = (uint32_t)bytes;
    out->map_base = (uint32_t)map_base;
    out->map_bytes = (uint32_t)(map_end - map_base);
    return 1;
}
