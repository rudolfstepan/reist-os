"""Execute native heap ownership and bounded continuation behavior at O0/O2."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
import re
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs
import run_qemu_x86_64_native_heap as guest


class NativeHeapTests(unittest.TestCase):
    def test_batched_zero_checks_read_every_original_byte(self):
        sizes=[1024,2048,128,128,64,16,120,144,16,32,32,64,4,4]
        original=''.join('set $i=0\nwhile $i<'+str(n)+'\nif *(unsigned char*)('+hex(0x100000000+i*4096)+
            '+$i)!=0\nset $zero=0\nend\nset $i=$i+1\nend\n' for i,n in enumerate(sizes))
        transformed=guest.batch_zero_checks(original)
        blocks=re.findall(r'python\n(.*?)\nend\n',transformed,re.S)
        self.assertEqual(len(blocks),14)
        for i,(block,n) in enumerate(zip(blocks,sizes)):
            compiled=compile(block,'zero-batch','exec')
            data=bytearray(n);reads=[];effects=[]
            def read(address,length):
                self.assertEqual((address,length),(0x100000000+i*4096,n))
                reads.append((address,length));return memoryview(data)
            gdb=SimpleNamespace(selected_inferior=lambda:SimpleNamespace(read_memory=read),execute=effects.append)
            exec(compiled,{'gdb':gdb});self.assertEqual(effects,[])
            for offset in range(n):
                data[offset]=1;exec(compiled,{'gdb':gdb});data[offset]=0
                self.assertEqual(effects.pop(),'set $zero=0')
            self.assertEqual(len(reads),n+1)
        for bad in (original.replace('1024','1023',1),original+original,original.replace('set $zero=0','set $zero=1',1)):
            with self.assertRaises(ValueError):guest.batch_zero_checks(bad)

    def test_heap_oracle_rejects_lost_progress_mapping_and_cleanup(self):
        rows=[dict(slot=s,generation=r*4+s+1,state=4) for r in range(2) for s in range(4)]
        records=[(m,s,s+1,4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)]
        records += [(4,s,10+s,3 if s==3 else 4) for s in range(4)]
        records += [(5,s,20+s,4) for s in range(4)]+[(6,1,31,8),(6,1,32,8),(6,0,30,4)]
        records += [(8,x['slot'],x['generation'],x['state']) for x in rows]
        frames=[0,0x100001000]+[0]*6+[0x100002000,0x100006000,0x100005000,0x100004000,0x100003000]
        trace='NATIVE_MEMORY_MAP_OK ram=4096 managed=1046000 huge=2042 mixed=3 high=1\n'
        for seq,(mode,slot,gen,state) in enumerate(records,1):
            if mode==8:
                if not slot&1:
                    for nr,result in ((50,0),(54,-110)):
                        trace+=f'NATIVE_IPC_BLOCK slot={slot} gen={gen} nr={nr} deadline=20 result=-4095\n'
                        trace+=f'NATIVE_IPC_READY slot={slot} gen={gen} nr={nr} deadline=20 result={result}\n'
                trace+=f'NATIVE_IPC_COPYOUT slot={slot} gen={gen} bytes=140 cr3=1\n'*(5 if slot&1 else 2)
                trace+=f'NATIVE_IPC_FENCE slot={slot} gen={gen}\nPROCESS_FENCE_OK seq={seq} slot={slot} gen={gen}\n'
            trace+=f'TASK_FRAMES_BEFORE seq={seq} mode={mode} slot={slot} gen={gen} state={state} root=100003000 active=117000 before=1000000 fp=1 frames='+','.join(f'{f:x}' for f in frames)+'\n'
            trace+=''.join(f'TASK_FRAMES_FREE seq={seq} frame={f:x}\n' for f in frames if f)
            trace+=f'TASK_FRAMES_AFTER seq={seq} gen={gen} state={state} result=1 after=1000006 zero=1\n'
            if seq in (21,25):
                run=1 if seq==21 else 2
                trace+=f'PROCESS_ZERO_OK run={run} zero=1 free=1000000 initial=1000000 reaps=4 generation={run*4} ticks=32\n'
                trace+=f'NATIVE_HEAP_RUNTIME_WITNESS run={run} peers=3 steps=128 completed=14 zero=1\n'
        trace=re.sub(r'(NATIVE_IPC_COPYOUT slot=(\d+) gen=(\d+) bytes=140 cr3=1\n)',
                     r'\1NATIVE_HEAP_BUFFER slot=\2 gen=\3 pages=2 high=1 nx=1\n',trace)
        guest.validate_heap(trace,rows,4096,0)
        mutations=(('peers=3','peers=2'),('steps=128','steps=8192'),('steps=128','steps=7'),
                   ('completed=14','completed=7'),('completed=14 zero=1','completed=14 zero=0'),
                   ('nx=1','nx=0'),('pages=2','pages=1'),('high=1','high=0'),
                   ('NATIVE_HEAP_BUFFER','MISSING'),('NATIVE_HEAP_RUNTIME_WITNESS','MISSING'),
                   ('PROCESS_FENCE_OK','MISSING'),('100001000','4001000'),('bytes=140','bytes=139'))
        for before,after in mutations:
            with self.subTest(mutation=after):
                with self.assertRaises((ValueError,RuntimeError)):
                    guest.validate_heap(trace.replace(before,after,1),rows,4096,0)
        for bad in (trace+trace,trace+'NATIVE_HEAP_OBSERVER_FAIL test\n'):
            with self.assertRaises((ValueError,RuntimeError)):guest.validate_heap(bad,rows,4096,0)

    def test_actual_heap_transactions_o0_o2(self):
        suppress_windows_test_dialogs()
        folder = ROOT / 'build/codex-agent/r83aa-heap' / ('host-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/codex-agent/zig-global')
        env['ZIG_LOCAL_CACHE_DIR'] = str(folder / 'cache')
        for opt in ('0', '2'):
            exe = folder / ('heap-' + opt + '.exe')
            command = [str(find_zig()), 'cc', '-std=c11', '-O' + opt,
                       '-Wall', '-Wextra', '-Werror', '-DREIST_HOST_TEST',
                       '-DREIST_NATIVE_HEAP_HOST_TEST', '-I.',
                       'arch/x86_64/mm/native_heap.c', 'kernel/init/critical_object.c',
                       'test/x86_64_native_heap_host.c', '-o', str(exe)]
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                    text=True, timeout=60,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            (folder / ('compile-' + opt + '.log')).write_text(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, result.stderr[-3000:])
            for case in ('normal', 'oom', 'corrupt', 'leaf', 'table', 'stale', 'owners', 'quota'):
                result = subprocess.run([str(exe), case], cwd=ROOT, capture_output=True,
                                        text=True, timeout=60,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                (folder / (case + '-' + opt + '.log')).write_text(result.stdout + result.stderr)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('NATIVE_HEAP_HOST_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
