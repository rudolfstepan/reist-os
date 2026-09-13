#include "native_service.h"
static uint64_t service_clock(void *v){
    reist_native_service *s=v;uint64_t now=s->upstream.clock(s->upstream.context);
    if(now<s->last_clock)s->clock_fault=1;else s->last_clock=now;
    return now;
}
static int service_check(reist_native_service *s,uint64_t now){
    if(s->clock_fault)return -84;
    return !s->deadline || now>=s->deadline?-110:0;
}
static int64_t service_port(void *v,reist_native_pio_request *q){
    reist_native_service *s=v;
    if(s->clock_fault)return -84;
    reist_native_pio_request bounded;
    int error=reist_x64_pio_deadline_prepare(&bounded,q,s->deadline);
    if(error)return error;
    return s->upstream.call(s->upstream.context,&bounded);
}
static int service_sleep(void *v,unsigned ms){
    reist_native_service *s=v;uint64_t now=service_clock(s);int error=service_check(s,now);
    if(error)return error;
    if(!ms || ms>=s->deadline-now)return -110;
    error=s->upstream.sleep(s->upstream.context,ms);if(error)return error;
    return service_check(s,service_clock(s));
}
static int service_pace(void *v,unsigned ms){
    reist_native_service *s=v;return s->upstream.sleep(s->upstream.context,ms);
}
static int service_read(void *v,uint32_t lba,unsigned char *out,uint64_t deadline){
    reist_native_service *s=v;s->deadline=deadline;
    reist_pio_ops p={s,service_port,service_clock,service_sleep};
    int result=reist_pio_read(&p,s->owner,s->server.capacity,lba,out);
    s->deadline=0;return result;
}
static int service_init(reist_native_service *s,uint64_t owner,const reist_pio_ops *upstream,uint64_t session_end){
    if(!s)return -22;
    *s=(reist_native_service){0};
    if(!upstream || !upstream->call || !upstream->clock || !upstream->sleep)return -22;
    s->upstream=*upstream;s->owner=owner;s->last_clock=service_clock(s);
    if(s->last_clock>UINT64_MAX-1000)return -22;
    s->deadline=s->last_clock+1000;
    if(session_end){
        if(s->last_clock>=session_end)return -110;
        if(s->deadline>session_end)s->deadline=session_end;
    }
    reist_pio_ops p={s,service_port,service_clock,service_sleep};
    uint32_t capacity=0;unsigned char sector[512];
    int result=reist_pio_identify(&p,owner,&capacity);
    if(!result)result=reist_pio_read(&p,owner,capacity,0,sector);
    uint64_t now=service_clock(s);
    if(!result)result=service_check(s,now);
    s->deadline=0;
    if(result)return result;
    return reist_block_server_init(&s->server,owner,capacity,now);
}
int reist_native_service_init(reist_native_service *s,uint64_t owner,const reist_pio_ops *upstream){
    return service_init(s,owner,upstream,0);
}
int reist_native_service_dispatch(reist_native_service *s,const x86os_ipc_message_t *q,
                                  x86os_ipc_bulk_message_t *reply){
    if(!s)return -22;
    reist_block_backend b={s,service_clock,service_pace,service_read};
    return reist_block_dispatch(&s->server,&b,q,reply);
}
int reist_native_service_init_profile(reist_native_profile_service *s,uint64_t owner,
    const reist_pio_ops *upstream,const reist_block_profile_v1 *profile){
    if(!s || !upstream || !upstream->clock || !upstream->sleep || !upstream->call ||
       (uint32_t)owner<2 || (uint32_t)owner>3 || !(owner>>32) || owner>>32>0x7fffffff ||
       (owner>>32)<=(s->service.owner>>32) || !profile)return -22;
    reist_pio_ops upstream_snapshot=*upstream;
    reist_block_profile_v1 snapshot=*profile;
    int status=reist_block_profile_admit(&snapshot,upstream_snapshot.clock(upstream_snapshot.context));
    if(status)return status;
    s->profile=snapshot;
    return service_init(&s->service,owner,&upstream_snapshot,snapshot.deadline_ms);
}
int reist_native_service_dispatch_profile(reist_native_profile_service *s,
    const x86os_ipc_message_t *q,x86os_ipc_bulk_message_t *reply){
    if(!s)return -22;
    reist_block_backend b={&s->service,service_clock,service_pace,service_read};
    return reist_block_dispatch_profile(&s->service.server,&s->profile,&b,q,reply);
}
