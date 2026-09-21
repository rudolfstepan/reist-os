"""Five immutable generated layouts for the explicit application object profile."""
import struct
from build_x86_64_fs_media import image as base_image,LAYOUTS,MAX_BYTES
NAMES=('boot.prg','cat.prg','ls.prg','probe.prg','data.txt')
DATA=b'REIST native application file objects\nRead-only, generation-bound, revocable.\n'

def admit(files):
    if type(files) is not dict or set(files)!=set(NAMES):raise ValueError('exact application file set')
    for name in NAMES:
        value=files[name]
        if type(value) is not bytes or not 0<len(value)<=(16384 if name=='data.txt' else 274432):
            raise ValueError('bounded application object '+name)

def image(layout,files):
    admit(files)
    if layout not in LAYOUTS:raise ValueError('application media layout')
    raw=bytearray(base_image(layout,program=bytes(64)))
    def w16(at,value):struct.pack_into('<H',raw,at,value)
    def w32(at,value):struct.pack_into('<I',raw,at,value)
    if layout.startswith('fat'):
        fat32=layout=='fat32';reserved=32 if fat32 else 1;fat=544 if fat32 else 9
        root=reserved+2*fat;data=root+(1 if fat32 else 14)
        raw[reserved*512:]=bytes(len(raw)-reserved*512)
        next_cluster=3 if fat32 else 2
        def entry(cluster,value):
            for copy in range(2):
                at=(reserved+copy*fat)*512
                if fat32:w32(at+4*cluster,value)
                else:
                    at+=cluster+cluster//2;old=raw[at]|raw[at+1]<<8
                    w16(at,(old&15)|(value<<4) if cluster&1 else (old&0xf000)|value)
        for n,v in enumerate((0xffffff8,0xfffffff,0xfffffff) if fat32 else (0xff0,0xfff)):entry(n,v)
        for n,name in enumerate(NAMES):
            value=files[name];count=(len(value)+511)//512;first=next_cluster;next_cluster+=count
            end=data*512+(next_cluster-(3 if fat32 else 2))*512
            if end>len(raw):raise ValueError('application medium capacity')
            for cluster in range(first,next_cluster):entry(cluster,cluster+1 if cluster+1<next_cluster else 0xfffffff if fat32 else 0xfff)
            at=root*512+n*32;stem,extension=name.upper().split('.')
            raw[at:at+11]=stem.ljust(8).encode()+extension.ljust(3).encode();raw[at+11]=0x20
            w16(at+26,first);w32(at+28,len(value))
            start=data*512+(first-(3 if fat32 else 2))*512;raw[start:start+len(value)]=value
        if fat32:
            w32(512+488,70000-reserved-2*fat-(next_cluster-2));w32(512+492,next_cluster)
            raw[7*512:8*512]=raw[512:1024]
    else:
        bs=1024<<(LAYOUTS.index(layout)-2);raw=bytearray(1048576)
        total=len(raw)//bs;first=int(bs==1024);gd=(2 if first else 1)*bs
        occupied=set(range(first,5+(2048+bs-1)//bs))|{21}
        for at,v in ((0,16),(4,total),(16,0),(20,first),(24,LAYOUTS.index(layout)-2),
                     (28,LAYOUTS.index(layout)-2),(32,total),(36,total),(40,16),(76,1),(84,11),(96,2)):w32(1024+at,v)
        for at,v in ((56,0xef53),(58,1),(88,128)):w16(1024+at,v)
        for at,v in ((0,3),(4,4),(8,5)):w32(gd+at,v)
        raw[4*bs:4*bs+2]=b'\xff\xff'
        root=5*bs+128;w16(root,0x41ed);w32(root+4,bs);w16(root+26,2);w32(root+28,bs//512);w32(root+40,21)
        cursor=32
        for n,name in enumerate(NAMES):
            value=files[name];count=(len(value)+bs-1)//bs;indirect=count>12
            if count>12+bs//4 or cursor+count>total:raise ValueError('application direct/single-indirect bound')
            at=5*bs+(11+n)*128;w16(at,0x81a4);w32(at+4,len(value));w16(at+26,1);w32(at+28,(count+indirect)*bs//512)
            for i in range(min(12,count)):w32(at+40+i*4,cursor+i)
            if indirect:
                block=22+n;occupied.add(block);w32(at+88,block)
                for i in range(count-12):w32(block*bs+4*i,cursor+12+i)
            occupied.update(range(cursor,cursor+count));raw[cursor*bs:cursor*bs+len(value)]=value;cursor+=count
        offset=21*bs
        records=[(2,b'.',2),(2,b'..',2)]+[(12+n,name.encode(),1) for n,name in enumerate(NAMES)]
        for n,(ino,name,kind) in enumerate(records):
            length=((8+len(name)+3)//4)*4 if n+1<len(records) else 22*bs-offset
            w32(offset,ino);w16(offset+4,length);raw[offset+6]=len(name);raw[offset+7]=kind
            raw[offset+8:offset+8+len(name)]=name;offset+=length
        for block in occupied:
            bit=block-first;raw[3*bs+bit//8]|=1<<(bit%8)
        free=total-first-len(occupied);w32(1024+12,free);w16(gd+12,free);w16(gd+14,0);w16(gd+16,1)
    if not 0<len(raw)<=MAX_BYTES or len(raw)%512:raise ValueError('application data extent')
    return bytes(raw)
