"""Execute the actual queue mechanism with native callers and retain logs."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class QueueTests(unittest.TestCase):
    def test_production_adapters_share_the_core_without_role_policy(self):
        source = (ROOT / 'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        core = (ROOT / 'arch/x86_64/proc/queue_core.asm').read_text()
        bridge = source.split('scheduler_queue_apply64:',1)[1].split('scheduler_runqueue_enqueue64:',1)[0]
        self.assertIn('and rsp, -16',bridge)
        self.assertIn('call reist_x64_queue_apply',bridge)
        for name in ('SCHEDULER_MODE','TASK_SHELL','TASK_RUNQUEUE','token','syscall'):
            self.assertNotIn(name,core)
        for start,end in (
            ('scheduler_runqueue_enqueue64:', 'scheduler_runqueue_dequeue64:'),
            ('scheduler_runqueue_dequeue64:', 'scheduler_runqueue_dispatch64:'),
            ('scheduler_deadline_insert64:', 'scheduler_deadline_remove_shell_receive64:')):
            body=source.split(start,1)[1].split(end,1)[0]
            self.assertIn('call scheduler_queue_apply64',body)
            self.assertIn('TASK_GENERATION',body)
        for start,end in (
            ('scheduler_deadline_remove_shell_receive64:', 'scheduler_validate_shell_receive_deadline64:'),
            ('scheduler_deadline_remove_shell_send64:', 'x86_64_scheduler_deadline_tick64:'),
            ('x86_64_scheduler_deadline_tick64:', 'scheduler_sleep_dispatch_or_idle64:')):
            body=source.split(start,1)[1].split(end,1)[0]
            self.assertIn('call scheduler_deadline_remove_exact64',body)
        self.assertIn('cmp r8d, 64',core)
        self.assertIn('shr rax, 32\n    jnz .fail',core)

    def test_actual_queue_mechanism(self):
        suppress_windows_test_dialogs()
        folder = ROOT / 'build/codex-agent/r83d-queue' / ('host-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(folder / 'cache')
        def run(args, name, timeout=90):
            result = subprocess.run(list(map(str,args)), cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=timeout,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder / (name+'.log')).write_text(result.stdout+result.stderr, encoding='utf-8')
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
            return result.stdout
        obj = folder / 'queue.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',
             'arch/x86_64/proc/queue_core.asm','-o',obj], 'assemble')
        for opt in ('-O0','-O2'):
            exe = folder / (opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,
                 '-mno-red-zone','-fno-sanitize=all','-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','test/x86_64_queue_host.c',obj,
                 '-o',exe], opt+'-build')
            self.assertIn('X86_64_QUEUE_HOST_OK',run([exe],opt+'-run',10))


if __name__ == '__main__': unittest.main()
