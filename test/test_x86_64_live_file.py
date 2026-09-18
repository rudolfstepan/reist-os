"""Concurrent file-service admission and actual lifecycle regressions."""
from pathlib import Path
from unittest.mock import patch
import ast,copy,hashlib,inspect,json,os,re,struct,subprocess,sys,types,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_boot_programs as producer

PROFILE=dict(family=True,startup=True,import_image=True,pio=True,block=True,
             wide=True,block_profile=True,filesystem=True,file_launch=True,
             task_pool=True,pool_pio=True,live_file=True)

class Admitted(Exception):pass

class LiveFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'build/codex-agent/r83ar-live-file/host'/uuid.uuid4().hex
        cls.folder.mkdir(parents=True)

    def command(self,command,limit=45):
        run=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=limit,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (self.folder/(uuid.uuid4().hex+'.log')).write_bytes(run.stdout+run.stderr)
        self.assertEqual(run.returncode,0,(run.stdout+run.stderr).decode(errors='replace')[-4000:])
        return run

    def test_actual_main_normalizes_paths_before_admission(self):
        import run_qemu_x86_64_live_file as live
        import verify_x86_64_live_file as verify
        image=Path('build/codex-agent/r83ar-live-file/native/x86_64/reist-x86_64-bootstrap.elf')
        evidence=Path('build/codex-agent/r83ar-live-file/path-adapter/guests')
        for a,b in ((image,evidence),(ROOT/image,ROOT/evidence)):
            def admitted(got_image,got_evidence):
                self.assertEqual(got_image,image.resolve());self.assertEqual(got_evidence,evidence.resolve())
                self.assertTrue(got_image.is_absolute() and got_evidence.is_absolute())
                raise Admitted()
            with patch.object(sys,'argv',['live','--image',str(a),'--evidence',str(b)]),\
                 patch.object(verify,'admit_runtime',side_effect=admitted),\
                 patch.object(live,'image_config',side_effect=AssertionError('output before admission')):
                with self.assertRaises(Admitted):live.main()

    def test_actual_selector_cache_barrier_and_fail_closed(self):
        import run_qemu_x86_64_live_file as live
        from run_qemu_x86_64_service_cpu import SameStopReads
        source=live.function(live.observer_body(),'select_case')
        for fault in range(4):
            with self.subTest(fault=fault):
                address=0x415000;frame=0x100020000;dm=0xffff800000000000;nx=1<<63
                raw=bytearray(struct.pack('<4I',0 if fault==1 else 1,0,2,0));writes=[];events=[];reads=[]
                def memory(a,n):
                    self.assertEqual((a,n),(dm+frame,16));reads.append(bytes(raw));return bytes(raw)
                def write(a,value):
                    self.assertEqual(a,dm+frame);self.assertEqual(len(value),16)
                    writes.append(bytes(value))
                    if fault!=3:raw[:]=value
                namespace=dict(struct=struct,CONFIG=dict(selection_address=address,layout=0),CASE=0,
                    MASK=0x3fffff000,NX=nx,DM=dm,mem=memory,
                    gdb=types.SimpleNamespace(selected_inferior=lambda:types.SimpleNamespace(write_memory=write)),
                    emit=lambda kind,**fields:events.append(dict(kind=kind,**fields)))
                cache=SameStopReads(namespace);namespace['stop_reads']=cache
                namespace['user']=lambda t,a,n:namespace['mem'](dm+frame,n)
                exec(source,namespace)
                leaves=[0]*64;leaves[(address-0x400000)//4096]=frame|nx|(5 if fault==2 else 7)
                def start():namespace['select_case'](None,1,leaves)
                invoke=cache.wrap_stop(lambda hook:hook.fn())
                if fault:
                    with self.assertRaises(AssertionError):invoke(types.SimpleNamespace(fn=start))
                    self.assertEqual(len(writes),int(fault==3));self.assertFalse(events)
                else:
                    invoke(types.SimpleNamespace(fn=start))
                    self.assertEqual(writes,[struct.pack('<4I',1,0,0,0)])
                    self.assertEqual(len(events),1);self.assertEqual(reads,[struct.pack('<4I',1,0,2,0),writes[0]])
                self.assertFalse(cache.inside or cache.active or cache.entries or cache.used)

    def test_actual_cold_control_routes_and_witness_coverage(self):
        import run_qemu_x86_64_live_file as live
        code=live.observer_body();registrations=[]
        tree=ast.parse(code)
        calls=[n for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
               and isinstance(n.value.func,ast.Name) and n.value.func.id=='Hook'
               and len(n.value.args)==2 and isinstance(n.value.args[1],ast.Name)
               and n.value.args[1].id=='control_syscall']
        for node in calls:exec(ast.get_source_segment(code,node),dict(Hook=lambda name,fn:registrations.append(name),control_syscall=None))
        self.assertEqual(registrations,['family_syscall64','native_pio_apply64.fence_request'])
        source=live.function(code,'control_syscall')
        # Execute the exact callback on actual CREATE-v5/v6 and CANCEL shapes.
        for slot,version,op,state in ((0,5,1,1),(0,6,1,1),(0,1,3,1),(0,1,3,3),(2,6,1,1),(4,1,3,1)):
            effects=[];raw=struct.pack('<4IQ',version,80 if version==6 else 64,op,0,(5<<32)|4)+bytes(40)
            ns=dict(struct=struct,mode=lambda:8,d=lambda a:slot,S=dict(scheduler_current_slot=1,syscall_rax=2,syscall_rdi=3),
                q=lambda a:132 if a==2 else 0x401000,task=lambda n:[state,5],user=lambda t,a,n:raw,
                caller_result=lambda:effects.append('witness'),created=None,create_begin_hook=types.SimpleNamespace(enabled=False),
                create_watch=lambda:effects.append('create'),cancel_watch=lambda gs:effects.append(('cancel',gs)))
            exec(source,ns);ns['control_syscall']()
            expected=[] if slot else ['witness']+(['create'] if op==1 else [('cancel',[5])] if state==1 else [])
            self.assertEqual(effects,expected)
        # Every fixture phase has an unchanged observer before its next effect:
        # IPC for STAT/GO, family for CREATE/CANCEL, fence for dependency loss,
        # and fault for owner loss. No clock/PIO-transfer callback is needed.
        for name in ('ipc','fault'):
            self.assertIn('caller_result()',live.function(code,name))
        self.assertIn('caller_result()',source)
        self.assertIn("Hook('x86_64_scheduler_user_exception64',cold_fault)",code)
        self.assertIn('fault()',live.function(code,'cold_fault'))

    def test_retained_image_cold_control_dispatch_instructions(self):
        import build_x86_64_c_payload as elf
        image=ROOT/'build/codex-agent/r83ar-live-file/native/x86_64/reist-x86_64-bootstrap.elf'
        parsed=elf.elf(image.read_bytes(),32);section=parsed['sections']['.text'];symbols=parsed['symbols']
        data=section['data'];base=section['address']
        def segment(name,size):return data[symbols[name]['value']-base:symbols[name]['value']-base+size]
        raw=segment('process_run_syscall64',260)
        matches=[]
        for n in range(len(raw)-17):
            if raw[n:n+3]==bytes.fromhex('48813d') and raw[n+7:n+13]==bytes.fromhex('840000000f84'):
                matches.append(n)
        self.assertEqual(len(matches),1);n=matches[0];address=symbols['process_run_syscall64']['value']+n
        self.assertEqual(address+11+struct.unpack_from('<i',raw,n+3)[0],symbols['syscall_rax']['value'])
        self.assertEqual(address+17+struct.unpack_from('<i',raw,n+13)[0],symbols['family_syscall64']['value'])
        raw=segment('native_pio_apply64',150);pattern=bytes.fromhex('41837d08050f84');n=raw.index(pattern)
        self.assertEqual(raw.count(pattern),1)
        self.assertEqual(symbols['native_pio_apply64']['value']+n+11+struct.unpack_from('<i',raw,n+7)[0],
                         symbols['native_pio_apply64.fence_request']['value'])
        raw=segment('native_pio_apply64.fence_request',9)
        self.assertEqual(raw[:4],bytes.fromhex('4585f675'));self.assertEqual(raw[5],0xe8)
        self.assertEqual(symbols['native_pio_apply64.fence_request']['value']+10+struct.unpack_from('<i',segment('native_pio_apply64.fence_request',10),6)[0],
                         symbols['native_pio_apply64.fence']['value'])

    def test_actual_terminal_cancel_receipt_and_authority_negatives(self):
        import run_qemu_x86_64_live_file as live
        source=live.function(live.observer_body(),'control_syscall')
        def invoke(mutate=None):
            identity=(3<<32)|2;task_words=[0]*128;events=[]
            receipt=[identity,1<<32,0,0,(1<<32)|134,4,0,0]
            start=dict(slot=2,parent=1,live=False)
            plan=copy.deepcopy(live.roles(6));starts={3:start}
            request=bytearray(struct.pack('<4IQ',1,64,3,0,identity)+bytes(40))
            model=dict(task=task_words,receipt=receipt,start=start,plan=plan,starts=starts,request=request)
            if mutate:mutate(model)
            def mem(a,n):
                self.assertEqual((a,n),(0x1080,64));return struct.pack('<8Q',*receipt)
            ns=dict(struct=struct,mode=lambda:8,d=lambda a:0,S=dict(scheduler_current_slot=1,syscall_rax=2,syscall_rdi=3,family_records=0x1000),
                q=lambda a:132 if a==2 else 0x401000,task=lambda n:[2,1]+[0]*126 if n==0 else task_words,
                user=lambda t,a,n:bytes(request),mem=mem,CONFIG=dict(roles=plan),starts=starts,
                caller_result=lambda:events.append('witness'),created=None,create_begin_hook=types.SimpleNamespace(enabled=False),
                create_watch=lambda:events.append('create'),cancel_watch=lambda gs:events.append(('cancel',gs)))
            exec(source,ns);ns['control_syscall']();self.assertEqual(events,['witness'])
        invoke()
        for status,state,result in ((0,3,2<<32),(90,4,90),(256,3,(1<<32)|256)):
            def positive(m):
                m['plan'][3].update(status=status,state=state);m['receipt'][4]=result
            invoke(positive)
        mutations=[lambda m,i=i:m['receipt'].__setitem__(i,m['receipt'][i]^1) for i in range(8)]
        mutations += [lambda m:m['task'].__setitem__(64,1),lambda m:m['task'].__setitem__(1,4),
            lambda m:m['task'].__setitem__(0,1),lambda m:m['starts'].clear(),
            lambda m:m['start'].__setitem__('live',True),lambda m:m['start'].__setitem__('slot',3),
            lambda m:m['start'].__setitem__('parent',2),lambda m:m['plan'][3].__setitem__('root',2),
            lambda m:m['plan'][3].__setitem__('slot',3),lambda m:m['plan'][3].__setitem__('status',256),
            lambda m:struct.pack_into('<Q',m['request'],16,(4<<32)|2),
            lambda m:struct.pack_into('<Q',m['request'],16,(3<<32)|7),
            lambda m:struct.pack_into('<Q',m['request'],16,2)]
        for n,mutation in enumerate(mutations):
            with self.subTest(mutation=n),self.assertRaises((AssertionError,KeyError)):invoke(mutation)

    def test_old_accepted_cancel_cannot_enter_new_receipt_branch(self):
        import run_qemu_x86_64_live_file as live
        old_path=ROOT/'build/codex-agent/r83ar-live-file/cold-control/candidate-01/source/scripts__run_qemu_x86_64_live_file.py'
        old=types.ModuleType('old_live');exec(compile(old_path.read_text(),str(old_path),'exec'),old.__dict__)
        functions=[live.function(m.observer_body(),'control_syscall') for m in (old,live)]
        for slot in (2,3,4):
            for gen in (1,3,0x7fffffff):
                for state in range(7):
                    observed=[]
                    for source in functions:
                        effects=[];raw=struct.pack('<4IQ',1,64,3,0,(gen<<32)|slot)+bytes(40)
                        ns=dict(struct=struct,mode=lambda:8,d=lambda a:0,S=dict(scheduler_current_slot=1,syscall_rax=2,syscall_rdi=3),
                            q=lambda a:132 if a==2 else 0x401000,task=lambda n:[state,gen]+[0]*126,user=lambda t,a,n:raw,
                            caller_result=lambda:effects.append('witness'),created=None,create_begin_hook=types.SimpleNamespace(enabled=False),
                            create_watch=lambda:effects.append('create'),cancel_watch=lambda gs:effects.append(('cancel',gs)),
                            mem=lambda *a:(_ for _ in ()).throw(AssertionError('new terminal read on old accepted state')))
                        exec(source,ns);ns['control_syscall']();observed.append(effects)
                    self.assertEqual(observed[0],observed[1],(slot,gen,state))

    def test_exact_terminal_delta_and_bound_prefix_reuse(self):
        import verify_x86_64_live_file as verify
        current=(ROOT/'scripts/run_qemu_x86_64_live_file.py').read_text()
        old_path=ROOT/'build/codex-agent/r83ar-live-file/cold-control/candidate-01/source/scripts__run_qemu_x86_64_live_file.py'
        self.assertEqual(verify.terminal_inverse(current),old_path.read_text())
        for changed in (current.replace(verify.TERMINAL_BRANCH,''),current.replace(verify.TERMINAL_BRANCH,verify.TERMINAL_BRANCH*2),
                        current.replace('receipt==(identity,root<<32,0,0,result,4,0,0)','receipt[0]==identity')):
            with self.assertRaises(ValueError):verify.terminal_inverse(changed)
        cold=verify.read(verify.COLD_STOP);manifest=verify.read(ROOT/cold['frozen']['path'])
        f=copy.deepcopy(manifest)
        f['commands'][11]=f['commands'][11].replace('/cold-control/guests','/terminal-receipt/guests')
        rows=verify.reuse_prefix(f)
        self.assertEqual(len(rows),11);self.assertTrue(all(r['executed'] is False and r['passed'] for r in rows))
        self.assertNotIn(6,[r['case'] for r in rows])
        matrix=ROOT/cold['matrix']['path'];original=verify.read
        mutations=[lambda m:m['cases'][0].__setitem__('passed',False),lambda m:m['cases'][-1].__setitem__('passed',True),
                   lambda m:m['cases'][0].__setitem__('layout',4),lambda m:m.__setitem__('closed',False),
                   lambda m:m['image'].__setitem__('sha256','0'*64),lambda m:m['cases'].pop()]
        for change in mutations:
            def read(path):
                value=original(path)
                if Path(path)==matrix:change(value)
                return value
            with patch.object(verify,'read',side_effect=read),self.assertRaises(ValueError):verify.reuse_prefix(f)

    def test_actual_capture_requests_mandatory_proof_options(self):
        import run_qemu_x86_64_live_file as live
        import verify_x86_64_live_file as verify
        evidence=self.folder/'capture-options';captured=[]
        def capture(*args,**kwargs):captured.append(kwargs);raise Admitted()
        with patch.object(sys,'argv',['live','--image',str(self.folder/'never.elf'),'--evidence',str(evidence)]),\
             patch.object(verify,'admit_runtime',return_value=dict(candidate='host-model')),\
             patch.object(verify,'reuse_prefix',return_value=[]),\
             patch.object(verify,'source_binding'),patch.object(verify,'link',return_value={}),\
             patch.object(live,'image_config',return_value=({}, {}, b'')),\
             patch.object(live,'observer',return_value='host-model'),patch.object(live.file,'program_variant',return_value=b''),\
             patch.object(live.pio,'Fixture'),patch.object(live.wide.transport,'capture',side_effect=capture):
            self.assertEqual(live.main(),1)
        self.assertEqual(captured,[dict(binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True)])

    def test_actual_producer_admission(self):
        folder=ROOT/'build/codex-agent/r83ar-live-file/host'/uuid.uuid4().hex
        def admitted(directory,cc,nasm,ld):
            self.assertIn('-DREIST_NATIVE_LIVE_FILE=1',cc)
            self.assertIn('-DREIST_NATIVE_SERVICE_CPU=1',cc)
            self.assertIn('-DREIST_NATIVE_POOL_PIO=1',cc)
            self.assertNotIn('-DREIST_NATIVE_SERVICE_PIO=1',cc)
            raise Admitted()
        with patch.object(producer,'build_file_program',side_effect=admitted):
            with self.assertRaises(Admitted):
                producer.build(folder,['cc'],['nasm'],['ld'],0,**PROFILE)

    def test_reject_conflicts_before_outputs(self):
        bad=[dict(live_file=v) for v in (None,0,1,'1')]
        bad += [{name:False} for name in ('family','startup','import_image','pio','block','wide','block_profile','filesystem','file_launch','task_pool','pool_pio')]
        bad += [{name:True} for name in ('service_cpu','service_pio')]
        bad += [{name:1} for name in ('case','family_case','startup_case','pio_case','memory_case','block_profile_case','filesystem_case','file_launch_case')]
        bad += [dict(filesystem_layout=n) for n in (0,1,3,4)]
        for change in bad:
            values=dict(PROFILE,**change);case=values.pop('case',0)
            destination=self.folder/('reject-'+uuid.uuid4().hex)
            with self.subTest(change=change),self.assertRaises(ValueError):
                producer.build(destination,['never'],['never'],['never'],case,**values)
            self.assertFalse(destination.exists())

    def test_actual_application_and_fs_capture_o0_o2(self):
        import build_x86_64_fs_media as media
        # Standard independent ELF fixture at the NEW fixture's maximum extent.
        raw=bytearray(1280);raw[:7]=b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
        struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096);raw[120]=0xc3
        elf=self.folder/'file.prg';elf.write_bytes(raw)
        for opt in ('0','2'):
            exe=self.folder/('live-'+opt+'.exe')
            command=['gcc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror','-I.','-Iuserspace/sdk/include',
                     'test/x86_64_live_file_host.c','userspace/sdk/lib/x86_64/file_image.c','userspace/sdk/lib/x86_64/image.c',
                     *['userspace/storage/lib/'+n+'.c' for n in ('native_block','vfs_shadow_fat32','vfs_shadow_ext2')],'-o',exe]
            self.command(command)
            for layout in media.LAYOUTS:
                disk=self.folder/(layout+'.raw')
                if not disk.exists():disk.write_bytes(media.image(layout,program=bytes(raw)))
                with self.subTest(opt=opt,layout=layout):
                    result=self.command([exe,disk,layout,elf],10)
                    self.assertIn(b'LIVE_FILE_HOST_PASS',result.stdout)

    def test_make_admission(self):
        from test_x86_64_file_launch import direct_make_plan
        options={'X86_64_NATIVE_LIVE_FILE':'1','X86_64_NATIVE_TASK_POOL':'1','X86_64_NATIVE_POOL_PIO':'1'}
        result=direct_make_plan(self.folder,options)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('--live-file',result.stdout)
        self.assertIn('-DREIST_NATIVE_CPU_TRACE=1',result.stdout)
        self.assertIn('-DREIST_NATIVE_SERVICE_CPU=1',result.stdout)
        for change in ({'X86_64_NATIVE_LIVE_FILE':'2'},{'X86_64_NATIVE_SERVICE_PIO':'1'},
                       {'X86_64_NATIVE_FILE_LAUNCH':'0'},{'X86_64_FILE_LAUNCH_CASE':'1'}):
            result=direct_make_plan(self.folder,dict(options,**change))
            self.assertNotEqual(result.returncode,0)

    def test_generated_observer_and_finite_matrix(self):
        import run_qemu_x86_64_live_file as live
        self.assertEqual(len(live.CASES),25);self.assertEqual(len(set(live.CASES)),25)
        body=live.observer_body();compile(body,'<actual live observer>','exec')
        live.lifecycle_validator()
        self.assertIn("Hook('native_cpu_trace_after64.full'",body)
        self.assertNotIn("CPUHook(core+'.charge'",body)
        self.assertIn("('scheduler_tasks',8192)",body)
        self.assertIn("('scheduler_cpu_windows',256)",body)
        self.assertIn("('process_run_plan',336)",body)
        self.assertIn('for i in range(13)',body)
        self.assertIn('slot==4',live.function(body,'program_ready'))
        self.assertIn('cpu_trace_reader.finish();cpu_ledger.finish()',body)
        for case,layout,ram,point in live.CASES:
            plan=live.roles(case);self.assertLessEqual(len(plan),18)
            self.assertEqual(sorted(plan),list(range(1,len(plan)+1)))
            self.assertTrue(all(i['slot']==4 for i in plan.values() if i['role']=='program'))
        for bad in (-1,18,True,'0',None):
            with self.assertRaises(ValueError):live.roles(bad)

    def test_actual_retirement_o0_o2(self):
        import test_x86_64_file_launch as prior
        root=(ROOT/'arch/x86_64/user/live_file.c').read_text()
        fs=(ROOT/'arch/x86_64/user/filesystem.c').read_text()
        control='typedef struct {'+fs.split('typedef struct {',1)[1].split('} Control;',1)[0]+'} Control;'
        reply=fs.split('    c.phase=4;c.result=result;',1)[1].split('    exercising=1;',1)[0]
        reply='c.phase=4;c.result=result;'+reply
        retirement=root.split('static int retire(',1)[1].split('{',1)[1].split('\n}\nint main',1)[0]
        retirement='int64_t fs_status=mode==5?90:mode==1?((1LL<<32)|134):(2LL<<32);\nint64_t driver_status=mode==5?((1LL<<32)|134):(2LL<<32);\n'+retirement
        source=prior.RETIREMENT_HOST.replace('/* CONTROL_TYPE */',control).replace('/* FS_REPLY_EXIT */',reply).replace('/* RETIREMENT */',retirement)
        for old,new in (('219,220,221,222,223,224,224,224,225,225','240,241,242,243,244,245,245,245,246,246'),
                        ('219,221,222,223,224,224,224,225,225','240,242,243,244,245,245,245,246,246'),
                        ('actual_retire()!=221','actual_retire()!=242')):
            self.assertEqual(source.count(old),1);source=source.replace(old,new)
        path=self.folder/'retire.c';path.write_text(source)
        for opt in ('0','2'):
            exe=self.folder/('retire-'+opt+'.exe')
            self.command(['gcc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror',path,'-o',exe])
            result=self.command([exe],10);self.assertIn(b'FILE_RETIREMENT_HOST_PASS cases=89',result.stdout)

    def test_actual_cpu_oracle_mutations(self):
        import run_qemu_x86_64_live_file as live
        plan=live.roles(0);events=[];serial=[]
        for gen,info in plan.items():
            slot=info['slot'];before=[gen,32,0,0,0 if slot==4 else 100,0,0,0]
            after,result=live.cpu.charge_result(before,gen)
            events += [dict(kind='start',gen=gen),dict(kind='cpu_start',gen=gen,slot=slot,now=0,records=before),
                dict(kind='cpu_charge',gen=gen,slot=slot,now=gen,before=before,after=after,result=result),
                dict(kind='cpu_final',gen=gen,slot=slot,now=gen,records=after),dict(kind='release',gen=gen)]
            serial.append('REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,info['status'],info['state'],1,0x410100).hex().upper())
        serial='\n'.join(serial);live.validate_cpu(serial,events,0)
        for index,key,value in ((1,'slot',7),(1,'records',[1,32,0,0,0,0,0,0]),(2,'result',2),
                                (2,'after',[1,32,2,1,100,0,0,2]),(3,'records',[1,32,0,0,100,0,0,0])):
            changed=copy.deepcopy(events);changed[index][key]=value
            with self.assertRaises((ValueError,KeyError)):live.validate_cpu(serial,changed,0)
        with self.assertRaises(ValueError):live.validate_cpu(serial,events[:-2],0)

    def test_actual_coexistence_snapshot_bounded_reads_and_negatives(self):
        import run_qemu_x86_64_live_file as live
        source=live.function(live.observer_body(),'caller_result')
        for fault in range(7):
            phase=[1];seen=[];reads=[];prepared=b'P'*266336;owner=(4<<32)|3;driver=(3<<32)|2
            def task(slot):return [2 if slot==0 else 1 if fault==3 and slot==4 else 6,slot+1]
            def user(task,address,n):
                self.assertLessEqual(n,266336);reads.append((address,n))
                if address==100:
                    return struct.pack('<10Q',0x4c49564546494c31,phase[0],owner,driver,
                        0 if phase[0]==1 else (5<<32)|4,0,1000,1000000,0,2)
                if address==1000:return (b'Q' if fault==1 else b'P')*n if phase[0]==1 else b'\x5a'*n
                self.assertIn((address,n),((1000000,2048),(1002048,266336)))
                return bytes(n-1)+bytes([int(fault==2 and address==1002048)])
            namespace=dict(struct=struct,hashlib=hashlib,task=task,user=user,mode=lambda:8,CASE=0,
                CONFIG=dict(result_address=100,layout=2,roles=live.roles(0),prepared=prepared,requests=[None]*8),
                S=dict(family_records=2000),q=lambda a:(2 if fault==4 else 1)<<32,
                results=set(),live_phases=set(),proofs={5},
                starts={g:dict(live=not(fault==5 and g==3)) for g in (3,4,5)},
                pstate=lambda:(driver,0,0),fs_replies={} if fault==6 else {(owner,8):(0,b'')},
                emit=lambda kind,**fields:seen.append(dict(kind=kind,**fields)))
            exec(source,namespace)
            def run():
                for p in (1,2,3):phase[0]=p;namespace['caller_result']()
            if fault:
                with self.subTest(fault=fault),self.assertRaises(AssertionError):run()
            else:
                run();self.assertEqual([e['kind'] for e in seen],['file_result','live','live'])
                self.assertIn((1002048,266336),reads)

    def test_reject_old_nonconcurrent_guest_proof(self):
        import test_x86_64_file_launch as prior
        import run_qemu_x86_64_live_file as live
        serial,events,counts,raw=prior.sample()
        with self.assertRaises(ValueError):live.lifecycle_validator()(serial,prior.trace(events),0,2,None,counts,raw)

    def test_actual_new_role_syntax_and_file_extent(self):
        from build_user_program import find_zig
        zig=str(find_zig());env=os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(self.folder/'zig-cache')
        for n in range(4):
            cmd=[zig,'cc','-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror',
                 '-Iuserspace/sdk/include','-DREIST_NATIVE_LIVE_FILE=1','-DPROGRAM_ID='+str(n),'-DFILESYSTEM_CASE=0',
                 '-Dimport_blob=((unsigned char[1]){0})','-Dfilesystem_blob=((unsigned char[1]){0})',
                 '-c','arch/x86_64/user/live_file.c','-o',str(self.folder/f'role-{n}.o')]
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=20)
            (self.folder/f'role-{n}.log').write_bytes(r.stdout+r.stderr)
            self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'))
        # A single small PRG is not an OS image; no kernel/guest build here.
        raw=producer.build_file_program(self.folder/'actual-program',[zig,'cc','-DREIST_NATIVE_LIVE_FILE=1'],['nasm'],[zig,'ld.lld'])
        self.assertLessEqual(len(raw),1280);self.assertEqual(len(producer.prepare(raw,[],True)),266336)
        print('LIVE_FILE_PROGRAM',len(raw),hashlib.sha256(raw).hexdigest())

    def test_actual_powershell_admission(self):
        source=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text().split('$RepoRoot =',1)[0]
        source+="\n@{pool=[int]$NativePoolPIO.IsPresent;tasks=[int]$NativeTaskPool.IsPresent;file=[int]$NativeFileLaunch.IsPresent;fs=[int]$NativeFilesystem.IsPresent;cpu=[int]$NativeServiceCPU.IsPresent;pio=[int]$NativeServicePIO.IsPresent} | ConvertTo-Json -Compress\n"
        path=self.folder/'actual-admission.ps1';path.write_text(source)
        result=self.command(['powershell.exe','-NoProfile','-File',path,'-NativeLiveFile'],10)
        self.assertEqual(json.loads(result.stdout),dict(pool=1,tasks=1,file=1,fs=1,cpu=0,pio=0))
        for flags in (['-NativeServicePIO'],['-NativeServiceCPU'],['-FilesystemLayout','1'],['-FileLaunchCase','1']):
            result=subprocess.run(['powershell.exe','-NoProfile','-File',str(path),'-NativeLiveFile',*flags],cwd=ROOT,capture_output=True,timeout=10)
            (self.folder/(uuid.uuid4().hex+'.log')).write_bytes(result.stdout+result.stderr)
            self.assertNotEqual(result.returncode,0)

    def test_old_producer_commands_exact_with_modeled_tool_outputs(self):
        # Execute both actual producers. Only compiler/linker output is modeled;
        # this is dispatch/default evidence, never compiled-image evidence.
        original=subprocess.check_output(['git','show','c7e5e72a:scripts/build_x86_64_boot_programs.py'],cwd=ROOT,timeout=10).decode()
        old=types.ModuleType('accepted_producer');old.__file__=str(ROOT/'scripts/build_x86_64_boot_programs.py')
        exec(compile(original,old.__file__,'exec'),old.__dict__)
        raw=bytearray(128);raw[:7]=b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x400078,64,0,0,64,56,1,0,0,0)
        struct.pack_into('<II6Q',raw,64,1,5,0,0x400000,0x400000,121,121,4096);raw[120]=0xc3
        base=dict(family=True,startup=True,import_image=True,wide=True)
        pio_profile=dict(base,pio=True,block=True,block_profile=True,task_pool=True,pool_pio=True)
        profiles=[{},base,dict(base,task_pool=True),dict(base,task_pool=True,service_cpu=True),pio_profile,dict(pio_profile,service_pio=True)]
        profiles += [dict(base,pio=True,block=True,block_profile=True,filesystem=True,file_launch=True,filesystem_layout=n) for n in range(5)]
        for index,profile in enumerate(profiles):
            outputs=[]
            for label,module in (('before',old),('after',producer)):
                folder=self.folder/f'modeled-{index}-{label}';calls=[]
                def tool(command,**kwargs):
                    values=list(map(str,command));out=Path(values[values.index('-o')+1]);out.write_bytes(raw)
                    normalized=[re.sub(r'programs-[0-9a-f]{32}','programs-attempt',v.replace(str(folder),'<output>')) for v in values]
                    calls.append(normalized);return types.SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
                with patch.object(module.subprocess,'run',side_effect=tool):
                    module.build(folder,['cc'],['nasm'],['ld'],0,**profile)
                outputs.append(calls)
            self.assertEqual(outputs[0],outputs[1],profile)

if __name__=='__main__':unittest.main()
