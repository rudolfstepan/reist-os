"""Build an isolated BV QEMU extension from retained, hash-bound inputs.

Only three translation units are rebuilt. Retained sources, objects, binaries and
installed tools are read-only inputs. This is an incremental diagnostic build,
not a claim that the entire QEMU distribution was rebuilt from source.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PORTABLE = ROOT / "build/codex-agent/r83bs-native-math/portable-qemu"
SOURCE = PORTABLE / "qemu-ae35f033b874c627d81d51070187fbf55f0bf1a7"
BUILD = PORTABLE / "build"
ACCEPTED = ROOT / "build/codex-agent/r83bt-native-text/portable-production01"
PATCH = ROOT / "scripts/qemu_x86_64_large_file_observer.patch"
FILES = ("gdbstub/gdbstub.c", "gdbstub/system.c",
         "target/i386/whpx/whpx-all.c", "gdbstub/reist-observer.h")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def patched_sources(patch, source):
    """Apply exact line-number/context hunks; no fuzz, traversal or shell."""
    lines = patch.splitlines(keepends=True)
    result = {}
    index = 0
    while index < len(lines):
        old = lines[index].removeprefix("--- ").strip()
        if not lines[index].startswith("--- ") or index + 1 >= len(lines):
            raise ValueError("invalid patch header")
        new = lines[index + 1].removeprefix("+++ b/").strip()
        if new not in FILES or new in result or not lines[index+1].startswith("+++ b/"):
            raise ValueError("unexpected/duplicate patch path")
        if old not in ("/dev/null", "a/" + new):
            raise ValueError("invalid old path")
        before = [] if old == "/dev/null" else (source / new).read_text().splitlines(True)
        after, cursor = [], 0
        index += 2
        while index < len(lines) and lines[index].startswith("@@ "):
            match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n",
                                 lines[index])
            if not match:
                raise ValueError("invalid hunk")
            start, count, newstart, newcount = [
                int(value) if value is not None else 1 for value in match.groups()
            ]
            at = max(0, start - 1)
            if at < cursor or at > len(before):
                raise ValueError("overlapping/out-of-range hunk")
            after.extend(before[cursor:at])
            if len(after) != max(0, newstart - 1):
                raise ValueError("new hunk position")
            cursor, removed, added = at, 0, 0
            index += 1
            while index < len(lines) and lines[index][:1] in (" ", "+", "-"):
                line = lines[index]
                if line.startswith("--- "):
                    break
                if line[0] in (" ", "-"):
                    if cursor >= len(before) or before[cursor] != line[1:]:
                        raise ValueError("patch context mismatch")
                    cursor += 1
                    removed += 1
                if line[0] in (" ", "+"):
                    after.append(line[1:])
                    added += 1
                index += 1
            if (removed, added) != (count, newcount):
                raise ValueError("hunk extent mismatch")
        after.extend(before[cursor:])
        result[new] = "".join(after)
    if set(result) != set(FILES):
        raise ValueError("incomplete patch")
    return result


def build(destination):
    started = time.monotonic()
    destination = Path(destination).resolve()
    base = (ROOT / "build/codex-agent/r83bv-large-file").resolve()
    if not destination.is_relative_to(base) or destination == base:
        raise ValueError("destination must be a new BV evidence subdirectory")
    destination.mkdir(parents=True, exist_ok=False)
    receipt = {"state": "reserved", "limit": 300, "qualification": False}
    (destination / "build.json").write_text(json.dumps(receipt))
    commands = []
    env = dict(os.environ)
    env["PATH"] = str(PORTABLE / "dependencies/mingw64/bin") + os.pathsep + \
        "C:/msys64/mingw64/bin" + os.pathsep + env["PATH"]

    def remaining():
        value = 295 - (time.monotonic() - started)
        if value <= 0:
            raise TimeoutError("build lease exhausted")
        return value

    def sha(path):
        remaining()
        value = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        remaining()
        return value

    def run(command):
        commands.append(command)
        timeout = remaining()
        # Windows taskkill on the owned PID handles compiler/linker descendants.
        with (destination / "build.log").open("ab") as output:
            process = subprocess.Popen(command, cwd=BUILD, env=env,
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=4, check=True)
                process.wait(timeout=1)
                raise
            if code:
                raise RuntimeError(f"command failed ({code}): {command[0]}")

    try:
        binding_path = ACCEPTED / "binary-binding01.json"
        binding = json.loads(binding_path.read_text())
        if sha(binding["executable"]) != binding["sha256"]:
            raise ValueError("accepted binary changed")
        if (SOURCE / "target/i386/whpx/whpx-all.c").read_bytes() != \
                (ACCEPTED / "whpx-all-after.c").read_bytes():
            raise ValueError("accepted WHPX source changed")
        patched = patched_sources(PATCH.read_text(), SOURCE)
        staged = destination / "source"
        for name, content in patched.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        compilation = json.loads((BUILD / "compile_commands.json").read_text())
        replacements, compile_commands = {}, []
        for name in FILES[:3]:
            matches = [entry for entry in compilation
                       if entry["file"].endswith("/" + name) and
                       (entry["output"].startswith("gdbstub/libgdb_system.a.p/")
                        if name.startswith("gdbstub/") else
                        entry["output"].startswith("libqemu-x86_64-softmmu.a.p/"))]
            if len(matches) != 1:
                raise ValueError("ambiguous compile command")
            entry = matches[0]
            args = shlex.split(entry["command"])
            if args[0] != "cc":
                raise ValueError("unexpected compiler")
            args[0] = "C:/msys64/mingw64/bin/gcc.exe"
            obj = destination / (Path(name).name + ".obj")
            for flag, value in (("-o", str(obj)), ("-MF", str(obj)+".d"),
                                ("-MQ", str(obj))):
                args[args.index(flag)+1] = value
            if args[-1] != entry["file"]:
                raise ValueError("unexpected source operand")
            args[-1] = str(staged / name)
            # Retain sibling-header lookup after relocating this source file.
            # All original source/header inputs are bound below.
            args[1:1] = ["-iquote", str((SOURCE / name).parent)]
            replacements[entry["output"]] = str(obj)
            compile_commands.append(args)
        ninja = (BUILD / "build.ninja").read_text().splitlines()
        i = next(i for i, line in enumerate(ninja)
                 if line.startswith("build qemu-system-x86_64.exe: c_LINKER_RSP "))
        operands = ninja[i].split(": c_LINKER_RSP ", 1)[1].split(" | ", 1)[0].split()
        if any("$" in item for item in operands):
            raise ValueError("unsupported ninja input escape")
        if not ninja[i+1].startswith(" LINK_ARGS = "):
            raise ValueError("missing link arguments")
        link_args = shlex.split(ninja[i+1].split(" = ", 1)[1])
        response_inputs = {}
        for flag in link_args:
            if flag.startswith("@"):
                if flag not in ("@block.syms", "@qemu.syms") or (BUILD / flag[1:]).read_bytes():
                    raise ValueError("unexpected/nonempty nested response file")
                response_inputs[str(BUILD / flag[1:])] = sha(BUILD / flag[1:])
        link_args = [flag for flag in link_args if not flag.startswith("@")]
        inputs = {str(BUILD / item): sha(BUILD / item) for item in operands}
        inputs.update(response_inputs)
        for item in link_args:
            path = Path(item)
            if not path.is_absolute():
                path = BUILD / path
            if path.is_file():
                inputs[str(path)] = sha(path)
        for path in [PATCH, binding_path, BUILD / "compile_commands.json",
                     BUILD / "build.ninja", Path(__file__),
                     Path("C:/msys64/mingw64/bin/gcc.exe"),
                     Path("C:/msys64/mingw64/bin/ld.exe")]:
            inputs[str(path)] = sha(path)
        # Bind all source/header and generated header inputs of the incremental build.
        for tree, suffixes in ((SOURCE, {".c", ".h", ".inc"}), (BUILD, {".h"})):
            for path in tree.rglob("*"):
                remaining()
                if path.is_file() and path.suffix in suffixes:
                    inputs[str(path)] = sha(path)
        (destination / "inputs.json").write_text(json.dumps(inputs, indent=2))
        (destination / "observer-builder.py").write_bytes(Path(__file__).read_bytes())
        if sha(destination / "observer-builder.py") != inputs[str(Path(__file__))]:
            raise ValueError("builder snapshot mismatch")
        runtime = destination / "runtime"
        shutil.copytree(ACCEPTED / "runtime", runtime)
        executable = runtime / "qemu-system-x86_64.exe"
        args = ["-o", str(executable)] + [replacements.get(item, item) for item in operands] + link_args
        response = destination / "link.rsp"
        response.write_text("\n".join('"' + value.replace("\\", "/").replace('"', '\\"') + '"'
                                     for value in args), encoding="utf-8")
        for command in compile_commands:
            run(command)
        run(["C:/msys64/mingw64/bin/gcc.exe", "-m64", "@" + str(response)])
        for path, digest in inputs.items():
            if sha(path) != digest:
                raise ValueError("retained input changed during build: " + path)
        for name, entry in binding["dlls"].items():
            if sha(runtime / name) != entry["sha256"]:
                raise ValueError("runtime DLL mismatch")
        binding.update(executable=str(executable), sha256=sha(executable),
                       observer_version=1, observer_patch=sha(PATCH),
                       observer_inputs=sha(destination / "inputs.json"),
                       observer_sources={name: sha(staged/name) for name in FILES},
                       observer_commands=commands, qualification=False)
        (destination / "binary-binding.json").write_text(json.dumps(binding, indent=2))
        remaining()
        receipt.update(state="finished", result=0)
    except BaseException as error:
        receipt.update(state="finished", result=1, error=str(error))
        raise
    finally:
        receipt.update(elapsed=time.monotonic()-started, commands=commands)
        (destination / "build.json").write_text(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(args.output)
