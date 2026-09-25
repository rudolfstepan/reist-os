#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define C(x) do{if(!(x)){printf("CPU line=%u %s\n",(unsigned)__LINE__,#x);return 1;}}while(0)
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const void*);
extern int64_t __attribute__((sysv_abi)) family_cpu_attenuate64(const void*,uint64_t,uint64_t);
extern uint64_t __attribute__((sysv_abi)) process_run_admit64(const void*);
extern uint64_t __attribute__((sysv_abi)) reist_x64_period_apply(void*,void*,uint64_t,uint64_t,uint64_t,uint64_t);
struct plan{uint32_t version,size,count,reserved;uint64_t tasks[8][4],periods[8];};
static struct plan make(unsigned version){
 struct plan p={version,336,8,0,{{0}},{0}};
 for(unsigned i=0;i<8;i++){p.tasks[i][0]=i<2;p.tasks[i][1]=512;p.tasks[i][2]=32;p.tasks[i][3]=i<2?i+3:i+5;p.periods[i]=i<2?100:0;}
 return p;
}
#if SELECTED
extern uint64_t __attribute__((sysv_abi)) process_run_live_admit64(const void*);
#endif
int main(void){
#if SELECTED
 for(unsigned slot=0;slot<8;slot++)for(unsigned limit=0;limit<=65;limit++){
  struct plan p=make(6);p.tasks[0][2]=64;p.tasks[slot][2]=limit;p.periods[slot]=100;
  struct plan before=p;
  C(process_run_live_admit64(&p)==(limit&&limit<=(slot==1?32:64)));
  C(!memcmp(&p,&before,sizeof p));
  if(slot>=2){p.tasks[0][2]=32;C(process_run_live_admit64(&p)==(limit&&limit<=32));
   p.tasks[0][2]=64;p.periods[slot]=0;C(process_run_live_admit64(&p)==(limit&&limit<=32));}
 }
#endif
 uint64_t q[10],saved[10];
 for(unsigned v=6;v<=9;v++)for(unsigned limit=0;limit<=65;limit++){
  unsigned periodic=v!=7;uint64_t init[10]={v|((uint64_t)(periodic?80:64)<<32),1,0,0x20000000,0,0x30000000,limit,0x31000000,periodic?1000:0,0};
  memcpy(q,init,80);memcpy(saved,q,80);
  unsigned max=v==9&&SELECTED?64:32;
  unsigned valid=(v!=9||SELECTED)&&limit&&limit<=max;
  C(family_request_admit64(q)==(valid?1:-22));C(!memcmp(q,saved,80));
  if(!valid||!periodic)continue;
  for(unsigned parent=0;parent<=65;parent++){
   C(family_cpu_attenuate64(q,100,parent)==(parent&&parent<=(SELECTED?64:32)&&limit<=parent?1:-13));
   C(!memcmp(q,saved,80));
  }
  C(family_cpu_attenuate64(q,0,64)==-13);
  C(family_cpu_attenuate64(q,99,64)==-13);
  q[8]=999;C(family_request_admit64(q)==-22);q[8]=1000;
  q[9]=1;C(family_request_admit64(q)==-22);q[9]=0;
  q[1]|=1ULL<<32;C(family_request_admit64(q)==-22);
 }
 for(unsigned version=5;version<=6;version++)for(unsigned slot=0;slot<8;slot++)for(unsigned limit=0;limit<=65;limit++){
  struct plan p=make(version);p.tasks[slot][2]=limit;struct plan before=p;
  unsigned max=version==6&&slot==0&&SELECTED?64:32;
  C(process_run_admit64(&p)==((version==5||SELECTED)&&limit&&limit<=max));
  C(!memcmp(&p,&before,sizeof p));
 }
 for(unsigned version=5;version<=6;version++)for(unsigned slot=0;slot<8;slot++){
  struct plan p=make(version);p.periods[slot]=101;struct plan before=p;
  C(!process_run_admit64(&p));C(!memcmp(&p,&before,sizeof p));
 }
 for(unsigned limit=1;limit<=65;limit++){
  uint64_t b[4]={0},w[4]={0};
  unsigned valid=limit<=(SELECTED?64:32);
  C(reist_x64_period_apply(b,w,1,17,(100ULL<<32)|limit,1000)==valid);
  if(!valid){C(!(b[0]|b[1]|b[2]|b[3]|w[0]|w[1]|w[2]|w[3]));continue;}
  for(unsigned epoch=0;epoch<3;epoch++)for(unsigned tick=1;tick<=limit-(epoch<2);tick++){
   C(reist_x64_period_apply(b,w,2,17,1000+epoch*100+tick,1000+epoch*100+tick)==(tick==limit?2:1));
   C(b[1]==limit && b[2]==epoch*(limit-1)+tick && w[2]==epoch && w[3]==tick);
  }
  uint64_t oldb[4],oldw[4];memcpy(oldb,b,32);memcpy(oldw,w,32);
  C(!reist_x64_period_apply(b,w,2,18,0,1400));C(!memcmp(b,oldb,32)&&!memcmp(w,oldw,32));
  C(!reist_x64_period_apply(b,w,1,17,(100ULL<<32)|limit,1400));C(!memcmp(b,oldb,32)&&!memcmp(w,oldw,32));
 }
 puts("DESKTOP_CPU_OK");return 0;
}
