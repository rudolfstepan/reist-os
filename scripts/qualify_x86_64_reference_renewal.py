"""Explicit R8.3am i386 reference renewal; never learns or changes guard pins.

The existing qualifier owns platform oracles, signed-content admission, guest
isolation and cleanup. This fixed adapter adds source and ordered-gate binding.
It does not alter the historical qualifier or run an agent/orchestrator.
"""
from contextlib import contextmanager
import hashlib,json,os,stat,sys
from pathlib import Path
import qualify_x86_64_reference_artifacts as legacy

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'build/codex-agent/r83am-file-launch/reference-metadata'
EXPECTED={
    'build/reist-os.img':'2b58094b7bc68eb261f18ab0cf053b4815f8528bc6e33ed6ca68e73232353bc7',
    'build/vmware/reist-os/reist-os-flat.vmdk':'9f2998be4acc1ed6a8b7ab3051746fd14de1de06851575871422a0ad996309f5',
    'build/codex-agent/r345-js-colors/framebuffer/reist-os.img':'ac4b127e871c6aa46d36c92cd4929bf9225a25ddbcf571c8b91b2ad232984f42',
}
PROGRAM_DIGEST='7ba8d99a96ce6e242d9c07ed50907df5ceb8356b6c3387780dd1bb9db1997de5'
PROFILE=dict(EXPECTED=EXPECTED,PROGRAM_DIGEST=PROGRAM_DIGEST,EVIDENCE=EVIDENCE,
             REBUILD=EVIDENCE/'vmware',QEMU_REBUILD=EVIDENCE/'qemu')
BUILD_CACHE=ROOT/'build/codex-agent/r83am-file-launch/reference-metadata'
# These seven files are not read by either recorded build command (no RunTests).
# Keep all other inputs, notably test/fixtures signing keys, in the build key.
BUILD_NON_INPUTS=frozenset(('automation/reist-s03b.toml','docs/architecture/NATIVE_FILE_LAUNCH_CONTRACT.md',
    'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md',
    'docs/architecture/X86_64_BOOTSTRAP.md','scripts/qualify_x86_64_reference_renewal.py',
    'test/test_x86_64_reference_renewal.py'))
BUILD_CACHE_PINS={
    'frozen-gates.json':'91987fc568d5e9c1fec245168e8edd0f24941e55dfb150c94df8a1b7c1bebca0',
    'qualification-prefix-result.json':'e90b1456817e817e22e3e16c99832560f3b5e2ce3cf530b58211cf5c734ede1d',
    'reference-qualification-f78c492a4778439abf17467ac429e54d/summary.json':'d91fad02f7211f205c5ac74d1ed8b7ddb1fa7da9141a075b32ec545a103e3b55',
}
need=legacy.need
MAX_SOURCE_BYTES=legacy.guard.MAX_FILE_BYTES

def read_json(path):
    need(path.is_file() and path.stat().st_size<=1048576,'JSON capacity/type')
    def unique(pairs):
        result={}
        for key,value in pairs:
            need(key not in result,'duplicate JSON field');result[key]=value
        return result
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique)

def write_json(path,value):
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,indent=2);out.write('\n')

def source_digest(path):
    """SHA256 includes empty sources; artifact nonempty admission is separate."""
    before=path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and
         0<=before.st_size<=MAX_SOURCE_BYTES,'invalid source size/type/link')
    def identity(info):
        return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,
                info.st_size,info.st_mtime_ns,info.st_ctime_ns,
                getattr(info,'st_birthtime_ns',None))
    def shared_identity(info):
        # Windows path and handle APIs project ctime and executable mode bits
        # differently. Preserve both full views, but bridge their common fields.
        return (info.st_dev,info.st_ino,stat.S_IFMT(info.st_mode),info.st_nlink,
                info.st_size,info.st_mtime_ns,getattr(info,'st_birthtime_ns',None))
    expected=identity(before);result=hashlib.sha256();remaining=before.st_size
    with path.open('rb') as incoming:
        opened=os.fstat(incoming.fileno());opened_expected=identity(opened)
        need(shared_identity(opened)==shared_identity(before),'source changed before read')
        for _ in range((before.st_size+1048575)//1048576):
            wanted=min(1048576,remaining);chunk=incoming.read(wanted)
            need(len(chunk)==wanted,'source shortened while reading')
            result.update(chunk);remaining-=wanted
        need(remaining==0 and not incoming.read(1),'source grew while reading')
        need(identity(os.fstat(incoming.fileno()))==opened_expected,'source changed while reading')
    need(identity(path.lstat())==expected,'source changed after read')
    return result.hexdigest()


def check_hashes(root,entries,*,artifacts=False):
    need(type(artifacts) is bool,'inventory kind')
    need(isinstance(entries,dict) and 0<len(entries)<=20000,'source inventory capacity')
    for name,sha in entries.items():
        need(isinstance(name,str) and '\\' not in name and not Path(name).is_absolute() and '..' not in Path(name).parts,'source path')
        need(isinstance(sha,str) and len(sha)==64 and all(c in '0123456789abcdef' for c in sha),'source digest')
        path=root/name
        need(path.resolve().is_relative_to(root.resolve()),'source path escape')
        for parent in (path,*path.parents):
            if parent==root:break
            need(not parent.is_symlink() and not parent.is_junction(),'source path alias')
        need((legacy.guard.digest(path) if artifacts else source_digest(path))==sha,'source drift: '+name)

def admit_cached_builds(root,folder,frozen,result,summary):
    """Verify retained build evidence, without a subprocess or runtime verdict."""
    need(folder.resolve().is_relative_to(root.resolve()),'build cache scope')
    need(len(frozen['gates'])==17 and 12<=len(result['gates'])<=17,'build receipt count')
    inputs=frozen['source_inputs']
    need(isinstance(inputs,dict) and 0<len(inputs)<=20000,'build input capacity')
    check_hashes(root,{name:sha for name,sha in inputs.items() if name not in BUILD_NON_INPUTS})
    check_hashes(root,frozen['original_artifacts'],artifacts=True)
    tools=frozen['tools_sha256']
    need(isinstance(tools,dict) and 0<len(tools)<=64,'build tool capacity')
    for name,sha in tools.items():
        need(Path(name).is_absolute() and legacy.guard.digest(Path(name))==sha,'build tool drift')
    programs=summary['programs'];before=summary['before'];records=[]
    need(isinstance(programs,dict) and len(programs)==96 and isinstance(before,dict) and len(before)<=20000,'build artifact inventory')
    need(all(isinstance(n,str) and Path(n).name==n and '\\' not in n and n.endswith('.PRG') for n in programs),'build program path')
    for index,target in ((11,'vmware'),(12,'qemu')):
        prefix=(folder/target).relative_to(root).as_posix()
        expected=dict(id=index,name='build-'+target,timeout=900,argv=[
            'C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-File','scripts/build-windows.ps1',
            '-Target',target,'-Video','vga','-OutputDirectory',prefix])
        gate=frozen['gates'][index-1];row=result['gates'][index-1]
        need(gate==expected and all(row.get(k)==v for k,v in expected.items()),'build receipt identity/profile')
        need(row['result']=='PASS' and row['exit_code']==0 and 0<row['elapsed_seconds']<900,'failed build receipt')
        log=(folder/f'gate-{index:02d}.log').relative_to(root).as_posix()
        need(row['log']==log,'build log path')
        check_hashes(root,{log:row['log_sha256']},artifacts=True)
        names={prefix+'/'+n for n in ('kernel.bin','kernel.bin.sig','reist-os.img','reist-sbom.spdx.json','.windows-build-config.json')}
        names.update(prefix+'/programs/'+name for name in programs)
        artifacts={name:sha for name,sha in before.items() if name.startswith(prefix+'/')}
        need(set(artifacts)==names and len(artifacts)==101,'incomplete build artifacts')
        check_hashes(root,artifacts,artifacts=True)
        config=read_json(folder/target/'.windows-build-config.json')
        need(config['target']==target and config['video']=='vga' and config['output_directory']==prefix,'build configuration profile')
        records.append(dict(target=target,status='REUSED',runtime_accepted=False,artifact_count=len(artifacts),
                            original_build_seconds=row['elapsed_seconds'],receipt=row))
    return records

def check_builds():
    """Fixed reviewed cache only; a miss rejects rather than rebuilding."""
    prefix=BUILD_CACHE.relative_to(ROOT).as_posix()
    pins={prefix+'/'+name:sha for name,sha in BUILD_CACHE_PINS.items()}
    check_hashes(ROOT,pins,artifacts=True)
    frozen,result,summary=(read_json(BUILD_CACHE/name) for name in BUILD_CACHE_PINS)
    need(frozen['head'].startswith('9cb39d62') and frozen['package']=='R8.3am-x86_64-file-launch','cached build authority')
    need(len(frozen['source_inputs'])==1516 and result['frozen_sha256']==BUILD_CACHE_PINS['frozen-gates.json'],'cached build binding')
    records=admit_cached_builds(ROOT,BUILD_CACHE,frozen,result,summary)
    check_hashes(ROOT,pins,artifacts=True)
    print('REFERENCE_BUILDS_REUSED '+json.dumps(dict(builds=0,guests=0,runtime_accepted=False,records=records,
        avoided_build_seconds=round(sum(r['original_build_seconds'] for r in records),3))))
    return 0

def admit_receipts(folder,frozen,count):
    need(count in (12,15),'admission phase')
    need(len(frozen['gates'])==17,'frozen gate count');records=[]
    for index,gate in enumerate(frozen['gates'][:count],1):
        row=read_json(folder/f'gate-{index:02d}.result.json')
        need(gate['id']==index and all(row.get(k)==v for k,v in gate.items()),'gate receipt identity')
        need(row['result']=='PASS' and row['exit_code']==0 and 0<row['elapsed_seconds']<gate['timeout'],'failed gate')
        log=ROOT/row['log'];need(log.resolve().is_relative_to(folder.resolve()),'gate log escape')
        need(legacy.guard.digest(log)==row['log_sha256'],'gate log drift');records.append(row)
    return records

def admission(count):
    frozen=read_json(EVIDENCE/'frozen-gates.json')
    need(frozen['package']=='R8.3am-x86_64-file-launch' and frozen['head'].startswith('9cb39d62'),'qualification authority')
    check_hashes(ROOT,frozen['source_inputs'])
    check_hashes(ROOT,frozen['original_artifacts'],artifacts=True)
    need(legacy.guard.inventory_digest(legacy.guard.program_inventory(ROOT/'build/programs'))==PROGRAM_DIGEST,'reviewed programs changed')
    return frozen,admit_receipts(EVIDENCE,frozen,count)

@contextmanager
def reviewed_profile():
    saved={name:getattr(legacy,name) for name in PROFILE}
    try:
        for name,value in PROFILE.items():setattr(legacy,name,value)
        yield
    finally:
        for name,value in saved.items():setattr(legacy,name,value)

def qualify():
    frozen,_=admission(12)
    need(not any(EVIDENCE.glob('reference-qualification-*')),'reference attempt already used')
    try:
        with reviewed_profile():code=legacy.main()
    finally:
        check_hashes(ROOT,frozen['source_inputs']);check_hashes(ROOT,frozen['original_artifacts'],artifacts=True)
    summaries=list(EVIDENCE.glob('reference-qualification-*/summary.json'))
    need(len(summaries)==1,'exact reference summary')
    summary=read_json(summaries[0])
    write_json(EVIDENCE/'reference-summary.json',dict(passed=code==0 and summary['passed'],
        original=summaries[0].relative_to(ROOT).as_posix(),sha256=legacy.guard.digest(summaries[0])))
    return code

def review():
    frozen,records=admission(15)
    reference=read_json(EVIDENCE/'reference-summary.json')
    need(reference['passed'] and legacy.guard.digest(ROOT/reference['original'])==reference['sha256'],'reference qualification failed')
    original=read_json(ROOT/reference['original'])
    need(len(original['guests'])==4 and all(g['passed'] for g in original['guests']),'reference guest matrix incomplete')
    result=legacy.guard.verify(ROOT,EXPECTED,96,PROGRAM_DIGEST)
    write_json(EVIDENCE/'reviewed-admission.json',dict(passed=True,reference_only=True,package_accepted=False,
        authority_commit=frozen['head'],frozen_sha256=legacy.guard.digest(EVIDENCE/'frozen-gates.json'),
        reference=reference,records=records,images=EXPECTED,program_digest=PROGRAM_DIGEST,artifacts=result,
        source_inputs=frozen['source_inputs']))
    print('REFERENCE_RENEWAL_REVIEWED gates=15 guests=6 pins_unchanged=true')
    return 0

if __name__=='__main__':
    try:
        if sys.argv[1:]==[]:raise SystemExit(qualify())
        if sys.argv[1:]==['--check-reviewed']:raise SystemExit(review())
        if sys.argv[1:]==['--check-builds']:raise SystemExit(check_builds())
        raise ValueError('unsupported reference renewal command')
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('REFERENCE_RENEWAL FAIL: '+str(error));raise SystemExit(1)
