"""Bounded graphical sessions, explicit qualification and independent raw replay."""
from pathlib import Path
import argparse,hashlib,json,os,queue,re,shutil,socket,struct,subprocess,threading,time,uuid
import verify_x86_64_graphical_session as verify
import check_x86_64_graphical_media as check
import build_x86_64_c_payload as elf
import run_qemu_x86_64_boot as boot
import run_qemu_x86_64_shell_boot_media as bios
import run_qemu_x86_64_pio as pio
from run_qemu_x86_64_terminal_service import QMP as BaseQMP
from run_qemu_x86_64_display import ppm
ROOT=verify.ROOT
need=verify.need

class QMP(BaseQMP):
    def call(self,op,args):
        need(op in ('qmp_capabilities','query-name','query-status','stop','cont','quit','pmemsave','screendump','input-send-event'),'QMP operation')
        self.seq+=1;deadline=min(self.end,time.monotonic()+2)
        need(self.seq<=256 and time.monotonic()<deadline,'QMP request budget')
        self.sock.sendall((json.dumps({'execute':op,'arguments':args,'id':self.seq})+'\n').encode())
        original_end=self.end;self.end=deadline
        try:
            for _ in range(8224):
                need(time.monotonic()<deadline,'QMP command deadline')
                row=self.read()
                if 'event' in row:
                    need(row['event'] in ('STOP','RESUME'),'unexpected QMP notification')
                    continue
                need(row.get('id')==self.seq and 'return' in row and 'error' not in row,'QMP response '+str(row))
                return row['return']
            raise ValueError('QMP notification capacity')
        finally:self.end=original_end

class Data(pio.Fixture):
    def __init__(self,folder,data,end):
        need(type(data) is bytes and len(data)==1048576,'graphical volume size')
        self.data=data;self.end=end
        super().__init__(folder,filesystem='ext2-1k')
    def expected(self):return self.data
    def run(self,*args):
        remaining=self.end-time.monotonic();need(remaining>0,'data tool deadline')
        r=subprocess.run([str(self.tool),*args],cwd=ROOT,capture_output=True,text=True,
            timeout=min(10,remaining),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.commands.append(dict(args=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (self.folder/'media-commands.json').write_text(json.dumps(self.commands,indent=2),encoding='utf-8')
        need(r.returncode==0,'data tool: '+r.stderr[-1000:]);return r.stdout

SNAPSHOTS=(('tasks','scheduler_tasks',8192),('profiles','family_profiles',256),
    ('family','family_records',512),('display','native_display_state',128),
    ('input','native_input_state',128),('terminal-service','native_terminal_service_state',64),
    ('terminal-lease','native_terminal_state',24),('terminal-proposal','native_terminal_service_proposal',72),
    ('display-commits','native_display_commits',8),('input-transfers','native_input_transfers',8),
    ('service-acquisitions','native_terminal_service_acquisitions',8))

CASES=(('healthy-hdd',0,'hdd',4096),('healthy-floppy',0,'floppy',8192),
       ('focus-capture',0,'hdd',4096),
       *((name,n,'hdd',4096) for n,name in enumerate((
           'compositor-crash','compositor-hang','compositor-cpu',
           'driver-crash','driver-hang','driver-cpu',
           'client-crash','client-hang','client-cpu','malformed-client',
           'lost-control','active-parent','stale-client','restart-exhaustion',
           'altered-service'),1)))

def reap_records(raw):
    return [struct.unpack('<4I2Q',bytes.fromhex(m.decode())) for m in
            re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',raw)]

def desktop_receipts(raw):
    # The shell may reuse slot4 for cat after GUI retirement. Its distinct
    # generation is outside the initial desktop command's prompt interval.
    intervals=raw.split(b'C:\\>',2)
    need(len(intervals)==3 and intervals[1].startswith(b'desktop\n'),'bounded desktop command interval')
    return reap_records(intervals[1])

def exhaustion_receipts(raw,owner):
    faults=[r for r in desktop_receipts(raw) if r[0]==4]
    need(owner&0xffffffff==4 and raw.split(b'C:\\>',2)[1].count(b'GRAPHICAL_READY\n')==3 and len(faults)==3 and
         faults[0][1]==owner>>32 and faults[0][1]<faults[1][1]<faults[2][1] and
         all(r[2:4]==(134,3) for r in faults),'three actual compositor generations fail before shell returns')
    return faults

def altered_volume(package):
    """Change one loaded service instruction, keeping the on-disk ELF valid."""
    original=(package/'system.ext2').read_bytes();raw=bytearray(original)
    inode=5*1024+16*128 # inode17: sixth directory file, desktop.prg
    first=struct.unpack_from('<I',raw,inode+40)[0]*1024
    need(raw[first:first+7]==b'\x7fELF\x02\x01\x01','service inode executable')
    phoff=struct.unpack_from('<Q',raw,first+32)[0]
    size,count=struct.unpack_from('<2H',raw,first+54);need(size==56 and count<=16,'service ELF headers')
    choices=[]
    for n in range(count):
        kind,flags,offset,va,_,filesz,_,_=struct.unpack_from('<II6Q',raw,first+phoff+n*56)
        if kind==1 and flags==5 and filesz:choices.append(first+offset)
    need(len(choices)==1,'one service executable segment');at=choices[0];raw[at]^=1
    need(sum(a!=b for a,b in zip(original,raw))==1,'sole immutable-file mutation')
    return bytes(raw),dict(offset=at,before=original[at],after=raw[at],
        original_sha256=hashlib.sha256(original).hexdigest(),sha256=hashlib.sha256(raw).hexdigest())

def lifecycle_observer(image,symbols,port,folder,selector):
    """One decisive terminal/validation stop, never per-message tracing."""
    need(selector in range(1,15),'lifecycle selector')
    from run_qemu_x86_64_block_profile import map_symbol
    selected={name:0xffffffff80000000+symbols[name] for name in
        {n for _,n,_ in SNAPSHOTS}|{'family_terminal64.restore','scheduler_current_slot',
        'process_run_receipt','scheduler_cpu_budgets','scheduler_cpu_windows'}}
    client=selector in (10,13);probe=None
    if client:
        bindings=audit_bindings(image)
        choices=list(image.parent.glob('programs-*/desktop.map'));need(len(choices)==1,'one bound compositor map')
        mapping=choices[0];need(verify.digest(mapping)==bindings[4]['map_sha256'],'bound validation site')
        probe=dict(address=map_symbol(mapping,'client_fail'),owners=map_symbol(mapping,'owners'))
    target=0 if selector==12 else 6 if selector in (7,8,9,10,13) else 5 if selector in (4,5,6) else 4
    script=folder/'lifecycle.gdb'
    body=r'''
import gdb,struct,json,pathlib
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(n):return int(gdb.parse_and_eval('$'+n))&((1<<64)-1)
result=dict(passed=False,stops=0)
class Terminal(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(PROBE['address'] if PROBE else S['family_terminal64.restore']),
            internal=True,type=gdb.BP_HARDWARE_BREAKPOINT)
    def stop(self):
        try:
            result['stops']+=1;assert result['stops']<=128
            slot=struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]
            if PROBE:
                if slot!=4:return False
                reason=struct.unpack('<i',struct.pack('<I',reg('rsi')&0xffffffff))[0]
                if reg('rdi')!=0 or reason!=(-22 if SELECTOR==10 else -116):return False
                result.update(reason=reason,client=0,owners=mem(PROBE['owners'],32).hex())
            else:
                receipt=struct.unpack('<4I2Q',mem(S['process_run_receipt'],32))
                if receipt[0]!=TARGET:return False
                assert receipt[1]>0 and receipt[3] in (3,4)
                result['receipt']=receipt
                (FOLDER/'cpu-budgets.bin').write_bytes(mem(S['scheduler_cpu_budgets'],256))
                (FOLDER/'cpu-windows.bin').write_bytes(mem(S['scheduler_cpu_windows'],256))
            result['current_slot']=slot
            for name,symbol,size in SNAPSHOTS:(FOLDER/(name+'.bin')).write_bytes(mem(S[symbol],size))
            result['passed']=True;return True
        except BaseException as error:result['error']=repr(error);return True
Terminal()
(FOLDER/'attached.json').write_text(json.dumps(dict(attached=True)))
'''
    folder.mkdir()
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nimport pathlib\nFOLDER=pathlib.Path({str(folder)!r})\n'+
        f'S={selected!r}\nSNAPSHOTS={SNAPSHOTS!r}\nPROBE={probe!r}\nTARGET={target}\nSELECTOR={selector}\n'+
        body+'\nend\ncontinue\npython\n'+
        "(FOLDER/'result.json').write_text(json.dumps(result))\nend\ndelete breakpoints\ndetach\nquit 0\n",encoding='ascii')
    executable=shutil.which('gdb');need(executable,'lifecycle debugger available')
    command=[executable,'-q','-nx','-batch','-x',str(script)]
    verify.save(folder/'command.json',dict(command=command,tool_sha256=verify.digest(executable),script_sha256=verify.digest(script),probe=probe))
    log=(folder/'observer.log').open('xb')
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return process,log

def state(path,live):
    tasks=(path/'tasks.bin').read_bytes();profiles=(path/'profiles.bin').read_bytes()
    family=(path/'family.bin').read_bytes();root=struct.unpack_from('<Q',tasks,8)[0]<<32
    need(root>0,'live root')
    service=struct.unpack('<8Q',(path/'terminal-service.bin').read_bytes())
    lease=struct.unpack('<3Q',(path/'terminal-lease.bin').read_bytes())
    need(all(service[n]^service[n+4]==2**64-1 for n in range(4)),'protected terminal service')
    need(not any((path/'terminal-proposal.bin').read_bytes()),'scrubbed terminal proposal')
    owners=[]
    common=sum(1<<n for n in (9,22,40,41,42,53))
    for slot in range(4,8):
        owner=(struct.unpack_from('<Q',tasks,slot*1024+8)[0]<<32)|slot
        if live:
            low=common|(1<<54 if slot!=5 else 0)
            if slot==4:low|=sum(1<<n for n in (4,5,15,20,49,52,55,58))
            high=(1<<49)|(1<<63) if slot==4 else 1<<49 if slot==5 else 0
            need(owner>>32>0 and struct.unpack_from('<4Q',profiles,slot*32)==(owner>>32,low,high,0),'exact role profile '+str(slot))
            need(struct.unpack_from('<2Q',family,slot*64)==(owner,root),'exact child relationship')
            owners.append(owner)
        else:
            need(not any(tasks[slot*1024:(slot+1)*1024]) and not any(profiles[slot*32:(slot+1)*32]),'reaped graphical role '+str(slot))
    for name,role in (('display',0),('input',1)):
        values=struct.unpack('<16Q',(path/(name+'.bin')).read_bytes())
        need(all(values[n]^values[n+8]==2**64-1 for n in range(8)),'protected '+name)
        if live:need(values[0]==owners[role] and values[1]==root and values[2]>0 and values[3]==0,'live '+name+' ownership')
        else:need(values[3]==1,'retired '+name)
    if live:
        need(service[:2]==(root,owners[0]) and service[2]>0 and service[3]==0 and lease==(root,owners[0],0),'exclusive compositor lease')
    else:need(service[3]==1 and lease==(root,0,0),'restored root lease')
    return dict(root=root,owners=owners,service_epoch=service[2])

def input_probe(image):
    """Bind an existing function entry to object bytes, map and admitted ELF."""
    from run_qemu_x86_64_block_profile import map_symbol
    from build_x86_64_boot_programs import prepare
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    directories=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    need(len(directories)==1,'unique program catalog');directory=directories[0]
    mapping=directory/'desktop.map';address=map_symbol(mapping,'reist_native_input')
    program=directory/'desktop.prg';raw=program.read_bytes();prepare(raw,[],True)
    obj=directory/'graphical-desktop-2.o';data=obj.read_bytes()
    need(data[:7]==b'\x7fELF\x02\x01\x01' and struct.unpack_from('<2H',data,16)==(1,62),'bound AMD64 relocatable object')
    shoff=struct.unpack_from('<Q',data,40)[0];size,count,names=struct.unpack_from('<3H',data,58)
    need(size==64 and count<256 and 0<names<count,'bounded object sections')
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,shoff+n*64) for n in range(count)]
    table=data[sections[names][4]:sections[names][4]+sections[names][5]]
    def name(section):return table[section[0]:table.index(0,section[0])].decode('ascii')
    matches=[s for s in sections if name(s)=='.text.reist_native_input'];need(len(matches)==1,'actual compiled input function')
    section=matches[0];prefix=data[section[4]:section[4]+32];need(len(prefix)==32 and section[5]>32,'function entry extent')
    for s in sections:
        if s[1]==4 and s[7]==sections.index(section):
            need(s[9]==24 and s[5]%24==0,'bounded function relocations')
            for at in range(s[4],s[4]+s[5],24):need(struct.unpack_from('<Q',data,at)[0]>=32,'relocation-free entry witness')
    phoff=struct.unpack_from('<Q',raw,32)[0];phsize,phcount=struct.unpack_from('<2H',raw,54)
    matches=[]
    for n in range(phcount):
        kind,flags,offset,va,_,filesz,_,_=struct.unpack_from('<II6Q',raw,phoff+n*phsize)
        if kind==1 and flags==5 and va<=address and address+32<=va+filesz:matches.append(raw[offset+address-va:offset+address-va+32])
    need(matches==[prefix],'exact object/linked input entry bytes')
    return dict(address=address,prefix=prefix.hex(),bindings={str(p.relative_to(ROOT)):verify.digest(p) for p in (mapping,program,obj)})

def observer(symbols,port,folder,probe=None):
    """Read successful copyout at its actual address-space boundary only."""
    names={name for _,name,_ in SNAPSHOTS}|{'scheduler_current_slot','scheduler_last_tick',
        'native_display_syscall64.shape_ready','native_display_request','process_ipc_copyout64.message_written'}
    selected={name:0xffffffff80000000+symbols[name] for name in names}
    script=folder/'observer.gdb'
    body=r'''
import gdb,struct,json,pathlib
output=(FOLDER/'ipc.jsonl').open('x',encoding='ascii')
count=0;ready=0;done=False;failure=None
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(n):return int(gdb.parse_and_eval('$'+n))&((1<<64)-1)
def capture(label):
    target=FOLDER/label;target.mkdir()
    for name,symbol,size in SNAPSHOTS:(target/(name+'.bin')).write_bytes(mem(S[symbol],size))
class Copy(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(S['process_ipc_copyout64.message_written']),internal=True)
    def stop(self):
        global count,ready,done,failure
        try:
            count+=1;assert count<=4096 and not reg('eflags')&512
            slot=struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]
            assert slot<8
            if slot not in (0,4,6,7):return False
            task=mem(S['scheduler_tasks']+slot*1024,24);state,generation,cr3=struct.unpack('<3Q',task)
            request=mem(reg('r13'),2136);op,endpoint,destination=struct.unpack_from('<3Q',request)
            capacity=struct.unpack_from('<Q',request,2128)[0]
            assert op in (51,54) and struct.unpack_from('<q',request,40)[0]==0 and state==2 and cr3==reg('cr3')
            wire=request[64:64+capacity];assert mem(destination,capacity)==wire
            assert capacity==140 and struct.unpack_from('<2I',wire)==(1,140)
            length=struct.unpack_from('<I',wire,8)[0]
            assert length in (64,124) and not any(wire[12+length:])
            tick=struct.unpack('<Q',mem(S['scheduler_last_tick'],8))[0]
            row=dict(index=count,slot=slot,generation=generation,endpoint=endpoint,tick=tick,wire=wire.hex())
            output.write(json.dumps(row,separators=(',',':'))+'\n');output.flush()
            payload=wire[12:12+length]
            if slot==0 and length==64 and struct.unpack_from('<4I',payload)==(1,64,4,0):
                ready+=1;capture('trace-ready'+str(ready))
                (FOLDER/'trace-ready.json').write_text(json.dumps(dict(ready=ready,index=count)))
            if slot==0 and length==64 and struct.unpack_from('<4I',payload)==(1,64,6,0):
                done=True;return True
            return False
        except BaseException as error:
            failure=repr(error);return True
class Bind(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(S['native_display_syscall64.shape_ready']),internal=True,type=gdb.BP_HARDWARE_BREAKPOINT)
    def stop(self):
        global failure
        try:
            assert struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]==0
            assert struct.unpack_from('<I',mem(S['native_display_request'],64),8)[0]==1
            self.enabled=False
            if PROBE is None:Copy()
            else:Input()
            return False
        except BaseException as error:failure=repr(error);return True
class Input(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(PROBE['address']),internal=True,type=gdb.BP_HARDWARE_BREAKPOINT)
    def stop(self):
        global count,ready,done,failure
        try:
            slot=struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]
            if slot!=4:return False
            count+=1;assert count<=256
            assert mem(PROBE['address'],32).hex()==PROBE['prefix']
            task=struct.unpack('<3Q',mem(S['scheduler_tasks']+4096,24))
            assert task[0]==2 and task[2]==reg('cr3')
            payload=mem(reg('rsi'),64);event=struct.unpack('<4I4Q3iI',payload)
            assert event[:2]==(2,64) and event[5]==(task[1]<<32|4)
            if not ready:
                ready=1;capture('trace-live1')
            tick=struct.unpack('<Q',mem(S['scheduler_last_tick'],8))[0]
            output.write(json.dumps(dict(index=count,slot=slot,generation=task[1],tick=tick,payload=payload.hex()))+'\n');output.flush()
            if event[2]==2 and event[8]==1 and not event[3]&1:done=True;return True
            return False
        except BaseException as error:failure=repr(error);return True
Bind()
(FOLDER/'observer-attached.json').write_text(json.dumps(dict(attached=True)))
'''
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nS={selected!r}\nSNAPSHOTS={SNAPSHOTS!r}\n'+
        'import pathlib\nFOLDER=pathlib.Path('+repr(str(folder))+')\nPROBE='+repr(probe)+'\n'+body+'\nend\ncontinue\npython\n'+
        "output.close()\n(FOLDER/'observer-result.json').write_text(json.dumps(dict(passed=done and failure is None,records=count,ready=ready,error=failure)))\n"+
        'end\ndelete breakpoints\ndetach\nquit 0\n',encoding='ascii')
    executable=shutil.which('gdb');need(executable,'GDB present')
    log=(folder/'observer.log').open('xb')
    command=[executable,'-q','-nx','-batch','-x',str(script)]
    verify.save(folder/'observer-command.json',dict(command=command,tool_sha256=verify.digest(executable),script_sha256=verify.digest(script)))
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return process,log

def replay_records(rows):
    need(0<len(rows)<=4096,'bounded actual IPC records')
    input_rows=[];local=[];tick=0;index=0
    for row in rows:
        need(row['index']>index and row['tick']>=tick and row['slot'] in (0,4,6,7) and row['generation']>0,'ordered IPC copyouts')
        index=row['index'];tick=row['tick'];wire=bytes.fromhex(row['wire'])
        need(len(wire)==140 and struct.unpack_from('<2I',wire)==(1,140),'canonical IPC envelope')
        length=struct.unpack_from('<I',wire,8)[0];need(length in (64,124) and not any(wire[12+length:]),'canonical IPC padding')
        payload=wire[12:12+length]
        if length==64 and struct.unpack_from('<I',payload)[0]==2:
            event=struct.unpack('<4I4Q3iI',payload)
            need(row['slot']==4 and event[:2]==(2,64) and event[4]&0xffffffff==5 and
                event[5]==(row['generation']<<32|4) and event[4]>>32>0 and event[6]>0 and event[7]==len(input_rows)+1,'actual generation-scoped input sequence')
            if input_rows:need(event[4:7]==input_rows[0][4:7],'one live input generation')
            input_rows.append(event)
        if length==124 and struct.unpack_from('<3I',payload)==(6,124,129):
            need(row['slot'] in (6,7),'local Surface receiver')
            event=struct.unpack_from('<2I4i4I',payload,84)
            need(event[1]>0 and not event[-1],'canonical local event')
            local.append((row['slot'],event))
    need(len(input_rows)>32 and input_rows[0][2]==1,'persistent real received input')
    keys=[e for e in input_rows if e[2]==2 and e[8]==30]
    need(len(keys)==40 and [e[3]&1 for e in keys]==[0,1]*20,'exact real twenty key pairs')
    typed=[(slot,e) for slot,e in local if e[0]==3 and e[8]==ord('a')]
    need(len(typed)==40 and all(slot==6 for slot,_ in typed) and [e[7] for _,e in typed]==[1,0]*20,'focus isolates exact local keyboard deliveries')
    return dict(received_input=len(input_rows),local_keyboard=len(typed))

def replay_healthy(folder):
    rows=[json.loads(line) for line in (folder/'ipc.jsonl').read_text().splitlines()]
    proof=replay_records(rows);proof['ready']=state(folder/'trace-ready1',True)
    result=json.loads((folder/'observer-result.json').read_text())
    need(result['passed'] and result['ready']==1 and result['records']>=len(rows),'complete observer and normal stop')
    return proof

def audit_bindings(image):
    from run_qemu_x86_64_block_profile import map_symbol
    from build_x86_64_boot_programs import prepare
    build=image.parent.parent.name
    need(image.parent.parent.parent==verify.EVIDENCE and re.fullmatch('build[0-9]{2}',build),'scoped audit build receipt')
    receipt=json.loads((verify.EVIDENCE/('development-'+build+'.json')).read_text())
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    choices=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    need(len(choices)==1,'unique audit program set');programs=choices[0];result={}
    for slot,name in ((4,'desktop'),(6,'text'),(7,'paint')):
        mapping=programs/(name+'.map');program=programs/(name+'.prg')
        for path in (mapping,program):
            need(receipt['artifacts'].get(path.relative_to(ROOT).as_posix())==verify.digest(path),'build-bound audit input')
        address=map_symbol(mapping,'reist_native_audit');raw=program.read_bytes();prepare(raw,[],True)
        need(0x410000<=address<address+20544<=0x440000 and address%8==0,'bounded audit location')
        phoff=struct.unpack_from('<Q',raw,32)[0];phsize,count=struct.unpack_from('<2H',raw,54);found=0
        for n in range(count):
            kind,flags,offset,va,_,filesz,memsz,_=struct.unpack_from('<II6Q',raw,phoff+n*phsize)
            if kind==1 and flags==6 and va+filesz<=address and address+20544<=va+memsz:found+=1
        need(found==1,'zero initialized writable audit object')
        result[slot]=dict(address=address,bytes=20544,map_sha256=verify.digest(mapping),program_sha256=verify.digest(program))
        if slot==4 and int(build[5:])>=4:
            result[slot]['readiness']=map_symbol(mapping,'integrated')
            result[slot]['health']=map_symbol(mapping,'health_seq')
    return result

def parse_audit(raw,owner,epoch):
    need(type(raw) is bytes and len(raw)==20544,'fixed audit extent')
    magic,actual_owner,actual_epoch,sequence,version,capacity,size,exhausted,r0,r1=struct.unpack_from('<4Q4I2Q',raw)
    need((magic,actual_owner,actual_epoch,version,capacity,size,exhausted,r0,r1)==
        (0x3154494455414752,owner,epoch,1,128,20544,0,0,0),'exact audit owner/epoch/header')
    need(sequence<=128,'complete non-overwritten diagnostic input window')
    rows=[];last=0
    for n in range(128):
        entry=raw[64+n*160:64+(n+1)*160]
        if n>=sequence:need(not any(entry),'unused audit zero');continue
        serial,ms,endpoint=struct.unpack_from('<2QI',entry);wire=entry[20:]
        need(serial==n+1 and ms>=last and 0<endpoint<=0xffffffff,'committed audit sequence/time/endpoint')
        need(struct.unpack_from('<2I',wire)==(1,140),'actual canonical IPC reply')
        length=struct.unpack_from('<I',wire,8)[0]
        need(length in (64,124) and not any(wire[12+length:]),'actual IPC payload extent/padding')
        need((length==64 and struct.unpack_from('<I',wire,12)[0]==2) or
             (length==124 and struct.unpack_from('<3I',wire,12)==(6,124,129)),'input-only receive history')
        rows.append(dict(sequence=serial,slot=owner&0xffffffff,generation=owner>>32,endpoint=endpoint,tick=ms,wire=wire.hex()));last=ms
    return rows

def capture_audits(image,symbols,port,folder,end,spec=None,*,readiness_only=False):
    need(not folder.exists(),'fresh audit snapshot');folder.mkdir()
    bindings=audit_bindings(image);verify.save(folder/'bindings.json',bindings)
    selected={name:0xffffffff80000000+symbols[name] for _,name,_ in SNAPSHOTS}
    script=folder/'capture.gdb'
    body=r'''
import gdb,struct,json,pathlib
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u64(a):return struct.unpack('<Q',mem(a,8))[0]
DM=0xffff800000000000;MASK=0x3fffff000
def user_bytes(cr3,address,remaining):
    assert 0<remaining<=20544 and 0x410000<=address<address+remaining<=0x440000
    output=bytearray();pages=0
    while remaining:
        pages+=1;assert pages<=7
        root=cr3
        for shift in (39,30,21):
            entry=u64(DM+root+((address>>shift)&511)*8)
            assert entry&7==7 and not entry&128
            root=entry&MASK
        leaf=u64(DM+root+((address>>12)&511)*8)
        assert leaf&~MASK&~0x60==(1<<63)|7
        length=min(remaining,4096-(address&4095))
        output.extend(mem(DM+(leaf&MASK)+(address&4095),length))
        remaining-=length;address+=length
    return output
result=dict(passed=False)
try:
    for name,symbol,size in SNAPSHOTS:(FOLDER/(name+'.bin')).write_bytes(mem(S[symbol],size))
    tasks=(FOLDER/'tasks.bin').read_bytes()
    for slot,binding in BINDINGS.items():
        state,generation,cr3=struct.unpack_from('<3Q',tasks,slot*1024)
        assert state in (1,2,5,6) and generation>0 and cr3 and cr3&MASK==cr3
        output=user_bytes(cr3,binding['address'],binding['bytes'])
        (FOLDER/('audit'+str(slot)+'.bin')).write_bytes(output)
        if 'readiness' in binding:
            (FOLDER/'readiness.bin').write_bytes(user_bytes(cr3,binding['readiness'],4))
            (FOLDER/'health.bin').write_bytes(user_bytes(cr3,binding['health'],32))
    assert tasks==mem(S['scheduler_tasks'],8192)
    result['passed']=True
except BaseException as error:result['error']=repr(error)
(FOLDER/'capture-result.json').write_text(json.dumps(result))
'''
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nS={selected!r}\nBINDINGS={bindings!r}\nSNAPSHOTS={SNAPSHOTS!r}\n'+
        'import pathlib\nFOLDER=pathlib.Path('+repr(str(folder))+')\n'+body+'\nend\ndetach\nquit 0\n',encoding='ascii')
    executable=shutil.which('gdb');need(executable,'snapshot debugger available')
    command=[executable,'-q','-nx','-batch','-x',str(script)]
    verify.save(folder/'command.json',dict(command=command,sha256=verify.digest(executable),script_sha256=verify.digest(script)))
    remaining=min(10,end-5-time.monotonic());need(remaining>0,'audit snapshot deadline')
    with (folder/'capture.log').open('xb') as output:
        process=subprocess.Popen(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:need(process.wait(timeout=remaining)==0,'audit debugger status')
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=1)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=1)
    need(json.loads((folder/'capture-result.json').read_text())['passed'],'audit snapshot: '+(folder/'capture-result.json').read_text())
    return review_audits(folder,spec,readiness_only=readiness_only)

def review_audits(folder,spec=None,*,readiness_only=False):
    proof=state(folder,True);rows=[]
    bindings=json.loads((folder/'bindings.json').read_text())
    if 'readiness' in bindings['4']:
        need((folder/'readiness.bin').read_bytes()==struct.pack('<I',15),'actual reintegrated roles')
        health=struct.unpack('<4Q',(folder/'health.bin').read_bytes())
        need(health[2]>0 and health[3]>0,'actual client health before reintegration')
    for slot in (4,6,7):
        rows.extend(parse_audit((folder/('audit'+str(slot)+'.bin')).read_bytes(),proof['owners'][slot-4],proof['service_epoch']))
    rows.sort(key=lambda row:(row['tick'],row['slot'],row['sequence']))
    for n,row in enumerate(rows,1):row['index']=n
    if readiness_only:
        need('readiness' in bindings['4'],'actual complete readiness witness required')
        return dict(authority=proof,pending_input=len(rows))
    result=replay_records(rows);result['authority']=proof
    if spec is not None:
        received=[r['tick'] for r in rows if r['slot']==4]
        need(received[-1]-received[0]>5000,'actual monotonic input health beyond five seconds')
        result['routing']=replay_routing(rows,spec)
    return result

def replay_routing(rows,spec):
    """Independent fixed-geometry input model, including implicit left grab.

    This oracle does not call the compositor or trust reported success counts.
    Only consecutive pending motion may coalesce under Surface-v6.
    """
    focus=0 if spec[1] in (7,8,9,10,13) else 1
    z=[1-focus,focus];capture=None;x=y=8;buttons=serial=0
    expected=[];actual=[];surface={};pointer=[]
    def emit(slot,kind,button=0,pressed=0,key=0,dx=0,dy=0):
        nonlocal serial
        if slot is None:return
        serial+=1;xx=max(0,min(319,x-(23+240*slot)));yy=max(0,min(191,y-(64+160*slot)))
        if kind==3:xx=yy=0
        expected.append((6+slot,(kind,serial,xx,yy,dx,dy,button,pressed,key,0)))
    def hit():
        for n in reversed(z):
            if 20+240*n<=x<346+240*n and 40+160*n<=y<259+160*n:
                return n if 23+240*n<=x<343+240*n and 64+160*n<=y<256+160*n else None
        return None
    for row in rows:
        wire=bytes.fromhex(row['wire']);length=struct.unpack_from('<I',wire,8)[0];payload=wire[12:12+length]
        if length==124:
            need(struct.unpack_from('<4I',payload)==(6,124,129,0),'local Surface message type/flags')
            handle=struct.unpack_from('<2I',payload,16)
            need(1<=handle[0]<=8 and handle[1]>0 and not any(payload[24:84]),'local Surface handle and zero unused fields')
            need(surface.setdefault(row['slot'],handle)==handle,'one exact local surface generation')
            actual.append((row['slot'],struct.unpack_from('<2I4i4I',payload,84)));continue
        e=struct.unpack('<4I4Q3iI',payload);kind,flags=e[2:4];code,dx,dy,b=e[8:]
        if kind==1:
            need(not (flags or code or dx or dy or b),'canonical input health');continue
        if kind==2:
            need(flags&~63==0 and not (dx or dy or b),'canonical raw keyboard')
            if code==15 and flags&16 and not flags&1:
                focus=1-focus;z=[1-focus,focus];continue
            need(code in (15,30,48,56),'only injected scan codes')
            key={15:9,30:97,48:98,56:0}[code]
            need(not flags&(2|4|32),'unmodified diagnostic key')
            if key:emit(focus,3,pressed=1-(flags&1),key=key)
            continue
        need(kind==3 and not flags and not code and -256<=dx<=255 and -256<=dy<=255 and b<=7,'canonical pointer packet')
        oldx,oldy=x,y;x=max(0,min(639,x+dx));y=max(0,min(479,y-dy))
        target=capture if capture is not None else hit()
        if (x,y)!=(oldx,oldy):emit(target,1,dx=x-oldx,dy=y-oldy)
        for button in range(3):
            if not (buttons^b)&(1<<button):continue
            pressed=(b>>button)&1;previous=capture
            if button==0:
                if pressed:
                    capture=hit()
                    if capture is not None:focus=capture;z=[1-focus,focus]
                else:capture=None
            target=previous if previous is not None else capture
            emit(target,2,button=button+1,pressed=pressed)
            pointer.append((target,pressed,x,y))
        buttons=b
    # Global Surface serial establishes cross-client order independently of
    # their receive scheduling and millisecond timestamp ties.
    actual.sort(key=lambda item:item[1][1]);need(len({e[1][1] for e in actual})==len(actual),'unique delivered Surface serial')
    at=0;coalesced=0
    for event in actual:
        while at<len(expected) and expected[at]!=event:
            old=expected[at]
            need(old[1][0]==1 and at+1<len(expected) and expected[at+1][0]==old[0] and
                 expected[at+1][1][0]==1,'no lost/reordered key or button delivery')
            at+=1;coalesced+=1
        need(at<len(expected) and expected[at]==event,'exact local coordinates, delta, serial, focus and capture');at+=1
    need(at==len(expected),'complete local input delivery')
    if spec[0]=='focus-capture':
        need(pointer==[(0,1,50,80),(0,0,505,385),(1,1,500,300),(1,0,500,300)],'outside release stays with original capture')
        bs=[slot for slot,e in actual if e[0]==3 and e[8]==98]
        need(bs==[7,7],'newly focused unrelated client receives B only')
        need(any(slot==6 and e[0]==1 and e[2:4]==(319,191) for slot,e in actual),'outside grab local coordinate clamp')
    return dict(local_events=len(actual),coalesced_motion=coalesced,buttons=[list(p) for p in pointer])

def pixel_proof(folder):
    width,height,initial=ppm(folder/'initial/pixels.ppm')
    w,h,after=ppm(folder/'after-input/pixels.ppm')
    need((width,height)==(w,h)==(1024,768),'expected real VGA extent')
    font=(ROOT/'assets/fonts/reist-vga.psf').read_bytes();glyph=font[32+97*16:32+98*16]
    fg=bytes((234,242,250));bg=bytes((24,34,45))
    for y in range(16):
        for x in range(296):
            expected=fg if x<160 and glyph[y]&(128>>(x%8)) else bg
            at=((112+y)*width+35+x)*3
            need(after[at:at+3]==expected,'independent PSF2 twenty-character pixel oracle')
    for y in range(height):
        left=640 if y<480 else 0;at=(y*width+left)*3;end=(y+1)*width*3
        need(initial[at:end]==after[at:end],'no framebuffer writes outside GUI viewport')
    return dict(width=width,height=height,glyphs=20,font_sha256=verify.digest(ROOT/'assets/fonts/reist-vga.psf'))

def fault_selection(image,symbols,port,folder,selector,end):
    need(selector in range(1,15),'named private fault selector')
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    choices=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').read_bytes()==catalog]
    need(len(choices)==1,'unique root image');program=choices[0]/'program0.prg';raw=program.read_bytes()
    expected=struct.pack('<2Q',0x315549474e545352,0);matches=[]
    phoff=struct.unpack_from('<Q',raw,32)[0];phsize,count=struct.unpack_from('<2H',raw,54)
    for n in range(count):
        kind,flags,offset,va,_,filesz,_,_=struct.unpack_from('<II6Q',raw,phoff+n*phsize)
        if kind==1 and flags==6:
            for match in re.finditer(re.escape(expected),raw[offset:offset+filesz]):matches.append(va+match.start())
    need(len(matches)==1 and matches[0]%8==0,'unique loaded private fault selector')
    selected={name:0xffffffff80000000+symbols[name] for name in
        ('native_session_probe_start_site64','scheduler_current_slot','scheduler_tasks','scheduler_mode')}
    script=folder/'selection.gdb'
    body=r'''
import gdb,struct,json,pathlib
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u64(a):return struct.unpack('<Q',mem(a,8))[0]
assert int(gdb.parse_and_eval('$rip'))&((1<<64)-1)==S['native_session_probe_start_site64']
assert not int(gdb.parse_and_eval('$eflags'))&512
assert mem(S['scheduler_mode'],1)==b'\x08' and mem(S['scheduler_current_slot'],4)==bytes(4)
state,generation,root=struct.unpack('<3Q',mem(S['scheduler_tasks'],24));assert (state,generation)==(2,1)
DM=0xffff800000000000;MASK=0x3fffff000
for shift in (39,30,21):
    entry=u64(DM+root+((VA>>shift)&511)*8);assert entry&7==7 and not entry&128;root=entry&MASK
leaf=u64(DM+root+((VA>>12)&511)*8);assert leaf&~MASK&~0x60==(1<<63)|7
address=DM+(leaf&MASK)+(VA&4095);assert VA&4095<=4080
before=struct.pack('<2Q',0x315549474e545352,0);after=struct.pack('<2Q',0x315549474e545352,SELECTOR)
assert mem(address,16)==before
gdb.selected_inferior().write_memory(address,after)
assert mem(address,16)==after
(FOLDER/'selection.json').write_text(json.dumps(dict(before=before.hex(),after=after.hex(),address=VA)))
'''
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\nhbreak *{selected["native_session_probe_start_site64"]:#x}\ncontinue\npython\n'+
        'import pathlib\nFOLDER=pathlib.Path('+repr(str(folder))+f')\nS={selected!r}\nVA={matches[0]}\nSELECTOR={selector}\n'+
        body+'\nend\ndelete breakpoints\ndetach\nquit 0\n',encoding='ascii')
    executable=shutil.which('gdb');need(executable,'fault selector debugger')
    command=[executable,'-q','-nx','-batch','-x',str(script)]
    verify.save(folder/'selection-command.json',dict(command=command,tool_sha256=verify.digest(executable),script_sha256=verify.digest(script),program_sha256=verify.digest(program)))
    remaining=min(30,end-5-time.monotonic());need(remaining>0,'first-entry selection deadline')
    with (folder/'selection.log').open('xb') as output:
        process=subprocess.Popen(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:need(process.wait(timeout=remaining)==0,'private selector debugger status')
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=1)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=1)
    selection=json.loads((folder/'selection.json').read_text())
    need(selection==dict(before=expected.hex(),after=struct.pack('<2Q',0x315549474e545352,selector).hex(),address=matches[0]),'exact sole private selector write')
    return selection

def lifecycle_proof(folder,spec,before=None):
    selector=spec[1];path=folder/'lifecycle';row=json.loads((path/'result.json').read_text())
    need(row['passed'] and 0<row['stops']<=128 and 'error' not in row,'bounded actual lifecycle stop')
    if selector in (10,13):
        need(row['current_slot']==4 and row['client']==0 and row['reason']==(-22 if selector==10 else -116),'actual malformed/stale validator rejection')
        owners=struct.unpack('<4Q',bytes.fromhex(row['owners']))
        live=state(path,True)
        need(tuple(live['owners'])==owners,'actual validator owners')
        return dict(reason=row['reason'],owners=list(owners))
    receipt=row['receipt'];slot=receipt[0]
    need(row['current_slot']==slot and slot==(0 if selector==12 else 6 if selector in (7,8,9) else 5 if selector in (4,5,6) else 4),'exact failing role')
    tasks=(path/'tasks.bin').read_bytes();generation=struct.unpack_from('<Q',tasks,slot*1024+8)[0]
    need(generation==receipt[1],'terminal receipt exact generation')
    if selector in (1,4,7,12,14):need(receipt[2:4]==[134,3],'actual invalid-opcode fault')
    elif selector in (3,6,9):
        need(receipt[2:4]==[256,3],'actual CPU fault')
        budget=struct.unpack_from('<4Q',(path/'cpu-budgets.bin').read_bytes(),slot*32)
        window=struct.unpack_from('<4Q',(path/'cpu-windows.bin').read_bytes(),slot*32)
        need(budget[0]==generation and budget[1]==32 and window[0]==100 and window[3]==32,'unchanged actual periodic CPU32 enforcement')
    else:need(receipt[2:4] in ([0,3],[71,4],[110,4]),'bounded cancellation or endpoint/health exit')
    if selector==12:
        root=generation<<32;family=(path/'family.bin').read_bytes()
        need(struct.unpack('<Q',(path/'service-acquisitions.bin').read_bytes())[0]>0,'parent died after actual terminal acquisition')
        for name in ('display','input'):
            v=struct.unpack('<16Q',(path/(name+'.bin')).read_bytes())
            need(all(v[n]^v[n+8]==2**64-1 for n in range(8)) and v[3]==1,'parent device fenced before child reap')
        service=struct.unpack('<8Q',(path/'terminal-service.bin').read_bytes())
        need(all(service[n]^service[n+4]==2**64-1 for n in range(4)) and service[3]==1,'parent service fenced before child reap')
        need((path/'terminal-lease.bin').read_bytes()==bytes(24),'dead parent lease cleared')
        need(not any((path/'terminal-proposal.bin').read_bytes()),'dead parent pending proposal cleared')
        for child in range(4,8):
            owner=struct.unpack_from('<Q',tasks,child*1024+8)[0]<<32|child
            need(owner>>32 and struct.unpack_from('<2Q',family,child*64)==(owner,root),'active graphical children at root loss')
    elif before is not None:
        need(receipt[1]==before['owners'][slot-4]>>32,'fault belongs to previously READY role')
    return dict(receipt=receipt)

def matrix_dialogue(image,symbols,port,folder,end,spec,row,raw,wait,delay,send,snapshot,inject,key):
    selector=spec[1];debugger=log=None
    try:
        wait(lambda:b'C:\\>' in raw,35);row['initial']=snapshot('initial',False)
        def observe():
            nonlocal debugger,log
            debugger,log=lifecycle_observer(image,symbols,port,folder/'lifecycle',selector)
            wait(lambda:(folder/'lifecycle/attached.json').exists() or debugger.poll() is not None,3)
            need((folder/'lifecycle/attached.json').exists(),'lifecycle observer attached')
        def observed():
            wait(lambda:debugger.poll() is not None,25);need(debugger.returncode==0,'lifecycle debugger detached')
            log.flush();row['fault']=lifecycle_proof(folder,spec,row.get('live'))
        if selector==12:observe()
        send('desktop')
        if selector==15:
            wait(lambda:raw.count(b'C:\\>')>=2,110)
            need(b'GRAPHICAL_READY' not in raw,'altered file never READY')
            row['retired']=snapshot('retired',False)
            need(row['retired']==row['initial'],'altered file publishes no device/role authority')
            for name in ('display-commits','input-transfers','service-acquisitions'):
                need((folder/'initial'/(name+'.bin')).read_bytes()==(folder/'retired'/(name+'.bin')).read_bytes(),'no altered-service side effect '+name)
        elif selector==12:
            wait(lambda:b'GRAPHICAL_READY\n' in raw,110)
            observed();need(raw.count(b'GRAPHICAL_READY\n')==1,'active parent READY before actual fault')
            wait(lambda:raw.count(b'C:\\>')>=2,15)
            row['retired']=snapshot('retired',False)
            need(row['retired']['root']>row['initial']['root'],'new root after complete old group retirement')
        else:
            wait(lambda:b'GRAPHICAL_READY\n' in raw,110);ready=time.monotonic()
            row['live']=snapshot('live',True)
            if selector:
                observe();observed()
                if selector==14:
                    wait(lambda:raw.count(b'C:\\>')>=2,25)
                    need(raw.count(b'GRAPHICAL_READY\n')==3,'two bounded restarts then degraded exit')
                    row['retired']=snapshot('retired',False)
                    previous=len(raw);send('desktop');wait(lambda:raw.count(b'C:\\>')>=3,5)
                    need(b'GRAPHICAL_READY' not in raw[previous:],'degraded session refuses manual budget bypass')
                    row['degraded']=snapshot('degraded',False)
                    need(row['degraded']==row['retired'],'sticky degraded graphical authority')
                    for name in ('display-commits','input-transfers','service-acquisitions'):
                        need((folder/'retired'/(name+'.bin')).read_bytes()==(folder/'degraded'/(name+'.bin')).read_bytes(),'no degraded service restart '+name)
                elif selector in (7,8,9,10,13):
                    old=row['live']['owners'][2]
                    wait(lambda:sum(r[0]==6 and r[1]>=old>>32 for r in reap_records(raw))>=(2 if selector==13 else 1),10)
                    delay(3);row['recovered']=snapshot('recovered',True)
                    a=row['live'];b=row['recovered']
                    need(a['root']==b['root'] and a['service_epoch']==b['service_epoch'] and
                        all(a['owners'][n]==b['owners'][n] for n in (0,1,3)) and
                        b['owners'][2]>>32>a['owners'][2]>>32,'client replacement must retain all unrelated owners')
                    row['reintegration']=capture_audits(image,symbols,port,folder/'reintegration',end,readiness_only=True)
                    need(row['reintegration']['authority']==b,'new client actually ready before user input')
                else:
                    wait(lambda:raw.count(b'GRAPHICAL_READY\n')>=2 or raw.count(b'C:\\>')>=2,12)
                    need(raw.count(b'GRAPHICAL_READY\n')==2 and raw.count(b'C:\\>')==1,'automatic group reintegration')
                    row['recovered']=snapshot('recovered',True)
                ready=time.monotonic()
            if selector!=14:
                current=row.get('recovered',row['live'])
                if selector not in (7,8,9,10,13):inject([key('alt',True),key('tab',True),key('tab',False),key('alt',False)])
                for _ in range(20):
                    inject([key('a',True)]);delay(.075);inject([key('a',False)]);delay(.075)
                if spec[0]=='focus-capture':
                    def move(dx,dy):
                        inject([dict(type='rel',data=dict(axis='x',value=dx)),dict(type='rel',data=dict(axis='y',value=dy))]);delay(.15)
                    def button(down):inject([dict(type='btn',data=dict(button='left',down=down))]);delay(.15)
                    move(42,72);button(True);move(255,255);move(200,50);button(False)
                    move(-5,-85);button(True);button(False)
                    inject([key('b',True)]);delay(.15);inject([key('b',False)]);delay(.15)
                delay(max(.01,ready+5.5-time.monotonic()))
                row['after_input']=snapshot('after-input',True)
                need(current==row['after_input'],'all reintegrated roles survive persistent input')
                row['pixels']=pixel_proof(folder)
                row['active_seconds']=time.monotonic()-ready;need(row['active_seconds']>5,'session persists beyond old 5000ms lease')
                row['receive_audit']=capture_audits(image,symbols,port,folder/'receive-audit',end,spec)
                inject([key('esc',True),key('esc',False)]);wait(lambda:raw.count(b'C:\\>')>=2,10)
                row['retired']=snapshot('retired',False)
        count=raw.count(b'C:\\>');offset=len(raw);send('cat /data.txt')
        wait(lambda:raw.count(b'C:\\>')>=count+1,15)
        need(b'Read-only, generation-bound, revocable.' in raw[offset:],'independent root and file-service liveness')
    finally:
        if debugger is not None:
            if debugger.poll() is None:debugger.terminate()
            try:debugger.wait(timeout=1)
            except subprocess.TimeoutExpired:debugger.kill();debugger.wait(timeout=1)
        if log is not None:log.close()

def run_case(image,package,folder,spec):
    need(image==verify.build_binding() and package==check.verify(verify.EVIDENCE/('media'+verify.MEDIA_ID)),'exact qualified package')
    return diagnostic(spec=spec,directory=folder)

def accepted_package():
    """Local acceptance receipt plus signed immutable media; no implicit build."""
    final_path=verify.EVIDENCE/'final.json'
    need(final_path.is_file(),'Grafikpaket noch nicht abgenommen: final.json fehlt')
    final=json.loads(final_path.read_text(encoding='utf-8'))
    need(final.get('accepted') is True and final.get('package')==verify.PACKAGE and
        re.fullmatch('[0-9a-f]{40}',final.get('commit','')),'exact accepted graphical commit')
    seal_path=ROOT/final['seal']['path']
    need(seal_path.resolve()==verify.BASE/'acceptance-seal.json' and verify.digest(seal_path)==final['seal']['sha256'],'bound acceptance seal')
    seal=json.loads(seal_path.read_text(encoding='utf-8'))
    need(seal['accepted'] and seal['graphical_cases']==18 and seal['cli_cases']==10,'complete graphical and CLI acceptance')
    for name in ('frozen','gates','scope','review','graphical_review','raw'):
        value=seal[name];path=ROOT/value['path']
        need(path.resolve().is_relative_to(verify.BASE) and verify.digest(path)==value['sha256'],'bound accepted '+name)
    gates=json.loads((ROOT/seal['gates']['path']).read_text())
    need(gates['passed'] and len(gates['gates'])==8 and all(r['passed'] and r['exit_code']==0 for r in gates['gates']),'eight successful frozen gates')
    frozen=json.loads((ROOT/seal['frozen']['path']).read_text())
    need(frozen['commands']==[r['command'] for r in gates['gates']],'accepted exact gate list')
    # Outcome-only queue/docs updates after verification are expected. All code,
    # tests and build inputs must still be the actually qualified bytes.
    for name,sha in frozen['sources'].items():
        if name=='Makefile' or name.startswith(('arch/','kernel/','userspace/','include/','lib/','config/','scripts/','test/')):
            need(verify.digest(ROOT/name)==sha,'accepted source changed '+name)
    need(subprocess.run(['git','merge-base','--is-ancestor',final['commit'],'HEAD'],cwd=ROOT,
        capture_output=True,timeout=30).returncode==0,'accepted local commit belongs to current history')
    image,package=verify.package()
    need(verify.link(image)==frozen['image'] and package.relative_to(ROOT).as_posix()==frozen['attempt'],'exact accepted graphical artifacts')
    return package

def machine_arguments(qemu,ram,display):
    need(type(ram) is int and ram in (4096,8192) and display in ('none','gtk'),'explicit reference machine')
    return [str(qemu),'-machine','pc,accel=tcg','-cpu','qemu64','-smp','1','-m',str(ram),
        '-display',display,'-vga','none','-device','VGA,vgamem_mb=16','-net','none',
        '-monitor','none','-serial','stdio','-no-reboot','-no-shutdown']

def launch(*,layout='hdd',ram=4096,check_only=False):
    need(layout in ('hdd','floppy') and type(ram) is int and ram in (4096,8192) and type(check_only) is bool,'supported graphical session')
    package=accepted_package()
    if check_only:
        print('GRAPHICAL_ACCEPTED_CHECK_OK',package,flush=True);return dict(passed=True,check_only=True)
    folder=verify.EVIDENCE/'sessions'/('session-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    start=time.monotonic();end=start+180;medium=data=vm=None
    result=dict(passed=False,limit=180,layout=layout,ram=ram,package=str(package))
    try:
        source=package/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
        medium=bios.BootMedium(source,folder/'boot-medium',layout,'normal',end);medium.verify('before')
        data=Data(folder,(package/'system.ext2').read_bytes(),end);data.verify('before')
        command=machine_arguments(boot.resolve_qemu(None),ram,'gtk')+bios.boot_arguments(medium.overlay,layout)+data.arguments(folder)
        verify.save(folder/'command.json',command)
        remaining=end-5-time.monotonic();need(remaining>0,'graphical launch deadline')
        print('REIST native64: desktop in der seriellen Shell starten. Esc kehrt zur Shell zurueck.\n'
              'QEMU-Fenster oder Strg+C beendet; Gesamtdauer maximal180s. Nachweise: '+str(folder),flush=True)
        vm=subprocess.Popen(command,cwd=ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            need(vm.wait(timeout=remaining)==0,'QEMU session exit');result['reason']='window-exit'
        except subprocess.TimeoutExpired:result['reason']='session-deadline'
        except KeyboardInterrupt:result['reason']='user-exit'
    except BaseException as error:result['error']=str(error);raise
    finally:
        try:
            try:
                if vm is not None:
                    if vm.poll() is None:vm.terminate()
                    try:vm.wait(timeout=2)
                    except subprocess.TimeoutExpired:vm.kill();vm.wait(timeout=1)
            finally:
                try:
                    if data is not None:data.verify('after')
                finally:
                    if medium is not None:medium.verify('after')
            result.update(elapsed=time.monotonic()-start,closed=vm is None or vm.poll() is not None)
            need(result['elapsed']<=180 and result['closed'],'whole graphical session cleanup deadline')
            result['passed']='reason' in result and 'error' not in result
        except BaseException as error:result['cleanup_error']=str(error);raise
        finally:verify.save(folder/'session.json',result)
    return result

def media_proof(package,folder,spec):
    from verify_x86_64_shell_boot_media import boot_base_proof
    _,selector,layout,_=spec
    source=package/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
    boot_base_proof(source,folder/'boot-medium/base.raw',layout,'normal')
    expected=altered_volume(package)[0] if selector==15 else (package/'system.ext2').read_bytes()
    need((folder/'generated.raw').read_bytes()==expected,'exact independent graphical volume')
    for medium,commands_name,prefix,base_name,size in (
        (folder/'boot-medium','commands.json','','base.raw',source.stat().st_size),
        (folder,'media-commands.json','media-','generated.raw',1048576)):
        commands=json.loads((medium/commands_name).read_text())
        need(len(commands)==7 and all(r['returncode']==0 for r in commands),'complete successful media tool history')
        sha=verify.digest(medium/base_name)
        for phase,at in (('before',1),('after',4)):
            receipt=json.loads((medium/(prefix+phase+'.json')).read_text());extents=json.loads(commands[at+1]['stdout'])
            need(receipt['passed'] and receipt['overlay_allocated_data']==0 and receipt['extents']==extents and
                [r['args'][0] for r in commands[at:at+3]]==['info','map','compare'],'complete unchanged COW proof')
            need((receipt['base_sha256'] if prefix else receipt['base']['sha256'])==sha,'immutable base hash')
            end=0
            for extent in extents:
                need(extent['start']==end and extent['length']>0 and extent['depth']==1,'no writable overlay sectors');end+=extent['length']
            need(end==size,'complete disk extent')

def review_case(image,package,folder,spec,*,diagnostic=False):
    name,selector,layout,ram=spec;row=json.loads((folder/'result.json').read_text())
    need(type(diagnostic) is bool and (not diagnostic or folder==verify.EVIDENCE/'guest11' and selector==14),'explicit reserved diagnostic review')
    need(row['passed'] and row['closed'] and row['qualification']==(not diagnostic) and row['guest']==name and
        (row['selector'],row['layout'],row['ram'])==(selector,layout,ram) and 0<row['elapsed']<=180,'exact complete fresh graphical guest')
    need(row['image']==verify.digest(image) and all(verify.digest(ROOT/n)==sha for n,sha in row['observer_sources'].items()),'source and loaded image identity')
    command=json.loads((folder/'command.json').read_text())
    for flag,value in (('-machine','pc,accel=tcg'),('-cpu','qemu64'),('-smp','1'),('-m',str(ram)),('-net','none'),('-display','none')):
        need(command.count(flag)==1 and command[command.index(flag)+1]==value,'fixed reference machine '+flag)
    raw=(folder/'guest.log').read_bytes();need(len(raw)<=2097152,'bounded serial evidence')
    bios.validate_bios(raw.decode('ascii',errors='replace'),layout,'normal')
    need(not any(s.encode() in raw for s in boot.FAILURES),'no fatal guest marker')
    initial=state(folder/'initial',False);retired=state(folder/'retired',False)
    need(initial==row['initial'] and retired==row['retired'],'raw initial and final state')
    receipts=reap_records(raw);need(len({r[:2] for r in receipts})==len(receipts),'unique actual reaps')
    count=raw.count(b'GRAPHICAL_READY\n');proof=dict(ready=count,retired=retired)
    need(raw.count(b'Read-only, generation-bound, revocable.')>=1,'independent immutable file read after GUI')
    if selector==15:
        need(count==0 and initial==retired and row['alteration']==altered_volume(package)[1],'corrupted service admission fails before rights')
        need(not any(r[0]>=4 for r in desktop_receipts(raw)),'corrupted file creates no GUI process')
    elif selector==12:
        need(count==1 and retired['root']>initial['root'],'active root containment and replacement')
        proof['fault']=lifecycle_proof(folder,spec)
        fault=proof['fault']['receipt'];needle=bytes.fromhex(struct.pack('<4I2Q',*fault).hex()).hex().upper().encode()
        need(raw.index(b'GRAPHICAL_READY\n')<raw.index(needle),'READY strictly precedes root reap')
        tasks=(folder/'lifecycle/tasks.bin').read_bytes()
        for slot in (0,4,5,6,7):
            generation=struct.unpack_from('<Q',tasks,slot*1024+8)[0]
            need(sum(r[:2]==(slot,generation) for r in receipts)==1,'old active root/group completely reaped')
    else:
        before=state(folder/'live',True);need(before==row['live'],'actual READY role group')
        need(initial['root']==before['root']==retired['root'],'root survives child failure and GUI exit')
        if selector:
            proof['fault']=lifecycle_proof(folder,spec,before)
            if 'receipt' in proof['fault']:
                receipt=tuple(proof['fault']['receipt']);need(receipt in receipts,'observed terminal receipt reaches reap')
                needle=struct.pack('<4I2Q',*receipt).hex().upper().encode()
                need(raw.index(b'GRAPHICAL_READY\n')<raw.index(needle),'role failure follows actual READY')
        if selector==14:
            need(count==3 and state(folder/'degraded',False)==retired,'exact exhausted group budget and sticky refusal')
            proof['exhausted_generations']=[r[1] for r in exhaustion_receipts(raw,before['owners'][0])]
        else:
            current=state(folder/'recovered',True) if selector else before
            if selector in (7,8,9,10,13):
                need(count==1 and current['root']==before['root'] and current['service_epoch']==before['service_epoch'] and
                    all(current['owners'][n]==before['owners'][n] for n in (0,1,3)) and current['owners'][2]>>32>before['owners'][2]>>32,'client-only recovery keeps unrelated authorities')
                old=before['owners'][2]>>32;new=current['owners'][2]>>32
                need(sum(r[0]==6 and old<=r[1]<new for r in receipts)==(2 if selector==13 else 1),'exact failed client generations retired')
                reintegration=review_audits(folder/'reintegration',readiness_only=True)
                need(reintegration==row['reintegration'] and reintegration['authority']==current,'independent complete pre-input reintegration')
                if selector==13:
                    rejected=proof['fault']['owners'][2]>>32
                    need(old<rejected<new,'prior Surface rejected by actual replacement generation')
            elif selector:
                need(count==2 and current['root']==before['root'] and current['service_epoch']==before['service_epoch']+1 and
                    all(b>>32>a>>32 for a,b in zip(before['owners'],current['owners'])),'complete fresh service group after fencing')
            else:need(count==1,'one persistent healthy session')
            need(state(folder/'after-input',True)==current and row['active_seconds']>5,'persistent recovered roles')
            proof['input']=review_audits(folder/'receive-audit',spec)
            need(proof['input']==row['receive_audit'] and proof['input']['authority']==current,'independent raw receive replay')
            expected={str(k):v for k,v in audit_bindings(image).items()}
            need(json.loads((folder/'receive-audit/bindings.json').read_text())==expected,'exact current compiled audit addresses')
            proof['pixels']=pixel_proof(folder);need(proof['pixels']==row['pixels'],'independent actual scanout')
        for owner in before['owners']+(row.get('recovered',{}).get('owners',[])):
            need(sum(r[:2]==(owner&0xffffffff,owner>>32) for r in receipts)==1,'every admitted role exactly reaped')
    if selector in (14,15):
        first='retired' if selector==14 else 'initial';last='degraded' if selector==14 else 'retired'
        for name in ('display-commits','input-transfers','service-acquisitions'):
            need((folder/first/(name+'.bin')).read_bytes()==(folder/last/(name+'.bin')).read_bytes(),'denied admission has no device side effects')
    media_proof(package,folder,spec);return proof

def diagnostic(number='01',*,spec=None,directory=None):
    need(number in ('01','02','03','04','05','06','07','08','09','10','11') and
         (spec is None or spec in CASES),'only reserved diagnostics or exact matrix member')
    if number=='11':
        need(spec is None and directory is None,'reserved exhaustion diagnostic')
        spec=next(s for s in CASES if s[0]=='restart-exhaustion');directory=verify.EVIDENCE/'guest11'
    traced=number in ('02','03','04')
    folder=verify.EVIDENCE/('guest'+number) if spec is None else Path(directory)
    need(folder.resolve().is_relative_to(verify.EVIDENCE) and folder==folder.resolve(),'owned graphical evidence path')
    need(not folder.exists(),'fresh diagnostic folder')
    folder.mkdir(parents=True);start=time.monotonic();end=start+180
    label,selector,layout,ram=spec or ('diagnostic'+number,0,'hdd',4096)
    row=dict(passed=False,qualification=spec is not None and number!='11',limit=180,guest=label,layout=layout,ram=ram,selector=selector)
    verify.save(folder/'started.json',row)
    vm=medium=data=qmp=reader=errors=debugger=debuglog=None;raw=bytearray();pending=queue.Queue(maxsize=128);reader_errors=[]
    try:
        image=verify.build_binding();media=verify.EVIDENCE/('media'+verify.MEDIA_ID)
        binding=json.loads((verify.EVIDENCE/('development-media'+verify.MEDIA_ID+'.json')).read_text())
        need(binding['passed'] and binding['sources']==verify.media_sources() and binding['tools']==verify.build_tools(),'exact published media inputs')
        need(binding['index_sha256']==verify.digest(media/'graphical-media.json'),'exact media index')
        package=check.verify(media);symbols={n:v['value'] for n,v in elf.elf(image.read_bytes(),32)['symbols'].items()}
        row['image']=verify.digest(image);row['package']=str(package)
        inputs={str(Path(__file__).relative_to(ROOT)):verify.digest(__file__),
                'scripts/verify_x86_64_graphical_session.py':verify.digest(verify.__file__)}
        row['observer_sources']=inputs
        medium=bios.BootMedium(package/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img'),folder/'boot-medium',layout,'normal',end)
        volume=(package/'system.ext2').read_bytes()
        if selector==15:volume,row['alteration']=altered_volume(package)
        medium.verify('before');data=Data(folder,volume,end);data.verify('before')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        name='reist-graphical-'+uuid.uuid4().hex;qemu=boot.resolve_qemu(None)
        row['qemu']={'path':str(qemu),'sha256':verify.digest(qemu)}
        command=machine_arguments(qemu,ram,'none')+['-name',name,'-S','-qmp',f'tcp:127.0.0.1:{port},server=on,wait=off',
            *bios.boot_arguments(medium.overlay,layout),*data.arguments(folder)]
        if number!='01' or spec is not None:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));gdbport=sock.getsockname()[1]
            command+=['-gdb',f'tcp:127.0.0.1:{gdbport}']
        verify.save(folder/'command.json',command);errors=(folder/'stderr.log').open('xb')
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def read():
            try:
                while True:
                    chunk=os.read(vm.stdout.fileno(),4096)
                    if not chunk:return
                    pending.put(chunk,timeout=2)
            except BaseException as error:reader_errors.append(str(error))
        reader=threading.Thread(target=read,daemon=True);reader.start()
        for _ in range(100):
            need(vm.poll() is None,'QEMU startup')
            try:qmp=QMP(port,name,end);break
            except ConnectionRefusedError:time.sleep(.02)
        need(qmp is not None,'QMP startup limit')
        if spec is not None and 0<selector<15:row['selection']=fault_selection(image,symbols,gdbport,folder,selector,end)
        elif number in ('06','07','08','10'):row['selection']=fault_selection(image,symbols,gdbport,folder,7 if number in ('08','10') else 1,end)
        else:qmp.call('cont',{})
        def pump():
            for _ in range(4096):
                try:raw.extend(pending.get_nowait())
                except queue.Empty:break
            need(len(raw)<=2097152 and not reader_errors,'bounded serial capture')
            need(not any(s.encode() in raw for s in boot.FAILURES),'guest fatal marker')
            need(vm.poll() is None,'unexpected QEMU exit')
            if debugger is not None:need(debugger.poll() in (None,0),'observer failure')
        def wait(predicate,seconds):
            deadline=min(end-5,time.monotonic()+seconds)
            while time.monotonic()<deadline:
                pump()
                if predicate():return
                time.sleep(.005)
            raise TimeoutError('guest dialogue deadline: '+raw[-600:].decode(errors='replace'))
        def delay(seconds):
            until=time.monotonic()+seconds;wait(lambda:time.monotonic()>=until,seconds+.1)
        def send(command):
            at=len(raw);prefix=b'';encoded=command.encode('ascii')
            for offset in range(0,len(encoded),8):
                chunk=encoded[offset:offset+8];vm.stdin.write(chunk);vm.stdin.flush();prefix+=chunk
                wait(lambda:prefix in raw[at:],5)
            vm.stdin.write(b'\n');vm.stdin.flush()
        def snapshot(step,live):
            qmp.call('stop',{});need(qmp.call('query-status',{})['running'] is False,'paused snapshot')
            target=folder/step;target.mkdir()
            for name,symbol,size in SNAPSHOTS:
                path=target/(name+'.bin');qmp.call('pmemsave',dict(val=symbols[symbol],size=size,filename=str(path)))
                need(path.stat().st_size==size,'snapshot length')
            qmp.call('screendump',dict(filename=str(target/'pixels.ppm')))
            proof=state(target,live) if live is not None else None;qmp.call('cont',{});return proof
        def key(name,down):return dict(type='key',data=dict(down=down,key=dict(type='qcode',data=name)))
        injections=[]
        def inject(events):
            args={'events':events};qmp.call('input-send-event',args);injections.append(dict(elapsed=time.monotonic()-start,arguments=args))
        if spec is not None:
            matrix_dialogue(image,symbols,gdbport,folder,end,spec,row,raw,wait,delay,send,snapshot,inject,key)
        else:
            wait(lambda:b'C:\\>' in raw,35);row['initial']=snapshot('initial',False)
            if traced:
                probe=input_probe(image) if number=='04' else None
                if probe:row['probe']=probe
                debugger,debuglog=observer(symbols,gdbport,folder,probe)
                wait(lambda:(folder/'observer-attached.json').exists(),3)
            send('desktop');wait(lambda:b'GRAPHICAL_READY\n' in raw,110)
            ready=time.monotonic()
            if not traced:row['live']=snapshot('live',True)
            else:
                row['live']=state(folder/('trace-live1' if number=='04' else 'trace-ready1'),True)
                (folder/'live').mkdir();qmp.call('screendump',dict(filename=str(folder/'live/pixels.ppm')))
            if number in ('06','07'):
                row['before_fault']=row['live']
                wait(lambda:raw.count(b'GRAPHICAL_READY\n')>=2 or raw.count(b'C:\\>')>=2,12)
                need(raw.count(b'GRAPHICAL_READY\n')==2 and raw.count(b'C:\\>')==1,'automatic group recovery READY before shell return')
                row['live']=snapshot('recovered',True);ready=time.monotonic()
                need(row['live']['root']==row['before_fault']['root'] and
                     row['live']['service_epoch']==row['before_fault']['service_epoch']+1 and
                     all(b>>32>a>>32 for a,b in zip(row['before_fault']['owners'],row['live']['owners'])),'fresh recovered group with retained root')
                receipts=[struct.unpack('<4I2Q',bytes.fromhex(m.decode())) for m in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',raw)]
                old=row['before_fault']['owners'][0]
                faults=[r for r in receipts if r[:2]==(4,old>>32)]
                need(len(faults)==1 and faults[0][2:4]==(134,3),'actual compositor invalid-opcode fault/reap')
                row['fault_reap']=faults[0]
            if number in ('08','10'):
                row['before_fault']=row['live'];old=row['live']['owners'][2]
                def child_reaped():
                    return any(struct.unpack('<2I',bytes.fromhex(m.decode())[:8])==(6,old>>32)
                        for m in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',raw))
                wait(child_reaped,8);delay(3 if number=='10' else 1.5)
                row['live']=snapshot('recovered',True);ready=time.monotonic()
                need(row['live']['root']==row['before_fault']['root'] and row['live']['service_epoch']==row['before_fault']['service_epoch'] and
                    all(row['live']['owners'][n]==row['before_fault']['owners'][n] for n in (0,1,3)) and row['live']['owners'][2]>>32>old>>32,'only failed client recreated')
                faults=[struct.unpack('<4I2Q',bytes.fromhex(m.decode())) for m in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',raw)]
                matched=[r for r in faults if r[:2]==(6,old>>32)]
                need(len(matched)==1 and matched[0][2:4]==(134,3),'actual client invalid-opcode reap');row['fault_reap']=matched[0]
                if number=='10':row['reintegration']=capture_audits(image,symbols,gdbport,folder/'reintegration',end,readiness_only=True)
            else:inject([key('alt',True),key('tab',True),key('tab',False),key('alt',False)])
            for _ in range(20):
                inject([key('a',True)]);delay(.075);inject([key('a',False)]);delay(.075)
            delay(max(.01,ready+5.5-time.monotonic()))
            if not traced:row['after_input']=snapshot('after-input',True)
            else:
                row['after_input']=row['live']
                (folder/'after-input').mkdir();qmp.call('screendump',dict(filename=str(folder/'after-input/pixels.ppm')))
            need(row['live']==row['after_input'],'same roles survive sustained input')
            w,h,before=ppm(folder/'live/pixels.ppm');w2,h2,after=ppm(folder/'after-input/pixels.ppm')
            need((w,h)==(w2,h2) and before!=after,'visible input response')
            row['active_seconds']=time.monotonic()-ready;need(row['active_seconds']>5,'persistent session')
            if number in ('05','06','07','08','09','10'):row['receive_audit']=capture_audits(image,symbols,gdbport,folder/'receive-audit',end)
            inject([key('esc',True),key('esc',False)]);wait(lambda:raw.count(b'C:\\>')>=2,10)
            if debugger is not None:
                need(debugger.wait(timeout=2)==0,'observer detached');debuglog.flush()
                if number!='04':row['replay']=replay_healthy(folder)
                else:
                    records=[json.loads(line) for line in (folder/'ipc.jsonl').read_text().splitlines()]
                    events=[struct.unpack('<4I4Q3iI',bytes.fromhex(r['payload'])) for r in records]
                    need(len(events)>32 and len(events)<=256 and all(e[7]==n+1 and e[4:7]==events[0][4:7] for n,e in enumerate(events)),'sparse real input generations and sequence')
                    keys=[e for e in events if e[2]==2 and e[8]==30]
                    need(len(keys)==40 and [e[3]&1 for e in keys]==[0,1]*20,'sparse exact keyboard stream')
                    need(json.loads((folder/'observer-result.json').read_text())['passed'],'sparse observer completion')
                    need(all(verify.digest(ROOT/n)==sha for n,sha in probe['bindings'].items()),'stable compiled probe binding')
                    row['sparse_input_count']=len(events)
            row['retired']=snapshot('retired',False);offset=len(raw);send('cat /data.txt')
            wait(lambda:raw.count(b'C:\\>')>=3,15)
            need(b'Read-only, generation-bound, revocable.' in raw[offset:],'independent shell/file liveness')
        bios.validate_bios(raw.decode('ascii',errors='replace'),layout,'normal')
        need(all(verify.digest(ROOT/n)==sha for n,sha in inputs.items()),'unchanged observer')
        row['injections']=injections;row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        if debugger is not None:
            if debugger.poll() is None:debugger.terminate()
            try:debugger.wait(timeout=1)
            except subprocess.TimeoutExpired:debugger.kill();debugger.wait(timeout=1)
        if debuglog is not None:debuglog.close()
        if vm is not None:
            if vm.poll() is None:vm.terminate()
            try:vm.wait(timeout=2)
            except subprocess.TimeoutExpired:vm.kill();vm.wait(timeout=1)
        if qmp is not None:qmp.sock.close()
        if reader is not None:reader.join(timeout=.2)
        if errors is not None:errors.close()
        while not pending.empty():raw.extend(pending.get_nowait())
        (folder/'guest.log').write_bytes(raw)
        try:
            if data is not None:data.verify('after')
            if medium is not None:medium.verify('after')
        except BaseException as error:row['passed']=False;row['cleanup_error']=str(error);raise
        finally:
            row.update(elapsed=time.monotonic()-start,closed=vm is None or vm.poll() is not None)
            if row['elapsed']>180:row['passed']=False;row['deadline_error']=True
            verify.save(folder/'result.json',row)
    need(row['passed'] and row['closed'],'complete diagnostic');return row

if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--diagnostic',choices=('01','02','03','04','05','06','07','08','09','10','11'))
    group.add_argument('--launch',action='store_true');group.add_argument('--check-only',action='store_true')
    parser.add_argument('--layout',choices=('hdd','floppy'),default='hdd');parser.add_argument('--ram',type=int,choices=(4096,8192),default=4096)
    args=parser.parse_args()
    if args.diagnostic:
        row=diagnostic(args.diagnostic)
        if args.diagnostic=='11':
            spec=next(s for s in CASES if s[0]=='restart-exhaustion')
            proof=review_case(verify.build_binding(),Path(row['package']),verify.EVIDENCE/'guest11',spec,diagnostic=True)
            verify.save(verify.EVIDENCE/'guest11/review.json',proof)
        print('GRAPHICAL_DIAGNOSTIC_OK',row['elapsed'])
    else:launch(layout=args.layout,ram=args.ram,check_only=args.check_only)
