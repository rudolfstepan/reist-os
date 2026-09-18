"""AR frozen scope, reference reuse, actual kernel equality and raw review."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT/'build/codex-agent/r83ar-live-file';BASE=PARENT/'terminal-receipt'
PACKAGE='R8.3ar-x86_64-live-file'
ACCEPTED='c7e5e72ad05c7a0e9355e9dc4b0fc99ad99ba8ff'
AQ=ROOT/'build/codex-agent/r83aq-service-pio/active-calibration'
AQ_PROOF=AQ/'verification-status-service-pio-final.json'
AQ_SHA='a7d9665b47a74f38bd46b5e47f2ee69a04cee211ab347aeb38a7719decdd6535'
IMAGE=PARENT/'native/x86_64/reist-x86_64-bootstrap.elf'
STOP=PARENT/'verification-status-pre-guest-stopped.json'
STOP_SHA='4ad99449bb5ca153dfa8e512553af8d42d4e88d5aca2d127f77fd641d17045cb'
PATH_STOP=PARENT/'path-adapter/verification-status-selector-stopped.json'
PATH_STOP_SHA='0afb6a8cac2bfe83a4c75a9cdb4d7aaf48083cafea2ab02929dee74473d6d891'
OBSERVER_STOP=PARENT/'observer-adapter/verification-status-cpu-stopped.json'
OBSERVER_STOP_SHA='7ceed258ddc7aeba9ed9aa8054d82c981310d5ba2e7b18be210494b3519ea5d7'
COLD_STOP=PARENT/'cold-control/verification-status-terminal-receipt-stopped.json'
COLD_STOP_SHA='16ed2d44d24545f30689b21e4325fe111cfd0dd406e9e9d4e8167fdb114f82e8'
TERMINAL_BRANCH="""        assert slot in (2,3,4)
        t=task(slot)
        if t[0]==0 and t[1]==0:
            gen=identity>>32;assert 0<gen<0x80000000 and len(t)==128 and not any(t)
            info=CONFIG['roles'][gen];root=task(0)[1];entry=starts[gen]
            assert info['slot']==slot and info['root']==root
            assert entry['slot']==slot and entry['parent']==root and not entry['live']
            result=info['status']|((0 if info['state']==4 else 1 if info['status'] else 2)<<32)
            receipt=struct.unpack('<8Q',mem(S['family_records']+slot*64,64))
            assert receipt==(identity,root<<32,0,0,result,4,0,0)
            return
"""

def terminal_inverse(current):
    from run_qemu_x86_64_file_launch import once
    for new,old in (
        ("/r83ar-live-file/terminal-receipt'","/r83ar-live-file/cold-control'"),
        (TERMINAL_BRANCH,''),
        ('admit_runtime,source_binding,digest,link,need,reuse_prefix','admit_runtime,source_binding,digest,link,need'),
        ('    prefix=reuse_prefix(frozen)\n',''),
        ("    summary=dict(passed=False,closed=False,candidate=frozen['candidate'],cases=list(prefix),\n"
         "                 guest_elapsed=sum(r['elapsed'] for r in prefix),image=link(args.image),\n"
         "                 reused_guests=len(prefix),new_guests=0,new_guest_elapsed=0.0)",
         "    summary=dict(passed=False,closed=False,candidate=frozen['candidate'],cases=[],guest_elapsed=0.0,image=link(args.image))"),
        ('for case,layout,ram,point in CASES[len(prefix):]:','for case,layout,ram,point in CASES:'),
        ("            need(summary['new_guests']<14 and summary['new_guest_elapsed']+45<=630,'live fresh guest reserve')\n",''),
        ('passed=False,executed=True)','passed=False)'),
        ("            summary['new_guests']+=1\n",''),
        ("                summary['new_guest_elapsed']+=row['elapsed']\n",'')):
        current=once(current,new,old)
    return current

def commands(package):
    result=package['targeted_tests']+package['package_tests']+package['runtime_tests']
    need(len(result)==14,'AR exact14 obligations');return result

def gate_limit(n):return 300 if n<=8 else 1200 if n==12 else 180

def source_binding():
    candidates=sorted(BASE.glob('candidate-*/frozen.json'))
    need(len(candidates)==1,'AR one changed terminal-receipt candidate')
    for n,p in enumerate(candidates,1):
        need(p.parent.name==f'candidate-{n:02d}','AR candidate sequence')
        if p!=candidates[-1]:
            stop=read(p.parent/'stopped.json')
            need(stop['candidate']==read(p)['candidate'] and stop['failed_gate']<10,'AR pre-build changed correction only')
    f=read(candidates[-1]);need(f['head']==git('rev-parse','HEAD'),'AR contract head')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    p=next(p for p in queue['packages'] if p['id']==PACKAGE)
    need(queue['active_id']==PACKAGE and p['status']=='active' and p==f['package'] and commands(p)==f['commands'],'AR frozen queue')
    verify_files(f['source_inputs']);verify_files(f['helpers']);verify_files(f['tools_sha256'])
    need(digest(AQ_PROOF)==AQ_SHA==f['prior_acceptance']['sha256'],'AR accepted AQ pin')
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(f['sources']) and changed<=set(p['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'AR exact visible scope')
    need(f['candidate']==hashlib.sha256(json.dumps(f['source_inputs'],sort_keys=True).encode()).hexdigest(),'AR candidate hash')
    need(f['red']==link(PARENT/'expected-red.json') and read(PARENT/'expected-red.json')['expected_red'],'AR retained expected red')
    need(digest(STOP)==STOP_SHA,'AR immutable pre-guest stop')
    stopped=read(STOP)
    need(stopped['gates_passed']==11 and stopped['gates_failed']==[12] and stopped['new_images']==1 and
         stopped['new_guests']==0 and stopped['remaining_qemu_gdb']==0,'AR exact stopped boundary')
    for name,sha in stopped['source_inputs'].items():
        if name not in p['path_adapter_files']:need(f['source_inputs'][name]==sha,'AR path-only correction '+name)
    need(digest(PATH_STOP)==PATH_STOP_SHA,'AR immutable selector stop')
    path_stop=read(PATH_STOP)
    need(path_stop['gates_passed']==11 and path_stop['gates_failed']==[12] and path_stop['new_images']==0 and
         path_stop['new_guests']==1 and path_stop['remaining_qemu_gdb']==0 and
         path_stop['image']==stopped['image'] and 0<path_stop['guest_elapsed']<4,'AR exact selector stop')
    for name,sha in path_stop['source_inputs'].items():
        if name not in p['path_adapter_files']:need(f['source_inputs'][name]==sha,'AR observer-only correction '+name)
    need(digest(OBSERVER_STOP)==OBSERVER_STOP_SHA,'AR immutable CPU stop')
    observer_stop=read(OBSERVER_STOP)
    need(observer_stop['gates_passed']==11 and observer_stop['gates_failed']==[12] and observer_stop['new_images']==0 and
         observer_stop['cumulative_guests']==2 and observer_stop['remaining_qemu_gdb']==0 and
         observer_stop['image']==stopped['image'] and 9<observer_stop['cumulative_guest_elapsed']<10,'AR exact CPU stop')
    for name,sha in observer_stop['source_inputs'].items():
        if name not in p['path_adapter_files']:need(f['source_inputs'][name]==sha,'AR cold-control-only correction '+name)
    need(digest(COLD_STOP)==COLD_STOP_SHA,'AR immutable terminal stop')
    cold=read(COLD_STOP)
    need(cold['gates_passed']==11 and cold['gates_failed']==[12] and cold['passed_guests']==11 and
         cold['cumulative_guests']==14 and cold['remaining_qemu_gdb']==0 and cold['image']==stopped['image'],
         'AR exact terminal boundary')
    for name,sha in cold['source_inputs'].items():
        if name not in p['path_adapter_files']:need(f['source_inputs'][name]==sha,'AR terminal-only correction '+name)
    old=ROOT/read(ROOT/stopped['frozen']['path'])['directory']/'source/scripts__run_qemu_x86_64_live_file.py'
    current=(ROOT/'scripts/run_qemu_x86_64_live_file.py').read_text()
    from run_qemu_x86_64_file_launch import once
    current=terminal_inverse(current)
    cold_source=ROOT/read(ROOT/cold['frozen']['path'])['directory']/'source/scripts__run_qemu_x86_64_live_file.py'
    need(current==cold_source.read_text(),'AR exact terminal observer and prefix adapter only')
    current=once(current,"/r83ar-live-file/cold-control'","/r83ar-live-file'")
    current=once(current,'    args.image=args.image.resolve();args.evidence=args.evidence.resolve()\n','')
    current=once(current,'    stop_reads.before_write()\n','')
    current=once(current,"binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True",
                 "binary_memory='full',service_pio_budget=True")
    current=once(current,"Hook('family_syscall64',control_syscall)\nHook('native_pio_apply64.fence_request',control_syscall)",
                 "Hook('process_run_syscall64',control_syscall)")
    need(current==old.read_text(),'AR exact runtime except path/cache/proof transport/cold hooks')
    need(read(PARENT/'path-adapter/expected-path-red.json')['expected_red'],'AR actual path regression red')
    need(read(PARENT/'observer-adapter/expected-observer-red.json')['expected_red'],'AR actual observer regression red')
    need(read(PARENT/'cold-control/expected-cold-red.json')['expected_red'],'AR actual cold-control regression red')
    need(read(BASE/'expected-terminal-red.json')['expected_red'],'AR actual terminal regression red')
    return f

def reuse_build(f):
    stopped=read(STOP);verify_files(stopped['evidence_sha256'])
    verify_files(read(PATH_STOP)['evidence_sha256'])
    verify_files(read(OBSERVER_STOP)['evidence_sha256'])
    verify_files(read(COLD_STOP)['evidence_sha256'])
    row=read(ROOT/read(ROOT/stopped['frozen']['path'])['directory']/'gate-10.json')
    need(row['passed'] and row['exit_code']==0 and row['command']==f['commands'][9] and
         row['log']==link(ROOT/row['log']['path']),'AR exact retained build command/log')
    verify_files(row['artifacts']);verify_files(stopped['tools_sha256'])
    need(row['artifacts'][IMAGE.relative_to(ROOT).as_posix()]==digest(IMAGE)==stopped['image']['sha256'],'AR retained image binding')
    # source_binding enforces every build input byte, including entrypoints,
    # linker/configuration, kernel, Ring3/SDK and generator, against this stop.
    source_binding();return row

def reuse_prefix(f):
    import run_qemu_x86_64_live_file as live
    need(digest(COLD_STOP)==COLD_STOP_SHA,'AR retained prefix stop pin')
    cold=read(COLD_STOP);verify_files(cold['evidence_sha256']);verify_files(cold['tools_sha256'])
    need(cold['image']==link(IMAGE),'AR same prefix image')
    manifest=read(ROOT/cold['frozen']['path']);need(cold['frozen']==link(ROOT/cold['frozen']['path']),'AR prefix frozen binding')
    need(manifest['tools_sha256']==f['tools_sha256'],'AR prefix tools unchanged')
    for name,sha in manifest['source_inputs'].items():
        if name not in f['package']['path_adapter_files']:need(f['source_inputs'][name]==sha,'AR prefix input '+name)
    current=(ROOT/'scripts/run_qemu_x86_64_live_file.py').read_text()
    prior=(ROOT/manifest['directory']/'source/scripts__run_qemu_x86_64_live_file.py').read_text()
    need(terminal_inverse(current)==prior,'AR exact prefix observer/oracle implication')
    gate=read(ROOT/manifest['directory']/'gate-12.json')
    need(gate['candidate']==cold['candidate'] and not gate['passed'] and gate['exit_code']==1 and
         gate['command']==manifest['commands'][11] and gate['log']==link(ROOT/gate['log']['path']),'AR stopped prefix command/log')
    need(gate['command'].replace('/cold-control/guests','/terminal-receipt/guests')==f['commands'][11],'AR prefix exact command delta')
    path=ROOT/cold['matrix']['path'];need(cold['matrix']==link(path),'AR prefix matrix link')
    summary=read(path);rows=summary['cases']
    need(summary['closed'] and not summary['passed'] and summary['candidate']==cold['candidate'] and
         summary['image']==link(IMAGE) and len(rows)==12 and not rows[-1]['passed'],'AR failed case excluded')
    need([(r['case'],r['layout'],r['ram'],r['point']) for r in rows]==list(live.CASES[:12]),'AR exact case prefix')
    reused=[]
    for row in rows[:11]:
        need(row['passed'] and 0<row['elapsed']<=45 and row['folder'].startswith('build/codex-agent/r83ar-live-file/cold-control/guests/'),'AR passed prefix only')
        folder=ROOT/row['folder'];live.pio.safe_folder(folder)
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and metrics['cleanup_seconds']<=3,'AR prefix cleanup')
        for path in folder.rglob('*'):
            if path.is_file():
                name=path.relative_to(ROOT).as_posix()
                need(not path.is_symlink() and gate['artifacts'].get(name)==cold['evidence_sha256'].get(name)==digest(path),'AR exact prefix raw '+name)
        reused.append(dict(row,executed=False,reused_from=link(COLD_STOP)))
    return reused

def prior_gates(f,last):
    result=[]
    for n in range(1,last+1):
        path=ROOT/f['directory']/f'gate-{n:02d}.json';row=read(path)
        need(row['passed'] and row['exit_code']==0 and row['candidate']==f['candidate'] and
             row['command']==f['commands'][n-1] and 0<=row['elapsed']<=gate_limit(n),'AR gate '+str(n))
        need(row['log']==link(ROOT/row['log']['path']),'AR gate log')
        verify_files(row['artifacts']);result.append(link(path))
    return result

def host_group(kind):
    f=source_binding();begin=time.monotonic();rows=[]
    group=[['test/test_syscall_abi_source.py','-v'],['test/test_documentation.py','-v']] if kind=='abi-docs' else [
        ['test/test_x86_64_service_cpu.py',*['ServiceCPUTests.test_actual_'+n for n in
            ('period_core','family_admission','service_family_retirement','scheduler_binding','full_snapshot_before_effects','run_admission','sdk_layout_and_dispatch')],'-v'],
        ['test/test_x86_64_task_pool.py',*['TaskPoolTests.test_actual_'+n for n in
            ('run_admission','c_owners','family_pool','whole_pool_frame_ownership')],'-v'],
        ['test/test_x86_64_native_ipc.py','-v']]
    for args in group:
        remaining=300-(time.monotonic()-begin);need(remaining>0,'AR host group bound')
        command=[sys.executable,*args];started=time.monotonic()
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=remaining,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        log=ROOT/f['directory']/(kind+'-'+str(len(rows)+1)+'.log')
        with log.open('xb') as stream:stream.write(r.stdout+r.stderr)
        rows.append(dict(command=command,exit_code=r.returncode,elapsed=time.monotonic()-started,log=link(log)))
        if r.returncode:print((r.stdout+r.stderr).decode(errors='replace')[-3000:]);raise ValueError('AR host subgroup '+args[0])
    return dict(passed=True,kind=kind,commands=rows)

def references():
    from build_user_program import find_zig
    f=source_binding();gates=prior_gates(f,8);a=read(AQ_PROOF)
    need(a['accepted'] and a['clean_worktree'] and a['implementation_commit']==ACCEPTED and a['gates_passed']==15 and a['qualified_guests']==18,'AR accepted AQ boundary')
    verify_files(a['protected_artifacts']);verify_files(a['evidence_sha256'])
    # Apart from these explicitly frozen sources, accepted executable inputs stay exact.
    allowed=set(f['package']['allowed_files'])|set(a.get('documentation_sha256',{}))
    for name,sha in a['source_inputs'].items():
        if name not in allowed:need(digest(ROOT/name)==sha,'AR unchanged accepted mechanism '+name)
    folder=BASE/('reference-'+uuid.uuid4().hex);folder.mkdir()
    outputs={};env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
    for name in ('filesystem.c','file_program.c'):
        old=folder/('old-'+name)
        old.write_bytes(subprocess.check_output(['git','show',ACCEPTED+':arch/x86_64/user/'+name],cwd=ROOT,timeout=10))
        for role in (range(4) if name=='filesystem.c' else (0,)):
            values=[]
            for label,path in (('before',old),('after',ROOT/'arch/x86_64/user'/name)):
                command=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-E','-P','-Iuserspace/sdk/include',
                    '-Iarch/x86_64/user','-DPROGRAM_ID='+str(role),'-DFILESYSTEM_CASE=0','-DFILESYSTEM_LAYOUT=2',
                    '-Dimport_blob=((unsigned char[1]){0})','-Dfilesystem_blob=((unsigned char[1]){0})',str(path)]
                r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                log=folder/f'{name}-{role}-{label}.log';log.write_bytes(r.stderr)
                need(r.returncode==0,'AR default preprocessing '+r.stderr.decode(errors='replace')[-1500:])
                output=folder/f'{name}-{role}-{label}.i';output.write_bytes(r.stdout);values.append(r.stdout.split())
                for p in (log,output):outputs[p.relative_to(ROOT).as_posix()]=digest(p)
            need(values[0]==values[1],'AR exact legacy C tokens '+name+str(role))
    # Reference gate already binds command/tool/source/artifact provenance, not just filenames.
    ref_path=ROOT/a['gate_receipts'][9]['path'];need(a['gate_receipts'][9]==link(ref_path),'AR AQ reference receipt')
    reference=read(ref_path);need(reference['passed'] and reference['exit_code']==0,'AR prior reference success')
    verify_files(reference['artifacts'])
    return dict(passed=True,kind='references',candidate=f['candidate'],gates=gates,prior_acceptance=link(AQ_PROOF),
                references=link(ref_path),artifacts=reference['artifacts'],preprocessing=outputs,new_builds=0,new_guests=0)

def kernel_equivalence():
    f=source_binding();prior_gates(f,10);old=AQ/'native/x86_64';new=IMAGE.parent
    names={p.name for p in old.glob('*.o')}-{ 'elf64_loader.o' }
    need(names and names=={p.name for p in new.glob('*.o')}-{'elf64_loader.o'},'AR exact kernel object inventory')
    names|={'reist-x86_64-c-core.elf','bootstrap_core_layout.inc','bootstrap_core_layout.json',
            'bootstrap_core_text.bin','bootstrap_core_rodata.bin','bootstrap_core_data.bin'}
    compared={}
    for name in sorted(names):
        need(digest(old/name)==digest(new/name),'AR byte-exact accepted kernel '+name)
        compared[name]=dict(before=link(old/name),after=link(new/name))
    return dict(passed=True,kind='kernel-equivalence',candidate=f['candidate'],objects=compared,
                loader_exclusion='catalog bytes intentionally change; loader source/flags frozen',image=link(IMAGE))

def admit_runtime(image,evidence):
    f=source_binding();prior_gates(f,11)
    need(image.resolve()==IMAGE.resolve() and evidence.resolve()==BASE/'guests','AR runtime output scope')
    need(not list((BASE/'guests').glob('attempt-*')),'AR one matrix, no post-build retry')
    row=read(ROOT/f['directory']/'gate-10.json')
    need(row['artifacts'][IMAGE.relative_to(ROOT).as_posix()]==digest(IMAGE),'AR build image binding')
    return f

def review():
    import run_qemu_x86_64_live_file as live
    f=source_binding();gates=prior_gates(f,13)
    paths=list((BASE/'guests').glob('attempt-*/summary.json'));need(len(paths)==1,'AR unique matrix')
    path=paths[0];summary=read(path)
    need(summary['passed'] and summary['closed'] and summary['candidate']==f['candidate'] and summary['image']==link(IMAGE),'AR matrix acceptance')
    need([(r['case'],r['layout'],r['ram'],r['point']) for r in summary['cases']]==list(live.CASES),'AR complete25 cases')
    prefix=reuse_prefix(f)
    need(summary['cases'][:11]==prefix and summary['reused_guests']==11 and summary['new_guests']==14 and
         all(r.get('executed') is True for r in summary['cases'][11:]),'AR exact reused/fresh partition')
    need(0<summary['new_guest_elapsed']<=630 and
         abs(summary['new_guest_elapsed']-sum(r['elapsed'] for r in summary['cases'][11:]))<1e-6 and
         abs(summary['guest_elapsed']-sum(r['elapsed'] for r in summary['cases']))<1e-6,'AR exact cumulative time accounting')
    need(0<summary['guest_elapsed']<=1125 and summary['elapsed']<=1200,'AR total guest bound')
    config,counts,raw=live.image_config(IMAGE);evidence={}
    for row in summary['cases']:
        need(row['passed'] and 0<row['elapsed']<=45,'AR guest passed within bound')
        folder=ROOT/row['folder'];live.pio.safe_folder(folder)
        serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
        live.validate(serial,trace,row['case'],row['layout'],row['oom'],counts,raw,
                      (folder/live.cpu.CPU_FILE).read_bytes(),(folder/'cpu-trace-v1.bin').read_bytes())
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','AR exact cleanup')
        disk=live.media.image(live.media.LAYOUTS[row['layout']],program=live.file.program_variant(raw,row['case']))
        need((folder/'generated.raw').read_bytes()==disk,'AR unchanged generated disk')
        for phase in ('before','after'):
            m=read(folder/('media-'+phase+'.json'))
            need(m['passed'] and m['phase']==phase and m['overlay_allocated_data']==0 and m['logical_bytes']==len(disk) and m['base_sha256']==hashlib.sha256(disk).hexdigest(),'AR read-only backing/overlay')
        reads=live.cpu.binary_capacity(folder)
        need([r['equivalence'] for r in reads if r['equivalence'] is not None]==['kernel','high'],'AR independent byte equivalence')
        for n,r in enumerate(reads,1):
            p=folder/'binary-memory'/r['file']
            need(r['sequence']==n and p.name==f'ram-{n:04d}.bin' and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'AR complete raw RAM')
        for p in folder.rglob('*'):
            if p.is_file():need(not p.is_symlink(),'AR evidence symlink');evidence[p.relative_to(ROOT).as_posix()]=digest(p)
    return dict(passed=True,kind='review',candidate=f['candidate'],gates=gates,matrix=link(path),evidence_sha256=evidence,
                cases=25,new_images=0,reused_guests=11,new_guests=14,guest_elapsed=summary['guest_elapsed'],
                cumulative_images=1,cumulative_guests=28,
                cumulative_guest_elapsed=read(COLD_STOP)['cumulative_guest_elapsed']+summary['new_guest_elapsed'])

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('core-hosts','abi-docs','references','kernel-equivalence','review'):g.add_argument('--'+name,action='store_true')
    args=p.parse_args();kind=next(n.replace('_','-') for n,v in vars(args).items() if v)
    started=time.monotonic();row=dict(passed=False,kind=kind)
    try:
        row=host_group(kind) if kind in ('core-hosts','abi-docs') else references() if kind=='references' else kernel_equivalence() if kind=='kernel-equivalence' else review()
        print('LIVE_FILE_VERIFY_OK',kind);return 0
    except Exception as error:
        row['error']=str(error);print('LIVE_FILE_VERIFY_FAIL',kind,error);return 1
    finally:
        row['elapsed']=time.monotonic()-started
        with (BASE/(kind+'-'+uuid.uuid4().hex+'.json')).open('x') as stream:json.dump(row,stream,indent=2)

if __name__=='__main__':raise SystemExit(main())
