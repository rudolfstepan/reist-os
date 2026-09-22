#ifndef REIST_X64_NETWORK_SESSION_H
#define REIST_X64_NETWORK_SESSION_H
#include <stdint.h>
#include <x86os.h>

/* Private Ring3 control plane; public network-control v2 remains unchanged. */
#define REIST_NET_FRAME 1514U
#define REIST_NET_OPERATION_MS 2000U
typedef struct {
    uint64_t epoch,sequence,last_ms;
    uint32_t ip,mask,gateway,configured;
    uint8_t mac[6],reserved[2];
} reist_net_protocol;
typedef struct {
    void *context;
    uint64_t (*now)(void *);
    int (*sleep)(void *,unsigned);
    int (*send)(void *,const uint8_t *,unsigned,uint64_t);
    int (*receive)(void *,uint8_t *,unsigned,uint64_t);
} reist_net_io;
int reist_net_protocol_init(reist_net_protocol *,const uint8_t mac[6],uint64_t epoch);
int reist_net_protocol_control(reist_net_protocol *,const x86os_network_control_request_t *,const reist_net_io *);

/* IPC-v2 bulk carries one fully zero-padded, generation-scoped record. */
enum { REIST_NET_INIT=1,REIST_NET_READY,REIST_NET_CONTROL,REIST_NET_RESULT,
       REIST_NET_TX,REIST_NET_RX,REIST_NET_HEALTH,REIST_NET_BIND,REIST_NET_HELLO };
#ifdef REIST_NATIVE_APP_NETWORK
enum { REIST_NET_APP_GRANT=10,REIST_NET_APP_REQUEST,REIST_NET_APP_REVOKE };
#ifdef REIST_NATIVE_APP_TCP
enum { REIST_NET_TCP_GRANT=13,REIST_NET_TCP_REQUEST,REIST_NET_TCP_REVOKE };
#define REIST_NET_LAST REIST_NET_TCP_REVOKE
#else
#define REIST_NET_LAST REIST_NET_APP_REVOKE
#endif
#else
#define REIST_NET_LAST REIST_NET_HELLO
#endif
typedef struct {
    uint32_t version,size,type,length;
    uint64_t epoch,sequence,owner,deadline_ms;
    int32_t result;
    uint32_t reserved;
    uint64_t reserved2;
    uint8_t payload[1536];
} reist_net_message;
_Static_assert(sizeof(reist_net_message)==1600,"native network internal wire v1");
typedef struct {
    uint64_t owner,peer,epoch,sent,received,last_ms;
    uint32_t endpoint,failed;
} reist_net_channel;
typedef struct {
    uint64_t driver,stack,device_epoch;
    uint32_t endpoint,reserved;
} reist_net_binding;
int reist_net_channel_init(reist_net_channel *,uint32_t,uint64_t,uint64_t,uint64_t);
int reist_net_encode(reist_net_channel *,reist_net_message *,unsigned,const void *,unsigned,int,uint64_t,uint64_t);
int reist_net_decode(reist_net_channel *,const reist_net_message *,uint64_t);
void reist_net_zero(void *,unsigned);
void reist_net_copy(void *,const void *,unsigned);
/* Native transport lives behind a build selector so host tests execute only
 * the pure admission code above. A failed send is terminal for that channel. */
#ifdef REIST_NATIVE_NETWORK_SESSION
uint64_t reist_net_now(void);
int reist_net_pause(unsigned);
int reist_net_send(reist_net_channel *,reist_net_message *);
int reist_net_receive(reist_net_channel *,reist_net_message *,unsigned);
int reist_net_startup(reist_net_channel *,int,char **,unsigned,uint64_t *,unsigned *);
#endif
#endif
