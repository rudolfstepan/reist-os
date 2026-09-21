"""Finite real BIOS/Ring3 display proof with pixel and physical-state readback."""
from pathlib import Path
import argparse,hashlib,json,os,queue,re,shutil,socket,struct,subprocess,threading,time,types,uuid
import build_x86_64_c_payload as elf
import check_x86_64_display_media as check
import run_qemu_x86_64_boot as boot
import run_qemu_x86_64_cli_media as cli
import run_qemu_x86_64_shell_boot_media as bios
ROOT=check.ROOT
CASES=(('healthy1024','',16,4096),('healthy800','',2,4096),
       ('stale','s',16,4096),('crash','u',16,4096),('cpu','q',16,4096),
       ('hang','c',16,4096),('quota','b',16,4096),('8g','',16,8192),('parent-loss','p',16,4096))
need=check.need

def deadline_cleanup(events,root,request,reply,end,timeout,failed):
    """Original processing end followed only by bounded, observed cleanup."""
    closes=[r for r in events if r['kind'] in ('call','return') and r.get('gen')==root and
            r['op']==52 and r['args'][0] in (request,reply)]
    need([(r['kind'],r['args'][0]) for r in closes]==
         [('call',request),('return',request),('call',reply),('return',reply)],'display CLI complete ordered closes')
    first,done,second,last=closes
    need(timeout['result']==-110 and 0<timeout['args'][2]<=1000 and
         timeout['entered']+timeout['args'][2]==end==timeout['now'],'original exact broker timeout')
    need(done['result']==last['result']==0 and
         end<=first['entered']==done['entered']<=done['now']<=second['entered']==last['entered']<=
         last['now']==failed['now']<failed['entered']+1000 and
         failed['args'][2]==1000 and failed['entered']<end and failed['result']==-32,
         'successful cleanup and real wakeup before original child deadline')
    positions=[events.index(r) for r in (timeout,*closes,failed)]
    need(positions==sorted(set(positions)),'timeout/close/wakeup causal order')
    actions=[r for r in events[positions[0]+1:positions[-1]] if r['kind'] in ('call','return') and r.get('gen')==root]
    need(actions==closes,'only endpoint cleanup after broker deadline; no renewed work')
    return first['entered'],second['entered']

cli_qualified_outcome=cli.bb.function(cli.apps.qualified_outcome,dict(vars(cli.apps),deadline_cleanup=deadline_cleanup),[
    ('timeout=timeouts[0];failed=failures[0]',
     'timeout=timeouts[0];failed=failures[0]\n        request_entered,reply_entered=deadline_cleanup(events,root,request,reply,end,timeout,failed)'),
    ("failed['entered']<end==failed['now']","failed['entered']<end<=failed['now']<failed['entered']+1000"),
    ("len(closed)==1 and closed[0]['entered']==end and",
     "len(closed)==1 and closed[0]['entered']==(request_entered if endpoint==request else reply_entered) and")])
_cli_app_io=types.FunctionType(cli.apps.validate_io_and_faults.__code__,dict(vars(cli.apps),qualified_outcome=cli_qualified_outcome))

def cli_namespace(label):
    selected=cli.namespace(label)
    selected.ay.validate_io_and_faults=lambda *args:_cli_app_io(selected.ay,cli.apps.case_spec(label),*args)
    return selected

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
        need(op in ('qmp_capabilities','query-name','query-status','stop','cont','quit','pmemsave','screendump'),'QMP operation')
        self.seq+=1;need(self.seq<=256 and time.monotonic()<self.end,'QMP request budget')
        self.sock.sendall((json.dumps({'execute':op,'arguments':args,'id':self.seq})+'\n').encode())
        for _ in range(32):
            row=self.read()
            if 'event' in row:continue
            need(row.get('id')==self.seq and 'return' in row and 'error' not in row,'QMP response '+str(row))
            return row['return']
        raise ValueError('QMP event budget')

def ppm(path):
    raw=Path(path).read_bytes();need(len(raw)<=8*1024*1024,'pixel capture capacity')
    match=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',raw)
    need(match,'PPM header');w,h=map(int,match.groups());pixels=raw[match.end():]
    need((w,h) in ((1024,768),(800,600)) and len(pixels)==w*h*3,'complete pixel capture')
    return w,h,pixels

def validate_pixels(before,after):
    w,h,old=ppm(before);w2,h2,new=ppm(after);need((w,h)==(w2,h2),'stable display mode')
    expected=bytearray(old)
    for y in range(64):
        for x in range(64):
            at=((32+y)*w+32+x)*3;expected[at:at+3]=bytes((x*4,y*4,0x5a))
    need(new==bytes(expected),'exact Ring3 tile and unchanged surrounding scanout')

def validate_mapping(path,symbols,base,mapbytes):
    pml4=struct.unpack('<512Q',(path/'pml4.bin').read_bytes())
    pdpt=struct.unpack('<512Q',(path/'pdpt.bin').read_bytes())
    tables=struct.unpack('<3584Q',(path/'pd.bin').read_bytes())
    need(pml4[511]&~0x60==symbols['pdpt_table']|3,'supervisor shared kernel hierarchy')
    need(pdpt[509]&~0x60==symbols['native_display_pd']|3,'exact dedicated supervisor display directory')
    for n in range(512):
        expected=(symbols['native_display_pts']+n*4096)|3 if n<6 else 0
        need(tables[n]&~0x60==expected,'exact bounded display PT topology')
    for n in range(3072):
        expected=(base+n*4096)|0x800000000000001b if n<mapbytes//4096 else 0
        need(tables[512+n]&~0x60==expected,'only admitted NX supervisor UC MMIO leaves')

def validate_state(folder,step,mode,final=False,symbols=None):
    path=folder/step
    b=(path/'boot.bin').read_bytes();need(len(b)==64,'complete boot snapshot')
    words=struct.unpack('<8Q',b);need(all(words[n]^words[n+4]==2**64-1 for n in range(4)),'boot inverse')
    base,pitch,width,height,length,mapbase,mapbytes=struct.unpack('<Q6I',b[:32])
    need(base==mapbase and base>=0xc0000000 and base+mapbytes<=2**32 and
         (width,height)==((800,600) if mode==2 else (1024,768)) and pitch>=width*4 and
         length==pitch*height and mapbytes==(length+4095)&~4095,'admitted exact device extent')
    if symbols is not None:validate_mapping(path,symbols,mapbase,mapbytes)
    state=struct.unpack('<16Q',(path/'state.bin').read_bytes())
    need(all(state[n]^state[n+8]==2**64-1 for n in range(8)),'complete domain inverse')
    owner,parent,epoch,fenced,window,last,commits,bytes_=state[:8]
    need(fenced==1 and window<=last and commits<=64 and bytes_<=1048576,'fenced bounded domain')
    tasks=(path/'tasks.bin').read_bytes();profiles=(path/'profiles.bin').read_bytes()
    need(not any(tasks[4*1024:5*1024]) and not any(profiles[4*32:5*32]),'foreground fully reaped before shell prompt')
    need(not any((path/'request.bin').read_bytes()),'request and private staging scrubbed')
    if final:
        need(not owner and not parent and epoch>=2 and not any(tasks) and not any(profiles),'all generations retired')
        need(struct.unpack('<Q',(path/'finishes.bin').read_bytes())[0]==2,'both root cleanups')
    elif owner:
        need(owner&0xffffffff==4 and parent&0xffffffff==0 and owner>>32>0 and parent>>32>0,'exact retired foreground identity')
    else:
        need(not parent and not commits and not bytes_,'empty reset has no residual authority or quota')
        need(struct.unpack('<Q',(path/'finishes.bin').read_bytes())[0]==(1 if epoch else 0),'exact root reset count')
    return dict(owner=owner,parent=parent,epoch=epoch,fenced=fenced,commits=commits,bytes=bytes_,width=width,height=height)

def run_case(image,package,folder,spec):
    label,mode,vram,ram=spec;folder=Path(folder).absolute()
    need(not folder.exists() and folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent'),'fresh scoped guest evidence')
    folder.mkdir(parents=True);start=time.monotonic();end=start+320
    result=dict(passed=False,label=label,mode=mode,vram=vram,ram=ram,limit=320,snapshots=[])
    symbols={n:v['value'] for n,v in elf.elf(Path(image).read_bytes(),32)['symbols'].items()}
    medium=fixture=process=qmp=thread=debugger=debuglog=None;raw=bytearray();pending=queue.Queue(maxsize=128);reader_error=[]
    try:
        values=__import__('build_x86_64_display_media').inputs(Path(image).parent)
        files=check.medium_files(values)
        need((Path(package)/'system.ext2').read_bytes()==cli.apps.media.image('ext2-1k',files),'published data fixture')
        medium=bios.BootMedium(Path(package)/'reist-x86_64-floppy.img',folder/'boot-medium','floppy','normal',end)
        medium.verify('before');fixture=cli.data_fixture(folder,files,start,320);fixture.verify('before')
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        name='reist-display-'+uuid.uuid4().hex
        cmd=[str(boot.resolve_qemu(None)),'-name',name,'-machine','pc,accel=tcg','-cpu','qemu64',
             '-smp','1','-m',str(ram),'-display','none','-vga','none','-device','VGA,vgamem_mb='+str(vram),
             '-net','none','-monitor','none','-serial','stdio','-no-reboot','-no-shutdown','-S',
             '-qmp',f'tcp:127.0.0.1:{port},server=on,wait=off',*bios.boot_arguments(medium.overlay,'floppy'),*fixture.arguments(folder)]
        if mode=='p':
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
                ('commits','native_display_commits',8),('pd','native_display_pd',7*4096),
                ('pdpt','pdpt_table',4096),('pml4','pml4_table',4096)]:
                qmp.call('pmemsave',{'val':symbols[symbol],'size':size,'filename':str(out/(name+'.bin'))})
                need((out/(name+'.bin')).stat().st_size==size,'exact physical snapshot '+name)
            qmp.call('screendump',{'filename':str(out/'pixels.ppm')})
            proof=validate_state(folder,step,vram,final,symbols)
            result['snapshots'].append(dict(step=step,proof=proof,final=final))
            qmp.call('cont',{});return out
        wait(lambda:raw.count(b'C:\\>')>=1);snapshot('initial')
        if debugger is not None:
            need(debugger.wait(timeout=2)==0,'parent selector detached before dialogue');debuglog.flush()
            selection=re.findall(r'AY_DIAGNOSTIC_LAYOUT (\{[^\n]+\})',(folder/'parent-loss.log').read_text())
            need(len(selection)==1,'one recorded parent-loss selector')
            expected=dict(before=struct.pack('<4Q',0x3153455353484c53,1,2,0).hex(),
                          after=struct.pack('<4Q',0x3153455353484c53,1,2,15).hex())
            need(json.loads(selection[0])==expected,'only exact private root fault selector modified')
        prompts=1
        first='boot.prg'+(' '+mode if mode else '')
        commands=[first,'cat /data.txt','boot.prg','exit','boot.prg s','cat /data.txt','exit']
        if mode=='p':commands=['boot.prg','boot.prg s','cat /data.txt','exit']
        for number,command in enumerate(commands):
            before=len(raw);send(command)
            if number==len(commands)-1:
                wait(lambda:b'REIST_X86_64_NATIVE_PROCESSES_OK' in raw,60)
                snapshot('final',True);break
            prompts+=1;wait(lambda:raw.count(b'C:\\>')>=prompts,60)
            out=snapshot('step'+str(number))
            if mode=='p' and number==0:
                text=bytes(raw[before:]);rows=re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',text)
                reaps=[struct.unpack('<4I2Q',bytes.fromhex(v.decode())) for v in rows]
                need(len([r for r in reaps if r[:4]==(0,1,134,3)])==1,'actual root UD retirement')
                need(len([r for r in reaps if r[0]==4 and r[2:4]==(0,3)])==1,'bound child cancelled on parent loss')
                need((out/'pixels.ppm').read_bytes()==(folder/'initial/pixels.ppm').read_bytes(),'no output before terminal grant')
                need(result['snapshots'][-1]['proof']['epoch']==1 and not result['snapshots'][-1]['proof']['owner'],'parent domain fenced and reset')
                continue
            if command.startswith('boot.prg'):
                text=bytes(raw[before:]);need(b'DISPLAY_CLIENT_OK' in text,'actual display client completed paint')
                rows=re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',text)
                reaps=[struct.unpack('<4I2Q',bytes.fromhex(v.decode())) for v in rows]
                children=[r for r in reaps if r[0]==4];need(len(children)==1,'one foreground generation reaped')
                r=children[0]
                if number==0 and mode in ('u','q','c'):
                    need(r[3]==3,'fault/hang generation contained')
                    if mode=='q':need(r[2]==256 and r[4]==32,'unchanged CPU quota retirement')
                else:need(r[2:4]==(82,4),'display self-test and explicit exit82')
                validate_pixels(folder/'initial/pixels.ppm',out/'pixels.ppm')
            if command.startswith('cat'):need(b'Read-only, generation-bound, revocable.' in raw[before:],'independent CLI file liveness')
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
            if result['elapsed']>320:result['passed']=False;result['deadline_error']=True
            (folder/'result.json').write_text(json.dumps(result,indent=2))
    need(result['passed'] and result['closed'],'complete display guest');return result

def review_case(image,package,folder,spec):
    label,mode,vram,ram=spec;folder=Path(folder)
    row=json.loads((folder/'result.json').read_text())
    need(row['passed'] and row['closed'] and row['elapsed']<=320 and
         (row['label'],row['mode'],row['vram'],row['ram'])==spec,'complete exact display receipt')
    symbols={n:v['value'] for n,v in elf.elf(Path(image).read_bytes(),32)['symbols'].items()}
    steps=['initial','step0','step1','step2','final'] if mode=='p' else ['initial',*(f'step{n}' for n in range(6)),'final']
    need([r['step'] for r in row['snapshots']]==steps,'complete snapshot sequence')
    for r in row['snapshots']:
        need(r['final']==(r['step']=='final') and r['proof']==validate_state(folder,r['step'],vram,r['final'],symbols),'independent physical-state replay')
    painted=['step1','step2','final'] if mode=='p' else [*steps[1:]]
    for step in painted:validate_pixels(folder/'initial/pixels.ppm',folder/step/'pixels.ppm')
    if mode=='p':need((folder/'initial/pixels.ppm').read_bytes()==(folder/'step0/pixels.ppm').read_bytes(),'parent-loss no premature output')
    total=struct.unpack('<Q',(folder/'final/commits.bin').read_bytes())[0]
    need(total==(1 if mode=='p' else 66 if mode=='b' else 3),'exact committed tile count including rejected requests')
    serial=(folder/'guest.log').read_bytes();need(len(serial)<=2*1024*1024,'bounded raw serial')
    need(not any(s.encode() in serial for s in boot.FAILURES) and serial.count(b'REIST_X86_64_PROCESS_RUN_OK')==2 and
         serial.count(b'REIST_X86_64_NATIVE_PROCESSES_OK')==1,'complete two-root native execution')
    need(serial.count(b'DISPLAY_CLIENT_OK')==(1 if mode=='p' else 3),'exact actual paint self-tests')
    need(serial.count(b'Read-only, generation-bound, revocable.')==(1 if mode=='p' else 2),'CLI remains live after display retirement')
    receipts=[struct.unpack('<4I2Q',bytes.fromhex(v.decode())) for v in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',serial)]
    children=[r for r in receipts if r[0]==4]
    first={'u':(134,3),'q':(256,3),'c':(0,3),'p':(0,3)}.get(mode,(82,4))
    expected=[first,(82,4),(0,4)] if mode=='p' else [first,(0,4),(82,4),(82,4),(0,4)]
    need([r[2:4] for r in children]==expected,'all actual foreground outcomes in order')
    need(len({r[1] for r in receipts})==len(receipts),'no reused task generation')
    if mode=='q':need(children[0][4]==32,'unchanged CPU32 bound')
    if mode=='b':need(serial.count(b'DISPLAY_QUOTA_FENCED')==1,'explicit quota and subsequent denied commit')
    bios.validate_bios(serial.decode('ascii',errors='replace'),'floppy','normal')
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
    return dict(label=label,commits=total,epochs=row['snapshots'][-1]['proof']['epoch'],foreground=len(children))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',choices=[r[0] for r in CASES],default='healthy1024');a=p.parse_args()
    spec=next(r for r in CASES if r[0]==a.case)
    print(json.dumps(run_case(a.image,a.package,a.output,spec),indent=2))
