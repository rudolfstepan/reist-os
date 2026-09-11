"""Negative CPU admission: no SSE2 must fail before any native user task."""
import argparse
from pathlib import Path
import subprocess
import time
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    if not args.image.is_file(): parser.error('missing image')
    if args.log.exists(): parser.error('refusing to overwrite evidence')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with args.log.open('xb') as serial:
        process = subprocess.Popen([str(resolve_qemu(None)), '-machine', 'pc,accel=tcg',
            '-cpu', 'qemu64,-sse2', '-m', '128M', '-smp', '1', '-display', 'none',
            '-monitor', 'none', '-serial', 'stdio', '-no-reboot', '-no-shutdown',
            '-kernel', str(args.image.resolve())], stdin=subprocess.DEVNULL,
            stdout=serial, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            while time.monotonic()-started < 10:
                data = args.log.read_bytes()
                if b'REIST_X86_64_FP_UNSUPPORTED' in data or process.poll() is not None: break
                time.sleep(0.02)
        finally:
            terminate_bounded(process)
            error = process.stderr.read(4096).decode(errors='replace')
            process.stderr.close()
    data = args.log.read_bytes()
    passed = data.count(b'REIST_X86_64_FP_UNSUPPORTED') == 1 and \
        b'REIST_X86_64_EXCEPTION_IDT_READY' in data and not any(x in data for x in
        (b'REIST_X86_64_FP_CPU_READY', b'REIST_X86_64_USER_EXECUTION_OK',
         b'REIST_X86_64_RING3_SHELL_READY', b'REIST_X86_64_EXCEPTION_FATAL'))
    print('X86_64_FP_ADMISSION '+('PASS' if passed else 'FAIL '+error)+
          f' elapsed={time.monotonic()-started:.3f}s')
    return 0 if passed else 1


if __name__ == '__main__': raise SystemExit(main())
