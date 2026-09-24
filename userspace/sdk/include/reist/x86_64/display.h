#ifndef REIST_X64_DISPLAY_H
#define REIST_X64_DISPLAY_H
#include <stdint.h>
/* REIST native display-v1. DEVICE_CONTROL113/op30, explicitly delegated.
 * BGRX32 tiles; pitch and coordinates are bytes/pixels respectively. */
enum { REIST_DISPLAY_BIND=1, REIST_DISPLAY_QUERY=2,
       REIST_DISPLAY_COMMIT=3, REIST_DISPLAY_FENCE=4 };
typedef struct {
    uint32_t version, size, operation, flags;
    uint64_t owner, epoch, deadline_ms, pixels;
    uint32_t x, y;
    uint16_t width, height;
    uint32_t stride;
} reist_display_request_v1;
_Static_assert(sizeof(reist_display_request_v1)==64,"display-v1 request");
/* VBE geometry in pixels/bytes, BGRX32. No physical or virtual address.
 * Inputs: exact owner/epoch; all output fields zero. Opt-in kernel profile. */
enum { REIST_DISPLAY_INFO=5 };
typedef struct {
    uint32_t version, size, operation, flags;
    uint64_t owner, epoch;
    uint32_t width, height, pitch, bits_per_pixel;
    uint32_t red_field_position, green_field_position, blue_field_position, reserved;
} reist_display_info_v2;
_Static_assert(sizeof(reist_display_info_v2)==64,"display info-v2 request");
#endif
