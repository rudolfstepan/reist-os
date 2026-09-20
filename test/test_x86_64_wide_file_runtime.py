"""Complete generated observer/transport and retained safety predicates."""
from pathlib import Path
import ast,inspect,struct,sys,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_qemu_x86_64_wide_file as wide

class WideRuntimeTests(unittest.TestCase):
    def test_full_deadline_is_explicit_and_leaves_normal_collector_exact(self):
        normal=wide.selected_source()
        full=wide.full_source(normal)
        a={n.name:ast.dump(n) for n in ast.parse(normal).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        b={n.name:ast.dump(n) for n in ast.parse(full).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertEqual({n for n in a if a[n]!=b[n]},{'SessionFeeder','capture_namespace'})
        self.assertIn('elapsed<897',full)
        self.assertIn('elapsed<297',normal)
        self.assertIn('started+897',full)
        for value in (None,0,1,'full'):
            with self.assertRaises(ValueError):wide.namespace(full=value)
        for selected,helper in ((False,'configure_binary'),(True,'configure_binary_full')):
            module=wide.namespace(full=selected)
            ns=module.stepped_capture_namespace()
            self.assertIn(helper,ns['_capture_run'].__code__.co_names)
            feeder=module.SessionFeeder(module.input_plan(3));end=897 if selected else 297
            feeder.pump('','',lambda raw:len(raw),end-0.001)
            with self.assertRaisesRegex(ValueError,'deadline'):feeder.pump('','',lambda raw:len(raw),end)
        import qemu_binary_memory as binary
        body='reader-created\nmem=binary_reader.read\nwrap-stop-unchanged\n'
        with patch.object(binary,'configure',return_value=(['same-qmp'],body)):
            args,code=wide.configure_binary_full('observer',ROOT/'build',4096,'equivalence',service_pio_budget=True)
        self.assertEqual(args,['same-qmp'])
        self.assertEqual(code,body.replace('\nmem=', '\nbinary_reader.deadline+=855\nmem='))

    def test_exact_six_case_reuse_and_no_build_command(self):
        import verify_x86_64_wide_file as verify
        verify.normal_collector_projection()
        original=Path.read_text
        def mutation(path,*args,**kwargs):
            text=original(path,*args,**kwargs)
            return text.replace('elapsed<297','elapsed<298') if path==ROOT/'scripts/run_qemu_x86_64_wide_file.py' else text
        with patch.object(Path,'read_text',mutation),self.assertRaises(ValueError):verify.normal_collector_projection()
        rows=[dict(zip(('label','case','layout','ram','full'),case),passed=True,elapsed=1)
              for case in wide.CASES[:6]]
        self.assertEqual(wide.reuse_prefix(rows),6)
        for changed in (rows[:5],rows+rows[:1],list(reversed(rows)),
                        [dict(rows[0],passed=False)]+rows[1:],
                        [dict(rows[0],elapsed=301)]+rows[1:]):
            with self.assertRaises(ValueError):wide.reuse_prefix(changed)
        self.assertEqual(wide.reuse_prefix(None),0)
        with patch.object(verify,'binding',return_value={'candidate':'host','sources':{}}),\
             patch.object(verify,'built_images',return_value=['wide','legacy']),\
             patch.object(verify,'save') as save,patch.object(verify,'command') as command:
            verify.build()
        command.assert_not_called()
        self.assertEqual(save.call_args.args[1]['new_builds'],0)

    def test_lossless_evidence_codec_and_mutations(self):
        import base64
        row='SHELL_SESSION '+__import__('json').dumps(dict(kind='return',before='00'*8192))+'\n'
        encoded=wide.encode_evidence(row)
        self.assertLess(len(encoded),len(row)//4)
        self.assertEqual(wide.decode_evidence(encoded),row)
        plain='SHELL_SESSION {"kind": "start", "slot": 0}\nCONSOLE_IO {}\n'
        self.assertEqual(wide.decode_evidence(plain+encoded),plain+row)
        for bad in (encoded[:-1],encoded.replace('WIDE_D1','WIDE_D2'),
                    encoded.replace(encoded.split()[2],'0'*64),
                    encoded.replace(encoded.split()[1],'65537'),
                    encoded.replace(encoded.split()[3],base64.b64encode(base64.b64decode(encoded.split()[3])+b'x').decode()),
                    encoded.replace(encoded.split()[3],base64.b64encode(b'\xff\x01\x00\x01').decode()),
                    encoded.replace(encoded.split()[3],base64.b64encode(b'\xff\x04').decode()),
                    encoded.replace(encoded.split()[3],base64.b64encode(b'\xfe').decode())):
            with self.subTest(bad=bad[:100]),self.assertRaises(ValueError):wide.decode_evidence(bad)
        with self.assertRaises(ValueError):wide.encode_evidence('x'*65537)
        with patch.object(wide,'DECODE_LIMIT',len(row)-1):
            with self.assertRaises(ValueError):wide.decode_evidence(encoded)

    def test_cpu_diagnostic_projection_and_record_bounds(self):
        module=wide.namespace();original=wide.old.native_cpu_trace
        raw=struct.pack('<4I3Q19Q',1,1,2049,0,1,100,1,*([0]*18+[8]))
        self.assertEqual(module.native_cpu_trace.decode_trace_record(raw,2049)['gen'],1)
        with self.assertRaises(ValueError):original.decode_trace_record(raw,2049)
        with self.assertRaises(ValueError):module.native_cpu_trace.decode_trace_record(raw,262145)
        damaged=bytearray(raw);struct.pack_into('<Q',damaged,168,512)
        with self.assertRaises(ValueError):module.native_cpu_trace.decode_trace_record(bytes(damaged),2049)
        self.assertEqual(wide.cpu_default_projection(),True)

    def test_emitted_codec_is_executed_and_keeps_feeder_events_plain(self):
        import json,types
        emitted=[];scope={'gdb':types.SimpleNamespace(write=emitted.append),'json':json}
        original="def emit(kind,**values):gdb.write('SHELL_SESSION '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\\n')"
        exec(wide.lossless_observer(original),scope)
        scope['emit']('start',slot=0,gen=1);scope['emit']('return',before='00'*2048)
        self.assertTrue(emitted[0].startswith('SHELL_SESSION '))
        self.assertTrue(emitted[1].startswith('WIDE_D1 '))
        expected=''.join('SHELL_SESSION '+json.dumps(r,sort_keys=True)+'\n' for r in (
            dict(kind='start',slot=0,gen=1),dict(kind='return',before='00'*2048)))
        self.assertEqual(wide.decode_evidence(''.join(emitted)),expected)
        original_cpu=Path(wide.old.native_cpu_trace.__file__).read_text()
        projected=inspect.getsource(wide.namespace().native_cpu_trace.decode_trace_record)
        self.assertEqual(projected.replace('1<=sequence<=262144','1<=sequence<=2048'),
                         inspect.getsource(wide.old.native_cpu_trace.decode_trace_record))
        self.assertEqual(Path(wide.old.native_cpu_trace.__file__).read_text(),original_cpu)

    def test_cpu_exact_default_projection_rejects_quota_or_ring_changes(self):
        original=Path.read_text
        for before,after in [('cmp r10,262144','cmp r10,262145'),('resb 256*192','resb 512*192'),
                             ('jne .error','je .error')]:
            def changed(path,*a,**k):
                value=original(path,*a,**k)
                return value.replace(before,after) if path==ROOT/'arch/x86_64/proc/cpu_trace.inc' else value
            with patch.object(Path,'read_text',changed),self.assertRaises(ValueError):wide.cpu_default_projection()

    def test_codec_runs_inside_actual_gdb_without_optional_python_extensions(self):
        import subprocess,os
        program=('EVIDENCE_TOKENS='+repr(wide.EVIDENCE_TOKENS)+'\n'+inspect.getsource(wide.encode_evidence)+
            "\nprint(encode_evidence('SHELL_SESSION '+chr(123)+chr(34)+'before'+chr(34)+': '+chr(34)+'0'*8192+chr(34)+chr(125)+'\\n'),end='')")
        result=subprocess.run([wide.old.boot.shutil.which('gdb'),'-q','-nx','-batch','-ex','python exec('+repr(program)+')'],
            capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        trace=wide.old.capture_text(result.stdout)
        self.assertEqual(wide.decode_evidence(trace),'SHELL_SESSION {"before": "'+'0'*8192+'"}\n')

    def test_live_trace_reads_frozen_byte_extent_not_growing_character_limit(self):
        import io,types
        from unittest.mock import Mock
        class Stream(io.BytesIO):
            def fileno(self):return 17
        stream=Stream(b'a\r\nb\r\nGROWING_TAIL');stream.read=Mock(wraps=stream.read)
        path=Mock();path.open.return_value=stream
        with patch.object(wide.os,'fstat',return_value=types.SimpleNamespace(st_size=6)):
            self.assertEqual(wide.live_trace(path),'a\nb\n')
        stream.read.assert_called_once_with(6);path.open.assert_called_once_with('rb',buffering=0)
        stream=Stream(b'');path.open.return_value=stream
        with patch.object(wide.os,'fstat',return_value=types.SimpleNamespace(st_size=128*1024*1024+1)):
            with self.assertRaisesRegex(ValueError,'capacity'):wide.live_trace(path)

    def test_serial_byte_bound_is_independent_of_pipe_fragmentation(self):
        import io,queue,threading
        class ByteStream(io.BytesIO):
            def read(self,size):return super().read(1)
        for size in (128,129,262144,262145):
            stream=ByteStream(b'x'*size);out=queue.Queue(maxsize=262144);overflow=threading.Event()
            wide.serial_reader(stream,out,overflow)
            self.assertEqual(overflow.is_set(),size>262144)
            result=b''.join(out.get_nowait() for _ in range(out.qsize()))
            self.assertEqual(result,b'x'*min(size,262144))
        source=inspect.getsource(wide.old.boot._capture_run)
        source=source.replace('source.read(1024*1024+1)','source.read(128*1024*1024+1)')
        changed=wide.wide_serial_capture(source)
        self.assertIn('len(data)>262144',changed)
        self.assertIn('serial_reader(vm.stdout,output,overflow)',changed)

    def test_binary_deadline_adapter_preserves_shared_reader(self):
        import qemu_binary_memory as binary
        initial=inspect.getsource(binary.Reader)
        body='reader-created\nmem=binary_reader.read\nwrap-stop-unchanged\n'
        with patch.object(binary,'configure',return_value=(['same-qmp'],body)) as configure:
            args,code=wide.configure_binary('observer',ROOT/'build',4096,'equivalence',service_pio_budget=True)
            self.assertEqual(args,['same-qmp'])
            self.assertEqual(code,body.replace('\nmem=', '\nbinary_reader.deadline+=255\nmem='))
            configure.assert_called_once_with('observer',ROOT/'build',4096,'equivalence',service_pio_budget=True)
            with self.assertRaises(ValueError):wide.configure_binary('',ROOT/'build',4096,'equivalence')
        self.assertEqual(inspect.getsource(binary.Reader),initial)
        ns=wide.namespace().capture_namespace()
        self.assertIn('configure_binary',ns['_capture_run'].__code__.co_names)

    def test_canonical_fixture_passes_actual_capture_type_admission(self):
        def init(fixture,folder,**kwargs):
            fixture.filesystem=kwargs['filesystem'];fixture.file_program=kwargs['file_program']
            fixture.block=fixture.malformed=False
        with patch.object(wide.old.file.pio.Fixture,'__init__',init):
            fixture=wide.bounded_fixture(ROOT/'build',0,bytes(4096),wide.time.monotonic())
        self.assertIs(type(fixture),wide.old.file.pio.Fixture)
        self.assertEqual(fixture.expected(),wide.media.image('fat12',bytes(4096)))
        phases=[];fixture.arguments=lambda _:[];fixture.verify=phases.append
        ns=wide.namespace().capture_namespace()
        ns['_capture']=lambda *a,**k:'captured'
        self.assertEqual(ns['capture'](None,ROOT/'build','',4096,fixture,
            console_input=wide.old.input_plan(0),service_pio_budget=True),'captured')
        self.assertEqual(phases,['before','after'])
        with self.assertRaisesRegex(ValueError,'unsupported guest media'):
            ns['capture'](None,ROOT/'build','',4096,object(),
                console_input=wide.old.input_plan(0),service_pio_budget=True)

    def test_historical_projection_retains_exact_wide_selector_guards(self):
        import verify_x86_64_shell_session as session
        import verify_x86_64_terminal as terminal
        original=Path.read_text
        for check in (session.default_projection,terminal.default_sources):
            self.assertTrue(check())
            mutations=[('scripts/build-x86_64-bootstrap.ps1',s) for s in (
                '    [switch]$NativeWideFile,\n',
                'if ($NativeWideFile) { $NativeShellSession = [switch]$true }\n',
                '        "X86_64_NATIVE_WIDE_FILE=$([int]$NativeWideFile.IsPresent)" `\n')]
            if check==session.default_projection:
                mutations += [('Makefile',s) for s in (
                    'X86_64_NATIVE_WIDE_FILE ?= 0\n',
                    'X86_64_SHELL_MEDIA_INPUT ?= build/x86_64\n',
                    '$(error NativeWideFile requires explicit NativeShellSession)\n',
                    'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_WIDE_FILE)),--wide-file,)\n')]
            for name,token in mutations:
                for replacement in ('',token+token,token.replace('1','0')+'# drift\n'):
                    def altered(path,*a,**k):
                        text=original(path,*a,**k)
                        return text.replace(token,replacement) if path==ROOT/name else text
                    with self.subTest(check=check.__name__,name=name,token=token,replacement=replacement):
                        with patch.object(Path,'read_text',altered),self.assertRaises(ValueError):check()

    def test_transaction_stops_at_first_failed_gate(self):
        import verify_x86_64_wide_file as verify
        folder=ROOT/'build/codex-agent/r83ba-wide-file/development'/uuid.uuid4().hex
        frozen=dict(candidate='test',commands=['python first','python second'],limits=[1,1])
        with patch.object(verify,'BASE',folder),patch.object(verify,'binding',return_value=frozen),\
             patch.object(verify,'command',return_value=dict(passed=False,elapsed=0)) as command:
            with self.assertRaisesRegex(ValueError,'first failed gate'):verify.all_gates()
            self.assertEqual(command.call_count,1)
            self.assertTrue((folder/'stopped.json').is_file())
            self.assertFalse((folder/'gates-passed.json').exists())
            with self.assertRaisesRegex(ValueError,'single frozen execution'):verify.all_gates()
            self.assertEqual(command.call_count,1)

    def test_build_selection_is_opt_in_on_both_paths(self):
        make=(ROOT/'Makefile').read_text()
        ps=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text()
        producer=(ROOT/'scripts/build_x86_64_boot_programs.py').read_text()
        self.assertIn('X86_64_NATIVE_WIDE_FILE ?= 0',make)
        self.assertIn('NativeWideFile requires explicit NativeShellSession',make)
        self.assertIn('--wide-file',make)
        self.assertIn('[switch]$NativeWideFile',ps)
        self.assertIn('X86_64_NATIVE_WIDE_FILE=$([int]$NativeWideFile.IsPresent)',ps)
        self.assertIn('wide_file=False',producer)
        self.assertIn("'root/bin'",producer)
        self.assertIn("'shell.prg'",producer)

    def test_selected_namespace_does_not_mutate_legacy(self):
        original=wide.old.file.block.TRACE_CORE;media=wide.old.file.media;physical=wide.old.file.fs.EXTRA
        module=wide.namespace()
        self.assertEqual(wide.old.file.block.TRACE_CORE,original)
        self.assertIs(wide.old.file.media,media)
        self.assertEqual(module.ROOT,ROOT)
        for name in ('validate_image_start','validate_io_and_faults',
                     'validate_identity','validate_terminal','validate_ipc_delivery'):
            self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(module,name)))),
                             ast.dump(ast.parse(inspect.getsource(getattr(wide.old,name)))))
        self.assertIsNot(module.native_cpu_trace,wide.old.native_cpu_trace)
        self.assertIn('1<=sequence<=2048',inspect.getsource(wide.old.native_cpu_trace.decode_trace_record))
        self.assertEqual(inspect.getsource(module.validate_cpu).replace('sum(charges.values())<=262144',
            'sum(charges.values())<=2048'),inspect.getsource(wide.old.validate_cpu))
        self.assertIn('<=262144',module.file.block.TRACE_CORE)
        self.assertEqual(wide.old.file.fs.EXTRA,physical)
        expected=physical.replace('physical_events<=1024','physical_events<=262144').replace(
            "len(item['lbas'])<17","len(item['lbas'])<4096").replace('17*512-32','4096*512-32')
        self.assertEqual(module.file.fs.EXTRA,expected)
        self.assertEqual(len(wide.CASES),12)

    def test_full_generated_observer_and_transport(self):
        module=wide.namespace()
        folder=ROOT/'build/codex-agent/r83ba-wide-file/development'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        code=module.observer({'s':{},'cs':{}},{n:bytes(266336) for n in (2,3,4)},folder,2,2)
        body=code.split('\npython\n',1)[1].rsplit('\nend\n',1)[0]
        compile(body,'<wide-observer-host>','exec')
        self.assertIn('snapshots<=262144',body)
        self.assertIn('self.batches>=262144',body)
        self.assertIn("self.namespace['callbacks']<=262144",body)
        self.assertIn('self.running or self.failed or not self.pending or self.batches>=262144',body)
        self.assertIn('OBSERVER_FAIL reentrant service dispatch',body)
        self.assertIn('total<=262144',body)
        self.assertIn('self.sequence<=total<=262144 or total-self.sequence>256',body)
        self.assertIn('encode_evidence(line)',body)
        self.assertIn('target_hook.hit_count==1',body)
        self.assertIn('target_hook.delete()',body)
        namespace=module.stepped_capture_namespace()
        self.assertTrue(callable(namespace['capture']))

    def test_wide_response_oracle_and_old_rejection(self):
        module=wide.namespace();request=bytearray(512)
        struct.pack_into('<5I',request,0,1,512,6,0,9)
        struct.pack_into('<2I',request,24,524032,256)
        request[36:45]=b'/boot.prg'
        raw=bytes(request);app=bytes(524032)+bytes(range(256))
        status,response=module.fs_expected_response(raw,3,app)
        self.assertEqual(status,0);self.assertEqual(response[228:484],bytes(range(256)))
        self.assertEqual(struct.unpack_from('<I',response,32)[0],256)
        with self.assertRaises(ValueError):wide.old.fs_expected_response(raw,3,app)
        forged=bytearray(raw);forged[-1]=1
        with self.assertRaises(ValueError):module.fs_expected_response(bytes(forged),3,app)

    def test_media_admission_and_legacy_identity(self):
        old=wide.old.file.media.image('ext2-2k',program=bytes(728))
        for layout in wide.media.LAYOUTS:
            raw=wide.media.image(layout,bytes(524288))
            self.assertEqual(len(raw),(2880 if layout=='fat12' else 70000 if layout=='fat32' else 2048)*512)
        for value in (None,bytearray(64),bytes(63),bytes(524289)):
            with self.assertRaises(ValueError):wide.media.image('ext2-2k',value)
        self.assertEqual(wide.old.file.media.image('ext2-2k',program=bytes(728)),old)

if __name__=='__main__':unittest.main()
