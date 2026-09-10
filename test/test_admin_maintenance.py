import unittest
import subprocess
import sys
import shutil
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AdminMaintenanceContracts(unittest.TestCase):
    def test_guest_status_markers_use_complete_lines(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import run_qemu_admin_ata as guest
        for status in (guest.STATUS_ONLINE, guest.STATUS_DOWN):
            output = status + '\n' + guest.MOUNT_FRESH + '\n'
            guest.objects.handoff.validate_handoff_command(output, (status, guest.MOUNT_FRESH), ())
            with self.assertRaises(ValueError):
                guest.objects.handoff.validate_handoff_command(output.replace('resource=1', 'resource=2'), (status,), ())

    def test_ordinary_storage_path_stays_exact(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from verify_fat32_write_artifacts import safety_protected_source_equal, BASELINE
        old = subprocess.check_output(['git', 'show', BASELINE+':kernel/init/storage_safety.c'],
            cwd=ROOT, timeout=15).decode('utf-8').replace('\r\n', '\n')
        new = self.read('kernel/init/storage_safety.c')
        self.assertTrue(safety_protected_source_equal(old, new))
        for before, after in (('!storage_service_resource_available(resource)', 'false'),
            ('state.operation_active != 0U) return false;', 'false) return false;'),
            ('state.write_fenced = 1U;', 'state.write_fenced = 0U;'),
            ('#define STORAGE_WRITE_DEADLINE_MS 10000U', '#define STORAGE_WRITE_DEADLINE_MS 20000U')):
            self.assertIn(before, new)
            self.assertFalse(safety_protected_source_equal(old, new.replace(before, after)))

    def test_actual_ata_transition_flush(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from measure_cpp_baseline import suppress_windows_test_dialogs
        from test_reist_probe_domain import function
        suppress_windows_test_dialogs()
        evidence = ROOT / 'build/codex-agent/r342-fat32-write' / ('admin-host-' + uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        extracts = []
        for path, signatures in (
            ('kernel/init/storage_service.c', ('bool storage_service_resource_available(',
                'bool storage_service_resource_read_only(', 'bool storage_service_admin_flush_allowed(')),
            ('kernel/init/storage_safety.c', ('static bool storage_write_begin_admitted(',
                'bool storage_write_begin(', 'bool storage_admin_flush_begin(', 'bool storage_admin_flush_current(')),
            ('kernel/init/admin_maintenance.c', ('static int admin_flush_check(', 'static int flush_resources(')),
            ('drivers/block/ata.c', ('static int ata_admin_flush_check(', 'int ata_admin_flush_checked(')),
        ):
            source = self.read(path)
            extracts.extend(function(source, signature) for signature in signatures)
        (evidence / 'admin-under-test.h').write_text('\n'.join(extracts), encoding='utf-8')
        compiler = shutil.which('gcc') or shutil.which('clang')
        self.assertIsNotNone(compiler)
        for opt in ('-O0', '-O2'):
            binary = evidence / (opt[1:] + '.exe')
            for command, limit in (([compiler, '-std=c11', opt, '-Wall', '-Wextra', '-Werror',
                '-I', str(evidence), str(ROOT / 'test/admin_maintenance_transition_host.c'), '-o', str(binary)], 90),
                ([str(binary)], 30)):
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=limit,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                with (evidence / 'result.log').open('a', encoding='utf-8') as log:
                    log.write(repr(command) + '\n' + result.stdout + result.stderr)
                self.assertEqual(result.returncode, 0, str(evidence) + '\n' + result.stdout + result.stderr)
                if limit == 30: print(opt, result.stdout.strip(), flush=True)

    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_admin_abi_is_append_only_and_default_deny(self):
        header = self.read("include/kernel/admin_maintenance.h")
        sdk = self.read("userspace/sdk/include/x86os.h")
        process = self.read("kernel/proc/process.c")
        syscall = self.read("kernel/syscall/syscall_table.c")
        self.assertIn("ADMIN_STORAGE_SYSCALL REIST_SYS_ADMIN_STORAGE", header)
        self.assertIn("X86OS_SYS_ADMIN_STORAGE = 90", sdk)
        self.assertIn("PROCESS_DOMAIN_ADMIN", process)
        self.assertIn("SYS_ADMIN_STORAGE", process)
        self.assertIn("syscall_admin_storage", syscall)

    def test_process_canonicalizes_only_fixed_admin_tool_paths(self):
        process = self.read("kernel/proc/process.c")
        for source, canonical in (
            ("/DEVCTL.PRG", "/sbin/devctl.prg"),
            ("/MOUNT.PRG", "/sbin/mount.prg"),
            ("/UMOUNT.PRG", "/sbin/umount.prg"),
        ):
            self.assertIn(f'{{"{source}", "{canonical}"}}', process)
        self.assertIn('strcmp(resolved, "/sbin/devctl.prg") == 0', process)

    def test_root_and_parent_are_rejected_before_transition(self):
        source = self.read("kernel/init/admin_maintenance.c")
        validate = source[
            source.index("static int validate_target"):
            source.index("static int claim_transaction")
        ]
        self.assertIn("protected_root_resource_mask", validate)
        self.assertIn("ADMIN_EROOT", validate)
        self.assertNotIn("storage_service_admin_begin", validate)
        self.assertIn("control.root_resource_mask = discover_root_resource_mask()",
                      source)
        protected = source[
            source.index("static bool protected_root_resource_mask"):
            source.index("bool admin_maintenance_init")
        ]
        self.assertIn("critical_object_read(&protected_control", protected)

    def test_open_drain_is_bounded_and_revokes_after_deadline(self):
        source = self.read("kernel/init/admin_maintenance.c")
        drain = source[
            source.index("static int block_and_drain"):
            source.index("static int flush_resources")
        ]
        self.assertIn("vfs_maintenance_begin", drain)
        self.assertIn("pit_monotonic_ms", drain)
        self.assertIn("scheduler_sleep_ms", drain)
        self.assertIn("process_revoke_files_for_resource", drain)
        self.assertIn("(uint32_t)drive_count", drain)
        self.assertIn("_Static_assert(MAX_DRIVES", source)

    def test_mutation_uses_lease_and_fail_closed_storage_state(self):
        source = self.read("kernel/init/admin_maintenance.c")
        self.assertIn("storage_maintenance_acquire", source)
        self.assertIn("storage_maintenance_valid", source)
        self.assertIn("storage_maintenance_release", source)
        self.assertIn("storage_service_admin_fail", source)
        self.assertIn("storage_service_requalify_media", source)

    def test_vfs_blocks_before_unmount_and_supports_hidden_mount(self):
        header = self.read("fs/vfs/vfs.h")
        source = self.read("fs/vfs/vfs.c")
        self.assertIn("vfs_maintenance_begin", header)
        self.assertIn("vfs_maintenance_open_count", header)
        self.assertIn("vfs_mount_maintenance", header)
        open_body = source[
            source.index("static int vfs_open_locked"):
            source.index("static int vfs_close_locked")
        ]
        self.assertIn("maintenance_blocked", open_body)

    def test_admin_tools_are_built_into_system_images(self):
        programs = self.read("scripts/build_system_programs.py")
        windows = self.read("scripts/build-windows.ps1")
        makefile = self.read("Makefile")
        for host, target in (
            ("DEVCTL.PRG", "sbin/devctl.prg"),
            ("MOUNT.PRG", "sbin/mount.prg"),
            ("UMOUNT.PRG", "sbin/umount.prg"),
        ):
            self.assertIn(host, programs)
            self.assertIn(target, windows)
            self.assertIn(target, makefile)

    def test_admin_tools_are_prevalidated_and_resident_after_root_loss(self):
        process = self.read("kernel/proc/process.c")
        admin = self.read("kernel/init/admin_maintenance.c")
        self.assertIn("RESCUE_PROGRAM_CACHE_CAPACITY", process)
        self.assertIn("RESCUE_PROGRAM_CACHE_CAPACITY (224U * 1024U)", process)
        self.assertIn("RESCUE_PROGRAM_POOL_CAPACITY (448U * 1024U)", process)
        self.assertIn('"resident rescue cache"', process)
        self.assertIn('"capacity", cache->path', process)
        self.assertIn("panic_context_set_result(-28, used", process)
        self.assertIn("critical_object_read(&rescue_program_meta", process)
        self.assertIn("RESCUE_PROGRAM_POOL_CAPACITY", process)
        self.assertIn("rescue_crc32(rescue_program_pool + meta.offset", process)
        self.assertIn("/bin/shell.prg", process)
        self.assertIn("/bin/ls.prg", process)
        self.assertIn("/bin/cat.prg", process)
        self.assertIn("/sbin/devctl.prg", process)
        self.assertIn("/sbin/mount.prg", process)
        self.assertIn("/sbin/umount.prg", process)
        self.assertIn("load_program_file_uncached", process)
        self.assertIn("process_cache_rescue_programs", admin)


if __name__ == "__main__":
    unittest.main()
