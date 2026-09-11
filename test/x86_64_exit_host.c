#include "../arch/x86_64/proc/terminal_status.h"
#include <stdio.h>
#define CHECK(x) do { if(!(x)) { printf("EXIT_STATUS_FAIL line=%d\n",__LINE__);return 1; } } while(0)
int main(void) {
    const uint64_t mask=(1ULL<<0)|(1ULL<<1)|(1ULL<<3)|(1ULL<<4)|(1ULL<<5)|
        (1ULL<<6)|(1ULL<<13)|(1ULL<<14)|(1ULL<<16)|(1ULL<<17)|(1ULL<<19);
    for(uint64_t value=0;value<1024;value++) {
        CHECK(reist_x64_terminal_status(1,value)==(int64_t)value);
        int valid=(value>=256 && value<=258) ||
            (value>=128 && value<160 && ((mask>>(value-128))&1));
        CHECK(reist_x64_terminal_status(0,value)==(valid?(int64_t)value:-22));
    }
    const uint64_t edges[]={0x7fffffff,0x80000000,0xffffffff,0x100000000,
        0x10000004d,0xffffffff0000004d,UINT64_MAX};
    for(unsigned i=0;i<sizeof edges/sizeof *edges;i++) {
        CHECK(reist_x64_terminal_status(1,edges[i])==(edges[i]<=UINT32_MAX?(int64_t)edges[i]:-22));
        CHECK(reist_x64_terminal_status(0,edges[i])==-22);
        CHECK(reist_x64_terminal_status(2,edges[i])==-22);
        CHECK(reist_x64_terminal_status(UINT64_MAX,edges[i])==-22);
    }
    CHECK(reist_x64_terminal_status(2,0)==-22);
    puts("X86_64_EXIT_STATUS_HOST_OK kinds=2 boundary=32bits");
    return 0;
}
