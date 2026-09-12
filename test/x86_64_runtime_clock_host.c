#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"line%d: %s\n",__LINE__,#x);exit(1); } } while(0)
#define HORIZON (UINT64_C(1)<<60)
#ifdef RUNTIME_LAYOUT_TEST
extern uint64_t __attribute__((sysv_abi)) scheduler_probe_data_index64(void);
extern unsigned char runtime_page_flags[8];
extern uint64_t runtime_tasks[64];
extern uint64_t __attribute__((sysv_abi)) runtime_isolation(void);
int main(void) {
    unsigned char before[8];unsigned accepted=0;
    for(unsigned first=0;first<8;first++) for(unsigned last=first;last<8;last++)
        for(unsigned rx=0;rx<8;rx++) {
            if(rx>=first && rx<=last) continue;
            memset(runtime_page_flags,0,8);runtime_page_flags[rx]=5;
            for(unsigned i=first;i<=last;i++) runtime_page_flags[i]=6;
            memcpy(before,runtime_page_flags,8);
            CHECK(scheduler_probe_data_index64()==first);
            CHECK(!memcmp(before,runtime_page_flags,8));accepted++;
            for(unsigned i=0;i<8;i++) for(unsigned bad=1;bad<256;bad++) {
                if(bad==4 || bad==5 || bad==6) continue;
                memcpy(runtime_page_flags,before,8);runtime_page_flags[i]=(unsigned char)bad;
                CHECK(scheduler_probe_data_index64()==UINT64_MAX);
            }
        }
    memset(runtime_page_flags,0,8);CHECK(scheduler_probe_data_index64()==UINT64_MAX);
    runtime_page_flags[0]=5;CHECK(scheduler_probe_data_index64()==UINT64_MAX);
    runtime_page_flags[1]=6;runtime_page_flags[3]=6;CHECK(scheduler_probe_data_index64()==UINT64_MAX);
    runtime_page_flags[3]=0;runtime_page_flags[0]=4;CHECK(scheduler_probe_data_index64()==UINT64_MAX);
    CHECK(accepted==168);
    for(unsigned page=1;page<8;page++) {
        memset(runtime_page_flags,0,8);memset(runtime_tasks,0,sizeof runtime_tasks);
        runtime_page_flags[0]=5;runtime_page_flags[page]=6;
        runtime_tasks[2]=0x1000;runtime_tasks[3]=0x2000;runtime_tasks[4+page]=0x3000;
        runtime_tasks[34]=0x4000;runtime_tasks[35]=0x5000;runtime_tasks[36+page]=0x6000;
        CHECK(runtime_isolation()==1);
        runtime_tasks[36+page]=0x3000;CHECK(runtime_isolation()==0);
    }
    puts("RUNTIME_CLOCK_HOST_OK admitted_page_layout=1");return 0;
}
#elif defined(RUNTIME_IPC_TEST)
#include "arch/x86_64/ipc/native_ipc.c"
static int fault_expected;
void reist_native_ipc_fault(void) {
    if(fault_expected) { puts("RUNTIME_CLOCK_HOST_OK fault_closed=1");exit(0); }
    fputs("unexpected IPC fatal\n",stderr);exit(2);
}
static native_ipc_request_t r;
static void call(unsigned op,unsigned slot,uint64_t tick) {
    CHECK(reist_native_ipc(op,slot,slot+1,tick,&r)==1);
}
int main(int argc,char **argv) {
    uint64_t start=(UINT64_C(1)<<32)-2;
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_BIND,s,start);
    if(argc>1) {
        CHECK(!strcmp(argv[1],"backward") || !strcmp(argv[1],"horizon"));
        fault_expected=1;
        call(NATIVE_IPC_PUMP,0,!strcmp(argv[1],"backward")?start-1:HORIZON);
        return 3;
    }
    r.number=49;call(NATIVE_IPC_REQUEST,0,start);CHECK(r.result==0);
    unsigned h=r.handle;
    memset(&r,0,sizeof r);r.number=55;r.a0=h;r.a1=2;r.a2=3;
    call(NATIVE_IPC_REQUEST,0,start);CHECK(r.result==0);
    memset(&r,0,sizeof r);r.number=54;r.a0=h;r.a2=30;
    r.message.version=1;r.message.struct_size=140;
    call(NATIVE_IPC_REQUEST,0,start);CHECK(r.result==NATIVE_IPC_PENDING && r.deadline==start+3);
    call(NATIVE_IPC_PUMP,1,start+2);CHECK(!r.ready);
    call(NATIVE_IPC_PUMP,1,start+3);CHECK(r.ready==1);
    call(NATIVE_IPC_TAKE,0,start+3);CHECK(r.result==-110);
    CHECK(pit_monotonic_ms()==(start+3)*10);
    /* Reject out-of-horizon deadlines before consuming even a ready queue. */
    memset(&r,0,sizeof r);r.number=53;r.a0=h;
    r.message.version=1;r.message.struct_size=140;r.message.length=1;r.message.payload[0]=77;
    call(NATIVE_IPC_REQUEST,0,HORIZON-2);CHECK(r.result==0);
    memset(&r,0,sizeof r);r.number=54;r.a0=h;r.a2=20;
    r.message.version=1;r.message.struct_size=140;
    call(NATIVE_IPC_REQUEST,1,HORIZON-2);CHECK(r.result==-22 && !pending[1].state);
    r.a2=0;call(NATIVE_IPC_REQUEST,1,HORIZON-2);
    if(r.result || r.message.payload[0]!=77)
        fprintf(stderr,"receive result=%lld payload=%u\n",(long long)r.result,r.message.payload[0]);
    CHECK(r.result==0 && r.message.payload[0]==77);
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_REAP,s,HORIZON-1);
    call(NATIVE_IPC_END,0,HORIZON-1);
    CHECK(pit_monotonic_ms()==(HORIZON-1)*10);
    puts("RUNTIME_CLOCK_HOST_OK ipc_wrap_horizon_cleanup=1");return 0;
}
#else
extern uint64_t __attribute__((sysv_abi)) timer_runtime_progress64(uint64_t,uint64_t,uint64_t,uint64_t);
extern uint64_t __attribute__((sysv_abi)) runtime_admit(uint64_t);
extern uint64_t scheduler_last_tick;
extern uint64_t __attribute__((sysv_abi)) reist_x64_budget_apply(uint64_t*,uint64_t,uint64_t,uint64_t);
int main(void) {
    const uint64_t gap=3000000000ULL,now=7000000000ULL;
    const uint64_t ticks[]={0,255,256,UINT32_MAX,UINT64_C(1)<<32,HORIZON-2};
    for(unsigned i=0;i<sizeof ticks/sizeof ticks[0];i++) {
        uint64_t t=ticks[i];
        CHECK(timer_runtime_progress64(now,now+1,t,t)==now+gap);
        CHECK(!timer_runtime_progress64(now,now+1,t,t+1));
        CHECK(!timer_runtime_progress64(now,now-1,t,t));
        CHECK(!timer_runtime_progress64(now,now+gap+1,t,t));
        scheduler_last_tick=t;CHECK(runtime_admit(t+1)==1);
        CHECK(!runtime_admit(t));CHECK(!runtime_admit(t+2));CHECK(scheduler_last_tick==t);
    }
    CHECK(!timer_runtime_progress64(now,now+1,HORIZON-1,HORIZON-1));
    CHECK(!timer_runtime_progress64(now,gap-1,0,0));
    CHECK(!timer_runtime_progress64(UINT64_MAX,UINT64_MAX,1,1));
    scheduler_last_tick=HORIZON-1;CHECK(!runtime_admit(HORIZON));
    scheduler_last_tick=UINT64_MAX;CHECK(!runtime_admit(0));
    uint64_t budget[4]={0},before[4];
    CHECK(reist_x64_budget_apply(budget,1,7,32)==1);
    for(unsigned used=1;used<=32;used++) {
        uint64_t tick=(UINT64_C(1)<<32)-16+used;
        CHECK(reist_x64_budget_apply(budget,2,7,tick)==(used==32?2u:1u));
        CHECK(budget[2]==used && budget[3]==tick);
        memcpy(before,budget,sizeof budget);
        CHECK(!reist_x64_budget_apply(budget,2,7,tick));
        CHECK(!memcmp(before,budget,sizeof budget));
        CHECK(reist_x64_budget_apply(budget,0,7,0)==1);
        CHECK(!memcmp(before,budget,sizeof budget));
    }
    CHECK(!reist_x64_budget_apply(budget,2,7,HORIZON-1));
    CHECK(reist_x64_budget_apply(budget,3,7,0)==1);
    for(unsigned i=0;i<4;i++) CHECK(!budget[i]);
    puts("RUNTIME_CLOCK_HOST_OK timer_tick_width=1");return 0;
}
#endif
