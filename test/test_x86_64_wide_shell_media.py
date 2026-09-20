"""No-kernel-build regression for the independently named wide BIOS package."""
from pathlib import Path
import inspect,json,struct,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import check_x86_64_wide_shell_media as check
import build_x86_64_wide_shell_media as producer
import build_x86_64_wide_file_media as media

class WideShellMediaTests(unittest.TestCase):
    def test_resigned_corruption_reaches_filesystem_not_json_or_crypto(self):
        import verify_x86_64_wide_shell_media as verify
        value={'version':1,'nested':{'bytes':1048576}}
        raw=verify.canonical_descriptor(value)
        self.assertEqual(raw,b'{"nested":{"bytes":1048576},"version":1}\n')
        path=self.folder()/'package.json';path.write_bytes(raw)
        self.assertEqual(path.read_bytes(),raw)
        verify.require_ext2_failure(ValueError('wide EXT2 field/data at 6528'))
        for reason in ('signed index identity','signature rejected','artifact bytes system.ext2','unrelated'):
            with self.subTest(reason=reason),self.assertRaises(ValueError):verify.require_ext2_failure(ValueError(reason))

    def test_requalification_reuses_cases_without_starting_guests(self):
        import verify_x86_64_wide_shell_media as verify
        row=dict(name='retained',passed=True,reused=False,evidence_directory='original/path')
        old=dict(cases=[row],passed=True,closed=True,elapsed=10)
        frozen=dict(candidate='new',reused=dict(matrix=old))
        with patch.object(verify,'binding',return_value=frozen),patch.object(verify,'package_path'),\
             patch.object(verify,'save') as save,patch.object(verify.guest,'run_matrix') as guests:
            verify.runtime()
        guests.assert_not_called();result=save.call_args.args[1]
        self.assertEqual(result['fresh_guests'],0);self.assertEqual(result['physical_guest_seconds'],0)
        self.assertEqual(result['cases'],[dict(row,reused=True)])
        self.assertNotIn('command',verify.build_media.__code__.co_names)
        self.assertNotIn('build',verify.build_media.__code__.co_names)

    def folder(self):
        import tempfile
        return Path(tempfile.mkdtemp(prefix='bb-host-',dir=ROOT/'build/codex-agent'))

    def test_capture_is_bios_only_and_keeps_wide_runtime_guards(self):
        import ast,time,types
        import run_qemu_x86_64_wide_shell_media as guest
        import run_qemu_x86_64_wide_file as wide
        folder=self.folder();image=folder/'unused.elf'
        medium=types.SimpleNamespace(overlay=folder/'boot.qcow2',layout='hdd')
        namespace=guest.capture_namespace(time.monotonic(),medium,image,folder)
        self.assertIn('az_await_entry',namespace['_capture_run'].__code__.co_names)
        self.assertIn('configure_binary',namespace['_capture_run'].__code__.co_names)
        feeder=namespace['ConsoleFeeder'](guest.ay.input_plan(2))
        with self.assertRaises(ValueError):feeder.pump('','',lambda raw:len(raw),297)
        calls=[]
        class NotStarted(Exception):pass
        def blocked(command,**kwargs):calls.append(command);raise NotStarted()
        with patch.object(guest.selected.subprocess,'Popen',side_effect=blocked):
            with self.assertRaises(NotStarted):namespace['_capture_run'](image,folder,'python\npass\nend\ncontinue\n',4096,
                ['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0'],
                service_pio_budget=True,console_input=guest.ay.input_plan(2))
        self.assertEqual(len(calls),1);self.assertNotIn('-kernel',calls[0])
        self.assertIn('ide-hd,drive=az-boot,bus=ide.0,unit=1,bootindex=1',calls[0])
        before=wide.namespace()
        for name in ('validate_capture','validate_storage','validate_policy','validate_cpu','validate_identity',
                     'validate_io_and_faults','validate_terminal','validate_ipc_delivery','SessionFeeder'):
            self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(guest.ay,name)))),
                             ast.dump(ast.parse(inspect.getsource(getattr(before,name)))))
        self.assertEqual(sum(300+guest.bios_budget(c) if s is not None else guest.negative_budget(l,c)
            for _,l,c,s,_ in guest.CASES),1730)

    def test_data_fixture_is_canonical_and_absolute_deadline_is_not_renewed(self):
        import run_qemu_x86_64_wide_shell_media as guest
        import run_qemu_x86_64_wide_file as wide
        def init(obj,folder,**kwargs):
            obj.filesystem=kwargs['filesystem'];obj.file_program=kwargs['file_program']
            obj.block=obj.malformed=False
        for limit in (20,30,320,330):
            with patch.object(wide.old.file.pio.Fixture,'__init__',init):
                fixture=guest.data_fixture(self.folder(),bytes(29032),10,limit)
            self.assertIs(type(fixture),wide.old.file.pio.Fixture)
            self.assertEqual(fixture.expected(),media.image('ext2-1k',bytes(29032)))
            with patch.object(wide.time,'monotonic',return_value=10+limit),self.assertRaises(ValueError):fixture.run('info')
        for limit in (True,0,45,300,900):
            with self.assertRaises(ValueError):guest.data_fixture(self.folder(),bytes(29032),10,limit)

    def test_exact_make_projection_and_windows_dispatch(self):
        source=(ROOT/'Makefile').read_text(encoding='utf-8')
        self.assertNotIn('wide-shell-media',producer.without_wide_media_target(source))
        for bad in (source.replace('no kernel dependency.','changed dependency.'),
                    source.replace('x86_64-wide-shell-media:\n','x86_64-wide-shell-media: x86_64-bootstrap\n'),
                    source+producer.MAKE_BLOCK,source+'X86_64_WIDE_SHELL_MEDIA_DRIFT=1\n'):
            with self.assertRaises(ValueError):producer.without_wide_media_target(bad)
        windows=(ROOT/'scripts/build-x86_64-wide-shell-media.ps1').read_text()
        self.assertIn('scripts/build_x86_64_wide_shell_media.py --input-directory',windows)
        self.assertIn('finally',windows);self.assertNotIn('build-x86_64-bootstrap.ps1',windows)

    def test_publication_failure_preserves_previous_index(self):
        folder=self.folder();index=folder/'wide-shell-media.json';index.write_bytes(b'previous')
        candidate=folder/'shell-index-unit.json';candidate.write_bytes(b'new')
        with patch.object(producer.selected.old,'run',side_effect=ValueError('bad package')),\
             patch.object(producer.selected.os,'replace') as replace:
            with self.assertRaises(ValueError):producer.publish(folder,candidate,'openssl',folder/'log')
            replace.assert_not_called()
        with patch.object(producer.selected.old,'run'),\
             patch.object(producer.selected.os,'replace',side_effect=OSError('interrupted')) as replace:
            with self.assertRaises(OSError):producer.publish(folder,candidate,'openssl',folder/'log')
            replace.assert_called_once_with(candidate,index)
        self.assertEqual(index.read_bytes(),b'previous');self.assertEqual(candidate.read_bytes(),b'new')

    def test_first_failed_gate_prevents_any_later_execution(self):
        import verify_x86_64_wide_shell_media as verify
        frozen=dict(candidate='unit',commands=['python first','python second'],limits=[1,1])
        folder=self.folder()
        with patch.object(verify,'BASE',folder),patch.object(verify,'binding',return_value=frozen),\
             patch.object(verify,'command',return_value=dict(passed=False,elapsed=0)) as command:
            with self.assertRaisesRegex(ValueError,'first failed'):verify.all_gates()
            self.assertEqual(command.call_count,1)
            self.assertTrue((folder/'stopped.json').exists());self.assertFalse((folder/'gate-02.json').exists())
            with self.assertRaises(ValueError):verify.all_gates()
            self.assertEqual(command.call_count,1)

    def test_old_profile_remains_strict(self):
        import check_x86_64_shell_media as old
        self.assertEqual(old.FILES['file-program.prg'],1280)
        self.assertEqual(old.FILES['system.ext2'],131072)
        self.assertNotEqual(check.PROFILE,old.PROFILE)
        self.assertEqual(check.FILES['system.ext2'],1048576)
        p=dict(version=1,architecture='x86_64',profile=check.PROFILE,attempt='shell-media-'+'a'*32,
               artifacts={n:{} for n in check.FILES},devices=check.DEVICES)
        check.admit_package(p)
        with self.assertRaises(ValueError):old.admit_package(p)
        with self.assertRaises(ValueError):check.admit_package(dict(p,profile=old.PROFILE))

    def test_independent_ext2_direct_single_and_allocation_oracle(self):
        for size in (1537,12288,12289,29032,274432):
            app=bytes((n%251 for n in range(size)));raw=media.image('ext2-1k',app)
            check.data_volume(raw,app)
            for offset in (1028,1036,1080,2048,2060,3072,4096,5248,6528+4,6528+28,
                           6528+40,6528+40+13*4,21*1024+24,32*1024+size-1,1000*1024):
                bad=bytearray(raw);bad[offset]^=1
                with self.subTest(size=size,offset=offset),self.assertRaises(ValueError):check.data_volume(bytes(bad),app)
            if size>12288:
                bad=bytearray(raw);struct.pack_into('<I',bad,22*1024,21)
                with self.assertRaises(ValueError):check.data_volume(bytes(bad),app)
        for size in (1536,274433,524288):
            with self.assertRaises(ValueError):check.data_volume(media.image('ext2-1k',bytes(size)),bytes(size))

    def test_actual_accepted_inputs_and_no_kernel_compiler(self):
        values=producer.inputs(ROOT/'build/codex-agent/r83ba-wide-file/wide-pacing/x86_64')
        self.assertEqual(len(values['file-program.prg']),29032)
        for name in check.PINS:
            bad=dict(values);raw=bytearray(bad[name]);raw[-1]^=1;bad[name]=bytes(raw)
            with self.subTest(name=name),self.assertRaises(ValueError):check.input_binding(bad)
        source=inspect.getsource(producer.selected.build)
        self.assertNotIn('build-x86_64-bootstrap',source)
        self.assertNotIn('zig',source)

if __name__=='__main__':unittest.main()
