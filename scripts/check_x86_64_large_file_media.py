"""Independent signed BV input and immutable EXT2 consumer."""
from pathlib import Path
import argparse,hashlib,struct,inspect
import check_x86_64_shell_media as legacy
import check_x86_64_cli_media as cli
from check_x86_64_wide_shell_media import clone
from build_x86_64_large_image import prepare as large_prepare
NAMES=('boot.prg','cat.prg','ls.prg','probe.prg','data.txt','cpptest.prg','mathtest.prg','texttest.prg','largetest.prg')
EXTRA=tuple(n for n in NAMES if n!='boot.prg')
selected=clone(legacy,[
 ("PROFILE='research-native-shell-two-media-v1'","PROFILE='research-native-large-file-two-media-v1'"),
 ("'data':'primary-master-read-only-ext2-1k'","'data':'primary-master-read-only-large-file-ext2-2k'"),
 ("'file-program.prg':1280","'file-program.prg':274432,"+','.join(repr(n)+':'+str(16384 if n=='data.txt' else 1048576 if n=='largetest.prg' else 274432) for n in EXTRA)),
 ("'system.ext2':131072","'system.ext2':2097152"),
 ('64<=len(app)<=1280','1536<len(app)<=274432'),
 ("payload.verify_outer(inner,kernel)","payload.verify_outer(inner,kernel,large_image=True)"),
 ("payload.elf(kernel,32)","payload.elf(kernel,32,large_image=True)"),
 ("directory/'shell-media.json'","directory/'large-file-media.json'"),
 ("'file-program.prg',*(f'program{n}.prg' for n in range(4)))","'file-program.prg',*(f'program{n}.prg' for n in range(4)),*EXTRA)"),
 ("data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])","data_volume(bounded(attempt/'system.ext2',2097152),values)")], 'reist_large_file_consumer')
selected.EXTRA=EXTRA
for name in ('need','bounded','exact_path','digest','object_json','admit_package','PROFILE','FILES','DEVICES','KERNEL','CORE','KERNEL_LIMIT','ROOT','payload','manifest','old'):
 globals()[name]=getattr(selected,name)
base_binding=selected.input_binding

def input_binding(values):
 need(type(values) is dict and set(values)=={KERNEL,CORE,'boot-programs.bin','file-program.prg',*(f'program{n}.prg' for n in range(4)),*EXTRA},'BV exact inputs')
 base_binding(values)
 for name in ('file-program.prg','cat.prg','ls.prg','probe.prg','data.txt'):
  need(hashlib.sha256(values[name]).hexdigest()==cli.PINS[name],'retained CLI input '+name)
 pins={'texttest.prg':'be18943f25d49132a082592a9dae4a9d479d74d81973940b7e1d59aa48efc88f','cpptest.prg':'aa785524e096565dad5ae5901309ddef3a5b08abe802d5d7472430a014a72b9e','mathtest.prg':'52da74f04cf7ca7e869c885764e65d82dba199327b1024721562f03311314825'}
 for name,sha in pins.items():need(hashlib.sha256(values[name]).hexdigest()==sha,'retained runtime '+name)
 for name in EXTRA:
  if name!='data.txt':large_prepare(values[name],[])
 need(len(values['largetest.prg'])==1048576,'exact large consumer boundary')

def medium_files(values):return {n:values['file-program.prg' if n=='boot.prg' else n] for n in NAMES}

def verify_volume(raw,files,layout='ext2-2k'):
 if layout in ('fat12','fat32'):
  import check_x86_64_app_files_media as previous
  source=inspect.getsource(previous.verify)
  old="16384 if name=='data.txt' else 274432"
  need(source.count(old)==1,'BV independent FAT input bound binding')
  need(type(files) is dict and set(files)==set(NAMES),'BV FAT exact logical file set')
  source=source.replace(old,"16384 if name=='data.txt' else 1048576 if name=='largetst.prg' else 274432")
  disk_files={('largetst.prg' if n=='largetest.prg' else n):v for n,v in files.items()}
  names=tuple('largetst.prg' if n=='largetest.prg' else n for n in NAMES)
  namespace=dict(vars(previous),NAMES=names)
  exec(compile(source,'<BV-independent-FAT-consumer>','exec'),namespace)
  need(namespace['verify'](raw,layout,disk_files) is True,'BV complete FAT consumer')
  return dict(files=len(NAMES),layout=layout,bytes=len(raw))
 need(type(raw) is bytes and len(raw)==2097152 and layout in ('ext2-2k','ext2-4k'),'BV EXT2 extent/layout')
 need(type(files) is dict and set(files)==set(NAMES),'BV file set')
 bs=2048 if layout=='ext2-2k' else 4096;total=len(raw)//bs;log=1 if bs==2048 else 2
 u16=lambda at:struct.unpack_from('<H',raw,at)[0]
 u32=lambda at:struct.unpack_from('<I',raw,at)[0]
 need(tuple(u32(1024+n) for n in (0,4,16,20,24,28,32,36,40,76,84,96))==
  (32,total,12,0,log,log,total,total,32,1,11,2),'BV geometry/features')
 need((u16(1080),u16(1082),u16(1112))==(0xef53,1,128),'BV revision')
 need(tuple(u32(bs+n) for n in (0,4,8))==(3,4,5),'BV metadata')
 need(raw[4*bs:4*bs+3]==b'\xff\xff\x0f' and not any(raw[4*bs+3:5*bs]),'BV inode bitmap')
 used=set(range(5+4096//bs));used.add(21)
 inode=5*bs+128
 need((u16(inode),u32(inode+4),u16(inode+26),u32(inode+28),u32(inode+40))==(0x41ed,bs,2,bs//512,21),'BV root')
 entries=[];at=21*bs
 while at<22*bs:
  ino=u32(at);length=u16(at+4);n=raw[at+6];kind=raw[at+7]
  need(length>=8 and length%4==0 and at+length<=22*bs and n<=length-8,'BV directory bounds')
  entries.append((ino,raw[at+8:at+8+n],kind));need(len(entries)<=11,'BV directory capacity')
  need(not any(raw[at+8+n:at+length]),'BV directory padding');at+=length
 need(entries==[(2,b'.',2),(2,b'..',2)]+[(12+i,n.encode(),1) for i,n in enumerate(NAMES)],'BV directory names')
 def own(block):
  need(0<block<total and block not in used,'BV block ownership');used.add(block)
 for i,name in enumerate(NAMES):
  data=files[name];limit=16384 if name=='data.txt' else 1048576 if name=='largetest.prg' else 274432
  need(type(data) is bytes and 0<len(data)<=limit,'BV file extent')
  count=(len(data)+bs-1)//bs;at=5*bs+(11+i)*128
  need((u16(at),u32(at+4),u16(at+26),u32(at+28))==(0x81a4,len(data),1,(count+(count>12))*bs//512),'BV inode')
  need(count<=12+bs//4 and not any(raw[at+92:at+128]),'BV no double indirection')
  blocks=[u32(at+40+4*j) for j in range(min(12,count))]
  if count>12:
   ind=u32(at+88);own(ind)
   blocks.extend(u32(ind*bs+4*j) for j in range(count-12))
   need(not any(raw[ind*bs+4*(count-12):(ind+1)*bs]),'BV indirect padding')
  else:need(not any(raw[at+40+count*4:at+92]),'BV unused pointers')
  content=bytearray()
  for block in blocks:own(block);content.extend(raw[block*bs:(block+1)*bs])
  need(content[:len(data)]==data and not any(content[len(data):]),'BV complete data/padding')
 for block in range(total):
  need(bool(raw[3*bs+block//8]&(1<<(block%8)))==(block in used),'BV block bitmap')
  if block not in used:need(not any(raw[block*bs:(block+1)*bs]),'BV unallocated bytes')
 need(not any(raw[3*bs+(total+7)//8:4*bs]),'BV bitmap tail')
 free=total-len(used)
 need((u32(1036),u16(bs+12),u16(bs+14),u16(bs+16))==(free,free,12,1),'BV free accounting')
 return dict(files=len(files),allocated_blocks=len(used),free_inodes=12)

def data_volume(raw,values):return verify_volume(raw,medium_files(values))
selected.input_binding=input_binding;selected.data_volume=data_volume;verify=selected.verify
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--index',type=Path);p.add_argument('--openssl');a=p.parse_args()
 print('LARGE_FILE_MEDIA_VERIFY_OK',verify(a.directory,a.index,a.openssl))
