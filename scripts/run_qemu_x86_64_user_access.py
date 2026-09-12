"""Actual cross-page child R/NX IPC input, negative hole, and two full lifecycles."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid
from run_qemu_x86_64_boot import resolve_qemu,run_boot
from run_qemu_x86_64_mappings import elf_pages
from run_qemu_x86_64_ipc_handoff import REAP
from run_qemu_x86_64_requests import MECHANISMS
ROOT=Path(__file__).resolve().parents[1]

def validate(serial,rip):
    receipts=list(REAP.finditer(serial))
    runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial))
    done=list(re.finditer('MAPPING_OK',serial))
    if any(len(x)!=2 for x in (receipts,runs,done)) or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:
        raise RuntimeError('missing exact successful buffer/reap/parent witnesses')
    for i,row in enumerate(receipts):
        status,g,parent,q,address=(int(x,16) for x in row.groups())
        if (status,g,q,address)!=(77,41+i,0,rip) or parent not in (1,6,7):
            raise RuntimeError('wrong buffer fixture terminal receipt')
        if not (done[i-1].end() if i else -1)<row.start()<row.end()<=runs[i].start()<runs[i].end()<=done[i].start():
            raise RuntimeError('buffer success must follow matching reap and RUN')

def fixture(native):
    pages=elf_pages((native/'reist-x86_64-user-child.elf').read_bytes())
    if set(pages)!={0,1,2} or [pages[i][0] for i in range(3)]!=[5,4,4]:
        raise RuntimeError('expected one RX and two R/NX pages')
    message=struct.pack('<III',1,140,8)+b'token76\0'+bytes(120)
    data=pages[1][1]+pages[2][1]
    if data[4032:4032+140]!=message:raise RuntimeError('cross-page message content')
    code=pages[0][1]
    hits=list(re.finditer(rb'\x48\x8d\x35....',code,re.S))
    addresses=[0x400000+h.end()+struct.unpack_from('<i',code,h.start()+3)[0] for h in hits]
    if addresses.count(0x401fc0)!=1:raise RuntimeError('missing real cross-page SEND pointer')
    if bytes.fromhex('bec03f400031d20f05') not in code or bytes.fromhex('4883f8f2') not in code:
        raise RuntimeError('missing real hole SEND/EFAULT check')
    packet=bytes.fromhex('b80900000031f631d20f05')
    exits=list(re.finditer(re.escape(packet),code))
    if len(exits)!=1:raise RuntimeError('normal EXIT instruction identity')
    return 0x400000+exits[0].end()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence outside workspace')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result=dict(passed=False);started=time.monotonic()
    try:
        with (folder/'build.log').open('wb') as out:
            p=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-OutputDirectory',folder.relative_to(ROOT).as_posix(),'-MappingCase','4'],cwd=ROOT,
                stdout=out,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if p.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
        native=folder/'x86_64';normal=base.parent/'normal/x86_64'
        names=(*MECHANISMS,'frame_claim','syscall_profile','image_frames','address_space','task_frames','user_access')
        hashes={n:hashlib.sha256((native/(n+'.o')).read_bytes()).hexdigest() for n in names}
        if any(hashes[n]!=hashlib.sha256((normal/(n+'.o')).read_bytes()).hexdigest() for n in names):
            raise RuntimeError('fixture changes kernel mechanisms')
        rip=fixture(native)
        serial=run_boot(resolve_qemu(None),native/'reist-x86_64-bootstrap.elf',folder/'guest.log',10)
        validate(serial,rip)
        result.update(passed=True,generations=2,source='0x401fc0..0x40204b',hole='0x403fc0',
                      exit_rip=hex(rip),mechanism_sha256=hashes)
        print('X86_64_USER_ACCESS_RUNTIME_OK cross_page_R_IPC=1 hole_EFAULT=1 generations=2 evidence='+str(folder))
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired,struct.error) as exc:
        print('X86_64_USER_ACCESS_RUNTIME_FAIL '+str(exc));return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
if __name__=='__main__':raise SystemExit(main())
