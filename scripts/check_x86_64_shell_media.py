"""Independent bounded consumer of the opt-in, two-medium native shell package."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct
import build_x86_64_c_payload as payload
import build_x86_64_boot_programs as programs
import verify_x86_64_boot_media as old
import validate_boot_manifest as manifest
ROOT=Path(__file__).resolve().parents[1]
PROFILE='research-native-shell-two-media-v1'
KERNEL_LIMIT=3008*512
KERNEL='reist-x86_64-bootstrap.elf'
CORE='reist-x86_64-c-core.elf'
DEVICES={'data':'primary-master-read-only-ext2-1k','hdd':'primary-slave-bios-only',
         'floppy':'bios-only','runtime_program':'/boot.prg','initial_shell':'signed-embedded-/bin/shell.prg'}
FILES={KERNEL:KERNEL_LIMIT,CORE:1048576,'boot-programs.bin':4*266336,
       **{f'program{n}.prg':524288 for n in range(4)},'file-program.prg':1280,
       'stage1_mbr.bin':512,'stage1_floppy.bin':512,'stage2_bios.bin':32768,
       KERNEL+'.sig':256,'reist-x86_64.img':536870912,
       'reist-x86_64-floppy.img':1474560,'system.ext2':131072,'README.txt':4096}
need=old.need
bounded=old.bounded
exact_path=old.exact_path


def object_json(raw):
    need(type(raw) is bytes and 0<len(raw)<=16384,'index byte capacity')
    def unique(pairs):
        result={}
        for name,value in pairs:
            need(name not in result,'duplicate index field');result[name]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    need(type(value) is dict,'index object');return value


def admit_package(p):
    need(type(p) is dict and set(p)=={'version','architecture','profile','attempt','artifacts','devices'},'exact package fields')
    need(type(p['version']) is int and p['version']==1 and p['architecture']=='x86_64' and p['profile']==PROFILE,'separate shell profile')
    need(type(p['attempt']) is str and re.fullmatch('shell-media-[0-9a-f]{32}',p['attempt']),'package attempt identity')
    need(p['devices']==DEVICES and type(p['artifacts']) is dict and set(p['artifacts'])==set(FILES),'exact devices/artifacts')


def digest(path,limit):
    path=Path(path);size=path.stat().st_size
    need(type(limit) is int and 0<size<=limit,'artifact hash extent '+path.name)
    sha=hashlib.sha256();remaining=size
    with path.open('rb') as stream:
        while remaining:
            chunk=stream.read(min(65536,remaining));need(chunk,'artifact truncated')
            sha.update(chunk);remaining-=len(chunk)
        need(not stream.read(1),'artifact grew')
    return {'size':size,'sha256':sha.hexdigest()}


def input_binding(values):
    inner=values[CORE];kernel=values[KERNEL];catalog=values['boot-programs.bin']
    need(4096<=len(kernel)<=KERNEL_LIMIT,'physical kernel slot capacity')
    parsed=payload.validate(inner);payload.verify_outer(inner,kernel)
    need(parsed['layout_version']==5 and 'native_shell_session_profile_v1' in parsed['symbols'],'actual native shell profile')
    section=payload.elf(kernel,32)['sections']['.native_catalog']['data']
    need(len(catalog)==4*266336 and section[:len(catalog)]==catalog and not any(section[len(catalog):]),'signed embedded catalog binding')
    for n in range(4):
        need(programs.prepare(values[f'program{n}.prg'],[f'program{n}.prg',str(n)],True)==catalog[n*266336:(n+1)*266336],
             'actual embedded ELF64 program '+str(n))
    app=values['file-program.prg']
    need(64<=len(app)<=1280 and app not in values['program0.prg'],'external bounded file executable')
    programs.prepare(app,[],True)


def data_volume(raw,app):
    """Read the declared fixed EXT2 directory/inode/blocks, independently of producer."""
    need(len(raw)==131072,'EXT2 data medium extent')
    u16=lambda at:struct.unpack_from('<H',raw,at)[0]
    u32=lambda at:struct.unpack_from('<I',raw,at)[0]
    need((u32(1024),u32(1028),u32(1044),u32(1048),u32(1056),u16(1080),u16(1112))==
         (16,32,1,0,32,0xef53,128),'EXT2 fixed geometry')
    need((u32(2048),u32(2052),u32(2056))==(3,4,5),'EXT2 bounded metadata blocks')
    root=5*1024+128;file=5*1024+11*128
    need((u16(root),u32(root+4),u32(root+40))==(0x41ed,1024,21),'EXT2 actual root inode')
    need((u16(file),u32(file+4),u16(file+26))==(0x81a4,len(app),1),'EXT2 actual program inode')
    cursor=21*1024
    for ino,name,size,kind in ((2,b'.',12,2),(2,b'..',12,2),(12,b'boot.prg',1000,1)):
        need((u32(cursor),u16(cursor+4),raw[cursor+6],raw[cursor+7])==(ino,size,len(name),kind) and
             raw[cursor+8:cursor+8+len(name)]==name,'EXT2 exact root entry')
        cursor+=size
    blocks=(len(app)+1023)//1024
    need(blocks in (1,2) and u32(file+28)==blocks*2,'EXT2 file allocation')
    for n in range(15):need(u32(file+40+n*4)==(22+n if n<blocks else 0),'EXT2 direct-only file blocks')
    need(raw[22*1024:22*1024+len(app)]==app and not any(raw[22*1024+len(app):]),'EXT2 complete program/padding')


def verify(directory,index=None,openssl=None):
    directory=Path(directory).absolute()
    need(directory==directory.resolve() and directory.is_relative_to(ROOT/'build'),'package directory scope')
    index=Path(index).absolute() if index else directory/'shell-media.json'
    need(index.parent==directory and not index.is_symlink(),'index path')
    envelope=object_json(bounded(index,16384))
    need(set(envelope)=={'package','signature'},'index envelope')
    p=envelope['package'];admit_package(p)
    attempt=exact_path(directory,p['attempt']);need(attempt.is_dir(),'attempt directory')
    need({path.name for path in attempt.iterdir()}==set(FILES)|{'package.json','package.json.sig','build.log'},'complete package file inventory')
    openssl=openssl or shutil.which('openssl') or 'openssl'
    raw=(json.dumps(p,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    signed=exact_path(attempt,'package.json');sig=exact_path(attempt,'package.json.sig')
    signature=bounded(sig,256)
    need(bounded(signed,16384)==raw and len(signature)==256 and envelope['signature']==signature.hex(),'signed index identity')
    old.verify_signature(signed,sig,openssl)
    for name,limit in FILES.items():
        entry=p['artifacts'][name];path=exact_path(attempt,name)
        need(type(entry) is dict and set(entry)=={'size','sha256'} and type(entry['size']) is int and
             type(entry['sha256']) is str and re.fullmatch('[0-9a-f]{64}',entry['sha256']),'artifact descriptor')
        need(entry==digest(path,limit),'artifact bytes '+name)
    values={name:bounded(attempt/name,FILES[name]) for name in (KERNEL,CORE,'boot-programs.bin',
            'file-program.prg',*(f'program{n}.prg' for n in range(4)))}
    input_binding(values)
    kernel=values[KERNEL];kernel_sig=bounded(attempt/(KERNEL+'.sig'),256)
    need(len(kernel_sig)==256,'kernel signature extent')
    old.verify_signature(attempt/KERNEL,attempt/(KERNEL+'.sig'),openssl)
    data_volume(bounded(attempt/'system.ext2',131072),values['file-program.prg'])
    stage=bounded(attempt/'stage2_bios.bin',32768)
    for layout,name,size,base,slots in (
        ('hdd','reist-x86_64.img',536870912,2048,((0,128),(96,3136))),
        ('floppy','reist-x86_64-floppy.img',1474560,1,((0,128),))):
        path=attempt/name;need(path.stat().st_size==size,'medium extent')
        info=manifest.validate_image(path,layout)
        need(info.partition_lba==base and info.slot_count==len(slots),'boot layout')
        if layout=='hdd':need((info.active_slot,info.pending_slot,info.attempts_remaining,info.successful_mask)==(0,255,0,1),'fresh confirmed-A read-only boot profile')
        with path.open('rb') as stream:
            for header,lba in slots:
                stream.seek((base+header)*512);sector=stream.read(512)
                need(sector[80:336]==kernel_sig,'embedded signature')
                stream.seek((base+lba)*512);need(stream.read(len(kernel))==kernel,'embedded actual shell kernel')
            stream.seek((base+1)*512);need(stream.read(len(stage))==stage,'actual stage2')
            stream.seek(0);first=stream.read(512)
            s1=bounded(attempt/('stage1_mbr.bin' if layout=='hdd' else 'stage1_floppy.bin'),512)
            need(len(s1)==512 and ((first[:446]==s1[:446] and first[510:]==s1[510:]) if layout=='hdd' else
                 (first[:3]==s1[:3] and first[62:]==s1[62:])),'actual stage1')
            if layout=='hdd':need(first[466]==12 and struct.unpack_from('<II',first,470)==(8192,1040384),'unchanged data partition')
    return attempt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--index',type=Path);parser.add_argument('--openssl')
    args=parser.parse_args()
    try:print('SHELL_MEDIA_VERIFY_OK',verify(args.directory,args.index,args.openssl))
    except (OSError,ValueError,KeyError,TypeError,struct.error) as error:
        print('SHELL_MEDIA_VERIFY_FAIL',str(error));raise SystemExit(1)
