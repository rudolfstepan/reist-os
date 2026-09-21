"""Frozen starter transaction; unchanged accepted image, real owned sessions."""
from pathlib import Path
import argparse,hashlib,json,os,queue,re,shlex,struct,subprocess,sys,threading,time,tomllib
from unittest.mock import patch
import run_x86_64_display as app
import verify_x86_64_display as be
ROOT=app.check.ROOT
BASE=ROOT/'build/codex-agent/r83bf-display-delivery/candidate02'
PRIOR=ROOT/'build/codex-agent/r83be-display/candidate03/verification-status-display-final.json'
PRIOR_SHA='6c584e979e3cbf56dbf35f53aadf949b8d205481865159b1d4a0cd9b20ff4df8'
HEAD='9a331894'
LIMITS=(300,180,210,180,180,60)
need=app.check.need
read=be.read;save=be.save;git=be.git;changed=be.changed

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3bf-display-delivery' and p['status']=='active','one active starter package')
    return p
def sources():
    names=set(git('ls-files').splitlines())|set(package()['allowed_files'])
    return {n:digest(ROOT/n) for n in sorted(names)}
def prior():
    need(digest(PRIOR)==PRIOR_SHA,'exact accepted BE final receipt');r=read(PRIOR)
    need(r['accepted'] and r['clean_worktree'] and r['gates']==12 and r['display_cases']==9 and r['cli_cases']==10,'complete BE acceptance')
    allowed=set(package()['allowed_files'])
    for name,sha in r['sources'].items():
        if name not in allowed:need(digest(ROOT/name)==sha,'unchanged accepted dependency '+name)
    need(be.all_tools()==r['tools'],'accepted tools unchanged')
    for name in ('build','media','seal'):need(link(ROOT/r[name]['path'])==r[name],'bound BE '+name)
    for name,sha in read(ROOT/r['seal']['path'])['evidence'].items():need(digest(ROOT/name)==sha,'retained BE evidence '+name)
    be.build_binding();return r
def freeze():
    need(git('rev-parse','--short=8','HEAD')==HEAD and not BASE.exists(),'fresh clean setup boundary')
    p=package();need(set(changed())<=set(p['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'scope/index/whitespace')
    prior();state=sources();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==6,'six frozen gates')
    value=dict(head=git('rev-parse','HEAD'),package=p,queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text()),
        sources=state,changed=changed(),commands=commands,limits=LIMITS,tools=be.all_tools(),prior=link(PRIOR),
        reserved=dict(builds=0,media=0,guests=2,guest_seconds=120),
        candidate=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest())
    save(BASE/'frozen.json',value)
    for name in changed():
        out=BASE/'sources'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((ROOT/name).read_bytes())
def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and package()==f['package'] and sources()==f['sources'] and changed()==f['changed'],'immutable candidate inputs')
    need(be.all_tools()==f['tools'] and link(PRIOR)==f['prior'],'immutable tools/accepted predecessor');return f
def command(args,log,limit):
    start=time.monotonic()
    with log.open('xb') as out:
        try:
            code=subprocess.run(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
        except subprocess.TimeoutExpired:
            code=124;out.write(b'\nFROZEN_COMMAND_TIMEOUT\n')
    return dict(command=list(map(str,args)),passed=code==0,exit_code=code,elapsed=time.monotonic()-start,log=link(log))
def check_package():
    binding();prior();attempt,files=app.admit(app.DEFAULT)
    rows=[]
    for tag,cmd in [('python',[sys.executable,'scripts/run_x86_64_display.py','--check-only']),
                    ('windows',[be.build_tools()['pwsh']['path'],'-NoProfile','-File','scripts/start-x86_64-display.ps1','-CheckOnly']),
                    ('old-cli',[sys.executable,'scripts/run_x86_64_cli.py','--check-only'])]:
        row=command(cmd,BASE/(tag+'-entry.log'),45);rows.append(row);need(row['passed'],'actual entry admission '+tag)
    save(BASE/'package.json',dict(passed=True,attempt=str(attempt),entries=rows,builds=0,media=0))

def session(layout,ram):
    """Only replace host stdio handles; launch() owns QEMU and every cleanup."""
    folder=BASE/layout;folder.mkdir();raw=bytearray();chunks=queue.Queue(maxsize=512)
    errors=[];threads=[];spawned=[];before=set(app.SESSIONS.glob('session-*'))
    original=subprocess.Popen;qemu=app.guest.bios.ay.boot.resolve_qemu(None)
    start=time.monotonic();row=dict(passed=False,layout=layout,ram=ram,limit=60)
    stderr=(folder/'stderr.log').open('xb')
    def intercept(args,*pos,**kw):
        if str(args[0])!=str(qemu):return original(args,*pos,**kw)
        need(not spawned and not pos and 'stdin' not in kw and 'stdout' not in kw,'one exact QEMU stdio capture')
        vm=original(args,**dict(kw,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr));spawned.append(vm)
        end=time.monotonic()+50
        def reader():
            try:
                while True:
                    part=os.read(vm.stdout.fileno(),4096)
                    if not part:break
                    chunks.put(part,timeout=1)
            except BaseException as error:errors.append(str(error))
        def pump():
            while True:
                try:raw.extend(chunks.get_nowait())
                except queue.Empty:break
            need(len(raw)<=2*1024*1024 and not errors,'bounded serial queue/capture')
            need(not any(s.encode() in raw for s in app.guest.bios.ay.boot.FAILURES),'fatal guest output')
        def wait(predicate):
            while time.monotonic()<end:
                pump()
                if predicate():return
                need(vm.poll() is None,'guest exited before complete dialogue');time.sleep(.005)
            raise TimeoutError('bounded starter dialogue '+raw[-200:].decode(errors='replace'))
        def feed():
            try:
                prompts=1;wait(lambda:raw.count(b'C:\\>')>=prompts)
                for line in ('boot.prg','cat /data.txt','exit','boot.prg s','cat /data.txt','exit'):
                    at=len(raw);encoded=line.encode();prefix=b''
                    for n in range(0,len(encoded),8):
                        part=encoded[n:n+8];vm.stdin.write(part);vm.stdin.flush();prefix+=part
                        wait(lambda:prefix in bytes(raw[at:]))
                    vm.stdin.write(b'\n');vm.stdin.flush();prompts+=1
                    if prompts==7:wait(lambda:b'REIST_X86_64_NATIVE_PROCESSES_OK' in raw)
                    else:wait(lambda:raw.count(b'C:\\>')>=prompts)
            except BaseException as error:errors.append(str(error))
        for task in (reader,feed):
            thread=threading.Thread(target=task,daemon=True);threads.append(thread);thread.start()
        return vm
    try:
        with patch.object(app.subprocess,'Popen',side_effect=intercept):
            result=app.launch(layout=layout,ram=ram,headless=True,seconds=60)
        row['session']=result
        need(result['passed'] and result['reason']=='session-deadline','real host-owned deadline exit')
    except BaseException as error:row['error']=str(error);raise
    finally:
        for thread in threads:thread.join(timeout=2)
        stderr.close()
        while not chunks.empty():raw.extend(chunks.get_nowait())
        (folder/'serial.log').write_bytes(raw)
        sessions=set(app.SESSIONS.glob('session-*'))-before
        row.update(elapsed=time.monotonic()-start,errors=errors,threads_closed=all(not t.is_alive() for t in threads),
                   processes_closed=all(p.poll() is not None for p in spawned),guests=len(spawned),
                   evidence=next(iter(sessions)).relative_to(ROOT).as_posix() if len(sessions)==1 else None)
        row['passed']='error' not in row and not errors and row['threads_closed'] and row['processes_closed'] and row['guests']==1 and bool(row['evidence'])
        save(folder/'capture.json',row)
    need(row['passed'],'starter capture failed: '+str(errors));return row

def review_session(layout,ram):
    folder=BASE/layout;row=read(folder/'capture.json');out=ROOT/row['evidence'];r=read(out/'session.json')
    need(row['passed'] and row['guests']==1 and row['layout']==layout and row['ram']==ram and row['elapsed']<=70 and
         row['threads_closed'] and row['processes_closed'] and not row['errors'],'bounded owned capture')
    need(r==row['session'] and r['passed'] and r['headless'] and r['limit']==60 and r['layout']==layout and r['ram']==ram and
         57<=r['elapsed']<=60 and 0<=r['cleanup_seconds']<=3 and r['reason']=='session-deadline','exact session/cleanup receipt')
    raw=app.check.bounded(folder/'serial.log',2*1024*1024)
    need(not any(s.encode() in raw for s in app.guest.bios.ay.boot.FAILURES) and raw.count(b'DISPLAY_CLIENT_OK')==2 and
         raw.count(b'Read-only, generation-bound, revocable.')==2 and raw.count(b'REIST_X86_64_PROCESS_RUN_OK')==2 and
         raw.count(b'REIST_X86_64_NATIVE_PROCESSES_OK')==1,'complete actual shell/display/file lifecycle')
    app.guest.validate_bios(raw.decode('ascii',errors='replace'),layout,'normal')
    reaps=[struct.unpack('<4I2Q',bytes.fromhex(v.decode())) for v in re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',raw)]
    children=[r for r in reaps if r[0]==4];roots=[r for r in reaps if r[0]==0]
    need(len(children)==4 and len({r[1] for r in children})==4 and
         [r[2:4] for r in children]==[(82,4),(0,4),(82,4),(0,4)] and
         len(roots)==2 and all(r[2:4]==(0,4) for r in roots) and roots[0][1]!=roots[1][1],'actual successful generation reaps')
    attempt,_=app.admit(app.DEFAULT);cmd=read(out/'command.json')
    expected=[str(app.guest.bios.ay.boot.resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m',str(ram)+'M',
              '-smp','1','-display','none','-vga','none','-device','VGA,vgamem_mb=16','-monitor','none','-nic','none',
              '-serial','stdio','-no-reboot','-no-shutdown']
    for node in [dict(driver='file',filename=str(out/'generated.raw'),**{'node-name':'pio-base-file','read-only':True}),
                 dict(driver='raw',file='pio-base-file',**{'node-name':'pio-base','read-only':True}),
                 dict(driver='qcow2',file=dict(driver='file',filename=str(out/'disposable.qcow2')),backing='pio-base',**{'node-name':'pio-layer'})]:
        expected+=['-blockdev',json.dumps(node,separators=(',',':'))]
    expected+=['-device','ide-hd,drive=pio-layer,bus=ide.0,unit=0']+app.guest.boot_arguments(out/'boot-medium/disposable.qcow2',layout)
    need(cmd==expected,'exact BIOS two-media launch, no ambient devices')
    need(digest(out/'generated.raw')==digest(attempt/'system.ext2'),'actual immutable published data')
    need(digest(out/'boot-medium/base.raw')==digest(attempt/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')),'actual immutable published boot')
    for boot in (False,True):
        media=out/'boot-medium' if boot else out
        commands=read(media/('commands.json' if boot else 'media-commands.json'))
        need(len(commands)==7 and all(c['returncode']==0 for c in commands),'all original media tool results')
        for phase,at in (('before',1),('after',4)):
            receipt=read(media/((phase if boot else 'media-'+phase)+'.json'));extents=json.loads(commands[at+1]['stdout'])
            size=(536870912 if layout=='hdd' else 1474560) if boot else 1048576
            need(receipt['passed'] and receipt['overlay_allocated_data']==0 and receipt['extents']==extents and
                 [c['args'][0] for c in commands[at:at+3]]==['info','map','compare'],'full original no-write proof')
            if boot:need(receipt['base']==dict(size=size,sha256=digest(media/'base.raw')),'boot source binding')
            else:need(receipt['logical_bytes']==size and receipt['base_sha256']==digest(media/'generated.raw'),'data source binding')
            end=0
            for e in extents:need(e['start']==end and e['length']>0 and e['depth']==1,'unchanged complete overlay extent');end+=e['length']
            need(end==size,'complete medium coverage')
    return dict(layout=layout,ram=ram,passed=True,capture=link(folder/'capture.json'),session=link(out/'session.json'),generations=[r[1] for r in children])

def runtime():
    binding();rows=[]
    for layout,ram in (('hdd',4096),('floppy',8192)):
        rows.append(session(layout,ram));review_session(layout,ram)
    need(sum(r['session']['elapsed'] for r in rows)<=120,'two physical session reservation')
    save(BASE/'runtime.json',dict(passed=True,cases=rows,guests=2,guest_seconds=sum(r['session']['elapsed'] for r in rows)))
def review():
    binding();prior();proofs=[review_session(layout,ram) for layout,ram in (('hdd',4096),('floppy',8192))]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
    for row in read(BASE/'runtime.json')['cases']:
        hashes.update({p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/row['evidence']).rglob('*') if p.is_file()})
    save(BASE/'review.json',dict(passed=True,proofs=proofs,hashes=hashes))
def scope():
    f=binding();need(not git('diff','--check') and not git('diff','--cached','--name-only') and read(BASE/'review.json')['passed'],'complete clean scope')
    save(BASE/'scope.json',dict(passed=True,candidate=f['candidate'],changed=changed()))
def all_gates():
    f=binding();save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();row=command(shlex.split(cmd),BASE/f'gate-{n:02d}.log',limit);row['candidate']=f['candidate']
        save(BASE/f'gate-{n:02d}.json',row);print('DISPLAY_DELIVERY_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:save(BASE/'stopped.json',row);raise ValueError('first failed gate '+str(n))
    save(BASE/'gates-passed.json',dict(passed=True,candidate=f['candidate'],gates=6))
def evidence():return {p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
def seal():
    f=binding();need(read(BASE/'gates-passed.json')==dict(passed=True,candidate=f['candidate'],gates=6),'all six gates')
    for n,cmd in enumerate(f['commands'],1):
        row=read(BASE/f'gate-{n:02d}.json');need(row['passed'] and row['command']==shlex.split(cmd) and row['log']==link(ROOT/row['log']['path']),'exact gate result')
    for name,sha in read(BASE/'review.json')['hashes'].items():need(digest(ROOT/name)==sha,'reviewed raw evidence')
    save(BASE/'seal.json',dict(passed=True,candidate=f['candidate'],evidence=evidence()))
def ready():
    f=read(BASE/'frozen.json');s=read(BASE/'seal.json');state={n:digest(ROOT/n) for n in f['sources']}
    need(s['passed'] and s['candidate']==f['candidate'],'complete frozen acceptance seal')
    docs={n for n in f['package']['allowed_files'] if n.startswith(('docs/','automation/'))}
    need({n for n in state if state[n]!=f['sources'][n]}<=docs,'only outcome docs after gates')
    need(git('rev-parse','HEAD')==f['head'] and not git('diff','--check') and not git('diff','--cached','--name-only'),'precommit boundary')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());expected=f['queue'];expected['active_id']='';expected['packages'][0]['status']='done'
    need(q==expected and set(changed())<=set(f['package']['allowed_files']),'exact queue/scope completion')
    for name,sha in s['evidence'].items():need(digest(ROOT/name)==sha,'sealed evidence')
    save(BASE/'ready.json',dict(passed=True,sources=state,changed=changed(),seal=link(BASE/'seal.json'),evidence=evidence()))
def final():
    f=read(BASE/'frozen.json');r=read(BASE/'ready.json');head=git('rev-parse','HEAD')
    need(not git('status','--porcelain') and git('rev-parse','HEAD^')==f['head'],'clean accepted child commit')
    need(sorted(git('diff','--name-only',f['head'],head).splitlines())==r['changed'],'exact committed scope')
    for name,sha in {**r['sources'],**r['evidence']}.items():need(digest(ROOT/name)==sha,'committed sources/evidence')
    save(BASE/'final.json',dict(accepted=True,clean_worktree=True,implementation_commit=head,gates=6,guests=2,
         guest_seconds=read(BASE/'runtime.json')['guest_seconds'],prior=link(PRIOR),seal=r['seal'],sources=r['sources'],tools=f['tools']))
    print('DISPLAY_DELIVERY_ACCEPTED',head,flush=True)

if __name__=='__main__':
    actions=dict(freeze=freeze,package=check_package,runtime=runtime,review=review,scope=scope,all=all_gates,seal=seal,ready=ready,final=final)
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in actions:g.add_argument('--'+name,action='store_true')
    a=p.parse_args();actions[next(n for n in actions if getattr(a,n))]()
