"""Signed eight-file native text medium using retained CLI mechanisms."""
from pathlib import Path
import argparse,inspect,sys
import build_x86_64_shell_media as legacy
import build_x86_64_graphical_media as geometry
import check_x86_64_text_runtime_media as check
from run_qemu_x86_64_runtime_clock import once
NAMES=check.NAMES
source=inspect.getsource(geometry.image)
source=once(source,'(16,12)','(16,13)')
source=once(source,'(1<<20)-1','(1<<19)-1')
source=once(source,'u16(2048+14,12)','u16(2048+14,13)')
namespace={**vars(geometry),'NAMES':NAMES}
exec(compile(source,'<text-runtime-ext2-producer>','exec'),namespace)
image=namespace['image']
selected=check.clone(legacy,[
    ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_text_runtime_media.py'),
    ("output/'shell-media.json'","output/'text-runtime-media.json'"),
    ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):",
     "for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','cpptest.prg','mathtest.prg','texttest.prg'):"),
    ("    shell=attempt/'root/bin/shell.prg'",
     "    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
    ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-1k',check.medium_files(values))"),
    ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
     "'system.ext2 is read-only and contains the ordinary native texttest consumer.\\n'")],
    'reist_text_runtime_producer')
selected.check=check;selected.data=sys.modules[__name__]
inputs=selected.inputs;build=selected.build;publish=selected.publish;old=selected.old
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
