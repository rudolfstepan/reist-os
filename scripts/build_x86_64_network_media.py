"""Signed normal-shell package with two isolated native network executables."""
from pathlib import Path
import argparse, inspect, sys
import build_x86_64_shell_media as legacy
import build_x86_64_graphical_media as geometry
import check_x86_64_network_media as check
from run_qemu_x86_64_runtime_clock import once
NAMES=check.NAMES
source=inspect.getsource(geometry.image)
for old,new in [('(16,12)','(16,14)'),('(1<<20)-1','(1<<18)-1'),('u16(2048+14,12)','u16(2048+14,14)')]:
    source=once(source,old,new)
namespace={**vars(geometry),'NAMES':NAMES}
exec(compile(source,'<network-ext2-producer>','exec'),namespace)
image=namespace['image']
selected=check.clone(legacy,[
 ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_network_media.py'),
 ("output/'shell-media.json'","output/'network-media.json'"),
 ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):",
  "for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','netdrv.prg','netstack.prg'):"),
 ("    shell=attempt/'root/bin/shell.prg'",
  "    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
 ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-1k',check.medium_files(values))"),
 ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
  "'system.ext2 is read-only; net, ifconfig, arp and ping use separate Ring3 services.\\n'")],
 'reist_network_producer')
selected.check=check;selected.data=sys.modules[__name__]
inputs=selected.inputs;build=selected.build;publish=selected.publish
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
