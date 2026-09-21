#ifndef REIST_NETWORK_DMA_H
#define REIST_NETWORK_DMA_H
#include <stdint.h>
#include "userspace/sdk/include/reist/x86_64/network.h"
typedef struct { uint64_t words[24],inverse[24]; } network_dma_state;
typedef struct { volatile unsigned char rx[10240],tx[4][2048]; } network_dma_memory;
typedef struct {
    void *context;
    uint32_t (*read)(void *,unsigned,unsigned);
    void (*write)(void *,unsigned,unsigned,uint32_t);
    uint32_t rx_physical,tx_physical;
    network_dma_memory *memory;
} network_dma_io;
void network_dma_init(network_dma_state *);
int network_dma_valid(const network_dma_state *);
int64_t network_dma_apply(network_dma_state *,const reist_network_request_v1 *,
    uint64_t caller,uint64_t now,unsigned relationship,unsigned char *,const network_dma_io *);
int64_t network_dma_retire(network_dma_state *,uint64_t caller,const network_dma_io *);
#endif
