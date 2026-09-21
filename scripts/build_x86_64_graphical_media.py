"""Distinct read-only GUI data layout, unchanged signed BIOS boot media."""
from pathlib import Path
import argparse,struct
import build_x86_64_shell_media as legacy
import check_x86_64_graphical_media as check
NAMES=('boot.prg','cat.prg','ls.prg','probe.prg','data.txt','desktop.prg','input.prg','text.prg','paint.prg')

def image(layout,files):
    if layout!='ext2-1k' or type(files) is not dict or set(files)!=set(NAMES):raise ValueError('fixed GUI EXT2 file set')
    for name in NAMES:
        if type(files[name]) is not bytes or not 0<len(files[name])<=(16384 if name=='data.txt' else 274432):raise ValueError('bounded GUI file')
    raw=bytearray(1048576);bs=1024
    def u16(at,v):struct.pack_into('<H',raw,at,v)
    def u32(at,v):struct.pack_into('<I',raw,at,v)
    for at,v in ((0,32),(4,1024),(16,12),(20,1),(24,0),(28,0),(32,1024),(36,1024),
                 (40,32),(76,1),(84,11),(96,2)):u32(1024+at,v)
    for at,v in ((56,0xef53),(58,1),(88,128)):u16(1024+at,v)
    for at,v in ((0,3),(4,4),(8,5)):u32(2048+at,v)
    u32(4*bs,(1<<20)-1)
    root=5*bs+128;u16(root,0x41ed);u32(root+4,bs);u16(root+26,2);u32(root+28,2);u32(root+40,21)
    used=set(range(1,9))|{21};cursor=32
    for n,name in enumerate(NAMES):
        value=files[name];count=(len(value)+1023)//1024;indirect=count>12
        if count>268 or cursor+count>1024:raise ValueError('GUI direct/single-indirect volume capacity')
        inode=5*bs+(11+n)*128;u16(inode,0x81a4);u32(inode+4,len(value));u16(inode+26,1);u32(inode+28,2*(count+indirect))
        for j in range(min(12,count)):u32(inode+40+4*j,cursor+j)
        if indirect:
            block=22+n;used.add(block);u32(inode+88,block)
            for j in range(count-12):u32(block*bs+4*j,cursor+12+j)
        raw[cursor*bs:cursor*bs+len(value)]=value;used.update(range(cursor,cursor+count));cursor+=count
    records=[(2,b'.',2),(2,b'..',2)]+[(12+n,name.encode('ascii'),1) for n,name in enumerate(NAMES)]
    at=21*bs
    for n,(inode,name,kind) in enumerate(records):
        length=((8+len(name)+3)//4)*4 if n<len(records)-1 else 22*bs-at
        u32(at,inode);u16(at+4,length);raw[at+6]=len(name);raw[at+7]=kind;raw[at+8:at+8+len(name)]=name;at+=length
    for block in used:raw[3*bs+(block-1)//8]|=1<<((block-1)%8)
    free=1023-len(used);u32(1024+12,free);u16(2048+12,free);u16(2048+14,12);u16(2048+16,1)
    return bytes(raw)

selected=check.clone(legacy,[
    ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_graphical_media.py'),
    ("output/'shell-media.json'","output/'graphical-media.json'"),
    ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):",
     "for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),'cat.prg','ls.prg','probe.prg','desktop.prg','input.prg','text.prg','paint.prg'):"),
    ("    shell=attempt/'root/bin/shell.prg'",
     "    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
    ("[nasm,'-f','bin',ROOT/('arch/x86/boot/bios/'+name+'.asm')",
     "[nasm,'-f','bin','-DUSE_FRAMEBUFFER=1',ROOT/('arch/x86/boot/bios/'+name+'.asm')"),
    ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-1k',check.medium_files(values))"),
    ("'REIST native shell: bounded two-medium RESEARCH profile, not a finished OS/release.\\n'",
     "'REIST native64 graphical session RESEARCH profile, not a finished OS/release.\\n'"),
    ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'",
     "'system.ext2 is read-only; run desktop in the serial shell to open the GUI.\\n'")],
    'reist_graphical_producer')
import sys
selected.check=check;selected.data=sys.modules[__name__]
inputs=selected.inputs;build=selected.build;publish=selected.publish
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl')
    a=p.parse_args();build(a.input_directory,a.output_directory,a.nasm,a.openssl)
