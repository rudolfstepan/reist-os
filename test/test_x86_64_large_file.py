"""Real C regression of the separately versioned read/capture profile."""
from pathlib import Path
import os,struct,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class LargeFileTests(unittest.TestCase):
    def test_bounded_parallel_evidence_hashes(self):
        import hashlib,tempfile
        import verify_x86_64_large_file as verifier
        with tempfile.TemporaryDirectory(prefix='hash-proof-',dir=ROOT/'build/codex-agent/r83bv-large-file') as name:
            folder=Path(name);expected={};paths=[]
            for n in range(259):
                path=folder/str(n);raw=bytes([n%256])*(2*1024*1024+1 if n==258 else n)
                path.write_bytes(raw);paths.append(path)
                expected[path.relative_to(ROOT).as_posix()]=hashlib.sha256(raw).hexdigest()
            self.assertEqual(verifier.parallel_digests(iter(paths)),expected)
            with self.assertRaisesRegex(ValueError,'unique raw evidence path'):
                verifier.parallel_digests([paths[0],paths[0]])
            paths[-1].unlink()
            with self.assertRaises(FileNotFoundError):verifier.parallel_digests(paths)

    def test_retained_evidence_source_binding(self):
        from unittest.mock import patch
        import verify_x86_64_large_file as verifier
        self.assertEqual(len(verifier.retained_binding()),11)
        changed=verifier.sources();changed['scripts/run_qemu_x86_64_large_file.py']='0'*64
        with patch.object(verifier,'sources',return_value=changed):
            with self.assertRaisesRegex(ValueError,'unchanged capture/guest source set'):
                verifier.retained_binding()
        changed=verifier.sources();changed['unexpected-new-source.c']='0'*64
        with patch.object(verifier,'sources',return_value=changed):
            with self.assertRaisesRegex(ValueError,'unchanged capture/guest source set'):
                verifier.retained_binding()

    def test_legacy_candidate_admission(self):
        import hashlib
        import run_qemu_x86_64_shell_session as legacy
        image=ROOT/'build/codex-agent/r83ba-wide-file/legacy/x86_64/reist-x86_64-bootstrap.elf'
        folder=ROOT/'build/codex-agent/r83bv-large-file'/('legacy-admission-'+uuid.uuid4().hex)
        class Admitted(Exception):pass
        def binding():raise Admitted()
        with self.assertRaisesRegex(ValueError,'frozen runtime admission'):
            legacy.run_matrix(image,folder,'0'*40,binding)
        with self.assertRaises(Admitted):
            legacy.run_matrix(image,folder,hashlib.sha256(b'frozen candidate').hexdigest(),binding)
        self.assertFalse(folder.exists())

    def test_declared_observer_case_admission(self):
        import tempfile
        import run_qemu_x86_64_large_file as runtime
        image=ROOT/'build/codex-agent/r83bv-large-file/build24/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=runtime.image_config(image)
        for spec in runtime.CASES:
            with self.subTest(case=spec[0]), tempfile.TemporaryDirectory(
                    prefix='case-admission-',dir=image.parents[2]) as name:
                folder=Path(name);module=runtime.case_namespace(spec)
                selected=dict(config,app_case=spec[0],large_case_ram=spec[3])
                module.app_files=runtime.case_files(spec,files)
                # The shell passes logical names; the independent wire model
                # must return exact standard FAT 8.3 metadata and contents.
                for logical,content in module.app_files.items():
                    wire='largetst.prg' if spec[2]<2 and logical=='largetest.prg' else logical
                    for operation in (5,6):
                        request=bytearray(512);path=('/'+wire).encode()
                        struct.pack_into('<6I',request,0,1,512,operation,0,len(path),0)
                        if operation==6:struct.pack_into('<I',request,28,256)
                        offset=36 if operation==6 else 24
                        request[offset:offset+len(path)]=path
                        status,answer=module.fs_expected_response(bytes(request),spec[2],module.app_files)
                        self.assertEqual(status,0)
                        if operation==5:self.assertEqual(struct.unpack_from('<I',answer,476)[0],len(content))
                        else:self.assertEqual(answer[228:228+min(256,len(content))],content[:256])
                wrong=dict(selected,large_case_ram=4096 if spec[3]==8192 else 8192)
                with self.assertRaisesRegex(ValueError,'case/layout'):
                    module.observer(wrong,records,folder,spec[1],spec[2])
                with self.assertRaisesRegex(ValueError,'matrix member'):
                    module.validate_capture('', '',folder,wrong,records,b'',spec[1],spec[2],module.app_files)
                code=module.observer(selected,records,folder,spec[1],spec[2])
                compile(code.split('python\n',1)[1].rsplit('\nend',1)[0],
                        '<declared-case-observer>','exec')
                with self.assertRaisesRegex(ValueError,'complete kernel progress'):
                    module.validate_capture('', '',folder,selected,records,b'',spec[1],spec[2],module.app_files)

    def test_private_replay_equivalence(self):
        import base64,binascii,json,random
        import run_qemu_x86_64_large_file as runtime
        selected=runtime.normal_namespace();rng=random.Random(117)
        packed=[]
        for size in (1,3,4,255,4096,65000):
            for value in ('a'*size,'0'*size,''.join(rng.choice('012abXYZ :{}\\"') for _ in range(size))):
                line='SHELL_SESSION '+json.dumps(dict(kind='return',value=value))+'\n'
                if len(line)<=65536:packed.append(runtime.wide.encode_evidence(line))
        def outcome(fn,*args):
            try:return ('ok',fn(*args))
            except Exception as error:return (type(error).__name__,str(error))
        for encoded in packed:
            for trace in (encoded,encoded[:-1],encoded.replace('WIDE_D1','WIDE_D2'),encoded.replace('WIDE_D1 ','WIDE_D1 0',1)):
                self.assertEqual(outcome(selected.decode_evidence,trace),outcome(runtime.wide.decode_evidence,trace))
        for raw in (b'\xfe',b'\xff',b'\xff\x01\x00\x00',b'abc'*100,b'\xff\xff\xff\xff'):
            trace='WIDE_D1 16 00000000 '+base64.b64encode(raw).decode()+'\n'
            self.assertEqual(outcome(selected.decode_evidence,trace),outcome(runtime.wide.decode_evidence,trace))
        def message(data):return (struct.pack('<3I',1,140,len(data))+data).ljust(140,b'\0').hex()
        def operation(gen,op,data=b'ping',endpoint=3,result=0):
            raw=message(data)
            return [dict(kind='call',gen=gen,op=op),dict(kind='return',gen=gen,op=op,
                profile_denied=False,args=[endpoint,0,1000,0,0,0],result=result,before=raw,after=raw)]
        send=operation(1,53);receive=operation(2,54)
        samples=[send+receive,send+receive+send+receive,send+send+receive,
                 receive+send,send+operation(1,54),send+operation(2,54,endpoint=4),
                 send+operation(2,54,b'changed'),send+operation(2,54,result=-110)]
        for _ in range(48):
            sequence=[]
            for _ in range(rng.randrange(1,12)):
                sequence+=operation(rng.randrange(1,5),rng.choice((53,54)),rng.choice((b'a',b'b')),rng.randrange(1,4))
            samples.append(sequence)
        for sample in samples:
            self.assertEqual(outcome(selected.validate_ipc_delivery,sample),
                             outcome(runtime.wide.old.validate_ipc_delivery,sample))

    def test_rejected_capture_oracle(self):
        import run_qemu_x86_64_large_file as runtime
        def request(op,offset=0):
            path=b'/largetest.prg';raw=bytearray(512)
            struct.pack_into('<6I',raw,0,1,512,op,0,len(path),0)
            if op==6:struct.pack_into('<2I',raw,24,offset,256)
            begin=24 if op==5 else 36;raw[begin:begin+len(path)]=path
            return raw
        def message(op,owner,sequence,reply,frame,status=0):
            body=struct.pack('<4I4QIiQ',1,64,op,reply,owner,sequence,10000,0,len(frame),status,0)+frame
            return (struct.pack('<3I',2,2060,len(body))+body).ljust(2060,b'\0').hex()
        for spec in (runtime.CASES[5],runtime.CASES[6]):
            size=1048577 if spec[4]=='oversize' else 1048576
            files={'largetest.prg':bytes(size)};events=[]
            for run in (1,2):
                events.append(dict(kind='start',slot=0,run=run,gen=run));owner=((run+10)<<32)|3
                requests=[request(5)]
                if spec[4]=='unsupported':requests +=[request(6,n) for n in range(0,274433,256)]
                for sequence,frame in enumerate(requests,1):
                    op=struct.unpack_from('<I',frame,8)[0];answer=bytearray(frame);status=0
                    if op==5:struct.pack_into('<I',answer,476,size)
                    elif sequence==len(requests):answer=bytearray();status=-110
                    else:struct.pack_into('<I',answer,32,256)
                    events.append(dict(kind='return',gen=run,result=0,op=53,before=message(op,owner,sequence,0,frame)))
                    events.append(dict(kind='return',gen=run,result=0,op=54,after=message(op,owner,sequence,1,answer,status)))
            runtime.validate_case_history(spec,events,files)
            for damaged in (events[:-1],events+[events[-1]],events[1:]):
                with self.assertRaises(ValueError):runtime.validate_case_history(spec,damaged,files)

    def test_qualification_case_media(self):
        import ast
        import run_qemu_x86_64_large_file as runtime
        folder=ROOT/'build/codex-agent/r83bv-large-file/case-host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        raw=bytearray(1048576);raw[:7]=b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
        struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096);raw[120]=0xc3
        files={name:bytes(raw) if name=='largetest.prg' else b'fixture\n' for name in runtime.check.NAMES}
        elf=folder/'input.prg';elf.write_bytes(raw)
        source=(ROOT/'test/x86_64_large_file_host.c').read_text(encoding='utf-8')
        for before,after in (
            ('argc==4 || argc==5','argc==4 || argc==5 || argc==6'),
            ('int unsupported=','int oversized=argc==6;int unsupported='),
            ('unsupported||deadline_limited?1U:20U','unsupported||deadline_limited||oversized?1U:20U'),
            ('argc==5?argv[4]','argc>=5?argv[4]'),
            ('int error=unsupported?-110:deadline_limited?-116:0,untouched=0',
             'int error=oversized?-27:unsupported?-110:deadline_limited?-116:0,untouched=oversized')):
            self.assertEqual(source.count(before),1);source=source.replace(before,after)
        c=folder/'case.c';c.write_text(source,encoding='utf-8');exe=folder/'case.exe'
        args=['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-DREIST_NATIVE_SHELL_SESSION=1',
              '-DREIST_NATIVE_LARGE_FILE=1','-DREIST_NATIVE_LARGE_IMAGE=1','-I.','-Iuserspace/sdk/include',str(c),
              'userspace/sdk/lib/x86_64/file_image.c','userspace/sdk/lib/x86_64/image.c',
              'userspace/storage/lib/native_block.c','userspace/storage/lib/native_filesystem.c',
              'userspace/storage/lib/vfs_shadow_fat32.c','userspace/storage/lib/vfs_shadow_ext2.c','-o',str(exe)]
        def run(args):
            result=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,timeout=90)
            (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-2000:])
        run(args)
        self.assertEqual(len(runtime.CASES),12)
        for spec in runtime.CASES:
            with self.subTest(case=spec[0]):
                module=runtime.case_namespace(spec);ast.parse(module.observer_body())
                self.assertEqual(module.CASES,(spec[1:4],))
                selected=runtime.case_files(spec,files);disk=runtime.case_medium(spec,selected)
                if spec[4] in ('unsupported','oversize'):
                    path=folder/(spec[0]+'.raw');path.write_bytes(disk)
                    run([exe,path,runtime.wide.media.LAYOUTS[spec[2]],elf,'/largetest.prg']+
                        (['oversize'] if spec[4]=='oversize' else []))

    def test_actual_profile_pio_selection(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_session.c').read_text(encoding='utf-8')
        body=source[source.index('static int service_pio('):source.index('static int64_t service_task(')]
        folder=ROOT/'build/codex-agent/r83bv-large-file/pio-selection'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        c=folder/'selection.c'
        c.write_text('''#include <reist/x86_64/pio.h>
#include <string.h>
static struct { unsigned version; } session_service;
static unsigned calls;
static reist_native_pio_request actual;
static int fake(reist_native_pio_request *q) { actual=*q;calls++;return 7; }
#define reist_x64_pio fake
'''+body+'''
int main(void) {
    const uint64_t owner=(UINT64_C(3)<<32)|2;
    for(unsigned version=1;version<=3;version++) {
        session_service.version=version;
        for(unsigned op=1;op<=5;op+=4) {
            calls=0;
            if(service_pio(0,owner,op)!=7 || calls!=1)return 1;
            reist_native_pio_request expected={1,64,op,0,owner,0,0,0,0,0,0,0};
#ifdef REIST_NATIVE_LARGE_FILE
            if(version==3 && op==1){expected.version=3;expected.reserved1=128;}
#endif
            if(memcmp(&actual,&expected,64))return 2;
        }
    }
#ifdef REIST_NATIVE_LARGE_FILE
    calls=0;reist_native_pio_request saved=actual;
    if(service_pio(0,2,1)!=-22 || calls || memcmp(&saved,&actual,64))return 3;
#endif
    return 0;
}
''',encoding='utf-8')
        for selected in (False,True):
            exe=folder/('selected.exe' if selected else 'old.exe')
            command=['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iuserspace/sdk/include']
            if selected:command+=['-DREIST_NATIVE_LARGE_FILE=1']
            for args in (command+[str(c),'-o',str(exe)],[str(exe)]):
                result=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60)
                (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
                self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))

    def test_retained_artifact_binding(self):
        import hashlib,tempfile
        import verify_x86_64_large_file as verifier
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            root=Path(folder);file=root/'accepted.bin';file.write_bytes(b'accepted')
            items={'accepted.bin':hashlib.sha256(b'accepted').hexdigest()}
            self.assertEqual(verifier.retained_artifacts(root,items),1)
            file.write_bytes(b'changed')
            with self.assertRaises(ValueError):verifier.retained_artifacts(root,items)
            for invalid in ({},{'../outside':items['accepted.bin']},
                            {'accepted.bin':'z'*64},{str(file.resolve()):items['accepted.bin']}):
                with self.assertRaises(ValueError):verifier.retained_artifacts(root,invalid)

    def test_pio_trace_profile(self):
        import run_qemu_x86_64_large_file as runtime
        old=runtime.wide.namespace().file.block.TRACE_CORE
        selected=runtime.observer_namespace().file.block.TRACE_CORE
        ns=dict(struct=struct);exec(selected,ns)
        raw=bytearray(12304);struct.pack_into('<2Q',raw,0,1,0)
        owner=(3<<32)|2;tag=0xffffff7f00000080
        struct.pack_into('<2Q8Q5Q',raw,16,1,1,owner,owner^((1<<64)-1),0,10,10,128,10,tag,
                         0x1f7,0x20,2,3,1<<32)
        self.assertEqual(len(ns['trace_decode'](bytes(raw),0)),1)
        for offset,value in ((16+16+5*8,129),(16+16+7*8,0),(16+16+7*8,tag^1),
                             (16+16+7*8,tag^(1<<32)),(16+16+1*8,0)):
            damaged=bytearray(raw);struct.pack_into('<Q',damaged,offset,value)
            with self.assertRaises(ValueError):ns['trace_decode'](bytes(damaged),0)
        prior=dict(struct=struct);exec(old,prior)
        with self.assertRaises(ValueError):prior['trace_decode'](bytes(raw),0)
        self.assertEqual(runtime.wide.namespace().file.block.TRACE_CORE,old)

    def test_two_root_host_bounds(self):
        import ast,inspect
        import run_qemu_x86_64_large_file as runtime
        prior=runtime.wide.selected_source()
        module=runtime.normal_namespace()
        source=inspect.getsource(module.capture_namespace)
        for text in ('started+597','deadline=console_started+597',
                     'time.monotonic()-console_started>600',
                     'time.monotonic()-capture_started>600'):
            self.assertIn(text,source)
        # Compile the actual nested capture adapters, including WHPX's
        # composed path, without running a VM or altering shared globals.
        capture=module.stepped_capture_namespace()
        self.assertTrue(callable(capture['capture']))
        feeder=module.SessionFeeder(module.input_plan(0))
        writes=[]
        feeder.pump('', '', writes.append, 596.999)
        self.assertFalse(writes)
        with self.assertRaises(ValueError):feeder.pump('', '', writes.append,597)
        import time,types
        with self.assertRaises(ValueError):
            module.stepped_capture_namespace(time.monotonic()-598)['session_origin']()
        with self.assertRaises(ValueError):
            runtime.large_fixture_run(types.SimpleNamespace(started=time.monotonic()-601))
        code=runtime.selected_source()
        self.assertNotIn('<=128*1024*1024',code)
        self.assertIn("total+proof['bytes']+cpu_bytes+stored_bytes<=1024*1024*1024",code)
        self.assertIn('len(trace.encode())<=1024*1024*1024',code)
        self.assertNotIn('<=512*1024*1024',code)
        self.assertIn('snapshot_bytes<=256*1024*1024',module.OBSERVER)
        line='SHELL_SESSION {"kind": "return", "result": 0}\n'
        packed=runtime.wide.encode_evidence(line)
        self.assertEqual(module.decode_evidence(packed),line)
        self.assertEqual(module.decode_evidence.__globals__['DECODE_LIMIT'],1024*1024*1024)
        self.assertEqual(runtime.wide.DECODE_LIMIT,512*1024*1024)
        decoded=ast.parse(inspect.getsource(runtime.wide.decode_evidence))
        bound=next(n for n in ast.walk(decoded) if isinstance(n,ast.Compare)
                   and ast.unparse(n)=='total + length > DECODE_LIMIT')
        for total,exceeded in ((1024*1024*1024-65536,False),(1024*1024*1024-65535,True)):
            self.assertEqual(eval(compile(ast.Expression(bound),'<BV-decoded-bound>','eval'),
                                  dict(total=total,length=65536,DECODE_LIMIT=1024*1024*1024)),exceeded)
        self.assertEqual(runtime.wide.decode_evidence(packed),line)
        for bad in (packed[:-1],packed.replace('WIDE_D1','WIDE_D9'),packed.replace(' 000',' zzz')):
            if bad==packed:continue
            with self.assertRaises(ValueError):module.decode_evidence(bad)
        self.assertEqual(runtime.wide.selected_source(),prior)
        self.assertIn('snapshot_bytes<=128*1024*1024',prior)
        # Exact capacity predicates on the emitted producer/consumer.
        for tree,name in ((ast.parse(module.OBSERVER),'snapshot_bytes'),
                          (ast.parse(code),'self.bytes')):
            expr=next(n for n in ast.walk(tree) if isinstance(n,ast.Compare)
                      and ast.unparse(n.left)==name and '256 * 1024 * 1024' in ast.unparse(n))
            import types
            for size,expected in ((256*1024*1024,True),(256*1024*1024+1,False)):
                env={name:size} if name=='snapshot_bytes' else {'self':types.SimpleNamespace(bytes=size)}
                self.assertEqual(eval(compile(ast.Expression(expr),'<BV-host-bound>','eval'),env),expected)

    def test_observer_transport(self):
        from test_x86_64_large_file_observer import ObserverTests
        ObserverTests("test_actual_transport_o0_o2").test_actual_transport_o0_o2()
        ObserverTests("test_exact_isolated_patch").test_exact_isolated_patch()
        ObserverTests("test_client_response_mutations").test_client_response_mutations()
        ObserverTests("test_native_control_o0_o2").test_native_control_o0_o2()
        ObserverTests("test_native_snapshot_o0_o2").test_native_snapshot_o0_o2()
        ObserverTests("test_native_adapter").test_native_adapter()
        ObserverTests("test_native_sparse").test_native_sparse()
        ObserverTests("test_native_pinned_views").test_native_pinned_views()
        ObserverTests("test_five_site_control").test_five_site_control()
        ObserverTests("test_native_five_snapshot").test_native_five_snapshot()
        ObserverTests("test_native_five_receipt_replay").test_native_five_receipt_replay()
        ObserverTests("test_native_replay_backpressure").test_native_replay_backpressure()
        ObserverTests("test_whpx_timing").test_whpx_timing()
        ObserverTests("test_windows_exclusive_trace_open").test_windows_exclusive_trace_open()

    def test_cleanup_snapshot_envelope(self):
        import ast,hashlib,tempfile
        import run_qemu_x86_64_large_file as runtime
        module=runtime.observer_namespace()
        tree=ast.parse(module.OBSERVER)
        producer=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='snapshot')
        cleanup=next(n for n in ast.walk(ast.parse(runtime.selected_source()))
                     if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                     and n.func.id=='require' and len(n.args)==2
                     and isinstance(n.args[1],ast.Constant)
                     and n.args[1].value=='kernel cleanup bytes')
        cleanup_code=compile(ast.Expression(cleanup),'<BV-cleanup-replay>','eval')
        # Execute the real emitted writer and independent reader, including
        # the combined cleanup record rather than just the import record.
        size=sum(n for _,n in module.admission.ZERO_RANGES)+12408+4096
        self.assertGreater(size,1052960)
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            env=dict(snapshots=0,snapshot_bytes=0,OUT=Path(folder),hashlib=hashlib)
            exec(compile(ast.Module(body=[producer],type_ignores=[]),'<BV-snapshot>','exec'),env)
            reader=module.Snapshots(folder)
            for length in (size,2*1024*1024):
                data=bytes(length)
                ref=env['snapshot'](data)
                self.assertEqual(reader.read(ref,length),data)
                eval(cleanup_code,dict(raw=reader,row={'raw':ref},size=length,require=module.require))
                with self.assertRaises((AssertionError,ValueError)):
                    reader.read(ref,length-1)
            for offset in (0,size-1):
                data=bytearray(size);data[offset]=1
                ref=env['snapshot'](data)
                with self.assertRaises((AssertionError,ValueError)):
                    eval(cleanup_code,dict(raw=reader,row={'raw':ref},size=size,require=module.require))
            reader.finish()
            with self.assertRaises(AssertionError):env['snapshot'](bytes(2*1024*1024+1))
            self.assertEqual(len(list(Path(folder).glob('session-*.bin'))),4)
            oversized=dict(file='session-0003.bin',bytes=2*1024*1024+1,sha256='0'*64)
            with self.assertRaises((AssertionError,ValueError)):reader.read(oversized)
        # The private envelope must not relax the established wide profile.
        self.assertNotIn("reference['bytes']<=2*1024*1024",runtime.wide.selected_source())

    def test_large_memory_read_preserves_transport_limits(self):
        import types
        import run_qemu_x86_64_large_file as runtime
        calls=[]
        def read(address,size):
            calls.append((address,size));self.assertLessEqual(size,270336)
            return bytes([len(calls)])*size
        reader=types.SimpleNamespace(read=read)
        raw=runtime.chunked_read(reader,0x100000000,1056768)
        self.assertEqual(len(calls),4)
        self.assertEqual(raw,b''.join(bytes([n+1])*size for n,(_,size) in enumerate(calls)))
        self.assertEqual(calls,[(0x100000000+i*270336,min(270336,1056768-i*270336)) for i in range(4)])
        for address,size in ((0,1056769),(-1,1),(2**64-1,2),(True,1),(0,True)):
            calls.clear()
            with self.assertRaises(ValueError):runtime.chunked_read(reader,address,size)
            self.assertFalse(calls)
        calls.clear();self.assertEqual(runtime.chunked_read(reader,0,0),b'');self.assertFalse(calls)
        for failure in ('short','exception'):
            calls.clear()
            def broken(address,size):
                calls.append((address,size))
                if len(calls)==2:
                    if failure=='exception':raise ValueError('transport failed')
                    return b''
                return bytes(size)
            with self.assertRaises(ValueError):runtime.chunked_read(types.SimpleNamespace(read=broken),0,1056768)
            self.assertEqual(len(calls),2)

    def test_unsupported_ext2_fixture_valid_double_indirect(self):
        import build_x86_64_large_file as producer
        value=(bytes(range(251))*4200)[:1048576]
        raw=producer.image('ext2-1k',value);bs=1024;inode=5*bs+11*128
        u32=lambda at:struct.unpack_from('<I',raw,at)[0]
        count=(len(value)+bs-1)//bs;blocks=[u32(inode+40+4*n) for n in range(12)]
        single=u32(inode+88);double=u32(inode+92)
        blocks.extend(u32(single*bs+4*n) for n in range(256))
        leaves=[u32(double*bs+4*n) for n in range(3)]
        self.assertEqual(len(set(leaves+[single,double])),5)
        remaining=count-len(blocks)
        for leaf in leaves:
            take=min(256,remaining)
            blocks.extend(u32(leaf*bs+4*n) for n in range(take));remaining-=take
            self.assertFalse(any(raw[leaf*bs+take*4:(leaf+1)*bs]))
        self.assertEqual(remaining,0)
        self.assertEqual(len(set(blocks)),count)
        self.assertFalse(set(blocks)&set(leaves+[single,double]))
        self.assertEqual(b''.join(raw[n*bs:(n+1)*bs] for n in blocks),value)
        self.assertEqual(u32(inode+28),(count+5)*2)
        for block in blocks+leaves+[single,double]:
            bit=block-1
            self.assertTrue(raw[3*bs+bit//8]&(1<<(bit%8)))

    def test_complete_executable_capture_oracle(self):
        import run_qemu_x86_64_large_file as runtime
        import check_x86_64_large_file_media as media
        def fixture(size,layout):
            files={name:b'fixture' for name in media.NAMES}
            files['largetest.prg']=(bytes(range(256))*((size+255)//256))[:size]
            name='largetst' if layout<2 else 'largetest';path=('/'+name+'.prg').encode()
            root=dict(gen=1);child=dict(gen=4,args=[name])
            bound=runtime.disk_files(layout,files);oracle=runtime.storage_oracle(layout);events=[]
            requests=[(5,0)]+[(6,n) for n in range(0,size,256)]+[(6,size)]
            for seq,(op,offset) in enumerate(requests,1):
                q=bytearray(512);struct.pack_into('<6I',q,0,1,512,op,0,len(path),0)
                start=24 if op==5 else 36;q[start:start+len(path)]=path
                if op==6:struct.pack_into('<2I',q,24,offset,256)
                status,reply=oracle['fs_expected_response'](bytes(q),layout,bound)
                self.assertEqual(status,0)
                def envelope(payload,response):
                    header=struct.pack('<4I4QIiQ',1,576,op,response,3<<32|3,seq,120000,0,0,0,0)
                    frame=header+payload
                    return (struct.pack('<3I',2,2060,len(frame))+frame+bytes(2060-12-len(frame))).hex()
                events.append(dict(kind='call',op=53,gen=1,profile_denied=False,entered=seq*2,before=envelope(q,0)))
                events.append(dict(kind='return',op=54,gen=1,result=0,now=seq*2+1,after=envelope(reply,1)))
            create=struct.pack('<4I6Q',7,64,1,0,0,0,0,0,0,0)
            events.append(dict(kind='return',op=132,gen=1,result=4<<32|4,entered=10000,now=10001,before=create.hex()))
            return events,root,child,files
        for size,layout in ((513,0),(513,1),(1048576,3),(513,4)):
            events,root,child,files=fixture(size,layout)
            proof=runtime.validate_executable_capture(events,root,child,layout,files)
            self.assertEqual(proof['bytes'],size)
            self.assertEqual(proof['calls'],2+(size+255)//256)
            if size!=513:continue
            variants=[events[:-1],events[:-3]+events[-1:],events[2:],
                      events[:2]+events[4:6]+events[2:4]+events[6:]]
            for index,key,value in ((-1,'now',120003),(-1,'before',(struct.pack('<4I6Q',6,64,1,0,0,0,0,0,0,0)).hex()),
                                    (3,'now',1)):
                changed=list(events);changed[index]=dict(events[index],**{key:value});variants.append(changed)
            for at in (12+64+32,12+64+228):
                changed=list(events);raw=bytearray.fromhex(events[3]['after']);raw[at]^=1
                changed[3]=dict(events[3],after=raw.hex());variants.append(changed)
            for changed in variants:
                with self.assertRaises(ValueError):runtime.validate_executable_capture(changed,root,child,layout,files)

    def test_disabled_build_projection(self):
        import verify_x86_64_large_file as verifier
        self.assertTrue(verifier.build_projection()['passed'])

    def test_mixed_record_observer_geometry(self):
        import ast,types
        import run_qemu_x86_64_large_file as runtime
        source=runtime.selected_source()
        module=types.ModuleType('bv_host_observer')
        module.__file__=str(ROOT/'scripts/run_qemu_x86_64_large_file.py')
        exec(compile(source,'<bv-host-observer>','exec'),module.__dict__)
        ast.parse(module.OBSERVER)
        context_loop=next(n for n in ast.walk(ast.parse(module.OBSERVER))
                          if isinstance(n,ast.For) and isinstance(n.target,ast.Name)
                          and n.target.id=='address' and 'elf_context_store' in ast.unparse(n.iter))
        context_check=next(n.args[0] for n in ast.walk(ast.parse(source))
                           if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                           and n.func.id=='require' and len(n.args)==2
                           and isinstance(n.args[1],ast.Constant) and n.args[1].value=='ELF staging cleanup')
        clean=bytearray(2320);clean[2304:2308]=b'\x78\x56\x34\x12'
        for bad in (None,0,2048,2303,2308,2319):
            data=bytearray(clean)
            if bad is not None:data[bad]=1
            reads=[]
            def read_context(address,size):
                reads.append((address,size));return bytes(data)
            env=dict(S=dict(elf_context_window=0,elf_context_store=2320),
                     mem=read_context,contexts=[])
            code=compile(ast.Module(body=[context_loop],type_ignores=[]),'<BV-context>','exec')
            if bad is None:
                exec(code,env)
                self.assertEqual(reads,[(n*2320,2320) for n in range(14)])
            else:
                with self.assertRaises(AssertionError):exec(code,env)
            self.assertEqual(eval(compile(ast.Expression(context_check),'<BV-context-replay>','eval'),
                                  dict(contexts=bytes(clean)*13+bytes(data))),bad is None)
        authority=next(n.value for n in ast.walk(ast.parse(module.OBSERVER))
                       if isinstance(n,ast.keyword) and n.arg=='authority')
        reads=[]
        def stopped_mem(address,size):
            self.assertLess(size,32768);reads.append((address,size))
            return bytes([address//16384])*size
        captured=eval(compile(ast.Expression(authority),'<BV-authority>','eval'),
                      dict(snapshot=lambda b:b,mem=stopped_mem,S=dict(scheduler_tasks=0,family_records=32768),op=114,denied=False))
        self.assertEqual(reads,[(0,16384),(16384,16384),(32768,512)])
        self.assertEqual(captured,bytes(16384)+bytes([1])*16384+bytes([2])*512)
        prior=runtime.wide.namespace()
        original=(prior.file.FILE_RAM_BATCH,prior.file.FILE_USER_READ,
                  prior.admission.ZERO_RANGES,prior.admission.wide.OBSERVER)
        selected=runtime.observer_namespace()
        ast.parse(selected.observer_body())
        reference=runtime.normal_namespace()
        ast.parse(reference.observer_body())
        self.assertEqual(reference.CASES,((0,3,4096),))
        self.assertEqual(reference.input_plan(0)[0],((0,b'largetest\ncat /data.txt\nexit\n'),))
        self.assertEqual(original,(prior.file.FILE_RAM_BATCH,prior.file.FILE_USER_READ,
                         prior.admission.ZERO_RANGES,prior.admission.wide.OBSERVER))
        self.assertEqual(dict(selected.admission.ZERO_RANGES)['scheduler_tasks'],32768)
        self.assertEqual(dict(selected.admission.ZERO_RANGES)['elf_import_record'],1052960)
        # Execute the emitted page reader on all 261 owned frames. Preserve order
        # and exact bytes, reject duplicates/range violations before any read.
        reads=[];frames=[0x100000000+n*4096 for n in range(261)]
        def mem(address,size):
            reads.append((address,size))
            self.assertLessEqual(size,66*4096)
            self.assertEqual(size%4096,0)
            return b''.join(bytes([(address//4096+n)%256])*4096 for n in range(size//4096))
        ns=dict(struct=struct,mem=mem,DM=0,MASK=0x000ffffffffff000)
        exec(selected.file.FILE_RAM_BATCH,ns)
        actual=ns['file_pages'](list(reversed(frames)))
        self.assertEqual(actual,[bytes([(f//4096)%256])*4096 for f in reversed(frames)])
        self.assertEqual(sum(n for _,n in reads),261*4096)
        for bad in (frames+[frames[-1]+4096],frames+[frames[0]],frames[:-1]+[1]):
            reads.clear()
            with self.assertRaises(AssertionError):ns['file_pages'](bad)
            self.assertFalse(reads)
        for version,pages,header,size in ((2,64,96,266336),(3,256,288,1052960)):
            raw=bytearray(size);raw[:16]=b'RNPGv'+str(version).encode()+b'\0\0'+struct.pack('<II',version,size)
            raw[24]=5;raw[24+pages-1]=6;record=bytes(raw)
            self.assertEqual(runtime.record_layout(record),(pages,header,header+pages*4096))
            self.assertEqual(runtime.record_flag(record,pages-1),6)
            if pages==64:self.assertEqual(runtime.record_flag(record,255),0)
            for at in (0,8,12,24,24+pages):
                bad=bytearray(record);bad[at]^=255
                with self.assertRaises(ValueError):runtime.record_layout(bytes(bad))
            for changed in (record[:-1],record+b'\0'):
                with self.assertRaises(ValueError):runtime.record_layout(changed)

    def test_actual_consumer_terminal_handshake(self):
        source=(ROOT/'userspace/programs/largetest.c').read_text(encoding='utf-8')
        body=source[source.index('    int64_t previous='):source.index('    static const char message[]=')]
        folder=ROOT/'build/codex-agent/r83bv-large-file/terminal-host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        c=folder/'handshake.c'
        c.write_text(r'''
#include <stdint.h>
#include <stdio.h>
#define REIST_X64_SYS_MONOTONIC_MS 1
#define REIST_X64_SYS_SLEEP_MS 2
#define REIST_TERMINAL_CHECK 5
static int mode;static unsigned sleeps,checks,clocks;static int64_t clock_ms;
static int64_t reist_x64_syscall0(unsigned op) {
 if(op!=1)return -1;
 ++clocks;if(mode==3 && clocks==3)return clock_ms-1;
 return clock_ms;
}
static int64_t reist_x64_syscall1(unsigned op,unsigned ms) {
 if(op!=2 || ms!=10 || ++sleeps>100)return -1;
 if(mode==4)return -1;clock_ms+=ms;return 0;
}
static int reist_x64_terminal_input(unsigned op,unsigned pid,unsigned generation) {
 if(op!=5 || pid || generation)return -22;
 ++checks;return mode==0 || (mode==1 && sleeps==3)?0:-13;
}
static int actual(void) {
'''+body+r'''
 return 0;
}
int main(void) {
 for(mode=0;mode<6;mode++) {
  sleeps=checks=clocks=0;clock_ms=mode==5?INT64_MAX:100;
  int result=actual();
  if(result!=(mode<2?0:28))return 1;
  if(sleeps>100 || checks>100 || clocks>101)return 2;
  if(mode==0 && (sleeps || checks!=1))return 3;
  if(mode==1 && (sleeps!=3 || checks!=4 || clock_ms!=130))return 4;
  if(mode==5 && (sleeps || checks))return 5;
 }
 puts("TERMINAL_HANDSHAKE_OK");return 0;
}
''')
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe')
            for command in (['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-Wno-misleading-indentation',c,'-o',exe],[exe]):
                r=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=60)
                (folder/(uuid.uuid4().hex+'.log')).write_bytes(r.stdout+r.stderr)
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-1800:])

    def test_actual_frame_scan_bounded_stack(self):
        folder=ROOT/'build/codex-agent/r83bv-large-file/frame-host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text(encoding='utf-8')
        body=source[source.index('process_run_frames64:'):source.index('; Trusted caller pointer is pinned')]
        prefix='''BITS 64
%define REIST_NATIVE_WIDE 1
%define REIST_NATIVE_LARGE_IMAGE 1
%define REIST_NATIVE_TASK_POOL 1
%define X86_64_NATIVE_RAM 1
%include "arch/x86_64/mm/memory_profile.inc"
TASK_STATE equ 0
TASK_FREE equ 0
TASK_CR3 equ 16
TASK_STACK_FRAME equ 24
TASK_PRIVATE_FRAMES equ 32
PAGE_SIZE equ 4096
extern scheduler_tasks,scheduler_table_frames,scheduler_original_cr3
global scan_fixture,scan_stack
section .bss
align 16
scan_stack: resb 32768
saved_rsp: resq 1
section .text
scan_fixture:
 push rbp
 push rbx
 push r12
 push r13
 push r14
 push r15
 mov [rel saved_rsp],rsp
 lea rsp,[rel scan_stack+32768]
 call process_run_frames64
 mov rsp,[rel saved_rsp]
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
'''
        asm=folder/'scan.asm';asm.write_text(prefix+body)
        c=folder/'scan.c';c.write_text(r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
uint64_t scheduler_tasks[8][512],scheduler_table_frames[8][4],scheduler_original_cr3=0x1000;
extern unsigned char scan_stack[32768];
extern int __attribute__((sysv_abi)) scan_fixture(void);
static uint64_t saved_tasks[8][512],saved_tables[8][4];
#define CHECK(x) do {if(!(x)){printf("line%d: %s\n",__LINE__,#x);return 1;}}while(0)
static uint64_t *frame(unsigned n) {
 unsigned slot=n/261,index=n%261;
 return index<256?&scheduler_tasks[slot][4+index]:index==256?&scheduler_tasks[slot][3]:&scheduler_table_frames[slot][index-257];
}
static void init(unsigned live,unsigned sparse) {
 memset(scheduler_tasks,0,sizeof(scheduler_tasks));memset(scheduler_table_frames,0,sizeof(scheduler_table_frames));
 for(unsigned n=0;n<live*261;n++)*frame(n)=sparse && n%261<256 && n%3?0:0x100000000ULL+(n+1)*4096ULL;
 for(unsigned n=0;n<live;n++){scheduler_tasks[n][0]=2;scheduler_tasks[n][2]=scheduler_table_frames[n][0];}
}
static int check(int expected) {
 memcpy(saved_tasks,scheduler_tasks,sizeof(saved_tasks));memcpy(saved_tables,scheduler_table_frames,sizeof(saved_tables));
 memset(scan_stack,0xa5,32768);CHECK(scan_fixture()==expected);
 CHECK(!memcmp(saved_tasks,scheduler_tasks,sizeof(saved_tasks)) && !memcmp(saved_tables,scheduler_table_frames,sizeof(saved_tables)));
 for(unsigned n=0;n<32768-256;n++)CHECK(scan_stack[n]==0xa5);
 return 0;
}
int main(void) {
 for(unsigned live=0;live<=8;live++)for(unsigned sparse=0;sparse<2;sparse++) {init(live,sparse);CHECK(!check(1));}
 unsigned targets[]={1,255,256,257,258,260,261,516,517,518,519,521,1827,2083,2084,2085,2086,2087};
 for(unsigned k=0;k<sizeof(targets)/sizeof(targets[0]);k++) {
  init(8,0);unsigned n=targets[k];*frame(n)=*frame(0);
  if(n%261==257)scheduler_tasks[n/261][2]=*frame(n);
  CHECK(!check(0));
 }
 for(unsigned k=0;k<5;k++) {
  init(8,0);*frame(2087)=(uint64_t[]){0,1,0x1000,0x400000000ULL,0x100000001ULL}[k];CHECK(!check(0));
 }
 init(7,0);*frame(2087)=0x2000;CHECK(!check(0));
 init(8,0);scheduler_tasks[7][2]^=4096;CHECK(!check(0));
 puts("FRAME_SCAN_BOUNDED_OK");return 0;
}
''')
        def run(command):
            result=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=90)
            (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])
        obj=folder/'scan.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',asm,'-o',obj])
        baseline=subprocess.check_output(['git','show','2cf5228a:arch/x86_64/proc/process_run.inc'],cwd=ROOT).decode()
        baseline=baseline[baseline.index('process_run_frames64:'):baseline.index('; Trusted caller pointer is pinned')]
        for omitted in ('REIST_NATIVE_LARGE_IMAGE','REIST_NATIVE_TASK_POOL'):
            binaries=[]
            for index,content in enumerate((baseline,body)):
                selected=folder/f'{omitted}-{index}.asm';linked=selected.with_suffix('.o');binary=selected.with_suffix('.bin')
                selected.write_text(prefix.replace('%define '+omitted+' 1\n','')+content)
                run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',selected,'-o',linked])
                run(['C:/msys64/mingw64/bin/objcopy.exe','-O','binary','-j','.text',linked,binary])
                binaries.append(binary.read_bytes())
            self.assertEqual(*binaries,'exact legacy frame-scan machine code')
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe');run(['gcc',opt,'-Wall','-Wextra','-Werror',c,obj,'-o',exe]);run([exe])

    def test_disabled_source_projection(self):
        import verify_x86_64_large_file as verify
        self.assertTrue(verify.projection()['passed'])

    def test_independent_large_media(self):
        import build_x86_64_large_file_media as producer
        import check_x86_64_large_file_media as consumer
        files={n:(bytes(range(251))*4200)[:1048576 if n=='largetest.prg' else 16901 if n!='data.txt' else 4096]
            for n in consumer.NAMES}
        for layout in ('ext2-2k','ext2-4k'):
            raw=producer.image(layout,files)
            self.assertEqual(consumer.verify_volume(raw,files,layout)['files'],9)
            bs=2048 if layout=='ext2-2k' else 4096
            for at in (1028,1048,1080,bs+12,3*bs+80,4*bs+2,5*bs+128+40,
                       21*bs+8,30*bs,32*bs,5*bs+19*128+88,len(raw)-1):
                with self.subTest(layout=layout,at=at):
                    bad=bytearray(raw);bad[at]^=1
                    with self.assertRaises(ValueError):consumer.verify_volume(bytes(bad),files,layout)
        with self.assertRaises(ValueError):producer.image('ext2-1k',files)
        for layout in ('fat12','fat32'):
            raw=producer.image(layout,files)
            self.assertEqual(consumer.verify_volume(raw,files,layout)['files'],9)
            reserved,fat=(1,9) if layout=='fat12' else (32,544)
            root=(reserved+2*fat)*512
            data=root+(14*512 if layout=='fat12' else 512)
            for at in (11,13,16,510,reserved*512+4,(reserved+fat)*512+4,
                       root,root+8*32+28,data,data+len(files['boot.prg']),len(raw)-1):
                with self.subTest(layout=layout,at=at):
                    bad=bytearray(raw);bad[at]^=1
                    with self.assertRaises(ValueError):consumer.verify_volume(bytes(bad),files,layout)

    def test_service_lifecycle_all_versions(self):
        folder=ROOT/'build/codex-agent/r83bv-large-file/service-host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        original=(ROOT/'test/x86_64_service_session_host.c').read_text(encoding='utf-8')
        for version in (1,2,3):
            source=original
            if version>1:
                source=source.replace('reist_service_session_init(',f'reist_service_session_init_v{version}(')
                source=source.replace('reist_service_session_open(&s,&ops,1100,0)',
                    f'reist_service_session_open_v{version}(&s,&ops,1100,120100,0)')
                source=source.replace('c->deadline=m->now+2800','c->deadline=m->control.deadline')
                source=source.replace('m->layout==1?70000:256','m->layout==1?70000:'+str(2048 if version==2 else 4096))
                needle='int r=reist_service_session_open_v'
                # Wrong entry points may not publish state or call any operation.
                at=source.index(needle)
                source=source[:at]+'''reist_service_session_v1 saved_session=s;
        CHECK(reist_service_session_open(&s,&ops,1100,0)==-22 && !m.calls &&
            !memcmp(&s,&saved_session,sizeof(s)));
        '''+source[at:]
            c=folder/f'v{version}.c';c.write_text(source)
            for opt in ('-O0','-O2'):
                exe=folder/f'v{version}{opt[1:]}.exe'
                for command in (['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror',
                    '-DREIST_NATIVE_LARGE_FILE=1','-DREIST_NATIVE_LARGE_IMAGE=1','-Iuserspace/sdk/include',c,
                    'userspace/sdk/lib/x86_64/service_session.c','-o',exe],[exe]):
                    result=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=60)
                    (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
                    self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])

    def test_actual_pool_linker_guard(self):
        from build_user_program import find_zig
        import re
        source=(ROOT/'config/x86_64_bootstrap.ld').read_text(encoding='utf-8')
        baseline=subprocess.check_output(['git','show','2cf5228a:config/x86_64_bootstrap.ld'],cwd=ROOT).decode()
        pattern=r'ASSERT\(SIZEOF\(\.memory_state\) != 7499776.*?"native eight-owner arena requires exact wide boot pair"\)'
        guard=re.search(pattern,source,re.S).group()
        self.assertEqual(re.sub(pattern,'POOL_GUARD',source,flags=re.S),
                         re.sub(pattern,'POOL_GUARD',baseline,flags=re.S))
        folder=ROOT/'build/codex-agent/r83bv-large-file/link-guard'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        asm=folder/'empty.s';asm.write_text('.text\n.globl _start\n_start: ret\n')
        obj=folder/'empty.o';zig=str(find_zig())
        env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(ROOT/'build/zig-global-cache'),ZIG_LOCAL_CACHE_DIR=str(folder/'cache'))
        def run(command):
            result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=60)
            (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            return result
        self.assertEqual(run([zig,'cc','-target','x86_64-freestanding-none','-c',asm,'-o',obj]).returncode,0)
        for catalog in (1069055,1069056,1069057):
            for scratch in (270335,270336,270337,1056767,1056768,1056769):
                with self.subTest(catalog=catalog,scratch=scratch):
                    script=folder/'guard.ld'
                    script.write_text('SECTIONS { .text : { *(.text) } '+
                        '.memory_state (NOLOAD) : { . += 7499776; } '+
                        f'.native_catalog (NOLOAD) : {{ . += {catalog}; }} '+
                        f'.native_scratch (NOLOAD) : {{ . += {scratch}; }} '+guard+' }')
                    result=run([zig,'ld.lld','-m','elf_x86_64','-T',script,obj,'-o',folder/'guard.elf'])
                    self.assertEqual(result.returncode==0,catalog==1069056 and scratch in (270336,1056768))

    def test_actual_c_profiles_and_capture(self):
        folder=ROOT/'build/codex-agent/r83bv-large-file/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        def run(command,timeout=90):
            result=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,
                timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-4000:])
            return result.stdout
        for opt in ('-O0','-O2'):
            exe=folder/(opt[1:]+'.exe')
            run(['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror','-DREIST_NATIVE_SHELL_SESSION=1','-DREIST_NATIVE_LARGE_FILE=1','-DREIST_NATIVE_LARGE_IMAGE=1','-I.','-Iuserspace/sdk/include',
                'test/x86_64_large_file_host.c','userspace/sdk/lib/x86_64/file_image.c',
                'userspace/sdk/lib/x86_64/image.c','userspace/storage/lib/native_block.c',
                'userspace/storage/lib/native_filesystem.c','userspace/storage/lib/vfs_shadow_fat32.c',
                'userspace/storage/lib/vfs_shadow_ext2.c','-o',exe])
            import build_x86_64_large_file as media
            for size in (524288,524289,754104,1048576):
                raw=bytearray(size);raw[:7]=b'\x7fELF\x02\x01\x01'
                struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
                struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096)
                raw[120]=0xc3
                elf=folder/f'file-{size}.prg';elf.write_bytes(raw)
                for layout in media.LAYOUTS:
                    with self.subTest(opt=opt,size=size,layout=layout):
                        disk=folder/f'{layout}-{size}.raw';disk.write_bytes(media.image(layout,bytes(raw)))
                        self.assertIn(b'LARGE_FILE_PASS',run([exe,disk,layout,elf],60))
                        print(opt,size,layout,'PASS',flush=True)
                if size==1048576:
                    import build_x86_64_large_file_media as signed
                    for layout in ('ext2-2k','ext2-4k','fat12','fat32'):
                        files={n:bytes(raw) if n=='largetest.prg' else b'retained fixture\n' for n in signed.NAMES}
                        disk=folder/f'multifile-{layout}.raw';disk.write_bytes(signed.image(layout,files))
                        path='/largetst.prg' if layout.startswith('fat') else '/largetest.prg'
                        self.assertIn(b'LARGE_FILE_PASS',run([exe,disk,layout,elf,path],60))

if __name__=='__main__':unittest.main()
