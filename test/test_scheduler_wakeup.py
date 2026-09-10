"""Execute actual timed wake/idle dispatch code with real intrusive queues."""
import hashlib
import json
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from measure_cpp_baseline import suppress_windows_test_dialogs
from test_scheduler_slack import function

SIGNATURES = (
    "static bool wait_queue_wake_one_task_locked(",
    "void scheduler_wake_expired_waiters_locked(",
    "void scheduler_wake_expired_sleepers_locked(",
    "void scheduler_pit_interrupt_handler(",
)


class SchedulerWakeupTests(unittest.TestCase):
    def test_scope_guard_rejects_policy_and_wakeup_weakening(self):
        from verify_fat32_write_artifacts import scheduler_protected_source_equal, BASELINE
        old = subprocess.check_output(["git", "show", BASELINE+":kernel/sched/scheduler.c"],
            cwd=ROOT, timeout=15).decode("utf-8").replace("\r\n", "\n")
        new = (ROOT / "kernel/sched/scheduler.c").read_text(encoding="utf-8")
        self.assertTrue(scheduler_protected_source_equal(old, new))
        for before, after in (("current_task < 0 && kernel_context_saved", "true"),
            ("preempt_disable_count == 0U && preemption_pending", "true"),
            ("if (periodic || wake_idle)", "if (true)"),
            ("#define SCHEDULER_QUANTUM_MS 10U", "#define SCHEDULER_QUANTUM_MS 1U"),
            ("task->status = TASK_READY;", "task->status = TASK_RUNNING;"),
            ("candidates[index].runnable = runnable &&", "candidates[index].runnable = true ||"),
            ("if (!spinlock_trylock(&task_table_lock))", "if (false)"),
            ("reschedule_mask |= task->cpu_affinity_mask;", "reschedule_mask = 1U;")):
            self.assertIn(before, new)
            self.assertFalse(scheduler_protected_source_equal(old, new.replace(before, after)), before)

    def test_actual_deadline_wake_and_idle_dispatch(self):
        suppress_windows_test_dialogs()
        compiler = shutil.which("gcc") or shutil.which("clang")
        self.assertIsNotNone(compiler, "host compiler required")
        source = (ROOT / "kernel/sched/scheduler.c").read_text(encoding="utf-8")
        evidence = ROOT / "build/codex-agent/r342-fat32-write" / ("wake-" + uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        (evidence / "scheduler-under-test.h").write_text(
            "\n\n".join(function(source, s) for s in SIGNATURES), encoding="utf-8")
        records = []
        for opt in ("-O0", "-O2"):
            executable = evidence / (opt[1:] + ".exe")
            commands = [[compiler, "-std=c11", opt, "-Wall", "-Wextra", "-Werror",
                         "-I", str(ROOT), "-I", str(evidence),
                         str(ROOT / "test/test_scheduler_wakeup_host.c"),
                         str(ROOT / "kernel/sched/wait_queue.c"), "-o", str(executable)],
                        [str(executable)]]
            for index, command in enumerate(commands):
                start = time.monotonic()
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                    timeout=90 if index == 0 else 30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                records.append(dict(command=command, returncode=result.returncode,
                    elapsed_seconds=time.monotonic()-start, stdout=result.stdout, stderr=result.stderr))
                (evidence / "result.json").write_text(json.dumps(dict(
                    source_sha256=hashlib.sha256(source.encode()).hexdigest(), records=records), indent=2), encoding="utf-8")
                self.assertEqual(result.returncode, 0, str(evidence)+"\n"+result.stdout+result.stderr)
                if index: print(opt, result.stdout.strip(), flush=True)


if __name__ == "__main__":
    unittest.main()
