#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int final_verify(void);
#define U8(n) extern uint8_t scheduler_##n[]
#define U32(n) extern uint32_t scheduler_##n[]
#define U64(n) extern uint64_t scheduler_##n[]
U8(state_begin); U8(state_end); U8(kernel_stack_top); U8(mode); U8(shell_started);
U8(event_count); U8(events); U8(runqueue_head); U8(runqueue_tail); U8(runqueue_count);
U8(runqueue_membership); U8(deadline_count); U8(deadline_membership);
U8(dynamic_child_active); U8(shell_ipc_begin); U8(shell_ipc_end); U8(syscall_profiles);
U8(fp_states); U8(tasks);
U32(dynamic_spawn_count); U32(dynamic_completed_count); U32(dynamic_child_generation);
U32(dynamic_parent_generation); U32(dynamic_wait_generation); U32(dynamic_wait_child_generation);
U32(reap_count); U32(identity_retired); U32(shell_read_count); U32(shell_write_count);
U64(identity_pool); U64(runqueue_entries); U64(deadline_entries); U64(dynamic_wait_status_direct);
U64(cpu_budgets); U64(child_terminal_reason); U64(child_terminal_cpu_ticks);
U64(child_terminal_generation); U64(child_terminal_status); U64(child_terminal_endpoint);
U64(child_terminal_rip); U64(child_terminal_parent_state); U64(child_terminal_queued);
#define CHECK(c) do {if(!(c)){printf("line %d\n",__LINE__);return 1;}}while(0)
static size_t arena_size(void) {
    return (uintptr_t)scheduler_kernel_stack_top-(uintptr_t)scheduler_state_begin;
}
static void setup(unsigned n) {
    memset(scheduler_state_begin,0,arena_size());
    scheduler_mode[0]=7; scheduler_shell_started[0]=1;
    scheduler_dynamic_spawn_count[0]=scheduler_dynamic_completed_count[0]=n;
    scheduler_reap_count[0]=n+1;
    scheduler_event_count[0]=(uint8_t)(n+4);
    scheduler_events[0]=0x70; scheduler_events[1]=0x71;
    for(unsigned i=0;i<n;++i)scheduler_events[2+i]=0x74;
    scheduler_events[2+n]=0x72; scheduler_events[3+n]=0x73;
    scheduler_identity_pool[0]=(uintptr_t)scheduler_tasks;
    scheduler_identity_pool[1]=(uintptr_t)scheduler_identity_retired;
    scheduler_identity_pool[2]=4|((uint64_t)(40+n)<<32);
    scheduler_identity_retired[0]=40;
    scheduler_identity_retired[1]=n?40+n:0;
}
#ifndef LEGACY
static int checked(int expected) {
    static uint8_t snapshot[32768];
    if(arena_size()>sizeof(snapshot))return 0;
    /* Assembly labels alias this arena. Distinct C extern symbols do not
     * express that aliasing, so both snapshot and observation are volatile. */
    const volatile uint8_t *observed=scheduler_state_begin;
    for(size_t i=0;i<arena_size();++i)snapshot[i]=observed[i];
    int actual=final_verify();
    /* Inspect externally owned assembly storage byte-for-byte. Do not let
     * optimized C object/provenance assumptions fold this cross-symbol arena. */
    int unchanged=1;
    for(size_t i=0;i<arena_size();++i)if(snapshot[i]!=observed[i]) {
        printf("changed offset=%zu before=%u after=%u\n",i,snapshot[i],observed[i]);
        unchanged=0;
        break;
    }
    if(actual!=expected || !unchanged)
        printf("count=%u expected=%d actual=%d unchanged=%d\n",
               scheduler_dynamic_completed_count[0],expected,actual,unchanged);
    return actual==expected && unchanged;
}
static int dirty(void *p,size_t size) {
    uint8_t *b=p;
    for(size_t i=0;i<size;++i) {
        b[i]^=1;
        if(!checked(0))return 0;
        b[i]^=1;
    }
    return checked(1);
}
#define DIRTY(n) CHECK(dirty(scheduler_##n,sizeof(*scheduler_##n)))
#endif
int main(void) {
#ifdef LEGACY
    setup(2);CHECK(final_verify()==1);
    setup(1);CHECK(final_verify()==0);
    setup(0);CHECK(final_verify()==0);
    puts("SHELL_EXIT_LEGACY_OK quiescent_zero_and_one_rejected=1");
#else
    for(unsigned n=0;n<3;++n) {
        setup(n);CHECK(checked(1));
        for(unsigned reads=0;reads<=19;++reads)
            for(unsigned writes=0;writes<=9;++writes) {
                scheduler_shell_read_count[0]=reads; scheduler_shell_write_count[0]=writes;
                CHECK(checked(reads<=18 && writes<=8));
            }
        scheduler_shell_read_count[0]=scheduler_shell_write_count[0]=0;
        CHECK(dirty(scheduler_events,n+4));
        DIRTY(event_count);DIRTY(runqueue_head);DIRTY(runqueue_tail);DIRTY(runqueue_count);
        CHECK(dirty(scheduler_runqueue_membership,4));CHECK(dirty(scheduler_runqueue_entries,32));
        DIRTY(reap_count);DIRTY(shell_started);DIRTY(dynamic_spawn_count);DIRTY(dynamic_completed_count);
        DIRTY(dynamic_child_active);DIRTY(dynamic_child_generation);DIRTY(dynamic_parent_generation);
        DIRTY(dynamic_wait_generation);DIRTY(dynamic_wait_child_generation);DIRTY(dynamic_wait_status_direct);
        CHECK(dirty(scheduler_identity_retired,16));
        /* Valid pointer bindings are pinned: mutate generation/capacity, not pointers. */
        CHECK(dirty(scheduler_identity_pool+2,8));
        CHECK(dirty(scheduler_syscall_profiles,64));CHECK(dirty(scheduler_tasks,1024));
        CHECK(dirty(scheduler_fp_states,2048));CHECK(dirty(scheduler_cpu_budgets,128));
        CHECK(dirty(scheduler_shell_ipc_begin,(uintptr_t)scheduler_shell_ipc_end-(uintptr_t)scheduler_shell_ipc_begin));
        DIRTY(deadline_count);CHECK(dirty(scheduler_deadline_membership,4));CHECK(dirty(scheduler_deadline_entries,64));
        DIRTY(child_terminal_reason);DIRTY(child_terminal_cpu_ticks);DIRTY(child_terminal_generation);
        DIRTY(child_terminal_status);DIRTY(child_terminal_endpoint);DIRTY(child_terminal_rip);
        DIRTY(child_terminal_parent_state);DIRTY(child_terminal_queued);
    }
    for(unsigned n=3;n<=4;++n){setup(n);CHECK(checked(0));}
    setup(0);scheduler_dynamic_spawn_count[0]=0xffffffffU;CHECK(checked(0));
    scheduler_dynamic_completed_count[0]=0xffffffffU;CHECK(checked(0));
    puts("SHELL_EXIT_HOST_OK counts=3 exact_events_generations_zero_guards_no_mutation=1");
#endif
    return 0;
}
