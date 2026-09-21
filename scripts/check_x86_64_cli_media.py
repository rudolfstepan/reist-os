"""Exact accepted BC inputs in a separately named signed CLI research profile."""
from pathlib import Path
import argparse,hashlib
import check_x86_64_shell_media as legacy
from check_x86_64_wide_shell_media import clone,once
import check_x86_64_app_files_media as filesystem
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'build/codex-agent/r83bc-application-files/native-app-files-ipc/x86_64'
PINS={
    'reist-x86_64-bootstrap.elf':'f0fe88bc7711257d4af9eec28d73890ffd24b2157a3af9d1d9afb53db84e2730',
    'reist-x86_64-c-core.elf':'65738639762f1caceea2c61f0436467b6a15e75fd782d497c96b8a8e42819458',
    'boot-programs.bin':'dd39e7e4381c2f6cdd45ae3b95800a0d132534966baf436fc39f6f52a1d1a504',
    'file-program.prg':'22ced99f5be0f42e345a9cd1cba0f5c1bfcc0e8c7c6e578bf646c309eeb230da',
    'program0.prg':'eb41492a2475c26003855a6b57c5d4cc45421aa05aab0634c977038bdcb5f9d1',
    'program1.prg':'2d4a362fba07a43d8f4b3583b2a6b6a799c510a8fae71c8efda2641708204a6d',
    'program2.prg':'96f88b4eebe8865a3aa3a75e0407d495f664c19664740ea5e3333421d1364e89',
    'program3.prg':'16cddf76ac48126b5b18c8e044f5a9cfb8c7c2a2319bc7601e018ef77afb0957',
    'cat.prg':'d5535c7b457a41fd076628520fce4cb9d9942874d531b18236c1bfa945a8009e',
    'ls.prg':'6fd8aa33b1c2a69a29e18fd180930fcdb22b86af9e0b120439e6bbfff37d7088',
    'probe.prg':'01570645fb1ac0aaa8ac7f809182dcfeb136ee6c03308fed745ab34ca50672ec',
    'data.txt':'e3df252557f1cb403da4b9f86a5e17a46ba708bca50dd36c6a7992b21b224d24'}
selected=clone(legacy,[
    ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-cli-two-media-v1'"),
    ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-cli-ext2-1k'"),
    ("'file-program.prg':1280","'file-program.prg':274432,\n       'cat.prg':274432,'ls.prg':274432,'probe.prg':274432,'data.txt':16384"),
    ("'system.ext2':131072","'system.ext2':1048576"),
    ('64<=len(app)<=1280','1536<len(app)<=274432'),
    ("directory/'shell-media.json'","directory/'cli-media.json'"),
    ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))",
     "'file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','data.txt')"),
    ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])",
     "data_volume(bounded(attempt/'system.ext2',1048576),values)")], 'reist_cli_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json;admit_package=selected.admit_package
PROFILE=selected.PROFILE;FILES=selected.FILES;DEVICES=selected.DEVICES
KERNEL=selected.KERNEL;CORE=selected.CORE;KERNEL_LIMIT=selected.KERNEL_LIMIT
payload=selected.payload;manifest=selected.manifest;old=selected.old
_input_binding=selected.input_binding

def medium_files(values):
    return {n:values['file-program.prg' if n=='boot.prg' else n] for n in filesystem.NAMES}

def input_binding(values):
    need(type(values) is dict and set(values)==set(PINS),'exact accepted BC twelve inputs')
    for name,sha in PINS.items():
        need(type(values[name]) is bytes and hashlib.sha256(values[name]).hexdigest()==sha,'accepted BC input '+name)
    _input_binding(values)
    for name in ('cat.prg','ls.prg','probe.prg'):selected.programs.prepare(values[name],[],True)

def data_volume(raw,values):
    # Independent full allocation/records/bytes oracle, never calls producer.
    return filesystem.verify(raw,'ext2-1k',medium_files(values))

selected.input_binding=input_binding;selected.data_volume=data_volume
verify=selected.verify

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('CLI_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
