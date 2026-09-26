/* Ring3 fixed mode policy. The kernel mediates each bounded hardware step. */
#include "native_mode.h"
static int clock_valid(const reist_video_transport *io,uint64_t end,uint64_t *last) {
    if(!io || !io->clock || !io->request || end>>60)return -22;
    uint64_t now=io->clock(io->context);
    if(now>>60 || now<*last)return -84;
    if(now>=end || end-now>2000)return -110;
    *last=now;return 0;
}
int reist_video_enter(const reist_video_transport *io,uint64_t end) {
    uint64_t last=0;
    for(unsigned step=REIST_VIDEO_ID;step<=REIST_VIDEO_READY;step++) {
        int r=clock_valid(io,end,&last);if(r)return r;
        int64_t result=io->request(io->context,REIST_VIDEO_STEP,step);
        if(result)return result<0 && result>=-4095?(int)result:-71;
    }
    return clock_valid(io,end,&last);
}
int reist_video_leave(const reist_video_transport *io,uint64_t end) {
    uint64_t last=0;int r=clock_valid(io,end,&last);if(r)return r;
    int64_t result=io->request(io->context,REIST_VIDEO_STEP,REIST_VIDEO_STOP);
    if(result)return result<0 && result>=-4095?(int)result:-71;
    return clock_valid(io,end,&last);
}
