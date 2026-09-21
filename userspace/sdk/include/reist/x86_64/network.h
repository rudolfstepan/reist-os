#ifndef REIST_X64_NETWORK_H
#define REIST_X64_NETWORK_H
#include <stdint.h>
enum { REIST_NETWORK_BIND=1,REIST_NETWORK_QUERY,REIST_NETWORK_RESET,
       REIST_NETWORK_START,REIST_NETWORK_TX,REIST_NETWORK_RX,
       REIST_NETWORK_COMPLETE,REIST_NETWORK_FENCE,REIST_NETWORK_MAC };
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t owner,epoch,deadline_ms,address;
    uint32_t length,index;
    uint64_t reserved;
} reist_network_request_v1;
_Static_assert(sizeof(reist_network_request_v1)==64,"network device32 request-v1");
#endif
