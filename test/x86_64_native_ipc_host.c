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
static void bulk_request(unsigned slot,unsigned now,unsigned nr,unsigned h,unsigned timeout,unsigned tag) {
    memset(&r,0,sizeof(r));r.number=nr;r.a0=h;r.a2=timeout;
    r.bulk.version=2;r.bulk.struct_size=2060;r.bulk.length=2048;
    for(unsigned i=0;i<2048;i++) r.bulk.payload[i]=(unsigned char)(i*17+tag);
    call(NATIVE_IPC_REQUEST,slot,now);
}
static void bulk_checks(void) {
    request(0,0,49,0,0,0);assert(r.result==0);unsigned h=r.handle;
    request(0,0,55,h,2,3);assert(r.result==0);
    critical_object_t idle_tail[30];
    memcpy(idle_tail,pending_guards[0]+5,sizeof(idle_tail));
    call(NATIVE_IPC_PUMP,0,0);
    assert(!memcmp(idle_tail,pending_guards[0]+5,sizeof(idle_tail)));
    bulk_request(3,0,53,h,0,7);assert(r.result==-9);
    for(unsigned nr=50;nr<=54;nr++) if(nr!=52) {
        memset(&r,0,sizeof(r));r.number=nr;r.a0=h;
        r.bulk.version=2;r.bulk.struct_size=2060;r.bulk.length=2049;
        call(NATIVE_IPC_REQUEST,0,0);
        assert(r.result==((nr==50 || nr==53)?-90:-22));
    }
    bulk_request(0,0,53,h,0,7);assert(r.result==0);
    bulk_request(0,0,53,h,0,8);assert(r.result==-11);
    bulk_request(0,0,50,h,0,8);assert(r.result==NATIVE_IPC_PENDING);
    memset(&r,0xa5,sizeof(r)); /* Caller mutation cannot change pending input. */
    bulk_request(1,1,54,h,0,0);assert(r.result==0 && r.ready==1 && r.copy_size==2060);
    for(unsigned i=0;i<2048;i++) assert(r.bulk.payload[i]==(unsigned char)(i*17+7));
    call(NATIVE_IPC_TAKE,0,1);assert(r.result==0);
    bulk_request(1,1,51,h,0,0);assert(r.result==0);
    for(unsigned i=0;i<2048;i++) assert(r.bulk.payload[i]==(unsigned char)(i*17+8));
    /* Shared two-channel rule: v2 receive prefers v1 FIFO, zero-fills full2060. */
    bulk_request(0,1,53,h,0,9);assert(r.result==0);
    for(unsigned i=0;i<4;i++){request(0,1,53,h,10+i,0);assert(r.result==0);}
    for(unsigned i=0;i<4;i++) {
        bulk_request(1,1,54,h,0,0);assert(r.result==0 && r.copy_size==2060);
        assert(r.message.version==1 && r.message.struct_size==140 && r.message.payload[0]==10+i);
        for(unsigned j=4;j<2048;j++) assert(r.bulk.payload[j]==0);
    }
    bulk_request(1,1,54,h,0,0);assert(r.result==0 && r.bulk.payload[2047]==(unsigned char)(2047*17+9));
    bulk_request(1,1,54,h,20,0);assert(r.result==NATIVE_IPC_PENDING);
    call(NATIVE_IPC_PUMP,0,2);assert(!r.ready);
    call(NATIVE_IPC_PUMP,0,3);assert(r.ready==2);
    call(NATIVE_IPC_TAKE,1,3);assert(r.result==-110 && r.copy_size==2060);
    bulk_request(1,3,54,h,100,0);assert(r.result==NATIVE_IPC_PENDING);
    request(0,3,53,h,66,0);assert(r.result==0 && r.ready==2);
    call(NATIVE_IPC_TAKE,1,3);assert(r.result==0 && r.copy_size==2060 && r.message.version==1);
    for(unsigned j=4;j<2048;j++) assert(r.bulk.payload[j]==0);
    /* Both exact bounds, including an empty v2 message and maximum v1. */
    for(unsigned size=0;size<=128;size+=128) {
        memset(&r,0,sizeof(r));r.number=53;r.a0=h;
        r.message.version=1;r.message.struct_size=140;r.message.length=size;
        memset(r.message.payload,0x77,size);call(NATIVE_IPC_REQUEST,0,3);assert(!r.result);
        bulk_request(1,3,54,h,0,0);assert(!r.result && r.copy_size==2060 && r.message.length==size);
        for(unsigned j=0;j<2048;j++) assert(r.bulk.payload[j]==(j<size?0x77:0));
    }
    memset(&r,0,sizeof(r));r.number=53;r.a0=h;r.bulk.version=2;r.bulk.struct_size=2060;
    call(NATIVE_IPC_REQUEST,0,3);assert(!r.result);
    bulk_request(1,3,54,h,0,0);assert(!r.result && r.bulk.version==2 && !r.bulk.length);
    bulk_request(1,3,54,h,100,0);assert(r.result==NATIVE_IPC_PENDING);
    call(NATIVE_IPC_REAP,0,3);assert(r.ready==2);
    call(NATIVE_IPC_TAKE,1,3);assert(r.result==-32);
    bulk_request(1,3,54,h,0,0);assert(r.result==-9);
    for(unsigned s=1;s<4;s++) call(NATIVE_IPC_REAP,s,3);
    call(NATIVE_IPC_END,0,3);
    for(unsigned s=0;s<4;s++){gen[s]+=4;call(NATIVE_IPC_BIND,s,0);}
    request(0,0,49,0,0,0);assert(r.result==0 && r.handle!=h);
    bulk_request(0,0,53,h,0,0);assert(r.result==-9);
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_REAP,s,0);
    call(NATIVE_IPC_END,0,0);
    puts("NATIVE_BULK_HOST_OK");
}
int main(int argc,char **argv) {
    for(unsigned s=0;s<4;s++) call(NATIVE_IPC_BIND,s,0);
    if(argc==2 && !strcmp(argv[1],"bulk")) {bulk_checks();return 0;}
    if(argc==2) {
        expected_fault=1;
        if(!strcmp(argv[1],"bulk-tail") || !strcmp(argv[1],"bulk-capacity")) {
            request(0,0,49,0,0,0);assert(!r.result);unsigned h=r.handle;
            request(0,0,55,h,2,3);assert(!r.result);
            bulk_request(0,0,54,h,100,0);assert(r.result==NATIVE_IPC_PENDING);
            if(!strcmp(argv[1],"bulk-tail")) pending[0].request.bulk.payload[2047]^=1;
            else pending[0].request.copy_size=UINT64_MAX;
        }
        else if(!strcmp(argv[1],"busy")) retired_guard.publication_lock=1;
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
