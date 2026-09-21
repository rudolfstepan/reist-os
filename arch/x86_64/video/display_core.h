#ifndef REIST_X64_DISPLAY_CORE_H
#define REIST_X64_DISPLAY_CORE_H
#include "userspace/sdk/include/reist/x86_64/display.h"
typedef struct {
    uint64_t owner,parent,epoch,fenced,window_ms,last_ms,commits,bytes;
    uint64_t inverse[8];
} ReistX64DisplayState;
#define DISPLAY_ABI __attribute__((sysv_abi))
void DISPLAY_ABI native_display_core_init64(ReistX64DisplayState *);
int64_t DISPLAY_ABI native_display_core_apply64(ReistX64DisplayState *,
    const reist_display_request_v1 *,uint64_t caller,uint64_t now_ms,uint64_t bind_flags);
int64_t DISPLAY_ABI native_display_core_fence64(ReistX64DisplayState *,uint64_t caller);
int64_t DISPLAY_ABI native_display_core_admit64(const ReistX64DisplayState *);
uint64_t DISPLAY_ABI native_display_rectangle64(const reist_display_request_v1 *,
    uint64_t width,uint64_t height);
#endif
