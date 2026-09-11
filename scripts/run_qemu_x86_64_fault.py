"""Bounded real-instruction child retirement matrix; no synthetic exceptions."""
from pathlib import Path
import argparse
import json
import re
import struct
import subprocess
import time
import uuid

from run_qemu_x86_64_boot import resolve_qemu, run_boot

ROOT = Path(__file__).resolve().parents[1]
VECTORS = (0, 3, 6, 13, 14, 16)
MARKER = "REIST_X86_64_CHILD_FAULT_REAP_OK"
RUN = "REIST_X86_64_RING3_SHELL_RUN_OK"
RECEIPT = re.compile(MARKER + r" vector=([0-9A-F]{2}) generation=([0-9A-F]{2})"
                     r" parent=([0-9A-F]{2}) queued=([0-9A-F]{2}) rip=([0-9A-F]{16})\r?\n")


def fault_address(folder: Path, vector: int) -> int:
    # Independent ELF64 symbol + linked-section mapping, not a kernel RIP rule.
    obj = (folder / "user_child.o").read_bytes()
    linked = (folder / "reist-x86_64-user-child.elf").read_bytes()

    def sections(data):
        if len(data) > 65536 or data[:6] != b"\x7fELF\x02\x01":
            raise RuntimeError("unexpected child ELF64")
        off = struct.unpack_from("<Q", data, 40)[0]
        size, count = struct.unpack_from("<HH", data, 58)
        if size != 64 or not 0 < count <= 64 or off + size * count > len(data):
            raise RuntimeError("invalid child section table")
        return [struct.unpack_from("<IIQQQQIIQQ", data, off + i * size)
                for i in range(count)]

    table = sections(obj)
    matches = []
    for section in table:
        if section[1] != 2:
            continue
        strings = table[section[6]]
        names = obj[strings[4]:strings[4] + strings[5]]
        if section[9] != 24 or section[5] % 24 or section[4] + section[5] > len(obj):
            raise RuntimeError("invalid child symbols")
        for offset in range(section[4], section[4] + section[5], 24):
            name, _, _, index, value, _ = struct.unpack_from("<IBBHQQ", obj, offset)
            if names[name:].split(b"\0", 1)[0] == b"child_fault_instruction":
                code = table[index]
                matches.append((value, obj[code[4]:code[4] + code[5]]))
    if len(matches) != 1:
        raise RuntimeError("missing unique fault instruction")
    value, code = matches[0]
    text = [s for s in sections(linked) if s[2] & 4 and s[1] == 1]
    if len(text) != 1 or text[0][5] != len(code):
        raise RuntimeError("unexpected linked child code layout")
    opcodes = {0: b"\xf7\xf0", 3: b"\xcc", 6: b"\x0f\x0b",
               13: b"\x0f\x20\xc0", 14: b"\xc6\x00\x01", 16: b"\x9b"}
    if not code[value:].startswith(opcodes[vector]) or not linked[text[0][4] + value:].startswith(opcodes[vector]):
        raise RuntimeError("fault symbol does not name the required instruction")
    return text[0][3] + value + (1 if vector == 3 else 0)


def validate_receipts(captured: str, vector: int, phase: int, rip: int) -> None:
    receipts = list(RECEIPT.finditer(captured))
    runs = list(re.finditer(RUN, captured))
    if captured.count(MARKER) != 2 or len(receipts) != 2 or len(runs) != 2:
        raise RuntimeError("expected exactly two complete fault/reap and RUN receipts")
    for index, receipt in enumerate(receipts):
        actual = tuple(int(value, 16) for value in receipt.groups())
        expected = (vector, 41 + index, (1, 1, 6, 7)[phase], int(phase == 1), rip)
        if actual != expected:
            raise RuntimeError(f"fault receipt {actual} != expected {expected}")
        lower = captured.find("REIST_X86_64_RING3_SHELL_INFO_OK") if index == 0 else runs[0].end()
        if not 0 <= lower < receipt.start() < receipt.end() <= runs[index].start():
            raise RuntimeError("fault/reap must precede each matching successful WAIT/RUN")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    if not evidence.is_relative_to(ROOT / "build/codex-agent"):
        parser.error("evidence must stay within build/codex-agent")
    attempt = evidence / ("attempt-" + uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    results = []
    started = time.monotonic()
    try:
        qemu = resolve_qemu(None)
        for vector in VECTORS:
            for phase in range(4):
                folder = attempt / f"v{vector}-p{phase}"
                folder.mkdir()
                row = dict(vector=vector, phase=phase, passed=False)
                results.append(row)
                begin = time.monotonic()
                command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-File", "scripts/build-x86_64-bootstrap.ps1", "-OutputDirectory",
                           folder.relative_to(ROOT).as_posix(), "-FaultVector", str(vector),
                           "-FaultPhase", str(phase)]
                with (folder / "build.log").open("wb") as output:
                    result = subprocess.run(command, cwd=ROOT, stdout=output,
                        stderr=subprocess.STDOUT, timeout=90,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if result.returncode:
                    raise RuntimeError(f"build failed: {folder / 'build.log'}")
                native = folder / "x86_64"
                rip = fault_address(native, vector)
                captured = run_boot(qemu, native / "reist-x86_64-bootstrap.elf",
                                    folder / "guest.log", 10.0)
                validate_receipts(captured, vector, phase, rip)
                row.update(passed=True, elapsed=round(time.monotonic() - begin, 3), rip=hex(rip))
                print(f"X86_64_FAULT_CASE_OK vector={vector} phase={phase} seconds={row['elapsed']}", flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, struct.error) as exc:
        print(f"X86_64_FAULT_MATRIX_FAIL {exc}", flush=True)
        return 1
    finally:
        (attempt / "summary.json").write_text(json.dumps(dict(results=results,
            elapsed=round(time.monotonic() - started, 3)), indent=2), encoding="utf-8")
    print(f"X86_64_FAULT_MATRIX_OK cases=24 generations=48 evidence={attempt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
