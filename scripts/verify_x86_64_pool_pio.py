"""Read-only frozen source, previous-profile and same-image PIO proof bindings."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files,binary_map
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83ao-pool-pio'
PACKAGE='R8.3ao-x86_64-pool-pio'
METADATA_FILES=('automation/reist-s03b.toml','docs/architecture/NATIVE_POOL_PIO_CONTRACT.md','docs/development/CURRENT_WORK.md',
                'scripts/verify_x86_64_pool_pio.py','test/test_x86_64_pool_pio.py')
RENEWAL=BASE/'debug-metadata-renewal'
RUNTIME=BASE/'runtime-correction'
PRODUCER='scripts/build_x86_64_boot_programs.py'
RUNTIME_FILES=(*METADATA_FILES,PRODUCER)


def producer_optimization_binding(old,new):
    before=b"'-Oz' if pio else '-O2'";after=b"'-Oz' if pio and not pool_pio else '-O2'"
    need(type(old) is bytes and type(new) is bytes and old.count(before)==1 and new.count(after)==1 and
         old.replace(before,after)==new,'PIO exact producer optimization adapter')


def runtime_package_original(package):
    if 'runtime_correction_authority' not in package:return package
    result=json.loads(json.dumps(package))
    for key in ('runtime_correction_authority','runtime_correction_files','runtime_correction_prefix'):result.pop(key)
    new='build/codex-agent/r83ao-pool-pio/runtime-correction/native';old='build/codex-agent/r83ao-pool-pio/native'
    for values,index in ((result['package_tests'],2),(result['runtime_tests'],1),(result['runtime_tests'],2)):
        need(values[index].count(new)==1,'PIO exact new image argument')
        values[index]=values[index].replace(new,old)
    return result


def runtime_source_binding(frozen):
    admission=read(RUNTIME/'admission.json');old=read(ROOT/admission['frozen']['path'])
    need(admission['frozen']==link(BASE/'candidate-02/frozen-candidate.json') and
         admission['status']==link(BASE/'verification-status-pool-pio-debug-stopped.json'),'PIO runtime admission')
    need(runtime_package_original(frozen['package'])==old['package'] and
         frozen['package']['runtime_correction_files']==list(RUNTIME_FILES),'PIO runtime scope')
    need(set(frozen['source_inputs'])==set(old['source_inputs']),'PIO runtime input set')
    for name,sha in old['source_inputs'].items():
        if name not in RUNTIME_FILES:need(frozen['source_inputs'][name]==sha,'PIO runtime unrelated change '+name)
    before=BASE/'candidate-02/source'/PRODUCER.replace('/','__')
    need(digest(before)==old['source_inputs'][PRODUCER],'PIO original producer')
    producer_optimization_binding(before.read_bytes(),(ROOT/PRODUCER).read_bytes())


def runtime_image(frozen):
    base=RUNTIME if 'runtime_correction' in frozen else BASE
    return (base/'native/x86_64/reist-x86_64-bootstrap.elf').resolve()


def debug_object_sections(raw):
    """Bounded ELF64 ET_REL inspection. No stripping or file mutation."""
    need(type(raw) is bytes and 64<=len(raw)<=1048576,'debug ELF extent')
    need(raw[:16]==b'\x7fELF\x02\x01\x01'+bytes(9),'debug ELF identity')
    h=list(struct.unpack_from('<HHIQQQIHHHHHH',raw,16));offset=h[5];count=h[11]
    need(h[:5]==[1,62,1,0,0] and h[6:11]==[0,64,0,0,64] and 1<count<=128 and 0<h[12]<count,'debug ELF header')
    need(64<=offset and offset+count*64==len(raw),'debug section table bound')
    headers=[list(struct.unpack_from('<IIQQQQIIQQ',raw,offset+n*64)) for n in range(count)]
    need(headers[0]==[0]*10,'debug null section')
    strings=headers[h[12]]
    need(strings[1]==3 and 64<=strings[4]<offset and 0<strings[5]<=offset-strings[4],'debug section names')
    names=raw[strings[4]:strings[4]+strings[5]];need(names[0]==names[-1]==0,'debug string boundary')
    entries={};spans=[]
    for index,row in enumerate(headers):
        need(row[0]<len(names) and row[8] in (0,1,2,4,8,16,32,64,128,256,512,1024,4096),'debug section name/alignment')
        end=names.find(b'\0',row[0]);need(end>=row[0],'debug name termination')
        try:name=names[row[0]:end].decode('ascii')
        except UnicodeDecodeError:raise ValueError('debug non-ASCII section') from None
        need(name not in entries,'debug duplicate section')
        if index:need(name and row[1]!=0 and 64<=row[4]<=offset,'debug section position')
        need(row[5]<=1048576 and row[3]==0,'debug section size/address')
        data=b''
        if row[1]!=8 and row[5]:
            need(row[5]<=offset-row[4] and not row[4]%max(row[8],1),'debug section range')
            data=raw[row[4]:row[4]+row[5]]
        if index:spans.append((row[4],row[4]+len(data),index))
        entries[name]=dict(index=index,header=row,data=data)
    cursor=64;order=[]
    for first,last,index in sorted(spans):
        alignment=max(headers[index][8],1)
        need(first==(cursor+alignment-1)//alignment*alignment and not any(raw[cursor:first]),'debug overlap/packing/nonzero gap')
        cursor=last;order.append(index)
    need(offset==(cursor+7)//8*8 and not any(raw[cursor:offset]),'debug trailing gap')
    return h,entries,order


def debug_line_normalize(raw,directory):
    """DWARF4 6.2.4: only one exact include directory and its two lengths."""
    need(type(directory) is str and re.fullmatch(r'\./build\\codex-agent\\r83(?:an-task-pool\\native|ao-pool-pio\\pool-reference)\\x86_64\\programs-[0-9a-f]{32}',directory),'debug bound producer directory')
    need(28<=len(raw)<=65536,'debug line extent')
    unit,version,header=struct.unpack_from('<IHI',raw)
    need(unit==len(raw)-4 and version==4 and 18<=header<len(raw)-10,'debug line header')
    end=10+header;base=raw[15];need(1<=base<=32 and 15+base<end,'debug opcode table')
    pos=15+base;found=[]
    for unused in range(32):
        last=raw.find(b'\0',pos,end);need(last>=pos and last-pos<=512,'debug directory bound')
        if last==pos:break
        if raw[pos:last]==directory.encode('ascii'):found.append((pos,last))
        pos=last+1
    else:raise ValueError('debug directory capacity')
    need(len(found)==1,'debug exact directory entry')
    first,last=found[0];replacement=b'<REIST_BUILD>';delta=len(replacement)-(last-first)
    changed=bytearray(raw[:first]+replacement+raw[last:]);struct.pack_into('<I',changed,0,unit+delta);struct.pack_into('<I',changed,6,header+delta)
    return bytes(changed),end,delta


def debug_object_canonical(raw,directory):
    h,entries,order=debug_object_sections(raw)
    need('.debug_line' in entries and '.rela.debug_line' in entries,'debug sections missing')
    line=entries['.debug_line'];rel=entries['.rela.debug_line'];lh=line['header'];rh=rel['header']
    need(lh[1:4]==[1,0,0] and lh[6:]==[0,0,1,0],'debug line attributes')
    need(rh[1:4]==[4,64,0] and rh[5]==24 and rh[7:]==[line['index'],8,24],'debug relocation attributes')
    symbols=[entry for entry in entries.values() if entry['index']==rh[6]]
    need(len(symbols)==1 and symbols[0]['header'][1]==2 and symbols[0]['header'][9]==24,'debug relocation symbol table')
    normalized,end,delta=debug_line_normalize(line['data'],directory)
    target,info,addend=struct.unpack('<QQq',rel['data'])
    need(info&0xffffffff==1 and 0<info>>32<len(symbols[0]['data'])//24,'debug R_X86_64_64 target')
    need(end+3<=target<=len(line['data'])-8 and line['data'][target-3:target]==b'\0\x09\x02' and line['data'][target:target+8]==bytes(8),'debug set-address operand')
    # Every symbol/addend and every byte in the line program stays visible to
    # equality. Only the operand's file-relative offset follows the path size.
    line['data']=normalized;lh[5]=len(normalized);rel['data']=struct.pack('<QQq',target+delta,info,addend)
    cursor=64
    for index in order:
        entry=next(e for e in entries.values() if e['index']==index);alignment=max(entry['header'][8],1)
        cursor=(cursor+alignment-1)//alignment*alignment;entry['header'][4]=cursor;cursor+=len(entry['data'])
    h[5]=(cursor+7)//8*8
    sections=[]
    for name,entry in entries.items():
        fields=entry['header']
        sections.append((name,fields,entry['data'].hex()))
    return json.dumps((h,order,sections),separators=(',',':')).encode('ascii')


def debug_object_equivalent(old,new,old_directory,new_directory):
    a=debug_object_canonical(old,old_directory);b=debug_object_canonical(new,new_directory)
    need(a==b,'debug object has non-directory drift');return hashlib.sha256(a).hexdigest()


def candidate_dir(frozen):return ROOT/frozen['directory']


def source_binding(*,allow_stopped=False):
    baseline=read(BASE/'baseline.json');paths=sorted(BASE.glob('candidate-*/frozen-candidate.json'))
    need(1<=len(paths)<=3 and [p.parent.name for p in paths]==[f'candidate-{n:02d}' for n in range(1,len(paths)+1)],'PIO bounded candidates')
    for path in paths[:-1]:
        stopped=read(path.parent/'stopped.json')
        need(stopped['candidate']==read(path)['candidate'] and stopped['passed'] is False,'PIO prior failure preserved')
    frozen=read(paths[-1]);need(allow_stopped or not (paths[-1].parent/'stopped.json').exists(),'PIO stopped candidate')
    renewal=read((RUNTIME if len(paths)==3 else RENEWAL)/'expected-red.json') if len(paths)>1 else None
    need(frozen['head']==(renewal['head'] if renewal else baseline['head'])==git('rev-parse','HEAD'),'PIO baseline HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    package=next(p for p in queue['packages'] if p['id']==PACKAGE)
    need(queue['active_id']==PACKAGE and package==(renewal['package'] if renewal else baseline['package'])==frozen['package'],'PIO frozen queue')
    if renewal:
        need(frozen['metadata_renewal']==link(RENEWAL/'expected-red.json') and renewal['expected_red'] is True,'PIO metadata renewal binding')
        need({k:value for k,value in runtime_package_original(package).items() if k not in ('debug_metadata_authority','metadata_renewal_files','metadata_renewal_prefix')}==baseline['package'],'PIO unchanged original contract')
        need(package['metadata_renewal_files']==list(METADATA_FILES),'PIO exact metadata scope')
    if len(paths)==3:
        need(frozen['runtime_correction']==link(RUNTIME/'expected-red.json'),'PIO runtime correction binding')
        runtime_source_binding(frozen)
    need(frozen['baseline']==link(BASE/'baseline.json') and frozen['red']==link(BASE/'expected-red.json'),'PIO original bindings')
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed<=set(package['allowed_files']) and not git('diff','--cached','--name-only') and not git('diff','--check'),'PIO scope/index/whitespace')
    for group in ('source_inputs','sources','snapshots','tools_sha256'):verify_files(frozen[group])
    for name,sha in baseline['source_inputs'].items():
        if name not in package['allowed_files']:need(frozen['source_inputs'].get(name)==sha,'PIO unrelated input '+name)
    candidate=hashlib.sha256(json.dumps(frozen['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    need(candidate==frozen['candidate'] and all(read(p)['candidate']!=candidate for p in paths[:-1]),'PIO changed candidate digest')
    need(frozen['helper']==link(ROOT/frozen['helper']['path']),'PIO command helper')
    return frozen


def gate_limit(index):
    need(type(index) is int and 1<=index<=20,'PIO gate index')
    return 300 if index<=12 else 600 if index==17 else 120 if index==18 else 180


def gate_binding(frozen,index,receipt):
    limit=gate_limit(index)
    need(receipt['candidate']==frozen['candidate'] and receipt['command']==frozen['commands'][index-1] and
         receipt['passed'] is True and receipt['exit_code']==0 and 0<=receipt['elapsed']<=limit,'PIO gate '+str(index))
    verify_files({receipt['log']['path']:receipt['log']['sha256']})
    if index in (13,14,15,17,18):
        need(bool(receipt['artifacts']),'PIO missing build artifacts');verify_files(receipt['artifacts'])
    if 'metadata_renewal' in frozen and index in ((13,14) if 'runtime_correction' in frozen else (13,14,15)):
        path,old=build_reuse_proof(frozen,index)
        need(receipt.get('execution')=='REUSED' and receipt['argv']==[] and receipt['original_receipt']==link(path) and
             receipt['original_elapsed']==old['elapsed'] and receipt['artifacts']==old['artifacts'],'PIO exact build reuse')
    else:need('execution' not in receipt,'PIO unexpected reuse')


def build_reuse_binding(frozen,old,receipt,index):
    need(type(index) is int and index in (13,14,15),'PIO reuse index')
    runtime='runtime_correction' in frozen
    if runtime:need(index in (13,14) and frozen['directory'].endswith('/candidate-03'),'PIO runtime reference reuse only')
    need(old['directory']=='build/codex-agent/r83ao-pool-pio/candidate-01' and
         frozen['directory'] in ('build/codex-agent/r83ao-pool-pio/candidate-02','build/codex-agent/r83ao-pool-pio/candidate-03'),'PIO reuse candidates')
    need(set(old['source_inputs'])==set(frozen['source_inputs']),'PIO reuse input inventory')
    for candidate in (old,frozen):
        need(candidate['candidate']==hashlib.sha256(json.dumps(candidate['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'PIO reuse source digest')
    allowed=RUNTIME_FILES if runtime else METADATA_FILES
    need(all(sha==frozen['source_inputs'][name] for name,sha in old['source_inputs'].items() if name not in allowed),'PIO changed build dependency')
    package=runtime_package_original(frozen['package']) if runtime else frozen['package']
    commands=package['targeted_tests']+package['package_tests']+package['runtime_tests'] if runtime else frozen['commands']
    need(old['tools_sha256']==frozen['tools_sha256'] and old['commands']==commands and len(old['commands'])==20,'PIO reuse tools/commands')
    need({k:value for k,value in package.items() if k not in ('debug_metadata_authority','metadata_renewal_files','metadata_renewal_prefix')}==old['package'],'PIO reuse profile drift')
    if runtime:
        before=BASE/'candidate-01/source'/PRODUCER.replace('/','__');after=ROOT/PRODUCER
        need(digest(before)==old['source_inputs'][PRODUCER] and digest(after)==frozen['source_inputs'][PRODUCER],'PIO producer source binding')
        producer_optimization_binding(before.read_bytes(),after.read_bytes())
    need(receipt['candidate']==old['candidate'] and receipt['command']==old['commands'][index-1] and receipt['passed'] is True and
         receipt['exit_code']==0 and 0<=receipt['elapsed']<=180 and 'execution' not in receipt and bool(receipt['artifacts']),'PIO original build result')


def build_reuse_proof(frozen,index):
    admission=read(RENEWAL/'admission.json');old_path=BASE/'candidate-01/frozen-candidate.json'
    need(admission['frozen']==link(old_path),'PIO old build sources')
    need(type(index) is int and index in (13,14,15),'PIO reuse receipt index')
    path=BASE/'candidate-01'/f'gate-{index:02d}.json';need(admission['build_receipts'][index-13]==link(path),'PIO original build receipt')
    old=read(old_path);receipt=read(path);build_reuse_binding(frozen,old,receipt,index)
    verify_files(receipt['artifacts']);verify_files({receipt['log']['path']:receipt['log']['sha256']})
    return path,receipt


def prior_gates(frozen,end):
    result=[]
    for index in range(1,end+1):
        path=candidate_dir(frozen)/f'gate-{index:02d}.json';gate_binding(frozen,index,read(path));result.append(link(path))
    return result


def matching_receipt(kind,candidate):
    values=[(p,read(p)) for p in BASE.glob(kind+'-*.json')]
    values=[(p,v) for p,v in values if v.get('passed') and v.get('candidate')==candidate]
    need(len(values)==1,'PIO unique '+kind+' receipt');return values[0]


def preserve_previous():
    baseline=read(BASE/'baseline.json');verify_files(baseline['preserved_reference_artifacts']);verify_files(baseline['snapshots'])
    previous=read(ROOT/baseline['accepted_an']['path'])
    need(previous['accepted'] and previous['qualification_passed']==24 and
         previous['implementation_commit']=='4f4e1df43b32d00977321c54e750aab6cd94ac40','PIO accepted AN')
    for item in (baseline['accepted_an'],baseline['qualified_an']):
        need(item==link(ROOT/item['path']),'PIO prior receipt changed')
        verify_files(read(ROOT/item['path'])['evidence_sha256'])
    verify_files(previous['protected_artifacts']);verify_files(previous['tools_sha256'])
    for name,sha in baseline['source_inputs'].items():
        if name.startswith('scripts/run_qemu_') or name in ('scripts/qemu_binary_memory.py','scripts/verify_x86_64_file_launch.py','scripts/verify_x86_64_task_pool.py'):
            need(digest(ROOT/name)==sha,'PIO original guest oracle changed '+name)
    return baseline


def defaults():
    frozen=source_binding();receipts=prior_gates(frozen,15);baseline=preserve_previous();bindings={};debug={}
    for name,target in (('pool','pool-reference'),('file','file-reference')):
        old=baseline['old_profiles'][name];new=binary_map(BASE/target/'x86_64')
        verify_files({v['path']:v['sha256'] for v in old.values()})
        need(set(old)==set(new),'PIO default payload inventory '+name)
        for key in old:
            if old[key]['sha256']==new[key]['sha256']:continue
            need(name=='pool' and key in ('programs/program0.o','programs/program1.o'),'PIO default binary drift '+name+'/'+key)
            a=ROOT/old[key]['path'];b=ROOT/new[key]['path']
            normalized=debug_object_equivalent(a.read_bytes(),b.read_bytes(),'./'+str(a.parent.relative_to(ROOT)),'./'+str(b.parent.relative_to(ROOT)))
            debug[key]=dict(before=old[key],after=new[key],normalized_sha256=normalized)
        bindings[name]=dict(before=old,after=new)
    need(set(debug)=={'programs/program0.o','programs/program1.o'},'PIO exact two debug exceptions')
    return dict(passed=True,kind='defaults',candidate=frozen['candidate'],frozen=link(candidate_dir(frozen)/'frozen-candidate.json'),
        payloads=bindings,debug_metadata=debug,gates=receipts,old_acceptance=baseline['accepted_an'],old_qualification=baseline['qualified_an'],new_guests=0,new_builds=0)


def admit_runtime(image,*,fatal=False):
    frozen=source_binding();prior_gates(frozen,17 if fatal else 16)
    path,receipt=matching_receipt('defaults',frozen['candidate'])
    need(receipt['frozen']==link(candidate_dir(frozen)/'frozen-candidate.json'),'PIO default input binding')
    need(image==runtime_image(frozen),'PIO runtime exact image')
    for profile in receipt['payloads'].values():
        for side in ('before','after'):verify_files({v['path']:v['sha256'] for v in profile[side].values()})
    return dict(candidate=frozen['candidate'],defaults=link(path))


def review():
    import run_qemu_x86_64_pool_pio as runtime
    frozen=source_binding();gates=prior_gates(frozen,19);preserve_previous()
    image=runtime_image(frozen);admit_runtime(image,fatal=True)
    config=runtime.image_config(image);count=runtime.wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
    evidence={};matrices=[];total=0;spent=0;current_spent=0
    for fatal,base in ((False,BASE/'guests'),(True,BASE/'fatal-guests')):
        attempts=[(p,read(p)) for p in base.glob('attempt-*/summary.json')]
        need(1<=len(attempts)<=3 and all(r.get('closed') for p,r in attempts),'PIO bounded closed attempts')
        need(len({r['candidate'] for p,r in attempts})==len(attempts),'PIO unchanged matrix retry')
        total+=sum(len(r['cases']) for p,r in attempts);spent+=sum(r['guest_elapsed'] for p,r in attempts)
        current=[(p,r) for p,r in attempts if r['candidate']==frozen['candidate']];need(len(current)==1,'PIO current matrix')
        path,result=current[0];matrices.append(link(path));current_spent+=result['guest_elapsed']
        need(result['passed'] and result['fatal']==fatal and result['image_sha256']==digest(image) and result['guest_elapsed']<=(40 if fatal else 320),'PIO same-image result')
        expected=[(k,4096) for k in runtime.FATAL_CASES] if fatal else list(runtime.CASES)
        need([(r['case'],r['ram']) for r in result['cases']]==expected,'PIO complete frozen matrix')
        need((result['allocations'],result['child_sha256'])==(count,sha),'PIO actual allocation/ELF binding')
        for row in result['cases']:
            need(row['passed'] and 0<row['elapsed']<=20,'PIO guest deadline/result')
            folder=path.parent/f'guest-{row["case"]}-{row["ram"]}';runtime.pio.safe_folder(folder)
            serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
            rows=runtime.validate_fatal(serial,trace,row['case'],folder) if fatal else runtime.validate(serial,trace,row['case'],row['oom'],count,sha)
            need(row['tasks']==len(rows),'PIO task count')
            metrics=read(folder/'capture-metrics.json')
            need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
                 metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','PIO process closure')
            if not fatal:
                reads=[json.loads(line) for line in (folder/'binary-memory/reads.jsonl').read_text().splitlines()]
                need(0<len(reads)<=2048 and sum(r['bytes'] for r in reads)<=128*1024*1024,'PIO bounded RAM capture')
                need([r['equivalence'] for r in reads if r['equivalence'] is not None]==['kernel','high'],'PIO independent same-stop RAM comparisons')
                for index,r in enumerate(reads,1):
                    dump=folder/'binary-memory'/r['file']
                    need(r['sequence']==index and dump.name==f'ram-{index:04d}.bin' and dump.stat().st_size==r['bytes'] and digest(dump)==r['sha256'],'PIO raw RAM binding')
            if row['case']!=12:
                for phase in ('before','after'):
                    media=read(folder/('media-'+phase+'.json'))
                    need(media['passed'] and media['phase']==phase and media['overlay_allocated_data']==0 and
                         media['logical_bytes']==65536 and media['base_sha256']==hashlib.sha256(runtime.pio.BLOCK_DISK).hexdigest(),'PIO unchanged generated media')
                need((folder/'generated.raw').read_bytes()==runtime.pio.BLOCK_DISK,'PIO base bytes')
            else:need(not any(folder.glob('*.qcow2')) and not any(folder.glob('generated.raw')),'PIO absent device fixture')
            for f in folder.rglob('*'):
                if f.is_file():evidence[f.relative_to(ROOT).as_posix()]=digest(f)
    need(total<=54 and spent<=1080,'PIO cumulative guest bound')
    return dict(passed=True,kind='review',candidate=frozen['candidate'],gates=gates,matrices=matrices,evidence_sha256=evidence,
        cases=18,guest_elapsed=current_spent,total_guest_attempts=total,total_guest_elapsed=spent,new_builds=0,new_guests=0,scope=sorted(frozen['sources']))


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--defaults',action='store_true');group.add_argument('--review',action='store_true');args=parser.parse_args()
    kind='defaults' if args.defaults else 'review';started=time.monotonic();result=dict(passed=False,kind=kind)
    path=BASE/(kind+'-'+uuid.uuid4().hex+'.json')
    try:
        result=defaults() if args.defaults else review();print('POOL_PIO_'+kind.upper()+'_OK',flush=True);return 0
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result['error']=str(error);print('POOL_PIO_'+kind.upper()+'_FAIL '+str(error),flush=True);return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,6)
        with path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
        print('POOL_PIO_RECEIPT '+str(path),flush=True)


if __name__=='__main__':raise SystemExit(main())
