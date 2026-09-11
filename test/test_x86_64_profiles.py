"""Actual native syscall authority mechanism; no host OS syscalls in fixtures."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class ProfileTests(unittest.TestCase):
    def test_runtime_oracle(self):
        from run_qemu_x86_64_profiles import validate,PARENT,CHILD
        def life(op,gen):
            role=int(gen!=40);mask=sum(1<<n for n in (CHILD if role else PARENT)) if op==1 else 0
            state=9 if op==1 else 8 if role else 4
            return f'PROFILE_LIFE op={op} gen={gen} task={0x10000+role*256:x} profile={0x20000+role*16:x} state={state} live={gen if op==1 else 0} mask={mask:x} result=1\n'
        def deny(gen,bits):
            return ''.join(f'PROFILE_DENY gen={gen} number={n}\n'*2 for n in sorted(set(range(64))-bits|{1<<32,(1<<64)-1}))
        trace=life(1,40);serial=''
        for gen in (41,42):
            trace+=deny(40,PARENT)+life(1,gen)+deny(gen,CHILD)+life(3,gen)
            serial+=f'CHILD_EXIT_REAP_OK status=0000005B generation={gen:02X} parent=07 queued=00 rip=0000000000400669\n'
            serial+='REIST_X86_64_RING3_SHELL_RUN_OK\nPROFILE_OK\n'
        trace+=life(3,40)
        validate(serial,trace,0x10000,0x20000,0x400669)
        for bad in (trace.replace('state=8','state=4',1),trace.replace('result=1','result=0',1),
                    trace.replace('live=41','live=40',1),trace.replace('mask=fe010041d08200','mask=0',1),
                    trace.replace('task=10100','task=10000',1),trace.replace('profile=20010','profile=20000',1),
                    trace.replace('number=4294967296','number=0',1),trace.replace('PROFILE_DENY','MISSING',1),
                    trace+trace,trace.replace('gen=42','gen=41')):
            with self.assertRaises(RuntimeError):validate(serial,bad,0x10000,0x20000,0x400669)
        for bad in (serial.replace('PROFILE_OK',''),serial.replace('400669','400667',1),
                    serial.replace('queued=00','queued=01',1),serial.replace('generation=2A','generation=29'),
                    serial.replace('0000005B','0000005C',1),serial+serial):
            with self.assertRaises(RuntimeError):validate(bad,trace,0x10000,0x20000,0x400669)

    def test_shared_ingress_and_teardown(self):
        s=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        for name,end in [('scheduler_install_shell_syscall_profile64','scheduler_clear_shell_syscall_profile64'),
                         ('scheduler_clear_shell_syscall_profile64','scheduler_handle_runqueue_exit64'),
                         ('scheduler_validate_shell_syscall_profile64','scheduler_shell_syscall_dispatch64')]:
            body=s.split(name+':',1)[1].split(end+':',1)[0]
            self.assertIn('jmp scheduler_profile_apply64',body)
        timer=s.split('x86_64_scheduler_shell_timer_validate64:',1)[1].split('x86_64_scheduler_shell_timer_tail64:',1)[0]
        self.assertIn('call scheduler_profile_apply64',timer)
        core=(ROOT/'arch/x86_64/proc/syscall_profile.asm').read_text()
        self.assertNotIn('TASK_SHELL',core)
        self.assertNotIn('physical_frame_',core)
        self.assertLess(core.index('cmp rbx, 64'),core.index('bt r11, rbx'))

    def test_fixture_exclusion(self):
        out=ROOT/'build/codex-agent/r83m-profiles'/('excluded-'+uuid.uuid4().hex)
        r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
            '-OutputDirectory',out.relative_to(ROOT).as_posix(),'-ProfileCase','1','-IpcCase','1'],
            cwd=ROOT,capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertNotEqual(r.returncode,0);self.assertIn('ProfileCase is exclusive',r.stdout+r.stderr)
        self.assertFalse(out.exists())

    def test_host(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83m-profiles'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,label,timeout=90):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:]);return r.stdout
        obj=folder/'profile.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/proc/syscall_profile.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                'test/x86_64_profiles_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('X86_64_PROFILES_HOST_OK',run([exe],opt+'-run',10))

if __name__=='__main__':unittest.main()
