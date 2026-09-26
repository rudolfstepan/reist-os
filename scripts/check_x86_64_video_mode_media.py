"""Independent signed native mode media consumer, normal /video.prg dispatch."""
from pathlib import Path
import argparse,hashlib
import check_x86_64_shell_media as legacy
from check_x86_64_wide_shell_media import clone
import check_x86_64_app_files_media as files_base
import check_x86_64_cli_media as accepted
ROOT=Path(__file__).resolve().parents[1]
filesystem=clone(files_base,[("'probe.prg','data.txt')","'probe.prg','data.txt','video.prg')"),
    ("len(entries)<=7","len(entries)<=8"),
    ('at=5*bs+(11+i)*128','at=5*bs+(11+i if i<5 else 10)*128'),
    ("(12+i,n.encode(),1)","(12+i if i<5 else 11,n.encode(),1)")], 'reist_ck_files')
selected=clone(legacy,[
    ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-video-mode-two-media-v1'"),
    ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-cli-ext2-1k'"),
    ("'file-program.prg':1280","'file-program.prg':274432,\n       'cat.prg':274432,'ls.prg':274432,'probe.prg':274432,'video.prg':274432,'data.txt':16384"),
    ("'system.ext2':131072","'system.ext2':1048576"),
    ('64<=len(app)<=1280','1536<len(app)<=274432'),
    ("directory/'shell-media.json'","directory/'video-mode-media.json'"),
    ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))",
     "'file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','data.txt','video.prg')"),
    ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])",
     "data_volume(bounded(attempt/'system.ext2',1048576),values)")],'reist_ck_media_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json;admit_package=selected.admit_package
PROFILE=selected.PROFILE;FILES=selected.FILES;DEVICES=selected.DEVICES
KERNEL=selected.KERNEL;CORE=selected.CORE;KERNEL_LIMIT=selected.KERNEL_LIMIT
payload=selected.payload;manifest=selected.manifest;old=selected.old
INPUT_NAMES=(*accepted.PINS,'video.prg')
def medium_files(values):
    return {n:values['file-program.prg' if n=='boot.prg' else n] for n in filesystem.NAMES}
original_binding=selected.input_binding
def input_binding(values):
    need(type(values) is dict and set(values)==set(INPUT_NAMES),'exact CK inputs')
    original_binding(values)
    for name in ('file-program.prg','program1.prg','program2.prg','program3.prg',
                 'cat.prg','ls.prg','probe.prg','data.txt'):
        need(hashlib.sha256(values[name]).hexdigest()==accepted.PINS[name],'unchanged dependency '+name)
    symbols=payload.elf(values[KERNEL],32)['symbols']
    for name in ('native_video_syscall64','native_video_terminal64','native_display_boot','native_vga_state'):
        need(name in symbols,'mode mechanism '+name)
    for name in ('cat.prg','ls.prg','probe.prg','video.prg'):
        selected.programs.prepare(values[name],[],True)
def data_volume(raw,values):return filesystem.verify(raw,'ext2-1k',medium_files(values))
selected.input_binding=input_binding;selected.data_volume=data_volume
verify=selected.verify
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('VIDEO_MODE_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
