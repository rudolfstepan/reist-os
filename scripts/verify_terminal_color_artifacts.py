"""Authenticate color test images and preserve accepted benchmark payloads."""
import argparse
import json
import shutil
import time
import uuid
from pathlib import Path
from verify_js_examples_artifacts import BASELINE, BASE_IMAGES, short_path, same_payload
from run_qemu_math import ROOT, digest, kernel_digest
from verify_text_artifacts import read_fat_file

EVIDENCE = ROOT / 'build/codex-agent/r344-terminal-color'
FB_IMAGE = EVIDENCE / 'framebuffer/reist-os.img'


def check_programs(image):
    return {name: same_payload((ROOT/'build/programs'/name).read_bytes(),
            read_fat_file(image, 'bin/'+name.lower()), name)
            for name in ('ECHO.PRG', 'COLORTST.PRG')}


def verify():
    manifest = json.loads(FB_IMAGE.with_suffix('.json').read_text())
    if digest(FB_IMAGE) != manifest['sha256']:
        raise ValueError('changed framebuffer archive')
    config = json.loads((ROOT/'build/.windows-build-config.json').read_text())
    if (config['target'], config['video']) != ('qemu', 'vga'):
        raise ValueError('final reference must be qemu/vga')
    report = {}
    for target, image in (('qemu', ROOT/'build/reist-os.img'),
                          ('vmware', ROOT/'build/vmware/reist-os/reist-os-flat.vmdk'),
                          ('framebuffer', FB_IMAGE)):
        programs = check_programs(image)
        baseline_target = 'vmware' if target == 'vmware' else 'qemu'
        name, wanted_hash = BASE_IMAGES[baseline_target]
        baseline = BASELINE/baseline_target/name
        if digest(baseline) != wanted_hash:
            raise ValueError('unauthenticated baseline: '+baseline_target)
        for name in ('BENCHMARK.PRG', 'MATHTEST.PRG', 'TEXTTEST.PRG'):
            path = short_path('usr/bin/'+name.lower())
            programs[name] = same_payload(read_fat_file(baseline, path),
                                         read_fat_file(image, path), target+'/'+name)
        report[target] = {'sha256': digest(image), 'kernel_sha256': kernel_digest(image),
                          'programs': programs}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-framebuffer', action='store_true')
    args = parser.parse_args()
    start = time.monotonic()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    report = {'passed': False}
    try:
        if args.archive_framebuffer:
            config = json.loads((ROOT/'build/.windows-build-config.json').read_text())
            if (config['target'], config['video']) != ('qemu', 'framebuffer'):
                raise ValueError('archive requires qemu/framebuffer build')
            programs = check_programs(ROOT/'build/reist-os.img')
            FB_IMAGE.parent.mkdir(exist_ok=False)
            shutil.copyfile(ROOT/'build/reist-os.img', FB_IMAGE)
            report.update(sha256=digest(FB_IMAGE), config=config, programs=programs)
            if digest(ROOT/'build/reist-os.img') != report['sha256']:
                raise ValueError('source changed while archiving')
            report['passed'] = True
            FB_IMAGE.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
        else:
            report['images'] = verify()
        report['passed'] = True
    except (OSError, ValueError, KeyError) as error:
        report['error'] = str(error)
    report['elapsed_seconds'] = round(time.monotonic()-start, 3)
    (EVIDENCE/('artifacts-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(report, indent=2)+'\n')
    print('TERMINAL_COLOR_ARTIFACTS '+('PASS' if report['passed'] else 'FAIL: '+report['error'])+
          f" elapsed={report['elapsed_seconds']}s")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
