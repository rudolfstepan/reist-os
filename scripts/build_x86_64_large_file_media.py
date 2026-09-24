"""Explicit immutable BV EXT2 geometry with unchanged signed BIOS mechanisms."""
from pathlib import Path
import argparse,struct,sys,types
import build_x86_64_shell_media as legacy
import check_x86_64_large_file_media as check
from check_x86_64_wide_shell_media import clone
NAMES=check.NAMES

def admit(files):
 if type(files) is not dict or set(files)!=set(NAMES):raise ValueError('BV fixed file set')
 for name,value in files.items():
  limit=16384 if name=='data.txt' else 1048576 if name=='largetest.prg' else 274432
  if type(value) is not bytes or not 0<len(value)<=limit:raise ValueError('BV bounded file '+name)

def fat_image(layout,files):
 """Retain the existing FAT geometry/chain producer with the explicit file set."""
 import build_x86_64_app_files_media as previous
 admit(files)
 if layout not in ('fat12','fat32'):raise ValueError('BV FAT layout')
 # The unchanged FAT producer uses standard 8.3 short names, without LFN.
 disk_files={('largetst.prg' if n=='largetest.prg' else n):v for n,v in files.items()}
 names=tuple('largetst.prg' if n=='largetest.prg' else n for n in NAMES)
 def admit_disk(values):
  if set(values)!=set(names):raise ValueError('BV FAT short-name set')
  admit({('largetest.prg' if n=='largetst.prg' else n):v for n,v in values.items()})
 namespace=dict(vars(previous),NAMES=names,admit=admit_disk)
 return types.FunctionType(previous.image.__code__,namespace)(layout,disk_files)

def image(layout,files):
 if layout in ('fat12','fat32'):return fat_image(layout,files)
 if layout not in ('ext2-2k','ext2-4k') or type(files) is not dict or set(files)!=set(NAMES):raise ValueError('BV fixed file set/layout')
 bs=2048 if layout=='ext2-2k' else 4096;raw=bytearray(2097152);total=len(raw)//bs;log=1 if bs==2048 else 2
 def u16(at,v):struct.pack_into('<H',raw,at,v)
 def u32(at,v):struct.pack_into('<I',raw,at,v)
 for at,v in ((0,32),(4,total),(16,12),(20,0),(24,log),(28,log),(32,total),(36,total),(40,32),(76,1),(84,11),(96,2)):u32(1024+at,v)
 for at,v in ((56,0xef53),(58,1),(88,128)):u16(1024+at,v)
 for at,v in ((0,3),(4,4),(8,5)):u32(bs+at,v)
 u32(4*bs,(1<<20)-1)
 root=5*bs+128;u16(root,0x41ed);u32(root+4,bs);u16(root+26,2);u32(root+28,bs//512);u32(root+40,21)
 used=set(range(5+4096//bs))|{21};cursor=32
 for n,name in enumerate(NAMES):
  value=files[name];limit=16384 if name=='data.txt' else 1048576 if name=='largetest.prg' else 274432
  if type(value) is not bytes or not 0<len(value)<=limit:raise ValueError('BV bounded file')
  count=(len(value)+bs-1)//bs;indirect=count>12
  if count>12+bs//4 or cursor+count>total:raise ValueError('BV single indirect capacity')
  inode=5*bs+(11+n)*128;u16(inode,0x81a4);u32(inode+4,len(value));u16(inode+26,1);u32(inode+28,(bs//512)*(count+indirect))
  for j in range(min(12,count)):u32(inode+40+4*j,cursor+j)
  if indirect:
   block=22+n;used.add(block);u32(inode+88,block)
   for j in range(count-12):u32(block*bs+4*j,cursor+12+j)
  raw[cursor*bs:cursor*bs+len(value)]=value;used.update(range(cursor,cursor+count));cursor+=count
 entries=[(2,b'.',2),(2,b'..',2)]+[(12+n,name.encode(),1) for n,name in enumerate(NAMES)];at=21*bs
 for n,(inode,name,kind) in enumerate(entries):
  length=(8+len(name)+3)//4*4 if n<len(entries)-1 else 22*bs-at
  u32(at,inode);u16(at+4,length);raw[at+6]=len(name);raw[at+7]=kind;raw[at+8:at+8+len(name)]=name;at+=length
 for block in used:raw[3*bs+block//8]|=1<<(block%8)
 free=total-len(used);u32(1036,free);u16(bs+12,free);u16(bs+14,12);u16(bs+16,1)
 return bytes(raw)

selected=clone(legacy,[
 ('scripts/check_x86_64_shell_media.py','scripts/check_x86_64_large_file_media.py'),
 ("output/'shell-media.json'","output/'large-file-media.json'"),
 ("for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4))):","for name in ('file-program.prg',*(f'program{n}.prg' for n in range(4)),*(n for n in check.EXTRA if n!='data.txt')):"),
 ("    shell=attempt/'root/bin/shell.prg'","    values['data.txt']=check.bounded(check.exact_path(check.exact_path(attempt,'root'),'data.txt'),16384)\n    shell=attempt/'root/bin/shell.prg'"),
 ("data.image('ext2-1k',program=values['file-program.prg'])","data.image('ext2-2k',check.medium_files(values))"),
 ("'system.ext2 is the separate primary ATA master, read-only, containing /boot.prg.\\n'","'system.ext2 is read-only EXT2-2k containing the ordinary largetest consumer.\\n'")], 'reist_large_file_producer')
selected.check=check;selected.data=sys.modules[__name__]
inputs=selected.inputs;build=selected.build;publish=selected.publish;old=selected.old
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-directory',type=Path,required=True);p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--nasm');p.add_argument('--openssl');a=p.parse_args()
 build(a.input_directory,a.output_directory,a.nasm,a.openssl)
