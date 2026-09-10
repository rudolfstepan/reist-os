"""Bounded, headless ATA admin lifecycle; reference and entire auxiliary unchanged."""
import argparse
import json
import time
from pathlib import Path
import run_qemu_fat32_writable_objects as objects
import run_qemu_smoke as smoke

STATUS_ONLINE = 'ADMIN STATUS_STATE resource=1 state=ONLINE'
STATUS_DOWN = 'ADMIN STATUS_STATE resource=1 state=ADMIN_DOWN'
MOUNT_ORIGINAL = 'ADMIN STATUS_MOUNT resource=1 path=/mnt/hdd1'
MOUNT_FRESH = 'ADMIN STATUS_MOUNT resource=1 path=/mnt/admin'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    evidence, reference = args.evidence.resolve(), args.image.resolve()
    if evidence.exists() or evidence == objects.ALLOWED or not evidence.is_relative_to(objects.ALLOWED):
        parser.error('fresh evidence child of r342-fat32-write required')
    evidence.mkdir(parents=True)
    disk = evidence / 'admin-fat32.img'
    initial = objects.fixture(disk)
    digest = objects.handoff.transport.file_sha256(reference)
    previous = smoke.exact_line_position, smoke.failure_marker, smoke.monitor_key_commands
    smoke.exact_line_position, smoke.failure_marker, smoke.monitor_key_commands = (
        objects.handoff.handoff_line_position, objects.handoff.guard_failure_marker, objects.object_keys)
    guest = None
    start = time.monotonic()
    report = dict(passed=False, reference_sha256=digest, commands=[])
    try:
        guest = objects.Guest(args.qemu, reference, disk, evidence, 'admin', start+90)
        guest.boot()
        for command, required in (
            ('devctl status 1', (STATUS_ONLINE, MOUNT_ORIGINAL)),
            ('umount 1', ('ADMIN UMOUNT_OK resource=1',)),
            ('mount 1 fat32 /mnt/admin', ('ADMIN MOUNT_OK resource=1 path=/mnt/admin',)),
            ('devctl down 1', ('ADMIN DEVICE_DOWN_OK resource=1',)),
            ('devctl status 1', (STATUS_DOWN,)),
            ('devctl up 1', ('ADMIN DEVICE_UP_OK resource=1',)),
            ('devctl status 1', (STATUS_ONLINE, MOUNT_FRESH)),
            ('devctl down 0', ('ADMIN ROOT_PROTECTED',)),
            ('cat /htdocs/hello.js', ("print('Hello from REIST JavaScript');",)),
        ):
            output = guest.execute(command, required=required, forbidden=('UMOUNT_FAILED', 'MOUNT_FAILED', 'DEVICE_DOWN_FAILED', 'DEVICE_UP_FAILED'))
            report['commands'].append(dict(command=command, output=output))
        report['passed'] = True
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        report['error'] = str(error)
    finally:
        if guest:
            try:
                guest.close()
            except (OSError, ValueError, RuntimeError, TimeoutError) as error:
                report['passed'] = False
                report['error'] = str(error)
            report['host_continuity'] = guest.continuity.report()
        smoke.exact_line_position, smoke.failure_marker, smoke.monitor_key_commands = previous
        report['reference_unchanged'] = digest == objects.handoff.transport.file_sha256(reference)
        report['whole_auxiliary_unchanged'] = initial == disk.read_bytes()
        report['passed'] &= report['reference_unchanged'] and report['whole_auxiliary_unchanged']
        report['elapsed_seconds'] = round(time.monotonic()-start, 3)
        (evidence / 'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('ADMIN_ATA', 'PASS' if report['passed'] else 'FAIL', report.get('error', ''), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
