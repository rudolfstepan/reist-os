#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define PAGES (WIDE?64:8)
#define WORDS (WIDE?128:32)
#define COUNT (4*(PAGES+5))
extern uint64_t scheduler_tasks[512],scheduler_table_frames[16],scheduler_original_cr3;
extern uint64_t baseline_comparisons,candidate_comparisons;
extern uint64_t __attribute__((sysv_abi)) baseline(void),candidate(void);
#define C(x) do{if(!(x)){printf("frame cost line %d\n",__LINE__);exit(1);}}while(0)
static uint64_t *at(unsigned n){unsigned slot=n/(PAGES+5),field=n%(PAGES+5);
 return field<PAGES?&scheduler_tasks[slot*WORDS+4+field]:field==PAGES?&scheduler_tasks[slot*WORDS+3]:&scheduler_table_frames[slot*4+field-PAGES-1];}
static void put(unsigned n,uint64_t value){*at(n)=value;
 if(n%(PAGES+5)==PAGES+1)scheduler_tasks[n/(PAGES+5)*WORDS+2]=value;}
static void setup(unsigned stride){memset(scheduler_tasks,0,4096);memset(scheduler_table_frames,0,128);scheduler_original_cr3=0x1000;
 for(unsigned s=0;s<4;s++)scheduler_tasks[s*WORDS]=1;
 for(unsigned n=0;n<COUNT;n++)put(n,0x100000000ULL+((uint64_t)n*stride+1)*4096);}
static uint64_t vectors;
static uint64_t compare(void){uint64_t before[529];memcpy(before,scheduler_tasks,4096);memcpy(before+512,scheduler_table_frames,128);before[528]=scheduler_original_cr3;
 baseline_comparisons=candidate_comparisons=0;uint64_t a=baseline(),b=candidate();C(a==b);
 C(!memcmp(before,scheduler_tasks,4096)&&!memcmp(before+512,scheduler_table_frames,128)&&before[528]==scheduler_original_cr3);
 C(candidate_comparisons<=baseline_comparisons && baseline_comparisons<=(uint64_t)COUNT*(COUNT-1)/2);
 vectors++;return b;}
int main(void){
 setup(1);C(compare()==1);uint64_t before=baseline_comparisons,after=candidate_comparisons;
 C(WIDE?after*4<before:after==before);
 printf("FRAME_COST_SEQUENTIAL wide=%d frames=%u old=%llu new=%llu\n",WIDE,COUNT,(unsigned long long)before,(unsigned long long)after);
 for(unsigned i=0;i<COUNT;i++)for(unsigned j=0;j<i;j++){
  uint64_t saved=*at(i);put(i,*at(j));C(compare()==0);put(i,saved);
 }
 const uint64_t invalid[]={0,1,0x1001,0x400000000ULL,UINT64_MAX,0x1000};
 for(unsigned i=0;i<COUNT;i++)for(unsigned j=0;j<sizeof(invalid)/sizeof(*invalid);j++){
  uint64_t saved=*at(i);put(i,invalid[j]);C(compare()==(j==0&&i%(PAGES+5)<PAGES));put(i,saved);
 }
 for(unsigned s=0;s<4;s++){
  scheduler_tasks[s*WORDS+2]^=4096;C(compare()==0);scheduler_tasks[s*WORDS+2]^=4096;
  scheduler_tasks[s*WORDS]=0;C(compare()==0);scheduler_tasks[s*WORDS]=1;
 }
 memset(scheduler_tasks,0,4096);memset(scheduler_table_frames,0,128);C(compare()==1);
 for(unsigned i=0;i<COUNT;i++){*at(i)=0x100000000ULL;C(compare()==0);*at(i)=0;}
 /* Folded low9-bit filter adversary: all entries collide but are distinct. */
 setup(1);
 for(unsigned n=0;n<COUNT;n++){uint64_t page=((uint64_t)n<<9)|n;put(n,(page+0x100000)*4096);}
 C(compare()==1);
 C(candidate_comparisons==baseline_comparisons); /* every filter collision scanned */
 for(unsigned i=0;i<COUNT;i++){uint64_t saved=*at(i);put(i,0x200000000ULL+((uint64_t)i+1)*4096);C(compare()==1);put(i,saved);}
 if(WIDE){memcpy(scheduler_tasks,captured_tasks,4096);memcpy(scheduler_table_frames,captured_tables,128);scheduler_original_cr3=CAPTURED_ROOT;
  C(compare()==1);before=baseline_comparisons;after=candidate_comparisons;C(before>0 && after*4<before);
  printf("FRAME_COST_GUEST old=%llu new=%llu\n",(unsigned long long)before,(unsigned long long)after);
  for(unsigned n=0;n<32;n++)C(compare()==1);
 }
 puts("frame_cost_OK");printf("vectors=%llu\n",(unsigned long long)vectors);return 0;
}
