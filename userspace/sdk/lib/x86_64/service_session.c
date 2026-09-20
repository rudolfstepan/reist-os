#include <reist/x86_64/service_session.h>
#include <stddef.h>
#define SESSION_LAST_MS ((UINT64_C(1)<<63)-10001)
static void session_copy(void *to,const void *from,size_t bytes) {
    volatile unsigned char *out=to;const unsigned char *in=from;
    for(size_t n=0;n<bytes;n++)out[n]=in[n];
}
static int session_valid(const reist_session_policy_v1 *p,uint64_t now) {
    return p->version==1 && p->struct_size==sizeof(*p) && p->owner &&
        p->owner<=0x7fffffff && now<=SESSION_LAST_MS && now>=p->previous_ms &&
        p->io_anchor_ms<=p->previous_ms && p->restart_anchor_ms<=p->previous_ms &&
        p->operations<=4096 && p->received<=1024 && p->written<=16384 && p->restarts<=2 &&
        p->operations<=p->total_operations && p->received<=p->total_received &&
        p->written<=p->total_written && p->restarts<=p->total_restarts &&
        p->degraded<=1 && !p->reserved;
}
int reist_session_policy_init(reist_session_policy_v1 *p,uint64_t owner,uint64_t now) {
    if(!p || !owner || owner>0x7fffffff || now>SESSION_LAST_MS)return -22;
    const unsigned char *old=(const void *)p;
    for(size_t n=0;n<sizeof(*p);n++)if(old[n])return -22;
    /* The admitted object is completely zero. Explicit stores avoid an
     * implicit libc copy/zero dependency in the freestanding SDK. */
    p->version=1;p->struct_size=sizeof(*p);p->owner=owner;
    p->previous_ms=now;p->io_anchor_ms=now;p->restart_anchor_ms=now;
    return 0;
}
int reist_session_policy_charge(reist_session_policy_v1 *p,uint64_t now,
    uint32_t operations,uint32_t received,uint32_t written) {
    if(!p || operations>4096 || received>1024 || written>16384)return -22;
    if(!session_valid(p,now))return -5;
    reist_session_policy_v1 next;session_copy(&next,p,sizeof(next));
    uint64_t anchor=now-(now-next.io_anchor_ms)%1000;
    if(anchor!=next.io_anchor_ms) {
        next.io_anchor_ms=anchor;next.operations=next.received=next.written=0;
    }
    if(operations>4096-next.operations || received>1024-next.received || written>16384-next.written)return -110;
    if(operations>UINT64_MAX-next.total_operations || received>UINT64_MAX-next.total_received ||
       written>UINT64_MAX-next.total_written)return -5;
    next.operations+=operations;next.received+=received;next.written+=written;
    next.total_operations+=operations;next.total_received+=received;next.total_written+=written;
    next.previous_ms=now;session_copy(p,&next,sizeof(next));return 0;
}
int reist_session_policy_restart(reist_session_policy_v1 *p,uint64_t now) {
    if(!p)return -22;
    if(!session_valid(p,now))return -5;
    if(p->degraded)return -11;
    reist_session_policy_v1 next;session_copy(&next,p,sizeof(next));
    uint64_t anchor=now-(now-next.restart_anchor_ms)%10000;
    if(anchor!=next.restart_anchor_ms){next.restart_anchor_ms=anchor;next.restarts=0;}
    if(next.restarts==2) {
        next.degraded=1;next.previous_ms=now;session_copy(p,&next,sizeof(next));return -11;
    }
    if(next.total_restarts==UINT64_MAX)return -5;
    ++next.restarts;++next.total_restarts;next.previous_ms=now;
    session_copy(p,&next,sizeof(next));return 0;
}

static int service_ops(const reist_service_session_ops *o) {
    return o && o->clock && o->endpoint && o->close && o->create && o->delegate &&
        o->pio && o->send && o->receive && o->task;
}
static int service_valid(const reist_service_session_v1 *s) {
    if(!s || s->version!=1 || s->struct_size!=sizeof(*s) || !s->owner ||
       s->owner>0x7fffffff || s->layout>4 || s->phase>REIST_SESSION_ISOLATED || s->bound>1)return 0;
    if(s->driver && ((uint32_t)s->driver!=2 || !(s->driver>>32) || s->driver>INT64_MAX))return 0;
    if(s->filesystem && ((uint32_t)s->filesystem!=3 || !(s->filesystem>>32) || s->filesystem>INT64_MAX))return 0;
    if(s->bound && !s->driver)return 0;
    if(s->phase==REIST_SESSION_COLD && (s->driver || s->filesystem || s->bound ||
        s->driver_endpoint || s->filesystem_endpoint || s->deadline_ms || s->sectors))return 0;
    if(s->phase==REIST_SESSION_HEALTHY && (!s->driver || !s->filesystem || !s->bound ||
        !s->driver_endpoint || !s->filesystem_endpoint || s->driver_endpoint==s->filesystem_endpoint ||
        !s->deadline_ms || s->sectors!=(s->layout==0?2880U:s->layout==1?70000U:256U)))return 0;
    return 1;
}
int reist_service_session_init(reist_service_session_v1 *s,uint64_t owner,unsigned layout) {
    if(!s || !owner || owner>0x7fffffff || layout>4)return -22;
    const unsigned char *p=(const void*)s;
    for(size_t n=0;n<sizeof(*s);n++)if(p[n])return -22;
    s->version=1;s->struct_size=sizeof(*s);s->owner=owner;s->layout=layout;return 0;
}
static int service_remaining(reist_service_session_v1 *s,const reist_service_session_ops *o,uint64_t deadline) {
    uint64_t now=o->clock(o->context);
    if(now>SESSION_LAST_MS || now<s->previous_ms)return -5;
    s->previous_ms=now;
    if(now>=deadline)return -110;
    return (int)(deadline-now>1000?1000:deadline-now);
}
static int service_reap(const reist_service_session_ops *o,uint64_t handle) {
    int64_t status=o->task(o->context,3,handle,0);
    if(status)return -117;
    status=o->task(o->context,2,handle,1000);
    if(status<0 || (uint64_t)status>>32>3)return -117;
    return 0;
}
int reist_service_session_retire(reist_service_session_v1 *s,const reist_service_session_ops *o) {
    if(!service_ops(o) || !service_valid(s))return -22;
    if(s->phase==REIST_SESSION_COLD)return 0;
    if(s->retirements==UINT64_MAX)return -117;
    s->phase=REIST_SESSION_ISOLATED;
    /* A never-bound candidate has never received device authority. Once bind
     * succeeds, do not clear that fact until physical fencing is confirmed. */
    if(s->bound) {
        if(o->pio(o->context,s->driver,5))return -117;
        s->bound=0;
    }
    if(s->filesystem) {
        if(service_reap(o,s->filesystem))return -117;
        s->last_filesystem=s->filesystem;s->filesystem=0;
    }
    if(s->driver) {
        if(service_reap(o,s->driver))return -117;
        s->last_driver=s->driver;s->driver=0;
    }
    if(s->filesystem_endpoint) {
        if(o->close(o->context,s->filesystem_endpoint))return -117;
        s->filesystem_endpoint=0;
    }
    if(s->driver_endpoint) {
        if(o->close(o->context,s->driver_endpoint))return -117;
        s->driver_endpoint=0;
    }
    ++s->retirements;s->deadline_ms=0;s->sectors=0;s->phase=REIST_SESSION_COLD;return 0;
}
int reist_service_session_open(reist_service_session_v1 *s,const reist_service_session_ops *o,
    uint64_t deadline,unsigned fault_mode) {
    if(!service_ops(o) || !service_valid(s) || fault_mode>7)return -22;
    if(s->phase!=REIST_SESSION_COLD)return -16;
    uint64_t now=o->clock(o->context);
    if(now>SESSION_LAST_MS || now<s->previous_ms)return -5;
    if(deadline<=now)return -110;
    if(deadline-now>3000)return -22;
    if(s->starts==UINT64_MAX)return -75;
    s->previous_ms=now;++s->starts;s->phase=REIST_SESSION_STARTING;
    int result=o->endpoint(o->context,&s->driver_endpoint);
    if(result)goto rollback;
    if(!s->driver_endpoint)return -117;
    result=o->endpoint(o->context,&s->filesystem_endpoint);
    if(result)goto rollback;
    if(!s->filesystem_endpoint || s->filesystem_endpoint==s->driver_endpoint)return -117;
    unsigned options=(s->layout<<8)|fault_mode;
    int64_t child=o->create(o->context,2,s->driver_endpoint,options);
    if(child<0){if(child<-4095)return -117;result=(int)child;goto rollback;}
    if(!child || (uint32_t)child!=2 || (uint64_t)child<=s->last_driver || (uint64_t)child>>32<=s->owner)return -117;
    s->driver=(uint64_t)child;
    result=o->delegate(o->context,s->driver_endpoint,s->driver>>32);if(result)goto rollback;
    child=o->create(o->context,3,s->filesystem_endpoint,options);
    if(child<0){if(child<-4095)return -117;result=(int)child;goto rollback;}
    if(!child || (uint32_t)child!=3 || (uint64_t)child<=s->last_filesystem || (uint64_t)child>>32<=s->owner)return -117;
    s->filesystem=(uint64_t)child;
    result=o->delegate(o->context,s->filesystem_endpoint,s->filesystem>>32);if(result)goto rollback;
    result=o->pio(o->context,s->driver,1);if(result)goto rollback;
    s->bound=1;
    reist_session_control c={s->driver,s->filesystem,0,0,0,0,1,0,0};
    result=service_remaining(s,o,deadline);if(result<0)goto rollback;
    result=o->send(o->context,s->driver_endpoint,&c,(unsigned)result);if(result)goto rollback;
    result=service_remaining(s,o,deadline);if(result<0)goto rollback;
    result=o->receive(o->context,s->driver_endpoint,&c,(unsigned)result);if(result)goto rollback;
    now=o->clock(o->context);
    if(now<s->previous_ms || now>SESSION_LAST_MS){result=-5;goto rollback;}
    s->previous_ms=now;
    if(c.owner!=s->driver || c.peer!=s->filesystem || c.phase!=2 || c.result || c.reserved ||
       !c.request || !c.reply || c.request==c.reply || c.deadline<=now || c.deadline-now>2800 ||
       c.sectors!=(s->layout==0?2880U:s->layout==1?70000U:256U)){result=-71;goto rollback;}
    uint64_t service_deadline=c.deadline;uint32_t request=c.request,reply=c.reply,sectors=c.sectors;
    c.owner=s->filesystem;c.peer=s->driver;c.phase=3;
    result=service_remaining(s,o,deadline);if(result<0)goto rollback;
    result=o->send(o->context,s->filesystem_endpoint,&c,(unsigned)result);if(result)goto rollback;
    result=service_remaining(s,o,deadline);if(result<0)goto rollback;
    result=o->receive(o->context,s->filesystem_endpoint,&c,(unsigned)result);if(result)goto rollback;
    if(c.owner!=s->filesystem || c.peer!=s->driver || c.phase!=4 || c.reserved ||
       c.request!=request || c.reply!=reply || c.sectors!=sectors || c.deadline!=service_deadline){result=-71;goto rollback;}
    if(c.result){result=c.result>=-4095 && c.result<0?c.result:-71;goto rollback;}
    result=service_remaining(s,o,deadline<service_deadline?deadline:service_deadline);if(result<0)goto rollback;
    s->deadline_ms=service_deadline;s->sectors=sectors;s->phase=REIST_SESSION_HEALTHY;return 0;
rollback:
    if(result>=0)result=-71;
    return reist_service_session_retire(s,o)?-117:result;
}
