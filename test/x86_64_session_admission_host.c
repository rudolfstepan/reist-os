#ifdef REIST_SESSION_GUEST
/* Explicit qualification-only entry wrapper. Keep the accepted CPU fixture
 * byte-exact, including its local witness, and invoke its real main otherwise.
 * GNU-compatible --wrap=main affects only these two opt-in root test images. */
#include "../arch/x86_64/user/task_pool.c"
extern int __real_main(int,char **);
static int session_pause(void) {
    /* SLEEP_MS admits only1..100ms. One private, never delegated empty endpoint
     * provides an existing bounded1000ms IPC wait without intermediate resumes.
     * Five local handles/eight global endpoints maximum in case6, below8/16. */
    uint32_t endpoint=0;
    if(S1(IPC_CREATE,&endpoint) || !endpoint)return -1;
    volatile uint32_t message[35];message_init(message,0);
    int64_t result=S3(IPC_RECEIVE_TIMEOUT,endpoint,message,1000);
    int64_t closed=S1(IPC_CLOSE,endpoint);
    return result==-110 && !closed?0:-1;
}
#if PROGRAM_ID==0
static int session_retained(uint32_t endpoint) {
    /* EPIPE proves fencing; the unchanged raw phase4 oracle still requires a
     * retired receipt AND zero task state. Block while kernel reapers advance,
     * without spending the root's CPU allowance on 56 resumed YIELD calls. */
    for(unsigned n=0;n<8;n++) {
        volatile uint32_t message[35];message_init(message,0);
        int64_t result=S3(IPC_RECEIVE_TIMEOUT,endpoint,message,1000);
        if(result==-32)return session_pause();
        if(result!=-110)return -1;
    }
    return -1;
}
static int session_case6(void) {
    root_witness.owner=(uint64_t)S0(GETPID);root_witness.phase=1;
    REQUIRE(root_witness.owner && root_witness.owner<=UINT32_MAX,202);
    void *record=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    void *prepared=(void*)(uintptr_t)S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
    REQUIRE((int64_t)(uintptr_t)record>0 && (int64_t)(uintptr_t)prepared>0,203);
    REQUIRE(!reist_x64_image_prepare_v2(prepared,import_blob,sizeof(import_blob)),243);
    root_witness.record=(uintptr_t)record;service_template=prepared;
    uint32_t ports[3]={0,0,0};
    for(unsigned i=0;i<3;i++) {
        REQUIRE(S1(IPC_CREATE,&ports[i])==0 && ports[i],204);
        int64_t child=service_create(record,i,ports[i],0);
        REQUIRE(child>0,206);root_witness.children[i]=(uint64_t)child;
        REQUIRE(S3(IPC_DELEGATE,ports[i],(uint64_t)child>>32,2)==0,207);
    }
    root_witness.phase=2;REQUIRE(!service_idle(2),208);
    REQUIRE(service_create(record,0,ports[0],0)==-11,209);root_witness.phase=3;
    for(unsigned i=0;i<3;i++)REQUIRE(release(ports[i],i)==0,210);
    REQUIRE(!service_overlap(2500),210);
    REQUIRE(!session_retained(ports[0]),244);
    REQUIRE(service_create(record,0,ports[0],0)==-11,211);root_witness.phase=4;
    uint64_t previous=root_witness.children[0];REQUIRE(service_wait(previous)==80,212);
    REQUIRE(S1(IPC_CLOSE,ports[0])==0 && S1(IPC_CREATE,&ports[0])==0,213);
    int64_t replacement=service_create(record,0,ports[0],0);
    REQUIRE(replacement>0 && (uint32_t)replacement==(uint32_t)previous &&
            ((uint64_t)replacement>>32)>(previous>>32),214);
    root_witness.children[0]=(uint64_t)replacement;
    REQUIRE(control(2,previous,1)==-10,215);
    REQUIRE(S3(IPC_DELEGATE,ports[0],(uint64_t)replacement>>32,2)==0,216);
    root_witness.phase=5;REQUIRE(release(ports[0],0)==0,218);
    for(unsigned i=0;i<3;i++) {
        REQUIRE(service_wait(root_witness.children[i])==80+i,219);
        REQUIRE(control(2,root_witness.children[i],1)==-10 && S1(IPC_CLOSE,ports[i])==0,220);
    }
    REQUIRE(!S1(FREE,record) && !S1(FREE,prepared),221);
    service_template=0;root_witness.phase=6;return 90;
}
#endif
int __wrap_main(int argc,char **argv) {
#if PROGRAM_ID==0
    if(root_witness.mode==6)return session_case6();
#endif
    if(root_witness.mode!=12)return __real_main(argc,argv);
    root_witness.owner=(uint64_t)S0(GETPID);root_witness.phase=1;
    uint64_t previous=0;
    for(unsigned n=0;n<(PROGRAM_ID==0?12U:8U);n++) {
        if(PROGRAM_ID==0 && n==8)REQUIRE(!session_pause(),250);
        /* A trusted catalog child exits97; no imported image or extra grant.
         * One bounded retry after real blocking sleep, never retry-until-green. */
        reist_task_control_request_t q={1,64,1,0,0,6,0,1ULL<<9,32,0};
        int64_t child=reist_x64_task_control(&q);
        if(PROGRAM_ID==0 && child==-11) {
            REQUIRE(!session_pause(),250);
            child=reist_x64_task_control(&q);
        }
        REQUIRE(child>0 && (uint64_t)child>previous,251);
        if(previous)REQUIRE(control(2,previous,1)==-10 && control(3,previous,0)==-10,252);
        root_witness.children[0]=(uint64_t)child;root_witness.phase=2+n;
        REQUIRE(control(2,(uint64_t)child,1000)==97,253);
        REQUIRE(control(2,(uint64_t)child,1)==-10,254);previous=(uint64_t)child;
    }
    if(PROGRAM_ID==1) {
        REQUIRE(!session_pause(),255);
        reist_task_control_request_t q={1,64,1,0,0,6,0,1ULL<<9,32,0};
        REQUIRE(reist_x64_task_control(&q)==-11,249);
    }
    root_witness.phase=20;return 90+PROGRAM_ID;
}
#else
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef uint64_t U;
extern U __attribute__((sysv_abi)) session_admission64(U *,U,U,U);
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);abort();}}while(0)
/* Independent straight-line model; production assembly is always executed. */
static U model(U *s,U op,U gen,U now) {
    if(!gen || gen>0x7fffffff || now>=(1ULL<<60) || op<1 || op>3)return 0;
    if(op==1) {
        for(unsigned n=0;n<7;n++)if(s[n])return 0;
        s[0]=gen;s[1]=100;s[2]=s[3]=now;s[6]=1;return 1;
    }
    if(s[0]!=gen || s[1]!=100 || s[6]!=1 || s[2]>s[3] || s[3]>now ||
       s[3]-s[2]>=100 || s[4]>8 || s[4]>s[5] || s[5]>0x7fffffff)return 0;
    if(op==2)return 1;
    if(s[5]==0x7fffffff)return 2;
    U start=s[2]+((now-s[2])/100)*100;
    U count=start==s[2]?s[4]:0;
    if(count==8)return 2;
    s[2]=start;s[3]=now;s[4]=count+1;s[5]++;return 1;
}
static unsigned calls,results[3];
static void compare(const U *input,U op,U gen,U now) {
    U a[9],b[9];a[0]=b[0]=0xa55a;a[8]=b[8]=0x5aa5;
    memcpy(a+1,input,56);memcpy(b+1,input,56);
    U expected=model(b+1,op,gen,now),actual=session_admission64(a+1,op,gen,now);
    CHECK(actual==expected && !memcmp(a,b,sizeof(a)));calls++;results[actual]++;
    if(actual!=1 || op==2)CHECK(!memcmp(a+1,input,56));
}
int main(void) {
    U state[7]={0};compare(state,1,7,91);
    CHECK(session_admission64(state,1,7,91)==1);
    for(unsigned n=0;n<8;n++)CHECK(session_admission64(state,3,7,91+n)==1);
    compare(state,3,7,190);CHECK(session_admission64(state,3,7,190)==2);
    CHECK(session_admission64(state,3,7,191)==1 && state[4]==1 && state[5]==9);
    CHECK(session_admission64(state,3,7,1000091)==1 && state[4]==1 && state[5]==10);
    CHECK(state[2]==1000091); /* idle time yields one window, never credit */
    U values[]={0,1,7,8,9,99,100,101,190,191,192,0x7fffffff,0x80000000,
                (1ULL<<60)-1,1ULL<<60,UINT64_MAX};
    U seed[7]={7,100,91,99,8,8,1};
    for(unsigned op=0;op<=4;op++)for(unsigned ti=0;ti<sizeof(values)/sizeof(*values);ti++) {
        compare(seed,op,7,values[ti]);compare(seed,op,8,values[ti]);
        compare(seed,op,0,values[ti]);compare(seed,op,1ULL<<32,values[ti]);
        for(unsigned n=0;n<7;n++)for(unsigned vi=0;vi<sizeof(values)/sizeof(*values);vi++) {
            U changed[7];memcpy(changed,seed,56);changed[n]=values[vi];
            compare(changed,op,7,values[ti]);
        }
    }
    U edge[7]={0};CHECK(session_admission64(edge,1,0x7fffffff,(1ULL<<60)-102)==1);
    for(unsigned n=0;n<8;n++)CHECK(session_admission64(edge,3,0x7fffffff,(1ULL<<60)-102)==1);
    CHECK(session_admission64(edge,3,0x7fffffff,(1ULL<<60)-1)==1);
    edge[5]=0x7fffffff;compare(edge,3,0x7fffffff,(1ULL<<60)-1);
    CHECK(!session_admission64(NULL,1,7,0));
    unsigned char unaligned[64]={0};CHECK(!session_admission64((U*)(void*)(unaligned+1),1,7,0));
    CHECK(calls>9000 && results[0] && results[1] && results[2]);
    puts("SESSION_ADMISSION_OK");return 0;
}
#endif
