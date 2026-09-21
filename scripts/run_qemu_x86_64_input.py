"""Finite real PS/2 input proof; QMP hardware events and independent raw replay."""
from pathlib import Path
import argparse,hashlib,json,os,queue,re,shutil,socket,struct,subprocess,threading,time,types,uuid
import build_x86_64_c_payload as elf
import check_x86_64_input_media as check
import run_qemu_x86_64_boot as boot
import run_qemu_x86_64_cli_media as cli
import run_qemu_x86_64_shell_boot_media as bios
ROOT=check.ROOT
CASES=(('healthy1024','',16,4096),('healthy800','',2,4096),('8g','',16,8192),
       ('crash','u',16,4096),('cpu','q',16,4096),('hang','h',16,4096),
       ('quota','b',16,4096),('stale','s',16,4096),('malformed','m',16,4096),
       ('flood','f',16,4096),('missing','n',16,4096),('parent-loss','p',16,4096))
import run_qemu_x86_64_display as display
from run_x86_64_display import data_fixture
need=check.need

class QMP:
    def __init__(self,port,name,end):
        self.end=end;self.buf=bytearray();self.seq=0
        self.sock=socket.create_connection(('127.0.0.1',port),timeout=2)
        need('QMP' in self.read(),'QMP greeting')
        self.call('qmp_capabilities',{})
        need(self.call('query-name',{})=={'name':name},'owned QEMU identity')
    def read(self):
        end=min(self.end,time.monotonic()+2)
        for _ in range(64):
            if b'\n' in self.buf:
                line,_,rest=self.buf.partition(b'\n');self.buf[:]=rest;return json.loads(line)
            left=end-time.monotonic();need(left>0,'QMP command deadline')
            self.sock.settimeout(left);chunk=self.sock.recv(4096);need(chunk,'QMP closed')
            self.buf.extend(chunk);need(len(self.buf)<=16384,'QMP message capacity')
        raise ValueError('QMP fragmentation limit')
    def call(self,op,args):
        need(op in ('qmp_capabilities','query-name','query-status','stop','cont','quit','pmemsave','screendump','input-send-event'),'QMP operation')
        self.seq+=1;need(self.seq<=256 and time.monotonic()<self.end,'QMP request budget')
        self.sock.sendall((json.dumps({'execute':op,'arguments':args,'id':self.seq})+'\n').encode())
        for _ in range(32):
            row=self.read()
            if 'event' in row:continue
            need(row.get('id')==self.seq and 'return' in row and 'error' not in row,'QMP response '+str(row))
            return row['return']
        raise ValueError('QMP event budget')

def events(raw):
    # Kernel lifecycle diagnostics can interrupt distinct bounded user WRITEs.
    # Keep the raw stream for the independent reap oracle; remove only its exact
    # complete record grammar when reconstructing the user event stream.
    raw=re.sub(rb'REIST_X86_64_PROCESS_REAP_OK v1=[0-9A-F]{64}\r\n',b'',raw)
    return [struct.unpack('<4I4Q3iI',bytes.fromhex(v.decode())) for v in re.findall(rb'INPUT_EVENT v1=([0-9a-f]{128})',raw)]

def state(folder,step,mode,final=False,symbols=None):
    proof=display.validate_state(folder,step,mode,final,symbols)
    path=folder/step;words=struct.unpack('<16Q',(path/'input.bin').read_bytes())
    need(all(words[n]^words[n+8]==2**64-1 for n in range(8)),'input protected state inverse')
    owner,parent,epoch,fenced,window,last,operations,prefix=words[:8]
    need(fenced==1 and prefix==0 and operations<=64 and window<=last,'input fenced and bounded')
    tasks=(path/'tasks.bin').read_bytes();profiles=(path/'profiles.bin').read_bytes()
    need(not any(tasks[5*1024:6*1024]) and not any(profiles[5*32:6*32]),'input worker fully reaped')
    need(not any((path/'input-request.bin').read_bytes()),'input request scrubbed')
    if final:
        need(owner==parent==0 and epoch>=2 and struct.unpack('<Q',(path/'input-finishes.bin').read_bytes())[0]==2,'two root input cleanups')
    elif owner:need(owner&0xffffffff==5 and parent&0xffffffff==0 and owner>>32>0 and parent>>32>0,'generation-bound input domain')
    else:need(parent==prefix==operations==0,'empty input domain')
    proof['input']=dict(owner=owner,parent=parent,epoch=epoch,operations=operations)
    return proof

def input_arguments(flood=False):
    key=lambda name,down:dict(type='key',data=dict(down=down,key=dict(type='qcode',data=name)))
    if flood:return [key('a',n%2==0) for n in range(64)]
    return [key('shift',True),key('a',True),key('a',False),key('shift',False),
            dict(type='rel',data=dict(axis='x',value=12)),dict(type='rel',data=dict(axis='y',value=6)),
            dict(type='btn',data=dict(down=True,button='left'))]

def live_profile(path,event):
    tasks=(path/'tasks.bin').read_bytes();profiles=(path/'profiles.bin').read_bytes();family=(path/'family.bin').read_bytes()
    need((len(tasks),len(profiles),len(family))==(8192,256,512),'complete live authority snapshot')
    root=struct.unpack_from('<Q',tasks,8)[0]<<32
    ordinary=sum(1<<n for n in (4,5,6,9,15,20,22,40,41,42,50,51,53,54,58))
    driver=sum(1<<n for n in (9,22,41,42,53))
    for slot,handle,mask,high in ((4,event[5],ordinary,(1<<49)|(1<<63)),(5,event[4],driver,1<<49)):
        need(handle&0xffffffff==slot and struct.unpack_from('<Q',tasks,slot*1024+8)[0]==handle>>32,'live exact task identity')
        need(struct.unpack_from('<4Q',profiles,slot*32)==(handle>>32,mask,high,0),'exact attenuated live syscall profile')
        need(struct.unpack_from('<2Q',family,slot*64)==(handle,root),'exact live root-child relationship')
    return dict(root=root,driver=event[4],consumer=event[5],epoch=event[6])

def event_proof(raw,healthy):
    rows=events(raw);need(rows,'actual received input records')
    for n,r in enumerate(rows,1):
        need(r[:2]==(1,64) and r[4]&0xffffffff==5 and r[5]&0xffffffff==4 and
             r[4]>>32>0 and r[5]>>32>0 and 0<r[6]<2**63 and r[7]==n<=32,'event ABI and sequence')
        need(r[4:7]==rows[0][4:7],'one owner/target/epoch per session')
    need(rows[0][2:4]==(1,0) and rows[0][8:]==(0,0,0,0),'first self-tested healthy event')
    if healthy:
        expected=[(1,0,0,0,0,0),(2,4,42,0,0,0),(2,4,30,0,0,0),
                  (2,5,30,0,0,0),(2,1,42,0,0,0),(3,0,0,12,-6,1),(3,0,0,0,0,0)]
        actual=[(r[2],r[3],*r[8:]) for r in rows]
        need(len(actual)==7 and actual[0]==expected[0] and
             [r for r in actual if r[0]==2]==[r for r in expected if r[0]==2] and
             [r for r in actual if r[0]==3]==[r for r in expected if r[0]==3],
             'exact keyboard and AUX streams with contiguous shared sequence')
    return rows

def receive_diagnostic(program,symbols,port,folder):
    from build_x86_64_boot_programs import prepare
    prepare(program,[],True)
    phoff=struct.unpack_from('<Q',program,32)[0];count=struct.unpack_from('<H',program,56)[0]
    executable=[]
    for n in range(count):
        kind,flags,offset,va,_,filesz,_,_=struct.unpack_from('<II6Q',program,phoff+n*56)
        if kind==1 and flags==5:executable.append((va,program[offset:offset+filesz]))
    need(len(executable)==1,'one admitted executable input segment')
    address,body=executable[0]
    starts=[m.start() for m in re.finditer(re.escape(b'\xb8\x36\0\0\0'),body)]
    need(len(starts)==1,'one compiled receive syscall for read-only diagnostic')
    offset=body.find(b'\x0f\x05',starts[0],starts[0]+48)
    need(offset>=0,'actual receive SYSCALL instruction');pc=address+offset+2
    code='''import gdb,struct,json
class Receive(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(PC),internal=True,type=gdb.BP_HARDWARE_BREAKPOINT)
        self.count=0
    def stop(self):
        self.count+=1
        assert self.count<=4096
        inf=gdb.selected_inferior()
        slot=struct.unpack('<I',bytes(inf.read_memory(SLOT,4)))[0]
        if slot!=4:return False
        pointer=int(gdb.parse_and_eval('$rsi'))&((1<<64)-1)
        value=int(gdb.parse_and_eval('$rax'))&((1<<64)-1)
        data=bytes(inf.read_memory(pointer,140))
        gdb.write('INPUT_RECEIVE_DIAGNOSTIC '+json.dumps(dict(pc=PC,slot=slot,result=value,message=data.hex()))+'\\n')
        return True
Receive()
'''
    script=folder/'receive.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nPC={pc}\nSLOT={0xffffffff80000000+symbols["scheduler_current_slot"]}\n'+code+
        'end\ncontinue\ndelete breakpoints\ndetach\nquit 0\n',encoding='ascii')
    log=(folder/'receive.log').open('wb')
    process=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
        stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return process,log

def run_case(image,package,folder,spec,*,diagnostic=False):
    label,mode,vram,ram=spec;folder=Path(folder).absolute()
    need(not folder.exists() and folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent'),'fresh scoped guest evidence')
    folder.mkdir(parents=True);start=time.monotonic();end=start+90
    result=dict(passed=False,label=label,mode=mode,vram=vram,ram=ram,limit=90,snapshots=[])
    symbols={n:v['value'] for n,v in elf.elf(Path(image).read_bytes(),32)['symbols'].items()}
    medium=fixture=process=qmp=thread=debugger=debuglog=None;raw=bytearray();pending=queue.Queue(maxsize=128);reader_error=[]
    try:
        values=__import__('build_x86_64_input_media').inputs(Path(image).parent)
        files=check.medium_files(values)
        need((Path(package)/'system.ext2').read_bytes()==cli.apps.media.image('ext2-1k',files),'published data fixture')
        medium=bios.BootMedium(Path(package)/'reist-x86_64-floppy.img',folder/'boot-medium','floppy','normal',end)
        medium.verify('before');fixture=data_fixture(folder,files,start,90);fixture.verify('before')
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        name='reist-input-'+uuid.uuid4().hex
        cmd=[str(boot.resolve_qemu(None)),'-name',name,'-machine','pc,accel=tcg'+(',i8042=off' if mode=='n' else ''),'-cpu','qemu64',
             '-smp','1','-m',str(ram),'-display','none','-vga','none','-device','VGA,vgamem_mb='+str(vram),
             '-net','none','-monitor','none','-serial','stdio','-no-reboot','-no-shutdown','-S',
             '-qmp',f'tcp:127.0.0.1:{port},server=on,wait=off',*bios.boot_arguments(medium.overlay,'floppy'),*fixture.arguments(folder)]
        if mode=='p' or diagnostic:
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));gdbport=listener.getsockname()[1]
            cmd+=['-gdb',f'tcp:127.0.0.1:{gdbport}']
        (folder/'command.json').write_text(json.dumps(cmd,indent=2))
        errors=(folder/'stderr.log').open('wb')
        process=subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def reader():
            try:
                while True:
                    chunk=os.read(process.stdout.fileno(),4096)
                    if not chunk:return
                    pending.put(chunk,timeout=2)
            except BaseException as error:reader_error.append(str(error))
        thread=threading.Thread(target=reader,daemon=True);thread.start()
        for _ in range(100):
            need(process.poll() is None,'QEMU startup exit')
            try:qmp=QMP(port,name,end);break
            except ConnectionRefusedError:time.sleep(.02)
        need(qmp is not None,'QMP startup bound')
        if mode=='p':
            import run_qemu_x86_64_shell_session as session
            config,_,_=cli.apps.image_config(image,'ext2-1k')
            code=session.diagnostic_select_layout(config)
            old="after=struct.pack('<4Q',0x3153455353484c53,1,0,0)"
            need(code.count(old)==1,'exact existing first-entry selector adapter')
            code=code.replace(old,"after=struct.pack('<4Q',0x3153455353484c53,1,2,15)")
            script=folder/'parent-loss.gdb'
            script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
                f'target remote 127.0.0.1:{gdbport}\n'+code+'delete breakpoints\ndetach\nquit 0\n',encoding='ascii')
            debuglog=(folder/'parent-loss.log').open('wb')
            debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
                stdout=debuglog,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:qmp.call('cont',{})
        def pump():
            for _ in range(4096):
                try:raw.extend(pending.get_nowait())
                except queue.Empty:break
            need(len(raw)<=2*1024*1024 and not reader_error,'bounded complete serial capture')
            need(not any(s.encode() in raw for s in boot.FAILURES),'guest fatal marker')
            if debugger is not None:need(debugger.poll() in (None,0),'bounded parent selector failed')
        def wait(predicate,limit=60):
            until=min(end-3,time.monotonic()+limit)
            while time.monotonic()<until:
                pump()
                if predicate():return
                need(process.poll() is None,'unexpected guest exit')
                time.sleep(.005)
            raise TimeoutError('guest dialogue deadline: '+raw[-350:].decode(errors='replace'))
        def send(command):
            offset=len(raw);encoded=command.encode();prefix=b''
            for at in range(0,len(encoded),8):
                chunk=encoded[at:at+8];process.stdin.write(chunk);process.stdin.flush();prefix+=chunk
                wait(lambda:prefix in bytes(raw[offset:]),5)
            process.stdin.write(b'\n');process.stdin.flush()
        def snapshot(step,final=False):
            qmp.call('stop',{});need(qmp.call('query-status',{})['running'] is False,'paused snapshot')
            out=folder/step;out.mkdir()
            for name,symbol,size in [('boot','native_display_boot',64),('state','native_display_state',128),
                ('request','native_display_request',64+16384+8),('tasks','scheduler_tasks',8*1024),
                ('profiles','family_profiles',8*32),('finishes','native_display_finishes',8),
                ('commits','native_display_commits',8),('input','native_input_state',128),
                ('input-request','native_input_request',64),('input-finishes','native_input_finishes',8),
                ('transfers','native_input_transfers',8),('pd','native_display_pd',7*4096),
                ('pdpt','pdpt_table',4096),('pml4','pml4_table',4096)]:
                qmp.call('pmemsave',{'val':symbols[symbol],'size':size,'filename':str(out/(name+'.bin'))})
                need((out/(name+'.bin')).stat().st_size==size,'exact physical snapshot '+name)
            qmp.call('screendump',{'filename':str(out/'pixels.ppm')})
            proof=state(folder,step,vram,final,symbols)
            result['snapshots'].append(dict(step=step,proof=proof,final=final))
            qmp.call('cont',{});return out
        wait(lambda:raw.count(b'C:\\>')>=1);snapshot('initial')
        if diagnostic:debugger,debuglog=receive_diagnostic(values['file-program.prg'],symbols,gdbport,folder)
        if mode=='p':
            need(debugger.wait(timeout=2)==0,'parent selector detached before dialogue');debuglog.flush()
            selection=re.findall(r'AY_DIAGNOSTIC_LAYOUT (\{[^\n]+\})',(folder/'parent-loss.log').read_text())
            need(len(selection)==1,'one recorded parent-loss selector')
            expected=dict(before=struct.pack('<4Q',0x3153455353484c53,1,2,0).hex(),
                          after=struct.pack('<4Q',0x3153455353484c53,1,2,15).hex())
            need(json.loads(selection[0])==expected,'only exact private root fault selector modified')
        prompts=1;segments=[];injections=[];live=[]
        first='boot.prg'+(' '+mode if mode in ('u','q','h','b','s','m') else '')
        commands=[first,'cat /data.txt','boot.prg','exit','boot.prg s','cat /data.txt','exit']
        if mode=='p':commands=['boot.prg','boot.prg s','cat /data.txt','exit']
        for number,command in enumerate(commands):
            before=len(raw);send(command)
            is_input=command.startswith('boot.prg')
            healthy=is_input and mode!='n' and not(number==0 and mode in ('u','q','h','b','m','p','f'))
            inject=healthy or (number==0 and mode=='f')
            if inject:
                wait(lambda:b'INPUT_READY\n' in raw[before:],20)
                qmp.call('stop',{});need(qmp.call('query-status',{})['running'] is False,'paused live authority snapshot')
                path=folder/('live'+str(number));path.mkdir()
                for name,symbol,size in (('tasks','scheduler_tasks',8192),('profiles','family_profiles',256),('family','family_records',512)):
                    qmp.call('pmemsave',dict(val=symbols[symbol],size=size,filename=str(path/(name+'.bin'))))
                live.append(dict(number=number,proof=live_profile(path,events(raw[before:])[0])))
                qmp.call('cont',{})
                arguments={'events':input_arguments(mode=='f' and number==0)}
                qmp.call('input-send-event',arguments);injections.append(dict(number=number,arguments=arguments))
                if healthy:
                    wait(lambda:any(r[2]==3 and r[-1]==1 for r in events(raw[before:])),3)
                    arguments={'events':[dict(type='btn',data=dict(down=False,button='left'))]}
                    qmp.call('input-send-event',arguments);injections.append(dict(number=number,arguments=arguments))
            if number==len(commands)-1:
                wait(lambda:b'REIST_X86_64_NATIVE_PROCESSES_OK' in raw,20)
                snapshot('final',True);segments.append(dict(command=command,start=before,end=len(raw),healthy=False));break
            prompts+=1;wait(lambda:raw.count(b'C:\\>')>=prompts,20)
            out=snapshot('step'+str(number));text=bytes(raw[before:])
            segments.append(dict(command=command,start=before,end=len(raw),healthy=healthy))
            if is_input:
                if mode=='p' and number==0:need(b'INPUT_READY' not in text,'parent loss before terminal delivery')
                else:
                    need(b'DISPLAY_CLIENT_OK' in text,'normal input client received display and terminal')
                    if healthy:event_proof(text,True)
                    if mode=='n':need(b'INPUT_READY' not in text,'missing controller never healthy')
            if command.startswith('cat'):need(b'Read-only, generation-bound, revocable.' in text,'independent file liveness')
        result['segments']=segments;result['injections']=injections;result['live']=live
        need(raw.count(b'REIST_X86_64_PROCESS_RUN_OK')==2,'two complete root runs')
        bios.validate_bios(raw.decode('ascii',errors='replace'),'floppy','normal')
        result['passed']=True
    except BaseException as error:result['error']=str(error);raise
    finally:
        if debugger is not None:
            if debugger.poll() is None:debugger.terminate()
            try:debugger.wait(timeout=1)
            except subprocess.TimeoutExpired:debugger.kill();debugger.wait(timeout=1)
        if debuglog is not None:debuglog.close()
        if process is not None:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=1)
            errors.close()
        if qmp is not None:qmp.sock.close()
        if thread is not None:thread.join(timeout=.2)
        while not pending.empty():raw.extend(pending.get_nowait())
        (folder/'guest.log').write_bytes(raw)
        try:
            if fixture is not None:fixture.verify('after')
            if medium is not None:medium.verify('after')
        except BaseException as error:result['passed']=False;result['cleanup_error']=str(error);raise
        finally:
            result.update(elapsed=time.monotonic()-start,closed=process is None or process.poll() is not None)
            if result['elapsed']>90:result['passed']=False;result['deadline_error']=True
            (folder/'result.json').write_text(json.dumps(result,indent=2))
    need(result['passed'] and result['closed'],'complete input guest');return result

def media_proof(package,folder):
    import verify_x86_64_shell_boot_media as old
    old.boot_base_proof(Path(package)/'reist-x86_64-floppy.img',folder/'boot-medium/base.raw','floppy','normal')
    need((folder/'generated.raw').read_bytes()==(Path(package)/'system.ext2').read_bytes(),'exact immutable data volume')
    for medium,commands_name,prefix,base_name,size in [
        (folder/'boot-medium','commands.json','','base.raw',1474560),
        (folder,'media-commands.json','media-','generated.raw',1048576)]:
        commands=json.loads((medium/commands_name).read_text())
        need(len(commands)==7 and all(r['returncode']==0 for r in commands),'complete successful media command history')
        base_sha=hashlib.sha256((medium/base_name).read_bytes()).hexdigest()
        for phase,at in [('before',1),('after',4)]:
            receipt=json.loads((medium/(prefix+phase+'.json')).read_text());extents=json.loads(commands[at+1]['stdout'])
            need(receipt['passed'] and receipt['overlay_allocated_data']==0 and receipt['extents']==extents and
                 [r['args'][0] for r in commands[at:at+3]]==['info','map','compare'],'unchanged complete COW proof')
            need((receipt['base']['sha256'] if not prefix else receipt['base_sha256'])==base_sha,'actual base identity')
            end=0
            for extent in extents:
                need(extent['start']==end and extent['length']>0 and extent['depth']==1,'unchanged COW extent');end+=extent['length']
            need(end==size,'complete media extent')


def painted(before,after,pointer):
    w,h,initial=display.ppm(before);w2,h2,actual=display.ppm(after)
    need((w,h)==(w2,h2),'stable input framebuffer dimensions')
    expected=bytearray(initial)
    for y in range(64):
        for x in range(64):
            at=((32+y)*w+32+x)*3;expected[at:at+3]=bytes((x*4,y*4,90))
    if pointer:
        for y in range(134,198):
            for x in range(140,204):
                at=(y*w+x)*3;expected[at:at+3]=bytes((0,208,255))
    need(actual==bytes(expected),'exact tiles and unchanged complete surrounding scanout')

def review_case(image,package,folder,spec):
    label,mode,vram,ram=spec;folder=Path(folder)
    row=json.loads((folder/'result.json').read_text());serial=(folder/'guest.log').read_bytes()
    need(row['passed'] and row['closed'] and row['elapsed']<=90 and
         (row['label'],row['mode'],row['vram'],row['ram'])==spec,'exact bounded input guest receipt')
    need(len(serial)<=2*1024*1024 and not any(s.encode() in serial for s in boot.FAILURES),'bounded serial without fatal markers')
    need(serial.count(b'REIST_X86_64_PROCESS_RUN_OK')==2 and serial.count(b'REIST_X86_64_NATIVE_PROCESSES_OK')==1,'two complete root runs')
    command=json.loads((folder/'command.json').read_text())
    need('-kernel' not in command and command[command.index('-m')+1]==str(ram) and
         command[command.index('-machine')+1]=='pc,accel=tcg'+(',i8042=off' if mode=='n' else '') and
         command[command.index('-cpu')+1]=='qemu64' and command[command.index('-smp')+1]=='1' and
         command[command.index('-display')+1]=='none' and command[command.index('-net')+1]=='none' and
         ('-gdb' in command)==(mode=='p'),'exact isolated QEMU input profile')
    first='boot.prg'+(' '+mode if mode in ('u','q','h','b','s','m') else '')
    commands=[first,'cat /data.txt','boot.prg','exit','boot.prg s','cat /data.txt','exit']
    if mode=='p':commands=['boot.prg','boot.prg s','cat /data.txt','exit']
    steps=['initial',*(f'step{n}' for n in range(len(commands)-1)),'final']
    need([r['step'] for r in row['snapshots']]==steps and len(row['segments'])==len(commands),'complete commands/snapshots')
    symbols={n:v['value'] for n,v in elf.elf(Path(image).read_bytes(),32)['symbols'].items()}
    for snapshot in row['snapshots']:
        need(snapshot['final']==(snapshot['step']=='final') and snapshot['proof']==state(folder,snapshot['step'],vram,snapshot['final'],symbols),'independent input/display state replay')
    reaps=[struct.unpack('<4I2Q',bytes.fromhex(v.decode())) for v in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',serial)]
    need(len({r[1] for r in reaps})==len(reaps),'all reaped generations unique')
    inputs=[];live=[];injections=[];paint=False;pointer=False;commits=0;last_end=0;epochs=[]
    for number,(segment,cmd) in enumerate(zip(row['segments'],commands)):
        need(segment['command']==cmd and last_end<=segment['start']<segment['end']<=len(serial),'ordered exact serial command span')
        text=serial[segment['start']:segment['end']];last_end=segment['end']
        need(cmd.encode() in text,'actual normal shell command echo')
        healthy=cmd.startswith('boot.prg') and mode!='n' and not(number==0 and mode in ('u','q','h','b','m','p','f'))
        need(segment['healthy']==healthy,'declared healthy case')
        outcome=[r for r in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',text)]
        outcomes=[struct.unpack('<4I2Q',bytes.fromhex(r.decode())) for r in outcome]
        if cmd.startswith('boot.prg'):
            children=[r for r in outcomes if r[0]==4];workers=[r for r in outcomes if r[0]==5]
            need(len(children)==len(workers)==1,'one foreground and one driver reaped per start');child=children[0];worker=workers[0]
            inputs.append((child,worker));records=events(text)
            if number==0 and mode=='p':
                need(not records and b'DISPLAY_CLIENT_OK' not in text and child[2:4]==worker[2:4]==(0,3),'parent loss before publication, both children cancelled')
                need(any(r[:4]==(0,1,134,3) for r in outcomes),'actual parent UD fault')
            else:
                need(text.count(b'DISPLAY_CLIENT_OK')==1,'one ordinary display grant');paint=True;commits+=1
                if mode=='n':
                    need(not records and b'INPUT_READY' not in text and child[2] in (71,110) and child[3]==4 and
                         worker[2:4] in ((110,4),(0,3)),'missing controller fails before HEALTHY')
                else:
                    records=event_proof(text,healthy);epochs.append(records[0][6])
                    need(records[0][4]==worker[1]<<32|5 and records[0][5]==child[1]<<32|4,'wire identities equal actual retired tasks')
                    if healthy:
                        need(child[2:4]==(82,4) and worker[2:4]==(0,4),'healthy driver/client explicit exits')
                        pointer=True;commits+=2
                    elif mode in ('u','q','h'):
                        need(len(records)==1 and child[2:4]==(82,4),'faulted driver cannot publish later events')
                        need(worker[2:4]=={'u':(134,3),'q':(256,3),'h':(0,3)}[mode],'actual declared driver containment')
                        if mode=='q':need(worker[4]==32,'unchanged actual CPU32 exhaustion')
                    elif mode in ('b','m'):
                        error=-122 if mode=='b' else -71;status=-error
                        need(len(records)==2 and records[1][2:4]==(4,0) and records[1][8:]==(error,0,0,0) and
                             child[2:4]==(status,4) and worker[2:4] in ((status,4),(0,3)),'exact validated fault and bounded containment')
                    elif mode=='f':
                        need(1<=len(records)<=32 and all(r[2]==2 and r[8:]==(30,0,0,0) and r[3] in (0,1) for r in records[1:]),'bounded actual keyboard flood')
                        need(child[2:4] in ((82,4),(122,4)) and worker[2:4] in ((0,4),(122,4),(0,3)),'flood retirement remains bounded')
                    if healthy or (number==0 and mode=='f'):
                        live.append(dict(number=number,proof=live_profile(folder/('live'+str(number)),records[0])))
                        injections.append(dict(number=number,arguments={'events':input_arguments(mode=='f' and number==0)}))
                        if healthy:injections.append(dict(number=number,arguments={'events':[dict(type='btn',data=dict(down=False,button='left'))]}))
        if cmd.startswith('cat'):
            need(b'Read-only, generation-bound, revocable.' in text and len([r for r in outcomes if r[0]==4 and r[2:4]==(0,4)])==1,'ordinary file liveness after input isolation')
        path=folder/('final' if number==len(commands)-1 else 'step'+str(number))/'pixels.ppm'
        if paint:painted(folder/'initial/pixels.ppm',path,pointer)
        else:need(path.read_bytes()==(folder/'initial/pixels.ppm').read_bytes(),'no ungranted display output')
    need(row['live']==live and row['injections']==injections,'exact live grants and QMP input history')
    need(epochs==sorted(set(epochs)),'new self-tested epoch on each healthy recreation')
    total=struct.unpack('<Q',(folder/'final/commits.bin').read_bytes())[0]
    need(total==commits,'exact successful display commits')
    expected=2 if mode=='p' else 3;last=row['snapshots'][-1]['proof']
    need(last['epoch']==last['input']['epoch']==expected and len(inputs)==expected,'all starts fenced/reaped across roots')
    need(struct.unpack('<Q',(folder/'final/transfers.bin').read_bytes())[0]>(0 if mode!='n' else -1),'actual bounded transport exercised')
    bios.validate_bios(serial.decode('ascii',errors='replace'),'floppy','normal');media_proof(Path(package),folder)
    return dict(label=label,input_sessions=len(inputs),epochs=epochs,commits=commits,live_profiles=live)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--package',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--case',choices=[r[0] for r in CASES],default='healthy1024');a=p.parse_args()
    spec=next(r for r in CASES if r[0]==a.case);print(json.dumps(run_case(a.image,a.package,a.output,spec),indent=2))
