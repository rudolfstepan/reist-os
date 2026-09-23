"""Native formatter behavior, ABI and retained-profile evidence."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class NativeTextRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        cls.folder=ROOT/'build/codex-agent/r83bt-native-text'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True)
        cls.env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(ROOT/'build/zig-global-cache'),
                     ZIG_LOCAL_CACHE_DIR=str(cls.folder/'cache'))

    def run_command(self,args,timeout=90):
        p=subprocess.run(list(map(str,args)),env=self.env,cwd=ROOT,capture_output=True,
            text=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        return p.stdout.replace('\r','')

    def test_explicit_native_architecture(self):
        import build_user_text as text
        for value in ('arm64','',None,True):
            with self.assertRaisesRegex(ValueError,'architecture'):
                text.compile_text(find_zig(),self.folder,self.folder,self.env,architecture=value)

    def test_media_and_observer_construction(self):
        import run_qemu_x86_64_text_runtime as guest
        import check_x86_64_text_runtime_media as check
        base=ROOT/'build/codex-agent/r83bt-native-text'
        image=base/'build03/x86_64/reist-x86_64-bootstrap.elf'
        from verify_x86_64_text_runtime import PORTABLE as binding
        for label,case,_,_ in guest.CASES:
            config,records,files=guest.image_config(image,label)
            medium=guest.media.image('ext2-1k',files);check.verify_volume(medium,files)
            self.assertEqual(len(files),8)
            for at in (1024+16,4096+2,medium.find(files['texttest.prg'])+256):
                bad=bytearray(medium);bad[at]^=1
                with self.assertRaises(ValueError):check.verify_volume(bytes(bad),files)
            folder=self.folder/label;folder.mkdir()
            module=guest.hardware_namespace(label,toolchain=binding)
            code=module.observer(config,records,folder,case,2)
            compile(code.split('python\n',1)[1].rsplit('\nend',1)[0],'<text observer>','exec')
            self.assertIn("cr2=reg('cr2')",code)
            self.assertIn('actual single RET target hit',code)
            self.assertIn('set breakpoint always-inserted on',code)
            self.assertNotIn('TEXT_PROFILE_FIRST_RUN_STOP',code)

    def test_default_projection(self):
        import verify_x86_64_text_runtime as verify
        self.assertTrue(verify.projection())

    def test_canceled_breakpoint_fail_to_pass(self):
        import difflib,json
        import run_qemu_x86_64_text_runtime as guest
        base=ROOT/'build/codex-agent/r83bt-native-text'
        failed=json.loads((base/'diagnostic25/text-ret-mismatch.json').read_text())
        self.assertEqual(failed['step'],2580)
        self.assertEqual(failed['after_sp'],failed['sp']+8)
        self.assertNotEqual(failed['before'],failed['after'])
        self.assertEqual(failed['before']['cr3'],failed['after']['cr3'])
        for number in (25,26):
            log=(base/f'diagnostic{number}/stderr.log').read_text()
            self.assertEqual(log.count('BT_CANCEL_INJECT'),1)
            self.assertIn('pc=ffffffff8010ec41 flags=46 ret=2580',log)
            self.assertIn('mismatch=0',log)
        self.assertFalse((base/'diagnostic26/text-ret-mismatch.json').exists())
        image=base/'build03/x86_64/reist-x86_64-bootstrap.elf';folder=base/'diagnostic26'
        config,records,files=guest.image_config(image,'healthy8g')
        module=guest.namespace('healthy8g');module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),guest.spec_for('healthy8g')[1],2,files)
        self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
        guest.validate_hardware_bootstrap(folder,config)
        # Production must contain exactly the tested correction on the accepted
        # source, with neither diagnostic instrumentation nor event injection.
        injected=base/'portable-cancel-correction01';production=base/'portable-production01'
        a=(injected/'whpx-all-before.c').read_text().splitlines(True)
        b=(injected/'whpx-all-after.c').read_text().splitlines(True)
        source=(production/'whpx-all-before.c').read_text()
        self.assertEqual(source,(base/'portable-diagnostic01/whpx-all-before.c').read_text())
        count=0
        for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
            if tag=='equal':continue
            lo=max(0,i-1);hi=min(len(a),j+1)
            old=''.join(a[lo:hi]);new=''.join(a[lo:i]+b[k:l]+a[j:hi])
            self.assertEqual(source.count(old),1);source=source.replace(old,new);count+=1
        self.assertEqual(count,4)
        self.assertEqual(source,(production/'whpx-all-after.c').read_text())
        self.assertNotIn('BT_CANCEL_INJECT',source)
        self.assertNotIn('bt_ret_begin',source)

    def test_native_archive_stack_and_providers(self):
        import verify_x86_64_text_runtime as verify
        image=ROOT/'build/codex-agent/r83bt-native-text/build03/x86_64/reist-x86_64-bootstrap.elf'
        archive=verify.archive_review(image)
        self.assertTrue({'snprintf','vsnprintf'}<=set(archive['exports']))
        stack=verify.stack_review(image)
        self.assertLessEqual(stack['aggregate']+stack['margin'],stack['stack'])

    def test_healthy_raw_replay(self):
        import json
        import run_qemu_x86_64_text_runtime as guest
        base=ROOT/'build/codex-agent/r83bt-native-text'
        image=base/'build03/x86_64/reist-x86_64-bootstrap.elf';folder=base/'diagnostic01'
        config,records,files=guest.image_config(image,'healthy4g')
        module=guest.namespace('healthy4g');module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
        guest.validate_hardware_bootstrap(folder,config)

    def test_fault_and_owner_loss_raw_replays(self):
        import json
        import run_qemu_x86_64_text_runtime as guest
        base=ROOT/'build/codex-agent/r83bt-native-text'
        image=base/'build03/x86_64/reist-x86_64-bootstrap.elf'
        for number,label,case in ((2,'invalid-count',0),(3,'owner-loss',15)):
            folder=base/('diagnostic%02d'%number)
            config,records,files=guest.image_config(image,label);module=guest.namespace(label);module.app_files=files
            proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),case,2,files)
            self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
            guest.validate_hardware_bootstrap(folder,config)

    def test_witness_and_fault_mutations(self):
        import struct,types,copy
        import run_qemu_x86_64_text_runtime as guest
        values={'errno':struct.pack('<i',61),'task':struct.pack('<128Q',2,7,0x100000000,*([0]*125)),
            'witness':struct.pack('<16Q',1,1,8,8,len(guest.FORMATTED),61,0x800,*([0]*9)),
            'output':guest.FORMATTED+bytes(256-len(guest.FORMATTED))}
        def read(name,size):
            self.assertEqual(len(values[name]),size);return values[name]
        raw=types.SimpleNamespace(read=read)
        row=dict(kind='text_checkpoint',gen=7,run=1,slot=4,pc=0x41002d,root=0x100000000,
            witness='witness',output='output',errno='errno')
        starts={7:dict(args=['texttest.prg'],run=1,task='task')};config=dict(text_checkpoint=0x41002d)
        guest.validate_text_event(row,starts,{7},config,raw)
        initial=copy.deepcopy(values)
        for index,value in ((1,2),(2,4),(3,4),(4,1),(5,0),(6,0),(7,1),(15,1)):
            w=list(struct.unpack('<16Q',initial['witness']));w[index]=value;values['witness']=struct.pack('<16Q',*w)
            with self.assertRaises(ValueError):guest.validate_text_event(row,starts,{7},config,raw)
        values.update(initial)
        for name,bad in (('errno',bytes(4)),('output',b'x'+initial['output'][1:])):
            values[name]=bad
            with self.assertRaises(ValueError):guest.validate_text_event(row,starts,{7},config,raw)
            values.update(initial)
        with self.assertRaises(ValueError):guest.validate_text_event(row,starts,set(),config,raw)
        for mode,error in ((2,4),(3,6),(4,6)):
            self.assertEqual(guest.text_vector(dict(text_mode=mode),dict(slot=4,cr2=4)),(14,error))
            with self.assertRaises(ValueError):guest.text_vector(dict(text_mode=mode),dict(slot=4,cr2=8))

    def test_crash_raw_replay_requires_fault_not_timeout(self):
        import run_qemu_x86_64_text_runtime as guest
        base=ROOT/'build/codex-agent/r83bt-native-text'
        image=base/'build03/x86_64/reist-x86_64-bootstrap.elf'
        folder=base/'diagnostic20'
        config,records,files=guest.image_config(image,'crash')
        module=guest.namespace('crash');module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        self.assertTrue(proof)
        guest.validate_hardware_bootstrap(folder,config)

    def test_hang_and_cpu_raw_replays(self):
        import json
        import run_qemu_x86_64_text_runtime as guest
        base=ROOT/'build/codex-agent/r83bt-native-text'
        image=base/'build03/x86_64/reist-x86_64-bootstrap.elf'
        for number,label in ((21,'hang'),(22,'cpu')):
            with self.subTest(label=label):
                folder=base/('diagnostic%02d'%number)
                config,records,files=guest.image_config(image,label)
                module=guest.namespace(label);module.app_files=files
                proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
                self.assertEqual(proof,json.loads((folder/'summary.json').read_text())['proof'])
                guest.validate_hardware_bootstrap(folder,config)

    def test_native_c_cpp_headers(self):
        from build_user_program import validate_cpp_object
        source=self.folder/'headers.c'
        source.write_text('#include <stdio.h>\n#include <reist/x86_64/text_runtime.h>\nint f(char *p) { return snprintf(p,8,"%ld",1L); }\n')
        for lang in ('c','c++'):
            obj=self.folder/(lang+'.o')
            self.run_command([find_zig(),'cc','-target','x86_64-freestanding-none','-ffreestanding',
                '-fno-exceptions','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                '-Werror','-Iuserspace/text/include','-Iuserspace/sdk/include','-x',lang,'-c',source,'-o',obj])
            validate_cpp_object(obj.read_bytes(),architecture='x86_64')

    def test_static_formatter_stack(self):
        import build_user_text as text
        folder=self.folder/'static';folder.mkdir()
        vendor=text.extract(folder/'upstream')
        text.compile_text(find_zig(),vendor,folder,self.env,architecture='x86_64')
        reports=list(folder.glob('cache-*/tmp/*.su'));self.assertEqual(len(reports),5)
        rows=[line.split('\t') for p in reports for line in p.read_text().splitlines()]
        self.assertTrue(rows)
        self.assertTrue(all(kind=='static' and 0<=int(size)<=8192 for _,size,kind in rows),rows)
        self.assertLessEqual(sum(int(size) for _,size,_ in rows)+2048,32768)

    def test_actual_amd64_o0_o2(self):
        import build_user_text as text
        vendor=text.extract(self.folder/'upstream')
        for opt in ('-O0','-O2'):
            folder=self.folder/opt;folder.mkdir()
            objects=text.compile_text(find_zig(),vendor,folder,self.env,host=True,opt=opt,architecture='x86_64')
            exe=folder/'text-host.exe'
            self.run_command([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-fno-builtin',
                '-msse2','-mno-avx','-mno-mmx','-Iuserspace/math/include','-Iuserspace/libc/include',
                'test/x86_64_text_host.c',*objects,'-o',exe])
            output=self.run_command([exe],30)
            self.assertIn('TEXT_HOST_OK reference_samples=128',output)
            self.assertIn('NATIVE_TEXT_HOST_OK pointer_bits=64 long_bits=32',output)

if __name__=='__main__':unittest.main()
