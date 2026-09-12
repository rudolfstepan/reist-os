#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/image.h>
#include "../arch/x86_64/proc/process_run.h"
#include <reist/x86_64/task.h>
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const void *);
extern uint64_t __attribute__((sysv_abi)) family_request_admit64(const void *);
extern uint64_t __attribute__((sysv_abi)) boot_program_admit64(const void *,uint64_t);
extern uint64_t __attribute__((sysv_abi)) import_range_test(uint64_t);
uint64_t range_base;
unsigned range_count,range_fail;
#define CHECK(x) do { if(!(x)) { printf("FAIL %d\n",__LINE__);return 1; } } while(0)
static _Alignas(16) unsigned char raw[65536],record[36896],before[36896];
static void put(unsigned at,uint64_t v,unsigned count) {
    for(unsigned i=0;i<count;i++) raw[at+i]=(unsigned char)(v>>(8*i));
}
int main(int argc,char **argv) {
    if(argc==3) {
        FILE *f=fopen(argv[1],"rb");CHECK(f);size_t n=fread(raw,1,sizeof(raw),f);CHECK(!ferror(f));fclose(f);
        CHECK(reist_x64_image_prepare(record,raw,n)==0);
        f=fopen(argv[2],"wb");CHECK(f);CHECK(fwrite(record,1,sizeof(record),f)==sizeof(record));CHECK(fclose(f)==0);return 0;
    }
    for(unsigned fail=0;fail<=37;fail++) {
        range_base=0x100000000ULL;range_count=0;range_fail=fail;
        CHECK(import_range_test(range_base)==(fail==37));
        CHECK(range_count==(fail==37?37:fail+1));
    }
    range_count=0;CHECK(import_range_test(UINT64_MAX-36894)==0 && range_count==0);
    struct reist_x64_run_v1 plan={3,144,4,0,{{0}}};
    for(unsigned i=0;i<4;i++) {
        plan.tasks[i].argument=i<2;plan.tasks[i].syscalls=1ULL<<9;
        plan.tasks[i].cpu_samples=32;plan.tasks[i].reserved=i+3;
    }
    CHECK(process_run_admit64(&plan)==1);
    for(unsigned version=1;version<=3;version++) for(unsigned slot=0;slot<4;slot++)
        for(unsigned id=0;id<10;id++) {
            plan.version=version;plan.tasks[slot].reserved=id;
            struct reist_x64_run_v1 saved=plan;
            unsigned good=version>=2 && ((id>=3 && id<=6) || (version==3 && slot>=2 && id==slot+5));
            CHECK(process_run_admit64(&plan)==good && !memcmp(&plan,&saved,sizeof(plan)));
            plan.tasks[slot].reserved=slot+3;
        }
    reist_task_create_v3_t q={3,64,1,0,0,(uintptr_t)record,0,1ULL<<9,32,0x100000000};
    CHECK(family_request_admit64(&q)==1);
    q.operation=2;CHECK(family_request_admit64(&q)==(uint64_t)-22);q.operation=1;
    q.prepared=0;CHECK(family_request_admit64(&q)==(uint64_t)-22);
    memcpy(raw,"\177ELF\2\1\1",7);put(16,2,2);put(18,62,2);put(20,1,4);
    put(24,0x400000,8);put(32,64,8);put(52,64,2);put(54,56,2);put(56,1,2);
    put(64,1,4);put(68,5,4);put(72,4096,8);put(80,0x400000,8);
    put(96,1,8);put(104,4096,8);put(112,4096,8);raw[4096]=0xc3;
    CHECK(reist_x64_image_prepare(record,raw,4097)==0);
    CHECK(boot_program_admit64(record,sizeof(record))==1);
    CHECK(!memcmp(record,"RNPGv1\0\0",8) && record[24]==5 && record[32]==0xc3);
    for(unsigned i=33;i<36896;i++) CHECK(!record[i]);
    memcpy(before,record,sizeof(record));
    const unsigned invalid[]={0,4,5,6,7,8,16,18,20,24,32,48,52,54,56,64,68,72,80,96,111,112};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++) {
        unsigned at=invalid[i];raw[at]^=128;
        CHECK(reist_x64_image_prepare(record,raw,4097)==-22);
        CHECK(!memcmp(record,before,sizeof(record)));raw[at]^=128;
    }
    CHECK(reist_x64_image_prepare(record,raw,63)==-22);
    CHECK(reist_x64_image_prepare(record,raw,65537)==-22);
    CHECK(reist_x64_image_prepare(raw,raw,4097)==-22);
    CHECK(reist_x64_image_prepare(0,raw,4097)==-22);
    CHECK(reist_x64_image_prepare(record,0,4097)==-22);
    puts("IMAGE_IMPORT_HOST_OK");return 0;
}
