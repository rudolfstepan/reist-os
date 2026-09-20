"""Frozen AZ transaction, exact accepted dependencies, no kernel build."""
from pathlib import Path
import argparse,binascii,hashlib,inspect,json,re,shlex,shutil,struct,subprocess,time,tomllib
import check_x86_64_shell_media as check
import build_x86_64_shell_media as producer
import run_qemu_x86_64_shell_boot_media as guest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83az-shell-boot-media/candidate10'
PREVIOUS=BASE.parent/'candidate09'
NEGATIVE_ORIGIN=BASE.parent/'candidate09'
POSITIVE_ORIGIN=BASE.parent/'candidate07'
MEDIA_ORIGIN=BASE.parent/'candidate02'
MEDIA=MEDIA_ORIGIN/'media'
HEAD='bd02f5f6e535e53299ce76307de6702fb78bd88a'
PRIOR=ROOT/'build/codex-agent/r83ay-shell-session/candidate17/verification-status-shell-session-final.json'
PRIOR_SHA='058147106d58a0ced94d32dc54000efba177f53aeb39a62044cc80f7d9c577a3'
IMAGE=ROOT/'build/codex-agent/r83ay-shell-session/native-read-tickets/x86_64/reist-x86_64-bootstrap.elf'
LIMITS=(300,180,180,300,600,180,180,180)
DOCS={'automation/reist-s03b.toml','docs/architecture/NATIVE_SHELL_BOOT_MEDIA_CONTRACT.md',
      'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
need=check.need


def digest(path):
    sha=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while raw:=stream.read(65536):sha.update(raw)
    return sha.hexdigest()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,sort_keys=True,indent=2)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=30).strip()
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def changed():return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
def queue():return tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))


def make_projection():
    current=(ROOT/'Makefile').read_text(encoding='utf-8')
    projected,n=re.subn(r'# AZ packaging only:.*?# End AZ packaging-only target\.\n\n','',current,flags=re.S)
    need(n==1,'one packaging-only Make block');return projected


def positive_source_projection(source,old):
    source=guest.ay.once(source,inspect.getsource(guest.live_serial)+'\n\n','')
    source=guest.ay.once(source,"raw=live_serial(folder/'guest.log')","raw=check.bounded(folder/'guest.log',262144)")
    source=guest.ay.once(source,'def run_matrix(image,package,folder,binding,cases=CASES):','def run_matrix(image,package,folder,binding):')
    source=guest.ay.once(source,'for name,layout,case,session,ram in cases:','for name,layout,case,session,ram in CASES:')
    need(source==old,'exact entire positive runtime source projection')


def positive_reuse_projection():
    source=(ROOT/'scripts/run_qemu_x86_64_shell_boot_media.py').read_text(encoding='utf-8')
    source=guest.ay.once(source,inspect.getsource(guest.negative_budget)+'\n\n','')
    for new,old in (
        ('def negative(folder,medium,fixture,started,case):','def negative(folder,medium,fixture,started):'),
        ('started+negative_budget(medium.layout,case)-3','started+17'),
        ('if session is not None else negative_budget(layout,case)','if session is not None else 20'),
        ('ay.bounded_fixture(out,2,app,started-(45-limit))','ay.bounded_fixture(out,2,app,started-25)'),
        ('negative(out,medium,fixture,started,case)','negative(out,medium,fixture,started)'),
        ("result['guest_seconds']<=455","result['guest_seconds']<=435")):
        source=guest.ay.once(source,new,old)
    positive_source_projection(source,(POSITIVE_ORIGIN/'failed-source/run_qemu_x86_64_shell_boot_media.py').read_text(encoding='utf-8'))


def negative_source_projection(source,old):
    source=guest.ay.once(source,"return 30 if layout=='hdd' and case in ('signatures','digest') else 20",
        "return 30 if (layout,case)==('hdd','signatures') else 20")
    source=guest.ay.once(source,"result['guest_seconds']<=455","result['guest_seconds']<=445")
    need(source==old,'exact original signature-case runtime source')


def negative_reuse_projection():
    negative_source_projection((ROOT/'scripts/run_qemu_x86_64_shell_boot_media.py').read_text(encoding='utf-8'),
        (NEGATIVE_ORIGIN/'failed-source/run_qemu_x86_64_shell_boot_media.py').read_text(encoding='utf-8'))


def evidence_origin(spec):
    return POSITIVE_ORIGIN if spec[3] is not None else NEGATIVE_ORIGIN if spec[0]=='hdd-signatures' else BASE


def dependencies():
    need(digest(PRIOR)==PRIOR_SHA,'exact accepted AY receipt');prior=read(PRIOR)
    need(prior['accepted'] and prior['clean_worktree'] and prior['implementation_commit']=='455fbb9df66bcac3c9b3a53b172757841f14cf38','accepted AY transaction')
    for name,sha in prior['tools'].items():need(digest(name)==sha,'unchanged tool '+name)
    for name,sha in prior['sources'].items():
        if name not in DOCS|{'Makefile'}:need(digest(ROOT/name)==sha,'unchanged accepted dependency '+name)
    old=subprocess.check_output(['git','show','455fbb9d:Makefile'],cwd=ROOT,timeout=30).decode().replace('\r\n','\n')
    need(make_projection()==old,'exact old Make/default projection')
    need(link(IMAGE)==prior['image'],'exact accepted kernel')
    for name in ('seal','commit_ready'):
        row=prior[name];need(digest(ROOT/row['path'])==row['sha256'],'prior acceptance link '+name)
    values=producer.inputs(IMAGE.parent)
    need(hashlib.sha256(values[check.KERNEL]).hexdigest()==prior['image']['sha256'],'actual input byte binding')
    return prior


def freeze():
    need(git('rev-parse','HEAD')==HEAD and not BASE.exists(),'fresh AZ transaction')
    q=queue();p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3az-shell-boot-media' and p['status']=='active','one active AZ package')
    edits=changed();need(set(edits)<=set(p['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'candidate scope/index/whitespace')
    names=set(git('ls-files').splitlines())|set(p['allowed_files'])
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    need(digest(PREVIOUS/'frozen.json')=='a735e85a01ac3f33c9c3aae43fc83ddbf118a7c58d01d04824760fe88f9c81f4' and
         digest(PREVIOUS/'stopped.json')=='5337876ce749fab834917f46ddd3aded61b398e77d93c5985f8b831ccf3d7ae1','retained exact negative deadline failure')
    previous=read(PREVIOUS/'frozen.json');stopped=read(PREVIOUS/'stopped.json')
    need(len(stopped['gates'])==5 and all(r['passed'] for r in stopped['gates'][:4]) and not stopped['gates'][4]['passed'] and
         len(stopped['runtime']['cases'])==2 and stopped['runtime']['guest_seconds']==45.61209659994347 and
         stopped['runtime']['cases'][0]['passed'] and stopped['runtime']['cases'][0]['name']=='hdd-signatures' and
         stopped['runtime']['error']=='BIOS rejection count','prior window exact negative deadline failure')
    corrections=DOCS|{'scripts/verify_x86_64_shell_boot_media.py','test/test_x86_64_shell_boot_media.py','scripts/run_qemu_x86_64_shell_boot_media.py'}
    need(set(sources)==set(previous['sources']) and
         {n for n in sources if sources[n]!=previous['sources'][n]}<=corrections,'approved composed-host-only correction scope')
    for name in corrections-DOCS:
        need(digest(PREVIOUS/'failed-source'/Path(name).name)==previous['sources'][name],'retained failed source '+name)
    need(all((ROOT/n).is_file() for n in p['allowed_files']),'complete scoped implementation')
    positive_reuse_projection();negative_reuse_projection()
    reused=[POSITIVE_ORIGIN/'runtime'/spec[0] for spec in guest.CASES if spec[3] is not None]
    reuse_evidence={str(path.relative_to(ROOT)):digest(path) for folder in reused for path in sorted(folder.rglob('*')) if path.is_file()}
    reuse_evidence[str((POSITIVE_ORIGIN/'runtime/summary.json').relative_to(ROOT))]=digest(POSITIVE_ORIGIN/'runtime/summary.json')
    need(reuse_evidence==previous['reuse_evidence'],'unchanged entire positive evidence inventory')
    for path in sorted((NEGATIVE_ORIGIN/'runtime/hdd-signatures').rglob('*')):
        if path.is_file():reuse_evidence[str(path.relative_to(ROOT))]=digest(path)
    reuse_evidence[str((NEGATIVE_ORIGIN/'runtime/summary.json').relative_to(ROOT))]=digest(NEGATIVE_ORIGIN/'runtime/summary.json')
    original=read(POSITIVE_ORIGIN/'frozen.json')
    need(digest(POSITIVE_ORIGIN/'failed-source/run_qemu_x86_64_shell_boot_media.py')==original['sources']['scripts/run_qemu_x86_64_shell_boot_media.py'],'original positive source bytes')
    prior=read(PRIOR);need(digest(PRIOR)==PRIOR_SHA,'accepted receipt pin before freeze')
    artifacts={str(path.relative_to(ROOT)):digest(path) for path in sorted(IMAGE.parent.rglob('*')) if path.is_file()}
    need(0<len(artifacts)<=1024,'bounded accepted input inventory')
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==len(LIMITS),'eight frozen gates')
    candidate=hashlib.sha256(json.dumps(dict(sources=sources,artifacts=artifacts,commands=commands),sort_keys=True).encode()).hexdigest()
    BASE.mkdir(parents=True)
    save(BASE/'frozen.json',dict(head=HEAD,package=p,sources=sources,artifacts=artifacts,tools=prior['tools'],commands=commands,
        limits=LIMITS,changed=edits,candidate=candidate,accepted_receipt=link(PRIOR),kernel_builds=0,media_builds=0,max_guests=4,max_guest_seconds=90,
        reused_guests=6,reuse_evidence=reuse_evidence,matrix_max_seconds=455,
        previous_stopped=link(PREVIOUS/'stopped.json'),reused_media=link(MEDIA_ORIGIN/'build-media.json'),
        spent_kernel_builds=0,spent_media_builds=1,spent_guests=18,spent_guest_seconds=562.2795722998272,
        prelaunch_attempts=1,prelaunch_seconds=2.088810800021747))
    print('AZ_FROZEN',candidate)


def binding():
    f=read(BASE/'frozen.json');need(git('rev-parse','HEAD')==f['head']==HEAD,'frozen HEAD')
    q=queue();need(q['active_id']==f['package']['id'] and q['packages'][0]==f['package'],'frozen package')
    for fields in ('sources','artifacts','tools','reuse_evidence'):
        for name,sha in f[fields].items():need(digest(ROOT/name)==sha,'changed '+fields+' '+name)
    need(link(PRIOR)==f['accepted_receipt'],'accepted evidence retained')
    need(set(changed())<=set(f['package']['allowed_files']),'frozen changed paths');return f


def runtime():
    f=binding();positive_reuse_projection();negative_reuse_projection()
    prior=read(POSITIVE_ORIGIN/'runtime/summary.json')['cases'][:5]
    need(len(prior)==5 and all(r['passed'] for r in prior),'five qualified prior positives')
    previous_negative=read(NEGATIVE_ORIGIN/'runtime/summary.json')['cases'][0]
    need(previous_negative['passed'] and previous_negative['name']=='hdd-signatures','qualified previous signature negative')
    fresh=guest.run_matrix(IMAGE,package_path(),BASE/'runtime',binding,cases=tuple(s for s in guest.CASES if evidence_origin(s)==BASE))
    need(fresh['passed'] and len(fresh['cases'])==4 and fresh['guest_seconds']<=90,'four fresh negatives')
    rows=[dict(r,evidence_directory=(POSITIVE_ORIGIN/'runtime'/r['name']).relative_to(ROOT).as_posix(),reused=True) for r in prior]
    rows.append(dict(previous_negative,evidence_directory=(NEGATIVE_ORIGIN/'runtime/hdd-signatures').relative_to(ROOT).as_posix(),reused=True))
    rows += [dict(r,evidence_directory=(BASE/'runtime'/r['name']).relative_to(ROOT).as_posix(),reused=False) for r in fresh['cases']]
    save(BASE/'matrix.json',dict(passed=True,closed=True,cases=rows,guest_seconds=sum(r['elapsed'] for r in rows),
        fresh_guests=4,reused_guests=6,physical_guest_seconds=fresh['guest_seconds'],frozen=link(BASE/'frozen.json')))


def package_path():
    row=read(BASE/'build-media.json');need(row['passed'],'media publication passed')
    directory=ROOT/row['directory'];need(directory==MEDIA,'exact published directory')
    need(link(directory/'shell-media.json')==row['index'],'published index unchanged')
    attempt=check.verify(directory)
    need(attempt.relative_to(ROOT).as_posix()==row['attempt'],'published attempt unchanged');return attempt


def build_media():
    f=binding();need(not (BASE/'build-media.json').exists(),'one bound media reuse gate')
    need(digest(MEDIA_ORIGIN/'build-media.json')=='802715919daa71fb37f93c34b0fe2a435a330c5320773f50bb94ecf543262fb6' and
         link(MEDIA_ORIGIN/'build-media.json')==f['reused_media'],'exact previously built pair')
    started=time.monotonic();old=read(MEDIA_ORIGIN/'build-media.json')
    need(old['passed'] and old['kernel_builds']==0 and old['media_builds']==1 and
         link(MEDIA/'shell-media.json')==old['index'] and old['index']['sha256']=='89c5114a4fd4eb7af8efa8c69e2865393697ef6f42a823e94fca6c3abf9fd6c8','media identity')
    attempt=check.verify(MEDIA)
    need(attempt.relative_to(ROOT).as_posix()==old['attempt'],'same verified media pair')
    save(BASE/'build-media.json',dict(old,elapsed=time.monotonic()-started,media_builds=0,reused_from=link(MEDIA_ORIGIN/'build-media.json')))


def package_hosts():
    binding();attempt=package_path();folder=BASE/'package-hosts';folder.mkdir()
    # One owned quarantine copy; accepted source inputs and published package
    # are never edited. Every mutation/restoration is logged below.
    target=folder/attempt.name;shutil.copytree(attempt,target)
    index=folder/'shell-media.json';shutil.copyfile(MEDIA/'shell-media.json',index)
    results=[];started=time.monotonic()
    try:
        for name in (*check.FILES,'package.json','package.json.sig'):
            path=target/name
            with path.open('r+b') as stream:
                byte=stream.read(1);stream.seek(0);stream.write(bytes([byte[0]^1]))
            try:
                try:check.verify(folder)
                except (ValueError,UnicodeError,json.JSONDecodeError) as error:results.append(dict(case=name,rejected=True,error=str(error)[:256]))
                else:raise ValueError('artifact corruption accepted '+name)
            finally:
                with path.open('r+b') as stream:stream.write(byte)
        original=index.read_bytes()
        for raw in (b'[]',b'{}',b' '*16385,b'{"package":{},"package":{},"signature":""}'):
            index.write_bytes(raw)
            try:
                try:check.verify(folder)
                except (ValueError,KeyError,TypeError) as error:results.append(dict(case='index',sha256=hashlib.sha256(raw).hexdigest(),rejected=True,error=str(error)[:256]))
                else:raise ValueError('invalid index accepted')
            finally:index.write_bytes(original)
        # Valid research signatures cannot turn a malformed filesystem into a
        # supported volume. Re-sign the quarantine descriptor after corruption.
        path=target/'system.ext2';original_data=path.read_bytes();package=read(index)['package']
        old_package=(target/'package.json').read_bytes();old_sig=(target/'package.json.sig').read_bytes()
        bad=bytearray(original_data);bad[5*1024+11*128+40]^=1;path.write_bytes(bad)
        try:
            package['artifacts']['system.ext2']=check.digest(path,131072)
            (target/'package.json').write_text(json.dumps(package,sort_keys=True,separators=(',',':'))+'\n',encoding='ascii')
            producer.old.sign(target/'package.json',target/'package.json.sig',shutil.which('openssl') or 'openssl',folder/'sign.log')
            index.write_text(json.dumps(dict(package=package,signature=(target/'package.json.sig').read_bytes().hex())),encoding='ascii')
            try:check.verify(folder)
            except ValueError as error:results.append(dict(case='valid-signature-invalid-ext2',rejected=True,error=str(error)))
            else:raise ValueError('malformed signed EXT2 accepted')
        finally:
            path.write_bytes(original_data);(target/'package.json').write_bytes(old_package)
            (target/'package.json.sig').write_bytes(old_sig);index.write_bytes(original)
        check.verify(folder);package_path()
        save(folder/'result.json',dict(passed=True,results=results,elapsed=time.monotonic()-started))
    except BaseException as error:
        save(folder/'stopped.json',dict(passed=False,results=results,error=str(error),elapsed=time.monotonic()-started));raise


def boot_base_proof(original,actual,layout,case):
    patches=[];base=2048 if layout=='hdd' else 1
    if case!='normal':
        with original.open('rb') as stream:
            for relative in ((0,) if layout=='floppy' or case=='a-signature' else (0,96)):
                at=(base+relative)*512;stream.seek(at);header=bytearray(stream.read(512))
                if case in ('signatures','a-signature'):header[80]^=1
                elif case=='manifest':struct.pack_into('<I',header,8,4)
                else:
                    lba,size=struct.unpack_from('<II',header,24)
                    need(4096<=size<=check.KERNEL_LIMIT and lba in (128,3136),'independent mutation bounds')
                    start=(base+lba)*512;stream.seek(start);kernel=bytearray(stream.read(size));need(len(kernel)==size,'mutation exact kernel')
                    kernel[size//2]^=1;patches.append((start+size//2,bytes([kernel[size//2]])))
                    struct.pack_into('<I',header,36,binascii.crc32(kernel)&0xffffffff)
                struct.pack_into('<I',header,44,0);struct.pack_into('<I',header,44,(-sum(struct.unpack('<128I',header)))&0xffffffff)
                patches.append((at,bytes(header)))
    need(original.stat().st_size==actual.stat().st_size,'independent boot extent')
    with original.open('rb') as source,actual.open('rb') as target:
        cursor=0
        while raw:=source.read(65536):
            expected=bytearray(raw)
            for at,data in patches:
                left=max(cursor,at);right=min(cursor+len(raw),at+len(data))
                if left<right:expected[left-cursor:right-cursor]=data[left-at:right-at]
            need(target.read(len(raw))==expected,'only exact declared boot fault bytes');cursor+=len(raw)
        need(not target.read(1),'boot extent growth')


def review():
    binding();positive_reuse_projection();negative_reuse_projection();attempt=package_path();summary=read(BASE/'matrix.json')
    need(summary['passed'] and summary['closed'] and len(summary['cases'])==10 and summary['guest_seconds']<=455,'complete bound runtime matrix')
    config,records,app=guest.ay.image_config(IMAGE);catalog=(IMAGE.parent/'boot-programs.bin').read_bytes();proofs=[]
    for row,spec in zip(summary['cases'],guest.CASES):
        name,layout,case,session,ram=spec;origin=evidence_origin(spec);out=origin/'runtime'/name
        need(row['evidence_directory']==out.relative_to(ROOT).as_posix() and row['reused']==(origin!=BASE),'exact evidence origin')
        limit=(75 if case=='a-signature' else 65) if session is not None else (30 if layout=='hdd' and case in ('signatures','digest') else 20)
        need(row['passed'] and (row['name'],row['layout'],row['case'],row['session'],row['ram'])==spec and row['elapsed']<=limit,'exact guest receipt')
        command=read(out/'command.json');need('-kernel' not in command and 'ide-hd,drive=pio-layer,bus=ide.0,unit=0' in command,'BIOS-only launch and original data device')
        expected=guest.boot_arguments(out/'boot-medium/disposable.qcow2',layout)
        need(command[-len(expected):]==expected,'exact separate boot device')
        medium=out/'boot-medium';boot_base_proof(attempt/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img'),medium/'base.raw',layout,case)
        commands=read(medium/'commands.json');need(len(commands)==7 and all(r['returncode']==0 for r in commands),'all boot media commands')
        for phase,at in (('before',1),('after',4)):
            receipt=read(medium/(phase+'.json'));extents=json.loads(commands[at+1]['stdout'])
            need(receipt['passed'] and receipt['overlay_allocated_data']==0 and receipt['base']==check.digest(medium/'base.raw',536870912),'immutable boot receipt')
            need([r['args'][0] for r in commands[at:at+3]]==['info','map','compare'] and receipt['extents']==extents,'boot raw tool sequence')
            end=0
            for extent in extents:need(extent['start']==end and extent['length']>0 and extent['depth']==1,'boot unchanged extent');end+=extent['length']
            need(end==receipt['base']['size'],'boot complete extent replay')
        serial=check.bounded(out/'guest.log',262144).decode('ascii',errors='replace');guest.validate_bios(serial,layout,case)
        proof=guest.ay.evaluate(out,config,records,catalog,session,2,app) if session is not None else {}
        if session is not None:
            need(proof==row['proof'],'independent complete AY proof replay')
            entry=read(out/'bios-entry.json');metrics=read(out/'capture-metrics.json')
            stop=read(out/'bios-stop.json')
            need(entry['stop_sha256']==digest(out/'bios-stop.json') and stop['version']==1 and
                 all(stop[k]==entry[k] for k in ('entry','hits','registers','elapsed','guest_started')),'actual held stop acknowledgment binding')
            guest.entry_phase(entry,entry['guest_started'],entry['runtime_started'],case)
            need(entry==metrics['bios_phase'] and entry['entry']==guest.physical_entry(IMAGE,config) and
                 row['bios_seconds']==entry['runtime_started']-entry['guest_started'] and
                 0<=metrics['observe_seconds']<=42 and
                 0<=row['elapsed']-row['bios_seconds']-metrics['observe_seconds']<=3,'independent composed phase/cleanup proof')
        else:
            need(check.bounded(out/'generated.raw',131072)==check.bounded(attempt/'system.ext2',131072),'negative actual data bytes')
            data_commands=read(out/'media-commands.json')
            need(len(data_commands)==7 and all(r['returncode']==0 for r in data_commands),'negative data command count/results')
            for phase,at in (('before',1),('after',4)):
                data=read(out/('media-'+phase+'.json'));extents=json.loads(data_commands[at+1]['stdout'])
                need(data['passed'] and data['overlay_allocated_data']==0 and data['logical_bytes']==131072 and
                     data['base_sha256']==digest(out/'generated.raw') and data['extents']==extents,'negative data no-write proof')
                need([r['args'][0] for r in data_commands[at:at+3]]==['info','map','compare'],'negative data tool sequence')
                end=0
                for extent in extents:need(extent['start']==end and extent['length']>0 and extent['depth']==1,'negative data unchanged map');end+=extent['length']
                need(end==131072,'negative data complete mapping')
        proofs.append(dict(name=name,proof=proof))
    save(BASE/'review.json',dict(passed=True,proofs=proofs,summary=link(BASE/'matrix.json')))


def scope():
    f=binding();dependencies();need(not git('diff','--check') and not git('diff','--cached','--name-only'),'scope whitespace/index')
    need(read(BASE/'review.json')['passed'],'full raw review precedes scope')
    save(BASE/'scope.json',dict(passed=True,changed=changed(),candidate=f['candidate']))


def gates():
    f=binding();need(not (BASE/'running.json').exists(),'gate window not replayed')
    save(BASE/'running.json',dict(candidate=f['candidate'],commands=f['commands']))
    results=[]
    for n,(command,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();started=time.monotonic();log=BASE/f'gate-{n:02d}.log';exitcode=-1
        try:
            with log.open('xb') as stream:
                child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=limit,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));exitcode=child.returncode
        except subprocess.TimeoutExpired:exitcode=124
        row=dict(candidate=f['candidate'],command=command,limit=limit,elapsed=time.monotonic()-started,exit_code=exitcode,passed=exitcode==0,log=link(log))
        save(BASE/f'gate-{n:02d}.json',row);results.append(row);print('AZ_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:
            save(BASE/'stopped.json',dict(passed=False,gates=results,runtime=read(BASE/'runtime/summary.json') if (BASE/'runtime/summary.json').exists() else None))
            raise ValueError('first gate failure '+str(n))
    save(BASE/'qualified.json',dict(passed=True,candidate=f['candidate'],gates=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    for option in ('freeze','gates','dependencies','build-media','package-hosts','runtime','review','scope'):group.add_argument('--'+option,action='store_true')
    args=parser.parse_args()
    try:
        if args.freeze:freeze()
        elif args.gates:gates()
        elif args.dependencies:binding();dependencies();print('AZ_DEPENDENCIES_OK')
        elif args.build_media:build_media()
        elif args.package_hosts:package_hosts()
        elif args.runtime:runtime()
        elif args.review:review()
        elif args.scope:scope()
    except BaseException as error:
        print('AZ_FAIL',str(error),flush=True);raise
