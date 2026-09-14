/* Real native IRQ/idle instruction slices; only privileged operations adapted. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line%d: %s\n",__LINE__,#x); exit(1); } } while (0)
enum { NOW, CR3, OWNERSHIP, CONTEXT_CALLS, TICK_CALLS, ABORT_CALLS, EOI_CALLS,
       MASK_CALLS, TAIL_CALLS, EOI_TICK, EOI_DEADLINE, TAIL_TICK, REASON,
       SEQUENCE, CONTEXT_SEQ, TICK_SEQ, EOI_SEQ, TAIL_SEQ, GENERATION,
       DEADLINE, TICKS, EOIS, LAST_TICK, ORIGINAL_CR3, READY, SLEEPING,
       LIVE, RETIRING, PENDING, STATE_WORDS };
extern uint64_t host_state[STATE_WORDS];
extern unsigned char scheduler_kernel_stack_bottom[], scheduler_kernel_stack_top[];
extern unsigned char host_idle_wait[],host_idle_resume[],host_work_wait[],host_work_resume[];
extern uint64_t __attribute__((sysv_abi)) timer_irq_host(uint64_t *);
extern uint64_t __attribute__((sysv_abi)) idle_host(uint64_t *);
extern uint64_t __attribute__((sysv_abi)) idle_return_host(uint64_t *);
static uint64_t frame[22], saved[22], before[STATE_WORDS];
static unsigned trials;
#define HORIZON (UINT64_C(1)<<60)
#define GAP UINT64_C(3000000000)
static void setup(uint64_t tick) {
    memset(host_state,0,sizeof(uint64_t)*STATE_WORDS);
    memset(frame,0,sizeof frame);
    host_state[NOW]=UINT64_C(7000000000);
    host_state[DEADLINE]=host_state[NOW]+1;
    host_state[TICKS]=host_state[EOIS]=host_state[LAST_TICK]=tick;
    host_state[CR3]=host_state[ORIGINAL_CR3]=0x101000;
    host_state[OWNERSHIP]=1;host_state[GENERATION]=6;
    host_state[SLEEPING]=host_state[LIVE]=1;
    frame[15]=32;frame[17]=(uintptr_t)host_idle_resume;
    frame[18]=8;frame[19]=0x202;frame[20]=(uintptr_t)scheduler_kernel_stack_top;frame[21]=16;
}
static void run(int accepted,unsigned reason,unsigned context,unsigned tick) {
    memcpy(saved,frame,sizeof frame);memcpy(before,host_state,sizeof before);
    CHECK(timer_irq_host(frame)==(uint64_t)accepted);
    if(accepted)saved[19]&=~UINT64_C(512);
    CHECK(!memcmp(saved,frame,sizeof frame));
    CHECK(host_state[REASON]==reason);
    CHECK(host_state[CONTEXT_CALLS]==context && host_state[TICK_CALLS]==tick);
    CHECK(host_state[EOI_CALLS]==1);
    CHECK(host_state[ABORT_CALLS]==!accepted && host_state[MASK_CALLS]==!accepted);
    CHECK(host_state[TAIL_CALLS]==(uint64_t)accepted);
    for(unsigned n=NOW;n<CONTEXT_CALLS;n++)CHECK(host_state[n]==before[n]);
    for(unsigned n=GENERATION;n<STATE_WORDS;n++) {
        uint64_t expected=before[n];
        if(accepted && n==DEADLINE)expected=before[NOW]+GAP;
        if(accepted && (n==TICKS || n==EOIS))expected++;
        CHECK(host_state[n]==expected);
    }
    CHECK(host_state[EOI_TICK]==host_state[TICKS]);
    CHECK(host_state[EOI_DEADLINE]==host_state[DEADLINE]);
    if(accepted) {
        CHECK(host_state[CONTEXT_SEQ]<host_state[TICK_SEQ]);
        CHECK(host_state[TICK_SEQ]<host_state[EOI_SEQ]);
        CHECK(host_state[EOI_SEQ]<host_state[TAIL_SEQ]);
        CHECK(host_state[TAIL_TICK]==before[TICKS]+1);
    }
    trials++;
}
static void reject_context(void) { run(0,0,1,0); }
int main(void) {
    /* Captured CLI reentry: the previous wake has already made a task READY.
       IRET must not re-enable IF until dispatcher re-admission reaches STI. */
    setup(61);host_state[READY]=1;host_state[SLEEPING]=3;host_state[LIVE]=4;
    frame[19]=0x10202;memcpy(saved,frame,sizeof frame);
    CHECK(idle_host(frame)==0);
    CHECK(idle_return_host(frame)==1);
    CHECK(frame[19]==(saved[19]&~UINT64_C(512)));
    saved[19]&=~UINT64_C(512);CHECK(!memcmp(saved,frame,sizeof frame));
    const uint64_t ticks[]={0,255,256,UINT32_MAX,UINT64_C(1)<<32,HORIZON-2};
    for(unsigned n=0;n<sizeof ticks/sizeof ticks[0];n++) {
        setup(ticks[n]);run(1,0,1,1);
        setup(ticks[n]);host_state[DEADLINE]=host_state[NOW];run(1,0,1,1);
        setup(ticks[n]);host_state[DEADLINE]=host_state[NOW]+GAP;run(1,0,1,1);
        setup(ticks[n]);host_state[DEADLINE]=host_state[NOW]-1;run(0,4,0,0);
        setup(ticks[n]);host_state[DEADLINE]=host_state[NOW]+GAP+1;run(0,5,0,0);
        setup(ticks[n]);host_state[DEADLINE]=GAP-1;run(0,3,0,0);
        setup(ticks[n]);host_state[EOIS]++;run(0,2,0,0);
        setup(ticks[n]);host_state[LAST_TICK]++;run(0,0,1,1);
    }
    setup(HORIZON-1);run(0,1,0,0);
    setup(0);host_state[NOW]=host_state[DEADLINE]=UINT64_MAX;run(0,6,0,0);
    /* Kernel-idle bounds include the post-STI/HLT/CLI window, not nearby code. */
    for(uintptr_t rip=(uintptr_t)host_idle_wait;rip<=(uintptr_t)host_idle_resume;rip++) {
        setup(100);frame[17]=rip;run(1,0,1,1);
    }
    setup(100);frame[17]=(uintptr_t)host_idle_wait-1;reject_context();
    setup(100);frame[17]=(uintptr_t)host_idle_resume+1;reject_context();
    setup(100);frame[20]=(uintptr_t)scheduler_kernel_stack_bottom;run(1,0,1,1);
    setup(100);frame[20]=(uintptr_t)scheduler_kernel_stack_bottom-1;reject_context();
    setup(100);frame[20]=(uintptr_t)scheduler_kernel_stack_top+1;reject_context();
    setup(100);frame[21]=0;reject_context();
    setup(100);frame[18]=0;reject_context();
    setup(100);frame[19]&=~UINT64_C(512);reject_context();
    setup(100);host_state[CR3]^=4096;reject_context();
    setup(100);host_state[OWNERSHIP]=0;reject_context();
    setup(100);host_state[READY]=1;reject_context();
    setup(100);host_state[SLEEPING]=0;reject_context();
    setup(100);host_state[LIVE]=2;reject_context();
    for(unsigned field=15;field<=16;field++) {setup(100);frame[field]^=1;run(0,0,0,0);}
    setup(100);host_state[GENERATION]=5;run(0,0,0,0);
    /* Every nonempty fixed retirement set with consistent live accounting. */
    for(unsigned mask=1;mask<16;mask++) {
        unsigned count=0;for(unsigned m=mask;m;m>>=1)count+=m&1;
        setup(100);host_state[RETIRING]=mask;host_state[SLEEPING]=0;host_state[LIVE]=count;
        frame[17]=(uintptr_t)host_work_resume;run(1,0,1,1);
        setup(100);host_state[RETIRING]=mask;host_state[LIVE]=count+1;
        frame[17]=(uintptr_t)host_work_wait;run(1,0,1,1);
        setup(100);host_state[RETIRING]=mask;host_state[LIVE]=count+2;
        frame[17]=(uintptr_t)host_work_wait;reject_context();
    }
    setup(100);frame[17]=(uintptr_t)host_work_wait;reject_context();
    setup(100);frame[17]=(uintptr_t)host_work_wait;host_state[RETIRING]=16;reject_context();
    printf("TIMER_IDLE_HOST_OK trials=%u publication_eoi_tail=1\n",trials);return 0;
}
