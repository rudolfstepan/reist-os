#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/pio.h>
#define S __attribute__((sysv_abi))
#define C(x) do{if(!(x)){printf("POOL_PIO_CHECK line=%d expression=%s\n",__LINE__,#x);return 1;}}while(0)
extern int64_t S native_pio_admit64(const reist_native_pio_request *);
extern int64_t S native_pio_state_admit64(const uint64_t *);
extern int64_t S native_pio_apply64(uint64_t *,const reist_native_pio_request *,uint64_t,uint64_t,uint64_t);
extern int64_t S pio_adapter(unsigned);
extern uint64_t native_pio_state[8],native_pio_request[8],scheduler_tasks[8][128],family_records[8][8];
extern uint64_t syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9;
extern uint64_t scheduler_current_slot,scheduler_last_tick,host_fatal;
static unsigned ports,last_port,last_value,words;
uint64_t S native_pio_in8(uint64_t p){ports++;last_port=(unsigned)p;return 0x40;}
uint64_t S native_pio_in16(uint64_t p){ports++;last_port=(unsigned)p;return words++;}
void S native_pio_out8(uint64_t p,uint64_t v){ports++;last_port=(unsigned)p;last_value=(unsigned)v;}
static reist_native_pio_request request(uint64_t owner){
    return (reist_native_pio_request){1,64,1,0,owner,0,0,0,0,0,0,0};
}
static void empty(void){
    memset(native_pio_state,0,64);native_pio_state[1]=UINT64_MAX;native_pio_state[2]=1;
    memset(native_pio_request,0,64);memset(scheduler_tasks,0,sizeof scheduler_tasks);
    memset(family_records,0,sizeof family_records);scheduler_current_slot=0;scheduler_last_tick=10;
    scheduler_tasks[0][0]=2;scheduler_tasks[0][1]=9;syscall_rdi=29;
    syscall_rdx=syscall_r10=syscall_r8=syscall_r9=0;ports=last_port=last_value=words=0;
}
static int admission(void){
    reist_native_pio_request q=request((11ULL<<32)|7);
    C(native_pio_admit64(&q)==1); /* Expected red on accepted four-slot PIO. */
    const uint32_t slots[]={0,1,2,3,4,5,6,7,8,0x7fffffff,UINT32_MAX};
    const uint64_t generations[]={0,1,0x7fffffff,0x80000000,UINT32_MAX};
    for(unsigned i=0;i<sizeof slots/sizeof *slots;i++)for(unsigned j=0;j<sizeof generations/sizeof *generations;j++){
        q=request((generations[j]<<32)|slots[i]);int valid=slots[i]>=2&&slots[i]<8&&generations[j]&&generations[j]<=0x7fffffff;
        uint64_t s[8]={q.owner,~q.owner,1},before[8];memcpy(before,s,64);
        C(native_pio_admit64(&q)==valid);C(native_pio_state_admit64(s)==(valid||!q.owner));C(!memcmp(before,s,64));
        if(!valid){empty();unsigned n=ports;memcpy(before,native_pio_state,64);
            C(native_pio_apply64(native_pio_state,&q,9ULL<<32,10,3)==-22);
            C(ports==n&&!memcmp(before,native_pio_state,64));}
    }
    return 0;
}
static int binding(void){
    for(unsigned old=2;old<8;old++)for(unsigned target=2;target<8;target++){
        empty();uint64_t old_owner=(3ULL<<32)|old,owner=(11ULL<<32)|target;
        reist_native_pio_request q=request(owner);syscall_rsi=(uintptr_t)&q;
        native_pio_state[0]=old_owner;native_pio_state[1]=~old_owner;
        scheduler_tasks[old][0]=1;scheduler_tasks[old][1]=3;
        scheduler_tasks[target][0]=6;scheduler_tasks[target][1]=11;
        family_records[target][1]=9ULL<<32;
        uint64_t before[8];memcpy(before,native_pio_state,64);
        if(old!=target){C(pio_adapter(0)==-13 && ports==0);C(!memcmp(before,native_pio_state,64));scheduler_tasks[old][0]=0;}
        family_records[target][1]^=1;C(pio_adapter(0)==-13 && ports==0);family_records[target][1]^=1;
        scheduler_current_slot=1;scheduler_tasks[1][1]=9;
        C(pio_adapter(0)==-13 && ports==0);scheduler_current_slot=0;
        C(pio_adapter(0)==0 && ports==1 && !host_fatal);
        C(native_pio_state[0]==owner && native_pio_state[1]==~owner && !native_pio_state[2]);
        C(last_port==0x3f6 && last_value==6);
        q.operation=2;q.port=0x1f7;
        scheduler_current_slot=target;C(pio_adapter(0)==0x40 && ports==2);
        q.owner+=(1ULL<<32);C(pio_adapter(0)==-13 && ports==2);q.owner=owner;
        C(pio_adapter(1)==0 && ports==3 && native_pio_state[2]==1 && last_value==6);
        C(pio_adapter(1)==0 && ports==3);C(pio_adapter(0)==-13 && ports==3);
        for(unsigned i=0;i<8;i++)C(!native_pio_request[i]);
    }
    return 0;
}
static int finish_and_corruption(void){
    for(unsigned slot=2;slot<8;slot++)for(unsigned state=0;state<10;state++){
        empty();uint64_t owner=(11ULL<<32)|slot;
        native_pio_state[0]=owner;native_pio_state[1]=~owner;
        scheduler_tasks[slot][0]=state;uint64_t before[8];memcpy(before,native_pio_state,64);
        int64_t r=pio_adapter(2);
        if(state){C(r==-84 && host_fatal && ports==1 && last_port==0x3f6 && last_value==6);C(!memcmp(before,native_pio_state,64));}
        else C(!r && !host_fatal && !ports && !native_pio_state[0] && native_pio_state[1]==UINT64_MAX && native_pio_state[2]==1);
    }
    for(unsigned slot=8;slot<11;slot++){
        empty();native_pio_state[0]=(11ULL<<32)|slot;native_pio_state[1]=~native_pio_state[0];
        uint64_t before[8];memcpy(before,native_pio_state,64);
        C(pio_adapter(2)==-84 && host_fatal && ports==1 && last_value==6);
        C(!memcmp(before,native_pio_state,64));
    }
    for(unsigned slot=2;slot<8;slot++)for(unsigned field=0;field<8;field++){
        empty();native_pio_state[0]=(11ULL<<32)|slot;native_pio_state[1]=~native_pio_state[0];
        const uint64_t invalid[]={0,0,2,11,1ULL<<60,65,11,1};native_pio_state[field]=invalid[field];
        uint64_t before[8];memcpy(before,native_pio_state,64);
        reist_native_pio_request q=request((11ULL<<32)|slot);syscall_rsi=(uintptr_t)&q;
        C(pio_adapter(0)==-84 && host_fatal && ports==1 && last_port==0x3f6 && last_value==6);
        C(!memcmp(before,native_pio_state,64));
    }
    return 0;
}
int main(void){
    if(admission()||binding()||finish_and_corruption())return 1;
    puts("POOL_PIO_KERNEL_OK");return 0;
}
