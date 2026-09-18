"""Native periodic PIO profile: actual adapters and fail-closed composition."""
from pathlib import Path
import copy,hashlib,inspect,json,os,struct,subprocess,sys,tempfile,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
import build_x86_64_boot_programs as producer


def without_client_pause(body):
    import run_qemu_x86_64_service_pio as runtime
    for extra in (runtime.SERVICE_PAUSE_OBSERVER,
        "\n            if CASE!=12:service_pause_arm(gen,p)",
        "        service_pause_request(pio_owner>>32)\n",
        '    assert service_pause_pending is None and not pause_sleep_hook.enabled and not pause_block_hook.enabled and not pause_return_hook.enabled\n'):
        body=runtime.helpers.once(body,extra,'')
    return body


def without_client_fixture_pause(source):
    import run_qemu_x86_64_service_pio as runtime
    source=runtime.helpers.once(source,'#if REIST_NATIVE_SERVICE_PIO\n            zero(&message,sizeof message);message.version=1;message.struct_size=140;message.length=128;\n            REQUIRE(S3(IPC_RECEIVE_TIMEOUT,notice_ep,&message,800)==-110,245);\n#endif\n','')
    return runtime.helpers.once(source,'for(unsigned i=0;i<160;i++)REQUIRE(!S1(SLEEP_MS,100),231);',
        'for(unsigned i=0;i<120;i++)REQUIRE(!S1(SLEEP_MS,100),231);')


def without_active_calibration(source):
    from run_qemu_x86_64_file_launch import once
    source=once(source,'/* Qualification only: bounded active-clock calibration, acknowledged bounded',
        '/* Qualification only: exact accepted AP calibration, acknowledged bounded')
    source=once(source,'        unsigned polls;\n        for(polls=0;polls<100000;polls++) {\n'
        '            now=(uint64_t)S0(MONOTONIC_MS);\n'
        '            if(now<first || now-first>1000)return 0;\n'
        '            if(now-first>=20)break;\n'
        '            __asm__ volatile("pause");\n'
        '        }\n        if(polls==100000)return 0;\n',
        '        if(S1(SLEEP_MS,80))return 0;\n        now=(uint64_t)S0(MONOTONIC_MS);\n')
    return once(source,'if(now<first+20 || now-first>1000 || end<=begin',
        'if(now<first+80 || now-first>1000 || end<=begin')


class ServicePioTests(unittest.TestCase):
    def test_actual_sleep_admission_rejects800(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        guard=source.split('.sleep:\n',1)[1].split('    add eax, 10',1)[0]
        asm='''BITS 64
section .bss
syscall_rdi:resq 1
section .text
global actual_sleep_admission
actual_sleep_admission:
    mov [rel syscall_rdi],rcx
'''+guard+'''    xor eax,eax
    ret
.invalid:
    mov rax,-22
    ret
'''
        c=r'''
#include <stdint.h>
#include <stdio.h>
extern int64_t actual_sleep_admission(uint64_t);
int main(void){
    for(unsigned ms=0;ms<=1001;ms++)if(actual_sleep_admission(ms)!=((ms>=1&&ms<=100)?0:-22))return 1;
    if(actual_sleep_admission(UINT64_MAX)!=-22)return 2;
    puts("PIO_SLEEP_ADMISSION_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'PIO_SLEEP_ADMISSION')

    def test_actual_ipc_pause_admission_timeout_and_cleanup(self):
        import test_x86_64_service_cpu as host
        prefix=(ROOT/'test/x86_64_native_ipc_host.c').read_text().split('static void bulk_request',1)[0]
        c=prefix+r'''
int main(void){
    unsigned now=0;
    for(unsigned phase=0;phase<100;phase++)for(unsigned variant=0;variant<7;variant++){
        now+=200+phase;
        for(unsigned s=0;s<4;s++)call(NATIVE_IPC_BIND,s,now);
        request(0,now,49,0,0,0);assert(!r.result);unsigned endpoint=r.handle;
        request(0,now,55,endpoint,gen[2],1);assert(!r.result);
        request(2,now,53,endpoint,128,1000);assert(!r.result);
        request(0,now,54,endpoint,0,1000);assert(!r.result&&r.message.payload[0]==128);
        if(variant==6){request(0,now,52,endpoint,0,0);assert(!r.result);}
        memset(&r,0,sizeof r);r.number=54;r.a0=endpoint;r.a1=0x410100;r.a2=800;
        r.message.version=1;r.message.struct_size=140;r.message.length=128;
        if(variant==3)r.message.version=3;
        if(variant==4)r.message.struct_size=139;
        if(variant==5)r.a2=UINT64_C(1)<<32;
        call(NATIVE_IPC_REQUEST,0,now);
        if(variant>=3){assert(r.result==(variant==6?-9:-22));assert(!pending[0].state);}
        else {
            assert(r.result==NATIVE_IPC_PENDING&&r.deadline==now+80&&r.copy_size==140&&!r.ready);
            assert(pending[0].generation==gen[0]&&pending[0].state==1);
            memset(&r,0xa5,sizeof r); /* Published wait owns a copy, not this buffer. */
            call(NATIVE_IPC_PUMP,0,now+79);assert(!r.ready&&pending[0].state==1);
            if(variant==1){request(2,now+79,53,endpoint,55,0);assert(!r.result&&r.ready==1);}
            else if(variant==2){call(NATIVE_IPC_REAP,2,now+79);assert(r.ready==1);}
            else {call(NATIVE_IPC_PUMP,0,now+80);assert(r.ready==1);}
            call(NATIVE_IPC_TAKE,0,now+80);
            assert(r.result==(variant==1?0:variant==2?-32:-110));
            assert(r.number==54&&r.a0==endpoint&&r.a1==0x410100&&r.a2==800&&r.deadline==now+80&&r.copy_size==140);
            assert(!pending[0].state);
            if(!variant)for(unsigned n=0;n<128;n++)assert(!r.message.payload[n]);
        }
        for(unsigned s=0;s<4;s++)if(!(variant==2&&s==2))call(NATIVE_IPC_REAP,s,now+81);
        call(NATIVE_IPC_END,0,now+81);
        ipc_resource_stats_t stats;assert(!ipc_resource_stats(&stats));
        assert(!stats.active_endpoints&&!stats.active_capabilities&&!stats.queued_messages);
        for(unsigned s=0;s<4;s++)gen[s]+=4;
    }
    puts("PIO_IPC_PAUSE_OK");return 0;
}
'''
        host.ServiceCPUTests().retention_build(c,'PIO_IPC_PAUSE',['-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST',
            '-DREIST_HOST_TEST','-DREIST_NATIVE_TASK_POOL=1','-DREIST_NATIVE_RUNTIME=1','kernel/ipc/ipc.c','kernel/init/critical_object.c'])

    def test_actual_client_pause_order_errors_and_legacy(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/user/pool_pio.c').read_text()
        self.assertIn('REQUIRE(S3(IPC_RECEIVE_TIMEOUT,notice_ep,&message,800)==-110,245);',source)
        self.assertIn('for(unsigned i=0;i<160;i++)REQUIRE(!S1(SLEEP_MS,100),231);',source)
        body=source.split('        REQUIRE(!notice(child,fault,0,mode==12?19:128),211);',1)[1].split('            if(mode==11)',1)[0]
        body='        REQUIRE(!notice(child,fault,0,mode==12?19:128),211);'+body+'}\nreturn 0;\n}\n'
        harness=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static char calls[8];static unsigned used,bad,failure;static int returned;
enum {IPC_RECEIVE_TIMEOUT=54};
static unsigned notice_ep=42;
static struct {uint32_t version,struct_size,length;unsigned char payload[128];} message;
static void zero(void *p,unsigned n){memset(p,0,n);}
static int notice(uint64_t child,unsigned fault,unsigned phase,unsigned value){
    calls[used++]='N';if(child!=123||fault!=7||phase||!(value==19||value==128))bad=1;return failure==1;
}
static int S3(unsigned op,unsigned endpoint,void *buffer,unsigned ms){
    calls[used++]='I';if(op!=54||endpoint!=42||buffer!=&message||ms!=800||
        message.version!=1||message.struct_size!=140||message.length!=128)bad=1;
    for(unsigned n=0;n<128;n++)if(message.payload[n])bad=1;
    return returned;
}
static int reist_block_client_bind(int *client,uint64_t child){calls[used++]='B';if(*client!=9||child!=123)bad=1;return failure==3;}
#define REQUIRE(v,e) do{if(!(v))return e;}while(0)
'''
        for profile,label in ((1,'selected'),(0,'legacy')):
            harness+='\n#define REIST_NATIVE_SERVICE_PIO '+str(profile)+'\nstatic int '+label+'(unsigned mode){\n'
            harness+='uint64_t child=123,pool_pio_root[4]={0};unsigned fault=7;int client=9;\n(void)pool_pio_root;\n'+body+'#undef REIST_NATIVE_SERVICE_PIO\n'
        harness+=r'''
#define CHECK(v) do{if(!(v)){fprintf(stderr,"PAUSE_CHECK %u %s\n",__LINE__,#v);return 1;}}while(0)
int main(void){
    int results[]={-110,0,-22,-32,-9,-11};
    for(unsigned profile=0;profile<2;profile++)for(unsigned mode=0;mode<16;mode++)for(failure=0;failure<4;failure++)for(unsigned r=0;r<6;r++){
        memset(calls,0,sizeof calls);used=bad=0;
        memset(&message,0xa5,sizeof message);returned=results[r];
        int actual=profile?selected(mode):legacy(mode),expected=0;
        const char *want=mode==12?"N":profile?"NIB":"NB";
        if(failure==1){expected=211;want="N";}
        else if(mode!=12&&profile&&returned!=-110){expected=245;want="NI";}
        else if(mode!=12&&failure==3)expected=212;
        CHECK(actual==expected&&!bad&&!strcmp(calls,want));
    }
    puts("SERVICE_PIO_CLIENT_PAUSE_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',harness,'SERVICE_PIO_CLIENT_PAUSE')

    def test_actual_period_core_with_client_pause_all_phases(self):
        import test_x86_64_task_frames as host
        header=(ROOT/'arch/x86_64/proc/cpu_period.h').as_posix()
        harness='#include "'+header+'"\n'+r'''
#include <stdio.h>
#include <string.h>
#define CHECK(v) do{if(!(v)){fprintf(stderr,"PAUSE_PHASE %u %s\n",__LINE__,#v);return 1;}}while(0)
int main(void){
    unsigned old_exhausted=0;
    /* Model observed24-sample startup plus16-sample request, not a runtime WCET claim. */
    for(unsigned gap=0;gap<=80;gap+=80)for(unsigned phase=0;phase<100;phase++){
        struct reist_x64_cpu_budget b={0},saved;struct reist_x64_cpu_window w={0},saved_w;unsigned failed=0;
        CHECK(reist_x64_period_apply(&b,&w,1,3,32|((uint64_t)100<<32),0)==1);
        for(unsigned n=1;n<=24;n++)CHECK(reist_x64_period_apply(&b,&w,2,3,phase+n,phase+n)==1);
        saved=b;saved_w=w;uint64_t now=phase+24+gap;
        CHECK(!memcmp(&b,&saved,sizeof b)&&!memcmp(&w,&saved_w,sizeof w));
        for(unsigned n=1;n<=16;n++){
            uint64_t result=reist_x64_period_apply(&b,&w,2,3,now+n,now+n);
            CHECK(result==1||result==2);if(result==2){failed=1;break;}
        }
        if(!gap)old_exhausted+=failed;
        else CHECK(!failed&&b.used==40&&b.limit==32&&w.origin==0&&w.period==100&&w.used<32);
    }
    CHECK(old_exhausted>0);puts("SERVICE_PIO_PAUSE_PHASE_OK");return 0;
}
'''
        host.TaskFrameTests().build('%define REIST_NATIVE_SERVICE_CPU 1\n%include "arch/x86_64/proc/cpu_budget.asm"\n',harness,'SERVICE_PIO_PAUSE_PHASE')

    def test_client_pause_exact_fixture_and_old_assertions(self):
        import ast
        import run_qemu_x86_64_service_pio as runtime
        import verify_x86_64_service_pio as verify
        stop=verify.read(ROOT/verify.admission()['stopped']['path']);old=verify.read(ROOT/stop['frozen']['path'])
        def before(name):return (ROOT/old['directory']/'source'/name.replace('/','__')).read_text()
        fixture='arch/x86_64/user/pool_pio.c'
        self.assertEqual(without_client_fixture_pause((ROOT/fixture).read_text()),before(fixture))
        source=before('scripts/run_qemu_x86_64_service_pio.py')
        namespace=dict(__file__=str(ROOT/'scripts/run_qemu_x86_64_service_pio.py'),__name__='sealed_reap_observer')
        exec(compile(source,str(ROOT/old['directory']/'source/scripts__run_qemu_x86_64_service_pio.py'),'exec'),namespace)
        self.assertEqual(without_client_pause(runtime.observer_body()),namespace['observer_body']())
        self.assertEqual(runtime.FATAL_BODY,namespace['FATAL_BODY'])
        nodes={n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(inspect.getsource(runtime.validate_capture).strip().replace('        validate_service_pause(events,case)\n',''),nodes['validate_capture'])
        self.assertEqual(inspect.getsource(runtime.owner_validator).strip().replace("'cpu_idle','cpu_pause'","'cpu_idle'"),nodes['owner_validator'])

    def test_actual_client_pause_observer_callbacks(self):
        from types import SimpleNamespace
        import run_qemu_x86_64_service_pio as runtime
        for bad in ('none','argument','generation','root','if','late_block','not_blocked','root_unblocked','short_pause','charged','session',
                    'endpoint','header','return_value','return_request','return_deadline','return_capacity','missing_return','early_return'):
            clock=[100];driver=[1,3];root=[2,1];words=[3,32,64,99,100,0,0,24];profile=[1,24,1,0,4000]
            flags=[0];argument=[800];events=[];op=[53];endpoint=[42];capacity=[140]
            request=[54,42,0x410100,800,0,(1<<64)-110,180]
            header=bytearray(struct.pack('<3I',1,140,128)+bytes(128))
            def record(kind,**values):events.append(dict(kind=kind,**values))
            def query(a):return {2:op[0],3:endpoint[0],4:argument[0],5:0x410100,6:clock[0],0x10000+2128:capacity[0]}[a]
            def memory(a,n):self.assertEqual((a,n),(0x10000,56));return struct.pack('<7Q',*request)
            def user(t,a,n):return struct.pack('<4IQ',*profile) if n==24 else bytes(header)
            env=dict(DRIVER_SLOT=2,S={'scheduler_current_slot':1,'syscall_rax':2,'syscall_rdi':3,'syscall_rdx':4,'syscall_rsi':5,'scheduler_last_tick':6},
                CONFIG={'service':1000},starts={3:dict(live=True,slot=2,parent=1)},cpu_idle={3:12},
                mode=lambda:8,d=lambda a:0,task=lambda slot:root if slot==0 else driver,
                reg=lambda n:0x10000 if n=='r13' else flags[0],q=query,mem=memory,struct=struct,
                cpu_snapshot=lambda slot:(8,clock[0],list(words)),user=user,emit=record,
                Hook=lambda name,fn:SimpleNamespace(enabled=True,fn=fn))
            exec(compile(runtime.SERVICE_PAUSE_OBSERVER,'<actual pause callbacks>','exec'),env)
            env['service_pause_arm'](3,profile)
            def run():
                op[0]=54
                if bad=='argument':argument[0]=799
                if bad=='endpoint':endpoint[0]=43
                if bad=='header':header[0]=2
                if bad=='generation':driver[1]=4
                if bad=='root':root[1]=9
                if bad=='if':flags[0]=512
                env['service_pause_sleep']();driver[0]=root[0]=6;clock[0]=111 if bad=='late_block' else 102
                if bad=='not_blocked':driver[0]=1
                if bad=='root_unblocked':root[0]=1
                env['service_pause_blocked']();clock[0]=179 if bad=='early_return' else 180
                if bad=='return_value':request[5]=0
                if bad=='return_request':request[1]=43
                if bad=='return_deadline':request[6]=181
                if bad=='return_capacity':capacity[0]=139
                if bad!='missing_return':env['service_pause_return']()
                clock[0]=171 if bad=='short_pause' else 180;root[0]=2
                if bad=='charged':words[2]+=1
                if bad=='session':profile[4]+=1
                env['service_pause_request'](3)
            if bad=='none':
                run();self.assertEqual([e['step'] for e in events],[0,1,2]);self.assertIsNone(env['service_pause_pending'])
                self.assertFalse(env['pause_sleep_hook'].enabled or env['pause_block_hook'].enabled or env['pause_return_hook'].enabled)
            else:
                with self.subTest(bad=bad),self.assertRaises(AssertionError):run()

    def test_client_pause_oracle_rejects_missing_forged_and_short_proof(self):
        import run_qemu_x86_64_service_pio as runtime
        _,events,_,_,_=self.sample(0)
        runtime.validate_service_pause(events,0)
        for step in range(3):
            bad=copy.deepcopy(events);bad.pop(next(i for i,e in enumerate(bad) if e['kind']=='cpu_pause' and e['step']==step))
            with self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)
        for field,value in (('state',1),('ms',799),('root',9),('step',1),('gen',99),('now',0)):
            bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='cpu_pause' and e['step']==2)[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)
        for index in range(8):
            bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='cpu_pause' and e['step']==2)['records'][index]^=1
            with self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)
        for step in (1,2):
            bad=copy.deepcopy(events);rows=[e for e in bad if e['kind']=='cpu_pause']
            rows[step]['now']=rows[0]['now']+11 if step==1 else rows[1]['now']+69
            with self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)
        bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='cpu_pause')['profile'][4]+=1
        with self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)
        for field,values in (('wait',([41,42,0x410100,800],[54,0,0x410100,800],[54,42,0,800],[54,42,0x410100,799])),
                             ('completion',([], [0,0,-110],[180,180,0],[180,180,-32]))):
            for value in values:
                bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='cpu_pause' and e['step']==2)[field]=value
                with self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)
        bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='cpu_pause' and e['step']==1)['root_state']=2
        with self.assertRaises(ValueError):runtime.validate_service_pause(bad,0)

    def test_reap_probe_real_image_and_branch_admission(self):
        import run_qemu_x86_64_service_pio as runtime
        import verify_x86_64_service_pio as verify
        old=verify.read(ROOT/verify.admission()['stopped']['path']);image=ROOT/old['image']['path']
        payload=runtime.owner.payload;symbols=runtime.transport.symbols(image)
        elf=payload.elf(payload.read_bounded(image,bits=32),32)
        address=symbols['process_ipc_service64'];physical=address-payload.HIGH
        section=next(s for s in elf['sections'].values() if s['address']<=physical< s['address']+len(s['data']))
        offset=physical-section['address'];raw=section['data'][offset:offset+24]
        reads=[]
        def memory(a,n):reads.append((a,n));self.assertEqual((a,n),(address,24));return raw
        self.assertEqual(runtime.reap_probe_binding(memory,symbols),address+19)
        self.assertEqual(reads,[(address,24)])
        for index in range(24):
            corrupt=bytearray(raw);corrupt[index]^=1
            with self.subTest(byte=index),self.assertRaises(ValueError):runtime.reap_probe_binding(lambda a,n:bytes(corrupt),symbols)
        for bad in (raw[:-1],raw+b'\0'):
            with self.assertRaises(ValueError):runtime.reap_probe_binding(lambda a,n:bad,symbols)
        for delta in (-1,1):
            changed=dict(symbols);changed['process_ipc_service64.not_reap']+=delta
            with self.assertRaises(ValueError):runtime.reap_probe_binding(memory,changed)
        # Execute the unchanged decoder's actual short branches for all admitted
        # lifecycle operations; op4 alone reaches the MOV EAX,5 probe.
        for operation in range(6):
            pc=5;hits=[]
            for _ in range(8):
                if pc==24:break
                if pc==5:self.assertEqual(raw[pc:pc+2],b'\x85\xff');zero=operation==0;pc+=2
                elif pc==14:self.assertEqual(raw[pc:pc+3],b'\x83\xff\x04');zero=operation==4;pc+=3
                elif raw[pc]==0x75:pc+=2+(raw[pc+1] if not zero else 0)
                else:
                    self.assertEqual(raw[pc],0xb8)
                    if pc==19:hits.append(pc)
                    pc+=5
            self.assertEqual(pc,24);self.assertEqual(hits,[19] if operation==4 else [])

    def test_reap_probe_preserves_full_callback_and_generated_observer(self):
        import ast
        from types import SimpleNamespace
        import run_qemu_x86_64_service_pio as runtime
        import verify_x86_64_service_pio as verify
        a=verify.admission();stop=verify.read(ROOT/a['reap_baseline']['path']);old=verify.read(ROOT/stop['frozen']['path'])
        source=(ROOT/old['directory']/'source/scripts__run_qemu_x86_64_service_pio.py').read_text()
        namespace=dict(__file__=str(ROOT/'scripts/run_qemu_x86_64_service_pio.py'),__name__='old_observer')
        exec(compile(source,'<sealed old observer>','exec'),namespace)
        before=namespace['observer_body']();after=without_client_pause(runtime.observer_body())
        for fn in (runtime.reap_probe_address,runtime.reap_probe_binding):after=runtime.helpers.once(after,inspect.getsource(fn)+'\n','')
        after=runtime.helpers.once(after,"    assert reap_probe_binding(mem,S)==S['service_pio_reap_probe']\n",'')
        after=runtime.helpers.once(after,"S['service_pio_reap_probe']=reap_probe_address(S)\nHook('service_pio_reap_probe',cold_reap)","Hook('process_ipc_service64',cold_reap)")
        self.assertEqual(after,before)
        tree=ast.parse(runtime.observer_body());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cold_reap')
        for operation in range(6):
            for invalid in ('none','generation','slot','if','duplicate','capacity'):
                pending={(1,7)} if invalid=='duplicate' else {(n,n+20) for n in range(8)} if invalid=='capacity' else set()
                slot=8 if invalid=='slot' else 1;registers=dict(rdi=operation,rsi=slot,rdx=7,eflags=512 if invalid=='if' else 0)
                hook=SimpleNamespace(enabled=False)
                env=dict(mode=lambda:8,reg=lambda n:registers[n],task=lambda n:(0,8 if invalid=='generation' else 7),release_pending=pending,release_arm_hook=hook)
                exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual unchanged reap callback>','exec'),env)
                if operation==4 and invalid!='none':
                    with self.assertRaises(AssertionError):env['cold_reap']()
                else:
                    original=set(pending);env['cold_reap']()
                    self.assertEqual(pending,original|{(1,7)} if operation==4 else original)
                    self.assertEqual(hook.enabled,operation==4)

    def test_host_budget_keeps_all_observers_oracles_and_build_inputs(self):
        import ast
        import verify_x86_64_service_pio as verify
        a=verify.admission();old=verify.read(ROOT/a['retained_frozen']['path'])
        path=ROOT/old['directory']/'source/scripts__run_qemu_x86_64_service_pio.py'
        before=ast.parse(path.read_text())
        current=(ROOT/'scripts/run_qemu_x86_64_service_pio.py').read_text()
        current=self.undo_trace_delta('observer',current)
        after=ast.parse(current)
        def functions(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name not in ('main','observer_body','reap_probe_address','reap_probe_binding','scope_reap_probe','owner_validator','validate_capture','validate_service_pause')}
        self.assertEqual(functions(before),functions(after))
        exempt={'automation/reist-s03b.toml','docs/architecture/NATIVE_SERVICE_PIO_CONTRACT.md','docs/development/CURRENT_WORK.md',
            'scripts/run_qemu_x86_64_service_pio.py','scripts/verify_x86_64_service_pio.py','test/test_x86_64_service_pio.py','arch/x86_64/user/pool_pio.c',*a['package']['host_budget_files']}
        for name,sha in old['source_inputs'].items():
            if name in ('Makefile','arch/x86_64/proc/cooperative_scheduler.asm'):
                baseline=ROOT/a['trace_originals'][name]['path']
                self.assertEqual(verify.digest(baseline),sha,name)
                self.assertEqual(self.undo_trace_delta(name,(ROOT/name).read_text()),baseline.read_text(),name)
            elif name=='arch/x86_64/user/service_pio_workload.h':
                baseline=ROOT/verify.read(ROOT/a['calibration_stop']['path'])['frozen']['path']
                baseline=ROOT/verify.read(baseline)['directory']/'source'/name.replace('/','__')
                self.assertEqual(verify.digest(baseline),sha,name)
                self.assertEqual(without_active_calibration((ROOT/name).read_text()),baseline.read_text())
            elif name not in exempt:self.assertEqual(verify.digest(ROOT/name),sha,name)

    @staticmethod
    def undo_trace_delta(name,source):
        changes={
            'observer': [('native_cpu_trace.scope_observer(observer_body())','observer_body()')],
            'Makefile': [(' $(if $(filter 1,$(X86_64_NATIVE_SERVICE_PIO)),-DREIST_NATIVE_CPU_TRACE=1,)','')],
            'arch/x86_64/proc/cooperative_scheduler.asm': [
                ('%ifdef REIST_NATIVE_CPU_TRACE\n    cmp edx,2\n    jne .untraced_period\n    call native_cpu_trace_before64\n    call reist_x64_period_apply\n    call native_cpu_trace_after64\n    jmp .budget_result\n.untraced_period:\n%endif\n',''),
                ('%ifdef REIST_NATIVE_CPU_TRACE\n%include "arch/x86_64/proc/cpu_trace.inc"\n%endif\n','')],
        }
        for before,after in changes[name]:
            if source.count(before)!=1:raise ValueError('exact approved trace delta')
            source=source.replace(before,after)
        return source

    def test_trace_inverse_rejects_extra_missing_and_mutated_changes(self):
        import verify_x86_64_service_pio as verify
        a=verify.admission()
        for name in ('Makefile','arch/x86_64/proc/cooperative_scheduler.asm'):
            current=(ROOT/name).read_text();before=(ROOT/a['trace_originals'][name]['path']).read_text()
            self.assertEqual(self.undo_trace_delta(name,current),before)
            with self.assertRaises(ValueError):self.undo_trace_delta(name,current+current)
            with self.assertRaises(ValueError):self.undo_trace_delta(name,before)
            with self.assertRaises(ValueError):self.undo_trace_delta(name,current.replace('REIST_NATIVE_CPU_TRACE','INVALID_TRACE'))
            self.assertNotEqual(self.undo_trace_delta(name,current+'\nextra drift\n'),before)

    def options(self):
        return dict(family=True,startup=True,import_image=True,pio=True,block=True,
                    wide=True,block_profile=True,task_pool=True,pool_pio=True,service_pio=True)

    def test_actual_new_profile_admission(self):
        folder=ROOT/'build/codex-agent/r83aq-service-pio/host'
        folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            target=Path(temporary)/'valid'
            with patch.object(producer.subprocess,'run',side_effect=RuntimeError('AQ_ADMITTED_BEFORE_COMPILER')) as run:
                with self.assertRaisesRegex(RuntimeError,'AQ_ADMITTED_BEFORE_COMPILER'):
                    producer.build(target,['cc'],['nasm'],['ld'],0,**self.options())
                self.assertEqual(run.call_count,1)
            self.assertTrue(target.is_dir())

    def test_invalid_profile_has_no_output_or_compiler(self):
        folder=ROOT/'build/codex-agent/r83aq-service-pio/host'
        folder.mkdir(parents=True,exist_ok=True)
        bad=[dict(service_pio=x) for x in (None,0,1,'1')]
        bad += [dict(pool_pio=False),dict(service_cpu=True),dict(task_pool=False),
                dict(pio=False),dict(block_profile=False),dict(wide=False),
                dict(filesystem=True),dict(file_launch=True),dict(pio_case=1)]
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            for index,change in enumerate(bad):
                target=Path(temporary)/str(index);options=self.options();options.update(change)
                with self.subTest(change=change),patch.object(producer.subprocess,'run') as run:
                    with self.assertRaises(ValueError):producer.build(target,['cc'],['nasm'],['ld'],0,**options)
                    run.assert_not_called();self.assertFalse(target.exists())

    def test_actual_existing_owner_mechanisms(self):
        from test_x86_64_pool_pio import PoolPioTests
        tests=PoolPioTests()
        tests.test_actual_slot_owner_admission()
        tests.test_actual_ring3_service_all_owners()
        tests.test_actual_trace_eight_slot_bounds()

    def test_reference_adapters_reject_nonprofile_drift(self):
        import verify_x86_64_service_pio as verify
        a=verify.admission()
        def before(name):return (ROOT/a['snapshots'][name]['path']).read_text()
        name='scripts/build_x86_64_boot_programs.py';current=(ROOT/name).read_text()
        verify.producer_binding(before(name),current)
        with self.assertRaises(ValueError):verify.producer_binding(before(name),current.replace("'-O2'","'-O1'",1))
        make=(ROOT/'Makefile').read_text();ps=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text()
        verify.entrypoint_binding(before('Makefile'),make,before('scripts/build-x86_64-bootstrap.ps1'),ps)
        with self.assertRaises(ValueError):verify.entrypoint_binding(before('Makefile'),make+'\n# unbound\n',before('scripts/build-x86_64-bootstrap.ps1'),ps)
        with self.assertRaises(ValueError):verify.entrypoint_binding(before('Makefile'),make,before('scripts/build-x86_64-bootstrap.ps1'),ps.replace('[switch]$NativePIO','[int]$NativePIO',1))

    def test_actual_cpu_workload_o0_o2(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/user/service_pio_workload.h').read_text()
        original=(ROOT/'arch/x86_64/user/task_pool.c').read_text()
        left=without_active_calibration(source).split('static uint64_t service_cycles(void)',1)[1].split('static int service_pio_prepare',1)[0]
        right=original.split('static uint64_t service_cycles(void)',1)[1].split('static int service_samples',1)[0]
        self.assertEqual(left.strip(),right.strip())
        body='static uint64_t service_quantum(void)'+source.split('static uint64_t service_quantum(void)',1)[1].split('static int service_pio_idle',1)[0]
        harness=r'''
#include <stdint.h>
#include <stdio.h>
static uint64_t cycles;
static unsigned sleeps,calibrations,notices,bad,fail_notice,fail_sleep,stuck,clock_calls;
enum {MONOTONIC_MS=42,SLEEP_MS=41};
static uint64_t service_cycles(void){cycles+=1000;return cycles;}
static uint64_t S0(unsigned op){
    if(op!=MONOTONIC_MS||sleeps)bad=1;
    cycles+=10000;clock_calls++;if(!stuck&&clock_calls%3==0)calibrations++;
    return stuck?0:clock_calls*10;
}
static int S1(unsigned op,unsigned ms){
    if(op!=SLEEP_MS||ms!=80)bad=1;
    if(calibrations!=3)bad=1;sleeps++;
    cycles+=(uint64_t)ms*1000;return fail_sleep&&sleeps==fail_sleep?-1:0;
}
static int notice(unsigned mode,unsigned phase,unsigned value){
    if(mode!=7||phase!=2||value!=(notices+1)*5||value!=sleeps||calibrations!=3)bad=1;
    notices++;return notices==fail_notice?-1:0;
}
'''+body+r'''
#define CHECK(v) do{if(!(v)){fprintf(stderr,"PIO_WORK_CHECK %u %s\n",__LINE__,#v);return 1;}}while(0)
static void reset(void){cycles=0;sleeps=calibrations=notices=bad=fail_notice=fail_sleep=stuck=clock_calls=0;}
int main(void){
    CHECK(!service_pio_prepare(7)&&!bad&&sleeps==40&&notices==8&&calibrations==3);
    for(unsigned i=1;i<=8;i++){reset();fail_notice=i;CHECK(service_pio_prepare(7)==-1&&!bad&&notices==i&&sleeps==i*5);}
    for(unsigned i=1;i<=40;i++){reset();fail_sleep=i;CHECK(service_pio_prepare(7)==-1&&!bad&&sleeps==i&&notices==(i-1)/5);}
    reset();stuck=1;CHECK(service_pio_prepare(7)==-1&&!bad&&!sleeps&&!notices&&!calibrations&&clock_calls==100001);
    puts("SERVICE_PIO_WORKLOAD_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',harness,'SERVICE_PIO_WORKLOAD')

    def test_actual_fixture_compilation_all_roles(self):
        from build_user_program import find_zig
        folder=ROOT/'build/codex-agent/r83aq-service-pio'/('host-compile-'+uuid.uuid4().hex);folder.mkdir()
        header=folder/'blob.h';header.write_text('static const unsigned char import_blob[1]={0};\n')
        environment=os.environ.copy();environment['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        environment['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for n in range(4):
            command=[str(find_zig()),'cc','-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror',
                '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
                '-Iuserspace/sdk/include','-DREIST_NATIVE_POOL_PIO=1','-DREIST_NATIVE_SERVICE_CPU=1','-DREIST_NATIVE_SERVICE_PIO=1',
                '-DPROGRAM_ID='+str(n),*(['-include',str(header)] if n==0 else []),'-c','arch/x86_64/user/pool_pio.c','-o',str(folder/f'program{n}.o')]
            result=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/f'program{n}.log').write_bytes(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])

    def test_active_calibration_errors_bounds_and_exact_inverse(self):
        import test_x86_64_task_frames as host
        import verify_x86_64_service_pio as verify
        source=(ROOT/'arch/x86_64/user/service_pio_workload.h').read_text()
        frozen=verify.read(ROOT/verify.read(ROOT/verify.admission()['calibration_stop']['path'])['frozen']['path'])
        before=(ROOT/frozen['directory']/'source/arch__x86_64__user__service_pio_workload.h').read_text()
        self.assertEqual(without_active_calibration(source),before)
        for invalid in (before,source+source,source.replace('polls<100000','polls<100001')):
            with self.assertRaises(ValueError):without_active_calibration(invalid)
        burst=source.split('static int service_pio_prepare',1)[1].split('static int service_pio_idle',1)[0]
        self.assertNotIn('S0(',burst)
        body='static uint64_t service_quantum(void)'+source.split('static uint64_t service_quantum(void)',1)[1].split('static int service_pio_idle',1)[0]
        harness=r'''
#include <stdint.h>
#include <stdio.h>
static uint64_t cycles;
static unsigned fault,phase,clocks,reads,sleeps,notices;
enum {MONOTONIC_MS=42,SLEEP_MS=41};
static uint64_t service_cycles(void){
    reads++;cycles+=1000;
    if(fault==5&&reads==2)return 0;
    if(fault==6&&reads==2)return UINT64_C(3000001001);
    if(fault==7&&reads==2)return UINT64_C(250000001);
    if(fault==8)return 0;
    if(fault==10&&reads>6)return 100000;
    if(fault==11&&reads==8)return 0;
    return cycles;
}
static uint64_t S0(unsigned op){
    if(op!=MONOTONIC_MS)return UINT64_MAX;
    clocks++;cycles+=10000;
    if(fault==1)return 100;
    if(fault==2&&clocks==2)return 0;
    if(fault==3&&clocks==2)return 2000;
    if(fault==4)return UINT64_MAX-10;
    if(fault==9)return UINT64_MAX;
    return phase+clocks*10;
}
static int S1(unsigned op,unsigned ms){(void)op;(void)ms;sleeps++;return 0;}
static int notice(unsigned mode,unsigned step,unsigned value){(void)mode;(void)step;(void)value;notices++;return 0;}
'''+body+r'''
#define CHECK(v) do{if(!(v)){fprintf(stderr,"ACTIVE_CALIBRATION %u fault%u %s\n",__LINE__,fault,#v);return 1;}}while(0)
static void reset(void){cycles=0;clocks=reads=sleeps=notices=0;}
int main(void){
    for(phase=0;phase<10;phase++){
        reset();CHECK(service_quantum()==34100&&clocks==9&&reads==6&&!sleeps&&!notices);
    }
    for(fault=1;fault<=11;fault++){
        reset();CHECK(service_pio_prepare(7)==-1&&!sleeps&&!notices);
        CHECK(clocks<=100001&&reads<=1000008);
        if(fault==1)CHECK(clocks==100001&&reads==1);
        if(fault==10)CHECK(clocks==9&&reads==1000007);
        if(fault==11)CHECK(clocks==9&&reads==8);
    }
    puts("SERVICE_PIO_ACTIVE_CALIBRATION_OK");return 0;
}
'''
        host.TaskFrameTests().build('BITS 64\nsection .text\n',harness,'SERVICE_PIO_ACTIVE_CALIBRATION')

    def test_actual_idle_separation_and_period_core(self):
        import test_x86_64_task_frames as host
        source=(ROOT/'arch/x86_64/user/service_pio_workload.h').read_text()
        self.assertIn('static int service_pio_idle(unsigned mode)',source)
        body='static int service_pio_idle(unsigned mode)'+source.split('static int service_pio_idle(unsigned mode)',1)[1].split('#endif',1)[0]
        header=(ROOT/'arch/x86_64/proc/cpu_period.h').as_posix()
        harness='#include "'+header+'"\n'+r'''
#include <stdio.h>
#include <string.h>
static unsigned sleeps,notices,bad,fail_sleep,fail_notice;
static uint64_t now;
enum {SLEEP_MS=41};
static int S1(unsigned op,unsigned ms){
    if(op!=SLEEP_MS||ms!=100)bad=1;
    sleeps++;now+=11;return sleeps==fail_sleep?-1:0;
}
static int notice(unsigned mode,unsigned phase,unsigned value){
    if(mode!=7||phase!=3||value!=sleeps||value!=(notices+1)*6)bad=1;
    notices++;return notices==fail_notice?-1:0;
}
'''+body+r'''
#define CHECK(v) do{if(!(v)){fprintf(stderr,"IDLE_CHECK %u %s\n",__LINE__,#v);return 1;}}while(0)
static void reset(void){sleeps=notices=bad=fail_sleep=fail_notice=0;now=120;}
static int warm(struct reist_x64_cpu_budget *b,struct reist_x64_cpu_window *w){
    memset(b,0,sizeof *b);memset(w,0,sizeof *w);
    if(reist_x64_period_apply(b,w,1,3,32|((uint64_t)100<<32),0)!=1)return -1;
    for(unsigned n=1;n<=40;n++){
        uint64_t tick=n<=20?n:n+80;
        if(reist_x64_period_apply(b,w,2,3,tick,tick)!=1)return -1;
    }
    return 0;
}
int main(void){
    struct reist_x64_cpu_budget b,old_b;struct reist_x64_cpu_window w,old_w;
    CHECK(!warm(&b,&w)&&b.used==40&&w.used==20&&w.index==1);
    /* Actual unchanged core: immediately adding12 samples exhausts the window. */
    for(unsigned n=1;n<=12;n++)CHECK(reist_x64_period_apply(&b,&w,2,3,120+n,120+n)==(n==12?2:1));
    CHECK(!warm(&b,&w));old_b=b;old_w=w;reset();
    CHECK(!service_pio_idle(7)&&!bad&&sleeps==12&&notices==2&&now==252);
    CHECK(!memcmp(&b,&old_b,sizeof b)&&!memcmp(&w,&old_w,sizeof w));
    /* Sleep does not reset quota, origin, lifetime or any kernel word. */
    for(unsigned n=1;n<=24;n++)CHECK(reist_x64_period_apply(&b,&w,2,3,now+n,now+n)==1);
    CHECK(b.used==64&&w.period==100&&w.origin==0&&w.index==2&&w.used==24);
    for(unsigned n=1;n<=12;n++){reset();fail_sleep=n;CHECK(service_pio_idle(7)==-1&&!bad&&sleeps==n&&notices==(n-1)/6);}
    for(unsigned n=1;n<=2;n++){reset();fail_notice=n;CHECK(service_pio_idle(7)==-1&&!bad&&sleeps==n*6&&notices==n);}
    puts("SERVICE_PIO_IDLE_OK");return 0;
}
'''
        host.TaskFrameTests().build('%define REIST_NATIVE_SERVICE_CPU 1\n%include "arch/x86_64/proc/cpu_budget.asm"\n',harness,'SERVICE_PIO_IDLE')
        fixture=(ROOT/'arch/x86_64/user/pool_pio.c').read_text()
        self.assertIn('REQUIRE(!service_pio_prepare(kind)&&!service_pio_idle(kind),243);',fixture)
        self.assertIn('for(unsigned idle=6;idle<=12;idle+=6)REQUIRE(!notice(child,fault,3,idle),244);',fixture)

    def test_spacing_exact_fixture_delta_and_phase_model(self):
        import re
        import test_x86_64_task_frames as host
        import verify_x86_64_service_pio as verify
        a=verify.admission();stop=verify.read(ROOT/a['fixture_parent']['path']);f=verify.read(ROOT/stop['frozen']['path'])
        def original(name):return (ROOT/f['directory']/'source'/name.replace('/','__')).read_text()
        name='arch/x86_64/user/service_pio_workload.h';current=(ROOT/name).read_text()
        restored=without_active_calibration(current).replace('n==1000000 || S1(SLEEP_MS,80)','n==1000000 || S1(SLEEP_MS,40)').replace('i%5==4 && notice','i%10==9 && notice')
        self.assertEqual(restored,original(name))
        name='arch/x86_64/user/pool_pio.c';fixture=without_client_fixture_pause((ROOT/name).read_text())
        self.assertEqual(fixture.replace('batch=5;batch<=40;batch+=5','batch=10;batch<=40;batch+=10'),original(name))
        body=current.split('static int service_pio_prepare',1)[1].split('static int service_pio_idle',1)[0]
        gap=int(re.search(r'S1\(SLEEP_MS,(\d+)\)',body)[1]);self.assertEqual(gap,80)
        header=(ROOT/'arch/x86_64/proc/cpu_period.h').as_posix()
        harness='#include "'+header+'"\n#define SPACING_MS '+str(gap)+'\n'+r'''
#include <stdio.h>
#include <string.h>
#define CHECK(v) do{if(!(v)){fprintf(stderr,"SPACING_CHECK %u %s\n",__LINE__,#v);return 1;}}while(0)
int main(void){
    unsigned old_exhausted=0;
    /* Adversarial phase model, not a bound on real TSC burst execution:
     * three charged ticks per burst, for all100 possible window offsets. */
    for(unsigned gap=40;gap<=SPACING_MS;gap+=40)for(unsigned phase=0;phase<100;phase++){
        struct reist_x64_cpu_budget b={0};struct reist_x64_cpu_window w={0};unsigned exhausted=0,peak=0;
        CHECK(reist_x64_period_apply(&b,&w,1,3,32|((uint64_t)100<<32),0)==1);
        for(unsigned burst=0;burst<40&&!exhausted;burst++)for(unsigned sample=0;sample<3;sample++){
            uint64_t now=phase+1+burst*(gap/10+1+3)+sample;
            uint64_t result=reist_x64_period_apply(&b,&w,2,3,now,now);
            CHECK(result==1||result==2);if(w.used>peak)peak=(unsigned)w.used;
            if(result==2){exhausted=1;break;}
        }
        if(gap==40)old_exhausted+=exhausted;
        else CHECK(!exhausted&&b.used==120&&peak<32&&w.origin==0&&w.period==100&&b.limit==32);
    }
    CHECK(old_exhausted==100);puts("SERVICE_PIO_SPACING_OK");return 0;
}
'''
        host.TaskFrameTests().build('%define REIST_NATIVE_SERVICE_CPU 1\n%include "arch/x86_64/proc/cpu_budget.asm"\n',harness,'SERVICE_PIO_SPACING')

    def test_observer_construction_and_original_owner_predicates(self):
        import run_qemu_x86_64_service_pio as runtime
        body=runtime.observer_body();compile(body,'<AQ observer>','exec')
        self.assertIn('cpu_final(slot,gen)',body);self.assertIn('cpu_start(slot,gen)',body)
        self.assertIn('header==(6,80,1,0)',body);self.assertIn('cpu_batches.get(gen)==40',body)
        config={'s':{},'pool_pio_root':0x415000}
        for kind in runtime.FATAL_CASES:
            code=runtime.fatal_observer(config,ROOT/'build/codex-agent/r83aq-service-pio/host',kind)
            compile(code.split('\npython\n',1)[1].rsplit('\nend\n',1)[0],'<AQ fatal>','exec')
        validator=runtime.owner_validator()
        # Named metadata adapters retain the old function's predicate count.
        self.assertEqual(validator.__name__,'_validate')

    def test_observer_stops_are_generation_scoped(self):
        import ast,types
        import run_qemu_x86_64_service_pio as runtime
        body=runtime.observer_body();tree=ast.parse(body)
        functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
        self.assertIn('syscall_hooks',functions)
        namespace=dict(syscall_hook=types.SimpleNamespace(enabled=True),
            syscall_narrow=[types.SimpleNamespace(enabled=False),types.SimpleNamespace(enabled=False)])
        exec(compile(ast.Module(body=[functions['syscall_hooks']],type_ignores=[]),'<actual AQ hook switch>','exec'),namespace)
        for enabled in (False,True,False,True):
            namespace['syscall_hooks'](enabled)
            self.assertIs(namespace['syscall_hook'].enabled,enabled)
            self.assertTrue(all(h.enabled is not enabled for h in namespace['syscall_narrow']))
        # All old syscall predicates remain verbatim, before the sole switch.
        original=runtime.owner.SYSCALL.strip().replace('header==(5,64,1,0)','header==(6,80,1,0)').replace('w[2]==25','w[2]==60').replace('sleeps=25','sleeps=60')
        actual=ast.get_source_segment(body,functions['syscall'])
        suffix="\n    if call not in (22,132) and created_sources and not source_pending and set(created_sources)<=proofs:\n        syscall_hooks(False)"
        self.assertEqual(actual,original+suffix)
        calls=[];tasks={0:[2,1],1:[2,2],2:[2,3]};current={'slot':2,'call':113}
        shared=dict(S={'scheduler_current_slot':1,'syscall_rax':2,'syscall_rdi':3},mode=lambda:8,
            d=lambda address:current['slot'],q=lambda address:current['call'],task=lambda slot:tasks[slot],
            starts={},proofs=set(),created_sources={},source_pending=0,syscall_hooks=calls.append)
        exec(compile(ast.Module(body=[functions['syscall']],type_ignores=[]),'<actual AQ syscall switch>','exec'),shared)
        for created,proofs,pending,expected in (({},set(),0,[]),({3:100},set(),0,[]),
            ({3:100},{3},3,[]),({3:100},{3},0,[False]),({3:100,4:200},{3},0,[]),
            ({3:100,4:200},{3,4},0,[False])):
            calls.clear();shared.update(created_sources=created,proofs=proofs,source_pending=pending)
            shared['syscall']();self.assertEqual(calls,expected)
        for call in (22,132):
            calls.clear();current['call']=call;shared['syscall']();self.assertEqual(calls,[])
        # Actual root GETPID effects and CREATE/CANCEL admission still execute.
        current.update(slot=0,call=22);effects=[];shared['result']=lambda:effects.append('result')
        shared['syscall']();self.assertEqual(effects,['result']);self.assertEqual(calls,[])
        current['call']=132;shared.update(created=None,create_begin_hook=types.SimpleNamespace(enabled=False),
            cancel_hook=types.SimpleNamespace(enabled=False),user=lambda *args:struct.pack('<4I',6,80,1,0),struct=struct)
        shared['syscall']();self.assertTrue(shared['create_begin_hook'].enabled)
        shared['user']=lambda *args:struct.pack('<4I',1,64,3,0)
        shared['syscall']();self.assertTrue(shared['cancel_hook'].enabled)
        self.assertIn("Hook('process_run_syscall64.pid',syscall)",body)
        self.assertIn("Hook('family_syscall64',syscall)",body)
        self.assertIn('start_hook.enabled=True\n        syscall_hooks(True)',ast.get_source_segment(body,functions['create_end']))
        self.assertIn('start_hook.enabled=True\n    syscall_hooks(True)',ast.get_source_segment(body,functions['finish']))

    def test_actual_failed_cpu_prefix_is_persisted_not_accepted(self):
        import ast
        import run_qemu_x86_64_service_pio as runtime
        body=runtime.observer_body();tree=ast.parse(body)
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CPULedger')
        actual=ast.get_source_segment(body,node)
        self.assertEqual(actual.replace("path.open('xb',buffering=0)","path.open('xb')"),inspect.getsource(runtime.cpu.CPULedger).strip())
        namespace=dict(hashlib=hashlib,cpu_pack=runtime.cpu.cpu_pack)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual AQ CPU ledger>','exec'),namespace)
        with tempfile.TemporaryDirectory(dir=runtime.BASE) as temporary:
            path=Path(temporary)/'cpu.bin';trace=[];ledger=namespace['CPULedger'](path,trace.append)
            ledger.event(kind='cpu_start',slot=2,gen=3,now=0,records=[3,32,0,0,100,0,0,0])
            self.assertEqual(path.stat().st_size,168)
            with self.assertRaisesRegex(ValueError,'missing closure'):runtime.cpu.expand_cpu_trace(''.join(trace),path.read_bytes())
            ledger.finish();self.assertIn('cpu_start',runtime.cpu.expand_cpu_trace(''.join(trace),path.read_bytes()))

    @staticmethod
    def sample(case):
        import run_qemu_x86_64_service_pio as runtime
        from test_x86_64_pool_pio import PoolPioTests
        serial,events,oom,count,sha=PoolPioTests.sample(case)
        driver=runtime.owner.dimensions(case)[1];values={};totals={};out=[];tick=0;starts={};ready={}
        for event in events:
            kind=event['kind'];gen=event.get('gen')
            if kind=='boot' or kind=='finish':tick=0
            if kind=='peer':event=dict(event,sleeps=60)
            if kind=='ready':
                event=dict(event,deadline=(tick+250)*10);ready[gen]=event
            if kind=='request':
                pause_start=tick
                for step,advance,state in ((0,0,1),(1,2,6),(2,80,6)):
                    tick+=advance
                    out.append(dict(kind='cpu_pause',step=step,slot=driver,gen=gen,root=starts[gen]['parent'],now=tick,
                        records=list(values[gen]),state=state,ms=800,profile=[1,24,1,0,ready[gen]['deadline']],
                        root_state=6 if step==1 else 2,wait=[54,42,0x410100,800],
                        completion=[tick,pause_start+80,-110] if step==2 else []))
            if kind=='release':
                words=values[gen];out.append(dict(kind='cpu_final',slot=event['slot'],gen=gen,now=tick,records=list(words)))
                totals[gen]=words[2]
            out.append(event)
            if kind=='start':
                starts[gen]=event
                values[gen]=[gen,32,0,0,100,tick,0,0]
                out.append(dict(kind='cpu_start',slot=event['slot'],gen=gen,now=tick,records=list(values[gen])))
            if kind=='bind':
                for index in range(40):
                    tick+=5;before=list(values[gen]);after,result=runtime.cpu.charge_result(before,tick);values[gen]=after
                    out.append(dict(kind='cpu_charge',slot=driver,gen=gen,now=tick,before=before,after=list(after),result=result))
                    if index%5==4:out.append(dict(kind='cpu_batch',gen=gen,bursts=index+1))
                for step in (0,6,12):
                    if step:tick+=66
                    out.append(dict(kind='cpu_idle',slot=driver,gen=gen,step=step,now=tick,records=list(values[gen])))
            if kind=='partial' and event['mode']==9:
                while values[gen][7]<32:
                    tick+=1;before=list(values[gen]);after,result=runtime.cpu.charge_result(before,tick);values[gen]=after
                    out.append(dict(kind='cpu_charge',slot=driver,gen=gen,now=tick,before=before,after=list(after),result=result))
        def receipt(match):
            fields=list(struct.unpack('<4I2Q',bytes.fromhex(match[1])));fields[4]=totals[fields[1]]
            return match[0].replace(match[1],struct.pack('<4I2Q',*fields).hex().upper())
        serial=runtime.owner.wide.process.REAP.sub(receipt,serial)
        return serial,out,oom,count,sha

    def test_cpu_and_owner_oracles_all_cases_and_negatives(self):
        import run_qemu_x86_64_service_pio as runtime
        for case in range(16):
            serial,events,oom,count,sha=self.sample(case)
            trace='\n'.join('POOL_PIO '+json.dumps(e) for e in events)
            self.assertTrue(runtime.owner_validator()(serial,trace,case,oom,count,sha))
            runtime.validate_cpu(serial,events,case)
            runtime.validate_service_pause(events,case)
            for kind,field,value in (('cpu_charge','result',0),('cpu_batch','bursts',50),('cpu_final','now',0),('cpu_idle','step',12)):
                bad=copy.deepcopy(events);next(e for e in bad if e['kind']==kind)[field]=value
                with self.assertRaises(ValueError):runtime.validate_cpu(serial,bad,case)
            for kind in ('cpu_start','cpu_charge','cpu_final','cpu_batch','cpu_idle'):
                bad=copy.deepcopy(events);bad.pop(next(i for i,e in enumerate(bad) if e['kind']==kind))
                with self.assertRaises((ValueError,KeyError)):runtime.validate_cpu(serial,bad,case)
            for step in (6,12):
                bad=copy.deepcopy(events);entry=next(e for e in bad if e['kind']=='cpu_idle' and e['step']==step)
                earlier=next(e for e in bad if e['kind']=='cpu_idle' and e['gen']==entry['gen'] and e['step']==step-6)
                entry['now']=earlier['now']+59
                with self.assertRaises(ValueError):runtime.validate_cpu(serial,bad,case)
            bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='cpu_idle')['records'][5]+=1
            with self.assertRaises(ValueError):runtime.validate_cpu(serial,bad,case)

    def test_fatal_words_full_snapshots_and_physical_order(self):
        import run_qemu_x86_64_service_pio as runtime
        saved=[bytearray(size) for _,size in runtime.FATAL_RANGES];generation=8;owner_handle=(generation<<32)|7
        struct.pack_into('<2Q',saved[0],7*1024,1,generation)
        struct.pack_into('<4Q',saved[1],7*32,generation,32,0,0)
        struct.pack_into('<4Q',saved[2],7*32,100,100,0,0)
        struct.pack_into('<4I',saved[3],0,5,336,8,0);struct.pack_into('<Q',saved[3],272+7*8,100)
        struct.pack_into('<Q',saved[4],7*64,owner_handle);struct.pack_into('<I',saved[8],7*4,generation)
        struct.pack_into('<8Q',saved[9],0,owner_handle,owner_handle^0xffffffffffffffff,0,110,120,2,110,0)
        saved=list(map(bytes,saved));folder=ROOT/'build/codex-agent/r83aq-service-pio'/('host-fatal-'+uuid.uuid4().hex);folder.mkdir()
        for kind in runtime.FATAL_CASES:
            out=folder/kind;out.mkdir();changed,writes=runtime.fatal_mutation(kind,saved)
            self.assertEqual(len(writes),1);self.assertEqual(len(writes[0][2]),8);self.assertEqual(changed[9:],saved[9:])
            for name,parts in {'before':saved,**{n:changed for n in ('damaged','fenced','diagnostic','halt')}}.items():
                (out/(name+'.bin')).write_bytes(b''.join(parts))
            sha=hashlib.sha256(b''.join(changed)).hexdigest()
            events=[dict(kind='mode',gen=1,address=0x415008,physical=0x100000008,before=0,value=5),dict(kind='release'),
                dict(kind='inject',case=kind,original=hashlib.sha256(b''.join(saved)).hexdigest(),sha=sha,writes=8),
                dict(kind='fence',physical=1,sha=sha),dict(kind='diagnostic',interrupts=0,sha=sha),dict(kind='halt',cli_hlt=1,sha=sha)]
            serial='REIST_X86_64_EXCEPTION_FATAL pio=1\n'
            trace='\n'.join('SERVICE_PIO_FATAL '+json.dumps(e) for e in events)
            self.assertEqual(runtime.validate_fatal(serial,trace,kind,out),1)
            for left,right in (('"physical": 1','"physical": 0'),('"writes": 8','"writes": 16'),('"interrupts": 0','"interrupts": 1')):
                with self.assertRaises(ValueError):runtime.validate_fatal(serial,trace.replace(left,right),kind,out)
            bad=list(saved);state=bytearray(bad[9]);struct.pack_into('<Q',state,16,1);bad[9]=bytes(state)
            with self.assertRaises(ValueError):runtime.fatal_mutation(kind,bad)

    def test_actual_fatal_callback_requires_physical_fence(self):
        import types
        import run_qemu_x86_64_service_pio as runtime
        folder=ROOT/'build/codex-agent/r83aq-service-pio'/('host-fatal-callback-'+uuid.uuid4().hex);folder.mkdir()
        for early in (False,True):
            out=folder/str(early);out.mkdir();memory={};symbols={};pointer=0x10000
            for name,size in runtime.FATAL_RANGES:
                symbols[name]=pointer;memory[pointer]=bytearray(size);pointer+=0x10000
            for name in ('scheduler_mode','scheduler_current_slot','scheduler_enter_task64.state_published',
                'native_pio_out8.done','reist_x64_period_apply','serial_init64','halt64','process_run_resume64',
                'family_terminal64','scheduler_force_cleanup64','scheduler_release_task_frames64'):
                symbols[name]=pointer;memory[pointer]=bytearray(16);pointer+=0x10000
            memory[symbols['scheduler_mode']][0]=8;memory[symbols['halt64']][:4]=b'\xfa\xf4\xeb\xfd'
            memory[symbols['native_pio_out8.done']-1]=bytearray(b'\xee')
            generation=8;handle=(generation<<32)|7
            struct.pack_into('<2Q',memory[symbols['scheduler_tasks']],7168,1,generation)
            struct.pack_into('<4Q',memory[symbols['scheduler_cpu_budgets']],224,generation,32,0,0)
            struct.pack_into('<4Q',memory[symbols['scheduler_cpu_windows']],224,100,100,0,0)
            struct.pack_into('<4I',memory[symbols['process_run_plan']],0,5,336,8,0)
            struct.pack_into('<Q',memory[symbols['process_run_plan']],328,100)
            struct.pack_into('<Q',memory[symbols['family_records']],448,handle)
            struct.pack_into('<I',memory[symbols['process_run_generations']],28,generation)
            struct.pack_into('<8Q',memory[symbols['native_pio_state']],0,handle,handle^0xffffffffffffffff,0,110,120,2,110,0)
            def span(address,size):
                for base,raw in memory.items():
                    if base<=address and address+size<=base+len(raw):return raw,address-base
                raise AssertionError('unmapped host boundary')
            def read_memory(address,size):
                raw,offset=span(address,size);return bytes(raw[offset:offset+size])
            def write_memory(address,contents):
                raw,offset=span(address,len(contents));raw[offset:offset+len(contents)]=contents
            registers={'rdi':symbols['scheduler_cpu_budgets']+224,'rdx':0,'eflags':0,'edx':0x3f6,'eax':6}
            commands=[];trace=[];hooks=[]
            class Breakpoint:
                def __init__(self,*args,**kwargs):hooks.append(self)
            fake=types.SimpleNamespace(Breakpoint=Breakpoint,selected_inferior=lambda:types.SimpleNamespace(read_memory=read_memory,write_memory=write_memory),
                parse_and_eval=lambda name:registers[name[1:]],execute=commands.append,write=trace.append)
            namespace=dict(CONFIG=dict(s=symbols,out=str(out),kind='window-slot7',pool_pio_root=0x415000),
                FATAL_RANGES=runtime.FATAL_RANGES,fatal_mutation=runtime.fatal_mutation,read_user_spans=runtime.cpu.read_user_spans)
            with patch.dict(sys.modules,{'gdb':fake}):
                exec(compile(runtime.FATAL_BODY,'<actual AQ fatal callbacks>','exec'),namespace)
                namespace['configured']=namespace['released']=True
                namespace['trigger'].stop();self.assertTrue(namespace['injected'])
                diagnostic=next(h for h in hooks if h.label=='diagnostic')
                if early:
                    diagnostic.stop();self.assertFalse(namespace['diagnosed']);self.assertIn('quit 71',commands)
                    self.assertFalse((out/'diagnostic.bin').exists())
                else:
                    namespace['port_hook'].stop();self.assertTrue(namespace['fenced'])
                    diagnostic.stop();next(h for h in hooks if h.label=='halt').stop()
                    self.assertTrue(namespace['diagnosed']);self.assertIn('quit 0',commands);self.assertNotIn('quit 71',commands)
                    self.assertEqual((out/'damaged.bin').read_bytes(),(out/'fenced.bin').read_bytes())
                    self.assertEqual((out/'damaged.bin').read_bytes(),(out/'halt.bin').read_bytes())


def load_tests(loader,tests,pattern):
    import test_x86_64_binary_memory,test_x86_64_file_transport,test_x86_64_cpu_trace
    tests.addTests(loader.loadTestsFromModule(test_x86_64_binary_memory))
    tests.addTests(loader.loadTestsFromModule(test_x86_64_file_transport))
    tests.addTests(loader.loadTestsFromModule(test_x86_64_cpu_trace))
    return tests


if __name__=='__main__':unittest.main()
