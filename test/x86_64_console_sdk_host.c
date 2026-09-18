#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../userspace/sdk/include/reist/x86_64/syscall.h"
static uint64_t clock_value;static unsigned calls,sleeps,io_calls,mode;
static int64_t call0(uint64_t n) { calls++;if(n!=42)return -22;
    if(mode==6 && calls>2)return 1;
    if(mode==7)return -5;
    return (int64_t)clock_value;
}
static int64_t call1(uint64_t n,uint64_t pause) {
    calls++;sleeps++;if(n!=41 || !pause || pause>10)return -22;
    if(mode==4)return -5;
    if(mode==8)return 1;
    if(mode!=5)clock_value+=pause;
    return 0;
}
static int64_t call3(uint64_t n,uint64_t fd,uint64_t ptr,uint64_t count) {
    calls++;io_calls++;
    if((n!=15 && n!=20) || fd!=(n==20) || !ptr || !count || count>64)return -22;
    if(mode==1 || mode==4 || mode==5 || mode==6 || mode==8)return -11;
    if(mode==2 && io_calls==2)return -32;
    if(mode==3)return (int64_t)count+1;
    if(mode==9)return 0;
    unsigned take=count>17?17:(unsigned)count;
    if(n==15)memset((void *)(uintptr_t)ptr,0x6b,take);
    return take;
}
#define reist_x64_syscall0 call0
#define reist_x64_syscall1 call1
#define reist_x64_syscall3 call3
#include "../userspace/sdk/lib/x86_64/console.c"
#define CHECK(c) do { if(!(c)) {printf("line %d\n",__LINE__);return 1;} } while(0)
static void reset(unsigned test) {mode=test;clock_value=100;calls=sleeps=io_calls=0;}
int main(void) {
    unsigned char buffer[4096];uint32_t done;
    for(unsigned write=0;write<2;write++)for(unsigned test=0;test<10;test++) {
        reset(test);memset(buffer,0xa5,sizeof buffer);done=99;
        int result=write?reist_x64_console_write(buffer,64,100,&done):reist_x64_console_read(buffer,64,100,&done);
        int expected=!test?0:test==1 || test==5?-110:test==2?-32:-5;
        CHECK(result==expected && io_calls<=128 && sleeps<=128);
        CHECK(done==(!test?64:test==2?17:test==7?99:0));
        if(test==5)CHECK(io_calls==128 && sleeps==128);
        if(!test)CHECK(io_calls==4 && sleeps==3);
        if(test==1)CHECK(clock_value==200 && sleeps==10);
        if(write || (test && test!=2))for(unsigned n=0;n<4096;n++)CHECK(buffer[n]==0xa5);
    }
    for(unsigned test=0;test<8;test++) {
        reset(0);done=99;int result=0;
        if(test==0)result=reist_x64_console_read(0,1,100,&done);
        if(test==1)result=reist_x64_console_write(buffer,4097,100,&done);
        if(test==2)result=reist_x64_console_read(buffer,1,0,&done);
        if(test==3)result=reist_x64_console_read(buffer,1,1001,&done);
        if(test==4)result=reist_x64_console_read(buffer,1,100,0);
        if(test==5)result=reist_x64_console_read((void *)UINTPTR_MAX,1,100,&done);
        if(test==6)result=reist_x64_console_read(buffer,1,100,(void *)UINTPTR_MAX);
        if(test==7)result=reist_x64_console_write(&done,4,100,&done);
        CHECK(result==-22 && done==99 && !calls);
    }
    reset(0);done=99;CHECK(!reist_x64_console_read(0,0,1,&done) && !done && !calls);
    reset(0);CHECK(!reist_x64_console_read(buffer,1,1,&done) && done==1 && !sleeps);
    puts("CONSOLE_SDK_OK actual_deadlines_partial_clock_capacity_sleep_errors=1");return 0;
}
