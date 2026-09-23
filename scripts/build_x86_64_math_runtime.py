"""Native musl binary64 archive and ordinary mathtest, separate from i386."""
from pathlib import Path
import os,subprocess
import build_user_math as math
from build_user_program import validate_cpp_object
ROOT=Path(__file__).resolve().parents[1]

def build_tool(directory,cc,nasm,ld):
    from build_x86_64_boot_programs import prepare
    directory=Path(directory);env=os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(directory/'math-cache')
    root=directory/'cpp-sysroot';lib=root/'usr/lib'
    if not lib.is_dir():raise ValueError('native math requires explicit C/C++ sysroot')
    def run(command):
        p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=90,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'math-runtime-build.log').open('ab') as out:out.write(p.stdout+p.stderr)
        if p.returncode:raise ValueError((p.stdout+p.stderr).decode(errors='replace')[-2400:])
    work=directory/'math-native';work.mkdir();vendor=math.extract(work/'upstream',architecture='x86_64')
    objects=math.compile_math(Path(cc[0]),vendor,work,env,architecture='x86_64')
    for obj in objects:validate_cpp_object(obj.read_bytes(),architecture='x86_64')
    archive=lib/'libm.a';run([cc[0],'ar','rcs',archive,*objects])
    validate_cpp_object(archive.read_bytes(),architecture='x86_64')
    for p in math.PUBLIC.glob('*.h'):math.copy_changed(p,root/'usr/include/reist/math'/p.name)
    for n in math.NATIVE_MEMBERS:math.copy_changed(vendor/n,root/'usr/share/licenses/musl-math'/n)
    metadata=lib/'pkgconfig/reistmath.pc';metadata.parent.mkdir(exist_ok=True)
    metadata.write_text('prefix=${pcfiledir}/../..\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\n'
        'Name: reistmath\nDescription: REIST native AMD64 binary64 math subset (musl 1.2.6)\n'
        'Version: 1.0.0\nCflags: -I${includedir}/reist/math\nLibs: -L${libdir} -lm\n',encoding='ascii')
    common=[*cc,'-target','x86_64-freestanding-none','-march=x86_64','-Oz','-std=c11',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-ffreestanding','-nostdlib','-fno-builtin',
        '-fno-pic','-fno-pie','-fno-stack-protector','-fno-sanitize=all','-mno-red-zone',
        '-msse2','-mno-avx','-mno-mmx','-frounding-math','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
        '-ffunction-sections','-fdata-sections','-fstack-usage','-DREIST_NATIVE_MATH_RUNTIME=1',
        '-Iuserspace/math/include','-Iuserspace/sdk/include','-Iuserspace/libc/include']
    obj=directory/'math-consumer.o';run([*common,'-c','userspace/programs/mathtest.c','-o',obj])
    validate_cpp_object(obj.read_bytes(),architecture='x86_64')
    elf=directory/'mathtest.prg'
    run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
        '-z','noexecstack','--gc-sections','--strip-all','-T','config/x86_64_wide_program.ld',
        '-Map='+str(directory/'math.map'),'-o',elf,lib/'crt0.o',obj,'--start-group',
        archive,lib/'libreistc.a',lib/'libreistos-native.a','--end-group'])
    raw=elf.read_bytes();validate_cpp_object(raw,architecture='x86_64');prepare(raw,[],True)
    (directory/'root/mathtest.prg').write_bytes(raw);return elf
