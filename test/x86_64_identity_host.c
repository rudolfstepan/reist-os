#include "../arch/x86_64/proc/identity_core.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if(!(x)){printf("IDENTITY_FAIL line=%d\n",__LINE__);return 1;} } while(0)
struct storage { uint64_t before,tasks[64][32]; uint32_t retired[64]; uint64_t after; };
static void init(struct storage *s,struct reist_x64_identity_pool *p,unsigned cap,uint32_t last) {
    memset(s,0,sizeof *s);s->before=0x12345678;s->after=0xdeadbeef;
    *p=(struct reist_x64_identity_pool){s->tasks,s->retired,cap,last};
}
static int denied(struct reist_x64_identity_pool *p,struct storage *s,uint64_t op,uint64_t slot,uint64_t gen) {
    struct storage snapshot=*s;struct reist_x64_identity_pool prior=*p;
    return !reist_x64_identity_apply(p,op,slot,gen) && !memcmp(&snapshot,s,sizeof snapshot) && !memcmp(&prior,p,sizeof prior);
}
static void constructed(uint64_t *t) { t[2]=0x2000;t[3]=0x3000;t[12]=0x400078;t[13]=0x409000; }
static void released(uint64_t *t) { for(unsigned i=2;i<12;i++)t[i]=0; }
static int lifecycle(unsigned cap) {
    struct storage s;struct reist_x64_identity_pool p;uint32_t expected=39;
    init(&s,&p,cap,expected);
    CHECK(reist_x64_identity_apply(&p,0,0,0)==1);
    CHECK(denied(&p,&s,1,cap,0));CHECK(denied(&p,&s,1,UINT64_MAX,0));
    CHECK(denied(&p,&s,1,0,1));CHECK(denied(&p,&s,3,0,0));
    CHECK(denied(&p,&s,3,0,39));CHECK(denied(&p,&s,4,0,0));
    for(unsigned round=0;round<128;round++) {
        for(unsigned slot=0;slot<cap;slot++) {
            uint32_t old=s.retired[slot];
            uint64_t v=reist_x64_identity_apply(&p,1,slot,0);++expected;
            CHECK(v==((uint64_t)expected<<32|slot));
            CHECK(s.tasks[slot][0]==9 && s.tasks[slot][1]==expected && p.last_generation==expected);
            CHECK(denied(&p,&s,1,slot,0));CHECK(denied(&p,&s,2,slot,expected));
            CHECK(denied(&p,&s,3,slot,expected+(UINT64_C(1)<<32)));
            if(old) CHECK(denied(&p,&s,3,slot,old));
            if(round%3==0) { /* rollback reservation burns identity */
                CHECK(reist_x64_identity_apply(&p,3,slot,expected)==1);
            } else {
                constructed(s.tasks[slot]);
                CHECK(reist_x64_identity_apply(&p,2,slot,expected)==1);
                CHECK(s.tasks[slot][0]==1);CHECK(denied(&p,&s,2,slot,expected));
                for(unsigned state=1;state<=7;state++) if(state!=3 && state!=4) {
                    s.tasks[slot][0]=state; released(s.tasks[slot]);
                    CHECK(denied(&p,&s,3,slot,expected));
                }
                s.tasks[slot][0]=(round%2)?3:8;
                for(unsigned field=2;field<12;field++) {
                    s.tasks[slot][field]=0x4000;
                    CHECK(denied(&p,&s,3,slot,expected));s.tasks[slot][field]=0;
                }
                CHECK(reist_x64_identity_apply(&p,3,slot,expected)==1);
            }
            CHECK(s.retired[slot]==expected);
            for(unsigned i=0;i<32;i++) CHECK(s.tasks[slot][i]==0);
            struct storage before=s;
            CHECK(reist_x64_identity_apply(&p,3,slot,expected)==1);
            CHECK(!memcmp(&before,&s,sizeof s));
        }
    }
    CHECK(s.before==0x12345678 && s.after==0xdeadbeef);
    /* All slots live at once, duplicate/corrupt namespace must not mutate. */
    for(unsigned i=0;i<cap;i++) CHECK(reist_x64_identity_apply(&p,1,i,0));
    CHECK(denied(&p,&s,1,0,0));
    if(cap>1) {
        uint64_t saved=s.tasks[1][1];s.tasks[1][1]=s.tasks[0][1];
        for(unsigned op=0;op<4;op++) CHECK(denied(&p,&s,op,0,s.tasks[0][1]));
        s.tasks[1][1]=saved;
    }
    for(unsigned i=0;i<cap;i++) CHECK(reist_x64_identity_apply(&p,3,i,s.tasks[i][1])==1);
    return 0;
}
static int negatives(void) {
    struct storage s;struct reist_x64_identity_pool p;
    init(&s,&p,4,UINT32_MAX-1);
    CHECK(reist_x64_identity_apply(&p,1,0,0)==(UINT64_C(0xffffffff)<<32));
    CHECK(denied(&p,&s,1,1,0));
    CHECK(reist_x64_identity_apply(&p,3,0,UINT32_MAX)==1);
    CHECK(p.last_generation==UINT32_MAX && denied(&p,&s,1,0,0));
    init(&s,&p,4,0);
    for(unsigned field=0;field<32;field++) {
        s.tasks[0][field]=1;CHECK(denied(&p,&s,1,1,0));s.tasks[0][field]=0;
    }
    s.retired[0]=1;CHECK(denied(&p,&s,1,1,0));s.retired[0]=0;
    CHECK(reist_x64_identity_apply(&p,1,0,0));
    s.tasks[0][0]=10;CHECK(denied(&p,&s,0,0,0));s.tasks[0][0]=9;
    s.tasks[0][1]=UINT64_C(1)<<32;CHECK(denied(&p,&s,0,0,0));s.tasks[0][1]=1;
    s.retired[0]=1;CHECK(denied(&p,&s,0,0,0));s.retired[0]=0;
    constructed(s.tasks[0]);
    for(unsigned field=2;field<=3;field++) {
        uint64_t old=s.tasks[0][field];s.tasks[0][field]=1;
        CHECK(denied(&p,&s,2,0,1));s.tasks[0][field]=old;
    }
    p.capacity=0;CHECK(denied(&p,&s,0,0,0));p.capacity=65;CHECK(denied(&p,&s,0,0,0));
    init(&s,&p,4,2);
    s.tasks[0][0]=9;s.tasks[0][1]=1;s.retired[1]=1;
    CHECK(denied(&p,&s,0,0,0));
    memset(s.tasks,0,sizeof s.tasks);s.retired[0]=1;
    CHECK(denied(&p,&s,0,0,0));
    init(&s,&p,4,2);
    s.retired[0]=1;s.tasks[1][0]=9;s.tasks[1][1]=1;
    CHECK(denied(&p,&s,0,0,0));
    CHECK(!reist_x64_identity_apply(NULL,0,0,0));
    return 0;
}
int main(void) {
    CHECK(!lifecycle(1));CHECK(!lifecycle(4));CHECK(!lifecycle(64));CHECK(!negatives());
    puts("X86_64_IDENTITY_HOST_OK capacities=1,4,64 reuse=128 exhaustion=1 rollback=1 nonmutation=1");
    return 0;
}
