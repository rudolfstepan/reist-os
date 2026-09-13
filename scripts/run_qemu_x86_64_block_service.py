"""Fixed read-only Ring3 block RPC, real transport and retirement proof."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid,inspect
import run_qemu_x86_64_pio as pio
ROOT=pio.ROOT
startup=pio.startup

def terminal_owner_capabilities(raw,generation):
    if len(raw)!=108:raise ValueError('terminal client size')
    words=struct.unpack('<27I',raw)
    if words[:3]!=(generation,generation,1):raise ValueError('terminal client generation')
    handles=[]
    for i in range(3,27,3):
        handle,rights,live=words[i:i+3]
        if not live:
            if handle or rights:raise ValueError('terminal empty capability')
        elif live!=1 or not handle or rights!=7:raise ValueError('terminal capability rights')
        else:handles.append(handle)
    if len(handles)!=3 or len(set(handles))!=3:raise ValueError('terminal endpoint ownership')
    return handles

def observer(s,c,folder,ram,case,oom,record,result_address):
    code=pio.observer(s,c,folder,ram,case,oom,record,block=True)
    # The inherited start probe otherwise traps every resumed syscall. Keep
    # every full first-publication assertion, disarm only when all live tasks
    # were witnessed, and re-arm at CREATE copy and the next root transaction.
    code=pio.once(code,'Start()\nclass Cancel','family_start_probe=Start()\nclass Cancel')
    code=pio.once(code,"            started.add(gen);assert len(started)<=36",f"""            started.add(gen);assert len(started)<=36
            live=[struct.unpack('<2Q',mem({s['scheduler_tasks']}+i*256,16)) for i in range(4)]
            if all(state not in (1,2,6) or identity in started for state,identity in live):self.enabled=False""")
    code=pio.once(code,'            captured[gen]=','            family_start_probe.enabled=True\n            captured[gen]=')
    code=pio.once(code,"gdb.write('FAMILY_ZERO","family_start_probe.enabled=True\ngdb.write('FAMILY_ZERO")
    code=pio.once(code,'class StartupScrub(gdb.Breakpoint):',inspect.getsource(terminal_owner_capabilities)+'\nclass StartupScrub(gdb.Breakpoint):')
    code=pio.once(code,"                gdb.write('STARTUP_SCRUB",f"""                if {case}<2 and reg('rax')==0xfffffffffffffff5:
                    assert struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]==0
                    generation=u64({s['scheduler_tasks']}+8)
                    terminal_owner_capabilities(mem({c['symbols']['clients']['value']},108),generation)
                    gdb.write('BLOCK_OWNER_RELEASE gen=%d endpoints=3 automatic=1\\n'%generation)
                gdb.write('STARTUP_SCRUB""")
    extra=f'''python
rpc={{}};rpc_results={{}}
class BlockIPC(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['process_ipc_syscall64']}),internal=True)
    def stop(self):
        try:
            if u64({s['syscall_rax']})!=53 or not pio_owner:return False
            slot=struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]
            if slot not in (0,2):return False
            address=u64({s['syscall_rsi']});head=struct.unpack('<3I',mem(address,12))
            d=pio_seen[pio_owner]
            if head==(1,140,16):
                words=struct.unpack('<4I',mem(address+12,16))
                if words[2]==2:
                    assert slot==2 and words[0]==pio_owner>>32 and words[3]==110
                    gdb.write('PIO_DEADLINE gen=%d expired=1\\n'%words[0])
                return False # Separate readiness/partial-transfer notification.
            assert not d['retired']
            state=rpc.setdefault(pio_owner,dict(requests=0,replies=0,pending=None))
            h=struct.unpack('<4I4QIiQ',mem(address+12,64))
            if slot==0:
                assert head==(1,140,64) and not any(mem(address+76,64))
                assert state['pending'] is None and state['requests']<8
                probes=bool(int(captured[pio_owner>>32][3],16)&16)
                n=state['requests']+(0 if probes else 4);state['requests']+=1
                assert h[:4]==(1,64,2 if n==0 else 1,0)
                assert h[4]==pio_owner-(1<<32) if n==1 else h[4]==pio_owner
                assert h[5]==(1 if n<4 else n-3)
                assert h[6]==(128 if n==2 else 0 if n<4 else 1 if n%2==0 else 127)
                assert h[8:]==(512,0,0)
                state['pending']=(h,len(d['data']),pio_events,n,pio_state())
                gdb.write('BLOCK_REQUEST gen=%d n=%d seq=%d lba=%d\\n'%(pio_owner>>32,n,h[5],h[6]))
            else:
                assert head[0:2]==(2,2060) and state['pending'] is not None
                q,before,events,n,device_state=state['pending'];status=(-22,-13,-22,-110)[n] if n<4 else 0
                assert h[:5]==(1,64,1,1,pio_owner)
                mode=int(captured[pio_owner>>32][3],16)&15
                assert h[5]==(q[5]^1 if mode==3 and not status else q[5])
                assert h[6:8]==q[6:8] and h[8:]==(0 if status else 512,status,0)
                assert head[2]==(64 if status else 576) and not any(mem(address+12+head[2],2048-head[2]))
                data=b'' if status else mem(address+76,512)
                if status:assert len(d['data'])==before and pio_events==events and pio_state()==device_state
                else:
                    assert len(d['data'])==before+512
                    assert data==bytes(d['data'][-512:])==bytes((i^(q[6]*17)^0xa5)&255 for i in range(512))
                state['replies']+=1;state['pending']=None
                gdb.write('BLOCK_REPLY gen=%d n=%d status=%d bytes=%d sha256=%s noio=%d\\n'%(pio_owner>>32,n,status,len(data),hashlib.sha256(data).hexdigest(),int(bool(status))))
        except Exception as e:
            gdb.write('BLOCK_OBSERVER_FAIL IPC '+repr(e)+'\\n');gdb.execute('quit 81')
        return False
class BlockResult(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['process_run_syscall64.pid']}),internal=True)
    def stop(self):
        try:
            if struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]!=0:return False
            if not pio_owner:return False
            owner,seq,lba,result,pointer=struct.unpack('<5Q',mem({result_address},40));result&=0xffffffff
            if result>=1<<31:result-=1<<32
            gdb.write('BLOCK_DIAGNOSTIC result owner=%d seq=%d lba=%d result=%d data=%d\\n'%(owner,seq,lba,result,len(pio_seen[pio_owner]['data'])))
            assert owner==pio_owner and owner in rpc
            options=int(captured[owner>>32][3],16);mode=options&15
            assert result in ((-71,) if mode==3 else (-32,-110) if mode else (0,))
            seen=rpc_results.setdefault(owner,0);assert seq==seen+1 and lba==(127 if seen%2 else 1)
            data=mem(pointer,512)
            assert data==(bytes([0xcc])*512 if result else bytes((i^(lba*17)^0xa5)&255 for i in range(512)))
            rpc_results[owner]+=1
            if not result:assert rpc[owner]['pending'] is None and rpc[owner]['replies']==seq+(4 if options&16 else 0)
            gdb.write('BLOCK_RESULT gen=%d seq=%d lba=%d result=%d sha256=%s\\n'%(owner>>32,seq,lba,result,hashlib.sha256(data).hexdigest()))
        except Exception as e:
            gdb.write('BLOCK_OBSERVER_FAIL RESULT '+repr(e)+'\\n');gdb.execute('quit 82')
        return False
BlockIPC();BlockResult()
end
'''
    return code[:-len('continue\n')]+extra+'continue\n'

REQUEST=re.compile(r'BLOCK_REQUEST gen=(\d+) n=(\d+) seq=(\d+) lba=(\d+)')
REPLY=re.compile(r'BLOCK_REPLY gen=(\d+) n=(\d+) status=(-?\d+) bytes=(\d+) sha256=([0-9a-f]{64}) noio=(\d+)')
RESULT=re.compile(r'BLOCK_RESULT gen=(\d+) seq=(\d+) lba=(\d+) result=(-?\d+) sha256=([0-9a-f]{64})')

def validate_rpc(trace,case):
    if 'OBSERVER_FAIL' in trace:raise ValueError('block observer failure')
    sequence=pio.modes(case);count=len(sequence)+2
    requests=list(REQUEST.finditer(trace));replies=list(REPLY.finditer(trace));results=list(RESULT.finditer(trace))
    expected_requests=[];expected_replies=[];expected_results=[]
    for run in range(2):
        for i,mode in enumerate(sequence,3):
            gen=run*count+i
            if case==2:continue
            for n in range(0 if i==3 else 4,5 if mode else 6):
                seq=1 if n<4 else n-3;lba=128 if n==2 else 0 if n<4 else 1 if n%2==0 else 127
                expected_requests.append((gen,n,seq,lba))
                if n<4 or mode in (0,3):
                    status=(-22,-13,-22,-110)[n] if n<4 else 0
                    data=b'' if status else pio.BLOCK_DISK[lba*512:(lba+1)*512]
                    expected_replies.append((gen,n,status,len(data),hashlib.sha256(data).hexdigest(),int(bool(status))))
                if n>=4 and case!=3:
                    result=-71 if mode==3 else -110 if mode else 0
                    data=bytes([0xcc])*512 if mode else pio.BLOCK_DISK[lba*512:(lba+1)*512]
                    expected_results.append((gen,seq,lba,result,hashlib.sha256(data).hexdigest()))
    if [tuple(map(int,m.groups())) for m in requests]!=expected_requests:raise ValueError('block request coverage')
    if [tuple(int(v) if i!=4 else v for i,v in enumerate(m.groups())) for m in replies]!=expected_replies:raise ValueError('block reply coverage')
    actual_results=[(int(m[1]),int(m[2]),int(m[3]),-110 if int(m[4])==-32 else int(m[4]),m[5]) for m in results]
    if actual_results!=expected_results:raise ValueError('block client coverage')
    for q in requests:
        gen,n=int(q[1]),int(q[2])
        bind=list(re.finditer(r'PIO_BIND gen='+str(gen)+r' recycled=1',trace))
        fence=list(re.finditer(r'PIO_RETIRE gen='+str(gen)+r' identify=',trace))
        if len(bind)!=1 or len(fence)!=1 or not bind[0].end()<q.start()<fence[0].start():raise ValueError('block generation order')
        reply=next((r for r in replies if r[1]==q[1] and r[2]==q[2]),None)
        if reply is not None and not q.end()<reply.start()<reply.end()<fence[0].start():raise ValueError('block reply order')
        following=next((r for r in requests if r[1]==q[1] and int(r[2])==n+1),None)
        if following and (reply is None or reply.end()>following.start()):raise ValueError('block single in-flight')
        if n>=4:
            result=next((r for r in results if r[1]==q[1] and r[2]==q[3]),None)
            if result is not None:
                # A completed reply or EPIPE can be consumed after child reap.
                # It must still precede the next owner and the client's fence.
                root=(gen-1)//count*count+1
                root_fence=list(re.finditer(r'FAMILY_FENCE slot=0 gen='+str(root)+r' ipc=1 heap=1 profile=1',trace))
                next_bind=next(re.finditer(r'PIO_BIND gen='+str(gen+1)+r' recycled=1',trace),None)
                if len(root_fence)!=1:raise ValueError('block client fence')
                end=min(root_fence[0].start(),next_bind.start() if next_bind else len(trace))
                if not q.end()<result.start()<result.end()<end or reply and reply.end()>result.start() or following and result.end()>following.start():raise ValueError('block output order')
    for label,events in (('BLOCK_REQUEST',requests),('BLOCK_REPLY',replies),('BLOCK_RESULT',results)):
        if trace.count(label)!=len(events):raise ValueError('block malformed event')

def validate_owner_release(trace,case):
    count=len(pio.modes(case))+2
    releases=list(re.finditer(r'BLOCK_OWNER_RELEASE gen=(\d+) endpoints=3 automatic=1',trace))
    if [int(m[1]) for m in releases]!=([1,count+1] if case<2 else []) or trace.count('BLOCK_OWNER_RELEASE')!=len(releases):raise ValueError('block owner release coverage')
    for run,m in enumerate(releases):
        retire=list(re.finditer(r'PIO_RETIRE gen='+str((run+1)*count)+r' identify=',trace))
        fence=list(re.finditer(r'FAMILY_FENCE slot=0 gen='+m[1]+r' ipc=1 heap=1 profile=1',trace))
        results=[r for r in RESULT.finditer(trace) if run*count<int(r[1])<=(run+1)*count]
        if len(retire)!=1 or len(fence)!=1 or not retire[0].end()<m.start()<m.end()<fence[0].start() or any(r.end()>m.start() for r in results):raise ValueError('block owner release order')

def validate(serial,trace,case,oom=None):
    result=pio.validate(serial,trace,case,oom,block=True)
    validate_rpc(trace,case)
    validate_owner_release(trace,case)
    count=len(pio.modes(case))+2
    expected=[run*count+i for run in range(2) for i in range(3,count+1)]
    if list(map(int,re.findall(r'PIO_DEADLINE gen=(\d+) expired=1',trace)))!=expected or trace.count('PIO_DEADLINE')!=len(expected):raise ValueError('PIO deadline guest proof')
    return result

def normalize_memory_link(raw,entry):
    if not 0xffffffff80000000<=entry<=0xffffffffffffffff or not 64<=len(raw)<=1048576 or raw[:5]!=b'\x7fELF\x01':raise ValueError('memory link object/address')
    instruction=b'\x48\xc7\xc0'+struct.pack('<I',entry&0xffffffff)
    if raw.count(instruction)!=1:raise ValueError('memory link exact MOV')
    offset=raw.index(instruction)+3
    return raw[:offset]+bytes(4)+raw[offset+4:]

def mechanisms(image):
    # entry embeds C payload; elf64_loader embeds the user catalog. Their
    # artifact bytes legitimately differ; every standalone mechanism is fixed.
    names=('address_space','bootstrap_core','context_core','cooperative_scheduler','cpu_budget',
        'exceptions','fp_context','frame_claim','identity_core','image_frames','ipc_admission',
        'native_heap','native_ipc_integrity','native_ipc_memory_full','native_ipc_memory',
        'native_ipc_pool','native_ipc','native_memory','physical_memory','queue_core',
        'request_admission','startup_stack','syscall_profile','task_frames','terminal_status',
        'timer_interrupt','user_access','user_execution')
    result={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
    inner=startup.family.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    layout=startup.family.payload.validate(inner)
    startup.family.payload.verify_outer(inner,startup.family.payload.read_bounded(image))
    entry=layout['symbols']['reist_native_memory']['value']
    result['physical_memory']=hashlib.sha256(normalize_memory_link((image.parent/'physical_memory.o').read_bytes(),entry)).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--pio-reference',type=Path,default=ROOT/'build/codex-agent/r83ai-block/pio-reference/x86_64/reist-x86_64-bootstrap.elf');a=parser.parse_args()
    folder=startup.family.evidence_directory(a.evidence)/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,cases=[]);started=time.monotonic()
    try:
        image=a.image.resolve()
        if not image.is_relative_to(ROOT/'build'):raise ValueError('block image scope')
        reference=mechanisms(ROOT/'build/codex-agent/r83ah-pio/native/x86_64/reist-x86_64-bootstrap.elf')
        amended_names=('cooperative_scheduler','native_ipc')
        for name in amended_names:reference.pop(name)
        amended=None
        pio_image=a.pio_reference.resolve()
        if not pio_image.is_relative_to(ROOT/'build') or pio_image==image:raise ValueError('independent block PIO reference scope')
        pio_reference=mechanisms(pio_image)
        pio_amended={name:pio_reference.pop(name) for name in amended_names}
        if pio_reference!=reference:raise ValueError('block PIO reference mechanism drift')
        for case in range(4):
            if case:
                out=folder/f'build-{case}';out.mkdir()
                with (out/'build.log').open('wb') as log:
                    r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeBlock','-PIOCase',str(case),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode:raise ValueError('block fixture build')
                image=out/'x86_64/reist-x86_64-bootstrap.elf'
            current=mechanisms(image);changed={name:current.pop(name) for name in amended_names}
            if current!=reference or changed!=pio_amended or amended is not None and changed!=amended:raise ValueError('block kernel mechanism drift')
            amended=changed
            catalog=(image.parent/'boot-programs.bin').read_bytes()
            if len(catalog)!=4*36896:raise ValueError('block catalog length')
            candidates=[d for d in image.parent.glob('programs-*') if d.is_dir() and (d/'boot-programs.bin').is_file() and (d/'boot-programs.bin').read_bytes()==catalog]
            if not candidates:raise ValueError('block catalog provenance')
            child=(candidates[0]/'program2.prg').read_bytes()
            if any((d/'program2.prg').read_bytes()!=child for d in candidates):raise ValueError('block ambiguous child')
            record=pio.producer.prepare(child,[]);allocations=startup.creation_allocations(record)
            if record[:32800]!=catalog[73792:106592] or allocations<=9:raise ValueError('block child allocation extent')
            linkmap=(candidates[0]/'program0.map').read_text()
            witness=re.findall(r'^\s*(?:0x)?([0-9a-f]+)\s+(?:[0-9a-f]+\s+)*block_result_record\s*$',linkmap,re.M)
            if len(witness)!=1:raise ValueError('block witness link map')
            result_address=int(witness[0],16)
            inner=startup.family.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=startup.family.payload.validate(inner)
            startup.family.payload.verify_outer(inner,startup.family.payload.read_bounded(image))
            if c['layout_version']!=4:raise ValueError('block C layout')
            s=startup.family.symbols(image)
            variants=[(4096,n) for n in (0,1,2,3,6,9)] if case==1 else [(4096,None),(8192,None)] if case==0 else [(4096,None)]
            for ram,oom in variants:
                out=folder/f'guest-{case}-{ram}-{oom}';out.mkdir()
                fixture=None if case==2 else pio.Fixture(out,block=True)
                serial,trace=startup.family.programs.capture(image,out,observer(s,c,out,ram,case,oom,record,result_address),ram,fixture)
                tasks=validate(serial,trace,case,oom)
                summary['cases'].append(dict(case=case,ram=ram,oom=oom,tasks=tasks,allocations=allocations,record_sha256=hashlib.sha256(record).hexdigest()))
                print('BLOCK_GUEST_OK',case,ram,oom,flush=True)
        summary.update(passed=True,mechanisms=reference,amended_mechanisms=amended)
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('BLOCK_FAIL',error);return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('BLOCK_EVIDENCE',folder)
    return 0

if __name__=='__main__':raise SystemExit(main())
