#include <reist/x86_64/block.h>
typedef uint64_t block_word __attribute__((may_alias,aligned(1)));
static void block_zero(void *p,unsigned n){unsigned char *b=p;while(n>=8){*(volatile block_word*)b=0;b+=8;n-=8;}while(n--)*b++=0;}
static void block_copy(void *p,const void *q,unsigned n){unsigned char *o=p;const unsigned char *s=q;
    while(n>=8){*(volatile block_word*)o=*(const block_word*)s;o+=8;s+=8;n-=8;}while(n--)*o++=*s++;}
static int block_empty(const void *p,unsigned n){const unsigned char *b=p;
    while(n>=8){if(*(const block_word*)b)return 0;b+=8;n-=8;}while(n--)if(*b++)return 0;return 1;}
static int block_error(int e){return e==-5 || e==-11 || e==-13 || e==-19 || e==-22 || e==-84 || e==-110 || e==-116;}
int reist_block_client_bind(reist_block_client *c,uint64_t owner){
    if(!c || !owner || owner>INT64_MAX || owner<=c->owner)return -22;
    if(c->busy)return -16;
    c->owner=owner;c->sequence=0;c->failed=0;return 0;
}
static int block_client_result(reist_block_client *c,int result){
    c->busy=0;if(result)c->failed=1;return result;
}
int reist_block_read(reist_block_client *c,const reist_block_transport *t,uint64_t lba,
                     unsigned char output[512],unsigned timeout){
    if(!c || !t || !t->clock || !t->send || !t->receive || !output || !c->owner ||
       lba>=0x10000000ULL || !timeout || timeout>1000)return -22;
    if(c->busy)return -16;
    if(c->failed || c->sequence==UINT64_MAX)return -116;
    uint64_t now=t->clock(t->context);
    if(now>UINT64_MAX-timeout)return -22;
    reist_block_header h={1,64,1,0,c->owner,++c->sequence,lba,now+timeout,512,0,0};
    x86os_ipc_message_t request;block_zero(&request,sizeof(request));
    request.version=1;request.struct_size=sizeof(request);request.length=64;
    block_copy(request.payload,&h,64);c->busy=1;
    uint64_t admission=t->clock(t->context);
    if(admission<now || admission>=h.deadline_ms)return block_client_result(c,admission<now?-84:-110);
    int result=t->send(t->context,&request,(unsigned)(h.deadline_ms-admission));
    if(result)return block_client_result(c,result);
    uint64_t next=t->clock(t->context);
    if(next<admission || next>=h.deadline_ms)return block_client_result(c,next<admission?-84:-110);
    x86os_ipc_bulk_message_t reply;block_zero(&reply,sizeof(reply));
    reply.version=2;reply.struct_size=sizeof(reply);reply.length=2048;
    result=t->receive(t->context,&reply,(unsigned)(h.deadline_ms-next));
    if(result)return block_client_result(c,result);
    now=t->clock(t->context);
    if(now<next || now>=h.deadline_ms)return block_client_result(c,now<next?-84:-110);
    if(reply.version!=2 || reply.struct_size!=sizeof(reply) || (reply.length!=64 && reply.length!=576))
        return block_client_result(c,-71);
    reist_block_header r;block_copy(&r,reply.payload,64);
    if(r.version!=1 || r.size!=64 || r.operation!=1 || r.flags!=1 || r.reserved ||
       r.owner!=h.owner || r.sequence!=h.sequence || r.lba!=h.lba || r.deadline_ms!=h.deadline_ms ||
       (r.status==0?(r.length!=512 || reply.length!=576):
                    (!block_error(r.status) || r.length!=0 || reply.length!=64)) ||
       !block_empty(reply.payload+reply.length,2048-reply.length))
        return block_client_result(c,-71);
    if(r.status)return block_client_result(c,r.status);
    block_copy(output,reply.payload+64,512);return block_client_result(c,0);
}
int reist_block_server_init(reist_block_server *s,uint64_t owner,uint32_t sectors,uint64_t now){
    if(!s)return -22;
    block_zero(s,sizeof(*s));
    if(!owner || owner>INT64_MAX || !sectors || sectors>0x10000000U)return -22;
    s->owner=owner;s->capacity=sectors;s->next_sequence=1;s->last_read_ms=now;s->ready=1;return 0;
}
static int profile_fields(const reist_block_profile_v1 *p){
    return p && p->version==1 && p->size==24 && p->request_limit &&
        p->request_limit<=16 && !p->reserved && p->deadline_ms;
}
int reist_block_profile_admit(const reist_block_profile_v1 *p,uint64_t now){
    return profile_fields(p) && p->deadline_ms>now && p->deadline_ms-now<=3000?0:-22;
}
static int block_dispatch(reist_block_server *s,const reist_block_backend *b,
    const x86os_ipc_message_t *q,x86os_ipc_bulk_message_t *reply,unsigned limit,uint64_t session_end,
    unsigned session_ms,unsigned spacing){
    if(!s || !b || !b->clock || !b->sleep || !b->read || !q || !reply)return -22;
    block_zero(reply,sizeof(*reply));reply->version=2;reply->struct_size=sizeof(*reply);reply->length=64;
    reist_block_header h,r;block_copy(&h,q->payload,64);
    r=(reist_block_header){1,64,1,1,s->owner,h.sequence,h.lba,h.deadline_ms,0,-22,0};
    int status=-22;uint64_t now=b->clock(b->context);
    uint64_t deadline=h.deadline_ms;
    if(session_end){
        if(now<s->last_read_ms){status=-84;goto result;}
        if(now>=session_end){status=-110;goto result;}
        if(session_end-now>session_ms)goto result;
        if(deadline>session_end)deadline=session_end;
    }
    if(!s->ready || s->requests>=limit){status=-11;goto result;}
    s->requests++;
    if(q->version!=1 || q->struct_size!=sizeof(*q) || q->length!=64 ||
       !block_empty(q->payload+64,64) || h.version!=1 || h.size!=64 || h.operation!=1 ||
       h.flags || h.length!=512 || h.status || h.reserved)goto result;
    if(h.owner!=s->owner){status=-13;goto result;}
    if(!h.sequence || h.sequence!=s->next_sequence || h.sequence==UINT64_MAX){status=-116;goto result;}
    if(h.lba>=s->capacity || h.lba>=0x10000000ULL)goto result;
    if(h.deadline_ms<=now){status=-110;goto result;}
    if(h.deadline_ms-now>1000)goto result;
    if(now<s->last_read_ms){status=-84;goto result;}
    s->next_sequence++;
    /* Wide ready=1 retains the initial guard until a successful physical read.
     * Rejected requests/failed waits charge attempts, never consume that guard.
     * Legacy ready stays1 and its spacing remains100 throughout. */
#ifdef REIST_NATIVE_LARGE_FILE
    unsigned pace=(spacing==50 || spacing==25) && s->ready==1?100:spacing;
#else
    unsigned pace=spacing==50 && s->ready==1?100:spacing;
#endif
    if(now-s->last_read_ms<pace){
        unsigned delay=pace-(unsigned)(now-s->last_read_ms);
        if(deadline-now<=delay){status=-110;goto result;}
        status=b->sleep(b->context,delay);if(status)goto result;
        uint64_t next=b->clock(b->context);
        if(next<now){status=-84;goto result;}
        if(next-now<delay || next>=deadline){status=-110;goto result;}
        now=next;
    }
    status=b->read(b->context,(uint32_t)h.lba,reply->payload+64,deadline);
    s->last_read_ms=b->clock(b->context);
    if(s->last_read_ms<now)status=-84;
    else if(s->last_read_ms>=deadline)status=-110;
#ifdef REIST_NATIVE_LARGE_FILE
    if(!status && (spacing==50 || spacing==25))s->ready=2;
#else
    if(!status && spacing==50)s->ready=2;
#endif
result:
    if(status){if(!block_error(status))status=-5;block_zero(reply->payload+64,1984);}
    else {r.length=512;reply->length=576;}
    r.status=status;block_copy(reply->payload,&r,64);return status;
}
int reist_block_dispatch(reist_block_server *s,const reist_block_backend *b,
    const x86os_ipc_message_t *q,x86os_ipc_bulk_message_t *reply){
    return block_dispatch(s,b,q,reply,8,0,3000,100);
}
int reist_block_dispatch_profile(reist_block_server *s,const reist_block_profile_v1 *p,
    const reist_block_backend *b,const x86os_ipc_message_t *q,x86os_ipc_bulk_message_t *reply){
    if(!profile_fields(p))return -22;
    return block_dispatch(s,b,q,reply,p->request_limit,p->deadline_ms,3000,100);
}

#include <reist/x86_64/wide_file.h>
static int profile_fields_v2(const reist_block_profile_v2 *p){
    return p && p->version==2 && p->size==24 &&
        p->request_limit==REIST_WIDE_BLOCK_REQUESTS && !p->reserved && p->deadline_ms;
}
int reist_block_profile_admit_v2(const reist_block_profile_v2 *p,uint64_t now){
    return profile_fields_v2(p) && p->deadline_ms>now &&
        p->deadline_ms-now<=REIST_WIDE_FILE_MS?0:-22;
}
int reist_block_dispatch_profile_v2(reist_block_server *s,const reist_block_profile_v2 *p,
    const reist_block_backend *b,const x86os_ipc_message_t *q,x86os_ipc_bulk_message_t *reply){
    if(!profile_fields_v2(p))return -22;
    return block_dispatch(s,b,q,reply,p->request_limit,p->deadline_ms,REIST_WIDE_FILE_MS,50);
}

#ifdef REIST_NATIVE_LARGE_FILE
#include <reist/x86_64/large_file.h>
static int profile_fields_v3(const reist_block_profile_v3 *p){
    return p && p->version==3 && p->size==24 &&
        p->request_limit==REIST_LARGE_BLOCK_REQUESTS && !p->reserved && p->deadline_ms;
}
int reist_block_profile_admit_v3(const reist_block_profile_v3 *p,uint64_t now){
    return profile_fields_v3(p) && p->deadline_ms>now &&
        p->deadline_ms-now<=REIST_LARGE_FILE_MS?0:-22;
}
int reist_block_dispatch_profile_v3(reist_block_server *s,const reist_block_profile_v3 *p,
    const reist_block_backend *b,const x86os_ipc_message_t *q,x86os_ipc_bulk_message_t *reply){
    if(!profile_fields_v3(p))return -22;
    return block_dispatch(s,b,q,reply,p->request_limit,p->deadline_ms,REIST_LARGE_FILE_MS,25);
}
#endif
