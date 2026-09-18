"""Console package scope, exact old-profile reuse, and complete raw review."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT/'build/codex-agent/r83as-console';BASE=PARENT/'queue-drain'
PACKAGE='R8.3as-x86_64-console';ACCEPTED='7d34f2378352c0eb46c4eec646edbb1a871964ac'
AR=ROOT/'build/codex-agent/r83ar-live-file/terminal-receipt'
PRIOR=AR/'verification-status-live-file-final.json'
PRIOR_SHA='ba842403f570aed91cc7c76b482456b8e1769a758bbd76547a5af524255d760c'
IMAGE=PARENT/'native/x86_64/reist-x86_64-bootstrap.elf'
STOP=PARENT/'verification-status-observer-stopped.json'
STOP_SHA='9bc27614aa2816d9fb803fa628bb79551466fa869d4a0e1719d3e0a5152e3f0f'
BITMAP_STOP=PARENT/'observer-binding/verification-status-bitmap-stopped.json'
BITMAP_STOP_SHA='1919aced10adb2186bc44d9bf560f66500d27fb85de551ec9e60dffd7d201f43'
INPUT_STOP=PARENT/'bitmap-adapter/verification-status-input-stopped.json'
INPUT_STOP_SHA='76237d7a509df8fbd85e1803ac430a788b68e6aa4dc959fff2b99f01ca3b4e97'
PREFLIGHT_STOP=PARENT/'acknowledged-input/verification-status-preflight-stopped.json'
PREFLIGHT_SHA='6ebbe3a9735ac6dec68eab0b120022128a8a0579589cb7eeaa1e252ce69af5d2'
QUEUE_STOP=PARENT/'acknowledged-input/verification-status-queue-stopped.json'
QUEUE_SHA='f666d2adf68f521f55b0063c383d3eef81e289edf111aac048663353aabed5c2'

def capture_delta(old,current):
    import ast
    from run_qemu_x86_64_runtime_clock import once
    def remove(source,name):
        body=ast.parse(source).body
        index=next(i for i,n in enumerate(body) if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
        node=body[index];lines=source.splitlines(keepends=True)
        end=body[index+1].lineno-1 if index+1<len(body) else len(lines)
        return ''.join(lines[:node.lineno-1]+lines[end:]),node
    current,cls=remove(current,'ConsoleFeeder')
    old,left=remove(old,'_capture_run');current,right=remove(current,'_capture_run')
    need(old==current,'console exact capture outside opted-in feeder')
    class Default(ast.NodeTransformer):
        def visit_If(self,node):
            test=node.test.values[0] if isinstance(node.test,ast.BoolOp) and isinstance(node.test.op,ast.And) else node.test
            if ast.unparse(test)=='console_input is not None':return []
            return self.generic_visit(node)
        def visit_Assign(self,node):
            if any(isinstance(n,ast.Name) and n.id=='console_feeder' for n in node.targets):return []
            return node
    need(ast.dump(Default().visit(left))==ast.dump(Default().visit(right)),'console default capture AST exact')

def commands(p):
    rows=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(rows)==12,'console twelve obligations');return rows
def gate_limit(n):return 300 if n<=7 else 180
def source_binding():
    candidates=sorted(BASE.glob('candidate-*/frozen.json'));need(len(candidates)==1,'console one queue-drain candidate')
    for index,path in enumerate(candidates,1):
        need(path.parent.name==f'candidate-{index:02d}','console candidate sequence')
        if path!=candidates[-1]:need(digest(PREFLIGHT_STOP)==PREFLIGHT_SHA and read(PREFLIGHT_STOP)['frozen']==link(path),'console sealed preflight only')
    f=read(candidates[-1]);need(f['head']==git('rev-parse','HEAD'),'console contract HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());p=queue['packages'][0]
    need(queue['active_id']==PACKAGE and p['id']==PACKAGE and p['status']=='active' and p==f['package'] and commands(p)==f['commands'],'console exact queue')
    for files in (f['source_inputs'],f['tools_sha256'],f['helpers'],f['snapshots']):verify_files(files)
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(f['sources']) and changed<=set(p['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'console exact attributed scope')
    need(f['candidate']==hashlib.sha256(json.dumps(f['source_inputs'],sort_keys=True).encode()).hexdigest(),'console candidate digest')
    need(digest(PRIOR)==PRIOR_SHA and f['prior_acceptance']==link(PRIOR),'console accepted AR')
    need(f['red']==link(PARENT/'expected-red.json') and read(PARENT/'expected-red.json')['expected_red'],'console retained actual expected red')
    need(digest(STOP)==STOP_SHA,'console immutable stopped window');stop=read(STOP)
    need(stop['gates_passed']==9 and stop['gates_failed']==[10] and stop['cumulative_images']==1 and stop['cumulative_guests']==1 and
         stop['remaining_qemu_gdb']==0 and stop['image']==link(IMAGE),'console exact stopped boundary')
    for name,sha in stop['source_inputs'].items():
        if name not in p['feeder_files']:need(f['source_inputs'][name]==sha,'console adapter-only delta '+name)
    need(digest(BITMAP_STOP)==BITMAP_STOP_SHA,'console immutable bitmap stop');bitmap_stop=read(BITMAP_STOP)
    need(bitmap_stop['cumulative_images']==1 and bitmap_stop['cumulative_guests']==2 and bitmap_stop['remaining_qemu_gdb']==0 and
         bitmap_stop['image']==link(IMAGE) and bitmap_stop['prior_stop']==link(STOP),'console exact second stop')
    for name,sha in bitmap_stop['source_inputs'].items():
        if name not in p['feeder_files']:need(f['source_inputs'][name]==sha,'console bitmap-only delta '+name)
    old=ROOT/read(ROOT/bitmap_stop['frozen']['path'])['directory']/'source/scripts__run_qemu_x86_64_console.py'
    current=(ROOT/'scripts/run_qemu_x86_64_console.py').read_text()
    from run_qemu_x86_64_runtime_clock import once
    import inspect,run_qemu_x86_64_console as console
    current=once(current,inspect.getsource(console.memory_adapter)+'\n','')
    current=once(current,'    code=memory_adapter(code,c,ram)\n','')
    need(current==old.read_text(),'console only bounded bitmap adapter and high comparison')
    need(digest(INPUT_STOP)==INPUT_STOP_SHA,'console immutable input stop');input_stop=read(INPUT_STOP)
    need(input_stop['cumulative_guests']==3 and input_stop['cumulative_images']==1 and input_stop['remaining_qemu_gdb']==0 and
         input_stop['image']==link(IMAGE) and input_stop['prior_stop']==link(BITMAP_STOP),'console exact third stop')
    for name,sha in input_stop['source_inputs'].items():
        if name not in p['feeder_files']:need(f['source_inputs'][name]==sha,'console feeder-only delta '+name)
    need(digest(ROOT/'scripts/run_qemu_x86_64_console.py')==input_stop['source_inputs']['scripts/run_qemu_x86_64_console.py'],'console unchanged observer and oracle')
    snapshot=ROOT/read(ROOT/input_stop['frozen']['path'])['directory']/'source/scripts__run_qemu_x86_64_boot_programs.py'
    capture_delta(snapshot.read_text(),(ROOT/'scripts/run_qemu_x86_64_boot_programs.py').read_text())
    need(read(PARENT/'acknowledged-input/expected-feeder-red.json')['expected_red'],'console actual feeder regression')
    pre=read(PREFLIGHT_STOP);verify_files(pre['evidence_sha256'])
    for name,sha in pre['source_inputs'].items():
        if name not in ('automation/reist-s03b.toml','docs/architecture/NATIVE_CONSOLE_CONTRACT.md','docs/development/CURRENT_WORK.md',
                        'scripts/verify_x86_64_console.py','test/test_x86_64_console.py','scripts/run_qemu_x86_64_boot_programs.py'):
            need(f['source_inputs'][name]==sha,'console preflight correction only '+name)
    need(digest(QUEUE_STOP)==QUEUE_SHA,'console immutable queue stop');queue_stop=read(QUEUE_STOP)
    need(queue_stop['cumulative_guests']==4 and queue_stop['cumulative_images']==1 and queue_stop['remaining_qemu_gdb']==0 and
         queue_stop['image']==link(IMAGE),'console exact queue stop')
    for name,sha in queue_stop['source_inputs'].items():
        if name not in p['feeder_files']:need(f['source_inputs'][name]==sha,'console queue-only delta '+name)
    old_capture=ROOT/read(ROOT/queue_stop['frozen']['path'])['directory']/'source/scripts__run_qemu_x86_64_boot_programs.py'
    current=(ROOT/'scripts/run_qemu_x86_64_boot_programs.py').read_text()
    drain='                if console_input is not None:\n                    for _ in range(127):\n                        try:data.extend(output.get_nowait())\n                        except queue.Empty:break\n'
    current=once(current,drain,'')
    current=once(current,"if console_input is not None and 'NATIVE_CONSOLE_READY\\n' in serial:","if console_input is not None:")
    need(current==old_capture.read_text(),'console exact guard and bounded drain only')
    need(read(BASE/'expected-queue-red.json')['expected_red'],'console actual loop regression')
    return f

def reuse_build(f):
    need(digest(QUEUE_STOP)==QUEUE_SHA,'console queue stop binding');verify_files(read(QUEUE_STOP)['evidence_sha256'])
    need(digest(INPUT_STOP)==INPUT_STOP_SHA,'console third stop binding');verify_files(read(INPUT_STOP)['evidence_sha256'])
    need(digest(BITMAP_STOP)==BITMAP_STOP_SHA,'console second stop binding');verify_files(read(BITMAP_STOP)['evidence_sha256'])
    need(digest(STOP)==STOP_SHA,'console stopped image binding');stop=read(STOP);verify_files(stop['evidence_sha256']);verify_files(stop['tools_sha256'])
    old=read(ROOT/stop['frozen']['path']);path=ROOT/old['directory']/'gate-09.json';gate=read(path)
    need(gate['passed'] and gate['exit_code']==0 and gate['candidate']==old['candidate'] and gate['command']==f['commands'][8]==old['commands'][8] and
         gate['log']==link(ROOT/gate['log']['path']) and 0<=gate['elapsed']<=180,'console exact old successful build')
    need(f['tools_sha256']==old['tools_sha256'] and stop['image']==link(IMAGE),'console unchanged tools and image')
    for name,sha in old['source_inputs'].items():
        if name not in f['package']['feeder_files']:need(f['source_inputs'][name]==sha,'console unchanged build input '+name)
    verify_files(gate['artifacts']);return link(path),gate
def prior_gates(f,last):
    refs=[]
    for n in range(1,last+1):
        path=ROOT/f['directory']/f'gate-{n:02d}.json';r=read(path)
        need(r['passed'] and r['exit_code']==0 and r['candidate']==f['candidate'] and r['command']==f['commands'][n-1] and
             0<=r['elapsed']<=gate_limit(n) and r['log']==link(ROOT/r['log']['path']),'console gate '+str(n))
        verify_files(r['artifacts']);refs.append(link(path))
    return refs
def abi_docs():
    f=source_binding();rows=[];started=time.monotonic()
    for name in ('test/test_syscall_abi_source.py','test/test_documentation.py'):
        command=[sys.executable,name,'-v'];remaining=300-(time.monotonic()-started);need(remaining>0,'console host bound')
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=remaining,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        path=ROOT/f['directory']/('abi-docs-'+str(len(rows)+1)+'.log')
        with path.open('xb') as out:out.write(r.stdout+r.stderr)
        rows.append(dict(command=command,exit_code=r.returncode,log=link(path)))
        need(r.returncode==0,'console ABI/docs '+name+' '+(r.stdout+r.stderr).decode(errors='replace')[-1800:])
    return dict(passed=True,kind='abi-docs',candidate=f['candidate'],commands=rows)
def references():
    from build_user_program import find_zig
    f=source_binding();prior_gates(f,7);ar=read(PRIOR)
    need(ar['accepted'] and ar['clean_worktree'] and ar['implementation_commit']==ACCEPTED and ar['gates_passed']==14 and ar['qualified_guests']==25,'console AR accepted boundary')
    verify_files(ar['evidence_sha256'])
    allowed=set(f['package']['allowed_files'])|set(ar['documentation_sha256'])
    for name,sha in ar['source_inputs'].items():
        if name not in allowed:need(digest(ROOT/name)==sha,'console unrelated accepted input '+name)
    folder=BASE/('references-'+uuid.uuid4().hex);folder.mkdir();outputs={}
    env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
    basic=['REIST_NATIVE_PROGRAMS','REIST_NATIVE_RUNTIME','REIST_NATIVE_HEAP_BINDING','REIST_NATIVE_IPC_BINDING']
    profiles=[[],basic,basic+['REIST_NATIVE_LIFECYCLE','REIST_NATIVE_STARTUP','REIST_NATIVE_IMPORT','REIST_NATIVE_WIDE',
        'REIST_NATIVE_TASK_POOL','REIST_NATIVE_POOL_PIO','REIST_NATIVE_PIO','REIST_NATIVE_SERVICE_CPU','REIST_NATIVE_PIO_TRACE','REIST_NATIVE_CPU_TRACE']]
    for name in ('arch/x86_64/proc/process_run.inc','arch/x86_64/proc/cooperative_scheduler.asm','arch/x86_64/kernel/bootstrap_core.c'):
        original=folder/('before-'+Path(name).name);original.write_bytes(subprocess.check_output(['git','show',ACCEPTED+':'+name],cwd=ROOT,timeout=10))
        for index,defines in enumerate(profiles):
            compared=[]
            for label,path in (('before',original),('after',ROOT/name)):
                if name.endswith('.c'):
                    flags=[] if index==0 else ['-DX86_64_NATIVE_'+x+'=1' for x in ('PROCESSES','IPC','RAM','HEAP','PROGRAMS')]
                    if index==2:flags+=['-DX86_64_NATIVE_LIFECYCLE=1','-DREIST_NATIVE_TASK_POOL=1','-DREIST_NATIVE_SERVICE_CPU=1']
                    argv=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-E','-P','-I.','-Iarch/x86_64/kernel',*flags,str(path)]
                else:
                    flags=['-D'+x+'=1' for x in defines]
                    if index:flags+=['-DX86_64_NATIVE_RAM=1','-DC_CORE_LAYOUT_PATH="'+str(ROOT/'build/codex-agent/r83ar-live-file/native/x86_64/bootstrap_core_layout.inc').replace('\\','/')+'"']
                    argv=['C:/tools/nasm-3.02/nasm.exe','-E','-f','elf32',*flags,str(path)]
                r=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                stem=folder/f'{Path(name).name}-{index}-{label}'
                log=stem.with_name(stem.name+'.log');log.write_bytes(r.stderr)
                need(r.returncode==0,'console actual default preprocessing '+r.stderr.decode(errors='replace')[-1500:])
                raw=re.sub(rb'(?m)^%line[^\n]*\n',b'',r.stdout) if not name.endswith('.c') else r.stdout
                output=stem.with_name(stem.name+'.i');output.write_bytes(raw);compared.append(raw.split())
                for p in (log,output):outputs[p.relative_to(ROOT).as_posix()]=digest(p)
            need(compared[0]==compared[1],'console byte-token exact old profile '+name+str(index))
    ref=ROOT/ar['gate_receipts'][8]['path'];need(ar['gate_receipts'][8]==link(ref),'console prior exact reference receipt')
    rr=read(ref);need(rr['passed'] and rr['exit_code']==0,'console prior reference success');verify_files(rr['artifacts'])
    return dict(passed=True,kind='references',candidate=f['candidate'],prior_acceptance=link(PRIOR),
                references=link(ref),artifacts=rr['artifacts'],preprocessing=outputs,new_builds=0,new_guests=0)
def review():
    import run_qemu_x86_64_console as console
    f=source_binding();gates=prior_gates(f,11)
    paths=list((BASE/'guests').glob('attempt-*/summary.json'));need(len(paths)==1,'console unique matrix')
    summary=read(paths[0]);need(summary['closed'] and summary['passed'] and summary['candidate']==f['candidate'] and summary['image']==link(IMAGE),'console complete qualified matrix')
    need([(r['case'],r['ram']) for r in summary['cases']]==list(console.CASES),'console seven cases')
    need(0<summary['guest_elapsed']<=140 and summary['elapsed']<=180 and abs(summary['guest_elapsed']-sum(r['elapsed'] for r in summary['cases']))<1e-6,'console aggregate bounds')
    evidence={}
    for row in summary['cases']:
        need(row['passed'] and 0<row['elapsed']<=20,'console bounded passed guest');folder=ROOT/row['folder']
        serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text();case=row['case']
        if isinstance(case,str):console.validate_rejection(serial,trace,case)
        else:
            console.validate(serial,trace,case,row['ram']);sent=read(folder/'console-input.json')
            console.boot.ConsoleFeeder.validate(console.inputs(case),trace,read(folder/'console-chunks.json'),sent)
            need([r['payload'] for r in sent]==[r.hex() for r in console.inputs(case)] and
                 [r['run'] for r in sent]==[1,2] and all(r['bytes']==len(bytes.fromhex(r['payload'])) and 0<r['elapsed']<17 for r in sent),'console exact serial feeder')
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','console complete cleanup')
        dumps=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
        need(0<len(dumps)<=2048 and sum(r['bytes'] for r in dumps)<=128*1024*1024,'console raw memory bound')
        need([r['equivalence'] for r in dumps if r['equivalence'] is not None]==['kernel','high'],'console independent memory equivalence')
        for index,r in enumerate(dumps,1):
            path=folder/'binary-memory'/r['file']
            need(r['sequence']==index and path.name==f'ram-{index:04d}.bin' and path.stat().st_size==r['bytes'] and digest(path)==r['sha256'],'console every raw byte bound')
        for p in folder.rglob('*'):
            if p.is_file():need(not p.is_symlink(),'console no evidence symlink');evidence[p.relative_to(ROOT).as_posix()]=digest(p)
    return dict(passed=True,kind='review',candidate=f['candidate'],gates=gates,matrix=link(paths[0]),
                cases=7,new_images=0,new_guests=7,guest_elapsed=summary['guest_elapsed'],evidence_sha256=evidence,
                cumulative_images=1,cumulative_guests=11,cumulative_guest_elapsed=read(QUEUE_STOP)['cumulative_guest_elapsed']+summary['guest_elapsed'])
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('abi-docs','references','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args();kind=next(n.replace('_','-') for n,v in vars(a).items() if v);started=time.monotonic();row=dict(passed=False,kind=kind)
    try:
        row=abi_docs() if kind=='abi-docs' else references() if kind=='references' else review()
        print('CONSOLE_VERIFY_OK',kind);return 0
    except Exception as error:row['error']=str(error);print('CONSOLE_VERIFY_FAIL',kind,error);return 1
    finally:
        row['elapsed']=time.monotonic()-started
        with (BASE/(kind+'-'+uuid.uuid4().hex+'.json')).open('x') as out:json.dump(row,out,indent=2)
if __name__=='__main__':raise SystemExit(main())
