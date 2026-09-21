#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint64_t root,service,epoch,fenced,inverse[4];} Service;
typedef struct {uint64_t root,child,fenced;} Lease;
typedef struct {uint64_t caller,parent,root,target,target_parent,target_mask,target_ext,mask,ext;} View;
typedef struct {uint32_t version,size,op,reserved,pid,generation;} Request;
typedef struct {Service service;uint64_t child;} Proposal;
extern int64_t __attribute__((sysv_abi)) native_terminal_service_shape64(const Service*);
extern int64_t __attribute__((sysv_abi)) native_terminal_service_plan64(const Service*,const Lease*,const View*,const Request*,Proposal*,uint64_t);
extern int64_t __attribute__((sysv_abi)) native_terminal_service_retire64(Service*,uint64_t);
#define CHECK(x) do{if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
static void seal(Service *s){uint64_t *w=(void*)s;for(unsigned n=0;n<4;n++)s->inverse[n]=~w[n];}
static int plan(Service *s,Lease *l,View *v,Request *q,unsigned flags,int expected,Proposal *out){
 Service a=*s;Lease b=*l;View c=*v;Request d=*q;Proposal old;memset(out,0xa5,sizeof(*out));old=*out;
 int64_t r=native_terminal_service_plan64(s,l,v,q,out,flags);
 return r==expected&&!memcmp(s,&a,sizeof(a))&&!memcmp(l,&b,sizeof(b))&&!memcmp(v,&c,sizeof(c))&&!memcmp(q,&d,sizeof(d))&&(!expected||!memcmp(out,&old,sizeof(old)));
}
int main(void){
 const uint64_t root=1ULL<<32,child=(3ULL<<32)|4,other=(4ULL<<32)|5,io=(1ULL<<15)|(1ULL<<20),ext=(1ULL<<63)|(1ULL<<49);
 Service s={0,0,0,1,{0}};seal(&s);Lease l={root,0,0};View v={root,0,root,child,root,io,ext,io,ext};Request q={1,24,6,0,3,3};Proposal p;
 CHECK(native_terminal_service_shape64(&s)==1);
 CHECK(plan(&s,&l,&v,&q,0,-13,&p));CHECK(plan(&s,&l,&v,&q,1,0,&p));
 CHECK(p.service.root==root&&p.service.service==child&&p.service.epoch==1&&!p.service.fenced&&!p.child&&native_terminal_service_shape64(&p.service)==1);
 for(unsigned n=0;n<6;n++){Request bad=q;uint32_t *w=(void*)&bad;w[n]=n==0?2:n==1?23:n==2?8:n==3?1:n==4?0:2;CHECK(plan(&s,&l,&v,&bad,1,n==5?-116:-22,&p));}
 for(unsigned n=0;n<4;n++){View bad=v;if(!n)bad.caller=other;if(n==1)bad.target_parent=2ULL<<32;if(n==2)bad.target_mask=0;if(n==3)bad.target_ext=0;CHECK(plan(&s,&l,&bad,&q,1,-13,&p));}
 CHECK(plan(&s,&l,&v,&q,1,0,&p));s=p.service;CHECK(plan(&s,&l,&v,&q,1,-16,&p));
 for(unsigned op=1;op<=5;op++){Request bad={1,24,op,0,0,1};CHECK(plan(&s,&l,&v,&bad,1,-22,&p));}
 Request check={1,24,5,0,0,0};CHECK(plan(&s,&l,&v,&check,1,-11,&p));
 Request acquire={1,24,4,0,0,0};CHECK(plan(&s,&l,&v,&acquire,1,-13,&p));
 v.caller=other;v.parent=root;CHECK(plan(&s,&l,&v,&acquire,1,-13,&p));
 v.caller=child;CHECK(plan(&s,&l,&v,&acquire,1,0,&p));CHECK(p.child==child&&p.service.epoch==1);l.child=child;
 CHECK(plan(&s,&l,&v,&acquire,1,0,&p));CHECK(plan(&s,&l,&v,&check,1,0,&p));
 Request release={1,24,3,0,0,0};CHECK(plan(&s,&l,&v,&release,1,0,&p));CHECK(!p.child&&p.service.fenced);s=p.service;l.child=0;
 CHECK(plan(&s,&l,&v,&acquire,1,-13,&p));
 v.caller=root;v.parent=0;Request revoke={1,24,7,0,3,3};CHECK(plan(&s,&l,&v,&revoke,1,0,&p));CHECK(p.service.fenced);
 revoke.pid=revoke.generation=4;CHECK(plan(&s,&l,&v,&revoke,1,-116,&p));
 CHECK(plan(&s,&l,&v,&q,0,-13,&p));CHECK(plan(&s,&l,&v,&q,1,0,&p));CHECK(p.service.epoch==2);s=p.service;
 Service before=s;CHECK(native_terminal_service_retire64(&s,other)==0&&!memcmp(&s,&before,sizeof(s)));
 CHECK(native_terminal_service_retire64(&s,child)==0&&s.fenced);before=s;CHECK(native_terminal_service_retire64(&s,child)==0&&!memcmp(&s,&before,sizeof(s)));
 s=before;s.fenced=0;seal(&s);CHECK(native_terminal_service_retire64(&s,root)==0&&s.fenced);
 for(unsigned n=0;n<8;n++){Service bad=s;((uint64_t*)&bad)[n]^=1;CHECK(native_terminal_service_shape64(&bad)==0);CHECK(plan(&bad,&l,&v,&q,1,-117,&p));}
 for(unsigned n=0;n<7;n++){Service bad=s;if(n==0)bad.root|=1;if(n==1)bad.root=0;if(n==2)bad.service=(3ULL<<32)|1;if(n==3)bad.epoch=0;if(n==4)bad.fenced=2;if(n==5)bad.service=1ULL<<63|4;if(n==6)bad.epoch=1ULL<<63;seal(&bad);CHECK(native_terminal_service_shape64(&bad)==0);}
 s.epoch=INT64_MAX;seal(&s);CHECK(plan(&s,&l,&v,&q,1,-75,&p));
 puts("TERMINAL_SERVICE_OK");return 0;
}
