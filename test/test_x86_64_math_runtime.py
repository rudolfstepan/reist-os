"""Actual AMD64 numeric runtime, default compatibility and raw guest proof."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_user_math as math
from build_user_program import find_zig,validate_cpp_object

class NativeMathRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'build/codex-agent/r83bs-native-math'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True);cls.env=os.environ.copy()
        cls.env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        cls.env['ZIG_LOCAL_CACHE_DIR']=str(cls.folder/'cache')
    def command(self,args,timeout=90):
        p=subprocess.run([str(a) for a in args],cwd=ROOT,env=self.env,capture_output=True,timeout=timeout,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (self.folder/('command-'+uuid.uuid4().hex+'.log')).write_bytes(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-2400:]);return p.stdout

    def test_actual_native_math_o0_o2(self):
        vendor=math.extract(self.folder/'upstream',architecture='x86_64')
        self.assertIn('cvtsd2si',(vendor/'src/math/x86_64/lrint.c').read_text())
        zig=find_zig()
        defines=['-D'+n+'=reist_math_'+n for n in math.FUNCTIONS+math.INTEGER_FUNCTIONS+
                 ('fegetround','fesetround','feclearexcept','fetestexcept')]
        for opt in ('-O0','-O2'):
            out=self.folder/opt;out.mkdir()
            objects=math.compile_math(zig,vendor,out,self.env,host=True,opt=opt,architecture='x86_64')
            exe=out/'math-host.exe'
            self.command([zig,'cc','-target','x86_64-windows-gnu',opt,'-fno-builtin','-fno-sanitize=all',
                '-mno-avx','-mno-mmx','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',*defines,
                '-Iuserspace/math/include','test/x86_64_math_host.c',*objects,'-o',exe])
            self.assertIn(b'NATIVE_MATH_HOST_OK',self.command([exe],30))

    def test_real_elf64_archive_and_consumer(self):
        import json,shutil,re
        from build_x86_64_math_runtime import build_tool
        before=ROOT/'build/codex-agent/r83br-cpp-runtime/candidate01'
        frozen=json.loads((before/'frozen.json').read_text(encoding='utf-8'))
        original=list((before/'build/x86_64').glob('programs-*/cpp-sysroot'))
        self.assertEqual(len(original),1)
        out=self.folder/'elf64';out.mkdir();(out/'root').mkdir()
        shutil.copytree(original[0],out/'cpp-sysroot')
        zig=find_zig()
        elf=build_tool(out,[str(zig),'cc'],[frozen['tools']['nasm']['path']],[str(zig),'ld.lld'])
        validate_cpp_object(elf.read_bytes(),architecture='x86_64')
        archive=out/'cpp-sysroot/usr/lib/libm.a'
        validate_cpp_object(archive.read_bytes(),architecture='x86_64')
        nm='C:/msys64/mingw64/bin/nm.exe'
        defined=self.command([nm,'--defined-only','--extern-only',archive]).decode().replace('\r','')
        names=set(re.findall(r'(?m)^\S+\s+[A-Za-z]\s+(\S+)$',defined))
        self.assertTrue(set(math.FUNCTIONS+math.INTEGER_FUNCTIONS)<=names)
        undefined=self.command([nm,'-u',archive]).decode().replace('\r','')
        needs=set(re.findall(r'(?m)^\s+U\s+(\S+)$',undefined))
        self.assertFalse(needs-names,needs-names)
        self.assertNotIn('sqrtl',names);self.assertNotIn('drem',names)
        self.assertEqual(elf.read_bytes(),(out/'root/mathtest.prg').read_bytes())
        for bad in (None,1,'amd64','../../x86_64'):
            with self.assertRaises(ValueError):math.extract(self.folder/'denied',architecture=bad)
        self.assertFalse((self.folder/'denied').exists())

    def test_observer_construction(self):
        import run_qemu_x86_64_math_runtime as guest
        image=ROOT/'build/codex-agent/r83bs-native-math/build01/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'healthy4g')
        module=guest.namespace('healthy4g')
        folder=self.folder/'observer';folder.mkdir()
        code=module.observer(config,records,folder,0,2)
        self.assertIn('math_checkpoint',code)
        self.assertIn('math_reaped',code)
        self.assertEqual(len(files),7)

    def test_fp_payload_mutations(self):
        import run_qemu_x86_64_math_runtime as guest
        for mode in (0,0x400,0x800,0xc00):
            data=guest.fp_payload(mode);guest.fp_equal(data,data)
            for offset in (0,4,24,32,41,144,153,160,415):
                changed=bytearray(data);changed[offset]^=1
                with self.assertRaises((ValueError,AssertionError)):guest.fp_equal(bytes(changed),data)

    def test_hardware_observer_construction(self):
        import run_qemu_x86_64_math_runtime as guest
        image=ROOT/'build/codex-agent/r83bs-native-math/build02/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'mxcsr-fault')
        module=guest.hardware_namespace('mxcsr-fault')
        folder=self.folder/'hardware-observer';folder.mkdir()
        code=module.observer(config,records,folder,0,2)
        self.assertIn('set breakpoint always-inserted off\n',code)
        self.assertIn('MATH_HARDWARE_BOOTSTRAP_V1',code)
        self.assertLess(code.index('math_checkpoint=MathCheckpoint'),code.index('MATH_HARDWARE_BOOTSTRAP_V1'))
        capture=module.stepped_capture_namespace()
        self.assertIn('hardware_bootstrap',capture['_capture_run'].__code__.co_names)
        self.assertEqual(len(files),7)

    def test_retained_hardware_transport_rejection(self):
        import json
        base=ROOT/'build/codex-agent/r83bs-native-math'
        for number in ('08','09','10'):
            folder=base/('diagnostic'+number)
            receipt=json.loads((base/('diagnostic'+number+'.json')).read_text())
            self.assertEqual(receipt['result'],1)
            self.assertFalse(json.loads((folder/'summary.json').read_text())['passed'])
            boot=json.loads((folder/'hardware-bootstrap.json').read_text())
            self.assertTrue(boot['passed']);self.assertLess(boot['elapsed'],10)
            self.assertLessEqual(len(boot['reads']),128)
            for row in boot['reads']:
                import struct
                self.assertEqual(list(struct.unpack('<2Q',(folder/row['file']).read_bytes())),row['values'])
            self.assertEqual(boot['reads'][-1]['values'],[1,0])
        log='\n'.join((base/'diagnostic10'/name).read_text() for name in ('observer.log','frame-trace.log'))
        self.assertIn('Enabled packet Z0 (software-breakpoint) not recognized by stub',log)
        self.assertIn('WHPX: Unexpected VP exit code 4',(base/'diagnostic09/stderr.log').read_text())

    def test_portable_hardware_binding_and_observer(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math'
        binding=base/'portable-qemu/binary-binding09.json'
        exe,firmware=guest.portable_toolchain(binding)
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        config,records,_=guest.image_config(image,'mxcsr-fault')
        module=guest.hardware_namespace('mxcsr-fault',toolchain=binding)
        folder=self.folder/'portable-observer';folder.mkdir()
        code=module.observer(config,records,folder,0,2)
        self.assertIn('one-shot hardware gate cleared',code)
        self.assertIn('cold_step_mode=1',code)
        self.assertIn('RET preserves CPU state',code)
        self.assertIn('actual single RET target hit',code)
        self.assertNotIn('BP_WATCHPOINT',code)
        self.assertIn('gdb.BP_HARDWARE_BREAKPOINT',code)
        self.assertIn("hex(CONFIG['math_checkpoint']),type=gdb.BP_HARDWARE_BREAKPOINT",code)
        self.assertIn('gdb.selected_frame().read_register(n)',code)
        self.assertIn('set breakpoint always-inserted on',code)
        self.assertNotIn('MATH_PROFILE_FIRST_RUN_STOP',code)
        capture=module.stepped_capture_namespace()
        self.assertEqual(capture['resolve_qemu'](None),exe)
        self.assertIn(str(firmware),capture['_capture_run'].__code__.co_consts)
        probe=json.loads((base/'accelerator-probe13.json').read_text())
        self.assertTrue(probe['passed']);self.assertLess(probe['elapsed'],20)
        data=json.loads(binding.read_text());data['sha256']='0'*64
        bad=binding.parent/('rejected-binding-'+uuid.uuid4().hex+'.json')
        bad.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'portable binary binding'):guest.portable_toolchain(bad)

    def test_default_projection(self):
        import verify_x86_64_math_runtime as verify
        self.assertTrue(verify.projection())

    def test_retained_numeric_snapshots(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        folder=ROOT/'build/codex-agent/r83bs-native-math/diagnostic01'
        rows=json.loads((folder.parent/'diagnostic01-decoded.json').read_text(encoding='utf-8'))
        image=folder.parent/'build01/x86_64/reist-x86_64-bootstrap.elf'
        config,_,_=guest.image_config(image,'healthy4g');raw=guest.wide.old.Snapshots(folder)
        starts={r['gen']:r for r in rows if r['kind']=='start'};count=0
        for row in rows:
            if row['kind'].startswith('math_'):
                guest.validate_math_event(row,starts,set(starts),config,raw);count+=1
        self.assertEqual(count,16)

    def test_complete_raw_replay_and_mutations(self):
        import json,copy
        import run_qemu_x86_64_math_runtime as guest
        folder=ROOT/'build/codex-agent/r83bs-native-math/diagnostic02'
        image=folder.parent/'build01/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'healthy4g');module=guest.namespace('healthy4g');module.app_files=files
        module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        trace=guest.wide.decode_evidence((folder/'frame-trace.log').read_text(encoding='utf-8'))
        rows=[json.loads(line[14:]) for line in trace.splitlines() if line.startswith('SHELL_SESSION ')]
        starts={r['gen']:r for r in rows if r['kind']=='start'};raw=guest.wide.old.Snapshots(folder)
        for kind,key,offset in (('math_checkpoint','witness',8),('math_blocked','saved',24),
                                ('math_blocked','task',8),('math_fresh','raw',160),('math_reaped','raw',160)):
            row=next(r for r in rows if r['kind']==kind)
            descriptor=row[key]
            class Changed:
                def read(self,d,size):
                    data=raw.read(d,size)
                    if d==descriptor:
                        data=bytearray(data);data[offset]^=16;data=bytes(data)
                    return data
            with self.assertRaises(ValueError):guest.validate_math_event(row,starts,set(starts),config,Changed())

    def test_archive_and_stack_review(self):
        import verify_x86_64_math_runtime as verify
        image=ROOT/'build/codex-agent/r83bs-native-math/build01/x86_64/reist-x86_64-bootstrap.elf'
        self.assertLess(verify.stack_review(image)['aggregate'],32768)
        self.assertIn('lrint',verify.archive_review(image)['exports'])

    def test_actual_fault_and_unsupported_mxcsr_replays(self):
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math'
        image=base/'build01/x86_64/reist-x86_64-bootstrap.elf'
        for number,label in (('03','x87-fault'),('04','mxcsr-fault')):
            config,records,files=guest.image_config(image,label);module=guest.namespace(label);module.app_files=files
            args=(base/('diagnostic'+number),config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
            if number=='03':module.evaluate(*args)
            else:
                # Negative evidence: accepting status95 would hide the missing
                # architectural #GP. This does not satisfy the runtime gate.
                with self.assertRaisesRegex(ValueError,'ordinary foreground actual outcome'):
                    module.evaluate(*args)

    def test_hardware_mxcsr_raw_replay(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math'
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf';folder=base/'diagnostic17'
        config,records,files=guest.image_config(image,'mxcsr-fault')
        module=guest.namespace('mxcsr-fault');module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
        guest.validate_hardware_bootstrap(folder,config,require_cleared=False)
        # A changed bootstrap address must fail even when the guest history
        # itself is valid. The historical diagnostic predates the raw cleared
        # cell file; every qualification guest must supply that file.
        changed=dict(config,s=dict(config['s']))
        changed['s']['native_math_hardware_ready']+=8
        with self.assertRaisesRegex(ValueError,'physical binding'):
            guest.validate_hardware_bootstrap(folder,changed,require_cleared=False)
        with self.assertRaises(FileNotFoundError):guest.validate_hardware_bootstrap(folder,config)

    def test_hardware_stack_source_roots(self):
        import copy
        import verify_x86_64_math_runtime as verify
        base=ROOT/'build/codex-agent/r83bs-native-math/candidate01'
        a=base/'build/x86_64/reist-x86_64-bootstrap.elf'
        b=base/'hardware/x86_64/reist-x86_64-bootstrap.elf'
        first=verify.stack_review(a);second=verify.stack_review(b)
        self.assertNotEqual(first,second) # compiler reports contain build roots
        expected=verify.stack_signature(a,first)
        self.assertEqual(expected,verify.stack_signature(b,second))
        changed=copy.deepcopy(second)
        changed['functions'][next(iter(changed['functions']))]+=8
        self.assertNotEqual(expected,verify.stack_signature(b,changed))

    def test_archive_debug_directory_difference(self):
        import verify_x86_64_math_runtime as verify
        base=ROOT/'build/codex-agent/r83bs-native-math/candidate02'
        a=verify.archive_review(base/'build/x86_64/reist-x86_64-bootstrap.elf')
        b=verify.archive_review(base/'hardware/x86_64/reist-x86_64-bootstrap.elf')
        self.assertNotEqual(a['archive']['sha256'],b['archive']['sha256'])
        self.assertEqual(a['relocatable_sha256'],b['relocatable_sha256'])
        for name in ('exports','undefined','simd'):self.assertEqual(a[name],b[name])

    def test_duplicate_checkpoint_rejected(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math';folder=base/'diagnostic18'
        rows=[json.loads(line) for line in (folder/'math-checkpoint-debug.jsonl').read_text().splitlines()]
        pairs=[(a,b) for a,b in zip(rows,rows[1:]) if a['gen']==b['gen'] and a['witness']==b['witness']]
        self.assertTrue(pairs)
        for a,b in pairs:
            self.assertEqual((a['rip'],a['rsp'],a['caller']),(b['rip'],b['rsp'],b['caller']))
            self.assertEqual(a['flags']^b['flags'],0x100)
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'rounding-state');module=guest.namespace('rounding-state')
        module.app_files=files
        with self.assertRaisesRegex(ValueError,'exact checkpoint/lifecycle counts'):
            module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)

    def test_hardware_rounding_raw_replay(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math';folder=base/'diagnostic19'
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'rounding-state');module=guest.namespace('rounding-state')
        module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
        guest.validate_hardware_bootstrap(folder,config)

    def test_debugger_irq_step_correction(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math'
        negative=(base/'diagnostic20/stderr.log').read_text()
        self.assertIn('WHPX: Failed to set InterruptState, hr=c0350015',negative)
        self.assertIn('native_flags=346',negative)
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        config,_,_=guest.image_config(image,'healthy4g')
        with self.assertRaisesRegex(ValueError,'no ignored hardware verifier error'):
            guest.validate_hardware_bootstrap(base/'diagnostic20',config)
        for number,label in ((21,'healthy4g'),(22,'rounding-state')):
            folder=base/('diagnostic%d'%number)
            config,records,files=guest.image_config(image,label);module=guest.namespace(label);module.app_files=files
            proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
            self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
            guest.validate_hardware_bootstrap(folder,config)

    def test_complete_crash_with_registered_probes(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math';folder=base/'diagnostic24'
        comparison=json.loads((base/'accelerator-probe12/register-api.json').read_text())
        self.assertEqual(len(comparison['registers']),26)
        self.assertEqual(comparison['reads_per_method'],3328)
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'crash');module=guest.namespace('crash');module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
        guest.validate_hardware_bootstrap(folder,config)

    def test_owner_loss_physical_breakpoint_binding(self):
        import json
        import run_qemu_x86_64_math_runtime as guest
        base=ROOT/'build/codex-agent/r83bs-native-math'
        negative=base/'candidate06/guests/owner-loss/binary-memory'
        record=(negative/'ram-0028.bin').read_bytes()
        expected=record[96+16*4096:96+17*4096]
        actual=(negative/'ram-0029.bin').read_bytes()[:4096]
        self.assertEqual([(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b],[(45,0x55,0xcc)])
        image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        config,records,files=guest.image_config(image,'owner-loss')
        module=guest.namespace('owner-loss');module.app_files=files
        args=(config,records,(image.parent/'boot-programs.bin').read_bytes(),15,2,files)
        for number in (25,26):
            with self.assertRaisesRegex(ValueError,'exact checkpoint/lifecycle counts'):
                module.evaluate(base/('diagnostic%d'%number),*args)
        folder=base/'diagnostic27'
        proof=module.evaluate(folder,*args)
        self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
        guest.validate_hardware_bootstrap(folder,config)

    def test_seven_file_media(self):
        import build_x86_64_math_runtime_media as media
        import check_x86_64_math_runtime_media as check
        elf=self.folder/'elf64/mathtest.prg'
        if not elf.exists():self.test_real_elf64_archive_and_consumer()
        before=ROOT/'build/codex-agent/r83br-cpp-runtime/candidate01/build/x86_64'
        roots=list(before.glob('programs-*/root'));self.assertEqual(len(roots),1)
        files={n:(roots[0]/n).read_bytes() for n in check.accepted.NAMES}
        files['mathtest.prg']=elf.read_bytes()
        raw=media.image('ext2-1k',files);check.verify_volume(raw,files)
        self.assertEqual(len(check.NAMES),7)
        position=raw.find(files['mathtest.prg']);self.assertGreaterEqual(position,32*1024)
        for offset in (1024+16,2048+14,4096,position+256):
            changed=bytearray(raw);changed[offset]^=1
            with self.assertRaises(ValueError):check.verify_volume(bytes(changed),files)

if __name__=='__main__':unittest.main()
