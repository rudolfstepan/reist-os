/* Pure bounded lifecycle bookkeeping. A successful fence/reap call is made
 * only AFTER the corresponding kernel/IPC operation has been confirmed. */
#include <reist/x86_64/graphical_session.h>
static int valid(const reist_graphical_state *s,uint64_t now) {
    return s && s->root && !(uint32_t)s->root && s->root>>32<=0x7fffffff &&
        s->phase<=REIST_GRAPHICAL_DEGRADED && !s->reserved && now>=s->last_ms &&
        s->restart_blocked<=1 && !s->restart_padding;
}
static int role_owner(unsigned role,uint64_t owner) {
    return role<4 && (uint32_t)owner==4+role && owner>>32 && owner>>32<=0x7fffffff;
}
int reist_graphical_init(reist_graphical_state *s,uint64_t root,uint64_t now) {
    if(!s || !root || (uint32_t)root || root>>32>0x7fffffff)return -22;
    unsigned char *p=(unsigned char*)s;
    for(unsigned n=0;n<sizeof(*s);n++)p[n]=0;
    s->root=root;s->last_ms=now;return 0;
}
int reist_graphical_begin(reist_graphical_state *s,uint64_t now) {
    if(!valid(s,now))return -22;
    if(s->phase==REIST_GRAPHICAL_DEGRADED || s->restart_blocked)return -11;
    if(s->phase!=REIST_GRAPHICAL_OFF)return -16;
    if(s->epoch==UINT64_MAX || now>UINT64_MAX-REIST_GRAPHICAL_START_MS)return -75;
    for(unsigned r=0;r<4;r++)if(s->roles[r].phase!=REIST_GRAPHICAL_OFF &&
        s->roles[r].phase!=REIST_GRAPHICAL_REAPED)return -16;
    ++s->epoch;s->phase=REIST_GRAPHICAL_STARTING;
    s->last_ms=now;s->start_end=now+REIST_GRAPHICAL_START_MS;return 0;
}
static void policy_copy(void *destination,const void *source,size_t bytes) {
    volatile unsigned char *d=destination;const unsigned char *p=source;
    for(size_t n=0;n<bytes;n++)d[n]=p[n];
}
int reist_graphical_restart(reist_graphical_state *s,reist_session_policy_v1 *policy,uint64_t now) {
    if(!valid(s,now) || !policy)return -22;
    if(policy->owner!=s->root>>32)return -116;
    if(s->restart_blocked)return -11;
    if(s->phase!=REIST_GRAPHICAL_OFF && s->phase!=REIST_GRAPHICAL_LIVE)return -16;
    reist_session_policy_v1 proposal;policy_copy(&proposal,policy,sizeof(proposal));
    int r=reist_session_policy_restart(&proposal,now);
    if(r && r!=-11)return r;
    if(r==-11) {
        /* Only the private proposal acquired a new degraded bit. Keep all
         * spent counters/anchors/time, and preserve any OLD parent latch. */
        proposal.degraded=policy->degraded;s->restart_blocked=1;
    }
    policy_copy(policy,&proposal,sizeof(proposal));s->last_ms=now;return r;
}
int reist_graphical_bind(reist_graphical_state *s,unsigned r,uint64_t owner,uint64_t now) {
    if(!valid(s,now)||!role_owner(r,owner))return -22;
    if(s->phase!=REIST_GRAPHICAL_STARTING && !(s->phase==REIST_GRAPHICAL_LIVE&&r>=2))return -16;
    reist_graphical_role *v=&s->roles[r];
    if(v->phase!=REIST_GRAPHICAL_OFF && v->phase!=REIST_GRAPHICAL_REAPED)return -16;
    if(owner>>32<=v->owner>>32)return -116;
    if(now>UINT64_MAX-REIST_GRAPHICAL_START_MS)return -75;
    if(s->phase==REIST_GRAPHICAL_STARTING && now>=s->start_end)return -110;
    v->owner=owner;v->sequence=0;v->health_ms=now;v->retire_end=0;
    v->phase=REIST_GRAPHICAL_STARTING;v->fences=0;s->last_ms=now;return 0;
}
int reist_graphical_ready(reist_graphical_state *s,uint64_t epoch,unsigned proof,uint64_t now) {
    if(!valid(s,now))return -22;
    if(s->phase!=REIST_GRAPHICAL_STARTING || epoch!=s->epoch)return -116;
    if(proof!=31)return -71;
    if(now>=s->start_end)return -110;
    for(unsigned r=0;r<4;r++)if(s->roles[r].phase!=REIST_GRAPHICAL_STARTING)return -116;
    for(unsigned r=0;r<4;r++){s->roles[r].phase=REIST_GRAPHICAL_LIVE;s->roles[r].health_ms=now;}
    s->phase=REIST_GRAPHICAL_LIVE;s->last_ms=now;return 0;
}
int reist_graphical_heartbeat(reist_graphical_state *s,unsigned r,uint64_t owner,
                              uint64_t epoch,uint64_t seq,uint64_t now) {
    if(!valid(s,now)||!role_owner(r,owner))return -22;
    reist_graphical_role *v=&s->roles[r];
    if(s->phase!=REIST_GRAPHICAL_LIVE || epoch!=s->epoch || owner!=v->owner ||
       (v->phase!=REIST_GRAPHICAL_LIVE && v->phase!=REIST_GRAPHICAL_STARTING) ||
       !seq || v->sequence==UINT64_MAX || seq!=v->sequence+1)return -116;
    /* A recreated role is not healthy merely because IMPORT/BIND succeeded.
     * Keep the original startup allowance until its first real ready health;
     * every subsequent LIVE heartbeat retains the shorter1000ms bound. */
    unsigned limit=v->phase==REIST_GRAPHICAL_STARTING?REIST_GRAPHICAL_START_MS:REIST_GRAPHICAL_HEALTH_MS;
    if(now-v->health_ms>=limit)return -110;
    v->sequence=seq;v->health_ms=now;v->phase=REIST_GRAPHICAL_LIVE;s->last_ms=now;return 0;
}
int reist_graphical_expired(const reist_graphical_state *s,uint64_t now) {
    if(!valid(s,now))return -22;
    if(s->phase==REIST_GRAPHICAL_STARTING)return now>=s->start_end?15:0;
    unsigned mask=0;
    for(unsigned r=0;r<4;r++) {
        const reist_graphical_role *v=&s->roles[r];
        unsigned limit=v->phase==REIST_GRAPHICAL_STARTING?REIST_GRAPHICAL_START_MS:REIST_GRAPHICAL_HEALTH_MS;
        if(((v->phase==REIST_GRAPHICAL_LIVE||v->phase==REIST_GRAPHICAL_STARTING) &&
            now-v->health_ms>=limit) ||
           (v->phase==REIST_GRAPHICAL_FENCING && now>=v->retire_end))mask|=1U<<r;
    }
    return (int)mask;
}
int reist_graphical_isolate(reist_graphical_state *s,unsigned role,uint64_t now) {
    if(!valid(s,now)||role>=4)return -22;
    if(now>UINT64_MAX-REIST_GRAPHICAL_RETIRE_MS)return -75;
    if(s->phase!=REIST_GRAPHICAL_LIVE && s->phase!=REIST_GRAPHICAL_STARTING &&
       s->phase!=REIST_GRAPHICAL_FENCING)return -16;
    unsigned first=role<2?0:role,end=role<2?4:role+1;
    for(unsigned r=first;r<end;r++) {
        reist_graphical_role *v=&s->roles[r];
        if(v->phase==REIST_GRAPHICAL_LIVE || v->phase==REIST_GRAPHICAL_STARTING) {
            v->phase=REIST_GRAPHICAL_FENCING;v->retire_end=now+REIST_GRAPHICAL_RETIRE_MS;
        }
    }
    if(role<2)s->phase=REIST_GRAPHICAL_FENCING;
    s->last_ms=now;return 0;
}
int reist_graphical_fenced(reist_graphical_state *s,unsigned r,uint64_t owner,
                           unsigned fences,uint64_t now) {
    if(!valid(s,now)||r>=4||!fences||(fences&~15U))return -22;
    reist_graphical_role *v=&s->roles[r];
    if(!owner||owner!=v->owner)return -116;
    if(v->phase!=REIST_GRAPHICAL_FENCING)return -16;
    if(now>=v->retire_end)return -110;
    v->fences|=fences;s->last_ms=now;return 0;
}
int reist_graphical_reaped(reist_graphical_state *s,unsigned r,uint64_t owner,uint64_t now) {
    if(!valid(s,now)||r>=4)return -22;
    reist_graphical_role *v=&s->roles[r];
    if(!owner || v->owner!=owner)return -116;
    if(v->phase==REIST_GRAPHICAL_REAPED)return 0;
    if(v->phase!=REIST_GRAPHICAL_FENCING)return -16;
    unsigned required=REIST_GRAPHICAL_FENCE_CHANNEL|
        (r==0?REIST_GRAPHICAL_FENCE_TERMINAL|REIST_GRAPHICAL_FENCE_DISPLAY:
         r==1?REIST_GRAPHICAL_FENCE_INPUT:0);
    if((v->fences&required)!=required)return -13;
    if(now>=v->retire_end)return -110;
    v->phase=REIST_GRAPHICAL_REAPED;s->last_ms=now;return 0;
}
int reist_graphical_finish(reist_graphical_state *s,unsigned degraded,uint64_t now) {
    if(!valid(s,now)||degraded>1)return -22;
    if(s->phase!=REIST_GRAPHICAL_FENCING)return -16;
    for(unsigned r=0;r<4;r++)if(s->roles[r].phase!=REIST_GRAPHICAL_REAPED &&
        s->roles[r].phase!=REIST_GRAPHICAL_OFF)return -16;
    s->phase=degraded||s->restart_blocked?REIST_GRAPHICAL_DEGRADED:REIST_GRAPHICAL_OFF;
    s->start_end=0;s->last_ms=now;return 0;
}
int reist_graphical_charge(reist_graphical_rate *r,uint64_t now,unsigned limit) {
    if(!r||!limit||limit>128)return -22;
    if(r->failed)return -122;
    if(r->used && now<r->last_ms){r->failed=1;return -22;}
    if(!r->used || now-r->start_ms>=1000){r->start_ms=now;r->used=0;}
    if(r->used>=limit){r->failed=1;return -122;}
    ++r->used;r->last_ms=now;return 0;
}
