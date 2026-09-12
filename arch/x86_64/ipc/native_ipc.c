#define REIST_NATIVE_IPC_PRIMITIVES
#include "native_ipc.h"
#include "platform.h"
#ifndef REIST_NATIVE_IPC_HOST_TEST
#include "arch/x86/include/interrupt.h"
_Noreturn void reist_native_ipc_fault(void) {
    __asm__ volatile("ud2"); /* Existing trusted-kernel fatal boundary. */
    __builtin_unreachable();
}
#endif

static uint64_t current_tick;
/* These are fault-detection words, not logical booleans: prevent whole-TU
 * optimization from narrowing/re-encoding the stored32-bit complement. */
static volatile uint32_t initialized,entered;
static volatile uint32_t initialized_inverse=UINT32_MAX;
static Process clients[4];
static uint32_t retired[4];
typedef struct {
    native_ipc_request_t request;
    uint32_t generation,state; /*0 empty,1 deadline-wait,2 ready-for-copyout */
} Pending;
static Pending pending[4];
static critical_object_t client_guards[4][2],pending_guards[4][4];
static critical_object_t retired_guard;
_Static_assert(sizeof(Process)<=128 && sizeof(Pending)<=256,"bounded IPC snapshots");

void native_ipc_require(bool ok) { if(!ok) reist_native_ipc_fault(); }
static void serialized(void) {
#ifndef REIST_NATIVE_IPC_HOST_TEST
    native_ipc_require(!irq_enabled());
#endif
}
uint32_t native_ipc_lock(spinlock_t *lock) {
    serialized();native_ipc_require(lock && lock->held==0);
    lock->held=1;return 0;
}
void native_ipc_unlock(spinlock_t *lock,uint32_t flags) {
    serialized();native_ipc_require(lock && lock->held==1 && flags==0);
    lock->held=0;
}
uint64_t pit_monotonic_ms(void) { return current_tick*10; }
void wait_queue_init(wait_queue_t *q) {
    native_ipc_require(q!=NULL);q->head=NULL;q->tail=NULL;
}
int native_critical_init(critical_object_t *o,uint32_t v,const void *p,size_t n) {
    serialized();native_ipc_require(o && !o->publication_lock);
    int result=critical_object_init(o,v,p,n);
    native_ipc_require(result==0);return result;
}
int native_critical_update(critical_object_t *o,uint32_t v,const void *p,size_t n,
                            critical_object_validator_t valid) {
    serialized();native_ipc_require(o && !o->publication_lock);
    int result=critical_object_update(o,v,p,n,valid);
    native_ipc_require(result==0);return result;
}
critical_read_result_t native_critical_read(critical_object_t *o,uint32_t v,void *p,size_t n,
                                            size_t *length,critical_object_validator_t valid) {
    serialized();native_ipc_require(o && !o->publication_lock);
    critical_read_result_t result=critical_object_read(o,v,p,n,length,valid);
    native_ipc_require(result>=0);return result;
}
static bool chunk(const void *p,size_t n) { return p && n && n<=64; }
static void protect(critical_object_t *guards,const void *data,size_t size,bool init) {
    const unsigned char *p=data;
    for(size_t off=0;off<size;off+=64,guards++) {
        size_t n=size-off<64?size-off:64;
        if(init) native_critical_init(guards,1,p+off,n);
        else native_critical_update(guards,1,p+off,n,chunk);
    }
}
static void verify(critical_object_t *guards,const void *data,size_t size) {
    const unsigned char *p=data;unsigned char copy[64];
    for(size_t off=0;off<size;off+=64,guards++) {
        size_t n=size-off<64?size-off:64,length=0;
        native_critical_read(guards,1,copy,n,&length,chunk);
        native_ipc_require(length==n);
        for(size_t i=0;i<n;i++) native_ipc_require(copy[i]==p[off+i]);
    }
    memset(copy,0,sizeof(copy));
}
static void check_all(void) {
    verify(&retired_guard,retired,sizeof(retired));
    for(unsigned i=0;i<4;i++) {
        verify(client_guards[i],&clients[i],sizeof(clients[i]));
        verify(pending_guards[i],&pending[i],sizeof(pending[i]));
        native_ipc_require(pending[i].state<=2);
        if(pending[i].state) native_ipc_require(clients[i].is_running &&
                pending[i].generation==clients[i].generation);
    }
}
static void seal_all(bool init) {
    protect(&retired_guard,retired,sizeof(retired),init);
    for(unsigned i=0;i<4;i++) {
        protect(client_guards[i],&clients[i],sizeof(clients[i]),init);
        protect(pending_guards[i],&pending[i],sizeof(pending[i]),init);
    }
}
static int transfer(unsigned slot,native_ipc_request_t *r) {
    if(r->number==50 || r->number==53)
        return ipc_send_timeout(&clients[slot],(ipc_handle_t)r->a0,&r->message,0);
    return ipc_receive_timeout(&clients[slot],(ipc_handle_t)r->a0,&r->message,0);
}
static uint64_t pump(bool deadlines_only) {
    uint64_t ready=0;
    /* At most four completions. A completion can free space for a preceding
     * sender, hence four bounded passes, never a userspace-facing spin. */
    for(unsigned pass=0;pass<(deadlines_only?1U:4U);pass++) {
        bool progress=false;
        for(unsigned s=0;s<4;s++) {
            Pending *p=&pending[s];
            if(p->state!=1) continue;
            if(deadlines_only && current_tick<p->request.deadline) continue;
            int result=current_tick>=p->request.deadline ? -110 : transfer(s,&p->request);
            if(result==-11) continue;
            native_ipc_require(result!=IPC_EINTEGRITY);
            p->request.result=result==-9 ? -32 : result;
            p->state=2;ready|=UINT64_C(1)<<s;progress=true;
        }
        if(!progress) break;
    }
    return ready;
}
static int dispatch_request(unsigned slot,native_ipc_request_t *r) {
    if(r->number<49 || r->number>58 || r->number==56 || r->number==57 || r->a3)
        return -22;
    if(r->number!=49 && r->a0>UINT32_MAX) return -22;
    if(r->number==49) {
        if(r->a1 || r->a2) return -22;
        return ipc_create(&clients[slot],&r->handle);
    }
    if(r->number==52 || r->number==58) {
        if(r->a1 || r->a2) return -22;
        return r->number==52 ? ipc_close(&clients[slot],(ipc_handle_t)r->a0)
                            : ipc_release(&clients[slot],(ipc_handle_t)r->a0);
    }
    if(r->number==55) {
        if(!r->a1 || r->a1>INT32_MAX || r->a2>UINT32_MAX) return -22;
        for(unsigned s=0;s<4;s++) if(clients[s].is_running && (uint64_t)clients[s].pid==r->a1)
            return ipc_delegate(&clients[slot],(ipc_handle_t)r->a0,&clients[s],(uint32_t)r->a2);
        return -3; /* ESRCH: generation-valued PID no longer live. */
    }
    uint64_t timeout=(r->number==50 || r->number==51)?1000:r->a2;
    if(timeout>UINT32_MAX || ((r->number==50 || r->number==51) && r->a2)) return -22;
    uint64_t deadline=current_tick+(timeout+9)/10;
    if(deadline>=256) return -22; /* Admit before any queue effect. */
    /* The shared operations own message validation and errno precedence. */
    int result=transfer(slot,r);
    if(result!=-11 || !timeout) return result;
    r->deadline=deadline;r->result=NATIVE_IPC_PENDING;
    pending[slot].request=*r;pending[slot].generation=clients[slot].generation;
    pending[slot].state=1;
    return NATIVE_IPC_PENDING;
}
uint64_t reist_native_ipc(uint64_t operation,uint64_t slot,uint64_t generation,
                          uint64_t tick,native_ipc_request_t *r) {
    serialized();
    uint32_t init_snapshot=initialized;
    native_ipc_require(init_snapshot<=1 && initialized_inverse==~init_snapshot);
    native_ipc_require(!entered && slot<4 && generation && generation<=INT32_MAX &&
                        tick<256 && r && ((uintptr_t)r&7)==0 && operation<=NATIVE_IPC_END);
    entered=1;
    if(!init_snapshot) {
        native_ipc_require(operation==NATIVE_IPC_BIND);
        ipc_init();seal_all(true);initialized=1;initialized_inverse=~initialized;
    }
    check_all();current_tick=tick;r->ready=0;
    Process *p=&clients[slot];
    if(operation==NATIVE_IPC_BIND) {
        native_ipc_require(!p->is_running && !pending[slot].state && generation>retired[slot]);
        memset(p,0,sizeof(*p));p->pid=(int)generation;p->generation=(uint32_t)generation;p->is_running=true;
    } else if(operation==NATIVE_IPC_END) {
        ipc_resource_stats_t stats;
        native_ipc_require(ipc_resource_stats(&stats)==0 && !stats.active_endpoints &&
                            !stats.active_capabilities && !stats.queued_messages);
        for(unsigned s=0;s<4;s++) native_ipc_require(!clients[s].is_running && !pending[s].state);
    } else if(operation==NATIVE_IPC_PUMP) {
        r->ready=pump(true);
    } else {
        native_ipc_require(p->is_running && p->generation==generation);
        if(operation==NATIVE_IPC_REQUEST) {
            native_ipc_require(!pending[slot].state);
            r->deadline=0;r->handle=0;r->result=dispatch_request((unsigned)slot,r);
            native_ipc_require(r->result!=IPC_EINTEGRITY);
            if(r->result!=NATIVE_IPC_PENDING) r->ready=pump(false);
        } else if(operation==NATIVE_IPC_TAKE) {
            r->result=NATIVE_IPC_PENDING;
            if(pending[slot].state==2) {
                *r=pending[slot].request;r->ready=0;
                memset(&pending[slot],0,sizeof(pending[slot]));
            } else native_ipc_require(!pending[slot].state);
        } else if(operation==NATIVE_IPC_REAP) {
            memset(&pending[slot],0,sizeof(pending[slot]));
            ipc_process_cleanup(p->pid,p->generation);
            retired[slot]=p->generation;memset(p,0,sizeof(*p));r->ready=pump(false);
        }
    }
    seal_all(false);entered=0;return 1;
}
