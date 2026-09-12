"""Publish research native BIOS media using the existing signed boot format."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import struct
import uuid
import build_x86_64_c_payload as payload
import create_native_boot_image as disk
import create_floppy_boot_image as floppy

ROOT=Path(__file__).resolve().parents[1]
ARCHITECTURE='x86_64'
PROGRAMS={'bin/shell.prg':'reist-x86_64-user-shell.elf',
          'usr/bin/probe.prg':'reist-x86_64-user-probe.elf',
          'usr/bin/child.prg':'reist-x86_64-user-child.elf'}
KERNEL='reist-x86_64-bootstrap.elf'
CORE='reist-x86_64-c-core.elf'
HDD='reist-x86_64.img'
FLOPPY='reist-x86_64-floppy.img'
POLICY=ROOT/'safety/boot_trust_policy.json'
KEY=ROOT/'test/fixtures/reist-research-dev-private.pem'


def run(command,log):
    result=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,
                          timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    with log.open('ab') as stream:stream.write(result.stdout+result.stderr)
    if result.returncode:raise ValueError('native media command failed: '+str(command[1]))


def sign(artifact,signature,openssl,log):
    import sys
    run([sys.executable,ROOT/'scripts/sign_boot_artifact.py','--artifact',artifact,
         '--signature',signature,'--private-key',KEY,'--policy',POLICY,
         '--openssl',openssl,'--profile','research'],log)
    run([sys.executable,ROOT/'scripts/verify_boot_signature.py','--artifact',artifact,
         '--signature',signature,'--policy',POLICY,'--openssl',openssl,'--root',ROOT],log)


def digest(path):
    sha=hashlib.sha256();size=path.stat().st_size
    if not 0<size<=536870912:raise ValueError('artifact hash capacity')
    remaining=size
    with path.open('rb') as stream:
        while remaining:
            chunk=stream.read(min(65536,remaining))
            if not chunk:raise ValueError('artifact changed while hashing')
            sha.update(chunk);remaining-=len(chunk)
        if stream.read(1):raise ValueError('artifact grew while hashing')
    return {'size':size,'sha256':sha.hexdigest()}


def read_input(directory,name):
    path=directory/name
    if path.is_symlink() or not path.is_file() or path.resolve().parent!=directory:
        raise ValueError('native input path escape')
    return payload.read_bounded(path)


def build(directory,nasm,openssl):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(ROOT/'build'):raise ValueError('native media build directory')
    inner=read_input(directory,CORE);outer=read_input(directory,KERNEL)
    parsed=payload.validate(inner);payload.verify_outer(inner,outer)
    if parsed['layout_version']!=4 or 'reist_native_ipc' not in parsed['symbols']:
        raise ValueError('NativeImages requires native processes/IPC/RAM/heap')
    disk.validate_elf32(outer)
    inputs={CORE:inner,KERNEL:outer}
    for name in PROGRAMS.values():
        raw=read_input(directory,name)
        # User executables may be stripped; the private C payload symbol-table
        # contract does not apply to them. The independent consumer checks loads.
        if raw[:7]!=b'\x7fELF\x02\x01\x01' or struct.unpack_from('<HHI',raw,16)!=(2,62,1):
            raise ValueError('native user ELF64 identity')
        inputs[name]=raw
    attempt=directory/('native-media-'+uuid.uuid4().hex)
    attempt.mkdir();log=attempt/'build.log'
    for name,raw in inputs.items():(attempt/name).write_bytes(raw)
    for source,name in (('stage1_mbr','stage1_mbr.bin'),('stage1_floppy','stage1_floppy.bin'),('stage2_bios','stage2_bios.bin')):
        run([nasm,'-f','bin',ROOT/('arch/x86/boot/bios/'+source+'.asm'),'-o',attempt/name],log)
    sign(attempt/KERNEL,attempt/(KERNEL+'.sig'),openssl,log)
    files={path:inputs[name] for path,name in PROGRAMS.items()}
    (attempt/FLOPPY).write_bytes(floppy.create_floppy_image(
        (attempt/'stage1_floppy.bin').read_bytes(),(attempt/'stage2_bios.bin').read_bytes(),
        outer,(attempt/(KERNEL+'.sig')).read_bytes(),files))
    disk.build_image(attempt/'stage1_mbr.bin',attempt/'stage2_bios.bin',attempt/KERNEL,
                     attempt/(KERNEL+'.sig'),attempt/HDD,attempt/'reist-x86_64.vmdk',data_files=files)
    # Replace only the just-generated legacy VM template in this fresh attempt.
    # No legacy device/SMP/network configuration is inherited by the native image.
    vmx='''.encoding = "UTF-8"
config.version = "8"
virtualHW.version = "12"
displayName = "REIST native x86_64 research bootstrap"
guestOS = "other-64"
firmware = "bios"
memsize = "4096"
numvcpus = "1"
ide0:0.present = "TRUE"
ide0:0.fileName = "reist-x86_64.vmdk"
ide0:0.deviceType = "disk"
floppy0.present = "FALSE"
ethernet0.present = "FALSE"
sound.present = "FALSE"
usb.present = "FALSE"
usb.generic.allowHID = "FALSE"
usb.generic.allowLastHID = "FALSE"
sharedFolder.maxNum = "0"
RemoteDisplay.vnc.enabled = "FALSE"
mks.enable3d = "FALSE"
serial0.present = "TRUE"
serial0.fileType = "file"
serial0.fileName = "native-serial.log"
serial0.startConnected = "TRUE"
tools.syncTime = "FALSE"
'''
    (attempt/'reist-x86_64.vmx').write_text(vmx,encoding='ascii')
    (attempt/'README.txt').write_text(
        'REIST native x86_64 RESEARCH BOOTSTRAP\n'
        'Signed relative to existing writable research stage2; not Secure Boot or a release.\n'
        'HDD and rescue floppy contain identical kernel and ELF64 fixture programs.\n'
        'Filesystem programs are NOT loaded by this bootstrap; VFS/services remain unported.\n'
        'VMware configuration: one CPU,4GiB; no VMware acceptance claim, no automatic launch.\n'
        'Use disk image for HDD boot or the separate rescue floppy as BIOS boot medium.\n',encoding='ascii')
    names=[*inputs,'stage1_mbr.bin','stage1_floppy.bin','stage2_bios.bin',KERNEL+'.sig',
           HDD,FLOPPY,'reist-x86_64.vmdk','reist-x86_64.vmx','README.txt']
    package={'version':1,'architecture':ARCHITECTURE,'profile':'research-native-heap',
             'attempt':attempt.name,'programs':PROGRAMS,
             'artifacts':{name:digest(attempt/name) for name in names}}
    raw=(json.dumps(package,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    if len(raw)>16384:raise ValueError('native index capacity')
    (attempt/'package.json').write_bytes(raw)
    sign(attempt/'package.json',attempt/'package.json.sig',openssl,log)
    envelope={'package':package,'signature':(attempt/'package.json.sig').read_bytes().hex()}
    candidate=directory/('native-index-'+uuid.uuid4().hex+'.json')
    candidate.write_text(json.dumps(envelope,sort_keys=True,separators=(',',':'))+'\n',encoding='ascii')
    import sys
    run([sys.executable,ROOT/'scripts/verify_x86_64_boot_media.py','--directory',directory,
         '--index',candidate,'--openssl',openssl],log)
    os.replace(candidate,directory/'native-media.json')
    print('NATIVE_BOOT_MEDIA_BUILD_OK attempt='+str(attempt),flush=True)
    return attempt


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--nasm',default=shutil.which('nasm') or 'C:/tools/nasm-3.02/nasm.exe')
    p.add_argument('--openssl',default=shutil.which('openssl') or 'openssl')
    args=p.parse_args()
    try:build(args.directory,args.nasm,args.openssl);return 0
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:
        print('NATIVE_BOOT_MEDIA_BUILD_FAIL '+str(error));return 1


if __name__=='__main__':raise SystemExit(main())
