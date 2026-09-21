/* Native Ring3 graphical role protocol. Surface-v6 remains the client ABI. */
#ifndef REIST_X64_GRAPHICAL_SESSION_H
#define REIST_X64_GRAPHICAL_SESSION_H
#include <stdint.h>
#include <stddef.h>
#include <reist/x86_64/service_session.h>
#define REIST_GRAPHICAL_ROLES 4U
#define REIST_GRAPHICAL_PREPARED_HASH_BYTES 262240U
#define REIST_GRAPHICAL_HEALTH_MS 1000U
#define REIST_GRAPHICAL_START_MS 3000U
#define REIST_GRAPHICAL_RETIRE_MS 5000U
enum { REIST_GRAPHICAL_OFF,REIST_GRAPHICAL_STARTING,REIST_GRAPHICAL_LIVE,
       REIST_GRAPHICAL_FENCING,REIST_GRAPHICAL_REAPED,REIST_GRAPHICAL_DEGRADED };
enum { REIST_GRAPHICAL_FENCE_CHANNEL=1,REIST_GRAPHICAL_FENCE_TERMINAL=2,
       REIST_GRAPHICAL_FENCE_DISPLAY=4,REIST_GRAPHICAL_FENCE_INPUT=8,
       REIST_GRAPHICAL_FENCE_ALL=15 };
enum { REIST_GRAPHICAL_HELLO=1,REIST_GRAPHICAL_BIND,REIST_GRAPHICAL_BOUND,
       REIST_GRAPHICAL_READY,REIST_GRAPHICAL_HEALTH,REIST_GRAPHICAL_STOP,
       REIST_GRAPHICAL_FAILED,REIST_GRAPHICAL_CLIENT_REAPED };
typedef struct {
    uint32_t version,size,type,role;
    uint64_t epoch,sequence,owner;
    uint32_t endpoint,flags;
    uint64_t value,reserved;
} reist_graphical_control;
_Static_assert(sizeof(reist_graphical_control)==64,"graphical control-v1");
typedef struct {
    /* health_ms is the fixed bind instant during STARTING (3000ms), then
     * the most recent accepted LIVE heartbeat (1000ms). No renewal on bind. */
    uint64_t owner,sequence,health_ms,retire_end;
    uint32_t phase,fences;
} reist_graphical_role;
typedef struct {
    uint64_t root,epoch,last_ms,start_end;
    uint32_t phase,reserved;
    reist_graphical_role roles[REIST_GRAPHICAL_ROLES];
    uint32_t restart_blocked,restart_padding;
} reist_graphical_state;
typedef struct { uint64_t start_ms,last_ms; uint32_t used,failed; } reist_graphical_rate;

int reist_graphical_init(reist_graphical_state *,uint64_t root,uint64_t now);
/* Shares the unchanged root budget; exhaustion latches only this GUI domain.
 * A previously published parent degraded latch is never cleared. */
int reist_graphical_restart(reist_graphical_state *,reist_session_policy_v1 *,uint64_t now);
int reist_graphical_begin(reist_graphical_state *,uint64_t now);
int reist_graphical_bind(reist_graphical_state *,unsigned role,uint64_t owner,uint64_t now);
int reist_graphical_ready(reist_graphical_state *,uint64_t epoch,unsigned proof,uint64_t now);
int reist_graphical_heartbeat(reist_graphical_state *,unsigned role,uint64_t owner,
                              uint64_t epoch,uint64_t sequence,uint64_t now);
/* Bitmask of expired roles, negative error for an invalid/regressed clock. */
int reist_graphical_expired(const reist_graphical_state *,uint64_t now);
int reist_graphical_isolate(reist_graphical_state *,unsigned role,uint64_t now);
int reist_graphical_fenced(reist_graphical_state *,unsigned role,uint64_t owner,
                           unsigned fences,uint64_t now);
int reist_graphical_reaped(reist_graphical_state *,unsigned role,uint64_t owner,uint64_t now);
int reist_graphical_finish(reist_graphical_state *,unsigned degraded,uint64_t now);
int reist_graphical_charge(reist_graphical_rate *,uint64_t now,unsigned limit);

/* Callbacks allow host tests to execute the exact bounded hash admission. */
typedef struct {
    void *context;
    uint64_t (*clock_ms)(void *);
    int (*sleep_ms)(void *,unsigned);
} reist_graphical_hash_ops;
int reist_graphical_hash_admit(const void *prepared,size_t bytes,
    const unsigned char expected[32],const reist_graphical_hash_ops *ops);
#endif
