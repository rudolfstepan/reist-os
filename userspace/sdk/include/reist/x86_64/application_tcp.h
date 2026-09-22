#ifndef REIST_X86_64_APPLICATION_TCP_H
#define REIST_X86_64_APPLICATION_TCP_H
#include <stdint.h>
#include <reist/x86_64/network_session.h>
#define REIST_APP_TCP_PEER UINT32_C(0xc0000203)
#define REIST_APP_TCP_SOCKETS 4U
#define REIST_APP_TCP_BYTES 512U
#define REIST_APP_TCP_RECEIVE 2048U
#define REIST_APP_TCP_REQUESTS 64U
#define REIST_APP_TCP_MS 6000U
enum { REIST_APP_TCP_OPEN=1,REIST_APP_TCP_CONNECT,REIST_APP_TCP_SEND,
       REIST_APP_TCP_RECV,REIST_APP_TCP_CLOSE,REIST_APP_TCP_RELEASE,
       REIST_APP_TCP_STATS };
enum { REIST_TCP_CLOSED,REIST_TCP_SYN_SENT,REIST_TCP_ESTABLISHED,
       REIST_TCP_FIN_WAIT_1,REIST_TCP_FIN_WAIT_2,REIST_TCP_CLOSE_WAIT,
       REIST_TCP_CLOSING,REIST_TCP_LAST_ACK,REIST_TCP_TIME_WAIT };
typedef struct {
    uint32_t version,size;
    uint64_t root,application,service,epoch,expires;
    uint32_t protocol,peer;
    uint16_t local_port,peer_port;
    uint32_t reserved;
} reist_app_tcp_grant;
typedef struct {
    reist_app_tcp_grant grant;
    uint64_t sequence,deadline;
    uint32_t operation,handle,length;
    int32_t result;
    uint8_t payload[REIST_APP_TCP_BYTES];
} reist_app_tcp_request;
typedef struct {
    uint32_t handle,state,send_unacknowledged,send_next,receive_next,initial_sequence;
    uint32_t peer_window,peer_mss,receive_head,receive_count,peer_fin,retransmissions;
    uint32_t srtt8,rttvar4,rto_ms,tx_retries;
    uint64_t sent_at,retry_at;
    uint32_t tx_start,tx_end,tx_length,tx_acked,tx_flags,tx_retransmitted;
    uint32_t local_port;
    int32_t error;
    uint8_t peer_mac[6];
    uint16_t reserved;
    uint32_t window_sequence,window_ack;
    uint8_t receive[REIST_APP_TCP_RECEIVE];
} reist_app_tcp_socket;
typedef struct {
    uint64_t root,service,last_ms,last_epoch,last_application,sequence;
    uint32_t active,issued;
    reist_app_tcp_grant grant;
    reist_app_tcp_request pending;
    reist_app_tcp_socket sockets[REIST_APP_TCP_SOCKETS];
} reist_app_tcp_state;
_Static_assert(sizeof(reist_app_tcp_grant)==64,"TCP grant v1");
_Static_assert(sizeof(reist_app_tcp_request)==608,"TCP request v1");
_Static_assert(sizeof(reist_app_tcp_socket)==2176,"TCP fixed TCB and receive ring");
_Static_assert(sizeof(reist_app_tcp_state)==9432,"TCP fixed application table");
uint16_t reist_app_tcp_port_base(uint64_t application);
int reist_app_tcp_init(reist_app_tcp_state *,uint64_t root,uint64_t service,uint64_t now);
int reist_app_tcp_grant_set(reist_app_tcp_state *,const reist_app_tcp_grant *,uint64_t now);
void reist_app_tcp_revoke(reist_app_tcp_state *);
/* 0 completed with result in reply; 1 admitted IO; negative admission failure. */
int reist_app_tcp_begin(reist_app_tcp_state *,const reist_app_tcp_request *,reist_app_tcp_request *,uint64_t now);
int reist_app_tcp_finish(reist_app_tcp_state *,const reist_app_tcp_request *,reist_app_tcp_request *,int wire_result,uint64_t now);
int reist_app_tcp_exchange(reist_app_tcp_state *,reist_net_protocol *,const reist_net_io *,const reist_app_tcp_request *,reist_app_tcp_request *);
int reist_app_tcp_operand(int argc,const char *const *argv,reist_app_tcp_grant *);
#endif
