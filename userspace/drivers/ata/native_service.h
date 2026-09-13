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
#endif
