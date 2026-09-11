"""Real native admission assembly, with all source and destination guards."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class RequestTests(unittest.TestCase):
    def test_runtime_oracle(self):
        from run_qemu_x86_64_requests import validate
        serial=''
        for gen in (41,42):
            serial+=f'REIST_X86_64_CHILD_EXIT_REAP_OK status=0000005B generation={gen:02X} parent=01 queued=00 rip=0000000000400537\r\n'
            serial+='REIST_X86_64_RING3_SHELL_RUN_OK\r\nREQUEST_3_OK\r\n'
        validate(serial,3,0x400537)
        bad=[serial.replace('REQUEST_3_OK',''),serial.replace('0000005B','0000005C',1),
             serial.replace('generation=2A','generation=29'),serial.replace('queued=00','queued=01',1),
             serial.replace('400537','400539',1),serial.replace('parent=01','parent=02',1),
             serial+'REIST_X86_64_CHILD_FAULT_REAP_OK',serial+serial]
        for candidate in bad:
            with self.assertRaises(RuntimeError):validate(candidate,3,0x400537)

    def test_host(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83k-requests'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,label,timeout=90):
            result=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,
                capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
            return result.stdout
        obj=folder/'request.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/proc/request_admission.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                'test/x86_64_requests_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('X86_64_REQUEST_HOST_OK',run([exe],opt+'-run',10))

    def test_production_admission_precedes_effects(self):
        s=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        for name,end in [('read','write'),('write','yield'),('getpid','ipc_create'),('spawnv','spawn'),('spawn','wait'),('wait',None)]:
            section=s.split('scheduler_handle_shell_'+name+'64:',1)[1]
            if end:section=section.split('scheduler_handle_shell_'+end+'64:',1)[0]
            else:section=section.split('scheduler_shell_resume64:',1)[0]
            self.assertIn('call scheduler_request_admit64',section)
        spawn=s.split('scheduler_shell_spawn_validated64:',1)[1].split('scheduler_handle_shell_wait64:',1)[0]
        self.assertLess(spawn.index('call scheduler_validate_shell_child_endpoint64'),spawn.index('call x86_64_elf64_load64'))


if __name__=='__main__':unittest.main()
