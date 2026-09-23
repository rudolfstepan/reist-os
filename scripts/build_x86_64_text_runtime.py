"""Native bounded formatter archive and ordinary texttest, separate from i386."""
from pathlib import Path
import os,subprocess
import build_user_text as text
from build_user_program import validate_cpp_object
ROOT=Path(__file__).resolve().parents[1]

def build_tool(directory,cc,nasm,ld):
    from build_x86_64_boot_programs import prepare
    directory=Path(directory);env=os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(directory/'text-cache')
    root=directory/'cpp-sysroot';lib=root/'usr/lib'
    if not lib.is_dir():raise ValueError('native text requires explicit C/C++ sysroot')
    def run(command):
        p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=90,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'text-runtime-build.log').open('ab') as out:out.write(p.stdout+p.stderr)
        if p.returncode:raise ValueError((p.stdout+p.stderr).decode(errors='replace')[-2400:])
    work=directory/'text-native';work.mkdir();vendor=text.extract(work/'upstream')
    objects=text.compile_text(Path(cc[0]),vendor,work,env,architecture='x86_64')
    for obj in objects:validate_cpp_object(obj.read_bytes(),architecture='x86_64')
    archive=lib/'libreisttext.a';run([cc[0],'ar','rcs',archive,*objects])
    validate_cpp_object(archive.read_bytes(),architecture='x86_64')
    for p in (text.TEXT/'include').glob('*.h'):text.copy_changed(p,root/'usr/include/reist/text'/p.name)
    for n in text.MEMBERS:text.copy_changed(vendor/n,root/'usr/share/licenses/musl-text'/n)
    metadata=lib/'pkgconfig/reisttext.pc';metadata.parent.mkdir(exist_ok=True)
    metadata.write_text('prefix=${pcfiledir}/../..\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\n'
        'Name: reisttext\nDescription: REIST native AMD64 bounded string formatting subset (musl 1.2.6)\n'
        'Version: 1.0.0\nCflags: -I${includedir}/reist/text -I${includedir}/reist/math -I${includedir}/reist/libc\nLibs: -L${libdir} -lreisttext -lm -lreistc\n',encoding='ascii')
    common=[*cc,'-target','x86_64-freestanding-none','-march=x86_64','-Oz','-std=c11',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-ffreestanding','-nostdlib','-fno-builtin',
        '-fno-pic','-fno-pie','-fno-stack-protector','-fno-sanitize=all','-mno-red-zone',
        '-msse2','-mno-avx','-mno-mmx','-frounding-math','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
        '-ffunction-sections','-fdata-sections','-fstack-usage','-DREIST_NATIVE_TEXT_RUNTIME=1',
        '-Iuserspace/text/include','-Iuserspace/math/include','-Iuserspace/sdk/include','-Iuserspace/libc/include']
    obj=directory/'text-consumer.o';run([*common,'-c','userspace/programs/texttest.c','-o',obj])
    validate_cpp_object(obj.read_bytes(),architecture='x86_64')
    elf=directory/'texttest.prg'
    run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
        '-z','noexecstack','--gc-sections','--strip-all','-T','config/x86_64_wide_program.ld',
        '-Map='+str(directory/'text.map'),'-o',elf,lib/'crt0.o',obj,'--start-group',
        archive,lib/'libm.a',lib/'libreistc.a',lib/'libreistos-native.a','--end-group'])
    raw=elf.read_bytes();validate_cpp_object(raw,architecture='x86_64');prepare(raw,[],True)
    (directory/'root/texttest.prg').write_bytes(raw);return elf
