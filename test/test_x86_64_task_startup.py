"""Actual immutable native startup assembly and SDK; guest oracles supplement it."""
from pathlib import Path
import sys, unittest, os, subprocess, uuid, re, struct
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class StartupTests(unittest.TestCase):
    @staticmethod
    def sample(oom=None):
        from test_x86_64_task_family import FamilyTests
        import run_qemu_x86_64_task_startup as r
        serial,trace=FamilyTests.sample(4 if oom is not None else 0,oom)
        count=9 if oom is not None else 10
        def values(gen):
            n=(gen-1)%count+1
            return (n-1 if n<=2 else 2, {1:70,2:71,3:60,4:61,5:68,6:134,7:0,8:68,9:0,10:68}[n],3 if n in (6,7,9) else 4)
        def receipt(m):
            _,gen,_,_,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]))
            slot,status,state=values(gen)
            return 'REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,state,ticks,rip).hex().upper()
        serial=r.family.process.REAP.sub(receipt,serial)
        def frame(m):
            if int(m[2])!=8:return m[0]
            slot,_,state=values(int(m[4]))
            return m[0].replace('slot='+m[3],'slot='+str(slot)).replace('state='+m[5],'state='+str(state))
        trace=r.BEFORE.sub(frame,trace)
        def after(m):
            if int(m[1])<=17:return m[0]
            state=values(int(m[2]))[2]
            return m[0].replace('state='+m[3],'state='+str(state))
        trace=r.AFTER.sub(after,trace)
        trace=re.sub(r'FAMILY_CANCEL[^\n]*\n','',trace)
        trace=re.sub(r'FAMILY_OOM[^\n]*\n','',trace)
        def fence(m):
            gen=int(m[2]);slot=values(gen)[0];text=f'FAMILY_FENCE slot={slot} gen={gen} ipc=1 heap=1 profile=1'
            if (gen-1)%count+1 in (7,9):text=f'FAMILY_CANCEL slot=2 gen={gen} state=6 ipc=0 heap=0 reason=2\n'+text
            return text
        trace=re.sub(r'FAMILY_FENCE slot=(\d+) gen=(\d+) ipc=1 heap=1 profile=1',fence,trace)
        def start(m):
            gen=int(m[2]);slot=values(gen)[0]
            text=f'FAMILY_START slot={slot} gen={gen} image={3+slot} high=1 wx=1 argv=1'
            if slot==2:
                n=(gen-1)%count+1;argc=0 if n==3 else 1 if n==4 else 8
                text=f'STARTUP_ARGS gen={gen} argc={argc} immutable=1\n'+text
                if oom is not None and n==3:
                    owner=((gen-1)//count*count+1)<<32
                    text=f'FAMILY_OOM acquired={oom}\nSTARTUP_OOM_BOUNDARY owner={owner} acquired={oom} result=-12\n'+text
            return text
        trace=re.sub(r'FAMILY_START slot=(\d+) gen=(\d+) image=(\d+) high=1 wx=1 argv=1',start,trace)
        return serial,trace+'STARTUP_SCRUB bytes=4096 complete=1\n'*64

    def test_guest_oracle(self):
        import run_qemu_x86_64_task_startup as r
        for oom in (None,0,1,2,3,6,9):
            serial,trace=self.sample(oom)
            self.assertEqual(r.validate(serial,trace,oom),20 if oom is None else 18)
            for label in ('TASK_FRAMES_BEFORE','TASK_FRAMES_AFTER','TASK_FRAMES_FREE','FAMILY_START','FAMILY_FENCE','FAMILY_CANCEL','STARTUP_ARGS','STARTUP_SCRUB','PROCESS_ZERO_OK','FAMILY_ZERO'):
                with self.assertRaises(ValueError):r.validate(serial,trace.replace(label,'MISSING'),oom)
            for a,b in (('argc=8','argc=7'),('immutable=1','immutable=0'),('high=1','high=0'),('profile=1','profile=0'),('after=1000007','after=1000006'),('zero=1','zero=0'),('heap=1','heap=0'),('image=5','image=6'),('mode=1','mode=0'),('reason=2','reason=3')):
                with self.assertRaises(ValueError):r.validate(serial,trace.replace(a,b,1),oom)
            for bad in (serial+serial,serial+r.family.FAILURES[0],serial.replace(r.family.process.SUCCESS,'MISSING')):
                with self.assertRaises(ValueError):r.validate(bad,trace,oom)
            first=r.family.process.REAP.search(serial)
            for offset in (0,4,8,12,16,24):
                data=bytearray.fromhex(first[1]);data[offset+3]^=128
                with self.assertRaises(ValueError):r.validate(serial.replace(first[1],data.hex().upper(),1),trace,oom)
            if oom is not None:
                for bad in (trace.replace('STARTUP_OOM_BOUNDARY','MISSING',1),
                            trace.replace('result=-12','result=3',1),
                            trace.replace('owner=4294967296','owner=4294967297',1)):
                    with self.assertRaises(ValueError):r.validate(serial,bad,oom)

    def test_oom_window_and_fixture_extent(self):
        import run_qemu_x86_64_task_startup as r
        record=bytearray(36896);record[:8]=b'RNPGv1\0\0';record[24]=5
        self.assertEqual(r.creation_allocations(record),6) # Exact original defect.
        record[28:30]=bytes([6,6]);self.assertEqual(r.creation_allocations(record),10)
        self.assertTrue(all(n<r.creation_allocations(record) for n in (0,1,2,3,6,9)))
        for bad in (record[:-1],bytes(36896)):
            with self.assertRaises(ValueError):r.creation_allocations(bad)
        class Breakpoint:
            def __init__(self,*args,**kwargs):pass
        class Debugger:
            def __init__(self):self.Breakpoint=Breakpoint;self.messages=[];self.commands=[]
            def write(self,message):self.messages.append(message)
            def execute(self,command):self.commands.append(command)
        code=r.injection_guard({'family_create64.parent_result':0x1000},9)
        for missed,result,quit_code in ((True,3,'quit 64'),(False,3,'quit 65'),(False,0xfffffffffffffff4,None)):
            debugger=Debugger()
            env=dict(gdb=debugger,armed=missed,injected=not missed,
                injection_owner=1<<32,reg=lambda name:result)
            exec(code.removeprefix('python\n').removesuffix('end\n'),env)
            stop=env['StartupInjectionEnd']().stop
            self.assertEqual(stop(),quit_code is not None)
            self.assertEqual(debugger.commands,[] if quit_code is None else [quit_code])
            self.assertFalse(env['armed'])
            if quit_code is None:
                self.assertEqual(len(debugger.messages),1);self.assertFalse(stop())
                self.assertEqual(len(debugger.messages),1)

    def test_fixture_exclusion(self):
        for flags in (['-StartupCase','1'],['-NativeStartup','-FamilyCase','1']):
            out=ROOT/'build/codex-agent/r83af-startup'/('excluded-'+uuid.uuid4().hex)
            r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-OutputDirectory',out.relative_to(ROOT).as_posix(),*flags],cwd=ROOT,capture_output=True,text=True,
                timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())

    def test_actual_startup_and_sdk(self):
        source=(ROOT/'arch/x86_64/proc/task_family.inc').read_text().split('; RUNTIME ADAPTER')[0]
        asm='BITS 64\nsection .text\n'+source+'\n'
        asm+=(ROOT/'arch/x86_64/proc/startup_stack.asm').read_text()
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83af-startup'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        (folder/'source.asm').write_text(asm,encoding='ascii')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=60,
                capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-2500:]);return r.stdout
        obj=folder/'code.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',folder/'source.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                'test/x86_64_task_startup_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('TASK_STARTUP_HOST_OK',run([exe],opt+'-run'))

if __name__=='__main__':unittest.main()
