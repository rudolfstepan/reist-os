#include "native_heap.h"
#ifndef REIST_NATIVE_HEAP_HOST_TEST
#include "native_memory.h"
#include "arch/x86/include/interrupt.h"
uint64_t reist_native_heap_frame(bool user) {
    return reist_native_memory(user?NATIVE_MEMORY_USER_ALLOC:NATIVE_MEMORY_ALLOC,0);
}
void *reist_native_heap_pointer(uint64_t frame) {
    return (void *)(uintptr_t)(UINT64_C(0xffff800000000000)+frame);
}
void reist_native_heap_release(uint64_t frame) {
    if(reist_native_memory(NATIVE_MEMORY_FREE,frame)!=1)reist_native_heap_fault();
}
_Noreturn void reist_native_heap_fault(void) {
    __asm__ volatile("ud2");__builtin_unreachable();
}
#endif
__attribute__((section(".heap_state"),aligned(4096))) NativeHeapState native_heap_state;
#define H native_heap_state
#define NX UINT64_C(0x8000000000000000)
#define MASK UINT64_C(0x3fffff000)
enum { IDLE, ALLOCATE, COPY, RELEASE, ROLLBACK, REAP, TRIM };
static void need(bool value) {if(!value)reist_native_heap_fault();}
static bool chunk(const void *p,size_t n) {return p && n && n<=64;}
static void zero(void *p,size_t n) {unsigned char *q=p;for(size_t i=0;i<n;i++)q[i]=0;}
static void protect(critical_object_t *g,const void *p,size_t n,bool init) {
    need(!g->publication_lock);
    need((init?critical_object_init(g,1,p,n):critical_object_update(g,1,p,n,chunk))==0);
}
static void check(critical_object_t *g,const void *p,size_t n) {
    unsigned char copy[64];size_t length=0;
    need(!g->publication_lock);
    need(critical_object_read(g,1,copy,n,&length,chunk)>=0 && length==n);
    for(size_t i=0;i<n;i++)need(copy[i]==((const unsigned char*)p)[i]);
}
static void seal_control(NativeHeapTask *t,bool init) {
    for(unsigned i=0;i<2;i++)protect(&t->control_guards[i],(unsigned char*)&t->control+64*i,64,init);
}
static void control(NativeHeapTask *t) {
    for(unsigned i=0;i<2;i++)check(&t->control_guards[i],(unsigned char*)&t->control+64*i,64);
    NativeHeapControl *c=&t->control;
    need(c->generation<=UINT32_MAX && c->last_generation<=UINT32_MAX);
    need(c->budget==NATIVE_HEAP_LIMIT && c->used<=c->budget && !(c->used&4095));
    need(c->phase<=TRIM && c->region<128 && c->old_region<128 && c->scan<=256);
    need(!c->flags && !c->reserved);
}
static void seal_region(NativeHeapTask *t,unsigned i) {
    protect(&t->region_guards[i],&t->regions[i],sizeof(t->regions[i]),false);
}
static NativeHeapRegion *region(NativeHeapTask *t,unsigned i) {
    need(i<128);NativeHeapRegion *r=&t->regions[i];
    check(&t->region_guards[i],r,sizeof(*r));
    if(!r->state)need(!r->address && !r->requested && !r->mapped && !r->total);
    else {
        need(r->state<=2 && r->address>=NATIVE_HEAP_BASE && !(r->address&4095));
        need(r->address-NATIVE_HEAP_BASE<NATIVE_HEAP_LIMIT && r->total && !(r->total&4095));
        need(r->total<=NATIVE_HEAP_LIMIT-(r->address-NATIVE_HEAP_BASE));
        need(r->requested && r->requested<=r->total && r->mapped<=r->total && !(r->mapped&4095));
        need(r->state!=2 || r->mapped==r->total);
    }
    return r;
}
static void regions(NativeHeapTask *t) {
    uint64_t total=0;
    for(unsigned i=0;i<128;i++) {
        NativeHeapRegion *a=region(t,i);
        need(((t->control.occupied[i/64]>>(i%64))&1)==(a->state!=0));
        need(a->total<=NATIVE_HEAP_LIMIT-total);total+=a->total;
        if(!a->state)continue;
        for(unsigned j=0;j<i;j++) {
            NativeHeapRegion *b=&t->regions[j];
            need(!b->state || a->address>=b->address+b->total || b->address>=a->address+a->total);
        }
    }
    need(total==t->control.used);
}
static bool physical(uint64_t f) {return f && !(f&4095) && f<UINT64_C(0x400000000);}
static uint64_t *pointer(uint64_t f) {
    need(physical(f));uint64_t *p=reist_native_heap_pointer(f);
    need(p && !((uintptr_t)p&4095));return p;
}
static void seal_table(NativeHeapTask *t,unsigned i) {
    protect(&t->table_guards[i],&t->tables[i],sizeof(t->tables[i]),false);
}
static NativeHeapTable *table(NativeHeapTask *t,unsigned i) {
    need(i<256);NativeHeapTable *p=&t->tables[i];
    check(&t->table_guards[i],p,sizeof(*p));
    need(p->phase<=2 && p->used<=512);
    if(!p->phase)need(!p->pt && !p->used);
    else need(physical(p->pt));
    for(unsigned j=0;j<4;j++) {
        uint64_t f=p->guards[j];
        need(p->phase!=2 || physical(f));
        if(!f)continue;
        need(p->phase && physical(f) && f!=p->pt);
        for(unsigned k=0;k<j;k++)need(f!=p->guards[k]);
    }
    return p;
}
static uint64_t *directory(NativeHeapTask *t) {
    NativeHeapControl *c=&t->control;
    need((pointer(c->root)[0]&~UINT64_C(0x60))==(c->pdpt|7));
    uint64_t entry=pointer(c->pdpt)[4];
    if(!c->pd) {need(!entry);return NULL;}
    need((entry&~UINT64_C(0x60))==(c->pd|NX|7));return pointer(c->pd);
}
static critical_object_t *leaf_guard(NativeHeapTable *p,unsigned group) {
    need(p->phase==2 && group<64);
    return (critical_object_t*)pointer(p->guards[group/16])+(group%16);
}
static void leaves(NativeHeapTable *p,unsigned group,uint64_t words[8]) {
    uint64_t *raw=pointer(p->pt)+group*8;
    for(unsigned j=0;j<8;j++)words[j]=raw[j]&~UINT64_C(0x60);
    check(leaf_guard(p,group),words,64);
    for(unsigned j=0;j<8;j++)if(words[j]) {
        need((words[j]&~MASK)==(NX|7) && physical(words[j]&MASK));
        need((words[j]&MASK)!=p->pt);
        for(unsigned k=0;k<4;k++)need((words[j]&MASK)!=p->guards[k]);
    }
}
static uint64_t leaf(NativeHeapTask *t,uint64_t address) {
    unsigned index=(unsigned)((address-NATIVE_HEAP_BASE)>>21);
    NativeHeapTable *p=table(t,index);uint64_t *pd=directory(t);
    need(pd && p->phase==2 && (pd[index]&~UINT64_C(0x60))==(p->pt|NX|7));
    uint64_t words[8];unsigned offset=(unsigned)((address>>12)&511);
    leaves(p,offset/8,words);return words[offset%8];
}
static void write_leaf(NativeHeapTable *p,unsigned offset,uint64_t value) {
    uint64_t words[8];leaves(p,offset/8,words);words[offset%8]=value;
    pointer(p->pt)[offset]=value;
    protect(leaf_guard(p,offset/8),words,64,false);
}
/* All five metadata frames are registered before this bounded call returns. */
static bool prepare_table(NativeHeapTask *t,unsigned index,unsigned *work) {
    NativeHeapControl *c=&t->control;uint64_t *pd=directory(t);
    if(!pd) {
        uint64_t f=reist_native_heap_frame(false);++*work;if(!f)return false;
        need(physical(f));c->pd=f;seal_control(t,false);
        pointer(c->pdpt)[4]=f|NX|7;pd=directory(t);
    }
    NativeHeapTable *p=table(t,index);
    if(p->phase==2) {need((pd[index]&~UINT64_C(0x60))==(p->pt|NX|7));return true;}
    need(!pd[index]);
    if(!p->pt) {
        uint64_t f=reist_native_heap_frame(false);++*work;if(!f)return false;
        need(physical(f));p->pt=f;p->phase=1;seal_table(t,index);
    }
    for(unsigned j=0;j<4;j++)if(!p->guards[j]) {
        uint64_t f=reist_native_heap_frame(false);++*work;if(!f)return false;
        need(physical(f));p->guards[j]=f;seal_table(t,index);
    }
    uint64_t words[8]={0};
    for(unsigned group=0;group<64;group++) {
        uint64_t *raw=pointer(p->pt)+group*8;
        for(unsigned j=0;j<8;j++)need(!raw[j]);
        critical_object_t *g=(critical_object_t*)pointer(p->guards[group/16])+group%16;
        protect(g,words,64,true);
    }
    p->phase=2;seal_table(t,index);pd[index]=p->pt|NX|7;return true;
}
static void finish(NativeHeapTask *t,int64_t result) {
    NativeHeapControl *c=&t->control;
    c->result=(uint64_t)result;c->size=0;c->progress=0;
    c->operation=0;c->phase=IDLE;c->region=0;c->old_region=0;c->scan=0;
    seal_control(t,false);
}
static int find_region(NativeHeapTask *t,uint64_t address) {
    for(unsigned i=0;i<128;i++)if(t->regions[i].state==2 && t->regions[i].address==address)return (int)i;
    return -1;
}
static int64_t begin(NativeHeapTask *t,uint64_t operation,uint64_t address,uint64_t size) {
    NativeHeapControl *c=&t->control;need(c->phase==IDLE);regions(t);(void)directory(t);
    if(operation==NATIVE_HEAP_MALLOC) {size=address;address=0;}
    int old=-1;
    if(operation!=NATIVE_HEAP_MALLOC && address) {
        old=find_region(t,address);
        if(old<0)return operation==NATIVE_HEAP_FREE?-22:(!size?0:-12);
    }
    if(operation==NATIVE_HEAP_FREE || (operation==NATIVE_HEAP_REALLOC && !size)) {
        if(!address)return 0;
        c->operation=(uint32_t)operation;c->phase=RELEASE;c->region=(unsigned)old;
        c->result=0;t->regions[old].state=1;seal_region(t,(unsigned)old);seal_control(t,false);
        return NATIVE_HEAP_PENDING;
    }
    if(!size || size>NATIVE_HEAP_LIMIT)return -12;
    if(old>=0 && size<=t->regions[old].total) {
        t->regions[old].requested=size;seal_region(t,(unsigned)old);return (int64_t)address;
    }
    uint64_t total=(size+4095)&~UINT64_C(4095);
    if(total>c->budget-c->used)return -12;
    unsigned selected=128;
    for(unsigned i=0;i<128;i++)if(!t->regions[i].state){selected=i;break;}
    if(selected==128)return -12;
    uint64_t at=NATIVE_HEAP_BASE;
    for(unsigned pass=0;pass<=128;pass++) {
        if(at-NATIVE_HEAP_BASE>NATIVE_HEAP_LIMIT-total)return -12;
        bool overlap=false;
        for(unsigned i=0;i<128;i++) {
            NativeHeapRegion *r=&t->regions[i];if(!r->state)continue;
            if(at<r->address+r->total && r->address<at+total) {at=r->address+r->total;overlap=true;break;}
        }
        if(!overlap)break;
        if(pass==128)return -12;
    }
    t->regions[selected]=(NativeHeapRegion){at,size,0,total,1};seal_region(t,selected);
    c->occupied[selected/64]|=UINT64_C(1)<<(selected%64);
    c->used+=total;c->size=size;c->progress=0;c->result=(uint64_t)NATIVE_HEAP_PENDING;
    c->region=selected;c->old_region=old<0?selected:(unsigned)old;
    c->operation=old<0?NATIVE_HEAP_MALLOC:NATIVE_HEAP_REALLOC;c->phase=ALLOCATE;
    seal_control(t,false);return NATIVE_HEAP_PENDING;
}
static void release_page(NativeHeapTask *t,NativeHeapRegion *r,unsigned i) {
    need(r->mapped);uint64_t address=r->address+r->mapped-4096;
    unsigned index=(unsigned)((address-NATIVE_HEAP_BASE)>>21),offset=(unsigned)((address>>12)&511);
    uint64_t entry=leaf(t,address);need(entry);
    NativeHeapTable *p=&t->tables[index];need(p->used);
    write_leaf(p,offset,0); /* Current user cannot run until CR3 reload at dispatch. */
    reist_native_heap_release(entry&MASK);
    p->used--;seal_table(t,index);r->mapped-=4096;seal_region(t,i);
}
static void trim_one(NativeHeapTask *t,unsigned index,unsigned *work) {
    NativeHeapTable *p=table(t,index);++*work;
    if(!p->phase || p->used)return;
    uint64_t *pd=directory(t);need(pd);
    if(p->phase==2) {
        need((pd[index]&~UINT64_C(0x60))==(p->pt|NX|7));
        for(unsigned group=0;group<64;group++) {
            uint64_t words[8];leaves(p,group,words);
            for(unsigned j=0;j<8;j++)need(!words[j]);
        }
    } else need(!pd[index]);
    pd[index]=0;
    for(unsigned j=0;j<4;j++)if(p->guards[j]) {
        reist_native_heap_release(p->guards[j]);++*work;p->guards[j]=0;
    }
    reist_native_heap_release(p->pt);++*work;zero(p,sizeof(*p));seal_table(t,index);
}
static int64_t step(NativeHeapTask *t) {
    NativeHeapControl *c=&t->control;unsigned work=0;need(c->phase!=IDLE);
    while(work<58) { /* Six work slots remain for a table transaction. */
        if(c->phase==ALLOCATE) {
            NativeHeapRegion *r=region(t,c->region);
            if(r->mapped==r->total) {
                if(c->operation==NATIVE_HEAP_REALLOC) {c->phase=COPY;c->progress=0;}
                else {r->state=2;seal_region(t,c->region);finish(t,(int64_t)r->address);return (int64_t)c->result;}
            } else {
                uint64_t address=r->address+r->mapped;unsigned index=(unsigned)((address-NATIVE_HEAP_BASE)>>21);
                if(!prepare_table(t,index,&work)) {c->phase=ROLLBACK;c->result=(uint64_t)-12;}
                else {
                    need(!leaf(t,address));uint64_t frame=reist_native_heap_frame(true);work++;
                    if(!frame){c->phase=ROLLBACK;c->result=(uint64_t)-12;}
                    else {
                        need(physical(frame));NativeHeapTable *p=&t->tables[index];need(p->used<512);
                        write_leaf(p,(unsigned)((address>>12)&511),frame|NX|7);
                        p->used++;seal_table(t,index);r->mapped+=4096;seal_region(t,c->region);
                    }
                }
            }
        } else if(c->phase==COPY) {
            NativeHeapRegion *old=region(t,c->old_region),*r=region(t,c->region);
            if(c->progress==old->requested) {
                r->state=2;seal_region(t,c->region);c->result=r->address;
                c->region=c->old_region;old->state=1;seal_region(t,c->region);c->phase=RELEASE;
            } else {
                uint64_t src=leaf(t,old->address+c->progress),dst=leaf(t,r->address+c->progress);
                need(src && dst);uint64_t n=old->requested-c->progress;if(n>4096)n=4096;
                unsigned char *a=(unsigned char*)pointer(src&MASK),*b=(unsigned char*)pointer(dst&MASK);
                for(uint64_t i=0;i<n;i++)b[i]=a[i];c->progress+=n;work++;
            }
        } else if(c->phase==RELEASE || c->phase==ROLLBACK || c->phase==REAP) {
            NativeHeapRegion *r=region(t,c->region);
            if(r->mapped) {r->state=1;seal_region(t,c->region);release_page(t,r,c->region);work++;}
            else {
                need(c->used>=r->total);c->used-=r->total;zero(r,sizeof(*r));seal_region(t,c->region);work++;
                c->occupied[c->region/64]&=~(UINT64_C(1)<<(c->region%64));
                if(c->phase==REAP && c->region<127)c->region++;
                else {c->phase=TRIM;c->scan=0;}
            }
        } else if(c->phase==TRIM) {
            if(c->scan<256) {trim_one(t,c->scan,&work);c->scan++;}
            else {
                if(!c->used && c->pd) {
                    uint64_t *pd=directory(t);for(unsigned i=0;i<512;i++)need(!pd[i]);
                    pointer(c->pdpt)[4]=0;reist_native_heap_release(c->pd);c->pd=0;work++;
                }
                int64_t result=(int64_t)c->result;
                if(c->operation==NATIVE_HEAP_CANCEL) {
                    need(!c->used && !c->pd);c->last_generation=c->generation;c->generation=0;c->root=0;c->pdpt=0;result=0;
                }
                finish(t,result);return result;
            }
        } else need(false);
        seal_control(t,false);
    }
    return NATIVE_HEAP_PENDING;
}
static uint64_t access(NativeHeapTask *t,uint64_t address,uint64_t packed) {
    unsigned rights=(unsigned)(packed&7);uint64_t length=packed>>3;
    if(t->control.phase!=IDLE || (rights!=2 && rights!=4) || !length || length>2060 ||
       address<NATIVE_HEAP_BASE || address-NATIVE_HEAP_BASE>=NATIVE_HEAP_LIMIT ||
       length>NATIVE_HEAP_BASE+NATIVE_HEAP_LIMIT-address)return 0;
    uint64_t end=address+length;
    for(uint64_t at=address;at<end;at=(at&~UINT64_C(4095))+4096) {
        bool owned=false;
        /* Protected occupancy selects only live regions. Do not run128 ECC
         * reads for every short IPC header/copyout when one region is live. */
        for(unsigned word=0;word<2 && !owned;word++) {
            uint64_t bits=t->control.occupied[word];
            for(unsigned count=0;bits && count<64;count++,bits&=bits-1) {
                unsigned i=word*64+(unsigned)__builtin_ctzll(bits);
                NativeHeapRegion *r=region(t,i);need(r->state);
                if(r->state==2 && at>=r->address && at-r->address<r->total){owned=true;break;}
            }
        }
        if(!owned)return 0;need(leaf(t,at));
    }
    return 1;
}
uint64_t reist_native_heap(NativeHeapCall *call) {
    need(call && !((uintptr_t)call&7));
#ifndef REIST_NATIVE_HEAP_HOST_TEST
    need(!irq_enabled());
#endif
    need(!H.entered);H.entered=1;int64_t result=0;
    if(call->operation==NATIVE_HEAP_BOOT) {
        need(!H.initialized && !H.inverse && !H.reserved && !call->slot && !call->generation &&
             !call->root && !call->pdpt && !call->first && !call->second);
        for(unsigned slot=0;slot<4;slot++) {
            NativeHeapTask *t=&H.tasks[slot];
            const unsigned char *raw=(const unsigned char*)t;
            for(size_t i=0;i<sizeof(*t);i++)need(!raw[i]);
            t->control.budget=NATIVE_HEAP_LIMIT;seal_control(t,true);
            for(unsigned i=0;i<128;i++)protect(&t->region_guards[i],&t->regions[i],sizeof(t->regions[i]),true);
            for(unsigned i=0;i<256;i++)protect(&t->table_guards[i],&t->tables[i],sizeof(t->tables[i]),true);
        }
        H.initialized=1;H.inverse=~UINT32_C(1);protect(&H.guard,(const void*)&H.initialized,8,true);
    } else {
        check(&H.guard,(const void*)&H.initialized,8);need(H.initialized==1 && H.inverse==~UINT32_C(1));
        need(call->slot<4);NativeHeapTask *t=&H.tasks[call->slot];control(t);NativeHeapControl *c=&t->control;
        if(call->operation==NATIVE_HEAP_BIND) {
            need(!c->generation && !c->used && c->phase==IDLE && !call->first && !call->second);
            need(call->generation>c->last_generation && call->generation<=UINT32_MAX);
            need(physical(call->root) && physical(call->pdpt) && call->root!=call->pdpt);
            need((pointer(call->root)[0]&~UINT64_C(0x60))==(call->pdpt|7) && !pointer(call->pdpt)[4]);
            c->generation=call->generation;c->root=call->root;c->pdpt=call->pdpt;
            (void)directory(t);seal_control(t,false);
        } else if(call->operation==NATIVE_HEAP_CANCEL && !c->generation &&
                  call->generation && call->generation==c->last_generation) {
            /* Repeated retirement has no authority and no side effects. A stale
             * cancellation after a new bind still fails the live-owner check. */
            need(!call->first && !call->second && c->phase==IDLE && !c->used && !c->pd);
        } else {
            need(c->generation && call->generation==c->generation && call->root==c->root && call->pdpt==c->pdpt);
            switch(call->operation) {
            case NATIVE_HEAP_MALLOC: need(!call->second);result=begin(t,call->operation,call->first,0);break;
            case NATIVE_HEAP_FREE: need(!call->second);result=begin(t,call->operation,call->first,0);break;
            case NATIVE_HEAP_REALLOC:result=begin(t,call->operation,call->first,call->second);break;
            case NATIVE_HEAP_STEP:need(!call->first && !call->second);result=step(t);break;
            case NATIVE_HEAP_CANCEL:
                need(!call->first && !call->second);regions(t);
                c->operation=NATIVE_HEAP_CANCEL;c->phase=REAP;c->region=0;c->scan=0;c->result=0;
                seal_control(t,false);result=NATIVE_HEAP_PENDING;break;
            case NATIVE_HEAP_ACCESS:result=(int64_t)access(t,call->first,call->second);break;
            default:need(false);
            }
        }
    }
    need(H.entered==1);H.entered=0;call->result=(uint64_t)result;return 1;
}
