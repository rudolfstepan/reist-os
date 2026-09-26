"""Execute the production VGA text renderer with guarded storage."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class VgaConsoleTests(unittest.TestCase):
    def test_complete_cursor_capture_replay(self):
        import verify_x86_64_vga_console as verifier
        fixture=verifier.BASE/'qualification04'
        result=verifier.replay(fixture/'guest-healthy','healthy',verifier.media.verify(fixture/'media'))
        self.assertGreater(result['elapsed'],0)
        self.assertEqual(result['case'],'healthy')

    def test_cursor_pixel_oracle_rejects_old_row_and_blank_frame(self):
        from run_qemu_x86_64_vga_console import cursor_pixels
        folder=ROOT/'build/codex-agent/r83cj-vga'/('cursor-host-'+uuid.uuid4().hex)
        folder.mkdir();path=folder/'screen.ppm'
        header=b'P6\n720 400\n255\n';pixels=bytearray(720*400*3)
        path.write_bytes(header+pixels)
        self.assertFalse(cursor_pixels(path,23,4))
        for x in range(9):
            offset=((23*16+14)*720+4*9+x)*3
            pixels[offset:offset+3]=b'\xaa\xaa\xaa'
        path.write_bytes(header+pixels)
        self.assertTrue(cursor_pixels(path,23,4))
        self.assertFalse(cursor_pixels(path,22,4))
        self.assertFalse(cursor_pixels(path,23,5))
        path.write_bytes(header+pixels[:-1])
        with self.assertRaises(ValueError):cursor_pixels(path,23,4)

    def test_reference_normalization_preserves_object_code_and_relocations(self):
        import struct
        import verify_x86_64_vga_console as verifier
        reference=next((verifier.REFERENCE/'source/build/reference/x86_64').glob('programs-*'))/'program3.o'
        baseline=verifier.canonical_object(reference,verifier.REFERENCE/'source')
        raw=reference.read_bytes();offset=struct.unpack_from('<Q',raw,40)[0]
        count,index=struct.unpack_from('<HH',raw,60)
        headers=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+n*64) for n in range(count)]
        names=raw[headers[index][4]:headers[index][4]+headers[index][5]]
        folder=verifier.BASE/('object-host-'+uuid.uuid4().hex);folder.mkdir();target=folder/'changed.o'
        for label in (b'.text',b'.rela.debug_info'):
            section=next(h for h in headers if names[h[0]:].split(b'\0')[0]==label)
            self.assertGreater(section[5],0)
            changed=bytearray(raw);changed[section[4]]^=1;target.write_bytes(changed)
            self.assertNotEqual(baseline,verifier.canonical_object(target,verifier.REFERENCE/'source'))

    def test_independent_replay_rejects_changed_authority_cells_and_media(self):
        import json
        import shutil
        import verify_x86_64_vga_console as verifier
        image=verifier.media.verify(verifier.BASE/'media07')
        source=verifier.BASE/'guest13'
        folder=verifier.BASE/('replay-host-'+uuid.uuid4().hex)
        folder.mkdir()
        # Copy only the raw evidence consumed by the independent parser;
        # no guest, compiler, media producer or mutable VM disk is involved.
        for path in source.rglob('*'):
            if path.is_file() and path.suffix in ('.json','.bin','.txt','.log'):
                target=folder/path.relative_to(source)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
        verifier.replay(folder,'healthy',image,historical_host_fixture=True)
        for name,offset in (('startup/vga.bin',80),('startup/profiles.bin',136),
                            ('startup/family.bin',264),('startup/cells.bin',0),
                            ('startup/vga-page-3.bin',184*8)):
            path=folder/name;original=path.read_bytes();changed=bytearray(original);changed[offset]^=4
            path.write_bytes(changed)
            try:
                with self.assertRaises(ValueError):verifier.replay(folder,'healthy',image,historical_host_fixture=True)
            finally:path.write_bytes(original)
        path=folder/'media-after.json';original=path.read_bytes();changed=json.loads(original)
        changed['overlay_allocated_data']=512;path.write_text(json.dumps(changed))
        with self.assertRaises(ValueError):verifier.replay(folder,'healthy',image,historical_host_fixture=True)
        path.write_bytes(original)

    def test_serial_oracle_complete_interleaved_reap_only(self):
        import struct
        from run_qemu_x86_64_vga_console import console_text
        row=struct.pack('<4I2Q',1,2,77,4,0,0x41002b).hex().upper().encode()
        record=b'REIST_X86_64_PROCESS_REAP_OK v1='+row+b'\r\n'
        self.assertEqual(console_text(b'C:\\>z'+record+b'zzz\n'),b'C:\\>zzzz\n')
        for bad in (record[:-1],record.replace(b'v1=',b'v2='),record.replace(row,row[:-1])):
            self.assertNotEqual(console_text(b'C:\\>z'+bad+b'zzz\n'),b'C:\\>zzzz\n')
        bad=struct.pack('<4I2Q',8,2,77,4,0,0x41002b).hex().upper().encode()
        with self.assertRaises(ValueError):console_text(record.replace(row,bad))

    def test_selected_waits_keep_deadline_and_probe_health(self):
        def function(path,name):
            import re
            text=(ROOT/path).read_text()
            matches=list(re.finditer(r'^static [^\n;{]+\b'+name+r'\([^;{]*\)\s*\{',text,re.M))
            self.assertEqual(len(matches),1,'unique actual function '+name)
            start=matches[0].start();end=matches[0].end();depth=1
            while depth:
                depth+=(text[end]=='{')-(text[end]=='}');end+=1
            return text[start:end]
        folder=ROOT/'build/codex-agent/r83cj-vga'/('wait-host-'+uuid.uuid4().hex);folder.mkdir()
        code=r"""
#include <stdint.h>
#include <stdlib.h>
#undef NDEBUG
#include <assert.h>
#include <reist/abi/syscall.h>
#include <reist/x86_64/vga_console.h>
#define REIST_NATIVE_VGA_CONSOLE 1
#define REIST_X64_SYS_IPC_SEND_TIMEOUT 53
#define REIST_X64_SYS_IPC_RECEIVE_TIMEOUT 54
static uint64_t tick,session_vga_checked,session_vga_recovery_end;
static unsigned calls,health_calls,success_at,session_vga_busy,session_vga_disabled,session_vga_live;
static int session_vga_pending,health_result;
static uint64_t largest;
static void session_stop(int r){(void)r;abort();}
static int64_t session_vga_control(unsigned op){assert(op==REIST_VGA_STATUS);health_calls++;return health_result;}
"""
        code+=function('userspace/sdk/lib/x86_64/shell_vga_console.inc','session_vga_health')
        code+=r"""
static uint64_t session_now(void){session_vga_health(tick);return tick;}
static int64_t reist_x64_syscall3(unsigned op,uintptr_t a,uintptr_t b,uintptr_t duration){
    assert(a==7 && b==9);calls++;
    if(op!=53 && op!=54)return 17;
    if(duration>largest)largest=duration;
    tick+=duration;
    return success_at && calls==success_at?23:-110;
}
static int64_t reist_x64_task_control(const reist_task_control_request_t *q){
    assert(q->target==7);return reist_x64_syscall3(q->operation==2?54:99,7,9,q->timeout_ms);
}
"""
        code+=function('userspace/sdk/lib/x86_64/shell_session.c','session_vga_wait3')
        code+=function('userspace/sdk/lib/x86_64/shell_session.c','service_task')
        code+=r"""
static void reset(void){tick=0;calls=health_calls=success_at=0;largest=0;session_vga_checked=0;session_vga_recovery_end=0;
 session_vga_live=1;session_vga_busy=session_vga_disabled=0;session_vga_pending=health_result=0;}
int main(void){
 for(unsigned timeout=1;timeout<=1000;timeout++){
  reset();assert(session_vga_wait3(54,7,9,timeout)==-110);
  assert(tick==timeout && largest<=100 && calls<=10 && health_calls==timeout/100);
  reset();assert(service_task(0,2,7,timeout)==-110);
  assert(tick==timeout && largest<=100 && calls<=10 && health_calls==timeout/100);
 }
 reset();success_at=3;assert(session_vga_wait3(53,7,9,1000)==23 && tick==300 && calls==3);
 reset();success_at=2;assert(service_task(0,2,7,1000)==23 && tick==200 && calls==2);
 reset();assert(session_vga_wait3(54,7,9,1001)==-110 && calls==1 && largest==1001);
 reset();assert(session_vga_wait3(7,7,9,999)==17 && calls==1);
 reset();assert(service_task(0,3,7,0)==17 && calls==1);
 reset();health_result=-110;assert(session_vga_wait3(54,7,9,1000)==-110);
 assert(session_vga_pending==-110 && health_calls==1 && tick==1000 && session_vga_recovery_end==2100);
 tick=2000;session_vga_health(tick);assert(session_vga_recovery_end==2100 && health_calls==1);
 reset();session_vga_busy=1;tick=100;session_vga_health(tick);assert(health_calls==0);
 reset();session_vga_live=0;tick=100;session_vga_health(tick);assert(health_calls==0);
 return 0;
}
"""
        source=folder/'wait.c';source.write_text(code)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/('wait-'+opt+'.exe')
            for args in ([find_zig(),'cc','-target','x86_64-windows-gnu','-std=c11','-O'+opt,
                          '-Wall','-Wextra','-Werror','-Iuserspace/sdk/include',str(source),'-o',str(exe)],[str(exe)]):
                r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-2000:])

    def test_renderer_o0_o2(self):
        suppress_windows_test_dialogs()
        folder = ROOT / 'build/codex-agent/r83cj-vga' / ('host-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(folder / 'cache')
        def run(args, label):
            result = subprocess.run(list(map(str, args)), cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=60,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            (folder / (label + '.log')).write_text(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-2000:])
        import re
        scheduler=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        constants=''.join('%define '+name+' '+re.search(r'^'+name+r'\s+equ (\d+)',scheduler,re.M)[1]+'\n'
                          for name in ('TASK_STATE','TASK_GENERATION','TASK_FREE','TASK_READY','TASK_BLOCKED'))
        adapter = folder / 'adapter.asm'
        adapter.write_text('BITS 64\nsection .text\n'
                           '%define PF_R 4\n%define PF_W 2\n%define NATIVE_TASK_SHIFT 10\n'
                           +constants+
                           'extern scheduler_fail,vga_test_range\n'
                           'extern syscall_rdx,syscall_r10,syscall_r8,syscall_r9,syscall_rsi\n'
                           'extern scheduler_tasks,family_records,scheduler_current_slot,scheduler_last_tick\n'
                           '%include "arch/x86_64/video/vga_text_domain.inc"\n'
                           'global native_vga_request,vga_test_syscall\n'
                           'scheduler_validate_shell_range64:\nmov rdi,rax\nmov rsi,rdx\nmov edx,ecx\n'
                           'call vga_test_range\nret\n'
                           'process_run_resume64: ret\n'
                           'vga_test_syscall:\npush r12\npush r13\nsub rsp,8\n'
                           'mov eax,[rel scheduler_current_slot]\nshl eax,10\n'
                           'lea r12,[rel scheduler_tasks]\nadd r12,rax\n'
                           'call native_vga_syscall64\nadd rsp,8\npop r13\npop r12\nret\n')
        obj=folder/'adapter.o'
        run(['C:/tools/nasm-3.02/nasm.exe', '-f', 'win64', adapter,
             '-o', obj], 'assemble-adapter')
        for level in ('0', '2'):
            exe = folder / ('text-' + level + '.exe')
            run([find_zig(), 'cc', '-target', 'x86_64-windows-gnu', '-std=c11',
                 '-O' + level, '-Wall', '-Wextra', '-Werror', '-I.',
                 'test/x86_64_vga_console_host.c', 'userspace/drivers/vga/text.c', obj,
                 '-o', exe], 'compile-' + level)
            run([exe], 'run-' + level)
        for i, source in enumerate(('userspace/drivers/vga/native_console.c',
                                     'userspace/drivers/vga/text.c')):
            run([find_zig(), 'cc', '-target', 'x86_64-freestanding-none', '-std=c11',
                 '-Oz', '-Wall', '-Wextra', '-Werror', '-ffreestanding', '-nostdlib',
                 '-fno-builtin', '-fno-stack-protector', '-mno-red-zone', '-fno-pic',
                 '-fno-pie', '-mno-mmx', '-mno-sse', '-mno-sse2',
                 '-Iuserspace/sdk/include', '-c', source,
                 '-o', folder / ('service-' + str(i) + '.o')], 'service-' + str(i))


if __name__ == '__main__':
    unittest.main()
