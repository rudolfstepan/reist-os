"""Reject incomplete/malformed evidence at the actual profile guest oracle."""
from pathlib import Path
import ast,copy,hashlib,json,struct,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_qemu_x86_64_block_profile as r

def sample(case,oom=None):
    events=[dict(kind='poison',bytes=270336),dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]
    per=3 if case==6 else 4;blocks=[]
    def emit(kind,**fields):events.append(dict(kind=kind,**fields))
    for run in range(2):
        base=run*per;block=''
        for slot in (0,1):emit('start',slot=slot,gen=base+slot+1,pages=12,private=9)
        if oom is not None:
            emit('oom',owner=(base+1)<<32,acquired=oom);emit('rollback',owner=(base+1)<<32,acquired=oom,free=1000,before=1000)
        for ordinal in range(per-2):
            gen=base+ordinal+3;limit=1 if ordinal else 9;mode=case if not ordinal and case in (1,2,3,4,6) else 0
            emit('copy',gen=gen,bytes=r.wide.SIZE,sha='a'*64);emit('create',gen=gen,acquired=27)
            emit('start',slot=2,gen=gen,pages=12,private=9);emit('bind',gen=gen,owner=(gen<<32)|2)
            emit('ready',gen=gen,limit=limit,capacity=19 if case==5 else 128,deadline=2500)
            count=0 if case==5 else 1 if mode else limit+1
            for n in range(1,count+1):
                emit('request',gen=gen,sequence=n,lba=n)
                if mode in (1,2,3,6):emit('partial',gen=gen,bytes=256,mode=2 if mode==6 else mode)
                else:emit('reply',gen=gen,sequence=n,status=-11 if n==limit+1 else 0,bytes=0 if n==limit+1 else 512,noio=int(n==limit+1),bad=int(mode==4))
                if case!=6:
                    status=-110 if mode in (1,2,3) else -71 if mode==4 else -11 if n==limit+1 else 0
                    data=bytes([0xcc])*512 if status else bytes((b^(n*17)^0xa5)&255 for b in range(512))
                    emit('result',gen=gen,sequence=n,status=status,bytes=512,sha=hashlib.sha256(data).hexdigest())
            if mode in (1,6):emit('fault',gen=base+1 if mode==6 else gen,slot=0 if mode==6 else 2,vector=6)
            if mode in (2,4,6):emit('cancel',gen=gen,slot=2,state=6)
            lbas=[] if case==5 else [0,1] if mode else list(range(limit+1))
            size=0 if case==5 else 768 if mode in (1,2,3,6) else 1024 if mode==4 else 512*(limit+1)
            data=b''.join(bytes((n^(lba*17)^0xa5)&255 for n in range(512)) for lba in lbas)[:size]
            emit('retire',gen=gen,identify=0 if case==5 else 512,data=size,lbas=lbas,sha=hashlib.sha256(data).hexdigest(),fenced=1)
            emit('release',slot=2,gen=gen,frames=16,before=1000,after=1016,fenced=1)
        for slot in (0,1):emit('release',slot=slot,gen=base+slot+1,frames=16,before=1000,after=1016,fenced=1)
        count=sum((e['identify']+e['data'])//32+5+6*len(e['lbas']) for e in events if e['kind']=='retire' and base<e['gen']<=base+per)
        emit('trace_drained',run=run+1,events=count,sha='a'*64);emit('trace_clean',run=run+1,bytes=12304)
        emit('finish',run=run+1,free=1000,initial=1000,tasks=per,generation=(run+1)*per)
        for n in range(1,per+1):
            slot=n-1 if n<3 else 2;mode=case if n==3 else 0
            status=134 if case==6 and slot==0 else (79 if case==5 else 78) if slot==0 else 77 if slot==1 else 134 if mode==1 else 0 if mode in (2,4,6) else 256 if mode==3 else 89 if case==5 else 80
            state=3 if (case==6 and slot==0) or (slot==2 and mode in (1,2,3,4,6)) else 4
            block+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,base+n,status,state,32 if status==256 else 4,0x410123).hex().upper()+'\n'
        blocks.append(block+r.wide.process.DONE+'\n')
    markers=[m for m in r.wide.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[r.wide.process.SUCCESS]
    serial='\n'.join(markers).replace('REIST_X86_64_C_KERNEL_CONTROL_OK',''.join(blocks)+'REIST_X86_64_C_KERNEL_CONTROL_OK')
    return serial,events

def trace(events):return '\n'.join('PROFILE '+json.dumps(e) for e in events)

class ProfileRuntimeTests(unittest.TestCase):
    def test_exact_events_and_mutations(self):
        for case in range(8):
            oom=13 if case==7 else None;serial,events=sample(case,oom)
            self.assertEqual(len(r.validate(serial,trace(events),case,oom,27)),6 if case==6 else 8)
            for n in range(len(events)):
                for bad in (events[:n]+events[n+1:],events[:n]+[events[n]]+events[n:],list(reversed(events))):
                    with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,27)
            for kind,key,value in (('boot','aliases',1),('create','acquired',26),('copy','bytes',36896),('ready','limit',8),
                    ('retire','data',1),('retire','fenced',0),('release','after',1000),('finish','free',999),('trace_drained','events',1),('trace_clean','bytes',12288)):
                bad=copy.deepcopy(events);next(e for e in bad if e['kind']==kind)[key]=value
                with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,27)
            for bad in (serial+serial,serial.replace(r.wide.process.SUCCESS,''),serial+'\n'+r.wide.transport.FAILURES[0]):
                with self.assertRaises(ValueError):r.validate(bad,trace(events),case,oom,27)

    def test_exact_inherited_observer_boundaries(self):
        code=r.observer_body();compile(code,'block-profile-observer','exec')
        self.assertTrue(r.observer({},dict(symbols={}),ROOT/'build',0,None,0,0).startswith('set breakpoint always-inserted on\n'))
        self.assertIn("r['freed']==r['frames']",code)
        self.assertIn("frames[-1]==t[2]!=reg('cr3')",code)
        self.assertIn('pio_retire(slot,gen)',code)
        out=code.split('def out(event):',1)[1].split('def data(event):',1)[0]
        self.assertIn('port,value,slot,gen,parent=event[3]',out)
        self.assertIn('assert parent==gen<<32',out)
        self.assertIn("assert parent==devices[owner]['parent']",out)
        self.assertNotIn("Hook('native_pio_out8.done'",code)
        self.assertNotIn("Hook('native_pio_apply64.transfer_done'",code)
        for fn in ('pio_retire(slot,gen)','fault()','cancel()'):
            self.assertIn('def '+fn+':\n    trace_drain()',code)
        self.assertIn("trace_clean(mem(S['native_pio_trace'],12304))",code)
        self.assertEqual(code.count('start_hook.enabled=True'),2)
        self.assertIn('or identity in starts for state,identity in live):start_hook.enabled=False',code)
        self.assertNotIn('def syscall():',code)
        with self.assertRaises(ValueError):r.once('duplicate duplicate','duplicate','x')

    def test_exact_fault_rejection_and_continuation(self):
        serial,_=sample(0)
        for fault in ('gap','data','cleanup'):
            events=[dict(kind='trace_inject',fault=fault),dict(kind='trace_reject',fault=fault,error='trace '+fault)]
            self.assertEqual(len(r.validate_trace_fault(serial,trace(events),fault)),8)
            for bad in (events[:1],events[1:],events+events,list(reversed(events)),events+[dict(kind='finish')]):
                with self.assertRaises(ValueError):r.validate_trace_fault(serial,trace(bad),fault)
            for bad in (serial.replace(r.wide.process.SUCCESS,''),serial+serial):
                with self.assertRaises(ValueError):r.validate_trace_fault(bad,trace(events),fault)

    def test_data_injection_consumes_only_valid_prefix_before_exact_rejection(self):
        owner=3<<32|2;state=(owner,owner^0xffffffffffffffff,0,1,2,3,1,0)
        raw=bytearray(12304);struct.pack_into('<Q',raw,0,3)
        for seq,port,value,slot,gen in ((1,0x3f6,6,0,1),(2,0x3f6,2,2,3)):
            struct.pack_into('<2Q8Q5Q',raw,16+(seq-1)*192,1,seq,*state,port,value,slot,gen,1<<32)
        start=16+2*192;struct.pack_into('<2Q8Q',raw,start,2,3,*state)
        struct.pack_into('<4IQ4I3Q',raw,start+80,2,64,4,0,owner,0x1f0,0,16,0,0x408000,100,0)
        raw[start+144:start+176]=bytes(n^0xa5 for n in range(32));struct.pack_into('<Q',raw,start+176,16)
        original=bytes(raw);events=[];observed=[];commands=[]
        class Debugger:
            @staticmethod
            def selected_inferior():return Debugger
            @staticmethod
            def write_memory(address,value):raw[address:address+len(value)]=value
            @staticmethod
            def execute(command):commands.append(command)
        def data(event):
            observed.append(event[1])
            if event[4]!=bytes(n^0xa5 for n in range(32)):raise ValueError('trace data')
        ns=dict(CONFIG={'trace_fault':'data'},S={'native_pio_trace':0},struct=struct,trace_injected=False,
                trace_sequence=0,trace_digest=hashlib.sha256(),trace_decode=r.trace_decode,trace_snapshot=r.trace_snapshot,
                mem=lambda a,n:bytes(raw[a:a+n]),q=lambda a:struct.unpack_from('<Q',raw,a)[0],gdb=Debugger,
                emit=lambda kind,**kw:events.append(dict(kind=kind,**kw)),
                out=lambda event:(observed.append(event[1]),events.append(dict(kind='bind'))),data=data)
        functions=[node for node in ast.parse(r.EXTRA).body if isinstance(node,ast.FunctionDef) and node.name in ('trace_inject','trace_drain','trace_expected_rejection')]
        exec(compile(ast.Module(functions,type_ignores=[]),'actual-trace-injection','exec'),ns)
        ns['trace_inject']();self.assertEqual(observed,[1,2]);self.assertEqual(ns['trace_sequence'],2)
        self.assertEqual(ns['trace_digest'].digest(),hashlib.sha256(original[16:start]).digest())
        self.assertEqual([n for n in range(len(raw)) if raw[n]!=original[n]],[start+144])
        self.assertEqual(events[-1],dict(kind='trace_inject',fault='data'))
        with self.assertRaisesRegex(ValueError,'trace data') as caught:ns['trace_drain']()
        self.assertTrue(ns['trace_expected_rejection'](caught.exception));self.assertEqual(commands,['detach','quit'])
        serial,_=sample(0);self.assertEqual(len(r.validate_trace_fault(serial,trace(events),'data')),8)
        after=bytes(raw);ns['trace_inject']();self.assertEqual(bytes(raw),after)
        self.assertEqual(ns['trace_sequence'],2) # The corrupted record was never accepted.

if __name__=='__main__':unittest.main()
