#ifndef REIST_X64_DESKTOP_PLATFORM_H
#define REIST_X64_DESKTOP_PLATFORM_H
#include <reist/x86_64/desktop_services.h>
#include <reist/x86_64/graphical_session.h>
#include <reist/x86_64/input.h>
/* Persistent input-v2 from the existing supervised PS/2 role. Fixed queues;
 * no direct device access. Keyboard bytes use ASCII/ANSI CSI conventions. */
typedef struct {
    uint64_t owner,driver,epoch,sequence,previous,healthy_ms;
    reist_graphical_rate rate;
    uint32_t phase,mouse_head,mouse_count,key_head,key_count;
    x86os_mouse_event_t mice[32];
    unsigned char keys[64];
    /* Private FIFO ordering; ANSI bytes from one event share its sequence. */
    uint64_t mouse_sequence[32],key_sequence[64];
} reist_desktop_input_state;
int reist_desktop_input_bind(reist_desktop_input_state *,uint64_t owner,uint64_t driver,uint64_t epoch,uint64_t now);
int reist_desktop_input_push(reist_desktop_input_state *,const reist_input_event_v1 *,uint64_t now);
int reist_desktop_input_mouse(reist_desktop_input_state *,x86os_mouse_event_t *);
int reist_desktop_input_key(reist_desktop_input_state *);
int reist_desktop_input_peek_key(reist_desktop_input_state *);
/* Private compositor SDK adapter. Callbacks are startup-owned, never client
 * pointers received over IPC. Pump is non-reentrant and does no service RPC. */
struct reist_desktop_channels;
typedef struct {
    reist_desktop_service_client *service;
    void *context;
    int64_t (*call)(void *,unsigned,uint64_t,uint64_t,uint64_t);
    int (*pump)(void *);
    int (*mouse)(void *,x86os_mouse_event_t *);
    int (*key)(void *);
    int (*report)(void *,unsigned,unsigned);
    void (*failed)(void *,int);
    struct reist_desktop_channels *channels;
} reist_desktop_platform_config;
int reist_desktop_platform_attach(const reist_desktop_platform_config *);
/* Publish both startup children only after separate live supervisor replies. */
int reist_desktop_platform_adopt(const uint64_t owners[2]);
int reist_desktop_platform_replace(uint64_t old_owner,uint64_t new_owner);
void reist_desktop_platform_detach(void);
int reist_desktop_platform_pump(void);
struct reist_desktop_channels *reist_desktop_platform_channels(void);
struct desktop_surface_runtime;
int reist_desktop_frontend_adopt(struct desktop_surface_runtime *);
struct desktop_surface_manager;
struct desktop_wm;
int reist_desktop_frontend_recover(struct desktop_surface_runtime *,struct desktop_surface_manager *);
enum { REIST_DESKTOP_RECOVERY_LIVE, REIST_DESKTOP_RECOVERY_WAIT_REAP,
    REIST_DESKTOP_RECOVERY_REAPED, REIST_DESKTOP_RECOVERY_HELLO,
    REIST_DESKTOP_RECOVERY_WAIT_BIND, REIST_DESKTOP_RECOVERY_BIND,
    REIST_DESKTOP_RECOVERY_APP_HELLO, REIST_DESKTOP_RECOVERY_BOUND,
    REIST_DESKTOP_RECOVERY_WAIT_READY };
/* Startup-only readiness proof; subsequent health supervision remains active. */
int reist_desktop_frontend_presented(const struct desktop_surface_runtime *,const struct desktop_surface_manager *,const struct desktop_wm *);
/* Root handshake must already have established the service and both children.
 * Font is the verified boot asset and remains caller-owned. This transaction
 * owns only its two display buffers; entry owns its normal workspace/lifecycle.
 * Success here is the entry's return status, never a graphical READY proof. */
typedef struct {
    reist_desktop_platform_config platform;
    const unsigned char *font;
    size_t font_bytes;
    uint64_t children[2];
    int (*entry)(int,char **);
} reist_desktop_startup_config;
int reist_desktop_startup_run(const reist_desktop_startup_config *,int,char **);
/* Per-session IPC demultiplexer. Bulk root replies share a channel with
 * graphical control; application health shares each Surface-v6 channel.
 * No service RPC is issued while pumping. All receive operations are polls. */
typedef struct {
    void *context;
    int64_t (*call)(void *,unsigned,uint64_t,uint64_t,uint64_t);
    uint64_t root,desktop,epoch,children[2];
    uint32_t root_endpoint,input_endpoint,application_endpoints[2];
    reist_desktop_input_state *input;
    uint64_t start_deadline_ms;
} reist_desktop_channels_config;
typedef struct reist_desktop_channels {
    reist_desktop_channels_config config;
    unsigned phase,head,count,reply_pending,application_failed[2];
    unsigned application_closed[2];
    unsigned frontend_ready;
    uint64_t previous,health_sequence[2],health_ms[2];
    reist_graphical_rate application_rate[2];
    reist_graphical_control controls[4];
    reist_desktop_service_frame reply;
    unsigned recovery[2],recovery_ready[2];
    uint64_t recovery_old[2],recovery_owner[2],recovery_end[2];
    uint32_t recovery_endpoint[2];
} reist_desktop_channels;
int reist_desktop_channels_recovery_control(reist_desktop_channels *,const reist_graphical_control *,uint64_t);
int reist_desktop_channels_init(reist_desktop_channels *,const reist_desktop_channels_config *,uint64_t);
int reist_desktop_channels_control(reist_desktop_channels *,reist_graphical_control *);
int reist_desktop_channels_send(void *,const reist_desktop_service_frame *);
int reist_desktop_channels_receive(void *,reist_desktop_service_frame *);
int reist_desktop_channels_input(reist_desktop_channels *);
int reist_desktop_channels_surface(reist_desktop_channels *,unsigned,x86os_ipc_message_t *);
typedef struct {
    reist_desktop_channels_config channels;
    reist_desktop_input_state input;
    uint64_t deadline;
    uint32_t mode;
} reist_desktop_handshake_result;
/* Existing graphical role argv/control-v1. Zero result required. Creates only
 * three private endpoints; initial BIND delegation is confirmed before BOUND.
 * The absolute root deadline is never renewed. On failure output is unchanged.
 * Successful caller owns the endpoints and must close them after detaching. */
int reist_desktop_handshake(int,char **,
    int64_t (*)(void *,unsigned,uint64_t,uint64_t,uint64_t),void *,reist_desktop_handshake_result *);
int reist_desktop_handshake_close(reist_desktop_handshake_result *);
int reist_desktop_launch(int,char **,const unsigned char *,size_t,int (*)(int,char **),
    int64_t (*)(void *,unsigned,uint64_t,uint64_t,uint64_t),void *);
#endif
