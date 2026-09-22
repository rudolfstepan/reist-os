"""Bounded actual-C DNS validation gates; no guest-runtime claim."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time,tomllib
from build_user_sdk import find_zig
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83bo-dns-validation'
ACTIVE='R8.3bo-dns-validation'
CANDIDATE=BASE/'candidate01'

def need(ok,message):
    if not ok:raise ValueError(message)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as out:json.dump(value,out,indent=2)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    need(q['active_id']==ACTIVE,'one active DNS validation package')
    return next(p for p in q['packages'] if p['id']==ACTIVE)
def changed():return sorted(set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
def sources():
    paths=set(package()['allowed_files'])|{'AGENTS.md','scripts/build_user_sdk.py','test/test_dns_host.c'}
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'userspace/sdk/include').rglob('*.h'))
    return {n:digest(ROOT/n) for n in sorted(paths) if (ROOT/n).is_file()}
def tools():
    z=Path(find_zig());return dict(zig=str(z),zig_sha256=digest(z),python=sys.executable,python_sha256=digest(sys.executable))
def binding():
    f=read(CANDIDATE/'frozen.json')
    need(f['head']==git('rev-parse','HEAD') and f['package']==package() and f['changed']==changed() and
         f['sources']==sources() and f['tools']==tools(),'immutable source/tool/scope binding')
    return f
def run(folder,name,cmd,limit):
    env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
    save(folder/(name+'-started.json'),dict(command=cmd,limit=limit));start=time.monotonic()
    with (folder/(name+'.log')).open('xb') as out:
        p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
    save(folder/(name+'.json'),dict(passed=p.returncode==0,elapsed=time.monotonic()-start,log_sha256=digest(folder/(name+'.log'))))
    need(p.returncode==0,name+': '+(folder/(name+'.log')).read_text(errors='replace')[-2200:])
def host(folder):
    z=tools()['zig']
    for opt in ('0','2'):
        exe=folder/('dns-O'+opt+'.exe')
        run(folder,'compile-O'+opt,[z,'cc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror',
            '-Wno-unused-command-line-argument','-Iuserspace/sdk/include','test/test_dns_response_validation.c',
            'userspace/sdk/reist_dns.c','-o',str(exe)],120)
        run(folder,'execute-O'+opt,[str(exe)],30)
    print('DNS_HOST_OK')
def compile_targets():
    binding();z=tools()['zig'];artifacts={}
    for target in ('x86-freestanding-none','x86_64-freestanding-none'):
        obj=CANDIDATE/(target+'.o')
        run(CANDIDATE,target,[z,'cc','-target',target,'-std=c11','-Oz','-Wall','-Wextra','-Werror',
            '-Wno-unused-command-line-argument','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector',
            '-Iuserspace/sdk/include','-fstack-usage','-c','userspace/sdk/reist_dns.c','-o',str(obj)],120)
        artifacts[obj.name]=digest(obj)
    save(CANDIDATE/'artifacts.json',artifacts);print('DNS_COMPILE_OK')
def review():
    f=binding()
    for n in (1,2):need(read(CANDIDATE/('gate-%02d.json'%n))['passed'],'previous gate passed')
    current=(ROOT/'userspace/sdk/reist_dns.c').read_text(encoding='utf-8')
    old=subprocess.check_output(['git','show',f['head']+':userspace/sdk/reist_dns.c'],cwd=ROOT).decode('utf-8')
    need(current[:current.index('/* DNS response validation')] == old[:old.index('static int decode_name(')],'unchanged resolver prefix')
    marker='static int deadline_remaining('
    need(current[current.index(marker):]==old[old.index(marker):],'cache and transport remain a separate transaction')
    for name,sha in read(CANDIDATE/'artifacts.json').items():need(digest(CANDIDATE/name)==sha,'freestanding artifact '+name)
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    save(CANDIDATE/'acceptance-seal.json',dict(passed=True,frozen=f,artifacts=read(CANDIDATE/'artifacts.json'),
        records={p.name:digest(p) for p in CANDIDATE.iterdir() if p.is_file()}))
    print('DNS_REVIEW_OK')
def freeze():
    p=package();need(not CANDIDATE.exists(),'fresh candidate');need(set(changed())<=set(p['allowed_files']) and not git('diff','--cached','--name-only'),'scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    for n in git('ls-files','--others','--exclude-standard').splitlines():
        r=subprocess.run(['git','-c','core.safecrlf=false','diff','--no-index','--check','--','NUL',n],cwd=ROOT,capture_output=True,text=True,timeout=10)
        need(r.returncode in (0,1) and not r.stdout.strip() and not r.stderr.strip(),'new-file whitespace '+n+r.stdout+r.stderr)
    save(CANDIDATE/'frozen.json',dict(head=git('rev-parse','HEAD'),package=p,changed=changed(),sources=sources(),tools=tools(),
        commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'],limits=[600,300,120]))
def gates():
    f=binding()
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();run(CANDIDATE,'gate-%02d'%n,cmd.split(),limit);binding()
    save(CANDIDATE/'gates-passed.json',dict(passed=True,gates=[read(CANDIDATE/('gate-%02d.json'%n)) for n in (1,2,3)]))
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for n in ('freeze','gates','host','compile','review'):g.add_argument('--'+n,action='store_true')
    g.add_argument('--development',type=int);a=p.parse_args()
    if a.development is not None:
        need(1<=a.development<=8,'development reservation');folder=BASE/('development%02d'%a.development)
        need(not folder.exists(),'one run per reservation');save(folder/'reservation.json',dict(limit=600,sources=sources(),tools=tools()));host(folder)
    elif a.host:binding();host(CANDIDATE)
    elif a.compile:compile_targets()
    else:globals()[next(n for n in ('freeze','gates','review') if getattr(a,n))]()
