#include "../arch/x86_64/proc/request_admission.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("REQUEST_FAIL line=%d\n",__LINE__);return 1;}} while(0)
static _Alignas(16) unsigned char page[4096];
static struct reist_x64_request r;
static void init(unsigned op) {
    memset(page,0xa5,sizeof page);memcpy(page+32,"/shell/child",13);
    r=(struct reist_x64_request){op,0,0,0,page,UINT64_C(0x400000000),0,0,0,1};
}
static int check(int64_t expected) {
    struct reist_x64_request before=r;unsigned char bytes[4096];memcpy(bytes,page,4096);
    CHECK(reist_x64_request_admit(&r)==expected);
    CHECK(!memcmp(&r,&before,sizeof r)&&!memcmp(page,bytes,4096));return 0;
}
int main(void) {
    CHECK(reist_x64_request_admit(NULL)==-4096);
    for(unsigned op=15;op<=20;op+=5) {
        init(op);r.arg0=op==15?0:1;r.arg1=UINT64_MAX;
        CHECK(!check(0));r.arg2=1;CHECK(!check(1));
        r.arg2=op==15?2:65;CHECK(!check(-22));
        r.arg2=UINT64_MAX;CHECK(!check(-22));r.arg2=0;
        r.arg0=UINT64_C(0x100000001);CHECK(!check(-9));
        r.arg0=op==15?1:0;CHECK(!check(-9));
    }
    init(20);r.arg0=2;r.arg2=64;CHECK(!check(1));
    init(22);r.arg0=r.arg1=r.arg2=UINT64_MAX;CHECK(!check(1));
    init(24);r.arg0=301;CHECK(!check(-10));r.active_child=r.spawned=1;CHECK(!check(1));
    r.arg0=UINT64_C(0x10000012d);CHECK(!check(-10));r.arg0=301;r.arg2=1;CHECK(!check(-22));
    for(unsigned op=23;op<=30;op+=7) {
        init(op);r.arg0=r.user_base+32;CHECK(!check(1));
        r.endpoint=0;CHECK(!check(-9));r.endpoint=3;CHECK(!check(-11));
        r.endpoint=7;CHECK(!check(-11));r.endpoint=9;CHECK(!check(-11));r.endpoint=1;
        r.active_child=r.spawned=1;CHECK(!check(-11));
        r.active_child=0;r.spawned=r.completed=2;CHECK(!check(-11));
        init(op);r.arg0=0;CHECK(!check(-14));r.arg0=UINT64_MAX;CHECK(!check(-14));
        r.arg0=r.user_base+4095;CHECK(!check(-14));
        r.arg0=r.user_base+32;page[32]='!';CHECK(!check(-2));
        memset(page+32,'A',16);CHECK(!check(-36));
        page[4095]=0;r.arg0=r.user_base+4095;CHECK(!check(-2));
        memcpy(page+33,"/shell/child",13);r.arg0=r.user_base+33;CHECK(!check(1));
        r.arg1=1;CHECK(!check(op==23?-22:1));r.arg1=0;r.arg2=1;CHECK(!check(op==23?-22:1));
    }
    for(unsigned n=0;n<11;n++) {
        init(23);r.arg0=r.user_base+32;
        switch(n) {
        case 0:r.active_child=2;break;
        case 1:r.spawned=3;break;
        case 2:r.completed=1;break;
        case 3:r.active_child=1;break;
        case 4:r.endpoint=2;break;
        case 5:r.endpoint=5;break;
        case 6:r.endpoint=11;break;
        case 7:r.endpoint=16;break;
        case 8:r.page=NULL;break;
        case 9:r.user_base++;break;
        case 10:r.user_base=UINT64_MAX-4095;break;
        }
        CHECK(!check(-4096));
    }
    init(64);CHECK(!check(-38));
    puts("X86_64_REQUEST_HOST_OK nonmutating=1");return 0;
}
