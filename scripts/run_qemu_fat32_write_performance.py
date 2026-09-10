"""One authenticated R3.41/candidate benchmark pair, identical headless1024MiB settings."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
import run_qemu_benchmark as benchmark
import run_qemu_fat32_writable_objects as objects
import run_qemu_smoke as smoke
from verify_fat32_write_artifacts import BASELINE_ACCEPTANCE, BASELINE_IMAGES
from verify_text_artifacts import read_fat_file, image_program_path


def benchmark_digest(baseline, candidate):
    # The existing bounded reader uses the builder's 8.3 alias, not VFAT LFN.
    path = image_program_path("BENCHMARK.PRG")
    before = read_fat_file(baseline, path)
    after = read_fat_file(candidate, path)
    if not before or before != after:
        raise ValueError("BENCHMARK payload changed/empty")
    return hashlib.sha256(before).hexdigest()


def metrics(text):
    result = {}
    for pattern in (benchmark.CPU_ROW_PATTERN, benchmark.ROW_PATTERN):
        for match in pattern.finditer(text):
            name, value, status = (part.strip() for part in match.groups())
            if name in result: raise ValueError("duplicate benchmark row")
            if name in ("Multi CPU gesamt", "Multi/Single"):
                if (value, status) != ("-", "N/V"): raise ValueError("singleCPU contract")
                continue
            number = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?) (?:MOp/s|KiB/s)", value)
            if status != "OK" or number is None or float(number[1]) <= 0: raise ValueError("invalid result row")
            result[name] = float(number[1])
    if set(result) != {"Single CPU", "Seq. Schreiben", "Seq. Lesen"}: raise ValueError("missing benchmark rows")
    return result


def run_one(qemu, image, evidence, name, deadline):
    disk = evidence / (name+"-aux.img")
    objects.fixture(disk, 0)
    guest = objects.Guest(qemu, image, disk, evidence, name, deadline)
    started = time.monotonic()
    try:
        guest.boot()
        output = guest.execute("benchmark", (benchmark.DONE_MARKER,))
        position = -1
        # Retain strict ordered stage witnesses, including complete HDD cleanup.
        for marker in (benchmark.START_MARKER, *benchmark.EXPECTED_STATUS, benchmark.TABLE_MARKER, benchmark.DONE_MARKER):
            position = objects.handoff.handoff_line_position(output, marker, position)
            if position < 0: raise ValueError("missing/out-of-order benchmark phase: "+marker)
        guest.execute("cat /htdocs/hello.js", ("print('Hello from REIST JavaScript');",))
        return {"metrics":metrics(output),"elapsed_seconds":round(time.monotonic()-started,3),
            "host_timer_policy":guest.timer,"settings":{"memory_mib":1024,"smp":1,"accel":"tcg","nic":"none"}}
    finally: guest.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qemu",type=Path,required=True)
    parser.add_argument("--image",type=Path,required=True)
    parser.add_argument("--evidence",type=Path,required=True)
    args = parser.parse_args()
    qemu,image,evidence = args.qemu.resolve(),args.image.resolve(),args.evidence.resolve()
    allowed = objects.ALLOWED.resolve()
    if not qemu.is_file() or not image.is_file() or evidence.exists() or evidence == allowed or not evidence.is_relative_to(allowed):
        parser.error("existing qemu/image and fresh r342 evidence child required")
    evidence.mkdir(parents=True); objects.suppress_windows_test_dialogs()
    started = time.monotonic(); report = {"passed":False,"runs":{}}
    previous = smoke.exact_line_position,smoke.failure_marker,smoke.monitor_key_commands
    smoke.exact_line_position,smoke.failure_marker,smoke.monitor_key_commands = objects.handoff.handoff_line_position,objects.handoff.guard_failure_marker,objects.handoff.handoff_keys
    reference = objects.handoff.transport.file_sha256(image)
    try:
        accepted = json.loads(BASELINE_ACCEPTANCE.read_text(encoding="utf-8"))
        baseline = BASELINE_IMAGES / "reist-os.img"
        if not accepted["accepted"] or not accepted["archive_sources"]["passed"] or objects.handoff.transport.file_sha256(baseline) != accepted["archive_sources"]["images"]["qemu"]["sha256"]:
            raise ValueError("accepted baseline authentication failed")
        report["benchmark_sha256"] = benchmark_digest(baseline, image)
        report["baseline_sha256"] = objects.handoff.transport.file_sha256(baseline)
        report["candidate_sha256"] = reference
        for name,path in (("baseline",baseline),("candidate",image)):
            if time.monotonic() >= started+360: raise ValueError("pair360s deadline")
            report["runs"][name] = run_one(qemu,path,evidence,name,started+360)
        report["ratios"] = {key:report["runs"]["candidate"]["metrics"][key]/value
            for key,value in report["runs"]["baseline"]["metrics"].items()}
        # A single pair is a regression signal, not a hardware/WCET claim.
        # Never rerun unchanged candidates merely to select a favorable sample.
        if any(ratio < .80 for ratio in report["ratios"].values()): raise ValueError("material throughput drop (>20%); investigation required")
        report["passed"] = True
    except (OSError,ValueError,RuntimeError,KeyError) as caught: report["error"] = str(caught)
    finally:
        smoke.exact_line_position,smoke.failure_marker,smoke.monitor_key_commands = previous
        if reference != objects.handoff.transport.file_sha256(image): report.update(passed=False,error="reference modified")
        report["elapsed_seconds"] = round(time.monotonic()-started,3)
        (evidence / "result.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("FAT32_WRITE_PERFORMANCE", "PASS" if report["passed"] else "FAIL",report.get("error",""),flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
