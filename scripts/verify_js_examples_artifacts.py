"""R3.43: packaged scripts and byte-identical accepted R3.42 runtime payloads."""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from run_qemu_math import ROOT, digest, kernel_digest
from verify_text_artifacts import read_fat_file

BASELINE = ROOT / 'build/codex-agent/r342-fat32-write/accepted-final/images'
BASE_IMAGES = {
    'qemu': ('reist-os.img', '091825bdfaec7a3693e3264b310bded053a4c2ab3fd76a4bdfe5023ca4ee0452'),
    'vmware': ('reist-os-flat.vmdk', '93dcf68103bfadd8fb2994e16500271c8e517bf80b515ee97d5f9357c2f35251'),
}
EXAMPLES = ('jsargs.js', 'jsmath.js', 'jsjson.js', 'jserror.js', 'jssafe.js', 'jsread.js', 'mandel.js')


def short_path(path):
    # The independent reader skips LFN. Preserve the actual packaged directory.
    entry = Path(path)
    return (str(entry.with_name(entry.stem[:6] + '~1.prg')).replace('\\', '/')
            if len(entry.stem) > 8 else path)


def same_payload(wanted, actual, label):
    if not wanted or actual != wanted:
        raise ValueError('empty/changed/stale payload: ' + label)
    return hashlib.sha256(actual).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    report = {'baseline': 'f808b558', 'passed': False, 'images': {}}
    start = time.monotonic()
    try:
        windows = (ROOT / 'scripts/build-windows.ps1').read_text()
        paths = {name: path for path, name in re.findall(r"'([^']+)' = '([A-Z0-9]+\.PRG)'", windows)}
        if len(paths) < 93 or not {'JS.PRG', 'JSWORK.PRG', 'SHELL.PRG', 'BENCHMARK.PRG'} <= paths.keys():
            raise ValueError('incomplete program inventory')
        for target, image in (
            ('qemu', ROOT / 'build/reist-os.img'),
            ('vmware', ROOT / 'build/vmware/reist-os/reist-os-flat.vmdk'),
        ):
            name, expected_hash = BASE_IMAGES[target]
            baseline = BASELINE / target / name
            if digest(baseline) != expected_hash:
                raise ValueError('baseline image authentication: ' + target)
            kernel = kernel_digest(image)
            if kernel != kernel_digest(baseline):
                raise ValueError('kernel changed: ' + target)
            programs = {}
            for name, path in paths.items():
                actual_path = short_path(path)
                programs[name] = same_payload(read_fat_file(baseline, actual_path),
                    read_fat_file(image, actual_path), target + '/' + name)
                if digest(ROOT / 'build/programs' / name) != programs[name]:
                    raise ValueError('stale build program: ' + name)
            examples = {}
            for name in EXAMPLES:
                examples[name] = same_payload((ROOT / 'htdocs' / name).read_bytes(),
                    read_fat_file(image, 'htdocs/' + name), target + '/' + name)
            report['images'][target] = {'sha256': digest(image), 'kernel_sha256': kernel,
                                        'programs': programs, 'examples': examples}
        report['passed'] = True
    except (OSError, ValueError) as error:
        report['error'] = str(error)
    report['elapsed_seconds'] = round(time.monotonic() - start, 3)
    (args.evidence / 'protected.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('JS_EXAMPLES_ARTIFACTS ' + ('PASS' if report['passed'] else 'FAIL: ' + report['error']))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
