"""Four fixed same-image diagnostic runs; never an acceptance substitute."""
from pathlib import Path
import argparse,hashlib,json,re,struct,time,uuid,subprocess,inspect
import run_qemu_x86_64_block_service as block
ROOT=block.ROOT

def count_attribution(counts,key):
    if sum(counts.values())>=4096 or key not in counts and len(counts)>=256:
        raise ValueError('attribution capacity')
    counts[key]=counts.get(key,0)+1

def sample_attribution(generation,rip,return_rip,number):
    return ('irq',generation,number if rip==return_rip else -1,rip)

def read_attribution(trace):
    values=re.findall(r'^BLOCK_ATTRIBUTION (.*)$',trace,re.M)
    if len(values)!=1 or trace.count('BLOCK_ATTRIBUTION')!=1:
        raise ValueError('missing/duplicate attribution summary')
    rows=json.loads(values[0]);seen=set();total=0
    if not isinstance(rows,list) or not 1<=len(rows)<=256:raise ValueError('attribution rows')
    for row in rows:
        if not isinstance(row,list) or len(row)!=2:raise ValueError('attribution row')
        key,count=row
        if not isinstance(key,list) or len(key)!=4 or key[0] not in ('irq','ipc') or any(type(v) is not int for v in key[1:]):raise ValueError('attribution key')
        if type(count) is not int or not 1<=count<=4096 or tuple(key) in seen:raise ValueError('attribution count')
        seen.add(tuple(key));total+=count
    if total>4096:raise ValueError('attribution total')
    return rows

def attribution_commands(kind,s,c,folder,record,result):
    if kind=='detached':return commands(kind,s,c,folder,record,result)
    base=commands('full' if kind=='full-irq' else 'minimal',s,c,folder,record,result)
    if kind not in ('irq','ipc','full-irq'):raise ValueError('attribution mode')
    extra='python\nimport gdb,struct,json\n'+inspect.getsource(count_attribution)+inspect.getsource(sample_attribution)
    extra+=f'''
attribution_counts={{}}
attribution_callbacks=0
def attribution_reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def attribution_u64(a):return struct.unpack('<Q',bytes(gdb.selected_inferior().read_memory(a,8)))[0]
class Attribution(gdb.Breakpoint):
    def stop(self):
        global attribution_callbacks
        try:
            if attribution_callbacks>=4096:raise ValueError('attribution callback capacity')
            attribution_callbacks+=1
            if bytes(gdb.selected_inferior().read_memory({s['scheduler_mode']},1))!=b'\\x08':return False
            if {kind=='ipc'}:
                operation=attribution_reg('rdi');slot=attribution_reg('rsi');gen=attribution_reg('rdx')
                number=attribution_u64(attribution_reg('r8')) if operation==1 else -1
                key=('ipc',slot,operation,number)
            else:
                frame=attribution_reg('rdi')
                if attribution_u64(frame+144)&3!=3:return False
                slot=int(gdb.parse_and_eval('*(unsigned int*){s['scheduler_current_slot']}'))
                gen=attribution_u64({s['scheduler_tasks']}+slot*256+8)
                key=sample_attribution(gen,attribution_u64(frame+136),attribution_u64({s['syscall_rcx']}),attribution_u64({s['syscall_rax']}))
            count_attribution(attribution_counts,key)
            return False
        except Exception as error:
            gdb.write('BLOCK_ATTRIBUTION_FAIL '+str(error)+'\\n');gdb.execute('quit 82')
Attribution('*'+str({s['process_ipc_call64'] if kind=='ipc' else s['process_run_irq_tail64']}),internal=True)
attribution_execute=gdb.execute
def attribution_dump(command,*args,**kwargs):
    if command.startswith('quit'):
        gdb.write('BLOCK_ATTRIBUTION '+json.dumps([[list(k),v] for k,v in sorted(attribution_counts.items())])+'\\n')
    return attribution_execute(command,*args,**kwargs)
gdb.execute=attribution_dump
end
'''
    # CLI quit commands do not traverse gdb.execute: explicitly emit there too.
    base=re.sub(r'^quit$', 'python attribution_dump("quit")',base,flags=re.M)
    return base[:-len('continue\n')]+extra+'continue\n'

def inputs(image):
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    candidates=[d for d in image.parent.glob('programs-*') if (d/'boot-programs.bin').is_file() and (d/'boot-programs.bin').read_bytes()==catalog]
    if not candidates:raise ValueError('diagnostic catalog provenance')
    d=candidates[0];record=block.pio.producer.prepare((d/'program2.prg').read_bytes(),[])
    def address(n,name):
        values=re.findall(r'^\s*([0-9a-f]+)\s+(?:[0-9a-f]+\s+)*'+name+r'\s*$',(d/f'program{n}.map').read_text(),re.M)
        if len(values)!=1:raise ValueError('diagnostic map')
        return int(values[0],16)
    inner=block.startup.family.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    c=block.startup.family.payload.validate(inner);block.startup.family.payload.verify_outer(inner,block.startup.family.payload.read_bounded(image))
    s=block.startup.family.symbols(image)
    return s,c,record,address(0,'block_result_record')

def commands(kind,s,c,folder,record,result):
    logging='set logging file '+(folder/'frame-trace.log').as_posix()+'\nset logging enabled on\n'
    if kind=='detached':return logging+'detach\nquit\n'
    if kind=='minimal':
        return logging+f'''set $finished=0
break *{s['scheduler_return64']:#x} if *(unsigned char*){s['scheduler_mode']:#x}==8
commands
silent
set $finished=$finished+1
if $finished==2
detach
quit
end
continue
end
continue
'''
    code=block.observer(s,c,folder,4096,0,None,record,result)
    if kind=='full':return code
    if kind!='counted':raise ValueError('diagnostic mode')
    extra='''python
import time,json
diagnostic_counts={};diagnostic_seconds={}
def counted(original,label):
    def wrapped(self):
        diagnostic_counts[label]=diagnostic_counts.get(label,0)+1
        if sum(diagnostic_counts.values())>20000:raise RuntimeError('diagnostic counter bound')
        start=time.perf_counter()
        try:return original(self)
        finally:diagnostic_seconds[label]=diagnostic_seconds.get(label,0)+time.perf_counter()-start
    return wrapped
for cls in (Start,Cancel,StartupCopy,StartupScrub,PioOut,PioData,PioFailure,BlockIPC,BlockResult):
    cls.stop=counted(cls.stop,cls.__name__)
diagnostic_execute=gdb.execute
def execute(command,*args,**kwargs):
    if command.startswith('quit'):
        gdb.write('BLOCK_COST_COUNTS '+json.dumps(diagnostic_counts,sort_keys=True)+'\\n')
        gdb.write('BLOCK_COST_SECONDS '+json.dumps(diagnostic_seconds,sort_keys=True)+'\\n')
    return diagnostic_execute(command,*args,**kwargs)
gdb.execute=execute
end
'''
    return code[:-len('continue\n')]+extra+'continue\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--attribution',action='store_true');a=p.parse_args()
    image=a.image.resolve()
    if not image.is_relative_to(ROOT/'build/codex-agent'):raise ValueError('diagnostic image scope')
    folder=ROOT/'build/codex-agent/r83ai-block/diagnostic'/(('attribution-' if a.attribution else 'controlled-')+uuid.uuid4().hex);folder.mkdir(parents=True)
    files=(image,image.parent/'boot-programs.bin',image.parent/'reist-x86_64-c-core.elf')
    hashes=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    summary=dict(diagnostic_only=True,hashes=hashes(),cases=[]);started=time.monotonic()
    s,c,record,result=inputs(image)
    try:
        for kind in (('detached','irq','ipc','full-irq') if a.attribution else ('detached','minimal','full','counted')):
            if hashes()!=summary['hashes']:raise ValueError('diagnostic input drift')
            out=folder/kind;out.mkdir();item=dict(mode=kind);begin=time.monotonic()
            try:
                build_commands=attribution_commands if a.attribution else commands
                block.startup.family.programs.capture(image,out,build_commands(kind,s,c,out,record,result),4096,block.pio.Fixture(out,block=True))
            except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as error:item['capture_error']=str(error)
            serial=(out/'guest.log').read_text() if (out/'guest.log').is_file() else ''
            if a.attribution and kind!='detached':
                try:item['attribution']=read_attribution((out/'frame-trace.log').read_text())
                except (ValueError,OSError) as error:item['attribution_error']=str(error)
            item['receipts']=[struct.unpack('<4I2Q',bytes.fromhex(x)) for x in re.findall(r'PROCESS_REAP_OK v1=([0-9A-Fa-f]{64})',serial)]
            item['elapsed']=round(time.monotonic()-begin,3);summary['cases'].append(item)
            print('BLOCK_COST_DIAGNOSTIC',kind,item,flush=True)
        if hashes()!=summary['hashes']:raise ValueError('diagnostic input drift')
        return 1 if any('capture_error' in x or 'attribution_error' in x for x in summary['cases']) else 0
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('BLOCK_COST_EVIDENCE',folder)

if __name__=='__main__':raise SystemExit(main())
