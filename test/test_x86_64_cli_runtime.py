"""No guest starts: actual capture composition and bounded launcher behavior."""
from pathlib import Path
import ast,copy,inspect,json,struct,subprocess,sys,tempfile,time,types,unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_qemu_x86_64_cli_media as guest
import run_x86_64_cli as launcher

class CliRuntimeTests(unittest.TestCase):
    def folder(self):return Path(tempfile.mkdtemp(prefix='bd-runtime-host-',dir=ROOT/'build/codex-agent'))

    def hang_events(self,delta=10):
        spec=('hang',0,2,4096,(6,));start=dict(gen=7,run=1,slot=4,parent=1<<32,
            args=['probe.prg','/data.txt','@af1:00000105','@af1:00000106'])
        frame=struct.pack('<4I5Qi3IQ',1,512,0,1,1,7,1,1,4650,0,276,0,0,0)+bytes(432)
        bulk=(struct.pack('<3I',2,2060,512)+frame+bytes(1536)).hex()
        events=[dict(kind='return',gen=1,op=53,args=[262,0,970],result=0,before=bulk,now=3680),
            dict(kind='return',gen=1,op=54,args=[261,0,950],result=-110,entered=3700,now=4650),
            dict(kind='call',gen=1,op=52,args=[261],entered=4650),
            dict(kind='return',gen=1,op=52,args=[261],result=0,entered=4650,now=4650),
            dict(kind='call',gen=1,op=52,args=[262],entered=4650+delta),
            dict(kind='return',gen=1,op=52,args=[262],result=0,entered=4650+delta,now=4650+delta),
            dict(kind='return',gen=7,op=54,args=[262,0,1000],result=-32,entered=3700,now=4650+delta),
            dict(kind='call',gen=7,op=9,args=[1,0,0,0,0,0],entered=4660+delta)]
        return spec,start,events,{7:dict(status=1,state=4)}

    def test_distinct_close_syscalls_keep_deadline_and_actual_wakeup(self):
        for delta in (0,10,20,40):
            spec,start,events,receipts=self.hang_events(delta)
            self.assertEqual(guest.qualified_outcome(spec,start,[start],events,receipts),(1,4))

    def test_close_sequence_mutations_remain_fail_closed(self):
        spec,start,events,receipts=self.hang_events()
        for n in range(len(events)):
            with self.assertRaises(ValueError):guest.qualified_outcome(spec,start,[start],events[:n]+events[n+1:],receipts)
        for n,key,value in ((1,'now',4651),(2,'entered',4651),(3,'result',-9),(4,'entered',4649),
                            (5,'result',-9),(5,'now',4661),(6,'entered',4650),(6,'now',4700),
                            (6,'result',0),(7,'entered',5651)):
            bad=copy.deepcopy(events);bad[n][key]=value
            with self.subTest(n=n,key=key),self.assertRaises(ValueError):guest.qualified_outcome(spec,start,[start],bad,receipts)
        bad=copy.deepcopy(events);bad.insert(4,dict(kind='call',gen=1,op=53,args=[262],entered=4650))
        with self.assertRaises(ValueError):guest.qualified_outcome(spec,start,[start],bad,receipts)
        for delta in (-1,50,1000):
            spec,start,events,receipts=self.hang_events(delta)
            with self.assertRaises(ValueError):guest.qualified_outcome(spec,start,[start],events,receipts)

    def test_case_selection_and_original_predicates(self):
        self.assertEqual(len(guest.CASES),10)
        self.assertEqual(sum(300+guest.bios_budget(c) if s is not None else guest.negative_budget(l,c)
            for _,l,c,s,_ in guest.CASES),1730)
        self.assertEqual(guest.CASES[5:],guest.bios.CASES[5:])
        for label in guest.LABELS.values():
            selected=guest.namespace(label);old=guest.apps.namespace(label)
            for name in ('validate_capture','validate_storage','validate_policy','validate_cpu','validate_identity',
                         'validate_terminal','validate_ipc_delivery','evaluate','observer','SessionFeeder'):
                self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(selected.ay,name)))),
                                 ast.dump(ast.parse(inspect.getsource(getattr(old,name)))))
            self.assertIs(selected.ay.validate_objects,guest.apps.validate_objects)
            self.assertEqual(selected.ay.input_plan(0),guest.apps.input_plan(label))

    def test_bios_only_capture_retains_step_and_wide_guards_without_spawn(self):
        folder=self.folder();image=folder/'unused.elf';selected=guest.namespace('hang')
        medium=types.SimpleNamespace(overlay=folder/'boot.qcow2',layout='floppy')
        ns=selected.capture_namespace(time.monotonic(),medium,image,folder)
        self.assertIn('az_await_entry',ns['_capture_run'].__code__.co_names)
        self.assertIn('configure_binary',ns['_capture_run'].__code__.co_names)
        self.assertIn('session_step_loop',ns['_capture_run'].__code__.co_names)
        feeder=ns['ConsoleFeeder'](guest.apps.input_plan('hang'))
        with self.assertRaises(ValueError):feeder.pump('','',lambda raw:len(raw),297)
        calls=[]
        class NotStarted(Exception):pass
        def blocked(command,**kwargs):calls.append(command);raise NotStarted()
        with patch.object(selected.subprocess,'Popen',side_effect=blocked):
            with self.assertRaises(NotStarted):ns['_capture_run'](image,folder,'python\npass\nend\ncontinue\n',4096,
                ['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0'],
                service_pio_budget=True,console_input=guest.apps.input_plan('hang'))
        self.assertEqual(len(calls),1);self.assertNotIn('-kernel',calls[0])
        self.assertIn('floppy,drive=az-boot,unit=0',calls[0])
        self.assertIn('ide-hd,drive=pio-layer,bus=ide.0,unit=0',calls[0])

    def test_data_fixture_exact_files_and_unrenewable_deadline(self):
        files={'boot.prg':bytes(29032),'cat.prg':bytes(16736),'ls.prg':bytes(16736),
               'probe.prg':bytes(16840),'data.txt':guest.apps.media.DATA}
        def init(obj,folder,**kwargs):
            obj.filesystem=kwargs['filesystem'];obj.file_program=kwargs['file_program'];obj.block=obj.malformed=False
        for limit in (20,30,320,330):
            with patch.object(guest.apps.wide.old.file.pio.Fixture,'__init__',init):
                fixture=guest.data_fixture(self.folder(),files,10,limit)
            self.assertIs(type(fixture),guest.apps.wide.old.file.pio.Fixture)
            self.assertEqual(fixture.expected(),guest.apps.media.image('ext2-1k',files))
            with patch.object(guest.apps.wide.time,'monotonic',return_value=10+limit),self.assertRaises(ValueError):fixture.run('info')
        for limit in (True,0,45,300,900):
            with self.assertRaises(ValueError):guest.data_fixture(self.folder(),files,10,limit)

    def test_launcher_fail_closed_and_check_only_no_vm_or_medium(self):
        with patch.object(launcher.check,'verify',side_effect=ValueError('bad signature')),\
             patch.object(launcher.subprocess,'Popen') as spawn,patch.object(guest.bios,'BootMedium') as medium:
            with self.assertRaises(ValueError):launcher.launch()
            spawn.assert_not_called();medium.assert_not_called()
        with patch.object(launcher.check,'verify',return_value=self.folder()),\
             patch.object(launcher.subprocess,'Popen') as spawn,patch.object(guest.bios,'BootMedium') as medium:
            self.assertTrue(launcher.launch(check_only=True)['passed'])
            spawn.assert_not_called();medium.assert_not_called()
        for kwargs in ({'ram':True},{'ram':2048},{'layout':'raw-disk'},{'check_only':1}):
            with patch.object(launcher.check,'verify') as verify,self.assertRaises(ValueError):launcher.launch(**kwargs)
            verify.assert_not_called()

    def test_launcher_timeout_has_both_no_write_checks_and_no_kernel(self):
        folder=self.folder();data=Mock();data.base.read_bytes.return_value=b'volume'
        data.arguments.return_value=['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0']
        medium=Mock();medium.overlay=folder/'base.qcow2'
        vm=Mock();vm.wait.side_effect=subprocess.TimeoutExpired('qemu',317)
        with patch.object(launcher.check,'verify',return_value=folder),\
             patch.object(launcher.check,'bounded',return_value=b'volume'),patch.object(launcher.check,'input_binding'),\
             patch.object(guest,'data_fixture',return_value=data),patch.object(guest.bios,'BootMedium',return_value=medium),\
             patch.object(guest.bios.ay.boot,'terminate_bounded') as terminate,\
             patch.object(launcher.subprocess,'Popen',return_value=vm) as spawn:
            row=launcher.launch();self.assertTrue(row['passed']);self.assertEqual(row['reason'],'session-deadline')
            self.assertNotIn('-kernel',spawn.call_args.args[0]);self.assertIn('stdio',spawn.call_args.args[0])
            terminate.assert_called_once_with(vm)
            self.assertEqual([c.args for c in data.verify.call_args_list],[('before',),('after',)])
            self.assertEqual([c.args for c in medium.verify.call_args_list],[('before',),('after',)])
            self.assertGreater(vm.wait.call_args.kwargs['timeout'],0);self.assertLessEqual(vm.wait.call_args.kwargs['timeout'],317)

    def test_launcher_cleanup_failure_cannot_publish_pass(self):
        source=inspect.getsource(launcher.launch)
        self.assertIn("result['passed']=False",source)
        ps=(ROOT/'scripts/start-x86_64-cli.ps1').read_text()
        self.assertIn('finally',ps);self.assertIn('$LASTEXITCODE',ps);self.assertNotIn('Invoke-Expression',ps)

if __name__=='__main__':unittest.main()
