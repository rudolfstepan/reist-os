"""Bounded BV qualification and diagnostics with complete raw replay."""
from pathlib import Path
import argparse,hashlib,json,queue,subprocess,threading,time
import check_x86_64_large_file_media as check
import run_qemu_x86_64_shell_boot_media as bios
import run_qemu_x86_64_wide_file as wide
ROOT=Path(__file__).resolve().parents[1]

class NativeSnapshot:
    """RBVT1..4 replay; only explicitly available RAM may be read."""
    LIMIT=2147483648
    def __init__(self,stream,sites,targets):
        import struct
        self.stream=stream;self.used=0;self.failed=False
        self.sequence=1;self.phase=0;self.before=None;self.initialized=False;self.ram_current=False
        self.sites=tuple(sites);self.targets=tuple(targets)
        if len(self.sites) not in (3,5) or len(self.targets)!=len(self.sites) or len(set(self.sites))!=len(self.sites) or set(self.sites)&set(self.targets) or (len(self.sites)==3 and len(set(self.targets))!=3):
            raise ValueError('native bound sites/targets')
        self.pages={};self.ram=bytearray()
        self.seen=0;self.available=0
        raw=self._read(16)
        if raw[:8] not in (b'RBVT1\0\0\0',b'RBVT2\0\0\0',b'RBVT3\0\0\0',b'RBVT4\0\0\0',b'RBVT5\0\0\0'):raise ValueError('native trace version')
        self.version=raw[4]-ord('0')
        if (self.version==5)!=(len(self.sites)==5):raise ValueError('native version/site count')
        count,total=struct.unpack_from('<II',raw,8)
        if not 1<=count<=32 or not 1<=total<=8192:raise ValueError('native trace capacity')
        end=0
        for _ in range(count):
            address,n=struct.unpack('<QQ',self._read(16))
            if not 1<=n<=total-len(self.pages) or address%4096 or address<end or not (
                0x100000<=address and address+n*4096<=0x8000000 or
                0x100000000<=address and address+n*4096<=0x400000000
            ):raise ValueError('native physical range')
            for page in range(address,address+n*4096,4096):
                self.pages[page]=len(self.pages)*4096
            end=address+n*4096
        if len(self.pages)!=total:raise ValueError('native range page count')
        self.ram=bytearray(total*4096)

    def _read(self,n):
        if self.failed or self.used+n>self.LIMIT:raise ValueError('native trace limit/failure')
        data=self.stream.read(n)
        if type(data) is not bytes or len(data)!=n:
            self.failed=True
            raise ValueError('native truncated observation')
        self.used+=n
        return data

    @staticmethod
    def physical(address,n):
        if type(address) is not int or type(n) is not int or n<0:
            raise ValueError('native read arguments')
        for low,high,base in (
            (0xffffffff80100000,0xffffffff88000000,0xffffffff80000000),
            (0xffff800100000000,0xffff800400000000,0xffff800000000000),
        ):
            if low<=address<high and n<=high-address:return address-base
        raise ValueError('native virtual envelope')

    def memory(self,address,n):
        if self.failed or not self.initialized or not self.ram_current or not 0<=n<=1056768:
            raise ValueError('native unavailable snapshot')
        physical=self.physical(address,n);pieces=[]
        while n:
            page=physical&~4095;offset=physical&4095;size=min(n,4096-offset)
            if page not in self.pages:raise ValueError('native unread RAM page')
            if not self.available & (1 << (self.pages[page]//4096)):
                raise ValueError('native unavailable RAM page')
            begin=self.pages[page]+offset
            pieces.append(bytes(self.ram[begin:begin+size]))
            physical+=size;n-=size
        return b''.join(pieces)

    def next(self):
        import binascii,struct
        if self.failed:raise ValueError('native decoder failed')
        try:
            raw=self._read(224)
            if raw[:8]!=b'RBVF'+str(self.version).encode()+b'\0\0\0':raise ValueError('native frame version')
            values=struct.unpack_from('<27Q',raw,8)
            sequence,phase=values[:2]
            if (sequence,phase)!=(self.sequence,self.phase) or not 1<=sequence<=262144:
                raise ValueError('native frame order/capacity')
            full_ram=True
            if self.version>=3:
                flags=self._read(8);flag=struct.unpack('<Q',flags)[0];raw+=flags
                if flag!=int(phase==0 or sequence<=(160 if self.version==5 else 32)):
                    raise ValueError('native explicit RAM availability flag')
                full_ram=bool(flag)
            crc=binascii.crc32(raw);updates=[];last=-1;changed=0
            available=(1<<len(self.pages))-1 if full_ram else 0
            if self.version>=4 and full_ram:
                bitmap=self._read((len(self.pages)+7)//8)
                crc=binascii.crc32(bitmap,crc);available=int.from_bytes(bitmap,'little')
                if available>>len(self.pages):raise ValueError('native bitmap extent')
            while True:
                descriptor=self._read(8)
                address=struct.unpack('<Q',descriptor)[0]
                if address==0xffffffffffffffff:break
                if not full_ram:raise ValueError('native CPU-only record contains RAM')
                if address not in self.pages or address<=last or len(updates)>=len(self.pages):
                    raise ValueError('native duplicate/unknown/unordered page')
                bitmask=1 << (self.pages[address]//4096)
                if not available & bitmask:raise ValueError('native unselected page update')
                changed |= bitmask
                crc=binascii.crc32(descriptor,crc)
                if self.version==1:
                    page=self._read(4096);crc=binascii.crc32(page,crc)
                else:
                    encoded=self._read(8);mask=struct.unpack('<Q',encoded)[0]
                    crc=binascii.crc32(encoded,crc)
                    if not mask or (not self.seen & bitmask and mask!=0xffffffffffffffff):
                        raise ValueError('native empty/incomplete first block mask')
                    begin=self.pages[address]
                    page=bytearray(self.ram[begin:begin+4096])
                    while mask:
                        bit=(mask&-mask).bit_length()-1;end=bit+1
                        while end<64 and mask&(1<<end):end+=1
                        block=self._read((end-bit)*64)
                        crc=binascii.crc32(block,crc);page[bit*64:end*64]=block
                        mask&=~(((1<<(end-bit))-1)<<bit)
                    page=bytes(page)
                updates.append((address,page));last=address
            trailer=descriptor+self._read(24)
            seq,endphase,count,expected=struct.unpack_from('<QQII',trailer,8)
            if (seq,endphase,count)!=(sequence,phase,len(updates)) or (
                binascii.crc32(trailer[:28],crc)!=expected
            ):raise ValueError('native frame trailer/CRC')
            if available & ~(self.seen | changed):
                raise ValueError('native incomplete first snapshot')
            # Independent RET semantics; raw CPU fields have no padding.
            rip,rsp=values[2:4];registers=values[4:21]
            target=values[21];bindings=values[22:25];actual,opcode=values[25:]
            if actual!=1 or opcode!=0xc3:raise ValueError('native actual breakpoint/RET')
            if phase==0:
                if rip not in self.sites or target!=self.targets[self.sites.index(rip)] or (
                    registers[15]&512 or rsp>0xfffffffffffffff7
                ):raise ValueError('native source state')
                if bindings!=tuple(self.physical(a,n) for a,n in ((rip,1),(target,1),(rsp,8))):
                    raise ValueError('native source physical binding')
            else:
                before=self.before
                if before is None or rip!=before[21] or rsp!=before[3]+8 or (
                    values[4:]!=before[4:]
                ):raise ValueError('native RET changed state')
            if phase==0:
                # These bytes were read at this exact stop, not inferred.
                staged=dict(updates)
                def peek(address,n):
                    physical=self.physical(address,n)
                    page=physical&~4095;offset=physical&4095
                    if page not in self.pages or offset+n>4096:
                        raise ValueError('native source page coverage')
                    if not available & (1 << (self.pages[page]//4096)):
                        raise ValueError('native source page unavailable')
                    raw=staged.get(page)
                    if raw is None:
                        if not self.initialized:raise ValueError('native unread source page')
                        begin=self.pages[page];raw=self.ram[begin:begin+4096]
                    return raw[offset:offset+n]
                if peek(rip,1)!=b'\xc3' or struct.unpack('<Q',peek(rsp,8))[0]!=target:
                    raise ValueError('native recorded code/stack')
            for address,page in updates:
                begin=self.pages[address];self.ram[begin:begin+4096]=page
            self.initialized=True
            self.seen |= changed
            self.available=available
            self.ram_current=full_ram
            if phase==0:
                self.before=values
            else:self.before=None
            self.phase^=1
            if not self.phase:self.sequence+=1
            return dict(sequence=sequence,phase=phase,rip=rip,rsp=rsp,
                        registers=registers,target=target,bindings=bindings)
        except BaseException:
            self.failed=True
            raise

class BatchRAM:
    """Private RSP v1: all response bytes validated before any cache publication."""
    def __init__(self,packet):
        self.packet=packet;self.sequence=0;self.failed=False

    def read(self,spans):
        import struct
        if self.failed:raise ValueError('BV batch reader failed')
        try:
            if type(spans) is not tuple or not 1<=len(spans)<=32 or self.sequence>=262144:
                raise ValueError('BV batch capacity')
            total=0;end=0
            for address,size in spans:
                if type(address) is not int or type(size) is not int or not 0<size<=1536-total:
                    raise ValueError('BV batch span')
                if not (0xffffffff80100000<=address<0xffffffff88000000 and size<=0xffffffff88000000-address or
                        0xffff800100000000<=address<0xffff800400000000 and size<=0xffff800400000000-address):
                    raise ValueError('BV batch RAM profile')
                if address<end:raise ValueError('BV batch order/overlap')
                end=address+size;total+=size
            seq=self.sequence+1
            request='qreist-mem:1;%x;%x;'%(seq,len(spans))+';'.join('%x,%x'%span for span in spans)
            reply=self.packet(request)
            if type(reply) is not bytes or len(reply)!=2*(16+12*len(spans)+total) or any(c not in b'0123456789abcdef' for c in reply):
                raise ValueError('BV batch wire extent/hex')
            raw=bytes.fromhex(reply.decode('ascii'))
            if raw[:4]!=b'RBV1' or struct.unpack_from('<QHH',raw,4)!=(seq,len(spans),total):
                raise ValueError('BV batch identity')
            result=[];at=16
            for span in spans:
                if struct.unpack_from('<QI',raw,at)!=span:raise ValueError('BV batch descriptor')
                at+=12;size=span[1];result.append(raw[at:at+size]);at+=size
            if at!=len(raw):raise ValueError('BV batch trailing bytes')
            self.sequence=seq
            return tuple(result)
        except BaseException:
            self.failed=True
            raise


def batch_observer(code,*,equivalence_stops=64):
    """Seed the existing same-stop cache; retain every original read guard."""
    import inspect
    if type(equivalence_stops) is not int or not 1<=equivalence_stops<=1024:
        raise ValueError('BV batch equivalence bound')
    definitions=inspect.getsource(BatchRAM)+r'''
def bv_packet(request):
    answer=gdb.execute('maintenance packet '+request,to_string=True)
    prefix='sending: '+request+'\nreceived: "'
    if len(answer)>6144 or not answer.startswith(prefix) or not answer.endswith('"\n'):
        raise ValueError('BV exact GDB RSP envelope')
    return answer[len(prefix):-2].encode('ascii')
bv_batch=BatchRAM(bv_packet)
'''
    code=wide.replace(code,'class ColdHook(gdb.Breakpoint):',definitions+'\nclass ColdHook(gdb.Breakpoint):')
    marker='        def joined(address,size):'
    addition=r'''        # Only ColdHook's read-only, already stopped callback uses these bytes.
        extra=((S['native_terminal_state'],24),(S['native_pio_state'],64),
               (S['native_pio_trace'],16),(S['native_cpu_trace'],32),
               (S['native_session_pio_trace'],32))
        ordered=sorted(spans+[(a,a+n) for a,n in extra])
        merged=[]
        for begin,end in ordered:
            if merged and begin<=merged[-1][1]:
                merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((begin,end))
        requested=tuple((begin,end-begin) for begin,end in merged)
        context=tuple(reg(n) for n in ('rip','rsp','cr3','eflags'))
        assert context[0]==S[self.name] and not context[3]&512
        values=bv_batch.read(requested)
        assert context==tuple(reg(n) for n in ('rip','rsp','cr3','eflags'))
        if bv_batch.sequence<=BV_EQ_STOPS:
            for (address,size),raw in zip(requested,values):
                assert bounded(address,size)==raw,'BV exact stopped RAM equivalence'
        assert not cache.entries and not cache.used
        cache.entries.extend((address,raw) for (address,size),raw in zip(requested,values))
        cache.used=sum(len(raw) for raw in values)
'''
    code=wide.replace(code,marker,addition.replace('BV_EQ_STOPS',str(equivalence_stops))+marker)
    return code


def observer_toolchain(binding):
    """Bind the isolated extension and its preserved accepted firmware/DLLs."""
    import run_qemu_x86_64_text_runtime as text_runtime
    import build_x86_64_large_file_observer as builder
    binding=Path(binding).resolve()
    check.need(binding.is_relative_to(ROOT/'build/codex-agent/r83bv-large-file') and
               binding.stat().st_size<=65536,'BV tool binding scope')
    row=json.loads(binding.read_text(encoding='utf-8'))
    executable=Path(row['executable']).resolve()
    check.need(executable.is_relative_to(binding.parent) and builder.sha(executable)==row['sha256'] and
               type(row['observer_version']) is int and row['observer_version']==1 and
               row['observer_patch']==builder.sha(builder.PATCH),'BV tool binary/patch binding')
    accepted=builder.ACCEPTED/'binary-binding01.json'
    _,firmware=text_runtime.portable_toolchain(accepted)
    check.need(row['dlls']==json.loads(accepted.read_text())['dlls'],'BV complete accepted DLL set')
    check.need(Path(row['firmware_directory']).resolve()==firmware,'BV preserved firmware')
    for name,item in row['dlls'].items():
        path=(executable.parent/name).resolve()
        check.need(path.parent==executable.parent and builder.sha(path)==item['sha256'],'BV runtime DLL binding')
    check.need(builder.sha(binding.parent/'inputs.json')==row['observer_inputs'],'BV input manifest')
    inputs_path=binding.parent/'inputs.json'
    check.need(inputs_path.stat().st_size<=8*1024*1024,'BV input manifest capacity')
    inputs=json.loads(inputs_path.read_text())
    check.need(len(inputs)<=32768 and builder.sha(binding.parent/'observer-builder.py')==
               inputs[str(Path(builder.__file__))],'BV original builder source binding')
    check.need(set(row['observer_sources'])==set(builder.FILES),'BV complete staged source set')
    for name,pin in row['observer_sources'].items():
        check.need(name in builder.FILES and builder.sha(binding.parent/'source'/name)==pin,'BV staged source binding')
    return executable,firmware


def diagnostic(package,folder):
 package=Path(package).resolve();folder=Path(folder).absolute()
 check.need(folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent') and not folder.exists(),'fresh diagnostic scope')
 folder.mkdir(parents=True);start=time.monotonic();end=start+270
 result=dict(qualification=False,passed=False,commands=[],limit=300);vm=None;boot=None;data=None
 try:
  accepted=check.verify(package)
  boot=bios.BootMedium(accepted/'reist-x86_64.img',folder/'boot-medium','hdd','normal',start+297)
  boot.verify('before')
  cls=wide.old.file.pio.Fixture;data=cls.__new__(cls)
  data.started=start;data.wide_full=False
  data.expected=lambda:check.bounded(accepted/'system.ext2',2097152)
  import types
  data.run=types.MethodType(wide.Fixture.run,data)
  cls.__init__(data,folder,filesystem='ext2-2k',file_program=(accepted/'largetest.prg').read_bytes())
  data.verify('before')
  qemu=wide.old.boot.resolve_qemu(None)
  command=[str(qemu),'-machine','pc,accel=tcg','-cpu','max','-smp','1','-m','4096',
    '-display','none','-monitor','none','-serial','stdio','-no-reboot','-no-shutdown',
    '-nic','none','-device','isa-debug-exit,iobase=0xf4,iosize=0x04',
    *bios.boot_arguments(boot.overlay,'hdd'),*data.arguments(folder)]
  result['command']=command;result['qemu_sha256']=hashlib.sha256(qemu.read_bytes()).hexdigest()
  output=queue.Queue(maxsize=262144);overflow=threading.Event();serial=bytearray()
  def reader(stream):
   try:
    while b:=stream.read(1):output.put_nowait(b)
   except Exception:overflow.set()
  with (folder/'stderr.log').open('xb') as err:
   vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,
    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   thread=threading.Thread(target=reader,args=(vm.stdout,),daemon=True);thread.start()
   banner=wide.old.BANNER.encode();counts=[0,0];commands=(b'largetest\n',b'cat /data.txt\n',b'exit\n')
   while time.monotonic()<end:
    for _ in range(8192):
     try:serial.extend(output.get_nowait())
     except queue.Empty:break
    check.need(not overflow.is_set() and len(serial)<=262144,'diagnostic serial bound')
    parts=bytes(serial).split(banner);run=len(parts)-1
    check.need(run<=2,'diagnostic root bound')
    if run and counts[run-1]<3 and parts[-1].count(b'C:\\>')>counts[run-1]:
     command=commands[counts[run-1]];vm.stdin.write(command);vm.stdin.flush();counts[run-1]+=1
     result['commands'].append(dict(run=run,payload=command.hex(),elapsed=time.monotonic()-start))
    (folder/'serial.log').write_bytes(serial)
    if b'EXCEPTION_FATAL' in serial or b'PANIC' in serial:break
    if counts==[3,3] and serial.count(b'REIST_X86_64_PROCESS_RUN_OK')==2:break
    if vm.poll() is not None:break
    time.sleep(.01)
   result.update(returncode=vm.poll(),counts=counts,large_ok=serial.count(b'LARGETEST_OK'),serial_bytes=len(serial))
   (folder/'serial.log').write_bytes(serial)
   check.need(counts==[3,3] and result['large_ok']==2,'two diagnostic ordinary launches')
   check.need(b'PANIC' not in serial and b'FATAL' not in serial,'diagnostic fatal output')
   result['passed']=True
 finally:
  if vm and vm.poll() is None:vm.terminate();vm.wait(timeout=2)
  try:
   if data:data.verify('after')
   if boot:boot.verify('after')
  finally:
   result['elapsed']=time.monotonic()-start
   (folder/'diagnostic.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 return result


def record_layout(record):
    """Independent fixed-record geometry; never infer a version from capacity."""
    import struct
    if type(record) is not bytes:raise ValueError('BV record type')
    for version,pages,header,size in ((2,64,96,266336),(3,256,288,1052960)):
        if len(record)==size and record[:16]==b'RNPGv'+str(version).encode()+b'\0\0'+struct.pack('<II',version,size):
            if any(record[24+pages:header]) or any(f not in (0,4,5,6) for f in record[24:24+pages]):
                raise ValueError('BV record rights/reserved')
            return pages,header,header+pages*4096
    raise ValueError('BV exact record version/extent')

def image_content(record):return record[:record_layout(record)[2]]

def record_flag(record,page):
    pages,_,_=record_layout(record)
    if type(page) is not int or not 0<=page<256:raise ValueError('BV image page index')
    return record[24+page] if page<pages else 0

def chunked_read(reader,address,size):
    """Keep the original transport's per-read, aggregate and pause limits."""
    if type(address) is not int or type(size) is not int or not 0<=address<1<<64 or not 0<=size<=1056768 or size>(1<<64)-address:
        raise ValueError('BV bounded logical memory read')
    chunks=[]
    for offset in range(0,size,270336):
        count=min(270336,size-offset);raw=reader.read(address+offset,count)
        if type(raw) is not bytes or len(raw)!=count:raise ValueError('BV exact memory chunk')
        chunks.append(raw)
    return b''.join(chunks)

def configure_binary(code,folder,ram,mode,**kwargs):
    import inspect
    arguments,body=wide.configure_binary(code,folder,ram,mode,**kwargs)
    body=wide.replace(body,'binary_reader.deadline+=255','binary_reader.deadline+=555')
    body=wide.replace(body,'\nmem=binary_reader.read\n',
        '\n'+inspect.getsource(chunked_read)+'\nmem=lambda address,size:chunked_read(binary_reader,address,size)\n')
    return arguments,body

def large_host_helper(name):
    """Private BV evidence extent; retain old helpers and decoding semantics."""
    import inspect,re
    source=inspect.getsource(getattr(wide,name))
    source=wide.replace(source,'128*1024*1024','256*1024*1024')
    namespace=dict(vars(wide),DECODE_LIMIT=1024*1024*1024)
    if name=='decode_evidence':
        # Consume an ASCII run in C, preserving every token, expansion bound,
        # CRC and record check from the accepted decoder.
        source=wide.replace(source,'if token<128:part=bytes((token,))',
            'if token<128:\n'
            '                        literal=ASCII_RUN.match(packed,at-1)\n'
            '                        part=literal.group();at=literal.end()')
        namespace['ASCII_RUN']=re.compile(rb'[\x00-\x7f]+')
    exec(compile(source,'<BV-host-evidence-'+name+'>','exec'),namespace)
    return namespace[name]

def live_trace(path):
    return large_host_helper('live_trace')(path)

def large_serial_capture(source):
    source=wide.replace(source,'source.read(256*1024*1024+1)','source.read(128*1024*1024+1)')
    source=wide.wide_serial_capture(source)
    return wide.replace(source,'from run_qemu_x86_64_wide_file import live_trace',
                        'from run_qemu_x86_64_large_file import live_trace')

def large_fixture_run(self,*args):
    import inspect
    source=inspect.getsource(wide.Fixture.run)
    import textwrap
    source=textwrap.dedent(source)
    source=wide.replace(source,'limit=900 if self.wide_full else 300','limit=600')
    namespace=dict(vars(wide))
    exec(compile(source,'<BV-host-fixture-deadline>','exec'),namespace)
    return namespace['run'](self,*args)

def matching_record(slot,actual,records):
    candidates=[records[slot]] if slot in (2,3) else [records[n] for n in (4,5,6,7)]
    matches=[r for r in candidates if image_content(actual)==image_content(r)]
    check.need(len(matches)==1,'BV exact uniquely bound imported program')
    return matches[0]

def entry_record(row,raw,records):
    if row['slot']!=4:return records[row['slot']]
    import run_qemu_x86_64_app_files as apps
    name=apps.tool_name(row);slots=dict(largetest=4,largetst=4,cat=5,ls=6,probe=7)
    check.need(name in slots,'BV declared foreground executable')
    return records[slots[name]]

def storage_oracle(layout):
    """Independent inherited wire model, explicitly bound to the on-disk names."""
    import types
    import run_qemu_x86_64_app_files as apps
    import build_x86_64_large_file_media as media
    check.need(type(layout) is int and layout in range(5),'BV wire layout')
    names=tuple('largetst.prg' if layout<2 and n=='largetest.prg' else n for n in check.NAMES)
    def admit(files):
        check.need(type(files) is dict and set(files)==set(names),'BV wire exact file set')
        media.admit({('largetest.prg' if layout<2 and n=='largetst.prg' else n):v for n,v in files.items()})
    ns=dict(vars(apps),media=types.SimpleNamespace(NAMES=names,admit=admit))
    for name in ('info','fs_expected_response','expected_reply','validate_capture_before_grant'):
        fn=getattr(apps,name);ns[name]=types.FunctionType(fn.__code__,ns,name,fn.__defaults__,fn.__closure__)
    return ns

def disk_files(layout,files):
    check.need(type(files) is dict and set(files)==set(check.NAMES),'BV logical file set')
    return {('largetst.prg' if layout<2 and name=='largetest.prg' else name):value for name,value in files.items()}

def validate_executable_capture(events,root,child,layout,files,*,oracle=None):
    """Reconstruct all executable bytes and the terminal EOF before publication."""
    import struct
    import run_qemu_x86_64_app_files as apps
    bound=disk_files(layout,files);oracle=storage_oracle(layout) if oracle is None else oracle
    name=apps.tool_name(child)+'.prg';check.need(name in bound,'BV captured executable name')
    path=('/'+name).encode();incoming={};completed=[];creation=None
    for row in events:
        if row.get('gen')!=root['gen']:continue
        if row['kind']=='call' and row['op']==53 and not row['profile_denied']:
            raw=wide.old.ipc_message(bytes.fromhex(row['before']))
            if len(raw)==576:
                h=struct.unpack_from('<4I4QIiQ',raw)
                if h[2] in (5,6) and h[3]==0:
                    key=h[4:6];check.need(key not in incoming,'BV unique pending FS request')
                    incoming[key]=(row,raw[64:])
        if row['kind']!='return':continue
        if row['op']==132 and row['result']==(child['gen']<<32)|4:
            creation=row;break
        if row['op']==54 and row['result']==0:
            raw=wide.old.ipc_message(bytes.fromhex(row['after']))
            if len(raw)==576:
                h=struct.unpack_from('<4I4QIiQ',raw);key=h[4:6]
                if key in incoming:
                    sent,request=incoming.pop(key)
                    completed.append((sent,request,row,raw[64:],h[4]))
    check.need(creation is not None,'BV successful constructor after capture')
    selected=[]
    for item in completed:
        op,operand=wide.old.fs_request_frame(item[1])
        if (operand.lower() if layout<2 else operand)==path:selected.append(item)
    stats=[n for n,item in enumerate(selected) if wide.old.fs_request_frame(item[1])[0]==5]
    check.need(stats,'BV executable STAT before read')
    selected=selected[stats[-1]:];owner=selected[0][4];position=0;ended=False;content=bytearray()
    check.need(3<=len(selected)<=4098 and owner>0,'BV bounded complete capture calls')
    previous=selected[0][0]['entered']
    for n,(sent,request,received,answer,generation) in enumerate(selected):
        op,_=wide.old.fs_request_frame(request)
        check.need(generation==owner and previous<=sent['entered']<=received['now']<=creation['entered']
                   and not ended,'BV capture monotonic live owner/order')
        previous=received['now'];status,expected=oracle['fs_expected_response'](request,layout,bound)
        check.need(status==0 and answer==expected,'BV exact immutable executable reply')
        if not n:
            check.need(op==5,'BV initial STAT');continue
        offset,requested=struct.unpack_from('<2I',request,24);count=struct.unpack_from('<I',answer,32)[0]
        check.need(op==6 and offset==position and count<=requested,'BV executable contiguous read')
        if not count:ended=True
        else:content.extend(answer[228:228+count]);position+=count
    check.need(ended and bytes(content)==bound[name] and position==len(bound[name]),'BV executable exact bytes and EOF')
    check.need(0<=creation['now']-selected[0][0]['entered']<120000,'BV unchanged whole capture deadline')
    version,size,operation,reserved=struct.unpack_from('<4I',bytes.fromhex(creation['before']))
    check.need((version,size,operation,reserved)==(7,64,1,0),'BV application CREATE-v7 publication')
    return dict(bytes=position,calls=len(selected),owner=owner,sha256=hashlib.sha256(content).hexdigest())

def image_config(image):
    """Bind retained service-v2 records and all ordinary application-v3 bytes."""
    import run_qemu_x86_64_app_files as apps
    from build_x86_64_large_image import prepare
    image=Path(image).resolve();module=observer_namespace()
    config,records,_=module.image_config(image)
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    folders=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file()
             and (p/'boot-programs.bin').read_bytes()==catalog]
    check.need(len(folders)==1,'BV unique ordinary program source');folder=folders[0]
    values={name:(image.parent/name).read_bytes() for name in (check.KERNEL,check.CORE,'boot-programs.bin')}
    for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),*check.EXTRA):
        path=folder/'root/data.txt' if name=='data.txt' else folder/name
        values[name]=path.read_bytes()
    check.input_binding(values);files=check.medium_files(values)
    for slot,name in ((4,'largetest'),(5,'cat'),(6,'ls'),(7,'probe')):
        install=folder/'root'/('bin/largetest.prg' if slot==4 else name+'.prg')
        check.need(install.read_bytes()==files[name+'.prg'],'BV exact installed '+name)
        records[slot]=prepare(files[name+'.prg'],[])
    check.need(set(records)==set(range(2,8)) and all(record_layout(records[n])[0]==
        (64 if n<4 else 256) for n in records),'BV service/app record version boundary')
    config.update(app_probe=module.file.block.map_symbol(folder/'app-probe.map','reist_app_probe_selection'),
                  large_witness=module.file.block.map_symbol(folder/'largetest.map','reist_large_file_witness'),
                  probe_modes=())
    return config,records,files

def selected_source():
    """Preserve complete prior shell proof, selecting only new layout contracts."""
    import ast,re
    import run_qemu_x86_64_app_files as apps
    source=apps.selected_source()
    def change(before,after,count=None):
        nonlocal source
        actual=source.count(before)
        if not actual or count is not None and actual!=count:raise ValueError('BV source binding '+before)
        source=source.replace(before,after)
    change('8192 if case==5 else 4096', "config['large_case_ram']", 2)
    change('from run_qemu_x86_64_wide_file import configure_binary as configure',
           'from run_qemu_x86_64_large_file import configure_binary as configure',1)
    change("struct.unpack('<128Q'","struct.unpack('<512Q'")
    change("slot*1024,1024","slot*4096,4096")
    change("slot*1024","slot*4096")
    change("mem(reg('r12'),1024)","mem(reg('r12'),4096)")
    # BU enlarged each ELF context from64 to256 page entries. Preserve the
    # four-byte diagnostic counter exception at its actual new offset.
    change("S['elf_context_store']+i*592", "S['elf_context_store']+i*2320",1)
    change("raw=mem(address,592);assert not any(raw[:576]) and not any(raw[580:])",
           "raw=mem(address,2320);assert not any(raw[:2304]) and not any(raw[2308:])",1)
    change("raw.read(row['contexts'],14*592)","raw.read(row['contexts'],14*2320)",1)
    change("not any(contexts[n:n+576]) and not any(contexts[n+580:n+592]) for n in range(0,len(contexts),592)",
           "not any(contexts[n:n+2304]) and not any(contexts[n+2308:n+2320]) for n in range(0,len(contexts),2320)",1)
    change("2*1024,1024","2*4096,4096")
    change("mem(S['scheduler_tasks'],1024)","mem(S['scheduler_tasks'],4096)")
    # Identity/terminal request hooks prohibit QMP reads (>=32768 bytes).
    # Preserve that guard and capture the enlarged authority table in two
    # contiguous reads while the same read-only callback keeps the VM stopped.
    change("mem(S['scheduler_tasks'],8192)",
           "mem(S['scheduler_tasks'],16384)+mem(S['scheduler_tasks']+16384,16384)")
    change("raw.read(row['task'],1024)","raw.read(row['task'],4096)")
    change("raw.read(row['driver'],1024)","raw.read(row['driver'],4096)")
    change("len(raw)==8192","len(raw)==32768")
    change("len(raw)==8704","len(raw)==33280")
    change("row['authority'],8704","row['authority'],33280")
    change("raw,8192+slot*64","raw,32768+slot*64")
    source=re.sub(r'\b(t|task)\[(68|69|70|85|86|87)\]',lambda m:m[1]+'['+str(int(m[2])+192)+']',source)
    change('(0,1,68,69,70,85,86,87)','(0,1,260,261,262,277,278,279)')
    change('(0,1,2,68,69,70,85,86,87)','(0,1,2,260,261,262,277,278,279)')
    change('0x440000','0x500000')
    change('range(64)','range(256)')
    change('record[24+page]','record_flag(record,page)')
    change('record[24+p]','record_flag(record,p)')
    change('record[96+page*4096:96+(page+1)*4096]',
           'record[record_layout(record)[1]+page*4096:record_layout(record)[1]+(page+1)*4096]')
    change('record[96+p*4096:96+(p+1)*4096]',
           'record[record_layout(record)[1]+p*4096:record_layout(record)[1]+(p+1)*4096]')
    change("assert record[:16]==b'RNPGv2\\0\\0'+struct.pack('<II',2,266336)",'assert record_layout(record)')
    change("record[:16]==b'RNPGv2\\0\\0'+struct.pack('<II',2,266336)",'record_layout(record)')
    change("record=mem(S['elf_import_record'],266336)",
           "extent=d(S['elf_import_record']+12);assert extent in (266336,1052960)\n    record=mem(S['elf_import_record'],extent);record_layout(record)")
    change("record=raw.read(row['record'],266336)","record=raw.read(row['record']);record_layout(record)")
    change("record=raw.read(row['raw'],266336)","record=raw.read(row['raw']);record_layout(record)")
    change('record[:262240]','image_content(record)')
    change('r[:262240]','image_content(r)')
    change('expected[:262240]','image_content(expected)')
    change('matching_record(slot,record,records)[:262240]','image_content(matching_record(slot,record,records))')
    change("path.stat().st_size==266336","path.stat().st_size in (266336,1052960)")
    change("len(raw)!=266336","len(raw) not in (266336,1052960)")
    # A cleanup snapshot includes the import record AND scheduler/family
    # state. Bound the private host envelope separately from RNPG size;
    # replay still requires each semantic record's exact size and content.
    change('len(raw)<=1024*1024','len(raw)<=2*1024*1024')
    change("reference['bytes']<=1024*1024","reference['bytes']<=2*1024*1024")
    # Approved host-only two-root reservation; never replace guest deadlines.
    change('total+proof[\'bytes\']+cpu_bytes+stored_bytes<=256*1024*1024',
           'total+proof[\'bytes\']+cpu_bytes+stored_bytes<=1024*1024*1024',1)
    change('len(trace.encode())<=512*1024*1024','len(trace.encode())<=1024*1024*1024',1)
    change('128*1024*1024','256*1024*1024',6)
    change('now<started+297','now<started+597',1)
    change('deadline=console_started+297','deadline=console_started+597',1)
    change('time.monotonic()-console_started>300','time.monotonic()-console_started>600',1)
    change('time.monotonic()-capture_started>300','time.monotonic()-capture_started>600',1)
    change('elapsed<297','elapsed<597',1)
    change("HIGH+0xb05000,270336","HIGH+0xb05000,1056768")
    change('0<=size<=270336','0<=size<=1056768')
    change("row['frames']<=69","row['frames']<=261")
    change('((5,64),(6,80))','((5,64),(6,80),(7,64))')
    change('(2,24,4096,0,deadline)','(3,24,8192,0,deadline)')
    change('(2,40,1 if layout<2 else 2,sectors,owner,peer,deadline)',
           '(3,40,1 if layout<2 else 2,sectors,owner,peer,deadline)')
    change("device['requests']+1<=4096","device['requests']+1<=8192")
    change('fs_sequence.get(owner,0)+1<=2050','fs_sequence.get(owner,0)+1<=4098')
    change('v==2 and n==104','v==3 and n==104')
    change('    used=set()\n    for _,endpoint,payload,gen,completed in receives:\n'
           '        candidates=[n for n,(entered,ep,data,sender) in enumerate(sends)\n'
           '                    if n not in used and ep==endpoint and data==payload and sender!=gen and entered<completed]',
           '    used=set();by_message={}\n'
           '    for n,(entered,endpoint,payload,sender) in enumerate(sends):\n'
           '        by_message.setdefault((endpoint,payload),[]).append((n,entered,sender))\n'
           '    for _,endpoint,payload,gen,completed in receives:\n'
           '        candidates=[n for n,entered,sender in by_message.get((endpoint,payload),())\n'
           '                    if n not in used and sender!=gen and entered<completed]',1)
    change('    validate_objects(combined,receipts,layout,app,config)',
           '    validate_objects(combined,receipts,layout,app,config)\n'
           '    validate_large_case(combined,app)',1)
    change('wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32))',
           'wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32),large_image=True)')
    change('            validate_image_start(row,raw,expected)',
           '            validate_image_start(row,raw,expected)\n'
           "            if slot==4:\n"
           "                root=next(s for s in starts.values() if s['slot']==0 and s['run']==run)\n"
           '                validate_executable_capture(combined,root,row,layout,app)',1)
    # Helpers are embedded in the emitted GDB program and supplied to replay.
    import inspect
    functions='\n'.join(inspect.getsource(f) for f in (record_layout,image_content,record_flag))
    change("starts={};copies={};pending={};runs=0;",functions+"\nstarts={};copies={};pending={};runs=0;",1)
    tree=ast.parse(source) # Generated observer strings are compiled separately in tests.
    return source

def observer_namespace():
    """Private composed observer; case policy is bound by the qualification runner."""
    import linecache,sys,types
    source=selected_source();filename='<reist-large-file-observer>'
    module=types.ModuleType('_reist_large_file_observer');module.__file__=filename
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    sys.modules[module.__name__]=module
    exec(compile(source,filename,'exec'),module.__dict__)
    prior=wide.namespace();module.ROOT=ROOT
    module.file=types.SimpleNamespace(**vars(prior.file))
    module.file.block=types.SimpleNamespace(**vars(prior.file.block))
    # Profile3 exclusively binds the accepted BY128-call grant. Physical
    # records must carry its exact witnessed tag; shared old decoders stay64.
    core=wide.replace(module.file.block.TRACE_CORE,'v[5]>64','v[5]>128')
    module.file.block.TRACE_CORE=wide.replace(core,'or v[7]:',
        'or v[7]!=0xffffff7f00000080:')
    module.admission=types.SimpleNamespace(**vars(prior.admission))
    module.admission.wide=types.SimpleNamespace(**vars(prior.admission.wide))
    replace=wide.replace
    batch=module.file.FILE_RAM_BATCH
    for before,after in (('0x43ffff','0x4fffff'),
                         ('raw=mem(DM+root,64*8);assert len(raw)==64*8',
                          'raw=mem(DM+root,256*8);assert len(raw)==256*8'),("'<64Q'","'<256Q'"),
                         ('len(frames)<=69','len(frames)<=261')):
        batch=replace(batch,before,after)
    module.file.FILE_RAM_BATCH=batch
    module.file.FILE_USER_READ=replace(module.file.FILE_USER_READ,'n<=266336','n<=1052960')
    release=module.admission.wide.OBSERVER
    for before,after in (('t[4:68]','t[4:260]'),('t[2:68]','t[2:260]'),
                         ("len(release['freed'])<=69","len(release['freed'])<=261")):
        release=replace(release,before,after)
    module.admission.wide.OBSERVER=release
    ranges=dict(module.admission.ZERO_RANGES)
    if ranges.get('scheduler_tasks')!=8192 or ranges.get('elf_import_record')!=266336:
        raise ValueError('BV inherited zero-range binding')
    module.admission.ZERO_RANGES=tuple((name,32768 if name=='scheduler_tasks' else
        1052960 if name=='elf_import_record' else size) for name,size in module.admission.ZERO_RANGES)
    for name in ('native_cpu_trace','wide_serial_capture','lossless_observer','decode_evidence'):
        setattr(module,name,getattr(prior,name))
    module.wide_serial_capture=large_serial_capture
    module.decode_evidence=large_host_helper('decode_evidence')
    for helper in (record_layout,image_content,record_flag,matching_record,entry_record,validate_executable_capture):setattr(module,helper.__name__,helper)
    return module

CASES=(('ext2-2k-4g',0,3,4096,'full'),('ext2-2k-8g',0,3,8192,'full'),
       ('ext2-4k',0,4,4096,'full'),('fat12',0,0,4096,'full'),
       ('fat32',0,1,4096,'fat-healthy'),('unsupported-ext2',0,2,4096,'unsupported'),
       ('oversized-input',0,3,4096,'oversize'),('driver-crash',7,3,4096,'full'),
       ('fs-crash',9,3,4096,'full'),('fs-hang',10,3,4096,'full'),
       ('fs-reply',11,3,4096,'full'),('app-crash',12,3,4096,'crash'))

def case_files(spec,files):
    check.need(spec in CASES,'BV declared case')
    files=dict(files)
    if spec[4]=='fat-healthy':files['largetest.prg']=files['largetest.prg'][:754104]
    elif spec[4]=='oversize':files['largetest.prg']+=b'\0'
    elif spec[1] in (7,9,10,11,12):
        # Fault cases still exceed profile2's512KiB input ceiling and retain
        # every loaded page; only nonloaded ELF padding is shorter.
        files['largetest.prg']=files['largetest.prg'][:524289]
    return files

def case_medium(spec,files):
    """Only the two rejection fixtures extend the normal immutable producer."""
    import inspect
    import build_x86_64_large_file_media as media
    layout=wide.media.LAYOUTS[spec[2]]
    if spec[4] not in ('unsupported','oversize'):return media.image(layout,files)
    source=inspect.getsource(media.image)
    if spec[4]=='oversize':
        check.need(len(files['largetest.prg'])==1048577,'BV exact oversize fixture')
        source=wide.replace(source,'1048576 if name','1048577 if name')
    else:
        check.need(len(files['largetest.prg'])==1048576,'BV exact unsupported fixture')
        source=wide.replace(source,"('ext2-2k','ext2-4k')","('ext2-1k',)")
        source=wide.replace(source,"bs=2048 if layout=='ext2-2k' else 4096",'bs=1024')
        source=wide.replace(source,'log=1 if bs==2048 else 2','log=0')
        source=wide.replace(source,'(20,0)','(20,1)')
        source=wide.replace(source,'u32(bs+at,v)','u32(2*bs+at,v)')
        for offset in (12,14,16):
            source=wide.replace(source,'u16(bs+'+str(offset)+',','u16(2*bs+'+str(offset)+',')
        source=wide.replace(source,'count=(len(value)+bs-1)//bs;indirect=count>12',
            'count=(len(value)+bs-1)//bs;indirect=count>12\n'
            '  leaves=(max(0,count-12-bs//4)+bs//4-1)//(bs//4)\n'
            '  extra=1+leaves if leaves else 0')
        source=wide.replace(source,'count>12+bs//4 or cursor+count>total','leaves>3 or cursor+count+extra>total')
        source=wide.replace(source,'(count+indirect)','(count+indirect+extra)')
        source=wide.replace(source,'range(count-12)','range(min(count-12,bs//4))')
        source=wide.replace(source,'  raw[cursor*bs:',
            '  if leaves:\n'
            '   double=cursor+count;u32(inode+92,double);used.update(range(double,double+extra))\n'
            '   for k in range(leaves):\n'
            '    leaf=double+1+k;u32(double*bs+4*k,leaf)\n'
            '    for j in range(min(bs//4,count-12-bs//4-k*(bs//4))):u32(leaf*bs+4*j,cursor+12+bs//4+k*(bs//4)+j)\n'
            '  raw[cursor*bs:')
        source=wide.replace(source,'cursor+=count','cursor+=count+extra')
    namespace=dict(vars(media));exec(compile(source,'<BV-negative-medium>','exec'),namespace)
    return namespace['image'](layout,files)

def case_namespace(spec):
    """Full original raw lifecycle oracle with explicit case outcomes."""
    import inspect,types
    import run_qemu_x86_64_app_files as apps
    import build_x86_64_large_file_media as media
    check.need(spec in CASES,'BV declared qualification case')
    label,case,layout,ram,mode=spec
    module=observer_namespace();module.CASES=((case,layout,ram),)
    tool='largetst' if layout<2 else 'largetest'
    commands=(tool+'\ncat /data.txt\nexit\n').encode()
    first=(tool+'\n').encode()+commands if case in (7,9,10,11) else commands
    if mode=='crash':first=(tool+' c\ncat /data.txt\nexit\n').encode()
    if mode in ('unsupported','oversize'):first=commands=b'/largetest.prg\ncat /data.txt\nexit\n'
    module.input_plan=lambda unused:(((0,first),),((0,commands),))
    module.file.media=types.SimpleNamespace(LAYOUTS=apps.media.LAYOUTS,
        image=lambda unused,program:case_medium(spec,program))
    objects=storage_oracle(layout)
    if mode=='unsupported':
        expected=objects['fs_expected_response']
        def unsupported_reply(request,layout,files):
            import struct
            op,path=wide.old.fs_request_frame(request)
            if op==6 and path==b'/largetest.prg' and struct.unpack_from('<I',request,24)[0]==274432:
                return -110,b''
            return expected(request,layout,files)
        objects['fs_expected_response']=unsupported_reply
    if mode=='oversize':
        def admit(values):
            check.need(set(values)==set(check.NAMES) and len(values['largetest.prg'])==1048577,'BV negative wire binding')
            media.admit(dict(values,**{'largetest.prg':values['largetest.prg'][:-1]}))
        objects['media'].admit=admit
    objects['case_spec']=lambda unused:(label,case,layout,ram,())
    source=inspect.getsource(apps.validate_objects)
    source=wide.replace(source,"r['run']==run and r['slot']==4]",
        "r['run']==run and r['slot']==4 and tool_name(r) not in ('largetest','largetst')]")
    exec(compile(source,'<BV-reference-object-proof>','exec'),objects)
    module.fs_expected_response=lambda request,layout,files:objects['fs_expected_response'](
        request,layout,disk_files(layout,files))
    module.validate_executable_capture=lambda events,root,child,layout,files:validate_executable_capture(
        events,root,child,layout,files,oracle=objects)
    module.validate_objects=lambda events,receipts,layout,files,config:objects['validate_objects'](
        events,receipts,layout,disk_files(layout,files),config)
    module.validate_large_case=lambda events,files:validate_case_history(spec,events,files)
    module.tool_name=apps.tool_name;module.validate_probe_selection=apps.validate_probe_selection
    source=inspect.getsource(wide.namespace().validate_io_and_faults)
    for before,after in (
        ('expected_count=4 if case==6 and run==1 else 0 if case==16 and run==1 else 1',
         'expected_count='+str(1 if mode in ('unsupported','oversize') else 2)),
        ('expected=(134,3) if case==12 and run==1 else (256,3) if case==13 and run==1 else (0,3) if case in (14,15) and run==1 else (82,4)',
         "expected=(134,3) if case==12 and run==1 and tool_name(app_start) in ('largetest','largetst') else (0,4)"),
        ("written==(b'SESSION64\\n' if expected==(82,4) else b'')",
         "written==(b'' if expected==(134,3) else b'LARGETEST_OK\\n' if tool_name(app_start) in ('largetest','largetst') else app_files['data.txt'])"),
        ("struct.unpack_from('<Q',request,32)[0]==1000","0<struct.unpack_from('<Q',request,32)[0]<=1000")):
        source=wide.replace(source,before,after)
    # Freeze both exact command resolution and ordering in addition to bytes.
    source=wide.replace(source,"        require(len(apps)==expected_count,'actual foreground construction count')",
        "        require(len(apps)==expected_count,'actual foreground construction count')\n"
        "        require(tuple(tool_name(a) for a in apps)=="+repr(('cat',) if mode in ('unsupported','oversize') else (tool,'cat'))+",'BV reference command resolution')")
    if mode=='unsupported':
        source=wide.replace(source,"((2,1) if case==16 and run==1 else (1,0) if case in range(7,12) and run==1 else (0,0))",'(1,0)')
    exec(compile(source,'<BV-reference-foreground-proof>','exec'),module.__dict__)
    return module

def normal_namespace():return case_namespace(CASES[0])

def validate_case_history(spec,events,files):
    """Prove rejection before constructor publication, including exact prefix."""
    import struct
    if spec[4] not in ('unsupported','oversize'):return
    for run in (1,2):
        roots=[r for r in events if r['kind']=='start' and r['run']==run and r['slot']==0]
        check.need(len(roots)==1,'BV rejection root')
        root=roots[0]['gen'];sent=[];replies={}
        for row in events:
            if row.get('gen')!=root or row['kind']!='return' or row['result'] or row['op'] not in (53,54):continue
            raw=wide.old.ipc_message(bytes.fromhex(row['before' if row['op']==53 else 'after']))
            if len(raw) not in (64,576):continue
            header=struct.unpack_from('<4I4QIiQ',raw)
            if header[2] not in (5,6):continue
            if row['op']==53 and len(raw)==576:
                op,path=wide.old.fs_request_frame(raw[64:])
                if path==b'/largetest.prg':sent.append((header,raw[64:]))
            elif header[3]==1:
                key=header[4:6];check.need(key not in replies,'BV unique negative reply');replies[key]=(header,raw[64:])
        stats=[r for r in sent if r[0][2]==5];reads=[r for r in sent if r[0][2]==6]
        check.need(len(stats)==1 and stats[0][0][4:6] in replies,'BV one actual oversized/unsupported STAT')
        stat=replies[stats[0][0][4:6]]
        check.need(stat[0][9]==0 and struct.unpack_from('<I',stat[1],476)[0]==len(files['largetest.prg']),
                   'BV actual negative inode size')
        if spec[4]=='oversize':
            check.need(len(files['largetest.prg'])==1048577 and not reads,'BV oversized STAT rejects before READ')
            continue
        position=0
        check.need(len(reads)==274432//256+1,'BV exact single-indirect prefix plus rejection')
        for index,(header,request) in enumerate(reads):
            check.need(header[4]==stats[0][0][4] and header[4:6] in replies,'BV negative capture same generation')
            response,answer=replies[header[4:6]]
            check.need(struct.unpack_from('<2I',request,24)==(position,256),'BV negative contiguous prefix')
            if index==len(reads)-1:
                check.need(response[9]==-110 and not answer and position==274432,'BV unsupported map rejects before publication')
            else:
                check.need(response[9]==0 and struct.unpack_from('<I',answer,32)[0]==256 and
                           answer[228:484]==files['largetest.prg'][position:position+256],'BV actual immutable negative prefix')
                position+=256

def normal_hardware_namespace(binding,*,observer_batch=False,spec=None):
    """Reuse the accepted WHPX transport/bootstrap without text-app probes."""
    import inspect
    import run_qemu_x86_64_text_runtime as text_runtime
    source=inspect.getsource(text_runtime.hardware_namespace)
    source=wide.replace(source,
        '            code=replace(code,"super().__init__(\'*\'+hex(CONFIG[\'text_checkpoint\']),internal=True)",\n'
        '                "super().__init__(\'*\'+hex(CONFIG[\'text_checkpoint\']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)")\n','')
    namespace=dict(vars(text_runtime),namespace=lambda label:case_namespace(CASES[0] if spec is None else spec))
    if observer_batch:namespace['portable_toolchain']=observer_toolchain
    exec(compile(source,'<BV-bound-existing-WHPX-transport>','exec'),namespace)
    return namespace['hardware_namespace']('large-file-reference',toolchain=binding)

def timer_failure_probe(code):
    """Read-only probes on failed timer paths; never alter an acceptance result."""
    extra=r'''
class BVTimerFailure(gdb.Breakpoint):
    count=0
    def __init__(self,name):
        super().__init__('*'+hex(S[name]),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
        self.stage=name
    def stop(self):
        BVTimerFailure.count+=1
        assert BVTimerFailure.count<=4
        row=dict(stage=self.stage,registers={n:reg(n) for n in
            ('rax','rdi','rsi','rdx','rcx','r8','r9','rip','rsp','eflags','cr3')},
            mode=mem(S['timer_mode'],1).hex(),active=mem(S['timer_active'],1).hex(),
            deadline=q(S['timer_deadline']),ticks=q(S['timer_runtime_ticks']),
            eois=q(S['timer_runtime_eois']),slot=d(S['scheduler_current_slot']))
        with (OUT/'timer-failure.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        if self.stage=='x86_64_timer_interrupt64.shell_invalid':gdb.execute('quit 74')
        return False
for bv_failure_site in ('timer_runtime_progress64.fail','x86_64_timer_interrupt64.shell_clock_invalid',
                        'x86_64_timer_interrupt64.shell_invalid'):
    BVTimerFailure(bv_failure_site)
'''
    return wide.replace(code,'\nend\ncontinue\n','\n'+extra+'\nend\ncontinue\n')

def profile_observer(code,stops):
    if type(stops) is not int or not 1<=stops<=1024:raise ValueError('BV diagnostic profile stop bound')
    code=wide.replace(code,'def command_probe_observe(self):',
        'def command_probe_observe(self):\n'
        '    global bv_profile_stops\n'
        '    bv_profile_stops+=1\n'
        f'    if bv_profile_stops=={stops}:\n'
        '        bv_profile.disable()\n'
        "        bv_profile.dump_stats(str(OUT/'observer-profile.pstats'))\n"
        "        gdb.execute('quit 75')\n"
        '        return False')
    return wide.replace(code,'\nend\ncontinue\n',
        '\nimport cProfile\nbv_profile_stops=0\nbv_profile=cProfile.Profile()\nbv_profile.enable()\nend\ncontinue\n')

NATIVE_REPLAY=r'''
native_names=('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15','eflags','cr3')
native_five_sites=False
native_limit=160 if native_five_sites else 32
native_site_names=('request','denied','return')+(('start','pio') if native_five_sites else ())
native_sites=tuple(S['native_session_probe_'+name+'_site64'] for name in native_site_names)
native_targets=[]
for begin,end,helper in (
    (S['process_run_syscall64'],S['process_run_syscall64.denied'],S['native_session_probe_request64']),
    (S['process_run_syscall64.denied'],S['process_run_syscall64.denied']+5,S['native_session_probe_denied64']),
    (S['process_run_resume64'],S['process_run_resume64']+5,S['native_session_probe_return64']),
)+((
    (S['scheduler_enter_task64'],S['scheduler_enter_task64']+1024,S['native_session_probe_start64']),
    (S['process_run_resume64'],S['process_run_resume64']+5,S['native_session_probe_return64']),
) if native_five_sites else ()):
    assert 5<=end-begin<=1024
    raw=mem(begin,end-begin)
    found=[begin+i+5 for i in range(len(raw)-4) if raw[i]==0xe8 and
           begin+i+5+struct.unpack_from('<i',raw,i+1)[0]==helper]
    assert len(found)==1,'native exact bound CALL target'
    native_targets.append(found[0])
native_parameters=[2 if native_five_sites else 1]
for site,target in zip(native_sites,native_targets):native_parameters.extend((site,target))
native_parameters.extend((S['syscall_rax'],S['scheduler_current_slot'],S['scheduler_tasks']))
native_query='qreist-native:'+';'.join('%x'%n for n in native_parameters)
native_reply=gdb.execute('maintenance packet '+native_query,to_string=True)
assert len(native_reply)<=1024
with (OUT/'native-admission.json').open('x') as stream:
    points=gdb.execute('maintenance info breakpoints',to_string=True)
    assert len(points)<=32768
    json.dump(dict(query=native_query,reply=native_reply,breakpoints=points,
                   rip=reg('rip'),cr3=reg('cr3')),stream)
assert native_reply.splitlines()==['sending: '+native_query,'received: "OK"'],('native verifier admission',native_reply)
native_stream=(OUT/'native-ram.bin').open('rb')
native_reader=NativeSnapshot(native_stream,native_sites,native_targets)
native_inside=False
native_calibrations=0
native_explicit_steps=0
native_hooks={h.name:h for h in gdb.breakpoints() if isinstance(h,ColdHook)}
assert len(native_hooks)==3
native_acknowledged=[0]*8
if native_five_sites:
    for name,callback in (('start',start),('pio',pio_capture_full)):
        matches=[h for h in gdb.breakpoints() if isinstance(h,Hook) and h.fn is callback]
        assert len(matches)==1
        h=matches[0];h.name='native_session_probe_'+name+'_site64';h.callback=callback
        h.read_only=lambda h=h:ColdHook.read_only(h)
        h.commands='silent\npython native_extra_dispatch()\ncontinue'
        native_hooks[h.name]=h
assert len(native_hooks)==len(native_sites)
native_old_dispatch=stepped_probe_dispatch

def native_registers(row):
    result=dict(zip(native_names,row['registers']))
    result.update(rip=row['rip'],rsp=row['rsp'])
    return result

def native_emit_step(before,after):
    global cold_step_count
    assert 0<=cold_step_count<262144
    cold_step_count+=1
    row=dict(step=cold_step_count,site=native_sites.index(before['rip']),
             pc=before['rip'],target=before['target'],sp=before['rsp'],after_sp=after['rsp'])
    gdb.write('COLD_STEP_V1 '+json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')

def native_available():
    extent=(OUT/'native-ram.bin').stat().st_size
    assert native_reader.used<=extent<=NativeSnapshot.LIMIT
    return extent-native_reader.used

import os as native_os,time as native_time
native_drain_timing=native_os.environ.get('REIST_BV_DRAIN_TIMING')=='1'
native_drain_timing_rows=0
def native_drain():
    global native_inside,callbacks,native_drain_timing_rows
    if native_inside:return
    timing_start=native_time.monotonic() if native_drain_timing else 0
    timing_first=native_reader.sequence
    native_inside=True
    try:
        for _ in range(262144):
            if not native_available():return
            before=native_reader.next()
            assert before['phase']==0 and before['sequence']>native_limit,'calibration requires live stop'
            hook=native_hooks['native_session_probe_'+native_site_names[native_sites.index(before['rip'])]+'_site64']
            saved_mem,saved_reg=globals()['mem'],globals()['reg']
            registers=native_registers(before)
            globals()['mem']=native_reader.memory
            globals()['reg']=lambda name:registers[name]
            try:
                slot=d(S['scheduler_current_slot']);assert slot<8
                if native_sites.index(before['rip']) in (2,3):
                    assert pending.get(task(slot)[1],{}).get('op') not in (15,20,132),'controlled return stays live'
                else:assert q(S['syscall_rax']) not in (15,20,132),'CREATE entry stays live; console acknowledged live'
                callbacks+=1;assert callbacks<=262144
                hook.read_only()
            finally:globals()['mem'],globals()['reg']=saved_mem,saved_reg
            after=native_reader.next()
            assert after['phase']==1 and after['sequence']==before['sequence']
            native_emit_step(before,after)
        raise AssertionError('native drain capacity')
    finally:
        native_inside=False
        if native_drain_timing and native_reader.sequence>timing_first and native_drain_timing_rows<128:
            native_drain_timing_rows+=1
            row=dict(first=timing_first,end=native_reader.sequence,
                     seconds=native_time.monotonic()-timing_start)
            with (OUT/'native-drain-timing.jsonl').open('a') as stream:
                stream.write(json.dumps(row)+'\n')

def native_dispatch():
    global native_inside,native_calibrations,native_explicit_steps
    try:
        if not native_available() or native_calibrations==native_limit:
            native_drain()
            result=native_old_dispatch()
            native_explicit_steps+=1
            return result
        assert not native_inside and len(service_stops.pending)==1
        native_inside=True
        before=native_reader.next()
        assert before['phase']==0 and before['sequence']==native_calibrations+1<=native_limit
        hook=service_stops.pending[0]
        assert isinstance(hook,(ColdHook,Hook)) and hook.name in native_hooks and S[hook.name]==before['rip']
        registers=native_registers(before)
        saved_mem,saved_reg=globals()['mem'],globals()['reg']
        actual={name:saved_reg(name) for name in registers}
        assert actual==registers,'native live before-register equality'
        with (OUT/'native-calibration-progress.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(sequence=before['sequence'],stage='source',
                                         registers=actual))+'\n')
        reads=[]
        def compared(address,size):
            raw=saved_mem(address,size)
            assert raw==native_reader.memory(address,size),'native live before-RAM equality'
            assert len(reads)<4096,'native calibration read capacity'
            reads.append((address,raw.hex()))
            return raw
        globals()['mem']=compared
        try:service_stops.drain()
        finally:globals()['mem']=saved_mem
        assert not service_stops.pending and not service_stops.running and not service_stops.failed
        assert {name:saved_reg(name) for name in registers}==registers
        # Match the proven old dispatch: GDB must not TF-step its own source
        # breakpoint. QEMU's separately registered real target stays armed.
        hook.enabled=False
        try:output=gdb.execute('continue',to_string=True)
        finally:hook.enabled=True
        assert len(output)<=512
        after=native_reader.next()
        assert after['phase']==1 and after['sequence']==before['sequence']
        actual_after={name:saved_reg(name) for name in registers}
        assert actual_after==native_registers(after),'native actual target live-register equality'
        after_reads=[]
        for address,encoded in reads:
            raw=saved_mem(address,len(encoded)//2)
            assert raw==native_reader.memory(address,len(raw)),'native live after-RAM equality'
            after_reads.append((address,raw.hex()))
        assert not service_stops.pending and not service_stops.failed
        with (OUT/'native-equivalence.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(sequence=before['sequence'],before=actual,
                after=actual_after,reads=reads,after_reads=after_reads))+'\n')
        native_calibrations+=1
        native_emit_step(before,after)
        native_explicit_steps+=1
    except BaseException as error:
        emit('OBSERVER_FAIL',where='native calibration',error=repr(error))
        gdb.execute('quit 71')
        raise
    finally:native_inside=False

def native_extra_dispatch():
    if native_calibrations<native_limit and native_available():return native_dispatch()
    native_drain()
    service_stops.drain()

def native_ack_start(hook):
    if not native_five_sites or getattr(hook,'fn',None) is not start:return
    slot=d(S['scheduler_current_slot']);assert 0<=slot<8
    gen=task(slot)[1]
    assert gen in starts and starts[gen]['live'] and starts[gen]['slot']==slot
    if native_acknowledged[slot]==gen:return
    assert native_acknowledged[slot]<gen
    query='qreist-start:1;%x;%x'%(slot,gen)
    reply=gdb.execute('maintenance packet '+query,to_string=True)
    assert len(reply)<=512 and reply.splitlines()==['sending: '+query,'received: "OK"'],'native exact first-start acknowledgement'
    native_acknowledged[slot]=gen

def native_wrap_observe(original):
    def observe(self):
        try:native_drain()
        except BaseException as error:
            emit('OBSERVER_FAIL',where='native replay',error=repr(error))
            gdb.execute('quit 71')
            raise
        result=original(self)
        native_ack_start(self)
        return result
    return observe

Hook.observe=native_wrap_observe(Hook.observe)
ReleaseEnd.observe=native_wrap_observe(ReleaseEnd.observe)
ColdHook.observe=native_wrap_observe(ColdHook.observe)
stepped_probe_dispatch=native_dispatch
'''

def audit_native_calibration(folder,*,deadline=None):
    """Replay the32/160 raw live comparisons independently of GDB callback output."""
    import struct
    folder=Path(folder)
    admission=json.loads((folder/'native-admission.json').read_text())
    query=admission['query']
    check.need(type(query) is str and len(query)<512 and query.startswith('qreist-native:'),'native admission query')
    values=[int(v,16) for v in query.split(':',1)[1].split(';')]
    check.need((len(values),values[0]) in ((10,1),(14,2)),'native admission parameters')
    count=3 if values[0]==1 else 5;limit=32 if count==3 else 160;observed=set()
    check.need(admission['reply'].splitlines()==['sending: '+query,'received: "OK"'],'native admitted reply')
    path=folder/'native-equivalence.jsonl'
    check.need(path.stat().st_size<=8*1024*1024,'native calibration log capacity')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    check.need(len(rows)==limit,'native complete live comparisons')
    names=('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15','eflags','cr3')
    reads=0
    with (folder/'native-ram.bin').open('rb') as stream:
        reader=NativeSnapshot(stream,values[1:1+count*2:2],values[2:1+count*2:2])
        for seq,row in enumerate(rows,1):
            check.need(type(row.get('sequence')) is int and row['sequence']==seq,'native calibration chronology')
            for phase,key in ((0,'before'),(1,'after')):
                if deadline is not None:check.need(time.monotonic()<deadline,'native calibration audit deadline')
                state=reader.next()
                if phase==0:observed.add(state['rip'])
                expected=dict(zip(names,state['registers']),rip=state['rip'],rsp=state['rsp'])
                check.need((state['sequence'],state['phase'])==(seq,phase),'native calibration frame binding')
                check.need(type(row.get(key)) is dict and row[key]==expected and
                           all(type(v) is int for v in row[key].values()),'native calibration raw CPU equality')
                spans=row['reads' if phase==0 else 'after_reads']
                check.need(type(spans) is list and 0<len(spans)<=4096,'native calibration RAM count')
                for address,encoded in spans:
                    check.need(type(address) is int and type(encoded) is str and
                               len(encoded)<=65534 and len(encoded)%2==0,'native calibration RAM range')
                    raw=bytes.fromhex(encoded)
                    check.need(raw.hex()==encoded and reader.memory(address,len(raw))==raw,'native calibration raw RAM equality')
                    reads+=1
        consumed=reader.used
    if count==5:check.need(observed==set(values[1:11:2]),'native five-site live coverage')
    return dict(passed=True,qualification=False,returns=limit,register_values=limit*2*19,
                ram_reads=reads,trace_prefix_bytes=consumed)

def native_probe_targets(image,symbols):
    """Bind five continuations to executable ELF32 container bytes, not receipts."""
    import struct
    check.need(type(image) is bytes and 52<=len(image)<=4*1024*1024 and
               image[:7]==b'\x7fELF\x01\x01\x01','native kernel ELF32 container')
    offset=struct.unpack_from('<I',image,28)[0]
    size,count=struct.unpack_from('<HH',image,42)
    check.need(size==32 and 1<=count<=16 and 52<=offset<=len(image)-32*count,
               'native kernel program headers')
    segments=[]
    for n in range(count):
        kind,pos,va,pa,length,memory,flags,align=struct.unpack_from('<8I',image,offset+n*32)
        if kind!=1:continue
        check.need(pos<=len(image) and length<=len(image)-pos and length<=memory and
                   va+memory<=1<<32,'native kernel segment bounds')
        if flags&1:segments.append((va,pos,length))
    def read(address,length):
        address-=0xffffffff80000000
        matches=[image[pos+address-va:pos+address-va+length] for va,pos,n in segments
                 if va<=address and address+length<=va+n]
        check.need(len(matches)==1,'native unique executable range')
        return matches[0]
    s=symbols
    routes=((s['process_run_syscall64'],s['process_run_syscall64.denied'],s['native_session_probe_request64']),
            (s['process_run_syscall64.denied'],s['process_run_syscall64.denied']+5,s['native_session_probe_denied64']),
            (s['process_run_resume64'],s['process_run_resume64']+5,s['native_session_probe_return64']),
            (s['scheduler_enter_task64'],s['scheduler_enter_task64']+1024,s['native_session_probe_start64']),
            (s['process_run_resume64'],s['process_run_resume64']+5,s['native_session_probe_return64']))
    result=[]
    for name,(start,end,helper) in zip(('request','denied','return','start','pio'),routes):
        check.need(5<=end-start<=1024,'native bounded CALL search')
        raw=read(start,end-start)
        matches=[start+n+5 for n in range(len(raw)-4) if raw[n]==0xe8 and
                 start+n+5+struct.unpack_from('<i',raw,n+1)[0]==helper]
        check.need(len(matches)==1,'native exact executable CALL continuation')
        check.need(read(s['native_session_probe_'+name+'_site64'],1)==b'\xc3','native actual RET source')
        result.append(matches[0])
    return tuple(result)


def validate_native_probe_steps(trace,symbols,targets):
    """Appended five-site receipt version; never interpreted as old v1 evidence."""
    total=0;ended=False;seen=set()
    names=('request','denied','return','start','pio')
    check.need(len(targets)==5 and targets[2]==targets[4],'native five continuation binding')
    for line in trace.splitlines():
        if line.startswith('NATIVE_STEP_V2 '):
            encoded=line[len('NATIVE_STEP_V2 '):]
            check.need(not ended and len(encoded)<=192 and total<262144,'native bounded step sequence')
            row=json.loads(encoded)
            check.need(type(row) is dict and set(row)=={'step','site','pc','target','sp','after_sp'} and
                       all(type(v) is int and 0<=v<1<<64 for v in row.values()),'native step fields')
            total+=1;site=row['site']
            check.need(row['step']==total and 0<=site<5,'native step sequence/site')
            check.need(row['pc']==symbols['native_session_probe_'+names[site]+'_site64'] and
                       row['target']==targets[site],'native bound step route')
            check.need(row['sp']%8==0 and row['sp']>=0xffffffff80000000 and
                       row['after_sp']==row['sp']+8,'native actual RET stack')
            seen.add(site)
        elif line.startswith('NATIVE_STEP_END_V2 '):
            check.need(not ended and total>0 and line=='NATIVE_STEP_END_V2 '+str(total),
                       'native complete end count')
            ended=True
        elif line.startswith(('NATIVE_STEP','COLD_STEP')):
            raise ValueError('native unknown/mixed step receipt version')
    check.need(ended and seen==set(range(5)),'native complete five-site step proof')
    return total


def native_observer(code,profile_stops=0,*,five_sites=False):
    """Install after the unchanged binary reader, before the bounded outer loop."""
    import inspect
    check.need('bv_batch=' not in code,'native replay cannot read live batch RAM')
    marker='\npython\n\ndef stepped_probe_loop():'
    check.need(code.count(marker)==1,'native final observer insertion')
    support=inspect.getsource(NativeSnapshot)+'\n'+NATIVE_REPLAY
    if profile_stops:
        check.need(type(profile_stops) is int and 1<=profile_stops<=8192,'native profile bound')
        support+='\nimport cProfile\nnative_profile=cProfile.Profile()\nnative_profile.enable()\n'
        support=wide.replace(support,"    gdb.write('COLD_STEP_V1 '+json.dumps(row,sort_keys=True,separators=(',',':'))+'\\n')",
            "    gdb.write('COLD_STEP_V1 '+json.dumps(row,sort_keys=True,separators=(',',':'))+'\\n')\n"
            f"    if cold_step_count>={profile_stops}:\n"
            "        native_profile.disable()\n"
            "        native_profile.dump_stats(str(OUT/'native-profile.pstats'))\n"
            "        gdb.execute('quit 75')\n")
    check.need(type(five_sites) is bool,'native five-site selector')
    if five_sites:
        support=wide.replace(support,'native_five_sites=False','native_five_sites=True')
        support=support.replace("'COLD_STEP_V1 '","'NATIVE_STEP_V2 '")
        code=code.replace("'COLD_STEP_V1 '","'NATIVE_STEP_V2 '")
        code=wide.replace(code,"'COLD_STEP_END_V1 '","'NATIVE_STEP_END_V2 '")
        code=code.replace("self.name.replace('_site64','64')",
            "('native_session_probe_return64' if self.name=='native_session_probe_pio_site64' else self.name.replace('_site64','64'))")
    code=code.replace(marker,'\npython\n'+support+'\n\ndef stepped_probe_loop():')
    code=wide.replace(code,'            before=cold_step_count','            before=native_explicit_steps')
    return wide.replace(code,
        "assert cold_step_count==before+1,'exactly one verified RET before next continue'",
        "assert native_explicit_steps==before+1 and cold_step_count<=262144,'exactly one explicit GDB/calibration RET before next continue'")

def raw_diagnostic(image,folder,*,hardware_binding=None,failure_probe=False,profile_stops=0,observer_batch=False,observer_native=False,observer_sites=3):
    """One approved 600s two-root diagnosis with full independent replay."""
    started=time.monotonic() # Include binding/configuration in the same lease.
    import types,os
    import build_x86_64_large_file_media as media
    image=Path(image).resolve();folder=Path(folder).absolute()
    check.need(image.is_relative_to(ROOT/'build') and folder==folder.resolve() and
        folder.is_relative_to(ROOT/'build/codex-agent') and not folder.exists(),'BV fresh raw diagnostic scope')
    check.need(observer_sites in (3,5) and (observer_sites==3 or observer_native),'BV native site selection')
    check.need(not (observer_batch and observer_native),'BV one observation transport')
    check.need(not (observer_batch or observer_native) or hardware_binding is not None,'BV observer requires bound QEMU')
    module=normal_namespace() if hardware_binding is None else normal_hardware_namespace(hardware_binding,observer_batch=observer_batch or observer_native)
    config,records,files=image_config(image)
    config.update(app_case='ext2-2k',large_case_ram=4096);module.app_files=files
    if observer_sites==5:
        targets=native_probe_targets(image.read_bytes(),config['s'])
        module.validate_probe_steps=lambda trace,symbols:validate_native_probe_steps(trace,symbols,targets)
    folder.mkdir(parents=True)
    result=dict(qualification=False,passed=False,closed=False,limit=600)
    previous_batch=os.environ.get('REIST_BV_OBSERVER')
    previous_native={name:os.environ.get(name) for name in ('REIST_BV_NATIVE','REIST_BV_NATIVE_TRACE')}
    try:
        code=module.observer(config,records,folder,0,3)
        if observer_batch:
            code=batch_observer(code)
            os.environ['REIST_BV_OBSERVER']='1'
        if failure_probe:code=timer_failure_probe(code)
        if profile_stops and not observer_native:code=profile_observer(code,profile_stops)
        cls=wide.old.file.pio.Fixture;fixture=cls.__new__(cls)
        fixture.started=started;fixture.wide_full=False
        fixture.expected=lambda:media.image('ext2-2k',files)
        fixture.run=types.MethodType(large_fixture_run,fixture)
        cls.__init__(fixture,folder,filesystem='ext2-2k',file_program=files['boot.prg'])
        capture=module.stepped_capture_namespace(started)
        if observer_native:
            os.environ['REIST_BV_NATIVE']='1'
            os.environ['REIST_BV_NATIVE_TRACE']=str(folder/'native-ram.bin')
            original_tail=capture['session_step_loop']
            capture['session_step_loop']=lambda script:native_observer(original_tail(script),profile_stops,five_sites=observer_sites==5)
        capture['capture'](image,folder,code,4096,fixture,
            binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True,
            console_input=module.input_plan(0))
        check.need(time.monotonic()-started<=600,'BV complete diagnostic guest lease')
        if observer_native:result['native_calibration']=audit_native_calibration(folder,deadline=started+600)
        result['proof']=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,3,files)
        check.need(time.monotonic()-started<=600,'BV complete replay lease')
        result['passed']=True
    except BaseException as error:
        result['error']=repr(error);raise
    finally:
        if observer_batch:
            if previous_batch is None:os.environ.pop('REIST_BV_OBSERVER',None)
            else:os.environ['REIST_BV_OBSERVER']=previous_batch
        if observer_native:
            for name,value in previous_native.items():
                if value is None:os.environ.pop(name,None)
                else:os.environ[name]=value
        result.update(elapsed=time.monotonic()-started,closed=True)
        (folder/'diagnostic.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def bootstrap_marker(folder):
    result=[];total=0
    with (Path(folder)/'frame-trace.log').open('rb') as stream:
        for line in stream:
            total+=len(line)
            check.need(total<=256*1024*1024 and len(line)<=1024*1024,'BV bounded bootstrap transcript')
            if line.startswith(b'MATH_HARDWARE_BOOTSTRAP_V1 '):result.append(line.decode('ascii'))
    return ''.join(result)

def hardware_proof(folder,config):
    """Keep the accepted bootstrap proof; numeric checkpoints do not exist here."""
    import inspect
    import run_qemu_x86_64_math_runtime as hardware
    source=inspect.getsource(hardware.validate_hardware_bootstrap)
    source=wide.replace(source,"trace=wide.decode_evidence((folder/'frame-trace.log').read_text(encoding='utf-8'))",
                        'trace=bootstrap_marker(folder)')
    begin=source.index("        debug_file=folder/'math-checkpoint-debug.jsonl'")
    end=source.index('    return dict(',begin);source=source[:begin]+source[end:]
    namespace=dict(vars(hardware),bootstrap_marker=bootstrap_marker)
    exec(compile(source,'<BV-bootstrap-proof>','exec'),namespace)
    return namespace['validate_hardware_bootstrap'](folder,config)

def signed_capture(module,medium):
    """Boot the signed secondary disk, then use the same bounded raw observer."""
    import inspect,linecache
    source=inspect.getsource(module.capture_namespace)
    marker='        source=inspect.getsource(function)'
    arguments=bios.boot_arguments(medium.overlay,'hdd')
    addition=(marker+'\n        if function is boot._capture_run:\n'
              '            source=once(source,"\'-kernel\',str(image),", "")\n'
              '            source=once(source,"    command+=binary_arguments",'+
              repr('    command+=binary_arguments\n    command+='+repr(arguments))+')')
    source=wide.replace(source,marker,addition);filename='<BV-signed-BIOS-capture>'
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    exec(compile(source,filename,'exec'),module.__dict__)

def replay_case(image,folder,spec):
    image=Path(image);folder=Path(folder);module=case_namespace(spec)
    config,records,files=image_config(image);files=case_files(spec,files)
    config.update(app_case=spec[0],large_case_ram=spec[3]);module.app_files=files
    targets=native_probe_targets(image.read_bytes(),config['s'])
    module.validate_probe_steps=lambda trace,symbols:validate_native_probe_steps(trace,symbols,targets)
    return module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),spec[1],spec[2],files)

def run_case(image,folder,spec,binding,*,signed_package=None,qualification=True):
    """Fresh bounded complete two-root execution; every failure stays recorded."""
    import os,types
    started=time.monotonic();image=Path(image).resolve();folder=Path(folder).absolute()
    check.need(spec in CASES and type(qualification) is bool and not folder.exists() and
               folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent'),'BV fresh declared guest')
    check.need(signed_package is None or spec==CASES[0],'BV signed reference only')
    module=normal_hardware_namespace(binding,observer_batch=True,spec=spec)
    config,records,files=image_config(image);files=case_files(spec,files)
    config.update(app_case=spec[0],large_case_ram=spec[3]);module.app_files=files
    targets=native_probe_targets(image.read_bytes(),config['s'])
    module.validate_probe_steps=lambda trace,symbols:validate_native_probe_steps(trace,symbols,targets)
    folder.mkdir(parents=True)
    row=dict(label=spec[0],case=spec[1],layout=spec[2],ram=spec[3],mode=spec[4],limit=600,
             qualification=qualification,passed=False,closed=False,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    (folder/'started.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    previous={name:os.environ.get(name) for name in ('REIST_BV_NATIVE','REIST_BV_NATIVE_TRACE')};medium=None
    try:
        if signed_package is not None:
            package=check.verify(Path(signed_package))
            check.need((package/check.KERNEL).read_bytes()==image.read_bytes(),'BV signed exact executing kernel')
            medium=bios.BootMedium(package/'reist-x86_64.img',folder/'boot-medium','hdd','normal',started+600)
            medium.verify('before');signed_capture(module,medium)
        code=module.observer(config,records,folder,spec[1],spec[2])
        cls=wide.old.file.pio.Fixture;fixture=cls.__new__(cls)
        fixture.started=started;fixture.wide_full=False;fixture.expected=lambda:case_medium(spec,files)
        fixture.run=types.MethodType(large_fixture_run,fixture)
        cls.__init__(fixture,folder,filesystem=wide.media.LAYOUTS[spec[2]],file_program=files['boot.prg'])
        capture=module.stepped_capture_namespace(started);original=capture['session_step_loop']
        capture['session_step_loop']=lambda script:native_observer(original(script),five_sites=True)
        os.environ['REIST_BV_NATIVE']='1';os.environ['REIST_BV_NATIVE_TRACE']=str(folder/'native-ram.bin')
        capture['capture'](image,folder,code,spec[3],fixture,binary_memory='equivalence',diagnostic_metrics=True,
                           service_pio_budget=True,console_input=module.input_plan(spec[1]))
        if medium is not None:
            medium.verify('after');bios.validate_bios((folder/'guest.log').read_text(encoding='ascii'),'hdd','normal')
            row['signed']=True
        row['native_calibration']=audit_native_calibration(folder,deadline=started+600)
        row['hardware']=hardware_proof(folder,config)
        row['proof']=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),spec[1],spec[2],files)
        check.need(time.monotonic()-started<=600,'BV complete guest and replay deadline')
        row['passed']=True
    except BaseException as error:
        row['error']=repr(error);raise
    finally:
        for name,value in previous.items():
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value
        row.update(closed=True,elapsed=time.monotonic()-started)
        (folder/'result.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    return row

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--diagnostic',action='store_true',required=True);p.add_argument('--package',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
 print(json.dumps(diagnostic(a.package,a.directory),indent=2))
