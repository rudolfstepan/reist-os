#include <stdio.h>
#include <string.h>
#include "../arch/x86_64/proc/ipc_admission.h"
#define CHECK(x) do { if (!(x)) { printf("line %u\n", (unsigned)__LINE__); return 1; } } while (0)
static unsigned char page[8192] __attribute__((aligned(16)));
static struct reist_x64_ipc_request good(void) {
    struct reist_x64_ipc_request r = {50,41,41,7,0x101,0x101,0x101,
        0x100000100ULL,0x100000000ULL,page,0,4096};
    memset(page, 0xa5, sizeof(page));
    uint32_t h[3] = {1,140,128}; memcpy(page+256,h,sizeof(h));
    return r;
}
static int test_case(struct reist_x64_ipc_request r, int64_t expected) {
    unsigned char saved[8192]; memcpy(saved,page,sizeof(page));
    struct reist_x64_ipc_request before = r;
    CHECK(reist_x64_ipc_admit(&r)==expected);
    CHECK(!memcmp(&r,&before,sizeof(r)) && !memcmp(saved,page,sizeof(page)));
    return 0;
}
int main(void) {
    struct reist_x64_ipc_request r;
    for (unsigned length=0;length<=128;++length) {
        r=good();memcpy(page+264,&length,4);CHECK(!test_case(r,1));
        r.operation=53;r.argument2=10;CHECK(!test_case(r,1));
    }
    for (unsigned i=0;i<27;++i) {
        r=good(); int64_t error=-22;
        switch(i) {
        case 0:r.handle=0;error=-9;break;
        case 1:r.handle=0x201;error=-9;break;
        case 2:r.endpoint_handle=0;error=-9;break;
        case 3:r.cap_generation=r.rights=r.cap_handle=0;error=-13;break;
        case 4:r.rights=2;error=-13;break;
        case 5:r.cap_generation=42;error=-4096;break;
        case 6:r.cap_handle=0x201;error=-4096;break;
        case 7:r.rights=8;error=-4096;break;
        case 8:r.generation=1ULL<<32;error=-4096;break;
        case 9:r.address=0;error=-14;break;
        case 10:r.address=~0ULL;error=-14;break;
        case 11:r.address++;error=-14;break;
        case 12:r.address=r.user_base+4096-136;error=-14;break;
        case 13:page[256]=2;break;
        case 14:page[260]=139;break;
        case 15:page[264]=129;break;
        case 16:r.operation=51;break;
        case 17:r.argument2=1;break;
        case 18:r.operation=53;r.argument2=~0ULL;break;
        case 19:r.operation=200;error=-38;break;
        case 20:r.rights=0;error=-4096;break;
        case 21:r.page=0;error=-4096;break;
        case 22:r.user_base++;error=-4096;break;
        case 23:r.user_base=0x800000000000ULL;error=-4096;break;
        case 24:r.operation=52;break;
        case 25:r.operation=55;r.argument2=7;break;
        case 26:r.operation=55;r.argument2=1;r.address=300;break;
        }
        CHECK(!test_case(r,error));
    }
    CHECK(reist_x64_ipc_admit(0)==-4096);
    r=good();r.extent=8192;r.address=r.user_base+4096-8;
    memcpy(page+4096-8,page+256,140);CHECK(!test_case(r,1));
    r.extent=4096;CHECK(!test_case(r,-14));
    r.extent=~0ULL;CHECK(!test_case(r,-4096));
    const unsigned controls[]={51,52,54,55,58};
    for(unsigned i=0;i<5;i++) {
        r=good();r.operation=controls[i];
        if(r.operation==51 || r.operation==54) {
            memset(page+264,0,4);r.argument2=r.operation==54?10:0;
        } else if(r.operation==55) {r.address=301;r.argument2=1;}
        else r.address=0;
        CHECK(!test_case(r,1));
    }
    const uint64_t ops[]={50,51,52,53,54,58,999};
    for(unsigned i=0;i<7;++i)for(unsigned b=0;b<17;++b) {
        uint64_t op=ops[i];int64_t want;
        if(b>15 || (b&8 && b!=8) || (!(b&8) && ((b&2 && !(b&1)) || (b&4 && b&3))))want=-4096;
        else if(b==8)want=op==52?6:-9;
        else if(op==52)want=6;
        else if(op==58)want=7;
        else if(op==50 || op==53)want=b&4?3:!(b&1)?1:(b&2 || op==50)?-11:2;
        else if(op==51 || op==54)want=b&1?4:(b&4 || op==51)?-11:5;
        else want=-38;
        CHECK(reist_x64_ipc_plan(op,b)==want);
    }
    puts("X86_64_IPC_HANDOFF_HOST_OK");return 0;
}
