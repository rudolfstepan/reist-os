#ifndef REIST_X64_INPUT_H
#define REIST_X64_INPUT_H
#include <stdint.h>
enum { REIST_INPUT_BIND=1,REIST_INPUT_QUERY,REIST_INPUT_READ,
       REIST_INPUT_CONTROLLER,REIST_INPUT_DATA,REIST_INPUT_FENCE };
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t owner,epoch,deadline_ms,value,reserved[2];
} reist_input_request_v1;
enum { REIST_INPUT_HEALTHY=1,REIST_INPUT_KEY,REIST_INPUT_POINTER,REIST_INPUT_ERROR };
typedef struct {
    uint32_t version,size,type,flags;
    uint64_t owner,target,epoch,sequence;
    int32_t code,dx,dy;
    uint32_t buttons;
} reist_input_event_v1;
_Static_assert(sizeof(reist_input_request_v1)==64,"input request-v1");
_Static_assert(sizeof(reist_input_event_v1)==64,"input event-v1");
static inline int reist_input_event_valid(const reist_input_event_v1 *e,uint64_t owner,uint64_t target,uint64_t epoch,uint64_t sequence) {
    if(!e||!sequence)return 0;
    if(e->version!=1||e->size!=64||e->target!=target||e->sequence!=sequence||sequence>32||!e->epoch||e->epoch>>63)return 0;
    if((uint32_t)e->owner!=5||!(e->owner>>32)||e->owner>>32>0x7fffffff)return 0;
    if(sequence>1&&(e->owner!=owner||e->epoch!=epoch))return 0;
    if(e->type==REIST_INPUT_HEALTHY)return sequence==1&&!e->flags&&!e->code&&!e->dx&&!e->dy&&!e->buttons;
    if(sequence==1)return 0;
    if(e->type==REIST_INPUT_KEY)return !(e->flags&~63u)&&e->code>0&&e->code<=0x58&&!e->dx&&!e->dy&&!e->buttons;
    if(e->type==REIST_INPUT_POINTER)return !e->flags&&!e->code&&e->dx>=-256&&e->dx<=255&&e->dy>=-256&&e->dy<=255&&e->buttons<=7;
    if(e->type==REIST_INPUT_ERROR)return !e->flags&&e->code<0&&e->code>=-4095&&!e->dx&&!e->dy&&!e->buttons;
    return 0;
}
#endif
