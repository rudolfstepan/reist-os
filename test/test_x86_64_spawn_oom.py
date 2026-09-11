"""Actual production frame claim, ownership and allocator-failure regression."""
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

class OomTests(unittest.TestCase):
    def test_runtime_oracle(self):
        from run_qemu_x86_64_spawn_oom import validate, injection
        serial='';trace=''
        for i in range(2):
            trace+=f'OOM_INJECT ordinal=6 generation={40+i}\n'
            trace+=f'OOM_ROLLBACK generation={40+i} saved={40+i} free=32337 baseline=32337 spawned={i} completed={i} active=0 claim=0 selector=1\n'
            serial+=f'CHILD_EXIT_REAP_OK status=0000005B generation={41+i:02X} parent=01 queued=00 rip=0000000000400537\n'
            serial+='REIST_X86_64_RING3_SHELL_RUN_OK\nOOM_OK\n'
        validate(serial,trace,6,0x400537)
        bad_traces=[trace.replace('ordinal=6','ordinal=5',1),trace.replace('saved=40','saved=41',1),
            trace.replace('free=32337','free=32336',1),trace.replace('spawned=0','spawned=1',1),
            trace.replace('completed=0','completed=1',1),trace.replace('active=0','active=1',1),
            trace.replace('claim=0','claim=1',1),trace.replace('selector=1','selector=2',1),
            trace.replace('OOM_INJECT','MISSING',1),trace+trace]
        for bad in bad_traces:
            with self.assertRaises(RuntimeError):validate(serial,bad,6,0x400537)
        for bad in [serial.replace('OOM_OK',''),serial.replace('queued=00','queued=01',1),
                    serial.replace('0000005B','0000005C',1),serial.replace('400537','400539',1),
                    serial.replace('generation=2A','generation=29'),serial+serial]:
            with self.assertRaises(RuntimeError):validate(bad,trace,6,0x400537)
        # Injector is attached to allocator entry, never to a successful return.
        names=['physical_frame_alloc64','scheduler_identity_pool','scheduler_spawn_transaction_active',
               'scheduler_spawn_oom_verified64','scheduler_frame_claim','scheduler_tasks',
               'scheduler_spawn_initial_generation','free_frame_count','scheduler_spawn_initial_free',
               'scheduler_dynamic_spawn_count','scheduler_dynamic_completed_count',
               'scheduler_frame_claim_active','elf_image_selector','scheduler_return64','scheduler_mode']
        script=injection({n:4096*(i+1) for i,n in enumerate(names)},6)
        self.assertIn('set $pc = *(unsigned long long*)$rsp\nset $rsp = $rsp + 8\nset $rax = 0',script)
        self.assertNotIn('physical_frame_free64',script)

    def test_host(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83l-oom'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,label,timeout=90):
            result=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,
                capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
            return result.stdout
        obj=folder/'claim.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/mm/frame_claim.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                'test/x86_64_spawn_oom_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('X86_64_SPAWN_OOM_HOST_OK',run([exe],opt+'-run',10))

    def test_reservation_precedes_identity(self):
        s=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        spawn=s.split('scheduler_shell_spawn_validated64:',1)[1].split('scheduler_handle_shell_wait64:',1)[0]
        self.assertLess(spawn.index('call scheduler_claim_child_frames64'),spawn.index('call scheduler_build_task64'))
        build=s.split('scheduler_build_task64:',1)[1].split('scheduler_build_shell_child_stack64:',1)[0]
        self.assertNotIn('call physical_frame_alloc64',build)
        self.assertEqual(build.count('call scheduler_task_frame_alloc64'),3)
        rollback=s.split('scheduler_spawn_oom_rollback64:',1)[1].split('scheduler_handle_shell_wait64:',1)[0]
        self.assertIn('call physical_free_frame_count64',rollback)
        self.assertIn('scheduler_identity_pool + 20',rollback)
        self.assertIn('mov rax, -12',rollback)

if __name__=='__main__':unittest.main()
