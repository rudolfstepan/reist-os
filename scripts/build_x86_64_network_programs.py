"""Build separate ELF64 network roles and bind their prepared-image hashes."""
from pathlib import Path
import hashlib, os, subprocess
ROOT = Path(__file__).resolve().parents[1]

def build_roles(directory, cc, nasm, ld, app_network=False, app_tcp=False):
    from build_x86_64_boot_programs import prepare
    directory = Path(directory)
    environment = os.environ.copy()
    environment['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
    environment['ZIG_LOCAL_CACHE_DIR'] = str(directory / 'zig-cache')
    def run(command):
        p = subprocess.run(list(map(str, command)), cwd=ROOT, env=environment,
                           capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        with (directory / 'network-build.log').open('ab') as log:
            log.write(p.stdout + p.stderr)
        if p.returncode:
            raise ValueError((p.stdout + p.stderr).decode(errors='replace')[-3000:])
    common = [*cc, '-target', 'x86_64-freestanding-none', '-std=c11', '-Oz',
              '-Wall', '-Wextra', '-Werror', '-ffreestanding', '-nostdlib', '-fno-builtin',
              '-fno-stack-protector', '-mno-red-zone', '-fno-unwind-tables',
              '-fno-asynchronous-unwind-tables', '-fno-pic', '-fno-pie',
              '-mno-mmx', '-mno-sse', '-mno-sse2', '-ffunction-sections', '-fdata-sections',
              '-DREIST_NATIVE_NETWORK_SESSION=1', '-DREIST_NET_ROLE_RUNTIME=1',
              '-Iuserspace/sdk/include', '-fstack-usage']
    shared = ['userspace/sdk/lib/x86_64/network_session.c']
    roles = {
        'netdrv': shared + ['userspace/drivers/net/native_network.c'],
        'netstack': shared + ['userspace/programs/native_netstack.c',
                    'userspace/sdk/lib/x86_64/network_protocol.c',
                    'userspace/sdk/reist_ipv4_parser.c', 'userspace/sdk/reist_icmp_parser.c']}
    start = directory / 'network-start.o'
    if app_network:
        common += ['-DREIST_NATIVE_APP_NETWORK=1']
        roles['netstack'] += ['userspace/sdk/lib/x86_64/application_udp.c',
                             'userspace/sdk/lib/x86_64/application_udp_protocol.c',
                             'userspace/sdk/reist_udp_parser.c']
    if app_tcp:
        if not app_network:raise ValueError('TCP requires application network')
        common += ['-DREIST_NATIVE_APP_TCP=1']
        roles['netstack'] += ['userspace/sdk/lib/x86_64/application_tcp.c',
                             'userspace/sdk/lib/x86_64/application_tcp_protocol.c',
                             'userspace/sdk/reist_tcp_parser.c']
    run([*nasm, '-f', 'elf64', 'arch/x86_64/user/boot_start.asm', '-o', start])
    digests = []
    for name, sources in roles.items():
        objects = []
        for index, source in enumerate(sources):
            obj = directory / f'{name}-{index}.o'
            run([*common, '-c', source, '-o', obj]); objects.append(obj)
        elf = directory / (name + '.prg')
        run([*ld, '-m', 'elf_x86_64', '-nostdlib', '--build-id=none', '--fatal-warnings',
             '--no-undefined', '-z', 'noexecstack', '--gc-sections', '--strip-all',
             '-T', 'config/x86_64_wide_program.ld', '-Map=' + str(directory / (name + '.map')),
             '-o', elf, start, *objects])
        prepared = prepare(elf.read_bytes(), [], True)
        digests.append(hashlib.sha256(prepared[:262240]).digest())
    (directory / 'network_manifest.h').write_text(
        'static const unsigned char network_hashes[2][32]={' +
        ','.join('{' + ','.join(map(str, digest)) + '}' for digest in digests) + '};\n',
        encoding='ascii')
    return tuple(directory / (name + '.prg') for name in roles)
