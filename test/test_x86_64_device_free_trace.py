"""Actual trace producer and strict reader on the device-free qualification path."""
from pathlib import Path
import inspect, subprocess, sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
import test_x86_64_cpu_trace as original

class DeviceFreeTraceTests(original.CPUTraceTests):
    def test_device_free_actual_assembly(self):
        old=inspect.getsource(original.CPUTraceTests.test_actual_assembly_ring_and_unchanged_core)
        assert old.count('%define REIST_NATIVE_POOL_PIO 1')==1
        body=('class Fixture:\n'+old).replace('%define REIST_NATIVE_POOL_PIO 1','%define REIST_NATIVE_DEVICE_FREE_CPU_TRACE 1')
        env=dict(vars(sys.modules[original.CPUTraceTests.__module__]));exec(compile(body,'<device-free production trace harness>','exec'),env)
        env['Fixture'].test_actual_assembly_ring_and_unchanged_core(self)

    def test_invalid_build_selectors(self):
        import verify_x86_64_display as c
        for value in ('', '2', '0 1','1'):
            r=subprocess.run([c.build_tools()['make']['path'],'-f','Makefile','-n','x86_64-bootstrap',
                'X86_64_NATIVE_CPU_TRACE='+value],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('NativeCPUTrace',r.stdout+r.stderr)
        r=subprocess.run(['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeCPUTrace'],
            cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertNotEqual(r.returncode,0);self.assertIn('NativeCPUTrace requires',r.stdout+r.stderr)

if __name__=='__main__':unittest.main()
