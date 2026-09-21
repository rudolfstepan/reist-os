/* Validated DMA resource mediator. No packet/protocol interpretation. */
#include "network_dma.h"
#include <stddef.h>
enum { OWNER,PARENT,EPOCH,FENCED,WINDOW,LAST,OPERATIONS,PHASE,IO,PCI,RX_OFFSET,
       PENDING,END0,END1,END2,END3,TRANSFERS,TX_COUNT,RX_COUNT };
static void clear(volatile void *p,size_t n) { volatile unsigned char *b=p;while(n--)*b++=0; }
static void seal(network_dma_state *s) { for(unsigned n=0;n<24;n++)s->inverse[n]=~s->words[n]; }
void network_dma_init(network_dma_state *s) { clear(s,sizeof(*s));s->words[FENCED]=1;seal(s); }
static int owner_valid(uint64_t o) { return (uint32_t)o>=2 && (uint32_t)o<8 && o>>32 && o>>32<=0x7fffffff; }
int network_dma_valid(const network_dma_state *s) {
    if(!s)return 0;
    for(unsigned n=0;n<24;n++)if(s->inverse[n]!=~s->words[n])return 0;
    const uint64_t *v=s->words;
    if(v[FENCED]>1 || v[PHASE]>2 || v[OPERATIONS]>128 || v[WINDOW]>v[LAST] ||
       v[LAST]>>60 || v[EPOCH]>>63 || v[RX_OFFSET]>=8192 || v[RX_OFFSET]%4 || v[PENDING]>15)return 0;
    if(v[OWNER]) {
        if(!owner_valid(v[OWNER]) || (uint32_t)v[PARENT] || !v[PARENT] ||
           v[PARENT]>>32>0x7fffffff || !v[EPOCH])return 0;
    } else if(v[PARENT] || !v[FENCED] || v[PHASE])return 0;
    if(v[IO] && (v[IO]<0x1000 || v[IO]>0xff00 || v[IO]%256 || v[PCI]!=0x80002000))return 0;
    if(!v[IO] && (v[PCI] || v[PHASE]))return 0;
    if(v[FENCED] && (v[PHASE] || v[PENDING]))return 0;
    for(unsigned n=0;n<4;n++)if((v[PENDING]>>n&1)!=(v[END0+n]!=0) || v[END0+n]>>60)return 0;
    for(unsigned n=19;n<24;n++)if(v[n])return 0;
    return 1;
}
static uint32_t rd(const network_dma_io *i,unsigned p,unsigned w) { return i->read(i->context,p,w); }
static void wr(const network_dma_io *i,unsigned p,unsigned w,uint32_t v) { i->write(i->context,p,w,v); }
static uint32_t pci_read(const network_dma_io *i,unsigned offset) { wr(i,0xcf8,4,0x80002000|offset);return rd(i,0xcfc,4); }
static void pci_command(const network_dma_io *i,uint16_t value) { wr(i,0xcf8,4,0x80002004);wr(i,0xcfc,2,value); }
static int envelope(const network_dma_io *i) {
    return i && i->memory && i->read && i->write && i->rx_physical>=0x100000 &&
        i->tx_physical>=0x100000 && !(i->rx_physical&255) && !(i->tx_physical&255) &&
        i->rx_physical<=UINT32_MAX-10240 && i->tx_physical<=UINT32_MAX-8192 &&
        ((uint64_t)i->rx_physical+10240<=i->tx_physical || (uint64_t)i->tx_physical+8192<=i->rx_physical);
}
static int fence(network_dma_state *s,const network_dma_io *i) {
    uint64_t *v=s->words;
    if(v[IO]) {
        unsigned p=(unsigned)v[IO];
        wr(i,p+0x3c,2,0);wr(i,p+0x37,1,0);
        uint32_t cmd=pci_read(i,4);pci_command(i,(uint16_t)(cmd&~4U));
        if((pci_read(i,4)&4) || rd(i,p+0x3c,2) || (rd(i,p+0x37,1)&12))return -84;
    }
    clear(i->memory,sizeof(*i->memory));v[FENCED]=1;v[PHASE]=0;v[PENDING]=0;v[RX_OFFSET]=0;
    for(unsigned n=0;n<4;n++)v[END0+n]=0;
    seal(s);return 0;
}
int64_t network_dma_retire(network_dma_state *s,uint64_t who,const network_dma_io *i) {
    if(!envelope(i) || !network_dma_valid(s))return -84;
    return who && (who==s->words[OWNER] || who==s->words[PARENT])?fence(s,i):0;
}
static int reset(network_dma_state *s,const network_dma_io *i) {
    uint64_t *v=s->words;
    if(pci_read(i,0)!=0x813910ec)return -19;
    uint32_t bar=pci_read(i,0x10);
    if(!(bar&1) || (bar&3)!=1 || (bar&~255U)<0x1000 || (bar&~255U)>0xff00 || (bar&0xfc))return -19;
    v[IO]=bar&~255U;v[PCI]=0x80002000;
    /* No programmable DMA address is exposed to the owner. */
    uint32_t command=pci_read(i,4);pci_command(i,(uint16_t)((command|1)&~4U));
    if(pci_read(i,4)&4)return -84;
    int r=fence(s,i);if(r)return r;
    wr(i,(unsigned)v[IO]+0x37,1,16);v[PHASE]=1;v[FENCED]=0;return 0;
}
static int start(network_dma_state *s,const network_dma_io *i) {
    uint64_t *v=s->words;unsigned p=(unsigned)v[IO];
    if(v[PHASE]!=1)return -16;
    if(rd(i,p+0x37,1)&16)return -11;
    wr(i,p+0x3c,2,0);wr(i,p+0x3e,2,0xffff);
    wr(i,p+0x30,4,i->rx_physical);
    for(unsigned n=0;n<4;n++)wr(i,p+0x20+n*4,4,i->tx_physical+n*2048);
    wr(i,p+0x38,2,0xfff0);wr(i,p+0x44,4,0x78a); /* 8KiB, wrap slack, own+broadcast. */
    wr(i,p+0x40,4,0x03000700); /* Fixed C-mode TX; never C+ descriptors. */
    uint32_t command=pci_read(i,4);pci_command(i,(uint16_t)(command|5));
    if((pci_read(i,4)&5)!=5)return -84;
    wr(i,p+0x37,1,12);
    if((rd(i,p+0x37,1)&12)!=12)return -5;
    v[PHASE]=2;return 0;
}
int64_t network_dma_apply(network_dma_state *s,const reist_network_request_v1 *q,
    uint64_t caller,uint64_t now,unsigned relation,unsigned char *payload,const network_dma_io *i) {
    if(!envelope(i) || !network_dma_valid(s) || now>>60 || now<s->words[LAST])return -84;
    uint64_t *v=s->words;
    if(!q || q->version!=1 || q->size!=64 || q->flags || q->reserved ||
       q->operation<1 || q->operation>9 || !owner_valid(q->owner))return -22;
    unsigned op=q->operation;
    if(op==1) {
        if((uint32_t)caller || !caller || caller>>32>0x7fffffff || relation!=3)return -13;
        if(q->epoch || q->deadline_ms || q->address || q->length || q->index)return -22;
        if(!v[FENCED])return -16;
        if(q->owner>>32<=v[OWNER]>>32)return -116;
        if(v[EPOCH]==INT64_MAX)return -75;
        v[OWNER]=q->owner;v[PARENT]=caller;++v[EPOCH];v[FENCED]=0;v[LAST]=now;seal(s);return (int64_t)v[EPOCH];
    }
    if(q->owner!=v[OWNER] || q->epoch!=v[EPOCH])return -116;
    if(op==8) {
        if(caller!=v[OWNER] && caller!=v[PARENT])return -13;
        if(q->deadline_ms || q->address || q->length || q->index)return -22;
        int result=fence(s,i);if(!result){v[LAST]=now;seal(s);}return result;
    }
    if(caller!=v[OWNER] || v[FENCED])return -13;
    if(op==2) {
        if(q->deadline_ms || q->address || q->length || q->index)return -22;
        return (int64_t)v[EPOCH];
    }
    if(q->deadline_ms<=now)return -110;
    if(q->deadline_ms-now>1000)return -22;
    if(op==5 || op==6) {
        if(!q->address || !payload || q->index>3 || (op==6 && q->index) ||
           (op==5 && (q->length<14 || q->length>1514)) || (op==6 && q->length!=1536))return -22;
    } else if(q->address || q->length || q->index>(op==7?3U:0U))return -22;
    if(op!=3 && op!=4 && v[PHASE]!=2)return -16;
    if((op==5 || op==6) && (v[TRANSFERS]==UINT64_MAX || v[TX_COUNT]==UINT64_MAX || v[RX_COUNT]==UINT64_MAX))return -75;
    if(now-v[WINDOW]>=100){v[WINDOW]=now;v[OPERATIONS]=0;}
    if(v[OPERATIONS]==128)return -122;
    ++v[OPERATIONS];v[LAST]=now;
    int64_t result=0;unsigned p=(unsigned)v[IO],slot=q->index;
    if(op==3)result=reset(s,i);
    else if(op==4)result=start(s,i);
    else if(op==5) {
        if(v[PENDING]&(1U<<slot))result=-11;
        else {
            unsigned length=q->length<60?60:q->length;
            for(unsigned n=0;n<length;n++)i->memory->tx[slot][n]=n<q->length?payload[n]:0;
            v[PENDING]|=1U<<slot;v[END0+slot]=now+100;
            wr(i,p+0x10+4*slot,4,length);++v[TRANSFERS];++v[TX_COUNT];
        }
    } else if(op==7) {
        if(!(v[PENDING]&(1U<<slot)))result=-116;
        else {
            uint32_t status=rd(i,p+0x10+4*slot,4);
            if(status&((1U<<30)|(1U<<14)))result=-5;
            else if(status&(1U<<15)){v[PENDING]&=~(1ULL<<slot);v[END0+slot]=0;}
            else result=now>=v[END0+slot]?-110:-11;
        }
    } else if(op==6) {
        if(rd(i,p+0x37,1)&1)result=-11;
        else {
            unsigned offset=(unsigned)v[RX_OFFSET];volatile unsigned char *rx=i->memory->rx;
            unsigned status=rx[offset]|(unsigned)rx[offset+1]<<8,length=rx[offset+2]|(unsigned)rx[offset+3]<<8;
            if(!(status&1) || status&0x3e || length<18 || length>1518)result=-5;
            else {
                for(unsigned n=0;n<length-4;n++)payload[n]=rx[offset+4+n];
                v[RX_OFFSET]=(offset+4+length+3)&8188;
                wr(i,p+0x38,2,(uint16_t)(v[RX_OFFSET]-16));
                wr(i,p+0x3e,2,1);++v[TRANSFERS];++v[RX_COUNT];result=length-4;
            }
        }
    } else if(op==9) {
        for(unsigned n=0;n<6;n++)result|=(uint64_t)(rd(i,p+n,1)&255)<<(n*8);
    }
    if(result==-5 || result==-110 || result==-84){if(fence(s,i))return -84;}
    seal(s);return result;
}

#ifdef REIST_NATIVE_NETWORK_DMA
/* Only this native build links hardware access and the pinned supervisor BSS. */
network_dma_state native_network_state={
    {0,0,0,1}, {~0ULL,~0ULL,~0ULL,~1ULL,~0ULL,~0ULL,~0ULL,~0ULL,
    ~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,
    ~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,~0ULL,~0ULL}};
network_dma_memory native_network_dma __attribute__((aligned(256)));
static uint32_t native_read(void *p,unsigned port,unsigned width) {
    (void)p;uint32_t value=0;
    if(width==1){unsigned char v;__asm__ volatile("inb %w1,%0":"=a"(v):"d"((uint16_t)port):"memory");value=v;}
    else if(width==2){uint16_t v;__asm__ volatile("inw %w1,%0":"=a"(v):"d"((uint16_t)port):"memory");value=v;}
    else __asm__ volatile("inl %w1,%0":"=a"(value):"d"((uint16_t)port):"memory");
    return value;
}
static void native_write(void *p,unsigned port,unsigned width,uint32_t value) {
    (void)p;
    if(width==1)__asm__ volatile("outb %b0,%w1"::"a"((uint8_t)value),"d"((uint16_t)port):"memory");
    else if(width==2)__asm__ volatile("outw %w0,%w1"::"a"((uint16_t)value),"d"((uint16_t)port):"memory");
    else __asm__ volatile("outl %0,%w1"::"a"(value),"d"((uint16_t)port):"memory");
}
/* Private 112-byte C boundary, already copied/range-checked by assembly. */
typedef struct {reist_network_request_v1 request;uint64_t caller,now,relation,mode,payload;int64_t result;} network_call;
uint32_t reist_native_network(network_call *c) {
    uintptr_t address=(uintptr_t)&native_network_dma;
    if(address<0xffffffff801a1000ULL || address+sizeof(native_network_dma)>0xffffffff801e1000ULL)return 0;
    network_dma_io io={0,native_read,native_write,(uint32_t)(address-0xffffffff80000000ULL),
        (uint32_t)(address+10240-0xffffffff80000000ULL),&native_network_dma};
    if(c->mode==4) {
        if(pci_read(&io,0)==0x813910ec) {
            uint32_t command=pci_read(&io,4);pci_command(&io,(uint16_t)(command&~4U));
            (void)pci_read(&io,4);
        }
        return 1;
    }
    if(c->mode==0)c->result=network_dma_apply(&native_network_state,&c->request,c->caller,c->now,
        (unsigned)c->relation,(unsigned char*)(uintptr_t)c->payload,&io);
    else if(c->mode==1)c->result=network_dma_retire(&native_network_state,c->caller,&io);
    else if(c->mode==2) {
        c->result=network_dma_valid(&native_network_state)&&native_network_state.words[FENCED]?0:-84;
        if(!c->result){native_network_state.words[OWNER]=native_network_state.words[PARENT]=0;seal(&native_network_state);}
    } else if(c->mode==3)c->result=network_dma_valid(&native_network_state)?(int64_t)native_network_state.words[OWNER]:-84;
    else return 0;
    if(c->result==-84) {
        /* Do not trust corrupt software IO metadata. Disable bus mastering
         * using the fixed PCI function before the kernel fatal transition. */
        if(pci_read(&io,0)==0x813910ec) {
            uint32_t command=pci_read(&io,4);pci_command(&io,(uint16_t)(command&~4U));
            (void)pci_read(&io,4);
        }
        return 0;
    }
    return 1;
}
#endif
