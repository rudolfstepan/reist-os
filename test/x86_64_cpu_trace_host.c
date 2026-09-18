/* Actual scheduler wrapper + unchanged CPU assembly + trace producer. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t U;
#define CHECK(x) do{if(!(x)){fprintf(stderr,"CPU_TRACE line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
extern U scheduler_cpu_budgets[8][4],scheduler_cpu_windows[8][4],process_run_plan[42];
extern U scheduler_last_tick,scheduler_tasks[8][128],native_cpu_trace[];
extern uint32_t scheduler_current_slot;
extern unsigned char scheduler_mode;
extern U __attribute__((sysv_abi)) service_scheduler_apply(U,U,U,U);
extern U __attribute__((sysv_abi)) reist_x64_period_apply(U*,U*,U,U,U,U);
extern U __attribute__((sysv_abi)) trace_flags_probe(void);
static void setup(void){
    memset(scheduler_cpu_budgets,0,256);memset(scheduler_cpu_windows,0,256);
    memset(process_run_plan,0,336);memset(native_cpu_trace,0,32+257*192);
    scheduler_mode=8;scheduler_last_tick=0;
    for(unsigned slot=0;slot<8;slot++){
        process_run_plan[34+slot]=100;scheduler_tasks[slot][1]=100+slot;
        CHECK(service_scheduler_apply(1,slot,100+slot,32)==1);
    }
    CHECK(!native_cpu_trace[0] && !native_cpu_trace[1]);
}
static U apply(unsigned slot,U tick){
    U b[4],w[4];memcpy(b,scheduler_cpu_budgets[slot],32);memcpy(w,scheduler_cpu_windows[slot],32);
    U expected=reist_x64_period_apply(b,w,2,100+slot,tick,tick);
    scheduler_last_tick=tick;scheduler_current_slot=slot;
    U result=service_scheduler_apply(2,slot,100+slot,tick);
    CHECK(result==expected && !memcmp(b,scheduler_cpu_budgets[slot],32) && !memcmp(w,scheduler_cpu_windows[slot],32));
    return result;
}
int main(void){
    setup();CHECK(trace_flags_probe()==1);setup();
    for(unsigned n=1;n<=2048;n++){
        unsigned slot=(n-1)%8;U before[8];
        memcpy(before,scheduler_cpu_budgets[slot],32);memcpy(before+4,scheduler_cpu_windows[slot],32);
        CHECK(apply(slot,(U)n*100+1)==1 && native_cpu_trace[0]==n && !native_cpu_trace[1] && !native_cpu_trace[2]);
        U *r=native_cpu_trace+4+((n-1)&255)*24;uint32_t *d=(void*)r;
        CHECK(d[0]==1 && d[1]==1 && d[2]==n && d[3]==slot);
        CHECK(r[2]==100+slot && r[3]==(U)n*100+1 && r[4]==1);
        CHECK(!memcmp(r+5,before,64) && !memcmp(r+13,scheduler_cpu_budgets[slot],32) &&
              !memcmp(r+17,scheduler_cpu_windows[slot],32));
        /* Ring3 host truthfully captures IF=1; guest decoder must reject it.
         * Never fake CLI in user mode or silently substitute IF=0. */
        CHECK((r[21]&512) && (r[22]&512) && r[23]==8);
    }
    U ring[256*24];memcpy(ring,native_cpu_trace+4,sizeof ring);
    CHECK(apply(0,204901)==1 && native_cpu_trace[0]==2048 && native_cpu_trace[1]==1);
    CHECK(!memcmp(ring,native_cpu_trace+4,sizeof ring)); /* no overwrite after lifetime cap */
    for(unsigned fault=0;fault<4;fault++){
        setup();native_cpu_trace[fault]=fault==0?UINT64_MAX:1;
        CHECK(apply(0,1)==1 && native_cpu_trace[1]==1);
        CHECK(native_cpu_trace[0]==(fault==0?UINT64_MAX:0));
    }
    setup();for(unsigned n=1;n<=32;n++)CHECK(apply(7,n)==(n==32?2:1));
    CHECK(native_cpu_trace[0]==32 && native_cpu_trace[4+31*24+4]==2);
    CHECK(apply(7,33)==0 && native_cpu_trace[0]==33 && native_cpu_trace[4+32*24+4]==0);
    setup();scheduler_cpu_windows[3][0]=101;
    CHECK(apply(3,1)==0 && !native_cpu_trace[0]); /* wrapper rejects before the core */
    setup();scheduler_cpu_budgets[2][0]=88;
    CHECK(apply(2,1)==0 && native_cpu_trace[0]==1 && !native_cpu_trace[8]);
    setup();CHECK(service_scheduler_apply(2,8,108,1)==0 && !native_cpu_trace[0]);
    puts("CPU_TRACE_OK");return 0;
}
