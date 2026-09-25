"""Bounded query observations supplement the unchanged CPU/lifecycle oracle."""
from pathlib import Path
import json, struct
import run_qemu_x86_64_desktop_cpu as cpu

need=cpu.need

def query_transport(case):
    if case not in (8,9):return cpu.transport
    # clone reads the module's original file, not the already transformed code.
    # Repeat the existing CPU host deadlines when adding instruction timing.
    return cpu.clone(cpu.legacy.transport,[
        ('capture_started+27 if service_cpu_budget','capture_started+357 if service_cpu_budget'),
        ('time.monotonic()-capture_started>30:','time.monotonic()-capture_started>360:'),
        ("    command+=list(media_arguments)",
         "    command+=['-icount','shift=3,sleep=on']\n    command+=list(media_arguments)"),
    ],'query_instruction_clock')

EXTRA=r'''
query_count=0
def query_start(t,slot):
    global query_count
    if slot==2:syscall_hook.enabled=True
    if slot!=0:return
    query_count=0
    query_hook.enabled=True
    cap_hook.enabled=True
def query_before():
    global query_count
    if d(S['scheduler_current_slot'])!=0:return
    state=struct.unpack('<6Q',mem(S['query_state64'],48))
    t=task(0)
    assert t[0]==2 and state[0]==t[1] and state[1]==0 and 1<=state[2]<=8
    assert all(state[i]^state[i+3]==0xffffffffffffffff for i in range(3))
    number=q(S['syscall_rax']);value=reg('rax')
    assert number in (22,42)
    assert value==(t[1] if number==22 else q(S['scheduler_last_tick'])*10)
    query_count+=1
    assert query_count<=8
    if query_count==8:query_hook.enabled=False
def query_cap():
    if d(S['scheduler_current_slot'])!=0:return
    state=struct.unpack('<6Q',mem(S['query_state64'],48))
    t=task(0)
    assert t[0]==2 and state[:3]==(t[1],0,1)
    assert all(state[i]^state[i+3]==0xffffffffffffffff for i in range(3))
    cap_hook.enabled=False
query_hook=Hook('query_resume64',query_before)
query_hook.enabled=False
cap_hook=Hook('query_resume64.dispatch',query_cap)
cap_hook.enabled=False
'''

def replay(folder,serial,trace,count):
    folder=Path(folder)
    proof=cpu.replay(folder,serial,trace,count)
    config=json.loads((folder/'config.json').read_text())
    s=config['s'];raw=(folder/'reads.bin').read_bytes()
    samples={};caps={};finishes=0;name=None;reads=[];registers={}
    for line in (folder/'reads.jsonl').read_text().splitlines():
        row=json.loads(line)
        if 'begin' in row:name=row['begin'];reads=[];registers={}
        elif 'address' in row:
            reads.append((row['address'],raw[row['offset']:row['offset']+row['bytes']]))
        elif 'register' in row:registers[row['register']]=row['value']
        elif 'end' in row:
            def one(address,n):
                matches=[data for at,data in reads if at==address and len(data)==n]
                need(len(matches)==1,'unique query observation')
                return matches[0]
            if name in ('query_before','query_cap') and any(at==s['query_state64'] for at,_ in reads):
                state=struct.unpack('<6Q',one(s['query_state64'],48))
                task=struct.unpack('<512Q',one(s['scheduler_tasks'],4096))
                need(struct.unpack('<I',one(s['scheduler_current_slot'],4))[0]==0,'query root slot')
                need(task[0]==2 and state[:2]==(task[1],0) and 1<=state[2]<=8,'query owner/bound')
                need(all(state[i]^state[i+3]==2**64-1 for i in range(3)),'query complements')
                if name=='query_before':
                    number=struct.unpack('<Q',one(s['syscall_rax'],8))[0]
                    need(number in (22,42),'query syscall identity')
                    expected=task[1] if number==22 else struct.unpack('<Q',one(s['scheduler_last_tick'],8))[0]*10
                    need(registers['rax']==expected,'query actual return value')
                    samples.setdefault(task[1],[]).append(state[2])
                    need(len(samples[task[1]])<=8,'query observer capacity')
                else:
                    need(state[2]==1 and task[1] not in caps,'exact mandatory dispatch once per root')
                    caps[task[1]]=1
            elif name=='finish':
                need(one(s['query_state64'],48)==bytes(48),'no final burst owner')
                finishes+=1
            name=None
    need(finishes==2,'both run ownership resets')
    if config['query_case'] in (8,9):
        need(len(samples)==2 and all(len(values)==8 for values in samples.values()),'two bounded query samples')
        need(caps.keys()==samples.keys(),'actual eighth-query boundary for both roots')
    return dict(lifecycle=proof,queries=samples,caps=caps,cleared=finishes)

def capture(image,folder,case=0,oom=None):
    need(case in range(10),'query fixture case')
    image,folder=Path(image),Path(folder)
    folder.mkdir(parents=True,exist_ok=False)
    legacy=cpu.legacy
    c=legacy.payload.validate((image.parent/'reist-x86_64-c-core.elf').read_bytes())
    symbols=legacy.transport.symbols(image)
    fixture=next(image.parent.glob('programs-*'))
    hits=[line.split()[0] for line in (fixture/'program0.map').read_text().splitlines()
          if line.split() and line.split()[-1]=='reist_large_image_selection']
    need(len(hits)==1,'exact selector')
    from build_x86_64_large_image import prepare
    count=legacy.allocations(prepare((fixture/'program2.prg').read_bytes(),[]))
    equivalent={8:0,9:7}.get(case,case)
    ownership=cpu.root_ownership() if equivalent==7 else cpu.base
    code=ownership.observer(symbols,c,folder,equivalent,oom,int(hits[0],16))
    replacements=[
        ("Hook('scheduler_enter_task64.state_published',start)","Hook('process_run_enter64.query_admitted',start)"),
        ("Hook('process_run_syscall64',syscall)","syscall_hook=Hook('process_run_syscall64',syscall)\nsyscall_hook.enabled=False"),
        ("    proofs.add(gen);emit('stack',", "    syscall_hook.enabled=False\n    proofs.add(gen);emit('stack',"),
        ('    cpu_initial(t,slot)\n','    cpu_initial(t,slot)\n    query_start(t,slot)\n'),
        ('def finish():\n    global runs\n',
         "def finish():\n    global runs\n    assert mem(S['query_state64'],48)==bytes(48)\n"),
        ('\nend\ncontinue\n',EXTRA+'\nend\ncontinue\n'),
    ]
    for before,after in replacements:
        need(code.count(before)==1,'query observer fragment '+before)
        code=code.replace(before,after)
    need(code.count("struct.pack('<Q',CASE)")==2,'two exact selector writes/readbacks')
    code=code.replace("struct.pack('<Q',CASE)","struct.pack('<Q',%d)"%case)
    config=json.loads((folder/'config.json').read_text());config['query_case']=case
    (folder/'config.json').write_text(json.dumps(config,sort_keys=True),encoding='ascii')
    transport=query_transport(case)
    serial,trace=transport.capture(image,folder,code,4096,service_cpu_budget=True)
    (folder/'serial.txt').write_text(serial);(folder/'trace.txt').write_text(trace)
    return replay(folder,serial,trace,count)
