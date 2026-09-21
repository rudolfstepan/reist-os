"""Independent bounded FAT/EXT2 consumer for generated application tool media.

This does not call the image producer or infer successful filesystem access from
its metadata. Actual C-parser and guest reads remain separate required proofs.
"""
import struct
NAMES=('boot.prg','cat.prg','ls.prg','probe.prg','data.txt')
LAYOUTS=('fat12','fat32','ext2-1k','ext2-2k','ext2-4k')

def need(value,message):
    if not value:raise ValueError('application media '+message)

def verify(raw,layout,files):
    need(type(raw) is bytes and layout in LAYOUTS,'raw/layout')
    need(type(files) is dict and set(files)==set(NAMES),'exact file set')
    for name in NAMES:need(type(files[name]) is bytes and 0<len(files[name])<=(16384 if name=='data.txt' else 274432),'file extent')
    def u16(at):return struct.unpack_from('<H',raw,at)[0]
    def u32(at):return struct.unpack_from('<I',raw,at)[0]
    if layout.startswith('fat'):
        large=layout=='fat32';sectors=70000 if large else 2880;reserved=32 if large else 1;fat=544 if large else 9
        need(len(raw)==sectors*512 and raw[510:512]==b'\x55\xaa','FAT extent/signature')
        need(u16(11)==512 and raw[13]==1 and u16(14)==reserved and raw[16]==2,'FAT geometry')
        need((u16(17),u16(19),u16(22))==((0,0,0) if large else (224,2880,9)),'FAT fixed root/size')
        if large:
            need((u32(32),u32(36),u32(44),u16(48),u16(50))==(70000,544,2,1,6),'FAT32 root')
            need(raw[:512]==raw[3072:3584] and raw[512:1024]==raw[3584:4096],'FAT32 backups')
        a=raw[reserved*512:(reserved+fat)*512];b=raw[(reserved+fat)*512:(reserved+2*fat)*512]
        need(a==b,'FAT copies')
        def entry(n):
            if large:return struct.unpack_from('<I',a,4*n)[0]
            pair=struct.unpack_from('<H',a,n+n//2)[0];return pair>>4 if n&1 else pair&0xfff
        need(entry(0)==(0xffffff8 if large else 0xff0) and entry(1)==(0xfffffff if large else 0xfff),'FAT reserved entries')
        root=(reserved+2*fat)*512;data=root+(512 if large else 14*512)
        used={2} if large else set();first=3 if large else 2
        if large:need(entry(2)==0xfffffff,'root chain')
        for i,name in enumerate(NAMES):
            at=root+i*32;stem,extension=name.upper().split('.')
            need(raw[at:at+11]==stem.ljust(8).encode()+extension.ljust(3).encode() and raw[at+11]==0x20,'root name/type')
            need(not any(raw[at+12:at+26]) and u32(at+28)==len(files[name]),'directory metadata')
            cluster=u16(at+26);wanted=(len(files[name])+511)//512;content=bytearray()
            for n in range(wanted):
                need(first<=cluster and cluster not in used,'cluster authority/overlap')
                offset=data+(cluster-first)*512;need(data<=offset<=len(raw)-512,'cluster extent');used.add(cluster)
                content.extend(raw[offset:offset+512]);following=entry(cluster)
                if n+1==wanted:need(following==(0xfffffff if large else 0xfff),'complete finite chain')
                else:need(following>=first,'chain continuation')
                cluster=following
            need(content[:len(files[name])]==files[name] and not any(content[len(files[name]):]),'actual file/padding')
        need(not any(raw[root+32*len(NAMES):data]),'exact root entries')
        for cluster in range(first,(len(raw)-data)//512+first):
            if cluster not in used:
                need(entry(cluster)==0,'unallocated FAT')
                at=data+(cluster-first)*512;need(not any(raw[at:at+512]),'unused data')
        if large:
            need(u32(512)==0x41615252 and u32(996)==0x61417272 and u32(1020)==0xaa550000,'FSInfo signatures')
            need(u32(1000)==sectors-reserved-2*fat-len(used) and u32(1004)==max(used)+1,'FSInfo accounting')
    else:
        need(len(raw)==1048576,'EXT2 extent')
        bs=1024<<(LAYOUTS.index(layout)-2);first=int(bs==1024);total=len(raw)//bs
        need(u16(1080)==0xef53 and u32(1024)==16 and u32(1028)==total and u32(1044)==first,'EXT2 identity')
        need(u32(1048)==LAYOUTS.index(layout)-2 and u32(1052)==u32(1048) and u32(1056)==total and u32(1060)==total and u32(1064)==16,'EXT2 group geometry')
        need((u32(1100),u32(1108),u16(1112),u32(1120))==(1,11,128,2),'EXT2 revision')
        gd=(2 if first else 1)*bs
        need((u32(gd),u32(gd+4),u32(gd+8))==(3,4,5),'EXT2 metadata layout')
        used=set(range(first,5+(2048+bs-1)//bs))
        def own(block):
            need(first<=block<total and block not in used,'EXT2 block overlap/range');used.add(block)
        own(21)
        r=5*bs+128
        need((u16(r),u32(r+4),u16(r+26),u32(r+28),u32(r+40))==(0x41ed,bs,2,bs//512,21),'root inode')
        pos=21*bs;entries=[]
        while pos<22*bs:
            ino=u32(pos);length=u16(pos+4);n=raw[pos+6];kind=raw[pos+7]
            need(length>=8 and not length%4 and pos+length<=22*bs and n<=length-8,'directory record')
            entries.append((ino,raw[pos+8:pos+8+n],kind))
            need(not any(raw[pos+8+n:pos+length]),'directory padding');pos+=length
            need(len(entries)<=7,'directory capacity')
        need(entries==[(2,b'.',2),(2,b'..',2)]+[(12+i,n.encode(),1) for i,n in enumerate(NAMES)],'exact directory')
        for i,name in enumerate(NAMES):
            at=5*bs+(11+i)*128;count=(len(files[name])+bs-1)//bs
            need((u16(at),u32(at+4),u16(at+26),u32(at+28))==(0x81a4,len(files[name]),1,(count+(count>12))*bs//512),'file inode')
            need(count<=12+bs//4 and not any(raw[at+92:at+128]),'no double indirect/reserved inode')
            blocks=[u32(at+40+4*n) for n in range(min(12,count))]
            if count<=12:need(not any(raw[at+40+count*4:at+92]),'unused direct pointers')
            else:
                indirect=u32(at+88);own(indirect)
                blocks.extend(u32(indirect*bs+4*n) for n in range(count-12))
                need(not any(raw[indirect*bs+(count-12)*4:(indirect+1)*bs]),'indirect tail')
            content=bytearray()
            for block in blocks:own(block);content.extend(raw[block*bs:(block+1)*bs])
            need(content[:len(files[name])]==files[name] and not any(content[len(files[name]):]),'EXT2 actual file/padding')
        bitmap=bytearray(bs)
        for block in used:bitmap[(block-first)//8]|=1<<((block-first)%8)
        need(raw[3*bs:4*bs]==bitmap and raw[4*bs:5*bs]==b'\xff\xff'+bytes(bs-2),'allocation bitmaps')
        free=total-first-len(used)
        need(u32(1036)==free and u32(1040)==0 and (u16(gd+12),u16(gd+14),u16(gd+16))==(free,0,1),'free accounting')
        for block in range(first,total):
            if block not in used:need(not any(raw[block*bs:(block+1)*bs]),'unused EXT2 block')
    return True
