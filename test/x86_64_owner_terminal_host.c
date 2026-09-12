#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int owner_admit(void);
#define B(n) extern uint8_t scheduler_##n[]
#define D(n) extern uint32_t scheduler_##n[]
#define Q(n) extern uint64_t scheduler_##n[]
B(state_begin); B(kernel_stack_top); B(mode); B(active); B(shell_started);
B(dynamic_child_active); B(event_count); B(events); B(runqueue_head); B(runqueue_tail);
B(runqueue_count); B(runqueue_membership); B(deadline_count); B(deadline_membership);
B(fp_states); B(owner_receipt); B(shell_ipc_begin); B(shell_ipc_end);
D(current_slot); D(dynamic_spawn_count); D(dynamic_completed_count); D(dynamic_child_generation);
D(dynamic_parent_generation); D(dynamic_wait_generation); D(dynamic_wait_child_generation);
D(identity_retired); D(reap_count); D(last_tick); D(final_tick); D(shell_exit_status);
Q(identity_pool); Q(tasks); Q(cpu_budgets); Q(syscall_profiles); Q(table_frames);
Q(original_cr3); Q(dynamic_wait_status_direct); Q(runqueue_entries); Q(deadline_entries);
Q(child_terminal_generation); Q(child_terminal_status); Q(child_terminal_reason);
Q(child_terminal_parent_state); Q(child_terminal_endpoint); Q(child_terminal_rip);
Q(shell_ipc_endpoint_active); Q(shell_ipc_endpoint_generation); Q(shell_ipc_endpoint_owner_generation);
Q(shell_ipc_endpoint_handle); Q(shell_ipc_capabilities); Q(shell_ipc_message_ready);
Q(shell_ipc_message_sender_generation); Q(shell_ipc_send_generation); Q(shell_ipc_send_phase);
Q(shell_ipc_send_wait_handle); Q(shell_ipc_send_wait_generation);
B(shell_ipc_message); B(shell_ipc_send_wait_message);
#define CHECK(c) do {if(!(c)){printf("line %d\n", __LINE__); return 1;}} while(0)
#define MASK_PARENT ((1ULL<<9)|(1ULL<<15)|(1ULL<<20)|(1ULL<<22)|(1ULL<<23)|(1ULL<<24)|(1ULL<<30)|(1ULL<<40)|(1ULL<<49)|(1ULL<<50)|(1ULL<<51)|(1ULL<<52)|(1ULL<<53)|(1ULL<<54)|(1ULL<<55))
#define MASK_CHILD ((1ULL<<9)|(1ULL<<40)|(1ULL<<50)|(1ULL<<51)|(1ULL<<53)|(1ULL<<58))
static size_t arena_size(void) {return (uintptr_t)scheduler_kernel_stack_top-(uintptr_t)scheduler_state_begin;}
static void task(unsigned slot, unsigned gen, unsigned state) {
    uint64_t *t=scheduler_tasks+32*slot;
    uint64_t *f=scheduler_table_frames+4*slot;
    t[0]=state;t[1]=gen;t[28]=slot?0x1b:0x1a;
    for(unsigned i=0;i<8;i++) t[4+i]=0x10000+slot*0x10000+i*4096;
    t[3]=0x18000+slot*0x10000;
    for(unsigned i=0;i<4;i++) f[i]=0x19000+slot*0x10000+i*4096;
    t[2]=f[0]; t[12]=0x400000; t[13]=0x408f80;
    scheduler_syscall_profiles[2*slot]=gen;
    scheduler_syscall_profiles[2*slot+1]=slot?MASK_CHILD:MASK_PARENT;
    scheduler_cpu_budgets[4*slot]=gen;
    scheduler_cpu_budgets[4*slot+1]=slot?32:128;
}
static void message(uint8_t *p) {uint32_t words[3]={1,140,0};memcpy(p,words,sizeof(words));}
/* plan1 no child;2 ready;3 blocked;4 already reaped. endpoint may be absent. */
static void setup(unsigned completed, unsigned plan, int endpoint) {
    memset(scheduler_state_begin,0,arena_size());
    scheduler_mode[0]=7;scheduler_active[0]=scheduler_shell_started[0]=1;
    scheduler_original_cr3[0]=0x1000;
    unsigned spawn=completed+(plan!=1),gen=40+spawn,reaped=completed+(plan==4);
    scheduler_dynamic_spawn_count[0]=spawn;scheduler_dynamic_completed_count[0]=completed;
    scheduler_reap_count[0]=reaped;
    scheduler_identity_pool[0]=(uintptr_t)scheduler_tasks;
    scheduler_identity_pool[1]=(uintptr_t)scheduler_identity_retired;
    scheduler_identity_pool[2]=4|((uint64_t)gen<<32);
    scheduler_identity_retired[1]=reaped?40+reaped:0;
    task(0,40,2);
    scheduler_event_count[0]=(uint8_t)(2+reaped);
    scheduler_events[0]=0x70;scheduler_events[1]=0x71;
    for(unsigned i=0;i<reaped;i++)scheduler_events[2+i]=0x74;
    if(plan!=1) {
        scheduler_dynamic_child_active[0]=1;
        scheduler_dynamic_parent_generation[0]=40;scheduler_dynamic_child_generation[0]=gen;
        if(plan==4) {
            scheduler_child_terminal_generation[0]=gen;scheduler_child_terminal_status[0]=77;
            scheduler_child_terminal_reason[0]=1;scheduler_child_terminal_parent_state[0]=1;
            scheduler_child_terminal_rip[0]=0x400010;
        } else task(1,gen,plan==2?1:6);
    }
    if(plan==2) {
        scheduler_runqueue_tail[0]=scheduler_runqueue_count[0]=scheduler_runqueue_membership[1]=1;
        scheduler_runqueue_entries[0]=1|((uint64_t)gen<<32);
    }
    if(endpoint) {
        unsigned e=plan==1?spawn+1:spawn, handle=(e<<8)|1;
        scheduler_shell_ipc_endpoint_active[0]=1;scheduler_shell_ipc_endpoint_generation[0]=e;
        scheduler_shell_ipc_endpoint_owner_generation[0]=40;scheduler_shell_ipc_endpoint_handle[0]=handle;
        scheduler_shell_ipc_capabilities[0]=40;scheduler_shell_ipc_capabilities[1]=handle;
        scheduler_shell_ipc_capabilities[2]=7;
        if(plan==2 || plan==3) {
            scheduler_shell_ipc_capabilities[3]=gen;scheduler_shell_ipc_capabilities[4]=handle;
            scheduler_shell_ipc_capabilities[5]=1;
        }
        if(plan==3) {
            scheduler_shell_ipc_message_ready[0]=1;scheduler_shell_ipc_message_sender_generation[0]=40;
            scheduler_shell_ipc_send_generation[0]=gen;scheduler_shell_ipc_send_phase[0]=3;
            scheduler_shell_ipc_send_wait_generation[0]=gen;scheduler_shell_ipc_send_wait_handle[0]=handle;
            message(scheduler_shell_ipc_message);message(scheduler_shell_ipc_send_wait_message);
            scheduler_deadline_count[0]=scheduler_deadline_membership[1]=1;
            scheduler_deadline_entries[0]=12;scheduler_deadline_entries[1]=gen|(1ULL<<32);
            scheduler_last_tick[0]=10;scheduler_final_tick[0]=12;
        }
    }
}
static int checked(int expected) {
    static uint8_t snapshot[32768];
    if(arena_size()>sizeof(snapshot))return 0;
    volatile const uint8_t *b=scheduler_state_begin;
    for(size_t i=0;i<arena_size();i++)snapshot[i]=b[i];
    int result=owner_admit();
    for(size_t i=0;i<arena_size();i++)if(snapshot[i]!=b[i]) {printf("mutated %zu\n",i);return 0;}
    if(result!=expected)printf("expected=%d result=%d plan-child=%llu\n",expected,result,(unsigned long long)scheduler_tasks[32]);
    return result==expected;
}
static int dirty(void *p,size_t n) {
    uint8_t *b=p;
    for(size_t i=0;i<n;i++) {b[i]^=0x80;int ok=checked(0);b[i]^=0x80;if(!ok){printf("dirty byte=%zu\n",i);return 0;}}
    return 1;
}
#define DIRTY(n) CHECK(dirty(scheduler_##n,sizeof(*scheduler_##n)))
int main(void) {
    for(unsigned n=0;n<=2;n++)for(unsigned plan=1;plan<=4;plan++) {
        if(n==2 && plan!=1)continue;
        for(int endpoint=0;endpoint<=1;endpoint++) {
            if((plan==3 && !endpoint)||(plan==4 && endpoint)||(n==2 && endpoint))continue;
            setup(n,plan,endpoint);CHECK(checked((int)plan));
            DIRTY(mode);DIRTY(active);DIRTY(current_slot);DIRTY(shell_started);
            DIRTY(dynamic_spawn_count);DIRTY(dynamic_completed_count);DIRTY(dynamic_child_generation);
            DIRTY(dynamic_parent_generation);DIRTY(dynamic_child_active);DIRTY(reap_count);
            DIRTY(dynamic_wait_generation);DIRTY(dynamic_wait_child_generation);DIRTY(dynamic_wait_status_direct);
            CHECK(dirty(scheduler_identity_retired,16));CHECK(dirty(scheduler_identity_pool+2,8));
            CHECK(dirty(scheduler_syscall_profiles,64));CHECK(dirty(scheduler_owner_receipt,40));
            CHECK(dirty(scheduler_tasks+64,512));CHECK(dirty(scheduler_fp_states+1024,1024));
            CHECK(dirty(scheduler_table_frames+8,64));CHECK(dirty(scheduler_cpu_budgets+8,64));
            DIRTY(runqueue_head);DIRTY(runqueue_tail);DIRTY(runqueue_count);
            CHECK(dirty(scheduler_runqueue_membership,4));CHECK(dirty(scheduler_runqueue_entries,32));
            DIRTY(deadline_count);CHECK(dirty(scheduler_deadline_membership,4));CHECK(dirty(scheduler_deadline_entries,64));
            if(!endpoint)CHECK(dirty(scheduler_shell_ipc_begin,(uintptr_t)scheduler_shell_ipc_end-(uintptr_t)scheduler_shell_ipc_begin));
            if(endpoint) {
                DIRTY(shell_ipc_endpoint_active);DIRTY(shell_ipc_endpoint_generation);DIRTY(shell_ipc_endpoint_owner_generation);
                DIRTY(shell_ipc_endpoint_handle);CHECK(dirty(scheduler_shell_ipc_capabilities,96));
                DIRTY(shell_ipc_message_ready);DIRTY(shell_ipc_message_sender_generation);
            }
            CHECK(checked((int)plan));
        }
    }
    setup(0,2,1);scheduler_tasks[36]=scheduler_tasks[4];CHECK(checked(0)); /* cross-owner alias */
    setup(0,2,1);scheduler_tasks[35]=0;CHECK(checked(0));
    setup(0,1,0);scheduler_cpu_budgets[1]=129;CHECK(checked(0));
    setup(0,1,0);scheduler_cpu_budgets[2]=129;scheduler_cpu_budgets[3]=129;CHECK(checked(0));
    setup(0,1,0);scheduler_cpu_budgets[2]=128;scheduler_cpu_budgets[3]=128;CHECK(checked(1));
    setup(0,4,0);scheduler_child_terminal_generation[0]=42;CHECK(checked(0));
    setup(0,4,0);scheduler_child_terminal_reason[0]=2;CHECK(checked(0));
    setup(0,3,1);scheduler_final_tick[0]=10;CHECK(checked(0));
    setup(0,3,1);scheduler_shell_ipc_send_wait_generation[0]=40;CHECK(checked(0));
    puts("OWNER_TERMINAL_HOST_OK generations=2 live_blocked_pending_quiescent_no_mutation=1");
    return 0;
}
