#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { printf("failure line %d\n",__LINE__);return 1;} } while(0)
extern uint64_t __attribute__((sysv_abi)) boot_program_admit64(const void *,uint64_t);
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const void *);
extern int64_t __attribute__((sysv_abi)) reist_x64_startup_stack(const void *,uint64_t);
static _Alignas(16) unsigned char record[36896],saved[36896],destination[4096];
static void put(unsigned n,uint64_t x){memcpy(record+n,&x,8);}
int main(void) {
    memcpy(record,"RNPGv1\0\0",8);put(8,((uint64_t)36896<<32)|1);
    put(16,0x400010);record[24]=5;record[28]=6;
    put(32800,2);put(32808,0x1048);put(32816,0x1050);
    memcpy(record+32872,"one.prg",8);memcpy(record+32880,"arg",4);
    memcpy(saved,record,sizeof record);
    CHECK(boot_program_admit64(record,sizeof record)==1);
    CHECK(!boot_program_admit64(0,sizeof record));CHECK(!boot_program_admit64(record+1,sizeof record));
    for(unsigned n=0;n<36896;n++)if(n!=36896) { /* exact size is mandatory */
        CHECK(!boot_program_admit64(record,n));
    }
    for(unsigned n=0;n<16;n++) {record[n]^=128;CHECK(!boot_program_admit64(record,sizeof record));memcpy(record,saved,sizeof record);}
    const uint64_t bad_entry[]={0,0x3fffff,0x401000,0x404000,0x408000,UINT64_MAX};
    for(unsigned n=0;n<sizeof bad_entry/sizeof *bad_entry;n++) {
        put(16,bad_entry[n]);CHECK(!boot_program_admit64(record,sizeof record));memcpy(record,saved,sizeof record);
    }
    for(unsigned page=0;page<8;page++)for(unsigned flag=0;flag<256;flag++) {
        record[24+page]=(unsigned char)flag;
        int expected=(flag==0||flag==4||flag==5||flag==6) && (page!=0||flag==5);
        CHECK(boot_program_admit64(record,sizeof record)==(uint64_t)expected);
        memcpy(record,saved,sizeof record);
    }
    for(unsigned n=0;n<8;n++) {
        put(32800+n*8,UINT64_MAX);CHECK(!boot_program_admit64(record,sizeof record));memcpy(record,saved,sizeof record);
        if(n==2)break; /* argc and both used pointers */
    }
    memset(record+32872,'x',128);CHECK(!boot_program_admit64(record,sizeof record));memcpy(record,saved,sizeof record);
    uint64_t stack[7]={(uintptr_t)(record+32800),(uintptr_t)destination,0x1000,0x409000,0x1008,2,0};
    int64_t rsp=reist_x64_startup_stack(stack,1);CHECK(rsp>0 && !(rsp&15));
    uint64_t *v=(uint64_t *)(destination+(uint64_t)rsp-0x408000);
    CHECK(v[0]==2 && v[3]==0 && v[4]==0 && v[5]==0x52534901 && v[6]==0 && v[7]==0 && v[8]==0);
    CHECK(!strcmp((char*)destination+v[1]-0x408000,"one.prg"));
    CHECK(!strcmp((char*)destination+v[2]-0x408000,"arg"));
    CHECK(!memcmp(record,saved,sizeof record));
    _Alignas(16) uint64_t plan[18]={((uint64_t)144<<32)|2,4};
    for(unsigned n=0;n<4;n++){plan[2+n*4]=n;plan[3+n*4]=1<<9;plan[4+n*4]=32;plan[5+n*4]=n+3;}
    CHECK(process_run_admit64(plan)==1);
    for(unsigned n=0;n<4;n++)for(unsigned id=0;id<9;id++) {
        plan[5+n*4]=id;CHECK(process_run_admit64(plan)==(uint64_t)(id>=3&&id<=6));plan[5+n*4]=n+3;
    }
    plan[0]=((uint64_t)144<<32)|1;CHECK(!process_run_admit64(plan));
    for(unsigned n=0;n<4;n++)plan[5+n*4]=0;
    CHECK(process_run_admit64(plan)==1);
    puts("BOOT_PROGRAMS_HOST_OK");return 0;
}
