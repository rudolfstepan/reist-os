/* Private Ring3 session policy v1. No kernel authority follows from this data. */
#ifndef REIST_X86_64_SERVICE_SESSION_H
#define REIST_X86_64_SERVICE_SESSION_H
#include <stdint.h>
typedef struct {
    uint32_t version,struct_size;
    uint64_t owner,previous_ms,io_anchor_ms,restart_anchor_ms;
    uint64_t total_operations,total_received,total_written,total_restarts;
    uint32_t operations,received,written,restarts,degraded,reserved;
} reist_session_policy_v1;
typedef char reist_session_policy_size_check[sizeof(reist_session_policy_v1)==96?1:-1];
/* Initialize previously zeroed state exactly once per owner generation. */
int reist_session_policy_init(reist_session_policy_v1 *,uint64_t owner,uint64_t now_ms);
/* Single publication, no credit accumulation. Every error leaves state intact. */
int reist_session_policy_charge(reist_session_policy_v1 *,uint64_t now_ms,
    uint32_t operations,uint32_t received,uint32_t written);
/* Charge one automatic recovery. Exhaustion alone publishes degraded=1;
 * later calls never clear that latch, including after a window boundary. */
int reist_session_policy_restart(reist_session_policy_v1 *,uint64_t now_ms);

/* Existing finite FS/ATA control wire, not a new protocol or device grant. */
typedef struct {
    uint64_t owner,peer,deadline;
    uint32_t request,reply,sectors,phase;
    int32_t result;uint32_t reserved;
} reist_session_control;
typedef char reist_session_control_size_check[sizeof(reist_session_control)==48?1:-1];
enum { REIST_SESSION_COLD=0,REIST_SESSION_STARTING,REIST_SESSION_HEALTHY,
       REIST_SESSION_ISOLATED };
typedef struct {
    void *context;
    uint64_t (*clock)(void *);
    int (*endpoint)(void *,uint32_t *);
    int (*close)(void *,uint32_t);
    int64_t (*create)(void *,unsigned role,uint32_t endpoint,unsigned options);
    int (*delegate)(void *,uint32_t,uint64_t);
    int (*pio)(void *,uint64_t,unsigned);
    int (*send)(void *,uint32_t,const reist_session_control *,unsigned);
    int (*receive)(void *,uint32_t,reist_session_control *,unsigned);
    int64_t (*task)(void *,unsigned,uint64_t,unsigned);
} reist_service_session_ops;
typedef struct {
    uint32_t version,struct_size,phase,layout;
    uint64_t owner,driver,filesystem,last_driver,last_filesystem;
    uint64_t previous_ms,deadline_ms,starts,retirements;
    uint32_t driver_endpoint,filesystem_endpoint,bound,sectors;
} reist_service_session_v1;
/* Zero-init once; live state cannot be reinitialized or rebound in place. */
int reist_service_session_init(reist_service_session_v1 *,uint64_t owner,unsigned layout);
/* Exactly one construction transaction. No hidden retry or policy reset.
 * Ordinary failure returns only after rollback. -117 means containment is
 * uncertain: caller must exit, never try to repair/reopen this state. */
int reist_service_session_open(reist_service_session_v1 *,const reist_service_session_ops *,
    uint64_t deadline_ms,unsigned fault_mode);
/* Physical fence precedes every cancel/reap. Idempotent only after successful
 * complete cleanup. Historical handles and cumulative counters survive. */
int reist_service_session_retire(reist_service_session_v1 *,const reist_service_session_ops *);
/* Profile2 changes only local admission, not rights or restart/creation policy.
 * Existing retirement handles both admitted versions using the same fencing.
 * Startup has its own<=1000ms end inside the original whole-file deadline. */
typedef reist_service_session_v1 reist_service_session_v2;
int reist_service_session_init_v2(reist_service_session_v2 *,uint64_t owner,unsigned layout);
int reist_service_session_open_v2(reist_service_session_v2 *,const reist_service_session_ops *,
    uint64_t startup_deadline_ms,uint64_t capture_deadline_ms,unsigned fault_mode);
#endif
