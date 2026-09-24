"""Explicit large immutable data fixture; conventional filesystem formats."""
import inspect
import build_x86_64_wide_file_media as previous
LAYOUTS=previous.LAYOUTS
source=inspect.getsource(previous.image)
for old,new in [('524288','1048576'),('1024*1024-len(raw)','2*1024*1024-len(raw)'),('One1MiB group','One2MiB group')]:
    if source.count(old)!=1:raise ValueError('large media producer binding '+old)
    source=source.replace(old,new)
# A 1MiB EXT2-1k negative fixture requires three double-indirect leaf blocks.
# Keep the fixture structurally valid so unsupported access, rather than
# overwritten pointer blocks, is the reason the unchanged parser rejects it.
for old,new in [
 ('        overhead=int(count>12)+2*int(count>12+entries)',
  '        leaves=(max(0,count-12-entries)+entries-1)//entries\n'
  '        overhead=int(count>12)+(1+leaves if leaves else 0)'),
 ('            w32(inode+40+13*4,double);w32(double*bs,leaf)\n'
  '            for n in range(count-12-entries):w32(leaf*bs+4*n,start+12+entries+n)',
  '            w32(inode+40+13*4,double)\n'
  '            for k in range(leaves):\n'
  '                w32(double*bs+4*k,leaf+k)\n'
  '                for n in range(min(entries,count-12-entries-k*entries)):\n'
  '                    w32((leaf+k)*bs+4*n,start+12+entries+k*entries+n)'),
 ('        if count>12+entries:occupied|={double,leaf}',
  '        if leaves:occupied|={double}|set(range(leaf,leaf+leaves))')]:
    if source.count(old)!=1:raise ValueError('large negative EXT2 fixture binding')
    source=source.replace(old,new)
namespace=dict(vars(previous));exec(compile(source,'<large-file-media>','exec'),namespace)
image=namespace['image']

def build_tool(directory,cc,nasm,ld):
    """Build the real ordinary consumer; pad only nonloaded file bytes."""
    from pathlib import Path
    import os,subprocess
    from build_x86_64_large_image import prepare
    root=Path(__file__).resolve().parents[1];directory=Path(directory)
    env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(root/'build/zig-global-cache'),ZIG_LOCAL_CACHE_DIR=str(directory/'large-cache'))
    def run(command):
        result=subprocess.run(list(map(str,command)),cwd=root,env=env,capture_output=True,timeout=90,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'large-file-build.log').open('ab') as out:out.write(result.stdout+result.stderr)
        if result.returncode:raise ValueError(result.stderr.decode(errors='replace')[-2400:])
    start=directory/'large-start.o';obj=directory/'largetest.o';elf=directory/'largetest.prg'
    run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-fstack-usage',
        '-Iuserspace/sdk/include','-c','userspace/programs/largetest.c','-o',obj])
    console=directory/'large-console.o'
    run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
        '-Iuserspace/sdk/include','-c','userspace/sdk/lib/x86_64/console.c','-o',console])
    run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined','-z','noexecstack',
        '--strip-all','-Map='+str(directory/'largetest.map'),'-T','config/x86_64_large_program.ld','-o',elf,start,obj,console])
    raw=elf.read_bytes();prepare(raw,[])
    if not 64<=len(raw)<1048576:raise ValueError('large fixture unpadded size')
    (directory/'largetest.unpadded.prg').write_bytes(raw)
    padded=raw+bytes(1048576-len(raw));prepare(padded,[]);elf.write_bytes(padded)
    install=directory/'root/bin';install.mkdir(parents=True,exist_ok=True)
    (install/'largetest.prg').write_bytes(padded)
