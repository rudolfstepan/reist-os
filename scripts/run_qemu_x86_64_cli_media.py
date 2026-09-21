"""Unmodified BC safety proof composed with the accepted BIOS trust/no-write path."""
from pathlib import Path
import inspect,json,textwrap,time,types
import check_x86_64_cli_media as check
import run_qemu_x86_64_app_files as apps
import run_qemu_x86_64_shell_boot_media as bios
import run_qemu_x86_64_wide_shell_media as bb
ROOT=check.ROOT
LABELS={'hdd-fallback-recovery':'driver-crash','hdd-long':'repeated',
        'hdd-healthy':'ext2-1k','hdd-8g':'8g','floppy-app-hang':'hang'}
CASES=tuple((n,l,c,apps.case_spec(LABELS[n])[1] if n in LABELS else None,r)
            for n,l,c,_,r in bios.CASES)
boot_arguments=bios.boot_arguments;validate_bios=bios.validate_bios
physical_entry=bios.physical_entry;entry_phase=bios.entry_phase
bios_budget=bios.bios_budget;negative_budget=bios.negative_budget

def deadline_revoke(events,root,request,reply,end,timeout,failed):
    """Separate successful CLOSE syscalls, not a fictitious atomic timestamp.

    The first request fence remains at the original broker end. The second
    close/wakeup must precede the child's original relative receive timeout;
    no extra tick allowance or renewed lifetime is introduced.
    """
    closes=[r for r in events if r['kind'] in ('call','return') and r.get('gen')==root and
            r['op']==52 and r['args'][0] in (request,reply)]
    check.need([(r['kind'],r['args'][0]) for r in closes]==
        [('call',request),('return',request),('call',reply),('return',reply)],'CLI two complete ordered endpoint closes')
    first,done,second,last=closes
    check.need(done['result']==last['result']==0 and first['entered']==done['entered']==end and
        end<=done['now']<=second['entered']==last['entered']<=last['now']==failed['now']<failed['entered']+1000,
        'CLI original request fence and actual bounded reply-close wakeup')
    positions=[events.index(r) for r in (timeout,*closes,failed)]
    check.need(positions==sorted(set(positions)),'CLI timeout/close/wakeup causal order')
    actions=[r for r in events[positions[1]:positions[-2]+1] if r['kind'] in ('call','return') and r.get('gen')==root]
    check.need(actions==closes,'CLI no intervening broker operation during revocation')
    check.need(not any(r['kind']=='return' and r.get('gen')==root and r['op'] in (53,54) and
        r['args'][0] in (request,reply) and r['result']==0 for r in events[positions[0]+1:positions[-1]]),
        'CLI no successful broker operation after lifetime end')
    return second['entered']

qualified_outcome=bb.function(apps.qualified_outcome,dict(vars(apps),deadline_revoke=deadline_revoke),[
    ('timeout=timeouts[0];failed=failures[0]',
     'timeout=timeouts[0];failed=failures[0]\n        reply_entered=deadline_revoke(events,root,request,reply,end,timeout,failed)'),
    ("failed['entered']<end==failed['now']", "failed['entered']<end<=failed['now']<failed['entered']+1000"),
    ("len(closed)==1 and closed[0]['entered']==end and",
     "len(closed)==1 and closed[0]['entered']==(end if endpoint==request else reply_entered) and")])
_app_io=types.FunctionType(apps.validate_io_and_faults.__code__,dict(vars(apps),qualified_outcome=qualified_outcome))

def namespace(label):
    selected=check.clone(bios,[],'reist_cli_bios_'+label.replace('-','_'))
    selected.ay=apps.namespace(label);selected.check=check
    selected.ay.validate_io_and_faults=lambda *args:_app_io(selected.ay,apps.case_spec(label),*args)
    return selected

def data_fixture(folder,files,started,limit):
    check.need(type(limit) is int and limit in (20,30,320,330),'finite CLI media deadline')
    source=textwrap.dedent(inspect.getsource(apps.wide.Fixture.run))
    source=check.once(source,'limit=900 if self.wide_full else 300','limit='+str(limit))
    ns=dict(vars(apps.wide));exec(compile(source,'<BD bounded data medium>','exec'),ns)
    cls=apps.wide.old.file.pio.Fixture;fixture=cls.__new__(cls)
    fixture.started=started;fixture.wide_full=False
    fixture.expected=lambda:apps.media.image('ext2-1k',files)
    fixture.run=types.MethodType(ns['run'],fixture)
    cls.__init__(fixture,folder,filesystem='ext2-1k',file_program=files['boot.prg'])
    return fixture

def run_matrix(image,package,folder,binding,*,cases=CASES):
    check.need(cases in (CASES,CASES[5:]),'CLI full matrix or exact remaining negative suffix')
    image=Path(image).resolve();package=Path(package).resolve();folder=Path(folder).absolute()
    check.need(not folder.exists() and folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent'),'fresh CLI BIOS evidence')
    binding();catalog=(image.parent/'boot-programs.bin').read_bytes()
    folder.mkdir(parents=True);result=dict(passed=False,cases=[],guest_seconds=0.0);begin=time.monotonic()
    try:
        for name,layout,case,session,ram in cases:
            binding();check.need(time.monotonic()-begin<2000,'finite CLI runtime host window')
            label=LABELS.get(name,'ext2-1k');selected=namespace(label);module=selected.ay
            config,records,files=apps.image_config(image,label);module.app_files=files
            check.need(apps.media.image('ext2-1k',files)==check.bounded(package/'system.ext2',1048576),'actual published CLI volume')
            out=folder/name;out.mkdir();started=time.monotonic()
            limit=300+bios_budget(case) if session is not None else negative_budget(layout,case)
            trial=dict(name=name,layout=layout,case=case,session=session,ram=ram,passed=False,reused=False,
                       evidence_directory=out.relative_to(ROOT).as_posix())
            result['cases'].append(trial);medium=None
            try:
                source=package/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
                medium=selected.BootMedium(source,out/'boot-medium',layout,case,started+limit);medium.verify('before')
                fixture=data_fixture(out,files,started,limit)
                if session is not None:
                    code=selected.boot_entry_prefix(physical_entry(image,config),out,started,case)+module.observer(config,records,out,session,2)
                    selected.capture_namespace(started,medium,image,out,case)['capture'](image,out,code,ram,fixture,
                        binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True,console_input=apps.input_plan(label))
                else:
                    fixture.verify('before')
                    try:selected.negative(out,medium,fixture,started,case)
                    finally:fixture.verify('after')
            finally:
                try:
                    if medium is not None:medium.verify('after')
                finally:
                    trial['elapsed']=time.monotonic()-started;result['guest_seconds']+=trial['elapsed']
            check.need(trial['elapsed']<=limit and result['guest_seconds']<=1730,'whole CLI BIOS guest deadline')
            serial=check.bounded(out/'guest.log',262144).decode('ascii',errors='replace');validate_bios(serial,layout,case)
            if session is not None:
                metrics=json.loads((out/'capture-metrics.json').read_text());phase=metrics['bios_phase']
                seconds=phase['runtime_started']-started
                check.need(check.object_json(check.bounded(out/'bios-entry.json',1024))==phase and
                    0<=seconds<bios_budget(case) and 0<=metrics['observe_seconds']<=297 and
                    0<=trial['elapsed']-seconds-metrics['observe_seconds']<=3,'composed CLI phases include cleanup')
                trial['bios_seconds']=seconds;trial['proof']=module.evaluate(out,config,records,catalog,session,2,files)
            trial['passed']=True;print('CLI_BIOS_CASE_OK',name,round(trial['elapsed'],3),flush=True)
        result['passed']=True;return result
    except BaseException as error:result['error']=str(error);raise
    finally:
        result.update(elapsed=time.monotonic()-begin,closed=True,fresh_guests=len(result['cases']),reused_guests=0)
        with (folder/'summary.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
