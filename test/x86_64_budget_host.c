#include "../arch/x86_64/proc/cpu_budget.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("BUDGET_FAIL line=%d\n",__LINE__);return 1;}} while(0)
static int denied(struct reist_x64_cpu_budget *b,uint64_t op,uint64_t gen,uint64_t arg) {
    struct reist_x64_cpu_budget old=*b;
    return !reist_x64_budget_apply(b,op,gen,arg) && !memcmp(b,&old,sizeof old);
}
int main(void) {
    struct reist_x64_cpu_budget b={0};
    const unsigned limits[]={1,2,32,65536};
    CHECK(!reist_x64_budget_apply(NULL,0,0,0));
    CHECK(reist_x64_budget_apply(&b,0,0,0)==1);
    CHECK(denied(&b,1,0,32));CHECK(denied(&b,1,UINT64_C(0x100000001),32));
    CHECK(denied(&b,1,1,0));CHECK(denied(&b,1,1,65537));
    for(unsigned j=0;j<4;j++) {
        uint64_t gen=UINT32_MAX-j;
        CHECK(reist_x64_budget_apply(&b,1,gen,limits[j])==1);
        CHECK(denied(&b,1,gen,limits[j]));CHECK(denied(&b,3,gen-1,0));
        for(unsigned i=0;i<limits[j];i++) {
            uint64_t tick=UINT64_C(0x100000000)+i;
            struct reist_x64_cpu_budget old=b;
            CHECK(reist_x64_budget_apply(&b,0,gen,0)==1 && !memcmp(&old,&b,sizeof b));
            CHECK(denied(&b,2,gen-1,tick));
            CHECK(reist_x64_budget_apply(&b,2,gen,tick)==(i+1==limits[j]?2:1));
            CHECK(b.used==i+1 && b.last_tick==tick && b.generation==gen && b.limit==limits[j]);
            CHECK(denied(&b,2,gen,tick));CHECK(denied(&b,2,gen,tick-1));
        }
        CHECK(denied(&b,2,gen,UINT64_MAX));CHECK(denied(&b,3,gen,1));
        CHECK(reist_x64_budget_apply(&b,3,gen,0)==1);
        CHECK(!b.generation && !b.limit && !b.used && !b.last_tick);
    }
    CHECK(reist_x64_budget_apply(&b,1,1,2)==1);
    CHECK(reist_x64_budget_apply(&b,2,1,UINT64_MAX)==1);
    CHECK(denied(&b,2,1,0));CHECK(denied(&b,2,1,UINT64_MAX));
    CHECK(reist_x64_budget_apply(&b,3,1,0)==1);
    for(unsigned field=0;field<4;field++) {
        uint64_t *v=(uint64_t *)&b;v[field]=1;
        CHECK(denied(&b,1,1,32));CHECK(denied(&b,0,0,0));v[field]=0;
    }
    CHECK(reist_x64_budget_apply(&b,1,41,32)==1);
    b.used=33;CHECK(denied(&b,2,41,100));b.used=1;
    CHECK(denied(&b,2,41,100));b.used=0;b.last_tick=1;
    CHECK(denied(&b,2,41,100));
    puts("X86_64_BUDGET_HOST_OK limits=1,2,32,65536 stale=1 monotonic=1 nonmutation=1");return 0;
}
