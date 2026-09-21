"""Package accepted binaries; only the three existing BIOS stages are assembled."""
from pathlib import Path
import argparse
import build_x86_64_shell_media as legacy
import build_x86_64_app_files_media as data
import check_x86_64_cli_media as check
selected=check.clone(legacy,[
    ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_cli_media.py'),
    ("output/'shell-media.json'","output/'cli-media.json'"),
    ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):",
     "for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg'):"),
    ("    shell=attempt/'root/bin/shell.prg'", "    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
    ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-1k',check.medium_files(values))"),
    ("'REIST native shell: bounded two-medium RESEARCH profile, not a finished OS/release.\\n'",
     "'REIST native64 CLI: bounded two-medium RESEARCH delivery, not a production OS.\\n'"),
    ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
     "'system.ext2: primary ATA master, read-only1MiB EXT2, boot/cat/ls/probe.prg and data.txt.\\n'\n"
     "        'Run scripts/start-x86_64-cli.ps1; session320s maximum, two shell runs then halt.\\n'")],
    'reist_cli_producer')
selected.check=check;selected.data=data
inputs=selected.inputs;publish=selected.publish;build=selected.build;old=selected.old

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
