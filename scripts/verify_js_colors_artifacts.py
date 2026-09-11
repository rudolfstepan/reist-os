"""R3.45: authenticate three images and protect every unaffected binary."""
import argparse
import json
import re
import shutil
import time
import uuid
from run_qemu_math import ROOT, digest, kernel_digest
from verify_js_examples_artifacts import short_path, same_payload
from verify_text_artifacts import read_fat_file

EVIDENCE = ROOT/'build/codex-agent/r345-js-colors'
FB_IMAGE = EVIDENCE/'framebuffer/reist-os.img'
BASELINE = EVIDENCE/'baseline'
BASE_IMAGES = {
    'qemu': (ROOT/'build/reist-os.img', '68f4a69eee6b215f74b26cccd9f2d423ad4ecce003fa558393bc15e356417c8a'),
    'vmware': (ROOT/'build/vmware/reist-os/reist-os-flat.vmdk', '0b136069c5e5f082eda47d9601c69744d94f8ed6d52b7869c0d1c71a064b77dd'),
    'framebuffer': (ROOT/'build/codex-agent/r344-terminal-color/framebuffer/reist-os.img', '02095ab59e45ea9f0d87b74c7eb21a7ee04e9f55e53232519b155dcd9a5e6580'),
}
CHANGED = {'JS.PRG', 'JSWORK.PRG', 'JSRUNTST.PRG'}
EXAMPLES = ('jscolors.js', 'mandelc.js')


def copy_checked(source, destination, wanted):
    if digest(source) != wanted:
        raise ValueError('unauthenticated source: '+str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as output, source.open('rb') as incoming:
        shutil.copyfileobj(incoming, output, 1024*1024)
    if digest(source) != wanted or digest(destination) != wanted:
        raise ValueError('image changed while archiving')


def build_config(video):
    config = json.loads((ROOT/'build/.windows-build-config.json').read_text())
    if (config['target'], config['video']) != ('qemu', video):
        raise ValueError('wrong final reference configuration')
    return config


def verify():
    build_config('vga')
    manifest = json.loads(FB_IMAGE.with_suffix('.json').read_text())
    if not manifest['passed'] or digest(FB_IMAGE) != manifest['sha256']:
        raise ValueError('changed framebuffer archive')
    windows = (ROOT/'scripts/build-windows.ps1').read_text()
    paths = {name: path for path, name in re.findall(r"'([^']+)' = '([A-Z0-9]+\.PRG)'", windows)}
    if len(paths) < 95 or not CHANGED | {'SHELL.PRG', 'BENCHMARK.PRG', 'BROWSER.PRG'} <= paths.keys():
        raise ValueError('incomplete program inventory')
    report = {}
    for target, image in (('qemu', BASE_IMAGES['qemu'][0]), ('vmware', BASE_IMAGES['vmware'][0]),
                          ('framebuffer', FB_IMAGE)):
        source, wanted = BASE_IMAGES[target]
        baseline = BASELINE/(target+'.img') if target != 'framebuffer' else source
        if digest(baseline) != wanted:
            raise ValueError('unauthenticated baseline: '+target)
        kernel = kernel_digest(image)
        if kernel != kernel_digest(baseline):
            raise ValueError('kernel drift: '+target)
        programs = {}
        for name, path in paths.items():
            path = short_path(path)
            actual = read_fat_file(image, path)
            programs[name] = same_payload((ROOT/'build/programs'/name).read_bytes(), actual, target+'/'+name)
            if name not in CHANGED:
                same_payload(read_fat_file(baseline, path), actual, 'protected/'+target+'/'+name)
        examples = {name: same_payload((ROOT/'htdocs'/name).read_bytes(),
                    read_fat_file(image, 'htdocs/'+name), target+'/'+name) for name in EXAMPLES}
        report[target] = {'sha256': digest(image), 'kernel_sha256': kernel,
                          'programs': programs, 'examples': examples}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--archive-baseline', action='store_true')
    group.add_argument('--archive-framebuffer', action='store_true')
    args = parser.parse_args()
    start = time.monotonic(); EVIDENCE.mkdir(parents=True, exist_ok=True)
    report = {'passed': False}
    try:
        if args.archive_baseline:
            BASELINE.mkdir(exist_ok=False)
            for target in ('qemu', 'vmware'):
                source, wanted = BASE_IMAGES[target]
                copy_checked(source, BASELINE/(target+'.img'), wanted)
            if digest(BASE_IMAGES['framebuffer'][0]) != BASE_IMAGES['framebuffer'][1]:
                raise ValueError('unauthenticated previous framebuffer')
        elif args.archive_framebuffer:
            config = build_config('framebuffer')
            source = ROOT/'build/reist-os.img'; wanted = digest(source)
            copy_checked(source, FB_IMAGE, wanted)
            report.update(sha256=wanted, config=config, passed=True)
            FB_IMAGE.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
        else:
            report['images'] = verify()
        report['passed'] = True
    except (OSError, ValueError, KeyError) as error:
        report['error'] = str(error)
    report['elapsed_seconds'] = round(time.monotonic()-start, 3)
    (EVIDENCE/('artifacts-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(report, indent=2)+'\n')
    print('JS_COLOR_ARTIFACTS '+('PASS' if report['passed'] else 'FAIL: '+report['error'])+
          f" elapsed={report['elapsed_seconds']}s")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
