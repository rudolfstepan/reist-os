"""Terminal lease proof, retaining the complete live-file lifecycle oracle."""
from pathlib import Path
import argparse,hashlib,inspect,json,re,struct,time,uuid
import run_qemu_x86_64_live_file as live
from verify_x86_64_task_pool import need,read,link
ROOT=live.ROOT;CASES=live.CASES
LEDGER='terminal-v1.jsonl'
IO=(1<<15)|(1<<20);CTL=1<<63

class TerminalProbeScope:
    """Bounded probe interests, not guest authority or inferred evidence."""
    def __init__(self):self.io=set();self.control=set();self.phase={}
    def check(self):
        assert len(self.io)<=8 and len(self.control)<=8 and len(self.phase)<=2
        assert all(type(g) is int and 0<g<1<<31 for g in self.io|self.control|set(self.phase))
    def start(self,gen,slot):
        if slot==0:self.phase[gen]='initial'
        if slot in (0,4):self.io.add(gen)
        self.check()
    def ready(self,root):
        assert root in self.phase
        self.phase[root]='grant';self.io.add(root);self.control.add(root);self.check()
    def go(self,gen):self.io.add(gen);self.control.add(gen);self.check()
    def returned(self,row):
        gen=row['gen'];slot=row['slot'];op=row['op'];value=row['result']
        if slot==0:
            phase=self.phase[gen]
            if (phase=='initial' and op==20 and value==1 or
                phase=='grant' and op==15 and value==-11 or
                phase=='reclaim' and op==15 and value==0):
                self.io.discard(gen);self.control.discard(gen)
        elif slot==4:
            if op==20 and value==-13:self.io.discard(gen)
            if op==127 and value==-11 and struct.unpack('<4IiI',bytes.fromhex(row['data']))[2]==5:self.control.discard(gen)
        self.check()
    def retire(self,gen,slot,after):
        self.io.discard(gen);self.control.discard(gen)
        if slot==0:self.phase.pop(gen,None)
        if slot==4 and after[0]:
            root=after[0]>>32;assert root in self.phase
            self.phase[root]='reclaim';self.io.add(root);self.control.add(root)
        self.check()

EXTRA=r'''
terminal_stream=Path(CONFIG['terminal_ledger']).open('xb',buffering=0)
terminal_digest=hashlib.sha256();terminal_count=0;terminal_bytes=0
terminal_pending=None;terminal_retiring=None;terminal_denials=set()
terminal_scope=TerminalProbeScope()
def terminal_sync():
    terminal_console_hook.enabled=bool(terminal_scope.io)
    terminal_control_hook.enabled=bool(terminal_scope.control)
def terminal_state():return list(struct.unpack('<3Q',mem(S['native_terminal_state'],24)))
def terminal_emit(kind,**row):
    global terminal_count,terminal_bytes
    raw=(json.dumps(dict(kind=kind,**row),sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    terminal_count+=1;terminal_bytes+=len(raw)
    assert terminal_count<=512 and len(raw)<=2048 and terminal_bytes<=1048576
    assert terminal_stream.write(raw)==len(raw)
    terminal_digest.update(raw)
terminal_original_start=start_hook.fn
def terminal_started():
    before=set(starts);terminal_original_start()
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);gen=task(slot)[1]
    if gen in before:return
    assert gen in starts
    terminal_emit('start',gen=gen,slot=slot,state=terminal_state(),
        profile=list(struct.unpack('<4Q',mem(S['family_profiles']+slot*32,32))))
    terminal_scope.start(gen,slot);terminal_sync()
    if slot in (1,2,3):
        assert gen not in terminal_denials and len(terminal_denials)<8
        terminal_denials.add(gen);terminal_denial_hook.enabled=True
start_hook.fn=terminal_started
terminal_original_ready=program_ready
def program_ready(slot,t,gen,raw):
    terminal_original_ready(slot,t,gen,raw)
    terminal_scope.ready(CONFIG['roles'][gen]['root']);terminal_sync()
terminal_original_go=program_go
def program_go(t,gen,raw):
    before=set(live_programs);terminal_original_go(t,gen,raw)
    added=live_programs-before;assert len(added)==1
    terminal_scope.go(added.pop());terminal_sync()
def terminal_enter(denied=False):
    global terminal_pending
    op=q(S['syscall_rax'])
    if op not in (15,20,127):assert denied;return
    assert terminal_pending is None and not reg('eflags')&512
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    assert t[0]==2 and CONFIG['roles'][gen]['slot']==slot and t[2]==reg('cr3')
    assert reg('r12')==S['scheduler_tasks']+slot*1024
    profile=list(struct.unpack('<4Q',mem(S['family_profiles']+slot*32,32)))
    args=[q(S[name]) for name in ('syscall_rdi','syscall_rsi','syscall_rdx','syscall_r10','syscall_r8','syscall_r9')]
    size=24 if op==127 else args[2];address=args[0] if op==127 else args[1]
    assert size in ((24,) if op==127 else (0,1))
    terminal_pending=dict(gen=gen,slot=slot,op=op,denied=denied,profile=profile,args=args,
        state=terminal_state(),data=user(t,address,size).hex() if size else '',address=address,size=size)
    terminal_return_hook.enabled=True
def terminal_return():
    global terminal_pending
    assert terminal_pending is not None and not reg('eflags')&512
    row=terminal_pending;t=task(row['slot'])
    assert t[0]==2 and t[1]==row['gen'] and t[2]==reg('cr3')
    value=reg('rax');row['result']=value if value<1<<63 else value-(1<<64)
    row['after']=terminal_state()
    row['data_after']=user(t,row['address'],row['size']).hex() if row['size'] else ''
    terminal_emit('call',**row)
    terminal_scope.returned(row);terminal_sync()
    if row['denied'] and row['op']==20:
        assert row['gen'] in terminal_denials
        terminal_denials.remove(row['gen']);terminal_denial_hook.enabled=bool(terminal_denials)
    terminal_pending=None;terminal_return_hook.enabled=False
def terminal_retire_begin():
    global terminal_retiring
    if mode()!=8:return
    assert terminal_retiring is None and terminal_pending is None and not reg('eflags')&512
    slot=d(S['scheduler_current_slot']);t=task(slot)
    assert t[0] in (3,4) and reg('r12')==S['scheduler_tasks']+slot*1024
    terminal_retiring=dict(gen=t[1],slot=slot,state=terminal_state(),task_state=t[0])
def terminal_retire_end():
    global terminal_retiring
    if mode()!=8:return
    assert terminal_retiring is not None and not reg('eflags')&512
    after=terminal_state();terminal_emit('retire',**terminal_retiring,after=after)
    terminal_scope.retire(terminal_retiring['gen'],terminal_retiring['slot'],after);terminal_sync();terminal_retiring=None
terminal_original_finish=finish_hook.fn
def terminal_finished():
    assert not terminal_pending and not terminal_retiring and not terminal_denials
    assert not terminal_scope.io and not terminal_scope.control
    terminal_emit('finish',run=runs+1,state=terminal_state())
    if runs==1:
        terminal_stream.close()
        gdb.write('TERMINAL_LEDGER '+str(terminal_count)+' '+terminal_digest.hexdigest()+'\n')
    terminal_original_finish()
finish_hook.fn=terminal_finished
terminal_console_hook=Hook('native_console_syscall64',terminal_enter);terminal_console_hook.enabled=False
terminal_control_hook=Hook('native_terminal_syscall64',terminal_enter);terminal_control_hook.enabled=False
terminal_denial_hook=Hook('process_run_syscall64.denied',lambda:terminal_enter(True));terminal_denial_hook.enabled=False
terminal_return_hook=Hook('process_run_resume64',terminal_return);terminal_return_hook.enabled=False
Hook('family_terminal64',terminal_retire_begin)
Hook('native_pio_terminal64',terminal_retire_end)
'''

def observer(config,folder,case,layout,oom,raw):
    # The single old zero-extended-mask assertion becomes the exact explicit
    # terminal mask; all other AR callbacks, arithmetic and predicates survive.
    code=live.observer(dict(config,terminal_ledger=(folder/LEDGER).as_posix()),folder,case,layout,oom,raw)
    code=live.once(code,"    assert not any(mem(S['family_extended_masks']+slot*16,16))\n    record=copies[gen]",
        "    assert struct.unpack('<2Q',mem(S['family_extended_masks']+slot*16,16))==(1<<63,0)\n    record=copies[gen]")
    # AR registers this callback anonymously; retain its exact Hook object.
    code=live.once(code,"Hook('x86_64_c_process_run64.restore',finish)","finish_hook=Hook('x86_64_c_process_run64.restore',finish)")
    return live.once(code,'\nend\ncontinue\n','\n'+inspect.getsource(TerminalProbeScope)+'\n'+EXTRA+'\nend\ncontinue\n')

def decode_ledger(trace,raw):
    need(0<len(raw)<=1048576 and raw.endswith(b'\n'),'terminal ledger extent')
    lines=raw.splitlines();need(0<len(lines)<=512 and all(len(s)<=2048 for s in lines),'terminal rows bound')
    marker=re.findall(r'^TERMINAL_LEDGER (\d+) ([0-9a-f]{64})$',trace,re.M)
    need(marker==[(str(len(lines)),hashlib.sha256(raw).hexdigest())],'terminal complete raw ledger binding')
    return [json.loads(s) for s in lines]

def validate_terminal(trace,raw,case):
    rows=decode_ledger(trace,raw);plan=live.roles(case);state=[0,0,0];started=set();retired=set();finishes=0
    calls={g:[] for g in plan}
    for row in rows:
        kind=row['kind']
        if kind=='finish':
            finishes+=1;need(row==dict(kind='finish',run=finishes,state=[0,0,0]) and state==[0,0,0], 'terminal complete clear')
            continue
        g=row['gen'];info=plan[g];slot=info['slot'];handle=g<<32|slot
        need(row['slot']==slot,'terminal slot identity')
        if kind=='start':
            need(g not in started,'terminal unique start');started.add(g)
            if slot==0:need(state==[0,0,0],'terminal new root clean');state=[handle,0,0]
        else:need(g in started and g not in retired,'terminal live identity')
        need(row['state']==state,'terminal state continuity')
        if kind in ('start','call'):
            profile=row['profile'];expected_ext=((1<<49)|CTL) if slot==0 else (1<<49) if slot==2 else CTL if slot==4 else 0
            need(len(profile)==4 and profile[0]==g and profile[2:]==[expected_ext,(1<<4) if slot<2 else 0], 'terminal exact extended profile')
            need(profile[1]&IO==(IO if slot in (0,4) else 0),'terminal explicit IO eligibility')
        if kind=='start':continue
        if kind=='retire':
            need(row['task_state']==info['state'],'terminal retirement cause')
            if state[0]==handle:state=[0,0,0]
            elif state[1]==handle:state=[state[0],0,0]
            need(row['after']==state,'terminal exact automatic revoke');retired.add(g);continue
        need(kind=='call','terminal known event')
        calls[g].append(row);op=row['op'];args=row['args'];result=row['result']
        need(op in (15,20,127) and len(args)==6 and args[3:]==[0,0,0], 'terminal syscall transport')
        need(row['data']==row['data_after'],'terminal no unexpected buffer mutation')
        if op==127:
            need(slot in (0,4) and row['denied'] is False and args[1:]==[0]*5 and row['size']==24 and row['address']==args[0], 'terminal control admission')
            request=struct.unpack('<4IiI',bytes.fromhex(row['data']));version,size,operation,reserved,pid,gen=request
            need((version,size,reserved)==(1,24,0) and operation in (1,2,3,5),'terminal exact request')
            if operation==2:
                need(slot==0 and pid==gen and gen in plan and plan[gen]['root']==g,'terminal own target')
                target=plan[gen];expected=-116 if gen in retired else -13 if target['slot'] in (2,3) else 0
                if expected==0:
                    need(gen in started and state[1] in (0,gen<<32|4),'terminal live target');state=[state[0],gen<<32|4,0]
            else:
                need(pid==gen==0,'terminal no extraneous target')
                if operation==1:need(slot==0,'terminal root attach');expected=0
                elif operation==3:
                    need(slot==4,'terminal child release');expected=0
                    if state[1]==handle:state=[state[0],0,0]
                else:expected=0 if (slot==0 and not state[1]) or state[1]==handle else -11
            need(result==expected,'terminal exact control result')
        else:
            size=row['size'];need(size==args[2] and row['address']==args[1] and size in (0,1) and args[0]==int(op==20), 'terminal exact IO args')
            need(row['denied']==(slot in (1,2,3)), 'terminal static versus lease admission')
            if slot in (1,2,3) or slot==4 and state[1]!=handle:need(size==0 and args[1]==0 and result==-13,'terminal unleased IO denied')
            elif slot==0 and op==15:
                need(size==0 and args[1]==0 and result==(-11 if state[1] else 0),'terminal root exclusive input')
            elif op==15:need(size==1 and row['data']=='a5' and result==-11,'terminal actual empty RX')
            else:need(size==1 and row['data']==('0a' if slot==0 else '54') and result in (1,-11),'terminal actual TX')
        need(row['after']==state,'terminal publication/result agreement')
    need(started==retired==set(plan) and finishes==2,'terminal complete generation cleanup')
    for g,info in plan.items():
        own=calls[g];slot=info['slot']
        if slot in (1,2,3):need([r['op'] for r in own]==[15,20],'terminal every noneligible denial');continue
        controls=[(struct.unpack('<4IiI',bytes.fromhex(r['data']))[2],struct.unpack('<4IiI',bytes.fromhex(r['data']))[4],r['result']) for r in own if r['op']==127]
        io=[(r['op'],r['result']) for r in own if r['op']!=127]
        if slot==0:
            expected=[];programs=[a for a,i in plan.items() if i['root']==g and i['role']=='program']
            for a in programs:
                expected += [(2,a-1,-13),(2,a-2,-13),(1,0,0),(2,a,0),(2,a,0),(5,0,-11)]
                if case!=15:expected += [(5,0,0),(2,a,-116)]
            need(controls==expected,'terminal complete root control sequence')
            reads=[v for op,v in io if op==15]
            need(reads==[0]+[v for a in programs for v in ([0,-11] if case==15 else [0,-11,0])],'terminal root input phases')
            writes=[v for op,v in io if op==20]
            need(writes.count(1)==1+len(programs) and len(writes)<=10*(1+len(programs)) and all(v in (1,-11) for v in writes),'terminal root bounded output')
        else:
            need(io[:2]==[(15,-13),(20,-13)],'terminal eligible prelease denial')
            healthy=info['status']==82
            if healthy:need(controls==[(5,0,0),(3,0,0),(3,0,0),(5,0,-11)] and io[-2:]==[(15,-13),(20,-13)],'terminal complete child release')
            elif case==15:need(not controls and len(io)==2,'terminal root-loss blocked child')
            elif case==3:need(controls in ([],[(5,0,0)]),'terminal bounded cancel prefix')
            else:need(controls==[(5,0,0)],'terminal fault/quota after grant')
            middle=io[2:-2] if healthy else io[2:]
            if healthy or info['status'] in (134,256):
                need(2<=len(middle)<=11 and middle[0]==(15,-11) and middle[-1]==(20,1) and all(v==(20,-11) for v in middle[1:-1]),'terminal delegated IO before termination')
            elif middle:
                need(middle[0]==(15,-11) and len(middle)<=11 and all(op==20 and v in (-11,1) for op,v in middle[1:]) and sum(v==1 for _,v in middle)<=1,'terminal cancelled IO prefix')
    return rows

def validate(serial,trace,case,layout,oom,counts,raw,folder):
    rows=live.validate(serial,trace,case,layout,oom,counts,raw,(folder/live.cpu.CPU_FILE).read_bytes(),(folder/'cpu-trace-v1.bin').read_bytes())
    validate_terminal(trace,(folder/LEDGER).read_bytes(),case)
    return rows

FATAL_CASES=('root-generation','child-generation')
FATAL_RANGES=(('native_terminal_state',24),('native_pio_state',64),('scheduler_tasks',8192),
    ('family_records',512),('family_profiles',256),('family_extended_masks',128),('process_ipc_completions',192))

def fatal_mutation(kind,saved):
    need(kind in FATAL_CASES and len(saved)==len(FATAL_RANGES) and tuple(map(len,saved))==tuple(n for _,n in FATAL_RANGES),'terminal fatal input')
    need(struct.unpack('<3Q',saved[0])==(1<<32,5<<32|4,0),'terminal fatal live lease')
    owner=3<<32|2
    need(struct.unpack_from('<3Q',saved[1])==(owner,owner^0xffffffffffffffff,0),'terminal fatal released PIO')
    for slot,gen in ((0,1),(2,3),(3,4),(4,5)):
        task_state,task_gen=struct.unpack_from('<2Q',saved[2],slot*1024)
        need(task_state in (1,2,6) and task_gen==gen,'terminal fatal live identities')
    offset=0 if kind=='root-generation' else 8
    damaged=bytearray(saved[0]);struct.pack_into('<Q',damaged,offset,struct.unpack_from('<Q',damaged,offset)[0]+(1<<32))
    return [bytes(damaged)]+saved[1:],[(0,offset,bytes(damaged[offset:offset+8]))]

FATAL_BODY=r'''
from pathlib import Path
import gdb,struct,json,hashlib
S=CONFIG['s'];KIND=CONFIG['kind'];OUT=Path(CONFIG['out'])
RANGES=[(S[name],size) for name,size in FATAL_RANGES]
injected=False;fenced=False;diagnosed=False;saved=None
inferior=gdb.selected_inferior()
def reg(name):return int(gdb.parse_and_eval('$'+name))&0xffffffffffffffff
def mem(address,size):return bytes(inferior.read_memory(address,size))
def q(address):return struct.unpack('<Q',mem(address,8))[0]
def state():return [mem(a,n) for a,n in RANGES]
def event(kind,**row):gdb.write('TERMINAL_FATAL '+json.dumps(dict(kind=kind,**row),sort_keys=True)+'\n')
def snapshot(name,values):
    raw=b''.join(values)
    with (OUT/(name+'.bin')).open('xb') as stream:assert stream.write(raw)==len(raw)
    return hashlib.sha256(raw).hexdigest()
class Probe(gdb.Breakpoint):
    def __init__(self,address,label,enabled=True):
        super().__init__('*'+hex(address),internal=True);self.label=label;self.enabled=enabled
    def stop(self):
        try:self.capture()
        except Exception as error:
            gdb.write('TERMINAL_FATAL_OBSERVER_FAIL '+self.label+' '+repr(error)+'\n');gdb.execute('quit 71')
        return False
    def capture(self):
        global injected,fenced,diagnosed,saved
        if self.label=='trigger':
            if struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]!=4:return
            assert not injected and not reg('eflags')&512
            assert q(S['syscall_rax'])==127 and struct.unpack('<6I',mem(q(S['syscall_rdi']),24))==(1,24,5,0,0,0)
            self.enabled=False;before=state();changed,writes=fatal_mutation(KIND,before)
            original=snapshot('before',before)
            for index,offset,raw in writes:inferior.write_memory(RANGES[index][0]+offset,raw)
            assert state()==changed
            saved=changed;injected=True;port_hook.enabled=True
            for hook in forbidden:hook.enabled=True
            event('inject',case=KIND,original=original,sha=snapshot('damaged',saved),writes=8)
        elif self.label=='port':
            assert injected and not fenced and state()==saved
            assert reg('edx')&65535==0x3f6 and reg('eax')&255==6
            assert mem(S['native_pio_out8.done']-1,1)==b'\xee'
            fenced=True;self.enabled=False;event('fence',physical=1,sha=snapshot('fenced',state()))
        elif self.label=='diagnostic':
            if not injected:return
            assert fenced and not diagnosed and state()==saved and not reg('eflags')&512
            diagnosed=True;event('diagnostic',sha=snapshot('diagnostic',state()),interrupts=0)
        elif self.label=='halt':
            assert injected and fenced and diagnosed and state()==saved and not reg('eflags')&512
            assert mem(S['halt64'],4)==b'\xfa\xf4\xeb\xfd'
            event('halt',sha=snapshot('halt',state()),cli_hlt=1);gdb.execute('detach');gdb.execute('quit 0')
        else:raise AssertionError('cleanup/resume after terminal corruption')
Probe(S['native_terminal_syscall64'],'trigger')
port_hook=Probe(S['native_pio_out8.done'],'port',False)
Probe(S['serial_init64'],'diagnostic');Probe(S['halt64'],'halt')
forbidden=[Probe(S[name],'forbidden',False) for name in (
    'process_run_resume64','family_terminal64','scheduler_force_cleanup64','scheduler_release_task_frames64')]
'''

def fatal_observer(config,folder,kind):
    need(kind in FATAL_CASES,'terminal fatal case')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+
        repr(dict(s=config['s'],kind=kind,out=folder.as_posix()))+'\nFATAL_CASES='+repr(FATAL_CASES)+
        '\nFATAL_RANGES='+repr(FATAL_RANGES)+'\n'+inspect.getsource(need)+'\n'+inspect.getsource(fatal_mutation)+
        live.cpu.defer_observer_callbacks(FATAL_BODY,('Probe',))+'\nend\ncontinue\n')

def validate_fatal(serial,trace,kind,folder):
    need(kind in FATAL_CASES and 'OBSERVER_FAIL' not in trace,'terminal fatal observer')
    events=[json.loads(s) for s in re.findall(r'^TERMINAL_FATAL (.+)$',trace,re.M)]
    need([e['kind'] for e in events]==['inject','fence','diagnostic','halt'],'terminal fatal exact path')
    marker='REIST_X86_64_EXCEPTION_FATAL pio=1'
    need(serial.count('REIST_X86_64_EXCEPTION_FATAL')==1 and marker in serial and
        all(s not in serial for s in (live.wide.process.DONE,live.wide.process.SUCCESS)), 'terminal fatal no continuation')
    # The peer may already have exited. No other family task may have reaped.
    receipts=list(live.wide.process.REAP.finditer(serial))
    need(len(receipts)==serial.count('PROCESS_REAP_OK') and len(receipts)<=1,'terminal fatal prior receipt extent')
    for match in receipts:
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(match[1]))
        need((slot,gen,status,state)==(1,2,77,4) and ticks<=32 and 0x410000<=rip<0x440000 and match.end()<serial.index(marker),'terminal fatal peer receipt')
    def load(name):
        path=folder/(name+'.bin');size=sum(n for _,n in FATAL_RANGES)
        live.pio.regular(path,size);raw=path.read_bytes();need(len(raw)==size,'terminal fatal raw extent')
        parts=[];offset=0
        for _,count in FATAL_RANGES:parts.append(raw[offset:offset+count]);offset+=count
        return raw,parts
    original,before=load('before');changed,writes=fatal_mutation(kind,before);damaged=b''.join(changed);sha=hashlib.sha256(damaged).hexdigest()
    need(events==[dict(kind='inject',case=kind,original=hashlib.sha256(original).hexdigest(),sha=sha,writes=8),
        dict(kind='fence',physical=1,sha=sha),dict(kind='diagnostic',sha=sha,interrupts=0),dict(kind='halt',sha=sha,cli_hlt=1)],'terminal fatal exact snapshots')
    need(all(load(n)[0]==damaged for n in ('damaged','fenced','diagnostic','halt')),'terminal fatal no in-place repair')
    return events

def main():
    from verify_x86_64_terminal import binding,qualified_prefix,BASE,IMAGE
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--fatal',action='store_true');args=parser.parse_args()
    image=args.image.resolve();base=args.evidence.resolve();f=binding()
    need(image==IMAGE and base==BASE/('fatal' if args.fatal else 'guests') and not list(base.glob('attempt-*')),'terminal unique matrix')
    for n in range(1,12 if args.fatal else 11):need(read(BASE/f'gate-{n:02d}.json')['passed'],'terminal preceding gate')
    config,counts,raw=live.image_config(image)
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    prefix=[] if args.fatal else qualified_prefix(f)
    summary=dict(passed=False,closed=False,candidate=f['candidate'],image=link(image),fatal=args.fatal,cases=list(prefix),
        guest_elapsed=sum(r['elapsed'] for r in prefix),new_guests=0,new_guest_elapsed=0.0)
    begin=time.monotonic()
    try:
        cases=[(k,2,4096,None) for k in FATAL_CASES] if args.fatal else CASES[len(prefix):]
        for case,layout,ram,point in cases:
            binding();need(summary['guest_elapsed']+45<=(90 if args.fatal else 1125),'terminal finite reserve')
            need(summary['new_guests']<(2 if args.fatal else 19) and summary['new_guest_elapsed']+45<=(90 if args.fatal else 855),'terminal fresh reservation')
            oom=None if point is None else 0 if point=='first' else counts['program']//2 if point=='middle' else counts['program']-1
            out=folder/f'guest-{case}-{layout}-{ram}-{point}';out.mkdir()
            row=dict(case=case,layout=layout,ram=ram,point=point,oom=oom,folder=out.relative_to(ROOT).as_posix(),passed=False)
            summary['cases'].append(row);summary['new_guests']+=1;started=time.monotonic()
            try:
                fixture=live.pio.Fixture(out,filesystem=live.media.LAYOUTS[layout],file_program=raw if args.fatal else live.file.program_variant(raw,case))
                code=fatal_observer(config,out,case) if args.fatal else observer(config,out,case,layout,oom,raw)
                serial,trace=live.wide.transport.capture(image,out,code,ram,fixture,halt_witness=args.fatal,
                    binary_memory=None if args.fatal else 'equivalence',diagnostic_metrics=True,service_pio_budget=True)
                if args.fatal:validate_fatal(serial,trace,case,out)
                else:validate(serial,trace,case,layout,oom,counts,raw,out)
                need(link(image)==summary['image'],'terminal immutable image');row['passed']=True
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed'];summary['new_guest_elapsed']+=row['elapsed']
            need(row['elapsed']<=45,'terminal deadline including cleanup')
            print('TERMINAL_GUEST_OK',case,layout,ram,point,round(row['elapsed'],3),flush=True)
        need(len(summary['cases'])==(2 if args.fatal else 25) and time.monotonic()-begin<=(120 if args.fatal else 1200),'terminal complete matrix')
        summary['passed']=True;return 0
    except Exception as error:
        summary['error']=str(error);print('TERMINAL_FAIL',error,flush=True);return 1
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-begin)
        with (folder/'summary.json').open('x') as stream:json.dump(summary,stream,indent=2)
        print('TERMINAL_EVIDENCE',folder,flush=True)
if __name__=='__main__':raise SystemExit(main())
