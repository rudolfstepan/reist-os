"""Host admission and owned-session cleanup faults for the normal starter."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        import run_x86_64_display as app
        self.app=app
        self.folder=Path(tempfile.mkdtemp(prefix='bf-host-',dir=ROOT/'build/codex-agent'))

    def test_actual_data_fixture_uses_selected_absolute_deadline(self):
        import time
        app=self.app;_,files=app.admit(app.DEFAULT)
        with self.assertRaises(ValueError):app.guest.data_fixture(self.folder/'old',files,time.monotonic(),60)
        (self.folder/'actual').mkdir()
        fixture=app.data_fixture(self.folder/'actual',files,time.monotonic(),60)
        fixture.verify('before');fixture.verify('after')
        self.assertEqual(fixture.base.read_bytes(),app.guest.apps.media.image('ext2-1k',files))
        for limit in (29,321,True,60.0):
            with self.assertRaises(ValueError):app.data_fixture(self.folder/'invalid',files,time.monotonic(),limit)
        self.assertFalse((self.folder/'invalid').exists())
        with patch.object(app.guest.apps.wide.time,'monotonic',return_value=fixture.started+60),\
             patch.object(app.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'wide media absolute deadline'):fixture.run('info','invalid')
            run.assert_not_called()

    def test_exact_admission_and_each_input_mutation(self):
        app=self.app
        attempt,files=app.admit(app.DEFAULT)
        self.assertEqual(set(files),{'boot.prg','cat.prg','ls.prg','probe.prg','data.txt'})
        values={n:app.check.bounded(attempt/n,app.check.FILES[n]) for n in app.PINS}
        app.inputs(values)
        for name in values:
            bad=dict(values);raw=bytearray(bad[name]);raw[-1]^=1;bad[name]=bytes(raw)
            with self.subTest(name=name),self.assertRaises(ValueError):app.inputs(bad)
        for bad in ({},dict(values,extra=b'')):
            with self.assertRaises(ValueError):app.inputs(bad)
        (self.folder/'display-media.json').write_bytes(b'foreign')
        with patch.object(app.check,'verify') as verify,patch.object(app.subprocess,'Popen') as process:
            with self.assertRaises(ValueError):app.admit(self.folder)
            verify.assert_not_called();process.assert_not_called()

    def test_check_only_and_invalid_selectors_before_effects(self):
        app=self.app
        with patch.object(app,'admit',return_value=(self.folder,{})) as admit,\
             patch.object(app.subprocess,'Popen') as process,patch.object(app,'SESSIONS',self.folder/'sessions'):
            self.assertTrue(app.launch(check_only=True)['passed'])
            process.assert_not_called();self.assertFalse((self.folder/'sessions').exists())
            admit.reset_mock()
            for opts in ({'layout':'usb'},{'ram':True},{'ram':1024},{'headless':1},
                         {'seconds':29},{'seconds':321},{'seconds':True},{'seconds':30.0},{'check_only':1}):
                with self.subTest(opts=opts),self.assertRaises(ValueError):app.launch(**opts)
            admit.assert_not_called();process.assert_not_called()

    def session(self,*,wait=0,setup=None,after=None,spawn=None,late=False,slow_cleanup=False,headless=True):
        app=self.app;medium=Mock();fixture=Mock();vm=Mock();vm.wait.return_value=wait
        if isinstance(wait,BaseException):vm.wait.side_effect=wait
        fixture.base=self.folder/'data';fixture.base.write_bytes(b'data')
        fixture.arguments.return_value=['-drive','readonly-data']
        medium.overlay=self.folder/'overlay'
        medium.verify.side_effect=lambda phase:(_ for _ in ()).throw(ValueError('cleanup failure')) if phase=='after' and after else None
        clock=[0.0]
        def make_fixture(*args):
            if late:clock[0]=28
            if setup:raise ValueError('setup failure')
            return fixture
        def terminate(proc):
            self.assertIs(proc,vm)
            if slow_cleanup:clock[0]+=4
        with patch.object(app,'admit',return_value=(self.folder,{})),patch.object(app,'SESSIONS',self.folder/'sessions'),\
             patch.object(app.guest.bios,'BootMedium',return_value=medium),\
             patch.object(app,'data_fixture',side_effect=make_fixture),\
             patch.object(app.check,'bounded',return_value=b'data'),\
             patch.object(app.guest.bios.ay.boot,'resolve_qemu',return_value=Path('qemu')),\
             patch.object(app.guest,'boot_arguments',return_value=['-boot','c']),\
             patch.object(app.guest.bios.ay.boot,'terminate_bounded',side_effect=terminate) as stop,\
             patch.object(app.subprocess,'Popen',return_value=vm,side_effect=spawn) as process,\
             patch.object(app.time,'monotonic',side_effect=lambda:clock[0]):
            failed=setup or after or spawn or late or slow_cleanup or type(wait) is int and wait!=0
            if failed:
                with self.assertRaises((ValueError,OSError)):app.launch(headless=headless,seconds=30)
            else:self.assertTrue(app.launch(headless=headless,seconds=30)['passed'])
            result=json.loads(next((self.folder/'sessions').glob('*/session.json')).read_text())
            self.assertEqual(result['passed'],not bool(failed))
            medium.verify.assert_any_call('after')
            if not setup:fixture.verify.assert_any_call('after')
            if not (setup or spawn or late):stop.assert_called_once()
            else:stop.assert_not_called()
            if after and spawn:self.assertIn('launch failure',result['error']);self.assertIn('cleanup failure',result['cleanup_error'])
            if not (setup or spawn or late):
                cmd=process.call_args.args[0]
                self.assertEqual(cmd[cmd.index('-display')+1],'none' if headless else 'gtk')
                self.assertIn('VGA,vgamem_mb=16',cmd);self.assertEqual(cmd[cmd.index('-nic')+1],'none')
                self.assertNotIn('-kernel',cmd);self.assertNotIn('-enable-kvm',cmd)
            return result

    def test_guest_exit(self):self.assertEqual(self.session()['reason'],'guest-exit')
    def test_explicit_user_window_command(self):self.session(headless=False)
    def test_timeout(self):self.assertEqual(self.session(wait=subprocess.TimeoutExpired('qemu',27))['reason'],'session-deadline')
    def test_interrupt(self):self.assertEqual(self.session(wait=KeyboardInterrupt())['reason'],'user-exit')
    def test_nonzero_guest(self):self.session(wait=1)
    def test_setup_failure(self):self.session(setup=True)
    def test_process_and_cleanup_failure_preserve_both(self):self.session(spawn=OSError('launch failure'),after=True)
    def test_setup_deadline(self):self.session(late=True)
    def test_cleanup_deadline(self):self.session(slow_cleanup=True)

if __name__=='__main__':unittest.main()
