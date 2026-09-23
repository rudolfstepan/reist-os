"""Explicit AMD64 libc/C++ sysroot subset and ordinary cpptest consumer."""
from pathlib import Path
import os,subprocess,shutil
from build_user_program import cpp_compile_flags,validate_cpp_object
ROOT=Path(__file__).resolve().parents[1]

def build_tool(directory,cc,nasm,ld):
    from build_x86_64_boot_programs import prepare
    directory=Path(directory);env=os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(directory/'zig-cache')
    def run(command):
        p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=90,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'cpp-runtime-build.log').open('ab') as f:f.write(p.stdout+p.stderr)
        if p.returncode:raise ValueError((p.stdout+p.stderr).decode(errors='replace')[-2500:])
    common=[*cc,'-target','x86_64-freestanding-none','-Oz','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-fno-sanitize=all',
        '-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
        '-mno-mmx','-mno-sse','-mno-sse2','-ffunction-sections','-fdata-sections','-fstack-usage',
        '-Iuserspace/sdk/include','-Iuserspace/libc/include','-Iuserspace/cpp/include',
        '-DREIST_NATIVE_CPP_RUNTIME=1']
    root=directory/'cpp-sysroot';lib=root/'usr/lib';lib.mkdir(parents=True)
    for source,target in [('userspace/libc/include','reist/libc'),('userspace/cpp/include','reist/cpp'),
                          ('userspace/sdk/include','')]:
        shutil.copytree(ROOT/source,root/'usr/include'/target,dirs_exist_ok=True)
    groups={'reistc':['userspace/libc/lib/'+n+'.c' for n in ('heap','bytes','runtime','process_heap')],
            'reistcpp':['userspace/cpp/runtime.cpp'],
            'reistos-native':['userspace/sdk/lib/x86_64/cpp_runtime.c']}
    archives=[]
    for group,sources in groups.items():
        objects=[]
        for n,source in enumerate(sources):
            obj=directory/f'cpp-{group}-{n}.o'
            flags=cpp_compile_flags() if source.endswith('.cpp') else ['-std=c11']
            run([*common,*flags,'-c',source,'-o',obj])
            validate_cpp_object(obj.read_bytes(),architecture='x86_64');objects.append(obj)
        archive=lib/('lib'+group+'.a')
        run([cc[0],'ar','rcs',archive,*objects])
        validate_cpp_object(archive.read_bytes(),architecture='x86_64');archives.append(archive)
    start=lib/'crt0.o';run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    obj=directory/'cpp-consumer.o'
    run([*common,*cpp_compile_flags(),'-Wno-unused-function','-c','userspace/programs/cpptest.cpp','-o',obj])
    validate_cpp_object(obj.read_bytes(),architecture='x86_64')
    elf=directory/'cpptest.prg'
    run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
        '-z','noexecstack','--gc-sections','--strip-all','-T','config/x86_64_wide_program.ld',
        '-Map='+str(directory/'cpp.map'),'-o',elf,start,obj,'--start-group',*archives,'--end-group'])
    raw=elf.read_bytes();validate_cpp_object(raw,architecture='x86_64');prepare(raw,[],True)
    (directory/'root/cpptest.prg').write_bytes(raw)
    return elf
