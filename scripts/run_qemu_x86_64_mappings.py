"""Actual R/RX/RW mapping snapshots and real write/NX faults; read-only debugger."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid
from run_qemu_x86_64_spawn_oom import observed_boot,symbols
from run_qemu_x86_64_requests import MECHANISMS
from run_qemu_x86_64_ipc_handoff import REAP
from run_qemu_x86_64_fault import RECEIPT as FAULT_REAP
ROOT=Path(__file__).resolve().parents[1]
NX=1<<63;DM=0xffff800000000000;LIMIT=0x08000000
MAP=re.compile(r'MAPPING_TABLES generation=(\d+) result=(\d+) if0=(\d+)')
FAULT=re.compile(r'MAPPING_FAULT generation=(\d+) vector=(\d+) error=(\d+) cr2=([0-9a-f]+) rip=([0-9a-f]+) cs=([0-9a-f]+)')
MAGIC=bytes.fromhex('c35441444f52584e')

def elf_pages(data):
    if not 64<=len(data)<=65536 or data[:6]!=b'\x7fELF\x02\x01':raise RuntimeError('invalid ELF64 image')
    ph=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
    if size!=56 or not 1<=count<=4 or ph+size*count>len(data):raise RuntimeError('invalid program headers')
    pages={}
    for i in range(count):
        kind,flags,offset,address,_,length,memory,alignment=struct.unpack_from('<IIQQQQQQ',data,ph+i*size)
        if kind==0:continue
        if kind!=1 or flags not in (4,5,6) or not 0< memory or length>memory or offset+length>len(data) or alignment!=4096:
            raise RuntimeError('invalid load segment')
        if not 0x400000<=address<address+memory<=0x408000 or (offset^address)&4095:raise RuntimeError('invalid segment range')
        for page in range((address-0x400000)//4096,(address+memory-1-0x400000)//4096+1):
            if page in pages:raise RuntimeError('overlapping segment pages')
            content=bytearray(4096);start=max(address,0x400000+page*4096);end=min(address+length,0x401000+page*4096)
            if end>start:content[start-(0x400000+page*4096):end-(0x400000+page*4096)]=data[offset+start-address:offset+end-address]
            pages[page]=(flags,bytes(content))
    return pages

def child_outcome(native,case):
    pages=elf_pages((native/'reist-x86_64-user-child.elf').read_bytes())
    if set(pages)!={0,1} or (pages[0][0],pages[1][0])!=(5,4) or pages[1][1]!=MAGIC+bytes(4088):
        raise RuntimeError('fixture must contain distinct compact RX and R pages')
    code=pages[0][1]
    reads=list(re.finditer(re.escape(b'\x48\xb8'+MAGIC)+rb'\x48\x39\x05....',code,re.S))
    if len(reads)!=1 or 0x400000+reads[0].start()+17+struct.unpack_from('<i',code,reads[0].start()+13)[0]!=0x401000:
        raise RuntimeError('missing actual readonly data comparison')
    if case==1:
        packet=bytes.fromhex('b80900000031f631d20f05');hits=list(re.finditer(re.escape(packet),code))
        if len(hits)!=1:raise RuntimeError('missing normal EXIT instruction')
        return 0x400000+hits[0].end()
    packet=rb'\xc6\x05....\x90\x0f\x0b' if case==2 else rb'\x48\x8d\x05....\xff\xe0'
    hits=list(re.finditer(packet,code,re.S))
    if len(hits)!=1:raise RuntimeError('missing mapping violation instruction')
    offset=hits[0].start();disp=struct.unpack_from('<i',code,offset+(2 if case==2 else 3))[0]
    if 0x400000+offset+7+disp!=0x401000:raise RuntimeError('wrong violation target')
    return 0x400000+offset if case==2 else 0x401000

def validate_snapshot(plan,records):
    if len(plan)!=192:raise RuntimeError('plan size')
    tables=list(struct.unpack_from('<4Q',plan));source=list(struct.unpack_from('<8Q',plan,32));flags=list(plan[96:104])
    private=list(struct.unpack_from('<8Q',plan,104));stack,k0,k1=struct.unpack_from('<3Q',plan,168)
    frames=tables+source+private+[stack];nonzero=[x for x in frames if x]
    if any(not 0<x<LIMIT or x%4096 for x in nonzero) or len(set(nonzero))!=len(nonzero) or not all(tables) or not stack:
        raise RuntimeError('physical ownership')
    if (k0&3,k1&3)!=(3,3) or not k0&NX or k1&NX or any(k&~(NX|0x07fff023) for k in (k0,k1)):
        raise RuntimeError('supervisor template')
    if any(not k&0x07fff000 or k&0x07fff000 in nonzero for k in (k0,k1)):raise RuntimeError('kernel frame alias')
    if records.get('ptr')!=struct.pack('<21Q',*[DM+f if f else 0 for f in frames]):raise RuntimeError('cached direct-map pointers')
    expected_keys={'ptr','stack',*(f'table{i}' for i in range(4))}
    expected=[[0]*512 for _ in range(4)];expected[0][0]=tables[1]|7;expected[0][256]=k0;expected[0][511]=k1
    expected[1][0]=tables[2]|7;expected[2][2]=tables[3]|7;expected[3][8]=stack|7|NX
    for i,f in enumerate(flags):
        if f not in (0,4,5,6) or bool(source[i])!=bool(f) or bool(private[i])!=(f==6):raise RuntimeError('ELF/private flags')
        if not f:continue
        expected_keys.add(f'source{i}')
        if len(records.get(f'source{i}',b''))!=4096:raise RuntimeError('source snapshot')
        if f==6:
            expected_keys.add(f'private{i}')
            if records.get(f'private{i}')!=records[f'source{i}']:raise RuntimeError('private copy')
        expected[3][i]=(private[i] if f==6 else source[i])|5|(2 if f==6 else 0)|(0 if f==5 else NX)
    if records.get('stack')!=bytes(4096) or set(records)!=expected_keys:raise RuntimeError('stack or snapshot ownership')
    for i in range(4):
        if records.get(f'table{i}')!=struct.pack('<512Q',*expected[i]):raise RuntimeError('page-table permissions/guards')
    return flags

def validate_sources(flags,records,sources):
    if {i for i,f in enumerate(flags) if f}!=set(sources):raise RuntimeError('source mapping layout')
    for i,(flag,data) in sources.items():
        if flags[i]!=flag or records.get(f'source{i}')!=data:raise RuntimeError('staged source content changed')

def commands(s,folder):
    def at(name,kind='unsigned char'):return f'*({kind}*){s[name]:#x}'
    active=at('scheduler_mode')+' == 7'
    path=folder.resolve().as_posix();log=path+'/mapping-trace.log'
    if not re.fullmatch(r'[A-Za-z0-9_./:-]+',path):raise RuntimeError('unsafe debugger evidence path')
    def dump(suffix,start,length):
        # This GDB dump command treats quotes as literal filename characters.
        return f'eval "dump binary memory {path}/g%u-{suffix}.bin %#llx %#llx", $generation, {start}, ({start})+{length}\n'
    c=f'set logging file {log}\nset logging redirect on\nset logging enabled on\nset $maps = 0\nset $faults = 0\n'
    c+=f'break *{s["reist_x64_address_space_build.return"]:#x} if {active}\ncommands 1\nsilent\n'
    c+='set $maps=$maps+1\nif $maps>3 || $rax!=1 || ($eflags&512)!=0\nquit 2\nend\n'
    c+=f'set $generation=*(unsigned int*)({s["scheduler_identity_pool"]:#x}+20)\n'
    c+='printf "MAPPING_TABLES generation=%u result=%u if0=%u\\n",$generation,$rax,($eflags&512)==0\n'
    c+=dump('plan','$r12',192)+dump('ptr','$rsp',168)
    for i in range(4):c+=dump(f'table{i}',f'*(unsigned long long*)($rsp+{i*8})',4096)
    for i in range(8):
        c+=f'if *(unsigned long long*)($rsp+{32+i*8}) != 0\n'+dump(f'source{i}',f'*(unsigned long long*)($rsp+{32+i*8})',4096)+'end\n'
        c+=f'if *(unsigned long long*)($rsp+{96+i*8}) != 0\n'+dump(f'private{i}',f'*(unsigned long long*)($rsp+{96+i*8})',4096)+'end\n'
    c+=dump('stack','*(unsigned long long*)($rsp+160)',4096)+'continue\nend\n'
    c+=f'break *{s["x86_64_scheduler_user_exception64"]:#x} if {active}\ncommands 2\nsilent\n'
    c+='set $faults=$faults+1\nif $faults>2\nquit 3\nend\n'
    c+=f'printf "MAPPING_FAULT generation=%u vector=%llu error=%llu cr2=%llx rip=%llx cs=%llx\\n",{at("scheduler_dynamic_child_generation","unsigned int")},*(unsigned long long*)($rdi+120),*(unsigned long long*)($rdi+128),$cr2,*(unsigned long long*)($rdi+136),*(unsigned long long*)($rdi+144)\ncontinue\nend\n'
    c+=f'break *{s["scheduler_return64"]:#x} if {active}\ncommands 3\nsilent\ndetach\nquit\nend\ncontinue\n'
    return c

def validate_receipts(serial,trace,case,rip):
    maps=list(MAP.finditer(trace));faults=list(FAULT.finditer(trace))
    if [tuple(map(int,r.groups())) for r in maps]!=[(40,1,1),(41,1,1),(42,1,1)]:raise RuntimeError('mapping generation/count')
    if len(faults)!=(0 if case==1 else 2):raise RuntimeError('fault count')
    for i,r in enumerate(faults):
        g,v,e,a,ip,cs=r.groups()
        if (int(g),int(v),int(e),int(a,16),int(ip,16),int(cs,16))!=(41+i,14,7 if case==2 else 21,0x401000,rip,0x33):
            raise RuntimeError('real page-fault protection')
        if not maps[i+1].end()<=r.start()<(maps[2].start() if i==0 else len(trace)):raise RuntimeError('fault after correct generation mapping')
    receipts=list((REAP if case==1 else FAULT_REAP).finditer(serial));runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    done=list(re.finditer('MAPPING_OK',serial))
    if any(len(x)!=2 for x in (receipts,runs,done)) or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:raise RuntimeError('terminal mapping witnesses')
    for i,r in enumerate(receipts):
        code,g,parent,q,ip=(int(v,16) for v in r.groups())
        if (code,g,q,ip)!=(77 if case==1 else 14,41+i,0,rip) or parent not in (1,6,7):raise RuntimeError('exact mapping reap')
        if not (done[i-1].end() if i else -1)<r.start()<r.end()<=runs[i].start()<runs[i].end()<=done[i].start():
            raise RuntimeError('reap before successful WAIT/RUN')

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);args=p.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True);summary=dict(passed=False,cases=[]);start=time.monotonic()
    try:
        for case in (1,2,3):
            folder=attempt/str(case);folder.mkdir()
            with (folder/'build.log').open('wb') as out:
                r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                    '-OutputDirectory',folder.relative_to(ROOT).as_posix(),'-MappingCase',str(case)],cwd=ROOT,
                    stdout=out,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if r.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
            native=folder/'x86_64';image=native/'reist-x86_64-bootstrap.elf';s=symbols(image);rip=child_outcome(native,case)
            serial,_=observed_boot(image,folder,commands(s,folder))
            trace=folder/'mapping-trace.log'
            if trace.stat().st_size>32768:raise RuntimeError('trace size limit')
            validate_receipts(serial,trace.read_text(encoding='utf-8'),case,rip)
            binaries=list(folder.glob('*.bin'))
            if len(binaries)>69 or sum(f.stat().st_size for f in binaries)>512*1024 or any(f.stat().st_size>4096 for f in binaries):raise RuntimeError('snapshot bound')
            for gen in (40,41,42):
                prefix=f'g{gen}-';records={f.stem[len(prefix):]:f.read_bytes() for f in binaries if f.name.startswith(prefix)}
                flags=validate_snapshot(records.pop('plan'),records)
                sources=elf_pages((native/('reist-x86_64-user-shell.elf' if gen==40 else 'reist-x86_64-user-child.elf')).read_bytes())
                validate_sources(flags,records,sources)
            summary['cases'].append(dict(case=case,passed=True,rip=hex(rip),mechanism_sha256={n:hashlib.sha256((native/(n+'.o')).read_bytes()).hexdigest()
                for n in (*MECHANISMS,'frame_claim','syscall_profile','image_frames','address_space')}))
            print(f'X86_64_MAPPING_CASE_OK case={case}',flush=True)
        summary.update(passed=True,generations=6);print('X86_64_MAPPINGS_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        print('X86_64_MAPPINGS_RUNTIME_FAIL '+str(e));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-start,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
if __name__=='__main__':raise SystemExit(main())
