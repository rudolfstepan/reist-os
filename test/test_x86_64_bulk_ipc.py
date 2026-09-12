"""Real compatible v2 adapter behavior; no hosted assertion elision/dialogs."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class BulkIPCTests(unittest.TestCase):
    def test_actual_bulk_o0_o2(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83y-bulk'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/('bulk-'+opt+'.exe')
            command=[str(find_zig()),'cc','-std=c11','-Wall','-Wextra','-Werror','-O'+opt,
                     '-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_HOST_TEST','-I.',
                     'kernel/ipc/ipc.c','kernel/init/critical_object.c','test/x86_64_native_ipc_host.c','-o',str(exe)]
            for label,cmd in [('compile',command),('run',[str(exe),'bulk'])]:
                r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(label+'-'+opt+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
                self.assertEqual(r.returncode,0,r.stdout+r.stderr[-2500:])
            self.assertIn('NATIVE_BULK_HOST_OK',r.stdout)
            for case in ('bulk-tail','bulk-capacity'):
                r=subprocess.run([str(exe),case],cwd=ROOT,env=env,capture_output=True,text=True,timeout=10,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(case+'-'+opt+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                self.assertIn('NATIVE_IPC_FAULT_CLOSED_OK',r.stdout)

    def test_strict_bulk_observer_oracle(self):
        import run_qemu_x86_64_native_ipc as guest
        rows=[dict(slot=s,generation=run*4+s+1) for run in range(2) for s in range(4)]
        for case in range(4):
            lines=[]
            for row in rows:
                s,g=row['slot'],row['generation']
                if not s&1:
                    for nr,result in ((50,0),(54,-32 if case==2 and s==0 else -110)):
                        lines += [f'NATIVE_IPC_BLOCK slot={s} gen={g} nr={nr} deadline=20 result=-4095',
                                  f'NATIVE_IPC_READY slot={s} gen={g} nr={nr} deadline=20 result={result}']
                lines += [f'NATIVE_IPC_COPYOUT slot={s} gen={g} bytes=2060 cr3=1']*2
                lines += [f'NATIVE_IPC_FENCE slot={s} gen={g}']
            trace='\n'.join(lines);guest.validate_ipc_trace(trace,rows,case,True)
            for bad in (trace+trace,trace.replace('bytes=2060','bytes=140',1),trace.replace('cr3=1','cr3=0',1),
                        trace.replace('gen=1','gen=9',1),'\n'.join([lines[1],lines[0]]+lines[2:]),
                        trace.replace('NATIVE_IPC_FENCE slot=0','NATIVE_IPC_FENCE slot=1',1)):
                with self.assertRaises(ValueError):guest.validate_ipc_trace(bad,rows,case,True)

if __name__=='__main__':unittest.main()
