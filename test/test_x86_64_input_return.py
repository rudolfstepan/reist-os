"""Execute actual input return assembly and accepted shared burst core."""
from pathlib import Path
import unittest,subprocess,tempfile
from test_x86_64_program_memory import build_actual
import test_x86_64_query_return as query_tests
ROOT=Path(__file__).resolve().parents[1]

def body(source):
 return source.split('\n.result:\n',1)[1].split('\nnative_input_terminal64:',1)[0]

def assembly(code,enabled):
 return ('BITS 64\n'+('%define REIST_NATIVE_DESKTOP_CPU 1\n' if enabled else '')+r"""
section .text
global probe
probe:
 mov r8,rdi
 mov r9,rsi
 lea rdi,[rel native_input_request]
 mov ecx,8
 mov rax,-1
 rep stosq
 mov [rel native_input_request+8],r8d
 mov rax,r9
"""+code+r"""
query_resume64:
 mov qword [rel route],1
 ret
process_run_resume64:
 mov qword [rel route],0
 ret
section .bss
alignb 8
global native_input_request,route
native_input_request: resq 8
route: resq 1
""")

class InputReturnTests(unittest.TestCase):
 def test_actual_read_return(self):
  c=r"""
#include <stdint.h>
#include <stdio.h>
extern int64_t __attribute__((sysv_abi)) probe(uint64_t,int64_t);
extern uint64_t native_input_request[8],route;
int main(void){
 const int64_t values[]={INT64_MIN,-122,-116,-110,-84,-22,-14,-13,-11,-9,-1,0,1,2,255,256,65535,65536,65537,INT64_MAX};
 const uint32_t ops[]={0,1,2,3,4,5,6,UINT32_MAX};
 for(unsigned o=0;o<sizeof(ops)/sizeof(*ops);o++)for(unsigned v=0;v<sizeof(values)/sizeof(*values);v++){
  int64_t r=values[v];
  if(probe(ops[o],r)!=r)return 1;
  unsigned expected=ENABLED && ops[o]==3 && (r==-11 || (r>=1 && r<=65536));
  if(route!=expected)return 2;
  for(unsigned n=0;n<8;n++)if(native_input_request[n])return 3;
 }
 puts("INPUT_RETURN_OK");return 0;
}
"""
  source=body((ROOT/'arch/x86_64/devices/input_domain.inc').read_text())
  for enabled in (False,True):build_actual(assembly(source,enabled),'#define ENABLED '+str(int(enabled))+'\n'+c,'INPUT_RETURN')
 def test_disabled_byte_exact(self):
  path='arch/x86_64/devices/input_domain.inc'
  old=body(subprocess.check_output(['git','show','f5ebfb0d:'+path],cwd=ROOT).decode().replace('\r\n','\n'))
  new=body((ROOT/path).read_text())
  folder=ROOT/'build/codex-agent/r83ci-input-return';folder.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=folder) as temp:
   binaries=[]
   for i,code in enumerate((old,new)):
    src=Path(temp)/str(i);src.write_text(assembly(code,False))
    output=src.with_suffix('.o')
    subprocess.run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',str(src),'-o',str(output)],check=True,timeout=30,capture_output=True)
    binaries.append(output.read_bytes())
   self.assertEqual(*binaries)
 def test_shared_burst_and_adapter(self):
  original=query_tests.QueryReturnTests()
  original.test_actual_budget();original.test_actual_return_adapter()

 def test_frame_scan_differential(self):
  import base64,zlib
  captured=zlib.decompress(base64.b64decode('eJzt3btu02AYh/EvTQ9BgmK4Ag+I2UIMIBiMkCrE5IEBsWCJcznI4go8MoBkcQW+BF8Agy+AwTMLHiuQkLt0o0GNnxdI2uKotVTR/J/lR2zizxHQ9K1bM3BtA3TJsP11sPpnWx8VHLfECmts0C23enhS+awfYIgRxphgihnmWGCJFdbY2Otc4XWjjwGGGGGMCaaYYY4FllhhjQ06/rw99Hv+81dKKfVf9eXyrYnB93DixlK7PWW/hwn73e7tCV3vHW8/TD/+OB6PD9o+mFnHzsfOQymllFJKKaWUUkoppZRS+1vFc7Yhvcb15uv9Xv8tOW6FNTboWM9Dv2P9oOfzU0oppdTv7i+319vDnenr//d228dbw/ZxMg6ntg/tE4tDOoN77+HvnXN3OP72nOej6/9KKaXU0bO36XXbkN7g+8tv9jz/c9wKa2zQsZ6Hfs/rn3QBryfE6JS9PqWUUqeqctjO2+WP6fn/887B879tX+qY//cOc3b01zocf33O89H8r5RSSh09exs9bxu8R8ypz/udTyOOG2OCKWaYY4FKLWIlf/8rrLGxfxeP+XoZ+hhgiBHGmGCKGeZYYIkV1tige8L66GOAIUYYY4IpZphjgSVWWGOD7inro48BhhhhjAmmmGGOBZZYYY0Numesjz4GGGKEMSaYYoY5FlhihTU26Pj47KGPQc8ft9VC92BzY2L0dXr+H42mf8bf9s+bPffdVvu8aPvfz7f7Atj5aP5XSimljt7qzP11XPqCz0s3e77+z3ErrLFBx3oe+h3rB+wPMcIYE0x7fh1KKaXUAvRw0F5vT3/OzP8zv8/2W1c6jruCd5nr996jwzmeZ+ej+V8ppZQ6/vx/wTbkL7kO9arfubnmuA06ju+hjwGGHetH7I8xwRQzzHt+HUoppdQC9GmtnbfdzPy/xpuqzese+y+h7Z+3b9z/39bpOh/N/0oppdTx5/+LtqF8zXX6Nz3PzRzPQx8DDDHCuGP9hP0pZphjgWXfr0MppZQ6/dm87c1e/5+Z/332X0Xbf2jcN2Df/D/n+Wj+V0oppY5RMmSOxgxz7Mr+v4AMcyzQ7ieYYY4F2v0GfAzs/gN2fwD7eQTMsbDH9v0KWGJlj+3rGVhjg177lY9fAHD3sg=='))
  self.assertEqual(len(captured),33032)
  path='arch/x86_64/proc/process_run.inc'
  old=subprocess.check_output(['git','show','b6a7eeb2:'+path],cwd=ROOT).decode().replace('\r\n','\n')
  current=(ROOT/path).read_text()
  def scan(source):return source[source.index('process_run_frames64:'):source.index('; Trusted caller pointer is pinned')]
  # Source outside the approved collision scan stays byte-for-byte unchanged.
  def outside(source):
   a=source.index('    ; A collision proves nothing:')
   b=source.index('%else\n    xor edx, edx',a)
   return source[:a]+source[b:]
  self.assertEqual(outside(old),outside(current))
  asm="""BITS 64
%define REIST_NATIVE_WIDE 1
%define REIST_NATIVE_LARGE_IMAGE 1
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_DESKTOP_CPU 1
%define REIST_NATIVE_LARGE_PERIODIC 1
%define X86_64_NATIVE_RAM 1
%include "arch/x86_64/mm/memory_profile.inc"
TASK_STATE equ 0
TASK_FREE equ 0
TASK_CR3 equ 16
TASK_STACK_FRAME equ 24
TASK_PRIVATE_FRAMES equ 32
PAGE_SIZE equ 4096
extern scheduler_tasks,scheduler_table_frames,scheduler_original_cr3
section .bss
alignb 16
global scan_stack
scan_stack: resb 32768
saved_rsp: resq 1
section .text
"""
  # Disabled large-pool profile retains the original complete scan bytes.
  with tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent/r83ci-input-return') as temp:
   objects=[]
   for index,source in enumerate((old,current)):
    path=Path(temp)/str(index);path.write_text(asm.replace('%define REIST_NATIVE_DESKTOP_CPU 1\n','')+scan(source))
    output=path.with_suffix('.o')
    subprocess.run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',str(path),'-o',str(output)],check=True,capture_output=True,timeout=30)
    objects.append(output.read_bytes())
   self.assertEqual(*objects)
  for name,source in (('baseline',old),('candidate',current)):
   asm+='global '+name+'\n'+name+':\n push rbp\n push rbx\n push r12\n push r13\n push r14\n push r15\n mov [rel saved_rsp],rsp\n lea rsp,[rel scan_stack+32768]\n call '+name+'_core\n mov rsp,[rel saved_rsp]\n pop r15\n pop r14\n pop r13\n pop r12\n pop rbx\n pop rbp\n ret\n'
   asm+=scan(source).replace('process_run_frames64:',name+'_core:')
  c='static const unsigned char captured[]={'+','.join(str(v) for v in captured)+'};\n'+r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
uint64_t scheduler_tasks[8][512],scheduler_table_frames[8][4],scheduler_original_cr3=0x1000;
extern unsigned char scan_stack[32768];
extern int __attribute__((sysv_abi)) baseline(void),candidate(void);
static uint64_t saved_tasks[8][512],saved_tables[8][4];
#define CHECK(x) do{if(!(x)){printf("line%d %s\n",__LINE__,#x);return 1;}}while(0)
static uint64_t *frame(unsigned n){unsigned s=n/261,i=n%261;return i<256?&scheduler_tasks[s][4+i]:i==256?&scheduler_tasks[s][3]:&scheduler_table_frames[s][i-257];}
static void init(unsigned live,unsigned sparse){
 memset(scheduler_tasks,0,sizeof(scheduler_tasks));memset(scheduler_table_frames,0,sizeof(scheduler_table_frames));scheduler_original_cr3=0x1000;
 for(unsigned n=0;n<live*261;n++)*frame(n)=sparse && n%261<256 && n%3?0:0x100000000ULL+(n+1)*4096ULL;
 for(unsigned n=0;n<live;n++){scheduler_tasks[n][0]=2;scheduler_tasks[n][2]=scheduler_table_frames[n][0];}
}
static int verify(int expected){
 memcpy(saved_tasks,scheduler_tasks,sizeof(saved_tasks));memcpy(saved_tables,scheduler_table_frames,sizeof(saved_tables));
 for(unsigned n=0;n<2;n++){
  memset(scan_stack,0xa5,32768);CHECK((n?candidate():baseline())==expected);
  CHECK(!memcmp(saved_tasks,scheduler_tasks,sizeof(saved_tasks)) && !memcmp(saved_tables,scheduler_table_frames,sizeof(saved_tables)));
  for(unsigned k=0;k<32768-80;k++)CHECK(scan_stack[k]==0xa5);
 }
 return 0;
}
int main(void){
 for(unsigned live=0;live<=8;live++)for(unsigned sparse=0;sparse<2;sparse++){init(live,sparse);CHECK(!verify(1));}
 unsigned boundaries[]={0,1,254,255,256,257,258,259,260,261,515,516,517,518,519,520,521,1827,2082,2083,2084,2085,2086,2087};
 for(unsigned a=0;a<sizeof(boundaries)/sizeof(*boundaries);a++)for(unsigned b=a+1;b<sizeof(boundaries)/sizeof(*boundaries);b++){
  init(8,0);unsigned n=boundaries[b];*frame(n)=*frame(boundaries[a]);if(n%261==257)scheduler_tasks[n/261][2]=*frame(n);CHECK(!verify(0));
 }
 for(unsigned n=0;n<5;n++){init(8,0);*frame(2087)=(uint64_t[]){0,1,0x1000,0x400000000ULL,0x100000001ULL}[n];CHECK(!verify(0));}
 init(7,0);*frame(2087)=0x2000;CHECK(!verify(0));
 init(8,0);scheduler_tasks[7][2]^=4096;CHECK(!verify(0));
 memcpy(scheduler_tasks,captured,32768);memcpy(scheduler_table_frames,captured+32768,256);memcpy(&scheduler_original_cr3,captured+33024,8);CHECK(!verify(1));
 for(unsigned n=0;n<2;n++){clock_t t=clock();for(unsigned k=0;k<1000;k++)CHECK((n?candidate():baseline())==1);printf("FRAME_SCAN_TIMING %s seconds=%.6f\n",n?"candidate":"baseline",(double)(clock()-t)/CLOCKS_PER_SEC);}
 puts("INPUT_FRAME_SCAN_OK");return 0;
}
"""
  build_actual(asm,c,'INPUT_FRAME_SCAN')

if __name__=='__main__':unittest.main()
