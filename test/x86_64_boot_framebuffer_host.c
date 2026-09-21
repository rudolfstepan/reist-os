#include "arch/x86_64/video/boot_framebuffer.h"
#include <stdint.h>
#include <string.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>

static void put32(uint8_t *p, uint32_t x) {
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(x >> (i * 8));
}
static void put64(uint8_t *p, uint64_t x) {
    put32(p, (uint32_t)x); put32(p + 4, (uint32_t)(x >> 32));
}
static void make_record(uint8_t *p) {
    memset(p, 0, 116);
    put32(p, UINT32_C(1) << 12);
    put64(p + 88, UINT64_C(0xfd000000));
    put32(p + 96, 4096); put32(p + 100, 1024); put32(p + 104, 768);
    p[108] = 32; p[109] = 1;
    p[110] = 16; p[111] = 8;
    p[112] = 8; p[113] = 8;
    p[114] = 0; p[115] = 8;
}
static int parse(const uint8_t *p, ReistX64BootFramebuffer *out) {
    const ReistX64BootMemoryRange ram = {0x100000, 0x7f00000, 1};
    return reist_x64_boot_framebuffer_parse(p, 116, &ram, 1, out);
}
int main(void) {
    uint8_t p[116]; ReistX64BootFramebuffer out, old;
    make_record(p); memset(&out, 0xa5, sizeof out);
    assert(parse(p, &out) == 1);
    assert(out.base == UINT64_C(0xfd000000) && out.bytes == 4096 * 768);
    assert(out.map_base == UINT32_C(0xfd000000) && out.map_bytes == out.bytes);
    old = out;
#define REJECT(expression) do { expression; assert(parse(p, &out) == 0); \
    assert(memcmp(&out, &old, sizeof out) == 0); make_record(p); } while (0)
    REJECT(put32(p, 0));
    REJECT(p[108] = 24);
    REJECT(p[109] = 2);
    REJECT(p[110] = 24);
    REJECT(p[111] = 7);
    REJECT(p[112] = 9);
    REJECT(p[113] = 7);
    REJECT(p[114] = 1);
    REJECT(p[115] = 7);
    REJECT(put32(p + 100, 1920));
    REJECT(put32(p + 104, 0));
    REJECT(put32(p + 96, 4092));
    REJECT(put32(p + 96, 16388));
    REJECT(put64(p + 88, UINT64_C(0x100000000)));
    REJECT(put64(p + 88, UINT64_C(0xfffff000)));
    REJECT(put64(p + 88, UINT64_C(0x7000000)));
#undef REJECT
    assert(reist_x64_boot_framebuffer_parse(p, 115, 0, 0, &out) == 0);
    assert(reist_x64_boot_framebuffer_parse(p, 116, 0, 33, &out) == 0);
    assert(reist_x64_boot_framebuffer_parse(0, 116, 0, 0, &out) == 0);
    assert(reist_x64_boot_framebuffer_parse(p, 116, 0, 0, 0) == 0);
    const ReistX64BootMemoryRange overlap = {UINT64_C(0xfd000000), 4096, 1};
    assert(reist_x64_boot_framebuffer_parse(p, 116, &overlap, 1, &out) == 0);
    const ReistX64BootMemoryRange reserved = {UINT64_C(0xfd000000), 4096, 2};
    assert(reist_x64_boot_framebuffer_parse(p, 116, &reserved, 1, &out) == 1);
    assert(memcmp(&out, &old, sizeof out) == 0);
    put32(p + 96, 3200); put32(p + 100, 800); put32(p + 104, 600);
    assert(parse(p, &out) == 1 && out.bytes == 1920000);
    return 0;
}
