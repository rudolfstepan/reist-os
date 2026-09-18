"""Qualification trace: real producer and strict bounded consumer, no timing model."""
from pathlib import Path
import ast,copy,hashlib,inspect,json,struct,sys,tempfile,textwrap,unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]

class CPUTraceTests(unittest.TestCase):
    @staticmethod
    def records(count):
        import run_qemu_x86_64_service_cpu as cpu
        words=[3,32,0,0,100,0,0,0];out=[]
        for n in range(1,count+1):
            before=words;words,result=cpu.charge_result(words,n*100+1)
            event=dict(kind='cpu_charge',slot=2,gen=3,now=n*100+1,result=result,before=before,after=words)
            raw=struct.pack('<4I3Q19Q',1,1,n,2,3,event['now'],result,*before,*words,2,2,8)
            out.append((raw,event))
        return out

    def test_ring_drain_wrap_closure_and_exact_ledger(self):
        import native_cpu_trace as t
        rows=self.records(514);memory=bytearray(32+257*192);events=[];markers=[]
        with tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent') as folder:
            path=Path(folder)/'raw.bin'
            reader=t.CPUTraceReader(lambda a,n:bytes(memory[a-4096:a-4096+n]),4096,4096+len(memory),
                SimpleNamespace(event=lambda **e:events.append(e)),{3:dict(slot=2,live=True)},lambda:1000000,path,markers.append)
            with reader.stream:
                reader.initialize()
                with self.assertRaises(ValueError):reader.initialize()
                for first,last in ((1,250),(251,400),(401,514)):
                    for n in range(first,last+1):memory[32+((n-1)&255)*192:32+((n-1)&255)*192+192]=rows[n-1][0]
                    struct.pack_into('<4Q',memory,0,last,0,0,0);reader.drain();reader.drain()
                    self.assertEqual(reader.sequence,last)
                reader.finish();reader.drain()
                self.assertEqual(events,[e for _,e in rows]);self.assertTrue(reader.closed)
                self.assertEqual(path.read_bytes(),b''.join(r for r,_ in rows))
                self.assertEqual(t.validate_trace_records(''.join(markers),path.read_bytes(),events),events)
                with self.assertRaises(ValueError):reader.finish()
                struct.pack_into('<Q',memory,0,515)
                with self.assertRaises(ValueError):reader.drain()

    def test_raw_mutations_cannot_be_promoted_to_ledger(self):
        import native_cpu_trace as t
        rows=self.records(2);raw=b''.join(r for r,_ in rows);events=[e for _,e in rows]
        def marker(data):return 'PIO_CPU_TRACE_END '+str(len(data)//192)+' '+hashlib.sha256(data).hexdigest()+'\n'
        self.assertEqual(t.validate_trace_records(marker(raw),raw,events),events)
        for byte in range(168):
            for bit in range(8):
                changed=bytearray(raw);changed[byte]^=1<<bit;changed=bytes(changed)
                with self.subTest(byte=byte,bit=bit),self.assertRaises(ValueError):
                    t.validate_trace_records(marker(changed),changed,events)
        for offset in (168,176):
            changed=bytearray(raw);struct.pack_into('<Q',changed,offset,514)
            with self.assertRaises(ValueError):t.validate_trace_records(marker(changed),bytes(changed),events)
        for mode in (0,7,9,(1<<64)-1):
            changed=bytearray(raw);struct.pack_into('<Q',changed,184,mode)
            with self.assertRaises(ValueError):t.decode_trace_record(bytes(changed[:192]),1)
        for data in (raw[:192],raw[192:]+raw[:192],raw[:-1],b'',raw*1025):
            with self.assertRaises(ValueError):t.validate_trace_records(marker(data),data,events)
        for footer in ('',marker(raw)*2,marker(raw).replace(' 2 ',' 3 ')):
            with self.assertRaises(ValueError):t.validate_trace_records(footer,raw,events)
        for key in ('before','after'):
            for word in range(8):
                changed=copy.deepcopy(events);changed[0][key][word]^=1
                with self.assertRaises(ValueError):t.validate_trace_records(marker(raw),raw,changed)

    def test_consumer_rejects_overrun_pending_owner_time_and_io_failures(self):
        import native_cpu_trace as t
        raw,event=self.records(1)[0]
        cases=('error','pending','reserved','overrun','capacity','sequence','short_header','short_ring',
               'dead','slot','future','write','ledger','nonzero_boot','backward')
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory(dir=ROOT/'build/codex-agent') as folder:
                memory=bytearray(32+257*192);events=[];starts={3:dict(slot=2,live=True)}
                def read(a,n):
                    out=bytes(memory[a-4096:a-4096+n])
                    return out[:-1] if reader.started and (case=='short_header' and n==32 or case=='short_ring' and n==192) else out
                def emit(**e):
                    if case=='ledger':raise OSError('ledger failure')
                    events.append(e)
                reader=t.CPUTraceReader(read,4096,4096+len(memory),SimpleNamespace(event=emit),starts,
                    lambda:100 if case=='future' else 101,Path(folder)/'raw',lambda s:None)
                with reader.stream:
                    if case=='nonzero_boot':
                        memory[-1]=1
                        with self.assertRaises(ValueError):reader.initialize()
                        continue
                    reader.initialize();memory[32:224]=raw;struct.pack_into('<4Q',memory,0,1,0,0,0)
                    if case in ('error','pending','reserved'):struct.pack_into('<Q',memory,8*{'error':1,'pending':2,'reserved':3}[case],1)
                    if case in ('overrun','capacity'):struct.pack_into('<Q',memory,0,257 if case=='overrun' else 2049)
                    if case=='sequence':memory[40]^=1
                    if case=='dead':starts[3]['live']=False
                    if case=='slot':starts[3]['slot']=3
                    if case=='backward':reader.sequence=2
                    stream=reader.stream
                    if case=='write':reader.stream=SimpleNamespace(write=lambda raw:191)
                    with self.assertRaises((ValueError,OSError)):reader.drain()
                    reader.stream=stream
                    self.assertFalse(events)

    def test_actual_callback_adapter_preserves_checks_and_drain_order(self):
        import native_cpu_trace as t
        import run_qemu_x86_64_service_pio as runtime
        original=runtime.observer_body();changed=t.scope_observer(original)
        self.assertNotIn("    CPUHook(core+'.charge',cpu_charge)",changed)
        self.assertEqual(changed.count("Hook('native_cpu_trace_after64.full',cpu_trace_full)"),1)
        tree=ast.parse(changed);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Hook')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='observe')
        method=textwrap.dedent(ast.get_source_segment(changed,node))
        for boot in (False,True):
            for fail in ('','drain','callback','initialize'):
                calls=[]
                def operation(name):
                    calls.append(name)
                    if name==fail:raise ValueError('injected')
                def callback():operation('callback')
                env=dict(callbacks=0,cpu_trace_reader=SimpleNamespace(drain=lambda:operation('drain'),initialize=lambda:operation('initialize')),
                    boot=callback if boot else object(),emit=lambda *a,**k:calls.append('failure'),
                    gdb=SimpleNamespace(write=lambda s:None,execute=lambda s:calls.append(s)))
                exec(compile(method,'<actual traced Hook.observe>','exec'),env)
                env['observe'](SimpleNamespace(fn=callback))
                self.assertEqual(calls[:1],['drain'])
                if fail=='drain':self.assertNotIn('callback',calls)
                elif not fail:self.assertEqual(calls,['drain','callback']+(['initialize'] if boot else []))
                if fail in ('drain','callback') or boot and fail=='initialize':self.assertIn('quit 71',calls)
        constructors="for core in ('reist_x64_period_apply','reist_x64_budget_apply'):\n    CPUHook(core+'.charge',cpu_charge)\n    CPUHook(core+'.charge_result',cpu_return)"
        restored=changed[:changed.index('\ndef decode_trace_record')]
        restored=restored.replace('# Full raw CPU trace replaces only per-charge debugger stops.',constructors)
        restored=restored.replace('            cpu_trace_reader.drain()\n','').replace('            if self.fn is boot:cpu_trace_reader.initialize()\n','')
        restored=restored.replace('if runs==2:cpu_trace_reader.finish();cpu_ledger.finish()','if runs==2:cpu_ledger.finish()')
        self.assertEqual(restored.rstrip(),original.rstrip())
        for bad in (original+'\n'+constructors,original.replace(constructors,''),changed):
            with self.assertRaises(ValueError):t.scope_observer(bad)
        factory=inspect.getsource(runtime.observer)
        self.assertIn('native_cpu_trace.scope_observer(observer_body())',factory)

    def test_actual_assembly_ring_and_unchanged_core(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        wrapper='scheduler_budget_apply64:'+source.split('scheduler_budget_apply64:',1)[1].split('; Wait completion validates',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_TASK_POOL 1
%define REIST_NATIVE_SERVICE_CPU 1
%define REIST_NATIVE_POOL_PIO 1
%define REIST_NATIVE_CPU_TRACE 1
%include "arch/x86_64/mm/native_layout.inc"
SCHEDULER_MODE_PROCESS equ 8
TASK_RECORD_SIZE equ 1024
section .bss
align 16
global scheduler_cpu_budgets,scheduler_cpu_windows,process_run_plan,scheduler_mode,scheduler_last_tick,scheduler_tasks,scheduler_current_slot
scheduler_cpu_budgets:resb 256
scheduler_cpu_windows:resb 256
process_run_plan:resb 336
scheduler_last_tick:resq 1
scheduler_tasks:resb 8192
scheduler_current_slot:resd 1
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
global trace_flags_probe
trace_flags_probe:
    push rbx
    lea rdi,[rel scheduler_cpu_budgets]
    lea rsi,[rel scheduler_cpu_windows]
    mov edx,2
    mov ecx,100
    mov r9d,1
    stc
    pushfq
    pop rbx
    call native_cpu_trace_before64
    pushfq
    pop rax
    cmp rax,rbx
    jne .bad
    mov eax,1
    stc
    pushfq
    pop rbx
    call native_cpu_trace_after64
    pushfq
    pop rax
    cmp rax,rbx
    jne .bad
    mov eax,1
    pop rbx
    ret
.bad:
    xor eax,eax
    pop rbx
    ret
'''+wrapper+'''
%include "arch/x86_64/proc/cpu_budget.asm"
%include "arch/x86_64/proc/cpu_trace.inc"
'''
        host.TaskFrameTests().build(asm,ROOT/'test/x86_64_cpu_trace_host.c','CPU_TRACE')

if __name__=='__main__':unittest.main()
