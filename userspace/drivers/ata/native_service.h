#ifndef REIST_NATIVE_ATA_SERVICE_H
#define REIST_NATIVE_ATA_SERVICE_H
#include <reist/x86_64/block.h>
#include "native_pio.h"
typedef struct {
    reist_block_server server;
    reist_pio_ops upstream;
    uint64_t owner,deadline,last_clock;
    unsigned clock_fault;
} reist_native_service;
int reist_native_service_init(reist_native_service *,uint64_t,const reist_pio_ops *);
int reist_native_service_dispatch(reist_native_service *,const x86os_ipc_message_t *,x86os_ipc_bulk_message_t *);
/* Zero once; each attempted initialization consumes its owner generation.
 * The embedded legacy server is the sole request/sequence authority. */
typedef struct {
    reist_native_service service;
    reist_block_profile_v1 profile;
} reist_native_profile_service;
int reist_native_service_init_profile(reist_native_profile_service *,uint64_t,
    const reist_pio_ops *,const reist_block_profile_v1 *);
int reist_native_service_dispatch_profile(reist_native_profile_service *,
    const x86os_ipc_message_t *,x86os_ipc_bulk_message_t *);
typedef reist_native_profile_service reist_native_profile_service_v2;
int reist_native_service_init_profile_v2(reist_native_profile_service_v2 *,uint64_t,
    const reist_pio_ops *,const reist_block_profile_v2 *);
int reist_native_service_dispatch_profile_v2(reist_native_profile_service_v2 *,
    const x86os_ipc_message_t *,x86os_ipc_bulk_message_t *);
#endif
