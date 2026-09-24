#ifndef REIST_X64_DESKTOP_DISPLAY_H
#define REIST_X64_DESKTOP_DISPLAY_H
#include <stddef.h>
#include <stdint.h>
#include <reist/x86_64/display.h>

/* Private Ring3 adapter-v1. Single-threaded, non-reentrant callbacks. Attach
 * is configuration, never a display grant. Buffers/font outlive detach.
 * The supervisor must supply verified geometry and a live delegated epoch. */
typedef struct {
    uint32_t version, size, width, height;
    uint64_t owner, epoch;
    uint32_t *front, *back;
    size_t pixel_capacity;
    const unsigned char *font;
    size_t font_bytes;
    void *context;
    int (*clock_ms)(void *, uint64_t *);
    int (*commit)(void *, const reist_display_request_v1 *);
} reist_desktop_display_config;

int reist_desktop_display_attach(const reist_desktop_display_config *);
void reist_desktop_display_detach(void);
/* At most8 copies, no sleep. 0=drained,1=pending,<0=error. next_ms is the
 * earliest useful retry, not permission to busy-wait. Service input/health
 * between calls. A successful SDK frame commit queues private pixels; this
 * pump performs physical presentation and must be wired into the event loop. */
int reist_desktop_display_pump(uint64_t *next_ms);
#endif
