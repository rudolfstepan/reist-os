#include "../arch/x86_64/proc/syscall_profile.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){printf("PROFILE_FAIL line=%d\n",__LINE__);return 1;}}while(0)
struct sample {
    uint64_t before,task[32],gap;
    struct reist_x64_profile profile;
    uint64_t after;
    struct reist_x64_profile_binding binding;
};
static void init(struct sample *s,uint64_t generation,uint64_t mask){
    memset(s,0,sizeof *s);s->before=0x123456789;s->gap=0xabcdef;s->after=0x987654321;
    s->task[0]=9;s->task[1]=generation;
    s->binding=(struct reist_x64_profile_binding){s->task,&s->profile,generation,mask};
}
static int unchanged(struct sample *s,uint64_t op,uint64_t number,uint64_t result){
    struct sample before=*s;
    return reist_x64_profile_apply(&s->binding,op,number)==result && !memcmp(&before,s,sizeof *s);
}
int main(void){
    struct sample s;
    const uint64_t generations[]={1,40,41,42,0x10000,0x80000000,UINT32_MAX};
    const uint64_t masks[]={0,1,UINT64_C(1)<<63,UINT64_MAX,0x1249249249};
    for(unsigned g=0;g<sizeof generations/sizeof *generations;g++)
    for(unsigned m=0;m<sizeof masks/sizeof *masks;m++){
        init(&s,generations[g],masks[m]);
        struct sample expected=s;expected.profile=(struct reist_x64_profile){generations[g],masks[m]};
        CHECK(reist_x64_profile_apply(&s.binding,1,0)==1);
        CHECK(!memcmp(&s,&expected,sizeof s));CHECK(unchanged(&s,1,0,0));
        s.task[0]=2;
        CHECK(unchanged(&s,0,UINT64_MAX,1));
        for(unsigned n=0;n<64;n++)CHECK(unchanged(&s,2,n,(masks[m]>>n)&1?1:2));
        CHECK(unchanged(&s,2,64,2));CHECK(unchanged(&s,2,1ULL<<32,2));
        CHECK(unchanged(&s,2,UINT64_MAX,2));
        CHECK(unchanged(&s,3,0,0));
        s.task[0]=4;
        expected=s;expected.profile=(struct reist_x64_profile){0,0};
        CHECK(reist_x64_profile_apply(&s.binding,3,0)==1 && !memcmp(&s,&expected,sizeof s));
        CHECK(unchanged(&s,3,0,1));
        s.task[1]=generations[g]+1;CHECK(unchanged(&s,3,0,0));
    }
    for(unsigned state=0;state<=10;state++){
        init(&s,81,UINT64_MAX);s.task[0]=state;
        CHECK(unchanged(&s,2,1,0));
        if(state!=9)CHECK(unchanged(&s,1,0,0));
        s.profile=(struct reist_x64_profile){81,UINT64_MAX};
        if(state!=2)CHECK(unchanged(&s,2,1,0));
        if(state!=3 && state!=4 && state!=8 && state!=9)CHECK(unchanged(&s,3,0,0));
        else CHECK(reist_x64_profile_apply(&s.binding,3,0)==1);
    }
    init(&s,77,1);s.task[0]=2;s.profile=(struct reist_x64_profile){77,1};
    s.profile.generation=76;CHECK(unchanged(&s,2,0,0));s.profile.generation=77;
    s.profile.mask=3;CHECK(unchanged(&s,2,0,0));s.profile.mask=1;
    s.binding.generation=0;CHECK(unchanged(&s,2,0,0));
    s.binding.generation=1ULL<<32;CHECK(unchanged(&s,2,0,0));
    s.binding.generation=77;CHECK(unchanged(&s,4,0,0));
    CHECK(unchanged(&s,1ULL<<32,0,0));
    s.binding.profile=(void*)s.task;CHECK(unchanged(&s,1,0,0));
    s.binding.profile=(void*)&s.binding;CHECK(unchanged(&s,1,0,0));
    s.binding.profile=(void*)(UINTPTR_MAX-7);CHECK(unchanged(&s,1,0,0));
    s.binding.profile=(void*)((unsigned char*)&s.profile+1);CHECK(unchanged(&s,1,0,0));
    s.binding.profile=&s.profile;s.binding.task=(void*)&s.binding;CHECK(unchanged(&s,1,0,0));
    s.binding.task=(void*)(UINTPTR_MAX-7);CHECK(unchanged(&s,1,0,0));
    s.binding.task=0;CHECK(unchanged(&s,1,0,0));
    CHECK(reist_x64_profile_apply(0,0,0)==0);
    CHECK(reist_x64_profile_apply((void*)(UINTPTR_MAX-7),0,0)==0);
    puts("X86_64_PROFILES_HOST_OK");return 0;
}
