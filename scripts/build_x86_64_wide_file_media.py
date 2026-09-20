"""Opt-in immutable wide-file fixtures. Never opens/imports a user disk."""
import struct
import build_x86_64_fs_media as legacy
LAYOUTS=legacy.LAYOUTS
MAX_BYTES=legacy.MAX_BYTES

def image(layout,program):
    if type(layout) is not str or layout not in LAYOUTS or type(program) is not bytes or not 64<=len(program)<=524288:
        raise ValueError('wide immutable media selection/size')
    raw=bytearray(legacy.image(layout,program=bytes(64)))
    def w16(at,value):struct.pack_into('<H',raw,at,value)
    def w32(at,value):struct.pack_into('<I',raw,at,value)
    if layout.startswith('fat'):
        fat32=layout=='fat32';reserved=32 if fat32 else 1;fat=544 if fat32 else 9
        first=3 if fat32 else 2;count=(len(program)+511)//512
        for copy in range(2):
            off=(reserved+copy*fat)*512
            for cluster in range(first,first+count):
                value=cluster+1 if cluster+1<first+count else 0x0fffffff if fat32 else 0xfff
                if fat32:w32(off+4*cluster,value)
                else:
                    at=off+cluster+cluster//2;pair=raw[at]|raw[at+1]<<8
                    w16(at,(pair&15)|(value<<4) if cluster&1 else (pair&0xf000)|value)
        root=reserved+2*fat;data=root+(1 if fat32 else 14)
        w32(root*512+28,len(program));raw[data*512:data*512+len(program)]=program
        if fat32:
            w32(512+488,70000-reserved-2*fat-1-count);w32(512+492,first+count)
            raw[7*512:8*512]=raw[512:1024]
    else:
        # One1MiB group. Keep ordinary EXT2 metadata; independent consumers
        # must reject unsupported double-indirect access, not fabricate EOF.
        raw.extend(bytes(1024*1024-len(raw)))
        bs=1024<<(LAYOUTS.index(layout)-2);total=len(raw)//bs
        count=(len(program)+bs-1)//bs;entries=bs//4;start=32
        w32(1024+4,total);w32(1024+32,total);w32(1024+36,total)
        inode=5*bs+11*128
        raw[inode+40:inode+100]=bytes(60)
        w32(inode+4,len(program))
        indirect=22;double=23;leaf=24
        overhead=int(count>12)+2*int(count>12+entries)
        w32(inode+28,(count+overhead)*bs//512)
        for n in range(min(count,12)):w32(inode+40+n*4,start+n)
        if count>12:
            w32(inode+40+12*4,indirect)
            for n in range(min(count-12,entries)):w32(indirect*bs+4*n,start+12+n)
        if count>12+entries:
            w32(inode+40+13*4,double);w32(double*bs,leaf)
            for n in range(count-12-entries):w32(leaf*bs+4*n,start+12+entries+n)
        raw[start*bs:start*bs+len(program)]=program
        raw[3*bs:4*bs]=bytes(bs)
        occupied=set(range(0,5+(2048+bs-1)//bs))|{21}|set(range(start,start+count))
        if count>12:occupied.add(indirect)
        if count>12+entries:occupied|={double,leaf}
        first=1 if bs==1024 else 0
        for block in occupied:
            if block>=first:
                bit=block-first;raw[3*bs+bit//8]|=1<<(bit%8)
        allocated=sum(block>=first for block in occupied)
        w32(1024+12,total-first-allocated);w32(1024+16,4)
        gd=(2 if bs==1024 else 1)*bs
        w16(gd+12,total-first-allocated);w16(gd+14,4);w16(gd+16,1)
    if not 0<len(raw)<=MAX_BYTES or len(raw)%512:raise ValueError('wide media extent')
    return bytes(raw)
