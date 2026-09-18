"""Opt-in host observer transport. No guest writes or general monitor API.

QEMU QMP pmemsave exports physical RAM while the GDB callback owns the stop.
All old observer comparisons consume the returned bytes without alteration.
"""
from pathlib import Path
import hashlib
import json
import socket
import stat
import struct
import time
import uuid

HIGH = 0xffffffff80000000
DM = 0xffff800000000000
MASK = 0x3fffff000
MAX_READ = 270336
MAX_TOTAL = 128 * 1024 * 1024


class QMP:
    def __init__(self, port, name, deadline):
        self.deadline = deadline
        self.pending = bytearray()
        self.identifier = 0
        self.peer = socket.create_connection(('127.0.0.1', port), timeout=self.remaining())
        try:
            self.peer.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            greeting = self.receive(time.monotonic()+.5)
            hello=greeting.get('QMP')
            if not isinstance(hello, dict) or not isinstance(hello.get('version'),dict) or not isinstance(hello.get('capabilities'),list):
                raise ValueError('binary QMP greeting')
            if self.request('qmp_capabilities', {}) != {}:
                raise ValueError('binary QMP negotiation')
            if self.request('query-name', {}) != {'name': name}:
                raise ValueError('binary QMP guest identity')
        except BaseException:
            self.close()
            raise

    def close(self):
        self.peer.close()

    def remaining(self, deadline=None):
        remaining = min(self.deadline, deadline if deadline is not None else self.deadline)-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('binary QMP deadline')
        return min(remaining, .5)

    def receive(self, deadline):
        for _ in range(32):
            if b'\n' in self.pending:
                line, _, rest = self.pending.partition(b'\n')
                self.pending[:] = rest
                result = json.loads(line)
                if not isinstance(result, dict):raise ValueError('binary QMP object')
                return result
            self.peer.settimeout(self.remaining(deadline))
            chunk = self.peer.recv(4096)
            if not chunk:raise OSError('binary QMP closed')
            self.pending.extend(chunk)
            if len(self.pending)>8192:raise ValueError('binary QMP frame bound')
        raise ValueError('binary QMP fragmentation bound')

    def request(self, command, arguments):
        if command not in ('qmp_capabilities','query-name','query-status','pmemsave'):
            raise ValueError('binary QMP command authority')
        self.identifier += 1
        if self.identifier>8192:raise ValueError('binary QMP request bound')
        deadline = time.monotonic()+.5
        raw = json.dumps(dict(execute=command, arguments=arguments, id=self.identifier)).encode()+b'\n'
        if len(raw)>4096:raise ValueError('binary QMP request size')
        self.peer.settimeout(self.remaining(deadline))
        self.peer.sendall(raw)
        for _ in range(32):
            self.remaining(deadline)
            row = self.receive(deadline)
            if 'event' in row and 'id' not in row and 'return' not in row and 'error' not in row:
                if not isinstance(row['event'],str):raise ValueError('binary QMP event')
                continue
            if type(row.get('id')) is not int or row['id']!=self.identifier or 'error' in row or 'return' not in row:
                raise ValueError('binary QMP reply/error')
            return row['return']
        raise ValueError('binary QMP event bound')

    def stopped(self):
        row = self.request('query-status', {})
        if not isinstance(row,dict) or row.get('running') is not False or row.get('status') not in ('paused','debug'):
            raise ValueError('binary QMP guest not stopped')

    def save(self, physical, size, path):
        if self.request('pmemsave', dict(val=physical,size=size,filename=str(path))) != {}:
            raise ValueError('binary QMP export result')


def ram_extent(physical, size, ram):
    if type(ram) is not int or ram not in (4096,8192):raise ValueError('binary native RAM profile')
    if type(physical) is not int or type(size) is not int or not 0<size<=MAX_READ:
        raise ValueError('binary RAM size')
    end=physical+size
    if not (0x100000<=physical<end<=0x8000000 or 0x100000000<=physical<end<=(ram+1024)*1024*1024):
        raise ValueError('binary non-RAM extent')


def translate(address, size, root, ram, read):
    """Validate each requested translation using <=8 fresh exact table spans."""
    if type(address) is not int or not 0<=address<1<<64 or address+size>1<<64:
        raise ValueError('binary canonical range')
    if HIGH<=address<HIGH+0x8000000:physical=address-HIGH
    elif DM<=address<DM+0x400000000:physical=address-DM
    else:raise ValueError('binary alias')
    ram_extent(physical,size,ram)
    if type(root) is not int or root&~MASK or not root:raise ValueError('binary CR3')
    spans=0

    def table_read(table, start, count):
        nonlocal spans
        ram_extent(table,4096,ram)
        spans+=1
        if spans>8 or not 0<=start<512 or not 0<count<=512-start:raise ValueError('binary table spans')
        base=HIGH if table<0x8000000 else DM
        raw=read(base+table+start*8,count*8)
        if len(raw)!=count*8:raise ValueError('binary short table')
        return struct.unpack('<'+'Q'*count,raw)

    def walk(table, shift, va, count):
        first=(va>>shift)&511
        entries=table_read(table,first,((va+count-1)>>shift)-(va>>shift)+1)
        for entry in entries:
            chunk=min(count,(1<<shift)-(va&((1<<shift)-1)))
            # Reserved physical bits and non-present entries fail before export.
            if not entry&1 or entry&0x7ffffffc00000000:raise ValueError('binary table entry')
            if shift==12 or shift==21 and entry&128:
                leaf=entry&MASK
                if shift==21 and leaf&((1<<21)-1):raise ValueError('binary huge alignment')
                mapped=leaf+(va&((1<<shift)-1))
                if mapped!=physical+va-address:raise ValueError('binary translation mismatch')
            else:
                if entry&128:raise ValueError('binary unsupported large page')
                walk(entry&MASK,shift-9,va,chunk)
            va+=chunk;count-=chunk
    walk(root,39,address,size)
    return physical


class Reader:
    def __init__(self, port, name, folder, ram, original, cr3, compare=False, *, service_cpu_budget=False, service_pio_budget=False):
        if type(service_cpu_budget) is not bool:raise ValueError('service CPU host budget opt-in')
        if type(service_pio_budget) is not bool:raise ValueError('service PIO host budget opt-in')
        if service_cpu_budget and service_pio_budget:raise ValueError('exclusive service host budgets')
        self.port=port;self.name=name;self.folder=Path(folder)
        self.ram=ram;self.original=original;self.cr3=cr3;self.compare=compare
        self.deadline=time.monotonic()+(42 if service_pio_budget else 27 if service_cpu_budget else 20)
        self.client=None;self.count=0;self.total=0;self.compared=set();self.failed=False
        self.in_stop=False

    def close(self):
        if self.client is not None:
            client=self.client;self.client=None
            client.close()

    def wrap_stop(self,original):
        def stop(hook):
            if self.in_stop or self.failed:raise ValueError('binary nested/failed stop scope')
            self.in_stop=True
            try:return original(hook)
            except BaseException:
                self.failed=True;raise
            finally:
                self.in_stop=False;self.close()
        return stop

    def read(self, address, size):
        if self.failed:raise ValueError('binary reader already failed')
        try:return self._read(address,size)
        except BaseException:
            self.failed=True
            raise
        finally:
            # A connection may be shared only inside one explicit paused
            # callback; its outer finally closes before GDB can resume.
            # Outside that scope preserve the original per-read lifecycle.
            if self.failed or not self.in_stop:self.close()

    def _read(self, address, size):
        if type(size) is not int or size<0 or size>MAX_READ:raise ValueError('binary read bound')
        if size<32768:return self.original(address,size)
        if self.count>=2048 or self.total+size>MAX_TOTAL:raise ValueError('binary dump capacity')
        physical=translate(address,size,self.cr3(),self.ram,self.original)
        path=self.folder/('ram-%04d.bin'%(self.count+1))
        if path.exists() or path.is_symlink():raise ValueError('binary dump already exists')
        if self.client is None:self.client=QMP(self.port,self.name,self.deadline)
        self.client.stopped()
        self.count+=1;self.total+=size
        self.client.save(physical,size,path)
        self.client.stopped()
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size!=size or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('binary dump type/length')
        with path.open('rb') as source:raw=source.read(size+1)
        if len(raw)!=size:raise ValueError('binary dump short/oversize')
        kind='high' if physical>=1<<32 else 'kernel'
        compared=None
        if self.compare and kind not in self.compared:
            if raw!=self.original(address,size):raise ValueError('binary GDB byte mismatch')
            self.compared.add(kind);compared=kind
        row=dict(sequence=self.count,address=address,physical=physical,bytes=size,
                 sha256=hashlib.sha256(raw).hexdigest(),file=path.name,equivalence=compared)
        with (self.folder/'reads.jsonl').open('a',encoding='ascii') as log:log.write(json.dumps(row)+'\n')
        return raw


def configure(code, folder, ram, mode, *, service_cpu_budget=False, service_pio_budget=False):
    """Return fixed QEMU options and an appended reader, original oracle intact."""
    if type(service_cpu_budget) is not bool:raise ValueError('service CPU host budget opt-in')
    if type(service_pio_budget) is not bool:raise ValueError('service PIO host budget opt-in')
    if service_cpu_budget and service_pio_budget:raise ValueError('exclusive service host budgets')
    if mode not in ('full','equivalence') or ram not in (4096,8192):raise ValueError('binary transport mode/profile')
    tail='end\ncontinue\n'
    if not code.endswith(tail) or code.count('def mem(a,n):')!=1:raise ValueError('binary observer shape')
    folder=Path(folder)
    if folder!=folder.resolve() or not folder.is_relative_to(Path(__file__).resolve().parents[1]/'build/codex-agent'):
        raise ValueError('binary evidence scope')
    for parent in (folder,*folder.parents):
        if parent.exists() and getattr(parent.stat(),'st_file_attributes',0)&0x400:raise ValueError('binary evidence reparse')
    out=folder/'binary-memory';out.mkdir()
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    name='reist-memory-'+uuid.uuid4().hex
    setup=('\nimport sys\nsys.path.insert(0,'+repr(str(Path(__file__).resolve().parent))+')\n'
           'from qemu_binary_memory import Reader as BinaryReader\n'
           'binary_reader=BinaryReader('+repr(port)+','+repr(name)+','+repr(str(out))+','+repr(ram)+
           ',mem,lambda:reg("cr3"),'+repr(mode=='equivalence')+(',service_pio_budget=True' if service_pio_budget else ',service_cpu_budget=True' if service_cpu_budget else '')+')\nmem=binary_reader.read\n'
           'Hook.stop=binary_reader.wrap_stop(Hook.stop)\n'
           'ReleaseEnd.stop=binary_reader.wrap_stop(ReleaseEnd.stop)\n')
    return ['-qmp',f'tcp:127.0.0.1:{port},server=on,wait=off','-name',name],code[:-len(tail)]+setup+tail
