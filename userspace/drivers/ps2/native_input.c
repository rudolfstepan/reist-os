#include "native_input.h"
static void zero(void *p,unsigned n){unsigned char *b=p;while(n--)*b++=0;}
void reist_ps2_clear(reist_ps2_decoder *s){zero(s,sizeof(*s));}
static int fail(reist_ps2_decoder *s,int error){reist_ps2_clear(s);return error;}
int reist_ps2_decode(reist_ps2_decoder *s,uint8_t status,uint8_t data,uint64_t now,reist_input_event_v1 *e) {
    if(!s||!e)return -22;
    if(now<s->last||now>>60)return fail(s,-84);
    if((s->keyboard_end && now>=s->keyboard_end)||(s->mouse_end && now>=s->mouse_end))return fail(s,-110);
    s->last=now;zero(e,sizeof(*e));
    if(!(status&1)||(status&0xc0))return fail(s,-71);
    if(status&0x20) {
        if(!s->mouse_count) {
            if(!(data&8))return fail(s,-71);
            if(data&0xc0)return fail(s,-75);
            s->mouse_end=now+100;
        }
        if(s->mouse_count>2)return fail(s,-84);
        s->packet[s->mouse_count++]=data;
        if(s->mouse_count<3)return 0;
        e->type=REIST_INPUT_POINTER;e->buttons=s->packet[0]&7;
        e->dx=(int)s->packet[1]-((s->packet[0]&16)?256:0);
        e->dy=(int)s->packet[2]-((s->packet[0]&32)?256:0);
        s->mouse_count=0;s->mouse_end=0;return 1;
    }
    if(s->pause) {
        static const uint8_t pause[]={0x1d,0x45,0xe1,0x9d,0xc5};
        if(s->pause>5||data!=pause[s->pause-1])return fail(s,-71);
        if(++s->pause==6){s->pause=0;s->keyboard_end=0;}return 0;
    }
    if(data==0xe0||data==0xe1) {
        if(s->extended)return fail(s,-71);
        s->keyboard_end=now+100;
        if(data==0xe0)s->extended=1;else s->pause=1;return 0;
    }
    unsigned key=data&127,release=data>>7,ext=s->extended,index=key+128*ext;
    if(!key||key>0x58)return fail(s,-71);
    unsigned mask=1u<<(index&7),held=s->down[index/8]&mask;
    s->extended=0;s->keyboard_end=0;
    if(release && !held)return 0;
    if(release)s->down[index/8]&=(uint8_t)~mask;else s->down[index/8]|=(uint8_t)mask;
    unsigned mod=key==0x2a&&!ext?1:key==0x36&&!ext?2:key==0x1d?(ext?8:4):key==0x38?(ext?32:16):0;
    if(release)s->modifiers&=~mod;else s->modifiers|=mod;
    if(key==0x3a&&!ext&&!release&&!held)s->modifiers^=64;
    e->type=REIST_INPUT_KEY;e->code=(int)key;
    e->flags=release|(ext<<1)|((s->modifiers&3)?4:0)|((s->modifiers&12)?8:0)|((s->modifiers&48)?16:0)|((s->modifiers&64)?32:0);
    return 1;
}
static int transfer(const reist_ps2_transport *t,unsigned op,unsigned value,uint64_t end) {
    for(unsigned n=0;n<100;n++) {
        uint64_t now=t->clock(t->context);if(now>=end)return -110;
        int64_t r=t->transfer(t->context,op,value,end);
        if(r!=-11)return r>=-4095&&r<=65536?(int)r:-5;
        if(t->sleep(t->context,10))return -5;
    }
    return -110;
}
static int receive(const reist_ps2_transport *t,unsigned auxiliary,unsigned expected,uint64_t end) {
    int r=transfer(t,REIST_INPUT_READ,0,end);if(r<0)return r;
    if(!r)return -71;
    unsigned raw=(unsigned)r-1,status=raw>>8;
    return (status&0xc1)==1 && !!(status&32)==auxiliary && (raw&255)==expected?0:-71;
}
static int device(const reist_ps2_transport *t,unsigned aux,unsigned command,uint64_t end) {
    int r;if(aux && (r=transfer(t,REIST_INPUT_CONTROLLER,0xd4,end)))return r;
    r=transfer(t,REIST_INPUT_DATA,command,end);if(r)return r;
    return receive(t,aux,0xfa,end);
}
int reist_ps2_initialize(const reist_ps2_transport *t,uint64_t end) {
    if(!t||!t->clock||!t->transfer||!t->sleep)return -22;
    uint64_t now=t->clock(t->context);if(end<=now||end-now>1000)return -22;
    int r=transfer(t,REIST_INPUT_CONTROLLER,0x60,end);if(r)return r;
    r=transfer(t,REIST_INPUT_DATA,0x70,end);if(r)return r;
    /* Drain a bounded old FIFO before any protocol self-test. */
    unsigned drained;
    for(drained=0;drained<64;drained++) {
        if(t->clock(t->context)>=end)return -110;
        int64_t value=t->transfer(t->context,REIST_INPUT_READ,0,end);
        if(value==-11)break;if(value<0)return (int)value;
        if(t->sleep(t->context,10))return -5;
    }
    if(drained==64)return -75;
    if((r=transfer(t,REIST_INPUT_CONTROLLER,0x60,end)) || (r=transfer(t,REIST_INPUT_DATA,0x40,end)))return r;
    if((r=transfer(t,REIST_INPUT_CONTROLLER,0x20,end)) || (r=receive(t,0,0x40,end)))return r;
    for(unsigned aux=0;aux<2;aux++) {
        if((r=device(t,aux,0xff,end)) || (r=receive(t,aux,0xaa,end)))return r;
        if(aux && (r=receive(t,1,0,end)))return r;
        if((r=device(t,aux,0xf5,end)) || (r=device(t,aux,0xf6,end)))return r;
    }
    for(unsigned aux=0;aux<2;aux++)if((r=device(t,aux,0xf4,end)))return r;
    return 0;
}
