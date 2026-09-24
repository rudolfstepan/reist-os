#define main legacy_pio_main
#include "x86_64_pool_pio_host.c"
#undef main
#define TAG UINT64_C(0xffffff7f00000080)
static int throughput(void){
    uint64_t owner=(11ULL<<32)|2,root=9ULL<<32,before[8];
    reist_native_pio_request q=request(owner);q.version=3;q.reserved1=128;
    reist_native_pio_request prepared=request(owner),saved=prepared;
    C(reist_x64_pio_throughput_bind_prepare(0,owner)==-22);
    const uint64_t invalid_owners[]={0,1,2,(1ULL<<32)|1,(1ULL<<32)|8,UINT64_C(0x8000000000000002)};
    for(unsigned n=0;n<sizeof invalid_owners/sizeof *invalid_owners;n++){
        C(reist_x64_pio_throughput_bind_prepare(&prepared,invalid_owners[n])==-22);
        C(!memcmp(&prepared,&saved,sizeof prepared));
    }
    C(!reist_x64_pio_throughput_bind_prepare(&prepared,owner));
    C(!memcmp(&prepared,&q,sizeof q));
    C(native_pio_admit64(&q)==1);
    for(unsigned k=0;k<7;k++){
        reist_native_pio_request bad=q;
        if(k==0)bad.version=4;if(k==1)bad.operation=2;
        if(k==2)bad.reserved1=127;if(k==3)bad.reserved1=129;
        if(k==4)bad.reserved2=1;if(k==5)bad.flags=1;if(k==6)bad.port=0x1f7;
        C(!native_pio_admit64(&bad));
    }
    empty();memcpy(before,native_pio_state,64);
    C(native_pio_apply64(native_pio_state,&q,owner,10,3)==-13);
    C(!ports&&!memcmp(before,native_pio_state,64));
    C(native_pio_apply64(native_pio_state,&q,root,10,1)==-13);
    C(!ports&&!memcmp(before,native_pio_state,64));
    C(!native_pio_apply64(native_pio_state,&q,root,10,3));
    C(native_pio_state[7]==TAG && ports==1);
    memcpy(before,native_pio_state,64);
    C(native_pio_apply64(native_pio_state,&q,root,10,3)==-13);
    C(ports==1&&!memcmp(before,native_pio_state,64));
    q=request(owner);q.version=2;q.operation=2;q.port=0x1f7;q.reserved1=200;
    for(unsigned n=0;n<128;n++)C(native_pio_apply64(native_pio_state,&q,owner,10,0)==64);
    C(native_pio_state[5]==128 && ports==129);
    C(native_pio_apply64(native_pio_state,&q,owner,10,0)==-11);
    C(native_pio_state[2]==1&&ports==130&&last_port==0x3f6&&last_value==6);
    C(native_pio_apply64(native_pio_state,&q,owner,10,0)==-13&&ports==130);
    C(native_pio_state_admit64(native_pio_state)==1);
    for(unsigned bit=0;bit<64;bit++){
        native_pio_state[7]=TAG^(UINT64_C(1)<<bit);
        C(!native_pio_state_admit64(native_pio_state));
    }
    native_pio_state[7]=TAG;
    q=request(owner+(1ULL<<32));
    C(!native_pio_apply64(native_pio_state,&q,root,11,3));
    C(native_pio_state[7]==0&&native_pio_state[5]==0); /* Explicit legacy rebind. */
    q.operation=2;q.port=0x1f7;
    for(unsigned n=0;n<64;n++)C(native_pio_apply64(native_pio_state,&q,q.owner,11,0)==64);
    C(native_pio_apply64(native_pio_state,&q,q.owner,11,0)==-11);
    /* Exact100ms window reset and stale owner on the new profile. */
    empty();q=request(owner);q.version=3;q.reserved1=128;
    C(!native_pio_apply64(native_pio_state,&q,root,10,3));
    q.version=1;q.reserved1=0;q.operation=2;q.port=0x1f7;
    for(unsigned n=0;n<128;n++)C(native_pio_apply64(native_pio_state,&q,owner,19,0)==64);
    C(native_pio_apply64(native_pio_state,&q,owner+(1ULL<<32),20,0)==-13);
    C(native_pio_apply64(native_pio_state,&q,owner,20,0)==64&&native_pio_state[5]==1);
    C(native_pio_apply64(native_pio_state,&q,owner,19,0)==-84&&native_pio_state[2]);
    /* Real runtime parent/live-generation adapter and lifecycle scrub. */
    empty();q=request(owner);q.version=3;q.reserved1=128;syscall_rsi=(uintptr_t)&q;
    scheduler_tasks[2][0]=6;scheduler_tasks[2][1]=11;family_records[2][1]=root;
    C(!pio_adapter(0)&&native_pio_state[7]==TAG);
    scheduler_current_slot=2;C(!pio_adapter(1)&&native_pio_state[2]);
    scheduler_tasks[2][0]=0;C(!pio_adapter(2));
    C(!native_pio_state[0]&&native_pio_state[1]==UINT64_MAX&&native_pio_state[2]==1);
    for(unsigned n=3;n<8;n++)C(!native_pio_state[n]);
    return 0;
}
int main(void){C(!legacy_pio_main());C(!throughput());puts("PIO_THROUGHPUT_OK");return 0;}
