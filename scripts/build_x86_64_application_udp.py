"""Build the ordinary udp.prg with its explicit native object adapter."""
from pathlib import Path
import os,subprocess
ROOT=Path(__file__).resolve().parents[1]
def build_tool(directory,cc,nasm,ld):
    from build_x86_64_boot_programs import prepare
    directory=Path(directory);env=os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(directory/'zig-cache')
    def run(command):
        p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=60,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'application-udp-build.log').open('ab') as log:log.write(p.stdout+p.stderr)
        if p.returncode:raise ValueError((p.stdout+p.stderr).decode(errors='replace')[-3000:])
    # The adapter owns native transport; the generic network service transport
    # must not be linked into an application through inherited build defines.
    cc=[x for x in cc if not str(x).startswith('-DREIST_NATIVE_NETWORK_SESSION')]
    common=[*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2',
        '-ffunction-sections','-fdata-sections','-DREIST_NATIVE_APP_NETWORK=1','-Iuserspace/sdk/include','-fstack-usage']
    start=directory/'udp-start.o';run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    objects=[]
    for n,source in enumerate(['userspace/programs/udp.c','userspace/sdk/lib/x86_64/application_udp.c',
            'userspace/sdk/lib/x86_64/application_udp_platform.c','userspace/sdk/lib/x86_64/network_session.c']):
        obj=directory/f'udp-{n}.o';run([*common,'-c',source,'-o',obj]);objects.append(obj)
    elf=directory/'udp.prg'
    run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
         '-z','noexecstack','--gc-sections','--strip-all','--wrap=main','-T','config/x86_64_wide_program.ld',
         '-Map='+str(directory/'udp.map'),'-o',elf,start,*objects])
    raw=elf.read_bytes();prepare(raw,[],True)
    (directory/'root/udp.prg').write_bytes(raw)
    return elf
