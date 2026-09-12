"""External ELF64 preparation. Never linked into Ring0; no runtime file rights."""
from pathlib import Path
import argparse, os, struct, subprocess, uuid
ROOT=Path(__file__).resolve().parents[1]
SIZE=36896

def prepare(raw,args):
    def need(condition):
        if not condition:raise ValueError('unsupported/malformed bounded ELF64 or arguments')
    need(64<=len(raw)<=65536)
    need(raw[:16]==b'\x7fELF\x02\x01\x01'+bytes(9))
    typ,machine,version,entry,phoff,_,flags,ehsize,phsize,count,_,_,_=struct.unpack_from('<HHIQQQIHHHHHH',raw,16)
    need((typ,machine,version,flags,ehsize,phsize)==(2,62,1,0,64,56))
    need(1<=count<=8 and 64<=phoff<=len(raw)-count*56)
    pages=bytearray(32768);rights=bytearray(8);executable=False;previous=0
    for n in range(count):
        kind,pf,offset,va,_,filesz,memsz,align=struct.unpack_from('<II6Q',raw,phoff+n*56)
        if kind==0:continue
        need(kind==1 and pf in (4,5,6) and align==4096)
        need(0<memsz<=32768 and filesz<=memsz and offset<=len(raw) and filesz<=len(raw)-offset)
        need(0x400000<=va<0x408000 and memsz<=0x408000-va and va>=previous)
        need((offset^va)&4095==0)
        first=(va-0x400000)//4096;last=(va+memsz-1-0x400000)//4096
        need(not any(rights[first:last+1]))
        rights[first:last+1]=bytes([pf])*(last-first+1)
        pages[va-0x400000:va-0x400000+filesz]=raw[offset:offset+filesz]
        executable|=pf==5 and va<=entry<va+filesz
        previous=va+memsz
    need(executable and len(args)<=8)
    source=bytearray(4096);struct.pack_into('<Q',source,0,len(args));cursor=72
    for n,arg in enumerate(args):
        try:b=arg.encode('ascii')
        except (UnicodeEncodeError,AttributeError):raise ValueError('ASCII boot arguments required') from None
        need(len(b)<128 and b'\0' not in b)
        struct.pack_into('<Q',source,8+n*8,0x1000+cursor)
        source[cursor:cursor+len(b)+1]=b+b'\0';cursor+=len(b)+1
    return b'RNPGv1\0\0'+struct.pack('<IIQ',1,SIZE,entry)+rights+pages+source

def build(directory,cc,nasm,ld,case,family=False,family_case=0,startup=False,startup_case=0,import_image=False):
    if import_image and not startup:raise ValueError('import requires startup')
    if startup and (not family or family_case or case):raise ValueError('startup requires normal family')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    attempt=directory/('programs-'+uuid.uuid4().hex);attempt.mkdir()
    def run(args):
        r=subprocess.run(list(map(str,args)),cwd=ROOT,timeout=60,capture_output=True,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (attempt/'build.log').open('ab') as f:f.write(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-2000:])
    start=attempt/'start.o';run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    records=[None]*4
    for n in ([2,0,1,3] if import_image else range(4)):
        obj=attempt/f'program{n}.o';elf=attempt/f'program{n}.prg'
        extra=[];objects=[]
        if import_image and n==2:extra=['-DNATIVE_IMPORT_CHILD=1']
        if import_image and n==0:
            blob=(attempt/'program2.prg').read_bytes()
            # Writable input fixture is private to the Ring3 root; never a kernel parser.
            header=attempt/'import_blob.h'
            header.write_text('static const unsigned char import_blob[] __attribute__((section(".data.import_blob")))={'+','.join(str(b) for b in blob)+'};\n',encoding='ascii')
            extra=['-DNATIVE_IMPORT=1','-include',str(header)]
            parser=attempt/'image.o'
            run([*cc,'-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','userspace/sdk/lib/x86_64/image.c','-o',parser])
            objects.append(parser)
        run([*cc,'-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror',
             '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
             '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
             '-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include',
             f'-DPROGRAM_ID={n}',f'-DPROGRAM_CASE={case}',f'-DFAMILY_CASE={family_case}',f'-DSTARTUP_CASE={startup_case}',
             *extra,'-c','arch/x86_64/user/task_startup.c' if startup else 'arch/x86_64/user/task_family.c' if family else 'arch/x86_64/user/boot_program.c','-o',obj])
        run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
             '-z','noexecstack','--strip-all',f'--defsym=PROGRAM_LAYOUT={n}',
             '-T','config/x86_64_import_program.ld' if import_image and n==0 else 'config/x86_64_boot_program.ld','-o',elf,start,obj,*objects])
        records[n]=prepare(elf.read_bytes(),[f'program{n}.prg',str(n)])
    catalog=attempt/'boot-programs.bin';catalog.write_bytes(b''.join(records))
    # All inputs and all records admitted before replacing the build consumer.
    # Retain every attempt and ELF; only this explicit generated catalog changes.
    staged=directory/('boot-programs-'+uuid.uuid4().hex+'.tmp')
    staged.write_bytes(catalog.read_bytes());os.replace(staged,directory/'boot-programs.bin')
    print('NATIVE_BOOT_PROGRAMS_PREPARED',attempt)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True)
    for tool in ('cc','nasm','ld'):p.add_argument('--'+tool,required=True,nargs='+')
    p.add_argument('--case',type=int,choices=range(3),default=0)
    p.add_argument('--family',action='store_true')
    p.add_argument('--family-case',type=int,choices=range(6),default=0)
    p.add_argument('--startup',action='store_true')
    p.add_argument('--import-image',action='store_true')
    p.add_argument('--startup-case',type=int,choices=range(2),default=0)
    a=p.parse_args()
    if a.family_case and not a.family:p.error('family-case requires family')
    if a.startup_case and not a.startup:p.error('startup-case requires startup')
    build(a.directory,a.cc,a.nasm,a.ld,a.case,a.family,a.family_case,a.startup,a.startup_case,a.import_image)
