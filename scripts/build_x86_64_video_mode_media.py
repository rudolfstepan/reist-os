"""Signed text-first CK media; no early BIOS graphics switch."""
from pathlib import Path
import argparse
import build_x86_64_cli_media as legacy
import build_x86_64_app_files_media as data_base
import check_x86_64_video_mode_media as check
data=check.clone(data_base,[("'probe.prg','data.txt')","'probe.prg','data.txt','video.prg')"),
    ('at=5*bs+(11+n)*128','at=5*bs+(11+n if n<5 else 10)*128'),
    ("(12+n,name.encode(),1)","(12+n if n<5 else 11,name.encode(),1)")],'reist_ck_data_producer')
selected=check.clone(legacy,[
    ('import check_x86_64_cli_media as check','import check_x86_64_video_mode_media as check'),
    ('scripts/check_x86_64_cli_media.py','scripts/check_x86_64_video_mode_media.py'),
    ("output/'cli-media.json'","output/'video-mode-media.json'"),
    ("'cat.prg','ls.prg','probe.prg'):","'cat.prg','ls.prg','probe.prg','video.prg'):"),
    ('REIST native64 CLI: bounded two-medium RESEARCH delivery, not a production OS.',
     'REIST native64 mode-transition prerequisite, not the complete desktop.'),
    ('Run scripts/start-x86_64-cli.ps1; session320s maximum, two shell runs then halt.',
     'Boot real VGA text shell; VIDEO exercises a bounded graphics/text transition.'),
    ("'reist_cli_producer'","'reist_ck_producer'")],'reist_ck_media_builder')
selected.selected.data=data
inputs=selected.inputs;publish=selected.publish;build=selected.build
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
