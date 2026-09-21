"""Ordinary native tools and their common explicit immutable-data image layouts."""
from pathlib import Path
import os,subprocess
ROOT=Path(__file__).resolve().parents[1]
MAKE_SELECTOR='''# BC explicit Ring3 application objects; old/default profiles remain unchanged.
X86_64_NATIVE_APP_FILES ?= 0
ifneq ($(words $(X86_64_NATIVE_APP_FILES)),1)
$(error NativeAppFiles selector must be one explicit value)
endif
ifneq ($(filter $(X86_64_NATIVE_APP_FILES),0 1),$(X86_64_NATIVE_APP_FILES))
$(error NativeAppFiles selector must be 0 or 1)
endif
ifeq ($(X86_64_NATIVE_APP_FILES),1)
ifneq ($(X86_64_NATIVE_WIDE_FILE),1)
$(error NativeAppFiles requires explicit NativeWideFile)
endif
endif
'''

def without_app_build_selector(source,make=False):
    """Remove only this complete opt-in addition; reject drift/extra tokens."""
    parts=(MAKE_SELECTOR,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_APP_FILES)),--app-files,)\n') if make else (
        '    [switch]$NativeAppFiles,\n','if ($NativeAppFiles) { $NativeWideFile = [switch]$true }\n',
        '        "X86_64_NATIVE_APP_FILES=$([int]$NativeAppFiles.IsPresent)" `\n')
    tokens=('NATIVE_APP_FILES','NativeAppFiles','--app-files')
    if not any(t in source for t in tokens):return source
    for part in parts:
        if source.count(part)!=1:raise ValueError('exact application build selector')
        source=source.replace(part,'')
    if any(t in source for t in tokens):raise ValueError('unexpected application selector use')
    return source

def build_tools(directory,cc,nasm,ld):
    from build_x86_64_boot_programs import prepare
    from build_x86_64_app_files_media import DATA,LAYOUTS,image
    from check_x86_64_app_files_media import verify
    directory=Path(directory);environment=os.environ.copy()
    environment.setdefault('ZIG_GLOBAL_CACHE_DIR',str(ROOT/'build/zig-global-cache'))
    environment.setdefault('ZIG_LOCAL_CACHE_DIR',str(directory/'zig-cache'))
    def run(args):
        result=subprocess.run(list(map(str,args)),cwd=ROOT,env=environment,capture_output=True,timeout=60,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'app-files-build.log').open('ab') as log:log.write(result.stdout+result.stderr)
        if result.returncode:raise ValueError('native tool build: '+(result.stdout+result.stderr).decode(errors='replace')[-3000:])
    start=directory/'app-start.o';run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    files={'boot.prg':(directory/'file-program.prg').read_bytes(),'data.txt':DATA}
    common=[*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2',
        '-ffunction-sections','-fdata-sections','-Iuserspace/sdk/include','-Iuserspace/storage/include']
    for name in ('cat','ls','probe'):
        objects=[]
        sources=['userspace/sdk/lib/x86_64/app_files.c']
        if name=='probe':sources+=['arch/x86_64/user/app_files_probe.c']
        else:sources+=['userspace/sdk/lib/x86_64/app_file_platform.c',f'userspace/programs/{name}.c']
        for n,source in enumerate(sources):
            obj=directory/f'app-{name}-{n}.o'
            run([*common,*(['-DREIST_APP_LS=1'] if name=='ls' else []),'-c',source,'-o',obj]);objects.append(obj)
        elf=directory/(name+'.prg')
        run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
            '-z','noexecstack','--gc-sections','--strip-all','--wrap=main','-T','config/x86_64_wide_program.ld',
            '-Map='+str(directory/('app-'+name+'.map')),'-o',elf,start,*objects])
        raw=elf.read_bytes();prepare(raw,[],True);files[name+'.prg']=raw
    install=directory/'root';install.mkdir(exist_ok=True)
    for name,value in files.items():(install/name).write_bytes(value)
    for layout in LAYOUTS:
        raw=image(layout,files);verify(raw,layout,files)
        (directory/('app-files-'+layout+'.raw')).write_bytes(raw)
    return files

def build_budget_probe(directory,original,zig):
    """One test-only external ELF; never rebuild/overwrite normal image or tools."""
    from build_x86_64_boot_programs import prepare
    directory=Path(directory);original=Path(original)
    if directory.exists():raise ValueError('fresh budget-client build only')
    directory.mkdir(parents=True)
    environment=os.environ.copy()
    environment['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    environment['ZIG_LOCAL_CACHE_DIR']=str(directory/'zig-cache')
    obj=directory/'budget-probe.o';elf=directory/'probe.prg'
    commands=[
        [str(zig),'cc','-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
         '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
         '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2',
         '-ffunction-sections','-fdata-sections','-Iuserspace/sdk/include','-Iuserspace/storage/include',
         '-DREIST_APP_BUDGET_CLIENT=1','-c','arch/x86_64/user/app_files_probe.c','-o',str(obj)],
        [str(zig),'ld.lld','-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
         '-z','noexecstack','--gc-sections','--strip-all','--wrap=main','-T','config/x86_64_wide_program.ld',
         '-Map='+str(directory/'app-probe.map'),'-o',str(elf),str(original/'app-start.o'),
         str(original/'app-probe-0.o'),str(obj)]]
    for n,args in enumerate(commands):
        result=subprocess.run(args,cwd=ROOT,env=environment,capture_output=True,timeout=60,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (directory/f'command-{n}.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError('budget probe build: '+result.stderr.decode(errors='replace')[-2000:])
    prepare(elf.read_bytes(),[],True)
    return commands
