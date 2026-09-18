"""One device-free service image; bounded real CPU samples and full pool proofs."""
from pathlib import Path
import argparse,ast,hashlib,inspect,json,re,struct,time,uuid
import run_qemu_x86_64_task_pool as pool
helpers=pool.helpers;wide=pool.wide;transport=pool.transport;ROOT=pool.ROOT;SIZE=pool.SIZE
CASES=tuple((case,8192 if case==1 else 4096) for case in range(12))
FATAL_CASES=('window-slot7','generation-slot7')
CPU_KINDS={'cpu_start','cpu_charge','cpu_final'}
CPU_FILE='cpu-ledger-v1.bin'


def cpu_pack(sequence,event):
    kinds=('cpu_start','cpu_charge','cpu_final');kind=event.get('kind')
    if kind not in kinds:raise ValueError('CPU ledger kind')
    charge=kind=='cpu_charge'
    keys={'kind','slot','gen','now'}|({'before','after','result'} if charge else {'records'})
    if set(event)!=keys:raise ValueError('CPU ledger fields')
    for value,low,high in ((sequence,1,2085),(event['slot'],0,8),(event['gen'],1,1<<31),(event['now'],0,1<<60)):
        if type(value) is not int or not low<=value<high:raise ValueError('CPU ledger integer')
    words=[]
    for key in (('before','after') if charge else ('records',)):
        values=event[key]
        if type(values) is not list or len(values)!=8 or any(type(n) is not int or not 0<=n<1<<64 for n in values):
            raise ValueError('CPU ledger words')
        words+=values
    result=event['result'] if charge else 0
    if charge and (type(result) is not int or result not in (1,2)):raise ValueError('CPU ledger result')
    if not charge:words += [0]*8
    return struct.pack('<4I3Q16Q',1,kinds.index(kind),sequence,event['slot'],event['gen'],event['now'],result,*words)


class CPULedger:
    """One exclusive buffered stream; no lossy summaries or guest writes."""
    def __init__(self,path,emit):
        self.stream=path.open('xb');self.emit=emit;self.sha=hashlib.sha256()
        self.count=0;self.charges=0;self.lifecycle=0;self.closed=False

    def event(self,**event):
        if self.closed:raise ValueError('CPU ledger closed')
        raw=cpu_pack(self.count+1,event);charge=event['kind']=='cpu_charge'
        if self.charges+charge>2048 or self.lifecycle+(not charge)>36:raise ValueError('CPU ledger capacity')
        if self.stream.write(raw)!=168:raise ValueError('CPU ledger short write')
        self.sha.update(raw);self.count+=1;self.charges+=charge;self.lifecycle+=not charge
        self.emit('CPU1 '+str(self.count)+'\n')

    def finish(self):
        if self.closed or not self.count:raise ValueError('CPU ledger closure')
        self.stream.close();self.closed=True
        self.emit('CPU1_END '+str(self.count)+' '+self.sha.hexdigest()+'\n')


def expand_cpu_trace(trace,raw):
    """Decode private LE records in their original event order, fail closed."""
    if len(trace.encode())>65536 or not 0<len(raw)<=2084*168 or len(raw)%168:
        raise ValueError('CPU ledger/text capacity')
    count=len(raw)//168;sequence=0;closed=False;out=[];charges=0;lifecycle=0
    for line in trace.splitlines(keepends=True):
        if line.startswith('CPU'):
            if closed:raise ValueError('CPU ledger after closure')
            marker=re.fullmatch(r'CPU1 ([1-9][0-9]*)\r?\n',line)
            footer=re.fullmatch(r'CPU1_END ([1-9][0-9]*) ([0-9a-f]{64})\r?\n',line)
            if footer:
                if int(footer[1])!=count or sequence!=count or footer[2]!=hashlib.sha256(raw).hexdigest():
                    raise ValueError('CPU ledger final binding')
                closed=True;continue
            if not marker or int(marker[1])!=sequence+1 or sequence>=count:raise ValueError('CPU ledger order')
            row=raw[sequence*168:(sequence+1)*168];values=struct.unpack('<4I3Q16Q',row)
            version,kind,number,slot,gen,now,result,*words=values
            if version!=1 or kind not in (0,1,2):raise ValueError('CPU ledger version/kind')
            event=dict(kind=('cpu_start','cpu_charge','cpu_final')[kind],slot=slot,gen=gen,now=now)
            event.update(dict(before=words[:8],after=words[8:],result=result) if kind==1 else dict(records=words[:8]))
            if number!=sequence+1 or cpu_pack(number,event)!=row:raise ValueError('CPU ledger encoding')
            charges+=kind==1;lifecycle+=kind!=1
            if charges>2048 or lifecycle>36:raise ValueError('CPU ledger capacity')
            out.append('TASK_POOL '+json.dumps(event,sort_keys=True)+'\n');sequence+=1
        else:
            if line.startswith('TASK_POOL '):
                event=json.loads(line[10:])
                if event.get('kind') in CPU_KINDS:raise ValueError('CPU mixed unbound records')
                if event.get('kind')=='finish' and event.get('run')==2 and not closed:raise ValueError('CPU ledger unfinished')
            out.append(line)
    if not closed:raise ValueError('CPU ledger missing closure')
    return ''.join(out)


def validate_capture(serial,trace,case,oom,count,child_sha,folder):
    if (folder/'release-failure.json').exists() or (folder/'release-failure.json').is_symlink():raise ValueError('CPU release guard failure evidence')
    path=folder/CPU_FILE
    if path.is_symlink() or not 0<path.stat().st_size<=2084*168:raise ValueError('CPU ledger file')
    return validate(serial,expand_cpu_trace(trace,path.read_bytes()),case,oom,count,child_sha)


def binary_capacity(folder):
    reads=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
    failure=folder/'release-failure.json';extra=int(failure.exists())
    if failure.is_symlink() or extra and not 0<failure.stat().st_size<=1024:raise ValueError('CPU release failure record capacity')
    if not 0<len(reads) or len(reads)+1+extra>2048 or sum(r['bytes'] for r in reads)+(folder/CPU_FILE).stat().st_size+(failure.stat().st_size if extra else 0)>128*1024*1024:
        raise ValueError('CPU aggregate binary evidence capacity')
    return reads


def witness_hooks_needed(starts,proofs):
    """Only unpublished proofs need syscall stops; identity is the generation."""
    return any(entry['live'] and entry['slot']>=2 and gen not in proofs for gen,entry in starts.items())


class StopDispatcher:
    """GDB stop decisions collect only; command lists run complete callbacks.

    GDB calls every matching stop method before executing breakpoint commands.
    The first command drains every occurrence in that order, then continues.
    No counter repair, identity filtering or deduplication is performed.
    """
    def __init__(self,namespace):
        self.namespace=namespace;self.pending=[];self.running=False;self.failed=False;self.batches=0

    def bind(self,hook,retire=False):
        hook.service_retire=retire;hook.silent=True
        # One-line "python EXPR" is not a block. An extra "end" makes GDB
        # discard the following continue and silently end a batch capture.
        hook.commands='silent\npython service_stops.drain()\ncontinue'

    def collect(self,hook):
        # Do not call any GDB state-changing operation from Breakpoint.stop,
        # including on the error path. The command fails after the decision.
        if self.running or self.failed or len(self.pending)>=32:self.failed=True
        else:self.pending.append(hook)
        return True

    def drain(self):
        if self.running or self.failed or not self.pending or self.batches>=8192:
            self.failed=True;raise ValueError('OBSERVER_FAIL invalid service dispatch')
        pending=self.pending;self.pending=[];self.running=True;self.batches+=1
        try:
            for hook in pending:
                if not hook.is_valid():raise ValueError('OBSERVER_FAIL invalid service breakpoint')
                # configure() installs the final reader after observer setup.
                # Its connection must cover the actual callback, not collection.
                reader=self.namespace.get('binary_reader');action=type(hook).observe
                if reader is not None:action=reader.wrap_stop(action)
                try:
                    if action(hook) is not False:raise ValueError('OBSERVER_FAIL service callback result')
                    if self.failed or self.pending:raise ValueError('OBSERVER_FAIL reentrant service dispatch')
                finally:
                    if hook.service_retire and hook.is_valid():hook.delete()
        except BaseException:
            self.failed=True;raise
        finally:self.running=False


class ReadOnlyCPUStops:
    """Static probes read/record in stop; command context alone handles failure."""
    def __init__(self,namespace):
        self.namespace=namespace;self.running=False;self.failed=None

    def bind(self,hook):
        hook.silent=True;hook.commands='silent\npython cpu_stops.fail()'

    def stop(self,hook):
        try:
            assert not self.running and self.failed is None,'CPU nested/failed decision'
            dispatch=self.namespace['service_stops']
            assert not dispatch.pending and not dispatch.running and not dispatch.failed,'CPU mixed dispatch'
            reader=self.namespace.get('binary_reader')
            assert reader is None or not reader.in_stop and reader.client is None and not reader.failed,'CPU reader scope'
            cache=self.namespace.get('stop_reads')
            assert cache is None or not cache.inside and not cache.active,'CPU cache scope'
            self.namespace['callbacks']+=1
            assert self.namespace['callbacks']<=8192,'CPU callback capacity'
            self.running=True
            hook.fn()
            return False
        except BaseException as error:
            if self.failed is None:self.failed=(type(error).__name__+': '+str(error))[:512]
            return True
        finally:self.running=False

    def fail(self):
        # Preinstalled commands run after every GDB stop decision. Diagnostic
        # I/O failure must not suppress the nonzero exit or resume the target.
        try:self.namespace['emit']('OBSERVER_FAIL',where='static CPU probe',error=self.failed)
        finally:self.namespace['gdb'].execute('quit 71')


def defer_observer_callbacks(code,classes):
    """Preserve callback bodies; version only their GDB invocation boundary."""
    import ast
    tree=ast.parse(code);replacements=[]
    for name in classes:
        nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name]
        if len(nodes)!=1:raise ValueError('service dispatcher class identity')
        node=nodes[0];original=ast.get_source_segment(code,node);changed=original
        init=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        constructor=ast.get_source_segment(code,init)
        # Dynamic return hooks stay valid until their original callback has
        # run. Delete them explicitly in drain(), not during GDB stop analysis.
        revised=constructor.replace('temporary=True','temporary=False') if name=='ReleaseEnd' else constructor
        if init.lineno==init.end_lineno:
            declaration,suite=revised.split(':',1)
            revised=declaration+':\n        '+suite
        revised+='\n        service_stops.bind(self,'+repr(name=='ReleaseEnd')+')'
        changed=helpers.once(changed,constructor,revised)
        changed=helpers.once(changed,'    def stop(self):','    def observe(self):')
        changed+='\n    def stop(self):return service_stops.collect(self)'
        replacements.append((original,changed))
    for before,after in replacements:code=helpers.once(code,before,after)
    for name in classes:
        old=name+'.stop=stop_reads.wrap_stop('+name+'.stop)'
        if old in code:code=helpers.once(code,old,name+'.observe=stop_reads.wrap_stop('+name+'.observe)')
    prefix=inspect.getsource(StopDispatcher)+'\nservice_stops=StopDispatcher(globals())\n'
    result=prefix+code
    compile(result,'<deferred service callbacks>','exec')
    return result


def release_guard(release,reg,path):
    """Host-only failure context; preserve short circuit and perform no healthy I/O."""
    nested=release is not None
    flags=None if nested else reg('eflags')
    if not nested and not flags&512:return
    if flags is not None and (type(flags) is not int or not 0<=flags<1<<64):raise ValueError('release guard flags range')
    active={key:release.get(key) for key in ('slot','gen','ret')} if type(release) is dict else None
    if active is not None and any(value is not None and (type(value) is not int or not 0<=value<1<<64) for value in active.values()):
        raise ValueError('release guard context range')
    row=dict(version=1,nested=nested,eflags=flags,active=active)
    raw=json.dumps(row,sort_keys=True,separators=(',',':'))+'\n'
    if len(raw.encode('ascii'))>1024:raise ValueError('release guard record capacity')
    with path.open('x',encoding='ascii') as out:
        if out.write(raw)!=len(raw):raise OSError('release guard short write')
        out.flush()
    assert not nested and not flags&512


class SameStopReads:
    """Bounded read-through spans, only during audited read-only all-stop hooks."""
    def __init__(self,namespace):
        self.namespace=namespace;self.original=None;self.inside=False;self.active=False
        self.entries=[];self.used=0

    def read(self,address,size):
        if not self.active:return self.original(address,size)
        if type(address) is not int or type(size) is not int or size<0:
            raise ValueError('same-stop read range')
        for start,raw in self.entries:
            offset=address-start
            if 0<=offset and offset+size<=len(raw):return raw[offset:offset+size]
        raw=self.original(address,size)
        if len(raw)!=size:raise ValueError('same-stop read length')
        if size and len(self.entries)<256 and self.used+size<=1024*1024:
            self.entries.append((address,bytes(raw)));self.used+=size
        return raw

    def before_write(self):
        if not self.inside:raise ValueError('same-stop write outside callback')
        self.entries.clear();self.used=0;self.active=False

    def wrap_stop(self,original):
        def stop(hook):
            if self.inside:raise ValueError('same-stop nested callback')
            # qemu_binary_memory.configure installs the final reader after the
            # observer. Bind it lazily, retaining its original equivalence reads
            # and its outer connection/cleanup scope, without recursive wrapping.
            if self.original is None:
                self.original=self.namespace['mem'];self.namespace['mem']=self.read
            elif self.namespace['mem']!=self.read:raise ValueError('same-stop reader replaced')
            name=hook.fn.__name__ if hasattr(hook,'fn') else type(hook).__name__
            # start is read-only up to its explicit before_write barrier. No
            # cache is used during or after root-mode injection in that stop.
            self.inside=True;self.active=name in ('boot','start','receipt_capacity','syscall','copy','release_begin','ReleaseEnd')
            try:return original(hook)
            finally:
                self.entries.clear();self.used=0;self.active=False;self.inside=False
        return stop


def decode_child_record(packed,sha,python=None):
    """RFC1950 host-only transfer; exact RNPG bytes, no unbounded expansion."""
    import hashlib
    if type(packed) is not bytes or not 0<len(packed)<=266336:
        raise ValueError('CPU config compressed size')
    try:import zlib
    except ModuleNotFoundError as error:
        if error.name!='zlib' or python is None:raise
        # The pinned WinLibs GDB lacks zlib. Use the already hash-bound host
        # interpreter once, isolated and without a shell, within the same guest
        # deadline. This fixed worker can emit at most266336 bytes, never code
        # from CONFIG, imports from the worktree, or guest memory accesses.
        import subprocess
        worker=("import sys,zlib\np=sys.stdin.buffer.read(266337)\n"
            "assert 0<len(p)<=266336\nd=zlib.decompressobj();r=d.decompress(p,266337)\n"
            "assert len(r)==266336 and d.eof and not d.unused_data and not d.unconsumed_tail\n"
            "sys.stdout.buffer.write(r)\n")
        result=subprocess.run([python,'-I','-S','-c',worker],input=packed,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=2,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise ValueError('CPU config decoder failed')
        raw=result.stdout
    else:
        decoder=zlib.decompressobj();raw=decoder.decompress(packed,266337)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('CPU config exact stream')
    if len(raw)!=266336 or hashlib.sha256(raw).hexdigest()!=sha:
        raise ValueError('CPU config exact record')
    return raw


def read_user_spans(t,va,n,mem):
    """Bounded FILE_USER_READ adapter; retain every walk and exact-span check."""
    DM=0xffff800000000000;MASK=0x3fffff000
    assert type(n)==int and 0<=n<=270336 and type(va)==int and 0<=va<1<<64 and n<=(1<<64)-va
    pages={};ranges=[];fragments=0
    def entry(address,shift):
        base=address&~4095
        index=(address-base)//8
        if base not in pages:
            assert len(pages)<8
            count=min(512-index,((va+n-1)>>shift)-(va>>shift)+1)
            assert 1<=count<=512
            raw=mem(address,count*8);assert len(raw)==count*8
            pages[base]=(index,raw)
        first,raw=pages[base];offset=(index-first)*8
        assert 0<=offset<=len(raw)-8
        return struct.unpack_from('<Q',raw,offset)[0]
    while n:
        fragments+=1;assert fragments<=67
        root=t[2]
        for shift in (39,30,21):
            e=entry(DM+root+((va>>shift)&511)*8,shift)
            assert e&1 and not e&128
            root=e&MASK
        e=entry(DM+root+((va>>12)&511)*8,12);assert e&5==5
        count=min(n,4096-(va&4095));address=DM+(e&MASK)+(va&4095)
        if ranges and ranges[-1][0]+ranges[-1][1]==address:ranges[-1][1]+=count
        else:ranges.append([address,count])
        va+=count;n-=count
    out=bytearray()
    for address,size in ranges:
        raw=mem(address,size)
        if len(raw)!=size:raise ValueError('user payload length')
        out+=raw
    return bytes(out)


def cpu_snapshot_layout(symbols):
    """Immutable symbol offsets only; no guest bytes survive a callback."""
    names=('scheduler_cpu_budgets','scheduler_cpu_windows','scheduler_mode','scheduler_last_tick')
    sizes=(256,256,1,8)
    assert all(type(symbols[n]) is int and 0<=symbols[n]<=(1<<64)-size for n,size in zip(names,sizes))
    base=min(symbols[n] for n in names)
    end=max(symbols[n]+size for n,size in zip(names,sizes))
    assert 0<end-base<=1024
    for i in range(4):
        for j in range(i):assert symbols[names[i]]>=symbols[names[j]]+sizes[j] or symbols[names[j]]>=symbols[names[i]]+sizes[i]
    return (base,end-base,*(symbols[n]-base for n in names))


def observer_body():
    code=pool.observer_body()
    # FILE_USER_READ already coalesces physical spans. Keep its table batching,
    # permission checks and order; add explicit fragment and payload bounds.
    code=helpers.replace_function(code,'user',
        "def user(t,va,n):\n    return read_user_spans(t,va,n,mem)")
    code+='\n'+inspect.getsource(read_user_spans)
    # Pool EXTRA installs the sole allocator-return adapter after all hook
    # construction. Do not retain a second, shadowed mutation implementation.
    allocations=[node for node in ast.parse(code).body if isinstance(node,ast.FunctionDef) and node.name=='allocation']
    if len(allocations)!=2:raise ValueError('service CPU exact inherited allocator definitions')
    code=helpers.once(code,ast.get_source_segment(code,allocations[0]),
        "def allocation():\n    raise AssertionError('allocator adapter not installed')")
    # These are exact, fail-closed adaptations of the accepted pool observer.
    # Full per-generation memory/page/FP/IPC witnesses remain unchanged.
    code=helpers.once(code,'callbacks<=4096','callbacks<=8192')
    code=helpers.once(code,'slot=d(S[\'scheduler_current_slot\']);t=task(slot);gen=t[1]\n    if gen in starts:return',
        "slot=d(S['scheduler_current_slot']);assert slot<8\n"
        "    gen=q(S['scheduler_tasks']+slot*1024+8)\n    if gen in starts:return\n    t=task(slot)")
    code=helpers.once(code,'==(4,272,8,0)','==(5,336,8,0)')
    code=helpers.once(code,"expected=CASE if role==0 and index==0 and CASE in (2,3) else 0",
        "expected=({2:2,3:3,10:4,11:5}.get(CASE,0) if role==0 and index==0 else 0)")
    code=helpers.once(code,"('process_run_plan',272)","('process_run_plan',336),('scheduler_cpu_windows',256)")
    code=helpers.once(code,"Hook('process_run_syscall64',syscall)",
        "witness_hooks=(Hook('process_ipc_syscall64',syscall),Hook('process_run_syscall64.sleep',syscall))")
    code=helpers.once(code,"Hook('process_run_syscall64',receipt_capacity)",
        "capacity_owner=None\ncapacity_hooks=[]\nif CASE==6:\n"
        "    capacity_hooks=[Hook('family_syscall64',receipt_capacity),Hook('process_ipc_syscall64',receipt_capacity)]\n"
        "    for hook in capacity_hooks:hook.enabled=False")
    code=helpers.once(code,'    key=(root[1],w[3])',
        "    assert root[1]==capacity_owner,'capacity generation'\n    key=(root[1],w[3])")
    code=helpers.once(code,"    records=[struct.unpack('<8Q',mem(S['family_records']+slot*64,64)) for slot in range(2,8)]",
        "    packed=mem(S['family_records']+128,384);assert len(packed)==384\n"
        "    records=[struct.unpack_from('<8Q',packed,offset) for offset in range(0,384,64)]")
    code=helpers.once(code,"    capacity_seen.add(key);emit('capacity',gen=root[1],phase=w[3],occupied=6,receipt=int(w[3]==4))",
        "    if w[3]==4:assert (root[1],3) in capacity_seen,'capacity phase order'\n"
        "    capacity_seen.add(key);emit('capacity',gen=root[1],phase=w[3],occupied=6,receipt=int(w[3]==4))\n"
        "    if w[3]==4:capacity_complete()")
    code+='''
def capacity_arm(gen):
    global capacity_owner
    assert CASE==6 and type(gen) is int and 0<gen<1<<31
    assert capacity_owner is None or gen>capacity_owner and {(capacity_owner,3),(capacity_owner,4)}<=capacity_seen
    assert len(capacity_seen) in (0,2) and (gen,3) not in capacity_seen and (gen,4) not in capacity_seen
    capacity_owner=gen
    for hook in capacity_hooks:hook.enabled=True

def capacity_complete():
    assert capacity_owner is not None and {(capacity_owner,3),(capacity_owner,4)}<=capacity_seen
    for hook in capacity_hooks:hook.enabled=False
'''
    original=pool.SYSCALL.strip()
    code=helpers.once(code,original,original+
        "\n    if not witness_hooks_needed(starts,proofs):\n        for hook in witness_hooks:hook.enabled=False")
    code=helpers.once(code,"Hook('scheduler_enter_task64.state_published',start)",
        "start_hook=Hook('scheduler_enter_task64.state_published',start)")
    code=helpers.once(code,"        created_sources[gen]=source_pointer",
        "        created_sources[gen]=source_pointer\n        start_hook.enabled=True\n        for hook in witness_hooks:hook.enabled=True")
    code=helpers.once(code,"    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512",
        "    start_hook.enabled=True\n    for hook in witness_hooks:hook.enabled=True\n    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512")
    code=helpers.once(code,"    if slot<2:\n        address=CONFIG['root_data'][slot]",
        "    cpu_start(slot,gen)\n    if slot>=2:\n        for hook in witness_hooks:hook.enabled=True\n"
        "    if slot==0 and CASE==6:capacity_arm(gen)\n    if slot<2:\n        address=CONFIG['root_data'][slot]")
    code=helpers.once(code,"        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))",
        "        stop_reads.before_write()\n        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))")
    code=helpers.once(code,"    if slot>=2:assert gen in proofs,'child witness before fence'",
        "    if slot>=2:assert gen in proofs,'child witness before fence'\n    cpu_final(slot,gen)")
    code=helpers.once(code,"    emit('finish',run=runs,free=free()",
        "    if runs==2:cpu_ledger.finish()\n    emit('finish',run=runs,free=free()")
    code=helpers.once(code,"    assert release is None and not reg('eflags')&512\n",
        "    release_guard(release,reg,release_failure_path)\n")
    body=code+'\nfrom pathlib import Path\n'+inspect.getsource(release_guard)+\
        "\nrelease_failure_path=Path(CONFIG['cpu_ledger']).with_name('release-failure.json')\n"+\
        inspect.getsource(witness_hooks_needed)+'\n'+inspect.getsource(cpu_pack)+'\n'+inspect.getsource(CPULedger)+\
        "\ncpu_ledger=CPULedger(Path(CONFIG['cpu_ledger']),gdb.write)\n"+inspect.getsource(cpu_snapshot_layout)+inspect.getsource(ReadOnlyCPUStops)+CPU_OBSERVER+'\n'+inspect.getsource(SameStopReads)+\
        "\nstop_reads=SameStopReads(globals())\nHook.stop=stop_reads.wrap_stop(Hook.stop)\nReleaseEnd.stop=stop_reads.wrap_stop(ReleaseEnd.stop)\n"
    return defer_observer_callbacks(body,('Hook','ReleaseEnd'))


CPU_OBSERVER=r'''
cpu_pending=None;cpu_charges=0
CPU_LAYOUT=cpu_snapshot_layout(S)
def cpu_snapshot(slot):
    assert type(slot) is int and 0<=slot<8
    base,size,budget,window,mode_offset,tick=CPU_LAYOUT
    raw=mem(base,size);assert len(raw)==size
    records=[]
    for offset in (budget,window):records+=struct.unpack_from('<4Q',raw,offset+slot*32)
    return raw[mode_offset],struct.unpack_from('<Q',raw,tick)[0],records
def cpu_start(slot,gen):
    current,now,records=cpu_snapshot(slot);assert current==8
    cpu_ledger.event(kind='cpu_start',slot=slot,gen=gen,now=now,records=records)
    # Each published generation keeps the full first-entry proof. Already
    # proven resumes do not need a debugger stop on every monotonic syscall.
    raw=mem(S['scheduler_tasks'],7184);assert len(raw)==7184
    pending=[struct.unpack_from('<2Q',raw,n*1024) for n in range(8)]
    start_hook.enabled=any(state in (1,2,6) and generation not in starts for state,generation in pending)
def cpu_final(slot,gen):
    assert cpu_pending is None
    current,now,records=cpu_snapshot(slot);assert current==8
    cpu_ledger.event(kind='cpu_final',slot=slot,gen=gen,now=now,records=records)
def cpu_charge():
    global cpu_pending,cpu_charges
    offset=reg('rdi')-S['scheduler_cpu_budgets'];assert 0<=offset<256 and not offset&31
    slot=offset//32;current,now,records=cpu_snapshot(slot)
    if current!=8:return
    gen=q(S['scheduler_tasks']+slot*1024+8)
    assert gen in starts and starts[gen]['live'] and starts[gen]['slot']==slot
    assert cpu_pending is None and not reg('eflags')&512
    cpu_charges+=1;assert cpu_charges<=2048
    cpu_pending=dict(slot=slot,gen=gen,now=now,before=records)
def cpu_return():
    global cpu_pending
    offset=reg('rdi')-S['scheduler_cpu_budgets'];assert 0<=offset<256 and not offset&31
    slot=offset//32;current,now,records=cpu_snapshot(slot)
    if current!=8:
        assert cpu_pending is None
        return
    assert cpu_pending is not None and not reg('eflags')&512
    event=cpu_pending
    assert slot==event['slot'] and now==event['now']
    cpu_ledger.event(kind='cpu_charge',**event,result=reg('rax'),after=records)
    cpu_pending=None

cpu_stops=ReadOnlyCPUStops(globals())
class CPUHook(gdb.Breakpoint):
    def __init__(self,address,fn):
        super().__init__('*'+hex(S[address]),internal=True);self.fn=fn
        cpu_stops.bind(self)
    def stop(self):return cpu_stops.stop(self)

cpu_addresses=[S[core+suffix] for core in ('reist_x64_period_apply','reist_x64_budget_apply')
               for suffix in ('.charge','.charge_result')]
assert len(set(cpu_addresses))==4
# Existing static hooks must not share these PCs. Dynamic ReleaseEnd hooks
# target allocator return PCs, never either accounting core.
assert all(location.address not in cpu_addresses for hook in (gdb.breakpoints() or ()) for location in hook.locations)
for core in ('reist_x64_period_apply','reist_x64_budget_apply'):
    CPUHook(core+'.charge',cpu_charge)
    CPUHook(core+'.charge_result',cpu_return)
'''


def observer(config,folder,case,oom):
    import sys,zlib
    settings=dict(config,case=case,oom=oom,cpu_ledger=(folder/CPU_FILE).as_posix())
    record=settings.pop('child_record');packed=zlib.compress(record,9);sha=hashlib.sha256(record).hexdigest()
    if decode_child_record(packed,sha)!=record:raise ValueError('CPU config encoding')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+
        '\n'+inspect.getsource(decode_child_record)+"\nCONFIG['child_record']=decode_child_record(bytes.fromhex("+repr(packed.hex())+'),'+repr(sha)+','+repr(sys.executable)+')\n'+
        '\n'+observer_body()+'\nend\ncontinue\n')


def pool_validator():
    """Retain every old lifecycle predicate; explicitly version only CPU/cases.

    No receipt values are rewritten. This adapter must fail if its input source
    changes: exact single replacements, with raw CPU proof checked separately.
    """
    code=inspect.getsource(pool._validate)
    changes=[('range(10)','range(12)'),('(case>=7)','(7<=case<=9)'),
        ("'rollback','capacity'}","'rollback','capacity'}|CPU_KINDS"),
        ('case in (2,3,4)','case in (2,3,4,10)'),
        ('{2:134,3:256,4:0}','{2:134,3:256,4:0,10:256}'),
        (' or ticks>32 or bad and case==3 and ticks!=32','')]
    for old,new in changes:code=helpers.once(code,old,new)
    env=dict(vars(pool),CPU_KINDS=CPU_KINDS)
    exec(compile(code,'<service-pool-lifecycle>','exec'),env)
    return env['_validate']


def charge_result(before,now):
    """Independent integer reference, never used to charge or modify the guest."""
    if not isinstance(before,list) or len(before)!=8 or any(type(n) is not int or not 0<=n<1<<64 for n in before):
        raise ValueError('CPU record shape')
    gen,limit,total,last,period,origin,index,used=before
    if not 0<gen<1<<31 or not 1<=limit<=32 or type(now) is not int or not 0<now<1<<60 or not last<now:
        raise ValueError('CPU generation/quota/clock')
    if period==0:
        if any(before[4:]) or not 0<=total<limit or (last<total if total else last!=0):raise ValueError('legacy CPU records')
        return [gen,limit,total+1,now,0,0,0,0],2 if total+1==limit else 1
    if period!=100 or not 0<=origin<now or not 0<=used<limit:raise ValueError('CPU immutable window')
    if total:
        if not origin<last or total>last-origin or index!=(last-origin)//100 or not 1<=used<=min(total,(last-origin)%100+1) or total>(index+1)*limit:
            raise ValueError('CPU window counters')
    elif last or index or used:raise ValueError('CPU empty counters')
    next_index=(now-origin)//100
    if next_index<index:raise ValueError('CPU backward window')
    next_used=used+1 if next_index==index else 1
    return [gen,limit,total+1,now,period,origin,next_index,next_used],2 if next_used==limit else 1


def validate_cpu(serial,events,case):
    bygen={e['gen']:e for e in events if e['kind']=='start'}
    receipts={}
    for m in wide.process.REAP.finditer(serial):
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]));receipts[gen]=(slot,status,state,ticks)
    previous={};positions={};charges={g:[] for g in bygen};final=set();last_tick={}
    for position,e in enumerate(events):
        kind=e['kind']
        if kind not in CPU_KINDS:continue
        gen=e['gen'];entry=bygen[gen];slot=entry['slot'];now=e['now']
        if e['slot']!=slot or type(now) is not int or not 0<=now<1<<60:raise ValueError('CPU owner/time')
        for name in (('before','after') if kind=='cpu_charge' else ('records',)):
            values=e[name]
            if not isinstance(values,list) or len(values)!=8 or any(type(n) is not int or not 0<=n<1<<64 for n in values):raise ValueError('CPU exact record encoding')
        per=9 if case==6 else 8;run=(gen-1)//per
        if kind=='cpu_start':
            if gen in previous:raise ValueError('CPU duplicate bind')
            b=e['records'];legacy=case==10 and entry['role']==0 and entry['index']==0
            period=0 if legacy else 100
            if len(b)!=8 or any(type(n) is not int for n in b) or b[:4]!=[gen,32,0,0] or b[4]!=period or b[6:]!=[0,0] or not 0<=b[5]<=now or legacy and b[5]!=0:
                raise ValueError('CPU initial binding')
            if not next(i for i,r in enumerate(events) if r['kind']=='start' and r.get('gen')==gen)<position:raise ValueError('CPU start order')
            previous[gen]=b;positions[gen]=position
        elif kind=='cpu_charge':
            if gen in final or e['before']!=previous[gen] or now<=last_tick.get(run,-1):raise ValueError('CPU charge continuity')
            after,result=charge_result(e['before'],now)
            if e['after']!=after or type(e['result']) is not int or e['result']!=result:raise ValueError('CPU actual charge')
            previous[gen]=after;charges[gen].append(now);last_tick[run]=now
        else:
            if gen in final or e['records']!=previous[gen] or now<previous[gen][3] or position<=positions[gen]:raise ValueError('CPU retirement continuity')
            if not position<next(i for i,r in enumerate(events) if r['kind']=='release' and r.get('gen')==gen):raise ValueError('CPU premature clear')
            b=e['records'];slot,status,state,total=receipts[gen]
            if b[2]!=total or total!=len(charges[gen]):raise ValueError('CPU lifetime receipt')
            if state==4 and (total<40 or b[4]!=100 or b[6]<1 or not b[7]<b[1]):raise ValueError('CPU healthy lifetime')
            if status==256:
                if case==10:
                    if b[4]!=0 or total!=32 or charges[gen][-1]-charges[gen][0]<100:raise ValueError('CPU legacy lifetime exhaustion')
                elif case!=3 or b[4]!=100 or b[7]!=32:raise ValueError('CPU periodic exhaustion')
            if case==11 and entry['role']==0 and entry['index']==0 and max(b-a for a,b in zip(charges[gen],charges[gen][1:]))<200:
                raise ValueError('CPU idle skipped window')
            final.add(gen)
    if final!=set(bygen) or sum(map(len,charges.values()))>2048:raise ValueError('CPU complete ledger')


def validate(serial,trace,case,oom,count,child_sha):
    try:
        rows=pool_validator()(serial,trace,case,oom,count,child_sha)
        events=[json.loads(line[10:]) for line in trace.splitlines() if line.startswith('TASK_POOL ')]
        validate_cpu(serial,events,case)
        return rows
    except (KeyError,TypeError,StopIteration,struct.error,IndexError) as error:
        raise ValueError('malformed service CPU evidence: '+str(error)) from error


FATAL_RANGES=(('scheduler_tasks',8192),('scheduler_cpu_budgets',256),('scheduler_cpu_windows',256),
    ('process_run_plan',336),('family_records',512),('family_profiles',256),
    ('family_extended_masks',128),('process_ipc_completions',192),('process_run_generations',32))


def fatal_mutation(kind,saved):
    if kind not in FATAL_CASES or len(saved)!=len(FATAL_RANGES) or tuple(map(len,saved))!=tuple(n for _,n in FATAL_RANGES):
        raise ValueError('CPU fatal shape')
    state,gen=struct.unpack_from('<2Q',saved[0],7*1024)
    b=list(struct.unpack_from('<4Q',saved[1],7*32))+list(struct.unpack_from('<4Q',saved[2],7*32))
    if state not in (1,2,6) or not 0<gen<1<<31 or b[0]!=gen or b[1]!=32 or b[4]!=100 or not b[5]<1<<60:
        raise ValueError('CPU fatal last-slot binding')
    if struct.unpack_from('<4I',saved[3])!=(5,336,8,0) or struct.unpack_from('<Q',saved[3],272+7*8)[0]!=100:
        raise ValueError('CPU fatal plan')
    # Validate real pre-injection accounting via a read-only prospective sample.
    charge_result(b,max(b[3],b[5])+1)
    if struct.unpack_from('<Q',saved[4],7*64)[0]!=(gen<<32)|7 or struct.unpack_from('<I',saved[8],7*4)[0]!=gen:
        raise ValueError('CPU fatal family generation')
    index,offset,value=(2,7*32+24,33) if kind=='window-slot7' else (1,7*32,gen+1)
    raw=struct.pack('<Q',value);changed=list(saved)
    changed[index]=saved[index][:offset]+raw+saved[index][offset+8:]
    return changed,[(index,offset,raw)]


FATAL_BODY=r'''
from pathlib import Path
import gdb,struct,json,hashlib
S=CONFIG['s'];KIND=CONFIG['kind'];OUT=Path(CONFIG['out'])
RANGES=[(S[name],size) for name,size in FATAL_RANGES]
injected=False;diagnosed=False;saved=None;callbacks=0
inferior=gdb.selected_inferior()
def reg(name):return int(gdb.parse_and_eval('$'+name))&0xffffffffffffffff
def mem(address,size):return bytes(inferior.read_memory(address,size))
def q(address):return struct.unpack('<Q',mem(address,8))[0]
def state():return [mem(a,n) for a,n in RANGES]
def event(kind,**values):gdb.write('SERVICE_CPU_FATAL '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\n')
def snapshot(name,values):
    raw=b''.join(values)
    with (OUT/(name+'.bin')).open('xb') as stream:stream.write(raw)
    return hashlib.sha256(raw).hexdigest()
class Probe(gdb.Breakpoint):
    def __init__(self,name,label,enabled=True):
        super().__init__('*'+hex(S[name]),internal=True);self.label=label;self.enabled=enabled
    def stop(self):
        global injected,diagnosed,saved,callbacks
        try:
            callbacks+=1;assert callbacks<=2048
            if self.label=='arm':
                if mem(S['scheduler_mode'],1)==b'\x08' and 0<reg('rax')<1<<63 and reg('rax')&0xffffffff==7:
                    trigger.enabled=True;self.enabled=False
            elif self.label=='trigger':
                if mem(S['scheduler_mode'],1)!=b'\x08' or reg('rdi')!=S['scheduler_cpu_budgets']+7*32:return False
                assert not injected and not reg('eflags')&512 and reg('rdx')==0
                before=state();changed,writes=fatal_mutation(KIND,before)
                original=snapshot('before',before);assert len(writes)==1 and len(writes[0][2])==8
                for index,offset,raw in writes:inferior.write_memory(RANGES[index][0]+offset,raw)
                assert state()==changed
                saved=changed;injected=True;self.enabled=False
                for hook in forbidden:hook.enabled=True
                event('inject',case=KIND,original=original,sha=snapshot('damaged',saved),writes=8)
            elif self.label=='diagnostic':
                if not injected:return False
                assert not diagnosed and state()==saved and not reg('eflags')&512
                diagnosed=True;event('diagnostic',sha=snapshot('diagnostic',state()),interrupts=0)
            elif self.label=='halt':
                assert injected and diagnosed and state()==saved and not reg('eflags')&512
                assert mem(S['halt64'],4)==b'\xfa\xf4\xeb\xfd'
                event('halt',sha=snapshot('halt',state()),cli_hlt=1)
                gdb.execute('detach');gdb.execute('quit 0')
            else:raise AssertionError('cleanup/resume after CPU corruption')
        except Exception as error:
            event('OBSERVER_FAIL',where=self.label,error=repr(error));gdb.execute('quit 71')
        return False
# Stop at the pure core entry BEFORE validation, not inside its admitted charge
# branch. Otherwise corrupting a just-validated word would bypass the proof.
trigger=Probe('reist_x64_period_apply','trigger',False)
Probe('family_create64.parent_result','arm')
Probe('scheduler_fail','diagnostic')
Probe('halt64','halt')
forbidden=[Probe(name,'forbidden',False) for name in ('process_run_resume64','family_terminal64',
    'scheduler_force_cleanup64','scheduler_release_task_frames64')]
'''


def fatal_observer(config,folder,kind):
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+
        repr(dict(s=config['s'],kind=kind,out=folder.as_posix()))+'\nFATAL_CASES='+repr(FATAL_CASES)+
        '\nFATAL_RANGES='+repr(FATAL_RANGES)+'\n'+inspect.getsource(charge_result)+'\n'+inspect.getsource(fatal_mutation)+
        defer_observer_callbacks(FATAL_BODY,('Probe',))+'\nend\ncontinue\n')


def validate_fatal(serial,trace,kind,folder):
    if kind not in FATAL_CASES or 'OBSERVER_FAIL' in trace:raise ValueError('CPU fatal observer')
    events=[json.loads(line[18:]) for line in trace.splitlines() if line.startswith('SERVICE_CPU_FATAL ')]
    if [e['kind'] for e in events]!=['inject','diagnostic','halt']:raise ValueError('CPU fatal exact path')
    marker='REIST_X86_64_PROCESS_SCHEDULER_STAGE_'
    if serial.count(marker)!=1 or not re.search(marker+'[0-9A-F]{2}\r?\n',serial) or 'pio=1' in serial or any(m in serial for m in (wide.process.DONE,wide.process.SUCCESS,'PROCESS_REAP_OK')):
        raise ValueError('CPU fatal serial')
    snapshots={};total=sum(n for _,n in FATAL_RANGES)
    for name in ('before','damaged','diagnostic','halt'):
        path=folder/(name+'.bin')
        if path.is_symlink() or path.stat().st_size!=total:raise ValueError('CPU fatal snapshot length')
        raw=path.read_bytes();offset=0;parts=[]
        for _,n in FATAL_RANGES:parts.append(raw[offset:offset+n]);offset+=n
        snapshots[name]=parts
    changed,writes=fatal_mutation(kind,snapshots['before'])
    if any(snapshots[n]!=changed for n in ('damaged','diagnostic','halt')):raise ValueError('CPU fatal metadata changed')
    digest=lambda name:hashlib.sha256(b''.join(snapshots[name])).hexdigest()
    if events!=[dict(kind='inject',case=kind,original=digest('before'),sha=digest('damaged'),writes=8),
        dict(kind='diagnostic',sha=digest('diagnostic'),interrupts=0),dict(kind='halt',sha=digest('halt'),cli_hlt=1)]:
        raise ValueError('CPU fatal snapshot binding')
    return len(writes)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--fatal',action='store_true')
    args=parser.parse_args();image=args.image.resolve();base=args.evidence.resolve()
    root=ROOT/'build/codex-agent/r83ap-service-cpu'
    if image!=(root/'workload-renewal/native/x86_64/reist-x86_64-bootstrap.elf').resolve() or base!=(root/('fatal-guests' if args.fatal else 'guests')).resolve():
        parser.error('service CPU evidence scope')
    import verify_x86_64_service_cpu as verify
    binding=verify.admit_runtime(image,args.fatal)
    verify.matrix_budget(binding['candidate'],args.fatal,starting=True)
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result=dict(passed=False,closed=False,candidate=binding['candidate'],image_sha256=pool.digest(image),fatal=args.fatal,cases=[])
    (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    begin=time.monotonic();spent=0
    try:
        config=pool.image_config(image);count=wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
        result.update(allocations=count,child_sha256=sha)
        for case,ram in (tuple((k,4096) for k in FATAL_CASES) if args.fatal else CASES):
            if pool.digest(image)!=result['image_sha256']:raise ValueError('service CPU image changed')
            oom={7:0,8:count//2,9:count-1}.get(case);out=folder/f'guest-{case}-{ram}';out.mkdir()
            row=dict(case=case,ram=ram,oom=oom,passed=False);result['cases'].append(row);started=time.monotonic()
            try:
                code=fatal_observer(config,out,case) if args.fatal else observer(config,out,case,oom)
                serial,trace=transport.capture(image,out,code,ram,halt_witness=args.fatal,
                    binary_memory=None if args.fatal else 'equivalence',diagnostic_metrics=True,service_cpu_budget=True)
                row['tasks']=validate_fatal(serial,trace,case,out) if args.fatal else len(validate_capture(serial,trace,case,oom,count,sha,out))
                if not args.fatal:binary_capacity(out)
                row['passed']=True
            finally:
                elapsed=time.monotonic()-started;spent+=elapsed;row['elapsed']=round(elapsed,6)
            if elapsed>30 or spent>(60 if args.fatal else 360):raise ValueError('service CPU frozen guest deadline')
            print(f'SERVICE_CPU_GUEST_OK case={case} ram={ram} elapsed={elapsed:.3f}',flush=True)
        result['passed']=True;return 0
    except (ValueError,RuntimeError,OSError,KeyError) as error:
        result['error']=str(error);print('SERVICE_CPU_FAIL '+str(error),flush=True);return 1
    finally:
        result.update(closed=True,elapsed=round(time.monotonic()-begin,6),guest_elapsed=round(spent,6))
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('SERVICE_CPU_EVIDENCE '+str(folder),flush=True)


if __name__=='__main__':raise SystemExit(main())
