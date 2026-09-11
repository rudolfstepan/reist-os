#include "../arch/x86_64/mm/task_frames.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d: %s\n",__LINE__,#x);exit(1);}}while(0)
#define FRAME(i) (UINT64_C(0x04000000)+(i)*4096)
#define CANARY UINT64_C(0xaabbedde01234567)
static struct {uint64_t pre,frames[8],stack,tables[4],cr3,post;} owner;
static struct {uint64_t pre;ReistX64TaskFrames binding;uint64_t post;} descriptor;
static uint64_t foreign[4];
static unsigned live[13],calls,fail_call,free_count,delta_fault,count_calls;
static int order[13],order_count;
int __attribute__((sysv_abi)) physical_frame_free64(uint64_t frame) {
    calls++;
    if(calls==fail_call)return 0;
    unsigned i=(unsigned)((frame-FRAME(0))/4096);
    CHECK(frame>=FRAME(0) && frame<=FRAME(12) && !(frame&4095) && live[i]);
    live[i]=0;free_count++;order[order_count++]=(int)i;return 1;
}
unsigned __attribute__((sysv_abi)) physical_free_frame_count64(void) {
    count_calls++;return free_count+(count_calls==2?delta_fault:0);
}
static uint64_t *record(unsigned i) {
    return i<8?&owner.frames[i]:i==8?&owner.stack:&owner.tables[12-i];
}
static void reset(unsigned mask) {
    memset(&owner,0,sizeof owner);memset(&descriptor,0,sizeof descriptor);
    owner.pre=owner.post=descriptor.pre=descriptor.post=CANARY;
    for(unsigned i=0;i<4;i++)foreign[i]=CANARY+i;
    free_count=100;calls=fail_call=delta_fault=count_calls=0;order_count=0;
    for(unsigned i=0;i<13;i++){live[i]=!!(mask&(1u<<i));if(live[i])*record(i)=FRAME(i);}
    owner.cr3=owner.tables[0];
    descriptor.binding=(ReistX64TaskFrames){owner.frames,&owner.stack,owner.tables,&owner.cr3};
}
static void guards(void) {
    CHECK(owner.pre==CANARY && owner.post==CANARY && descriptor.pre==CANARY && descriptor.post==CANARY);
    for(unsigned i=0;i<4;i++)CHECK(foreign[i]==CANARY+i);
}
static void sparse(void) {
    for(unsigned mask=0;mask<8192;mask++) {
        reset(mask);ReistX64TaskFrames saved=descriptor.binding;
        CHECK(reist_x64_task_frames_release(&descriptor.binding)==1);
        unsigned n=0;for(unsigned i=0;i<13;i++) {
            if(mask&(1u<<i))CHECK(order[n++]==(int)i);
            CHECK(!live[i] && !*record(i));
        }
        CHECK(calls==n && free_count==100+n && !owner.cr3 && count_calls==2);
        CHECK(!memcmp(&saved,&descriptor.binding,sizeof saved));guards();
        calls=count_calls=0;
        CHECK(reist_x64_task_frames_release(&descriptor.binding)==1 && !calls);guards();
    }
}
static void bad_metadata(void) {
    for(unsigned kind=0;kind<11;kind++) {
        reset(8191);
        switch(kind) {
        case 0:owner.frames[7]=owner.frames[0];break;
        case 1:owner.tables[0]=owner.stack;owner.cr3=owner.tables[0];break;
        case 2:owner.stack=0x08000000;break;
        case 3:owner.frames[5]|=1;break;
        case 4:owner.tables[3]=UINT64_MAX;break;
        case 5:owner.cr3+=4096;break;
        case 6:descriptor.binding.stack=owner.frames;break;
        case 7:descriptor.binding.tables=(void*)UINTPTR_MAX;break;
        case 8:descriptor.binding.cr3=NULL;break;
        case 9:descriptor.binding.frames=(void*)&descriptor.binding;break;
        case 10:descriptor.binding.stack=(void*)((char*)&owner.stack+1);break;
        }
        unsigned char saved[sizeof owner];memcpy(saved,&owner,sizeof owner);
        CHECK(!reist_x64_task_frames_release(&descriptor.binding));
        CHECK(!calls && !count_calls && !memcmp(saved,&owner,sizeof owner));guards();
    }
    CHECK(!reist_x64_task_frames_release(NULL));
    CHECK(!reist_x64_task_frames_release((void*)(UINTPTR_MAX-7)));
    CHECK(!reist_x64_task_frames_release((void*)((char*)&descriptor.binding+1)));
    for(unsigned region=0;region<4;region++)for(unsigned kind=0;kind<3;kind++) {
        reset(8191);
        uint64_t **pointers[]={&descriptor.binding.frames,&descriptor.binding.stack,
                              &descriptor.binding.tables,&descriptor.binding.cr3};
        *pointers[region]=kind==0?NULL:kind==1?(void*)(UINTPTR_MAX-7):
                         (void*)((char*)*pointers[region]+1);
        unsigned char saved[sizeof owner];memcpy(saved,&owner,sizeof owner);
        CHECK(!reist_x64_task_frames_release(&descriptor.binding));
        CHECK(!calls && !count_calls && !memcmp(saved,&owner,sizeof owner));guards();
    }
    for(unsigned a=0;a<4;a++)for(unsigned b=0;b<a;b++) {
        reset(8191);
        uint64_t **pointers[]={&descriptor.binding.frames,&descriptor.binding.stack,
                              &descriptor.binding.tables,&descriptor.binding.cr3};
        *pointers[a]=*pointers[b];
        unsigned char saved[sizeof owner];memcpy(saved,&owner,sizeof owner);
        CHECK(!reist_x64_task_frames_release(&descriptor.binding));
        CHECK(!calls && !count_calls && !memcmp(saved,&owner,sizeof owner));guards();
    }
    for(unsigned index=0;index<13;index++)for(unsigned kind=0;kind<4;kind++) {
        reset(8191);
        *record(index)=kind==0?FRAME(index)+1:kind==1?0x08000000:
                       kind==2?(UINT64_MAX-4095):*record((index+1)%13);
        if(index==12)owner.cr3=owner.tables[0];
        unsigned char saved[sizeof owner];memcpy(saved,&owner,sizeof owner);
        CHECK(!reist_x64_task_frames_release(&descriptor.binding));
        CHECK(!calls && !count_calls && !memcmp(saved,&owner,sizeof owner));guards();
    }
}
static void failed_release(void) {
    for(unsigned failed=1;failed<=13;failed++) {
        reset(8191);fail_call=failed;
        CHECK(!reist_x64_task_frames_release(&descriptor.binding));
        CHECK(calls==failed && free_count==100+failed-1 && count_calls==2);
        for(unsigned i=0;i<13;i++)CHECK(live[i]==(i>=failed-1) && *record(i)==(i>=failed-1?FRAME(i):0));
        CHECK(owner.cr3==FRAME(12));guards();
        fail_call=calls=count_calls=0;
        CHECK(reist_x64_task_frames_release(&descriptor.binding)==1);
        CHECK(calls==14-failed && free_count==113 && !owner.cr3);guards();
    }
    reset(8191);delta_fault=1;
    CHECK(!reist_x64_task_frames_release(&descriptor.binding));
    CHECK(calls==13 && !owner.cr3);guards();
    reset(8191);free_count=32769;
    CHECK(!reist_x64_task_frames_release(&descriptor.binding) && !calls);guards();
    reset(8191);free_count=32768;
    CHECK(!reist_x64_task_frames_release(&descriptor.binding) && !calls);guards();
}
int main(void) {
    sparse();bad_metadata();failed_release();
    puts("TASK_FRAMES_HOST_OK layouts=8192 failed_positions=13");return 0;
}
