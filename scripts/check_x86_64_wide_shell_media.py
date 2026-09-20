"""Independent selected-profile consumer; old signed package stays strict."""
from pathlib import Path
import argparse,hashlib,inspect,linecache,struct,types
import check_x86_64_shell_media as legacy
from run_qemu_x86_64_runtime_clock import once
PINS={
    'reist-x86_64-bootstrap.elf':'2fb2abf870364be311cc69d2979215b9c28fb7703ed2100c5828e37db5314df9',
    'reist-x86_64-c-core.elf':'01ab8aa79f9f09c80158ecf915d6b36c59648cc450d9941313ed25ab0ac86a34',
    'boot-programs.bin':'e4df048cbcb83bd7ebe32f9c8144bde3a25ca517977545b3fcc3928fa7c64e41',
    'file-program.prg':'22ced99f5be0f42e345a9cd1cba0f5c1bfcc0e8c7c6e578bf646c309eeb230da',
    'program0.prg':'c7973a7030f7a7a40f4833a9d28320291cf72ce6c1f9a5e282d8fac5f4ff217c',
    'program1.prg':'2d4a362fba07a43d8f4b3583b2a6b6a799c510a8fae71c8efda2641708204a6d',
    'program2.prg':'96f88b4eebe8865a3aa3a75e0407d495f664c19664740ea5e3333421d1364e89',
    'program3.prg':'16cddf76ac48126b5b18c8e044f5a9cfb8c7c2a2319bc7601e018ef77afb0957'}

def clone(module,changes,name):
    source=Path(module.__file__).read_text(encoding='utf-8')
    for before,after in changes:source=once(source,before,after)
    filename='<'+name+'>';result=types.ModuleType(name);result.__file__=module.__file__
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    exec(compile(source,filename,'exec'),result.__dict__)
    return result

selected=clone(legacy,[
    ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-wide-shell-two-media-v1'"),
    ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-wide-ext2-1k'"),
    ("'file-program.prg':1280","'file-program.prg':274432"),
    ("'system.ext2':131072","'system.ext2':1048576"),
    ('64<=len(app)<=1280','1536<len(app)<=274432'),
    ("directory/'shell-media.json'","directory/'wide-shell-media.json'"),
    ("data_volume(bounded(attempt/'system.ext2',131072)","data_volume(bounded(attempt/'system.ext2',1048576)")],
    'reist_wide_shell_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json;admit_package=selected.admit_package
PROFILE=selected.PROFILE;FILES=selected.FILES;DEVICES=selected.DEVICES
KERNEL=selected.KERNEL;CORE=selected.CORE;KERNEL_LIMIT=selected.KERNEL_LIMIT
payload=selected.payload;manifest=selected.manifest;old=selected.old
_input_binding=selected.input_binding

def input_binding(values):
    need(set(values)==set(PINS),'exact admitted BA inputs')
    for name,sha in PINS.items():need(hashlib.sha256(values[name]).hexdigest()==sha,'accepted BA input '+name)
    _input_binding(values)

def data_volume(raw,app):
    """Independent complete canonical EXT2 grammar, including unused bytes.

    No producer call: validate the fixed geometry, bitmap accounting, inode and
    directory records, direct/single-indirect pointers and actual data bytes.
    Remaining bytes must be zero; no hidden allocation or double-indirect alias.
    """
    need(type(raw) is bytes and len(raw)==1048576 and type(app) is bytes and
         1536<len(app)<=274432,'wide EXT2 extents')
    count=(len(app)+1023)//1024;indirect=int(count>12)
    occupied=set(range(1,7))|{21}|set(range(32,32+count))
    if indirect:occupied.add(22)
    remaining=bytearray(raw)
    def expect(at,want):
        need(raw[at:at+len(want)]==want,'wide EXT2 field/data at '+str(at))
        remaining[at:at+len(want)]=bytes(len(want))
    sb=bytearray(1024)
    for at,value in ((0,16),(4,1024),(12,1023-len(occupied)),(16,4),(20,1),(24,0),(28,0),
                     (32,1024),(36,1024),(40,16),(76,1),(84,11),(96,2)):
        struct.pack_into('<I',sb,at,value)
    for at,value in ((56,0xef53),(58,1),(88,128)):struct.pack_into('<H',sb,at,value)
    expect(1024,sb)
    gd=bytearray(1024);struct.pack_into('<3I3H',gd,0,3,4,5,1023-len(occupied),4,1);expect(2048,gd)
    bitmap=bytearray(1024)
    for block in occupied:bitmap[(block-1)//8]|=1<<((block-1)%8)
    expect(3072,bitmap);expect(4096,b'\xff\x0f'+bytes(1022))
    for number,mode,size,links,blocks in ((2,0x41ed,1024,2,[21]),
        (12,0x81a4,len(app),1,list(range(32,32+min(count,12)))+([22] if indirect else []))):
        inode=bytearray(128);struct.pack_into('<H',inode,0,mode);struct.pack_into('<I',inode,4,size)
        struct.pack_into('<H',inode,26,links)
        struct.pack_into('<I',inode,28,2 if number==2 else (count+indirect)*2)
        for n,block in enumerate(blocks):struct.pack_into('<I',inode,40+4*n,block)
        expect(5*1024+(number-1)*128,inode)
    directory=bytearray(1024);offset=0
    for ino,name,length,kind in ((2,b'.',12,2),(2,b'..',12,2),(12,b'boot.prg',1000,1)):
        struct.pack_into('<IHBB',directory,offset,ino,length,len(name),kind)
        directory[offset+8:offset+8+len(name)]=name;offset+=length
    expect(21*1024,directory)
    if indirect:
        table=bytearray(1024)
        for n in range(count-12):struct.pack_into('<I',table,n*4,44+n)
        expect(22*1024,table)
    expect(32*1024,app+bytes(count*1024-len(app)))
    need(not any(remaining),'wide EXT2 unused bytes/padding')

selected.input_binding=input_binding;selected.data_volume=data_volume
verify=selected.verify

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('WIDE_SHELL_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
