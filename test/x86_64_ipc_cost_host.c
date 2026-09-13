/* Actual adapter: primitive counts, semantic transcript and failure witnesses. */
#include "include/kernel/critical_object.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"ipc-cost line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
static unsigned reads,updates,inits,client_updates;
static int counted_init(critical_object_t *,uint32_t,const void *,size_t);
static int counted_update(critical_object_t *,uint32_t,const void *,size_t,critical_object_validator_t);
static critical_read_result_t counted_read(critical_object_t *,uint32_t,void *,size_t,size_t *,critical_object_validator_t);
#define critical_object_init counted_init
#define critical_object_update counted_update
#define critical_object_read counted_read
#include IPC_SOURCE
#undef critical_object_init
#undef critical_object_update
#undef critical_object_read
static int counted_init(critical_object_t *o,uint32_t v,const void *p,size_t n){inits++;return critical_object_init(o,v,p,n);}
static int counted_update(critical_object_t *o,uint32_t v,const void *p,size_t n,critical_object_validator_t f){
    updates++;
    if((uintptr_t)o>=(uintptr_t)client_guards && (uintptr_t)o<(uintptr_t)client_guards+sizeof(client_guards))client_updates++;
    return critical_object_update(o,v,p,n,f);
}
static critical_read_result_t counted_read(critical_object_t *o,uint32_t v,void *p,size_t n,size_t *size,critical_object_validator_t f){reads++;return critical_object_read(o,v,p,n,size,f);}
static jmp_buf trap;
static unsigned armed;
void reist_native_ipc_fault(void){CHECK(armed && !updates && !inits);longjmp(trap,1);}
static native_ipc_request_t r;
static uint32_t generations[4]={1,2,3,4};
static uint64_t digest=1469598103934665603ULL;
static unsigned steps;
static void hash(const void *p,size_t n){const unsigned char *b=p;while(n--){digest^=*b++;digest*=1099511628211ULL;}}
static void call(unsigned op,unsigned slot,unsigned tick,const char *label){
    reads=updates=inits=client_updates=0;
    CHECK(reist_native_ipc(op,slot,generations[slot],steps+tick,&r)==1);
    if(label)printf("COST %s %u %u %u %u\n",label,reads,updates,inits,client_updates);
    hash(&r,sizeof(r));hash(clients,sizeof(clients));hash(pending,sizeof(pending));hash(retired,sizeof(retired));
    steps++;check_all(); /* Every operation must leave a completely valid snapshot. */
}
static void request(unsigned slot,unsigned tick,unsigned nr,unsigned handle,unsigned arg,unsigned ms,unsigned version){
    memset(&r,0,sizeof(r));r.number=nr;r.a0=handle;r.a1=arg;r.a2=ms;
    r.message.version=version;r.message.struct_size=version==2?2060:140;
    r.message.length=version==2?2048:128;
    for(unsigned i=0;i<r.message.length;i++)r.bulk.payload[i]=(unsigned char)(i*17+arg);
    call(NATIVE_IPC_REQUEST,slot,tick,nr==53?"send":nr==54?"receive":nr==55?"delegate":0);
}
static void faults(unsigned slot){
    /* Real entry must find corruption even when that operation would publish
     * nothing. Include every raw byte of active pending records and clients. */
    unsigned char *regions[]={(unsigned char*)&clients[slot],(unsigned char*)&pending[slot],(unsigned char*)retired};
    size_t lengths[]={sizeof(Process),sizeof(Pending),sizeof(retired)};
    for(unsigned region=0;region<3;region++)for(size_t n=0;n<lengths[region];n++){
        unsigned char old=regions[region][n];regions[region][n]^=1;
        armed=1;reads=updates=inits=0;
        if(!setjmp(trap)){(void)reist_native_ipc(NATIVE_IPC_PUMP,slot,generations[slot],current_tick,&r);CHECK(0);}
        entered=0;armed=0;regions[region][n]=old;
    }
    critical_object_t *objects[]={&retired_guard,&client_guards[slot][0],&pending_guards[slot][0],&pending_guards[slot][34]};
    for(unsigned i=0;i<4;i++)for(unsigned kind=0;kind<2;kind++){
        critical_object_t saved=*objects[i];
        if(kind)objects[i]->publication_lock=1;
        else {objects[i]->primary.crc32^=3;objects[i]->shadow.crc32^=3;}
        armed=1;reads=updates=inits=0;
        if(!setjmp(trap)){(void)reist_native_ipc(NATIVE_IPC_PUMP,slot,generations[slot],current_tick,&r);CHECK(0);}
        entered=0;armed=0;*objects[i]=saved;
    }
    for(unsigned i=0;i<4;i++){
        unsigned char before[64],after[64];size_t n=0,m=0;
        CHECK(critical_object_read(objects[i],1,before,64,&n,chunk)>=0);
        objects[i]->primary.words[4]^=1;
        reads=updates=inits=0;
        CHECK(reist_native_ipc(NATIVE_IPC_PUMP,slot,generations[slot],current_tick,&r)==1);
        CHECK(critical_object_read(objects[i],1,after,64,&m,chunk)>=0);
        CHECK(n==m && !memcmp(before,after,n));
    }
    check_all();puts("IPC_COST_FAULT_OK");
}
int main(int argc,char **argv){
    for(unsigned s=0;s<4;s++)call(NATIVE_IPC_BIND,s,0,0);
    call(NATIVE_IPC_PUMP,0,0,"idle");
    call(NATIVE_IPC_TAKE,0,0,"empty-take");CHECK(r.result==NATIVE_IPC_PENDING);
    if(argc==2){
        unsigned s=(unsigned)strtoul(argv[1],0,10);CHECK(s<4);
        request(s,0,49,0,0,0,1);CHECK(!r.result);unsigned h=r.handle;
        request(s,0,54,h,0,100,2);CHECK(r.result==NATIVE_IPC_PENDING);
        faults(s);return 0;
    }
    for(unsigned cycle=0;cycle<4;cycle++){
        unsigned sender=cycle,receiver=(cycle+1)%4;
        for(unsigned version=1;version<=2;version++){
            request(sender,0,49,0,0,0,version);CHECK(!r.result);unsigned h=r.handle;
            request(sender,0,55,h,generations[receiver],3,version);CHECK(!r.result);
            request(receiver,0,54,h,0,100,version);CHECK(r.result==NATIVE_IPC_PENDING);
            call(NATIVE_IPC_PUMP,sender,0,version==1?"wait-v1":"wait-v2");CHECK(!r.ready);
            request(sender,0,99,h,0,0,version);CHECK(r.result==-22 && !r.ready); /* Failed pump transfer still sealed. */
            request(sender,0,53,h,17,0,version);CHECK(!r.result && r.ready==(1ULL<<receiver));
            call(NATIVE_IPC_TAKE,receiver,0,"take");CHECK(!r.result && r.message.payload[0]==17);
            request(receiver,0,54,h,0,10,version);CHECK(r.result==NATIVE_IPC_PENDING);
            call(NATIVE_IPC_PUMP,sender,1,"timeout");CHECK(r.ready==(1ULL<<receiver));
            call(NATIVE_IPC_TAKE,receiver,1,0);CHECK(r.result==-110);
            /* Queue pressure and four-pass sender progress, including EAGAIN. */
            unsigned capacity=version==1?4:1;
            for(unsigned n=0;n<capacity;n++){request(sender,0,53,h,20+n,0,version);CHECK(!r.result);}
            request(sender,0,53,h,44,100,version);CHECK(r.result==NATIVE_IPC_PENDING);
            request(receiver,0,54,h,0,0,version);CHECK(!r.result && r.ready==(1ULL<<sender));
            call(NATIVE_IPC_TAKE,sender,0,0);CHECK(!r.result);
            for(unsigned n=0;n<capacity;n++){request(receiver,0,54,h,0,0,version);CHECK(!r.result);}
            request(receiver,0,54,h,0,100,version);CHECK(r.result==NATIVE_IPC_PENDING);
            request(sender,0,52,h,0,0,version);CHECK(!r.result && r.ready==(1ULL<<receiver));
            call(NATIVE_IPC_TAKE,receiver,0,0);CHECK(r.result==-32);
            request(receiver,0,54,h,0,0,version);CHECK(r.result==-9);
        }
    }
    /* Reap while a peer awaits data; clear pending and generation, then rebind. */
    for(unsigned s=0;s<4;s++){
        unsigned peer=(s+1)%4;
        request(s,0,49,0,0,0,1);CHECK(!r.result);unsigned h=r.handle;
        request(s,0,55,h,generations[peer],3,1);CHECK(!r.result);
        request(peer,0,54,h,0,100,2);CHECK(r.result==NATIVE_IPC_PENDING);
        call(NATIVE_IPC_REAP,s,0,"reap");CHECK(r.ready==(1ULL<<peer));
        call(NATIVE_IPC_TAKE,peer,0,0);CHECK(r.result==-32);
        generations[s]+=4;call(NATIVE_IPC_BIND,s,0,"bind");
        request(s,0,54,h,0,0,1);CHECK(r.result==-9);
    }
    for(unsigned s=0;s<4;s++)call(NATIVE_IPC_REAP,s,0,0);
    call(NATIVE_IPC_END,0,0,"end");
    printf("SEMANTICS %u %016llx\n",steps,(unsigned long long)digest);
    puts("IPC_COST_HOST_OK");return 0;
}
