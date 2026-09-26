/* Bounded admission/state mechanism. Device policy and waits stay in Ring3. */
#include "video_mode.h"
static int overlap(uint64_t a,uint64_t n,uint64_t b,uint64_t m) {
    return a<b+m && b<a+n;
}
int reist_video_fifo_update(volatile uint32_t *fifo,unsigned minimum,
                           unsigned x,unsigned y,unsigned width,unsigned height,int publish) {
    if(!fifo || minimum<16 || minimum>4072 || minimum%4 || (publish!=0 && publish!=1) ||
       !width || !height || width>1024 || height>768 || x>1024-width || y>768-height ||
       (uint64_t)width*height>4096)return -22;
    unsigned min=fifo[0],max=fifo[1],next=fifo[2],stop=fifo[3];
    if(min!=minimum || max!=4096 || next<min || next>=max || next%4 ||
       stop<min || stop>=max || stop%4)return -5;
    unsigned available=stop>next?stop-next:max-next+stop-min;
    if(available<24)return -11; /* reserve one dword to distinguish full */
    if(!publish)return 0;
    const uint32_t update[5]={1,x,y,width,height}; /* SVGA_CMD_UPDATE */
    for(unsigned n=0;n<5;n++) {
        fifo[next/4]=update[n];next+=4;
        if(next==max)next=min;
    }
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
    fifo[2]=next;
    return 0;
}
int reist_video_resources_admit(const reist_video_pci *p,const reist_video_memory_range *map,
                               unsigned count,reist_video_resources *out) {
    if(!p || !map || !out || !count || count>128)return -22;
    if(p->id!=0x040515ad || p->class_revision>>8!=0x030000 || (p->header&127) ||
       (p->command&3)!=3 || p->command&~0xffffU)return -19;
    /* Sizes are established by the frozen virtual platform inventory, never
     * inferred from a guest request or merely from an SVGA size register. */
    if(p->profile==REIST_VIDEO_QEMU) {
        if(p->framebuffer_bytes!=16U*1024*1024 || p->fifo_bytes!=65536)return -19;
    } else if(p->profile==REIST_VIDEO_VMWARE) {
        if(p->framebuffer_bytes!=128U*1024*1024 || p->fifo_bytes!=8U*1024*1024)return -19;
    } else return -19;
    if((p->bar[0]&3)!=1 || (p->bar[1]&7) || (p->bar[2]&7))return -19;
    reist_video_resources r={p->bar[0]&~3U,p->bar[1]&~15U,p->framebuffer_bytes,
                             p->bar[2]&~15U,p->fifo_bytes};
    if(r.port<0x1000 || r.port>0xfff0 || r.port%16 ||
       r.framebuffer<0xc0000000 || r.framebuffer%r.framebuffer_bytes ||
       r.fifo<0xc0000000 || r.fifo%r.fifo_bytes ||
       (uint64_t)r.framebuffer+r.framebuffer_bytes>UINT64_C(0x100000000) ||
       (uint64_t)r.fifo+r.fifo_bytes>UINT64_C(0x100000000) ||
       overlap(r.framebuffer,r.framebuffer_bytes,r.fifo,r.fifo_bytes))return -19;
    /* The supported profiles must not cover APIC/firmware windows. */
    if(overlap(r.framebuffer,r.framebuffer_bytes,0xfec00000,0x1400000) ||
       overlap(r.fifo,r.fifo_bytes,0xfec00000,0x1400000))return -19;
    int usable=0;
    for(unsigned n=0;n<count;n++) {
        const reist_video_memory_range *e=&map[n];
        if(!e->length || e->base>UINT64_MAX-e->length || e->reserved || !e->type)return -22;
        if(e->type!=1)continue;
        usable=1;
        if(overlap(r.framebuffer,r.framebuffer_bytes,e->base,e->length) ||
           overlap(r.fifo,r.fifo_bytes,e->base,e->length))return -19;
    }
    if(!usable)return -19;
    *out=r;return 0;
}
static void seal(reist_video_state *s) {
    for(unsigned i=0;i<12;i++)s->inverse[i]=~s->word[i];
}
void reist_video_init(reist_video_state *s) {
    for(unsigned i=0;i<12;i++)s->word[i]=0;
    s->word[VM_FENCED]=1;seal(s);
}
static int child(uint64_t h) {
    return (uint32_t)h==5 && h>>32 && h>>32<=0x7fffffff;
}
static int parent(uint64_t h) {
    return !(uint32_t)h && h>>32 && h>>32<=0x7fffffff;
}
int reist_video_valid(const reist_video_state *s) {
    if(!s)return 0;
    for(unsigned i=0;i<12;i++)if(s->inverse[i]!=~s->word[i])return 0;
    const uint64_t *v=s->word;
    if(v[VM_PHASE]>REIST_VIDEO_REVOKING || v[VM_FENCED]>1 || v[VM_FAULT]>1 ||
       v[VM_LAST]>>60 || v[VM_HEALTH]>v[VM_LAST] || v[VM_DEADLINE]>>60 ||
       v[VM_NEXT]>REIST_VIDEO_STOP || v[VM_EPOCH]>>63 ||
       v[VM_RESERVED0] || v[VM_RESERVED1])return 0;
    if(v[VM_OWNER]) {
        if(!child(v[VM_OWNER]) || !parent(v[VM_PARENT]) || !v[VM_EPOCH])return 0;
    } else if(v[VM_PARENT] || !v[VM_FENCED] || v[VM_EPOCH])return 0;
    if(v[VM_FENCED] && (v[VM_PHASE]!=REIST_VIDEO_TEXT || v[VM_NEXT]))return 0;
    if(!v[VM_FENCED] && (!v[VM_OWNER] || v[VM_PHASE]==REIST_VIDEO_TEXT || !v[VM_DEADLINE]))return 0;
    if(v[VM_PHASE]==REIST_VIDEO_PREPARING && v[VM_NEXT]>REIST_VIDEO_READY)return 0;
    if(v[VM_PHASE]==REIST_VIDEO_GRAPHICS && v[VM_NEXT]!=REIST_VIDEO_STOP)return 0;
    return 1;
}
static int io_valid(const reist_video_io *io) {
    return io && io->step && io->fence;
}
static int fence(reist_video_state *s,const reist_video_io *io) {
    if(s->word[VM_FENCED])return s->word[VM_FAULT]?-5:0;
    /* Publish revocation before attempting any device cleanup. */
    s->word[VM_PHASE]=REIST_VIDEO_REVOKING;seal(s);
    int result=io->fence(io->context);
    s->word[VM_FENCED]=1;s->word[VM_PHASE]=REIST_VIDEO_TEXT;
    s->word[VM_NEXT]=0;s->word[VM_FAULT]=result!=0;seal(s);
    return result?-5:0;
}
int reist_video_retire(reist_video_state *s,uint64_t caller,const reist_video_io *io) {
    if(!reist_video_valid(s))return -84;
    if(!io_valid(io))return -22;
    if(!caller || (caller!=s->word[VM_OWNER] && caller!=s->word[VM_PARENT]))return 0;
    return fence(s,io);
}
int64_t reist_video_apply(reist_video_state *s,const reist_video_request_v1 *q,
                         uint64_t caller,uint64_t now,unsigned flags,const reist_video_io *io) {
    if(!reist_video_valid(s))return -84;
    if(!q || !io_valid(io))return -22;
    uint64_t *v=s->word;
    if(now>>60 || now<v[VM_LAST])return -84;
    if(q->version!=1 || q->size!=64 || q->operation<1 || q->operation>REIST_VIDEO_STATUS)return -22;
    for(unsigned i=0;i<4;i++)if(q->reserved[i])return -22;
    if(q->operation!=REIST_VIDEO_STEP && q->step)return -22;
    if(q->operation==REIST_VIDEO_BIND) {
        if(q->epoch || !child(q->owner))return -22;
        if(!parent(caller) || flags!=3)return -1;
        if(!v[VM_FENCED])return -16;
        if(v[VM_FAULT])return -5;
        if(v[VM_EPOCH]==INT64_MAX || now>((UINT64_C(1)<<60)-2001))return -75;
        v[VM_OWNER]=q->owner;v[VM_PARENT]=caller;v[VM_EPOCH]++;
        v[VM_PHASE]=REIST_VIDEO_PREPARING;v[VM_FENCED]=0;
        v[VM_LAST]=v[VM_HEALTH]=now;v[VM_DEADLINE]=now+2000;v[VM_NEXT]=0;
        seal(s);return (int64_t)v[VM_EPOCH];
    }
    if(!q->owner || q->owner!=v[VM_OWNER])return -116;
    if(q->operation==REIST_VIDEO_QUERY) {
        if(q->epoch)return -22;
        if(caller!=v[VM_OWNER] && caller!=v[VM_PARENT])return -1;
        return v[VM_FENCED]?-32:(int64_t)v[VM_EPOCH];
    }
    if(q->epoch!=v[VM_EPOCH])return -116;
    if(q->operation==REIST_VIDEO_FENCE || q->operation==REIST_VIDEO_STATUS) {
        if(caller!=v[VM_PARENT])return -1;
    } else if(caller!=v[VM_OWNER])return -1;
    if(q->operation==REIST_VIDEO_FENCE) {
        v[VM_LAST]=now;seal(s);return fence(s,io);
    }
    if(v[VM_FENCED])return -32;
    if(now-v[VM_HEALTH]>=1000)return -110;
    if(v[VM_PHASE]!=REIST_VIDEO_GRAPHICS && now>=v[VM_DEADLINE])return -110;
    if(q->operation==REIST_VIDEO_STATUS) {
        v[VM_LAST]=now;seal(s);return (int64_t)v[VM_PHASE];
    }
    if(q->operation==REIST_VIDEO_HEARTBEAT) {
        v[VM_LAST]=v[VM_HEALTH]=now;seal(s);return 0;
    }
    if(q->step==REIST_VIDEO_STOP) {
        v[VM_LAST]=now;return fence(s,io);
    }
    if(v[VM_PHASE]!=REIST_VIDEO_PREPARING || q->step!=v[VM_NEXT] || q->step>REIST_VIDEO_READY)return -22;
    int result=io->step(io->context,q->step);
    v[VM_LAST]=now;
    if(result) {
        (void)fence(s,io);
        return result<0 && result>=-4095?result:-5;
    }
    v[VM_NEXT]++;
    if(q->step==REIST_VIDEO_READY)v[VM_PHASE]=REIST_VIDEO_GRAPHICS;
    seal(s);return 0;
}

#ifdef REIST_NATIVE_VIDEO_MODE
/* Fixed-port hardware adapter. No user pointers, parsers, allocation or waits. */
static reist_video_state native_video_state={
    {0,0,0,0,1,0,0,0,0,0,0,0},
    {UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX-1,
     UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX}};
enum { HW_PORT,HW_FB,HW_FB_BYTES,HW_FIFO,HW_FIFO_BYTES,HW_PROFILE,
       HW_MIN,HW_MAPPED,HW_MAP_BASE,HW_ID,HW_COUNT };
static uint64_t hardware[HW_COUNT];
static uint64_t hardware_inverse[HW_COUNT]={UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,
    UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX};
static void hardware_seal(void) {
    for(unsigned n=0;n<HW_COUNT;n++)hardware_inverse[n]=~hardware[n];
}
static uint32_t port_read(unsigned port) {
    uint32_t v;__asm__ volatile("inl %w1,%0":"=a"(v):"d"((uint16_t)port));return v;
}
static void port_write(unsigned port,uint32_t value) {
    __asm__ volatile("outl %0,%w1"::"a"(value),"d"((uint16_t)port):"memory");
}
static uint32_t pci_read(unsigned slot,unsigned offset) {
    port_write(0xcf8,0x80000000U|(slot<<11)|offset);return port_read(0xcfc);
}
static uint32_t reg_read(unsigned index) {
    port_write((unsigned)hardware[HW_PORT],index);
    return port_read((unsigned)hardware[HW_PORT]+1);
}
static void reg_write(unsigned index,uint32_t value) {
    port_write((unsigned)hardware[HW_PORT],index);
    port_write((unsigned)hardware[HW_PORT]+1,value);
}
static int same12(const uint32_t words[3],const char *name) {
    const unsigned char *bytes=(const unsigned char *)words;
    for(unsigned n=0;n<12;n++)if(bytes[n]!=(unsigned char)name[n])return 0;
    return 1;
}
static int inventory(const reist_video_platform *p) {
    uint32_t a,b,c,d;
    __asm__ volatile("cpuid":"=a"(a),"=b"(b),"=c"(c),"=d"(d):"a"(0x40000000U),"c"(0));
    const uint32_t vendor[3]={b,c,d};
    unsigned profile=same12(vendor,"TCGTCGTCGTCG")?REIST_VIDEO_QEMU:
                     same12(vendor,"VMwareVMware")?REIST_VIDEO_VMWARE:0;
    if(!profile)return -19;
    unsigned found=32;
    for(unsigned slot=0;slot<32;slot++)if(pci_read(slot,0)==0x040515ad) {
        if(found!=32)return -19;found=slot;
    }
    if(found==32)return -19;
    reist_video_pci device={0};
    device.profile=profile;device.id=pci_read(found,0);
    device.class_revision=pci_read(found,8);device.command=pci_read(found,4)&0xffff;
    device.header=(pci_read(found,12)>>16)&255;
    for(unsigned n=0;n<3;n++)device.bar[n]=pci_read(found,16+4*n);
    device.framebuffer_bytes=profile==REIST_VIDEO_QEMU?16777216:134217728;
    device.fifo_bytes=profile==REIST_VIDEO_QEMU?65536:8388608;
    reist_video_resources r;
    if(p->range_count>128)return -19;
    int result=reist_video_resources_admit(&device,(const reist_video_memory_range *)(uintptr_t)p->ranges,
                                           (unsigned)p->range_count,&r);
    if(result)return result;
    hardware[HW_PORT]=r.port;hardware[HW_FB]=r.framebuffer;hardware[HW_FB_BYTES]=r.framebuffer_bytes;
    hardware[HW_FIFO]=r.fifo;hardware[HW_FIFO_BYTES]=r.fifo_bytes;hardware[HW_PROFILE]=profile;
    hardware_seal();return 0;
}
static void tlb_flush(void) {
    uint64_t cr3;__asm__ volatile("mov %%cr3,%0":"=r"(cr3));
    __asm__ volatile("mov %0,%%cr3"::"r"(cr3):"memory");
}
static uint64_t physical(uint64_t pointer) { return pointer-UINT64_C(0xffffffff80000000); }
static void unmap(const reist_video_platform *p) {
    ((volatile uint64_t *)(uintptr_t)p->pdpt)[509]=0;
    tlb_flush();
    uint64_t *boot=(uint64_t *)(uintptr_t)p->boot,*inverse=(uint64_t *)(uintptr_t)p->boot_inverse;
    for(unsigned n=0;n<4;n++){boot[n]=0;inverse[n]=UINT64_MAX;}
    hardware[HW_MAPPED]=hardware[HW_MAP_BASE]=hardware[HW_MIN]=0;hardware_seal();
}
static int hardware_fence(void *context) {
    const reist_video_platform *p=context;
    int64_t (*display_fence)(uint64_t)=(void *)(uintptr_t)p->fence_display;
    if(display_fence(native_video_state.word[VM_PARENT]))return -5;
    unmap(p);
    if(!hardware[HW_PORT])return 0;
    reg_write(20,0);reg_write(1,0);
    if(reg_read(1)&1)return -5;
    *(volatile unsigned char *)(uintptr_t)p->text_ready=1;
    return 0;
}
static int map_framebuffer(const reist_video_platform *p) {
    if(reg_read(2)!=1024 || reg_read(3)!=768 || reg_read(7)!=32 || !(reg_read(1)&1) ||
       reg_read(12)!=4096 || reg_read(13)!=hardware[HW_FB] ||
       reg_read(15)!=hardware[HW_FB_BYTES] || reg_read(19)!=hardware[HW_FIFO_BYTES])return -5;
    uint32_t offset=reg_read(14),bytes=reg_read(16),fifo=reg_read(18),regs=reg_read(30);
    if((offset&4095) || offset>hardware[HW_FB_BYTES] ||
       bytes>hardware[HW_FB_BYTES]-offset || bytes<3U*1024*1024 ||
       (fifo && fifo!=hardware[HW_FIFO]) || regs>1018)return -5;
    if(!regs)regs=4;
    if(regs<4)return -5;
    uint64_t base=hardware[HW_FB]+offset;
    uint64_t *pdpt=(void *)(uintptr_t)p->pdpt,*pd=(void *)(uintptr_t)p->pd;
    uint64_t *pts=(void *)(uintptr_t)p->pts,*fp=(void *)(uintptr_t)p->fifo_pt;
    if(pdpt[509])return -16;
    for(unsigned n=0;n<3072;n++)pts[n]=n<768?(base+n*4096)|UINT64_C(0x800000000000001b):0;
    for(unsigned n=0;n<512;n++){pd[n]=0;fp[n]=0;}
    for(unsigned n=0;n<6;n++)pd[n]=(physical(p->pts)+n*4096)|3;
    pd[6]=physical(p->fifo_pt)|3;
    fp[0]=hardware[HW_FIFO]|UINT64_C(0x800000000000001b);
    pdpt[509]=physical(p->pd)|3;tlb_flush();
    uint64_t *boot=(void *)(uintptr_t)p->boot,*inv=(void *)(uintptr_t)p->boot_inverse;
    boot[0]=base;boot[1]=((uint64_t)1024<<32)|4096;
    boot[2]=((uint64_t)(3U*1024*1024)<<32)|768;
    boot[3]=((uint64_t)(3U*1024*1024)<<32)|base;
    for(unsigned n=0;n<4;n++)inv[n]=~boot[n];
    hardware[HW_MAPPED]=1;hardware[HW_MAP_BASE]=base;hardware[HW_MIN]=regs*4;
    hardware_seal();return 0;
}
static int hardware_step(void *context,unsigned step) {
    const reist_video_platform *p=context;
    if(step==REIST_VIDEO_ID) {
        int r=inventory(p);if(r)return r;
        reg_write(0,0x90000002);
        if(reg_read(0)!=0x90000002)return -19;
        hardware[HW_ID]=0x90000002;hardware_seal();
        return reg_read(4)>=1024 && reg_read(5)>=768?0:-19;
    }
    if(!hardware[HW_PORT] || hardware[HW_ID]!=0x90000002)return -5;
    switch(step) {
        case REIST_VIDEO_DISABLE:reg_write(1,0);return reg_read(1)&1?-5:0;
        case REIST_VIDEO_WIDTH:reg_write(2,1024);return 0;
        case REIST_VIDEO_HEIGHT:reg_write(3,768);return 0;
        case REIST_VIDEO_BPP:reg_write(7,32);return 0;
        case REIST_VIDEO_ENABLE:
            *(volatile unsigned char *)(uintptr_t)p->text_ready=0;
            reg_write(1,1);return reg_read(1)&1?0:-5;
        case REIST_VIDEO_MAP:return map_framebuffer(p);
        case REIST_VIDEO_CONFIGURE: {
            if(!hardware[HW_MAPPED])return -5;
            volatile uint32_t *fifo=(void *)(uintptr_t)UINT64_C(0xffffffff40c00000);
            fifo[0]=(uint32_t)hardware[HW_MIN];fifo[1]=4096;
            fifo[2]=fifo[3]=(uint32_t)hardware[HW_MIN];
            if(hardware[HW_MIN]>=1164)fifo[290]=0;
            __atomic_thread_fence(__ATOMIC_SEQ_CST);reg_write(20,1);return 0;
        }
        case REIST_VIDEO_READY:
            return hardware[HW_MAPPED] && reg_read(1)&1 && reg_read(2)==1024 &&
                   reg_read(3)==768 && reg_read(12)==4096?0:-5;
        default:return -22;
    }
}
int reist_native_video(reist_video_call *call) {
    if(!call || !call->platform)return 0;
    for(unsigned n=0;n<HW_COUNT;n++)if(hardware_inverse[n]!=~hardware[n])return 0;
    if(hardware[HW_MAPPED]>1 || (hardware[HW_PORT] &&
       (hardware[HW_PORT]<0x1000 || hardware[HW_PORT]>0xfff0 || hardware[HW_PORT]%16)))return 0;
    reist_video_platform *p=(void *)(uintptr_t)call->platform;
    const reist_video_io io={p,hardware_step,hardware_fence};
    if(call->mode==0)call->result=reist_video_apply(&native_video_state,&call->request,
        call->caller,call->now,(unsigned)call->relation,&io);
    else if(call->mode==1)call->result=reist_video_retire(&native_video_state,call->caller,&io);
    else if(call->mode==2) {
        call->result=reist_video_valid(&native_video_state)&&native_video_state.word[VM_FENCED]?0:-84;
        /* The complete root lifetime ends; preserve hardware-fault quarantine. */
        if(!call->result && !native_video_state.word[VM_FAULT])reist_video_init(&native_video_state);
    } else if(call->mode==5) {
        call->result=reist_video_valid(&native_video_state)?(int64_t)native_video_state.word[VM_OWNER]:-84;
    } else if(call->mode==3 || call->mode==4) {
        if(!reist_video_valid(&native_video_state))return 0;
        if(native_video_state.word[VM_FENCED] || native_video_state.word[VM_PHASE]!=REIST_VIDEO_GRAPHICS ||
           !hardware[HW_MAPPED])call->result=-32;
        else if(call->now<native_video_state.word[VM_LAST] || call->now>>60)return 0;
        else if(call->now-native_video_state.word[VM_HEALTH]>=1000)call->result=-110;
        else {
            call->result=reist_video_fifo_update((void *)(uintptr_t)UINT64_C(0xffffffff40c00000),
                (unsigned)hardware[HW_MIN],call->request.version,call->request.size,
                call->request.operation,call->request.step,call->mode==4);
            if(!call->result && call->mode==4)reg_write(21,1);
        }
    } else return 0;
    return call->result!=-84;
}
#endif
