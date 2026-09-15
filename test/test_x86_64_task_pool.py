"""Actual native task-pool mechanisms; bounded host and guest proof contracts."""
from pathlib import Path
import sys,unittest,os,subprocess,uuid,re,json,struct,copy,ast
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host


class TaskPoolTests(unittest.TestCase):
    def test_observer_context_owner(self):
        import run_qemu_x86_64_task_pool as r
        # Execute the real generated START prefix through context selection;
        # hardware reads only are faked, and no guest write is reachable here.
        prefix=r.START[:r.START.index('    for page in range(64):')]
        code=getattr(r,'IMAGE_CONTEXT','')+prefix+'    return selector,staged\n'
        s=dict(scheduler_current_slot=0x1000,scheduler_tasks=0x2000,
            process_run_plan=0x5000,process_run_generations=0x6000,
            family_records=0x7000,elf_image_selector=0x8000,
            elf_context_window=0x9000,elf_context_store=0xa000,
            elf_page_frames=0x9000,boot_program_catalog=0x100000)
        record=bytearray(r.SIZE);record[:16]=b'RNPGv2\0\0'+struct.pack('<II',2,r.SIZE)
        struct.pack_into('<Q',record,16,0x410000);record[24+16:24+19]=bytes((5,4,6))
        def setup(slot,selected):
            gen=slot+21;image=slot+3 if slot<2 else slot+5
            t=[0]*128;t[0]=2;t[1]=gen;t[68]=0x410000;t[69]=0x40ff80
            contexts=[];expected=[]
            for owner in range(13):
                raw=bytearray(592);frames=[0]*64
                for page in (16,17,18):frames[page]=0x100000000+owner*0x100000+page*4096
                struct.pack_into('<64Q',raw,0,*frames);raw[512:576]=record[24:88]
                struct.pack_into('<I4BQ',raw,576,1000000,1,1,0,1,0x410000)
                contexts.append(raw);expected.append(tuple(frames))
            plan=bytearray(272);struct.pack_into('<4I',plan,0,4,272,8,0)
            struct.pack_into('<Q',plan,16+slot*32+24,image)
            generations=bytearray(32);struct.pack_into('<I',generations,slot*4,gen)
            families=bytearray(512);struct.pack_into('<Q',families,slot*64,(gen<<32)|slot)
            struct.pack_into('<Q',families,slot*64+40,1 if slot<2 else 2)
            store=bytearray(b''.join(contexts));store[selected*592:(selected+1)*592]=bytes([0xa5])*592
            regions={s['scheduler_current_slot']:bytearray(struct.pack('<I',slot)),
                s['process_run_plan']:plan,s['process_run_generations']:generations,
                s['family_records']:families,s['elf_image_selector']:bytearray([selected]),
                s['elf_context_window']:bytearray(contexts[selected]),s['elf_context_store']:store,
                s['boot_program_catalog']+slot*r.SIZE:bytearray(record)}
            reads=[]
            def mem(address,size):
                reads.append((address,size))
                for base,raw in regions.items():
                    if base<=address and address+size<=base+len(raw):return bytes(raw[address-base:address-base+size])
                raise AssertionError(('unbound hardware read',address,size))
            env=dict(struct=struct,S=s,starts={},copies={gen:bytes(record)},mode=lambda:8,
                task=lambda n:t if n==slot else None,reg=lambda name:0,mem=mem,
                q=lambda a:struct.unpack('<Q',mem(a,8))[0],d=lambda a:struct.unpack('<I',mem(a,4))[0],
                file_leaves=lambda task:[0]*64)
            exec(code,env)
            return env,regions,reads,image,expected[image]
        # First case reproduces the original first-root/current-window mismatch.
        for slot,selected in [(0,4)]+[(slot,selected) for slot in range(8) for selected in range(13)]:
            env,regions,reads,image,frames=setup(slot,selected)
            with self.subTest(slot=slot,selected=selected):
                self.assertEqual(env['start'](),(image,frames))
                context=s['elf_context_window'] if image==selected else s['elf_context_store']+image*592
                self.assertIn((context,592),reads)
        for slot,selected in ((0,4),(0,3),(7,4),(7,12)):
            image=slot+3 if slot<2 else slot+5
            base=s['elf_context_window'] if image==selected else s['elf_context_store']+image*592
            cases=[(s['process_run_plan'],0,'I',3),
                (s['process_run_plan'],16+slot*32+24,'Q',image+1),
                (s['process_run_generations'],slot*4,'I',1),
                (s['family_records'],slot*64,'Q',((slot+20)<<32)|slot),
                (s['family_records'],slot*64+40,'Q',4),
                (s['elf_image_selector'],0,'B',13),
                (base,580,'B',0),(base,581,'B',0),(base,582,'B',1),(base,583,'B',0),
                (base,584,'Q',0x410001),(base,512+16,'B',6),
                (base,16*8,'Q',0),(base,17*8,'Q',0x1234),(base,0,'Q',0x100000000),
                (base,17*8,'Q',0x100000000+image*0x100000+16*4096)]
            for address,offset,fmt,value in cases:
                env,regions,reads,unused,frames=setup(slot,selected)
                region=next(a for a,raw in regions.items() if a<=address and address+offset+struct.calcsize(fmt)<=a+len(raw))
                struct.pack_into('<'+fmt,regions[region],address-region+offset,value)
                with self.subTest(slot=slot,selected=selected,address=address,offset=offset):
                    with self.assertRaises(AssertionError):env['start']()

    def test_build_reuse_bindings(self):
        import hashlib
        import verify_x86_64_task_pool as v
        from unittest.mock import patch
        def sign(value):
            value['candidate']=hashlib.sha256(json.dumps(value['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        commands=['command-'+str(n) for n in range(24)]
        original=dict(directory='build/codex-agent/r83an-task-pool/candidate-06',
            source_inputs={'Makefile':'a'*64,**{n:'b'*64 for n in v.CONTEXT_RENEWAL_SOURCES+v.CONTEXT_RENEWAL_DOCS}},
            tools_sha256={'compiler':'c'*64},commands=commands,package=dict(package_tests=commands[17:20],profile='pool'))
        sign(original);frozen=copy.deepcopy(original);frozen['directory']='build/codex-agent/r83an-task-pool/candidate-07'
        frozen['package']['context_owner_renewal_files']=list(v.CONTEXT_RENEWAL_SOURCES)
        frozen['source_inputs'][v.CONTEXT_RENEWAL_SOURCES[0]]='d'*64;sign(frozen)
        gate=dict(candidate=original['candidate'],command=commands[17],passed=True,exit_code=0,elapsed=3,
            artifacts={'build/kernel.elf':'e'*64},log=dict(path='build/compile.log',sha256='f'*64))
        for index in (18,19,20):
            g=dict(gate,command=commands[index-1]);v.build_reuse_binding(frozen,original,g,index)
        mutations=[('frozen',['directory'],'wrong'),('original',['directory'],'wrong'),
            ('frozen',['source_inputs','Makefile'],'x'*64),('frozen',['tools_sha256','compiler'],'x'*64),
            ('frozen',['package','profile'],'different'),('frozen',['commands'],['different']*24),
            ('frozen',['candidate'],'0'*64),('gate',['candidate'],'0'*64),('gate',['passed'],False),
            ('gate',['exit_code'],1),('gate',['elapsed'],181),('gate',['elapsed'],-1),
            ('gate',['artifacts'],{}),('gate',['command'],'different'),('gate',['execution'],'REUSED')]
        for kind,keys,value in mutations:
            values=dict(frozen=copy.deepcopy(frozen),original=copy.deepcopy(original),gate=copy.deepcopy(gate))
            target=values[kind]
            for key in keys[:-1]:target=target[key]
            target[keys[-1]]=value
            if keys[0]=='source_inputs':sign(values[kind])
            with self.subTest(kind=kind,keys=keys):
                with self.assertRaises(ValueError):v.build_reuse_binding(values['frozen'],values['original'],values['gate'],18)
        for index in (17,21,True):
            with self.assertRaises(ValueError):v.build_reuse_binding(frozen,original,gate,index)
        for added in (False,True):
            bad=copy.deepcopy(frozen)
            if added:bad['source_inputs']['unexpected.c']='0'*64
            else:del bad['source_inputs']['Makefile']
            sign(bad)
            with self.assertRaises(ValueError):v.build_reuse_binding(bad,original,gate,18)
        # Real bytes/logs/JSON links exercise the complete proof wrapper.
        folder=v.BASE/('host-reuse-'+uuid.uuid4().hex);base=folder/'build/codex-agent/r83an-task-pool'
        (base/'candidate-06').mkdir(parents=True);(base/'context-owner-renewal').mkdir()
        artifact=folder/'build/kernel.elf';log=folder/'build/compile.log'
        artifact.write_bytes(b'unchanged build');log.write_bytes(b'build passed')
        with patch.object(v,'ROOT',folder),patch.object(v,'BASE',base):
            old_path=base/'candidate-06/frozen-candidate.json';old_path.write_text(json.dumps(original))
            actual=dict(gate,artifacts={'build/kernel.elf':v.digest(artifact)},log=v.link(log))
            receipt=base/'candidate-06/gate-18.json';receipt.write_text(json.dumps(actual))
            admission=dict(build_frozen=v.link(old_path),build_receipts=[v.link(receipt)])
            admitted=base/'context-owner-renewal/admission.json';admitted.write_text(json.dumps(admission))
            self.assertEqual(v.build_reuse_proof(frozen,18)[1],actual)
            for path in (artifact,log,receipt,old_path):
                saved=path.read_bytes();path.write_bytes(saved+b' ')
                with self.subTest(changed=path.name):
                    with self.assertRaises(ValueError):v.build_reuse_proof(frozen,18)
                path.write_bytes(saved)
            self.assertEqual(v.build_reuse_proof(frozen,18)[1],actual)

    def test_actual_run_admission(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('; Read-only whole-run ownership gate;',1)[0]
        prefix='''BITS 64
%define REIST_NATIVE_PROGRAMS 1
%define REIST_NATIVE_LIFECYCLE 1
%define REIST_NATIVE_WIDE 1
TASK_SLOT_CAPACITY equ 4
section .text
global process_run_admit64
'''
        completion=(ROOT/'arch/x86_64/proc/process_ipc.inc').read_text().split('; Preserve caller registers except RAX.')[0]
        for profile in (0,1):
            asm=('%define REIST_NATIVE_TASK_POOL 1\n' if profile else '')+prefix+body+completion
            asm+='\nglobal task_pool_host_capacity,process_ipc_completion_apply64\ntask_pool_host_capacity:\nmov eax,NATIVE_POOL_TASKS\nret\n'
            host.TaskFrameTests().build(asm,ROOT/'test/x86_64_task_pool_host.c','TASK_POOL_ADMISSION')

    def test_actual_c_owners(self):
        host.suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83an-task-pool'/('host-c-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(command,label,limit=60,expected_exit=0):
            result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,
                timeout=limit,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
            self.assertEqual(result.returncode,expected_exit,(result.stdout+result.stderr)[-2500:]);return result.stdout+result.stderr
        for profile in (0,1):
            for kind in ('heap','ipc'):
                flags=['-DREIST_HOST_TEST','-DREIST_NATIVE_TASK_POOL='+str(profile),'-DTASK_POOL_'+kind.upper()+'_TEST']
                if kind=='heap':
                    flags+=['-DREIST_NATIVE_HEAP_HOST_TEST'];sources=['arch/x86_64/mm/native_heap.c']
                else:
                    flags+=['-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_NATIVE_RUNTIME'];sources=['kernel/ipc/ipc.c']
                for opt in ('0','2'):
                    label=f'{kind}-{profile}-{opt}';exe=folder/(label+'.exe')
                    run([host.find_zig(),'cc','-O'+opt,'-std=c11','-Wall','-Wextra','-Werror','-I.',
                         *flags,*sources,'kernel/init/critical_object.c','test/x86_64_task_pool_host.c','-o',exe],label+'-compile')
                    if kind=='ipc':
                        output=run([exe,'check-failure'],label+'-check-failure',15,1)
                        self.assertEqual(output.splitlines().count('TASK_POOL_CHECK_SIDE_EFFECT'),1)
                        self.assertIn('check failed line',output)
                        self.assertNotIn('TASK_POOL_CHECK_BYPASSED',output)
                        if opt=='2':self.assertIn('TASK_POOL_CHECK_NDEBUG=1',output)
                    for case in ('normal','corrupt','outside','stale',*(('owner',) if kind=='ipc' else ())):
                        output=run([exe,case],label+'-'+case,15)
                        expected='TASK_POOL_'+kind.upper()+'_OK' if case in ('normal','owner') else (
                            'NATIVE_HEAP_HOST_OK fail_closed=1' if kind=='heap' else 'NATIVE_IPC_FAULT_CLOSED_OK')
                        self.assertIn(expected,output)

    def test_actual_family_pool(self):
        family=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        names=('family_record64','family_initialize64','family_validate_runtime64','family_terminal64','family_reaped64','family_wait_expired64')
        core=''.join(re.search(r'^'+n+r':\n.*?(?=^[A-Za-z_]\w*:|^section |\Z)',family,re.M|re.S).group() for n in names)
        data=family[family.index('family_begin:'):family.index('section .text\n%endif')]
        externals={'process_run_plan':272,'scheduler_tasks':8192,'process_run_generations':32,
            'process_heap_retire_mask':4,'scheduler_current_slot':4,'scheduler_last_tick':8,
            'scheduler_deadline_entries':128,'process_run_receipt':32}
        data='core_begin:\n'+data+''.join('alignb 8\n'+n+': resb '+str(size)+'\n' for n,size in externals.items())+'core_end:\n'
        exports=''.join('global '+n+'\n' for n in re.findall(r'^(\w+):',data,re.M))
        asm='''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_WIDE 1
%include "arch/x86_64/mm/native_layout.inc"
TASK_STATE equ 0
TASK_GENERATION equ 8
TASK_RAX equ 680
TASK_FREE equ 0
TASK_READY equ 1
TASK_RUNNING equ 2
TASK_FAULTED equ 3
TASK_BLOCKED equ 6
section .bss
alignb 8
'''+exports+data+'section .text\n'+family.split('; RUNTIME ADAPTER')[0]
        asm+='\n'+(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        asm+='\n'+(ROOT/'arch/x86_64/proc/syscall_profile.asm').read_text()
        asm+='\n'+''.join('global '+n+'\n' for n in names)+core
        asm+='''
global family_expire_test
family_expire_test:
    push rbp
    push r12
    sub rsp,8
    mov rbp,rsi
    mov eax,edi
    shl eax,NATIVE_TASK_SHIFT
    lea r12,[rel scheduler_tasks]
    add r12,rax
    call family_wait_expired64
    add rsp,8
    pop r12
    pop rbp
    ret
scheduler_fail: ud2
'''
        c='#define TASK_POOL_FAMILY_TEST\n#include "'+(ROOT/'test/x86_64_task_pool_host.c').as_posix()+'"\n'
        host.TaskFrameTests().build(asm,c,'TASK_POOL_FAMILY')

    def test_actual_whole_pool_frame_ownership(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('process_run_frames64:',1)[1].split('global x86_64_process_run64',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_WIDE 1
%define X86_64_NATIVE_RAM 1
%include "arch/x86_64/mm/memory_profile.inc"
TASK_STATE equ 0
TASK_CR3 equ 16
TASK_STACK_FRAME equ 24
TASK_PRIVATE_FRAMES equ 32
TASK_FREE equ 0
PAGE_SIZE equ 4096
section .bss
alignb 16
global scheduler_tasks,scheduler_table_frames,scheduler_original_cr3
scheduler_tasks: resq 8*128
scheduler_table_frames: resq 8*4
scheduler_original_cr3: resq 1
section .text
global pool_frames
pool_frames:
 push rbx
 push r12
 push r13
 call process_run_frames64
 pop r13
 pop r12
 pop rbx
 ret
process_run_frames64:
'''+body
        c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t scheduler_tasks[8][128],scheduler_table_frames[8][4],scheduler_original_cr3;
extern uint64_t __attribute__((sysv_abi)) pool_frames(void);
static uint64_t saved_tasks[8][128],saved_tables[8][4];
#define C(x) do{if(!(x)){printf("pool frames line %d\\n",__LINE__);return 1;}}while(0)
static void setup(void){
 memset(scheduler_tasks,0,sizeof(saved_tasks));memset(scheduler_table_frames,0,sizeof(saved_tables));
 scheduler_original_cr3=0x115000;uint64_t next=0x100000000ULL;
 for(unsigned s=0;s<8;s++){
  scheduler_tasks[s][0]=1;
  for(unsigned p=0;p<64;p++){scheduler_tasks[s][4+p]=next;next+=4096;}
  scheduler_tasks[s][3]=next;next+=4096;
  for(unsigned p=0;p<4;p++){scheduler_table_frames[s][p]=next;next+=4096;}
  scheduler_tasks[s][2]=scheduler_table_frames[s][0];
 }
}
static int checked(unsigned expected){
 memcpy(saved_tasks,scheduler_tasks,sizeof(saved_tasks));memcpy(saved_tables,scheduler_table_frames,sizeof(saved_tables));
 return pool_frames()==expected && !memcmp(saved_tasks,scheduler_tasks,sizeof(saved_tasks)) && !memcmp(saved_tables,scheduler_table_frames,sizeof(saved_tables));
}
int main(void){
 setup();C(checked(1));
 for(unsigned s=0;s<8;s++)for(unsigned p=0;p<69;p++){
  setup();uint64_t *frame=p<64?&scheduler_tasks[s][4+p]:p==64?&scheduler_tasks[s][3]:&scheduler_table_frames[s][p-65];
  uint64_t original=*frame;*frame=original|1;C(checked(0));
  *frame=0x400000000ULL;C(checked(0));
  *frame=scheduler_original_cr3;C(checked(0));
  *frame=0;C(checked(p<64));
 }
 setup();scheduler_tasks[7][67]=scheduler_tasks[0][4];C(checked(0));
 setup();scheduler_tasks[7][0]=0;C(checked(0));
 for(unsigned s=0;s<8;s++){memset(scheduler_tasks[s],0,sizeof(scheduler_tasks[s]));memset(scheduler_table_frames[s],0,sizeof(scheduler_table_frames[s]));}
 C(checked(1));scheduler_table_frames[7][3]=0x100000000ULL;C(checked(0));
 puts("TASK_POOL_FRAMES_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'TASK_POOL_FRAMES')

    def test_producer_rejects_before_output(self):
        import build_x86_64_boot_programs as producer
        from unittest import mock
        base=dict(case=0,family=True,startup=True,import_image=True,wide=True,task_pool=True)
        for name,value in [('task_pool',1),('wide',False),('import_image',False),('startup',False),
                           ('family',False),('pio',True),('block',True),('block_profile',True),
                           ('filesystem',True),('file_launch',True),('memory_case',1),
                           ('case',1),('family_case',1),('startup_case',1),('pio_case',1),
                           ('block_profile_case',1),('filesystem_case',1),('file_launch_case',1),('filesystem_layout',0)]:
            with self.subTest(selector=name):
                args={**base,name:value}
                with mock.patch.object(producer.Path,'mkdir') as mkdir, mock.patch.object(producer.subprocess,'run') as run:
                    with self.assertRaises(ValueError):producer.build(ROOT/'build/codex-agent/r83an-task-pool/rejected',[],[],[],**args)
                    mkdir.assert_not_called();run.assert_not_called()

    def test_stripped_fixture_section_binding(self):
        import run_qemu_x86_64_task_pool as r
        raw=bytearray(0x3300);raw[:16]=b'\x7fELF\x02\x01\x01'+bytes(9)
        struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410000,64,0x3000,0,64,56,2,64,5,4)
        struct.pack_into('<II6Q',raw,64,1,5,0x1000,0x410000,0,1,1,4096)
        struct.pack_into('<II6Q',raw,120,1,6,0x2000,0x411000,0,64,8192,4096)
        raw[0x1000]=0xc3;raw[0x2000:0x2040]=bytes(range(64))
        names=b'\0.text\0.data\0.bss\0.shstrtab\0';raw[0x3200:0x3200+len(names)]=names
        for i,row in enumerate(((1,1,6,0x410000,0x1000,1,0,0,16,0),
                (7,1,3,0x411000,0x2000,64,0,0,8,0),
                (13,8,3,0x412000,0x2040,4096,0,0,4096,0),
                (18,3,0,0,0x3200,len(names),0,0,1,0)),1):
            struct.pack_into('<II4QII2Q',raw,0x3000+i*64,*row)
        sections=r.fixture_sections(bytes(raw))
        self.assertEqual(sections['.data'],dict(address=0x411000,size=64))
        self.assertEqual(sections['.bss'],dict(address=0x412000,size=4096))
        for offset,fmt,value in ((40,'Q',0xffff),(58,'H',32),(60,'H',129),(62,'H',0),
            (0x3000,'Q',1),(0x3080,'I',0),(0x3084,'I',8),(0x3088,'Q',7),
            (0x3090,'Q',0x410000),(0x3098,'Q',0x32ff),(0x30a0,'Q',0x40000),
            (0x30b0,'Q',3),(0x30c0,'I',7),(0x30c4,'I',1),(0x30d0,'Q',0x411000)):
            bad=bytearray(raw);struct.pack_into('<'+fmt,bad,offset,value)
            with self.subTest(offset=offset,value=value):
                with self.assertRaises(ValueError):r.fixture_sections(bytes(bad))

    @staticmethod
    def sample(case):
        import run_qemu_x86_64_task_pool as r
        per=9 if case==6 else 8;count=30;sha='9'*64;oom={7:0,8:count//2,9:count-1}.get(case)
        common=[m for m in r.transport.REQUIRED_MARKERS if 'SHELL' not in m]
        cut=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
        serial='\n'.join(common[:cut])+'\n';events=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]
        def emit(kind,**fields):events.append(dict(kind=kind,**fields))
        for run in range(2):
            base=run*per;starts=[]
            for slot in range(8):
                gen=base+slot+1;role=slot if slot<2 else 0 if slot<5 else 1;index=-1 if slot<2 else slot-2 if slot<5 else slot-5
                parent=0 if slot<2 else base+role+1
                if slot>=2:
                    if slot==2 and oom is not None:
                        emit('oom',owner=(base+1)<<32,acquired=oom)
                        emit('rollback',owner=(base+1)<<32,acquired=oom,free=1000000,before=1000000)
                    emit('copy',gen=gen,bytes=r.SIZE,sha=sha)
                    emit('create',gen=gen,owner=(parent<<32)|role,slot=slot,acquired=count)
                entry=dict(slot=slot,gen=gen,parent=parent,index=index,role=role,image=slot+3 if slot<2 else slot+5,pages=20,private=10,live=slot+1)
                starts.append(entry);emit('start',**entry)
                if slot<2:emit('mode',slot=slot,gen=gen,address=0x415008,physical=0x100000008+4096*gen,before=0,value=case)
            for e in starts[2:]:
                checksum=sum(((i^e['gen'])&255)+((i+e['gen'])&255)+((i^e['parent'])&255) for i in range(4096))
                emit('witness',gen=e['gen'],parent=e['parent'],index=e['index'],role=e['role'],heap=8192,private=4096,immutable=1,checksum=checksum)
            if case in (2,5):emit('fault',gen=base+(3 if case==2 else 1),slot=2 if case==2 else 0,vector=6)
            if case in (4,5):
                for slot in ([2] if case==4 else [2,3,4]):emit('cancel',gen=base+slot+1,slot=slot,state=6,reason=2 if case==4 else 3)
            def retire(e):
                nonlocal serial
                slot=e['slot'];bad=e['role']==0 and e['index']==0 and case in (2,3,4)
                status=90+slot if slot<2 else 80+e['index']+3*e['role'];state=4
                if case==5 and e['role']==0:status=134 if slot==0 else 0;state=3
                if bad:status={2:134,3:256,4:0}[case];state=3
                data=struct.pack('<4I2Q',slot,e['gen'],status,state,32 if bad and case==3 else 1,0x410078)
                serial+='REIST_X86_64_PROCESS_REAP_OK v1='+data.hex().upper()+'\n'
                emit('release',slot=slot,gen=e['gen'],frames=14,before=1000000,after=1000014,fenced=1)
            if case==6:
                emit('capacity',gen=base+1,phase=3,occupied=6,receipt=0);retire(starts[2])
                emit('capacity',gen=base+1,phase=4,occupied=6,receipt=1)
                gen=base+9;emit('copy',gen=gen,bytes=r.SIZE,sha=sha)
                emit('create',gen=gen,owner=(base+1)<<32,slot=2,acquired=count)
                new=dict(starts[2],gen=gen,live=8);emit('start',**new)
                checksum=sum(((i^gen)&255)+((i+gen)&255)+((i^(base+1))&255) for i in range(4096))
                emit('witness',gen=gen,parent=base+1,index=0,role=0,heap=8192,private=4096,immutable=1,checksum=checksum)
                starts[2]=new
            for entry in starts[2:]+starts[:2]:retire(entry)
            serial+=r.wide.process.DONE+'\n'
            emit('finish',run=run+1,free=1000010,initial=1000010,tasks=per,generation=(run+1)*per,zero=1)
        serial+='\n'.join(common[cut:])+'\n'+r.wide.process.SUCCESS+'\n'
        return serial,events,oom,count,sha

    def test_actual_guest_oracle_mutations(self):
        import run_qemu_x86_64_task_pool as r
        for case in range(10):
            serial,events,oom,count,sha=self.sample(case)
            def trace(rows):return '\n'.join('TASK_POOL '+json.dumps(e) for e in rows)+'\n'
            self.assertEqual(len(r.validate(serial,trace(events),case,oom,count,sha)),18 if case==6 else 16)
            for index,event in enumerate(events):
                # Every row is required exactly once, with a bound lifecycle.
                with self.assertRaises(ValueError):r.validate(serial,trace(events[:index]+events[index+1:]),case,oom,count,sha)
                with self.assertRaises(ValueError):r.validate(serial,trace(events[:index]+[event]+events[index:]),case,oom,count,sha)
            for kind,key,value in (('start','parent',0),('start','image',13),('start','live',9),
                 ('create','owner',0),('copy','sha','0'*64),('witness','immutable',0),
                 ('witness','checksum',0),('witness','heap',4096),('release','fenced',0),
                 ('release','after',1000000),('finish','zero',0),('finish','initial',1),
                 ('mode','before',1),('mode','physical',0)):
                changed=copy.deepcopy(events)
                entry=next(e for e in changed if e['kind']==kind and (kind!='start' or e['slot']>=2))
                entry[key]=value
                with self.subTest(case=case,field=key):
                    with self.assertRaises(ValueError):r.validate(serial,trace(changed),case,oom,count,sha)
            for bad in (serial+serial,serial.replace(r.wide.process.DONE,'MISSING',1),serial.replace(r.wide.process.SUCCESS,'MISSING')):
                with self.assertRaises(ValueError):r.validate(bad,trace(events),case,oom,count,sha)
            first=r.wide.process.REAP.search(serial)
            for offset in (0,4,8,12,16,24):
                raw=bytearray.fromhex(first[1]);raw[offset+3]^=128
                with self.assertRaises(ValueError):r.validate(serial.replace(first[1],raw.hex().upper(),1),trace(events),case,oom,count,sha)

    def test_observer_has_only_scoped_mutations(self):
        import run_qemu_x86_64_task_pool as r
        code=r.observer_body();tree=ast.parse(code)
        writes=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_memory']
        self.assertEqual(len(writes),1)
        self.assertEqual(ast.unparse(writes[0].args[1]),"struct.pack('<Q', CASE)")
        self.assertNotIn('def poison',code);self.assertNotIn('pio_',code)
        self.assertEqual(r.CASES,tuple((n,8192 if n==1 else 4096) for n in range(10)))

    def test_selected_fatal_path_never_cleans_unknown_owners(self):
        text=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body=text.split('scheduler_fail:\n',1)[1].split('scheduler_return_failure64:',1)[0]
        selected=body.split('%ifdef REIST_NATIVE_TASK_POOL\n',1)[1].split('%endif',1)[0]
        instructions='\n'.join(line.split(';',1)[0] for line in selected.splitlines())
        self.assertNotIn('cleanup',instructions);self.assertNotIn('release',instructions)
        self.assertIn('    cli\n',selected);self.assertIn('    jmp halt64\n',selected)
        asm='''BITS 64
section .data
global fatal_state
fatal_state:
scheduler_active: db 1
scheduler_failure_stage: db 0xe0
align 8
counts: times 5 dq 0
scheduler_stage_message: db 1,0
scheduler_newline: db 13,10,0
section .text
global selected_failure
selected_failure:
'''+selected.replace('    cli\n','    call host_cli\n')+'''
host_cli:
    inc qword [rel counts]
    ret
serial_init64:
    inc qword [rel counts+8]
    ret
serial_write64:
    inc qword [rel counts+16]
    ret
scheduler_hex8_local64:
    cmp al,0xe0
    jne wrong
    inc qword [rel counts+24]
    ret
halt64:
    inc qword [rel counts+32]
    ret
wrong: ud2
'''
        c='''#include <stdint.h>
#include <stdio.h>
extern unsigned char fatal_state[];
extern void __attribute__((sysv_abi)) selected_failure(void);
int main(void){
 selected_failure();uint64_t *counts=(void*)(fatal_state+8);
 if(fatal_state[0] || fatal_state[1]!=0xe0 || counts[0]!=1 || counts[1]!=1 || counts[2]!=2 || counts[3]!=1 || counts[4]!=1)return 1;
 puts("TASK_POOL_FATAL_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'TASK_POOL_FATAL')


if __name__=='__main__':unittest.main()
