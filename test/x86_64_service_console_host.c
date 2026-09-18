#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const void *);
extern int64_t __attribute__((sysv_abi)) family_profile_admit64(const void *);
#define CHECK(c) do { if(!(c)) { printf("line %d\n",__LINE__);return 1; } } while(0)
typedef struct { uint32_t version,size,count,reserved; uint64_t tasks[8][4],periods[8]; } Plan;
int main(void) {
    const uint64_t base=(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42);
    Plan original={5,336,8,0,{{0}},{100,100,0,0,0,0,0,0}};
    for(unsigned i=0;i<8;i++) {
        original.tasks[i][0]=i<2;original.tasks[i][1]=base;
        original.tasks[i][2]=32;original.tasks[i][3]=i<2?i+3:i+5;
    }
    CHECK(process_run_admit64(&original)==1);
    for(unsigned rights=0;rights<4;rights++) for(unsigned slot=0;slot<8;slot++) {
        Plan p=original;
        uint64_t mask=((rights&1)?1ULL<<15:0)|((rights&2)?1ULL<<20:0);
        p.tasks[slot][1]|=mask;Plan before=p;
        CHECK(process_run_admit64(&p)==(!mask || !slot));
        CHECK(!memcmp(&p,&before,sizeof p));
    }
    for(unsigned version=1;version<=5;version++) {
        Plan p=original;p.version=version;p.size=version==5?336:version==4?272:144;p.count=version>=4?8:4;
        for(unsigned i=0;i<8;i++) {
            if(i>=p.count)memset(p.tasks[i],0,sizeof p.tasks[i]);
            else if(version<=2) {p.tasks[i][0]=0;p.tasks[i][3]=version==1?0:i+3;}
        }
        p.tasks[0][1]|=1ULL<<15;
        CHECK(process_run_admit64(&p)==(version==5));
    }
    for(unsigned i=0;i<8;i++) {
        Plan p=original;p.tasks[0][1]|=1ULL<<20;p.periods[i]=1;
        CHECK(!process_run_admit64(&p));
    }
    for(unsigned bit=0;bit<64;bit++) {
        Plan p=original;p.tasks[0][1]|=1ULL<<bit;
        uint64_t allowed=base|(1ULL<<15)|(1ULL<<20);
        CHECK(process_run_admit64(&p)==((allowed>>bit)&1));
    }
    CHECK(!process_run_admit64(0));
    uint64_t profile[5]={1ULL|(40ULL<<32),base,0,0,0};
    CHECK(family_profile_admit64(profile)==1);
    for(unsigned rights=1;rights<4;rights++) {
        profile[1]=base|((rights&1)?1ULL<<15:0)|((rights&2)?1ULL<<20:0);
        uint64_t before[5];memcpy(before,profile,sizeof profile);
        CHECK(family_profile_admit64(profile)==-13);
        CHECK(!memcmp(before,profile,sizeof profile));
    }
    puts("SERVICE_CONSOLE_ADMISSION_OK");return 0;
}
