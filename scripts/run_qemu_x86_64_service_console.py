"""Service-console authority proof layered on the unchanged complete AR oracle."""
from pathlib import Path
import argparse,json,re,time,uuid
import run_qemu_x86_64_live_file as live
from verify_x86_64_task_pool import need,read,digest,link
ROOT=live.ROOT
CASES=live.CASES

EXTRA=r'''
console_pending=None
console_events=0
console_denial_needed=set()
console_original_start=start_hook.fn
def console_started():
    before=set(starts)
    console_original_start()
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);gen=task(slot)[1]
    if gen in before:return
    assert gen in starts
    if slot:
        assert gen not in console_denial_needed and len(console_denial_needed)<8
        console_denial_needed.add(gen)
        console_denial_hook.enabled=True
start_hook.fn=console_started
def console_enter(denied=False):
    global console_pending
    op=q(S['syscall_rax'])
    if op not in (15,20):
        assert denied
        return
    assert console_pending is None and not reg('eflags')&512
    slot=d(S['scheduler_current_slot']);assert 0<=slot<8
    t=task(slot);gen=t[1];info=CONFIG['roles'][gen]
    assert t[0]==2 and info['slot']==slot and t[2]==reg('cr3')
    assert reg('r12')==S['scheduler_tasks']+slot*1024
    profile=struct.unpack('<4Q',mem(S['family_profiles']+slot*32,32))
    assert profile[0]==gen and bool(profile[1]&(1<<op))==bool(not denied)
    assert profile[2:]==((1<<49) if slot in (0,2) else 0,(1<<4) if slot<2 else 0)
    assert (slot!=0)==denied
    address=q(S['syscall_rsi']);size=q(S['syscall_rdx'])
    assert size in (0,1) and (not size or slot==0 and op==20)
    before=user(t,address,size).hex() if size else ''
    record=list(struct.unpack('<10Q',user(t,CONFIG['result_address'],80))) if slot==0 else []
    neighbors=[[task(n)[0],task(n)[1]] for n in (2,3,4)] if record and record[0] else []
    console_pending=dict(slot=slot,gen=gen,root=info['root'],op=op,denied=denied,
        profile=list(profile),fd=q(S['syscall_rdi']),pointer=address,size=size,
        unused=[q(S[name]) for name in ('syscall_r10','syscall_r8','syscall_r9')],
        before=before,record=record,neighbors=neighbors)
    console_return_hook.enabled=True
def console_return():
    global console_pending,console_events
    assert console_pending is not None and not reg('eflags')&512
    row=console_pending;t=task(row['slot'])
    assert t[1]==row['gen'] and t[0]==2 and t[2]==reg('cr3')
    value=reg('rax');row['result']=value if value<1<<63 else value-(1<<64)
    row['after']=user(t,row['pointer'],row['size']).hex() if row['size'] else ''
    console_events+=1;assert console_events<=512
    gdb.write('SERVICE_CONSOLE '+json.dumps(row,sort_keys=True)+'\n')
    if row['denied'] and row['op']==20:
        assert row['gen'] in console_denial_needed
        console_denial_needed.remove(row['gen'])
        console_denial_hook.enabled=bool(console_denial_needed)
    console_pending=None;console_return_hook.enabled=False
Hook('native_console_syscall64',console_enter)
console_denial_hook=Hook('process_run_syscall64.denied',lambda:console_enter(True))
console_denial_hook.enabled=False
console_return_hook=Hook('process_run_resume64',console_return)
console_return_hook.enabled=False
'''

def observer(config,folder,case,layout,oom,raw):
    code=live.observer(config,folder,case,layout,oom,raw)
    return live.once(code,'\nend\ncontinue\n','\n'+EXTRA+'\nend\ncontinue\n')

def validate_console(trace,case):
    rows=[json.loads(s) for s in re.findall(r'^SERVICE_CONSOLE (.+)$',trace,re.M)]
    need(0<len(rows)<=512 and trace.count('SERVICE_CONSOLE ')==len(rows),'console complete raw rows')
    plan=live.roles(case)
    for row in rows:
        info=plan[row['gen']];slot=info['slot'];op=row['op'];size=row['size']
        need(row['slot']==slot and row['root']==info['root'] and op in (15,20),'console identity')
        need(row['unused']==[0,0,0] and row['fd']==int(op==20),'console exact arguments')
        need(row['profile'][0]==row['gen'] and len(row['profile'])==4,'console profile generation')
        need(row['profile'][2:]==[(1<<49) if slot in (0,2) else 0,(1<<4) if slot<2 else 0],'console exact extended rights')
        need(row['before']==row['after'],'console buffer unchanged')
        if slot:
            need(row['denied'] is True and row['result']==-13 and size==0 and row['pointer']==0 and
                 not row['profile'][1]&((1<<15)|(1<<20)) and row['before']=='' and
                 row['record']==row['neighbors']==[],'console no peer/driver/child authority')
        else:
            need(row['denied'] is False and row['profile'][1]&((1<<15)|(1<<20))==((1<<15)|(1<<20)),
                 'console explicit root grant')
            need((size==0 and op==15 and row['pointer']==0 and row['result']==0 and row['before']=='') or
                 (size==1 and op==20 and row['before']=='0a' and row['result'] in (1,-11)),
                 'console exact mediator result')
            record=row['record'];need(len(record)==10,'console raw witness size')
            if any(record):
                need(record[0]==0x4c49564546494c31 and record[1]==2 and record[5]==0,'console concurrent phase')
                app=record[4]>>32;fs=record[2]>>32;driver=record[3]>>32
                need(plan[app]['root']==row['gen'] and (fs,driver)==(app-1,app-2),'console current dependencies')
                need([r[1] for r in row['neighbors']]==[driver,fs,app] and
                     all(r[0] in (1,2,6) for r in row['neighbors']),'console live dependencies')
            else:need(row['neighbors']==[],'console initial root')
    for gen,info in plan.items():
        own=[r for r in rows if r['gen']==gen]
        if info['slot']:
            need([r['op'] for r in own]==[15,20],'console every non-root denial')
        else:
            expected=[0]+[g for g,i in plan.items() if i['root']==gen and i['role']=='program']
            groups=[]
            for row in own:
                if row['op']==15:groups.append([row])
                else:need(bool(groups),'console write after probe');groups[-1].append(row)
            need(len(groups)==len(expected),'console all root phases')
            for group,app in zip(groups,expected):
                need(2<=len(group)<=11 and [r['result'] for r in group]==[0]+[-11]*(len(group)-2)+[1],
                     'console bounded progress')
                need(all((r['record'][4]>>32 if any(r['record']) else 0)==app for r in group),'console phase binding')
    return rows

def validate(serial,trace,case,layout,oom,counts,raw,ledger,raw_cpu):
    result=live.validate(serial,trace,case,layout,oom,counts,raw,ledger,raw_cpu)
    validate_console(trace,case)
    return result

def main():
    from verify_x86_64_service_console import binding,BASE,IMAGE
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    image=args.image.resolve();base=args.evidence.resolve();f=binding()
    need(image==IMAGE and base==BASE/'guests' and not list(base.glob('attempt-*')),'console unique matrix')
    for n in range(1,10):need(read(BASE/f'gate-{n:02d}.json')['passed'],'console preceding gate')
    config,counts,raw=live.image_config(image)
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,closed=False,candidate=f['candidate'],image=link(image),cases=[],guest_elapsed=0.0)
    begin=time.monotonic()
    try:
        for case,layout,ram,point in CASES:
            binding();need(summary['guest_elapsed']+45<=1125,'console finite guest reserve')
            oom=None if point is None else 0 if point=='first' else counts['program']//2 if point=='middle' else counts['program']-1
            out=folder/f'guest-{case}-{layout}-{ram}-{point}';out.mkdir()
            row=dict(case=case,layout=layout,ram=ram,point=point,oom=oom,folder=out.relative_to(ROOT).as_posix(),passed=False)
            summary['cases'].append(row);started=time.monotonic()
            try:
                fixture=live.pio.Fixture(out,filesystem=live.media.LAYOUTS[layout],file_program=live.file.program_variant(raw,case))
                code=observer(config,out,case,layout,oom,raw)
                serial,trace=live.wide.transport.capture(image,out,code,ram,fixture,binary_memory='equivalence',
                                                        diagnostic_metrics=True,service_pio_budget=True)
                validate(serial,trace,case,layout,oom,counts,raw,(out/live.cpu.CPU_FILE).read_bytes(),(out/'cpu-trace-v1.bin').read_bytes())
                need(link(image)==summary['image'],'console immutable image');row['passed']=True
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed']
            need(row['elapsed']<=45,'console deadline including cleanup')
            print('SERVICE_CONSOLE_GUEST_OK',case,layout,ram,point,round(row['elapsed'],3),flush=True)
        need(len(summary['cases'])==25 and time.monotonic()-begin<=1200,'console complete matrix')
        summary['passed']=True;return 0
    except Exception as error:
        summary['error']=str(error);print('SERVICE_CONSOLE_FAIL',error,flush=True);return 1
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-begin)
        with (folder/'summary.json').open('x') as stream:json.dump(summary,stream,indent=2)
        print('SERVICE_CONSOLE_EVIDENCE',folder,flush=True)
if __name__=='__main__':raise SystemExit(main())
