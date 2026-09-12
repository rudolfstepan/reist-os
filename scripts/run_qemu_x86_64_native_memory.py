"""NativeRAM: one kernel,1/4/8GiB, real full-width paging and exact retirement."""
from pathlib import Path
import argparse,json,re,struct,time,uuid,subprocess
import run_qemu_x86_64_native_ipc as ipc
import build_x86_64_c_payload as payload
from run_qemu_x86_64_task_frames import BEFORE,AFTER,FREE
from run_qemu_x86_64_spawn_oom import symbols
from measure_cpp_baseline import suppress_windows_test_dialogs
ROOT=Path(__file__).resolve().parents[1]

# Same13-frame/25-retirement/fence/order/zero oracle as the128MiB profile;
# only this explicit physical profile has a16GiB frame/count bound.
def validate_trace(trace,rows):
    before=list(BEFORE.finditer(trace));after=list(AFTER.finditer(trace));frees=list(FREE.finditer(trace))
    expected={(m,slot,1+slot):(4 if slot==0 else 3 if m==1 else 5) for m in (1,2,3) for slot in (0,1)}
    expected.update({(4,s,10+s):3 if s==3 else 4 for s in range(4)})
    expected.update({(5,s,20+s):4 for s in range(4)})
    expected.update({(6,0,30):4,(6,1,31):8,(6,1,32):8})
    expected.update({(8,r['slot'],r['generation']):r['state'] for r in rows})
    if len(before)!=25 or len(after)!=25 or len(frees)>325:raise RuntimeError('frame count')
    seen=set();consumed=0;native=[]
    for i,(b,a) in enumerate(zip(before,after)):
        seq,mode,slot,gen,state,root,active,free,fp,frames=b.groups()
        seq,mode,slot,gen,state,free,fp=map(int,(seq,mode,slot,gen,state,free,fp))
        frames=[int(f,16) for f in frames.split(',')];owned=[f for f in frames if f]
        if seq!=i+1 or (mode,slot,gen) in seen or expected.get((mode,slot,gen))!=state or fp!=1:
            raise RuntimeError('frame identity/state/FP')
        seen.add((mode,slot,gen))
        if mode==8:native.append((seq,slot,gen))
        if len(frames)!=13 or not all(frames[8:]) or len(set(owned))!=len(owned) or any(not 0<f<0x400000000 or f%4096 for f in owned):
            raise RuntimeError('frame ownership')
        root,active=int(root,16),int(active,16)
        if root!=frames[-1] or root==active or not 0<active<0x400000000 or active%4096:
            raise RuntimeError('active root')
        if tuple(map(int,a.groups()))!=(seq,gen,state,1,free+len(owned),1) or not 0<free<free+len(owned)<=4194304:
            raise RuntimeError('frame balance/scrub')
        if not (after[i-1].end() if i else -1)<b.start()<b.end()<a.start():raise RuntimeError('frame order')
        calls=[f for f in frees if b.end()<=f.start()<a.start()];consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(seq,f) for f in owned]:raise RuntimeError('backend free order')
    if consumed!=len(frees) or seen!=set(expected):raise RuntimeError('unowned or missing release')
    if native!=[(18+i,r['slot'],r['generation']) for i,r in enumerate(rows)]:raise RuntimeError('serial/frame lifecycle mismatch')
    fences=list(re.finditer(r'PROCESS_FENCE_OK seq=(\d+) slot=(\d+) gen=(\d+)',trace))
    if [tuple(map(int,f.groups())) for f in fences]!=native:raise RuntimeError('exact independent fences')
    for f,(seq,_,_) in zip(fences,native):
        if not after[seq-2].end()<f.start()<f.end()<=before[seq-1].start():raise RuntimeError('fence after free')
    zeros=list(re.finditer(r'PROCESS_ZERO_OK run=(\d+) zero=(\d+) free=(\d+) initial=(\d+) reaps=(\d+) generation=(\d+) ticks=(\d+)',trace))
    if len(zeros)!=2:raise RuntimeError('final zero count')
    for i,z in enumerate(zeros):
        run,zero,free,initial,reaps,gen,ticks=map(int,z.groups())
        if (run,zero,reaps,gen)!=(i+1,1,4,4*(i+1)) or not 0<free==initial<=4194304 or not 6<=ticks<256:
            raise RuntimeError('final generation/zero/frame balance')
        if not after[20+i*4].end()<z.start() or i==0 and z.end()>before[21].start():
            raise RuntimeError('run zero ordering')



def observer(s,c,log,ram):
    code=ipc.observer_commands(s,c,log)
    if not code.endswith('continue\n'):raise ValueError('memory observer template')
    high=0xffffffff80000000
    state=c['symbols']['native_memory_state']['value']
    pd=s['direct_page_directory'];tables=s['direct_page_tables']
    # A single boot checkpoint, batched raw reads, no debugger mutation.
    check=f'''python
class RAMWatch(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex({s['physical_frame_test_high_window64']}),internal=True)
        self.calls=0
    def stop(self):
        self.calls+=1
        try:
            assert self.calls==1 and not reg('eflags')&512
            managed,free,initialized,inverse=struct.unpack('<4I',mem({state},16))
            assert ({ram}-32)*256<managed==free<={ram}*256
            assert (initialized,inverse)==(1,0xfffffffe)
            usable=mem({state}+64,524288)
            population=tuple(bin(x).count('1') for x in range(256))
            assert sum(population[x] for x in usable)==managed
            assert not any(mem({state}+64+524288,524288))
            entries=struct.unpack('<8192Q',mem({pd},65536))
            huge=mixed=0
            for region,pde in enumerate(entries):
                bits=int.from_bytes(usable[region*64:region*64+64],'little')
                if not bits: assert pde==0;continue
                if bits==(1<<512)-1:
                    assert pde&~0x60==(1<<63)|(region<<21)|0x83
                    huge+=1;continue
                assert pde&7==3 and pde>>63==1 and not pde&0x80
                physical=pde&0x3fffff000
                assert {tables-high}<=physical<{tables-high}+512*4096
                assert pde&~0x60==(1<<63)|physical|3
                leaves=struct.unpack('<512Q',mem({high}+physical,4096))
                for i,leaf in enumerate(leaves):
                    expected=((1<<63)|((region*512+i)<<12)|3) if bits>>i&1 else 0
                    assert leaf&~0x60==expected
                mixed+=1
            assert huge>0 and 0<mixed<=512
            # Every arena4KiB higher-half leaf is RW/NX, no U or large bit.
            count=({payload.MEMORY_ARENA_BYTES}+4095)//4096
            highpt=struct.unpack('<'+str(count)+'Q',mem({s['high_page_table']}+512*8,count*8))
            assert all(p&~0x60==(1<<63)|(0x200000+i*4096)|3 for i,p in enumerate(highpt))
            above=any(usable[131072:])
            assert above==({ram}>=4096)
            gdb.write('NATIVE_MEMORY_MAP_OK ram={ram} managed=%d huge=%d mixed=%d high=%d\\n'%(managed,huge,mixed,above))
            self.enabled=False
        except Exception as e:
            import traceback
            gdb.write(traceback.format_exc())
            gdb.write('NATIVE_MEMORY_OBSERVER_FAIL '+repr(e)+'\\n')
            gdb.execute('quit 31')
        return False
RAMWatch()
end
continue
'''
    return code[:-len('continue\n')]+check

def validate_memory(trace,rows,ram):
    validate_trace(trace,rows)
    ipc.validate_ipc_trace(trace,rows,0)
    if 'OBSERVER_FAIL' in trace:raise ValueError('memory observer failure')
    marks=re.findall(r'NATIVE_MEMORY_MAP_OK ram=(\d+) managed=(\d+) huge=(\d+) mixed=(\d+) high=(\d+)',trace)
    if len(marks)!=1 or trace.count('NATIVE_MEMORY_MAP_OK')!=1:raise ValueError('memory map witness')
    actual,managed,huge,mixed,high=map(int,marks[0])
    if actual!=ram or not (ram-32)*256<managed<=ram*256 or huge<1 or not 0<mixed<=512 or high!=(ram>=4096):
        raise ValueError('memory map bounds')
    floor=0x100000000 if ram>=4096 else 0x20000000
    for match in BEFORE.finditer(trace):
        if any(int(f,16)<floor for f in match[10].split(',') if int(f,16)):
            raise ValueError('missing high physical consumer proof')

def rejected_commands(s,log,case):
    if case not in ('overflow','size','reserved'):raise ValueError('boot fault case')
    start=s['x86_64_physical_memory_init32']-0xffffffff80000000
    # GDB boot input injection ONLY before admission, not a runtime bypass.
    mutation={'overflow':"set *(unsigned long long*)($map+4)=0xfffffffffffff000\nset *(unsigned long long*)($map+12)=0x2000\n",
              'size':"set *(unsigned int*)$map=19\n",
              'reserved':"set *(unsigned int*)($map+20)=2\nset *(unsigned int*)($ebx+44)=24\n"}[case]
    return ('set logging file '+log.as_posix()+'\nset logging enabled on\n'+
        f'break *{start:#x}\ncommands\nsilent\nset $map=*(unsigned int*)($ebx+48)\n'+mutation+
        'detach\nquit\nend\ncontinue\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();base=a.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence scope')
    suppress_windows_test_dialogs()
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();result=dict(passed=False,cases=[])
    try:
        image=a.image.resolve();inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
        c=payload.validate(inner);payload.verify_outer(inner,payload.read_bounded(image))
        if c['layout_version']!=3:raise ValueError('NativeRAM layout3 required')
        s=symbols(image)
        for ram in (1024,4096,8192):
            target=folder/str(ram);target.mkdir()
            serial,trace=ipc.capture(image,target,observer(s,c,target/'frame-trace.log',ram),ram)
            rows=ipc.validate(serial,0);validate_memory(trace,rows,ram)
            result['cases'].append(dict(ram_mib=ram,tasks=rows))
            print('NATIVE_MEMORY_GUEST_OK ram='+str(ram),flush=True)
        for case in ('overflow','size','reserved'):
            target=folder/case;target.mkdir()
            serial,trace=ipc.capture(image,target,rejected_commands(s,target/'frame-trace.log',case),1024)
            if serial.count('REIST_X86_64_MEMORY_MAP_ERROR')!=1 or 'REIST_X86_64_LONG_MODE_OK' in serial or 'PHYSICAL_MEMORY_OK' in serial:
                raise ValueError('invalid boot map progressed '+case)
            result['cases'].append(dict(rejected=case))
        result['passed']=True;print('NATIVE_MEMORY_RUNTIME_OK evidence='+str(folder));return 0
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as e:
        result['error']=str(e);print('NATIVE_MEMORY_RUNTIME_FAIL '+str(e)+' evidence='+str(folder));return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

if __name__=='__main__':raise SystemExit(main())
