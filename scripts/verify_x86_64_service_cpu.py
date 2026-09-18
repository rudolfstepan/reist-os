"""Read-only admission for the frozen periodic CPU package; never runs a gate."""
from pathlib import Path
import argparse,ast,hashlib,inspect,json,re,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files,binary_map
import verify_x86_64_pool_pio as historical
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83ap-service-cpu'
PACKAGE='R8.3ap-x86_64-service-cpu'
PROFILES=(('pool','pool-reference'),('pio','pio-reference'),('file','file-reference'))
RENEWAL=BASE/'owner-renewal'
COMPACT=BASE/'compact-renewal'
COMPACT_FILES={'scripts/run_qemu_x86_64_service_cpu.py','scripts/verify_x86_64_service_cpu.py',
    'test/test_x86_64_service_cpu.py','docs/architecture/NATIVE_SERVICE_CPU_CONTRACT.md','docs/development/CURRENT_WORK.md'}
WORKLOAD=BASE/'workload-renewal'
FIXTURE='arch/x86_64/user/task_pool.c'
WORKLOAD_FILES=COMPACT_FILES|{FIXTURE}
SERVICE_IMAGE=BASE/'critical-renewal/native/x86_64/reist-x86_64-bootstrap.elf'
COST=BASE/'cost-renewal'


def cost_admission():
    workload_admission();a=read(COST/'admission.json')
    for item in [a[k] for k in ('stopped','old_candidate','helper','image')]+a['build_receipts']+a['old_matrices']:
        need(item==link(ROOT/item['path']),'CPU cost immutable evidence')
    stopped=read(ROOT/a['stopped']['path']);old=dict(a['package'])
    need(bool(old.pop('cost_renewal_authority')) and old.pop('cost_renewal_prefix')==COST.relative_to(ROOT).as_posix() and
         set(old.pop('cost_renewal_files'))==COMPACT_FILES and old==stopped['package'],'CPU cost scope/gates')
    need((a['candidate_limit'],a['diagnostic_limit'],a['new_build_limit'],a['spent_guests'],a['spent_guest_seconds'])==
         (2,1,0,8,159.7972) and (a['guest_limit'],a['guest_seconds_limit'])==(42,840),'CPU cost limits')
    need(a['old_candidate']==stopped['frozen'] and a['image']==stopped['retained_service_image'],'CPU cost image origin')
    f=read(ROOT/a['old_candidate']['path'])
    need(a['build_receipts']==[link(ROOT/f['directory']/f'gate-{i:02d}.json') for i in (16,17,18,19)],'CPU cost four build receipts')
    for key in ('evidence_sha256','protected_artifacts','tools_sha256'):verify_files(stopped[key])
    diagnosis=read(COST/'diagnosis.json')
    need(diagnosis['closed'] and diagnosis['measured'] and diagnosis['diagnostic_only'] and
         not diagnosis['qualification_passed'] and diagnosis['host']['passed'] and
         diagnosis['new_builds']==0 and diagnosis['new_guests']==1 and
         diagnosis['admission']==link(COST/'admission.json') and diagnosis['helper']==a['helper'],'CPU measured diagnosis')
    verify_files(diagnosis['evidence_sha256'])
    return a


def cost_observer_binding(before,after):
    def function(source,name):
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name]
        need(len(nodes)==1,'CPU cost observer function '+name);return ast.get_source_segment(source,nodes[0])
    old=function(before,'observer_body');new=function(after,'observer_body');helper=function(after,'witness_hooks_needed')
    need(after==before.replace(old,helper+'\n\n\n'+new,1),'CPU cost immutable codec/oracles/CPU callbacks')


def cost_inputs(inputs,a,observer=None):
    need(set(inputs)==set(a['source_inputs']),'CPU cost complete inventory')
    for name,sha in a['source_inputs'].items():
        if name not in COMPACT_FILES:need(inputs[name]==sha,'CPU cost build input '+name)
    source='scripts/run_qemu_x86_64_service_cpu.py'
    saved=BASE/'workload-stop-source/scripts__run_qemu_x86_64_service_cpu.py'
    actual=(ROOT/source).read_bytes() if observer is None else observer
    need(digest(saved)==a['source_inputs'][source] and hashlib.sha256(actual).hexdigest()==inputs[source],'CPU cost observer input')
    cost_observer_binding(saved.read_text(),actual.decode().replace('\r\n','\n'))


def cost_reuse_inputs(frozen,a,index):
    need(type(index) is int and index in (16,17,18,19),'CPU cost reuse index')
    observer=None
    if 'directory' in frozen:
        path=ROOT/frozen['directory']/'source/scripts__run_qemu_x86_64_service_cpu.py'
        need(frozen['snapshots'].get(path.relative_to(ROOT).as_posix())==digest(path),'CPU historical cost observer snapshot')
        observer=path.read_bytes()
    cost_inputs(frozen['source_inputs'],a,observer);old=read(ROOT/a['old_candidate']['path'])
    need(frozen['package']==a['package'] and frozen['tools_sha256']==old['tools_sha256'] and
         frozen['commands']==old['commands'],'CPU cost exact build commands/tools/package')
    for name,sha in old['source_inputs'].items():
        if name not in COMPACT_FILES|{'automation/reist-s03b.toml'}:
            need(frozen['source_inputs'][name]==sha,'CPU cost retained producer '+name)


def fixture_change_binding(before,after):
    """Only the explicitly disabled service calibration may differ, byte for byte."""
    changes=[
        (b'    /* Test workload calibration, never accounting authority. Both clocks\n     * remain independently checked by the actual IRQ sample observer. */',
         b'    /* Enclose both clock syscalls, including delayed resumes. Remove one\n     * 10ms quantization interval; the IRQ observer remains the authority. */'),
        (b'uint64_t first=(uint64_t)S0(MONOTONIC_MS),begin=service_cycles(),now=first;',
         b'uint64_t begin=service_cycles(),first=(uint64_t)S0(MONOTONIC_MS),now=first;'),
        (b'uint64_t quantum=(end-begin)*50/((now-first)*4);',b'uint64_t quantum=(end-begin)*11/(now-first-10);')]
    prefix=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(prefix)==1,'CPU exact excluded service suffix')
    start=before.index(b'static uint64_t service_quantum(void)');end=before.index(b'static int service_samples',start)
    need(start>before.index(prefix),'CPU calibration only in service suffix')
    result=before
    for old,new in changes:
        need(result.count(old)==1 and old in before[start:end],'CPU exact calibration substitution')
        result=result.replace(old,new)
    need(after==result,'CPU unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def overlap_fixture_binding(before,after):
    """Exact service-only work relocation; no broad fixture/hash exception."""
    helper=b'''static int service_overlap(unsigned hold_ms) {
    if(hold_ms!=2500 && hold_ms!=3000)return -1;
    uint64_t first=(uint64_t)S0(MONOTONIC_MS),last=first;
    if(first>(uint64_t)INT64_MAX-hold_ms || service_samples(40,0))return -1;
    /* Keep the whole holding interval, but do the root's existing work
     * alongside its children. Only the remaining time needs blocking sleep. */
    for(unsigned n=0;n<31;n++) {
        uint64_t now=(uint64_t)S0(MONOTONIC_MS);
        if(now<last || now>(uint64_t)INT64_MAX)return -1;
        if(now-first>=hold_ms)return 0;
        last=now;
        uint64_t remaining=hold_ms-(now-first);
        if(S1(SLEEP_MS,remaining<100?remaining:100))return -1;
    }
    return -1;
}
'''
    idle=b'''static int service_idle(unsigned count) {
    for(unsigned n=0;n<count;n++)if(S1(SLEEP_MS,100))return -1;
    return 0;
}
'''
    changes=[(idle,idle+helper),
        (b'    REQUIRE(!service_idle(PROGRAM_ID==1 && mode==6?30:2),208);',
         b'    if(PROGRAM_ID==1 && mode==6)REQUIRE(!service_overlap(3000),208);\n    else REQUIRE(!service_idle(2),208);'),
        (b'        REQUIRE(release(ports[0],0)==0 && !service_idle(25),210);',
         b'        REQUIRE(release(ports[0],0)==0 && !service_overlap(2500),210);'),
        (b'    REQUIRE(!service_samples(40,0),242);',b'    if(mode!=6)REQUIRE(!service_samples(40,0),242);')]
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(marker)==1,'CPU overlap unique disabled-service boundary');result=before
    for old,new in changes:
        need(result.count(old)==1 and before.index(old)>before.index(marker),'CPU overlap exact service-only replacement')
        result=result.replace(old,new)
    need(after==result,'CPU overlap unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def retention_fixture_binding(before,after):
    """Only the case6 fixture's bounded fence/drain barrier may change."""
    helper=b'''static int service_retained(uint32_t endpoint) {
    /* EPIPE proves peer fencing, not heap reaping. Do not consume WAIT yet.
     * This child owns at most8192 heap bytes: actual CANCEL needs <=7 steps.
     * Eight-slot round robin plus56 blocking sleeps supplies >=56 dispatches.
     * The unchanged observer still requires terminal receipt AND task zero. */
    for(unsigned n=0;n<8;n++) {
        volatile uint32_t message[35];message_init(message,0);
        int64_t result=S3(IPC_RECEIVE_TIMEOUT,endpoint,message,1000);
        if(result==-32) {
            for(unsigned step=0;step<56;step++)if(S1(SLEEP_MS,1))return -1;
            return 0;
        }
        if(result!=-110)return -1;
    }
    return -1;
}
'''
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    anchor=b'    return -110;\n}\n#endif\nint main(int argc,char **argv) {'
    call=b'        REQUIRE(release(ports[0],0)==0 && !service_overlap(2500),210);\n'
    need(before.count(marker)==before.count(anchor)==before.count(call)==1 and
         before.index(anchor)>before.index(marker) and before.index(call)>before.index(anchor),'CPU retained service-only anchors')
    result=before.replace(anchor,anchor.replace(b'#endif',helper+b'#endif'),1).replace(call,call+b'        REQUIRE(!service_retained(ports[0]),244);\n',1)
    need(after==result,'CPU retention unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def parallel_fixture_binding(before,after):
    """Exact private case6 scheduling changes; child and default bytes stay exact."""
    changes=[
        (b'     * Eight-slot round robin plus56 blocking sleeps supplies >=56 dispatches.',
         b'     * Eight-slot round robin plus56 yields supplies >=56 dispatches without\n     * waiting for artificial timer expirations or polling completion state.'),
        (b'for(unsigned step=0;step<56;step++)if(S1(SLEEP_MS,1))return -1;',
         b'for(unsigned step=0;step<56;step++)if(S0(YIELD))return -1;'),
        (b'        REQUIRE(release(ports[0],0)==0 && !service_overlap(2500),210);',
         b'        for(unsigned i=0;i<3;i++)REQUIRE(release(ports[i],i)==0,210);\n        REQUIRE(!service_overlap(2500),210);'),
        (b'    for(unsigned i=0;i<3;i++)\n        if(!(PROGRAM_ID==0 && mode==4 && !i))REQUIRE(release(ports[i],i)==0,218);',
         b'    for(unsigned i=0;i<3;i++)\n        if(!(PROGRAM_ID==0 && ((mode==4 && !i) || (mode==6 && i))))\n            REQUIRE(release(ports[i],i)==0,218);')]
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(marker)==1,'CPU parallel unique disabled-service boundary');result=before
    for old,new in changes:
        need(result.count(old)==1 and before.index(old)>before.index(marker),'CPU parallel exact service-only replacement')
        result=result.replace(old,new)
    need(after==result,'CPU parallel unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def dual_fixture_binding(before,after):
    """Only release role1's three children before its unchanged case6 hold."""
    changes=[
        (b'    if(PROGRAM_ID==1 && mode==6)REQUIRE(!service_overlap(3000),208);',
         b'    if(PROGRAM_ID==1 && mode==6) {\n'
         b'        /* Overlap both families; keep all receipts until the original hold ends. */\n'
         b'        for(unsigned i=0;i<3;i++)REQUIRE(release(ports[i],i)==0,208);\n'
         b'        REQUIRE(!service_overlap(3000),208);\n    }'),
        (b'        if(!(PROGRAM_ID==0 && ((mode==4 && !i) || (mode==6 && i))))',
         b'        if(!(PROGRAM_ID==0 && ((mode==4 && !i) || (mode==6 && i))) &&\n'
         b'           !(PROGRAM_ID==1 && mode==6))')]
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(marker)==1,'CPU dual service boundary');result=before
    for old,new in changes:
        need(result.count(old)==1 and result.index(old)>result.index(marker),'CPU dual exact service-only change')
        result=result.replace(old,new,1)
    need(after==result,'CPU dual unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def peer_fixture_binding(before,after):
    """Exact case6 peer-fence lifetime and overlap; no public/runtime ABI edit."""
    helper=b'''static int service_peer_open(uint32_t *endpoint) {
    /* Private case6 fixture pairs (1,2) and (10,11), not PID discovery.
     * Only a successful explicit grant establishes the peer-fence contract. */
    if(!endpoint || (root_witness.owner!=2 && root_witness.owner!=11))return -1;
    *endpoint=0;
    if(S1(IPC_CREATE,endpoint) || !*endpoint)return -1;
    if(S3(IPC_DELEGATE,*endpoint,root_witness.owner-1,2)) {
        (void)S1(IPC_CLOSE,*endpoint);*endpoint=0;return -1;
    }
    return 0;
}
static int service_peer_finish(uint32_t endpoint) {
    if(!endpoint)return -1;
    int fenced=0;
    for(unsigned n=0;n<8;n++) {
        volatile uint32_t message[35];message_init(message,0);
        int64_t result=S3(IPC_RECEIVE_TIMEOUT,endpoint,message,1000);
        if(result==-32) {fenced=1;break;}
        if(result!=-110)break;
    }
    int64_t closed=S1(IPC_CLOSE,endpoint);
    return fenced && !closed?0:-1;
}
'''
    anchor=(b'    REQUIRE(root_witness.mode<=11,201);\n'
            b'    root_witness.owner=(uint64_t)S0(GETPID);root_witness.phase=1;\n'
            b'    REQUIRE(root_witness.owner && root_witness.owner<=UINT32_MAX,202);\n')
    changes=[(b'static int service_retained(uint32_t endpoint) {',helper+b'static int service_retained(uint32_t endpoint) {'),
        (anchor,anchor+b'    uint32_t peer=0;\n    if(PROGRAM_ID==1 && mode==6)REQUIRE(!service_peer_open(&peer),246);\n'),
        (b'        /* Overlap both families; keep all receipts until the original hold ends. */',
         b'        /* Keep every receipt until the other root is generation-fenced. */'),
        (b'        REQUIRE(!service_overlap(3000),208);',
         b'        REQUIRE(!service_overlap(3000),208);\n        REQUIRE(!service_peer_finish(peer),247);'),
        (b'        REQUIRE(!service_overlap(2500),210);',b'        REQUIRE(!service_idle(25),210);'),
        (b'    if(mode!=6)REQUIRE(!service_samples(40,0),242);',b'    if(mode!=6 || PROGRAM_ID==0)REQUIRE(!service_samples(40,0),242);')]
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(marker)==1,'CPU peer service boundary');result=before
    for old,new in changes:
        need(result.count(old)==1 and result.index(old)>result.index(marker),'CPU peer exact service-only change')
        result=result.replace(old,new,1)
    need(after==result,'CPU peer unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def critical_fixture_binding(before,after):
    """Only move root0's existing work into its hold; retain peer fencing."""
    changes=[(b'        REQUIRE(!service_idle(25),210);',b'        REQUIRE(!service_overlap(2500),210);'),
        (b'    if(mode!=6 || PROGRAM_ID==0)REQUIRE(!service_samples(40,0),242);',
         b'    if(mode!=6)REQUIRE(!service_samples(40,0),242);')]
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(marker)==1,'CPU critical service boundary');result=before
    for old,new in changes:
        need(result.count(old)==1 and result.index(old)>result.index(marker),'CPU critical exact service-only change')
        result=result.replace(old,new,1)
    need(after==result,'CPU critical unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def idle_fixture_binding(before,after):
    """Only case11's split idle becomes one existing bounded receive wait."""
    changes=[(b'static int service_samples(unsigned count,unsigned idle_after_twenty) {',
              b'static int service_samples(unsigned count,unsigned idle_endpoint) {'),
        (b'        if(i==19 && idle_after_twenty)\n            for(unsigned j=0;j<20;j++)if(S1(SLEEP_MS,100))return -1;',
         b'''        if(i==19 && idle_endpoint) {
            /* One blocked interval: separate sleeps permit charged resumes.
             * The original release was consumed; the parent retains the port
             * until WAIT. Any message, revocation or other error fails closed. */
            volatile uint32_t message[35];message_init(message,0);
            if(S3(IPC_RECEIVE_TIMEOUT,idle_endpoint,message,2000)!=-110)return -1;
        }'''),
        (b'service_samples(40,mode==5)',b'service_samples(40,mode==5?port:0)')]
    marker=b'#if REIST_NATIVE_SERVICE_CPU\n#undef main\n#if PROGRAM_ID<3\n'
    need(before.count(marker)==1,'CPU idle service boundary');result=before
    for old,new in changes:
        need(result.count(old)==1 and result.index(old)>result.index(marker),'CPU idle exact service-only change')
        result=result.replace(old,new,1)
    need(after==result,'CPU idle unrelated fixture difference')
    return hashlib.sha256(after).hexdigest()


def workload_original(package):
    original=json.loads(json.dumps(package))
    need(bool(original.pop('workload_renewal_authority')) and
         original.pop('workload_renewal_prefix')==WORKLOAD.relative_to(ROOT).as_posix() and
         set(original.pop('workload_renewal_files'))==WORKLOAD_FILES,'CPU workload scope')
    new=WORKLOAD.relative_to(ROOT).as_posix()+'/native';old=BASE.relative_to(ROOT).as_posix()+'/native'
    for key,index in [('package_tests',3),('runtime_tests',1),('runtime_tests',2)]:
        need(original[key][index].count(new)==1,'CPU workload literal image path')
        original[key][index]=original[key][index].replace(new,old)
    return original


def workload_admission():
    compact=compact_admission();admission=read(WORKLOAD/'admission.json')
    for item in [admission[key] for key in ('stopped','old_candidate','build_frozen','fixture','observer','diagnosis','helper')]+admission['build_receipts']+admission['old_matrices']:
        need(item==link(ROOT/item['path']),'CPU workload immutable evidence')
    stopped=read(ROOT/admission['stopped']['path'])
    need(workload_original(admission['package'])==stopped['package'] and
         stopped['compact_candidates_spent']==stopped['compact_candidates_unused']==1 and
         stopped['qualification_failed_gate']==21,'CPU workload admitted correction')
    need((admission['candidate_limit'],admission['new_build_limit'],admission['guest_limit'],admission['guest_seconds_limit'])==(1,1,42,840) and
         (admission['spent_guests'],admission['spent_guest_seconds'])==(7,135.570475),'CPU workload bounds')
    need(admission['build_frozen']==compact['build_frozen'] and admission['build_receipts']==compact['build_receipts'][:3],
         'CPU workload exactly three reference reuses')
    need(admission['fixture']['sha256']==stopped['source_inputs'][FIXTURE] and
         admission['observer']['sha256']==stopped['source_inputs']['scripts/run_qemu_x86_64_service_cpu.py'],'CPU old source snapshots')
    for group in ('evidence_sha256','protected_artifacts','tools_sha256'):verify_files(stopped[group])
    return admission


def workload_inputs(inputs,admission,observer=None,fixture=None):
    need(set(inputs)==set(admission['source_inputs']),'CPU workload full inventory')
    for name,sha in admission['source_inputs'].items():
        if name not in WORKLOAD_FILES:need(inputs[name]==sha,'CPU workload outside correction '+name)
    actual_fixture=(ROOT/FIXTURE).read_bytes() if fixture is None else fixture
    need(inputs[FIXTURE]==fixture_change_binding((ROOT/admission['fixture']['path']).read_bytes(),actual_fixture),
         'CPU workload fixture binding')
    name='scripts/run_qemu_x86_64_service_cpu.py';before=(ROOT/admission['observer']['path']).read_bytes()
    old=b"(root/'native/x86_64/reist-x86_64-bootstrap.elf')";new=b"(root/'workload-renewal/native/x86_64/reist-x86_64-bootstrap.elf')"
    actual=(ROOT/name).read_bytes() if observer is None else observer
    need(before.count(old)==1 and actual==before.replace(old,new) and inputs[name]==hashlib.sha256(actual).hexdigest(),
         'CPU workload immutable observer/codecs/oracles')


def workload_reuse_inputs(frozen,old,admission,index):
    need(type(index) is int and index in (16,17,18),'CPU workload reference-only reuse')
    observer=None;fixture=None
    if 'directory' in frozen:
        path=ROOT/frozen['directory']/'source/scripts__run_qemu_x86_64_service_cpu.py'
        need(frozen['snapshots'].get(path.relative_to(ROOT).as_posix())==digest(path),'CPU historical observer snapshot')
        observer=path.read_bytes()
        path=ROOT/frozen['directory']/'source'/FIXTURE.replace('/','__')
        need(frozen['snapshots'].get(path.relative_to(ROOT).as_posix())==digest(path),'CPU historical fixture snapshot')
        fixture=path.read_bytes()
    workload_inputs(frozen['source_inputs'],admission,observer,fixture)
    need(frozen['package']==admission['package'] and frozen['tools_sha256']==old['tools_sha256'],'CPU workload tools/package')
    original=workload_original(frozen['package'])
    need(sum((original[key] for key in ('targeted_tests','package_tests','runtime_tests')),[])==old['commands'] and
         frozen['commands']==sum((frozen['package'][key] for key in ('targeted_tests','package_tests','runtime_tests')),[]),
         'CPU workload unchanged obligations')
    need(set(frozen['source_inputs'])==set(old['source_inputs']),'CPU workload reference inventory')
    for name,sha in old['source_inputs'].items():
        if name not in WORKLOAD_FILES|{'automation/reist-s03b.toml'}:need(frozen['source_inputs'][name]==sha,'CPU workload build input '+name)


def renewal_admission():
    admission=read(RENEWAL/'admission.json')
    for item in [admission['stopped'],admission['helper'],admission['owner_red'],admission['diagnosis'],*admission['original_candidates']]:
        need(item==link(ROOT/item['path']),'CPU immutable owner renewal evidence')
    stopped=read(ROOT/admission['stopped']['path'])
    need(stopped['candidates_spent']==3 and stopped['new_kernel_builds']==stopped['new_guests']==0 and
         stopped['qualification_failed_gate']==3,'CPU owner renewal boundary')
    need((admission['candidate_limit'],admission['guest_limit'],admission['guest_seconds_limit'])==(3,42,840),'CPU renewal limits')
    package=json.loads(json.dumps(admission['package']))
    need(package.pop('owner_renewal_prefix')==RENEWAL.relative_to(ROOT).as_posix() and
         bool(package.pop('owner_renewal_authority')),'CPU explicit owner renewal')
    need(package['allowed_files'].pop()=='test/test_x86_64_owner_terminal.py' and package==stopped['package'],'CPU unchanged gates/one-file renewal')
    need(admission['original_candidates']==[link(BASE/f'candidate-{n:02d}/frozen-candidate.json') for n in (1,2,3)],'CPU original spent candidates')
    for n in (1,2,3):
        old=read(BASE/f'candidate-{n:02d}/stopped.json')
        need(old['passed'] is False and old['candidate']==read(BASE/f'candidate-{n:02d}/frozen-candidate.json')['candidate'],'CPU preserved failure')
    red=read(ROOT/admission['owner_red']['path'])
    need(red['passed'] is False and red['exit_code']==1 and red['candidate']==stopped['candidate'],'CPU owner actual red')
    for key in ('evidence_sha256','protected_artifacts','tools_sha256'):verify_files(stopped[key])
    return admission


def compact_admission():
    renewal_admission()
    admission=read(COMPACT/'admission.json')
    for item in [admission['stopped'],admission['helper'],admission['diagnosis'],admission['build_frozen'],
                 *admission['build_receipts'],*admission['old_matrices']]:
        need(item==link(ROOT/item['path']),'CPU compact immutable admission')
    stopped=read(ROOT/admission['stopped']['path'])
    need(stopped['new_guests']==admission['spent_guests']==2 and
         stopped['guest_elapsed']==admission['spent_guest_seconds']==41.888588 and
         stopped['renewal_candidates_spent']==3 and stopped['qualification_failed_gate']==21,'CPU compact stopped boundary')
    need((admission['candidate_limit'],admission['guest_limit'],admission['guest_seconds_limit'])==(2,42,840) and
         admission['new_builds']==admission['new_guests']==0,'CPU compact renewal limits')
    package=json.loads(json.dumps(admission['package']))
    need(bool(package.pop('compact_renewal_authority')) and
         package.pop('compact_renewal_prefix')==COMPACT.relative_to(ROOT).as_posix() and
         set(package.pop('compact_renewal_files'))==COMPACT_FILES and package==stopped['package'],'CPU compact exact scope/gates')
    need(admission['build_frozen']==stopped['frozen'],'CPU compact exact successful build candidate')
    old=read(ROOT/admission['build_frozen']['path'])
    need(admission['build_receipts']==[link(ROOT/old['directory']/f'gate-{i:02d}.json') for i in (16,17,18,19)],'CPU compact four builds')
    need(len(admission['old_matrices'])==2 and all(not read(ROOT/p['path'])['passed'] for p in admission['old_matrices']),
         'CPU old failed matrices remain failed')
    for key in ('evidence_sha256','protected_artifacts','tools_sha256'):verify_files(stopped[key])
    archive_binding()
    return admission


def compact_inputs(inputs,admission):
    need(set(inputs)==set(admission['source_inputs']),'CPU compact full input inventory')
    for name,sha in admission['source_inputs'].items():
        if name not in COMPACT_FILES:need(inputs[name]==sha,'CPU compact outside evidence-only scope '+name)


def reuse_inputs(frozen,old,admission,index):
    """Every kernel, fixture, SDK, producer and tool byte remains identical."""
    need(type(index) is int and index in (16,17,18,19),'CPU reuse build index')
    compact_inputs(frozen['source_inputs'],admission)
    need(frozen['tools_sha256']==old['tools_sha256'] and frozen['commands']==old['commands'],'CPU reuse tools/commands')
    need(set(frozen['source_inputs'])==set(old['source_inputs']),'CPU reuse inventory')
    for name,sha in old['source_inputs'].items():
        if name not in COMPACT_FILES|{'automation/reist-s03b.toml'}:
            need(frozen['source_inputs'][name]==sha,'CPU reuse build input '+name)


def source_binding():
    baseline=read(BASE/'baseline.json');resume=cost_admission()
    paths=sorted(COST.glob('candidate-*/frozen-candidate.json'))
    need(1<=len(paths)<=2 and [p.parent.name for p in paths]==[f'candidate-{i:02d}' for i in range(1,len(paths)+1)],'CPU candidate capacity/order')
    for path in paths[:-1]:
        stopped=read(path.parent/'stopped.json')
        need(stopped['candidate']==read(path)['candidate'] and stopped['passed'] is False,'CPU failed candidate preservation')
    path=paths[-1];frozen=read(path)
    need(not (path.parent/'stopped.json').exists(),'CPU stopped candidate')
    need(frozen['head']==resume['head']==git('rev-parse','HEAD'),'CPU frozen HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    need(queue['active_id']==PACKAGE and queue['packages'][0]==resume['package']==frozen['package'],'CPU frozen queue')
    need(frozen['commands']==sum((frozen['package'][key] for key in ('targeted_tests','package_tests','runtime_tests')),[])
         and len(frozen['commands'])==24,'CPU frozen gates')
    for key,name in (('baseline','baseline.json'),('resume','scope-resume.json'),('red','expected-red.json')):
        need(frozen[key]==link(BASE/name),'CPU original '+key)
    need(frozen['owner_admission']==link(RENEWAL/'admission.json') and
         frozen['gate_executor']==link(ROOT/'build/codex-agent/service_cpu_gates.py'),'CPU renewal and original executor binding')
    need(frozen['compact_admission']==link(COMPACT/'admission.json') and
         frozen['runtime_archive']==link(RENEWAL/'runtime-archive.json'),'CPU compact/archive binding')
    need(frozen['workload_admission']==link(WORKLOAD/'admission.json'),'CPU workload admission binding')
    need(frozen['cost_admission']==link(COST/'admission.json') and
         frozen['cost_diagnosis']==link(COST/'diagnosis.json') and
         frozen['cost_red']==link(COST/'witness-red.log'),'CPU cost diagnosis binding')
    cost_inputs(frozen['source_inputs'],resume)
    stopped=read(ROOT/resume['stopped']['path'])
    need(resume['stopped']==link(ROOT/resume['stopped']['path']),'CPU previous stop')
    verify_files(stopped['evidence_sha256']);verify_files(stopped['protected_artifacts'])
    for group in ('source_inputs','sources','snapshots','tools_sha256'):verify_files(frozen[group])
    need(frozen['tools_sha256']==baseline['tools_sha256'],'CPU tool identity')
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(frozen['sources']) and changed<=set(frozen['package']['allowed_files']) and
         not git('diff','--cached','--name-only') and not git('diff','--check'),'CPU scope/index/whitespace')
    for name,sha in baseline['source_inputs'].items():
        if name not in frozen['package']['allowed_files']:need(frozen['source_inputs'].get(name)==sha,'CPU unrelated source '+name)
    expected=set(baseline['source_inputs'])|{n for n in frozen['package']['allowed_files'] if (ROOT/n).is_file()}
    need(set(frozen['source_inputs'])==expected,'CPU full input inventory')
    signature=hashlib.sha256(json.dumps(frozen['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    need(frozen['candidate']==signature and all(read(p)['candidate']!=signature for p in paths[:-1]),'CPU unchanged retry')
    need(frozen['directory']==path.parent.relative_to(ROOT).as_posix() and frozen['helper']==link(ROOT/frozen['helper']['path']),'CPU verifier helper')
    return frozen


def archive_binding():
    archive=read(RENEWAL/'runtime-archive.json')
    for key in ('frozen','stopped','failed_gate','helper'):
        item=archive[key];need(item==link(ROOT/item['path']),'CPU immutable archived '+key)
    old=read(ROOT/archive['frozen']['path'])
    need(old['directory']==(RENEWAL/'candidate-02').relative_to(ROOT).as_posix() and
         read(ROOT/archive['stopped']['path'])['gate']==21 and
         read(ROOT/archive['failed_gate']['path'])['passed'] is False,'CPU exact archived failed candidate')
    need([g['index'] for g in archive['groups']]==[16,17,18,19],'CPU archive four builds')
    for group,name in zip(archive['groups'],('pool-reference','pio-reference','file-reference','native')):
        source=(BASE/name).relative_to(ROOT).as_posix()
        target=(RENEWAL/'candidate-02/build-archive'/name).relative_to(ROOT).as_posix()
        receipt=ROOT/old['directory']/f'gate-{group["index"]:02d}.json';r=read(receipt)
        need(group['source']==source and group['target']==target and group['receipt']==link(receipt),'CPU exact archive paths')
        need(r['passed'] and r['exit_code']==0 and r['candidate']==old['candidate'] and
             r['command']==old['commands'][group['index']-1] and 0<r['elapsed']<=gate_limit(group['index']),'CPU old successful build')
        verify_files({r['log']['path']:r['log']['sha256']})
        need(all(key.startswith(source+'/') for key in r['artifacts']),'CPU archive subtree')
        expected={key:dict(path=target+key[len(source):],sha256=sha) for key,sha in r['artifacts'].items()}
        need(group['files']==expected,'CPU archive exact raw hashes')
        verify_files({entry['path']:entry['sha256'] for entry in expected.values()})
    return archive


def gate_limit(index):
    need(type(index) is int and 1<=index<=24,'CPU gate index')
    return 300 if index<=15 else 600 if index==21 else 120 if index==22 else 180


def gate_binding(frozen,index,receipt):
    need(receipt['candidate']==frozen['candidate'] and receipt['command']==frozen['commands'][index-1] and
         receipt['passed'] is True and receipt['exit_code']==0 and 0<=receipt['elapsed']<=gate_limit(index),'CPU gate '+str(index))
    if 'execution' in receipt:
        need(receipt['execution']=='reuse' and index in (16,17,18,19),'CPU unproved build reuse')
        if 'cost_admission' in frozen:
            admission=read(COST/'admission.json');cost_reuse_inputs(frozen,admission,index)
            old=read(ROOT/admission['old_candidate']['path']);ref=admission['build_receipts'][index-16]
            need(ref==link(ROOT/ref['path']) and admission['old_candidate']==link(ROOT/admission['old_candidate']['path']) and
                 receipt['reuse']==dict(frozen=admission['old_candidate'],receipt=ref),'CPU cost reuse origin')
            original=read(ROOT/ref['path']);need(receipt['artifacts']==original['artifacts'],'CPU cost exact artifacts')
            gate_binding(old,index,original)
            verify_files({receipt['log']['path']:receipt['log']['sha256']});verify_files(old['tools_sha256'])
            return
        workload='workload_admission' in frozen
        admission=read((WORKLOAD if workload else COMPACT)/'admission.json');old=read(ROOT/admission['build_frozen']['path'])
        need(admission['build_frozen']==link(ROOT/admission['build_frozen']['path']),'CPU reuse frozen source binding')
        if workload:workload_reuse_inputs(frozen,old,admission,index)
        else:reuse_inputs(frozen,old,admission,index)
        original=admission['build_receipts'][index-16]
        need(original==link(ROOT/original['path']) and
             original['path']==old['directory']+f'/gate-{index:02d}.json','CPU reuse original receipt')
        r=read(ROOT/original['path']);need('execution' not in r,'CPU reuse must originate in actual build')
        need(receipt['reuse']==dict(frozen=admission['build_frozen'],receipt=original) and
             receipt['artifacts']==r['artifacts'],'CPU reuse exact evidence')
        gate_binding(old,index,r)
        verify_files(old['tools_sha256'])
    verify_files({receipt['log']['path']:receipt['log']['sha256']})
    if index in (16,17,18,19,21,22):
        need(bool(receipt['artifacts']),'CPU gate evidence missing');verify_files(receipt['artifacts'])


def prior_gates(frozen,last):
    results=[]
    for index in range(1,last+1):
        path=ROOT/frozen['directory']/f'gate-{index:02d}.json';receipt=read(path)
        gate_binding(frozen,index,receipt);results.append(link(path))
    return results


def preserve_previous():
    baseline=read(BASE/'baseline.json')
    for key in ('protected_artifacts','snapshots','tools_sha256'):verify_files(baseline[key])
    for key in ('accepted_ao','qualified_ao'):
        item=baseline[key];need(item==link(ROOT/item['path']),'CPU historical receipt '+key)
        old=read(ROOT/item['path']);verify_files(old['evidence_sha256'])
    accepted=read(ROOT/baseline['accepted_ao']['path'])
    need(accepted['accepted'] and accepted['qualification_passed']==20 and
         accepted['implementation_commit']=='30b8046e145c7f422b0744905af5380afac44095','CPU accepted AO identity')
    return baseline


def debug_object_sections(raw):
    """Exact ELF64 producer layout, including zero-file-size SHT_NOBITS.

    gABI3.2: sh_offset is conceptual for NOBITS; sh_addralign constrains its
    memory address, not nonexistent file bytes. Require its offset to equal
    the preceding file end exactly. No padding or header field is ignored.
    The old pool-only parser remains immutable for its historical evidence.
    """
    source=inspect.getsource(historical.debug_object_sections)
    old='alignment=max(headers[index][8],1)'
    need(source.count(old)==1,'CPU exact ELF packing adapter')
    source=source.replace(old,'alignment=1 if headers[index][1]==8 else max(headers[index][8],1)')
    env=dict(vars(historical));exec(compile(source,'CPU ELF64 zero-file section admission','exec'),env)
    return env['debug_object_sections'](raw)


def debug_equivalent(old,new,old_directory,new_directory):
    """The accepted DWARF4 parser, with exactly two manifest-bound paths.

    Only the directory string, two DWARF lengths and the corresponding section
    positions/relocation offset are normalized. Every opcode/symbol/address and
    all other bytes still participate in equality. No broader debug exception.
    """
    patterns=(r'\./build\\codex-agent\\r83ao-pool-pio\\(?:pool-reference|file-reference|runtime-correction\\native)\\x86_64\\programs-[0-9a-f]{32}',
        r'\./build\\codex-agent\\r83ap-service-cpu\\(?:pool-reference|pio-reference|file-reference)\\x86_64\\programs-[0-9a-f]{32}')
    need(re.fullmatch(patterns[0],old_directory) and re.fullmatch(patterns[1],new_directory),'CPU manifest debug directories')
    source=inspect.getsource(historical.debug_line_normalize)
    lines=source.splitlines();guards=[i for i,line in enumerate(lines) if "'debug bound producer directory'" in line]
    need(len(guards)==1,'CPU historical directory guard')
    lines[guards[0]]="    need(type(directory) is str and directory in directories,'debug bound producer directory')"
    env=dict(vars(historical),directories={old_directory,new_directory},debug_object_sections=debug_object_sections)
    exec(compile('\n'.join(lines)+'\n'+inspect.getsource(historical.debug_object_canonical),'CPU bounded DWARF4 adapter','exec'),env)
    a=env['debug_object_canonical'](old,old_directory);b=env['debug_object_canonical'](new,new_directory)
    need(a==b,'CPU default non-directory object drift');return hashlib.sha256(a).hexdigest()


def defaults():
    frozen=source_binding();gates=prior_gates(frozen,19);baseline=preserve_previous();bindings={};debug={}
    for name,target in PROFILES:
        old=baseline['old_profiles'][name];new=binary_map(BASE/target/'x86_64')
        verify_files({v['path']:v['sha256'] for v in old.values()});need(set(old)==set(new),'CPU default inventory '+name)
        for key in old:
            if old[key]['sha256']==new[key]['sha256']:continue
            need(key in ('programs/program0.o','programs/program1.o'),'CPU default binary drift '+name+'/'+key)
            a=ROOT/old[key]['path'];b=ROOT/new[key]['path']
            sha=debug_equivalent(a.read_bytes(),b.read_bytes(),'./'+str(a.parent.relative_to(ROOT)),'./'+str(b.parent.relative_to(ROOT)))
            debug[name+'/'+key]=dict(before=old[key],after=new[key],normalized_sha256=sha)
        bindings[name]=dict(before=old,after=new)
    return dict(passed=True,kind='defaults',candidate=frozen['candidate'],frozen=link(ROOT/frozen['directory']/'frozen-candidate.json'),
        gates=gates,payloads=bindings,debug_metadata=debug,old_acceptance=baseline['accepted_ao'],new_guests=0,new_builds=0)


def matching_receipt(kind,candidate):
    values=[(p,read(p)) for p in BASE.glob(kind+'-*.json')]
    values=[(p,v) for p,v in values if v.get('passed') and v.get('candidate')==candidate]
    need(len(values)==1,'CPU unique '+kind+' receipt');return values[0]


def admit_runtime(image,fatal=False):
    frozen=source_binding();prior_gates(frozen,21 if fatal else 20)
    path,receipt=matching_receipt('defaults',frozen['candidate'])
    need(receipt['frozen']==link(ROOT/frozen['directory']/'frozen-candidate.json'),'CPU defaults source binding')
    need(image==SERVICE_IMAGE.resolve(),'CPU exact runtime image')
    for profile in receipt['payloads'].values():
        for side in ('before','after'):verify_files({v['path']:v['sha256'] for v in profile[side].values()})
    return dict(candidate=frozen['candidate'],defaults=link(path))


def compact_matrix_budget(candidate,fatal,starting=False):
    admission=read(COMPACT/'admission.json');old={p['path']:p for p in admission['old_matrices']}
    total=0;spent=0;new={False:[],True:[]};found=set()
    for kind,name in ((False,'guests'),(True,'fatal-guests')):
        for path in (BASE/name).glob('attempt-*/summary.json'):
            row=read(path);key=path.relative_to(ROOT).as_posix()
            need(row.get('closed') and row['fatal']==kind,'CPU closed matrix')
            need(type(row['guest_elapsed']) in (int,float) and 0<=row['guest_elapsed']<=840,'CPU matrix elapsed')
            total+=len(row['cases']);spent+=row['guest_elapsed']
            if key in old:
                need(link(path)==old[key] and not row['passed'],'CPU preserved failed matrix');found.add(key)
            else:new[kind].append(row)
    need(found==set(old) and all(len(rows)<=2 for rows in new.values()),'CPU compact matrix budget')
    need(total<=42 and spent<=840,'CPU cumulative guest budget')
    if starting:
        need(len(new[fatal])<2 and all(r['candidate']!=candidate for r in new[fatal]),'CPU unchanged/exhausted matrix retry')
        need(total+(2 if fatal else 12)<=42 and spent+(40 if fatal else 240)<=840,'CPU reserve bounded full matrix')
    return total,spent


def matrix_budget(candidate,fatal,starting=False):
    a=read(COST/'admission.json');diag=read(COST/'diagnosis.json')
    need(diag['closed'] and diag['measured'] and diag['new_guests']==1 and diag['new_builds']==0 and
         0<diag['guest_elapsed']<=40,'CPU counted diagnostic')
    total=1;spent=diag['guest_elapsed'];old={p['path']:p for p in a['old_matrices']};found=set();new={False:[],True:[]}
    for kind,name in ((False,'guests'),(True,'fatal-guests')):
        for path in (BASE/name).glob('attempt-*/summary.json'):
            row=read(path);key=path.relative_to(ROOT).as_posix()
            need(row.get('closed') and row['fatal']==kind and type(row['guest_elapsed']) in (int,float) and
                 0<=row['guest_elapsed']<=840,'CPU closed counted matrix')
            total+=len(row['cases']);spent+=row['guest_elapsed']
            if key in old:need(link(path)==old[key] and not row['passed'],'CPU preserved failed matrix');found.add(key)
            else:new[kind].append(row)
    need(found==set(old) and all(len(rows)<=2 for rows in new.values()),'CPU cost matrix capacity')
    need(total<=42 and spent<=840,'CPU cumulative guest budget')
    if starting:
        need(len(new[fatal])<2 and all(row['candidate']!=candidate for row in new[fatal]),'CPU unchanged/exhausted matrix retry')
        need(total+(2 if fatal else 12)<=42 and spent+(40 if fatal else 240)<=840,'CPU full matrix reservation')
    return total,spent


def review():
    import run_qemu_x86_64_service_cpu as runtime
    frozen=source_binding();gates=prior_gates(frozen,23);preserve_previous()
    image=SERVICE_IMAGE;admit_runtime(image,fatal=True)
    config=runtime.pool.image_config(image);count=runtime.wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
    evidence={};matrices=[];total=1;spent=read(COST/'diagnosis.json')['guest_elapsed'];current_spent=0
    if 'capture_admission' in frozen:
        admission=read(ROOT/frozen['capture_admission']['path']);phase=admission['phase_diagnosis']
        need(phase==link(ROOT/phase['path']),'CPU phase diagnostic binding')
        diagnosis=read(ROOT/phase['path'])
        need(diagnosis['closed'] and diagnosis['measured'] and diagnosis['diagnostic_only'] and
             not diagnosis['qualification_passed'] and diagnosis['new_guests']==1 and diagnosis['new_builds']==0,
             'CPU phase diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    if 'capacity_admission' in frozen:
        admission=read(ROOT/frozen['capacity_admission']['path']);capacity=admission['capacity_diagnosis']
        need(capacity==link(ROOT/capacity['path']),'CPU capacity diagnostic binding')
        diagnosis=read(ROOT/capacity['path'])
        need(diagnosis['closed'] and diagnosis['measured'] and diagnosis['diagnostic_only'] and
             not diagnosis['qualification_passed'] and diagnosis['new_guests']==1 and diagnosis['new_builds']==0,
             'CPU capacity diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    if 'coalesce_admission' in frozen:
        admission=read(ROOT/frozen['coalesce_admission']['path'])
        need(len(admission['newer_diagnoses'])==4,'CPU four later diagnostics')
        for ref in admission['newer_diagnoses']:
            need(ref==link(ROOT/ref['path']),'CPU later diagnostic binding')
            diagnosis=read(ROOT/ref['path'])
            need(diagnosis['closed'] and diagnosis['diagnostic_only'] and
                 not diagnosis['qualification_passed'] and diagnosis['new_guests']==1 and diagnosis['new_builds']==0 and
                 0<diagnosis['guest_elapsed']<=40,'CPU later diagnostic counted only')
            total+=1;spent+=diagnosis['guest_elapsed']
    if 'monotonic_admission' in frozen:
        admission=read(ROOT/frozen['monotonic_admission']['path']);ref=admission['case6_diagnosis']
        need(ref==link(ROOT/ref['path']),'CPU case6 diagnostic binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['diagnostic_only'] and not diagnosis['qualification_passed'] and
             not diagnosis['measured'] and diagnosis['error']=='case6 timestamp moved backward' and
             diagnosis['new_guests']==1 and diagnosis['new_builds']==0 and 0<diagnosis['guest_elapsed']<=40,
             'CPU failed case6 diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    if 'overlap_admission' in frozen:
        admission=read(ROOT/frozen['overlap_admission']['path']);ref=admission['transport_diagnosis']
        need(ref==link(ROOT/ref['path']),'CPU transport diagnostic binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['diagnostic_only'] and not diagnosis['qualification_passed'] and
             not diagnosis['measured'] and diagnosis['error'].startswith('RSP relay failed ConnectionResetError: [WinError 10054]') and
             diagnosis['new_guests']==1 and diagnosis['new_builds']==0 and 0<diagnosis['guest_elapsed']<=30,
             'CPU failed transport diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    if 'guard_admission' in frozen:
        admission=read(ROOT/frozen['guard_admission']['path']);ref=admission['release_diagnosis']
        need(ref==link(ROOT/ref['path']),'CPU release diagnostic binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['diagnostic_only'] and not diagnosis['qualification_passed'] and
             diagnosis['outcome']=='inconclusive_not_reproduced' and diagnosis['new_guests']==1 and
             diagnosis['new_builds']==0 and 0<diagnosis['guest_elapsed']<=20,'CPU release diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    if 'retention_admission' in frozen:
        admission=read(ROOT/frozen['retention_admission']['path']);ref=admission['retention_diagnosis']
        need(ref==link(ROOT/ref['path']),'CPU retention diagnostic binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['diagnostic_only'] and not diagnosis['qualification_passed'] and
             diagnosis['outcome']=='family_receipt_not_terminal' and diagnosis['new_guests']==1 and
             diagnosis['new_builds']==0 and 0<diagnosis['guest_elapsed']<=23,'CPU retention diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    if 'debugger_admission' in frozen:
        admission=read(ROOT/frozen['debugger_admission']['path'])
        ref=admission['allocation_diagnosis'];need(ref==link(ROOT/ref['path']),'CPU allocation diagnostic binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['measured'] and diagnosis['diagnostic_only'] and
             not diagnosis['qualification_passed'] and diagnosis['new_guests']==1 and diagnosis['new_builds']==0 and
             diagnosis['outcome']=='inconclusive_not_reproduced' and 0<diagnosis['guest_elapsed']<=20,
             'CPU allocation diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
        ref=admission['allocation_series'];need(ref==link(ROOT/ref['path']),'CPU allocation series binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['diagnostic_only'] and not diagnosis['qualification_passed'] and
             diagnosis['new_guests']==3 and diagnosis['new_builds']==0 and
             [row['index'] for row in diagnosis['results']]==[1,2,3],'CPU allocation series counted only')
        for row in diagnosis['results']:
            need(row['measured'] and row['new_guests']==1 and row['new_builds']==0 and
                 row['outcome']=='inconclusive_not_reproduced' and 0<row['guest_elapsed']<=20,'CPU allocation series row')
            total+=1;spent+=row['guest_elapsed']
    if 'dual_admission' in frozen:
        admission=read(ROOT/frozen['dual_admission']['path']);ref=admission['case6_diagnosis']
        need(ref==link(ROOT/ref['path']),'CPU dual case6 diagnostic binding')
        diagnosis=read(ROOT/ref['path'])
        need(diagnosis['closed'] and diagnosis['measured'] and diagnosis['diagnostic_only'] and
             not diagnosis['qualification_passed'] and diagnosis['new_guests']==1 and diagnosis['new_builds']==0 and
             0<diagnosis['guest_elapsed']<=23,'CPU dual diagnostic counted only')
        total+=1;spent+=diagnosis['guest_elapsed']
    for fatal,base in ((False,BASE/'guests'),(True,BASE/'fatal-guests')):
        attempts=[(p,read(p)) for p in base.glob('attempt-*/summary.json')]
        need(bool(attempts) and all(r.get('closed') for _,r in attempts),'CPU closed matrices')
        total+=sum(len(r['cases']) for _,r in attempts);spent+=sum(r['guest_elapsed'] for _,r in attempts)
        values=[(p,r) for p,r in attempts if r['candidate']==frozen['candidate']]
        need(len(values)==1,'CPU unique runtime matrix');path,result=values[0]
        need(result['passed'] and result['fatal']==fatal and result['image_sha256']==digest(image) and
             0<result['guest_elapsed']<=(40 if fatal else 240),'CPU matrix identity/result/deadline')
        need((result['allocations'],result['child_sha256'])==(count,sha),'CPU actual image allocation binding')
        expected=[(k,4096) for k in runtime.FATAL_CASES] if fatal else list(runtime.CASES)
        need([(r['case'],r['ram']) for r in result['cases']]==expected,'CPU complete matrix')
        matrices.append(link(path));current_spent+=result['guest_elapsed']
        for row in result['cases']:
            need(row['passed'] and 0<row['elapsed']<=20,'CPU per-guest deadline')
            folder=path.parent/f'guest-{row["case"]}-{row["ram"]}'
            need(not (folder/'release-failure.json').exists() and not (folder/'release-failure.json').is_symlink(),'CPU failed release cannot qualify')
            serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
            need((folder/'frame-trace.log').stat().st_size<=65536,'CPU bounded text trace')
            tasks=runtime.validate_fatal(serial,trace,row['case'],folder) if fatal else len(runtime.validate_capture(serial,trace,row['case'],row['oom'],count,sha,folder))
            need(tasks==row['tasks'],'CPU task ledger')
            metrics=read(folder/'capture-metrics.json')
            need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
                 metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','CPU guest closure')
            if not fatal:
                reads=runtime.binary_capacity(folder)
                need([r['equivalence'] for r in reads if r['equivalence'] is not None]==['kernel','high'],'CPU independent same-stop equivalence')
                for index,r in enumerate(reads,1):
                    dump=folder/'binary-memory'/r['file']
                    need(r['sequence']==index and dump.name==f'ram-{index:04d}.bin' and dump.stat().st_size==r['bytes'] and digest(dump)==r['sha256'],'CPU full RAM bytes')
            for f in folder.rglob('*'):
                if f.is_file():
                    need(not f.is_symlink(),'CPU evidence symlink');evidence[f.relative_to(ROOT).as_posix()]=digest(f)
    need((total,spent)==matrix_budget(frozen['candidate'],True),'CPU cumulative guest budget')
    return dict(passed=True,kind='review',candidate=frozen['candidate'],gates=gates,matrices=matrices,evidence_sha256=evidence,
        cases=14,guest_elapsed=current_spent,total_guest_attempts=total,total_guest_elapsed=spent,new_builds=0,new_guests=0,scope=sorted(frozen['sources']))


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--defaults',action='store_true');group.add_argument('--review',action='store_true');args=parser.parse_args()
    kind='defaults' if args.defaults else 'review';started=time.monotonic();result=dict(passed=False,kind=kind)
    path=BASE/(kind+'-'+uuid.uuid4().hex+'.json')
    try:
        result=defaults() if args.defaults else review();print('SERVICE_CPU_'+kind.upper()+'_OK',flush=True);return 0
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result['error']=str(error);print('SERVICE_CPU_'+kind.upper()+'_FAIL '+str(error),flush=True);return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,6)
        with path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
        print('SERVICE_CPU_RECEIPT '+str(path),flush=True)


if __name__=='__main__':raise SystemExit(main())
