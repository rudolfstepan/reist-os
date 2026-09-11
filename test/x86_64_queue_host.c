#include "../arch/x86_64/proc/queue_core.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { printf("QUEUE_FAIL line=%d\n",__LINE__); return 1; } } while (0)
struct storage { uint64_t before, entries[128]; uint8_t members[64], meta[4]; uint64_t after; };
struct item { uint64_t tick; uint32_t slot, generation; };
static uint32_t random_state=0x12905;
static uint32_t rng(void) { random_state^=random_state<<13; random_state^=random_state>>17; random_state^=random_state<<5; return random_state; }
static uint64_t key(struct item v) { return ((uint64_t)v.generation<<32)|v.slot; }
static void init(struct storage *s, struct reist_x64_queue *q, unsigned cap, unsigned kind) {
    memset(s,0,sizeof *s); s->before=0x125671234ULL; s->after=0xdeadbeefULL;
    *q=(struct reist_x64_queue){s->entries,s->members,s->meta,cap,kind};
}
static int compare(const void *a,const void *b) {
    const struct item *x=a,*y=b;
    if(x->tick!=y->tick) return x->tick<y->tick?-1:1;
    return x->slot<y->slot?-1:x->slot!=y->slot;
}
static int match(struct storage *s,struct reist_x64_queue *q,struct item *m,unsigned n) {
    if(reist_x64_queue_apply(q,0,0,0,0)!=1 || s->meta[q->kind?0:2]!=n) return 0;
    for(unsigned i=0;i<n;i++) {
        if(q->kind) {
            struct reist_x64_deadline *d=(void*)s->entries;
            if(d[i].tick!=m[i].tick || d[i].slot!=m[i].slot || d[i].generation!=m[i].generation) return 0;
        } else if(s->entries[(s->meta[0]+i)%q->capacity]!=key(m[i])) return 0;
    }
    return s->before==0x125671234ULL && s->after==0xdeadbeefULL;
}
static int unchanged(struct reist_x64_queue *q,struct storage *s,uint64_t op,uint64_t slot,uint64_t gen,uint64_t tick) {
    struct storage before=*s;
    return reist_x64_queue_apply(q,op,slot,gen,tick)==0 && !memcmp(&before,s,sizeof before);
}
static int stress(unsigned cap,unsigned kind) {
    struct storage s; struct reist_x64_queue q; struct item model[64]; unsigned n=0;
    init(&s,&q,cap,kind);
    CHECK(unchanged(&q,&s,1,cap,1,1));
    CHECK(unchanged(&q,&s,1,0,0,1));
    CHECK(unchanged(&q,&s,1,0,UINT64_C(1)<<32,1));
    CHECK(unchanged(&q,&s,1,UINT64_MAX,1,1));
    CHECK(unchanged(&q,&s,9,0,1,1));
    CHECK(unchanged(&q,&s,2,0,0,0));
    CHECK(unchanged(&q,&s,3,0,1,0));
    if(kind) CHECK(unchanged(&q,&s,1,0,1,0));
    for(unsigned i=0;i<cap;i++) {
        struct item v={UINT64_MAX-(i%3),cap-1-i,UINT32_MAX-i};
        CHECK(reist_x64_queue_apply(&q,1,v.slot,v.generation,v.tick)==1);
        model[n++]=v;
        if(kind) qsort(model,n,sizeof *model,compare);
    }
    CHECK(match(&s,&q,model,n));
    CHECK(unchanged(&q,&s,1,0,77,1));
    for(unsigned i=0;i<cap*5;i++) {
        struct item v=model[0];
        CHECK(reist_x64_queue_apply(&q,2,0,0,0)==key(v));
        memmove(model,model+1,(--n)*sizeof *model);
        CHECK(reist_x64_queue_apply(&q,1,v.slot,v.generation,v.tick)==1);
        model[n++]=v;
        if(kind) qsort(model,n,sizeof *model,compare);
        CHECK(match(&s,&q,model,n));
    }
    for(unsigned step=0;step<12000;step++) {
        unsigned op=rng()%3+1, slot=rng()%cap, pos=n;
        uint32_t gen=(rng()|1U); uint64_t tick=(rng()%128)+1;
        for(unsigned i=0;i<n;i++) if(model[i].slot==slot) pos=i;
        if(op==1) {
            if(pos<n || n==cap) CHECK(unchanged(&q,&s,op,slot,gen,tick));
            else {
                CHECK(reist_x64_queue_apply(&q,op,slot,gen,tick)==1);
                model[n++]=(struct item){tick,slot,gen};
                if(kind) qsort(model,n,sizeof *model,compare);
            }
        } else if(op==2) {
            if(!n) CHECK(unchanged(&q,&s,op,0,0,0));
            else {
                CHECK(reist_x64_queue_apply(&q,op,0,0,0)==key(model[0]));
                memmove(model,model+1,(--n)*sizeof *model);
            }
        } else if(pos<n && (rng()&1)) {
            gen=model[pos].generation;
            CHECK(unchanged(&q,&s,op,slot,(uint64_t)gen+(UINT64_C(1)<<32),0));
            CHECK(reist_x64_queue_apply(&q,op,slot,gen,0)==1);
            memmove(model+pos,model+pos+1,(n-pos-1)*sizeof *model); --n;
            CHECK(unchanged(&q,&s,op,slot,gen,0));
            CHECK(reist_x64_queue_apply(&q,1,slot,gen==UINT32_MAX?1:gen+1,tick)==1);
            model[n++]=(struct item){tick,slot,gen==UINT32_MAX?1:gen+1};
            if(kind) qsort(model,n,sizeof *model,compare);
            CHECK(unchanged(&q,&s,op,slot,gen,0));
        } else {
            if(pos<n) gen=model[pos].generation==1?2:1;
            CHECK(unchanged(&q,&s,op,slot,gen,0));
        }
        CHECK(match(&s,&q,model,n));
    }
    while(n) { CHECK(reist_x64_queue_apply(&q,2,0,0,0)==key(model[0])); memmove(model,model+1,(--n)*sizeof *model); }
    CHECK(match(&s,&q,model,n));
    for(unsigned i=0;i<128;i++) CHECK(!s.entries[i]);
    return 0;
}
static int corrupt(unsigned kind) {
    struct storage s,good; struct reist_x64_queue q;
    init(&s,&q,4,kind);
    CHECK(reist_x64_queue_apply(&q,1,0,123,10)==1);
    CHECK(reist_x64_queue_apply(&q,1,1,456,20)==1);
    good=s;
    for(unsigned which=0;which<10;which++) {
        s=good;
        switch(which) {
        case 0:s.meta[kind?0:2]=5;break;
        case 1:s.members[0]=0;break;
        case 2:s.members[2]=1;break;
        case 3:s.members[0]=2;break;
        case 4:s.entries[kind?6:3]=99;break;
        case 5:if(kind)s.entries[3]=s.entries[1];else s.entries[1]=s.entries[0];break;
        case 6:if(kind)s.entries[1]|=UINT64_C(1)<<48;else s.meta[1]=4;break;
        case 7:if(kind)s.entries[2]=1;else s.meta[0]=4;break;
        case 8:if(kind)s.entries[1]&=~UINT64_C(0xffffffff);else s.entries[0]=1;break;
        case 9:if(kind)s.entries[1]=(UINT64_C(4)<<32)|123;else s.entries[0]=(UINT64_C(123)<<32)|4;break;
        }
        for(unsigned op=0;op<=3;op++) CHECK(unchanged(&q,&s,op,0,123,1));
    }
    s=good;
    q.capacity=0; CHECK(unchanged(&q,&s,0,0,0,0));
    q.capacity=65; CHECK(unchanged(&q,&s,0,0,0,0));
    q.capacity=4; q.kind=2; CHECK(unchanged(&q,&s,0,0,0,0));
    CHECK(!reist_x64_queue_apply(NULL,0,0,0,0));
    return 0;
}
int main(void) {
    const unsigned capacities[]={1,3,4,64};
    for(unsigned kind=0;kind<2;kind++) {
        for(unsigned i=0;i<4;i++) CHECK(!stress(capacities[i],kind));
        CHECK(!corrupt(kind));
    }
    puts("X86_64_QUEUE_HOST_OK capacities=1,3,4,64 model_steps=96000 kinds=2 corrupt_nonmutation=1");
    return 0;
}
