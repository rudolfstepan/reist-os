#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../arch/x86_64/proc/process_run.h"
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const struct reist_x64_run_v1 *);
#define CHECK(c) do { if(!(c)) { printf("line %d\n",__LINE__);return 1; } } while(0)
#ifndef CONSOLE_MEDIATOR
int main(void) {
    struct reist_x64_run_v1 p={2,144,4,0,{{0}}};
    for(unsigned n=0;n<4;n++) {
        p.tasks[n].syscalls=REIST_X64_RUN_SYSCALLS;
        p.tasks[n].cpu_samples=32;p.tasks[n].reserved=n+3;
    }
    struct reist_x64_run_v1 original=p;
    for(unsigned rights=0;rights<4;rights++) {
        uint64_t mask=((rights&1)?1ULL<<15:0)|((rights&2)?1ULL<<20:0);
        for(unsigned slot=0;slot<4;slot++) {
            p=original;p.tasks[slot].syscalls|=mask;
            struct reist_x64_run_v1 before=p;
            CHECK(process_run_admit64(&p)==(!mask || !slot));
            CHECK(!memcmp(&p,&before,sizeof p));
        }
    }
    p=original;p.tasks[0].syscalls|=(1ULL<<15)|(1ULL<<20);
    CHECK(process_run_admit64(&p)==1);
    p.tasks[1].syscalls|=1ULL<<15;CHECK(!process_run_admit64(&p));
    p=original;p.version=1;
    for(unsigned n=0;n<4;n++)p.tasks[n].reserved=0;
    CHECK(process_run_admit64(&p)==1);
    p.tasks[0].syscalls|=1ULL<<15;CHECK(!process_run_admit64(&p));
    p=original;p.tasks[0].syscalls|=1ULL<<20;
    for(unsigned q=0;q<64;q++) {
        struct reist_x64_run_v1 bad=p;bad.tasks[0].syscalls|=1ULL<<q;
        uint64_t allowed=REIST_X64_RUN_SYSCALLS|(1ULL<<15)|(1ULL<<20);
        CHECK(process_run_admit64(&bad)==((allowed>>q)&1));
    }
    CHECK(!process_run_admit64(0));
    puts("CONSOLE_ADMISSION_OK actual_masks_slot_version_nonmutation=1");return 0;
}
#else
extern int64_t __attribute__((sysv_abi)) console_apply(void);
extern uint64_t scheduler_current_slot,syscall_rax,syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9;
static unsigned char buffer[80],sent[64];
static unsigned checks,inputs,outputs,available,hardware_error,range_ok,range_calls,bad;
static uintptr_t wanted;static unsigned length,permission;
uint64_t __attribute__((sysv_abi)) host_range(uint64_t address,uint64_t size,uint64_t access) {
    range_calls++;if(address!=wanted || size!=length || access!=permission || checks || inputs || outputs) bad++;
    return range_ok;
}
uint64_t __attribute__((sysv_abi)) host_in(uint64_t port) {
    if(port==0x3fd) { checks++;return inputs+outputs>=available?hardware_error?2:0:0x21; }
    if(port!=0x3f8 || checks!=inputs+1 || outputs) bad++;
    return 0x30+inputs++;
}
void __attribute__((sysv_abi)) host_out(uint64_t port,uint64_t byte) {
    if(port!=0x3f8 || outputs>=64 || checks!=outputs+1 || inputs) {bad++;return;}
    sent[outputs++]=(unsigned char)byte;
}
static void reset(unsigned write,unsigned size) {
    scheduler_current_slot=0;syscall_rax=write?20:15;syscall_rdi=write;
    syscall_rsi=(uintptr_t)(buffer+8);syscall_rdx=size;syscall_r10=syscall_r8=syscall_r9=0;
    memset(buffer,0xa5,sizeof buffer);memset(sent,0,sizeof sent);
    checks=inputs=outputs=range_calls=hardware_error=bad=0;available=64;range_ok=1;
    wanted=syscall_rsi;length=size;permission=write?4:2;
}
int main(void) {
    for(unsigned write=0;write<2;write++)for(unsigned size=0;size<=65;size++) {
        for(unsigned ready=0;ready<=64;ready++)for(unsigned error=0;error<=1;error++) {
            reset(write,size);available=ready;hardware_error=error;
            unsigned count=size<ready?size:ready;
            int64_t expected=size>64?-22:!size?0:count?(int64_t)count:error?-5:-11;
            CHECK(console_apply()==expected && !bad);
            if(size>64 || !size) CHECK(!checks && !inputs && !outputs && !range_calls);
            else {
                CHECK(range_calls==1 && checks<=64 && inputs+outputs==count);
                CHECK(checks==count+(count<size));
                for(unsigned n=0;n<80;n++) {
                    unsigned char want=!write && n>=8 && n<8+count?(unsigned char)(0x30+n-8):0xa5;
                    CHECK(buffer[n]==want);
                }
                for(unsigned n=0;n<outputs;n++) CHECK(sent[n]==0xa5);
            }
        }
    }
    for(unsigned write=0;write<2;write++)for(unsigned kind=0;kind<10;kind++) {
        reset(write,64);int64_t expected=-22;
        if(kind==0) {range_ok=0;expected=-14;}
        if(kind==1) {syscall_rsi=0;wanted=0;range_ok=0;expected=-14;}
        if(kind==2) {syscall_rdi=2;expected=-9;}
        if(kind==3) syscall_r10=1;
        if(kind==4) syscall_r8=1;
        if(kind==5) syscall_r9=1;
        if(kind==6) {scheduler_current_slot=1;expected=-13;}
        if(kind==7) {scheduler_current_slot=UINT32_MAX;expected=-13;}
        if(kind==8) syscall_rax=19;
        if(kind==9) syscall_rdx=UINT64_MAX;
        CHECK(console_apply()==expected && !bad && !checks && !inputs && !outputs);
        for(unsigned n=0;n<80;n++)CHECK(buffer[n]==0xa5);
    }
    puts("CONSOLE_MEDIATOR_OK actual_branches_bounds_partial_no_effect_before_admission=1");return 0;
}
#endif
