"""Independent signed GUI package and fixed EXT2 consumer; no producer imports."""
from pathlib import Path
import argparse,hashlib,struct
import check_x86_64_shell_media as legacy
import check_x86_64_terminal_service_media as prior
from check_x86_64_wide_shell_media import clone
NAMES=('boot.prg','cat.prg','ls.prg','probe.prg','data.txt','desktop.prg','input.prg','text.prg','paint.prg')
selected=clone(legacy,[
    ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-graphical-session-two-media-v1'"),
    ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-gui-ext2-1k'"),
    ("'runtime_program':'/boot.prg'","'runtime_program':'/desktop.prg'"),
    ("'file-program.prg':1280","'file-program.prg':274432,\n       'cat.prg':274432,'ls.prg':274432,'probe.prg':274432,'data.txt':16384,\n       'desktop.prg':274432,'input.prg':274432,'text.prg':274432,'paint.prg':274432"),
    ("'system.ext2':131072","'system.ext2':1048576"),
    ('64<=len(app)<=1280','1536<len(app)<=274432'),
    ("directory/'shell-media.json'","directory/'graphical-media.json'"),
    ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))",
     "'file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','data.txt','desktop.prg','input.prg','text.prg','paint.prg')"),
    ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])",
     "data_volume(bounded(attempt/'system.ext2',1048576),values)")],
    'reist_graphical_consumer')
need=selected.need;bounded=selected.bounded;exact_path=selected.exact_path
digest=selected.digest;object_json=selected.object_json;PROFILE=selected.PROFILE
FILES=selected.FILES;DEVICES=selected.DEVICES;ROOT=selected.ROOT
KERNEL=selected.KERNEL;CORE=selected.CORE;KERNEL_LIMIT=selected.KERNEL_LIMIT
payload=selected.payload;old=selected.old

def medium_files(values):return {name:values['file-program.prg' if name=='boot.prg' else name] for name in NAMES}

def input_binding(values):
    expected=set(prior.accepted.PINS)|{'desktop.prg','input.prg','text.prg','paint.prg'}
    need(type(values) is dict and set(values)==expected,'exact sixteen graphical inputs')
    prior.input_binding({name:values[name] for name in prior.accepted.PINS})
    manifest=b''
    for name in ('desktop.prg','input.prg','text.prg','paint.prg'):
        raw=values[name];need(type(raw) is bytes and 64<=len(raw)<=274432,'bounded native role '+name)
        prepared=selected.programs.prepare(raw,[],True)
        manifest+=hashlib.sha256(prepared[:262240]).digest()
    need(values['program0.prg'].count(manifest)==1,'exact role digests bound in signed root')
    need(b'GRAPHICAL_READY\n' in values['program0.prg'],'actual GUI shell integration')
    need(values['text.prg']!=values['paint.prg'],'two separate ordinary client programs')

def verify_volume(raw,files):
    need(type(raw) is bytes and len(raw)==1048576,'fixed GUI volume extent')
    need(type(files) is dict and set(files)==set(NAMES),'exact GUI files')
    u16=lambda at:struct.unpack_from('<H',raw,at)[0]
    u32=lambda at:struct.unpack_from('<I',raw,at)[0]
    need(tuple(u32(1024+n) for n in (0,4,16,20,24,28,32,36,40,76,84,96))==
         (32,1024,12,1,0,0,1024,1024,32,1,11,2),'GUI EXT2 geometry/features')
    need((u16(1080),u16(1082),u16(1112))==(0xef53,1,128),'GUI EXT2 revision/inode size')
    need(tuple(u32(2048+n) for n in (0,4,8))==(3,4,5),'GUI metadata positions')
    need(raw[4096:4100]==b'\xff\xff\x0f\x00' and not any(raw[4100:5120]),'exact20 allocated inodes')
    root=5*1024+128
    need((u16(root),u32(root+4),u16(root+26),u32(root+28),u32(root+40))==(0x41ed,1024,2,2,21),'root inode')
    cursor=21*1024
    entries=[(2,b'.',2),(2,b'..',2)]+[(12+n,name.encode('ascii'),1) for n,name in enumerate(NAMES)]
    for n,(inode,name,kind) in enumerate(entries):
        length=((8+len(name)+3)//4)*4 if n<len(entries)-1 else 22*1024-cursor
        need((u32(cursor),u16(cursor+4),raw[cursor+6],raw[cursor+7])==(inode,length,len(name),kind),
             'exact directory record '+name.decode())
        need(raw[cursor+8:cursor+8+len(name)]==name and not any(raw[cursor+8+len(name):cursor+length]),'directory text/padding')
        cursor+=length
    used=set(range(1,9))|{21};first=32
    for n,name in enumerate(NAMES):
        value=files[name];need(type(value) is bytes and 0<len(value)<=(16384 if name=='data.txt' else 274432),'GUI object size')
        count=(len(value)+1023)//1024;indirect=count>12;inode=5120+(11+n)*128
        need(count<=268 and first+count<=1024,'single-indirect file bounds')
        need((u16(inode),u32(inode+4),u16(inode+26),u32(inode+28))==
             (0x81a4,len(value),1,2*(count+indirect)),'file inode '+name)
        for j in range(12):need(u32(inode+40+j*4)==(first+j if j<count else 0),'direct block identity')
        need(u32(inode+88)==(22+n if indirect else 0) and not any(raw[inode+92:inode+100]),'indirection pointers')
        if indirect:
            block=22+n;used.add(block)
            for j in range(256):need(u32(block*1024+4*j)==(first+12+j if j<count-12 else 0),'indirect extent/padding')
        need(raw[first*1024:first*1024+len(value)]==value and
             not any(raw[first*1024+len(value):(first+count)*1024]),'all file bytes/padding '+name)
        used.update(range(first,first+count));first+=count
    for block in range(1,1025):
        bit=block-1;need(bool(raw[3072+bit//8]&(1<<(bit%8)))==(block in used),'exact block bitmap')
    need(not any(raw[3200:4096]),'block bitmap tail')
    free=1023-len(used)
    need((u32(1036),u16(2060),u16(2062),u16(2064))==(free,free,12,1),'exact free counts')
    # Any unallocated data block remains zero, including the unused indirect slots.
    for block in range(9,1024):
        if block not in used:need(not any(raw[block*1024:(block+1)*1024]),'unallocated block zero')
    return {'files':len(files),'allocated_blocks':len(used),'free_inodes':12}

def data_volume(raw,values):return verify_volume(raw,medium_files(values))
selected.input_binding=input_binding;selected.data_volume=data_volume
verify=selected.verify
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
    print('GRAPHICAL_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
