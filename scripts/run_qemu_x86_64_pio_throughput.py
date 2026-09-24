"""Private new-profile adapter of the accepted full pool-PIO guest proof."""
from pathlib import Path
import inspect,json,linecache,time,types
import run_qemu_x86_64_pool_pio as prior
ROOT=prior.ROOT
TAG=0xffffff7f00000080
CASES=((0,4096),(1,4096),(6,8192),(7,4096),(8,4096),(9,4096),(11,4096))
PORTABLE=ROOT/'build/codex-agent/r83bs-native-math/portable-qemu/binary-binding09.json'

def hardware_capture():
    """Reuse the accepted WHPX tool and one-shot pre-task rendezvous."""
    import run_qemu_x86_64_math_runtime as hardware
    exe,firmware=hardware.portable_toolchain(PORTABLE)
    ns=dict(vars(prior.transport));ns['resolve_qemu']=lambda unused:exe
    once=prior.helpers.once
    for name in ('_capture_run','_capture','capture'):
        source=inspect.getsource(getattr(prior.transport,name))
        if name=='_capture_run':
            source=once(source,"'-machine','pc,accel=tcg'","'-machine','pc','-accel','whpx,kernel-irqchip=off'")
            source=once(source,'    command+=binary_arguments',
                        '    command+=binary_arguments\n    command+='+repr(['-L',str(firmware)]))
            marker='            debugger=subprocess.Popen('
            source=once(source,marker,
                '            from run_qemu_x86_64_math_runtime import hardware_bootstrap\n'
                '            hardware_bootstrap(command,folder,image)\n'+marker)
        exec(compile(source,'<BY-WHPX-'+name+'>','exec'),ns)
    return ns['capture']

def hardware_observer(code,config,folder):
    once=prior.helpers.once;s=config['s']
    # Exactly the generic observer and release-return breakpoint constructors.
    if code.count('internal=True')!=2:raise ValueError('BY exact execution probe constructors')
    code=code.replace('internal=True','type=gdb.BP_HARDWARE_BREAKPOINT,internal=True')
    ready=s['native_math_hardware_ready'];release=s['native_math_hardware_release']
    if release!=ready+8:raise ValueError('BY hardware cell layout')
    code=once(code,'def boot():',
        'def boot():\n    global hardware_deferred\n'
        '    assert hardware_deferred\n'
        '    for probe,enabled in hardware_deferred:probe.enabled=enabled\n'
        '    hardware_deferred=[]\n'
        '    cleared=mem('+str(ready)+',16);assert cleared==bytes(16)\n'
        '    with open('+repr(str(folder/'hardware-cleared.bin'))+",'xb') as f:assert f.write(cleared)==16")
    tail=("hardware_deferred=[(bp,bp.enabled) for bp in gdb.breakpoints() if bp.fn.__name__ not in ('boot','cold_fail')]\n"
          "assert 10<=len(hardware_deferred)<=32\n"
          "for probe,enabled in hardware_deferred:probe.enabled=False\n"
          f"assert {s['native_math_hardware_gate64.wait']} <= reg('rip') < {s['native_math_hardware_gate64.failed']}\n"
          "assert reg('cs')==8 and reg('cr0')&0x80010000==0x80010000 and reg('cr3')>0\n"
          f"assert mem({ready},16)==struct.pack('<2Q',1,0)\n"
          f"gdb.selected_inferior().write_memory({release},struct.pack('<Q',1))\n"
          f"assert mem({ready},16)==struct.pack('<2Q',1,1)\n"
          "gdb.write('BY_HARDWARE '+json.dumps(dict(rip=reg('rip'),cr0=reg('cr0'),cr3=reg('cr3'),cs=reg('cs'),release=1))+'\\n')\n")
    return 'set remote software-breakpoint-packet on\n'+once(code,'\nend\ncontinue\n','\n'+tail+'end\ncontinue\n')

def namespace(case):
    if case not in {n for n,_ in CASES}:raise ValueError('BY declared case')
    tag=TAG if case else 0;limit=128 if case else 64
    module=types.ModuleType('_by_pio_'+str(case));module.__dict__.update(vars(prior))
    once=prior.helpers.once
    module.TRACE_CORE=once(prior.TRACE_CORE,'v[5]>64','v[5]>'+str(limit))
    module.TRACE_CORE=once(module.TRACE_CORE,'or v[7]:','or v[7]!='+str(tag)+':')
    module.EXTRA=once(prior.EXTRA,'v[5]<=64 and not v[7]',
        f'v[5]<={limit} and v[7]==({tag} if v[0] else 0)')
    module.EXTRA=once(module.EXTRA,"emit('bind',gen=owner>>32,owner=owner)",
        "emit('bind',gen=owner>>32,owner=owner,quota=128 if v[7] else 64)")
    code=module.TRACE_CORE+'\n'+'\n'.join(inspect.getsource(getattr(prior,n))
                                         for n in ('observer_body','observer','_validate','validate'))
    filename='<BY-profile-'+str(case)+'>'
    linecache.cache[filename]=(len(code),None,code.splitlines(True),filename)
    exec(compile(code,filename,'exec'),module.__dict__)
    original=module.validate
    def validate(serial,trace,*args):
        rows=original(serial,trace,*args)
        events=[json.loads(line[9:]) for line in trace.splitlines() if line.startswith('POOL_PIO ')]
        binds=[r for r in events if r.get('kind')=='bind']
        if not binds or any(r.get('quota')!=limit for r in binds):raise ValueError('BY actual profile binding')
        return rows
    module.validate=validate
    return module

def run(image,folder,case,ram):
    image=Path(image).resolve();folder=Path(folder).absolute()
    if (case,ram) not in CASES or folder.exists() or not folder.is_relative_to(ROOT/'build/codex-agent/r83by-pio-throughput'):
        raise ValueError('BY fresh bounded guest')
    started=time.monotonic();folder.mkdir(parents=True)
    result=dict(passed=False,closed=False,case=case,ram=ram,limit=60)
    try:
        module=namespace(case);config=module.image_config(image)
        fixture=module.pio.Fixture(folder,block=True)
        code=module.observer(config,folder,case,None)
        capture=module.transport.capture;options={}
        if 'native_math_hardware_ready' in config['s']:
            code=hardware_observer(code,config,folder);capture=hardware_capture()
            result['hardware']=True
            options['service_pio_budget']=True
        serial,trace=capture(image,folder,code,ram,fixture,
            diagnostic_metrics=True,binary_memory='equivalence',**options)
        count=module.wide.allocations(config['child_record'])
        import hashlib
        sha=hashlib.sha256(config['child_record']).hexdigest()
        rows=module.validate(serial,trace,case,None,count,sha)
        result.update(tasks=len(rows),child_sha256=sha,image_sha256=module.digest(image))
        if time.monotonic()-started>60:raise ValueError('BY complete guest lease')
        result['passed']=True
    except BaseException as error:
        result['error']=str(error)
        raise
    finally:
        result.update(closed=True,elapsed=time.monotonic()-started)
        (folder/'result.json').write_text(json.dumps(result,indent=2))
    return result
