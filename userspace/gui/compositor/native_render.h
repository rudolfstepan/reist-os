#ifndef REIST_NATIVE_RENDER_H
#define REIST_NATIVE_RENDER_H
#include "native_session.h"
/* Fixed 640x480 viewport; the framebuffer ABI intentionally exports no map. */
typedef struct {
    uint64_t tiles[2];
    uint64_t next_draw,last_draw;
    uint32_t cursor,pixels[64*64];
} reist_native_renderer;
int reist_native_render_due(reist_native_renderer *,uint64_t);
void reist_native_render_damage(reist_native_renderer *,reist_native_compositor *);
int reist_native_render_tile(reist_native_renderer *,const reist_native_compositor *,
    unsigned *x,unsigned *y,unsigned *width,unsigned *height);
#endif
