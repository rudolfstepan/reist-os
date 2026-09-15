/* Actual selected mechanisms with only existing explicit host hardware fakes. */
#if defined(TASK_POOL_HEAP_TEST)
#define main task_pool_legacy_heap_main
#include "x86_64_native_heap_host.c"
#undef main
int main(int argc,char **argv) {
    CHECK(argc==2);start();
    NativeHeapCall owners[REIST_NATIVE_TASKS];uint64_t addresses[REIST_NATIVE_TASKS];
    owners[0]=owner;
    for(unsigned s=0;s<REIST_NATIVE_TASKS;s++) {
        if(s) {
            owner=(NativeHeapCall){0};owner.slot=s;owner.generation=s+1;
            owner.root=reist_native_heap_frame(false);owner.pdpt=reist_native_heap_frame(false);
            ((uint64_t*)reist_native_heap_pointer(owner.root))[0]=owner.pdpt|7;
            CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);owners[s]=owner;
        }
        addresses[s]=(uint64_t)complete(invoke(NATIVE_HEAP_MALLOC,8192,0));
        CHECK(addresses[s]==NATIVE_HEAP_BASE);
        for(unsigned b=0;b<8192;b++){CHECK(*data(addresses[s]+b)==0);*data(addresses[s]+b)=(unsigned char)(s+b);}
    }
    owner=owners[REIST_NATIVE_TASKS-1];
    if(!strcmp(argv[1],"corrupt")) {
        native_heap_state.tasks[owner.slot].control.generation^=2;
        expected_fault=1;(void)invoke(NATIVE_HEAP_MALLOC,4096,0);return 3;
    }
    if(!strcmp(argv[1],"outside")) {
        owner.slot=REIST_NATIVE_TASKS;expected_fault=1;
        (void)invoke(NATIVE_HEAP_CANCEL,0,0);return 3;
    }
    CHECK(!strcmp(argv[1],"normal") || !strcmp(argv[1],"stale"));
    for(unsigned s=REIST_NATIVE_TASKS;s-->0;) {
        owner=owners[s];
        for(unsigned b=0;b<8192;b++)CHECK(*data(addresses[s]+b)==(unsigned char)(s+b));
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0);
        unsigned before=live;CHECK(invoke(NATIVE_HEAP_CANCEL,0,0)==0 && live==before);
        owner.generation+=REIST_NATIVE_TASKS;CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);
        if(!strcmp(argv[1],"stale")) {
            owner.generation-=REIST_NATIVE_TASKS;expected_fault=1;
            (void)invoke(NATIVE_HEAP_CANCEL,0,0);return 3;
        }
        CHECK(complete(invoke(NATIVE_HEAP_MALLOC,4096,0))==(int64_t)addresses[s]);
        for(unsigned b=0;b<4096;b++)CHECK(*data(addresses[s]+b)==0);
        CHECK(complete(invoke(NATIVE_HEAP_CANCEL,0,0))==0);
        CHECK(!native_heap_state.tasks[s].control.generation &&
              native_heap_state.tasks[s].control.last_generation==owner.generation);
        reist_native_heap_release(owner.root);reist_native_heap_release(owner.pdpt);
    }
    CHECK(!live && acquisitions==releases);
    puts("TASK_POOL_HEAP_OK");return 0;
}
#elif defined(TASK_POOL_IPC_TEST)
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "arch/x86_64/ipc/native_ipc.c"
#undef assert
#define assert(x) do { if(!(x)) { fprintf(stderr,"check failed line%d: %s\n",__LINE__,#x);exit(1); } } while(0)
/* The same explicit fatal boundary as the existing four-owner host fixture.
 * Include production directly, not its unrelated executable's main function. */
static int expected_fault;
static native_ipc_request_t r;
void reist_native_ipc_fault(void) {
    if(expected_fault){puts("NATIVE_IPC_FAULT_CLOSED_OK");exit(0);}
    fputs("unexpected native integrity fault\n",stderr);exit(2);
}
static unsigned pool_gen[REIST_NATIVE_TASKS];
static void pool_call(unsigned op,unsigned slot,unsigned now) {
    assert(reist_native_ipc(op,slot,pool_gen[slot],now,&r)==1);
}
static void pool_request(unsigned slot,unsigned nr,unsigned handle,unsigned arg,unsigned timeout) {
    memset(&r,0,sizeof(r));r.number=nr;r.a0=handle;r.a1=arg;r.a2=timeout;
    r.message.version=1;r.message.struct_size=140;r.message.length=4;r.message.payload[0]=(unsigned char)arg;
    pool_call(NATIVE_IPC_REQUEST,slot,0);
}
int main(int argc,char **argv) {
    assert(argc==2);
    if(!strcmp(argv[1],"check-failure")) {
#ifdef NDEBUG
        puts("TASK_POOL_CHECK_NDEBUG=1");
#endif
        assert((puts("TASK_POOL_CHECK_SIDE_EFFECT"),0));
        puts("TASK_POOL_CHECK_BYPASSED");return 3;
    }
    for(unsigned s=0;s<REIST_NATIVE_TASKS;s++){pool_gen[s]=s+1;pool_call(NATIVE_IPC_BIND,s,0);}
    unsigned last=REIST_NATIVE_TASKS-1;
    if(!strcmp(argv[1],"corrupt")) {
        clients[last].generation^=2;expected_fault=1;
        pool_call(NATIVE_IPC_PUMP,0,0);return 3;
    }
    if(!strcmp(argv[1],"outside")) {
        expected_fault=1;reist_native_ipc(NATIVE_IPC_BIND,REIST_NATIVE_TASKS,99,0,&r);return 3;
    }
    assert(!strcmp(argv[1],"normal") || !strcmp(argv[1],"owner") || !strcmp(argv[1],"stale"));
    unsigned handles[REIST_NATIVE_TASKS]={0};
    for(unsigned s=2;s<REIST_NATIVE_TASKS;s++) {
        pool_request(0,49,0,0,0);assert(!r.result && r.handle);handles[s]=r.handle;
        pool_request(0,55,handles[s],pool_gen[s],2);assert(!r.result);
        pool_request(s,54,handles[s],0,100);assert(r.result==NATIVE_IPC_PENDING);
    }
    /* An unrelated owner continues while all six child completions are pending. */
    pool_request(1,49,0,0,0);assert(!r.result);unsigned peer=r.handle;
    pool_request(1,55,peer,pool_gen[0],3);assert(!r.result);
    pool_request(1,53,peer,93,0);assert(!r.result);
    pool_request(0,54,peer,0,0);assert(!r.result && r.message.payload[0]==93);
    pool_request(0,53,peer,94,0);assert(!r.result);
    pool_request(1,54,peer,0,0);assert(!r.result && r.message.payload[0]==94);
    if(!strcmp(argv[1],"owner")) {
        pool_call(NATIVE_IPC_REAP,0,0);assert(r.ready==REIST_NATIVE_CHILD_MASK);
    } else for(unsigned s=2;s<REIST_NATIVE_TASKS;s++) {
        pool_request(0,53,handles[s],s,0);assert(!r.result && (r.ready&(1U<<s)));
    }
    for(unsigned s=2;s<REIST_NATIVE_TASKS;s++) {
        pool_call(NATIVE_IPC_TAKE,s,0);
        assert(r.result==(!strcmp(argv[1],"owner")?-32:0));
        if(!r.result)assert(r.message.payload[0]==s && r.copy_size==140);
        assert(!pending[s].state);
    }
    for(unsigned s=0;s<REIST_NATIVE_TASKS;s++) {
        if(s || strcmp(argv[1],"owner"))pool_call(NATIVE_IPC_REAP,s,0);
        assert(!clients[s].is_running && !pending[s].state && retired[s]==pool_gen[s]);
    }
    pool_call(NATIVE_IPC_END,0,0);
    for(unsigned s=0;s<REIST_NATIVE_TASKS;s++){pool_gen[s]+=REIST_NATIVE_TASKS;pool_call(NATIVE_IPC_BIND,s,0);}
    if(!strcmp(argv[1],"stale")) {
        expected_fault=1;--pool_gen[last];pool_call(NATIVE_IPC_REAP,last,0);return 3;
    }
    for(unsigned s=2;s<REIST_NATIVE_TASKS;s++){pool_request(s,54,handles[s],0,0);assert(r.result==-9);}
    for(unsigned s=0;s<REIST_NATIVE_TASKS;s++)pool_call(NATIVE_IPC_REAP,s,0);
    pool_call(NATIVE_IPC_END,0,0);
    puts("TASK_POOL_IPC_OK");return 0;
}
#elif defined(TASK_POOL_FAMILY_TEST)
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../include/reist/abi/syscall.h"
#define C(x) do {if(!(x)){printf("TASK_POOL_FAMILY_FAIL line=%d\n",__LINE__);return 1;}}while(0)
extern uint8_t core_begin[],core_end[];
/* Actual ASM uses eight-byte alignment, not the compiler's default sixteen
 * for large extern arrays. Preserve its layout in optimized host accesses. */
_Alignas(8) extern uint64_t family_records[8][8],family_profiles[8][4],scheduler_tasks[8][128],scheduler_last_tick;
_Alignas(8) extern uint64_t scheduler_deadline_entries[8][2];
_Alignas(8) extern uint32_t process_run_plan[],process_run_generations[8],family_reasons[8];
extern uint32_t family_total,family_cancel_mask;
_Alignas(8) extern uint32_t scheduler_current_slot,process_run_receipt[8],process_heap_retire_mask;
extern uint64_t __attribute__((sysv_abi)) family_validate_runtime64(void);
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const reist_task_control_request_t *);
extern void __attribute__((sysv_abi)) family_terminal64(void),family_reaped64(void),family_expire_test(uint64_t,uint64_t);
static void pool_family_setup(void) {
    memset(core_begin,0,(size_t)(core_end-core_begin));process_run_plan[0]=4;family_total=8;scheduler_last_tick=100;
    for(unsigned s=0;s<8;s++) {
        family_records[s][0]=((uint64_t)(s+1)<<32)|s;family_records[s][5]=s<2?1:2;
        scheduler_tasks[s][0]=1;scheduler_tasks[s][1]=s+1;process_run_generations[s]=s+1;
        if(s>=2)family_records[s][1]=family_records[s&1][0];
    }
}
int main(void) {
    uint8_t before[32768];size_t size=(size_t)(core_end-core_begin);C(size<=sizeof(before));
    pool_family_setup();C(family_validate_runtime64()==1);
    for(unsigned s=2;s<8;s++)for(unsigned bit=0;bit<64;bit++) {
        pool_family_setup();family_records[s][1]^=1ULL<<bit;
        for(size_t i=0;i<size;i++)before[i]=((volatile uint8_t*)core_begin)[i];
        C(!family_validate_runtime64());C(!memcmp(before,core_begin,size));
    }
    for(unsigned s=0;s<8;s++) {
        pool_family_setup();family_records[s][7]=1;C(!family_validate_runtime64());
        pool_family_setup();process_run_generations[s]++;C(!family_validate_runtime64());
    }
    pool_family_setup();family_records[1][2]=family_records[7][0];family_records[1][3]=105;
    scheduler_tasks[1][0]=6;scheduler_deadline_entries[7][0]=105;scheduler_deadline_entries[7][1]=2;
    C(family_validate_runtime64()==1);family_expire_test(1,105);
    C(!family_records[1][2] && !family_records[1][3] && (int64_t)scheduler_tasks[1][85]==-110);
    for(unsigned root=0;root<2;root++) {
        pool_family_setup();scheduler_current_slot=root;process_run_receipt[3]=3;scheduler_tasks[root][0]=3;
        family_terminal64();C(family_records[root][5]==5 && family_records[root^1][5]==1);
        C(family_cancel_mask==(root?0xa8U:0x54U));
        for(unsigned s=2;s<8;s++)C(family_reasons[s]==((s&1)==root?3U:0U));
        process_heap_retire_mask=1U<<root;C(family_validate_runtime64()==1);
        scheduler_tasks[root][0]=0;family_reaped64();process_heap_retire_mask=0;
        C(family_records[root][5]==6 && family_validate_runtime64()==1);
        for(unsigned s=2;s<8;s++)if((s&1)==root) {
            scheduler_current_slot=s;scheduler_tasks[s][0]=3;process_run_receipt[2]=0;
            family_terminal64();C(family_records[s][5]==3 && family_records[s][4]==3ULL<<32);
            process_heap_retire_mask=1U<<s;C(family_validate_runtime64()==1);
            family_profiles[s][3]=1;C(!family_validate_runtime64());family_profiles[s][3]=0;
            scheduler_tasks[s][0]=0;family_reaped64();process_heap_retire_mask=0;
            C(family_records[s][5]==4 && family_validate_runtime64()==1);
        }
    }
    for(unsigned s=0;s<9;s++) {
        reist_task_control_request_t q={1,64,2,0,((uint64_t)(s+1)<<32)|s,0,1000,0,0,0};
        reist_task_control_request_t saved=q;
        C(family_request_admit64(&q)==(s<8?1:-22));C(!memcmp(&saved,&q,sizeof(q)));
        q.operation=3;q.timeout_ms=0;C(family_request_admit64(&q)==(s<8?1:-22));
    }
    pool_family_setup();family_total=19;C(!family_validate_runtime64());
    pool_family_setup();family_records[0][6]=9;C(!family_validate_runtime64());
    pool_family_setup();family_cancel_mask=256;C(!family_validate_runtime64());
    puts("TASK_POOL_FAMILY_OK");return 0;
}
#else
/* Independent exact run layouts and no-mutation oracle. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const void *);
extern uint64_t __attribute__((sysv_abi)) task_pool_host_capacity(void);
extern uint64_t __attribute__((sysv_abi)) process_ipc_completion_apply64(void *,uint64_t,uint64_t,uint64_t);
typedef struct { uint64_t argument,mask,cpu,image; } Task;
typedef struct { uint32_t version,size,count,reserved;Task task[8]; } Plan;
_Static_assert(sizeof(Plan)==272,"independent private run-v4 layout");
#define C(x) do { if(!(x)) { printf("TASK_POOL_ADMISSION_FAIL line=%d\n",__LINE__);return 1; } } while(0)
static Plan make(unsigned version) {
    Plan p={0};p.version=version;p.count=version==4?8:4;p.size=16+32*p.count;
    for(unsigned s=0;s<p.count;s++)p.task[s]=(Task){s<2,1ULL<<9,32,s<2?s+3:s+5};
    return p;
}
static int checked(Plan *p,unsigned expected) {
    Plan before=*p;uint64_t value=process_run_admit64(p);
    return value==expected && !memcmp(&before,p,sizeof(*p));
}
int main(void) {
    unsigned capacity=(unsigned)task_pool_host_capacity();C(capacity==4 || capacity==8);
    _Alignas(16) Plan p=make(3);C(checked(&p,1));
    p=make(4);C(checked(&p,capacity==8));
    if(capacity==8) {
    for(unsigned s=0;s<8;s++) {
        for(unsigned cpu=1;cpu<=32;cpu++){p=make(4);p.task[s].cpu=cpu;C(checked(&p,1));}
        p=make(4);p.task[s].cpu=0;C(checked(&p,0));
        p=make(4);p.task[s].cpu=33;C(checked(&p,0));
        p=make(4);p.task[s].mask|=1ULL<<63;C(checked(&p,0));
        p=make(4);p.task[s].mask=0;C(checked(&p,0));
        p=make(4);p.task[s].argument^=1;C(checked(&p,0));
        p=make(4);p.task[s].image=13;C(checked(&p,0));
        if(s>=2){p=make(4);p.task[s].image=(s==7?7:s+6);C(checked(&p,0));}
    }
    for(unsigned count=0;count<=9;count++)if(count!=8){p=make(4);p.count=count;C(checked(&p,0));}
    for(unsigned size=0;size<=280;size+=8)if(size!=272){p=make(4);p.size=size;C(checked(&p,0));}
    p=make(4);p.version=5;C(checked(&p,0));
    p=make(4);p.reserved=1;C(checked(&p,0));
    C(!process_run_admit64(0));
    p=make(4);C(!process_run_admit64((const unsigned char*)&p+1));
    }
    uint64_t completion[8][3]={0};
    for(unsigned s=0;s<capacity;s++) {
        completion[s][1]=UINT64_MAX;completion[s][2]=UINT64_C(0x936da17cb852e40f);
    }
    for(unsigned round=0;round<2;round++) {
        for(unsigned s=0;s<capacity;s++)C(process_ipc_completion_apply64(completion,1,s,round*capacity+s+1)==1);
        for(unsigned s=0;s<capacity;s++) {
            unsigned generation=round*capacity+s+1;
            C(process_ipc_completion_apply64(completion,2,s,generation)==1);
            C(process_ipc_completion_apply64(completion,3,s,generation)==1);
            C(process_ipc_completion_apply64(completion,0,s,generation)==2);
            C(process_ipc_completion_apply64(completion,4,s,generation)==1);
            uint64_t before[8][3];memcpy(before,completion,sizeof(before));
            C(!process_ipc_completion_apply64(completion,5,s,generation+1));
            C(!memcmp(before,completion,sizeof(before)));
        }
        for(unsigned s=0;s<capacity;s++)for(unsigned word=0;word<3;word++)for(unsigned bit=0;bit<64;bit++) {
            uint64_t poisoned[8][3];memcpy(poisoned,completion,sizeof(poisoned));poisoned[s][word]^=1ULL<<bit;
            uint64_t before[8][3];memcpy(before,poisoned,sizeof(before));
            C(!process_ipc_completion_apply64(poisoned,7,0,0));C(!memcmp(before,poisoned,sizeof(before)));
        }
        for(unsigned s=0;s<capacity;s++)C(process_ipc_completion_apply64(completion,5,s,round*capacity+s+1)==1);
        C(process_ipc_completion_apply64(completion,6,0,0)==1);
        uint64_t before[8][3];memcpy(before,completion,sizeof(before));
        C(!process_ipc_completion_apply64(completion,1,capacity,99));C(!memcmp(before,completion,sizeof(before)));
    }
    puts("TASK_POOL_ADMISSION_OK");return 0;
}
#endif
