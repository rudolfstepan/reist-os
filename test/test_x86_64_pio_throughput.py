"""Execute the actual quota mediator, runtime adapter and legacy regressions."""
from pathlib import Path
import unittest
import sys,struct,ast
import test_x86_64_pool_pio as previous
ROOT=Path(__file__).resolve().parents[1]

class ThroughputTests(unittest.TestCase):
    def test_hardware_observer_preserves_oracle(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import run_qemu_x86_64_pio_throughput as r
        module=r.namespace(6);body=module.observer_body()
        s={'native_math_hardware_ready':0xffffffff80140000,
           'native_math_hardware_release':0xffffffff80140008,
           'native_math_hardware_gate64.wait':0xffffffff80120000,
           'native_math_hardware_gate64.failed':0xffffffff80120040}
        code='python\n'+body+'\nend\ncontinue\n'
        result=r.hardware_observer(code,{'s':s},ROOT/'build/codex-agent/host-only')
        self.assertEqual(result.count('type=gdb.BP_HARDWARE_BREAKPOINT'),2)
        from types import SimpleNamespace
        probes=[SimpleNamespace(fn=SimpleNamespace(__name__=n),enabled=e)
                for n,e in (('boot',True),('cold_fail',True),('start',True),('allocation',False))]
        expression=next(l.split('=',1)[1] for l in result.splitlines() if l.startswith('hardware_deferred=['))
        deferred=eval(expression,{'gdb':SimpleNamespace(breakpoints=lambda:probes)})
        self.assertEqual(deferred,[(probes[2],True),(probes[3],False)])
        for line in body.splitlines():
            if line.strip() and 'internal=True' not in line:self.assertIn(line,result)
        compile(result.split('python\n',1)[1].rsplit('\nend\n',1)[0],'<hardware>','exec')
        self.assertTrue(callable(r.hardware_capture()))
        with self.assertRaises(ValueError):r.hardware_observer(code.replace('internal=True','internal=False'),{'s':s},ROOT)

    def test_opt_in_driver_optimization(self):
        tree=ast.parse((ROOT/'scripts/build_x86_64_boot_programs.py').read_text())
        choices=[n for n in ast.walk(tree) if isinstance(n,ast.IfExp)
                 and isinstance(n.test,ast.Name) and n.test.id=='pio_throughput']
        self.assertEqual(len(choices),2)
        for n in choices:
            expr=compile(ast.Expression(n),'<optimization>','eval')
            for enabled in (False,True):
                self.assertEqual(eval(expr,{'__builtins__':{}},{'pio_throughput':enabled}),
                                 '-O2' if enabled else '-Oz')

    def test_private_observer_profile_bounds(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import run_qemu_x86_64_pio_throughput as runtime
        old=(runtime.prior.TRACE_CORE,runtime.prior.EXTRA)
        for case,quota,tag in ((0,64,0),(1,128,runtime.TAG)):
            module=runtime.namespace(case)
            body=module.observer_body()
            self.assertIn(module.TRACE_CORE,body)
            self.assertIn('quota=128 if v[7] else 64',body)
            raw=bytearray(12304);struct.pack_into('<2Q',raw,0,1,0)
            owner=(11<<32)|2
            struct.pack_into('<2Q8Q5Q',raw,16,1,1,owner,owner^0xffffffffffffffff,
                             0,10,10,quota,10,tag,0x3f6,6,0,9,9<<32)
            self.assertEqual(module.trace_decode(bytes(raw),0)[0][2][5],quota)
            for offset,value in ((72,quota+1),(88,tag^1),(88,runtime.TAG if not tag else 0)):
                bad=bytearray(raw);struct.pack_into('<Q',bad,offset,value)
                with self.assertRaises(ValueError):module.trace_decode(bytes(bad),0)
        self.assertEqual((runtime.prior.TRACE_CORE,runtime.prior.EXTRA),old)

    def test_actual_profile_and_lifecycle(self):
        previous.PoolPioTests().build(previous.kernel_asm(),
            ROOT/'test/x86_64_pio_throughput_host.c','PIO_THROUGHPUT')

if __name__=='__main__':unittest.main()
