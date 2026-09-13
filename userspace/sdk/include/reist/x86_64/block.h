/* REIST native block RPC v1; existing IPC envelopes, not STORAGE_SUBMIT ABI. */
#ifndef REIST_X86_64_BLOCK_H
#define REIST_X86_64_BLOCK_H
#include <x86os.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t owner,sequence,lba,deadline_ms;
    uint32_t length; int32_t status; uint64_t reserved;
} reist_block_header;
typedef char reist_block_header_size_check[sizeof(reist_block_header)==64?1:-1];
typedef char reist_block_units_check[X86OS_STORAGE_BLOCK_READ==1 && X86OS_STORAGE_BLOCK_SIZE==512?1:-1];
typedef struct {uint64_t owner,sequence;unsigned busy,failed;} reist_block_client;
typedef struct {
    uint64_t owner,next_sequence,last_read_ms;
    uint32_t capacity,requests,ready;
} reist_block_server;
typedef struct {
    void *context; uint64_t (*clock)(void *);
    int (*send)(void *,const x86os_ipc_message_t *,unsigned);
    int (*receive)(void *,x86os_ipc_bulk_message_t *,unsigned);
} reist_block_transport;
typedef struct {
    void *context; uint64_t (*clock)(void *); int (*sleep)(void *,unsigned);
    int (*read)(void *,uint32_t,unsigned char *,uint64_t);
} reist_block_backend;
/* Local, generation-snapshotted service policy; never a wire request/grant. */
typedef struct {
    uint32_t version,size,request_limit,reserved;
    uint64_t deadline_ms;
} reist_block_profile_v1;
typedef char reist_block_profile_size_check[sizeof(reist_block_profile_v1)==24?1:-1];
int reist_block_profile_admit(const reist_block_profile_v1 *,uint64_t now);
int reist_block_dispatch_profile(reist_block_server *,const reist_block_profile_v1 *,
    const reist_block_backend *,const x86os_ipc_message_t *,x86os_ipc_bulk_message_t *);
/* Zero-initialize client storage once; rebind only to a newer generation. */
int reist_block_client_bind(reist_block_client *,uint64_t owner);
int reist_block_read(reist_block_client *,const reist_block_transport *,uint64_t lba,
                     unsigned char output[512],unsigned timeout_ms);
int reist_block_server_init(reist_block_server *,uint64_t owner,uint32_t sectors,uint64_t now);
int reist_block_dispatch(reist_block_server *,const reist_block_backend *,
                        const x86os_ipc_message_t *,x86os_ipc_bulk_message_t *);
#ifdef __cplusplus
}
#endif
#endif
