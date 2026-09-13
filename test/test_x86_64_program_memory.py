"""Execute the real wide-image producer and assembly, not a model kernel."""
from pathlib import Path
import sys, unittest, re, os, subprocess, uuid, struct
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'test'), str(ROOT/'scripts')]
import test_x86_64_task_frames as frame_tests

def build_actual(asm,c,label,check=None):
    frame_tests.suppress_windows_test_dialogs()
    folder=ROOT/'build/codex-agent/r83aj-memory'/('host-'+label+'-'+uuid.uuid4().hex)
    folder.mkdir(parents=True)
    env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
    def run(args,name,limit):
        result=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=limit,capture_output=True,text=True,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise AssertionError((result.stdout+result.stderr)[-3000:])
        return result.stdout
    (folder/'source.asm').write_text(asm,encoding='ascii');(folder/'source.c').write_text(c,encoding='ascii')
    run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',folder/'source.asm','-o',folder/'code.o'],'asm',90)
    for opt in ('-O0','-O2'):
        exe=folder/(opt+'.exe');out=folder/(opt+'-vectors');out.mkdir()
        run([frame_tests.find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
             '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',folder/'source.c',folder/'code.o','-o',exe],opt+'-build',90)
        if label+'_OK' not in run([exe,out] if check else [exe],opt+'-run',30):raise AssertionError('missing host proof')
        if check:check(out)

class ProgramMemoryTests(unittest.TestCase):
    def test_real_preparation_and_record_admission(self):
        asm = 'BITS 64\n%define REIST_NATIVE_WIDE 1\n%include "arch/x86_64/mm/native_layout.inc"\nsection .text\n'
        asm += (ROOT/'arch/x86_64/exec/boot_programs.inc').read_text().split('; END_PURE_ADMISSION')[0]
        asm += (ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        source = (ROOT/'userspace/sdk/lib/x86_64/image.c').read_text().replace(
            '<reist/x86_64/image.h>', '"'+(ROOT/'userspace/sdk/include/reist/x86_64/image.h').as_posix()+'"')
        harness = (ROOT/'test/x86_64_program_memory_host.c').read_text().replace(
            '#include "userspace/sdk/lib/x86_64/image.c"', source)
        import build_x86_64_boot_programs as producer
        def compare(out):
            for page in range(64):
                raw=bytearray(8192);raw[:16]=b'\x7fELF\x02\x01\x01'+bytes(9)
                struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x400000+page*4096,64,0,0,64,56,1,0,0,0)
                struct.pack_into('<II6Q',raw,64,1,5,4096,0x400000+page*4096,0,4096,4096,4096)
                raw[4096:]=bytes(i^page for i in range(256))*16
                if 7<=page<=15:
                    with self.assertRaises(ValueError):producer.prepare(raw,[],True)
                else:self.assertEqual((out/f'page-{page}.rnpg').read_bytes(),producer.prepare(raw,[],True))
        build_actual(asm,harness,'wide_image',compare)

    def mechanism(self,files,headers,c,label):
        asm='BITS 64\n%define REIST_NATIVE_WIDE 1\n%define X86_64_NATIVE_RAM 1\n'
        asm+='\n'.join('%include "'+f+'"' for f in files)
        c='#define REIST_NATIVE_WIDE 1\n'+''.join('#include "'+(ROOT/h).as_posix()+'"\n' for h in headers)+c
        build_actual(asm,c,label)

    def test_mapping_and_pointer_mechanisms(self):
        self.mechanism(['arch/x86_64/mm/address_space.asm','arch/x86_64/mm/user_access.asm'],
            ['arch/x86_64/mm/address_space.h','arch/x86_64/mm/user_access.h'],MAPPING,'wide_mapping')

    def test_context_and_identity_full_layout(self):
        # Reuse the actual existing behavioral vectors; independently move only
        # task-array context fields, never frame, generation or status indices.
        c=(ROOT/'test/x86_64_context_host.c').read_text().split('\n',1)[1]
        c=c.replace('task[32]','task[128]').replace('i<32','i<128')
        c=re.sub(r'task\[(\d+)\]',lambda m:'task['+str(int(m[1])+56 if 12<=int(m[1])<=31 else int(m[1]))+']',c)
        c=c.replace('task[target[i]]','task[target[i]+56]')
        c=c.replace('0x400001000','0x400008000').replace('offset<=4096','offset<=32768')
        c=c.replace('X86_64_CONTEXT_HOST_OK','wide_context_OK')
        self.mechanism(['arch/x86_64/proc/context_core.asm'],['arch/x86_64/proc/context_core.h'],c,'wide_context')
        c=(ROOT/'test/x86_64_identity_host.c').read_text().split('\n',1)[1]
        c=c.replace('tasks[64][32]','tasks[64][128]').replace('i<32','i<128').replace('field<32','field<128')
        c=c.replace('t[12]','t[68]').replace('t[13]','t[69]')
        c=re.sub(r'\b(i|field)<12\b',r'\1<68',c)
        c=c.replace('X86_64_IDENTITY_HOST_OK','wide_identity_OK')
        self.mechanism(['arch/x86_64/proc/identity_core.asm'],['arch/x86_64/proc/identity_core.h'],c,'wide_identity')

    def test_exact_stack_top_and_full_profile_overlap(self):
        scheduler=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body=scheduler.split('; BEGIN_PURE_NATIVE_MEMORY_ADAPTERS',1)[1].split('; END_PURE_NATIVE_MEMORY_ADAPTERS',1)[0]
        asm='BITS 64\n%define REIST_NATIVE_WIDE 1\n%define X86_64_NATIVE_RAM 1\n%include "arch/x86_64/mm/memory_profile.inc"\nsection .text\nglobal native_stack_top64,native_profile_ranges64\n'+body
        c=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t __attribute__((sysv_abi)) native_stack_top64(void*);
extern uint64_t __attribute__((sysv_abi)) native_profile_ranges64(void*,unsigned);
#define C(x) do{if(!(x)){printf("adapter line %d\n",__LINE__);return 1;}}while(0)
int main(void){
 _Alignas(16) uint64_t task[128]={0},binding[6]={0},profile[4]={0};
 task[3]=0x100000000ULL;
 C(native_stack_top64(task)==0x409000);
 for(unsigned mask=0;mask<128;mask++){
  for(unsigned i=0;i<7;i++)task[13+i]=(mask&(1<<i))?0x100001000ULL+i*4096:0;
  uint64_t before[128];memcpy(before,task,sizeof task);
  C(native_stack_top64(task)==(mask==0?0x409000:mask==127?0x410000:0));
  C(!memcmp(task,before,sizeof task));
 }
 task[19]=task[13];C(!native_stack_top64(task));task[19]=0x100007000ULL;
 task[11]=0x100010000ULL;C(!native_stack_top64(task));task[11]=0;
 task[12]=task[3];C(!native_stack_top64(task));task[12]=0;
 C(!native_stack_top64((void*)(UINTPTR_MAX-7)));
 binding[0]=(uintptr_t)task;binding[1]=(uintptr_t)profile;
 for(unsigned kind=1;kind<=2;kind++){
  C(native_profile_ranges64(binding,kind)==1);
  for(unsigned offset=0;offset<1024;offset+=8){
   binding[1]=(uintptr_t)task+offset;C(!native_profile_ranges64(binding,kind));
  }
  binding[1]=(uintptr_t)profile;
  C(!native_profile_ranges64((void*)(UINTPTR_MAX-7),kind));
 }
 puts("wide_adapters_OK");return 0;
}
'''
        build_actual(asm,c,'wide_adapters')

    def test_claim_oom_every_acquisition(self):
        self.mechanism(['arch/x86_64/mm/frame_claim.asm'],['arch/x86_64/mm/frame_claim.h'],LEDGER+r'''
int main(void){
 for(unsigned count=1;count<=69;count++)for(unsigned fail=0;fail<=count;fail++){
  struct reist_x64_frame_claim c={0};reset();fail_at=fail;
  long long result=reist_x64_frame_claim_begin(&c,count);
  if(fail<count){C(result==-12);C(!memcmp(&c,&(struct reist_x64_frame_claim){0},sizeof c));C(frees==fail);}
  else {C(result==1 && c.count==count);for(unsigned i=0;i<count;i++)C((uint64_t)reist_x64_frame_claim_take(&c)==FRAME(i));C(reist_x64_frame_claim_abort(&c)==1 && !frees);}
 }
 struct reist_x64_frame_claim c={0};reset();C(reist_x64_frame_claim_begin(&c,69)==1);
 c.frames[68]=c.frames[0];C(reist_x64_frame_claim_abort(&c)==-4096 && !frees);
 c.frames[68]=FRAME(68);C(reist_x64_frame_claim_abort(&c)==1 && frees==69);
 C(reist_x64_frame_claim_abort(&c)==1 && frees==69);
 puts("wide_claim_OK");return 0;
}
''','wide_claim')

    def test_image_and_task_release_every_slot(self):
        self.mechanism(['arch/x86_64/exec/image_frames.asm'],['arch/x86_64/exec/image_frames.h'],LEDGER+r'''
int main(void){
 for(unsigned bad=0;bad<64;bad++){
  ReistX64Image image={0};reset();
  for(unsigned i=0;i<64;i++){image.frames[i]=FRAME(i);image.flags[i]=4;live[i]=1;}
  image.active=1;image.entry=0x410000;image.executable=1;
  image.frames[bad]|=1;ReistX64Image before=image;
  C(!reist_x64_image_release(&image) && !frees && !memcmp(&before,&image,sizeof image));
  image.frames[bad]&=~1ULL;C(reist_x64_image_release(&image)==1 && frees==64);
  for(unsigned i=0;i<64;i++)C(!image.frames[i] && !image.flags[i] && !live[i]);
  C(!image.active && !image.entry);C(reist_x64_image_release(&image)==1 && frees==64);
 }
 puts("wide_image_release_OK");return 0;
}
''','wide_image_release')
        self.mechanism(['arch/x86_64/mm/task_frames.asm'],['arch/x86_64/mm/task_frames.h'],LEDGER+r'''
int main(void){
 for(unsigned bad=0;bad<69;bad++){
  uint64_t frames[64],stack,tables[4],cr3;reset();
  for(unsigned i=0;i<64;i++)frames[i]=FRAME(i);
  stack=FRAME(64);for(unsigned i=0;i<4;i++)tables[i]=FRAME(68-i);
  cr3=tables[0];for(unsigned i=0;i<69;i++)live[i]=1;
  ReistX64TaskFrames binding={frames,&stack,tables,&cr3};
  uint64_t *p=bad<64?frames+bad:bad==64?&stack:tables+68-bad;
  *p|=1;C(!reist_x64_task_frames_release(&binding) && !frees);*p&=~1ULL;
  C(reist_x64_task_frames_release(&binding)==1 && frees==69 && !cr3 && !stack);
  for(unsigned i=0;i<64;i++)C(!frames[i]);for(unsigned i=0;i<4;i++)C(!tables[i]);
  C(reist_x64_task_frames_release(&binding)==1 && frees==69);
 }
 puts("wide_task_release_OK");return 0;
}
''','wide_task_release')

LEDGER=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define C(x) do{if(!(x)){printf("ledger line %d\n",__LINE__);exit(1);}}while(0)
#define FRAME(i) (0x100000000ULL+(i)*4096ULL)
static unsigned live[69],allocs,frees,fail_at;
static void reset(void){memset(live,0,sizeof live);allocs=frees=0;fail_at=70;}
uint64_t __attribute__((sysv_abi)) physical_frame_alloc64(void){
 if(allocs==fail_at)return 0;C(allocs<69);live[allocs]=1;return FRAME(allocs++);
}
unsigned __attribute__((sysv_abi)) physical_free_frame_count64(void){return 1000+frees;}
int __attribute__((sysv_abi)) physical_frame_free64(uint64_t frame){
 C(frame>=FRAME(0) && frame<FRAME(69) && !(frame&4095));unsigned i=(unsigned)((frame-FRAME(0))/4096);
 C(live[i]);live[i]=0;++frees;return 1;
}
'''

MAPPING=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define C(x) do{if(!(x)){printf("mapping line %d\n",__LINE__);exit(1);}}while(0)
#define F(i) (0x100000000ULL+(i)*4096ULL)
#define NX (1ULL<<63)
static _Alignas(4096) uint64_t pages[133][512],saved[133][512];
static unsigned calls,fail_at;
void *__attribute__((sysv_abi)) reist_x64_mapping_pointer64(uint64_t frame){
 C(frame>=F(0) && frame<F(133) && !(frame&4095));++calls;
 if(calls==fail_at)return 0;return pages[(frame-F(0))/4096];
}
static ReistX64AddressPlan plan;
static void setup(unsigned page,unsigned flags){
 memset(pages,0,sizeof pages);memset(&plan,0,sizeof plan);calls=fail_at=0;
 for(unsigned i=0;i<4;i++)plan.tables[i]=F(i);
 plan.stack=F(132);plan.kernel_entries[0]=NX|0x2003;plan.kernel_entries[1]=0x3003;
 plan.source[page]=F(4+page);plan.flags[page]=flags;
 if(flags==6)plan.private_frames[page]=F(68+page);
 for(unsigned i=0;i<512;i++)pages[4+page][i]=0x1234567800000000ULL+i;
}
int main(void){
 for(unsigned page=0;page<64;page++)for(unsigned flags=4;flags<=6;flags++){
  setup(page,flags);ReistX64AddressPlan before=plan;memcpy(saved,pages,sizeof pages);
  int ok=reist_x64_address_space_build(&plan);
  C(ok==(page!=8));C(!memcmp(&before,&plan,sizeof plan));
  if(page==8){C(!calls && !memcmp(saved,pages,sizeof pages));continue;}
  C(pages[0][0]==(F(1)|7) && pages[1][0]==(F(2)|7) && pages[2][2]==(F(3)|7));
  for(unsigned i=0;i<512;i++){
   uint64_t expected=i==8?(F(132)|7|NX):i==page?((flags==6?F(68+page):F(4+page))|5|(flags==6?2:0)|(flags==5?0:NX)):0;
   C(pages[3][i]==expected);
  }
  C(!memcmp(pages[4+page],saved[4+page],4096));
  if(flags==6)C(!memcmp(pages[68+page],saved[4+page],4096));
  uint64_t task[128]={2,42,F(0),F(132)};
  if(flags==6)task[4+page]=F(68+page);
  ReistX64UserAccess binding={task,plan.tables,42,F(0)};
  int expect=(page<9 || page>15 || flags==6);
  C(reist_x64_user_access(&binding,0x400000+page*4096,1,4)==(expect?1:-4096));
  if(expect){
   C(reist_x64_user_access(&binding,0x400000+page*4096,1,1)==(flags==5));
   C(reist_x64_user_access_bulk(&binding,0x400000+page*4096,1040,2)==(flags==6));
  }
  memcpy(saved,pages,sizeof pages);calls=0;C(!reist_x64_address_space_build(&plan));C(!memcmp(saved,pages,sizeof pages));
 }
 for(unsigned stop=1;stop<=7;stop++){
  setup(63,6);memcpy(saved,pages,sizeof pages);fail_at=stop;
  C(!reist_x64_address_space_build(&plan));C(!memcmp(saved,pages,sizeof pages));
 }
 setup(63,6);plan.private_frames[63]=plan.source[63];memcpy(saved,pages,sizeof pages);
 C(!reist_x64_address_space_build(&plan) && !calls && !memcmp(saved,pages,sizeof pages));
 puts("wide_mapping_OK");return 0;
}
'''

if __name__ == '__main__': unittest.main()
