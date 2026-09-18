#include <stdint.h>
#include <stdio.h>
#include <string.h>
/* Never use assert: O2 may define NDEBUG and must still execute mechanisms. */
#define CHECK(x) do {if(!(x)){fprintf(stderr,"SERVICE_CPU_CHECK line=%u: %s\n",(unsigned)__LINE__,#x);return 1;}}while(0)
#if SERVICE_RUN_TEST
struct plan {uint32_t version,size,count,reserved;uint64_t tasks[8][4],periods[8];};
_Static_assert(sizeof(struct plan)==336,"private run-v5 size");
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const void *);
static struct plan good(void) {
    struct plan p={0};p.version=5;p.size=336;p.count=8;
    for(unsigned i=0;i<8;i++) {
        p.tasks[i][0]=i<2;p.tasks[i][1]=1ULL<<9;p.tasks[i][2]=32;
        p.tasks[i][3]=i<2?i+3:i+5;p.periods[i]=i<2?100:0;
    }
    return p;
}
int main(void) {
    struct plan p=good(),before;
    p.version=4;p.size=272;CHECK(process_run_admit64(&p)==1);
    p=good();before=p;
    CHECK(process_run_admit64(&p)==1); /* actual missing run-v5 admission */
    CHECK(!memcmp(&p,&before,sizeof p));
    for(unsigned slot=0;slot<8;slot++) {
        p=good();p.periods[slot]=100;CHECK(process_run_admit64(&p)==1);
        for(unsigned kind=0;kind<5;kind++) {
            p=good();p.periods[slot]=(uint64_t[]){1,99,101,UINT32_MAX,UINT64_MAX}[kind];before=p;
            CHECK(!process_run_admit64(&p));CHECK(!memcmp(&p,&before,sizeof p));
        }
        for(unsigned limit=1;limit<=32;limit++) {
            p=good();p.tasks[slot][2]=limit;CHECK(process_run_admit64(&p)==1);
        }
        for(unsigned kind=0;kind<4;kind++) {
            p=good();p.tasks[slot][2]=(uint64_t[]){0,33,UINT32_MAX,UINT64_MAX}[kind];before=p;
            CHECK(!process_run_admit64(&p));CHECK(!memcmp(&p,&before,sizeof p));
        }
        p=good();p.tasks[slot][1]|=1ULL<<63;before=p;
        CHECK(!process_run_admit64(&p));CHECK(!memcmp(&p,&before,sizeof p));
        p=good();p.tasks[slot][0]^=1;CHECK(!process_run_admit64(&p));
        p=good();p.tasks[slot][3]=13;CHECK(!process_run_admit64(&p));
    }
    for(unsigned field=0;field<4;field++) {
        p=good();((uint32_t*)&p)[field]^=1;before=p;
        CHECK(!process_run_admit64(&p));CHECK(!memcmp(&p,&before,sizeof p));
    }
    CHECK(!process_run_admit64(0));
    p=good();CHECK(!process_run_admit64((const unsigned char*)&p+1));
    puts("SERVICE_CPU_RUN_OK");return 0;
}
#endif

#if SERVICE_PERIOD_TEST
#include "../arch/x86_64/proc/cpu_period.h"
struct pair {struct reist_x64_cpu_budget budget;struct reist_x64_cpu_window window;};
static uint64_t apply(struct pair *p,uint64_t op,uint64_t gen,uint64_t arg,uint64_t now) {
    return reist_x64_period_apply(&p->budget,&p->window,op,gen,arg,now);
}
static struct pair initial(uint64_t origin) {
    struct pair p={{17,32,0,0},{100,origin,0,0}};return p;
}
int main(void) {
    struct pair p={0},before;
    CHECK(apply(&p,0,0,0,0)==1);
    for(unsigned quota=1;quota<=32;quota++) {
        memset(&p,0,sizeof p);
        CHECK(apply(&p,1,17,((uint64_t)100<<32)|quota,1000)==1);
        CHECK(p.budget.generation==17 && p.budget.limit==quota && p.window.origin==1000);
        before=p;CHECK(!apply(&p,1,17,((uint64_t)100<<32)|quota,1000));CHECK(!memcmp(&p,&before,sizeof p));
        for(unsigned n=1;n<=quota;n++) {
            CHECK(apply(&p,2,17,1000+n,1000+n)==(n==quota?2:1));
            CHECK(p.budget.used==n && p.window.used==n);
        }
        before=p;
        CHECK(!apply(&p,2,17,2000,2000));CHECK(!memcmp(&p,&before,sizeof p));
        CHECK(apply(&p,0,17,0,2000)==1);
        CHECK(!apply(&p,3,18,0,2000));CHECK(!memcmp(&p,&before,sizeof p));
        CHECK(apply(&p,3,17,0,2000)==1);
        CHECK(!memcmp(&p,&(struct pair){0},sizeof p));
        CHECK(!apply(&p,2,17,2001,2001));
        CHECK(apply(&p,1,18,((uint64_t)100<<32)|quota,2000)==1);
    }
    const uint64_t origins[]={0,1,(1ULL<<32)-50,(1ULL<<60)-10000};
    for(unsigned o=0;o<sizeof origins/sizeof origins[0];o++) {
        p=initial(origins[o]);
        for(unsigned n=1;n<=120;n++) {
            uint64_t tick=origins[o]+n*5;
            CHECK(apply(&p,2,17,tick,tick)==1);
            CHECK(p.budget.used==n && p.budget.last_tick==tick);
            CHECK(p.window.index==n/20 && p.window.used==(n<20?n:n%20+1));
            before=p;
            for(unsigned op=0;op<=3;op++) {
                CHECK(!apply(&p,op,16,0,tick));CHECK(!memcmp(&p,&before,sizeof p));
            }
            CHECK(!apply(&p,2,17,tick,tick));CHECK(!memcmp(&p,&before,sizeof p));
            CHECK(!apply(&p,2,17,tick-1,tick));CHECK(!memcmp(&p,&before,sizeof p));
            CHECK(!apply(&p,2,17,tick+1,tick));CHECK(!memcmp(&p,&before,sizeof p));
            CHECK(apply(&p,0,17,0,tick)==1);CHECK(!memcmp(&p,&before,sizeof p));
        }
        CHECK(apply(&p,3,17,0,origins[o]+601)==1);
    }
    p=initial(10);
    CHECK(apply(&p,2,17,109,109)==1 && p.window.index==0);
    CHECK(apply(&p,2,17,110,110)==1 && p.window.index==1 && p.window.used==1);
    CHECK(apply(&p,2,17,(1ULL<<32)+10,(1ULL<<32)+10)==1);
    CHECK(p.window.index==(1ULL<<32)/100 && p.budget.used==3 && p.window.used==1);
    /* Reach the greatest admitted timestamp without iteration over windows. */
    CHECK(apply(&p,2,17,(1ULL<<60)-1,(1ULL<<60)-1)==1);
    before=p;CHECK(!apply(&p,2,17,1ULL<<60,1ULL<<60));CHECK(!memcmp(&p,&before,sizeof p));
    for(unsigned field=0;field<8;field++) {
        const uint64_t bad[]={UINT64_MAX,1ULL<<60,1ULL<<32};
        for(unsigned n=0;n<3;n++) {
            p=initial(10);CHECK(apply(&p,2,17,20,20)==1);
            ((uint64_t*)&p)[field]=bad[n];before=p;
            for(unsigned op=0;op<=3;op++) {
                CHECK(!apply(&p,op,17,op==2?21:0,21));CHECK(!memcmp(&p,&before,sizeof p));
            }
        }
    }
    /* Plausible small corruptions must fail, not just all-ones overflow. */
    const unsigned fields[]={0,1,2,3,4,5,6,7,7,7};
    const uint64_t values[]={18,33,21,9,99,21,1,0,2,33};
    for(unsigned n=0;n<sizeof fields/sizeof fields[0];n++) {
        p=initial(10);CHECK(apply(&p,2,17,20,20)==1);
        ((uint64_t*)&p)[fields[n]]=values[n];before=p;
        CHECK(!apply(&p,2,17,21,21));CHECK(!memcmp(&p,&before,sizeof p));
    }
    p=initial(10);before=p;
    CHECK(!apply(&p,2,17,10,10));CHECK(!apply(&p,0,17,1,10));
    CHECK(!apply(&p,4,17,0,10));CHECK(!apply(&p,0,17,0,9));
    CHECK(!apply(&p,0,(1ULL<<32)|17,0,10));CHECK(!memcmp(&p,&before,sizeof p));
    CHECK(!reist_x64_period_apply(0,&p.window,0,17,0,10));
    CHECK(!reist_x64_period_apply(&p.budget,0,0,17,0,10));
    CHECK(!reist_x64_period_apply(&p.budget,(void*)&p.budget,0,17,0,10));
    CHECK(!reist_x64_period_apply(&p.budget,(void*)((unsigned char*)&p+8),0,17,0,10));
    CHECK(!reist_x64_period_apply((void*)((unsigned char*)&p+1),&p.window,0,17,0,10));
    CHECK(!reist_x64_period_apply((void*)(uintptr_t)(UINT64_MAX-7),&p.window,0,17,0,10));
    CHECK(!memcmp(&p,&before,sizeof p));
    /* Legacy quota stays lifetime-bound across more than three windows. */
    memset(&p,0,sizeof p);CHECK(apply(&p,1,9,32,1)==1);
    for(unsigned n=1;n<=32;n++)CHECK(apply(&p,2,9,n*100,n*100)==(n==32?2:1));
    before=p;CHECK(!apply(&p,2,9,9999,9999));CHECK(!memcmp(&p,&before,sizeof p));
    CHECK(!memcmp(&p.window,&(struct reist_x64_cpu_window){0},32));
    CHECK(apply(&p,3,9,0,10000)==1);
    /* Non-native bootstrap limits remain valid, not reinterpreted as periodic. */
    CHECK(apply(&p,1,8,65536,10000)==1);
    CHECK(apply(&p,2,8,10001,10001)==1 && p.budget.limit==65536);
    CHECK(apply(&p,3,8,0,10001)==1);
    puts("SERVICE_CPU_PERIOD_OK");return 0;
}
#endif

#if SERVICE_FAMILY_TEST
struct request {uint32_t version,bytes,op,flags;uint64_t handle,image,timeout,profile,cpu,startup,period,reserved;};
_Static_assert(sizeof(struct request)==80,"CREATE-v6 extent");
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const void *);
extern int64_t __attribute__((sysv_abi)) family_cpu_attenuate64(const void *,uint64_t,uint64_t);
static struct request request(void) {
    struct request r={6,80,1,0,0,0x410000,0,0x420000,32,0x430000,1000,0};return r;
}
int main(void) {
    struct request r=request(),saved=r;
    CHECK(family_request_admit64(&r)==1 && family_cpu_attenuate64(&r,100,32)==1);
    CHECK(!memcmp(&r,&saved,sizeof r));
    for(unsigned n=1;n<=32;n++) {
        r=request();r.cpu=n;CHECK(family_request_admit64(&r)==1);
        CHECK(family_cpu_attenuate64(&r,100,n)==1);
        CHECK(family_cpu_attenuate64(&r,100,n-1)==-13);
        CHECK(family_cpu_attenuate64(&r,0,n)==-13);
        CHECK(family_cpu_attenuate64(&r,101,n)==-13);
        CHECK(family_cpu_attenuate64(&r,100,33)==-13);
    }
    for(unsigned field=0;field<12;field++) {
        r=request();
        if(field<4)((uint32_t*)&r)[field]^=1;
        else ((uint64_t*)&r)[field-2]=field==5 || field==7 || field==9?0:UINT64_MAX;
        saved=r;CHECK(family_request_admit64(&r)==-22);CHECK(!memcmp(&r,&saved,sizeof r));
    }
    for(unsigned v=1;v<=5;v++) {
        r=request();r.version=v;r.bytes=64;r.period=UINT64_MAX;r.reserved=UINT64_MAX;
        if(v<3)r.image=5;
        if(v<4)r.profile=1ULL<<9;
        if(v==1)r.startup=0;
        CHECK(family_request_admit64(&r)==1);
        CHECK(family_cpu_attenuate64(&r,0,0)==1);
    }
    for(unsigned op=2;op<=3;op++)for(unsigned slot=0;slot<8;slot++) {
        r=(struct request){1,64,op,0,((uint64_t)17<<32)|slot,0,op==2?1000:0,0,0,0,0,0};
        CHECK(family_request_admit64(&r)==1);
        r.version=6;r.bytes=80;r.period=1000;CHECK(family_request_admit64(&r)==-22);
    }
    puts("SERVICE_CPU_FAMILY_OK");return 0;
}
#endif

#if SERVICE_SCHEDULER_TEST
#include "../arch/x86_64/proc/cpu_period.h"
extern struct reist_x64_cpu_budget scheduler_cpu_budgets[8];
extern struct reist_x64_cpu_window scheduler_cpu_windows[8];
extern uint64_t process_run_plan[42],scheduler_last_tick;
extern unsigned char scheduler_mode;
extern uint64_t __attribute__((sysv_abi)) service_scheduler_apply(uint64_t,uint64_t,uint64_t,uint64_t);
int main(void) {
    scheduler_mode=8;scheduler_last_tick=1000;
    for(unsigned slot=0;slot<8;slot++) {
        process_run_plan[34+slot]=slot&1?0:100;
        CHECK(service_scheduler_apply(1,slot,slot+1,32)==1);
        CHECK(scheduler_cpu_budgets[slot].generation==slot+1);
        CHECK(scheduler_cpu_windows[slot].period==process_run_plan[34+slot]);
        CHECK(scheduler_cpu_windows[slot].origin==(slot&1?0:1000));
    }
    scheduler_last_tick=1001;
    for(unsigned slot=0;slot<8;slot++) {
        CHECK(service_scheduler_apply(2,slot,slot+1,1001)==1);
        CHECK(scheduler_cpu_budgets[slot].used==1);
        CHECK(service_scheduler_apply(0,slot,slot+1,0)==1);
        CHECK(!service_scheduler_apply(0,slot,slot+2,0));
        CHECK(!service_scheduler_apply(2,slot,slot+1,1002));
        CHECK(scheduler_cpu_budgets[slot].used==1);
        uint64_t period=process_run_plan[34+slot];process_run_plan[34+slot]=period?0:100;
        CHECK(!service_scheduler_apply(0,slot,slot+1,0));
        process_run_plan[34+slot]=(1ULL<<32)|period;
        CHECK(!service_scheduler_apply(0,slot,slot+1,0));
        process_run_plan[34+slot]=period;
    }
    CHECK(!service_scheduler_apply(0,8,1,0));
    CHECK(!service_scheduler_apply(0,UINT32_MAX,1,0));
    scheduler_last_tick=1100;
    for(unsigned slot=0;slot<8;slot++) {
        CHECK(service_scheduler_apply(2,slot,slot+1,1100)==1);
        CHECK(scheduler_cpu_budgets[slot].used==2);
        CHECK(scheduler_cpu_windows[slot].used==(slot&1?0:1));
        CHECK(service_scheduler_apply(3,slot,slot+1,0)==1);
        CHECK(!memcmp(&scheduler_cpu_budgets[slot],&(struct reist_x64_cpu_budget){0},32));
        CHECK(!memcmp(&scheduler_cpu_windows[slot],&(struct reist_x64_cpu_window){0},32));
        CHECK(!service_scheduler_apply(1,slot,slot+9,(1ULL<<32)|32));
    }
    scheduler_mode=5;
    for(unsigned slot=0;slot<8;slot++) {
        CHECK(service_scheduler_apply(1,slot,slot+20,128)==(slot<4?1:0));
        CHECK(!memcmp(&scheduler_cpu_windows[slot],&(struct reist_x64_cpu_window){0},32));
        if(slot<4)CHECK(service_scheduler_apply(3,slot,slot+20,0)==1);
    }
    puts("SERVICE_CPU_SCHEDULER_OK");return 0;
}
#endif

#if SERVICE_SNAPSHOT_TEST
struct snapshot_request {uint32_t version,bytes,op,flags;uint64_t handle,image,timeout,profile,cpu,startup,period,reserved;};
extern unsigned char family_request[96];
extern uintptr_t syscall_rdi;
extern int64_t __attribute__((sysv_abi)) family_syscall64(void);
static uintptr_t allowed;
static uint64_t extent,calls,lengths[2];
uint64_t __attribute__((sysv_abi)) service_range(uintptr_t address,uint64_t bytes,uint64_t flags) {
    if(calls<2)lengths[calls]=bytes;
    calls++;
    return address==allowed && bytes<=extent && flags==4 && calls<=2;
}
int main(void) {
    struct snapshot_request r={6,80,1,0,0,0x410000,0,0x420000,32,0x430000,1000,0};
    allowed=syscall_rdi=(uintptr_t)&r;
    for(extent=0;extent<=80;extent++) {
        memset(family_request,0xa5,96);calls=0;
        int64_t result=family_syscall64();
        CHECK(result==(extent<80?-14:1));
        CHECK(calls==(extent<64?1:2));CHECK(lengths[0]==64);
        if(calls==2)CHECK(lengths[1]==80);
        if(extent==80)CHECK(!memcmp(family_request,&r,80));
        for(unsigned n=extent<80?0:80;n<96;n++)CHECK(family_request[n]==0xa5);
    }
    /* Old fixed64 snapshots never read the extension or inherit v6 authority. */
    r.version=5;r.bytes=64;r.period=UINT64_MAX;r.reserved=UINT64_MAX;extent=64;calls=0;
    memset(family_request,0xa5,96);
    CHECK(family_syscall64()==1 && calls==1 && lengths[0]==64);
    CHECK(!memcmp(family_request,&r,64));
    for(unsigned n=64;n<96;n++)CHECK(family_request[n]==0xa5);
    r.version=6;r.bytes=64;extent=80;calls=0;
    CHECK(family_syscall64()==-22 && calls==2);
    puts("SERVICE_CPU_SNAPSHOT_OK");return 0;
}
#endif
