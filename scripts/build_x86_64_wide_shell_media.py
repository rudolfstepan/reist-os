"""Package only the accepted BA artifacts, never rebuild a kernel."""
from pathlib import Path
import argparse
import build_x86_64_shell_media as legacy
import build_x86_64_wide_file_media as data
import check_x86_64_wide_shell_media as check
selected=check.clone(legacy,[
    ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_wide_shell_media.py'),
    ("output/'shell-media.json'","output/'wide-shell-media.json'"),
    ("'REIST native shell: bounded two-medium RESEARCH profile, not a finished OS/release.\\n'",
     "'REIST wide native shell: bounded two-medium RESEARCH profile, not a finished OS/release.\\n'"),
    ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
     "'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'\n"
     "        '1MiB EXT2-1k, direct/single-indirect only; no full512KiB claim on this volume.\\n'")],
    'reist_wide_shell_producer')
selected.check=check;selected.data=data
inputs=selected.inputs;publish=selected.publish;build=selected.build;old=selected.old

MAKE_BLOCK=('# BB packaging only: exact accepted WideFile input; no kernel dependency.\n'
    '.PHONY: x86_64-wide-shell-media\n'
    'X86_64_WIDE_SHELL_MEDIA_INPUT ?= build/x86_64\n'
    'X86_64_WIDE_SHELL_MEDIA_OUTPUT ?= build/codex-agent/native-wide-shell-media\n'
    'x86_64-wide-shell-media:\n'
    '\t@$(PYTHON) scripts/build_x86_64_wide_shell_media.py --input-directory "$(X86_64_WIDE_SHELL_MEDIA_INPUT)" --output-directory "$(X86_64_WIDE_SHELL_MEDIA_OUTPUT)" --nasm "$(AS)" --openssl "$(OPENSSL)"\n'
    '# End BB packaging-only target.\n\n')

def without_wide_media_target(source):
    tokens=('WIDE_SHELL_MEDIA','wide-shell-media','wide_shell_media')
    if not any(t in source for t in tokens):return source
    result=check.once(source,MAKE_BLOCK,'')
    check.need(not any(t in result for t in tokens),'unexpected BB packaging use')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
