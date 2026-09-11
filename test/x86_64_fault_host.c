#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint32_t __attribute__((sysv_abi)) x86_64_user_fault_status64(const uint64_t *frame);
static int allowed(unsigned v) {
    return v==0 || v==1 || v==3 || v==4 || v==5 || v==6 ||
           v==13 || v==14 || v==16 || v==17 || v==19;
}
int main(void) {
    uint64_t f[22]={0}, before[22];
    for(unsigned v=0;v<34;++v) for(unsigned cpl=0;cpl<4;++cpl) {
        f[15]=v; f[16]=0; f[17]=UINT64_C(0xffff800000001000);
        f[18]=0x30+cpl; f[19]=2; f[20]=UINT64_C(0x8000000000000000);f[21]=0x2b;
        memcpy(before,f,sizeof f);
        uint32_t want=cpl==3 && allowed(v)?128+v:0;
        if(x86_64_user_fault_status64(f)!=want || memcmp(before,f,sizeof f)) return 1;
        f[16]=UINT64_C(1)<<32;
        if(x86_64_user_fault_status64(f)) return 2;
        f[16]=1;
        if(v!=13 && v!=14 && x86_64_user_fault_status64(f)) return 3;
        f[16]=0; f[21]=0x10;
        if(x86_64_user_fault_status64(f)) return 4;
    }
    f[15]=UINT64_MAX;f[18]=0x33;f[21]=0x2b;
    if(x86_64_user_fault_status64(f)) return 5;
    puts("X86_64_FAULT_HOST_OK vectors=34 cpl=4 poisoned_addresses=1 immutable=1");
    return 0;
}
