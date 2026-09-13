#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "userspace/sdk/lib/x86_64/image.c"
extern int __attribute__((sysv_abi)) boot_program_admit64(const void *,size_t);
static _Alignas(16) unsigned char elf[524288], record[266336], before[266336];
#define CHECK(x) do {if(!(x)){fprintf(stderr,"wide image line %d\n",__LINE__);exit(1);}}while(0)
static void fixture(unsigned page) {
    memset(elf,0,sizeof(elf));
    put(elf,0x00010102464c457fULL,8);put(elf+16,2,2);put(elf+18,62,2);
    put(elf+20,1,4);put(elf+24,0x400000+page*4096,8);put(elf+32,64,8);
    put(elf+52,64,2);put(elf+54,56,2);put(elf+56,1,2);
    put(elf+64,1,4);put(elf+68,5,4);put(elf+72,4096,8);
    put(elf+80,0x400000+page*4096,8);put(elf+96,4096,8);
    put(elf+104,4096,8);put(elf+112,4096,8);
    for(unsigned i=0;i<4096;i++)elf[4096+i]=(unsigned char)(i^page);
}
int main(int argc,char **argv) {
    CHECK(argc==2);
    for(unsigned page=0;page<64;page++) {
        fixture(page);memset(record,0xa5,sizeof(record));memcpy(before,record,sizeof(record));
        int result=reist_x64_image_prepare_v2(record,elf,8192);
        if(page>=7 && page<=15){CHECK(result==-22);CHECK(!memcmp(record,before,sizeof(record)));continue;}
        CHECK(result==0);CHECK(boot_program_admit64(record,sizeof(record))==1);
        CHECK(!memcmp(record+96+page*4096,elf+4096,4096));
        CHECK(get(record+8,4)==2 && get(record+12,4)==sizeof(record));
        char path[1024];int n=snprintf(path,sizeof(path),"%s/page-%u.rnpg",argv[1],page);
        CHECK(n>0 && (size_t)n<sizeof(path));FILE *output=fopen(path,"wb");CHECK(output);
        CHECK(fwrite(record,1,sizeof(record),output)==sizeof(record));CHECK(fclose(output)==0);
        for(unsigned i=0;i<64;i++)CHECK(record[24+i]==(i==page?5:(i>=9 && i<=15?6:0)));
        memcpy(before,record,sizeof(record));
        const unsigned offsets[]={0,8,12,24+7,24+8,24+9,24+15,88,95,96+7*4096,96+8*4096,96+9*4096,96+15*4096};
        for(unsigned i=0;i<sizeof(offsets)/sizeof(*offsets);i++) {
            record[offsets[i]]^=1;CHECK(boot_program_admit64(record,sizeof(record))==0);
            CHECK(record[offsets[i]]==(unsigned char)(before[offsets[i]]^1));record[offsets[i]]^=1;
        }
        CHECK(!memcmp(record,before,sizeof(record)));
        CHECK(!boot_program_admit64(record,sizeof(record)-1));
        CHECK(!boot_program_admit64(record+1,sizeof(record)));
    }
    fixture(16);memset(record,0xa5,sizeof(record));memcpy(before,record,sizeof(record));
    CHECK(reist_x64_image_prepare(record,elf,8192)==-22);
    CHECK(reist_x64_image_prepare_v2(record,elf,524289)==-22);
    CHECK(reist_x64_image_prepare_v2(elf,elf,8192)==-22);
    CHECK(!memcmp(record,before,sizeof(record)));
    fixture(0);CHECK(reist_x64_image_prepare(record,elf,8192)==0);
    CHECK(boot_program_admit64(record,36896)==1);
    puts("wide_image_OK slots=64 legacy=1 reserved=zero");return 0;
}
