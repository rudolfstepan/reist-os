import unittest
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated function: {signature}")


class BootServiceReadyContractTests(unittest.TestCase):
    def test_cold_preparation_precedes_timed_service_admission(self):
        # Execute the actual boot sequencing, not a second implementation.
        signature = 'static void start_boot_services(void)'
        if signature in self.kernel:
            production = function(self.kernel, signature)
            main = function(self.kernel, 'void kernel_main(')
            self.assertEqual(main.count('start_boot_services();'), 1)
            self.assertLess(main.index('driver_init(multiboot_info);'),
                            main.index('start_boot_services();'))
            self.assertLess(main.index('start_boot_services();'),
                            main.index('configure_network_after_service();'))
        else:
            start = self.kernel.index('    boot_context("userspace-start", "REIST probe"')
            end = self.kernel.index('    supervisor_handle_t video_driver_handle', start)
            production = signature + '{\n' + self.kernel[start:end] + '}\n'
        sys.path.insert(0, str(ROOT/'scripts'))
        from build_user_program import find_zig
        from measure_cpp_baseline import suppress_windows_test_dialogs
        suppress_windows_test_dialogs()
        directory = ROOT/'build/codex-agent/r346-window-options/boot-host'
        directory.mkdir(parents=True, exist_ok=True)
        generated = directory/'boot.c'
        generated.write_text(read('test/boot_service_preparation_host.c').replace(
            '/* PRODUCTION */', production), encoding='utf-8')
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(ROOT/'build/zig-cache')
        for opt in ('-O0', '-O2'):
            exe = directory/('boot'+opt+'.exe')
            result = subprocess.run([str(find_zig()), 'cc', '-std=c11', opt,
                '-UNDEBUG', '-Wall', '-Wextra', '-Werror', str(generated), '-o', str(exe)],
                capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('BOOT_PREPARATION_OK', result.stdout)

    @classmethod
    def setUpClass(cls) -> None:
        cls.kernel = read("kernel/init/kernel.c")
        cls.supervisor = read("kernel/init/supervisor.c")
        cls.supervisor_h = read("include/kernel/supervisor.h")
        cls.sdk_h = read("userspace/sdk/include/x86os.h")
        cls.probe = read("userspace/programs/reist_probe.c")

    def test_report_abi_is_append_only_and_published_after_udp_self_test(self):
        self.assertIn("REIST_REPORT_SERVICE_READY 12U", self.supervisor_h)
        self.assertIn("X86OS_REIST_REPORT_SERVICE_READY 12U", self.sdk_h)
        stale_unbind = self.probe.index("x86os_reist_udp_unbind(stale_binding)")
        ready_report = self.probe.index("X86OS_REIST_REPORT_SERVICE_READY")
        service_loop = self.probe.index("for (;;)", ready_report)
        self.assertLess(stale_unbind, ready_report)
        self.assertLess(ready_report, service_loop)

    def test_readiness_is_protected_and_generation_reset(self):
        self.assertIn("uint32_t service_ready;", self.supervisor_h)
        # Version 3 already added protected post-ready CPU affinity; do not
        # regress the production contract to the old readiness-only version.
        self.assertIn("SUPERVISOR_PROBE_CONTROL_VERSION 3U", self.supervisor_h)
        self.assertIn("uint32_t post_ready_cpu_affinity_mask;", self.supervisor_h)
        ready = function(self.supervisor, "bool supervisor_probe_ready(")
        self.assertIn("control.service_ready != 0U", ready)
        report = function(self.supervisor, "int supervisor_probe_report(")
        self.assertIn("REIST_REPORT_SERVICE_READY", report)
        self.assertIn("control.service_ready = 1U", report)
        fence = function(self.supervisor, "static bool probe_fence_apply(")
        spawn = function(self.supervisor, "static bool probe_spawn_next(")
        self.assertIn("control.service_ready = 0U", fence)
        self.assertIn("control.service_ready = 0U", spawn)

    def test_no_nic_still_waits_bounded_before_boot_and_shell(self):
        configure = function(
            self.kernel, "static void configure_network_after_service(")
        wait = configure.index("while (!supervisor_probe_ready()")
        no_nic = configure.index("if (!netdev_available())")
        self.assertLess(wait, no_nic)
        self.assertIn("10000U", configure)
        self.assertIn("local-only", configure)
        self.assertNotIn("settle_deadline", configure)
        call = self.kernel.index("configure_network_after_service();")
        boot_ok = self.kernel.index('printf("BOOT_OK\\n")', call)
        shell = self.kernel.index(
            'start_userspace_program(multiboot_info, "bin/shell.prg"', boot_ok)
        self.assertLess(call, boot_ok)
        self.assertLess(boot_ok, shell)

    def test_system_program_loading_keeps_vfs_sleepable(self):
        start = function(self.kernel, "static int start_userspace_program(")
        self.assertIn("create_process_for_file_args(", start)
        self.assertIn("wait_for_process(pid)", start)
        self.assertNotIn("scheduler_preempt_disable()", start)
        self.assertNotIn("scheduler_preempt_enable()", start)


if __name__ == "__main__":
    unittest.main()
