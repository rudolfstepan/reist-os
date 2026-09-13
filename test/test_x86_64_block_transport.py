"""Bounded transport diagnostics: real capture control flow, mocked processes."""
from pathlib import Path
from unittest.mock import patch
import ast,copy,io,json,os,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
import run_qemu_x86_64_boot_programs as transport
import diagnose_x86_64_block_transport as diagnostic


class TransportTests(unittest.TestCase):
    def folder(self):
        base=ROOT/'build/codex-agent/r83ak-block-profile';base.mkdir(parents=True,exist_ok=True)
        # Retain diagnostic test evidence, including failures.
        return Path(tempfile.mkdtemp(prefix='transport-host-',dir=base))

    def test_default_and_opt_in_metrics(self):
        folder=self.folder();answer=('serial','trace')
        with patch.object(transport,'_capture_run',return_value=answer) as run:
            self.assertEqual(transport._capture(ROOT/'build/a.elf',folder,'code',4096),answer)
            self.assertNotIn('metrics',run.call_args.kwargs)
            self.assertFalse((folder/'capture-metrics.json').exists())
        for fail in (False,True):
            target=self.folder()
            def run(*args,**kwargs):
                kwargs['metrics'].update(pid=123,spawned=True,cpu={'kernel_ns':100,'user_ns':200})
                if fail:raise ValueError('expected failure')
                return answer
            with patch.object(transport,'_capture_run',side_effect=run):
                if fail:
                    with self.assertRaisesRegex(ValueError,'expected failure'):
                        transport._capture(ROOT/'build/a.elf',target,'code',4096,diagnostic_metrics=True)
                else:self.assertEqual(transport._capture(ROOT/'build/a.elf',target,'code',4096,diagnostic_metrics=True),answer)
            metrics=json.loads((target/'capture-metrics.json').read_text())
            self.assertEqual(metrics['version'],1);self.assertEqual(metrics['failed'],fail)
            self.assertEqual(metrics['cpu'],dict(kernel_ns=100,user_ns=200))

    def test_partial_build_history_does_not_hide_valid_provenance(self):
        folder=self.folder();(folder/'programs-incomplete').mkdir();valid=folder/'programs-valid';valid.mkdir()
        catalog=bytes(diagnostic.profile.wide.SIZE*4)
        (valid/'boot-programs.bin').write_bytes(catalog)
        self.assertEqual(diagnostic.catalog_source(folder,catalog),valid)
        for bad in (b'',bytes([1])+catalog[1:]):
            with self.assertRaises(ValueError):diagnostic.catalog_source(folder,bad)

    def test_real_capture_cleanup_and_failed_launches(self):
        class Process:
            def __init__(self,vm):
                self.pid=123 if vm else 124;self.returncode=None if vm else 0
                self.stdin=io.BytesIO();self.stdout=io.BytesIO(transport.process.SUCCESS.encode())
            def poll(self):return self.returncode
            def wait(self,timeout):return self.returncode
        for failure in ('none','vm','debugger','debugger_status'):
            folder=self.folder();made=[];terminated=[]
            (folder/'frame-trace.log').write_text('bounded trace',encoding='ascii')
            def popen(*args,**kwargs):
                is_vm=not made
                if failure==('vm' if is_vm else 'debugger'):raise OSError('expected launch failure')
                p=Process(is_vm);made.append(p)
                if not is_vm and failure=='debugger_status':p.returncode=71
                return p
            def terminate(p):p.returncode=0;terminated.append(p)
            with patch.object(transport.subprocess,'Popen',side_effect=popen),patch.object(transport,'resolve_qemu',return_value=Path('qemu.exe')),patch.object(transport,'terminate_bounded',side_effect=terminate),patch.object(transport,'process_cpu_ns',return_value=dict(kernel_ns=100,user_ns=200)):
                if failure!='none':
                    with self.assertRaises((OSError,ValueError)):
                        transport._capture(ROOT/'build/a.elf',folder,'code',4096,diagnostic_metrics=True)
                else:self.assertIn(transport.process.SUCCESS,transport._capture(ROOT/'build/a.elf',folder,'code',4096,diagnostic_metrics=True)[0])
            m=json.loads((folder/'capture-metrics.json').read_text());self.assertEqual(m['failed'],failure!='none')
            if made:
                self.assertIn(made[0],terminated);self.assertTrue(made[0].stdin.closed);self.assertTrue(made[0].stdout.closed)
            self.assertTrue((folder/'observe.gdb').exists())
            command=json.loads((folder/'command.json').read_text())
            self.assertNotIn('-icount',command);self.assertNotIn('-rtc',command);self.assertNotIn('-daemonize',command)

    def test_media_finally_unchanged(self):
        import run_qemu_x86_64_pio as pio
        class Media:
            def __init__(self):self.calls=[]
            def arguments(self,folder):return ['fixture']
            def verify(self,stage):self.calls.append(stage)
        for measured in (False,True):
            media=Media()
            with patch.object(pio,'Fixture',Media),patch.object(transport,'_capture',side_effect=ValueError('launch')):
                with self.assertRaises(ValueError):transport.capture(ROOT/'build/a.elf',self.folder(),'code',4096,media,diagnostic_metrics=measured)
            self.assertEqual(media.calls,['before','after'])

    def test_observer_construction_and_metric_mutations(self):
        for kind in diagnostic.INITIAL+diagnostic.FOLLOWUP:
            code=diagnostic.body(kind)
            compile(code,'diagnostic-observer','exec')
            self.assertNotIn('Qqemu.sstep',code)
            if not kind.startswith('full'):self.assertNotIn('set $',code)
            else:self.assertIn('pio_retire(slot,gen)',code) # Full oracle retained; OOM=None.
        base=diagnostic.profile.observer_body();scoped=diagnostic.profile.scope_pio_page_hooks(base)
        for line in base.splitlines():
            if line.strip().startswith('assert '):self.assertIn(line,scoped)
        self.assertIn("if not any(v['live'] for v in starts.values()):trace_before_hook.enabled=trace_after_hook.enabled=True",scoped)
        self.assertIn("if CASE in (2,4) and status and ((owner>>32)-3)%4==0:cancel_hook.enabled=True",scoped)
        self.assertIn("if CASE==6:cancel_hook.enabled=True",scoped)
        with self.assertRaises(ValueError):diagnostic.profile.scope_pio_page_hooks(scoped)
        good=dict(version=1,callbacks=2,reads=3,bytes=32,registers=1,host_ns=900,functions={'finish':dict(calls=2,host_ns=900)})
        trace='TRANSPORT_COST '+json.dumps(good)
        self.assertEqual(diagnostic.costs(trace),good)
        for key,value in (('version',2),('callbacks',4097),('reads',1000001),('bytes',1<<31),('host_ns',-1),('functions',{})):
            bad=copy.deepcopy(good);bad[key]=value
            with self.assertRaises(ValueError):diagnostic.costs('TRANSPORT_COST '+json.dumps(bad))
        for bad in ('',trace+'\n'+trace,trace.replace('"reads":','"unknown":')):
            with self.assertRaises(ValueError):diagnostic.costs(bad)

    def test_actual_measurement_wrapper_and_read_cap(self):
        lines=[]
        class Debugger:
            @staticmethod
            def write(line):lines.append(line)
            @staticmethod
            def execute(command,to_string=False):
                self.assertIn(command,('maintenance packet qqemu.sstepbits','maintenance packet qqemu.sstep'))
                return '0x7'
        class Hook:
            def __init__(self,fn):self.fn=fn
            def stop(self):self.fn();return False
        ns={'gdb':Debugger,'json':json,'Hook':Hook,'mem':lambda a,n:bytes(n),'reg':lambda n:17}
        exec(diagnostic.MEASURE,ns)
        def observed():
            self.assertEqual(ns['mem'](0,9),bytes(9));self.assertEqual(ns['reg']('rax'),17)
        hook=Hook(observed);self.assertFalse(hook.stop());self.assertFalse(hook.stop())
        with self.assertRaises(AssertionError):ns['mem'](0,270337)
        ns['cost_report']();ns['cost_report']()
        v=diagnostic.costs(''.join(lines));self.assertEqual((v['callbacks'],v['reads'],v['bytes'],v['registers']),(2,2,18,2))

    def test_validator_page_hook_lifecycle_and_exact_branches(self):
        profile=diagnostic.profile
        base=profile.observer_body(scoped=False);code=profile.scope_validator_page_hooks(base)
        compile(code,'scoped-validator-observer','exec')
        for line in base.splitlines():
            if line.strip().startswith('assert '):self.assertIn(line,code)
        self.assertNotIn("Hook('scheduler_fail',fail)",code)
        self.assertIn("Hook('native_pio_fail64',fail)",code)
        self.assertIn("release_hook=Hook('scheduler_release_task_frames64',release_begin);release_hook.enabled=False",code)
        with self.assertRaises(ValueError):profile.scope_validator_page_hooks(code)
        class Trap:
            enabled=False
        symbols={'process_run_complete_retire64':0x1000,'scheduler_release_task_frames64':0x2100,
                 'scheduler_fail':0x2500,'native_pio_fail64':0x3800}
        memory={}
        for source,target,opcode in (('process_run_complete_retire64','scheduler_release_task_frames64',0xe8),('scheduler_fail','native_pio_fail64',0xe9)):
            memory[symbols[source]]=bytes([opcode])+struct.pack('<i',symbols[target]-symbols[source]-5)
        hook=Trap();ns=dict(S=symbols,mem=lambda a,n:memory[a][:n],struct=struct,mode=lambda:8,release=None,release_hook=hook)
        tree=ast.parse(code)
        chosen=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('branch_target','release_arm')]
        self.assertEqual(len(chosen),2);exec(compile(ast.Module(chosen,type_ignores=[]),'actual-hook-functions','exec'),ns)
        for _ in range(8):
            ns['release_arm']();self.assertTrue(hook.enabled)
            with self.assertRaises(AssertionError):ns['release_arm']()
            hook.enabled=False
        for address in tuple(memory):
            good=memory[address]
            for bad in (b'',bytes([good[0]^1])+good[1:],good[:1]+struct.pack('<i',0)):
                memory[address]=bad
                with self.assertRaises(AssertionError):ns['release_arm']()
                self.assertFalse(hook.enabled)
            memory[address]=good
        for key,value in (('mode',lambda:7),('release',{})):
            good=ns[key];ns[key]=value
            with self.assertRaises(AssertionError):ns['release_arm']()
            self.assertFalse(hook.enabled);ns[key]=good
        release=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='release_begin')
        self.assertIsInstance(release.body[2],ast.Assign)
        statements=ast.Module([release.body[2]],type_ignores=[])
        hook.enabled=True;exec(compile(statements,'actual-release-disarm','exec'),ns);self.assertFalse(hook.enabled)
        # Published retirement's actual entry still CALLs the original helper;
        # NativePIO's scheduler failure is an unconditional, flag-preserving JMP.
        asm=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        self.assertRegex(asm,r'process_run_complete_retire64:\s*%endif\s*call scheduler_release_task_frames64')
        asm=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        self.assertRegex(asm,r'scheduler_fail:\s*%ifdef REIST_NATIVE_PIO\s*;[^\n]*\n\s*jmp native_pio_fail64')

    def test_actual_process_counter_read(self):
        if os.name!='nt':self.skipTest('Windows reference metric')
        values=transport.process_cpu_ns(os.getpid())
        self.assertEqual(set(values),{'kernel_ns','user_ns'})
        self.assertTrue(all(type(v)==int and v>=0 for v in values.values()))
        with self.assertRaises(OSError):transport.process_cpu_ns(0)

    def test_creation_page_hooks_exact_success_retry_and_replacement(self):
        profile=diagnostic.profile;base=profile.scope_validator_page_hooks(profile.observer_body(scoped=False))
        code=profile.scope_creation_page_hooks(base);compile(code,'creation-observer','exec')
        for line in base.splitlines():
            if line.strip().startswith('assert '):self.assertIn(line,code)
        self.assertIn('if slot==0:create_watch()',code)
        self.assertIn("if r['slot']==2 and CASE!=6 and (r['gen']-3)%4==0:create_watch()",code)
        self.assertIn("create_watch_leave(reg('rax')==0xfffffffffffffff4)",code)
        with self.assertRaises(ValueError):profile.scope_creation_page_hooks(code)
        class Trap:
            enabled=False
        for case in range(8):
            ns=dict(created=None,create_begin_hook=Trap(),copy_hook=Trap(),create_end_hook=Trap())
            functions=[node for node in ast.parse(code).body if isinstance(node,ast.FunctionDef) and node.name.startswith('create_watch')]
            self.assertEqual(len(functions),3);exec(compile(ast.Module(functions,type_ignores=[]),'actual-create-hooks','exec'),ns)
            for run in range(2):
                for child in range(1 if case==6 else 2):
                    ns['create_watch']()
                    with self.assertRaises(AssertionError):ns['create_watch']()
                    for retry in ([True,False] if case==7 and child==0 else [False]):
                        ns['create_watch_enter']();ns['created']=True
                        self.assertFalse(ns['create_begin_hook'].enabled)
                        self.assertTrue(ns['copy_hook'].enabled and ns['create_end_hook'].enabled)
                        with self.assertRaises(AssertionError):ns['create_watch_enter']()
                        ns['create_watch_leave'](retry);ns['created']=None
                        self.assertEqual(ns['create_begin_hook'].enabled,retry)
                        self.assertFalse(ns['copy_hook'].enabled or ns['create_end_hook'].enabled)
            with self.assertRaises(AssertionError):ns['create_watch_enter']()
            with self.assertRaises(AssertionError):ns['create_watch_leave'](False)

    def test_receipt_classification_and_mutations(self):
        from test_x86_64_block_profile_runtime import sample
        serial,_=sample(0)
        self.assertEqual(diagnostic.outcome(serial,'','finish',None,27)['classification'],'normal')
        for bad in (serial+serial,serial.replace(transport.process.SUCCESS,''),serial.replace(transport.process.DONE,'')):
            with self.assertRaises(ValueError):diagnostic.outcome(bad,'','finish',None,27)
        cpu=''
        for run in range(2):
            for slot,gen,status,state,ticks in ((2,run*3+3,256,3,32),(0,run*3+1,221,4,9),(1,run*3+2,77,4,1)):
                cpu+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,state,ticks,0x410123).hex().upper()+'\n'
            cpu+=transport.process.DONE+'\n'
        cpu+=transport.process.SUCCESS
        self.assertEqual(diagnostic.outcome(cpu,'','rpc-noop',None,27)['classification'],'cpu_bound')
        for bad in (cpu+cpu,cpu.replace(transport.process.DONE,''),cpu.replace('2000000000000000','2100000000000000'),transport.process.DONE+cpu.replace(transport.process.DONE,'',1)):
            with self.assertRaises(ValueError):diagnostic.outcome(bad,'','rpc-noop',None,27)


if __name__=='__main__':unittest.main()
