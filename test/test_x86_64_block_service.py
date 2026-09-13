"""Actual bounded Ring3 block client/server and ATA adapter at O0/O2."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class BlockTests(unittest.TestCase):
    def test_bounded_cost_attribution(self):
        import json
        import diagnose_x86_64_block_costs as d
        counts={}
        for i in range(4096):d.count_attribution(counts,('irq',1,54,0x4008d3))
        self.assertEqual(sum(counts.values()),4096)
        with self.assertRaises(ValueError):d.count_attribution(counts,('irq',1,54,0x4008d3))
        counts={}
        for i in range(256):d.count_attribution(counts,('ipc',i))
        with self.assertRaises(ValueError):d.count_attribution(counts,('ipc',256))
        self.assertEqual(d.sample_attribution(1,0x4008d3,0x4008d3,54),('irq',1,54,0x4008d3))
        self.assertEqual(d.sample_attribution(1,0x4008d4,0x4008d3,54),('irq',1,-1,0x4008d4))
        from collections import defaultdict
        import itertools
        addresses=itertools.count(0x100000,0x1000)
        symbols=defaultdict(lambda:next(addresses))
        c={'symbols':defaultdict(lambda:{'value':next(addresses)})}
        for kind in ('detached','irq','ipc','full-irq'):
            code=d.attribution_commands(kind,symbols,c,ROOT/'build/codex-agent/r83ai-block',bytes(36896),0x405000)
            for section in re.findall(r'^python\n(.*?)^end\n',code,re.M|re.S):compile(section,'<cost-attribution>','exec')
            if kind!='detached':
                self.assertIn('attribution_dump',code)
                self.assertNotRegex(code,r'(?m)^quit$')
                self.assertIn('attribution_callbacks>=4096',code)
        rows=[[['ipc',0,3,-1],4096]]
        self.assertEqual(d.read_attribution('BLOCK_ATTRIBUTION '+json.dumps(rows)),rows)
        for text in ('', 'BLOCK_ATTRIBUTION []', 'BLOCK_ATTRIBUTION nope',
                     'BLOCK_ATTRIBUTION '+json.dumps(rows*2),
                     'BLOCK_ATTRIBUTION '+json.dumps([[['ipc',0,3,-1],4097]]),
                     ('BLOCK_ATTRIBUTION '+json.dumps(rows)+'\n')*2):
            with self.assertRaises(ValueError):d.read_attribution(text)

    def test_exact_terminal_owner_capabilities(self):
        import struct
        import run_qemu_x86_64_block_service as b
        words=[11,11,1]+[v for handle in (257,258,259) for v in (handle,7,1)]+[0]*15
        raw=struct.pack('<27I',*words)
        self.assertEqual(b.terminal_owner_capabilities(raw,11),[257,258,259])
        for offset,value in ((0,10),(1,10),(2,0),(3,0),(4,3),(5,0),(6,257),(12,260),(13,7),(14,1)):
            wrong=words.copy();wrong[offset]=value
            with self.assertRaises(ValueError):b.terminal_owner_capabilities(struct.pack('<27I',*wrong),11)
        for wrong in (raw[:-1],raw+bytes(1)):
            with self.assertRaises(ValueError):b.terminal_owner_capabilities(wrong,11)

    def test_exact_derived_memory_link(self):
        import struct
        import run_qemu_x86_64_block_service as b
        old,new=0xffffffff8018a8f0,0xffffffff8018ac10
        def object_bytes(address):return b'\x7fELF\x01'+bytes(51)+b'\x48\xc7\xc0'+struct.pack('<I',address&0xffffffff)+bytes(range(64))
        before,after=object_bytes(old),object_bytes(new)
        self.assertEqual(b.normalize_memory_link(before,old),b.normalize_memory_link(after,new))
        for raw,address in ((after,old),(after+after,new),(after.replace(b'\xc7',b'\xb8'),new),
                            (after,0x8018ac10),(after,1<<64),(after,0xffffffff7fffffff)):
            with self.assertRaises(ValueError):b.normalize_memory_link(raw,address)
        for offset in range(len(after)):
            if 59<=offset<63:continue # The one explicitly derived imm32 field.
            changed=bytearray(after);changed[offset]^=1
            try:normalized=b.normalize_memory_link(bytes(changed),new)
            except ValueError:continue
            self.assertNotEqual(normalized,b.normalize_memory_link(before,old))

    def test_actual_generated_observer_and_deadline_witness(self):
        import ast,itertools,struct,types
        from collections import defaultdict
        import run_qemu_x86_64_block_service as b
        addresses=itertools.count(0x100000,0x1000)
        symbols=defaultdict(lambda:next(addresses))
        c={'symbols':defaultdict(lambda:{'value':next(addresses)})}
        for case,oom in [(0,None),*((1,n) for n in (0,1,2,3,6,9)),(2,None),(3,None)]:
            code=b.observer(symbols,c,ROOT/'build/codex-agent/r83ai-block',4096,case,oom,bytes(36896),0x405000)
            blocks=re.findall(r'^python\n(.*?)^end\n',code,re.M|re.S)
            self.assertGreater(len(blocks),2)
            for block in blocks:compile(block,'<actual-block-observer>','exec')
        tree=ast.parse(next(x for x in blocks if 'class PioData(' in x))
        node=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='PioData')
        probe=compile(ast.Module(body=[node],type_ignores=[]),'<actual-pio-data-probe>','exec')
        owner=(3<<32)|2;state=(owner,owner^((1<<64)-1),0,10,20,1,10,0)
        original=[2,64,4,0,owner,0x1f0,0,16,0,0x20000,201,0]
        class Breakpoint:
            def __init__(self,*args,**kwargs):pass
        def quit_probe(command):raise RuntimeError(command)
        for change in (None,(0,1),(1,63),(2,3),(3,1),(4,owner-(1<<32)),(5,0x1f1),
                       (6,1),(7,15),(8,1),(10,200),(10,1201),(11,1)):
            q=original.copy()
            if change:q[change[0]]=change[1]
            witnessed={'retired':False,'released':True,'command':0x20,'identify':bytearray(),'data':bytearray()}
            reads=[]
            def mem(address,length):
                reads.append((address,length))
                if address==0x10000 and length==64:return struct.pack('<4IQ4I3Q',*q)
                if address==0x20000 and length==32:return bytes(range(32))
                raise AssertionError('unexpected data read')
            env=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,write=lambda _:None,execute=quit_probe),
                     struct=struct,mem=mem,reg=lambda n:0x10000 if n=='r13' else 16,
                     pio_state=lambda:state,pio_seen={owner:witnessed})
            exec(probe,env)
            if change:
                with self.assertRaisesRegex(RuntimeError,'quit 72'):env['PioData']().stop()
                self.assertEqual(witnessed['data'],b'')
                self.assertNotIn((0x20000,32),reads)
            else:
                self.assertFalse(env['PioData']().stop())
                self.assertEqual(witnessed['data'],bytes(range(32)))

    def test_actual_cached_import_lifecycle(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/user/block_service.c').read_text()
        helpers='\n'.join(re.search(r'static '+kind+r' '+name+r'\(.*?^}',source,re.M|re.S).group()
                          for kind,name in (('void','image_words'),('int64_t','create')))
        mask=re.search(r'^#define MASK .*$',source,re.M).group()
        code='#include "'+(ROOT/'userspace/sdk/include/reist/abi/syscall.h').as_posix()+'"\n'+mask+'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line%d\\n",__LINE__);exit(1);}}while(0)
static unsigned char pool[36896],record[36896],import_blob[1];
static reist_task_startup_v1_t startup;
static unsigned allocations,frees,preparations,imports,fail_alloc=1,fail_prepare=1;
static int64_t result=-12;
static int64_t allocate(uintptr_t n){CHECK(n==36896);allocations++;return fail_alloc?-12:(intptr_t)pool;}
static int64_t release(uintptr_t p){CHECK(p==(uintptr_t)pool);frees++;return 0;}
#define S1(n,p) host_##n((uintptr_t)(p))
#define host_MALLOC allocate
#define host_FREE release
static int reist_x64_image_prepare(void *p,const void *bytes,unsigned n){
    CHECK(p==pool && bytes==import_blob && n==sizeof(import_blob));preparations++;
    for(unsigned i=0;i<36896;i++)pool[i]=(unsigned char)(i^0xa5);
    return fail_prepare?-22:0;
}
static int64_t reist_x64_task_import_profile(const void *p,const reist_task_profile_v1_t *profile,
                                             uint64_t cpu,const reist_task_startup_v1_t *s){
    CHECK(cpu==32 && s==&startup && profile->version==1 && profile->struct_size==40);
    CHECK(profile->masks[0]==MASK && profile->masks[1]==(1ULL<<49) && !profile->masks[2] && !profile->reserved);
    CHECK(p==(imports<2?(const void*)record:(const void*)pool));imports++;
    for(unsigned i=0;i<36896;i++)CHECK(((const unsigned char*)p)[i]==(unsigned char)(i^0xa5));
    return result;
}
'''+helpers+'''
int main(void){
    memset(record,0xcc,sizeof(record));
    if(0)release((uintptr_t)pool); /* Compile the pre-fix missing-cleanup witness. */
    CHECK(create(record,&startup)==-12 && allocations==1 && !preparations && !imports);
    fail_alloc=0;
    CHECK(create(record,&startup)==-22 && allocations==2 && preparations==1 && frees==1 && !imports);
    for(unsigned i=0;i<36896;i++)CHECK(record[i]==0xcc);
    fail_prepare=0;
    CHECK(create(record,&startup)==-12 && allocations==3 && preparations==2 && imports==1);
    for(unsigned i=0;i<36896;i++)CHECK(record[i]==pool[i]);
    result=(3LL<<32)|2;
    CHECK(create(record,&startup)==result && imports==2);
    for(unsigned i=0;i<36896;i++)CHECK(record[i]==0x5a && pool[i]==(unsigned char)(i^0xa5));
    for(unsigned attempt=0;attempt<8;attempt++){
        result=attempt==7?-11:((4LL+attempt)<<32)|2;
        CHECK(create(record,&startup)==result && allocations==3 && preparations==2 && frees==1);
        for(unsigned i=0;i<36896;i++)CHECK(record[i]==0x5a && pool[i]==(unsigned char)(i^0xa5));
    }
    puts("BLOCK_CACHE_HOST_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',code,'BLOCK_CACHE_HOST')

    def test_block_cancellation_and_frame_oracle(self):
        import run_qemu_x86_64_pio as p
        from test_x86_64_pio import PioTests
        for case,oom in [(0,None),*((1,n) for n in (0,1,2,3,6,9)),(2,None),(3,None)]:
            serial,trace=PioTests.sample(case,oom,block=True)
            self.assertEqual(p.validate(serial,trace,case,oom,block=True),2*(len(p.modes(case))+2))
            if 'state=6 ipc=1' in trace:
                for state,ipc in ((1,0),(1,2)):
                    p.validate(serial,trace.replace('state=6 ipc=1',f'state={state} ipc={ipc}'),case,oom,block=True)
                for state,ipc in ((6,2),(1,1),(6,3),(0,0)):
                    with self.assertRaisesRegex(ValueError,'cancellation'):
                        p.validate(serial,trace.replace('state=6 ipc=1',f'state={state} ipc={ipc}',1),case,oom,block=True)
            for label in ('FAMILY_CANCEL','FAMILY_FENCE','TASK_FRAMES_FREE','IMPORT_COPY','STARTUP_ARGS','IMPORT_SCRUB','PIO_RETIRE'):
                if label in trace:
                    with self.assertRaises(ValueError):p.validate(serial,trace.replace(label,'MISSING',1),case,oom,block=True)
            if 'state=6 ipc=0' in trace:
                with self.assertRaisesRegex(ValueError,'cancellation'):
                    p.validate(serial,trace.replace('state=6 ipc=0','state=6 ipc=1',1),case,oom,block=True)

    def test_actual_bulk_import_copy(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/user/block_service.c').read_text()
        helper=re.search(r'static void image_words\(.*?^}',source,re.M|re.S).group()
        code='#include <stdint.h>\n#include <stdio.h>\n'+helper+'''
int main(void){
    unsigned char from[36928],to[36928];
    for(unsigned offset=0;offset<16;offset++){
        for(unsigned n=0;n<sizeof(from);n++){from[n]=(unsigned char)(n^0xa5);to[n]=0xcc;}
        image_words(to+offset+8,from+offset+8);
        for(unsigned n=0;n<sizeof(to);n++)if(to[n]!=(n>=offset+8 && n<offset+8+36896?from[n]:0xcc))return 1;
        image_words(to+offset+8,0);
        for(unsigned n=0;n<sizeof(to);n++)if(to[n]!=(n>=offset+8 && n<offset+8+36896?0x5a:0xcc))return 2;
    }
    puts("BLOCK_IMAGE_COPY_HOST_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',code,'BLOCK_IMAGE_COPY_HOST')

    def test_fixed_sector_profiles(self):
        import run_qemu_x86_64_pio as p
        self.assertEqual(len(p.BLOCK_DISK),65536)
        self.assertEqual(p.BLOCK_DISK[:512],p.SECTOR)
        self.assertEqual(len({p.BLOCK_DISK[i:i+512] for i in range(0,65536,512)}),128)
        self.assertEqual(p.DISK,p.SECTOR*128)
        for case in range(4):self.assertEqual(p.minimum_scrubs(case)-p.minimum_scrubs(case,True),6)

    def test_rpc_oracle_missing_duplicate_reordered(self):
        import run_qemu_x86_64_block_service as b
        for case in range(4):
            events=[];sequence=b.pio.modes(case);count=len(sequence)+2
            for run in range(2):
                for i,mode in enumerate(sequence,3):
                    gen=run*count+i;events.append(f'PIO_BIND gen={gen} recycled=1')
                    if case!=2:
                        for n in range(0 if i==3 else 4,5 if mode else 6):
                            seq=1 if n<4 else n-3;lba=128 if n==2 else 0 if n<4 else 1 if n%2==0 else 127
                            events.append(f'BLOCK_REQUEST gen={gen} n={n} seq={seq} lba={lba}')
                            if n<4 or mode in (0,3):
                                status=(-22,-13,-22,-110)[n] if n<4 else 0
                                data=b'' if status else b.pio.BLOCK_DISK[lba*512:(lba+1)*512]
                                events.append(f'BLOCK_REPLY gen={gen} n={n} status={status} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()} noio={int(bool(status))}')
                            if n>=4 and case!=3:
                                result=-71 if mode==3 else -110 if mode else 0
                                data=bytes([0xcc])*512 if mode else b.pio.BLOCK_DISK[lba*512:(lba+1)*512]
                                events.append(f'BLOCK_RESULT gen={gen} seq={seq} lba={lba} result={result} sha256={hashlib.sha256(data).hexdigest()}')
                    events.append(f'PIO_RETIRE gen={gen} identify=512')
                if case<2:events.append(f'BLOCK_OWNER_RELEASE gen={run*count+1} endpoints=3 automatic=1')
                events.append(f'FAMILY_FENCE slot=0 gen={run*count+1} ipc=1 heap=1 profile=1')
            trace='\n'.join(events);b.validate_rpc(trace,case)
            b.validate_owner_release(trace,case)
            if case<2:
                release=next(e for e in events if e.startswith('BLOCK_OWNER_RELEASE'))
                for bad in (trace.replace(release,'',1),trace+'\n'+release,trace.replace('endpoints=3','endpoints=2',1)):
                    with self.assertRaises(ValueError):b.validate_owner_release(bad,case)
                wrong=events.copy();wrong.remove(release);wrong.insert(0,release)
                with self.assertRaises(ValueError):b.validate_owner_release('\n'.join(wrong),case)
            for run in range(2):
                for i,mode in enumerate(sequence,3):
                    if case in (2,3) or mode not in (0,1,4):continue
                    gen=run*count+i
                    result=next(e for e in reversed(events) if e.startswith(f'BLOCK_RESULT gen={gen} '))
                    retire=f'PIO_RETIRE gen={gen} identify=512'
                    late=events.copy();late.remove(retire);late.insert(late.index(result),retire)
                    b.validate_rpc('\n'.join(late),case) # Complete reply / EPIPE can be consumed after reap.
                    root=f'FAMILY_FENCE slot=0 gen={run*count+1} ipc=1 heap=1 profile=1'
                    late.remove(result);late.insert(late.index(root)+1,result)
                    with self.assertRaises(ValueError):b.validate_rpc('\n'.join(late),case)
                    if i<count:
                        late=events.copy();late.remove(result)
                        next_bind=f'PIO_BIND gen={gen+1} recycled=1'
                        late.insert(late.index(next_bind)+1,result)
                        with self.assertRaises(ValueError):b.validate_rpc('\n'.join(late),case)
            for i,event in enumerate(events):
                if not event.startswith(('BLOCK_REQUEST','BLOCK_REPLY','BLOCK_RESULT')):continue
                for bad in (events[:i]+events[i+1:],events[:i]+[event]+events[i:]):
                    with self.assertRaises(ValueError):b.validate_rpc('\n'.join(bad),case)
                if i and events[i-1].startswith('BLOCK_'):
                    with self.assertRaises(ValueError):b.validate_rpc('\n'.join(events[:i-1]+[events[i],events[i-1]]+events[i+1:]),case)
            if case!=2:
                for bad in (trace.replace('noio=1','noio=0',1),trace.replace('bytes=512','bytes=511',1),trace.replace('seq=1','seq=2',1),trace+'\nBLOCK_REQUEST invalid'):
                    if bad==trace:continue # Owner loss has no completed success reply.
                    with self.assertRaises(ValueError):b.validate_rpc(bad,case)

    def test_actual_protocol_and_service(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ai-block'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            commands=([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                '-fno-sanitize=all','-ffreestanding','-fno-builtin','-Wall','-Wextra','-Werror',
                '-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                ROOT/'test/x86_64_block_service_host.c','-o',exe],[exe])
            for phase,command in zip(('build','run'),commands):
                r=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,
                    text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(opt+'-'+phase+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2500:])
                if phase=='run':self.assertIn('NATIVE_BLOCK_HOST_OK',r.stdout)

if __name__=='__main__':unittest.main()
