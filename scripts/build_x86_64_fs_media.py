"""Finite generated immutable filesystem media, not a user-image importer."""
import struct
LAYOUTS=('fat12','fat32','ext2-1k','ext2-2k','ext2-4k')
CONTENT=b'REIST NATIVE FILESYSTEM\n'
MAX_BYTES=70000*512

def image(layout,malformed=False):
    if type(layout) is not str or layout not in LAYOUTS or type(malformed) is not bool:
        raise ValueError('filesystem media selector')
    raw=bytearray((2880 if layout=='fat12' else 70000 if layout=='fat32' else 256)*512)
    def w16(at,value):struct.pack_into('<H',raw,at,value)
    def w32(at,value):struct.pack_into('<I',raw,at,value)
    if layout.startswith('fat'):
        fat32=layout=='fat32';reserved=32 if fat32 else 1;fat=544 if fat32 else 9
        raw[:11]=b'\xeb\x58\x90REISTFS ';w16(11,512);raw[13]=1;w16(14,reserved);raw[16]=2
        w16(17,0 if fat32 else 224);w16(19,0 if fat32 else 2880);raw[21]=0xf8 if fat32 else 0xf0
        w16(22,0 if fat32 else fat);w16(24,63 if fat32 else 18);w16(26,255 if fat32 else 2)
        if fat32:
            w32(32,70000);w32(36,fat);w32(44,2);w16(48,1);w16(50,6)
            raw[64]=0x80;raw[66]=0x29;w32(67,0x52465331)
            raw[71:82]=b'REIST FS   ';raw[82:90]=b'FAT32   '
            w32(512,0x41615252);w32(512+484,0x61417272)
            w32(512+488,70000-reserved-2*fat-2);w32(512+492,4);w32(512+508,0xaa550000)
        else:
            raw[38]=0x29;w32(39,0x52465331);raw[43:54]=b'REIST FS   ';raw[54:62]=b'FAT12   '
        raw[510:512]=b'\x55\xaa'
        if fat32:raw[6*512:7*512]=raw[:512];raw[7*512:8*512]=raw[512:1024]
        for copy in range(2):
            off=(reserved+copy*fat)*512
            if fat32:
                for n,value in enumerate((0x0ffffff8,0xffffffff,0x0fffffff,0x0fffffff)):w32(off+4*n,value)
            else:raw[off:off+5]=b'\xf0\xff\xff\xff\x0f'
        root=reserved+2*fat;data=root+(1 if fat32 else 14);entry=root*512
        raw[entry:entry+11]=b'README  TXT';raw[entry+11]=0x20
        w16(entry+26,3 if fat32 else 2);w32(entry+28,len(CONTENT))
        raw[data*512:data*512+len(CONTENT)]=CONTENT
        if malformed:raw[510]^=0x01
    else:
        log=LAYOUTS.index(layout)-2;bs=1024<<log;sb=1024
        for off,value in ((0,16),(4,32),(20,0 if log else 1),(24,log),(28,log),
                          (32,32),(36,32),(40,16),(76,1),(84,11),(96,2)):w32(sb+off,value)
        w16(sb+56,0xef53);w16(sb+58,1);w16(sb+88,128)
        gd=(1 if log else 2)*bs
        for off,value in ((0,3),(4,4),(8,5)):w32(gd+off,value)
        # Allocated metadata/data and inode bits, no journal or write profile.
        occupied=set(range(0,5+(2048+bs-1)//bs))|{21,22}
        for block in occupied:
            if block>=(0 if log else 1):
                bit=block-(0 if log else 1);raw[3*bs+bit//8]|=1<<(bit%8)
        for inode in range(1,13):raw[4*bs+(inode-1)//8]|=1<<((inode-1)%8)
        for number,mode,size,block,links in ((2,0x41ed,bs,21,2),(12,0x81a4,len(CONTENT),22,1)):
            off=5*bs+(number-1)*128;w16(off,mode);w32(off+4,size);w16(off+26,links)
            w32(off+28,bs//512);w32(off+40,block)
        off=21*bs
        for number,name,length,kind in ((2,b'.',12,2),(2,b'..',12,2),(12,b'readme.txt',bs-24,1)):
            w32(off,number);w16(off+4,length);raw[off+6]=len(name);raw[off+7]=kind
            raw[off+8:off+8+len(name)]=name;off+=length
        raw[22*bs:22*bs+len(CONTENT)]=CONTENT
        if malformed:raw[1024+56]^=0x01
    if not 0<len(raw)<=MAX_BYTES or len(raw)%512:raise ValueError('generated media extent')
    return bytes(raw)

def sector(layout,lba,malformed=False):
    raw=image(layout,malformed)
    if type(lba) is not int or not 0<=lba<len(raw)//512:raise ValueError('generated sector')
    return raw[lba*512:(lba+1)*512]
