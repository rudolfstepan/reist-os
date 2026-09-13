/* Only the harness loads registers; the capture and clear bodies are actual ASM. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t native_pio_trace[1538],trace_guard_before[2],trace_guard_after[2];
extern uint64_t native_pio_state[8],native_pio_request[8],scheduler_tasks[512],scheduler_current_slot,family_records[32];
extern uint64_t capture_registers[17],capture_after[17];
extern unsigned char trace_data[64];
extern void __attribute__((sysv_abi)) capture_out(void),capture_data(void),capture_clear(void);
#define C(x) do{if(!(x)){printf("trace line %d\n",__LINE__);return 1;}}while(0)
static unsigned char before[12304];
static void setup(void){
 memset(native_pio_trace,0,12304);memset(native_pio_request,0,64);
 for(unsigned i=0;i<17;i++)capture_registers[i]=0x1122334455660000ULL+i;
 capture_registers[0]=0xabcdef0123450006ULL;capture_registers[3]=0x98765432100003f6ULL;
 capture_registers[6]=16;capture_registers[11]=(uintptr_t)native_pio_state;capture_registers[12]=(uintptr_t)native_pio_request;
 capture_registers[16]=0xcd7; /* IF, DF and arithmetic flags; DF must survive. */
 scheduler_current_slot=0;scheduler_tasks[1]=1;family_records[17]=1ULL<<32;
 native_pio_state[0]=3ULL<<32|2;native_pio_state[1]=~native_pio_state[0];
 native_pio_state[2]=0;native_pio_state[3]=native_pio_state[4]=1;native_pio_state[5]=1;native_pio_state[6]=1;native_pio_state[7]=0;
 for(unsigned i=0;i<2;i++)trace_guard_before[i]=trace_guard_after[i]=0x123456789abcdeffULL;
 for(unsigned i=0;i<64;i++)trace_data[i]=(unsigned char)(i^0xa5);
}
static int intact(void){
 for(unsigned i=0;i<16;i++)if(capture_registers[i]!=capture_after[i])return 0;
 if((capture_after[16]&0xcd5)!=(capture_registers[16]&0xcd5))return 0;
 for(unsigned i=0;i<2;i++)if(trace_guard_before[i]!=0x123456789abcdeffULL || trace_guard_after[i]!=0x123456789abcdeffULL)return 0;
 return 1;
}
static int zero(const void *p,unsigned n){const unsigned char *b=p;for(unsigned i=0;i<n;i++)if(b[i])return 0;return 1;}
static void request(unsigned count){
 uint32_t *q=(uint32_t*)native_pio_request;q[0]=2;q[1]=64;q[2]=4;q[3]=0;
 native_pio_request[2]=native_pio_state[0];q[6]=0x1f0;q[7]=0;q[8]=count;q[9]=0;
 native_pio_request[5]=(uintptr_t)trace_data;native_pio_request[6]=100;native_pio_request[7]=0;
 capture_registers[3]=(uintptr_t)trace_data;capture_registers[6]=count;
}
int main(void){
 setup();
 for(unsigned n=1;n<=4096;n++){
  scheduler_current_slot=n&3;scheduler_tasks[(n&3)*128+1]=n;
  capture_out();C(intact() && native_pio_trace[0]==n && !native_pio_trace[1]);
  uint64_t *r=native_pio_trace+2+((n-1)&63)*24;
  C(r[0]==1 && r[1]==n && !memcmp(r+2,native_pio_state,64));
  C(r[10]==0x3f6 && r[11]==6 && r[12]==(n&3) && r[13]==n && r[14]==1ULL<<32 && zero(r+15,72));
  if(n==64 || n==65 || n==4096)for(unsigned i=0;i<64;i++)C(native_pio_trace[2+i*24+1]==n-((n-1-i)&63));
 }
 memcpy(before,native_pio_trace,12304);capture_out();C(intact() && native_pio_trace[0]==4096 && native_pio_trace[1]==1 && !memcmp(before+16,(char*)native_pio_trace+16,12288));
 for(unsigned n=0;n<5;n++){
  setup();native_pio_trace[0]=n==0?4097:n==1?UINT64_MAX:n==2?1ULL<<63:0;native_pio_trace[1]=n==3?UINT64_MAX:n==4?1:0;
  memcpy(before,native_pio_trace,12304);capture_out();C(intact() && native_pio_trace[0]==((uint64_t*)before)[0] && native_pio_trace[1] && !memcmp(before+16,(char*)native_pio_trace+16,12288));
 }
 for(unsigned count=1;count<=16;count++){
  setup();request(count);memset(native_pio_trace+2,0xcc,12288);capture_data();C(intact() && native_pio_trace[0]==1 && !native_pio_trace[1]);
  uint64_t *r=native_pio_trace+2;C(r[0]==2 && r[1]==1 && !memcmp(r+2,native_pio_state,64));
  C(!memcmp(r+10,native_pio_request,64) && !memcmp(r+18,trace_data,count*2) && zero((char*)(r+18)+count*2,32-count*2));
  C(r[22]==count && !r[23]);
 }
 for(unsigned bad=0;bad<14;bad++){
  setup();request(16);
  switch(bad){
   case 0:capture_registers[12]=1;break;case 1:capture_registers[11]=1;break;
   case 2:capture_registers[6]=0;break;case 3:capture_registers[6]=17;break;
   case 4:((uint32_t*)native_pio_request)[8]=15;break;case 5:capture_registers[3]+=2;break;
   case 6:native_pio_request[5]=capture_registers[3]=0;break;
   case 7:native_pio_request[5]=capture_registers[3]=UINT64_MAX-1;break;
   case 8:native_pio_request[5]=capture_registers[3]=(uintptr_t)trace_data+1;break;
   case 9:scheduler_current_slot=4;break;case 10:native_pio_state[0]=UINT64_MAX;break;
   case 11:scheduler_tasks[1]=0;break;case 12:scheduler_tasks[1]=1ULL<<63;break;
   case 13:((uint32_t*)native_pio_request)[2]=3;break;
  }
  capture_data();C(intact() && !native_pio_trace[0] && native_pio_trace[1] && zero(native_pio_trace+2,12288));
 }
 setup();memset(native_pio_trace,0xff,12304);capture_clear();C(intact() && zero(native_pio_trace,12304));
 capture_clear();C(intact() && zero(native_pio_trace,12304));
 puts("pio_trace_OK slots=64 events=4096 registers=all clear=12304");return 0;
}
/* ASM
%macro load_capture 1
global %1
%1:
 push rbp
 push rbx
 push r12
 push r13
 push r14
 push r15
 mov rax,[rel capture_registers+16*8]
 push rax
 popfq
 mov rax,[rel capture_registers]
 mov rbx,[rel capture_registers+8]
 mov rcx,[rel capture_registers+16]
 mov rdx,[rel capture_registers+24]
 mov rsi,[rel capture_registers+32]
 mov rdi,[rel capture_registers+40]
 mov rbp,[rel capture_registers+48]
 mov r8,[rel capture_registers+56]
 mov r9,[rel capture_registers+64]
 mov r10,[rel capture_registers+72]
 mov r11,[rel capture_registers+80]
 mov r12,[rel capture_registers+88]
 mov r13,[rel capture_registers+96]
 mov r14,[rel capture_registers+104]
 mov r15,[rel capture_registers+112]
 mov [rel capture_registers+120],rsp
%endmacro
load_capture capture_out
 call native_pio_trace_out64
 jmp capture_save
load_capture capture_data
 call native_pio_trace_data64
 jmp capture_save
load_capture capture_clear
 call native_pio_trace_clear64
capture_save:
 mov [rel capture_after],rax
 mov [rel capture_after+8],rbx
 mov [rel capture_after+16],rcx
 mov [rel capture_after+24],rdx
 mov [rel capture_after+32],rsi
 mov [rel capture_after+40],rdi
 mov [rel capture_after+48],rbp
 mov [rel capture_after+56],r8
 mov [rel capture_after+64],r9
 mov [rel capture_after+72],r10
 mov [rel capture_after+80],r11
 mov [rel capture_after+88],r12
 mov [rel capture_after+96],r13
 mov [rel capture_after+104],r14
 mov [rel capture_after+112],r15
 mov [rel capture_after+120],rsp
 pushfq
 pop rax
 mov [rel capture_after+128],rax
 cld
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
ASM */
