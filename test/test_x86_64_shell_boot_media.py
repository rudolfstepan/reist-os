"""No-build host regressions for the separately signed native shell media."""
from pathlib import Path
import json,sys,unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import check_x86_64_shell_media as check
import build_x86_64_shell_media as producer
import run_qemu_x86_64_shell_boot_media as guest


class ShellBootMediaTests(unittest.TestCase):
    def test_signature_case_reuse_rejects_unrelated_changes(self):
        import verify_x86_64_shell_boot_media as verifier
        old="return 30 if (layout,case)==('hdd','signatures') else 20\nresult['guest_seconds']<=445\noriginal_guard()\n"
        new="return 30 if layout=='hdd' and case in ('signatures','digest') else 20\nresult['guest_seconds']<=455\noriginal_guard()\n"
        verifier.negative_source_projection(new,old)
        with self.assertRaises(ValueError):verifier.negative_source_projection(new.replace('original_guard()',''),old)
        origins=[verifier.evidence_origin(s) for s in guest.CASES]
        self.assertEqual(origins,[verifier.POSITIVE_ORIGIN]*5+[verifier.NEGATIVE_ORIGIN]+[verifier.BASE]*4)

    def test_only_double_payload_hdd_negatives_have_thirty_seconds(self):
        self.assertEqual(guest.negative_budget('hdd','signatures'),30)
        self.assertEqual(guest.negative_budget('hdd','digest'),30)
        for layout,case in (('hdd','manifest'),('floppy','signatures'),('floppy','digest')):
            self.assertEqual(guest.negative_budget(layout,case),20)
        for layout,case in (('hdd','normal'),('hdd','a-signature'),('floppy','manifest'),('usb','signatures')):
            with self.assertRaises(ValueError):guest.negative_budget(layout,case)

    def test_positive_reuse_rejects_any_unrelated_runtime_drift(self):
        import inspect
        import verify_x86_64_shell_boot_media as verifier
        original="def run_matrix(image,package,folder,binding):\n    for name,layout,case,session,ram in CASES:\n        raw=check.bounded(folder/'guest.log',262144)\n        old_assertion()\n"
        candidate=inspect.getsource(guest.live_serial)+'\n\n'+original.replace('binding):','binding,cases=CASES):').replace('in CASES:','in cases:').replace("raw=check.bounded(folder/'guest.log',262144)","raw=live_serial(folder/'guest.log')")
        verifier.positive_source_projection(candidate,original)
        with self.assertRaises(ValueError):verifier.positive_source_projection(candidate.replace('old_assertion()','weakened_assertion()'),original)
        with self.assertRaises(ValueError):verifier.positive_source_projection(candidate+'extra_change()\n',original)

    def test_live_serial_allows_empty_startup_but_final_reader_stays_strict(self):
        import tempfile
        folder=Path(tempfile.mkdtemp(prefix='az-empty-serial-',dir=ROOT/'build/codex-agent'))
        path=folder/'guest.log';path.write_bytes(b'')
        self.assertEqual(guest.live_serial(path),b'')
        with self.assertRaises(ValueError):check.bounded(path,262144)
        path.write_bytes(b'boot bytes');self.assertEqual(guest.live_serial(path),b'boot bytes')
        path.write_bytes(b'x'*262145)
        with self.assertRaises(ValueError):guest.live_serial(path)

    def test_profile_is_separate_and_sizes_preserve_physical_extents(self):
        self.assertEqual(check.PROFILE,'research-native-shell-two-media-v1')
        self.assertEqual(check.KERNEL_LIMIT,3008*512)
        self.assertGreater(check.KERNEL_LIMIT,1382432)
        self.assertEqual(check.FILES['system.ext2'],128*1024)
        self.assertEqual(check.FILES['reist-x86_64.img'],512*1024*1024)
        self.assertEqual(check.FILES['reist-x86_64-floppy.img'],1474560)

    def test_json_rejects_duplicate_keys_and_nonobjects(self):
        for raw in (b'[]',b'null',b'1',b'{"a":1,"a":2}',b' '*16385):
            with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):check.object_json(raw)
        self.assertEqual(check.object_json(b'{"a":1}'),{'a':1})

    def test_profile_header_and_exact_artifact_identity(self):
        value=dict(version=1,architecture='x86_64',profile=check.PROFILE,
            attempt='shell-media-'+'a'*32,artifacts={name:{} for name in check.FILES},
            devices=check.DEVICES)
        check.admit_package(value)
        for field,bad in (('version',True),('version',2),('architecture','i386'),
                          ('profile','research-native-heap'),('attempt','../escape'),
                          ('devices',dict(check.DEVICES,driver='primary-slave')),
                          ('artifacts',{})):
            with self.subTest(field=field),self.assertRaises(ValueError):
                check.admit_package(dict(value,**{field:bad}))
        with self.assertRaises(ValueError):check.admit_package(dict(value,extra=0))

    def test_boot_device_never_replaces_primary_runtime_data(self):
        path=ROOT/'build/codex-agent/az-unit/disposable.qcow2'
        args=guest.boot_arguments(path,'hdd')
        self.assertNotIn('-kernel',args)
        self.assertIn('ide-hd,drive=az-boot,bus=ide.0,unit=1,bootindex=1',args)
        self.assertNotIn('unit=0',','.join(args))
        floppy=guest.boot_arguments(path,'floppy')
        self.assertIn('-boot',floppy);self.assertEqual(floppy[-1],'a')
        for layout in ('usb','primary','',None):
            with self.subTest(layout=layout),self.assertRaises(ValueError):guest.boot_arguments(path,layout)
        with self.assertRaises(ValueError):guest.boot_arguments(ROOT/'user.qcow2','hdd')

    def test_bios_order_and_failure_counts_are_additional(self):
        serial='\n'.join(('x86 native BIOS loader','Verifying kernel SHA-256/RSA-PSS...',
            'Loading ELF32 kernel...','Starting kernel...','REIST_X86_64_LONG_MODE_BOOT_OK'))
        guest.validate_bios(serial,'hdd','normal')
        for bad in (serial.replace('Verifying kernel SHA-256/RSA-PSS...',''),
                    serial+'\nStarting kernel...',serial+'\nDisk read failed',
                    serial.replace('Loading ELF32 kernel...','Starting kernel...')):
            with self.assertRaises(ValueError):guest.validate_bios(bad,'hdd','normal')
        rejected='x86 native BIOS loader\nKernel RSA-PSS verification failed\n'
        guest.validate_bios(rejected,'floppy','signatures')
        for bad in (rejected+'Starting kernel...',rejected+'REIST_X86_64_X',
                    rejected.replace('RSA-PSS','SHA-256')):
            with self.assertRaises(ValueError):guest.validate_bios(bad,'floppy','signatures')

    def test_guest_matrix_remains_bounded_and_reuses_original_cases(self):
        self.assertEqual(len(guest.CASES),10)
        self.assertEqual(sum(45+guest.bios_budget(row[2]) if row[3] is not None else guest.negative_budget(row[1],row[2]) for row in guest.CASES),455)
        self.assertEqual([(row[3],row[4]) for row in guest.CASES if row[3] is not None],
                         [(7,4096),(6,4096),(2,4096),(5,8192),(13,4096)])

    def test_only_a_signature_fallback_gets_thirty_seconds(self):
        self.assertEqual(guest.bios_budget('normal'),20)
        self.assertEqual(guest.bios_budget('a-signature'),30)
        for case in ('signatures','digest','manifest','',None,True):
            with self.assertRaises(ValueError):guest.bios_budget(case)
        record=dict(version=3,entry=0x101000,hits=1,registers=dict(rip=0x101000,rax=0x2badb002,
            rbx=0x5000,cr0=17,rsp=0x90000,eflags=6),elapsed=24.0,guest_started=100.0,
            runtime_started=125.0,stop_sha256='0'*64)
        guest.entry_phase(record,100.0,125.1,case='a-signature')
        with self.assertRaises(ValueError):guest.entry_phase(record,100.0,125.1)
        with self.assertRaises(ValueError):guest.entry_phase(record,100.0,130.0,case='a-signature')

    def test_make_and_windows_packaging_do_not_rebuild_kernel(self):
        make=(ROOT/'Makefile').read_text()
        section=make.split('# AZ packaging only:',1)[1].split('# End AZ packaging-only target.',1)[0]
        self.assertIn('x86_64-shell-media:\n',section)
        self.assertNotIn('x86_64-bootstrap:',section)
        self.assertNotIn('build-x86_64-bootstrap.ps1',section)
        windows=(ROOT/'scripts/build-x86_64-shell-media.ps1').read_text()
        for source in (section,windows):
            self.assertIn('scripts/build_x86_64_shell_media.py --input-directory',source)
            self.assertIn('--output-directory',source)
        self.assertIn('finally',windows)

    def test_actual_capture_factory_replaces_only_qemu_kernel_transport(self):
        import tempfile,time
        root=ROOT/'build/codex-agent';root.mkdir(parents=True,exist_ok=True)
        folder=Path(tempfile.mkdtemp(prefix='az-capture-host-',dir=root))
        image=root/'unused-test.elf'
        medium=type('Medium',(),dict(overlay=folder/'disposable.qcow2',layout='hdd'))()
        namespace=guest.capture_namespace(time.monotonic(),medium,image,folder)
        calls=[]
        class NotStarted(Exception):pass
        def blocked(command,**kwargs):calls.append(command);raise NotStarted()
        with mock.patch.object(guest.subprocess,'Popen',side_effect=blocked):
            with self.assertRaises(NotStarted):
                namespace['_capture_run'](image,folder,'python\npass\nend\ncontinue\n',4096,
                    ['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0'],
                    service_pio_budget=True,console_input=guest.ay.input_plan(2))
        self.assertEqual(len(calls),1)
        self.assertNotIn('-kernel',calls[0]);self.assertIn('-S',calls[0])
        self.assertIn('ide-hd,drive=pio-layer,bus=ide.0,unit=0',calls[0])
        self.assertIn('ide-hd,drive=az-boot,bus=ide.0,unit=1,bootindex=1',calls[0])
        self.assertEqual(json.loads((folder/'command.json').read_text()),calls[0])

    def test_failed_verification_or_publication_preserves_old_index(self):
        import tempfile
        root=ROOT/'build/codex-agent';root.mkdir(parents=True,exist_ok=True)
        folder=Path(tempfile.mkdtemp(prefix='az-publication-host-',dir=root))
        old=folder/'shell-media.json';candidate=folder/'shell-index-test.json'
        old.write_bytes(b'previous accepted index');candidate.write_bytes(b'candidate')
        with mock.patch.object(producer.old,'run',side_effect=ValueError('verification rejected')):
            with mock.patch.object(producer.os,'replace') as replace:
                with self.assertRaises(ValueError):producer.publish(folder,candidate,'openssl',folder/'log')
                replace.assert_not_called()
        with mock.patch.object(producer.old,'run'):
            with mock.patch.object(producer.os,'replace',side_effect=OSError('publication interrupted')):
                with self.assertRaises(OSError):producer.publish(folder,candidate,'openssl',folder/'log')
        self.assertEqual(old.read_bytes(),b'previous accepted index');self.assertEqual(candidate.read_bytes(),b'candidate')

    def test_make_projection_is_explicit_utf8_not_windows_ansi(self):
        import verify_x86_64_shell_boot_media as verifier
        source=(ROOT/'Makefile').read_bytes().decode('utf-8').replace('\r\n','\n')
        before,rest=source.split('# AZ packaging only:',1)
        after=rest.split('# End AZ packaging-only target.\n\n',1)[1]
        expected=before+after
        self.assertIn('\u2713',expected)
        self.assertEqual(verifier.make_projection(),expected)

    def test_cold_bios_entry_stop_is_real_bounded_and_always_removed(self):
        import tempfile,types,queue,threading
        root=ROOT/'build/codex-agent';root.mkdir(parents=True,exist_ok=True)
        for wrong in (None,'hit','pc','mode','magic'):
            with self.subTest(wrong=wrong):
                folder=Path(tempfile.mkdtemp(prefix='az-entry-host-',dir=root));live=[];calls=[];deleted=[]
                class Breakpoint:
                    def __init__(self,spec,type,internal):
                        self.enabled=True;self.hit_count=0;self.valid=True
                        self.locations=[types.SimpleNamespace(address=0x100000,enabled=True)]
                        self.number=1;live.append(self)
                    def is_valid(self):return self.valid
                    def delete(self):self.valid=False;live.remove(self);deleted.append(self)
                class Failed(Exception):pass
                def execute(command,**kwargs):
                    calls.append(command)
                    if command=='continue':live[0].hit_count=0 if wrong=='hit' else 1;return 'actual stop'
                    if command=='quit 71':raise Failed()
                    raise AssertionError(command)
                registers={'$rip':0x100001 if wrong=='pc' else 0x100000,'$rax':0 if wrong=='magic' else 0x2badb002,
                    '$rbx':0x5000,'$cr0':0x80000001 if wrong=='mode' else 1,'$rsp':0x90000,'$eflags':2}
                gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_HARDWARE_BREAKPOINT=2,
                    breakpoints=lambda:tuple(live),execute=execute,parse_and_eval=registers.__getitem__,write=lambda text:None)
                origin=guest.time.monotonic()
                code=guest.boot_entry_prefix(0x100000,folder,origin)
                self.assertTrue(code.startswith('python\n') and code.endswith('end\n'))
                def acknowledge(delay):
                    process=types.SimpleNamespace(poll=lambda:None)
                    guest.await_entry(origin,folder,queue.Queue(),bytearray(),threading.Event(),process,process)
                # Deliberately unrelated GDB epoch: never compare its absolute
                # clock to the parent QPC clock. Only a held-stop handshake works.
                gdb_clock=types.SimpleNamespace(monotonic=lambda:guest.time.monotonic()-1000,sleep=acknowledge)
                with mock.patch.dict(sys.modules,{'gdb':gdb,'time':gdb_clock}):
                    if wrong:
                        with self.assertRaises(Failed):exec(code[7:-4],{})
                    else:exec(code[7:-4],{})
                self.assertFalse(live);self.assertEqual(len(deleted),1)
                self.assertEqual(calls,['continue','quit 71'] if wrong else ['continue'])
                self.assertEqual((folder/'bios-entry.json').exists(),wrong is None)

    def test_entry_phase_is_real_finite_and_not_a_feeder_clock_reset(self):
        import tempfile,queue,threading,types
        folder=Path(tempfile.mkdtemp(prefix='az-phase-host-',dir=ROOT/'build/codex-agent'))
        record=dict(version=3,entry=0x101000,hits=1,registers=dict(rip=0x101000,rax=0x2badb002,
            rbx=0x5000,cr0=17,rsp=0x90000,eflags=6),elapsed=8.0,guest_started=100.0,
            runtime_started=109.0,stop_sha256='0'*64)
        process=types.SimpleNamespace(poll=lambda:None)
        def await_record(value,now=109.1):
            return guest.entry_phase(value,100.0,now)
        self.assertEqual(await_record(record),record)
        for key,value in (('guest_started',99.0),('runtime_started',110.0),('runtime_started',120.0),
                          ('elapsed',20.0),('hits',2),('version',1),
                          ('runtime_started',float('nan')),('runtime_started',True)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):await_record(dict(record,**{key:value}))
        with self.assertRaises(ValueError):await_record(record,120.0)
        source=guest.composed_capture_source()
        self.assertEqual(source.count('az_await_entry('),1)
        self.assertLess(source.index('az_await_entry('),source.index("exec(compile(source,"))

    def test_missing_entry_times_out_and_serial_overflow_is_not_ignored(self):
        import tempfile,queue,threading,types
        folder=Path(tempfile.mkdtemp(prefix='az-phase-missing-',dir=ROOT/'build/codex-agent'))
        process=types.SimpleNamespace(poll=lambda:None);overflow=threading.Event()
        with mock.patch.object(guest.time,'monotonic',return_value=120.0):
            with self.assertRaises(ValueError):guest.await_entry(100.0,folder,queue.Queue(),bytearray(),overflow,process,process)
        overflow.set()
        with mock.patch.object(guest.time,'monotonic',return_value=101.0):
            with self.assertRaises(ValueError):guest.await_entry(100.0,folder,queue.Queue(),bytearray(),overflow,process,process)

    def test_generated_capture_starts_runtime_once_before_first_feeder_call(self):
        import tempfile,types,io,queue
        folder=Path(tempfile.mkdtemp(prefix='az-composed-capture-',dir=ROOT/'build/codex-agent'))
        image=folder/'unused.elf';medium=types.SimpleNamespace(overlay=folder/'disposable.qcow2',layout='hdd')
        (folder/'frame-trace.log').write_text('',encoding='ascii')
        namespace=guest.capture_namespace(100.0,medium,image,folder)
        events=[];fifo=queue.Queue();fifo.put((guest.ay.BANNER+'\n'+namespace['process'].SUCCESS).encode('ascii'))
        class Feeder:
            def __init__(self,plan):self.sent=[];self.chunks=[];events.append('create')
            def pump(self,serial,trace,write,elapsed):
                events.append(('pump',elapsed));self.sent=[1,2]
        class Process:
            def __init__(self,*args,**kwargs):
                self.stdin=io.BytesIO();self.stdout=io.BytesIO();self.pid=123;self.returncode=None
            def poll(self):return self.returncode
            def wait(self,timeout):self.returncode=0;return 0
        def boundary(*args):events.append('actual-entry');return {'runtime_started':109.0}
        namespace.update(ConsoleFeeder=Feeder,az_await_entry=boundary,
            queue=types.SimpleNamespace(Queue=lambda **kw:fifo,Empty=queue.Empty,Full=queue.Full),
            threading=types.SimpleNamespace(Event=guest.ay.boot.threading.Event,
                Thread=lambda **kw:types.SimpleNamespace(start=lambda:None,join=lambda **kw:None)),
            terminate_bounded=lambda proc:setattr(proc,'returncode',0),process_cpu_ns=lambda pid:{})
        metrics={}
        with mock.patch.object(guest.subprocess,'Popen',side_effect=Process),mock.patch.object(guest.time,'monotonic',return_value=109.25):
            namespace['_capture_run'](image,folder,'python\npass\nend\ncontinue\n',4096,
                ['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0'],metrics=metrics,
                service_pio_budget=True,console_input=guest.ay.input_plan(2))
        self.assertEqual(events,['create','actual-entry',('pump',.25)])
        self.assertEqual(metrics['observe_seconds'],.25)
        self.assertEqual(metrics['bios_phase'],{'runtime_started':109.0})

    def test_physical_entry_is_bound_to_elf_and_high_half_observer(self):
        parsed={'entry':0x101000,'symbols':{'x86_64_bootstrap_start':{'value':0x101000}}}
        config={'s':{'x86_64_bootstrap_start':0xffffffff80101000}}
        with mock.patch.object(check,'bounded',return_value=b'validated transport'):
            with mock.patch.object(check.payload,'elf',return_value=parsed) as parser:
                self.assertEqual(guest.physical_entry(ROOT/'build/test.elf',config),0x101000)
                parser.assert_called_with(b'validated transport',32)
                with self.assertRaises(ValueError):guest.physical_entry(ROOT/'build/test.elf',{'s':{'x86_64_bootstrap_start':0x101000}})
                parsed['symbols']['x86_64_bootstrap_start']['value']+=1
                with self.assertRaises(ValueError):guest.physical_entry(ROOT/'build/test.elf',config)


if __name__=='__main__':unittest.main()
