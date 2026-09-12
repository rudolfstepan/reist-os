"""Nine real BIOS/media cases, preserving the original direct-boot oracles."""
from pathlib import Path
import argparse
import binascii
import json
import shutil
import struct
import subprocess
import time
import uuid
import verify_x86_64_boot_media as package
import run_qemu_x86_64_native_ipc as ipc
from run_qemu_x86_64_boot import resolve_qemu,terminate_bounded,FAILURES
from measure_cpp_baseline import suppress_windows_test_dialogs
ROOT=Path(__file__).resolve().parents[1]
SIGNATURE='Kernel RSA-PSS verification failed'
DIGEST='Kernel SHA-256 verification failed'
MANIFEST='Invalid boot manifest'
FALLBACK='BOOT_SLOT_A_FAILED_TRY_B'
CASES=(('hdd',4096,'normal'),('hdd',8192,'normal'),('hdd',4096,'a-signature'),
       ('hdd',4096,'signatures'),('hdd',4096,'digest'),('hdd',4096,'manifest'),
       ('floppy',4096,'normal'),('floppy',4096,'signatures'),('floppy',4096,'digest'))


def mutate(source,destination,layout,case):
    if destination.exists() or destination.resolve()==source.resolve():raise ValueError('fresh mutation target required')
    shutil.copyfile(source,destination)
    partition=2048 if layout=='hdd' else 1
    slots=(0,) if layout=='floppy' or case=='a-signature' else (0,96)
    with destination.open('r+b') as image:
        for slot in slots:
            at=(partition+slot)*512;image.seek(at);header=bytearray(image.read(512))
            if header[:8]!=b'X86BOOT2':raise ValueError('mutation manifest identity')
            if case in ('signatures','a-signature'):header[80]^=1
            elif case=='manifest':struct.pack_into('<I',header,8,4)
            elif case=='digest':
                lba,size=struct.unpack_from('<II',header,24)
                if not 4096<=size<=1048576 or lba not in (128,3136):raise ValueError('mutation kernel bounds')
                position=(partition+lba)*512;image.seek(position);kernel=bytearray(image.read(size))
                if len(kernel)!=size:raise ValueError('mutation truncated kernel')
                kernel[size//2]^=1;image.seek(position);image.write(kernel)
                struct.pack_into('<I',header,36,binascii.crc32(kernel)&0xffffffff)
            else:raise ValueError('unknown mutation')
            struct.pack_into('<I',header,44,0)
            struct.pack_into('<I',header,44,(-sum(struct.unpack('<128I',header)))&0xffffffff)
            image.seek(at);image.write(header)


def validate(serial,layout,case):
    positive=case in ('normal','a-signature')
    if serial.count('x86 native BIOS loader')!=1:raise ValueError('BIOS loader count')
    expected_fallback=int(layout=='hdd' and case!='normal')
    if serial.count(FALLBACK)!=expected_fallback or 'BOOT_SLOT_B_FAILED_TRY_A' in serial:
        raise ValueError('BIOS exact fallback count')
    expected={SIGNATURE:1 if case=='a-signature' else (2 if layout=='hdd' else 1) if case=='signatures' else 0,
              DIGEST:(2 if layout=='hdd' else 1) if case=='digest' else 0,
              MANIFEST:2 if case=='manifest' else 0}
    if any(serial.count(marker)!=count for marker,count in expected.items()):raise ValueError('BIOS rejection count')
    if any(marker in serial for marker in ('Kernel CRC32 verification failed','Disk read failed','Kernel load failed','Invalid ELF32 kernel','Boot control validation/write failed')):
        raise ValueError('unexpected BIOS failure')
    if positive:
        stages=('x86 native BIOS loader','Verifying kernel SHA-256/RSA-PSS...',
                'Loading ELF32 kernel...','Starting kernel...','REIST_X86_64_LONG_MODE_BOOT_OK')
        positions=[serial.find(marker) for marker in stages]
        if min(positions)<0 or positions!=sorted(positions):raise ValueError('BIOS verified-start ordering')
        if any(serial.count(marker)!=1 for marker in stages[2:]):raise ValueError('BIOS unique kernel entry')
        if case=='a-signature' and not serial.index(SIGNATURE)<serial.index(FALLBACK)<serial.index('Loading ELF32 kernel...'):
            raise ValueError('BIOS reject before fallback execution')
        return ipc.validate(serial,0)
    if any(marker in serial for marker in ('Starting kernel...','Loading ELF32 kernel...','REIST_X86_64_')):
        raise ValueError('rejected media entered kernel')
    return []


def capture(image,layout,folder,positive,ram):
    if layout not in ('hdd','floppy') or ram not in (4096,8192) or any(c in str(image) for c in ',\r\n'):
        raise ValueError('BIOS device/profile admission')
    serial=folder/'guest.log';errors=folder/'stderr.log'
    command=[str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m',str(ram)+'M',
             '-smp','1','-display','none','-monitor','none','-serial','file:'+str(serial),
             '-no-reboot','-no-shutdown','-snapshot','-nic','none',
             '-drive','file='+str(image)+',format=raw,if='+('ide' if layout=='hdd' else 'floppy'),
             '-boot','c' if layout=='hdd' else 'a']
    (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
    with errors.open('wb') as log:
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        started=time.monotonic();text=''
        try:
            while time.monotonic()-started<20:
                if serial.exists():text=package.bounded(serial,262144).decode('ascii',errors='replace') if serial.stat().st_size else ''
                if (positive and ipc.process.SUCCESS in text) or any(marker in text for marker in FAILURES):break
                if not positive and 'REIST_X86_64_' in text:break
                if vm.poll() is not None:raise ValueError('BIOS VM exited before witness lease')
                time.sleep(.02)
        finally:terminate_bounded(vm)
    if errors.stat().st_size>65536:raise ValueError('BIOS stderr capacity')
    return package.bounded(serial,262144).decode('ascii',errors='replace')


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence scope')
    if not args.directory.resolve().is_relative_to(ROOT/'build'):p.error('native input scope')
    suppress_windows_test_dialogs();folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result={'passed':False,'cases':[]};started=time.monotonic()
    try:
        media=package.verify(args.directory,openssl=shutil.which('openssl') or 'openssl')
        for layout,ram,case in CASES:
            target=folder/(layout+'-'+str(ram)+'-'+case);target.mkdir()
            image=media/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
            if case!='normal':
                selected=target/'mutated.img';mutate(image,selected,layout,case);image=selected
            serial=capture(image,layout,target,case in ('normal','a-signature'),ram)
            rows=validate(serial,layout,case)
            result['cases'].append({'layout':layout,'ram_mib':ram,'case':case,'tasks':rows})
            print('NATIVE_BOOT_MEDIA_CASE_OK '+layout+' '+str(ram)+' '+case,flush=True)
        package.verify(args.directory,openssl=shutil.which('openssl') or 'openssl')
        result['passed']=True;print('NATIVE_BOOT_MEDIA_RUNTIME_OK evidence='+str(folder));return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
        result['error']=str(error);print('NATIVE_BOOT_MEDIA_RUNTIME_FAIL '+str(error)+' evidence='+str(folder));return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
