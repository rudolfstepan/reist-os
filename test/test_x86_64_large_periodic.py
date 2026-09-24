"""Execute production request admission and immutable parent attenuation."""
from pathlib import Path
import unittest
from test_x86_64_program_memory import build_actual

ROOT = Path(__file__).resolve().parents[1]


class LargePeriodicTests(unittest.TestCase):
    def test_invalid_selectors_fail_before_output(self):
        import build_x86_64_boot_programs as producer
        import uuid
        output=ROOT/'build/codex-agent/r83cd-large-periodic'/('must-not-exist-'+uuid.uuid4().hex)
        valid=dict(large_periodic=True,large_image=True,wide=True,task_pool=True,service_cpu=True)
        cases=[dict(valid,large_periodic=1),dict(valid,large_image=False),
               dict(valid,wide=False),dict(valid,task_pool=False),dict(valid,service_cpu=False),
               dict(valid,session=True),dict(valid,large_file=True)]
        for values in cases:
            with self.subTest(values=values),self.assertRaises(ValueError):
                producer.build(output,[],[],[],0,**values)
            self.assertFalse(output.exists())

    def test_actual_sdk_transport(self):
        asm='''BITS 64
section .text
global reist_sdk64_test_trap
reist_sdk64_test_trap:
 mov [rel number],rax
 push rsi
 push rdi
 push rcx
 mov rsi,rdi
 lea rdi,[rel captured]
 mov ecx,10
 rep movsq
 pop rcx
 pop rdi
 pop rsi
 mov eax,1234
 ret
section .bss
alignb 16
global captured,number
captured: resq 10
number: resq 1
'''
        c='''#define REIST_NATIVE_LARGE_IMAGE 1
#define REIST_NATIVE_LARGE_PERIODIC 1
#define REIST_X64_TEST_TRAP 1
#include "'''+(ROOT/'userspace/sdk/include/reist/x86_64/task.h').as_posix()+'''"
#include <stdio.h>
#include <string.h>
extern uint64_t captured[10],number;
int main(void){
 reist_task_profile_v1_t profile={0};reist_task_startup_v1_t startup={0};
 char image[1];uint64_t expected[10]={8ULL|(80ULL<<32),1,0,(uintptr_t)image,0,
                                     (uintptr_t)&profile,17,(uintptr_t)&startup,1000,0};
 if(reist_x64_task_import_large_periodic(image,&profile,17,&startup)!=1234 ||
    number!=REIST_SYS_TASK_CONTROL || memcmp(expected,captured,80))return 1;
 puts("large_periodic_sdk_OK");return 0;
}
'''
        # The existing behavior harness has no repository include option; use
        # CPATH only for this compiler invocation and restore it afterwards.
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {'CPATH':str(ROOT/'userspace/sdk/include')}):
            build_actual(asm,c,'large_periodic_sdk')

    def test_actual_period_publication(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        start=source.index('%ifdef REIST_NATIVE_SERVICE_CPU\n    xor eax,eax',source.index('family_create64:'))
        end=source.index('    mov eax,edi\n    shl eax,4',start)
        for enabled in (False,True):
            asm='BITS 64\n%define REIST_NATIVE_SERVICE_CPU 1\n'
            if enabled:asm+='%define REIST_NATIVE_LARGE_PERIODIC 1\n'
            asm+='section .text\nglobal publish\npublish:\n'+source[start:end]+'''ret
section .bss
alignb 16
global family_request,process_run_plan
family_request: resb 80
process_run_plan: resb 336
'''
            c=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern void __attribute__((sysv_abi)) publish(uint64_t);
extern uint32_t family_request[20];
extern uint64_t process_run_plan[42];
int main(void){
 for(unsigned version=6;version<=8;version++)for(unsigned slot=0;slot<8;slot++){
  uint64_t before[42];memset(before,0xa5,sizeof before);
  memcpy(process_run_plan,before,sizeof before);family_request[0]=version;
  publish(slot);before[34+slot]=version==6||(ENABLED&&version==8)?100:0;
  if(memcmp(before,process_run_plan,sizeof before))return 1;
 }
 puts("large_periodic_plan_OK");return 0;
}
'''.replace('ENABLED',str(int(enabled)))
            build_actual(asm,c,'large_periodic_plan')

    def test_complete_snapshot_and_image_dispatch(self):
        source = (ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        admission = source.split('; Pinned profile-v1')[0]
        body = source[source.index('family_syscall64:'):source.index('\n.admitted:', source.index('family_syscall64:'))]
        asm = ('BITS 64\n%define REIST_NATIVE_WIDE 1\n'
               '%define REIST_NATIVE_LARGE_IMAGE 1\n'
               '%define REIST_NATIVE_SERVICE_CPU 1\n'
               '%define REIST_NATIVE_LARGE_PERIODIC 1\n'
               '%define REIST_NATIVE_TASK_POOL 1\nPF_R equ 4\nsection .text\n')
        asm += admission + body + '''
.admitted:
 mov eax,1
 ret
.pointer:
 mov rax,-14
 ret
.invalid_image:
 mov rax,-22
 ret
process_run_syscall64.invalid:
 mov rax,-22
 ret
family_result64:
 ret
family_profile_admit64:
family_startup_admit64:
 mov eax,1
 ret
family_import_range64:
 mov dword [rel selected_range],1
 mov eax,1
 ret
family_import_range_v2_64:
 mov dword [rel selected_range],2
 mov eax,1
 ret
family_import_range_v3_64:
 mov dword [rel selected_range],3
 mov eax,1
 ret
boot_program_admit64:
 mov [rel selected_bytes],rsi
 mov eax,1
 ret
scheduler_validate_shell_range64:
 inc dword [rel checks]
 cmp rax,[rel syscall_rdi]
 jne .other
 cmp rdx,[rel readable]
 ja .bad
.other:
 mov eax,1
 ret
.bad:
 xor eax,eax
 ret
global invoke
invoke:
 push rdi
 push rsi
 call family_syscall64
 pop rsi
 pop rdi
 ret
section .data
global syscall_rdi,readable,selected_bytes,selected_range,checks
syscall_rdi: dq 0
syscall_rsi: dq 0
syscall_rdx: dq 0
syscall_r10: dq 0
syscall_r8: dq 0
syscall_r9: dq 0
readable: dq 0
selected_bytes: dq 0
selected_range: dd 0
checks: dd 0
section .bss
alignb 16
global family_request,elf_import_record
family_request: resb 80
family_admitted_profile: resb 40
family_startup: resb 1040
alignb 16
elf_import_record: resb 1052960
'''
        c = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define C(x) do{if(!(x)){printf("snapshot line %d\n",__LINE__);return 1;}}while(0)
extern int64_t __attribute__((sysv_abi)) invoke(void);
extern uint64_t syscall_rdi,readable,selected_bytes;
extern unsigned selected_range,checks;
extern unsigned char family_request[80],elf_import_record[1052960];
static unsigned char record[1052960];
int main(void) {
 uint64_t profile[5]={1ULL|(40ULL<<32),0x1234,0,0,0};
 uint64_t startup[130]={0};
 for(unsigned version=6;version<=8;version++) {
  unsigned n=version==7?64:80,bytes=version==6?266336:1052960;
  uint64_t request[10]={version|((uint64_t)n<<32),1,0,(uintptr_t)record,0,
                       (uintptr_t)profile,32,(uintptr_t)startup,1000,0};
  syscall_rdi=(uintptr_t)request;
  for(unsigned available=0;available<n;available++) {
   readable=available;checks=selected_range=0;selected_bytes=0;
   memset(family_request,0xa5,80);memset(elf_import_record,0xa5,sizeof record);
   C(invoke()==-14);
   C(checks==(available<64?1U:2U)&&!selected_range&&!selected_bytes);
   for(unsigned i=0;i<80;i++)C(family_request[i]==0xa5);
   for(unsigned i=0;i<sizeof record;i++)C(elf_import_record[i]==0xa5);
  }
  readable=n;checks=selected_range=0;selected_bytes=0;
  memset(record,0,bytes);record[256]=0x71;record[bytes-4097]=0x39;
  memset(elf_import_record,0xa5,sizeof record);
  C(invoke()==1);C(selected_range==(version==6?2U:3U)&&selected_bytes==bytes);
  C(!memcmp(elf_import_record,record,bytes));
  for(unsigned i=bytes;i<sizeof record;i++)C(elf_import_record[i]==0xa5);
  C(!memcmp(family_request,request,40));
  C(!memcmp(family_request+48,(unsigned char*)request+48,n-48));
  C(*(uint64_t*)(family_request+40)==profile[1]);
  record[bytes-1]=1;C(invoke()==-22);record[bytes-1]=0;
 }
 puts("large_periodic_snapshot_OK");return 0;
}
'''
        build_actual(asm, c, 'large_periodic_snapshot')

    def test_admission_and_attenuation(self):
        source = (ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        pure = source.split('; Pinned profile-v1')[0]
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                asm = ('BITS 64\n%define REIST_NATIVE_WIDE 1\n'
                       '%define REIST_NATIVE_LARGE_IMAGE 1\n'
                       '%define REIST_NATIVE_SERVICE_CPU 1\n'
                       '%define REIST_NATIVE_TASK_POOL 1\n')
                if enabled:
                    asm += '%define REIST_NATIVE_LARGE_PERIODIC 1\n'
                asm += 'section .text\n' + pure
                c = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define C(x) do { if(!(x)){printf("line %d\n",__LINE__);return 1;} } while(0)
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const void*);
extern int64_t __attribute__((sysv_abi)) family_cpu_attenuate64(const void*,uint64_t,uint64_t);
int main(void) {
 uint64_t q[10],saved[10];
 for(unsigned version=6;version<=8;version++) {
  unsigned periodic=version!=7;
  uint64_t initial[10]={version|((uint64_t)(periodic?80:64)<<32),1,0,
                       0x20000000,0,0x30000000,32,0x31000000,periodic?1000:0,0};
  memcpy(q,initial,sizeof q);memcpy(saved,q,sizeof q);
  C(family_request_admit64(q)==(version==8&&!ENABLED?-22:1));
  C(!memcmp(q,saved,sizeof q));
  if(version==8&&!ENABLED)continue;
  for(unsigned budget=1;budget<=32;budget++) {
   q[6]=budget;
   C(family_request_admit64(q)==1);
   for(unsigned parent=0;parent<=33;parent++) {
    int64_t expected=!periodic||(parent>=budget&&parent<=32)?1:-13;
    memcpy(saved,q,sizeof q);
    C(family_cpu_attenuate64(q,100,parent)==expected);
    C(!memcmp(q,saved,sizeof q));
    C(family_cpu_attenuate64(q,0,parent)==(periodic?-13:1));
    C(family_cpu_attenuate64(q,99,parent)==(periodic?-13:1));
    C(family_cpu_attenuate64(q,101,parent)==(periodic?-13:1));
   }
  }
  for(unsigned field=0;field<10;field++) {
   for(unsigned bit=0;bit<64;bit++) {
    memcpy(q,initial,sizeof q);q[field]^=1ULL<<bit;
    memcpy(saved,q,sizeof q);
    int64_t result=family_request_admit64(q);
    C(!memcmp(q,saved,sizeof q));
    if(field==2||field==4||(field==1&&bit>=32)||
       (field==6&&(q[6]==0||q[6]>32))||
       (periodic&&(field==8||field==9)))C(result==-22);
   }
  }
  memcpy(q,initial,sizeof q);q[0]=version|((uint64_t)(periodic?64:80)<<32);
  C(family_request_admit64(q)==-22);
  memcpy(q,initial,sizeof q);q[6]=0;C(family_request_admit64(q)==-22);
 }
 puts("large_periodic_OK");return 0;
}
'''.replace('ENABLED', str(int(enabled)))
                build_actual(asm, c, 'large_periodic')


if __name__ == '__main__':
    unittest.main()
