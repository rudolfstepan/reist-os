"""Selected profile2 adaptation of the complete accepted shell/raw proof.

No mutation of the old module or shared transport. Each changed predicate names
the new finite local policy; CPU/device/IPC/identity/reap predicates stay exact.
"""
from pathlib import Path
import ast,hashlib,inspect,json,linecache,os,sys,time,types
import run_qemu_x86_64_shell_session as old
import build_x86_64_wide_file_media as media
ROOT=Path(__file__).resolve().parents[1]
DECODE_LIMIT=512*1024*1024
EVIDENCE_TOKENS=tuple(('"'+key+'": ').encode('ascii') for key in
    'kind slot gen run op entered before after result now size args authority family_before family profile_denied unused denied flags handle deadline mask value state reason'.split())+(
    b'SHELL_SESSION ',b'null',b'false',b'true',b', ',b'"call"',b'"return"',b'"cpu_charge"',b'"0x',b'"',b': ')
CASES=tuple((str(n),n,n,4096,False) for n in range(5))+(
    ('8g',5,2,8192,False),('full',3,3,4096,True),
    ('driver',7,2,4096,False),('fs',9,2,4096,False),
    ('hang',10,2,4096,False),('reply',11,2,4096,False),('app',12,2,4096,False))

def replace(source,before,after):
    if source.count(before)!=1:raise ValueError('wide exact adaptation: '+before[:100])
    return source.replace(before,after)

def encode_evidence(line):
    """Private dictionary/zero-run v1; standard base64 and CRC32 envelope.

    The pinned GDB lacks zlib/_ctypes. No dependency installation or native call.
    ASCII bytes are literal,128..254 fixed tokens,255+LE24 a zero run.
    """
    import base64,binascii,re
    raw=line.encode('ascii')
    if not 0<len(raw)<=65536 or not line.startswith('SHELL_SESSION ') or line.count('\n')!=1 or not line.endswith('\n'):
        raise ValueError('wide evidence record extent')
    packed=raw
    for n,token in enumerate(EVIDENCE_TOKENS):packed=packed.replace(token,bytes((128+n,)))
    packed=re.sub(b'0{4,}',lambda m:b'\xff'+len(m[0]).to_bytes(3,'little'),packed)
    return 'WIDE_D1 %d %08x %s\n'%(len(raw),binascii.crc32(raw),base64.b64encode(packed).decode('ascii'))

def decode_evidence(trace):
    import base64,binascii
    if type(trace) is not str or len(trace)>128*1024*1024 or not trace.endswith('\n'):
        raise ValueError('wide stored evidence extent')
    result=[];total=0
    for line in trace.splitlines(keepends=True):
        if line.startswith('WIDE_'):
            fields=line.rstrip('\n').split(' ')
            if len(fields)!=4 or fields[0]!='WIDE_D1' or not fields[1].isascii() or not fields[1].isdigit():
                raise ValueError('wide evidence version/header')
            length=int(fields[1])
            if not 0<length<=65536 or str(length)!=fields[1] or len(line)>90000 or total+length>DECODE_LIMIT:
                raise ValueError('wide decoded evidence capacity')
            try:
                packed=base64.b64decode(fields[3],validate=True);raw=bytearray();at=0
                while at<len(packed):
                    token=packed[at];at+=1
                    if token<128:part=bytes((token,))
                    elif token<128+len(EVIDENCE_TOKENS):part=EVIDENCE_TOKENS[token-128]
                    elif token==255:
                        if at+3>len(packed):raise ValueError('wide evidence short run')
                        count=int.from_bytes(packed[at:at+3],'little');at+=3
                        if not 4<=count<=length-len(raw):raise ValueError('wide evidence run extent')
                        part=b'0'*count
                    else:raise ValueError('wide evidence unknown token')
                    if len(part)>length-len(raw):raise ValueError('wide evidence expansion bound')
                    raw.extend(part)
                if (base64.b64encode(packed).decode('ascii')!=fields[3] or len(raw)!=length or
                    '%08x'%binascii.crc32(raw)!=fields[2]):
                    raise ValueError('wide evidence checksum/extent/closure')
                line=raw.decode('ascii')
            except UnicodeError as error:raise ValueError('wide evidence decoding') from error
            if not line.startswith('SHELL_SESSION ') or line.count('\n')!=1 or not line.endswith('\n'):
                raise ValueError('wide evidence decoded record')
        total+=len(line)
        if total>DECODE_LIMIT:raise ValueError('wide decoded evidence capacity')
        result.append(line)
    return ''.join(result)

def lossless_observer(body):
    original="def emit(kind,**values):gdb.write('SHELL_SESSION '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\\n')"
    selected=('EVIDENCE_TOKENS='+repr(EVIDENCE_TOKENS)+'\n'+inspect.getsource(encode_evidence)+"\ndef emit(kind,**values):\n"
        "    line='SHELL_SESSION '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\\n'\n"
        "    gdb.write(line if kind=='start' else encode_evidence(line))")
    return replace(body,original,selected)

def cpu_default_projection():
    import subprocess
    name='arch/x86_64/proc/cpu_trace.inc'
    before=subprocess.check_output(['git','show','ccd6ff46:'+name],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
    after=(ROOT/name).read_text()
    clause='%ifdef REIST_NATIVE_WIDE_FILE\n    cmp r10,262144\n%else\n    cmp r10,2048\n%endif'
    if after.count(clause)!=2 or after.replace(clause,'    cmp r10,2048')!=before:
        raise ValueError('wide CPU exact default/diagnostic projection')
    return True

def cpu_namespace():
    original=old.native_cpu_trace
    source=Path(original.__file__).read_text()
    for before,after in [('1<=sequence<=2048','1<=sequence<=262144'),
                         ('self.sequence<=total<=2048','self.sequence<=total<=262144'),
                         ('0<len(raw)<=2048*192','0<len(raw)<=262144*192')]:
        source=replace(source,before,after)
    name='_reist_wide_cpu_trace';filename='<reist-wide-cpu-trace>'
    module=types.ModuleType(name);module.__file__=filename;sys.modules[name]=module
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    exec(compile(source,filename,'exec'),module.__dict__)
    return module

def serial_reader(stream,output,overflow):
    """Same262144-byte lifetime cap, including arbitrarily short pipe reads."""
    total=0
    try:
        while chunk:=stream.read(256):
            total+=len(chunk)
            if total>262144:
                overflow.set();return
            output.put_nowait(chunk)
    except Exception:
        overflow.set()

def live_trace(path):
    # TextIO.read(character_limit) can chase a growing CRLF log indefinitely.
    # Snapshot its byte extent first, then normalize exactly like final replay.
    with path.open('rb',buffering=0) as stream:
        size=os.fstat(stream.fileno()).st_size
        if not 0<=size<=128*1024*1024:raise ValueError('wide live trace capacity')
        raw=stream.read(size)
        if len(raw)!=size:raise ValueError('wide live trace short snapshot')
    return old.capture_text(raw)

def configure_binary(code,folder,ram,mode,*,service_cpu_budget=False,service_pio_budget=False):
    import qemu_binary_memory as binary
    if service_cpu_budget is not False or service_pio_budget is not True:
        raise ValueError('wide binary reader explicit profile')
    # Establish the approved observation bound once at reader construction.
    # Per-QMP deadlines, limits, translation/equivalence and stop cleanup stay exact.
    initial=inspect.getsource(binary.Reader.__init__)
    if initial.count('self.deadline=time.monotonic()+(42 if service_pio_budget else 27 if service_cpu_budget else 20)')!=1:
        raise ValueError('wide binary reader original deadline binding')
    arguments,body=binary.configure(code,folder,ram,mode,service_pio_budget=True)
    body=replace(body,'\nmem=binary_reader.read\n','\nbinary_reader.deadline+=255\nmem=binary_reader.read\n')
    return arguments,body

def selected_source():
    source=Path(old.__file__).read_text(encoding='utf-8')
    def node(name,changes):
        nonlocal source
        tree=ast.parse(source)
        item=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
        before=ast.get_source_segment(source,item);after=before
        for a,b in changes:after=replace(after,a,b)
        source=replace(source,before,after)
    node('image_config',[('64<=len(app)<=1280','1536<len(app)<=524288')])
    node('pio_record_decode',[('1<=sequence<=2048','1<=sequence<=262144')])
    node('PioCallReader',[('self.sequence<=total<=2048','self.sequence<=total<=262144')])
    node('SessionFeeder',[
        ('self.calls>4096','self.calls>32768'),('elapsed<42','elapsed<297'),
        ('len(trace)>8*1024*1024','len(trace)>128*1024*1024'),('rows>8192','rows>262144')])
    node('fs_expected_response',[('64<=len(app)<=1280','64<=len(app)<=524288')])
    node('validate_storage',[
        ('128 if row[\'slot\']==2 else 8400','128 if row[\'slot\']==2 else 8408'),
        ('(1,24,16,0,deadline)','(2,24,4096,0,deadline)'),
        ('(1,40,1 if layout<2 else 2,sectors,owner,peer,deadline)',
         '(2,40,1 if layout<2 else 2,sectors,owner,peer,deadline)'),
        ("if phase==1:require(not any((deadline,rq,rp,count,status)),'initial control canonical')",
         "if phase==1:require(now<deadline<=now+120000 and not any((rq,rp,count,status)),'initial wide control canonical')"),
        ('now<deadline<=now+2800 and rq and rp and rq!=rp and count==sectors',
         "now<deadline<=now+120000 and deadline==struct.unpack_from('<Q',pair,16)[0] and rq and rp and rq!=rp and count==sectors"),
        ("device['requests']+1<=16","device['requests']+1<=4096"),
        ('fs_sequence.get(owner,0)+1<=8','fs_sequence.get(owner,0)+1<=2050')])
    node('validate_policy',[('v==1 and n==104','v==2 and n==104')])
    node('Snapshots',[
        ('session-[0-9]{4}', 'session-[0-9]{4,6}'),
        ('len(self.seen)<=2048 and self.bytes<=32*1024*1024',
         'len(self.seen)<=262144 and self.bytes<=128*1024*1024')])
    node('validate_capture',[
        ('len(trace.encode())<=8*1024*1024','len(trace.encode())<=512*1024*1024'),
        ('cpu_path.stat().st_size<=2048*192','cpu_path.stat().st_size<=262144*192'),
        ('len(combined)<=32768','len(combined)<=1048576'),
        ("128 if row['slot']==2 else 8400","128 if row['slot']==2 else 8408")])
    node('validate_pio_records',[
        ('total==previous+(len(data)-32)//384<=2048','total==previous+(len(data)-32)//384<=262144')])
    node('validate_probe_steps',[('total<8192','total<262144')])
    node('observer',[("    return ('set breakpoint always-inserted on",
        "    body=once(body,'self.batches>=8192','self.batches>=262144')\n"
        "    body=once(body,\"self.namespace['callbacks']<=8192\",\"self.namespace['callbacks']<=262144\")\n"
        "    body=lossless_observer(body)\n"
        "    return ('set breakpoint always-inserted on")])
    node('evaluate',[
        ("folder/'frame-trace.log',8*1024*1024","folder/'frame-trace.log',128*1024*1024"),
        ("    steps=validate_probe_steps(trace,config['s'])\n","    stored_bytes=len(trace.encode())\n"),
        ('    proof=validate_capture(serial,trace,folder,config,records,catalog,case,layout,app)',
         "    trace=decode_evidence(trace)\n    steps=validate_probe_steps(trace,config['s'])\n    proof=validate_capture(serial,trace,folder,config,records,catalog,case,layout,app)"),
        ("len(reads)+proof['snapshots']+1<=4096 and total+proof['bytes']+cpu_bytes<=128*1024*1024",
         "len(reads)+proof['snapshots']+1<=262144 and total+proof['bytes']+cpu_bytes+stored_bytes<=256*1024*1024")])
    node('validate_cpu',[('sum(charges.values())<=2048','sum(charges.values())<=262144')])
    node('capture_namespace',[
        ('now<started+42','now<started+297'),
        ("'deadline=console_started+42'","'deadline=console_started+297'"),
        ("'time.monotonic()-console_started>45'","'time.monotonic()-console_started>300'"),
        ("'source.read(8*1024*1024+1)'","'source.read(128*1024*1024+1)'"),
        ("(8*1024*1024 if name=='frame-trace.log' else 65536)","(128*1024*1024 if name=='frame-trace.log' else 65536)"),
        ("        exec(compile(source,", "        if function is boot._capture_run:\n            source=once(source,'time.monotonic()-capture_started>45','time.monotonic()-capture_started>300')\n            source=once(source,'from qemu_binary_memory import configure','from run_qemu_x86_64_wide_file import configure_binary as configure')\n            source=wide_serial_capture(source)\n        exec(compile(source,")])
    # Only bounded private observation counts, never RAM addresses or CPU quotas.
    for name in ('hybrid_probe_observer','command_probe_observer','step_loop_tail','stepped_probe_observer'):
        tree=ast.parse(source);item=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        before=ast.get_source_segment(source,item);after=before.replace('8192','262144')
        if before==after:raise ValueError('wide missing selected callback ceiling')
        source=replace(source,before,after)
    # Inside the emitted base observer, not the raw CPU-trace helpers.
    source=replace(source,'snapshots<=2048 and snapshot_bytes<=32*1024*1024',
                   'snapshots<=262144 and snapshot_bytes<=128*1024*1024')
    source=replace(source,"128 if slot==2 else 8400","128 if slot==2 else 8408")
    source=replace(source,"'callbacks<=32768'","'callbacks<=262144'")
    source=replace(source,'cpu_events<=2176','cpu_events<=262272')
    return source

def configure_binary_full(*args,**kwargs):
    arguments,body=configure_binary(*args,**kwargs)
    return arguments,replace(body,'\nbinary_reader.deadline+=255\n','\nbinary_reader.deadline+=855\n')

def full_source(source):
    # Only the explicitly selected full-size, two-root host observation window.
    # Kernel time, semantic predicates, proof capacities and RPC bounds stay exact.
    for name,changes in (
        ('SessionFeeder',[('elapsed<297','elapsed<897')]),
        ('capture_namespace',[
            ('now<started+297','now<started+897'),
            ("'deadline=console_started+297'","'deadline=console_started+897'"),
            ("'time.monotonic()-console_started>300'","'time.monotonic()-console_started>900'"),
            ("'time.monotonic()-capture_started>300'","'time.monotonic()-capture_started>900'"),
            ('import configure_binary as configure','import configure_binary_full as configure')])):
        item=next(n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
        before=ast.get_source_segment(source,item);after=before
        for a,b in changes:after=replace(after,a,b)
        source=replace(source,before,after)
    return source

def namespace(*,full=False):
    if type(full) is not bool:raise ValueError('wide explicit full selector')
    source=selected_source();name='_reist_wide_file_selected';filename='<reist-wide-file-selected>'
    if full:source=full_source(source);name+='_full';filename='<reist-wide-file-full>'
    module=types.ModuleType(name);module.__file__=filename
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    sys.modules[name]=module
    exec(compile(source,filename,'exec'),module.__dict__)
    module.ROOT=ROOT
    module.wide_serial_capture=wide_serial_capture
    module.lossless_observer=lossless_observer
    module.decode_evidence=decode_evidence
    module.native_cpu_trace=cpu_namespace()
    # Avoid modifying shared modules: old regression keeps its own exact view.
    module.file=types.SimpleNamespace(**vars(old.file))
    module.file.media=media
    module.file.block=types.SimpleNamespace(**vars(old.file.block))
    core=module.file.block.TRACE_CORE
    for a,b in [('last<=4096','last<=262144'),('last<=end<=4096','last<=end<=262144')]:
        if a not in core:raise ValueError('wide physical trace adaptation')
        core=core.replace(a,b)
    # Some guards use the split last<=end form; retain every other predicate.
    core=core.replace('last<=end<=4096','last<=end<=262144')
    module.file.block.TRACE_CORE=core
    module.file.fs=types.SimpleNamespace(**vars(old.file.fs))
    physical=module.file.fs.EXTRA
    for before,after in [('physical_events<=1024','physical_events<=262144'),
                         ("len(item['lbas'])<17","len(item['lbas'])<4096"),
                         ('17*512-32','4096*512-32')]:
        physical=replace(physical,before,after)
    module.file.fs.EXTRA=physical
    return module

def wide_serial_capture(source):
    source=replace(source,'output=queue.Queue(maxsize=128)',
        'output=queue.Queue(maxsize=262144)')
    before=('                while chunk:=vm.stdout.read(256):\n'
        '                    try:output.put_nowait(chunk)\n'
        '                    except queue.Full:overflow.set();return')
    after=('                from run_qemu_x86_64_wide_file import serial_reader\n'
        '                serial_reader(vm.stdout,output,overflow)')
    source=replace(source,before,after)
    return replace(source,"with trace_path.open(encoding='ascii') as source:trace=source.read(128*1024*1024+1)",
        'from run_qemu_x86_64_wide_file import live_trace;trace=live_trace(trace_path)')

class Fixture(old.file.pio.Fixture):
    def __init__(self,folder,layout,app,started):
        self.started=started
        self.wide_full=False
        super().__init__(folder,filesystem=media.LAYOUTS[layout],file_program=app)
    def expected(self):
        if self.block or self.malformed:raise ValueError('wide read-only fixture selector')
        return media.image(self.filesystem,self.file_program)
    def run(self,*args):
        limit=900 if self.wide_full else 300
        remaining=self.started+limit-time.monotonic()
        if not 0<remaining<=limit:raise ValueError('wide media absolute deadline')
        ns=dict(vars(old.file.pio),wide_remaining=lambda:min(10,remaining))
        import textwrap
        source=textwrap.dedent(inspect.getsource(old.file.pio.Fixture.run))
        source=replace(source,'timeout=10,','timeout=wide_remaining(),')
        exec(compile(source,'<wide-bounded-media>','exec'),ns)
        return ns['run'](self,*args)

def bounded_fixture(folder,layout,app,started,*,full=False):
    if type(full) is not bool:raise ValueError('wide explicit full fixture selector')
    # Capture intentionally admits the canonical class, not subclasses.
    # Bind only selected media contents/deadline, like the retained AY adapter.
    fixture=old.file.pio.Fixture.__new__(old.file.pio.Fixture)
    fixture.started=started
    fixture.wide_full=full
    fixture.expected=types.MethodType(Fixture.expected,fixture)
    fixture.run=types.MethodType(Fixture.run,fixture)
    old.file.pio.Fixture.__init__(fixture,folder,filesystem=media.LAYOUTS[layout],file_program=app)
    return fixture

def reuse_prefix(reused):
    if reused is None:return 0
    old.require(type(reused) is list and len(reused)==6,'exact six-case reuse')
    for row,case in zip(reused,CASES[:6]):
        old.require(row['passed'] is True and
                    tuple(row[k] for k in ('label','case','layout','ram','full'))==case and
                    0<row['elapsed']<=300,'exact passed normal prefix')
    return 6

def run_matrix(image,folder,candidate,binding,reused=None):
    image=Path(image).resolve();folder=Path(folder).absolute()
    old.require(image.is_relative_to(ROOT/'build') and folder.is_relative_to(ROOT/'build/codex-agent') and
                folder==folder.resolve() and not folder.exists(),'wide fresh scope')
    binding();module=namespace();config,records,original=module.image_config(image)
    catalog=(image.parent/'boot-programs.bin').read_bytes();image_sha=hashlib.sha256(image.read_bytes()).hexdigest()
    folder.mkdir(parents=True);old.file.pio.safe_folder(folder)
    summary=dict(candidate=candidate,image_sha256=image_sha,cases=[],passed=False,closed=False,guest_elapsed=0.0)
    begin=time.monotonic()
    try:
        if reused is not None:
            reuse_prefix(reused)
            for row in reused:
                old.require(row['proof']==module.evaluate(ROOT/row['folder'],config,records,catalog,
                            row['case'],row['layout'],original),'full reused raw replay')
                summary['cases'].append(dict(row));summary['guest_elapsed']+=row['elapsed']
        for label,case,layout,ram,full in CASES[reuse_prefix(reused):]:
            binding();old.require(hashlib.sha256(image.read_bytes()).hexdigest()==image_sha,'wide same image')
            limit=900 if full else 300
            old.require(summary['guest_elapsed']+limit<=3600 and time.monotonic()-begin<3700,'wide finite reservation')
            module=namespace(full=full)
            app=original+bytes(524288-len(original)) if full else original
            old.require(old.admission.wide.producer.prepare(app,[],True)==records[4],'wide exact prepared app')
            out=folder/label;out.mkdir();started=time.monotonic()
            row=dict(label=label,case=case,layout=layout,ram=ram,full=full,passed=False,folder=out.relative_to(ROOT).as_posix())
            summary['cases'].append(row)
            try:
                code=module.observer(config,records,out,case,layout)
                fixture=bounded_fixture(out,layout,app,started,full=full)
                capture=module.stepped_capture_namespace(started)['capture']
                capture(image,out,code,ram,fixture,binary_memory='equivalence',diagnostic_metrics=True,
                        service_pio_budget=True,console_input=module.input_plan(case))
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed']
            old.require(row['elapsed']<=limit,'wide whole-guest deadline incl cleanup')
            row['proof']=module.evaluate(out,config,records,catalog,case,layout,app)
            row['passed']=True;print('WIDE_FILE_GUEST_PASS',label,round(row['elapsed'],3),flush=True)
        summary['passed']=True
        return summary
    except BaseException as error:
        summary['error']=str(error);raise
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-begin)
        with (folder/'summary.json').open('x',encoding='utf-8') as stream:json.dump(summary,stream,indent=2,sort_keys=True)
