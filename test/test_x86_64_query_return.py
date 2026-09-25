"""Execute production bounded query-return assembly, not a scheduling model."""
from pathlib import Path
import unittest
from test_x86_64_program_memory import build_actual
ROOT=Path(__file__).resolve().parents[1]
class QueryReturnTests(unittest.TestCase):
    def test_query_observer_preserves_cpu_deadlines(self):
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from run_qemu_x86_64_query_return import query_transport
        reference=query_transport(0)._capture_run.__code__.co_consts
        selected=query_transport(8)._capture_run.__code__.co_consts
        self.assertIn(357,reference)
        self.assertIn(360,reference)
        self.assertIn(357,selected)
        self.assertIn(360,selected)
        self.assertIn('shift=3,sleep=on',selected)
    def test_actual_budget(self):
        asm='BITS 64\nsection .text\n%include "arch/x86_64/proc/query_return.inc"\n'
        c='#include "'+(ROOT/'arch/x86_64/proc/query_return.h').as_posix()+'"\n'
        c+=(ROOT/'test/x86_64_query_return_host.c').read_text()
        build_actual(asm,c,'NATIVE_QUERY_RETURN')
    def test_actual_return_adapter(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        start=source.index('query_resume64:')
        end=source.index('; QUERY_RETURN_ADAPTER_END',start)
        dispatch=source.index('process_run_dispatch64:')
        reset=source[dispatch:source.index('    call process_run_validate64',dispatch)]
        enter=source[source.index('process_run_enter64:'):source.index('process_run_syscall64:')]
        scheduler=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        constants=scheduler[scheduler.index('TASK_STATE '):scheduler.index('TASK_TABLE_LEVELS ')]
        constants+=next(line for line in scheduler.splitlines() if line.startswith('TASK_RUNNING '))+'\n'
        asm='BITS 64\n'+''.join('%define '+n+' 1\n' for n in (
            'REIST_NATIVE_WIDE','REIST_NATIVE_LARGE_IMAGE','REIST_NATIVE_LARGE_PERIODIC',
            'REIST_NATIVE_TASK_POOL','REIST_NATIVE_SERVICE_CPU','REIST_NATIVE_DESKTOP_CPU'))
        asm+='%include "arch/x86_64/mm/native_layout.inc"\n'+constants+'\nsection .text\n'
        asm+='%include "arch/x86_64/proc/query_return.inc"\n'+source[start:end]
        asm+=reset+'    mov rax,r15\n    ret\n'+enter+r"""
global query_probe,query_enter
query_enter:
 push r12
 push r15
 mov edi,4
 lea r11,[rel query_task]
 mov qword [r11+TASK_GENERATION],17
 call process_run_enter64
 pop r15
 pop r12
 ret
query_probe:
 push r12
 push r15
 mov rax,rdi
 lea r12,[rel query_task]
 mov qword [r12+TASK_STATE],TASK_RUNNING
 mov qword [r12+TASK_GENERATION],17
 call query_resume64
 pop r15
 pop r12
 ret
scheduler_save_syscall_context64:
 inc qword [rel saved]
 ret
scheduler_enter_task64:
 ud2
.state_published:
 inc qword [rel direct]
 mov rax,[r11+TASK_RAX]
 ret
process_run_resume64:
 inc qword [rel ordinary]
 mov r15,rax
 jmp process_run_dispatch64
scheduler_fail:
 ud2
section .data
scheduler_current_slot: dd 4
process_run_generations: dd 0,0,0,0,17,0,0,0
section .bss
alignb 16
global query_state64,direct,ordinary,saved
query_state64: resq 6
direct: resq 1
ordinary: resq 1
saved: resq 1
query_task: resb NATIVE_TASK_BYTES
"""
        c='#include "'+(ROOT/'arch/x86_64/proc/query_return.h').as_posix()+'"\n'+r"""
#include <stdio.h>
extern reist_native_query_state query_state64;
extern uint64_t direct,ordinary,saved;
extern uint64_t __attribute__((sysv_abi)) query_probe(uint64_t);
extern void __attribute__((sysv_abi)) query_enter(void);
int main(void){
 for(unsigned burst=0;burst<8;burst++){
  query_enter();
  if(query_state64.generation!=17 || query_state64.slot!=4 ||
     query_state64.remaining!=8)return 1;
  for(unsigned n=0;n<8;n++){
   if(query_probe(1234+n)!=1234+n)return 2;
   if(direct!=burst*8+1+(n<7?n+1:7) || ordinary!=burst+(n==7))return 3;
   if(saved!=direct-burst-1)return 4;
  }
  for(unsigned i=0;i<6;i++)if(((uint64_t *)&query_state64)[i])return 5;
 }
 puts("NATIVE_QUERY_ADAPTER_OK");return 0;
}
"""
        build_actual(asm,c,'NATIVE_QUERY_ADAPTER')
if __name__=='__main__':unittest.main()
