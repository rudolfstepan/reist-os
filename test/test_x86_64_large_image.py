"""Large prepared image behavior; old profiles remain separately bounded."""
from pathlib import Path
import os,subprocess,sys,struct,unittest,uuid,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
class LargeImageTests(unittest.TestCase):
    def test_large_boot_area_requires_explicit_selection(self):
        import build_x86_64_c_payload as payload
        base=ROOT/'build/codex-agent/r83bu-large-image'
        def artifacts(name):
            folder=base/name/'x86_64'
            return ((folder/'reist-x86_64-c-core.elf').read_bytes(),
                    (folder/'reist-x86_64-bootstrap.elf').read_bytes())
        inner,outer=artifacts('build03')
        payload.verify_outer(inner,outer,large_image=True)
        with self.assertRaises(ValueError):payload.verify_outer(inner,outer)
        inner,outer=artifacts('baseline01')
        payload.verify_outer(inner,outer)
        with self.assertRaises(ValueError):payload.verify_outer(inner,outer,large_image=True)

    def test_actual_large_mapping_and_rollback(self):
        self.run_mechanism_vectors('test_mapping_and_pointer_mechanisms',
            {64:256,68:260,128:512,132:516,133:517})

    def test_actual_large_claim_every_oom(self):
        self.run_mechanism_vectors('test_claim_oom_every_acquisition',
            {64:256,68:260,69:261,70:262})

    def test_actual_large_release_every_slot(self):
        self.run_mechanism_vectors('test_image_and_task_release_every_slot',
            {64:256,68:260,69:261,70:262})

    def test_actual_large_context_and_identity(self):
        self.run_mechanism_vectors('test_context_and_identity_full_layout',{})

    def test_raw_replay_and_corruption_rejection(self):
        from unittest.mock import patch
        import run_qemu_x86_64_large_image as runtime
        folder=ROOT/'build/codex-agent/r83bu-large-image/diagnostic06'
        serial=(folder/'serial.txt').read_text();trace=(folder/'trace.txt').read_text()
        self.assertEqual(len(runtime.replay(folder,serial,trace,52)),8)
        original=Path.read_bytes;raw=(folder/'reads.bin').read_bytes()
        import json
        records=[json.loads(line) for line in (folder/'reads.jsonl').read_text().splitlines()]
        offsets=[];kind=None;reads=[]
        wanted={'boot':1056768,'start':4096,'copy':1052960,'syscall':4096,'release_end':4096,'finish':16384}
        for row in records:
            if 'begin' in row:kind=row['begin'];reads=[]
            if 'bytes' in row:reads.append(row)
            if 'event' in row and kind in wanted and kind not in [k for k,at in offsets]:
                candidates=[r for r in reads if r['bytes']==wanted[kind]]
                if candidates:offsets.append((kind,candidates[0]['offset']+(16 if kind=='release_end' else 0)))
        self.assertEqual(len(offsets),6)
        for kind,at in offsets:
            bad=bytearray(raw);bad[at]^=0xff
            with self.subTest(kind=kind),patch.object(Path,'read_bytes',lambda path:bytes(bad) if path==folder/'reads.bin' else original(path)):
                with self.assertRaises(ValueError):runtime.replay(folder,serial,trace,52)

    def run_mechanism_vectors(self,method,numbers):
        import test_x86_64_program_memory as legacy
        class LargeVectors(legacy.ProgramMemoryTests):
            def mechanism(inner,files,headers,c,label):
                if label=='wide_context':
                    c=c.replace('task[128]','task[512]').replace('i<128','i<512')
                    c=re.sub(r'task\[(\d+)\]',lambda m:'task['+str(int(m[1])+192 if 68<=int(m[1])<=87 else int(m[1]))+']',c)
                    c=c.replace('task[target[i]+56]','task[target[i]+248]')
                if label=='wide_identity':
                    c=c.replace('round<128','round<(cap==64?3U:128U)').replace('reuse=128','reuse=128/128/3')
                    c=c.replace('tasks[64][128]','tasks[64][512]').replace('i<128','i<512').replace('field<128','field<512')
                    c=c.replace('t[68]','t[260]').replace('t[69]','t[261]').replace('i<68','i<260').replace('field<68','field<260')
                if label=='wide_mapping':
                    c=c.replace('setup(63,6)','setup(255,6)').replace('[63]','[255]')
                c=re.sub(r'\b[0-9]+\b',lambda m:str(numbers.get(int(m[0]),int(m[0]))),c)
                asm='BITS 64\n%define REIST_NATIVE_LARGE_IMAGE 1\n%define REIST_NATIVE_WIDE 1\n%define X86_64_NATIVE_RAM 1\n'
                asm+='\n'.join('%include "'+f+'"' for f in files)
                c='#define REIST_NATIVE_LARGE_IMAGE 1\n#define REIST_NATIVE_WIDE 1\n'+''.join('#include "'+(ROOT/h).as_posix()+'"\n' for h in headers)+c
                legacy.build_actual(asm,c,label)
        getattr(LargeVectors(),method)()

    def test_actual_create_versions_and_complete_preflight(self):
        import test_x86_64_program_memory as legacy
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        request=source.split('\n%ifdef REIST_NATIVE_SERVICE_CPU\n; Already admitted')[0]
        ranges=source[source.index('%ifdef REIST_NATIVE_LARGE_IMAGE\nfamily_import_range_v3_64:'):source.index('\nfamily_syscall64:')]
        asm='BITS 64\n%define REIST_NATIVE_WIDE 1\n%define REIST_NATIVE_LARGE_IMAGE 1\n%define REIST_NATIVE_SERVICE_CPU 1\nPF_R equ 4\nsection .text\n'+request+ranges
        asm+='''
extern validate_chunk
global large_range
large_range:
 mov rax,rdi
 jmp family_import_range_v3_64
scheduler_validate_shell_range64:
 push r8
 push r9
 push rcx
 push rdx
 sub rsp,8
 mov rdi,rax
 mov rsi,rdx
 mov rdx,rcx
 call validate_chunk
 add rsp,8
 pop rdx
 pop rcx
 pop r9
 pop r8
 ret
'''
        c=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define C(x) do{if(!(x)){printf("create line %d\n",__LINE__);return 1;}}while(0)
extern int64_t __attribute__((sysv_abi)) family_request_admit64(const void*);
extern int __attribute__((sysv_abi)) large_range(uint64_t);
static unsigned calls,fail,wrong;
int __attribute__((sysv_abi)) validate_chunk(uint64_t address,uint64_t bytes,uint64_t rights){
 unsigned at=calls++;
 if(address!=0x20000000ULL+at*1024 || bytes!=(at==1028?288:1024) || rights!=4)wrong=1;
 return at!=fail;
}
int main(void){
 uint64_t request[10]={7ULL|(64ULL<<32),1,0,0x20000000,0,0x30000000,32,0x31000000,0,0};
 uint64_t saved[10];memcpy(saved,request,sizeof saved);
 C(family_request_admit64(request)==1 && !memcmp(saved,request,sizeof saved));
 for(unsigned version=4;version<=7;version++){
  request[0]=version|((uint64_t)(version==6?80:64)<<32);request[8]=version==6?1000:0;
  C(family_request_admit64(request)==1);
  request[6]=33;C(family_request_admit64(request)==-22);request[6]=32;
 }
 memcpy(request,saved,sizeof saved);
 for(unsigned field=0;field<8;field++){
  uint64_t old=request[field];request[field]=0;
  C(family_request_admit64(request)==(field==2||field==4?1:-22));request[field]=old;
 }
 request[0]=8ULL|(64ULL<<32);C(family_request_admit64(request)==-22);
 for(fail=0;fail<=1029;fail++){
  calls=wrong=0;C(large_range(0x20000000)==(fail==1029));
  C(!wrong && calls==(fail==1029?1029:fail+1));
 }
 calls=0;C(!large_range(UINT64_MAX-1052958) && !calls);
 puts("large_create_OK");return 0;
}
'''
        legacy.build_actual(asm,c,'large_create')

    def test_actual_parser_profiles(self):
        import build_x86_64_large_image as large
        import build_x86_64_boot_programs as old
        from build_user_program import find_zig
        folder=ROOT/'build/codex-agent/r83bu-large-image'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(ROOT/'build/zig-global-cache'),ZIG_LOCAL_CACHE_DIR=str(folder/'cache'))
        asm='BITS 64\n%define REIST_NATIVE_WIDE 1\n%define REIST_NATIVE_LARGE_IMAGE 1\n%include "arch/x86_64/mm/native_layout.inc"\nsection .text\n'
        asm+=(ROOT/'arch/x86_64/exec/boot_programs.inc').read_text().split('; END_PURE_ADMISSION')[0]
        asm+=(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        source=folder/'admission.asm';source.write_text(asm)
        obj=folder/'admission.o'
        r=subprocess.run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',source,'-o',obj],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        raw=(ROOT/'build/codex-agent/native-js-inventory01/probe03.elf').read_bytes()
        # Concrete measured engine must be rejected by the existing v2 boundary.
        with self.assertRaises(ValueError):old.prepare(raw,[],True)
        expected=large.prepare(raw,[])
        self.assertEqual(len(expected),1052960)
        self.assertEqual(expected[:16],b'RNPGv3\0\0'+struct.pack('<II',3,1052960))
        self.assertEqual(expected[280:288],bytes(8))
        self.assertEqual(expected[31:40],bytes([0,0]+[6]*7))
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            command=[str(find_zig()),'cc','-target','x86_64-windows-gnu',opt,'-fno-sanitize=all','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-DREIST_NATIVE_LARGE_IMAGE=1','-Iuserspace/sdk/include','test/x86_64_large_image_host.c','userspace/sdk/lib/x86_64/image.c',str(obj),'-o',str(exe)]
            r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            inp=folder/'input.elf';out=folder/'prepared.bin';inp.write_bytes(raw)
            r=subprocess.run([exe,'3',inp,out],timeout=30);self.assertEqual(r.returncode,0);self.assertEqual(out.read_bytes(),expected)
            self.assertEqual(subprocess.run([exe,'2',inp,out],timeout=30).returncode,22)
            padded=raw+bytes(1048576-len(raw));inp.write_bytes(padded)
            self.assertEqual(subprocess.run([exe,'3',inp,out],timeout=30).returncode,0)
            self.assertEqual(out.read_bytes(),large.prepare(padded,[]))
            malformed=[padded+b'x']
            for at,fmt,value in ((0,'I',0),(4,'B',1),(16,'H',3),(18,'H',3),
                    (20,'I',0),(24,'Q',0),(32,'Q',len(raw)),(48,'I',1),
                    (52,'H',63),(54,'H',55),(56,'H',9),(64,'I',4),
                    (68,'I',7),(72,'Q',len(raw)+4096),(80,'Q',0x500000),
                    (96,'Q',len(raw)+1),(104,'Q',2097152),(112,'Q',0)):
                bad=bytearray(raw);struct.pack_into('<'+fmt,bad,at,value);malformed.append(bytes(bad))
            for bad in malformed:
                with self.assertRaises(ValueError):large.prepare(bad,[])
                inp.write_bytes(bad)
                self.assertEqual(subprocess.run([exe,'3',inp,out],timeout=30).returncode,22)
if __name__=='__main__':unittest.main()
