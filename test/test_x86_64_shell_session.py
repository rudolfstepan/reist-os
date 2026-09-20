"""Execute the new normal-shell/session boundary; retain every test attempt."""
from pathlib import Path
import copy,inspect,json,os,subprocess,sys,textwrap,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class ShellSessionTests(unittest.TestCase):
    def test_persistent_target_only_changes_insertion_policy(self):
        import run_qemu_x86_64_shell_session as session
        body=session.return_target_observer(session.stepped_probe_observer(
            session.command_probe_observer(session.hybrid_probe_observer(session.observer_body()))))
        code='set breakpoint always-inserted off\npython\n'+body+'\nend\ncontinue\n'
        result=session.persistent_target_observer(code)
        self.assertEqual(result,'set breakpoint always-inserted on\n'+code.split('\n',1)[1])
        self.assertIn("target_hook.hit_count==1,'actual single RET target hit'",result)
        self.assertIn('target_hook.delete()',result)
        with self.assertRaises(ValueError):session.persistent_target_observer(result)
        with self.assertRaises(ValueError):session.persistent_target_observer('set breakpoint always-inserted off\n')

    def test_return_target_requires_actual_hit_and_cleanup(self):
        import types,struct
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        base=session.stepped_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        code=session.return_target_observer(base)
        for name in ('syscall','complete','resume','command_probe_stop','command_probe_observe'):
            self.assertEqual(source_node(base,name),source_node(code,name))
        self.assertNotIn("gdb.execute('stepi'",code)
        for failure in (None,'create','location','continue','no_hit','two_hits','pc','sp','register','delete'):
            with self.subTest(failure=failure):
                events=[];lines=[];targets=[]
                class Hook:
                    name='native_session_probe_request_site64';enabled=True
                    def is_valid(self):return True
                hook=Hook();dispatch=types.SimpleNamespace(pending=[hook],running=False,failed=False)
                registers=dict(rip=1000,rsp=2000,eflags=2)
                for n in ('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15','cr3'):
                    registers[n]=100+len(n)
                class Target:
                    enabled=True;hit_count=0;valid=True
                    def __init__(self,spec,**kwargs):
                        events.append('create')
                        self.locations=[types.SimpleNamespace(address=3001 if failure=='location' else 3000)]
                        if failure=='create':raise RuntimeError('creation failed')
                        targets.append(self)
                    def is_valid(self):return self.valid
                    def delete(self):
                        events.append('delete');self.valid=False
                        if failure=='delete':raise RuntimeError('delete failed')
                def construct(spec,**kwargs):
                    self.assertEqual(spec,'*0xbb8');self.assertEqual(kwargs,dict(type=7,internal=True))
                    self.assertFalse(hook.enabled)
                    return Target(spec,**kwargs)
                def execute(command,**kwargs):
                    events.append(command)
                    if command=='maintenance packet qqemu.sstep':return 'sending: qqemu.sstep\nreceived: "0x7"\n'
                    if command=='continue':
                        self.assertFalse(hook.enabled);self.assertEqual(dispatch.pending,[])
                        if failure=='continue':raise RuntimeError('resume failed')
                        targets[0].hit_count=0 if failure=='no_hit' else 2 if failure=='two_hits' else 1
                        registers.update(rip=1000 if failure=='pc' else 3000,rsp=2000 if failure=='sp' else 2008)
                        if failure=='register':registers['rax']+=1
                        return 'target stopped\n'
                    self.assertEqual(command,'quit 71')
                def original_dispatch():events.append('callback');dispatch.pending.clear()
                def raw(address,size):
                    if (address,size)==(1000,1):return b'\xc3'
                    self.assertEqual((address,size),(2000,8));return struct.pack('<Q',3000)
                ns=dict(gdb=types.SimpleNamespace(execute=execute,write=lines.append,Breakpoint=construct,
                        BP_HARDWARE_BREAKPOINT=7,selected_inferior=lambda:types.SimpleNamespace(read_memory=raw)),
                    reg=lambda n:registers[n],S={hook.name:1000},struct=struct,json=json,
                    ColdHook=Hook,service_stops=dispatch,hybrid_dispatch=original_dispatch,
                    cold_step_count=0,cold_step_mode=None,emit=lambda *a,**kw:lines.append(kw))
                exec(source_node(code,'stepped_probe_dispatch'),ns)
                if failure is None:
                    ns['stepped_probe_dispatch']()
                    self.assertTrue(any(isinstance(l,str) and l.startswith('COLD_STEP_V1 ') for l in lines))
                else:
                    with self.assertRaises((AssertionError,RuntimeError)):ns['stepped_probe_dispatch']()
                    self.assertEqual(events[-1],'quit 71')
                    self.assertFalse(any(isinstance(l,str) and l.startswith('COLD_STEP_V1 ') for l in lines))
                self.assertEqual(events.count('callback'),1)
                self.assertLessEqual(events.count('continue'),1)
                self.assertNotIn('stepi',events)
                self.assertTrue(hook.enabled)
                if targets:self.assertFalse(targets[0].valid);self.assertEqual(events.count('delete'),1)

    def test_probe_exit_capture_is_filtered_and_bounded(self):
        import io
        import run_qemu_x86_64_shell_session as session
        folder=ROOT/'build/codex-agent/r83ay-shell-session/probe-exit-host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        body=session.command_probe_observer(session.hybrid_probe_observer(session.observer_body()))
        code=session.stepped_probe_observer('python\n'+body+'\nend\ncontinue\n')
        ns=session.probe_exit_capture_namespace()
        self.assertIs(ns['ContinuationTrace'],session.boot.ContinuationTrace)
        ns['resolve_qemu']=lambda _:Path('qemu-not-launched.exe')
        commands=[]
        def no_vm(command,**kwargs):
            commands.append(command)
            self.assertIs(kwargs['stderr'],subprocess.PIPE)
            raise RuntimeError('host-only command proof')
        with patch.object(session.boot.subprocess,'Popen',side_effect=no_vm):
            with self.assertRaisesRegex(RuntimeError,'host-only command proof'):
                ns['_capture_run'](folder/'not-built.elf',folder,code,4096,('-drive','host-only'),
                    binary_memory='equivalence',service_pio_budget=True,trace_continuation=True,
                    console_input=session.input_plan(2))
        self.assertEqual(len(commands),1)
        command=commands[0]
        self.assertEqual(command[-10:],['-msg','timestamp=on','-d','exec','-dfilter','0xffffffff80110000+3',
            '-trace','enable=gdbstub_op_stepping','-trace','enable=gdbstub_hit_break'])
        self.assertEqual(command[command.index('-machine')+1],'pc,accel=tcg')
        script=(folder/'observe.gdb').read_text()
        self.assertLess(script.index('binary_reader=BinaryReader('),script.index('def stepped_probe_loop():'))
        self.assertEqual(script.count('def stepped_probe_dispatch():'),1)
        self.assertIn("'actual one-RET progress'",script)
        calls=[];ns['_capture']=lambda *a,**kw:calls.append(kw)
        class Fixture:
            def arguments(self,folder):return ()
            def verify(self,stage):pass
        with patch('run_qemu_x86_64_pio.Fixture',Fixture):
            ns['capture'](None,None,None,4096,media=Fixture(),service_pio_budget=True,
                          console_input=session.input_plan(2))
        self.assertTrue(calls[0]['trace_continuation'])
        with self.assertRaisesRegex(ValueError,'diagnostic trace owns'):
            ns['capture'](None,None,None,4096,trace_continuation=False)
        for initial,chunk in ((8*1024*1024,b'x'),(0,b'x'*4096)):
            sink=ns['ContinuationTrace']();sink.bytes=initial;output=io.BytesIO()
            sink.run(io.BytesIO(chunk),output)
            if initial:
                with self.assertRaisesRegex(ValueError,'capacity'):sink.check()
                self.assertEqual(output.getvalue(),b'')
            else:
                sink.check();self.assertEqual(output.getvalue(),chunk)

    def test_compact_probe_step_raw_replay(self):
        import run_qemu_x86_64_shell_session as session
        base=0xffffffff80100000
        symbols={'native_session_probe_'+name+'_site64':base+100+i for i,name in enumerate(('request','denied','return'))}
        symbols.update(process_run_resume64=base+900,**{'process_run_syscall64.denied':base+800})
        rows=[dict(step=i+1,site=i,pc=base+100+i,target=base+700+i*100,sp=base+4000,after_sp=base+4008) for i in range(3)]
        rows[1]['target']=base+805;rows[2]['target']=base+905
        def encode(records,ending='3'):
            return ''.join('COLD_STEP_V1 '+json.dumps(r,separators=(',',':'))+'\n' for r in records)+'COLD_STEP_END_V1 '+ending+'\n'
        self.assertEqual(session.validate_probe_steps(encode(rows),symbols),3)
        variants=[encode(rows[:-1]),encode(rows+rows[:1]),encode(rows[::-1]),encode(rows,'2'),
                  encode(rows).replace('COLD_STEP_END_V1 3\n',''),encode(rows)+'COLD_STEP_END_V1 3\n',
                  encode(rows)+'COLD_STEP_V1 '+json.dumps(rows[-1])+'\n']
        for key,value in (('step',True),('site',3),('pc',base),('sp',base+4001),('after_sp',base+4016),('target',base+5)):
            bad=copy.deepcopy(rows);bad[2][key]=value;variants.append(encode(bad))
        for trace in variants:
            with self.subTest(trace=trace[-120:]):
                with self.assertRaises(ValueError):session.validate_probe_steps(trace,symbols)
        # No dependency on ignored historical receipts in the reusable host test.
        large=[dict(rows[n%3],step=n+1) for n in range(8192)]
        self.assertEqual(session.validate_probe_steps(encode(large,'8192'),symbols),8192)
        with self.assertRaises(ValueError):session.validate_probe_steps(encode(large+[dict(rows[0],step=8193)],'8193'),symbols)

    def test_explicit_step_real_binary_capture_order(self):
        import run_qemu_x86_64_shell_session as session
        folder=ROOT/'build/codex-agent/r83ay-shell-session/capture-host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        body=session.ticket_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        original='python\n'+body+'\nend\ncontinue\n'
        code=session.stepped_probe_observer(original)
        ns=session.stepped_capture_namespace()
        def no_vm(_):raise RuntimeError('stop before VM launch')
        ns['resolve_qemu']=no_vm
        with patch.object(session.boot.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'stop before VM launch'):
                ns['_capture_run'](folder/'not-built.elf',folder,code,4096,('-drive','host-only'),
                    binary_memory='equivalence',service_pio_budget=True,console_input=session.input_plan(13))
            spawn.assert_not_called()
        script=(folder/'observe.gdb').read_text()
        self.assertLess(script.index('binary_reader=BinaryReader('),script.index('def stepped_probe_loop():'))
        self.assertIn('mem=binary_reader.read',script)
        self.assertIn('Hook.stop=binary_reader.wrap_stop(Hook.stop)',script)
        self.assertTrue(script.endswith('stepped_probe_loop()\nend\n'))
        self.assertEqual(script.count('def stepped_probe_dispatch():'),1)
        self.assertEqual(script.count('def stepped_probe_loop():'),1)
        self.assertNotIn('session_step_loop',session.capture_namespace())
        self.assertEqual(session.step_loop_tail(code),session.stepped_loop_observer(original))

    def test_explicit_probe_outer_loop_requires_one_step(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        body=session.ticket_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        original='python\n'+body+'\nend\ncontinue\n'
        stepped=session.stepped_probe_observer(original)
        code=session.stepped_loop_observer(original)
        self.assertTrue(code.startswith(stepped[:-len('continue\n')]))
        self.assertTrue(code.endswith('stepped_probe_loop()\nend\n'))
        loop=code.split('\nend\npython\n')[-1].rsplit('\nstepped_probe_loop()',1)[0]
        for delta,state in ((0,'idle'),(2,'idle'),(1,'pending'),(1,'running'),(1,'failed'),(1,'idle')):
            with self.subTest(delta=delta,state=state):
                dispatch=types.SimpleNamespace(pending=[],running=False,failed=False)
                events=[];errors=[]
                ns=dict(cold_step_count=0,service_stops=dispatch,emit=lambda *a,**kw:errors.append(kw))
                def execute(command):
                    events.append(command)
                    if command=='continue':
                        ns['cold_step_count']+=delta
                        if state=='pending':dispatch.pending.append(object())
                        if state=='running':dispatch.running=True
                        if state=='failed':dispatch.failed=True
                def bounded_range(limit):
                    self.assertEqual(limit,8192)
                    return range(2)
                ns.update(gdb=types.SimpleNamespace(execute=execute),range=bounded_range)
                exec(loop,ns)
                with self.assertRaises(AssertionError):ns['stepped_probe_loop']()
                self.assertEqual(events.count('continue'),2 if (delta,state)==(1,'idle') else 1)
                self.assertEqual(events[-1],'quit 71');self.assertEqual(len(errors),1)
        with self.assertRaises(ValueError):session.stepped_loop_observer(body)

    def test_explicit_probe_step_progress_and_failure(self):
        import types,struct
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        original=session.ticket_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        code=session.stepped_probe_observer(original)
        compile(code,'<explicit probe step>','exec')
        for name in ('syscall','complete','resume','command_probe_stop','command_probe_observe'):
            self.assertEqual(source_node(original,name),source_node(code,name))
        self.assertIn('python stepped_probe_dispatch()',code)
        self.assertNotIn('python stepped_probe_dispatch()',original)
        class Hook:
            name='native_session_probe_request_site64';enabled=True
            def is_valid(self):return True
        for failure in (None,'duplicate','busy','capacity','step_mode','opcode','guard','step','pc','sp','register','flags','cr3','reentrant'):
            with self.subTest(failure=failure):
                hook=Hook();events=[];lines=[];steps=[]
                dispatch=types.SimpleNamespace(pending=[hook],running=False,failed=False)
                registers={n:100+n.__len__() for n in
                    ('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15','cr3')}
                registers.update(rip=1000,rsp=2000,eflags=2)
                initial=dict(registers)
                def raw(address,size):
                    if (address,size)==(1000,1):return b'\x90' if failure=='opcode' else b'\xc3'
                    self.assertEqual((address,size),(2000,8));return struct.pack('<Q',3000)
                def execute(command,**kwargs):
                    events.append(command)
                    if command=='maintenance packet qqemu.sstep':
                        return 'sending: qqemu.sstep\nreceived: "'+('0x5' if failure=='step_mode' else '0x7')+'"\n'
                    if command=='stepi':
                        self.assertFalse(hook.enabled);self.assertEqual(dispatch.pending,[])
                        steps.append(1)
                        if failure=='step':raise RuntimeError('target step failure')
                        registers.update(rip=3000,rsp=2008)
                        if failure=='pc':registers['rip']=1000
                        if failure=='sp':registers['rsp']=2000
                        if failure=='register':registers['rax']+=1
                        if failure=='flags':registers['eflags']=514
                        if failure=='cr3':registers['cr3']+=4096
                        if failure=='reentrant':dispatch.pending.append(hook)
                        return '0x0000000000000bb8 in ?? ()\n'
                    self.assertEqual(command,'quit 71')
                def original_dispatch():
                    events.append('callback')
                    if failure=='guard':raise AssertionError('original pending guard')
                    dispatch.pending.clear()
                if failure=='duplicate':dispatch.pending.append(hook)
                if failure=='busy':dispatch.running=True
                ns=dict(gdb=types.SimpleNamespace(execute=execute,write=lines.append,
                        selected_inferior=lambda:types.SimpleNamespace(read_memory=raw)),
                    reg=lambda n:registers[n],S={hook.name:1000},struct=struct,json=json,
                    ColdHook=Hook,service_stops=dispatch,hybrid_dispatch=original_dispatch,
                    cold_step_count=8192 if failure=='capacity' else 0,cold_step_mode=None,
                    emit=lambda *a,**kw:lines.append(kw))
                exec(source_node(code,'stepped_probe_dispatch'),ns)
                if failure is None:
                    ns['stepped_probe_dispatch']()
                    self.assertEqual(registers,dict(initial,rip=3000,rsp=2008))
                    self.assertEqual(events.count('callback'),1);self.assertEqual(steps,[1])
                    self.assertEqual(ns['cold_step_count'],1)
                    self.assertTrue(any(isinstance(l,str) and l.startswith('COLD_STEP_V1 ') for l in lines))
                else:
                    with self.assertRaises((AssertionError,RuntimeError)):ns['stepped_probe_dispatch']()
                    self.assertEqual(events[-1],'quit 71')
                    self.assertLessEqual(events.count('callback'),1);self.assertLessEqual(len(steps),1)
                    self.assertFalse(any(isinstance(l,str) and l.startswith('COLD_STEP_V1 ') for l in lines))
                self.assertTrue(hook.enabled)

    def test_transient_breakpoint_diagnostic_only(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        body=session.ticket_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        original='set breakpoint always-inserted on\npython\n'+body+'\nend\ncontinue\n'
        result=session.transient_probe_observer(original)
        self.assertEqual(result,'set breakpoint always-inserted off\n'+original.split('\n',1)[1])
        self.assertIn("set breakpoint always-inserted on",inspect.getsource(session.observer))
        self.assertEqual(result.split('\n',1)[1],original.split('\n',1)[1])
        with self.assertRaises(ValueError):session.transient_probe_observer(result)
        with self.assertRaises(ValueError):session.transient_probe_observer(original+original)

    def test_read_ticket_observer_preserves_pending_guard(self):
        import types,struct
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        before=session.command_probe_observer(session.hybrid_probe_observer(session.observer_body()))
        code=session.ticket_probe_observer(before);compile(code,'<ticket observer>','exec')
        for name in ('complete','resume','command_probe_stop'):
            self.assertEqual(source_node(before,name),source_node(code,name))
        symbols={n:n for n in ('scheduler_current_slot','syscall_rax','scheduler_last_tick',
            'syscall_rdi','syscall_rsi','syscall_rdx','syscall_r10','syscall_r8','syscall_r9',
            'native_terminal_state','native_session_read_tickets')}
        values=dict(syscall_rax=15,syscall_rsi=500,syscall_rdx=1,scheduler_last_tick=573)
        ticket=[399,398];reads=[];rows=[];pending={}
        def mem(address,size):
            reads.append((address,size))
            return struct.pack('<2Q',*ticket) if address=='native_session_read_tickets' else bytes(size)
        ns=dict(S=symbols,CONFIG=dict(case=3),struct=struct,mode=lambda:8,d=lambda _:0,
            task=lambda _:[2,10],q=lambda a:values.get(a,0),starts={10:dict(live=True)},
            pending=pending,mem=mem,user=lambda t,p,n:bytes(n),runs=1,
            emit=lambda kind,**r:rows.append(dict(kind=kind,**r)))
        exec(source_node(code,'syscall'),ns);ns['syscall']()
        self.assertEqual(pending[10]['read_ticket'],[399,398]);self.assertEqual(rows[-1]['read_ticket'],[399,398])
        count=len(reads)
        for current in ([399,398],[399,399],[400,399]):
            ticket[:]=current
            with self.assertRaisesRegex(AssertionError,'pending=15'):ns['syscall']()
            self.assertEqual(len(reads),count) # no repaired/deduplicated invocation
        for invalid in ([0,0],[8193,8192],[1,8193]):
            pending.clear();ticket[:]=invalid
            with self.assertRaises(AssertionError):ns['syscall']()
        self.assertIn("data['read_ticket']=list(struct.unpack('<2Q',raw(S['native_session_read_tickets'],16)))",
                      source_node(code,'failure_only_snapshot'))

    def test_failure_only_probe_has_no_healthy_reads(self):
        import types,struct
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        original=session.command_probe_observer(session.hybrid_probe_observer(session.observer_body()))
        code=session.failure_only_probe_observer(original)
        for name in ('syscall','complete','resume','command_probe_stop'):
            self.assertEqual(source_node(original,name),source_node(code,name))
        reads=[];lines=[];exits=[];regs=dict(rip=100,rsp=200,rax=15,rcx=300,eflags=0)
        t=[0]*128;t[:3]=[2,10,0x100000000]
        symbols=dict(scheduler_current_slot=1,scheduler_tasks=2,scheduler_last_tick=3,
                     native_session_probe_pending=4,**{'syscall_'+n:5+i for i,n in enumerate(('rax','rcx','rdi','rsi','rdx'))})
        memory={1:bytes(4),2:struct.pack('<128Q',*t),3:struct.pack('<Q',678),4:b'\x01'+bytes(7)}
        memory.update({5+i:struct.pack('<Q',v) for i,v in enumerate((15,300,0,400,1))})
        def read(address,size):reads.append((address,size));return memory[address][:size]
        ns=dict(S=symbols,struct=struct,json=json,callbacks=0,reg=lambda n:regs[n],
            gdb=types.SimpleNamespace(selected_inferior=lambda:types.SimpleNamespace(read_memory=read),
                write=lines.append,execute=exits.append),
            service_stops=types.SimpleNamespace(batches=99),pending={10:dict(gen=10,op=15,before='00')},
            resume_hook=types.SimpleNamespace(number=2,enabled=True,hit_count=87),
            emit=lambda *a,**kw:lines.append(kw),static_failure_context=lambda e,h:str(e))
        exec(source_node(code,'failure_only_snapshot')+'\n'+source_node(code,'command_probe_observe'),ns)
        hook=types.SimpleNamespace(name='request',number=1,enabled=True,hit_count=100,read_only=lambda:None)
        self.assertFalse(ns['command_probe_observe'](hook));self.assertEqual((reads,lines,exits),([],[],[]))
        def fail():raise AssertionError('original pending guard')
        hook.read_only=fail
        with self.assertRaisesRegex(AssertionError,'original pending guard'):ns['command_probe_observe'](hook)
        self.assertLessEqual(sum(n for _,n in reads),2048);self.assertEqual(exits,['quit 71'])
        row=json.loads(lines[0].split(' ',1)[1]);self.assertEqual(row['kernel_pending'],'01'+'00'*7)
        self.assertEqual(row['task'][:3],[2,10,0x100000000]);self.assertEqual(row['pending']['op'],15)
        self.assertEqual(row['request_hook'],[1,True,100]);self.assertEqual(row['return_hook'],[2,True,87])
        memory[1]=b'';lines.clear()
        with self.assertRaisesRegex(AssertionError,'original pending guard'):ns['command_probe_observe'](hook)
        self.assertTrue(lines[0].startswith('PENDING_FAILURE_UNAVAILABLE '));self.assertEqual(exits,['quit 71']*2)

    def test_oom_pause_raw_proof(self):
        import run_qemu_x86_64_shell_session as session
        events=[dict(kind='start',gen=3,slot=2,run=1),dict(kind='start',gen=5,slot=2,run=1),
                dict(kind='call',gen=1,op=41),
                dict(kind='io',gen=5,op=15,profile_denied=True,result=-13),
                dict(kind='io',gen=5,op=20,profile_denied=True,result=-13),
                dict(kind='cpu_charge',gen=5,now=78),
                dict(kind='return',gen=1,slot=0,run=1,op=41,args=[100,0,0,0,0,0],
                     result=0,entered=770,now=870),dict(kind='oom')]
        session.validate_oom_pause(events,17)
        for at,key,value in ((6,'args',[99,0,0,0,0,0]),(6,'result',-5),
                             (6,'now',869),(6,'now',1770),(6,'slot',1),(6,'run',2),
                             (4,'result',0),(4,'op',15),(5,'gen',1)):
            bad=copy.deepcopy(events);bad[at][key]=value
            with self.assertRaises(ValueError):session.validate_oom_pause(bad,17)
        for bad in (events[:-1],events[:4]+events[5:],events[:6]+[events[7],events[6]],
                    events[:6]+[events[6],events[6],events[7]]):
            with self.assertRaises(ValueError):session.validate_oom_pause(bad,17)
        for case in range(17):
            session.validate_oom_pause([],case)
            with self.assertRaises(ValueError):session.validate_oom_pause(events,case)

    def test_oom_sleep_observer_is_selected_only(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        import struct
        source=source_node(session.OBSERVER,'syscall')
        for case,run,slot,duration,starts,expected in (
            (17,0,0,100,2,True),(0,0,0,100,2,False),(17,1,0,100,2,False),
            (17,0,1,100,2,False),(17,0,0,99,2,False),(17,0,0,100,1,False),
            (17,0,0,100,3,False)):
            rows=[];reads=[];pending={};hook=type('Hook',(),{'enabled':False})()
            symbols={name:name for name in ('scheduler_current_slot','syscall_rax',
                'syscall_rdi','syscall_rsi','syscall_rdx','syscall_r10','syscall_r8','syscall_r9',
                'scheduler_last_tick','native_terminal_state')}
            values=dict(syscall_rax=41,syscall_rdi=duration,scheduler_last_tick=77)
            ns=dict(CONFIG=dict(case=case,service=1000),runs=run,S=symbols,struct=struct,
                mode=lambda:8,d=lambda _:slot,task=lambda _:[2,1],q=lambda a:values.get(a,0),
                starts={1:dict(live=True)},pending=pending,resume_hook=hook,
                user=lambda t,p,n:reads.append((p,n)) or struct.pack('<Q',starts),
                mem=lambda a,n:bytes(n),emit=lambda kind,**kw:rows.append(dict(kind=kind,**kw)))
            exec(source,ns);ns['syscall']()
            self.assertEqual(bool(rows),expected);self.assertEqual(bool(pending),expected)
            self.assertEqual(hook.enabled,expected)
            if expected:self.assertEqual(rows[0]['args'],[100,0,0,0,0,0])

    def test_pending_watch_collects_then_reads_without_mutation(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        from run_qemu_x86_64_service_cpu import StopDispatcher
        before=session.audit_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        code=session.watch_pending_observer(before)
        for name in ('syscall','resume','complete'):
            self.assertEqual(source_node(before,name),source_node(code,name))
        self.assertNotIn("    pending_watch=PendingWatch()\n    emit('boot',zero=1)",code)
        self.assertIn('def watched_probe_arm():',code)
        calls=[]
        class Breakpoint:
            def __init__(self,expression,**kwargs):
                calls.append((expression,kwargs));self.type=kwargs['type']
            def is_valid(self):return True
        ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_WATCHPOINT=2,
                BP_HARDWARE_WATCHPOINT=3,WP_WRITE=4),S=dict(native_session_probe_pending=0x1000),
                callbacks=0,pending_watch_audit=types.SimpleNamespace(record=lambda h:calls.append('read')))
        ns['service_stops']=StopDispatcher(ns)
        exec(source_node(code,'PendingWatch'),ns);hook=ns['PendingWatch']()
        self.assertEqual(calls,[('*(unsigned char*)0x1000',dict(type=2,wp_class=4,internal=True))])
        self.assertTrue(hook.stop());self.assertEqual(len(calls),1)
        hook.type=3;ns['service_stops'].drain();self.assertEqual(calls[-1],'read')
        self.assertEqual(ns['callbacks'],1)
        hook.type=2;self.assertTrue(hook.stop())
        with self.assertRaisesRegex(AssertionError,'hardware pending watch'):
            ns['service_stops'].drain()
        self.assertEqual(calls.count('read'),1)

    def test_pending_watch_arms_only_after_second_history(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        code=session.watch_pending_observer(session.audit_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body()))))
        calls=[];watch=object()
        ns=dict(original_probe_audit_arm=lambda:calls.append('arm-context'),
                probe_debug_armed=False,pending_watch=None,
                pending_watch_audit=type('Audit',(),dict(total=0))(),
                PendingWatch=lambda:calls.append('arm') or watch,
                S=dict(native_session_probe_pending=4096),mem=lambda a,n:calls.append((a,n)) or bytes(n))
        exec(source_node(code,'watched_probe_arm'),ns)
        with self.assertRaisesRegex(AssertionError,'late audit arm'):
            ns['watched_probe_arm']()
        self.assertFalse(calls);self.assertIsNone(ns['pending_watch'])
        ns['probe_debug_armed']=True
        ns['watched_probe_arm']();self.assertEqual(calls,['arm-context',(4096,1),'arm'])
        self.assertIs(ns['pending_watch'],watch)
        with self.assertRaisesRegex(AssertionError,'late audit arm'):ns['watched_probe_arm']()
        self.assertEqual(len(calls),3)
        ns['pending_watch']=None;ns['mem']=lambda a,n:b'\x01'
        with self.assertRaisesRegex(AssertionError,'idle root pending'):ns['watched_probe_arm']()
        self.assertIsNone(ns['pending_watch'])

    def test_probe_audit_no_early_target_reads(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        code=session.audit_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        calls=[];row=dict(op=20,before=b'5  history\n'.hex(),result=11,size=11)
        ns=dict(pending={7:row},runs=0,probe_debug_armed=False,
                original_probe_complete=lambda slot,t:calls.append('original') or 19,
                probe_audit_arm=lambda:calls.append('armed'))
        exec(source_node(code,'probe_audit_complete'),ns)
        for run,slot,result,op in ((0,0,11,20),(1,1,11,20),(1,0,-11,20),(1,0,2,20),(1,0,11,15)):
            ns['runs']=run;row.update(result=result,op=op)
            self.assertEqual(ns['probe_audit_complete'](slot,[2,7]),19)
            self.assertFalse(ns['probe_debug_armed'])
        self.assertEqual(calls,['original']*5)
        row.update(result=11,op=20);ns['runs']=1
        ns['probe_audit_complete'](0,[2,7]);self.assertEqual(calls[-2:],['original','armed'])
        self.assertTrue(ns['probe_debug_armed'])
        ns['probe_audit_complete'](0,[2,7]);self.assertEqual(calls.count('armed'),1)
        def fail(slot,t):raise RuntimeError('original failure')
        ns['probe_debug_armed']=False;ns['original_probe_complete']=fail
        with self.assertRaisesRegex(RuntimeError,'original failure'):ns['probe_audit_complete'](0,[2,7])
        self.assertFalse(ns['probe_debug_armed'])

    def test_continuation_capture_is_explicit_and_bounded(self):
        import run_qemu_x86_64_shell_session as session
        normal=session.capture_namespace();diagnostic=session.continuation_capture_namespace()
        self.assertIs(normal['ContinuationTrace'],diagnostic['ContinuationTrace'])
        self.assertEqual(normal['CONTINUATION_EVENTS'],diagnostic['CONTINUATION_EVENTS'])
        # Exercise the generated capture's admission before any process/files.
        plan=session.input_plan(15);calls=[]
        diagnostic['_capture']=lambda *a,**kw:calls.append(kw) or 'captured'
        class Fixture:
            def arguments(self,folder):return ()
            def verify(self,stage):pass
        with patch('run_qemu_x86_64_pio.Fixture',Fixture):
            self.assertEqual(diagnostic['capture'](None,None,None,4096,service_pio_budget=True,
                                                 console_input=plan,media=Fixture()),'captured')
        self.assertTrue(calls[0]['trace_continuation'])
        self.assertTrue(calls[0]['service_pio_budget'])
        with self.assertRaisesRegex(ValueError,'explicit diagnostic'):
            diagnostic['capture'](None,None,None,4096,trace_continuation=False)
        # Non-diagnostic entry still rejects the formerly forbidden combination.
        with self.assertRaises(ValueError):
            normal['capture'](None,None,None,4096,service_pio_budget=True,
                              console_input=plan,trace_continuation=True)

    def test_probe_audit_is_bounded_and_preserves_callbacks(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        code=session.audit_probe_observer(session.command_probe_observer(
            session.hybrid_probe_observer(session.observer_body())))
        self.assertIn('            if probe_debug_armed:probe_audit.record(self)\n            self.callback()',code)
        self.assertIn("finally:gdb.execute('quit 71')",code)
        self.assertEqual(source_node(code,'syscall'),source_node(session.observer_body(),'syscall').replace(
            'if op!=9:pending[gen]=row;resume_hook.enabled=True','if op!=9:pending[gen]=row'))
        samples=[];output=[]
        ns=dict(json=json)
        exec(source_node(code,'ProbeAudit'),ns)
        audit=ns['ProbeAudit'](lambda hook:dict(number=len(samples),name=hook),output.append)
        for n in range(40):
            samples.append(n);audit.record('request')
        self.assertEqual(len(audit.rows),16)
        self.assertEqual([r['number'] for r in audit.rows],list(range(25,41)))
        self.assertFalse(output);audit.dump()
        self.assertEqual(json.loads(output[0].removeprefix('PROBE_AUDIT '))['total'],40)
        self.assertEqual(len(output),1)
        audit.dump();self.assertEqual(len(output),1)
        with self.assertRaisesRegex(ValueError,'closed'):audit.record('late')
        audit=ns['ProbeAudit'](lambda hook:dict(blob='x'*4096),output.append)
        with self.assertRaisesRegex(ValueError,'record capacity'):audit.record('large')
        audit=ns['ProbeAudit'](lambda hook:{},output.append);audit.total=8192
        with self.assertRaisesRegex(ValueError,'event capacity'):audit.record('overflow')

    def test_command_probe_collects_without_target_access(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        from run_qemu_x86_64_service_cpu import StopDispatcher
        code=session.command_probe_observer(session.hybrid_probe_observer(session.observer_body()))
        calls=[]
        class Breakpoint:
            def __init__(self,*a,**kw):pass
            def is_valid(self):return True
        def forbidden(*a):self.fail('target access during GDB stop decision')
        ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_HARDWARE_BREAKPOINT=1,
                                        execute=lambda c:calls.append(c)),
                S={'native_session_probe_request_site64':100},callbacks=0,
                cpu_stops=types.SimpleNamespace(failed=None),d=forbidden,q=forbidden,task=forbidden,
                emit=lambda kind,**row:calls.append((kind,row)))
        ns['service_stops']=StopDispatcher(ns)
        for name in ('static_failure_context','ColdHook','command_probe_stop','command_probe_observe'):
            exec(source_node(code,name),ns)
        cls=ns['ColdHook'];cls.stop=ns['command_probe_stop'];cls.observe=ns['command_probe_observe']
        hook=cls('native_session_probe_request_site64',lambda:None)
        hook.read_only=lambda:calls.append('read')
        self.assertTrue(hook.stop());self.assertFalse(calls);self.assertEqual(ns['callbacks'],0)
        ns['service_stops'].drain();self.assertEqual(calls,['read']);self.assertEqual(ns['callbacks'],1)
        self.assertFalse(ns['service_stops'].pending);self.assertFalse(ns['service_stops'].running)
        # Duplicate stop occurrences must not be silently deduplicated.
        self.assertTrue(hook.stop());self.assertTrue(hook.stop());ns['service_stops'].drain()
        self.assertEqual(calls,['read']*3);self.assertEqual(ns['callbacks'],3)
        def failure():raise AssertionError('missing completion')
        hook.read_only=failure;self.assertTrue(hook.stop())
        with self.assertRaisesRegex(AssertionError,'missing completion'):ns['service_stops'].drain()
        self.assertEqual(calls[-1],'quit 71');self.assertTrue(ns['service_stops'].failed)
        self.assertIn('missing completion',calls[-2][1]['error'])

    def test_pending_request_failure_context_does_not_read_user(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        ns=dict(mode=lambda:8,S=dict(scheduler_current_slot=1,syscall_rax=2),d=lambda a:2,
                task=lambda s:[2,10],q=lambda a:49,starts={10:dict(live=True)},pending={10:dict(op=49)},
                user=lambda *a:self.fail('no new user read after duplicate request'))
        exec(source_node(session.observer_body(),'syscall'),ns)
        with self.assertRaisesRegex(AssertionError,'request s=2 g=10 op=49 live=True pending=49'):
            ns['syscall']()
        self.assertEqual(ns['pending'],{10:dict(op=49)})

    def test_static_probe_failure_preserves_cause_and_bounds(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        body=session.static_probe_observer(session.observer_body())
        ns={};exec(source_node(body,'static_failure_context'),ns)
        exec(source_node(body,'ReadOnlyCPUStops'),ns)
        emitted=[];commands=[]
        state=dict(callbacks=0,service_stops=types.SimpleNamespace(pending=[],running=False,failed=None),
                   emit=lambda kind,**kw:emitted.append((kind,kw)),gdb=types.SimpleNamespace(execute=commands.append))
        reader=ns['ReadOnlyCPUStops'](state)
        def actual_failure():raise AssertionError('original assertion')
        hook=types.SimpleNamespace(name='native_session_probe_return_site64',fn=actual_failure)
        self.assertTrue(reader.stop(hook));self.assertFalse(reader.running)
        self.assertIn('AssertionError: original assertion',reader.failed)
        self.assertIn('actual_failure:',reader.failed);self.assertIn('hook='+hook.name,reader.failed)
        self.assertLessEqual(len(reader.failed),512)
        reader.fail();self.assertEqual(commands,['quit 71']);self.assertEqual(emitted[0][0],'OBSERVER_FAIL')
        reader=ns['ReadOnlyCPUStops'](state);hook.fn=lambda:None
        self.assertFalse(reader.stop(hook));self.assertIsNone(reader.failed)
        self.assertEqual(commands,['quit 71'])

    def test_feeder_decodes_each_complete_record_once(self):
        import run_qemu_x86_64_shell_session as session
        feeder=session.SessionFeeder(session.input_plan(6));loads=json.loads
        root='SHELL_SESSION '+json.dumps(dict(kind='start',slot=0,run=1,gen=1,now=0))+'\n'
        irrelevant='SHELL_SESSION '+json.dumps(dict(kind='cpu_charge',slot=0,gen=1))+'\n'
        with patch.object(session.json,'loads',wraps=loads) as decoder:
            feeder.pump('',root,lambda _:self.fail('premature send'),0)
            self.assertEqual(decoder.call_count,1)
            for count in range(1,41):
                partial=root+irrelevant*count+'SHELL_SESSION '
                feeder.pump('',partial,lambda _:self.fail('premature send'),count/10)
                feeder.pump('',partial,lambda _:self.fail('premature send'),count/10)
                self.assertEqual(decoder.call_count,count+1)
            with self.assertRaisesRegex(ValueError,'stale trace'):
                feeder.pump('',root,lambda _:None,5)

    def test_feeder_incremental_io_capacity_is_cumulative(self):
        import run_qemu_x86_64_shell_session as session
        feeder=session.SessionFeeder(session.input_plan(6))
        root='SHELL_SESSION '+json.dumps(dict(kind='start',slot=0,run=1,gen=1,now=0))+'\n'
        row='CONSOLE_IO '+json.dumps(dict(run=1,slot=0,gen=1,now=1,op=15,fd=0,unused=[0,0,0],
                                        size=1,result=-11,before='00',after='00'))+'\n'
        for count in (4096,8192):
            feeder.pump('',root+row*count,lambda _:self.fail('premature send'),1)
        with self.assertRaisesRegex(ValueError,'IO capacity'):
            feeder.pump('',root+row*8193,lambda _:self.fail('premature send'),1)

    def test_partial_oom_snapshot_after_cached_image_release(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node as node
        code=session.lifecycle_probe_observer(session.observer_body())
        self.assertIn("create_begin_hook=Hook('family_create64.cached_entry',create_begin)",code)
        self.assertNotIn("Hook('family_create64.found',create_begin)",code)
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        begin=source.index('    ; The free dynamic slot is this staging image')
        end=source.index('.cached_entry:',begin)
        evict=source[begin:end]
        self.assertIn('call x86_64_elf64_release64',evict)
        self.assertIn('call physical_free_frame_count64\n    mov [rel family_initial_free],eax',evict)
        S={name:index*4096 for index,name in enumerate(('scheduler_current_slot','family_build_slot',
             'family_initial_free','process_run_generation','scheduler_tasks','family_records','family_create64.cached_entry'),1)}
        parent=struct.pack('<128Q',0,7,*([0]*126));driver=b'D'*1024;record=b'F'*64
        state=dict(free=100,generation=9,slot=3,current=0,iflag=0,pc=S['family_create64.cached_entry'],driver=driver,
                   parent=parent,record=record,initial=100)
        allocator=types.SimpleNamespace(enabled=False);events=[];writes=[]
        def d(address):
            return {S['scheduler_current_slot']:state['current'],S['family_build_slot']:state['slot'],
                    S['family_initial_free']:state['initial'],S['process_run_generation']:state['generation']}[address]
        def mem(address,size):
            return {S['scheduler_tasks']+2048:state['driver'],S['scheduler_tasks']:state['parent'],
                    S['family_records']+192:state['record']}[address]
        regs=dict(rdi=0,rsp=0x1000,rax=(1<<64)-12)
        ns=dict(S=S,CONFIG=dict(case=17,service=0x2000),runs=0,oom_armed=False,oom_injected=False,
                oom_count=0,oom_before=None,allocator=allocator,free=lambda:state['free'],d=d,mem=mem,
                mode=lambda:8,reg=lambda n:state['iflag'] if n=='eflags' else state['pc'] if n=='rip' else regs[n],
                task=lambda slot:struct.unpack('<128Q',state['parent']),
                user=lambda t,a,n:struct.pack('<Q',2),struct=struct,q=lambda a:0x1234,
                gdb=types.SimpleNamespace(execute=writes.append),signed=lambda n:n-(1<<64) if n>>63 else n,
                emit=lambda kind,**row:events.append(dict(kind=kind,**row)),snapshot=lambda raw:raw)
        for name in ('create_begin','allocation','create_end'):exec(node(code,name),ns)
        for key,value in (('initial',80),('pc',0),('iflag',512),('current',1)):
            saved=state[key];state[key]=value
            with self.assertRaises(AssertionError):ns['create_begin']()
            self.assertFalse(allocator.enabled);self.assertIsNone(ns['oom_before']);state[key]=saved
        ns['create_begin']();self.assertTrue(allocator.enabled);self.assertEqual(ns['oom_before'][0],100)
        for count in range(3):
            ns['allocation']();state['free']-=1
            self.assertEqual(ns['oom_count'],count+1);self.assertFalse(writes)
        ns['allocation']();self.assertEqual(len(writes),3);self.assertFalse(allocator.enabled)
        self.assertEqual(events,[dict(kind='oom',run=1,slot=3,acquired=3,free=97)])
        state['free']=100
        for key,value in (('free',99),('free',101),('generation',10),('driver',b'X'*1024),
                          ('parent',bytes(1024)),('record',bytes(64))):
            saved=state[key];state[key]=value
            with self.assertRaises(AssertionError):ns['create_end']()
            self.assertEqual(len(events),1);self.assertTrue(ns['oom_armed']);state[key]=saved
        ns['create_end']();self.assertFalse(ns['oom_armed']);self.assertIsNone(ns['oom_before'])
        self.assertEqual(events[1],dict(kind='rollback',run=1,slot=3,generation=9,free=100,before=100,
                                       driver=driver,family=record))

    def test_cold_fault_route(self):
        import struct
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node as node
        code=session.retirement_probe_observer(session.lifecycle_probe_observer(session.observer_body()))
        S=dict(native_session_probe_fault_site64=0x9000,process_run_exception64=0x1000,scheduler_active=0x2000)
        calls=[];regs=dict(rip=0x9000,rsp=0x8000,eflags=0)
        ns=dict(S=S,mode=lambda:8,mem=lambda a,n:b'\x01',reg=lambda n:regs[n],q=lambda a:0x1005,
                branch_target=lambda *a:calls.append(a),cold_control_paths=lambda:calls.append('routes'),
                fault=lambda:calls.append('frame'))
        exec(node(code,'cold_fault'),ns);ns['cold_fault']()
        self.assertEqual(calls,[('process_run_exception64',232,'native_session_probe_fault_site64'),'routes','frame'])
        for field,value in (('rip',0x9001),('eflags',512)):
            saved=regs[field];regs[field]=value;calls.clear()
            with self.assertRaises(AssertionError):ns['cold_fault']()
            self.assertFalse(calls);regs[field]=saved
        ns['q']=lambda a:0x1006
        with self.assertRaises(AssertionError):ns['cold_fault']()
        ns['mode']=lambda:7;ns['reg']=lambda n:self.fail('inactive fault read');ns['cold_fault']()
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        self.assertIn('process_run_exception64:\n%ifdef REIST_NATIVE_SHELL_SESSION\n    call native_session_probe_fault_site64\n%endif\n',source)
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        self.assertIn('    call native_pio_terminal64\n%endif\n%ifdef REIST_NATIVE_SHELL_SESSION\n.session_probe:\n    call native_session_probe_terminal_site64\n%endif\n',source)
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        for name in ('terminal','fault'):
            self.assertIn('native_session_probe_'+name+'_site64:\n    ret\n',source)

    def test_untraced_command_layout_admission(self):
        import tempfile
        import run_qemu_x86_64_shell_session as session
        with tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent') as directory:
            base=Path(directory)
            for layout in (0,2):
                folder=base/str(layout);calls=[]
                def capture(image,out,code,ram,fixture,**kwargs):
                    self.assertEqual(ram,4096);self.assertEqual(kwargs['console_input'],session.input_plan(0))
                    self.assertEqual('SELECT' in code,layout==0)
                    self.assertIn('detach\nquit 0',code)
                    return '', 'AY_DIAGNOSTIC_NO_BREAKPOINTS'+(' AY_DIAGNOSTIC_LAYOUT ' if layout==0 else '')
                image=base/'absent-image'
                with patch.object(session,'image_config',return_value=({}, {}, b'app')), \
                     patch.object(session,'bounded_fixture',side_effect=lambda f,l,a,s:calls.append(l)), \
                     patch.object(session,'diagnostic_select_layout',return_value='SELECT'), \
                     patch.object(session,'capture_namespace',return_value={'capture':capture}), \
                     patch.object(Path,'read_bytes',return_value=b'image'):
                    result=session.diagnostic_commands(image,folder,'test',lambda:None,layout=layout)
                self.assertEqual(calls,[layout]);self.assertEqual(result['first_layout'],layout)
                self.assertEqual(result['second_layout'],2);self.assertFalse(result['qualification'])
            for layout in (-1,1,3,True,'2'):
                with self.assertRaises(ValueError):
                    session.diagnostic_commands(None,base/'invalid','test',lambda:self.fail('invalid side effect'),layout=layout)

    def test_capture_dispatch_requires_known_pio_end(self):
        import ast
        import run_qemu_x86_64_shell_session as session
        tree=ast.parse(inspect.getsource(session.validate_capture))
        checks=[n for n in ast.walk(tree) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                and any(isinstance(a,ast.Constant) and a.value=='known event kind' for a in n.value.args)]
        self.assertEqual(len(checks),1)
        code=compile(ast.fix_missing_locations(ast.Module(body=checks,type_ignores=[])),'<actual event guard>','exec')
        for kind in ('cpu_start','cpu_charge','cpu_final','pio_end','oom','pio_calls_end'):
            exec(code,dict(kind=kind,require=session.require))
        for kind in ('unknown','pio_calls_end_fake','PIO_END',None):
            with self.assertRaises(ValueError):exec(code,dict(kind=kind,require=session.require))

    def test_cpu_reader_without_notification_still_rejects_gap(self):
        import io,struct,types
        from native_cpu_trace import CPUTraceReader
        memory=bytearray(32+257*192);events=[];stream=io.BytesIO()
        reader=CPUTraceReader(lambda a,n:bytes(memory[a:a+n]),0,len(memory),
            types.SimpleNamespace(event=lambda **row:events.append(row)),{1:dict(live=True,slot=0)},
            lambda:300,types.SimpleNamespace(open=lambda *a,**k:stream),lambda _:None)
        reader.initialize()
        for header in ((257,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)):
            struct.pack_into('<4Q',memory,0,*header)
            with self.assertRaises(ValueError):reader.drain()
            self.assertEqual(reader.sequence,0);self.assertFalse(events);self.assertEqual(stream.getvalue(),b'')
        struct.pack_into('<4Q',memory,0,256,0,0,0)
        for index in range(256):
            struct.pack_into('<4I3Q19Q',memory,32+index*192,1,1,index+1,0,1,index+1,1,*([0]*18+[8]))
        reader.drain();self.assertEqual(reader.sequence,256);self.assertEqual(len(events),256)
        self.assertEqual(len(stream.getvalue()),256*192)

    def test_retirement_probe_transport(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node as node
        before=session.lifecycle_probe_observer(session.hardware_probe_observer(session.observer_body()))
        code=session.retirement_probe_observer(before)
        compile(code,'<retirement transport>','exec')
        for name in ('drain','before_release','release_arm','fault','complete','syscall','resume'):
            self.assertEqual(node(code,name),node(before,name))
        self.assertNotIn("Hook('process_ipc_service64',cold_reap)",code)
        self.assertNotIn("Hook('native_cpu_trace_after64.full',cpu_trace_full)",code)
        self.assertNotIn("Hook('family_terminal64',terminal_pending)",code)
        self.assertNotIn("Hook('x86_64_scheduler_user_exception64',cold_fault)",code)
        self.assertIn("Hook('native_session_probe_terminal_site64',terminal_pending)",code)
        S=dict(process_run_retire64=0x1000,**{'family_cancel_one64.removed':0x2000},
               family_terminal64=0x3000,process_ipc_service64=0x4000,scheduler_current_slot=0x5000,
               scheduler_tasks=0x6000,process_run_receipt=0x9000,native_session_probe_terminal_site64=0xb000,
               native_pio_terminal64=0xc000,**{'family_terminal64.session_probe':0x3020})
        for caller,call,operation in ((0x1081,0x10d4,0x10c4),(0x2066,0x209d,0x2091)):
            memory={caller-5:b'\xe8'+struct.pack('<i',S['family_terminal64']-caller),
                    call:b'\xe8'+struct.pack('<i',S['process_ipc_service64']-call-5),
                    operation:b'\xbf\x04\0\0\0',0x9000:struct.pack('<4I',7,19,0,3),
                    0x3020:b'\xe8'+struct.pack('<i',0xb000-0x3025),
                    0x301b:b'\xe8'+struct.pack('<i',0xc000-0x3020)}
            regs=dict(rip=0xb000,rsp=0xa000,r12=0x6000+7*1024,eflags=0)
            ns=dict(S=S,mode=lambda:8,d=lambda _:7,task=lambda _:(3,19),reg=lambda n:regs[n],
                    q=lambda a:0x3025 if a==0xa000 else caller,mem=lambda a,n:memory[a][:n],struct=struct,release_pending=set(),
                    release_arm_hook=types.SimpleNamespace(enabled=False))
            exec(node(code,'terminal_pending'),ns)
            ns['terminal_pending']();self.assertEqual(ns['release_pending'],{(7,19)})
            self.assertTrue(ns['release_arm_hook'].enabled)
            with self.assertRaises(AssertionError):ns['terminal_pending']()
            ns['release_pending'].clear();ns['release_arm_hook'].enabled=False
            for field,value in (('rip',0x3001),('r12',0x6000),('eflags',512)):
                old=regs[field];regs[field]=value
                with self.assertRaises(AssertionError):ns['terminal_pending']()
                regs[field]=old
            for address in (caller-5,call,operation,0x9000):
                old=memory[address];memory[address]=bytes(len(old))
                with self.assertRaises(AssertionError):ns['terminal_pending']()
                memory[address]=old
            self.assertFalse(ns['release_pending']);self.assertFalse(ns['release_arm_hook'].enabled)
            ns['mode']=lambda:7;ns['reg']=lambda _:self.fail('nonprocess read');ns['terminal_pending']()

    def test_untraced_command_control_feeder(self):
        import run_qemu_x86_64_shell_session as session
        feeder=session.DiagnosticCommandFeeder(session.input_plan(0));serial='';sent=[]
        def write(raw):sent.append(raw);return len(raw)
        for run in (1,2):
            serial+=session.BANNER
            feeder.pump(serial,'',lambda _:self.fail('banner without prompt'),0)
            for command in session.HEALTHY[0][1].splitlines(keepends=True):
                serial+='C:\\>';count=len(sent)
                feeder.pump(serial,'',write,0);self.assertEqual(sent[count:],[command])
                feeder.pump(serial,'',lambda _:self.fail('stale prompt'),0)
                serial+=command.decode()
        self.assertEqual(b''.join(sent),session.HEALTHY[0][1]*2)
        self.assertEqual(len(feeder.sent),2);self.assertEqual(len(feeder.chunks),12)
        feeder.pump(serial,'',lambda _:self.fail('completed control'),0)
        with self.assertRaises(ValueError):feeder.pump(serial,'',write,42)
        with self.assertRaises(ValueError):session.DiagnosticCommandFeeder(session.input_plan(6))
        with self.assertRaises(ValueError):feeder.pump(serial[:-3],'',write,0)

    def test_hybrid_cold_probe_transport(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        base=session.lifecycle_probe_observer(session.hardware_probe_observer(session.observer_body()))
        code=session.hybrid_probe_observer(base)
        compile(code,'<hybrid observer>','exec')
        for name in ('syscall','resume','complete','start','copy','before_release','creation_enter','creation_leave','drain','fault','fail'):
            expected=source_node(base,name).replace(';resume_hook.enabled=True','').replace('    resume_hook.enabled=False','    pass')
            self.assertEqual(source_node(code,name),expected)
        calls=[]
        class Breakpoint:
            def __init__(self,*args,**kwargs):pass
            def is_valid(self):return True
        ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_HARDWARE_BREAKPOINT=2),
                S={'scheduler_current_slot':1,'syscall_rax':2,'native_session_probe_request_site64':100,
                   'native_session_probe_return_site64':102,'native_session_probe_denied_site64':101},
                d=lambda _:0,task=lambda _:[2,7],q=lambda _:15,pending={},callbacks=0,
                cpu_stops=types.SimpleNamespace(failed=None,stop=lambda h:calls.append('static') or False,
                                               fail=lambda:calls.append('fail')),
                service_stops=types.SimpleNamespace(bind=lambda h:None,collect=lambda h:calls.append('collect') or True,
                                                   drain=lambda:calls.append('deferred')))
        exec(source_node(code,'hybrid_dispatch')+'\n'+source_node(code,'ColdHook'),ns)
        for name in ('request','denied','return'):
            hook=ns['ColdHook']('native_session_probe_'+name+'_site64',lambda:None)
            self.assertIn('hybrid_dispatch()',hook.commands)
            hook.read_only=lambda:calls.append('callback')
            for operation in (15,20,53,54,113,114,127,132):
                ns['q']=lambda _,op=operation:op
                ns['pending']={7:{'op':operation}}
                calls.clear();self.assertEqual(hook.stop(),operation==132)
                self.assertEqual(calls,['collect' if operation==132 else 'static'])
                if operation==132:
                    self.assertFalse(hook.observe());self.assertEqual(calls,['collect','callback'])
            if name=='return':
                ns['pending']={};calls.clear();self.assertFalse(hook.stop());self.assertEqual(calls,['static'])
        calls.clear();ns['hybrid_dispatch']();self.assertEqual(calls,['deferred'])
        ns['cpu_stops'].failed=('ValueError','bad');calls.clear();ns['hybrid_dispatch']();self.assertEqual(calls,['fail'])
        ns['cpu_stops'].failed=None;ns['d']=lambda _:8;calls.clear()
        self.assertTrue(hook.stop());self.assertIsNotNone(ns['cpu_stops'].failed);self.assertFalse(calls)
        # Exercise the actual deferred contract, not only routing stubs.
        from run_qemu_x86_64_service_cpu import StopDispatcher,ReadOnlyCPUStops
        ns['d']=lambda _:0;ns['q']=lambda _:132
        ns['service_stops']=StopDispatcher(ns);ns['cpu_stops']=ReadOnlyCPUStops(ns)
        hook=ns['ColdHook']('native_session_probe_request_site64',lambda:None)
        hook.read_only=lambda:calls.append('actual callback');calls.clear()
        self.assertTrue(hook.stop());ns['hybrid_dispatch']()
        self.assertEqual(calls,['actual callback']);self.assertFalse(ns['service_stops'].running)
        self.assertFalse(ns['service_stops'].pending);self.assertFalse(hook.service_retire)

    def test_pio_record_decoder_and_reader(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        def record(n):
            raw=bytearray(384)
            struct.pack_into('<2I7Q',raw,0,1,0,n,2,17,10,11,(1<<64)-22,0)
            struct.pack_into('<6Q',raw,64,29,0x40f080,0,0,0,0)
            raw[112:176]=b'1'*64;raw[176:240]=b'2'*64
            struct.pack_into('<4Q',raw,352,2,2,8,8)
            return bytes(raw)
        call,reply=session.pio_record_decode(record(1),1,1)
        self.assertEqual(call,dict(run=1,slot=2,gen=17,op=113,args=[29,0x40f080,0,0,0,0],pointer=0x40f080,
            size=64,before=(b'1'*64).hex(),fd=29,unused=[0,0,0],entered=100,profile_denied=False,
            family_before=None,authority=None,terminal_before=bytes(24).hex()))
        self.assertEqual(reply,dict(call,result=-22,now=110,after=(b'2'*64).hex(),terminal=bytes(24).hex(),
                                   pio=bytes(64).hex(),family=None))
        for offset,value,format_ in ((0,2,'I'),(4,1,'I'),(8,2,'Q'),(16,8,'Q'),(24,0,'Q'),
            (24,1<<31,'Q'),(32,12,'Q'),(40,1<<60,'Q'),(56,1,'Q'),(352,514,'Q'),(360,514,'Q'),(368,7,'Q'),(376,7,'Q')):
            raw=bytearray(record(1));struct.pack_into('<'+format_,raw,offset,value)
            with self.assertRaises(ValueError):session.pio_record_decode(bytes(raw),1,1)
        memory=bytearray(12320);events=[];snapshots={};current_run=[1];reads=[]
        def read(a,n):reads.append((a,n));return bytes(memory[a:a+n])
        def snapshot(raw):
            name=str(len(snapshots));snapshots[name]=raw;return name
        reader=session.PioCallReader(read,0,{17:dict(slot=2,live=True)},lambda:20,snapshot,
            lambda kind,**kw:events.append(dict(kind=kind,**kw)),lambda:current_run[0])
        reader.initialize()
        for run in (1,2):
            current_run[0]=run;events.append(dict(kind='start',slot=2,gen=17))
            for total in (31,34):
                for n in range(max(1,total-31),total+1):memory[32+((n-1)&31)*384:32+((n-1)&31)*384+384]=record(n)
                struct.pack_into('<4Q',memory,0,total,0,0,0);reader.drain()
                self.assertEqual(reader.sequence,total)
            reader.finish_run();events.append(dict(kind='release',slot=2,gen=17))
            memory[:]=bytes(12320);reader.drain();self.assertEqual(reader.sequence,0)
        raw=types.SimpleNamespace(read=lambda reference:snapshots[reference])
        session.validate_pio_records(events,raw)
        calls=[i for i,row in enumerate(events) if row['kind']=='call']
        for alteration in ('drop','duplicate','field','end'):
            bad=copy.deepcopy(events)
            if alteration=='drop':del bad[calls[0]]
            elif alteration=='duplicate':bad.insert(calls[0],copy.deepcopy(bad[calls[0]]))
            elif alteration=='field':bad[calls[0]]['entered']+=10
            else:next(row for row in bad if row['kind']=='pio_calls_end')['total']-=1
            with self.assertRaises(ValueError):session.validate_pio_records(bad,raw)
        for total,error,pending,reserved in ((33,0,0,0),(2049,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)):
            memory[:]=bytes(12320);struct.pack_into('<4Q',memory,0,total,error,pending,reserved)
            prior=len(events)
            with self.assertRaises(ValueError):reader.drain()
            self.assertEqual(len(events),prior)
        self.assertTrue(all(n<=12320 for a,n in reads))

    def test_actual_pio_record_ring(self):
        from test_x86_64_task_frames import TaskFrameTests
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        self.assertEqual(source.count('; AY_PIO_RECORD_BEGIN\n'),1)
        body=source.split('; AY_PIO_RECORD_BEGIN\n')[1].split('; AY_PIO_RECORD_END')[0]
        # Host ring3 cannot choose IF. Substitute only the sampled input flag
        # word; production save/restore and all admission/copy/commit code run.
        self.assertEqual(body.count('mov rax,[rsp+120]'),2)
        body=body.replace('mov rax,[rsp+120]','mov rax,[rel host_flags]')
        asm=r'''BITS 64
TASK_GENERATION equ 8
PF_R equ 4
section .bss
align 8
global scheduler_mode,scheduler_current_slot,scheduler_last_tick,scheduler_tasks
global syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9
global native_terminal_state,native_pio_state,native_session_pio_trace,host_flags,host_valid,host_request,host_flushes
scheduler_mode: resq 1
scheduler_current_slot: resq 1
scheduler_last_tick: resq 1
align 16
scheduler_tasks: resb 8192
syscall_rdi: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
align 16
native_terminal_state: resq 3
align 16
native_pio_state: resq 8
align 16
native_session_pio_trace: resb 12320
host_flags: resq 1
host_valid: resq 1
align 16
host_request: resb 64
host_flushes: resq 1
section .text
scheduler_validate_shell_range64:
    cmp rdx,64
    jne .bad
    cmp ecx,PF_R
    jne .bad
    lea r11,[rel host_request]
    cmp rax,r11
    jne .bad
    mov rax,[rel host_valid]
    ret
.bad: xor eax,eax
    ret
native_session_probe_pio_site64:
    pushfq
    inc qword [rel host_flushes]
    popfq
    ret
global trace_call
trace_call:
    push r12
    lea r12,[rel scheduler_tasks]
    mov eax,[rel scheduler_current_slot]
    and eax,7
    shl eax,10
    add r12,rax
    lea r11,[rel trace_calls]
    mov rax,-123
    mov ecx,0x76543210
    mov edx,0x12345678
    stc
    pushfq
    pop r10
    call [r11+rdi*8]
    pushfq
    pop r8
    cmp r10,r8
    jne .bad
    cmp rax,-123
    jne .bad
    cmp rcx,0x76543210
    jne .bad
    cmp rdx,0x12345678
    jne .bad
    mov eax,1
    pop r12
    ret
.bad: xor eax,eax
    pop r12
    ret
section .data
trace_calls: dq native_session_pio_enter64,native_session_pio_return64
section .text
'''+body
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern uint64_t scheduler_mode,scheduler_current_slot,scheduler_last_tick,scheduler_tasks[8][128];
extern uint64_t syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9;
extern uint64_t native_terminal_state[3],native_pio_state[8],host_flags,host_valid,host_flushes;
extern unsigned char native_session_pio_trace[12320],host_request[64];
extern int __attribute__((sysv_abi)) trace_call(unsigned);
#define CHECK(x) do{if(!(x)){fprintf(stderr,"PIO record line%d\n",__LINE__);exit(1);}}while(0)
static uint64_t word(unsigned offset){uint64_t v;memcpy(&v,native_session_pio_trace+offset,8);return v;}
static void reset(void){memset(native_session_pio_trace,0,12320);scheduler_mode=8;scheduler_current_slot=2;
 scheduler_last_tick=10;scheduler_tasks[2][1]=17;host_flags=0;host_valid=1;host_flushes=0;
 syscall_rdi=29;syscall_rsi=(uintptr_t)host_request;syscall_rdx=0;syscall_r10=0;syscall_r8=0;syscall_r9=0;
 memset(host_request,0x35,64);for(unsigned i=0;i<3;i++)native_terminal_state[i]=11+i;
 for(unsigned i=0;i<8;i++)native_pio_state[i]=21+i;}
int main(void){
 reset();for(unsigned n=1;n<=2048;n++){
  memset(host_request,n&255,64);scheduler_last_tick=10+n;CHECK(trace_call(0));
  CHECK(word(0)==n-1&&!word(8)&&word(16)==1);unsigned at=32+((n-1)&31)*384;
  CHECK(word(at)==1&&word(at+8)==n&&word(at+16)==2&&word(at+24)==17);
  CHECK(word(at+32)==10+n&&word(at+64)==29&&word(at+72)==(uintptr_t)host_request);
  CHECK(!memcmp(native_session_pio_trace+at+112,host_request,64));
  CHECK(!memcmp(native_session_pio_trace+at+240,native_terminal_state,24));
  memset(host_request,0xa7,64);scheduler_last_tick++;
  CHECK(trace_call(1));CHECK(word(0)==n&&!word(8)&&!word(16)&&host_flushes==n/32);
  CHECK(word(at+40)==11+n&&word(at+48)==(uint64_t)-123);
  CHECK(!memcmp(native_session_pio_trace+at+176,host_request,64));
  CHECK(!memcmp(native_session_pio_trace+at+264,native_terminal_state,24));
  CHECK(!memcmp(native_session_pio_trace+at+288,native_pio_state,64));
  CHECK(!word(at+352)&&!word(at+360)&&word(at+368)==8&&word(at+376)==8);
 }
 CHECK(trace_call(0));CHECK(word(8)==1&&word(0)==2048);
 for(unsigned mode=0;mode<7;mode++){
  reset();if(mode==0)host_valid=0;else if(mode==1)host_flags=512;else if(mode==2)scheduler_current_slot=8;
  else if(mode==3)scheduler_tasks[2][1]=0;else if(mode==4)scheduler_last_tick=1ULL<<60;
  else if(mode==5)scheduler_mode=7;else syscall_rsi=0;
  CHECK(trace_call(0));CHECK(word(8)==1&&!word(0));CHECK(host_request[0]==0x35);
 }
 reset();CHECK(trace_call(1));CHECK(word(8)==1&&!word(0));
 reset();CHECK(trace_call(0));CHECK(trace_call(0));CHECK(word(8)==1&&!word(0));
 for(unsigned mode=0;mode<4;mode++){
  reset();CHECK(trace_call(0));if(mode==0)scheduler_tasks[2][1]++;else if(mode==1)scheduler_current_slot=3;
  else if(mode==2)scheduler_last_tick--;else host_valid=0;
  CHECK(trace_call(1));CHECK(word(8)==1&&!word(0));
 }
 puts("SHELL_SESSION_PIO_RING_OK");return 0;
}'''
        TaskFrameTests().build(asm,c,'SHELL_SESSION_PIO_RING')

    def test_deferred_syscall_read_spans(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_service_cpu import SameStopReads
        node=session.admission.source_node
        base=session.lifecycle_probe_observer(session.hardware_probe_observer(session.observer_body()))
        code=session.deferred_read_observer(base)
        compile(code,'<deferred joined reads>','exec')
        for name in ('syscall','syscall_denied','resume','complete','creation_enter','creation_leave','Hook'):
            self.assertEqual(node(code,name),node(base,name))
        symbols=dict(scheduler_mode=400,scheduler_current_slot=404,scheduler_last_tick=408)
        symbols.update({'syscall_'+n:500+8*i for i,n in enumerate(('rax','rdi','rsi','rdx','r10','r8','r9'))})
        reads=[];epoch=[1]
        def memory(a,n):reads.append((a,n));return bytes([epoch[0]])*n
        ns=dict(S=symbols,mem=memory,SameStopReads=SameStopReads)
        exec(compile(node(code,'DeferredReadSpans'),'<actual deferred read scope>','exec'),ns)
        scope=ns['DeferredReadSpans'](ns);values=[]
        def action(hook):
            for a,n in ((400,1),(404,4),(408,8),(508,8),(516,8),(508,8),(700,12),(700,12)):
                values.append(ns['mem'](a,n))
            return False
        wrapped=scope.wrap(action)
        for name in ('syscall','syscall_denied','resume','start','cold_fault'):
            hook=types.SimpleNamespace(fn=types.SimpleNamespace(__name__=name))
            for e in (1,2):
                epoch[0]=e;reads.clear();values.clear();self.assertFalse(wrapped(hook))
                self.assertEqual(values,[bytes([e])*n for n in (1,4,8,8,8,8,12,12)])
                self.assertEqual(len(reads),3 if name in ('syscall','syscall_denied','resume') else 8)
                self.assertIs(ns['mem'],memory);self.assertFalse(scope.active)
        hook.fn.__name__='syscall'
        def broken(hook):raise RuntimeError('callback failure')
        with self.assertRaises(RuntimeError):scope.wrap(broken)(hook)
        self.assertIs(ns['mem'],memory);self.assertFalse(scope.active)
        scope.active=True
        with self.assertRaises(ValueError):wrapped(hook)
        scope.active=False
        def nested(hook):return wrapped(hook)
        with self.assertRaises(ValueError):scope.wrap(nested)(hook)
        self.assertIs(ns['mem'],memory);self.assertFalse(scope.active)

    def test_lifecycle_scoped_observer(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        node=session.admission.source_node
        original=session.hardware_probe_observer(session.observer_body())
        code=session.lifecycle_probe_observer(original)
        compile(code,'<lifecycle-scoped complete observer>','exec')
        for name in ('fault','fail','copy','create_begin','create_end','drain','before_release'):
            self.assertEqual(node(code,name),node(original,name))
        self.assertNotIn("Hook('process_run_exception64',fault)",code)
        self.assertNotIn("Hook('scheduler_fail',fail)",code)
        self.assertIn("Hook('x86_64_scheduler_user_exception64',cold_fault)",code)
        self.assertIn("Hook('serial_init64',cold_fail)",code)
        self.assertIn("if not any(v['live'] for v in starts.values()):trace_before_hook.enabled=trace_after_hook.enabled=True",code)
        hooks=[types.SimpleNamespace(enabled=False) for _ in range(3)]
        ns=dict(zip(('create_begin_hook','copy_hook','create_end_hook'),hooks));ns['struct']=struct
        for name in ('creation_enter','creation_leave'):exec(compile(node(code,name),'<actual creation hooks>','exec'),ns)
        for op,denied,operation in ((20,False,0),(132,True,1),(132,False,2),(132,False,3)):
            row=dict(op=op,profile_denied=denied,before=struct.pack('<3I',1,64,operation).hex())
            ns['creation_enter'](row);ns['creation_leave'](row)
            self.assertFalse(any(h.enabled for h in hooks))
        row=dict(op=132,profile_denied=False,before=struct.pack('<3I',6,80,1).hex())
        for result in (3<<32|2,-11,-12,-22):
            ns['creation_enter'](row);self.assertTrue(all(h.enabled for h in hooks))
            with self.assertRaises(AssertionError):ns['creation_enter'](row)
            ns['creation_leave'](dict(row,result=result));self.assertFalse(any(h.enabled for h in hooks))
            with self.assertRaises(AssertionError):ns['creation_leave'](row)
        regs={'rdi':4,'rsi':7,'rdx':19,'eflags':0};checks=[]
        ns=dict(mode=lambda:8,reg=lambda n:regs[n],task=lambda slot:(3,19),release_pending=set(),
                release=None,release_hook=types.SimpleNamespace(enabled=False),
                release_arm_hook=types.SimpleNamespace(enabled=False),d=lambda a:7,
                S={'scheduler_current_slot':100},branch_target=lambda *args:checks.append(args))
        for name in ('cold_reap','release_arm'):exec(compile(node(code,name),'<actual retirement hooks>','exec'),ns)
        ns['cold_reap']();self.assertEqual(ns['release_pending'],{(7,19)})
        with self.assertRaises(AssertionError):ns['cold_reap']()
        ns['release_arm']();self.assertTrue(ns['release_hook'].enabled)
        self.assertFalse(ns['release_pending']);self.assertFalse(ns['release_arm_hook'].enabled)
        self.assertEqual(checks,[('process_run_complete_retire64',232,'scheduler_release_task_frames64'),
                                 ('scheduler_fail',233,'native_pio_fail64')])
        ns['release_hook'].enabled=False;regs['rsi']=8
        with self.assertRaises(AssertionError):ns['cold_reap']()
        regs['rsi']=0;regs['rdx']=18
        with self.assertRaises(AssertionError):ns['cold_reap']()
        regs['rdi']=3;ns['cold_reap']();self.assertFalse(ns['release_pending'])

    def test_release_observation_process_mode_only(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        body=source_node(session.observer_body(),'before_release')
        for selected in tuple(range(8))+(9,10,255):
            def forbidden(*args,**kwargs):raise AssertionError('pre-process evidence access')
            ns=dict(mode=lambda:selected,d=forbidden,S={},task=forbidden,mem=forbidden,
                    cpu_sink=types.SimpleNamespace(event=forbidden),release_begin=forbidden)
            exec(compile(body,'<actual release callback>','exec'),ns)
            ns['before_release']()
        events=[];pending={3:dict(gen=3,slot=2,op=53)}
        pio=struct.pack('<8Q',3<<32|2,0,1,0,0,0,0,0)
        buffers={300:pio,432:bytes(16),500:bytes(24)}
        ns=dict(mode=lambda:8,S=dict(scheduler_current_slot=100,scheduler_last_tick=200,
                native_pio_state=300,family_extended_masks=400,native_terminal_state=500),
                d=lambda a:2,task=lambda slot:(3,3),pending=pending,q=lambda a:20,
                cpu_record=lambda slot:[3,32,5,20,100,0,0,5],struct=struct,
                mem=lambda a,n:buffers[a],emit=lambda kind,**kw:events.append((kind,kw)),
                cpu_sink=types.SimpleNamespace(event=lambda **kw:events.append(('cpu',kw))),
                release_begin=lambda:events.append(('release',{})))
        exec(compile(body,'<actual process retirement>','exec'),ns)
        ns['before_release']()
        self.assertEqual([e[0] for e in events],['abandoned','cpu','fenced','release'])
        self.assertEqual(pending,{})
        self.assertEqual(events[2][1]['gen'],3)

    def test_cached_readonly_probe_transport(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        from run_qemu_x86_64_service_cpu import ReadOnlyCPUStops,SameStopReads
        original=session.static_probe_observer(session.hardware_probe_observer(session.observer_body()))
        code=session.cached_probe_observer(original)
        compile(code,'<same-stop joined reads>','exec')
        for name in ('syscall','resume','complete','drain'):
            self.assertEqual(source_node(code,name),source_node(original,name))
        calls=[];writes=[];epoch=[7]
        class Breakpoint:
            def __init__(self,*args,**kwargs):pass
        names=('scheduler_mode','scheduler_current_slot','scheduler_last_tick')
        symbols=dict(zip(names,(400,404,408)))
        symbols.update({'syscall_'+n:500+8*i for i,n in enumerate(('rax','rdi','rsi','rdx','r10','r8','r9'))})
        symbols.update(native_session_probe_request_site64=100,native_session_probe_request64=300)
        def memory(address,size):
            calls.append((address,size))
            if address==195:return b'\xe8'+struct.pack('<i',100)
            return bytes([epoch[0]])*size
        ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_HARDWARE_BREAKPOINT=2),S=symbols,
                reg=lambda name:100 if name=='rip' else 1000,q=lambda address:200,mem=memory,
                struct=struct,callbacks=0,SameStopReads=SameStopReads,drain=lambda:None,
                service_stops=types.SimpleNamespace(pending=[],running=False,failed=False))
        ns['cpu_stops']=ReadOnlyCPUStops(ns)
        exec(compile(source_node(code,'ColdHook'),'<actual joined callback>','exec'),ns)
        values=[]
        def callback():
            for address,size in ((400,1),(404,4),(408,8),(508,8),(516,8),(508,8),(700,12),(700,12)):
                values.append(ns['mem'](address,size))
        hook=ns['ColdHook']('native_session_probe_request_site64',callback)
        for value in (7,9):
            epoch[0]=value;calls.clear();values.clear()
            self.assertFalse(hook.stop())
            self.assertEqual(calls,[(195,5),(400,16),(500,56),(700,12)])
            self.assertEqual(values,[bytes([value])*n for n in (1,4,8,8,8,8,12,12)])
            self.assertIs(ns['mem'],memory)
        hook.callback=lambda:ns['mem'](400,32768)
        calls.clear();self.assertTrue(hook.stop());self.assertEqual(calls,[(195,5)])
        self.assertIs(ns['mem'],memory)

    def test_diagnostic_same_layout_selection(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        config=dict(selection=0x410080,s=dict(native_session_probe_start_site64=100,
                    scheduler_mode=200,scheduler_current_slot=204,scheduler_tasks=4096))
        code=session.diagnostic_select_layout(config)
        self.assertIn('hbreak *0x64\ncontinue\npython\n',code)
        body=code.split('\npython\n',1)[1].split('\nend\n')[0]
        dm=0xffff800000000000;selection=dm+0x100000080
        for bad in (None,'slot','generation','leaf','selection'):
            writes=[];reads=[]
            task=[0]*128;task[0]=2;task[1]=2 if bad=='generation' else 1;task[2]=0x2000
            memory={200:b'\x08',204:struct.pack('<I',1 if bad=='slot' else 0),
                    4096:struct.pack('<128Q',*task),dm+0x2000:struct.pack('<Q',0x3007),
                    dm+0x3000:struct.pack('<Q',0x4007),dm+0x4010:struct.pack('<Q',0x5007),
                    dm+0x5080:struct.pack('<Q',(1<<63)|0x100000000|(5 if bad=='leaf' else 7)),
                    selection:struct.pack('<4Q',0x3153455353484c53,1,3 if bad=='selection' else 2,0)}
            def read(address,size):
                reads.append((address,size));raw=memory[address];self.assertEqual(len(raw),size);return raw
            def write(address,raw):writes.append((address,raw));memory[address]=raw
            fake=types.SimpleNamespace(selected_inferior=lambda:types.SimpleNamespace(read_memory=read,write_memory=write),
                parse_and_eval=lambda expr:100 if expr=='$rip' else 0,write=lambda text:None)
            with patch.dict(sys.modules,{'gdb':fake}):
                if bad:
                    with self.assertRaises(AssertionError):exec(compile(body,'<same-layout selection>','exec'),{})
                    self.assertEqual(writes,[])
                else:
                    exec(compile(body,'<same-layout selection>','exec'),{})
                    self.assertEqual(writes,[(selection,struct.pack('<4Q',0x3153455353484c53,1,0,0))])

    def test_static_readonly_probe_transport(self):
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        code=session.static_probe_observer(session.hardware_probe_observer(session.observer_body()))
        compile(code,'<static same-field observer>','exec')
        request=source_node(code,'syscall');reply=source_node(code,'resume')
        self.assertNotIn('resume_hook.enabled',request+reply)
        self.assertIn("ColdHook('native_session_probe_request_site64',syscall)",code)
        self.assertIn("ColdHook('native_session_probe_denied_site64',syscall_denied)",code)
        self.assertIn("ColdHook('native_session_probe_return_site64',resume)",code)
        self.assertIn('size<32768',code)
        self.assertIn("finally:globals()['mem']=original",code)
        self.assertIn("cpu_stops=ReadOnlyCPUStops(globals())",code)
        # All runtime collection functions differ only in hook arming; no field
        # read, emit, pending transition or raw result is dropped.
        old=session.observer_body()
        for name in ('syscall','resume','complete'):
            expected=source_node(old,name).replace(';resume_hook.enabled=True','').replace('    resume_hook.enabled=False','    pass')
            self.assertEqual(source_node(code,name),expected)
        import struct,types
        from run_qemu_x86_64_service_cpu import ReadOnlyCPUStops
        for fault in (None,'large','pc','caller'):
            reads=[];events=[];constructors=[]
            class Breakpoint:
                def __init__(self,address,**kwargs):constructors.append((address,kwargs))
            def memory(address,size):
                reads.append((address,size))
                if (address,size)==(195,5):return b'\xe8'+struct.pack('<i',101 if fault=='caller' else 100)
                return bytes(size)
            ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_HARDWARE_BREAKPOINT=2),
                S={'native_session_probe_request_site64':100,'native_session_probe_request64':300},
                reg=lambda name: (101 if fault=='pc' else 100) if name=='rip' else 1000,
                q=lambda address:200,mem=memory,struct=struct,callbacks=0,
                service_stops=types.SimpleNamespace(pending=[],running=False,failed=False),
                drain=lambda:events.append('drain'))
            ns['cpu_stops']=ReadOnlyCPUStops(ns)
            exec(compile(source_node(code,'ColdHook'),'<actual static callback>','exec'),ns)
            def callback():
                events.append('callback');ns['mem'](500,32768 if fault=='large' else 16)
            hook=ns['ColdHook']('native_session_probe_request_site64',callback)
            self.assertEqual(constructors,[('*0x64',dict(internal=True,type=2))])
            self.assertEqual(hook.stop(),fault is not None)
            self.assertIs(ns['mem'],memory)
            self.assertFalse(ns['cpu_stops'].running)
            self.assertEqual(ns['callbacks'],1)
            self.assertEqual(events,[] if fault in ('pc','caller') else ['drain','callback'])
            self.assertNotIn((500,32768),reads)
            self.assertEqual(ns['cpu_stops'].failed is None,fault is None)

    def test_hardware_cold_probe_selection(self):
        import types
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        code=session.hardware_probe_observer(session.observer_body())
        seen=[]
        class Breakpoint:
            def __init__(self,address,**kwargs):seen.append((address,kwargs))
        names=['native_session_probe_'+site+'_site64' for site in ('request','denied','return','start')]+['scheduler_fail']
        ns=dict(gdb=types.SimpleNamespace(Breakpoint=Breakpoint,BP_BREAKPOINT=1,BP_HARDWARE_BREAKPOINT=2),
                S=dict(zip(names,range(100,105))),service_stops=types.SimpleNamespace(bind=lambda *a:None))
        exec(compile(source_node(code,'Hook'),'<real hardware probe constructor>','exec'),ns)
        for name in names:ns['Hook'](name,lambda:None)
        self.assertEqual([v['type'] for _,v in seen],[2,2,2,2,1])
        self.assertTrue(all(v['internal'] for _,v in seen))
        with self.assertRaises(ValueError):session.hardware_probe_observer('wrong constructor')

    def test_cold_probe_pc_diagnostic(self):
        import run_qemu_x86_64_shell_session as session
        code=session.observer_body()
        probe=session.cold_probe_pc_diagnostic(code)
        self.assertIn('PROBE_PC ',probe)
        self.assertIn("assert actual==expected,'PROBE_PC_MISMATCH'",probe)
        self.assertLess(probe.index("'PROBE_PC_MISMATCH'"),probe.index('            self.fn()'))
        compile(probe,'<bounded PC diagnostic>','exec')
        with self.assertRaises(ValueError):session.cold_probe_pc_diagnostic('wrong callback')

    def test_cold_probe_binding_and_blocked_copyout_order(self):
        import run_qemu_x86_64_shell_session as session
        body=session.observer_body()
        for site in ('request','denied','return','start'):
            self.assertIn("Hook('native_session_probe_"+site+"_site64'",body)
        self.assertNotIn("Hook('process_run_resume64'",body)
        self.assertNotIn("Hook('scheduler_enter_task64.state_published'",body)
        self.assertNotIn("Hook('process_run_syscall64.denied'",body)
        kernel=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        section=kernel.split('.state_published:\n',1)[1].split('    push qword USER_DATA_SELECTOR',1)[0]
        self.assertLess(section.index('call process_ipc_take64'),section.index('call native_session_probe_start64'))
        self.assertIn("assert not any(mem(S['native_session_probe_seen'],12408))",body)
        self.assertIn("pieces.append(raw)\n    contexts=[]",body)
        compile(body,'<cold full AY observer>','exec')

    def test_actual_cold_probe_dispatch(self):
        from test_x86_64_task_frames import TaskFrameTests
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        self.assertEqual(source.count('; AY_COLD_PROBES_BEGIN\n'),1)
        body=source.split('; AY_COLD_PROBES_BEGIN\n')[1].split('; AY_COLD_PROBES_END')[0]
        for index,name in enumerate(('request','denied','return','start')):
            anchor='native_session_probe_'+name+'_site64:\n    ret'
            self.assertEqual(body.count(anchor),1)
            body=body.replace(anchor,anchor[:-3]+'pushfq\n    inc qword [rel counters+'+str(index*8)+']\n    popfq\n    ret')
        asm=r'''BITS 64
TASK_GENERATION equ 8
SCHEDULER_MODE_PROCESS equ 8
section .bss
align 8
global scheduler_mode,scheduler_current_slot,syscall_rax,syscall_rdi,scheduler_tasks,native_session_probe_seen,native_session_probe_pending,counters,native_session_read_tickets
scheduler_mode: resq 1
scheduler_current_slot: resq 1
syscall_rax: resq 1
syscall_rdi: resq 1
scheduler_tasks: resb 8192
native_session_probe_seen: resq 8
native_session_probe_pending: resb 8
native_session_read_tickets: resq 2
align 16
counters: resq 4
section .text
global probe_call
probe_call:
    lea r9,[rel calls]
    mov ecx,[rel scheduler_current_slot]
    and ecx,7
    shl ecx,10
    lea r11,[rel scheduler_tasks]
    add r11,rcx
    mov eax,0x12345678
    mov ecx,0x87654321
    mov edx,0x11223344
    cmp rax,rax
    pushfq
    pop r10
    call [r9+rdi*8]
    pushfq
    pop r8
    cmp r8,r10
    jne .bad
    cmp rax,0x12345678
    jne .bad
    mov r8d,0x87654321
    cmp rcx,r8
    jne .bad
    cmp rdx,0x11223344
    jne .bad
    mov eax,1
    ret
.bad: xor eax,eax
    ret
section .data
calls: dq native_session_probe_request64,native_session_probe_denied64,native_session_probe_return64,native_session_probe_start64,native_session_probe_terminal_site64,native_session_probe_fault_site64
section .text
native_session_pio_enter64:
    pushfq
    inc qword [rel counters]
    popfq
    ret
native_session_pio_return64:
    pushfq
    inc qword [rel counters+16]
    popfq
    ret
'''+body
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern uint64_t scheduler_mode,scheduler_current_slot,syscall_rax,syscall_rdi,scheduler_tasks[8][128],native_session_probe_seen[8],counters[4];
extern unsigned char native_session_probe_pending[8];
extern uint64_t native_session_read_tickets[2];
extern int __attribute__((sysv_abi)) probe_call(unsigned);
#define CHECK(v) do{if(!(v)){fprintf(stderr,"cold probe line%d\n",__LINE__);exit(1);}}while(0)
int main(void){
 scheduler_mode=8;
 for(unsigned slot=0;slot<8;slot++){
  scheduler_current_slot=slot;scheduler_tasks[slot][1]=slot+17;
  uint64_t starts=counters[3];CHECK(probe_call(3));CHECK(counters[3]==starts+1);
  CHECK(native_session_probe_seen[slot]==slot+17);CHECK(probe_call(3));CHECK(counters[3]==starts+1);
  for(unsigned duration=0;duration<3;duration++){
  syscall_rdi=duration==0?10:duration==1?100:101;
  for(unsigned op=0;op<160;op++){
   int watched=op==9||op==15||op==20||(op>=49&&op<=55)||op==113||op==114||op==127||op==132||(op==41&&slot==0&&syscall_rdi==100);
   syscall_rax=op;uint64_t requests=counters[0],denied=counters[1],returns=counters[2];
   uint64_t read_requests=native_session_read_tickets[0],read_returns=native_session_read_tickets[1];
   unsigned root_read=slot==0&&op==15;
   CHECK(probe_call(0));CHECK(counters[0]==requests+watched);
   CHECK(native_session_read_tickets[0]==read_requests+root_read);
   CHECK(native_session_probe_pending[slot]==(op==113?2:(watched&&op!=9)));
   CHECK(probe_call(2));CHECK(counters[2]==returns+(watched&&op!=9));CHECK(!native_session_probe_pending[slot]);
   CHECK(native_session_read_tickets[1]==read_returns+root_read);
   CHECK(probe_call(1));CHECK(counters[1]==denied+watched);
   CHECK(native_session_read_tickets[0]==read_requests+2*root_read);
   starts=counters[3];CHECK(probe_call(3));CHECK(counters[3]==starts+(watched&&op!=9));CHECK(!native_session_probe_pending[slot]);
  }
  }
 }
 scheduler_current_slot=0;syscall_rax=15;
 native_session_read_tickets[0]=native_session_read_tickets[1]=8192;
 for(unsigned n=0;n<3;n++){CHECK(probe_call(0));CHECK(probe_call(2));
  CHECK(native_session_read_tickets[0]==8193&&native_session_read_tickets[1]==8193);}
 uint64_t saved[4];memcpy(saved,counters,sizeof(saved));scheduler_current_slot=8;syscall_rax=15;
 for(unsigned n=0;n<6;n++)CHECK(probe_call(n));
 CHECK(!memcmp(saved,counters,sizeof(saved)));scheduler_current_slot=0;scheduler_mode=7;
 for(unsigned n=0;n<6;n++)CHECK(probe_call(n));
 CHECK(!memcmp(saved,counters,sizeof(saved)));puts("SHELL_SESSION_COLD_PROBES_OK");return 0;
}'''
        TaskFrameTests().build(asm,c,'SHELL_SESSION_COLD_PROBES')

    def test_diagnostic_untraced_transport(self):
        import run_qemu_x86_64_shell_session as session
        ns=session.diagnostic_untraced_namespace(12.5)
        self.assertEqual(ns['probe_started'],12.5)
        calls=[]
        ns['_capture']=lambda *args,**kwargs:calls.append((args,kwargs))
        ns['capture']('image','folder','detach\nquit 0\n',4096)
        self.assertEqual(calls,[(('image','folder','detach\nquit 0\n',4096),{'halt_witness':False})])
        for value in (-1,True,'12',float('inf'),float('nan')):
            with self.assertRaises(ValueError):session.diagnostic_untraced_namespace(value)

    def test_diagnostic_lifecycle_probe_scope(self):
        import struct
        import run_qemu_x86_64_shell_session as session
        from run_qemu_x86_64_session_admission import source_node
        body=session.diagnostic_observer_body(2)
        compile(body,'<diagnostic lifecycle transport>','exec')
        self.assertIn("for name in ('native_console_syscall64',):",body)
        self.assertIn("Hook('process_ipc_syscall64',diagnostic_flush)",body)
        self.assertNotIn("Hook('native_pio_syscall64'",body)
        class Hook:enabled=True
        raw=bytearray(8192);hook=Hook()
        ns=dict(S={'scheduler_tasks':100},mem=lambda address,size:bytes(raw),struct=struct,starts={},
                start_hook=hook)
        exec(compile(source_node(body,'diagnostic_start_scope'),'<real probe scope>','exec'),ns)
        ns['diagnostic_start_scope']();self.assertFalse(hook.enabled)
        for state in (1,2,6):
            struct.pack_into('<2Q',raw,3*1024,state,17)
            ns['diagnostic_start_scope']();self.assertTrue(hook.enabled)
            ns['starts'][17]={};ns['diagnostic_start_scope']();self.assertFalse(hook.enabled)
            ns['starts'].clear()
        for version in (False,True,0,3,'2'):
            with self.assertRaises(ValueError):session.diagnostic_observer_body(version)

    def test_diagnostic_pio_probe_scope(self):
        import run_qemu_x86_64_shell_session as session
        original=session.observer_body(cold=False)
        probe=session.diagnostic_observer_body()
        expected=original.replace("'process_ipc_syscall64','native_pio_syscall64','process_run_syscall64.exit'",
                                  "'process_ipc_syscall64','native_pio_apply64.bind','native_pio_apply64.fence_request','process_run_syscall64.exit'")
        self.assertNotEqual(original,expected)
        self.assertEqual(probe,expected)
        compile(probe,'<diagnostic cold PIO observation>','exec')
        # No callback, field, oracle or physical/CPU record is discarded.
        self.assertEqual(probe.count("Hook('native_pio_finish64.trace_before_clear',pio_before_clear)"),1)
        self.assertEqual(probe.count("Hook('native_cpu_trace_after64.full',cpu_trace_full)"),1)
        with patch.object(session,'observer_body',return_value='wrong observer'):
            with self.assertRaises(ValueError):session.diagnostic_observer_body()

    def test_terminal_historical_projection_and_mutations(self):
        import verify_x86_64_terminal as terminal
        actual_read=Path.read_text
        names=terminal.default_sources()
        self.assertEqual(len(names),9)
        for revision in ('f05fcc86','69282e76','f7566ac3',None):
            def source(path,*args,**kwargs):
                name=path.relative_to(ROOT).as_posix()
                if revision and name in names:
                    return subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT,timeout=10).decode().replace('\r\n','\n')
                return actual_read(path,*args,**kwargs)
            with patch.object(Path,'read_text',source):
                self.assertEqual(terminal.default_sources(),names)
            for target in names:
                def altered(path,*args,**kwargs):
                    result=source(path,*args,**kwargs)
                    return result+'\nUNEXPECTED_DEFAULT_CHANGE\n' if path==ROOT/target else result
                with patch.object(Path,'read_text',altered),self.assertRaises(ValueError):
                    terminal.default_sources()
        name='scripts/build-x86_64-bootstrap.ps1'
        for token in ('    [switch]$NativeShellSession,\n','    [switch]$NativeSession,\n',
                      '    [switch]$NativeTerminal,\n',"        throw 'NativeShellSession excludes finite shell and device-free session fixtures.'\n"):
            for replacement in ('',token+token):
                def malformed(path,*args,**kwargs):
                    result=actual_read(path,*args,**kwargs)
                    return result.replace(token,replacement) if path==ROOT/name else result
                with patch.object(Path,'read_text',malformed),self.assertRaises(ValueError):
                    terminal.default_sources()

    def test_composed_storage_raw_proof_and_mutations(self):
        import struct,types
        import run_qemu_x86_64_shell_session as session
        app=b'file bytes'*10;disk=session.file.media.image('fat12',program=app);events=[]
        reader=types.SimpleNamespace(read=lambda raw,size=None:raw if size is None or len(raw)==size else self.fail('snapshot extent'))
        for run in (1,2):
            root=run*10;driver=root+2;fs=root+3;owner=(driver<<32)|2;parser=(fs<<32)|3;sequence=0
            for slot,gen in ((0,root),(2,driver),(3,fs)):
                events.append(dict(kind='start',run=run,slot=slot,gen=gen,parent=0 if not slot else root<<32,
                                   args=['00000001','00000000'] if slot else []))
            state=(owner,owner^0xffffffffffffffff,0,0,1,0,0,0)
            def physical(kind,fields,data=b''):
                nonlocal sequence
                sequence+=1;record=bytearray(192);struct.pack_into('<2Q8Q',record,0,kind,sequence,*state)
                if kind==1:struct.pack_into('<5Q',record,80,*fields)
                else:
                    struct.pack_into('<4IQ4I3Q',record,80,*fields);record[144:176]=data;struct.pack_into('<Q',record,176,16)
                raw=bytearray(12304);struct.pack_into('<2Q',raw,0,sequence,0)
                offset=16+((sequence-1)&63)*192;raw[offset:offset+192]=record
                events.append(dict(kind='pio',run=run,previous=sequence-1,raw=bytes(raw)))
            def port(address,value,is_root=False):physical(1,(address,value,0 if is_root else 2,root if is_root else driver,root<<32))
            def data(raw):
                for n in range(0,512,32):physical(2,(2,64,4,0,owner,0x1f0,0,16,0,0x100000,100,0),raw[n:n+32])
            def sector():
                for address,value in ((0x1f2,1),(0x1f3,0),(0x1f4,0),(0x1f5,0),(0x1f6,0xe0),(0x1f7,0x20)):port(address,value)
                data(disk[:512])
            def call(slot,gen,payload,size=140):
                raw=struct.pack('<3I',1 if size==140 else 2,size,len(payload))+payload+bytes(size-12-len(payload))
                row=dict(kind='call',run=run,slot=slot,gen=gen,op=53,args=[1,100,100,0,0,0],profile_denied=False,
                         before=raw.hex(),size=size,entered=10)
                events.append(row);return raw
            def control(phase):
                return struct.pack('<3Q4IiI',owner if phase<3 else parser,parser if phase<3 else owner,
                                   0 if phase==1 else 2000,0 if phase==1 else 5,0 if phase==1 else 6,
                                   0 if phase==1 else 2880,phase,0,0)
            call(0,root,control(1));port(0x3f6,6,True);port(0x3f6,2);port(0x1f7,0xec)
            ident=bytearray(512);struct.pack_into('<H',ident,98,512);struct.pack_into('<I',ident,120,2880);data(bytes(ident));sector()
            message=call(2,driver,control(2));service=bytearray(128)
            struct.pack_into('<2Q',service,0,owner,1);struct.pack_into('<3I',service,24,2880,0,1)
            struct.pack_into('<4IQ',service,104,1,24,16,0,2000)
            events.append(dict(kind='service_ready',slot=2,gen=driver,run=run,control=message.hex(),raw=bytes(service)))
            call(0,root,control(3))
            block=struct.pack('<4I4QIiQ',1,64,1,0,owner,1,0,900,512,0,0)
            call(3,fs,block);sector()
            call(2,driver,struct.pack('<4I4QIiQ',1,64,1,1,owner,1,0,900,512,0,0)+disk[:512],2060)
            message=call(3,fs,control(4));service=bytearray(8400)
            struct.pack_into('<4I3Q',service,0,1,40,1,2880,parser,owner,2000)
            struct.pack_into('<2Q',service,40,owner,1);struct.pack_into('<5I',service,120,0,2,0,0,1)
            events.append(dict(kind='service_ready',slot=3,gen=fs,run=run,control=message.hex(),raw=bytes(service)))
            frame=bytearray(512);struct.pack_into('<6I',frame,0,1,512,7,0,1,0);frame[28]=47
            call(0,root,struct.pack('<4I4QIiQ',1,64,7,0,parser,1,900,0,512,0,0)+frame,2060)
            status,answer=session.fs_expected_response(bytes(frame),0,app)
            call(3,fs,struct.pack('<4I4QIiQ',1,64,7,1,parser,1,900,0,512,status,0)+answer,2060)
            for slot,gen in ((3,fs),(2,driver),(0,root)):
                if slot==2:events.append(dict(kind='fenced',slot=2,gen=driver,pio=struct.pack('<8Q',owner,owner^0xffffffffffffffff,1,0,1,0,0,0).hex()))
                events.append(dict(kind='release',slot=slot,gen=gen))
            events.extend([dict(kind='pio_end',run=run,sequence=sequence),dict(kind='pio_clear',run=run,raw=bytes(12304))])
        self.assertEqual(session.validate_storage(events,reader,0,app,0)['devices'],2)
        for kind,field in (('pio','raw'),('service_ready','raw')):
            bad=copy.deepcopy(events);row=next(r for r in bad if r['kind']==kind);data=bytearray(row[field]);data[0]^=1;row[field]=bytes(data)
            with self.assertRaises((AssertionError,ValueError)):session.validate_storage(bad,reader,0,app,0)
        bad=copy.deepcopy(events);row=next(r for r in bad if r['kind']=='call' and r['slot']==3 and r['size']==2060 and len(session.ipc_message(bytes.fromhex(r['before'])))==576)
        data=bytearray.fromhex(row['before']);data[76+476]^=1;row['before']=data.hex()
        with self.assertRaises(ValueError):session.validate_storage(bad,reader,0,app,0)

    def test_actual_session_capture_bounds_and_old_profile_projection(self):
        import io,types
        from unittest.mock import Mock
        import run_qemu_x86_64_shell_session as session
        import verify_x86_64_shell_session as verifier
        self.assertEqual(set(verifier.default_projection()),{
            'arch/x86_64/proc/cooperative_scheduler.asm','arch/x86_64/proc/process_run.inc',
            'arch/x86_64/proc/task_family.inc','arch/x86_64/kernel/bootstrap_core.c',
            'userspace/sdk/lib/x86_64/shell_platform.c','userspace/storage/lib/vfs_shadow_ext2.c',
            'Makefile','scripts/build-x86_64-bootstrap.ps1'})
        folder=ROOT/'build/codex-agent/r83ay-shell-session/capture-host'/uuid.uuid4().hex;folder.mkdir(parents=True)
        class Process:
            def __init__(self):self.returncode=None;self.stdin=io.BytesIO();self.stdout=io.BytesIO()
            def poll(self):return self.returncode
            def wait(self,timeout):self.returncode=0;return 0
        class Feeder:
            def __init__(self,_):self.sent=[{},{}];self.chunks=[]
            def pump(self,*_):pass
        for size,finish in ((65537,144),(8*1024*1024,145),(8*1024*1024+1,144),(65537,146)):
            out=folder/f'{size}-{finish}';out.mkdir();(out/'frame-trace.log').write_bytes(b'x'*size)
            vm,debug=Process(),Process();output=Mock();output.get.return_value=session.BANNER.encode()
            output.get_nowait.side_effect=session.boot.queue.Empty;output.empty.return_value=True
            ns=session.capture_namespace(100);ns['ConsoleFeeder']=Feeder;ns['resolve_qemu']=lambda _:Path('qemu.exe')
            ns['terminate_bounded']=lambda p:setattr(p,'returncode',0)
            with patch.object(session.boot.subprocess,'Popen',side_effect=[vm,debug]),patch.object(session.boot.queue,'Queue',return_value=output),\
                 patch.object(session.boot.threading,'Thread'),patch.object(session.time,'monotonic',side_effect=[100,101,102,142,143,finish]):
                call=lambda:ns['_capture_run'](folder/'image.elf',out,'code',4096,('media',),service_pio_budget=True,console_input=session.input_plan(0))
                if finish>145 or size>8*1024*1024:
                    with self.assertRaises(ValueError):call()
                else:
                    serial,trace=call();self.assertEqual(serial,session.BANNER);self.assertEqual(len(trace),size)
            self.assertEqual(output.get.call_count,1);self.assertTrue(vm.stdin.closed and vm.stdout.closed)
        for now in (99,142,150):
            with patch.object(session.time,'monotonic',return_value=now):
                with self.assertRaises(ValueError):session.capture_namespace(100)['session_origin']()
        for started,timeout in ((90,10),(60,5),(54,None)):
            out=folder/f'media-{started}';out.mkdir()
            with patch.object(session.time,'monotonic',return_value=100),patch.object(session.file.pio.subprocess,'run',
                    return_value=types.SimpleNamespace(returncode=0,stdout='',stderr='')) as run:
                if timeout is None:
                    with self.assertRaises(ValueError):session.bounded_fixture(out,2,b'a'*64,started)
                    run.assert_not_called()
                else:
                    session.bounded_fixture(out,2,b'a'*64,started)
                    self.assertEqual(run.call_args.kwargs['timeout'],timeout)
                    self.assertEqual(run.call_count,1)

    def test_foreground_io_and_timeout_outcome_oracle(self):
        import struct
        import run_qemu_x86_64_shell_session as session
        for case in (0,6,12,13,14,15,16,17):
            events=[];receipts={};policies={};attempts={};faults=[]
            for run in (1,2):
                root=run*100;count=4 if case==6 and run==1 else 0 if case==16 and run==1 else 1
                events.append(dict(kind='start',slot=0,gen=root,run=run,now=0))
                policies[root]=(0,0,0,0,0,0,2,1) if case==16 and run==1 else (0,)*8
                attempts[root]=12 if case==6 and run==1 else 3
                def io(gen,slot,op,data,now=0):
                    return dict(kind='io',gen=gen,slot=slot,op=op,run=run,fd=int(op==20),unused=[0,0,0],
                        size=len(data),result=len(data),before=(bytes(len(data)) if op==15 else data).hex(),after=data.hex(),now=now)
                data=b''.join(data for _,data in session.input_plan(case)[run-1])
                events.append(io(root,0,15,data,5000 if case==6 and run==1 else 0))
                events.append(io(root,0,20,session.BANNER.encode()))
                for n in range(count):
                    gen=root+10+n;events.append(dict(kind='start',slot=4,gen=gen,run=run,parent=root<<32))
                    status,state=(134,3) if case==12 and run==1 else (256,3) if case==13 and run==1 else (0,3) if case in (14,15) and run==1 else (82,4)
                    receipts[gen]=dict(status=status,state=state)
                    if status==82:events.append(io(gen,4,20,b'SESSION64\n'))
                    if case==12 and run==1:faults.append(dict(slot=4,gen=gen,run=run))
                    if case==15 and run==1:continue
                    reason=0 if state==4 else 2 if case==14 and run==1 else 1
                    for op,result in ([(2,-110),(3,0),(2,reason<<32|status)] if case==14 and run==1 else [(2,reason<<32|status)]):
                        request=struct.pack('<4I6Q',1,64,op,0,(gen<<32)|4,0,1000 if op==2 else 0,0,0,0)
                        events.append(dict(kind='return',op=132,gen=root,before=request.hex(),result=result))
                    events.append(dict(kind='return',op=114,gen=root,args=[10,gen,0,0,0,0],result=-3))
                    events.append(dict(kind='return',op=127,gen=root,before=struct.pack('<6I',1,24,2,0,gen,gen).hex(),result=-116))
                if run==1 and case==15:faults.append(dict(slot=0,gen=root,run=run))
                if run==1 and case==16:
                    for gen in range(root+20,root+23):
                        events.append(dict(kind='start',slot=3,gen=gen,run=run,parent=root<<32,args=['00000001','00000201']))
                        for op in (15,20):events.append(dict(kind='io',slot=3,gen=gen,op=op,profile_denied=True,result=-13,size=0,before='',after=''))
                        receipts[gen]=dict(status=134,state=3);faults.append(dict(slot=3,gen=gen,run=run))
                if run==1 and case==17:
                    events.extend([dict(kind='oom',run=1,slot=3,acquired=3,free=17),dict(kind='rollback',run=1,slot=3,before=20,free=20),
                                   dict(kind='return',op=132,gen=root,before=struct.pack('<4I6Q',6,80,1,0,*([0]*6)).hex(),result=-12)])
            session.validate_io_and_faults(events,receipts,case,attempts,policies,faults)
            bad=copy.deepcopy(events);next(r for r in bad if r['kind']=='io')['after']='00'
            with self.assertRaises(ValueError):session.validate_io_and_faults(bad,receipts,case,attempts,policies,faults)
            bad=copy.deepcopy(receipts);next(iter(bad.values()))['status']=5
            with self.assertRaises(ValueError):session.validate_io_and_faults(events,bad,case,attempts,policies,faults)
            bad=copy.deepcopy(policies);bad[100]=(0,)*6+(3,0)
            with self.assertRaises(ValueError):session.validate_io_and_faults(events,receipts,case,attempts,bad,faults)

    def test_physical_storage_stream_and_generation_oracle(self):
        import struct
        import run_qemu_x86_64_shell_session as session
        for layout in range(5):
            ns=session.physical_oracle(layout,bytes(range(256))*3)
            owner=(9<<32)|2;parent=7<<32
            state=(owner,owner^0xffffffffffffffff,0,0,1,0,0,0)
            def output(port,value,root=False):
                return (1,1,state,(port,value,0 if root else 2,7 if root else 9,parent),b'',0)
            def read(data):
                return (2,1,state,(2,64,4,0,owner,0x1f0,0,16,0,0x100000,100,0),data,16)
            ns['out'](output(0x3f6,6,True));ns['out'](output(0x3f6,2))
            with self.assertRaises(AssertionError):ns['out'](output(0x1f7,0x30))
            ns['out'](output(0x1f7,0xec))
            ident=bytearray(512);struct.pack_into('<H',ident,98,512);struct.pack_into('<I',ident,120,ns['CONFIG']['sectors'])
            for n in range(0,512,32):ns['data'](read(bytes(ident[n:n+32])))
            for lba in (0,1):
                for port,value in ((0x1f2,1),(0x1f3,lba),(0x1f4,0),(0x1f5,0),(0x1f6,0xe0)):
                    ns['out'](output(port,value))
                ns['out'](output(0x1f7,0x20));sector=ns['expected_sector'](lba)
                broken=bytearray(sector[:32]);broken[0]^=1
                with self.assertRaises(AssertionError):ns['data'](read(bytes(broken)))
                for n in range(0,512,32):ns['data'](read(sector[n:n+32]))
            self.assertEqual(bytes(ns['devices'][owner]['data']),ns['expected_sector'](0)+ns['expected_sector'](1))
            ns['devices'][owner]['retired']=True
            with self.assertRaises(AssertionError):ns['data'](read(bytes(32)))
            with self.assertRaises(AssertionError):ns['out'](output(0x1f7,0x20))

    def test_complete_ipc_and_immutable_file_response_oracles(self):
        import struct
        import run_qemu_x86_64_shell_session as session
        app=bytes(range(256))*4+b'last'
        for layout in range(5):
            requests=session.file.frames(layout,app)
            answers=session.file.frames(layout,app,True)
            for request,answer in zip(requests,answers):
                self.assertEqual(session.fs_expected_response(request,layout,app),(0,answer))
                for offset in (0,4,12,20,511):
                    bad=bytearray(request);bad[offset]^=1
                    with self.assertRaises(ValueError):session.fs_request_frame(bytes(bad))
            frame=bytearray(512);struct.pack_into('<6I',frame,0,1,512,7,0,1,0);frame[28]=47
            status,result=session.fs_expected_response(bytes(frame),layout,app)
            self.assertEqual(status,0);self.assertEqual(struct.unpack_from('<2I',result,476),(1,len(app)))
            struct.pack_into('<I',frame,24,1)
            status,result=session.fs_expected_response(bytes(frame),layout,app)
            self.assertEqual(status,1);self.assertFalse(any(result[220:]))
        for size,version in ((140,1),(2060,2)):
            payload=b'actual message';raw=struct.pack('<3I',version,size,len(payload))+payload+bytes(size-12-len(payload))
            self.assertEqual(session.ipc_message(raw),payload)
            for offset in (0,4,8,size-1):
                bad=bytearray(raw);bad[offset]^=128
                if offset==8:struct.pack_into('<I',bad,8,size)
                with self.assertRaises(ValueError):session.ipc_message(bytes(bad))
            receive=struct.pack('<3I',version,size,size-12)+bytes(size-12)
            send=dict(kind='call',gen=7,op=53,args=[11,100,50,0,0,0],profile_denied=False,before=raw.hex())
            read=dict(kind='call',gen=8,op=54,args=[11,200,50,0,0,0],profile_denied=False,before=receive.hex())
            returned=dict(read,kind='return',result=0,after=raw.hex())
            sent=dict(send,kind='return',result=0,after=raw.hex())
            for rows in ([send,read,sent,returned],[read,send,returned,sent]):
                self.assertEqual(tuple(map(len,session.validate_ipc_delivery(rows))),(1,1))
                for field,value in (('args',[12,200,50,0,0,0]),('after',receive.hex())):
                    bad=copy.deepcopy(rows);bad[bad.index(returned)][field]=value
                    with self.assertRaises(ValueError):session.validate_ipc_delivery(bad)
                bad=copy.deepcopy(rows);bad[bad.index(sent)]['result']=-110
                with self.assertRaises(ValueError):session.validate_ipc_delivery(bad)
            failure=dict(read,kind='return',result=-110,after=receive.hex())
            self.assertEqual(session.validate_ipc_delivery([read,failure]),([],[]))
            with self.assertRaises(ValueError):session.validate_ipc_delivery([read,dict(failure,after=raw.hex())])

    def test_freestanding_units_and_real_file_elf_capacity(self):
        import build_x86_64_boot_programs as producer
        folder=ROOT/'build/codex-agent/r83ay-shell-session/freestanding'/uuid.uuid4().hex;folder.mkdir(parents=True)
        zig=str(find_zig());flags=['-DREIST_NATIVE_LIVE_FILE=1','-DREIST_NATIVE_TERMINAL=1','-DREIST_NATIVE_SHELL_SESSION=1']
        raw=producer.build_file_program(folder,[zig,'cc',*flags],['C:/tools/nasm-3.02/nasm.exe'],[zig,'ld.lld'])
        self.assertLessEqual(len(raw),1280);self.assertLessEqual(1+(len(raw)+255)//256+1,8)
        prepared=producer.prepare(raw,[],True)
        self.assertIn(b'SESSION64\n',prepared);self.assertEqual(sum(p==5 for p in prepared[24:88]),1)
        for name in ('service_session','shell_platform'):
            obj=folder/(name+'.o')
            command=[zig,'cc','-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
                '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
                '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2',
                '-Iuserspace/sdk/include','-Iuserspace/storage/include',*flags,'-c','userspace/sdk/lib/x86_64/'+name+'.c','-o',str(obj)]
            env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
            result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-2000:])
            symbols=subprocess.run(['nm','-u',str(obj)],cwd=ROOT,capture_output=True,timeout=10,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'-undefined.log')).write_bytes(symbols.stdout+symbols.stderr)
            self.assertEqual(symbols.returncode,0,symbols.stderr)
            undefined={line.split()[-1] for line in symbols.stdout.decode().splitlines()}
            self.assertFalse(undefined&{'memcpy','memmove','memset','malloc','free','__stack_chk_fail'},undefined)

    def test_actual_raw_cpu_identity_terminal_and_policy_oracles(self):
        import run_qemu_x86_64_shell_session as session
        import struct
        starts={7:dict(kind='start',gen=7,slot=0,parent=0,run=1),
                8:dict(kind='start',gen=8,slot=1,parent=0,run=1),
                9:dict(kind='start',gen=9,slot=4,parent=7<<32,run=1)}
        authority=bytearray(8704)
        for gen,entry in starts.items():
            slot=entry['slot'];struct.pack_into('<2Q',authority,slot*1024,2 if slot==0 else 1,gen)
            struct.pack_into('<2Q',authority,8192+slot*64,(gen<<32)|slot,entry['parent'])
            struct.pack_into('<Q',authority,8192+slot*64+40,1 if slot<2 else 2)
        actual,live=session.authority_state(bytes(authority))
        self.assertEqual(live,{7,8,9});self.assertEqual(actual[9]['parent'],7<<32)
        for offset in (8192,8192+64+40,8192+4*64+8):
            bad=bytearray(authority);bad[offset]^=1
            with self.assertRaises(ValueError):session.authority_state(bytes(bad))
        for pid,result in ((7,0),(8,-13),(9,0),(10,-3)):
            row=dict(slot=0,gen=7,profile_denied=False,size=16,args=[123,pid,0,0,0,0],before='a5'*16,
                after=struct.pack('<4I',1,16,pid,pid).hex() if not result else 'a5'*16,result=result)
            session.validate_identity(row,starts,set(starts))
            for key,value in (('result',-5),('after','00'*16),('slot',1),('args',[123,pid,1,0,0,0])):
                with self.assertRaises(ValueError):session.validate_identity(dict(row,**{key:value}),starts,set(starts))
        root=7<<32;child=(9<<32)|4
        for slot,gen,operation,pid,before,after,result in (
            (0,7,2,9,(root,0,0),(root,child,0),0),(0,7,2,8,(root,0,0),(root,0,0),-13),
            (0,7,2,10,(root,0,0),(root,0,0),-116),(4,9,5,0,(root,0,0),(root,0,0),-11),
            (4,9,3,0,(root,child,0),(root,0,0),0),(0,7,5,0,(root,child,0),(root,child,0),-11)):
            request=struct.pack('<6I',1,24,operation,0,pid,pid).hex()
            row=dict(op=127,slot=slot,gen=gen,profile_denied=False,size=24,args=[123,0,0,0,0,0],
                before=request,after=request,terminal_before=struct.pack('<3Q',*before).hex(),
                terminal=struct.pack('<3Q',*after).hex(),result=result)
            session.validate_terminal(row,starts,set(starts))
            for key,value in (('result',-5),('after','00'*24),('terminal','00'*24)):
                with self.assertRaises(ValueError):session.validate_terminal(dict(row,**{key:value}),starts,set(starts))
        raw=struct.pack('<2I8Q6I',1,96,7,150,100,100,3,2,1,0,3,2,1,0,0,0)
        service=struct.pack('<4I9Q4I',1,104,0,2,7,*([0]*12))
        row=dict(gen=7,now=150,policy=raw.hex(),service=service.hex())
        state=session.validate_policy(row,None)
        for offset,value in ((0,2),(8,8),(72,4097),(76,1025),(80,16385),(84,3),(88,2),(92,1)):
            damaged=bytearray(raw);struct.pack_into('<I',damaged,offset,value)
            with self.assertRaises(ValueError):session.validate_policy(dict(row,policy=damaged.hex()),None)
        with self.assertRaises(ValueError):session.validate_policy(row,tuple(n+1 for n in state))
        for exhausted in (False,True):
            gen=9 if exhausted else 7;slot=4 if exhausted else 0
            before=[gen,32,0,0,0 if exhausted else 100,0,0,0]
            events=[starts[gen],dict(kind='cpu_start',gen=gen,slot=slot,now=0,records=before)]
            for now in range(1,33 if exhausted else 2):
                after,result=session.admission.cpu.charge_result(before,now)
                events.append(dict(kind='cpu_charge',gen=gen,slot=slot,now=now,before=before,after=after,result=result));before=after
            events.extend([dict(kind='cpu_final',gen=gen,slot=slot,now=33,records=before),dict(kind='release',gen=gen)])
            receipts={gen:dict(slot=slot,ticks=32 if exhausted else 1,status=256 if exhausted else 0,state=3 if exhausted else 4)}
            session.validate_cpu(events,receipts)
            bad=copy.deepcopy(events);bad[2]['after'][2]+=1
            with self.assertRaises(ValueError):session.validate_cpu(bad,receipts)
            with self.assertRaises(ValueError):session.validate_cpu(events[:-1],receipts)

    def test_actual_observer_request_and_return_callbacks(self):
        import run_qemu_x86_64_shell_session as session
        import run_qemu_x86_64_session_admission as admission
        import struct
        body=session.observer_body();compile(body,'<AY complete generated observer>','exec')
        for op,bulk in ([(op,False) for op in (9,15,20,49,50,51,52,53,54,55,113,114,127,132)]+
                        [(op,True) for op in (50,51,53,54)]):
            with self.subTest(op=op,bulk=bulk):
                pointer=0x500000;size=64 if op==132 else 24 if op==127 else 16 if op==114 else 4 if op==49 else 140 if op in (50,51,53,54) else 1 if op in (15,20) else 0
                if bulk:size=2060
                if op==113:size=64
                args=[pointer,0,0,0,0,0]
                if op in (15,20):args=[int(op==20),pointer,1,0,0,0]
                elif op in (50,51,53,54):args=[17,pointer,1000,0,0,0]
                elif op in (52,55):args=[17,11 if op==55 else 0,3 if op==55 else 0,0,0,0]
                elif op==113:args=[29,pointer,0,0,0,0]
                state=[2,7]+[0]*126;state[85]=0
                values={'syscall_rax':op,'scheduler_last_tick':50}
                values.update(dict(zip(('syscall_rdi','syscall_rsi','syscall_rdx','syscall_r10','syscall_r8','syscall_r9'),args)))
                before=(struct.pack('<2I',2 if bulk else 1,size)+bytes(size-8)) if size>=8 else bytes(size)
                events=[];reads=[];pending={};written=[]
                def user(t,address,bytes_):
                    self.assertIs(t,state);reads.append((address,bytes_))
                    if address in (100,200):return bytes(bytes_)
                    self.assertEqual(address,pointer);self.assertLessEqual(bytes_,size);return before[:bytes_]
                class GDB:
                    @staticmethod
                    def write(text):written.append(text)
                class ResultHook:enabled=False
                ns=dict(S={name:name for name in (*values,'scheduler_current_slot','native_terminal_state','native_pio_state','scheduler_tasks','family_records')},
                    CONFIG=dict(policy=100,service=200),mode=lambda:8,d=lambda _:0,q=lambda name:values[name],
                    task=lambda _:state,starts={7:dict(live=True)},pending=pending,user=user,struct=struct,
                    runs=0,emit=lambda kind,**row:events.append(dict(kind=kind,**row)),signed=lambda n:n-(1<<64) if n>>63 else n,
                    mem=lambda name,size:bytes(size),family=lambda:bytes(572),snapshot=lambda raw:raw.hex(),gdb=GDB,json=json,
                    resume_hook=ResultHook())
                for name in ('syscall','complete'):
                    exec(compile(admission.source_node(body,name),'<actual AY '+name+'>','exec'),ns)
                ns['syscall']();self.assertEqual(events[-1]['op'],op)
                self.assertEqual(events[-1]['before'],before.hex())
                self.assertEqual(bool(pending),op!=9)
                if op!=9:
                    with self.assertRaises(AssertionError):ns['syscall']()
                    state[85]=(1<<64)-11;ns['complete'](0,state);self.assertFalse(pending)
                    row=json.loads(written[-1][11:]) if op in (15,20) else events[-1]
                    self.assertEqual(row['result'],-11);self.assertEqual(row['before'],row['after'])
                    self.assertEqual(row['gen'],7);self.assertEqual(row['now'],500)
                if op in (52,55):self.assertFalse(reads)

    def test_old_producer_commands_remain_exact(self):
        sys.path.insert(0,str(ROOT/'test'))
        import test_x86_64_live_file as prior
        self.folder=ROOT/'build/codex-agent/r83ay-shell-session/producer'/uuid.uuid4().hex
        self.folder.mkdir(parents=True)
        code=textwrap.dedent(inspect.getsource(prior.LiveFileTests.test_old_producer_commands_exact_with_modeled_tool_outputs))
        self.assertEqual(code.count('c7e5e72a:scripts/build_x86_64_boot_programs.py'),1)
        code=code.replace('c7e5e72a:scripts/build_x86_64_boot_programs.py','f7566ac3:scripts/build_x86_64_boot_programs.py')
        anchor='    for index,profile in enumerate(profiles):'
        self.assertEqual(code.count(anchor),1)
        code=code.replace(anchor,"    live=dict(pio_profile,filesystem=True,file_launch=True,live_file=True)\n"
            "    profiles.extend([dict(console=True),dict(console=True,native_shell=True),live,dict(live,service_console=True),\n"
            "        dict(live,service_console=True,terminal=True),dict(base,task_pool=True,service_cpu=True,session=True)])\n"+anchor)
        ns=dict(vars(prior));exec(compile(code,'<AY old-producer command equivalence>','exec'),ns)
        ns['test_old_producer_commands_exact_with_modeled_tool_outputs'](self)

    def test_session_selectors_reject_before_effects(self):
        import build_x86_64_boot_programs as producer
        sys.path.insert(0,str(ROOT/'test'))
        from test_x86_64_file_launch import direct_make_plan
        folder=ROOT/'build/codex-agent/r83ay-shell-session/selectors'/uuid.uuid4().hex;folder.mkdir(parents=True)
        complete=dict(family=True,startup=True,import_image=True,pio=True,block=True,wide=True,
            block_profile=True,filesystem=True,file_launch=True,task_pool=True,pool_pio=True,
            live_file=True,service_console=True,terminal=True,shell_session=True)
        for delta in (dict(shell_session=1),dict(terminal=False),dict(service_console=False),
                      dict(session=True),dict(native_shell=True),dict(service_cpu=True)):
            with patch.object(producer.subprocess,'run',side_effect=AssertionError('early tool')):
                with self.assertRaises(ValueError):producer.build(folder/'absent',['cc'],['nasm'],['ld'],0,**dict(complete,**delta))
            self.assertFalse((folder/'absent').exists())
        options={'X86_64_NATIVE_'+name:'1' for name in ('TASK_POOL','POOL_PIO','LIVE_FILE','SERVICE_CONSOLE','TERMINAL','SHELL_SESSION')}
        good=direct_make_plan(folder,options);self.assertEqual(good.returncode,0,good.stderr)
        self.assertIn('--shell-session',good.stdout);self.assertIn('-DREIST_NATIVE_SESSION=1',good.stdout)
        self.assertIn('-DREIST_NATIVE_SHELL_SESSION=1',good.stdout)
        self.assertNotIn('--session ',good.stdout)
        for delta in ({'X86_64_NATIVE_SHELL_SESSION':'2'},{'X86_64_NATIVE_SHELL_SESSION':'1 0'},
                      {'X86_64_NATIVE_TERMINAL':'0'},{'X86_64_NATIVE_SESSION':'1'},{'X86_64_NATIVE_SHELL':'1'}):
            self.assertNotEqual(direct_make_plan(folder,dict(options,**delta)).returncode,0)
        for flag in ('-NativeShell','-NativeSession','-NativeConsole','-NativeServiceCPU'):
            target=folder/flag[1:]
            result=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-NativeShellSession',flag,'-OutputDirectory',target.relative_to(ROOT).as_posix()],
                cwd=ROOT,capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(flag[1:]+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertNotEqual(result.returncode,0);self.assertFalse(target.exists())

    def test_actual_ordinary_program_syscall_sequence(self):
        sys.path.insert(0,str(ROOT/'test'))
        from test_x86_64_task_frames import TaskFrameTests
        source=(ROOT/'arch/x86_64/user/shell_session_program.asm').read_text()
        # Execute the real program body; only the privileged transition is
        # modeled, preserving every argument register as the syscall ABI does.
        source=source.replace('global main','global fixture_main').replace('\nmain:', '\nfixture_main:')
        source=source.replace('    syscall','    call fixture_syscall')
        source=source[:source.index('section .note.GNU-stack')]+'''
section .bss
global unused_arguments
unused_arguments: resq 3
section .text
extern host_syscall
fixture_syscall:
    mov [rel unused_arguments],r10
    mov [rel unused_arguments+8],r8
    mov [rel unused_arguments+16],r9
    push rdi
    push rsi
    push rdx
    push r10
    push r8
    push r9
    sub rsp,8
    mov rcx,rdx
    mov rdx,rsi
    mov rsi,rdi
    mov rdi,rax
    call host_syscall
    add rsp,8
    pop r9
    pop r8
    pop r10
    pop rdx
    pop rsi
    pop rdi
    ret
'''
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int __attribute__((sysv_abi)) fixture_main(int,const char **);
extern uint64_t unused_arguments[3];
static unsigned mode,checks,sleeps,releases,writes,bytes;static char text[16];
#define CHECK(x) do {if(!(x)){printf("line %d mode %u\n",__LINE__,mode);exit(1);}}while(0)
int64_t __attribute__((sysv_abi)) host_syscall(uint64_t op,uint64_t a,uint64_t b,uint64_t c){
 CHECK(!(unused_arguments[0]|unused_arguments[1]|unused_arguments[2]));
 if(op==127){
  const uint32_t *q=(const void*)(uintptr_t)a;CHECK(!b && !c && q[0]==1 && q[1]==24 && !q[3] && !q[4] && !q[5]);
  if(q[2]==5){checks++;return checks<=2 || mode==1?-11:0;}
  CHECK(q[2]==3 && bytes==10);releases++;return 0;
 }
 if(op==41){CHECK(!b && !c && (a==50 || a==10 || a==100));sleeps++;return 0;}
 CHECK(op==20 && a==1 && c && c<=10);writes++;
 if(mode==2 || writes==1)return -11;
 unsigned count=c>3?3:(unsigned)c;CHECK(bytes+count<=sizeof(text));memcpy(text+bytes,(void*)(uintptr_t)b,count);bytes+=count;return count;
}
int main(void){
 for(mode=0;mode<4;mode++){
  checks=sleeps=releases=writes=bytes=0;memset(text,0,sizeof(text));
  const char *args[]={"boot.prg",mode==3?"c":0};int result=fixture_main(mode==3?2:1,args);
  CHECK(result==(mode==0?82:250));
  if(mode==0)CHECK(releases==1 && writes==5 && sleeps==3 && !strcmp(text,"SESSION64\n"));
  if(mode==1)CHECK(checks==20 && sleeps==20 && !writes && !releases);
  if(mode==2)CHECK(writes==20 && sleeps==22 && !bytes && !releases);
  if(mode==3)CHECK(sleeps==22 && !writes && !releases);
 }
 puts("SHELL_SESSION_PROGRAM_OK");return 0;
}'''
        TaskFrameTests().build(source,c,'SHELL_SESSION_PROGRAM')

    def test_actual_bounded_session_feeder(self):
        import run_qemu_x86_64_shell_session as session
        session.capture_namespace() # Exact transformations must still resolve.
        for case in range(18):
            plan=session.input_plan(case);feeder=session.SessionFeeder(plan);trace='';elapsed=0.0
            for run,gen in ((1,7),(2,37)):
                trace+='SHELL_SESSION '+json.dumps(dict(kind='start',slot=0,gen=gen,run=run,now=100))+'\n'
                def io(op,raw,now,result=None):
                    return 'CONSOLE_IO '+json.dumps(dict(run=run,slot=0,gen=gen,now=now,
                        op=op,fd=int(op==20),unused=[0,0,0],size=len(raw),result=len(raw) if result is None else result,
                        before=(raw if op==20 else bytes(len(raw))).hex(),after=raw.hex()))+'\n'
                trace+=io(20,session.BANNER.encode(),100)
                # An echoed banner alone must never authorize host input.
                probe=session.SessionFeeder(plan);probe.pump(session.BANNER,'',lambda _:self.fail('serial trusted'),0)
                feeder.pump('',trace,lambda _:self.fail('missing first prompt'),elapsed)
                trace+=io(20,b'C:\\>',100)
                for due,part in plan[run-1]:
                    now=100+due;trace+=io(15,b'\0',now,-11)
                    offset=0
                    while offset<len(part):
                        sent=[];elapsed+=.01
                        end=min(offset+8,part.index(b'\n',offset)+1)
                        feeder.pump('',trace,lambda raw:sent.append(raw) or len(raw),elapsed)
                        self.assertEqual(sent,[part[offset:end]])
                        feeder.pump('',trace,lambda _:self.fail('unacknowledged repeat'),elapsed)
                        trace+=io(15,sent[0],now)
                        offset=end
                        if sent[0].endswith(b'\n'):
                            feeder.pump('C:\\>',trace,lambda _:self.fail('RX newline is not next prompt'),elapsed)
                            trace+=io(20,b'C:\\',now)
                            feeder.pump('',trace,lambda _:self.fail('partial prompt'),elapsed)
                            trace+=io(20,b'>',now)
            session.SessionFeeder.validate(plan,trace,feeder.chunks,feeder.sent)
            # The live reader uses universal newlines on Windows. Persisted
            # byte limits/hash evidence stay raw, but prefix offsets are text.
            for encoded in (trace.encode('ascii'),trace.replace('\n','\r\n').encode('ascii')):
                normalized=session.capture_text(encoded)
                self.assertEqual(normalized,trace)
                session.SessionFeeder.validate(plan,normalized,feeder.chunks,feeder.sent)
                corrupt=copy.deepcopy(feeder.chunks);corrupt[0]['trace_bytes']-=1
                with self.assertRaises(ValueError):session.SessionFeeder.validate(plan,normalized,corrupt,feeder.sent)
            for bad in (trace.replace('"gen": 7','"gen": 8',1),trace.replace('"fd": 1','"fd": 0',1),
                        trace.replace('"unused": [0, 0, 0]','"unused": [0, 1, 0]',1)):
                with self.assertRaises(ValueError):session.SessionFeeder.validate(plan,bad,feeder.chunks,feeder.sent)
            bad=copy.deepcopy(feeder.chunks);bad[0]['acknowledged']=1
            with self.assertRaises(ValueError):session.SessionFeeder.validate(plan,trace,bad,feeder.sent)
            feeder.pump('',trace,lambda _:self.fail('completed plan repeat'),elapsed)
            with self.assertRaises(ValueError):feeder.pump('',trace,lambda _:0,42)
            with self.assertRaises(ValueError):feeder.pump('',trace[:-100],lambda _:0,elapsed)
        for case in (-1,18,True,'0'):
            with self.assertRaises(ValueError):session.input_plan(case)
        for bad in (None,(),(b'fake',b'fake'),(((False,b'pwd\npath\nboot\nhistory\nexit\n'),),session.HEALTHY)):
            with self.assertRaises(ValueError):session.SessionFeeder(bad)

    def test_actual_normal_shell_and_session_platform(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ay-shell-session/platform'/uuid.uuid4().hex;folder.mkdir(parents=True)
        for opt in ('O0','O2'):
            exe=folder/(opt+'.exe')
            command=['gcc','-std=c11','-'+opt,'-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',
                '-Iuserspace/sdk/include','-Iuserspace/storage/include','test/x86_64_shell_session_host.c',
                'userspace/bin/shell_vfs.c','userspace/sdk/lib/x86_64/service_session.c',
                'userspace/sdk/lib/x86_64/file_image.c','userspace/sdk/lib/x86_64/image.c',
                *['userspace/storage/lib/'+name+'.c' for name in ('native_filesystem','native_block','vfs_shadow_fat32','vfs_shadow_ext2')],
                '-Wl,--gc-sections','-o',str(exe)]
            for n,args in enumerate([command,*[[str(exe),str(mode)] for mode in range(18)]]):
                r=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60 if n==0 else 5,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/f'{opt}-{n}.log').write_bytes(r.stdout+r.stderr)
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-3500:])
                if n:self.assertIn(b'SHELL_SESSION_PLATFORM_OK',r.stdout)

    def test_actual_identity_syscall_publication(self):
        sys.path.insert(0,str(ROOT/'test'))
        from test_x86_64_task_frames import TaskFrameTests
        asm='''BITS 64
%define REIST_NATIVE_SHELL_SESSION 1
TASK_GENERATION equ 8
TASK_STATE equ 0
TASK_READY equ 1
TASK_RUNNING equ 2
TASK_BLOCKED equ 6
NATIVE_TASK_SHIFT equ 10
NATIVE_POOL_TASKS equ 8
PF_W equ 2
section .bss
global scheduler_tasks,family_records,scheduler_current_slot
global syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9
scheduler_tasks: resb 8192
family_records: resb 512
scheduler_current_slot: resq 1
syscall_rdi: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
section .text
global identity_call
extern identity_range
identity_call:
    sub rsp,8
    call native_identity_syscall64
    add rsp,8
    ret
scheduler_validate_shell_range64:
    mov rdi,rax
    mov esi,edx
    mov edx,ecx
    jmp identity_range
process_run_resume64: ret
scheduler_fail: mov rax,-117
    ret
%include "arch/x86_64/proc/native_identity.inc"
'''
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t scheduler_tasks[8][128],family_records[8][8],scheduler_current_slot;
extern uint64_t syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9;
extern int64_t __attribute__((sysv_abi)) identity_call(void);
static unsigned char output[32],saved[32];static unsigned extent=16,checks;
int __attribute__((sysv_abi)) identity_range(uint64_t pointer,unsigned bytes,unsigned flags){
 ++checks;return pointer==(uintptr_t)output+8 && bytes==16 && flags==2 && extent>=bytes;
}
#define CHECK(x) do {if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
static int unchanged(int expected){
 memset(output,0xa5,sizeof(output));memcpy(saved,output,sizeof(output));
 return identity_call()==expected && !memcmp(output,saved,sizeof(output));
}
int main(void){
 scheduler_tasks[0][0]=2;scheduler_tasks[0][1]=7;
 family_records[0][0]=7ULL<<32;family_records[0][5]=1;
 scheduler_tasks[2][0]=6;scheduler_tasks[2][1]=9;
 family_records[2][0]=(9ULL<<32)|2;family_records[2][1]=7ULL<<32;family_records[2][5]=2;
 syscall_rdi=(uintptr_t)output+8;
 for(unsigned n=0;n<3;n++){
  syscall_rsi=n==0?0:n==1?7:9;memset(output,0xa5,sizeof(output));
  CHECK(!identity_call());uint32_t wanted[4]={1,16,n==2?9:7,n==2?9:7};
  CHECK(!memcmp(output+8,wanted,16));
  for(unsigned i=0;i<8;i++)CHECK(output[i]==0xa5 && output[24+i]==0xa5);
 }
 for(unsigned n=0;n<16;n++){extent=n;CHECK(unchanged(-14));}extent=16;
 syscall_rdi=0;checks=0;CHECK(unchanged(-22) && !checks);
 syscall_rdi=(uintptr_t)output+9;CHECK(unchanged(-14));syscall_rdi=(uintptr_t)output+8;
 uint64_t *unused[]={&syscall_rdx,&syscall_r10,&syscall_r8,&syscall_r9};
 for(unsigned n=0;n<4;n++){*unused[n]=1;checks=0;CHECK(unchanged(-22) && !checks);*unused[n]=0;}
 syscall_rsi=0x80000000;checks=0;CHECK(unchanged(-22) && !checks);
 syscall_rsi=9;scheduler_current_slot=1;CHECK(unchanged(-13) && !checks);scheduler_current_slot=0;
 family_records[2][1]=8ULL<<32;CHECK(unchanged(-13));family_records[2][1]=7ULL<<32;
 syscall_rsi=10;CHECK(unchanged(-3));syscall_rsi=9;
 scheduler_tasks[2][0]=4;CHECK(unchanged(-3));scheduler_tasks[2][0]=6;
 family_records[2][0]^=1;CHECK(unchanged(-117));
 puts("SHELL_SESSION_IDENTITY_ADAPTER_OK");return 0;
}'''
        TaskFrameTests().build(asm,c,'SHELL_SESSION_IDENTITY_ADAPTER')

    def test_actual_identity_lookup_authority_and_generation(self):
        sys.path.insert(0,str(ROOT/'test'))
        from test_x86_64_task_frames import TaskFrameTests
        asm='''BITS 64
TASK_GENERATION equ 8
TASK_STATE equ 0
TASK_READY equ 1
TASK_RUNNING equ 2
TASK_BLOCKED equ 6
NATIVE_TASK_SHIFT equ 10
NATIVE_POOL_TASKS equ 8
section .text
%include "arch/x86_64/proc/native_identity.inc"
'''
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int64_t __attribute__((sysv_abi)) native_identity_lookup64(const void*,const void*,uint64_t,uint64_t);
static uint64_t tasks[8][128],family[8][8],before_tasks[8][128],before_family[8][8];
#define CHECK(x) do {if(!(x)){printf("line %d\n",__LINE__);return 1;}}while(0)
int main(void){
 uint64_t root=7ULL<<32;
 tasks[0][0]=2;tasks[0][1]=7;family[0][0]=root;family[0][5]=1;
 tasks[1][0]=1;tasks[1][1]=8;family[1][0]=(8ULL<<32)|1;family[1][5]=1;
 for(unsigned s=2;s<8;s++){tasks[s][0]=s%2?6:1;tasks[s][1]=9+s;family[s][0]=((9ULL+s)<<32)|s;family[s][1]=root;family[s][5]=2;}
 memcpy(before_tasks,tasks,sizeof(tasks));memcpy(before_family,family,sizeof(family));
 CHECK(native_identity_lookup64(tasks,family,root,0)==7);
 CHECK(native_identity_lookup64(tasks,family,root,7)==7);
 CHECK(native_identity_lookup64(tasks,family,root,8)==-13);
 CHECK(native_identity_lookup64(tasks,family,root,10)==-3);
 for(unsigned s=2;s<8;s++)CHECK(native_identity_lookup64(tasks,family,root,9+s)==9+s);
 CHECK(!memcmp(before_tasks,tasks,sizeof(tasks)) && !memcmp(before_family,family,sizeof(family)));
 CHECK(native_identity_lookup64(tasks,family,root,UINT64_MAX)==-22);
 CHECK(native_identity_lookup64(tasks,family,root,0x80000000)==-22);
 CHECK(native_identity_lookup64(tasks,family,root|1,7)==-13);
 CHECK(native_identity_lookup64(tasks,family,0,0)==-13);
 family[2][1]=(8ULL<<32)|1;CHECK(native_identity_lookup64(tasks,family,root,11)==-13);
 family[2][1]=root;tasks[2][0]=4;CHECK(native_identity_lookup64(tasks,family,root,11)==-3);
 tasks[2][0]=1;family[2][0]^=1;CHECK(native_identity_lookup64(tasks,family,root,11)==-117);
 family[2][0]^=1;family[2][5]=4;CHECK(native_identity_lookup64(tasks,family,root,11)==-117);
 tasks[0][1]=99;CHECK(native_identity_lookup64(tasks,family,root,11)==-117);
 puts("SHELL_SESSION_IDENTITY_OK");return 0;
}'''
        TaskFrameTests().build(asm,c,'SHELL_SESSION_IDENTITY')

    def test_actual_session_window_and_recovery_budget(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ay-shell-session/host'/uuid.uuid4().hex
        folder.mkdir(parents=True)
        environment=os.environ.copy();environment['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        environment['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('O0','O2'):
            exe=folder/(opt+'.exe')
            commands=([find_zig(),'cc','-target','x86_64-windows-gnu','-'+opt,'-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                'test/x86_64_service_session_host.c','userspace/sdk/lib/x86_64/service_session.c','-o',exe],[exe])
            for index,command in enumerate(commands):
                result=subprocess.run(list(map(str,command)),cwd=ROOT,env=environment,capture_output=True,
                    timeout=60 if index==0 else 5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/f'{opt}-{index}.log').write_bytes(result.stdout+result.stderr)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])
                if index:self.assertIn(b'SERVICE_SESSION_POLICY_OK',result.stdout)

if __name__=='__main__':unittest.main()
