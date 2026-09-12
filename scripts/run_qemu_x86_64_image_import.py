"""Ring3 ELF preparation through immutable mapping import and full retirement."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,uuid
import run_qemu_x86_64_task_startup as startup
import build_x86_64_boot_programs as producer
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    folder=startup.family.evidence_directory(a.evidence)/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();summary=dict(passed=False,cases=[])
    try:
        image=a.image.resolve();reference=None
        for case in range(2):
            if case:
                out=folder/'oom-build';out.mkdir()
                with (out/'build.log').open('wb') as f:
                    r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeImport','-StartupCase','1','-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode:raise ValueError('import OOM fixture build')
                image=out/'x86_64/reist-x86_64-bootstrap.elf'
            names=('cooperative_scheduler','elf64_loader','syscall_profile','bootstrap_core','identity_core','queue_core','cpu_budget','task_frames','fp_context','timer_interrupt','startup_stack')
            hashes={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            # Loader .o embeds the fixture catalog: compare mechanisms except that container.
            mechanisms={n:h for n,h in hashes.items() if n!='elf64_loader'}
            if reference is not None and reference!=mechanisms:raise ValueError('import mechanism drift')
            reference=mechanisms
            catalog=(image.parent/'boot-programs.bin').read_bytes()
            if len(catalog)!=4*36896:raise ValueError('import catalog length')
            candidates=[d for d in image.parent.glob('programs-*') if d.is_dir() and (d/'boot-programs.bin').is_file() and (d/'boot-programs.bin').read_bytes()==catalog]
            if not candidates:raise ValueError('import catalog provenance missing')
            child=(candidates[0]/'program2.prg').read_bytes()
            if any((d/'program2.prg').read_bytes()!=child for d in candidates):raise ValueError('import catalog provenance ambiguous')
            record=producer.prepare(child,[])
            if record[:32800]!=catalog[73792:106592] or startup.creation_allocations(record)!=10:raise ValueError('import child extent')
            inner=startup.family.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=startup.family.payload.validate(inner)
            startup.family.payload.verify_outer(inner,startup.family.payload.read_bounded(image))
            if c['layout_version']!=4:raise ValueError('import C layout')
            s=startup.family.symbols(image)
            variants=[(4096,n) for n in (0,1,2,3,6,9)] if case else [(4096,None),(8192,None)]
            for ram,oom in variants:
                out=folder/f'guest-{ram}-{oom}';out.mkdir()
                serial,trace=startup.family.programs.capture(image,out,startup.observer(s,c,out,ram,oom,record),ram)
                tasks=startup.validate(serial,trace,oom,True)
                summary['cases'].append(dict(ram=ram,oom=oom,tasks=tasks,record_sha256=hashlib.sha256(record).hexdigest()))
                print('IMPORT_GUEST_OK',ram,oom,flush=True)
        summary['passed']=True;summary['mechanisms']=reference
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('IMPORT_FAIL',error);return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('IMPORT_EVIDENCE',folder)
    return 0

if __name__=='__main__':raise SystemExit(main())
