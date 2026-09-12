#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../arch/x86_64/proc/syscall_profile.h"
#include "../include/reist/abi/syscall.h"
#define CHECK(x) do { if (!(x)) { printf("FAIL line=%d\n",__LINE__); return 1; } } while(0)
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const reist_task_control_request_t *);
extern uint8_t core_begin[],core_end[];
extern uint64_t family_records[4][8],family_profiles[4][4],scheduler_tasks[4][32],scheduler_last_tick;
extern uint64_t scheduler_deadline_entries[4][2];
extern uint32_t process_run_plan[],process_run_generations[4],family_total,family_cancel_mask,family_reasons[4];
extern uint32_t scheduler_current_slot,process_run_receipt[8],process_heap_retire_mask;
extern uint64_t __attribute__((sysv_abi)) family_validate_runtime64(void);
extern void __attribute__((sysv_abi)) family_terminal64(void),family_reaped64(void);
extern void __attribute__((sysv_abi)) family_expire_test(uint64_t,uint64_t);
static void setup(void) {
    memset(core_begin,0,(size_t)(core_end-core_begin));process_run_plan[0]=3;family_total=3;scheduler_last_tick=100;
    for(unsigned s=0;s<3;s++) {
        family_records[s][0]=((uint64_t)(s+1)<<32)|s;
        family_records[s][5]=s<2?1:2;
        scheduler_tasks[s][0]=1;scheduler_tasks[s][1]=s+1;process_run_generations[s]=s+1;
    }
    family_records[2][1]=family_records[0][0];
}
static int lifecycle(void) {
    uint8_t before[8192];size_t size=(size_t)(core_end-core_begin);CHECK(size<=sizeof(before));
    setup();CHECK(family_validate_runtime64()==1);
    /* Actual owner/generation validation is nonmutating on stale handles. */
    for(unsigned bit=0;bit<64;bit++) {
        setup();family_records[2][1]^=1ULL<<bit;
        /* NASM exports core_begin and family_records as overlapping symbols;
         * force actual reads rather than C's distinct-global alias folding. */
        for(size_t i=0;i<size;i++) before[i]=((volatile uint8_t*)core_begin)[i];
        uint64_t result=family_validate_runtime64();
        if(result) printf("stale bit=%u result=%llu owner=%llx\n",bit,(unsigned long long)result,(unsigned long long)family_records[2][1]);
        CHECK(result==0);
        for(size_t i=0;i<size;i++) if(before[i]!=core_begin[i]) { printf("changed bit=%u offset=%llu before=%u after=%u size=%llu\n",bit,(unsigned long long)i,before[i],core_begin[i],(unsigned long long)size);break; }
        CHECK(!memcmp(before,core_begin,size));
    }
    setup();family_records[0][6]=8;CHECK(family_validate_runtime64()==1);
    family_records[0][6]=9;CHECK(family_validate_runtime64()==0);
    setup();family_records[0][2]=family_records[2][0];family_records[0][3]=105;
    scheduler_tasks[0][0]=6;scheduler_deadline_entries[0][0]=105;scheduler_deadline_entries[0][1]=1;
    CHECK(family_validate_runtime64()==1);
    family_records[0][3]=106;CHECK(family_validate_runtime64()==0);family_records[0][3]=105;
    family_expire_test(0,105);
    CHECK(!family_records[0][2] && !family_records[0][3] && (int64_t)scheduler_tasks[0][29]==-110);
    CHECK(family_records[2][5]==2 && family_records[0][6]==0);
    /* Root loss marks only its children; terminal heap/fence precedes receipts. */
    setup();scheduler_current_slot=0;process_run_receipt[3]=3;scheduler_tasks[0][0]=3;
    family_terminal64();CHECK(family_records[0][5]==5 && family_records[1][5]==1);
    CHECK(family_cancel_mask==4 && family_reasons[2]==3);
    process_heap_retire_mask=1;CHECK(family_validate_runtime64()==1);
    scheduler_tasks[0][0]=0;family_reaped64();process_heap_retire_mask=0;
    CHECK(family_records[0][5]==6 && family_validate_runtime64()==1);
    scheduler_current_slot=2;scheduler_tasks[2][0]=3;process_run_receipt[2]=0;
    family_terminal64();CHECK(family_records[2][5]==3 && family_records[2][4]==3ULL<<32);
    process_heap_retire_mask=4;CHECK(family_validate_runtime64()==1);
    family_profiles[2][3]=16;CHECK(family_validate_runtime64()==0);family_profiles[2][3]=0;
    scheduler_tasks[2][0]=0;family_reaped64();process_heap_retire_mask=0;
    CHECK(family_records[2][5]==4 && family_validate_runtime64()==1);
    return 0;
}
int main(void) {
    CHECK(lifecycle()==0);
    reist_task_control_request_t q={1,64,1,0,0,3,0,1ULL<<9,32,0}, copy;
    CHECK(sizeof(q)==64);
    CHECK(family_request_admit64(&q)==1);
    for(unsigned n=0;n<512;n++) {
        copy=q; ((uint8_t*)&copy)[n/8]^=1U<<(n%8);
        int64_t r=family_request_admit64(&copy);
        CHECK(r==1 || r==-22 || r==-13);
    }
    copy=q;copy.version=2;CHECK(family_request_admit64(&copy)==-22);
    copy=q;copy.image=7;CHECK(family_request_admit64(&copy)==-22);
    copy=q;copy.cpu_samples=33;CHECK(family_request_admit64(&copy)==-22);
    copy=q;copy.syscalls|=1ULL<<23;CHECK(family_request_admit64(&copy)==-13);
    copy=q;copy.syscalls=0;CHECK(family_request_admit64(&copy)==-13);
    q=(reist_task_control_request_t){1,64,2,0,0x100000002ULL,0,1,0,0,0};
    CHECK(family_request_admit64(&q)==1);
    q.timeout_ms=1000;CHECK(family_request_admit64(&q)==1);
    q.timeout_ms=1001;CHECK(family_request_admit64(&q)==-22);
    q.timeout_ms=0;CHECK(family_request_admit64(&q)==-22);
    q.operation=3;CHECK(family_request_admit64(&q)==1);
    q.target=0;CHECK(family_request_admit64(&q)==-22);
    uint64_t task[32]={9,0x12345678};
    struct reist_x64_profile_v2 profile={0};
    struct reist_x64_profile_binding_v2 b={task,&profile,task[1],{1ULL<<9,1ULL<<1,1ULL<<4}};
    CHECK(reist_x64_profile_apply_v2(&b,1,0)==1);
    CHECK(profile.generation==task[1] && profile.masks[2]==16);
    task[0]=2;
    for(unsigned n=0;n<256;n++) {
        uint64_t expected=(n==9 || n==65 || n==132)?1:2;
        CHECK(reist_x64_profile_apply_v2(&b,2,n)==expected);
    }
    for(unsigned n=0;n<256;n++) {
        struct reist_x64_profile_v2 old=profile;
        ((uint8_t*)&profile)[n/8]^=1U<<(n%8);
        struct reist_x64_profile_v2 poisoned=profile;
        CHECK(reist_x64_profile_apply_v2(&b,0,0)==0);
        CHECK(!memcmp(&poisoned,&profile,sizeof(profile)));
        profile=old;
    }
    task[0]=3;CHECK(reist_x64_profile_apply_v2(&b,3,0)==1);
    struct reist_x64_profile_v2 zero={0};CHECK(!memcmp(&profile,&zero,sizeof(zero)));
    CHECK(reist_x64_profile_apply_v2(&b,3,0)==1);
    CHECK(reist_x64_profile_apply_v2(&b,2,132)==0);
    task[0]=9;b.masks[2]|=32;CHECK(reist_x64_profile_apply_v2(&b,1,0)==0);
    CHECK(!memcmp(&profile,&zero,sizeof(zero)));
    puts("TASK_FAMILY_HOST_OK");return 0;
}
