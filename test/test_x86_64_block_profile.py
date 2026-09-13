"""Actual profile and wide PIO adapter behavior, not a simulated kernel."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class BlockProfileTests(unittest.TestCase):
    def test_actual_task_binding_and_finish(self):
        source=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
        binding=source.split('.buffer_ready:\n',1)[1].split('\n.invoke:',1)[0]
        state='native_pio_state_admit64:'+source.split('native_pio_state_admit64:',1)[1].split('; State64:',1)[0]
        finish='native_pio_finish64:'+source.split('native_pio_finish64:',1)[1].split('native_pio_emergency_fence64:',1)[0]
        for wide in (False,True):
            folder=ROOT/'build/codex-agent/r83ak-block-profile'/('pio-host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
            asm=('BITS 64\n'+('%define REIST_NATIVE_WIDE 1\n' if wide else '')+
                 '%include "arch/x86_64/mm/native_layout.inc"\nTASK_STATE equ 0\nTASK_GENERATION equ 8\n'
                 'TASK_FREE equ 0\nTASK_READY equ 1\nTASK_BLOCKED equ 6\nsection .text\n'
                 'global profile_binding,profile_finish\nprofile_binding:\n push r12\n'
                 ' lea r12,[rel scheduler_tasks]\n call binding\n pop r12\n ret\nbinding:\n'+binding+
                 '\n.invoke:\n mov rax,r8\n ret\nprofile_finish:\n jmp native_pio_finish64\n'
                 'native_pio_fail64:\n mov rax,-84\n ret\n'+state+finish+
                 '\nsection .bss\nalign 16\nglobal scheduler_tasks,family_records,native_pio_request,native_pio_state,scheduler_current_slot\n'
                 'scheduler_tasks: resb NATIVE_TASK_BYTES*4\nfamily_records: resb 256\nnative_pio_request: resb 64\n'
                 'native_pio_state: resb 64\nscheduler_current_slot: resd 1\n')
            (folder/'source.asm').write_text(asm,encoding='ascii')
            words=128 if wide else 32
            c=PIO_HOST.replace('@WORDS@',str(words));(folder/'source.c').write_text(c,encoding='ascii')
            env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
            commands=[('asm',['C:/tools/nasm-3.02/nasm.exe','-f','win64',folder/'source.asm','-o',folder/'code.o'])]
            for opt in ('-O0','-O2'):
                exe=folder/(opt+'.exe');commands.extend([(opt+'-build',[find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-fno-sanitize=all',
                    '-Wno-unused-command-line-argument','-Wall','-Wextra','-Werror',folder/'source.c',folder/'code.o','-o',exe]),(opt+'-run',[exe])])
            suppress_windows_test_dialogs()
            for phase,command in commands:
                result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,
                    timeout=30 if phase.endswith('run') else 90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(phase+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-2500:])
                if phase.endswith('run'):self.assertIn('PROFILE_PIO_ADAPTER_OK',result.stdout)

    def test_actual_profile_service(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ak-block-profile'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            for phase,command in (
                ('build',[find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                    '-fno-sanitize=all','-ffreestanding','-fno-builtin','-Wall','-Wextra','-Werror',
                    '-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                    ROOT/'test/x86_64_block_profile_host.c','-o',exe]),('run',[exe])):
                result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,
                    timeout=90 if phase=='build' else 30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(opt+'-'+phase+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-2500:])
                if phase=='run':self.assertIn('NATIVE_BLOCK_PROFILE_OK',result.stdout)

PIO_HOST=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define WORDS @WORDS@
extern uint64_t scheduler_tasks[4][WORDS],family_records[4][8],native_pio_request[8],native_pio_state[8];
extern uint32_t scheduler_current_slot;
extern int64_t __attribute__((sysv_abi)) profile_binding(void),profile_finish(void);
#define C(x) do{if(!(x)){printf("PIO adapter line %d\n",__LINE__);return 1;}}while(0)
static void empty(void){memset(scheduler_tasks,0,sizeof(scheduler_tasks));memset(family_records,0,sizeof(family_records));
 memset(native_pio_request,0,64);memset(native_pio_state,0,64);scheduler_current_slot=0;
 scheduler_tasks[0][1]=9;native_pio_request[1]=1;native_pio_state[1]=UINT64_MAX;native_pio_state[2]=1;}
int main(void){
 for(unsigned old=2;old<4;old++)for(unsigned target=2;target<4;target++)for(unsigned state=0;state<8;state++){
  empty();native_pio_state[0]=(3ULL<<32)|old;native_pio_state[1]=~native_pio_state[0];
  scheduler_tasks[old][0]=1;scheduler_tasks[old][1]=3;
  scheduler_tasks[target][0]=state;scheduler_tasks[target][1]=11;
  native_pio_request[2]=(11ULL<<32)|target;family_records[target][1]=9ULL<<32;
  unsigned retired=old==target;unsigned live=state==1||state==6;
  uint64_t before[4][WORDS];memcpy(before,scheduler_tasks,sizeof(before));
  C(profile_binding()==(int64_t)(retired|(live?2:0)));C(!memcmp(before,scheduler_tasks,sizeof(before)));
  family_records[target][1]^=1;C(profile_binding()==retired);
  family_records[target][1]^=1;scheduler_tasks[target][1]=12;C(profile_binding()==retired);
 }
 for(unsigned slot=2;slot<4;slot++)for(unsigned state=0;state<8;state++){
  empty();scheduler_tasks[slot][0]=state;uint64_t before[8];memcpy(before,native_pio_state,64);
  int64_t result=profile_finish();
  if(state){C(result==-84);C(!memcmp(before,native_pio_state,64));}
  else{C(native_pio_state[0]==0 && native_pio_state[1]==UINT64_MAX && native_pio_state[2]==1);}
 }
 empty();native_pio_state[1]=0;C(profile_finish()==-84 && native_pio_state[1]==0);
 puts("PROFILE_PIO_ADAPTER_OK");return 0;
}
'''

if __name__=='__main__':unittest.main()
