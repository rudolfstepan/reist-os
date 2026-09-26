"""Selected native mode driver and ordinary /video.prg hardware exerciser."""
from pathlib import Path
import struct

def compact_elf(raw):
    """Omit optional ELF section metadata and unbacked tail padding only."""
    from build_x86_64_boot_programs import prepare
    prepared=prepare(raw,[],True)
    data=bytearray(raw);phoff=struct.unpack_from('<Q',raw,32)[0]
    count=struct.unpack_from('<H',raw,56)[0];end=max(64,phoff+56*count)
    for i in range(count):
        at=phoff+56*i;kind,flags,offset,va,pa,filesz,memsz,alignment=struct.unpack_from('<II6Q',raw,at)
        if kind!=1:raise ValueError('only ordinary admitted ELF load headers')
        if not filesz:
            # System V ELF: no file bytes for this segment. Preserve its
            # page-offset congruence even when virtual addresses are unaligned.
            struct.pack_into('<Q',data,at+8,va%alignment)
        else:end=max(end,offset+filesz)
    struct.pack_into('<Q',data,40,0)
    struct.pack_into('<HHH',data,58,0,0,0)
    compact=bytes(data[:end])
    if prepare(compact,[],True)!=prepared:raise ValueError('loaded image/rights/entry changed')
    return compact

def build_roles(attempt,cc,ld,run,start):
    from build_x86_64_boot_programs import prepare
    outputs=[]
    for role,sources in (
        ('video-driver',('userspace/drivers/video/native_mode_main.c','userspace/drivers/video/native_mode.c',
                         'userspace/drivers/vga/native_console.c','userspace/drivers/vga/text.c',
                         'userspace/drivers/ps2/native_input.c')),
        ('video',('userspace/gui/compositor/native_mode_probe.c',))):
        objects=[]
        for index,source in enumerate(sources):
            obj=Path(attempt)/(role+'-'+str(index)+'.o')
            run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz',
                 '-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin',
                 '-fno-stack-protector','-mno-red-zone','-fno-unwind-tables',
                 '-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
                 '-mno-mmx','-mno-sse','-mno-sse2','-fstack-usage',
                 '-Iuserspace/sdk/include',
                 *(['-Dmain=reist_native_text_main'] if source=='userspace/drivers/vga/native_console.c' else []),
                 '-c',source,'-o',obj]);objects.append(obj)
        target=Path(attempt)/(role+'.prg')
        run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings',
             '--no-undefined','-z','noexecstack','--strip-all','-T','config/x86_64_wide_program.ld',
             '-o',target,start,*objects])
        prepare(target.read_bytes(),[],True);outputs.append(target)
        if role=='video-driver':
            original=target.read_bytes()
            target.with_suffix('.untrimmed.prg').write_bytes(original)
            target.write_bytes(compact_elf(original))
    root=Path(attempt)/'root';root.mkdir(exist_ok=True)
    (root/'video.prg').write_bytes(outputs[1].read_bytes())
    return outputs[0].read_bytes()
