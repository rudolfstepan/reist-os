"""Build the isolated fixed-storage VGA/PS2 service with the existing toolchain."""
from pathlib import Path


def build_role(attempt, cc, ld, run, start):
    from build_x86_64_boot_programs import prepare
    objects = []
    for i, source in enumerate(('userspace/drivers/vga/native_console.c',
                                 'userspace/drivers/vga/text.c',
                                 'userspace/drivers/ps2/native_input.c')):
        obj = Path(attempt) / ('vga-' + str(i) + '.o')
        run([*cc, '-target', 'x86_64-freestanding-none', '-std=c11', '-Oz',
             '-Wall', '-Wextra', '-Werror', '-ffreestanding', '-nostdlib',
             '-fno-builtin', '-fno-stack-protector', '-mno-red-zone',
             '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
             '-fno-pic', '-fno-pie', '-mno-mmx', '-mno-sse', '-mno-sse2',
             '-fstack-usage', '-Iuserspace/sdk/include', '-c', source, '-o', obj])
        objects.append(obj)
    worker = Path(attempt) / 'vga-console.prg'
    run([*ld, '-m', 'elf_x86_64', '-nostdlib', '--build-id=none',
         '--fatal-warnings', '--no-undefined', '-z', 'noexecstack', '--strip-all',
         '-T', 'config/x86_64_wide_program.ld', '-o', worker, start, *objects])
    blob = worker.read_bytes()
    prepare(blob, [], True)
    return blob
