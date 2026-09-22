"""Signed nine-file immutable native application TCP profile."""
from pathlib import Path
import argparse,inspect,sys
import build_x86_64_shell_media as legacy
import build_x86_64_graphical_media as geometry
import check_x86_64_application_tcp_media as check
from run_qemu_x86_64_runtime_clock import once
NAMES=check.NAMES
source=inspect.getsource(geometry.image)
namespace={**vars(geometry),'NAMES':NAMES}
exec(compile(source,'<application-tcp-ext2-producer>','exec'),namespace)
image=namespace['image']
selected=check.clone(legacy,[
 ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_application_tcp_media.py'),
 ("output/'shell-media.json'","output/'application-tcp-media.json'"),
 ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):",
  "for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','netdrv.prg','netstack.prg','udp.prg','nc.prg'):"),
 ("    shell=attempt/'root/bin/shell.prg'",
  "    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
 ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-1k',check.medium_files(values))"),
 ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
  "'system.ext2 is read-only; UDP and TCP use explicit application grants and separate Ring3 services.\\n'")],
 'reist_application_tcp_producer')
selected.check=check;selected.data=sys.modules[__name__]
inputs=selected.inputs;build=selected.build;publish=selected.publish
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
