#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define SYSV __attribute__((sysv_abi))
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d\n",__LINE__);return 1;}}while(0)
extern uint64_t SYSV process_ipc_completion_apply64(uint64_t*,uint64_t,uint64_t,uint64_t);
extern uint64_t SYSV host_adapter(uint64_t,uint64_t,uint64_t,uint64_t);
extern uint64_t process_ipc_completions[12],scheduler_tasks[128],host_counters[4],host_result;
extern uint32_t process_run_generations[4];
extern uint64_t scheduler_deadline_entries[8],syscall_rax,syscall_rdi,syscall_rsi,syscall_rdx;
extern uint64_t host_flags;
static const uint64_t cookie=UINT64_C(0x936da17cb852e40f);
static uint64_t calls,ready;static int64_t result;
static unsigned char output[140];
static void encode(uint64_t *p,uint64_t value){p[0]=value;p[1]=~value;p[2]=((value<<17)|(value>>47))^cookie;}
static void init(uint64_t *p){for(unsigned s=0;s<4;s++)encode(p+3*s,0);}
uint64_t SYSV fake_ipc(uint64_t op,uint64_t slot,uint64_t gen,uint64_t tick,uint64_t *r){
    (void)slot;(void)gen;(void)tick;calls++;r[5]=(uint64_t)result;r[7]=ready;r[6]=100;
    if(op==3 && !result){r[0]=54;r[2]=(uintptr_t)output;*(uint64_t*)((unsigned char*)r+2128)=140;
        memset((unsigned char*)r+64,0x5a,140);}
    return 1;
}
int main(void){
    uint64_t p[12],before[12];init(p);
    CHECK(process_ipc_completion_apply64(p,6,0,0)==1);
    for(unsigned s=0;s<4;s++){
        CHECK(process_ipc_completion_apply64(p,1,s,s+1)==1);
        CHECK(process_ipc_completion_apply64(p,0,s,s+1)==1);
        CHECK(process_ipc_completion_apply64(p,3,s,s+1)==0);
        CHECK(process_ipc_completion_apply64(p,2,s,s+1)==1);
        CHECK(process_ipc_completion_apply64(p,0,s,s+1)==0);
        CHECK(process_ipc_completion_apply64(p,3,s,s+1)==1);
        CHECK(process_ipc_completion_apply64(p,3,s,s+1)==0);
        CHECK(process_ipc_completion_apply64(p,0,s,s+1)==2);
        CHECK(process_ipc_completion_apply64(p,4,s,s+1)==1);
        CHECK(process_ipc_completion_apply64(p,4,s,s+1)==0);
    }
    CHECK(!process_ipc_completion_apply64(p,6,0,0));
    for(unsigned word=0;word<12;word++)for(unsigned bit=0;bit<64;bit++){
        memcpy(before,p,sizeof(p));p[word]^=UINT64_C(1)<<bit;
        uint64_t damaged[12];memcpy(damaged,p,sizeof(p));
        CHECK(!process_ipc_completion_apply64(p,7,0,0));CHECK(!memcmp(p,damaged,sizeof(p)));
        memcpy(p,before,sizeof(p));
    }
    for(unsigned s=0;s<4;s++)for(unsigned a=0;a<3;a++)for(unsigned b=a+1;b<3;b++){
        memcpy(before,p,sizeof(p));p[3*s+a]^=1;p[3*s+b]^=1;
        CHECK(!process_ipc_completion_apply64(p,7,0,0));memcpy(p,before,sizeof(p));
    }
    for(unsigned s=0;s<4;s++){
        memcpy(before,p,sizeof(p));CHECK(!process_ipc_completion_apply64(p,5,s,s+2));CHECK(!memcmp(p,before,sizeof(p)));
        for(unsigned state=1;state<=3;state++){
            encode(p+3*s,((uint64_t)(s+1)<<32)|state);
            CHECK(process_ipc_completion_apply64(p,5,s,s+1)==1);
            CHECK(!process_ipc_completion_apply64(p,1,s,s+1));
        }
        CHECK(process_ipc_completion_apply64(p,1,s,s+10)==1);
        CHECK(process_ipc_completion_apply64(p,5,s,s+10)==1);
    }
    CHECK(process_ipc_completion_apply64(p,6,0,0)==1);
    CHECK(!process_ipc_completion_apply64(p,8,0,0));CHECK(!process_ipc_completion_apply64(p,1,4,1));
    CHECK(!process_ipc_completion_apply64(p,1,0,0));CHECK(!process_ipc_completion_apply64(p,1,0,UINT64_C(0x80000000)));
    CHECK(!process_ipc_completion_apply64(0,1,0,1));
    /* Actual adapter, not a reimplementation: bind, blocked receive, wake,
       copyout, repeated no-work dispatch, cancel, stale/fault paths. */
    init(process_ipc_completions);
    for(unsigned s=0;s<4;s++){
        uint64_t gen=s+1;scheduler_tasks[s*32+1]=gen;process_run_generations[s]=(uint32_t)gen;
        result=0;ready=0;CHECK(host_adapter(1,0,s,gen));
        uint64_t old=calls;for(unsigned i=0;i<1000;i++)CHECK(host_adapter(0,0,s,gen));CHECK(calls==old);
        memset(output,0xcc,sizeof(output));((uint32_t*)output)[0]=1;((uint32_t*)output)[1]=140;
        syscall_rax=54;syscall_rdi=1;syscall_rsi=(uintptr_t)output;syscall_rdx=100;
        result=-4095;CHECK(host_adapter(2,0,s,gen));CHECK((uint32_t)process_ipc_completions[s*3]==2);
        scheduler_deadline_entries[0]=100;scheduler_deadline_entries[1]=gen|((uint64_t)s<<32);
        result=0;ready=UINT64_C(1)<<s;CHECK(host_adapter(1,2,0,1));CHECK((uint32_t)process_ipc_completions[s*3]==3);
        ready=0;old=calls;CHECK(host_adapter(0,0,s,gen));CHECK(calls==old+1);
        for(unsigned i=0;i<140;i++)CHECK(output[i]==0x5a);
        CHECK(scheduler_tasks[s*32+29]==0);
        old=calls;CHECK(host_adapter(0,0,s,gen));CHECK(calls==old);
        for(unsigned error=0;error<2;error++){
            encode(process_ipc_completions+3*s,(gen<<32)|3);
            memset(output,0xcc,sizeof(output));result=error?-32:-110;old=calls;
            CHECK(host_adapter(0,0,s,gen));CHECK(calls==old+1);
            CHECK(scheduler_tasks[s*32+29]==(uint64_t)result);
            for(unsigned i=0;i<140;i++)CHECK(output[i]==0xcc);
        }
        /* A duplicate ready receipt cannot enqueue twice. */
        scheduler_tasks[s*32]=6;encode(process_ipc_completions+3*s,(gen<<32)|3);
        uint64_t enqueues=host_counters[1];result=0;ready=UINT64_C(1)<<s;
        CHECK(!host_adapter(1,2,0,1));CHECK(host_counters[1]==enqueues);ready=0;
        /* A ticket with no corresponding C result must not publish output. */
        encode(process_ipc_completions+3*s,(gen<<32)|3);memset(output,0xcc,sizeof(output));
        result=-4095;CHECK(!host_adapter(0,0,s,gen));for(unsigned i=0;i<140;i++)CHECK(output[i]==0xcc);
        result=0;CHECK(host_adapter(1,4,s,gen));
        old=calls;CHECK(!host_adapter(0,0,s,gen));CHECK(calls==old);
        CHECK(!host_adapter(1,0,s,gen));CHECK(calls==old);
    }
    result=0;CHECK(host_adapter(1,5,0,1));
    /* Corruption in any slot is rejected even by an unrelated idle dispatch. */
    init(process_ipc_completions);CHECK(host_adapter(1,0,0,1));
    uint64_t old_calls=calls;host_flags=512;
    CHECK(!host_adapter(0,0,0,1));CHECK(calls==old_calls);host_flags=0;
    for(unsigned word=0;word<12;word++){
        uint64_t old=calls;process_ipc_completions[word]^=1;
        CHECK(!host_adapter(0,0,0,1));CHECK(calls==old);process_ipc_completions[word]^=1;
    }
    /* Coherently encoded but invalid fields still fail semantic admission. */
    uint64_t invalid[]={UINT64_C(0x8000000000000001),4,1,UINT64_C(0x100000004)};
    for(unsigned i=0;i<4;i++){
        init(p);encode(p,invalid[i]);memcpy(before,p,sizeof(p));
        CHECK(!process_ipc_completion_apply64(p,7,0,0));CHECK(!memcmp(p,before,sizeof(p)));
    }
    puts("IPC_COMPLETION_HOST_OK");return 0;
}
