"""Execute production periodic admission/accounting and verify guest evidence."""
from pathlib import Path
import ast,copy,hashlib,json,os,struct,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host


class ServiceCPUTests(unittest.TestCase):
    def sealed_peer_runtime(self):
        from types import ModuleType
        path=ROOT/'build/codex-agent/r83ap-service-cpu/peer-stop-source/scripts__run_qemu_x86_64_service_cpu.py'
        module=ModuleType('sealed_peer_service_cpu');module.__file__=str(path)
        # inspect.getsource(class) resolves through __module__, unlike function
        # inspection. It must see the sealed file, not current line numbers.
        sys.modules[module.__name__]=module
        exec(compile(path.read_text(),str(path),'exec'),vars(module))
        return module

    def test_static_cpu_decisions_and_deferred_failure(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        calls=[];deciding=False
        def mutation(value):
            self.assertFalse(deciding,'GDB mutation inside stop decision');calls.append(value)
        env=dict(callbacks=0,gdb=SimpleNamespace(execute=mutation),
                 emit=lambda *a,**k:calls.append((a,k)),service_stops=r.StopDispatcher({}))
        cpu=r.ReadOnlyCPUStops(env);hook=SimpleNamespace(fn=lambda:calls.append('read'))
        cpu.bind(hook)
        self.assertEqual(hook.commands,'silent\npython cpu_stops.fail()')
        deciding=True
        self.assertIs(cpu.stop(hook),False)
        deciding=False
        self.assertEqual(calls,['read']);self.assertEqual(env['callbacks'],1)
        for variant in ('counter','nested','dispatcher','reader','cache','callback'):
            with self.subTest(variant=variant):
                env['callbacks']=0;env['service_stops']=r.StopDispatcher({})
                env.pop('binary_reader',None);env.pop('stop_reads',None)
                cpu=r.ReadOnlyCPUStops(env);calls.clear()
                def fail():raise OSError('bounded read failed')
                hook.fn=fail if variant=='callback' else lambda:calls.append('read')
                if variant=='counter':env['callbacks']=8192
                if variant=='nested':cpu.running=True
                if variant=='dispatcher':env['service_stops'].pending=[hook]
                if variant=='reader':env['binary_reader']=SimpleNamespace(in_stop=False,client=object(),failed=False)
                if variant=='cache':env['stop_reads']=SimpleNamespace(inside=False,active=True)
                deciding=True
                self.assertIs(cpu.stop(hook),True);self.assertTrue(cpu.failed)
                self.assertEqual(calls,[])
                deciding=False
                cpu.fail();self.assertEqual(calls[-1],'quit 71')
                calls.clear();self.assertIs(cpu.stop(hook),True);self.assertEqual(calls,[])

    def test_static_actual_core_old_new_equivalence(self):
        saved=ROOT/'build/codex-agent/r83ap-service-cpu/peer-stop-source'
        budget=(saved/'arch__x86_64__proc__cpu_budget.asm').read_text()
        period=(saved/'arch__x86_64__proc__cpu_period.inc').read_text()
        old=budget.replace('%include "arch/x86_64/proc/cpu_period.inc"',period)
        old=old.replace('reist_x64_budget_apply','old_budget').replace('reist_x64_period_apply','old_period')
        asm='%define REIST_NATIVE_SERVICE_CPU 1\n'+old+'\n%include "arch/x86_64/proc/cpu_budget.asm"\n'
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
/* Zig's release CRT may disable standard assert even for this O0 driver. */
#define assert(x) do { if(!(x)) {fprintf(stderr,"check line %d: %s\n",__LINE__,#x);abort();} } while(0)
typedef uint64_t U;
typedef U __attribute__((sysv_abi)) (*L)(U*,U,U,U);
typedef U __attribute__((sysv_abi)) (*P)(U*,U*,U,U,U,U);
extern U __attribute__((sysv_abi)) old_budget(U*,U,U,U),reist_x64_budget_apply(U*,U,U,U);
extern U __attribute__((sysv_abi)) old_period(U*,U*,U,U,U,U),reist_x64_period_apply(U*,U*,U,U,U,U);
static unsigned results[3],calls;
static void compare(const U *input,U op,U gen,U arg,U now,int periodic) {
    U a[12],b[12];memcpy(a,input,sizeof a);memcpy(b,input,sizeof b);
    U x=periodic?old_period(a+2,a+6,op,gen,arg,now):old_budget(a+2,op,gen,arg);
    U y=periodic?reist_x64_period_apply(b+2,b+6,op,gen,arg,now):reist_x64_budget_apply(b+2,op,gen,arg);
    assert(x==y && x<=2 && !memcmp(a,b,sizeof a));results[x]++;calls++;
    assert(a[0]==input[0] && a[1]==input[1] && a[10]==input[10] && a[11]==input[11]);
    if(!x)assert(!memcmp(a,input,sizeof a));
}
int main(void) {
    U seed[12]={0x55,0xaa,7,32,0,0,100,10,0,0,0x1234,0xabcd};
    U times[]={0,1,10,11,31,41,99,100,109,110,111,200,9999,(1ULL<<60)-1,1ULL<<60,UINT64_MAX};
    U words[]={0,1,2,7,31,32,33,100,101,65536,65537,1ULL<<32,UINT64_MAX};
    for(int periodic=0;periodic<=1;periodic++)for(unsigned total=0;total<=33;total++) {
        U state[12];memcpy(state,seed,sizeof state);
        state[4]=total;state[5]=total?10+total:0;state[9]=periodic?total:0;
        if(!periodic)memset(state+6,0,32);
        for(unsigned op=0;op<=4;op++)for(unsigned ti=0;ti<sizeof times/sizeof *times;ti++) {
            U now=times[ti];compare(state,op,7,op==2?now:0,now,periodic);
            for(unsigned wi=2;wi<10;wi++)for(unsigned vi=0;vi<sizeof words/sizeof *words;vi++) {
                U changed[12];memcpy(changed,state,sizeof changed);changed[wi]=words[vi];
                compare(changed,op,7,op==2?now:0,now,periodic);
            }
            compare(state,op,8,now,now,periodic);compare(state,op,1ULL<<32,now,now,periodic);
            compare(state,op,7,now-1,now,periodic);
        }
    }
    U empty[12]={0};compare(empty,1,7,32,10,0);compare(empty,1,7,(100ULL<<32)|32,10,1);
    seed[4]=31;seed[5]=140;seed[8]=1;seed[9]=1;
    compare(seed,2,7,210,210,1);compare(seed,2,7,141,141,1);
    assert(results[0] && results[1] && results[2] && calls>500000);
    puts("STATIC_CPU_EQUIVALENCE_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'STATIC_CPU_EQUIVALENCE')

    def test_static_nonservice_actual_nasm_objects_exact(self):
        import verify_x86_64_service_cpu as v
        saved=v.BASE/'peer-stop-source';stop=v.read(v.BASE/'verification-status-peer-stopped.json')
        nasm=next(n for n in stop['tools_sha256'] if Path(n).name.lower()=='nasm.exe')
        self.assertEqual(v.digest(Path(nasm)),stop['tools_sha256'][nasm])
        folder=v.BASE/('host-static-nasm-'+uuid.uuid4().hex);folder.mkdir()
        name='arch/x86_64/proc/cpu_budget.asm';inc='arch/x86_64/proc/cpu_period.inc';outputs={};commands=[]
        for label in ('old','new'):
            cwd=folder/label;(cwd/'arch/x86_64/proc').mkdir(parents=True)
            for source in (name,inc):
                data=(saved/source.replace('/','__')).read_bytes() if label=='old' else (ROOT/source).read_bytes()
                (cwd/source).write_bytes(data)
            for profile,flags in (('default',[]),('service',['-DREIST_NATIVE_SERVICE_CPU=1'])):
                obj=cwd/(profile+'.o');argv=[nasm,'-f','elf32',*flags,name,'-o',str(obj)]
                result=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=15,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                log=cwd/(profile+'.log');log.write_text(result.stdout+result.stderr)
                self.assertEqual(result.returncode,0,result.stderr);outputs[obj.relative_to(ROOT).as_posix()]=v.digest(obj)
                commands.append(dict(argv=argv,cwd=str(cwd),exit_code=result.returncode,log=v.link(log)))
        self.assertEqual((folder/'old/default.o').read_bytes(),(folder/'new/default.o').read_bytes())
        self.assertNotEqual((folder/'old/service.o').read_bytes(),(folder/'new/service.o').read_bytes())
        refs=[]
        for profile in ('pool-reference','pio-reference','file-reference'):
            obj=v.BASE/profile/'x86_64/cpu_budget.o'
            self.assertEqual(obj.read_bytes(),(folder/'new/default.o').read_bytes());refs.append(v.link(obj))
        proof=dict(passed=True,old={n:v.link(saved/n.replace('/','__')) for n in (name,inc)},
            new={n:v.link(ROOT/n) for n in (name,inc)},nasm=dict(path=nasm,sha256=v.digest(Path(nasm))),commands=commands,
            outputs=outputs,references=refs)
        (folder/'proof.json').write_text(json.dumps(proof,indent=2))

    def test_static_native_gdb_actual_cpu_probes(self):
        import inspect
        import run_qemu_x86_64_service_cpu as r
        import verify_x86_64_service_cpu as v
        tools=v.read(v.BASE/'verification-status-peer-stopped.json')['tools_sha256']
        gdb=next(n for n in tools if Path(n).name.lower()=='gdb.exe')
        gcc=next(n for n in tools if Path(n).name.lower()=='gcc.exe')
        nasm=next(n for n in tools if Path(n).name.lower()=='nasm.exe')
        for tool in (gdb,gcc,nasm):self.assertEqual(v.digest(Path(tool)),tools[tool])
        folder=v.BASE/('host-static-gdb-'+uuid.uuid4().hex);folder.mkdir()
        asm=folder/'fixture.asm';c=folder/'fixture.c';obj=folder/'fixture.o';exe=folder/'fixture.exe'
        asm.write_text('''%define REIST_NATIVE_SERVICE_CPU 1
%include "arch/x86_64/proc/cpu_budget.asm"
section .bss
align 16
global scheduler_cpu_budgets,scheduler_cpu_windows,scheduler_mode,scheduler_last_tick,scheduler_tasks
scheduler_cpu_budgets:resq 32
scheduler_cpu_windows:resq 32
scheduler_mode:resq 1
scheduler_last_tick:resq 1
scheduler_tasks:resb 8192
''')
        c.write_text('''#include <stdint.h>
#include <assert.h>
extern uint64_t scheduler_cpu_budgets[],scheduler_cpu_windows[],scheduler_tasks[],scheduler_mode,scheduler_last_tick;
extern uint64_t __attribute__((sysv_abi)) reist_x64_budget_apply(uint64_t*,uint64_t,uint64_t,uint64_t);
extern uint64_t __attribute__((sysv_abi)) reist_x64_period_apply(uint64_t*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
__attribute__((noinline)) void host_done(void){__asm__ volatile("" ::: "memory");}
int main(int argc,char **argv){
 (void)argv;scheduler_tasks[1]=7;
 for(int periodic=0;periodic<2;periodic++){
  scheduler_mode=0;scheduler_last_tick=0;
  assert(reist_x64_period_apply(scheduler_cpu_budgets,scheduler_cpu_windows,1,7,periodic?((100ULL<<32)|32):32,0)==1);
  scheduler_mode=8;
  for(unsigned i=1;i<=32;i++){
   scheduler_last_tick=(argc>1 && i==2)?1:i;
   uint64_t tick=scheduler_last_tick;
   uint64_t value=reist_x64_period_apply(scheduler_cpu_budgets,scheduler_cpu_windows,2,7,tick,tick);
   assert(value==(i==32?2:1));
  }
  assert(reist_x64_period_apply(scheduler_cpu_budgets,scheduler_cpu_windows,3,7,0,32)==1);
 }
 host_done();return 0;
}
''')
        commands=[]
        def command(argv,label,timeout=30,expected=0):
            result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=timeout,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            log=folder/(label+'.log');log.write_text(result.stdout+result.stderr)
            commands.append(dict(argv=argv,exit_code=result.returncode,log=v.link(log)))
            self.assertEqual(result.returncode,expected,(result.stdout+result.stderr)[-3000:])
            self.assertLessEqual(log.stat().st_size,65536)
        command([nasm,'-f','win64',str(asm),'-o',str(obj)],'asm')
        command([gcc,'-O0','-g','-fno-inline',str(c),str(obj),'-o',str(exe)],'build')
        names=['scheduler_cpu_budgets','scheduler_cpu_windows','scheduler_mode','scheduler_last_tick','scheduler_tasks']
        names += [core+suffix for core in ('reist_x64_period_apply','reist_x64_budget_apply') for suffix in ('.charge','.charge_result')]
        generated=r.observer_body();tree=ast.parse(generated)
        hook=next(ast.get_source_segment(generated,n) for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Hook')
        setup='''import gdb,struct,json,hashlib
from pathlib import Path
callbacks=0;deciding=False;unsafe=[];starts={7:dict(live=True,slot=0)}
def reg(name):
    # This is a Windows Ring3 fixture, not a guest IRQ proof. Model its
    # unprivileged IF operand only; all other registers/memory remain actual.
    return 0 if name=='eflags' else int(gdb.parse_and_eval('$'+name))&0xffffffffffffffff
def mem(address,size):return bytes(gdb.selected_inferior().read_memory(address,size))
def q(address):return struct.unpack('<Q',mem(address,8))[0]
def emit(*args,**kw):gdb.write('HOST_EVENT '+repr((args,kw))+'\\n')
def mutation(event):
    if deciding:unsafe.append(event.number)
gdb.events.breakpoint_modified.connect(mutation)
gdb.events.breakpoint_created.connect(mutation)
gdb.events.breakpoint_deleted.connect(mutation)
'''
        setup+='S={name:int(gdb.parse_and_eval("(unsigned long long)&\\\'"+name+"\\\'")) for name in '+repr(names+['host_done'])+'}\n'
        setup+=inspect.getsource(r.StopDispatcher)+'\nservice_stops=StopDispatcher(globals())\n'+hook+'\n'
        setup+=inspect.getsource(r.ReadOnlyCPUStops)+'\n'+inspect.getsource(r.cpu_snapshot_layout)+'\n'+inspect.getsource(r.cpu_pack)+'\n'+inspect.getsource(r.CPULedger)+'\n'
        setup+='cpu_ledger=CPULedger(Path(LEDGER),gdb.write)\n'+r.CPU_OBSERVER
        setup+='''
original=CPUHook.stop
def decision(self):
    global deciding
    assert not deciding
    deciding=True
    try:return original(self)
    finally:deciding=False
CPUHook.stop=decision
def done():
    assert cpu_pending is None and cpu_charges==64 and callbacks==129 and not unsafe
    cpu_ledger.finish()
    with open(PROOF,'x') as out:json.dump(dict(passed=True,charges=64,callbacks=callbacks,unsafe=unsafe,irq_modeled=True,guest_irqs_proven=False),out)
    gdb.execute('quit 0')
Hook('host_done',done)
'''
        for label,argument,expected in (('healthy','',0),('invalid','invalid',71)):
            script=folder/(label+'.gdb');proof=folder/(label+'.json');ledger=folder/(label+'.bin')
            code='set confirm off\nset pagination off\nfile '+exe.as_posix()+'\nstart '+argument+'\npython\n'
            code+='LEDGER='+repr(ledger.as_posix())+'\nPROOF='+repr(proof.as_posix())+'\n'+setup+'\nend\ncontinue\n'
            script.write_text(code);command([gdb,'-q','-nx','-batch','-x',str(script)],label,45,expected)
            if not expected:
                self.assertTrue(json.loads(proof.read_text())['passed'])
                raw=ledger.read_bytes();self.assertEqual(len(raw),64*168)
                for i in range(64):
                    row=struct.unpack_from('<4I3Q16Q',raw,i*168)
                    self.assertEqual(row[6],2 if i%32==31 else 1)
                    self.assertEqual(row[7:11],(7,32,i%32,i%32))
                    self.assertEqual(row[15:19],(7,32,i%32+1,i%32+1))
            else:
                self.assertFalse(proof.exists());self.assertIn('OBSERVER_FAIL',(folder/(label+'.log')).read_text())
        (folder/'receipt.json').write_text(json.dumps(dict(passed=True,new_guests=0,
            runtime=v.link(Path(r.__file__)),sources={n:v.link(ROOT/n) for n in ('arch/x86_64/proc/cpu_budget.asm','arch/x86_64/proc/cpu_period.inc')},
            commands=commands,tools_sha256={n:tools[n] for n in (gdb,gcc,nasm)}),indent=2))

    def test_static_actual_generated_cpu_callbacks(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        tree=ast.parse(r.CPU_OBSERVER)
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cpu_charge','cpu_return')]
        env=dict(cpu_pending=None,cpu_charges=0,S={'scheduler_cpu_budgets':4096,'scheduler_tasks':8192},
            starts={7:dict(live=True,slot=0)},reg=lambda name:dict(rdi=4096,eflags=0,rax=1)[name],q=lambda address:7)
        records=[7,32,0,0,100,0,0,0];state=[8,1,records];events=[]
        env.update(cpu_snapshot=lambda slot:tuple(state),cpu_ledger=SimpleNamespace(event=lambda **row:events.append(row)))
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'<actual static CPU callbacks>','exec'),env)
        env['cpu_charge']();state[2]=[7,32,1,1,100,0,0,1];env['cpu_return']()
        self.assertEqual(events,[dict(kind='cpu_charge',slot=0,gen=7,now=1,before=records,result=1,after=state[2])])
        self.assertIsNone(env['cpu_pending'])
        for variant in ('orphan','slot','tick','mode','if','ledger'):
            with self.subTest(variant=variant):
                state[:]=[8,2,state[2]];env['cpu_pending']=None
                env['reg']=lambda name:dict(rdi=4096,eflags=0,rax=1)[name]
                if variant!='orphan':env['cpu_charge']()
                if variant=='slot':env['reg']=lambda name:dict(rdi=4128,eflags=0,rax=1)[name]
                if variant=='tick':state[1]=3
                if variant=='mode':state[0]=0
                if variant=='if':env['reg']=lambda name:dict(rdi=4096,eflags=512,rax=1)[name]
                if variant=='ledger':env['cpu_ledger']=SimpleNamespace(event=lambda **kw:(_ for _ in ()).throw(OSError('write')))
                with self.assertRaises((AssertionError,OSError)):env['cpu_return']()
                self.assertEqual(len(events),1)
        env['cpu_pending']=None;state[0]=0;env['cpu_charge']();env['cpu_return']()
        self.assertIsNone(env['cpu_pending']);self.assertEqual(len(events),1)

    def test_dispatch_single_line_python_keeps_continue(self):
        import run_qemu_x86_64_service_cpu as runtime
        from types import SimpleNamespace
        dispatcher=runtime.StopDispatcher({});hook=SimpleNamespace()
        dispatcher.bind(hook)
        # A one-line GDB 'python EXPR' command has no following 'end'. The
        # actual pinned-GDB diagnosis shows an extra end truncates continue.
        self.assertEqual(hook.commands,'silent\npython service_stops.drain()\ncontinue')
        self.assertTrue(hook.silent);self.assertFalse(hook.service_retire)
        base=ROOT/'build/codex-agent/r83ap-service-cpu/debugger-host'
        old=json.loads((base/'run-original/receipt.json').read_text())
        self.assertEqual(old['exit_code'],0);self.assertFalse(old['completion'])
        self.assertEqual(old['last_stage']['callbacks'],1)
        rows=[json.loads(line) for line in (base/'run-original/stages.jsonl').read_text().splitlines()]
        commands=[row['commands'] for row in rows if row['label']=='bound_commands']
        self.assertTrue(commands);self.assertEqual(set(commands),{'silent\npython service_stops.drain()\n'})
        before=json.loads((base/'run-baseline/proof.json').read_text())
        after=json.loads((base/'run-final/proof.json').read_text())
        receipt=json.loads((base/'run-final/receipt.json').read_text())
        self.assertTrue(receipt['passed']);self.assertEqual(receipt['exit_code'],0)
        self.assertEqual(receipt['runtime']['sha256'],hashlib.sha256((ROOT/'build/codex-agent/r83ap-service-cpu/peer-stop-source/scripts__run_qemu_x86_64_service_cpu.py').read_bytes()).hexdigest())
        for key in ('events','counts','returns','callbacks','actual_calls'):self.assertEqual(before[key],after[key])
        self.assertEqual(after['counts'],[24]*12);self.assertEqual(after['callbacks'],613)
        self.assertGreater(before['unsafe_mutations'],0);self.assertEqual(after['unsafe_mutations'],0)

    def test_actual_callback_dispatch_outside_stop_decision(self):
        import run_qemu_x86_64_service_cpu as runtime
        from types import SimpleNamespace
        tree=ast.parse(runtime.observer_body());state=dict(deciding=False);changes=[]
        class Breakpoint:
            def __init__(self,*args,**kwargs):self._enabled=True;self.valid=True
            @property
            def enabled(self):return self._enabled
            @enabled.setter
            def enabled(self,value):
                changes.append(('enabled',state['deciding']));self._enabled=value
            def is_valid(self):return self.valid
            def delete(self):changes.append(('delete',state['deciding']));self.valid=False
        def command(value):changes.append((value,state['deciding']))
        env=dict(gdb=SimpleNamespace(Breakpoint=Breakpoint,execute=command,write=lambda value:None),S={'begin':1},
            callbacks=0,emit=lambda *args,**kw:None,created=None,source_pointer=0,allocation_count=99,
            allocation_before=0,allocation_owner=0,q=lambda address:100 if address==124 else (7<<32),
            d=lambda address:0,free=lambda:1045657)
        env['S'].update(family_request=100,scheduler_current_slot=200,family_records=300)
        if hasattr(runtime,'StopDispatcher'):env['service_stops']=runtime.StopDispatcher(env)
        selected=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Hook' or isinstance(n,ast.FunctionDef) and n.name=='create_begin']
        exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual callback dispatch>','exec'),env)
        env['allocator']=Breakpoint();hook=env['Hook']('begin',env['create_begin'])
        state['deciding']=True
        try:answer=hook.stop()
        finally:state['deciding']=False
        self.assertEqual(changes,[],'callback changed GDB state during Breakpoint.stop')
        self.assertIsNone(env['created'],'callback ran inside stop decision')
        self.assertIs(answer,True)
        env['service_stops'].drain()
        self.assertEqual(changes,[('enabled',False)]);self.assertTrue(env['created'])
        self.assertEqual((env['allocation_count'],env['allocation_before'],env['allocation_owner']),(0,1045657,7<<32))
        self.assertEqual(env['callbacks'],1)

    def test_dispatch_occurrences_order_bounds_and_errors(self):
        import run_qemu_x86_64_service_cpu as runtime
        events=[];namespace={};dispatch=runtime.StopDispatcher(namespace)
        class Hook:
            service_retire=False
            def __init__(self,name):self.name=name;self.valid=True
            def is_valid(self):return self.valid
            def delete(self):events.append(('delete',self.name));self.valid=False
            def observe(self):events.append(('observe',self.name));return False
        first=Hook('first');second=Hook('second')
        for hook in (first,second,first):self.assertTrue(dispatch.collect(hook))
        self.assertEqual(events,[]);dispatch.drain()
        self.assertEqual(events,[('observe','first'),('observe','second'),('observe','first')])
        events.clear();second.service_retire=True;dispatch.collect(second);dispatch.drain()
        self.assertEqual(events,[('observe','second'),('delete','second')])
        for variant in ('empty','capacity','budget','invalid','return','exception','nested'):
            with self.subTest(variant=variant):
                d=runtime.StopDispatcher({});hook=Hook(variant)
                if variant!='empty':d.collect(hook)
                if variant=='capacity':
                    for _ in range(32):d.collect(hook)
                    self.assertEqual(len(d.pending),32)
                if variant=='budget':d.batches=8192
                if variant=='invalid':hook.valid=False
                original=Hook.observe
                if variant=='return':Hook.observe=lambda self:None
                if variant=='exception':Hook.observe=lambda self:(_ for _ in ()).throw(OSError('actual callback'))
                if variant=='nested':Hook.observe=lambda self:(d.collect(self),False)[1]
                try:
                    with self.assertRaises((ValueError,OSError)):d.drain()
                    self.assertTrue(d.failed);self.assertFalse(d.running)
                finally:Hook.observe=original

    def test_dispatch_actual_binary_cleanup_and_same_stop_read_scope(self):
        import run_qemu_x86_64_service_cpu as runtime
        import qemu_binary_memory as binary
        namespace={};dispatch=runtime.StopDispatcher(namespace);calls=[]
        reader=binary.Reader(1,'host',Path('bound-host'),4096,lambda a,n:b'x'*n,lambda:4096)
        namespace['binary_reader']=reader
        class Client:
            def close(self):calls.append('closed')
        class Hook:
            service_retire=True
            def is_valid(self):return True
            def delete(self):calls.append(('delete',reader.in_stop))
            def observe(self):
                self_test.assertTrue(reader.in_stop);reader.client=Client();raise OSError('callback read failure')
        self_test=self;dispatch.collect(Hook())
        with self.assertRaises(OSError):dispatch.drain()
        self.assertTrue(reader.failed);self.assertIsNone(reader.client);self.assertFalse(reader.in_stop)
        self.assertEqual(calls,['closed',('delete',False)])

    def test_dispatch_generated_original_callback_bodies_exact(self):
        import inspect
        import run_qemu_x86_64_service_cpu as runtime
        runtime=self.sealed_peer_runtime()
        old=(ROOT/'build/codex-agent/r83ap-service-cpu/allocation-series-stop-source/scripts__run_qemu_x86_64_service_cpu.py').read_text()
        env=dict(vars(runtime));node=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='observer_body')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<sealed pre-dispatch observer>','exec'),env)
        before=env['observer_body']();after=runtime.observer_body()
        self.assertEqual(after,runtime.defer_observer_callbacks(before,('Hook','ReleaseEnd')))
        for original,current,names in ((before,after,('Hook','ReleaseEnd')),
                                      (runtime.FATAL_BODY,runtime.defer_observer_callbacks(runtime.FATAL_BODY,('Probe',)),('Probe',))):
            oldtree=ast.parse(original);newtree=ast.parse(current)
            for name in names:
                first=next(n for n in oldtree.body if isinstance(n,ast.ClassDef) and n.name==name)
                second=next(n for n in newtree.body if isinstance(n,ast.ClassDef) and n.name==name)
                oldstop=next(n for n in first.body if isinstance(n,ast.FunctionDef) and n.name=='stop')
                decision=next(n for n in second.body if isinstance(n,ast.FunctionDef) and n.name=='stop')
                observe=next(n for n in second.body if isinstance(n,ast.FunctionDef) and n.name=='observe')
                observe.name='stop';self.assertEqual(ast.dump(oldstop),ast.dump(observe))
                self.assertEqual(ast.unparse(decision),'def stop(self):\n    return service_stops.collect(self)')
            oldother=[n for n in oldtree.body if not isinstance(n,ast.ClassDef) or n.name not in names]
            # Only the dispatcher prefix and the cache wrapper's method target
            # are new. Every function (including both allocation definitions)
            # and every fault/normal predicate stays byte-for-byte equivalent.
            funcs=lambda t:[ast.dump(n) for n in t.body if isinstance(n,ast.FunctionDef)]
            self.assertEqual(funcs(oldtree),funcs(newtree))

    def retention_build(self,c,label,extra):
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-retention-'+uuid.uuid4().hex)
        folder.mkdir();source=folder/'source.c';source.write_text(c,encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/(label+opt+'.exe')
            commands=[([str(host.find_zig()),'cc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror','-I.',*extra,str(source),'-o',str(exe)],'build'),([str(exe)],'run')]
            for argv,kind in commands:
                result=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(opt+'-'+kind+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-2500:])
                if kind=='run':self.assertIn(label+'_OK',result.stdout)

    def test_actual_retention_ipc_fence_without_receipt_consumption(self):
        prefix=(ROOT/'test/x86_64_native_ipc_host.c').read_text().split('int main(int argc,char **argv)',1)[0]
        c=prefix+r'''int main(void) {
    (void)bulk_checks;
    for(unsigned round=0;round<2;round++) {
        for(unsigned s=0;s<4;s++)call(NATIVE_IPC_BIND,s,0);
        request(0,0,49,0,0,0);assert(!r.result);unsigned h=r.handle;
        request(0,0,55,h,gen[1],2);assert(!r.result);
        request(0,0,53,h,71,0);assert(!r.result);
        /* The owner cannot receive its own queued release, even before the
         * child has consumed it. Receiving cannot consume a family receipt. */
        request(0,0,54,h,0,1000);assert(r.result==NATIVE_IPC_PENDING);
        request(1,1,54,h,0,0);assert(!r.result && r.message.payload[0]==71 && !r.ready);
        call(NATIVE_IPC_PUMP,0,99);assert(!r.ready);
        call(NATIVE_IPC_PUMP,0,100);assert(r.ready==1);
        call(NATIVE_IPC_TAKE,0,100);assert(r.result==-110);
        request(0,100,54,h,0,1000);assert(r.result==NATIVE_IPC_PENDING);
        call(NATIVE_IPC_REAP,1,101);assert(r.ready==1);
        call(NATIVE_IPC_TAKE,0,101);assert(r.result==-32);
        request(0,101,54,h,0,1000);assert(r.result==-32);
        request(0,101,52,h,0,0);assert(!r.result);
        for(unsigned s=0;s<4;s++)if(s!=1)call(NATIVE_IPC_REAP,s,101);
        call(NATIVE_IPC_END,0,101);
        for(unsigned s=0;s<4;s++)gen[s]+=4;
    }
    puts("RETENTION_IPC_OK");return 0;
}
'''
        self.retention_build(c,'RETENTION_IPC',['-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_HOST_TEST',
            'kernel/ipc/ipc.c','kernel/init/critical_object.c'])

    def test_actual_retention_heap_seven_step_bound(self):
        c=r'''#define main original_heap_main
#include "test/x86_64_native_heap_host.c"
#undef main
int main(void) {
    start();unsigned baseline=live;
    /* Empty, live8192, freed8192 and each allocation failure prefix. */
    for(unsigned variant=0;variant<14;variant++) {
        if(variant) {owner.generation++;CHECK(invoke(NATIVE_HEAP_BIND,0,0)==0);}
        if(variant) {
            if(variant>=3)fail_at=acquisitions+variant-2;
            int64_t result=complete(invoke(NATIVE_HEAP_MALLOC,8192,0));fail_at=0;
            CHECK(result==-12 || result==(int64_t)NATIVE_HEAP_BASE);
            if(variant==2)CHECK(complete(invoke(NATIVE_HEAP_FREE,(uint64_t)result,0))==0);
        }
        int64_t result=invoke(NATIVE_HEAP_CANCEL,0,0);unsigned steps=0;
        while(result==NATIVE_HEAP_PENDING && steps<7){steps++;result=invoke(NATIVE_HEAP_STEP,0,0);}
        CHECK(result==0 && steps==7 && live==baseline);
        CHECK(!native_heap_state.tasks[0].control.generation);
        CHECK(invoke(NATIVE_HEAP_CANCEL,0,0)==0);
    }
    puts("RETENTION_HEAP_OK");return 0;
}
'''
        self.retention_build(c,'RETENTION_HEAP',['-DREIST_NATIVE_HEAP_HOST_TEST','arch/x86_64/mm/native_heap.c','kernel/init/critical_object.c'])

    def test_actual_retention_reaper_rotation(self):
        source=(ROOT/'arch/x86_64/proc/process_heap.inc').read_text()
        body='process_heap_reapers64:'+source.split('process_heap_reapers64:',1)[1].split('section .bss',1)[0]
        asm='''BITS 64
NATIVE_POOL_TASKS equ 8
NATIVE_TASK_SHIFT equ 10
section .bss
align 16
global process_heap_retire_mask,process_heap_reaper_cursor,process_heap_receipts
process_heap_retire_mask: resd 1
process_heap_reaper_cursor: resd 1
align 16
process_heap_receipts: resb 256
scheduler_current_slot: resd 1
scheduler_tasks: resb 8192
process_run_receipt: resb 32
section .text
global run_reaper
extern heap_step,retire_complete,scheduler_fail
run_reaper:
    push r12
    call process_heap_reapers64
    pop r12
    ret
process_heap_service64:
    call heap_step
    ret
process_run_complete_retire64:
    call retire_complete
    ret
'''+body
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
extern unsigned process_heap_retire_mask,process_heap_reaper_cursor;
extern uint64_t process_heap_receipts[32];
extern void __attribute__((sysv_abi)) run_reaper(void);
static unsigned steps[8],done[8],last,calls,bad;
int64_t __attribute__((sysv_abi)) heap_step(unsigned operation,unsigned slot) {
    if(operation!=5 || slot>=8 || done[slot] || !(process_heap_retire_mask&(1U<<slot)))bad=1;
    last=slot;calls++;return ++steps[slot]==7?0:-4095;
}
void __attribute__((sysv_abi)) retire_complete(void){done[last]++;}
void __attribute__((sysv_abi)) scheduler_fail(void){exit(2);}
int main(void) {
    for(unsigned mask=1;mask<256;mask++)for(unsigned cursor=0;cursor<8;cursor++) {
        process_heap_retire_mask=mask;process_heap_reaper_cursor=cursor;calls=bad=0;
        for(unsigned s=0;s<8;s++){steps[s]=done[s]=0;for(unsigned j=0;j<4;j++)process_heap_receipts[s*4+j]=s+1;}
        for(unsigned turn=0;turn<56;turn++) {
            unsigned before=calls;run_reaper();if(calls-before>1 || bad)return 1;
        }
        if(process_heap_retire_mask || calls>56)return 3;
        for(unsigned s=0;s<8;s++)if(mask&(1U<<s)) {
            if(steps[s]!=7 || done[s]!=1)return 4;
            for(unsigned j=0;j<4;j++)if(process_heap_receipts[s*4+j])return 5;
        } else if(steps[s] || done[s])return 6;
    }
    puts("RETENTION_REAPER_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'RETENTION_REAPER')
        run=(ROOT/'arch/x86_64/proc/process_run.inc').read_text().split('process_run_dispatch64:',1)[1]
        self.assertLess(run.index('call process_heap_reapers64'),run.index('call family_dispatch64'))

    def test_actual_retention_barrier_bounds_and_phase_order(self):
        source=(ROOT/'arch/x86_64/user/task_pool.c').read_text()
        helper='static int service_retained'+source.split('static int service_retained',1)[1].split('#endif',1)[0]
        c=r'''#include <stdint.h>
#include <stdio.h>
#define REIST_X64_PREPARED_V2_BYTES 16
#define REQUIRE(x,n) do {if(!(x))return n;}while(0)
enum {GETPID=1,MALLOC,FREE,IPC_CREATE,IPC_CLOSE,IPC_DELEGATE,SLEEP_MS,MONOTONIC_MS,IPC_RECEIVE_TIMEOUT,YIELD};
static struct {uint64_t mode,owner,phase,record,children[3],oom;} root_witness;
static const void *service_template;static unsigned char import_blob[1],heap[2][16];
static unsigned allocated,port,receives,sleeps,delay,fail_sleep,waits,barriers,bad;static int64_t answer;
static int64_t S0(unsigned op){
 if(op==GETPID)return 1;
 if(op!=YIELD || root_witness.phase!=3)bad=1;
 return ++sleeps==fail_sleep?-1:0;
}
static int64_t s1(unsigned op,uintptr_t arg){
 if(op==SLEEP_MS){bad=1;return -1;}
 if(op==MALLOC)return (int64_t)(uintptr_t)heap[allocated++];
 if(op==IPC_CREATE)*(uint32_t*)arg=++port;return 0;
}
#define S1(op,arg) s1(op,(uintptr_t)(arg))
static void message_init(volatile uint32_t *p,unsigned length){for(unsigned n=0;n<35;n++)p[n]=0;p[0]=1;p[1]=140;p[2]=length;}
static int64_t s3(unsigned op,uint64_t a,uintptr_t b,uint64_t c){
 if(op==IPC_DELEGATE)return 0;
 if(op!=IPC_RECEIVE_TIMEOUT || a!=1 || c!=1000 || root_witness.phase!=3)bad=1;
 volatile uint32_t *p=(void*)b;if(p[0]!=1 || p[1]!=140 || p[2])bad=1;
 receives++;return receives<=delay?-110:answer;
}
#define S3(op,a,b,c) s3(op,a,(uintptr_t)b,c)
static int reist_x64_image_prepare_v2(void *a,const void *b,unsigned n){(void)a;(void)b;(void)n;return 0;}
static int64_t service_create(void *a,unsigned index,uint32_t endpoint,unsigned fault){
 (void)a;(void)endpoint;(void)fault;
 if(root_witness.phase==2)return -11;
 if(root_witness.phase==3){barriers++;if(sleeps!=56 || receives<=delay || answer!=-32)bad=1;return -11;}
 return ((uint64_t)(root_witness.phase==4?12:index+6)<<32)|(index+5);
}
static int64_t release(unsigned endpoint,unsigned index){(void)endpoint;(void)index;return 0;}
static int service_overlap(unsigned n){(void)n;return 0;}
static int service_idle(unsigned n){(void)n;return 0;}
static int service_samples(unsigned n,unsigned idle){(void)n;(void)idle;return 0;}
/* This harness executes root0 only; peer operations belong exclusively to root1. */
static int service_peer_open(uint32_t *endpoint){(void)endpoint;bad=1;return -1;}
static int service_peer_finish(uint32_t endpoint){(void)endpoint;bad=1;return -1;}
static int64_t control(unsigned operation,uint64_t child,unsigned timeout){(void)operation;(void)child;(void)timeout;return -10;}
static int64_t service_wait(uint64_t child){waits++;return 80+(unsigned)child-5;}
'''+helper+self.overlap_root_source(source,'actual_root',0)+r'''
static void reset(void){root_witness=(typeof(root_witness)){0};root_witness.mode=6;allocated=port=receives=sleeps=waits=barriers=bad=0;}
#define CHECK(x) do {if(!(x)){fprintf(stderr,"retained line%d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){
 for(delay=0;delay<8;delay++)for(fail_sleep=0;fail_sleep<=56;fail_sleep++) {
  answer=-32;reset();int result=actual_root(0,0);CHECK(!bad && receives==delay+1);
  if(!fail_sleep)CHECK(result==90 && sleeps==56 && waits==4 && barriers==1);
  else CHECK(result==244 && sleeps==fail_sleep && root_witness.phase==3 && !waits && !barriers);
 }
 int64_t errors[]={0,1,-9,-11,-22,-110,INT64_MIN,INT64_MAX};fail_sleep=0;
 for(unsigned n=0;n<sizeof(errors)/sizeof(errors[0]);n++)for(delay=0;delay<=8;delay++) {
  answer=errors[n];reset();CHECK(actual_root(0,0)==244 && !bad && !sleeps && !waits && !barriers && root_witness.phase==3);
  CHECK(receives==(delay==8 || answer==-110?8:delay+1));
 }
 puts("RETENTION_BARRIER_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'RETENTION_BARRIER')
        run=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        self.assertEqual(run.split('.yield:',1)[1].split('.sleep:',1)[0].strip(),
                         'xor eax, eax\n    jmp process_run_resume64')
        resume=run.split('process_run_resume64:',1)[1].split('process_run_exception64:',1)[0]
        self.assertIn('call scheduler_runqueue_enqueue64',resume)
        self.assertTrue(resume.rstrip().endswith('jmp process_run_dispatch64'))

    def test_actual_parallel_release_order_and_unchanged_modes(self):
        import verify_x86_64_service_cpu as v
        old=(v.BASE/'retention-renewal-stop-source/arch__x86_64__user__task_pool.c').read_text()
        new=(v.BASE/'case6-dispatch-stop-source/arch__x86_64__user__task_pool.c').read_text()
        self.parallel_root_proof(old,new,False)

    def test_actual_dual_release_order_and_fail_closed(self):
        import verify_x86_64_service_cpu as v
        old=(v.BASE/'case6-dispatch-stop-source/arch__x86_64__user__task_pool.c').read_text()
        new=(v.BASE/'dual-stop-source/arch__x86_64__user__task_pool.c').read_text()
        self.parallel_root_proof(old,new,True)

    def test_actual_peer_root_order_and_fail_closed(self):
        import verify_x86_64_service_cpu as v
        old=(v.BASE/'dual-stop-source/arch__x86_64__user__task_pool.c').read_text()
        peer=(v.BASE/'static-stop-source/arch__x86_64__user__task_pool.c').read_text()
        self.parallel_root_proof(old,peer,True,True)

    def test_actual_critical_root_order_and_fail_closed(self):
        import verify_x86_64_service_cpu as v
        peer=(v.BASE/'static-stop-source/arch__x86_64__user__task_pool.c').read_text()
        self.parallel_root_proof(peer,(ROOT/v.FIXTURE).read_text(),True,True,True)

    def test_actual_peer_fence_ipc_and_cleanup_o0_o2(self):
        source=(ROOT/'arch/x86_64/user/task_pool.c').read_text()
        helpers='static int service_peer_open'+source.split('static int service_peer_open',1)[1].split('static int service_retained',1)[0]
        prefix=(ROOT/'test/x86_64_native_ipc_host.c').read_text().split('static void bulk_request',1)[0]
        c=prefix+r'''
enum {IPC_CREATE=49,IPC_CLOSE=52,IPC_RECEIVE_TIMEOUT=54,IPC_DELEGATE=55};
static struct {uint64_t owner;} root_witness;
static unsigned now,receives,closes,grants,creates,fence_after,peer_live,create_fail,close_fail;
static int unexpected;
static void message_init(volatile uint32_t *m,unsigned length){for(unsigned i=0;i<35;i++)m[i]=0;m[0]=1;m[1]=140;m[2]=length;}
static void peer_reap(void){assert(peer_live);call(NATIVE_IPC_REAP,0,now);peer_live=0;}
static int64_t s1(unsigned op,uintptr_t arg){
 if(op==IPC_CREATE){creates++;if(create_fail)return -28;request(1,now,49,0,0,0);if(!r.result)*(uint32_t*)arg=r.handle;return r.result;}
 assert(op==IPC_CLOSE);closes++;if(close_fail)return -9;request(1,now,52,(unsigned)arg,0,0);return r.result;
}
#define S1(op,arg) s1(op,(uintptr_t)(arg))
static int64_t s3(unsigned op,uint64_t a,uintptr_t b,uint64_t t){
 if(op==IPC_DELEGATE){grants++;assert(t==2 && b==root_witness.owner-1);request(1,now,55,(unsigned)a,(unsigned)b,2);return r.result;}
 assert(op==IPC_RECEIVE_TIMEOUT && t==1000);
 volatile uint32_t *m=(volatile uint32_t*)b;assert(m[0]==1 && m[1]==140 && !m[2]);
 for(unsigned i=3;i<35;i++)assert(!m[i]);
 receives++;if(unexpected)return unexpected==1?0:unexpected;
 request(1,now,54,(unsigned)a,0,1000);
 if(r.result==NATIVE_IPC_PENDING){
  /* Neither a stale cleanup nor an unrelated generation can signal EOF. */
  ipc_process_cleanup((int)gen[0],gen[0]+1);call(NATIVE_IPC_PUMP,1,now);assert(!r.ready);
  if(receives>fence_after)peer_reap();else{now+=100;call(NATIVE_IPC_PUMP,1,now);}
  assert(r.ready==2);call(NATIVE_IPC_TAKE,1,now);
 }
 return r.result;
}
#define S3(op,a,b,c) s3(op,(uint64_t)(a),(uintptr_t)(b),(uint64_t)(c))
'''+helpers+r'''
static void begin(unsigned base,int missing){
 now+=1;gen[0]=base;gen[1]=base+1;root_witness.owner=gen[1];peer_live=!missing;
 if(peer_live)call(NATIVE_IPC_BIND,0,now);call(NATIVE_IPC_BIND,1,now);
 receives=closes=grants=creates=create_fail=close_fail=0;unexpected=0;
}
static void finish(void){
 if(peer_live)peer_reap();call(NATIVE_IPC_REAP,1,now);call(NATIVE_IPC_END,1,now);
 ipc_resource_stats_t stats;assert(!ipc_resource_stats(&stats));
 assert(!stats.active_endpoints && !stats.active_capabilities && !stats.queued_messages);
}
int main(int argc,char **argv){
 assert(argc==3);unsigned base=(unsigned)strtoul(argv[1],0,10),mode=(unsigned)strtoul(argv[2],0,10);
 begin(base,mode==10);uint32_t endpoint=777;
 if(mode==11){root_witness.owner=3;assert(service_peer_open(&endpoint)==-1 && endpoint==777 && !creates && !grants);finish();}
 else if(mode==12){create_fail=1;assert(service_peer_open(&endpoint)==-1 && !endpoint && creates==1 && !grants && !closes);finish();}
 else if(mode==10){assert(service_peer_open(&endpoint)==-1 && !endpoint && creates==1 && grants==1 && closes==1);finish();}
 else {
  assert(!service_peer_open(&endpoint) && endpoint && creates==1 && grants==1 && !closes);
  ipc_handle_t previous=endpoint;
  if(mode==0)peer_reap();
  fence_after=mode==9?8:mode?mode-1:0;
  if(mode>=13){unexpected=mode==13?1:mode==14?-9:-5;}
  if(mode==16){unexpected=0;close_fail=1;fence_after=0;}
  int result=service_peer_finish(endpoint);
  if(mode<=8)assert(!result && receives==(mode?mode:1) && !peer_live && closes==1);
  else if(mode==9)assert(result==-1 && receives==8 && peer_live && closes==1);
  else assert(result==-1 && receives==1 && closes==1);
  close_fail=0;finish();
  /* A recreated peer cannot grant a stale endpoint a second lifetime. */
  begin(base+20,0);request(1,now,54,previous,0,0);assert(r.result==-9);finish();
 }
 puts("SERVICE_PEER_IPC_OK");return 0;
}
'''
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-peer-'+uuid.uuid4().hex);folder.mkdir()
        unit=folder/'source.c';unit.write_text(c,encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(argv,name):
            result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:]);return result.stdout
        for opt in ('0','2'):
            exe=folder/('peer-'+opt+'.exe')
            run([host.find_zig(),'cc','-std=c11','-Wall','-Wextra','-Werror','-O'+opt,'-DREIST_NATIVE_IPC',
                 '-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_HOST_TEST','-DREIST_NATIVE_TASK_POOL=1','-DREIST_NATIVE_RUNTIME=1',
                 '-I.','kernel/ipc/ipc.c','kernel/init/critical_object.c',unit,'-o',exe],'compile-'+opt)
            for base in (1,10):
                for case in range(17):self.assertIn('SERVICE_PEER_IPC_OK',run([exe,base,case],f'{opt}-{base}-{case}'))

    def parallel_root_proof(self,old,new,dual,peer=False,critical=False):
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define REIST_X64_PREPARED_V2_BYTES 16
#define REQUIRE(x,n) do {if(!(x))return n;}while(0)
enum {GETPID=1,MALLOC,FREE,IPC_CREATE,IPC_CLOSE,IPC_DELEGATE,SLEEP_MS};
static struct {uint64_t mode,owner,phase,record,children[3],oom;} root_witness;
static const void *service_template;static unsigned char import_blob[1],heap[2][16];
static uint64_t events[128][4],releases[4][3];
static unsigned allocated,port,role,parallel,event_count,release_count,overlaps,barriers,waits,bad,fail_release,fail_overlap;
static unsigned peer_opened,peer_done,work_phase,work_count,last_idle,fail_open,fail_finish,fail_retained;
static void event(unsigned op,uint64_t a,uint64_t b){
 if(event_count==128){bad=1;return;}
 uint64_t *p=events[event_count++];p[0]=op;p[1]=a;p[2]=b;p[3]=root_witness.phase;
}
static uint64_t S0(unsigned op){return op==GETPID?1:0;}
static int64_t s1(unsigned op,uintptr_t arg){
 event(op,op==MALLOC?arg:0,0);
 if(op==MALLOC){if(allocated==2){bad=1;return -1;}return (int64_t)(uintptr_t)heap[allocated++];}
 if(op==IPC_CREATE)*(uint32_t*)arg=++port;return 0;
}
#define S1(op,arg) s1(op,(uintptr_t)(arg))
static int64_t S3(unsigned op,uint64_t a,uint64_t b,uint64_t rights){
 if(op!=IPC_DELEGATE || rights!=2)bad=1;event(op,a,b);return 0;
}
static int reist_x64_image_prepare_v2(void *a,const void *b,unsigned n){(void)a;(void)b;(void)n;return 0;}
static int64_t service_create(void *a,unsigned index,uint32_t endpoint,unsigned fault){
 (void)a;event(20,index,((uint64_t)endpoint<<32)|fault);
 if(!role && root_witness.mode==6 && (root_witness.phase==2 || root_witness.phase==3))return -11;
 if(!role && !index && root_witness.mode>=7 && root_witness.mode<=9 && !root_witness.oom)return -12;
 return ((uint64_t)(root_witness.phase==4?12:index+6)<<32)|(index+5);
}
static int64_t release(unsigned endpoint,unsigned index){
 if(release_count==4){bad=1;return -1;}
 uint64_t *p=releases[release_count++];p[0]=endpoint;p[1]=index;p[2]=root_witness.phase;
 return release_count==fail_release?-1:0;
}
static int service_overlap(unsigned hold){
 if(hold!=(role?3000U:2500U) || release_count!=(role?(DUAL && (parallel || PEER)?3U:0U):(DUAL || parallel?3U:1U)))bad=1;
 overlaps++;event(21,hold,0);return fail_overlap?-1:0;
}
static int service_retained(unsigned endpoint){
 if(endpoint!=1 || (PEER && (CRITICAL?!parallel:parallel)?last_idle!=25:!overlaps) || root_witness.phase!=3)bad=1;
 barriers++;event(22,endpoint,0);return fail_retained?-1:0;
}
static int service_idle(unsigned count){last_idle=count;event(23,count,0);return 0;}
static int service_samples(unsigned count,unsigned idle){work_count++;work_phase=(unsigned)root_witness.phase;event(24,count,idle);return 0;}
#if PEER
static int service_peer_open(uint32_t *endpoint){
 if(!role || root_witness.mode!=6 || root_witness.phase!=1 || allocated || port)bad=1;
 peer_opened++;event(27,0,0);*endpoint=99;return fail_open?-1:0;
}
static int service_peer_finish(uint32_t endpoint){
 if(endpoint!=99 || !peer_opened || waits || root_witness.phase!=2 || release_count!=3 || overlaps!=1)bad=1;
 peer_done=!fail_finish;event(28,endpoint,0);return fail_finish?-1:0;
}
#endif
static int64_t control(unsigned op,uint64_t child,unsigned timeout){event(25,op,child);(void)timeout;return op==2?-10:0;}
static int64_t service_wait(uint64_t child){
 if(role && root_witness.mode==6 && (root_witness.phase!=5 || overlaps!=1 || release_count!=3))bad=1;
 if(PEER && (parallel || CRITICAL) && role && root_witness.mode==6 && !peer_done)bad=1;
 waits++;event(26,child,0);unsigned index=(unsigned)child-5;
 if(!role && !index){
  if(root_witness.mode==2)return (1LL<<32)|134;
  if(root_witness.mode==3 || root_witness.mode==10)return (1LL<<32)|256;
  if(root_witness.mode==4)return 2LL<<32;
 }
 return 80+index+3*role;
}
'''
        c='#define DUAL '+str(int(dual))+'\n#define PEER '+str(int(peer))+'\n#define CRITICAL '+str(int(critical))+'\n'+c
        for label,source in [('old',old),('new',new)]:
            for role in range(2):c+=self.overlap_root_source(source,label+str(role),role)
        c+=r'''
static void reset(unsigned mode,unsigned which,unsigned newer){
 memset(&root_witness,0,sizeof(root_witness));memset(events,0,sizeof(events));memset(releases,0,sizeof(releases));
 root_witness.mode=mode;role=which;parallel=newer;
 allocated=port=event_count=release_count=overlaps=barriers=waits=bad=0;
 peer_opened=peer_done=work_phase=work_count=last_idle=0;
}
static unsigned filtered(uint64_t target[128][4],uint64_t source[128][4],unsigned count){
 unsigned used=0;memset(target,0,128*4*sizeof(uint64_t));
 for(unsigned i=0;i<count;i++)if(source[i][0]!=21 && source[i][0]!=23 && source[i][0]!=24 && source[i][0]!=27 && source[i][0]!=28)
  memcpy(target[used++],source[i],4*sizeof(uint64_t));
 return used;
}
#define CHECK(x) do {if(!(x)){fprintf(stderr,"parallel line%d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){
 int (*old[2])(int,char**)={old0,old1},(*newer[2])(int,char**)={new0,new1};
 for(unsigned mode=0;mode<12;mode++)for(unsigned which=0;which<2;which++){
  uint64_t previous[128][4],sent[4][3];unsigned count,number;
  reset(mode,which,0);int first=old[which](0,0);CHECK(!bad);
  count=event_count;number=release_count;memcpy(previous,events,sizeof(events));memcpy(sent,releases,sizeof(releases));
  reset(mode,which,1);int second=newer[which](0,0);
  CHECK(!bad && first==second && release_count==number);
  if(PEER && mode==6){
   uint64_t a[128][4],b[128][4];CHECK(filtered(a,previous,count)==filtered(b,events,event_count));
   CHECK(!memcmp(a,b,sizeof(a)));
   if(which)CHECK(peer_opened==1 && peer_done && !work_count);
   else if(CRITICAL)CHECK(!peer_opened && !peer_done && !work_count && overlaps==1 && last_idle==2);
   else CHECK(!peer_opened && !peer_done && work_count==1 && work_phase==5 && last_idle==25);
  }else CHECK(event_count==count && !memcmp(previous,events,sizeof(events)));
  if(mode==6 && !which){
   CHECK(number==4 && barriers==1 && waits==4 && overlaps==(PEER && !CRITICAL?0U:1U) && second==90);
   for(unsigned i=0;i<3;i++)CHECK(releases[i][0]==i+1 && releases[i][1]==i && releases[i][2]==3);
   CHECK(releases[3][0]==4 && releases[3][1]==0 && releases[3][2]==5);
   CHECK(sent[0][0]==1 && sent[0][2]==3);
   if(DUAL)CHECK(!memcmp(sent,releases,sizeof(releases)));
   else CHECK(sent[1][0]==4 && sent[1][2]==5);
  }else if(DUAL && mode==6 && which){
   CHECK(number==3 && !barriers && waits==3 && overlaps==1 && second==91);
   for(unsigned i=0;i<3;i++)CHECK(sent[i][0]==i+1 && sent[i][1]==i && sent[i][2]==(PEER?2U:5U) &&
                                releases[i][0]==i+1 && releases[i][1]==i && releases[i][2]==2);
  }else CHECK(!memcmp(sent,releases,sizeof(releases)));
 }
 if(DUAL){
  for(fail_release=1;fail_release<=3;fail_release++){
   reset(6,1,1);int result=new1(0,0);
   CHECK(!bad && result==208 && release_count==fail_release && root_witness.phase==2 && !overlaps && !barriers && !waits);
  }
  fail_release=0;fail_overlap=1;reset(6,1,1);
  CHECK(new1(0,0)==208 && !bad && release_count==3 && overlaps==1 && !barriers && !waits && root_witness.phase==2);
  fail_overlap=0;
 }
 for(fail_release=1;fail_release<=4;fail_release++){
  reset(6,0,1);int result=new0(0,0);CHECK(!bad && release_count==fail_release);
  if(fail_release<=3)CHECK(result==210 && root_witness.phase==3 && !overlaps && !barriers && !waits);
  else CHECK(result==218 && root_witness.phase==5 && overlaps==(PEER && !CRITICAL?0U:1U) && barriers==1 && waits==1);
 }
 if(CRITICAL){
  fail_release=0;fail_overlap=1;reset(6,0,1);
  CHECK(new0(0,0)==210 && !bad && release_count==3 && overlaps==1 && !barriers && !waits && root_witness.phase==3);
  fail_overlap=0;fail_retained=1;reset(6,0,1);
  CHECK(new0(0,0)==244 && !bad && release_count==3 && overlaps==1 && barriers==1 && !waits && root_witness.phase==3);
  fail_retained=0;
 }
 if(PEER){
  fail_release=0;fail_open=1;reset(6,1,1);
  CHECK(new1(0,0)==246 && !bad && peer_opened==1 && !allocated && !port && !release_count && !waits && root_witness.phase==1);
  fail_open=0;fail_finish=1;reset(6,1,1);
  CHECK(new1(0,0)==247 && !bad && peer_opened==1 && !peer_done && release_count==3 && overlaps==1 && !waits && root_witness.phase==2);
 }
 puts("PARALLEL_ROOT_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'PARALLEL_ROOT')

    def guard_function(self,body=None):
        import run_qemu_x86_64_service_cpu as r
        tree=ast.parse(r.observer_body() if body is None else body)
        return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='release_begin')

    def guard_call(self,fn,release,flags,target,mode=8,error=None):
        import run_qemu_x86_64_service_cpu as r
        calls=[]
        def reg(name):
            calls.append(('reg',name))
            if error:raise error
            return flags
        def following(address):calls.append(('following',address));raise LookupError('original following code')
        ns=dict(release=release,reg=reg,mode=lambda:mode,d=following,S={'scheduler_current_slot':17},
                release_guard=getattr(r,'release_guard',None),release_failure_path=target)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual release_begin>','exec'),ns)
        try:answer=ns['release_begin']();outcome=('return',answer)
        except Exception as caught:outcome=(type(caught).__name__,str(caught))
        return outcome,calls

    def test_actual_release_failure_context(self):
        import verify_x86_64_service_cpu as v
        folder=v.BASE/'guard-renewal'/('host-context-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        target=folder/'release-failure.json'
        outcome,calls=self.guard_call(self.guard_function(),None,512,target)
        self.assertEqual(outcome,('AssertionError',''));self.assertEqual(calls,[('reg','eflags')])
        self.assertTrue(target.is_file(),'actual failed release guard must persist its existing operands')
        self.assertLessEqual(target.stat().st_size,1024)
        self.assertEqual(json.loads(target.read_text()),dict(version=1,nested=False,eflags=512,active=None))

    def previous_guard_body(self):
        import run_qemu_x86_64_service_cpu as r
        r=self.sealed_peer_runtime()
        source=(ROOT/'build/codex-agent/r83ap-service-cpu/release-stop-source/scripts__run_qemu_x86_64_service_cpu.py').read_text()
        fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='observer_body')
        namespace=dict(vars(r));exec(compile(ast.Module(body=[fn],type_ignores=[]),'<frozen observer>','exec'),namespace)
        return namespace['observer_body']()

    def test_release_guard_original_short_circuit_and_following_effects(self):
        import io
        from unittest.mock import Mock
        old=self.guard_function(self.previous_guard_body());new=self.guard_function()
        class Sink(io.StringIO):
            def close(self):pass
        for mode in (0,8):
            for release in (None,{},dict(slot=7,gen=12,ret=(1<<64)-1)):
                for flags in (*range(1024),1<<63,(1<<64)-1):
                    sink=Sink();path=Mock();path.open.return_value=sink
                    self.assertEqual(self.guard_call(old,release,flags,path,mode),self.guard_call(new,release,flags,path,mode))
                    failed=mode==8 and (release is not None or flags&512)
                    if failed:
                        path.open.assert_called_once_with('x',encoding='ascii')
                        self.assertLessEqual(len(sink.getvalue().encode('ascii')),1024)
                        self.assertEqual(json.loads(sink.getvalue()),dict(version=1,nested=release is not None,
                            eflags=flags if release is None else None,
                            active={key:release.get(key) for key in ('slot','gen','ret')} if release is not None else None))
                    else:path.open.assert_not_called();self.assertEqual(sink.getvalue(),'')

    def test_release_guard_generated_code_only_adds_failure_context(self):
        import inspect
        import run_qemu_x86_64_service_cpu as r
        r=self.sealed_peer_runtime()
        current=r.observer_body();previous=r.defer_observer_callbacks(self.previous_guard_body(),('Hook','ReleaseEnd'))
        compile(current,'<actual generated observer>','exec')
        call='    release_guard(release,reg,release_failure_path)\n'
        extra='\nfrom pathlib import Path\n'+inspect.getsource(r.release_guard)+"\nrelease_failure_path=Path(CONFIG['cpu_ledger']).with_name('release-failure.json')\n"
        self.assertEqual(current.count(call),1);self.assertEqual(current.count(extra),1)
        normalized=current.replace(call,"    assert release is None and not reg('eflags')&512\n",1).replace(extra,'\nfrom pathlib import Path\n',1)
        self.assertEqual(normalized,previous)

    def test_release_guard_io_and_schema_fail_closed(self):
        from unittest.mock import Mock,patch
        import verify_x86_64_service_cpu as v
        import run_qemu_x86_64_service_cpu as r
        fn=self.guard_function();path=Mock()
        result,calls=self.guard_call(fn,None,512,path,error=OSError('register unavailable'))
        self.assertEqual(result,('OSError','register unavailable'));path.open.assert_not_called()
        for release in ({'slot':-1},{'gen':True},{'ret':1<<64},{'slot':'not an integer'}):
            result,calls=self.guard_call(fn,release,0,path)
            self.assertEqual(result[0],'ValueError');self.assertEqual(calls,[]);path.open.assert_not_called()
        for stage in ('open','write','flush','short'):
            from unittest.mock import MagicMock
            path=MagicMock();out=path.open.return_value.__enter__.return_value
            out.write.side_effect=lambda raw:len(raw)
            if stage=='open':path.open.side_effect=OSError(stage)
            elif stage=='short':out.write.side_effect=lambda raw:len(raw)-1
            else:getattr(out,stage).side_effect=OSError(stage)
            result,calls=self.guard_call(fn,None,512,path)
            self.assertEqual(result[0],'OSError');self.assertEqual(calls,[('reg','eflags')])
        path=Mock()
        with patch.object(r.json,'dumps',return_value='x'*1024):
            self.assertEqual(self.guard_call(fn,None,512,path)[0][0],'ValueError');path.open.assert_not_called()
        folder=v.BASE/'guard-renewal'/('host-exclusive-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        target=folder/'release-failure.json'
        self.guard_call(fn,None,512,target);before=target.read_bytes()
        result,calls=self.guard_call(fn,{},0,target)
        self.assertEqual(result[0],'FileExistsError');self.assertEqual(calls,[]);self.assertEqual(target.read_bytes(),before)

    def test_release_failure_never_qualifies_and_counts_capacity(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import run_qemu_x86_64_service_cpu as r
        folder=Path('bound-host-evidence');failure=folder/'release-failure.json';ledger=folder/r.CPU_FILE
        sizes={failure:100,ledger:168};present=True;symlink=False;count=2046;size=1
        def exists(p):return p==failure and present
        def symbolic(p):return p==failure and symlink
        def read(p):return '\n'.join(json.dumps(dict(bytes=size)) for _ in range(count))
        with patch.object(Path,'exists',exists),patch.object(Path,'is_symlink',symbolic),\
             patch.object(Path,'stat',lambda p:SimpleNamespace(st_size=sizes[p])),patch.object(Path,'read_text',read):
            self.assertEqual(len(r.binary_capacity(folder)),2046)
            count=2047
            with self.assertRaisesRegex(ValueError,'aggregate'):r.binary_capacity(folder)
            present=False;self.assertEqual(len(r.binary_capacity(folder)),2047)
            count=1;size=128*1024*1024-168;self.assertEqual(len(r.binary_capacity(folder)),1)
            present=True
            with self.assertRaisesRegex(ValueError,'aggregate'):r.binary_capacity(folder)
            for value in (0,1025):
                sizes[failure]=value
                with self.assertRaisesRegex(ValueError,'record capacity'):r.binary_capacity(folder)
            with self.assertRaisesRegex(ValueError,'guard failure'):r.validate_capture('', '',0,False,24,'hash',folder)
            present=False;symlink=True
            with self.assertRaisesRegex(ValueError,'guard failure'):r.validate_capture('', '',0,False,24,'hash',folder)
            with self.assertRaisesRegex(ValueError,'record capacity'):r.binary_capacity(folder)

    def overlap_root_source(self,source,name,role):
        suffix=source.split('#if REIST_NATIVE_SERVICE_CPU\n#undef main',1)[1]
        root=suffix.split('int main(int argc,char **argv) {\n#if PROGRAM_ID<2',1)[1].split('#elif PROGRAM_ID==2',1)[0]
        self.assertEqual(root.count('if(PROGRAM_ID==0 && mode==5)__asm__ volatile("ud2");'),1)
        root=root.replace('if(PROGRAM_ID==0 && mode==5)__asm__ volatile("ud2");','if(PROGRAM_ID==0 && mode==5)return 245;')
        return '\n#undef PROGRAM_ID\n#define PROGRAM_ID '+str(role)+'\nstatic int '+name+'(int argc,char **argv) {\n'+root+'}\n'

    def test_actual_case6_root_work_overlaps_hold(self):
        current=(ROOT/'build/codex-agent/r83ap-service-cpu/retention-stop-source/arch__x86_64__user__task_pool.c').read_text()
        previous=(ROOT/'build/codex-agent/r83ap-service-cpu/transport-stop-source/arch__x86_64__user__task_pool.c').read_text()
        idle='static int service_idle'+current.split('static int service_idle',1)[1].split('#endif',1)[0]
        c=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define REIST_X64_PREPARED_V2_BYTES 16
#define REQUIRE(x,n) do {if(!(x))return n;}while(0)
enum {GETPID=1,MALLOC,FREE,IPC_CREATE,IPC_CLOSE,IPC_DELEGATE,SLEEP_MS,MONOTONIC_MS};
static struct {uint64_t mode,owner,phase,record,children[3],oom;} root_witness;
static const void *service_template;
static unsigned char import_blob[1],heap[2][16];
static uint64_t now,work_ms,work_at,hold_begin,events[128][4];
static unsigned role,work_calls,work_phase,allocated,port,event_count,bad,omit_overlap;
static void event(unsigned kind,uint64_t a,uint64_t b) {
    if(event_count>=128){bad=1;return;}
    events[event_count][0]=kind;events[event_count][1]=a;events[event_count][2]=b;
    events[event_count++][3]=root_witness.phase;
}
static uint64_t S0(unsigned op) {return op==GETPID?1:op==MONOTONIC_MS?now:UINT64_MAX;}
static int64_t s1(unsigned op,uintptr_t arg) {
    if(op==SLEEP_MS){if(!arg || arg>100)bad=1;now+=arg;return 0;}
    event(op,op==MALLOC?arg:0,0);
    if(op==MALLOC){if(allocated>=2){bad=1;return -1;}return (int64_t)(uintptr_t)heap[allocated++];}
    if(op==IPC_CREATE)*(uint32_t*)arg=++port;
    return 0;
}
#define S1(op,arg) s1(op,(uintptr_t)(arg))
static int64_t S3(unsigned op,uint64_t a,uint64_t b,uint64_t c) {if(op!=IPC_DELEGATE || c!=2)bad=1;event(op,a,b);return 0;}
static int reist_x64_image_prepare_v2(void *a,const void *b,unsigned n) {(void)a;(void)b;(void)n;return 0;}
static int64_t service_create(void *a,unsigned index,uint32_t endpoint,unsigned fault) {
    (void)a;event(20,index,((uint64_t)endpoint<<32)|fault);
    if(!role && root_witness.mode==6 && (root_witness.phase==2 || root_witness.phase==3))return -11;
    if(!role && !index && root_witness.mode>=7 && root_witness.mode<=9 && !root_witness.oom)return -12;
    return ((uint64_t)(root_witness.phase==4?12:index+3)<<32)|(index+1);
}
static int64_t release(unsigned endpoint,unsigned index) {
    event(21,endpoint,index);
    if(root_witness.mode==6) {
        if(!role && root_witness.phase==3)hold_begin=now;
        else if(now<hold_begin+(role?3000:2500))bad=1;
    }
    return 0;
}
static int64_t service_wait(uint64_t child) {
    event(22,child,0);unsigned index=(unsigned)child-1;
    if(!role && !index) {
        if(root_witness.mode==2)return (1LL<<32)|134;
        if(root_witness.mode==3 || root_witness.mode==10)return (1LL<<32)|256;
        if(root_witness.mode==4)return 2LL<<32;
    }
    return 80+index+3*role;
}
static int64_t control(unsigned operation,uint64_t child,unsigned timeout) {event(23,operation,child);(void)timeout;return operation==2?-10:0;}
static int service_samples(unsigned count,unsigned idle) {
    if(count!=40 || idle || work_calls++)bad=1;
    work_phase=(unsigned)root_witness.phase;work_at=now;now+=work_ms;return 0;
}
'''+idle
        for side,source in [('old',previous),('new',current)]:
            for role in range(2):c+=self.overlap_root_source(source,side+str(role),role)
        c+=r'''
static void reset(unsigned mode,unsigned which,uint64_t duration) {
    memset(&root_witness,0,sizeof(root_witness));root_witness.mode=mode;role=which;
    now=work_at=hold_begin=event_count=bad=work_calls=work_phase=allocated=port=omit_overlap=0;work_ms=duration;
}
#define CHECK(x) do {if(!(x)){fprintf(stderr,"CASE6_OVERLAP_CHECK %u %s\n",__LINE__,#x);return 1;}}while(0)
int main(void) {
    int (*old[2])(int,char**)={old0,old1},(*newer[2])(int,char**)={new0,new1};
    for(unsigned mode=0;mode<12;mode++)for(unsigned which=0;which<2;which++)
    for(unsigned duration=0;duration<=4000;duration+=200) {
        uint64_t prior[128][4],old_end;unsigned prior_count,prior_calls;
        reset(mode,which,duration);int first=old[which](0,0);
        CHECK(!bad);prior_count=event_count;prior_calls=work_calls;old_end=now;memcpy(prior,events,sizeof(prior));
        reset(mode,which,duration);int second=newer[which](0,0);
        CHECK(!bad && first==second && event_count==prior_count && work_calls==prior_calls);
        CHECK(!memcmp(prior,events,event_count*sizeof(events[0])));
        if(mode==6) {
            CHECK(work_calls==1 && work_phase==(which?2:3));
            CHECK(work_at==hold_begin && now>=hold_begin+(which?3000:2500));
            CHECK(now==hold_begin+(duration>(which?3000U:2500U)?duration:(which?3000U:2500U)));
            CHECK(now<=old_end);
        } else CHECK(now==old_end && (mode==5 && !which?work_calls==0:work_phase==5));
    }
    puts("SERVICE_CPU_OVERLAP_ROOT_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'SERVICE_CPU_OVERLAP_ROOT')

    def test_actual_overlap_bounds_and_failure_before_effects(self):
        source=(ROOT/'arch/x86_64/user/task_pool.c').read_text()
        body='static int service_overlap'+source.split('static int service_overlap',1)[1].split('#endif',1)[0]
        c=r'''#include <stdint.h>
#include <stdio.h>
enum {MONOTONIC_MS=42,SLEEP_MS=41};
static uint64_t now,duration,clock_calls,sleeps,work_calls,work_fail,sleep_fail,clock_fail,freeze_clock,regress_clock,bad;
static uint64_t S0(unsigned op) {
    if(op!=MONOTONIC_MS)bad=1;
    clock_calls++;
    if(clock_fail && clock_calls==clock_fail)return UINT64_MAX;
    if(regress_clock && clock_calls==regress_clock)return now-1;
    return now;
}
static int S1(unsigned op,uint64_t ms) {
    if(op!=SLEEP_MS || !ms || ms>100)bad=1;
    sleeps++;
    if(sleep_fail && sleeps==sleep_fail)return -1;
    if(!freeze_clock)now+=ms;
    return 0;
}
static int service_samples(unsigned n,unsigned idle) {
    if(n!=40 || idle)bad=1;
    work_calls++;now+=duration;return work_fail?-1:0;
}
'''+body+r'''
#define CHECK(x) do {if(!(x)){fprintf(stderr,"OVERLAP_BOUND_CHECK %u %s\n",__LINE__,#x);return 1;}}while(0)
static void reset(void) {now=500;duration=clock_calls=sleeps=work_calls=work_fail=sleep_fail=clock_fail=freeze_clock=regress_clock=bad=0;}
int main(void) {
    for(unsigned hold=2500;hold<=3000;hold+=500)
    for(unsigned ms=0;ms<=4000;ms++) {
        reset();duration=ms;CHECK(!service_overlap(hold) && !bad && work_calls==1 && sleeps<=30 && clock_calls<=32);
        CHECK(now==500+(duration>hold?duration:hold));
    }
    for(unsigned bad_hold=0;bad_hold<3200;bad_hold++)if(bad_hold!=2500 && bad_hold!=3000) {
        reset();CHECK(service_overlap(bad_hold)==-1 && !clock_calls && !work_calls && !sleeps);
    }
    reset();CHECK(service_overlap(UINT32_MAX)==-1 && !clock_calls && !work_calls);
    for(unsigned hold=2500;hold<=3000;hold+=500) {
        reset();now=(uint64_t)INT64_MAX-hold;CHECK(!service_overlap(hold) && now==INT64_MAX);
        reset();now=(uint64_t)INT64_MAX-hold+1;CHECK(service_overlap(hold)==-1 && !work_calls && !sleeps);
        reset();clock_fail=1;CHECK(service_overlap(hold)==-1 && !work_calls && !sleeps);
        reset();clock_fail=2;CHECK(service_overlap(hold)==-1 && work_calls==1 && !sleeps);
        reset();work_fail=1;CHECK(service_overlap(hold)==-1 && clock_calls==1 && work_calls==1 && !sleeps);
        reset();sleep_fail=1;CHECK(service_overlap(hold)==-1 && work_calls==1 && sleeps==1);
        reset();freeze_clock=1;CHECK(service_overlap(hold)==-1 && sleeps==31 && clock_calls==32 && work_calls==1);
        reset();regress_clock=2;CHECK(service_overlap(hold)==-1 && !sleeps && work_calls==1);
        reset();freeze_clock=1;regress_clock=3;CHECK(service_overlap(hold)==-1 && sleeps==1 && work_calls==1);
        reset();now=INT64_MAX-3000;duration=4000;CHECK(service_overlap(hold)==-1 && !sleeps);
    }
    puts("SERVICE_CPU_OVERLAP_BOUNDS_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'SERVICE_CPU_OVERLAP_BOUNDS')

    def cpu_start_env(self,states=None,body=None):
        import run_qemu_x86_64_service_cpu as r
        source=r.CPU_OBSERVER if body is None else body
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='cpu_start')
        raw=bytearray(7184);reads=[];events=[]
        states=states or [(1,n+1) for n in range(8)]
        for n,(state,gen) in enumerate(states):struct.pack_into('<2Q',raw,n*1024,state,gen)
        def mem(address,count):
            reads.append((address,count));return bytes(raw[address-0x10000:address-0x10000+count])
        from types import SimpleNamespace
        env=dict(struct=struct,S={'scheduler_tasks':0x10000},mem=mem,starts={},
            cpu_snapshot=lambda slot:(8,100,[slot]*8),cpu_ledger=SimpleNamespace(event=lambda **row:events.append(row)),
            start_hook=SimpleNamespace(enabled=False))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual CPU start>','exec'),env)
        return env,raw,reads,events

    def test_cpu_start_headers_single_bounded_read(self):
        env,raw,reads,events=self.cpu_start_env();env['cpu_start'](0,1)
        self.assertEqual(reads,[(0x10000,7184)])
        self.assertTrue(env['start_hook'].enabled)
        self.assertEqual(events,[dict(kind='cpu_start',slot=0,gen=1,now=100,records=[0]*8)])

    def test_cpu_start_old_new_exact_values_and_enable_policy(self):
        path=ROOT/'build/codex-agent/r83ap-service-cpu/case6-stop-source/scripts__run_qemu_x86_64_service_cpu.py'
        old=next(ast.literal_eval(n.value) for n in ast.parse(path.read_text()).body
                 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CPU_OBSERVER' for t in n.targets))
        for state in range(8):
            for missing in range(9):
                outcomes=[]
                for body in (old,None):
                    env,raw,reads,events=self.cpu_start_env([(state,n+1) for n in range(8)],body)
                    env['starts']={n+1:{} for n in range(8) if n!=missing};env['cpu_start'](3,4)
                    outcomes.append((env['start_hook'].enabled,events))
                self.assertEqual(outcomes[0],outcomes[1])

    def test_cpu_start_headers_exact_length_and_read_failure(self):
        for delta in (-1,1):
            env,raw,reads,events=self.cpu_start_env();env['mem']=lambda address,count:bytes(count+delta)
            with self.assertRaises(AssertionError):env['cpu_start'](0,1)
            self.assertEqual(len(events),1) # Original event precedes header census.
        env,raw,reads,events=self.cpu_start_env()
        def fail(*args):raise OSError('read failure')
        env['mem']=fail
        with self.assertRaisesRegex(OSError,'read failure'):env['cpu_start'](0,1)

    def test_cpu_start_headers_fresh_same_stop_cache(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        env,raw,reads,events=self.cpu_start_env();cache=r.SameStopReads(env)
        def start():env['cpu_start'](0,1)
        wrapped=cache.wrap_stop(lambda hook:hook.fn());hook=SimpleNamespace(fn=start)
        wrapped(hook);self.assertTrue(env['start_hook'].enabled)
        for n in range(8):struct.pack_into('<2Q',raw,n*1024,0,n+1)
        wrapped(hook);self.assertFalse(env['start_hook'].enabled)
        self.assertEqual(reads,[(0x10000,7184)]*2);self.assertFalse(cache.inside or cache.active or cache.entries)

    def test_cpu_snapshot_layout_checked_once_not_guest_data(self):
        import run_qemu_x86_64_service_cpu as r
        symbols=dict(scheduler_cpu_budgets=0x1000,scheduler_cpu_windows=0x1100,scheduler_mode=0x123d,scheduler_last_tick=0x1320)
        self.assertEqual(r.cpu_snapshot_layout(symbols),(0x1000,808,0,256,573,800))
        for name in symbols:
            for value in (-1,True,1<<64):
                with self.assertRaises(AssertionError):r.cpu_snapshot_layout(dict(symbols,**{name:value}))
        for bad in ({'scheduler_mode':0x1101},{'scheduler_last_tick':0x1800},{'scheduler_cpu_windows':0x1080}):
            with self.assertRaises(AssertionError):r.cpu_snapshot_layout(dict(symbols,**bad))

    def test_cpu_snapshot_old_new_exact_words_reads_and_errors(self):
        import run_qemu_x86_64_service_cpu as r
        path=ROOT/'build/codex-agent/r83ap-service-cpu/case6-stop-source/scripts__run_qemu_x86_64_service_cpu.py'
        old=next(ast.literal_eval(n.value) for n in ast.parse(path.read_text()).body
                 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CPU_OBSERVER' for t in n.targets))
        names=('scheduler_cpu_budgets','scheduler_cpu_windows','scheduler_mode','scheduler_last_tick')
        for offsets in ((0,256,524,704),(256,0,524,704),(0,256,700,512),(16,280,0,544)):
            symbols={name:0x10000+offset for name,offset in zip(names,offsets)}
            base,size,*unused=r.cpu_snapshot_layout(symbols);raw=bytearray((i%251 for i in range(size)))
            for slot in range(8):
                values=[]
                for source in (old,r.CPU_OBSERVER):
                    reads=[]
                    def mem(address,count):reads.append((address,count));return bytes(raw)
                    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='cpu_snapshot')
                    env=dict(S=symbols,struct=struct,mem=mem,CPU_LAYOUT=r.cpu_snapshot_layout(symbols))
                    exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual old/new CPU snapshot>','exec'),env)
                    values.append(env['cpu_snapshot'](slot));self.assertEqual(reads,[(base,size)])
                    for delta in (-1,1):
                        env['mem']=lambda a,n:bytes(n+delta)
                        with self.assertRaises(AssertionError):env['cpu_snapshot'](slot)
                self.assertEqual(values[0],values[1])
            # The immutable layout retains no raw memory; subsequent calls see
            # a changed target through the same read path.
            env['mem']=lambda a,n:bytes(raw);before=env['cpu_snapshot'](0)
            raw[symbols[names[0]]-base]^=1;self.assertNotEqual(env['cpu_snapshot'](0),before)

    def user_env(self,code=None):
        import run_qemu_x86_64_service_cpu as r
        source=r.observer_body() if code is None else code
        selected=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('user','read_user_spans')]
        self.assertEqual(sum(n.name=='user' for n in selected),1)
        env=dict(DM=0xffff800000000000,MASK=0x3fffff000,struct=struct)
        exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual generated user reads>','exec'),env)
        return env

    def user_mapping(self,env,va,size,frames=None):
        pages=(size+(va&4095)+4095)//4096;tables={};reads=[];payloads=[]
        frames=[0x100000000+i*4096 for i in range(pages)] if frames is None else frames
        self.assertEqual(len(frames),pages)
        allocated={():0x200000}
        for i,frame in enumerate(frames):
            address=(va&~4095)+i*4096;key=()
            for shift in (39,30,21):
                parent=allocated[key];index=(address>>shift)&511;key+=index,
                if key not in allocated:allocated[key]=0x200000+len(allocated)*4096
                tables[env['DM']+parent+index*8]=allocated[key]|7
            tables[env['DM']+allocated[key]+((address>>12)&511)*8]=frame|5
        def data(address,count):return bytes((address+i)%251 for i in range(count))
        def mem(address,count):
            reads.append((address,count))
            if address in tables:
                return b''.join(struct.pack('<Q',tables.get(p,0)) for p in range(address,address+count,8))
            payloads.append((address,count));return data(address,count)
        env['mem']=mem;expected=bytearray();remaining=size
        for i,frame in enumerate(frames):
            offset=va&4095 if i==0 else 0;count=min(remaining,4096-offset)
            expected+=data(env['DM']+frame+offset,count);remaining-=count
        return tables,reads,payloads,bytes(expected)

    def test_user_contiguous_payload_coalesced(self):
        env=self.user_env();va=0x400123;size=266336
        tables,reads,payloads,expected=self.user_mapping(env,va,size)
        self.assertEqual(env['user']((0,1,0x200000),va,size),expected)
        self.assertEqual(payloads,[(env['DM']+0x100000000+0x123,size)])
        self.assertEqual(len(reads),5) # Four exact table spans plus one payload.

    def test_user_rejects_short_payload(self):
        env=self.user_env();va=0x400123;size=266336
        tables,reads,payloads,expected=self.user_mapping(env,va,size);original=env['mem']
        def short(address,count):
            raw=original(address,count)
            return raw if address in tables else raw[:-1]
        env['mem']=short
        with self.assertRaisesRegex(ValueError,'user payload length'):
            env['user']((0,1,0x200000),va,size)

    def test_user_old_new_exact_spans_and_virtual_order(self):
        import run_qemu_x86_64_file_launch as inherited
        for va,size in ((0x400000,0),(0x400000,1),(0x400fff,1),(0x400fff,4098),
                        (0x5fffff,8194),((1<<30)-7,32768),((1<<39)-7,32768),(0x400123,266336)):
            pages=(size+(va&4095)+4095)//4096
            for layout in ('contiguous','fragmented','alias','reverse'):
                with self.subTest(va=va,size=size,layout=layout):
                    order=list(range(pages))
                    if layout=='fragmented':order=[i*2 for i in order]
                    if layout=='alias':order=[i%2 for i in order]
                    if layout=='reverse':order.reverse()
                    frames=[0x100000000+i*4096 for i in order];results=[];logs=[]
                    for source in (inherited.FILE_USER_READ,None):
                        env=self.user_env(source);tables,reads,payloads,expected=self.user_mapping(env,va,size,frames)
                        results.append(env['user']((0,1,0x200000),va,size));logs.append(reads)
                        self.assertEqual(results[-1],expected)
                        self.assertEqual(sum(n for a,n in payloads),size)
                    self.assertEqual(results[0],results[1]);self.assertEqual(logs[0],logs[1])

    def test_user_bounds_and_malformed_tables_before_payload(self):
        for va,n in ((-1,1),(1<<64,0),((1<<64)-1,2),(0,-1),(0,270337),(True,1),(0,True),(0,1.0)):
            env=self.user_env();env['mem']=lambda *args:self.fail('invalid range read')
            with self.subTest(va=va,n=n),self.assertRaises(AssertionError):env['user']((0,1,0x200000),va,n)
        env=self.user_env();va=0x400fff;n=270336
        tables,reads,payloads,expected=self.user_mapping(env,va,n)
        self.assertEqual(env['user']((0,1,0x200000),va,n),expected)
        self.assertEqual(len([e for e in tables.values() if e&~4095>=1<<32]),67)
        for failure in ('missing-root','large-root','large-pdpt','large-pd','missing-last','kernel-last','short-table','long-table'):
            env=self.user_env();va=0x5fffff;n=8194
            tables,reads,payloads,expected=self.user_mapping(env,va,n);original=env['mem']
            addresses=list(tables);root=env['DM']+0x200000
            if failure=='missing-root':tables[root]=0
            if failure=='large-root':tables[root]|=128
            if failure=='large-pdpt':tables[env['DM']+0x201000]|=128
            if failure=='large-pd':tables[env['DM']+0x202000+16]|=128
            if failure=='missing-last':tables[addresses[-1]]=0
            if failure=='kernel-last':tables[addresses[-1]]&=~4
            if failure in ('short-table','long-table'):
                env['mem']=lambda a,n:original(a,n)[:-1] if failure=='short-table' else original(a,n)+b'x'
            with self.subTest(failure=failure),self.assertRaises(AssertionError):env['user']((0,1,0x200000),va,n)
            self.assertFalse(payloads) # Validate even the last leaf before any payload.

    def test_user_failed_payload_stops_without_partial_result(self):
        for failure in ('short','long','io'):
            env=self.user_env();va=0x400fff;n=8194
            tables,reads,payloads,expected=self.user_mapping(env,va,n,[0x100000000+i*8192 for i in range(4)])
            original=env['mem']
            def bad(a,n):
                raw=original(a,n)
                if a in tables:return raw
                if len(payloads)==2:
                    if failure=='io':raise OSError('payload failed')
                    return raw[:-1] if failure=='short' else raw+b'x'
                return raw
            env['mem']=bad
            with self.subTest(failure=failure),self.assertRaises((ValueError,OSError)):
                env['user']((0,1,0x200000),va,n)
            self.assertEqual(len(payloads),2)

    def test_user_actual_binary_reader_and_same_stop_invalidation(self):
        import qemu_binary_memory as binary
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        env=self.user_env();va=0x400123;n=266336;physical=0x100000000
        tables,reads,payloads,expected=self.user_mapping(env,va,n);raw=env['mem']
        other=self.user_env();alias_tables,_,_,_=self.user_mapping(other,binary.DM+physical+0x123,n)
        alias_tables={a+0x100000:(e+0x100000 if e&~4095<1<<32 else e) for a,e in alias_tables.items()}
        revision=[False]
        def original(a,n):
            if binary.HIGH<=a<binary.HIGH+0x8000000:
                address=a-binary.HIGH+binary.DM
                return b''.join(struct.pack('<Q',alias_tables.get(p,0)) for p in range(address,address+n,8))
            result=raw(a,n)
            return bytes(x^255 for x in result) if a not in tables and revision[0] else result
        folder=ROOT/'build/codex-agent'/('cpu-user-host-'+uuid.uuid4().hex);folder.mkdir()
        peer=Mock()
        def save(p,size,path):
            self.assertEqual((p,size),(physical+0x123,n))
            with path.open('xb') as out:out.write(original(binary.DM+p,size))
        peer.save.side_effect=save
        env['mem']=original;cache=r.SameStopReads(env)
        reader=binary.Reader(0,'host',folder,4096,original,lambda:0x300000,True)
        env['mem']=reader.read
        def syscall():
            wanted=bytes(x^255 for x in expected) if revision[0] else expected
            self.assertEqual(env['user']((0,1,0x200000),va,n),wanted)
            self.assertEqual(env['user']((0,1,0x200000),va,n),wanted)
        wrapper=reader.wrap_stop(cache.wrap_stop(lambda hook:hook.fn()))
        with patch.object(binary,'QMP',return_value=peer) as connect:
            for revision[0] in (False,True):
                wrapper(SimpleNamespace(fn=syscall))
                self.assertFalse(reader.in_stop);self.assertIsNone(reader.client)
                self.assertFalse(cache.entries);self.assertFalse(cache.inside)
            self.assertEqual(connect.call_count,2)
        self.assertEqual(peer.save.call_count,2);self.assertEqual(peer.close.call_count,2)
        records=[json.loads(line) for line in (folder/'reads.jsonl').read_text().splitlines()]
        self.assertEqual([row['equivalence'] for row in records],['high',None])
        self.assertEqual([row['bytes'] for row in records],[n,n])

    def capacity_env(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        code=r.observer_body();names=('capacity_arm','capacity_complete','receipt_capacity')
        tree=ast.parse(code);selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        self.assertEqual({n.name for n in selected},set(names))
        memory=bytearray(512);words=[0]*9;root=[2,1];events=[];reads=[]
        for slot in range(2,8):struct.pack_into('<Q',memory,slot*64+40,2)
        def mem(a,n):reads.append((a,n));return bytes(memory[a:a+n])
        env=dict(CASE=6,S={'family_records':0},CONFIG={'root_data':[4096]},struct=struct,
            mode=lambda:8,task=lambda slot:root if slot==0 else [0],
            user=lambda t,a,n:struct.pack('<9Q',*words),mem=mem,q=lambda a:struct.unpack('<Q',mem(a,8))[0],
            capacity_seen=set(),capacity_owner=None,capacity_hooks=[SimpleNamespace(enabled=False) for _ in range(2)],
            emit=lambda kind,**kw:events.append(dict(kind=kind,**kw)))
        exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual capacity hooks>','exec'),env)
        return env,memory,words,root,events,reads

    def test_capacity_actual_two_generation_lifecycle(self):
        import run_qemu_x86_64_service_cpu as r
        env,memory,words,root,events,reads=self.capacity_env()
        body=ast.parse(r.observer_body())
        start=next(n for n in body.body if isinstance(n,ast.FunctionDef) and n.name=='start')
        arm=next(n for n in start.body if isinstance(n,ast.If) and ast.unparse(n.test)=='slot == 0 and CASE == 6')
        arm_code=compile(ast.Module(body=[arm],type_ignores=[]),'<actual root rearm>','exec')
        for generation in (1,10):
            root[1]=generation;words[3]=0;env.update(slot=0,gen=generation);exec(arm_code,env)
            self.assertTrue(all(h.enabled for h in env['capacity_hooks']))
            env['receipt_capacity']();self.assertEqual(len(events),(generation==10)*2)
            words[3]=3;env['receipt_capacity']();env['receipt_capacity']()
            self.assertTrue(all(h.enabled for h in env['capacity_hooks']))
            words[3]=4;words[4]=generation<<32|2;struct.pack_into('<Q',memory,2*64+40,4)
            env['receipt_capacity']();env['receipt_capacity']()
            self.assertFalse(any(h.enabled for h in env['capacity_hooks']))
        self.assertEqual([(e['gen'],e['phase'],e['occupied'],e['receipt']) for e in events],
                         [(1,3,6,0),(1,4,6,1),(10,3,6,0),(10,4,6,1)])
        self.assertEqual(reads.count((128,384)),4)
        self.assertFalse(any(n==64 for a,n in reads))
        with self.assertRaises(AssertionError):env['capacity_arm'](19)
        env.update(slot=1,gen=11);exec(arm_code,env)
        self.assertEqual(env['capacity_owner'],10) # Peer first entry never rearms.

    def test_capacity_actual_rejects_missing_stale_or_invalid_proof(self):
        for failure in ('early','missing','stale','occupancy','receipt','live','rearm','duplicate'):
            with self.subTest(failure=failure):
                env,memory,words,root,events,reads=self.capacity_env()
                if failure!='early':env['capacity_arm'](1)
                words[3]=3
                if failure=='stale':root[1]=10
                if failure=='occupancy':struct.pack_into('<Q',memory,7*64+40,0)
                if failure in ('missing','receipt','live'):
                    if failure!='missing':env['receipt_capacity']()
                    words[3]=4;words[4]=2
                    if failure!='receipt':struct.pack_into('<Q',memory,2*64+40,4)
                    if failure=='live':env['task']=lambda slot:root if slot==0 else [1]
                with self.assertRaises(AssertionError):
                    if failure in ('rearm','duplicate'):env['capacity_arm'](10 if failure=='rearm' else 1)
                    else:env['receipt_capacity']()
                if failure!='early':self.assertTrue(all(h.enabled for h in env['capacity_hooks']))

    def test_same_stop_start_read_prefix_invalidates_before_write(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        memory=bytearray(range(64));calls=[];env={}
        def mem(a,n):calls.append((a,n));return bytes(memory[a:a+n])
        env['mem']=mem;cache=r.SameStopReads(env)
        def start():
            self.assertEqual(env['mem'](0,32),env['mem'](0,32))
            self.assertEqual(len(calls),1)
            cache.before_write();self.assertFalse(cache.active);self.assertFalse(cache.entries)
            memory[:32]=bytes(32);self.assertEqual(env['mem'](0,32),bytes(32))
            self.assertEqual(len(calls),2)
        cache.wrap_stop(lambda hook:hook.fn())(SimpleNamespace(fn=start))
        self.assertFalse(cache.inside);self.assertFalse(cache.entries)
        with self.assertRaises(ValueError):cache.before_write()
        code=r.observer_body();start_node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='start')
        # Execute the actual write tail with cached stale pre-write data. Removing
        # or moving invalidation must fail the original post-write comparison.
        tail=next(i for i,n in enumerate(start_node.body[-1].body) if isinstance(n,ast.Expr) and
                  isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='stop_reads.before_write')
        statement=start_node.body[-1].body[tail:]
        raw={8:bytes(8)};cached={8:bytes(8)};trace=[]
        def read(a,n):return cached.get(a,raw[a])
        def clear():cached.clear();trace.append('invalidate')
        def write(a,data):self.assertEqual(trace,['invalidate']);raw[a]=data
        actual=dict(stop_reads=SimpleNamespace(before_write=clear),gdb=SimpleNamespace(selected_inferior=lambda:SimpleNamespace(write_memory=write)),
                    target=8,struct=struct,CASE=6,mem=read,emit=lambda *a,**kw:None,slot=0,gen=1,address=0,leaf=0,MASK=0)
        exec(compile(ast.Module(body=statement,type_ignores=[]),'<actual injection tail>','exec'),actual)

    def test_same_stop_reads_actual_forwarding_and_invalidation(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        calls=[];memory=bytearray(range(128));env={}
        def read(a,n):calls.append((a,n));return bytes(memory[a:a+n])
        env['mem']=lambda *args:self.fail('reader captured before binary transport installation')
        cache=r.SameStopReads(env)
        def syscall():
            self.assertEqual(env['mem'](16,32),bytes(memory[16:48]))
            self.assertEqual(env['mem'](16,32),bytes(memory[16:48]))
            self.assertEqual(env['mem'](24,8),bytes(memory[24:32]))
            return 71
        wrapped=cache.wrap_stop(lambda hook:hook.fn())
        env['mem']=read # The binary transport installs its reader last.
        self.assertEqual(wrapped(SimpleNamespace(fn=syscall)),71)
        self.assertEqual(calls,[(16,32)])
        self.assertFalse(cache.active);self.assertFalse(cache.entries);self.assertEqual(cache.used,0)
        memory[16:48]=bytes([99])*32
        self.assertEqual(wrapped(SimpleNamespace(fn=syscall)),71)
        self.assertEqual(calls,[(16,32)]*2) # Never reuse across a resume.
        def allocation():
            before=env['mem'](16,8);memory[16:24]=bytes(8)
            self.assertNotEqual(env['mem'](16,8),before)
        wrapped(SimpleNamespace(fn=allocation)) # Register-mutating allocator cannot cache.
        self.assertEqual(calls[-2:],[(16,8)]*2)
        class ReleaseEnd:pass
        def release(hook):
            self.assertEqual(env['mem'](48,8),env['mem'](48,8));return False
        self.assertIs(cache.wrap_stop(release)(ReleaseEnd()),False)
        self.assertEqual(calls[-1],(48,8));self.assertEqual(calls.count((48,8)),1)
        self.assertEqual(env['mem'](0,8),bytes(memory[:8])) # Outside a stop: forward.

    def test_same_stop_reads_bounds_and_failure_cleanup(self):
        import run_qemu_x86_64_service_cpu as r
        from types import SimpleNamespace
        calls=[];env={}
        def read(a,n):calls.append((a,n));return bytes([a&255])*n
        env['mem']=read;cache=r.SameStopReads(env)
        def syscall():
            for a in range(257):self.assertEqual(env['mem'](a*16,8),bytes([a*16&255])*8)
            self.assertEqual(len(cache.entries),256);self.assertEqual(cache.used,2048)
            env['mem'](4096,8);self.assertEqual(calls.count((4096,8)),2)
        wrapper=cache.wrap_stop(lambda hook:hook.fn());hook=SimpleNamespace(fn=syscall)
        wrapper(hook);self.assertFalse(cache.entries)
        def syscall():
            env['mem'](0,1024*1024);env['mem'](2*1024*1024,8)
            self.assertEqual(cache.used,1024*1024);self.assertEqual(len(cache.entries),1)
            raise RuntimeError('callback failed')
        with self.assertRaisesRegex(RuntimeError,'callback failed'):wrapper(SimpleNamespace(fn=syscall))
        self.assertFalse(cache.active);self.assertFalse(cache.entries);self.assertEqual(cache.used,0)
        def syscall():wrapper(hook)
        with self.assertRaisesRegex(ValueError,'nested'):wrapper(SimpleNamespace(fn=syscall))
        self.assertFalse(cache.entries)
        for result in (b'',b'123456789'):
            env={'mem':lambda a,n:result};cache=r.SameStopReads(env)
            def syscall():env['mem'](0,8)
            with self.assertRaisesRegex(ValueError,'length'):cache.wrap_stop(lambda h:h.fn())(SimpleNamespace(fn=syscall))
            self.assertFalse(cache.entries);self.assertFalse(cache.active)
        def failure(a,n):raise OSError('read failed')
        env={'mem':failure};cache=r.SameStopReads(env)
        def syscall():env['mem'](0,8)
        with self.assertRaisesRegex(OSError,'read failed'):cache.wrap_stop(lambda h:h.fn())(SimpleNamespace(fn=syscall))
        self.assertFalse(cache.entries);self.assertFalse(cache.active)

    def test_same_stop_reads_inside_final_binary_reader(self):
        import run_qemu_x86_64_service_cpu as r
        from qemu_binary_memory import Reader
        from types import SimpleNamespace
        from unittest.mock import patch
        env={};calls=[]
        def legacy(a,n):calls.append((a,n));return bytes([42])*n
        env['mem']=legacy;cache=r.SameStopReads(env)
        reader=Reader(0,'host',ROOT/'build/codex-agent',4096,legacy,lambda:0,True)
        def syscall():
            self.assertTrue(reader.in_stop);self.assertTrue(cache.active)
            self.assertEqual(env['mem'](16,8),env['mem'](16,8));return False
        wrapper=reader.wrap_stop(cache.wrap_stop(lambda hook:hook.fn()))
        env['mem']=reader.read
        with patch.object(reader,'close',wraps=reader.close) as close:
            self.assertIs(wrapper(SimpleNamespace(fn=syscall)),False)
            self.assertEqual(close.call_count,1)
        self.assertEqual(cache.original,reader.read);self.assertEqual(calls,[(16,8)])
        self.assertFalse(reader.in_stop);self.assertFalse(cache.active)
        def syscall():env['mem'](16,8);raise RuntimeError('actual callback failure')
        with patch.object(reader,'close',wraps=reader.close) as close:
            with self.assertRaisesRegex(RuntimeError,'actual callback failure'):wrapper(SimpleNamespace(fn=syscall))
            self.assertEqual(close.call_count,1)
        self.assertTrue(reader.failed);self.assertFalse(reader.in_stop);self.assertFalse(cache.entries)

    def test_packed_observer_configuration_exact_and_bounded(self):
        import run_qemu_x86_64_service_cpu as r
        import zlib
        raw=bytes(range(256))*1040+bytes(96);self.assertEqual(len(raw),266336)
        packed=zlib.compress(raw,9);sha=hashlib.sha256(raw).hexdigest()
        self.assertEqual(r.decode_child_record(packed,sha),raw)
        for bad in (b'',packed[:-1],packed+b'x',packed+packed,zlib.compress(raw[:-1]),
                    zlib.compress(raw+b'x'),zlib.compress(bytes(2*1024*1024)),bytes(266337)):
            with self.assertRaises((ValueError,zlib.error)):r.decode_child_record(bad,sha)
        with self.assertRaises(ValueError):r.decode_child_record(packed,'0'*64)
        config={'s':{'known':123},'cs':{},'child_record':raw,'child_data':7,'child_bss':8,'root_data':[1,2]}
        folder=ROOT/'build/codex-agent/host-config-only'
        code=r.observer(config,folder,7,0);prefix=code.split('\npython\n',1)[1].split(r.observer_body(),1)[0]
        env={};exec(compile(prefix,'actual packed config','exec'),env)
        self.assertEqual(env['CONFIG'],dict(config,case=7,oom=0,cpu_ledger=(folder/r.CPU_FILE).as_posix()))
        self.assertEqual(config['child_record'],raw);self.assertLess(len(prefix),len(repr(config))//4)

    def test_packed_config_missing_gdb_zlib_uses_bounded_host(self):
        import builtins,zlib
        import run_qemu_x86_64_service_cpu as r
        from unittest.mock import patch
        raw=bytes(266336);packed=zlib.compress(raw,9);sha=hashlib.sha256(raw).hexdigest()
        original=builtins.__import__
        def missing(name,*args,**kwargs):
            if name=='zlib':raise ModuleNotFoundError("No module named 'zlib'",name='zlib')
            return original(name,*args,**kwargs)
        with patch.object(builtins,'__import__',side_effect=missing):
            with patch.object(subprocess,'run',wraps=subprocess.run) as run:
                self.assertEqual(r.decode_child_record(packed,sha,sys.executable),raw)
                self.assertEqual(run.call_count,1);args,kw=run.call_args
                self.assertEqual(args[0][:4],[sys.executable,'-I','-S','-c'])
                self.assertEqual(kw['timeout'],2);self.assertEqual(kw['input'],packed);self.assertNotIn('shell',kw)
            for bad in (packed[:-1],packed+b'x',packed+packed,zlib.compress(raw+b'x'),zlib.compress(bytes(2*1024*1024))):
                with self.assertRaises(ValueError):r.decode_child_record(bad,sha,sys.executable)
            with self.assertRaises(ValueError):r.decode_child_record(packed,'0'*64,sys.executable)
            with self.assertRaises(ModuleNotFoundError):r.decode_child_record(packed,sha)
            with patch.object(subprocess,'run',side_effect=subprocess.TimeoutExpired('pinned decoder',2)):
                with self.assertRaises(subprocess.TimeoutExpired):r.decode_child_record(packed,sha,sys.executable)

    def test_actual_gdb_decodes_config_without_a_guest(self):
        import run_qemu_x86_64_service_cpu as r
        import verify_x86_64_service_cpu as v
        tools=v.read(v.BASE/'baseline.json')['tools_sha256']
        debuggers=[name for name in tools if Path(name).name.lower()=='gdb.exe'];self.assertEqual(len(debuggers),1)
        self.assertEqual(v.digest(Path(debuggers[0])),tools[debuggers[0]])
        # This host-only decoder gate precedes the new build. Exercise GDB with
        # the preserved, hash-bound image; runtime gates cover the new image.
        stopped=v.read(v.BASE/'verification-status-transport-stopped.json')
        image=ROOT/stopped['retained_service_image']['path']
        self.assertEqual(v.link(image),stopped['retained_service_image'])
        prefix=image.parent.relative_to(ROOT).as_posix()+'/'
        artifacts={name:sha for name,sha in stopped['evidence_sha256'].items() if name.startswith(prefix)}
        self.assertIn(image.relative_to(ROOT).as_posix(),artifacts)
        v.verify_files(artifacts)
        config=r.pool.image_config(image);folder=v.BASE/('host-gdb-config-'+uuid.uuid4().hex);folder.mkdir()
        code=r.observer(config,folder,0,None).split('\npython\n',1)[1].split(r.observer_body(),1)[0]
        sha=hashlib.sha256(config['child_record']).hexdigest()
        script=folder/'config.gdb'
        with script.open('x') as out:
            out.write('python\n'+code+"\nimport hashlib\nassert hashlib.sha256(CONFIG['child_record']).hexdigest()=="+repr(sha)+
                      "\nprint('SERVICE_CPU_GDB_CONFIG_OK')\nend\n")
        self.assertLess(script.stat().st_size,262144)
        result=subprocess.run([debuggers[0],'-nx','-batch','-x',str(script)],cwd=ROOT,capture_output=True,text=True,
                              timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (folder/'config.log').open('x') as out:out.write(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SERVICE_CPU_GDB_CONFIG_OK',result.stdout)

    def compact(self,trace,folder):
        import run_qemu_x86_64_service_cpu as r
        lines=[];writer=r.CPULedger(folder/r.CPU_FILE,lines.append)
        for line in trace.splitlines(keepends=True):
            event=json.loads(line[10:]) if line.startswith('TASK_POOL ') else {}
            if event.get('kind') in r.CPU_KINDS:writer.event(**event)
            else:
                if event.get('kind')=='finish' and event.get('run')==2:writer.finish()
                lines.append(line)
        if not writer.closed:writer.finish()
        return ''.join(lines)

    def test_compact_actual_failed_trace_round_trip(self):
        import run_qemu_x86_64_service_cpu as r
        base=ROOT/'build/codex-agent/r83ap-service-cpu'
        old=base/'guests/attempt-764bb9ea734242208aed013534a1816f/guest-0-4096'
        trace=(old/'frame-trace.log').read_text();serial=(old/'guest.log').read_text()
        self.assertGreater((old/'frame-trace.log').stat().st_size,65536)
        self.assertTrue(json.loads((old/'capture-metrics.json').read_text())['failed'])
        folder=base/('host-ledger-'+uuid.uuid4().hex);folder.mkdir()
        compact=self.compact(trace,folder);self.assertLess(len(compact.encode()),65536)
        raw=(folder/r.CPU_FILE).read_bytes()
        self.assertEqual(len(raw),860*168)
        expanded=r.expand_cpu_trace(compact,raw)
        events=lambda text:[json.loads(line[10:]) for line in text.splitlines() if line.startswith('TASK_POOL ')]
        self.assertEqual(events(expanded),events(trace))
        result=json.loads((old.parent/'summary.json').read_text())
        self.assertEqual(len(r.validate_capture(serial,compact,0,None,result['allocations'],result['child_sha256'],folder)),16)
        # A host re-encoding is not a guest qualification and cannot change the
        # original failed capture, matrix, byte bound or frozen receipts.
        self.assertFalse(result['passed'])
        self.assertTrue(json.loads((old/'capture-metrics.json').read_text())['failed'])

    def test_compact_capacity_and_actual_buffered_writer(self):
        import run_qemu_x86_64_service_cpu as r
        from unittest.mock import patch
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-ledger-'+uuid.uuid4().hex);folder.mkdir()
        lines=[];path=folder/r.CPU_FILE
        with patch.object(Path,'open',autospec=True,side_effect=Path.open) as opened:
            writer=r.CPULedger(path,lines.append)
            for i in range(36):writer.event(kind='cpu_start' if i%2==0 else 'cpu_final',slot=i%8,gen=i+1,now=i,records=[0]*8)
            for i in range(2048):writer.event(kind='cpu_charge',slot=i%8,gen=i+1,now=i,result=1,before=[0]*8,after=[(1<<64)-1]*8)
            with self.assertRaises(ValueError):writer.event(kind='cpu_charge',slot=0,gen=1,now=1,result=1,before=[0]*8,after=[0]*8)
            self.assertEqual(opened.call_count,1)
            writer.finish()
        raw=path.read_bytes();trace=''.join(lines)
        self.assertEqual(len(raw),2084*168);self.assertLess(len(trace.encode()),65536)
        self.assertEqual(r.expand_cpu_trace(trace,raw).count('TASK_POOL '),2084)
        with self.assertRaises(ValueError):writer.finish()
        with self.assertRaises(ValueError):writer.event(kind='cpu_start',slot=0,gen=1,now=0,records=[0]*8)
        with self.assertRaises(FileExistsError):r.CPULedger(path,lines.append)
        for key,bad in [('slot',True),('slot',8),('gen',0),('gen',1<<31),('now',1<<60),('records',[0]*7),('records',[False]*8),('records',[-1]*8),('kind','unknown')]:
            with self.assertRaises(ValueError):r.cpu_pack(1,dict(kind='cpu_start',slot=0,gen=1,now=0,records=[0]*8,**{})|{key:bad})

    def test_compact_rejects_unbound_or_damaged_evidence(self):
        import run_qemu_x86_64_service_cpu as r
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-ledger-'+uuid.uuid4().hex);folder.mkdir()
        serial,events,oom,count,sha=self.sample(0)
        trace=self.compact(''.join('TASK_POOL '+json.dumps(e)+'\n' for e in events),folder)
        raw=(folder/r.CPU_FILE).read_bytes()
        self.assertEqual(len(r.validate(serial,r.expand_cpu_trace(trace,raw),0,oom,count,sha)),16)
        footer=next(line for line in trace.splitlines(keepends=True) if line.startswith('CPU1_END '))
        for bad in [trace.replace('CPU1 1\n','',1),trace.replace('CPU1 1\n','CPU1 1\nCPU1 1\n',1),
                    trace.replace('CPU1 1\n','CPU1 2\n',1),trace.replace('CPU1 1\n','CPU1 01\n',1),
                    trace.replace(footer,''),trace+footer,trace+'CPU1 1\n',trace.replace('CPU1 1\n','CPU2 1\n',1),
                    trace+'TASK_POOL '+json.dumps(next(e for e in events if e['kind']=='cpu_start'))+'\n',
                    'x'*65537+trace]:
            with self.assertRaises(ValueError):r.expand_cpu_trace(bad,raw)
        for bad in (b'',raw[:-1],raw+bytes(168),bytes(2085*168),bytes([raw[0]^1])+raw[1:]):
            with self.assertRaises(ValueError):r.expand_cpu_trace(trace,bad)
        def rebound(data):return trace.replace(hashlib.sha256(raw).hexdigest(),hashlib.sha256(data).hexdigest())
        for offset,fmt,value in ((0,'I',2),(4,'I',3),(8,'I',2),(12,'I',8),(16,'Q',0),(24,'Q',1<<60),(32,'Q',1),(104,'Q',1)):
            bad=bytearray(raw);struct.pack_into('<'+fmt,bad,offset,value)
            with self.assertRaises(ValueError):r.expand_cpu_trace(rebound(bad),bad)
        # Rebind the hash deliberately: every original 64-bit accounting word
        # still reaches the unchanged lifecycle/CPU oracle, not just a checksum.
        selected={}
        for index in range(len(raw)//168):selected.setdefault(struct.unpack_from('<I',raw,index*168+4)[0],index)
        for kind,index in selected.items():
            for word in range(16 if kind==1 else 8):
                bad=bytearray(raw);bad[index*168+40+word*8+7]^=128
                with self.assertRaises(ValueError):r.validate(serial,r.expand_cpu_trace(rebound(bad),bad),0,oom,count,sha)

    def test_reuse_exact_build_inputs_and_receipts(self):
        import verify_x86_64_service_cpu as v
        admission=v.read(v.COMPACT/'admission.json');old=v.read(ROOT/admission['build_frozen']['path'])
        current=copy.deepcopy(old);current['source_inputs']=dict(admission['source_inputs']);current['candidate']='host-reuse-negative'
        for index in (16,17,18,19):
            original=admission['build_receipts'][index-16];r=v.read(ROOT/original['path'])
            receipt=dict(r,candidate=current['candidate'],execution='reuse',reuse=dict(frozen=admission['build_frozen'],receipt=original))
            v.gate_binding(current,index,receipt)
            for key,value in (('candidate','wrong'),('command','wrong'),('passed',False),('exit_code',1),('elapsed',181),
                              ('execution','build'),('reuse',{}),('artifacts',{}),('log',dict(r['log'],sha256='0'*64))):
                bad=copy.deepcopy(receipt);bad[key]=value
                with self.assertRaises((ValueError,KeyError)):v.gate_binding(current,index,bad)
            for key in r['artifacts']:
                bad=copy.deepcopy(receipt);bad['artifacts'][key]='0'*64
                with self.assertRaises(ValueError):v.gate_binding(current,index,bad)
        # Mutate every input, including headers, includes, build producers and
        # old tests; ONLY the five explicit observer/documentation files may vary.
        for name in current['source_inputs']:
            bad=copy.deepcopy(current);bad['source_inputs'][name]='0'*64
            if name in v.COMPACT_FILES:v.reuse_inputs(bad,old,admission,16)
            else:
                with self.assertRaises(ValueError):v.reuse_inputs(bad,old,admission,16)
        for name in current['tools_sha256']:
            bad=copy.deepcopy(current);bad['tools_sha256'][name]='0'*64
            with self.assertRaises(ValueError):v.reuse_inputs(bad,old,admission,16)
        for index in range(24):
            bad=copy.deepcopy(current);bad['commands'][index]+=' --wrong'
            with self.assertRaises(ValueError):v.reuse_inputs(bad,old,admission,16)
        for index in (True,1,15,20,21,24):
            with self.assertRaises(ValueError):v.reuse_inputs(current,old,admission,index)
        for action in ('missing','extra'):
            bad=copy.deepcopy(current)
            if action=='missing':bad['source_inputs'].pop(next(iter(bad['source_inputs'])))
            else:bad['source_inputs']['unbound-input']='0'*64
            with self.assertRaises(ValueError):v.reuse_inputs(bad,old,admission,16)

    def test_compact_matrix_budget_includes_failures(self):
        import verify_x86_64_service_cpu as v
        from unittest.mock import patch
        admission=v.read(v.COMPACT/'admission.json')
        oldpaths=[ROOT/p['path'] for p in admission['old_matrices']]
        budget=v.compact_matrix_budget # Preserve the historical admission regression.
        data={p:v.read(p) for p in oldpaths};data[v.COMPACT/'admission.json']=admission
        normal=list(oldpaths);fatal=[]
        def glob(path,pattern):
            self.assertEqual(pattern,'attempt-*/summary.json')
            return iter(normal if path==v.BASE/'guests' else fatal)
        with patch.object(Path,'glob',glob),patch.object(v,'read',side_effect=lambda path:copy.deepcopy(data[path])):
            self.assertEqual(budget('new',False,starting=True),(2,41.888588))
            def add(kind,candidate,elapsed=200,cases=12):
                paths=fatal if kind else normal
                path=v.BASE/('fatal-guests' if kind else 'guests')/('host-budget-'+str(len(paths)))
                paths.append(path);data[path]=dict(closed=True,fatal=kind,passed=False,candidate=candidate,guest_elapsed=elapsed,cases=[{}]*cases)
                return path
            p=add(False,'same')
            self.assertEqual(budget('new',False,starting=True),(14,241.888588))
            with self.assertRaises(ValueError):budget('same',False,starting=True)
            for key,value in (('closed',False),('fatal',True),('guest_elapsed',-1),('guest_elapsed',841)):
                saved=data[p][key];data[p][key]=value
                with self.assertRaises(ValueError):budget('new',False,starting=True)
                data[p][key]=saved
            add(False,'second')
            with self.assertRaises(ValueError):budget('third',False,starting=True)
            q=add(True,'fatal',40,2)
            self.assertEqual(budget('next',True,starting=True)[0],28)
            data[q]['cases']=[{}]*20
            with self.assertRaises(ValueError):budget('next',True,starting=True)
            data[q]['cases']=[{}]*2;data[q]['guest_elapsed']=800
            with self.assertRaises(ValueError):budget('next',True,starting=True)

    def test_cost_reuse_and_immutable_oracles(self):
        import verify_x86_64_service_cpu as v
        a=v.read(v.COST/'admission.json');paths=sorted(v.COST.glob('candidate-*/frozen-candidate.json'))
        f=v.read(paths[-1])
        for index in (16,17,18,19):
            v.cost_reuse_inputs(f,a,index)
        for index in (True,1,15,20,24):
            with self.assertRaises(ValueError):v.cost_reuse_inputs(f,a,index)
        for name in f['source_inputs']:
            if name in v.COMPACT_FILES:continue
            bad=copy.deepcopy(f);bad['source_inputs'][name]='0'*64
            with self.assertRaises(ValueError):v.cost_reuse_inputs(bad,a,19)
        for name in f['tools_sha256']:
            bad=copy.deepcopy(f);bad['tools_sha256'][name]='0'*64
            with self.assertRaises(ValueError):v.cost_reuse_inputs(bad,a,19)
        for index in range(24):
            bad=copy.deepcopy(f);bad['commands'][index]+=' --unbound'
            with self.assertRaises(ValueError):v.cost_reuse_inputs(bad,a,19)
        before=(v.BASE/'workload-stop-source/scripts__run_qemu_x86_64_service_cpu.py').read_text()
        path=ROOT/f['directory']/'source/scripts__run_qemu_x86_64_service_cpu.py'
        self.assertEqual(v.digest(path),f['snapshots'][path.relative_to(ROOT).as_posix()])
        after=path.read_text()
        v.cost_observer_binding(before,after)
        for old,new in [('total<40','total<39'),('charges<=2048','charges<=2049'),
                        ('len(raw)%168','len(raw)%160'),("('window-slot7','generation-slot7')","('window-slot7',)")]:
            self.assertIn(old,after)
            with self.assertRaises(ValueError):v.cost_observer_binding(before,after.replace(old,new))

    def test_cost_budget_counts_diagnostic_and_all_failures(self):
        import verify_x86_64_service_cpu as v
        from unittest.mock import patch
        a=v.read(v.COST/'admission.json');diag=v.read(v.COST/'diagnosis.json')
        normal=[ROOT/p['path'] for p in a['old_matrices']];fatal=[]
        data={p:v.read(p) for p in normal};data[v.COST/'admission.json']=a;data[v.COST/'diagnosis.json']=diag
        def glob(path,pattern):return iter(normal if path==v.BASE/'guests' else fatal)
        with patch.object(Path,'glob',glob),patch.object(v,'read',side_effect=lambda p:copy.deepcopy(data[p])):
            count,spent=v.matrix_budget('new',False,True)
            self.assertEqual(count,9);self.assertAlmostEqual(spent,159.7972+diag['guest_elapsed'])
            def add(candidate,kind=False,elapsed=200):
                path=v.BASE/('fatal-guests' if kind else 'guests')/('host-'+candidate)
                (fatal if kind else normal).append(path)
                data[path]=dict(candidate=candidate,closed=True,fatal=kind,passed=False,guest_elapsed=elapsed,cases=[{}]*(2 if kind else 12))
                return path
            p=add('same')
            with self.assertRaises(ValueError):v.matrix_budget('same',False,True)
            self.assertEqual(v.matrix_budget('new',False,True)[0],21)
            for key,value in [('closed',False),('fatal',True),('guest_elapsed',-1),('guest_elapsed',841)]:
                saved=data[p][key];data[p][key]=value
                with self.assertRaises(ValueError):v.matrix_budget('new',False,True)
                data[p][key]=saved
            add('second')
            with self.assertRaises(ValueError):v.matrix_budget('third',False,True)
            q=add('fatal',True,40);self.assertEqual(v.matrix_budget('next',True,True)[0],35)
            data[q]['guest_elapsed']=800
            with self.assertRaises(ValueError):v.matrix_budget('next',True,True)

    def test_compact_binary_aggregate_and_short_write(self):
        import run_qemu_x86_64_service_cpu as r
        from unittest.mock import patch,Mock
        stream=Mock();stream.write.return_value=167;lines=[]
        with patch.object(Path,'open',return_value=stream):
            writer=r.CPULedger(Path('host-short-write'),lines.append)
            with self.assertRaises(ValueError):writer.event(kind='cpu_start',slot=0,gen=1,now=0,records=[0]*8)
            self.assertFalse(lines);self.assertEqual(writer.count,0)
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-capacity-'+uuid.uuid4().hex)
        (folder/'binary-memory').mkdir(parents=True)
        with (folder/r.CPU_FILE).open('xb') as out:out.write(bytes(168))
        with patch.object(Path,'read_text',return_value=json.dumps(dict(bytes=128*1024*1024-168))):
            self.assertEqual(len(r.binary_capacity(folder)),1)
        for contents in ('',json.dumps(dict(bytes=128*1024*1024-167)),(json.dumps(dict(bytes=1))+'\n')*2048):
            with patch.object(Path,'read_text',return_value=contents):
                with self.assertRaises(ValueError):r.binary_capacity(folder)
    def build(self,asm,branch):
        c='#define SERVICE_'+branch+'_TEST 1\n#include "'+(ROOT/'test/x86_64_service_cpu_host.c').as_posix()+'"\n'
        host.TaskFrameTests().build(asm,c,'SERVICE_CPU_'+branch)

    def test_actual_period_core(self):
        self.build('%define REIST_NATIVE_SERVICE_CPU 1\n%include "arch/x86_64/proc/cpu_budget.asm"\n','PERIOD')

    def test_actual_family_admission(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        asm='%define REIST_NATIVE_TASK_POOL 1\n%define REIST_NATIVE_WIDE 1\n%define REIST_NATIVE_SERVICE_CPU 1\nBITS 64\nsection .text\n'
        self.build(asm+source.split('; Pinned profile-v1',1)[0],'FAMILY')

    def test_actual_service_family_retirement(self):
        from unittest.mock import patch
        from test_x86_64_task_pool import TaskPoolTests
        import run_qemu_x86_64_file_launch as adapters
        captured=[]
        with patch.object(host.TaskFrameTests,'build',side_effect=lambda *args:captured.append(args)):
            TaskPoolTests().test_actual_family_pool()
        self.assertEqual(len(captured),1)
        asm=adapters.once(captured[0][0],'process_run_plan: resb 272','process_run_plan: resb 336')
        asm='%define REIST_NATIVE_SERVICE_CPU 1\n'+asm
        fixture=(ROOT/'test/x86_64_task_pool_host.c').read_text()
        fixture=adapters.once(fixture,'process_run_plan[0]=4','process_run_plan[0]=5')
        fixture=fixture.replace('#include "../include/reist/abi/syscall.h"','#include "'+(ROOT/'include/reist/abi/syscall.h').as_posix()+'"')
        fixture=fixture.replace('TASK_POOL_FAMILY_OK','SERVICE_CPU_RETIRE_OK')
        host.TaskFrameTests().build(asm,'#define TASK_POOL_FAMILY_TEST 1\n'+fixture,'SERVICE_CPU_RETIRE')

    def test_actual_scheduler_binding(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body='scheduler_budget_apply64:'+source.split('scheduler_budget_apply64:',1)[1].split('; Wait completion validates',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_SERVICE_CPU 1
%include "arch/x86_64/mm/native_layout.inc"
SCHEDULER_MODE_PROCESS equ 8
section .bss
align 16
global scheduler_cpu_budgets,scheduler_cpu_windows,process_run_plan,scheduler_mode,scheduler_last_tick
scheduler_cpu_budgets:resb 256
scheduler_cpu_windows:resb 256
process_run_plan:resb 336
scheduler_last_tick:resq 1
scheduler_mode:resb 1
section .text
global service_scheduler_apply
service_scheduler_apply:
    mov eax,edi
    mov edi,esi
    mov rsi,rdx
    mov rdx,rcx
    mov r8,0x123456789abcdef0
    mov r9,r8
    mov r10,r8
    mov r11,r8
    push rcx
    push rdx
    push rsi
    push rdi
    call scheduler_budget_apply64
    cmp rdi,[rsp]
    jne .bad
    cmp rsi,[rsp+8]
    jne .bad
    cmp rdx,[rsp+16]
    jne .bad
    cmp rcx,[rsp+24]
    jne .bad
    cmp r8,r9
    jne .bad
    cmp r8,r10
    jne .bad
    cmp r8,r11
    jne .bad
    mov rcx,0x123456789abcdef0
    cmp r8,rcx
    je .done
.bad:
    mov rax,-1
.done:
    add rsp,32
    ret
'''+body+'\n%include "arch/x86_64/proc/cpu_budget.asm"\n'
        self.build(asm,'SCHEDULER')

    def test_actual_full_snapshot_before_effects(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        admission=source.split('; Pinned profile-v1',1)[0]
        snapshot='family_syscall64:'+source.split('family_syscall64:',1)[1].split('    cmp dword [rel family_request],4',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_SERVICE_CPU 1
%define REIST_NATIVE_WIDE 1
PF_R equ 4
section .bss
align 16
global family_request,syscall_rdi
family_request:resb 96
syscall_rdi:resq 1
syscall_rsi:resq 1
syscall_rdx:resq 1
syscall_r10:resq 1
syscall_r8:resq 1
syscall_r9:resq 1
section .text
extern service_range
global family_syscall64
'''+admission+snapshot+'''
    ret
.pointer:
    mov rax,-14
    ret
family_result64:
    ret
process_run_syscall64.invalid:
    mov rax,-22
    ret
scheduler_validate_shell_range64:
    push rbp
    mov rbp,rsp
    and rsp,-16
    mov rdi,rax
    mov rsi,rdx
    mov rdx,rcx
    call service_range
    leave
    ret
'''
        self.build(asm,'SNAPSHOT')

    @staticmethod
    def sample(case):
        import run_qemu_x86_64_service_cpu as r
        from test_x86_64_task_pool import TaskPoolTests
        serial,rows,oom,count,sha=TaskPoolTests.sample(3 if case==10 else 0 if case==11 else case)
        entries={e['gen']:e for e in rows if e['kind']=='start'}
        receipts={struct.unpack('<4I2Q',bytes.fromhex(m[1]))[1]:m[1] for m in r.wide.process.REAP.finditer(serial)}
        events=[];records={};clock={0:0,1:0};per=9 if case==6 else 8
        for event in rows:
            event=copy.deepcopy(event);kind=event['kind'];gen=event.get('gen');entry=entries.get(gen)
            if kind=='mode':event['value']=case
            if kind=='start':
                events.append(event);legacy=case==10 and entry['role']==0 and entry['index']==0
                records[gen]=[gen,32,0,0,0 if legacy else 100,0,0,0]
                events.append(dict(kind='cpu_start',slot=entry['slot'],gen=gen,now=0,records=records[gen][:]));continue
            if kind=='release':
                data=list(struct.unpack('<4I2Q',bytes.fromhex(receipts[gen])))
                n=32 if data[2]==256 else 40 if data[3]==4 else 0;run=(gen-1)//per
                if case==3 and data[2]==256:clock[run]=(clock[run]//100+1)*100-1
                for index in range(n):
                    clock[run]+=1 if case==3 and data[2]==256 else 5
                    if case==11 and entry['role']==0 and entry['index']==0 and index==20:clock[run]+=200
                    before=records[gen][:];after,result=r.charge_result(before,clock[run]);records[gen]=after
                    events.append(dict(kind='cpu_charge',slot=entry['slot'],gen=gen,now=clock[run],before=before,after=after[:],result=result))
                events.append(dict(kind='cpu_final',slot=entry['slot'],gen=gen,now=clock[run],records=records[gen][:]))
                data[4]=n;serial=serial.replace(receipts[gen],struct.pack('<4I2Q',*data).hex().upper(),1)
            events.append(event)
        return serial,events,oom,count,sha

    def test_actual_guest_oracle(self):
        import run_qemu_x86_64_service_cpu as r
        def trace(rows):return '\n'.join('TASK_POOL '+json.dumps(e) for e in rows)+'\n'
        for case in range(12):
            serial,events,oom,count,sha=self.sample(case)
            self.assertEqual(len(r.validate(serial,trace(events),case,oom,count,sha)),18 if case==6 else 16)
            # All inherited event classes plus every CPU event class remain
            # mandatory; exercise omission, duplication and each record field.
            selected={}
            for i,e in enumerate(events):selected.setdefault(e['kind'],i)
            for kind,i in selected.items():
                with self.subTest(case=case,kind=kind):
                    with self.assertRaises(ValueError):r.validate(serial,trace(events[:i]+events[i+1:]),case,oom,count,sha)
                    with self.assertRaises(ValueError):r.validate(serial,trace(events[:i]+[events[i]]+events[i:]),case,oom,count,sha)
            for kind in r.CPU_KINDS:
                index=selected[kind]
                for name in (('before','after') if kind=='cpu_charge' else ('records',)):
                    for field in range(8):
                        bad=copy.deepcopy(events);bad[index][name][field]^=1<<63
                        with self.subTest(case=case,kind=kind,field=field):
                            with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,count,sha)
            for kind,key,value in (('witness','immutable',0),('release','fenced',0),('finish','zero',0),
                ('copy','sha','0'*64),('cpu_charge','result',2),('cpu_charge','now',1<<60),('cpu_final','gen',999)):
                bad=copy.deepcopy(events);bad[selected[kind]][key]=value
                with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,count,sha)
            first=r.wide.process.REAP.search(serial);raw=bytearray.fromhex(first[1]);raw[16]^=1
            with self.assertRaises(ValueError):r.validate(serial.replace(first[1],raw.hex().upper(),1),trace(events),case,oom,count,sha)

    def test_generation_scoped_witness_hooks(self):
        import run_qemu_x86_64_service_cpu as runtime
        predicate=runtime.witness_hooks_needed
        self.assertFalse(predicate({},set()))
        for gen in range(1,19):
            for slot in range(8):
                for live in (False,True):
                    starts={gen:dict(live=live,slot=slot)}
                    self.assertEqual(predicate(starts,set()),live and slot>=2)
                    self.assertFalse(predicate(starts,{gen}))
        starts={1:dict(live=True,slot=0),2:dict(live=True,slot=2)}
        self.assertFalse(predicate(starts,{2}))
        starts[2]['live']=False;starts[3]=dict(live=True,slot=2)
        self.assertTrue(predicate(starts,{2})) # reused slot never inherits proof
        self.assertFalse(predicate(starts,{2,3}))
        old=runtime.pool.SYSCALL.strip()
        tree=ast.parse(runtime.observer_body())
        actual=next(ast.get_source_segment(runtime.observer_body(),n) for n in tree.body
                    if isinstance(n,ast.FunctionDef) and n.name=='syscall')
        self.assertTrue(actual.startswith(old)) # all original proof code exact
        class Hook:
            enabled=True
        hooks=(Hook(),Hook());calls=[]
        env=dict(mode=lambda:8,starts=starts,proofs={2,3},witness_hooks=hooks,
                 witness_hooks_needed=predicate)
        exec(actual,env);env['syscall']()
        self.assertTrue(all(not h.enabled for h in hooks))
        # A newly published, not-ready generation retains both hooks.
        starts[4]=dict(live=True,slot=3,role=0,parent=1)
        env.update(task=lambda slot:(1,1),user=lambda *a:struct.pack('<9Q',0,0,0,1,0,0,0,0,0),
                   CONFIG={'root_data':[0,0]},struct=struct)
        for h in hooks:h.enabled=True
        env['syscall']();self.assertTrue(all(h.enabled for h in hooks))
        # Execute the actual successful CREATE tail to prove rearming, not text alone.
        body=runtime.observer_body()
        create=next(ast.get_source_segment(body,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_end')
        for h in hooks:h.enabled=False
        env.update(allocator=Hook(),created=True,reg=lambda name:(4<<32)|3,OOM=None,
                   copies={4:b'bound'},created_sources={},source_pointer=123,emit=lambda *a,**k:calls.append((a,k)),
                   allocation_owner=1<<32,allocation_count=24,start_hook=Hook())
        exec(create,env);env['create_end']()
        self.assertTrue(all(h.enabled for h in hooks));self.assertEqual(env['created_sources'],{4:123})
        self.assertFalse(env['created']);self.assertEqual(calls[0][0],('create',))
        # A peer syscall may run after CREATE, before the child enters starts.
        # Replay the frozen review failure through the real first-entry tail.
        env['starts']={1:dict(slot=0,live=True),2:dict(slot=2,live=False)}
        env['proofs']={2};env['syscall']()
        self.assertTrue(all(not h.enabled for h in hooks))
        env['starts'][3]=dict(slot=2,live=True)
        first=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='start')
        index=next(i for i,n in enumerate(first.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                   and isinstance(n.value.func,ast.Name) and n.value.func.id=='cpu_start')
        env.update(slot=2,gen=3,cpu_start=lambda *a:None)
        exec(compile(ast.Module(body=first.body[index:],type_ignores=[]),'<actual first-entry tail>','exec'),env)
        self.assertTrue(predicate(env['starts'],env['proofs']))
        self.assertTrue(all(h.enabled for h in hooks))

    def test_observer_scope_and_compilation(self):
        import run_qemu_x86_64_service_cpu as r
        code=r.observer_body();ast.parse(code)
        self.assertNotIn("Hook('process_run_syscall64'",code)
        self.assertIn('callbacks<=8192',code)
        self.assertIn("('process_run_plan',336),('scheduler_cpu_windows',256)",code)
        self.assertIn('start_hook.enabled=any',code)
        self.assertEqual(code.count('.write_memory('),1)
        self.assertEqual(code.count("gdb.execute('set $"),3)
        ast.parse(r.FATAL_BODY)
        self.assertEqual(r.FATAL_BODY.count('.write_memory('),1)
        self.assertIn("Probe('family_create64.parent_result','arm')",r.FATAL_BODY)
        self.assertIn("reg('rdx')==0",r.FATAL_BODY)

    def test_actual_cpu_snapshot_batch(self):
        import run_qemu_x86_64_service_cpu as r
        node=next(n for n in ast.parse(r.CPU_OBSERVER).body if isinstance(n,ast.FunctionDef) and n.name=='cpu_snapshot')
        symbols=dict(scheduler_cpu_budgets=4096,scheduler_cpu_windows=4352,scheduler_mode=4620,scheduler_last_tick=4800)
        raw=bytearray(712);reads=[]
        for slot in range(8):
            struct.pack_into('<4Q',raw,slot*32,slot+1,32,slot*40,slot*100)
            struct.pack_into('<4Q',raw,256+slot*32,100,slot,3,slot+1)
        raw[524]=8;struct.pack_into('<Q',raw,704,1000)
        def mem(address,size):
            reads.append((address,size));self.assertEqual((address,size),(4096,712));return bytes(raw)
        env=dict(S=symbols,mem=mem,struct=struct,CPU_LAYOUT=r.cpu_snapshot_layout(symbols))
        exec(compile(ast.get_source_segment(r.CPU_OBSERVER,node),'<actual CPU snapshot>','exec'),env)
        for slot in range(8):
            self.assertEqual(env['cpu_snapshot'](slot),(8,1000,[slot+1,32,slot*40,slot*100,100,slot,3,slot+1]))
        self.assertEqual(len(reads),8)
        for slot in (True,-1,8):
            with self.assertRaises(AssertionError):env['cpu_snapshot'](slot)
        for name,value in (('scheduler_cpu_windows',4096),('scheduler_last_tick',9000)):
            before=symbols[name];symbols[name]=value
            with self.assertRaises(AssertionError):r.cpu_snapshot_layout(symbols)
            symbols[name]=before

    def test_actual_workload_clock_separation(self):
        source=(ROOT/'arch/x86_64/user/task_pool.c').read_text()
        body=source.split('static uint64_t service_quantum(void)',1)[1].split('#if PROGRAM_ID<2\nstatic int service_idle',1)[0]
        old=(ROOT/'build/codex-agent/r83ap-service-cpu/idle-renewal/before/arch__x86_64__user__task_pool.c').read_text()
        old_body=old.split('static uint64_t service_quantum(void)',1)[1].split('#if PROGRAM_ID<2\nstatic int service_idle',1)[0]
        old_body=old_body.replace('service_quantum()', 'old_quantum()').replace('service_samples(', 'old_samples(')
        c='''#include <stdint.h>
#include <stdio.h>
static uint64_t cycles;
static unsigned mono,sleeps,idles,calibrations,bad,stuck,waits;
static int64_t reply=-110;
enum { MONOTONIC_MS=42,SLEEP_MS=41,IPC_RECEIVE_TIMEOUT=54 };
static void message_init(volatile uint32_t *m,unsigned n){for(unsigned i=0;i<35;i++)m[i]=0;m[0]=1;m[1]=140;m[2]=n;}
static int64_t S3(unsigned op,unsigned endpoint,volatile uint32_t *m,unsigned ms) {
    if(op!=IPC_RECEIVE_TIMEOUT || endpoint!=0x1234 || ms!=2000 || sleeps!=20 || waits)bad=1;
    if(m[0]!=1 || m[1]!=140)bad=1;
    for(unsigned i=2;i<35;i++)if(m[i])bad=1;
    waits++;cycles+=(uint64_t)ms*1000;return reply;
}
static uint64_t service_cycles(void) {cycles+=1000;return cycles;}
static uint64_t S0(unsigned op) {if(op!=MONOTONIC_MS || sleeps)bad=1;mono++;cycles+=10000;return stuck?0:cycles/10000*10;}
static int S1(unsigned op,unsigned ms) {
    if(op!=SLEEP_MS || (ms!=40 && ms!=80 && ms!=100))bad=1;
    if(ms==40)sleeps++;else if(ms==80){if(sleeps)bad=1;calibrations++;}
    else {if(sleeps!=20)bad=1;idles++;}
    cycles+=(uint64_t)ms*1000;return 0;
}
static uint64_t service_quantum(void)'''+body+'static uint64_t old_quantum(void)'+old_body+'''
#define CHECK(x) do {if(!(x)){fprintf(stderr,"IDLE_CHECK %u %s\\n",__LINE__,#x);return 1;}}while(0)
static void reset(void){sleeps=idles=calibrations=bad=mono=waits=stuck=0;cycles=0;reply=-110;}
int main(void) {
    (void)S3;(void)message_init;
    CHECK(!service_samples(40,0x1234) && !bad && sleeps==40 && !idles && waits==1 && calibrations==3 && mono==6);
    reset();CHECK(!old_samples(40,1) && !bad && sleeps==40 && idles==20 && !waits && calibrations==3 && mono==6);
    reset();CHECK(!service_samples(40,0) && !bad && sleeps==40 && !idles && !waits);
    const int errors[]={0,-9,-13,-32,-4};
    for(unsigned i=0;i<sizeof errors/sizeof errors[0];i++) {
        reset();reply=errors[i];CHECK(service_samples(40,0x1234)==-1 && !bad && sleeps==20 && !idles && waits==1);
    }
    reset();stuck=1;
    CHECK(service_samples(40,0)==-1 && !sleeps && !idles && !waits && !bad && calibrations==1 && mono==2);
    puts("SERVICE_CPU_WORKLOAD_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'SERVICE_CPU_WORKLOAD')

    def test_actual_idle_ipc_deadline_and_reap_o0_o2(self):
        prefix=(ROOT/'test/x86_64_native_ipc_host.c').read_text().split('static void bulk_request',1)[0]
        c=prefix+r'''
int main(void) {
    call(NATIVE_IPC_BIND,0,0);call(NATIVE_IPC_BIND,1,0);
    request(0,0,49,0,0,0);assert(!r.result);unsigned endpoint=r.handle;
    request(0,0,55,endpoint,2,2);assert(!r.result);
    /* Consume exactly the parent's existing release before the idle wait. */
    request(0,0,53,endpoint,7,0);assert(!r.result);
    request(1,0,54,endpoint,0,0);assert(!r.result && r.message.payload[0]==7);
    memset(&r,0,sizeof r);r.number=54;r.a0=endpoint;r.a2=2000;
    r.message.version=1;r.message.struct_size=140;
    call(NATIVE_IPC_REQUEST,1,0);
    assert(r.result==NATIVE_IPC_PENDING && r.deadline==200 && !r.ready);
    for(unsigned now=0;now<200;now++) {
        call(NATIVE_IPC_PUMP,0,now);assert(!r.ready);
        assert(pending[1].state==1 && pending[1].request.deadline==200);
        assert(clients[0].is_running && clients[1].is_running);
    }
    call(NATIVE_IPC_PUMP,0,200);assert(r.ready==2);
    call(NATIVE_IPC_TAKE,1,200);assert(r.result==-110 && r.copy_size==140);
    assert(!pending[1].state);
    request(0,200,52,endpoint,0,0);assert(!r.result);
    call(NATIVE_IPC_REAP,1,200);call(NATIVE_IPC_REAP,0,200);call(NATIVE_IPC_END,0,200);
    ipc_resource_stats_t stats;assert(!ipc_resource_stats(&stats));
    assert(!stats.active_endpoints && !stats.active_capabilities && !stats.queued_messages);
    gen[0]=3;gen[1]=4;call(NATIVE_IPC_BIND,0,201);call(NATIVE_IPC_BIND,1,201);
    request(1,201,54,endpoint,0,2000);assert(r.result==-9);
    call(NATIVE_IPC_REAP,1,201);call(NATIVE_IPC_REAP,0,201);call(NATIVE_IPC_END,0,201);
    puts("SERVICE_IDLE_IPC_OK");return 0;
}
'''
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-idle-ipc-'+uuid.uuid4().hex);folder.mkdir()
        unit=folder/'source.c';unit.write_text(c,encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/('idle-'+opt+'.exe')
            command=[host.find_zig(),'cc','-std=c11','-Wall','-Wextra','-Werror','-O'+opt,'-DREIST_NATIVE_IPC',
                     '-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_HOST_TEST','-DREIST_NATIVE_TASK_POOL=1','-DREIST_NATIVE_RUNTIME=1',
                     '-I.','kernel/ipc/ipc.c','kernel/init/critical_object.c',unit,'-o',exe]
            for name,argv in [('compile',command),('run',[exe])]:
                result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(name+opt+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
                if name=='run':self.assertIn('SERVICE_IDLE_IPC_OK',result.stdout)

    def test_actual_enclosing_calibration_with_delayed_resumes(self):
        import verify_x86_64_service_cpu as v
        admission=v.read(v.WORKLOAD/'admission.json')
        before=(ROOT/admission['fixture']['path']).read_text()
        after=(ROOT/v.FIXTURE).read_text()
        def function(source):
            return 'static uint64_t service_quantum(void)'+source.split('static uint64_t service_quantum(void)',1)[1].split('static int service_samples',1)[0]
        old=function(before).replace('service_quantum(void)','old_quantum(void)')
        c='''#include <stdint.h>
#include <stdio.h>
static uint64_t cycles,first_delay,last_delay;
static unsigned calls,mode;
enum { MONOTONIC_MS=42,SLEEP_MS=41 };
static uint64_t service_cycles(void) {return cycles;}
static uint64_t S0(unsigned op) {
    if(op!=MONOTONIC_MS)return UINT64_MAX;
    uint64_t value=cycles/10000*10;
    if(mode==1)value=0;
    if(mode==2)value=UINT64_MAX;
    cycles+=(calls++&1)?last_delay:first_delay;
    return value;
}
static int S1(unsigned op,unsigned ms) {
    if(op!=SLEEP_MS || ms!=80 || mode==3)return -1;
    if(mode==4)cycles=0;
    else cycles+=mode==5?3000000001ULL:mode==6?1100000:80000;
    return 0;
}
'''+old+function(after)+'''
#define CHECK(x) do {if(!(x)){fprintf(stderr,"CALIBRATION_CHECK %u %s\\n",__LINE__,#x);return 1;}}while(0)
int main(void) {
    first_delay=40000;cycles=calls=0;
    CHECK(old_quantum()==8333); /* fewer than one10ms tick */
    cycles=calls=0;CHECK(service_quantum()==12000);
    for(unsigned first=0;first<=65000;first+=5000)
    for(unsigned last=0;last<=65000;last+=5000)
    for(unsigned phase=0;phase<10000;phase+=137) {
        first_delay=first;last_delay=last;cycles=phase;calls=0;
        CHECK(service_quantum()>=11000 && calls==6);
    }
    first_delay=last_delay=0;
    for(mode=1;mode<=6;mode++) {
        cycles=100000;calls=0;CHECK(!service_quantum());
    }
    mode=0;cycles=calls=0;last_delay=2000000000ULL;
    CHECK(!service_quantum()); /* excessive quantum rejected */
    puts("SERVICE_CPU_CALIBRATION_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'SERVICE_CPU_CALIBRATION')

    def test_default_fixture_preprocessing_is_byte_exact(self):
        import verify_x86_64_service_cpu as v
        admission=v.read(v.WORKLOAD/'admission.json')
        before=(ROOT/admission['fixture']['path']).read_bytes();after=(ROOT/v.FIXTURE).read_bytes()
        calibrated=(v.BASE/'transport-stop-source/arch__x86_64__user__task_pool.c').read_bytes()
        overlapped=(v.BASE/'retention-stop-source/arch__x86_64__user__task_pool.c').read_bytes()
        retained=(v.BASE/'retention-renewal-stop-source/arch__x86_64__user__task_pool.c').read_bytes()
        parallel=(v.BASE/'case6-dispatch-stop-source/arch__x86_64__user__task_pool.c').read_bytes()
        dual=(v.BASE/'dual-stop-source/arch__x86_64__user__task_pool.c').read_bytes()
        peer=(v.BASE/'static-stop-source/arch__x86_64__user__task_pool.c').read_bytes()
        critical=(v.BASE/'idle-renewal/before/arch__x86_64__user__task_pool.c').read_bytes()
        v.fixture_change_binding(before,calibrated);v.overlap_fixture_binding(calibrated,overlapped)
        v.retention_fixture_binding(overlapped,retained);v.parallel_fixture_binding(retained,parallel)
        v.dual_fixture_binding(parallel,dual);v.peer_fixture_binding(dual,peer);v.critical_fixture_binding(peer,critical)
        v.idle_fixture_binding(critical,after)
        for bad in (calibrated+b'\n',calibrated.replace(b'if(quantum<best)',b'if(quantum>best)'),
                    calibrated.replace(b'S1(SLEEP_MS,40)',b'S1(SLEEP_MS,30)'),
                    calibrated.replace(b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1'),
                    calibrated.replace(b'return 90+PROGRAM_ID;',b'return 91+PROGRAM_ID;',1)):
            with self.assertRaises(ValueError):v.fixture_change_binding(before,bad)
        for left,right in ((b'hold_ms!=2500',b'hold_ms!=2400'),(b'hold_ms!=3000',b'hold_ms!=2900'),
                           (b'n<31',b'n<32'),(b'now<last',b'now<first'),(b'service_samples(40,0)',b'service_samples(39,0)'),
                           (b'if(mode!=6)',b'if(mode==6)'),(b'S1(SLEEP_MS,40)',b'S1(SLEEP_MS,30)'),
                           (b'root_witness.phase=4',b'root_witness.phase=5'),(b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1')):
            self.assertIn(left,overlapped)
            with self.assertRaises(ValueError):v.overlap_fixture_binding(calibrated,overlapped.replace(left,right))
        for left,right in ((b'n<8',b'n<9'),(b'step<56',b'step<55'),(b'if(result==-32)',b'if(result==0)'),
                           (b'if(result!=-110)',b'if(result!=-11)'),(b'S1(SLEEP_MS,1)',b'S1(SLEEP_MS,0)'),
                           (b'!service_retained(ports[0])',b'1'),(b'root_witness.phase=4',b'root_witness.phase=5')):
            self.assertIn(left,retained)
            with self.assertRaises(ValueError):v.retention_fixture_binding(overlapped,retained.replace(left,right))
        for left,right in ((b'n<8',b'n<9'),(b'step<56',b'step<55'),(b'S0(YIELD)',b'S0(GETPID)'),
                           (b'if(result==-32)',b'if(result==0)'),(b'!service_retained(ports[0])',b'1'),
                           (b'(mode==6 && i)',b'(mode==6 && !i)'),(b'release(ports[i],i)==0,210',b'release(ports[0],0)==0,210'),
                           (b'service_overlap(2500)',b'service_overlap(2400)'),(b'S1(SLEEP_MS,40)',b'S1(SLEEP_MS,30)'),
                           (b'root_witness.phase=4',b'root_witness.phase=5'),(b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1')):
            self.assertIn(left,parallel)
            with self.assertRaises(ValueError):v.parallel_fixture_binding(retained,parallel.replace(left,right))
        for left,right in ((b'release(ports[i],i)==0,208',b'release(ports[0],0)==0,208'),
                           (b'service_overlap(3000)',b'service_overlap(2900)'),
                           (b'!(PROGRAM_ID==1 && mode==6)',b'!(PROGRAM_ID==1 && mode==5)'),
                           (b'step<56',b'step<55'),(b'service_samples(40,0)',b'service_samples(39,0)'),
                           (b'root_witness.phase=4',b'root_witness.phase=5'),
                           (b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1')):
            self.assertIn(left,dual)
            with self.assertRaises(ValueError):v.dual_fixture_binding(parallel,dual.replace(left,right))
        for left,right in ((b'owner!=11',b'owner!=10'),(b'owner-1,2)',b'owner-1,3)'),
                           (b'service_peer_finish(peer)',b'0'),(b'if(result==-32)',b'if(result==-110)'),
                           (b'service_idle(25)',b'service_idle(20)'),(b'mode!=6 || PROGRAM_ID==0',b'mode!=6'),
                           (b'n<8',b'n<9'),(b'step<56',b'step<55'),(b'service_samples(40,0)',b'service_samples(39,0)'),
                           (b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1')):
            self.assertIn(left,peer)
            with self.assertRaises(ValueError):v.peer_fixture_binding(dual,peer.replace(left,right))
        for left,right in ((b'service_overlap(2500)',b'service_idle(25)'),
                           (b'if(mode!=6)REQUIRE(!service_samples(40,0),242)',b'if(mode!=6 || PROGRAM_ID==0)REQUIRE(!service_samples(40,0),242)'),
                           (b'owner!=11',b'owner!=10'),(b'owner-1,2)',b'owner-1,3)'),
                           (b'service_peer_finish(peer)',b'0'),(b'if(result==-32)',b'if(result==-110)'),
                           (b'service_overlap(3000)',b'service_overlap(2900)'),(b'hold_ms!=2500',b'hold_ms!=2400'),
                           (b'n<8',b'n<9'),(b'step<56',b'step<55'),(b'service_samples(40,0)',b'service_samples(39,0)'),
                           (b'root_witness.phase=4',b'root_witness.phase=5'),(b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1')):
            self.assertIn(left,critical)
            with self.assertRaises(ValueError):v.critical_fixture_binding(peer,critical.replace(left,right))
        for left,right in ((b'message,2000)!=-110',b'message,1990)!=-110'),
                           (b'message,2000)!=-110',b'message,2000)!=0'),
                           (b'mode==5?port:0',b'mode==5?1:0'),(b'mode==5?port:0',b'mode!=5?port:0'),
                           (b'S1(SLEEP_MS,40)',b'S1(SLEEP_MS,30)'),(b'if(i==19 && idle_endpoint)',b'if(i==20 && idle_endpoint)'),
                           (b'service_samples(40,0)',b'service_samples(39,0)'),(b'#if REIST_NATIVE_SERVICE_CPU',b'#if 1')):
            self.assertIn(left,after)
            with self.assertRaises(ValueError):v.idle_fixture_binding(critical,after.replace(left,right))
        with self.assertRaises(ValueError):v.idle_fixture_binding(critical,after+b'\n')
        folder=v.BASE/('host-preprocess-'+uuid.uuid4().hex);folder.mkdir()
        build=v.read(ROOT/admission['build_receipts'][0]['path'])
        header=next(ROOT/name for name in build['artifacts'] if name.endswith('/import_blob.h'))
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for program in range(4):
            command=[str(host.find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-O2',
                     '-ffreestanding','-nostdlib','-Iuserspace/sdk/include','-DPROGRAM_ID='+str(program),
                     *(['-DNATIVE_IMPORT=1','-include',str(header)] if program<2 else ['-DNATIVE_IMPORT_CHILD=1'] if program==2 else []),
                     '-x','c','-E','-P','-']
            values=[]
            for side,source in [('old',before),('new',after)]:
                result=subprocess.run(command,input=source,cwd=ROOT,env=env,timeout=30,capture_output=True,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                with (folder/f'{program}-{side}.log').open('xb') as out:out.write(result.stderr)
                with (folder/f'{program}-{side}.i').open('xb') as out:out.write(result.stdout)
                self.assertEqual(result.returncode,0,result.stderr[-2000:]);values.append(result.stdout)
            self.assertTrue(values[0]);self.assertEqual(values[0],values[1])
        with (folder/'proof.json').open('x') as out:
            json.dump(dict(passed=True,before=v.link(ROOT/admission['fixture']['path']),after=v.link(ROOT/v.FIXTURE),
                           calibrated=v.link(v.BASE/'transport-stop-source/arch__x86_64__user__task_pool.c'),
                           overlapped=v.link(v.BASE/'retention-stop-source/arch__x86_64__user__task_pool.c'),
                           retained=v.link(v.BASE/'retention-renewal-stop-source/arch__x86_64__user__task_pool.c'),
                           parallel=v.link(v.BASE/'case6-dispatch-stop-source/arch__x86_64__user__task_pool.c'),
                           dual=v.link(v.BASE/'dual-stop-source/arch__x86_64__user__task_pool.c'),
                           peer=v.link(v.BASE/'static-stop-source/arch__x86_64__user__task_pool.c'),
                           critical=v.link(v.BASE/'idle-renewal/before/arch__x86_64__user__task_pool.c'),
                           outputs={p.relative_to(ROOT).as_posix():v.digest(p) for p in folder.glob('*.i')},program_ids=list(range(4))),out,indent=2)

    def test_workload_reference_reuse_has_no_broad_fixture_exception(self):
        import verify_x86_64_service_cpu as v
        admission=v.read(v.WORKLOAD/'admission.json');old=v.read(ROOT/admission['build_frozen']['path'])
        current=v.read(v.WORKLOAD/'candidate-01/frozen-candidate.json')
        for index in (16,17,18):
            v.workload_reuse_inputs(current,old,admission,index)
            ref=admission['build_receipts'][index-16];receipt=v.read(ROOT/ref['path'])
            receipt.update(candidate=current['candidate'],execution='reuse',reuse=dict(frozen=admission['build_frozen'],receipt=ref))
            v.gate_binding(current,index,receipt)
            bad=copy.deepcopy(receipt);bad['reuse']['receipt']['sha256']='0'*64
            with self.assertRaises(ValueError):v.gate_binding(current,index,bad)
        for index in (True,1,15,19,20,21):
            with self.assertRaises(ValueError):v.workload_reuse_inputs(current,old,admission,index)
        for name in current['source_inputs']:
            if name in v.COMPACT_FILES-{'scripts/run_qemu_x86_64_service_cpu.py'}:continue
            bad=copy.deepcopy(current);bad['source_inputs'][name]='0'*64
            with self.assertRaises(ValueError):v.workload_reuse_inputs(bad,old,admission,16)
        for name in current['tools_sha256']:
            bad=copy.deepcopy(current);bad['tools_sha256'][name]='0'*64
            with self.assertRaises(ValueError):v.workload_reuse_inputs(bad,old,admission,16)
        for key in ('targeted_tests','package_tests','runtime_tests'):
            for index in range(len(current['package'][key])):
                bad=copy.deepcopy(current);bad['package'][key][index]+=' --unbound'
                with self.assertRaises(ValueError):v.workload_reuse_inputs(bad,old,admission,16)

    def test_actual_normal_and_fatal_capture_transport_dispatch(self):
        import run_qemu_x86_64_service_cpu as runtime
        import verify_x86_64_service_cpu as verify
        from unittest.mock import patch
        actual=verify.BASE/'idle-renewal/native/x86_64/reist-x86_64-bootstrap.elf'
        config=runtime.pool.image_config(actual)
        folder=verify.BASE/('host-fatal-transport-'+uuid.uuid4().hex)
        marker='HOST_CAPTURE_BEFORE_SPAWN'
        for index,kind in enumerate((None,*runtime.FATAL_CASES)):
            root=folder/str(index);base=root/'build/codex-agent/r83ap-service-cpu'
            image=base/'workload-renewal/native/x86_64/reist-x86_64-bootstrap.elf'
            evidence=base/('fatal-guests' if kind else 'guests')
            argv=['capture-test','--image',str(image),'--evidence',str(evidence),*(['--fatal'] if kind else [])]
            # Actual main -> capture -> configuration -> pre-spawn boundary.
            # Popen is intercepted; neither a QEMU nor a GDB process starts.
            with patch.object(runtime,'ROOT',root),patch.object(runtime.pool,'image_config',return_value=config), \
                 patch.object(runtime.pool,'digest',return_value='host-fixture'), \
                 patch.object(runtime,'CASES',((0,4096),)),patch.object(runtime,'FATAL_CASES',(kind,) if kind else runtime.FATAL_CASES), \
                 patch.object(verify,'admit_runtime',return_value={'candidate':'host-only'}), \
                 patch.object(verify,'matrix_budget',return_value=(0,0)),patch.object(sys,'argv',argv), \
                 patch.object(runtime.transport.subprocess,'Popen',side_effect=ValueError(marker)) as spawn:
                self.assertEqual(runtime.main(),1)
                self.assertEqual(spawn.call_count,1,'selected observer must reach the mocked pre-spawn boundary')
            summaries=list(evidence.glob('attempt-*/summary.json'));self.assertEqual(len(summaries),1)
            summary=json.loads(summaries[0].read_text())
            self.assertFalse(summary['passed']);self.assertTrue(summary['closed']);self.assertEqual(summary['error'],marker)
            out=summaries[0].parent/('guest-'+str(kind or 0)+'-4096')
            metrics=json.loads((out/'capture-metrics.json').read_text())
            self.assertFalse(metrics['spawned']);self.assertTrue(metrics['failed']);self.assertEqual(metrics['error'],marker)
            self.assertEqual((out/'binary-memory').is_dir(),kind is None)
            self.assertFalse((out/'before.bin').exists())

    def test_fatal_exact_word_and_rejection(self):
        import run_qemu_x86_64_service_cpu as r
        saved=[bytearray(n) for _,n in r.FATAL_RANGES];gen=8
        struct.pack_into('<2Q',saved[0],7*1024,1,gen)
        struct.pack_into('<4Q',saved[1],7*32,gen,32,0,0)
        struct.pack_into('<4Q',saved[2],7*32,100,10,0,0)
        struct.pack_into('<4I',saved[3],0,5,336,8,0);struct.pack_into('<Q',saved[3],272+7*8,100)
        struct.pack_into('<Q',saved[4],7*64,(gen<<32)|7);struct.pack_into('<I',saved[8],7*4,gen)
        saved=list(map(bytes,saved))
        for kind in r.FATAL_CASES:
            changed,writes=r.fatal_mutation(kind,saved)
            self.assertEqual(len(writes),1);section,offset,raw=writes[0]
            self.assertEqual(len(raw),8)
            self.assertEqual((section,offset),(2,248) if kind=='window-slot7' else (1,224))
            for i,(a,b) in enumerate(zip(saved,changed)):
                self.assertEqual(b,a[:offset]+raw+a[offset+8:] if i==section else a)
            for index,offset,fmt,value in ((0,7*1024,'Q',0),(0,7*1024+8,'Q',0),
                (1,7*32,'Q',9),(1,7*32+8,'Q',33),(2,7*32,'Q',0),(2,7*32+24,'Q',1),
                (3,0,'I',4),(3,272+7*8,'Q',0),(4,7*64,'Q',0),(8,7*4,'I',9)):
                bad=list(map(bytearray,saved));struct.pack_into('<'+fmt,bad[index],offset,value)
                with self.assertRaises(ValueError):r.fatal_mutation(kind,list(map(bytes,bad)))
            folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-fatal-'+uuid.uuid4().hex);folder.mkdir()
            values={'before':saved,**{n:changed for n in ('damaged','diagnostic','halt')}}
            for name,parts in values.items():
                with (folder/(name+'.bin')).open('xb') as output:output.write(b''.join(parts))
            digest=lambda name:hashlib.sha256(b''.join(values[name])).hexdigest()
            events=[dict(kind='inject',case=kind,original=digest('before'),sha=digest('damaged'),writes=8),
                dict(kind='diagnostic',sha=digest('diagnostic'),interrupts=0),dict(kind='halt',sha=digest('halt'),cli_hlt=1)]
            trace='\n'.join('SERVICE_CPU_FATAL '+json.dumps(e) for e in events)
            serial='REIST_X86_64_PROCESS_SCHEDULER_STAGE_E0\n'
            self.assertEqual(r.validate_fatal(serial,trace,kind,folder),1)
            for bad in (trace+trace,trace.replace('"writes": 8','"writes": 16'),trace.replace('"interrupts": 0','"interrupts": 1')):
                with self.assertRaises(ValueError):r.validate_fatal(serial,bad,kind,folder)

    def test_producer_rejects_before_output(self):
        import build_x86_64_boot_programs as producer
        good=dict(service_cpu=True,task_pool=True,wide=True,import_image=True,startup=True,family=True)
        for key,value in [('service_cpu',1),('task_pool',False),('pool_pio',True),('pio',True),('block',True),
            ('filesystem',True),('file_launch',True),('wide',False),('import_image',False),('startup',False),('family',False),
            ('memory_case',1),('family_case',1),('filesystem_layout',1)]:
            folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-reject-'+uuid.uuid4().hex)
            with self.assertRaises(ValueError):producer.build(folder,[],[],[],0,**dict(good,**{key:value}))
            self.assertFalse(folder.exists())

    def test_actual_sdk_layout_and_dispatch(self):
        task=(ROOT/'userspace/sdk/include/reist/x86_64/task.h').read_text()
        self.assertEqual(task.count('#include <reist/x86_64/syscall.h>'),1)
        task=task.replace('#include <reist/x86_64/syscall.h>','')
        c='#include "'+(ROOT/'userspace/sdk/include/reist/abi/syscall.h').as_posix()+'"\n'+'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
static unsigned char captured[80];
static uint64_t number;
static int64_t reist_x64_syscall1(uint64_t call,uint64_t pointer) {
    const uint32_t *header=(const void*)(uintptr_t)pointer;
    number=call;
    if(header[1]!=64 && header[1]!=80)return -1;
    memset(captured,0xff,80);memcpy(captured,header,header[1]);return 777;
}
'''+task+'''
_Static_assert(sizeof(reist_task_create_v6_t)==80,"v6");
_Static_assert(offsetof(reist_task_create_v6_t,cpu_period_ms)==64,"append only");
_Static_assert(offsetof(reist_task_create_v6_t,reserved)==72,"reserved");
int main(void) {
    reist_task_profile_v1_t profile={0};reist_task_startup_v1_t startup={0};
    const char *arguments[]={"service"};
    if(reist_x64_startup_init(&startup,1,arguments) || startup.argc!=1)return 3;
    reist_task_control_request_t control={0};control.version=1;control.struct_size=64;
    if(reist_x64_task_control(&control)!=777 || number!=132)return 4;
    const void *image=(const void*)(uintptr_t)0x410000;
    for(unsigned version=2;version<=6;version++) {
        int64_t result=version==2?reist_x64_task_create(3,512,32,&startup):
            version==3?reist_x64_task_import(image,512,32,&startup):
            version==4?reist_x64_task_import_profile(image,&profile,32,&startup):
            version==5?reist_x64_task_import_wide(image,&profile,32,&startup):
            reist_x64_task_import_periodic(image,&profile,32,1000,&startup);
        reist_task_create_v6_t q;memcpy(&q,captured,80);
        if(result!=777 || number!=132 || q.version!=version || q.struct_size!=(version==6?80U:64U) ||
            q.operation!=1 || q.flags || q.target || q.timeout_ms || q.cpu_samples!=32 ||
            q.startup!=(uintptr_t)&startup || q.prepared!=(version==2?3:(uintptr_t)image) ||
            q.profile!=(version<4?512:(uintptr_t)&profile))return 1;
        if(version==6?(q.cpu_period_ms!=1000 || q.reserved):(q.cpu_period_ms!=UINT64_MAX || q.reserved!=UINT64_MAX))return 2;
    }
    puts("SERVICE_CPU_SDK_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',c,'SERVICE_CPU_SDK')

    def test_actual_fixture_branches_compile(self):
        folder=ROOT/'build/codex-agent/r83ap-service-cpu'/('host-fixture-'+uuid.uuid4().hex);folder.mkdir()
        header=folder/'blob.h'
        with header.open('x') as out:out.write('static const unsigned char import_blob[1]={0};\n')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for program in range(4):
            command=[str(host.find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror',
                '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
                '-Iuserspace/sdk/include','-DREIST_NATIVE_SERVICE_CPU=1','-Dmain=reist_pool_finite_fixture_main',
                '-DPROGRAM_ID='+str(program),'-include',str(header),'-c','arch/x86_64/user/task_pool.c','-o',str(folder/f'program{program}.o')]
            result=subprocess.run(command,cwd=ROOT,env=env,timeout=60,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            with (folder/f'program{program}.log').open('x') as out:out.write(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-2000:])

    def test_legacy_fixture_prefix_and_gate_binding(self):
        import verify_x86_64_service_cpu as v
        self.assertEqual((ROOT/'userspace/sdk/include/reist/abi/syscall.h').read_bytes(),
                         (ROOT/'include/reist/abi/syscall.h').read_bytes())
        original=(v.BASE/'original-source/arch__x86_64__user__task_pool.c').read_text()
        self.assertTrue((ROOT/'arch/x86_64/user/task_pool.c').read_text().startswith(original))
        self.assertEqual([v.gate_limit(n) for n in range(1,25)],[300]*15+[180]*5+[600,120,180,180])
        for bad in (True,0,25,-1):
            with self.assertRaises(ValueError):v.gate_limit(bad)

    def test_exact_debug_directory_adapter(self):
        import verify_x86_64_service_cpu as v
        baseline=v.read(v.BASE/'baseline.json')
        for profile,target in v.PROFILES:
            old_path=ROOT/baseline['old_profiles'][profile]['programs/program0.o']['path']
            old=old_path.read_bytes();old_directory='./'+str(old_path.parent.relative_to(ROOT))
            new_directory='./build\\codex-agent\\r83ap-service-cpu\\'+target+'\\x86_64\\programs-'+'0'*32
            header,entries,order=v.debug_object_sections(old)
            if profile=='file':
                self.assertNotIn('.debug_line',entries)
                with self.assertRaises(ValueError):v.debug_equivalent(old,old,old_directory,new_directory)
                continue
            line=entries['.debug_line'];delta=len(new_directory)-len(old_directory)
            self.assertEqual(line['data'].count(old_directory.encode()),1)
            changed=bytearray(line['data'].replace(old_directory.encode(),new_directory.encode()))
            for offset in (0,6):struct.pack_into('<I',changed,offset,struct.unpack_from('<I',changed,offset)[0]+delta)
            line['data']=bytes(changed);line['header'][5]=len(changed)
            relocation=entries['.rela.debug_line'];offset,info,addend=struct.unpack('<QQq',relocation['data'])
            relocation['data']=struct.pack('<QQq',offset+delta,info,addend)
            result=bytearray(old[:64])
            for index in order:
                entry=next(e for e in entries.values() if e['index']==index)
                alignment=1 if entry['header'][1]==8 else max(entry['header'][8],1)
                result+=bytes((-len(result))%alignment);entry['header'][4]=len(result);result+=entry['data']
            result+=bytes((-len(result))%8);header[5]=len(result)
            for entry in sorted(entries.values(),key=lambda e:e['index']):result+=struct.pack('<IIQQQQIIQQ',*entry['header'])
            struct.pack_into('<HHIQQQIHHHHHH',result,16,*header)
            self.assertRegex(v.debug_equivalent(old,bytes(result),old_directory,new_directory),'^[0-9a-f]{64}$')
            for entry in entries.values():
                if entry['header'][1]==8:
                    bad=bytearray(result);struct.pack_into('<Q',bad,header[5]+entry['index']*64+24,entry['header'][4]+8)
                    with self.assertRaises(ValueError):v.debug_equivalent(old,bytes(bad),old_directory,new_directory)
                if not entry['data']:continue
                for offset in {0,len(entry['data'])//2,len(entry['data'])-1}:
                    bad=bytearray(result);bad[entry['header'][4]+offset]^=1
                    with self.subTest(profile=profile,index=entry['index'],offset=offset):
                        with self.assertRaises(ValueError):v.debug_equivalent(old,bytes(bad),old_directory,new_directory)
            for directory in (new_directory+'x',new_directory.replace('programs-','unbound-'),new_directory.replace(target,'native')):
                with self.assertRaises(ValueError):v.debug_equivalent(old,bytes(result),old_directory,directory)

    def test_actual_run_admission(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('process_run_admit64:',1)[1].split('process_run_validate64:',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_SERVICE_CPU 1
%define REIST_NATIVE_PROGRAMS 1
%define REIST_NATIVE_LIFECYCLE 1
%include "arch/x86_64/mm/native_layout.inc"
section .text
global process_run_admit64
process_run_admit64:
'''+body
        c='#define SERVICE_RUN_TEST 1\n#include "'+(ROOT/'test/x86_64_service_cpu_host.c').as_posix()+'"\n'
        host.TaskFrameTests().build(asm,c,'SERVICE_CPU_RUN')


def load_tests(loader,tests,pattern):
    # The approved host-budget transaction keeps24 gate groups. Execute the
    # shared adapters' behavior/cleanup regressions in this existing host gate.
    import test_x86_64_binary_memory as binary
    import test_x86_64_file_transport as transport
    tests.addTests(loader.loadTestsFromTestCase(binary.BinaryTests))
    tests.addTests(loader.loadTestsFromTestCase(transport.FileTransportTests))
    return tests


if __name__=='__main__':unittest.main()
