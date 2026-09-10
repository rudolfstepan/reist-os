"""R3.42 exact reference kernels/payloads and protected runtime source.

Checked PIO helpers must reduce exactly to accepted R3.41 code when the
explicit admission argument is absent. Only external journal and dedicated
admin-flush mediation are cold-body exceptions; ordinary ATA code is not
exempted wholesale. The only
permitted journal-core delta is the user-approved primary-only CLEAN attach.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))
from test_reist_probe_domain import function

BASELINE = "3e7c02add995b5c33aed045913382dc7ccce2d0f"
DIRECT_CONSUMERS = frozenset(name + ".PRG" for name in (
    "JS", "JSRUNTST", "CAT", "CHKDSK", "BASIC", "DESKTOP", "NOTEPAD", "BROWSER",
    "IMAGEVIEWER", "CONTROL", "MOUSE", "DISPLAY", "COPY", "HTTPD", "EDIT", "GTEST", "OBJGDTST"))
INDIRECT_CONSUMERS = frozenset(("WAVPLAY.PRG", "SOUNDPLAYER.PRG"))
CONSUMERS = DIRECT_CONSUMERS | INDIRECT_CONSUMERS
CLIENT_SOURCE = "userspace/storage/lib/vfs_file_client.c"
AUDIO_SOURCES = frozenset(("userspace/audio/lib/audio.c", "userspace/audio/lib/audio_wave.c",
    CLIENT_SOURCE, "userspace/storage/lib/vfs_path.c"))
BASELINE_ACCEPTANCE = ROOT / "build/codex-agent/r341-journal-handoff/accepted-final/acceptance.json"
BASELINE_IMAGES = ROOT / "build/codex-agent/r341-journal-handoff/deadline-repair/corrected-reference"
RESCUE_FILES = ("bin/shell.prg", "sbin/devctl.prg", "sbin/mount.prg", "sbin/umount.prg", "sbin/svcctl.prg",
    "libexec/reist/storage.prg", "libexec/reist/reist.prg", "sbin/drives.prg", "bin/ls.prg", "bin/cat.prg", "sbin/chkdsk.prg")


def validate_rescue_sizes(sizes):
    if set(sizes) != set(RESCUE_FILES) or any(not isinstance(n,int) or not 0 < n <= 224*1024 for n in sizes.values()):
        raise ValueError("rescue image inventory/per-image224KiB budget")
    total = sum(sizes.values())
    if total > 448*1024: raise ValueError("rescue aggregate448KiB budget")
    return {"total_bytes":total,"pool_capacity":448*1024,"per_image_capacity":224*1024,"images":sizes}


def replace_once(text, old, new=""):
    if text.count(old) != 1:
        raise ValueError("ATA admission anchor drift: " + old)
    return text.replace(old, new, 1)


def critical_protected_source_equal(old, new):
    """Only arithmetic may differ; decoding decisions and all object machinery stay exact."""
    try:
        helper="static uint8_t secded_parity("
        if helper in new:
            new=replace_once(new,function(new,helper))
        for signature,tail in (("static uint8_t secded_encode(","    bool overall ="),
                               ("static int secded_decode(","    bool overall_mismatch ="),
                               ("static uint32_t crc32_bytes(",None)):
            before,after=function(old,signature),function(new,signature)
            if tail and before[before.index(tail):].split()!=after[after.index(tail):].split(): return False
            if signature.startswith("static int") and "if ((stored & 0x80U) != 0) return -1;" not in after: return False
            old=replace_once(old,before);new=replace_once(new,after)
        return old.split()==new.split()
    except ValueError: return False


def scheduler_protected_source_equal(old, new):
    """Permit only timed local-idle wake hints and the existing post-EOI hook."""
    try:
        for signature, sleeper in (("void scheduler_wake_expired_sleepers_locked(", True),
                                   ("void scheduler_wake_expired_waiters_locked(", False)):
            before, after = function(old, signature), function(new, signature)
            restored = replace_once(after, "    uint32_t reschedule_mask = 0U;\n")
            restored = replace_once(restored,
                "    if ((reschedule_mask & (1U << scheduler_cpu_local()->cpu_index)) != 0U)\n"
                "        preemption_pending = true;\n")
            if sleeper:
                restored = replace_once(restored,
                    "wait_queue_wake_one_task_locked(&sleep_waiters, &reschedule_mask)",
                    "wait_queue_wake_one_task_locked(&sleep_waiters, NULL)")
            else:
                restored = replace_once(restored, "            reschedule_mask |= task->cpu_affinity_mask;\n")
            if restored.split() != before.split(): return False
            new = replace_once(new, after, before)
        signature = "void scheduler_pit_interrupt_handler("
        before, after = function(old, signature), function(new, signature)
        expected = '''void scheduler_pit_interrupt_handler(void) {
    uint32_t flags = irq_save();
    bool periodic = false;
    if (scheduler_uses_pit_fallback() &&
        ++pit_scheduler_ticks >= SCHEDULER_QUANTUM_MS) {
        pit_scheduler_ticks = 0;
        periodic = true;
    }
    bool wake_idle = current_task < 0 && kernel_context_saved &&
        preempt_disable_count == 0U && preemption_pending;
    if (periodic || wake_idle) scheduler_interrupt_handler();
    irq_restore(flags);
}'''
        import re
        if re.sub(r"/\*.*?\*/", "", after, flags=re.S).split() != expected.split(): return False
        new = replace_once(new, after, before)
        return old.split() == new.split()
    except ValueError: return False


def ata_protected_source_equal(old, new):
    """Require exact legacy bodies, NULL adapters and admission locations.

    The list is intentionally structural, not a digest of the candidate:
    unrelated code, a changed batch bound or even a missing authority check
    must fail. Runtime tests independently exercise the allowed callbacks.
    """
    try:
        # R3.42 approved MULTIPLE mode arithmetic/DRQ adaptation only. Remove
        # its exact wrappers and invert the parameterized cores, then apply
        # the existing strict legacy/admission reconstruction below.
        for name in ('ata_read_sectors_pio_checked','ata_write_sectors_pio_deferred_checked'):
            wrapper=function(new,'static bool '+name+'(')
            core='ata_read_sectors_pio_mode_checked' if name.startswith('ata_read') else 'ata_write_sectors_pio_mode_checked'
            last='0' if name.startswith('ata_read') else '1'
            expected=('return '+core+'(base, lba, count, buffer, is_master, deadline, admission, '+last+');')
            if wrapper[wrapper.index('{')+1:wrapper.rindex('}')].split()!=expected.split(): return False
            new=replace_once(new,wrapper)
        body=function(new,'static bool ata_read_sectors_pio_mode_checked(')
        restored=body.replace('ata_read_sectors_pio_mode_checked(', 'ata_read_sectors_pio_checked(',1)
        restored=replace_once(restored,', int mode)',')')
        restored=replace_once(restored,'    /* A supplied mode is stack-local to one continuously locked external IO.\n'
            '     * Zero keeps legacy fresh negotiation. No cross-call/device mode cache. */\n'
            '    if (mode < 0 || mode > 128 || (mode && (!admission || (mode & (mode-1))))) return false;\n')
        restored=replace_once(restored,'int block = mode ? mode : count > 1U','int block = count > 1U')
        new=replace_once(new,body,restored)
        body=function(new,'static bool ata_write_sectors_pio_mode_checked(')
        restored=body.replace('ata_write_sectors_pio_mode_checked(', 'ata_write_sectors_pio_deferred_checked(',1)
        restored=replace_once(restored,', int block)',')')
        restored=replace_once(restored,'    if (block < 1 || block > 128 || (block & (block-1)) || (block > 1 && !admission)) return false;\n')
        restored=replace_once(restored,'use_lba48, block > 1, deadline, admission','use_lba48, false, deadline, admission')
        restored=replace_once(restored,'for (uint32_t index = 0U; index < count;) {\n'
            '        uint32_t amount = count-index;\n'
            '        if (amount > (uint32_t)block) amount = (uint32_t)block;',
            'for (uint32_t index = 0U; index < count; ++index) {')
        restored=replace_once(restored,'amount * (SECTOR_SIZE / 2U));','SECTOR_SIZE / 2U);')
        restored=replace_once(restored,'        index += amount;\n')
        new=replace_once(new,body,restored)
        new=replace_once(new,'(multiple ? ATA_WRITE_MULTIPLE_EXT : ATA_WRITE_SECTORS_EXT)','ATA_WRITE_SECTORS_EXT')
        new=replace_once(new,'(multiple ? ATA_WRITE_MULTIPLE : ATA_WRITE_SECTORS)','ATA_WRITE_SECTORS')
        wrappers = (
            "static bool ata_program_pio_batch(unsigned short base, uint32_t lba,\n"
            "    uint32_t count, bool is_master, bool write, bool use_lba48, bool multiple, uint64_t deadline) {\n"
            "    return ata_program_pio_batch_checked(base, lba, count, is_master, write, use_lba48, multiple, deadline, NULL);\n}",
            "static bool ata_read_sectors_pio_until(unsigned short base, uint32_t lba,\n"
            "    uint32_t count, void* buffer, bool is_master, uint64_t deadline) {\n"
            "    return ata_read_sectors_pio_checked(base, lba, count, buffer, is_master, deadline, NULL);\n}",
            "static bool ata_flush_cache_until(unsigned short base, bool is_master,\n"
            "    const drive_t* drive, uint64_t deadline) {\n"
            "    return ata_flush_cache_checked(base, is_master, drive, deadline, NULL);\n}",
            "static bool ata_write_sectors_pio_deferred_until(unsigned short base,\n"
            "    uint32_t lba, uint32_t count, const void* buffer, bool is_master, uint64_t deadline) {\n"
            "    return ata_write_sectors_pio_deferred_checked(base, lba, count, buffer, is_master, deadline, NULL);\n}",
            "int ata_external_journal_io(uint32_t resource, uint32_t operation,\n"
            "    uint32_t sector, uint32_t count, void* buffer, bool pending, uint64_t deadline_ms) {\n"
            "    return ata_external_journal_io_checked(resource, operation, sector, count, buffer, pending, deadline_ms, NULL);\n}",
            "int ata_external_journal_io_checked(uint32_t resource, uint32_t operation,\n"
            "    uint32_t sector, uint32_t count, void* buffer, bool pending, uint64_t deadline_ms,\n"
            "    ata_journal_admission_t* admission) {\n"
            "    return ata_external_journal_transport(resource, operation, sector, count, buffer, pending, deadline_ms, admission, false);\n}",
            "int ata_repair_journal_io_checked(uint32_t resource, uint32_t operation,\n"
            "    uint32_t sector, uint32_t count, void* buffer, bool pending, uint64_t deadline_ms,\n"
            "    ata_journal_admission_t* admission) {\n"
            "    return ata_external_journal_transport(resource, operation, sector, count, buffer, pending, deadline_ms, admission, true);\n}",
        )
        for wrapper in wrappers:
            new = replace_once(new, wrapper)
        # These five transformations are the complete permitted delta in the
        # existing PIO path. Removing them must reconstruct the accepted code.
        for stem, original, checks in (
            ("static int ata_pio_read_block_size", "ata_pio_read_block_size", (3, 0)),
            ("static bool ata_program_pio_batch", "ata_program_pio_batch", (0, 0)),
            ("static bool ata_read_sectors_pio", "ata_read_sectors_pio_until", (2, 0)),
            ("static bool ata_write_sectors_pio_deferred", "ata_write_sectors_pio_deferred_until", (1, 0)),
            ("static bool ata_flush_cache", "ata_flush_cache_until", (0, 1)),
        ):
            signature = stem + "_checked("
            if new.count(signature) != 1:
                return False
            body = function(new, signature)
            restored = replace_once(body, signature, stem.rsplit(" ", 1)[0] + " " + original + "(")
            # Normalize layout only for the parameter which is being removed.
            import re
            restored, removed = re.subn(r",\s*ata_journal_admission_t\* admission", "", restored)
            if removed != 1:
                return False
            for effect, expected in (("false", checks[0]), ("true", checks[1])):
                statement = "if (!ata_journal_check(admission, " + effect + ")) return " + ("-1" if stem.startswith("static int") else "false") + ";"
                if restored.count(statement) != expected:
                    return False
                restored = restored.replace(statement, "")
            if original == "ata_program_pio_batch":
                restored = replace_once(restored, "if (!ata_journal_check(admission, write)) return false;")
            if original == "ata_read_sectors_pio_until":
                restored = replace_once(restored, "ata_pio_read_block_size_checked(base, is_master, deadline, admission)",
                                        "ata_pio_read_block_size(base, is_master, deadline)")
            if original in ("ata_read_sectors_pio_until", "ata_write_sectors_pio_deferred_until"):
                restored = replace_once(restored, "ata_program_pio_batch_checked(", "ata_program_pio_batch(")
                restored = replace_once(restored, "deadline, admission))", "deadline))")
            new = replace_once(new, body, restored)
        # Cold external admission/supervision code, not an ordinary IO waiver.
        new = replace_once(new, "typedef struct {\n    ata_journal_admission_t* owner;\n"
            "    uint32_t resource;\n    bool supervised;\n    bool repair;\n} ata_external_command_t;")
        for signature in ("static int ata_external_command_check(", "static int ata_external_journal_transport(",
                          "static int ata_admin_flush_check(", "int ata_admin_flush_checked("):
            if new.count(signature) != 1:
                return False
            new = replace_once(new, function(new, signature))
        signature = "int ata_external_journal_io("
        if old.count(signature) != 1:
            return False
        old = replace_once(old, function(old, signature))
        return old.split() == new.split()
    except (ValueError, IndexError):
        return False


def safety_protected_source_equal(old, new):
    """Reconstruct the exact ordinary write path; only private flush admission is new."""
    try:
        wrapper = function(new, "bool storage_write_begin(")
        original = function(old, "bool storage_write_begin(")
        common = function(new, "static bool storage_write_begin_admitted(")
        opening = common.index("    storage_control_t state;")
        restored = "bool storage_write_begin(uint32_t resource, uint64_t now_ms) {\n" + common[opening:]
        admission = wrapper[wrapper.index("    if (resource"):wrapper.index("    return storage_write_begin_admitted")]
        restored = replace_once(restored, "    if (deadline_ms <= now_ms) return false;\n", admission)
        restored = replace_once(restored, "    if (deadline_ms < state.operation_deadline_ms)\n"
            "        state.operation_deadline_ms = deadline_ms;\n")
        if restored.split() != original.split(): return False
        for signature in ("bool storage_admin_flush_begin(", "bool storage_admin_flush_current("):
            new = replace_once(new, function(new, signature))
        new = replace_once(new, common)
        return replace_once(new, wrapper, original).split() == old.split()
    except (ValueError, IndexError):
        return False


def journal_protected_source_equal(old, new):
    """Allow only the exact primary-only repair decision, not an attach waiver.

    All record validation, v1 upgrade, ACTIVE restoration, write batching and
    flush ordering must reconstruct the accepted R3.41 source unchanged.
    Behavioral tests independently cover owned and recovery hosts.
    """
    before = (
        "    } else {\n        record = primary;\n        repair_headers = true;\n"
        "    }\n\n    if (record->version == 1U) {"
    )
    after = (
        "    } else {\n        record = primary;\n"
        "        /* A valid primary alone needs no header repair when the declared\n"
        "         * extent has no mirror. ACTIVE recovery and v1 upgrade still apply. */\n"
        "        repair_headers = mirror_lba != 0U;\n"
        "    }\n\n    if (record->version == 1U) {"
    )
    old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
    try:
        if old.count(before) != 1:
            return False
        return old.split() == replace_once(new, after, before).split()
    except ValueError:
        return False


def source_at_baseline(path):
    return subprocess.check_output(["git", "show", BASELINE + ":" + path], cwd=ROOT,
        timeout=15).decode("utf-8").replace("\r\n", "\n")


def validate_program_sets(baseline, actual):
    if len(baseline) != 93 or set(actual) != set(baseline) | {"FWRITEST.PRG"}:
        raise ValueError("expected accepted93 + exactly FWRITEST payloads")
    for name, expected in baseline.items():
        if name not in CONSUMERS | {"STORAGE.PRG"} and actual[name] != expected:
            raise ValueError("protected program changed " + name)
    return sorted(name for name in baseline if actual[name] != baseline[name])


def validate_consumer_source(path, original, candidate):
    if path != CLIENT_SOURCE and original.replace("\r\n", "\n") != candidate.replace("\r\n", "\n"):
        raise ValueError("consumer dependency source changed " + path)


def validate_audio_sources(paths):
    if len(paths) != len(AUDIO_SOURCES) or set(paths) != AUDIO_SOURCES:
        raise ValueError("indirect audio dependency inventory changed")


def main():
    from build_system_programs import PROGRAMS
    from build_user_sdk import AUDIO_LIBRARY_SOURCES
    from run_qemu_math import digest, kernel_digest
    from verify_file_object_guard_artifacts import program_paths
    from verify_text_artifacts import read_fat_file
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    allowed = (ROOT / "build/codex-agent/r342-fat32-write").resolve()
    if evidence.exists() or evidence == allowed or not evidence.is_relative_to(allowed):
        parser.error("new evidence child under r342-fat32-write required")
    evidence.mkdir(parents=True)
    report = {"passed": False, "baseline": BASELINE, "programs": {}, "images": {}, "unchanged_source": []}
    started = time.monotonic()
    try:
        accepted = json.loads(BASELINE_ACCEPTANCE.read_text(encoding="utf-8"))
        baseline = accepted["archive_sources"]
        if not accepted["accepted"] or not baseline["passed"]:
            raise ValueError("accepted R3.41 archive missing")
        report["baseline_acceptance_sha256"] = digest(BASELINE_ACCEPTANCE)
        # Verify the accepted images themselves, not an unauthenticated list of
        # favorable expected hashes. Keep historical failed records untouched.
        for target, name in (("qemu", "reist-os.img"), ("vmware", "reist-os-flat.vmdk")):
            if digest(BASELINE_IMAGES / name) != baseline["images"][target]["sha256"]:
                raise ValueError("accepted reference image changed " + target)
        paths = program_paths()
        # HELLO is the separately selected user payload, not part of the fixed
        # system map. Check it explicitly below; no unnamed registry exception.
        if set(paths) | {"HELLO.PRG"} != set(PROGRAMS): raise ValueError("program build/image registry mismatch")
        if paths.get("FWRITEST.PRG") != "bin/fwritest.prg": raise ValueError("new shell command path mismatch")
        make = (ROOT / "Makefile").read_text(encoding="utf-8")
        if "bin/fwritest.prg=$(SYSTEM_PROGRAM_DIR)/FWRITEST.PRG" not in make:
            raise ValueError("Makefile shell command missing")
        report["programs"] = {name: digest(ROOT / "build/programs" / name) for name in paths}
        report["rescue_budget"] = validate_rescue_sizes({path:(ROOT / "build/programs" / Path(path).name.upper()).stat().st_size
            for path in RESCUE_FILES})
        report["changed_programs"] = validate_program_sets(baseline["programs"], report["programs"])
        # Shared-client consumers may relink, their application sources may not
        # change. Pin all other linked sources and the browser/JS host policy.
        checked_sources = set()
        audio_paths = [source.relative_to(ROOT).as_posix() for source in AUDIO_LIBRARY_SOURCES]
        validate_audio_sources(audio_paths)
        # The two approved indirect relinks do not exempt their archive recipe,
        # audio implementation or path handling from baseline protection.
        for path in ["scripts/build_user_sdk.py", *audio_paths]:
            if path == CLIENT_SOURCE: continue
            validate_consumer_source(path, source_at_baseline(path), (ROOT / path).read_text(encoding="utf-8"))
            checked_sources.add(path)
        for name in CONSUMERS:
            sources = PROGRAMS[name] if isinstance(PROGRAMS[name], tuple) else (PROGRAMS[name],)
            for source in sources:
                path = source.relative_to(ROOT).as_posix()
                if path == CLIENT_SOURCE or path in checked_sources: continue
                validate_consumer_source(path, source_at_baseline(path), (ROOT / path).read_text(encoding="utf-8"))
                checked_sources.add(path)
        report["consumer_sources_unchanged"] = sorted(checked_sources)
        report["consumer_link_cause"] = [CLIENT_SOURCE]
        report["indirect_consumers"] = sorted(INDIRECT_CONSUMERS)
        hello = read_fat_file(BASELINE_IMAGES / "reist-os.img", "usr/bin/hello.prg")
        if hello != (ROOT / "build/programs/HELLO.PRG").read_bytes(): raise ValueError("selected HELLO payload changed")
        report["selected_hello_sha256"] = hashlib.sha256(hello).hexdigest()
        for target, image, kernel in (
            ("vmware", ROOT / "build/vmware/reist-os/reist-os-flat.vmdk", allowed / "kernel-vmware.bin"),
            ("qemu", ROOT / "build/reist-os.img", ROOT / "build/kernel.bin")):
            actual = kernel_digest(image)
            if actual != digest(kernel): raise ValueError("kernel/image mismatch " + target)
            if read_fat_file(image,"usr/bin/hello.prg") != hello: raise ValueError("selected HELLO image mismatch " + target)
            for name, expected in report["programs"].items():
                if hashlib.sha256(read_fat_file(image, paths[name])).hexdigest() != expected:
                    raise ValueError("stale packaged program " + target + "/" + name)
            report["images"][target] = {"sha256": digest(image), "kernel_sha256": actual}
        for path in ("kernel/sched/scheduler.c", "kernel/sched/scheduler.h", "arch/x86/include/cpu_local.h",
                     "kernel/proc/process.c", "drivers/char/serial.c", "drivers/block/ata.c", "drivers/block/ata_journal.c",
                     "include/kernel/critical_object.h", "kernel/init/critical_object.c", "kernel/init/storage_safety.c"):
            old, new = source_at_baseline(path), (ROOT / path).read_text(encoding="utf-8")
            match = ata_protected_source_equal(old, new) if path == "drivers/block/ata.c" else \
                journal_protected_source_equal(old, new) if path == "drivers/block/ata_journal.c" else \
                critical_protected_source_equal(old, new) if path == "kernel/init/critical_object.c" else \
                safety_protected_source_equal(old, new) if path == "kernel/init/storage_safety.c" else \
                scheduler_protected_source_equal(old, new) if path == "kernel/sched/scheduler.c" else old.split() == new.split()
            if not match: raise ValueError("protected source changed " + path)
            report["unchanged_source"].append(path)
        release = (ROOT / "build/programs/STORAGE.PRG").read_bytes()
        for marker in (b"R342_PRIVATE_", b"__r342_", b"HANDOFF_RECOVERY_COMMIT_OK", b"HANDOFF_FAILED"):
            if marker in release: raise ValueError("private fault hook in release Storage")
        report["passed"] = True
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
    report["elapsed_seconds"] = round(time.monotonic()-started, 3)
    (evidence / "protected.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("FAT32_WRITE_ARTIFACTS " + ("PASS" if report["passed"] else "FAIL: " + report["error"]), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
