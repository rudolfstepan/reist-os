"""Explicit graphics stage2 selection, existing signing/layouts and read-only data."""
from pathlib import Path
import argparse
import build_x86_64_shell_media as legacy
import build_x86_64_app_files_media as data
import check_x86_64_display_media as check
selected=check.clone(legacy,[
 ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_display_media.py'),
 ("output/'shell-media.json'","output/'display-media.json'"),
 ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):",
  "for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg'):"),
 ("    shell=attempt/'root/bin/shell.prg'","    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
 ("[nasm,'-f','bin',ROOT/('arch/x86/boot/bios/'+name+'.asm')",
  "[nasm,'-f','bin','-DUSE_FRAMEBUFFER=1',ROOT/('arch/x86/boot/bios/'+name+'.asm')"),
 ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-1k',check.medium_files(values))"),
 ("'REIST native shell: bounded two-medium RESEARCH profile, not a finished OS/release.\\n'",
  "'REIST native64 DISPLAY research profile; bounded Ring3 tiles and serial shell.\\n'"),
 ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
  "'system.ext2: read-only primary master; /boot.prg is the explicit display client.\\n'")],
 'reist_display_producer')
selected.check=check;selected.data=data
inputs=selected.inputs;publish=selected.publish;build=selected.build
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
