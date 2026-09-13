"""One explicitly authorized i386 reference qualification; never updates pins.

This consumer is separate from the normal byte-identity guard. Original disks
are only read; actual Workstation guests use exclusive disposable copies.
A later user build is not automatically admitted. Constants identify this
reviewed attempt. VMware runs its APIC profile; QEMU runs its own APIC/PIT
build. Cross-profile execution never qualifies either protected reference.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import uuid

import verify_x86_64_reference_artifacts as guard
import validate_boot_manifest as manifest
from verify_text_artifacts import read_fat_file
from verify_js_examples_artifacts import short_path
import run_qemu_smoke as smoke

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'build/codex-agent/r83ah-pio'
REBUILD = EVIDENCE / 'reference-rebuild'
QEMU_REBUILD = EVIDENCE / 'qemu-reference-rebuild'
EXPECTED = {
    'build/reist-os.img': 'd6e77ebe48762d9b1e41bae29c26e5e1240afee70f1bd77ca03a9d135384713c',
    'build/vmware/reist-os/reist-os-flat.vmdk': '793b1955d41aa6d468bc6cb6f289c01c1febda588009734406e1582f93122a3b',
    'build/codex-agent/r345-js-colors/framebuffer/reist-os.img': 'ac4b127e871c6aa46d36c92cd4929bf9225a25ddbcf571c8b91b2ad232984f42',
}
PROGRAM_DIGEST = '6e7d0301097d05be5c7595211372f1087a9fa7d106c5a0e5ca131664c2303556'
DISKS = tuple(EXPECTED)[:2]


def need(value, message):
    if not value:
        raise ValueError(message)


def local_file(path):
    need(path.resolve().is_relative_to(ROOT), 'reference path escape')
    for parent in (path, *path.parents):
        if parent == ROOT:
            break
        need(not parent.is_symlink() and not parent.is_junction(), 'reference path alias')
    need(path.is_file() and path.stat().st_nlink == 1, 'reference file kind/link')
    return path


def snapshot():
    files = [ROOT / p for p in EXPECTED]
    files += [ROOT / 'build' / p for p in (
        'kernel.bin', 'kernel.bin.sig', 'reist-sbom.spdx.json', '.windows-build-config.json')]
    programs = guard.program_inventory(ROOT / 'build/programs')
    files += [ROOT / 'build/programs' / name for name in programs]
    for directory in (REBUILD, QEMU_REBUILD):
        files += [directory / name for name in ('kernel.bin', 'kernel.bin.sig', 'reist-os.img',
                  'reist-sbom.spdx.json', '.windows-build-config.json')]
        files += [directory / 'programs' / name for name in programs]
    return {str(p.relative_to(ROOT)).replace('\\', '/'): guard.digest(local_file(p)) for p in files}


def unchanged_during(take_snapshot, work):
    before = take_snapshot()
    try:
        return work()
    finally:
        need(take_snapshot() == before, 'reference changed during qualification')


def same_programs(expected, actual):
    need(len(expected) == 96 and expected.keys() == actual.keys(), 'exact96 program inventory')
    wrong = [name for name in expected if expected[name] != actual[name]]
    need(not wrong, 'program payload mismatch: ' + ','.join(wrong))


def json_file(path):
    local_file(path)
    need(path.stat().st_size <= 1024 * 1024, 'JSON capacity')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, 'duplicate JSON field')
            out[key] = value
        return out
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def verify_contents(report):
    before = snapshot()
    need(all(before[p] == sha for p, sha in EXPECTED.items()), 'reviewed candidate changed')
    programs = guard.program_inventory(ROOT / 'build/programs')
    need(guard.inventory_digest(programs) == PROGRAM_DIGEST, 'reviewed programs changed')
    for directory, target in ((ROOT / 'build', 'vmware'), (REBUILD, 'vmware'), (QEMU_REBUILD, 'qemu')):
        config = json_file(directory / '.windows-build-config.json')
        need(config['target'] == target and config['video'] == 'vga', 'reference build profile')
        need(not any(v is True for v in config.values()), 'reference contains enabled test switch')
    sbom = json_file(ROOT / 'build/reist-sbom.spdx.json')
    entries = sbom['files']
    need(len(entries) == 99, 'SBOM exact artifact inventory')
    expected_names = {'./build/' + name for name in ('kernel.bin', 'kernel.bin.sig', 'reist-os.img')}
    expected_names.update('./build/programs/' + name for name in programs)
    need({entry['fileName'] for entry in entries} == expected_names, 'SBOM exact artifact paths')
    seen = set()
    for entry in entries:
        name = entry['fileName']
        need(name.startswith('./build/') and name not in seen, 'SBOM path/duplicate')
        seen.add(name)
        relative = name[2:]
        need(relative in before and relative not in (
            'build/reist-sbom.spdx.json', 'build/.windows-build-config.json'), 'SBOM unexpected artifact')
        checks = [x['checksumValue'] for x in entry['checksums'] if x['algorithm'] == 'SHA256']
        need(len(checks) == 1, 'SBOM digest count')
        # The untouched packaged VMware disk is the SBOM's original main disk.
        actual = before[DISKS[1]] if relative == DISKS[0] else before[relative]
        need(checks[0] == actual, 'SBOM payload mismatch: ' + relative)
    rebuilt_programs = guard.program_inventory(REBUILD / 'programs')
    same_programs(programs, rebuilt_programs)
    same_programs(programs, guard.program_inventory(QEMU_REBUILD / 'programs'))
    kernel = before['build/kernel.bin']
    need(guard.digest(local_file(REBUILD / 'kernel.bin')) == kernel, 'rebuilt kernel differs')
    openssl = shutil.which('openssl')
    if not openssl:
        candidate = Path('C:/msys64/mingw64/bin/openssl.exe')
        need(candidate.is_file(), 'OpenSSL unavailable')
        openssl = str(candidate)
    for directory in (ROOT / 'build', REBUILD, QEMU_REBUILD):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_boot_signature.py'),
            '--artifact', str(directory / 'kernel.bin'), '--signature', str(directory / 'kernel.bin.sig'),
            '--policy', str(ROOT / 'safety/boot_trust_policy.json'), '--openssl', openssl,
            '--root', str(ROOT)], capture_output=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        need(result.returncode == 0, 'RSA-PSS signature failed')
    windows = (ROOT / 'scripts/build-windows.ps1').read_text(encoding='utf-8')
    paths = {name: short_path(path) for path, name in
             re.findall(r"'([^']+)' = '([A-Z0-9]+\.PRG)'", windows)}
    paths['HELLO.PRG'] = 'usr/bin/hello.prg'
    need(paths.keys() == programs.keys(), 'packaged path inventory')
    images = {}
    for relative in (*DISKS, str((REBUILD / 'reist-os.img').relative_to(ROOT)),
                     str((QEMU_REBUILD / 'reist-os.img').relative_to(ROOT))):
        image = local_file(ROOT / relative)
        info = manifest.validate_image(image, 'hdd')
        directory = image.parent if image.parent in (REBUILD, QEMU_REBUILD) else ROOT / 'build'
        need(info.kernel_sha256 == guard.digest(directory / 'kernel.bin') and info.slot_count == 2,
             'embedded platform kernel/slots')
        need(info.signature_sha256 == guard.digest(directory / 'kernel.bin.sig'), 'embedded signature')
        embedded = {name: hashlib.sha256(read_fat_file(image, path)).hexdigest()
                    for name, path in paths.items()}
        same_programs(programs, embedded)
        with image.open('rb') as disk:
            stage1 = (REBUILD / 'stage1_mbr.bin').read_bytes()
            need(len(stage1) == 512 and disk.read(446) == stage1[:446], 'rebuilt stage1 code')
            stage2 = (REBUILD / 'stage2_bios.bin').read_bytes()
            need(0 < len(stage2) <= 32768, 'stage2 capacity')
            disk.seek((info.partition_lba + 1) * 512)
            need(disk.read(len(stage2)) == stage2, 'rebuilt stage2 code')
        images[relative] = {'manifest': asdict(info), 'programs': embedded,
                            'sha256': guard.digest(image)}
    report.update(before=before, images=images, programs=programs,
                  sbom_created=sbom['creationInfo']['created'], rebuild=str(REBUILD),
                  qemu_rebuild=str(QEMU_REBUILD))


def reference_cases():
    return [('vmware-main-apic', 'vmware', ROOT / DISKS[0], False),
            ('vmware-package-apic', 'vmware', ROOT / DISKS[1], False),
            ('qemu-apic', 'qemu', QEMU_REBUILD / 'reist-os.img', False),
            ('qemu-pit', 'qemu', QEMU_REBUILD / 'reist-os.img', True)]


def guest_cases(qemu, image, profile):
    # A VMware image may boot under QEMU but its ATA timing is not the QEMU
    # runtime profile. Never silently turn that cross-profile run into evidence.
    need(profile == 'qemu', 'VMware reference requires matching runtime qualification')
    return [dict(qemu=qemu, image=image, timeout=60, no_apic=pit, memory='1024M',
                 persistent=False, nic='none', smp=1, expect_reist_probe=True,
                 boot_only=False) for pit in (False, True)]


def guest_result(code, transcript, error):
    need(code == 0 and error is None, 'guest capture failed: ' + str(error))
    failure = smoke.validate(transcript, expect_reist_probe=True)
    need(failure is None, 'guest oracle failed: ' + str(failure))


def vmware_config(port, pit):
    need(type(port) is int and 1024 <= port <= 65535 and type(pit) is bool, 'VMware port/profile')
    config = {
        '.encoding': 'UTF-8', 'config.version': '8', 'virtualHW.version': '20',
        'displayName': 'REIST isolated reference proof', 'guestOS': 'other',
        'firmware': 'bios', 'bios.bootOrder': 'hdd', 'bios.hddOrder': 'sata0:0',
        'memsize': '1024', 'numvcpus': '1', 'cpuid.coresPerSocket': '1',
        'mem.hotadd': 'FALSE', 'vcpu.hotadd': 'FALSE',
        'sata0.present': 'TRUE', 'sata0:0.present': 'TRUE',
        'sata0:0.fileName': 'reference.vmdk', 'sata0:0.deviceType': 'disk',
        'sata0:0.mode': 'persistent', 'sata0:0.startConnected': 'TRUE',
        'floppy0.present': 'FALSE', 'sound.present': 'FALSE',
        'usb.present': 'FALSE', 'ehci.present': 'FALSE', 'usb_xhci.present': 'FALSE',
        'usb.generic.allowHID': 'FALSE', 'usb.generic.allowLastHID': 'FALSE',
        'ethernet0.present': 'FALSE', 'sharedFolder.maxNum': '0',
        'isolation.tools.hgfs.disable': 'TRUE', 'isolation.tools.copy.disable': 'TRUE',
        'isolation.tools.paste.disable': 'TRUE', 'svga.present': 'TRUE',
        'mks.enable3d': 'FALSE', 'serial0.present': 'TRUE', 'serial0.fileType': 'file',
        'serial0.fileName': 'serial.log', 'serial0.startConnected': 'TRUE',
        'serial0.tryNoRxLoss': 'TRUE', 'serial0.yieldOnMsrRead': 'TRUE',
        'RemoteDisplay.vnc.enabled': 'TRUE', 'RemoteDisplay.vnc.ip': '127.0.0.1',
        'RemoteDisplay.vnc.port': str(port), 'tools.syncTime': 'FALSE',
        'tools.remindInstall': 'FALSE', 'uuid.action': 'create',
        'msg.autoAnswer': 'TRUE',
    }
    if pit:
        config['cpuid.1.edx'] = '----:----:----:----:----:--0-:----:----'
    return config


def parse_vm_list(output):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    count = re.fullmatch(r'Total running VMs: ([0-9]+)', lines[0]) if lines else None
    need(count is not None and 0 <= int(count[1]) <= 64, 'unverified VMware inventory')
    need(len(lines) == int(count[1]) + 1, 'VMware inventory count')
    need(all(line.lower().endswith('.vmx') for line in lines[1:]), 'VMware inventory path')
    return lines[1:]


def owns_vm_process(command, vmx):
    if not isinstance(command, str):
        return False
    normalized = command.replace('\\', '/').lower()
    path = str(vmx).replace('\\', '/').lower()
    return re.search(r'(?:^|\s)"?' + re.escape(path) + r'"?(?:\s|$)', normalized) is not None


def vmware_processes():
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
        "@(Get-CimInstance Win32_Process -Filter \"Name='vmware-vmx.exe'\" | "
        "Select-Object ProcessId,CommandLine,CreationDate) | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=10,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    need(result.returncode == 0, 'VMX process inventory failed')
    data = json.loads(result.stdout) if result.stdout.strip() else []
    data = [data] if isinstance(data, dict) else data
    need(isinstance(data, list) and len(data) <= 64, 'VMX process inventory capacity')
    return data


def vmware_timer_backend(text, pit):
    apic_marker = 'Timer calibrated to 10 ms'
    pit_marker = 'Local APIC unavailable; using PIT scheduler fallback'
    wanted, forbidden = (pit_marker, apic_marker) if pit else (apic_marker, pit_marker)
    need(wanted in text and forbidden not in text, 'actual VMware timer backend missing/conflicting')


class VmwareCopy:
    """Exclusive local test VM; no original descriptor or VMX is ever launched."""
    def __init__(self, folder, source, pit):
        self.folder = folder.absolute()
        need(self.folder.is_relative_to(EVIDENCE) and not self.folder.exists(), 'fresh VM folder required')
        for parent in self.folder.parents:
            if parent == ROOT:
                break
            need(not parent.is_symlink() and not parent.is_junction(), 'VM folder alias')
        self.folder.mkdir()
        self.vmx = self.folder / 'reference.vmx'
        self.pit = pit
        self.commands = []
        self.tool = next((p for p in (
            Path('C:/Program Files/VMware/VMware Workstation/vmrun.exe'),
            Path('C:/Program Files (x86)/VMware/VMware Workstation/vmrun.exe')) if p.is_file()), None)
        need(self.tool is not None, 'Workstation vmrun unavailable')
        need(source in (ROOT / p for p in DISKS), 'unapproved source disk')
        local_file(source)
        need(source.stat().st_size == 536870912, 'exact reference extent size')
        before = guard.digest(source)
        with source.open('rb') as incoming, (self.folder / 'reference.img').open('xb') as out:
            for _ in range(512):
                block = incoming.read(1048576)
                need(len(block) == 1048576, 'reference shortened while copying')
                out.write(block)
            need(not incoming.read(1), 'reference grew while copying')
        need(guard.digest(source) == before == guard.digest(self.folder / 'reference.img'), 'VM copy digest')
        with (self.folder / 'reference.vmdk').open('x', encoding='ascii') as out:
            out.write('version=1\nencoding="UTF-8"\nCID=fffffffe\nparentCID=ffffffff\n'
                      'createType="monolithicFlat"\nRW 1048576 FLAT "reference.img" 0\n'
                      'ddb.adapterType = "ide"\nddb.geometry.cylinders = "1040"\n'
                      'ddb.geometry.heads = "16"\nddb.geometry.sectors = "63"\n')
        with socket.socket() as port_probe:
            port_probe.bind(('127.0.0.1', 0))
            self.port = port_probe.getsockname()[1]
        config = vmware_config(self.port, pit)
        with self.vmx.open('x', encoding='ascii') as out:
            out.write(''.join(f'{key} = "{value}"\n' for key, value in config.items()))

    def command(self, *args, timeout=15):
        record = {'args': list(map(str, args)), 'timeout': timeout}
        self.commands.append(record)
        try:
            result = subprocess.run([str(self.tool), '-T', 'ws', *map(str, args)],
                capture_output=True, text=True, timeout=timeout,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            record.update(exit=result.returncode, stdout=result.stdout, stderr=result.stderr)
            need(len(result.stdout) + len(result.stderr) <= 65536, 'vmrun output capacity')
            return result
        except subprocess.TimeoutExpired:
            record['timed_out'] = True
            raise
        finally:
            (self.folder / 'commands.json').write_text(json.dumps(self.commands, indent=2), encoding='utf-8')

    def inventory(self):
        result = self.command('list', timeout=5)
        need(result.returncode == 0, 'vmrun list failed')
        return parse_vm_list(result.stdout)

    def stop(self):
        # Always attempt the exact fresh VM path, including ambiguous launches.
        try:
            self.command('stop', self.vmx, 'hard', timeout=10)
        except subprocess.TimeoutExpired:
            pass
        owned = [p for p in vmware_processes() if owns_vm_process(p['CommandLine'], self.vmx)]
        for process in owned:
            pid = process['ProcessId']
            need(type(pid) is int and pid > 0, 'owned PID type')
            # Recheck creation identity and exact command before process-scoped
            # fallback; never kill an unrelated/reused PID or VMware UI.
            again = next((p for p in vmware_processes() if p['ProcessId'] == pid), None)
            if again is None:
                continue
            need(again == process, 'VMX process identity changed')
            kill = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                f'Stop-Process -Id {pid} -Force -ErrorAction Stop'], capture_output=True,
                timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            need(kill.returncode == 0, 'owned VMX teardown failed')
        listed = self.inventory()
        need(not any(Path(p) == self.vmx for p in listed), 'owned VM still registered')
        need(not any(owns_vm_process(p['CommandLine'], self.vmx) for p in vmware_processes()),
             'owned VM process remains')
        (self.folder / 'cleanup.json').write_text(json.dumps({'stopped': True, 'vmx': str(self.vmx)}), encoding='utf-8')

    def serial(self):
        path = self.folder / 'serial.log'
        if not path.exists():
            return ''
        local_file(path)
        need(path.stat().st_size <= 4 * 1024 * 1024, 'serial capacity')
        return path.read_text(encoding='utf-8', errors='replace')

    def run(self):
        need(not self.inventory() and not vmware_processes(), 'existing VMware VM; refusing launch')
        local_file(self.vmx)
        try:
            result = self.command('start', self.vmx, 'nogui', timeout=20)
            need(result.returncode == 0, 'headless VMware launch failed: ' + result.stdout.strip() + result.stderr.strip())
            deadline = time.monotonic() + 60
            sent = False
            while time.monotonic() < deadline:
                text = self.serial()
                failure = smoke.failure_marker(text)
                need(failure is None, 'VMware guest failure: ' + str(failure))
                if not sent and smoke.SHELL_PROMPT in text and 'BOOT_OK' in text:
                    vmware_timer_backend(text, self.pit)
                    send_gtest(self.port, deadline)
                    sent = True
                if sent and smoke.validate(text, expect_reist_probe=True) is None:
                    vmware_timer_backend(text, self.pit)
                    return text
                time.sleep(0.1)
            raise ValueError('VMware GTEST/recovery deadline')
        finally:
            self.stop()


def send_gtest(port, guest_deadline):
    """Existing loopback RFB3.8 KeyEvent contract, no framebuffer allocation."""
    deadline = min(guest_deadline, time.monotonic() + 2)
    need(time.monotonic() < deadline, 'RFB deadline')
    with socket.create_connection(('127.0.0.1', port), timeout=deadline-time.monotonic()) as client:
        def receive(size):
            need(0 < size <= 4096, 'RFB read capacity')
            data = bytearray()
            while len(data) < size:
                need(time.monotonic() < deadline, 'RFB read deadline')
                client.settimeout(deadline - time.monotonic())
                part = client.recv(size - len(data))
                need(part, 'RFB closed')
                data.extend(part)
            return bytes(data)
        need(receive(12) == b'RFB 003.008\n', 'RFB version')
        client.sendall(b'RFB 003.008\n')
        count = receive(1)[0]
        need(0 < count <= 32 and 1 in receive(count), 'RFB authentication profile')
        client.sendall(b'\x01')
        need(receive(4) == bytes(4), 'RFB security result')
        client.sendall(b'\x01')
        width, height = struct.unpack('>HH', receive(4))
        need(320 <= width <= 8192 and 200 <= height <= 8192, 'RFB geometry')
        receive(16)
        length = struct.unpack('>I', receive(4))[0]
        need(0 < length <= 4096, 'RFB server name capacity')
        receive(length)
        for key in (*map(ord, 'gtest'), 0xff0d):
            need(time.monotonic() + 0.02 < deadline, 'RFB command deadline')
            client.settimeout(deadline - time.monotonic())
            client.sendall(struct.pack('>BBHI', 4, 1, 0, key))
            client.sendall(struct.pack('>BBHI', 4, 0, 0, key))
            time.sleep(0.02)


def main():
    start = time.monotonic()
    folder = EVIDENCE / ('reference-qualification-' + uuid.uuid4().hex)
    folder.mkdir(exist_ok=False)
    report = {'passed': False, 'guests': [], 'old_pins': dict(guard.IMAGES),
              'old_program_digest': guard.PROGRAMS_SHA256}
    def work():
        verify_contents(report)
        profile = json_file(ROOT / 'build/.windows-build-config.json')['target']
        need(profile == 'vmware', 'matching Workstation reference required')
        qemu = next((p for p in (Path('C:/tmp/qemu-portable/qemu-system-i386.exe'),
                    Path('C:/Program Files/qemu/qemu-system-i386.exe'),
                    Path('C:/msys64/mingw64/bin/qemu-system-i386.exe')) if p.is_file()), None)
        need(qemu is not None, 'reference QEMU unavailable')
        for label, target, image, pit in reference_cases():
            began = time.monotonic()
            item = {'case': label, 'target': target, 'image': str(image), 'passed': False}
            report['guests'].append(item)
            try:
                if target == 'vmware':
                    need(not pit, 'VMware PIT unsupported in this reference profile')
                    transcript = VmwareCopy(folder / label, image, pit).run()
                    guest_result(0, transcript, None)
                else:
                    need(image == QEMU_REBUILD / 'reist-os.img', 'QEMU exact matching image')
                    case = guest_cases(qemu, image, target)[int(pit)]
                    code, transcript, error = smoke.run(**case)
                    (folder / (label + '.log')).write_text(transcript, encoding='utf-8')
                    guest_result(code, transcript, error)
                    vmware_timer_backend(transcript, pit)
                item['passed'] = True
            finally:
                item['elapsed'] = time.monotonic() - began
            print('REFERENCE_GUEST_OK ' + label, flush=True)
    try:
        unchanged_during(snapshot, work)
        report['passed'] = True
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        report['error'] = str(error)
    report['elapsed'] = time.monotonic() - start
    (folder / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('REFERENCE_QUALIFICATION ' + ('PASS' if report['passed'] else 'FAIL ' + report['error']) +
          f" elapsed={report['elapsed']:.3f}s evidence={folder}")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
