"""Opt-in packaging only: never compiles a kernel or grants another device."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,uuid
import build_x86_64_boot_media as old
import build_x86_64_fs_media as data
import check_x86_64_shell_media as check
ROOT=Path(__file__).resolve().parents[1]


def publish(output,candidate,openssl,log):
    check.need(candidate.parent==output and candidate.name.startswith('shell-index-') and
               not candidate.is_symlink(),'publication candidate path')
    old.run([sys.executable,ROOT/'scripts/check_x86_64_shell_media.py','--directory',output,'--index',candidate,'--openssl',openssl],log)
    os.replace(candidate,output/'shell-media.json')


def inputs(directory):
    directory=Path(directory).absolute()
    check.need(directory==directory.resolve() and directory.is_relative_to(ROOT/'build'),'exact input directory')
    values={name:check.bounded(check.exact_path(directory,name),check.FILES[name]) for name in (check.CORE,check.KERNEL,'boot-programs.bin')}
    catalog=values['boot-programs.bin']
    attempts=list(directory.glob('programs-*'));check.need(len(attempts)<=128,'input producer capacity')
    matching=[]
    for attempt in attempts:
        check.need(not attempt.is_symlink() and attempt.resolve().parent==directory,'producer path')
        if attempt.is_dir() and (attempt/'boot-programs.bin').is_file() and check.bounded(attempt/'boot-programs.bin',4*266336)==catalog:
            matching.append(attempt)
    check.need(len(matching)==1,'unique catalog producer');attempt=matching[0]
    for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):
        values[name]=check.bounded(check.exact_path(attempt,name),check.FILES[name])
    shell=attempt/'root/bin/shell.prg'
    check.need(not shell.is_symlink() and shell.resolve()==shell and check.bounded(shell,524288)==values['program0.prg'],'normal packaged shell binding')
    check.input_binding(values);return values


def build(directory,output,nasm=None,openssl=None):
    values=inputs(directory);output=Path(output).absolute()
    check.need(output==output.resolve() and output.is_relative_to(ROOT/'build/codex-agent'),'new media output scope')
    output.mkdir(parents=True,exist_ok=True)
    attempt=output/('shell-media-'+uuid.uuid4().hex);attempt.mkdir()
    log=attempt/'build.log';nasm=nasm or shutil.which('nasm') or 'C:/tools/nasm-3.02/nasm.exe'
    openssl=openssl or shutil.which('openssl') or 'openssl'
    for name,raw in values.items():
        with (attempt/name).open('xb') as stream:stream.write(raw)
    for name in ('stage1_mbr','stage1_floppy','stage2_bios'):
        old.run([nasm,'-f','bin',ROOT/('arch/x86/boot/bios/'+name+'.asm'),'-o',attempt/(name+'.bin')],log)
    old.sign(attempt/check.KERNEL,attempt/(check.KERNEL+'.sig'),openssl,log)
    # Existing fixed media layouts, with no unnecessary duplicate user ELFs on
    # the rescue floppy. The actual normal shell is inside the signed catalog.
    kernel_sig=(attempt/(check.KERNEL+'.sig')).read_bytes()
    floppy=old.floppy.create_floppy_image((attempt/'stage1_floppy.bin').read_bytes(),
        (attempt/'stage2_bios.bin').read_bytes(),values[check.KERNEL],kernel_sig)
    with (attempt/'reist-x86_64-floppy.img').open('xb') as stream:stream.write(floppy)
    # The reused legacy producer always emits VM metadata. Keep that unaccepted
    # metadata in a separate evidence directory, never in this signed package.
    work=output/('shell-build-'+attempt.name.removeprefix('shell-media-'));work.mkdir()
    old.disk.build_image(attempt/'stage1_mbr.bin',attempt/'stage2_bios.bin',attempt/check.KERNEL,
        attempt/(check.KERNEL+'.sig'),attempt/'reist-x86_64.img',work/'producer-only.vmdk',data_files={})
    with (attempt/'system.ext2').open('xb') as stream:stream.write(data.image('ext2-1k',program=values['file-program.prg']))
    (attempt/'README.txt').write_text(
        'REIST native shell: bounded two-medium RESEARCH profile, not a finished OS/release.\n'
        'Kernel, initial /bin/shell.prg and services are in the signed embedded catalog.\n'
        'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\n'
        'Boot HDD is primary ATA slave with BIOS priority; alternatively boot the floppy.\n'
        'Use disposable COW layers; no writes are permitted on either medium.\n'
        'Public research signing key; no Secure Boot, hardware or VMware acceptance claim.\n'
        'One CPU, QEMU pc/TCG, 4 or8GiB, serial shell; no network, DMA or host shares.\n',encoding='ascii')
    package=dict(version=1,architecture='x86_64',profile=check.PROFILE,attempt=attempt.name,
        artifacts={name:check.digest(attempt/name,limit) for name,limit in check.FILES.items()},devices=check.DEVICES)
    raw=(json.dumps(package,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    check.need(len(raw)<=16384,'signed index capacity')
    (attempt/'package.json').write_bytes(raw);old.sign(attempt/'package.json',attempt/'package.json.sig',openssl,log)
    envelope={'package':package,'signature':(attempt/'package.json.sig').read_bytes().hex()}
    candidate=output/('shell-index-'+uuid.uuid4().hex+'.json')
    with candidate.open('x',encoding='ascii') as stream:json.dump(envelope,stream,sort_keys=True,separators=(',',':'))
    publish(output,candidate,openssl,log)
    print('SHELL_MEDIA_BUILD_OK',attempt,flush=True);return attempt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input-directory',type=Path,required=True)
    parser.add_argument('--output-directory',type=Path,required=True);parser.add_argument('--nasm');parser.add_argument('--openssl')
    args=parser.parse_args()
    try:build(args.input_directory,args.output_directory,args.nasm,args.openssl)
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        print('SHELL_MEDIA_BUILD_FAIL',str(error));raise SystemExit(1)
