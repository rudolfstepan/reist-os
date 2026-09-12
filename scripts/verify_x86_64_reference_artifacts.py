"""Read-only i386 non-regression guard during native x86_64 development.

Pins are reviewed source constants, never learned from the candidate. This is
byte identity against accepted artifacts, not a new i386 runtime qualification.
The historical JS framebuffer has its own pin; it is not compared to new GUI
programs. No archive/rebaseline option and no writes to reference artifacts.
"""
import hashlib
import json
from pathlib import Path
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = '7bd4bef0'
MAX_FILE_BYTES = 1024 * 1024 * 1024
IMAGES = {
    # Captured after the user shut down VMware, before native implementation.
    'build/reist-os.img':
        'e497673dec8b2b687604413e6b1fb1f8fa0edaca53b7eff1e817c95a0a9e8fa5',
    'build/vmware/reist-os/reist-os-flat.vmdk':
        'a43b6e2ff14e3a572622a50e3532c7b3d68a41e13e766648cb3c9e44b4c6f48a',
    'build/codex-agent/r345-js-colors/framebuffer/reist-os.img':
        'ac4b127e871c6aa46d36c92cd4929bf9225a25ddbcf571c8b91b2ad232984f42',
}
PROGRAM_COUNT = 96
PROGRAMS_SHA256 = 'e8204a38f486f5a83c482eb51b56c5a8b4fb0f1420d59e95b40bf1d49514481f'


def digest(path):
    before = path.stat()
    if not path.is_file() or not 0 < before.st_size <= MAX_FILE_BYTES:
        raise ValueError('invalid artifact size/type: ' + str(path))
    result = hashlib.sha256()
    total = 0
    with path.open('rb') as incoming:
        while chunk := incoming.read(1024 * 1024):
            total += len(chunk)
            if total > before.st_size:
                raise ValueError('artifact grew while hashing: ' + str(path))
            result.update(chunk)
    after = path.stat()
    if (total != before.st_size or before.st_size != after.st_size or
            before.st_mtime_ns != after.st_mtime_ns):
        raise ValueError('artifact changed while hashing: ' + str(path))
    return result.hexdigest()


def program_inventory(directory):
    entries = sorted(directory.iterdir(), key=lambda p: p.name)
    if not entries or len(entries) > 256:
        raise ValueError('invalid program inventory size')
    records = {}
    for entry in entries:
        if not entry.is_file() or entry.suffix != '.PRG' or not entry.stem.isalnum():
            raise ValueError('unexpected program entry: ' + entry.name)
        records[entry.name] = digest(entry)
    if [p.name for p in entries] != sorted(p.name for p in directory.iterdir()):
        raise ValueError('program inventory changed while hashing')
    return records


def inventory_digest(records):
    canonical = ''.join(name + ':' + records[name] + '\n' for name in sorted(records))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def verify(root, images, program_count, programs_sha256):
    # Validate all pins first: an unfinished/reference-less guard cannot pass.
    if not images or any(not isinstance(value, str) or len(value) != 64 or
                         any(c not in '0123456789abcdef' for c in value)
                         for value in [*images.values(), programs_sha256]):
        raise ValueError('missing/invalid frozen reference pin')
    actual = {}
    for relative, wanted in images.items():
        actual[relative] = digest(root / relative)
        if actual[relative] != wanted:
            raise ValueError('reference drift: ' + relative)
    programs = program_inventory(root / 'build/programs')
    if len(programs) != program_count or inventory_digest(programs) != programs_sha256:
        raise ValueError('program inventory drift')
    return {'artifacts': actual, 'programs': programs}


def main():
    start = time.monotonic()
    report = {'passed': False, 'baseline_commit': BASELINE_COMMIT}
    try:
        report.update(verify(ROOT, IMAGES, PROGRAM_COUNT, PROGRAMS_SHA256))
        report['passed'] = True
    except (OSError, ValueError) as error:
        report['error'] = str(error)
    report['elapsed_seconds'] = round(time.monotonic() - start, 3)
    evidence = ROOT / 'build/codex-agent/r83s-shell-exit/reference'
    evidence.mkdir(parents=True, exist_ok=True)
    with (evidence / ('check-' + uuid.uuid4().hex + '.json')).open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print('X86_64_REFERENCE ' + ('PASS' if report['passed'] else 'FAIL: ' + report['error']) +
          f" elapsed={report['elapsed_seconds']}s")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
