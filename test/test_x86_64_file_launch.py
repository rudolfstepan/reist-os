"""File launch producer and actual runtime-observer regressions."""
from pathlib import Path
from unittest.mock import patch
import ast,copy,hashlib,json,os,struct,subprocess,sys,unittest,uuid
from contextlib import ExitStack
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_boot_programs as producer
from build_user_program import find_zig
import run_qemu_x86_64_file_launch as runtime

MAKE_FILE_PROFILE=('PROCESSES','IPC','RAM','HEAP','RUNTIME','PROGRAMS','LIFECYCLE',
                   'STARTUP','IMPORT','PIO','BLOCK','WIDE','BLOCK_PROFILE','FILESYSTEM','FILE_LAUNCH')
MAKE_CASE_DEFAULTS=('FILESYSTEM_CASE','PIO_CASE','STARTUP_CASE')

def direct_make_plan(folder,overrides):
    """Exercise the actual Make parser/recipe without creating its output tree."""
    output=folder/'dry-run'
    if output.exists():raise AssertionError('Make dry-run output already exists')
    options={'X86_64_NATIVE_'+name:'1' for name in MAKE_FILE_PROFILE};options.update(overrides)
    environment={k:v for k,v in os.environ.items() if not k.upper().startswith('X86_64_')
                 and k.upper() not in ('MAKEFLAGS','MFLAGS','MAKEOVERRIDES','MAKEFILES')}
    command=['make','--no-print-directory','-n','x86_64-bootstrap',
             'OUTPUT_DIR='+output.relative_to(ROOT).as_posix(),*[k+'='+v for k,v in options.items()]]
    result=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,timeout=10)
    if len(result.stdout)+len(result.stderr)>131072:raise AssertionError('Make dry-run log bound')
    with (folder/('plan-'+uuid.uuid4().hex+'.json')).open('x',encoding='utf-8') as evidence:
        json.dump(dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr),evidence,indent=2)
    if output.exists():raise AssertionError('Make dry-run unexpectedly published output')
    return result

RETIREMENT_HOST=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define REQUIRE(v,e) do { if(!(v)) return (e); } while(0)
#define REIST_PIO_FENCE 2
#define IPC_CLOSE 49
#define S1(n,a) close_endpoint(n,a)
/* Actual source statements below; only syscall/scheduling boundaries adapted. */
/* CONTROL_TYPE */
static const uint64_t fs=(4ULL<<32)|3,driver=(3ULL<<32)|2;
static const uint32_t control_ep=101,driver_control=102;
static unsigned mode,calls,fail_at,fs_done,fs_reaped,driver_reaped,fenced,closed;
static unsigned fs_cancels,driver_cancels,stuck,wrong_status,stale;
static int64_t fs_exit,driver_exit;
static char order[16];
static int record(char op) {
    if(calls>=sizeof(order)-1) return -1;
    order[calls++]=op;return calls==fail_at?-1:0;
}
static int control_send(uint32_t ep,const Control *c) {
    return ep!=control_ep || c->phase!=4 || c->result!=-5?-1:0;
}
static int actual_fs_exit(void) {
    Control c={0};int result=-5;
    /* FS_REPLY_EXIT */
    return -999;
}
static int64_t port_control(uint64_t owner,unsigned operation) {
    if(record('F') || owner!=driver || operation!=REIST_PIO_FENCE) return -5;
    fenced=1;return 0;
}
static int64_t task_control(unsigned op,uint64_t owner,unsigned timeout) {
    if(record(op==3?'C':timeout==1?'S':'W')) return -5;
    if(!fenced || stale || (owner!=fs && owner!=driver)) return -13;
    if(op==3) {
        if(timeout) return -22;
        if(owner==fs) {
            fs_cancels++;
            if(!fs_done) { fs_done=1;fs_exit=2LL<<32; }
        } else { driver_cancels++; }
        return 0;
    }
    if(op!=2 || (timeout!=1000 && timeout!=1)) return -22;
    if(timeout==1) return (owner==fs?fs_reaped:driver_reaped)?-10:-110;
    if(stuck) return -110;
    if(owner==fs) {
        if(fs_reaped) return -10;
        if(!fs_done && mode==5) { fs_exit=actual_fs_exit();fs_done=1; }
        if(!fs_done) return -110;
        fs_reaped=1;return wrong_status?91:fs_exit;
    }
    if(!fs_reaped || !driver_cancels || driver_reaped) return -10;
    driver_reaped=1;return driver_exit;
}
static int close_endpoint(unsigned operation,uint32_t ep) {
    if(record('X') || operation!=IPC_CLOSE || !fenced || !fs_reaped || !driver_reaped) return -5;
    if(ep!=(closed?driver_control:control_ep) || closed>=2) return -9;
    closed++;return 0;
}
static int actual_retire(void) {
    /* RETIREMENT */
    return 0;
}
static void reset(unsigned m,unsigned already_exited) {
    mode=m;calls=fail_at=fs_reaped=driver_reaped=fenced=closed=0;
    fs_cancels=driver_cancels=stuck=wrong_status=stale=0;memset(order,0,sizeof(order));
    fs_done=m==1 || (m==5 && already_exited);
    fs_exit=m==1?((1LL<<32)|134):m==5?actual_fs_exit():0;
    driver_exit=m==5?((1LL<<32)|134):(2LL<<32);
}
int main(void) {
    unsigned checked=0;const unsigned modes[]={0,1,4,5};
    for(unsigned n=0;n<4;n++) for(unsigned ready=0;ready<2;ready++) {
        unsigned m=modes[n];reset(m,ready);int result=actual_retire();
        if(result) {printf("RETIREMENT_FAIL mode=%u already_exited=%u result=%d order=%s\n",m,ready,result,order);return 1;}
        const char *expected=m==5?"FWCW FSSXX":"FCWCW FSSXX";
        char compact[16]={0};unsigned count=0;
        for(unsigned i=0;expected[i];i++) if(expected[i]!=' ') compact[count++]=expected[i];
        if(strcmp(order,compact) || fs_cancels!=(m!=5) || driver_cancels!=1 || closed!=2 || !fs_reaped || !driver_reaped) return 2;
        checked++;
        const unsigned normal_errors[]={219,220,221,222,223,224,224,224,225,225};
        const unsigned init_errors[]={219,221,222,223,224,224,224,225,225};
        for(unsigned i=1;i<=count;i++) {
            reset(m,ready);fail_at=i;result=actual_retire();
            if(result!=(int)(m==5?init_errors:normal_errors)[i-1] || calls!=i || strncmp(order,compact,i)) return 3;
            checked++;
        }
    }
    for(unsigned fault=0;fault<3;fault++) {
        reset(5,0);stuck=fault==0;wrong_status=fault==1;stale=fault==2;
        if(actual_retire()!=221 || calls!=2 || closed || driver_cancels) return 4;
        checked++;
    }
    printf("FILE_RETIREMENT_HOST_PASS cases=%u\n",checked);return 0;
}
'''

def sample(case=0):
    raw=bytearray(512);raw[:7]=b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHIQQQIHHHHHH',raw,16,2,62,1,0x410078,64,0,0,64,56,1,0,0,0)
    struct.pack_into('<II6Q',raw,64,1,5,0,0x410000,0x410000,121,121,4096);raw[120]=0xc3;raw=bytes(raw)
    image=runtime.program_variant(raw,case);disk=runtime.media.image('ext2-1k',program=image)
    counts=dict(driver=25,fs=30,program=20,sha=dict(driver='a'*64,fs='b'*64,program=hashlib.sha256(producer.prepare(raw,[],True)).hexdigest()))
    plan=runtime.roles(case);per=len(plan)//2;events=[];receipts=[[],[]]
    def emit(kind,**fields):events.append(dict(kind=kind,**fields))
    def release(gen):
        info=plan[gen];emit('release',gen=gen,slot=info['slot'],frames=12,before=1000,after=1012,fenced=1)
        row=struct.pack('<4I2Q',info['slot'],gen,info['status'],info['state'],32 if info['status']==256 else 8,0x410100)
        receipts[(gen-1)//per].append('REIST_X86_64_PROCESS_REAP_OK v1='+row.hex().upper())
    def created(gen):
        role=plan[gen]['role'];emit('copy',gen=gen,bytes=266336,sha=counts['sha'][role]);emit('create',gen=gen,acquired=counts[role]);emit('start',gen=gen,slot=plan[gen]['slot'])
    def terminate(gen):
        if plan[gen]['status']==134:emit('fault',gen=gen,slot=plan[gen]['slot'],vector=6)
        if plan[gen]['slot']>=2 and not plan[gen]['status']:emit('cancel',gen=gen,slot=plan[gen]['slot'],state=6)
    emit('poison',bytes=270336);emit('boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)
    canonical=runtime.frames(2,image)
    for run in range(2):
        root=run*per+1;emit('start',gen=root,slot=0);emit('start',gen=root+1,slot=1)
        for driver,info in plan.items():
            if info['root']!=root or info['role']!='driver':continue
            gen=driver+1;created(driver);created(gen)
            for g in (driver,gen):emit('immutable',gen=g,slot=plan[g]['slot'],source=266336,device=int(g==driver))
            emit('bind',gen=driver,owner=(driver<<32)|2);emit('driver_ready',gen=driver,peer=(gen<<32)|3,capacity=256,deadline=1000)
            first=not info['round'];partial=case in (6,7) and first;lbas=[0,1] if partial else [0,2,3,4,5,*range(44,44+(len(image)+511)//512)]
            for sequence,lba in enumerate(lbas[1:],1):
                emit('block_request',gen=driver,client=gen,sequence=sequence,lba=lba)
                if not partial:emit('block_reply',gen=driver,sequence=sequence,lba=lba,sha=hashlib.sha256(disk[lba*512:(lba+1)*512]).hexdigest())
            if case!=7:
                bad=case==6 and first;emit('fs_ready',gen=gen,peer=(driver<<32)|2,status=-5 if bad else 0,deadline=1000,cached=0 if bad else 4)
                n=0 if bad else 1 if case==9 or case in (5,10) and first else len(canonical)
                for sequence in range(1,n+1):
                    emit('fs_request',gen=gen,sequence=sequence,op=5 if sequence==1 else 6,sha=hashlib.sha256(canonical[sequence-1]).hexdigest())
                    if not (case==5 and first):emit('fs_reply',gen=gen,sequence=sequence,status=0,bad=int(case==10 and first),sha=hashlib.sha256(runtime.frames(2,image,True)[sequence-1]).hexdigest())
                status=-22 if case==4 else -27 if case==9 else -71 if case==10 and first else -32 if case==5 and first else -5 if bad else 0
                digest=hashlib.sha256(b'\xa5'*266336).hexdigest() if status else counts['sha']['program']
                emit('file_result',gen=gen,caller=root,status=status,sha=digest,scrub=int(not bad))
            actual=b''.join(disk[lba*512:(lba+1)*512] for lba in lbas);amount=768 if partial else len(actual)
            if case==7:terminate(root)
            terminate(gen);release(gen);terminate(driver)
            emit('retire',gen=driver,identify=512,data=amount,lbas=lbas,sha=hashlib.sha256(actual[:amount]).hexdigest(),fenced=1);release(driver)
            program=gen+1
            if program in plan and plan[program]['role']=='program':
                if case==8 and first:
                    emit('image_retire',owner=root<<32,gen=driver,slot=2,frames=3,before=997,after=1000,scrub=1)
                    emit('oom',owner=root<<32,acquired=0);emit('rollback',owner=root<<32,acquired=0,free=1000,before=1000)
                created(program);emit('program_ready',gen=program,slot=2,source=266336,device=0,sha=counts['sha']['program']);terminate(program);release(program)
        release(root);release(root+1)
        emit('trace_drained',run=run+1,events=100,sha='c'*64);emit('trace_clean',run=run+1,bytes=12304)
        emit('finish',run=run+1,tasks=per,generation=(run+1)*per,free=1000,initial=1000)
    common=[m for m in runtime.wide.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[runtime.wide.process.SUCCESS]
    at=common.index('REIST_X86_64_C_KERNEL_CONTROL_OK')
    done='REIST_X86_64_PROCESS_RUN_OK'
    serial='\n'.join(common[:at]+receipts[0]+[done]+receipts[1]+[done]+common[at:])
    return serial,events,counts,raw

def trace(events):return '\n'.join('FILE_LAUNCH '+json.dumps(e) for e in events)
class FileLaunchTests(unittest.TestCase):
    def oom_context(self,point=0):
        nodes={n.name:n for n in ast.parse(runtime.observer_body()).body if isinstance(n,ast.FunctionDef)}
        symbols={n:0x1000+i*1024 for i,n in enumerate(('family_request','family_records','process_run_generation','elf_context_window','elf_image_selector','family_build_slot','family_initial_free'))}
        memory=bytearray(16384);registers=dict(rdi=2,rax=0,rsp=0x300,rip=0,eflags=0)
        struct.pack_into('<Q',memory,0x300,0x400)
        def put(name,offset,fmt,*values):struct.pack_into(fmt,memory,symbols[name]+offset,*values)
        put('family_request',0,'I',5);put('family_request',24,'Q',0x410000)
        put('family_records',0,'Q',1<<32);put('process_run_generation',0,'I',4)
        put('elf_image_selector',0,'B',7);put('family_build_slot',0,'I',2)
        frames=[0x100010000,0x100012000,0x100013000];record=bytearray(266336)
        for page,frame in zip((0,16,17),frames):
            put('elf_context_window',page*8,'Q',frame);put('elf_context_window',512+page,'B',5);record[24+page]=5
        put('elf_context_window',583,'B',1)
        hooks={};events=[];counter=[1000];pages={f:b'\xa5'*4096 for f in frames}
        class Hook:
            def __init__(self,name,fn):self.enabled=True;self.fn=fn;hooks[name]=self
        class Gdb:
            def execute(self,command):
                name,value=command.removeprefix('set $').split('=')
                registers[name]=registers['rsp']+8 if value=='$rsp+8' else int(value,0)
        env=dict(S=symbols,CONFIG=dict(roles=runtime.roles(8)),OOM=point,CASE=8,DM=0xffff800000000000,MASK=0x3fffff000,
            created=None,created_sources={},source_pointer=0,allocation_count=0,allocation_before=0,allocation_owner=0,allocation_slot=0,
            copies={},injected=set(),starts={3:dict(slot=2,live=False,record=bytes(record))},
            allocator=Hook('allocator',None),start_hook=Hook('start',None),Hook=Hook,gdb=Gdb(),struct=struct,
            reg=lambda n:registers[n],mem=lambda a,n:bytes(memory[a:a+n]),q=lambda a:struct.unpack_from('<Q',memory,a)[0],
            d=lambda a:struct.unpack_from('<I',memory,a)[0],free=lambda:counter[0],mode=lambda:8,
            task=lambda slot:[0]*128,emit=lambda kind,**fields:events.append(dict(kind=kind,**fields)),
            create_watch_enter=lambda:None,create_watch_leave=lambda retry:None,file_pages=lambda fs:[pages[f] for f in fs])
        exec(compile(ast.Module(body=[nodes[n] for n in ('create_begin','allocation','create_end')],type_ignores=[]),'<actual OOM callbacks>','exec'),env)
        if hasattr(runtime,'FILE_OOM_RETIREMENT'):exec(runtime.FILE_OOM_RETIREMENT,env)
        def enter():
            env['create_begin']()
            if 'image_retire_begin' in env:env['image_retire_begin']()
        def retire():
            for frame in frames:
                registers['rdi']=frame
                if 'image_retire_free' in env:env['image_retire_free']()
                pages[frame]=bytes(4096);counter[0]+=1
            memory[symbols['elf_context_window']:symbols['elf_context_window']+592]=bytes(592)
            put('family_initial_free',0,'I',counter[0]);registers['rax']=counter[0]
        def boundary():
            if 'image_retire_end' in env:env['image_retire_end']()
        def rollback():
            for _ in range(point):env['allocation']()
            env['allocation']();registers['rax']=0xfffffffffffffff4;env['create_end']()
        return dict(env=env,enter=enter,retire=retire,boundary=boundary,rollback=rollback,put=put,frames=frames,
            registers=registers,counter=counter,pages=pages,hooks=hooks,events=events)

    def test_actual_oom_transaction_boundary(self):
        for point in (0,10,19):
            with self.subTest(point=point):
                c=self.oom_context(point);c['enter']();c['retire']();c['boundary']();c['rollback']()
                self.assertEqual(c['events'][-1],dict(kind='rollback',owner=1<<32,acquired=point,free=1003,before=1003))
                self.assertIsNone(c['env']['created'])

    def test_actual_oom_retirement_fail_closed(self):
        for bad in ('selector','live','duplicate','unaligned','flags','active','version','owner','early_allocation','reentry',
                    'wrong_free','extra_free','missing_free','dirty','metadata','counter_low','counter_high','kernel_counter',
                    'missing_begin','missing_boundary','rollback_leak','published','generation'):
            with self.subTest(bad=bad):
                c=self.oom_context();e=c['env'];put=c['put']
                with self.assertRaises(AssertionError):
                    if bad=='selector':put('elf_image_selector',0,'B',8)
                    if bad=='live':e['starts'][3]['live']=True
                    if bad=='duplicate':put('elf_context_window',16*8,'Q',c['frames'][0])
                    if bad=='unaligned':put('elf_context_window',0,'Q',c['frames'][0]+1)
                    if bad=='flags':put('elf_context_window',512,'B',7)
                    if bad=='active':put('elf_context_window',583,'B',0)
                    if bad=='version':put('family_request',0,'I',4)
                    if bad=='owner':put('family_records',0,'Q',2<<32)
                    if bad=='missing_begin':e['create_begin']();e['image_retire_end']()
                    c['enter']()
                    if bad=='early_allocation':e['allocation']()
                    if bad=='reentry':e['image_retire_begin']()
                    if bad=='wrong_free':c['registers']['rdi']=c['frames'][1];e['image_retire_free']()
                    c['retire']()
                    if bad=='extra_free':e['image_retire_free']()
                    if bad=='missing_free':e['image_retirement']['freed'].pop()
                    if bad=='dirty':c['pages'][c['frames'][-1]]=bytes(4095)+b'X'
                    if bad=='metadata':put('elf_context_window',17*8,'Q',c['frames'][-1])
                    if bad=='counter_low':c['counter'][0]-=1
                    if bad=='counter_high':c['counter'][0]+=1
                    if bad=='kernel_counter':put('family_initial_free',0,'I',1002)
                    if bad=='missing_boundary':e['allocation']()
                    c['boundary']()
                    if bad=='rollback_leak':c['counter'][0]-=1
                    if bad=='published':e['copies'][5]=b'bad'
                    if bad=='generation':put('process_run_generation',0,'I',5)
                    c['rollback']()

    def test_actual_oom_hooks_cold_and_receipt_guards(self):
        for unrelated in ('normal','slot3','retry','driver'):
            c=self.oom_context();e=c['env']
            if unrelated=='normal':e['OOM']=None
            if unrelated=='slot3':c['registers']['rdi']=3
            if unrelated=='retry':e['injected'].add(1<<32)
            if unrelated=='driver':c['put']('process_run_generation',0,'I',2)
            e['create_begin']()
            self.assertIsNone(e['image_retirement'])
            self.assertFalse(any(c['hooks'][n].enabled for n in ('x86_64_elf64_release64','physical_frame_free64','family_create64.cached_entry')))
        serial,events,counts,raw=sample(8)
        for key,value in (('gen',2),('slot',3),('owner',2<<32),('frames',0),('frames',65),('after',1001),('before',996),('scrub',0)):
            bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='image_retire')[key]=value
            with self.assertRaises(ValueError,msg=key):runtime.validate(serial,trace(bad),8,2,0,counts,raw)
        for kind in ('release','oom','rollback','copy'):
            bad=copy.deepcopy(events);i=next(i for i,e in enumerate(bad) if e['kind']=='image_retire')
            gen=bad[i]['gen'];j=next(j for j,e in enumerate(bad) if e['kind']==kind and (e.get('gen')==(gen if kind=='release' else gen+2) if kind in ('release','copy') else True))
            bad[i],bad[j]=bad[j],bad[i]
            with self.assertRaises(ValueError,msg=kind):runtime.validate(serial,trace(bad),8,2,0,counts,raw)

    def test_actual_retirement_o0_o2_reply_exit_order_and_failures(self):
        launch=(ROOT/'arch/x86_64/user/file_launch.c').read_text()
        fs_source=(ROOT/'arch/x86_64/user/filesystem.c').read_text()
        start='        REQUIRE(!port_control(driver,REIST_PIO_FENCE),219);'
        end='        previous_driver=driver;previous_fs=fs;'
        self.assertEqual(launch.count(start),1);self.assertEqual(launch.count(end),1)
        retirement=launch[launch.index(start):launch.index(end)]
        reply='    c.phase=4;c.result=result;REQUIRE(!control_send(control_ep,&c),244);'
        self.assertEqual(fs_source.count(reply),1)
        reply_exit=fs_source[fs_source.index(reply):fs_source.index('    exercising=1;')]
        control=fs_source[fs_source.index('typedef struct {'):fs_source.index('} Control;')+len('} Control;')]
        source=RETIREMENT_HOST.replace('/* CONTROL_TYPE */',control).replace('/* FS_REPLY_EXIT */',reply_exit).replace('/* RETIREMENT */',retirement)
        folder=ROOT/'build/codex-agent/r83am-file-launch'/('retirement-host-'+uuid.uuid4().hex);folder.mkdir()
        unit=folder/'actual-retirement.c';unit.write_text(source,encoding='utf-8')
        for opt in ('-O0','-O2'):
            with self.subTest(opt=opt):
                exe=folder/(opt[1:]+'.exe')
                built=subprocess.run(['gcc','-std=c11',opt,'-Wall','-Wextra','-Werror',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,timeout=30)
                (folder/(opt[1:]+'-build.log')).write_bytes(built.stdout+built.stderr)
                self.assertEqual(built.returncode,0,(built.stdout+built.stderr).decode(errors='replace')[-2000:])
                ran=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=5)
                (folder/(opt[1:]+'-run.log')).write_bytes(ran.stdout+ran.stderr)
                output=(ran.stdout+ran.stderr).decode(errors='replace')
                self.assertEqual(ran.returncode,0,output)
                self.assertIn('FILE_RETIREMENT_HOST_PASS cases=89',output);print(opt,output.strip())

    def test_regular_binary_matrix_dispatch_and_original_observer(self):
        # Execute the actual capture assignment inside main, not a parallel
        # test-only dispatcher. No build, disk publication or guest is started.
        tree=ast.parse((ROOT/'scripts/run_qemu_x86_64_file_launch.py').read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        matrix=next(n.value for n in main.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='matrix' for t in n.targets))
        cases=eval(compile(ast.Expression(matrix),'<actual matrix>','eval'))
        calls=[n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Tuple) and [x.id for x in t.elts]==['serial','trace'] for t in n.targets)]
        self.assertEqual(len(calls),1);self.assertEqual(len(cases),18)
        dispatch=compile(ast.Module(body=calls,type_ignores=[]),'<actual matrix capture>','exec')
        folder=ROOT/'build/codex-agent/host-file-capture';raw=sample()[3]
        original=runtime.observer({},dict(symbols={}),folder,0,2,None,{},raw)
        for case,layout,ram,oom in cases:
            with self.subTest(case=case,layout=layout,ram=ram,oom=oom):
                fixture=object();image=folder/'image.elf'
                env=dict(vars(runtime),image=image,out=folder,case=case,layout=layout,ram=ram,oom=oom,
                         symbols={},core={'symbols':{}},addresses={},raw=raw,fixture=fixture)
                with patch.object(runtime,'observer',return_value=original) as observer, patch.object(runtime.wide.transport,'capture',return_value=('serial','trace')) as capture:
                    env['observer']=observer;exec(dispatch,env)
                    observer.assert_called_once_with({},dict(symbols={}),folder,case,layout,oom,{},raw)
                    self.assertEqual((env['serial'],env['trace']),('serial','trace'))
                    # Reject option drift before unittest formats the large
                    # immutable observer payload in a failure message.
                    self.assertEqual(capture.call_args.kwargs,{'binary_memory':'full'})
                    capture.assert_called_once_with(image,folder,original.replace('set logging enabled on\n','set logging redirect on\nset logging enabled on\n'),ram,fixture,binary_memory='full')
                    code=capture.call_args.args[2]
                    self.assertEqual(code.count('set logging redirect on\n'),1)
                    self.assertEqual(code.replace('set logging redirect on\n',''),original)

    def test_regular_binary_capture_fail_closed_without_fallback(self):
        image=Path('image.elf');folder=Path('evidence');fixture=object()
        code='set logging enabled on\npython\noriginal_assertions()\nend\ncontinue\n'
        with patch.object(runtime.wide.transport,'capture') as capture:
            for broken in (code.replace('set logging enabled on\n',''),code+code):
                with self.assertRaises(ValueError):runtime.capture(image,folder,broken,4096,fixture)
            capture.assert_not_called()
            for error in (ValueError('binary mismatch'),RuntimeError('capture failure'),OSError('export failure')):
                capture.reset_mock();capture.side_effect=error
                with self.assertRaises(type(error)) as raised:runtime.capture(image,folder,code,8192,fixture)
                self.assertIs(raised.exception,error);self.assertEqual(capture.call_count,1)
                self.assertEqual(capture.call_args.kwargs,{'binary_memory':'full'})

    def test_actual_physical_page_batches_are_complete_and_bounded(self):
        code=runtime.observer_body();helpers={n.name:n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)}
        calls=[];base=0x100000000;frames=[base+n*4096 for n in range(69)]
        def mem(address,size):
            calls.append((address,size))
            self.assertLessEqual(size,270336)
            self.assertEqual(address%4096,0);self.assertEqual(size%4096,0)
            return b''.join(bytes([(f-base)//4096%251])*4096 for f in range(address,address+size,4096))
        ns=dict(mem=mem,DM=0,MASK=0x3fffff000,struct=struct)
        exec(compile(ast.Module(body=[helpers['file_pages']],type_ignores=[]),'<actual page batch>','exec'),ns)
        read=ns['file_pages'];expected=[bytes([n])*4096 for n in range(69)]
        self.assertEqual(read(list(reversed(frames))),list(reversed(expected)))
        self.assertEqual(calls,[(base,66*4096),(base+66*4096,3*4096)])
        calls.clear();self.assertEqual(read([frames[2],frames[0]]),[expected[2],expected[0]])
        self.assertEqual(calls,[(base,4096),(base+8192,4096)]) # Never read the gap.
        for bad in ([frames[0]]*2,[base+1],[True],[0],frames+[base+69*4096]):
            calls.clear()
            with self.assertRaises(AssertionError):read(bad)
            self.assertEqual(calls,[])
        calls.clear();self.assertEqual(read([]),[]);self.assertEqual(calls,[])
        ns['mem']=lambda a,n:mem(a,n)[:-1]
        with self.assertRaises(AssertionError):read(frames)
        ns['mem']=lambda a,n:b'\0'*(n-1)+b'\1'
        self.assertFalse(all(not any(raw) for raw in read(frames)))

    def test_actual_image_leaves_and_start_batch_reject_corruption(self):
        code=runtime.observer_body();helpers={n.name:n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)}
        base=0x100000000;parents={base:base+4096|1,base+4096:base+8192|1,base+8192+16:base+12288|1}
        leaves=list(range(64));calls=[]
        ns=dict(q=lambda a:parents[a],mem=lambda a,n:(calls.append((a,n)) or struct.pack('<64Q',*leaves)),DM=0,MASK=0x3fffff000,struct=struct)
        exec(compile(ast.Module(body=[helpers['file_leaves']],type_ignores=[]),'<actual leaf batch>','exec'),ns)
        self.assertEqual(ns['file_leaves']((0,0,base)),tuple(leaves));self.assertEqual(calls,[(base+12288,512)])
        for address,value in list(parents.items()):
            for bad in (0,value|128):
                parents[address]=bad;calls.clear()
                with self.assertRaises(AssertionError):ns['file_leaves']((0,0,base))
                self.assertEqual(calls,[])
            parents[address]=value
        ns['mem']=lambda a,n:bytes(n-1)
        with self.assertRaises(AssertionError):ns['file_leaves']((0,0,base))
        # Execute the actual transformed publication callback with canonical
        # startup records; no fake replacement for its flag/content assertions.
        record=bytearray(266336);struct.pack_into('<Q',record,16,0x410000)
        record[24+8:24+16]=bytes([6])*8;record[24+16]=5
        t=[0]*128;t[0]=2;t[1]=5;t[2]=base;t[68]=0x410000;t[69]=0x40ffa0
        payload={};leaves=[0]*64
        for page in range(8,17):
            frame=base+(page+16)*4096;pf=record[24+page]
            leaves[page]=frame|5|(2 if pf==6 else 0)|(0 if pf==5 else 1<<63)
            if pf==6:t[3 if page==8 else 4+page]=frame
            payload[frame]=bytes(4096)
        args={100:b'/boot.prg',200:b'00000001',300:b'0'};fetched=[];events=[]
        def user(task,address,size):
            if address==t[69]:return struct.pack('<10Q',3,100,200,300,0,0,0x52534901,0,0,0)
            if address in args:return args[address]+bytes(128-len(args[address]))
            self.assertEqual((address,size),(0x408000,32768));return bytes(32768)
        def fetch(frames):fetched.extend(frames);return [payload[f] for f in frames]
        ns=dict(mode=lambda:8,d=lambda a:2,task=lambda slot:tuple(t),reg=lambda n:0,
            S={'scheduler_current_slot':1,'scheduler_tasks':10000},mem=lambda a,n:bytes(n),
            file_leaves=lambda task:tuple(leaves),file_pages=fetch,copies={5:bytes(record)},starts={},CONFIG={'roles':runtime.roles(0)},
            MASK=0x3fffff000,NX=1<<63,CASE=0,struct=struct,user=user,emit=lambda *a,**k:events.append(k),
            start_hook=type('Hook',(),{'enabled':True})())
        exec(compile(ast.Module(body=[helpers['start']],type_ignores=[]),'<actual batched start>','exec'),ns)
        ns['start']();self.assertEqual(len(fetched),9);self.assertEqual(len(events),1)
        for page in (8,16):
            ns['starts'].clear();events.clear();fetched.clear();saved=leaves[page];leaves[page]^=4
            with self.assertRaises(AssertionError):ns['start']()
            self.assertEqual(fetched,[]);self.assertEqual(events,[]);leaves[page]=saved
        for page in (8,16):
            frame=leaves[page]&ns['MASK'];payload[frame]=bytes(4095)+b'\1';ns['starts'].clear()
            with self.assertRaises(AssertionError):ns['start']()
            self.assertFalse(ns['starts']);payload[frame]=bytes(4096)

    def test_actual_bounded_table_page_reads(self):
        tables={n*4096:bytearray(4096) for n in range(1,5)}
        struct.pack_into('<Q',tables[4096],0,8192|1)
        struct.pack_into('<Q',tables[8192],0,12288|1)
        struct.pack_into('<Q',tables[12288],2*8,16384|1)
        payload=bytes(n%251 for n in range(67*4096))
        for n in range(67):struct.pack_into('<Q',tables[16384],n*8,(0x10000+n*4096)|5)
        calls=[]
        def mem(address,size):
            calls.append((address,size))
            for start,raw in tables.items():
                if start<=address and address+size<=start+len(raw):return bytes(raw[address-start:address-start+size])
            self.assertGreaterEqual(address,0x10000)
            self.assertLessEqual(address+size,0x10000+len(payload))
            return payload[address-0x10000:address-0x10000+size]
        context=dict(mem=mem,struct=struct,DM=0,MASK=0x000ffffffffff000)
        node=[n for n in ast.parse(runtime.observer_body()).body if isinstance(n,ast.FunctionDef) and n.name=='user'][-1]
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual file observer>','exec'),context)
        read=context['user'];task=(0,0,4096)
        self.assertEqual(read(task,0x400000+123,266336),payload[123:123+266336])
        self.assertEqual(calls[:4],[(4096,8),(8192,8),(12288+16,8),(16384,66*8)])
        self.assertEqual(len(calls),5)
        calls.clear();self.assertEqual(read(task,0x400000,12),payload[:12])
        self.assertEqual(sum(size for address,size in calls if address<0x10000),32)
        calls.clear();self.assertEqual(read(task,0x400000+4092,12),payload[4092:4104])
        self.assertEqual(calls[3],(16384,16))
        # A real contiguous range across a PT boundary needs two bounded spans.
        tables[20480]=bytearray(4096);struct.pack_into('<Q',tables[12288],3*8,20480|1)
        struct.pack_into('<Q',tables[16384],511*8,0x10000|5)
        for n in range(66):struct.pack_into('<Q',tables[20480],n*8,(0x11000+n*4096)|5)
        calls.clear();self.assertEqual(read(task,0x5ff000+123,266336),payload[123:123+266336])
        self.assertEqual(calls[:5],[(4096,8),(8192,8),(12288+16,16),(16384+511*8,8),(20480,65*8)])
        self.assertEqual(len(calls),6)
        struct.pack_into('<Q',tables[20480],0,0x11000|1);calls.clear()
        with self.assertRaises(AssertionError):read(task,0x5ff000+4092,12)
        self.assertTrue(all(address<0x10000 for address,size in calls))
        context['mem']=lambda address,size:mem(address,size)[:-1]
        with self.assertRaises(AssertionError):read(task,0x400000,12)
        context['mem']=mem
        calls.clear();self.assertEqual(read(task,0x400000,0),b'');self.assertEqual(calls,[])
        for bad in (1,4,0):
            struct.pack_into('<Q',tables[16384],0,0x10000|bad)
            calls.clear()
            with self.assertRaises(AssertionError):read(task,0x400000,1)
            self.assertTrue(all(address<0x10000 for address,size in calls))
        for va,n in ((0x400000,266337),((1<<64)-1,2),(-1,1),(0,True)):
            calls.clear()
            with self.assertRaises(AssertionError):read(task,va,n)
            self.assertEqual(calls,[])

    def test_actual_workspace_scrub_uses_bounded_complete_reads(self):
        source=runtime.EXTRA;node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='caller_result')
        function=ast.get_source_segment(source,node);calls=[];published=[];workspace=bytearray(268384)
        record=bytes(266336);header=struct.pack('<7Q',0x46494c4550525032,(4<<32)|3,0,0x100000000,0x100100000,(3<<32)|2,0)
        def user(t,address,n):
            self.assertLessEqual(n,266336);calls.append((address,n))
            if address==100:return header
            if address==0x100000000:return record
            offset=address-0x100100000
            self.assertTrue(0<=offset and offset+n<=len(workspace));return bytes(workspace[offset:offset+n])
        ns=dict(task=lambda n:(2,1),mode=lambda:8,user=user,CONFIG={'result_address':100,'roles':runtime.roles(0),'prepared':record},results=set(),CASE=0,
            struct=struct,hashlib=hashlib,emit=lambda *a,**k:published.append(k))
        exec(function,ns);ns['caller_result']()
        reads=[(a-0x100100000,n) for a,n in calls if a>=0x100100000]
        self.assertEqual(reads,[(0,2048),(2048,266336)]);self.assertEqual(len(published),1)
        for offset in (0,1535,1536,2047,2048,268383):
            ns['results'].clear();workspace[offset]=1
            with self.assertRaises(AssertionError):ns['caller_result']()
            workspace[offset]=0
    def test_complete_oracle_missing_duplicate_corrupt_and_reordered(self):
        for case in range(11):
            serial,events,counts,raw=sample(case);oom=0 if case==8 else None
            with self.subTest(case=case):
                self.assertEqual(len(runtime.validate(serial,trace(events),case,2,oom,counts,raw)),len(runtime.roles(case)))
                for n in range(len(events)):
                    for bad in (events[:n]+events[n+1:],events[:n]+[events[n]]+events[n:]):
                        with self.assertRaises(ValueError,msg=str((case,n,events[n]['kind']))):runtime.validate(serial,trace(bad),case,2,oom,counts,raw)
                with self.assertRaises(ValueError):runtime.validate(serial,trace(list(reversed(events))),case,2,oom,counts,raw)
                for kind,key,value in (('copy','sha','f'*64),('immutable','device',0),('retire','sha','0'*64),('release','after',1013),('trace_clean','bytes',0)):
                    bad=copy.deepcopy(events);next(e for e in bad if e['kind']==kind)[key]=value
                    with self.assertRaises(ValueError,msg=kind):runtime.validate(serial,trace(bad),case,2,oom,counts,raw)
                for kind,key,value in (('program_ready','device',1),('file_result','sha','f'*64),('fs_reply','sha','f'*64)):
                    if any(e['kind']==kind for e in events):
                        bad=copy.deepcopy(events);next(e for e in bad if e['kind']==kind)[key]=value
                        with self.assertRaises(ValueError,msg=kind):runtime.validate(serial,trace(bad),case,2,oom,counts,raw)
    def test_actual_observer_program_publication_and_source_guards(self):
        source=runtime.observer_body();tree=ast.parse(source)
        helpers={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
        self.assertIn("CONFIG['roles'][d(S['process_run_generation'])+1]['role']=='program'",helpers['allocation'])
        self.assertIn("if CONFIG['roles'][gen]['role']=='program':return",helpers['pio_retire'])
        self.assertIn("caller_result();trace_drain()",helpers['pio_retire'])
        self.assertIn('len(copies)<12',helpers['copy'])
        serial,events,counts,raw=sample();record=producer.prepare(raw,[],True);proofs=set();seen=[]
        def user(t,address,n):
            return b'\x5a'*266336 if n==266336 else record[96+address-0x400000:96+address-0x400000+n]
        namespace=dict(CONFIG={'roles':runtime.roles(0),'prepared':record},proofs=proofs,copies={5:record},created_sources={5:0},
            user=user,task=lambda n:None,mem=lambda a,n:bytes(n),S={'family_extended_masks':0},emit=lambda *a,**k:seen.append((a,k)),CASE=0,struct=struct,hashlib=hashlib)
        exec(helpers['program_ready'],namespace);ack=bytes(12)+struct.pack('<Q',5)+b'ELF64RO!'
        with self.assertRaises(AssertionError):namespace['program_ready'](2,None,5,ack[:-1]+b'?')
        self.assertFalse(proofs);namespace['program_ready'](2,None,5,ack);self.assertEqual(proofs,{5})
        with self.assertRaises(AssertionError):namespace['program_ready'](2,None,5,ack)
        self.assertEqual(len(seen),1)
    def test_actual_standard_file_program_build(self):
        folder=ROOT/'build/codex-agent/r83am-file-launch'/('program-host-'+uuid.uuid4().hex)
        zig=str(find_zig());raw=producer.build_file_program(folder,[zig,'cc'],['nasm'],[zig,'ld.lld'])
        self.assertLessEqual(len(raw),1536)
        self.assertEqual(struct.unpack_from('<Q',raw,72)[0],0)
        prepared=producer.prepare(raw,[],True)
        self.assertEqual(len(prepared),266336);self.assertEqual(prepared[24+16],5)
        self.assertEqual(prepared[96+0x10000:96+0x10000+len(raw[:struct.unpack_from('<Q',raw,96)[0]])],raw[:struct.unpack_from('<Q',raw,96)[0]])
        print('FILE_PROGRAM',len(raw),hashlib.sha256(raw).hexdigest())
    def test_selectors_reject_before_publication(self):
        with self.assertRaises(ValueError):producer.build('.',[],[],[],0,file_launch=True)
        with self.assertRaises(ValueError):producer.build('.',[],[],[],0,file_launch_case=1)
        with self.assertRaises(ValueError):producer.build('.',[],[],[],0,file_launch_case=True)
        for args in (['-NativeFileLaunch','-FilesystemCase','1'],['-FileLaunchCase','1']):
            result=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',*args],cwd=ROOT,capture_output=True,timeout=10)
            self.assertNotEqual(result.returncode,0);self.assertNotIn(b'X86_64_BOOTSTRAP_BUILD_OK',result.stdout)
        result=subprocess.run(['make','-n','x86_64-bootstrap','X86_64_NATIVE_FILE_LAUNCH=1'],cwd=ROOT,capture_output=True,timeout=10)
        self.assertNotEqual(result.returncode,0);self.assertIn(b'NativeFileLaunch requires plain NativeFilesystem',result.stderr)

    def test_direct_make_defaults_match_explicit_selectors(self):
        folder=ROOT/'build/codex-agent/r83am-file-launch'/('make-selection-host-'+uuid.uuid4().hex);folder.mkdir()
        baseline=direct_make_plan(folder,{'X86_64_'+name:'0' for name in MAKE_CASE_DEFAULTS})
        self.assertEqual(baseline.returncode,0,baseline.stderr)
        self.assertIn('--file-launch --file-launch-case 0',baseline.stdout)
        self.assertIn('--filesystem --filesystem-case 0 --filesystem-layout 2',baseline.stdout)
        for mask in range(8):
            with self.subTest(explicit_mask=mask):
                options={'X86_64_'+name:'0' for bit,name in enumerate(MAKE_CASE_DEFAULTS) if mask&(1<<bit)}
                result=direct_make_plan(folder,options)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout,baseline.stdout)

    def test_direct_make_layout_cases_and_rejections(self):
        folder=ROOT/'build/codex-agent/r83am-file-launch'/('make-selection-host-'+uuid.uuid4().hex);folder.mkdir()
        for layout in range(5):
            with self.subTest(layout=layout):
                result=direct_make_plan(folder,{'X86_64_FILESYSTEM_LAYOUT':str(layout)})
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('--filesystem --filesystem-case 0 --filesystem-layout '+str(layout),result.stdout)
        for case in range(11):
            with self.subTest(file_case=case):
                result=direct_make_plan(folder,{'X86_64_FILE_LAUNCH_CASE':str(case)})
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('--file-launch --file-launch-case '+str(case),result.stdout)
        bad=({'X86_64_FILESYSTEM_CASE':'1'},{'X86_64_PIO_CASE':'1'},
             {'X86_64_STARTUP_CASE':'1'},{'X86_64_BLOCK_PROFILE_CASE':'1'},
             {'X86_64_NATIVE_FILE_LAUNCH':'0','X86_64_FILE_LAUNCH_CASE':'1'},
             {'X86_64_NATIVE_FILESYSTEM':'0'})
        for options in bad:
            with self.subTest(rejected=options):
                result=direct_make_plan(folder,options)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('requires',result.stderr)
                self.assertEqual(result.stdout,'')
class NativeCacheTests(unittest.TestCase):
    def alias_fixture(self):
        folder,catalog=self.fixture();link=folder/'tool.exe';target=folder/'installed-tool.exe';target.write_bytes(b'tool')
        original_resolve=Path.resolve;original_link=Path.is_symlink
        def resolve(path,*args,**kwargs):return target if path==link else original_resolve(path,*args,**kwargs)
        def is_link(path):return path==link or original_link(path)
        stack=ExitStack()
        stack.enter_context(patch.object(Path,'resolve',resolve));stack.enter_context(patch.object(Path,'is_symlink',is_link))
        stack.enter_context(patch.object(runtime,'NATIVE_TOOL_ALIASES',{link:(target,hashlib.sha256(b'tool').hexdigest())},create=True))
        return folder,catalog,link,target,stack

    def test_native_cache_admits_only_bound_installation_alias(self):
        folder,catalog,link,target,context=self.alias_fixture()
        with context,patch.object(subprocess,'run',side_effect=AssertionError('tool must not execute')):
            self.assertEqual(len(runtime.admit_native_builds(folder,catalog)),12)

    def test_native_cache_alias_rejects_unbound_retargeted_and_changed_payload(self):
        for kind in ('unknown','target','retarget_after_read','link_type','target_type','target_bytes','link_bytes','pin','identity'):
            folder,catalog,link,target,context=self.alias_fixture();other=folder/'other-tool.exe';other.write_bytes(b'tool')
            with self.subTest(kind=kind),context,ExitStack() as changes:
                if kind=='unknown':changes.enter_context(patch.object(runtime,'NATIVE_TOOL_ALIASES',{}))
                elif kind=='pin':changes.enter_context(patch.object(runtime,'NATIVE_TOOL_ALIASES',{link:(target,'0'*64)}))
                elif kind=='target_bytes':target.write_bytes(b'changed')
                elif kind=='link_bytes':link.write_bytes(b'changed')
                elif kind=='identity':
                    previous_stat=Path.lstat;calls=[0]
                    def lstat(path,*args,**kwargs):
                        info=previous_stat(path,*args,**kwargs)
                        if path==link:
                            calls[0]+=1
                            if calls[0]>1:
                                fields={n:getattr(info,n) for n in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')}
                                fields['st_mtime_ns']+=1;fields['st_birthtime_ns']=getattr(info,'st_birthtime_ns',None)
                                return SimpleNamespace(**fields)
                        return info
                    changes.enter_context(patch.object(Path,'lstat',lstat))
                elif kind in ('target','retarget_after_read'):
                    previous=Path.resolve;calls=[0]
                    def resolve(path,*args,**kwargs):
                        if path==link:
                            calls[0]+=1
                            return target if kind=='retarget_after_read' and calls[0]==1 else other
                        return previous(path,*args,**kwargs)
                    changes.enter_context(patch.object(Path,'resolve',resolve))
                else:
                    previous_link=Path.is_symlink
                    def is_link(path):
                        if path==link and kind=='link_type':return False
                        if path==target and kind=='target_type':return True
                        return previous_link(path)
                    changes.enter_context(patch.object(Path,'is_symlink',is_link))
                with self.assertRaisesRegex(ValueError,'native cache tool'):
                    runtime.admit_native_builds(folder,catalog)

    def fixture(self):
        folder=ROOT/'build/codex-agent/r83am-file-launch'/('native-cache-host-'+uuid.uuid4().hex);folder.mkdir()
        inputs={'input.c':b'kernel input','empty.c':b''};entries=[]
        for case,layout in [(0,n) for n in (0,1,3,4)]+[(n,2) for n in range(1,9)]:
            image=f'build/case-{case}-{layout}/x86_64/reist-x86_64-bootstrap.elf';log=f'build/case-{case}-{layout}/build.log'
            artifacts={image:b'ELF fixture',log:b'complete build receipt'}
            for name,data in artifacts.items():
                path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            entries.append(dict(case=case,layout=layout,image=image,artifacts={n:hashlib.sha256(v).hexdigest() for n,v in artifacts.items()},
                prior_build_log=dict(path=log,sha256=hashlib.sha256(artifacts[log]).hexdigest()),runtime_accepted=False))
        for name,data in inputs.items():(folder/name).write_bytes(data)
        tool=folder/'tool.exe';tool.write_bytes(b'tool')
        catalog=dict(version=1,profile='native-file-launch-v1',source_inputs={n:hashlib.sha256(v).hexdigest() for n,v in inputs.items()},
            tools_sha256={str(tool):hashlib.sha256(b'tool').hexdigest()},entries=entries,source_proof={},runtime_accepted=False)
        return folder,catalog

    def test_native_cache_admits_exact_variants_without_subprocess(self):
        folder,catalog=self.fixture()
        with patch.object(subprocess,'run',side_effect=AssertionError('unexpected build/guest')),patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected process')):
            result=runtime.admit_native_builds(folder,catalog)
        self.assertEqual(set(result),{(0,n) for n in (0,1,3,4)}|{(n,2) for n in range(1,9)})
        self.assertEqual(result[(0,0)],folder/catalog['entries'][0]['image'])
        self.assertNotIn((0,2),result);self.assertNotIn((9,2),result);self.assertNotIn((10,2),result)

    def test_native_cache_rejects_changed_missing_sources_tools_and_outputs(self):
        for kind in ('input','empty','tool','image','log','missing'):
            with self.subTest(kind=kind):
                folder,catalog=self.fixture();entry=catalog['entries'][0]
                path=folder/({'input':'input.c','empty':'empty.c','tool':'tool.exe','image':entry['image'],
                    'log':entry['prior_build_log']['path'],'missing':entry['image']}[kind])
                if kind=='missing':path.unlink()
                else:path.write_bytes(path.read_bytes()+b'changed')
                with patch.object(subprocess,'run',side_effect=AssertionError('cache must not rebuild')),self.assertRaises((ValueError,OSError)):
                    runtime.admit_native_builds(folder,catalog)

    def test_native_cache_rejects_profiles_receipts_and_partial_inventory(self):
        folder,original=self.fixture()
        def change(c,kind):
            if kind=='version':c['version']=True
            elif kind=='profile':c['profile']='native-filesystem'
            elif kind=='accepted':c['runtime_accepted']=True
            elif kind=='partial':c['entries'].pop()
            elif kind=='duplicate':c['entries'][-1]=c['entries'][0]
            elif kind=='case':c['entries'][0]['case']=False
            elif kind=='layout':c['entries'][0]['layout']=2
            elif kind=='rowaccepted':c['entries'][0]['runtime_accepted']=True
            elif kind=='receipt':c['entries'][0]['prior_build_log']['sha256']='0'*64
            elif kind=='image':c['entries'][0]['image']='build/not-bound.elf'
            elif kind=='noartifact':c['entries'][0]['artifacts']={}
            elif kind=='escape':c['source_inputs']={'../input.c':'0'*64}
            elif kind=='absolute':c['source_inputs']={str(folder/'input.c'):'0'*64}
        for kind in ('version','profile','accepted','partial','duplicate','case','layout','rowaccepted','receipt','image','noartifact','escape','absolute'):
            with self.subTest(kind=kind),self.assertRaises((ValueError,OSError)):
                catalog=copy.deepcopy(original);change(catalog,kind);runtime.admit_native_builds(folder,catalog)

    def test_native_cache_fixed_pin_missing_catalog_and_duplicate_json(self):
        folder,catalog=self.fixture();path=folder/'catalog.json'
        with patch.object(runtime,'NATIVE_CACHE',path),patch.object(runtime,'ROOT',folder):
            self.assertEqual(runtime.native_build_cache(),{})
            with self.assertRaisesRegex(ValueError,'catalog missing'):runtime.native_build_cache(required=True)
            raw=json.dumps(catalog).encode();path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'catalog pin'):runtime.native_build_cache()
            with patch.object(runtime,'NATIVE_CACHE_SHA256',hashlib.sha256(raw).hexdigest()):
                self.assertEqual(len(runtime.native_build_cache(required=True)),12)
            raw=b'{"version":1,"version":1}';path.write_bytes(raw)
            with patch.object(runtime,'NATIVE_CACHE_SHA256',hashlib.sha256(raw).hexdigest()),self.assertRaisesRegex(ValueError,'duplicate JSON'):
                runtime.native_build_cache()

    def test_native_cache_admission_precedes_build_and_guest_side_effects(self):
        folder,_=self.fixture();destination=folder/'not-published'
        for argv in ([__file__,'--check-builds'],[__file__,'--image',str(folder/'native.elf'),'--evidence',str(destination)]):
            with self.subTest(argv=argv),patch.object(sys,'argv',argv),patch.object(runtime,'native_build_cache',side_effect=ValueError('injected cache rejection')),\
                    patch.object(subprocess,'run',side_effect=AssertionError('unexpected build')),patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected guest')),\
                    self.assertRaisesRegex(ValueError,'injected cache rejection'):
                runtime.main()
            self.assertFalse(destination.exists())

    def test_native_cache_keeps_original_runtime_oracles_and_uncached_build(self):
        source=(ROOT/'scripts/run_qemu_x86_64_file_launch.py').read_text();tree=ast.parse(source)
        names=('roles','program_variant','frames','replace_function','observer_body','_validate','validate','observer','capture')
        nodes={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names}
        self.assertEqual(len(nodes),9)
        self.assertEqual(hashlib.sha256(json.dumps(nodes,sort_keys=True).encode()).hexdigest(),'12005b126458ea7acf689408b9850cb9138973860e992dadcf02499003e86aa6')
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        builds=[ast.get_source_segment(source,n) for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess']
        self.assertEqual(hashlib.sha256(json.dumps(builds).encode()).hexdigest(),'36f5c5ae567f49d8889184f9048a7716390e9f748482269c691f28942083720e')

    def test_native_cache_actual_matrix_selects_existing_image_before_parser(self):
        folder,catalog=self.fixture();destination=folder/'matrix';selected=folder/catalog['entries'][0]['image']
        argv=[__file__,'--image',str(folder/'provided.elf'),'--evidence',str(destination)]
        with patch.object(sys,'argv',argv),patch.object(runtime,'native_build_cache',return_value={(0,0):selected}),\
                patch.object(runtime.wide.payload,'read_bounded',side_effect=ValueError('stop after cached selection')) as read,\
                patch.object(subprocess,'run',side_effect=AssertionError('unexpected rebuild')),patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected guest')):
            self.assertEqual(runtime.main(),1)
        read.assert_called_once_with(selected.parent/'reist-x86_64-c-core.elf')
        report=json.loads(next(destination.glob('attempt-*/summary.json')).read_text())
        self.assertFalse(report['passed']);self.assertEqual(report['error'],'stop after cached selection')
        self.assertEqual(report['builds_reused'],[{'case':0,'layout':0,'image':str(selected.relative_to(ROOT)),
            'catalog_sha256':runtime.NATIVE_CACHE_SHA256}])

if __name__=='__main__':unittest.main()
