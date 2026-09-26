"""Independent signed BIOS text-media consumer; no graphics selector."""
from pathlib import Path
import argparse
import hashlib
import check_x86_64_shell_media as legacy
from check_x86_64_wide_shell_media import clone
import check_x86_64_app_files_media as filesystem
import check_x86_64_cli_media as accepted

ROOT=Path(__file__).resolve().parents[1]
selected=clone(legacy,[
    ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-vga-console-two-media-v1'"),
    ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-cli-ext2-1k'"),
    ("'file-program.prg':1280","'file-program.prg':274432,\n       'cat.prg':274432,'ls.prg':274432,'probe.prg':274432,'data.txt':16384"),
    ("'system.ext2':131072","'system.ext2':1048576"),
    ('64<=len(app)<=1280','1536<len(app)<=274432'),
    ("directory/'shell-media.json'","directory/'vga-console-media.json'"),
    ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))",
     "'file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','data.txt')"),
    ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])",
     "data_volume(bounded(attempt/'system.ext2',1048576),values)")],'reist_vga_media_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json;admit_package=selected.admit_package
PROFILE=selected.PROFILE;FILES=selected.FILES;DEVICES=selected.DEVICES
KERNEL=selected.KERNEL;CORE=selected.CORE;KERNEL_LIMIT=selected.KERNEL_LIMIT
payload=selected.payload;manifest=selected.manifest;old=selected.old


def medium_files(values):
    return {n:values['file-program.prg' if n=='boot.prg' else n] for n in filesystem.NAMES}


def input_binding(values):
    need(type(values) is dict and set(values)==set(accepted.PINS),'exact VGA inputs')
    selected_original_binding(values)
    for name in ('file-program.prg','program1.prg','program2.prg','program3.prg',
                 'cat.prg','ls.prg','probe.prg','data.txt'):
        need(hashlib.sha256(values[name]).hexdigest()==accepted.PINS[name],
             'unchanged accepted application/service '+name)
    symbols=payload.elf(values[KERNEL],32)['symbols']
    for name in ('native_vga_state','native_vga_syscall64','native_vga_terminal64',
                 'native_vga_status64','native_input_state','native_input_syscall64'):
        need(name in symbols,'VGA mechanism '+name)
    need('native_display_boot' not in symbols,'text-only kernel')
    for name in ('cat.prg','ls.prg','probe.prg'):
        selected.programs.prepare(values[name],[],True)


def data_volume(raw,values):
    return filesystem.verify(raw,'ext2-1k',medium_files(values))


selected_original_binding=selected.input_binding
selected.input_binding=input_binding;selected.data_volume=data_volume
verify=selected.verify
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('VGA_CONSOLE_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
