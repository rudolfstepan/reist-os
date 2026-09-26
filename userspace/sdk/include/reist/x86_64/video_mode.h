#ifndef REIST_X64_VIDEO_MODE_H
#define REIST_X64_VIDEO_MODE_H
#include <stdint.h>
/* Private append-only device34 v1. Fixed VMware SVGA-II mode sequence.
 * No request field is a raw port, register value or physical address. */
enum { REIST_VIDEO_RESOURCE=34, REIST_VIDEO_BIND=1, REIST_VIDEO_FENCE,
       REIST_VIDEO_QUERY, REIST_VIDEO_STEP, REIST_VIDEO_HEARTBEAT,
       REIST_VIDEO_STATUS };
enum { REIST_VIDEO_ID=0, REIST_VIDEO_DISABLE, REIST_VIDEO_WIDTH,
       REIST_VIDEO_HEIGHT, REIST_VIDEO_BPP, REIST_VIDEO_ENABLE,
       REIST_VIDEO_MAP, REIST_VIDEO_CONFIGURE, REIST_VIDEO_READY,
       REIST_VIDEO_STOP };
enum { REIST_VIDEO_TEXT=0, REIST_VIDEO_PREPARING, REIST_VIDEO_GRAPHICS,
       REIST_VIDEO_REVOKING };
typedef struct {
    uint32_t version,size,operation,step;
    uint64_t owner,epoch,reserved[4];
} reist_video_request_v1;
_Static_assert(sizeof(reist_video_request_v1)==64,"video mode v1 size");
#endif
