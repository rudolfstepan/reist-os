"""Synthetic negatives exercise the actual oracle, never guest acceptance."""
from pathlib import Path
import ast,copy,hashlib,json,re,struct,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_qemu_x86_64_filesystem as r
COUNTS={2:27,3:42,'sha':{2:'a'*64,3:'b'*64}}
def sample(case,layout=2,oom=None):
    events=[];blocks=[];per=4 if case==6 else 6
    def emit(kind,**fields):events.append(dict(kind=kind,**fields))
    emit('poison',bytes=270336);emit('boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)
    image=r.media.image(r.media.LAYOUTS[layout],case==8);sectors=len(image)//512
    lb={0:[0,19,33],1:[0,1120,1121],2:[2,3,4,10,42,43,12,44],
        3:[2,3,4,20,84,85,86,87,22,88],4:[2,3,8,40,168,169,170,171,172,173,174,175,42,176]}[layout]
    outcomes={gen:(slot,status,state) for slot,gen,status,state in r.expected_receipts(case)}
    for run in range(2):
        base=run*per;released=[]
        for slot in (0,1):emit('start',slot=slot,gen=base+slot+1,pages=28,private=12)
        if oom is not None:
            emit('oom',owner=(base+1)<<32,acquired=oom);emit('rollback',owner=(base+1)<<32,acquired=oom,free=1000,before=1000)
        for round_ in range(1 if case==6 else 2):
            driver=base+3+2*round_;fs=driver+1;partial=case in (5,6) and not round_
            for slot,gen in ((2,driver),(3,fs)):
                emit('copy',gen=gen,bytes=r.wide.SIZE,sha=COUNTS['sha'][slot]);emit('create',gen=gen,acquired=COUNTS[slot])
                emit('start',slot=slot,gen=gen,pages=28,private=12)
            emit('bind',gen=driver,owner=(driver<<32)|2)
            for slot,gen in ((2,driver),(3,fs)):emit('immutable',gen=gen,slot=slot,source=r.wide.SIZE,device=int(slot==2))
            emit('driver_ready',gen=driver,peer=(fs<<32)|3,capacity=sectors,deadline=2500)
            if case!=6:
                bad=case==8 or case==5 and not round_
                emit('fs_ready',gen=fs,peer=(driver<<32)|2,status=-5 if bad else 0,deadline=2500,cached=0 if bad else 1 if layout<2 else 4)
            lbas=[0,lb[0]] if partial else [0]+lb[:1] if case==8 else [0]+lb
            for sequence,lba in enumerate(lbas[1:],1):
                emit('block_request',gen=driver,client=fs,sequence=sequence,lba=lba)
                if not partial:emit('block_reply',gen=driver,sequence=sequence,lba=lba,sha=hashlib.sha256(image[lba*512:(lba+1)*512]).hexdigest())
            n=0 if case in (6,8) or case==5 and not round_ else 1 if case in (1,2,3,4) and not round_ else 9
            for sequence in range(1,n+1):
                request=r.file_frame(layout,sequence);op=struct.unpack_from('<I',request,8)[0]
                emit('fs_request',gen=fs,sequence=sequence,op=op,sha=hashlib.sha256(request).hexdigest())
                if not (n==1 and case in (1,2,3)):
                    status=1 if sequence==6 else -2 if sequence==7 else -11 if sequence==9 else 0
                    emit('fs_reply',gen=fs,sequence=sequence,status=status,bad=int(n==1 and case==4))
                status=-110 if n==1 and case in (1,2,3) else -71 if n==1 else 1 if sequence==6 else -2 if sequence==7 else -11 if sequence==9 else 0
                emit('result',gen=fs,caller=base+1,sequence=sequence,op=op,status=status,sha=hashlib.sha256(r.file_frame(layout,sequence,status>=0)).hexdigest())
            if not round_ and case in (1,5,6):
                slot={1:3,5:2,6:0}[case];gen=fs if slot==3 else driver if slot==2 else base+1
                emit('fault',gen=gen,slot=slot,vector=6)
            for slot,gen in ((3,fs),(2,driver)):
                _,status,state=outcomes[gen]
                if status==0 and state==3:emit('cancel',gen=gen,slot=slot,state=6)
                if slot==2:
                    data=b''.join(image[lba*512:(lba+1)*512] for lba in lbas)
                    size=768 if partial else len(data)
                    emit('retire',gen=gen,identify=512,data=size,lbas=lbas,sha=hashlib.sha256(data[:size]).hexdigest(),fenced=1)
                emit('release',slot=slot,gen=gen,frames=16,before=1000,after=1016,fenced=1);released.append(gen)
        for slot in (0,1):
            gen=base+slot+1;emit('release',slot=slot,gen=gen,frames=16,before=1000,after=1016,fenced=1);released.append(gen)
        emit('trace_drained',run=run+1,events=100,sha='c'*64);emit('trace_clean',run=run+1,bytes=12304)
        emit('finish',run=run+1,free=1000,initial=1000,tasks=per,generation=(run+1)*per)
        block=''
        for gen in released:
            slot,status,state=outcomes[gen]
            block+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,state,32 if status==256 else 5,0x410123).hex().upper()+'\n'
        blocks.append(block+r.wide.process.DONE+'\n')
    markers=[m for m in r.wide.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[r.wide.process.SUCCESS]
    serial='\n'.join(markers).replace('REIST_X86_64_C_KERNEL_CONTROL_OK',''.join(blocks)+'REIST_X86_64_C_KERNEL_CONTROL_OK')
    return serial,events
def trace(events):return '\n'.join('FILESYSTEM '+json.dumps(e) for e in events)
class FilesystemRuntime(unittest.TestCase):
    def test_build_selector_admission_and_both_layouts(self):
        producer=r.wide.producer
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'must-not-create'
            valid=dict(family=True,startup=True,import_image=True,pio=True,block=True,wide=True,block_profile=True,filesystem=True)
            for change in (dict(filesystem=1),dict(filesystem_case=-1),dict(filesystem_case=9),
                dict(filesystem_layout=-1),dict(filesystem_layout=5),dict(block_profile=False),
                dict(block_profile_case=1),dict(filesystem=False,filesystem_case=1),
                dict(filesystem=False,filesystem_layout=0)):
                with self.assertRaises(ValueError):producer.build(output,[],[],[],0,**(valid|change))
                self.assertFalse(output.exists())
        flags=['X86_64_NATIVE_'+n+'=1' for n in ('FILESYSTEM','BLOCK_PROFILE','WIDE','IMPORT','STARTUP',
            'LIFECYCLE','PROGRAMS','RUNTIME','HEAP','RAM','IPC','PROCESSES','PIO','BLOCK')]
        # Match the existing Windows caller's complete explicit fixture flags;
        # Make's BlockProfile guard precedes these two later default declarations.
        flags+=['X86_64_PIO_CASE=0','X86_64_STARTUP_CASE=0']
        def make(extra):
            return subprocess.run(['make','-n','x86_64-bootstrap',*flags,*extra],cwd=ROOT,capture_output=True,text=True,timeout=15)
        for layout in range(5):
            result=make(['X86_64_FILESYSTEM_LAYOUT='+str(layout),'X86_64_FILESYSTEM_CASE=8'])
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('--filesystem --filesystem-case 8 --filesystem-layout '+str(layout),result.stdout)
        for options in (['X86_64_NATIVE_BLOCK_PROFILE=0'],['X86_64_BLOCK_PROFILE_CASE=1'],
            ['X86_64_NATIVE_FILESYSTEM=0','X86_64_FILESYSTEM_CASE=1'],
            ['X86_64_NATIVE_FILESYSTEM=0','X86_64_FILESYSTEM_LAYOUT=0']):
            result=make(options);self.assertNotEqual(result.returncode,0);self.assertIn('Filesystem',result.stderr)
        for options in (['-FilesystemCase','1'],['-FilesystemLayout','0'],
            ['-NativeFilesystem','-BlockProfileCase','1'],['-NativeFilesystem','-FilesystemLayout','5'],
            ['-NativeFilesystem','-FilesystemCase','9']):
            result=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',*options],
                cwd=ROOT,capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            # Localized PowerShell diagnostics are not necessarily CP1252;
            # validate the exact ASCII selector without a lossy text decoder.
            self.assertNotEqual(result.returncode,0);self.assertIn(b'Filesystem',result.stderr)
    def test_actual_cold_control_paths_and_reap(self):
        source=r.observer_body();tree=ast.parse(source)
        functions={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
        self.assertTrue('cold_control_paths' in functions)
        symbols={'native_pio_fail64':0x1000,'native_pio_emergency_fence64':0x2000,'serial_init64':0x3000,
            'x86_64_scheduler_user_exception64':0x4000,'scheduler_active':0x5000,'scheduler_mode':0x5001,
            'process_run_exception64':0x6000}
        raw={}
        def put(at,data):
            for i,b in enumerate(data):raw[at+i]=b
        def call(at,target):put(at,b'\xe8'+struct.pack('<i',target-at-5))
        call(0x1000,0x2000);call(0x1005,0x3000)
        put(0x4000,b'\x80\x3d'+struct.pack('<i',0x5000-0x4007)+b'\x01\x0f\x85'+bytes(4))
        put(0x400d,b'\x80\x3d'+struct.pack('<i',0x5001-0x4014)+b'\x08\x0f\x84'+struct.pack('<i',0x6000-0x401a))
        class Hook:
            enabled=False
        namespace={'struct':struct,'S':symbols,'mem':lambda a,n:bytes(raw[a+i] for i in range(n)),
            'branch_target':None,'release_arm_hook':Hook(),'release_pending':set(),
            'mode':lambda:8,'d':lambda a:4,'reg':lambda n:0,'release':None,'release_hook':Hook()}
        for name in ('branch_target','cold_control_paths','cold_reap','cold_fail'):
            exec(functions[name],namespace)
        namespace['cold_control_paths']()
        for address in (0x1000,0x1001,0x1005,0x1006,0x4000,0x4002,0x4006,0x400d,0x400f,0x4013,0x4014,0x4016):
            raw[address]^=1
            with self.assertRaises(AssertionError):namespace['cold_control_paths']()
            raw[address]^=1
        registers={'rdi':4,'rsi':2,'rdx':3,'eflags':0}
        namespace.update(reg=lambda n:registers[n],task=lambda slot:[6,3])
        namespace['cold_reap']();self.assertEqual(namespace['release_pending'],{(2,3)})
        self.assertTrue(namespace['release_arm_hook'].enabled)
        with self.assertRaises(AssertionError):namespace['cold_reap']()
        namespace['release_pending'].clear();registers['rdx']=5
        with self.assertRaises(AssertionError):namespace['cold_reap']()
        registers['rdx']=3;registers['eflags']=512
        with self.assertRaises(AssertionError):namespace['cold_reap']()
        registers['rdi']=3;namespace['cold_reap']();self.assertFalse(namespace['release_pending'])
        registers['rsp']=0
        faults=[];namespace.update(q=lambda address:0x100a,fail=lambda:faults.append(1))
        namespace['cold_fail']();self.assertEqual(faults,[1])
        namespace['q']=lambda address:0x1010;namespace['cold_fail']();self.assertEqual(faults,[1])
    def test_actual_pio_hooks_only_cover_pending_lifecycle(self):
        source=r.observer_body();tree=ast.parse(source)
        functions={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
        self.assertIn('cancel_watch',functions)
        class Hook:
            enabled=False
        hooks={name:Hook() for name in ('cancel_hook','trace_before_hook','trace_after_hook')}
        rows={2:[6,3],3:[6,4]};events=[];drains=[]
        namespace=dict(hooks,cancel_pending=set(),task=lambda slot:rows[slot],
            reg=lambda name:2,trace_drain=lambda:drains.append(1),
            pstate=lambda:(0,0,1),emit=lambda kind,**fields:events.append((kind,fields)))
        for name in ('cancel_watch','cancel'):
            exec(functions[name],namespace)
        namespace['cancel_watch']([3,4])
        self.assertTrue(hooks['cancel_hook'].enabled)
        with self.assertRaises(AssertionError):namespace['cancel_watch']([3])
        rows[2][1]=5
        with self.assertRaises(AssertionError):namespace['cancel']()
        self.assertEqual(namespace['cancel_pending'],{3,4})
        rows[2][1]=3;namespace['cancel']()
        self.assertTrue(hooks['cancel_hook'].enabled)
        namespace['reg']=lambda name:3;namespace['cancel']()
        self.assertFalse(hooks['cancel_hook'].enabled)
        self.assertFalse(namespace['cancel_pending'])
        with self.assertRaises(AssertionError):namespace['cancel']()
        for bad in ([],[3,3],[3,4,5],[5]):
            with self.assertRaises(AssertionError):namespace['cancel_watch'](bad)
        self.assertEqual([e[1]['gen'] for e in events],[3,4])
        # Cleanup traps become reachable only after the last live task release;
        # cancellation must already be fully witnessed, and all bytes stay checked.
        self.assertIn("if not any(v['live'] for v in starts.values()):",source)
        self.assertIn('assert not cancel_pending',source)
        self.assertIn('trace_before_hook.enabled=trace_after_hook.enabled=True',source)
        self.assertIn('trace_before_hook.enabled=trace_after_hook.enabled=False',functions['after_clear'])
        self.assertIn("trace_clean(mem(S['native_pio_trace'],12304))",functions['after_clear'])
        self.assertIn('cancel_watch([gen-1])',functions['pio_retire'])
        self.assertIn('cancel_watch([gen-1,gen] if bad else [gen-1])',functions['ipc'])
        self.assertIn('cancel_watch([(owner>>32)-1,owner>>32])',functions['ipc'])
    def test_actual_ipc_drains_snapshot_before_non_send(self):
        tree=ast.parse(r.EXTRA)
        helper=ast.get_source_segment(r.EXTRA,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ipc'))
        calls=[]
        namespace={'mode':lambda:8,'d':lambda address:0,'q':lambda address:49,
            'S':{'scheduler_current_slot':1,'syscall_rax':2},
            'result':lambda:calls.append('snapshot'),'caller_result':lambda:calls.append('snapshot')}
        exec(helper,namespace);namespace['ipc']();self.assertEqual(calls,['snapshot'])
    def test_actual_result_snapshot_without_diagnostic_syscall(self):
        source=(ROOT/'arch/x86_64/user/filesystem.c').read_text()
        helper=re.search(r'static void witness\(reist_fs_client \*c,unsigned operation,int result\) \{.*?\n}',source,re.S).group()
        code=r'''
#include <reist/x86_64/filesystem.h>
static reist_fs_frame frame;
static volatile reist_fs_frame filesystem_result_snapshot;
static volatile uint64_t filesystem_result_record[7];
static unsigned mode=3,syscalls;
#define S0(n) (syscalls++,0)
'''+helper+r'''
int main(void) {
    reist_fs_client c={(4ULL<<32)|3,7,0,0};
    for(unsigned n=0;n<512;n++) frame.bytes[n]=(unsigned char)(n^0xa5);
    witness(&c,6,-110);
    if(syscalls || filesystem_result_record[0]!=0x4e46535250435631ULL ||
       filesystem_result_record[1]!=c.owner || filesystem_result_record[2]!=7 ||
       filesystem_result_record[3]!=6 || filesystem_result_record[4]!=(uint64_t)(int64_t)-110 ||
       filesystem_result_record[5]!=(uintptr_t)&filesystem_result_snapshot || filesystem_result_record[6]!=3)return 1;
    for(unsigned n=0;n<512;n++) {
        if(filesystem_result_snapshot.bytes[n]!=(unsigned char)(n^0xa5))return 2;
        frame.bytes[n]=0;
        if(filesystem_result_snapshot.bytes[n]!=(unsigned char)(n^0xa5))return 3;
    }
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);unit=path/'snapshot.c';unit.write_text(code)
            for opt in ('-O0','-O2'):
                exe=path/(opt[1:]+'.exe')
                result=subprocess.run(['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-I'+str(ROOT/'userspace/sdk/include'),str(unit),'-o',str(exe)],capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))
                result=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,'actual snapshot vector '+str(result.returncode))
    def test_actual_startup_missing_capability_handshake(self):
        source=(ROOT/'arch/x86_64/user/filesystem.c').read_text()
        helper=re.search(r'static int startup\(Control \*c\) \{.*?\n}',source,re.S).group()
        code=r'''
#include <stdint.h>
typedef struct { unsigned char bytes[48]; } Control;
static unsigned control_ep=1,calls,sleeps;
static int first=-9,always;
static int control_receive(unsigned ep,Control *c) {
    (void)c;if(ep!=1)return -5;
    return calls++==0 || always?first:0;
}
static int pause_ms(unsigned ms) { if(ms!=10)return -5;sleeps++;return 0; }
#define S1(n,v) pause_ms(v)
'''+helper+r'''
int main(void) {
    Control c={0};
    if(startup(&c)!=0 || calls!=2 || sleeps!=1)return 1;
    calls=sleeps=0;first=-13;
    if(startup(&c)!=-13 || calls!=1 || sleeps)return 2;
    calls=sleeps=0;first=-32;
    if(startup(&c)!=-32 || calls!=1 || sleeps)return 3;
    calls=sleeps=0;first=-9;always=1;
    if(startup(&c)!=-110 || calls!=20 || sleeps!=20)return 4;
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);unit=path/'startup.c';unit.write_text(code)
            for opt in ('-O0','-O2'):
                exe=path/(opt[1:]+'.exe')
                result=subprocess.run(['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror',str(unit),'-o',str(exe)],capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))
                result=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,'actual startup handshake vector '+str(result.returncode))
    def test_complete_oracle_missing_duplicate_reversed_and_corrupt(self):
        for case in range(9):
            oom=21 if case==7 else None;serial,events=sample(case,2,oom)
            with self.subTest(case=case):
                self.assertEqual(len(r.validate(serial,trace(events),case,2,oom,COUNTS)),8 if case==6 else 12)
                for n in range(len(events)):
                    for bad in (events[:n]+events[n+1:],events[:n]+[events[n]]+events[n:]):
                        with self.assertRaises(ValueError,msg=str((case,n,events[n]['kind']))):r.validate(serial,trace(bad),case,2,oom,COUNTS)
                with self.assertRaises(ValueError):r.validate(serial,trace(list(reversed(events))),case,2,oom,COUNTS)
                for kind,key,value in (('copy','sha','f'*64),('immutable','device',0),('driver_ready','capacity',128),
                    ('retire','sha','0'*64),('release','after',1015),('trace_clean','bytes',12303),('finish','initial',999)):
                    bad=copy.deepcopy(events);next(e for e in bad if e['kind']==kind)[key]=value
                    with self.assertRaises(ValueError,msg=kind):r.validate(serial,trace(bad),case,2,oom,COUNTS)
        for layout in range(5):
            serial,events=sample(0,layout)
            self.assertEqual(len(r.validate(serial,trace(events),0,layout,None,COUNTS)),12)
            bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='result')['sha']='0'*64
            with self.assertRaisesRegex(ValueError,'canonical'):r.validate(serial,trace(bad),0,layout,None,COUNTS)
    def test_actual_observer_composition_and_lifecycle_arms(self):
        source=r.observer_body();tree=ast.parse(source)
        functions={node.name:ast.get_source_segment(source,node) for node in tree.body if isinstance(node,ast.FunctionDef)}
        self.assertIn("allocation_slot==3",functions['allocation'])
        self.assertIn("create_watch_leave(reg('rax')==0xfffffffffffffff4 or reg('rax')&0xffffffff==2)",functions['create_end'])
        self.assertIn("walk_entries.clear()",source)
        self.assertIn("all(not any(mem(DM+f,4096))",source)
        self.assertIn("len(copies)<8",functions['copy'])
        self.assertIn("stack=user(t,0x408000,32768)",functions['start'])
        calls=[]
        namespace={'created':True,'create_begin_hook':type('Hook',(),{'enabled':False})(),
            'copy_hook':type('Hook',(),{'enabled':True})(),'create_end_hook':type('Hook',(),{'enabled':True})()}
        exec(functions['create_watch_leave'],namespace)
        for retry in (False,True):
            namespace['copy_hook'].enabled=namespace['create_end_hook'].enabled=True;namespace['create_begin_hook'].enabled=False
            namespace['create_watch_leave'](retry)
            self.assertEqual(namespace['create_begin_hook'].enabled,retry)
            self.assertFalse(namespace['copy_hook'].enabled or namespace['create_end_hook'].enabled)
    def test_last_reply_and_fault_are_bound_to_live_caller(self):
        for case in (0,1,3):
            serial,events=sample(case)
            index=next(i for i,e in enumerate(events) if e['kind']=='result' and e['gen']==4 and e['sequence']==(9 if case==0 else 1))
            result=events.pop(index)
            release=next(i for i,e in enumerate(events) if e['kind']=='release' and e['gen']==4)
            events.insert(release+1,result)
            self.assertEqual(len(r.validate(serial,trace(events),case,2,None,COUNTS)),12)
            bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='result' and e['gen']==4)['caller']=7
            with self.assertRaisesRegex(ValueError,'caller generation'):r.validate(serial,trace(bad),case,2,None,COUNTS)
            events.remove(result);root=next(i for i,e in enumerate(events) if e['kind']=='release' and e['gen']==1)
            events.insert(root+1,result)
            with self.assertRaisesRegex(ValueError,'caller lifetime'):r.validate(serial,trace(events),case,2,None,COUNTS)
    def test_actual_physical_sector_decoder_and_wrong_bytes(self):
        raw=r.media.image('fat32');namespace={'struct':struct,'hashlib':hashlib,'Hook':lambda *args:type('Hook',(),{'enabled':True})(),
            'emit':lambda *args,**kwargs:None,'CONFIG':{'sectors':70000,'media':{1121:raw[1121*512:1122*512].hex()}}}
        exec(r.EXTRA,namespace);owner=(3<<32)|2;state=(owner,owner^0xffffffffffffffff,0,1,2,1,1,0)
        namespace['out']((1,1,state,(0x3f6,6,0,1,1<<32),b'',0))
        namespace['out']((1,2,state,(0x3f6,2,2,3,1<<32),b'',0))
        item=namespace['devices'][owner];item['identify']=bytearray(512)
        for port,value in ((0x1f2,1),(0x1f3,1121&255),(0x1f4,1121>>8),(0x1f5,0),(0x1f6,0xe0),(0x1f7,0x20)):
            namespace['out']((1,3,state,(port,value,2,3,1<<32),b'',0))
        request=(2,64,4,0,owner,0x1f0,0,16,0,0x410000,500,0)
        data=raw[1121*512:1121*512+32]
        with self.assertRaises(AssertionError):namespace['data']((2,4,state,request,bytes([data[0]^1])+data[1:],16))
        self.assertEqual(len(item['data']),0)
        namespace['data']((2,4,state,request,data,16));self.assertEqual(bytes(item['data']),data)
if __name__=='__main__':unittest.main()
