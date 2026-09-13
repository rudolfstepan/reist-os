"""Execute the production boot leaf verifier with a bounded fake page table."""
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'test'))
import test_x86_64_program_memory as host

class WideBootTests(unittest.TestCase):
    def test_actual_all_leaf_permissions_and_bounds(self):
        source=(ROOT/'arch/x86_64/boot/entry.asm').read_text()
        self.assertIn('verify_native_pages64:',source)
        body=source.split('verify_native_pages64:',1)[1].split('; END_NATIVE_PAGE_VERIFY',1)[0]
        leaf=source.split('verify_high_page64:',1)[1].split('long_mode_state_error:',1)[0]
        asm='''BITS 64
%define X86_64_NATIVE_RAM 1
PAGE_HW_AD_MASK equ 0x60
section .bss
align 16
global high_page_table
high_page_table: resq 4096
section .text
global check_pages
check_pages:
    push rbx
    push r12
    mov r12,rsp
    mov rax,rdi
    mov rdi,rsi
    mov rsi,rax
    call verify_native_pages64
    mov eax,1
finish:
    mov rsp,r12
    pop r12
    pop rbx
    ret
higher_half_state_error:
    xor eax,eax
    jmp finish
verify_native_pages64:
'''+body+'\nverify_high_page64:\n'+leaf
        c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t high_page_table[4096];
extern int __attribute__((sysv_abi)) check_pages(uint64_t,uint64_t,uint64_t,uint64_t);
#define C(x) do{if(!(x)){printf("boot leaf line %d\\n",__LINE__);return 1;}}while(0)
int main(void){
 const uint64_t nx=0x8000000000000000ULL;
 for(unsigned region=0;region<2;region++){
  unsigned start=region?0xb05000:0xa00000,end=region?0xb47000:0xb05000,flags=region?3:1;
  memset(high_page_table,0,sizeof(high_page_table));
  for(unsigned p=start;p<end;p+=4096)high_page_table[p>>12]=p|flags|nx;
  C(check_pages(start,end,flags,0x80000000)==1);
  /* Every occupied leaf, each forbidden permission/alias bit and absent page. */
  for(unsigned p=start;p<end;p+=4096){
   uint64_t old=high_page_table[p>>12];
   const uint64_t changes[]={1,2,4,0x80,0x1000,1ULL<<32,nx};
   for(unsigned i=0;i<sizeof(changes)/sizeof(changes[0]);i++){
    high_page_table[p>>12]=old^changes[i];C(!check_pages(start,end,flags,0x80000000));
   }
   high_page_table[p>>12]=old|0x60;C(check_pages(start,end,flags,0x80000000));
   high_page_table[p>>12]=old;
  }
  C(!check_pages(start-1,end,flags,0x80000000));
  C(!check_pages(start,end+1,flags,0x80000000));
  C(!check_pages(end,start,flags,0x80000000));
  C(!check_pages(start,start,flags,0x80000000));
  C(!check_pages(start+(1ULL<<32),end,flags,0x80000000));
  C(!check_pages(start,end+(1ULL<<32),flags,0x80000000));
 }
 C(!check_pages(0x9ff000,0xa00000,1,0x80000000));
 C(!check_pages(0xb47000,0xb48000,3,0x80000000));
 puts("wide_boot_OK");return 0;
}
'''
        host.build_actual(asm,c,'wide_boot')

if __name__=='__main__':unittest.main()
