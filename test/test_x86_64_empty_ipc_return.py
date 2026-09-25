"""Execute admitted IPC return/scrub assembly and unchanged query/IPC safety."""
from pathlib import Path
import unittest
from test_x86_64_program_memory import build_actual
from test_x86_64_query_return import QueryReturnTests
import test_x86_64_native_ipc as native
ROOT=Path(__file__).resolve().parents[1]
class NativeCoreTests(native.NativeIPCTests):
    pass
class EmptyReturnTests(unittest.TestCase):
    def test_actual_empty_return(self):
        s=(ROOT/'arch/x86_64/proc/process_ipc.inc').read_text()
        a=s.index('; EMPTY_IPC_RETURN_BEGIN');b=s.index('; EMPTY_IPC_RETURN_END',a)
        tail=s[a:b]
        zero=s[s.index('process_ipc_zero64:'):s.index('; EDI operation,',s.index('process_ipc_zero64:'))]
        for enabled in (0,1):
            asm='BITS 64\n'+('%define REIST_NATIVE_DESKTOP_CPU 1\n' if enabled else '')
            asm+='section .text\nglobal ipc_probe\nipc_probe:\n'
            asm+=r"""
 push r13
 push rbx
 sub rsp,2144
 mov r13,rsp
 mov rbx,rdi
 push rsi
 push rdx
 push rcx
 lea rdi,[r13]
 mov eax,0x5a5a5a5a
 mov ecx,2144/4
 cld
 rep stosd
 pop rcx
 pop rdx
 pop rsi
 mov [r13],rbx
 mov [r13+24],rsi
 mov [r13+40],rdx
 mov [rel frame],r13
 mov rax,rdx
"""+tail+r"""
process_run_resume64:
 mov dword [rel direct],0
 jmp finish
query_resume64:
 mov dword [rel direct],1
finish:
 mov [rel returned],rax
 mov rsi,[rel frame]
 mov ecx,2144
 lea rdi,[rel scrub]
 rep movsb
 pop rbx
 pop r13
 ret
"""+zero+r"""
section .data
global direct,returned,scrub,scheduler_cpu_budgets,scheduler_cpu_windows
scheduler_current_slot:dd 0
align 8
scheduler_cpu_budgets:times 32 dq 0
scheduler_cpu_windows:times 32 dq 0
frame:dq 0
direct:dd 0
align 8
returned:dq 0
align 16
scrub:times 2144 db 0
"""
            c='#define ENABLED '+str(enabled)+'\n'+r"""
#include <stdint.h>
#include <stdio.h>
extern uint64_t scheduler_cpu_budgets[32],scheduler_cpu_windows[32];
extern uint32_t direct;
extern int64_t returned;
extern unsigned char scrub[2144];
extern int64_t __attribute__((sysv_abi)) ipc_probe(uint64_t,uint64_t,int64_t);
int main(void) {
 const uint64_t waits[]={0,1,100,1000,UINT32_MAX,UINT64_MAX};
 const int64_t results[]={-11,0,1,-9,-13,-14,-22,-32,-110,-4095,INT64_MIN};
 const uint64_t limits[]={0,32,64,65,UINT64_MAX};
 const uint64_t periods[]={0,99,100,101,UINT64_MAX};
 for(unsigned l=0;l<5;l++)for(unsigned p=0;p<5;p++){
 scheduler_cpu_budgets[1]=limits[l];scheduler_cpu_windows[0]=periods[p];
 for(uint64_t op=0;op<64;op++)for(unsigned w=0;w<6;w++)for(unsigned r=0;r<11;r++){
  int64_t value=ipc_probe(op,waits[w],results[r]);
  if(value!=results[r] || returned!=value){printf("result op=%llu wait=%llu in=%lld out=%lld saved=%lld\n",(unsigned long long)op,(unsigned long long)waits[w],(long long)results[r],(long long)value,(long long)returned);return 1;}
  if(direct!=(unsigned)(ENABLED && limits[l]==64 && periods[p]==100 && op==54 && !waits[w] && value==-11))return 2;
  for(unsigned n=0;n<2144;n++)if(scrub[n]){printf("scrub byte=%u value=%u\n",n,scrub[n]);return 3;}
 }
 }
 puts("EMPTY_IPC_RETURN_OK");return 0;
}
"""
            build_actual(asm,c,'EMPTY_IPC_RETURN')
if __name__=='__main__':unittest.main()
