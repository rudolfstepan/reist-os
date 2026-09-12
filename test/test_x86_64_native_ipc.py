"""Execute the real native IPC adapter and retain the legacy implementation proof."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid, struct, shutil, re
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class NativeIPCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        cls.folder=ROOT/'build/codex-agent/r83x-native-ipc'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True)
        cls.env=os.environ.copy()
        cls.env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        cls.env['ZIG_LOCAL_CACHE_DIR']=str(cls.folder/'cache')

    def test_actual_adapter_o0_o2(self):
        for opt in ('0','2'):
            exe=self.folder/('native-'+opt+'.exe')
            cmd=[str(find_zig()),'cc','-std=c11','-Wall','-Wextra','-Werror','-O'+opt,
                 '-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_HOST_TEST',
                 '-I',str(ROOT),'kernel/ipc/ipc.c','kernel/init/critical_object.c',
                 'test/x86_64_native_ipc_host.c','-o',str(exe)]
            run=subprocess.run(cmd,cwd=ROOT,env=self.env,capture_output=True,text=True,timeout=60,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/('compile-'+opt+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
            self.assertEqual(run.returncode,0,run.stderr[-3000:])
            run=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=10,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/('run-'+opt+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('NATIVE_IPC_HOST_OK',run.stdout)
            for case in ('busy','dual','raw','bootstrap','pending','blocking'):
                run=subprocess.run([str(exe),case],cwd=ROOT,capture_output=True,text=True,timeout=10,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (self.folder/('fault-'+opt+'-'+case+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
                self.assertEqual(run.returncode,0,case+': '+run.stdout+run.stderr)
                self.assertIn('NATIVE_IPC_FAULT_CLOSED_OK',run.stdout)

    def test_legacy_preprocessing_and_behavior(self):
        old=self.folder/'ipc.c'
        old.write_bytes(subprocess.check_output(['git','show','b90c2cab:kernel/ipc/ipc.c'],cwd=ROOT,timeout=10))
        before=subprocess.run([str(find_zig()),'cc','-target','x86-freestanding-none','-I.','-E','-P',str(old)],
                              cwd=ROOT,capture_output=True,text=True,timeout=30,env=self.env)
        after=subprocess.run([str(find_zig()),'cc','-target','x86-freestanding-none','-I.','-E','-P','kernel/ipc/ipc.c'],
                             cwd=ROOT,capture_output=True,text=True,timeout=30,env=self.env)
        self.assertEqual((before.returncode,after.returncode),(0,0),before.stderr+after.stderr)
        self.assertEqual(before.stdout.split(),after.stdout.split())
        for opt in ('0','2'):
            exe=self.folder/('legacy-'+opt+'.exe')
            cmd=[str(find_zig()),'cc','-O'+opt,'-UNDEBUG','-DREIST_HOST_TEST','-I.',
                 'kernel/ipc/ipc.c','kernel/init/critical_object.c','kernel/sched/wait_queue.c','test/test_ipc_host.c','-o',str(exe)]
            run=subprocess.run(cmd,cwd=ROOT,env=self.env,capture_output=True,text=True,timeout=60,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/('legacy-compile-'+opt+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
            self.assertEqual(run.returncode,0,run.stderr[-2000:])
            run=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=10,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_native_syscall_guest_oracle(self):
        import run_qemu_x86_64_native_ipc as guest
        import test_x86_64_process_run as prior
        for case in range(4):
            serial=prior.ProcessRunTests.sample(0)
            for match in reversed(list(guest.process.REAP.finditer(serial))):
                raw=list(struct.unpack('<4I2Q',bytes.fromhex(match[1])))
                slot,gen=raw[:2];fault=slot==0 and case in (1,3)
                raw[2]=134 if fault and case==1 else 256 if fault else 0xc100+slot
                raw[3]=3 if fault else 4
                if fault and case==3:raw[4]=32
                serial=serial[:match.start(1)]+struct.pack('<4I2Q',*raw).hex().upper()+serial[match.end(1):]
            rows=guest.validate(serial,case);self.assertEqual(len(rows),8)
            for bad in (serial+serial,serial.replace(guest.process.DONE,'MISSING',1),serial.replace('C1000004','C0000004',1)):
                with self.assertRaises(ValueError):guest.validate(bad,case)

    def test_observer_start_failure_reaps_only_owned_vm(self):
        import run_qemu_x86_64_native_ipc as guest
        vm=mock.Mock()
        with mock.patch.object(guest,'resolve_qemu',return_value=Path('qemu')), \
             mock.patch.object(guest.subprocess,'Popen',side_effect=[vm,OSError('debugger missing')]), \
             mock.patch.object(guest,'terminate_bounded') as terminate:
            with self.assertRaises(OSError):guest.capture(Path('image'),self.folder,'continue\n')
        terminate.assert_called_once_with(vm);vm.stdin.close.assert_called_once();vm.stdout.close.assert_called_once()

    def test_ipc_wait_and_copyout_oracle(self):
        import run_qemu_x86_64_native_ipc as guest
        rows=[dict(slot=s,generation=run*4+s+1) for run in range(2) for s in range(4)]
        for case in range(4):
            lines=[]
            for r in rows:
                s,g=r['slot'],r['generation']
                if not s&1:
                    for nr,result in ((50,0),(54,-32 if case==2 and s==0 else -110)):
                        lines += [f'NATIVE_IPC_BLOCK slot={s} gen={g} nr={nr} deadline=20 result=-4095',
                                  f'NATIVE_IPC_READY slot={s} gen={g} nr={nr} deadline=20 result={result}']
                lines += [f'NATIVE_IPC_COPYOUT slot={s} gen={g} bytes=140 cr3=1']*(5 if s&1 else 2)
                lines += [f'NATIVE_IPC_FENCE slot={s} gen={g}']
            trace='\n'.join(lines);guest.validate_ipc_trace(trace,rows,case)
            bads=[trace+'\n'+lines[0],trace.replace('bytes=140','bytes=139',1),trace.replace('cr3=1','cr3=0',1),
                  trace.replace('NATIVE_IPC_FENCE slot=0','NATIVE_IPC_FENCE slot=1',1),
                  trace.replace('NATIVE_IPC_COPYOUT slot=0','NATIVE_IPC_COPYOUT slot=1',1),
                  '\n'.join([lines[1],lines[0]]+lines[2:]),trace.replace('result=-4095','result=0',1),
                  trace.replace('result=-110','result=-32',1),trace.replace('nr=50','nr=53'),
                  trace+'\nNATIVE_IPC_READY malformed',trace.replace('deadline=20','deadline=21',1)]
            for bad in bads:
                with self.assertRaises(ValueError):guest.validate_ipc_trace(bad,rows,case)

    def test_real_elf_export_and_rejected_bindings(self):
        import build_x86_64_c_payload as p
        zig=str(find_zig());flags=['-target','x86_64-freestanding-none','-O2','-g0','-ffreestanding','-fno-builtin',
            '-fno-pic','-mcmodel=kernel','-mno-red-zone','-mno-sse','-mno-sse2','-fno-stack-protector',
            '-fno-unwind-tables','-fno-asynchronous-unwind-tables']
        def run(args,label,source=None):
            r=subprocess.run(args,cwd=ROOT,env=self.env,input=source,capture_output=True,text=True,timeout=60,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stderr[-2000:])
        run([zig,'cc',*flags,'-c','arch/x86_64/kernel/bootstrap_core.c','-o',str(self.folder/'core.o')],'export-core')
        run([zig,'cc',*flags,'-x','c','-','-c','-o',str(self.folder/'export.o')],'export-stub',
            'unsigned long long reist_native_ipc(unsigned long long n){return n+1;}')
        path=self.folder/'export.elf'
        run([zig,'ld.lld','-m','elf_x86_64','-T','config/x86_64_c_payload.ld','-o',str(path),
             str(self.folder/'core.o'),str(self.folder/'export.o')],'export-link')
        data=p.read_bounded(path);v=p.validate(data);symbol=v['symbols']['reist_native_ipc']
        self.assertIn(f'%define C_NATIVE_IPC_ENTRY {symbol["value"]:#x}'.encode(),p.outputs(data)['bootstrap_core_layout.inc'])
        table=v['sections']['.symtab']
        offsets=[o for o in range(table['offset'],table['offset']+table['size'],24)
                 if struct.unpack_from('<Q',data,o+8)[0]==symbol['value'] and data[o+4]==0x12]
        self.assertEqual(len(offsets),1);offset=offsets[0]
        for field,fmt,value in ((4,'B',0x11),(4,'B',2),(5,'B',2),(6,'H',v['sections']['.data']['index']),
                                (8,'Q',p.HIGH+0x184000),(8,'Q',v['sections']['.text']['address']+v['sections']['.text']['size']),
                                (16,'Q',0),(16,'Q',65536)):
            bad=bytearray(data);struct.pack_into('<'+fmt,bad,offset+field,value)
            with self.assertRaises(ValueError):p.validate(bytes(bad))
        bad=bytearray(data);bad[table['offset']+24:table['offset']+48]=data[offset:offset+24]
        with self.assertRaises(ValueError):p.validate(bytes(bad))
        # Compile the production TU separately: including it in a fault-injection
        # harness changes optimizer knowledge and cannot prove stored widths.
        obj=self.folder/'native-runtime.o'
        run([zig,'cc',*flags,'-I.','-c','arch/x86_64/ipc/native_ipc.c','-o',str(obj)],'native-state-width')
        output=subprocess.check_output([shutil.which('nm') or 'C:/msys64/mingw64/bin/nm.exe','-S','--defined-only',str(obj)],
                                       cwd=ROOT,text=True,timeout=10)
        (self.folder/'native-state-width-nm.log').write_text(output,encoding='utf-8')
        sizes={m[2]:int(m[1],16) for m in re.finditer(r'^\S+\s+(\S+)\s+\S\s+(\S+)$',output,re.M)}
        for name in ('initialized','initialized_inverse','entered'):self.assertEqual(sizes[name],4,name)

    def test_legacy_operation_bodies_unchanged(self):
        old=subprocess.check_output(['git','show','b90c2cab:kernel/ipc/ipc.c'],cwd=ROOT,timeout=10).decode()
        now=(ROOT/'kernel/ipc/ipc.c').read_text()
        self.assertEqual(old.replace('\r\n','\n').split('#define IPC_MAX_CAPABILITY_RECORDS',1)[1],
                         now.split('#define IPC_MAX_CAPABILITY_RECORDS',1)[1])


if __name__=='__main__':unittest.main()
