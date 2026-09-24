"""Bounded qualification for the append-only native geometry request."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,time,tomllib
import verify_x86_64_display as old
ROOT=old.ROOT
BASE=ROOT/'build/codex-agent/r83cc-display-info'
GATES=BASE/'qualification02'
HEAD='566d8d94'
need=old.need
save=old.save
digest=old.digest

def read(p):return json.loads(Path(p).read_text())
def sources():
    names=old.git('ls-files','--cached','--others','--exclude-standard').splitlines()
    return {n:digest(ROOT/n) for n in sorted(set(names)) if n=='Makefile' or n.startswith(
        ('arch/','kernel/','userspace/','include/','lib/','config/','scripts/','test/'))}
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    active=[p for p in q['packages'] if p['status']=='active']
    need(len(active)==1 and active[0]['id']==q['active_id']=='R8.3cc-display-info','one CC package')
    return active[0]
def scope():
    need(set(old.changed())<=set(package()['allowed_files']),'frozen scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True,timeout=30,capture_output=True)
def freeze():
    scope();need(old.git('rev-parse','--short=8','HEAD')==HEAD,'clean contract baseline')
    save(GATES/'frozen.json',dict(head=old.git('rev-parse','HEAD'),sources=sources(),tools=old.all_tools(),
        package=package(),baseline=digest(BASE/'development-buildbaseline01.json')))
def binding():
    f=read(GATES/'frozen.json');scope()
    need(f['head']==old.git('rev-parse','HEAD') and f['sources']==sources() and f['tools']==old.all_tools(),
         'unchanged frozen source/tool inputs')
    need(f['package']==package() and f['baseline']==digest(BASE/'development-buildbaseline01.json'),'frozen gate/baseline')
    return f
def artifacts(folder):
    out={}
    for p in folder.rglob('*'):
        if not p.is_file() or any('cache' in part for part in p.parts) or p.suffix not in ('.elf','.prg','.o','.bin','.inc','.json'):continue
        key=re.sub(r'programs-[0-9a-f]{32}', 'programs',p.relative_to(folder).as_posix())
        need(key not in out,'unique artifact path');out[key]=digest(p)
    need(10<len(out)<2048,'bounded complete artifacts');return out
def build(label,enabled):
    folder=BASE/label;need(not folder.exists(),'fresh build')
    command=['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeDisplay',
        *(['-NativeDisplayInfo'] if enabled else []),'-OutputDirectory',folder.relative_to(ROOT).as_posix()]
    run(command,GATES/(label+'.log'),300)
    a=artifacts(folder);save(GATES/(label+'.json'),a)
    return folder/'x86_64/reist-x86_64-bootstrap.elf'
def run(command,log,limit):
    start=time.monotonic()
    with log.open('xb') as stream:
        r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=limit,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    need(r.returncode==0,'command failed '+str(log)+': '+log.read_text(errors='replace')[-2400:])
    return dict(command=command,elapsed=time.monotonic()-start,sha256=digest(log))
def projection():
    # Every removed addition has an explicit feature guard or exact selector line.
    for n,opener,closer in [('arch/x86_64/video/display_core.inc','%ifdef REIST_NATIVE_DISPLAY_INFO','%endif'),
                           ('arch/x86_64/video/display_domain.inc','%ifdef REIST_NATIVE_DISPLAY_INFO','%endif'),
                           ('arch/x86_64/user/display_probe.c','#ifdef REIST_NATIVE_DISPLAY_INFO','#endif')]:
        s=(ROOT/n).read_text();lines=s.splitlines(keepends=True);out=[];inside=False
        for line in lines:
            if line.strip()==opener:need(not inside,'no nested info guard');inside=True
            elif inside and line.strip()==closer:inside=False
            elif not inside:out.append(line)
        need(not inside,'closed info guard')
        baseline=subprocess.check_output(['git','show',HEAD+':'+n],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
        need(''.join(out)==baseline,'exact disabled production projection '+n)
    return True
def defaults():
    projection();baseline=read(BASE/'development-buildbaseline01.json')
    need(baseline['passed'] and baseline['elapsed']<=300 and baseline['tools']==old.build_tools(),'baseline build receipt')
    for name,sha in baseline['artifacts'].items():need(digest(ROOT/name)==sha,'preserved baseline artifact')
    build('disabled02',False)
    need(artifacts(BASE/'disabled02')==artifacts(BASE/'buildbaseline01'),'all disabled output bytes equal baseline')
    return dict(artifacts=len(artifacts(BASE/'disabled02')),exact=True)
def make_package():
    image=build('enabled01',True)
    log=GATES/'media01.log'
    r=run([sys.executable,'scripts/build_x86_64_display_media.py','--input-directory',str(image.parent),
        '--output-directory',str(BASE/'media01')],log,180)
    import check_x86_64_display_media as check
    folder=check.verify(BASE/'media01')
    save(GATES/'media.json',dict(folder=folder.relative_to(ROOT).as_posix(),
        files={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}))
    return r
def media_binding():
    need(artifacts(BASE/'enabled01')==read(GATES/'enabled01.json'),'exact enabled artifacts')
    m=read(GATES/'media.json');folder=ROOT/m['folder']
    need({p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}==m['files'],'bound signed media')
    return BASE/'enabled01/x86_64/reist-x86_64-bootstrap.elf',folder
def geometry(folder,width):
    raw=(folder/'guest.log').read_bytes()
    markers=re.findall(rb'DISPLAY_INFO_(\d+)\r?\n',raw)
    need(markers==[str(width).encode()]*3,'three exact Ring3 geometry/denial self-tests')
    receipt=read(folder/'result.json')
    need(all(r['proof']['width']==width and r['proof']['height']==(768 if width==1024 else 600)
             for r in receipt['snapshots']),'same geometry in every authoritative boot/QMP snapshot')
    return dict(width=width,self_tests=len(markers))
def runtime():
    import run_qemu_x86_64_display as guest
    image,package=media_binding();rows=[];start=time.monotonic()
    for spec in guest.CASES[:2]:
        folder=GATES/spec[0]
        r=guest.run_case(image,package,folder,spec)
        geometry(folder,1024 if spec[2]==16 else 800)
        rows.append(r)
    need(time.monotonic()-start<=640,'aggregate640s runtime limit')
    save(GATES/'runtime-files.json',{p.relative_to(GATES).as_posix():digest(p)
        for spec in guest.CASES[:2] for p in (GATES/spec[0]).rglob('*') if p.is_file()})
    return dict(cases=2,elapsed=sum(r['elapsed'] for r in rows))
def review():
    import run_qemu_x86_64_display as guest
    image,package=media_binding();rows=[]
    for n,sha in read(GATES/'runtime-files.json').items():need(digest(GATES/n)==sha,'unchanged complete raw evidence')
    for spec in guest.CASES[:2]:
        folder=GATES/spec[0]
        rows.append(dict(original=guest.review_case(image,package,folder,spec),
                         geometry=geometry(folder,1024 if spec[2]==16 else 800)))
    projection();return rows
def gate(name,work):
    binding();start=time.monotonic();save(GATES/(name+'-started.json'),{'started':start})
    result={'passed':False}
    try:result['result']=work();binding();result['passed']=True
    except BaseException as e:result['error']=str(e);raise
    finally:result['elapsed']=time.monotonic()-start;save(GATES/(name+'.json'),result)
    print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for flag in ('freeze','defaults','package','runtime','review'):g.add_argument('--'+flag,action='store_true')
    a=p.parse_args()
    if a.freeze:freeze()
    else:
        name=next(k for k,v in vars(a).items() if v)
        gate(name,dict(defaults=defaults,package=make_package,runtime=runtime,review=review)[name])
