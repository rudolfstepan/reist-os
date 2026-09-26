#ifndef REIST_VGA_CORE_H
#define REIST_VGA_CORE_H
#include "userspace/sdk/include/reist/x86_64/vga_console.h"
typedef struct {
    /* fenced is a phase: 0 starting, 1 fenced, 2 self-tested/healthy. */
    uint64_t owner,parent,epoch,fenced,last,heartbeat;
    uint64_t output_head,output_count,input_head,input_count;
    uint64_t inverse[10];
    uint8_t output[2048],input[64];
} reist_vga_state;
_Static_assert(sizeof(reist_vga_state)==2272,"VGA fixed state");
#define VGA_ABI __attribute__((sysv_abi))
int64_t VGA_ABI native_vga_core_init64(reist_vga_state *);
int64_t VGA_ABI native_vga_core_admit64(const reist_vga_state *);
int64_t VGA_ABI native_vga_core_apply64(reist_vga_state *,const reist_vga_request_v1 *,
                                     uint64_t caller,uint64_t now,uint64_t bind_flags);
int64_t VGA_ABI native_vga_core_fence64(reist_vga_state *,uint64_t caller);
/* Caller has already checked authority, pointers and the monotonic deadline.
 * selector: 0 append output, 1 consume output, 2 append input, 3 consume input.
 * Appends are atomic; reads may return a bounded partial count.
 */
int64_t VGA_ABI native_vga_core_transfer64(reist_vga_state *,void *,uint64_t,uint64_t);
#endif
