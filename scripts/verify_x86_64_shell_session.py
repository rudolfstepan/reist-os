"""Frozen AY gates, one image and one complete bounded runtime matrix."""
from pathlib import Path
import argparse,hashlib,json,shlex,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
from verify_x86_64_service_console import disabled
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'build/codex-agent/r83ay-shell-session'
BASE=PARENT/'candidate17'
PREVIOUS=PARENT/'candidate16'
BUILD=PARENT/'diagnostic30'
EXT2_FILES={'userspace/storage/lib/vfs_shadow_ext2.c','test/test_vfs_shadow_ext2_host.c',
            'test/test_reist_vfs_shadow_ext2.py'}
CORRECTION={'scripts/verify_x86_64_shell_session.py','test/test_x86_64_shell_session.py',
            'scripts/run_qemu_x86_64_shell_session.py'}
IMAGE=PARENT/'native-read-tickets/x86_64/reist-x86_64-bootstrap.elf'
BASELINE='f7566ac32c7500b6f7e6ca0b799b01ee78814e29'
PRIOR=ROOT/'build/codex-agent/r83ax-session-admission/candidate06/verification-status-session-final.json'
PRIOR_SHA='231d1df92e6eedf2ded04fd3a1bb5de14439a902d51db156ab66a2b96c9d7c13'
DOCS={'automation/reist-s03b.toml','docs/architecture/NATIVE_SHELL_SESSION_CONTRACT.md',
      'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
LIMITS=(300,300,300,900,180,180,900,180,180,180)
DIAGNOSTIC=PARENT/'diagnostic38'
TICKET_EVIDENCE=PARENT/'diagnostic30'
TICKET_IMAGE=PARENT/'native-read-tickets/x86_64/reist-x86_64-bootstrap.elf'
TICKET_BUILD=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
              '-NativeShellSession','-OutputDirectory','build/codex-agent/r83ay-shell-session/native-read-tickets']
TICKET_HOST=ROOT/'build/codex-agent/r83ay-development-persistent-target-green38.log'
TICKET_HOST_SHA='85ae797d8781eee771cdd7fc7abb63c9a43bd45ffa37c59e14a6ae61794b5e50'
DIAGNOSTIC_CHANGED=DOCS|{'scripts/run_qemu_x86_64_shell_session.py',
                       'scripts/verify_x86_64_shell_session.py','test/test_x86_64_shell_session.py'}
FIX=PARENT/'correction28'
FIX_IMAGE=PARENT/'native-oom-ordering/x86_64/reist-x86_64-bootstrap.elf'
FIX_HOST=['python','test/test_x86_64_shell_session.py',
          'ShellSessionTests.test_actual_normal_shell_and_session_platform',
          'ShellSessionTests.test_actual_cold_probe_dispatch',
          'ShellSessionTests.test_oom_pause_raw_proof',
          'ShellSessionTests.test_oom_sleep_observer_is_selected_only','-v']
FIX_BUILD=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
           '-NativeShellSession','-OutputDirectory','build/codex-agent/r83ay-shell-session/native-oom-ordering']


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,indent=2,sort_keys=True)


def changed():
    return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))


def prior():
    need(digest(PRIOR)==PRIOR_SHA,'AY accepted AX receipt pin');old=read(PRIOR)
    need(old['accepted'] and old['clean_worktree'] and old['implementation_commit']=='69282e7613a67263beb7e659d5675b8301066e7d','AY accepted predecessor')
    verify_files(old['tools']);return old


def freeze12_legacy():
    need(git('rev-parse','HEAD')==BASELINE and not BASE.exists(),'AY fresh reuse qualification')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));package=queue['packages'][0]
    need(queue['active_id']==package['id']=='R8.3ay-shell-session' and package['status']=='active','AY active package')
    old=prior();edits=changed();need(set(edits)<=set(package['allowed_files']),'AY allowed changes')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'AY staging/whitespace')
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    need(digest(PREVIOUS/'frozen.json')=='a444875c938d36317df1735cb290c1ee7c4482f741427718e58e1ad9fff779da' and
         digest(PREVIOUS/'stopped.json')=='ade6cd2eade9241e0bc7ed054c963025718a68871ea83de992427cc1c4592834',
         'AY exact stopped candidate11')
    previous=read(PREVIOUS/'frozen.json')
    need(set(sources)==set(previous['sources']) and
         {n for n in sources if sources[n]!=previous['sources'][n]}<=DOCS|CORRECTION,
         'AY only command-context transport/test and proof/docs changed')
    need(digest(PARENT/'diagnostic16/result.json')=='a0383c793638c57b5af741a379808cd1414154bb77d247ee644717c4feda6dca',
         'AY exact successful unqualified ext2 control')
    summary=read(PREVIOUS/'guests/summary.json');stop=read(PREVIOUS/'stopped.json')
    need(stop['failed_gate']==7 and stop['image']==link(IMAGE) and summary['closed'] and not summary['passed'] and
         [(r['case'],r['passed']) for r in summary['cases']]==[(i,i<15) for i in range(16)] and
         summary['guest_elapsed']==327.4590193000913 and
         digest(IMAGE)=='514d890c41bd11f4ea6eeaf900ae30f59a317a27614e2f297d1b4452969c08e5',
         'AY all prior spent guests and exact fifth image')
    name='userspace/storage/lib/vfs_shadow_ext2.c'
    need(disabled((ROOT/name).read_text(),'REIST_NATIVE_SHELL_SESSION',False)==original(name),
         'AY exact old parser projection')
    import ast
    name='scripts/run_qemu_x86_64_shell_session.py'
    def validators(source):
        return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body
                if isinstance(n,ast.FunctionDef) and (n.name.startswith('validate') or n.name=='evaluate')}
    before=validators((PREVIOUS/'sources'/name).read_text())
    after=validators((ROOT/name).read_text())
    need(after==before,'AY all original raw predicates and PIO closure exact')
    diagnostic=PARENT/'diagnostic18'
    need(digest(diagnostic/'frozen.json')=='1c119ad366f9d0e8bd98bbb4529cc39e30d65c59bc0f8eb369b6c427415c96cf' and
         digest(diagnostic/'result.json')=='282d0276bd2e7c11c0a60ccf71bd3f433310837f487ad19d61381f867b6a39d7',
         'AY exact successful but unqualified diagnostic18; diagnostic17 failure retained')
    before=(diagnostic/'sources'/name).read_text();after=(ROOT/name).read_text()
    node=next(n for n in ast.parse(after).body if isinstance(n,ast.FunctionDef) and n.name=='command_probe_observer')
    after=after.replace(ast.get_source_segment(after,node)+'\n\n\n','')
    after=after.replace('body=command_probe_observer(hybrid_probe_observer(retirement_probe_observer(lifecycle_probe_observer(hardware_probe_observer(cold_probe_pc_diagnostic(body))))))',
                        'body=hybrid_probe_observer(retirement_probe_observer(lifecycle_probe_observer(hardware_probe_observer(cold_probe_pc_diagnostic(body)))))')
    need(after==before,'AY sole new transport override; callbacks, feeder, capture and all oracles exact')
    commands=package['targeted_tests']+package['package_tests']+package['runtime_tests']
    expected=list(previous['commands']);expected[5]='python scripts/verify_x86_64_shell_session.py --reuse-image'
    need(commands==expected and len(commands)==10 and
         package['subsystem_host_tests']==previous['package']['subsystem_host_tests'] and
         package['allowed_files']==previous['package']['allowed_files'],
         'AY original ten obligations plus approved ext2 hosts/scope')
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log')}
    for p in PARENT.rglob('*'):
        if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts):
            retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for p in (ROOT/'build/codex-agent/ext2-directory-host').rglob('*'):
        if p.is_file() and 'cache' not in p.parts:retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in edits:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    value=dict(head=BASELINE,package=package,changed=edits,sources=sources,tools=old['tools'],commands=commands,
        prior=link(PRIOR),retained=retained,candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        planned_image=IMAGE.relative_to(ROOT).as_posix(),previous_stop=link(PREVIOUS/'stopped.json'),
        image=link(IMAGE),build_receipt=link(BUILD/'gate-06.json'),
        previous_spent=dict(builds=5,guests=69,guest_seconds=1347.4950213001287),
        reserved=dict(builds=0,guests=18,guest_seconds=45,cleanup_seconds=3,total_guest_seconds=810))
    save(BASE/'frozen.json',value);binding();print('SHELL_SESSION_FROZEN',value['candidate'],flush=True)


def freeze15_legacy():
    import ast
    need(git('rev-parse','HEAD')==BASELINE and not BASE.exists(),'AY fresh explicit-step qualification')
    need(digest(BUILD/'frozen.json')=='6bacdae1721cd4fa2e51412bf52e1e3273fe8f6ae950b801c07c2af9083364bf' and
         digest(BUILD/'build.json')=='a48246a9baa5492b56c96b8eb244bfc4ba223a4f64ef3123fc44334f0bd5de30',
         'AY exact single seventh image build')
    control=PARENT/'diagnostic35'
    need(digest(control/'frozen.json')=='0a6a1c84775161f5b51e2bf18fcfbbc57c3a8547067b332101b57759e4d42c66' and
         digest(control/'result.json')=='8adb6d4db60bb954d3a369c061772e5b48eb0821adaa7a185cfdd293abfe4aa4',
         'AY exact full explicit-RET diagnosis, not qualification')
    old=read(control/'frozen.json');result=read(control/'result.json');previous=read(PREVIOUS/'frozen.json')
    need(result['passed'] and not result['qualification'] and result['observation']['passed'] and
         [(r['case'],r['passed']) for r in result['observation']['cases']]==[(13,True)] and
         result['observation']['guest_elapsed']==21.838239100005012 and result['image']==link(IMAGE),
         'AY actual verified instruction progress, no diagnostic promotion')
    need(digest(PREVIOUS/'stopped.json')=='73d05ac883fa2ae5cc901805de3455bef50a16f64fc12b7ac863b39457a1a4da' and
         digest(PARENT/'diagnostic31/result.json')=='540b788e4b9b2d1c0823000778c983fd2a0614ef23423016c6b9547994eff019',
         'AY failed acceptance and repeated-notification cause retained')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());package=queue['packages'][0]
    need(queue['active_id']==package['id']=='R8.3ay-shell-session' and package['status']=='active','AY active package')
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,
         'AY unchanged kernel/SDK, only explicit-step adapter/proof/tests and freeze/docs')
    name='scripts/run_qemu_x86_64_shell_session.py'
    before=(control/'sources'/name).read_text();after=(ROOT/name).read_text()
    def functions(source):
        return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    old_functions=functions(before);new_functions=functions(after)
    need(set(new_functions)==set(old_functions)|{'validate_probe_steps'},'AY sole additional raw step validator')
    for symbol in old_functions:
        if symbol not in {'observer','run_matrix','stepped_probe_observer','evaluate'}:
            need(new_functions[symbol]==old_functions[symbol],'AY exact old function '+symbol)
    need(new_functions['observer'].replace('        body=stepped_probe_observer(body)\n','')==old_functions['observer'],
         'AY normal observer only adds verified step transport')
    need(new_functions['run_matrix'].replace('(capture_namespace if diagnostic else stepped_capture_namespace)(started)',
         'capture_namespace(started)')==old_functions['run_matrix'],'AY sole post-reader capture selector')
    need(new_functions['evaluate'].replace("    steps=validate_probe_steps(trace,config['s'])\n",'').replace(',probe_steps=steps','')
         ==old_functions['evaluate'],'AY every old raw oracle exact, step proof additional')
    def support(source):
        node=ast.parse(source).body[0]
        return next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and
                    any(isinstance(t,ast.Name) and t.id=='support' for t in n.targets))
    old_support=support(old_functions['stepped_probe_observer']);new_support=support(new_functions['stepped_probe_observer'])
    need(old_support.split('        record=dict(')[0]==new_support.split('        site=tuple(')[0] and
         old_support[old_support.index('    except BaseException as error:'):]==new_support[new_support.index('    except BaseException as error:'):],
         'AY all actual step/register/progress/failure guards byte-exact; only compact receipt differs')
    host=ROOT/'build/codex-agent/r83ay-development-compact-step-green15.log'
    need(digest(host)=='73acb825d5c0d181c80b5fe2dcc1c5b7a44dbfefca1d0e1be29ba2f9cfdf6e1a',
         'AY four passed compact/raw/step/control/binary integration regressions')
    # Exercise the new decoder against retained actual transitions, not synthetic completion data.
    import run_qemu_x86_64_shell_session as run
    raw=(control/'guests/guest-13-2-4096/frame-trace.log').read_text();compact=[]
    for line in raw.splitlines():
        if not line.startswith('COLD_STEP '):continue
        row=json.loads(line[10:]);site=('request','denied','return').index(row['hook'].split('_')[-2])
        value={k:row[k] for k in ('step','pc','target','sp','after_sp')}|dict(site=site)
        compact.append('COLD_STEP_V1 '+json.dumps(value,separators=(',',':'))+'\n')
    config,_,_=run.image_config(IMAGE)
    need(len(compact)==822 and run.validate_probe_steps(''.join(compact)+'COLD_STEP_END_V1 822\n',config['s'])==822,
         'AY offline decoder regression on actual step rows; supplied test terminator is not guest evidence')
    need(all(package[k]==old['package'][k]==previous['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),
         'AY exact ten gate obligations and eighteen-case acceptance')
    edits=changed();need(set(edits)<=set(package['allowed_files']) and not git('diff','--cached','--name-only') and
                         not git('diff','--check'),'AY corrected-image scope/staging')
    prior();verify_files(old['tools']);verify_files(old['retained']);default_projection()
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in edits:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    commands=package['targeted_tests']+package['package_tests']+package['runtime_tests']
    need(commands==previous['commands'] and len(commands)==10,'AY frozen command order')
    save(BASE/'frozen.json',dict(head=BASELINE,package=package,changed=edits,sources=sources,tools=old['tools'],
        commands=commands,prior=link(PRIOR),retained=retained,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        planned_image=IMAGE.relative_to(ROOT).as_posix(),previous_stop=link(PREVIOUS/'stopped.json'),
        image=link(IMAGE),build_receipt=link(BUILD/'build.json'),
        previous_spent=dict(builds=7,guests=108,guest_seconds=2146.2288713001476,
                            prelaunch_attempts=1,prelaunch_seconds=0.38712120000855066),
        reserved=dict(builds=0,guests=18,guest_seconds=45,cleanup_seconds=3,total_guest_seconds=810)))
    binding();print('SHELL_SESSION_FROZEN',flush=True)


def freeze():
    need(git('rev-parse','HEAD')==BASELINE and not BASE.exists(),'AY fresh persistent-target qualification')
    control=PARENT/'diagnostic38'
    need(digest(control/'frozen.json')=='1271fb13af5df6a1d069bdecb5af48cda6917f5a9bb160d1de80b6ff81eb95cd' and
         digest(control/'result.json')=='af03796c800fc922afc0b5fe0eac6ff5143f004ed6076cd5140cac610b00c2c0',
         'AY exact successful long target diagnosis')
    old=read(control/'frozen.json');result=read(control/'result.json');previous=read(PREVIOUS/'frozen.json')
    need(result['passed'] and not result['qualification'] and result['observation']['passed'] and
         [(r['case'],r['passed'],r['proof']['probe_steps']) for r in result['observation']['cases']]==
         [(6,True,2437)] and
         result['observation']['guest_elapsed']==36.573199900012696 and result['image']==link(IMAGE),
         'AY complete long actual-target diagnosis, no acceptance promotion')
    need(digest(PREVIOUS/'frozen.json')=='de46e5dbcb448083323cfc3dc63344bc9a577f6a485fa3f458b84f0c1fddb3ec' and
         digest(PREVIOUS/'stopped.json')=='5d8504b0a96a641b89034dbb5b52552f719c315cd67f50e0089c7469003ead26',
         'AY retained failed long qualification')
    need(digest(BUILD/'frozen.json')=='6bacdae1721cd4fa2e51412bf52e1e3273fe8f6ae950b801c07c2af9083364bf' and
         digest(BUILD/'build.json')=='a48246a9baa5492b56c96b8eb244bfc4ba223a4f64ef3123fc44334f0bd5de30' and
         read(BUILD/'build.json')['image']==link(IMAGE),'AY exact seventh build/image')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());package=queue['packages'][0]
    need(queue['active_id']==package['id']=='R8.3ay-shell-session' and package['status']=='active','AY active package')
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DOCS|
         {'scripts/run_qemu_x86_64_shell_session.py','scripts/verify_x86_64_shell_session.py','test/test_x86_64_shell_session.py'},
         'AY sole transport mode and host expectation delta')
    name='scripts/run_qemu_x86_64_shell_session.py'
    before=(control/'sources'/name).read_text();after=(ROOT/name).read_text()
    selected="    return ('set breakpoint always-inserted on\\nset logging file '"
    need(after.count(selected)==1 and after.replace(selected,
         "    return ('set breakpoint always-inserted off\\nset logging file '")==before,
         'AY sole normal insertion-mode line; all guards/targets/oracles exact')
    name='test/test_x86_64_shell_session.py'
    before=(control/'sources'/name).read_text();after=(ROOT/name).read_text()
    selected='self.assertIn("set breakpoint always-inserted on",inspect.getsource(session.observer))'
    need(after.count(selected)==1 and after.replace(selected,selected.replace(' on',' off'))==before,
         'AY sole matching host expectation change')
    need(digest(TICKET_HOST)==TICKET_HOST_SHA,'AY passed sole-mode host regression')
    need(all(package[k]==old['package'][k]==previous['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),
         'AY unchanged ten gate obligations and full matrix')
    edits=changed();need(set(edits)<=set(package['allowed_files']) and not git('diff','--cached','--name-only') and
                         not git('diff','--check'),'AY scope/staging')
    prior();verify_files(old['tools']);verify_files(old['retained']);default_projection()
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in edits:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    commands=package['targeted_tests']+package['package_tests']+package['runtime_tests']
    need(commands==previous['commands'] and len(commands)==10,'AY frozen gate order')
    save(BASE/'frozen.json',dict(head=BASELINE,package=package,changed=edits,sources=sources,tools=old['tools'],
        commands=commands,prior=link(PRIOR),retained=retained,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        planned_image=IMAGE.relative_to(ROOT).as_posix(),previous_stop=link(PREVIOUS/'stopped.json'),
        image=link(IMAGE),build_receipt=link(BUILD/'build.json'),
        previous_spent=dict(builds=7,guests=123,guest_seconds=2492.493842600176,
                            prelaunch_attempts=1,prelaunch_seconds=0.38712120000855066),
        reserved=dict(builds=0,guests=18,guest_seconds=45,cleanup_seconds=3,total_guest_seconds=810)))
    binding();print('SHELL_SESSION_FROZEN',flush=True)


def reuse_image():
    import run_qemu_x86_64_shell_session as run
    f=binding();previous=read(BUILD/'frozen.json');gate=read(BUILD/'build.json')
    need(digest(BUILD/'frozen.json')=='6bacdae1721cd4fa2e51412bf52e1e3273fe8f6ae950b801c07c2af9083364bf',
         'AY exact original seventh-image build candidate')
    need(f['build_receipt']==link(BUILD/'build.json') and gate['passed'] and gate['exit_code']==0 and
         gate['candidate']==previous['candidate'] and gate['command']==previous['build_command'] and
         gate['log']==link(ROOT/gate['log']['path']),'AY exact passed historical build')
    need(f['image']==gate['image']==link(IMAGE) and digest(IMAGE)=='6f2667fc02810c9af2962e39cf023dde9659bc782997ec0ea3c5c84715a59295',
         'AY exact existing image')
    need(set(f['sources'])==set(previous['sources']) and
         {n for n in f['sources'] if f['sources'][n]!=previous['sources'][n]}<=DIAGNOSTIC_CHANGED,
         'AY complete unchanged production inputs')
    verify_files(previous['tools'])
    config,records,app=run.image_config(IMAGE)
    need(set(records)=={2,3,4} and 64<=len(app)<=1280 and config['selection']!=config['policy'],
         'AY inner/outer ELF and actual shell/catalog bindings')
    return dict(passed=True,builds=0,image=link(IMAGE),historical_build=f['build_receipt'],
                complete_production_sources_unchanged=True,elf_and_catalog_verified=True)


def binding():
    f=read(BASE/'frozen.json');need(git('rev-parse','HEAD')==f['head']==BASELINE,'AY frozen HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    need(queue['active_id']==f['package']['id'] and queue['packages'][0]==f['package'],'AY frozen contract')
    verify_files(f['sources']);verify_files(f['tools']);verify_files(f['retained'])
    need(changed()==f['changed'] and set(f['changed'])<=set(f['package']['allowed_files']),'AY exact source scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'AY staging/whitespace')
    need(hashlib.sha256(json.dumps(f['sources'],sort_keys=True).encode()).hexdigest()==f['candidate'] and
         link(PRIOR)==f['prior'],'AY exact candidate/predecessor');return f


def original(name):
    return subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=10).decode('utf-8').replace('\r\n','\n')


def diagnostic25_freeze_legacy():
    import ast
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh stop-provenance diagnostic')
    prior_diagnostic=PARENT/'diagnostic24'
    need(digest(prior_diagnostic/'frozen.json')=='3cb8e89c2636f5a47059fa3a6ba4723d5afab136b18e3c33e40657dc148e44f8' and
         digest(prior_diagnostic/'result.json')=='5efddf62f0a0248776012aac43f5259205234229e971c7e2269fdbc8d4321785',
         'AY exact stopped late-audit control24')
    observation=read(prior_diagnostic/'guests/summary.json')
    need(not observation['passed'] and not observation['qualification'] and observation['closed'] and
         [(r['case'],r['passed']) for r in observation['cases']]==[(0,False)] and
         observation['guest_elapsed']==13.384179499989841 and
         observation['error']=='session feeder incomplete prior run','AY preserved root-quota diagnostic')
    name='scripts/run_qemu_x86_64_shell_session.py'
    need(digest(ROOT/name)==read(prior_diagnostic/'frozen.json')['sources'][name],
         'AY identical observer/feeder/oracles; only select normal capture without extra QEMU trace')
    need(digest(BASE/'stopped.json')=='78d948a25e033532ac79f4a2538997804ac28f3ffc04e9163f5d6d1f4518e67e',
         'AY exact candidate12 failed stop')
    old=read(BASE/'frozen.json');summary=read(BASE/'guests/summary.json')
    need(old['candidate']=='50c436bb3817e9accfb16018cc72c6d18f8ef34d87f71eb459d55d97347b7220' and
         summary['closed'] and not summary['passed'] and summary['guest_elapsed']==140.03139020004892 and
         [(r['case'],r['passed']) for r in summary['cases']]==[(n,n<5) for n in range(6)] and
         link(IMAGE)==old['image'],'AY retained six attempts and exact fifth image')
    package=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())['packages'][0]
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,'AY immutable production')
    name='scripts/run_qemu_x86_64_shell_session.py'
    after=(ROOT/name).read_text()
    for symbol in ('ProbeAudit','audit_probe_observer','continuation_capture_namespace','watch_pending_observer'):
        node=next(n for n in ast.parse(after).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==symbol)
        after=after.replace(ast.get_source_segment(after,node)+'\n\n\n','')
    need(after==(BASE/'sources'/name).read_text(),'AY only diagnostic adapter added; full observer/oracles exact')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),'AY unchanged acceptance')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'AY diagnostic staging/whitespace')
    verify_files(old['tools']);verify_files(old['retained'])
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=DIAGNOSTIC/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    value=dict(sources=sources,retained=retained,tools=old['tools'],changed=changed(),package=package,
        head=BASELINE,image=link(IMAGE),stop=link(BASE/'stopped.json'),
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=5,guests=81,guest_seconds=1610.6604701001493),
        reserved=dict(builds=0,guests=2,cases=[17,0],guest_seconds=45,cleanup_seconds=3,
                      total_guest_seconds=90,host_seconds=180),qualification=False)
    save(DIAGNOSTIC/'frozen.json',value);diagnostic_binding()
    print('SHELL_SESSION_DIAGNOSTIC_FROZEN',value['candidate'],flush=True)


def diagnostic18_freeze_legacy():
    previous=PARENT/'diagnostic17'
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh request-identity diagnostic')
    need(digest(previous/'frozen.json')=='ab000d6daa128a5c6d9cbbfbe8bc3408c462f34dbb55a544a2d426c9de247949' and
         digest(previous/'result.json')=='82e573196b84d50019816a0fa4464b23e0548834a8554a261f6c13968875c040',
         'AY exact diagnostic17 assertion location')
    old=read(previous/'frozen.json');summary=read(previous/'guests/summary.json')
    need(not read(previous/'result.json')['passed'] and summary['closed'] and not summary['passed'] and
         [(r['case'],r['passed']) for r in summary['cases']]==[(15,False)] and
         summary['guest_elapsed']==18.193377499992494 and link(IMAGE)==old['image'],'AY retained diagnostic and image')
    package=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())['packages'][0]
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,'AY immutable production')
    name='scripts/run_qemu_x86_64_shell_session.py'
    before=(previous/'sources'/name).read_text();after=(ROOT/name).read_text()
    guard="    assert gen in starts and starts[gen]['live'] and gen not in pending"
    suffix=", ('request s=%s g=%s op=%s live=%s pending=%s' % (slot,gen,op,starts.get(gen,{}).get('live'),pending.get(gen,{}).get('op')))"
    need(after.count(guard+suffix)==1 and after.replace(guard+suffix,guard)==before,
         'AY sole added failure message; predicate and healthy path exact')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),'AY unchanged full acceptance')
    verify_files(old['tools']);verify_files(old['retained'])
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=DIAGNOSTIC/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    value=dict(sources=sources,retained=retained,tools=old['tools'],changed=changed(),package=package,
        head=BASELINE,image=link(IMAGE),stop=link(BASE/'stopped.json'),
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=5,guests=68,guest_seconds=1325.1971648001347),
        reserved=dict(builds=0,guests=1,guest_seconds=45,cleanup_seconds=3,host_seconds=90),qualification=False)
    save(DIAGNOSTIC/'frozen.json',value);diagnostic_binding()
    print('SHELL_SESSION_DIAGNOSTIC_FROZEN',value['candidate'],flush=True)


def diagnostic17_freeze_legacy():
    import ast
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh single-case failure diagnostic')
    need(digest(BASE/'frozen.json')=='a444875c938d36317df1735cb290c1ee7c4482f741427718e58e1ad9fff779da' and
         digest(BASE/'stopped.json')=='ade6cd2eade9241e0bc7ed054c963025718a68871ea83de992427cc1c4592834',
         'AY exact candidate11 stopped observer assertion')
    old=read(BASE/'frozen.json');summary=read(BASE/'guests/summary.json')
    need(summary['closed'] and not summary['passed'] and
         [(r['case'],r['passed']) for r in summary['cases']]==[(i,i<15) for i in range(16)] and
         summary['guest_elapsed']==327.4590193000913 and
         link(IMAGE)==old['image'],'AY exact full prefix and immutable fifth image')
    package=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())['packages'][0]
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,'AY diagnostic unchanged production')
    def projection(source):
        import re
        lines=source.splitlines(keepends=True)
        for n in reversed(ast.parse(source).body):
            if isinstance(n,ast.FunctionDef) and n.name in ('static_failure_context','static_probe_observer'):
                del lines[n.lineno-1:n.end_lineno]
        return re.sub(r'\n{3,}','\n\n',''.join(lines))
    name='scripts/run_qemu_x86_64_shell_session.py'
    need(projection((BASE/'sources'/name).read_text())==projection((ROOT/name).read_text()),
         'AY only static failure formatter/wiring; no oracle, input, guest or callback change')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),
         'AY complete gates and scope retained')
    verify_files(old['tools']);verify_files(old['retained'])
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=DIAGNOSTIC/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    value=dict(sources=sources,retained=retained,tools=old['tools'],changed=changed(),package=package,
        head=BASELINE,image=link(IMAGE),stop=link(BASE/'stopped.json'),
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=5,guests=67,guest_seconds=1307.0037873001422),
        reserved=dict(builds=0,guests=1,guest_seconds=45,cleanup_seconds=3,host_seconds=90),qualification=False)
    save(DIAGNOSTIC/'frozen.json',value);diagnostic_binding()
    print('SHELL_SESSION_DIAGNOSTIC_FROZEN',value['candidate'],flush=True)


def diagnostic16_freeze_legacy():
    import ast
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh ext2 control')
    need(digest(BASE/'frozen.json')=='bd7ba487ca6bf0f7696f7556f957cc33049ee8b466646aec94a975f9d9dd70a2' and
         digest(BASE/'stopped.json')=='3aa9bac38cb26618a00b85ac2942bfdf1e45c66d2f2eb8bb2807130e89ca2fa9',
         'AY exact candidate05 ext2 stop')
    old=read(BASE/'frozen.json');stop=read(BASE/'stopped.json');summary=read(BASE/'guests/summary.json')
    need(stop['failed_gate']==7 and stop['image']==link(IMAGE) and
         [(r['case'],r['passed']) for r in summary['cases']]==[(0,True),(1,True),(2,False)] and
         not summary['passed'] and summary['closed'],'AY retained full runtime prefix and failure')
    need(digest(IMAGE)=='04780f7103c5670c3cd8c9ff9268c9b97c9e818398ae6b6c8d9fc35a4e0c4052','AY immutable image')
    package=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())['packages'][0]
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,'AY unchanged production')
    name='scripts/run_qemu_x86_64_shell_session.py'
    def project(source):
        n=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='diagnostic_commands')
        lines=source.splitlines(keepends=True);return ''.join(lines[:n.lineno-1]+lines[n.end_lineno:])
    need(project((BASE/'sources'/name).read_text())==project((ROOT/name).read_text()),
         'AY only diagnostic layout entry; full runtime/oracle exact')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),
         'AY unchanged complete scope/gates')
    verify_files(old['tools']);verify_files(old['retained'])
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=DIAGNOSTIC/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    value=dict(sources=sources,retained=retained,tools=old['tools'],changed=changed(),package=package,
        head=BASELINE,image=link(IMAGE),stop=link(BASE/'stopped.json'),
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=3,guests=21,guest_seconds=312.56778849996044),
        reserved=dict(builds=0,guests=1,guest_seconds=45,cleanup_seconds=3),qualification=False)
    save(DIAGNOSTIC/'frozen.json',value);diagnostic_binding()
    print('SHELL_SESSION_DIAGNOSTIC_FROZEN',value['candidate'],flush=True)


def diagnostic15_freeze_legacy():
    import ast
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh diagnostic')
    need(digest(BASE/'frozen.json')=='c6c4e78e7fa7d8ea3346cdb254b2fc8fbdd3428781059926975b29e1dd02b3ee' and
         digest(BASE/'stopped.json')=='154ecf76acaf5ebf5b0322780c7f790c753bdacbb1201860f7fc47d509016d68',
         'AY exact candidate04 feeder stop')
    old=read(BASE/'frozen.json');stop=read(BASE/'stopped.json')
    need(digest(PARENT/'diagnostic14/result.json')=='2bdaea08cb6cf1359b5c3fe1fbdf03f08952c6988e620342549df293b5555efd',
         'AY retained untraced command control')
    need(digest(PARENT/'diagnostic13/result.json')=='4081b23ee2825ed335af13a9c14d6fb02381c9061ceda1af2cea9f57f6964937',
         'AY retained full hybrid quota stop')
    need(digest(PARENT/'diagnostic12/result.json')=='d2edffcd843fec2e55d4d2afe8284fac98df589cc97b4a5bc75cdf5b90f05d65',
         'AY retained hybrid binding stop')
    need(digest(PARENT/'diagnostic11/result.json')=='fdc975f90eb1aaccd3f3c52e010973f338a1c6c7a459a76e309f7e2d847e55d9',
         'AY retained command-feeder diagnostic')
    need(stop['failed_gate']==7 and stop['image']==link(IMAGE) and
         digest(IMAGE)=='04780f7103c5670c3cd8c9ff9268c9b97c9e818398ae6b6c8d9fc35a4e0c4052','AY unchanged third image')
    package=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())['packages'][0]
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,'AY diagnostic immutable production')
    name='scripts/run_qemu_x86_64_shell_session.py'
    before=(BASE/'sources'/name).read_text();after=(ROOT/name).read_text()
    def project(source):
        tree=ast.parse(source)
        feeder=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SessionFeeder')
        pump=next(n for n in feeder.body if isinstance(n,ast.FunctionDef) and n.name=='pump')
        lines=source.splitlines(keepends=True)
        return ''.join(lines[:pump.lineno-1]+lines[pump.end_lineno:])
    hybrid=next(n for n in ast.parse(after).body if isinstance(n,ast.FunctionDef) and n.name=='hybrid_probe_observer')
    after=after.replace(ast.get_source_segment(after,hybrid)+'\n\n\n','')
    for name in ('DiagnosticCommandFeeder','diagnostic_commands','retirement_probe_observer'):
        node=next(n for n in ast.parse(after).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
        after=after.replace(ast.get_source_segment(after,node)+'\n\n\n','')
    after=after.replace('if lifecycle_probes:body=hybrid_probe_observer(retirement_probe_observer(lifecycle_probe_observer(body)))',
                        'if lifecycle_probes:body=deferred_read_observer(lifecycle_probe_observer(body))')
    need(project(before)==project(after),'AY only feeder and hybrid transport; all validators exact')
    need(package['allowed_files']==old['package']['allowed_files'] and
         all(package[k]==old['package'][k] for k in ('targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),
         'AY unchanged scope and full frozen gates')
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    value=dict(sources=sources,retained=retained,tools=old['tools'],changed=changed(),package=package,
               head=BASELINE,image=link(IMAGE),stop=link(BASE/'stopped.json'),
               candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
               previous_spent=dict(builds=3,guests=17,guest_seconds=243.48874109995086),
               reserved=dict(builds=0,guests=1,guest_seconds=45,cleanup_seconds=3),
               qualification=False)
    save(DIAGNOSTIC/'frozen.json',value);diagnostic_binding()
    print('SHELL_SESSION_DIAGNOSTIC_FROZEN',value['candidate'],flush=True)


def diagnostic35_freeze_legacy():
    import ast
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh explicit-RET diagnosis')
    need(digest(BASE/'frozen.json')=='cc21bd3dbc8a7965cd170147c46063b9b18cd9173fe4c2601dc101c97e414134' and
         digest(BASE/'stopped.json')=='73d05ac883fa2ae5cc901805de3455bef50a16f64fc12b7ac863b39457a1a4da',
         'AY exact failed candidate14; default insertion mode not a repair')
    previous=PARENT/'diagnostic34'
    need(digest(previous/'frozen.json')=='002e8b8d43b4cbf4299d649c1c5efb21b0becf7ca88b7c0af191a35d95db65f8' and
         digest(previous/'result.json')=='93456e2c99b785b4d73315f18ab6bf5a4f40827d5e474ee4a09aa2103131f892',
         'AY exact binary-adapter prelaunch rejection')
    need(digest(PARENT/'diagnostic31/result.json')=='540b788e4b9b2d1c0823000778c983fd2a0614ef23423016c6b9547994eff019' and
         digest(TICKET_EVIDENCE/'build.json')=='a48246a9baa5492b56c96b8eb244bfc4ba223a4f64ef3123fc44334f0bd5de30',
         'AY exact repeated-notification evidence and seventh build')
    old=read(previous/'frozen.json');summary=read(BASE/'guests/summary.json')
    need(summary['closed'] and not summary['passed'] and
         [(r['case'],r['passed']) for r in summary['cases']]==[(n,n<13) for n in range(14)] and
         summary['guest_elapsed']==283.2625752000022 and old['image']==link(IMAGE),
         'AY retained fourteen qualification guests and exact seventh image')
    spent=read(previous/'guests/summary.json')
    need(spent['closed'] and not spent['passed'] and spent['guest_elapsed']==0.38712120000855066 and
         [(r['case'],r['passed']) for r in spent['cases']]==[(13,False)],'AY retained prelaunch attempt')
    metrics=read(previous/'guests/guest-13-2-4096/capture-metrics.json')
    need(metrics['spawned'] is False and metrics['pid']==0 and metrics['error']=='binary observer shape' and
         not (previous/'guests/guest-13-2-4096/command.json').exists(),'AY no physical guest counted for prelaunch rejection')
    raw=(PARENT/'diagnostic31/guests/guest-15-2-4096/frame-trace.log').read_text()
    failures=[json.loads(line[len('PENDING_FAILURE '):]) for line in raw.splitlines() if line.startswith('PENDING_FAILURE ')]
    need(len(failures)==1 and failures[0]['read_ticket']==failures[0]['pending']['read_ticket']==[14,13] and
         failures[0]['slot']==0 and failures[0]['pending']['gen']==8 and failures[0]['tick']==572,
         'AY actual same request, no intervening request or return')
    build=read(TICKET_EVIDENCE/'build.json');built=read(TICKET_EVIDENCE/'frozen.json')
    need(build['passed'] and build['image']==link(TICKET_IMAGE) and
         build['command']==built['build_command']==TICKET_BUILD and build['candidate']==built['candidate'] and
         build['log']==link(ROOT/build['log']['path']), 'AY exact single seventh image')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());package=queue['packages'][0]
    need(queue['active_id']==package['id']=='R8.3ay-shell-session' and package['status']=='active','AY active diagnostic')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),'AY unchanged gates/scope')
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,
         'AY unchanged kernel/SDK and bounded diagnostic wrapper/test')
    name='scripts/run_qemu_x86_64_shell_session.py';after=ast.parse((ROOT/name).read_text())
    before=ast.parse((previous/'sources'/name).read_text())
    def loop_literal(tree,name):
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        return next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and
                    any(isinstance(t,ast.Name) and t.id=='loop' for t in n.targets))
    need(loop_literal(before,'stepped_loop_observer')==loop_literal(after,'step_loop_tail'),
         'AY bounded loop logic exactly retained')
    helpers={'stepped_loop_observer','step_loop_tail','stepped_capture_namespace'}
    for tree in (before,after):tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name not in helpers]
    need(ast.dump(before)==ast.dump(after),'AY all other adapter/callback/guard/oracle logic exact')
    need(not git('diff','--cached','--name-only') and not git('diff','--check') and
         set(changed())<=set(package['allowed_files']),'AY diagnostic scope/staging')
    verify_files(old['tools']);verify_files(old['retained']);default_projection()
    need(digest(TICKET_HOST)==TICKET_HOST_SHA,'AY passed real binary configure/capture integration without VM')
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=DIAGNOSTIC/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    save(DIAGNOSTIC/'frozen.json',dict(head=BASELINE,package=package,sources=sources,changed=changed(),
        tools=old['tools'],retained=retained,image=link(IMAGE),stop=link(BASE/'stopped.json'),qualification=False,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        host=link(TICKET_HOST),build_receipt=link(TICKET_EVIDENCE/'build.json'),ticket_image=link(TICKET_IMAGE),
        previous_spent=dict(builds=7,guests=107,guest_seconds=2124.3906322001426,
                            prelaunch_attempts=1,prelaunch_seconds=0.38712120000855066),
        reserved=dict(builds=0,guests=1,cases=[13],guest_seconds=45,cleanup_seconds=3,
                      total_guest_seconds=45,host_seconds=90)))
    diagnostic_binding();print('SHELL_SESSION_DIAGNOSTIC_FROZEN',flush=True)


def diagnostic_freeze():
    import ast
    import run_qemu_x86_64_shell_session as run
    need(not DIAGNOSTIC.exists() and git('rev-parse','HEAD')==BASELINE,'AY fresh persistent-target diagnosis')
    need(digest(BASE/'frozen.json')=='de46e5dbcb448083323cfc3dc63344bc9a577f6a485fa3f458b84f0c1fddb3ec' and
         digest(BASE/'stopped.json')=='5d8504b0a96a641b89034dbb5b52552f719c315cd67f50e0089c7469003ead26',
         'AY exact failed candidate16')
    old=read(BASE/'frozen.json');summary=read(BASE/'guests/summary.json')
    need(summary['closed'] and not summary['passed'] and
         [(r['case'],r['passed']) for r in summary['cases']]==[(n,n<6) for n in range(7)] and
         summary['guest_elapsed']==182.27384790001088,'AY retained seven qualification attempts')
    for index in range(1,7):need(read(BASE/f'gate-{index:02d}.json')['passed'],'AY retained preliminary gate')
    folder=BASE/'guests/guest-06-2-4096';raw=(folder/'frame-trace.log').read_text()
    metrics=read(folder/'capture-metrics.json')
    need(raw.count('COLD_STEP_V1 ')==2429 and 'OBSERVER_FAIL' not in raw and
         metrics['stop_reason']=='deadline' and metrics['observe_seconds']==42.008332 and
         metrics['debugger_cpu']==dict(kernel_ns=8843750000,user_ns=17062500000),
         'AY demonstrated debugger overhead, no instruction-progress failure')
    need(digest(TICKET_EVIDENCE/'build.json')=='a48246a9baa5492b56c96b8eb244bfc4ba223a4f64ef3123fc44334f0bd5de30' and
         read(TICKET_EVIDENCE/'build.json')['image']==link(IMAGE)==old['image'], 'AY immutable seventh image')
    config,_,_=run.image_config(IMAGE)
    need([config['s']['native_session_probe_'+n+'_site64'] for n in ('request','denied','return')]==
         [0xffffffff80110000,0xffffffff80110001,0xffffffff80110002], 'AY exact three one-byte probe filter')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());package=queue['packages'][0]
    need(queue['active_id']==package['id']=='R8.3ay-shell-session' and package['status']=='active','AY active package')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),'AY frozen gates/scope')
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=DIAGNOSTIC_CHANGED,'AY diagnostic-only source delta')
    name='scripts/run_qemu_x86_64_shell_session.py'
    before=ast.parse((BASE/'sources'/name).read_text());after=ast.parse((ROOT/name).read_text())
    additions=[n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='persistent_target_observer']
    need(len(additions)==1,'AY sole diagnostic insertion-mode wrapper')
    after.body.remove(additions[0])
    need(ast.dump(before)==ast.dump(after),'AY every normal callback/guard/oracle/capture unchanged')
    need(not git('diff','--cached','--name-only') and not git('diff','--check') and
         set(changed())<=set(package['allowed_files']),'AY scope and empty staging')
    verify_files(old['tools']);verify_files(old['retained']);default_projection()
    need(digest(TICKET_HOST)==TICKET_HOST_SHA,'AY exact sole mode-line regression with required target proof')
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=DIAGNOSTIC/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    save(DIAGNOSTIC/'frozen.json',dict(head=BASELINE,package=package,sources=sources,changed=changed(),
        tools=old['tools'],retained=retained,image=link(IMAGE),stop=link(BASE/'stopped.json'),qualification=False,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        host=link(TICKET_HOST),build_receipt=link(TICKET_EVIDENCE/'build.json'),ticket_image=link(TICKET_IMAGE),
        previous_spent=dict(builds=7,guests=122,guest_seconds=2455.920642700163,
                            prelaunch_attempts=1,prelaunch_seconds=0.38712120000855066),
        reserved=dict(builds=0,guests=1,cases=[6],guest_seconds=45,cleanup_seconds=3,
                      total_guest_seconds=45,host_seconds=90)))
    diagnostic_binding();print('SHELL_SESSION_DIAGNOSTIC_FROZEN',flush=True)


def diagnostic_binding():
    f=read(DIAGNOSTIC/'frozen.json');need(git('rev-parse','HEAD')==f['head']==BASELINE,'AY diagnostic HEAD')
    verify_files(f['sources']);verify_files(f['retained']);verify_files(f['tools'])
    need(changed()==f['changed'] and set(f['changed'])<=set(f['package']['allowed_files']) and
         not git('diff','--cached','--name-only') and not git('diff','--check'),'AY diagnostic scope/staging')
    need(link(IMAGE)==f['image'] and link(BASE/'stopped.json')==f['stop'] and
         hashlib.sha256(json.dumps(f['sources'],sort_keys=True).encode()).hexdigest()==f['candidate'],
         'AY diagnostic exact image/sources/stop')
    need(f['ticket_image']==link(TICKET_IMAGE) and f['build_receipt']==link(TICKET_EVIDENCE/'build.json'),
         'AY immutable reused seventh image/build')
    return f


def diagnostic35_legacy():
    import inspect
    import run_qemu_x86_64_shell_session as run
    from run_qemu_x86_64_runtime_clock import once
    f=diagnostic_binding();need(not (DIAGNOSTIC/'started.json').exists(),'AY no diagnostic retry')
    save(DIAGNOSTIC/'started.json',dict(candidate=f['candidate'],qualification=False,cases=f['reserved']['cases']))
    started=time.monotonic();result=dict(passed=False,qualification=False,candidate=f['candidate'])
    try:
        need(f['host']==link(TICKET_HOST) and digest(TICKET_HOST)==TICKET_HOST_SHA,
             'AY no repeated targeted host build')
        source=inspect.getsource(run.run_matrix)
        source=once(source,'for case,layout,ram in (CASES[:1] if diagnostic else CASES):',
                           'for case,layout,ram in (CASES[13],):')
        source=once(source,"time.monotonic()-begin<855 and summary['guest_elapsed']+45<=810",
                           "time.monotonic()-begin<45 and summary['guest_elapsed']+45<=45")
        source=once(source,"summary['guest_elapsed']<=810","summary['guest_elapsed']<=45")
        source=once(source,"time.monotonic()-begin<=900","time.monotonic()-begin<=90")
        source=once(source,"summary['qualification']=not diagnostic","summary['qualification']=False")
        namespace=dict(vars(run),observer=lambda *a,**kw:run.stepped_probe_observer(run.ticket_probe_observer(run.observer(*a,**kw))),
                       capture_namespace=run.stepped_capture_namespace)
        exec(compile(source,'<independent read tickets>','exec'),namespace)
        begin=time.monotonic()
        try:result['observation']=namespace['run_matrix'](TICKET_IMAGE,DIAGNOSTIC/'guests',f['candidate'],diagnostic_binding)
        finally:need(time.monotonic()-begin<=90,'AY diagnostic runtime host bound')
        need(result['observation']['passed'] and not result['observation']['qualification'],
             'AY diagnostic outcome never qualification')
        result['passed']=True;return 0
    except Exception as error:
        result['error']=repr(error);print('SHELL_SESSION_DIAGNOSTIC_FAIL',repr(error),flush=True);return 1
    finally:
        result.update(elapsed=time.monotonic()-started,image=link(TICKET_IMAGE) if TICKET_IMAGE.exists() else None)
        save(DIAGNOSTIC/'result.json',result)
        need(result['elapsed']<=90,'AY bounded explicit-RET runtime window')


def diagnostic():
    import inspect
    import run_qemu_x86_64_shell_session as run
    from run_qemu_x86_64_runtime_clock import once
    f=diagnostic_binding();need(not (DIAGNOSTIC/'started.json').exists(),'AY no diagnostic retry')
    save(DIAGNOSTIC/'started.json',dict(candidate=f['candidate'],qualification=False,cases=f['reserved']['cases']))
    started=time.monotonic();result=dict(passed=False,qualification=False,candidate=f['candidate'])
    try:
        need(f['host']==link(TICKET_HOST) and digest(TICKET_HOST)==TICKET_HOST_SHA,'AY retained host proof')
        source=inspect.getsource(run.run_matrix)
        source=once(source,'for case,layout,ram in (CASES[:1] if diagnostic else CASES):',
                           'for case,layout,ram in (CASES[6],):')
        source=once(source,'time.monotonic()-begin<855 and summary[\'guest_elapsed\']+45<=810',
                           'time.monotonic()-begin<45 and summary[\'guest_elapsed\']+45<=45')
        source=once(source,"summary['guest_elapsed']<=810","summary['guest_elapsed']<=45")
        source=once(source,'time.monotonic()-begin<=900','time.monotonic()-begin<=90')
        source=once(source,"summary['qualification']=not diagnostic","summary['qualification']=False")
        namespace=dict(vars(run),observer=lambda *a,**kw:run.persistent_target_observer(run.observer(*a,**kw)))
        exec(compile(source,'<persistent target insertion diagnosis>','exec'),namespace)
        result['observation']=namespace['run_matrix'](TICKET_IMAGE,DIAGNOSTIC/'guests',f['candidate'],diagnostic_binding)
        need(result['observation']['passed'] and not result['observation']['qualification'],'AY diagnosis never qualification')
        result['passed']=True;return 0
    except Exception as error:
        result['error']=repr(error);print('SHELL_SESSION_DIAGNOSTIC_FAIL',repr(error),flush=True);return 1
    finally:
        result.update(elapsed=time.monotonic()-started,image=link(TICKET_IMAGE))
        save(DIAGNOSTIC/'result.json',result)
        need(result['elapsed']<=90,'AY persistent-target runtime host bound')


def diagnostic16_legacy():
    import run_qemu_x86_64_shell_session as run
    f=diagnostic_binding();need(not (DIAGNOSTIC/'started.json').exists(),'AY no diagnostic retry')
    save(DIAGNOSTIC/'started.json',dict(candidate=f['candidate'],qualification=False))
    started=time.monotonic();result=dict(passed=False,qualification=False,candidate=f['candidate'])
    try:
        result['observation']=run.diagnostic_commands(IMAGE,DIAGNOSTIC/'guest',f['candidate'],diagnostic_binding,layout=2)
        observation=result['observation'];receipts=observation['receipts']
        need(observation['file_markers']==2 and observation['shell_banners']==2 and
             len([r for r in receipts if r['slot']==0 and r['status']==0 and r['state']==4])==2 and
             len([r for r in receipts if r['slot']==4 and r['status']==82 and r['state']==4])==2 and
             len([r for r in receipts if r['slot']==1 and r['status']==77 and r['state']==4])==2,
             'AY complete detached ext2 commands/app/root/peer')
        result['passed']=True
        return 0
    except Exception as error:
        result['error']=repr(error);print('SHELL_SESSION_DIAGNOSTIC_FAIL',repr(error),flush=True);return 1
    finally:
        result.update(elapsed=time.monotonic()-started,image=link(IMAGE))
        save(DIAGNOSTIC/'result.json',result)


def correction_freeze():
    import ast
    need(not FIX.exists() and not FIX_IMAGE.parent.parent.exists(),'AY fresh correction outputs')
    previous=PARENT/'diagnostic25'
    need(digest(previous/'frozen.json')=='114db9070e7e1d31ffa1172a6258fb5db7595155fdfdcd4d6b8d1ed3895e60b9' and
         digest(previous/'result.json')=='f3d44255233d8abebad115c6c1fba632dd4c8c29b0b60b1dc24f9692e6bb1822',
         'AY exact failed OOM ordering evidence')
    old=read(previous/'frozen.json');observation=read(previous/'guests/summary.json')
    need(not observation['passed'] and observation['closed'] and not observation['qualification'] and
         [(r['case'],r['passed']) for r in observation['cases']]==[(17,False)] and
         observation['guest_elapsed']==19.80013659998076,'AY retained spent diagnostic25')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());package=queue['packages'][0]
    need(queue['active_id']==package['id']=='R8.3ay-shell-session' and package['status']=='active',
         'AY correction remains sole active package')
    need(all(package[k]==old['package'][k] for k in
         ('allowed_files','targeted_tests','package_tests','runtime_tests','subsystem_host_tests')),
         'AY complete frozen gates and scope unchanged')
    names=set(git('ls-files').splitlines())|set(package['allowed_files'])
    sources={name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
    allowed=DIAGNOSTIC_CHANGED|{'userspace/sdk/lib/x86_64/shell_session.c',
        'arch/x86_64/proc/process_run.inc','test/x86_64_shell_session_host.c'}
    need(set(sources)==set(old['sources']) and
         {n for n in sources if sources[n]!=old['sources'][n]}<=allowed,'AY exact correction scope')
    name='scripts/run_qemu_x86_64_shell_session.py'
    def validators(source):
        return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body
                if isinstance(n,ast.FunctionDef) and (n.name.startswith('validate') or n.name=='evaluate')}
    before=validators((previous/'sources'/name).read_text());after=validators((ROOT/name).read_text())
    after.pop('validate_oom_pause')
    after['validate_capture']=after['validate_capture'].replace('    validate_oom_pause(combined,case)\n','')
    need(after==before,'AY every old raw predicate retained exactly')
    need(git('rev-parse','HEAD')==BASELINE and not git('diff','--cached','--name-only') and
         not git('diff','--check') and set(changed())<=set(package['allowed_files']),'AY clean scope/staging')
    verify_files(old['tools']);verify_files(old['retained'])
    need(link(IMAGE)==old['image'],'AY original fifth image retained')
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in PARENT.rglob('*')
              if p.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in p.parts)}
    for p in (ROOT/'build/codex-agent').glob('r83ay-development-*.log'):
        retained[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in changed():
        target=FIX/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    save(FIX/'frozen.json',dict(head=BASELINE,sources=sources,changed=changed(),tools=old['tools'],
        retained=retained,package=package,previous=link(previous/'result.json'),image=link(IMAGE),
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        commands=[FIX_HOST,FIX_BUILD],previous_spent=dict(builds=5,guests=82,guest_seconds=1630.46060670013),
        reserved=dict(builds=1,guests=1,cases=[17],host_seconds=300,build_seconds=180,
                      runtime_seconds=90,guest_seconds=45,cleanup_seconds=3),qualification=False))
    correction_binding();print('SHELL_SESSION_CORRECTION_FROZEN',flush=True)


def correction_binding():
    f=read(FIX/'frozen.json')
    need(git('rev-parse','HEAD')==f['head']==BASELINE and changed()==f['changed'] and
         not git('diff','--cached','--name-only') and not git('diff','--check'),'AY correction scope/HEAD')
    verify_files(f['sources']);verify_files(f['tools']);verify_files(f['retained'])
    need(hashlib.sha256(json.dumps(f['sources'],sort_keys=True).encode()).hexdigest()==f['candidate'] and
         link(IMAGE)==f['image'],'AY correction binding')
    if (FIX/'build.json').exists():
        b=read(FIX/'build.json');need(b['passed'] and b['image']==link(FIX_IMAGE),'AY single immutable new image')
    return f


def correction():
    import inspect
    import run_qemu_x86_64_shell_session as run
    from run_qemu_x86_64_runtime_clock import once
    f=correction_binding();need(not (FIX/'started.json').exists(),'AY no correction retry')
    save(FIX/'started.json',dict(candidate=f['candidate'],qualification=False))
    started=time.monotonic();result=dict(passed=False,qualification=False,candidate=f['candidate'])
    try:
        for name,command,limit in (('host',FIX_HOST,300),('build',FIX_BUILD,180)):
            correction_binding();begin=time.monotonic();log=FIX/(name+'.log')
            record=dict(command=command,limit=limit,passed=False,candidate=f['candidate'])
            try:
                with log.open('xb') as out:
                    child=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                record.update(passed=child.returncode==0,exit_code=child.returncode)
                if name=='build' and record['passed']:record['image']=link(FIX_IMAGE)
            except Exception as error:record['error']=repr(error)
            finally:
                record.update(elapsed=time.monotonic()-begin,log=link(log));save(FIX/(name+'.json'),record)
            print('SHELL_SESSION_CORRECTION',name,record['passed'],round(record['elapsed'],3),flush=True)
            need(record['passed'],'AY correction '+name+' failed: '+log.read_text(errors='replace')[-2500:])
        source=inspect.getsource(run.run_matrix)
        source=once(source,'for case,layout,ram in (CASES[:1] if diagnostic else CASES):',
                           'for case,layout,ram in (CASES[17],):')
        source=once(source,"time.monotonic()-begin<855 and summary['guest_elapsed']+45<=810",
                           "time.monotonic()-begin<45 and summary['guest_elapsed']+45<=45")
        source=once(source,"summary['qualification']=not diagnostic","summary['qualification']=False")
        ns=dict(vars(run));exec(compile(source,'<one OOM ordering correction guest>','exec'),ns)
        begin=time.monotonic()
        try:result['observation']=ns['run_matrix'](FIX_IMAGE,FIX/'guests',f['candidate'],correction_binding)
        finally:need(time.monotonic()-begin<=90,'AY correction runtime host limit')
        need(result['observation']['passed'] and not result['observation']['qualification'],
             'AY correction not qualification')
        result['passed']=True;return 0
    except Exception as error:
        result['error']=repr(error);print('SHELL_SESSION_CORRECTION_FAIL',repr(error),flush=True);return 1
    finally:
        result.update(elapsed=time.monotonic()-started,image=link(FIX_IMAGE) if FIX_IMAGE.exists() else None)
        save(FIX/'result.json',result)


def default_projection():
    from run_qemu_x86_64_runtime_clock import once
    from verify_x86_64_terminal import without_wide_build_selector
    from build_x86_64_wide_shell_media import without_wide_media_target
    names=('arch/x86_64/proc/cooperative_scheduler.asm','arch/x86_64/proc/process_run.inc',
           'arch/x86_64/proc/task_family.inc','arch/x86_64/kernel/bootstrap_core.c','userspace/sdk/lib/x86_64/shell_platform.c',
           'userspace/storage/lib/vfs_shadow_ext2.c')
    for name in names:
        after=disabled((ROOT/name).read_text(encoding='utf-8'),'REIST_NATIVE_SHELL_SESSION',name.endswith(('.inc','.asm')))
        need(after==original(name),'AY disabled production exact '+name)
    name='Makefile';after=without_wide_build_selector(without_wide_media_target((ROOT/name).read_text(encoding='utf-8')),make=True)
    # Accepted AZ adds a separate packaging target, not a default recipe change.
    # Match its full body, not a wildcard section that could hide altered rules.
    if 'x86_64-shell-media' in after:
        az=('\n# AZ packaging only: explicit already-built ShellSession input; no kernel dependency.\n'
            '.PHONY: x86_64-shell-media\n'
            'X86_64_SHELL_MEDIA_INPUT ?= build/x86_64\n'
            'X86_64_SHELL_MEDIA_OUTPUT ?= build/codex-agent/native-shell-media\n'
            'x86_64-shell-media:\n'
            '\t@$(PYTHON) scripts/build_x86_64_shell_media.py --input-directory "$(X86_64_SHELL_MEDIA_INPUT)" --output-directory "$(X86_64_SHELL_MEDIA_OUTPUT)" --nasm "$(AS)" --openssl "$(OPENSSL)"\n'
            '# End AZ packaging-only target.\n')
        after=once(after,az,'')
    first=after[after.index('X86_64_NATIVE_SHELL_SESSION ?= 0\n'):after.index('ifneq ($(words $(X86_64_NATIVE_SESSION)),1)')]
    need(first.count('endif\n')==2,'AY Make selector block');after=once(after,first,'')
    first=after[after.index('ifeq ($(X86_64_NATIVE_SHELL_SESSION),1)'):after.index('ifneq ($(words $(X86_64_NATIVE_TERMINAL)),1)')]
    need(first.count('endif\n')==2,'AY Make profile block');after=once(after,first,'')
    for line in ('X86_64_SERVICE_CPU_FLAGS += $(if $(filter 1,$(X86_64_NATIVE_SHELL_SESSION)),-DREIST_NATIVE_SESSION=1 -DREIST_NATIVE_SHELL_SESSION=1,)\n',
                 'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_SHELL_SESSION)),--shell-session,)\n'):
        after=once(after,line,'')
    need(after==original(name),'AY exact old Make recipes')
    name='scripts/build-x86_64-bootstrap.ps1';after=without_wide_build_selector((ROOT/name).read_text(encoding='utf-8'))
    first=after[after.index('if ($NativeShellSession) {'):after.index('if ($NativeSession) {')]
    need(first.count('$NativeTerminal = [switch]$true')==1,'AY PS selector block');after=once(after,first,'')
    for line in ('    [switch]$NativeShellSession,\n',
                 '        "X86_64_NATIVE_SHELL_SESSION=$([int]$NativeShellSession.IsPresent)" `\n'):
        after=once(after,line,'')
    need(after==original(name),'AY exact old Windows build body')
    return list(names)+['Makefile','scripts/build-x86_64-bootstrap.ps1']


def defaults():
    f=binding();old=prior();names=default_projection()
    gate=read(BASE/'gate-01.json')
    need(gate['passed'] and gate['candidate']==f['candidate'] and gate['log']==link(ROOT/gate['log']['path']),
         'AY prior host proof includes exact seventeen old producer profiles and selector admission')
    # Public SDK/ABI, services, UART/PIO/CPU mechanisms and shell source are
    # outside the implemented delta. Their complete hashes are frozen too.
    for name in ('userspace/bin/shell.c','userspace/bin/shell_vfs.c','arch/x86_64/user/filesystem.c',
                 'userspace/sdk/lib/x86_64/file_image.c','arch/x86_64/proc/native_terminal.inc'):
        need((ROOT/name).read_text(encoding='utf-8')==original(name),'AY retained implementation '+name)
    return dict(passed=True,exact_disabled_sources=names,prior=link(PRIOR),old_profile_host_gate=link(BASE/'gate-01.json'),
                unchanged_abi=True,reference_tools=old['tools'])


def subsystem_hosts():
    f=binding();folder=BASE/'subsystem-hosts';need(not folder.exists(),'AY one subsystem manifest execution');folder.mkdir()
    rows=[];begin=time.monotonic()
    try:
        for n,command in enumerate(f['package']['subsystem_host_tests'],1):
            limit=min(300,900-(time.monotonic()-begin));need(limit>0,'AY subsystem manifest deadline')
            started=time.monotonic();row=dict(command=command,passed=False);rows.append(row);log=folder/f'{n:02d}.log'
            try:
                with log.open('xb') as out:
                    child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                row.update(exit_code=child.returncode,passed=child.returncode==0)
            finally:row.update(elapsed=time.monotonic()-started,log=link(log))
            need(row['passed'],'AY retained host failed: '+command)
        return dict(passed=True,commands=rows)
    finally:save(folder/'manifest.json',dict(candidate=f['candidate'],commands=rows,elapsed=time.monotonic()-begin,
        passed=len(rows)==10 and all(r['passed'] for r in rows)))


def runtime():
    import run_qemu_x86_64_shell_session as run
    f=binding()
    return run.run_matrix(IMAGE,BASE/'guests',f['candidate'],binding)


def review():
    import run_qemu_x86_64_shell_session as run
    f=binding();prior()
    for n in range(1,9):
        gate=read(BASE/f'gate-{n:02d}.json')
        need(gate['passed'] and gate['candidate']==f['candidate'] and gate['command']==f['commands'][n-1] and
             gate['log']==link(ROOT/gate['log']['path']),'AY complete unchanged passed gate')
    summary=read(BASE/'guests/summary.json');config,records,app=run.image_config(IMAGE)
    catalog=(IMAGE.parent/'boot-programs.bin').read_bytes()
    need(summary['passed'] and summary['closed'] and summary['candidate']==f['candidate'] and
         summary['image_sha256']==digest(IMAGE) and summary['elapsed']<=900,'AY complete bound matrix')
    need([(r['case'],r['layout'],r['ram']) for r in summary['cases']]==list(run.CASES),'AY all eighteen cases')
    need(summary['guest_elapsed']==sum(r['elapsed'] for r in summary['cases'])<=810,'AY complete spent ledger')
    for row in summary['cases']:
        folder=ROOT/row['folder'];need(folder.parent==BASE/'guests' and row['passed'] and 0<row['elapsed']<=45,'AY guest path/bounds')
        need(row['proof']==run.evaluate(folder,config,records,catalog,row['case'],row['layout'],app),'AY full raw evidence replay')
    evidence={}
    for directory in (BASE/'guests',IMAGE.parent.parent):
        for path in directory.rglob('*'):
            if path.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in path.parts):
                need(not path.is_symlink(),'AY evidence no symlink');evidence[path.relative_to(ROOT).as_posix()]=digest(path)
    return dict(passed=True,candidate=f['candidate'],image=link(IMAGE),matrix=link(BASE/'guests/summary.json'),
                evidence_sha256=evidence,builds=0,historical_build=f['build_receipt'],guests=18,guest_elapsed=summary['guest_elapsed'])


def scope():
    f=binding();need(set(f['changed'])<=set(f['package']['allowed_files']),'AY final allowed scope')
    need(read(BASE/'gate-09.json')['passed'],'AY raw review precedes scope closure')
    review_files=list(BASE.glob('review-*.json'));need(len(review_files)==1,'AY unique complete raw review')
    reviewed=read(review_files[0]);need(reviewed['passed'],'AY successful raw review');verify_files(reviewed['evidence_sha256'])
    return dict(passed=True,candidate=f['candidate'],changed=f['changed'],review=link(review_files[0]),
                default_projection=default_projection(),public_abi_unchanged=True)


def gates():
    f=binding();need(not list(BASE.glob('gate-*.json')),'AY no unchanged gate retry')
    for n,(command,limit) in enumerate(zip(f['commands'],LIMITS),1):
        binding();log=BASE/f'gate-{n:02d}.log';started=time.monotonic()
        result=dict(passed=False,candidate=f['candidate'],command=command,limit=limit)
        try:
            with log.open('xb') as out:
                child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result.update(passed=child.returncode==0,exit_code=child.returncode)
        except Exception as error:result['error']=str(error)
        result.update(elapsed=time.monotonic()-started,log=link(log));save(BASE/f'gate-{n:02d}.json',result)
        print('SHELL_SESSION_GATE',n,'PASS' if result['passed'] else 'FAIL',round(result['elapsed'],3),flush=True)
        if not result['passed']:
            matrix=BASE/'guests/summary.json'
            save(BASE/'stopped.json',dict(frozen=link(BASE/'frozen.json'),failed_gate=n,result=result,
                image=link(IMAGE) if IMAGE.exists() else None,matrix=link(matrix) if matrix.exists() else None))
            print(log.read_text(errors='replace')[-3500:],flush=True);return 1
    return 0


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    actions=('freeze','gates','defaults','subsystem-hosts','runtime','review','scope','reuse-image','diagnostic-freeze','diagnostic','correction-freeze','correction')
    for name in actions:group.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.correction_freeze:correction_freeze();return 0
    if args.correction:return correction()
    if args.diagnostic_freeze:diagnostic_freeze();return 0
    if args.diagnostic:return diagnostic()
    if args.freeze:freeze();return 0
    if args.gates:return gates()
    name=next(n for n in actions if getattr(args,n.replace('-','_')));started=time.monotonic();result=dict(passed=False)
    try:result=globals()[name.replace('-','_')]();print('SHELL_SESSION_'+name.upper()+'_PASS',flush=True);return 0
    except Exception as error:result['error']=repr(error);print('SHELL_SESSION_VERIFY_FAIL',repr(error),flush=True);return 1
    finally:result['elapsed']=time.monotonic()-started;save(BASE/(name+'-'+uuid.uuid4().hex+'.json'),result)


if __name__=='__main__':raise SystemExit(main())
