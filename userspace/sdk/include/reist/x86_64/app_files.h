/* Explicit immutable Ring3 objects. Not an ambient VFS or storage syscall. */
#ifndef REIST_X86_64_APP_FILES_H
#define REIST_X86_64_APP_FILES_H
#include <x86os.h>
enum { REIST_APP_BYTES=16384, REIST_APP_ENTRIES=32, REIST_APP_REQUESTS=80,
       REIST_APP_MS=1000, REIST_APP_CHUNK=256,
       REIST_APP_HELLO=0, REIST_APP_STAT=1, REIST_APP_READ=2,
       REIST_APP_READDIR=3, REIST_APP_CLOSE=4,
       REIST_APP_READY=1, REIST_APP_BOUND=2, REIST_APP_CLOSED=3 };
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t root,child,epoch,sequence,deadline;
    int32_t status;uint32_t length,offset,requested;
    uint64_t reserved;
    uint8_t payload[432];
} reist_app_frame;
_Static_assert(sizeof(reist_app_frame)==512,"application object frame v1");
typedef struct {
    x86os_file_info_t info;
    uint32_t length,count;
    union { uint8_t bytes[REIST_APP_BYTES];x86os_file_info_t entries[REIST_APP_ENTRIES]; };
} reist_app_snapshot;
typedef struct {
    uint32_t version,size,phase,reserved;
    uint64_t root,child,epoch,deadline,previous,sequence;
    const reist_app_snapshot *object;
} reist_app_grant;
/* Caller supplies a complete validated immutable capture, including actual EOF
 * for directories. Init requires zero state. No in-place renewal/rebind. */
int reist_app_grant_init(reist_app_grant *,const reist_app_snapshot *,
    uint64_t root,uint64_t child,uint64_t epoch,uint64_t now);
/* Transport must have admitted this exact child via private send-only endpoint.
 * Errors publish neither state nor reply; caller revokes after protocol errors. */
int reist_app_dispatch(reist_app_grant *,const reist_app_snapshot *,
    const reist_app_frame *,reist_app_frame *,uint64_t now);
void reist_app_revoke(reist_app_grant *);
/* Select only the explicit operand of the existing cat/ls grammar. 1 means
 * help/no file grant. No path canonicalization or ambient lookup here. */
int reist_app_operand(unsigned tool,int argc,const char *const *argv,const char **path);
#endif
