#ifndef REIST_X64_DESKTOP_SERVICES_H
#define REIST_X64_DESKTOP_SERVICES_H
#include <stdint.h>
#include <stddef.h>
#include <x86os.h>

enum { REIST_DESKTOP_STAT=1, REIST_DESKTOP_OPEN, REIST_DESKTOP_READ,
    REIST_DESKTOP_READDIR, REIST_DESKTOP_CLOSE, REIST_DESKTOP_LAUNCH,
    REIST_DESKTOP_IDENTITY, REIST_DESKTOP_WAIT, REIST_DESKTOP_CANCEL };
enum { REIST_DESKTOP_MANIFEST_READ=1, REIST_DESKTOP_MANIFEST_EXEC=2,
    REIST_DESKTOP_SERVICE_READ_BYTES=1792, REIST_DESKTOP_SERVICE_ENTRIES=6,
    REIST_DESKTOP_REPLY_ADMITTED=1 };
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t root,desktop,epoch,sequence,deadline_ms,object;
    uint32_t offset,count,argc;
    int32_t status;
    uint64_t reserved[6];
    union {
        unsigned char bytes[1920];
        struct { char path[192],argv[8][128]; unsigned char reserved[704]; } command;
        x86os_file_info_t info;
        x86os_file_info_t entries[REIST_DESKTOP_SERVICE_ENTRIES];
    } payload;
} reist_desktop_service_frame;
_Static_assert(sizeof(x86os_file_info_t)==276,"file metadata ABI");
_Static_assert(sizeof(reist_desktop_service_frame)==2048,"desktop service wire-v1");

/* Immutable supervisor-owned manifest from the qualified signed image. Its
 * paths and metadata are actual image observations, not client assertions.
 * EXEC digests bind prepared RNPG bytes; the backend must check before CREATE. */
typedef struct {
    char path[192];
    x86os_file_info_t info;
    uint32_t rights;
    unsigned char digest[32];
} reist_desktop_service_manifest;
typedef struct {
    uint64_t root,desktop,epoch,service_generation;
    const reist_desktop_service_manifest *manifest;
    uint32_t manifest_count;
    void *context;
    int (*clock_ms)(void *,uint64_t *);
    /* One bounded work quantum;1=pending,0=complete,<0=terminal failure.
     * No whole-file wait. Broker initializes/owns output. On CREATE backend
     * must retain every actual child for abort even if its reply is corrupt. */
    int (*step)(void *,const reist_desktop_service_frame *,
        const reist_desktop_service_manifest *,reist_desktop_service_frame *);
    /* Fence/revoke/reap all delegated objects and actual created children. */
    int (*abort)(void *);
} reist_desktop_broker_config;
typedef struct {
    uint64_t id,deadline,service_generation;
    uint32_t manifest_index;
} reist_desktop_read_object;
typedef struct {
    uint32_t version,size,phase,head,count,started,rate_head,rate_count;
    uint64_t previous,sequence,object_sequence,last_epoch;
    uint64_t timestamps[16],children[2],last_children[2];
    reist_desktop_broker_config config;
    reist_desktop_read_object objects[8];
    reist_desktop_service_frame queue[4],reply;
} reist_desktop_broker;
/* Zero-init once. Reinit only after successful revoke with a newer epoch. */
int reist_desktop_broker_init(reist_desktop_broker *,const reist_desktop_broker_config *,uint64_t now);
/* Root-only startup: adopt the two actual manifest-verified CREATE results
 * before admitting any desktop request. This is not a wire operation. */
int reist_desktop_broker_adopt(reist_desktop_broker *,const uint64_t owners[2],uint64_t now);
/* Root-only; caller has fenced/reaped old and validated actual CREATE result.
 * Never exposed as a wire operation. Pending old-owner work forbids rebinding. */
int reist_desktop_broker_replace(reist_desktop_broker *,uint64_t old_owner,uint64_t new_owner,uint64_t now);
int reist_desktop_broker_submit(reist_desktop_broker *,const reist_desktop_service_frame *,uint64_t now);
/* 0=idle,1=pending,2=reply. Errors never publish output. */
int reist_desktop_broker_step(reist_desktop_broker *,reist_desktop_service_frame *,uint64_t now);
int reist_desktop_broker_revoke(reist_desktop_broker *);

/* Rejection with flags0 has not consumed the request sequence. Admitted
 * replies use flags1 even for an operational error (e.g. WAIT/EAGAIN). */
int reist_desktop_service_reply_valid(const reist_desktop_service_frame *,const reist_desktop_service_frame *);
int reist_desktop_service_reject(const reist_desktop_service_frame *,int,reist_desktop_service_frame *);
typedef struct {
    uint64_t root,desktop,epoch;
    void *context;
    int (*clock_ms)(void *,uint64_t *);
    int (*send)(void *,const reist_desktop_service_frame *);
    int (*receive)(void *,reist_desktop_service_frame *);
    /* Pump input/health/display, then sleep for the requested1..10ms. */
    int (*wait)(void *,unsigned);
    void (*failed)(void *,int);
} reist_desktop_service_client_config;
typedef struct {
    reist_desktop_service_client_config config;
    uint64_t sequence,previous,last_epoch,timestamps[16];
    unsigned phase,busy,head,count;
    reist_desktop_service_frame request,reply;
} reist_desktop_service_client;
int reist_desktop_service_client_init(reist_desktop_service_client *,const reist_desktop_service_client_config *);
void reist_desktop_service_client_detach(reist_desktop_service_client *);
/* Caller supplies operation/arguments in a zero-routed version1/size2048
 * request. Output unchanged on any error. No implicit retries of operations
 * rejected by root. Only transport backpressure may retry within timeout. */
int reist_desktop_service_exchange(reist_desktop_service_client *,const reist_desktop_service_frame *,
    reist_desktop_service_frame *,unsigned timeout_ms);
#endif
