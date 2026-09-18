"""Execute the real profiler and capture diagnostics, never launch a guest."""
from pathlib import Path
from unittest.mock import Mock, patch
import ast,copy,io,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import diagnose_x86_64_file_transport as diagnostic
transport=diagnostic.launch.wide.transport


class FileTransportTests(unittest.TestCase):
    def test_service_pio_capture_reserves_cleanup_and_rejects_overrun(self):
        class Process:
            def __init__(self):self.returncode=None;self.stdin=io.BytesIO();self.stdout=io.BytesIO()
            def poll(self):return self.returncode
            def wait(self,timeout):self.returncode=0;return 0
        for finish in (143,145,146):
            folder=self.folder();(folder/'frame-trace.log').write_text('')
            vm,debug=Process(),Process();output=Mock();output.get.side_effect=transport.queue.Empty;output.empty.return_value=True
            def terminate(p):p.returncode=0
            clock=Mock(side_effect=[100,141,142,finish])
            with self.subTest(finish=finish),patch.object(transport.subprocess,'Popen',side_effect=[vm,debug]),patch.object(transport,'resolve_qemu',return_value=Path('qemu.exe')),patch.object(transport.time,'monotonic',clock),patch.object(transport,'terminate_bounded',side_effect=terminate),patch.object(transport.queue,'Queue',return_value=output):
                if finish>145:
                    with self.assertRaisesRegex(ValueError,'service PIO total host deadline'):
                        transport._capture_run(ROOT/'build/a.elf',folder,'code',4096,service_pio_budget=True)
                else:self.assertEqual(transport._capture_run(ROOT/'build/a.elf',folder,'code',4096,service_pio_budget=True),('',''))
            self.assertEqual(output.get.call_count,1);self.assertEqual(clock.call_count,4)
            self.assertTrue(vm.stdin.closed and vm.stdout.closed);self.assertEqual(debug.returncode,0)

    def test_service_cpu_capture_reserves_cleanup(self):
        class Process:
            def __init__(self):self.returncode=None;self.stdin=io.BytesIO();self.stdout=io.BytesIO()
            def poll(self):return self.returncode
            def wait(self,timeout):self.returncode=0;return 0
        folder=self.folder();(folder/'frame-trace.log').write_text('')
        vm,debug=Process(),Process();output=Mock();output.get.side_effect=transport.queue.Empty;output.empty.return_value=True
        def terminate(p):p.returncode=0
        clock=Mock(side_effect=[100,126,127,128])
        with patch.object(transport.subprocess,'Popen',side_effect=[vm,debug]),patch.object(transport,'resolve_qemu',return_value=Path('qemu.exe')),patch.object(transport.time,'monotonic',clock),patch.object(transport,'terminate_bounded',side_effect=terminate),patch.object(transport.queue,'Queue',return_value=output):
            self.assertEqual(transport._capture_run(ROOT/'build/a.elf',folder,'code',4096,service_cpu_budget=True),('',''))
        # One observation at26s, stop at27s, cleanup checked at28s: total<=30.
        self.assertEqual(output.get.call_count,1);self.assertEqual(clock.call_count,4)
        self.assertTrue(vm.stdin.closed and vm.stdout.closed)

    def test_case6_timing_original_observer_and_capture_dispatch(self):
        folder=self.folder();original='set logging enabled on\npython\n'+diagnostic.launch.observer_body()+'\nend\ncontinue\n'
        for kind in ('minimal','profiled'):
            code=diagnostic.case6_timing_observer(kind,original,folder)
            expected=diagnostic.timeline_observer('stops',original,folder) if kind=='minimal' else diagnostic.combined_observer(original,folder)
            self.assertEqual(code,expected)
            self.assertEqual(code.count('Hook('),original.count('Hook('))
            self.assertEqual(code.count('write_memory'),original.count('write_memory'))
            for line in original.splitlines():
                if line.strip().startswith('assert '):self.assertIn(line,code)
            self.assertNotIn('maintenance packet',code)
            ast.parse(code.split('python\n',1)[1].removesuffix('\nend\ncontinue\n'))
        with self.assertRaises(ValueError):diagnostic.case6_timing_observer('other',original,folder)
        image=folder/'image.elf';media=object()
        with patch.object(diagnostic.launch.wide.transport,'capture',return_value=('s','t')) as capture:
            self.assertEqual(diagnostic.case6_timing_capture(image,folder,original,media),('s','t'))
            capture.assert_called_once_with(image,folder,original,4096,media,diagnostic_metrics=True,binary_memory='full')
        with patch.object(diagnostic.launch.wide.transport,'capture',side_effect=ValueError('original failure')) as capture:
            with self.assertRaisesRegex(ValueError,'original failure'):diagnostic.case6_timing_capture(image,folder,original,media)
            self.assertEqual(capture.call_count,1)
        tree=ast.parse(Path(diagnostic.__file__).read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='timing_main')
        calls=[n for n in ast.walk(main) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('original','media')]
        self.assertEqual(len(calls),2)
        validation=next(n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='validate')
        for profile,expected in (('case6',(6,2,'ext2-1k')),('fat12',(0,0,'fat12'))):
            case,layout,filesystem,_,_=diagnostic.timing_profile(profile)
            self.assertEqual((case,layout,filesystem),expected)
            env=dict(launch=diagnostic.launch,folder=folder,symbols={},core={},addresses={},raw=b'ELF',
                case=case,layout=layout,filesystem=filesystem,serial='serial',trace='trace',counts={'pages':1})
            with patch.object(diagnostic.launch,'observer',return_value='script') as observer,patch.object(diagnostic.launch.pio,'Fixture',return_value=media) as fixture,patch.object(diagnostic.launch,'validate') as validate:
                exec(compile(ast.Module(body=calls,type_ignores=[]),'<actual timing dispatch>','exec'),env)
                exec(compile(ast.Module(body=[ast.Expr(value=validation,lineno=1,col_offset=0)],type_ignores=[]),'<actual timing validation>','exec'),env)
                observer.assert_called_once_with({}, {},folder,case,layout,None,{},b'ELF')
                fixture.assert_called_once_with(folder,filesystem=filesystem,file_program=b'ELF')
                validate.assert_called_once_with('serial','trace',case,layout,None,{'pages':1},b'ELF')

    def test_case6_timing_pinned_image_and_pair_budget(self):
        package=dict(case6_timing_image='build/codex-agent/r83am-file-launch/oom-boundary-renewal/guests/attempt-34ee1dafaa1c4d80bb67d75e6c11aa47/build-6-2/x86_64/reist-x86_64-bootstrap.elf',
            case6_timing_image_sha256='6a5d2859f8d57112c4884d42d9afaee2ea552c735f7110d244668895238104b3')
        with patch.object(diagnostic,'digest',return_value=package['case6_timing_image_sha256']):
            self.assertEqual(diagnostic.case6_timing_image(package),ROOT/package['case6_timing_image'])
            for bad in ('../image.elf','build/other.elf',package['case6_timing_image'].replace('/build-6-2/','/build-0-0/')):
                with self.assertRaises(ValueError):diagnostic.case6_timing_image(dict(package,case6_timing_image=bad))
        with patch.object(diagnostic,'digest',return_value='0'*64):
            with self.assertRaises(ValueError):diagnostic.case6_timing_image(package)
        with self.assertRaises(ValueError):diagnostic.case6_timing_image(dict(package,case6_timing_image_sha256='0'*64))
        base=self.folder()
        with self.assertRaises(ValueError):diagnostic.reserve_case6_timing(base,'profiled')
        first=diagnostic.reserve_case6_timing(base,'minimal')
        with self.assertRaises(ValueError):diagnostic.reserve_case6_timing(base,'minimal')
        with self.assertRaises(ValueError):diagnostic.reserve_case6_timing(base,'profiled')
        (first/'summary.json').write_text(json.dumps(dict(completed=False)))
        with self.assertRaises(ValueError):diagnostic.reserve_case6_timing(base,'profiled')
        (first/'summary.json').write_text(json.dumps(dict(completed=True)))
        diagnostic.reserve_case6_timing(base,'profiled')
        with self.assertRaises(ValueError):diagnostic.reserve_case6_timing(base,'profiled')

    def test_fat12_timing_pinned_image_and_fixed_profile(self):
        package=dict(fat12_timing_image='build/codex-agent/r83am-file-launch/post-case6-renewal/guests/attempt-399aa05cf7914430afdf9bda934882a9/build-0-0/x86_64/reist-x86_64-bootstrap.elf',
            fat12_timing_image_sha256='3c79f8becaffdd9428e1ed23f2d5c6c30367e5f801fb9cb13d4b9b2944abc8a8')
        with patch.object(diagnostic,'digest',return_value=package['fat12_timing_image_sha256']):
            self.assertEqual(diagnostic.fat12_timing_image(package),ROOT/package['fat12_timing_image'])
            for bad in ('../image.elf','build/other.elf',package['fat12_timing_image'].replace('/build-0-0/','/build-6-2/')):
                with self.assertRaises(ValueError):diagnostic.fat12_timing_image(dict(package,fat12_timing_image=bad))
        with patch.object(diagnostic,'digest',return_value='0'*64):
            with self.assertRaises(ValueError):diagnostic.fat12_timing_image(package)
        with self.assertRaises(ValueError):diagnostic.fat12_timing_image(dict(package,fat12_timing_image_sha256='0'*64))
        with self.assertRaises(ValueError):diagnostic.timing_profile('../case6')
        with self.assertRaises(ValueError):diagnostic.timing_main('other','fat12')
        self.assertEqual(diagnostic.timing_profile('fat12'),(0,0,'fat12','verification-status-post-case6.json',diagnostic.fat12_timing_image))
        self.assertEqual(diagnostic.timing_profile('case6'),(6,2,'ext2-1k','verification-status-oom-boundary.json',diagnostic.case6_timing_image))

    def test_timing_cli_and_legacy_wrapper_dispatch(self):
        with patch.object(diagnostic,'timing_main',return_value=7) as run:
            self.assertEqual(diagnostic.case6_timing_main('minimal'),7)
            run.assert_called_once_with('minimal','case6')
        for profile in ('case6','fat12'):
            for kind in ('minimal','profiled'):
                with patch.object(sys,'argv',['diagnostic','--'+profile+'-timing',kind]),patch.object(diagnostic,'timing_main',return_value=9) as run:
                    self.assertEqual(diagnostic.main(),9);run.assert_called_once_with(kind,profile)
        for args in (['--fat12-timing','other'],['--fat12-timing','minimal','--case6-timing','minimal']):
            with patch.object(sys,'argv',['diagnostic',*args]),patch.object(sys,'stderr',io.StringIO()),patch.object(diagnostic,'timing_main') as run:
                with self.assertRaises(SystemExit):diagnostic.main()
                run.assert_not_called()

    def test_equivalence_cost_two_reads_timing_errors_and_limits(self):
        import hashlib
        now=[0];rows=[];calls=[]
        def read(a,n):calls.append((a,n));now[0]+=20;return bytes(n)
        cost=diagnostic.EquivalenceReadCost(lambda:now[0],rows.append)
        wrapped=cost.wrap(read)
        self.assertEqual(wrapped(1,8),bytes(8));self.assertEqual(rows,[])
        for address in (0xffffffff80b05000,0xffff80010002d000):
            self.assertEqual(wrapped(address,32768),bytes(32768))
        self.assertEqual(len(calls),3);self.assertEqual(len(rows),4)
        self.assertEqual([r['event'] for r in rows],['enter','return']*2)
        self.assertEqual(rows[1]['read_ns'],20)
        self.assertEqual(rows[1]['sha256'],hashlib.sha256(bytes(32768)).hexdigest())
        with self.assertRaises(ValueError):wrapped(0xffffffff80b05000,32768)
        self.assertEqual(len(calls),3)
        for result in ('failure','short'):
            rows=[];cost=diagnostic.EquivalenceReadCost(lambda:0,rows.append)
            def fail(a,n):
                if result=='failure':raise OSError('original read failure')
                return b'x'
            if result=='failure':
                with self.assertRaisesRegex(OSError,'original read failure'):cost.wrap(fail)(0xffffffff80b05000,32768)
                self.assertEqual(rows[-1]['event'],'exception')
            else:self.assertEqual(cost.wrap(fail)(0xffffffff80b05000,32768),b'x')
        for address,size in ((0,32768),(0xffffffff80b05000,270337)):
            cost=diagnostic.EquivalenceReadCost(lambda:0,lambda r:None)
            with self.assertRaises(ValueError):cost.wrap(read)(address,size)
        now=[0];cost=diagnostic.EquivalenceReadCost(lambda:now[0],lambda r:None)
        now[0]=24000000000
        with self.assertRaises(ValueError):cost.wrap(read)(0xffffffff80b05000,32768)

    def test_equivalence_cost_actual_reader_keeps_both_comparisons_and_failure(self):
        import qemu_binary_memory as binary
        for broken in (False,True):
            folder=self.folder();rows=[];original_calls=[];closed=[]
            def original(a,n):original_calls.append((a,n));return (b'x' if broken else b'\0')*n
            cost=diagnostic.EquivalenceReadCost(lambda:0,rows.append)
            class QMP:
                def __init__(self,*args):pass
                def stopped(self):pass
                def save(self,physical,size,path):path.write_bytes(bytes(size))
                def close(self):closed.append(True)
            reader=binary.Reader(1234,'host',folder,4096,cost.wrap(original),lambda:0x100000,True)
            def translate(a,n,*args):return a-(binary.HIGH if a>=binary.HIGH else binary.DM)
            with patch.object(binary,'translate',side_effect=translate),patch.object(binary,'QMP',QMP):
                if broken:
                    with self.assertRaisesRegex(ValueError,'binary GDB byte mismatch'):reader.read(binary.HIGH+0xb05000,32768)
                    self.assertTrue(reader.failed);self.assertIsNone(reader.client)
                else:
                    for a in (binary.HIGH+0xb05000,binary.DM+0x10002d000,binary.DM+0x100030000):self.assertEqual(reader.read(a,32768),bytes(32768))
                    self.assertEqual(reader.compared,{'kernel','high'})
                    self.assertEqual(len(original_calls),2);self.assertEqual(len(rows),4)
            self.assertEqual(len(closed),1 if broken else 3)

    def test_equivalence_cost_binding_and_original_observer_identity(self):
        import hashlib,types
        folder=self.folder();env=dict(EQUIVALENCE_COST_FILE=str(folder/'equivalence-cost.jsonl'),
            EquivalenceReadCost=diagnostic.EquivalenceReadCost,mem=lambda a,n:bytes(n),json=json,hashlib=hashlib)
        exec(diagnostic.EQUIVALENCE_COST_BINDING,env)
        self.assertEqual(env['mem'](0xffffffff80b05000,32768),bytes(32768))
        self.assertEqual(len((folder/'equivalence-cost.jsonl').read_text().splitlines()),2)
        original='set logging enabled on\npython\n'+diagnostic.launch.observer_body()+'\nend\ncontinue\n'
        for kind in ('minimal','profiled'):
            code=diagnostic.equivalence_cost_observer(kind,original,folder)
            for line in original.splitlines():
                if line.strip().startswith('assert '):self.assertIn(line,code)
            self.assertEqual(code.count('Hook('),original.count('Hook('))
            self.assertEqual(code.count('write_memory'),original.count('write_memory'))
            self.assertEqual('cost=Cost(' in code,kind=='profiled')
            for banned in ('Timeline','Qqemu.sstep','maintenance packet'):self.assertNotIn(banned,code)
            ast.parse(code.split('python\n',1)[1].removesuffix('\nend\ncontinue\n'))

    def test_equivalence_cost_decoder_ledger_and_pair_bounds(self):
        import hashlib
        folder=self.folder();path=folder/'equivalence-cost.jsonl';rows=[];now=[0]
        cost=diagnostic.EquivalenceReadCost(lambda:now[0],rows.append)
        for address in (0xffffffff80b05000,0xffff80010002d000):cost.wrap(lambda a,n:bytes(n))(address,32768)
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        ledger=[dict(address=r['address'],bytes=r['bytes'],sha256=r['sha256'],equivalence=r['kind']) for r in rows if r['event']=='return']
        self.assertEqual(diagnostic.equivalence_cost_records(path,ledger)['comparison_ns'],0)
        for broken in (rows+rows[:1],[rows[1],rows[0],*rows[2:]]):
            path.write_text(''.join(json.dumps(r)+'\n' for r in broken))
            with self.assertRaises(ValueError):diagnostic.equivalence_cost_records(path,ledger)
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows));ledger[0]['sha256']='0'*64
        with self.assertRaises(ValueError):diagnostic.equivalence_cost_records(path,ledger)
        base=self.folder()
        with self.assertRaises(ValueError):diagnostic.reserve_equivalence_cost(base,'profiled')
        first=diagnostic.reserve_equivalence_cost(base,'minimal')
        with self.assertRaises(ValueError):diagnostic.reserve_equivalence_cost(base,'minimal')
        (first/'summary.json').write_text(json.dumps(dict(completed=True)))
        diagnostic.reserve_equivalence_cost(base,'profiled')
        with self.assertRaises(ValueError):diagnostic.reserve_equivalence_cost(base,'profiled')

    def test_continuation_actual_step_probe_only_two_bounded_read_queries(self):
        calls=[];saved=[]
        def execute(command,to_string):calls.append((command,to_string));return '0x7'
        diagnostic.continuation_step_probe(execute,saved.append)
        self.assertEqual(calls,[('maintenance packet qqemu.sstepbits',True),('maintenance packet qqemu.sstep',True)])
        self.assertEqual(saved,[{'qqemu.sstepbits':'0x7','qqemu.sstep':'0x7'}])
        for answer in ('x'*8193,42):
            saved=[]
            with self.assertRaises(ValueError):diagnostic.continuation_step_probe(lambda *a,**k:answer,saved.append)
            self.assertFalse(saved)

    def test_continuation_observer_preserves_original_and_queries_only_readonly_mask(self):
        original='set logging enabled on\npython\n'+diagnostic.launch.observer_body()+'\nend\ncontinue\n'
        for mode in ('plain','measured'):
            code=diagnostic.continuation_observer(mode,original,Path('build/codex-agent/trace'))
            for line in original.splitlines():
                if line.strip().startswith('assert '):self.assertIn(line,code)
            self.assertEqual(code.count('Hook('),original.count('Hook('))
            self.assertEqual(code.count('write_memory'),original.count('write_memory'))
            self.assertIn('maintenance packet qqemu.sstepbits',code)
            self.assertNotIn('Qqemu.sstep',code)
            ast.parse(code.split('python\n',1)[1].removesuffix('\nend\ncontinue\n'))
        with self.assertRaises(ValueError):diagnostic.continuation_observer('wrong',original,self.folder())

    def test_continuation_decoder_and_pair_budget(self):
        folder=self.folder();path=folder/'stderr.log'
        path.write_text('[1@10.000000] gdbstub_op_continue \n[2@10.010000] pic_interrupt irq 0\n[1@10.020000] gdbstub_hit_break pc=0x1\n')
        rows=diagnostic.continuation_records(path)
        self.assertEqual([r['event'] for r in rows],['gdbstub_op_continue','pic_interrupt','gdbstub_hit_break'])
        self.assertEqual(rows[-1]['ns']-rows[0]['ns'],20000000)
        path.write_text('2026-09-14T09:30:06.432047Z vm_state_notify running 1 reason 9 (running)\n'
                        '2026-09-14T09:30:06.433047Z gdbstub_op_stepping Stepping CPU 0\n')
        rows=diagnostic.continuation_records(path)
        self.assertEqual(rows[-1]['ns']-rows[0]['ns'],1000000)
        self.assertIsNone(rows[0]['thread'])
        for bad in ('gdbstub_op_continue', '[1@10.000000] gdbstub_io_command secret\n',
                    '[1@10.000000] gdbstub_op_continue '+('x'*512)):
            path.write_text(bad)
            with self.assertRaises(ValueError):diagnostic.continuation_records(path)
        base=self.folder()
        with self.assertRaises(ValueError):diagnostic.reserve_continuation(base,'measured')
        first=diagnostic.reserve_continuation(base,'plain')
        with self.assertRaises(ValueError):diagnostic.reserve_continuation(base,'plain')
        (first/'summary.json').write_text(json.dumps(dict(completed=False)))
        with self.assertRaises(ValueError):diagnostic.reserve_continuation(base,'measured')
        (first/'summary.json').write_text(json.dumps(dict(completed=True)))
        diagnostic.reserve_continuation(base,'measured')
        with self.assertRaises(ValueError):diagnostic.reserve_continuation(base,'measured')

    def folder(self):
        return Path(tempfile.mkdtemp(prefix='file-transport-host-',dir=ROOT/'build/codex-agent/r83am-file-launch'))

    def test_combined_nested_cost_has_no_double_counting_and_preserves_errors(self):
        clock=[0];rows=[];stages=diagnostic.StageCost(lambda:clock[0],rows.append)
        def leaf():clock[0]+=3;return b'bytes'
        nested=stages.wrap('gdb_read',leaf)
        def outer():
            clock[0]+=2;self.assertEqual(nested(),b'bytes');clock[0]+=5;return False
        self.assertFalse(stages.wrap('translate',outer)())
        def failure():clock[0]+=4;raise ValueError('original')
        with self.assertRaisesRegex(ValueError,'original'):stages.wrap('qmp_save',failure)()
        stages.checkpoint(True)
        value=rows[-1]
        self.assertEqual(value['stages']['translate']['inclusive_ns'],10)
        self.assertEqual(value['stages']['translate']['exclusive_ns'],7)
        self.assertEqual(sum(r['exclusive_ns'] for r in value['stages'].values()),14)
        self.assertEqual(value['stages']['qmp_save']['errors'],1);self.assertEqual(stages.stack,[])
        path=self.folder()/'stages.jsonl';path.write_text(json.dumps(value)+'\n')
        self.assertEqual(diagnostic.stage_costs(path),rows)
        for key,bad in [('calls',True),('elapsed_ns',1),('sequence',2)]:
            broken=copy.deepcopy(value);broken[key]=bad;path.write_text(json.dumps(broken)+'\n')
            with self.assertRaises(ValueError):diagnostic.stage_costs(path)
        broken=copy.deepcopy(value);broken['stages']['translate']['exclusive_ns']=11
        path.write_text(json.dumps(broken)+'\n')
        with self.assertRaises(ValueError):diagnostic.stage_costs(path)

    def test_combined_stage_capacities_deadline_and_recursion(self):
        stage=diagnostic.StageCost(lambda:0,lambda row:None)
        stage.calls=1000000
        with self.assertRaises(AssertionError):stage.wrap('read',lambda:None)()
        stage=diagnostic.StageCost(lambda:0,lambda row:None)
        for n in range(16):stage.wrap(str(n),lambda:None)()
        with self.assertRaises(AssertionError):stage.wrap('overflow',lambda:None)()
        stage=diagnostic.StageCost(lambda:0,lambda row:None)
        recurse=stage.wrap('nested',lambda:recurse())
        with self.assertRaises(AssertionError):recurse()
        self.assertEqual(stage.stack,[])
        stage.records=128
        with self.assertRaises(AssertionError):stage.checkpoint(True)
        now=[0];stage=diagnostic.StageCost(lambda:now[0],lambda row:None)
        now[0]=24000000000
        with self.assertRaises(AssertionError):stage.checkpoint(True)

    def test_combined_observer_reuses_all_assertions_and_only_host_wrappers(self):
        original='set logging enabled on\npython\n'+diagnostic.launch.observer_body()+'\nend\ncontinue\n'
        code=diagnostic.combined_observer(original,Path('build/codex-agent/combined'))
        self.assertEqual(code.count('Hook('),original.count('Hook('))
        self.assertEqual(code.count('write_memory'),original.count('write_memory'))
        for line in original.splitlines():
            if line.strip().startswith('assert '):self.assertIn(line,code)
        self.assertIn('binary.QMP.request=stages.wrap',code)
        self.assertIn("timeline.sample=stages.wrap('snapshot'",code)
        ast.parse(code.split('python\n',1)[1].removesuffix('\nend\ncontinue\n'))
        self.assertEqual(code.count('set $'),original.count('set $')) # Existing OOM injection only.
        for banned in ('Qqemu.sstep','-icount','-rtc'):self.assertNotIn(banned,code)

    def test_combined_actual_binding_observes_original_read_and_qmp_paths(self):
        import types
        folder=self.folder();clock=[0];trace=[]
        def now():clock[0]+=100;return clock[0]
        class QMP:
            def __init__(self,*args):self.request('capabilities',{})
            def request(self,*args):trace.append('request');return {}
            def stopped(self):self.request('status',{})
            def save(self,*args):self.request('save',{})
            def close(self):trace.append('close')
        class Reader:
            def read(self,a,n):
                if n<32768:return bytes(n)
                client=QMP();client.stopped();client.save();client.close();return bytes(n)
        module=types.SimpleNamespace(QMP=QMP,Reader=Reader,translate=lambda *a:42)
        timeline=types.SimpleNamespace(sample=lambda:None)
        class Hook:
            fn=staticmethod(lambda:None)
            def stop(self):return False
        class ReleaseEnd:
            def stop(self):return False
        env=dict(COMBINED_SCRIPTS=str(ROOT/'scripts'),COMBINED_COST=str(folder/'cost.jsonl'),
                 COMBINED_STAGE=str(folder/'stages.jsonl'),json=json,time=types.SimpleNamespace(perf_counter_ns=now),
                 Cost=diagnostic.Cost,StageCost=diagnostic.StageCost,mem=lambda a,n:bytes(n),reg=lambda n:42,
                 timeline=timeline,timeline_flush=lambda:None,Hook=Hook,ReleaseEnd=ReleaseEnd)
        with patch.dict(sys.modules,{'qemu_binary_memory':module}):exec(diagnostic.COMBINED_BINDING,env)
        self.assertFalse(Hook().stop());self.assertEqual(Reader().read(1,32768),bytes(32768))
        self.assertEqual(Reader().read(1,8),bytes(8));self.assertEqual(trace,['request','request','request','close'])
        env['combined_flush']()
        final=diagnostic.stage_costs(folder/'stages.jsonl')[-1]
        self.assertEqual(final['stages']['binary_read']['calls'],1)
        self.assertEqual(final['stages']['qmp_request']['calls'],3)

    def test_combined_reservation_is_ordered_distinct_and_once_only(self):
        base=self.folder()
        with self.assertRaises(ValueError):diagnostic.reserve_combined(base,'gdb')
        first=diagnostic.reserve_combined(base,'binary')
        with self.assertRaises(ValueError):diagnostic.reserve_combined(base,'binary')
        with self.assertRaises(ValueError):diagnostic.reserve_combined(base,'gdb')
        (first/'summary.json').write_text(json.dumps(dict(completed=True)))
        diagnostic.reserve_combined(base,'gdb')
        for kind in ('binary','gdb','other'):
            with self.assertRaises(ValueError):diagnostic.reserve_combined(base,kind)

    def test_actual_timeline_wrapper_preserves_callbacks_and_measures_intervals(self):
        rows=[];clock=[0];called=[];snapshots=[]
        def now():return clock[0]
        def sample():snapshots.append(1);return {'scheduler_mode':'00'}
        recorder=diagnostic.Timeline(now,rows.append,sample)
        class Hook:
            def __init__(self,fn):self.fn=fn
            def stop(self):called.append(self.fn.__name__);clock[0]+=200;return self.fn()
        def work():return False
        def broken():raise ValueError('original callback')
        wrapped=recorder.wrap_stop(Hook.stop)
        clock[0]=100;recorder.notify('cont');self.assertFalse(wrapped(Hook(work)))
        clock[0]+=1000
        with self.assertRaisesRegex(ValueError,'original callback'):wrapped(Hook(broken))
        self.assertIsNone(recorder.active);self.assertEqual(called,['work','broken']);self.assertEqual(len(snapshots),1)
        folder=self.folder();path=folder/'timeline.jsonl';path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        result=diagnostic.timeline_records(path)
        self.assertEqual(result['callbacks'],2);self.assertEqual(result['completed_callbacks'],2)
        self.assertEqual(result['callback_ns'],400);self.assertEqual(result['gap_ns'],1000)
        self.assertEqual(result['notifications'],{'cont':1,'stop':0});self.assertFalse(result['active'])
        for at,key,value in [(0,'seq',2),(1,'call',2),(3,'name','wrong'),(3,'ns',0),(2,'state',{'arbitrary':'00'})]:
            bad=copy.deepcopy(rows);bad[at][key]=value;path.write_text(''.join(json.dumps(r)+'\n' for r in bad))
            with self.assertRaises(ValueError):diagnostic.timeline_records(path)
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows[:-1]))
        self.assertEqual(diagnostic.timeline_records(path)['active'],'broken')
        recorder.callbacks=4096
        with self.assertRaises(AssertionError):wrapped(Hook(work))
        recorder.events=8192
        with self.assertRaises(AssertionError):recorder.notify('cont')

    def test_actual_clock_snapshot_has_fixed_reads_and_exact_lengths(self):
        names=list(diagnostic.TIMELINE_RANGES);symbols={name:0x1000+i*4096 for i,name in enumerate(dict.fromkeys(v[0] for v in diagnostic.TIMELINE_RANGES.values()))};calls=[]
        def read(address,size):
            calls.append((address,size));return b'\x08' if address==symbols['scheduler_mode'] else bytes(size)
        value=diagnostic.timeline_sample(symbols,read)
        self.assertEqual(set(value),set(names));self.assertLessEqual(sum(n for a,n in calls),1280)
        expected=[(symbols[symbol]+offset,size) for symbol,offset,size in diagnostic.TIMELINE_RANGES.values()]
        self.assertEqual(calls,expected)
        with self.assertRaises(AssertionError):diagnostic.timeline_sample(symbols,lambda a,n:bytes(n-1))
        calls.clear();self.assertEqual(diagnostic.timeline_sample(symbols,lambda a,n:bytes(n)),{'scheduler_mode':'00'})
        recorder=diagnostic.Timeline(lambda:0,lambda row:None,lambda:value);recorder.samples=192
        class Hook:
            fn=staticmethod(lambda:None)
        with self.assertRaises(AssertionError):recorder.wrap_stop(lambda hook:False)(Hook())

    def test_actual_timeline_observer_keeps_production_code_and_no_new_traps(self):
        original='set logging enabled on\npython\n'+diagnostic.launch.observer_body()+'\nend\ncontinue\n'
        for kind in ('stops','peer-clock'):
            code=diagnostic.timeline_observer(kind,original,Path('build/codex-agent/timeline'))
            self.assertEqual(code.count('Hook('),original.count('Hook('))
            self.assertEqual(code.count('write_memory'),original.count('write_memory'))
            self.assertIn('gdb.events.cont.connect',code);self.assertIn('gdb.events.stop.connect',code)
            self.assertNotIn('Qqemu.sstep',code)
            for line in original.splitlines():
                if line.strip().startswith('assert '):self.assertIn(line,code)
            ast.parse(code.split('python\n',1)[1].removesuffix('\nend\ncontinue\n'))
        with self.assertRaises(ValueError):diagnostic.timeline_observer('retry',original,Path('.'))

    def test_actual_timeline_reservation_enforces_order_no_retries_and_failure_stop(self):
        folder=self.folder()
        with self.assertRaises(ValueError):diagnostic.reserve_timeline(folder,'peer-clock')
        first=diagnostic.reserve_timeline(folder,'stops')
        with self.assertRaises(ValueError):diagnostic.reserve_timeline(folder,'stops')
        with self.assertRaises(ValueError):diagnostic.reserve_timeline(folder,'peer-clock')
        (first/'summary.json').write_text(json.dumps({'completed':False}))
        with self.assertRaises(ValueError):diagnostic.reserve_timeline(folder,'peer-clock')
        (first/'summary.json').write_text(json.dumps({'completed':True}))
        diagnostic.reserve_timeline(folder,'peer-clock')
        for kind in ('stops','peer-clock'):
            with self.assertRaises(ValueError):diagnostic.reserve_timeline(folder,kind)

    def test_actual_cost_wrappers_preserve_result_failure_and_accounting(self):
        rows=[];now=[0]
        def clock():now[0]+=100;return now[0]
        cost=diagnostic.Cost(clock,rows.append)
        def read(a,n):now[0]+=400;return bytes([a])*n
        def reg(name):now[0]+=600;return 42
        reader=cost.wrap_read(read);register=cost.wrap_register(reg)
        class Hook:
            def __init__(self,fn):self.fn=fn
            def stop(self):return self.fn()
        def original():
            self.assertEqual(reader(7,9),bytes([7])*9);self.assertEqual(register('rax'),42)
            return False
        stopped=cost.wrap_stop(Hook.stop)
        self.assertFalse(stopped(Hook(original)))
        def broken():raise ValueError('original failure')
        with self.assertRaisesRegex(ValueError,'original failure'):stopped(Hook(broken))
        self.assertIsNone(cost.active);cost.checkpoint(True)
        self.assertEqual((rows[-1]['callbacks'],rows[-1]['reads'],rows[-1]['registers']),(2,1,1))
        folder=self.folder();path=folder/'cost.jsonl'
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        self.assertEqual(diagnostic.costs(path),rows)
        for key,bad in [('bytes',-1),('callbacks',True),('functions',{}),('read_ns',1<<63),('sequence',2)]:
            value=copy.deepcopy(rows[-1]);value[key]=bad;path.write_text(json.dumps(value)+'\n')
            with self.assertRaises(ValueError):diagnostic.costs(path)
        for n in (-1,True,270337):
            before=cost.value['reads']
            with self.assertRaises(AssertionError):reader(0,n)
            self.assertEqual(cost.value['reads'],before)
        cost.records=128
        with self.assertRaises(AssertionError):cost.checkpoint(True)

    def test_observer_profiling_keeps_original_assertions_and_hooks(self):
        original='set logging enabled on\npython\n'+diagnostic.launch.observer_body()+'\nend\ncontinue\n'
        profiled=diagnostic.observer('full-profile',original,Path('build/codex-agent/profile'),{})
        self.assertIn('Hook.stop=cost.wrap_stop(Hook.stop)',profiled)
        for line in original.splitlines():
            if line.strip().startswith('assert '):self.assertIn(line,profiled)
        ast.parse(profiled.split('python\n',1)[1].removesuffix('\nend\ncontinue\n'))
        self.assertEqual(profiled.count('Hook('),original.count('Hook('))
        self.assertEqual(profiled.count('write_memory'),original.count('write_memory'))
        for kind in diagnostic.INITIAL+diagnostic.FOLLOWUP:
            code=diagnostic.observer(kind,original,Path('build/codex-agent/profile'),{})
            if kind.startswith('full'):
                self.assertEqual(code.count('Hook('),original.count('Hook('))
                for line in original.splitlines():
                    if line.strip().startswith('assert '):self.assertIn(line,code)
        with self.assertRaises(ValueError):diagnostic.observer('unbounded',original,Path('.'),{})

    def test_stop_reason_is_diagnostic_not_acceptance(self):
        classify=transport.capture_stop_reason
        self.assertEqual(classify('',False,None,0,True),'deadline')
        self.assertEqual(classify(transport.process.SUCCESS,False,None,0,False),'success_marker')
        self.assertEqual(classify(transport.FAILURES[0],False,None,None,False),'failure_marker')
        self.assertEqual(classify(transport.FAILURES[0],True,None,None,False),'capture_error')
        self.assertEqual(classify('',True,None,0,False),'debugger_exit')
        self.assertEqual(classify('',False,0,None,False),'vm_exit')
        m={'progress':[]};serial=''
        for n in range(16):
            serial+='REIST_X86_64_PROCESS_REAP_OK\n';transport.capture_progress(m,serial,n)
            transport.capture_progress(m,serial,n+.1)
        self.assertEqual(len(m['progress']),16);self.assertEqual(m['progress'][-1]['reaps'],16)
        m['progress']=[dict(m['progress'][-1]) for _ in range(64)]
        with self.assertRaises(ValueError):transport.capture_progress(m,'',0)

    def test_actual_capture_timeout_records_active_and_cleanup_separately(self):
        class Process:
            def __init__(self,pid):self.pid=pid;self.returncode=None;self.stdin=io.BytesIO();self.stdout=io.BytesIO()
            def poll(self):return self.returncode
            def wait(self,timeout):self.returncode=1;return 1
        folder=self.folder();(folder/'frame-trace.log').write_text('')
        vm,debug=Process(123),Process(124);counter=[0];terminated=[]
        def monotonic():counter[0]+=5;return counter[0]
        def terminate(p):p.returncode=1;terminated.append(p)
        with patch.object(transport.subprocess,'Popen',side_effect=[vm,debug]),patch.object(transport,'resolve_qemu',return_value=Path('qemu.exe')),patch.object(transport.time,'monotonic',side_effect=monotonic),patch.object(transport,'process_cpu_ns',return_value={'kernel_ns':10,'user_ns':20}),patch.object(transport,'terminate_bounded',side_effect=terminate):
            with self.assertRaisesRegex(ValueError,'program capture/detach failure'):
                transport._capture(ROOT/'build/a.elf',folder,'code',4096,diagnostic_metrics=True)
        metrics=json.loads((folder/'capture-metrics.json').read_text())
        self.assertEqual(metrics['stop_reason'],'deadline');self.assertTrue(metrics['failed'])
        self.assertIn('observe_seconds',metrics);self.assertIn('cleanup_seconds',metrics)
        self.assertEqual(metrics['cpu'],metrics['debugger_cpu']);self.assertIn(vm,terminated)
        self.assertTrue(vm.stdout.closed and vm.stdin.closed)


if __name__=='__main__':unittest.main()
