#include <reist/x86_64/service_session.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#define CHECK(x) do { if(!(x)){printf("line %d: %s\n",__LINE__,#x);return 1;} }while(0)
static int lifecycle(void);
int main(void) {
    reist_session_policy_v1 p={0},saved;
    CHECK(reist_session_policy_init(&p,7,91)==0);
    CHECK(p.version==1 && p.struct_size==sizeof(p) && p.owner==7);
    CHECK(!reist_session_policy_charge(&p,91,4096,1024,16384));
    saved=p;CHECK(reist_session_policy_charge(&p,1090,1,0,0)==-110 && !memcmp(&p,&saved,sizeof(p)));
    CHECK(!reist_session_policy_charge(&p,1091,1,0,0));
    CHECK(p.operations==1 && p.received==0 && p.written==0 && p.total_operations==4097);
    CHECK(!reist_session_policy_charge(&p,1000091,4096,1024,16384));
    saved=p;CHECK(reist_session_policy_charge(&p,1000091,1,0,0)==-110 && !memcmp(&p,&saved,sizeof(p)));
    CHECK(reist_session_policy_charge(&p,1000090,0,0,0)==-5 && !memcmp(&p,&saved,sizeof(p)));
    CHECK(reist_session_policy_init(&p,8,1000091)==-22 && !memcmp(&p,&saved,sizeof(p)));
    CHECK(!reist_session_policy_restart(&p,1000091));CHECK(!reist_session_policy_restart(&p,1000091));
    CHECK(p.restarts==2 && p.total_restarts==2 && !p.degraded);
    CHECK(reist_session_policy_restart(&p,1000091)==-11 && p.degraded==1 && p.total_restarts==2);
    saved=p;CHECK(reist_session_policy_restart(&p,2000091)==-11 && !memcmp(&p,&saved,sizeof(p)));
    CHECK(!reist_session_policy_charge(&p,2000091,1,0,0) && p.degraded==1);
    reist_session_policy_v1 clean={0};CHECK(!reist_session_policy_init(&clean,9,0));
    CHECK(!reist_session_policy_restart(&clean,0));CHECK(!reist_session_policy_restart(&clean,10000));
    CHECK(clean.restarts==1 && clean.total_restarts==2);
    for(unsigned index=0;index<sizeof(clean);index++) {
        reist_session_policy_v1 bad=clean;((unsigned char*)&bad)[index]^=0x80;
        /* Mutations are not all invalid (e.g. a legitimate counter increase),
         * but no failure may publish a partially updated state. */
        saved=bad;int r=reist_session_policy_charge(&bad,10000,1,0,0);
        CHECK(r==0 || ((r==-5 || r==-110) && !memcmp(&bad,&saved,sizeof(bad))));
    }
    saved=clean;CHECK(reist_session_policy_charge(&clean,UINT64_MAX,1,0,0)==-5 && !memcmp(&clean,&saved,sizeof(clean)));
    CHECK(reist_session_policy_charge(&clean,10000,4097,0,0)==-22 && !memcmp(&clean,&saved,sizeof(clean)));
    clean.total_operations=UINT64_MAX;saved=clean;
    CHECK(reist_session_policy_charge(&clean,10000,1,0,0)==-5 && !memcmp(&clean,&saved,sizeof(clean)));
    CHECK(reist_session_policy_charge(0,0,1,0,0)==-22);
    CHECK(!lifecycle());puts("SERVICE_SESSION_POLICY_OK");return 0;
}

typedef struct {
    uint64_t now,generation,driver,fs;
    unsigned calls,fail,bad,driver_live,fs_live,bound,endpoint_count,driver_ep,fs_ep,closed,layout;
    unsigned corrupt_phase,corrupt_field;
    unsigned actions[128],used;
    reist_session_control control;
} Model;
static int effect(Model *m,unsigned op) {
    if(m->used>=128){m->bad=1;return -5;}
    m->actions[m->used++]=op;return ++m->calls==m->fail?-5:0;
}
static uint64_t clock_model(void *v){return ((Model*)v)->now;}
static int endpoint_model(void *v,uint32_t *out) {
    Model *m=v;int r=effect(m,1);if(r)return r;
    *out=++m->endpoint_count+100;
    if(!m->driver_ep)m->driver_ep=*out;else m->fs_ep=*out;return 0;
}
static int close_model(void *v,uint32_t ep) {
    Model *m=v;int r=effect(m,2);if(r)return r;
    if(m->driver_live || m->fs_live || m->bound)m->bad=1;
    if(ep==m->driver_ep)m->driver_ep=0;else if(ep==m->fs_ep)m->fs_ep=0;else m->bad=1;
    ++m->closed;return 0;
}
static int64_t create_model(void *v,unsigned role,uint32_t ep,unsigned options) {
    Model *m=v;int r=effect(m,role==2?3:4);if(r)return -12;
    if((options>>8)!=m->layout || (role!=2 && role!=3))m->bad=1;
    uint64_t handle=(++m->generation<<32)|role;
    if(role==2){if(ep!=m->driver_ep || m->driver_live)m->bad=1;m->driver=handle;m->driver_live=1;}
    else {if(ep!=m->fs_ep || m->fs_live)m->bad=1;m->fs=handle;m->fs_live=1;}
    return (int64_t)handle;
}
static int delegate_model(void *v,uint32_t ep,uint64_t owner) {
    Model *m=v;int r=effect(m,5);if(r)return r;
    if(!((ep==m->driver_ep && owner==m->driver>>32)||(ep==m->fs_ep && owner==m->fs>>32)))m->bad=1;
    return 0;
}
static int pio_model(void *v,uint64_t owner,unsigned op) {
    Model *m=v;int r=effect(m,op==1?6:7);if(r)return r;
    if(owner!=m->driver || (op!=1 && op!=5))m->bad=1;
    if(op==1){if(!m->driver_live || !m->fs_live || m->bound)m->bad=1;m->bound=1;}
    else m->bound=0;
    return 0;
}
static int send_model(void *v,uint32_t ep,const reist_session_control *c,unsigned timeout) {
    Model *m=v;int r=effect(m,8);if(r)return r;
    if(!timeout || timeout>1000 || !m->bound || c->reserved || c->result)m->bad=1;
    if(ep==m->driver_ep) {
        if(c->owner!=m->driver || c->peer!=m->fs || c->phase!=1)m->bad=1;
    } else if(ep!=m->fs_ep || c->owner!=m->fs || c->peer!=m->driver || c->phase!=3)m->bad=1;
    m->control=*c;return 0;
}
static int receive_model(void *v,uint32_t ep,reist_session_control *c,unsigned timeout) {
    Model *m=v;int r=effect(m,9);if(r)return r;
    if(!timeout || timeout>1000 || !m->bound)m->bad=1;
    *c=m->control;
    if(ep==m->driver_ep){c->phase=2;c->request=11;c->reply=12;c->deadline=m->now+2800;c->sectors=m->layout==0?2880:m->layout==1?70000:256;}
    else if(ep==m->fs_ep)c->phase=4;else m->bad=1;
    if(c->phase==m->corrupt_phase)switch(m->corrupt_field) {
        case 0:c->owner^=1ULL<<32;break;
        case 1:c->peer^=1ULL<<32;break;
        case 2:c->deadline=UINT64_MAX;break;
        case 3:c->request=0;break;
        case 4:c->reply=c->request;break;
        case 5:c->sectors++;break;
        case 6:c->phase++;break;
        case 7:c->result=1;break;
        case 8:c->reserved=1;break;
        case 9:c->result=INT32_MIN;break;
        default:m->bad=1;
    }
    return 0;
}
static int64_t task_model(void *v,unsigned op,uint64_t handle,unsigned timeout) {
    Model *m=v;int r=effect(m,op==3?10:11);if(r)return r;
    if(m->bound || (op!=2 && op!=3) || timeout!=(op==2?1000U:0U))m->bad=1;
    unsigned *live=handle==m->driver?&m->driver_live:handle==m->fs?&m->fs_live:0;
    if(!live || !*live)m->bad=1;
    if(op==2 && live){*live=0;return 2LL<<32;}
    return 0;
}
static int lifecycle(void) {
    for(unsigned layout=0;layout<5;layout++)for(unsigned fail=0;fail<=11;fail++) {
        Model m={0};m.now=100;m.generation=7;m.fail=fail;m.layout=layout;
        reist_service_session_ops ops={&m,clock_model,endpoint_model,close_model,create_model,
            delegate_model,pio_model,send_model,receive_model,task_model};
        reist_service_session_v1 s={0};CHECK(!reist_service_session_init(&s,7,layout));
        int r=reist_service_session_open(&s,&ops,1100,0);
        CHECK(!m.bad && r==(fail?(fail==3 || fail==5?-12:-5):0));
        if(!fail) {
            CHECK(s.phase==REIST_SESSION_HEALTHY && s.starts==1 && m.bound);
            unsigned calls=m.calls;CHECK(reist_service_session_open(&s,&ops,1100,0)==-16 && m.calls==calls);
            uint64_t old_driver=s.driver,old_fs=s.filesystem;
            CHECK(!reist_service_session_retire(&s,&ops) && s.last_driver==old_driver && s.last_filesystem==old_fs);
            m.used=0;CHECK(!reist_service_session_open(&s,&ops,1100,0));
            CHECK(s.driver>old_driver && s.filesystem>old_fs && s.starts==2);
            CHECK(!reist_service_session_retire(&s,&ops));
        }
        CHECK(!m.bad && !m.bound && !m.driver_live && !m.fs_live && !m.driver_ep && !m.fs_ep);
        CHECK(s.phase==REIST_SESSION_COLD && s.retirements==(fail?1:2));
        unsigned calls=m.calls;CHECK(!reist_service_session_retire(&s,&ops) && m.calls==calls);
    }
    for(unsigned failure=1;failure<=7;failure++) {
        Model m={0};m.now=100;m.generation=7;m.layout=2;
        reist_service_session_ops ops={&m,clock_model,endpoint_model,close_model,create_model,
            delegate_model,pio_model,send_model,receive_model,task_model};
        reist_service_session_v1 s={0};CHECK(!reist_service_session_init(&s,7,2));
        CHECK(!reist_service_session_open(&s,&ops,1100,0));
        m.calls=0;m.fail=failure;
        CHECK(reist_service_session_retire(&s,&ops)==-117 && s.phase==REIST_SESSION_ISOLATED && !m.bad);
        CHECK(m.calls==failure && !s.retirements); /* First uncertain cleanup stops. */
    }
    for(unsigned phase=2;phase<=4;phase+=2)for(unsigned field=0;field<10;field++) {
        Model m={0};m.now=100;m.generation=7;m.layout=2;m.corrupt_phase=phase;m.corrupt_field=field;
        reist_service_session_ops ops={&m,clock_model,endpoint_model,close_model,create_model,
            delegate_model,pio_model,send_model,receive_model,task_model};
        reist_service_session_v1 s={0};CHECK(!reist_service_session_init(&s,7,2));
        CHECK(reist_service_session_open(&s,&ops,1100,0)==-71);
        CHECK(!m.bad && s.phase==REIST_SESSION_COLD && !m.bound && !m.driver_live && !m.fs_live && !m.driver_ep && !m.fs_ep);
        CHECK(s.starts==1 && s.retirements==1 && s.last_driver && s.last_filesystem);
    }
    return 0;
}
