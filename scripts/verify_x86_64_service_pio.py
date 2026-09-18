"""Frozen AQ inputs, exact old-profile reuse and full combined guest review."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
from run_qemu_x86_64_file_launch import once
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/codex-agent/r83aq-service-pio/active-calibration'
PACKAGE='R8.3aq-x86_64-service-pio';IMAGE=BASE/'native/x86_64/reist-x86_64-bootstrap.elf'


def admission():
    a=read(BASE/'admission.json')
    for key in ('calibration_stop','calibration_diagnosis'):need(a[key]==link(ROOT/a[key]['path']),'AQ exact calibration boundary '+key)
    need(a['trace_host_stop']==link(ROOT/a['trace_host_stop']['path']),'AQ retained trace host failure')
    for key in ('helper','parent_admission','stopped','diagnosis','scope_stop','prior_acceptance','red','earlier_invocation_failure','fixture_parent','retained_build','retained_frozen','reap_baseline','host_stop','host_diagnosis','ipc_stop','ipc_diagnosis','profile_stop','profile_diagnosis','trace_stop','trace_parent_stop'):
        need(a[key]==link(ROOT/a[key]['path']),'AQ admission '+key)
    return a


def source_binding():
    a=admission();paths=sorted(BASE.glob('candidate-*/frozen-candidate.json'))
    need(len(paths)==1 and paths[0].parent.name=='candidate-01','AQ one trace candidate')
    f=read(paths[0]);need(f['head']==a['head']==git('rev-parse','HEAD'),'AQ contract head')
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    need(q==a['queue'] and f['commands']==a['commands'] and f['package']==a['package'],'AQ frozen obligations')
    need(f['admission']==link(BASE/'admission.json') and f['helper']==link(ROOT/f['helper']['path']),'AQ frozen helpers')
    need(f['idle_red']==link(BASE/'expected-red.json') and read(BASE/'expected-red.json')['expected_red'],'AQ retained red')
    stop=read(ROOT/a['calibration_stop']['path'])
    need(not stop['accepted'] and stop['total_images']==6 and stop['gates_passed']==11 and stop['gates_failed']==[12] and
         stop['total_guest_attempts']==a['spent_guests']==18 and round(stop['total_guest_elapsed'],6)==a['spent_seconds']==450.884613 and
         stop['remaining_qemu_gdb']==0,'AQ exact trace runtime boundary')
    verify_files(stop['evidence_sha256'])
    corrections={'automation/reist-s03b.toml','arch/x86_64/user/service_pio_workload.h','test/test_x86_64_service_pio.py',
        'scripts/run_qemu_x86_64_service_pio.py','scripts/verify_x86_64_service_pio.py',
        'docs/architecture/NATIVE_SERVICE_PIO_CONTRACT.md','docs/development/CURRENT_WORK.md'}
    for name,sha in stop['source_inputs'].items():
        if name not in corrections:need(digest(ROOT/name)==sha,'AQ calibration-only correction '+name)
    previous=ROOT/read(ROOT/stop['frozen']['path'])['directory']/'source'
    old_runtime=previous/'scripts__run_qemu_x86_64_service_pio.py'
    need((ROOT/'scripts/run_qemu_x86_64_service_pio.py').read_text().replace("/active-calibration'","/cpu-trace-adapter'")==old_runtime.read_text(),
         'AQ exact runtime path-only correction')
    before=(previous/'arch__x86_64__user__service_pio_workload.h').read_text()
    current=(ROOT/'arch/x86_64/user/service_pio_workload.h').read_text()
    current=once(current,'bounded active-clock calibration','exact accepted AP calibration')
    def calibration(body):
        return body.split('static uint64_t service_quantum(void)',1)[1].split('static int service_pio_prepare',1)[0]
    need(once(current,calibration(current),calibration(before))==before,'AQ only calibration function changes')
    for name,ref in a['trace_originals'].items():need(ref==link(ROOT/ref['path']),'AQ immutable trace baseline '+name)
    for key in ('source_inputs','sources','snapshots','tools_sha256'):verify_files(f[key])
    verify_files(a['protected_artifacts'])
    need(f['candidate']==hashlib.sha256(json.dumps(f['source_inputs'],sort_keys=True).encode()).hexdigest(),'AQ candidate digest')
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(f['sources']) and changed<=set(a['package']['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'AQ exact attributed scope')
    for name,sha in a['source_inputs'].items():
        if name not in corrections:need(f['source_inputs'][name]==sha,'AQ unchanged implementation '+name)
    return f


def gate_limit(index):return 300 if index<=9 else 800 if index==12 else 150 if index==13 else 180


def gate_binding(f,index,row):
    need(1<=index<=15 and row['candidate']==f['candidate'] and row['command']==f['commands'][index-1] and
         row['passed'] is True and row['exit_code']==0 and 0<=row['elapsed']<=gate_limit(index),'AQ successful exact gate')
    verify_files({row['log']['path']:row['log']['sha256']})
    if index in (10,11,12,13,15):need(row.get('artifacts'),'AQ complete gate artifacts');verify_files(row['artifacts'])


def prior_gates(f,last):
    directory=ROOT/f['directory'];rows=[]
    for index in range(1,last+1):
        path=directory/f'gate-{index:02d}.json';gate_binding(f,index,read(path));rows.append(link(path))
    return rows


def matrix_budget(candidate,fatal,starting=False):
    a=admission();total=a['spent_guests'];spent=a['spent_seconds'];current=[]
    for kind,name in ((False,'guests'),(True,'fatal-guests')):
        paths=list((BASE/name).glob('attempt-*/summary.json'));need(len(paths)<=1,'AQ one renewed matrix')
        candidates=set()
        for path in paths:
            row=read(path);need(row['closed'] and row['fatal']==kind and row['candidate'] not in candidates,'AQ closed unique attempts')
            candidates.add(row['candidate']);need(len(row['cases'])<=(2 if kind else 16),'AQ case count')
            need(0<=row['guest_elapsed']<=(90 if kind else 720),'AQ matrix elapsed')
            total+=len(row['cases']);spent+=row['guest_elapsed']
            if row['candidate']==candidate and kind==fatal:current.append(row)
    need(total<=a['max_guests']==36 and spent<=a['max_seconds']==1260.884613,'AQ cumulative budget')
    if starting:
        reserve=2 if fatal else 16
        need(not current and total+reserve<=a['max_guests'] and spent+reserve*45<=a['max_seconds'],'AQ fresh matrix reservation')
    return total,spent


def admit_runtime(image,fatal):
    f=source_binding();prior_gates(f,12 if fatal else 11)
    need(image.resolve()==IMAGE.resolve(),'AQ runtime image path')
    build=read(ROOT/f['directory']/'gate-11.json')
    need(build['artifacts'][IMAGE.relative_to(ROOT).as_posix()]==digest(IMAGE),'AQ retained build image')
    return f


def producer_binding(before,after):
    source=after
    source=once(source,',service_cpu=False,service_pio=False):',',service_cpu=False):')
    source=once(source,"    if type(service_pio) is not bool:raise ValueError('service PIO selector')\n",'')
    source=once(source,"    if service_pio and (not pool_pio or service_cpu):raise ValueError('service PIO requires pool PIO and excludes service CPU')\n",'')
    source=once(source,"    if service_pio:cc=[*cc,'-DREIST_NATIVE_SERVICE_CPU=1','-DREIST_NATIVE_SERVICE_PIO=1']\n",'')
    source=once(source,"    p.add_argument('--service-pio',action='store_true')\n",'')
    source=once(source,',a.service_cpu,a.service_pio)',',a.service_cpu)')
    need(source==before,'AQ producer exact old paths')


def entrypoint_binding(before_make,after_make,before_ps,after_ps):
    after_make=once(after_make,' $(if $(filter 1,$(X86_64_NATIVE_SERVICE_PIO)),-DREIST_NATIVE_CPU_TRACE=1,)','')
    start=after_make.index('X86_64_NATIVE_SERVICE_PIO ?= 0\n')
    end=after_make.index('ifneq ($(words $(X86_64_NATIVE_SERVICE_CPU)),1)',start)
    block=after_make[start:end]
    need(block.count('NativeServicePIO')==3 and block.count('ifeq (')==1 and block.count('ifneq (')==3,'AQ exact bounded Make selection block')
    source=after_make[:start]+after_make[end:]
    source=once(source,'$(filter 1,$(X86_64_NATIVE_SERVICE_CPU) $(X86_64_NATIVE_SERVICE_PIO))','$(filter 1,$(X86_64_NATIVE_SERVICE_CPU))')
    source=once(source,' $(if $(filter 1,$(X86_64_NATIVE_SERVICE_PIO)),--service-pio,)','')
    need(source==before_make,'AQ old Make paths exact')
    source=once(after_ps,'    [switch]$NativeServicePIO,\n','')
    source=once(source,"if ($NativeServicePIO) {\n    if ($NativeServiceCPU) { throw 'NativeServicePIO is distinct from device-free NativeServiceCPU.' }\n    $NativePoolPIO = [switch]$true\n}\n",'')
    source=once(source,'        "X86_64_NATIVE_SERVICE_PIO=$([int]$NativeServicePIO.IsPresent)" `\n','')
    need(source==before_ps,'AQ old PowerShell paths exact')


def references():
    f=source_binding();gates=prior_gates(f,9);a=admission();ap=read(ROOT/a['prior_acceptance']['path'])
    need(ap['accepted'] and ap['implementation_commit']=='9011ef1e8176ae6b202911edc31e8d9e1bb9aecc','AQ accepted AP baseline')
    def original(name):
        ref=a['snapshots'][name];need(ref==link(ROOT/ref['path']),'AQ original source snapshot');return (ROOT/ref['path']).read_text()
    producer_binding(original('scripts/build_x86_64_boot_programs.py'),(ROOT/'scripts/build_x86_64_boot_programs.py').read_text())
    entrypoint_binding(original('Makefile'),(ROOT/'Makefile').read_text(),original('scripts/build-x86_64-bootstrap.ps1'),(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text())
    from build_user_program import find_zig
    folder=BASE/('reference-preprocess-'+uuid.uuid4().hex);folder.mkdir();outputs={}
    name='arch/x86_64/user/pool_pio.c';old=ROOT/a['snapshots'][name]['path']
    environment=os.environ.copy();environment['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');environment['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
    for n in range(4):
        values=[]
        for label,path in (('before',old),('after',ROOT/name)):
            command=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-E','-P','-x','c',
                '-Iuserspace/sdk/include','-Iarch/x86_64/user','-DREIST_NATIVE_POOL_PIO=1','-DPROGRAM_ID='+str(n),str(path)]
            result=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/f'{label}-{n}.stderr').write_bytes(result.stderr);need(result.returncode==0,'AQ actual preprocessing '+result.stderr.decode(errors='replace')[-1500:])
            out=folder/f'{label}-{n}.i';out.write_bytes(result.stdout);outputs[out.relative_to(ROOT).as_posix()]=digest(out);values.append(result.stdout)
        need(values[0]==values[1],'AQ byte-exact original PoolPIO branch '+str(n))
    builds=[];artifacts={}
    for index in (16,17,18,19):
        ref=ap['gate_receipts'][index-1];need(ref==link(ROOT/ref['path']),'AQ original gate receipt');row=read(ROOT/ref['path'])
        need(row['passed'] and row['exit_code']==0 and row['candidate']==ap['candidate'] and row['execution']=='reuse','AQ successful original build')
        origin=row['reuse'];need(origin['receipt']==link(ROOT/origin['receipt']['path']) and origin['frozen']==link(ROOT/origin['frozen']['path']),'AQ original build provenance')
        verify_files({row['log']['path']:row['log']['sha256']});verify_files(row['artifacts']);artifacts.update(row['artifacts']);builds.append(ref)
    outputs.update(trace_reference_preprocessing(a,ap,folder))
    return dict(passed=True,kind='references',candidate=f['candidate'],gates=gates,builds=builds,
        preprocessing=outputs,artifacts=artifacts,source_inputs=f['source_inputs'],new_builds=0,new_guests=0)


def trace_reference_preprocessing(a,ap,folder):
    """No reference build: assemble-input equality with tracing disabled."""
    nasm=next(name for name in a['tools_sha256'] if Path(name).name.lower()=='nasm.exe')
    need(digest(Path(nasm))==a['tools_sha256'][nasm],'AQ bound assembler')
    before=ROOT/a['trace_originals']['arch/x86_64/proc/cooperative_scheduler.asm']['path']
    outputs={}
    for index,kind in ((16,'pool'),(17,'pio'),(18,'file'),(19,'cpu')):
        row=read(ROOT/ap['gate_receipts'][index-1]['path'])
        layouts=[name for name in row['artifacts'] if name.endswith('/bootstrap_core_layout.inc')]
        need(len(layouts)==1,'AQ exact reference layout')
        flags=['-DREIST_NATIVE_RUNTIME=1','-DREIST_NATIVE_PROGRAMS=1','-DREIST_NATIVE_LIFECYCLE=1',
            '-DREIST_NATIVE_WIDE=1','-DX86_64_NATIVE_RAM=1','-DC_CORE_LAYOUT_PATH="'+layouts[0]+'"']
        if kind!='file':flags+=['-DREIST_NATIVE_TASK_POOL=1']
        if kind in ('pio','file'):flags+=['-DREIST_NATIVE_PIO=1','-DREIST_NATIVE_PIO_TRACE=1']
        if kind=='pio':flags+=['-DREIST_NATIVE_POOL_PIO=1']
        if kind=='cpu':flags+=['-DREIST_NATIVE_SERVICE_CPU=1']
        normalized=[]
        for label,path in (('before',before),('after',ROOT/'arch/x86_64/proc/cooperative_scheduler.asm')):
            command=[nasm,'-E','-f','elf32',*flags,str(path)]
            result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            log=folder/f'trace-{kind}-{label}.stderr';log.write_bytes(result.stderr)
            need(result.returncode==0,'AQ reference NASM '+result.stderr.decode(errors='replace')[-2000:])
            out=folder/f'trace-{kind}-{label}.asm';out.write_bytes(result.stdout)
            normalized.append(b'\n'.join(line for line in result.stdout.splitlines() if not line.startswith(b'%line ')))
            receipt=folder/f'trace-{kind}-{label}.json'
            receipt.write_text(json.dumps(dict(command=command,exit_code=result.returncode,source=link(path),log=link(log),output=link(out))))
            for item in (log,out,receipt):outputs[item.relative_to(ROOT).as_posix()]=digest(item)
        need(normalized[0]==normalized[1],'AQ byte-exact reference NASM tokens '+kind)
    return outputs


def review():
    import run_qemu_x86_64_service_pio as runtime
    f=source_binding();gates=prior_gates(f,14);admit_runtime(IMAGE,True)
    config=runtime.owner.image_config(IMAGE);count=runtime.owner.wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
    matrices=[];evidence={};elapsed=0
    for fatal,name in ((False,'guests'),(True,'fatal-guests')):
        found=[p for p in (BASE/name).glob('attempt-*/summary.json') if read(p)['candidate']==f['candidate']]
        need(len(found)==1,'AQ complete unique matrix');path=found[0];row=read(path)
        need(row['passed'] and row['closed'] and row['fatal']==fatal and row['image_sha256']==digest(IMAGE),'AQ successful bound matrix')
        expected=[(x,4096) for x in runtime.FATAL_CASES] if fatal else list(runtime.CASES)
        need([(x['case'],x['ram']) for x in row['cases']]==expected and (row['allocations'],row['child_sha256'])==(count,sha),'AQ all cases and actual ELF')
        matrices.append(link(path));elapsed+=row['guest_elapsed']
        for entry in row['cases']:
            need(entry['passed'] and 0<entry['elapsed']<=45,'AQ guest bound')
            folder=path.parent/f'guest-{entry["case"]}-{entry["ram"]}';runtime.pio.safe_folder(folder)
            serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
            need((folder/'frame-trace.log').stat().st_size<=65536,'AQ bounded trace')
            tasks=runtime.validate_fatal(serial,trace,entry['case'],folder) if fatal else len(runtime.validate_capture(serial,trace,entry['case'],entry['oom'],count,sha,folder))
            need(tasks==entry['tasks'],'AQ exact task record')
            metrics=read(folder/'capture-metrics.json')
            need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','AQ process cleanup')
            if not fatal:
                runtime.native_cpu_trace.validate_capture(folder,trace,runtime.cpu)
                reads=runtime.cpu.binary_capacity(folder)
                need([x['equivalence'] for x in reads if x['equivalence'] is not None]==['kernel','high'],'AQ independent RAM equivalence')
                for index,item in enumerate(reads,1):
                    dump=folder/'binary-memory'/item['file']
                    need(item['sequence']==index and dump.name==f'ram-{index:04d}.bin' and dump.stat().st_size==item['bytes'] and digest(dump)==item['sha256'],'AQ all raw RAM')
            if entry['case']!=12:
                for phase in ('before','after'):
                    media=read(folder/('media-'+phase+'.json'))
                    need(media['passed'] and media['phase']==phase and media['overlay_allocated_data']==0 and media['logical_bytes']==65536 and
                         media['base_sha256']==hashlib.sha256(runtime.pio.BLOCK_DISK).hexdigest(),'AQ unchanged read-only media')
                need((folder/'generated.raw').read_bytes()==runtime.pio.BLOCK_DISK,'AQ immutable media bytes')
            else:need(not any(folder.glob('*.qcow2')) and not (folder/'generated.raw').exists(),'AQ absent media')
            for file in folder.rglob('*'):
                if file.is_file():need(not file.is_symlink(),'AQ evidence symlink');evidence[file.relative_to(ROOT).as_posix()]=digest(file)
    total,spent=matrix_budget(f['candidate'],True)
    return dict(passed=True,kind='review',candidate=f['candidate'],gates=gates,matrices=matrices,evidence_sha256=evidence,
        cases=18,guest_elapsed=elapsed,total_guest_attempts=total,total_guest_elapsed=spent,new_builds=0,new_guests=0)


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--references',action='store_true');group.add_argument('--review',action='store_true');args=parser.parse_args()
    kind='references' if args.references else 'review';started=time.monotonic();row=dict(passed=False,kind=kind)
    path=BASE/(kind+'-'+uuid.uuid4().hex+'.json')
    try:
        row=references() if args.references else review();print('SERVICE_PIO_'+kind.upper()+'_OK',flush=True);return 0
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        row['error']=str(error);print('SERVICE_PIO_'+kind.upper()+'_FAIL',str(error),flush=True);return 1
    finally:
        row['elapsed']=round(time.monotonic()-started,6)
        with path.open('x') as out:json.dump(row,out,indent=2)
        print('SERVICE_PIO_RECEIPT',path,flush=True)


if __name__=='__main__':raise SystemExit(main())
