"""Two fixed same-image runs per baseline/after label; diagnostic, not acceptance."""
from pathlib import Path
import argparse,hashlib,json,re,struct,time
import run_qemu_x86_64_block_profile as profile
ROOT=profile.ROOT
BASE=ROOT/'build/codex-agent/r83ak-block-profile/diagnostic'

def commands(symbols,folder,snapshot):
    prefix='set logging file '+(folder/'frame-trace.log').as_posix()+'\nset logging enabled on\n'
    if not snapshot:return prefix+'detach\nquit\n'
    return prefix+'python\nS='+repr(symbols)+r'''
import gdb,json,struct
calls=0
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
class Snapshot(gdb.Breakpoint):
    def stop(self):
        global calls
        calls+=1
        if calls>4096:raise RuntimeError('diagnostic callback capacity')
        if mem(S['scheduler_mode'],1)!=b'\x08':return False
        if struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]!=2:return False
        tasks=mem(S['scheduler_tasks'],4096)
        if struct.unpack_from('<2Q',tasks,2048)!=(2,3):return False
        tables=mem(S['scheduler_table_frames'],128)
        original=struct.unpack('<Q',mem(S['scheduler_original_cr3'],8))[0]
        gdb.write('FRAME_COST_SNAPSHOT '+json.dumps(dict(tasks=tasks.hex(),tables=tables.hex(),original=original,calls=calls))+'\n')
        return True
Snapshot('*'+str(S['process_run_frames64']),internal=True)
end
continue
detach
quit
'''

def snapshot(trace):
    matches=re.findall(r'^FRAME_COST_SNAPSHOT (.*)$',trace,re.M)
    if len(matches)!=1 or trace.count('FRAME_COST_SNAPSHOT')!=1:raise ValueError('exact frame snapshot')
    s=json.loads(matches[0])
    if set(s)!={'tasks','tables','original','calls'}:raise ValueError('snapshot fields')
    if not isinstance(s['tasks'],str) or len(s['tasks'])!=8192 or not isinstance(s['tables'],str) or len(s['tables'])!=256:raise ValueError('snapshot bounds')
    if type(s['original']) is not int or not 0<s['original']<0x400000000 or s['original']%4096 or type(s['calls']) is not int or not 1<=s['calls']<=4096:raise ValueError('snapshot scalar')
    if struct.unpack_from('<2Q',bytes.fromhex(s['tasks']),2048)!=(2,3):raise ValueError('snapshot live generation')
    bytes.fromhex(s['tables'])
    return s

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--phase',choices=('baseline','after'),required=True);a=parser.parse_args()
    image=a.image.resolve()
    if not image.is_relative_to(ROOT/'build/codex-agent'):raise ValueError('diagnostic image scope')
    inner=profile.wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    profile.wide.payload.validate(inner);profile.wide.payload.verify_outer(inner,profile.wide.payload.read_bounded(image,bits=32))
    files=(image,image.parent/'reist-x86_64-c-core.elf',image.parent/'boot-programs.bin')
    def hashes():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=hashes();folder=BASE/a.phase;folder.mkdir(parents=True,exist_ok=False)
    profile.pio.safe_folder(folder);s=profile.wide.transport.symbols(image)
    summary=dict(diagnostic_only=True,hashes=original,cases=[]);start=time.monotonic()
    try:
        for kind in ('detached','snapshot'):
            if hashes()!=original:raise ValueError('diagnostic input drift')
            out=folder/kind;out.mkdir();begin=time.monotonic()
            serial,trace=profile.wide.transport.capture(image,out,commands(s,out,kind=='snapshot'),4096,profile.pio.Fixture(out,block=True))
            if kind=='snapshot':(folder/'snapshot.json').write_text(json.dumps(snapshot(trace),indent=2),encoding='utf-8')
            rows=[struct.unpack('<4I2Q',bytes.fromhex(m)) for m in re.findall(r'PROCESS_REAP_OK v1=([0-9a-fA-F]{64})',serial)]
            if not rows or len(rows)>8:raise ValueError('diagnostic receipt bounds')
            summary['cases'].append(dict(mode=kind,receipts=rows,elapsed=round(time.monotonic()-begin,3)))
            print('FRAME_COST_DIAGNOSTIC',kind,summary['cases'][-1],flush=True)
        if hashes()!=original:raise ValueError('diagnostic input drift')
        return 0
    finally:
        summary['elapsed']=round(time.monotonic()-start,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print('FRAME_COST_EVIDENCE',folder)

if __name__=='__main__':raise SystemExit(main())
