"""Independent bounded consumer of the native research media package."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import validate_boot_manifest as manifest
import build_x86_64_c_payload as payload

ROOT=Path(__file__).resolve().parents[1]
VERSION=1
FILES={'reist-x86_64-bootstrap.elf':1048576,'reist-x86_64-c-core.elf':1048576,
       'reist-x86_64-user-shell.elf':1048576,'reist-x86_64-user-probe.elf':1048576,
       'reist-x86_64-user-child.elf':1048576,'stage1_mbr.bin':512,'stage1_floppy.bin':512,
       'stage2_bios.bin':32768,'reist-x86_64-bootstrap.elf.sig':256,
       'reist-x86_64.img':536870912,'reist-x86_64-floppy.img':1474560,
       'reist-x86_64.vmdk':4096,'reist-x86_64.vmx':4096,'README.txt':4096}
PROGRAMS={'bin/shell.prg':'reist-x86_64-user-shell.elf',
          'usr/bin/probe.prg':'reist-x86_64-user-probe.elf',
          'usr/bin/child.prg':'reist-x86_64-user-child.elf'}


def need(value,message):
    if not value:raise ValueError(message)


def bounded(path,limit):
    need(path.is_file(),'regular package file '+path.name)
    with path.open('rb') as stream:raw=stream.read(limit+1)
    need(0<len(raw)<=limit,'file capacity '+path.name);return raw


def exact_path(parent,name):
    need(isinstance(name,str) and '/' not in name and '\\' not in name and name not in ('','.','..'), 'package path')
    result=parent/name
    need(not result.is_symlink() and result.resolve().parent==parent.resolve(),'package path escape')
    return result


def verify_signature(artifact,signature,openssl):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify_boot_signature.py'),
        '--artifact',str(artifact),'--signature',str(signature),'--policy',str(ROOT/'safety/boot_trust_policy.json'),
        '--openssl',str(openssl),'--root',str(ROOT)],cwd=ROOT,capture_output=True,timeout=30,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    need(result.returncode==0,'package RSA-PSS verification')


def user_elf(raw):
    need(64<=len(raw)<=1048576 and raw[:7]==b'\x7fELF\x02\x01\x01','user ELF64 header')
    kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=struct.unpack_from('<HHIQQQIHHHHHH',raw,16)
    need((kind,machine,version,flags,ehsize,phsize)==(2,62,1,0,64,56),'user ELF64 identity')
    need(1<=phnum<=16 and 64<=phoff<=len(raw)-phnum*56,'user program table')
    ranges=[];executable=False
    for i in range(phnum):
        typ,rights,offset,address,physical,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',raw,phoff+i*56)
        if typ!=1:
            need(typ==0x6474e551 and rights==6 and not filesz and not memsz,'user runtime dependency');continue
        need(0<memsz<=32768 and filesz<=memsz and offset<=len(raw)-filesz,'user segment size')
        need(address==physical and 0x400000<=address<address+memsz<=0x408000,'user fixture address')
        need(rights in (4,5,6) and align==4096 and offset%4096==address%4096,'user W^X/alignment')
        ranges.append((address,address+memsz))
        if rights==5 and address<=entry<address+filesz:executable=True
    ranges.sort()
    need(executable and all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'user entry/overlap')


def fat_file(stream,start,path,is_fat32):
    """Read only the declared short-name paths; never trust producer tree logic."""
    def read(offset,size):
        need(0<=offset and 0<size<=1048576,'FAT read capacity')
        stream.seek(offset);raw=stream.read(size);need(len(raw)==size,'FAT truncated');return raw
    boot=read(start,512)
    bps=struct.unpack_from('<H',boot,11)[0];spc=boot[13]
    reserved=struct.unpack_from('<H',boot,14)[0];fats=boot[16]
    root_entries=struct.unpack_from('<H',boot,17)[0]
    sectors=struct.unpack_from('<I' if is_fat32 else '<H',boot,32 if is_fat32 else 19)[0]
    fat_sectors=struct.unpack_from('<I' if is_fat32 else '<H',boot,36 if is_fat32 else 22)[0]
    need(bps==512 and spc==1 and fats==2 and reserved>0 and boot[510:]==b'\x55\xaa','FAT geometry')
    need((is_fat32 and root_entries==0 and sectors==1040384) or
         (not is_fat32 and root_entries==224 and sectors==2880),'FAT profile')
    root_size=(root_entries*32+511)//512*512
    data_relative=(reserved+fats*fat_sectors)*512+root_size
    clusters=(sectors*512-data_relative)//512
    need(0<fat_sectors<=8192 and 0<clusters<=1048576,'FAT bounds')
    fat_start=start+reserved*512
    def chain(first):
        seen=set();parts=[];current=first
        for _ in range(2048):
            need(2<=current<clusters+2 and current not in seen,'FAT chain cycle/range')
            seen.add(current);parts.append(read(start+data_relative+(current-2)*512,512))
            offset=current*4 if is_fat32 else current+current//2
            width=4 if is_fat32 else 2
            need(offset+width<=fat_sectors*512,'FAT entry bounds')
            a=read(fat_start+offset,width);b=read(fat_start+fat_sectors*512+offset,width)
            need(a==b,'FAT mirrored allocation mismatch')
            value=int.from_bytes(a,'little')
            current=(value&0xfffffff) if is_fat32 else ((value>>4 if current&1 else value)&0xfff)
            if current>=(0xffffff8 if is_fat32 else 0xff8):return b''.join(parts)
        raise ValueError('FAT chain capacity')
    listing=chain(struct.unpack_from('<I',boot,44)[0]) if is_fat32 else read(start+(reserved+fats*fat_sectors)*512,root_size)
    pieces=path.split('/')
    for index,piece in enumerate(pieces):
        base,_,ext=piece.upper().partition('.')
        wanted=(base.ljust(8)+ext.ljust(3)).encode('ascii');matches=[]
        for offset in range(0,len(listing),32):
            entry=listing[offset:offset+32]
            if entry[0]==0:break
            if entry[0]==0xe5 or entry[11]&8:continue
            if entry[:11]==wanted:matches.append(entry)
        need(len(matches)==1,'FAT exact program path '+path)
        entry=matches[0];directory=index<len(pieces)-1
        need(bool(entry[11]&16)==directory,'FAT path kind')
        cluster=struct.unpack_from('<H',entry,26)[0]
        if is_fat32:cluster|=struct.unpack_from('<H',entry,20)[0]<<16
        listing=chain(cluster)
        if not directory:
            size=struct.unpack_from('<I',entry,28)[0]
            need(0<size<=1048576 and len(listing)==(size+511)//512*512,'FAT exact file allocation')
            return listing[:size]
    raise ValueError('FAT missing file')


def verify_vm_configuration(vmx,descriptor):
    settings={}
    for line in vmx.splitlines():
        match=re.fullmatch(r'([A-Za-z0-9_.:]+) = "([^"]*)"',line)
        need(match and match[1] not in settings,'VMX duplicate/invalid key');settings[match[1]]=match[2]
    expected={'.encoding':'UTF-8','config.version':'8','virtualHW.version':'12',
        'displayName':'REIST native x86_64 research bootstrap','guestOS':'other-64','firmware':'bios',
        'memsize':'4096','numvcpus':'1','ide0:0.present':'TRUE','ide0:0.fileName':'reist-x86_64.vmdk',
        'ide0:0.deviceType':'disk','floppy0.present':'FALSE','ethernet0.present':'FALSE',
        'sound.present':'FALSE','usb.present':'FALSE','usb.generic.allowHID':'FALSE',
        'usb.generic.allowLastHID':'FALSE','sharedFolder.maxNum':'0','RemoteDisplay.vnc.enabled':'FALSE',
        'mks.enable3d':'FALSE','serial0.present':'TRUE','serial0.fileType':'file',
        'serial0.fileName':'native-serial.log','serial0.startConnected':'TRUE','tools.syncTime':'FALSE'}
    need(settings==expected,'VMX exact native authority')
    rows=[line for line in descriptor.splitlines() if line and not line.startswith('#')]
    need(len(rows)==11 and rows[0:2]==['version=1','encoding="UTF-8"'] and
         re.fullmatch(r'CID=[0-9a-f]{8}',rows[2]),'VMDK header')
    need(rows[3:]==['parentCID=ffffffff','createType="monolithicFlat"',
         'RW 1048576 FLAT "reist-x86_64.img" 0','ddb.adapterType = "ide"',
         'ddb.geometry.cylinders = "1040"','ddb.geometry.heads = "16"',
         'ddb.geometry.sectors = "63"','ddb.virtualHWVersion = "4"'], 'VMDK exact local extent')


def verify(directory,index=None,openssl='openssl'):
    directory=Path(directory).resolve();index=Path(index) if index else directory/'native-media.json'
    need(index.resolve().parent==directory and not index.is_symlink(),'native index path')
    def unique(pairs):
        result={}
        for name,value in pairs:
            need(name not in result,'duplicate index key');result[name]=value
        return result
    envelope=json.loads(bounded(index,16384),object_pairs_hook=unique)
    need(isinstance(envelope,dict) and set(envelope)=={'package','signature'},'index envelope')
    package=envelope['package']
    need(isinstance(package,dict) and set(package)=={'version','architecture','profile','attempt','artifacts','programs'},'index fields')
    need(type(package['version']) is int and package['version']==1 and package['architecture']=='x86_64' and package['profile']=='research-native-heap','native profile')
    need(isinstance(package['attempt'],str) and re.fullmatch('native-media-[0-9a-f]{32}',package['attempt']),'attempt identity')
    attempt=exact_path(directory,package['attempt']);need(attempt.is_dir(),'attempt directory')
    raw=(json.dumps(package,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    signed=exact_path(attempt,'package.json');signature=exact_path(attempt,'package.json.sig')
    need(bounded(signed,16384)==raw,'signed index mismatch')
    sig=bounded(signature,256)
    need(len(sig)==256 and envelope['signature']==sig.hex(),'index signature binding')
    verify_signature(signed,signature,openssl)
    need(package['programs']==PROGRAMS and isinstance(package['artifacts'],dict) and set(package['artifacts'])==set(FILES),'exact artifact/program set')
    for name,limit in FILES.items():
        item=package['artifacts'][name];path=exact_path(attempt,name)
        need(isinstance(item,dict) and set(item)=={'size','sha256'},'artifact descriptor')
        need(type(item['size']) is int and 0<item['size']<=limit and path.stat().st_size==item['size'],'artifact size '+name)
        sha=hashlib.sha256();remaining=item['size']
        with path.open('rb') as stream:
            while remaining:
                chunk=stream.read(min(65536,remaining))
                need(chunk,'artifact truncated while hashing');sha.update(chunk);remaining-=len(chunk)
            need(not stream.read(1),'artifact grew while hashing')
        need(item['sha256']==sha.hexdigest(),'artifact digest '+name)
    inner=bounded(attempt/'reist-x86_64-c-core.elf',1048576)
    kernel=bounded(attempt/'reist-x86_64-bootstrap.elf',1048576)
    parsed=payload.validate(inner);payload.verify_outer(inner,kernel)
    need(parsed['layout_version']==4 and 'reist_native_ipc' in parsed['symbols'],'native kernel binding')
    kernel_sig=bounded(attempt/'reist-x86_64-bootstrap.elf.sig',256)
    verify_signature(attempt/'reist-x86_64-bootstrap.elf',attempt/'reist-x86_64-bootstrap.elf.sig',openssl)
    for name in PROGRAMS.values():user_elf(bounded(attempt/name,1048576))
    for layout,name,size,partition,slots in (
            ('hdd','reist-x86_64.img',536870912,2048,((0,128),(96,3136))),
            ('floppy','reist-x86_64-floppy.img',1474560,1,((0,128),))):
        path=attempt/name;need(path.stat().st_size==size,'exact medium size')
        info=manifest.validate_image(path,layout)
        need(info.partition_lba==partition and info.slot_count==len(slots),'native manifest layout')
        with path.open('rb') as stream:
            for relative,kernel_lba in slots:
                stream.seek((partition+relative)*512);sector=stream.read(512)
                need(sector[80:336]==kernel_sig,'embedded signature binding')
                stream.seek((partition+kernel_lba)*512)
                need(stream.read(len(kernel))==kernel,'embedded native kernel binding')
            stage=bounded(attempt/'stage2_bios.bin',32768)
            stream.seek((partition+1)*512);need(stream.read(len(stage))==stage,'stage2 content')
            stream.seek(0);first=stream.read(512)
            expected=bounded(attempt/('stage1_mbr.bin' if layout=='hdd' else 'stage1_floppy.bin'),512)
            # Only documented MBR partition entries or FAT12 BPB are patched.
            need((first[:446]==expected[:446] and first[510:]==expected[510:]) if layout=='hdd' else
                 (first[:3]==expected[:3] and first[62:]==expected[62:]),'stage1 code binding')
            if layout=='hdd':
                need(first[466]==0x0c and struct.unpack_from('<II',first,470)==(8192,1040384),'data partition')
            for filename,artifact in PROGRAMS.items():
                need(fat_file(stream,8192*512 if layout=='hdd' else 0,filename,layout=='hdd')==
                     bounded(attempt/artifact,1048576),'packaged ELF64 program '+filename)
    vmx=bounded(attempt/'reist-x86_64.vmx',4096).decode('ascii')
    descriptor=bounded(attempt/'reist-x86_64.vmdk',4096).decode('ascii')
    verify_vm_configuration(vmx,descriptor)
    return attempt


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--openssl',default=shutil.which('openssl') or 'openssl')
    args=p.parse_args()
    try:
        attempt=verify(args.directory,args.index,args.openssl);print('NATIVE_BOOT_MEDIA_VERIFY_OK attempt='+str(attempt));return 0
    except (OSError,ValueError,KeyError,TypeError,struct.error,subprocess.TimeoutExpired) as error:
        print('NATIVE_BOOT_MEDIA_VERIFY_FAIL '+str(error));return 1


if __name__=='__main__':raise SystemExit(main())
