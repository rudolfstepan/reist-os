"""Execute actual frame gates against frozen predecessor; never time-based safety."""
from pathlib import Path
import base64,hashlib,json,re,struct,subprocess,sys,unittest,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
from test_x86_64_program_memory import build_actual
import diagnose_x86_64_block_profile as diagnostic

# Pinned actual baseline capture; hosts remain runnable without ignored evidence.
# Origin: r83ak-block-profile/diagnostic/baseline/snapshot.json (13 Sep2026).
CAPTURE_B64='eJztmMtqwzAQRf9F6yxGD+vhv5EfKqGmhbq70n8vsdPWum4CxqYVdM4mORiNNJMhI/wm2jgMo6i1Ponnl/PD+SkOopayCtL6k3iNzdCPohZEPU3I+YMogV+/f7kEt0Rq6Q7cgwfwflqS7Z/5HCLbP/N9iEstxsepFBhytQWWqoNSlIaC82lwA16tf9rMHbjfmX+A9RG8AW8LrzfznwkdObPoTUUpmsVzY6c/vjU3+tnCegTj76XxqV/Gc1vjYx6f2eqf63OzHgzzF1jwVXfiVUfOvV3sPIpw3ga8Be/WV7PMEzgVnj/D/B7RES3nm/Up3Zv/MtyP5yhfj9gjh/8RqG314fnPFAV24/Xe+g2+qoiHvoo4HgXn0+AGvAK34A7cb8w/FF4vhtlHNv9xfiuedwzDMAzDMAxDhSDePwCkjUol'
def captured_snapshot():
    raw=zlib.decompress(base64.b64decode(CAPTURE_B64))
    if hashlib.sha256(raw).hexdigest()!='0aa26df19859ef34fae1cd81012d4bc5a1ef9274a0b904460c291da81461f60f':raise ValueError('pinned capture hash')
    return json.loads(raw)

def body(source):
    return re.search(r'^process_run_frames64:\n.*?(?=^global |^[A-Za-z_]\w*:)',source,re.M|re.S)[0]

class FrameCostTests(unittest.TestCase):
    def test_diagnostic_snapshot_admission(self):
        s=captured_snapshot()
        text='FRAME_COST_SNAPSHOT '+json.dumps(s)
        self.assertEqual(diagnostic.snapshot(text),s)
        for bad in ('',text+'\n'+text,text.replace('"calls":','"extra":')):
            with self.assertRaises(ValueError):diagnostic.snapshot(bad)
        for key,value in (('original',0),('calls',4097),('tasks','00'),('tables','00')):
            bad=dict(s);bad[key]=value
            with self.assertRaises(ValueError):diagnostic.snapshot('FRAME_COST_SNAPSHOT '+json.dumps(bad))

    def test_actual_differential_and_comparison_bound(self):
        old=subprocess.check_output(['git','show','61efea3d:arch/x86_64/proc/process_run.inc'],cwd=ROOT,text=True,timeout=15)
        current=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        captured=captured_snapshot()
        c=(ROOT/'test/x86_64_frame_cost_host.c').read_text()
        for wide in (False,True):
            asm='BITS 64\n'+('%define REIST_NATIVE_WIDE 1\n' if wide else '')
            asm+='%define X86_64_NATIVE_RAM 1\n%include "arch/x86_64/mm/memory_profile.inc"\n'
            asm+='TASK_SLOT_CAPACITY equ 4\nTASK_FREE equ 0\nTASK_STATE equ 0\nTASK_CR3 equ 16\nTASK_STACK_FRAME equ 24\nTASK_PRIVATE_FRAMES equ 32\nPAGE_SIZE equ 4096\nsection .text\n'
            for name,source in (('baseline',old),('candidate',current)):
                code=body(source).replace('process_run_frames64:',name+'_core:')
                needle='    cmp [rsp+rdx*8], rax'
                self.assertEqual(code.count(needle),1)
                code=code.replace(needle,'    inc qword [rel '+name+'_comparisons]\n'+needle)
                asm+='global '+name+'\n'+name+':\n push rbx\n push r12\n push r13\n call '+name+'_core\n pop r13\n pop r12\n pop rbx\n ret\n'+code
            asm+='section .bss\nalign 16\nglobal scheduler_tasks,scheduler_table_frames,scheduler_original_cr3,baseline_comparisons,candidate_comparisons\nscheduler_tasks: resb 4096\nscheduler_table_frames: resb 128\nscheduler_original_cr3: resq 1\nbaseline_comparisons: resq 1\ncandidate_comparisons: resq 1\n'
            values=struct.unpack('<512Q',bytes.fromhex(captured['tasks']))
            tables=struct.unpack('<16Q',bytes.fromhex(captured['tables']))
            prefix=f'#define WIDE {int(wide)}\nstatic const unsigned long long captured_tasks[512]={{'+','.join(str(v)+'ULL' for v in values)+'};\n'
            prefix+='static const unsigned long long captured_tables[16]={'+','.join(str(v)+'ULL' for v in tables)+'};\n'
            prefix+=f'#define CAPTURED_ROOT {captured["original"]}ULL\n'
            build_actual(asm,prefix+c,'frame_cost')

if __name__=='__main__':unittest.main()
