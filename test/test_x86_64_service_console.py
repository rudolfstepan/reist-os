"""Actual service-root console boundary; no source-pattern-only admission proof."""
from pathlib import Path
import copy,inspect,json,re,struct,subprocess,sys,textwrap,types,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host

class ServiceConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'build/codex-agent/r83au-service-console/host'/uuid.uuid4().hex
        cls.folder.mkdir(parents=True)

    def test_actual_service_and_child_admission(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('process_run_admit64:',1)[1].split('process_run_validate64:',1)[0]
        family=(ROOT/'arch/x86_64/proc/task_family.inc').read_text()
        child=family.split('family_profile_admit64:',1)[1].split('; RDI profile-v1,',1)[0]
        asm='BITS 64\n'+''.join('%define '+n+' 1\n' for n in (
            'REIST_NATIVE_PROGRAMS','REIST_NATIVE_LIFECYCLE','REIST_NATIVE_TASK_POOL',
            'REIST_NATIVE_SERVICE_CPU','REIST_NATIVE_CONSOLE','REIST_NATIVE_SERVICE_CONSOLE'))
        asm+='section .text\nglobal process_run_admit64, family_profile_admit64\nprocess_run_admit64:\n'+body
        asm+='family_profile_admit64:\n'+child
        host.TaskFrameTests().build(asm,ROOT/'test/x86_64_service_console_host.c','SERVICE_CONSOLE_ADMISSION')

    def test_old_producer_commands(self):
        import test_x86_64_live_file as old
        source=textwrap.dedent(inspect.getsource(old.LiveFileTests.test_old_producer_commands_exact_with_modeled_tool_outputs))
        source=source.replace('c7e5e72a:scripts','473da11c:scripts')
        source=source.replace('    for index,profile in enumerate(profiles):',
            '    profiles.extend([dict(console=True),dict(console=True,native_shell=True),dict(pio_profile,filesystem=True,file_launch=True,live_file=True)])\n    for index,profile in enumerate(profiles):')
        ns=dict(vars(old));exec(source,ns);ns['test_old_producer_commands_exact_with_modeled_tool_outputs'](self)

    def test_selectors_before_effects(self):
        import build_x86_64_boot_programs as producer
        from test_x86_64_live_file import PROFILE
        for update in (dict(service_console=1),dict(service_console='1'),dict(live_file=False),
                       dict(console=True),dict(native_shell=True),dict(service_cpu=True),dict(service_pio=True)):
            options=dict(PROFILE,service_console=True);options.update(update)
            target=self.folder/('absent-'+uuid.uuid4().hex)
            with patch.object(producer.subprocess,'run',side_effect=AssertionError('premature effect')):
                with self.assertRaises(ValueError):producer.build(target,['cc'],['as'],['ld'],0,**options)
            self.assertFalse(target.exists())
        from test_x86_64_file_launch import direct_make_plan,MAKE_FILE_PROFILE
        options={'X86_64_NATIVE_'+name:'0' for name in MAKE_FILE_PROFILE}
        options.update({'X86_64_NATIVE_'+name:'1' for name in ('PROCESSES','IPC','RAM','HEAP','RUNTIME','PROGRAMS',
            'LIFECYCLE','STARTUP','IMPORT','PIO','BLOCK','WIDE','BLOCK_PROFILE','FILESYSTEM','FILE_LAUNCH','TASK_POOL','POOL_PIO','LIVE_FILE','SERVICE_CONSOLE')})
        result=direct_make_plan(self.folder,options);self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('--service-console',result.stdout);self.assertIn('-DREIST_NATIVE_SERVICE_CONSOLE=1',result.stdout)
        for update in ({'X86_64_NATIVE_SERVICE_CONSOLE':'2'},{'X86_64_NATIVE_SERVICE_CONSOLE':'1 0'},
                       {'X86_64_NATIVE_LIVE_FILE':'0'},{'X86_64_NATIVE_CONSOLE':'1'},{'X86_64_NATIVE_SHELL':'1'}):
            self.assertNotEqual(direct_make_plan(self.folder,dict(options,**update)).returncode,0)
        source=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text().split('$RepoRoot =',1)[0]
        source+='\n@{live=[int]$NativeLiveFile.IsPresent;console=[int]$NativeConsole.IsPresent;service=[int]$NativeServiceConsole.IsPresent} | ConvertTo-Json -Compress\n'
        path=self.folder/'admit.ps1';path.write_text(source)
        for flags in ([],['-NativeConsole'],['-NativeShell'],['-NativeServiceCPU'],['-NativeServicePIO']):
            r=subprocess.run(['powershell.exe','-NoProfile','-File',str(path),'-NativeServiceConsole',*flags],
                cwd=ROOT,capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if flags:self.assertNotEqual(r.returncode,0)
            else:self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),dict(live=1,console=0,service=1))

    def test_actual_fixture_compilation_and_file_bound(self):
        import test_x86_64_live_file as old
        source=textwrap.dedent(inspect.getsource(old.LiveFileTests.test_actual_new_role_syntax_and_file_extent))
        source=source.replace('arch/x86_64/user/live_file.c','arch/x86_64/user/service_console.c')
        source=source.replace("'-DREIST_NATIVE_LIVE_FILE=1'","'-DREIST_NATIVE_LIVE_FILE=1','-DREIST_NATIVE_SERVICE_CONSOLE=1'")
        ns=dict(vars(old));exec(source,ns);ns['test_actual_new_role_syntax_and_file_extent'](self)

    def test_actual_observer_and_oracle(self):
        import run_qemu_x86_64_service_console as run
        class Hook:
            def __init__(self,name,fn):self.enabled=True;self.name=name;self.fn=fn
        names=('scheduler_current_slot','scheduler_tasks','family_profiles','syscall_rax','syscall_rdi',
               'syscall_rsi','syscall_rdx','syscall_r10','syscall_r8','syscall_r9')
        symbols={name:(i+1)*0x10000 for i,name in enumerate(names)}
        for case in range(18):
            output=[];plan=run.live.roles(case);current={};record=[0]*10;neighbors={}
            def task(slot):
                if slot==current['slot']:return [2,current['gen'],0x100001000]+[0]*125
                return [6,neighbors[slot],0x100002000]+[0]*125
            def q(a):return current[next(n for n,p in symbols.items() if p==a).removeprefix('syscall_')]
            def memory(a,n):
                slot=current['slot']
                self.assertEqual((a,n),(symbols['family_profiles']+slot*32,32))
                return struct.pack('<4Q',current['gen'],(1<<9)|(((1<<15)|(1<<20)) if not slot else 0),
                                   (1<<49) if slot in (0,2) else 0,(1<<4) if slot<2 else 0)
            def user(t,a,n):
                if n==80:self.assertEqual(a,0x420000);return struct.pack('<10Q',*record)
                self.assertEqual((a,n),(0x40fff0,1));return b'\n'
            registers=lambda n:dict(eflags=0,cr3=0x100001000,r12=symbols['scheduler_tasks']+current['slot']*1024,rax=current.get('result',0))[n]
            starts={}
            ns=dict(struct=struct,json=json,S=symbols,CONFIG=dict(roles=plan,result_address=0x420000),starts=starts,mode=lambda:8,
                    q=q,d=lambda a:current['slot'],task=task,mem=memory,user=user,reg=registers,Hook=Hook,
                    gdb=types.SimpleNamespace(write=output.append),start_hook=Hook('start',lambda:starts.update({current['gen']:dict(slot=current['slot'])})))
            exec(run.EXTRA,ns)
            def calls(gen,app=0):
                nonlocal record,neighbors
                info=plan[gen];slot=info['slot'];record=[0]*10
                if app:
                    record=[0x4c49564546494c31,2,((app-1)<<32)|3,((app-2)<<32)|2,(app<<32)|4,0,0x100000000,0x100001000,0,2]
                    neighbors={2:app-2,3:app-1,4:app}
                for op in (15,20):
                    size=int(not slot and op==20)
                    current.clear();current.update(slot=slot,gen=gen,rax=op,rdi=int(op==20),rsi=0x40fff0 if size else 0,
                                                   rdx=size,r10=0,r8=0,r9=0,result=-13 if slot else size)
                    if op==15 and slot:
                        self.assertFalse(ns['console_denial_hook'].enabled)
                        ns['start_hook'].fn()
                        self.assertTrue(ns['console_denial_hook'].enabled)
                    ns['console_enter'](bool(slot));self.assertTrue(ns['console_return_hook'].enabled)
                    ns['console_return']();self.assertFalse(ns['console_return_hook'].enabled)
                    if slot:self.assertEqual(ns['console_denial_hook'].enabled,op==15)
            for gen,info in plan.items():
                calls(gen)
                if info['role']=='program':calls(info['root'],gen)
            trace=''.join(output);rows=run.validate_console(trace,case)
            for key,value in (('slot',7),('gen',999),('result',99),('after','ff'),('profile',[999,0]),
                              ('profile',[1,(1<<9)|(1<<15)|(1<<20),0,0]),('unused',[0,0,1])):
                bad=copy.deepcopy(rows);bad[0][key]=value
                with self.assertRaises((ValueError,KeyError)):
                    run.validate_console(''.join('SERVICE_CONSOLE '+json.dumps(r)+'\n' for r in bad),case)
            with self.assertRaises(ValueError):run.validate_console(''.join(output[:-1]),case)
            self.assertIsNone(ns['console_pending'])
            self.assertFalse(ns['console_denial_needed'])
        self.assertEqual(run.CASES,run.live.CASES)
        image=ROOT/'build/codex-agent/r83ar-live-file/native/x86_64/reist-x86_64-bootstrap.elf'
        config,_,raw=run.live.image_config(image)
        old=run.live.observer(config,self.folder,0,2,None,raw)
        new=run.observer(config,self.folder,0,2,None,raw)
        self.assertEqual(new.replace('\n'+run.EXTRA,'',1),old)
        for block in re.findall(r'(?ms)^python\n(.*?)^end\n',new):compile(block,'<actual service-console observer>','exec')

    def test_actual_family_profile_slot_lookup(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text().split('family_profile_apply64:',1)[1]
        match=re.search(r'    mov eax,edi\n    shl eax,5\n    lea r10,\[rel family_profiles\]\n    add r10,rax\n',source)
        self.assertIsNotNone(match)
        asm='BITS 64\nsection .bss\nalign 16\nglobal family_profiles\nfamily_profiles: resq 32\nsection .text\nglobal lookup\nlookup:\n'+match[0]+'    mov rax,r10\n    ret\n'
        c='''#include <stdint.h>
#include <stdio.h>
extern uint64_t family_profiles[8][4];
extern uint64_t *__attribute__((sysv_abi)) lookup(unsigned);
int main(void) {
    for(unsigned n=0;n<8;n++) {
        family_profiles[n][0]=n+10;
        if(lookup(n)!=family_profiles[n] || lookup(n)[0]!=n+10)return 1;
    }
    puts("SERVICE_PROFILE_LOOKUP_OK");return 0;
}
'''
        host.TaskFrameTests().build(asm,c,'SERVICE_PROFILE_LOOKUP')
        scheduler=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        self.assertIn('cmp dword [rel process_run_plan],NATIVE_POOL_RUN_VERSION\n    je family_profile_apply64',scheduler)
        import run_qemu_x86_64_service_console as run
        self.assertIn("mem(S['family_profiles']+slot*32,32)",run.EXTRA)
        self.assertNotIn('scheduler_syscall_profiles',run.EXTRA)

    def test_actual_accepted_receipt_schema(self):
        import verify_x86_64_service_console as verify
        accepted=verify.read(verify.PRIOR)
        self.assertEqual(verify.digest(verify.PRIOR),verify.PRIOR_SHA)
        self.assertTrue(accepted['tools']);self.assertNotIn('tools_sha256',accepted)
        import tomllib
        package=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))['packages'][0]
        with patch.object(verify,'binding',return_value=dict(package=package)),patch.object(verify,'verify_files') as check:
            self.assertTrue(verify.defaults()['passed'])
        self.assertEqual(check.call_args_list,[( (accepted['evidence_sha256'],),{}),((accepted['tools'],),{})])

    def test_reuse_rejects_production_or_inventory_drift(self):
        import verify_x86_64_service_console as verify
        old=verify.read(verify.PARENT/'proof-fix/frozen.json')['sources']
        current={n:verify.digest(ROOT/n) for n in old}
        verify.reuse_sources(old,current)
        for name in ('arch/x86_64/user/service_console.c','arch/x86_64/proc/process_run.inc',
                     'scripts/build_x86_64_boot_programs.py','test/test_x86_64_pool_pio.py'):
            bad=dict(current);bad[name]='0'*64
            with self.assertRaises(ValueError):verify.reuse_sources(old,bad)
        bad=dict(current);bad['unbound.c']='0'*64
        with self.assertRaises(ValueError):verify.reuse_sources(old,bad)
        bad=dict(current);bad.pop('Makefile')
        with self.assertRaises(ValueError):verify.reuse_sources(old,bad)

    def test_actual_scoped_start_filters_and_interleaved_owners(self):
        import run_qemu_x86_64_service_console as run
        class Hook:
            def __init__(self,name,fn):self.enabled=True;self.fn=fn
        active=[0,2,3];starts={};calls=[];reads=[]
        def original():
            calls.append(tuple(active))
            if active[0]==8:starts[active[2]]=dict(slot=active[1])
        def current(a):reads.append(a);self.assertEqual(active[0],8);return active[1]
        ns=dict(Hook=Hook,starts=starts,mode=lambda:active[0],S={'scheduler_current_slot':1},d=current,
                task=lambda slot:[2,active[2]],start_hook=Hook('start',original))
        exec(run.EXTRA,ns)
        for mode in range(8):active[0]=mode;ns['start_hook'].fn()
        self.assertFalse(reads);self.assertEqual(len(calls),8)
        self.assertFalse(ns['console_denial_hook'].enabled)
        active[0]=8;ns['start_hook'].fn();ns['start_hook'].fn()
        self.assertEqual(ns['console_denial_needed'],{3})
        active[1:]=[3,4];ns['start_hook'].fn()
        self.assertEqual(ns['console_denial_needed'],{3,4})
        ns['console_denial_needed'].clear();ns['console_denial_hook'].enabled=False
        ns['start_hook'].fn()
        self.assertFalse(ns['console_denial_hook'].enabled)
        active[1:]=[2,6];ns['start_hook'].fn()
        self.assertEqual(ns['console_denial_needed'],{6})

if __name__=='__main__':unittest.main()
