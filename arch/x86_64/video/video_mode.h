#ifndef REIST_NATIVE_VIDEO_MODE_CORE_H
#define REIST_NATIVE_VIDEO_MODE_CORE_H
#include "userspace/sdk/include/reist/x86_64/video_mode.h"
enum { REIST_VIDEO_FIFO_BYTES=16384, REIST_VIDEO_FIFO_MIN_DATA=10240 };
typedef struct { uint64_t word[12],inverse[12]; } reist_video_state;
enum { VM_OWNER,VM_PARENT,VM_EPOCH,VM_PHASE,VM_FENCED,VM_LAST,VM_HEALTH,
       VM_DEADLINE,VM_NEXT,VM_FAULT,VM_RESERVED0,VM_RESERVED1 };
/* Trusted kernel adapters / host transcript only; never from userspace. */
typedef struct {
    void *context;
    int (*step)(void *,unsigned);
    int (*fence)(void *);
} reist_video_io;
void reist_video_init(reist_video_state *);
int reist_video_valid(const reist_video_state *);
int64_t reist_video_apply(reist_video_state *,const reist_video_request_v1 *,
                         uint64_t caller,uint64_t now,unsigned bind_flags,
                         const reist_video_io *);
int reist_video_retire(reist_video_state *,uint64_t,const reist_video_io *);
enum { REIST_VIDEO_QEMU=1,REIST_VIDEO_VMWARE=2 };
typedef struct { uint64_t base,length;uint32_t type,reserved; } reist_video_memory_range;
typedef struct {
    uint32_t profile,id,class_revision,command,header,bar[3];
    uint32_t framebuffer_bytes,fifo_bytes; /* trusted platform aperture proof */
} reist_video_pci;
typedef struct { uint32_t port,framebuffer,framebuffer_bytes,fifo,fifo_bytes; } reist_video_resources;
int reist_video_resources_admit(const reist_video_pci *,const reist_video_memory_range *,
                               unsigned,reist_video_resources *);
int reist_video_fifo_update(volatile uint32_t *,unsigned minimum,
                           unsigned x,unsigned y,unsigned width,unsigned height,int publish);
/* Kernel-private call envelope, populated by the assembly adapter only. */
typedef struct {
    uint64_t pdpt,pd,pts,fifo_pt,boot,boot_inverse,ranges,range_count,fence_display,text_ready;
} reist_video_platform;
typedef struct {
    reist_video_request_v1 request;
    uint64_t caller,now,relation,mode;
    int64_t result;
    uint64_t platform;
} reist_video_call;
_Static_assert(sizeof(reist_video_call)==112,"video kernel call");
#endif
