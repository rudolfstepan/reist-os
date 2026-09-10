"""R3.42 actual native boundaries; the complete package also requires guest gates."""
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from measure_cpp_baseline import suppress_windows_test_dialogs
from test_reist_probe_domain import function


class Fat32WritableObjectTests(unittest.TestCase):
    def test_performance_authenticates_real_packaged_benchmark(self):
        import hashlib
        from unittest.mock import patch
        import run_qemu_fat32_write_performance as perf
        from create_native_boot_image import write_fat32_volume
        before, after = Path("accepted.img"), Path("candidate.img")
        payload = b"protected benchmark executable"
        evidence = ROOT / "build/codex-agent/r342-fat32-write" / ("benchmark-path-" + uuid.uuid4().hex)
        evidence.mkdir()
        fixture = evidence / "fixture.img"
        with fixture.open("w+b") as disk:
            disk.truncate((8192 + 70000)*512)
            write_fat32_volume(disk, 8192, 70000, 0x342, {"usr/bin/benchmark.prg": payload})
        with self.assertRaisesRegex(ValueError, "missing image entry"):
            perf.read_fat_file(fixture, "usr/bin/benchmark.prg")
        self.assertEqual(perf.benchmark_digest(fixture, fixture), hashlib.sha256(payload).hexdigest())
        with patch.object(perf, "read_fat_file", return_value=payload) as read:
            self.assertEqual(perf.benchmark_digest(before, after), hashlib.sha256(payload).hexdigest())
            self.assertEqual(read.call_args_list, [((before, "usr/bin/benchm~1.prg"),), ((after, "usr/bin/benchm~1.prg"),)])
        for values in ((payload, b"changed"), (b"", b"")):
            with self.subTest(values=values), patch.object(perf, "read_fat_file", side_effect=values), self.assertRaises(ValueError):
                perf.benchmark_digest(before, after)
        for path in ("Makefile", "scripts/build-windows.ps1"):
            self.assertIn("usr/bin/benchmark.prg", (ROOT / path).read_text(encoding="utf-8"))

    def test_exhaust_root_observer_stays_in_original_process(self):
        import run_qemu_fat32_writable_objects as guest
        source = (ROOT / "userspace/programs/fwritest.c").read_text(encoding="utf-8")
        normal = guest.private_client_source(source)
        exhaust = guest.private_client_source(source, exhaust=True)
        self.assertNotIn("R342_PRIVATE_ROOT_WAIT", normal)
        self.assertIn("R342_PRIVATE_ROOT_WAIT", exhaust)
        self.assertIn("if(result && r342_wait_root())", exhaust)
        wait = function(exhaust, "static int r342_wait_root(")
        self.assertIn("x86os_read(0,&key,1)", wait)
        self.assertIn("now-start>=5000", wait)
        self.assertIn("x86os_sleep_ms(1)", wait)
        self.assertIn("? r342_root_read() : -22", wait)
        for forbidden in ("spawn", "component_control", "admin_storage", "storage_submit"):
            self.assertNotIn(forbidden, wait)
        with self.assertRaises(ValueError): guest.private_client_source(exhaust, exhaust=True)

    def test_independent_root_read_is_bounded_and_closes(self):
        import run_qemu_fat32_writable_objects as guest
        suppress_windows_test_dialogs()
        private = guest.private_client_source((ROOT / "userspace/programs/fwritest.c").read_text(encoding="utf-8"))
        body = function(private, "static int r342_root_read(")
        self.assertIn('x86os_open_flags("/htdocs/hello.js",X86OS_O_RDONLY)', body)
        self.assertNotIn("reist_vfs_file_", body)
        self.assertNotIn("storage_", body)
        evidence = guest.ALLOWED / ("rescue-root-" + uuid.uuid4().hex)
        evidence.mkdir()
        fixture = evidence / "root.c"
        fixture.write_text('''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define X86OS_O_RDONLY 0U
#define X86OS_O_NOFOLLOW 0x20000U
static unsigned mode, offset, reads, closes, emitted;
static const char data[]="independent root bytes\\n";
static char output[1024];
static int x86os_monotonic_ms(uint64_t* now) {
    *now=10+(mode==5 && reads ? 5000U : 0U);
    return mode==6 ? -5 : 0;
}
static int x86os_open_flags(const char* path, uint32_t flags) {
    return mode==2 || strcmp(path,"/htdocs/hello.js") || flags!=X86OS_O_RDONLY ? -2 : 7;
}
static int x86os_read(int fd, void* dst, size_t size) {
    ++reads;
    if(fd!=7 || mode==3)return -5;
    if(mode==7)return (int)size+1;
    if(mode==8){memset(dst,'x',size);return (int)size;}
    unsigned n=(unsigned)sizeof(data)-1-offset;
    if(n>size)n=(unsigned)size;
    if(mode==1 && n)n=1;
    memcpy(dst,data+offset,n);offset+=n;return (int)n;
}
static int x86os_close(int fd) {++closes;return fd!=7 || mode==4 ? -5 : 0;}
static void x86os_putchar(char ch){if(emitted<sizeof(output)-1)output[emitted++]=ch;}
static void x86os_puts(const char* text){while(*text)x86os_putchar(*text++);}
''' + body + '''
int main(void) {
    for(mode=0;mode<9;++mode){
        offset=reads=closes=emitted=0;memset(output,0,sizeof(output));
        int result=r342_root_read();
        if((result==0)!=(mode<2))return 10+(int)mode;
        if(closes!=(mode==2 || mode==6 ? 0U : 1U))return 30+(int)mode;
        if(mode<2 && (strncmp(output,data,sizeof(data)-1) || !strstr(output,"R342_PRIVATE_ROOT_READ_OK")))return 50+(int)mode;
        if(mode>=2 && emitted)return 70+(int)mode;
        if(reads>513)return 90;
    }
    return 0;
}
''', encoding="utf-8")
        for opt in ("-O0", "-O2"):
            executable = evidence / (opt[1:] + ".exe")
            for index, command in enumerate((["gcc", "-std=c11", opt, "-Wall", "-Wextra", "-Werror", str(fixture), "-o", str(executable)], [str(executable)])):
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90 if not index else 30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                (evidence / f"{opt}-{index}.log").write_text(result.stdout+result.stderr, encoding="utf-8")
                self.assertEqual(result.returncode, 0, str(evidence)+result.stderr)

    def test_quarantine_inside_complete_failure_receipt(self):
        import run_qemu_fat32_writable_objects as guest
        locate = getattr(guest, "object_line_position", guest.handoff.handoff_line_position)
        marker = "REIST_STORAGE RESOURCE_QUARANTINED 1"
        receipt = "FWRITE FAIL stage=2 result=-22"
        for newline in ("\n", "\r\n"):
            for retired in ("", "REIST_STORAGE SERVICE_RETIRED pid=2 generation=1" + newline):
                for split in range(1, len(receipt)):
                    raw = "boot" + newline + receipt[:split] + marker + newline + retired + receipt[split:] + newline
                    position = raw.index(marker)
                    with self.subTest(split=split, newline=newline, retired=bool(retired)):
                        self.assertEqual(locate(raw, marker), position)
                        self.assertEqual(locate(raw, marker, position), -1)
                        self.assertEqual(locate(raw[:-len(newline)], marker), -1)
        actual = ("FWRITE FAIL stage=2 res" + marker + "\n"
                  "REIST_STORAGE SERVICE_RETIRED pid=2 generation=1\nult=-22\n")
        for bad in (actual.replace("stage=2", "stage=8"), actual.replace("ult=-22", "ult=0"),
                    actual.replace("pid=2", "pid=0"), actual.replace("pid=2", "pid=2147483648"),
                    actual.replace("generation=1", "generation=4294967296"),
                    actual.replace(marker, marker+"0"), "quoted " + actual,
                    actual.replace("ult=-22", "ult=-2147483649")):
            with self.subTest(bad=bad): self.assertEqual(locate(bad, marker), -1)
        source = (ROOT / "scripts/run_qemu_fat32_writable_objects.py").read_text(encoding="utf-8")
        self.assertIn("= object_line_position,handoff.guard_failure_marker,object_keys", source)
        for receipt in ("R342_PRIVATE_STALE_REJECTED", "R342_PRIVATE_STALE_ACCEPTED"):
            for newline in ("\n", "\r\n"):
                for split in range(1, len(receipt)):
                    raw = receipt[:split] + marker + newline
                    raw += "REIST_STORAGE SERVICE_RETIRED pid=2 generation=1" + newline
                    raw += receipt[split:] + newline
                    with self.subTest(receipt=receipt, split=split, newline=newline):
                        self.assertEqual(locate(raw, marker), split)
                        self.assertEqual(locate(raw, receipt), 0)
                        self.assertEqual(locate(raw, receipt, 0), -1)
                        self.assertEqual(locate(raw, receipt + "x"), -1)
                        self.assertEqual(locate("quoted " + raw, receipt), -1)

    def test_hang_fault_witness_excludes_boot_but_not_operation_faults(self):
        import run_qemu_fat32_writable_objects as guest
        prefix = "*** USER PROCESS EXCEPTION ***\nException: Invalid Opcode (IRQ 6)\n"
        prefix += "REIST_PROBE CRASH_DETECTED\nREIST_PROBE CRASH_RECOVERED\n"
        boundary = len(prefix)
        normal = prefix + guest.smoke.SHELL_PROMPT + "\nFWRITE FAIL\n"
        guest.validate_hang_interval(normal, boundary)
        for fault in ("*** USER PROCESS EXCEPTION ***", "*** USER PROCESS PAGE FAULT ***", "Exception: Invalid Opcode (IRQ 6)",
                      "Exception: Page Fault", "Exception: General Protection"):
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                guest.validate_hang_interval(normal + fault + "\n", boundary)
        for start in (-1, len(normal), boundary + 1, 0):
            with self.subTest(start=start), self.assertRaises(ValueError):
                guest.validate_hang_interval(normal, start)
        source = (ROOT / "scripts/run_qemu_fat32_writable_objects.py").read_text(encoding="utf-8")
        case = source[source.index("def run_case("):source.index("def archive_closed_private_image(")]
        self.assertIn("validate_hang_interval(guest.text(), before)", case)
        self.assertIn("validate_hang_interval(raw, before)", case)

    def test_all_private_variants_compile_freestanding(self):
        import os
        import run_qemu_fat32_writable_objects as guest
        from build_user_program import find_zig, freestanding_compile_prefix
        suppress_windows_test_dialogs()
        evidence = guest.ALLOWED / ("private-compile-" + uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        original = ROOT / "userspace/programs/storage_service.c"
        source = original.read_text(encoding="utf-8")
        environment = os.environ.copy()
        environment["ZIG_GLOBAL_CACHE_DIR"] = str(ROOT / "build/zig-global-cache/zig-global")
        environment["ZIG_LOCAL_CACHE_DIR"] = str(evidence / "zig-local")
        prefix = freestanding_compile_prefix(find_zig(), [ROOT / "userspace/storage/include", ROOT])
        records = []
        for mode in range(len(guest.CASES)):
            generated = evidence / f"storage-{mode}.c"
            generated.write_text(guest.private_source(source, mode), encoding="utf-8")
            command = [*prefix, "-std=c11", "-fno-inline-functions", "-fno-unroll-loops",
                "-falign-functions=1", "-ffunction-sections", "-fdata-sections", "-iquote",
                str(original.parent), "-c", str(generated), "-o", str(evidence / f"storage-{mode}.o")]
            start = time.monotonic()
            result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True,
                timeout=90, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            records.append(dict(mode=mode, command=command, returncode=result.returncode,
                elapsed_seconds=time.monotonic()-start, stdout=result.stdout, stderr=result.stderr))
            (evidence / "result.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
            self.assertEqual(result.returncode, 0, str(evidence) + "\n" + result.stderr)

    def test_closed_image_archive_is_scoped_and_after_vm_stop(self):
        import run_qemu_fat32_writable_objects as guest
        from unittest.mock import patch
        for path in (ROOT / "build/reist-os.img", guest.ALLOWED,
                     guest.ALLOWED / "normal-fat32.img", guest.ALLOWED / "private-7.img"):
            with self.assertRaises(ValueError): guest.archive_closed_private_image(path)
        evidence = guest.ALLOWED / ("archive-test-" + uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        image = evidence / "private-0.img"
        image.write_bytes(b"closed diagnostic image")
        with patch.object(guest.os, "name", "nt"), patch.object(guest.subprocess, "run") as run:
            run.return_value.stdout = b"archived"; run.return_value.stderr = b""
            guest.archive_closed_private_image(image)
            self.assertEqual(run.call_args.args[0], ["compact.exe", "/C", "/I", "/Q", str(image.resolve())])
            self.assertEqual(run.call_args.kwargs["timeout"], 30)
            run.return_value.check_returncode.assert_called_once()
        for name in guest.CASES:
            for suffix in ("fat32", "expected"):
                closed = evidence / f"{name}-{suffix}.img"
                original = b"closed complete observed/oracle bytes"
                closed.write_bytes(original)
                with patch.object(guest.os, "name", "nt"), patch.object(guest.subprocess, "run") as run:
                    run.return_value.stdout = b"archived"; run.return_value.stderr = b""
                    guest.archive_closed_private_image(closed, case_media=True)
                    self.assertEqual(closed.read_bytes(), original)
                    run.return_value.check_returncode.assert_called_once()
                with self.assertRaises(ValueError): guest.archive_closed_private_image(closed)
        with self.assertRaises(ValueError): guest.archive_closed_private_image(image, case_media=True)
        source = (ROOT / "scripts/run_qemu_fat32_writable_objects.py").read_text(encoding="utf-8")
        main = source[source.index("def main():"):]
        self.assertLess(main.index("result = run_case("), main.index("archive_closed_private_image(private)"))
        self.assertIn("raw = guest.close()", source[:source.index("def archive_closed_private_image(")])

    def test_journal_admission_single_snapshot(self):
        self.native("journal-probe", "R342_JOURNAL_PROBE_TEST", [], "R342 journal-probe checks")

    def test_cluster_rounding_extremes(self):
        suppress_windows_test_dialogs()
        evidence = ROOT / "build/codex-agent/r342-fat32-write" / ("rounding-"+uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        source = (ROOT / "userspace/storage/lib/fat32_file_write.c").read_text(encoding="utf-8")
        fixture = evidence / "rounding.c"
        fixture.write_text("#include <stdint.h>\n"+function(source,"static uint32_t file_cluster_count(")+"""
int main(void) {
    for (uint32_t sectors=1;sectors<=128;sectors*=2) {
        uint32_t cb=sectors*512, seed=0;
        for(unsigned i=0;i<20000;++i) {
            uint32_t values[]={0,1,cb-1,cb,cb+1,UINT32_MAX,UINT32_MAX-cb,seed};
            for(unsigned j=0;j<sizeof(values)/sizeof(values[0]);++j)
                if(file_cluster_count(values[j],cb)!=((uint64_t)values[j]+cb-1)/cb)return 1;
            seed=seed*1664525U+1013904223U;
        }
    }
    return 0;
}
""",encoding="utf-8")
        records=[]
        for optimization in ("-O0","-O2"):
            exe=evidence/(optimization[1:]+".exe")
            for command,budget in ((["gcc","-std=c11",optimization,"-Wall","-Wextra","-Werror",str(fixture),"-o",str(exe)],90),([str(exe)],30)):
                started=time.monotonic()
                result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=budget,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                records.append({"command":command,"returncode":result.returncode,"elapsed_seconds":time.monotonic()-started,"stdout":result.stdout,"stderr":result.stderr})
                (evidence/"result.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
                self.assertEqual(result.returncode,0,result.stderr)

    def test_freestanding_client_has_no_implicit_libc(self):
        import os
        import re
        from build_user_program import find_zig, freestanding_compile_prefix
        suppress_windows_test_dialogs()
        evidence = ROOT / "build/codex-agent/r342-fat32-write" / ("client-freestanding-"+uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        environment = os.environ.copy()
        environment["ZIG_GLOBAL_CACHE_DIR"] = str(ROOT / "build/zig-global-cache/zig-global")
        environment["ZIG_LOCAL_CACHE_DIR"] = str(evidence / "zig-local")
        records = []
        for optimization in ("-O0","-O2"):
            assembly = evidence / (optimization[1:]+".s")
            command = [*freestanding_compile_prefix(find_zig()), optimization, "-std=c11", "-S",
                str(ROOT / "userspace/storage/lib/vfs_file_client.c"), "-o", str(assembly)]
            started = time.monotonic()
            result = subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,timeout=90,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            records.append({"command":command,"returncode":result.returncode,
                "elapsed_seconds":time.monotonic()-started,"stdout":result.stdout,"stderr":result.stderr})
            (evidence / "result.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(re.search(r"\b(?:memcpy|memmove|memset)\b",assembly.read_text(encoding="utf-8")),str(evidence))
            self.assertIn(".text.reist_vfs_write",assembly.read_text(encoding="utf-8"))

    def test_private_guest_observer_and_oracle(self):
        import tempfile
        import run_qemu_fat32_writable_objects as guest
        self.assertEqual(guest.object_keys("FWRITEST"),
            ["sendkey shift-"+ch.lower()+"\n" for ch in "FWRITEST"]+["sendkey ret\n"])
        self.assertEqual(guest.object_keys("fwritest /mnt/a_b.bin --test-data"),
            guest.handoff.handoff_keys("fwritest /mnt/a_b.bin --test-data"))
        for command in ("a"*257,"x\nquit","x\r","ä"):
            with self.assertRaises(ValueError): guest.object_keys(command)
        source = (ROOT / "userspace/programs/storage_service.c").read_text(encoding="utf-8")
        for mode in range(len(guest.CASES)):
            candidate = guest.private_source(source, mode)
            self.assertIn("R342_PRIVATE_PLAN", candidate)
            self.assertNotIn("R342_PRIVATE_", source)
            with self.assertRaises(ValueError): guest.private_source(candidate, mode)
        client = (ROOT / "userspace/programs/fwritest.c").read_text(encoding="utf-8")
        private_client = guest.private_client_source(client)
        self.assertTrue("R342_PRIVATE_PLAN_BEGIN" in private_client)
        self.assertIn("R342_PRIVATE_STALE_REJECTED", private_client)
        self.assertIn("--r342-observe", private_client)
        self.assertEqual(guest.private_stats("R342_PRIVATE_STATS "+" ".join(map(str,range(12)))+"\n"),list(range(12)))
        for text in ("", "R342_PRIVATE_STATS 1\n", "R342_PRIVATE_STATS "+"1 "*11+"-1\n",
                     "R342_PRIVATE_STATS "+"1 "*11+"4294967296\n"):
            with self.assertRaises(ValueError): guest.private_stats(text)
        for mode in (1,2,3,4,5,6):
            self.assertNotIn("x86os_puts(\"R342_PRIVATE", guest.private_source(source,mode))
        with self.assertRaises(ValueError): guest.private_client_source(private_client)
        with self.assertRaises(ValueError): guest.private_source(source+"\n    return vfs_write_finish_plan(job);", 0)
        with tempfile.TemporaryDirectory(dir=ROOT / "build/codex-agent/r342-fat32-write") as directory:
            initial = guest.fixture(Path(directory) / "test.img", 131073)
            values = [1,3,10237,131073,131073,0,0,20] + [guest.DATA+1+7*i for i in range(20)]
            oracle = guest.DiskOracle(initial)
            oracle.apply(values)
            self.assertEqual(oracle.data_progress[1],10237)
            self.assertEqual(oracle.flushes,4)
            for rank in range(20):
                sector = guest.DATA+1+rank*7
                for index in range(3 if rank==0 else 0,512):
                    self.assertEqual(oracle.raw[sector*512+index],((rank*512+index-3)*17+23)&255)
            restored = oracle.rollback()
            self.assertEqual(restored[32*512:],initial[32*512:])
            self.assertNotEqual(restored,initial) # exact retained undo and sequence matter
            for index,value in ((0,8),(1,4),(2,10238),(3,7),(4,7),(5,1),(6,21),(7,19),(8,0),(9,guest.DATA+1)):
                malformed = list(values); malformed[index]=value
                with self.subTest(index=index), self.assertRaises(ValueError): guest.DiskOracle(initial).apply(malformed)
            with self.assertRaises(ValueError): guest.plan_records("R342_PRIVATE_PLAN 1 garbage\n")
            with self.assertRaises(ValueError): guest.plan_records("FWRITE OK\n")
            self.assertEqual(guest.plan_records("R342_PRIVATE_PLAN "+" ".join(map(str,values))+"\n"),[values])
            segmented = "R342_PRIVATE_PLAN_BEGIN\n" + "".join(
                "R342_PRIVATE_VALUES "+" ".join(map(str,values[i:i+4]))+"\n" for i in range(0,len(values),4)) + "R342_PRIVATE_PLAN_END\n"
            self.assertEqual(guest.plan_records(segmented),[values])
            for broken in (segmented.replace("R342_PRIVATE_PLAN_END", ""),
                           "R342_PRIVATE_PLAN_END\n", "R342_PRIVATE_VALUES 1\n",
                           "R342_PRIVATE_PLAN_BEGIN\n"+segmented):
                with self.assertRaises(ValueError): guest.plan_records(broken)

    def test_artifact_payload_exceptions_are_exact(self):
        from verify_fat32_write_artifacts import validate_program_sets, BASELINE_ACCEPTANCE, CONSUMERS, RESCUE_FILES, validate_rescue_sizes
        from verify_fat32_write_artifacts import INDIRECT_CONSUMERS, AUDIO_SOURCES, validate_audio_sources, validate_consumer_source
        self.assertEqual(CONSUMERS, frozenset(name + ".PRG" for name in (
            "JS", "JSRUNTST", "CAT", "CHKDSK", "BASIC", "DESKTOP", "NOTEPAD", "BROWSER",
            "IMAGEVIEWER", "CONTROL", "MOUSE", "DISPLAY", "COPY", "HTTPD", "EDIT", "GTEST", "OBJGDTST",
            "WAVPLAY", "SOUNDPLAYER")))
        self.assertEqual(INDIRECT_CONSUMERS, {"WAVPLAY.PRG", "SOUNDPLAYER.PRG"})
        validate_audio_sources(list(AUDIO_SOURCES))
        for paths in ([], list(AUDIO_SOURCES)*2, list(AUDIO_SOURCES)+["foreign.c"]):
            with self.assertRaises(ValueError): validate_audio_sources(paths)
        for path in AUDIO_SOURCES | {"scripts/build_user_sdk.py"}:
            validate_consumer_source(path, "old\r\n", "old\n")
            if path.endswith("vfs_file_client.c"): continue
            with self.subTest(path=path), self.assertRaises(ValueError): validate_consumer_source(path, "old", "new")
        baseline = json.loads(BASELINE_ACCEPTANCE.read_text(encoding="utf-8"))["archive_sources"]["programs"]
        actual = dict(baseline, **{"FWRITEST.PRG":"new"})
        self.assertEqual(validate_program_sets(baseline,actual),[])
        for name in CONSUMERS | {"STORAGE.PRG"}:
            changed = dict(actual); changed[name]="changed"
            self.assertEqual(validate_program_sets(baseline,changed),[name])
        for name in set(baseline)-CONSUMERS-{"STORAGE.PRG"}:
            changed = dict(actual); changed[name]="changed"
            with self.subTest(name=name), self.assertRaises(ValueError): validate_program_sets(baseline,changed)
        for changed in (baseline,dict(actual,**{"EXTRA.PRG":"bad"}),{k:v for k,v in actual.items() if k!="JS.PRG"}):
            with self.assertRaises(ValueError): validate_program_sets(baseline,changed)
        sizes = {name:4096 for name in RESCUE_FILES}
        self.assertEqual(validate_rescue_sizes(sizes)["total_bytes"],11*4096)
        for changed in ({},dict(sizes,**{"libexec/reist/storage.prg":224*1024+1}),
                        {name:48*1024 for name in RESCUE_FILES}):
            with self.assertRaises(ValueError): validate_rescue_sizes(changed)

    def test_fwritest_program_and_userspace_shell(self):
        import build_system_programs
        from verify_file_object_guard_artifacts import program_paths
        self.assertIn("FWRITEST.PRG", build_system_programs.PROGRAMS)
        self.assertEqual(program_paths()["FWRITEST.PRG"], "bin/fwritest.prg")
        windows = (ROOT / "scripts/build-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("'bin/fwritest.prg' = 'FWRITEST.PRG'", windows)
        program = (ROOT / "userspace/programs/fwritest.c").read_text(encoding="utf-8")
        for forbidden in ("x86os_write(", "x86os_create(", "x86os_storage_", "x86os_file_object_", "x86os_file_repair("):
            self.assertNotIn(forbidden, program)
        self.native("fwritest", "R342_PROGRAM_TEST", [], "R342 fwritest checks")

    def test_repair_guard_reservation(self):
        self.native("repair-guard", "R342_REPAIR_GUARD_TEST", "file_object_guard.c", "R342 repair-guard checks")

    def test_writable_client_receipts(self):
        self.native("write-client", "R342_WRITE_CLIENT_TEST",
                    "../../userspace/storage/lib/vfs_file_client.c", "R342 write-client checks")

    def test_service_writable_dispatch(self):
        self.native("write-service", "R342_SERVICE_TEST", [
            "file_object_guard.c", "../../userspace/storage/lib/vfs_shadow_fat32.c",
            "../../userspace/storage/lib/vfs_file_client.c",
            "../../userspace/storage/lib/fat32_file_write.c", "../../userspace/storage/lib/fat32_transaction.c",
            "../../drivers/block/ata_journal.c"], "R342 write-service checks")

    def test_owned_pin_admission(self):
        self.native("owned-pin", "R342_OWNED_PIN_TEST", "file_object_guard.c", "R342 owned-pin checks")

    def test_complete_input_transport(self):
        self.native("complete-input", "R342_INPUT_TEST", "storage_request_pool.c", "R342 complete-input checks")

    def test_input_syscall_and_sdk(self):
        self.native("input-syscall", "R342_SYSCALL_TEST", "storage_request_pool.c", "R342 syscall checks")

    def test_mutation_receipt_lifetime(self):
        self.native("mutation-receipt", "R342_RECEIPT_TEST", "storage_request_pool.c", "R342 receipt checks")

    def test_long_chain_windows(self):
        self.native("long-chain", "R342_CHAIN_TEST", "../../userspace/storage/lib/vfs_shadow_fat32.c",
                    "R342 long-chain checks")

    def test_long_read_host_deadline_and_pin(self):
        self.native("read-context", "R342_READ_CONTEXT_TEST", [], "R342 read-context checks")

    def test_allocation_ownership_windows(self):
        self.native("ownership", "R342_OWNERSHIP_TEST", [
            "../../userspace/storage/lib/vfs_shadow_fat32.c",
            "../../userspace/storage/lib/fat32_file_write.c",
            "../../userspace/storage/lib/fat32_transaction.c",
            "../../drivers/block/ata_journal.c"], "R342 ownership checks")

    def test_owned_overwrite_planner(self):
        self.native("overwrite", "R342_OVERWRITE_TEST", [
            "file_object_guard.c",
            "../../userspace/storage/lib/vfs_shadow_fat32.c",
            "../../userspace/storage/lib/fat32_file_write.c",
            "../../userspace/storage/lib/fat32_transaction.c",
            "../../drivers/block/ata_journal.c"], "R342 overwrite checks")

    def native(self, label, define, source, marker):
        suppress_windows_test_dialogs()
        evidence = ROOT / "build/codex-agent/r342-fat32-write" / (label + "-" + uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        if define == "R342_JOURNAL_PROBE_TEST":
            text = (ROOT / "fs/vfs/vfs.c").read_text(encoding="utf-8")
            (evidence / "journal_admission.inc").write_text("\n".join(function(text, signature) for signature in (
                "static int vfs_journal_authorize_context(", "int vfs_storage_journal_authorized(")), encoding="utf-8")
        if define == "R342_READ_CONTEXT_TEST":
            text = (ROOT / "userspace/programs/storage_service.c").read_text(encoding="utf-8")
            (evidence / "read_context.inc").write_text("\n".join(function(text, signature) for signature in (
                "static int vfs_object_read_clock(", "static int vfs_object_read_progress(",
                "static int vfs_object_read_info(", "static int vfs_object_read_sector(")), encoding="utf-8")
        if define == "R342_PROGRAM_TEST":
            import re
            shell = (ROOT / "userspace/bin/shell.c").read_text(encoding="utf-8")
            globals_text = "\n".join(re.search(r"^#define " + name + r" .*", shell, re.M).group(0)
                for name in ("SHELL_PATH_CAPACITY", "SHELL_MAX_ARGUMENTS", "SHELL_MAX_PATH_ENTRIES"))
            globals_text += "\n" + shell[shell.index("static char search_paths["):shell.index("static unsigned search_path_count")]
            globals_text += re.search(r"static unsigned search_path_count.*;", shell).group(0) + "\n"
            (evidence / "fwritest_shell.inc").write_text(globals_text + "\n".join(function(shell, name) for name in (
                "static unsigned text_length(", "static char lower(", "static int text_equal(",
                "static int copy_text(", "static int join_program_path(", "static int executable_file(",
                "static int explicit_program_path(", "static int has_program_extension(",
                "static const char* program_alias(", "static const char* resident_program_path(",
                "static void run_program(")), encoding="utf-8")
        if define == "R342_SERVICE_TEST":
            text = (ROOT / "userspace/programs/storage_service.c").read_text(encoding="utf-8")
            objects = text[text.index("#define VFS_OBJECT_CAPACITY"):text.index("static int vfs_ext2_object_stat(")]
            host = text[text.index("/* R3.42 writable object host."):text.index("static int vfs_symlink_reserved_zero(")]
            recovery = text[text.index("/* R3.42 repair host."):text.index("int main(void)")]
            (evidence / "write_service.inc").write_text(objects + host + recovery, encoding="utf-8")
        if define == "R342_WRITE_CLIENT_TEST":
            text = (ROOT / "userspace/programs/storage_service.c").read_text(encoding="utf-8")
            (evidence / "write_service_validator.inc").write_text("\n".join(
                function(text, signature) for signature in (
                    "static int vfs_object_reserved_zero(", "static int vfs_write_frame_valid(")), encoding="utf-8")
        if define == "R342_SYSCALL_TEST":
            text = (ROOT / "kernel/syscall/syscall_table.c").read_text(encoding="utf-8")
            extracted = "\n".join(function(text, signature) for signature in (
                "static int syscall_storage_submit(", "static int syscall_storage_claim_identity_v3(",
                "static int syscall_storage_bulk("))
            (evidence / "input_syscalls.inc").write_text(extracted, encoding="utf-8")
        results = []
        for optimization in ("-O0", "-O2"):
            executable = evidence / (optimization[1:] + ".exe")
            commands = [
                ["gcc", "-std=c11", optimization, "-Wall", "-Wextra", "-Werror",
                 "-DREIST_HOST_TEST", "-D" + define, "-I", str(ROOT), "-I", str(evidence),
                 "-I", str(ROOT / "userspace/sdk/include"),
                 "-I", str(ROOT / "userspace/storage/include"),
                 str(ROOT / ("test/test_vfs_file_client_host.c" if define == "R342_WRITE_CLIENT_TEST"
                             else "test/fat32_writable_objects_host.c")),
                 *[str(ROOT / "kernel/init" / path) for path in (source if isinstance(source, list) else [source])],
                 str(ROOT / "kernel/init/critical_object.c"), "-o", str(executable)],
                [str(executable)],
            ]
            for index, command in enumerate(commands):
                started = time.monotonic()
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                        timeout=90 if index == 0 else 30,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                record = {"command": command, "returncode": result.returncode,
                          "elapsed_seconds": time.monotonic() - started,
                          "stdout": result.stdout, "stderr": result.stderr}
                results.append(record)
                (evidence / "result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
                self.assertEqual(result.returncode, 0, str(evidence) + "\n" + result.stdout + result.stderr)
                if index:
                    self.assertIn(marker, result.stdout)
                    print(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
