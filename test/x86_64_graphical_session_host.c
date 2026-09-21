#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/graphical_session.h>
#include <reist/x86_64/service_session.h>
extern int reist_graphical_restart(reist_graphical_state *,reist_session_policy_v1 *,uint64_t);
static void restart_containment(void) {
    reist_graphical_state s={0},before;
    reist_session_policy_v1 p={0},old;
    assert(!reist_graphical_init(&s,1ULL<<32,0));assert(!reist_session_policy_init(&p,1,0));
    assert(!reist_session_policy_charge(&p,0,1,2,3));
    assert(!reist_graphical_restart(&s,&p,100));assert(!reist_graphical_restart(&s,&p,200));
    assert(p.restarts==2 && p.total_restarts==2 && !p.degraded);
    assert(reist_graphical_restart(&s,&p,300)==-11);
    assert(!p.degraded && p.restarts==2 && p.total_restarts==2 && p.restart_anchor_ms==0 && p.previous_ms==300);
    assert(p.operations==1 && p.received==2 && p.written==3);
    assert(p.total_operations==1 && p.total_received==2 && p.total_written==3);
    old=p;assert(reist_graphical_restart(&s,&p,400)==-11);assert(!memcmp(&p,&old,sizeof(p)));
    assert(reist_graphical_begin(&s,400)==-11);
    assert(!reist_session_policy_charge(&p,400,1,0,0)); /* unrelated normal work */
    assert(!reist_session_policy_restart(&p,10300)); /* original window, not reset by GUI */
    assert(p.restarts==1 && p.total_restarts==3 && p.restart_anchor_ms==10000);
    old=p;assert(reist_graphical_restart(&s,&p,10301)==-11);assert(!memcmp(&p,&old,sizeof(p)));
    assert(reist_graphical_begin(&s,10301)==-11);
    memset(&s,0,sizeof(s));memset(&p,0,sizeof(p));
    assert(!reist_graphical_init(&s,1ULL<<32,0));assert(!reist_session_policy_init(&p,1,0));
    assert(!reist_session_policy_restart(&p,0));assert(!reist_session_policy_restart(&p,1));
    assert(reist_session_policy_restart(&p,2)==-11 && p.degraded);
    assert(reist_graphical_restart(&s,&p,3)==-11 && p.degraded); /* never clear parent degradation */
    memset(&s,0,sizeof(s));memset(&p,0,sizeof(p));
    assert(!reist_graphical_init(&s,1ULL<<32,0));assert(!reist_session_policy_init(&p,2,0));
    before=s;old=p;assert(reist_graphical_restart(&s,&p,1)==-116);
    assert(!memcmp(&s,&before,sizeof(s)) && !memcmp(&p,&old,sizeof(p)));
    p.owner=1;p.version=2;old=p;assert(reist_graphical_restart(&s,&p,1)==-5);
    assert(!memcmp(&s,&before,sizeof(s)) && !memcmp(&p,&old,sizeof(p)));
    p.version=1;p.total_restarts=UINT64_MAX;old=p;
    assert(reist_graphical_restart(&s,&p,1)==-5);
    assert(!memcmp(&s,&before,sizeof(s)) && !memcmp(&p,&old,sizeof(p)));
    memset(&s,0,sizeof(s));memset(&p,0,sizeof(p));
    assert(!reist_graphical_init(&s,1ULL<<32,0));assert(!reist_session_policy_init(&p,1,0));
    assert(!reist_graphical_begin(&s,0));
    for(unsigned n=0;n<4;n++)assert(!reist_graphical_bind(&s,n,((uint64_t)(2+n)<<32)|(4+n),0));
    assert(!reist_graphical_ready(&s,1,31,0));
    assert(!reist_graphical_restart(&s,&p,100));assert(!reist_graphical_restart(&s,&p,200));
    assert(reist_graphical_restart(&s,&p,300)==-11 && s.phase==REIST_GRAPHICAL_LIVE);
    assert(!reist_graphical_isolate(&s,0,300));
    for(unsigned n=0;n<4;n++) {
        assert(!reist_graphical_fenced(&s,n,s.roles[n].owner,REIST_GRAPHICAL_FENCE_ALL,300));
        assert(!reist_graphical_reaped(&s,n,s.roles[n].owner,300));
    }
    assert(!reist_graphical_finish(&s,0,300));
    assert(s.phase==REIST_GRAPHICAL_DEGRADED && !p.degraded && p.restarts==2 && p.total_restarts==2);
}
#ifdef REIST_GRAPHICAL_AUDIT_HOST
#include "../userspace/gui/lib/native_surface.h"
static void audit_test(void) {
    assert(!reist_native_fault_due(3499,3000));assert(reist_native_fault_due(3500,3000));
    assert(reist_native_fault_due(3501,3000));assert(!reist_native_fault_due(UINT64_MAX,UINT64_MAX-499));
    assert(sizeof(reist_native_audit)==20544);
    reist_native_audit_init(7ULL<<32|4,3);
    assert(reist_native_audit.magic==0x3154494455414752ULL && reist_native_audit.sequence==0);
    x86os_ipc_message_t message={0};message.version=1;message.struct_size=140;message.length=64;
    uint32_t version=2;memcpy(message.payload,&version,4);
    for(unsigned n=1;n<=260;n++) {
        memcpy(message.payload+4,&n,4);reist_native_audit_append(100,&message,n);
        unsigned index=(n-1)%128;
        assert(reist_native_audit.sequence==n && reist_native_audit.entries[index].sequence==n);
        assert(reist_native_audit.entries[index].ms==n && reist_native_audit.entries[index].endpoint==100);
        assert(!memcmp((const void*)reist_native_audit.entries[index].wire,&message,140));
    }
    assert(reist_native_audit.entries[4].sequence==133 && reist_native_audit.entries[3].sequence==260);
    message.length=124;version=6;memcpy(message.payload,&version,4);version=129;memcpy(message.payload+8,&version,4);
    reist_native_audit_append(101,&message,261);assert(reist_native_audit.sequence==261);
    version=128;memcpy(message.payload+8,&version,4);
    reist_native_audit_append(101,&message,262);assert(reist_native_audit.sequence==261);
    message.length=64;version=2;memcpy(message.payload,&version,4);
    reist_native_audit.sequence=UINT64_MAX;reist_native_audit_append(101,&message,263);
    assert(reist_native_audit.sequence==UINT64_MAX && reist_native_audit.exhausted==1);
    reist_native_audit_append(101,&message,264);assert(reist_native_audit.sequence==UINT64_MAX);
    reist_native_audit_init(8ULL<<32|6,4);
    assert(!reist_native_audit.sequence && !reist_native_audit.exhausted && !reist_native_audit.entries[3].sequence);
}
#endif

static uint64_t owner(unsigned role,unsigned generation) {
    return (uint64_t)generation<<32|(4+role);
}
static void start(reist_graphical_state *s,uint64_t now,unsigned generation) {
    assert(!reist_graphical_begin(s,now));
    for(unsigned r=0;r<4;r++)assert(!reist_graphical_bind(s,r,owner(r,generation+r),now));
    assert(!reist_graphical_ready(s,s->epoch,31,now));
}
static void replacement_startup(void) {
    reist_graphical_state s={0},before,late,reaped;
    assert(!reist_graphical_init(&s,1ULL<<32,0));start(&s,0,2);
    uint64_t old=s.roles[2].owner;
    assert(!reist_graphical_isolate(&s,2,100));
    assert(!reist_graphical_fenced(&s,2,old,REIST_GRAPHICAL_FENCE_CHANNEL,100));
    assert(!reist_graphical_reaped(&s,2,old,100));
    reaped=s;
    assert(!reist_graphical_bind(&s,2,owner(2,9),100));
    for(unsigned r=0;r<4;r++)if(r!=2)assert(!reist_graphical_heartbeat(&s,r,s.roles[r].owner,1,1,900));
    assert(!(reist_graphical_expired(&s,1100)&4));
    before=reaped;assert(reist_graphical_bind(&reaped,2,owner(2,9),UINT64_MAX-2999)==-75);
    assert(!memcmp(&reaped,&before,sizeof(reaped)));
    assert(!(reist_graphical_expired(&s,3099)&4));
    assert(reist_graphical_expired(&s,3100)&4);
    late=s;before=late;
    assert(reist_graphical_heartbeat(&late,2,owner(2,9),1,1,3100)==-110);
    assert(!memcmp(&late,&before,sizeof(late)));
    before=s;assert(reist_graphical_heartbeat(&s,2,old,1,1,1500)==-116);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(s.roles[2].phase==REIST_GRAPHICAL_STARTING && s.roles[2].sequence==0 && s.roles[2].health_ms==100);
    assert(!reist_graphical_heartbeat(&s,2,owner(2,9),1,1,2000));
    assert(s.roles[2].phase==REIST_GRAPHICAL_LIVE && s.roles[2].health_ms==2000);
    assert(!(reist_graphical_expired(&s,2999)&4));assert(reist_graphical_expired(&s,3000)&4);
    before=s;assert(reist_graphical_heartbeat(&s,2,owner(2,9),1,2,3000)==-110);
    assert(!memcmp(&s,&before,sizeof(s)));
}
int main(void) {
    restart_containment();
    replacement_startup();
#ifdef REIST_GRAPHICAL_AUDIT_HOST
    audit_test();
#endif
    reist_graphical_state s={0},before;
    assert(!reist_graphical_init(&s,1ULL<<32,100));
    before=s;assert(reist_graphical_begin(&s,99)==-22);assert(!memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_begin(&s,100));
    assert(reist_graphical_ready(&s,1,31,101)==-116);
    for(unsigned r=0;r<4;r++) {
        before=s;
        assert(reist_graphical_bind(&s,r,owner(r,2+r)^1,100)==-22);
        assert(!memcmp(&s,&before,sizeof(s)));
        assert(!reist_graphical_bind(&s,r,owner(r,2+r),100));
        before=s;assert(reist_graphical_bind(&s,r,owner(r,8+r),100)==-16);
        assert(!memcmp(&s,&before,sizeof(s)));
    }
    before=s;assert(reist_graphical_ready(&s,1,15,101)==-71);assert(!memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_ready(&s,1,31,102));
    assert(!reist_graphical_heartbeat(&s,0,owner(0,2),1,1,500));
    before=s;assert(reist_graphical_heartbeat(&s,0,owner(0,2),1,1,501)==-116);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(reist_graphical_expired(&s,1101)==0);
    assert(reist_graphical_expired(&s,1102)==14);
    assert(reist_graphical_expired(&s,1500)==15);
    assert(!reist_graphical_isolate(&s,2,1500));
    before=s;assert(reist_graphical_reaped(&s,2,owner(2,4),1500)==-13);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_fenced(&s,2,owner(2,4),REIST_GRAPHICAL_FENCE_CHANNEL,1500));
    assert(!reist_graphical_reaped(&s,2,owner(2,4),1500));
    assert(s.roles[0].phase==REIST_GRAPHICAL_LIVE && s.roles[3].phase==REIST_GRAPHICAL_LIVE);
    before=s;assert(reist_graphical_bind(&s,2,owner(2,4),1500)==-116);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_bind(&s,2,owner(2,9),1500));
    assert(!reist_graphical_isolate(&s,0,1500));
    for(unsigned r=0;r<4;r++) {
        assert(s.roles[r].phase==REIST_GRAPHICAL_FENCING);
        uint64_t id=s.roles[r].owner;
        before=s;assert(reist_graphical_reaped(&s,r,id,1501)==-13);
        assert(!memcmp(&s,&before,sizeof(s)));
        assert(!reist_graphical_fenced(&s,r,id,REIST_GRAPHICAL_FENCE_ALL,1501));
        assert(!reist_graphical_fenced(&s,r,id,REIST_GRAPHICAL_FENCE_ALL,1501));
        assert(!reist_graphical_reaped(&s,r,id,1501));
        before=s;assert(reist_graphical_reaped(&s,r,id-1,1501)==-116);
        assert(!memcmp(&s,&before,sizeof(s)));
        assert(!reist_graphical_reaped(&s,r,id,1501));
    }
    assert(!reist_graphical_finish(&s,0,1502));assert(s.epoch==1);
    start(&s,1503,20);assert(s.epoch==2);
    before=s;assert(reist_graphical_heartbeat(&s,0,owner(0,20),1,1,1504)==-116);
    assert(!memcmp(&s,&before,sizeof(s)));
    assert(!reist_graphical_isolate(&s,1,1504));
    for(unsigned r=0;r<4;r++) {
        assert(!reist_graphical_fenced(&s,r,s.roles[r].owner,REIST_GRAPHICAL_FENCE_ALL,1505));
        assert(!reist_graphical_reaped(&s,r,s.roles[r].owner,1505));
    }
    assert(!reist_graphical_finish(&s,1,1506));
    before=s;assert(reist_graphical_begin(&s,1507)==-11);assert(!memcmp(&s,&before,sizeof(s)));
    reist_graphical_rate rate={0};
    assert(!reist_graphical_charge(&rate,10,128));
    for(unsigned n=1;n<128;n++)assert(!reist_graphical_charge(&rate,10+n,128));
    assert(reist_graphical_charge(&rate,999,128)==-122);
    assert(reist_graphical_charge(&rate,2000,128)==-122); /* no reset after failure */
    memset(&rate,0,sizeof(rate));assert(!reist_graphical_charge(&rate,100,128));
    assert(!reist_graphical_charge(&rate,1100,128));assert(rate.used==1);
    assert(reist_graphical_charge(&rate,1099,128)==-22);
    assert(reist_graphical_charge(&rate,1200,128)==-122);
    assert(!reist_graphical_init(&s,1ULL<<32,0));s.epoch=UINT64_MAX;
    before=s;assert(reist_graphical_begin(&s,1)==-75);assert(!memcmp(&s,&before,sizeof(s)));
    puts("GRAPHICAL_LIFECYCLE_OK");return 0;
}
