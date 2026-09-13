/* Native read-only filesystem RPC-v1. Not the legacy STORAGE_SUBMIT ABI. */
#ifndef REIST_X86_64_FILESYSTEM_H
#define REIST_X86_64_FILESYSTEM_H
#include <reist/x86_64/block.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { REIST_FS_FAT=1, REIST_FS_EXT2=2, REIST_FS_CACHE_SECTORS=16,
       REIST_FS_SESSION_REQUESTS=8 };
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t owner,sequence,deadline_ms,reserved;
    uint32_t length; int32_t status; uint64_t reserved_tail;
} reist_fs_header;
typedef union {
    x86os_vfs_shadow_frame_t stat;
    x86os_vfs_shadow_read_frame_t read;
    x86os_vfs_shadow_readdir_frame_t directory;
    uint8_t bytes[512];
} reist_fs_frame;
typedef char reist_fs_header_size_check[sizeof(reist_fs_header)==64?1:-1];
typedef char reist_fs_frame_size_check[sizeof(reist_fs_frame)==512?1:-1];
typedef char reist_fs_payload_sizes_check[
    sizeof(x86os_vfs_shadow_frame_t)==512 && sizeof(x86os_vfs_shadow_read_frame_t)==512 &&
    sizeof(x86os_vfs_shadow_readdir_frame_t)==512?1:-1];
typedef struct {
    void *context; uint64_t (*clock)(void *);
    int (*send)(void *,const x86os_ipc_bulk_message_t *,unsigned);
    int (*receive)(void *,x86os_ipc_bulk_message_t *,unsigned);
} reist_fs_transport;
typedef struct { uint64_t owner,sequence; uint32_t busy,failed; } reist_fs_client;
typedef struct {
    uint32_t version,size,filesystem,sectors;
    uint64_t owner,block_owner,deadline_ms;
} reist_fs_profile_v1;
typedef char reist_fs_profile_size_check[sizeof(reist_fs_profile_v1)==40?1:-1];
typedef struct {
    reist_fs_profile_v1 profile;
    reist_block_client block;
    reist_block_transport transport;
    uint64_t last_clock,next_sequence,request_deadline;
    uint32_t requests,ready,failed,busy,used;
    uint32_t lba[REIST_FS_CACHE_SECTORS];
    uint8_t data[REIST_FS_CACHE_SECTORS][512];
} reist_fs_server;
typedef char reist_fs_server_observer_layout_check[
    offsetof(reist_fs_server,requests)==120 && offsetof(reist_fs_server,lba)==140 &&
    offsetof(reist_fs_server,data)==204 && sizeof(reist_fs_server)==8400?1:-1];
/* Zero storage once. Rebinding requires a strictly newer exact generation.
 * init performs fresh media/root self-test; only immutable read-only media. */
int reist_fs_server_init(reist_fs_server *,const reist_fs_profile_v1 *,const reist_block_transport *);
int reist_fs_server_fence(reist_fs_server *);
int reist_fs_dispatch(reist_fs_server *,const x86os_ipc_bulk_message_t *,x86os_ipc_bulk_message_t *);
int reist_fs_client_bind(reist_fs_client *,uint64_t owner);
/* Initialize a canonical512-byte request, then submit once. Error leaves the
 * caller's frame unchanged; success (including readdir EOF=1) publishes reply. */
int reist_fs_request_init(reist_fs_frame *,unsigned operation,const char *,unsigned path_length,
                          uint32_t offset_or_index,uint32_t requested);
int reist_fs_call(reist_fs_client *,const reist_fs_transport *,reist_fs_frame *,unsigned timeout_ms);
#ifdef __cplusplus
}
#endif
#endif
