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
#endif
