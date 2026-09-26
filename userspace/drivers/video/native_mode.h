#ifndef REIST_NATIVE_MODE_POLICY_H
#define REIST_NATIVE_MODE_POLICY_H
#include <stdint.h>
#include <reist/x86_64/video_mode.h>
typedef struct {
    void *context;
    uint64_t (*clock)(void *);
    int64_t (*request)(void *,unsigned,unsigned);
} reist_video_transport;
/* Caller supplies the original absolute start/return deadline. */
int reist_video_enter(const reist_video_transport *,uint64_t deadline);
int reist_video_leave(const reist_video_transport *,uint64_t deadline);
#endif
