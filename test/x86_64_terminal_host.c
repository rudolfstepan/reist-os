#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct { uint64_t root,child,fenced; } State;
typedef struct { uint64_t caller,parent,root,target,target_parent,target_mask,target_ext,mask,ext; } View;
typedef struct { uint32_t version,size,operation,reserved; int32_t pid; uint32_t generation; } Request;
extern int64_t __attribute__((sysv_abi)) native_terminal_shape64(const State *);
extern int64_t __attribute__((sysv_abi)) native_terminal_plan64(const State *,const View *,const Request *,uint64_t *);
extern int64_t __attribute__((sysv_abi)) native_terminal_io64(const State *,uint64_t,unsigned);
extern int64_t __attribute__((sysv_abi)) native_terminal_retire64(State *,uint64_t);
#define CHECK(c) do { if(!(c)){printf("line %d\n",__LINE__);return 1;} }while(0)
static int plan(State *s,View *v,Request *q,int64_t expected,uint64_t next) {
    State before=*s;View old=*v;Request req=*q;uint64_t proposal=UINT64_MAX;
    int64_t result=native_terminal_plan64(s,v,q,&proposal);
    return result==expected && !memcmp(s,&before,sizeof before) && !memcmp(v,&old,sizeof old) &&
        !memcmp(q,&req,sizeof req) && proposal==(expected?UINT64_MAX:next);
}
int main(void) {
    const uint64_t root=1ULL<<32,child=(3ULL<<32)|2,other=(4ULL<<32)|3;
    const uint64_t io=(1ULL<<15)|(1ULL<<20),ctl=1ULL<<63;
    State s={root,0,0};View v={root,0,root,child,root,io,ctl,io,ctl};Request q={1,24,1,0,0,0};
    CHECK(native_terminal_shape64(&s)==1);
    CHECK(plan(&s,&v,&q,0,0));q.operation=5;CHECK(plan(&s,&v,&q,0,0));
    q.operation=2;q.pid=3;q.generation=3;CHECK(plan(&s,&v,&q,0,child));
    s.child=child;CHECK(plan(&s,&v,&q,0,child));
    v.target=other;q.pid=4;q.generation=4;CHECK(plan(&s,&v,&q,-16,0));
    v.target=child;q.pid=3;q.generation=3;
    for(unsigned field=0;field<6;field++) {
        Request bad=q;uint32_t *w=(uint32_t*)&bad;
        w[field]=field==0?2:field==1?23:field==2?6:field==3?1:field==4?0:2;
        CHECK(plan(&s,&v,&bad,field==5?-116:-22,0));
    }
    for(unsigned test=0;test<4;test++) {
        View bad=v;
        if(test==0)bad.target=0;
        if(test==1)bad.target_parent=9ULL<<32;
        if(test==2)bad.target_mask=0;
        if(test==3)bad.target_ext=ctl|(1ULL<<49);
        CHECK(plan(&s,&bad,&q,test==0?-116:-13,0));
    }
    q=(Request){1,24,5,0,0,0};CHECK(plan(&s,&v,&q,-11,0));
    CHECK(native_terminal_io64(&s,root,15)==-11);
    CHECK(native_terminal_io64(&s,root,20)==1);
    CHECK(native_terminal_io64(&s,child,15)==1 && native_terminal_io64(&s,child,20)==1);
    CHECK(native_terminal_io64(&s,other,15)==-13 && native_terminal_io64(&s,child,127)==-13);
    v.caller=child;v.parent=root;CHECK(plan(&s,&v,&q,0,child));
    q.operation=1;CHECK(plan(&s,&v,&q,-13,0));q.operation=4;CHECK(plan(&s,&v,&q,-95,0));
    q.operation=2;q.pid=4;q.generation=4;CHECK(plan(&s,&v,&q,-13,0));
    q=(Request){1,24,3,0,0,0};CHECK(plan(&s,&v,&q,0,0));
    s.child=0;CHECK(plan(&s,&v,&q,0,0));
    s.child=other;CHECK(plan(&s,&v,&q,0,other));
    CHECK(native_terminal_retire64(&s,child)==0 && s.child==other);
    CHECK(native_terminal_retire64(&s,other)==1 && !s.child);
    CHECK(native_terminal_retire64(&s,other)==0);
    s.child=child;s.fenced=1;
    CHECK(native_terminal_io64(&s,root,20)==-5 && plan(&s,&v,&q,-5,0));
    CHECK(native_terminal_retire64(&s,root)==1 && !s.root && !s.child && s.fenced==1);
    CHECK(native_terminal_retire64(&s,root)==0 && native_terminal_io64(&s,root,15)==-13);
    for(unsigned i=0;i<6;i++) {
        State bad={root,child,0};
        if(i==0)bad.fenced=2;
        if(i==1)bad.root|=1;
        if(i==2)bad.root=0;
        if(i==3)bad.root=1ULL<<63;
        if(i==4)bad.child=(3ULL<<32)|1;
        if(i==5)bad.child=(3ULL<<32)|8;
        State before=bad;
        CHECK(!native_terminal_shape64(&bad));
        CHECK(native_terminal_retire64(&bad,root)==-117 && !memcmp(&bad,&before,sizeof bad));
        CHECK(native_terminal_io64(&bad,root,20)==-117 && plan(&bad,&v,&q,-117,0));
    }
    puts("TERMINAL_STATE_OK");return 0;
}
