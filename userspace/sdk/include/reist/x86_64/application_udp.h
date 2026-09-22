#ifndef REIST_X86_64_APPLICATION_UDP_H
#define REIST_X86_64_APPLICATION_UDP_H
#include <stdint.h>
#include <reist/x86_64/network_session.h>
#define REIST_APP_UDP_PEER UINT32_C(0xc0000203)
#define REIST_APP_UDP_SOCKETS 8U
#define REIST_APP_UDP_QUEUE 4U
#define REIST_APP_UDP_BYTES 512U
#define REIST_APP_UDP_REQUESTS 64U
#define REIST_APP_UDP_MS 6000U
enum { REIST_APP_UDP_OPEN=1, REIST_APP_UDP_BIND, REIST_APP_UDP_SEND,
       REIST_APP_UDP_RECEIVE, REIST_APP_UDP_CLOSE, REIST_APP_UDP_RELEASE };
typedef struct {
    uint32_t version,size;
    uint64_t root,application,service,epoch,expires;
    uint32_t protocol,peer;
    uint16_t local_port,peer_port;
    uint32_t reserved;
} reist_app_udp_grant;
typedef struct {
    reist_app_udp_grant grant;
    uint64_t sequence,deadline;
    uint32_t operation,handle,length;
    int32_t result;
    uint8_t payload[REIST_APP_UDP_BYTES];
} reist_app_udp_request;
typedef struct { uint32_t length;uint8_t payload[REIST_APP_UDP_BYTES]; } reist_app_udp_datagram;
typedef struct {
    uint32_t handle,bound,head,count;
    reist_app_udp_datagram queue[REIST_APP_UDP_QUEUE];
} reist_app_udp_socket;
typedef struct {
    uint64_t root,service,last_ms,last_epoch,sequence;
    uint32_t active,issued;
    reist_app_udp_grant grant;
    reist_app_udp_request pending;
    reist_app_udp_socket sockets[REIST_APP_UDP_SOCKETS];
} reist_app_udp_state;
_Static_assert(sizeof(reist_app_udp_grant)==64,"UDP grant v1");
_Static_assert(sizeof(reist_app_udp_request)==608,"UDP request v1");
int reist_app_udp_init(reist_app_udp_state *,uint64_t root,uint64_t service,uint64_t now);
int reist_app_udp_grant_set(reist_app_udp_state *,const reist_app_udp_grant *,uint64_t now);
void reist_app_udp_revoke(reist_app_udp_state *);
/* 0: complete, result in reply; 1: admitted packet operation requires IO.
 * A negative return is admission failure with no state/output publication. */
int reist_app_udp_begin(reist_app_udp_state *,const reist_app_udp_request *,reist_app_udp_request *,uint64_t now);
int reist_app_udp_finish(reist_app_udp_state *,const reist_app_udp_request *,reist_app_udp_request *,int wire_result,uint64_t now);
int reist_app_udp_enqueue(reist_app_udp_state *,const reist_app_udp_grant *,const uint8_t *,unsigned length,uint64_t now);
int reist_app_udp_exchange(reist_app_udp_state *,reist_net_protocol *,const reist_net_io *,const reist_app_udp_request *,reist_app_udp_request *);
int reist_app_udp_operand(int argc,const char *const *argv,reist_app_udp_grant *);
#endif
