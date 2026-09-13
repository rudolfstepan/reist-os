#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "../userspace/storage/lib/native_block.c"
#include "../userspace/drivers/ata/native_pio.c"
#include "../userspace/drivers/ata/native_service.c"
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {
    reist_block_server server; x86os_ipc_bulk_message_t reply;
    uint64_t now;unsigned reads,sleeps,sends,receives,corrupt,fail,late,clock_reads,expire_on;
} Model;
static uint64_t clock_now(void *v){Model *m=v;if(++m->clock_reads==m->expire_on)m->now+=1000;return m->now;}
static int sleeping(void *v,unsigned ms){Model *m=v;CHECK(ms && ms<=100);m->now+=ms;m->sleeps++;return 0;}
static int reading(void *v,uint32_t lba,unsigned char *out,uint64_t deadline){
    Model *m=v;CHECK(m->now<deadline && lba<128);m->reads++;
    for(unsigned n=0;n<512;n++)out[n]=(unsigned char)(n^(lba*17)^0xa5);
    if(m->late)m->now=deadline;
    return m->fail?-5:0;
}
static int sending(void *v,const x86os_ipc_message_t *q,unsigned timeout){
    Model *m=v;CHECK(timeout && timeout<=1000);m->sends++;
    reist_block_backend b={m,clock_now,sleeping,reading};
    (void)reist_block_dispatch(&m->server,&b,q,&m->reply);
    if(m->corrupt)((unsigned char*)&m->reply)[m->corrupt-1]^=1;
    return 0;
}
static int receiving(void *v,x86os_ipc_bulk_message_t *reply,unsigned timeout){
    Model *m=v;CHECK(timeout && timeout<=1000);m->receives++;
    memcpy(reply,&m->reply,sizeof(*reply));return 0;
}
static void setup(Model *m,reist_block_client *c,reist_block_transport *t){
    memset(m,0,sizeof(*m));memset(c,0,sizeof(*c));m->now=100;
    CHECK(reist_block_server_init(&m->server,0x300000002ULL,128,m->now)==0);
    CHECK(reist_block_client_bind(c,0x300000002ULL)==0);
    *t=(reist_block_transport){m,clock_now,sending,receiving};
}
static void protocol(void){
    Model m;reist_block_client c;reist_block_transport t;unsigned char out[512],old[512];
    setup(&m,&c,&t);CHECK(sizeof(reist_block_header)==64);
    for(unsigned n=0;n<8;n++){
        unsigned lba=n==7?127:n;
        CHECK(reist_block_read(&c,&t,lba,out,1000)==0);
        for(unsigned i=0;i<512;i++)CHECK(out[i]==(unsigned char)(i^(lba*17)^0xa5));
        CHECK(m.reads==n+1 && m.server.next_sequence==n+2);
    }
    CHECK(reist_block_read(&c,&t,0,out,1000)==-11 && m.reads==8);
    CHECK(reist_block_client_bind(&c,0x300000002ULL)<0);
    CHECK(reist_block_client_bind(&c,0x400000002ULL)==0);
    memset(old,0x5a,sizeof(old));
    /* Every malformed reply header/tail byte: no output and no second send. */
    for(unsigned offset=0;offset<2060;offset++){
        if(offset>=12+64 && offset<12+64+512)continue; /* Data authenticity is the caller's media contract. */
        setup(&m,&c,&t);m.corrupt=offset+1;memcpy(out,old,512);
        CHECK(reist_block_read(&c,&t,0,out,1000)<0 && !memcmp(out,old,512));
        unsigned sends=m.sends;CHECK(reist_block_read(&c,&t,0,out,1000)<0 && m.sends==sends);
    }
    setup(&m,&c,&t);m.fail=1;memcpy(out,old,512);
    CHECK(reist_block_read(&c,&t,1,out,1000)==-5 && !memcmp(out,old,512));
    setup(&m,&c,&t);m.late=1;memcpy(out,old,512);
    CHECK(reist_block_read(&c,&t,1,out,1000)==-110 && !memcmp(out,old,512));
    setup(&m,&c,&t);CHECK(reist_block_read(&c,&t,0,out,1)==-110 && !m.reads);
    setup(&m,&c,&t);CHECK(reist_block_read(&c,&t,128,out,1000)==-22 && !m.reads);
    setup(&m,&c,&t);m.now=UINT64_MAX-10;CHECK(reist_block_read(&c,&t,0,out,1000)==-22 && !m.sends);
    setup(&m,&c,&t);CHECK(reist_block_read(&c,&t,1ULL<<28,out,1000)==-22 && !m.sends);
    setup(&m,&c,&t);m.expire_on=2;CHECK(reist_block_read(&c,&t,0,out,1000)==-110 && !m.sends);
    /* Raw request admission: replay/stale/wrong layout/deadline before read. */
    for(unsigned kind=0;kind<12;kind++){
        setup(&m,&c,&t);x86os_ipc_message_t q={1,140,64,{0}};
        reist_block_header h={1,64,1,0,c.owner,1,0,1100,512,0,0};
        if(kind==0)h.version=2;if(kind==1)h.size=63;if(kind==2)h.operation=2;
        if(kind==3)h.flags=1;if(kind==4)h.owner++;if(kind==5)h.sequence=0;
        if(kind==6)h.lba=128;if(kind==7)h.deadline_ms=100;if(kind==8)h.deadline_ms=1101;
        if(kind==9)h.length=511;if(kind==10)h.status=-5;if(kind==11)h.reserved=1;
        memcpy(q.payload,&h,64);reist_block_backend b={&m,clock_now,sleeping,reading};
        CHECK(reist_block_dispatch(&m.server,&b,&q,&m.reply)<0 && !m.reads && m.server.next_sequence==1);
    }
    setup(&m,&c,&t);x86os_ipc_message_t q={1,140,64,{0}};
    reist_block_header h={1,64,1,0,c.owner,1,0,1100,512,0,0};memcpy(q.payload,&h,64);
    reist_block_backend b={&m,clock_now,sleeping,reading};
    CHECK(reist_block_dispatch(&m.server,&b,&q,&m.reply)==0 && m.reads==1);
    CHECK(reist_block_dispatch(&m.server,&b,&q,&m.reply)==-116 && m.reads==1);
}
typedef struct {uint64_t now;unsigned calls,words,identify,lba,fail,late;} Ata;
static uint64_t ata_clock(void *v){return ((Ata*)v)->now;}
static int ata_sleep(void *v,unsigned ms){((Ata*)v)->now+=ms;return 0;}
static int64_t ata_port(void *v,reist_native_pio_request *q){
    Ata *a=v;if(++a->calls==a->fail)return -5;
    if(a->calls==a->late)a->now+=1000;
    if(q->version!=2 || !reist_x64_pio_deadline_ms(q))return -22;
    if(reist_x64_pio_deadline_ms(q)<=a->now)return -110;
    if(reist_x64_pio_deadline_ms(q)-a->now>1000)return -22;
    if(q->operation==REIST_PIO_WRITE8 && q->port==0x1f7){a->identify=q->value==0xec;a->words=0;}
    if(q->operation==REIST_PIO_WRITE8 && q->port==0x1f3)a->lba=q->value;
    if(q->operation==REIST_PIO_READ8)return a->words<256?0x48:0x40;
    if(q->operation==REIST_PIO_READ16){uint16_t *p=(void*)(uintptr_t)q->data;
        for(unsigned i=0;i<q->count;i++,a->words++)p[i]=a->identify?(a->words==49?512:a->words==60?128:0):
            (uint16_t)(((2*a->words)^(a->lba*17)^0xa5)&255)|
            (uint16_t)((((2*a->words+1)^(a->lba*17)^0xa5)&255)<<8);
    }return 0;
}
static void adapter(void){
    Ata a={0};reist_pio_ops ops={&a,ata_port,ata_clock,ata_sleep};reist_native_service s;
    CHECK(reist_native_service_init(&s,0x300000002ULL,&ops)==0 && s.server.capacity==128);
    unsigned calls=a.calls;
    for(unsigned n=1;n<=calls;n++){a=(Ata){.fail=n};CHECK(reist_native_service_init(&s,0x300000002ULL,&ops)<0 && !s.server.ready);}
    for(unsigned n=1;n<=calls;n++){a=(Ata){.late=n};CHECK(reist_native_service_init(&s,0x300000002ULL,&ops)==-110 && !s.server.ready);}
    a=(Ata){0};CHECK(reist_native_service_init(&s,0x300000002ULL,&ops)==0);
    x86os_ipc_message_t q={1,140,64,{0}};x86os_ipc_bulk_message_t reply;
    reist_block_header h={1,64,1,0,0x300000002ULL,1,127,a.now+1000,512,0,0};memcpy(q.payload,&h,64);
    CHECK(reist_native_service_dispatch(&s,&q,&reply)==0);
    for(unsigned i=0;i<512;i++)CHECK(reply.payload[64+i]==(unsigned char)(i^(127*17)^0xa5));
    CHECK(!s.deadline);
}
int main(void){protocol();adapter();puts("NATIVE_BLOCK_HOST_OK");return 0;}
