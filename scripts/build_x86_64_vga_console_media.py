"""Signed text-mode BIOS packaging using the accepted CLI layouts."""
from pathlib import Path
import argparse
import build_x86_64_cli_media as legacy
from check_x86_64_wide_shell_media import clone

selected=clone(legacy,[
    ('import check_x86_64_cli_media as check','import check_x86_64_vga_console_media as check'),
    ('scripts/check_x86_64_cli_media.py','scripts/check_x86_64_vga_console_media.py'),
    ("output/'cli-media.json'","output/'vga-console-media.json'"),
    ('REIST native64 CLI: bounded two-medium RESEARCH delivery, not a production OS.',
     'REIST native64 VGA console: unaccepted research candidate; actual mode03 text shell.'),
    ('Run scripts/start-x86_64-cli.ps1; session320s maximum, two shell runs then halt.',
     'Use only the bounded VGA-console qualifier; desktop transition remains outstanding.'),
    ("'reist_cli_producer'","'reist_vga_producer'")],'reist_vga_media_builder')
inputs=selected.inputs;publish=selected.publish;build=selected.build
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
