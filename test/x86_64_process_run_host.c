#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../arch/x86_64/proc/process_run.h"
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const struct reist_x64_run_v1 *);
#define CHECK(c) do { if (!(c)) {printf("line %d\n", __LINE__);return 1;} } while (0)
#ifndef PROCESS_OWNERSHIP
int main(void) {
    struct reist_x64_run_v1 p, before;
    for (unsigned count=1; count<=4; ++count) {
        memset(&p,0,sizeof p); p.version=1; p.size=sizeof p; p.count=count;
        for (unsigned s=0; s<count; ++s) {
            p.tasks[s].argument=UINT64_MAX-s;
            p.tasks[s].syscalls=REIST_X64_RUN_SYSCALLS;
            p.tasks[s].cpu_samples=1+s*10;
        }
        before=p; CHECK(process_run_admit64(&p)==1); CHECK(!memcmp(&p,&before,sizeof p));
        for (unsigned byte=0; byte<sizeof p; ++byte) {
            p=before; ((unsigned char *)&p)[byte]^=0x80;
            struct reist_x64_run_v1 changed=p;
            uint64_t result=process_run_admit64(&p);
            /* All argument bits are deliberately opaque and never policy. */
            unsigned entry=byte>=16 ? (byte-16)/32 : 4;
            unsigned field=byte>=16 ? (byte-16)%32 : 32;
            CHECK(result==(entry<count && field<8 ? 1u:0u));
            CHECK(!memcmp(&p,&changed,sizeof p));
        }
        p=before;
        for (unsigned s=0;s<count;++s) {
            p.tasks[s].syscalls=0; CHECK(!process_run_admit64(&p));
            p.tasks[s].syscalls=REIST_X64_RUN_SYSCALLS;
            for (unsigned q=0;q<=33;++q) {
                p.tasks[s].cpu_samples=q;
                CHECK(process_run_admit64(&p)==(q>=1 && q<=32));
            }
            p.tasks[s].cpu_samples=32;
        }
    }
    memset(&p,0,sizeof p); CHECK(!process_run_admit64(&p));
    CHECK(!process_run_admit64(0));
    puts("PROCESS_RUN_HOST_OK descriptors_opaque_arguments_bounds_nonmutation=1");return 0;
}
#else
extern uint64_t __attribute__((sysv_abi)) run_ownership(void);
extern uint64_t run_wake(unsigned tick);
extern unsigned char process_run_host_begin[],process_run_host_end[];
extern uint64_t scheduler_tasks[4][32],scheduler_table_frames[4][4];
extern uint64_t scheduler_cpu_budgets[4][4],scheduler_syscall_profiles[4][2];
extern uint64_t scheduler_runqueue_entries[4],scheduler_deadline_entries[4][2];
extern unsigned char scheduler_runqueue_head,scheduler_runqueue_tail,scheduler_runqueue_count;
extern unsigned char scheduler_runqueue_membership[4],scheduler_deadline_count,scheduler_deadline_membership[4];
extern unsigned char scheduler_mode,scheduler_active;
extern uint32_t scheduler_identity_retired[4],scheduler_reap_count,scheduler_last_tick,scheduler_current_slot;
extern uint64_t scheduler_original_cr3;
extern struct {void *tasks,*retired;uint32_t capacity,last;} scheduler_identity_pool;
extern struct reist_x64_run_v1 process_run_plan;
extern uint32_t process_run_generation,process_run_generations[4],process_run_live;
static unsigned char snapshot[65536];
static size_t arena_size(void) {return (uintptr_t)process_run_host_end-(uintptr_t)process_run_host_begin;}
static void setup(unsigned count, unsigned previous, unsigned variant) {
    memset(process_run_host_begin,0,arena_size());
    scheduler_mode=8;scheduler_active=1;scheduler_original_cr3=0x115000;
    process_run_plan.version=1;process_run_plan.size=144;process_run_plan.count=count;
    process_run_generation=count+previous;process_run_live=count;
    scheduler_identity_pool.tasks=scheduler_tasks;scheduler_identity_pool.retired=scheduler_identity_retired;
    scheduler_identity_pool.capacity=4;scheduler_identity_pool.last=process_run_generation;
    scheduler_current_slot=variant==0?0:UINT32_MAX;
    for(unsigned s=0;s<count;++s) {
        uint64_t *task=scheduler_tasks[s];unsigned gen=previous+s+1;
        task[0]=variant==1?6:variant==2?1:s==0?2:1;
        task[1]=gen;task[12]=0x400010;task[13]=0x409000;task[14]=0x202;
        process_run_generations[s]=gen;
        process_run_plan.tasks[s].argument=0x123400+s;
        process_run_plan.tasks[s].syscalls=REIST_X64_RUN_SYSCALLS;
        process_run_plan.tasks[s].cpu_samples=4+s*4;
        scheduler_cpu_budgets[s][0]=gen;scheduler_cpu_budgets[s][1]=4+s*4;
        scheduler_syscall_profiles[s][0]=gen;scheduler_syscall_profiles[s][1]=REIST_X64_RUN_SYSCALLS;
        for(unsigned i=0;i<4;++i)scheduler_table_frames[s][i]=0x4000000+(s*16+i)*4096;
        task[2]=scheduler_table_frames[s][0];task[3]=0x4000000+(s*16+4)*4096;
        task[5]=0x4000000+(s*16+5)*4096;
        if(task[0]==1) {
            scheduler_runqueue_entries[scheduler_runqueue_count++]=((uint64_t)gen<<32)|s;
            scheduler_runqueue_membership[s]=1;
        } else if(task[0]==6) {
            scheduler_deadline_entries[s][0]=s+1;
            scheduler_deadline_entries[s][1]=gen|((uint64_t)s<<32);
            scheduler_deadline_count++;scheduler_deadline_membership[s]=1;
        }
    }
    scheduler_runqueue_tail=scheduler_runqueue_count%4;
}
static int unchanged(unsigned expected) {
    volatile unsigned char *p=process_run_host_begin;
    size_t n=arena_size();if(n>sizeof snapshot)return 0;
    for(size_t i=0;i<n;++i)snapshot[i]=p[i];
    uint64_t result=run_ownership();
    for(size_t i=0;i<n;++i)if(snapshot[i]!=p[i])return 0;
    return result==expected;
}
int main(void) {
    CHECK(arena_size()<=sizeof snapshot);
    for(unsigned n=1;n<=4;++n)for(unsigned v=0;v<3;++v)for(unsigned prev=0;prev<=1;++prev) {
        setup(n,prev?UINT32_MAX-4:0,v);CHECK(unchanged(1));
        for(unsigned slot=0;slot<n;++slot) {
            uint64_t *fields[]={&scheduler_tasks[slot][1],&scheduler_tasks[slot][2],
                &scheduler_syscall_profiles[slot][0],&scheduler_syscall_profiles[slot][1],
                &scheduler_cpu_budgets[slot][0],&scheduler_cpu_budgets[slot][1],
                &scheduler_cpu_budgets[slot][2],&scheduler_cpu_budgets[slot][3],
                &scheduler_table_frames[slot][1],&scheduler_tasks[slot][3]};
            for(unsigned i=0;i<sizeof fields/sizeof *fields;++i) {
                uint64_t old=*fields[i];*fields[i]^=0x8000000000000000ULL;
                CHECK(unchanged(0));*fields[i]=old;
            }
            unsigned old=process_run_generations[slot];process_run_generations[slot]^=1;
            CHECK(unchanged(0));process_run_generations[slot]=old;
            unsigned char saved=scheduler_runqueue_membership[slot];scheduler_runqueue_membership[slot]^=1;
            CHECK(unchanged(0));scheduler_runqueue_membership[slot]=saved;
            saved=scheduler_deadline_membership[slot];scheduler_deadline_membership[slot]^=1;
            CHECK(unchanged(0));scheduler_deadline_membership[slot]=saved;
        }
        if(n>1) {scheduler_tasks[1][5]=scheduler_tasks[0][5];CHECK(unchanged(0));}
    }
    setup(4,0,2);scheduler_runqueue_entries[2]^=1ULL<<32;CHECK(unchanged(0));
    setup(4,0,1);scheduler_deadline_entries[1][1]^=1ULL<<32;CHECK(unchanged(0));
    setup(4,0,1);scheduler_last_tick=1;CHECK(unchanged(0));
    setup(1,0,0);scheduler_tasks[1][0]=1;CHECK(unchanged(0));
    setup(1,0,0);scheduler_identity_pool.capacity=3;CHECK(unchanged(0));
    setup(1,0,0);process_run_live=2;CHECK(unchanged(0));
    setup(1,0,0);scheduler_current_slot=1;CHECK(unchanged(0));
    setup(1,0,0);scheduler_tasks[0][5]=scheduler_tasks[0][3];CHECK(unchanged(0));
    setup(1,0,0);scheduler_tasks[0][5]=scheduler_original_cr3;CHECK(unchanged(0));
    /* Exact retired slot and fresh second run; stale profiles must not revive. */
    setup(4,10,2);
    memset(scheduler_tasks,0,sizeof scheduler_tasks);memset(scheduler_table_frames,0,sizeof scheduler_table_frames);
    memset(scheduler_cpu_budgets,0,sizeof scheduler_cpu_budgets);memset(scheduler_syscall_profiles,0,sizeof scheduler_syscall_profiles);
    memset(scheduler_runqueue_entries,0,sizeof scheduler_runqueue_entries);memset(scheduler_runqueue_membership,0,4);
    scheduler_runqueue_head=scheduler_runqueue_tail=scheduler_runqueue_count=0;
    scheduler_reap_count=4;process_run_live=0;
    for(unsigned s=0;s<4;++s)scheduler_identity_retired[s]=11+s;
    CHECK(unchanged(1));scheduler_identity_retired[1]=11;CHECK(unchanged(0));
    setup(4,0,1);
    CHECK(!run_wake(0));CHECK(unchanged(1));
    CHECK(!run_wake(2));CHECK(unchanged(1));
    for(unsigned tick=1;tick<=4;++tick) {
        CHECK(run_wake(tick)==1);CHECK(unchanged(1));
        CHECK(scheduler_deadline_count==4-tick && scheduler_runqueue_count==tick);
        for(unsigned slot=0;slot<4;++slot)CHECK(scheduler_tasks[slot][0]==(slot<tick?1u:6u));
        CHECK(!run_wake(tick));CHECK(unchanged(1));
    }
    puts("PROCESS_RUN_HOST_OK descriptors_ownership_frames_queues_retirement_nonmutation=1");return 0;
}
#endif
