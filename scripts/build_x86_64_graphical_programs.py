"""Native graphical userspace build inputs, pinned vendor SHA-256 only."""
from pathlib import Path
import os,struct,subprocess,hashlib
from build_user_sdk import extract_mbedtls
ROOT=Path(__file__).resolve().parents[1]
MAKE_SELECTOR='''# BI explicit Ring3 graphical session; no additional kernel selector.
X86_64_NATIVE_GRAPHICAL_SESSION ?= 0
ifneq ($(words $(X86_64_NATIVE_GRAPHICAL_SESSION)),1)
$(error NativeGraphicalSession selector must be one explicit value)
endif
ifneq ($(filter $(X86_64_NATIVE_GRAPHICAL_SESSION),0 1),$(X86_64_NATIVE_GRAPHICAL_SESSION))
$(error NativeGraphicalSession selector must be 0 or 1)
endif
ifeq ($(X86_64_NATIVE_GRAPHICAL_SESSION),1)
ifneq ($(X86_64_NATIVE_TERMINAL_SERVICE),1)
$(error NativeGraphicalSession requires explicit NativeTerminalService)
endif
endif
'''
MAKE_PACKAGE='''# BI graphical package; caller may select a different admitted build directory.
.PHONY: x86_64-graphical-media
X86_64_GRAPHICAL_MEDIA_INPUT ?= build/codex-agent/r83bi-graphical-session/build07/x86_64
X86_64_GRAPHICAL_MEDIA_OUTPUT ?= build/codex-agent/r83bi-graphical-session/media07
x86_64-graphical-media:
	@$(PYTHON) scripts/build_x86_64_graphical_media.py --input-directory "$(X86_64_GRAPHICAL_MEDIA_INPUT)" --output-directory "$(X86_64_GRAPHICAL_MEDIA_OUTPUT)" --nasm "$(AS)" --openssl "$(OPENSSL)"
# End BI packaging target.
'''
MAKE_PARTS=(MAKE_SELECTOR,
    'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_GRAPHICAL_SESSION)),--graphical-session,)\n',MAKE_PACKAGE)
PS_PARTS=('    [switch]$NativeGraphicalSession,\n',
    'if ($NativeGraphicalSession) { $NativeTerminalService = [switch]$true }\n',
    '        "X86_64_NATIVE_GRAPHICAL_SESSION=$([int]$NativeGraphicalSession.IsPresent)" `\n')

def without_graphical_build_selector(source,make=False):
    tokens=('NATIVE_GRAPHICAL_SESSION','NativeGraphicalSession','--graphical-session','X86_64_GRAPHICAL_MEDIA','x86_64-graphical-media')
    if not any(t in source for t in tokens):return source
    for part in MAKE_PARTS if make else PS_PARTS:
        if source.count(part)!=1:raise ValueError('exact complete graphical build selector')
        source=source.replace(part,'')
    if any(t in source for t in tokens):raise ValueError('unreviewed graphical recipe')
    return source

def hash_inputs(directory,freestanding=False):
    vendor=extract_mbedtls(Path(directory)/'mbedtls')
    includes=[ROOT/'userspace/sdk/lib/x86_64',vendor/'tf-psa-crypto/include',
        vendor/'tf-psa-crypto/core',vendor/'tf-psa-crypto/drivers/builtin/include',
        vendor/'tf-psa-crypto/drivers/builtin/src',vendor/'tf-psa-crypto/platform']
    flags=['-DTF_PSA_CRYPTO_CONFIG_FILE="graphical_hash_config.h"',
        *['-I'+str(p) for p in includes]]
    if freestanding:flags+=['-DREIST_GRAPHICAL_FREESTANDING=1','-Iuserspace/tls/lib/compat']
    return [ROOT/'userspace/sdk/lib/x86_64/graphical_hash.c',
        vendor/'tf-psa-crypto/drivers/builtin/src/sha256.c'],flags

def font_header(directory):
    raw=(ROOT/'assets/fonts/reist-vga.psf').read_bytes()
    if len(raw)!=4944 or struct.unpack_from('<8I',raw)!=(0x864ab572,0,32,1,257,16,16,8):
        raise ValueError('pinned conventional PSF2 8x16 asset required')
    path=Path(directory)/'native_font.h'
    path.write_text('static const unsigned char native_font[2048]={'+
        ','.join(map(str,raw[32:32+2048]))+'};\n',encoding='ascii')
    return path

def build_roles(directory,cc,nasm,ld):
    from build_x86_64_boot_programs import prepare
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    environment=os.environ.copy()
    environment['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    environment['ZIG_LOCAL_CACHE_DIR']=str(directory/'zig-cache')
    def run(command):
        r=subprocess.run(list(map(str,command)),cwd=ROOT,env=environment,capture_output=True,timeout=60,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'graphical-build.log').open('ab') as log:log.write(r.stdout+r.stderr)
        if r.returncode:raise ValueError((r.stdout+r.stderr).decode(errors='replace')[-3200:])
    font_header(directory)
    common=[*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
        '-mno-mmx','-mno-sse','-mno-sse2','-ffunction-sections','-fdata-sections',
        '-Iuserspace/sdk/include','-Iuserspace/gui/include','-I'+str(directory)]
    runtime=['userspace/gui/lib/native_surface.c']
    roles={
        'desktop':runtime+['userspace/gui/compositor/native_desktop.c','userspace/gui/compositor/native_session.c',
            'userspace/gui/compositor/native_render.c','userspace/gui/compositor/desktop_wm.c',
            'userspace/gui/compositor/desktop_surface.c','userspace/gui/lib/font_catalog.c',
            'userspace/sdk/lib/x86_64/graphical_session.c'],
        'input':runtime+['userspace/drivers/ps2/native_session.c','userspace/drivers/ps2/native_input.c',
            'userspace/sdk/lib/x86_64/graphical_session.c'],
        'text':runtime+['userspace/gui/apps/native_client.c','userspace/gui/lib/surface_client.c','userspace/gui/lib/font_catalog.c'],
        'paint':runtime+['userspace/gui/apps/native_client.c','userspace/gui/lib/surface_client.c','userspace/gui/lib/font_catalog.c']}
    start=directory/'graphical-start.o'
    run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    digests=[]
    for name,sources in roles.items():
        objects=[]
        for n,source in enumerate(sources):
            obj=directory/f'graphical-{name}-{n}.o'
            run([*common,'-DREIST_NATIVE_CLIENT='+str(int(name=='paint')),'-c',source,'-o',obj]);objects.append(obj)
        elf=directory/(name+'.prg')
        run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
            '-z','noexecstack','--gc-sections','--strip-all','-T','config/x86_64_wide_program.ld',
            '-Map='+str(directory/(name+'.map')),'-o',elf,start,*objects])
        raw=elf.read_bytes();prepared=prepare(raw,[],True)
        digests.append(hashlib.sha256(prepared[:262240]).digest())
    (directory/'graphical_manifest.h').write_text('static const unsigned char graphical_hashes[4][32]={'+
        ','.join('{'+','.join(map(str,d))+'}' for d in digests)+'};\n',encoding='ascii')
    return tuple(directory/(name+'.prg') for name in roles)
