"""Private qualification CPU trace-v1; full records, no inferred charges."""
from pathlib import Path
import ast,hashlib,inspect,json,re,stat,struct


def decode_trace_record(raw,sequence):
    if type(raw) is not bytes or len(raw)!=192 or type(sequence) is not int or not 1<=sequence<=2048:
        raise ValueError('CPU trace extent/sequence')
    version,kind,index,slot,gen,now,result,*words=struct.unpack('<4I3Q19Q',raw)
    if (version,kind,index)!=(1,1,sequence) or slot>=8 or not 0<gen<1<<31 or now>=1<<60 or result not in (1,2):
        raise ValueError('CPU trace header/result')
    if words[16]&512 or words[17]&512 or words[18]!=8:
        raise ValueError('CPU trace IF/mode')
    return dict(kind='cpu_charge',slot=slot,gen=gen,now=now,result=result,before=words[:8],after=words[8:16])


class CPUTraceReader:
    def __init__(self,read,address,end,ledger,starts,clock,path,emit):
        if type(address) is not int or type(end) is not int or not 0<=address<end<1<<64 or end-address!=32+257*192:
            raise ValueError('CPU trace symbol extent')
        self.read=read;self.address=address;self.ledger=ledger;self.starts=starts;self.clock=clock;self.emit=emit
        self.sequence=0;self.started=False;self.closed=False;self.sha=hashlib.sha256()
        self.stream=path.open('xb',buffering=0)

    def initialize(self):
        if self.started:raise ValueError('CPU trace duplicate initialization')
        raw=self.read(self.address,32+257*192)
        if len(raw)!=32+257*192 or any(raw):raise ValueError('CPU trace not initially zero')
        self.started=True

    def drain(self):
        if not self.started:return
        raw=self.read(self.address,32)
        if len(raw)!=32:raise ValueError('CPU trace header read')
        total,error,pending,reserved=struct.unpack('<4Q',raw)
        if error or pending or reserved or not self.sequence<=total<=2048 or total-self.sequence>256:
            raise ValueError('CPU trace corrupt/overflow/pending header')
        if self.closed and total!=self.sequence:raise ValueError('CPU trace after closure')
        if total==self.sequence:return
        now=self.clock()
        if type(now) is not int or not 0<=now<1<<60:raise ValueError('CPU trace observation time')
        for _ in range(2):
            if self.sequence==total:break
            index=self.sequence&255;count=min(total-self.sequence,256-index)
            chunk=self.read(self.address+32+index*192,count*192)
            if len(chunk)!=count*192:raise ValueError('CPU trace ring read')
            for offset in range(0,len(chunk),192):
                raw=chunk[offset:offset+192];event=decode_trace_record(raw,self.sequence+1)
                entry=self.starts.get(event['gen'])
                if not entry or not entry['live'] or entry['slot']!=event['slot'] or event['now']>now:
                    raise ValueError('CPU trace owner/time')
                if self.stream.write(raw)!=192:raise OSError('CPU trace short write')
                self.sha.update(raw);self.ledger.event(**event);self.sequence+=1
        if self.sequence!=total:raise ValueError('CPU trace incomplete drain')

    def finish(self):
        if not self.started or self.closed:raise ValueError('CPU trace closure state')
        self.drain()
        if not self.sequence:raise ValueError('CPU trace empty closure')
        self.stream.close();self.closed=True
        self.emit('PIO_CPU_TRACE_END '+str(self.sequence)+' '+self.sha.hexdigest()+'\n')


def scope_observer(code):
    """Only adapt transport; keep the original callback/oracle bodies."""
    def once(body,old,new):
        if body.count(old)!=1:raise ValueError('CPU trace exact observer adaptation')
        return body.replace(old,new)
    constructors="""for core in ('reist_x64_period_apply','reist_x64_budget_apply'):
    CPUHook(core+'.charge',cpu_charge)
    CPUHook(core+'.charge_result',cpu_return)"""
    code=once(code,constructors,'# Full raw CPU trace replaces only per-charge debugger stops.')
    for name in ('Hook','ReleaseEnd'):
        tree=ast.parse(code);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='observe')
        old=ast.get_source_segment(code,node)
        if name=='Hook':
            new=once(old,'            self.fn()',
                '            cpu_trace_reader.drain()\n            self.fn()\n            if self.fn is boot:cpu_trace_reader.initialize()')
        else:new=once(old,'        try:\n','        try:\n            cpu_trace_reader.drain()\n')
        code=once(code,old,new)
    code=once(code,'if runs==2:cpu_ledger.finish()','if runs==2:cpu_trace_reader.finish();cpu_ledger.finish()')
    code+='\n'+inspect.getsource(decode_trace_record)+'\n'+inspect.getsource(CPUTraceReader)+'''
cpu_trace_reader=CPUTraceReader(lambda a,n:mem(a,n),S['native_cpu_trace'],S['native_cpu_trace_end'],
    cpu_ledger,starts,lambda:q(S['scheduler_last_tick']),Path(CONFIG['cpu_ledger']).with_name('cpu-trace-v1.bin'),gdb.write)
def cpu_trace_full():pass
Hook('native_cpu_trace_after64.full',cpu_trace_full)
'''
    compile(code,'<bounded CPU trace observer>','exec')
    return code


def validate_trace_records(trace,raw,events):
    if type(raw) is not bytes or not 0<len(raw)<=2048*192 or len(raw)%192:
        raise ValueError('CPU trace raw capacity')
    marker='PIO_CPU_TRACE_END '+str(len(raw)//192)+' '+hashlib.sha256(raw).hexdigest()
    if [line for line in trace.splitlines() if line.startswith('PIO_CPU_TRACE')]!=[marker]:
        raise ValueError('CPU trace closure binding')
    records=[decode_trace_record(raw[n:n+192],n//192+1) for n in range(0,len(raw),192)]
    if records!=[event for event in events if event['kind']=='cpu_charge']:
        raise ValueError('CPU trace exact ledger equivalence')
    return records


def validate_capture(folder,trace,cpu):
    path=folder/'cpu-trace-v1.bin'
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_nlink!=1 or
        getattr(info,'st_file_attributes',0)&0x400 or not 0<info.st_size<=2048*192):
        raise ValueError('CPU trace raw file')
    normalized=''.join('TASK_POOL '+line[9:] if line.startswith('POOL_PIO ') else line for line in trace.splitlines(keepends=True))
    expanded=cpu.expand_cpu_trace(normalized,(folder/cpu.CPU_FILE).read_bytes())
    events=[json.loads(line[10:]) for line in expanded.splitlines() if line.startswith('TASK_POOL ')]
    records=validate_trace_records(trace,path.read_bytes(),events)
    reads=cpu.binary_capacity(folder);failure=folder/'release-failure.json';extra=int(failure.exists())
    size=sum(r['bytes'] for r in reads)+(folder/cpu.CPU_FILE).stat().st_size+info.st_size+(failure.stat().st_size if extra else 0)
    if len(reads)+2+extra>2048 or size>128*1024*1024:raise ValueError('CPU trace aggregate capacity')
    return records
