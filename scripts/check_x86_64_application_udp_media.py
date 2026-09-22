"""Independent signed UDP profile consumer; accepted BL profile stays strict."""
from pathlib import Path
import argparse,hashlib,inspect
import check_x86_64_shell_media as legacy
import check_x86_64_graphical_media as geometry
import check_x86_64_cli_media as accepted
from check_x86_64_wide_shell_media import clone
from run_qemu_x86_64_runtime_clock import once
NAMES=('boot.prg','cat.prg','ls.prg','probe.prg','data.txt','netdrv.prg','netstack.prg','udp.prg')
selected=clone(legacy,[
 ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-application-udp-two-media-v1'"),
 ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-application-udp-ext2-1k'"),
 ("'file-program.prg':1280","'file-program.prg':274432, 'cat.prg':274432, 'ls.prg':274432, 'probe.prg':274432, 'data.txt':16384, 'netdrv.prg':274432, 'netstack.prg':274432, 'udp.prg':274432"),
 ("'system.ext2':131072","'system.ext2':1048576"),('64<=len(app)<=1280','1536<len(app)<=274432'),
 ("directory/'shell-media.json'","directory/'application-udp-media.json'"),
 ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))",
  "'file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','data.txt','netdrv.prg','netstack.prg','udp.prg')"),
 ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])",
  "data_volume(bounded(attempt/'system.ext2',1048576),values)")],'reist_application_udp_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json
PROFILE=selected.PROFILE;FILES=selected.FILES;DEVICES=selected.DEVICES
KERNEL=selected.KERNEL;CORE=selected.CORE;ROOT=selected.ROOT
_input_binding=selected.input_binding
def input_binding(values):
    need(set(values)==set(accepted.PINS)|{'netdrv.prg','netstack.prg','udp.prg'},'exact UDP profile files')
    _input_binding(values)
    for name in ('program1.prg','program2.prg','program3.prg','cat.prg','ls.prg','probe.prg','data.txt'):
        need(hashlib.sha256(values[name]).hexdigest()==accepted.PINS[name],'unchanged independent program '+name)
    hashes=b''.join(hashlib.sha256(selected.programs.prepare(values[name],[],True)[:262240]).digest()
                    for name in ('netdrv.prg','netstack.prg'))
    need(values['program0.prg'].count(hashes)==1,'signed root binds exact network roles')
    selected.programs.prepare(values['udp.prg'],[],True)
    symbols=selected.payload.elf(values[KERNEL],32)['symbols']
    need(all(n in symbols for n in ('native_network_syscall64','native_network_emergency64','native_terminal_syscall64')),'actual combined mechanisms')
def medium_files(values):return {n:values['file-program.prg' if n=='boot.prg' else n] for n in NAMES}
source=inspect.getsource(geometry.verify_volume)
for old,new in [('(32,1024,12,1,','(32,1024,13,1,'),
                ("b'\\xff\\xff\\x0f\\x00'","b'\\xff\\xff\\x07\\x00'"),
                ("'exact20 allocated inodes'","'exact19 allocated inodes'"),
                ('(free,free,12,1)','(free,free,13,1)'),("'free_inodes':12","'free_inodes':13")]:
    source=once(source,old,new)
namespace={**vars(geometry),'NAMES':NAMES}
exec(compile(source,'<application-udp-ext2-consumer>','exec'),namespace)
verify_volume=namespace['verify_volume']
def data_volume(raw,values):return verify_volume(raw,medium_files(values))
selected.input_binding=input_binding;selected.data_volume=data_volume
verify=selected.verify
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('APPLICATION_UDP_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
