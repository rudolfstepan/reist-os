#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../userspace/sdk/include/reist/x86_64/task.h"
#define CHECK(x) do { if(!(x)) { printf("FAIL line=%d\n",__LINE__); return 1; } } while(0)
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const void *);
extern int64_t __attribute__((sysv_abi)) family_startup_admit64(const void *);
extern int64_t __attribute__((sysv_abi)) family_startup_build64(void *,void *);
int main(void) {
    _Alignas(16) uint8_t source[4096],stack[4096],before[4096];
    reist_task_startup_v1_t *s=(void*)source;
    const char *args[8]={"", "service", "channel", "generation", "4", "5", "6", "7"};
    char maximum[128];memset(maximum,'Z',127);maximum[127]=0;args[7]=maximum;
    CHECK(sizeof(*s)==1040 && sizeof(reist_task_create_v2_t)==64);
    for(unsigned count=0;count<=8;count++) {
        memset(source,0xa5,sizeof(source));memset(stack,0x5a,sizeof(stack));
        CHECK(reist_x64_startup_init(s,count,args)==0);
        memcpy(before,source,sizeof(source));
        CHECK(family_startup_admit64(s)==1 && !memcmp(before,source,sizeof(source)));
        int64_t rsp=family_startup_build64(source,stack);
        CHECK(rsp>0x408000 && rsp<0x409000 && !(rsp&15));
        uint64_t *v=(void*)(stack+rsp-0x408000);CHECK(v[0]==count);
        CHECK(v[count+1]==0 && v[count+2]==0 && v[count+3]==0x52534901 && v[count+4]==0 && v[count+5]==0);
        for(unsigned i=0;i<count;i++) CHECK(!strcmp((char*)stack+v[i+1]-0x408000,args[i]));
        CHECK(!memcmp(before,source,1040));
    }
    CHECK(reist_x64_startup_init(s,1,args)==0);
    for(unsigned n=0;n<1040;n++) {
        memcpy(before,source,sizeof(source));source[n]^=128;
        uint8_t pinned[4096];memcpy(pinned,source,sizeof(source));
        int64_t status=family_startup_admit64(s);
        CHECK(status==1 || status==-22 || status==-7);
        CHECK(!memcmp(pinned,source,sizeof(source)));
        if(status!=1) {
            memset(stack,0x5a,sizeof(stack));
            CHECK(family_startup_build64(source,stack)==status);
            for(unsigned i=0;i<4096;i++) CHECK(stack[i]==0x5a);
        }
        memcpy(source,before,sizeof(source));
    }
    CHECK(reist_x64_startup_init(s,9,args)==-7);
    memcpy(before,source,sizeof(source));
    CHECK(reist_x64_startup_init(s,1,NULL)==-22 && !memcmp(before,source,sizeof(source)));
    const char *alias[1]={s->arguments[0]};
    CHECK(reist_x64_startup_init(s,1,alias)==-22 && !memcmp(before,source,sizeof(source)));
    memset(maximum,'Z',sizeof(maximum));args[0]=maximum;
    CHECK(reist_x64_startup_init(s,1,args)==-7 && !memcmp(before,source,sizeof(source)));
    reist_task_create_v2_t q={2,64,1,0,0,5,0,1ULL<<9,32,(uintptr_t)s};
    CHECK(family_request_admit64(&q)==1);
    q.operation=2;CHECK(family_request_admit64(&q)==-22);q.operation=1;
    q.startup=0;CHECK(family_request_admit64(&q)==-22);q.startup=(uintptr_t)s;
    q.version=1;CHECK(family_request_admit64(&q)==-22);
    puts("TASK_STARTUP_HOST_OK");return 0;
}
