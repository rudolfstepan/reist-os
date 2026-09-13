#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../include/reist/abi/syscall.h"
#include "../userspace/drivers/ata/native_pio.c"
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d\n",__LINE__);return 1;}}while(0)
#define SYSV __attribute__((sysv_abi))
extern int64_t SYSV native_pio_admit64(const reist_native_pio_request *);
extern int64_t SYSV native_pio_apply64(uint64_t *,const reist_native_pio_request *,uint64_t,uint64_t,uint64_t);
extern int64_t SYSV family_profile_admit64(const reist_task_profile_v1_t *);
extern int64_t SYSV family_profile_attenuate64(const reist_task_profile_v1_t *,const uint64_t *,uint64_t);
static unsigned ports,last_port,last_value,word;
extern int64_t SYSV pio_adapter_test(unsigned);
extern uint64_t native_pio_state[8],native_pio_request[8],scheduler_tasks[4][32],family_records[4][8];
extern uint64_t syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9;
extern uint64_t scheduler_current_slot,scheduler_last_tick,host_faulted,host_output;
extern uint64_t family_extended_masks[4][2],family_profiles[4][4];
extern int64_t SYSV profile_adapter_test(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t);
uint64_t SYSV native_pio_in8(uint64_t p) {ports++;last_port=(unsigned)p;return 0x40;}
uint64_t SYSV native_pio_in16(uint64_t p) {ports++;last_port=(unsigned)p;return word++;}
void SYSV native_pio_out8(uint64_t p,uint64_t v) {ports++;last_port=(unsigned)p;last_value=(unsigned)v;}
static int core(void) {
    const uint64_t owner=0x300000002ULL,root=0x100000000ULL;
    uint64_t s[8]={0,UINT64_MAX,1},saved[8];
    reist_native_pio_request q={1,64,1,0,owner,0,0,0,0,0,0,0},bad;
    CHECK(native_pio_admit64(&q)==1);
    for(unsigned bit=0;bit<512;bit++) {
        bad=q;((unsigned char*)&bad)[bit/8]^=1U<<(bit%8);
        if(!native_pio_admit64(&bad)) {
            memcpy(saved,s,64);unsigned old=ports;
            CHECK(native_pio_apply64(s,&bad,root,1,3)==-22);
            CHECK(!memcmp(saved,s,64) && ports==old);
        }
    }
    for(unsigned witness=0;witness<3;witness++) CHECK(native_pio_apply64(s,&q,root,10,witness)==-13);
    CHECK(native_pio_apply64(s,&q,root|1,10,3)==-13);
    CHECK(ports==0 && native_pio_apply64(s,&q,root,10,3)==0);
    CHECK(s[0]==owner && s[1]==~owner && !s[2] && ports==1 && last_port==0x3f6 && last_value==6);
    CHECK(native_pio_apply64(s,&q,root,10,3)==-13);
    q.operation=3;q.port=0x3f6;q.value=2;
    CHECK(native_pio_apply64(s,&q,owner,10,0)==-13 && ports==1 && s[5]==0);
    CHECK(native_pio_apply64(s,&q,owner,11,0)==0 && ports==2);
    q.port=0x1f7;
    for(unsigned cmd=0;cmd<256;cmd++) {
        q.value=cmd;CHECK(native_pio_admit64(&q)==(cmd==0xec || cmd==0x20));
    }
    q.value=0x30;unsigned old=ports;memcpy(saved,s,64);
    CHECK(native_pio_apply64(s,&q,owner,11,0)==-22 && ports==old && !memcmp(saved,s,64));
    q.operation=2;q.port=0x1f7;q.value=0;
    CHECK(native_pio_apply64(s,&q,owner+(1ULL<<32),11,0)==-13);
    for(unsigned n=1;n<64;n++) CHECK(native_pio_apply64(s,&q,owner,11,0)==0x40);
    CHECK(native_pio_apply64(s,&q,owner,11,0)==-11 && s[2]==1 && last_value==6);
    CHECK(native_pio_apply64(s,&q,owner,1000,0)==-13);
    q=(reist_native_pio_request){1,64,1,0,owner+(1ULL<<32),0,0,0,0,0,0,0};
    CHECK(native_pio_apply64(s,&q,root,1000,2)==-13);
    CHECK(native_pio_apply64(s,&q,root,1000,3)==0);
    q.operation=4;q.port=0x1f0;q.count=16;uint16_t output[18];
    for(unsigned n=0;n<18;n++) output[n]=0xaaaa;
    q.data=(uintptr_t)&output[1];
    CHECK(native_pio_apply64(s,&q,q.owner,1001,0)==0);
    CHECK(output[0]==0xaaaa && output[17]==0xaaaa);
    for(unsigned n=0;n<16;n++) CHECK(output[n+1]==n);
    q.count=17;CHECK(native_pio_apply64(s,&q,q.owner,1001,0)==-22);
    q.count=16;CHECK(native_pio_apply64(s,&q,q.owner,999,0)==-84 && s[2]==1 && last_value==6);
    for(unsigned n=0;n<64;n++) {
        memcpy(saved,s,64);s[1]^=1ULL<<n;old=ports;
        CHECK(native_pio_apply64(s,&q,q.owner,1002,0)==-84 && ports==old);
        memcpy(s,saved,64);
    }
    return 0;
}
static int profiles(void) {
    reist_task_profile_v1_t p={1,40,{1ULL<<9,1ULL<<49,0},0},before;
    uint64_t parent[4]={7,1ULL<<9,1ULL<<49,16};
    CHECK(sizeof(p)==40 && family_profile_admit64(&p)==1);
    CHECK(family_profile_attenuate64(&p,parent,7)==1);
    CHECK(family_profile_attenuate64(&p,parent,6)==-13);
    for(unsigned bit=0;bit<192;bit++) {
        before=p;p.masks[bit/64]^=1ULL<<(bit%64);
        int64_t r=family_profile_admit64(&p);
        CHECK(r==1 || r==-13);
        if(bit!=9 && bit!=113 && bit!=132) CHECK(family_profile_attenuate64(&p,parent,7)==-13);
        p=before;
    }
    parent[2]=0;CHECK(family_profile_attenuate64(&p,parent,7)==-13);
    p.reserved=1;CHECK(family_profile_admit64(&p)==-22);
    return 0;
}
static void adapter_setup(void) {
    memset(native_pio_state,0,64);native_pio_state[1]=UINT64_MAX;native_pio_state[2]=1;
    memset(native_pio_request,0,64);memset(scheduler_tasks,0,sizeof(scheduler_tasks));
    memset(family_records,0,sizeof(family_records));
    scheduler_tasks[0][0]=2;scheduler_tasks[0][1]=1;
    scheduler_tasks[2][0]=1;scheduler_tasks[2][1]=3;
    family_records[2][1]=1ULL<<32;scheduler_current_slot=0;scheduler_last_tick=10;
    syscall_rdi=29;syscall_rdx=syscall_r10=syscall_r8=syscall_r9=0;
}
static int profile_adapter(void) {
    memset(scheduler_tasks,0,sizeof(scheduler_tasks));
    memset(family_profiles,0,sizeof(family_profiles));
    memset(family_extended_masks,0,sizeof(family_extended_masks));
    for(unsigned slot=0;slot<4;slot++) {
        uint64_t gen=slot+1;scheduler_tasks[slot][0]=9;scheduler_tasks[slot][1]=gen;
        family_extended_masks[slot][0]=slot>=2?1ULL<<49:0;
        CHECK(profile_adapter_test(slot,gen,1ULL<<9,1,0)==1);
        CHECK(family_profiles[slot][0]==gen && family_profiles[slot][1]==1ULL<<9);
        CHECK(family_profiles[slot][2]==(slot==1?0:1ULL<<49) && family_profiles[slot][3]==(slot<2?16:0));
        scheduler_tasks[slot][0]=2;
        for(unsigned call=0;call<192;call++) {
            unsigned granted=call==9 || (call==113 && slot!=1) || (call==132 && slot<2);
            CHECK(profile_adapter_test(slot,gen,1ULL<<9,2,call)==(granted?1:2));
        }
        for(unsigned bit=0;bit<128;bit++) {
            uint64_t expected[4];memcpy(expected,family_profiles[slot],32);
            family_extended_masks[slot][bit/64]^=1ULL<<(bit%64);
            CHECK(profile_adapter_test(slot,gen,1ULL<<9,0,0)==0);
            CHECK(!memcmp(expected,family_profiles[slot],32));
            family_extended_masks[slot][bit/64]^=1ULL<<(bit%64);
        }
        CHECK(profile_adapter_test(slot,gen+1,1ULL<<9,0,0)==0);
        scheduler_tasks[slot][0]=3;
        CHECK(profile_adapter_test(slot,gen,1ULL<<9,3,0)==1);
        CHECK(!family_extended_masks[slot][0] && !family_extended_masks[slot][1]);
        for(unsigned n=0;n<4;n++)CHECK(!family_profiles[slot][n]);
        CHECK(profile_adapter_test(slot,gen,1ULL<<9,3,0)==1);
    }
    CHECK(profile_adapter_test(4,1,1ULL<<9,1,0)==0);
    return 0;
}
static int adapter(void) {
    uint64_t zero[8]={0},saved[8];unsigned old;
    reist_native_pio_request q={1,64,1,0,0x300000002ULL,0,0,0,0,0,0,0};
    adapter_setup();syscall_rsi=1;old=ports;
    CHECK(pio_adapter_test(0)==-14 && !host_faulted && ports==old);
    syscall_rsi=(uintptr_t)&q;
    CHECK(pio_adapter_test(0)==0 && !host_faulted && !memcmp(native_pio_request,zero,64));
    CHECK(native_pio_state[0]==q.owner && !native_pio_state[2]);
    q.operation=4;q.port=0x1f0;q.count=16;q.data=1;
    old=ports;memcpy(saved,native_pio_state,64);
    CHECK(pio_adapter_test(0)==-22 && ports==old && !memcmp(saved,native_pio_state,64));
    q.data=0x100500000ULL;
    CHECK(pio_adapter_test(0)==-14 && ports==old && !memcmp(saved,native_pio_state,64));
    CHECK(!memcmp(native_pio_request,zero,64));
    uint16_t output[16];host_output=q.data=(uintptr_t)output;
    CHECK(pio_adapter_test(0)==-13 && ports==old); /* Root has no driver data authority. */
    scheduler_current_slot=2;scheduler_last_tick=11;
    CHECK(pio_adapter_test(0)==0 && !host_faulted && ports==old+16);
    old=ports;CHECK(pio_adapter_test(1)==0 && native_pio_state[2]==1 && ports==old+1 && last_value==6);
    CHECK(pio_adapter_test(1)==0 && native_pio_state[2]==1 && ports==old+1); /* Idempotent physical revoke. */
    q=(reist_native_pio_request){1,64,5,0,0x300000002ULL,0,0,0,0,0,0,0};
    scheduler_current_slot=0;memcpy(saved,native_pio_state,64);old=ports;
    CHECK(pio_adapter_test(0)==0 && !host_faulted && ports==old && !memcmp(saved,native_pio_state,64));
    scheduler_current_slot=2;
    /* A replacement may terminate before binding: the prior fenced generation
     * is legitimate retained state, not permission to touch or repair it. */
    scheduler_tasks[2][1]=4;old=ports;memcpy(saved,native_pio_state,64);
    CHECK(pio_adapter_test(1)==0 && !host_faulted && ports==old && !memcmp(saved,native_pio_state,64));
    native_pio_state[2]=0;memcpy(saved,native_pio_state,64);
    CHECK(pio_adapter_test(1)==-84 && host_faulted && ports==old+1 && !memcmp(saved,native_pio_state,64));
    native_pio_state[2]=1;scheduler_tasks[2][1]=2;old=ports;memcpy(saved,native_pio_state,64);
    CHECK(pio_adapter_test(1)==-84 && host_faulted && ports==old+1 && !memcmp(saved,native_pio_state,64));
    scheduler_tasks[2][0]=0;CHECK(pio_adapter_test(2)==0 && native_pio_state[0]==0 && native_pio_state[1]==UINT64_MAX && native_pio_state[2]==1);
    /* Corruption must never be repaired by terminal or final cleanup. */
    for(unsigned op=1;op<=2;op++) for(unsigned field=0;field<8;field++) {
        adapter_setup();scheduler_tasks[2][0]=0;
        if(field==0) native_pio_state[0]=1;
        if(field==1) native_pio_state[1]=0;
        if(field==2) native_pio_state[2]=2;
        if(field==3) native_pio_state[3]=1;
        if(field==4) native_pio_state[4]=1ULL<<60;
        if(field==5) native_pio_state[5]=65;
        if(field==6) native_pio_state[6]=1;
        if(field==7) native_pio_state[7]=1;
        memcpy(saved,native_pio_state,64);old=ports;
        CHECK(pio_adapter_test(op)==-84 && host_faulted && !memcmp(saved,native_pio_state,64));
        CHECK(ports==old+1 && last_port==0x3f6 && last_value==6);
    }
    return 0;
}
typedef struct {unsigned calls,fail,words,identify,status,sleeps;uint64_t now;} Model;
static int64_t port(void *v,reist_native_pio_request *q) {
    Model *m=v;if(++m->calls==m->fail) return -5;
    if(q->operation==REIST_PIO_WRITE8 && q->port==0x1f7) {m->identify=q->value==0xec;m->words=0;}
    if(q->operation==REIST_PIO_READ8) return m->status?m->status:(m->words<256?0x48:0x40);
    if(q->operation==REIST_PIO_READ16) {
        uint16_t *out=(void*)(uintptr_t)q->data;
        for(unsigned n=0;n<q->count;n++,m->words++)
            out[n]=m->identify?(m->words==49?512:m->words==60?128:0):(uint16_t)(m->words^0xa55a);
    }
    return 0;
}
static uint64_t now(void *v) {return ((Model*)v)->now;}
static int delay(void *v,unsigned ms) {Model *m=v;m->now+=ms;m->sleeps++;return 0;}
static int driver(void) {
    const uint64_t owner=0x300000002ULL;Model m={0};reist_pio_ops o={&m,port,now,delay};
    uint32_t capacity=0xdeadbeef;CHECK(reist_pio_identify(&o,owner,&capacity)==0 && capacity==128);
    unsigned count=m.calls;
    for(unsigned n=1;n<=count;n++) {
        m=(Model){.fail=n};capacity=0xdeadbeef;
        CHECK(reist_pio_identify(&o,owner,&capacity)==-5 && capacity==0xdeadbeef);
    }
    unsigned char out[512],before[512];m=(Model){0};
    CHECK(reist_pio_read(&o,owner,128,0,out)==0);
    for(unsigned n=0;n<256;n++) CHECK((out[2*n]|((unsigned)out[2*n+1]<<8))==(n^0xa55a));
    count=m.calls;memset(before,0x5a,512);
    for(unsigned n=1;n<=count;n++) {
        m=(Model){.fail=n};memcpy(out,before,512);
        CHECK(reist_pio_read(&o,owner,128,0,out)==-5 && !memcmp(out,before,512));
    }
    m=(Model){.status=255};CHECK(reist_pio_read(&o,owner,128,0,out)==-19);
    m=(Model){.status=128};CHECK(reist_pio_read(&o,owner,128,0,out)==-110 && m.sleeps==20 && m.calls<64);
    m=(Model){0};CHECK(reist_pio_read(&o,owner,128,128,out)==-22 && !m.calls);
    return 0;
}
int main(void) {CHECK(!core());CHECK(!profiles());CHECK(!driver());CHECK(!adapter());CHECK(!profile_adapter());puts("NATIVE_PIO_HOST_OK");return 0;}
