#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kernel/sched/wait_queue.h"

/* Only privileged CPU access and the final dispatcher are mocked. The actual
 * deadline transitions, pending hint, ordered queue and PIT decision execute. */
#define MAX_TASKS 32U
#define SCHEDULER_QUANTUM_MS 10U
#define TASK_READY 0
#define TASK_SLEEPING 2
#define TASK_WAITING 4
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
#define KASSERT_IRQ_DISABLED() CHECK(!irq_on)
typedef struct {
    int status, wait_result, blocked_owner_task;
    uint32_t blocked_owner_generation, cpu_affinity_mask;
    wait_queue_node_t wait_node;
    uint64_t wait_deadline_ms;
} task_t;
static task_t tasks[MAX_TASKS];
static wait_queue_t sleep_waiters, other_waiters;
static int task_table_lock, current_task;
static bool irq_on, kernel_context_saved, preemption_pending, apic_timer_active;
static unsigned preempt_disable_count, pit_scheduler_ticks, dispatches, defer_dispatch;
static struct { unsigned cpu_index; } local;
#define scheduler_cpu_local() (&local)
static bool irq_enabled(void) { return irq_on; }
static uint32_t irq_save(void) { bool old=irq_on; irq_on=false; return old; }
static void irq_restore(uint32_t flags) { irq_on=flags!=0; }
static void spinlock_acquire(int *lock) { CHECK(!*lock); *lock=1; }
static void spinlock_release(int *lock) { CHECK(*lock); *lock=0; }
static void assert_task_table_locked(void) { CHECK(task_table_lock); }
static task_t *task_from_wait_node(wait_queue_node_t *node) {
    task_t *task=(task_t *)((char *)node - offsetof(task_t,wait_node));
    CHECK(task>=tasks && task<tasks+MAX_TASKS); return task;
}
static bool scheduler_uses_pit_fallback(void) { return !apic_timer_active; }
static void scheduler_interrupt_handler(void) {
    CHECK(!irq_on && !task_table_lock);
    if(preempt_disable_count || defer_dispatch) { preemption_pending=true; return; }
    ++dispatches; preemption_pending=false;
}
#include "scheduler-under-test.h"

static void reset(bool apic) {
    memset(tasks,0,sizeof(tasks)); wait_queue_init(&sleep_waiters); wait_queue_init(&other_waiters);
    task_table_lock=0; current_task=-1; kernel_context_saved=true; irq_on=false;
    preemption_pending=false; apic_timer_active=apic; preempt_disable_count=0;
    pit_scheduler_ticks=0; dispatches=0; defer_dispatch=0; local.cpu_index=0;
}
static void sleeper(unsigned index, uint64_t deadline, uint32_t affinity) {
    task_t *t=tasks+index; t->status=TASK_SLEEPING; t->cpu_affinity_mask=affinity;
    t->blocked_owner_task=3; t->blocked_owner_generation=7;
    CHECK(wait_queue_insert_ordered_locked(&sleep_waiters,&t->wait_node,deadline));
}
static void waiter(unsigned index, uint64_t deadline, uint32_t affinity) {
    task_t *t=tasks+index; t->status=TASK_WAITING; t->cpu_affinity_mask=affinity;
    t->wait_deadline_ms=deadline; t->blocked_owner_task=3; t->blocked_owner_generation=7;
    CHECK(wait_queue_push_locked(&other_waiters,&t->wait_node));
}
static void tick(uint64_t now) {
    uint32_t flags=irq_save();
    scheduler_wake_expired_sleepers_locked(now);
    scheduler_wake_expired_waiters_locked(now);
    scheduler_pit_interrupt_handler();
    CHECK(!irq_on); irq_restore(flags);
}
int main(void) {
    reset(true); sleeper(0,1,1); tick(1);
    CHECK(tasks[0].status==TASK_READY && dispatches==1); /* red before repair */
    CHECK(!preemption_pending && !tasks[0].wait_node.queue);
    CHECK(tasks[0].blocked_owner_task==-1 && tasks[0].blocked_owner_generation==0);
    for(unsigned i=2;i<1000;++i) tick(i);
    CHECK(dispatches==1); /* no unconditional1kHz scheduler */

    reset(true); waiter(0,1,1); waiter(1,2,1); waiter(2,UINT64_MAX,1); tick(1);
    CHECK(dispatches==1 && tasks[0].wait_result==-110 && tasks[1].status==TASK_WAITING);
    CHECK(tasks[0].wait_deadline_ms==0 && tasks[0].blocked_owner_generation==0);
    CHECK(tasks[2].wait_node.queue==&other_waiters);
    CHECK(wait_queue_remove_locked(&other_waiters,&tasks[1].wait_node));
    tick(2); CHECK(dispatches==1); /* cancelled node never runs */

    reset(true); sleeper(0,3,1); tick(2); CHECK(dispatches==0); tick(3); CHECK(dispatches==1);
    reset(true); sleeper(0,1,1); tasks[0].status=TASK_READY; tick(1);
    CHECK(dispatches==0 && !preemption_pending); /* stale queue node */
    reset(true); sleeper(0,1,2); waiter(1,1,2); tick(1);
    CHECK(dispatches==0 && !preemption_pending); /* AP-only work */
    reset(true); sleeper(0,1,3); tick(1); CHECK(dispatches==1);

    reset(true); for(unsigned i=0;i<MAX_TASKS;++i) sleeper(i,1,1); tick(1);
    CHECK(dispatches==1 && wait_queue_is_empty(&sleep_waiters));
    for(unsigned i=0;i<MAX_TASKS;++i) CHECK(tasks[i].status==TASK_READY);
    reset(true); for(unsigned i=0;i<MAX_TASKS;++i) waiter(i,1,1); tick(1);
    CHECK(dispatches==1 && wait_queue_is_empty(&other_waiters));

    reset(true); current_task=0; sleeper(1,1,1); tick(1);
    CHECK(dispatches==0 && preemption_pending); /* running quantum preserved */
    current_task=-1; tick(2); CHECK(dispatches==1);
    reset(true); kernel_context_saved=false; sleeper(0,1,1); tick(1);
    CHECK(dispatches==0 && preemption_pending); kernel_context_saved=true;
    tick(2); CHECK(dispatches==1);
    reset(true); preempt_disable_count=1; sleeper(0,1,1); tick(1);
    CHECK(dispatches==0 && preemption_pending); preempt_disable_count=0;
    tick(2); CHECK(dispatches==1);
    reset(true); defer_dispatch=1; sleeper(0,1,1); tick(1);
    CHECK(dispatches==0 && preemption_pending); defer_dispatch=0;
    tick(2); CHECK(dispatches==1); tick(3); CHECK(dispatches==1);

    reset(false); current_task=0;
    for(unsigned i=1;i<=100;++i) { tick(i); CHECK(dispatches==i/10); }
    reset(false); sleeper(0,1,1); tick(1); CHECK(dispatches==1);
    for(unsigned i=2;i<=10;++i) tick(i);
    CHECK(dispatches==2 && pit_scheduler_ticks==0); /* fixed fallback cadence */
    reset(false); sleeper(0,10,1);
    for(unsigned i=1;i<=10;++i) tick(i);
    CHECK(dispatches==1); /* periodic and wake coalesce */
    printf("SCHEDULER_WAKE checks=%u\n",checks); return 0;
}
