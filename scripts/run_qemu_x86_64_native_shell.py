"""Actual normal shell on native console; immutable AS observer/capture reuse."""
from pathlib import Path
import argparse,inspect,json,re,time,uuid
import run_qemu_x86_64_console as console
import run_qemu_x86_64_boot_programs as boot
from run_qemu_x86_64_runtime_clock import once
ROOT=Path(__file__).resolve().parents[1]
BANNER='REIST OS userspace shell\n'
NORMAL=b'help\npath\nhistory\nx\nexit\n'
EDIT=b'patx\bh\n\x1b[A\nhistory\npwd\nexit\n'
CASES=((0,4096),(0,8192),(1,4096),(2,4096))
def inputs(case):return ((NORMAL,EDIT,b'pwd\n')[case],NORMAL)
def input_plan(value):
    if type(value) is not tuple or len(value)!=2 or value not in tuple(inputs(i) for i in range(3)):
        raise ValueError('native shell fixed two-run input')
    return value
def capture_namespace():
    ns=dict(vars(boot));ns['console_input_plan']=input_plan
    for item in (boot.ConsoleFeeder,boot._capture_run,boot._capture,boot.capture):
        source=inspect.getsource(item).replace('NATIVE_CONSOLE_READY\\n','REIST OS userspace shell\\n')
        exec(compile(source,'<native-shell-original-capture>','exec'),ns)
    return ns
def base_validator():
    code=inspect.getsource(boot.validate)
    code=once(code,'ident=slot if run==0 else 3-slot;bad=case and ident==2','ident=slot;bad=False')
    code=once(code,'else 40+ident,3 if bad else 4',
              'else ((110 if case==2 and run==0 else 0) if ident==0 else 61+ident),3 if bad else 4')
    code=once(code,'not 0x400000<=rip<0x401000','not 0x400000<=rip<(0x404000 if slot==0 else 0x401000)')
    code=once(code,'(s if r==0 else 3-s)+3,(s if r==0 else 3-s)+2','s+3,s+2')
    ns=dict(vars(boot));exec(compile(code,'<native-shell-original-oracle>','exec'),ns);return ns['validate']
def validate_io(events,case):
    if not events or len(events)>512:raise ValueError('shell raw capacity')
    for run in (1,2):
        received=bytearray();written=bytearray();empty=0
        rows=[r for r in events if r['run']==run]
        if not rows:raise ValueError('shell missing generation')
        for row in rows:
            op,size,result=row['op'],row['size'],row['result']
            if (row['slot'],row['gen'])!=(0,(run-1)*4+1) or op not in (15,20) or row['fd']!=(op==20) or any(row['unused']):
                raise ValueError('shell console exact authority')
            before=None if row['before'] is None else bytes.fromhex(row['before'])
            after=None if row['after'] is None else bytes.fromhex(row['after'])
            if size==0:
                if op!=15 or result or row['pointer'] or before is not None or after is not None:raise ValueError('shell authority probe')
            elif not 0<size<=64 or before is None or after is None or len(before)!=size or len(after)!=size:
                raise ValueError('shell whole IO bytes')
            elif result>0:
                if result>size:raise ValueError('shell short IO extent')
                if op==20:
                    if before!=after:raise ValueError('shell write mutation')
                    written.extend(before[:result])
                else:
                    if before[result:]!=after[result:]:raise ValueError('shell read tail mutation')
                    received.extend(after[:result])
            elif result!=-11 or before!=after:raise ValueError('shell unexpected IO error')
            else:empty+=1
        if bytes(received)!=inputs(case)[run-1]:raise ValueError('shell exact raw input')
        if not written.startswith((BANNER+'Type HELP for available commands.\nUSB keyboard: diagnostics unavailable\n\n?>').encode()):raise ValueError('shell actual startup')
        mode=case if run==1 else 0
        expected={0:(b'Built-ins: cd path pwd history help exit\n',b'PATH=',b'Program lookup unavailable.\n'),
                  1:(b'PATH=',b'Unable to read working directory.\n'),2:(b'Unable to read working directory.\n',)}[mode]
        if any(marker not in written for marker in expected):raise ValueError('shell actual command dispatch')
        if mode==2 and not empty:raise ValueError('shell actual empty input wait')
        if mode!=2 and not written.endswith(b'exit\n'):raise ValueError('shell normal exit command')
    if any(r['run'] not in (1,2) for r in events):raise ValueError('shell unexpected generation')
def validate(serial,trace,case,ram):
    rows=base_validator()(serial,trace,case,ram)
    events=[json.loads(m) for m in re.findall(r'^CONSOLE_IO (.+)$',trace,re.M)]
    if trace.count('CONSOLE_IO ')!=len(events):raise ValueError('shell malformed trace')
    validate_io(events,case);return rows
def main():
    from verify_x86_64_native_shell import binding,link
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    a=parser.parse_args();binding();image=a.image.resolve();s,c=console.image_config(image)
    folder=a.evidence.resolve()/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,cases=[],guest_elapsed=0,image=link(image));started=time.monotonic()
    capture=capture_namespace()['capture']
    try:
        for case,ram in CASES:
            binding()
            if summary['guest_elapsed']+20>80:raise ValueError('shell finite reservation')
            target=folder/f'{case}-{ram}';target.mkdir();begin=time.monotonic()
            row=dict(case=case,ram=ram,passed=False,folder=target.relative_to(ROOT).as_posix());summary['cases'].append(row)
            try:
                serial,trace=capture(image,target,console.observer(s,c,target,ram),ram,
                    diagnostic_metrics=True,binary_memory='equivalence',console_input=inputs(case))
                validate(serial,trace,case,ram)
                if link(image)!=summary['image']:raise ValueError('shell image changed')
                row['passed']=True
            finally:row['elapsed']=time.monotonic()-begin;summary['guest_elapsed']+=row['elapsed']
            if row['elapsed']>20:raise ValueError('shell guest cleanup deadline')
            print('NATIVE_SHELL_GUEST_OK',case,ram,round(row['elapsed'],3),flush=True)
        if time.monotonic()-started>120:raise ValueError('shell matrix deadline')
        summary['passed']=True;return 0
    except Exception as error:summary['error']=str(error);print('NATIVE_SHELL_FAIL',error,flush=True);return 1
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-started)
        with (folder/'summary.json').open('x') as out:json.dump(summary,out,indent=2)
if __name__=='__main__':raise SystemExit(main())
