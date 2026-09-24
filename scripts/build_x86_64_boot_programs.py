"""External ELF64 preparation. Never linked into Ring0; no runtime file rights."""
from pathlib import Path
import argparse, os, struct, subprocess, uuid, sys
ROOT=Path(__file__).resolve().parents[1]
SIZE=36896

def prepare(raw,args,wide=False):
    slots=64 if wide else 8; extent=slots*4096; limit=0x400000+extent
    def need(condition):
        if not condition:raise ValueError('unsupported/malformed bounded ELF64 or arguments')
    need(64<=len(raw)<=(524288 if wide else 65536))
    need(raw[:16]==b'\x7fELF\x02\x01\x01'+bytes(9))
    typ,machine,version,entry,phoff,_,flags,ehsize,phsize,count,_,_,_=struct.unpack_from('<HHIQQQIHHHHHH',raw,16)
    need((typ,machine,version,flags,ehsize,phsize)==(2,62,1,0,64,56))
    need(1<=count<=8 and 64<=phoff<=len(raw)-count*56)
    pages=bytearray(extent);rights=bytearray(slots);executable=False;previous=0
    for n in range(count):
        kind,pf,offset,va,_,filesz,memsz,align=struct.unpack_from('<II6Q',raw,phoff+n*56)
        if kind==0:continue
        need(kind==1 and pf in (4,5,6) and align==4096)
        need(0<memsz<=extent and filesz<=memsz and offset<=len(raw) and filesz<=len(raw)-offset)
        need(0x400000<=va<limit and memsz<=limit-va and va>=previous)
        need((offset^va)&4095==0)
        first=(va-0x400000)//4096;last=(va+memsz-1-0x400000)//4096
        need(not wide or first>15 or last<7)
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
    if wide:
        rights[9:16]=bytes([6])*7
        return b'RNPGv2\0\0'+struct.pack('<IIQ',2,266336,entry)+rights+bytes(8)+pages+source
    return b'RNPGv1\0\0'+struct.pack('<IIQ',1,SIZE,entry)+rights+pages+source

def build_file_program(directory,cc,nasm,ld):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    environment=os.environ.copy()
    environment.setdefault('ZIG_GLOBAL_CACHE_DIR',str(ROOT/'build/zig-global-cache'))
    environment.setdefault('ZIG_LOCAL_CACHE_DIR',str(directory/'zig-cache'))
    start=directory/'file-start.o';obj=directory/'file-program.o';elf=directory/'file-program.prg'
    wide_file='-DREIST_NATIVE_WIDE_FILE=1' in cc
    commands=[[*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start],
        ([*nasm,'-f','elf64','arch/x86_64/user/wide_file_program.asm' if wide_file else 'arch/x86_64/user/shell_session_program.asm' if '-DREIST_NATIVE_SHELL_SESSION=1' in cc else 'arch/x86_64/user/terminal_program.asm','-o',obj] if '-DREIST_NATIVE_TERMINAL=1' in cc else
         [*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','arch/x86_64/user/file_program.c','-o',obj]),
        [*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined','-z','noexecstack','--strip-all','-T','config/x86_64_wide_program.ld' if wide_file else 'config/x86_64_file_program.ld','-o',elf,start,obj]]
    if '-DREIST_NATIVE_DISPLAY=1' in cc:
        commands[1]=[*cc,'-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','arch/x86_64/user/input_client.c' if '-DREIST_NATIVE_INPUT=1' in cc else 'arch/x86_64/user/display_probe.c','-o',obj]
    for command in commands:
        r=subprocess.run(list(map(str,command)),cwd=ROOT,env=environment,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (directory/'file-build.log').open('ab') as log:log.write(r.stdout+r.stderr)
        if r.returncode:raise ValueError('file program build: '+(r.stdout+r.stderr).decode(errors='replace')[-2000:])
    raw=elf.read_bytes()
    limit=524288 if wide_file else 1280 if '-DREIST_NATIVE_LIVE_FILE=1' in cc else 1536
    if not 64<=len(raw)<=limit:raise ValueError('file program exceeds existing8-RPC capture bound: '+str(len(raw)))
    prepare(raw,[],True);return raw

def build(directory,cc,nasm,ld,case,family=False,family_case=0,startup=False,startup_case=0,import_image=False,pio=False,pio_case=0,block=False,wide=False,memory_case=0,block_profile=False,block_profile_case=0,filesystem=False,filesystem_case=0,filesystem_layout=2,file_launch=False,file_launch_case=0,task_pool=False,pool_pio=False,service_cpu=False,service_pio=False,live_file=False,console=False,native_shell=False,service_console=False,terminal=False,session=False,shell_session=False,wide_file=False,app_files=False,display=False,input=False,terminal_service=False,graphical_session=False,network_dma=False,network_session=False,app_network=False,app_tcp=False,app_dns=False,app_http=False,app_cpp_runtime=False,math_runtime=False,text_runtime=False,large_image=False,pio_throughput=False,large_file=False,display_info=False,large_periodic=False):
    if type(large_file) is not bool or large_file and (not large_image or not text_runtime or any((display,input,graphical_session,network_session))):raise ValueError("large file requires separate large image/text shell")
    if large_file:cc=[*cc,'-DREIST_NATIVE_LARGE_FILE=1']
    if type(large_periodic) is not bool or large_periodic and (not (large_image and wide and task_pool and service_cpu) or any((large_file,memory_case,pio,block,filesystem,shell_session,text_runtime,session))):
        raise ValueError('large periodic requires explicit device-free large service CPU')
    if large_periodic:cc=[*cc,'-DREIST_NATIVE_LARGE_PERIODIC=1']
    if type(large_image) is not bool or large_image and (not wide or not (large_file or large_periodic) and any((memory_case,pio,block,task_pool,service_cpu,filesystem,shell_session,text_runtime))):raise ValueError("large image requires plain NativeWide or explicit large file")
    if large_image:
        cc=[*cc,'-DREIST_NATIVE_LARGE_IMAGE=1']
    if type(text_runtime) is not bool or text_runtime and not math_runtime:raise ValueError("native text requires native math runtime")
    if type(math_runtime) is not bool or math_runtime and not app_cpp_runtime:raise ValueError("native math requires native C/C++ runtime")
    if type(app_cpp_runtime) is not bool or app_cpp_runtime and (not app_files or any((display,input,graphical_session,network_session))):raise ValueError("native C++ runtime requires separate application-file profile")
    if type(app_http) is not bool or app_http and not app_dns:raise ValueError("application HTTP requires DNS profile")
    if type(app_dns) is not bool or app_dns and not app_tcp:raise ValueError("application DNS requires TCP")
    if type(app_tcp) is not bool or app_tcp and not app_network:raise ValueError("application TCP requires application network")
    if type(app_network) is not bool or app_network and not network_session:raise ValueError("application network requires network session")
    if type(network_session) is not bool or network_session and (not network_dma or not app_files or display or input or terminal_service or graphical_session):raise ValueError("network session requires DMA/application files and excludes GUI")
    if type(network_dma) is not bool or network_dma and not network_session and (not task_pool or any((pool_pio,service_cpu,service_pio,console,graphical_session))):raise ValueError("network DMA requires separate plain task pool")
    if type(graphical_session) is not bool or graphical_session and not terminal_service:raise ValueError("graphical session requires terminal service profile")
    if type(terminal_service) is not bool or terminal_service and not input:raise ValueError("terminal service requires input profile")
    if type(input) is not bool or input and not display:raise ValueError("input requires display profile")
    if type(display) is not bool or display and not app_files:raise ValueError("display requires application-file profile")
    if type(app_files) is not bool or app_files and not wide_file:
        raise ValueError('application files require explicit wide file')
    if type(wide_file) is not bool or wide_file and not shell_session:
        raise ValueError('wide file requires explicit shell session')
    if type(shell_session) is not bool or shell_session and (not terminal or session or native_shell or service_cpu):
        raise ValueError('shell session requires explicit terminal service profile, excludes old shell/session fixtures')
    if type(session) is not bool or session and not service_cpu:raise ValueError('session requires explicit device-free service CPU')
    if type(terminal) is not bool or terminal and not service_console:raise ValueError('terminal requires explicit service console')
    if type(service_console) is not bool or service_console and (not live_file or console or native_shell):
        raise ValueError('service console requires live file and excludes console-only fixtures')
    if type(native_shell) is not bool or native_shell and not console:raise ValueError('native shell requires explicit console')
    if type(console) is not bool:raise ValueError('console selector')
    if console and (any((case,family,family_case,startup,startup_case,import_image,pio,pio_case,block,wide,memory_case,block_profile,block_profile_case,filesystem,filesystem_case,file_launch,file_launch_case,task_pool,pool_pio,service_cpu,service_pio,live_file)) or filesystem_layout!=2):
        raise ValueError('console requires plain native programs without other fixtures')
    if type(live_file) is not bool:raise ValueError('live file selector')
    if live_file and (not (pool_pio and filesystem and file_launch) or service_cpu or service_pio):
        raise ValueError('live file requires pool PIO and file launch, excludes other service fixtures')
    if type(service_pio) is not bool:raise ValueError('service PIO selector')
    if service_pio and (not pool_pio or service_cpu):raise ValueError('service PIO requires pool PIO and excludes service CPU')
    if type(service_cpu) is not bool:raise ValueError('service CPU selector')
    if service_cpu and (not task_pool or any((pool_pio,pio,block,block_profile,filesystem,file_launch))):
        raise ValueError('service CPU requires device-free task pool')
    if type(pool_pio) is not bool:raise ValueError('pool PIO selector')
    if pool_pio and (not (task_pool and wide and import_image and startup and family and pio and block and block_profile) or
        any((filesystem and not live_file,file_launch and not live_file,case,family_case,startup_case,pio_case,memory_case,block_profile_case,filesystem_case,file_launch_case)) or filesystem_layout!=2):
        raise ValueError('pool PIO requires complete pool/block profile and excludes other fixtures')
    if type(task_pool) is not bool:raise ValueError('task pool selector')
    if task_pool and (not (wide and import_image and startup and family) or
        any((pio and not pool_pio,block and not pool_pio,block_profile and not pool_pio,filesystem and not live_file,file_launch and not live_file,case,family_case,startup_case,
             pio_case,memory_case,block_profile_case,filesystem_case,file_launch_case)) or filesystem_layout!=2):
        raise ValueError('task pool requires plain wide import and excludes device/fault selectors')
    if type(file_launch) is not bool or type(file_launch_case) is not int or file_launch_case not in range(11):raise ValueError('file launch selector')
    if file_launch and (not filesystem or filesystem_case):raise ValueError('file launch requires plain filesystem')
    if file_launch_case and not file_launch:raise ValueError('file launch case requires selection')
    if type(filesystem) is not bool or filesystem_case not in range(9) or filesystem_layout not in range(5):raise ValueError('filesystem selector')
    if filesystem and (not block_profile or block_profile_case):raise ValueError('filesystem requires plain block profile')
    if not filesystem and (filesystem_case or filesystem_layout!=2):raise ValueError('filesystem options')
    if block_profile and (not (wide and import_image and pio and block) or memory_case or pio_case or startup_case):raise ValueError('block profile requires plain wide PIO block')
    if block_profile_case not in range(8) or (block_profile_case and not block_profile):raise ValueError('block profile case')
    if wide and not block_profile and (not import_image or pio or block or startup_case):raise ValueError("wide requires plain import")
    if memory_case not in range(7) or (memory_case and not wide):raise ValueError("memory case")
    if block and not pio:raise ValueError('block service requires PIO')
    if pio and (not import_image or startup_case):raise ValueError('PIO requires normal import')
    if pio_case not in range(4) or (pio_case and not pio):raise ValueError('PIO case')
    if import_image and not startup:raise ValueError('import requires startup')
    if startup and (not family or family_case or case):raise ValueError('startup requires normal family')
    if network_dma:cc=[*cc,'-DREIST_NATIVE_NETWORK_DMA=1']
    if type(pio_throughput) is not bool or pio_throughput and (not pool_pio or service_cpu or service_pio or live_file):raise ValueError('PIO throughput fixture requires plain pool PIO')
    if pio_throughput:cc=[*cc,'-DREIST_NATIVE_PIO_THROUGHPUT=1']
    if pool_pio:cc=[*cc,'-DREIST_NATIVE_POOL_PIO=1']
    if service_cpu:cc=[*cc,'-DREIST_NATIVE_SERVICE_CPU=1',*([] if large_periodic else ['-Dmain=reist_pool_finite_fixture_main'])]
    if service_pio:cc=[*cc,'-DREIST_NATIVE_SERVICE_CPU=1','-DREIST_NATIVE_SERVICE_PIO=1']
    if live_file:cc=[*cc,'-DREIST_NATIVE_SERVICE_CPU=1','-DREIST_NATIVE_LIVE_FILE=1']
    if service_console:cc=[*cc,'-DREIST_NATIVE_SERVICE_CONSOLE=1']
    if terminal:cc=[*cc,'-DREIST_NATIVE_TERMINAL=1']
    if session:cc=[*cc,'-DREIST_NATIVE_SESSION=1']
    if shell_session:cc=[*cc,'-DREIST_NATIVE_SESSION=1','-DREIST_NATIVE_SHELL_SESSION=1']
    if wide_file:cc=[*cc,'-DREIST_NATIVE_WIDE_FILE=1']
    if app_files:cc=[*cc,'-DREIST_NATIVE_APP_FILES=1']
    if type(display_info) is not bool or display_info and not display:raise ValueError("display info requires display")
    if display_info:cc=[*cc,'-DREIST_NATIVE_DISPLAY_INFO=1']
    if display:cc=[*cc,'-DREIST_NATIVE_DISPLAY=1']
    if input:cc=[*cc,'-DREIST_NATIVE_INPUT=1']
    if terminal_service:cc=[*cc,'-DREIST_NATIVE_TERMINAL_SERVICE=1']
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    attempt=directory/('programs-'+uuid.uuid4().hex);attempt.mkdir()
    if graphical_session:cc=[*cc,'-DREIST_NATIVE_GRAPHICAL_SESSION=1','-I'+str(attempt)]
    if network_session:cc=[*cc,'-DREIST_NATIVE_NETWORK_SESSION=1','-I'+str(attempt)]
    if app_network:cc=[*cc,'-DREIST_NATIVE_APP_NETWORK=1']
    if app_tcp:cc=[*cc,'-DREIST_NATIVE_APP_TCP=1']
    if file_launch:build_file_program(attempt,cc,nasm,ld)
    if app_files:
        from build_x86_64_app_files import build_tools
        build_tools(attempt,cc,nasm,ld)
    if app_cpp_runtime:
        from build_x86_64_cpp_runtime import build_tool as build_cpp_tool
        build_cpp_tool(attempt,cc,nasm,ld)
    if math_runtime:
        from build_x86_64_math_runtime import build_tool as build_math_tool
        build_math_tool(attempt,cc,nasm,ld)
    if text_runtime:
        from build_x86_64_text_runtime import build_tool as build_text_tool
        build_text_tool(attempt,cc,nasm,ld)
    if large_file:
        from build_x86_64_large_file import build_tool as build_large_tool
        build_large_tool(attempt,cc,nasm,ld)
    if graphical_session:
        from build_x86_64_graphical_programs import build_roles,hash_inputs
        graphical_roles=build_roles(attempt,cc,nasm,ld)
        for role in graphical_roles:(attempt/'root'/role.name).write_bytes(role.read_bytes())
        graphical_hash_sources,graphical_hash_flags=hash_inputs(attempt,True)
    if network_session:
        from build_x86_64_network_programs import build_roles as network_roles
        from build_x86_64_graphical_programs import hash_inputs
        for role in network_roles(attempt,cc,nasm,ld,app_network,app_tcp,app_dns):(attempt/'root'/role.name).write_bytes(role.read_bytes())
        network_hash_sources,network_hash_flags=hash_inputs(attempt,True)
        if app_network:
            from build_x86_64_application_udp import build_tool
            build_tool(attempt,cc,nasm,ld)
        if app_tcp:
            from build_x86_64_application_tcp import build_tool as build_tcp_tool
            build_tcp_tool(attempt,cc,nasm,ld)
    if app_dns:
        from build_x86_64_application_dns import build_tool as build_dns_tool
        build_dns_tool(attempt,cc,nasm,ld)
        cc=[*cc,'-DREIST_NATIVE_APP_DNS=1']
    if app_http:
        from build_x86_64_application_http import build_tool as build_http_tool
        build_http_tool(attempt,cc,nasm,ld)
        cc=[*cc,'-DREIST_NATIVE_APP_HTTP=1']
    def run(args):
        r=subprocess.run(list(map(str,args)),cwd=ROOT,timeout=60,capture_output=True,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (attempt/'build.log').open('ab') as f:f.write(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-2000:])
    start=attempt/'start.o';run([*nasm,'-f','elf64','arch/x86_64/user/boot_start.asm','-o',start])
    if input and not graphical_session:
        input_objects=[]
        for index,source in enumerate(('arch/x86_64/user/input_service.c','userspace/drivers/ps2/native_input.c')):
            unit=attempt/f'input-{index}.o'
            run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c',source,'-o',unit])
            input_objects.append(unit)
        worker=attempt/'input-service.prg'
        run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined','-z','noexecstack','--strip-all','-T','config/x86_64_wide_program.ld','-o',worker,start,*input_objects])
        input_blob=worker.read_bytes();prepare(input_blob,[],True)
    records=[None]*4
    for n in ([2,3,0,1] if filesystem else [2,0,1,3] if import_image else range(4)):
        obj=attempt/f'program{n}.o';elf=attempt/f'program{n}.prg'
        extra=[];objects=[]
        shell_root=(native_shell or shell_session) and n==0
        if app_dns and shell_root:
            # Optimize across root SDK units within the existing image ceiling.
            # Restore the command vectors before building any independent role.
            cc=[*cc,'-flto'];ld=[*ld,'--lto-O2']
        if shell_root:
            for index,source in enumerate(('userspace/bin/shell_vfs.c','userspace/sdk/lib/x86_64/shell_platform.c')):
                unit=attempt/f'shell-{index}.o'
                run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-fstack-usage','-Iuserspace/sdk/include','-Iuserspace/storage/include','-c',source,'-o',unit])
                objects.append(unit)
            if shell_session:
                unit=attempt/'service-session.o'
                run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','userspace/sdk/lib/x86_64/service_session.c','-o',unit])
                objects.append(unit)
            if app_files:
                unit=attempt/'app-files.o'
                run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','userspace/sdk/lib/x86_64/app_files.c','-o',unit])
                objects.append(unit)
        if (graphical_session or network_session) and shell_root:
            role_sources=([ 'userspace/sdk/lib/x86_64/network_session.c',*network_hash_sources] if network_session else ['userspace/sdk/lib/x86_64/graphical_session.c',*graphical_hash_sources])
            if app_network:role_sources+=['userspace/sdk/lib/x86_64/application_udp.c']
            if app_tcp:role_sources+=['userspace/sdk/lib/x86_64/application_tcp.c']
            if app_dns:role_sources+=['userspace/sdk/lib/x86_64/application_dns.c']
            if app_http:role_sources+=['userspace/sdk/lib/x86_64/application_http.c']
            role_hash_flags=network_hash_flags if network_session else graphical_hash_flags
            for index,source in enumerate(role_sources):
                unit=attempt/f'graphical-root-{index}.o'
                run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-ffunction-sections','-fdata-sections','-Iuserspace/sdk/include',*role_hash_flags,'-c',source,'-o',unit])
                objects.append(unit)
        if console or shell_session and n==0:
            unit=attempt/f'console-{n}.o'
            run([*cc,'-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','userspace/sdk/lib/x86_64/console.c','-o',unit])
            objects.append(unit)
        if import_image and n==2:extra=['-DNATIVE_IMPORT_CHILD=1']
        if import_image and (n==0 or task_pool and not pool_pio and n==1):
            blob=(attempt/'program2.prg').read_bytes()
            # Writable input fixture is private to the Ring3 root; never a kernel parser.
            header=attempt/'import_blob.h'
            header.write_text('static const unsigned char import_blob[] __attribute__((section(".data.import_blob")))={'+','.join(str(b) for b in blob)+'};\n',encoding='ascii')
            if filesystem:
                fs_blob=(attempt/'program3.prg').read_bytes()
                with header.open('a',encoding='ascii') as output:
                    output.write('static const unsigned char filesystem_blob[] __attribute__((section(".data.import_blob")))={'+','.join(str(b) for b in fs_blob)+'};\n')
            if shell_session and n==0:
                with header.open('a',encoding='ascii') as output:
                    output.write('#include <reist/x86_64/shell_session.h>\nconst reist_shell_images reist_native_shell_images={import_blob,sizeof(import_blob),filesystem_blob,sizeof(filesystem_blob)};\n')
            if input and not graphical_session and n==0:
                with header.open('a',encoding='ascii') as output:
                    output.write('const unsigned char reist_native_input_image[]={'+','.join(str(b) for b in input_blob)+'};\nconst size_t reist_native_input_image_bytes=sizeof(reist_native_input_image);\n')
            extra=['-DNATIVE_IMPORT=1','-include',str(header)]
            parser=attempt/'image.o'
            run([*cc,'-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','userspace/sdk/lib/x86_64/image.c','-o',parser])
            objects.append(parser)
        if pio and n==2:
            driver=attempt/'ata-pio.o'
            run([*cc,'-target','x86_64-freestanding-none','-std=c11','-O2' if pio_throughput else '-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-c','userspace/drivers/ata/native_pio.c','-o',driver])
            objects.append(driver)
        if block and (n in (0,2) or filesystem and n==3):
            sources=['userspace/storage/lib/native_block.c']
            if n==2:sources+=['userspace/drivers/ata/native_service.c']
            if filesystem and n in (0,3):sources+=['userspace/storage/lib/native_filesystem.c']
            if filesystem and n==3:sources+=['userspace/storage/lib/vfs_shadow_fat32.c','userspace/storage/lib/vfs_shadow_ext2.c']
            if file_launch and n==0:sources+=['userspace/sdk/lib/x86_64/file_image.c']
            for index,source in enumerate(sources):
                unit=attempt/f'block-{n}-{index}.o'
                run([*cc,'-target','x86_64-freestanding-none','-std=c11','-O2' if pio_throughput else '-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-ffunction-sections','-fdata-sections','-Iuserspace/sdk/include','-c',source,'-o',unit])
                objects.append(unit)
        run([*cc,'-target','x86_64-freestanding-none','-std=c11','-Oz' if shell_root or pio and not pool_pio else '-O2','-Wall','-Wextra','-Werror',
             '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
             '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
             '-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include',
             f'-DPROGRAM_ID={n}',f'-DPROGRAM_CASE={case}',f'-DFAMILY_CASE={family_case}',f'-DSTARTUP_CASE={startup_case}',
             f'-DPIO_CASE={pio_case}',f'-DMEMORY_CASE={memory_case}',f'-DBLOCK_PROFILE_CASE={block_profile_case}',
             *([f'-DFILESYSTEM_CASE={filesystem_case}',f'-DFILESYSTEM_LAYOUT={filesystem_layout}'] if filesystem else []),
             *([f'-DFILE_LAUNCH_CASE={file_launch_case}'] if file_launch else []),
             *(['-fstack-usage'] if shell_root else []),
             *(['-DREIST_SESSION_GUEST=1'] if session and n<2 else []),
             *extra,'-c','arch/x86_64/user/large_image.c' if large_periodic else 'arch/x86_64/user/network_dma.c' if network_dma and not network_session else 'test/x86_64_session_admission_host.c' if session and n<2 else 'userspace/bin/shell.c' if shell_root else 'arch/x86_64/user/console.c' if console else 'arch/x86_64/user/service_console.c' if service_console else 'arch/x86_64/user/live_file.c' if live_file else 'arch/x86_64/user/pool_pio.c' if pool_pio else 'arch/x86_64/user/task_pool.c' if task_pool else 'arch/x86_64/user/file_launch.c' if file_launch else 'arch/x86_64/user/filesystem.c' if filesystem else 'arch/x86_64/user/block_profile.c' if block_profile else 'arch/x86_64/user/large_image.c' if large_image else 'arch/x86_64/user/program_memory.c' if wide else 'arch/x86_64/user/block_service.c' if block else 'arch/x86_64/user/pio_domain.c' if pio else 'arch/x86_64/user/task_startup.c' if startup else 'arch/x86_64/user/task_family.c' if family else 'arch/x86_64/user/boot_program.c','-o',obj])
        run([*ld,'-m','elf_x86_64','-nostdlib','--build-id=none','--fatal-warnings','--no-undefined',
             '-z','noexecstack','--strip-all',f'--defsym=PROGRAM_LAYOUT={n}',
             *(['-Map='+str(attempt/f'program{n}.map')] if large_image else []),
             *(['--wrap=main'] if session and n<2 else []),
             *(['--wrap=main'] if shell_session and n==0 else []),
             *(['--gc-sections','--defsym=PROGRAM_SERVICE=1','-Map='+str(attempt/f'program{n}.map')] if block else []),
             '-T','config/x86_64_native_shell.ld' if shell_root and not shell_session else 'config/x86_64_large_program.ld' if large_image and not large_file and n==2 else 'config/x86_64_wide_program.ld' if wide else 'config/x86_64_import_program.ld' if import_image and n==0 else 'config/x86_64_boot_program.ld','-o',elf,start,obj,*objects])
        if large_image and not large_file and n==2:
            from build_x86_64_large_image import prepare as large_prepare
            large_prepare(elf.read_bytes(),[])
        else:
            records[n]=prepare(elf.read_bytes(),[f'program{n}.prg',str(n)],wide)
        if app_dns and shell_root:
            cc=cc[:-1];ld=ld[:-1]
        if shell_root:
            install=attempt/'root/bin';install.mkdir(parents=True,exist_ok=large_file)
            (install/'shell.prg').write_bytes(elf.read_bytes())
    if large_image and not large_file:
        # The large child is only an imported image; catalog slot2 is a small
        # separately owned copy of the existing inert slot3 fixture.
        records[2]=records[3]
    catalog=attempt/'boot-programs.bin';catalog.write_bytes(b''.join(records))
    # All inputs and all records admitted before replacing the build consumer.
    # Retain every attempt and ELF; only this explicit generated catalog changes.
    staged=directory/('boot-programs-'+uuid.uuid4().hex+'.tmp')
    staged.write_bytes(catalog.read_bytes());os.replace(staged,directory/'boot-programs.bin')
    print('NATIVE_BOOT_PROGRAMS_PREPARED',attempt)

def compact_input_elf(path,objcopy,terminal_service=False,network_session=False):
    """Drop only new local debug names; preserve every loaded byte and address."""
    from build_x86_64_c_payload import elf,require
    path=Path(path).absolute()
    require(path==path.resolve() and path.is_relative_to(ROOT/'build'),'input ELF output scope')
    raw=path.read_bytes();before=elf(raw,32)
    if type(network_session) is not bool or network_session and terminal_service:raise ValueError('exclusive network compaction selector')
    prefixes=('native_pio_','native_terminal_','native_network_') if network_session else ('native_input_', 'native_terminal_') if terminal_service else ('native_input_',)
    removed={n for n,s in before['symbols'].items() if n.startswith(prefixes) and '.' in n and s['binding']==0}
    require(1<=len(removed)<=128,'bounded input local debug symbols')
    retained=path.with_suffix('.untrimmed.elf');temporary=path.with_suffix('.compact.elf')
    require(not retained.exists() and not temporary.exists(),'fresh compaction artifacts')
    with retained.open('xb') as out:out.write(raw)
    command=[str(objcopy),*[arg for n in sorted(removed) for arg in ('--strip-symbol',n)],str(retained),str(temporary)]
    r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    require(r.returncode==0,'input local symbol compaction: '+r.stderr.decode(errors='replace')[-1200:])
    compact=bytearray(temporary.read_bytes())
    # GNU objcopy canonicalizes an empty NOBITS segment's file offset. Retain
    # even that nonloaded header field so the complete original layout is exact.
    phoff=struct.unpack_from('<I',raw,28)[0];count=struct.unpack_from('<H',raw,44)[0]
    require(struct.unpack_from('<I',compact,28)[0]==phoff and struct.unpack_from('<H',compact,44)[0]==count,'exact program-header table')
    for n in range(count):
        at=phoff+n*32;original=struct.unpack_from('<8I',raw,at);changed=struct.unpack_from('<8I',compact,at)
        if original[0]==1 and original[4]==0:
            require(original[:1]+original[2:]==changed[:1]+changed[2:],'only empty segment file offset may be canonicalized')
            struct.pack_into('<I',compact,at+4,original[1])
    compact=bytes(compact);after=elf(compact,32)
    require(after['entry']==before['entry'] and after['programs']==before['programs'],'exact input load layout')
    for segment in before['programs']:
        lo=segment['offset'];hi=lo+segment['filesz']
        require(raw[lo:hi]==compact[lo:hi],'every loaded input byte unchanged')
    require(after['symbols']=={n:s for n,s in before['symbols'].items() if n not in removed},'all other diagnostic symbols unchanged')
    require(len(compact)<len(raw),'input symbol compaction reduced file')
    checked=path.with_suffix('.checked.elf')
    with checked.open('xb') as out:out.write(compact)
    os.replace(checked,path)
    print('NATIVE_INPUT_SYMBOLS_COMPACTED',len(removed),len(raw),len(compact))

if __name__=='__main__' and '--compact-input-elf' in sys.argv:
    p=argparse.ArgumentParser();p.add_argument('--compact-input-elf',required=True);p.add_argument('--objcopy',required=True);p.add_argument('--terminal-service',action='store_true');p.add_argument('--network-session',action='store_true')
    a=p.parse_args();compact_input_elf(a.compact_input_elf,a.objcopy,a.terminal_service,a.network_session)
elif __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True)
    for tool in ('cc','nasm','ld'):p.add_argument('--'+tool,required=True,nargs='+')
    p.add_argument('--case',type=int,choices=range(3),default=0)
    p.add_argument('--family',action='store_true')
    p.add_argument('--family-case',type=int,choices=range(6),default=0)
    p.add_argument('--startup',action='store_true')
    p.add_argument('--import-image',action='store_true')
    p.add_argument('--pio',action='store_true')
    p.add_argument('--block',action='store_true')
    p.add_argument('--wide',action='store_true')
    p.add_argument('--block-profile',action='store_true')
    p.add_argument('--block-profile-case',type=int,choices=range(8),default=0)
    p.add_argument('--filesystem',action='store_true')
    p.add_argument('--filesystem-case',type=int,choices=range(9),default=0)
    p.add_argument('--filesystem-layout',type=int,choices=range(5),default=2)
    p.add_argument('--file-launch',action='store_true')
    p.add_argument('--task-pool',action='store_true')
    p.add_argument('--pool-pio',action='store_true')
    p.add_argument('--pio-throughput',action='store_true')
    p.add_argument('--service-cpu',action='store_true')
    p.add_argument('--service-pio',action='store_true')
    p.add_argument('--live-file',action='store_true')
    p.add_argument('--console',action='store_true')
    p.add_argument('--native-shell',action='store_true')
    p.add_argument('--service-console',action='store_true')
    p.add_argument('--terminal',action='store_true')
    p.add_argument('--session',action='store_true')
    p.add_argument('--shell-session',action='store_true')
    p.add_argument('--wide-file',action='store_true')
    p.add_argument('--app-files',action='store_true')
    p.add_argument('--display',action='store_true')
    p.add_argument('--display-info',action='store_true')
    p.add_argument('--input',action='store_true')
    p.add_argument('--terminal-service',action='store_true')
    p.add_argument('--graphical-session',action='store_true')
    p.add_argument('--network-dma',action='store_true')
    p.add_argument('--network-session',action='store_true')
    p.add_argument('--app-network',action='store_true')
    p.add_argument('--app-tcp',action='store_true')
    p.add_argument('--large-periodic',action='store_true')
    p.add_argument('--app-dns',action='store_true');p.add_argument('--app-http',action='store_true');p.add_argument('--app-cpp-runtime',action='store_true');p.add_argument('--math-runtime',action='store_true');p.add_argument('--text-runtime',action='store_true');p.add_argument('--large-image',action='store_true');p.add_argument('--large-file',action='store_true')
    p.add_argument('--file-launch-case',type=int,choices=range(11),default=0)
    p.add_argument('--memory-case',type=int,choices=range(7),default=0)
    p.add_argument('--pio-case',type=int,choices=range(4),default=0)
    p.add_argument('--startup-case',type=int,choices=range(2),default=0)
    a=p.parse_args()
    if a.family_case and not a.family:p.error('family-case requires family')
    if a.startup_case and not a.startup:p.error('startup-case requires startup')
    build(a.directory,a.cc,a.nasm,a.ld,a.case,a.family,a.family_case,a.startup,a.startup_case,a.import_image,a.pio,a.pio_case,a.block,a.wide,a.memory_case,a.block_profile,a.block_profile_case,a.filesystem,a.filesystem_case,a.filesystem_layout,a.file_launch,a.file_launch_case,a.task_pool,a.pool_pio,a.service_cpu,a.service_pio,a.live_file,a.console,a.native_shell,a.service_console,a.terminal,a.session,a.shell_session,a.wide_file,a.app_files,a.display,a.input,a.terminal_service,a.graphical_session,a.network_dma,a.network_session,a.app_network,a.app_tcp,a.app_dns,a.app_http,a.app_cpp_runtime,a.math_runtime,a.text_runtime,a.large_image,a.pio_throughput,a.large_file,a.display_info,a.large_periodic)
