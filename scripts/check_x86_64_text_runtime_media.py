"""Independent native text formatting consumer; all accepted CLI inputs remain pinned."""
from pathlib import Path
import argparse,inspect
import check_x86_64_shell_media as legacy
import check_x86_64_math_runtime_media as accepted
import check_x86_64_graphical_media as geometry
from check_x86_64_wide_shell_media import clone
from run_qemu_x86_64_runtime_clock import once
from build_user_program import validate_cpp_object
NAMES=(*accepted.NAMES,'texttest.prg')
selected=clone(legacy,[
    ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-text-runtime-two-media-v1'"),
    ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-text-runtime-ext2-1k'"),
    ("'file-program.prg':1280","'file-program.prg':274432,'cat.prg':274432,'ls.prg':274432,'probe.prg':274432,'data.txt':16384,'cpptest.prg':274432,'mathtest.prg':274432,'texttest.prg':274432"),
    ("'system.ext2':131072","'system.ext2':1048576"),('64<=len(app)<=1280','1536<len(app)<=274432'),
    ("directory/'shell-media.json'","directory/'text-runtime-media.json'"),
    ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))",
     "'file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','data.txt','cpptest.prg','mathtest.prg','texttest.prg')"),
    ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])",
     "data_volume(bounded(attempt/'system.ext2',1048576),values)")], 'reist_text_runtime_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json;admit_package=selected.admit_package
PROFILE=selected.PROFILE;FILES=selected.FILES;DEVICES=selected.DEVICES
KERNEL=selected.KERNEL;CORE=selected.CORE;KERNEL_LIMIT=selected.KERNEL_LIMIT;ROOT=selected.ROOT
payload=selected.payload;manifest=selected.manifest;old=selected.old

def input_binding(values):
    need(type(values) is dict and set(values)==set(accepted.accepted.accepted.PINS)|{'cpptest.prg','mathtest.prg','texttest.prg'},'exact native text inputs')
    accepted.input_binding({n:v for n,v in values.items() if n!='texttest.prg'})
    need(__import__('hashlib').sha256(values['cpptest.prg']).hexdigest()==
        'aa785524e096565dad5ae5901309ddef3a5b08abe802d5d7472430a014a72b9e','accepted C++ consumer pin')
    need(__import__('hashlib').sha256(values['mathtest.prg']).hexdigest()=='52da74f04cf7ca7e869c885764e65d82dba199327b1024721562f03311314825','accepted math consumer pin')
    validate_cpp_object(values['texttest.prg'],architecture='x86_64')
    selected.programs.prepare(values['texttest.prg'],[],True)


def medium_files(values):return {n:values['file-program.prg' if n=='boot.prg' else n] for n in NAMES}
source=inspect.getsource(geometry.verify_volume)
source=once(source,'(32,1024,12,1,0,0,1024,1024,32,1,11,2)','(32,1024,13,1,0,0,1024,1024,32,1,11,2)')
source=once(source,"b'\\xff\\xff\\x0f\\x00'","b'\\xff\\xff\\x07\\x00'")
source=once(source,'(free,free,12,1)','(free,free,13,1)')
source=once(source,"'free_inodes':12","'free_inodes':13")
namespace={**vars(geometry),'NAMES':NAMES}
exec(compile(source,'<text-runtime-ext2-consumer>','exec'),namespace)
verify_volume=namespace['verify_volume']
def data_volume(raw,values):return verify_volume(raw,medium_files(values))
selected.input_binding=input_binding;selected.data_volume=data_volume;verify=selected.verify
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('MATH_RUNTIME_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
