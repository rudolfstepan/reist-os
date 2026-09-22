"""Frozen native application HTTP gates in a separate evidence namespace."""
from pathlib import Path
import argparse,ast,hashlib,json,re,shutil,subprocess,sys,time
import verify_x86_64_network_dma as previous
from check_x86_64_wide_shell_media import clone
evidence=clone(previous,[
    ("EVIDENCE=ROOT/'build/codex-agent/r83bj-network-dma'","EVIDENCE=ROOT/'build/codex-agent/r83bq-application-http'"),
    ("BASE=EVIDENCE/'candidate02'","BASE=EVIDENCE/'candidate01'"),
    ("HEAD='c6533954'","HEAD='848cef97'"),
    ("PACKAGE='R8.3bj-network-dma'","PACKAGE='R8.3bq-application-http'"),
    ("BUILD='03'","BUILD='03'")], 'reist_application_http_evidence')
def tools():
    from verify_x86_64_graphical_session import build_tools
    from run_qemu_x86_64_boot import resolve_qemu
    result=build_tools()
    for name,path in [('qemu',resolve_qemu(None)),('gdb',shutil.which('gdb'))]:
        evidence.need(path is not None,'tool '+name);path=Path(path).resolve()
        result[name]=dict(path=str(path),sha256=evidence.digest(path))
    return result
def source_projection():
    v=evidence;macro='REIST_NATIVE_APP_HTTP'
    def project(s):
        lines=s.splitlines(keepends=True);out=[];i=0
        while i<len(lines):
            word=lines[i].strip()
            if word not in ('#ifdef '+macro,'#ifndef '+macro):out.append(lines[i]);i+=1;continue
            positive=word.startswith('#ifdef');i+=1;start=i;depth=1;alternate=None
            while depth:
                word=lines[i].strip()
                if word.startswith('#if'):depth+=1
                if word=='#endif':depth-=1
                if depth==1 and word=='#else':alternate=i
                if depth:i+=1
            if positive:chosen='' if alternate is None else ''.join(lines[alternate+1:i])
            else:chosen=''.join(lines[start:alternate if alternate is not None else i])
            out.append(project(chosen));i+=1
        return ''.join(out)
    def tokens(s):return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',s)
    def replace(s,a,b=''):
        v.need(s.count(a)==1,'one explicit HTTP addition '+a[:60]);return s.replace(a,b)
    for n in ('userspace/sdk/lib/x86_64/shell_session.c','userspace/programs/curl.c',
              'userspace/programs/curl_http.h',
              'userspace/sdk/lib/x86_64/shell_application_tcp.inc',
              'userspace/sdk/lib/x86_64/application_tcp_platform.c'):
        s=project((v.ROOT/n).read_text(encoding='utf-8'))
        v.need(tokens(s)==tokens(v.original(n)),'complete disabled C tokens '+n)
    n='scripts/build-x86_64-bootstrap.ps1';s=(v.ROOT/n).read_text(encoding='utf-8')
    for part in ('    [switch]$NativeAppHTTP,\n','if ($NativeAppHTTP) { $NativeAppDNS = [switch]$true }\n',
                 '        "X86_64_NATIVE_APP_HTTP=$([int]$NativeAppHTTP.IsPresent)" `\n'):s=replace(s,part)
    v.need(s==v.original(n),'exact disabled Windows build')
    n='Makefile';s=(v.ROOT/n).read_text(encoding='utf-8')
    a=s.index('# Explicit local HTTP application profile;');b=s.index('# Explicit DNS application profile;',a)
    s=s[:a]+s[b:]
    s=replace(s,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_APP_HTTP)),--app-http,)\n')
    a=s.index('.PHONY: x86_64-application-http-media');b=s.index('.PHONY: x86_64-application-dns-media',a)
    s=s[:a]+s[b:];v.need(s==v.original(n),'exact disabled Make rules')
    class Disabled(ast.NodeTransformer):
        def visit_If(self,n):
            if any(isinstance(x,ast.Name) and x.id=='app_http' for x in ast.walk(n.test)):
                v.need(not n.orelse,'no hidden default branch');return None
            return self.generic_visit(n)
        def visit_FunctionDef(self,n):
            if n.name in ('build','build_roles') and n.args.args[-1].arg=='app_http':
                n.args.args.pop();n.args.defaults.pop()
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call) and any(isinstance(a,ast.Constant) and a.value=='--app-http' for a in n.value.args):return None
            return self.generic_visit(n)
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if n.args and (isinstance(n.args[-1],ast.Name) and n.args[-1].id=='app_http' or
                          isinstance(n.args[-1],ast.Attribute) and n.args[-1].attr=='app_http'):n.args.pop()
            return n
    for n in ('scripts/build_x86_64_boot_programs.py','scripts/build_x86_64_network_programs.py'):
        current=Disabled().visit(ast.parse((v.ROOT/n).read_text(encoding='utf-8')))
        v.need(ast.dump(current)==ast.dump(ast.parse(v.original(n))),'complete disabled Python AST '+n)
    for n in ('userspace/sdk/include/x86os.h','userspace/sdk/include/reist/x86_64/application_udp.h',
              'userspace/sdk/include/reist/x86_64/application_tcp.h'):
        v.need((v.ROOT/n).read_text(encoding='utf-8')==v.original(n),'unchanged public ABI '+n)
    return True

def defaults():
    source_projection();v=evidence
    for receipt in ('r83bi-graphical-session/development-build07.json','r83bk-network-fatal/build01.json','r83bl-network-session/build14.json'):
        old=v.read(v.ROOT/'build/codex-agent'/receipt)
        v.need(all(v.digest(v.ROOT/n)==sha for n,sha in old['artifacts'].items()),'accepted artifacts retained '+receipt)
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=v.ROOT,timeout=120,check=True)
    seal=v.read(v.ROOT/'build/codex-agent/r83bm-application-udp/candidate04/acceptance-seal.json')
    v.need(seal['passed'],'accepted UDP predecessor')
    for name,sha in seal['package']['artifacts'].items():v.need(v.digest(v.ROOT/name)==sha,'retained accepted UDP artifact '+name)
    seal=v.read(v.ROOT/'build/codex-agent/r83bn-application-tcp/candidate06/acceptance-seal.json')
    v.need(seal['passed'],'accepted TCP predecessor')
    for name,sha in seal['package']['artifacts'].items():v.need(v.digest(v.ROOT/name)==sha,'retained accepted TCP artifact '+name)
    seal=v.read(v.ROOT/'build/codex-agent/r83bp-application-dns/candidate04/acceptance-seal.json')
    v.need(seal['passed'],'accepted DNS predecessor')
    for name,sha in seal['package']['artifacts'].items():v.need(v.digest(v.ROOT/name)==sha,'retained DNS artifact '+name)
    print('APPLICATION_HTTP_DEFAULTS_OK')
def freeze():
    v=evidence;v.need(not v.BASE.exists() and v.git('rev-parse','--short=8','HEAD')==v.HEAD,'fresh candidate and clean baseline commit')
    p=v.package_row();paths=v.changed();v.need(set(paths)<=set(p['allowed_files']) and not v.git('diff','--cached','--name-only'),'exact package scope')
    subprocess.run(['git','diff','--check'],cwd=v.ROOT,check=True)
    # git diff --check omits untracked files; inspect each new candidate file
    # before admitting costly gates, using Git's own complete-file check.
    for name in v.git('ls-files','--others','--exclude-standard').splitlines():
        result=subprocess.run(['git','-c','core.safecrlf=false','diff','--no-index','--check','--',str(Path('NUL')),name],
                              cwd=v.ROOT,capture_output=True,text=True,timeout=10)
        v.need(result.returncode in (0,1) and not result.stdout.strip() and not result.stderr.strip(),
               'new file whitespace check '+name+': '+result.stdout+result.stderr)
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];v.need(len(commands)==5,'five frozen gates')
    v.save(v.BASE/'frozen.json',dict(head=v.git('rev-parse','HEAD'),package=p,changed=paths,sources=v.sources(),
        tools=tools(),regression_inputs=regression_inputs(),commands=commands,limits=[600,600,600,4800,600]))

def regression_inputs():
    v=evidence;paths=[]
    for name in ('diagnostic01','diagnostic02'):
        folder=v.EVIDENCE/name;v.need(folder.is_dir(),'retained HTTP diagnostic '+name)
        paths.extend(p for p in folder.iterdir() if p.is_file() and
            (p.suffix in ('.bin','.json') or p.name in ('guest.log','frame-trace.log')))
    paths.append(v.EVIDENCE/'build02/x86_64/reist-x86_64-bootstrap.elf')
    paths.extend(v.EVIDENCE/('development-host%02d.json'%n) for n in range(1,14))
    paths.extend(v.EVIDENCE/('media%02d.json'%n) for n in (1,2))
    return {p.relative_to(v.ROOT).as_posix():v.digest(p) for p in paths}


def binding():
    v=evidence;f=v.read(v.BASE/'frozen.json')
    v.need(f['head']==v.git('rev-parse','HEAD') and f['package']==v.package_row() and f['changed']==v.changed() and
           f['sources']==v.sources() and f['tools']==tools() and f['regression_inputs']==regression_inputs(),'immutable candidate, tools and regression inputs')
    return f
def image():
    v=evidence;row=v.read(v.BASE/'package.json');path=v.ROOT/row['image']['path']
    v.need(row['passed'] and v.link(path)==row['image'],'bound accepted reference image')
    from run_qemu_x86_64_application_http import stack_review
    v.need(stack_review(path)==row['stack'],'bound compiler stack usage')
    return path
def package():
    import check_x86_64_application_http_media as consumer
    v=evidence;f=binding();folder=v.BASE/'build';media=v.BASE/'media'
    def run(name,command,limit):
        binding();v.save(v.BASE/(name+'-started.json'),dict(command=command,limit=limit,sources=f['sources'],tools=f['tools']))
        log=v.BASE/(name+'.log');start=time.monotonic()
        with log.open('xb') as out:p=subprocess.run(command,cwd=v.ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
        row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,passed=p.returncode==0,log=v.link(log))
        v.save(v.BASE/(name+'.json'),row);v.need(row['passed'],name+' failed: '+log.read_text(errors='replace')[-1800:]);binding()
    run('reference-build',[f['tools']['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeAppHTTP','-OutputDirectory',folder.relative_to(v.ROOT).as_posix()],300)
    run('reference-media',[sys.executable,'scripts/build_x86_64_application_http_media.py','--input-directory',
        str(folder/'x86_64'),'--output-directory',str(media)],180)
    consumer.verify(media)
    from run_qemu_x86_64_application_http import stack_review
    stack=stack_review(folder/'x86_64/reist-x86_64-bootstrap.elf')
    v.save(v.BASE/'package.json',dict(passed=True,stack=stack,image=v.link(folder/'x86_64/reist-x86_64-bootstrap.elf'),
        index=v.link(media/'application-http-media.json'),artifacts={p.relative_to(v.ROOT).as_posix():v.digest(p)
        for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p) and p.suffix in ('.elf','.prg','.bin','.map','.o')}))
def runtime():
    import run_qemu_x86_64_application_http as guest
    v=evidence;binding();img=image();rows=[]
    for name in guest.CASES:
        binding();folder=v.BASE/'guests'/name;row=guest.diagnostic(img,folder,name=name)
        row['proof']=guest.review(img,folder,name);rows.append(row)
        v.save(v.BASE/(name+'.json'),row);print('APPLICATION_HTTP_CASE_OK',name,flush=True)
    v.need(sum(row['elapsed'] for row in rows)<=4500,'total twenty-five-guest runtime bound')
    v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows))
def review():
    import run_qemu_x86_64_application_http as guest
    v=evidence;f=binding();img=image();matrix=v.read(v.BASE/'matrix.json')
    v.need(matrix['passed'] and len(matrix['cases'])==25,'twenty-five fresh cases')
    for row,name in zip(matrix['cases'],guest.CASES):
        v.need(guest.review(img,v.BASE/'guests'/name,name)==row['proof'],'independent complete raw replay '+name)
    for name,sha in v.read(v.BASE/'package.json')['artifacts'].items():v.need(v.digest(v.ROOT/name)==sha,'reference artifact '+name)
    v.need(set(v.changed())<=set(v.package_row()['allowed_files']) and not v.git('diff','--cached','--name-only'),'final scope')
    subprocess.run(['git','diff','--check'],cwd=v.ROOT,check=True)
    raw={p.relative_to(v.ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}
    v.save(v.BASE/'acceptance-seal.json',dict(passed=True,frozen=f,raw=raw,package=v.read(v.BASE/'package.json'),
        gates=[v.read(v.BASE/f'gate-{n:02d}.json') for n in range(1,5)]))
    print('APPLICATION_HTTP_REVIEW_OK')
def gates():
    evidence.binding=binding;evidence.gates()
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args();globals()[next(n for n in vars(a) if getattr(a,n))]()
