#include "arch/x86_64/ipc/native_ipc.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "arch/x86_64/ipc/native_ipc.c"
#undef assert
#define assert(x) do { if(!(x)) { fprintf(stderr,"check failed line%d: %s\n",__LINE__,#x);exit(1); } } while(0)

static int expected_fault;
void reist_native_ipc_fault(void) {
    if(expected_fault) { puts("NATIVE_IPC_FAULT_CLOSED_OK");exit(0); }
    fputs("unexpected native integrity fault\n",stderr);exit(2);
}
static native_ipc_request_t r;
static unsigned gen[4]={1,2,3,4};
static void call(unsigned op,unsigned slot,unsigned now) {
    assert(reist_native_ipc(op,slot,gen[slot],now,&r)==1);
}
static void request(unsigned slot,unsigned now,unsigned nr,unsigned h,unsigned arg,unsigned timeout) {
    memset(&r,0,sizeof(r));r.number=nr;r.a0=h;r.a1=arg;r.a2=timeout;
    r.message.version=1;r.message.struct_size=140;r.message.length=4;
    r.message.payload[0]=(unsigned char)arg;
    call(NATIVE_IPC_REQUEST,slot,now);
}
int main(int argc,char **argv) {
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_BIND,s,0);
    if(argc==2) {
        expected_fault=1;
        if(!strcmp(argv[1],"busy")) retired_guard.publication_lock=1;
        else if(!strcmp(argv[1],"dual")) {retired_guard.primary.crc32^=3;retired_guard.shadow.crc32^=3;}
        else if(!strcmp(argv[1],"raw")) clients[0].ipc_capabilities[0].rights=4;
        else if(!strcmp(argv[1],"bootstrap")) initialized=0;
        else if(!strcmp(argv[1],"pending")) pending[0].state=1;
        else if(!strcmp(argv[1],"blocking")) {
            wait_queue_t q={0};spinlock_t l={0};
            wait_queue_block_until_spinlocked(&q,0,1,&l,0);
        } else return 3;
        call(NATIVE_IPC_PUMP,0,0);
        return 4;
    }
    /* Correctable guards use the unchanged real primitive, then compare the
     * recovered snapshot with live authority before continuing. */
    retired_guard.primary.words[4]^=1;
    call(NATIVE_IPC_PUMP,0,0);
    assert(retired_guard.primary.words[4]==0);
    request(0,0,49,0,0,0);assert(r.result==0);unsigned h=r.handle;
    request(2,0,49,0,0,0);assert(r.result==0);unsigned other=r.handle;
    request(0,0,55,h,2,3);assert(r.result==0);
    request(2,0,55,other,4,3);assert(r.result==0);
    /* Keep common v1 validation precedence, including its distinct oversized
     * send/receive errno; do not invent a second message validator. */
    for(unsigned number=50;number<=54;number++) {
        if(number==52) continue;
        memset(&r,0,sizeof(r));r.number=number;r.a0=h;
        r.message.version=1;r.message.struct_size=140;r.message.length=129;
        call(NATIVE_IPC_REQUEST,0,0);
        assert(r.result==((number==50 || number==53)?-90:-22));
    }
    request(1,0,55,h,3,4);assert(r.result==-22);
    request(3,0,53,h,1,0);assert(r.result==-9);
    for(unsigned i=0;i<4;i++){request(0,0,53,h,10+i,0);assert(r.result==0);}
    request(0,0,53,h,99,0);assert(r.result==-11);
    request(0,0,53,h,14,50);assert(r.result==NATIVE_IPC_PENDING && r.deadline==5);
    request(1,1,54,h,0,0);assert(r.result==0 && r.message.payload[0]==10 && r.ready==1);
    call(NATIVE_IPC_TAKE,0,1);assert(r.result==0);
    for(unsigned i=11;i<=14;i++){request(1,1,54,h,0,0);assert(r.result==0 && r.message.payload[0]==i);}
    /* A clock notification must not poll message queues. Model a trusted
     * event that has queued a message but has not yet issued its event turn. */
    request(1,1,54,h,0,100);assert(r.result==NATIVE_IPC_PENDING);
    ipc_message_t ingress={1,140,4,{55}};
    assert(ipc_send_timeout(&clients[0],h,&ingress,0)==0);
    call(NATIVE_IPC_PUMP,0,1);assert(r.ready==0);
    request(2,1,49,0,0,0);assert(r.result==0 && r.ready==2);
    call(NATIVE_IPC_TAKE,1,1);assert(r.result==0 && r.message.payload[0]==55);
    request(1,1,54,h,0,20);assert(r.result==NATIVE_IPC_PENDING && r.deadline==3);
    call(NATIVE_IPC_PUMP,0,2);assert(r.ready==0);
    call(NATIVE_IPC_PUMP,0,3);assert(r.ready==2);
    call(NATIVE_IPC_TAKE,1,3);assert(r.result==-110);
    request(1,3,54,h,0,100);assert(r.result==NATIVE_IPC_PENDING);
    call(NATIVE_IPC_REAP,0,3);assert(r.ready==2);
    call(NATIVE_IPC_TAKE,1,3);assert(r.result==-32);
    request(1,3,54,h,0,0);assert(r.result==-9);
    request(2,3,53,other,77,0);assert(r.result==0);
    request(3,3,54,other,0,0);assert(r.result==0 && r.message.payload[0]==77);
    for(unsigned s=1;s<4;s++) call(NATIVE_IPC_REAP,s,3);
    call(NATIVE_IPC_END,0,3);
    for(unsigned s=0;s<4;s++){gen[s]+=4;call(NATIVE_IPC_BIND,s,0);}
    request(0,0,49,0,0,0);assert(r.result==0 && r.handle!=h);
    request(0,0,52,h,0,0);assert(r.result==-9);
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_REAP,s,0);
    call(NATIVE_IPC_END,0,0);
    /* Pool exhaustion and rollback:8 owner capabilities,16 endpoints, no
     * partial capability publication on rejection. Exact generation survives
     * repeated lifecycle cleanup and no polling continuation is invoked. */
    for(unsigned s=0;s<4;s++){gen[s]+=4;call(NATIVE_IPC_BIND,s,0);}
    unsigned handles[16];
    for(unsigned i=0;i<16;i++) {request(i/8,0,49,0,0,0);assert(r.result==0);handles[i]=r.handle;}
    request(0,0,49,0,0,0);assert(r.result==-28);
    request(2,0,49,0,0,0);assert(r.result==-28);
    request(0,0,52,handles[0],0,0);assert(r.result==0);
    request(2,0,49,0,0,0);assert(r.result==0 && r.handle!=handles[0]);
    request(0,0,52,handles[0],0,0);assert(r.result==-9);
    request(2,0,55,r.handle,gen[3],4);assert(r.result==-22);
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_REAP,s,0);
    call(NATIVE_IPC_END,0,0);
    puts("NATIVE_IPC_HOST_OK");
}
